from pathlib import Path
from PIL import Image
import hashlib,json,sys,copy,shutil
from types import SimpleNamespace
W=Path.cwd();O=W/'.work/tileshift-crystaldust-sweep/special';S=W/'.work/tileshift-v0445-checkpoint/source-final';F=O/'files';sys.path[:0]=[str(W/'.tools/python'),str(S/'tools')]
import preview,catalog,gen2_extended_review as review,interior_review
interior_review.WORKSPACE=W
from center_mart_overhang_review import write_rows
CACHE=Path('C:/Users/LSDMTHC/AppData/Roaming/pokemon-love2d');imp=interior_review.Imports(CACHE,W/'.work/tileshift-catalog');D=W/'.work/tileshift-firegold/crystaldust';dc=json.loads((D/'catalog.json').read_text());AS='assets/third_party/johto-hacks/crystaldust-special-rooms';AD=F/AS;AD.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
rgba=lambda im:hashlib.sha256(im.convert('RGBA').tobytes()).hexdigest()
digest=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
assets={};proof=[];images={}
def plane(n,ly):
 k=n,ly
 if k not in images:images[k]=Image.open(D/f'maps/{n}-{ly}.png').convert('RGBA')
 return images[k]
def save(tag,im,origin):
 assert im.size==(16,16)
 p=AD/f'{tag}.png';im.save(p)
 assets[tag]=dict(kind='third_party',asset=AS+'/'+p.name,assetFileHash=sha(p),assetPixelHash=rgba(im),credit='CrystalDust by Sierraffinity and contributors; exact native artwork from user-supplied ROM.',sourceUrl='https://github.com/Sierraffinity/CrystalDust')
 proof.append(dict(file=p.name,rgba_sha256=rgba(im),**origin));return assets[tag]
def cell(n,x,y,tag=None):
 tag=tag or f'{n}-{x}-{y}'
 if tag in assets:return assets[tag]
 m=next(m for m in dc['maps']if m['id']==n);box=(x*16,y*16,x*16+16,y*16+16)
 return save(tag,plane(n,'flat').crop(box),dict(map=n,pair=m['pair'],mid=m['grid'][y*m['width']+x]&1023,source_plane='flat',source_rect=[x*16,y*16,16,16],source_png_sha256=sha(D/f'maps/{n}-flat.png'),pixel_scale=1))
