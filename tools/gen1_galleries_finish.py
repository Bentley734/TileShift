"""Celadon apartments and Pewter exhibits, using complete native Gen3 objects."""
from gen1_family_review import FamilyReview,cell_info
from native_room_parts import RoomParts
f=FamilyReview('galleries',{'MANSION','MUSEUM'});condo=RoomParts(f.imp,'firered','FR_CELADON_CITY_CONDOMINIUMS_1F');roof=RoomParts(f.imp,'firered','FR_CELADON_CITY_DEPARTMENT_STORE_ROOF');museum=RoomParts(f.imp,'firered','FR_PEWTER_CITY_MUSEUM_1F');museum2=RoomParts(f.imp,'firered','FR_PEWTER_CITY_MUSEUM_2F');ship=RoomParts(f.imp,'firered','FR_SSANNE_1F_ROOM1')
STONE=[[247,247,247],[189,206,214],[132,148,156],[66,74,107]]
TIMBER=[[247,239,206],[222,214,140],[181,173,99],[82,82,107]]
def n(r,mid,role):return f.native(r.ref(mid),role)
def at(c,x,y,m,data):
 if not 0<=x<m['width']*2 or not 0<=y<m['height']*2:return ()
 return tuple(cell_info(f.cache,c['game'],data,m['tileset'],m['blocks'][y//2*m['width']+x//2],y%2*2+x%2)['tiles'])
def middle_table(bottom,floor):
 parts=[]
 for role,sx,tx in(('household_table_sw'if bottom else'household_table_nw',8,0),('household_table_se'if bottom else'household_table_ne',0,8)):
  a=f.template(role)
  for p in a['parts']:
   px,py=p.get('x',0),p.get('y',0);ix,ex=max(px,sx),min(px+p['w'],sx+8)
   if ex>ix:
    z=dict(p);z.update(srcX=p.get('srcX',0)+ix-px,x=tx+ix-sx,w=ex-ix);parts.append(z)
 return f.composite(floor,parts,'gen1_mansion_complete_worktable_middle')
def handle(c,x,y,name,m,data):
 raw=tuple(c['tiles']);isroof=name=='CELADON_MANSION_ROOF';floor=roof.ref(648)if isroof else museum.ref(641)if c['tileset']=='MUSEUM'else condo.ref(641)
 if c['tileset']=='MUSEUM':
  if 1<=x<=4 and((name=='MUSEUM_1F'and y in(2,3,5,6))or(name=='MUSEUM_2F'and y in(4,5))):
   sy=48 if y in(2,5)and name=='MUSEUM_1F'else 64 if name=='MUSEUM_1F'else None
   if sy is not None:return f.composite(floor,museum.rect(48+(x-1)*16,sy,16,16),'gen1_museum_complete_native_fossil_case')
   mid=(728,729,730,731)[x-1]if y==4 else(736,737,738,739)[x-1];return n(museum2,mid,'gen1_museum_complete_native_moonstone_case')
  if name=='MUSEUM_2F'and 10<=x<=12 and y in(1,2):return n(museum2,(656,657,658)[x-10]if y==1 else(664,665,666)[x-10],'gen1_museum_complete_native_space_shuttle')
  if raw==(72,72,74,74):return n(museum,647,'gen1_museum_complete_wall_header')
  if raw==(23,24,23,24):return n(museum,709,'gen1_museum_complete_wall_pillar')
  if raw in((7,8,34,35),(34,35,34,35)):return f.template('johto_domestic_complete_single_bay_bookcase_'+str(0 if raw[0]==7 else 1),floor)
  if raw in((78,79,74,74),):return f.template('johto_complete_native_region_map',museum.ref(647))
  if raw==(72,72,7,8):return f.template('johto_domestic_complete_single_bay_bookcase_0',museum.ref(647))
  if raw==(5,6,21,22):return n(museum,685,'gen1_museum_native_palm_head')
  if raw==(37,38,53,54):return n(museum,694,'gen1_museum_native_palm_pot')
  if raw==(2,3,18,19):return f.template('johto_center_whole_lounge_chair',floor)
  if raw in((12,13,28,29),(10,11,26,27)):return f.template('johto_gate_stairs_'+('up'if raw[0]==12 else'down'),floor)
  if raw==(4,4,20,20):return f.template('household_rug_left'if at(c,x-1,y,m,data)!=raw else'household_rug_right',floor)
  if raw==(76,77,92,93):return f.source_palette(STONE,'gen1_museum_original_amber_pedestal')
  if raw in((23,24,50,51),(9,9,50,51),(9,8,50,51),(7,8,23,24)):return n(museum,662,'gen1_museum_complete_native_counter')
 if c['tileset']=='MANSION':
  if name=='CELADON_MANSION_2F'and 0<=x<=1 and 5<=y<=6:return f.template('johto_pokecom_complete_admin_computer_'+str(x)+'_'+str(y-5),floor)
  if raw in((36,37,64,65),(52,53,66,67)):return f.template('johto_pokecom_complete_admin_computer_'+str(0 if raw[0]==36 else 1)+'_0',floor)
  if raw in((2,3,18,19),(85,86,17,17))and at(c,x,y-1,m,data)in((36,37,64,65),(52,53,66,67)):return f.template('johto_pokecom_complete_admin_computer_'+str(0 if raw[0]==2 else 1)+'_1',floor)
  if isroof and 1<=x<=3 and 4<=y<=8:return f.source_palette(STONE,'gen1_mansion_intact_rooftop_shack')
  if raw==(1,1,1,1):return f.native(floor,'gen1_mansion_rooftop_paving')
  if raw==(17,17,17,17):return f.native(floor,'gen1_mansion_native_carpet')
  if raw==(16,16,16,16):return n(condo,0,'gen1_mansion_original_void')
  if raw in((80,80,80,80),(80,80,38,41)):return n(condo,649,'gen1_mansion_complete_wall_header')
  if raw in((74,75,74,75),(74,75,90,91)):return n(roof,822 if raw[2]==74 else 851,'gen1_mansion_rooftop_balustrade')
  if raw in((76,76,30,30),(78,79,74,75),(44,79,74,75),(44,92,74,75)):return f.source_palette(STONE,'gen1_mansion_original_rooftop_corner_and_rim')
  if raw in((38,41,34,35),(76,76,38,41)):return f.template('johto_domestic_complete_single_bay_bookcase_0',floor)
  if raw in((34,35,50,51),):return f.template('johto_domestic_complete_single_bay_bookcase_1',floor)
  if raw in((38,41,40,21),(56,87,50,51)):return f.source_palette(STONE,'gen1_mansion_original_cabinet_ornament')
  if raw==(68,69,8,9):return n(condo,713,'gen1_mansion_native_palm_head')
  if raw==(70,71,24,25):return n(condo,720,'gen1_mansion_native_palm_pot')
  if raw==(45,46,61,62):return f.template('johto_lighthouse_complete_native_bed_head',floor)
  if raw==(61,62,63,47):return f.template('johto_lighthouse_complete_native_bed_foot',floor)
  if raw==(72,73,88,89):return f.source_palette(STONE,'gen1_mansion_original_complete_framed_wall_fitting')
  if raw in((12,13,28,29),(10,11,26,27)):return f.template('johto_gate_stairs_'+('up'if raw[0]==12 else'down'),floor)
  if raw==(4,4,20,20):return f.template('household_rug_left'if at(c,x-1,y,m,data)!=raw else'household_rug_right',floor)
  if raw==(17,17,5,5):return f.template('johto_gate_complete_north_doorway',floor)
  if raw in((76,76,22,23),(76,77,30,93)):return f.source_palette(STONE,'gen1_mansion_complete_reception_window_frame')
  if raw in((38,39,54,55),(39,41,55,57)):return f.template('household_table_nw'if raw[0]==38 else'household_table_ne',floor)
  if raw==(39,39,55,55):return middle_table(False,floor)
  if raw in((54,55,60,58),(55,57,58,59)):return f.template('household_table_sw'if raw[0]==54 else'household_table_se',floor)
  if raw==(55,55,58,58):return middle_table(True,floor)
  if raw in((2,3,18,19),):return f.template('household_chair_left',floor)
  if raw==(85,86,17,17):return f.native(floor,'gen1_mansion_floor_beneath_computer')
  if raw==(81,82,83,84):return f.source_palette(STONE,'gen1_mansion_original_complete_door_and_handle')
  if isroof:return f.source_palette(STONE,'gen1_mansion_original_roof_planter_and_boundary_details')
 return None
f.run(handle,('CELADON_MANSION_1F','CELADON_MANSION_2F','CELADON_MANSION_ROOF','CELADON_CHIEF_HOUSE','MUSEUM_1F','MUSEUM_2F'),'Complete native Gen3 apartment furniture, carpet, palms, PCs and museum cases/rocket. Native displays keep their full64x32 or48x32 footprints without scaling or removing frame corners. The compact original rooftop shack, thin balustrade joins, service window and scientific pedestal retain exact source geometry in approved Gen3 tones where no intact native shape fits. Original stairs, doors, source collisions, exhibits, story objects and computer interactions remain unchanged.')
