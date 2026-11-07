from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from types import SimpleNamespace
import copy,hashlib,json,shutil,sys
W=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent;ROOT=Path(json.loads((W/'.work/tileshift-v0445-checkpoint/frozen.json').read_text())['stage'])
sys.path[:0]=[str(W/'.tools/python'),str(ROOT/'tools')]
import preview,gen2_extended_review as neutral
import interior_review;interior_review.WORKSPACE=W
from interior_review import Imports
from center_mart_overhang_review import write_rows
CACHE=Path('C:/Users/LSDMTHC/AppData/Roaming/pokemon-love2d');imp=Imports(CACHE,W/'.work/tileshift-catalog')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();rgba=lambda im:hashlib.sha256(im.convert('RGBA').tobytes()).hexdigest();digest=lambda r:hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':')).encode()).hexdigest()
ASSET='assets/third_party/johto-hacks/crystaldust-ilex-shrine';ad=OUT/'files'/ASSET;ad.mkdir(parents=True,exist_ok=True)
src=W/'.work/tileshift-firegold/crystaldust';sp=src/'maps/g24_m011-flat.png';source=Image.open(sp).convert('RGBA').crop((348,461,372,495));whole=source.copy()
# These are only the exact native exterior grass/tree-background palette.
# The shrine's wood, slate shadow, door, roof and both feet use disjoint colors.
exterior={(115,206,165),(66,181,140),(165,230,197),(25,165,107),(58,148,49)};removed=[]
for y in range(34):
 for x in range(24):
  if source.getpixel((x,y))[:3]in exterior:whole.putpixel((x,y),(0,0,0,0));removed.append([x,y])
assert len(removed)==152 and whole.getbbox()==(0,0,24,34)
whole.save(ad/'whole24x34.png');canvas=Image.new('RGBA',(48,48));canvas.alpha_composite(whole,(12,14));assets={}
for y in range(3):
 for x in range(3):
  im=canvas.crop((x*16,y*16,x*16+16,y*16+16))
  if im.getbbox():
   p=ad/f'cell-{x+7}-{y+21}.png';im.save(p);assets[x+7,y+21]=(p,im)
assert len(assets)==7
pool=json.loads((W/'.work/tileshift-crystaldust-sweep/audit/selected-row-pool.json').read_text())['rows'];oldrows=[v for v in pool if v['row'].get('role')=='ilex_original_shrine'];assert len(oldrows)==6
supers=[];background=[];overlays=[]
for v in oldrows:
 old=v['row'];r={k:copy.deepcopy(val)for k,val in old.items()if k.startswith('source')and k not in('sourceUrl',)}
 r.update({k:old[k]for k in ('game','style','map','tileset','id','quadrant','x','y')});r.update(donor=copy.deepcopy(old['base']),role='ilex_native_shrine_selected_ground',status='reviewed',evidence='Selected native ground beneath complete native-scale CrystalDust shrine foreground. The original two Ilex shrine source cells, collision, interaction and event scripts remain unchanged; no reduced shrine remains in the background.')
 r['compositionPixelHash']=rgba(preview.replacement_image(CACHE,r,imp.packed,ROOT));background.append(r);supers.append(dict(module=v['module'],original_row=old,original_row_sha256=v['semantic_sha256'],candidate_row=r))
for game in ('gold','silver','crystal'):
 old=next(v['row']for v in oldrows if v['row']['game']==game and v['row']['quadrant']==0)
 for (x,y),(p,im)in assets.items():
  r={k:copy.deepcopy(v)for k,v in old.items()if k.startswith('source')and k not in('sourceUrl','sourceCells')};r.update(game=game,style='gen3',map='ILEX_FOREST',tileset='TILESET_FOREST',id=32,quadrant=0,sourceCells=[[8,22]],sourceHash='7909c2afb5b8ad5d87ad24345244efdbd3798b6908ec2c32a9ddec904b498b42',kind='third_party',status='reviewed',furniture='ilex_shrine',anchorX=8,anchorY=22,x=x,y=y,frontY=380,asset=ASSET+'/'+p.name,assetFileHash=sha(p),assetPixelHash=rgba(im),role='ilex_crystaldust_native_shrine',credit='CrystalDust by Sierraffinity and contributors; complete native Ilex Forest shrine.',sourceUrl='https://github.com/Sierraffinity/CrystalDust',evidence='Complete native24x34 CrystalDust Ilex Forest shrine at1:1scale, worldorigin124,350, feet384. Only exact source exteriorgrass/tree colors are transparent. Pin originalGSC Ilex Forest block32quadrant0 at8,22 with original collision/palette/priority/files. Background precedes actors; only opaque shrine pixels replay over actors with physicalfeet behindfront380. No sprite, collision, interaction or script changes.')
  overlays.append(r)
