"""Normalize original transparent foam and animate using exact quarter turns."""
import argparse,json,math
from pathlib import Path
from PIL import Image
import catalog
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);a=p.parse_args();im=Image.open(a.source).convert('RGBA');im.putalpha(im.getchannel('A').point(lambda v:255 if v>=128 else 0));b=im.getbbox();factor=math.ceil(max(b[2]-b[0],b[3]-b[1])/16);cx,cy=(b[0]+b[2])//2,(b[1]+b[3])//2;box=(cx-factor*8,cy-factor*8,cx+factor*8,cy+factor*8)
 sprite=im.crop(box).resize((16,16),Image.Resampling.NEAREST).quantize(colors=8,method=Image.Quantize.FASTOCTREE,dither=Image.Dither.NONE).convert('RGBA');sprite.putalpha(sprite.getchannel('A').point(lambda v:255 if v>=128 else 0));folder=ROOT/'assets/original/whirlpool';folder.mkdir(parents=True,exist_ok=True);files={}
 for frame in range(8):
  tile=sprite.rotate(-90*(frame//2),resample=Image.Resampling.NEAREST);path=folder/f'foam-{frame}.png';tile.save(path);files[path.name]=catalog.sha(path.read_bytes())
 proof={'origin':'Original transparent whirlpool foam generated with built-in imagegen. Native ocean remains visible through the spiral.','source_file':a.source.name,'source_sha256':catalog.sha(a.source.read_bytes()),'source_size':im.size,'visible_bounds':b,'crop':box,'integer_reduction':factor,'final_size':[16,16],'animation':'Eight phases: four exact clockwise quarter-turn orientations, each held for two native water frames. No interpolated rotation.','binary_alpha':True,'no_collision_or_event_changes':True,'files':files};(folder/'provenance.json').write_text(json.dumps(proof,indent=2)+'\n');sprite.resize((256,256),Image.Resampling.NEAREST).save(ROOT.parent/'.work/tileshift-johto-final-outdoors/whirlpool-review.png');print(json.dumps(proof))
if __name__=='__main__':main()
