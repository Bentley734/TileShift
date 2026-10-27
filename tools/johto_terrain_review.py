"""Extend reviewed Johto terrain only where complete source pixels and movement match."""
import argparse,copy,json,os
from pathlib import Path
from types import SimpleNamespace
from PIL import Image,ImageDraw
import catalog,preview,gen2_extended_review as e
from newbark_building_review import lua
ROOT=Path(__file__).resolve().parents[1]
MAPS=('NEW_BARK_TOWN','CHERRYGROVE_CITY','VIOLET_CITY','AZALEA_TOWN','GOLDENROD_CITY','ECRUTEAK_CITY','OLIVINE_CITY','CIANWOOD_CITY','MAHOGANY_TOWN','BLACKTHORN_CITY','LAKE_OF_RAGE','NATIONAL_PARK','RUINS_OF_ALPH_OUTSIDE','ILEX_FOREST','SILVER_CAVE_OUTSIDE')+tuple('ROUTE_'+str(n)for n in range(29,47))

def main():
 p=argparse.ArgumentParser();p.add_argument('--activate',action='store_true');args=p.parse_args();cache=Path(os.environ['APPDATA'])/'pokemon-love2d';out=ROOT.parent/'.work/tileshift-johto-terrain';out.mkdir(exist_ok=True)
 active=[r for path in (ROOT/'mappings').glob('*.lua')if path.name!='johto_terrain.lua'for r in preview.read_reviewed(path)];rows=[];stats=[];packed={};contacts=[]
 for game in e.GAMES:
  data=e.source(cache,game);seeds={}
  for r in active:
   if r['game']==game and r.get('map')=='MAHOGANY_TOWN'and r['role'].startswith('mahogany_')and 'gate'not in r['role']:
    seeds.setdefault(e.identity(e.cell_info(cache,game,data,r['tileset'],r['id'],r['quadrant'])),r)
  for name in MAPS:
   assert name in data['maps'],name
   m=data['maps'][name]
   if m['tileset']not in e.SETS:continue
   selected=[r for r in active if r['game']==game and r['tileset']==m['tileset']and r.get('map',name)==name];generic={(r['id'],r['quadrant'])for r in selected if r.get('x')is None};positioned={(r['id'],r['quadrant'],r['x'],r['y'])for r in selected if r.get('x')is not None};count=0
   for j,bid in enumerate(m['blocks']):
    for q in range(4):
     x,y=j%m['width']*2+q%2,j//m['width']*2+q//2
     if (bid,q)in generic or(bid,q,x,y)in positioned:continue
     c=e.cell_info(cache,game,data,m['tileset'],bid,q);seed=seeds.get(e.identity(c))
     if seed is None:continue
     row=copy.deepcopy(seed);row.update(game=game,map=name,tileset=m['tileset'],id=bid,quadrant=q,x=x,y=y,sourceCells=[[x,y]],sourceHash=c['sourceHash'],sourceFiles=data['fingerprints'][m['tileset']],sourceCollision=c['collision'],sourcePriority=[bool(z.get('priority'))for z in c['attributes']],sourcePalettes=[z.get('palette',1)for z in c['attributes']],role='johto_terrain_'+seed['role'])
     row['reviewedSeed']={'map':seed['map'],'x':seed['x'],'y':seed['y'],'tileset':seed['tileset'],'id':seed['id'],'quadrant':seed['quadrant']};row['evidence']='Reviewed exact complete Johto terrain repeat in '+name+'. Entire original pixels, collision, palette slots and priority match the approved Mahogany directional terrain counterpart. No building, tree half, shore or other semantic family is inferred. Native one-way north walls remain north walls, not jump ledges; all encounters, source geometry and events remain original. Full native pixel rectangles remain unscaled.'
     rows.append(row);count+=1
   if count:
    stats.append({'game':game,'map':name,'added_cells':count})
    if game=='crystal':
     c=preview.map_preview(cache,out,game,name,name,active+rows,packed,1,ROOT);contacts.append((name,c))
 occurrences=len(rows);groups={}
 for row in rows:
  key=(row['game'],row['map'],row['tileset'],row['id'],row['quadrant'])
  if key in groups:groups[key]['sourceCells'].extend(row['sourceCells'])
  else:
   value=copy.deepcopy(row);value.pop('x');value.pop('y');groups[key]=value
 rows=list(groups.values())
 live=e.validate_batch(rows,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=out),ROOT)
 (out/'candidates.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');(out/'proof.json').write_text(json.dumps({'live':live,'maps':stats},indent=2),encoding='utf-8')
 width=1500;sheet=Image.new('RGB',(width,((len(contacts)+2)//3)*270),'#18202c');draw=ImageDraw.Draw(sheet)
 for n,(name,c)in enumerate(contacts):
  im=Image.open(out/(name+'-after-native.png')).convert('RGB');im.thumbnail((480,240),Image.Resampling.NEAREST);x=n%3*500;y=n//3*270;sheet.paste(im,(x,y+20));draw.text((x,y),name+f' {c["replaced_occurrences"]}/{c["visible_cells"]}',fill='white')
 sheet.save(out/'context-overview.png')
 if args.activate:
  text='-- Complete source-identity checked Johto terrain repeats.\nlocal rows={}\nlocal function add(batch)for _,r in ipairs(batch)do rows[#rows+1]=r end end\n'
  for i in range(0,len(rows),20):text+='add((function()return '+lua(rows[i:i+20])+' end)())\n'
  (ROOT/'mappings/johto_terrain.lua').write_text(text+'return rows\n',encoding='utf-8')
 print(json.dumps({'rows':len(rows),'new_cells':occurrences,'maps':len(stats),'live':live,'activated':args.activate}))
if __name__=='__main__':main()
