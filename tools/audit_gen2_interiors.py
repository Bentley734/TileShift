"""Render every GSC interior for visual QA; never activates inferred matches."""
import os,json,hashlib
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import catalog,preview
from interior_review import Imports
from validate_gpu import runtime_fingerprint
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'.work/tileshift-gen2-interior-audit';OUT.mkdir(exist_ok=True)
cache=Path(os.environ['APPDATA'])/'pokemon-love2d'
fingerprint=runtime_fingerprint(ROOT)['sha256']
marker=OUT/'capture-inputs.json'
reuse=marker.exists()and json.loads(marker.read_text()).get('runtime_sha256')==fingerprint
rows=[r for path in sorted((ROOT/'mappings').glob('*.lua'))for r in preview.read_reviewed(path)if r['game']in('gold','silver','crystal')and r['style']=='gen3']
packed={};memo={};original=preview.replacement_image


def cached(cache,row,packed,root):
 key=json.dumps(row,sort_keys=True)
 if key not in memo:memo[key]=original(cache,row,packed,root)
 return memo[key]
preview.replacement_image=cached
records=[];unique={}
for game in ('crystal','gold','silver'):
 maps=catalog.read_lua(cache/game/'data/generated/maps.lua')
 target=OUT/game;target.mkdir(exist_ok=True)
 for name,m in sorted(maps.items()):
  if not isinstance(m,dict)or m.get('environment')not in('INDOOR','GATE','DUNGEON','CAVE'):continue
  if reuse and(target/(name+'-development.png')).exists():
   result={'existing_capture':True}
  else:
   try:result=preview.map_preview(cache,target,game,name,name,rows,packed,1,ROOT)
   except AssertionError as error:result={'render_error':str(error)}
  records.append(dict(result,game=game,map=name,environment=m['environment']))
  (OUT/'progress.json').write_text(json.dumps({'rendered':len(records),'game':game,'map':name}))
 (OUT/'manifest.json').write_text(json.dumps(records,indent=2))
marker.write_text(json.dumps({'runtime_sha256':fingerprint,'visited_maps':len(records),'render_errors':[r for r in records if 'render_error'in r]},indent=2))
print('Visited',len(records),'interior map variants;',sum('render_error'in r for r in records),'render errors; captures require visual review')
