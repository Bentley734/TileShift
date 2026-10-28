"""Direct Gen3 office, Hideout, Mansion, Power Plant and puzzle counterparts."""
import json
from gen1_family_review import FamilyReview
from native_room_parts import RoomParts
from gen1_native_plant import native_plant_parts
f=FamilyReview('facilities',{'FACILITY'})
rocket=RoomParts(f.imp,'firered','FR_ROCKET_HIDEOUT_B2F');silph=RoomParts(f.imp,'firered','FR_SILPH_CO_1F');mansion=RoomParts(f.imp,'firered','FR_POKEMON_MANSION_1F');power=RoomParts(f.imp,'firered','FR_POWER_PLANT');saffron=RoomParts(f.imp,'firered','FR_SAFFRON_CITY_GYM');cinnabar=RoomParts(f.imp,'firered','FR_CINNABAR_ISLAND_GYM');tower=RoomParts(f.imp,'emerald','EM_BATTLE_FRONTIER_BATTLE_TOWER_LOBBY');lab=RoomParts(f.imp,'firered','FR_OAKS_LAB')
STEEL=[[255,255,255],[197,206,214],[123,140,156],[57,66,82]]
STONE=[[255,239,181],[214,197,140],[148,132,99],[74,74,82]]
def palette(colors,role):return f.source_palette(colors,'gen1_facility_'+role)
def n(room,mid,role):return f.native(room.ref(mid),'gen1_facility_'+role)
def layout(name):
 if name.startswith('POKEMON_MANSION'):return mansion,mansion.ref(644),674,692
 if name=='POWER_PLANT':return power,power.ref(671),661,664
 if name=='SAFFRON_GYM':return saffron,saffron.ref(641),643,652
 if name=='CINNABAR_GYM':return cinnabar,cinnabar.ref(641),643,715
 if name.startswith('SILPH_CO'):return silph,silph.ref(820),816,876
 return rocket,rocket.ref(641),649,670
def shared(role,base):
 a=f.template(role,base);a['role']='gen1_facility_'+role;return a
def handle(c,x,y,name,m,data):
 raw=tuple(c['tiles']);room,floor,north,vertical=layout(name)
 if raw in((17,17,17,17),(82,82,82,82),(66,82,66,82),(82,66,82,66)):
  return f.native(floor,'gen1_facility_complete_context_floor')
 if raw==(20,20,20,20):return n(silph,968,'native_office_reception_carpet')
 arrows={(33,33,32,32):673,(49,49,48,48):681,(33,49,33,49):672,(32,48,32,48):680}
 if raw in arrows:return n(rocket,arrows[raw],'native_spinner_'+{673:'left',681:'right',672:'up',680:'down'}[arrows[raw]])
 if raw==(94,94,94,94):return n(rocket,655,'native_spinner_stop_panel')
 if raw==(33,49,32,48):return n(saffron,659,'complete_native_teleport_pad')
 if raw in((3,4,19,78),(86,86,88,88)):
  return f.original('assets/original/interior-stairs/'+('up'if raw[0]==3 else'down')+'.png',floor,'gen1_facility_complete_stairs')
 if raw in((5,6,21,22),(7,15,23,31)):
  return f.composite(floor,native_plant_parts(f.imp,raw[0]==5),'gen1_facility_complete_native_plant_'+('head'if raw[0]==5 else'pot'))
 if raw in((42,42,13,14),(87,87,13,14)):
  return f.composite(floor,[{'donor':room.ref(north),'w':16,'h':8}]+lab.rect(128,64,8,8,0,8)+lab.rect(168,64,8,8,8,8),'gen1_facility_complete_table_cap_below_wall')
 table_raws={(13,2,29,53),(2,14,53,30),(29,53,29,53),(53,30,53,30),(29,53,68,69),(53,30,69,68),(13,14,29,30),(29,30,29,30),(29,30,18,18),(65,17,65,17),(65,17,81,17),(64,64,80,80)}
 if raw in table_raws:
  if raw==(29,30,18,18):return f.composite(floor,lab.rect(128,80,8,8)+lab.rect(168,80,8,8,8,0),'gen1_facility_complete_narrow_table_foot')
  modules={13:(128,64),14:(168,64),2:(144,64),29:(128,72),30:(168,72),53:(144,72),68:(128,80),69:(144,80),64:(144,72),80:(144,80),65:(128,72),81:(128,80)}
  parts=[]
  for q,t in enumerate(raw):
   if t==17:continue
   sx,sy=modules[t]
   if t==68 and q%2:sx=168
   parts+=lab.rect(sx,sy,8,8,q%2*8,q//2*8)
  return f.composite(floor,parts,'gen1_facility_complete_native_modular_lab_table')
 if raw==(40,41,56,57):return shared('johto_lighthouse_complete_native_bed_head',floor)
 if raw==(56,57,25,26):return shared('johto_lighthouse_complete_native_bed_foot',floor)
 if raw==(9,10,25,26):
  if name=='CINNABAR_GYM':return n(cinnabar,664,'native_quiz_console')
  return n(rocket,741,'complete_native_spinner_maze_barrier')
 if raw==(83,84,54,38):return n(mansion,716,'complete_native_broken_masonry')
 if raw in((55,63,61,62),(1,1,39,47)):
  return palette(STONE,'preserved_compact_switch_statue_or_broken_edge')
 if raw in((74,75,76,77),(11,12,27,28)):
  return palette(STEEL,'preserved_complete_compact_cabinet')
 if raw in((87,87,89,89),(90,91,67,52)):
  return palette(STEEL,'preserved_complete_wall_equipment')
 # All original closed partitions remain visibly solid. Complete native
 # structural modules provide wall faces; no walkability is inferred from art.
 horizontal={(42,42,58,58),(2,2,18,18)}
 verticals={(43,44,43,44),(29,53,29,53),(53,30,53,30),(29,30,29,30),(65,17,65,17),(65,17,81,17)}
 corners={(42,46,58,60),(45,42,59,58),(42,46,43,44),(13,2,29,53),(2,14,53,30),(45,42,43,44),(29,53,68,69),(53,30,69,68),(45,46,43,44),(43,44,59,60),(29,30,18,18)}
 if raw in horizontal:return n(room,north,'native_partition_north_face')
 if raw in verticals:return n(room,vertical,'native_partition_vertical_face')
 if raw in corners:
  if room is mansion:return n(mansion,673 if raw[0]in(45,2)else 675,'complete_native_timber_partition_corner')
  if room is saffron:return n(saffron,663 if raw[0]in(45,2)else 644,'complete_native_psychic_partition_corner')
  if room is cinnabar:return n(cinnabar,709 if raw[0]in(45,2)else 707,'complete_native_gym_partition_corner')
  return n(rocket,734 if raw[0]in(45,2)else 735,'complete_native_office_partition_corner')
 return None
f.run(handle,('SILPH_CO_3F','ROCKET_HIDEOUT_B3F','POKEMON_MANSION_B1F','POWER_PLANT','SAFFRON_GYM','CINNABAR_GYM'),'Reviewed native Gen3 office/Hideout/Mansion/Power Plant/gym surfaces, complete computers, framed doors, staircase modules, plants and teleport pads. Four spinner directions use whole native arrow panels matched to the original extracted scripted first-movement directions; the full stop panel remains distinct. Original compact switch statues, ruined boundary fragments and small wall equipment keep every source pixel in the approved Gen3 palette when no complete same-footprint native object exists. All original forced movement, Card Key doors, quiz conditions, Mansion switches, encounters, warps, NPCs and collisions stay unchanged.')
