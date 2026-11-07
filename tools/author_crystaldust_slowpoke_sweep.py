from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import hashlib,json,sys,copy,re,shutil
from types import SimpleNamespace
W=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent;F=W/'.work/tileshift-v0445-checkpoint/frozen.json';f=json.loads(F.read_text());ROOT=Path(f['stage']);sys.path[:0]=[str(W/'.tools/python'),str(ROOT/'tools')]
import catalog,preview,gen2_extended_review as neutral
import interior_review;interior_review.WORKSPACE=W
from interior_review import Imports
from center_mart_overhang_review import write_rows
CACHE=Path('C:/Users/LSDMTHC/AppData/Roaming/pokemon-love2d');imp=Imports(CACHE,W/'.work/tileshift-catalog');ASSET='assets/third_party/johto-hacks/crystaldust-slowpoke';ad=OUT/'files'/ASSET;ad.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();rgba=lambda im:hashlib.sha256(im.convert('RGBA').tobytes()).hexdigest();digest=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
source=W/'.work/tileshift-firegold/crystaldust';cd=json.loads((source/'catalog.json').read_text());m=next(m for m in cd['maps']if m['id']=='g00_m011');dest=next(m for m in cd['maps']if m['id']=='g24_m004');assert m['warps'][6]==dict(x=37,y=10,elevation=0,dest_warp=0,dest_num=4,dest_group=24);assert dest['region']==60 and dest['warps'][0]['dest_group']==0 and dest['warps'][0]['dest_num']==11 and dest['warps'][0]['dest_warp']==6
ids=[[m['grid'][(8+y)*m['width']+36+x]&1023 for x in range(3)]for y in range(3)];assert ids==[[555,556,557],[563,564,565],[571,572,573]]
sp=source/'maps/g00_m011-mid.png';whole=Image.open(sp).convert('RGBA').crop((576,128,624,176));assert whole.size==(48,48);assert Image.open(source/'maps/g00_m011-over.png').crop((576,128,624,176)).getbbox()is None
whole.save(ad/'whole48.png');assets={};files={'whole48.png':sha(ad/'whole48.png')}
for y in range(3):
 for x in range(3):
  im=whole.crop((x*16,y*16,x*16+16,y*16+16));p=ad/f'cell-{x}-{y}.png';im.save(p);files[p.name]=sha(p);assets[x,y]=dict(kind='third_party',asset=ASSET+'/'+p.name,assetFileHash=sha(p),assetPixelHash=rgba(im),credit='CrystalDust by Sierraffinity and contributors; exact native artwork from user-supplied ROM.',sourceUrl='https://github.com/Sierraffinity/CrystalDust')
inv=json.loads((OUT.parent/'selected-outdoors.json').read_text());allrows=inv['selected_rows'];selected={}
for game in ('gold','silver','crystal'):
 sourceMap=imp.table(game,'maps')['AZALEA_TOWN'];generic={};pos={}
 for item in allrows:
  r=item['row']
  if r['game']==game and r['tileset']==sourceMap['tileset']and r.get('map','AZALEA_TOWN')=='AZALEA_TOWN':
   if r.get('x')is None:generic[r['id'],r['quadrant']]=item
   else:pos[r['id'],r['quadrant'],r['x'],r['y']]=item
 for i,bid in enumerate(sourceMap['blocks']):
  for q in range(4):
   x=i%sourceMap['width']*2+q%2;y=i//sourceMap['width']*2+q//2;item=pos.get((bid,q,x,y),generic.get((bid,q)));assert item;(selected.setdefault(game,{}))[x,y]=item
rows=[];new=[];supers=[];sourceproof=[]
for game in ('gold','silver','crystal'):
 mp=imp.table(game,'maps')['AZALEA_TOWN'];assert any(w['destMap']=='SLOWPOKE_WELL_B1F'and w['x']==31 and w['y']==7 for w in mp['warps']);sourceproof.append(dict(game=game,map='AZALEA_TOWN',map_sha256=digest(mp),warps=mp['warps']))
 for y in range(5,9):
  for x in range(30,33):
   old=selected[game][x,y]['row'];r={k:copy.deepcopy(v)for k,v in old.items()if k.startswith('source')and k not in('sourceColors','sourceCells')};r.update(game=game,style='gen3',map='AZALEA_TOWN',tileset=mp['tileset'],id=old['id'],quadrant=old['quadrant'],x=x,y=y,sourceCells=[[x,y]],status='reviewed',role='crystaldust_slowpoke_well_whole_mound',evidence='Exact functional Slowpoke Well entrance counterpart from supplied CrystalDust Azalea, unscaled complete48x48MIDplane. CD warp37,10 leads to its SLOWPOKEWELL room; source warp31,7 remains SLOWPOKE_WELL_B1F. Entire native image moves up16pixels to align entrance; former generated step row returns to selected ground. Native source collision/scripts/NPCs/warps remain byte-identical.')
   if y<8:
    base=copy.deepcopy(old.get('base')or old.get('donor'));assert base and base['id']==1
    r.update(base=base,**assets[x-30,y-5])
   else:r.update(kind='native',donor=copy.deepcopy(old['base']))
   r['compositionPixelHash']=rgba(preview.replacement_image(CACHE,r,imp.packed,OUT/'files'));rows.append(r)
   if old.get('x')==x and old.get('y')==y:supers.append(dict(module=selected[game][x,y]['module'],original_row=old,original_row_sha256=digest(old),candidate_row=r))
   else:new.append(r)
