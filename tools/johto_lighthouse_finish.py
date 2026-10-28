"""Explicit complete Olivine interior surfaces, furniture and beacon."""
from johto_family_review import FamilyReview
from native_room_parts import RoomParts
import preview
f=FamilyReview('lighthouse',{'TILESET_LIGHTHOUSE'});museum=RoomParts(f.imp,'firered','FR_PEWTER_CITY_MUSEUM_1F');power=RoomParts(f.imp,'firered','FR_POWER_PLANT');ship=RoomParts(f.imp,'firered','FR_SSANNE_1F_ROOM1');floor=museum.ref(642);wall=power.ref(649);patch=f.templates['interior_shiproom_floor']['donor']
# The complete native single bunk is20x26. Four identical blank mattress
# columns are omitted; pillow, frame, corners and foot remain at native scale.
native_bed=f.imp.gba('firered',ship.map)[0];bed=native_bed.crop((62,83,82,109));columns=list(range(8))+list(range(12,20));background=set(native_bed.crop((16,48,32,64)).get_flattened_data())
for x in range(8,12):assert bed.crop((x,0,x+1,26)).tobytes()==bed.crop((8,0,9,26)).tobytes()
bedparts=[ship.masked(62,83,columns,list(range(10)),0,6,background),ship.masked(62,83,columns,list(range(10,26)),background=background)]
def handle(c,x,y,name,m,data):
 raw=tuple(c['tiles']);col=c['collision']
 if raw==(94,95,74,75):return f.native(wall,'johto_lighthouse_stone_wall')
 if raw==(46,47,47,46):return f.native(floor,'johto_lighthouse_stone_floor')
 if raw==(1,1,1,1)and col==96:return f.native(power.ref(0),'johto_lighthouse_original_fall_void')
 if raw==(90,91,76,77):return f.original('assets/original/interior-planter/planter.png',floor,'johto_lighthouse_low_planter')
 if raw==(78,78,76,77):
  r=f.template('johto_house_complete_window',wall);r['parts']=r['parts'][1:];r['role']='johto_lighthouse_complete_window';return r
 if raw in((41,42,57,58),(39,40,55,56)):
  return f.original('assets/original/interior-stairs/'+('up.png'if raw[0]==41 else'down.png'),floor,'johto_lighthouse_stairs_'+('up'if raw[0]==41 else'down'))
 if raw==(36,36,52,52):return f.template('johto_house_entry_rug',floor)
 if raw in((70,71,86,87),(131,132,133,134),(86,87,59,60)):return f.composite(patch,bedparts[0 if raw[0]==70 else 1],'johto_lighthouse_complete_native_bed_'+('head'if raw[0]==70 else'foot'))
 if raw==(7,8,23,24):return f.template('johto_house_chair_left',patch)
 beacon={(9,10,25,26):(0,0),(10,12,44,28):(1,0),(25,64,25,80):(0,1),(65,28,81,28):(1,1),(20,130,11,128):(0,2),(130,53,129,11):(1,2),(20,44,11,59):(0,2),(44,53,60,11):(1,2)}
 if raw in beacon:
  xx,yy=beacon[raw];return f.original('assets/original/interior-beacon/cell-'+str(xx)+'-'+str(yy)+'.png',patch,'johto_lighthouse_complete_beacon_'+str(xx)+'_'+str(yy))
 return None
f.run(handle,('OLIVINE_LIGHTHOUSE_1F','OLIVINE_LIGHTHOUSE_2F','OLIVINE_LIGHTHOUSE_6F'),'Complete native Gen3 gray stone floor, structural wall, window, stair, seating and bed counterparts reviewed in the actual Olivine floor plans. Native bunk retains its pillow, complete frame and foot; only four identical blank mattress columns are omitted. Original compact beacon and planters are independently created Gen3 artwork. All source fall holes, stair destinations, NPC/Ampharos events, lighting, collision and original warp coordinates remain unchanged.')
