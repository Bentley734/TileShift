"""Complete explicit Kanto/shared room families at native pixel size.

Whole source glyphs are matched only within declared equivalent room purposes.
Unmatched architecture and unique props remain held for explicit review.
"""
import argparse, copy, json, os
from collections import defaultdict, Counter
from pathlib import Path
from types import SimpleNamespace
import catalog, preview, gen2_extended_review as e
from interior_review import Imports
from native_room_parts import RoomParts
from johto_remaining_review import artwork
from center_mart_overhang_review import write_rows

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'.work/tileshift-gen2-special-rooms'
TARGET=ROOT/'mappings/gen2_kanto_special_rooms_finish.lua'
SETS={'TILESET_MANSION','TILESET_ELITE_FOUR_ROOM','TILESET_CHAMPIONS_ROOM',
      'TILESET_UNDERGROUND','TILESET_GAME_CORNER','TILESET_RADIO_TOWER','TILESET_LAB','TILESET_PARK'}
NAMES={'WILLS_ROOM','KOGAS_ROOM','BRUNOS_ROOM','KARENS_ROOM','LANCES_ROOM',
 'CELADON_MANSION_1F','CELADON_MANSION_2F','CELADON_MANSION_3F','CELADON_MANSION_ROOF',
 'MOBILE_TRADE_ROOM','MOBILE_BATTLE_ROOM','FUCHSIA_GYM','OAKS_LAB','LAV_RADIO_TOWER_1F',
 'CELADON_GAME_CORNER','CELADON_GAME_CORNER_PRIZE_ROOM','CELADON_CAFE','VERMILION_GYM',
 'UNDERGROUND_PATH','VERMILION_PORT_PASSAGE','SAFFRON_GYM','SAFARI_ZONE_BETA','SAFARI_ZONE_MAIN_OFFICE'}
SOURCES={
 'LAV_RADIO_TOWER_1F':('RADIO_TOWER_1F','RADIO_TOWER_2F','RADIO_TOWER_3F','RADIO_TOWER_4F','RADIO_TOWER_5F'),
 'OAKS_LAB':('ELMS_LAB','EARLS_POKEMON_ACADEMY'),
 'VERMILION_PORT_PASSAGE':('OLIVINE_PORT_PASSAGE',),
 'UNDERGROUND_PATH':('GOLDENROD_UNDERGROUND','GOLDENROD_UNDERGROUND_WAREHOUSE'),
 'CELADON_GAME_CORNER':('GOLDENROD_GAME_CORNER',),
 'CELADON_GAME_CORNER_PRIZE_ROOM':('GOLDENROD_GAME_CORNER',),
 'CELADON_CAFE':('OLIVINE_CAFE',),
 'SAFARI_ZONE_MAIN_OFFICE':('OLIVINE_CAFE','GOLDENROD_GAME_CORNER'),
 'SAFARI_ZONE_BETA':('NATIONAL_PARK','NATIONAL_PARK_BUG_CONTEST'),
}
RED_SOURCES={
 'OAKS_LAB':('OAKS_LAB',),'FUCHSIA_GYM':('FUCHSIA_GYM',),'SAFFRON_GYM':('SAFFRON_GYM',),
 'VERMILION_GYM':('VERMILION_GYM',),'CELADON_CAFE':('CELADON_DINER',),
 'CELADON_MANSION_1F':('CELADON_MANSION_1F',),'CELADON_MANSION_2F':('CELADON_MANSION_2F',),
 'CELADON_MANSION_3F':('CELADON_MANSION_1F',),'CELADON_MANSION_ROOF':('CELADON_MANSION_ROOF',),
 'CELADON_GAME_CORNER':('GAME_CORNER',),'CELADON_GAME_CORNER_PRIZE_ROOM':('GAME_CORNER_PRIZE_ROOM',),
 'UNDERGROUND_PATH':('UNDERGROUND_PATH_NORTH_SOUTH',),
}
NAMES-={'CELADON_MANSION_1F','CELADON_MANSION_2F','CELADON_MANSION_3F','CELADON_MANSION_ROOF','MOBILE_TRADE_ROOM','MOBILE_BATTLE_ROOM'}
STONE=[[240,248,240],[176,192,200],[104,128,144],[48,56,80]]
PURPLE=[[224,216,248],[176,152,216],[120,96,176],[56,48,104]]
GOLD=[[255,239,181],[239,189,82],[189,123,49],[82,66,49]]
RED=[[255,216,184],[248,112,96],[200,64,64],[88,48,64]]
ELITE_TRIM={(39,38,55,54),(37,39,53,55),(57,57,57,57),(72,73,74,75),
 (19,19,18,18),(19,19,19,19),(80,80,36,36),(14,93,14,90),(14,14,92,14),
 (92,14,14,14),(93,90,90,14),(81,81,82,82),(83,84,83,84),(89,83,89,83),
 (2,2,56,2),(56,2,91,2),(2,2,2,91),(2,2,2,56),(2,91,2,2)}

