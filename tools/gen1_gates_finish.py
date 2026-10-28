"""Native Gen3 gate furniture, observation windows and Underground Path."""
from gen1_family_review import FamilyReview,cell_info
from native_room_parts import RoomParts
import preview
f=FamilyReview('gates',{'GATE','FOREST_GATE','UNDERGROUND'})
gate=RoomParts(f.imp,'firered','FR_ROUTE_11_EAST_ENTRANCE_1F');upper=RoomParts(f.imp,'firered','FR_ROUTE_11_EAST_ENTRANCE_2F');north=RoomParts(f.imp,'firered','FR_ROUTE_5_SOUTH_ENTRANCE');tunnel=RoomParts(f.imp,'firered','FR_UNDERGROUND_PATH_NORTH_SOUTH_TUNNEL')
floor=upper.ref(642)
indigo=RoomParts(f.imp,'firered','FR_INDIGO_PLATEAU_EXTERIOR');width=indigo.layout['width'];at=next(i for i,v in enumerate(indigo.layout['mids'])if v==694 and indigo.layout['mids'][i+width]==671);statue_x=at%width*16;statue_y=at//width*16
statue_bg=set()
for mid in(1,8,9,16,17):statue_bg.update(preview.native_donor(f.cache,indigo.ref(mid),f.packed).get_flattened_data())
statue_outside=indigo.exterior(statue_x,statue_y,16,32,statue_bg)
def statue(top):return f.composite(gate.ref(647)if top else floor,indigo.masked(statue_x,statue_y+(0 if top else 16),list(range(16)),list(range(16)),transparent_pixels=statue_outside),'gen1_gate_complete_native_rhydon_'+('head'if top else'base'))
def native(room,mid,role):return f.native(room.ref(mid),'gen1_gate_'+role)
def shared(role,base=floor):
 r=f.template(role,base);r['role']='gen1_gate_'+role;return r
def same(c,x,y,m,data,dx,raw):
 xx=x+dx
 return 0<=xx<m['width']*2 and tuple(cell_info(f.cache,c['game'],data,m['tileset'],m['blocks'][y//2*m['width']+xx//2],y%2*2+xx%2)['tiles'])==raw
def stairs(c,x,y,m,base):
 warp=next((w for w in m.get('warps',[])if w.get('x')==x and w.get('y')==y),None)
 up=bool(warp and str(warp.get('destMap','')).endswith('2F'))or m['tileset']=='UNDERGROUND'
 return f.original('assets/original/interior-stairs/'+('up'if up else'down')+'.png',base,'gen1_gate_complete_stairs_'+('up'if up else'down'))
def handle(c,x,y,name,m,data):
 raw=tuple(c['tiles'])
 if c['tileset']=='UNDERGROUND':
  if raw==(11,12,12,11):return native(tunnel,649,'native_tunnel_floor')
  if raw==(6,6,9,9):return native(tunnel,655,'native_tunnel_north_wall')
  if raw==(2,2,16,16):return native(tunnel,645,'native_tunnel_north_void_edge')
  if raw==(16,22,16,22):return native(tunnel,659,'native_tunnel_west_wall')
  if raw==(23,16,23,16):return native(tunnel,663,'native_tunnel_east_wall')
  if raw==(3,4,19,20):return stairs(c,x,y,m,tunnel.ref(649))
  return None
 if raw==(17,1,1,17):return f.native(floor,'gen1_gate_public_checker_floor')
 if raw in((0,0,0,0),(72,72,74,74)):return native(gate,647,'native_complete_header_wall')
 if raw==(16,16,16,16):return native(gate,0,'outside_void')
 if raw in((32,33,50,51),(2,3,18,19)):return native(upper,742,'whole_native_chair')
 if raw==(5,6,21,22):return native(gate,746,'whole_potted_plant_crown')
 if raw==(37,38,53,54):return native(gate,753,'whole_potted_plant_pot')
 if raw==(30,31,50,51):return statue(False)
 if raw in((0,0,14,15),(17,1,14,15)):return statue(True)
 if raw in((10,11,26,27),(11,12,28,29),(12,13,28,29)):return stairs(c,x,y,m,floor)
 if raw==(43,41,59,42):
  parts=north.rect(56,10,8,5)+north.rect(80,10,8,5,8,0)+north.rect(56,21,8,11,0,5)+north.rect(80,21,8,11,8,5)
  return f.composite(floor,parts,'gen1_gate_complete_north_door_frame')
 if raw==(4,4,20,20):return shared('household_rug_right'if same(c,x,y,m,data,-1,raw)else'household_rug_left')
 if raw in((55,56,55,56),(56,55,56,55),(94,94,56,56),(56,56,94,94)):return f.native(floor,'gen1_gate_original_walkable_threshold')
 if raw==(36,36,52,52):return native(upper,704,'complete_binocular_lenses')
 if raw in((57,57,17,17),(57,57,1,17)):return native(upper,712,'complete_binocular_stand')
 glass={58:(688,4,0),45:(680,2,4),61:(689,6,4),62:(688,0,0)}
 if all(t in glass for t in raw):
  parts=[]
  for q,t in enumerate(raw):
   mid,sx,sy=glass[t];parts.append({'donor':upper.ref(mid),'srcX':sx,'srcY':sy,'w':8,'h':8,'x':q%2*8,'y':q//2*8})
  return f.composite(floor,parts,'gen1_gate_continuous_native_glazing')
 if raw in((7,8,34,35),(34,34,34,34),(34,35,34,35)):
  return shared('johto_domestic_complete_single_bay_bookcase_'+('0'if raw[0]==7 else'1'))
 if raw in((7,8,23,24),(7,9,23,24),(9,8,23,24)):return native(gate,706,'complete_desk_back_cap')
 if raw==(23,24,23,24):return native(gate,715,'complete_desk_surface')
 if raw in((9,9,50,51),(9,8,50,51),(7,9,50,51),(9,8,50,24),(23,24,50,51),(7,8,50,51),(23,2,29,53),(7,8,23,24)):
  return native(gate,714,'complete_desk_front')
 return None
f.run(handle,('ROUTE_2_GATE','ROUTE_15_GATE_2F','SAFARI_ZONE_EAST_REST_HOUSE','VIRIDIAN_FOREST_NORTH_GATE','UNDERGROUND_PATH_NORTH_SOUTH'),'Direct native FireRed gate/observation-room desks, complete chairs, bookcases, potted plants, glass/frame modules and whole binocular lenses/stands. Compact complete stair and north-door modules keep their full frames. Native Underground Path walls/floor retain original tunnel geometry. Every original source tile walkability, counter behavior, binocular interaction, exit, hidden-item location and NPC remains unchanged.')
