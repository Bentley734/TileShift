from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from types import SimpleNamespace
import json,sys,hashlib,copy,re,shutil
W=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent;f=json.loads((W/'.work/tileshift-v0445-checkpoint/frozen.json').read_text());ROOT=Path(f['stage']);sys.path[:0]=[str(W/'.tools/python'),str(ROOT/'tools')]
import catalog,preview,gen2_extended_review as neutral
import interior_review;interior_review.WORKSPACE=W
from interior_review import Imports
CACHE=Path('C:/Users/LSDMTHC/AppData/Roaming/pokemon-love2d');imp=Imports(CACHE,W/'.work/tileshift-catalog');ASSET='assets/third_party/johto-hacks/crystaldust-goldenrod-closed';ad=OUT/'files'/ASSET;ad.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();rgba=lambda im:hashlib.sha256(im.convert('RGBA').tobytes()).hexdigest();digest=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
source=W/'.work/tileshift-firegold/crystaldust';cd=json.loads((source/'catalog.json').read_text());m=next(m for m in cd['maps']if m['id']=='g00_m003');assert m['region']==10
specs={'closed32':(32,1,2,3),'closed64':(28,1,4,3)};assets={};proofs={};files={}
for name,(x,y,w,h)in specs.items():
 whole=Image.new('RGBA',(w*16,h*16));planes={}
 for plane in('mid','over'):
  p=source/'maps'/f'g00_m003-{plane}.png';part=Image.open(p).convert('RGBA').crop((x*16,y*16,(x+w)*16,(y+h)*16));whole.alpha_composite(part);planes[plane]=dict(png=str(p),sha256=sha(p),crop=[x*16,y*16,w*16,h*16])
 ids=[[m['grid'][(y+dy)*m['width']+x+dx]&1023 for dx in range(w)]for dy in range(h)]
 flat=Image.open(source/'maps/g00_m003-flat.png').convert('RGBA').crop((x*16,y*16,(x+w)*16,(y+h)*16))
 for a,b in zip(whole.get_flattened_data(),flat.get_flattened_data()):
  if a[3]:assert a==b
 p=ad/(name+'-whole.png');whole.save(p);files[p.name]=sha(p);proofs[name]=dict(map='g00_m003',source_rect=[x*16,y*16,w*16,h*16],mids=ids,pair=m['pair'],planes=planes,native_size=list(whole.size),rgba_sha256=rgba(whole),entrance='none; same complete native closed-apartment function',all_opaque_source_pixels_unchanged=True)
 for cy in range(h):
  for cx in range(w):
   im=whole.crop((cx*16,cy*16,cx*16+16,cy*16+16));p=ad/(name+f'-{cx}-{cy}.png');im.save(p);files[p.name]=sha(p);assets[name,cx,cy]=dict(kind='third_party',asset=ASSET+'/'+p.name,assetFileHash=sha(p),assetPixelHash=rgba(im),credit='CrystalDust by Sierraffinity and contributors; user-supplied native ROM artwork.',sourceUrl='https://github.com/Sierraffinity/CrystalDust')
