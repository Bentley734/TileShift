"""Review the National Park and its contest variant against complete Gen3 art."""
import argparse,copy,json,os
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
from PIL import Image
import catalog,preview,gen2_extended_review as e
from interior_review import Imports
from johto_remaining_review import artwork,gate96
from center_mart_overhang_review import write_rows
ROOT=Path(__file__).resolve().parents[1]
MAPS=('NATIONAL_PARK','NATIONAL_PARK_BUG_CONTEST')
def main():
 p=argparse.ArgumentParser();p.add_argument('--activate',action='store_true');a=p.parse_args();cache=Path(os.environ['APPDATA'])/'pokemon-love2d';out=ROOT.parent/'.work/tileshift-park';out.mkdir(exist_ok=True);imp=Imports(cache,ROOT.parent/'.work/tileshift-catalog');active=[r for path in(ROOT/'mappings').glob('*.lua')if path.name!='park.lua'for r in preview.read_reviewed(path)]
 def ref(game,pair,mid):
  rec=imp.cell_index(game)[pair,mid];return{'game':game,'tileset':pair,'id':mid,'hash':rec['pixel_sha256']}
 paving=ref('emerald','general__slateport',514);ground=ref('emerald','general__petalburg',1);water=next(r for r in active if r.get('donor',{}).get('id')==368 and r.get('animated'))
 def part(mid,sx,sy,w=8,h=8,x=0,y=0,game='firered',pair='general__rom_082d4af4',layers=None):
  v={'donor':ref(game,pair,mid),'srcX':sx,'srcY':sy,'w':w,'h':h,'x':x,'y':y}
  if layers:v.update(layers=layers,layerHashes={k:imp.cell_index(game)[pair,mid]['layer_sha256'][k]for k in layers})
  return v
 rows=[];unmatched=[]
 for game in e.GAMES:
  data=e.source(cache,game);closed={(r['x']-18,r['y']-28):r for r in active if r['game']==game and r.get('map')=='OLIVINE_CITY'and r['role']=='olivine_port_closed_front'};front={(r['x']-8,r['y']):r for r in active if r['game']==game and r.get('map')=='MAHOGANY_TOWN'and r['role']=='mahogany_north_gate'}
  special={};special.update(gate96(closed,front,34,14,False));special.update(gate96(closed,front,8,48,False))
  for name in MAPS:
   m=data['maps'][name]
   for y in range(m['height']*2):
    for x in range(m['width']*2):
     bid=m['blocks'][y//2*m['width']+x//2];q=y%2*2+x%2;c=e.cell_info(cache,game,data,m['tileset'],bid,q);raw=c['tiles'];r={'game':game,'style':'gen3','map':name,'tileset':m['tileset'],'id':bid,'quadrant':q,'x':x,'y':y,'sourceCells':[[x,y]],'sourceHash':c['sourceHash'],'sourceFiles':data['fingerprints'][m['tileset']],'sourceCollision':c['collision'],'sourcePriority':[bool(z.get('priority'))for z in c['attributes']],'sourcePalettes':[z.get('palette',1)for z in c['attributes']],'status':'reviewed','evidence':'National Park and separate Bug Contest map reviewed at original pixel scale. Original two grass permissions, inaccessible ornamental basin, bench collisions, paths, gates, item positions and contest events remain unchanged.'};art=None;role='park_native_material'
     if(x,y)in special:art=special[x,y];role='park_native_gate'
     elif bid==6:
      role='forest_whole_broadleaf_tree_'+str(q);art=artwork(next(z for z in active if z['role']==role));art['base']=ground
     elif c['collision']in(20,24)and not(12<=x<=23 and 14<=y<=23):
      seed=next(z for z in active if z['game']==game and z['role']=='tall_grass');art=artwork(seed);art['donor']=ref('emerald','general__petalburg',21 if c['collision']==20 else 13);role='tall_grass'
     elif bid in(14,):
      path=ROOT/'assets/original/park-bench'/('cell-'+str(q)+'.png');art={'kind':'original','asset':path.relative_to(ROOT).as_posix(),'assetFileHash':catalog.sha(path.read_bytes()),'base':paving};role='park_whole_bench_'+str(q)
     elif bid in(15,47)and c['collision']==7:
      art={'kind':'native_composite','base':paving,'parts':[part(650,0,0,16,16,pair='general__rom_082d4d94',layers=['mid'])]};role='park_litter_bin'
     elif raw==[69,70,85,86]:
      art={'kind':'native_composite','base':paving,'parts':[part(3,0,0,16,16,layers=['mid'])]};role='park_freestanding_sign'
     elif bid in(60,61,62):
      if q<2:
       art=artwork(next(z for z in active if z['game']==game and z['role']=='decorative_flower_northwest'));role='decorative_flower_northwest'
      else:art={'kind':'native_composite','base':paving,'parts':[part(588,0,8,16,8,game='emerald',pair='general__slateport')]};role='park_flowerbed_stone_curb'
     elif 16<=x<20 and 17<=y<21:
      path=ROOT/'assets/third_party/metalflygon08'/('park-fountain-'+str(y-17)+'-'+str(x-16)+'.png');art={'kind':'third_party','asset':path.relative_to(ROOT).as_posix(),'assetFileHash':catalog.sha(path.read_bytes()),'base':copy.deepcopy(water['donor']),'animated':True,'animation':copy.deepcopy(water['animation']),'credit':'MetalFlygon08','sourceUrl':'https://imgur.com/gallery/testing-out-gen-3-style-tiles-johto-6A43Cji'};role='freshwater_pond_park_fountain'
     elif set(raw)<={0,20,21}and 12<=x<=23 and 14<=y<=23:
      parts=[]
      for i,tile in enumerate(raw):
       if tile==0:parts.append(part(514,0,0,8,8,x=i%2*8,y=i//2*8,game='emerald',pair='general__slateport'))
       elif tile==21:parts.append(part(68,0,0,8,8,x=i%2*8,y=i//2*8))
      art={'kind':'native_composite','base':copy.deepcopy(water['donor']),'parts':parts,'animated':True,'animation':copy.deepcopy(water['animation'])};role='freshwater_pond_park_basin'
      if not parts:art={'kind':'native','donor':copy.deepcopy(water['donor']),'animated':True,'animation':copy.deepcopy(water['animation'])}
     elif c['collision']in(112,118,126):
      if c['collision']==112:art=artwork(next(z for z in active if z['game']==game and z['role']=='olivine_port_down_warp_marker'))
      else:art=artwork(next(z for z in active if z['game']==game and z['role']=='azalea_ilex_gate_side_entrance'and z.get('parts',[{}])[0].get('donor',{}).get('id')==(324 if y%2==0 else 332)))
      role='park_native_gate_marker'
     elif raw==[0,76,6,92]:art={'kind':'native','donor':paving}
     elif set(raw)<={0,1,2,5,6,22,27,35,36,37,38,43,51,52,53,54,67,83}:
      if set(raw)<={0,1,2,6,22}:art={'kind':'native','donor':ground if set(raw)<={1}else paving}
      elif raw in([35,36,51,52],[37,38,53,54]):art={'kind':'native_composite','base':paving,'parts':[part(231,0,0,16,16,layers=['mid'])]}
      else:
       parts=[]
       for i,tile in enumerate(raw):
        if tile not in(0,1,2,6):parts.append(part(244 if tile==5 else 231,0,i//2*8,8,8,x=i%2*8,y=i//2*8,layers=['mid']))
       art={'kind':'native_composite','base':paving,'parts':parts}
     if art is None:unmatched.append({'game':game,'map':name,'x':x,'y':y,'bid':bid,'q':q,'raw':raw,'collision':c['collision']});continue
     r.update(copy.deepcopy(art),role=role);r['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,r,imp.packed,ROOT).tobytes());rows.append(r)
 (out/'unmatched.json').write_text(json.dumps(unmatched,indent=2)+'\n')
 if unmatched:print(json.dumps({'unmatched':len(unmatched),'examples':unmatched[:25]}));return
 # Share identical checked cells within each supported map instead of carrying
 # thousands of duplicate recipes. Keep the unrelated Safari beta map scoped out.
 groups=defaultdict(list)
 for r in rows:groups[(r['game'],r['map'],r['tileset'],r['id'],r['quadrant'])].append(r)
 compact=[]
 for group in groups.values():
  if len({json.dumps(artwork(r),sort_keys=True)for r in group})==1 and len({r['role']for r in group})==1:
   r=copy.deepcopy(group[0]);r.pop('x');r.pop('y');r['sourceCells']=[list(p)for p in sorted({tuple(z['sourceCells'][0])for z in group})];compact.append(r)
  else:compact.extend(group)
 rows=compact
 live=e.validate_batch(rows,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=out),ROOT)
 for game in e.GAMES:
  for name in MAPS:
   proof=preview.map_preview(cache,out,game,name,game+'-'+name,active+rows,imp.packed,1,ROOT);assert proof['visible_cells']==proof['replaced_occurrences']
 if a.activate:write_rows(ROOT/'mappings/park.lua',rows)
 (out/'proof.json').write_text(json.dumps(live,indent=2)+'\n');print(json.dumps({'rows':len(rows),'live':live,'activated':a.activate}))
if __name__=='__main__':main()
