"""Native Gen3 shop, department store, arcade, diner and lift counterparts."""
from gen1_family_review import FamilyReview,cell_info,source,GAMES
from native_room_parts import RoomParts
from gen1_center_finish import center_art,floor as center_floor
from gen1_native_plant import native_plant_parts
import preview
f=FamilyReview('commercial',{'MART','LOBBY'})
mart=RoomParts(f.imp,'firered','FR_VIRIDIAN_CITY_MART');dept=RoomParts(f.imp,'firered','FR_CELADON_CITY_DEPARTMENT_STORE_1F');roof=RoomParts(f.imp,'firered','FR_CELADON_CITY_DEPARTMENT_STORE_ROOF');cafe=RoomParts(f.imp,'firered','FR_CELADON_CITY_RESTAURANT');arcade=RoomParts(f.imp,'firered','FR_CELADON_CITY_GAME_CORNER');lift=RoomParts(f.imp,'firered','FR_CELADON_CITY_DEPARTMENT_STORE_ELEVATOR');gate=RoomParts(f.imp,'firered','FR_ROUTE_11_EAST_ENTRANCE_2F')
north=RoomParts(f.imp,'firered','FR_ROUTE_5_SOUTH_ENTRANCE')
cafe_bg=set()
for mid in(689,708,709,724):cafe_bg.update(preview.native_donor(f.cache,cafe.ref(mid),f.packed).get_flattened_data())
STEEL=[[248,240,208],[168,192,200],[88,128,152],[32,48,72]]
def n(room,mid,role):return f.native(room.ref(mid),'gen1_commercial_'+role)
def tile(room,sx,sy,base,role):return f.composite(base,room.rect(sx,sy,16,16),'gen1_commercial_'+role)
def shared(role,base):
 r=f.template(role,base);r['role']='gen1_commercial_'+role;return r
mart_bg=set()
for mid in(641,642,643,644,650,651,652):mart_bg.update(preview.native_donor(f.cache,mart.ref(mid),f.packed).get_flattened_data())
def stock(sx,sy,base,role):
 # Remove only the connected native shop floor outside the whole fixture.
 outside=mart.exterior(sx,sy,16,16,mart_bg)
 return f.composite(base,mart.masked(sx,sy,list(range(16)),list(range(16)),transparent_pixels=outside),'gen1_commercial_'+role)
def counter(base,role,front=False,right=False):
 if front:return f.composite(base,[{'donor':mart.ref(690 if right else 688),'w':16,'h':16}],'gen1_commercial_'+role)
 # The native checkout has a removable paper pad. Repeating its blank blue
 # surface keeps long counters free of repeated pads and intact side rails.
 return f.composite(base,[{'donor':mart.ref(677),'srcY':8,'w':16,'h':8},{'donor':mart.ref(677),'srcY':8,'w':16,'h':8,'y':8}],'gen1_commercial_'+role)
