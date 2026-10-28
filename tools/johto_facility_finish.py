"""Direct Gen3 industrial rooms, equipment and research furniture."""
import copy
import gen2_extended_review as e
from johto_family_review import FamilyReview,ROOT
from native_room_parts import RoomParts
f=FamilyReview('facility',{'TILESET_FACILITY'});rocket=RoomParts(f.imp,'firered','FR_ROCKET_HIDEOUT_B1F');lab=RoomParts(f.imp,'firered','FR_OAKS_LAB');power=RoomParts(f.imp,'firered','FR_POWER_PLANT');electric=RoomParts(f.imp,'emerald','EM_MAUVILLE_CITY_GYM');club=RoomParts(f.imp,'emerald','EM_SLATEPORT_CITY_POKEMON_FAN_CLUB')
floor=rocket.ref(641);wall=rocket.ref(649)
club_native=f.imp.gba('emerald',club.map)[0]
sofa_bg={v for v in club_native.crop((80,72,144,96)).get_flattened_data()if v[0]>v[1]and v[0]>v[2]}
sofa_outside=club.exterior(80,72,64,24,sofa_bg)
tables_by_map={'MR_POKEMONS_HOUSE':[(4,4,2)],'RUINS_OF_ALPH_RESEARCH_CENTER':[(4,4,2)],'TEAM_ROCKET_BASE_B3F':[(11,3,3),(9,13,3)]}
f.overrides={(game,name,x,y)for game in('gold','silver','crystal')for name,rects in tables_by_map.items()for ox,oy,w in rects for x in range(ox,ox+w)for y in range(oy,oy+2)}
for r in f.active:
 if r['game']=='red'and r['role'].startswith('household_'):f.templates.setdefault(r['role'],r)
def part(ref,sx=0,sy=0,w=16,h=16,x=0,y=0,layers=None):
 p={'donor':ref,'srcX':sx,'srcY':sy,'w':w,'h':h,'x':x,'y':y}
 if layers:p.update(layers=layers,layerHashes={k:f.imp.cell_index(ref['game'])[ref['tileset'],ref['id']]['layer_sha256'][k]for k in layers})
 return p
