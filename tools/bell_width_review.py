"""Keep the supplied Bell Tower proportions at a larger integer pixel size."""
import argparse,copy,json,os
from pathlib import Path
from types import SimpleNamespace
from PIL import Image
import catalog,preview,gen2_extended_review as e
from newbark_building_review import lua
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'.work/tileshift-bell-wide'
def main():
 p=argparse.ArgumentParser();p.add_argument('--activate',action='store_true');p.add_argument('--reuse-assets',action='store_true');p.add_argument('--source',type=Path,default=OUT/'user-reference.png');args=p.parse_args();OUT.mkdir(exist_ok=True)
 folder=ROOT/'assets/original/bell-wide';box=(0,622,864,1774)
 if args.reuse_assets:
  previous=json.loads((folder/'provenance.json').read_text(encoding='utf-8'))
  for name,digest in previous['files'].items():assert catalog.sha((folder/name).read_bytes())==digest
  sprite=Image.open(folder/'bell.png').convert('RGBA');assert catalog.sha(sprite.tobytes())==previous['rgba_sha256'];source_hash=previous['source_sha256']
 else:
  source=Image.open(args.source).convert('RGBA');assert source.size==(887,1774)
  source.putalpha(source.getchannel('A').point(lambda a:255 if a>=128 else 0))
  sprite=source.crop(box).resize((96,128),Image.Resampling.NEAREST)
  sprite=sprite.quantize(colors=40,method=Image.Quantize.FASTOCTREE,dither=Image.Dither.NONE).convert('RGBA');source_hash=catalog.sha(args.source.read_bytes())
 assert set(sprite.getchannel('A').get_flattened_data())=={0,255}
 assert sprite.getchannel('A').getbbox()==(8,0,86,128)and sprite.getpixel((40,126))[3]==255
 folder.mkdir(parents=True,exist_ok=True);files={};assets={}
 path=folder/'bell.png';sprite.save(path);files[path.name]=catalog.sha(path.read_bytes())
 for y in range(8):
  for x in range(6):
   im=sprite.crop((x*16,y*16,x*16+16,y*16+16));name=f'cell-{x}-{y}.png';path=folder/name;im.save(path);files[name]=catalog.sha(path.read_bytes());assets[x,y]={'asset':path.relative_to(ROOT).as_posix(),'assetFileHash':files[name],'assetPixelHash':catalog.sha(im.tobytes())}
 provenance={'origin':'The user supplied the original generated Bell Tower reference again and requested its proportions, wider eaves, complete window panels and transparent partial side tiles. This is the same original source image used for the earlier tower; no new image generation or lateral stretching.','source_sha256':source_hash,'source_size':[887,1774],'crop_xyxy':box,'integer_reduction':9,'final_size':[96,128],'alpha_bounds':[8,0,86,128],'visible_width':78,'old_core_width':64,'map_origin_cell':[35,0],'unchanged_collision_rect_cells':[36,0,4,8],'door_bottom_anchor_px':[40,128],'original_entrance_cell':[37,7],'rgba_sha256':catalog.sha(sprite.tobytes()),'core_rgba_sha256':catalog.sha(sprite.crop((16,0,80,128)).tobytes()),'processing':'Uniform9:1 integer nearest-neighbour reduction, binary alpha128,40 colors without dithering. The original tower continues beyond the north map edge, so its original visible vertical map span is retained. No aspect-ratio change, window splicing, repeated columns or added collision. Only partial decorative side columns extend beyond the original source footprint; genuine unused alpha remains transparent.','files':files}
 (folder/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8')
 cache=Path(os.environ['APPDATA'])/'pokemon-love2d';old=preview.read_reviewed(ROOT/'mappings/ecruteak.lua');rows=copy.deepcopy(old);sides=[];changed=[];packed={}
 for r in rows:
  if r['role']!='ecruteak_original_bell':continue
  x,y=r['x']-35,r['y'];assert 1<=x<=4 and 0<=y<8
  r.update(assets[x,y]);r['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,r,packed,ROOT).tobytes());r['evidence']='The exact user-supplied original Bell Tower reference, at uniform9:1 integer reduction to retain broader orange eaves and complete larger window panels. The original64x128 collision footprint, original entrance37,7 and TIN_TOWER_1F destination remain unchanged. Its genuine alpha side strips draw over neighbouring trees/ground and the native right map border without replacing those source tiles or adding collision. The tower continues north beyond the original map edge; no lateral stretching, window splicing or fractional scaling.';changed.append(r)
 assert len(changed)==96
 assert [r for r in rows if r['role']!='ecruteak_original_bell']==[r for r in old if r['role']!='ecruteak_original_bell']
 for game in e.GAMES:
  data=e.source(cache,game);m=data['maps']['ECRUTEAK_CITY'];assert any(w['x']==37 and w['y']==7 and w['destMap']=='TIN_TOWER_1F'for w in m['warps'])
  for side,x,ax in(('left',35,0),('right',40,5)):
   sx=min(x,m['width']*2-1)
   for y in range(8):
    bid=m['blocks'][y//2*m['width']+sx//2];q=y%2*2+sx%2;c=e.cell_info(cache,game,data,m['tileset'],bid,q)
    sides.append({'game':game,'style':'gen3','map':'ECRUTEAK_CITY','tileset':m['tileset'],'id':bid,'quadrant':q,'x':x,'y':y,'sourceX':sx,'buildingX':36,'buildingY':0,'buildingW':4,'buildingH':8,'side':side,'sourceHash':c['sourceHash'],'sourceFiles':data['fingerprints'][m['tileset']],'sourceCollision':c['collision'],'sourcePriority':[bool(a.get('priority'))for a in c['attributes']],'sourcePalettes':[a.get('palette',1)for a in c['attributes']],'kind':'original','status':'reviewed','role':'bell_partial_side','evidence':'User authorizes partial artwork in the adjacent left/right tiles. Original source tree/ground/collision remains underneath; unused alpha stays transparent. The right strip is outside the map image and fingerprints the nearest real source column39. Rendering and actor occlusion use the original native map border without extending source maps or movement. Only this single adjacent column is permitted on each side.',**assets[ax,y]})
 live=e.validate_batch(changed,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=OUT),ROOT)
 top=preview.read_reviewed(ROOT/'lib/roof_catalog.lua');active=[r for path in(ROOT/'mappings').glob('*.lua')if path.name!='ecruteak.lua'for r in preview.read_reviewed(path)]
 stats=[]
 for game in e.GAMES:
  report=preview.map_preview(cache,OUT,game,'ECRUTEAK_CITY',game+'-wide',active+rows,packed,2,ROOT,roof_rows=top+sides);assert report['replaced_occurrences']==report['visible_cells']==1440;stats.append({'game':game,'coverage':1440,'source_collision_rect':[36,0,4,8],'entrance':[37,7]})
 (OUT/'proof.json').write_text(json.dumps({'live_core_cells':live,'side_cells':len(sides),'maps':stats,'source_geometry_unchanged':True},indent=2),encoding='utf-8')
 (OUT/'side-candidates.json').write_text(json.dumps(sides,indent=2),encoding='utf-8')
 if args.activate:
  text='-- Complete Ecruteak; Bell Tower uses the supplied wider reference at integer scale.\nlocal rows={}\nlocal function add(batch)for _,r in ipairs(batch)do rows[#rows+1]=r end end\n'
  for n in range(0,len(rows),20):text+='add((function()return '+lua(rows[n:n+20])+' end)())\n'
  (ROOT/'mappings/ecruteak.lua').write_bytes((text+'return rows\n').encode())
  (ROOT/'lib/side_catalog.lua').write_bytes(('-- Partial Bell Tower side cells; decorative alpha only, never source replacements.\nreturn '+lua(sides)+'\n').encode())
 print(json.dumps({'updated_core_cells':len(changed),'decorative_side_cells':len(sides),'visible_width':78,'live':live,'activated':args.activate}))
if __name__=='__main__':main()
