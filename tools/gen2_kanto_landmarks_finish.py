"""Whole native Kanto landmarks, closed facades and directional gate portals.

Keeps full original footprints/entry anchors. Native roof/wall units repeat at
1:1; complete arches, door caps, windows and left/right portal pairs remain
intact. Decorative upper/side cells carry alpha and never change collisions.
"""
import argparse
import copy
import hashlib
import json
import re
from collections import Counter, deque
from pathlib import Path
from types import SimpleNamespace

from PIL import Image
import catalog
import preview
import gen2_extended_review as e
from center_mart_overhang_review import write_rows
from gen2_kanto_buildings_finish import templates_for, safe_native_art
from gen2_kanto_shores_finish import Reviewer as ShoresReviewer
from goldenrod_native_art import remap
from johto_remaining_review import artwork
from native_room_parts import RoomParts

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'.work/tileshift-gen2-kanto-landmarks'
TARGET=ROOT/'mappings/gen2_kanto_landmarks_finish.lua'
DECOR=ROOT/'lib/gen2_kanto_landmark_decorations.lua'
ASSETS=ROOT/'assets/third_party/kanto-landmarks'
PUBLIC_URL='https://imgur.com/gallery/testing-out-gen-3-style-tiles-johto-6A43Cji'
GRASS={(66,181,140,255),(115,206,165,255),(165,230,197,255)}
ROOF_BRICK_LEFT=(76,78,90,94)
ROOF_BRICK_MID=(78,78,94,94)
ROOF_BRICK_RIGHT=(78,77,94,90)
ROOF_GABLE_LEFT=(5,6,21,22)
ROOF_GABLE_TALL_LEFT=(5,6,21,56)


def mapping_key(row):
    return tuple(row.get(k)for k in('game','style','tileset','id','quadrant','map','x','y'))


def remove_authored_rows(path,rows,removed):
    """Delete exact authored row literals, retaining every other row's bytes."""
    result=[];number=0
    for line in path.read_text().splitlines(keepends=True):
        if not line.startswith('add((function()return {'):
            result.append(line);continue
        spans=[];depth=0;quoted=escaped=False;start=None
        for i in range(line.index('{'),len(line)):
            char=line[i]
            if quoted:
                if escaped:escaped=False
                elif char=='\\':escaped=True
                elif char=='"':quoted=False
                continue
            if char=='"':quoted=True
            elif char=='{':
                if depth==1:start=i
                depth+=1
            elif char=='}':
                depth-=1
                if depth==1 and start is not None:spans.append((start,i+1));start=None
        assert depth==0 and not quoted
        if not spans:result.append(line);continue
        keep=[]
        for a,b in spans:
            if number not in removed:keep.append(line[a:b])
            number+=1
        separator=line[spans[0][1]:spans[1][0]]if len(spans)>1 else','
        result.append(line[:spans[0][0]]+separator.join(keep)+line[spans[-1][1]:])
    assert number==len(rows),(path,number,len(rows))
    expected=[r for i,r in enumerate(rows)if i not in removed]
    path.write_text(''.join(result))
    assert preview.read_reviewed(path)==expected,'Exact supersession changed an unrelated authored row'


def supersede_older_positioned(rows):
    """A whole new native footprint replaces exact older positioned artwork.

    Generic fallbacks remain intact. Source fingerprints, collision, palette
    slots and priorities must be identical before an older key can be removed.
    """
    replacements={mapping_key(r):r for r in rows if r.get('x')is not None}
    changed=[]
    main_files=list(dict.fromkeys(re.findall(r"'(mappings/[^']+\.lua)'",(ROOT/'main.lua').read_text())))
    for name in main_files:
        path=ROOT/name
        if path==TARGET:continue
        old=preview.read_reviewed(path);remove=set();records=[]
        for index,r in enumerate(old):
            if r.get('x')is None:continue
            replacement=replacements.get(mapping_key(r))
            if replacement is None:continue
            for field in('sourceHash','sourceFiles','sourceCollision','sourcePriority','sourcePalettes'):
                assert r.get(field)==replacement.get(field),(name,mapping_key(r),field)
            remove.add(index)
            records.append(dict(key=list(mapping_key(r)),previous_role=r['role'],replacement_role=replacement['role'],
                sourceHash=r['sourceHash'],previous_artwork_hash=r.get('compositionPixelHash'),
                replacement_artwork_hash=replacement.get('compositionPixelHash')))
        if remove:
            before=catalog.sha(path.read_bytes());remove_authored_rows(path,old,remove)
            changed.append(dict(module=name,removed_rows=len(remove),before_sha256=before,
                after_sha256=catalog.sha(path.read_bytes()),exact_keys=records))
    # The older Route16 house had no decorative extension. Check the separate
    # catalog explicitly so stale house roofs cannot survive an art change.
    old_decor=preview.read_reviewed(ROOT/'lib/gen2_kanto_building_roofs.lua')
    route16=[r for r in old_decor if r.get('map')=='ROUTE_16'and r.get('game')in e.GAMES
             and(r.get('buildingX'),r.get('buildingY'),r.get('buildingW'),r.get('buildingH'))==(10,4,4,4)]
    assert not route16,'Superseded Route16 house still has a decorative extension'
    proof=dict(removed_rows=sum(v['removed_rows']for v in changed),changed_modules=changed,
        route16_type='Native transit gate with paired left/right source side portals9/14,6/7; no front entrance.',
        superseded_route16_decorative_rows=0,generic_fallbacks_unchanged=True)
    (OUT/'positioned-supersession.json').write_text(json.dumps(proof,indent=2)+'\n')
    return proof


