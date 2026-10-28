"""Direct native Gen3 counterparts for the remaining Johto gym interiors."""
from johto_family_review import FamilyReview
from native_room_parts import RoomParts
import gen2_extended_review as e

f=FamilyReview('gyms',{'TILESET_ELITE_FOUR_ROOM','TILESET_CHAMPIONS_ROOM'})
vir=RoomParts(f.imp,'firered','FR_VIRIDIAN_CITY_GYM')
cel=RoomParts(f.imp,'firered','FR_CELADON_CITY_GYM')
ice=RoomParts(f.imp,'emerald','EM_SOOTOPOLIS_CITY_GYM_1F')
fire=RoomParts(f.imp,'emerald','EM_LAVARIDGE_TOWN_GYM_1F')
power=RoomParts(f.imp,'firered','FR_POWER_PLANT')
bike=RoomParts(f.imp,'firered','FR_CERULEAN_CITY_BIKE_SHOP')
north=RoomParts(f.imp,'firered','FR_ROUTE_5_SOUTH_ENTRANCE')
cave=f.ref('emerald','general__cave',513)

def nat(room,mid,role):return f.native(room.ref(mid),role)
def raw_at(c,x,y,m,data):
 if not 0<=x<m['width']*2 or not 0<=y<m['height']*2:return ()
 return tuple(e.cell_info(f.cache,c['game'],data,m['tileset'],m['blocks'][y//2*m['width']+x//2],y%2*2+x%2)['tiles'])

def handle(c,x,y,name,m,data):
 raw=tuple(c['tiles']);col=c['collision'];shop=name=='GOLDENROD_BIKE_SHOP'
 floor=bike.ref(670)if shop else cel.ref(670)if name=='AZALEA_GYM'else fire.ref(513)if name.startswith('BLACKTHORN')else vir.ref(641)
 if c['tileset']=='TILESET_ELITE_FOUR_ROOM':
  if raw==(1,1,1,1):return f.native(floor,'johto_gym_native_tiled_floor')
  if raw==(3,3,3,3):return nat(cel,670,'johto_bug_gym_clear_path')
  if raw in((31,31,30,31),(30,31,31,31),(31,31,30,30)):return nat(cel,641,'johto_bug_gym_turf')
  if raw in((7,8,23,24),(62,63,23,24)):return f.template('johto_house_complete_single_flowerpot',floor)
  trees={(11,12,27,28):'northwest',(13,31,29,31):'northeast',(46,47,31,31):'southwest',(10,31,31,31):'southeast'}
  if raw in trees:return f.template('dense_forest_tree_'+trees[raw],cel.ref(641))
  if raw in((42,43,58,59),(37,39,53,55),(39,38,55,54),(37,38,53,54)):return nat(power,649,'johto_gym_complete_stone_partition')
  if raw==(16,16,16,16):return nat(power,649,'johto_switch_room_partition_face')
  if raw==(26,26,26,26):return nat(power,708,'johto_switch_room_partition_grille')
  if raw in((19,19,18,18),(57,57,57,57),(57,57,2,91),(57,57,2,2)):
   if col==96:return f.native(f.ref('firered','general__rom_082d4e24',859),'johto_gym_original_fall_hole')
   return f.composite(floor,[{'donor':power.ref(649),'w':16,'h':8}],'johto_gym_platform_front_edge')
  if raw==(17,17,1,1):return f.native(floor,'johto_switch_room_native_floor')
  if raw in((5,6,21,22),(80,80,36,36)):return nat(ice,525,'johto_ice_gym_sliding_ice')
  if raw==(52,52,52,52):return nat(ice,520,'johto_ice_gym_blue_partition')
  if raw==(40,40,40,40):return nat(power,708,'johto_ice_gym_grip_floor_grate')
  if set(raw)<={2,56,91}:return f.native(f.ref('emerald','general__lavaridge',819),'johto_dragon_gym_native_magma')
  if raw==(85,86,87,88):
   d=f.ref('emerald','general__cave',514);h=f.imp.cell_index('emerald')['general__cave',514]['layer_sha256']['mid']
   return f.composite(floor,[{'donor':d,'layers':['mid'],'layerHashes':{'mid':h},'w':16,'h':16}],'johto_gym_whole_strength_boulder')
  if raw==(78,79,94,95):return f.native(f.ref('firered','general__rom_082d4e24',859),'johto_dragon_gym_boulder_hole')
  if raw in((64,65,66,67),(44,45,60,61)):return f.template('johto_gate_stairs_'+('up'if raw[0]==64 else'down'),floor)
  if raw==(76,77,16,16):return nat(power,750,'johto_switch_room_complete_wall_control')
  if raw==(72,73,74,75):
   sx=72 if raw_at(c,x-1,y,m,data)==raw else 56
   return f.composite(floor,north.rect(sx,10,16,5)+north.rect(sx,21,16,11,0,5),'johto_switch_room_complete_north_exit')
  if raw==(32,33,48,49):return nat(cel,696,'johto_gym_complete_statue_head')
  if raw==(34,35,50,51):return nat(cel,697,'johto_gym_complete_statue_plinth')
 if c['tileset']=='TILESET_CHAMPIONS_ROOM':
  if shop:
   if raw in((17,17,32,32),(17,32,17,32),(17,17,17,32),(32,32,32,32)):return nat(bike,670,'johto_bike_shop_native_floor')
   if raw==(1,1,33,33):return nat(bike,662,'johto_bike_shop_wall_foot')
   if raw in((1,1,37,37),(1,1,37,39)):return nat(bike,662,'johto_bike_shop_wall_foot')
   books={(37,38,54,55):(16,16),(38,39,55,58):(32,16),(34,35,50,51):(16,32),(35,36,51,52):(32,32)}
   if raw in books:
    sx,sy=books[raw];return f.composite(floor,bike.rect(sx,sy,16,16),'johto_bike_shop_complete_shelf')
   if raw in((2,3,43,44),(18,19,33,33),(18,19,43,44)):return f.template('johto_house_complete_single_flowerpot',floor)
   # Both games' complete bicycles span32x16. Their native foreground
   # layers retain both wheels, the frame, saddle and handlebar.
   if raw==(5,6,21,22):return nat(bike,667,'johto_bike_shop_wall_handlebars')
   bikes={(12,13,28,29):0,(14,15,30,31):1,(32,42,32,32):0,(40,41,56,57):1}
   if raw in bikes:return f.composite(floor,bike.rect(16+bikes[raw]*16,80,16,16,layers=['mid']),'johto_bike_shop_whole_native_bicycle')
   if raw==(8,9,24,25):return nat(bike,656,'johto_bike_shop_counter_register')
   if raw==(53,23,48,49):return nat(bike,659,'johto_bike_shop_counter_end')
   if raw in((38,38,38,7),(38,38,7,7)):return nat(bike,665,'johto_bike_shop_counter_top')
  else:
   if raw in((10,11,10,11),(10,11,26,27)):
    return nat(vir,674 if x==0 else 680,'johto_steel_gym_perimeter_wall')
   if raw==(45,45,45,45):return nat(vir,653,'johto_steel_gym_tiled_walkway')
   if raw in((72,72,72,72),(81,81,81,81)):return f.native(cave,'johto_steel_gym_raised_stone_floor')
   rock={(70,71,86,87):529,(72,72,81,81):521,(80,80,80,80):538,(82,82,82,82):529,(83,64,64,80):530,(66,83,82,66):540,(80,67,67,66):539,(80,67,67,68):539,(69,82,68,69):530}
   if raw in rock:return f.native(f.ref('emerald','general__cave',rock[raw]),'johto_steel_gym_rock_mass_'+str(rock[raw]))
   if raw==(84,85,84,85):return f.native(f.ref('emerald','general__cave',516),'johto_steel_gym_stone_steps')
   if raw==(46,47,62,63):return nat(cel,696,'johto_steel_gym_statue_head')
   if raw==(78,79,94,95):return nat(cel,697,'johto_steel_gym_statue_plinth')
 if raw==(4,4,20,20):
  left=raw_at(c,x-1,y,m,data)!=raw
  return f.template('household_rug_left'if left else'household_rug_right',floor)
 return None

f.run(handle,('AZALEA_GYM','BLACKTHORN_GYM_1F','BLACKTHORN_GYM_2F','MAHOGANY_GYM','GOLDENROD_GYM','VIOLET_GYM','OLIVINE_GYM','GOLDENROD_BIKE_SHOP','GOLDENROD_UNDERGROUND_SWITCH_ROOM_ENTRANCES'),'Direct existing native Gen3 gym floors, turf, complete statues, partitions, strength rocks, ice, magma, bicycle displays and shop furnishings. Native artwork remains at its original pixel scale. Original collision, holes, boulder changes, sliding, switches, scripts, actors and entrances are preserved.')
