"""Proposal-only ordinary floor variants with independently checked8px glyphs.

Targets must use only whole8px glyphs from one same-pair reviewed floor,
have no native OVER and be walkable at every actual logical layout use.
No candidate is adopted until its complete room context is reviewed.
"""
import argparse,json,struct,zlib
from collections import defaultdict
from PIL import Image,ImageDraw,ImageFont
import catalog,preview
from reverse_gen2_kanto_final import Final,OUT,previous


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--allow-flat',action='store_true');parser.add_argument('--mixed-walkability',action='store_true');parser.add_argument('--walls',action='store_true');args=parser.parse_args()
 prefix='wall-glyph'if args.walls else'floor-mixed'if args.mixed_walkability else'floor-flat'if args.allow_flat else'floor-glyph'
 expected_walkable=not args.walls
 def material_role(role):
  if not args.walls:return previous.plain_floor(role)
  return 'wall'in role and not any(v in role for v in('corner','cap','glyph','window','door','end','inward','overhang','border','foot','side','ledge','partition','roof'))
 r=Final();r.remaining_inventory();r.stage();packed={};images={};profiles=defaultdict(set)
 for(game,name),(spec,layout)in r.layouts.items():
  raw=(r.cache/game/'data/generated/gba/native'/spec['file']).read_bytes();raw=raw if raw[:4]==b'SVML'else zlib.decompress(raw)
  pw,ph,w,h=struct.unpack_from('<HHHH',raw,6);w=w or pw;h=h or ph;offset=16+raw[14]*raw[15]*2
  for y in range(h):
   for x in range(w):
    p=offset+(y*pw+x)*4;mid=int.from_bytes(raw[p:p+2],'little');profiles[game,spec['pair'],mid].add(bool(r.imp.permissions.isWalkable(raw[p+2])))
 def original(game,pair,mid):
  key=game,pair,mid
  if key not in images:
   c=r.imp.cell_index(game)[pair,mid];images[key]=preview.native_donor(r.cache,dict(game=game,tileset=pair,id=mid,hash=c['pixel_sha256']),r.packed)
  return images[key]
 def glyphs(game,pair,mid):
  im=original(game,pair,mid);out=[]
  for q in range(4):
   lookup={};pixels=im.crop((q%2*8,q//2*8,q%2*8+8,q//2*8+8)).get_flattened_data()
   values=bytes(lookup.setdefault(p,len(lookup))for p in pixels)
   if len(lookup)<2 and not args.allow_flat:return None
   out.append(catalog.sha(values))
  return frozenset(out)
 floors=defaultdict(list);empty=catalog.sha(bytes(1024))
 for key,row in r.current.items():
  game,style,pair,mid,map_id=key
  if map_id is not None or not row.get('donor')or row['donor'].get('game')!='crystal'or not material_role(row.get('role','')):continue
  if(game,pair,mid)not in r.usage or(expected_walkable not in profiles[game,pair,mid]if args.mixed_walkability else profiles[game,pair,mid]!={expected_walkable}):continue
  cell=r.imp.cell_index(game)[pair,mid]
  if cell['layer_sha256']['over']!=empty:continue
  patterns=glyphs(game,pair,mid)
  if patterns:floors[game,pair].append((patterns,row))
 proposals=[]
 for group in r.remaining:
  for s in group['sources']:
   key=s['game'],'gen2',s['pair'],s['id'],None
   if key in r.rows or s['layers']['over']!=empty or(expected_walkable not in profiles[s['game'],s['pair'],s['id']]if args.mixed_walkability else profiles[s['game'],s['pair'],s['id']]!={expected_walkable}):continue
   patterns=glyphs(s['game'],s['pair'],s['id'])
   if not patterns:continue
   choices=[row for known,row in floors[s['game'],s['pair']]if patterns<=known and(not args.allow_flat or row.get('sourceBehavior')==s['behavior'])]
   outputs=defaultdict(list)
   for row in choices:outputs[row.get('compositionPixelHash')or catalog.sha(r.render(row).tobytes())].append(row)
   if len(outputs)!=1:continue
   canonical=min(next(iter(outputs.values())),key=lambda row:row['id'])
   proposals.append(dict(target=s,canonical=dict(game=canonical['game'],pair=canonical['tileset'],mid=canonical['id']),
    canonical_row_sha256=catalog.sha(previous.stable(canonical).encode()),role=canonical.get('role',''),output=next(iter(outputs))))
 grouped=defaultdict(list)
 for p in proposals:grouped[p['target']['rgba'],p['target']['layers']['under'],p['output']].append(p)
 items=list(grouped.values());items.sort(key=lambda g:-sum(p['target']['count']for p in g))
 (OUT/(prefix+'-proposals.json')).write_text(json.dumps(items,indent=2)+'\n')
 font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',12)
 for start in range(0,len(items),12):
  canvas=Image.new('RGB',(1600,6*244),'#18212b');d=ImageDraw.Draw(canvas)
  for at,g in enumerate(items[start:start+12]):
   p=g[0];s=p['target'];x,y=at%2*800,at//2*244;w=s['witnesses'][0];spec,layout=r.layouts[s['game'],w['map']]
   index=layout['mids'].index(s['id']);cx,cy=index%layout['width'],index//layout['width'];ctx=Image.new('RGBA',(112,112))
   for yy in range(7):
    for xx in range(7):
     tx,ty=cx+xx-3,cy+yy-3
     if 0<=tx<layout['width']and 0<=ty<layout['height']:ctx.paste(original(s['game'],spec['pair'],layout['mids'][ty*layout['width']+tx]),(xx*16,yy*16))
   im=original(s['game'],s['pair'],s['id']);old=r.current[p['canonical']['game'],'gen2',p['canonical']['pair'],p['canonical']['mid'],None]
   canvas.paste(im.resize((96,96),Image.Resampling.NEAREST),(x,y+32));canvas.paste(r.render(old).resize((96,96),Image.Resampling.NEAREST),(x+104,y+32));canvas.paste(ctx.resize((224,224),Image.Resampling.NEAREST),(x+560,y+20))
   d.text((x,y),f"{start+at}: {s['pair']}/{s['id']} {w['map']}",font=font,fill='white')
   d.text((x,y+140),f"{len(g)} keys /{sum(z['target']['count']for z in g)} cells",font=font,fill='white');d.text((x,y+164),p['role'],font=font,fill='white')
  canvas.save(OUT/f'{prefix}-context-review-{start//12+1:02}.png')
 print(json.dumps(dict(groups=len(items),keys=len(proposals),cells=sum(p['target']['count']for p in proposals))))


if __name__=='__main__':main()
