"""Replace generated Johto exteriors with checked CrystalDust native artwork."""
import argparse,copy,json,os,re
from pathlib import Path
from collections import deque
from types import SimpleNamespace
from PIL import Image
import catalog,preview,gen2_extended_review as e
from center_mart_overhang_review import write_rows
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'.work/tileshift-firegold/exteriors'
DONOR=ROOT.parent/'.work/tileshift-firegold/crystaldust'
ASSETS=ROOT/'assets/third_party/johto-hacks/exteriors'
URL='https://github.com/Sierraffinity/CrystalDust'
CREDIT='CrystalDust by Sierraffinity and contributors; user-supplied ROM'
BACKGROUND_MASKS={'closed': [[0, 0, 64, 9], [3, 9, 58, 1]], 'home': [[0, 0, 64, 9], [3, 9, 58, 1]], 'theater': [[0, 0, 80, 9], [3, 9, 74, 1]], 'bell': [[0, 75, 8, 28], [0, 107, 16, 21]], 'lighthouse': [[0, 128, 16, 1], [48, 128, 16, 1]]}
SPECS={
 'lighthouse':('g00_m002',(28,14,4,14),[(24,15),(27,26)],None),
 'closed':('g00_m001',(6,18,4,4),[(4,18),(6,22),(9,22)],None),
 'home':('g00_m001',(14,28,4,4),[(13,28),(14,32),(17,32)],None),
 'temple':('g00_m001',(18,12,6,4),[(17,12),(18,16),(23,16)],None),
 'theater':('g00_m001',(23,22,5,4),[(22,22),(23,26),(27,26)],None),
 'burned':('g00_m001',(6,6,4,4),[(6,10),(9,10)],None),
 'bell':('g00_m001',(37,4,6,8),[(36,4),(42,12)],None),
 'sprout':('g00_m000',(23,2,6,6),[(22,2),(23,8),(28,8)],None),
}

