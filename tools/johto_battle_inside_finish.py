"""Use Emerald Battle Tower rooms for Crystal's original Battle Tower."""
from johto_family_review import FamilyReview
from native_room_parts import RoomParts
import preview
f=FamilyReview('battle_inside',{'TILESET_BATTLE_TOWER_INSIDE'})
lobby=RoomParts(f.imp,'emerald','EM_BATTLE_FRONTIER_BATTLE_TOWER_LOBBY')
battle=RoomParts(f.imp,'emerald','EM_BATTLE_FRONTIER_BATTLE_TOWER_BATTLE_ROOM')
lift=RoomParts(f.imp,'emerald','EM_BATTLE_FRONTIER_BATTLE_TOWER_ELEVATOR')
corridor=RoomParts(f.imp,'emerald','EM_BATTLE_FRONTIER_BATTLE_TOWER_CORRIDOR')
casino=RoomParts(f.imp,'firered','FR_CELADON_CITY_GAME_CORNER')
floor=lobby.ref(512)
plant_bg=set()
for mid in (512,515,516,525):plant_bg.update(preview.native_donor(f.cache,lobby.ref(mid),f.packed).get_flattened_data())
plant_outside=lobby.exterior(0,128,16,32,plant_bg)
def plant(dx,dy,base):
 return f.composite(base,lobby.masked(dx*8,128+dy*16,list(range(8)),list(range(16)),8 if dx==0 else 0,0,transparent_pixels=plant_outside),'johto_battle_complete_native_potted_plant')
def native(room,mid,role):return f.native(room.ref(mid),'johto_battle_'+role)
def part(room,mid,sx=0,sy=0,w=16,h=16,x=0,y=0):return {'donor':room.ref(mid),'srcX':sx,'srcY':sy,'w':w,'h':h,'x':x,'y':y}
def handle(c,x,y,name,m,data):
 raw=tuple(c['tiles']);col=c['collision']
 if name=='BATTLE_TOWER_BATTLE_ROOM':
  if 2<=x<=5 and 2<=y<=5:
   # Keep every pixel of the circle and all four border corners; remove only
   # 16px of repeatable plain court surface from each outer side.
   columns=[0,1,*range(18,78),94,95][(x-2)*16:(x-1)*16]
   return f.composite(battle.ref(570),battle.masked(32,56,columns,list(range((y-2)*16,(y-1)*16))),'johto_battle_complete_native_court')
  if col==113:return native(corridor,548,'whole_native_room_door')
  if raw==(88,88,55,55):return f.composite(battle.ref(0),[part(battle,570,w=16,h=8)],'johto_battle_lower_room_corner')
  if raw in((4,5,20,21),(7,23,4,5),(20,21,37,37)):return native(battle,567 if y==0 else 570,'battle_wall'if y==0 else'battle_floor')
  if raw in((48,48,48,48),(37,37,48,48)):return native(battle,570,'battle_room_tiled_floor')
  plants={(48,48,48,70):(0,0),(48,48,71,48):(1,0),(48,86,48,48):(0,1),(87,48,48,48):(1,1)}
  if raw in plants:
   dx,dy=plants[raw];return plant(dx,dy,battle.ref(570))
  if raw==(33,33,49,49):return native(battle,534 if x==3 else 535,'battle_room_exit_mat')
 if name=='BATTLE_TOWER_ELEVATOR':
  if raw in((91,91,91,91),(91,91,91,92),(91,91,77,93)):return native(lift,816 if x==0 else 820,'native_lift_wall')
  if raw in((92,78,48,48),(94,92,48,48)):return native(lift,824 if x==0 else 828,'lift_lower_wall')
  if raw==(48,48,48,48):return native(lift,604,'lift_floor')
  if col==113:return native(lift,591 if x==1 else 599,'lift_exit_mat')
  if col==112:return native(lift,591 if x==1 else 599,'lift_control_mat')
 if raw==(17,17,17,17):return native(lobby,512,'lobby_floor')
 if raw in((1,1,17,17),(1,17,1,17),(1,1,1,17)):return native(lobby,516,'lobby_carpet_border')
 if raw in((17,17,89,90),(17,17,75,76)):return native(corridor,631 if raw[2]==89 else 623,'corridor_floor_medallion')
 if raw in((84,85,80,81),(68,69,84,85),(67,69,84,85),(68,69,72,73),(68,69,74,85),(84,85,79,95)):
  return f.template('johto_house_bookcase_'+str(x%2),lobby.ref(521))
 if raw==(80,81,1,1):return f.template('johto_house_bookcase_'+str(2+x%2),floor)
 if raw==(69,69,2,3):return native(lobby,518,'corridor_door_header')
 if raw==(18,19,1,1):return native(lobby,526,'corridor_door_threshold')
 if raw==(2,3,18,19):return native(corridor,548,'whole_native_lobby_door')
 if raw==(53,11,53,11):return native(lobby,528,'counter_return')
 if raw==(14,15,30,31):return f.composite(floor,casino.rect(16,96,16,16),'johto_battle_whole_seat')
 plants={(17,17,17,70):(0,0),(17,17,71,17):(1,0),(17,86,17,17):(0,1),(87,17,17,17):(1,1)}
 if raw in plants:
  dx,dy=plants[raw];return plant(dx,dy,floor)
 if raw in((46,47,62,63),(44,45,60,61)):return native(lobby,528,'side_counter')
 if raw in((64,17,46,65),(17,59,58,45)):return native(lobby,532,'side_counter_cap')
 if raw==(33,33,49,49):return native(lobby,534 if x==7 else 535,'entry_mat')
 if raw in((10,10,26,26),(53,129,22,26),(6,10,22,26)):return native(lobby,530,'registration_counter_front')
 if raw in((88,88,55,56),(91,91,92,92)):return native(lobby,560,'registration_counter_side')
 if raw==(8,9,24,25):return native(lobby,4,'complete_native_registration_terminal')
 if raw==(12,13,28,29):return native(lobby,544,'registration_terminal_base')
 if raw in((40,41,56,57),(42,43,26,27)):return native(lobby,4,'whole_native_video_terminal')
 return None
f.run(handle,('BATTLE_TOWER_1F','BATTLE_TOWER_BATTLE_ROOM','BATTLE_TOWER_HALLWAY','BATTLE_TOWER_ELEVATOR'),'Direct Emerald Battle Tower lobby, battle court, corridor, elevator and furniture. Complete court circle and corners retained at native pixel size by omitting only blank repeat columns. All original challenge, registration, elevator, doors and battle rules are unchanged.')
