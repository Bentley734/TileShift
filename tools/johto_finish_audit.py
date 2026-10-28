"""Authoritative Johto membership and remaining source-art contacts."""
import argparse,json,os
from collections import defaultdict,Counter
from pathlib import Path
import catalog,preview,gen2_extended_review as e
from gen2_cave_review import contact,source_image
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--game',default='crystal',choices=e.GAMES);a=p.parse_args();cache=Path(os.environ['APPDATA'])/'pokemon-love2d';out=ROOT.parent/'.work/tileshift-johto-finish-audit'/a.game;out.mkdir(exist_ok=True,parents=True);data=e.source(cache,a.game);active=e.active_rows(ROOT);landmarks=catalog.read_lua(cache/a.game/'data/generated/landmarks.lua')['landmarks'];limit=landmarks['LANDMARK_PALLET_TOWN']['index'];unknown=defaultdict(dict);stats=[]
 for name,m in sorted(data['maps'].items()):
  if not isinstance(m,dict)or not 0<m.get('landmark',999)<limit:continue
  ts=m['tileset'];selected=[r for r in active if r['game']==a.game and r['tileset']==ts and r.get('map',name)==name];generic={(r['id'],r['quadrant'])for r in selected if r.get('x')is None};pos={(r['id'],r['quadrant'],r['x'],r['y'])for r in selected if r.get('x')is not None};remaining=0
  for y in range(m['height']*2):
   for x in range(m['width']*2):
    bid=m['blocks'][y//2*m['width']+x//2];q=y%2*2+x%2
    if(bid,q)in generic or(bid,q,x,y)in pos:continue
    c=e.cell_info(cache,a.game,data,ts,bid,q);key=e.identity(c);remaining+=1
    if key not in unknown[ts]:unknown[ts][key]={'seed':c,'contexts':[],'occurrences':0,'image':source_image(cache,a.game,data,c,m)}
    r=unknown[ts][key];r['occurrences']+=1
    if len(r['contexts'])<10:r['contexts'].append({'map':name,'xy':[x,y],'bid':bid,'q':q})
  stats.append({'map':name,'tileset':ts,'landmark':m['landmark'],'total':m['width']*m['height']*4,'remaining':remaining})
 records={}
 for ts,group in unknown.items():
  values=sorted(group.values(),key=lambda z:-z['occurrences']);images=[]
  for i,z in enumerate(values):
   im=z.pop('image');z['number']=i;c=z['seed'];images.append((str(i)+' '+str(c['tiles'])+' col'+str(c['collision'])+' x'+str(z['occurrences'])+'\n'+z['contexts'][0]['map']+'\n'+str(z['contexts'][0]['xy']),im))
  records[ts]=values
  for start in range(0,len(images),35):contact(out/(ts+'-'+str(start//35)+'.png'),a.game.upper()+' '+ts+': original remaining artwork, flags and actual contexts',images[start:start+35])
 (out/'remaining.json').write_text(json.dumps(records,indent=2));(out/'maps.json').write_text(json.dumps(stats,indent=2));print(json.dumps({'game':a.game,'maps':len(stats),'complete':sum(z['remaining']==0 for z in stats),'remaining_cells':sum(z['remaining']for z in stats),'families':{ts:{'unique':len(v),'cells':sum(z['occurrences']for z in v)}for ts,v in records.items()}}))
if __name__=='__main__':main()