def main():
 a=argparse.ArgumentParser();a.add_argument('--activate',action='store_true');args=a.parse_args();OUT.mkdir(exist_ok=True,parents=True);ASSETS.mkdir(exist_ok=True,parents=True)
 meta=json.loads((DONOR/'catalog.json').read_text());files={};proof={};assets={}
 for name,(mid,box,grounds,_)in SPECS.items():
  x,y,w,h=box;source=Image.open(DONOR/'maps'/(mid+'-flat.png')).convert('RGBA');sprite=source.crop((x*16,y*16,(x+w)*16,(y+h)*16))
  colors=set()
  for gx,gy in grounds:colors.update(source.crop((gx*16,gy*16,gx*16+16,gy*16+16)).get_flattened_data())
  outside=set();q=deque();sw,sh=sprite.size
  for px in range(sw):
   for py in (0,sh-1):
    if sprite.getpixel((px,py))in colors:outside.add((px,py));q.append((px,py))
  for py in range(sh):
   for px in (0,sw-1):
    if sprite.getpixel((px,py))in colors and(px,py)not in outside:outside.add((px,py));q.append((px,py))
  while q:
   px,py=q.popleft()
   for dx,dy in((1,0),(-1,0),(0,1),(0,-1)):
    pt=(px+dx,py+dy)
    if 0<=pt[0]<sw and 0<=pt[1]<sh and pt not in outside and sprite.getpixel(pt)in colors:outside.add(pt);q.append(pt)
  for rx,ry,rw,rh in BACKGROUND_MASKS.get(name,[]):
   outside.update((px,py)for py in range(ry,ry+rh)for px in range(rx,rx+rw))
  original=sprite.copy()
  for pt in outside:sprite.putpixel(pt,(0,0,0,0))
  for pt in ((px,py)for py in range(sh)for px in range(sw)if(px,py)not in outside):assert sprite.getpixel(pt)==original.getpixel(pt)
  path=ASSETS/(name+'.png');sprite.save(path);files[path.name]=catalog.sha(path.read_bytes());sprite.resize((sw*3,sh*3),Image.Resampling.NEAREST).save(OUT/(name+'-review.png'))
  proof[name]={'map':mid,'box_cells':box,'ground_reference_cells':grounds,'reviewed_exterior_clear_rects':BACKGROUND_MASKS.get(name,[]),'source_flat_png_sha256':catalog.sha((DONOR/'maps'/(mid+'-flat.png')).read_bytes()),'transparent_ground_pixels':len(outside),'native_retained_pixels':sw*sh-len(outside),'pixel_scale':1,'rgba_sha256':catalog.sha(sprite.tobytes())}
  assets[name]={}
  for cy in range(h):
   for cx in range(w):
    cell=sprite.crop((cx*16,cy*16,cx*16+16,cy*16+16));path=ASSETS/(name+'-'+str(cx)+'-'+str(cy)+'.png');cell.save(path);files[path.name]=catalog.sha(path.read_bytes());assets[name][cx,cy]={'kind':'third_party','asset':path.relative_to(ROOT).as_posix(),'assetFileHash':files[path.name],'credit':CREDIT,'sourceUrl':URL}
 (ASSETS/'provenance.json').write_text(json.dumps({'origin':'Exact native pixel extraction from the user-supplied CrystalDust ROM; no generated pixels, scaling, redraw or imported ROM binary bundled. Exterior connected floor pixels omitted for source-room background transparency. Bell/Sprout upper stories naturally continue north beyond the Gen2 map boundary. Whole visible modules remain at native pixel size.','rom_name':meta['rom_name'],'rom_sha256':meta['rom_sha256'],'source':URL,'credit':CREDIT,'objects':proof,'files':files},indent=2))
 lookup={ref['asset']:(name,cx,cy)for name,cs in assets.items()for(cx,cy),ref in cs.items()}
 paths=[ROOT/'mappings/olivine.lua',ROOT/'mappings/ecruteak.lua',ROOT/'mappings/buildings_extended.lua'];allfiles={p:preview.read_reviewed(p)for p in paths};changed=[];cache=Path(os.environ['APPDATA'])/'pokemon-love2d';packed={}
 def change(r,name,cx,cy):
  if 'sourceCells'not in r:r['sourceCells']=[[r['x'],r['y']]]
  r.update(assets[name][cx,cy]);r.pop('assetPixelHash',None);r.pop('artOverlay',None);r.pop('parts',None);r.pop('donor',None);r['evidence']='Exact counterpart from user-supplied CrystalDust ROM, unscaled native pixels and checked extraction. Only exterior connected source-floor pixels are omitted. Original Gen2 collision, entrance, scripts and interactions remain unchanged.';r['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,r,packed,ROOT).tobytes());changed.append(r)
 for rows in allfiles.values():
  for r in rows:
   if r['game']in e.GAMES and r.get('asset')in lookup:change(r,*lookup[r['asset']]);continue
   if r['game']not in e.GAMES or not(r.get('asset')or r.get('artOverlay',{}).get('asset','')).startswith('assets/original/'):continue
   old=r.get('asset')or r['artOverlay']['asset'];match=re.search(r'cell-(\d+)-(\d+)\.png$',old)
   if not match:continue
   cx,cy=map(int,match.groups())
   if '/olivine-lighthouse/'in old:change(r,'lighthouse',cx,cy)
   elif '/bell-wide/'in old:change(r,'bell',cx,cy)
   elif '/ecruteak-v2/'in old:
    name=old.split('/')[-2]
    if name in assets:change(r,name,cx+(1 if name=='theater'else 0),cy)
   elif '/sprout-tower/'in old:change(r,'sprout',cx+1,cy+1)
 roofs=[r for r in preview.read_reviewed(ROOT/'lib/roof_catalog.lua')if r['role']!='hack_native_building_overhang'];sides=[r for r in preview.read_reviewed(ROOT/'lib/side_catalog.lua')if r['role']!='hack_native_building_overhang']
 for r in roofs:
  if r['game']in e.GAMES and r.get('asset')in lookup:change(r,*lookup[r['asset']]);continue
  if r['game']not in e.GAMES:continue
  old=r.get('asset','');match=re.search(r'cell-(\d+)-(\d+)\.png$',old)
  if not match:continue
  cx,cy=map(int,match.groups())
  if '/ecruteak-v2/'in old:
   name=old.split('/')[-2]
   if name in assets:change(r,name,cx+(1 if name=='theater'else 0),cy)
  elif '/sprout-tower/'in old:change(r,'sprout',cx+1,cy)
 for r in sides:
  if r['game']in e.GAMES and r.get('asset')in lookup:change(r,*lookup[r['asset']]);continue
  if r['game']in e.GAMES and '/bell-wide/'in r.get('asset',''):
   cx,cy=map(int,re.search(r'cell-(\d+)-(\d+)\.png$',r['asset']).groups());change(r,'bell',cx,cy)
 for game in e.GAMES:
  data=e.source(cache,game)
  def decorate(mapname,x,y,bx,by,bw,bh,side,name,cx,cy,top=False):
   m=data['maps'][mapname];sx=max(0,min(m['width']*2-1,x));b=m['blocks'][y//2*m['width']+sx//2];quad=y%2*2+sx%2;c=e.cell_info(cache,game,data,m['tileset'],b,quad)
   r={'game':game,'style':'gen3','map':mapname,'tileset':m['tileset'],'id':b,'quadrant':quad,'x':x,'y':y,'sourceHash':c['sourceHash'],'sourceFiles':data['fingerprints'][m['tileset']],'sourceCollision':c['collision'],'sourcePriority':[bool(a.get('priority'))for a in c['attributes']],'sourcePalettes':[a.get('palette',1)for a in c['attributes']],'status':'reviewed','role':'hack_native_building_overhang','buildingY':by}
   if side:r.update(side=side,sourceX=sx,buildingX=bx,buildingW=bw,buildingH=bh)
   change(r,name,cx,cy);(roofs if top else sides).append(r)
  for yy in range(1,6):
   for side,x,cx in [('left',21,0),('right',26,5)]:decorate('VIOLET_CITY',x,yy,22,1,4,5,side,'sprout',cx,yy)
  for x,cx in[(21+i,i)for i in range(6)]:decorate('VIOLET_CITY',x,0,22,1,4,5,None,'sprout',cx,0,True)
  for yy in range(19,22):decorate('ECRUTEAK_CITY',21,yy,22,19,4,3,'left','theater',0,yy-18)
  decorate('ECRUTEAK_CITY',21,18,22,19,4,3,None,'theater',0,0,True)
 # Merge the independently reviewed expanded Center decorative cells.
 centers=ROOT.parent/'.work/tileshift-firegold/centers'
 roofcenter=json.loads((centers/'roof-replacements.json').read_text());sidecenter=json.loads((centers/'left-side-additions.json').read_text())
 centerroofs=preview.read_reviewed(ROOT/'lib/center_mart_roofs.lua')
 centerroofs=[r for r in centerroofs if not(r['game']in e.GAMES and r['role']=='larger_center')]+roofcenter
 sides=[r for r in sides if not(r['game']in e.GAMES and r['role']=='larger_center')]+sidecenter
 e.validate_batch([r for r in changed if not r.get('side')],SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=OUT),ROOT)
 active=[r for p in(ROOT/'mappings').glob('*.lua')for r in allfiles.get(p,preview.read_reviewed(p))]
 more=centerroofs+[r for name in('goldenrod_roofs','pallet_roofs')for r in preview.read_reviewed(ROOT/'lib'/(name+'.lua'))]
 for mapname in('OLIVINE_CITY','ECRUTEAK_CITY','VIOLET_CITY'):
  preview.map_preview(cache,OUT,'crystal',mapname,'crystal-'+mapname,active,packed,2,ROOT,roof_rows=roofs+sides+more)
 (OUT/'proof.json').write_text(json.dumps({'changed_rows':len(changed),'roof_rows':len(roofs),'side_rows':len(sides),'objects':proof},indent=2))
 if args.activate:
  for p,rows in allfiles.items():write_rows(p,rows)
  write_rows(ROOT/'lib/roof_catalog.lua',roofs);write_rows(ROOT/'lib/side_catalog.lua',sides);write_rows(ROOT/'lib/center_mart_roofs.lua',centerroofs)
 print('Reviewed',len(changed),'exterior cells')
if __name__=='__main__':main()
