"""Install the actual reference arcade without scaling or generated substitutes."""
import argparse,copy,json,os
from pathlib import Path
from types import SimpleNamespace
from PIL import Image
import catalog,preview,gen2_extended_review as e
from interior_review import Imports
from building_review import decode_layout
from newbark_building_review import lua
ROOT=Path(__file__).resolve().parents[1]
URL='https://imgur.com/gallery/testing-out-gen-3-style-tiles-johto-6A43Cji'
PERMISSION='https://www.reddit.com/r/PokemonRMXP/comments/yf90qb/full_johto_gen_3_tileset_tile_set_at_the_bottom/'
def main():
 p=argparse.ArgumentParser();p.add_argument('--activate',action='store_true');args=p.parse_args()
 out=ROOT.parent/'.work/tileshift-goldenrod-arcade';out.mkdir(exist_ok=True);folder=ROOT/'assets/third_party/metalflygon08';folder.mkdir(parents=True,exist_ok=True)
 atlas=Image.open(ROOT.parent/'.work/tileshift-ecruteak-finish/johto-native-atlas.png').convert('RGBA');source=atlas.crop((0,3200,80,3264));xs=list(range(72))+list(range(56,72))+list(range(72,80));sprite=Image.new('RGBA',(96,64))
 for x,sx in enumerate(xs):sprite.paste(source.crop((sx,0,sx+1,64)),(x,0))
 assert sprite.crop((0,0,72,64)).tobytes()==source.crop((0,0,72,64)).tobytes()
 assert sprite.crop((72,0,88,64)).tobytes()==source.crop((56,0,72,64)).tobytes()
 assert sprite.crop((88,0,96,64)).tobytes()==source.crop((72,0,80,64)).tobytes()
 files={};assets={}
 for name,im in(('game-corner-source.png',source),('game-corner.png',sprite)):
  path=folder/name;im.save(path);files[name]=catalog.sha(path.read_bytes())
 for y in range(4):
  for x in range(6):
   im=sprite.crop((x*16,y*16,x*16+16,y*16+16));name=f'game-corner-cell-{x}-{y}.png';path=folder/name;im.save(path);files[name]=catalog.sha(path.read_bytes());assets[x,y]={'asset':path.relative_to(ROOT).as_posix(),'assetFileHash':files[name],'assetPixelHash':catalog.sha(im.tobytes())}
 provenance={'artist':'MetalFlygon08 (preferred credit), also known as SkidMarc25','source_url':URL,'permission_url':PERMISSION,'permission':'Author states the tileset is free to use and prefers the name MetalFlygon08 for optional credit.','atlas_sha256':catalog.sha((ROOT.parent/'.work/tileshift-ecruteak-finish/johto-native-atlas.png').read_bytes()),'atlas_crop_xyxy':[0,3200,80,3264],'source_size':[80,64],'final_size':[96,64],'source_columns':xs,'scale':1,'repeated_complete_roof_window_wall_module_xyxy':[56,0,72,64],'insert_at_x':72,'all_original_pixels_retained':True,'door_bottom_anchor_px':[40,64],'source_rgba_sha256':catalog.sha(source.tobytes()),'final_rgba_sha256':catalog.sha(sprite.tobytes()),'files':files}
 previous=json.loads((folder/'provenance.json').read_text(encoding='utf-8'))if(folder/'provenance.json').exists()else{}
 provenance['files']={**previous.get('files',{}),**files}
 for key in ('buildings',):
  if key in previous:provenance[key]=previous[key]
 (folder/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8')
 cache=Path(os.environ['APPDATA'])/'pokemon-love2d';imports=Imports(cache,ROOT.parent/'.work/tileshift-catalog');packed=imports.packed;active=[r for path in(ROOT/'mappings').glob('*.lua')if path.name!='goldenrod_arcade.lua'for r in preview.read_reviewed(path)];ground=next(r['base']for r in active if r.get('base',{}).get('tileset')=='general__petalburg'and r['base']['id']==1)
 native=imports.table('emerald','gba/native/manifest')['layouts']['EM_MAUVILLE_CITY'];layout=decode_layout(cache/'emerald/data/generated/gba/native'/native['file']);assert layout['mids'][13*layout['width']+8]==723;assert any(w['x']==8 and w['y']==13 and w['destMap']=='EM_MAUVILLE_CITY_GAME_CORNER'for w in imports.table('emerald','gba/warps')['EM_MAUVILLE_CITY']);door=imports.cell_index('emerald')[native['pair'],723];door={'game':'emerald','tileset':native['pair'],'id':723,'hash':door['pixel_sha256']}
 rows=[];stats=[]
 for game in e.GAMES:
  data=e.source(cache,game);m=data['maps']['GOLDENROD_CITY'];assert any(w['x']==14 and w['y']==21 and w['destMap']=='GOLDENROD_GAME_CORNER'for w in m['warps'])
  for dy in range(4):
   for dx in range(6):
    x,y=12+dx,18+dy;bid=m['blocks'][y//2*m['width']+x//2];q=y%2*2+x%2;c=e.cell_info(cache,game,data,m['tileset'],bid,q)
    r={'game':game,'style':'gen3','map':'GOLDENROD_CITY','tileset':m['tileset'],'id':bid,'quadrant':q,'x':x,'y':y,'sourceCells':[[x,y]],'sourceHash':c['sourceHash'],'sourceFiles':data['fingerprints'][m['tileset']],'sourceCollision':c['collision'],'sourcePriority':[bool(a.get('priority'))for a in c['attributes']],'sourcePalettes':[a.get('palette',1)for a in c['attributes']],'kind':'third_party','credit':'MetalFlygon08','sourceUrl':URL,'base':copy.deepcopy(door if(dx,dy)==(2,3)else ground),'role':'goldenrod_native_arcade','status':'reviewed',**assets[dx,dy]}
    r['evidence']='Actual MetalFlygon08 Johto Gen3 Game Corner, used under the author free-use statement. Original80x64 artwork remains unscaled and wholly intact. One complete16px roof/window/wall module repeats to fill the original96x64 source building. All roof edges, vents, window frames, lamps and entrance pixels remain intact; no generated architecture is used. Original doorway14,21 and GOLDENROD_GAME_CORNER destination remain unchanged. Transparent roof corners match current Emerald1 lawn; the one transparent entry cell uses the actual native Mauville Game Corner723 door backdrop, with no imported door scripts, animation or mechanic.'
    if(dx,dy)==(2,3):assert c['collision']==113
    r['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,r,packed,ROOT).tobytes());rows.append(r)
  report=preview.map_preview(cache,out,game,'GOLDENROD_CITY',game+'-native-arcade',active+rows,packed,1,ROOT);stats.append({'game':game,'map':'GOLDENROD_CITY','arcade_cells':24,'replaced':report['replaced_occurrences'],'total':report['visible_cells']})
 live=e.validate_batch(rows,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=out),ROOT);(out/'proof.json').write_text(json.dumps({'maps':stats,'live':live,'native_door_base':door},indent=2),encoding='utf-8')
 if args.activate:
  text='-- Actual Johto Gen3 arcade; complete original building and door anchors.\nlocal rows={}\nlocal function add(batch)for _,r in ipairs(batch)do rows[#rows+1]=r end end\n'
  for n in range(0,len(rows),20):text+='add((function()return '+lua(rows[n:n+20])+' end)())\n'
  (ROOT/'mappings/goldenrod_arcade.lua').write_bytes((text+'return rows\n').encode())
 print(json.dumps({'rows':len(rows),'maps':stats,'live':live,'activated':args.activate}))
if __name__=='__main__':main()
