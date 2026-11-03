"""Source-scoped Gen1 seating and domestic/commercial background review."""
import argparse
import copy
import json
import os
import re
from collections import Counter,defaultdict,deque
from types import SimpleNamespace
from pathlib import Path

from PIL import Image,ImageDraw,ImageFont
import catalog,preview
from gen1_family_review import source,cell_info,source_image,GAMES
from interior_review import Imports
from johto_remaining_review import artwork
from native_room_parts import RoomParts
from center_mart_overhang_review import write_rows
import gen2_extended_review as validation

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'.work/tileshift-v0310-seating-domestic'
MODULE='mappings/gen1_seating_domestic_audit.lua'
SETS={'HOUSE','REDS_HOUSE_1','REDS_HOUSE_2','MART','LOBBY','POKECENTER','GATE','FOREST_GATE','CLUB','BEACH_HOUSE'}
EXTRA={'WARDENS_HOUSE','FUCHSIA_MEETING_ROOM','SAFARI_ZONE_SECRET_HOUSE','CERULEAN_BADGE_HOUSE',
       'FUCHSIA_GOOD_ROD_HOUSE','POKEMON_FAN_CLUB','VIRIDIAN_SCHOOL_HOUSE','CELADON_CHIEF_HOUSE'}
EXCLUDE={'BILLS_HOUSE','SILPH_CO_11F','ROCKET_HIDEOUT_ELEVATOR','SILPH_CO_ELEVATOR'}
ASSETS=ROOT/'assets/third_party/gen1-seating-domestic'
NATIVE_FLOORS=(('FR_RIVALS_HOUSE',(1,)),('FR_PLAYERS_HOUSE_1F',(1,)),
 ('FR_VIRIDIAN_CITY_POKEMON_CENTER_1F',(641,)),('FR_VIRIDIAN_CITY_POKEMON_CENTER_2F',(641,)),
 ('FR_VIRIDIAN_CITY_MART',(641,)),('FR_CELADON_CITY_GAME_CORNER',(657,658)),
 ('FR_CELADON_CITY_RESTAURANT',(709,719,724)),('FR_CELADON_CITY_DEPARTMENT_STORE_1F',(704,)),
 ('FR_CELADON_CITY_DEPARTMENT_STORE_ROOF',(696,)),('FR_VERMILION_CITY_POKEMON_FAN_CLUB',(648,)),
 ('FR_ROUTE_11_EAST_ENTRANCE_1F',(641,642,643)),('FR_ROUTE_11_EAST_ENTRANCE_2F',(641,642)),
 ('FR_CELADON_CITY_CONDOMINIUMS_1F',(641,)),('FR_SILPH_CO_1F',(820,)))

def digest(value):return catalog.sha(json.dumps(value,sort_keys=True,separators=(',',':')).encode())
def seat(row):return any(word in row['role']for word in('chair','stool','seat','cushion','sofa'))
def unlabelled_seat(name,raw):return(name in('COLOSSEUM','TRADE_CENTER')and tuple(raw)==(42,43,38,39))or(name=='SUMMER_BEACH_HOUSE'and tuple(raw)==(2,3,18,19))
def scoped(name,m):return name not in EXCLUDE and(m['tileset']in SETS or name in EXTRA or name.startswith('CELADON_MANSION_'))

