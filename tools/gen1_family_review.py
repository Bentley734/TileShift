"""Explicit source-guarded Gen1 family recipes; no inferred tile counterparts."""
import argparse,copy,json,os
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
from PIL import Image
import catalog,preview,gen2_extended_review as validation
from interior_review import Imports
from johto_remaining_review import artwork
from center_mart_overhang_review import write_rows
ROOT=Path(__file__).resolve().parents[1]
GAMES=('red','blue','yellow')

def source(cache,game):
 root=cache/game
 return {'maps':catalog.read_lua(root/'data/generated/maps.lua'),'sets':catalog.read_lua(root/'data/generated/tilesets.lua'),'sheets':{},'cells':{},'fingerprints':{}}

def cell_info(cache,game,data,tileset,block_id,q):
 key=tileset,block_id,q
 if key in data['cells']:return data['cells'][key]
 ts=data['sets'][tileset]
 if tileset not in data['sheets']:
  data['sheets'][tileset]=Image.open(cache/game/ts['image']).convert('RGBA')
  data['fingerprints'][tileset]={'metadata':catalog.sha((cache/game/'data/generated/tilesets.lua').read_bytes()),'image':catalog.sha((cache/game/ts['image']).read_bytes()),'maps':catalog.sha((cache/game/'data/generated/maps.lua').read_bytes())}
 block=catalog.lua_array(catalog.dict_at(ts['blocks'],block_id+1));x,y=q%2*2,q//2*2
 ids=[block[i]for i in(y*4+x,y*4+x+1,(y+1)*4+x,(y+1)*4+x+1)]
 attrs=[catalog.gb_tile(data['sheets'][tileset],ts,t)[1]for t in ids]
 walk=set(catalog.lua_array(ts.get('walkable',[])));warps=set(catalog.lua_array(ts.get('warpTiles',[])));doors=set(catalog.lua_array(ts.get('doorTiles',[])));counters=set(catalog.lua_array(ts.get('counterTiles',[])))
 behavior={'walkable':[t in walk for t in ids],'grass':ts.get('grassTile')in ids,'warp':[t in warps for t in ids],'door':[t in doors for t in ids],'counter':[t in counters for t in ids]}
 pixels=preview.native_cell(data['sheets'][tileset],ts,block,q)
 c={'game':game,'tileset':tileset,'id':block_id,'quadrant':q,'tiles':ids,'attributes':attrs,'sourceHash':catalog.sha(pixels.tobytes()),'walkable_tiles':behavior['walkable'],'grass_tile_present':behavior['grass'],'warp_tile_present':any(behavior['warp']),'door_tiles':behavior['door'],'counter_tiles':behavior['counter'],'collision':tuple(behavior['walkable']),'behavior':behavior}
 data['cells'][key]=c;return c

def identity(c):
 b=c['behavior'];return(c['sourceHash'],tuple(b['walkable']),b['grass'],tuple(b['warp']),tuple(b['door']),tuple(b['counter']))

def source_image(cache,game,data,c,definition=None):
 ts=data['sets'][c['tileset']]
 return preview.native_cell(data['sheets'][c['tileset']],ts,catalog.lua_array(catalog.dict_at(ts['blocks'],c['id']+1)),c['quadrant'])