assert len(rows)==36 and len(new)==9 and len(supers)==27
(OUT/'files/mappings').mkdir(parents=True,exist_ok=True)
write_rows(OUT/'files/mappings/crystaldust_slowpoke_sweep.lua',new)
(OUT/'rows.json').write_text(json.dumps(rows,indent=2)+'\n');(OUT/'supersessions.json').write_text(json.dumps(supers,indent=2)+'\n')
provenance=dict(source='Native CrystalDust Slowpoke Well functional entrance',rom_sha256=cd['rom_sha256'],catalog_sha256=sha(source/'catalog.json'),source_map='g00_m011',source_pair=m['pair'],source_mids=ids,source_plane='mid',source_png=str(sp),source_png_sha256=sha(sp),source_rect=[576,128,48,48],native_size=[48,48],source_entrance=[37,10],source_destination=dict(map='g24_m004',region_name='SLOWPOKE WELL',return_warp=dest['warps'][0]),target_origin=[30,5],target_entrance=[31,7],restored_ground_row=8,source_target_maps=sourceproof,pixel_scale=1,no_mask_or_color_conversion=True,rgba_sha256=rgba(whole),files=files)
(ad/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
for n in ('mapping.lua','session.lua','donor.lua','composition.lua'):
 p=OUT/'files/lib'/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'lib'/n,p)
result=neutral.validate_batch(rows,SimpleNamespace(cache=CACHE,engine=W/'.work/tileshift-engine-0400',output=OUT),OUT/'files');(OUT/'neutral-proof.json').write_text(json.dumps(result,indent=2)+'\n')
# Review actual whole map; ordinary image layers only, actors/native cap renderer are separate.
preview_rows={(r['game'],r['x'],r['y']):r for r in rows};imcache={}
for game in ('crystal',):
 mp=imp.table(game,'maps')['AZALEA_TOWN'];before=Image.new('RGBA',(mp['width']*32,mp['height']*32));after=before.copy()
 for(x,y),item in selected[game].items():
  old=item['row'];key=item['module'],item['index']
  if key not in imcache:imcache[key]=preview.replacement_image(CACHE,old,imp.packed,ROOT)
  a=imcache[key];r=preview_rows.get((game,x,y));b=preview.replacement_image(CACHE,r,imp.packed,OUT/'files')if r else a;before.alpha_composite(a,(x*16,y*16));after.alpha_composite(b,(x*16,y*16))
 before.save(OUT/'crystal-AZALEA-before.png');after.save(OUT/'crystal-AZALEA-after.png');font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17);board=Image.new('RGB',(before.width*2+36,before.height+55),'#18222d');dr=ImageDraw.Draw(board);dr.text((12,8),'Current published artwork',font=font,fill='white');dr.text((before.width+24,8),'Complete native CrystalDust entrance',font=font,fill='white');board.paste(before,(12,40));board.paste(after,(before.width+24,40));board.save(OUT/'Azalea-whole-map-review.png')
manifest=dict(status='reviewable_candidate',mapping_stem='crystaldust_slowpoke_sweep',candidate=str(OUT/'files/mappings/crystaldust_slowpoke_sweep.lua'),new_rows=9,supersessions=str(OUT/'supersessions.json'),superseded_rows=27,all_rows=36,assets=[dict(source=str(p),target=ASSET+'/'+p.name,sha256=sha(p))for p in sorted(ad.iterdir())],tools=[dict(source=str(Path(__file__).resolve()),target='tools/author_crystaldust_slowpoke_sweep.py',sha256=sha(Path(__file__)))],neutral=result,whole_scene_review=str(OUT/'Azalea-whole-map-review.png'))
(OUT/'integration.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(dict(rows=36,new_rows=9,supersessions=27,neutral=result,integration_sha256=sha(OUT/'integration.json'))))
