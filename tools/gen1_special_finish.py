"""Native Sea Cottage pods and room-specific Gen3 social/link-room artwork."""
from gen1_family_review import FamilyReview,ROOT,GAMES,source,cell_info
from native_room_parts import RoomParts
from gen1_native_plant import native_plant_parts
f=FamilyReview('special',{'CLUB','INTERIOR','BEACH_HOUSE'})
cottage=RoomParts(f.imp,'firered','FR_ROUTE_25_SEA_COTTAGE');fan=RoomParts(f.imp,'firered','FR_VERMILION_CITY_POKEMON_FAN_CLUB');office=RoomParts(f.imp,'firered','FR_SILPH_CO_1F');shop=RoomParts(f.imp,'firered','FR_CERULEAN_CITY_BIKE_SHOP');gate=RoomParts(f.imp,'firered','FR_ROUTE_5_SOUTH_ENTRANCE');saffron=RoomParts(f.imp,'firered','FR_SAFFRON_CITY_GYM');house=RoomParts(f.imp,'firered','FR_RIVALS_HOUSE')
cfloor=cottage.ref(cottage.layout['mids'][7*cottage.layout['width']+8]);ffloor=fan.ref(fan.layout['mids'][2*fan.layout['width']+1]);ofloor=office.ref(820);bfloor=shop.ref(641)
sand=RoomParts(f.imp,'firered','FR_SAFARI_ZONE_WEST').ref(258)
STEEL=[[248,248,232],[184,208,216],[112,152,176],[40,56,80]]
TIMBER=[[248,240,200],[208,192,128],[144,136,88],[56,64,64]]
GREEN=[[240,248,224],[168,208,160],[96,152,128],[40,72,72]]
BLUE=[[240,248,248],[160,216,232],[88,152,192],[40,64,96]]
ORANGE=[[248,240,200],[232,176,104],[176,112,72],[64,64,72]]
for game in GAMES:
 for ox in(0,5):
  for y in range(3):
   for x in range(ox,ox+3):f.overrides.add((game,'BILLS_HOUSE',x,y))

