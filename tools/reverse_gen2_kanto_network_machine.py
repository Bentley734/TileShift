"""Inspect/freeze the complete unique Celio Network Machine.

Crystal's small healing/link terminals are not this regional Gen3 device.
The complete static source machine retains every coordinate/alpha/priority
pixel in four reviewed Crystal hardware shades. Only an explicitly reviewed
ordinary clinic-floor mask receives the selected native Crystal floor.
"""
from __future__ import annotations
import argparse
import json
from collections import Counter
from PIL import Image,ImageDraw
import catalog,preview
from reverse_gen2_kanto_final import Final,OUT,DECISIONS
from classic_geometry_review import art as classic_art

PALETTE=((247,230,214),(123,132,255),(74,74,255),(58,58,58))
# Literal shade decisions for the actual complete machine/wall/floor colors.
COLORS={
 (0,230,115):PALETTE[1],(58,115,140):PALETTE[2],(82,82,107):PALETTE[3],
 (99,156,165):PALETTE[2],(123,123,123):PALETTE[2],(132,181,206):PALETTE[1],
 (181,181,165):PALETTE[1],(181,214,230):PALETTE[0],(197,181,140):PALETTE[2],
 (214,206,156):PALETTE[1],(222,230,230):PALETTE[0],(230,140,99):PALETTE[2],
 (230,189,115):PALETTE[1],(230,222,156):PALETTE[0],(239,239,173):PALETTE[0],
 (247,239,165):PALETTE[0],(247,247,206):PALETTE[0],(255,181,0):PALETTE[1],
 (255,255,255):PALETTE[0],
}
FLOOR={(197,181,140),(214,206,156),(230,222,156),(239,239,173),(247,247,206)}
WALL={(247,239,165),(230,222,156),(230,140,99),(230,189,115)}


