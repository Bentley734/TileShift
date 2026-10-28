"""Rebuild a whole original object from its recorded prompt and logical size."""
import argparse,json,math
from pathlib import Path
from PIL import Image
import catalog
def main():
 p=argparse.ArgumentParser();p.add_argument('provenance',type=Path);p.add_argument('source',type=Path);a=p.parse_args();spec=json.loads(a.provenance.read_text());w,h=spec['logical_size'];im=Image.open(a.source).convert('RGBA');im.putalpha(im.getchannel('A').point(lambda v:255 if v>=128 else 0));b=im.getbbox();factor=math.ceil(max((b[2]-b[0])/w,(b[3]-b[1])/h));left=(b[0]+b[2]-w*factor)//2;box=(left,b[3]-h*factor,left+w*factor,b[3]);assert box[0]<=b[0]and box[1]<=b[1]and box[2]>=b[2];tile=im.crop(box).resize((w,h),Image.Resampling.NEAREST).quantize(colors=spec.get('palette_colors',16),method=Image.Quantize.FASTOCTREE,dither=Image.Dither.NONE).convert('RGBA');tile.putalpha(tile.getchannel('A').point(lambda v:255 if v>=128 else 0));folder=a.provenance.parent;files={}
 def save(name,pixels):
  path=folder/name;pixels.save(path);files[name]=catalog.sha(path.read_bytes())
 save(spec['name']+'.png',tile)
 if w>=16 and h>=16:
  assert w%16==0 and h%16==0
  for y in range(h//16):
   for x in range(w//16):save('cell-'+str(x)+'-'+str(y)+'.png',tile.crop((x*16,y*16,x*16+16,y*16+16)))
 if spec.get('repeat_2x2'):
  assert(w,h)==(8,8);repeat=Image.new('RGBA',(16,16))
  for y in(0,8):
   for x in(0,8):repeat.paste(tile,(x,y))
  save('repeat.png',repeat)
 spec.update(tool='image_gen.imagegen',source_file=a.source.name,source_sha256=catalog.sha(a.source.read_bytes()),source_size=im.size,visible_bounds=b,crop=box,integer_reduction=factor,binary_alpha=128,dither=False,whole_visible_object_preserved=True,files=files);a.provenance.write_text(json.dumps(spec,indent=2)+'\n');print(json.dumps({'asset':spec['name'],'logical_size':[w,h],'integer_reduction':factor,'files':len(files)}))
if __name__=='__main__':main()