def recolor(colors,role):return f.source_palette(colors,'gen1_special_'+role)
def door(base):return f.composite(base,gate.rect(56,10,8,5)+gate.rect(80,10,8,5,8,0)+gate.rect(56,21,8,11,0,5)+gate.rect(80,21,8,11,8,5),'gen1_complete_native_special_room_door')
def handle(c,x,y,name,m,data):
 raw=tuple(c['tiles'])
 if name=='BILLS_HOUSE':
  if y<3 and(x<3 or x>=5):
   ox=0 if x<3 else 5;sx=32 if x<3 else 144
   return f.composite(cfloor,cottage.rect(sx+(x-ox)*16,16+y*16,16,16),'gen1_whole_native_bill_transporter_pod')
  if raw in((31,31,31,31),(69,69,31,31),(31,65,31,31),(66,31,31,31)):return f.native(cfloor,'gen1_bill_native_floor')
  if raw==(16,16,16,16):return f.native(cottage.ref(cottage.layout['mids'][3]),'gen1_bill_native_wall')
  if raw==(38,38,54,54):return f.composite(cfloor,cottage.rect(80,24,16,16),'gen1_bill_complete_native_transporter_conduit')
  if 1<=x<=2 and 4<=y<=5:return f.composite(cfloor,cottage.rect(64+(x-1)*16,80+(y-4)*16,16,16,layers=['mid']),'gen1_bill_complete_native_workstation')
  if raw==(70,70,71,71):return f.template('household_rug_left'if x==2 else'household_rug_right',cfloor)
  return recolor([BLUE if t in(7,8,9,23,24,25,40,41,55,56,57,58)else STEEL for t in raw],'original_transporter_small_connections')
 if c['tileset']=='BEACH_HOUSE':
  if raw==(17,17,17,17):return f.native(sand,'gen1_beach_native_sandy_ground')
  if raw==(4,4,20,20):return f.template('household_rug_left'if x==2 else'household_rug_right',sand)
  if raw in((68,69,8,9),(70,71,24,25)):
   top=raw==(68,69,8,9)
   return f.composite(sand,native_plant_parts(f.imp,top),'gen1_beach_complete_native_potted_plant_'+('crown'if top else'pot'))
  if raw==(1,1,1,1):return f.native(house.ref(1),'gen1_beach_native_dotted_floor')
  if raw==(3,3,3,3):return f.native(cfloor,'gen1_beach_native_board_floor')
  return recolor([BLUE if t in(8,9,10,11,24,25,26,27,40,41,56,57)else TIMBER if t in(3,4,5,6,19,20,21,22)else STEEL for t in raw],'original_complete_surf_house_details')
 if c['tileset']=='CLUB':
  if name=='BIKE_SHOP':
   if raw in((15,31,31,15),(15,15,15,15)):return f.native(bfloor,'gen1_bike_shop_native_floor')
   if raw==(6,6,6,6):return f.native(shop.ref(shop.layout['mids'][1]),'gen1_bike_shop_native_wall')
   if raw in((7,8,7,8),(6,6,7,8)):return f.template('johto_bike_shop_counter_top',bfloor)
   if raw in((7,8,23,24),(54,16,23,24),(16,5,23,24)):return f.template('johto_bike_shop_counter_end',bfloor)
   if raw==(5,10,26,26):return f.template('household_rug_left'if x==2 else'household_rug_right',bfloor)
   return recolor([ORANGE if t in(11,12,13,14,17,18,27,28,29)else STEEL for t in raw],'original_complete_compact_display_bicycles')
  # Original compact Cable Club consoles retain every port and keypad; the
  # native wireless rooms are larger and would obscure the original seats.
  return recolor([STEEL if t in(48,49,50,51,53,54,55,56,57,58,59,60,61,62,63,68,69,70,71,72,73)else ORANGE if t in(6,52)else BLUE for t in raw],'original_complete_link_room_court_and_console')
 if name=='POKEMON_FAN_CLUB':
  if raw==(31,31,31,31):return f.native(ffloor,'gen1_fan_club_native_floor')
  if raw==(61,62,59,60):return f.template('johto_house_chair_left'if x<4 else'johto_house_chair_right',ffloor)
  if raw in((19,20,35,36),):return recolor(TIMBER,'original_complete_pokemon_portrait')
  if 2<=x<=5 and 2<=y<=5:return recolor(GREEN,'original_octagonal_meeting_table_and_presidential_chair')
  if raw in((52,52,68,68),(9,52,68,49),(30,52,50,50),(31,52,51,68)):return recolor(ORANGE,'original_complete_compact_sofa')
  return recolor(STEEL,'original_fan_club_wall_or_furniture_module')
 if name=='SILPH_CO_11F':
  if raw==(31,31,31,31):return f.native(ofloor,'gen1_silph_top_floor_native_floor')
  if raw==(47,47,47,47):return f.native(office.ref(0),'gen1_silph_original_blocked_void')
  if raw in((5,6,21,22),(3,3,4,4)):return door(ofloor)
  if raw==(83,84,85,86):return f.native(saffron.ref(659),'gen1_silph_native_teleport_pad')
  if raw in((61,62,59,60),):return f.template('johto_house_chair_left'if x<8 else'johto_house_chair_right',ofloor)
  if raw==(19,20,35,36):return recolor(TIMBER,'original_complete_executive_pokemon_portrait')
  if 6<=x<=9 and 6<=y<=9:return recolor(GREEN,'original_complete_executive_meeting_table_and_chair')
  if 10<=x<=11 and 12<=y<=13:
   return f.composite(ofloor,cottage.rect(64+(x-10)*16,80+(y-12)*16,16,16,layers=['mid']),'gen1_silph_complete_native_executive_workstation')
  return recolor(STEEL,'original_silph_complete_partition_corner_or_desk')
 return None
if __name__=='__main__':f.run(handle,('BILLS_HOUSE','POKEMON_FAN_CLUB','SILPH_CO_11F','BIKE_SHOP','COLOSSEUM','TRADE_CENTER','SUMMER_BEACH_HOUSE'),'Both complete native Gen3 Sea Cottage transporter pods use48x48 original source envelopes without scaling or clipping. Complete native16x32 Yellow beach-house palms retain both crowns and pots over the same native sand as the surrounding floor; the complete native entrance mat retains its original two-cell warp footprint. Native floors, chairs, room doors, PCs, teleport pads and shop counters match their original functions. Original compact display bicycles, octagonal meeting furniture, executive chair, Cable Club court/console ports and Yellow surf-house posters retain every original pixel with four distinct native Gen3 colors per8px source tile where whole native counterparts have different footprints. Original Bill transformation, bike purchase, link trading/battles, Surfing Pikachu, Silph story, all original movement flags, NPCs, maps and warps remain unchanged.')
