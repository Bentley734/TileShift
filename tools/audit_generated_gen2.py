"""Audit all active Gen2 artwork references and the effective foliage catalog."""
import sys,json,collections,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import preview
p=argparse.ArgumentParser();p.add_argument('--require-only-kept-well',action='store_true');a=p.parse_args()
root=Path(__file__).resolve().parents[1]
def refs(v,field=''):
 if isinstance(v,dict):
  for k,x in v.items():yield from refs(x,field+'.'+str(k))
 elif isinstance(v,list):
  for i,x in enumerate(v):yield from refs(x,field+'['+str(i)+']')
 elif isinstance(v,str)and v.startswith(('assets/original/','assets/user_flora/')):yield field,v
left=[]
for path in list((root/'mappings').glob('*.lua'))+[root/'lib'/n for n in ('roof_catalog.lua','side_catalog.lua','center_mart_roofs.lua','goldenrod_roofs.lua','pallet_roofs.lua','johto_roofs.lua','gen2_kanto_building_roofs.lua','gen2_kanto_landmark_decorations.lua')]:
 for r in preview.read_reviewed(path):
  if r['game']not in ('gold','silver','crystal'):continue
  for field,asset in refs(r):left.append(dict(module=path.relative_to(root).as_posix(),game=r['game'],map=r.get('map'),role=r['role'],field=field,asset=asset))
sys.path.insert(0,str(root.parent/'.tools/python'))
from lupa.luajit21 import LuaRuntime
rt=LuaRuntime(unpack_returned_tuples=True)
base=rt.execute((root/'lib/flora_catalog.lua').read_text());effective=rt.execute((root/'lib/johto_hack_flora.lua').read_text())(base)
flora=[]
for group in ('trees','big_trees','cut_trees','flowers','grass','water'):
 for _,entry in effective[group].items():
  asset=entry['asset']
  if asset and asset.startswith(('assets/original/','assets/user_flora/')):flora.append(dict(group=group,asset=asset))
exception=[r for r in left if r['asset'].startswith('assets/original/slowpoke-well/')]
unresolved=[r for r in left if r not in exception]
report=dict(references=left,kept_well_references=len(exception),unresolved_generated_references=unresolved,effective_gen2_flora_generated_references=flora)
(root.parent/'.work/tileshift-firegold/remaining-generated-qa.json').write_text(json.dumps(report,indent=2))
print(json.dumps(dict(reference_count=len(left),kept_well=len(exception),unresolved=len(unresolved),generated_flora=len(flora))))
if a.require_only_kept_well:assert not unresolved and not flora,'Generated GSC artwork still active'
