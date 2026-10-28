"""Apply only explicitly reviewed neutral glyph/interaction/recipe matches."""
import sys,os,json,argparse,hashlib
from types import SimpleNamespace
from pathlib import Path
from collections import defaultdict,Counter

import catalog,preview,gen2_extended_review as e
from johto_remaining_review import artwork
from center_mart_overhang_review import write_rows
from gen2_cave_review import contact,source_image
parser=argparse.ArgumentParser();parser.add_argument('--validate',action='store_true');parser.add_argument('--activate',action='store_true');args=parser.parse_args();assert not args.activate or args.validate
root=Path(__file__).resolve().parents[1];approved={(r['sourceHash'],r['sourceCollision'],r['recipe_sha256'])for r in json.loads((root/'tools/johto_shared_matches.json').read_text())};cache=Path(os.environ['APPDATA'])/'pokemon-love2d';out=root.parent/'.work/tileshift-johto-shared-finish';out.mkdir(exist_ok=True);active=[r for f in(root/'mappings').glob('*.lua')if f.name!='johto_shared_finish.lua'for r in preview.read_reviewed(f)];rows=[];held=defaultdict(list)
for game in e.GAMES:
 data=e.source(cache,game);limit=catalog.read_lua(cache/game/'data/generated/landmarks.lua')['landmarks']['LANDMARK_PALLET_TOWN']['index'];known=defaultdict(dict)
 for r in active:
  if r['tileset'] in ('TILESET_JOHTO','TILESET_KANTO','TILESET_PARK','TILESET_CAVE','TILESET_DARK_CAVE','TILESET_ICE_PATH') or r['game']!=game or r.get('x')is not None or r.get('foreground')or r.get('sourceWhole32Profile')or 'overhang'in r['role']:continue
  c=e.cell_info(cache,game,data,r['tileset'],r['id'],r['quadrant']);known[(c['sourceHash'],c['collision'])][json.dumps(artwork(r),sort_keys=True)]=r
 for name,m in sorted(data['maps'].items()):
  if not isinstance(m,dict)or not 0<m.get('landmark',999)<limit or m['tileset'] in ('TILESET_JOHTO','TILESET_KANTO','TILESET_PARK','TILESET_CAVE','TILESET_DARK_CAVE','TILESET_ICE_PATH'):continue
  # The harbour's neutral dotted glyph is concrete, despite sharing the
  # outdoor grass glyph. Its reviewed dock family owns this context.
  if name=='OLIVINE_PORT':continue
  selected=[r for r in active if r['game']==game and r['tileset']==m['tileset']and r.get('map',name)==name];generic={(r['id'],r['quadrant'])for r in selected if r.get('x')is None};pos={(r['id'],r['quadrant'],r['x'],r['y'])for r in selected if r.get('x')is not None};occ=defaultdict(list)
  for y in range(m['height']*2):
   for x in range(m['width']*2):
    b=m['blocks'][y//2*m['width']+x//2];q=y%2*2+x%2
    if(b,q)not in generic and(b,q,x,y)not in pos:occ[b,q].append([x,y])
  for(b,q),coords in occ.items():
   c=e.cell_info(cache,game,data,m['tileset'],b,q)
   # These monochrome glyphs coincide with unrelated floor patterns. Their
   # gym/shop context requires an explicit native interior counterpart.
   if name=='GOLDENROD_BIKE_SHOP'and tuple(c['tiles'])==(32,32,32,32):continue
   if name=='OLIVINE_GYM'and tuple(c['tiles'])in((72,72,72,72),(81,81,81,81)):continue
   arts=known[(c['sourceHash'],c['collision'])]
   if len(arts)!=1:continue
   seed=next(iter(arts.values()));recipe_hash=hashlib.sha256(json.dumps(artwork(seed),sort_keys=True).encode()).hexdigest()
   if(c['sourceHash'],c['collision'],recipe_hash)not in approved:continue
   r={'game':game,'style':'gen3','map':name,'tileset':m['tileset'],'id':b,'quadrant':q,'sourceCells':coords,'sourceHash':c['sourceHash'],'sourceFiles':data['fingerprints'][m['tileset']],'sourceCollision':c['collision'],'sourcePriority':[bool(z.get('priority'))for z in c['attributes']],'sourcePalettes':[z.get('palette',1)for z in c['attributes']],'status':'candidate','role':seed['role'],'evidence':'Exact original neutral pixels and interaction byte match the explicitly reviewed complete Gen3 counterpart in tools/johto_shared_matches.json. Source palettes and priority remain individually fingerprinted; color-slot differences do not infer a new semantic match. Complete artwork/role pairs and original Johto contexts were visually reviewed before activation. Original events, collision and warps remain unchanged.','template':{'map':seed.get('map'),'tileset':seed['tileset'],'id':seed['id'],'quadrant':seed['quadrant']}};r.update(artwork(seed));rows.append(r)
(out/'candidates.json').write_text(json.dumps(rows,indent=2));print(json.dumps({'rows':len(rows),'cells':sum(len(r['sourceCells'])for r in rows),'families':dict(Counter(r['tileset']for r in rows))}))

if args.validate:
 for r in rows:r['status']='reviewed'
 proof=e.validate_batch(rows,SimpleNamespace(cache=cache,engine=root.parent/'.tools/engine-0395',output=out),root)
 (out/'proof.json').write_text(json.dumps(proof,indent=2))
 if args.activate:write_rows(root/'mappings/johto_shared_finish.lua',rows)