# Exact native architecture modules preserve complete window bays/cornercaps.
source64=Image.open(ad/'closed64-whole.png').convert('RGBA')
closed48=Image.new('RGBA',(48,48));closed48.alpha_composite(source64.crop((0,0,24,48)),(0,0));closed48.alpha_composite(source64.crop((40,0,64,48)),(24,0))
tall=Image.new('RGBA',(64,80));tall.alpha_composite(source64.crop((0,0,64,32)),(0,0))
for dy in(32,48,64):tall.alpha_composite(source64.crop((0,32,64,48)),(0,dy))
for name,whole,parts in [('closed48',closed48,[dict(source_rect=[0,0,24,48],destination=[0,0]),dict(source_rect=[40,0,24,48],destination=[24,0])]),('closed_tall',tall,[dict(source_rect=[0,0,64,32],destination=[0,0])]+[dict(source_rect=[0,32,64,16],destination=[0,y])for y in(32,48,64)])]:
 p=ad/(name+'-whole.png');whole.save(p);files[p.name]=sha(p);proofs[name]=dict(native_source=proofs['closed64'],native_size=list(whole.size),complete_modules=parts,rgba_sha256=rgba(whole),assembly='Complete native window bays andcornercaps retained; optionalcentral shutter bay omitted for48px facade. Whole facade story repeated below one full roof for tall apartment.',pixel_scale=1,no_unique_window_cropped=True)
 for cy in range(whole.height//16):
  for cx in range(whole.width//16):
   im=whole.crop((cx*16,cy*16,cx*16+16,cy*16+16));p=ad/(name+f'-{cx}-{cy}.png');im.save(p);files[p.name]=sha(p);assets[name,cx,cy]=dict(kind='third_party',asset=ASSET+'/'+p.name,assetFileHash=sha(p),assetPixelHash=rgba(im),credit='CrystalDust by Sierraffinity and contributors; complete native architecture modules.',sourceUrl='https://github.com/Sierraffinity/CrystalDust')
inv=json.loads((OUT.parent/'selected-outdoors.json').read_text());chosen=[r for r in inv['selected_rows']if r['row']['role']in('goldenrod_native_closed32','goldenrod_native_closed64','goldenrod_native_closed48','goldenrod_native_closed_tall')];rows=[];supers=[]
for item in chosen:
 old=item['row'];name=old['role'].removeprefix('goldenrod_native_');match=re.search(r'cell-(\d+)-(\d+)\.png$',old['asset']);assert match;cx,cy=map(int,match.groups());r=copy.deepcopy(old);r.update(assets[name,cx,cy]);r.pop('artOverlay',None);r['evidence']='Complete corresponding closed-apartment artwork from the actual CrystalDust Goldenrod map, whole native32/64px apartments and complete native48px/tall module adaptations; both whole roof and whole facade retain original scale and source transparency. Decorative roof strip is replaced together with itsbody, not mixed with the previous artist version. Original source collision/layout/scripts/warps/actors stay unchanged.';r['compositionPixelHash']=rgba(preview.replacement_image(CACHE,r,imp.packed,OUT/'files'));rows.append(r);supers.append(dict(module=item['module'],original_row=old,original_row_sha256=digest(old),candidate_row=r))
roofs=preview.read_reviewed(ROOT/'lib/goldenrod_roofs.lua');roofsupers=[];newroof=[]
for i,old in enumerate(roofs):
 if old['role']not in('goldenrod_native_closed32','goldenrod_native_closed64','goldenrod_native_closed48','goldenrod_native_closed_tall'):newroof.append(old);continue
 name=old['role'].removeprefix('goldenrod_native_');match=re.search(r'cell-(\d+)-(\d+)\.png$',old['asset']);assert match;cx,cy=map(int,match.groups());r=copy.deepcopy(old);r.update(assets[name,cx,cy]);r['evidence']='Exact native CrystalDust roof continuation belonging to the same complete closed-apartment facade below. Whole pixels remain1:1; source positions and roof anchor conditions retained.';r.pop('compositionPixelHash',None);newroof.append(r);roofsupers.append(dict(module='lib/goldenrod_roofs.lua',index=i,original_row=old,original_row_sha256=digest(old),candidate_row=r))
(ad/'provenance.json').write_text(json.dumps(dict(source='CrystalDust native Goldenrod closed apartment families',rom_sha256=cd['rom_sha256'],catalog_sha256=sha(source/'catalog.json'),objects=proofs,files=files,pixel_scale=1,no_scaling_masking_or_redraw=True,complete_native_module_adaptations=True),indent=2)+'\n')
(OUT/'rows.json').write_text(json.dumps(rows,indent=2)+'\n');(OUT/'supersessions.json').write_text(json.dumps(supers+roofsupers,indent=2)+'\n');(OUT/'roof-rows.json').write_text(json.dumps([r['candidate_row']for r in roofsupers],indent=2)+'\n')
for name in('mapping.lua','session.lua','donor.lua','composition.lua'):
 p=OUT/'files/lib'/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'lib'/name,p)
result=neutral.validate_batch(rows,SimpleNamespace(cache=CACHE,engine=W/'.work/tileshift-engine-0400',output=OUT),OUT/'files');(OUT/'neutral-proof.json').write_text(json.dumps(result,indent=2)+'\n')
# Complete map review includes existing decorative architecture overlays.
game='crystal';mp=imp.table(game,'maps')['GOLDENROD_CITY'];generic={};positions={}
for item in inv['selected_rows']:
 r=item['row']
 if r['game']==game and r['tileset']==mp['tileset']and r.get('map','GOLDENROD_CITY')=='GOLDENROD_CITY':
  if r.get('x')is None:generic[r['id'],r['quadrant']]=item
  else:positions[r['id'],r['quadrant'],r['x'],r['y']]=item
changes={(r['game'],r['id'],r['quadrant'],r.get('map'),r.get('x'),r.get('y')):r for r in rows};before=Image.new('RGBA',(mp['width']*32,mp['height']*32));after=before.copy();cache={}
for i,bid in enumerate(mp['blocks']):
 for q in range(4):
  x=i%mp['width']*2+q%2;y=i//mp['width']*2+q//2;item=positions.get((bid,q,x,y),generic.get((bid,q)));assert item;(path,index,r)=(item['module'],item['index'],item['row']);key=path,index
  if key not in cache:cache[key]=preview.replacement_image(CACHE,r,imp.packed,ROOT)
  im=cache[key];new=changes.get((game,bid,q,r.get('map'),r.get('x'),r.get('y')));before.alpha_composite(im,(x*16,y*16));after.alpha_composite(preview.replacement_image(CACHE,new,imp.packed,OUT/'files')if new else im,(x*16,y*16))
for canvas,rs,mod in[(before,roofs,ROOT),(after,newroof,OUT/'files')]:
 for r in rs:
  if r['game']!=game or r.get('map')!='GOLDENROD_CITY':continue
  p=mod/r['asset']
  if not p.exists():p=ROOT/r['asset']
  canvas.alpha_composite(Image.open(p).convert('RGBA'),(r['x']*16,r['y']*16))
before.save(OUT/'crystal-GOLDENROD-before.png');after.save(OUT/'crystal-GOLDENROD-after.png');board=Image.new('RGB',(before.width*2+36,before.height+55),'#18222d');dr=ImageDraw.Draw(board);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17);dr.text((12,8),'Current native public-artist closedhouses',font=font,fill='white');dr.text((before.width+24,8),'Actual CrystalDust complete closedhouses',font=font,fill='white');board.paste(before,(12,40));board.paste(after,(before.width+24,40));board.save(OUT/'Goldenrod-whole-map-review.png')
manifest=dict(status='reviewable_candidate',supersessions=str(OUT/'supersessions.json'),mapping_rows=len(rows),roof_rows=len(roofsupers),assets=[dict(source=str(p),target=ASSET+'/'+p.name,sha256=sha(p))for p in sorted(ad.iterdir())],tools=[dict(source=str(Path(__file__).resolve()),target='tools/author_crystaldust_goldenrod_closed.py',sha256=sha(Path(__file__)))],neutral=result,whole_scene_review=str(OUT/'Goldenrod-whole-map-review.png'))
(OUT/'integration.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(dict(mapping=len(rows),roofs=len(roofsupers),neutral=result,integration_sha256=sha(OUT/'integration.json'))))
