"""Direct native Gen3 shop and department-store tile counterparts."""
import copy
from johto_family_review import FamilyReview
from native_room_parts import RoomParts
import gen2_extended_review as e
f=FamilyReview('mart',{'TILESET_MART'})
mart=RoomParts(f.imp,'firered','FR_VIRIDIAN_CITY_MART')
dept=RoomParts(f.imp,'firered','FR_CELADON_CITY_DEPARTMENT_STORE_1F')
roof=RoomParts(f.imp,'firered','FR_CELADON_CITY_DEPARTMENT_STORE_ROOF')
gate=RoomParts(f.imp,'firered','FR_ROUTE_5_SOUTH_ENTRANCE')
power=RoomParts(f.imp,'firered','FR_POWER_PLANT')
for r in f.active:
 if r['game']=='red'and r['role'].startswith('household_'):f.templates.setdefault(r['role'],r)
def n(room,mid,role):return f.native(room.ref(mid),'johto_shop_'+role)
def tile(room,sx,sy,base,role):return f.composite(base,room.rect(sx,sy,16,16),'johto_shop_'+role)
def shared(role,base):
 r=f.template(role,base);r['role']='johto_shop_'+role;return r
def handle(c,x,y,name,m,data):
 raw=tuple(c['tiles']);floor=roof.ref(696)if name.endswith('_ROOF')else mart.ref(641)if name.endswith('_MART')else dept.ref(704);wall=mart.ref(645)if name.endswith('_MART')else dept.ref(643)
 if raw in((145,145,145,145),(200,201,216,145),(202,203,145,145)):return f.native(floor,'johto_shop_complete_floor')
 if raw==(14,15,28,29):return shared('johto_house_complete_window',wall)
 if raw==(14,15,42,43):return shared('johto_house_complete_window',wall)
 shelves={(64,65,80,81):(112,16),(66,43,82,69):(144,16),(67,68,83,84):(112,32),(92,93,31,85):(144,32),(12,13,80,81):(112,16),(80,81,94,95):(112,32)}
 if raw in shelves:return tile(mart,*shelves[raw],floor,'complete_stock_display')
 if raw in((12,13,86,87),(88,89,90,91)):
  return tile(mart,64,0 if raw[0]==12 else 16,floor,'complete_window_'+str(int(raw[0]!=12)))
 if raw in((38,39,54,55),(40,41,56,57)):
  return tile(mart,112,64 if raw[0]==38 else 96,floor,'stock_shelf_'+str(int(raw[0]!=38)))
 if raw==(62,63,62,63):return n(mart,677,'sales_counter_top')
 if raw==(32,33,48,49):return f.original('assets/original/interior-computer/computer.png',mart.ref(677),'johto_shop_complete_checkout_register')
 if raw==(17,17,42,43):return f.native(wall,'johto_shop_counter_back')
 if raw in((59,59,26,26),(30,30,26,26)):return n(mart,688,'sales_counter_front')
 if raw in((46,30,24,26),(42,59,62,63)):return n(mart,688,'sales_counter_left_end')
 if raw in((30,47,26,25),(59,43,62,63)):return n(mart,690,'sales_counter_right_end')
 if raw==(11,11,27,27):
  right=x>0 and tuple(e.cell_info(f.cache,c['game'],data,m['tileset'],m['blocks'][y//2*m['width']+(x-1)//2],y%2*2+(x-1)%2)['tiles'])==raw
  return shared('household_rug_right'if right else'household_rug_left',floor)
 if raw in((6,7,22,23),):
  parts=gate.rect(56,10,8,5)+gate.rect(80,10,8,5,8,0)+gate.rect(56,21,8,11,0,5)+gate.rect(80,21,8,11,8,5)
  return f.composite(floor,parts,'johto_shop_complete_lift_entry_frame')
 if raw in((10,17,73,73),(17,10,73,73)):return tile(dept,80,16,wall,'lift_call_panel')
 if raw==(44,45,60,61):return tile(dept,128,16,wall,'complete_floor_directory')
 if raw in((4,5,20,21),(2,3,18,19),(135,136,151,152)):
  up=raw[0]==4
  return f.original('assets/original/interior-stairs/'+('up.png'if up else'down.png'),floor,'johto_shop_stairs_'+('up'if up else'down'))
 if raw==(27,27,1,1):return f.native(floor,'johto_shop_floor_at_lift')
 if raw in((74,75,8,9),(137,138,167,168)):
  return tile(mart,16,16 if raw[0]==74 else 32,floor,'complete_potted_plant')
 if raw in((8,9,8,9),(8,9,24,25)):
  return tile(mart,16,16 if raw[2]==8 else 32,floor,'complete_potted_plant')
 if raw in((34,35,50,51),(36,37,52,53),(36,37,139,140)):
  # Native roof seating is a whole16x32 seat; only surrounding native table
  # background is excluded, preserving the entire chair frame and cushion.
  sy=80 if raw[0]==34 else 96
  return tile(roof,48,sy,floor,'complete_lounge_seat')
 if raw in((12,13,76,77),(76,77,78,79)):
  return tile(roof,160,32 if raw[0]==12 else 48,floor,'complete_vending_machine')
 if raw in((58,58,58,58),(1,1,70,58),(1,1,58,71),(70,58,70,58),(58,71,58,71)):
  return f.native(floor,'johto_shop_customer_floor_border')
 if raw in((62,63,12,13),(58,58,12,13)):return n(mart,688,'sales_counter_front_rail')
 # Roof parapets retain all original source collision and sky boundaries.
 if raw in((129,129,145,145),):return n(roof,826,'roof_north_parapet')
 if raw in((129,130,145,146),):return n(roof,842,'roof_north_east_parapet')
 if raw==(144,145,144,145):return tile(roof,16,64,floor,'roof_west_parapet')
 if raw==(145,146,145,146):return tile(roof,288,64,floor,'roof_east_parapet')
 if raw in((161,161,150,150),(160,161,150,150),(161,162,150,150)):
  return tile(roof,16 if raw[0]==160 else 288 if raw[1]==162 else 64,144,floor,'roof_south_parapet')
 if raw in((131,132,147,148),(133,134,148,149)):
  return f.original('assets/original/interior-planter/planter.png',floor,'johto_shop_complete_roof_planter')
 if raw==(153,154,169,170):return f.native(power.ref(753),'johto_shop_roof_ventilation_grille')
 if raw in((192,193,208,209),(194,195,210,211)):
  return tile(roof,144 if raw[0]==192 else 160,32,floor,'roof_vending_equipment_top')
 if raw in((196,197,212,213),(198,199,214,215)):
  return f.original('assets/original/interior-planter/planter.png',floor,'johto_shop_complete_roof_planter')
 if raw==(217,218,219,220):return tile(roof,160,48,floor,'roof_vending_equipment_base')
 # Native Celadon skylight end frames and repeatable glass modules.
 skylight={(155,129,171,141):756,(129,129,142,142):757,(129,156,142,172):758,(171,158,171,158):764,(158,158,1,1):765,(158,172,1,172):766}
 if raw in skylight:return f.native(roof.ref(skylight[raw]),'johto_shop_complete_roof_skylight')
 if raw in((174,175,145,145),(175,175,145,145),(175,173,145,145)):return f.native(floor,'johto_shop_floor_below_skylight')
 return None
f.run(handle,('AZALEA_MART','GOLDENROD_DEPT_STORE_1F','GOLDENROD_DEPT_STORE_2F','GOLDENROD_DEPT_STORE_5F','GOLDENROD_DEPT_STORE_6F','GOLDENROD_DEPT_STORE_ROOF','GOLDENROD_DEPT_STORE_ELEVATOR'),'Existing native FireRed Marts and department-store stock shelves, checkout register, counters, windows, directory, roof seating, vending machines, parapets and shelter modules retain their native pixel scale. Source shops, vendors, elevator destinations, stairs, roof interactions, events and collision remain unchanged. Narrow source stock displays use complete native left/right end modules; no unique machine caps or shelf feet are omitted.')