def comp(parts,role,base=floor):return f.composite(base,parts,'johto_facility_'+role)
def native(ref,role,base=floor):return comp([part(ref,layers=['mid'])],role,base)
def whole(room,sx,sy,role):return comp(room.rect(sx,sy,16,16,layers=['mid']),role)
def cell(c,x,y,m,data,dy):
 yy=y+dy
 if not 0<=yy<m['height']*2:return None
 return tuple(e.cell_info(f.cache,c['game'],data,m['tileset'],m['blocks'][yy//2*m['width']+x//2],yy%2*2+x%2)['tiles'])
wall_horizontal=comp([part(rocket.ref(649),h=8),part(rocket.ref(657),sy=8,h=8,y=8)],'complete_horizontal_wall')
wall_vertical=comp([part(rocket.ref(656),sx=8,w=8),part(rocket.ref(660),w=8,x=8)],'complete_vertical_wall')
def bank(raw):
 # The original control banks mix half-width mesh and complete monitors.
 # Match each of their native8px modules, preserving continuous geometry.
 parts=[]
 for q,t in enumerate(raw):
  xx,yy=q%2*8,q//2*8
  if t in(10,11,26,27):
   n=(0 if t in(10,26)else 1)+(0 if t in(10,11)else 2);parts.append(part(rocket.ref(781),n%2*8,n//2*8,8,8,xx,yy,layers=['mid']))
  elif t in(69,70,74,75,85,86,90,91):
   n=(0 if t in(69,74,85,90)else 1)+(0 if t in(69,70,74,75)else 2);parts.append(part(power.ref(708),n%2*8,n//2*8,8,8,xx,yy))
  elif t==59:parts.append(part(power.ref(708),q%2*8,q//2*8,8,8,xx,yy))
  else:return None
 return comp(parts,'complete_control_bank')
def handle(c,x,y,name,m,data):
 raw=tuple(c['tiles']);col=c['collision']
 for ox,oy,w in tables_by_map.get(name,[]):
  if ox<=x<ox+w and oy<=y<oy+2:
   sx=128 if x==ox else 160 if x==ox+w-1 else 144
   return whole(lab,sx,64+(y-oy)*16,'complete_native_table_'+str(x-ox)+'_'+str(y-oy))
 if raw==(1,38,38,1):return f.native(floor,'johto_facility_shared_floor')
 if raw==(34,34,34,34):return f.native(wall,'johto_facility_back_wall')
 if raw in((65,65,77,77),(64,65,76,77),(65,66,77,78),(64,66,80,82)):
  return copy.deepcopy(wall_horizontal)
 if raw==(80,82,80,82):return copy.deepcopy(wall_vertical)
 if raw==(80,82,26,27):return comp([part(rocket.ref(656),sx=8,w=8,h=8),part(rocket.ref(660),w=8,h=8,x=8),part(rocket.ref(657),sy=8,h=8,y=8)],'complete_wall_lower_end')
 if raw==(56,56,57,57):
  a,b=(544,552)if x%2==0 else(545,553)
  return comp([part(electric.ref(a),sy=8,h=8,layers=['over']),part(electric.ref(b),h=8,y=8,layers=['over'])],'electric_security_barrier')
 if raw==(12,13,12,13):return comp([part(electric.ref(584),layers=['over'])],'vertical_electric_security_barrier')
 if raw==(16,17,32,33):return f.original('assets/original/interior-stairs/down.png',floor,'johto_facility_stairs_down')
 if raw==(39,39,55,55):return f.template('household_rug_left'if x==2 else'household_rug_right',floor)
 if raw in((44,45,60,61),(46,47,62,63)):
  return f.template('household_plant_head'if raw[0]==44 else'household_plant_base',floor)
 if raw==(14,15,30,31):return f.template('johto_house_chair_right',floor)
 if raw==(64,66,40,41):return f.template('johto_domestic_complete_single_bay_bookcase_0',wall)
 if raw in((40,41,42,43),(40,41,40,41)):return f.template('johto_domestic_complete_single_bay_bookcase_1',floor)
 if raw in((64,66,10,11),(34,34,92,93)):
  return native(rocket.ref(775),'whole_research_server_head',wall)
 if raw in((10,11,26,27),(94,95,22,23)):
  return native(rocket.ref(783),'whole_research_server_base')
 if raw in((35,36,87,88),(36,37,88,89)):
  # Complete sofa end modules retain both arms, the full back and its feet.
  sx=80 if raw[0]==35 else 128
  return comp(club.masked(sx,72,list(range(16)),list(range(8)),transparent_pixels=sofa_outside)+club.masked(sx,88,list(range(16)),list(range(8)),0,8,transparent_pixels=sofa_outside),'complete_modular_sofa')
 # Whole Gen3 workstation32x32, split only at original cell boundaries.
 machines={(2,3,18,19):(32,8),(4,5,20,21):(48,8),(6,7,38,1):(32,24),(8,9,38,1):(48,24)}
 if raw in machines:
  sx,sy=machines[raw];return whole(lab,sx,sy,'whole_research_workstation')
 table={(64,65,80,72):(128,64),(65,65,81,81):(144,64),(65,66,73,82):(160,64),(65,66,81,82):(160,64),(80,72,83,58):(128,80),(73,82,58,84):(160,80),(80,81,83,58):(128,80),(81,81,58,58):(144,80),(81,82,58,84):(160,80)}
 if raw in table:
  sx,sy=table[raw];return whole(lab,sx,sy,'whole_research_table')
 if raw==(59,59,59,59):return f.native(power.ref(708),'johto_facility_steel_grille')
 return bank(raw)
f.run(handle,('MR_POKEMONS_HOUSE','RUINS_OF_ALPH_RESEARCH_CENTER','TEAM_ROCKET_BASE_B2F','TEAM_ROCKET_BASE_B3F'),'Direct native Gen3 industrial counterparts: FireRed Rocket equipment and complete server cabinets, FireRed lab workstations/tables, Power Plant steel grilles and Emerald Mauville electric security barriers. Complete native caps, outside frames and repeated wall/table/sofa modules keep their pixel scale. Original password doors, electricity switches, Electrode rooms, hidden passages, plant/desk interactions, NPCs, stairs and source collision remain unchanged.')
