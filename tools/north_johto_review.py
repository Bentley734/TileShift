"""Complete Blackthorn and Lake of Rage with checked native terrain counterparts."""
import argparse,copy,json,os
from pathlib import Path
from types import SimpleNamespace
import catalog,preview,gen2_extended_review as e
from interior_review import Imports
from newbark_building_review import lua
ROOT=Path(__file__).resolve().parents[1]
MAPS=('BLACKTHORN_CITY','LAKE_OF_RAGE')
def main():
 p=argparse.ArgumentParser();p.add_argument('--activate',action='store_true');args=p.parse_args();cache=Path(os.environ['APPDATA'])/'pokemon-love2d';out=ROOT.parent/'.work/tileshift-north-johto';out.mkdir(exist_ok=True);imports=Imports(cache,ROOT.parent/'.work/tileshift-catalog');packed=imports.packed
 active=[r for path in(ROOT/'mappings').glob('*.lua')if path.name!='north_johto.lua'for r in preview.read_reviewed(path)];rows=[];stats=[]
 def ref(mid,pair='pewter_outdoor',game='firered'):
  c=imports.cell_index(game)[pair,mid];return {'game':game,'tileset':pair,'id':mid,'hash':c['pixel_sha256']}
 for game in e.GAMES:
  data=e.source(cache,game);water={};rock={}
  # Freshwater first, then the same approved rocky bank family for missing turns.
  for r in sorted(active,key=lambda r:r.get('map')!='ECRUTEAK_CITY'):
   if r['game']!=game or r['tileset']not in e.SETS:continue
   c=e.cell_info(cache,game,data,r['tileset'],r['id'],r['quadrant'])
   if c['collision']==41 and r.get('donor',{}).get('game')=='emerald'and r['donor']['tileset']=='general__petalburg'and r['donor']['id']in(368,392,393,394,400,402,408,410):water.setdefault(e.identity(c),r)
   if r.get('map')=='CIANWOOD_CITY'and r['role']=='cianwood_inward_rock_corner':rock.setdefault(e.identity(c),r)
  outcrops={q:next(r for r in active if r['game']==game and r.get('map')=='AZALEA_TOWN'and r['id']==10 and r['quadrant']==q)for q in range(4)}
  for name in MAPS:
   m=data['maps'][name];sel=[r for r in active if r['game']==game and r['tileset']==m['tileset']and r.get('map',name)==name];generic={(r['id'],r['quadrant'])for r in sel if r.get('x')is None};positioned={(r['id'],r['quadrant'],r['x'],r['y'])for r in sel if r.get('x')is not None};added=0
   for j,bid in enumerate(m['blocks']):
    for q in range(4):
     x,y=j%m['width']*2+q%2,j//m['width']*2+q//2
     if(bid,q)in generic or(bid,q,x,y)in positioned:continue
     c=e.cell_info(cache,game,data,m['tileset'],bid,q);identity=e.identity(c);seed=None
     if c['collision']==41:
      seed=water.get(identity);assert seed is not None,(game,name,x,y,c['tiles']);role='freshwater_pond_north_johto_'+str(seed['donor']['id'])
     elif bid==10:
      seed=outcrops[q];assert e.identity(c)==e.identity(e.cell_info(cache,game,data,seed['tileset'],seed['id'],seed['quadrant']));role='north_johto_whole_outcrop_'+str(q)
     elif identity in rock:seed=rock[identity];role='north_johto_complete_inward_cliff_turn'
     elif c['collision']==7 and c['tiles']in([76,76,61,76],[76,76,76,59]):role='north_johto_complete_inward_cliff_turn'
     elif c['collision']==123:
      assert name=='BLACKTHORN_CITY'and(x,y)in((20,1),(36,9))and c['tiles']==[70,71,86,87];role='north_johto_native_cave_entrance'
     else:raise AssertionError((game,name,bid,q,x,y,c['tiles'],c['collision']))
     r={'game':game,'style':'gen3','map':name,'tileset':m['tileset'],'id':bid,'quadrant':q,'sourceCells':[[x,y]],'sourceHash':c['sourceHash'],'sourceFiles':data['fingerprints'][m['tileset']],'sourceCollision':c['collision'],'sourcePriority':[bool(a.get('priority'))for a in c['attributes']],'sourcePalettes':[a.get('palette',1)for a in c['attributes']],'status':'reviewed','role':role}
     if seed:
      for field in('kind','donor','base','parts','animated','animation'):
       if field in seed:r[field]=copy.deepcopy(seed[field])
      r['reviewedSeed']={'map':seed.get('map'),'tileset':seed['tileset'],'id':seed['id'],'quadrant':seed['quadrant']}
      r['evidence']='Exact full source pixels, collision, palettes and priority match the independently approved counterpart. Complete32px land outcrops retain all four native FR104/106/120/122 quadrants; full native123/125 inward cliffs retain handedness. Freshwater uses one coherent eight-frame368/392/393/394/400/402/408/410 family, with no ocean grouping. All original movement, Surf/fishing, Headbutt, encounters, scripts and warps remain native.'
     elif role=='north_johto_complete_inward_cliff_turn':
      mid=123 if c['tiles'][2]==61 else 125;c3=imports.cell_index('firered')['pewter_outdoor',mid];r.update(kind='native_composite',base=copy.deepcopy(outcrops[0]['base']),parts=[{'donor':ref(mid),'layers':['mid'],'layerHashes':{'mid':c3['layer_sha256']['mid']},'srcX':0,'srcY':0,'x':0,'y':0,'w':16,'h':16}],evidence='Reviewed Blackthorn original inward cliff shape, with own current palette/priority fingerprint. Full native123/12516px inward turn retains original handedness; no side splicing, scaling or movement change.')
     else:
      r['donor']=ref(169,'general__rom_082d4af4');r['evidence']='Complete unscaled native FireRed MtMoon cave-mouth metatile169 at the original16px cave entrance. Full dark opening, rock jambs and threshold match the surrounding native124/121 cliff family. Dragon Den20,1 and Ice Path36,9 retain their original destinations and collision0x7b; no donor warp or mechanic imported.'
     if r.get('parts'):r['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,r,packed,ROOT).tobytes())
     rows.append(r);added+=1
   for x,y,dest in((20,1,'DRAGONS_DEN_1F'),(36,9,'ICE_PATH_1F'))if name=='BLACKTHORN_CITY'else():assert any(w['x']==x and w['y']==y and w['destMap']==dest for w in m['warps'])
   report=preview.map_preview(cache,out,game,name,game+'-'+name,active+rows,packed,2,ROOT);assert report['replaced_occurrences']==report['visible_cells']==1440;stats.append({'game':game,'map':name,'new_cells':added,'coverage':1440})
 groups={}
 for r in rows:
  key=(r['game'],r['map'],r['id'],r['quadrant'])
  if key in groups:groups[key]['sourceCells']+=r['sourceCells']
  else:groups[key]=r
 rows=list(groups.values());live=e.validate_batch(rows,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=out),ROOT);(out/'proof.json').write_text(json.dumps({'maps':stats,'rows':len(rows),'live':live},indent=2),encoding='utf-8')
 if args.activate:
  text='-- Complete native Blackthorn and Lake of Rage terrain, ponds and cave mouths.\nlocal rows={}\nlocal function add(batch)for _,r in ipairs(batch)do rows[#rows+1]=r end end\n'
  for i in range(0,len(rows),20):text+='add((function()return '+lua(rows[i:i+20])+' end)())\n'
  (ROOT/'mappings/north_johto.lua').write_bytes((text+'return rows\n').encode())
 print(json.dumps({'rows':len(rows),'maps':stats,'live':live,'activated':args.activate}))
if __name__=='__main__':main()
