"""Source-shape-equivalent native terrain for Dragon's Den's lower chamber."""
import copy
import catalog,preview,gen2_extended_review as e
from johto_family_review import FamilyReview
from johto_remaining_review import artwork,strip
f=FamilyReview('dragonden',{'TILESET_JOHTO'},maps={'DRAGONS_DEN_B1F'})
known={};house={};source=e.source(f.cache,'crystal')
for r in f.active:
 if r['game']!='crystal'or r['tileset']!='TILESET_JOHTO':continue
 c=e.cell_info(f.cache,'crystal',source,r['tileset'],r['id'],r['quadrant'])
 known.setdefault(tuple(c['tiles']),[]).append(r)
 if r.get('map')=='LAKE_OF_RAGE'and r['role']=='architecture_home48':house[r['x']-6,r['y']-1]=r
assert len(house)==12
ground=f.ref('emerald','general__cave',513)
# Cave paths share a generic outdoor floor glyph; scope the cave counterpart
# explicitly while leaving generic outdoor art unchanged.
source_by_game={g:e.source(f.cache,g)for g in e.GAMES}
f.active=[r for r in f.active if not(r['tileset']=='TILESET_JOHTO'and r.get('map','DRAGONS_DEN_B1F')=='DRAGONS_DEN_B1F'and tuple(e.cell_info(f.cache,r['game'],source_by_game[r['game']],r['tileset'],r['id'],r['quadrant'])['tiles'])in((5,5,5,5),(6,6,6,6)))]
def on_ground(art):
 r=copy.deepcopy(art)
 if r.get('base',{}).get('id')==1:r['base']=ground
 if r.get('donor',{}).get('tileset')=='general__petalburg'and r['donor'].get('id')==1:r['donor']=ground
 return r
def choose(raw,role):
 rows=[r for r in known.get(raw,[])if r['role']==role]
 assert rows,(raw,role)
 return on_ground(artwork(rows[0]))|{'role':role}

water=f.template('cave_plain_water')
def cave_water(mid):
 return f.template('cave_plain_water'if mid==635 else'freshwater_pond_cave_bank_'+str(mid))

def cave_barrier():
 ref=f.ref('emerald','general__cave',514)
 parts=[{'donor':ref,'srcX':0,'srcY':0,'w':16,'h':16,'x':0,'y':0,'layers':['mid'],'layerHashes':{'mid':f.imp.cell_index('emerald')['general__cave',514]['layer_sha256']['mid']}}]
 r=f.composite(water['donor'],parts,'freshwater_pond_cave_rock_barrier')
 r.update(animated=True,animation=copy.deepcopy(water['animation']))
 return r

water_shapes={(20,20,20,20):635,(76,76,20,20):657,(73,73,20,20):657,(61,20,61,20):650,(20,59,20,59):648,(76,93,20,59):641,(77,20,20,20):658,(20,75,20,20):656,(92,76,61,20):649,(92,76,20,20):649}
roles={
 (20,20,20,20):'freshwater_pond_interior',
 (76,76,20,20):'freshwater_pond_north_bank',
 (61,20,61,20):'freshwater_pond_west_bank',
 (20,59,20,59):'freshwater_pond_east_bank',
 (76,93,20,59):'freshwater_pond_northeast_bank',
 (77,20,20,20):'freshwater_pond_inward_northwest_bank',
 (20,75,20,20):'freshwater_pond_north_johto_410',
 (88,88,88,88):'rocky_coast_sea_rock_barrier',
 (5,5,5,5):'short_nonencounter_grass',
 (30,31,62,63):'headbutt_small_tree',
 (70,71,86,87):'north_johto_native_cave_entrance',
 (50,51,66,67):'rocky_coast_whirlpool',
 (60,43,43,59):'mahogany_northwest_rock_corner',
 (59,59,59,59):'mahogany_azalea_raised_rock_west',
 (59,75,75,76):'mahogany_azalea_raised_rock_west',
 (76,76,76,76):'mahogany_azalea_raised_rock_2',
 (61,61,61,61):'mahogany_violet_whole_raised_ground',
 (44,44,60,60):'mahogany_violet_whole_raised_ground',
 (45,60,61,45):'mahogany_violet_whole_raised_ground',
 (77,61,76,77):'mahogany_violet_whole_raised_ground',
 (76,76,61,76):'north_johto_complete_inward_cliff_turn',
 (76,76,76,59):'north_johto_complete_inward_cliff_turn',
 (92,76,61,20):'freshwater_pond_northwest_bank',
 (43,44,59,60):'north_johto_whole_outcrop_0',
 (44,45,60,61):'north_johto_whole_outcrop_1',
 (59,60,75,76):'north_johto_whole_outcrop_2',
 (60,61,76,77):'north_johto_whole_outcrop_3',
 (90,90,89,89):'johto_route_complete_metal_fence',
 (90,90,89,74):'johto_route_complete_metal_fence',
 (90,90,74,89):'johto_route_complete_left_fence_turn',
 (6,74,6,74):'johto_route_complete_metal_fence',
 (74,6,74,6):'johto_route_complete_metal_fence',
}
def handle(c,x,y,name,m,data):
 if name!='DRAGONS_DEN_B1F':return None
 raw=tuple(c['tiles'])
 if 18<=x<=21 and (26 if c['game']!='crystal'else 27)<=y<=29:
  dy=y-27
  if dy==-1:r=on_ground(artwork(house[x-18,0]))
  elif dy==0 and c['game']!='crystal':
   a=house[x-18,0];r=f.composite(ground,strip(a['parts'],8,8,0)+strip(a['parts'],8,8,8),'johto_dragonden_shrine_repeat_shingle_course')
  else:r=on_ground(artwork(house[x-18,dy]))
  r['role']='johto_dragonden_complete_native_timber_shrine_module';return r
 if raw in((5,5,5,5),(6,6,6,6)):return f.native(ground,'johto_dragonden_cave_floor')
 if raw in water_shapes:return cave_water(water_shapes[raw])
 if raw==(88,88,88,88):return cave_barrier()
 if raw==(50,51,66,67):
  r=choose(raw,'rocky_coast_whirlpool');r['base']=copy.deepcopy(water['donor']);r['animation']=copy.deepcopy(water['animation']);r['role']='freshwater_pond_cave_whirlpool';return r
 if raw==(60,60,60,60):return choose(raw,'mahogany_azalea_raised_rock_0')
 if raw==(92,76,20,20):return choose((92,76,61,20),'freshwater_pond_northwest_bank')
 if raw in roles:return choose(raw,roles[raw])
 return None
f.run(handle,('DRAGONS_DEN_B1F',),'Native Gen3 cave floor513, animated cave water635 and the complete checked cave-bank family preserve the original source bank handedness. Whole cave-rock514 silhouettes sit on the same animated cave water, and the whirlpool keeps its complete foam animation on that matching base. Cave ground replaces outdoor lawn beneath trees, rails and shrine modules. Native rock geometry, whole outcrop quadrants, Headbutt trees and complete native timber-building modules preserve all source footprints. Shrine remains64x48 with original door position (G/S retain their additional shingle course); original Surf/Whirlpool requirements, events, collisions, warps and paths remain authoritative. Water semantic roles remain recognizable for all existing water choices and speed controls. No new generated art.')
