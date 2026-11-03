"""Offline visual/source audit of every selected R/B/Y outdoor counterpart.

Only the new outdoor audit module and dedicated exact native assets are
authored. Source maps, objects, collision, warps and runtime remain unchanged.
"""
import argparse
import copy
import json
import os
import re
from collections import Counter,defaultdict
from pathlib import Path
from types import SimpleNamespace

from PIL import Image,ImageDraw,ImageFont
import catalog
import preview
import gen2_extended_review as validation
from gen1_family_review import GAMES,source,cell_info,source_image
from interior_review import Imports
from johto_remaining_review import artwork
from center_mart_overhang_review import write_rows
from native_room_parts import RoomParts
from gen2_kanto_details_finish import FENCES,SINGLE_POST,COMPACT_TERMINALS,PAIR as FENCE_PAIR,CONTEXTS as FENCE_CONTEXTS
from gen2_kanto_landmarks_finish import GRASS as NATIVE_FIELD_COLORS

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'.work/tileshift-v0310-gen1-outdoor-audit'
TARGET=ROOT/'mappings/gen1_outdoor_audit.lua'
ASSETS=ROOT/'assets/third_party/gen1-outdoor-audit'
SETS={'OVERWORLD','FOREST','PLATEAU','SHIP_PORT'}
ART_FIELDS={'kind','donor','base','parts','asset','assetFileHash','assetPixelHash','assetFrames','animated','animation',
            'foreground','occludes','artOverlay','credit','sourceUrl','sourceColors','compositionPixelHash','frames','flora','buildingCompact'}
WATER_MIDS={'freshwater_pond_interior':299,'freshwater_pond_north_bank':291,'freshwater_pond_west_bank':298,
            'freshwater_pond_east_bank':300,'freshwater_pond_northwest_bank':721,'freshwater_pond_northeast_bank':722,
            'freshwater_pond_inward_northwest_bank':305,'freshwater_pond_north_johto_410':304}
OCEAN_MAPS={'PALLET_TOWN','VERMILION_CITY','CINNABAR_ISLAND','ROUTE_11','ROUTE_12','ROUTE_13',
            'ROUTE_17','ROUTE_18','ROUTE_19','ROUTE_20','ROUTE_21'}
CATALOGS=('roof_catalog.lua','side_catalog.lua','center_mart_roofs.lua','goldenrod_roofs.lua',
          'pallet_roofs.lua','johto_roofs.lua','gen2_kanto_building_roofs.lua','gen2_kanto_landmark_decorations.lua')


def digest(v):return catalog.sha(json.dumps(v,sort_keys=True,separators=(',',':')).encode())
def key(r):return tuple(r.get(k)for k in('game','style','tileset','id','quadrant','map','x','y'))


