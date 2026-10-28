"""Keep whole original bench and whole public fountain at integer/native scale."""
import argparse,json,math
from pathlib import Path
from PIL import Image
import catalog
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('bench',type=Path);p.add_argument('atlas',type=Path);a=p.parse_args();im=Image.open(a.bench).convert('RGBA');im.putalpha(im.getchannel('A').point(lambda v:255 if v>=128 else 0));b=im.getbbox();factor=max(math.ceil((b[2]-b[0])/32),math.ceil((b[3]-b[1])/24));left=(b[0]+b[2])//2-16*factor;box=(left,b[3]-24*factor,left+32*factor,b[3]);sprite=im.crop(box).resize((32,24),Image.Resampling.NEAREST).quantize(colors=16,method=Image.Quantize.FASTOCTREE,dither=Image.Dither.NONE).convert('RGBA');sprite.putalpha(sprite.getchannel('A').point(lambda v:255 if v>=128 else 0));canvas=Image.new('RGBA',(32,32));canvas.paste(sprite,(0,8));folder=ROOT/'assets/original/park-bench';folder.mkdir(parents=True,exist_ok=True);files={}
 for q in range(4):
  path=folder/f'cell-{q}.png';canvas.crop((q%2*16,q//2*16,q%2*16+16,q//2*16+16)).save(path);files[path.name]=catalog.sha(path.read_bytes())
 (folder/'provenance.json').write_text(json.dumps({'origin':'Original Gen3-style outdoor park bench generated with built-in imagegen.','source_file':a.bench.name,'source_sha256':catalog.sha(a.bench.read_bytes()),'visible_bounds':b,'crop':box,'integer_reduction':factor,'final_size':[32,24],'canvas':[32,32],'all_visible_art_preserved':True,'files':files},indent=2)+'\n');canvas.resize((256,256),Image.Resampling.NEAREST).save(ROOT.parent/'.work/tileshift-johto-final-outdoors/bench-review.png')
 atlas=Image.open(a.atlas).convert('RGBA');folder=ROOT/'assets/third_party/metalflygon08';proof=json.loads((folder/'provenance.json').read_text());assert catalog.sha(a.atlas.read_bytes())==proof['atlas_sha256'];sprite=atlas.crop((84,3565,124,3610));assert sprite.getbbox()==(0,0,40,45);canvas=Image.new('RGBA',(64,64));canvas.paste(sprite,(12,9));new={}
 for y in range(4):
  for x in range(4):
   path=folder/f'park-fountain-{y}-{x}.png';canvas.crop((x*16,y*16,x*16+16,y*16+16)).save(path);new[path.name]=catalog.sha(path.read_bytes())
 proof['files'].update(new);proof['park_fountain']={'crop':[84,3565,124,3610],'native_size':[40,45],'scale':1,'canvas':[64,64],'position':[12,9],'complete_silhouette':True,'no_collision_or_event_changes':True};(folder/'provenance.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'bench_factor':factor,'fountain_files':len(new)}))
if __name__=='__main__':main()