LANCE_ORNAMENT={37, 38, 39, 59, 60, 61, 88, 89, 93, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 221, 222}

class Review:
 def __init__(self):
  self.cache=Path(os.environ['APPDATA'])/'pokemon-love2d';self.imp=Imports(self.cache,ROOT.parent/'.work/tileshift-catalog');self.packed=self.imp.packed
  self.active=[r for p in sorted((ROOT/'mappings').glob('*.lua'))if p!=TARGET for r in preview.read_reviewed(p)]
  self.index=defaultdict(list);self.rooms={};self.templates={r['role']:r for r in self.active if r['game']=='crystal'}
  for r in self.active:
   self.index[r['game'],r.get('map'),r.get('sourceHash')].append(r)
   if r['game']=='red':self.templates.setdefault(r['role'],r)
 def room(self,name,game='firered'):
  key=game,name
  if key not in self.rooms:self.rooms[key]=RoomParts(self.imp,game,name)
  return self.rooms[key]
 def native(self,ref,role):return dict(kind='native',donor=copy.deepcopy(ref),role=role)
 def template(self,role,base=None):
  a=artwork(self.templates[role]);a['role']=role
  if base is not None and 'base'in a:a['base']=copy.deepcopy(base)
  return a
 def foreground(self,room,mid,base,role):
  ref=room.ref(mid);record=self.imp.cell_index(room.game)[room.pair,mid]
  return dict(kind='native_composite',base=copy.deepcopy(base),parts=[dict(donor=ref,layers=['mid','over'],layerHashes={k:record['layer_sha256'][k]for k in('mid','over')},w=16,h=16)],role=role)
 def table(self,x,y,base):
  # The complete32x32 native table begins8px down inside the source32x48
  # occupied rectangle. Split exact foreground pixels across three rows;
  # leave the casino floor underneath, never copy a donor house floor.
  origin=1 if y<4 else 5;host=y-origin;side=x-2;parts=[]
  for srcrow,sy,h,ty in ([(0,0,8,8)]if host==0 else[(0,8,8,0),(1,0,8,8)]if host==1 else[(1,8,8,0)]):
   role=('household_table_nw','household_table_ne','household_table_sw','household_table_se')[srcrow*2+side]
   for part in self.template(role)['parts']:
    px,py=part.get('x',0),part.get('y',0);iy=max(py,sy);ey=min(py+part.get('h',16),sy+h)
    if ey<=iy:continue
    z=copy.deepcopy(part);z.update(srcY=part.get('srcY',0)+iy-py,y=ty+iy-sy,h=ey-iy);parts.append(z)
  return dict(kind='native_composite',base=copy.deepcopy(base),parts=parts,role='kanto_cafe_complete_native_table_'+str(side)+'_'+str(host))
 def recolor(self,c,colors,role):
  return dict(kind='source_palette',sourceColors=copy.deepcopy(colors if len(colors)==4 and isinstance(colors[0][0],list) else [colors]*4),
   role=role,credit='Original Pokemon Gold/Silver/Crystal / Game Freak; palette recolor only.',sourceUrl='https://github.com/pret/pokecrystal',
   originalGeometryFallback=dict(pixel_scale=1,reason='Compact original architectural or patterned ornament has no complete native Gen3 module in the same footprint. Every original pixel and frame remains intact.'))
 def base(self,name):
  if name in ('WILLS_ROOM','KARENS_ROOM'):return self.room('FR_POKEMON_LEAGUE_AGATHAS_ROOM').ref(752)
  if name=='BRUNOS_ROOM':return self.room('FR_POKEMON_LEAGUE_BRUNOS_ROOM').ref(720)
  if name=='KOGAS_ROOM':return self.room('FR_CELADON_CITY_GYM').ref(670)
  if name=='LANCES_ROOM':return self.room('FR_POKEMON_LEAGUE_HALL_OF_FAME').ref(688)
  if name in ('FUCHSIA_GYM','VERMILION_GYM'):return self.room('FR_'+name.replace('_GYM','_CITY_GYM')).ref(641)
  if name=='SAFFRON_GYM':return self.room('FR_SAFFRON_CITY_GYM').ref(641)
  if name=='OAKS_LAB':return self.room('FR_OAKS_LAB').ref(649)
  if name=='LAV_RADIO_TOWER_1F':return self.room('FR_SILPH_CO_1F').ref(820)
  if name in ('CELADON_CAFE','SAFARI_ZONE_MAIN_OFFICE','CELADON_GAME_CORNER','CELADON_GAME_CORNER_PRIZE_ROOM'):return self.room('FR_CELADON_CITY_GAME_CORNER').ref(657)
  return None
 def rug(self,c,x,y,m,data,base):
  left=()
  if x>0:left=tuple(e.cell_info(self.cache,c['game'],data,m['tileset'],m['blocks'][y//2*m['width']+(x-1)//2],y%2*2+(x-1)%2)['tiles'])
  return self.template('household_rug_right'if left==tuple(c['tiles'])else'household_rug_left',base)
 def elite(self,c,x,y,name,m,data):
  raw=tuple(c['tiles']);base=self.base(name)
  if c['tileset']=='TILESET_ELITE_FOUR_ROOM':
   if raw in ((1,1,1,1),(17,17,1,1),(82,82,82,82)):return self.native(base,'kanto_league_native_arena_floor')
   if raw==(0,0,0,0):return self.native(self.room('FR_POKEMON_LEAGUE_AGATHAS_ROOM').ref(0),'kanto_league_original_unlit_void')
   if raw==(16,16,16,16):return self.native(self.room('FR_POWER_PLANT').ref(649),'kanto_league_complete_stone_partition')
   if raw in ((32,33,48,49),(34,35,50,51)):
    return self.template('kanto_special_complete_statue_head'if raw[0]==32 else'kanto_special_complete_statue_plinth',base)
   if raw==(4,4,20,20):return self.rug(c,x,y,m,data,base)
   trees={(11,12,27,28):'northwest',(13,31,29,31):'northeast',(46,47,31,31):'southwest',(10,31,31,31):'southeast'}
   if name=='KOGAS_ROOM':
    grass=self.room('FR_CELADON_CITY_GYM').ref(641)
    if raw in trees:return self.template('dense_forest_tree_'+trees[raw],grass)
    if raw in ((31,31,31,31),(31,31,30,31),(30,31,31,31),(31,31,30,30)):return self.native(grass,'kanto_koga_native_flat_turf')
   if raw==(2,2,2,2)and name=='BRUNOS_ROOM':return self.native(self.room('EM_LAVARIDGE_TOWN','emerald').ref(819),'kanto_bruno_native_magma')
   if raw==(64,65,66,67):return self.recolor(c,STONE,'kanto_league_complete_original_compact_stairs')
   if raw in ELITE_TRIM:
    colors=PURPLE if name=='WILLS_ROOM'and any(t in(14,90,92,93)for t in raw)else RED if name=='BRUNOS_ROOM'and any(t in(2,56,91)for t in raw)else STONE
    if name=='BRUNOS_ROOM'and any(t in(2,56,91)for t in raw):
     magma=self.room('EM_LAVARIDGE_TOWN','emerald').ref(819);counts=Counter(preview.native_donor(self.cache,magma,self.packed).get_flattened_data());colors=[[255,206,0],[255,99,0],list(counts.most_common(1)[0][0][:3]),[156,49,0]]
    return self.recolor(c,colors,'kanto_league_original_platform_portal_and_patterned_trim')
  if name=='LANCES_ROOM':
   if raw==(151,151,151,151):return self.native(base,'kanto_champion_native_arena_floor')
   if set(raw)<={59,60,61}:return self.recolor(c,RED,'kanto_champion_complete_original_red_carpet')
   if raw==(4,4,20,20):return self.rug(c,x,y,m,data,base)
   if c['game']in('gold','silver'):
    if raw in((46,47,62,63),(78,79,94,95)):return self.template('kanto_special_complete_statue_head'if raw[0]==46 else'kanto_special_complete_statue_plinth',base)
    if raw in((90,90,90,74),(90,90,74,74),(90,74,90,74),(74,74,74,74)):
     return self.recolor(c,[[255,239,247],[239,189,214],[206,140,181],[112,72,112]],'kanto_champion_complete_original_pink_arena_paving')
    if raw in((73,73,73,73),(73,73,77,77),(37,39,53,23),(53,23,53,23),(53,23,88,89),(75,76,91,92),(84,85,84,85)):
     return self.recolor(c,STONE,'kanto_champion_complete_original_compact_portal_pilasters_and_steps')
   # The two original halls contain complete one-cell sculptural pilasters,
   # a32px shutter and banners unlike FRLG's48px pillars. Keep their entire
   # original assembly; native floor-only8px pieces use the exact new floor.
   if all(t in LANCE_ORNAMENT for t in raw):
    counts=Counter(preview.native_donor(self.cache,base,self.packed).get_flattened_data());flat=list(counts.most_common(1)[0][0][:3]);stone=copy.deepcopy(STONE);stone[1]=flat
    colors=[(RED if a.get('palette')==2 else [flat]*4 if t in(93,151,209,210,211,212) else GOLD if t in(193,194,195,196,197,198)else stone)for t,a in zip(raw,c['attributes'])]
    return self.recolor(c,colors,'kanto_champion_complete_original_ornate_hall')
  return None
 def explicit(self,c,x,y,name,m,data):
  raw=tuple(c['tiles']);base=self.base(name)
  gc=self.room('FR_CELADON_CITY_GAME_CORNER')
  if name in('CELADON_CAFE','CELADON_GAME_CORNER','CELADON_GAME_CORNER_PRIZE_ROOM'):
   if raw==(6,7,8,9):return self.template('johto_complete_native_region_map',gc.ref(gc.layout['mids'][0]))
   if raw in((166,167,34,35),(42,43,58,59),(4,5,34,35),(34,35,50,51)):
    left=tuple(e.cell_info(self.cache,c['game'],data,m['tileset'],m['blocks'][y//2*m['width']+(x-1)//2],y%2*2+(x-1)%2)['tiles'])if x>0 else()
    right=left==raw;head=raw[0]in(166,4)
    return dict(kind='native_composite',base=base,parts=gc.rect(32+16*int(right),8 if head else 24,16,16),role='kanto_casino_complete_native_drink_dispenser_'+str(int(right))+'_'+str(int(head)))
   books={(22,23,38,39):0,(23,24,39,40):1,(54,55,17,18):2,(55,56,17,18):3}
   if raw in books:return self.template('johto_house_bookcase_'+str(books[raw]),base)
   if name=='CELADON_CAFE':
    if x in(2,3)and y in(1,2,3,5,6,7):return self.table(x,y,base)
    if raw==(70,71,86,87):return self.foreground(self.room('FR_VERMILION_CITY_GYM'),696,base,'kanto_cafe_complete_native_bin')
   if raw==(135,136,151,152):
    lab=self.room('FR_OAKS_LAB');return dict(kind='native_composite',base=gc.ref(gc.layout['mids'][0]),parts=lab.rect(96,16,16,16),role='kanto_casino_complete_native_wall_notice')
   if raw in((77,77,196,81),(77,77,81,81)):return self.recolor(c,[[240,248,248],[168,192,224],[96,128,184],[48,64,104]],'kanto_casino_complete_original_compact_service_terminal')
  if name=='FUCHSIA_GYM':
   room=self.room('FR_FUCHSIA_CITY_GYM')
   if raw==(1,1,17,17):return self.native(room.ref(644),'kanto_fuchsia_complete_native_wall_header')
   if raw in((76,77,92,93),(78,79,94,95)):return self.template('kanto_special_complete_statue_head'if raw[0]==76 else'kanto_special_complete_statue_plinth',base)
  if name=='OAKS_LAB':
   if raw==(8,9,24,25):return self.template('johto_complete_native_region_map',self.room('FR_OAKS_LAB').ref(648))
   if raw==(37,38,16,16):return self.template('johto_domestic_complete_single_bay_bookcase_1',base)
  if name=='LAV_RADIO_TOWER_1F':
   office=self.room('FR_SILPH_CO_1F')
   if raw==(90,7,23,23):return self.native(office.ref(880),'kanto_radio_complete_native_reception_front')
   if raw==(36,6,23,22):return self.template('johto_gate_complete_desk_computer',office.ref(880))
  if name=='SAFFRON_GYM':
   room=self.room('FR_SAFFRON_CITY_GYM')
   walls={(4,4,20,20):646,(3,4,19,20):645,(4,5,20,21):647}
   if raw in walls:return self.native(room.ref(walls[raw]),'kanto_saffron_complete_native_wall_'+str(walls[raw]))
   if raw in((3,5,12,13),(12,13,12,13)):return self.recolor(c,[[240,240,248],[184,168,224],[112,104,160],[0,0,0]],'kanto_saffron_original_compact_partition_caps')
   if raw==(34,35,50,51):return self.native(room.ref(659),'kanto_saffron_complete_native_teleport_pad')
   if raw in((7,8,23,24),(9,25,48,49)):return self.template('kanto_special_complete_statue_head'if raw[0]==7 else'kanto_special_complete_statue_plinth',base)
  if name in('UNDERGROUND_PATH','VERMILION_PORT_PASSAGE')and raw==(12,13,12,13):
   return self.recolor(c,[[240,248,240],[176,192,200],[104,128,144],[0,0,0]],'kanto_passage_original_compact_sidewall')
  if name=='VERMILION_GYM':
   room=self.room('FR_VERMILION_CITY_GYM')
   if raw==(45,45,45,45):return self.native(room.ref(0),'kanto_vermilion_original_solid_outside_void')
   if raw==(1,16,17,18):return self.native(base,'kanto_vermilion_native_clear_floor')
   if raw==(70,71,86,87):return self.foreground(room,696,base,'kanto_vermilion_complete_native_switch_bin')
   if raw in((66,67,82,83),(68,69,84,85)):return self.template('kanto_special_complete_statue_head'if raw[0]==66 else'kanto_special_complete_statue_plinth',base)
   if raw in((73,73,45,45),(73,74,45,76),(77,77,91,91),(72,73,75,45),
     (45,76,45,76),(75,45,75,45),(72,73,88,89),(73,73,89,89),(73,74,89,90),
     (92,77,94,91),(77,93,91,95)):
    return self.recolor(c,[[240,248,240],[176,192,200],[104,128,144],[0,0,0]],'kanto_vermilion_complete_original_electrical_barrier_and_caps')
  if name=='SAFARI_ZONE_BETA':
   if raw==(20,20,20,20):
    a=self.template('freshwater_pond_interior');a['role']='freshwater_pond_interior';return a
   if raw in((1,1,1,3),(3,1,1,1)):return self.template('decorative_flower_southeast'if raw[0]==1 else'decorative_flower_northwest')
   if raw==(2,2,2,2):return self.template('short_nonencounter_grass')
  return None
 def same(self,c,names,game=None):
  game=game or c['game'];choices=[]
  for name in names:
   for r in self.index[game,name,c['sourceHash']]:
    if game==c['game'] and (r['tileset']!=c['tileset'] or r.get('sourceCollision')!=c['collision'] or r.get('sourcePriority')!=[bool(a.get('priority'))for a in c['attributes']] or r.get('sourcePalettes')!=[a.get('palette',1)for a in c['attributes']]):continue
    if game=='red'and r.get('kind')=='source_palette':continue
    choices.append(r)
  bypixels={}
  for r in choices:bypixels[catalog.sha(preview.replacement_image(self.cache,r,self.packed,ROOT).tobytes())]=r
  if len(bypixels)!=1:return None
  r=next(iter(bypixels.values()));a=artwork(r);a['role']=r['role'];a['reviewedCounterpart']=dict(game=r['game'],map=r.get('map'),id=r['id'],quadrant=r['quadrant'],sourceHash=r['sourceHash']);return a
 def handle(self,c,x,y,name,m,data):
  if name=='CELADON_CAFE'and x in(2,3)and y in(1,2,3,5,6,7):return self.explicit(c,x,y,name,m,data)
  if name in ('WILLS_ROOM','KOGAS_ROOM','BRUNOS_ROOM','KARENS_ROOM','LANCES_ROOM'):return self.elite(c,x,y,name,m,data)
  if tuple(c['tiles'])in((3,3,19,19),(2,2,18,18))and c['collision']in(112,120):
   base=self.base(name)
   if base is None:base=self.room('FR_ROCKET_HIDEOUT_B1F').ref(641)
   return self.rug(c,x,y,m,data,base)
  a=self.same(c,SOURCES.get(name,()))
  if a:return a
  a=self.same(c,RED_SOURCES.get(name,()),'red')
  return a if a else self.explicit(c,x,y,name,m,data)

 def room_context(self,a,c,x,y,name):
  """A copied glyph never brings its former room floor along with it."""
  casino_names={'CELADON_CAFE','CELADON_GAME_CORNER','CELADON_GAME_CORNER_PRIZE_ROOM','SAFARI_ZONE_MAIN_OFFICE'}
  if not a.get('base'):
   if name in casino_names and a.get('donor') and 'floor' in a['role']:
    a=copy.deepcopy(a);old=copy.deepcopy(a['donor']);a['donor']=self.base(name)
    a['reviewedRoomFloorContext']=dict(originalBase=old,actualRoomBase=copy.deepcopy(a['donor']),rule='Literal native floor beneath equipment uses the actual room carpet')
   return a
  a=copy.deepcopy(a);old=copy.deepcopy(a['base']);new=None;role=a['role']
  if name in casino_names:
   # 641 is the actual native blue wall. 657 is the yellow carpet used by
   # all source floor cells. Small display notices alone remain on the wall;
   # counter surfaces/terminal bases retain their own complete native units.
   wall_object=any(tag in role for tag in ('wall_notice','region_map','complete_window'))or(y==0 and any(tag in role for tag in ('bookcase','counter_back_cap')))
   if not wall_object and not ('prize_terminal' in role and old.get('id')==673):new=self.base(name)
  elif name=='OAKS_LAB':
   lab=self.room('FR_OAKS_LAB')
   if old.get('game')!='firered' or old.get('tileset')!=lab.pair:
    wall_object=('bookcase' in role and y==0)or any(tag in role for tag in ('wall_notice','region_map','complete_window'))
    new=lab.ref(648) if wall_object else self.base(name)
  if new is None:return a
  a['base']=copy.deepcopy(new)
  # Older narrow-bookcase/table helpers inserted explicit pure background
  # rectangles among their foreground pieces. Rebase those too; their native
  # glyph caps, feet, legs, shadows and layer hashes stay intact.
  known={('firered','house',1),('firered','house',40),('firered','player_house',1),('firered','player_house',40),
   ('firered','pewter_gym',704),('firered','pewter_gym',705),('firered','pewter_gym',715)}
  known.add((old.get('game'),old.get('tileset'),old.get('id')))
  for part in a.get('parts',[]):
   ref=part['donor']
   if (ref.get('game'),ref.get('tileset'),ref.get('id'))in known:
    part['donor']=copy.deepcopy(new)
    part.pop('layers',None);part.pop('layerHashes',None)
  a['reviewedRoomFloorContext']=dict(originalBase=old,actualRoomBase=copy.deepcopy(new),
   rule='Actual native target floor below furniture; real native wall retained only for wall objects',pixel_scale=1)
  return a

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--validate',action='store_true');p.add_argument('--activate',action='store_true');p.add_argument('--previews',action='store_true');p.add_argument('--games',default='gold,silver,crystal');args=p.parse_args();assert not args.activate or args.validate
 assert not args.activate or args.games.split(',')==list(e.GAMES),'Activation must preserve all three cartridges'
 OUT.mkdir(parents=True,exist_ok=True);v=Review();rows=[];held=[];stats=[]
 for game in args.games.split(','):
  assert game in e.GAMES
  data=e.source(v.cache,game)
  for name in sorted(NAMES):
   if name not in data['maps']:continue
   if name=='SAFARI_ZONE_BETA'and game!='crystal':continue # GS's unused beta area references unimported255 graphics.
   m=data['maps'][name];assert m['tileset']in SETS
   selected=[r for r in v.active if r['game']==game and r['tileset']==m['tileset']and r.get('map',name)==name]
   generic={(r['id'],r['quadrant'])for r in selected if r.get('x')is None};pos={(r['id'],r['quadrant'],r['x'],r['y'])for r in selected if r.get('x')is not None};added=0;missing=0
   for y in range(m['height']*2):
    for x in range(m['width']*2):
     bid=m['blocks'][y//2*m['width']+x//2];q=y%2*2+x%2
     force=(name=='LANCES_ROOM'and set(e.cell_info(v.cache,game,data,m['tileset'],bid,q)['tiles'])<={59,60,61})or(name=='CELADON_CAFE'and x in(2,3)and y in(1,2,3,5,6,7))
     if ((bid,q)in generic or(bid,q,x,y)in pos)and not force:continue
     missing+=1
     try:c=e.cell_info(v.cache,game,data,m['tileset'],bid,q)
     except AssertionError as ex:raise AssertionError((game,name,bid,q,x,y,str(ex)))from ex
     a=v.handle(c,x,y,name,m,data)
     if a is None:
      held.append(dict(game=game,map=name,tileset=m['tileset'],id=bid,quadrant=q,x=x,y=y,raw=c['tiles'],collision=c['collision'],sourceHash=c['sourceHash']));continue
     a=v.room_context(a,c,x,y,name)
     r=dict(game=game,style='gen3',map=name,tileset=m['tileset'],id=bid,quadrant=q,x=x,y=y,sourceCells=[[x,y]],sourceHash=c['sourceHash'],sourceFiles=data['fingerprints'][m['tileset']],sourceCollision=c['collision'],sourcePriority=[bool(a.get('priority'))for a in c['attributes']],sourcePalettes=[a.get('palette',1)for a in c['attributes']],status='reviewed',_positioned=force,evidence='Explicit equivalent room purpose and complete original source glyph reviewed against its native Gen3 counterpart. All native parts stay at1:1 pixels with matching room floors. Original source geometry, collisions, events, warps and interactions remain unchanged.');r.update(a);r['compositionPixelHash']=catalog.sha(preview.replacement_image(v.cache,r,v.packed,ROOT).tobytes());rows.append(r);added+=1
   if missing:stats.append(dict(game=game,map=name,prior_remaining=missing,added=added,remaining=missing-added))
 grouped=defaultdict(list)
 for r in rows:grouped[r['game'],r['map'],r['id'],r['quadrant']].append(r)
 rows=[]
 for g in grouped.values():
  if not any(r.get('_positioned')for r in g)and len({json.dumps(artwork(r),sort_keys=True)for r in g})==1:
   r=g[0];r.pop('x');r.pop('y');r['sourceCells']=[z['sourceCells'][0]for z in g];rows.append(r)
  else:rows.extend(g)
 for r in rows:r.pop('_positioned',None)
 (OUT/'candidates.json').write_text(json.dumps(rows,indent=2));(OUT/'held.json').write_text(json.dumps(held,indent=2));summary=dict(rows=len(rows),cells=sum(s['added']for s in stats),remaining=sum(s['remaining']for s in stats),maps=stats);(OUT/'summary.json').write_text(json.dumps(summary,indent=2))
 unique={}
 for z in held:
  if z['game']=='crystal':unique.setdefault((z['map'],tuple(z['raw']),z['collision']),z)
 (OUT/'held-unique.json').write_text(json.dumps(list(unique.values()),indent=2))
 if args.previews:
  for name in ('WILLS_ROOM','KOGAS_ROOM','BRUNOS_ROOM','KARENS_ROOM','LANCES_ROOM','CELADON_GAME_CORNER','CELADON_CAFE','OAKS_LAB','FUCHSIA_GYM','SAFFRON_GYM','VERMILION_GYM','LAV_RADIO_TOWER_1F','VERMILION_PORT_PASSAGE','SAFARI_ZONE_BETA'):
   preview.map_preview(v.cache,OUT,'crystal',name,'staged-'+name,v.active+rows,v.packed,2,ROOT)
 if args.validate:
  assert not held,'Unreviewed source shapes remain in the requested room family'
  proof=e.validate_batch(rows,SimpleNamespace(cache=v.cache,engine=ROOT.parent/'.tools/engine-0395',output=OUT),ROOT);(OUT/'proof.json').write_text(json.dumps(proof,indent=2))
  if args.activate:write_rows(TARGET,rows)
 print(json.dumps({k:val for k,val in summary.items()if k!='maps'}))

if __name__=='__main__':main()
