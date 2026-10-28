"""Direct native storage/Hideout counterparts for Johto underground rooms."""
from johto_family_review import FamilyReview
from native_room_parts import RoomParts
import gen2_extended_review as e
import preview
f=FamilyReview('underground',{'TILESET_UNDERGROUND'})
hide=RoomParts(f.imp,'firered','FR_ROCKET_HIDEOUT_B1F')
ship=RoomParts(f.imp,'emerald','EM_SLATEPORT_CITY_STERNS_SHIPYARD_1F')
dojo=RoomParts(f.imp,'firered','FR_SAFFRON_CITY_DOJO')
floor=hide.ref(641);wall=hide.ref(649)
statue_bg=set(preview.native_donor(f.cache,dojo.ref(704),f.packed).get_flattened_data())|{(0,0,0,255)}
statue_outside=dojo.exterior(48,192,16,32,statue_bg)
def native(mid,role):return f.native(hide.ref(mid),'johto_underground_'+role)
def neighbor(c,x,y,m,data,dx):
 xx=x+dx
 if not 0<=xx<m['width']*2:return None
 return tuple(e.cell_info(f.cache,c['game'],data,m['tileset'],m['blocks'][y//2*m['width']+xx//2],y%2*2+xx%2)['tiles'])
def handle(c,x,y,name,m,data):
 raw=tuple(c['tiles']);col=c['collision']
 if raw in((16,16,16,16),(52,52,52,52)):return native(641,'native_hideout_floor')
 if raw==(67,68,83,84):return f.native(ship.ref(821),'johto_underground_whole_native_storage_crate')
 if raw==(4,4,20,20):return native(649,'north_wall')
 if raw==(12,13,12,13):return native(652 if x==m['width']*2-1 else 656,'side_wall')
 if raw in((3,5,12,13),(3,5,19,21),(3,5,3,5)):return native(649,'complete_partition_cap')
 if raw==(4,5,20,21):return native(649,'north_wall_east_cap')
 if raw==(3,4,19,20):return native(649,'north_wall_west_cap')
 if raw in((69,70,85,86),(9,25,48,49)):
  top=raw[0]==69
  return f.composite(wall if top else floor,dojo.masked(48,192 if top else 208,list(range(16)),list(range(16)),transparent_pixels=statue_outside),'johto_underground_whole_native_statue_'+('head'if top else'base'))
 if raw in((1,2,18,18),(2,2,18,18)):
  return f.template('household_rug_right'if neighbor(c,x,y,m,data,-1)in((1,2,18,18),(2,2,18,18))else'household_rug_left',floor)
 if raw in((42,43,58,59),(44,45,60,61)):return f.template('johto_gate_stairs_up'if raw[0]==42 else'johto_gate_stairs_down',floor)
 if raw in((30,31,46,47),(62,63,16,16)):return f.template('johto_gate_plant_head'if raw[0]==30 else'johto_gate_plant_base',floor)
 if raw in((64,66,26,27),(26,27,28,29)):
  right=neighbor(c,x,y,m,data,-1)==raw
  return f.template('johto_house_bookcase_'+str((0 if raw[0]==64 else 2)+int(right)),wall if raw[0]==64 else floor)
 if raw in((4,4,64,65),(80,93,38,39)):return f.template('johto_complete_pc_'+('0'if raw[0]==4 else'1'),wall if raw[0]==4 else floor)
 if raw==(4,4,78,79):return native(773,'native_control_panel_head')
 if raw==(94,95,54,55):return native(774,'native_control_panel_base')
 if raw==(40,41,56,57):return native(739,'whole_native_computer_seat')
 if raw==(34,35,50,51):return native(153,'native_teleport_panel')
 return None
f.run(handle,('GOLDENROD_UNDERGROUND_WAREHOUSE','TEAM_ROCKET_BASE_B1F','OLIVINE_PORT_PASSAGE'),'Native Gen3 Hideout walls, control panels, complete PCs, storage crates, complete statue pairs, shelves, stairs, plants and warp panels. All source collisions, Persian alarms, switch state, movable shelves, storage access and events are retained. Direct pixel-size counterparts; no new artwork or map changes.')
