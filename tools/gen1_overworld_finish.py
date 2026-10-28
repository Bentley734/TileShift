"""Explicit native Kanto outdoor material, shoreline and building modules."""
from gen1_family_review import FamilyReview
from native_room_parts import RoomParts
from johto_remaining_review import artwork
f=FamilyReview('overworld',{'OVERWORLD'})
p=RoomParts(f.imp,'firered','FR_PEWTER_CITY');cliff=RoomParts(f.imp,'firered','FR_SAFARI_ZONE_WEST');port=RoomParts(f.imp,'firered','FR_SSANNE_EXTERIOR')
ground=p.ref(1)
OCEAN={'VERMILION_CITY','CINNABAR_ISLAND','ROUTE_11','ROUTE_12','ROUTE_13','ROUTE_19','ROUTE_20','ROUTE_21'}
rocks={(17,17,17,17):113,(1,1,17,17):105,(36,36,36,36):114,(39,39,39,39):112,(55,55,55,55):121,(35,30,30,39):104,(2,57,36,2):106,(39,54,54,55):120,(53,55,36,53):122,(52,36,55,52):179,(55,19,19,39):178,(39,44,39,44):112,(13,36,13,36):114,(39,44,54,55):120,(39,54,54,55):120,(13,36,55,52):179}
roof={(83,83,18,18):702,(18,18,18,18):710,(18,18,23,23):689,(76,83,90,18):687,(90,18,92,23):695,(83,77,18,90):655,(18,90,23,93):663,(83,77,18,90):655,(18,18,23,34):689}
def native(room,mid,role):return f.native(room.ref(mid),'gen1_kanto_'+role)
def wall(role='complete_native_siding'):
 return f.composite(ground,p.rect(520,176,8,16)+p.rect(520,176,8,16,8,0),'gen1_kanto_'+role)
def window(role='whole_native_framed_window'):
 # The complete native gold frame is555..565,176..185, inside this16px crop.
 return f.composite(ground,p.rect(552,176,16,16),'gen1_kanto_'+role)
def halfwall(left):return f.composite(ground,p.rect(512 if left else 576,176,16,16),'gen1_kanto_native_siding_outer_jamb')
def fence(raw):
 # Native fence237 is a complete pair of posts. Side rails use whole16px
 # modules; no source collision is inferred from their Gen3 counterpart.
 return f.template('johto_route_complete_metal_fence',ground)
def handle(c,x,y,name,m,data):
 raw=tuple(c['tiles'])
 if raw in((29,36,29,36),(29,36,55,52)):return native(cliff,114 if raw[2]==29 else 179,'complete_thin_cliff_turn')
 if raw==(72,73,88,89):return f.template('north_johto_native_cave_entrance')
 leftroof=((5,6,21,22),(5,6,21,56),(21,56,21,22),(21,56,21,56),(21,22,37,38),(37,38,92,23))
 rightroof=((8,9,24,25),(8,9,56,25),(56,25,24,25),(56,25,56,25),(24,25,40,41),(40,41,23,93))
 if raw in leftroof:return native(p,687 if raw[0]==5 else 695,'complete_left_roof_edge')
 if raw in rightroof:return native(p,655 if raw[0]==8 else 663,'complete_right_roof_edge')
 if raw in((37,38,15,34),(37,38,78,26),(40,41,75,31),(40,41,26,79),(40,41,34,31)):
  left=raw[0]==37
  return f.composite(ground,[{'donor':p.ref(695 if left else 663),'srcY':8,'w':16,'h':8},{'donor':p.ref(703 if left else 671),'srcY':8,'w':16,'h':8,'y':8}],'gen1_kanto_complete_roof_wall_corner')
 if raw==(7,7,23,23):return native(p,689,'complete_lower_roof_course')
 if raw==(23,23,34,34):return wall('whole_eaves_and_wall_course')
 if raw in((34,47,34,34),(63,34,34,34),(68,69,74,74)):
  return f.source_palette([[230,239,247],[189,206,222],[115,140,173],[49,58,73]],'gen1_kanto_preserved_complete_shop_gym_sign')
 if raw in rocks:return native(cliff,rocks[raw],'complete_native_cliff_'+str(rocks[raw]))
 if raw==(20,20,20,20):return f.template('coastal_ocean_water_interior'if name in OCEAN else'freshwater_pond_interior')
 banks={(51,51,20,20):'north',(49,49,20,20):'north',(50,20,50,20):'west',(20,84,20,84):'east',(51,51,50,20):'northwest',(51,51,20,84):'northeast',(51,20,20,20):'inward_northwest',(20,51,20,20):'inward_northeast',(20,51,20,84):'northeast'}
 if raw in banks:
  key=banks[raw]
  if name in OCEAN:return f.template('rocky_coast_goldenrod_northeast'if key=='northeast'else'rocky_coast_'+key)
  role={'north':'freshwater_pond_north_bank','west':'freshwater_pond_west_bank','east':'freshwater_pond_east_bank','northwest':'freshwater_pond_northwest_bank','northeast':'freshwater_pond_northeast_bank','inward_northwest':'freshwater_pond_inward_northwest_bank','inward_northeast':'freshwater_pond_north_johto_410'}[key]
  return f.template(role)
 if raw==(91,91,91,91):return native(p,449,'complete_native_stone_paving')
 if raw in((60,60,60,60),(57,57,60,60),(60,60,4,60)):
  return f.template('goldenrod_brick_road')
 if raw in((48,57,57,48),(44,48,48,44),(48,48,48,48)):return native(cliff,258,'nonencounter_sandy_ground')
 if set(raw)<={16,35,32,33}and any(t in(16,32,33)for t in raw):return fence(raw)
 if raw in roof:return native(p,roof[raw],'whole_roof_module_'+str(roof[raw]))
 if raw==(11,12,27,28):return native(p,718,'whole_native_door')
 if raw in((10,10,75,75),(10,10,26,26),(10,10,34,34),(10,10,23,23)):return window()
 if raw in((75,75,26,26),(34,31,26,79),(34,31,26,79),(75,10,75,75),(10,75,75,75)):return wall()
 if raw in((15,10,15,75),(15,75,78,26),(15,10,78,26),(15,34,78,26)):return halfwall(True)
 if raw in((10,31,75,31),(75,31,26,79),(10,31,26,79),(34,31,26,79)):return halfwall(False)
 if raw in((10,34,26,26),(10,34,23,23),(35,10,26,26),(10,35,26,26)):return window()
 return None
f.run(handle,('PEWTER_CITY','CERULEAN_CITY','VERMILION_CITY','SAFFRON_CITY','CELADON_CITY','FUCHSIA_CITY','CINNABAR_ISLAND','ROUTE_12','ROUTE_20'),'Direct reviewed Gen3 Kanto materials: complete rock topology, actual ocean/inland banks, unscaled paving, railings, roof and wall modules. Each gold-framed outdoor window is whole inside its16px native rectangle; doors retain their complete frame. Original source layout, Cut/Snorlax/ship events, ledges, fishing, warps and collision remain unchanged. Unmatched specialized structures remain held for explicit counterparts.')