def same(c,x,y,m,data,dx,raw):
 xx=x+dx
 return 0<=xx<m['width']*2 and tuple(cell_info(f.cache,c['game'],data,m['tileset'],m['blocks'][y//2*m['width']+xx//2],y%2*2+xx%2)['tiles'])==raw
def handle(c,x,y,name,m,data):
 raw=tuple(c['tiles']);isroof=name.endswith('_ROOF');isarcade=name=='GAME_CORNER';isdiner=name=='CELADON_DINER';islift=name.endswith('_ELEVATOR')
 if c['tileset']=='MART':
  floor=center_floor if name=='INDIGO_PLATEAU_LOBBY'else mart.ref(641)
  if name=='INDIGO_PLATEAU_LOBBY':
   if raw in((32,33,48,49),(34,35,50,51)):
    return f.composite(center_floor,native_plant_parts(f.imp,raw[0]==32),'gen1_commercial_complete_native_plant_'+('head'if raw[0]==32 else'pot'))
   r=center_art(c,x,y,name,m,data)
   if r:return r
  if raw in((1,11,17,27),(54,11,26,27)):return f.native(floor,'gen1_commercial_mart_floor')
  if raw in((40,40,78,79),(76,77,23,29)):
   return tile(mart,112+x%2*32,0 if raw[0]==40 else 16,floor,'complete_back_wall_stock_case')
  if raw in((90,91,44,45),(46,47,62,63)):
   # Keep the left and right frames and repeat only the center glass module.
   left=not same(c,x,y,m,data,-1,raw);right=not same(c,x,y,m,data,1,raw)
   return tile(mart,64 if left else 96 if right else 80,0 if raw[0]==90 else 16,floor,'complete_glazing_'+str(int(raw[0]==46)))
  shelves={(64,65,80,81):(112,64),(65,67,81,83):(128,64),(68,69,84,85):(112,96),(69,71,85,87):(128,96)}
  if raw in shelves:return stock(*shelves[raw],floor,'complete_stock_case_head_and_feet')
  if raw==(12,12,28,28):return shared('household_rug_right'if same(c,x,y,m,data,-1,raw)else'household_rug_left',floor)
  if raw==(0,0,0,0):return n(mart,0,'outside_void')
  if raw in((40,40,40,40),(90,91,40,40),(90,91,20,40)):return n(mart,645,'full_back_wall')
  if raw in((40,89,16,41),(16,41,16,41)):return counter(floor,'sales_counter_top')
  if raw==(14,15,30,31):return f.original('assets/original/interior-computer/computer.png',mart.ref(677),'gen1_commercial_complete_checkout_register')
  if raw==(56,8,25,24):return n(mart,688,'complete_counter_left_front')
  if raw==(16,41,25,24):return n(mart,690,'complete_counter_right_front')
  if raw==(90,91,25,24):return n(mart,690,'complete_counter_right_front_below_wall')
  return None
 floor=roof.ref(696)if isroof else arcade.ref(658)if isarcade else cafe.ref(709)if isdiner else lift.ref(758)if islift else dept.ref(704)
 if isarcade:
  # Whole32px slot-machine banks. Only their repeating body sections are
  # extended vertically; the distinctive head, sides and feet remain intact.
  if raw in((38,41,54,57),(54,57,54,57),(75,76,75,76),(75,76,77,78)):
   right=x%6==1
   return n(arcade,(681 if right else 680)if raw[0]==38 else(705 if right else 704)if raw[2]==77 else(697 if right else 696),'complete_slot_bank_'+('head'if raw[0]==38 else'foot'if raw[2]==77 else'body'))
  if raw==(7,8,23,24):return n(arcade,682 if x%6==2 else 683,'complete_native_arcade_chair')
 if raw==(79,79,79,79):return n(roof,855,'native_rooftop_sky')
 if raw==(55,69,69,55):return f.native(floor,'gen1_commercial_native_context_floor')
 if raw==(32,32,32,32):return n(cafe,719,'native_kitchen_floor')if isdiner else f.native(floor,'gen1_commercial_floor_below_desks')
 if raw==(1,1,1,1):return n(roof,830,'native_rooftop_stair_housing_wall')if isroof else n(cafe,693,'diner_north_wall')if isdiner else n(dept,643 if y==0 else 651,'complete_department_wall')
 if raw==(1,1,33,33):return n(roof,838,'native_rooftop_stair_housing_base')if isroof else n(lift,756,'native_lift_wall')if islift else n(cafe,701,'diner_lower_wall')if isdiner else n(dept,651,'lower_department_wall')
 if raw in((55,55,55,55),(55,55,91,91)):
  return n(roof,823 if raw[2]==55 else 830,'native_rooftop_stair_housing')if isroof else n(arcade,649,'prize_room_back_wall')
 if raw==(92,92,93,93):return n(lift,744,'complete_elevator_wall_cap')
 if raw==(4,4,20,20):return shared('household_rug_right'if same(c,x,y,m,data,-1,raw)else'household_rug_left',floor)
 if raw==(7,8,23,24):
  sx,sy=(48,48)if isroof and x in(6,10)else(144,48)
  outside=cafe.exterior(sx,sy,16,16,cafe_bg)
  return f.composite(floor,cafe.masked(sx,sy,list(range(16)),list(range(16)),transparent_pixels=outside),'gen1_commercial_complete_chair_over_context_floor')
 if raw in((68,68,84,84),(79,76,79,76),(75,79,75,79)):
  return n(roof,833 if y==0 else 826,'complete_roof_parapet')if raw[0]==68 else tile(roof,16 if raw[0]==79 else 288,64,floor,'complete_side_parapet')
 if raw==(75,76,75,76):return n(lift,756,'complete_lift_side_wall')
 if raw==(40,40,56,56):
  parts=north.rect(56,10,8,5)+north.rect(80,10,8,5,8,0)+north.rect(56,21,8,11,0,5)+north.rect(80,21,8,11,8,5)
  return f.composite(floor,parts,'gen1_commercial_complete_native_lift_entry_frame')
 if raw in((6,1,22,33),(62,1,63,33),(1,62,33,63)):
  return tile(dept,80,16,dept.ref(651),'complete_lift_call_panel')if not islift else n(lift,755,'complete_interior_lift_control')
 if raw in((10,11,26,27),(12,13,28,29)):
  # The hidden arcade stair has the same whole source stair silhouette.
  return f.original('assets/original/interior-stairs/'+('down'if raw[0]==10 else'up')+'.png',floor,'gen1_commercial_complete_stairs')
 if raw==(46,47,33,33):return tile(dept,128,16,dept.ref(651),'complete_department_directory')
 if raw==(2,3,18,19):return f.source_palette(STEEL,'gen1_commercial_complete_compact_public_telephone')
 if raw==(72,73,88,89):return f.source_palette([[248,240,208],[224,168,88],[160,104,96],[48,56,80]],'gen1_commercial_complete_compact_wall_poster')
 if raw in((14,15,30,31),(34,35,50,51),(38,41,34,35)):
  if isroof:return tile(roof,160,48 if raw[0]==34 else 32,floor,'whole_native_roof_vending_machine')
  if name=='CELADON_MART_3F':return shared('johto_complete_pc_'+('1'if raw[0]==34 else'0'),floor)
  return shared('johto_domestic_complete_single_bay_bookcase_'+('1'if raw[0]==34 else'0'),floor)
 shelves={(42,43,58,59):(112,16),(44,45,60,61):(144,16),(64,65,80,81):(112,32),(66,67,82,83):(144,32)}
 if raw in shelves:
  if isarcade:return tile(arcade,32+x%2*16,0 if raw[0]in(42,44)else 16,floor,'whole_native_prize_display')
  return stock(*shelves[raw],floor,'complete_department_stock_display')
 tables={(9,39,54,55):0,(39,25,55,57):1,(70,55,85,86):2,(55,71,87,55):3}
 if raw in tables:
  q=tables[raw];return tile(cafe,16+q%2*16,112+q//2*16,floor,'whole_native_cafe_table_'+str(q))
 if raw==(36,37,52,53):return f.original('assets/original/interior-computer/computer.png',mart.ref(677),'gen1_commercial_complete_department_computer')
 if raw==(55,55,10,11):return n(arcade,645,'complete_prize_display_header')
 if raw==(1,1,38,41):
  return n(cafe,728,'complete_diner_counter_cap')if isdiner else counter(floor,'complete_sales_counter_cap')
 if raw==(54,57,54,57):return n(cafe,736,'complete_diner_counter_surface')if isdiner else counter(floor,'complete_sales_counter_surface')
 if raw in((39,39,21,21),(38,39,48,21),(39,41,21,49),(39,41,21,21),(46,47,21,49)):
  return n(cafe,737 if raw[0]==38 else 740 if raw[1]==41 else 738,'complete_diner_counter_front')if isdiner else n(mart,688 if raw[0]==38 else 690 if raw[1]==41 else 689,'complete_sales_counter_front')
 if raw in((21,21,32,32),(48,21,32,32),(21,49,32,32)):
  return n(mart,688 if raw[0]==48 else 690 if raw[1]==49 else 689,'complete_computer_desk_front')
 if raw in((38,41,54,57),(39,41,54,57),(38,39,54,57),(39,39,55,55)):
  if isroof:return n(roof,822,'complete_stair_housing_left_edge')
  return counter(floor,'complete_native_counter_top')
 return None
if __name__=='__main__':
 # Older broad interior recipes confused machine banks and counters. Replace
 # those exact reviewed source shapes as positioned rows in this family.
 for game in GAMES:
  data=source(f.cache,game)
  for name,m in data['maps'].items():
   if not isinstance(m,dict)or m.get('tileset')not in f.tilesets:continue
   for y in range(m['height']*2):
    for x in range(m['width']*2):
     c=cell_info(f.cache,game,data,m['tileset'],m['blocks'][y//2*m['width']+x//2],y%2*2+x%2)
     if handle(c,x,y,name,m,data):f.overrides.add((game,name,x,y))
 f.run(handle,('CINNABAR_MART','INDIGO_PLATEAU_LOBBY','CELADON_MART_2F','CELADON_MART_3F','CELADON_MART_ROOF','CELADON_DINER','GAME_CORNER','GAME_CORNER_PRIZE_ROOM','CELADON_MART_ELEVATOR'),'Direct native Gen3 stock cases, glazing frames, checkout counters, whole potted plants, healing units, chairs, complete cafe tables, native slot-machine bank heads/sides/feet, department fixtures, stairs and lift controls. Repeatable blank display rows and slot-bank body sections alone may repeat or be omitted; complete native product-display ends and machine details remain unscaled. Compact original telephones and posters retain all source pixels in native Gen3 color ramps; lift doors use complete native entry frames. Every source shop interaction, slot direction and payment event, counter flag, source walkability, warp and original layout stays unchanged.')
