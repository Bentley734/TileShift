"""Direct native Gen3 counterparts for Johto traditional and player homes."""
import copy
import gen2_extended_review as e
from johto_family_review import FamilyReview,ROOT
from native_room_parts import RoomParts
from johto_remaining_review import artwork
f=FamilyReview('domestic',{'TILESET_TRADITIONAL_HOUSE','TILESET_PLAYERS_HOUSE','TILESET_PLAYERS_ROOM'})
unique_objects={('DANCE_THEATER',x,y)for x in(5,6)for y in(6,7)}
unique_objects|={('KURTS_HOUSE',x,y)for x in range(12,16)for y in(1,2)}
unique_objects|={('KURTS_HOUSE',12,y)for y in(3,4,5)}
f.overrides={(game,name,x,y)for game in('gold','silver','crystal')for name,x,y in unique_objects}
house=RoomParts(f.imp,'firered','FR_PLAYERS_HOUSE_1F');bedroom=RoomParts(f.imp,'firered','FR_PLAYERS_HOUSE_2F');dojo=RoomParts(f.imp,'firered','FR_SAFFRON_CITY_DOJO');may=RoomParts(f.imp,'emerald','EM_LITTLEROOT_TOWN_MAYS_HOUSE_1F');center=RoomParts(f.imp,'firered','FR_VIRIDIAN_CITY_POKEMON_CENTER_1F')
for r in f.active:
 if r['game']=='red' and r['role'].startswith('household_'):f.templates.setdefault(r['role'],r)
