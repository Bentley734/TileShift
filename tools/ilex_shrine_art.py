"""Normalize an original generated forest shrine with integer-only reduction."""
import argparse,json,math
from pathlib import Path
from PIL import Image
import catalog
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);args=p.parse_args()
 source=Image.open(args.source).convert('RGBA');source.putalpha(source.getchannel('A').point(lambda a:255 if a>=128 else 0));b=source.getchannel('A').getbbox();factor=max(math.ceil((b[2]-b[0])/16),math.ceil((b[3]-b[1])/32));left=(b[0]+b[2])//2-factor*8;box=(left,b[3]-factor*32,left+factor*16,b[3]);assert box[0]<=b[0]and box[1]<=b[1]and box[2]>=b[2]
 sprite=source.crop(box).resize((16,32),Image.Resampling.NEAREST).quantize(colors=24,method=Image.Quantize.FASTOCTREE,dither=Image.Dither.NONE).convert('RGBA');assert set(sprite.getchannel('A').get_flattened_data())<={0,255}
 folder=ROOT/'assets/original/ilex-shrine';folder.mkdir(parents=True,exist_ok=True);files={}
 for name,im in(('shrine.png',sprite),('cell-0.png',sprite.crop((0,0,16,16))),('cell-1.png',sprite.crop((0,16,16,32)))):
  path=folder/name;im.save(path);files[name]=catalog.sha(path.read_bytes())
 proof={'origin':'Original artwork generated with built-in imagegen for the Ilex Forest wayside Celebi altar. Not a walk-in building.','source_file':args.source.name,'source_sha256':catalog.sha(args.source.read_bytes()),'source_size':source.size,'visible_bounds':b,'integer_reduction':factor,'crop':box,'final_size':[16,32],'binary_alpha':128,'colors':24,'dither':False,'all_visible_original_art_in_crop':True,'original_map_anchor':[8,22],'no_collision_or_event_changes':True,'files':files};(folder/'provenance.json').write_text(json.dumps(proof,indent=2)+'\n');sprite.resize((160,320),Image.Resampling.NEAREST).save(ROOT.parent/'.work/tileshift-johto-final-outdoors/ilex-shrine-review.png');print(json.dumps(proof))
if __name__=='__main__':main()
