from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from types import SimpleNamespace
import copy, hashlib, json, shutil, sys
W=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
ROOT=Path(json.loads((W/'.work/tileshift-v0445-checkpoint/frozen.json').read_text())['stage'])
sys.path[:0]=[str(W/'.tools/python'),str(ROOT/'tools')]
import preview, gen2_extended_review as neutral
from center_mart_overhang_review import write_rows
import interior_review;interior_review.WORKSPACE=W
from interior_review import Imports
CACHE=Path('C:/Users/LSDMTHC/AppData/Roaming/pokemon-love2d');imp=Imports(CACHE,W/'.work/tileshift-catalog')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
rgba=lambda im:hashlib.sha256(im.convert('RGBA').tobytes()).hexdigest()
ASSET='assets/third_party/johto-hacks/crystaldust-route19-rockfall';ad=OUT/'files'/ASSET;ad.mkdir(parents=True,exist_ok=True)
source=W/'.work/tileshift-firegold/crystaldust';atlas=source/'pairs/083df704_083df794/mid.png'
rock=Image.open(atlas).convert('RGBA').crop((32,512,48,528))
assert rgba(rock)=='e3baee7ad5d6d1f729d164959bdad917435c89e3af15195271a1b71971d72160'
rock.save(ad/'rock16.png');whole=Image.new('RGBA',(32,32))
for y in range(2):
 for x in range(2):whole.alpha_composite(rock,(x*16,y*16))
whole.save(ad/'rubble32.png')
pool=json.loads((W/'.work/tileshift-crystaldust-sweep/audit/selected-row-pool.json').read_text())['rows']
keys=[v for v in json.loads((OUT.parent/'field-states/alias-inventory.json').read_text())['keys']if v['map']=='ROUTE_19'];assert len(keys)==12
rows=[];proof=[]
for k in keys:
 game=k['game'];c=k['source'];a=next(v['row']for v in pool if v['row']['game']==game and v['row'].get('map')=='ROUTE_19'and v['row']['id']==26 and v['row']['quadrant']==0)
 r=dict(game=game,style='gen3',map='ROUTE_19',tileset='TILESET_KANTO',id=122,quadrant=k['quadrant'],kind='third_party',asset=ASSET+'/rock16.png',assetFileHash=sha(ad/'rock16.png'),assetPixelHash=rgba(rock),base=copy.deepcopy(a['donor']),sourceHash=c['sourceHash'],sourceCollision=c['collision'],sourcePriority=[bool(v.get('priority'))for v in c['attributes']],sourcePalettes=[v.get('palette',1)for v in c['attributes']],sourceFiles=k['sourceFiles'],sourceCells={},status='reviewed',role='crystaldust_route19_scripted_rockfall',credit='CrystalDust by Sierraffinity and contributors; complete native16px boulder repeated without scaling.',sourceUrl='https://github.com/Sierraffinity/CrystalDust',evidence='Reachable native Route19 MAPCALLBACK_TILES: while event215 is false, six exact changeblock writes install solid rockfall block122. Route20 sets event215 and later Route19 loads retain cleared native layout. The32x32 barrier uses four whole unscaled native CrystalDust16x16 boulders over the selected Route19 ground; no clipped large boulder, changed collision, altered event or script mechanics.',fieldStateReview=dict(event=215,when=False,callback=k['witnesses'][0]['script'],writes=k['witnesses'],clear_event_map='ROUTE_20'))
 r['compositionPixelHash']=rgba(preview.replacement_image(CACHE,r,imp.packed,OUT/'files'));rows.append(r);proof.append(k)
(OUT/'files/mappings').mkdir(parents=True,exist_ok=True);write_rows(OUT/'files/mappings/crystaldust_route19_rockfall.lua',rows)
(OUT/'rows.json').write_text(json.dumps(rows,indent=2)+'\n');(OUT/'witnesses.json').write_text(json.dumps(proof,indent=2)+'\n')
provenance=dict(origin='Four whole native CrystalDust16px boulders form a bounded32px rockfall barrier; all opaque artwork pixels remain native1:1. Transparent exterior shows the existing selected Route19 ground.',rom_sha256='51196cba923c315d0088b747b5cdee704f2ac057cd493f9ddf226fb7227302cf',source_pair='083df704_083df794',source_mid=514,source_plane='mid',source_atlas_sha256=sha(atlas),source_crop=[32,512,16,16],source_rgba_sha256=rgba(rock),source_contexts=['g24_m004 (Slowpoke Well):4,6;2,7;4,7;8,7','g24_m009 (Slowpoke Well B2F)'],files={p.name:sha(p)for p in sorted(ad.glob('*.png'))})
(ad/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
(OUT/'files/lib').mkdir(parents=True,exist_ok=True)
for n in ['mapping.lua','session.lua','donor.lua','composition.lua']:shutil.copyfile(ROOT/'lib'/n,OUT/'files/lib'/n)
result=neutral.validate_batch(rows,SimpleNamespace(cache=CACHE,engine=W/'.work/tileshift-engine-0400',output=OUT),OUT/'files');(OUT/'neutral-proof.json').write_text(json.dumps(result,indent=2)+'\n')
game='crystal';mp=imp.table(game,'maps')['ROUTE_19'];by={}
for v in pool:
 r=v['row']
 if r['game']==game and r.get('map')=='ROUTE_19':by[r['id'],r['quadrant']]=r
native=Image.new('RGBA',(mp['width']*32,mp['height']*32));changed=native.copy();writes={tuple(v['block_coordinate'])for v in keys[-1]['witnesses']};made={r['quadrant']:r for r in rows if r['game']==game}
for i,bid in enumerate(mp['blocks']):
 bx=i%mp['width'];byy=i//mp['width']
 for q in range(4):
  r=by[bid,q];im=preview.replacement_image(CACHE,r,imp.packed,ROOT);pos=(bx*32+q%2*16,byy*32+q//2*16);native.alpha_composite(im,pos)
  changed.alpha_composite(preview.replacement_image(CACHE,made[q],imp.packed,OUT/'files')if(bx,byy)in writes else im,pos)
native.save(OUT/'route19-cleared.png');changed.save(OUT/'route19-rockfall.png');font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17);board=Image.new('RGB',(native.width*2+36,native.height+55),'#18222d');d=ImageDraw.Draw(board);d.text((12,8),'After Route20: cleared',font=font,fill='white');d.text((native.width+24,8),'Before Route20: rockfall',font=font,fill='white');board.paste(native,(12,40));board.paste(changed,(native.width+24,40));board.save(OUT/'Route19-whole-map-review.png')
manifest=dict(status='ready_private_candidate',mapping_stem='crystaldust_route19_rockfall',candidate=str(OUT/'files/mappings/crystaldust_route19_rockfall.lua'),mapping_sha256=sha(OUT/'files/mappings/crystaldust_route19_rockfall.lua'),new_keys=12,script_placements=18,witnesses=str(OUT/'witnesses.json'),neutral=result,whole_scene_review=str(OUT/'Route19-whole-map-review.png'),assets=[dict(source=str(p),target=ASSET+'/'+p.name,sha256=sha(p))for p in sorted(ad.iterdir())],tools=[dict(source=str(Path(__file__).resolve()),target='tools/author_crystaldust_route19_rockfall.py',sha256=sha(Path(__file__)))],runtime_replay='Native callback truth branch confirmed from imported scripts; root frozen native callback replay pending.')
(OUT/'integration.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(dict(rows=len(rows),neutral=result,integration_sha256=sha(OUT/'integration.json'))))
