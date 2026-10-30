"""Stage exact existing house counterparts in rooms whose furniture remains native."""
import os,copy,json,argparse
from pathlib import Path
from collections import defaultdict
from types import SimpleNamespace
import catalog,preview,gen2_extended_review as e
from johto_remaining_review import artwork
from interior_review import Imports
from center_mart_overhang_review import write_rows
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT.parent/'.work/tileshift-gen2-house-context-cleanup';OUT.mkdir(exist_ok=True)
TARGET=ROOT/'mappings/gen2_house_context_cleanup.lua'
def main():
 p=argparse.ArgumentParser();p.add_argument('--activate',action='store_true');p.add_argument('--validate',action='store_true');a=p.parse_args();assert not a.activate or a.validate
 cache=Path(os.environ['APPDATA'])/'pokemon-love2d';imp=Imports(cache,ROOT.parent/'.work/tileshift-catalog');active=[r for path in sorted((ROOT/'mappings').glob('*.lua'))if path!=TARGET for r in preview.read_reviewed(path)];added=[];held=[]
 for game in ('gold','silver','crystal'):
  data=e.source(cache,game);pool=defaultdict(dict)
  for r in active:
   if r['game']!=game or r['style']!='gen3'or r['tileset']not in('TILESET_HOUSE','TILESET_TRADITIONAL_HOUSE','TILESET_PLAYERS_HOUSE','TILESET_PLAYERS_ROOM')or r.get('kind')=='source_palette':continue
   key=(r['tileset'],r['id'],r['quadrant'],r['sourceHash']);art=artwork(r);pool[key][json.dumps(art,sort_keys=True)]=r
  for name,m in sorted(data['maps'].items()):
   if not isinstance(m,dict)or m.get('environment')!='INDOOR'or m['tileset']not in('TILESET_HOUSE','TILESET_TRADITIONAL_HOUSE','TILESET_PLAYERS_HOUSE','TILESET_PLAYERS_ROOM'):continue
   current=[r for r in active if r['game']==game and r['style']=='gen3'and r['tileset']==m['tileset']and r.get('map',name)==name];generic={(r['id'],r['quadrant'])for r in current if r.get('x')is None};positioned={(r['id'],r['quadrant'],r['x'],r['y'])for r in current if r.get('x')is not None}
   for y in range(m['height']*2):
    for x in range(m['width']*2):
     bid=m['blocks'][y//2*m['width']+x//2];q=y%2*2+x%2
     if(bid,q)in generic or(bid,q,x,y)in positioned:continue
     c=e.cell_info(cache,game,data,m['tileset'],bid,q);choices=pool.get((m['tileset'],bid,q,c['sourceHash']),{})
     if len(choices)!=1:held.append({'game':game,'map':name,'xy':[x,y],'reason':'No unique exact reviewed recipe'});continue
     seed=next(iter(choices.values()))
     backgrounds={json.dumps(r['donor'],sort_keys=True)for r in current if r.get('donor')and any(tag in r['role']for tag in('floor','wall','tatami'))}
     if seed.get('base')and json.dumps(seed['base'],sort_keys=True)not in backgrounds:
      floors={json.dumps(r['donor'],sort_keys=True)for r in current if r.get('donor')and 'floor'in r['role']}
      # These checked native mid-layer recipes contain only furniture alpha,
      # so their detached floor reference can use the room's own exact floor.
      detached=seed.get('kind')=='native_composite'and seed.get('parts')and all(p.get('layers')==['mid']for p in seed['parts'])
      if detached and len(floors)==1 and any(tag in seed['role']for tag in('chair','table','plant')):
       seed=copy.deepcopy(seed);seed['base']=json.loads(next(iter(floors)))
      else:
       held.append({'game':game,'map':name,'xy':[x,y],'reason':'Existing room background differs from template'});continue
     if seed.get('sourceCollision')is not None and seed['sourceCollision']!=c['collision']:continue
     r={'game':game,'style':'gen3','map':name,'tileset':m['tileset'],'id':bid,'quadrant':q,'x':x,'y':y,'sourceCells':[[x,y]],'sourceHash':c['sourceHash'],'sourceFiles':data['fingerprints'][m['tileset']],'sourceCollision':c['collision'],'sourcePriority':[bool(v.get('priority'))for v in c['attributes']],'sourcePalettes':[v.get('palette',1)for v in c['attributes']],'status':'reviewed','evidence':'Exact same original house tileset, block/quadrant and source pixel fingerprint as the unique already reviewed native Gen3 object recipe. No cross-family or collision-only match; source map geometry, events and interactions are retained. Explicit room scope keeps the counterpart and its floor context reviewable.'};r.update(artwork(seed));r['role']=seed['role'];r['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,r,imp.packed,ROOT).tobytes());added.append(r)
 (OUT/'candidates.json').write_text(json.dumps(added,indent=2));(OUT/'held.json').write_text(json.dumps(held,indent=2))
 for name in sorted({r['map']for r in added if r['game']=='crystal'}):preview.map_preview(cache,OUT,'crystal',name,name,active+added,imp.packed,2,ROOT)
 if a.validate:print(e.validate_batch(added,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=OUT),ROOT))
 if a.activate:write_rows(TARGET,added)
 print(json.dumps({'new_rows':len(added),'maps':len({(r['game'],r['map'])for r in added}),'held':len(held)}))
if __name__=='__main__':main()
