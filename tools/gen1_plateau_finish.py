"""Native Gen3 Indigo approach surfaces and intact original gateway details."""
from gen1_family_review import FamilyReview,GAMES,source,cell_info
from native_room_parts import RoomParts
import preview
f=FamilyReview('plateau',{'PLATEAU'});p=RoomParts(f.imp,'firered','FR_INDIGO_PLATEAU_EXTERIOR');route=RoomParts(f.imp,'firered','FR_ROUTE_23');house=RoomParts(f.imp,'firered','FR_PEWTER_CITY');ground=p.ref(1)
bg=set()
for mid in(1,8,9,16,17):bg.update(preview.native_donor(f.cache,p.ref(mid),f.packed).get_flattened_data())
outside=p.exterior(128,144,16,32,bg)
statue={dy:p.masked(128,144+16*dy,list(range(16)),list(range(16)),transparent_pixels=outside)for dy in(0,1)}
STONE=[[230,239,247],[189,206,214],[123,156,173],[49,66,82]]
walls={(3,3,3,3):113,(3,3,13,13):105,(13,13,15,15):113,(15,15,15,15):121,(15,15,14,14):121,(46,47,46,47):114,(3,3,32,33):106,(32,33,46,47):104,(5,6,21,22):120}
water={(20,20,20,20):'freshwater_pond_interior',(51,51,20,20):'freshwater_pond_north_bank',(20,31,20,31):'freshwater_pond_east_bank',(50,20,50,20):'freshwater_pond_west_bank',(20,31,20,20):'freshwater_pond_north_johto_410',(50,20,20,20):'freshwater_pond_inward_northwest_bank'}
def handle(c,x,y,name,m,data):
 raw=tuple(c['tiles'])
 if raw in((37,38,40,41),(16,18,40,41)):
  return f.composite(ground,statue[0],'gen1_plateau_complete_rhydon_statue_head')
 if raw in((21,22,5,6),(5,6,48,49),(21,22,48,49)):
  if y>0:
   above=cell_info(f.cache,c['game'],data,m['tileset'],m['blocks'][(y-1)//2*m['width']+x//2],(y-1)%2*2+x%2)
   if tuple(above['tiles'])in((37,38,40,41),(16,18,40,41)):
    return f.composite(ground,statue[1],'gen1_plateau_complete_rhydon_statue_base')
  return f.source_palette(STONE,'gen1_plateau_preserved_complete_monument_column_shaft_or_foot')
 if raw in((42,43,34,29),(7,8,23,24)):return f.native(route.ref(159),'gen1_plateau_whole_native_fixed_boulder')
 if name=='INDIGO_PLATEAU'and not any(c['walkable_tiles']):
  return f.source_palette(STONE,'gen1_plateau_preserved_complete_monument_terraces')
 # The unique Gen1 inset gateway is not flattened/shrunk to remake geometry.
 # Preserve its exact stone carving and paired original entrance cells.
 if name=='INDIGO_PLATEAU'and 6<=x<=13 and y<=5:
  return f.source_palette(STONE,'gen1_plateau_preserved_complete_league_gateway')
 if raw in walls:return f.source_palette(STONE,'gen1_plateau_preserved_complete_monument_wall_or_column')
 if raw in water:return f.template(water[raw])
 if c['grass_tile_present']:return f.template('tall_grass')
 if raw in((35,35,35,35),(35,35,45,35),(69,69,69,69)):return f.native(ground,'gen1_plateau_native_open_ground')
 if raw in((44,35,35,44),(44,44,44,44)):return f.native(p.ref(650),'gen1_plateau_native_stone_approach')
 roof={(61,61,61,61):710,(62,62,61,61):702,(68,61,68,61):695,(61,68,61,68):663,(64,62,68,61):687,(62,65,61,68):655}
 if raw in roof:return f.native(house.ref(roof[raw]),'gen1_plateau_complete_native_checkpoint_roof')
 if raw==(11,12,27,28):return f.native(house.ref(718),'gen1_plateau_complete_native_checkpoint_door')
 if raw==(9,10,25,26):return f.template('forest_freestanding_sign')
 return None
# Both Plateau maps use symmetric monument columns and horizontal masonry,
# not directional natural cliffs. Correct older broad matches as well.
for game in GAMES:
 data=source(f.cache,game)
 for name in ('INDIGO_PLATEAU','ROUTE_23'):
  m=data['maps'][name]
  for y in range(m['height']*2):
   for x in range(m['width']*2):
    c=cell_info(f.cache,game,data,m['tileset'],m['blocks'][y//2*m['width']+x//2],y%2*2+x%2)
    if tuple(c['tiles'])in walls or tuple(c['tiles'])in((37,38,40,41),(16,18,40,41),(21,22,5,6),(5,6,48,49),(21,22,48,49),(42,43,34,29),(7,8,23,24)):f.overrides.add((game,name,x,y))
f.run(handle,('INDIGO_PLATEAU','ROUTE_23'),'Actual Gen3 Indigo approach paths, intact monument masonry, complete Rhydon statues, animated inland water, grass and checkpoint modules at original pixel size. The unique Gen1 League gateway, the tall monument terraces in both maps and symmetric columns retain every original pixel, intact column shafts and paired entrance in a Gen3 stone palette, rather than shrinking remake geometry. Original badge checks, guard scripts, Surf, ledges, encounters, warps and collision remain unchanged.')