def feature(n,box,tag,open_door=False):
 im=plane(n,'flat').crop(box)
 origin=dict(map=n,source_rect=[box[0],box[1],box[2]-box[0],box[3]-box[1]],source_plane='flat',source_png_sha256=sha(D/f'maps/{n}-flat.png'),pixel_scale=1)
 if open_door:
  # This removes the native closed leaf (the complete16x16 UNDER metatile531)
  # and retains the complete unscaled native MID door arch and OVER lamp.
  under=plane(n,'under').crop(box);black=plane(n,'under').crop((0,0,16,16));assert len(set(black.getdata()))==1 and black.getpixel((0,0))==(0,0,0,255)
  under.paste(black,(96-box[0],32-box[1]));under.alpha_composite(plane(n,'mid').crop(box));under.alpha_composite(plane(n,'over').crop(box));im=under
  origin.update(source_plane='under+mid+over',removed_closed_leaf_rect=[96,32,16,16],replacement_native_black_mid=8,plane_hashes={ly:sha(D/f'maps/{n}-{ly}.png')for ly in ['under','mid','over']})
 assert im.size==(32,32)
 for q in range(4):save(f'{tag}-{q}',im.crop((q%2*16,q//2*16,q%2*16+16,q//2*16+16)),dict(origin,feature_name=tag,feature_rgba_sha256=rgba(im),feature_size=[32,32],feature_quadrant=q))
feature('g16_m000',(88,16,120,48),'e4-closed-door')
feature('g16_m000',(88,16,120,48),'e4-open-door',True)
feature('g16_m000',(88,64,120,96),'e4-complete-stair')
feature('g16_m004',(88,16,120,48),'champion-closed-door')
feature('g16_m004',(88,16,120,48),'champion-open-door',True)
# Native book-sized complete ruin statues are two source cells, no masked pixels.
for q in range(2):cell('g24_m084',2,3+q,f'ruin-statue-{q}')
modules=['johto_ruins_finish.lua','gen2_kanto_special_rooms_finish.lua','interiors.lua'];pool=[(fn,r)for fn in modules for r in preview.read_reviewed(S/'mappings'/fn)];supers=[];new=[];rows=[];chosen={}
def artrow(old,art,role,ev):
 r={k:copy.deepcopy(v)for k,v in old.items()if k.startswith('source')and k not in ['sourceColors']}
 for k in ['game','style','tileset','id','quadrant','map','x','y']:
  if k in old:r[k]=old[k]
 r.update(art,status='reviewed',role=role,evidence=ev)
 r['compositionPixelHash']=rgba(preview.replacement_image(CACHE,r,imp.packed,F));return r
EV='Reviewed actual CrystalDust room counterpart at native1:1pixels, complete modular architectural cell or complete object; source collision, scripts, puzzle interactions, warps and NPC positions are unchanged. Unique source Unown and puzzle-control geometry is retained where no complete native CrystalDust counterpart fits.'
rooms={'WILLS_ROOM':'g16_m000','KOGAS_ROOM':'g16_m001','BRUNOS_ROOM':'g16_m002','KARENS_ROOM':'g16_m003'}
for fn,old in pool:
 n=old.get('map','');role=old.get('role','');art=None;tag=None
 if fn=='johto_ruins_finish.lua'and n.startswith('RUINS_OF_ALPH_')and '_WORD_ROOM'not in n:
  if role=='johto_ruins_native_tanoby_stone_floor' or role=='johto_ruins_native_stone_below_complete_statue':art=cell('g24_m084',4,6);tag='ruins_native_crystaldust_floor'
  elif role=='johto_ruins_native_tanoby_stone_wall':art=cell('g24_m084',1,1);tag='ruins_native_crystaldust_brick'
  elif role=='johto_ruins_native_tanoby_stone_wall_cap':art=cell('g24_m084',2,0);tag='ruins_native_crystaldust_wall_cap'
  elif role=='johto_ruins_whole_pokemon_statue_head':art=assets['ruin-statue-0'];tag='ruins_complete_crystaldust_statue_head'
  elif role=='johto_ruins_whole_pokemon_statue_base':art=assets['ruin-statue-1'];tag='ruins_complete_crystaldust_statue_base'
 elif fn=='gen2_kanto_special_rooms_finish.lua'and n in rooms:
  bid,q=old['id'],old['quadrant'];cd=rooms[n]
  if bid==20:art=cell(cd,q%2,q//2);tag='elite_four_crystaldust_north_wall'
  elif bid==21:
   art=cell(cd,q%2,2 if q<2 else 3);tag='elite_four_crystaldust_wall_lower'if q<2 else'elite_four_crystaldust_passage_floor'
  elif bid==34:art=assets[f'e4-closed-door-{q}'];tag='elite_four_complete_crystaldust_closed_door'
  elif bid==1:art=assets[f'e4-complete-stair-{q}'];tag='elite_four_complete_crystaldust_stair'
  elif bid==52:art=cell(cd,q%2,3 if q<2 else 4);tag='elite_four_crystaldust_platform_header'
  elif bid==42:art=cell(cd,q%2,17 if q<2 else 18);tag='elite_four_crystaldust_closed_partition'
  elif n=='WILLS_ROOM' and bid==36:art=cell(cd,0,15);tag='elite_four_crystaldust_ice_basin'
  elif n=='WILLS_ROOM' and bid==31:art=cell(cd,4,12)if q<2 else cell(cd,0,15);tag='elite_four_crystaldust_ice_platform_edge'
  elif role in ['household_rug_left','household_rug_right']:
   tag=f'elite_four_crystaldust_floor_native_rug_{n.lower()}_{q}'
   bg=plane(cd,'flat').crop((96,240,112,256))
   for part in old['parts']:
    di=preview.native_donor(CACHE,part['donor'],imp.packed)
    bg.alpha_composite(di.crop((part['srcX'],part['srcY'],part['srcX']+part['w'],part['srcY']+part['h'])),(part['x'],part['y']))
   art=save(tag,bg,dict(map=cd,source_plane='flat',source_rect=[96,240,16,16],source_png_sha256=sha(D/f'maps/{cd}-flat.png'),complete_native_firered_rug_parts=old['parts'],pixel_scale=1))
   art['credit']='CrystalDust by Sierraffinity and contributors, native floor; Pokemon FireRed / Game Freak, complete native entrance rug. No resampling or color conversion.'
  elif role=='kanto_league_native_arena_floor':art=cell(cd,6,15);tag='elite_four_crystaldust_arena_floor'
 elif fn=='gen2_kanto_special_rooms_finish.lua'and n=='LANCES_ROOM':
  bid,q=old['id'],old['quadrant']
  if role=='kanto_champion_complete_original_red_carpet':art=cell('g16_m004',5 if q%2==0 else 7,12);tag='champion_crystaldust_complete_carpet_border'
  elif bid==46:art=assets[f'champion-closed-door-{q}'];tag='champion_complete_crystaldust_closed_door'
 if art is not None:
  r=artrow(old,art,tag,EV)
  if rgba(preview.replacement_image(CACHE,old,imp.packed,S))==r['compositionPixelHash']:continue
  supers.append(dict(module=fn,original_row=old,original_row_sha256=digest(old),candidate_row=r));rows.append(r);chosen[old['game'],n,bid if n in rooms or n=='LANCES_ROOM' else old['id'],old['quadrant'],old.get('x'),old.get('y')]=r
# Reachable callback states have map scope and no positioned x/y so bare-layout
# warming cannot memoize an absent runtime cell. Unchanged quads retain exact
# same-source-cell art. New floor/open passage states use functional native CD parts.
data={g:review.source(CACHE,g)for g in ['gold','silver','crystal']};ledger=json.loads((O.parent/'interiors/runtime-missing-root.json').read_text())
for item in ledger['keys']:
 g,n,bid,q=item['game'],item['map'],item['id'],item['quadrant'];ci=review.cell_info(CACHE,g,data[g],item['tileset'],bid,q);same=[(fn,r)for fn,r in pool if r['game']==g and r.get('map')==n and r['sourceHash']==ci['sourceHash']and r.get('sourceCollision')==ci['collision']]
 if same:
  fn,old=same[0];r=copy.deepcopy(chosen.get((g,n,old['id'],old['quadrant'],old.get('x'),old.get('y')),old));r.pop('x',None);r.pop('y',None)
 else:
  old=dict(game=g,style='gen3',map=n,tileset=item['tileset'],id=bid,quadrant=q,sourceHash=ci['sourceHash'],sourceFiles=data[g]['fingerprints'][item['tileset']],sourceCollision=ci['collision'],sourcePriority=[bool(a.get('priority'))for a in ci['attributes']],sourcePalettes=[a.get('palette',1)for a in ci['attributes']])
  if n.startswith('RUINS_'):
   assert(bid,q)in[(1,3),(2,2),(46,0)]
   art=cell('g24_m084',1,1)if bid==46 else cell('g24_m084',4,6)
  elif n in rooms:
   assert bid==22 and q<2
   art=cell(rooms[n],q%2,3)
  elif n=='LANCES_ROOM':
   assert bid==11
   if g=='crystal':art=assets[f'champion-open-door-{q}']
   else:art=cell('g16_m004',4+q%2,5)if q<2 else cell('g16_m004',5 if q%2==0 else 7,12)
  else:raise AssertionError(item)
  r=artrow(old,art,'crystaldust_reachable_special_room_state',EV)
 r.update(id=bid,quadrant=q,sourceHash=ci['sourceHash'],sourceFiles=data[g]['fingerprints'][item['tileset']],sourceCollision=ci['collision'],sourcePriority=[bool(a.get('priority'))for a in ci['attributes']],sourcePalettes=[a.get('palette',1)for a in ci['attributes']],sourceCells=[[a['x'],a['y']]for a in item['witnesses']],evidence=EV+' Runtime source witness: '+json.dumps(item['witnesses'],separators=(',',':')))
 # Re-evaluate composed hash after binding exact new source key.
 r['compositionPixelHash']=rgba(preview.replacement_image(CACHE,r,imp.packed,F if r.get('asset','').startswith(AS)else S));new.append(r);rows.append(r)
assert len(new)==176
(F/'mappings').mkdir(parents=True,exist_ok=True);write_rows(F/'mappings/crystaldust_special_runtime.lua',new)
(O/'supersessions.json').write_text(json.dumps(supers,indent=2)+'\n');(O/'rows.json').write_text(json.dumps(rows,indent=2)+'\n')
used={Path(r['asset']).name for r in rows if r.get('asset','').startswith(AS)}
(AD/'provenance.json').write_text(json.dumps(dict(source='Native CrystalDust Ruins of Alph, Elite Four and Champion room modular counterparts',rom_sha256=dc['rom_sha256'],catalog_sha256=sha(D/'catalog.json'),pixel_scale=1,no_resampling_or_color_conversion=True,recipes=[r for r in proof if r['file']in used],files={p.name:sha(p)for p in AD.glob('*.png')if p.name in used}),indent=2)+'\n')
for n in ['mapping.lua','session.lua','donor.lua','composition.lua']:
 p=F/'lib'/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(S/'lib'/n,p)
# Private validation root also needs existing referenced assets for alias quads.
for r in rows:
 if r.get('asset')and not r['asset'].startswith(AS):
  p=F/r['asset'];p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(S/r['asset'],p)
result=review.validate_batch(rows,SimpleNamespace(cache=CACHE,engine=W/'.work/tileshift-engine-0410',output=O),F);(O/'neutral-proof.json').write_text(json.dumps(result,indent=2)+'\n')
manifest=dict(status='reviewable_candidate',mapping_stem='crystaldust_special_runtime',candidate=str(F/'mappings/crystaldust_special_runtime.lua'),new_rows=len(new),supersessions=str(O/'supersessions.json'),superseded_rows=len(supers),all_rows=len(rows),assets=[dict(source=str(p),target=AS+'/'+p.name,sha256=sha(p))for p in AD.iterdir()if p.name in used or p.name=='provenance.json'],tools=[dict(source=str(Path(__file__).resolve()),target='tools/author_crystaldust_special_sweep.py',sha256=sha(__file__))],neutral=result)
(O/'integration.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(dict(rows=len(rows),supersessions=len(supers),new=len(new),neutral=result)))
