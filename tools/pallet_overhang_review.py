"""Restore additional native roofing above Pallet's unchanged buildings."""
import argparse,copy,json,os
from pathlib import Path
from types import SimpleNamespace
from PIL import Image
import catalog,preview,gen2_extended_review as e
from newbark_building_review import native_reference
from center_mart_overhang_review import write_rows
ROOT=Path(__file__).resolve().parents[1]

def source_cell(cache,game,data,tileset,bid,q):
 if game in e.GAMES:return e.cell_info(cache,game,data,tileset,bid,q)
 ts=data['sets'][tileset];sheet=data['sheets'].setdefault(tileset,Image.open(cache/game/ts['image']).convert('RGBA'));block=catalog.lua_array(catalog.dict_at(ts['blocks'],bid+1))
 data['fingerprints'][tileset]={'metadata':catalog.sha((cache/game/'data/generated/tilesets.lua').read_bytes()),'image':catalog.sha((cache/game/ts['image']).read_bytes()),'maps':catalog.sha((cache/game/'data/generated/maps.lua').read_bytes())}
 xx,yy=q%2*2,q//2*2;ids=[block[i]for i in(yy*4+xx,yy*4+xx+1,(yy+1)*4+xx,(yy+1)*4+xx+1)]
 return{'sourceHash':catalog.sha(preview.native_cell(sheet,ts,block,q).tobytes()),'attributes':[catalog.gb_tile(sheet,ts,t)[1]for t in ids],'collision':None}

def main():
 p=argparse.ArgumentParser();p.add_argument('--activate',action='store_true');args=p.parse_args()
 cache=Path(os.environ['APPDATA'])/'pokemon-love2d';out=ROOT.parent/'.work/tileshift-pallet-overhang';out.mkdir(exist_ok=True);active=e.active_rows(ROOT);packed={}
 stage=SimpleNamespace(cache=cache,catalog=ROOT.parent/'.work/tileshift-catalog',output=out)
 originals={};roofparts={}
 for name,dest,rect,cols,ys in(
  ('home','FR_PLAYERS_HOUSE_1F',(5,3,5,5),(0,1,2,3,4,5,8,9),(0,1,2,5)),
  ('lab','FR_OAKS_LAB',(13,9,7,5),(0,1,2,3,6,7,8,9,10,11,12,13),tuple(range(6)))):
  source,native=native_reference(stage,name,{'native':('firered','FR_PALLET_TOWN',dest,rect)},packed);parts={}
  for y,sy in enumerate(ys):
   for x,sx in enumerate(cols):
    gx,gy=native['pixel_origin'][0]+sx*8,native['pixel_origin'][1]+sy*8;mid=native['layout']['mids'][gy//16*native['layout']['width']+gx//16];rec=native['records'][mid]
    part={'donor':{'game':'firered','tileset':native['pair'],'id':mid,'hash':rec['pixel_sha256']},'layers':['over'],'layerHashes':{'over':rec['layer_sha256']['over']},'srcX':gx%16,'srcY':gy%16,'w':8,'h':8,'x':x%2*8,'y':y%2*8};parts.setdefault((x//2,y//2),[]).append(part)
  roofparts[name]=parts
 rows=[];roofs=[];proof=[]
 for game in('red','blue','yellow','gold','silver','crystal'):
  data=e.source(cache,game);m=data['maps']['PALLET_TOWN'];matching=[r for r in active if r['game']==game and r['tileset']==m['tileset']and r.get('map','PALLET_TOWN')=='PALLET_TOWN'];generic={(r['id'],r['quadrant']):r for r in matching if r.get('x')is None};positioned={(r['x'],r['y']):r for r in matching if r.get('x')is not None}
  for name,ox,oy,w,h,door in(('home',4,3,4,3,(5,5)),('home',12,3,4,3,(13,5)),('lab',10,8,6,4,(12,11))):
   assert any((v['x'],v['y'])==door for v in m['warps']);whole=Image.new('RGBA',(w*16,(h+1)*16))
   for dy in range(h+1):
    for dx in range(w):
     x,y=ox+dx,oy-1+dy;bid=m['blocks'][y//2*m['width']+x//2];q=y%2*2+x%2;c=source_cell(cache,game,data,m['tileset'],bid,q)
     r={'game':game,'style':'gen3','map':'PALLET_TOWN','tileset':m['tileset'],'id':bid,'quadrant':q,'x':x,'y':y,'sourceCells':[[x,y]],'sourceHash':c['sourceHash'],'sourceFiles':data['fingerprints'][m['tileset']],'sourceCollision':c['collision'],'sourcePriority':[bool(z.get('priority'))for z in c['attributes']],'sourcePalettes':[z.get('palette',1)for z in c['attributes']],'kind':'native_composite','role':'pallet_larger_'+name,'status':'reviewed','evidence':'Additional one-tile native roof overhang above the unchanged Pallet '+name+'. Complete FireRed roof panels and alpha outlines use native8px parts without scaling. Existing complete windows, awnings, entrance caps and door pixels stay in their approved world positions. Source doors, map layout, collision, actors and events unchanged.'}
     if r['sourceCollision']is None:r.pop('sourceCollision')
     if dy<(2 if name=='home'else 3):r['parts']=copy.deepcopy(roofparts[name][dx,dy])
     else:
      prior=positioned.get((x,y),generic.get((bid,q)));assert prior and prior.get('parts');r['parts']=copy.deepcopy(prior['parts'])
     if dy==0:r['buildingY']=oy
     else:
      prior=positioned.get((x,y),generic.get((bid,q)));assert prior
      r['base']=copy.deepcopy(prior.get('base'))
      if r['base']is None:r.pop('base')
     pixels=preview.replacement_image(cache,r,packed,ROOT);r['compositionPixelHash']=catalog.sha(pixels.tobytes());whole.paste(pixels,(dx*16,dy*16));(roofs if dy==0 else rows).append(r)
   stem=game+'-'+name+'-'+str(ox);whole.save(out/(stem+'.png'));proof.append({'game':game,'map':'PALLET_TOWN','kind':name,'rect':[ox,oy,w,h],'draw_origin':[ox,oy-1],'door':list(door),'image':stem+'.png','rgba_sha256':catalog.sha(whole.tobytes())})
 live=e.validate_batch(rows,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=out),ROOT)
 live_roofs=e.validate_batch(roofs,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=out),ROOT)
 (out/'proof.json').write_text(json.dumps({'instances':proof,'live':live,'live_roofs':live_roofs},indent=2)+'\n')
 if args.activate:
  for path in(ROOT/'mappings').glob('*.lua'):
   if path.name=='pallet_overhangs.lua':continue
   previous=preview.read_reviewed(path);keep=[r for r in previous if not(r.get('map')=='PALLET_TOWN'and r.get('x')is not None and any(ox<=r['x']<ox+w and oy<=r['y']<oy+h for ox,oy,w,h in((4,3,4,3),(12,3,4,3),(10,8,6,4))))]
   if len(keep)!=len(previous):write_rows(path,keep)
  write_rows(ROOT/'mappings/pallet_overhangs.lua',rows);write_rows(ROOT/'lib/pallet_roofs.lua',roofs)
 print(json.dumps({'buildings':len(proof),'rows':len(rows),'roofs':len(roofs),'live':live,'activated':args.activate}))
if __name__=='__main__':main()