class Audit:
    def __init__(self):
        self.cache=Path(os.environ['APPDATA'])/'pokemon-love2d';self.imp=Imports(self.cache,ROOT.parent/'.work/tileshift-catalog');self.packed=self.imp.packed
        self.modules=list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(ROOT/'main.lua').read_text())))
        self.rows={};self.all=[];self.family=defaultdict(list);self.sources={g:source(self.cache,g)for g in GAMES};self.images={};self.cells={};self.maps=[];self.objects={}
        self.native_rooms={};self.source_masks={};self.floor_refs=set();self.mask_proofs=[];self.changes=[];self.asset_records={}
        for name in self.modules:
            if name==MODULE:continue
            batch=catalog.plain(catalog.LUA.execute((ROOT/name).read_text()))
            if batch=={}:batch=[]
            self.rows[name]=batch
            for index,row in enumerate(batch,1):
                self.all.append(row)
                if row.get('game')in GAMES and row.get('style')=='gen3':self.family[row['game'],row['tileset']].append((row,name,index))

    def grid(self,g,name,m):
        global_rows={};map_rows={};positions={}
        for row,module,index in self.family[g,m['tileset']]:
            if row.get('map')not in(None,name):continue
            key=row['id'],row['quadrant']
            if row.get('x')is not None:positions[key+(row['x'],row['y'])]=(row,module,index)
            elif row.get('map')is None:global_rows[key]=(row,module,index)
            else:map_rows[key]=(row,module,index)
        cells={}
        for index,bid in enumerate(m['blocks']):
            for q in range(4):
                x,y=index%m['width']*2+q%2,index//m['width']*2+q//2
                selected=positions.get((bid,q,x,y),map_rows.get((bid,q),global_rows.get((bid,q))))
                if selected:cells[x,y]=selected
        return cells

    def image(self,row):
        art=artwork(row)
        if row.get('kind')=='source_palette':art.update({k:row[k]for k in('game','tileset','id','quadrant','sourceHash','sourceFiles','sourceColors')if k in row})
        key=digest(art)
        if key not in self.images:self.images[key]=preview.replacement_image(self.cache,row,self.packed,ROOT)
        return self.images[key]

    def inventory(self):
        objects={};seats=[];map_hashes={};missing=[]
        for g in GAMES:
            data=self.sources[g]
            for name,m in sorted(data['maps'].items()):
                if not isinstance(m,dict)or not m.get('tileset')or not m.get('width')or not m.get('height'):continue
                cells=self.grid(g,name,m)
                owned=scoped(name,m)
                if not owned and not any(seat(r)for r,_,_ in cells.values()):continue
                self.cells[g,name]=cells
                canvas=Image.new('RGBA',(m['width']*32,m['height']*32));roles=Counter();bases=Counter();floor_roles=Counter()
                for y in range(m['height']*2):
                    for x in range(m['width']*2):
                        if(x,y)not in cells:missing.append(dict(game=g,map=name,position=[x,y]));continue
                        r,module,index=cells[x,y];roles[r['role']]+=1
                        if r.get('base'):bases[json.dumps(r['base'],sort_keys=True)]+=1
                        if any(t in r['role']for t in('floor','ground')):floor_roles[r['role']]+=1
                        im=self.image(r);canvas.alpha_composite(im,(x*16,y*16))
                        c=cell_info(self.cache,g,data,m['tileset'],r['id'],r['quadrant'])
                        identity=digest(dict(art=artwork(r),role=r['role'],raw=c['tiles'],sourceHash=c['sourceHash']))
                        if identity not in objects:
                            objects[identity]=dict(role=r['role'],raw=c['tiles'],sourceHash=c['sourceHash'],art=artwork(r),behavior=c['behavior'],contexts=[],image_hash=catalog.sha(im.tobytes()))
                            self.objects[identity]=(r,im)
                        context=dict(game=g,map=name,x=x,y=y,module=module,index=index,positioned=r.get('x')is not None)
                        objects[identity]['contexts'].append(context)
                        if seat(r)or unlabelled_seat(name,c['tiles']):
                            neighbors=[]
                            for direction,dx,dy in(('east',1,0),('west',-1,0),('north',0,-1),('south',0,1)):
                                other=cells.get((x+dx,y+dy))
                                if other:neighbors.append(dict(direction=direction,position=[x+dx,y+dy],role=other[0]['role']))
                            seats.append(dict(**context,row=copy.deepcopy(r),neighbors=neighbors,raw=c['tiles'],behavior=c['behavior'],
                                actors=[obj for obj in m.get('objects',[])if obj.get('x')==x and obj.get('y')==y]))
                output=OUT/g;output.mkdir(exist_ok=True,parents=True);canvas.convert('RGB').save(output/(name+'-before.png'))
                rgba=catalog.sha(canvas.tobytes());same=map_hashes.get(rgba)
                if same is None:map_hashes[rgba]=[g,name]
                self.maps.append(dict(game=g,map=name,tileset=m['tileset'],owned_room=owned,cells=m['width']*m['height']*4,roles=dict(roles),
                    floor_roles=dict(floor_roles),bases=[dict(ref=json.loads(k),cells=v)for k,v in bases.items()],rgba_sha256=rgba,same_artwork_as=same,
                    original_objects=m.get('objects',[])))
        (OUT/'map-inventory.json').write_text(json.dumps(self.maps,indent=2)+'\n')
        (OUT/'object-inventory.json').write_text(json.dumps(objects,indent=2)+'\n')
        (OUT/'seat-inventory.json').write_text(json.dumps(seats,indent=2)+'\n')
        (OUT/'missing-cells.json').write_text(json.dumps(missing,indent=2)+'\n')
        self.object_inventory=objects;self.seats=seats
        summary=dict(maps=len(self.maps),owned_room_maps=sum(r['owned_room']for r in self.maps),seat_cells=len(seats),unique_room_art=len(map_hashes),
            source_cells=sum(r['cells']for r in self.maps),missing=len(missing),roles=dict(Counter(r['row']['role']for r in seats)),
            scope=[dict(game=r['game'],map=r['map'],tileset=r['tileset'])for r in self.maps if r['owned_room']])
        (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
        return map_hashes

    def contacts(self,unique):
        font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',13);w,h=410,370
        for start in range(0,len(unique),12):
            canvas=Image.new('RGB',(w*3,h*4),'#18202c');d=ImageDraw.Draw(canvas)
            for i,(g,name)in enumerate(list(unique.values())[start:start+12]):
                im=Image.open(OUT/g/(name+'-before.png'));x,y=i%3*w,i//3*h
                scale=max(1,min(2,(w-12)//im.width,(h-38)//im.height));show=im.resize((im.width*scale,im.height*scale),Image.Resampling.NEAREST)
                if show.width>w-12 or show.height>h-38:show.thumbnail((w-12,h-38),Image.Resampling.NEAREST)
                canvas.paste(show,(x+6,y+32));d.text((x+6,y+5),g+' / '+name,fill='white',font=font)
            canvas.save(OUT/f'rooms-contact-{start//12+1:02}.png')

    def room(self,name):
        if name not in self.native_rooms:self.native_rooms[name]=RoomParts(self.imp,'firered',name)
        return self.native_rooms[name]

    def layer(self,room,mid,base,role):
        ref=room.ref(mid);rec=self.imp.cell_index('firered')[room.pair,mid]
        return dict(kind='native_composite',base=copy.deepcopy(base),parts=[dict(donor=ref,w=16,h=16,layers=['mid'],layerHashes={'mid':rec['layer_sha256']['mid']})],role=role)

    def asset(self,im,base,role,evidence):
        assert im.size==(16,16)and set(im.getchannel('A').get_flattened_data())<={0,255}
        ASSETS.mkdir(exist_ok=True,parents=True);path=ASSETS/('foreground-'+catalog.sha(im.tobytes())[:24]+'.png')
        if not path.exists():im.save(path)
        relative=path.relative_to(ROOT).as_posix();sha=catalog.sha(path.read_bytes())
        record=self.asset_records.setdefault(relative,dict(path=relative,sha256=sha,width=16,height=16,rgba_sha256=catalog.sha(im.tobytes()),pixel_scale=1,contexts=[]))
        if evidence not in record['contexts']:record['contexts'].append(evidence)
        art=dict(kind='third_party',asset=relative,assetFileHash=sha,role=role,
            credit='Game Freak native pixel art from locally imported games; complete object pixels retained at original size, exterior room-floor pixels omitted.',sourceUrl='https://github.com/pret/pokered')
        if base is not None:art['base']=copy.deepcopy(base)
        return art

    def floor(self,cells,x,y):
        floors=[]
        for(fx,fy),(r,_,_)in cells.items():
            if not any(t in r['role']for t in('floor','carpet','paving'))or r.get('parts')or not r.get('donor'):continue
            ref=copy.deepcopy(r['donor'])
            if r['role']=='gen1_gate_public_checker_floor':ref=self.room('FR_ROUTE_11_EAST_ENTRANCE_2F').ref(641)
            floors.append((abs(fx-x)+abs(fy-y),fy,fx,ref))
        return min(floors,key=lambda t:t[:3])[3]if floors else None

    def native_masks(self):
        from gen2_domestic_floor_audit import Audit as Domestic
        import gen2_domestic_floor_audit as domestic
        old=domestic.SOURCE_ROOMS;domestic.SOURCE_ROOMS=tuple(('firered',name,mids)for name,mids in NATIVE_FLOORS)
        try:Domestic.masks(self)
        finally:domestic.SOURCE_ROOMS=old

    def clean_native(self,row,base):
        if not base or not(row.get('parts')or row.get('donor')):return None
        if any(t in row['role']for t in('wall','window','floor','border','stair','stage','roof','mat','screen','glazing','door','threshold','void','portrait','poster','call_panel')):return None
        before=self.image(row);fg=Image.new('RGBA',(16,16));removed=[]
        for part in row.get('parts')or[dict(donor=row['donor'],w=16,h=16)]:
            ref=part['donor'];tag=ref['game'],ref['tileset'],ref['id'];px,py=part.get('x',0),part.get('y',0);w,h=part['w'],part['h']
            if not part.get('layers')and tag in self.floor_refs:
                fg.paste((0,0,0,0),(px,py,px+w,py+h));removed.append(dict(empty_floor_part=part));continue
            full=preview.native_donor(self.cache,ref,self.packed,part.get('layers'),part.get('layerHashes'));sx,sy=part.get('srcX',0),part.get('srcY',0)
            patch=full.crop((sx,sy,sx+w,sy+h));mask=self.source_masks.get(tag,set())if not part.get('layers')else set();omitted=[]
            for yy in range(h):
                for xx in range(w):
                    if(sx+xx,sy+yy)in mask and patch.getpixel((xx,yy))[3]:patch.putpixel((xx,yy),(0,0,0,0));omitted.append([sx+xx,sy+yy])
            if omitted:removed.append(dict(part=part,connected_native_floor_pixels=omitted))
            fg.alpha_composite(patch,(px,py))
        if not fg.getbbox():return None
        # Copied opaque floor strips sometimes hide an earlier fragment. Their
        # omission must expose the target floor, never uncover that hidden art.
        occluded=[]
        for yy in range(16):
            for xx in range(16):
                if fg.getpixel((xx,yy))[3]and fg.getpixel((xx,yy))!=before.getpixel((xx,yy)):
                    fg.putpixel((xx,yy),(0,0,0,0));occluded.append([xx,yy])
        if occluded:removed.append(dict(preserve_old_floor_occlusion=occluded))
        after=Image.alpha_composite(preview.native_donor(self.cache,base,self.packed),fg)
        if after.tobytes()==before.tobytes():return None
        for a,b in zip(fg.get_flattened_data(),before.get_flattened_data()):
            if a[3]:assert a==b,('foreground changed',row['role'])
        if not removed and row.get('base')==base:return None
        proof=dict(native_floor_parts_removed=removed,retained_object_pixels=sum(p[3]>0 for p in fg.get_flattened_data()),original_artwork=artwork(row),target_floor=base)
        return self.asset(fg,base,'gen1_domestic_complete_object_over_actual_floor',proof),proof

    def source_exterior(self,g,name,m,cells):
        canvas=Image.new('RGBA',(m['width']*32,m['height']*32));floorcells=[];allowed=set()
        for(x,y),(r,_,_)in cells.items():
            c=cell_info(self.cache,g,self.sources[g],m['tileset'],r['id'],r['quadrant']);im=source_image(self.cache,g,self.sources[g],c);canvas.paste(im,(x*16,y*16))
            if any(t in r['role']for t in('floor','carpet','paving'))and not r.get('parts')and r.get('donor'):
                # A legacy floor recipe also matched the operator's shadow
                # corner (57,11,60,27). Never seed through object/outline colors.
                if any(p[0]<170 for p in im.get_flattened_data()):continue
                floorcells.append((x,y))
                for yy in range(16):
                    for xx in range(16):allowed.add(im.getpixel((xx,yy)))
        outside=set();queue=deque()
        for x,y in floorcells:
            for yy in range(y*16,y*16+16):
                for xx in range(x*16,x*16+16):outside.add((xx,yy));queue.append((xx,yy))
        while queue:
            x,y=queue.popleft()
            for p in((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if 0<=p[0]<canvas.width and 0<=p[1]<canvas.height and p not in outside and canvas.getpixel(p)in allowed:outside.add(p);queue.append(p)
        return outside

    def direction(self,name,x,y,row):
        if name=='CELADON_DINER':return 'east'if x==5 else 'north'if y==7 else 'south'
        if name=='CELADON_MART_ROOF':return 'east'if x in(3,7)else 'west'
        if name=='CELADON_MART_1F':return 'west'
        if name in('CELADON_MANSION_ROOF_HOUSE','VIRIDIAN_SCHOOL_HOUSE'):return 'north'
        if name=='CINNABAR_LAB_TRADE_ROOM':return 'south'if y==2 else 'north'
        if name=='FUCHSIA_MEETING_ROOM':return 'south'
        if name=='MUSEUM_1F':return 'south'
        return None

    def template(self,role,base):
        row=next(r for r in self.all if r.get('game')=='red'and r['role']==role)
        result=artwork(row);result.update(role=role,base=copy.deepcopy(base));return result

    def extra_native(self,g,name,m,cells,x,y,old,c,base):
        raw=tuple(c['tiles'])
        if name in('COLOSSEUM','TRADE_CENTER')and raw==(42,43,38,39):
            floor_row=cells[4,5][0];floor_source=cell_info(self.cache,g,self.sources[g],m['tileset'],floor_row['id'],floor_row['quadrant']);assert floor_source['tiles']==[15]*4
            floor=self.image(floor_row);assert len(set(floor.get_flattened_data()))==1
            room=self.room('FR_SILPH_CO_1F');ref=room.ref(786);lh=self.imp.cell_index('firered')[room.pair,786]['layer_sha256']['mid'];fg=preview.native_donor(self.cache,ref,self.packed,['mid'],{'mid':lh});full=Image.alpha_composite(floor,fg)
            proof=dict(reason='Original round backless link-room stool uses a complete native Gen3 round studio stool; the existing plain Gen3-colored court floor is retained.',native_donor=ref,native_layer_hash=lh,native_foreground_pixels=sum(p[3]>0 for p in fg.get_flattened_data()),court_floor_source=[4,5],court_floor_sourceHash=floor_source['sourceHash'],court_floor_rgba_sha256=catalog.sha(floor.tobytes()),pixel_scale=1)
            return self.asset(full,None,'gen1_link_court_complete_native_round_stool',proof),proof
        if name=='CELADON_MANSION_ROOF'and old['role']=='gen1_mansion_intact_rooftop_shack'and raw==(1,)*4:
            return dict(kind='native',donor=self.room('FR_CELADON_CITY_DEPARTMENT_STORE_ROOF').ref(648),role='gen1_rooftop_complete_native_paving'),dict(reason='Pure original rooftop paving was inside an overly broad shack rectangle; restore the full native paving tile.')
        if name in('FUCHSIA_MEETING_ROOM','SAFARI_ZONE_SECRET_HOUSE','WARDENS_HOUSE')and old['role']=='gen1_lab_native_floor'and raw==(39,39,55,55):
            which='left'if tuple(cell_info(self.cache,g,self.sources[g],m['tileset'],cells[x-1,y][0]['id'],cells[x-1,y][0]['quadrant'])['tiles'])!=raw else 'right'
            art=self.template('household_rug_'+which,base);art['role']='gen1_complete_native_entrance_mat_'+which
            return art,dict(reason='Original walkable entrance mat is not plain floor; preserve its original two-cell footprint with the existing complete native Gen3 entry rug.')
        if name=='SUMMER_BEACH_HOUSE'and old['role']=='gen1_special_original_complete_surf_house_details':
            if raw==(2,3,18,19):return self.layer(self.room('FR_VIRIDIAN_CITY_POKEMON_CENTER_2F'),757,base,'gen1_beach_complete_native_backless_padded_seat'),dict(reason='Original square padded seat has no backrest; use the complete native Gen3 padded stool over the original wood floor.')
            if x in(9,10)and y in(2,3,4,5):
                q=(y%2)*2+x-9;art=self.template('gen1_commercial_whole_native_cafe_table_'+str(q),base);art['role']='gen1_beach_complete_native_dining_table_'+str(q)
                cleaned=self.clean_native(art,base)
                if cleaned:art,_=cleaned;art['role']='gen1_beach_complete_native_dining_table_'+str(q)
                return art,dict(reason='Complete native32x32 dining table with plate replaces the original32x32 dining table; no cropping, scaling, movement or gameplay change.')
        return None

    def source_floor_object(self,name,x,y,role):
        if any(t in role for t in('table','sofa','bicycle','compact_furniture','collection_display')):return True
        if role in('gen1_original_complete_handheld_and_cord','gen1_original_small_scattered_house_objects','gen1_original_cable_club_terminal_and_operator','gen1_mansion_original_cabinet_ornament','gen1_original_compact_fossil_instrument_bay'):return True
        if name=='POKEMON_FAN_CLUB'and y>=1 and role=='gen1_special_original_fan_club_wall_or_furniture_module':return True
        if name in('CERULEAN_BADGE_HOUSE','FUCHSIA_GOOD_ROD_HOUSE')and role=='gen1_ship_complete_compact_original_furniture_and_railings'and y in(3,4):return True
        return False

    def border_rows(self):
        rows=[];roof=self.room('FR_CELADON_CITY_DEPARTMENT_STORE_ROOF')
        for g in GAMES:
            for name,block,raw in(('CELADON_MANSION_ROOF',9,(32,)*4),('CELADON_MART_ROOF',66,(79,)*4)):
                m=self.sources[g]['maps'][name]
                for q in range(4):
                    c=cell_info(self.cache,g,self.sources[g],m['tileset'],block,q);assert tuple(c['tiles'])==raw
                    row=dict(game=g,style='gen3',map=name,tileset=m['tileset'],id=block,quadrant=q,sourceCells={},sourceHash=c['sourceHash'],sourceFiles=copy.deepcopy(self.sources[g]['fingerprints'][m['tileset']]),sourceBehavior=copy.deepcopy(c['behavior']),status='reviewed',kind='native',donor=roof.ref(855),role='gen1_rooftop_native_sky_border',evidence='Original uniform nonblack out-of-map rooftop background uses the complete existing native Gen3 rooftop sky; actual positioned map cells keep precedence.')
                    row['compositionPixelHash']=catalog.sha(self.image(row).tobytes());rows.append(row)
        return rows

    def stage(self,validate=False,activate=False):
        self.native_masks();new=[];removals=[];fixed=Counter();chair_audit=[];evidence=[]
        south=self.room('FR_CELADON_CITY_RESTAURANT');gate=self.room('FR_ROUTE_11_EAST_ENTRANCE_2F')
        for entry in self.maps:
            g,name=entry['game'],entry['map'];m=self.sources[g]['maps'][name];cells=self.cells[g,name];outside=None;after=Image.open(OUT/g/(name+'-before.png')).convert('RGBA')
            for(x,y),(old,module,index)in sorted(cells.items(),key=lambda z:(z[0][1],z[0][0])):
                c=cell_info(self.cache,g,self.sources[g],m['tileset'],old['id'],old['quadrant']);base=self.floor(cells,x,y);art=None;reason=None;proof={};raw=tuple(c['tiles'])
                extra=self.extra_native(g,name,m,cells,x,y,old,c,base)
                if extra:art,proof=extra;reason=proof['reason']
                elif old['role']=='gen1_gate_whole_native_chair'and raw==(32,33,50,51):
                    assert not any(c['behavior']['walkable']);art=dict(kind='native',donor=gate.ref(647),role='gen1_gate_native_boundary_wall_instead_of_misidentified_chair');reason='Source panelled solid boundary wall; native Gen3 gate wall, not seating.'
                elif old['role']=='gen1_gate_public_checker_floor':
                    art=dict(kind='native',donor=gate.ref(641),role='gen1_gate_native_clear_checker_floor');reason='Use complete native clear checker floor rather than repeating the left-wall shadow.'
                elif old['role']=='gen1_gate_whole_native_chair':
                    assert raw==(2,3,18,19);art=self.layer(south,741,base,'gen1_gate_complete_native_south_waiting_chair');reason='Original standalone waiting chair has backrest above seat; complete native south-facing chair.'
                elif m['tileset']=='SHIP'and old['role']=='household_chair_left':
                    assert raw==(7,8,23,24);art=self.layer(self.room('FR_VIRIDIAN_CITY_POKEMON_CENTER_2F'),765,base,'gen1_native_complete_backless_padded_stool');reason='Original SHIP object is a round backless stool, not a directional chair; use the complete native padded stool.'
                elif seat(old)and 'tipped'not in old['role']and self.direction(name,x,y,old):
                    direction=self.direction(name,x,y,old);reason='Whole native chair faces the adjacent table/counter; source positions and gameplay unchanged.'
                    if direction=='north':
                        path=ROOT/'assets/third_party/native-kanto-chairs/north-blue.png';art=dict(kind='third_party',asset=path.relative_to(ROOT).as_posix(),assetFileHash=catalog.sha(path.read_bytes()),base=base,role='gen1_native_complete_north_chair',credit='Complete native Emerald S.S. Tidal chair in native FireRed chair colors; native-kanto-chairs provenance.',sourceUrl='https://github.com/pret/pokeemerald')
                    else:art=self.layer(south,dict(east=717,west=718,south=741)[direction],base,'gen1_native_complete_'+direction+'_chair')
                    proof=dict(direction=direction,source_position=[x,y],native_pixel_scale=1)
                elif entry['owned_room']and old.get('kind')=='source_palette'and self.source_floor_object(name,x,y,old['role']):
                    if outside is None:outside=self.source_exterior(g,name,m,cells)
                    mask={(xx,yy)for yy in range(16)for xx in range(16)if(x*16+xx,y*16+yy)in outside}
                    if mask and base:
                        fg=self.image(old).copy()
                        for p in mask:fg.putpixel(p,(0,0,0,0))
                        if fg.getbbox():
                            proof=dict(source_original_connected_floor_pixels=[list(p)for p in sorted(mask)],retained_original_geometry_pixels=sum(p[3]>0 for p in fg.get_flattened_data()),original_artwork=artwork(old),target_floor=base)
                            art=self.asset(fg,base,'gen1_original_complete_furniture_over_native_floor',proof);reason='Unique compact original geometry retained in Gen3 colors; only connected original room-floor pixels omitted.'
                elif entry['owned_room']or seat(old):
                    cleaned=self.clean_native(old,base)
                    if cleaned:art,proof=cleaned;reason='Retain exact complete native furniture pixels over the actual room floor, omitting connected donor-floor fragments.'
                if seat(old)or unlabelled_seat(name,c['tiles']):chair_audit.append(dict(game=g,map=name,x=x,y=y,raw=c['tiles'],old_role=old['role'],action=reason or 'Retained: complete source-position seat already matches table/waiting/damaged context.',native_artwork=artwork(art or old)))
                if not art:continue
                r=dict(game=g,style='gen3',map=name,tileset=m['tileset'],id=old['id'],quadrant=old['quadrant'],x=x,y=y,sourceCells=[[x,y]],sourceHash=c['sourceHash'],sourceFiles=copy.deepcopy(self.sources[g]['fingerprints'][m['tileset']]),sourceBehavior=copy.deepcopy(c['behavior']),status='reviewed',evidence=reason)
                r.update(art);im=self.image(r)
                if im.tobytes()==self.image(old).tobytes():continue
                r['compositionPixelHash']=catalog.sha(im.tobytes());new.append(r);after.paste(im,(x*16,y*16));fixed[reason]+=1
                ev=dict(game=g,map=name,x=x,y=y,oldmodule=module,oldindex=index,oldrow_sha256=digest(old),reason=reason,proof=proof);evidence.append(ev)
                if old.get('x')is not None:removals.append(dict(oldmodule=module,oldindex=index,oldrow=copy.deepcopy(old),oldrow_sha256=digest(old),newmodule=MODULE,newrow_index=len(new),newrow=copy.deepcopy(r)))
            after.convert('RGB').save(OUT/g/(name+'-after.png'))
        new.extend(self.border_rows())
        for filename,value in [('candidates.json',new),('replacements.json',removals),('change-proof.json',evidence),('chair-context-audit.json',chair_audit),('native-mask-proof.json',self.mask_proofs)]:
            (OUT/filename).write_bytes((json.dumps(value,indent=2)+'\n').encode())
        ASSETS.mkdir(exist_ok=True,parents=True);(ASSETS/'provenance.json').write_bytes((json.dumps(dict(files=list(self.asset_records.values()),pixel_geometry='Exact 1:1 source/native object pixels; only map-connected exterior background removed.',authoring_tool='tools/gen1_seating_domestic_audit.py'),indent=2)+'\n').encode())
        for stale in ASSETS.glob('foreground-*.png'):
            assert stale.resolve().is_relative_to(ASSETS.resolve())and ASSETS.resolve().is_relative_to(ROOT.resolve())
            if stale.relative_to(ROOT).as_posix()not in self.asset_records:stale.unlink()
        summary=dict(rows=len(new),positioned_old_rows_removed=len(removals),changed_maps=len({(r['game'],r['map'])for r in new}),reasons=dict(fixed),chair_contexts=len(chair_audit),original_positions_and_gameplay_preserved=True,assets=len(self.asset_records))
        if validate:
            result=validation.validate_batch(new,SimpleNamespace(cache=self.cache,engine=ROOT.parent/'.tools/engine-0395',output=OUT),ROOT);summary['validation']=result
            assert result.get('rejected',0)==0,result
        (OUT/'proof.json').write_bytes((json.dumps(summary,indent=2)+'\n').encode());print(json.dumps(summary,indent=2))
        if activate:assert validate;write_rows(ROOT/MODULE,new)

    def extend(self):
        """Append separately reviewed non-keyword details, preserving frozen rows."""
        self.native_masks();previous=preview.read_reviewed(ROOT/MODULE);previous_hash=digest(previous);added=[];evidence=[]
        done={(r['game'],r['map'],r.get('x'),r.get('y'))for r in previous if r.get('x')is not None}
        provenance=json.loads((ASSETS/'provenance.json').read_text());self.asset_records={r['path']:r for r in provenance['files']}
        removals=json.loads((OUT/'replacements.json').read_text())
        for entry in self.maps:
            if not entry['owned_room']:continue
            g,name=entry['game'],entry['map'];m=self.sources[g]['maps'][name];cells=self.cells[g,name];outside=None
            for(x,y),(old,module,index)in sorted(cells.items(),key=lambda z:(z[0][1],z[0][0])):
                if(g,name,x,y)in done:continue
                c=cell_info(self.cache,g,self.sources[g],m['tileset'],old['id'],old['quadrant']);base=self.floor(cells,x,y);art=None;proof={}
                extra=self.extra_native(g,name,m,cells,x,y,old,c,base)
                if extra:art,proof=extra
                elif old.get('kind')=='source_palette'and self.source_floor_object(name,x,y,old['role']):
                    if outside is None:outside=self.source_exterior(g,name,m,cells)
                    mask={(xx,yy)for yy in range(16)for xx in range(16)if(x*16+xx,y*16+yy)in outside}
                    if mask and base:
                        fg=self.image(old).copy()
                        for p in mask:fg.putpixel(p,(0,0,0,0))
                        if fg.getbbox():
                            proof=dict(reason='Preserve every complete outlined source prop pixel in Gen3 colors; replace only its connected original exterior floor with the actual native room floor.',source_original_connected_floor_pixels=[list(p)for p in sorted(mask)],retained_original_geometry_pixels=sum(p[3]>0 for p in fg.get_flattened_data()),original_artwork=artwork(old),target_floor=base)
                            art=self.asset(fg,base,'gen1_complete_original_prop_over_actual_native_floor',proof)
                if not art:continue
                r=dict(game=g,style='gen3',map=name,tileset=m['tileset'],id=old['id'],quadrant=old['quadrant'],x=x,y=y,sourceCells=[[x,y]],sourceHash=c['sourceHash'],sourceFiles=copy.deepcopy(self.sources[g]['fingerprints'][m['tileset']]),sourceBehavior=copy.deepcopy(c['behavior']),status='reviewed',evidence=proof['reason']);r.update(art);im=self.image(r)
                if im.tobytes()==self.image(old).tobytes():continue
                r['compositionPixelHash']=catalog.sha(im.tobytes());added.append(r);evidence.append(dict(game=g,map=name,x=x,y=y,proof=proof,oldmodule=module,oldindex=index,oldrow_sha256=digest(old)))
                if old.get('x')is not None:removals.append(dict(oldmodule=module,oldindex=index,oldrow=copy.deepcopy(old),oldrow_sha256=digest(old),newmodule=MODULE,newrow_index=len(previous)+len(added),newrow=copy.deepcopy(r)))
        proof=validation.validate_batch(added,SimpleNamespace(cache=self.cache,engine=ROOT.parent/'.tools/engine-0395',output=OUT),ROOT)
        final=previous+added;assert digest(final[:len(previous)])==previous_hash
        write_rows(ROOT/MODULE,final)
        for filename,value in [('candidates.json',final),('replacements.json',removals),('nonkeyword-extra-proof.json',dict(validation=proof,preserved_previous_rows=len(previous),previous_rows_sha256=previous_hash,extra_rows=len(added),contexts=evidence))]:
            (OUT/filename).write_bytes((json.dumps(value,indent=2)+'\n').encode())
        provenance['files']=list(self.asset_records.values());(ASSETS/'provenance.json').write_bytes((json.dumps(provenance,indent=2)+'\n').encode())
        summary=json.loads((OUT/'proof.json').read_text());summary.update(rows=len(final),positioned_old_rows_removed=len(removals),changed_maps=len({(r['game'],r['map'])for r in final}),assets=len(self.asset_records),nonkeyword_rows=len(added),nonkeyword_validation=proof)
        (OUT/'proof.json').write_bytes((json.dumps(summary,indent=2)+'\n').encode())
        for g,name in sorted({(r['game'],r['map'])for r in added}):
            m=self.sources[g]['maps'][name];canvas=Image.new('RGBA',(m['width']*32,m['height']*32));cells=self.cells[g,name]
            for(x,y),(r,_,_)in cells.items():canvas.paste(self.image(r),(x*16,y*16))
            for r in final:
                if r['game']==g and r['map']==name and r.get('x')is not None:canvas.paste(self.image(r),(r['x']*16,r['y']*16))
            canvas.convert('RGB').save(OUT/g/(name+'-after.png'))
        print(json.dumps(summary,indent=2))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--contacts',action='store_true');p.add_argument('--stage',action='store_true');p.add_argument('--validate',action='store_true');p.add_argument('--activate',action='store_true');p.add_argument('--extend',action='store_true');a=p.parse_args();OUT.mkdir(exist_ok=True,parents=True)
    audit=Audit();unique=audit.inventory()
    if a.contacts:audit.contacts(unique)
    if a.stage or a.validate or a.activate:audit.stage(a.validate,a.activate)
    if a.extend:audit.extend()

if __name__=='__main__':main()
