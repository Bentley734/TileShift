from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from types import SimpleNamespace
import copy,hashlib,json,shutil,sys
W=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent;ROOT=Path(json.loads((W/'.work/tileshift-v0445-checkpoint/frozen.json').read_text())['stage']);sys.path[:0]=[str(W/'.tools/python'),str(ROOT/'tools')]
import preview,gen2_extended_review as neutral
import interior_review;interior_review.WORKSPACE=W
from interior_review import Imports
CACHE=Path('C:/Users/LSDMTHC/AppData/Roaming/pokemon-love2d');imp=Imports(CACHE,W/'.work/tileshift-catalog')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();rgba=lambda im:hashlib.sha256(im.convert('RGBA').tobytes()).hexdigest();digest=lambda r:hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':')).encode()).hexdigest()
ASSET='assets/third_party/johto-hacks/crystaldust-moomoo-farm';ad=OUT/'files'/ASSET;ad.mkdir(parents=True,exist_ok=True);src=W/'.work/tileshift-firegold/crystaldust';flat=src/'maps/g00_m026-flat.png';im=Image.open(flat).convert('RGBA')
cd=json.loads((src/'catalog.json').read_text());maps={m['id']:m for m in cd['maps']};m=maps['g00_m026'];assert m['warps'][0]==dict(x=3,y=5,elevation=0,dest_warp=0,dest_num=1,dest_group=18);assert m['warps'][1]==dict(x=7,y=5,elevation=0,dest_warp=0,dest_num=0,dest_group=18)
barn=im.crop((32,48,96,96));removed=[]
# Above the left hip is a separate source fence; the native roof starts x14.
# At upper-right only the literal ochre/green exterior ground is transparent.
exterior={(214,197,132),(173,222,165),(230,222,165),(115,206,165),(197,173,107),(173,148,74)}
for y in range(16):
 for x in range(64):
  if x<14 or barn.getpixel((x,y))[:3]in exterior:barn.putpixel((x,y),(0,0,0,0));removed.append([x,y])
