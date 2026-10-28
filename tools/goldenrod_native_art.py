"""Native-scale modular Johto buildings. Only public community pixels saved."""
import json
from pathlib import Path
from PIL import Image
import catalog
ROOT=Path(__file__).resolve().parents[1]

def remap(source,xs,ys):
 result=Image.new('RGBA',(len(xs),len(ys)))
 for y,sy in enumerate(ys):
  for x,sx in enumerate(xs):result.putpixel((x,y),source.getpixel((sx,sy)))
 return result

def build():
 atlas_path=ROOT.parent/'.work/tileshift-ecruteak-finish/johto-native-atlas.png'
 atlas=Image.open(atlas_path).convert('RGBA');art={};metadata={}
 # The entire40px parapet remains; only a whole plain16px module repeats.
 roof=atlas.crop((48,3344,128,3384));xs=list(range(64))+list(range(32,48))+list(range(64,80))
 im=Image.new('RGBA',(96,144));im.paste(remap(roof,xs,range(40)),(0,8))
 window=atlas.crop((64,3384,80,3416));brick=atlas.crop((96,3392,112,3408))
 for y in(48,80):
  im.paste(atlas.crop((48,3384,56,3416)),(0,y));im.paste(atlas.crop((120,3384,128,3416)),(88,y))
  for x in range(8,88,16):im.paste(window,(x,y))
 for y in(112,128):
  for x in range(0,96,16):im.paste(brick,(x,y))
 im.paste(atlas.crop((48,3384,56,3416)),(0,112));im.paste(atlas.crop((120,3384,128,3416)),(88,112))
 trim=atlas.crop((48,3420,128,3424));im.paste(remap(trim,list(range(8))+list(range(16,32))*5+list(range(72,80)),range(4)),(0,140))
 mart=atlas.crop((0,3388,48,3424))
 for y in range(36):
  for x in range(48):
   color=mart.getpixel((x,y))
   if color[3]or(16<=x<32 and 20<=y<36):im.putpixel((16+x,108+y),color)
 for y in(48,80):
  for x in range(8,88,16):assert im.crop((x,y,x+16,y+24)).tobytes()==window.crop((0,0,16,24)).tobytes()
 art['department']=im;metadata['department']={'source_roof':[48,3344,128,3384],'roof_columns':xs,'complete_windows':10,'door_anchor':[40,144],'top_transparent_rows':8,'size':[96,144]}
 # The original arch and every pillar/window remain complete. Repeat right
 # window units to fill the source width; move the whole arch to its warp.
 source=atlas.crop((0,2792,80,2864));im=Image.new('RGBA',(96,80))
 im.paste(remap(source,list(range(64))+list(range(32,48))+list(range(64,80)),range(32)),(0,8))
 xs=list(range(8))+list(range(24,56))+list(range(56,72))*3+list(range(72,80))
 im.paste(remap(source,xs,range(32,72)),(0,40));art['station']=im
 assert im.crop((8,40,40,80)).tobytes()==source.crop((24,32,56,72)).tobytes()
 metadata['station']={'source':[0,2792,80,2864],'complete_arch_preserved':True,'door_anchor':[24,80],'size':[96,80],'facade_columns':xs}
 # One-story closed houses: complete framed green roofing components plus
 # a full lower window/wall floor. No fragment of the omitted upper floor.
 source=atlas.crop((0,3264,80,3344));ys=list(range(8))+list(range(24,40))+list(range(56,80))
 for w in(32,48,64,80,96):
  units=[((8,24),(32,48),(56,72))[i%3]for i in range((w-16)//16)]
  xs=list(range(8))+[x for a,b in units for x in range(a,b)]+list(range(72,80))
  art['closed'+str(w)]=remap(source,xs,ys);metadata['closed'+str(w)]={'source':[0,3264,80,3344],'columns':xs,'rows':ys,'size':[w,48],'closed_no_door':True}
 xs=list(range(8))+list(range(8,24))+list(range(32,48))+list(range(56,80))
 art['closed_tall']=remap(source,xs,range(80));metadata['closed_tall']={'source':[0,3264,80,3344],'columns':xs,'size':[64,80],'closed_no_door':True}
 # Florist: whole striped canopy, doorway and window/planter modules.
 source=atlas.crop((32,3136,128,3200));xs=list(range(16))+list(range(32,48))+list(range(64,96));ys=list(range(8))+list(range(24,64))
 im=remap(source,xs,ys);art['florist']=im;metadata['florist']={'source':[32,3136,128,3200],'columns':xs,'rows':ys,'size':[64,48],'door_anchor':[24,48]}
 # Underground entrance: complete native striped canopy/opening32px high,
 # with a new flat stone roof assembled from full station edge components.
 source=atlas.crop((0,3112,48,3144))
 # The next atlas object starts at x32,y3136. It is not part of the hut.
 source.paste((0,0,0,0),(32,24,48,32));im=Image.new('RGBA',(64,48))
 im.paste(remap(atlas.crop((0,2792,80,2824)),list(range(32))+list(range(48,80)),list(range(8))+list(range(24,32))),(0,0))
 xs=list(range(40))+list(range(24,40))+list(range(40,48));im.paste(remap(source,xs,range(32)),(0,16))
 art['underground']=im;metadata['underground']={'complete_canopy_opening':[0,3112,48,3144],'size':[64,48],'door_anchor':[24,48]}
 # Radio Tower is modular: the entire narrow clock/lattice mast, a complete
 #40px dish, full fascia, whole window-floor units and full24px entrance.
 im=Image.new('RGBA',(64,192));im.paste(atlas.crop((16,2620,32,2704)),(8,12))
 for sx,dx in((0,0),(72,32)):im.paste(atlas.crop((sx,2680,sx+32,2720)),(dx,96))
 im.paste(atlas.crop((0,2720,32,2728)),(0,136));im.paste(atlas.crop((72,2720,104,2728)),(32,136))
 for x,sx in((0,0),(16,0),(32,80),(48,96)):im.paste(atlas.crop((sx,2728,sx+16,2752)),(x,144))
 xs=list(range(8))+list(range(40,72))+list(range(80,104));im.paste(remap(atlas.crop((0,2760,112,2784)),xs,range(24)),(0,168))
 assert im.crop((8,168,40,192)).tobytes()==atlas.crop((40,2760,72,2784)).tobytes()
 art['radio']=im;metadata['radio']={'mast':[16,2620,32,2704],'dish':[72,2680,104,2720],'complete_entrance':[40,2760,72,2784],'size':[64,192],'door_anchor':[24,192]}
 art['road']=atlas.crop((48,2928,64,2944));metadata['road']={'source':[48,2928,64,2944],'size':[16,16]}
 assert art['road'].getchannel('A').getextrema()==(255,255)
 art['rail']=atlas.crop((96,2824,112,2856));metadata['rail']={'source':[96,2824,112,2856],'size':[16,32]}
 crossing=Image.new('RGBA',(16,16));crossing.paste(art['rail'].crop((0,0,16,8)),(0,0));art['rail_crossing']=crossing;metadata['rail_crossing']={'source':[96,2824,112,2832],'size':[16,16],'transparent_below_rail':True}
 planter=Image.new('RGBA',(16,16));planter.paste(atlas.crop((32,3192,48,3200)),(0,8));art['planter']=planter;metadata['planter']={'container':[32,3192,48,3200],'size':[16,16]}
 folder=ROOT/'assets/third_party/metalflygon08';provenance=json.loads((folder/'provenance.json').read_text());assets={}
 for name,im in art.items():
  path=folder/(name+'.png');im.save(path);provenance['files'][path.name]=catalog.sha(path.read_bytes());assets[name]={}
  assert set(im.getchannel('A').get_flattened_data())<={0,255}
  for y in range(im.height//16):
   for x in range(im.width//16):
    crop=im.crop((x*16,y*16,x*16+16,y*16+16));p=folder/(name+'-cell-'+str(x)+'-'+str(y)+'.png');crop.save(p);h=catalog.sha(p.read_bytes());provenance['files'][p.name]=h;assets[name][x,y]={'asset':p.relative_to(ROOT).as_posix(),'assetFileHash':h}
  metadata[name].update(scale=1,rgba_sha256=catalog.sha(im.tobytes()))
 provenance['buildings']=metadata;(folder/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
 return art,assets,metadata
if __name__=='__main__':print(json.dumps(build()[2]))
