"""Review Mt Silver's complete outdoor cliff family and freshwater geometry."""
import argparse,copy,json,os
from pathlib import Path
from types import SimpleNamespace
import catalog,preview,gen2_extended_review as e
from interior_review import Imports
from newbark_building_review import lua
ROOT=Path(__file__).resolve().parents[1]
NAME='SILVER_CAVE_OUTSIDE'
# Original Kanto artwork has its own tile IDs and proportions. These are
# explicitly reviewed shapes, not aliases inferred from passability.
FULL={(55,55,55,55):121,(36,36,36,36):114,(39,39,39,39):112,
 (39,54,54,55):120,(52,36,55,52):122,(55,19,19,39):125,
 (53,55,36,53):123,(1,1,17,17):105,(2,17,36,2):106,
 (17,30,30,39):104}
WATER={(51,51,51,20):392,(51,51,20,20):393,(51,51,20,84):394,
 (51,20,51,20):400,(20,84,20,84):402,(20,20,20,20):368,
 (20,51,20,20):410}
def main():
 p=argparse.ArgumentParser();p.add_argument('--activate',action='store_true');args=p.parse_args()
 cache=Path(os.environ['APPDATA'])/'pokemon-love2d';out=ROOT.parent/'.work/tileshift-silver-cave-outside';out.mkdir(exist_ok=True)
 imports=Imports(cache,ROOT.parent/'.work/tileshift-catalog');packed=imports.packed
 active=[r for path in(ROOT/'mappings').glob('*.lua')if path.name!='silver_cave_outside.lua'for r in preview.read_reviewed(path)]
 ground=next(r['base']for r in active if r.get('base',{}).get('tileset')=='general__petalburg'and r['base']['id']==1)
 rows=[];stats=[]
 def ref(mid,pair='pewter_outdoor',game='firered'):
  c=imports.cell_index(game)[pair,mid];return {'game':game,'tileset':pair,'id':mid,'hash':c['pixel_sha256']}
 def part(mid,sx,sy,x,y,w,h):
  c=imports.cell_index('firered')['pewter_outdoor',mid]
  return {'donor':ref(mid),'layers':['mid'],'layerHashes':{'mid':c['layer_sha256']['mid']},'srcX':sx,'srcY':sy,'x':x,'y':y,'w':w,'h':h}
 def half_front(mid,x=0,w=16):return [part(mid,x,0,x,8,w,4),part(mid,x,12,x,12,w,4)]
 for game in e.GAMES:
  data=e.source(cache,game);m=data['maps'][NAME];sel=[r for r in active if r['game']==game and r['tileset']==m['tileset']and r.get('map',NAME)==NAME]
  generic={(r['id'],r['quadrant'])for r in sel if r.get('x')is None};positioned={(r['id'],r['quadrant'],r['x'],r['y'])for r in sel if r.get('x')is not None};groups={}
  for j,bid in enumerate(m['blocks']):
   for q in range(4):
    x,y=j%m['width']*2+q%2,j//m['width']*2+q//2
    if(bid,q)in generic or(bid,q,x,y)in positioned:continue
    if(bid,q)in groups:groups[bid,q]['sourceCells'].append([x,y]);continue
    c=e.cell_info(cache,game,data,m['tileset'],bid,q);raw=tuple(c['tiles']);r={'game':game,'style':'gen3','map':NAME,'tileset':m['tileset'],'id':bid,'quadrant':q,'sourceCells':[[x,y]],'sourceHash':c['sourceHash'],'sourceFiles':data['fingerprints'][m['tileset']],'sourceCollision':c['collision'],'sourcePriority':[bool(a.get('priority'))for a in c['attributes']],'sourcePalettes':[a.get('palette',1)for a in c['attributes']],'status':'reviewed'}
    if c['collision']==41:
     mid=WATER[raw];seed=next(z for z in active if z['game']==game and z.get('map')in('BLACKTHORN_CITY','LAKE_OF_RAGE')and z.get('donor',{}).get('id')==mid and z['role'].startswith('freshwater_pond_'))
     r.update(donor=copy.deepcopy(seed['donor']),animated=True,animation=copy.deepcopy(seed.get('animation')),role='freshwater_pond_silver_cave_'+str(mid));r.pop('animation')if r['animation']is None else None
    elif c['collision']==123:
     assert(x,y)==(18,11)and raw==(72,73,88,89);assert any(w['x']==x and w['y']==y and w['destMap']=='SILVER_CAVE_ROOM_1'for w in m['warps']);r.update(donor=ref(169,'general__rom_082d4af4'),role='silver_cave_native_cave_entrance')
    elif raw==(70,71,86,87):
     assert c['collision']==7 and(x,y)==(17,13);seed=next(z for z in active if z['game']==game and z.get('map')=='PALLET_TOWN'and z['role']=='gen2_pallet_freestanding_sign');r.update({k:copy.deepcopy(seed[k])for k in('kind','donor','base','parts')if k in seed});r['role']='silver_cave_freestanding_sign'
    else:
     r.update(kind='native_composite',base=copy.deepcopy(ground),role='silver_cave_complete_cliff')
     if raw in FULL:
      assert c['collision']==(178 if raw==(1,1,17,17)else 7);r['parts']=[part(FULL[raw],0,0,0,0,16,16)]
     elif raw==(44,44,4,4):
      assert c['collision']==0;r.update(role='silver_cave_native_stair_threshold',parts=[copy.deepcopy(next(z for a in active for z in a.get('parts',[])if z['donor']['game']=='firered'and z['donor']['id']==137 and z.get('srcY')==8))])
     elif raw==(44,44,55,55):r['parts']=half_front(121)
     elif raw==(44,44,55,52):r['parts']=half_front(122)
     elif raw==(39,44,39,44):r['parts']=[part(112,0,0,0,0,8,16)]
     elif raw==(44,36,44,36):r['parts']=[part(114,8,0,8,0,8,16)]
     elif raw==(39,44,54,55):r['parts']=[part(120,0,0,0,0,8,16)]+half_front(121,8,8)
     elif raw==(44,36,55,52):r['parts']=[part(122,8,0,8,0,8,16)]+half_front(121,0,8)
     else:raise AssertionError((game,bid,q,x,y,c))
     if raw not in FULL and raw!=(44,44,4,4):assert c['collision']==7
    r['evidence']='Individually reviewed Mt Silver source shape and original full/half-cell footprint. Complete native FR104/105/106/112/114/120/121/122 cliffs retain handedness; full123/125 inward bends, no sideways splices. Half-height faces omit only repeated middle wall material and retain both complete silhouette edges. Collision0xb2 north rims remain north-blocking rock, never stairs or jump ledges. Original cave18,11, sign17,13, water, encounters, movement and scripts remain unchanged. Inland water uses one coherent animated Emerald bank family without ocean grouping. Native pixels stay unscaled.'
    if r.get('parts')or r.get('kind')=='original':r['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,r,packed,ROOT).tobytes())
    groups[bid,q]=r
  rows+=list(groups.values());report=preview.map_preview(cache,out,game,NAME,game+'-'+NAME,active+rows,packed,2,ROOT);assert report['replaced_occurrences']==report['visible_cells']==1440;stats.append({'game':game,'new_cells':sum(len(z['sourceCells'])for z in groups.values()),'coverage':1440})
 live=e.validate_batch(rows,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=out),ROOT);(out/'proof.json').write_text(json.dumps({'maps':stats,'rows':len(rows),'live':live},indent=2),encoding='utf-8');(out/'candidates.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
 if args.activate:
  text='-- Complete Mt Silver outdoor native terrain; original source mechanics retained.\nlocal rows={}\nlocal function add(batch)for _,r in ipairs(batch)do rows[#rows+1]=r end end\n'
  for i in range(0,len(rows),20):text+='add((function()return '+lua(rows[i:i+20])+' end)())\n'
  (ROOT/'mappings/silver_cave_outside.lua').write_bytes((text+'return rows\n').encode())
 print(json.dumps({'rows':len(rows),'maps':stats,'live':live,'activated':args.activate}))
if __name__=='__main__':main()