def main():
 args=argparse.ArgumentParser();args.add_argument('--freeze',action='store_true');args=args.parse_args()
 r=Final();spec,layout=r.layouts['firered','SEVII_ONE_ISLAND_POKECENTER']
 print('layout',layout['width'],layout['height'],spec['pair'])
 chosen=set()
 for y in range(0,8):
  print(y,layout['mids'][y*layout['width']:(y+1)*layout['width']])
 for y in range(1,6):
  for x in range(12,18):chosen.add(layout['mids'][y*layout['width']+x])
 chosen.add(837) # One extra lower-left foot/shadow cell completes the closed outline.
 images={};colors=Counter()
 for mid in sorted(chosen):
  c=r.imp.cell_index('firered')[spec['pair'],mid]
  images[mid]=preview.native_donor(r.cache,dict(game='firered',tileset=spec['pair'],id=mid,hash=c['pixel_sha256']),r.packed)
  mids,palette,planes=r.packed['firered',spec['pair']];slot=mids.index(mid)
  colors.update(p[:3]for name,blob in planes.items()for p in catalog.rgba_native(blob[slot*256:(slot+1)*256],palette,name!='under').get_flattened_data()if p[3])
 print('mids',sorted(chosen));print('colors',sorted(colors.items()))
 for mid in(641,695,675,703):
  c=r.imp.cell_index('firered')[spec['pair'],mid]
  im=preview.native_donor(r.cache,dict(game='firered',tileset=spec['pair'],id=mid,hash=c['pixel_sha256']),r.packed)
  print('floor',mid,sorted(set(im.get_flattened_data())))
 canvas=Image.new('RGB',(6*112,5*112),'#18212b');draw=ImageDraw.Draw(canvas)
 for n,mid in enumerate(sorted(chosen)):
  x,y=n%6*112,n//6*112;canvas.paste(images[mid].resize((96,96),Image.Resampling.NEAREST),(x,y+16));draw.text((x,y),str(mid),fill='white')
 canvas.save(OUT/'celio-network-machine-source-atlas.png')
 region=Image.new('RGBA',(6*16,5*16))
 for y in range(5):
  for x in range(6):region.paste(images[layout['mids'][(y+1)*layout['width']+x+12]],(x*16,y*16))
 region.resize((576,480),Image.Resampling.NEAREST).save(OUT/'celio-network-machine-source-whole.png')
 if not args.freeze:return
 decisions=json.loads(DECISIONS.read_text());records=[]
 masks_scene=Image.new('RGBA',(6*16,6*16),(0,0,0,255));result=masks_scene.copy()
 for game in r.games:
  gs,gl=r.layouts[game,'SEVII_ONE_ISLAND_POKECENTER'];assert gs['pair']=='network'
  floor=r.current[game,'gen2','network',641,None]['donor']
  wall=r.gb_at('crystal','VIRIDIAN_POKECENTER_1F',3,0)
  for mid in sorted(chosen):
   cell=r.imp.cell_index(game)['network',mid]
   preview.native_donor(r.cache,dict(game=game,tileset='network',id=mid,hash=cell['pixel_sha256']),r.packed)
   mids,palette,planes=r.packed[game,'network'];slot=mids.index(mid)
   images={name:catalog.rgba_native(blob[slot*256:(slot+1)*256],palette,name!='under')for name,blob in planes.items()}
   excluded=WALL if mid in(840,843)else FLOOR
   masks={name:''.join('1'if p[3]and p[:3]in excluded else'0'for p in im.get_flattened_data())for name,im in images.items()}
   masks={name:mask for name,mask in masks.items()if'1'in mask}
   ground=dict(donor=wall if mid in(840,843)else floor,masks=masks)if masks else None
   art=classic_art(r,game,'network',mid,'celio_network_machine',PALETTE,COLORS,
    role='classic_gen2_complete_unique_celio_network_machine',ground=ground)
   records.append(dict(game=game,pair='network',mid=mid,rgba=cell['pixel_sha256'],behavior=cell['behavior'],layers=cell['layer_sha256'],art=art,
    evidence='The complete unique Sevii Celio Network Machine is explicitly reviewed in OneIslandPokeCenter as a single96x96 maximum-envelope device, including its whole screen, closed housing, keyboard, vents, status lamps, side consoles and lower-left foot. '
     'Crystal has no complete native counterpart to this regional network device. Every original device pixel coordinate, outline, functional cue, alpha and priority remains intact in a documented four-color derivative using the original Crystal clinic hardware blue palette. '
     'Only literal per-plane masks of the independently reviewed warm floor/background pixels are replaced by the already selected native Crystal pink diamond clinic floor; the two top corners instead reveal the actual native clinic horizontal wall. '
     'Source colors alone never remove a blue/gray hardware pixel, green lamp, yellow status lamp, keyboard key or white device border. Complete source/layer/animation-manifest guards are frozen; original layouts, collision, NPCs, scripts, warps and source actor anchors remain unchanged.'))
   if game=='firered':
    for yy in range(6):
     for xx in range(6):
      if gl['mids'][(yy+1)*gl['width']+xx+12]!=mid:continue
      im=r.render(dict(art,game=game,style='gen2',tileset='network',id=mid,sourceHash=cell['pixel_sha256'],sourceBehavior=cell['behavior']));result.paste(im,(xx*16,yy*16));overlay=im.copy()
      union=[any(mask[i]=='1'for mask in masks.values())for i in range(256)]
      for i,v in enumerate(union):
       if v:overlay.putpixel((i%16,i//16),(255,0,255,255))
      masks_scene.paste(overlay,(xx*16,yy*16))
 decisions['geometry'] = [
  entry for entry in decisions.get('geometry', [])
  if entry['art']['classicGeometry']['feature'] != 'celio_network_machine'
 ] + records
 DECISIONS.write_text(json.dumps(decisions,indent=2)+'\n')
 result.resize((576,576),Image.Resampling.NEAREST).save(OUT/'celio-network-machine-four-color-review.png')
 masks_scene.resize((576,576),Image.Resampling.NEAREST).save(OUT/'celio-network-machine-floor-mask-review.png')
 print('frozen',len(records))


if __name__=='__main__':main()
