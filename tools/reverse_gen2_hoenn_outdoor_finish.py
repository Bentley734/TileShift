"""Explicit Crystal counterparts for reviewed Hoenn outdoor/natural families.

Only missing shared Gen2-style pair-global rows are authored. Source maps,
actors, behavior, collision, events, the Gen1 theme and reviewed early towns
remain unchanged. Ambiguous source objects are recorded privately for review.
"""
from __future__ import annotations
import argparse,copy,json,re,zlib
from collections import Counter,defaultdict
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import catalog,preview
from reverse_common import ReverseReview,ROOT
from reverse_hoenn_review import native_geometry,ground_ref
from interior_review import decode_layout
from johto_remaining_review import artwork
from reverse_kanto_review import exterior,runs
from gb_theme_animation import specification,foreground_frames

GAMES=('ruby','sapphire','emerald')
TARGET=ROOT/'mappings/reverse_gen2_hoenn_outdoor_finish.lua'
# Immutable binding of the original contact sequence to every actual native
# family/MID/indexed-geometry/behavior identity AND all source RGBA hashes.
# Additional facility/border/dynamic keys append; changing any original source
# requires a fresh visual review before this fingerprint may be updated.
REVIEWED_BODY_GROUP_COUNT=7440
REVIEWED_BODY_GROUP_FINGERPRINT='60a105629d99ea8ec84112bd9570e2a7fdfb48b80b14eb9add2ae32d5eb5c25e'
INTERIOR_SECONDARIES={'general__bike_shop','general__inside_of_truck','general__ship','general__inside_ship',
 'general__contest','general__battle_palace','general__battle_tent','general__battle_frontier','general__facility'}
FACILITY_OUTDOOR_IDS={804,805,808,809,810,811,812,813,814,815,816,817,818,823,824,825,826,827,828,829,830,831,832,833,834,835,
 702,703,718,719,819,820,861,947,968,969,970,971,972,973}
CITY_BUILDING_RESERVED={'general__mauville':{623,631,643,644,645,651,652,653,659,661,667,669,676,677,684,685},
 'general__rustboro':{699,707,548,549,550,566,574,567,556,557,558,532,533,534,578,535,540,541,543,542}}

def digest(value):return catalog.sha(json.dumps(value,sort_keys=True,separators=(',',':')).encode())
def identity(row):return(row['game'],row['style'],row['tileset'],row['id'],row.get('map'))
def scope(pair,mid):return pair.startswith('general__')and(mid<512 or pair not in INTERIOR_SECONDARIES or pair=='general__facility'and mid in FACILITY_OUTDOOR_IDS)