assert len(overlays)==21
recomposed=[]
for game in ('gold','silver','crystal'):
 actual=Image.new('RGBA',(48,48))
 for r in overlays:
  if r['game']==game:actual.alpha_composite(Image.open(OUT/'files'/r['asset']).convert('RGBA'),((r['x']-7)*16,(r['y']-21)*16))
 assert actual.tobytes()==canvas.tobytes()
 recomposed.append(dict(game=game,cells=7,world_origin=[124,350],native_size=[24,34],native_opaque_pixels=664,all_native_object_pixels_unchanged=True,full_cell_composition_rgba_sha256=rgba(actual),native_rgba_sha256=rgba(whole)))
(OUT/'foreground-recomposition-proof.json').write_text(json.dumps(recomposed,indent=2)+'\n')
(OUT/'supersessions.json').write_text(json.dumps(supers,indent=2)+'\n');(OUT/'furniture-additions.json').write_text(json.dumps(overlays,indent=2)+'\n');(OUT/'background-rows.json').write_text(json.dumps(background,indent=2)+'\n')
provenance=dict(origin='Complete native24x34 CrystalDust Ilex Forest shrine; no resizing, repainting, palette changes or incomplete roof/legs.152 literal source exterior pixels become transparent; all664 object pixels are byte-identical to the supplied native source map.',rom_sha256='51196cba923c315d0088b747b5cdee704f2ac057cd493f9ddf226fb7227302cf',source_map='g24_m011',metadata_region='ILEX FOREST',source_pair='083df704_083df74c',source_png_sha256=sha(sp),source_crop=[348,461,24,34],source_crop_rgba_sha256=rgba(source),native_rgba_sha256=rgba(whole),transparent_source_coordinates=removed,removed_exterior_palette=[list(c)for c in sorted(exterior)],native_opaque_pixels=664,placement=dict(world_origin=[124,350],source_anchor=[8,22],source_block=32,source_quadrant=0,frontY=380),files={p.name:sha(p)for p in sorted(ad.glob('*.png'))})
(ad/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
lib=OUT/'files/lib';lib.mkdir(parents=True,exist_ok=True)
for n in ['mapping.lua','session.lua','donor.lua','composition.lua']:shutil.copyfile(ROOT/'lib'/n,lib/n)
runtime=(ROOT/'lib/roofs.lua').read_text()
needle="    local checked={};for k,v in pairs(row)do checked[k]=v end\n    checked.x,checked.y=row.anchorX,row.anchorY"
shrine="""    local shrine=coords and row.furniture=='ilex_shrine'
      and(row.game=='gold'or row.game=='silver'or row.game=='crystal')
      and row.map=='ILEX_FOREST'and row.tileset=='TILESET_FOREST'
      and row.id==32 and row.quadrant==0 and row.anchorX==8 and row.anchorY==22
      and row.sourceHash=='7909c2afb5b8ad5d87ad24345244efdbd3798b6908ec2c32a9ddec904b498b42'
      and row.sourceCollision==7 and row.role=='ilex_crystaldust_native_shrine'
      and row.x>=7 and row.x<=9 and row.y>=21 and row.y<=23 and row.frontY==380
"""
assert runtime.count(needle)==1;runtime=runtime.replace(needle,shrine+needle).replace('(bed or pc or carpet)and','(bed or pc or carpet or shrine)and')
needle2="          end\n        end\n        return image\n"
check="""          end
          if row.furniture=='ilex_shrine'then
            -- Complete native24x34 altar, centered at the original Ilex source.
            for py=0,15 do for px=0,15 do
              local _,_,_,alpha=image:getPixel(px,py)
              local wx,wy=x*16+px,y*16+py
              assert(alpha==0 or(wx>=124 and wx<148 and wy>=350 and wy<384),
                'Shrine foreground escapes its native24x34 silhouette envelope')
            end end
          end
        end
        return image
"""
assert runtime.count(needle2)==1;runtime=runtime.replace(needle2,check);(lib/'roofs.lua').write_text(runtime)
full=preview.read_reviewed(ROOT/'lib/johto_furniture.lua')+overlays;write_rows(lib/'johto_furniture.lua',full)
result=neutral.validate_batch(background,SimpleNamespace(cache=CACHE,engine=W/'.work/tileshift-engine-0400',output=OUT),OUT/'files');(OUT/'neutral-proof.json').write_text(json.dumps(result,indent=2)+'\n')
# Whole-map CPU artwork preview uses actual source layout and selected backing.
area=json.loads((W/'.work/tileshift-crystaldust-sweep/audit/areas/crystal/ILEX_FOREST.json').read_text());lookup={v['row_id']:v['row']for v in pool};mp=imp.table('crystal','maps')['ILEX_FOREST'];before=Image.new('RGBA',(mp['width']*32,mp['height']*32));after=before.copy();new={(r['x'],r['y']):r for r in background if r['game']=='crystal'}
for x,y,bid,q,rid in area['selected_cells']:
 r=lookup[rid];a=preview.replacement_image(CACHE,r,imp.packed,ROOT);before.alpha_composite(a,(x*16,y*16));after.alpha_composite(preview.replacement_image(CACHE,new[x,y],imp.packed,OUT/'files')if(x,y)in new else a,(x*16,y*16))
after.alpha_composite(whole,(124,350));before.save(OUT/'Ilex-before.png');after.save(OUT/'Ilex-after.png')
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17);board=Image.new('RGB',(700,410),'#18222d');d=ImageDraw.Draw(board);d.text((12,10),'Current reduced shrine',font=font,fill='white');d.text((362,10),'Full native CrystalDust shrine',font=font,fill='white');box=(80,304,192,416);board.paste(before.crop(box).resize((336,336),Image.Resampling.NEAREST),(12,45));board.paste(after.crop(box).resize((336,336),Image.Resampling.NEAREST),(362,45));board.save(OUT/'Ilex-shrine-review.png')
manifest=dict(status='ready_private_candidate',supersessions=str(OUT/'supersessions.json'),superseded_rows=6,furniture_additions=str(OUT/'furniture-additions.json'),foreground_rows=len(overlays),assets=[dict(source=str(p),target=ASSET+'/'+p.name,sha256=sha(p))for p in sorted(ad.iterdir())],files=[dict(source=str(lib/'roofs.lua'),target='lib/roofs.lua',sha256=sha(lib/'roofs.lua'),baseline_sha256=sha(ROOT/'lib/roofs.lua')),dict(source=str(OUT/'files/tests/roofs_shrine_test.lua'),target='tests/roofs_shrine_test.lua',sha256=sha(OUT/'files/tests/roofs_shrine_test.lua'))],catalog_baseline_sha256=sha(ROOT/'lib/johto_furniture.lua'),catalog_preview=str(lib/'johto_furniture.lua'),tools=[dict(source=str(Path(__file__).resolve()),target='tools/author_crystaldust_ilex_shrine.py',sha256=sha(Path(__file__)))],neutral=result,foreground_recomposition=str(OUT/'foreground-recomposition-proof.json'),runtime_tests=str(OUT/'runtime-tests.json'),preview=str(OUT/'Ilex-shrine-review.png'),whole_scene_preview=str(OUT/'Ilex-after.png'))
(OUT/'integration.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(dict(background_rows=6,foreground_rows=len(overlays),neutral=result,integration_sha256=sha(OUT/'integration.json'))))