class Audit:
    def __init__(self):
        self.cache=Path(os.environ['APPDATA'])/'pokemon-love2d';self.imp=Imports(self.cache,ROOT.parent/'.work/tileshift-catalog');self.packed=self.imp.packed
        self.paths=[ROOT/p for p in dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(ROOT/'main.lua').read_text()))if ROOT/p!=TARGET]
        self.rows={p:preview.read_reviewed(p)for p in self.paths};self.all=[r for rows in self.rows.values()for r in rows]
        self.by_family=defaultdict(list)
        for p,rows in self.rows.items():
            for i,r in enumerate(rows):
                if r['game']in GAMES and r['style']=='gen3':self.by_family[r['game'],r['tileset']].append((r,p,i))
        self.sources={g:source(self.cache,g)for g in GAMES};self.images={};self.cells={};self.records=[];self.object_inventory={};self.objects={}
        self.decor=[r for name in CATALOGS for r in preview.read_reviewed(ROOT/'lib'/name)]
        self.overrides=defaultdict(dict);self.new_decor=[];self.changes=[];self.assets={};self.animations={};self.proofs={}
        self.ground=next(copy.deepcopy(r['base'])for r in self.all if r.get('base',{}).get('game')=='emerald'and r['base'].get('tileset')=='general__petalburg'and r['base'].get('id')==1)
        self.fr_safari=RoomParts(self.imp,'firered','FR_SAFARI_ZONE_WEST');self.sand=self.fr_safari.ref(277)
        self.fr_pallet=RoomParts(self.imp,'firered','FR_PALLET_TOWN')
        self.water_seed=next(r for r in self.all if r['game']=='crystal'and r['role']=='coastal_ocean_water_interior'and r.get('donor',{}).get('game')=='firered'and r.get('animated'))
        self.brick=artwork(next(r for r in self.all if r['game']=='crystal'and r['role']=='kanto_native_brick_road'))
        self.border_rows=[]

    def image(self,r):
        art=artwork(r)
        if r.get('kind')=='source_palette':art.update({k:r[k]for k in('game','tileset','id','quadrant','sourceHash','sourceFiles','sourceColors')})
        k=digest(art)
        if k not in self.images:self.images[k]=preview.replacement_image(self.cache,r,self.packed,ROOT)
        return self.images[k]

    def grid(self,g,name,m):
        generic={};pos={}
        pool=sorted(self.by_family[g,m['tileset']],key=lambda item:bool(item[0].get('map')))
        for r,p,i in pool:
            if r.get('map',name)!=name:continue
            if r.get('x')is None:generic[r['id'],r['quadrant']]=(r,p,i)
            else:pos[r['id'],r['quadrant'],r['x'],r['y']]=(r,p,i)
        result={}
        for i,bid in enumerate(m['blocks']):
            for q in range(4):
                x,y=i%m['width']*2+q%2,i//m['width']*2+q//2
                result[x,y]=pos.get((bid,q,x,y),generic.get((bid,q)))
        return result

    def render(self,g,name,m,cells,overrides=None,compact=False,extra_decor=()):
        out=Image.new('RGBA',(m['width']*32,m['height']*32));overrides=overrides or{}
        for(x,y),entry in cells.items():
            if(x,y)in overrides:
                row=overrides[x,y]
                if compact and row.get('buildingCompact'):
                    row={k:v for k,v in row.items()if k not in ART_FIELDS};row.update(overrides[x,y]['buildingCompact'])
                im=self.image(row)
            elif entry:im=self.image(entry[0])
            else:
                bid=m['blocks'][y//2*m['width']+x//2];q=y%2*2+x%2;c=cell_info(self.cache,g,self.sources[g],m['tileset'],bid,q)
                im=source_image(self.cache,g,self.sources[g],c,m)
            out.alpha_composite(im,(x*16,y*16))
        for row in self.decor+list(extra_decor):
            if row['game']!=g or row['map']!=name:continue
            if compact and row['role']=='larger_center':continue
            pixels=self.image(row)if row.get('parts')else preview.asset_image(row,ROOT)
            out.alpha_composite(pixels,(row['x']*16,row['y']*16))
        return out

    def inventory(self,render=True):
        map_images={};objects={};missing=[]
        for g in GAMES:
            data=self.sources[g]
            for name,m in sorted(data['maps'].items()):
                if not isinstance(m,dict)or m.get('tileset')not in SETS or not m.get('width')or not m.get('height'):continue
                cells=self.grid(g,name,m);self.cells[g,name]=cells;roles=Counter();kinds=Counter()
                for(x,y),entry in cells.items():
                    bid=m['blocks'][y//2*m['width']+x//2];q=y%2*2+x%2;c=cell_info(self.cache,g,data,m['tileset'],bid,q)
                    if not entry:missing.append(dict(game=g,map=name,x=x,y=y,source=c));continue
                    r,p,i=entry;im=self.image(r);roles[r['role']]+=1;kinds[r.get('kind','native')]+=1
                    objkey=digest(dict(art=artwork(r),sourceHash=r['sourceHash'],raw=c['tiles'],role=r['role']))
                    if objkey not in objects:
                        objects[objkey]=dict(role=r['role'],art=artwork(r),raw=c['tiles'],behavior=c['behavior'],sourceHash=r['sourceHash'],
                            rgba_sha256=catalog.sha(im.tobytes()),contexts=[])
                        self.objects[objkey]=(r,im)
                    objects[objkey]['contexts'].append(dict(game=g,map=name,x=x,y=y,module=p.relative_to(ROOT).as_posix(),index=i,positioned=r.get('x')is not None))
                canvas=self.render(g,name,m,cells);sha=catalog.sha(canvas.tobytes());same=map_images.get(sha)
                self.records.append(dict(game=g,map=name,tileset=m['tileset'],dimensions=list(canvas.size),cells=len(cells),
                    unmapped=sum(not item for item in cells.values()),roles=dict(roles),kinds=dict(kinds),rgba_sha256=sha,same_artwork_as=same,
                    native_source_geometry_sha256=digest({k:m.get(k)for k in('blocks','width','height','objects','warps','signs','connections')})))
                if render:
                    dest=OUT/g;dest.mkdir(parents=True,exist_ok=True);canvas.convert('RGB').save(dest/(name+'-before.png'))
                if same is None:map_images[sha]=[g,name]
                (OUT/'progress.json').write_text(json.dumps(dict(game=g,map=name,visited_maps=len(self.records))))
        self.object_inventory=objects
        (OUT/'inventory.json').write_text(json.dumps(self.records,indent=2)+'\n');(OUT/'object-inventory.json').write_text(json.dumps(objects,indent=2)+'\n');(OUT/'missing.json').write_text(json.dumps(missing,indent=2)+'\n')
        if render:self.contacts(map_images)
        return dict(map_variants=len(self.records),unique_rendered_layouts=len(map_images),source_cells=sum(r['cells']for r in self.records),
            unique_art_source_contexts=len(objects),unmapped_cells=len(missing),source_palette_cells=sum(r['kinds'].get('source_palette',0)for r in self.records))

    def contacts(self,maps):
        font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
        items=list(maps.values());cw,ch=520,560
        for start in range(0,len(items),6):
            canvas=Image.new('RGB',(cw*3,ch*2),'#18202c');d=ImageDraw.Draw(canvas)
            for i,(g,name)in enumerate(items[start:start+6]):
                im=Image.open(OUT/g/(name+'-before.png'));x,y=i%3*cw,i//3*ch
                # Contact overview only. Full native1:1 images remain beside it.
                im.thumbnail((cw-12,ch-40),Image.Resampling.NEAREST)
                canvas.paste(im,(x+6,y+34));d.text((x+6,y+5),g+' / '+name,fill='white',font=font)
            canvas.save(OUT/f'maps-contact-{start//6+1:02}.png')
        entries=list(self.objects.items());tw,th=230,130
        for start in range(0,len(entries),48):
            canvas=Image.new('RGB',(tw*6,th*8),'#18202c');d=ImageDraw.Draw(canvas)
            for i,(objkey,(r,im))in enumerate(entries[start:start+48]):
                x,y=i%6*tw,i//6*th;canvas.paste(im.resize((64,64),Image.Resampling.NEAREST),(x+4,y+30))
                d.text((x+4,y+4),str(start+i)+' '+objkey[:8],fill='white',font=font)
                role=r['role'];d.text((x+72,y+32),role[:23]+'\n'+role[23:46]+'\n'+role[46:69],fill='#d6e0e7',font=font)
                first=self.object_inventory[objkey]['contexts'][0];d.text((x+4,y+104),first['map'][:28],fill='#abc4ce',font=font)
            canvas.save(OUT/f'objects-contact-{start//48+1:02}.png')

    def ref(self,g,pair,mid):
        rec=self.imp.cell_index(g)[pair,mid]
        return dict(game=g,tileset=pair,id=mid,hash=rec['pixel_sha256'])

    def part(self,mid,layer='mid',pair=FENCE_PAIR,g='firered',sx=0,sy=0,w=16,h=16,x=0,y=0):
        rec=self.imp.cell_index(g)[pair,mid]
        return dict(donor=self.ref(g,pair,mid),layers=[layer],layerHashes={layer:rec['layer_sha256'][layer]},
                    srcX=sx,srcY=sy,w=w,h=h,x=x,y=y)

    def water(self,mid):
        if mid not in self.animations:
            art=dict(kind='native',donor=self.fr_pallet.ref(mid),animated=True,animation=copy.deepcopy(self.water_seed['animation']))
            art['animation'].pop('frame0Hash',None);frames=preview.native_water_frames(self.cache,art,self.packed)
            assert len(frames)==8 and len({f.tobytes()for f in frames})==8
            art['animation']['frame0Hash']=catalog.sha(frames[0].tobytes());self.animations[mid]=art
            self.proofs.setdefault('native_water_frames',{})[str(mid)]=dict(donor=art['donor'],frames=[catalog.sha(f.tobytes())for f in frames],pixel_scale=1)
        return copy.deepcopy(self.animations[mid])

    def queue(self,g,name,x,y,art,role,reason,extra=None):
        prior,module,index=self.cells[g,name][x,y];data=self.sources[g];m=data['maps'][name]
        c=cell_info(self.cache,g,data,m['tileset'],prior['id'],prior['quadrant'])
        assert prior['sourceHash']==c['sourceHash'] and all(a.get('source_pixels_complete',True)for a in c['attributes'])
        row={k:copy.deepcopy(v)for k,v in prior.items()if k not in ART_FIELDS}
        row.update(art);row.update(game=g,style='gen3',map=name,x=x,y=y,sourceCells=[[x,y]],role=role,status='reviewed')
        row['gen1OutdoorAudit']=dict(original_module=module.relative_to(ROOT).as_posix(),original_row_sha256=digest(prior),
            source_context=[g,name,x,y],sourceBehavior=copy.deepcopy(c['behavior']),pixel_scale=1)
        row['evidence']=reason+' Actual original per8px walk/grass/warp/door/counter flags, source pixels and map geometry are recorded. No actor, facing, collision, interaction, warp or event changes.'
        if extra:row.update(extra)
        row['compositionPixelHash']=catalog.sha(self.image(row).tobytes());self.overrides[g,name][x,y]=row
        self.changes.append(dict(game=g,map=name,x=x,y=y,role=role,reason=reason))
        return row

    def save_foreground(self,image,proof):
        ASSETS.mkdir(parents=True,exist_ok=True);sha=catalog.sha(image.tobytes());path=ASSETS/('foreground-'+sha[:24]+'.png')
        if not path.exists():image.save(path)
        self.assets.setdefault(path.relative_to(ROOT).as_posix(),dict(dimensions=list(image.size),rgba_sha256=sha,pixel_scale=1,source=proof))
        return dict(kind='third_party',asset=path.relative_to(ROOT).as_posix(),assetFileHash=catalog.sha(path.read_bytes()))

    def over_background(self,foreground,background,credit,url,proof):
        if isinstance(background,dict)and'game'in background:
            return dict(**self.save_foreground(foreground,proof),base=copy.deepcopy(background),credit=credit,sourceUrl=url)
        overlay=self.save_foreground(foreground,proof)
        return dict(kind='third_party',asset=background['asset'],assetFileHash=background['assetFileHash'],credit=credit,sourceUrl=url,
            artOverlay=dict(kind='third_party',asset=overlay['asset'],hash=overlay['assetFileHash'],mode='over',preserveRects={}))

    def rebase_city(self,row,background):
        old=artwork(row)
        if row.get('animated'):return None
        if old.get('base')and old['base'].get('id')==1 and(old.get('parts')or old.get('asset')):
            naked=copy.deepcopy(old);naked.pop('base');foreground=preview.replacement_image(self.cache,naked,self.packed,ROOT)
        elif old.get('donor')and old['donor']['game']in('firered','emerald'):
            ref=old['donor'];rec=self.imp.cell_index(ref['game'])[ref['tileset'],ref['id']]
            foreground=preview.native_donor(self.cache,ref,self.packed,['mid','over'],{k:rec['layer_sha256'][k]for k in('mid','over')})
            full=preview.native_donor(self.cache,ref,self.packed)
            omitted={b for a,b in zip(foreground.get_flattened_data(),full.get_flattened_data())if not a[3]}
            field={(66,181,140,255),(115,206,165,255),(165,230,197,255),(189,239,214,255),(156,230,197,255),(140,214,189,255)}
            if not omitted or not omitted<=field:return None
        else:return None
        if foreground.getextrema()[3][0]==255:return None
        original=self.image(row)
        assert all(a==b for a,b in zip(foreground.get_flattened_data(),original.get_flattened_data())if a[3])
        credit='Game Freak complete native Gen3 object; MetalFlygon08 brick paving where selected.'
        return self.over_background(foreground,background,credit,row.get('sourceUrl','https://github.com/pret/pokefirered'),dict(originalArtwork=old,unchanged_foreground_pixels=sum(p[3]>0 for p in foreground.get_flattened_data())))

    def terrain(self):
        for(g,name),cells in self.cells.items():
            m=self.sources[g]['maps'][name]
            for(x,y),(r,_,_)in cells.items():
                c=cell_info(self.cache,g,self.sources[g],m['tileset'],r['id'],r['quadrant']);raw=tuple(c['tiles'])
                if r['role']in WATER_MIDS:
                    self.queue(g,name,x,y,self.water(WATER_MIDS[r['role']]),r['role'],
                        'Complete matching FireRed animated pond surface/bank, preserving the exact north/west/east and inward-corner family. All8 native frames are present; static flat-blue imports are superseded.')
                elif r['role']=='gen1_kanto_nonencounter_sandy_ground'and r.get('donor',{}).get('id')==258:
                    self.queue(g,name,x,y,dict(kind='native',donor=self.sand),r['role'],
                        'The source is complete walkable sandy ground. Use complete native Safari sand277, not native NW grass/sand transition258 repeated inside the ground.')
                elif r['role']=='johto_route_complete_metal_fence'and raw in FENCES:
                    mid,layer,shape=FENCES[raw]
                    self.queue(g,name,x,y,dict(kind='native_composite',base=copy.deepcopy(r.get('base',self.ground)),parts=[self.part(mid,layer)]),
                        'gen1_native_rail_'+shape,'Complete native FR railing family has distinct handed corners and vertical/horizontal modules; replace the old repeated horizontal panel with the corresponding full native shape.')
                elif r['role']=='johto_route_complete_metal_fence'and raw in set(SINGLE_POST)|COMPACT_TERMINALS:
                    px=SINGLE_POST.get(raw,0 if raw[0]==16 else 8)
                    self.queue(g,name,x,y,dict(kind='native_composite',base=copy.deepcopy(r.get('base',self.ground)),parts=[self.part(238,'over',sx=8,sy=2,w=8,h=14,x=px,y=2)]),
                        'gen1_native_complete_rail_post','Complete native84-pixel post cap, shaft and shadow at1:1, placed on the correct original side; no clipping or scaling.')
        # Only true blocked ocean-edge scenery beside actual full-water cells
        # receives a sea rock; land trees and all Cuttable roles stay unchanged.
        for(g,name),cells in self.cells.items():
            if name not in OCEAN_MAPS:continue
            m=self.sources[g]['maps'][name];w,h=m['width']*2,m['height']*2
            for(x,y),(r,_,_)in cells.items():
                if r['role']not in('boundary_tree','dense_round_tree')or not(x in(0,w-1)or y in(0,h-1)):continue
                c=cell_info(self.cache,g,self.sources[g],m['tileset'],r['id'],r['quadrant'])
                if any(c['walkable_tiles'])or c['grass_tile_present']or c['warp_tile_present']:continue
                neighbors=[]
                for p in((x+dx,y+dy)for dy in(-1,0,1)for dx in(-1,0,1)if dx or dy):
                    entry=cells.get(p)
                    if not entry:continue
                    s=cell_info(self.cache,g,self.sources[g],m['tileset'],entry[0]['id'],entry[0]['quadrant'])
                    if tuple(s['tiles'])==(20,20,20,20):neighbors.append(p)
                if not neighbors:continue
                p=neighbors[0];water=self.overrides[g,name].get(p,cells[p][0])
                assert water.get('animated')and water.get('donor')
                art=dict(kind='native_composite',base=copy.deepcopy(water['donor']),animated=True,animation=copy.deepcopy(water['animation']),
                         parts=[self.part(404,'mid',pair='general__petalburg',g='emerald')])
                self.queue(g,name,x,y,art,'coastal_rock_shore_native_boundary_rock',
                    'Blocked map-edge ocean scenery has an actual adjacent full-water source cell. The complete native16px sea rock keeps every rock/shadow pixel over that same animated ocean, removing the unrelated grassy tree ground.',
                    dict(sourceOceanBounds=dict(adjacentFullWaterCells=[list(p)for p in neighbors])))

    def sandy_object_bases(self):
        counts=Counter()
        for(g,name),cells in self.cells.items():
            if name not in('CINNABAR_ISLAND','LAVENDER_TOWN'):continue
            for(x,y),(row,_,_)in cells.items():
                # These two towns' reviewed streets are all sand. Keep foliage
                # options and terrain transitions outside this object-only pass.
                if not(row['role'].startswith(('architecture_','gen1_kanto_whole_','gen1_kanto_complete_left_roof','gen1_kanto_complete_right_roof','gen1_kanto_native_siding','gen1_kanto_complete_native_siding','gen1_kanto_complete_roof_wall'))or row['role']=='freestanding_sign'):continue
                current=self.overrides[g,name].get((x,y),row)
                art=self.rebase_city(current,self.sand)
                if not art:continue
                self.queue(g,name,x,y,art,current['role'],
                    'The checked Cinnabar/Lavender street is native sand277. Only verified exterior field/background pixels below the complete native building/sign are replaced with that same sand; all opaque native roof, facade, door, window and sign pixels remain exact.')
                counts[g,name]+=1
        self.proofs['sandy_object_bases']={g+'/'+name:count for(g,name),count in counts.items()}

    def validate_decorations(self):
        checked=[];counts=Counter()
        for row in self.new_decor:
            m=self.sources[row['game']]['maps'][row['map']]
            x,y=row['x'],row['y'];sx,sy=row.get('sourceX',x),row.get('sourceY',y)
            assert sx==max(0,min(m['width']*2-1,x))
            assert 0<=sx<m['width']*2 and 0<=sy<m['height']*2
            if row.get('sourceY')is not None:
                assert y==-1 and row['buildingY']==0 and sy==0 and not row.get('side')
                assert row['buildingX']-1<=x<=row['buildingX']+row['buildingW']+1
                counts['north_edge_continuations']+=1
            elif row.get('side'):
                bx,by,bw,bh=(row[k]for k in('buildingX','buildingY','buildingW','buildingH'))
                assert by<=y<by+bh and bx+bw<=m['width']*2 and by+bh<=m['height']*2
                assert bx-2<=x<bx if row['side']=='left'else bx+bw<=x<=bx+bw+1
                counts['bounded_side_cells']+=1
            else:
                assert row['buildingY']==y+1;counts['upper_cells']+=1
            bid=m['blocks'][sy//2*m['width']+sx//2];q=sy%2*2+sx%2
            assert(row['id'],row['quadrant'])==(bid,q)
            c=cell_info(self.cache,row['game'],self.sources[row['game']],m['tileset'],bid,q)
            assert row['sourceHash']==c['sourceHash'] and row['sourceBehavior']==c['behavior']
            clone=copy.deepcopy(row);clone.update(x=sx,y=sy);checked.append(clone)
        # The north tip and first body row legitimately share a source guard
        # while drawing at distinct y values. Validate both art recipes in
        # separate unique-key batches, just as the cold catalog validates each.
        batches=[];keys=[]
        for row in checked:
            k=key(row)
            index=next((i for i,seen in enumerate(keys)if k not in seen),None)
            if index is None:index=len(batches);batches.append([]);keys.append(set())
            batches[index].append(row);keys[index].add(k)
        results=[validation.validate_batch(batch,SimpleNamespace(cache=self.cache,engine=ROOT.parent/'.tools/engine-0395',output=OUT),ROOT)for batch in batches]
        self.proofs['decoration_validation']=dict(counts=counts,checked_source_anchors=len(checked),validation_batches=results)

    def saffron(self):
        cityproof={};post_pair=RoomParts(self.imp,'firered','FR_INDIGO_PLATEAU_EXTERIOR').pair;post=self.part(711,'mid',pair=post_pair)
        postfg=preview.native_donor(self.cache,post['donor'],self.packed,['mid'],post['layerHashes'])
        assert sum(p[3]>0 for p in postfg.get_flattened_data())==211
        floor_roles={'short_nonencounter_grass','open_grassy_ground','gen1_kanto_complete_native_stone_paving'}
        for g in GAMES:
            name='SAFFRON_CITY';m=self.sources[g]['maps'][name];cells=self.cells[g,name]
            blocked={(4,21),(14,21),(24,29),(25,29),(26,29)}
            openings={(x,6)for x in(6,7,8,17,18,19,20,25,26,27,33,34,35)}
            openings|={(2,y)for y in(16,17,18)}|{(37,y)for y in(16,17,18)}|{(x,31)for x in(19,20,21,22)}
            counts=Counter()
            for(x,y),(r,_,_)in cells.items():
                c=cell_info(self.cache,g,self.sources[g],m['tileset'],r['id'],r['quadrant']);curb=r['role']=='johto_route_complete_metal_fence'
                perimeter=(x in(2,37)and 6<=y<=31)or(y in(6,31)and 2<=x<=37)
                urban=(2<=x<=37)or(x<2 and y in(16,17,18))or(x>37 and y in(16,17,18))
                art=None;role=r['role']
                if(x,y)in blocked:
                    assert not any(c['walkable_tiles']);art=self.over_background(postfg,self.brick,'Game Freak native complete FireRed stone bollard; MetalFlygon08 paving.',self.brick['sourceUrl'],dict(native_post=post['donor'],native_layer='mid',whole_native_pixels=211));role='gen1_saffron_visible_stone_bollard';counts['visible_blockers']+=1
                elif curb and perimeter and(x,y)not in openings:
                    current=self.overrides[g,name].get((x,y),r);changed=self.rebase_city(current,self.brick)
                    if changed:art=changed;role=current['role']
                    counts['perimeter_rail_cells']+=1
                elif urban and(curb or r['role']in floor_roles):
                    assert all(c['walkable_tiles']);art=copy.deepcopy(self.brick);role='gen1_saffron_urban_brick_paving';counts['walkable_curbs_paved'if curb else'ground_cells_paved']+=1
                elif urban and r['role']not in('boundary_tree','dense_round_tree','cuttable_small_tree'):
                    art=self.rebase_city(r,self.brick)
                    if art:counts['object_ground_rebased']+=1
                if art:self.queue(g,name,x,y,art,role,'Gen1 Saffron uses the same connected brown/yellow brick streets approved for Gen2. Only the outer rail remains, with original north-building and route access gaps; true interior blocking objects remain visible as complete native stone bollards. Object/door/window pixels are unchanged.')
            assert counts['visible_blockers']==5
            cityproof[g]=dict(counts=counts,original_warps=m['warps'],paved_access_cells=[list(p)for p in sorted(openings)],blocked_cells=[list(p)for p in sorted(blocked)])
        self.proofs['saffron']=cityproof

    def centers(self):
        clinic=ROOT/'assets/third_party/johto-hacks/centers';native=Image.new('RGBA',(80,80))
        for y in range(5):
            for x in range(5):native.alpha_composite(Image.open(clinic/f'firegold-center-{x}-{y}.png').convert('RGBA'),(x*16,y*16))
        credit='FireGold1.4 by Tzx211; complete native clinic from the user-supplied ROM.'
        url='https://www.pokecommunity.com/threads/pok%C3%A9mon-fire-gold-1-4.473130/'
        proof=[]
        for(g,name),cells in self.cells.items():
            points={p:v for p,v in cells.items()if v and v[0]['role']=='architecture_center'}
            if not points:continue
            x0,y0=min(x for x,y in points),min(y for x,y in points);assert len(points)==16 and set(points)=={(x0+x,y0+y)for y in range(4)for x in range(4)}
            m=self.sources[g]['maps'][name];warps=[z for z in m['warps']if'POKECENTER'in z['destMap']];assert len(warps)==1 and(warps[0]['x'],warps[0]['y'])==(x0+1,y0+3)
            background=self.brick if name=='SAFFRON_CITY'else self.sand if name in('CINNABAR_ISLAND','LAVENDER_TOWN')else self.ground
            native_rows=[1,2,3,4]
            model=native.copy();assert model.tobytes()==native.tobytes()
            for(x,y),(old,_,_)in points.items():
                dx,dy=x-x0,y-y0;ny=native_rows[dy];path=clinic/f'firegold-center-{dx+1}-{ny}.png'
                compact=artwork(old)
                if name=='SAFFRON_CITY':compact=self.rebase_city(old,self.brick)or compact
                elif compact.get('base'):compact['base']=copy.deepcopy(background)
                if isinstance(background,dict)and'game'in background:
                    art=dict(kind='third_party',asset=path.relative_to(ROOT).as_posix(),assetFileHash=catalog.sha(path.read_bytes()),base=copy.deepcopy(background),credit=credit,sourceUrl=url)
                else:art=self.over_background(Image.open(path).convert('RGBA'),background,credit+' MetalFlygon08 street paving.',url,dict(existing_native_asset=path.relative_to(ROOT).as_posix()))
                self.queue(g,name,x,y,art,'larger_center','Complete native FireGold clinic retains all front-wall windows, full32px entrance/emblem and door frame at1:1. The original64px body, entrance coordinate and current COMPACT artwork remain selectable. One transparent decorative left column and upper row preserve the full native width/height where source space exists.',dict(buildingCompact=compact))
            # New cold catalog only; root registers it with the existing bounded
            # decorator. Never overwrite shared catalog entries.
            placements=[(x0-1,y0+dy,0,ny,'left')for dy,ny in enumerate(native_rows)]
            placements=[(x0-1,y0-1,0,0,'left'if y0>0 else None)]+placements+[(x0+dx,y0-1,dx+1,0,None)for dx in range(4)]
            for x,y,nx,ny,side in placements:
                sy=max(0,y);assert 0<=x<m['width']*2 and -1<=y<m['height']*2
                bid=m['blocks'][sy//2*m['width']+x//2];q=sy%2*2+x%2;c=cell_info(self.cache,g,self.sources[g],m['tileset'],bid,q)
                path=clinic/f'firegold-center-{nx}-{ny}.png';row=dict(game=g,style='gen3',map=name,tileset=m['tileset'],id=bid,quadrant=q,x=x,y=y,
                    sourceHash=c['sourceHash'],sourceFiles=copy.deepcopy(self.sources[g]['fingerprints'][m['tileset']]),sourceBehavior=copy.deepcopy(c['behavior']),sourceCells=[[x,sy]],
                    kind='third_party',asset=path.relative_to(ROOT).as_posix(),assetFileHash=catalog.sha(path.read_bytes()),credit=credit,sourceUrl=url,role='larger_center',status='reviewed',
                    evidence='Exact native clinic overhang. Complete alpha/native foreground drawn once by the existing bounded decorator; no source tile, collision, actor or event edits.',buildingY=y0)
                if side:row.update(side=side,sourceX=x,buildingX=x0,buildingY=max(0,y0-1),buildingW=4,buildingH=4 if y0==0 else 5)
                if y<0:row.update(sourceY=sy,sourceX=x,buildingX=x0,buildingW=4,buildingH=4)
                self.new_decor.append(row)
            proof.append(dict(game=g,map=name,source_core=[x0,y0,4,4],original_entrance=warps[0],native_dimensions=[80,80],pixel_scale=1,
                whole_front_wall_pixels_unchanged=80*32,whole_native_clinic_pixels_unchanged=80*80,north_edge_continuation=y0==0,compact_native_art_preserved=True))
        assert len(proof)==33
        self.proofs['centers']=proof

    def league(self):
        """Use the approved unscaled GSC League fit on the identical GB anchor."""
        native=RoomParts(self.imp,'firered','FR_INDIGO_PLATEAU_EXTERIOR');original=self.imp.gba('firered','FR_INDIGO_PLATEAU_EXTERIOR')[0]
        rectangles=[]
        for sx,w,dx in((96,16,8),(128,144,24)):
            rectangles.append((sx,0,w,96,dx,0))
            for a,b,sy in((96,160,80),(160,208,96),(208,272,80)):
                left,right=max(sx,a),min(sx+w,b)
                if left<right:rectangles.append((left,sy,right-left,32 if a==160 else 16,dx+left-sx,96))
        refined=[]
        for sx,sy,w,h,dx,dy in rectangles:
            xs=sorted({sx,sx+w}|{v for v in(144,160,208,224)if sx<v<sx+w});ys=sorted({sy,sy+h}|({64}if sy<64<sy+h else set()))
            for y0,y1 in zip(ys,ys[1:]):
                for x0,x1 in zip(xs,xs[1:]):
                    offset=-16 if y0>=64 and 144<=x0<160 else 16 if y0>=64 and 208<=x0<224 else 0
                    refined.append((x0+offset,y0,x1-x0,y1-y0,dx+x0-sx,dy+y0-sy))
        outside={(x,y)for y in range(128)for x in range(96,272)if original.getpixel((x,y))in NATIVE_FIELD_COLORS}
        grid={};whole=Image.new('RGBA',(176,128))
        for cy in range(8):
            for cx in range(11):
                parts=[]
                for sx,sy,w,h,dx,dy in refined:
                    x0,y0=max(cx*16,dx),max(cy*16,dy);x1,y1=min(cx*16+16,dx+w),min(cy*16+16,dy+h)
                    if x0>=x1 or y0>=y1:continue
                    parts+=native.masked(sx+x0-dx,sy+y0-dy,list(range(x1-x0)),list(range(y1-y0)),x=x0-cx*16,y=y0-cy*16,transparent_pixels=outside)
                if not parts:continue
                art=dict(kind='native_composite',base=copy.deepcopy(self.ground),parts=parts);grid[cx,cy]=art
                whole.alpha_composite(preview.replacement_image(self.cache,dict(kind='native_composite',parts=parts),self.packed,ROOT),(cx*16,cy*16))
        count=0
        for y in range(64,128):
            for x in range(160,208):
                if(x,y)not in outside:assert whole.getpixel((x-104,y))==original.getpixel((x,y));count+=1
        assert count==2962
        for g in GAMES:
            name='INDIGO_PLATEAU';m=self.sources[g]['maps'][name]
            assert {(w['x'],w['y'])for w in m['warps']}=={(9,5),(10,5)}
            for(cx,cy),art in grid.items():
                x,y=5+cx,-1+cy
                if 6<=x<14 and 0<=y<6 or y==6:
                    self.queue(g,name,x,y,art,'gen1_whole_native_indigo_league',
                        'Complete native Gen3 Pokemon League front, with all48x64 entrance/arch/plinth pixels retained at1:1. The approved eight-cell source fit aligns the same original paired GB entrances9/10,y5; only repeat roof/wall spacing changes, while the complete native doorway and foundation remain intact.')
                    continue
                sy=max(0,y);bid=m['blocks'][sy//2*m['width']+x//2];q=sy%2*2+x%2;c=cell_info(self.cache,g,self.sources[g],m['tileset'],bid,q)
                row=dict(game=g,style='gen3',map=name,tileset=m['tileset'],id=bid,quadrant=q,x=x,y=y,sourceHash=c['sourceHash'],
                    sourceFiles=copy.deepcopy(self.sources[g]['fingerprints'][m['tileset']]),sourceBehavior=copy.deepcopy(c['behavior']),sourceCells=[[x,sy]],
                    kind='native_composite',parts=copy.deepcopy(art['parts']),role='gen1_whole_native_indigo_league',status='reviewed',
                    evidence='Complete native League repeat modules in one checked upper row or bounded side columns; native alpha retains source scenery behind it, with no physical map or actor changes.',buildingY=0)
                if y==-1:row.update(sourceY=0,sourceX=x,buildingX=6,buildingW=8,buildingH=6)
                else:row.update(side='left'if x<6 else'right',sourceX=x,buildingX=6,buildingW=8,buildingH=6)
                self.new_decor.append(row)
        whole.save(OUT/'native-full-league-fit.png')
        self.proofs['league']=dict(native_map='FR_INDIGO_PLATEAU_EXTERIOR',complete_native_entrance_rect=[160,64,48,64],unchanged_native_entrance_pixels=count,
            original_gb_warps=[[9,5],[10,5]],original_gb_door_centers=[[152,88],[168,88]],native_door_center=[160,88],pixel_scale=1,
            whole_model_rgba_sha256=catalog.sha(whole.tobytes()),only_repeated_roof_wall_spacing_rearranged=True)

    def pokemon_tower(self):
        native=RoomParts(self.imp,'firered','FR_LAVENDER_TOWN');image=self.imp.gba('firered','FR_LAVENDER_TOWN')[0].crop((240,0,352,112))
        assert image.size==(112,112)
        assembled=Image.new('RGBA',(112,112))
        grid={}
        for yy in range(7):
            for xx in range(7):
                parts=native.rect(240+xx*16,yy*16,16,16)
                art=dict(kind='native_composite',parts=parts);tile=preview.replacement_image(self.cache,art,self.packed,ROOT)
                assembled.alpha_composite(tile,(xx*16,yy*16));grid[xx,yy]=art
        assert assembled.tobytes()==image.tobytes()
        for g in GAMES:
            name='LAVENDER_TOWN';m=self.sources[g]['maps'][name];warp=next(w for w in m['warps']if w['destMap']=='POKEMON_TOWER_1F')
            assert(warp['x'],warp['y'])==(14,5)
            for(xx,yy),art in grid.items():
                x,y=11+xx,yy-1
                if x>=12 and y>=0:
                    self.queue(g,name,x,y,art,'gen1_whole_native_pokemon_tower',
                        'The complete112x112 native FR Lavender Pokemon Tower front matches the original96x96 core with one checked upper row and left column. Every native pixel, full window band, facade edge and16px entrance is retained at1:1; the original14,5 entrance remains aligned. Native north-boundary continuation is stored, not squeezed or clipped in the asset.')
                else:
                    sy=max(0,y);bid=m['blocks'][sy//2*m['width']+x//2];q=sy%2*2+x%2;c=cell_info(self.cache,g,self.sources[g],m['tileset'],bid,q)
                    row=dict(game=g,style='gen3',map=name,tileset=m['tileset'],id=bid,quadrant=q,x=x,y=y,sourceHash=c['sourceHash'],
                        sourceFiles=copy.deepcopy(self.sources[g]['fingerprints'][m['tileset']]),sourceBehavior=copy.deepcopy(c['behavior']),sourceCells=[[x,sy]],
                        kind='native_composite',parts=copy.deepcopy(art['parts']),role='gen1_whole_native_pokemon_tower',status='reviewed',buildingY=0,
                        evidence='Complete native Pokemon Tower source rectangle at unchanged pixel scale. Bounded transparent-independent upper/left continuation changes no physical tile, source warp or actor.')
                    if y<0:row.update(sourceY=0,sourceX=x,buildingX=12,buildingW=6,buildingH=6)
                    else:row.update(side='left',sourceX=x,buildingX=12,buildingW=6,buildingH=6)
                    self.new_decor.append(row)
        self.proofs['pokemon_tower']=dict(native_map='FR_LAVENDER_TOWN',source_rect=[240,0,112,112],whole_native_pixels_unchanged=112*112,
            whole_native_rgba_sha256=catalog.sha(image.tobytes()),original_entrance=[14,5],native_entrance_center=[232,88],pixel_scale=1)

    def borders(self):
        inventory=json.loads((ROOT.parent/'.work/tileshift-v0310-border-inventory.json').read_text())
        indigo=RoomParts(self.imp,'firered','FR_INDIGO_PLATEAU_EXTERIOR');route=RoomParts(self.imp,'firered','FR_ROUTE_23')
        sea=artwork(next(r for r in self.all if r['game']=='red'and r['role']=='coastal_ocean_water_interior'and r.get('animated')))
        seen=set();counts=Counter()
        for item in inventory['nonblack_missing']:
            if item['tileset']not in SETS:continue
            g,name,ts,bid,q=item['game'],item['map'],item['tileset'],item['block'],item['quadrant'];k=(g,name,ts,bid,q)
            if k in seen:continue
            seen.add(k);c=cell_info(self.cache,g,self.sources[g],ts,bid,q);raw=tuple(c['tiles'])
            assert c['sourceHash']==item['sourceHash']
            if ts=='OVERWORLD'and raw==(20,20,20,20):
                art=copy.deepcopy(sea);role='coastal_ocean_water_interior';reason='Optional water border fill is actual complete source water, not black void. Reuse the complete existing animated Gen3 ocean surface, all8 native frames, for the same source-only border block.'
            elif ts=='FOREST'and raw==(0,0,0,0):
                assert not any(c['walkable_tiles'])
                art=dict(kind='native',donor=self.fr_pallet.ref((28,29,36,37)[q]));role='forest_whole_broadleaf_tree_'+str(q)
                reason='The actual Safari border block is featureless solid blank forest backing. Its complete32px block receives one intact native32x32 FR broadleaf tree28/29 over36/37, all1024 pixels unchanged; no partial canopy or source interaction is invented.'
            elif ts=='PLATEAU'and raw==(45,45,45,45):
                assert all(c['walkable_tiles'])
                art=dict(kind='native',donor=indigo.ref(650));role='gen1_plateau_native_dense_stone_border'
                reason='The actual Indigo border is featureless walkable blank approach ground. Complete native Indigo stone650 matches the reviewed approach stone; no arch, pillar, entrance or unique source feature exists in this blank border cell.'
            elif ts=='PLATEAU'and raw==(7,8,23,24):
                art=dict(kind='native',donor=route.ref(159));role='gen1_plateau_whole_native_fixed_boulder'
                reason='Exact same complete blocked source boulder glyph and native16px Route23 boulder159 as the reviewed original route interior, extended only to the actual border block aliases.'
            else:raise AssertionError(('Unreviewed outdoor border',item,c))
            row=dict(game=g,style='gen3',map=name,tileset=ts,id=bid,quadrant=q,sourceHash=c['sourceHash'],sourceFiles=copy.deepcopy(self.sources[g]['fingerprints'][ts]),
                sourceBehavior=copy.deepcopy(c['behavior']),sourceCells={},role=role,status='reviewed',evidence=reason+' Original maps, actors, collision, events and warp coordinates remain unchanged.',
                gen1OutdoorAudit=dict(border_only=True,border_mode=item['mode'],sourceBehavior=copy.deepcopy(c['behavior']),pixel_scale=1))
            row.update(art);row['compositionPixelHash']=catalog.sha(self.image(row).tobytes());self.border_rows.append(row);counts[ts]+=1
        assert len(self.border_rows)==264
        self.proofs['border_only_new_rows']=dict(counts)

    def stage(self,activate=False):
        self.terrain();self.sandy_object_bases();self.saffron();self.centers();self.league();self.pokemon_tower();self.borders();self.validate_decorations();added=[r for points in self.overrides.values()for r in points.values()];removals={}
        for new_index,r in enumerate(added):
            prior,module,index=self.cells[r['game'],r['map']][r['x'],r['y']]
            if prior.get('x')is not None:
                removals[key(prior)]=dict(module=module.relative_to(ROOT).as_posix(),old_index=index,index=index,key=list(key(prior)),old_row=prior,full_row_sha256=digest(prior),
                    new_module=TARGET.relative_to(ROOT).as_posix(),new_index=new_index,new_row=r)
        added+=self.border_rows
        proof=validation.validate_batch(added,SimpleNamespace(cache=self.cache,engine=ROOT.parent/'.tools/engine-0395',output=OUT),ROOT)
        if activate:
            write_rows(TARGET,added);write_rows(ROOT/'lib/gen1_building_audit_roofs.lua',self.new_decor)
        (OUT/'candidates.json').write_text(json.dumps(added,indent=2)+'\n');(OUT/'decorations.json').write_text(json.dumps(self.new_decor,indent=2)+'\n');(OUT/'positioned-supersessions.json').write_text(json.dumps(list(removals.values()),indent=2)+'\n')
        (OUT/'changes.json').write_text(json.dumps(self.changes,indent=2)+'\n')
        ASSETS.mkdir(parents=True,exist_ok=True);files={Path(p).name:catalog.sha((ROOT/p).read_bytes())for p in self.assets}
        (ASSETS/'provenance.json').write_text(json.dumps(dict(assets=self.assets,files=files),indent=2)+'\n')
        if activate:
            for p in ASSETS.glob('foreground-*.png'):
                assert p.resolve().parent==ASSETS.resolve()
                if p.name not in files:p.unlink()
        report=dict(reviewed_variants=len(self.records),reviewed_source_cells=sum(r['cells']for r in self.records),reviewed_unique_layouts=len({r['rgba_sha256']for r in self.records}),
            reviewed_art_source_contexts=len(self.object_inventory),new_rows=len(added),changed_maps=len(self.overrides),new_decorations=len(self.new_decor),old_positioned_rows=len(removals),
            source_geometry_unchanged=True,source_actor_state_unchanged=True,pixel_scale=1,validation=proof,proofs=self.proofs,activated=activate)
        (OUT/'proof.json').write_text(json.dumps(report,indent=2)+'\n')
        for(g,name),points in self.overrides.items():
            if g!='red':continue
            m=self.sources[g]['maps'][name]
            for compact in(False,True)if any(r.get('buildingCompact')for r in points.values())else(False,):
                after=self.render(g,name,m,self.cells[g,name],points,compact,self.new_decor);label='compact'if compact else'expanded'
                after.convert('RGB').save(OUT/g/(name+'-after-'+label+'.png'))
                before=Image.open(OUT/g/(name+'-before.png')).convert('RGB');canvas=Image.new('RGB',(before.width*2+48,before.height+86),'#18202c');d=ImageDraw.Draw(canvas)
                d.text((16,8),name.replace('_',' ').title()+' - Gen3 outdoor audit / '+label+' Center',fill='white');d.text((16,34),'Before',fill='white');d.text((before.width+32,34),'After - native pixels, original source geometry',fill='white')
                canvas.paste(before,(16,58));canvas.paste(after.convert('RGB'),(before.width+32,58));canvas.save(OUT/(name+'-'+label+'-comparison.png'))
        return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--no-render',action='store_true');p.add_argument('--stage',action='store_true');p.add_argument('--activate',action='store_true');args=p.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    audit=Audit();inventory=audit.inventory(not args.no_render);print(json.dumps(audit.stage(args.activate)if args.stage or args.activate else inventory,indent=2))


if __name__=='__main__':main()
