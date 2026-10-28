"""Native Gen3 gym, dojo and memorial objects with exact Gen1 puzzle geometry."""
import copy
from gen1_family_review import FamilyReview,ROOT,cell_info
from native_room_parts import RoomParts
f=FamilyReview('temples',{'GYM','DOJO','CEMETERY'})
vir=RoomParts(f.imp,'firered','FR_VIRIDIAN_CITY_GYM');dojo=RoomParts(f.imp,'firered','FR_SAFFRON_CITY_DOJO');cel=RoomParts(f.imp,'firered','FR_CELADON_CITY_GYM');ver=RoomParts(f.imp,'firered','FR_VERMILION_CITY_GYM');cer=RoomParts(f.imp,'firered','FR_CERULEAN_CITY_GYM');fuc=RoomParts(f.imp,'firered','FR_FUCHSIA_CITY_GYM');tower=RoomParts(f.imp,'firered','FR_POKEMON_TOWER_2F');tower5=RoomParts(f.imp,'firered','FR_POKEMON_TOWER_5F');oak=RoomParts(f.imp,'firered','FR_OAKS_LAB');power=RoomParts(f.imp,'firered','FR_POWER_PLANT')
indigo=RoomParts(f.imp,'firered','FR_INDIGO_PLATEAU_EXTERIOR')
STONE=[[239,239,247],[181,181,165],[123,123,123],[0,0,0]]
TIMBER=[[247,239,206],[222,214,140],[181,173,99],[0,0,0]]
def rawat(c,x,y,m,data):
 if not 0<=x<m['width']*2 or not 0<=y<m['height']*2:return ()
 return tuple(cell_info(f.cache,c['game'],data,m['tileset'],m['blocks'][y//2*m['width']+x//2],y%2*2+x%2)['tiles'])
def n(room,mid,role):return f.native(room.ref(mid),role)
def statue(mid,base,role):
 d=indigo.ref(mid);hs=f.imp.cell_index('firered')[d['tileset'],mid]['layer_sha256'];return f.composite(base,[{'donor':d,'layers':['mid','over'],'layerHashes':{k:hs[k]for k in('mid','over')},'w':16,'h':16}],role)
WALLS={15,16,35,36,37,38,39,53,54,55,56,57,58,59,60,61,62,66}
def handle(c,x,y,name,m,data):
 raw=tuple(c['tiles']);ts=c['tileset'];room=dojo if ts=='DOJO'else tower if ts=='CEMETERY'else cer if name=='CERULEAN_GYM'else cel if name=='CELADON_GYM'else fuc if name=='FUCHSIA_GYM'else ver if name=='VERMILION_GYM'else vir
 floor=dojo.ref(704)if ts=='DOJO'else tower.ref(642)if ts=='CEMETERY'else room.ref(670 if name=='CELADON_GYM'else 641)
 if raw==(17,17,17,17):return f.native(floor,'gen1_gym_native_theme_floor')
 if raw==(9,10,25,26):return n(power,649,'gen1_memorial_complete_stone_partition')
 if raw==(5,6,21,22)and ts=='CEMETERY':return n(tower,657,'gen1_tower_complete_gravestone')
 if raw in((4,4,4,4),(34,34,34,34))and ts=='CEMETERY':return n(tower5,674,'gen1_tower_complete_purification_marker')
 if raw in((3,4,19,20),(11,12,27,28))and ts=='CEMETERY':return f.template('johto_gate_stairs_'+('up'if raw[0]==3 else'down'),floor)
 if raw in((2,2,18,18),(32,32,48,48))and ts=='CEMETERY':return n(tower,664,'gen1_tower_complete_wall_header')
 if raw==(2,2,18,18)and ts=='DOJO':return n(dojo,705,'gen1_lab_complete_wall_header')
 if raw in((20,0,21,22),(29,30,29,30))and ts=='CEMETERY':return n(tower,672,'gen1_tower_complete_wall_column')
 if raw in((2,3,18,19),(2,56,18,19)):return statue(694,floor,'gen1_gym_complete_rhydon_statue_head')
 if raw in((54,54,55,50),(34,35,50,51))and ts!='CEMETERY':return statue(671,floor,'gen1_gym_complete_rhydon_statue_plinth')
 if raw in((55,55,53,53),(55,63,61,62))and ts=='CEMETERY':return statue(671,floor,'gen1_memorial_complete_rhydon_statue_plinth')
 if raw==(1,1,39,47)and ts=='CEMETERY':return statue(694,floor,'gen1_memorial_complete_rhydon_statue_head')
 if raw==(1,1,51,51)and ts=='CEMETERY':return n(vir,673,'gen1_memorial_complete_statue_head')
 if raw==(19,19,35,35)and ts=='CEMETERY':return f.native(floor,'gen1_memorial_flower_offerings')
 if raw==(7,8,23,24)and ts=='GYM':
  d=f.ref('emerald','general__cave',514);hs=f.imp.cell_index('emerald')['general__cave',514]['layer_sha256']['mid'];return f.composite(floor,[{'donor':d,'layers':['mid'],'layerHashes':{'mid':hs},'w':16,'h':16}],'gen1_gym_complete_boulder')
 if raw==(20,20,20,20)and name in('CERULEAN_GYM','LORELEIS_ROOM'):return n(cer,657,'freshwater_pond_gym_pool')
 if raw==(4,4,20,20)and name in('CERULEAN_GYM','LORELEIS_ROOM'):return n(cer,649,'freshwater_pond_gym_pool_north_bank')
 if raw==(1,1,2,2)and name=='CERULEAN_GYM':return n(cer,672,'gen1_gym_pool_ladder_and_deck')
 if raw in((51,51,51,51),(31,31,31,31))and name=='FUCHSIA_GYM':return n(fuc,649,'gen1_gym_original_invisible_partition_floor')
 if raw==(63,63,63,63):return n(vir,653,'gen1_gym_stop_floor')
 arrows={(76,77,76,77):651,(60,60,76,76):649,(60,61,60,61):652,(61,61,77,77):650}
 if raw in arrows:return n(vir,arrows[raw],'gen1_gym_original_conveyor_direction_'+str(arrows[raw]))
 if raw in((27,28,27,28),(11,12,27,28))and ts=='GYM':return n(ver,696,'gen1_gym_complete_trash_switch_bin')
 if raw==(11,12,27,28)and name=='OAKS_LAB':return n(ver,696,'gen1_lab_complete_trash_bin')
 if raw==(13,14,29,30):
  # Gen1 displays16px units; two contiguous units become one complete32px
  # Gen3 cabinet, without shrinking its shelf or cutting the outside frame.
  start=x
  while rawat(c,start-1,y,m,data)==raw:start-=1
  return f.template('johto_house_bookcase_'+str(2+(x-start)%2),floor)
 if raw==(41,42,13,14):
  start=x
  while rawat(c,start-1,y,m,data)==raw:start-=1
  return f.template('johto_house_bookcase_'+str((x-start)%2),floor)
 if raw in((44,45,46,44),(44,45,46,47)):return f.template('boundary_tree',cel.ref(641))
 if raw in((44,44,50,51),(64,65,80,81)):return f.template('cuttable_small_tree',cel.ref(641))
 if all(t in(3,43,44,47)for t in raw)and ts=='GYM':return n(cel,641,'gen1_gym_native_turf')
 if raw in((50,51,51,50),(52,67,82,83)):return f.source_palette(TIMBER,'gen1_dojo_original_framed_calligraphy')
 if raw==(5,5,16,16):return n(dojo,705,'gen1_temple_complete_wall_header')if ts=='DOJO'else n(vir,657,'gen1_gym_complete_wall_header')
 if raw==(1,1,17,17):return f.native(floor,'gen1_gym_native_deck')
 if raw==(6,6,22,22):return f.template('household_rug_left'if rawat(c,x-1,y,m,data)!=raw else'household_rug_right',floor)
 if raw in((69,70,86,86),(5,5,86,86),(68,5,84,86),(5,71,86,87)):return n(ver,646,'gen1_gym_whole_electrical_switch_control')
 if raw in((99,100,52,53),(99,100,52,52)):return f.template('johto_complete_pc_1',floor)
 if raw==(98,99,84,85):return f.template('johto_complete_native_region_map',floor)
 if raw in((88,89,17,17),(89,89,17,17)):
  above=rawat(c,x,y-1,m,data)
  if above in((41,59,78,57),(59,42,57,79)):return f.template('household_table_sw'if above[0]==41 else'household_table_se',floor)
 if raw in((88,88,74,74),(89,90,17,17),(88,88,21,22),(89,90,21,22),(88,89,17,17),(89,89,17,17)):
  return n(oak,753,'gen1_lab_complete_modular_desk_front')
 if raw in((68,63,84,48),):return f.template('johto_gate_complete_desk_computer',floor)
 if raw==(91,92,54,55):return n(oak,98,'gen1_lab_complete_computer_display')
 if raw==(93,94,85,95):return n(oak,803,'gen1_lab_complete_keyboard_and_control_unit')
 if raw in((88,89,25,26),(89,90,25,26)):return n(oak,753,'gen1_lab_complete_console_foot')
 if raw in((41,59,78,57),(59,42,57,79)):return f.template('household_table_nw'if raw[0]==41 else'household_table_ne',floor)
 if raw in((32,33,48,49),):return f.source_palette(STONE,'gen1_league_original_embedded_record_panel')
 if raw==(72,73,74,75):return f.template('johto_gate_stairs_up',floor)
 if raw in((41,42,13,14),(13,14,29,30)):return None
 if all(t in WALLS for t in raw):
  return f.source_palette(TIMBER if ts=='DOJO'else STONE,'gen1_original_narrow_architectural_frames')
 return None
f.run(handle,('POKEMON_TOWER_4F','POKEMON_TOWER_5F','AGATHAS_ROOM','FIGHTING_DOJO','OAKS_LAB','LANCES_ROOM','CERULEAN_GYM','CELADON_GYM','VERMILION_GYM','VIRIDIAN_GYM','FUCHSIA_GYM'),'Direct native Gen3 complete tombstones, purification markers, gym statues, strength rocks, bins, floors, shelves, grass, pool and directional conveyor counterparts. Original collision and all puzzle, switch, hidden-wall, healing, stair and story behavior remain unchanged. Gen1-specific narrow architectural frames and literal dojo calligraphy retain every original pixel in Gen3 timber/stone colors when no native geometry fits without chopping the frame. All complete furniture and native modules remain at1:1 pixel scale.')
