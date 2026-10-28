"""Complete native Gen3 home furniture and actual Cerulean damage counterparts."""
import copy
from collections import Counter
from gen1_family_review import FamilyReview,ROOT,GAMES,source,cell_info
from native_room_parts import RoomParts
import preview
f=FamilyReview('domestic',{'HOUSE','REDS_HOUSE_1','REDS_HOUSE_2'})
house=RoomParts(f.imp,'firered','FR_RIVALS_HOUSE');lab=RoomParts(f.imp,'firered','FR_OAKS_LAB');broken=RoomParts(f.imp,'firered','FR_CERULEAN_CITY_HOUSE2');roof=RoomParts(f.imp,'firered','FR_CELADON_CITY_CONDOMINIUMS_ROOF_ROOM')
floor=house.ref(1);wall=house.ref(40)
damaged=f.imp.gba('firered',broken.map)[0];roofimage=f.imp.gba('firered',roof.map)[0]
plainwood=set(preview.native_donor(f.cache,broken.ref(265),f.packed).get_flattened_data());woodcolors=plainwood|set(preview.native_donor(f.cache,broken.ref(273),f.packed).get_flattened_data())
carpet=Counter(damaged.crop((32,48,96,112)).get_flattened_data()).most_common(1)[0][0];tablemask=broken.exterior(48,64,32,32,woodcolors|{carpet});plantmask=broken.exterior(128,96,32,32,woodcolors)
roofcolors=set(roofimage.crop((16,64,32,80)).get_flattened_data());booktablemask=roof.exterior(64,56,32,32,roofcolors)
footprints={55:(112,48),40:(120,53)}
for sx,sy in footprints.values():assert sum(damaged.getpixel((sx+x,sy+y))not in plainwood for y in range(8)for x in range(8))==32
for game in GAMES:
 for name in('CERULEAN_TRASHED_HOUSE','CELADON_MANSION_ROOF_HOUSE'):
  for y in(3,4):
   for x in(3,4):f.overrides.add((game,name,x,y))

def template(role,base=None):return f.template(role,base)
def tablepart(room,sx,sy,outside,q,role):
 return f.composite(floor,room.masked(sx+q%2*16,sy+q//2*16,list(range(16)),list(range(16)),transparent_pixels=outside),role)
def scarred_floor(raw):
 parts=[]
 for i,t in enumerate(raw):
  if t in(55,40):
   sx,sy=footprints[t]
   parts+=broken.masked(sx,sy,list(range(8)),list(range(8)),i%2*8,i//2*8,background=plainwood)
  elif t!=1:return None
 return f.composite(floor,parts,'gen1_complete_native_robbed_house_footprints')if parts else f.native(floor,'gen1_house_native_floor')

def handle(c,x,y,name,m,data):
 raw=tuple(c['tiles'])
 if name=='CERULEAN_TRASHED_HOUSE'and 3<=x<=4 and 3<=y<=4:return tablepart(broken,48,64,tablemask,(y-3)*2+x-3,'gen1_complete_native_damaged_table')
 if name=='CELADON_MANSION_ROOF_HOUSE'and 3<=x<=4 and 3<=y<=4:return tablepart(roof,64,56,booktablemask,(y-3)*2+x-3,'gen1_complete_native_book_table')
 if m['tileset']=='HOUSE':
  if set(raw)<={1,40,55}:return scarred_floor(raw)
  if raw==(2,3,18,19):return template('johto_house_chair_left'if x<=3 else'johto_house_chair_right',floor)
  if raw==(28,29,68,69):
   mid=674 if x<3 else 667;layout=broken.layout;pos=next(i for i,v in enumerate(layout['mids'])if v==mid);sx,sy=pos%layout['width']*16,pos//layout['width']*16;outside=broken.exterior(sx,sy,16,16,woodcolors|{carpet})
   return f.composite(floor,broken.masked(sx,sy,list(range(16)),list(range(16)),transparent_pixels=outside),'gen1_complete_native_tipped_chair')
  if raw in((42,43,12,13),(44,37,53,56)):
   return f.composite(floor,broken.masked(128 if raw[0]==42 else 144,106,list(range(16)),list(range(16)),transparent_pixels=plantmask),'gen1_whole_native_fallen_plant')
  if raw in((0,63,63,0),(35,74,84,85),(72,73,88,89),(73,75,90,91)):
   return f.source_palette([[240,248,232],[184,208,192],[104,136,128],[40,64,64]],'gen1_original_wall_damage_and_opening')
  # Whole ordinary table quadrants without the special book/damage context.
  table={(38,39,54,47):0,(39,41,47,57):1,(80,81,82,83):2,(47,57,58,59):3,(38,39,70,71):0,(86,87,60,58):2}
  if raw in table:return template(('household_table_nw','household_table_ne','household_table_sw','household_table_se')[table[raw]],floor)
  if raw==(34,1,1,34):return f.source_palette([[240,232,200],[184,168,120],[112,96,72],[48,48,48]],'gen1_original_small_scattered_house_objects')
 if m['tileset']=='REDS_HOUSE_2':
  if raw in((64,65,32,33),(66,67,50,51)):return template('johto_complete_pc_'+('0'if raw[0]==64 else'1'),wall if raw[0]==64 else floor)
  table={(0,0,38,39):0,(0,0,39,41):1,(44,42,60,58):2,(42,43,58,59):3}
  if raw in table:return template(('household_table_nw','household_table_ne','household_table_sw','household_table_se')[table[raw]],wall if table[raw]<2 else floor)
  if raw==(10,11,26,27):return f.original('assets/original/interior-stairs/down.png',floor,'gen1_home_stairs_down')
  if raw in((45,46,61,62),(61,62,63,47)):return template('johto_lighthouse_complete_native_bed_'+('head'if raw[0]==45 else'foot'),floor)
  if raw==(14,15,30,31):return f.source_palette([[240,232,208],[176,176,160],[104,112,112],[40,48,64]],'gen1_original_complete_handheld_and_cord')
 return None
if __name__=='__main__':f.run(handle,('DAYCARE','CERULEAN_TRASHED_HOUSE','CELADON_MANSION_ROOF_HOUSE','COPYCATS_HOUSE_2F','REDS_HOUSE_2F'),'Complete native Gen3 house, study, bed, monitor, table and actual FireRed Cerulean robbed-house counterparts. Footprints use full native8px shoe marks over matching reviewed floor; fallen plant retains its complete27x15 native silhouette in32x16 source cells. Damaged table, tips and book table preserve all native caps, legs, books and unique damage at1:1 pixels. Compact original wall cracks/opening and handheld-with-cord retain their complete original geometry with native Gen3 color ramps. Existing furniture, interactions, Red/Blue/Yellow scripts, source movement flags, exits and warps remain unchanged.')
