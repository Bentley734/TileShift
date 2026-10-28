"""All Gen1 source-map coverage and exact remaining-art contacts."""
import argparse,json,os
from collections import defaultdict
from pathlib import Path
import preview
from gen1_family_review import ROOT,GAMES,source,cell_info,identity,source_image
from gen2_cave_review import contact

def main():
 p=argparse.ArgumentParser();p.add_argument('--game',default='red',choices=GAMES);a=p.parse_args();cache=Path(os.environ['APPDATA'])/'pokemon-love2d';out=ROOT.parent/'.work/tileshift-gen1-finish-audit'/a.game;out.mkdir(exist_ok=True,parents=True);data=source(cache,a.game);active=[r for path in(ROOT/'mappings').glob('*.lua')for r in preview.read_reviewed(path)];unknown=defaultdict(dict);stats=[]
 for name,m in sorted(data['maps'].items()):
  if not isinstance(m,dict)or not m.get('tileset')or not m.get('width')or not m.get('height'):continue
  ts=m['tileset'];selected=[r for r in active if r['game']==a.game and r['tileset']==ts and r.get('map',name)==name];generic={(r['id'],r['quadrant'])for r in selected if r.get('x')is None};pos={(r['id'],r['quadrant'],r['x'],r['y'])for r in selected if r.get('x')is not None};remaining=0
  for y in range(m['height']*2):
   for x in range(m['width']*2):
    b=m['blocks'][y//2*m['width']+x//2];q=y%2*2+x%2
    if(b,q)in generic or(b,q,x,y)in pos:continue
    c=cell_info(cache,a.game,data,ts,b,q);key=identity(c);remaining+=1
    if key not in unknown[ts]:unknown[ts][key]={'seed':c,'contexts':[],'occurrences':0,'image':source_image(cache,a.game,data,c,m)}
    record=unknown[ts][key];record['occurrences']+=1
    if len(record['contexts'])<12:record['contexts'].append({'map':name,'xy':[x,y],'bid':b,'q':q})
  stats.append({'map':name,'tileset':ts,'total':m['width']*m['height']*4,'remaining':remaining})
 records={}
 for ts,group in unknown.items():
  values=sorted(group.values(),key=lambda z:-z['occurrences']);images=[]
  for n,z in enumerate(values):
   image=z.pop('image');z['number']=n;c=z['seed'];walk=''.join('1'if v else'0'for v in c['walkable_tiles']);images.append((str(n)+' '+str(c['tiles'])+' walk'+walk+' x'+str(z['occurrences'])+'\n'+z['contexts'][0]['map']+'\n'+str(z['contexts'][0]['xy']),image))
  records[ts]=values
  for start in range(0,len(images),35):contact(out/(ts+'-'+str(start//35)+'.png'),a.game.upper()+' '+ts+': exact original geometry and source walk/warp flags',images[start:start+35])
 (out/'remaining.json').write_text(json.dumps(records,indent=2));(out/'maps.json').write_text(json.dumps(stats,indent=2));print(json.dumps({'game':a.game,'maps':len(stats),'complete':sum(z['remaining']==0 for z in stats),'remaining_cells':sum(z['remaining']for z in stats),'families':{ts:{'unique':len(v),'cells':sum(z['occurrences']for z in v)}for ts,v in records.items()}}))
if __name__=='__main__':main()
