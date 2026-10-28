"""Native Gen3 station surroundings; the unique Magnet Train is held."""
import copy
import catalog,gen2_extended_review as e
from johto_family_review import FamilyReview,ROOT
from native_room_parts import RoomParts
f=FamilyReview('station',{'TILESET_TRAIN_STATION'})
office=RoomParts(f.imp,'firered','FR_SILPH_CO_1F');museum=RoomParts(f.imp,'firered','FR_PEWTER_CITY_MUSEUM_1F');center=RoomParts(f.imp,'firered','FR_VIRIDIAN_CITY_POKEMON_CENTER_1F');mart=RoomParts(f.imp,'firered','FR_VIRIDIAN_CITY_MART');power=RoomParts(f.imp,'firered','FR_POWER_PLANT')
platform=museum.ref(642);lobby=mart.ref(641);wall=power.ref(649)
for r in f.active:
 if r['game']=='red'and r['role'].startswith('household_'):f.templates.setdefault(r['role'],r)
train=((7,47,23,0),(40,40,31,31),(31,5,20,21),(6,10,22,26),(9,10,25,26),(10,9,26,25),(10,11,26,27),(12,31,28,29),(36,37,32,31),(38,39,46,31),(41,39,46,31),(42,41,31,46),(42,43,31,46),(44,45,31,15),(10,10,26,26))
def shared(role,base):
 r=f.template(role,base);r['role']='johto_station_'+role;return r
def rail(upper):
 r=shared('goldenrod_raised_rail_platform',platform)
 if upper:
  path=ROOT/'assets/third_party/metalflygon08/rail-cell-0-0.png';r['asset']=path.relative_to(ROOT).as_posix();r['assetFileHash']=catalog.sha(path.read_bytes())
 r['role']='johto_station_complete_rail_'+('upper'if upper else'lower');return r
def handle(c,x,y,name,m,data):
 raw=tuple(c['tiles'])
 if raw in train:return None
 if raw==(61,61,61,61):return f.native(lobby,'johto_station_blue_lobby_floor')
 if raw==(62,62,62,62):return f.native(platform,'johto_station_concrete_platform')
 if raw in((62,62,51,51),(50,50,51,51)):
  # Whole native straight ledge-cap module on the platform safety boundary.
  return f.composite(platform,office.rect(224,204,16,4,0,12),'johto_station_platform_safety_edge')
 if raw==(48,48,48,48):return f.native(wall,'johto_station_structural_wall')
 if raw==(55,56,55,56):return f.native(wall,'johto_station_structural_pillar')
 if raw==(8,8,24,24):return shared('ecruteak_native_metal_fence',platform)
 if raw in((53,54,55,56),(57,58,59,60)):
  p=copy.deepcopy(f.templates['ecruteak_native_metal_fence']['parts'][0]);mid=244 if x<9 else 245;p['donor']=f.ref('firered',p['donor']['tileset'],mid);p['layers']=['over'];p['layerHashes']={'over':f.imp.cell_index('firered')[p['donor']['tileset'],mid]['layer_sha256']['over']}
  return f.composite(platform,[p],'johto_station_complete_gate_side_rail')
 if raw==(31,31,49,49):return rail(True)
 if raw==(17,17,17,17):return rail(False)
 if raw==(64,65,66,67):return f.composite(lobby,center.rect(176,80,16,16),'johto_station_complete_waiting_chair')
 if raw in((68,128,69,129),(61,68,61,69)):
  p=copy.deepcopy(f.templates['ecruteak_native_metal_fence']['parts'][0]);p['donor']=f.ref('firered',p['donor']['tileset'],245);p['layers']=['over'];p['layerHashes']={'over':f.imp.cell_index('firered')[p['donor']['tileset'],245]['layer_sha256']['over']}
  return f.composite(lobby,[p],'johto_station_complete_lobby_guard_rail')
 if raw in((70,130,71,131),(61,70,61,71)):
  return f.original('assets/original/interior-computer/computer.png',wall,'johto_station_complete_gate_control')
 if raw in((80,81,82,83),(82,83,84,85)):
  return shared('household_plant_head'if raw[0]==80 else'household_plant_base',lobby)
 if raw==(14,14,30,30):
  right=x>0 and tuple(e.cell_info(f.cache,c['game'],data,m['tileset'],m['blocks'][y//2*m['width']+(x-1)//2],y%2*2+(x-1)%2)['tiles'])==raw
  return shared('household_rug_right'if right else'household_rug_left',lobby)
 return None
f.run(handle,('GOLDENROD_MAGNET_TRAIN_STATION',),'Existing Gen3 station lobby floor, concrete platform, metal structural panels, safety edge, complete waiting chairs, plants, access-control terminals, gate rails and MetalFlygon08 railway modules. Original boarding events, train movement, controls, source collision and warp positions remain unchanged. The unique Magnet Train vehicle has no reviewed existing native Gen3 counterpart and remains original pending the user choice; it is not replaced with unrelated machinery.',preserved_raw=train)