farm_native=im.crop((96,48,160,96));farm=Image.new('RGBA',(64,64));farm.alpha_composite(farm_native.crop((0,0,64,16)),(0,0));farm.alpha_composite(farm_native,(0,16))
art={'barn':barn,'farmhouse':farm};wholefiles={}
for name,a in art.items():
 p=ad/(name+'-whole.png');a.save(p);wholefiles[name]=p
 for y in range(a.height//16):
  for x in range(4):a.crop((x*16,y*16,x*16+16,y*16+16)).save(ad/f'{name}-{x}-{y}.png')
pool=json.loads((W/'.work/tileshift-crystaldust-sweep/audit/selected-row-pool.json').read_text())['rows'];supers=[];body=[];roofs=[]
credit='CrystalDust by Sierraffinity and contributors; actual native Moomoo Farm exterior artwork.'
evidence='Actual CrystalDust Route39 functional counterpart: blue barn doorway3,5 leads to Miltank barn g18_m001; orange farmhouse doorway7,5 leads to domestic g18_m000. Native whole windows, doors and eaves stay at1:1 pixel size. Only one complete plain16px orange roof module repeats for the taller original farmhouse. The barn uses its complete64x48 native geometry including the already-supported decorative upper row. Original GSC entrances, sourceblocks, collision, scripts and actors stay unchanged.'
def make(old,name,x,y,isroof=False):
 r={k:copy.deepcopy(v)for k,v in old.items()if k.startswith('source')and k not in('sourceUrl',)}
 for k in ['game','style','map','tileset','id','quadrant','x','y','buildingY']:
  if k in old:r[k]=old[k]
 p=ad/f'{name}-{x}-{y}.png';r.update(kind='third_party',asset=ASSET+'/'+p.name,assetFileHash=sha(p),assetPixelHash=rgba(Image.open(p)),credit=credit,sourceUrl='https://github.com/Sierraffinity/CrystalDust',role='crystaldust_moomoo_'+name+('_roof'if isroof else''),status='reviewed',evidence=evidence)
 if not isroof:r['base']=copy.deepcopy(old['base']);r['compositionPixelHash']=rgba(preview.replacement_image(CACHE,r,imp.packed,OUT/'files'))
 return r
for v in pool:
 old=v['row'];role=old.get('role')
 if role not in ['johto_moomoo_farmhouse','johto_moomoo_barn']:continue
 name='farmhouse'if role.endswith('farmhouse')else'barn';x=old['x']-(4 if name=='farmhouse'else 0);y=old['y']-(0 if name=='farmhouse'else 1);r=make(old,name,x,y);body.append(r);supers.append(dict(module=v['module'],original_row=old,original_row_sha256=v['semantic_sha256'],candidate_row=r))
for old in preview.read_reviewed(ROOT/'lib/johto_roofs.lua'):
 if old.get('role')!='moomoo_barn_roof':continue
 r=make(old,'barn',old['x'],0,True);roofs.append(r);supers.append(dict(module='lib/johto_roofs.lua',original_row=old,original_row_sha256=digest(old),candidate_row=r))
assert len(body)==72 and len(roofs)==12
(OUT/'supersessions.json').write_text(json.dumps(supers,indent=2)+'\n');(OUT/'body-rows.json').write_text(json.dumps(body,indent=2)+'\n');(OUT/'roof-rows.json').write_text(json.dumps(roofs,indent=2)+'\n')
provenance=dict(origin='Actual supplied CrystalDust Moomoo Farm, Route39. All opaque building pixels native1:1. Whole64x48 barn; whole64x48 farmhouse plus one complete plain16px roof stripe module for64x64 destination.',rom_sha256='51196cba923c315d0088b747b5cdee704f2ac057cd493f9ddf226fb7227302cf',source_map='g00_m026',source_pair=m['pair'],source_png_sha256=sha(flat),source_crops=dict(barn=[32,48,64,48],farmhouse=[96,48,64,48]),source_warps=m['warps'],source_destination_return_warps={s:maps[s]['warps']for s in ['g18_m000','g18_m001']},source_destination_native_contexts='g18_m001 is native Miltank pen; g18_m000 is native domestic kitchen/dining room, personally inspected.',barn_omitted_exterior_coordinates=removed,farmhouse_native_modules=[dict(source_rect=[0,0,64,16],placement=[0,0]),dict(source_rect=[0,0,64,48],placement=[0,16])],files={p.name:sha(p)for p in sorted(ad.glob('*.png'))})
(ad/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
lib=OUT/'files/lib';lib.mkdir(parents=True,exist_ok=True)
for n in ['mapping.lua','session.lua','donor.lua','composition.lua']:shutil.copyfile(ROOT/'lib'/n,lib/n)
result=neutral.validate_batch(body,SimpleNamespace(cache=CACHE,engine=W/'.work/tileshift-engine-0400',output=OUT),OUT/'files');(OUT/'neutral-proof.json').write_text(json.dumps(result,indent=2)+'\n')
area=json.loads((W/'.work/tileshift-crystaldust-sweep/audit/areas/crystal/ROUTE_39.json').read_text());lookup={v['row_id']:v['row']for v in pool};mp=imp.table('crystal','maps')['ROUTE_39'];before=Image.new('RGBA',(mp['width']*32,mp['height']*32));after=before.copy();new={(r['x'],r['y']):r for r in body if r['game']=='crystal'}
assert any(w['x']==1 and w['y']==3 and w['destMap']=='ROUTE_39_BARN'for w in mp['warps']);assert any(w['x']==5 and w['y']==3 and w['destMap']=='ROUTE_39_FARMHOUSE'for w in mp['warps'])
for x,y,bid,q,rid in area['selected_cells']:
 r=lookup[rid];a=preview.replacement_image(CACHE,r,imp.packed,ROOT);before.alpha_composite(a,(x*16,y*16));after.alpha_composite(preview.replacement_image(CACHE,new[x,y],imp.packed,OUT/'files')if(x,y)in new else a,(x*16,y*16))
oldroof=[r for r in preview.read_reviewed(ROOT/'lib/johto_roofs.lua')if r.get('role')=='moomoo_barn_roof'and r['game']=='crystal']
for r in oldroof:before.alpha_composite(preview.replacement_image(CACHE,r,imp.packed,ROOT),(r['x']*16,r['y']*16))
for r in roofs:
 if r['game']=='crystal':after.alpha_composite(Image.open(OUT/'files'/r['asset']).convert('RGBA'),(r['x']*16,r['y']*16))
before.save(OUT/'Route39-before.png');after.save(OUT/'Route39-after.png');font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17);board=Image.new('RGB',(before.width*2+36,before.height+55),'#18222d');d=ImageDraw.Draw(board);d.text((12,8),'Current Gen3 farm buildings',font=font,fill='white');d.text((before.width+24,8),'Actual CrystalDust Moomoo Farm',font=font,fill='white');board.paste(before,(12,40));board.paste(after,(before.width+24,40));board.save(OUT/'Moomoo-Farm-whole-map-review.png')
manifest=dict(status='ready_private_candidate',supersessions=str(OUT/'supersessions.json'),superseded_body_rows=72,superseded_roof_rows=12,new_rows=0,assets=[dict(source=str(p),target=ASSET+'/'+p.name,sha256=sha(p))for p in sorted(ad.iterdir())],tools=[dict(source=str(Path(__file__).resolve()),target='tools/author_crystaldust_moomoo_farm.py',sha256=sha(Path(__file__)))],neutral=result,whole_scene_preview=str(OUT/'Moomoo-Farm-whole-map-review.png'))
(OUT/'integration.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(dict(body=len(body),roofs=len(roofs),neutral=result,integration_sha256=sha(OUT/'integration.json'))))
