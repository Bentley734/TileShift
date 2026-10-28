"""S.S.Anne native furnishings and animated harbour, retaining its compact hull."""
import copy
from gen1_family_review import FamilyReview,cell_info
from native_room_parts import RoomParts
f=FamilyReview('ship',{'SHIP','SHIP_PORT'});cabin=RoomParts(f.imp,'firered','FR_SSANNE_1F_ROOM1');captain=RoomParts(f.imp,'firered','FR_SSANNE_CAPTAINS_OFFICE');kitchen=RoomParts(f.imp,'firered','FR_SSANNE_KITCHEN');harbor=RoomParts(f.imp,'firered','FR_SSANNE_EXTERIOR');museum=RoomParts(f.imp,'firered','FR_PEWTER_CITY_MUSEUM_1F');power=RoomParts(f.imp,'firered','FR_POWER_PLANT')
STEEL=[[247,247,247],[189,206,214],[132,148,156],[66,74,107]]
WOOD=[[247,239,206],[222,214,140],[181,173,99],[0,0,0]]
WATER=[[99,165,222],[66,132,197],[49,107,173],[33,82,140]]
def n(room,mid,role):return f.native(room.ref(mid),role)
def water(parts=None,role='coastal_ocean_water_interior'):
 a=f.template('coastal_ocean_water_interior')
 if parts:a['base']=a.pop('donor');a['kind']='native_composite';a['parts']=parts
 a['role']=role;return a
def at(c,x,y,m,data):
 if not 0<=x<m['width']*2 or not 0<=y<m['height']*2:return ()
 return tuple(cell_info(f.cache,c['game'],data,m['tileset'],m['blocks'][y//2*m['width']+x//2],y%2*2+x%2)['tiles'])
def handle(c,x,y,name,m,data):
 raw=tuple(c['tiles']);floor=f.ref('firered','house',1)if name in('CERULEAN_BADGE_HOUSE','FUCHSIA_GOOD_ROD_HOUSE')else cabin.ref(796)
 if c['tileset']=='SHIP_PORT':
  if raw==(20,20,20,20):return water()
  if raw==(58,58,20,20):return water(harbor.rect(512,232,16,8),'coastal_rock_shore_ship_dock_north_bank')
  if raw==(10,10,10,10):return n(harbor,449,'gen1_port_native_walkable_pier')
  if raw in((9,9,41,41),(58,58,41,41)):
   w=water();a=f.template('ecruteak_native_metal_fence',w['donor']);a.update(animated=True,animation=copy.deepcopy(w['animation']),role='coastal_rock_shore_ship_dock_metal_barrier');return a
  if raw==(49,49,49,49):return n(power,649,'gen1_port_complete_quay_barrier')
  # The Gen3 ship is a separately drawn large vessel; its complete pixels
  # cannot be squeezed into this128x48 background hull. User-approved palette
  # conversion keeps all original hull corners, portholes, ladders and wake.
  return f.source_palette([WATER if t==20 else STEEL for t in raw],'gen1_port_original_compact_ship_and_harbour_geometry')
 if raw==(1,1,1,1):return n(cabin,0,'gen1_ship_original_void')
 if raw==(13,29,29,13):return f.native(floor,'gen1_ship_native_cabin_floor')
 if raw==(4,4,4,4):return n(captain,664,'gen1_ship_native_timber_deck')
 if raw==(20,20,20,20):return water()
 if raw==(14,15,30,31):return n(cabin,641,'gen1_ship_complete_native_door')
 if raw==(16,16,18,19):return n(cabin,652,'gen1_ship_complete_wall_panel')
 if raw==(2,3,18,19):return n(cabin,826,'gen1_ship_complete_native_wall_clock')
 if raw==(70,71,86,87):return f.template('johto_lighthouse_complete_native_bed_head',floor)
 if raw==(86,87,86,87):return f.template('johto_lighthouse_complete_native_bed_foot',floor)
 if raw==(7,8,23,24):return f.template('household_chair_left',floor)
 if raw==(72,73,88,89):return n(kitchen,650,'gen1_ship_complete_trash_container')
 if raw in((39,40,55,56),(41,42,57,58)):return f.template('johto_gate_stairs_'+('up'if raw[0]==41 else'down'),floor)
 if raw in((9,12,54,43),(54,43,54,43)):return f.template('johto_domestic_complete_single_bay_bookcase_'+str(0 if raw[0]==9 else 1),floor)
 # Retain the whole32x32 native cooking range, including its four burners
 # and cabinet base. No quarter contains a detached/cropped circular burner.
 stove={(10,10,44,53):746,(10,10,53,44):747,(44,53,44,44):728,(53,44,44,44):729}
 if raw in stove:return n(kitchen,stove[raw],'gen1_ship_complete_native_four_burner_range')
 pots={(10,10,44,64):722,(10,10,65,44):723,(44,80,44,44):730,(81,44,26,44):731}
 if raw in pots:return f.source_palette(STEEL,'gen1_ship_original_complete_large_cooking_pots')
 tables={(25,64,25,80):720,(65,28,81,28):721,(25,44,25,44):728,(26,28,44,28):729}
 if raw in tables:return f.source_palette(STEEL,'gen1_ship_original_continuous_galley_bench_and_cookware')
 # These source modules combine a complete compact table/chair/clock in a
 # single16px cell or trace the unique8px deck/hull boundary. Preserve their
 # entire original geometry rather than cut a larger native object apart.
 boundary={1,5,6,17,21,22,32,33,34,35,37,38,45,48,49,50,51,61,74}
 if all(t in boundary or t==4 for t in raw):return f.source_palette(WOOD,'gen1_ship_original_narrow_deck_and_hull_frame')
 compact={(46,47,62,63),(36,36,52,52),(10,12,44,28),(2,3,9,10),(16,16,10,12),(25,26,11,11),(44,28,11,11),(86,87,59,60),(9,10,25,26),(25,44,11,59),(44,28,60,11),(32,16,48,19),(16,33,18,49),(16,16,84,85),(66,67,23,24),(9,10,25,44),(10,10,68,69),(25,44,59,60),(44,44,11,11),(44,28,59,60)}
 if raw in compact:return f.source_palette(STEEL,'gen1_ship_complete_compact_original_furniture_and_railings')
 return None
f.run(handle,('SS_ANNE_1F_ROOMS','SS_ANNE_2F_ROOMS','SS_ANNE_CAPTAINS_ROOM','SS_ANNE_KITCHEN','SS_ANNE_BOW','SS_ANNE_1F','VERMILION_DOCK','CERULEAN_BADGE_HOUSE'),'Direct complete native Gen3 cabin floors, doors, clocks, beds, chairs, shelves, kitchen ranges; the harbour and sea use checked native animated water. The original compact128x48 ship, narrow hull/deck joins continuous galley benches with all cookware, and combined16px cabin furniture preserve all their pixels in approved Gen3 colors where no complete native footprint fits without scaling or cropping features. Original captain/rubbing story, kitchen items, doors, collisions, stairs, ship departure and boarding behavior remain unchanged.')
