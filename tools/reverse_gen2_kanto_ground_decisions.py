"""Review finite ordinary Kanto field/path joins in their actual contexts."""
import argparse,json
from PIL import Image,ImageDraw,ImageFont
import catalog,preview
from reverse_gen2_kanto_final import Final,DECISIONS,OUT

FIELDS=(189,190,191,197,199)
PATHS=(213,225,227,229)
FAMILIES={'general','pallet_outdoor','viridian_outdoor','pewter_outdoor','sevii_outdoor'}


def main():
 p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');a=p.parse_args()
 r=Final();r.remaining_inventory();r.stage();chosen=[]
 prior=json.loads(DECISIONS.read_text());owned={(x['game'],'gen2',x['pair'],x['mid'],None)for x in prior.get('native_modules',[])if x['feature'].startswith('ordinary_outdoor_')}
 for item in r.remaining:
  for s in item['sources']:
   if s['pair'].split('__')[0]not in FAMILIES or s['id']not in FIELDS+PATHS:continue
   key=s['game'],'gen2',s['pair'],s['id'],None
   if key in r.rows and key not in owned:continue
   assert s['layers']['over']==catalog.sha(bytes(1024))
   chosen.append(s)
 groups={}
 for s in chosen:groups.setdefault((s['rgba'],s['id']),[]).append(s)
 items=list(groups.values());font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',12)
 for start in range(0,len(items),12):
  canvas=Image.new('RGB',(1600,6*244),'#18212b');d=ImageDraw.Draw(canvas)
  for at,group in enumerate(items[start:start+12]):
   s=group[0];x,y=at%2*800,at//2*244;w=s['witnesses'][0];spec,layout=r.layouts[s['game'],w['map']]
   index=layout['mids'].index(s['id']);cx,cy=index%layout['width'],index//layout['width'];ctx=Image.new('RGBA',(112,112))
   for yy in range(7):
    for xx in range(7):
     tx,ty=cx+xx-3,cy+yy-3
     if 0<=tx<layout['width']and 0<=ty<layout['height']:
      mid=layout['mids'][ty*layout['width']+tx];c=r.imp.cell_index(s['game'])[spec['pair'],mid]
      im=preview.native_donor(r.cache,dict(game=s['game'],tileset=spec['pair'],id=mid,hash=c['pixel_sha256']),r.packed);ctx.paste(im,(xx*16,yy*16))
   im=preview.native_donor(r.cache,dict(game=s['game'],tileset=s['pair'],id=s['id'],hash=s['rgba']),r.packed)
   canvas.paste(im.resize((128,128),Image.Resampling.NEAREST),(x,y+32));canvas.paste(ctx.resize((224,224),Image.Resampling.NEAREST),(x+560,y+20))
   d.text((x,y),f"{start+at}: {s['pair']}/{s['id']} {w['map']}",font=font,fill='white')
   d.text((x+144,y+48),f"{len(group)} keys /{sum(z['count']for z in group)} cells",font=font,fill='white')
  canvas.save(OUT/f'ground-context-review-{start//12+1:02}.png')
 (OUT/'ground-context-review.json').write_text(json.dumps(items,indent=2)+'\n')
 print(json.dumps(dict(groups=len(items),keys=len(chosen),cells=sum(s['count']for s in chosen))))
 if not a.freeze:return
 decisions=json.loads(DECISIONS.read_text());records=[]
 for s in chosen:
  path=s['id']in PATHS;feature='ordinary_outdoor_open_path_join'if path else'ordinary_outdoor_open_field_variant'
  ref=r.gb_at('crystal','PALLET_TOWN',2,3)if path else r.gb_ref('crystal','PALLET_TOWN',1,0)
  art=r.native(ref,'classic_gen2_complete_'+feature);art['overMask']='0'*256
  records.append(dict(game=s['game'],pair=s['pair'],mid=s['id'],rgba=s['rgba'],behavior=s['behavior'],layers=s['layers'],feature=feature,art=art,
   evidence='Finite complete ordinary outdoor source family reviewed in the full route/town contexts and source-resolution contact atlas: '+feature+'. '
    'The source contains only ordinary nonencounter lawn scuffs/tufts or an open pale path/sand join with neighboring grass. The source primary General field/path art is separately scoped from indoor primary Building art. '
    'Use the complete corresponding original Crystal Kanto field/path material at1:1, coherently matching the already selected Pallet-style route terrain; the original classic path design is a full pale cell rather than the Gen3 blended yellow-green border. '
    'No tree, cliff face/cap, boulder, fence, soil plot, water/beach border, hop lip, doorway, arrow, stair or foreground object enters this selection. Native behavior, all source layer/alpha hashes, encounters, collisions, maps, NPCs and scripts stay unchanged.'))
 decisions['native_modules']=[x for x in decisions.get('native_modules',[])if not x['feature'].startswith('ordinary_outdoor_')]+records
 DECISIONS.write_text(json.dumps(decisions,indent=2)+'\n')


if __name__=='__main__':main()
