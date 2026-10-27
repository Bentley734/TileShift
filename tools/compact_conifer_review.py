"""Replace the default one-cell tree with a complete compact Emerald conifer."""
import argparse,hashlib,json,copy
from pathlib import Path
from PIL import Image,ImageDraw
import preview,gen2_extended_review as e
ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path('C:/Users/LSDMTHC/.codex/generated_images/01a1779e-1657-7893-8b0a-94f8fb9ac828/exec-4d6f60e9-c2c0-4fea-8f48-9059ddf51412.png')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--activate',action='store_true');args=p.parse_args();folder=ROOT/'assets/original/compact-conifer';folder.mkdir(exist_ok=True);out=ROOT.parent/'.work/tileshift-ecruteak-finish';im=Image.open(SOURCE).convert('RGBA');alpha=im.getchannel('A').point(lambda a:255 if a>=128 else 0);assert alpha.getbbox()==(130,56,1124,1205);im.putalpha(alpha);im=im.crop((0,0,1248,1248)).resize((16,16),Image.Resampling.NEAREST).quantize(colors=12,method=Image.Quantize.FASTOCTREE,dither=Image.Dither.NONE).convert('RGBA');asset=folder/'tree.png';im.save(asset);assert im.getchannel('A').getbbox()[3]==15 or im.getchannel('A').getbbox()[3]==16
 provenance={'origin':'Original compact tree designed with built-in imagegen','prompt':json.loads((out/'prompts.json').read_text(encoding='utf-8'))['tree'],'style_reference':'Own imported native Emerald general__petalburg14+22 complete16x32 tree, style only. No native bitmap redistributed.','source_file':SOURCE.name,'source_sha256':sha(SOURCE),'generated_size':[1254,1254],'crop_xyxy':[0,0,1248,1248],'integer_reduction':78,'runtime_size':[16,16],'processing':'Redesigned square proportions; whole canopy and visible trunk retained, uniform78:1 nearest reduction, binary alpha128,12 colors including transparency without dithering. No fractional or runtime scaling.','files':{'tree.png':sha(asset)}};(folder/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8');changed={};count=0
 for p in(ROOT/'mappings').glob('*.lua'):
  rows=preview.read_reviewed(p);n=0
  for r in rows:
   if r.get('asset')=='assets/third_party/j-treecko252/compact-tree.png':
    assert r['role']in('boundary_tree','dense_round_tree','forest_boundary_small_tree','forest_safari_round_boundary_tree');r.update(asset=asset.relative_to(ROOT).as_posix(),assetFileHash=sha(asset));r['evidence']+=' User replaced the default B4 round tree with an original complete16x16 redesign of the taller native Emerald14+22 conifer. Full pointed canopy, layered foliage and trunk remain within the one-cell source footprint, uniform integer nearest reduction only. Original source identity and collision remain unchanged.';n+=1
    # Original asset rows do not carry compositionPixelHash in the released mappings.
    r.pop('compositionPixelHash',None)
  if n:
   changed[p.name]=n;count+=n
   if args.activate:
    raw=p.read_bytes();old_path=b'assets/third_party/j-treecko252/compact-tree.png';old_hash=sha(ROOT/'assets/third_party/j-treecko252/compact-tree.png').encode();assert raw.count(old_path)>0
    raw=raw.replace(old_path,asset.relative_to(ROOT).as_posix().encode()).replace(old_hash,sha(asset).encode()).replace(b'["kind"]="third_party"',b'["kind"]="original"').replace(b"kind='third_party'",b"kind='original'")
    raw=raw.replace(b'83b0a8ca3bf5ddffb32c494f60547f2384d5f31d7989d3a0e0f2eb4eae6ac305',hashlib.sha256(im.tobytes()).hexdigest().encode()).replace(b'J-Treecko252; additional palette contributions credited to Zyxeion',b'Original compact Emerald-style conifer; built-in imagegen').replace(b'https://www.deviantart.com/j-treecko252/art/Tree-Tiles-Ver-02-884751013',b'https://github.com/Bentley734/TileShift/tree/main/assets/original/compact-conifer')
    p.write_bytes(b'-- Default one-cell tree revised: complete compact Emerald-style conifer; see assets/original/compact-conifer/provenance.json. Historical source-review evidence below remains recorded.\n'+raw)
 sheet=Image.new('RGB',(720,340),'#18202c');d=ImageDraw.Draw(sheet);d.text((16,12),'DEFAULT 1x1 TREE — previous / compact Emerald-style replacement',fill='white');old=Image.open(ROOT/'assets/third_party/j-treecko252/compact-tree.png').convert('RGBA')
 for col,sprite in enumerate((old,im)):
  for y in range(3):
   for x in range(4):sheet.paste(sprite.resize((64,64),Image.Resampling.NEAREST),(16+col*352+x*64,52+y*64),sprite.resize((64,64),Image.Resampling.NEAREST))
 d.text((16,272),'Complete canopy + trunk. 16x16 footprint. Original blocking preserved.',fill='white');sheet.save(out/'compact-tree-comparison.png');(out/'compact-tree-proof.json').write_text(json.dumps({'mapping_rows':count,'modules':changed,'asset':str(asset),'activated':args.activate},indent=2),encoding='utf-8');print(json.dumps({'rows':count,'modules':changed,'activated':args.activate}))
if __name__=='__main__':main()
