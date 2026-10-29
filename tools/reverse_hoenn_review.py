"""Reviewed native GB counterparts for Hoenn's shared terrain and structures.

Only direct, explicitly named terrain/floor counterparts may be reversed from
the earlier review. Composite building/furniture rows are never auto-inverted.
Native GBA aliases require the same pair family, behavior and full pixel hash.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import copy
import json
from pathlib import Path

import catalog, preview
from reverse_common import ReverseReview, ROOT, STYLES

GAMES=('ruby','sapphire','emerald')
def ground_ref(review,style):
 # Hoenn's grassy fields use the native Johto nonencounter lawn. Kanto's
 # urban pale ground is a different reviewed material, not this tile's base.
 return(review.gb_ref('red','PALLET_TOWN',1,0)if style=='gen1'
        else review.gb_ref('crystal','NEW_BARK_TOWN',2,0))
SAFE_OUTDOOR={
 'open_grassy_ground','short_nonencounter_grass','tall_grass',
 'decorative_flower_northwest','decorative_flower_southeast','freestanding_sign',
 'coastal_ocean_water_interior','freshwater_pond_johto_repeat_368',
 'south_ledge_left_cap','south_ledge_center','south_ledge_center_tufted','south_ledge_right_cap',
}
SAFE_CAVE={
 'cave_rock_floor','cave_raised_rock_plateau_top','cave_raised_rock_mass_front',
 'cave_raised_plateau_north_rim','cave_rock_mass_west_side','cave_rock_mass_east_side',
 'cave_convex_northwest','cave_convex_northeast','cave_convex_southwest','cave_convex_southeast',
 'johto_cave_inward_wall_539','johto_cave_inward_wall_540','johto_cave_stone_steps',
 'cave_plain_water','cave_native_vertical_waterfall',
}
RED_EQUIVALENT={
 'cave_raised_rock_plateau_top':'cave_raised_rock_mass_top',
 'cave_raised_plateau_north_rim':'cave_north_mass_edge',
 'cave_rock_mass_west_side':'cave_west_mass_face',
 'cave_rock_mass_east_side':'cave_east_mass_face',
 'cave_convex_northwest':'cave_large_nw_corner','cave_convex_northeast':'cave_large_ne_corner',
 'cave_convex_southwest':'cave_large_sw_corner','cave_convex_southeast':'cave_large_se_corner',
 'johto_cave_stone_steps':'cave_rock_stairs',
}

_NATIVE_INDICES={}
def native_geometry(f,game,pair,mid):
 """Exact indexed layer geometry, allowing the native R/S/E palette to differ."""
 key=game,pair
 if key not in _NATIVE_INDICES:
  root=f.cache/game/'data/generated/gba/native'/pair;parts={}
  for name,file in(('under','mids.idx'),('mid','mids_mid.idx'),('over','mids_over.idx')):
   p=root/file
   if p.exists():
    mids,pixels,_=catalog.read_idx(p)
    for i,m in enumerate(mids):
     # Preserve transparency exactly for overlay layers; the low nibble is
     # the native4bpp pixel. A different palette bank alone is cosmetic.
     raw=pixels[i*256:(i+1)*256]
     parts.setdefault(m,[]).append(bytes((v%16 if name=='under'or v else 255)for v in raw))
  _NATIVE_INDICES[key]={m:tuple(p)for m,p in parts.items()}
 return _NATIVE_INDICES[key][mid]
# Native GBA floor roles whose complete original GB cell is a plain floor.
# Functional/puzzle/invisible-floor rows are not generalized across rooms.
SAFE_FLOORS={
 'interior_home1_floor','interior_home2_floor','interior_house_floor','interior_lab_floor',
 'interior_center_floor','interior_mart_floor','interior_facility_floor','interior_tower_floor',
 'interior_rocket_floor','interior_mansion_floor','interior_gate_floor','interior_tunnel_floor',
 'interior_ship_floor','interior_shiproom_floor','interior_museum_floor','interior_fanclub_floor',
 'interior_labroom_floor','interior_dept_floor','interior_gamecorner_floor',
 'johto_house_plain_floor','johto_domestic_wood_floor','johto_labrooms_school_floor',
 'johto_shop_complete_floor','johto_gym_native_tiled_floor','johto_battle_lobby_floor',
 'johto_battle_battle_room_tiled_floor','johto_gate_public_floor',
}


def forward_rows():
 rows=[]
 for path in sorted((ROOT/'mappings').glob('*.lua')):
  if path.name.startswith('reverse_'):continue
  for row in preview.read_reviewed(path):
   donor=row.get('donor',{})
   if(row['game']in('red','crystal')and row.get('kind')in(None,'native')and
      donor.get('game')in('ruby','sapphire','emerald','firered','leafgreen')and donor.get('kind')is None):
    rows.append(row)
 return rows


def donor_ref(f,row):
 game=row['game'];map_id=row.get('map')
 if not map_id:
  map_id=next(n for n,m in f.imp.table(game,'maps').items()
   if isinstance(m,dict)and m.get('tileset')==row['tileset']and row['id']in m.get('blocks',[]))
 ref=f.gb_ref(game,map_id,row['id'],row['quadrant'])
 assert ref['hash']==row['sourceHash'],'Inverse witness source changed'
 return ref


def simple_materials(f,prior):
 candidates=defaultdict(list)
 for r in prior:candidates[r['game'],r['role']].append(r)
 def choose(game,role):
  if game=='crystal'and role in('south_ledge_left_cap','south_ledge_center','south_ledge_right_cap'):
   # Crystal's approach collision and stone face occupy separate native
   # cells. The complete8px stone glyph from its south ledge supplies the
   # matching Hoenn one-cell face; source jump behavior remains Hoenn's.
   return f.gb_ref('crystal','ROUTE_29',87,2)
  options=candidates.get((game,role),[])
  if not options:return None
  # Prefer cells from the classic common outdoor/cave source family. All
  # selected role names have explicit earlier visual review evidence.
  rank=lambda r:(r['tileset']not in('OVERWORLD','CAVERN','TILESET_JOHTO','TILESET_CAVE'),r.get('map',''),r['id'],r['quadrant'])
  return donor_ref(f,min(options,key=rank))
 witnesses={}
 for r in prior:
  d=r['donor'];role=r['role']
  if d['game']!='emerald' or role not in SAFE_OUTDOOR|SAFE_CAVE|SAFE_FLOORS:continue
  if not(d['tileset'].startswith('general__')or d['tileset'].startswith('building__')):continue
  if role=='freshwater_pond_johto_repeat_368':role='coastal_ocean_water_interior'
  native=f.imp.cell_index('emerald')[d['tileset'],d['id']]
  key=d['tileset'],d['id']
  # Keep an explicit semantic identity. A floor that only happens to share
  # RGB with another room is not allowed to acquire the other room's role.
  witnesses.setdefault(key,(role,native,r))
 for (pair,mid),(role,source,witness)in sorted(witnesses.items()):
  for style,gb in STYLES.items():
   use_role=RED_EQUIVALENT.get(role,role)if gb=='red'else role
   ref=choose(gb,use_role)
   if ref is None and role in SAFE_FLOORS:
    # A native house/lab/shop floor can use the equivalent complete classic
    # floor even when only the other GB generation witnessed the GBA room.
    fallback=('interior_lab_floor'if 'lab'in pair else'interior_mart_floor'if any(n in pair for n in('shop','mart'))else'interior_house_floor'if'house'in pair else None)
    if fallback:ref=choose(gb,fallback)
   if ref is None:continue
   for game in GAMES:
    index=f.imp.cell_index(game)
    canonical=index.get((pair,mid))
    if not canonical or not canonical.get('used_by_map_count'):continue
    # The actual R/S gym cell513 is unused black, unlike Emerald's new
    # brick floor. Its contact was reviewed and explicitly excluded.
    if pair=='building__lavaridge_gym'and game!='emerald':continue
    for (candidate_pair,candidate_mid),cell in index.items():
     if not cell.get('used_by_map_count'):continue
     if candidate_mid!=mid:continue
     if candidate_pair!=pair and not(mid<512 and pair.startswith('general__')and candidate_pair.startswith('general__')):continue
     if cell.get('behavior')!=canonical.get('behavior'):continue
     if native_geometry(f,game,candidate_pair,candidate_mid)!=native_geometry(f,game,pair,mid):continue
     if role=='short_nonencounter_grass'and style=='gen1':ref=f.gb_ref('red','PALLET_TOWN',1,0)
     art=f.native(ref,'reverse_hoenn_'+role)
     if role in('decorative_flower_northwest','decorative_flower_southeast'):
      from gb_theme_animation import specification
      tile=f.imp.cell_index(gb)[ref['tileset'],ref['id'],ref['quadrant']]['tiles'].index(3)
      part={'donor':ref,'srcX':tile%2*8,'srcY':tile//2*8,'w':8,'h':8,'x':4,'y':4}
      art=f.composite(ground_ref(f,style),[part],'reverse_hoenn_complete_native_flower')
      spec=specification(f.cache,ref,'flower')
      if spec:
       art['parts'][0]['animated']=True
       art.update(animated=True,animation=spec,animationCategory='flowers')
     f.row(game,candidate_pair,candidate_mid,style,art,
      'Direct native GB '+role+' counterpart from the previously reviewed forward role '+witness['role']+'. Each canonical Ruby/Sapphire/Emerald cell was visually reviewed in canonical-rse contacts; unused black gym variants are excluded. The complete original GB16px cell is retained at1:1. Aliases within each cartridge require the same native cell identity, exact indexed-layer geometry and behavior. Primary General cells may be shared across actual General pairs. Source map, collision, encounters, warps and events remain unchanged.')

 # The worn doorstep/clearing is a bare ground mark, not encounter grass.
 for style,gb in STYLES.items():
  ground= f.gb_ref('red','PALLET_TOWN',1,1)if gb=='red'else f.gb_at('crystal','NEW_BARK_TOWN',6,9)
  for game in GAMES:
   index=f.imp.cell_index(game)
   for(pair,mid),cell in index.items():
    if not cell.get('used_by_map_count'):continue
    if pair.startswith('general__')and mid in(0,462,463,464,465,466,472,473,474,480,481,482):
     canonical=f.imp.cell_index(game).get(('general__petalburg',mid))
     if canonical and native_geometry(f,game,pair,mid)==native_geometry(f,game,'general__petalburg',mid)and cell.get('behavior')==canonical.get('behavior'):
      base=f.gb_ref('red','PALLET_TOWN',1,0)if style=='gen1'else choose(gb,'short_nonencounter_grass')
      if base:f.row(game,pair,mid,style,f.native(base,'reverse_hoenn_nonencounter_lawn_variant'),
       'Reviewed Hoenn outdoor nonencounter lawn/edge variant. Uses the full native GB nonencounter grass tile; original behavior remains unchanged. Exact native pixel/behavior aliases only.')
    if pair.startswith('general__')and mid==513:
     canonical=f.imp.cell_index(game).get(('general__petalburg',513))
     if canonical and native_geometry(f,game,pair,mid)==native_geometry(f,game,'general__petalburg',513)and cell.get('behavior')==canonical.get('behavior'):
      f.row(game,pair,mid,style,f.native(ground,'reverse_hoenn_worn_entry_ground'),
       'Hoenn worn entry patch uses native GB bare ground, distinct from taller encounter grass. No collision, warp or movement changes.')

 for style,gb in STYLES.items():
  grass=choose(gb,'tall_grass')
  ledge=choose(gb,'south_ledge_center')
  ground=ground_ref(f,style)
  for game in GAMES:
   for mid,ref,role in((454,grass,'foreground_tall_grass_left'),(455,grass,'foreground_tall_grass_right'),(110,ledge,'raised_ledge_outer_corner'),(142,ledge,'raised_ledge_inner_corner')):
    if ref is None:continue
    canonical=f.imp.cell_index(game).get(('general__petalburg',mid))
    if not canonical:continue
    for(pair,cmid),cell in f.imp.cell_index(game).items():
     if cmid!=mid or not pair.startswith('general__')or not cell.get('used_by_map_count'):continue
     if cell.get('behavior')!=canonical.get('behavior')or native_geometry(f,game,pair,mid)!=native_geometry(f,game,'general__petalburg',mid):continue
     art=f.native(ref,'reverse_hoenn_'+role)
     if mid in(110,142):
      places=((8,8,0),)if mid==110 else((8,0,0),(0,8,0),(8,8,8))
      art=f.composite(ground,[{'donor':ref,'srcX':sx,'srcY':8,'w':8,'h':8,'x':x,'y':y}for x,y,sx in places],'reverse_hoenn_'+role)
     f.row(game,pair,mid,style,art,
      'Visually reviewed complete Hoenn source family. Tall-grass454/455 retain native source foreground ordering. Source110 is the outer lower-right-facing ledge corner;142 is its connecting inner step, with open ground upper-left and rock face on the right/bottom. Complete native classic8px ledge-stone modules form these exact orientations over matching GB ground, joining the unchanged directional cap/body family without rotating highlights or cutting a glyph. Original source movement, collision and events remain unchanged.')

 # Hoenn's three reviewed south-facing ledge modules have the same movement
 # direction as the classic south ledge family. Each source remains guarded.
 for style,gb in STYLES.items():
  for mid,role in((213,'south_ledge_left_cap'),(135,'south_ledge_center'),(214,'south_ledge_right_cap')):
   ref=choose(gb,role)
   if ref is None:continue
   for game in GAMES:
    canonical=f.imp.cell_index(game).get(('general__petalburg',mid))
    if not canonical:continue
    for(pair,cmid),cell in f.imp.cell_index(game).items():
     if cmid!=mid or not pair.startswith('general__')or not cell.get('used_by_map_count'):continue
     if cell.get('behavior')!=canonical.get('behavior')or native_geometry(f,game,pair,mid)!=native_geometry(f,game,'general__petalburg',mid):continue
     art=f.native(ref,'reverse_hoenn_'+role)
     if gb=='crystal'and mid in(213,214):
      x=8 if mid==213 else 0
      art=f.composite(ground_ref(f,style),[{'donor':ref,'srcX':0 if mid==213 else 8,'srcY':8,'w':8,'h':8,'x':x,'y':8}],'reverse_hoenn_'+role)
     f.row(game,pair,mid,style,art,
      'Visually reviewed complete native Hoenn south ledge family: left213, middle135, right214. Native GB south-facing cap/body counterparts preserve the original jump direction, source behavior and collision. Crystal uses intact8px native stone modules for its short left/right ends, because its own approach collision and face occupy separate cells; no glyph is scaled or clipped.')


def trees(f):
 from reverse_kanto_review import tree_art
 for style in STYLES:
  ground=ground_ref(f,style)
  for game in GAMES:
   canonical=f.imp.cell_index(game)
   for(pair,mid),cell in canonical.items():
    if not pair.startswith('general__')or not cell.get('used_by_map_count'):continue
    if mid not in(468,469,470,471,476,477,478,479,484,485,486,487):continue
    source=canonical.get(('general__petalburg',mid))
    if not source or native_geometry(f,game,pair,mid)!=native_geometry(f,game,'general__petalburg',mid)or cell.get('behavior')!=source.get('behavior'):continue
    q={468:0,469:1,470:0,471:1,476:2,477:3,478:2,479:3,484:2,485:3,486:2,487:3}[mid]
    art=tree_art(f,style,q,ground)
    # Actual Hoenn trees already occupy32x32; unlike FR/LG there is no
    # decorative third row. Keep the complete native GB upper canopy.
    art['overMask']='0'*256
    f.row(game,pair,mid,style,art,
     'Complete original32x32 GB forest tree, native1:1 pixels, inside the actual32x32 Hoenn tree family:468/469 or470/471 upper canopy;476/477,480/481,484/485,486/487 trunk/base variants. No upper leaves are cropped and no nonexistent third row is cleared. The whole-object exterior mask preserves all internal highlights and exposes matching ground outside the silhouette. Original source collision, tree placement and interactions stay unchanged.')


def structure_art(f,style,kind,mid):
 """Native GB outlines, intact8px windows/16px doors, plain modular repeats."""
 gb=STYLES[style]
 source_map='PALLET_TOWN'if gb=='red'else'NEW_BARK_TOWN'
 if kind=='home':
  ox,oy,width,rh=(4,3,4,16)if gb=='red'else(12,2,4,32)
  roofs={520:(0,0),521:(1,0),522:(3,0),528:(0,1),529:(1,1),530:(3,1),536:(0,2),537:(1,2),538:(3,2)}
  edges={546:0,544:0,545:3,547:3,554:0,552:0,553:3,555:3}
  windows={562};lower={554,552,553,555,568,569,570,584}
 else:
  ox,oy,width,rh=(10,8,6,32)if gb=='red'else(4,0,6,32)
  roofs={524:(0,0),525:(2,0),526:(5,0),532:(0,1),533:(2,1),534:(5,1),578:(1,0),579:(2,0),586:(1,1),587:(2,1)}
  edges={542:0,543:5,550:0,551:5};windows={527};lower={550,551,535,564,565,585}
 sx,sy=ox*16,oy*16
 def rect(x,y,w,h,dx=0,dy=0):return f.gb_rect(gb,source_map,sx+x,sy+y,w,h,dx,dy)
 if mid in roofs:
  col,row=roofs[mid];parts=[]
  if rh==16:
   if row==0:parts+=rect(col*16,0,16,8)
   if row==2:parts+=rect(col*16,8,16,8,0,8)
   yy=8 if row==0 else 0;stop=8 if row==2 else 16
   if col in(0,width-1):
    for y in range(yy,stop):parts+=rect(col*16,8,16,1,0,y)
   else:
    for y in range(yy,stop,4):parts+=rect(col*16,4,16,4,0,y)
  elif row==0:parts=rect(col*16,0,16,16)
  elif kind=='home'and row==2:parts=rect(col*16,rh-16,16,16)
  elif col in(0,width-1):
   if kind=='lab'and gb=='red':parts=rect(col*16,16,16,16)
   else:parts=rect(col*16,8,16,16)
  else:parts=rect(col*16,8,16,16)
  return f.composite(None,parts,'classic_'+kind+'_native_roof_'+str(mid))
 # Plain GB siding is reconstructed exclusively from repeatable original
 # stripe/brick sections; no windows, frames or glyphs are cut to resize.
 if gb=='red'and kind=='home':
  parts=[]
  for y in range(0,16,4):parts+=f.gb_rect('red','PALLET_TOWN',96,88,16,4,0,y)
 elif gb=='red':
  # Native brick75 occupies this complete8px lower band. The upper band
  # contains a real window, so repeating the entire source cell is wrong.
  parts=rect(32,40,16,8)+rect(32,40,16,8,0,8)
 else:
  plain=f.gb_at('crystal','NEW_BARK_TOWN',13,4)
  parts=[{'donor':plain,'w':16,'h':16}]
 if mid in lower:
  if mid in(584,585):return f.composite(None,rect((1 if kind=='home'else 2)*16,rh+16,16,16),'classic_'+kind+'_complete_native_door')
  parts+=rect((2 if kind=='home'else 3)*16,rh+30,16,2,0,14)
 if mid in edges:
  col=edges[mid];left=col==0;x=0 if left else 8
  source_x=0 if left else width*16-8
  if kind=='home':parts+=rect(source_x,rh+(16 if mid in lower else 0),8,16,x)
  elif mid in lower:parts+=rect(source_x,rh+16,8,16,x)
  else:parts+=rect(source_x,rh+8,8,8,x,8)
 if kind=='lab'and mid not in lower:
  col=0 if mid==542 else width-1 if mid==543 else 2
  # The native Gen3 lab shares its middle roof metatile in both rows. Put
  # the complete old-game lower rim into the existing8px front cornice,
  # then retain the full native window beneath it (not a cropped frame).
  parts+=rect(col*16,rh if gb=='red'and col in(0,width-1)else rh-8,16,8)
 if mid in windows:
  if gb=='red':parts+=f.gb_rect('red','PALLET_TOWN',96,80,16,8,0,8)
  else:
   wx=40 if kind=='home'else 8
   parts+=rect(wx,rh+8,16,8,0,8)
 return f.composite(None,parts,'classic_'+kind+'_complete_native_wall_or_window_'+str(mid))


def structures(f):
 from reverse_kanto_review import exterior,runs
 layouts={
 'home':[[520,521,521,521,522],[528,529,529,529,530],[536,537,537,537,538],[546,562,560,576,545],[554,570,568,584,553]],
 'lab':[[524,578,579,525,525,525,526],[532,586,587,533,533,533,534],[532,533,533,533,533,533,534],[542,527,527,556,577,557,543],[550,535,535,564,585,565,551]]}
 extra_home={544,547,552,555,561,569}
 for style in STYLES:
  ground=ground_ref(f,style)
  for kind,layout in layouts.items():
   mids={mid for row in layout for mid in row}|(extra_home if kind=='home'else set())
   arts={mid:structure_art(f,style,kind,mid)for mid in mids}
   for mid in(578,579,586,587):
    if mid not in arts:continue
    q={578:0,579:1,586:2,587:3}[mid];path=ROOT/'assets/original/classic-vent'/(style+'-'+str(q)+'.png')
    if path.exists():arts[mid]['artOverlay']={'asset':path.relative_to(ROOT).as_posix(),'hash':catalog.sha(path.read_bytes()),'mode':'over','preserveRects':[]}
   width=len(layout[0]);whole=__import__('PIL.Image',fromlist=['Image']).new('RGBA',(width*16,80))
   for y,row in enumerate(layout):
    for x,mid in enumerate(row):whole.paste(f.render(arts[mid]),(x*16,y*16))
   bg={(255,255,255,255)}if style=='gen1'else set(f.gb_image(ground).get_flattened_data())
   outside=exterior(whole,bg);masks={}
   for y,row in enumerate(layout):
    for x,mid in enumerate(row):
     mask=[(x*16+px,y*16+py)not in outside for py in range(16)for px in range(16)]
     if mid in masks:assert masks[mid]==mask,(kind,mid,'Repeated module has different exterior context')
     masks[mid]=mask
   # Mirror-only home wall modules reuse the equivalent outer edge mask.
   for a,b in((544,546),(547,545),(552,554),(555,553),(561,560),(569,568)):
    if a in arts:masks[a]=masks[b]
   for mid,art in arts.items():
    if mid in(578,579,586,587)and not art.get('artOverlay'):continue
    mask=masks[mid];parts=[]
    for p in art['parts']:
     for span in runs([bool(mask[i])and p.get('x',0)<=i%16<p.get('x',0)+p['w']and p.get('y',0)<=i//16<p.get('y',0)+p['h']for i in range(256)]):
      q=copy.deepcopy(p);q.update(srcX=p.get('srcX',0)+span['x']-p.get('x',0),srcY=p.get('srcY',0)+span['y']-p.get('y',0),**span);parts.append(q)
    assert 0<len(parts)<=32,(kind,mid,len(parts))
    art=dict(art,parts=parts,base=ground)
    roof=(mid in({520,521,522,528,529,530,536,537,538}if kind=='home'else{524,525,526,532,533,534,578,579,586,587})or(kind=='lab'and mid not in{550,551,535,564,565,585}))
    art['overMask']=''.join('1'if v and roof else'0'for v in mask)
    for game in GAMES:
     canonical=f.imp.cell_index(game).get(('general__petalburg',mid))
     if not canonical:continue
     for(pair,cmid),cell in f.imp.cell_index(game).items():
      if cmid!=mid or not pair.startswith('general__')or not cell.get('used_by_map_count'):continue
      if cell.get('behavior')!=canonical.get('behavior')or native_geometry(f,game,pair,mid)!=native_geometry(f,game,'general__petalburg',mid):continue
      f.row(game,pair,mid,style,art,
       'Complete native GB '+kind+' modules at original pixels. Only plain roof/siding bands and complete identical window modules repeat. Native roofs, entrance frames and every selected window panel remain intact; original Hoenn80x80 homes/112x80 laboratory footprint and entrance anchors are preserved. Whole-building exterior flood keeps internal highlights and leaves unused roof corners transparent over matching GB ground. Generated classic exhaust vent only supplies the unique missing counterpart. Source collision, map layout, scripts and events stay unchanged.')


def household_floors(f,prior):
 for style,gb in STYLES.items():
  witness=next(r for r in prior if r['game']==gb and r['role']=='interior_home1_floor')
  ref=donor_ref(f,witness)
  for game in GAMES:
   pair='building__brendans_mays_house'
   for mid in(513,516,517,519):
    c=f.imp.cell_index(game).get((pair,mid))
    if c and c.get('used_by_map_count'):
     f.row(game,pair,mid,style,f.native(ref,'reverse_hoenn_native_house_wood_floor'),
      'Actual Ruby/Sapphire/Emerald player-house plain timber floor and its empty edge bands were reviewed in the native room contact. Uses the complete classic player-home floor at1:1; furniture, stairs, walls and their interactions are not inferred from floor appearance.')


def animate_water(f):
 from gb_theme_animation import specification
 for row in f.rows.values():
  ref=row.get('donor')
  if not ref or 'water'not in row['role']:continue
  c=f.imp.cell_index(ref['game'])[ref['tileset'],ref['id'],ref['quadrant']]
  if 20 not in c['tiles']:continue
  spec=specification(f.cache,ref,'water')
  if spec:
   row.update(animated=True,animation=spec,animationCategory='water')
   row['compositionPixelHash']=catalog.sha(f.render(row).tobytes())


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--validate',action='store_true');parser.add_argument('--activate',action='store_true');args=parser.parse_args()
 assert not args.activate or args.validate
 f=ReverseReview('hoenn',GAMES)
 prior=forward_rows()
 simple_materials(f,prior)
 trees(f)
 structures(f)
 household_floors(f,prior)
 animate_water(f)
 target=ROOT/'mappings/reverse_hoenn.lua'if args.activate else f.out/'candidates.lua'
 f.write(target)
 stats=[]
 for game,prefix in(('ruby','RU'),('sapphire','SA'),('emerald','EM')):
  for suffix in('LITTLEROOT_TOWN','OLDALE_TOWN','ROUTE101','LITTLEROOT_TOWN_PROFESSOR_BIRCHS_LAB','LITTLEROOT_TOWN_BRENDANS_HOUSE_1F'):
   for style in STYLES:stats.append(f.map_preview(game,prefix+'_'+suffix,style))
 (f.out/'coverage.json').write_text(json.dumps(stats,indent=2))
 if args.validate:print(json.dumps(f.validate(),indent=2))
 print(json.dumps({'rows':len(f.rows),'styles':dict(Counter(r['style']for r in f.rows.values())),'scenes':stats},indent=2))

if __name__=='__main__':main()