def compile_all_main_rows():
    """Run the actual same Mapping.index call that gates main.lua boot."""
    from lupa.luajit21 import LuaRuntime
    runtime=LuaRuntime(unpack_returned_tuples=True)
    mapping=runtime.execute((ROOT/'lib/mapping.lua').read_text())
    files=list(dict.fromkeys(re.findall(r"'(mappings/[^']+\.lua)'",(ROOT/'main.lua').read_text())))
    runner=runtime.eval('''function(mapping,sources)
      local all={}
      for _,source in ipairs(sources)do
        local rows=assert(loadstring(source))()
        for _,row in ipairs(rows)do all[#all+1]=row end
      end
      local indexed,errors=mapping.index(all)
      return #all,#errors,errors
    end''')
    count,rejected,errors=runner(mapping,runtime.table_from([(ROOT/name).read_text()for name in files]))
    messages=[errors[i]for i in range(1,rejected+1)]
    proof=dict(main_listed_modules=len(files),rows=count,rejected=rejected,errors=messages,
        actual_main_mapping_index=True)
    (OUT/'main-integration-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    assert rejected==0,messages[:20]
    return proof


class Reviewer(ShoresReviewer):
    def __init__(self):
        super().__init__()
        self.active=[r for p in sorted((ROOT/'mappings').glob('*.lua'))if p!=TARGET for r in preview.read_reviewed(p)]
        self.all_decor=[r for n in('roof_catalog.lua','side_catalog.lua','center_mart_roofs.lua','goldenrod_roofs.lua',
            'pallet_roofs.lua','johto_roofs.lua','gen2_kanto_building_roofs.lua')for r in preview.read_reviewed(ROOT/'lib'/n)]
        self.objects={};self.files={};self.features=[]
        self.closed_gate=self.grid('OLIVINE_CITY','olivine_port_closed_front')
        self.front_gate=self.grid('MAHOGANY_TOWN','mahogany_north_gate')
        self.gate_room=RoomParts(self.imp,'firered','FR_ROUTE_15')
        self.police_room=RoomParts(self.imp,'firered','FR_CERULEAN_CITY')
        self.build_assets()
        data=e.source(self.cache,'crystal')
        ts=templates_for(self.cache,'crystal',data,self.active)
        self.small_home=next(t for t in ts if t['role']=='architecture_home48'and t['w']==4 and t['h']==3 and t['door']==[1,2])
        self.center=next(t for t in ts if t['role']=='larger_center'and t['w']==4 and t['h']==4)
        self.rows=[];self.decor=[];self.proofs=[];self.occupied=set()

    def grid(self,name,role):
        rows=[r for r in self.active if r['game']=='crystal'and r.get('map')==name and r['role']==role]
        assert rows
        ox,oy=min(r['x']for r in rows),min(r['y']for r in rows)
        return {(r['x']-ox,r['y']-oy):r for r in rows}

    def save_asset(self,name,image,metadata,credit,url):
        ASSETS.mkdir(parents=True,exist_ok=True)
        assert image.width%16==image.height%16==0
        assert set(image.getchannel('A').get_flattened_data())<={0,255}
        path=ASSETS/(name+'.png');image.save(path);self.files[path.name]=catalog.sha(path.read_bytes())
        value={}
        for y in range(image.height//16):
            for x in range(image.width//16):
                p=ASSETS/f'{name}-{x}-{y}.png';image.crop((x*16,y*16,x*16+16,y*16+16)).save(p)
                self.files[p.name]=catalog.sha(p.read_bytes())
                value[x,y]={'kind':'third_party','asset':p.relative_to(ROOT).as_posix(),
                    'assetFileHash':self.files[p.name],'credit':credit,'sourceUrl':url}
        self.objects[name]=metadata|{'pixel_scale':1,'dimensions':list(image.size),'rgba_sha256':catalog.sha(image.tobytes())}
        image.resize((image.width*4,image.height*4),Image.Resampling.NEAREST).save(OUT/(name+'-native-size-proof.png'))
        return value

    def build_assets(self):
        atlas_path=ROOT.parent/'.work/tileshift-ecruteak-finish/johto-native-atlas.png'
        atlas=Image.open(atlas_path).convert('RGBA')
        station=atlas.crop((0,2792,80,2864));im=Image.new('RGBA',(128,80))
        xs=list(range(64))+list(range(32,48))*3+list(range(64,80))
        assert len(xs)==128
        im.paste(remap(station,xs,range(32)),(0,8))
        front=list(range(8))+list(range(56,72))*3+list(range(24,56))+list(range(56,72))*2+list(range(72,80))
        assert len(front)==128
        im.paste(remap(station,front,range(32,72)),(0,40))
        assert im.crop((56,40,88,80)).tobytes()==station.crop((24,32,56,72)).tobytes()
        self.station=self.save_asset('saffron-station',im,dict(source_atlas=atlas_path.name,
            source_sha256=catalog.sha(atlas_path.read_bytes()),source_rect=[0,2792,80,72],roof_columns=xs,
            facade_columns=front,complete_arch_source=[24,32,32,40],complete_arch_target=[56,40,32,40],
            door_anchor=[72,80],processing='Repeat full16px window/pillar and plain roof units around the complete32x40 arch. No resizing or removed frame pixels.'),
            'MetalFlygon08 native Johto station components',PUBLIC_URL)
        self.public_closed={}
        source=atlas.crop((0,3264,80,3344))
        for width in (4,5,6,8,10):
            w=width*16
            units=[((8,24),(32,48),(56,72))[i%3]for i in range((w-16)//16)]
            columns=list(range(8))+[x for a,b in units for x in range(a,b)]+list(range(72,80))
            for h in(2,4):
                ys=list(range(8))+list(range(24,40))+list(range(56,80))if h==2 else list(range(80))
                art=remap(source,columns,ys)
                key=f'closed-{width}-{h}'
                self.public_closed[width,h]=self.save_asset(key,art,dict(source_atlas=atlas_path.name,
                    source_sha256=catalog.sha(atlas_path.read_bytes()),source_rect=[0,3264,80,80],columns=columns,rows=ys,
                    closed_no_door=True,processing='Full native outer caps and whole window-floor modules; only complete repetitive roof/wall modules are omitted/repeated. One decorative upper row; no scaling.'),
                    'MetalFlygon08 native closed-building components',PUBLIC_URL)
        donor=ROOT.parent/'.work/tileshift-firegold/firegold'
        meta=json.loads((donor/'catalog.json').read_text());m=next(x for x in meta['maps']if x['id']=='g03_m004')
        native=Image.open(donor/'maps/g03_m004-flat.png').convert('RGBA');sprite=native.crop((240,0,352,112))
        # Only native field pixels connected to the exterior are absent; every
        # actual tower/column/window/plinth/entrance pixel remains unchanged.
        outside=set();queue=[]
        for y in range(112):
            for x in range(112):
                if(x in(0,111)or y in(0,111))and sprite.getpixel((x,y))in GRASS:outside.add((x,y));queue.append((x,y))
        for x,y in queue:
            for dx,dy in((1,0),(-1,0),(0,1),(0,-1)):
                p=x+dx,y+dy
                if 0<=p[0]<112 and 0<=p[1]<112 and p not in outside and sprite.getpixel(p)in GRASS:outside.add(p);queue.append(p)
        original=sprite.copy()
        for p in outside:sprite.putpixel(p,(0,0,0,0))
        assert all(sprite.getpixel((x,y))==original.getpixel((x,y))for y in range(112)for x in range(112)if(x,y)not in outside)
        assert any(w['x']==18 and w['y']==6 for w in m['warps'])
        self.radio=self.save_asset('lavender-radio',sprite,dict(rom_name=meta['rom_name'],rom_sha256=meta['rom_sha256'],
            source_map=m['id'],source_pair=m['pair'],source_flat_png_sha256=catalog.sha((donor/'maps/g03_m004-flat.png').read_bytes()),
            source_rect=[240,0,112,112],native_grid=[[m['grid'][y*m['width']+x]&1023 for x in range(15,22)]for y in range(7)],
            source_door=[18,6],door_anchor=[56,112],exterior_omitted=[list(p)for p in sorted(outside)],
            processing='Complete visible native FireGold Lavender tower. Original native tower continues north beyond its map; target likewise continues beyond the north viewport. One decorative left column preserves full112px width and the original entrance, without shrinking.'),
            'FireGold1.4 by Tzx211 and contributors; native Lavender tower from user-supplied ROM','https://www.pokecommunity.com/threads/pok%C3%A9mon-fire-gold-1-4.473130/')

    def art_at(self,grid,x,y):
        r=grid[x,y]
        art=artwork(r)if 'status'in r else copy.deepcopy(r)
        if 'buildingCompact'in r:art['buildingCompact']=copy.deepcopy(r['buildingCompact'])
        return art

    def filler(self,model,y):
        # Complete repeating8px masonry/glass spacing from the inside of the
        # native left pilaster. Door caps and window objects are never cut.
        original=model[0,y];parts=[]
        for p in original.get('parts',[]):
            left=max(8,p.get('x',0));right=min(16,p.get('x',0)+p['w'])
            if left>=right:continue
            for dx in(0,8):
                q=copy.deepcopy(p);q.update(srcX=p.get('srcX',0)+left-p.get('x',0),x=left-8+dx,w=right-left);parts.append(q)
        assert parts
        return {'kind':'native_composite','base':copy.deepcopy(self.ground),'parts':parts}

    def gate(self,w,h,door=None):
        assert w>=4 and h>=4 and h%2==0
        result={}
        for y in range(h):
            for x in range(w):
                if y<2:
                    sx=0 if x==0 else 3 if x==w-1 else 1
                    art=artwork(self.closed_gate[sx,y])
                else:
                    sy=(y-2)%2
                    if door is not None and y>=h-2:
                        if x==door:sx=1
                        elif x==door+1:sx=2
                        elif x==0:sx=0
                        elif x==w-1:sx=3
                        else:sx=None
                        art=artwork(self.front_gate[sx,sy])if sx is not None else self.filler(self.front_gate,sy)
                    else:
                        sx=0 if x==0 else 3 if x==w-1 else 1+(x-1)%2
                        art=artwork(self.closed_gate[sx,sy+2])
                art['base']=copy.deepcopy(self.ground)
                result[x,y]=art
        return result

    def police(self):
        # Original target64x64 stays64x64. The full native32x24 door and24x17
        # window fit in an88px facade with transparent right-side overhang.
        # The original sign at25,17 remains visible on its separate left cell.
        native=self.police_room
        rectangles=[(448,136,48,32,0,8),(512,136,48,32,48,8),
            (448,168,8,24,0,40),(504,168,8,24,8,40),(504,168,8,24,16,40),
            (472,168,32,24,24,40),(512,168,24,24,56,40),(552,168,8,24,80,40)]
        result={}
        for cy in range(4):
            for cx in range(6):
                parts=[]
                for sx,sy,w,h,dx,dy in rectangles:
                    x0,y0=max(cx*16,dx),max(cy*16,dy);x1,y1=min(cx*16+16,dx+w),min(cy*16+16,dy+h)
                    if x0>=x1 or y0>=y1:continue
                    parts+=native.masked(sx+x0-dx,sy+y0-dy,list(range(x1-x0)),list(range(y1-y0)),x=x0-cx*16,y=y0-cy*16,background=GRASS)
                result[cx,cy]={'kind':'native_composite','base':copy.deepcopy(self.ground),'parts':parts}
        image=Image.new('RGBA',(96,64))
        for(x,y),art in result.items():
            naked=copy.deepcopy(art);naked.pop('base');image.paste(preview.replacement_image(self.cache,naked,self.packed,ROOT),(x*16,y*16))
        source=self.imp.gba('firered','FR_CERULEAN_CITY')[0]
        for label,sbox,dbox in [('whole door with jambs and cap',(472,168,504,192),(24,40,56,64)),
                                 ('whole24x17 window frame',(512,175,536,192),(56,47,80,64))]:
            assert image.crop(dbox).tobytes()==source.crop(sbox).tobytes(),label
            self.features.append(dict(object='cerulean-police',feature=label,source_map='FR_CERULEAN_CITY',source_rect=list(sbox),target_rect=list(dbox),unchanged_pixels=(dbox[2]-dbox[0])*(dbox[3]-dbox[1])))
        image.resize((384,256),Image.Resampling.NEAREST).save(OUT/'cerulean-police-native-size-proof.png')
        return result

    def league(self):
        native=RoomParts(self.imp,'firered','FR_INDIGO_PLATEAU_EXTERIOR')
        original=self.imp.gba('firered','FR_INDIGO_PLATEAU_EXTERIOR')[0]
        # One whole repeated16px facade/roof unit is omitted. The full48x64
        # entrance/arch/plinth stays intact. Eight transparent pixels on each
        # outer side align its24px door opening with BOTH native GSC warps.
        rectangles=[]
        for sx,w,dx in((96,16,8),(128,144,24)):
            rectangles.append((sx,0,w,96,dx,0))
            # Complete native32px window/foundation floors extend the wings
            # to the original full-width base. The central arch/plinth stays
            # entirely unmodified and no blocked source wall becomes lawn.
            for a,b,sy in((96,160,80),(160,208,96),(208,272,80)):
                left,right=max(sx,a),min(sx+w,b)
                if left<right:rectangles.append((left,sy,right-left,32 if a==160 else 16,dx+left-sx,96))
        refined=[]
        for sx,sy,w,h,dx,dy in rectangles:
            xs=sorted({sx,sx+w}|{v for v in(144,160,208,224)if sx<v<sx+w})
            ys=sorted({sy,sy+h}|{64}if sy<64<sy+h else{sy,sy+h})
            for y0,y1 in zip(ys,ys[1:]):
                for x0,x1 in zip(xs,xs[1:]):
                    # The native front-garden plants are separate whole16px
                    # objects, not facade windows. Replace their full columns
                    # with whole adjacent native wall/window units rather than
                    # stacking cut plant silhouettes on the repeated floor.
                    offset=-16 if y0>=64 and 144<=x0<160 else 16 if y0>=64 and 208<=x0<224 else 0
                    refined.append((x0+offset,y0,x1-x0,y1-y0,dx+x0-sx,dy+y0-sy))
        rectangles=refined
        outside={(x,y)for y in range(128)for x in range(96,272)if original.getpixel((x,y))in GRASS}
        result={}
        for cy in range(8):
            for cx in range(11):
                parts=[]
                for sx,sy,w,h,dx,dy in rectangles:
                    x0,y0=max(cx*16,dx),max(cy*16,dy);x1,y1=min(cx*16+16,dx+w),min(cy*16+16,dy+h)
                    if x0>=x1 or y0>=y1:continue
                    parts+=native.masked(sx+x0-dx,sy+y0-dy,list(range(x1-x0)),list(range(y1-y0)),
                        x=x0-cx*16,y=y0-cy*16,transparent_pixels=outside)
                result[cx,cy]={'kind':'native_composite','base':copy.deepcopy(self.ground),'parts':parts}
        image=Image.new('RGBA',(176,128))
        for(x,y),art in result.items():
            naked=copy.deepcopy(art);naked.pop('base')
            if naked.get('parts'):image.paste(preview.replacement_image(self.cache,naked,self.packed,ROOT),(x*16,y*16))
        count=0
        for y in range(64,128):
            for x in range(160,208):
                if(x,y)not in outside:
                    assert image.getpixel((x-104,y))==original.getpixel((x,y));count+=1
        self.features.append(dict(object='indigo-league',feature='complete native48x64 entrance arch and plinth',
            source_map='FR_INDIGO_PLATEAU_EXTERIOR',source_rect=[160,64,208,128],target_rect=[56,64,104,128],unchanged_pixels=count))
        self.features.append(dict(object='indigo-league',feature='native entrance and original paired warp alignment',
            source_warp=[11,6],target_warps=[[9,5],[10,5]],mapped_native_door_center=[160,88],
            original_target_door_centers=[[152,88],[168,88]],native_plinth_below_facade_is_ground=True))
        image.resize((528,384),Image.Resampling.NEAREST).save(OUT/'indigo-league-native-size-proof.png')
        return result

    def source_row(self,game,name,m,data,x,y,role):
        bid=m['blocks'][y//2*m['width']+x//2];q=y%2*2+x%2;c=e.cell_info(self.cache,game,data,m['tileset'],bid,q)
        assert all(a.get('source_pixels_complete')for a in c['attributes'])
        return dict(game=game,style='gen3',map=name,tileset=m['tileset'],id=bid,quadrant=q,x=x,y=y,sourceCells=[[x,y]],
            sourceHash=c['sourceHash'],sourceFiles=data['fingerprints'][m['tileset']],sourceCollision=c['collision'],
            sourcePriority=[bool(a.get('priority'))for a in c['attributes']],sourcePalettes=[a.get('palette',1)for a in c['attributes']],
            status='reviewed',role=role,evidence='Whole original building footprint and all original entrance destinations checked in the native map. Complete native Gen3 caps, eaves, jambs, doorway and window units retain original pixel size. Only repetitive roof/wall spacing repeats; alpha exterior pixels show the actual underlying source-map ground. Decorative upper/side rows never change source collision. Original collision, movement, encounters, map geometry, warps and scripts remain unchanged.')

    def install(self,game,name,m,data,rect,grid,role,draw_origin=None,destination=None):
        ox,oy,w,h=rect;drawx,drawy=draw_origin or(ox,oy)
        gw=max(x for x,y in grid)+1;gh=max(y for x,y in grid)+1
        if destination:
            assert any(z['destMap']==destination and ox<=z['x']<ox+w and oy<=z['y']<oy+h for z in m.get('warps',[])),(name,rect,destination)
        for py in range(gh):
            for px in range(gw):
                x,y=drawx+px,drawy+py
                if not(0<=x<m['width']*2 and 0<=y<m['height']*2):continue
                key=game,name,x,y
                art=self.art_at(grid,px,py)
                if art.get('kind')=='native_composite'and not art.get('parts'):
                    if ox<=x<ox+w and oy<=y<oy+h:art={'kind':'native','donor':copy.deepcopy(self.ground)}
                    else:continue
                r=self.source_row(game,name,m,data,x,y,role);r.update(art)
                r['base']=copy.deepcopy(self.ground)
                lower_floor=role=='kanto_whole_native_indigo_league'and y==oy+h
                if ox<=x<ox+w and oy<=y<oy+h or lower_floor:
                    if lower_floor:r['nativeFloorExtension']=True;r['evidence']+=' The complete native entrance plinth extends one decorative ground row below the facade; this is ordinary background beneath actors, preserving the source walkable floor and all collision/events.'
                    self.rows.append(r);self.occupied.add(key)
                else:
                    r.pop('base',None);r['buildingY']=oy
                    # Upper-row corners remain ordinary upper decorations,
                    # even when they extend sideways. A bounded side exists
                    # only alongside the actual vertical source footprint.
                    if oy<=y<oy+h and(x<ox or x>=ox+w):
                        r.update(side='left'if x<ox else'right',sourceX=x,buildingX=ox,buildingW=w,buildingH=h)
                    self.decor.append(r)
                r['compositionPixelHash']=catalog.sha(preview.replacement_image(self.cache,r,self.packed,ROOT).tobytes())
        self.proofs.append(dict(game=game,map=name,source_rect=list(rect),art_dimensions=[gw*16,gh*16],draw_origin=[drawx,drawy],role=role,destination=destination))

    def portals(self,game,name,m,data,missing):
        portals=[(x,y,c)for x,y,c in missing if tuple(c['tiles'])==(79,79,79,79)]
        by_column={}
        for x,y,c in portals:
            if c['collision'] in(118,126):by_column.setdefault((x,c['collision']),[]).append(y)
        for x,y,c in portals:
            if c['collision'] in(118,126):
                ys=sorted(by_column[x,c['collision']]);assert len(ys)%2==0
                dy=ys.index(y)%2
                # Left-moving source entry is the RIGHT face of the building;
                # right-moving source entry is its LEFT face. Native pairs are
                # actual Route15 x16/y11..12 and x9/y11..12, respectively.
                nx=16 if c['collision']==118 else 9;ny=11+dy
                r=self.source_row(game,name,m,data,x,y,'kanto_complete_native_gate_side_portal')
                r.update(kind='native_composite',base=copy.deepcopy(self.ground),parts=self.gate_room.rect(nx*16,ny*16,16,16,layers=['mid']))
            elif c['collision']==112:
                seed=next(z for z in self.active if z['game']==game and z['role']=='olivine_port_down_warp_marker')
                r=self.source_row(game,name,m,data,x,y,'kanto_native_down_warp_marker');r.update(artwork(seed));r['base']=copy.deepcopy(self.ground)
            else:continue
            assert any(z['x']==x and z['y']==y for z in m.get('warps',[])),(name,x,y)
            r['compositionPixelHash']=catalog.sha(preview.replacement_image(self.cache,r,self.packed,ROOT).tobytes());self.rows.append(r);self.occupied.add((game,name,x,y))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--validate',action='store_true');p.add_argument('--activate',action='store_true');p.add_argument('--no-previews',action='store_true');p.add_argument('--repair-integration',action='store_true');args=p.parse_args();assert not args.activate or args.validate
    if args.repair_integration:
        superseded=supersede_older_positioned(preview.read_reviewed(TARGET))
        compiled=compile_all_main_rows();print(json.dumps(dict(supersession=superseded,main_integration=compiled),indent=2));return
    OUT.mkdir(parents=True,exist_ok=True);tool=Reviewer();police=tool.police();league=tool.league();held=[]
    for game in e.GAMES:
        data=e.source(tool.cache,game);limit=catalog.read_lua(tool.cache/game/'data/generated/landmarks.lua')['landmarks']['LANDMARK_PALLET_TOWN']['index']
        for name,m in sorted(data['maps'].items()):
            if not isinstance(m,dict)or m.get('tileset')not in('TILESET_KANTO','TILESET_JOHTO')or m.get('environment')not in('TOWN','ROUTE')or 0<m.get('landmark',999)<limit:continue
            active=[r for r in tool.active if r['game']==game and r['tileset']==m['tileset']and r.get('map',name)==name]
            g={(r['id'],r['quadrant'])for r in active if r.get('x')is None};pos={(r['x'],r['y'])for r in active if r.get('x')is not None};grid={};missing=[]
            for i,bid in enumerate(m['blocks']):
                for q in range(4):
                    x,y=i%m['width']*2+q%2,i//m['width']*2+q//2;c=e.cell_info(tool.cache,game,data,m['tileset'],bid,q);grid[x,y]=c
                    if(bid,q)not in g and(x,y)not in pos:missing.append((x,y,c))
            if not missing:continue
            def raw(x,y):return tuple(grid[x,y]['tiles'])if(x,y)in grid else()
            def needed(rect):
                ox,oy,w,h=rect
                return any(ox<=x<ox+w and oy<=y<oy+h and(game,name,x,y)not in tool.occupied for x,y,c in missing)
            if name=='SAFFRON_CITY':tool.install(game,name,m,data,(4,0,8,4),tool.station,'kanto_whole_saffron_station',(4,-1),'SAFFRON_MAGNET_TRAIN_STATION')
            if name=='LAVENDER_TOWN':tool.install(game,name,m,data,(12,0,6,6),tool.radio,'kanto_whole_lavender_radio_tower',(11,-1),'LAV_RADIO_TOWER_1F')
            if name=='CERULEAN_CITY':tool.install(game,name,m,data,(26,14,4,4),police,'kanto_whole_cerulean_police_station',(26,14),'CERULEAN_POLICE_STATION')
            if name=='ROUTE_26':tool.install(game,name,m,data,(6,2,4,4),tool.gate(4,4,1),'kanto_whole_victory_road_gate',destination='VICTORY_ROAD_GATE')
            if name=='ROUTE_23':tool.install(game,name,m,data,(6,0,8,6),league,'kanto_whole_native_indigo_league',(5,-1),'INDIGO_PLATEAU_POKECENTER_1F')
            if name=='ROUTE_10_NORTH':
                t=tool.center;art={(xx,yy):t['rows'][yy*4+xx]for yy in range(4)for xx in range(4)}
                tool.install(game,name,m,data,(10,0,4,2),art,'larger_center',(10,-2),'ROUTE_10_POKECENTER_1F')
            if name=='ROUTE_6':tool.install(game,name,m,data,(4,0,6,2),tool.gate(6,4,2),'kanto_whole_north_edge_gate',(4,-2),'ROUTE_6_SAFFRON_GATE')
            # Complete source roof runs establish each whole facade rectangle.
            # A known cap on each end is required; missing isolated wall cells
            # never authorize a new building or a doorway.
            for y in range(m['height']*2):
                for x in range(m['width']*2):
                    first=raw(x,y)
                    if first==ROOF_BRICK_LEFT:
                        end=x+1
                        while raw(end,y)==ROOF_BRICK_MID:end+=1
                        if raw(end,y)!=ROOF_BRICK_RIGHT:continue
                        w=end-x+1;h=4
                        # Original tall closed buildings repeat complete wall
                        # courses; the bottom8px base is26/29/60, not masonry75.
                        while y+h<m['height']*2 and any(t in(15,31,75)for t in raw(x,y+h-1)[2:])and h<12:h+=2
                        rect=x,y,w,h
                        if not needed(rect)or any((game,name,xx,yy)in tool.occupied for yy in range(y,y+h)for xx in range(x,x+w)):continue
                        doors=[z for z in m.get('warps',[])if x<=z['x']<x+w and y<=z['y']<y+h and grid[z['x'],z['y']]['collision']==113]
                        assert len(doors)<=1,(name,rect,doors)
                        d=doors[0]['x']-x if doors else None
                        assert d is None or 0<d<w-1
                        tool.install(game,name,m,data,rect,tool.gate(w,h,d),'kanto_whole_native_public_building',destination=doors[0]['destMap']if doors else None)
                    elif first in(ROOF_GABLE_LEFT,ROOF_GABLE_TALL_LEFT):
                        tall=first==ROOF_GABLE_TALL_LEFT;mid=(83,83,18,18)if tall else(7,7,23,23);right=(8,9,56,25)if tall else(8,9,24,25)
                        end=x+1
                        while raw(end,y)==mid:end+=1
                        if raw(end,y)!=right:continue
                        w=end-x+1;h=4 if tall else 3 if raw(x,y+1)==(37,38,15,34)else 2;rect=x,y,w,h
                        if not needed(rect)or any((game,name,xx,yy)in tool.occupied for yy in range(y,y+h)for xx in range(x,x+w)):continue
                        doors=[z for z in m.get('warps',[])if x<=z['x']<x+w and y<=z['y']<y+h]
                        adjacent=[z for z in m.get('warps',[])if z['x']in(x-1,x+w)and y<=z['y']<y+h and'GATE'in z['destMap']]
                        if adjacent and tall:tool.install(game,name,m,data,rect,tool.gate(w,h),'kanto_whole_closed_side_gate')
                        elif not doors:
                            key=(w,2 if h==3 else h)
                            assert key in tool.public_closed,(name,rect)
                            tool.install(game,name,m,data,rect,tool.public_closed[key],'kanto_whole_closed_native_house',(x,y if h==3 else y-1))
                        elif h==3 and w==4 and len(doors)==1 and doors[0]['x']-x==2:
                            tool.install(game,name,m,data,rect,police,'kanto_whole_native_house_with_full_right_door',(x,y-1),doors[0]['destMap'])
                        elif not tall and w==4 and len(doors)==1:
                            t=tool.small_home;art={(xx,yy):t['rows'][yy*4+xx]for yy in range(3)for xx in range(4)}
                            tool.install(game,name,m,data,rect,art,'kanto_whole_native_small_facility',(x,y-1),doors[0]['destMap'])
            # Native edge-gate halves: the original full facade continues beyond
            # the map. Keep the complete hidden counterpart; the viewport clips
            # its unseen half naturally, matching the original map boundary.
            for expected,rect in {'ROUTE_15':(-2,2,4,4),'ROUTE_17':(18,80,4,4),
                                  'ROUTE_18':(-2,4,4,4),'FUCHSIA_CITY':(38,20,4,4),
                                  'ROUTE_16':(10,4,4,4)}.items():
                if name==expected and(needed(rect)or any(tuple(c['tiles'])==(79,79,79,79)for _,_,c in missing)):
                    tool.install(game,name,m,data,rect,tool.gate(4,4),'kanto_whole_native_edge_gate')
            tool.portals(game,name,m,data,missing)
            for x,y,c in missing:
                if(game,name,x,y)not in tool.occupied:held.append(dict(game=game,map=name,x=x,y=y,raw=c['tiles'],collision=c['collision']))
    # Preserve insertion order of positional overrides but write each final
    # exact target once (e.g. a true carpet overrides its closed roof underlay).
    unique={}
    for r in tool.rows:unique[r['game'],r['map'],r['x'],r['y']]=r
    rows=list(unique.values())
    # Actual source carpet cells keep their visible access marker rather than
    # receiving a decorative roof pixel from the facade immediately below.
    portal_keys={(r['game'],r['map'],r['x'],r['y'])for r in rows if r['role']in('kanto_native_down_warp_marker','kanto_complete_native_gate_side_portal')}
    tool.decor=[r for r in tool.decor if(r['game'],r['map'],r['x'],r['y'])not in portal_keys]
    dedup={}
    for r in tool.decor:dedup[r['game'],r['map'],r['x'],r['y']]=r
    tool.decor=list(dedup.values())
    proof={'rows':len(rows),'decorative_rows':len(tool.decor),'instances':tool.proofs,
        'whole_native_feature_checks':tool.features,'held_cells':len(held),'active':args.activate}
    (OUT/'held.json').write_text(json.dumps(held,indent=2)+'\n');(OUT/'candidates.json').write_text(json.dumps(rows,indent=2)+'\n')
    (OUT/'decorations.json').write_text(json.dumps(tool.decor,indent=2)+'\n')
    (ASSETS/'provenance.json').write_text(json.dumps(dict(origin='Exact native pixels from checked imported FireRed, user-supplied FireGold and already authorized MetalFlygon08 Johto source art. No AI-generated or repainted pixels, no scaling. Whole feature/cap/jamb/window checks and source coordinates retained.',objects=tool.objects,files=tool.files),indent=2)+'\n')
    if args.validate:
        proof['validation']=e.validate_batch(rows,SimpleNamespace(cache=tool.cache,engine=ROOT.parent/'.tools/engine-0395',output=OUT),ROOT)
        proof['decoration_validation']=e.validate_batch(tool.decor,SimpleNamespace(cache=tool.cache,engine=ROOT.parent/'.tools/engine-0395',output=OUT),ROOT)
    (OUT/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    if not args.no_previews:
        for name in('SAFFRON_CITY','LAVENDER_TOWN','CERULEAN_CITY','FUCHSIA_CITY','ROUTE_10_NORTH','ROUTE_2','ROUTE_26'):
            preview.map_preview(tool.cache,OUT,'crystal',name,'staged-'+name,tool.active+rows,tool.packed,1,ROOT,roof_rows=tool.all_decor+tool.decor)
    if args.activate:
        write_rows(TARGET,rows);write_rows(DECOR,tool.decor)
        proof['positioned_supersession']=supersede_older_positioned(rows)
        proof['main_integration']=compile_all_main_rows()
        (OUT/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps({k:v for k,v in proof.items()if k not in('instances','whole_native_feature_checks')},indent=2))


if __name__=='__main__':main()
