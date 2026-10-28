"""Common source-guarded staging and live validation for explicit Johto recipes.

This infrastructure chooses no counterparts. Each family supplies its own
visually reviewed handler; unknown source artwork is held, never filled.
"""
import argparse,copy,json,os
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
import catalog,preview,gen2_extended_review as e
from interior_review import Imports
from johto_remaining_review import artwork
from center_mart_overhang_review import write_rows
ROOT=Path(__file__).resolve().parents[1]
class FamilyReview:
 def __init__(self,name,tilesets,maps=None):
  self.name=name;self.tilesets=set(tilesets);self.maps=set(maps)if maps is not None else None;self.overrides=set();self.cache=Path(os.environ['APPDATA'])/'pokemon-love2d';self.out=ROOT.parent/('.work/tileshift-johto-'+name+'-finish');self.out.mkdir(exist_ok=True);self.imp=Imports(self.cache,ROOT.parent/'.work/tileshift-catalog');self.packed=self.imp.packed;self.path=ROOT/('mappings/johto_'+name+'_finish.lua');self.active=[r for f in(ROOT/'mappings').glob('*.lua')if f!=self.path for r in preview.read_reviewed(f)];self.templates={r['role']:r for r in self.active if r['game']=='crystal'}
 def ref(self,game,pair,mid):return{'game':game,'tileset':pair,'id':mid,'hash':self.imp.cell_index(game)[pair,mid]['pixel_sha256']}
 def native(self,ref,role):return{'kind':'native','donor':ref,'role':role}
 def composite(self,base,parts,role):return{'kind':'native_composite','base':copy.deepcopy(base),'parts':copy.deepcopy(parts),'role':role}
 def template(self,role,base=None):
  r=artwork(self.templates[role]);r['role']=role
  if base is not None:r['base']=copy.deepcopy(base)
  return r
 def original(self,asset,base,role):
  path=ROOT/asset
  if not path.exists():return None
  return{'kind':'original','asset':asset,'assetFileHash':catalog.sha(path.read_bytes()),'base':copy.deepcopy(base),'role':role}
 def run(self,handler,scenes,evidence,preserved_raw=()):
  p=argparse.ArgumentParser();p.add_argument('--validate',action='store_true');p.add_argument('--activate',action='store_true');a=p.parse_args();assert not a.activate or a.validate;rows=[];held=[];stats=[]
  for game in e.GAMES:
   data=e.source(self.cache,game);limit=self.imp.table(game,'landmarks')['landmarks']['LANDMARK_PALLET_TOWN']['index']
   for name,m in sorted(data['maps'].items()):
    if not isinstance(m,dict)or not 0<m.get('landmark',999)<limit or m['tileset']not in self.tilesets or(self.maps is not None and name not in self.maps):continue
    selected=[r for r in self.active if r['game']==game and r['tileset']==m['tileset']and r.get('map',name)==name];generic={(r['id'],r['quadrant'])for r in selected if r.get('x')is None};pos={(r['id'],r['quadrant'],r['x'],r['y'])for r in selected if r.get('x')is not None};added=0
    for y in range(m['height']*2):
     for x in range(m['width']*2):
      b=m['blocks'][y//2*m['width']+x//2];q=y%2*2+x%2
      force=(game,name,x,y)in self.overrides
      if((b,q)in generic or(b,q,x,y)in pos)and not force:continue
      c=e.cell_info(self.cache,game,data,m['tileset'],b,q);art=handler(c,x,y,name,m,data)
      if not art:held.append({'game':game,'map':name,'x':x,'y':y,'raw':c['tiles'],'collision':c['collision'],'sourceHash':c['sourceHash']});continue
      r={'game':game,'style':'gen3','map':name,'tileset':m['tileset'],'id':b,'quadrant':q,'x':x,'y':y,'sourceCells':[[x,y]],'sourceHash':c['sourceHash'],'sourceFiles':data['fingerprints'][m['tileset']],'sourceCollision':c['collision'],'sourcePriority':[bool(v.get('priority'))for v in c['attributes']],'sourcePalettes':[v.get('palette',1)for v in c['attributes']],'status':'candidate','evidence':evidence,'_positioned':force};r.update(art);r['compositionPixelHash']=catalog.sha(preview.replacement_image(self.cache,r,self.packed,ROOT).tobytes());rows.append(r);added+=1
    stats.append({'game':game,'map':name,'added':added})
  grouped=defaultdict(list)
  for r in rows:grouped[r['game'],r['map'],r['id'],r['quadrant']].append(r)
  rows=[]
  for group in grouped.values():
   if not any(r.get('_positioned')for r in group)and len({json.dumps(artwork(r),sort_keys=True)for r in group})==1:
    r=group[0];r.pop('x');r.pop('y');r['sourceCells']=[z['sourceCells'][0]for z in group];rows.append(r)
   else:rows.extend(group)
  for r in rows:r.pop('_positioned',None)
  (self.out/'candidates.json').write_text(json.dumps(rows,indent=2));(self.out/'held.json').write_text(json.dumps(held,indent=2));(self.out/'summary.json').write_text(json.dumps(stats,indent=2));print(json.dumps({'rows':len(rows),'held':len(held),'unique_held':list({tuple(z['raw'])for z in held}),'maps':len(stats)}))
  for name in scenes:preview.map_preview(self.cache,self.out,'crystal',name,'crystal-'+name,self.active+rows,self.packed,2,ROOT)
  if a.validate:
   assert all(tuple(z['raw'])in preserved_raw for z in held),'Unreviewed source shapes remain'
   for r in rows:r['status']='reviewed'
   proof=e.validate_batch(rows,SimpleNamespace(cache=self.cache,engine=ROOT.parent/'.tools/engine-0395',output=self.out),ROOT)
   for s in stats:
    v=preview.map_preview(self.cache,self.out,s['game'],s['map'],s['game']+'-'+s['map'],self.active+rows,self.packed,1,ROOT);remaining=sum(z['game']==s['game']and z['map']==s['map']for z in held);assert v['visible_cells']-v['replaced_occurrences']==remaining,s
   if held:proof.update(preserved_original_cells=len(held),preserved_original_shapes=sorted({tuple(z['raw'])for z in held}),complete=False)
   (self.out/'proof.json').write_text(json.dumps(proof,indent=2))
   if a.activate:write_rows(self.path,rows)
