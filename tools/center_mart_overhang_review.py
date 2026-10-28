"""Full native Center/Mart features with one additional decorative roof row."""
import argparse,copy,json,os
from pathlib import Path
from types import SimpleNamespace
import catalog,preview,gen2_extended_review as e
from architecture_review import TEMPLATES
from newbark_building_review import native_reference,lua
ROOT=Path(__file__).resolve().parents[1]

def write_rows(path,rows):
 text='-- Reviewed, source-fingerprinted rows; no gameplay changes.\nlocal rows={}\nlocal function add(batch)for _,r in ipairs(batch)do rows[#rows+1]=r end end\n'
 for n in range(0,len(rows),20):text+='add((function()return '+lua(rows[n:n+20])+' end)())\n'
 path.write_bytes((text+'return rows\n').encode())

def main():
 p=argparse.ArgumentParser();p.add_argument('--activate',action='store_true');args=p.parse_args()
 cache=Path(os.environ['APPDATA'])/'pokemon-love2d';out=ROOT.parent/'.work/tileshift-center-mart-overhang';out.mkdir(exist_ok=True)
 active=e.active_rows(ROOT);instances={};old={}
 ground=copy.deepcopy(next(r['base']for r in active if r.get('base',{}).get('tileset')=='general__petalburg'and r['base']['id']==1))
 for r in active:
  if r['game']in e.GAMES and r['role']in('architecture_center','architecture_mart','larger_center','larger_mart'):
   key=r['game'],r['map'],r['role'].split('_')[-1];instances.setdefault(key,[]).append(r);old[r['game'],r['map'],r['x'],r['y']]=r
 stage=SimpleNamespace(cache=cache,catalog=ROOT.parent/'.work/tileshift-catalog',output=out)
 templates={};compact={};packed={}
 for name in('center','mart'):
  source,native=native_reference(stage,name,TEMPLATES[name],packed);parts={}
  row_sources=(0,1,2,3,4,6,6,5,6,7)if name=='center'else(0,1,1,1,2,3,4,5,6,7)
  for y,sy in enumerate(row_sources):
   for x in range(8):
    # Both8px columns of each shoulder need the plain lower roof panel.
    # Copying row1 into columns1/6 repeats their horizontal grey top caps.
    yy=2 if name=='mart'and y in(2,3)and x in(0,1,6,7)else sy
    sx=1 if name=='center'and y in(5,6)and 0<x<7 else x
    gx,gy=native['pixel_origin'][0]+sx*8,native['pixel_origin'][1]+yy*8
    mid=native['layout']['mids'][gy//16*native['layout']['width']+gx//16];rec=native['records'][mid]
    part={'donor':{'game':native['game'],'tileset':native['pair'],'id':mid,'hash':rec['pixel_sha256']},'srcX':gx%16,'srcY':gy%16,'x':x%2*8,'y':y%2*8,'w':8,'h':8}
    if y<2:part.update(layers=['over'],layerHashes={'over':rec['layer_sha256']['over']})
    parts.setdefault((x//2,y//2),[]).append(part)
  templates[name]=parts;compact[name]={}
  for y in range(8):
   for x in range(8):
    gx,gy=native['pixel_origin'][0]+x*8,native['pixel_origin'][1]+y*8;mid=native['layout']['mids'][gy//16*native['layout']['width']+gx//16];rec=native['records'][mid]
    part={'donor':{'game':native['game'],'tileset':native['pair'],'id':mid,'hash':rec['pixel_sha256']},'srcX':gx%16,'srcY':gy%16,'x':x%2*8,'y':y%2*8,'w':8,'h':8}
    if y<2:part.update(layers=['over'],layerHashes={'over':rec['layer_sha256']['over']})
    compact[name].setdefault((x//2,y//2),[]).append(part)
 rows=[];roofs=[];proof=[]
 for (game,map_id,name),prior in sorted(instances.items()):
  ox=min(r['x']for r in prior);oy=min(r['y']for r in prior);assert len(prior)==16
  data=e.source(cache,game);m=data['maps'][map_id];assert max(r['x']for r in prior)==ox+3 and max(r['y']for r in prior)==oy+3
  door=next(w for w in m['warps']if w['x']==ox+1 and w['y']==oy+3)
  whole=__import__('PIL.Image',fromlist=['Image']).new('RGBA',(64,80))
  for dy in range(5):
   for dx in range(4):
    x,y=ox+dx,oy-1+dy
    if y<0:continue
    bid=m['blocks'][y//2*m['width']+x//2];q=y%2*2+x%2;c=e.cell_info(cache,game,data,m['tileset'],bid,q)
    growth='two complete8px plain front-wall bands beneath the unchanged roof'if name=='center'else'two complete8px plain roofing bands'
    r={'game':game,'style':'gen3','map':map_id,'tileset':m['tileset'],'id':bid,'quadrant':q,'x':x,'y':y,'sourceCells':[[x,y]],'sourceHash':c['sourceHash'],'sourceFiles':data['fingerprints'][m['tileset']],'sourceCollision':c['collision'],'sourcePriority':[bool(z.get('priority'))for z in c['attributes']],'sourcePalettes':[z.get('palette',1)for z in c['attributes']],'kind':'native_composite','parts':copy.deepcopy(templates[name][dx,dy]),'role':'larger_'+name,'status':'reviewed','evidence':'Full native Emerald '+name+' at original pixel scale. Insert '+growth+', creating64x80 artwork with one decorative upper row. All original emblem, doorway, steps, sign and facade pixels retained unscaled. Native over-layer alpha exposes selected scenery outside the upper roof silhouette. Original entrance, events and collision unchanged.'}
    if dy==0:r['buildingY']=oy
    else:r['base']=copy.deepcopy(old[game,map_id,x,y].get('base')or ground)
    if r.get('base')is None:r.pop('base',None)
    if name=='center':
     if dy:
      r['buildingCompact']={'kind':'native_composite','parts':copy.deepcopy(compact[name][dx,dy-1])}
      if r.get('base'):r['buildingCompact']['base']=copy.deepcopy(r['base'])
     if dy>=2:
      path=ROOT/'assets/original/center-expanded'/('cell-'+str(dx)+'-'+str(dy)+'.png');h=catalog.sha(path.read_bytes())
      if dy==2:
       r['parts']=[p for p in r['parts']if p.get('y',0)==0]
       r['artOverlay']={'asset':path.relative_to(ROOT).as_posix(),'hash':h,'preserveRects':[[0,0,16,8]]}
      else:
       r.pop('parts');r.update(kind='original',asset=path.relative_to(ROOT).as_posix(),assetFileHash=h)
     r['evidence']='Original redesigned blue-glass, white-and-teal Gen3 clinic facade below the exact unscaled native40px roof. Expanded front includes complete upper windows, trim, sign and entrance surround. Original single entrance cell and all collisions unchanged. Native compact64x64 version is retained as a selectable alternative.'
    pixels=preview.replacement_image(cache,r,packed,ROOT);r['compositionPixelHash']=catalog.sha(pixels.tobytes());whole.paste(pixels,(dx*16,dy*16))
    (roofs if dy==0 else rows).append(r)
  whole.save(out/(game+'-'+map_id+'-'+name+'.png'));proof.append({'game':game,'map':map_id,'kind':name,'rect':[ox,oy,4,4],'draw_rect':[ox,oy-1,4,5],'door':[door['x'],door['y']],'destination':door['destMap'],'core_rgba_sha256':catalog.sha(whole.crop((0,16,64,80)).tobytes()),'full_rgba_sha256':catalog.sha(whole.tobytes())})
 live=e.validate_batch(rows+roofs,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=out),ROOT)
 (out/'proof.json').write_text(json.dumps({'instances':proof,'live':live},indent=2)+'\n')
 if args.activate:
  for path in(ROOT/'mappings').glob('*.lua'):
   if path.name=='building_overhangs.lua':continue
   previous=preview.read_reviewed(path);keep=[r for r in previous if not(r['game']in e.GAMES and r['role']in('architecture_center','architecture_mart','larger_center','larger_mart'))]
   if len(keep)!=len(previous):write_rows(path,keep)
  write_rows(ROOT/'mappings/building_overhangs.lua',rows);write_rows(ROOT/'lib/center_mart_roofs.lua',roofs)
 print(json.dumps({'buildings':len(instances),'core_rows':len(rows),'upper_rows':len(roofs),'live':live,'activated':args.activate}))
if __name__=='__main__':main()
