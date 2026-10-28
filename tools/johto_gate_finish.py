"""Review source-scoped Johto gate desks, seating, stairs and shop corridor."""
import argparse,copy,json,os
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
import catalog,preview,gen2_extended_review as e
from interior_review import Imports
from native_room_parts import RoomParts
from johto_remaining_review import artwork
from center_mart_overhang_review import write_rows
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--validate',action='store_true');p.add_argument('--activate',action='store_true');a=p.parse_args();assert not a.activate or a.validate
 cache=Path(os.environ['APPDATA'])/'pokemon-love2d';out=ROOT.parent/'.work/tileshift-johto-gate-finish';out.mkdir(exist_ok=True);imp=Imports(cache,ROOT.parent/'.work/tileshift-catalog');active=[r for f in(ROOT/'mappings').glob('*.lua')if f.name!='johto_gate_finish.lua'for r in preview.read_reviewed(f)];gate=RoomParts(imp,'firered','FR_ROUTE_11_EAST_ENTRANCE_1F');north=RoomParts(imp,'firered','FR_ROUTE_5_SOUTH_ENTRANCE');dept=RoomParts(imp,'firered','FR_CELADON_CITY_DEPARTMENT_STORE_1F');floor=gate.ref(641);templates={r['role']:r for r in active if r['game']=='crystal'}
 door=imp.gba('firered','FR_ROUTE_5_SOUTH_ENTRANCE')[0].crop((56,10,88,32))
 for y in range(5,11):assert door.crop((0,y,32,y+1)).tobytes()==door.crop((0,4,32,5)).tobytes()
 for x in range(8,24):assert door.crop((x,0,x+1,14)).tobytes()==door.crop((8,0,9,14)).tobytes()
 def n(mid,role):return{'kind':'native','donor':gate.ref(mid),'role':'johto_gate_'+role}
 def shared(role,base=floor):
  r=artwork(templates[role]);r['base']=base;r['role']='johto_gate_'+role;return r
 def original(path,role):
  path=ROOT/path
  if not path.exists():return None
  return{'kind':'original','base':floor,'asset':path.relative_to(ROOT).as_posix(),'assetFileHash':catalog.sha(path.read_bytes()),'role':'johto_gate_'+role}
 def explicit(c,x,y,m,data):
  raw=tuple(c['tiles']);col=c['collision']
  if raw==(0,0,0,0)and col==7:return n(0,'outside_void')
  if raw in((1,1,1,1),(17,17,1,1),(17,17,17,1),(17,1,17,1)):return n(641,'public_floor')
  if raw in((92,93,16,16),(92,93,8,9)):return n(647,'complete_header_wall')
  if raw==(84,85,86,87):
   left=x+1<m['width']*2 and e.cell_info(cache,c['game'],data,m['tileset'],m['blocks'][y//2*m['width']+(x+1)//2],y%2*2+(x+1)%2)['collision']in(7,144)
   return shared('johto_house_chair_left'if left else'johto_house_chair_right')
  if raw==(8,9,24,25):return n(706,'desk_head')
  if raw==(8,9,14,15):return shared('johto_complete_pc_0',gate.ref(715))
  if raw==(24,25,24,25):return n(715,'desk_surface')
  if raw in((24,25,36,37),(7,7,36,37),(8,7,36,37),(7,9,36,37)):return n(714,'desk_foot')
  if raw==(32,33,24,25):return shared('johto_complete_pc_1',gate.ref(715))
  if raw==(14,15,32,33):
   r=original('assets/original/interior-computer/computer.png','complete_desk_computer')
   if r:r['base']=gate.ref(715)
   return r
  if raw==(56,57,5,6):return n(746,'plant_head')
  if raw in((8,5,21,22),(5,6,21,22)):return n(753,'plant_base')
  if raw==(56,57,21,22):return original('assets/original/interior-flowerpot/flowerpot.png','small_planter')
  if raw in((92,93,72,73),(74,75,78,79)):return shared('johto_complete_pc_'+('0'if raw[0]==92 else'1'),gate.ref(655)if raw[0]==92 else floor)
  if raw in((23,53,16,16),):return{'kind':'native_composite','base':gate.ref(647),'parts':dept.rect(128,16,16,16),'role':'johto_gate_wall_directory'}
  if raw==(2,3,18,19):
   def same(xx):return 0<=xx<m['width']*2 and tuple(e.cell_info(cache,c['game'],data,m['tileset'],m['blocks'][y//2*m['width']+xx//2],y%2*2+xx%2)['tiles'])==raw
   columns=[(72,16,0)]if same(x-1)else[(56,16,0)]if same(x+1)else[(56,8,0),(80,8,8)];parts=[]
   for sx,w,tx in columns:
    parts+=north.rect(sx,10,w,5,tx,0)+north.rect(sx,21,w,11,tx,5)
   return{'kind':'native_composite','base':floor,'parts':parts,'role':'johto_gate_complete_north_doorway'}
  if raw in((80,81,82,83),(88,89,90,91)):return original('assets/original/interior-stairs/'+('up.png'if raw[0]==80 else'down.png'),'stairs_'+('up'if raw[0]==80 else'down'))
  if raw==(4,4,20,20):
   right=x>0 and tuple(e.cell_info(cache,c['game'],data,m['tileset'],m['blocks'][y//2*m['width']+(x-1)//2],y%2*2+(x-1)%2)['tiles'])==raw
   return shared('household_rug_right'if right else'household_rug_left')
  if raw==(40,41,40,41):return n(729 if col==118 else 730,'side_entry_rug')
  return None
 # Rugs are identical original-native recipes shared by the Gen1 furniture set.
 for r in active:
  if r['game']=='red'and r['role'].startswith('household_'):templates.setdefault(r['role'],r)
 rows=[];held=[];stats=[]
 for game in e.GAMES:
  data=e.source(cache,game);limit=imp.table(game,'landmarks')['landmarks']['LANDMARK_PALLET_TOWN']['index']
  for name,m in sorted(data['maps'].items()):
   if not isinstance(m,dict)or not 0<m.get('landmark',999)<limit or m['tileset']!='TILESET_GATE':continue
   selected=[r for r in active if r['game']==game and r['tileset']==m['tileset']and r.get('map',name)==name];generic={(r['id'],r['quadrant'])for r in selected if r.get('x')is None};pos={(r['id'],r['quadrant'],r['x'],r['y'])for r in selected if r.get('x')is not None};added=0
   for y in range(m['height']*2):
    for x in range(m['width']*2):
     b=m['blocks'][y//2*m['width']+x//2];q=y%2*2+x%2
     if(b,q)in generic or(b,q,x,y)in pos:continue
     c=e.cell_info(cache,game,data,m['tileset'],b,q);art=explicit(c,x,y,m,data)
     if not art:held.append({'game':game,'map':name,'x':x,'y':y,'raw':c['tiles'],'collision':c['collision']});continue
     r={'game':game,'style':'gen3','map':name,'tileset':m['tileset'],'id':b,'quadrant':q,'x':x,'y':y,'sourceCells':[[x,y]],'sourceHash':c['sourceHash'],'sourceFiles':data['fingerprints'][m['tileset']],'sourceCollision':c['collision'],'sourcePriority':[bool(v.get('priority'))for v in c['attributes']],'sourcePalettes':[v.get('palette',1)for v in c['attributes']],'status':'candidate','evidence':'Complete native Gen3 public-room counterpart reviewed against the actual Johto desk, chair, plant, wall, directory or entrance. Source NPC seating, shop interactions, stair directions and warp positions remain unchanged.'};r.update(art);r['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,r,imp.packed,ROOT).tobytes());rows.append(r);added+=1
   stats.append({'game':game,'map':name,'added':added})
 grouped=defaultdict(list)
 for r in rows:grouped[r['game'],r['map'],r['id'],r['quadrant']].append(r)
 rows=[]
 for group in grouped.values():
  if len({json.dumps(artwork(r),sort_keys=True)for r in group})==1:
   r=group[0];r.pop('x');r.pop('y');r['sourceCells']=[z['sourceCells'][0]for z in group];rows.append(r)
  else:rows.extend(group)
 (out/'candidates.json').write_text(json.dumps(rows,indent=2));(out/'held.json').write_text(json.dumps(held,indent=2));print(json.dumps({'rows':len(rows),'held':len(held),'unique_held':list({tuple(z['raw'])for z in held}),'maps':len(stats)}))
 for name in('GOLDENROD_UNDERGROUND','ROUTE_29_ROUTE_46_GATE','ROUTE_35_NATIONAL_PARK_GATE'):preview.map_preview(cache,out,'crystal',name,'crystal-'+name,active+rows,imp.packed,2,ROOT)
 if a.validate:
  assert not held
  for r in rows:r['status']='reviewed'
  proof=e.validate_batch(rows,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=out),ROOT)
  for s in stats:
   v=preview.map_preview(cache,out,s['game'],s['map'],s['game']+'-'+s['map'],active+rows,imp.packed,1,ROOT);assert v['replaced_occurrences']==v['visible_cells']
  (out/'proof.json').write_text(json.dumps(proof,indent=2))
  if a.activate:write_rows(ROOT/'mappings/johto_gate_finish.lua',rows)
if __name__=='__main__':main()
