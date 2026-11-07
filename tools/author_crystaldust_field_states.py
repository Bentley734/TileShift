from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from types import SimpleNamespace
import hashlib,json,sys,copy
W=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent;f=json.loads((W/'.work/tileshift-v0445-checkpoint/frozen.json').read_text());ROOT=Path(f['stage']);sys.path[:0]=[str(W/'.tools/python'),str(ROOT/'tools')]
import catalog,preview,gen2_extended_review as neutral
from center_mart_overhang_review import write_rows
CACHE=Path('C:/Users/LSDMTHC/AppData/Roaming/pokemon-love2d');source=json.loads((OUT/'alias-inventory.json').read_text());rows=[];proofs=[];witnesses=[];packed={}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();digest=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
for item in source['keys']:
 if item['map']=='ROUTE_19':continue
 alias=item['best_alias'];assert alias;old=alias['row'];c=item['source'];r={k:copy.deepcopy(v)for k,v in old.items()if not k.startswith('source')and k not in('x','y','reviewedSeed','nativeContext','artifactReview','materialSource')}
 if old.get('sourceUrl'):r['sourceUrl']=old['sourceUrl']
 r.update(game=item['game'],style='gen3',map=item['map'],tileset=item['tileset'],id=item['id'],quadrant=item['quadrant'],sourceHash=c['sourceHash'],sourceCollision=c['collision'],sourcePriority=[bool(a.get('priority'))for a in c['attributes']],sourcePalettes=[a.get('palette',1)for a in c['attributes']],sourceFiles=item['sourceFiles'],sourceCells={},status='reviewed',evidence='Native Cut/Whirlpool destination quarter matches the independently reviewed natural source glyph exactly: identical neutralRGBA, nativecollision, every8pxpalette and priority. Retain the exact selected same-context counterpart including T1Headbutt tree quarters and full native water schedule. Only visual mappings are added; native fieldtables, permissions, collision, transitions and scripts remain unchanged.',fieldStateReview=dict(engine_actions=sorted({w['action']for w in item['witnesses']}),original_alias_module=alias['module'],original_alias_key=[v if v is not None else'*'for v in alias['key']],original_alias_semantic_sha256=alias['semantic_sha256'],source_signature='neutralRGBA+nativecollision+all8pxpalette+priority',witnesses=item['witnesses']))
 im=preview.replacement_image(CACHE,r,packed,ROOT);r['compositionPixelHash']=hashlib.sha256(im.tobytes()).hexdigest();before=preview.replacement_image(CACHE,old,packed,ROOT);assert im.tobytes()==before.tobytes();rows.append(r);proofs.append(dict(key=[item[k]for k in('game','map','tileset','id','quadrant')],source=c,alias_module=alias['module'],alias_key=alias['key'],alias_semantic_sha256=alias['semantic_sha256'],same_source_palette_priority_collision=True,output_rgba_sha256=r['compositionPixelHash'],witness_occurrences=len(item['witnesses'])))
 for w in item['witnesses']:witnesses.append(dict(game=item['game'],map=item['map'],tileset=item['tileset'],id=item['id'],quadrant=item['quadrant'],**w))
assert len(rows)==258
(OUT/'files/mappings').mkdir(parents=True,exist_ok=True);write_rows(OUT/'files/mappings/crystaldust_field_states.lua',rows);(OUT/'rows.json').write_text(json.dumps(rows,indent=2)+'\n');(OUT/'witnesses.json').write_text(json.dumps(witnesses,indent=2)+'\n');(OUT/'source-alias-proof.json').write_text(json.dumps(proofs,indent=2)+'\n')
result=neutral.validate_batch(rows,SimpleNamespace(cache=CACHE,engine=W/'.work/tileshift-engine-0400',output=OUT),ROOT);(OUT/'neutral-proof.json').write_text(json.dumps(result,indent=2)+'\n')
# Complete post-action source blocks demonstrate retained quarter arrangements.
by={}
for r in rows:
 if r['game']=='crystal':by.setdefault((r['map'],r['id']),{})[r['quadrant']]=r
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15);board=Image.new('RGB',(1200,((len(by)+5)//6)*150+55),'#18222d');dr=ImageDraw.Draw(board);dr.text((14,10),'Native post-Cut/Whirlpool blocks / exact reviewed counterpart quarters',font=font,fill='white')
pool=json.loads((W/'.work/tileshift-crystaldust-sweep/audit/selected-row-pool.json').read_text())['rows']
for i,((name,bid),qs)in enumerate(by.items()):
 x=i%6*200+10;y=i//6*150+50;dr.text((x,y),name+' '+str(bid),font=font,fill='white');whole=Image.new('RGBA',(32,32))
 for q in range(4):
  r=qs.get(q)
  if not r:
   existing=[v['row']for v in pool if v['row']['game']=='crystal'and v['row']['id']==bid and v['row']['quadrant']==q and v['row'].get('map',name)==name and v['row'].get('x')is None]
   existing.sort(key=lambda v:v.get('map')is not None)
   if existing:r=existing[-1]
  if r:whole.alpha_composite(preview.replacement_image(CACHE,r,packed,ROOT),(q%2*16,q//2*16))
 board.paste(whole.resize((96,96),Image.Resampling.NEAREST),(x,y+24))
board.save(OUT/'Post-field-blocks-review.png')
manifest=dict(status='ready_private_alias_candidate',mapping_stem='crystaldust_field_states',candidate=str(OUT/'files/mappings/crystaldust_field_states.lua'),mapping_sha256=sha(OUT/'files/mappings/crystaldust_field_states.lua'),new_keys=len(rows),witness_occurrences=len(witnesses),maps=len({(r['game'],r['map'])for r in rows}),source_alias_proof=str(OUT/'source-alias-proof.json'),witnesses=str(OUT/'witnesses.json'),neutral=result,tools=[dict(source=str(Path(__file__).resolve()),target='tools/author_crystaldust_field_states.py',sha256=sha(Path(__file__)))],native_runtime_replay='pending root frozen-stage native field action renderer',unused_beta_records_excluded=4)
(OUT/'integration.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(dict(rows=len(rows),occurrences=len(witnesses),neutral=result,module_sha256=manifest['mapping_sha256'],integration_sha256=sha(OUT/'integration.json'))))
