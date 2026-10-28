"""Repeat newly reviewed complete terrain shapes in explicit Johto map contexts."""
import argparse,copy,json,os
from pathlib import Path
from types import SimpleNamespace
import catalog,preview,gen2_extended_review as e
from johto_terrain_review import MAPS
from newbark_building_review import lua
ROOT=Path(__file__).resolve().parents[1]
# Only independently identified inland water. Marine/mixed/unknown water
# contexts remain held; identical source pixels do not establish sea/lake use.
FRESH={'ROUTE_29','ROUTE_30','ROUTE_31','ROUTE_33','ROUTE_35','ROUTE_36',
 'ROUTE_37','ROUTE_38','ROUTE_39','ROUTE_42','ROUTE_43','ROUTE_44','ROUTE_45',
 'ROUTE_46','BLACKTHORN_CITY','LAKE_OF_RAGE','ECRUTEAK_CITY','VIOLET_CITY',
 'AZALEA_TOWN','MAHOGANY_TOWN'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--activate',action='store_true');args=p.parse_args()
 cache=Path(os.environ['APPDATA'])/'pokemon-love2d';out=ROOT.parent/'.work/tileshift-johto-terrain-repeats';out.mkdir(exist_ok=True)
 active=[r for path in(ROOT/'mappings').glob('*.lua')if path.name!='johto_terrain_repeats.lua'for r in preview.read_reviewed(path)]
 rows=[];stats=[];packed={}
 for game in e.GAMES:
  data=e.source(cache,game);seeds={}
  for r in active:
   if r['game']!=game or r.get('map')not in('BLACKTHORN_CITY','LAKE_OF_RAGE'):continue
   if not(r['role'].startswith('north_johto_whole_outcrop_')or r['role']=='north_johto_complete_inward_cliff_turn'or r['role'].startswith('freshwater_pond_north_johto_')):continue
   c=e.cell_info(cache,game,data,r['tileset'],r['id'],r['quadrant']);key=e.identity(c)
   if key in seeds:assert preview.replacement_image(cache,seeds[key],packed,ROOT).tobytes()==preview.replacement_image(cache,r,packed,ROOT).tobytes()
   seeds[key]=r
  for name in MAPS:
   m=data['maps'][name]
   if m['tileset']not in e.SETS:continue
   selected=[r for r in active if r['game']==game and r['tileset']==m['tileset']and r.get('map',name)==name]
   gen={(r['id'],r['quadrant'])for r in selected if r.get('x')is None};pos={(r['id'],r['quadrant'],r['x'],r['y'])for r in selected if r.get('x')is not None};groups={}
   for j,bid in enumerate(m['blocks']):
    for q in range(4):
     x,y=j%m['width']*2+q%2,j//m['width']*2+q//2
     if(bid,q)in gen or(bid,q,x,y)in pos:continue
     c=e.cell_info(cache,game,data,m['tileset'],bid,q);seed=seeds.get(e.identity(c))
     if seed is None or(c['collision']==41 and name not in FRESH):continue
     if(bid,q)in groups:groups[bid,q]['sourceCells'].append([x,y]);continue
     r={'game':game,'style':'gen3','map':name,'tileset':m['tileset'],'id':bid,'quadrant':q,'sourceCells':[[x,y]],'sourceHash':c['sourceHash'],'sourceFiles':data['fingerprints'][m['tileset']],'sourceCollision':c['collision'],'sourcePriority':[bool(a.get('priority'))for a in c['attributes']],'sourcePalettes':[a.get('palette',1)for a in c['attributes']],'status':'reviewed','role':('freshwater_pond_johto_repeat_'+str(seed['donor']['id']))if c['collision']==41 else'johto_repeat_'+seed['role'],'reviewedSeed':{'map':seed['map'],'id':seed['id'],'quadrant':seed['quadrant'],'tileset':seed['tileset']}}
     for field in('kind','donor','base','parts','animated','animation','compositionPixelHash'):
      if field in seed:r[field]=copy.deepcopy(seed[field])
     r['evidence']='Exact complete source pixels, collision, palette slots and priority match the reviewed Blackthorn/Lake of Rage counterpart. Scope is explicit Johto outdoor maps. Full32px outcrop quadrants and full16px inward cliffs retain their geometry and handedness. Only independently identified inland ponds use the coherent eight-frame freshwater bank family; marine, mixed and uncertain water contexts are held. No architecture, entrance, tree half or mechanic is inferred. Native maps, collisions, encounters, scripts and warps remain unchanged.'
     groups[bid,q]=r
   if groups:
    rows+=list(groups.values());report=preview.map_preview(cache,out,game,name,game+'-'+name,active+rows,packed,1,ROOT);stats.append({'game':game,'map':name,'added_cells':sum(len(r['sourceCells'])for r in groups.values()),'replaced':report['replaced_occurrences'],'total':report['visible_cells']})
 live=e.validate_batch(rows,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=out),ROOT)
 (out/'candidates.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');(out/'proof.json').write_text(json.dumps({'maps':stats,'live':live},indent=2),encoding='utf-8')
 if args.activate:
  text='-- Exact complete reviewed terrain repeats in explicit Johto contexts.\nlocal rows={}\nlocal function add(batch)for _,r in ipairs(batch)do rows[#rows+1]=r end end\n'
  for n in range(0,len(rows),20):text+='add((function()return '+lua(rows[n:n+20])+' end)())\n'
  (ROOT/'mappings/johto_terrain_repeats.lua').write_bytes((text+'return rows\n').encode())
 print(json.dumps({'rows':len(rows),'maps':stats,'live':live,'activated':args.activate}))
if __name__=='__main__':main()
