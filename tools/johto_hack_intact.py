"""Keep the Gold/Silver intact tower version using whole native FireGold art."""
import json,os,copy
from pathlib import Path
from collections import deque
from PIL import Image
import catalog,preview,gen2_extended_review as e
from types import SimpleNamespace
from center_mart_overhang_review import write_rows
ROOT=Path(__file__).resolve().parents[1]
def main():
 out=ROOT.parent/'.work/tileshift-firegold/intact';out.mkdir(exist_ok=True);donor=ROOT.parent/'.work/tileshift-firegold/firegold';meta=json.loads((donor/'catalog.json').read_text());m=next(m for m in meta['maps']if m['id']=='g43_m015');source=Image.open(donor/'maps/g43_m015-flat.png').convert('RGBA');raw=source.crop((19*16,8*16,26*16,12*16));colors=set()
 for x,y in[(19,7),(25,7),(19,12),(25,12)]:colors.update(source.crop((x*16,y*16,x*16+16,y*16+16)).get_flattened_data())
 for by in range(raw.height):
  for bx in (0,raw.width-1):colors.add(raw.getpixel((bx,by)))
 q=deque();bg=set();w,h=raw.size
 for y in range(h):
  for x in range(w):
   if(x==0 or y==0 or x==w-1 or y==h-1)and raw.getpixel((x,y))in colors:bg.add((x,y));q.append((x,y))
 while q:
  x,y=q.popleft()
  for dx,dy in[(1,0),(-1,0),(0,1),(0,-1)]:
   pt=x+dx,y+dy
   if 0<=pt[0]<w and 0<=pt[1]<h and pt not in bg and raw.getpixel(pt)in colors:bg.add(pt);q.append(pt)
 for rx,ry,rw,rh in[(0,0,8,64),(104,0,8,64),(8,48,8,16),(96,48,8,16)]:bg.update((px,py)for py in range(ry,ry+rh)for px in range(rx,rx+rw))
 for pt in bg:raw.putpixel(pt,(0,0,0,0))
 sprite=Image.new('RGBA',(112,80));sprite.paste(raw,(0,16));folder=ROOT/'assets/third_party/johto-hacks/intact';folder.mkdir(exist_ok=True);files={};refs={};url='https://www.pokecommunity.com/threads/pok%C3%A9mon-fire-gold-1-4.473130/'
 def save(name,im):
  path=folder/name;im.save(path);files[name]=catalog.sha(path.read_bytes());return {'kind':'third_party','asset':path.relative_to(ROOT).as_posix(),'assetFileHash':files[name],'credit':'FireGold 1.4 by Tzx211; user-supplied ROM','sourceUrl':url}
 save('intact.png',sprite)
 for y in range(5):
  for x in range(7):refs[x,y]=save(f'cell-{x}-{y}.png',sprite.crop((x*16,y*16,x*16+16,y*16+16)))
 (folder/'provenance.json').write_text(json.dumps({'rom_sha256':meta['rom_sha256'],'map':'g43_m015','crop_cells':[19,8,7,4],'source_door':[22,11],'target_origin_cells':[2,1],'target_door':[5,5],'scale':1,'reviewed_exterior_clear_rects':[[0,0,8,64],[104,0,8,64],[8,48,8,16],[96,48,8,16]],'transparent_top_padding':16,'processing':'Complete native FireGold intact tower; only connected exterior grass omitted. No shrinking or removed windows. Whole artwork uses two left decorative columns and one right column outside unchanged Gen2 footprint.','files':files},indent=2))
 cache=Path(os.environ['APPDATA'])/'pokemon-love2d';rows=preview.read_reviewed(ROOT/'mappings/ecruteak.lua');sides=preview.read_reviewed(ROOT/'lib/side_catalog.lua');sides=[r for r in sides if r['role']!='hack_intact_side'];changed=[];packed={}
 for r in rows:
  if r['game']not in('gold','silver')or r['role']!='ecruteak_original_intact':continue
  r.update(refs[r['x']-2,r['y']-1]);r.pop('assetPixelHash',None);r['evidence']='Whole unscaled FireGold intact tower counterpart preserves Gold/Silver exterior distinction and original entrance. Native side strips are decorative only.';r['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,r,packed,ROOT).tobytes());changed.append(r)
 for game in('gold','silver'):
  data=e.source(cache,game);m=data['maps']['ECRUTEAK_CITY']
  for x,cx,side in[(2,0,'left'),(3,1,'left'),(8,6,'right')]:
   for y in range(1,6):
    b=m['blocks'][y//2*m['width']+x//2];quad=y%2*2+x%2;c=e.cell_info(cache,game,data,m['tileset'],b,quad)
    r={'game':game,'style':'gen3','map':'ECRUTEAK_CITY','tileset':m['tileset'],'id':b,'quadrant':quad,'x':x,'y':y,'sourceX':x,'buildingX':4,'buildingY':1,'buildingW':4,'buildingH':5,'side':side,'sourceHash':c['sourceHash'],'sourceFiles':data['fingerprints'][m['tileset']],'sourceCollision':c['collision'],'sourcePriority':[bool(a.get('priority'))for a in c['attributes']],'sourcePalettes':[a.get('palette',1)for a in c['attributes']],'status':'reviewed','role':'hack_intact_side','evidence':'Native FireGold intact tower decorative eaves/window strips; transparent exterior grass leaves source terrain visible and no collision is added.',**refs[cx,y-1]};sides.append(r)
 print(e.validate_batch(changed,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=out),ROOT));write_rows(ROOT/'mappings/ecruteak.lua',rows);write_rows(ROOT/'lib/side_catalog.lua',sides)
 sprite.resize((448,320),Image.Resampling.NEAREST).save(out/'intact-review.png')
if __name__=='__main__':main()
