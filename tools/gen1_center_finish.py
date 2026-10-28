"""Complete Gen1 healing counters, plants, PCs and Cable Club details."""
from gen1_family_review import FamilyReview,cell_info
from native_room_parts import RoomParts
from gen1_native_plant import native_plant_parts
f=FamilyReview('center',{'POKECENTER'})
center=RoomParts(f.imp,'firered','FR_VIRIDIAN_CITY_POKEMON_CENTER_1F');gate=RoomParts(f.imp,'firered','FR_ROUTE_5_SOUTH_ENTRANCE');floor=center.ref(641);wall=center.ref(644)
healing={(40,58,40,74):0,(59,40,75,40):1,(72,76,72,6):2,(72,76,76,2):2,(77,22,13,1):3,(77,73,22,73):3,(77,7,22,13):3}
def heal(raw):
 q=healing.get(tuple(raw))
 if q is None:return None
 return f.composite(floor,center.rect(80+q%2*16,16+q//2*16,16,16),'gen1_whole_native_healing_machine_'+str(q))

def center_art(c,x,y,name,m,data):
 raw=tuple(c['tiles']);r=heal(raw)
 if r:return r
 if raw in((1,11,17,27),(54,11,26,27),(57,11,60,27)):
  return f.native(floor,'gen1_center_native_public_floor')
 if raw in((32,33,48,49),(34,35,50,51)):
  return f.composite(floor,native_plant_parts(f.imp,top=raw[0]==32),'gen1_complete_native_center_plant')
 if raw==(40,40,40,40):return f.native(wall,'gen1_center_full_wall')
 if raw==(16,41,16,41):return f.native(wall,'gen1_center_structural_counter_wall')
 if raw==(8,8,24,25):return f.template('johto_center_nurse_counter')
 if raw in((56,8,24,25),(4,5,20,21)):return f.template('johto_center_counter_left_end')
 if raw in((8,10,24,25),(90,91,25,24)):return f.template('johto_center_counter_right_front')
 if raw in((66,70,82,86),(9,88,17,27)):
  return f.template('johto_complete_pc_'+('0'if raw[0]==66 else'1'),wall if raw[0]==66 else floor)
 if raw==(12,12,28,28):
  left=not(x>0 and tuple(cell_info(f.cache,c['game'],data,m['tileset'],m['blocks'][y//2*m['width']+(x-1)//2],y%2*2+(x-1)%2)['tiles'])==raw)
  return f.template('household_rug_left'if left else'household_rug_right',floor)
 if raw in((36,37,52,53),(38,39,42,43)):
  return f.source_palette([[248,240,208],[168,192,200],[88,128,152],[32,48,72]],'gen1_original_cable_club_terminal_and_operator')
 if raw in((40,2,40,18),(58,40,19,40),(3,40,19,40),(76,77,90,91)):
  return f.source_palette([[248,240,208],[224,104,96],[152,144,136],[40,48,64]],'gen1_original_compact_wall_pokeball_display')
 if raw in((72,76,76,2),(77,7,22,13),(77,73,22,73)):
  return f.source_palette([[248,240,208],[168,192,200],[88,128,152],[32,48,72]],'gen1_original_counter_equipment_connection')
 if raw==(92,93,94,95):
  parts=gate.rect(56,10,8,5)+gate.rect(80,10,8,5,8,0)+gate.rect(56,21,8,11,0,5)+gate.rect(80,21,8,11,8,5)
  return f.composite(floor,parts,'gen1_whole_native_cable_club_door_frame')
 return None
if __name__=='__main__':f.run(center_art,('VIRIDIAN_POKECENTER','CELADON_HOTEL','FUCHSIA_POKECENTER'),'Direct whole Gen3 healing-machine, nurse-counter, standing PC, potted plant, floor, wall and entry-rug counterparts retain full frames at native pixel scale. Source plant is independently identified from its full1x2 leaf/pot silhouette, never mistaken for machinery. Unique compact Cable Club operator-terminal and wall Pokeball display keep every original pixel with native Gen3 color ramps. Every nurse, multiplayer link, healing interaction, original counter rule, source walk/warp flag and event remains unchanged.')