class FamilyReview:
 def __init__(self,name,tilesets,maps=None):
  self.name=name;self.tilesets=set(tilesets);self.maps=set(maps)if maps is not None else None;self.overrides=set();self.cache=Path(os.environ['APPDATA'])/'pokemon-love2d';self.out=ROOT.parent/('.work/tileshift-gen1-'+name+'-finish');self.out.mkdir(exist_ok=True);self.imp=Imports(self.cache,ROOT.parent/'.work/tileshift-catalog');self.packed=self.imp.packed;self.path=ROOT/('mappings/gen1_'+name+'_finish.lua');self.active=[r for p in(ROOT/'mappings').glob('*.lua')if p!=self.path for r in preview.read_reviewed(p)];self.templates={r['role']:r for r in self.active if r['game']=='crystal'}
  for r in self.active:
   if r['game']=='red':self.templates.setdefault(r['role'],r)
 def ref(self,game,pair,mid):return{'game':game,'tileset':pair,'id':mid,'hash':self.imp.cell_index(game)[pair,mid]['pixel_sha256']}
 def native(self,ref,role):return{'kind':'native','donor':copy.deepcopy(ref),'role':role}
 def composite(self,base,parts,role):
  r={'kind':'native_composite','parts':copy.deepcopy(parts),'role':role}
  if base is not None:r['base']=copy.deepcopy(base)
  return r
 def template(self,role,base=None):
  r=artwork(self.templates[role]);r['role']=role
  if base is not None:r['base']=copy.deepcopy(base)
  return r
 def original(self,asset,base,role):
  path=ROOT/asset
  if not path.exists():return None
  return{'kind':'original','asset':asset,'assetFileHash':catalog.sha(path.read_bytes()),'base':copy.deepcopy(base),'role':role}
 def source_palette(self,colors,role):
  # Four colors may be repeated uniformly, or supply four separate8px palettes.
  palettes=[copy.deepcopy(colors)for _ in range(4)]if len(colors)==4 and len(colors[0])==3 and isinstance(colors[0][0],int)else copy.deepcopy(colors)
  return{'kind':'source_palette','sourceColors':palettes,'role':role}
 def run(self,handler,scenes,evidence,preserved_raw=()):
  p=argparse.ArgumentParser();p.add_argument('--validate',action='store_true');p.add_argument('--activate',action='store_true');a=p.parse_args();assert not a.activate or a.validate;rows=[];held=[];stats=[];data_by_game={}
  for game in GAMES:
   data=source(self.cache,game);data_by_game[game]=data
   for name,m in sorted(data['maps'].items()):
    if not isinstance(m,dict)or m.get('tileset')not in self.tilesets or not m.get('width')or not m.get('height')or(self.maps is not None and name not in self.maps):continue
    selected=[r for r in self.active if r['game']==game and r['tileset']==m['tileset']and r.get('map',name)==name];generic={(r['id'],r['quadrant'])for r in selected if r.get('x')is None};pos={(r['id'],r['quadrant'],r['x'],r['y'])for r in selected if r.get('x')is not None};added=0
    for y in range(m['height']*2):
     for x in range(m['width']*2):
      b=m['blocks'][y//2*m['width']+x//2];q=y%2*2+x%2;force=(game,name,x,y)in self.overrides
      if((b,q)in generic or(b,q,x,y)in pos)and not force:continue
      c=cell_info(self.cache,game,data,m['tileset'],b,q);art=handler(c,x,y,name,m,data)
      if not art:held.append({'game':game,'map':name,'x':x,'y':y,'raw':c['tiles'],'behavior':c['behavior'],'sourceHash':c['sourceHash']});continue
      r={'game':game,'style':'gen3','map':name,'tileset':m['tileset'],'id':b,'quadrant':q,'x':x,'y':y,'sourceCells':[[x,y]],'sourceHash':c['sourceHash'],'sourceFiles':data['fingerprints'][m['tileset']],'sourceBehavior':copy.deepcopy(c['behavior']),'status':'candidate','evidence':evidence,'_positioned':force};r.update(art);r['compositionPixelHash']=catalog.sha(preview.replacement_image(self.cache,r,self.packed,ROOT).tobytes());rows.append(r);added+=1
    stats.append({'game':game,'map':name,'tileset':m['tileset'],'added':added,'total':m['width']*m['height']*4})
  groups=defaultdict(list)
  for r in rows:groups[r['game'],r['map'],r['id'],r['quadrant']].append(r)
  rows=[]
  for group in groups.values():
   if not any(r.get('_positioned')for r in group)and len({json.dumps(artwork(r),sort_keys=True)for r in group})==1:
    r=group[0];r.pop('x');r.pop('y');r['sourceCells']=[v['sourceCells'][0]for v in group];rows.append(r)
   else:rows.extend(group)
  for r in rows:r.pop('_positioned',None)
  (self.out/'candidates.json').write_text(json.dumps(rows,indent=2));(self.out/'held.json').write_text(json.dumps(held,indent=2));(self.out/'summary.json').write_text(json.dumps(stats,indent=2));print(json.dumps({'rows':len(rows),'held':len(held),'unique_held':sorted({tuple(v['raw'])for v in held}),'maps':len(stats)}))
  for name in scenes:
   game=next((g for g in GAMES if name in data_by_game[g]['maps']),None)
   if game:preview.map_preview(self.cache,self.out,game,name,game+'-'+name,self.active+rows,self.packed,3,ROOT)
  if a.validate:
   assert all(tuple(z['raw'])in preserved_raw for z in held),'Unreviewed source shapes remain'
   for r in rows:r['status']='reviewed'
   proof=validation.validate_batch(rows,SimpleNamespace(cache=self.cache,engine=ROOT.parent/'.tools/engine-0395',output=self.out),ROOT)
   for s in stats:
    v=preview.map_preview(self.cache,self.out,s['game'],s['map'],s['game']+'-'+s['map'],self.active+rows,self.packed,2,ROOT);remaining=sum(z['game']==s['game']and z['map']==s['map']for z in held);assert v['visible_cells']-v['replaced_occurrences']==remaining,s
   proof.update(maps=len(stats),complete=not held,preserved_original_cells=len(held))
   (self.out/'proof.json').write_text(json.dumps(proof,indent=2))
   if a.activate:write_rows(self.path,rows)
