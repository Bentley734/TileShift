"""Record guarded ride inputs and reuse existing reviewed TileShift artwork."""
from pathlib import Path
import argparse,json,hashlib,os,sys
W=next(p for p in Path(__file__).resolve().parents if(p/'.tools/python').is_dir());sys.path.insert(0,str(W/'.tools/python'))
from PIL import Image
SHA=lambda b:hashlib.sha256(b).hexdigest()
def canonical(value):
 if isinstance(value,dict):return{k:canonical(value[k])for k in sorted(value)}
 if isinstance(value,list):return[canonical(v)for v in value]
 return value
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mod-root',type=Path,default=Path(__file__).resolve().parents[1]);a=p.parse_args();m=a.mod_root.resolve();sys.path.insert(0,str(m/'tools'))
 import catalog,preview
 from newbark_building_review import lua
 cache=Path(os.environ['APPDATA'])/'pokemon-love2d';hosts={}
 for game in('gold','silver','crystal'):
  root=cache/game;sets=catalog.read_lua(root/'data/generated/tilesets.lua');ts=sets['TILESET_TRAIN_STATION'];gfx=catalog.read_lua(root/'data/generated/field.lua')['magnetTrain'];im=Image.open(root/ts['image'])
  hosts[game]={'sheet':ts['image'],'width':im.width,'height':im.height,'files':{name:SHA((root/name).read_bytes())for name in('data/generated/tilesets.lua','data/generated/field.lua',ts['image'])},'bgTiles':gfx['bgTiles'],'tilemap':gfx['tilemap']}
 rows=preview.read_reviewed(m/'mappings/johto_station_finish.lua');edge=next(r for r in rows if r['game']=='crystal'and r['role']=='johto_station_platform_safety_edge');concrete=next(r for r in rows if r['game']=='crystal'and r['role']=='johto_station_concrete_platform')
 flora=catalog.plain(catalog.LUA.execute((m/'lib/flora_catalog.lua').read_text(encoding='utf8')))
 rails=[]
 for i in(0,1):
  name=f'assets/third_party/metalflygon08/rail-cell-0-{i}.png';rails.append({'asset':name,'hash':SHA((m/name).read_bytes())})
 result={'version':1,'hosts':hosts,'metal':[[255,255,255],[197,189,214],[123,123,123],[82,82,107]],'gold':[[255,206,90],[230,140,99],[165,156,165],[82,82,107]],
  'exterior':list((23,19,17,15,12,10,8,7,4,3,2,1,1)+(0,)*11+(1,1,2,3)+(0,)*4),'ground':flora['base'],'rails':rails,
  'concrete':concrete['donor'],'edge':{'kind':'native_composite','game':'crystal','style':'gen3','base':edge['base'],'parts':edge['parts']}}
 (m/'lib/magnet_train_ride_catalog.lua').write_bytes(('-- Native source fingerprints; no imported source artwork is distributed.\n-- Existing MetalFlygon08 rail credit/provenance remains with its original assets.\nreturn '+lua(canonical(result))+'\n').encode())
 print('Wrote guarded GSC ride metadata and existing native/community artwork references')
if __name__=='__main__':main()
