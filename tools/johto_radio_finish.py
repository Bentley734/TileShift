"""Native Gen3 office and broadcast-room counterparts; unknown props stay held."""
from johto_family_review import FamilyReview
from native_room_parts import RoomParts
import gen2_extended_review as e
f=FamilyReview('radio',{'TILESET_RADIO_TOWER'})
office=RoomParts(f.imp,'firered','FR_SILPH_CO_1F');lab=RoomParts(f.imp,'firered','FR_OAKS_LAB');dojo=RoomParts(f.imp,'firered','FR_SAFFRON_CITY_DOJO');power=RoomParts(f.imp,'firered','FR_POWER_PLANT')
floor=office.ref(820);wall=office.ref(816);wood=dojo.ref(704)
for r in f.active:
 if r['game']=='red'and r['role'].startswith('household_'):f.templates.setdefault(r['role'],r)
def tile(room,sx,sy,base,role):return f.composite(base,room.rect(sx,sy,16,16),'johto_radio_'+role)
def native(room,mid,role):return f.native(room.ref(mid),'johto_radio_'+role)
def template(role,base):
 r=f.template(role,base);r['role']='johto_radio_'+role;return r
def handle(c,x,y,name,m,data):
 raw=tuple(c['tiles']);col=c['collision'];studio=x>=12 and y>=3 and name in('RADIO_TOWER_2F','RADIO_TOWER_4F')or x>=8 and y>=3 and name=='RADIO_TOWER_5F';base=wood if studio else floor
 if raw==(1,1,1,1):return f.native(floor,'johto_radio_public_floor')
 if raw in((66,67,66,67),(50,51,66,67),(21,24,66,67),(24,22,66,67),(64,67,66,67)):return f.native(wood,'johto_radio_recording_room_wood_floor')
 if raw in((17,17,16,16),(17,17,17,17)):return f.native(wall,'johto_radio_complete_wall')
 if raw==(3,4,19,20):return tile(lab,96,16,wall,'complete_wall_notice')
 if raw in((70,71,72,73),(68,69,74,75),(72,73,74,75)):
  return native(office,845 if raw[0]==70 else 853,'complete_native_plant')
 if raw in((128,129,130,131),(132,133,134,135),(136,137,130,131)):
  return native(office,845 if raw[0]in(128,136)else 853,'complete_native_plant')
 if raw in((44,45,60,61),(39,40,55,56)):
  return native(office,786,'complete_round_studio_stool')
 if raw in((12,13,28,29),(14,15,30,31)):
  return f.original('assets/original/interior-stairs/'+('up.png'if raw[0]==12 else'down.png'),base,'johto_radio_stairs_'+('up'if raw[0]==12 else'down'))
 if raw==(2,2,18,18):
  right=x>0 and tuple(e.cell_info(f.cache,c['game'],data,m['tileset'],m['blocks'][y//2*m['width']+(x-1)//2],y%2*2+(x-1)%2)['tiles'])==raw
  return template('household_rug_right'if right else'household_rug_left',floor)
 if raw in((1,138,1,139),(66,138,66,139)):
  return native(office,652,'recording_room_partition_end')
 if raw==(25,9,25,9):return native(office,876,'studio_console_side')
 if raw in((7,7,23,23),(5,7,21,22),(5,7,21,23),(8,9,21,22)):
  return native(office,880,'reception_desk_front')
 if raw==(5,6,8,9):return native(office,876,'reception_desk_side')
 if raw in((36,6,76,77),(90,36,23,140),(90,36,23,64),(7,36,23,23),(7,36,23,22)):
  return f.original('assets/original/interior-computer/computer.png',office.ref(880),'johto_radio_complete_desk_terminal')
 if raw in((17,17,46,47),(62,63,58,59)):
  return template('johto_complete_pc_'+('0'if raw[0]==17 else'1'),wall if raw[0]==17 else floor)
 if raw in((48,49,26,27),(26,27,10,11)):
  return tile(lab,144,16 if raw[0]==48 else 32,base,'complete_record_library_shelf')
 if raw in((48,49,32,33),(17,17,48,49)):
  return template('johto_house_complete_tv_head',wall if y==0 else base)
 if raw in((32,33,41,42),(32,33,7,6),(65,33,64,42)):
  return template('johto_house_complete_tv_base',base)
 if raw==(48,49,48,49):return native(power,699,'equipment_cabinet_body')
 if raw in((34,35,50,51),):return tile(lab,16,16,wood,'complete_audio_control_panel')
 if raw in((86,87,88,89),(88,89,76,77)):
  return template('johto_complete_pc_'+('0'if raw[0]==86 else'1'),office.ref(880))
 if raw==(76,77,1,1):return template('johto_complete_pc_1',floor)
 if raw==(1,1,86,87):return template('johto_complete_pc_0',floor)
 if raw in((17,17,82,83),(17,17,82,52)):
  return native(office,842 if raw[3]==83 else 837,'complete_wall_mounted_equipment')
 if raw in((80,81,1,1),(141,142,80,81),(82,83,80,81)):
  return native(office,837,'complete_native_chair')
 if raw in((144,145,148,149),(146,147,150,151),(152,153,156,157),(154,155,158,159)):
  q={(144,145,148,149):0,(146,147,150,151):1,(152,153,156,157):2,(154,155,158,159):3}[raw]
  return tile(lab,128+q%2*16,64+q//2*16,base,'whole_studio_table_'+str(q))
 if raw in((17,17,16,91),(17,17,17,84)):return f.original('assets/original/interior-computer/computer.png',wall,'johto_radio_complete_security_control')
 if raw in((1,92,1,1),(1,85,1,1)):return f.native(floor,'johto_radio_floor_beneath_security_control')
 # These are microphone/stand and score-sheet artwork. No existing native
 # background counterpart was found; retain original cells pending a match.
 if raw in((32,33,37,38),(53,54,8,25),(78,79,94,95)):return None
 return None
f.run(handle,('RADIO_TOWER_1F','RADIO_TOWER_2F','RADIO_TOWER_3F','RADIO_TOWER_4F','RADIO_TOWER_5F'),'Existing Gen3 office and recording-room floor, partitions, reception desk, round stools, standing PCs, complete television monitors, audio-control equipment, library shelving, studio tables and plants. All radio shows, story events, NPCs, stair warps, door access and source interaction rules remain unchanged. Microphone stands and music scores without a reviewed existing Gen3 counterpart remain held rather than being assigned unrelated artwork.',preserved_raw=((32,33,37,38),(53,54,8,25),(78,79,94,95)))
