"""Complete casino/cafe equipment without altering original games or vendors."""
import json
from PIL import Image
import catalog,preview,gen2_extended_review as e
from johto_family_review import FamilyReview,ROOT
from native_room_parts import RoomParts
f=FamilyReview('gamecorner',{'TILESET_GAME_CORNER'});gc=RoomParts(f.imp,'firered','FR_CELADON_CITY_GAME_CORNER');center=RoomParts(f.imp,'firered','FR_VIRIDIAN_CITY_POKEMON_CENTER_1F');floor=gc.ref(641);wall=gc.ref(gc.layout['mids'][0])
native=f.imp.gba('firered',gc.map)[0];plant_bg=set(native.crop((160,16,176,32)).get_flattened_data())|set(preview.native_donor(f.cache,floor,f.packed).get_flattened_data())|set(preview.native_donor(f.cache,wall,f.packed).get_flattened_data());plant_outside=gc.exterior(0,16,16,32,plant_bg)
for r in f.active:
 if r['game']=='red'and r['role'].startswith('household_'):f.templates.setdefault(r['role'],r)
tables={(2,2,137,138):0,(2,2,138,139):1,(140,141,153,154):2,(141,142,155,156):3,(46,13,28,12):0,(13,47,12,29):1,(62,80,168,78):2,(80,63,79,169):3,(62,80,17,78):2,(80,63,79,18):3}
def tile(sx,sy,role,layers=None):return f.composite(floor,gc.rect(sx,sy,16,16,layers=layers),'johto_casino_'+role)
def relative(c,x,y,m,data,dx):
 xx=x+dx
 if not 0<=xx<m['width']*2:return None
 return tuple(e.cell_info(f.cache,c['game'],data,m['tileset'],m['blocks'][y//2*m['width']+xx//2],y%2*2+xx%2)['tiles'])
def handle(c,x,y,name,m,data):
 raw=tuple(c['tiles']);col=c['collision']
 if raw in((1,1,16,16),(1,16,17,18),(1,16,52,53)):return f.native(floor,'johto_casino_plain_floor_beneath_equipment')
 if raw==(2,2,2,2):return f.native(wall,'johto_casino_complete_blue_wall')
 if raw==(10,11,26,27):return tile(16,96,'whole_native_chair')
 if raw==(14,14,30,30):return tile(32,48,'service_counter_front')
 if raw==(20,21,20,21):return tile(16,32,'service_counter_left_side')
 if raw==(133,134,133,134):return tile(144,32,'service_counter_right_side')
 if raw in((120,132,14,30),(77,21,30,31),(148,134,30,31)):return tile(144,48,'service_counter_right_corner')
 if raw in((148,134,30,30),(20,77,61,30),(20,132,61,30),(4,14,61,30)):return tile(16,48,'service_counter_left_corner')
 if raw in((2,2,4,5),(2,2,149,150)):
  return f.composite(wall,gc.rect(16 if raw[2]==4 else 144,16,16,8,0,8),'johto_casino_counter_back_cap')
 if raw==(64,65,30,30):return f.original('assets/original/interior-computer/computer.png',gc.ref(gc.layout['mids'][3*gc.layout['width']+2]),'johto_casino_complete_prize_terminal')
 if raw in((2,2,164,165),(180,81,50,51),(180,181,50,51)):return f.template('johto_complete_pc_'+('0'if raw[0]==2 else'1'),wall if raw[0]==2 else floor)
 if raw in((166,167,34,35),(42,43,58,59),(4,5,34,35),(34,35,50,51)):
  right=relative(c,x,y,m,data,-1)==raw
  return tile(32+16*int(right),8 if raw[0]in(166,4)else 24,'complete_drink_dispenser_'+str(int(right))+'_'+str(int(raw[0]in(42,34))))
 if raw in((25,44,41,60),(57,15,36,37)):
  return f.composite(floor,gc.masked(0,16 if raw[0]==25 else 32,list(range(16)),list(range(16)),transparent_pixels=plant_outside),'johto_casino_complete_potted_plant')
 if raw==(3,3,19,19):
  right=relative(c,x,y,m,data,-1)==raw;return f.template('household_rug_right'if right else'household_rug_left',floor)
 shelves={(22,23,38,39):0,(23,24,39,40):1,(54,55,17,18):2,(55,56,17,18):3}
 if raw in shelves:return f.template('johto_house_bookcase_'+str(shelves[raw]),wall if shelves[raw]<2 else floor)
 if raw==(4,5,20,21)and col==144:return tile(80,80,'whole_machine_bank_left_cap')
 if raw in tables:
  q=tables[raw];r=f.composite(floor,center.rect(176+q%2*16,96+q//2*16,16,16,layers=['mid']),'johto_casino_complete_glass_table_'+str(q))
  if name=='GOLDENROD_GAME_CORNER'and q==1:return r
  return r
 bank={(128,129,144,145):(0,0),(130,131,146,147):(1,0),(160,161,144,145):(0,1),(162,163,146,147):(1,1),(176,177,192,193):(0,2),(178,179,194,195):(1,2)}
 if raw in bank:
  xx,yy=bank[raw];return tile(80+xx*16,80 if yy==0 else 160 if yy==2 else 96,'whole_machine_bank_'+str(xx)+'_'+str(yy))
 return None
f.run(handle,('GOLDENROD_GAME_CORNER','OLIVINE_CAFE'),'Complete Gen3 casino machine banks, three-spout drink dispensers, vendor terminal, displays, chairs, plants, counter curves and cafe tables reviewed in both original/native layouts. Each machine bank keeps its entire native top and foot; only whole repeat modules extend its body. Original SlotMachine/CardFlip scripts, lucky-machine positions, vendors, rewards, chairs, NPCs, exits and the left-behind drink interaction are unchanged. Goldenrod north32px object is a table with a drink, verified from the original bg event; it is not replaced with a television.')