floor=house.ref(1);wall=house.ref(40);wood=dojo.ref(704);mat=dojo.ref(715)
def native(ref,role):return f.native(ref,'johto_domestic_'+role)
def shared(role,base=floor):return f.template(role,base)
def object_tile(room,sx,sy,base,role):return f.composite(base,room.rect(sx,sy,16,16),'johto_domestic_'+role)
def at(c,x,y,m,data,dx):
 xx=x+dx
 if not 0<=xx<m['width']*2:return None
 return tuple(e.cell_info(f.cache,c['game'],data,m['tileset'],m['blocks'][y//2*m['width']+xx//2],y%2*2+xx%2)['tiles'])
def below(c,x,y,m,data):
 if y+1>=m['height']*2:return None
 return tuple(e.cell_info(f.cache,c['game'],data,m['tileset'],m['blocks'][(y+1)//2*m['width']+x//2],(y+1)%2*2+x%2)['tiles'])
def rug(c,x,y,m,data,base):return shared('household_rug_right'if at(c,x,y,m,data,-1)==tuple(c['tiles'])else'household_rug_left',base)
def crop(art,sx,sy,w,h,x,y):
 if art['kind']=='native':return[{'donor':art['donor'],'srcX':sx,'srcY':sy,'w':w,'h':h,'x':x,'y':y}]
 assert art['kind']=='native_composite',art['kind']
 out=[{'donor':art['base'],'srcX':sx,'srcY':sy,'w':w,'h':h,'x':x,'y':y}]
 for p in art['parts']:
  px,py=p.get('x',0),p.get('y',0);pw,ph=p.get('w',16),p.get('h',16);ix,iy=max(px,sx),max(py,sy);ex,ey=min(px+pw,sx+w),min(py+ph,sy+h)
  if ex>ix and ey>iy:
   z=copy.deepcopy(p);z.update(srcX=p.get('srcX',0)+ix-px,srcY=p.get('srcY',0)+iy-py,w=ex-ix,h=ey-iy,x=x+ix-sx,y=y+iy-sy);out.append(z)
 return out
tables=[shared(r)for r in('household_table_nw','household_table_ne','household_table_sw','household_table_se')]
# Native tabletop caps, repeating surfaces and legs remain distinct modules.
table_glyph={35:(0,0,0),34:(0,8,0),36:(1,8,0),66:(0,0,8),21:(0,8,8),67:(1,8,8),51:(2,0,0),50:(2,8,0),52:(3,8,0),28:(2,0,8),64:(2,8,8),29:(3,8,8)}
def table(raw,base=floor,extra={}):
 parts=[]
 for q,t in enumerate(raw):
  x,y=q%2*8,q//2*8
  if t in table_glyph:
   n,sx,sy=table_glyph[t];parts+=crop(tables[n],sx,sy,8,8,x,y)
  elif t in extra:parts+=extra[t](x,y)
  elif t!=1:return None
 return f.composite(base,parts,'johto_domestic_complete_modular_table')
def book(q,base):return shared('johto_house_bookcase_'+str(q),base)
def narrow_book(q,base):
 parts=crop(book(q*2,base),0,0,8,16,0,0)+crop(book(q*2+1,base),8,0,8,16,8,0)
 return f.composite(base,parts,'johto_domestic_complete_single_bay_bookcase_'+str(q))
def stairs(up,base):return f.original('assets/original/interior-stairs/'+('up'if up else'down')+'.png',base,'johto_domestic_stairs_'+('up'if up else'down'))
def low_table(right,base):
 sx=176+16*int(right)
 return f.composite(base,center.rect(sx,96,16,8)+center.rect(sx,120,16,8,0,8),'johto_domestic_complete_low_table_'+str(int(right)))
def trad(c,x,y,name,m,data):
 raw=tuple(c['tiles']);col=c['collision']
 if raw==(1,1,1,1):return native(wood,'wood_floor')
 if raw==(17,17,17,17):
  if below(c,x,y,m,data)==(10,11,26,27):return f.original('assets/original/interior-radio/cell-0.png',wall,'johto_domestic_radio_head')
  return native(dojo.ref(705),'traditional_lattice_wall')
 if raw in((68,69,84,85),(69,70,85,86),(81,38,85,86),(37,81,84,85),(37,38,85,86)):return native(mat,'tatami_mat')
 if raw in((16,16,1,1),(16,16,14,14),(16,16,14,1),(16,16,1,14)):return native(dojo.ref(723),'tatami_lower_border')
 if raw==(2,3,18,19):return shared('johto_house_chair_left',mat)
 if raw in((4,4,20,20),(4,4,54,54),(54,54,20,20)):return rug(c,x,y,m,data,wood)
 if raw==(80,80,80,80):return native(dojo.ref(731)if col==163 else wood,'stage_step'if col==163 else'stage_floor')
 if raw in((80,80,15,15),(80,80,95,95)):return native(dojo.ref(728),'stage_front')
 if raw==(78,79,94,94):return native(dojo.ref(711),'stage_screen')
 if raw==(64,64,65,65):return shared('azalea_metal_fence',wood)
 if raw in((17,17,35,36),(35,36,41,42),(35,36,30,31),(35,36,62,63)):return narrow_book(0,wall)
 if raw in((62,63,24,25),(46,47,24,25),(8,9,82,83),(57,58,82,83)):return narrow_book(1,mat)
 if raw==(10,11,26,27):return f.original('assets/original/interior-radio/cell-1.png',mat,'johto_domestic_radio')
 if raw in((6,7,22,23),(7,32,23,48)):return book(0 if raw[0]==6 else 1,wall)
 if raw in((33,39,49,55),(39,40,55,56)):return book(2 if raw[0]==33 else 3,mat)
 if raw in((71,72,87,88),(73,74,89,90)):
  art=shared('johto_complete_native_region_map',wall);parts=crop(art,0 if raw[0]==71 else 8,0,8,16,8 if raw[0]==71 else 0,0)
  return f.composite(wall,parts,'johto_domestic_complete_kurt_wall_map')
 if raw==(76,77,92,93):return stairs(True,mat)
 if raw in((43,44,59,60),(45,75,61,91)):
  return low_table(raw[0]==45,mat)
 # Small workshop apricorns and the portable tool box use complete native
 # workshop containers, retaining every original interaction coordinate.
 extras={12:lambda xx,yy:dojo.rect(6*16,3*16,8,8,xx,yy),13:lambda xx,yy:dojo.rect(6*16+8,3*16,8,8,xx,yy),7:lambda xx,yy:house.rect(4*16,5*16,8,8,xx,yy),81:lambda xx,yy:crop(native(mat,'mat'),0,0,8,8,xx,yy),38:lambda xx,yy:crop(native(mat,'mat'),8,0,8,8,xx,yy)}
 if set(raw)<=set(table_glyph)|set(extras)|{1}:return table(raw,mat,extras)
 return None
def modern(c,x,y,name,m,data):
 raw=tuple(c['tiles']);room=m['tileset']=='TILESET_PLAYERS_ROOM';col=c['collision']
 if raw in((17,17,17,17),(2,2,2,2)):
  if below(c,x,y,m,data)==(66,67,82,83):return f.original('assets/original/interior-radio/cell-0.png',wall,'johto_domestic_radio_head')
  return native(wall,'full_wall')
 if raw in((2,3,18,19),):return shared('johto_house_chair_left',floor)
 if raw==(4,4,20,20):return rug(c,x,y,m,data,floor)
 if raw in((17,17,6,7),(2,2,59,60)):return shared('johto_house_complete_tv_head',wall)
 if raw in((22,23,8,9),(75,76,91,92)):return shared('johto_house_complete_tv_base',floor)
 if raw in((17,17,32,33),(2,2,11,12)):return shared('johto_complete_pc_0',wall)
 if raw in((48,49,12,13),(27,28,43,44)):return shared('johto_complete_pc_1',floor)
 if raw==(66,67,82,83):return f.original('assets/original/interior-radio/cell-1.png',floor,'johto_domestic_radio')
 if raw in((14,15,30,31),(14,15,46,47),(5,6,21,22)):return narrow_book(0,wall)
 if raw in((46,47,24,25),(8,9,58,59),(37,38,53,54)):return narrow_book(1,floor)
 if raw==(14,15,58,59):return object_tile(house,3*16,1*16,wall,'native_cupboard')
 if raw==(44,45,17,17):return shared('johto_house_complete_window',wall)
 if raw in((76,77,92,93),(64,65,80,81)):return stairs(True,floor)
 if raw==(80,81,82,83):return object_tile(house,1*16,1*16,floor,'kitchen_sink')
 if raw==(67,69,24,25):return object_tile(house,2*16,1*16,floor,'kitchen_stove')
 if raw in((17,17,10,11),(26,27,42,43)):
  return object_tile(may,10*16,16 if raw[0]==17 else 32,wall if raw[0]==17 else floor,'complete_refrigerator')
 if raw in((51,50,17,17),(50,52,17,17)):return native(wall,'kitchen_wall')
 if raw in((37,53,37,53),(37,53,51,52)):return native(dojo.ref(709),'interior_partition')
 if raw in((48,49,1,1),(49,50,1,1)):return native(floor,'chair_foot_floor')
 if raw in((16,17,32,33),(17,18,33,34)):
  return low_table(raw[0]==17,floor)
 raw=tuple({37:66,53:67}.get(t,t)for t in raw)
 if set(raw)<=set(table_glyph)|{1}:return table(raw)
 return None
def handle(c,x,y,name,m,data):
 if(name,x,y)in unique_objects:
  wood_colors=[[222,214,140],[181,173,99],[115,106,66],[49,57,57]]
  mat_colors=[[214,255,197],[165,230,148],[148,214,165],[108,173,123]]
  steel_colors=[[238,244,252],[174,188,209],[103,121,145],[43,56,77]]
  return{'kind':'source_palette','sourceColors':[mat_colors if a.get('palette')==3 else steel_colors if a.get('palette')==1 else wood_colors for a in c['attributes']],'role':'johto_domestic_unique_teapot_or_apricorn_workbench_gen3_palette'}
 return trad(c,x,y,name,m,data)if m['tileset']=='TILESET_TRADITIONAL_HOUSE'else modern(c,x,y,name,m,data)
f.run(handle,('DANCE_THEATER','KURTS_HOUSE','ECRUTEAK_ITEMFINDER_HOUSE','MAHOGANY_MART_1F','ELMS_HOUSE','PLAYERS_HOUSE_1F','PLAYERS_HOUSE_2F'),'Direct existing native Gen3 domestic counterparts reviewed in original layouts: complete cupboards, bookcases, television, computer, kitchen appliances, floor cushions, tables, tatami edges, stage and stairs. Furniture is composed from complete native caps and repeating surface modules at original pixel scale. Original collision, story interactions, stairs, hidden Rocket entrance and room decoration scripts stay unchanged.')