class Review(ReverseReview):
 def __init__(self):
  super().__init__('gen2-hoenn-outdoor-finish',GAMES)
  paths=list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(ROOT/'main.lua').read_text())))
  self.prior=[];self.locations={}
  # The shipped result is only a read-only recipe template pool. Its keys
  # MUST NOT become occupied: a repeat run reconstructs all source bindings
  # after integration has removed the exact older superseded rows.
  self.templates=preview.read_reviewed(TARGET)if TARGET.exists()else[]
  for path in paths:
   if ROOT/path==TARGET:continue
   for i,row in enumerate(preview.read_reviewed(ROOT/path)):
    self.prior.append(row);self.locations[identity(row)]=(path,i,row)
  self.occupied={identity(row)for row in self.prior}
  self.groups={};self.usage=defaultdict(list);self.counts=Counter();self.uncertain=[];self.proofs={};self.recipes={}
  self.group_list=[]
  self.supersessions={}
  self.target_module=TARGET

 def neutral(self,ref):
  key=('neutral',digest(ref))
  if key not in self._gb:
   ts=self.imp.table('crystal','tilesets')[ref['tileset']];sheet=Image.open(self.cache/'crystal'/ts['image']).convert('RGBA')
   block=catalog.lua_array(catalog.dict_at(ts['blocks'],ref['id']+1))
   self._gb[key]=preview.native_cell(sheet,ts,block,ref['quadrant'])
   assert catalog.sha(self._gb[key].tobytes())==ref['hash']
  return self._gb[key]

 def gb_image(self,ref):
  if ref.get('game')=='crystal'and ref.get('monochrome'):
   image=self.neutral(ref);assert set(image.get_flattened_data())=={(0,0,0,255)},'Only exact native neutral black canvases may bypass DAY palettes'
   return image
  return super().gb_image(ref)

 def preserve_black_canvases(self):
  opaque_black=catalog.sha(Image.new('RGBA',(16,16),(0,0,0,255)).tobytes())
  ref=None
  for(ts,bid,q),c in self.imp.cell_index('crystal').items():
   if c['grayscale_pixel_sha256']!=opaque_black or not c['used_by_map_count']:continue
   map_id=next((n for n,m in self.imp.table('crystal','maps').items()if isinstance(m,dict)and m.get('tileset')==ts),None)
   if map_id:
    ref=self.gb_ref('crystal',map_id,bid,q);ref['monochrome']=True;ref['palettes']=[[[255,255,255],[170,170,170],[85,85,85],[0,0,0]]for _ in range(8)];break
  assert ref and set(self.gb_image(ref).get_flattened_data())=={(0,0,0,255)}
  corrected=[]
  for group in self.group_list:
   touched=False
   for item in group['source']:
    if item['hash']!=opaque_black:continue
    k=(item['game'],'gen2',item['pair'],item['mid'],None);prior=self.locations.get(k)
    if prior and set(self.render(prior[2]).get_flattened_data())=={(0,0,0,255)}:continue
    art=self.native(ref,'reverse_gen2_exact_native_black_canvas')
    new=self.row(item['game'],item['pair'],item['mid'],'gen2',art,
     'The actual complete native source cell is opaque black, not grass or another room floor. A complete actual Crystal neutral-black glyph preserves exactly the same1024RGBAbytes; explicit neutral palettes apply only to this already-black glyph. Source alpha, native priority, collision, puzzle triggers and all map/event data remain unchanged.')
    new['reverseGen2OutdoorReview']=dict(exact_black_canvas=True,pixel_scale=1)
    if prior:
     path,index,old=prior;self.supersessions[k]=dict(module=path,old_index=index,old_row=old,full_row_sha256=digest(old),new_module=Path(getattr(self,'target_module',TARGET)).relative_to(ROOT).as_posix(),new_row=new)
    corrected.append(dict(source=list(k),existing_wrong_lawn_recipe=bool(prior),exact_rgba_sha256=opaque_black))
    touched=True
   if touched and all(s['hash']==opaque_black for s in group['source']):
    self.recipes[group['review_index']]=dict(art=self.native(ref,'reverse_gen2_exact_native_black_canvas'),reason='Exact native black canvas preservation; no floor/grass inference.',proof=dict(exact_rgba_sha256=opaque_black))
  self.proofs['black_canvases_preserved']=corrected

 def raw_ref(self,tileset,raw,map_id):
  candidates=[(bid,q)for(ts,bid,q),c in self.imp.cell_index('crystal').items()if ts==tileset and tuple(c['tiles'])==tuple(raw)]
  assert candidates,(tileset,raw)
  bid,q=min(candidates);return self.gb_ref('crystal',map_id,bid,q)

 def emit(self,group,art,reason,proof=None):
  assert group['review_index']not in self.recipes
  assert group['mid']not in CITY_BUILDING_RESERVED.get(group['family'],set()),('City-building agent owns this source family',group['family'],group['mid'])
  self.recipes[group['review_index']]=dict(art=copy.deepcopy(art),reason=reason,proof=proof)
  for item in group['missing']:
   row=self.row(item['game'],item['pair'],item['mid'],'gen2',art,
    reason+' Source family visually reviewed in source-contact-'+f"{group['review_index']//64+1:02}"+'; actual per-cartridge source hashes, indexed under/mid/over geometry and behavior are verified. Entire native Crystal glyphs retain1:1 pixel scale. Source collision, elevations, encounter flags, warps, actors, scripts and events are unchanged; no GBA map-position scope.')
   row['reverseGen2OutdoorReview']=dict(review_index=group['review_index'],source_geometry_behavior_identity=group['source_identity'],pixel_scale=1,proof=copy.deepcopy(proof or{}))

 def replace_art(self,row,art,note,proof):
  k=identity(row)
  if k in self.rows:
   new=self.rows[k]
   for key in set(artwork(new))|{'role','overMask','animationCategory','compositionPixelHash'}:new.pop(key,None)
   new.update(copy.deepcopy(art));new['evidence']+=' '+note;new['compositionPixelHash']=catalog.sha(self.render(new).tobytes())
  else:
   new=self.row(row['game'],row['tileset'],row['id'],'gen2',art,row['evidence']+' '+note)
   path,index,old=self.locations[k];self.supersessions[k]=dict(module=path,old_index=index,old_row=old,full_row_sha256=digest(old),new_module=Path(getattr(self,'target_module',TARGET)).relative_to(ROOT).as_posix(),new_row=new)
  new.setdefault('reverseGen2OutdoorReview',{}).update(copy.deepcopy(proof))
  if k in self.supersessions:self.supersessions[k]['new_row']=new
  return new

 def park_tree_art(self,q,ground):
  # A verified isolated NATIONAL_PARK tree has grass/fence immediately
  # above it: all four PARK6 quadrants comprise the WHOLE32px tree.
  # FOREST5 is a different complete dense-forest pattern. PARK6 is the
  # selected shared standalone-tree artwork for these Hoenn32px slots.
  key=('verified_complete_park_tree',q,digest(ground))
  if key in self._gb:return copy.deepcopy(self._gb[key])
  whole=Image.new('RGBA',(32,32));refs=[]
  for n in range(4):
   ref=self.gb_at('crystal','NATIONAL_PARK',6+n%2,48+n//2);refs.append(ref);whole.paste(self.gb_image(ref),(n%2*16,n//2*16))
  # Actual Park field(0,38) shares three leaf greens, so a color flood
  # would erase the deliberately flat original canopy. These reviewed
  # inclusive row bounds preserve the whole canopy, trunk and shadow.
  bounds=[(7,23),(6,26),(4,28),(2,29),(1,29),(0,30),(1,31),(1,30),
   (0,30),(1,31),(0,31),(1,30),(1,30),(2,29),(3,28),(3,27),
   (6,25),(8,23),(8,22),(9,22),(9,22),(9,22),(6,25),(4,27),
   (3,28),(2,29),(2,29),(2,29),(3,28),(4,27),(6,25),(10,21)]
  allowed={(41,115,0,255),(99,206,8,255),(181,255,82,255),(222,255,222,255)}
  whole_mask=[bounds[y][0]<=x<=bounds[y][1]for y in range(32)for x in range(32)]
  assert sum(whole_mask)==774 and all(whole_mask[y*32+x]or whole.getpixel((x,y))in allowed for y in range(32)for x in range(32)),'Native Park silhouette/background changed: re-review rather than clip leaves'
  mask=[whole_mask[(q//2*16+y)*32+q%2*16+x]for y in range(16)for x in range(16)]
  parts=[dict(donor=refs[q],srcX=p['x'],srcY=p['y'],**p)for p in runs(mask)];assert 0<len(parts)<=32
  art=self.composite(ground,parts,'classic_complete_native_tree32_'+str(q));art['overMask']=''.join('1'if v else'0'for v in mask)
  result=self.render(art);source=self.gb_image(refs[q])
  assert all(not mask[y*16+x]or result.getpixel((x,y))==source.getpixel((x,y))for y in range(16)for x in range(16))
  self.proofs.setdefault('verified_complete_park_tree',{})[str(q)]=dict(native_ref=refs[q],native_source_rect=['crystal','NATIONAL_PARK',6,48,2,2],native_ground=['crystal','NATIONAL_PARK',0,38],native_dimensions=[32,32],retained_object_pixels=sum(mask),whole_retained_pixels=774,reviewed_silhouette_sha256=digest(bounds),every_retained_native_pixel_exact=True,removed_pixels_only_native_exterior_field=True,missing_cap_rows=0,pixel_scale=1)
  whole.save(self.out/'verified-native-Park-tree32.png')
  self._gb[key]=copy.deepcopy(art);return art

 def upgrade_whole_tree_sources(self):
  effective={identity(r):r for r in self.prior};effective.update(self.rows);changed=[]
  for k,row in list(effective.items()):
   if row['game']not in GAMES or row['style']!='gen2'or row.get('map')is not None or not scope(row['tileset'],row['id']):continue
   parts=row.get('parts',[])
   def old_tree(p):
    r=p.get('donor',{});return r.get('game')=='crystal'and r.get('tileset')=='TILESET_FOREST'and r.get('id')==5
   tree=[p for p in parts if old_tree(p)]
   if not tree:continue
   qs={p['donor']['quadrant']for p in tree};assert len(qs)==1,('Unreviewed mixed tree quadrants',k)
   q=next(iter(qs));assert all(p.get('srcX',0)==p.get('x',0)and p.get('srcY',0)==p.get('y',0)for p in tree),('Unreviewed offset tree fragment',k)
   base=row.get('base')or ground_ref(self,'gen2');replacement=self.park_tree_art(q,base)
   if len(tree)==len(parts):
    art=replacement;art['role']=row['role'];art['overMask']=replacement['overMask']if'1'in row.get('overMask','')else'0'*256
   else:
    n=len(tree);assert all(old_tree(p)for p in parts[:n])and not any(old_tree(p)for p in parts[n:]),('Tree/roof ordering needs review',k)
    art=artwork(row);art.update(role=row['role'],parts=copy.deepcopy(replacement['parts'])+copy.deepcopy(parts[n:]));assert len(art['parts'])<=32
    for field in('overMask','animationCategory'):
     if field in row:art[field]=copy.deepcopy(row[field])
   self.replace_art(row,art,'The complete isolated original Crystal NationalPark PARK6 tree is the shared selected standalone-tree artwork throughout the clear Hoenn32px tree slots. All four native32px crown/root quadrants remain1:1; actual grass/fence immediately above the isolated source tree proves there is no omitted cap row. The independently reviewed774-pixel silhouette removes only original exterior field/cream; every retained native leaf, trunk and shadow pixel is exact. The different original dense-forest FOREST5 tree is also complete, but its distinct canopy is not mixed into this selected standalone-tree family. Existing roof/window/door parts, source collision/priority and all source actors/events remain unchanged.',dict(verified_native_tree_source=['crystal','NATIONAL_PARK',6,48,2,2],native_dimensions=[32,32],tree_quadrant=q,complete_native_crown_and_roots=True,source_pixel_scale=1))
   changed.append(dict(source=list(k),quadrant=q,background_of_roof=len(tree)!=len(parts)))
  self.proofs['prior_whole_trees_upgraded']=changed

 def coherent_cave_water(self,source_scope=scope):
  # A pair is the native runtime atlas scope. GeneralCave also appears
  # outdoors, so its bodies/banks must use one coherent water everywhere.
  # Only actual native GB animated WATER glyphs are replaced; stone, wood,
  # ice, tree/flower masks and waterfall/lava programs remain native/exact.
  water=self.gb_ref('crystal','UNION_CAVE_1F',15,0);sample=self.gb_image(water).crop((0,0,8,8));sets=self.imp.table('crystal','tilesets')
  water_ids={'TILESET_JOHTO':20,'TILESET_JOHTO_MODERN':20,'TILESET_KANTO':20,'TILESET_CAVE':20,'TILESET_DARK_CAVE':20,'TILESET_FOREST':20,'TILESET_ICE_PATH':53}
  from gb_theme_animation import program_layers
  def raw(ref):return self.imp.cell_index('crystal')[ref['tileset'],ref['id'],ref['quadrant']]['tiles']
  def wet(ref):
   if ref.get('game')!='crystal'or ref['tileset']not in water_ids:return set()
   tile=water_ids[ref['tileset']];layers=program_layers(sets,sets[ref['tileset']],ref)
   return {q for q,t in enumerate(raw(ref))if t==tile}if tile in layers and layers[tile]['kind']in('water','scroll')else set()
  def merge(parts):
   parts=copy.deepcopy(parts);again=True
   while again:
    again=False
    for i,a in enumerate(parts):
     for j in range(i+1,len(parts)):
      b=parts[j];rect={'srcX','srcY','w','h','x','y'}
      if {k:v for k,v in a.items()if k not in rect}!={k:v for k,v in b.items()if k not in rect}:continue
      if a['srcX']-a['x']!=b['srcX']-b['x']or a['srcY']-a['y']!=b['srcY']-b['y']:continue
      if a['x']+a['w']==b['x']and a['y']==b['y']and a['h']==b['h']:a['w']+=b['w']
      elif a['y']+a['h']==b['y']and a['x']==b['x']and a['w']==b['w']:a['h']+=b['h']
      else:continue
      parts.pop(j);again=True;break
     if again:break
   return parts
  effective={identity(r):r for r in self.prior};effective.update(self.rows);changes=[];held=[]
  for k,row in list(effective.items()):
   if row['game']not in self.games or row['style']!='gen2'or not source_scope(row['tileset'],row['id'])or row['tileset']=='general__underwater'or row.get('map')is not None or row.get('kind','native')not in('native','native_composite')or row.get('animationCategory')not in(None,'water'):continue
   art=artwork(row);parts=copy.deepcopy(art.get('parts',[]));base=art.get('base');sources=[]
   if art.get('donor'):sources=[dict(donor=art['donor'],srcX=0,srcY=0,w=16,h=16,x=0,y=0,animated=bool(row.get('animated')))]
   else:
    if base and wet(base):sources.append(dict(donor=base,srcX=0,srcY=0,w=16,h=16,x=0,y=0));base=None
    sources+=parts
   if not any(wet(p['donor'])for p in sources):continue
   direction=row.get('animation',{}).get('flowDirection');spec=specification(self.cache,water,'program',flow_direction=direction)
   already=bool(row.get('animated'))and row.get('animation')==spec and not(art.get('base')and wet(art['base']))
   for p in sources:
    ref=p['donor'];qs=wet(ref)
    if qs and(not p.get('animated')or ref['tileset']!='TILESET_CAVE'or any(self.gb_image(ref).crop((q%2*8,q//2*8,q%2*8+8,q//2*8+8)).tobytes()!=sample.tobytes()for q in qs)):already=False
   if already:continue
   unsupported=False
   for p in sources:
    ref=p['donor'];qs=wet(ref)
    if qs and p.get('gbForeground'):unsupported=True
    if p.get('animated')and ref.get('game')=='crystal':
     layers=program_layers(sets,sets[ref['tileset']],ref)
     if ref['tileset']!='TILESET_CAVE'and any(t!=water_ids.get(ref['tileset'])for t in layers):unsupported=True
   if unsupported:
    held.append(dict(source=list(k),reason='Combined independent nonwater program or alpha-water part needs separate cadence/mask review'));continue
   newparts=[];visible_water=[False]*256
   for original in sources:
    p=copy.deepcopy(original)
    for name in('srcX','srcY','x','y'):p.setdefault(name,0)
    ref=p['donor'];qs=wet(ref);sx,sy=p['srcX'],p['srcY'];ex,ey=sx+p['w'],sy+p['h']
    image=preview.gb_donor_layers(self.cache,ref,self.packed)['foreground']if p.get('gbForeground')else self.gb_image(ref)
    for yy in range(sy,ey):
     for xx in range(sx,ex):
      if image.getpixel((xx,yy))[3]:visible_water[(p['y']+yy-sy)*16+p['x']+xx-sx]=(yy//8*2+xx//8)in qs
    if not qs:newparts.append(p);continue
    pieces=[]
    for q in range(4):
     left,top=max(sx,q%2*8),max(sy,q//2*8);right,bottom=min(ex,q%2*8+8),min(ey,q//2*8+8)
     if left>=right or top>=bottom:continue
     x,y=p['x']+left-sx,p['y']+top-sy
     if q in qs:
      pieces.append(dict(donor=water,srcX=x,srcY=y,w=right-left,h=bottom-top,x=x,y=y,animated=True))
     else:
      v=copy.deepcopy(p);v.update(srcX=left,srcY=top,w=right-left,h=bottom-top,x=x,y=y)
      # The old full bank was animated because another quadrant was
      # water. Its selected ROCK quadrant must now be static; otherwise
      # the JOHTO-water program would be requested with CAVE fingerprints.
      layers=program_layers(sets,sets[ref['tileset']],ref)if ref.get('game')=='crystal'else{}
      if raw(ref)[q]not in layers:v.pop('animated',None)
      pieces.append(v)
    newparts+=merge(pieces)
   if len(newparts)>32:
    held.append(dict(source=list(k),reason='Water-part normalization exceeds checked32-part bound',parts=len(newparts)));continue
   for name in('donor','base','parts'):art.pop(name,None)
   art.update(kind='native_composite',parts=newparts,role=row['role'],animated=True,animation=spec,animationCategory='water')
   if base is not None:art['base']=base
   if'overMask'in row:art['overMask']=row['overMask']
   before=self.render(row)
   try:after=self.render(art)
   except Exception as exc:raise AssertionError(('Native water part/cadence review failed',k))from exc
   assert all(visible_water[y*16+x]or before.getpixel((x,y))==after.getpixel((x,y))for y in range(16)for x in range(16)),('Nonwater cave glyph changed',k)
   self.replace_art(row,art,'This shared Gen2 body/bank now uses one original Crystal CAVE20 water glyph, palette and program throughout each complete water body across oceans, ponds and caves. Only native animated water8px regions are substituted; every visible nonwater stone/wood/ice/tree pixel is independently checked unchanged. Original waterfall/lava programs and any explicitly directed current stay intact. All source hashes, water/Surf/Dive/encounter behavior and events remain unchanged.',dict(coherent_native_cave_water=water,whole_water_bodies=True,all_visible_nonwater_pixels_exact=True,source_pixel_scale=1))
   changes.append(dict(source=list(k),visible_water_pixels=sum(visible_water),changed_phase0_pixels=sum(a!=b for a,b in zip(before.get_flattened_data(),after.get_flattened_data())),nonwater_exact=True))
  self.proofs['coherent_cave_water']=changes;self.proofs['coherent_cave_water_held']=held

 def existing_aliases(self):
  for group in self.group_list:
   if group['review_index']in self.recipes or not group['existing']or not group['missing']or group['mid']in CITY_BUILDING_RESERVED.get(group['family'],set()):continue
   existing=[self.locations[(s['game'],'gen2',s['pair'],s['mid'],None)]for s in group['existing']]
   arts=[]
   for path,index,row in existing:
    row=self.rows.get(identity(row),row)
    art=artwork(row);art['role']=row['role']
    for field in('overMask','animationCategory'):
     if field in row:art[field]=copy.deepcopy(row[field])
    arts.append((catalog.sha(self.render(row).tobytes()),row.get('overMask'),art,path,index))
   if len({(a[0],a[1])for a in arts})!=1:continue
   _,_,art,path,index=arts[0]
   self.emit(group,art,'Exact checked native geometry/behavior alias of an already complete Crystal-theme source family; the existing whole counterpart and foreground mask are copied unchanged.',dict(existing_module=path,existing_index=index,full_source_geometry_equal=True))

 def exact_visual_aliases(self):
  known=defaultdict(list)
  def signature(game,pair,mid):
   c=self.imp.cell_index(game)[pair,mid]
   # Exact native RGB AND all priority planes are required here. A shared
   # flat color, source ID, collision or palette alone never establishes this.
   return(game,'primary'if mid<512 else pair,c['pixel_sha256'],c.get('behavior'),digest(c['layer_sha256']))
  effective={identity(r):r for r in self.prior};effective.update(self.rows)
  for row in effective.values():
   if row['game']not in GAMES or row['style']!='gen2'or row.get('map')is not None or not scope(row['tileset'],row['id']):continue
   known[signature(row['game'],row['tileset'],row['id'])].append(row)
  for group in self.group_list:
   if not group['missing']or group['review_index']in self.recipes or group['mid']in CITY_BUILDING_RESERVED.get(group['family'],set()):continue
   options=[]
   for item in group['source']:options+=known.get(signature(item['game'],item['pair'],item['mid']),[])
   if not options:continue
   signatures={(catalog.sha(self.render(row).tobytes()),row.get('overMask'))for row in options}
   if len(signatures)!=1:continue
   row=options[0];art=artwork(row);art['role']=row['role']
   for field in('overMask','animationCategory'):
    if field in row:art[field]=copy.deepcopy(row[field])
   self.emit(group,art,'Exact native complete-pixel/under/mid/over/behavior duplicate of a separately reviewed source counterpart in the same primary material bank or the same secondary pair. Source-role evidence is the complete identical native picture and priority geometry, not a reused number, average palette or collision guess.',
    dict(exact_native_source=[row['game'],row['tileset'],row['id']],exact_native_rgba_and_all_planes=True))

 def exact_shared_nature_aliases(self):
  # Shared natural banks reuse complete native tiles at different numbers.
  # Explicit role and source-picture guards permit only already reviewed
  # natural objects/surfaces, with byte-identical original RGBA, all planes
  # AND behavior. Underwater and flat-color ambiguities never enter here.
  prefixes=('reverse_gen2_hoenn_native_cliff_','reverse_gen2_hoenn_water_',
   'reverse_hoenn_cave_','reverse_hoenn_johto_cave_',
   'reverse_gen2_hoenn_complete_native_cave_water_bank_',
   'reverse_gen2_hoenn_complete_classic_encounter_grass',
   'reverse_gen2_hoenn_complete_native_forest_tree_',
   'classic_complete_native_tree32_',
   'reverse_gen2_hoenn_native_sand_field_edge','reverse_gen2_hoenn_flat_sand',
   'reverse_gen2_hoenn_ordinary_cave_floor','reverse_gen2_hoenn_raised_rock_top',
   'reverse_gen2_hoenn_whole_fixed_boulder','reverse_gen2_hoenn_native_ice_floor',
   'reverse_gen2_hoenn_cave_join_','reverse_gen2_hoenn_complete_native_small_decorative_tree')
  effective={identity(r):r for r in self.prior};effective.update(self.rows);known=defaultdict(list)
  def signature(game,pair,mid):
   c=self.imp.cell_index(game)[pair,mid];return(c['pixel_sha256'],c.get('behavior'),digest(c['layer_sha256']))
  for row in effective.values():
   if row['game']not in GAMES or row.get('style')!='gen2'or row.get('map')is not None or not scope(row['tileset'],row['id'])or row['tileset']=='general__underwater'or not row['role'].startswith(prefixes):continue
   known[signature(row['game'],row['tileset'],row['id'])].append(row)
  for group in self.group_list:
   i=group['review_index']
   if i in self.recipes or not group['missing']or group['family']=='general__underwater'or group['mid']in CITY_BUILDING_RESERVED.get(group['family'],set()):continue
   choices=[]
   for s in group['source']:choices+=known.get(signature(s['game'],s['pair'],s['mid']),[])
   if not choices or len({(catalog.sha(self.render(r).tobytes()),r.get('overMask'))for r in choices})!=1:continue
   s=group['source'][0];native=preview.native_donor(self.cache,dict(game=s['game'],tileset=s['pair'],id=s['mid'],hash=s['hash']),self.packed)
   if len(set(native.get_flattened_data()))<3:continue
   # Every alias must independently carry the same exact original picture,
   # behavior and all priority planes, including different cartridge banks.
   witness=choices[0];sig=signature(witness['game'],witness['tileset'],witness['id'])
   if not all(signature(s['game'],s['pair'],s['mid'])==sig for s in group['source']):continue
   art=artwork(witness);art['role']=witness['role']
   for field in('overMask','animationCategory'):
    if field in witness:art[field]=copy.deepcopy(witness[field])
   self.emit(group,art,'Explicitly reviewed shared natural tile: its entire original source RGBA canvas, complete under/mid/over priority planes and actual behavior are byte-identical to the named previously reviewed nature counterpart, even though the secondary pair or MID number differs. The exact same complete native Crystal object/surface/foreground is therefore retained unchanged at1:1. Underwater, voids, flat-color ambiguities and unrelated furniture/building/unique-role families are explicitly excluded; there is no approximate geometry, color or material inference.',dict(exact_shared_native_source=[witness['game'],witness['tileset'],witness['id']],source_rgba_sha256=sig[0],source_behavior=sig[1],all_priority_planes_sha256=sig[2],native_output_sha256=catalog.sha(self.render(witness).tobytes()),native_role=witness['role']))

 def classic_cliff(self,shape,background='field'):
  key=('classic_cliff',shape,background)
  if key in self._gb:return copy.deepcopy(self._gb[key])
  ground=ground_ref(self,'gen2');whole=Image.new('RGBA',(32,32));refs=[]
  for q in range(4):
   ref=self.gb_ref('crystal','VIOLET_CITY',10,q);refs.append(ref);whole.paste(self.gb_image(ref),(q%2*16,q//2*16))
  bg=set(self.gb_image(ground).get_flattened_data())|set(self.gb_image(self.raw_ref('TILESET_JOHTO',(0,0,0,0),'VIOLET_CITY')).get_flattened_data())
  outside=exterior(whole,bg)
  glyphs={43:(0,0),44:(8,0),45:(24,0),59:(0,8),60:(8,8),61:(24,8),75:(0,24),76:(8,24),77:(24,24)}
  shapes={'nw':[43,44,59,60],'n':[44,44,60,60],'ne':[44,45,60,61],
   'w':[59,60,59,60],'top':[60]*4,'e':[60,61,60,61],
   'sw':[59,60,75,76],'front':[76]*4,'se':[60,61,76,77]}
  base=ground if background=='field'else self.raw_ref('TILESET_JOHTO',(60,)*4,'VIOLET_CITY')if background=='top'else self.raw_ref('TILESET_JOHTO',(76,)*4,'VIOLET_CITY')if background=='front'else self.raw_ref('TILESET_KANTO',(48,57,57,48),'PALLET_TOWN')
  parts=[];kept=0
  for i,tile in enumerate(shapes[shape]):
   sx,sy=glyphs[tile];ref=refs[sy//16*2+sx//16];mask=[(x+sx,y+sy)not in outside or tile in(44,60,76)for y in range(8)for x in range(8)]
   # Emit complete eight-pixel glyphs or their checked outside-background
   # mask. No perspective edge is borrowed from a differently oriented tile.
   for y in range(8):
    x=0
    while x<8:
     if not mask[y*8+x]:x+=1;continue
     stop=x+1
     while stop<8 and mask[y*8+stop]:stop+=1
     old=next((p for p in parts if p['donor']==ref and p['srcX']==sx%16+x and p['w']==stop-x and p['srcY']+p['h']==sy%16+y and p['x']==i%2*8+x and p['y']+p['h']==i//2*8+y),None)
     if old:old['h']+=1
     else:parts.append(dict(donor=ref,srcX=sx%16+x,srcY=sy%16+y,w=stop-x,h=1,x=i%2*8+x,y=i//2*8+y))
     kept+=stop-x;x=stop
  assert parts and len(parts)<=32,(shape,background,len(parts))
  art=self.composite(base,parts,'reverse_gen2_hoenn_native_cliff_'+shape+'_'+background);art['overMask']='0'*256
  self._gb[key]=copy.deepcopy(art)
  self.proofs.setdefault('native_cliff_modules',{})[shape+'/'+background]=dict(native_outcrop=['crystal','VIOLET_CITY',10],whole_8px_modules=shapes[shape],retained_native_pixels=kept,whole_object_exterior_mask=True,background=background)
  return art

 def core_nature(self):
  ground=ground_ref(self,'gen2');refs={}
  from gen2_kanto_shores_finish import JOHTO_BANKS
  water_raw={shape:raw for raw,shape in JOHTO_BANKS.items()}
  water_raw['interior']=(20,20,20,20)
  for shape,raw in water_raw.items():refs['water_'+shape]=self.raw_ref('TILESET_JOHTO',raw,'NEW_BARK_TOWN')
  grass=self.raw_ref('TILESET_JOHTO',(4,4,4,4),'NEW_BARK_TOWN')
  refs['grass']=grass;refs['sand']=self.raw_ref('TILESET_KANTO',(48,57,57,48),'PALLET_TOWN')
  # Every entry below names reviewed source-contact indices, rather than
  # assuming the same MID has the same meaning in R/S and Emerald.
  choices={
   'cliff_104':[146,147],'cliff_105':[148,149],'cliff_106':[150,151],
   'cliff_112':[159,160],'cliff_113':[161],'cliff_114':[162],
   'cliff_120':[168,169],'cliff_121':[170,171],'cliff_122':[172,173],
   'cliff_123':[174],'cliff_125':[176],
   'cliff_107':[152],'cliff_108':[153],'cliff_109':[154],
   'cliff_115':[163],'cliff_116':[164],'cliff_117':[165],'cliff_118':[166],'cliff_119':[167],'cliff_124':[175],
   'cliff_128':[177,178],'cliff_129':[179],'cliff_130':[180,181],
   'cliff_131':[182,183],'cliff_132':[184,185],
   'cliff_136':[192,193],'cliff_137':[194],'cliff_138':[195],
   'cliff_139':[196,197],'cliff_140':[198,199],'cliff_144':[205,206],'cliff_145':[207,208],
   'water_interior':[80,123,221,249,449,475,608,609,616,617,618,619],
   'water_west':[71,235,241], 'water_east':[87,243,477],
   'water_northwest':[235,452,469], 'water_north':[236,470], 'water_northeast':[237,471],
   'water_inward_northwest':[248,484], 'water_inward_northeast':[250,485],
  }
  # Resolve only the unambiguous bank instances in this first pass. The
  # complete reviewed contact, not a numeric source ID, controls orientation.
  choices['water_west']=[71,241]
  choices['water_northwest']=[235,469]
  choices['water_north']=[236,470]
  choices['water_northeast']=[237,471]
  choices['water_east']=[87,243,477]
  for name,indices in choices.items():
   for i in indices:
    group=self.group_list[i]
    if i in self.recipes or not group['missing']:continue
    if name.startswith('cliff_'):
     selection={104:('nw','field'),105:('n','field'),106:('ne','field'),112:('w','field'),113:('top','field'),114:('e','field'),
      120:('sw','field'),121:('front','field'),122:('se','field'),123:('se','front'),125:('sw','front'),
      107:('nw','top'),108:('n','top'),109:('ne','top'),115:('w','top'),116:('top','top'),117:('e','top'),118:('top','top'),119:('top','top'),124:('front','front'),
      128:('nw','sand'),129:('n','sand'),130:('ne','sand'),131:('nw','field'),132:('ne','field'),136:('w','sand'),137:('front','front'),138:('e','sand'),139:('sw','field'),140:('se','field'),144:('sw','sand'),145:('front','front')}
     shape,base=selection[int(name[6:])];art=self.classic_cliff(shape,base);ref=dict(native_outcrop=['VIOLET_CITY',10],shape=shape,background=base)
    else:ref=refs[name];art=self.native(ref,'reverse_gen2_hoenn_'+name)
    art['overMask']='0'*256
    if name.startswith('water_'):
     spec=specification(self.cache,ref,'program');assert spec
     art.update(animated=True,animation=spec,animationCategory='water')
    self.emit(group,art,'Complete native Crystal '+name.replace('_',' ')+' counterpart. The original handed cliff/bank shape remains distinct from straight pieces and from land/water interior.',dict(native_counterpart=ref))
  # Ordinary and long encounter grass both have the complete classic16px
  # grass counterpart; leaf foreground is restricted to the lower native band.
  for i in(20,33,34,61,62,532,533,534,535):
   group=self.group_list[i]
   if i in self.recipes or not group['missing']:continue
   im=self.gb_image(grass);bg=set(self.gb_image(ground).get_flattened_data())
   art=self.native(grass,'reverse_gen2_hoenn_complete_classic_encounter_grass')
   art['overMask']=''.join('1'if y>=8 and im.getpixel((x,y))not in bg else'0'for y in range(16)for x in range(16))
   self.emit(group,art,'Visually checked complete native Crystal encounter grass. The full16px field glyph remains unscaled, with its lower nonbackground leaf pixels above actor feet; original long/normal-grass encounters and movement remain unchanged.',dict(native_counterpart=grass,foreground='native lower leaf band'))
  # Full native16x32 Crystal conifer. Hoenn shares its middle foliage in
  # isolated three-row columns and dense forests, so only that intact16px
  # leaf module repeats. The complete crown, lower foliage and trunk survive.
  whole=Image.new('RGBA',(16,32))
  for y in range(2):whole.paste(self.gb_image(self.gb_at('crystal','NEW_BARK_TOWN',0,y)),(0,y*16))
  outside=exterior(whole,set(self.gb_image(ground).get_flattened_data()))
  def tree_piece(sy,base,priority):
   full=self.gb_rect('crystal','NEW_BARK_TOWN',0,sy,16,16);parts=[];mask=[]
   for y in range(16):
    for x in range(16):mask.append((x,sy+y)not in outside)
   for p in full:
    included=[mask[n]and p.get('x',0)<=n%16<p.get('x',0)+p['w']and p.get('y',0)<=n//16<p.get('y',0)+p['h']for n in range(256)]
    for span in runs(included):
     v=copy.deepcopy(p);v.update(srcX=p.get('srcX',0)+span['x']-p.get('x',0),srcY=p.get('srcY',0)+span['y']-p.get('y',0),**span);parts.append(v)
   assert parts and len(parts)<=32
   art=self.composite(base,parts,'reverse_gen2_hoenn_complete_native_conifer_'+str(sy))
   art['overMask']=''.join('1'if bit and priority else'0'for bit in mask)
   return art
  tree_sets={0:[21,22,23,24,262,263],8:[253,254,255,256],16:[35,36,37,38]}
  for sy,indices in tree_sets.items():
   for i in indices:
    group=self.group_list[i]
    if i in self.recipes or not group['missing']:continue
    self.emit(group,tree_piece(sy,ground,sy==0 and i in(21,22,23,24)),
     'Complete native Crystal narrow conifer column: original16px crown and lower16px foliage/trunk remain intact; the central four complete8px leaf glyphs repeat at1:1 only where Hoenn shares a taller/dense canopy. No canopy tip, trunk, branch or unique feature is cropped, shrunk or regenerated.',dict(native_tree_rect=[0,0,16,32],selected_leaf_module_y=sy,source_context_proof='primary-tree-contexts.json'))
  whole.save(self.out/'crystal-native-conifer-whole16x32.png')
  native=Image.new('RGBA',(16,48))
  for y,sy in enumerate((0,8,16)):native.paste(self.render(tree_piece(sy,ground,y==0)),(0,y*16))
  native.save(self.out/'crystal-native-conifer-complete48px-assembly.png')
  self.proofs['core_native_refs']=refs

 def flowers(self):
  template=next((r for r in self.prior+self.templates if r['game']in GAMES and r['style']=='gen2'and r['role']=='reverse_hoenn_complete_native_flower'),None)
  if template:
   art=artwork(template);art['role']=template['role'];template_identity=list(identity(template))
  else:
   flower=self.gb_ref('crystal','NEW_BARK_TOWN',4,0);profile=specification(self.cache,flower,'program');assert profile
   art=self.composite(ground_ref(self,'gen2'),[dict(donor=flower,srcX=8,srcY=8,w=8,h=8,x=4,y=4,animated=True,gbForeground=True)],'reverse_hoenn_complete_native_flower')
   art.update(animated=True,animation=profile,animationCategory='flowers');template_identity=['crystal','NEW_BARK_TOWN',4,0]
  for i in(8,):
   group=self.group_list[i]
   if group['missing']and i not in self.recipes:self.emit(group,art,'Complete native animated Crystal ground flower with matching nonencounter grass; no hanging-planter or tall-tree fragment is substituted.',dict(existing_native_recipe=template_identity))
  # Ever Grande's walkable two-flower bouquets have field and stone-path
  # versions. Both original8px Crystal blossoms remain complete and animated;
  # only their neutral shade0 exterior is omitted above the selected floor.
  flower=self.gb_ref('crystal','NEW_BARK_TOWN',4,0);profile=specification(self.cache,flower,'program');assert profile
  for indices,base in((range(2423,2439),ground_ref(self,'gen2')),(range(2439,2453),self.raw_ref('TILESET_JOHTO',(6,6,6,6),'VIOLET_CITY'))):
   for i in indices:
    group=self.group_list[i]
    if i in self.recipes or not group['missing']:continue
    parts=[dict(donor=flower,srcX=8,srcY=8,w=8,h=8,x=x,y=y,animated=True,gbForeground=True)for x,y in((8,0),(0,8))]
    art=self.composite(base,parts,'reverse_gen2_hoenn_complete_two_native_ground_flowers');art.update(animated=True,animation=profile,animationCategory='flowers')
    self.emit(group,art,'The complete two-blossom walkable bouquet uses two intact native Crystal8px ground flowers, never a hanging flowerpot. Original native animation stays synchronized. Neutral source-shade transparency exposes the actual matching field/stone floor without removing any colored blossom pixels.',dict(whole_native_flower_glyphs=2,native_flower=flower,background=base))
  changed=[]
  effective={identity(r):r for r in self.prior};effective.update(self.rows)
  for k,row in list(effective.items()):
   if row['game']not in GAMES or row['style']!='gen2'or'flower'not in row['role']or not scope(row['tileset'],row['id']):continue
   mask=['0']*256;art=artwork(row);art['role']=row['role'];art_changed=False
   parts=art.get('parts')or([dict(donor=art['donor'],w=16,h=16)]if art.get('donor')else[])
   for p in parts:
    ref=p['donor']
    if ref['game']!='crystal':continue
    c=self.imp.cell_index('crystal')[ref['tileset'],ref['id'],ref['quadrant']]
    images=foreground_frames(self.cache,ref,row['animation'],self.packed)if p.get('animated')else[preview.gb_donor_layers(self.cache,ref,self.packed)['foreground']]
    selected_raw={c['tiles'][(p.get('srcY',0)+y)//8*2+(p.get('srcX',0)+x)//8]for y in range(p['h'])for x in range(p['w'])}
    if selected_raw=={3}and not p.get('gbForeground'):p['gbForeground']=True;art_changed=True
    for yy in range(p['h']):
     for xx in range(p['w']):
      sx,sy=p.get('srcX',0)+xx,p.get('srcY',0)+yy;x,y=p.get('x',0)+xx,p.get('y',0)+yy
      raw_index=sy//8*2+sx//8
      if y>=8 and c['tiles'][raw_index]==3:
       # Only pixels that belong to the blossom/stem in every native CGB
       # frame cover feet; animated empty background never masks an actor.
       if all(v.getpixel((sx,sy))[3]==255 for v in images):mask[y*16+x]='1'
   value=''.join(mask)
   if '1'not in value or(row.get('overMask')==value and not art_changed):continue
   before=catalog.sha(self.render(row).tobytes())
   if k in self.rows:
    new=self.rows[k];new.update(art);new['overMask']=value;new['reverseGen2OutdoorReview']['native_flower_stem_mask']=True;new['compositionPixelHash']=catalog.sha(self.render(new).tobytes())
   else:
    art['overMask']=value
    new=self.row(row['game'],row['tileset'],row['id'],'gen2',art,row['evidence']+' Complete native Crystal blossom pixels/animation remain exact, while neutral shade0 background exposes the correct underlying field. Only lower flower pixels that remain opaque in every animation frame cover actor feet. Original source terrain, collision and encounters remain unchanged.')
    path,index,old=self.locations[k];self.supersessions[k]=dict(module=path,old_index=index,old_row=old,full_row_sha256=digest(old),new_module=Path(getattr(self,'target_module',TARGET)).relative_to(ROOT).as_posix(),new_row=new)
    new['reverseGen2OutdoorReview']=dict(priority_only=True,native_flower_stem_mask=True,pixel_scale=1)
   changed.append(dict(source=list(k),foreground_pixels=value.count('1'),all_mask_pixels_opaque_in_every_native_frame=True,blossom_pixels_unchanged=True,background_only_rgb_change=art_changed,rgb_unchanged=catalog.sha(self.render(self.rows[k]).tobytes())==before))
  self.proofs['flower_stem_foregrounds']=changed

 def cave_basics(self):
  floor=self.gb_ref('crystal','UNION_CAVE_1F',2,0)
  plateau=self.gb_ref('crystal','UNION_CAVE_1F',4,3)
  boulder=self.gb_ref('crystal','UNION_CAVE_1F',24,0)
  down=self.gb_ref('crystal','UNION_CAVE_1F',11,3)
  ice=self.gb_ref('crystal','ICE_PATH_B1F',3,0)
  water=self.gb_ref('crystal','UNION_CAVE_1F',15,0)
  waterfall=self.gb_ref('crystal','TOHJO_FALLS',44,0)
  choices={
   'floor':(floor,[1456,1457]),
   'raised_rock_top':(plateau,[1502,1503,1506,1507,1508,1509,1560,1561,1603,1604,1615,1616,1623,1624,1642,1643,1652,1653]),
   'whole_fixed_boulder':(boulder,[1450,1451]),
   'whole_down_ladder':(down,[1455]),
   'native_ice_floor':(ice,[1660,1661]),
   'cave_water':(water,[1630,1641,1668]),
   'native_vertical_waterfall':(waterfall,[111,238,242]),
  }
  for name,(ref,indices)in choices.items():
   for i in indices:
    group=self.group_list[i]
    if i in self.recipes or not group['missing']:continue
    art=self.native(ref,'reverse_gen2_hoenn_'+name);art['overMask']='0'*256
    if name in('cave_water','native_vertical_waterfall'):
     spec=specification(self.cache,ref,'program');assert spec;art.update(animated=True,animation=spec,animationCategory='water')
    self.emit(group,art,'Visually reviewed complete native Crystal '+name.replace('_',' ')+'. Full native floor/ice cells or the entire16px object are retained, with the correct original ladder direction and native cave palette; source events, movement and elevation remain unchanged.',dict(native_counterpart=ref))
  # Three complete8px rounded native rock glyphs retain the source cluster
  # count, with the same native cave floor below all unused space.
  rockglyph=self.gb_ref('crystal','UNION_CAVE_1F',4,2)
  for i in(1452,1453):
   group=self.group_list[i]
   if i in self.recipes or not group['missing']:continue
   art=self.composite(floor,[dict(donor=rockglyph,srcX=0,srcY=0,w=8,h=8,x=x,y=y)for x,y in((0,0),(8,0),(4,8))],'reverse_gen2_hoenn_three_complete_native_rock_cluster');art['overMask']='0'*256
   self.emit(group,art,'A fixed cluster of three small stones uses three whole native Crystal8px rounded rock glyphs at their original pixel size over the checked cave floor. No rock is reduced, clipped or replaced by a ladder/wall.',dict(native_rock_glyph=rockglyph,whole_native_8px_glyphs=3))
  self.proofs['cave_native_refs']=dict(floor=floor,plateau=plateau,boulder=boulder,down_ladder=down,ice=ice,water=water,waterfall=waterfall)

 def cave_joined_edges(self):
  # These are reviewed in the full Granite1F native map, not inferred from
  # the integer MID: R/S and Emerald use different indexed wall variants.
  # The original two-cell column is a wall seam, not a freestanding boulder.
  choices={
   (4,0):[1500,1501],       # outward northwest turn, solid southeast
   (6,1):[1504,1505],       # outward northeast turn, solid southwest
   (4,0,'column_cap'):[1498,1499],
   (4,2,'column_face'):[1510,1511],
   (58,1):[1543,1544],      # thin right-facing ledge over ordinary floor
   (57,2):[1580,1581],      # low south-facing rim over ordinary floor
   (17,2):[1558,1559],      # the checked east/south inward join
   (2,0):[1545,1546,1585,1586,1587,1588,1589,1590],
   (11,3):[1551],          # complete down ladder, actual1F->B1F warp
   (7,3):[1484,1485,1486,1487,1547,1548,1549,1550], # native up ladder variants
  }
  for key,indices in choices.items():
   bid,q=key[:2];ref=self.gb_ref('crystal','UNION_CAVE_1F',bid,q)
   for i in indices:
    group=self.group_list[i]
    if i in self.recipes or not group['missing']:continue
    role='reverse_gen2_hoenn_cave_join_'+str(bid)+'_'+str(q)
    art=self.native(ref,role);art['overMask']='0'*256
    self.emit(group,art,'Joined native Granite Cave and Victory Road source-context review: this exact handed stone-rim/wall/column or plain entrance-floor family receives the matching complete original Crystal cave glyph at1:1. A high-contrast native Hoenn entrance-floor highlight is ordinary walkable floor, not a new wall or stair. The two column cells retain full native top/continuation glyphs; ladder575 retains the complete down ladder (Granite1F35,3 goes toB1F). Source ledge direction, floor collision, elevation, exit/ladder events and actors are unchanged.',dict(native_counterpart=ref,source_context='granite-corner-contexts.png',joined_geometry=True,ladder_warp_proof=['EM_GRANITE_CAVE_1F',35,3,'EM_GRANITE_CAVE_B1F']if i==1551 else []))
  # Tiny inward southeast nub: three complete native floor glyphs and the
  # original eight-pixel rock-side glyph, retaining the source handed join.
  floor=self.gb_ref('crystal','UNION_CAVE_1F',2,0)
  face=self.gb_ref('crystal','UNION_CAVE_1F',6,3)
  for i in(1566,1567):
   group=self.group_list[i]
   if i in self.recipes or not group['missing']:continue
   art=self.composite(floor,[dict(donor=face,srcX=8,srcY=8,w=8,h=8,x=8,y=8)],'reverse_gen2_hoenn_cave_southeast_inward_nub');art['overMask']='0'*256
   self.emit(group,art,'The joined low cave-wall turn has floor on its north/west sides and a small rock-face nub only in the southeast. Three whole native Crystal floor8px glyphs remain untouched; one complete original right rock-face8px glyph supplies the correctly handed lower-right join, with no scaling or unique object clipping.',dict(native_floor=floor,native_complete_8px_face=face,quadrant=3,source_context='granite-corner-contexts.png'))

 def joined_dry_cave_contracts(self):
  # Independently reviewed ORIGINAL Ancient Tomb, Seafloor and Origin
  # complete maps/grids, not nearest-color/index proposals. All source
  # identities still bind to the frozen7440-contact fingerprint above.
  prototypes={544:(4,0),546:(6,1),521:(4,1),598:(4,2),599:(6,3),
   596:(12,3),597:(14,3),537:(12,3),595:(4,0),514:(24,0),
   574:(7,3),575:(11,3),534:(7,3),527:(12,3),528:(4,2),530:(6,3),536:(12,2),538:(14,3)}
  counterparts={
   720:544,744:544,768:544,770:544,721:521,745:521,818:521,
   722:546,746:546,769:546,771:546,728:598,752:598,776:598,778:598,
   730:599,754:599,777:599,779:599,737:596,761:596,
   738:597,762:597,785:597,787:597,739:537,740:537,
   760:595,780:595,784:595,786:595,783:514,828:574,829:575,833:534,832:527,
   791:546,794:546,792:544,800:528,802:530,809:537,808:536,810:538,
   595:595,596:596,597:597,598:598,599:599,527:527}
  for group in self.group_list:
   i,mid=group['review_index'],group['mid']
   if group['family']!='general__cave'or i in self.recipes or not group['missing']or mid not in counterparts:continue
   prototype=counterparts[mid];bid,q=prototypes[prototype];ref=self.gb_ref('crystal','UNION_CAVE_1F',bid,q)
   art=self.native(ref,'reverse_gen2_hoenn_joined_dry_cave_'+str(prototype));art['overMask']='0'*256
   self.emit(group,art,'Independent joined-source cave review (Ancient Tomb, Seafloor Cavern and Cave of Origin): this exact complete cell is the named handed native cliff/column/floor/stair counterpart at1:1. Raised mass versus actual walk floor and the connected neighboring front/east/west faces establish direction, not palette or indexed ranking. In particular597/738/762/785/787 are convex southeast,808 is convex southwest,800 faces west and802 faces east.783 is a whole fixed boulder, not a corner. The original complete up/down stair metaphor remains at its real warp tile; upper527/832 contains only a removed Gen3 extension and receives matching original Crystal front wall, preventing duplicate stair holes. Source collision, ledge direction, ladder/warp/elevation and all events remain unchanged.',dict(native_counterpart=ref,reviewed_source_prototype=prototype,source_mid=mid,source_joined_proof='root-reviewed-contracts.json and origin-remaining-native-contexts.json',native_dimensions=[16,16],pixel_scale=1))
  # Complete48x32 source entrances have one opening in the lower middle,
  # surrounded by intact native wall cap/side modules. One original16px
  # Crystal cave opening is never duplicated or stretched to fill a bank.
  native_layout=[[(4,0),(4,1),(6,1)],[(4,2),(19,3),(6,3)]]
  source_layouts=[[[523,524,525],[531,532,533]],[[782,766,767],[790,774,775]],[[813,814,815],[821,822,823]]]
  modules={};model=Image.new('RGBA',(48,32))
  for y,row in enumerate(native_layout):
   for x,(bid,q)in enumerate(row):
    ref=self.gb_ref('crystal','UNION_CAVE_1F',bid,q);art=self.native(ref,'reverse_gen2_hoenn_complete_native_rock_portal_'+str(x)+'_'+str(y));art['overMask']='0'*256
    modules[x,y]=art;model.paste(self.render(art),(x*16,y*16))
  source_to_piece={mid:(x,y)for layout in source_layouts for y,row in enumerate(layout)for x,mid in enumerate(row)}
  for group in self.group_list:
   i,mid=group['review_index'],group['mid']
   if group['family']!='general__cave'or i in self.recipes or not group['missing']or mid not in source_to_piece:continue
   x,y=source_to_piece[mid]
   self.emit(group,modules[x,y],'The actual complete48x32 cave entrance is reviewed as one3x2 object, including both side pillars, full cap and its single lower-middle opening. Complete original Crystal wall/cap cells surround exactly one intact native16px cave doorway at the original source warp anchor. No frame half, dark opening, pillar or roof is scaled/cropped or duplicated. Source generic523..533, Seafloor782/766/767+790/774/775 and Origin813..815+821..823 retain the same joined arrangement. Original solid side/cap collision and entrance events remain unchanged.',dict(native_complete_portal=[['4q0','4q1','6q1'],['4q2','19q3','6q3']],source_complete_layouts=source_layouts,source_object_piece=[x,y],native_object_dimensions=[48,32],single_original_opening=True,pixel_scale=1))
  model.save(self.out/'complete-native-cave-portal48x32.png')
  self.proofs['joined_dry_cave_contracts']=dict(source_to_native_prototypes=counterparts,original_GB_portal_dimensions=[48,32],single_original_opening_sha256=catalog.sha(self.gb_image(self.gb_ref('crystal','UNION_CAVE_1F',19,3)).tobytes()),source_layouts=source_layouts,complete_native_cells_only=True)

 def ordinary_materials(self):
  field=ground_ref(self,'gen2');sand=self.raw_ref('TILESET_KANTO',(48,57,57,48),'PALLET_TOWN');floor=self.gb_ref('crystal','UNION_CAVE_1F',2,0);top=self.gb_ref('crystal','UNION_CAVE_1F',4,3)
  simple=[('flat sand',sand,[365,366]),('ordinary field',field,[47,48]),
   ('ordinary rock floor',floor,[1625,1674,1675,1695,1696,1723,1724,1725,1726,1727]),
   ('complete stone stairs',self.gb_ref('crystal','UNION_CAVE_1F',18,3),[1520,1521]),
   ('raised rock top',top,[1674,1675])]
  for name,ref,indices in simple:
   for i in indices:
    group=self.group_list[i]
    if i in self.recipes or not group['missing']:continue
    art=self.native(ref,'reverse_gen2_hoenn_'+name.replace(' ','_'));art['overMask']='0'*256
    self.emit(group,art,'Separately reviewed complete '+name+' material: the entire original Crystal counterpart remains16x16 at1:1. This is an ordinary non-object surface or complete native stair, with no facade, curved water bank, ladder, puzzle glyph or tree silently classified as floor. Source walkability/encounters/elevation/warp data remain unchanged.',dict(native_counterpart=ref,reviewed_material=name))
  # The actual primary full-sand292 establishes this material's palette
  # only within the explicitly inspected sand/grass floor-edge family.
  # Fill its original geometric footprint with native Crystal sand; the
  # original field outside each inward/outward turn stays native field.
  for i in(348,349,350,351,352,353,358,359,360,361,362,363,368,369,370,371,372,373):
   group=self.group_list[i]
   if i in self.recipes or not group['missing']:continue
   source=next((s for s in group['source']if s['game']=='emerald'),group['source'][0]);game,pair=source['game'],source['pair'];index=self.imp.cell_index(game)
   full=index[pair,292];sample=preview.native_donor(self.cache,dict(game=game,tileset=pair,id=292,hash=full['pixel_sha256']),self.packed)
   native=preview.native_donor(self.cache,dict(game=game,tileset=pair,id=source['mid'],hash=source['hash']),self.packed)
   mask=[p in set(sample.get_flattened_data())for p in native.get_flattened_data()];spans=runs(mask)
   assert 0<len(spans)<=32,(i,len(spans))
   art=self.composite(field,[dict(donor=sand,srcX=p['x'],srcY=p['y'],**p)for p in spans],'reverse_gen2_hoenn_native_sand_field_edge');art['overMask']='0'*256
   self.emit(group,art,'This independently inspected ordinary sand/field corner or full sand path uses the complete native Crystal sand repeat at1:1 inside the exact original sandy floor footprint. Native field fills only the checked exterior grass pixels; handed inward/outward floor corners stay in their original positions. No water, coast bank, rock/cliff face or building is in this surface-only family.',dict(native_sand=sand,source_full_sand=[game,pair,292],source_full_sand_sha256=full['pixel_sha256'],source_sand_geometry_sha256=digest(mask),sand_pixels=sum(mask)))
  # Complete single-cell stones, rebased from native cave floor onto the
  # correct ordinary field/sand. Only whole-object exterior floor is cut.
  rock=self.gb_ref('crystal','UNION_CAVE_1F',24,0);rock_image=self.gb_image(rock)
  # The boulder and floor share two palette shades. A color flood would
  # erase connected face highlights and keep stray floor flecks. Use the
  # independently inspected whole16px round contour instead; every black
  # outline and white highlight pixel must lie inside it.
  left=[6,4,3,2,1,1,1,0,0,0,0,0,0,1,1,2]
  right=[11,12,13,14,15,15,16,16,16,16,16,16,16,16,15,13]
  mask=[left[y]<=x<right[y]for y in range(16)for x in range(16)];neutral=self.neutral(rock)
  assert all(mask[y*16+x]or neutral.getpixel((x,y))[0]in(85,170)for y in range(16)for x in range(16))
  parts=[dict(donor=rock,srcX=p['x'],srcY=p['y'],**p)for p in runs(mask)];assert 0<len(parts)<=32
  for base,indices in((field,[281,282,283,284]),(sand,[285,286])):
   for i in indices:
    group=self.group_list[i]
    if i in self.recipes or not group['missing']:continue
    art=self.composite(base,parts,'reverse_gen2_hoenn_whole_native_fixed_outdoor_boulder');art['overMask']='0'*256
    self.emit(group,art,'The complete fixed native16px Hoenn stone receives the entire original Crystal16px cave boulder, including all cap/face/base pixels. An independently inspected whole-object contour replaces only donor cave floor with the matching native field or sand, preserving every boulder pixel at1:1. The source stone remains fixed; no Strength interaction, collision or event is added.',dict(native_whole_boulder=rock,native_size=[16,16],retained_object_pixels=sum(mask),whole_object_exterior_only=True))
  # The small wooden route sign is a semantic counterpart of the already
  # checked freestanding native sign, not a building/window lookalike.
  group3=self.group_list[5]
  source=next(s for s in group3['existing']);r=self.locations[(source['game'],'gen2',source['pair'],source['mid'],None)][2];art=artwork(r);art['role']='reverse_gen2_hoenn_complete_native_wooden_route_sign'
  if'overMask'in r:art['overMask']=r['overMask']
  for i in(45,46):
   group=self.group_list[i]
   if i not in self.recipes and group['missing']:self.emit(group,art,'The separately reviewed complete one-cell wooden route sign receives the same intact original Crystal freestanding sign used by the completed early Hoenn towns. Original text interaction and source collision remain unchanged.',dict(native_complete_sign=r.get('donor',r.get('base'))))

 def simple_native_shores(self):
  # Original Crystal Cianwood/Route40 beaches meet the native animated
  # water abruptly: they do not use a raised rocky bank or Hoenn foam.
  # Preserve each reviewed shore's handed land/water footprint on the
  # original GB8px grid, using whole native water glyphs and original sand.
  field=ground_ref(self,'gen2');sand=self.raw_ref('TILESET_KANTO',(48,57,57,48),'PALLET_TOWN')
  water=self.raw_ref('TILESET_JOHTO',(20,20,20,20),'CIANWOOD_CITY');spec=specification(self.cache,water,'program');assert spec
  families=[('shallow puddle',field,[257,258,259,265,266,267,276,277,278]),
   ('sandy coast',sand,[354,355,356,357,364,367,374,375,376,392,393,394,395,402,403])]
  records=[]
  for name,base,indices in families:
   for i in indices:
    group=self.group_list[i]
    if i in self.recipes or not group['missing']:continue
    grids=[];samples=[]
    for item in group['source']:
     native=preview.native_donor(self.cache,dict(game=item['game'],tileset=item['pair'],id=item['mid'],hash=item['hash']),self.packed)
     # This test is limited to these visually inspected blue water/puddle
     # and yellow-sand/green-field source contacts; it is not a generic
     # material classifier. Each cartridge must independently agree on the
     # exact snapped footprint before any counterpart is authored.
     raw=list(native.get_flattened_data());blue=[p[3]>0 and p[2]>p[0] and p[2]>p[1]for p in raw]
     grid=[sum(blue[(y+qy*8)*16+x+qx*8]for y in range(8)for x in range(8))>=32 for qy in range(2)for qx in range(2)]
     grids.append(grid);samples.append(dict(game=item['game'],pair=item['pair'],mid=item['mid'],source_hash=item['hash'],water_pixels=sum(blue),whole_8px_grid=grid))
    assert all(g==grids[0]for g in grids),(i,'Cartridge shore masks disagree')
    grid=grids[0];parts=[dict(donor=water,srcX=q%2*8,srcY=q//2*8,w=8,h=8,x=q%2*8,y=q//2*8,animated=True)for q,wet in enumerate(grid)if wet]
    if parts:
     art=self.composite(base,parts,'reverse_gen2_hoenn_native_'+name.replace(' ','_'));art.update(animated=True,animation=spec,animationCategory='water')
    else:art=self.native(base,'reverse_gen2_hoenn_native_'+name.replace(' ','_')+'_dry_tip')
    art['overMask']='0'*256
    proof=dict(native_water=water,native_land=base,native_water_grid=grid,whole_native_8px_glyphs=True,all_cartridge_footprints_equal=True,source_samples=samples,native_shore_context='Crystal CIANWOOD_CITY and ROUTE_40 original direct land/water transition')
    self.emit(group,art,'Independently reviewed '+name+' adaptation to the original Crystal beach/puddle style: complete native animated water8px glyphs meet native field/sand directly, matching the actual original Cianwood/Route40 coast convention. The source shoreline is snapped to the original GB8px grid, retaining its handed land/water extent without inventing a rocky cliff, dry floor over water or foam art. All cartridge source masks agree. Hoenn puddles stay walkable and retain original splash behavior; ocean/shore collisions, elevations, Surf/Dive events and all source map data are unchanged.',proof)
    records.append(dict(review_index=i,**proof))
  self.proofs['native_shore_adaptations']=records

 def cave_water_and_lava(self):
  # Complete original cave bank glyphs, with their handed water/rock
  # layout inspected in the native source contact and original GB maps.
  banks={(37,1):[1635,1636,1646,1647],(38,0):[1639,1640,1650,1651],
   (39,0):[1637,1638,1648,1649,1664,1665],(50,0):[1662,1663],(50,1):[1666,1667]}
  for(bid,q),indices in banks.items():
   ref=self.gb_ref('crystal','UNION_CAVE_1F',bid,q);spec=specification(self.cache,ref,'program');assert spec
   for i in indices:
    group=self.group_list[i]
    if i in self.recipes or not group['missing']:continue
    art=self.native(ref,'reverse_gen2_hoenn_complete_native_cave_water_bank_'+str(bid)+'_'+str(q));art.update(animated=True,animation=spec,animationCategory='water',overMask='0'*256)
    self.emit(group,art,'The independently reviewed cave-water shore retains the correct east/west/north bank or inward rock-nub orientation. The complete original Crystal Union Cave16px water-bank cell supplies intact native stone/face glyphs and synchronized original animated water; it is never replaced with flat water or the opposite-handed bank. Source Surf/water/collision/elevation/warps and all encounters/events are unchanged.',dict(native_bank=ref,source_contact=group['review_index']//64+1,native_dimensions=[16,16],pixel_scale=1))
  lava=self.gb_ref('crystal','BLACKTHORN_GYM_1F',43,1);spec=specification(self.cache,lava,'program');assert spec
  for i in(1964,):
   group=self.group_list[i]
   if i in self.recipes or not group['missing']:continue
   # The original Blackthorn cell has two native opposite-phase lava
   # glyphs in its left column; repeat only that full8px lava column.
   art=self.composite(None,[dict(donor=lava,srcX=0,srcY=0,w=8,h=16,x=x,y=0,animated=True)for x in(0,8)],'reverse_gen2_hoenn_complete_native_lava');art.update(animated=True,animation=spec,animationCategory='water',overMask='0'*256)
   self.emit(group,art,'The full molten-lava surface uses the original Crystal Blackthorn Gym animated lava56/91 glyphs, including their opposite native phase, at1:1. Only a complete ordinary8x16 lava column repeats across the16px surface; no donor pink floor is copied and no invented frames/recolor is used. Original Hoenn lava movement/collision, events and encounters remain unchanged.',dict(native_lava_source=lava,whole_8px_glyphs=[56,91],native_column_repeat=2,pixel_scale=1))

 def reviewed_broad_materials(self):
  water=self.raw_ref('TILESET_JOHTO',(20,20,20,20),'CIANWOOD_CITY');water_spec=specification(self.cache,water,'program');assert water_spec
  floor=self.gb_ref('crystal','UNION_CAVE_1F',2,0);sand=self.raw_ref('TILESET_KANTO',(48,57,57,48),'PALLET_TOWN')
  exact={('general__mossdeep',531):('ordinary full ocean',water),('general__sootopolis',633):('ordinary full freshwater',water),
   ('general__rustboro',522):('ordinary full freshwater',water),('general__meteor_falls',513):('ordinary cave floor',floor),
   ('general__navel_rock',529):('raised cave backing',self.gb_ref('crystal','UNION_CAVE_1F',4,3)),('general__cave',673):('ordinary cave sand',sand),
   ('general__cave',665):('ordinary cave sand',sand),('general__mauville',593):('ordinary desert sand',sand),
   ('general__lavaridge',625):('solid stone surface',None),('general__fallarbor',577):('solid stone surface',None)}
  for group in self.group_list:
   i=group['review_index'];selected=exact.get((group['family'],group['mid']))
   if i in self.recipes or not group['missing']or not selected:continue
   name,ref=selected
   art=self.classic_cliff('top')if ref is None else self.native(ref,'reverse_gen2_hoenn_'+name.replace(' ','_'));art['overMask']='0'*256
   if ref==water:art.update(animated=True,animation=water_spec,animationCategory='water')
   self.emit(group,art,'This independently inspected high-occurrence source is '+name+', not a cliff edge, window/facade, underwater glyph, directional current, rock bank or unique object. It receives the entire matching original Crystal16px material repeat at1:1. The source native picture and actual map context establish its complete surface meaning; every cartridge hash/behavior stays guarded. Source water/depth/encounter/collision/elevation/warps remain unchanged.',dict(native_counterpart=ref if ref is not None else dict(native_outcrop=['crystal','VIOLET_CITY',10],shape='top'),reviewed_source_material=name,native_pixel_scale=1))
  # Reviewed full ocean/pond pictures have many bit-identical source IDs.
  # A new behavior/priority alias is safe only when its complete native
  # RGB picture is exactly the same inspected all-water picture AND its
  # own actual behavior explicitly denotes ordinary water, not a current.
  hashes=set()
  for game in GAMES:
   for pair,mid in(('general__mossdeep',531),('general__sootopolis',633),('general__rustboro',522)):
    c=self.imp.cell_index(game).get((pair,mid))
    if c:hashes.add(c['pixel_sha256'])
  allowed={'MB_OCEAN_WATER','MB_POND_WATER','MB_OCEAN_WAVE'}
  for group in self.group_list:
   i=group['review_index']
   if i in self.recipes or not group['missing']or not all(s['hash']in hashes and s['behavior_hint']in allowed for s in group['source']):continue
   art=self.native(water,'reverse_gen2_hoenn_exact_full_native_water_picture');art.update(animated=True,animation=water_spec,animationCategory='water',overMask='0'*256)
   self.emit(group,art,'The complete actual native16x16 picture is byte-identical to the independently inspected Mossdeep ocean/Sootopolis pond water, and every actual cartridge source behavior independently names ordinary ocean/pond water. Thus the full original animated Crystal water counterpart is identical too. This exact whole-picture material alias does not classify arbitrary blue cells or erase a shore, diver boundary, current direction, submerged object or bank; those distinct pictures/behaviors are excluded. Source water mechanics and all map data remain unchanged.',dict(exact_full_native_rgba_water=True,explicit_water_behaviors=sorted(allowed),native_water=water,pixel_scale=1))
  # Raised solid rock interiors have no handed boundary or object to fit.
  for i in(246,247,451,459,476):
   group=self.group_list[i]
   if i in self.recipes or not group['missing']:continue
   self.emit(group,self.classic_cliff('top'),'Independently reviewed complete16px solid mountain-top repeat. The entire original Crystal raised stone surface is retained at1:1; no cliff turn, slope, water edge or unique object is in this solid interior cell. Source terrain/collision/elevation remain unchanged.',dict(native_stone_surface=['crystal','VIOLET_CITY',10],shape='top'))
  for i in(229,462):
   group=self.group_list[i]
   if i in self.recipes or not group['missing']:continue
   art=self.classic_cliff('front','front');art['overMask']='0'*256
   self.emit(group,art,'Explicitly inspected contacts04/08 identify this as a complete interior repeat of the brown frontal rock mass (primary169/382), without any outside sand, grass, water, stair, boulder or handed cap. The whole original Crystal south-facing rock-front8px repeat supplies that full16px plane at1:1. It is never replaced with field, an isolated corner or a curved shore. Original source solid-mass collision, elevation and all events remain unchanged.',dict(native_rock_front=['crystal','VIOLET_CITY',10],shape='front',background='front',source_mid=group['mid'],complete_interior_material=True,pixel_scale=1))

 def directional_currents(self):
  ref=self.gb_ref('crystal','UNION_CAVE_1F',15,0)
  directions={'MB_WESTWARD_CURRENT':'west','MB_EASTWARD_CURRENT':'east','MB_NORTHWARD_CURRENT':'north','MB_SOUTHWARD_CURRENT':'south'}
  records=[]
  for group in self.group_list:
   i=group['review_index']
   if i in self.recipes or not group['missing']:continue
   hints={s['behavior_hint']for s in group['source']}
   if len(hints)!=1 or next(iter(hints))not in directions:continue
   direction=directions[next(iter(hints))];samples=[];clear=True
   for s in group['source']:
    image=preview.native_donor(self.cache,dict(game=s['game'],tileset=s['pair'],id=s['mid'],hash=s['hash']),self.packed)
    # These actual current contacts contain only complete blue/white
    # wave glyphs. Any brown shore/rock, transparent cap or object makes
    # this a separate joined-shore review instead of a flat-water alias.
    raw=list(image.get_flattened_data())
    if any(p[3]!=255 or p[2]<p[0] or p[2]<p[1]for p in raw):clear=False;break
    samples.append(dict(game=s['game'],pair=s['pair'],mid=s['mid'],source_hash=s['hash'],source_behavior=s['behavior'],source_hint=s['behavior_hint']))
   if not clear:continue
   spec=specification(self.cache,ref,'program',flow_direction=direction);assert spec
   art=self.native(ref,'reverse_gen2_hoenn_native_'+direction+'_current');art.update(animated=True,animation=spec,animationCategory='water',overMask='0'*256)
   self.emit(group,art,'The actual source behavior explicitly identifies a '+direction+'ward current, and the separately reviewed original picture is complete blue/white flowing water without a shore, object or rock face. Whole original Crystal cave-water8px wave glyphs scroll in that same direction at the native program cadence; every original glyph pixel is retained and cached, with no painted arrows, random per-tile style or invented frames. Hoenn original current direction/push/Surf mechanics, collisions, elevations, encounters and all map events stay unchanged.',dict(native_current_water=ref,flow_direction=direction,whole_native_8px_glyphs=True,source_direction_samples=samples,pixel_scale=1))
   records.append(dict(review_index=i,flow_direction=direction,source_samples=samples))
  self.proofs['native_directional_currents']=records

 def reviewed_complete_water_variants(self):
  # Explicitly viewed contacts07..08 and79..81. These are complete blue
  # wave pictures, including deep/shallow palette variants, not submerged
  # rocks, currents, beach masks or underwater reef art. Every reviewed
  # index remains bound to the complete frozen cartridge source identity.
  indices={404,416,417,424,489,5037,*range(5040,5133)}
  ref=self.gb_ref('crystal','UNION_CAVE_1F',15,0);spec=specification(self.cache,ref,'program');assert spec
  for i in sorted(indices):
   group=self.group_list[i]
   if i in self.recipes or not group['missing']:continue
   assert group['family']in('primary','general__mossdeep'),('Unreviewed water-family index',i,group['family'])
   samples=[]
   for s in group['source']:
    image=preview.native_donor(self.cache,dict(game=s['game'],tileset=s['pair'],id=s['mid'],hash=s['hash']),self.packed)
    assert all(p[3]==255 and p[2]>=p[0]and p[2]>=p[1]for p in image.get_flattened_data()),('Reviewed complete water now has nonwater pixels',i,s)
    samples.append(dict(game=s['game'],pair=s['pair'],id=s['mid'],hash=s['hash'],behavior=s['behavior']if s['behavior']is not None else -1,hint=s['behavior_hint']or'unlabeled'))
   art=self.native(ref,'reverse_gen2_hoenn_reviewed_complete_water_variant');art.update(animated=True,animation=spec,animationCategory='water',overMask='0'*256)
   self.emit(group,art,'These explicitly inspected full native wave surfaces (primary327/334/335/342/414 and Mossdeep complete-water contacts79..81) contain water over the entire16px cell. Deep-dive, ocean and shallow-water source variants use the same coherent original Crystal CAVE20 wave glyph/palette/program as every adjoining Gen2-theme water body. The native source depth and shallow-walk/Dive/Surf behavior remain exact; visual adaptation never changes them. No rocky bank, reef, foam beach, direction-forced current, object or underwater floor is flattened here. Every original cartridge whole-RGBA identity and all indexed priority planes are bound to its inspected source contact, with an additional opaque-blue-canvas assertion.',dict(native_water=ref,whole_water_source_samples=samples,explicit_contact_review=True,native_pixel_scale=1))

 def whole_water_boulder(self):
  # Actual VictoryB2F(23,14):336/337 above344/345 is ONE rock with
  # surrounding water in its four-cell envelope. All four original source
  # cells block, including the original visible-water corner pixels.
  water=self.gb_ref('crystal','UNION_CAVE_1F',15,0);rock=self.gb_ref('crystal','UNION_CAVE_1F',24,0)
  spec=specification(self.cache,water,'program');assert spec
  left=[6,4,3,2,1,1,1,0,0,0,0,0,0,1,1,2];right=[11,12,13,14,15,15,16,16,16,16,16,16,16,16,15,13]
  mask=[left[y]<=x<right[y]for y in range(16)for x in range(16)];source=self.gb_image(rock);whole=Image.new('RGBA',(32,32));pieces={}
  for q in range(4):
   qx,qy=q%2*16,q//2*16
   rock_mask=[0<=x+qx-8<16 and 0<=y+qy-8<16 and mask[(y+qy-8)*16+x+qx-8]for y in range(16)for x in range(16)]
   parts=[dict(donor=water,srcX=0,srcY=0,w=16,h=16,x=0,y=0,animated=True)]
   parts += [dict(donor=rock,srcX=p['x']+qx-8,srcY=p['y']+qy-8,**p)for p in runs(rock_mask)]
   assert len(parts)<=32
   art=self.composite(None,parts,'reverse_gen2_hoenn_complete_native_water_boulder_'+str(q));art.update(animated=True,animation=spec,animationCategory='water',overMask='0'*256)
   pieces[q]=art;whole.paste(self.render(art),(qx,qy))
  assert all(not mask[y*16+x]or whole.getpixel((x+8,y+8))==source.getpixel((x,y))for y in range(16)for x in range(16))
  positions={336:0,337:1,344:2,345:3}
  for group in self.group_list:
   i,mid=group['review_index'],group['mid']
   if group['family']!='primary'or mid not in positions or i in self.recipes or not group['missing']:continue
   q=positions[mid]
   self.emit(group,pieces[q],'Independent actual VictoryRoadB2F23,14 source/collision review establishes336/337+344/345 as ONE complete2x2 rock-in-water, not four ordinary water cells. One entire original Crystal16px round boulder is centered at8,8 within that32px source envelope over the same original Crystal CAVE20 animated water as the surrounding body. The source silhouette contour removes only original cave floor, preserving every native rock/outline/shadow pixel at1:1; all four source pieces join the same full object with no repeated rock, cropped feature, dry floor patch or water seam. The original four blocked source cells, Surf boundaries and all events remain unchanged, including the source visible-water corners that already block.',dict(native_complete_boulder=rock,native_canonical_water=water,source_layout=[[336,337],[344,345]],source_piece=q,native_object_rect=[8,8,16,16],source_context=['emerald','EM_VICTORY_ROAD_B2F',23,14],complete_native_retained_pixels=sum(mask),every_retained_boulder_pixel_exact=True,pixel_scale=1))
  whole.save(self.out/'complete-native-water-boulder32-envelope.png')

 def native_city_curbs(self):
  field=ground_ref(self,'gen2');pave=self.raw_ref('TILESET_JOHTO',(6,6,6,6),'VIOLET_CITY')
  definitions={'n':(35,0,[0,1],None),'s':(35,2,[2,3],None),
   'w':(39,0,[0,2],None),'e':(39,1,[1,3],None),
   'nw':(73,0,[0,1,2],0),'ne':(72,1,[0,1,3],1),
   'sw':(68,2,[0,2,3],2),'se':(69,3,[1,2,3],3)}
  models={}
  for name,(bid,q,quads,cap)in definitions.items():
   ref=self.gb_ref('crystal','SAFFRON_CITY',bid,q);image=self.gb_image(ref);mask=[False]*256
   for quad in quads:
    sx,sy=quad%2*8,quad//2*8
    if quad==cap:
     piece=image.crop((sx,sy,sx+8,sy+8));bg={piece.getpixel((0,0)),piece.getpixel((7,0)),piece.getpixel((0,7)),piece.getpixel((7,7))}
     # Four rounded-post corners are original outside field. Its enclosed
     # pale cap/highlight remains intact; no neutral-shade chroma key.
     outside=exterior(piece,bg)
    else:outside=set()
    for y in range(8):
     for x in range(8):mask[(sy+y)*16+sx+x]=(x,y)not in outside
   parts=[dict(donor=ref,srcX=p['x'],srcY=p['y'],**p)for p in runs(mask)];assert parts and len(parts)<=32
   for base_name,base in(('field',field),('paving',pave)):
    art=self.composite(base,parts,'reverse_gen2_hoenn_native_city_curb_'+name+'_'+base_name);art['overMask']='0'*256;models[name,base_name]=art
   self.proofs.setdefault('native_city_curb_modules',{})[name]=dict(native_source=ref,whole_8px_bar_glyphs=True,rounded_post_exterior_only=True,native_object_pixels=sum(mask),object_mask_sha256=digest(mask))
  fields={61:'nw',62:'n',63:'ne',69:'w',71:'e',77:'sw',78:'s',79:'se',320:'w',321:'e',322:'e'}
  paved={85:'nw',86:'n',87:'ne',93:'w',95:'e',101:'sw',102:'s',103:'se'}
  for group in self.group_list:
   i,mid=group['review_index'],group['mid']
   if group['family']!='primary'or i in self.recipes or not group['missing']:continue
   if mid in fields:shape=fields[mid];art=models[shape,'field']
   elif mid in paved:shape=paved[mid];art=models[shape,'paving']
   elif mid==94:shape='plain paving';art=self.native(pave,'reverse_gen2_hoenn_complete_native_city_paving');art['overMask']='0'*256
   else:continue
   self.emit(group,art,'The separately inspected low white/gray Hoenn curb uses the complete original Crystal Saffron low curb in the same handed direction, with intact native gray bar8px glyphs and original rounded corner-post cap. This preserves a visible low barrier rather than inventing tall fence rails or rotating upright posts. Only true exterior field around the small round cap is transparent; enclosed cap/bar highlights remain. Remaining quadrants use matching native field/paving. Full native pixels, source curb collision, route openings and all map/event data remain unchanged.',dict(native_city_curb_family=['crystal','SAFFRON_CITY'],shape=shape,pixel_scale=1,source_low_curb_mid=mid))
  contact=Image.new('RGBA',(8*16,2*16))
  for row,base_name in enumerate(('field','paving')):
   for col,name in enumerate(definitions):contact.paste(self.render(models[name,base_name]),(col*16,row*16))
  contact.resize((768,192),Image.Resampling.NEAREST).save(self.out/'native-city-curb-complete-family.png')

 def dewford_trees_and_pier(self):
  field=ground_ref(self,'gen2');sand=self.raw_ref('TILESET_KANTO',(48,57,57,48),'PALLET_TOWN')
  whole=Image.new('RGBA',(16,32))
  for y in range(2):whole.paste(self.gb_image(self.gb_at('crystal','NEW_BARK_TOWN',0,y)),(0,y*16))
  outside=exterior(whole,set(self.gb_image(field).get_flattened_data()))
  trees={}
  for sy,base_name,base in((0,'sand',sand),(0,'field',field),(16,'sand',sand)):
   ref=self.gb_at('crystal','NEW_BARK_TOWN',0,sy//16);mask=[(x,sy+y)not in outside for y in range(16)for x in range(16)]
   parts=[dict(donor=ref,srcX=p['x'],srcY=p['y'],**p)for p in runs(mask)];assert 0<len(parts)<=32
   art=self.composite(base,parts,'reverse_gen2_hoenn_dewford_complete_native_tree_'+str(sy)+'_'+base_name);art['overMask']=''.join('1'if v and sy==0 else'0'for v in mask);trees[sy,base_name]=art
  boards=self.raw_ref('TILESET_KANTO',(75,75,75,75),'ROUTE_12')
  edge=self.raw_ref('TILESET_KANTO',(49,49,20,20),'ROUTE_12');spec=specification(self.cache,edge,'program');assert spec
  for group in self.group_list:
   i,mid=group['review_index'],group['mid']
   if group['family']!='general__dewford'or i in self.recipes or not group['missing']:continue
   if mid in(569,570,579):
    sy,base_name={569:(0,'sand'),570:(16,'sand'),579:(0,'field')}[mid]
    self.emit(group,trees[sy,base_name],'The decorative narrow tropical tree receives the intact original Crystal New Bark16x32 tree in the exact same two-cell source footprint. Both native crown and lower foliage/trunk remain complete at1:1, with no inserted leaf band or reduced tree. Actual sandy/field backgrounds are retained independently around the native silhouette; source tree blocking, absence of Cut/Headbutt interaction and all source actors/events stay unchanged.',dict(native_complete_tree=['crystal','NEW_BARK_TOWN',0,0,1,2],source_tree_cell=mid,native_section_y=sy,matching_ground=base_name,pixel_scale=1))
   elif mid in(552,553):
    art=self.native(boards,'reverse_gen2_hoenn_complete_native_fishing_pier_boards');art['overMask']='0'*256
    self.emit(group,art,'The complete native Crystal Route12 fishing-pier boards are the direct ordinary jetty-floor counterpart. The whole original16px board pattern remains intact at1:1, without importing indoor carpet, inventing stakes or scaling wood strips. Original source board walkability, fishing positions, events and shoreline collision remain unchanged.',dict(native_fishing_pier_floor=boards,original_native_feature_collision=114,pixel_scale=1))
   elif mid in(560,561):
    if mid==561:art=self.native(edge,'reverse_gen2_hoenn_complete_native_fishing_pier_edge')
    else:
     art=self.composite(sand,[dict(donor=edge,srcX=0,srcY=0,w=16,h=8,x=0,y=0),dict(donor=edge,srcX=8,srcY=8,w=8,h=8,x=8,y=8,animated=True)],'reverse_gen2_hoenn_native_fishing_pier_sandy_edge')
    art.update(animated=True,animation=spec,animationCategory='water',overMask='0'*256)
    self.emit(group,art,'The actual lower edge of Dewford jetty uses the complete original Crystal fishing-pier front8px board glyphs over the original animated water. The westmost source cell560 retains its sandy lower-left quarter, while lower-right water and full-water edge561 keep the native water animation. All pieces are original complete8px modules at1:1. Source original water/shore/board collision and fishing mechanics remain unchanged.',dict(native_fishing_pier_edge=edge,source_west_sand_quadrant=2 if mid==560 else -1,original_native_edge_collision=41,pixel_scale=1))
  sign=self.gb_at('crystal','PALLET_TOWN',3,5);im=self.gb_image(sign)
  native_floor=set(self.gb_image(self.gb_at('crystal','PALLET_TOWN',3,4)).get_flattened_data());outside=exterior(im,native_floor)
  mask=[(x,y)not in outside for y in range(16)for x in range(16)]
  sign_art=self.composite(sand,[dict(p,donor=sign,srcX=p['x'],srcY=p['y'])for p in runs(mask)],'reverse_gen2_hoenn_dewford_complete_native_gym_sign');sign_art['overMask']='0'*256
  for group in self.group_list:
   i,mid=group['review_index'],group['mid']
   if group['family']!='general__dewford'or mid not in(520,528)or i in self.recipes or not group['missing']:continue
   art=sign_art if mid==528 else self.native(sand,'reverse_gen2_hoenn_dewford_sign_unused_walkable_cap')
   art=copy.deepcopy(art);art['overMask']='0'*256
   self.emit(group,art,'Actual Dewford11,15/16 source review identifies one freestanding gym-description sign: upper520 is walkable sand carrying only the taller Gen3 decorative badge cap; lower528 is its blocked sign/interaction anchor. One complete original Crystal16px freestanding sign replaces that lower cell at1:1, retaining its entire frame and both feet. Only the unused walkable upper badge clears to matching native sand. The full GYM label remains on the nearby complete gym facade; text interaction, collision, actor positions and all events stay unchanged.',dict(native_complete_sign=sign,source_sign_upper=[11,15,520,0],source_sign_lower=[11,16,528,7],upper_source_walkable=True,native_pixel_scale=1))

 def reviewed_ocean_cliffs(self):
  # Dewford's peninsula is raised land EAST of the open water:378 is
  # its west-facing side,386 its lower-left/southwest outward cap.
  water=self.gb_ref('crystal','UNION_CAVE_1F',15,0);spec=specification(self.cache,water,'program');assert spec
  for group in self.group_list:
   i,mid=group['review_index'],group['mid']
   if group['family']!='primary'or mid not in(378,386)or i in self.recipes or not group['missing']:continue
   shape='w'if mid==378 else'sw';art=self.classic_cliff(shape);art.pop('base',None)
   art['parts']=[dict(donor=water,srcX=0,srcY=0,w=16,h=16,x=0,y=0,animated=True)]+art['parts'];assert len(art['parts'])<=32
   art.update(role='reverse_gen2_hoenn_native_cliff_'+shape+'_water',animated=True,animation=spec,animationCategory='water',overMask='0'*256)
   self.emit(group,art,'Actual whole Dewford peninsula context establishes raised stone east/north of ocean:378 is the west-facing rock wall and386 its convex southwest cap. Complete original Crystal handed outcrop8px modules remain1:1, with only true exterior field replaced by the coherent original animated CAVE20 ocean. No side/corner is flattened, reversed or replaced by plain water. Source solid cliff collision, height, Surf boundaries and all events remain unchanged.',dict(native_outcrop=['crystal','VIOLET_CITY',10],shape=shape,native_water=water,source_context=['emerald','EM_DEWFORD_TOWN'],source_mid=mid,pixel_scale=1))

 def meteor_native_basics(self):
  refs={514:(18,3),515:(7,3),524:(7,3),525:(11,3),519:(2,0),548:(2,0),611:(12,3)}
  for group in self.group_list:
   i,mid=group['review_index'],group['mid']
   if group['family']!='general__meteor_falls'or i in self.recipes or not group['missing']or mid not in refs:continue
   bid,q=refs[mid];ref=self.gb_ref('crystal','UNION_CAVE_1F',bid,q);art=self.native(ref,'reverse_gen2_hoenn_meteor_native_'+str(mid));art['overMask']='0'*256
   self.emit(group,art,'Actual joined Meteor Falls maps and warp definitions reviewed:514 is a complete stone stair;515 is a complete ordinary unwarped rising ramp,524 the up-stair warp (B1F->1F),525 the down-stair warp (1F->B1F),519/548 ordinary entrance floor,611 only the upper Gen3 wall extension above the up stair. Each uses the whole original Crystal cave counterpart at1:1. A single complete original up icon remains at the actual warp;611 returns to the matching native wall instead of duplicating another stair hole. No source warp, elevation movement, collision or event is invented/changed.',dict(native_counterpart=ref,source_mid=mid,native_pixel_scale=1,source_ladder_proof='meteor-ladder-source-context.png',actual_unwarped_ramp_contexts=[[7,10],[3,22]]if mid==515 else []))
  native=[[(4,0),(4,1),(6,1)],[(4,2),(19,3),(6,3)]];source=[[581,582,583],[589,590,591]]
  positions={mid:(x,y)for y,row in enumerate(source)for x,mid in enumerate(row)}
  for group in self.group_list:
   i,mid=group['review_index'],group['mid']
   if group['family']!='general__meteor_falls'or i in self.recipes or not group['missing']or mid not in positions:continue
   x,y=positions[mid];bid,q=native[y][x];ref=self.gb_ref('crystal','UNION_CAVE_1F',bid,q);art=self.native(ref,'reverse_gen2_hoenn_meteor_complete_native_portal_'+str(x)+'_'+str(y));art['overMask']='0'*256
   self.emit(group,art,'The actual Meteor Falls48x32 portal is one complete3x2 object:581/582/583 above589/590/591, independently reviewed at1F1R(9,2)/(25,27) andB1F1R(16,2). Whole original Crystal cave-cap and side-pillar cells surround one intact original16px opening in the lower-middle source warp tile. No frame is shrunk/cut and no opening is duplicated. All source entrance events, side/cap collision and actor positions remain unchanged.',dict(native_complete_layout=[['4q0','4q1','6q1'],['4q2','19q3','6q3']],source_complete_layout=source,source_piece=[x,y],source_context='portal-contexts.json',native_dimensions=[48,32],single_opening=True,pixel_scale=1))

 def meteor_joined_walls(self):
  # Actual marked ORIGINAL map contexts establish each handed wall, not
  # the source MID's numerical resemblance to another bank. The source
  # inventory fingerprint above freezes every cartridge-specific alias.
  refs={520:(4,0),544:(4,0),521:(4,1),545:(4,1),522:(6,1),546:(6,1),
   528:(4,2),552:(4,2),530:(6,3),554:(6,3),536:(12,2),560:(12,2),
   538:(14,3),562:(14,3),537:(12,3),561:(12,3),580:(12,3),532:(17,2),
   531:(16,3),533:(17,2),558:(12,3),559:(12,3)}
  for group in self.group_list:
   i,mid=group['review_index'],group['mid']
   if group['family']!='general__meteor_falls'or i in self.recipes or not group['missing']or mid not in refs:continue
   bid,q=refs[mid];ref=self.gb_ref('crystal','UNION_CAVE_1F',bid,q)
   art=self.native(ref,'reverse_gen2_hoenn_meteor_joined_wall_'+str(mid));art['overMask']='0'*256
   self.emit(group,art,'The complete original Meteor Falls source maps were independently reviewed with marked neighboring cell grids:520/544 northwest raised-rim caps,521/545 north rim,522/546 northeast caps,528/552 west-facing wall,530/554 east-facing wall,536/560 convex southwest,538/562 convex southeast,537/561/580 horizontal front mass, and532/533 the exact front-left to west-face-below inward join.531 retains walk floor northwest with the front stone to its right and east-facing continuation below, exactly matching original Crystal16q3;532/533 match17q2.558/559 are lower frontal fringe directly above walk floor beside the golden pillars, not side walls, and use the same full native front as580. The corresponding complete original Crystal cave cells remain at1:1, with handedness established from adjoining actual walk floor and raised mass and independently checked original BurnedTower/DiglettsCave joins. No corner is rotated, reversed or flattened. Source collision, height, stair events, water boundaries and all native movement remain unchanged.',dict(native_counterpart=ref,source_mid=mid,source_joined_proof='wall-contexts.json and native-16-17-actual-contexts.png',complete_native_cells_only=True,pixel_scale=1))

 def navel_joined_native_cave(self):
  # Actual full DOWN02 and FORK grids distinguish outside529 from room513.
  # In particular an upper room corner is the convex lower corner of the
  # surrounding stone mass, not a top corner guessed from its screen name.
  refs={513:(2,0),515:(24,0),516:(18,3),519:(2,0),527:(12,3),
   528:(4,2),530:(6,3),535:(7,3),537:(12,3),539:(14,3),540:(12,2),
   575:(11,3),583:(4,1),720:(4,0),722:(6,1)}
  for group in self.group_list:
   i,mid=group['review_index'],group['mid']
   if group['family']!='general__navel_rock'or i in self.recipes or not group['missing']or mid not in refs:continue
   bid,q=refs[mid];ref=self.gb_ref('crystal','UNION_CAVE_1F',bid,q)
   art=self.native(ref,'reverse_gen2_hoenn_navel_joined_native_'+str(mid));art['overMask']='0'*256
   self.emit(group,art,'Actual original NavelRock DOWN02/FORK/ENTRANCE complete-map grids establish the connected room and surrounding raised stone:513 is room walkfloor, while separately handled529 is solid backing;528 faces west and530 east;537 is the south-facing front mass;539/540 are the surrounding mass convex southeast/southwest caps around the upper room corners;583 is its north-facing lower room rim;720/722 are corresponding northwest/northeast solid-mass caps. Complete original Crystal cave glyphs supply these exact handed joins at1:1.515 retains one whole fixed rock,516 the complete native stone stairs,535 one original up-stair icon and575 one complete down-stair opening.527 only clears the taller Gen3 upper extension to matching native front wall, leaving the full original icon at its actual warp. Source529 outside versus513 inside is established from actual collision/elevation and connected geometry, never pale source color alone. All source ladders, warp directions, actor locations, collision and events remain unchanged.',dict(native_counterpart=ref,source_mid=mid,source_context=['EM_NAVEL_ROCK_DOWN02','EM_NAVEL_ROCK_FORK','EM_NAVEL_ROCK_ENTRANCE'],joined_room_geometry=True,complete_native_glyphs_only=True,pixel_scale=1))

 def petalburg_native_hedges_and_planters(self):
  ground=ground_ref(self,'gen2');leaf=self.gb_at('crystal','NATIONAL_PARK',6,48)
  mids={572,573,574,575,580,581,582,588,596,612,613,614}
  for group in self.group_list:
   i,mid=group['review_index'],group['mid']
   if group['family']!='general__petalburg'or mid not in mids or i in self.recipes or not group['missing']:continue
   grids=[];samples=[]
   for s in group['source']:
    c=self.imp.cell_index(s['game'])[s['pair'],1]
    field=preview.native_donor(self.cache,dict(game=s['game'],tileset=s['pair'],id=1,hash=c['pixel_sha256']),self.packed)
    source=preview.native_donor(self.cache,dict(game=s['game'],tileset=s['pair'],id=s['mid'],hash=s['hash']),self.packed)
    bg=set(field.get_flattened_data());mask=[p not in bg for p in source.get_flattened_data()]
    grid=[sum(mask[(qy*8+y)*16+qx*8+x]for y in range(8)for x in range(8))>=32 for qy in range(2)for qx in range(2)]
    grids.append(grid);samples.append(dict(game=s['game'],pair=s['pair'],mid=s['mid'],source_hash=s['hash'],whole_native_8px_grid=grid))
   assert grids and all(g==grids[0]for g in grids),('Petalburg hedge cartridge footprint disagreement',i,grids)
   parts=[dict(donor=leaf,srcX=8,srcY=8,w=8,h=8,x=q%2*8,y=q//2*8)for q,v in enumerate(grids[0])if v]
   assert parts
   art=self.composite(ground,parts,'reverse_gen2_hoenn_native_low_hedge_'+str(mid));art['overMask']='0'*256
   self.emit(group,art,'Joined original Petalburg town review identifies this family as the low planted hedge around homes and gym, distinct from metal fencing, facades, grass floor and tall trees. The deliberate Gen2-style counterpart uses only the complete original8x8 central leafy module of Crystal NationalPark, repeated at1:1 inside the same handed hedge footprint on the native GB8px grid. All actual cartridge footprint masks independently agree; selected nonencounter field remains outside each cap/corner. No whole crown, trunk, frame or unique object is clipped or shrunk. Source original hedge collision, route openings, buildings, warps and actors remain unchanged.',dict(native_complete_leaf_module=leaf,native_leaf_rect=[8,8,8,8],source_joined_map='EM_PETALBURG_CITY',source_samples=samples,native_hedge_grid=grids[0],known_feature_style_adaptation=True,pixel_scale=1))
  # The actual four Petalburg garden cells(23/24,22/23) are source7,
  # collision7/elevation0: solid framed planters, not ground flowers.
  group=self.group_list[11]
  if group['review_index']not in self.recipes and group['missing']:
   assert group['family']=='primary'and group['mid']==7
   pot=self.gb_at('crystal','AZALEA_GYM',0,1);image=self.gb_image(pot)
   outside=exterior(image,{(247,230,214,255),(255,156,197,255)})
   mask=[(x,y)not in outside for y in range(16)for x in range(16)]
   assert all(mask[y*16+x]or image.getpixel((x,y))in{(247,230,214,255),(255,156,197,255)}for y in range(16)for x in range(16))
   parts=[dict(p,donor=pot,srcX=p['x'],srcY=p['y'])for p in runs(mask)];assert len(parts)<=32
   art=self.composite(ground,parts,'reverse_gen2_hoenn_complete_native_raised_flower_planter');art['overMask']='0'*256
   result=self.render(art);assert all(not mask[y*16+x]or result.getpixel((x,y))==image.getpixel((x,y))for y in range(16)for x in range(16))
   self.emit(group,art,'Actual joined Petalburg garden23/24,22/23 confirms primary7 is a solid raised rectangular framed planter (collision7/elevation0), not walkable ground flowers. The complete original Crystal AzaleaGym16px flower planter supplies its full wooden frame/base and both intact pink/red blossoms at1:1. Connected exterior pink floor corners alone expose matching selected native field; the closed frame protects every interior flower highlight. Every retained native plant/frame pixel is independently asserted exact. Source planter blocking, surrounding grass, actors and events remain unchanged.',dict(native_complete_planter=pot,source_context=['emerald','EM_PETALBURG_CITY',23,22],source_collision=7,source_elevation=0,native_dimensions=[16,16],native_retained_pixels=sum(mask),every_retained_native_pixel_exact=True,only_connected_exterior_floor_removed=True,pixel_scale=1))

 def inherited_field_and_sign_bases(self):
  sign=self.gb_at('crystal','PALLET_TOWN',3,5);image=self.gb_image(sign)
  bg=set(self.gb_image(self.gb_at('crystal','PALLET_TOWN',3,4)).get_flattened_data());outside=exterior(image,bg)
  mask=[(x,y)not in outside for y in range(16)for x in range(16)]
  parts=[dict(p,donor=sign,srcX=p['x'],srcY=p['y'])for p in runs(mask)]
  field=ground_ref(self,'gen2');sand=self.raw_ref('TILESET_KANTO',(48,57,57,48),'PALLET_TOWN')
  for group in self.group_list:
   i=group['review_index']
   if group['family']!='primary'or group['mid']!=2 or i in self.recipes or not group['missing']:continue
   art=self.native(field,'reverse_gen2_hoenn_native_field_below_complete_bank');art['overMask']='0'*256
   self.emit(group,art,'Actual joined Petalburg pond/field source review confirms primary2 is ordinary nonencounter field with only a tiny inherited brown lip from the bank immediately above, not a sign, object or blocked boulder. The full original Crystal bank is already complete in its preceding source row, so the complete native field cell continues below it. No freestanding plaque, extra collision marker or duplicate border object is invented. The actual sign is the distinct original source3 and remains separately mapped. Original source collision, water boundaries, terrain, interactions, actors and events remain unchanged.',dict(native_complete_field=field,native_dimensions=[16,16],source_feature='ordinary field below preceding bank lip',source_context=['emerald','EM_PETALBURG_CITY'],whole_native_bank_in_preceding_row=True,pixel_scale=1))
  # Existing general donor aliases used field under Dewford's signs. The
  # actual whole town is sandy; only the outside ground changes here.
  changes=[]
  for game in GAMES:
   for mid in(3,26):
    key=(game,'gen2','general__dewford',mid,None)
    if not self.counts[game,'general__dewford',mid]:continue
    row=self.rows.get(key)or(self.locations[key][2]if key in self.locations else None)
    if row is None:continue
    art=self.composite(sand,parts,row['role']);art['overMask']='0'*256
    new=self.replace_art(row,art,'The actual Dewford source sign stands on sand. Its entire original Crystal sign frame/text face/feet stay exact, while connected exterior ground becomes the matching native sand used by every surrounding cell. Source sign collision and text event stay unchanged.',dict(native_sign=sign,matching_native_floor=sand,complete_original_sign=True,pixel_scale=1))
    result=self.render(new);assert all(not mask[y*16+x]or result.getpixel((x,y))==image.getpixel((x,y))for y in range(16)for x in range(16))
    changes.append(list(key))
  self.proofs['dewford_sign_sand_rebase']=changes

 def restore_reviewed_templates(self):
  # After activation the exact superseded old rows no longer exist in
  # their original modules. Keep the shipped recipes as a read-only pool
  # for those bindings, without marking any own key occupied or preventing
  # a newly reviewed manual recipe from replacing it.
  restored=[]
  for row in self.templates:
   key=identity(row)
   if key in self.rows or key in self.occupied:continue
   assert row['game']in GAMES and row['style']=='gen2'and row.get('map')is None and scope(row['tileset'],row['id'])
   assert row['id']not in CITY_BUILDING_RESERVED.get(row['tileset'],set()),('Former outdoor template now belongs to city author',key)
   cell=self.imp.cell_index(row['game'])[row['tileset'],row['id']]
   assert row['sourceHash']==cell['pixel_sha256']and row.get('sourceBehavior')==cell.get('behavior'),('Previously reviewed source changed',key)
   assert catalog.sha(self.render(row).tobytes())==row['compositionPixelHash'],('Previously reviewed native recipe changed',key)
   self.rows[key]=copy.deepcopy(row);restored.append(list(key))
  for group in self.group_list:
   i=group['review_index']
   if i in self.recipes or not group['missing']:continue
   keys=[(s['game'],'gen2',s['pair'],s['mid'],None)for s in group['missing']]
   if all(key in self.rows for key in keys):self.recipes[i]=dict(art=artwork(self.rows[keys[0]]),reason='Exact previously reviewed own-module recipe restored after source-key supersession.',proof=dict(restored_source_keys=[list(k)for k in keys],own_templates_do_not_occupy_keys=True))
  self.proofs['own_native_recipe_templates_restored']=restored

 def stabilize_reviewed_templates(self):
  # Repeated authoring may rebuild identical art through a different
  # evidence path after old-key removals. Preserve the exact shipped row
  # when every source guard AND every runtime artwork field still agree;
  # new pixel/mask/animation choices are never suppressed.
  preserved=[]
  for old in self.templates:
   key=identity(old);new=self.rows.get(key)
   if new is None:continue
   fields=('role','overMask','animationCategory','sourceHash','sourceBehavior','compositionPixelHash')
   if artwork(old)==artwork(new)and all(old.get(k)==new.get(k)for k in fields):
    self.rows[key]=copy.deepcopy(old)
    if key in self.supersessions:self.supersessions[key]['new_row']=self.rows[key]
    preserved.append(list(key))
  self.proofs['identical_own_native_recipe_rows_preserved']=preserved

 def underwater_ref(self,bid,q):
  # Crystal has no dive map. This is an explicitly adapted underwater
  # material family made from ORIGINAL full Crystal cave/plant geometry
  # and an ORIGINAL Crystal DAY water palette, never recolored GBA art.
  colors=[[189,189,255],[148,156,255],[107,99,255],[58,58,58]]
  ref=self.gb_ref('crystal','UNION_CAVE_1F',bid,q);ref['palettes']=[copy.deepcopy(colors)for _ in range(8)]
  return ref

 def underwater_native_materials(self):
  # Actual four-byte native layout collision/elevation review resolves a
  # deceptive source palette: pale531 is BLOCKED reef, darker534 is walk
  # floor. Neither thumbnail brightness nor MB_NORMAL identifies floor.
  refs={531:self.underwater_ref(4,3),534:self.underwater_ref(2,0),
   559:self.underwater_ref(24,0),696:self.underwater_ref(24,0)}
  kelp=self.raw_ref('TILESET_JOHTO',(4,4,4,4),'NEW_BARK_TOWN')
  kelp['palettes']=copy.deepcopy(self.underwater_ref(2,0)['palettes'])
  refs.update({513:kelp,641:kelp})
  for group in self.group_list:
   i,mid=group['review_index'],group['mid']
   if group['family']!='general__underwater'or i in self.recipes or not group['missing']or mid not in refs:continue
   ref=refs[mid];kind={531:'raised_reef_fill',534:'walkable_seafloor',559:'whole_fixed_reef_boulder',696:'whole_decorative_seafloor_boulder',513:'complete_native_seaweed',641:'complete_native_seaweed'}[mid]
   art=self.native(ref,'reverse_gen2_hoenn_underwater_'+kind);art['overMask']='0'*256
   if mid in(513,641):
    neutral=self.neutral(ref);art['overMask']=''.join('1'if y>=8 and neutral.getpixel((x,y))[0]!=255 else'0'for y in range(16)for x in range(16))
   self.emit(group,art,'Actual complete underwater source maps and four-byte collision/elevation grids identify531 as raised blocked reef fill,534 as walkable seafloor,513/641 as seaweed,559 as a whole blocked round reef rock and696 as a complete decorative lower-depth rock. Their selected-style counterparts use complete original Crystal cave plateau/floor/boulder or encounter-plant cells at1:1, in the actual original Cianwood DAY four-shade blue water palette. This is a coherent newly adapted Gen2 underwater family from original GB artwork and palette, not a blanket recolor or guessed equivalent based on blue/purple source pixels. Every boulder/canopy glyph remains complete. Lower seaweed leaf pixels cover actor feet, while all original dive/surface flags, encounters, source elevation, collision, scripts, actors and positions remain unchanged.',dict(native_counterpart=ref,source_mid=mid,native_underwater_feature=kind,source_context='tileshift-reverse-gen2-underwater-source-review/review.json',native_palette_source=['crystal','CIANWOOD_CITY','DAY',20,4],original_native_geometry=True,all_eight_palette_slots_explicit=True,native_dimensions=[16,16],pixel_scale=1))
  handed={530:(4,2),532:(6,3),539:(12,3),518:(14,3),522:(4,0),524:(6,1)}
  for group in self.group_list:
   i,mid=group['review_index'],group['mid']
   if group['family']!='general__underwater'or i in self.recipes or not group['missing']or mid not in handed:continue
   bid,q=handed[mid];ref=self.underwater_ref(bid,q);art=self.native(ref,'reverse_gen2_hoenn_underwater_handed_reef_'+str(mid));art['overMask']='0'*256
   self.emit(group,art,'Independent marked underwater map/collision/elevation review establishes the complete reef geometry:530 west-facing face has mass right and floor left;532 east-facing face has mass left and floor right;539 front mass is above the floor;518 is a convex southeast mass corner;522 the northwest raised cap;524 the northeast raised cap. Each receives the matching entire original Crystal cave glyph at1:1 in the same actual native Cianwood DAY blue palette as the separately verified raised fill and walkable seafloor. Handedness comes from joined reef/floor positions, not source brightness or a reused number. Complete native corner/face highlights, source dive/surface behavior, collisions, elevations and events remain unchanged.',dict(native_counterpart=ref,source_mid=mid,source_context='tileshift-reverse-gen2-underwater-source-review/contacts-01..04.png',native_palette_source=['crystal','CIANWOOD_CITY','DAY',20,4],joined_reef_geometry=True,pixel_scale=1))

 def reviewed_indexed_cave_aliases(self):
  # These specific dry cave families were independently inspected in
  # contacts24..31. Their ENTIRE indexed under/mid/over picture is exactly
  # an already reviewed native source shape; only material palette differs.
  # This whitelist deliberately excludes blue icy counterparts, unrelated
  # pair families, generic flat-color guesses and unreviewed future groups.
  allowed={513,516,520,521,522,528,529,530,536,537,538,539,540,592,723,724,725,729,731,732,741,742,743,747,748,749,751,753,755,756,757,759,788,789,795,796,797,803,804,805,816,819,824,825,826,828,829,833,912}
  known=defaultdict(list);effective={identity(r):r for r in self.prior};effective.update(self.rows)
  def signature(game,pair,mid,behavior):return(behavior,digest([catalog.sha(p)for p in native_geometry(self,game,pair,mid)]))
  for row in effective.values():
   if row['game']not in GAMES or row.get('style')!='gen2'or row['tileset']!='general__cave'or row.get('map')is not None:continue
   known[signature(row['game'],row['tileset'],row['id'],row['sourceBehavior'])].append(row)
  for group in self.group_list:
   i=group['review_index']
   if group['family']!='general__cave'or group['mid']not in allowed or i in self.recipes or not group['missing']:continue
   s=group['source'][0];options=known.get(signature(s['game'],s['pair'],s['mid'],s['behavior']),[])
   if not options:continue
   # Native source geometry alone may not resolve two previously selected
   # palettes/compositions. Require an identical final native counterpart.
   if len({(catalog.sha(self.render(r).tobytes()),r.get('overMask'))for r in options})!=1:continue
   row=options[0];art=artwork(row);art['role']=row['role']
   for field in('overMask','animationCategory'):
    if field in row:art[field]=copy.deepcopy(row[field])
   self.emit(group,art,'Explicitly inspected dry-cave material variant has an exact whole indexed under/mid/over picture and identical source behavior to the named previously reviewed cave shape. The same complete original Crystal cliff/corner/floor/stair/ladder/boulder counterpart is retained unchanged at1:1. This is a bound source-geometry identity, not an inferred average color, numeric-ID alias or palette-only substitute; blue ice and unrelated tile families are excluded.',dict(exact_indexed_source=[row['game'],row['tileset'],row['id']],exact_all_native_indexed_planes=True,canonical_native_output_sha256=catalog.sha(self.render(row).tobytes()),explicit_dry_cave_family=True))

 def service_caps(self):
  from reverse_oldale_review import native_piece,mask_piece
  ground=ground_ref(self,'gen2')
  for kind,columns in(('center',{2:[107,108],3:[109,110]}),('mart',{3:[69,70]})):
   whole=Image.new('RGBA',(64,64));pieces={}
   for y in range(4):
    for x in range(4):
     pieces[x,y]=native_piece(self,'gen2',kind,x,y);whole.paste(self.render(pieces[x,y]),(x*16,y*16))
   outside=exterior(whole,set(self.gb_image(ground).get_flattened_data())|{(222,255,222,255)})
   for x,indices in columns.items():
    mask=[(x*16+px,py)not in outside for py in range(16)for px in range(16)]
    art=mask_piece(self,pieces[x,0],mask,ground,True)
    art['role']='reverse_gen2_hoenn_complete_native_'+kind+'_right_roof_cap_'+str(x)
    for i in indices:
     group=self.group_list[i]
     if i in self.recipes or not group['missing']:continue
     self.emit(group,art,'The separately reviewed generic Hoenn '+kind+' roof has the same complete64px clinic/shop body and entrance as the completed Oldale family. Its ordinary right cap receives the matching intact Crystal roof modules; native frames/signs/windows are shared unchanged, corners expose matching field, and roof pixels keep foreground priority. The Oldale tree-behind special cap is not copied into ordinary roofs.',dict(complete_native_model=[64,64],source_column=x,source_row=0,existing_oldale_body_unchanged=True))
   whole.save(self.out/('complete-native-'+kind+'-whole64.png'))

 def dewford_homes(self):
  from reverse_oldale_review import mask_piece,native_piece
  field=ground_ref(self,'gen2');sand=self.raw_ref('TILESET_KANTO',(48,57,57,48),'PALLET_TOWN')
  # Actual native New Bark64x64 home, complete roof, door and right window.
  # Dewford has a second window to the left of the same entrance: repeat
  # the original complete16x8 window pair, never narrow either half.
  pieces={};whole=Image.new('RGBA',(64,64))
  for y in range(4):
   for x in range(4):
    parts=self.gb_rect('crystal','NEW_BARK_TOWN',(12+x)*16,(2+y)*16,16,16)
    if y==2 and x in(0,1):
     parts+=self.gb_rect('crystal','NEW_BARK_TOWN',12*16+40+(x*8),2*16+40,8,8,8 if x==0 else 0,8)
    art=self.composite(None,parts,'reverse_gen2_hoenn_dewford_complete_native_home');pieces[x,y]=art;whole.paste(self.render(art),(x*16,y*16))
  outside=exterior(whole,set(self.gb_image(field).get_flattened_data())|{(222,255,222,255)})
  for(x,y),art in list(pieces.items()):
   mask=[(x*16+px,y*16+py)not in outside for py in range(16)for px in range(16)]
   pieces[x,y]=mask_piece(self,art,mask,sand,y<2)
  # The fifth column on the wider native house consists exclusively of
  # repeating roof/wall/window modules; all outer caps and its door remain.
  modules={523:(0,0),524:(1,0),525:(3,0),529:(0,0),530:(1,0),536:(3,0),
   531:(0,1),532:(1,1),533:(3,1),526:(0,2),541:(1,2),542:(2,2),527:(3,2),
   534:(0,3),549:(1,3),550:(2,3),551:(2,3),535:(3,3)}
  for group in self.group_list:
   if group['family']!='general__dewford' or group['review_index']in self.recipes or not group['missing']:continue
   mid=group['mid']
   if mid in modules:
    x,y=modules[mid];art=copy.deepcopy(pieces[x,y])
   elif mid==543:
    # Whole ordinary wall cell plus one complete native16x8 window pair.
    parts=self.gb_rect('crystal','NEW_BARK_TOWN',12*16+16,2*16+32,16,8)
    parts+=self.gb_rect('crystal','NEW_BARK_TOWN',12*16+40,2*16+40,16,8,0,8)
    art=self.composite(sand,parts,'reverse_gen2_hoenn_dewford_wide_home_complete_window_repeat');art['overMask']='0'*256
   elif mid in(515,516,517,518,521,522):
    x,y={515:(0,0),516:(1,0),517:(2,0),518:(3,0),521:(0,3),522:(3,3)}[mid]
    clinic=Image.new('RGBA',(64,64));model={}
    for yy in range(4):
     for xx in range(4):
      p=native_piece(self,'gen2','center',xx,yy);model[xx,yy]=p;clinic.paste(self.render(p),(xx*16,yy*16))
    border=exterior(clinic,set(self.gb_image(field).get_flattened_data())|{(222,255,222,255)})
    art=mask_piece(self,model[x,y],[(x*16+px,y*16+py)not in border for py in range(16)for px in range(16)],sand,y<2)
   else:continue
   self.emit(group,art,'The complete Dewford native4x4 home keeps the original Crystal New Bark64x64 house roof, side caps, full entrance frame, wall base and windows at1:1. Its second window repeats the entire original16x8 window pair. The wider5-column source house repeats only ordinary roof/wall/window modules and keeps both exterior caps and the original entrance anchor. Clinic corner variants use the exact existing full Crystal clinic body, with matching native sand outside true corners. Whole-building exterior masks prevent grass halos; no roof/facade feature is shrunk or cropped.',dict(native_complete_model=['crystal','NEW_BARK_TOWN',12,2,4,4],native_window_pair=[40,40,16,8],pixel_scale=1,source_mid=mid,background='native Crystal Kanto sand'))
  whole.save(self.out/'dewford-native-complete-home64.png')
  self.proofs['dewford_native_complete_home']=dict(native_model=['crystal','NEW_BARK_TOWN',12,2,4,4],native_windows_repeated_without_scaling=True,complete_original_roof_door_right_window_retained=True,whole_dimensions=[64,64],wide_source_dimensions=[80,64])

 def primary_homes(self):
  from reverse_oldale_review import mask_piece
  ground=ground_ref(self,'gen2');ox,oy=192,32
  layout=[[8,9,9,9,10],[16,17,17,17,18],[24,11,25,11,26],[32,19,33,19,34]]
  rects={8:[(0,0,16,16,0,0)],9:[(16,0,16,16,0,0)],10:[(48,0,16,16,0,0)],
   16:[(0,16,16,16,0,0)],17:[(16,16,16,16,0,0)],18:[(48,16,16,16,0,0)],
   24:[(0,32,16,16,0,0)],25:[(16,32,16,16,0,0)],
   26:[(48,32,16,16,0,0),(16,32,8,16,0,0)],
   32:[(0,48,16,16,0,0)],19:[(32,48,16,16,0,0)],33:[(16,48,16,16,0,0)],34:[(48,48,16,16,0,0)],
   11:[(16,32,16,16,0,0),(40,40,16,8,0,8)]}
  raw={};whole=Image.new('RGBA',(80,64))
  for mid,items in rects.items():
   parts=[]
   for sx,sy,w,h,x,y in items:parts+=self.gb_rect('crystal','NEW_BARK_TOWN',ox+sx,oy+sy,w,h,x,y)
   raw[mid]=self.composite(None,parts,'reverse_gen2_hoenn_complete_native_primary_home_'+str(mid))
  for y,row in enumerate(layout):
   for x,mid in enumerate(row):whole.paste(self.render(raw[mid]),(x*16,y*16))
  outside=exterior(whole,set(self.gb_image(ground).get_flattened_data())|{(222,255,222,255)})
  art_by_mid={}
  for y,row in enumerate(layout):
   for x,mid in enumerate(row):
    mask=[(x*16+px,y*16+py)not in outside for py in range(16)for px in range(16)]
    art=mask_piece(self,raw[mid],mask,ground,y<2)
    if mid in art_by_mid:
     assert self.render(art_by_mid[mid]).tobytes()==self.render(art).tobytes()and art_by_mid[mid]['overMask']==art['overMask'],('Repeated native home module differs',mid)
    else:art_by_mid[mid]=art
  for group in self.group_list:
   mid=group['mid'];i=group['review_index']
   if group['family']!='primary'or mid not in art_by_mid or i in self.recipes or not group['missing']:continue
   self.emit(group,art_by_mid[mid],'Independent whole-building source review of Petalburg primary home at5,2 (80x64) and the shared native route-house modules. The original Crystal New Bark64x64 house supplies complete roof caps, door frame, wall base and both complete16x8 window pairs at1:1. Only ordinary internal roof/wall bands repeat to the source width; each repeated source window11 receives a full window, and outercap26 keeps its unique outer8px while its now-duplicate half-window is replaced with original plain wall. Source door33 remains at its original anchor, with correct facade joins and transparent grassy corners. Source collisions, warps, actors and all events stay unchanged.',dict(native_complete_model=['crystal','NEW_BARK_TOWN',12,2,4,4],source_example=['emerald','EM_PETALBURG_CITY',5,2,5,4],native_model_parts=[list(rect)for rect in rects[mid]],source_entrance_module=33,complete_native_window_pair=[40,40,16,8],source_primary_module=mid,pixel_scale=1))
  whole.save(self.out/'primary-native-complete-home80.png')
  self.proofs['primary_native_complete_home']=dict(source_layout=layout,native_original_dimensions=[64,64],source_model_dimensions=[80,64],pixel_scale=1,complete_window_destinations=[[16,40,16,8],[48,40,16,8]],native_door_destination=[32,48,16,16],all_caps_and_complete_window_door_features_preserved=True)

 def standard_gyms(self):
  from reverse_oldale_review import mask_piece
  ground=ground_ref(self,'gen2');sand=self.raw_ref('TILESET_KANTO',(48,57,57,48),'PALLET_TOWN');ox,oy=16*16,14*16
  layout=[[426,427,427,427,427,428],[434,435,435,435,435,436],
   [440,441,442,435,443,444],[448,449,450,453,451,452],[456,457,458,461,459,460]]
  def native(sx,sy,w=16,h=16,x=0,y=0):return self.gb_rect('crystal','VIOLET_CITY',ox+sx,oy+sy,w,h,x,y)
  raw={}
  for mid,col in((426,0),(427,1),(428,5)):raw[mid]=native(col*16,0)
  for mid,col in((434,0),(435,1),(436,5)):raw[mid]=native(col*16,8)
  for mid,col in((440,0),(441,1),(442,2),(443,4),(444,5)):raw[mid]=native(col*16,16)
  for mid,col in((448,0),(449,1),(451,4),(452,5)):raw[mid]=native(col*16,32)
  # Move the ENTIRE original two-cell GYM label together, not half of a
  # letter. The projecting center roof has its complete cornice above it.
  raw[450]=native(32,40,16,8)+native(32,32,16,8,0,8)
  raw[453]=native(48,24,16,8)+native(48,32,16,8,0,8)
  for mid,col in((456,0),(457,1),(458,3),(459,4),(460,5)):raw[mid]=native(col*16,48)
  raw[461]=native(32,48)
  raw={mid:self.composite(None,parts,'reverse_gen2_hoenn_complete_native_gym_'+str(mid))for mid,parts in raw.items()}
  whole=Image.new('RGBA',(96,80))
  for y,row in enumerate(layout):
   for x,mid in enumerate(row):whole.paste(self.render(raw[mid]),(x*16,y*16))
  outside=exterior(whole,set(self.gb_image(ground).get_flattened_data())|{(222,255,222,255)})
  bybase={}
  for base_name,base in(('field',ground),('sand',sand)):
   recipes={}
   for y,row in enumerate(layout):
    for x,mid in enumerate(row):
     mask=[(x*16+px,y*16+py)not in outside for py in range(16)for px in range(16)]
     art=mask_piece(self,raw[mid],mask,base,y<3)
     if mid==453:art['overMask']=''.join('1'if mask[py*16+px]and py<8 else'0'for py in range(16)for px in range(16))
     if mid in recipes:assert self.render(recipes[mid]).tobytes()==self.render(art).tobytes()and recipes[mid]['overMask']==art['overMask'],('Repeated gym module differs',mid)
     else:recipes[mid]=art
   bybase[base_name]=recipes
  # Dewford's sand-backed variants use the identical standard gym body;
  # only its actual outside roof/base corners expose a different floor.
  dewford={538:426,539:427,540:428,546:434,547:435,548:436,
   555:440,556:441,557:442,558:443,559:444,
   563:448,564:449,565:450,566:451,567:452,
   571:456,572:457,573:458,574:459,575:460}
  for group in self.group_list:
   i,mid=group['review_index'],group['mid'];family=group['family']
   if i in self.recipes or not group['missing']:continue
   if family=='primary'and mid in raw:art=bybase['field'][mid];counterpart=mid
   elif family=='general__dewford'and mid in dewford:counterpart=dewford[mid];art=bybase['sand'][counterpart]
   else:continue
   self.emit(group,art,'Independent complete standard Hoenn gym source review: Petalburg12,4 is96x80 with original door atrelative3,4. The original Crystal Violet gym96x64 retains all complete windows, facade/roof caps, full cornice, full32x8 GYM sign and16px doorway at1:1. One ordinary plain roof band repeats to80px height. Shared435 remains plain roof at every occurrence; the complete sign strip moves down8px together, distinct453 keeps a full cornice above it, and the full door moves to the original Hoenn entrance column while its former donor slot becomes original plain siding. No cropped word/window, duplicate cornice midroof or reduced facade. True corners expose matching field/sand and only actual roof pixels receive foreground priority; source collision/warps/actors/events remain unchanged.',dict(native_complete_gym=['crystal','VIOLET_CITY',16,14,6,4],source_model=['emerald','EM_PETALBURG_CITY',12,4,6,5],native_pixel_scale=1,source_door_relative=[3,4],complete_native_sign_strip=[32,32,32,8],sign_destination=[32,56,32,8],source_module=mid,native_model_module=counterpart))
  whole.save(self.out/'standard-native-complete-gym96x80.png')
  # Exact complete feature pixel preservation, independent of serialized
  # per-cell recipes and exterior-floor masking.
  donor_word=Image.new('RGBA',(32,8));donor_door=self.render(self.composite(None,native(32,48),'proof'))
  for x in range(2):donor_word.paste(self.render(self.composite(None,native(32+x*16,32,16,8),'proof')).crop((0,0,16,8)),(x*16,0))
  assert whole.crop((32,56,64,64)).tobytes()==donor_word.tobytes()
  assert whole.crop((48,64,64,80)).tobytes()==donor_door.tobytes()
  self.proofs['standard_native_complete_gym']=dict(native_dimensions=[96,64],target_dimensions=[96,80],pixel_scale=1,full_native_word_rgba_sha256=catalog.sha(donor_word.tobytes()),full_native_door_rgba_sha256=catalog.sha(donor_door.tobytes()),complete_sign_and_door_exact=True,source_layout=layout)

 def whole_big_pines_and_shrubs(self):
  from reverse_kanto_review import tree_art
  ground=ground_ref(self,'gen2')
  for q,indices in((0,[51,52]),(1,[53,54]),(2,[63]),(3,[64])):
   art=self.park_tree_art(q,ground);art['overMask']='0'*256
   for i in indices:
    group=self.group_list[i]
    if i in self.recipes or not group['missing']:continue
    self.emit(group,art,'The complete four-cell Hoenn decorative pine receives the complete native32x32 Crystal NationalPark tree, all four original canopy/root sections at1:1. Native-map context proves this is one2x2 tree, not a partial taller canopy. No extra trunk, missing tip, fractional scale or cropped source object.',dict(native_tree=['crystal','NATIONAL_PARK',6],quadrant=q,whole_native_dimensions=[32,32],context_proof='primary-tree-contexts.json'))
  # Actual Route105 shows468/469+476/477 repeat EVERY TWO ROWS:
  # the trunk is already complete in476/477.484/485 are lower-edge
  # variants of those SAME under-planes, without a next-row cap overlay.
  # Never invent a third leaf/trunk row from those separate aliases.
  forest={0:[555,556,559,560],1:[557,558,561,562],
   2:[567,568,571,576,577,580,581,602,603,604,605],
   3:[569,570,572,578,579,582,583,600,601,606,607]}
  for q,indices in forest.items():
   art=self.park_tree_art(q,ground);art['role']='reverse_gen2_hoenn_complete_native_forest_tree_'+str(q)
   for i in indices:
    group=self.group_list[i]
    if i in self.recipes or not group['missing']:continue
    self.emit(group,art,'Joined actual Route105 tree/forest review proves this is one complete32x32 tree: native468/469 crown and476/477 trunk repeat every two source rows.484/485 have identical lower-tree under-planes without the next-tree tiny cap;498/499 have the opposite complete root half beneath a next-row crown cap. The corresponding full native Crystal NationalPark32x32 canopy/root quadrant is retained at1:1, with no inserted leaf band, third trunk row, missing native section or scaling. Only next-row Hoenn cap fragments outside the complete classic32px tree footprint are omitted; the next native tree begins in its original following row.',dict(native_complete_tree=['crystal','NATIONAL_PARK',6],native_dimensions=[32,32],quadrant=q,pixel_scale=1,source_joined_context='r105-six-tree-native-context.png',source_native_repetition_rows=2))
  for i in(584,585,586,587):
   group=self.group_list[i]
   if i in self.recipes or not group['missing']:continue
   q=0 if group['mid']==488 else 1;cap=self.park_tree_art(q,ground);parts=[];mask=['0']*256
   for p in cap['parts']:
    top=p.get('y',0);bottom=min(top+p['h'],8)
    if top>=bottom:continue
    part=copy.deepcopy(p);part.update(h=bottom-top,y=top+8);parts.append(part)
    for yy in range(top+8,bottom+8):
     for xx in range(part.get('x',0),part.get('x',0)+part['w']):mask[yy*16+xx]='1'
   assert parts and len(parts)<=32
   art=self.composite(ground,parts,'reverse_gen2_hoenn_native_next_row_tree_apex');art['overMask']=''.join(mask)
   self.emit(group,art,'Exact joined Lilycove/Route115/Safari source review identifies488/489 as mostly ordinary field with only the next tree apex at the bottom, not a third trunk cell. The complete original Crystal canopy apex8px band is retained at1:1 along that lower edge, while the intact native32px tree remains in the following two rows. The same original source is walkable in95 contexts and blocked in12 Lilycove contexts despite the original grass center; those native collision/overhang semantics remain unchanged. No duplicate full canopy or invisible all-field replacement is introduced. Route104500/501 are separately confirmed substantial tree ROOT halves and receive the full corresponding native root, never this field-cap recipe.',dict(native_complete_tree=['crystal','NATIONAL_PARK',6],native_tree_size=[32,32],native_apex_band_height=8,native_apex_band_source_y=0,apex_destination_y=8,next_row_cap_outside_native_tree=True,source_context='EM_LILYCOVE_CITY-exact-tree-sign-grid-context.png',collision_audit='tree-cap-walkability-audit.json',pixel_scale=1))
  # Complete one-cell original Crystal Headbutt-tree artwork, used purely
  # as art: source Gen3 topiary remains decorative and gains no interaction.
  ref=self.raw_ref('TILESET_JOHTO',(30,31,62,63),'NEW_BARK_TOWN');im=self.gb_image(ref)
  bg=set(self.gb_image(ground).get_flattened_data());outside=exterior(im,bg)
  parts=[dict(donor=ref,srcX=p['x'],srcY=p['y'],**p)for p in runs([(x,y)not in outside for y in range(16)for x in range(16)])]
  assert 0<len(parts)<=32
  for i in(2318,2319,2351,2352,2358,2359):
   group=self.group_list[i]
   if i in self.recipes or not group['missing']:continue
   art=self.composite(ground,parts,'reverse_gen2_hoenn_complete_native_small_decorative_tree');art['overMask']='0'*256
   self.emit(group,art,'This complete small decorative topiary uses the intact native Crystal16px small-tree counterpart at1:1. Every leaf and trunk pixel remains; original source Gen3 collision and lack of Cut/Headbutt interaction remain unchanged.',dict(native_counterpart=ref,native_dimensions=[16,16]))

 def paving(self):
  ground=ground_ref(self,'gen2');pave=self.raw_ref('TILESET_JOHTO',(6,6,6,6),'VIOLET_CITY')
  groups=[312,313,314,315,316,327,328,329,330,331,337,338,339,340,341,
   2339,2340,2344,2345,2402,2418,2419,
   2353,2354,2355,2356,2357,2404,2405,2406,2407,2411,2412,2413,2414,2415,2416,2417]
  for i in groups:
   group=self.group_list[i]
   if i in self.recipes or not group['missing']:continue
   source=next((s for s in group['source']if s['game']=='emerald'),group['source'][0]);game,pair=source['game'],source['pair'];index=self.imp.cell_index(game)
   field=index[pair,1];field_image=preview.native_donor(self.cache,dict(game=game,tileset=pair,id=1,hash=field['pixel_sha256']),self.packed)
   native=preview.native_donor(self.cache,dict(game=game,tileset=pair,id=source['mid'],hash=source['hash']),self.packed)
   field_colors=set(field_image.get_flattened_data());mask=[p not in field_colors for p in native.get_flattened_data()]
   spans=runs(mask);assert 0<len(spans)<=32,(i,'paving mask fragments',len(spans))
   parts=[dict(donor=pave,srcX=p['x'],srcY=p['y'],**p)for p in spans]
   art=self.composite(ground,parts,'reverse_gen2_hoenn_native_paved_ground');art['overMask']='0'*256
   self.emit(group,art,'The separately reviewed walkable stone/brick path receives the complete repeatable native Crystal paving texture at1:1. Only the actual visible path footprint is filled; checked native field pixels outside its handed corner/edge and in its grassy joints expose matching classic field. No wall, fence, pillar, step or unique object is treated as floor.',dict(native_paving=pave,native_field_source=[game,pair,1],source_field_rgba_hash=field['pixel_sha256'],reviewed_path_mask_sha256=digest(mask),paved_pixels=sum(mask)))
  for i in(2289,2293,2320,2321,2421,2422):
   group=self.group_list[i]
   if i in self.recipes or not group['missing']:continue
   art=self.native(ground,'reverse_gen2_hoenn_nonencounter_field_variant');art['overMask']='0'*256
   self.emit(group,art,'Complete native Crystal nonencounter field replaces this separately reviewed ordinary field shade/wear variation. It contains no path edge, object, tall encounter grass, water or building feature.',dict(native_counterpart=ground))

 def native_programs(self):
  effective={identity(r):r for r in self.prior};effective.update(self.rows);changed=[]
  for k,row in list(effective.items()):
   if row['game']not in GAMES or row['style']!='gen2'or not scope(row['tileset'],row['id'])or row.get('animated')or not row.get('donor'):continue
   ref=row['donor']
   if ref['game']!='crystal':continue
   spec=specification(self.cache,ref,'program')
   if not spec:continue
   art=artwork(row);art.update(role=row['role'],animated=True,animation=spec,animationCategory='water')
   if 'overMask'in row:art['overMask']=row['overMask']
   if k in self.rows:
    new=self.rows[k];new.update(animated=True,animation=spec,animationCategory='water');new['compositionPixelHash']=catalog.sha(self.render(new).tobytes())
   else:
    new=self.row(row['game'],row['tileset'],row['id'],'gen2',art,row['evidence']+' The checked original Crystal native animation program, including scrolling cave water/waterfalls, is now replayed with its original complete glyphs and native timing. No invented wave frames or source behavior changes.')
    path,index,old=self.locations[k];self.supersessions[k]=dict(module=path,old_index=index,old_row=old,full_row_sha256=digest(old),new_module=Path(getattr(self,'target_module',TARGET)).relative_to(ROOT).as_posix(),new_row=new)
   new.setdefault('reverseGen2OutdoorReview',{}).update(native_program=True,pixel_scale=1)
   changed.append(dict(source=list(k),native_ref=ref,program=spec))
  self.proofs['native_program_upgrades']=changed

 def build(self):
  self.preserve_black_canvases();self.existing_aliases();self.core_nature();self.cave_basics();self.cave_joined_edges();self.joined_dry_cave_contracts();self.ordinary_materials();self.simple_native_shores();self.cave_water_and_lava();self.reviewed_broad_materials();self.directional_currents();self.reviewed_complete_water_variants();self.whole_water_boulder();self.native_city_curbs();self.dewford_trees_and_pier();self.reviewed_ocean_cliffs();self.meteor_native_basics();self.meteor_joined_walls();self.navel_joined_native_cave();self.petalburg_native_hedges_and_planters();self.inherited_field_and_sign_bases();self.underwater_native_materials();self.service_caps();self.dewford_homes();self.primary_homes();self.standard_gyms();self.whole_big_pines_and_shrubs();self.paving();self.flowers();self.reviewed_indexed_cave_aliases();self.restore_reviewed_templates();self.upgrade_whole_tree_sources();self.native_programs();self.exact_visual_aliases();self.exact_shared_nature_aliases();self.coherent_cave_water();self.stabilize_reviewed_templates()
  held=[]
  for group in self.group_list:
   if group['missing']and group['review_index']not in self.recipes:held.append(group)
  (self.out/'held-source-groups.json').write_text(json.dumps(held,indent=2)+'\n')
  (self.out/'recipes.json').write_text(json.dumps(self.recipes,indent=2)+'\n')
  (self.out/'supersessions.json').write_text(json.dumps(list(self.supersessions.values()),indent=2)+'\n')
  (self.out/'pixel-preservation-proofs.json').write_text(json.dumps(self.proofs,indent=2)+'\n')
  report=dict(rows=len(self.rows),reviewed_groups=len(self.recipes),remaining_groups=len(held),newly_replaced_source_cells=sum(s['occurrences']for g in self.group_list if g['review_index']in self.recipes for s in g['missing']),
   remaining_source_cells=sum(s['occurrences']for g in held for s in g['missing']),existing_keys_superseded=len(self.supersessions),all_other_existing_rows_unchanged=True,gen1_theme_unchanged=True)
  (self.out/'coverage-stage.json').write_text(json.dumps(report,indent=2)+'\n');return report

 def previews(self):
  own=self.rows.copy();self.rows={identity(r):r for r in self.prior if r['game']in GAMES and r['style']=='gen2'};self.rows.update(own)
  reports=[]
  for game,prefix in(('ruby','RU'),('emerald','EM')):
   for name in('LITTLEROOT_TOWN','OLDALE_TOWN','DEWFORD_TOWN','PETALBURG_CITY','EVER_GRANDE_CITY','ROUTE115','ROUTE119','GRANITE_CAVE_1F'):
    reports.append(self.map_preview(game,prefix+'_'+name,'gen2'))
  layouts=self.imp.table('emerald','gba/native/manifest')['layouts']
  for name in('METEOR_FALLS_1F_1R','NAVEL_ROCK_DOWN02','NAVEL_ROCK_FORK','UNDERWATER_ROUTE124','UNDERWATER_ROUTE125','UNDERWATER_ROUTE126','UNDERWATER_SEALED_CHAMBER'):
   if 'EM_'+name in layouts:reports.append(self.map_preview('emerald','EM_'+name,'gen2'))
  self.rows=own;(self.out/'preview-coverage.json').write_text(json.dumps(reports,indent=2)+'\n')
  return reports

 def primary_contexts(self):
  wanted={14,15,21,22,23,29,30,31,37,38,39,45,46,64,198,199,206,402,403,492,493,498,499,500,501,508,509}
  groups=[g for g in self.groups.values()if g['family']=='primary'and g['mid']in wanted]
  font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',12);pictures={};records=[]
  for start in range(0,len(groups),16):
   canvas=Image.new('RGB',(4*305,4*280),'#18212b');draw=ImageDraw.Draw(canvas)
   for i,g in enumerate(groups[start:start+16]):
    item=next((v for v in g['source']if v['game']=='emerald'),g['source'][0]);context=item['contexts'][0];name=context['map'];game=item['game']
    if(game,name)not in pictures:pictures[game,name]=self.imp.gba(game,name)[0]
    spec=self.imp.table(game,'gba/native/manifest')['layouts'][name];layout=decode_layout(self.cache/game/'data/generated/gba/native'/spec['file'])
    x,y=next((p for p in context['coordinates']if p[0]>=2 and p[1]>=2),context['coordinates'][0]);ox,oy=max(0,x-2),max(0,y-2)
    im=pictures[game,name].crop((ox*16,oy*16,(ox+5)*16,(oy+6)*16));dx,dy=i%4*305,i//4*280
    canvas.paste(im.resize((160,192),Image.Resampling.NEAREST),(dx+4,dy+32));draw.text((dx+4,dy+4),f"{g['review_index']} mid{g['mid']} / {game}",fill='white',font=font)
    draw.text((dx+168,dy+32),'\n'.join(' '.join(f'{layout["mids"][yy*layout["width"]+xx]:3}'if 0<=xx<layout['width']and 0<=yy<layout['height']else'---'for xx in range(ox,ox+5))for yy in range(oy,oy+6)),fill='#d5dfe6',font=font)
    draw.text((dx+4,dy+232),name[3:]+'\n'+str([x,y]),fill='#b1c9d4',font=font)
    records.append(dict(review_index=g['review_index'],source=item,origin=[ox,oy],marked_cell=[x,y]))
   canvas.save(self.out/f'primary-tree-context-{start//16+1:02}.png')
  (self.out/'primary-tree-contexts.json').write_text(json.dumps(records,indent=2)+'\n')

 def inventory(self,contacts=True):
  for game in GAMES:
   index=self.imp.cell_index(game)
   for name,spec in self.imp.table(game,'gba/native/manifest')['layouts'].items():
    pair=spec['pair']
    if not pair.startswith('general__'):continue
    layout=decode_layout(self.cache/game/'data/generated/gba/native'/spec['file'])
    positions=defaultdict(list)
    for i,mid in enumerate(layout['mids']):
     if scope(pair,mid):positions[mid].append([i%layout['width'],i//layout['width']])
    for mid,coords in positions.items():
     self.counts[game,pair,mid]+=len(coords)
     self.usage[game,pair,mid].append(dict(map=name,count=len(coords),coordinates=coords[:8]))
   for(pair,mid),cell in index.items():
    if not scope(pair,mid)or not self.counts[game,pair,mid]:continue
    geometry=native_geometry(self,game,pair,mid)
    sig=digest([mid,'primary'if mid<512 else pair,cell['behavior'],[catalog.sha(g)for g in geometry]])
    group=self.groups.setdefault(sig,dict(mid=mid,family='primary'if mid<512 else pair,source_identity=sig,source=[],existing=[],missing=[]))
    item=dict(game=game,pair=pair,mid=mid,hash=cell['pixel_sha256'],behavior=cell['behavior'],behavior_hint=cell.get('behavior_hint'),
     category=cell.get('native_category'),occurrences=self.counts[game,pair,mid],contexts=self.usage[game,pair,mid][:5])
    group['source'].append(item)
    group['existing'if(game,'gen2',pair,mid,None)in self.occupied else'missing'].append(item)
  # The explicitly handed-off facility outdoor-only cells append after the
  # original reviewed body contacts, keeping those review IDs immutable.
  rows=sorted(self.groups.values(),key=lambda g:(g['family']=='general__facility',g['family']!='primary',g['family'],g['mid']))
  bindings=[[g['family'],g['mid'],g['source_identity'],[[s['game'],s['pair'],s['mid'],s['hash']]for s in g['source']]]for g in rows[:REVIEWED_BODY_GROUP_COUNT]]
  assert len(bindings)==REVIEWED_BODY_GROUP_COUNT and digest(bindings)==REVIEWED_BODY_GROUP_FINGERPRINT,'Native contact identity/order changed: re-review source groups instead of reusing numeric review indices'
  border_path=ROOT.parent/'.work/tileshift-v0320-native-border-inventory.json';export_holes=[];border_added=0
  if border_path.exists():
   known={(s['game'],s['pair'],s['mid'])for g in rows for s in g['source']}
   for item in json.loads(border_path.read_text())['only_border']:
    game,pair,mid=item['game'],item['pair'],item['id']
    if game not in GAMES or not scope(pair,mid)or(game,pair,mid)in known:continue
    cell=self.imp.cell_index(game).get((pair,mid))
    if cell is None:export_holes.append(item);continue
    geometry=native_geometry(self,game,pair,mid)
    sig=digest([mid,'primary'if mid<512 else pair,cell['behavior'],[catalog.sha(g)for g in geometry]])
    group=self.groups.get(sig)
    if group is None:
     group=dict(mid=mid,family='primary'if mid<512 else pair,source_identity=sig,source=[],existing=[],missing=[],border_only_group=True)
     self.groups[sig]=group;rows.append(group)
    entry=dict(game=game,pair=pair,mid=mid,hash=cell['pixel_sha256'],behavior=cell['behavior'],behavior_hint=cell.get('behavior_hint'),category=cell.get('native_category'),
     occurrences=0,border_only=True,contexts=[dict(map=name,count=0,coordinates=[])for name in item['maps']])
    group['source'].append(entry);group['existing'if(game,'gen2',pair,mid,None)in self.occupied else'missing'].append(entry);known.add((game,pair,mid));border_added+=1
  (self.out/'border-native-export-holes.json').write_text(json.dumps(export_holes,indent=2)+'\n');self.proofs['border_only_aliases_added']=border_added
  # Runtime SecretPower opens a metatile only at an ACTUAL imported
  # secret_base background event. The same closed number in another pair
  # may be an unrelated roof/rock, so neither bank membership nor numeric
  # presence alone establishes an opening. Append after frozen contacts.
  dynamic=[];dynamic_holes=[];dynamic_unexpected=[]
  known={(s['game'],s['pair'],s['mid'])for g in rows for s in g['source']}
  for game in GAMES:
   opened={e['closed']:e['open']for e in catalog.lua_array(self.imp.table(game,'gba/secret_base/manifest')['entranceMetatiles'])}
   layouts=self.imp.table(game,'gba/native/manifest')['layouts']
   for name,events in self.imp.table(game,'gba/scripts/events').items():
    if name not in layouts:continue
    actual=[e for e in catalog.lua_array(events.get('bgEvents',{}))if e.get('type')=='secret_base'or e.get('kind')==8]
    if not actual:continue
    spec=layouts[name];pair=spec['pair'];layout=decode_layout(self.cache/game/'data/generated/gba/native'/spec['file']);index=self.imp.cell_index(game)
    for event in actual:
     x,y=event['x'],event['y'];closed=layout['mids'][y*layout['width']+x]
     if closed not in opened:
      dynamic_unexpected.append(dict(game=game,map=name,pair=pair,x=x,y=y,observed_mid=closed,secret_base_id=event.get('secretBaseId')));continue
     mid=opened[closed]
     if not scope(pair,mid):continue
     proof=dict(game=game,map=name,pair=pair,x=x,y=y,closed=closed,open=mid,secret_base_id=event['secretBaseId'],closed_source_hash=index[pair,closed]['pixel_sha256'])
     cell=index.get((pair,mid))
     if cell is None:dynamic_holes.append(proof);continue
     proof['open_source_hash']=cell['pixel_sha256'];dynamic.append(proof)
     if(game,pair,mid)in known:continue
     geometry=native_geometry(self,game,pair,mid);sig=digest([mid,'primary'if mid<512 else pair,cell['behavior'],[catalog.sha(p)for p in geometry]])
     group=self.groups.get(sig)
     if group is None:
      group=dict(mid=mid,family='primary'if mid<512 else pair,source_identity=sig,source=[],existing=[],missing=[],dynamic_only_group=True);self.groups[sig]=group;rows.append(group)
     item=dict(game=game,pair=pair,mid=mid,hash=cell['pixel_sha256'],behavior=cell['behavior'],behavior_hint=cell.get('behavior_hint'),category=cell.get('native_category'),occurrences=0,dynamic_only=True,
      contexts=[dict(map=name,count=0,coordinates=[[x,y]],dynamic_secret_base=True,original_closed_id=closed)])
     group['source'].append(item);group['existing'if(game,'gen2',pair,mid,None)in self.occupied else'missing'].append(item);known.add((game,pair,mid))
  (self.out/'dynamic-secret-base-entrances.json').write_text(json.dumps(dict(actual_events=dynamic,missing_native_exports=dynamic_holes,unmatched_default_source=dynamic_unexpected),indent=2)+'\n')
  self.proofs['actual_dynamic_secret_base_entrances']=dynamic
  self.group_list=rows
  for n,g in enumerate(rows):g['review_index']=n
  (self.out/'inventory.json').write_text(json.dumps(rows,indent=2)+'\n')
  if contacts:
   font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',11)
   for start in range(0,len(rows),64):
    canvas=Image.new('RGB',(8*154,8*126+36),'#18212b');draw=ImageDraw.Draw(canvas)
    draw.text((8,8),'Hoenn native source cells: missing rows marked *; no automatic equivalence approval',fill='white',font=font)
    for i,group in enumerate(rows[start:start+64]):
     item=next((s for s in group['source']if s['game']=='emerald'),group['source'][0]);x,y=i%8*154,i//8*126+34
     ref=dict(game=item['game'],tileset=item['pair'],id=item['mid'],hash=item['hash'])
     im=preview.native_donor(self.cache,ref,self.packed)
     canvas.paste(im.resize((64,64),Image.Resampling.NEAREST),(x+4,y+20))
     draw.text((x+3,y+1),f"{group['review_index']} / {item['mid']}"+(' *'if group['missing']else''),fill='white',font=font)
     draw.text((x+72,y+20),item['pair'].replace('general__','')[:13]+'\n'+str(item['behavior_hint'])[:13]+'\n'+str(sum(s['occurrences']for s in group['source'])),fill='#d2dce4',font=font)
     draw.text((x+3,y+88),item['contexts'][0]['map'][3:24],fill='#a8c4d1',font=font)
    canvas.save(self.out/f'source-contact-{start//64+1:02}.png')
  return dict(groups=len(rows),source_keys=sum(len(g['source'])for g in rows),missing_keys=sum(len(g['missing'])for g in rows),
   source_cells=sum(s['occurrences']for g in rows for s in g['source']),missing_cells=sum(s['occurrences']for g in rows for s in g['missing']))

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inventory',action='store_true');p.add_argument('--no-contacts',action='store_true');p.add_argument('--contexts',action='store_true');p.add_argument('--build',action='store_true');p.add_argument('--previews',action='store_true');p.add_argument('--validate',action='store_true');p.add_argument('--activate',action='store_true');a=p.parse_args()
 review=Review();report=review.inventory(not a.no_contacts)
 if a.contexts:review.primary_contexts()
 if a.build or a.validate or a.activate:
  report['stage']=review.build();review.write(TARGET if a.activate else review.out/'candidates.lua')
  if a.validate or a.activate:report['validation']=review.validate()
  if a.previews:report['previews']=review.previews()
 (review.out/'coverage-before.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
