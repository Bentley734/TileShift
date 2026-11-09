"""Use whole native CrystalDust piers and Union Cave/Slowpoke Well ladders.

Native actors, warp anchors, collision, fishing and Lapras callbacks are retained.
Only the native wood/ladder planes are imported; selected local water and floor
remain visible underneath. Furniture depth uses the bounded ladder catalog.
"""
from pathlib import Path
import argparse,copy,hashlib,json,os,re,sys
from types import SimpleNamespace
W=next(p for p in Path(__file__).resolve().parents if(p/'.tools/python').is_dir()and(p/'.work').is_dir())
sys.dont_write_bytecode=True
sys.path.insert(0,str(W/'.tools/python'))
from PIL import Image
GAMES=('gold','silver','crystal')
FOLDER='assets/third_party/johto-hacks/crystaldust-route32-union'
ROM='51196cba923c315d0088b747b5cdee704f2ac057cd493f9ddf226fb7227302cf'
sha=lambda b:hashlib.sha256(b).hexdigest()
pixel=lambda im:sha(im.convert('RGBA').tobytes())
def key(row):return tuple(row.get(k)for k in('game','style','tileset','map','id','quadrant','x','y'))
def canonical(value):
 if isinstance(value,dict):return{k:canonical(v)for k,v in sorted(value.items())}
 if isinstance(value,list):return[canonical(v)for v in value]
 return value
def atomic(path,data):
 path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_name(path.name+'.route32.tmp')
 assert not temp.exists();temp.write_bytes(data);os.replace(temp,path)
def footer(path,body,marker):
 raw=path.read_bytes();start=('-- BEGIN '+marker).encode();end=('-- END '+marker).encode()
 block=start+b'\n'+body.encode()+b'\n'+end+b'\n'
 if start in raw:
  assert raw.count(start)==raw.count(end)==1
  left=raw.index(start);right=raw.index(end,left)+len(end)
  if raw[left+len(start):left+len(start)+2]==b'\r\n':block=block.replace(b'\n',b'\r\n')
  if raw[right:right+2]==b'\r\n':right+=2
  elif raw[right:right+1]==b'\n':right+=1
  # Retain all other authors' bytes and footer order on cumulative replay.
  atomic(path,raw[:left]+block+raw[right:])
  return sha(block)
 nl=b'\r\n'if b'\r\n'in raw else b'\n'
 tail=re.search(br'(?m)^return rows[ \t]*\r?\n?\Z',raw)
 if tail:prefix=raw[:tail.start()]
 else:
  assert len(re.findall(br'(?m)^return[ \t]+\{',raw))==1 and raw.rstrip().endswith(b'}')
  prefix=re.sub(br'(?m)^return[ \t]+\{',b'local rows={',raw,count=1)
 if not prefix.endswith((b'\n',b'\r')):prefix+=nl
 atomic(path,prefix+block+b'return rows'+nl)
 return sha(block)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True)
 p.add_argument('--mod-root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True)
 p.add_argument('--native-root',type=Path,default=W/'.work/tileshift-firegold/crystaldust')
 p.add_argument('--cache',type=Path,default=Path(os.environ['APPDATA'])/'pokemon-love2d');p.add_argument('--engine',type=Path,default=W/'.work/tileshift-engine-0420')
 a=p.parse_args();base,mod,native,out=(v.resolve()for v in(a.baseline,a.mod_root,a.native_root,a.output));assert base!=mod
 assert json.loads((base/'manifest.json').read_text())['version']=='0.46.8'
 sys.path.insert(0,str(mod/'tools'));import preview,catalog,gen2_extended_review as review
 out.mkdir(parents=True,exist_ok=True);cache=a.cache.resolve();packed={}
 nc=json.loads((native/'catalog.json').read_text());assert nc['rom_sha256']==ROM
 maps={v['id']:v for v in nc['maps']};route=maps['g00_m019'];cave=maps['g24_m012'];well=maps['g24_m004']
 art={};origins=[];files={};dest=mod/FOLDER;dest.mkdir(parents=True,exist_ok=True)
 atlases={}
 def native_tile(pair,layer,mid):
  k=pair,layer
  if k not in atlases:atlases[k]=Image.open(native/'pairs'/pair/(layer+'.png')).convert('RGBA')
  return atlases[k].crop((mid%16*16,mid//16*16,mid%16*16+16,mid//16*16+16))
 def export(name,pair,layer,mid,native_map,xy):
  image=native_tile(pair,layer,mid);path=dest/name
  image.save(out/name);atomic(path,(out/name).read_bytes());files[name]=sha(path.read_bytes())
  ref=dict(asset=FOLDER+'/'+name,assetFileHash=files[name],assetPixelHash=pixel(image))
  origins.append(dict(file=name,native_map=native_map,native_cell=list(xy),pair=pair,plane=layer,metatile=mid,
   atlas_rect_xywh=[mid%16*16,mid//16*16,16,16],rgba_sha256=pixel(image),opaque_pixels=sum(v>0 for v in image.getchannel('A').get_flattened_data()),pixel_scale=1,whole_native_plane=True))
  return ref
 pier_path='mappings/johto_remaining.lua';ladder_path='mappings/gen2_caves.lua'
 pier_rows=preview.read_reviewed(base/pier_path);ladder_rows=preview.read_reviewed(base/ladder_path)
 selected=[r for r in pier_rows if r['game']in GAMES and r['style']=='gen3'and r.get('map')=='ROUTE_32'and r['role'].startswith('johto_fishing_pier_')]
 assert len(selected)==162 and all('x'in r for r in selected)
 native_ids={route['grid'][r['y']*route['width']+r['x']+4]&1023 for r in selected}
 assert native_ids=={749,750,751,752,754,755,756,757,758,759,760,761}
 opaque_junctions={749,750,757,758}
 for mid in sorted(native_ids):
  witness=next(r for r in selected if route['grid'][r['y']*route['width']+r['x']+4]&1023==mid)
  art[mid]=export(f'pier-{mid}.png',route['pair'],'bottom'if mid in opaque_junctions else'top',mid,'g00_m019',(witness['x']+4,witness['y']))
  if mid in opaque_junctions:assert origins[-1]['opaque_pixels']==256
 ladder_art=[export('ladder-top.png',cave['pair'],'top',526,'g24_m012',(2,32)),export('ladder-bottom.png',cave['pair'],'top',534,'g24_m012',(2,33))]
 well_art=[export('well-ladder-top.png',well['pair'],'top',526,'g24_m004',(17,14)),export('well-ladder-bottom.png',well['pair'],'top',534,'g24_m004',(17,15))]
 complete=Image.new('RGBA',(16,32))
 for y,ref in enumerate(ladder_art):complete.alpha_composite(Image.open(mod/ref['asset']).convert('RGBA'),(0,y*16))
 assert complete.getbbox()==(1,2,14,32)and sum(v>0 for v in complete.getchannel('A').get_flattened_data())==233
 assert pixel(complete)=='f2fa7e2013a3d6392c73b0d0b7e8dfb0a7fe5f0a4cc2e438c600485802ee66f3'
 complete_well=Image.new('RGBA',(16,32))
 for y,ref in enumerate(well_art):complete_well.alpha_composite(Image.open(mod/ref['asset']).convert('RGBA'),(0,y*16))
 assert complete_well.getbbox()==(1,2,14,32)and sum(v>0 for v in complete_well.getchannel('A').get_flattened_data())==233
 native_ladder_contexts=[]
 for map_id,x,y,is_well in(('g24_m012',7,19,False),('g24_m012',2,33,False),('g24_m095',5,3,False),('g24_m004',17,15,True),('g24_m009',9,11,True)):
  md=maps[map_id];upper=md['grid'][(y-1)*md['width']+x]&1023;lower=md['grid'][y*md['width']+x]&1023
  exact=Image.new('RGBA',(16,32));exact.alpha_composite(native_tile(md['pair'],'top',upper),(0,0));exact.alpha_composite(native_tile(md['pair'],'top',lower),(0,16))
  assert exact.tobytes()==(complete_well if is_well else complete).tobytes()
  native_ladder_contexts.append(dict(native_map=map_id,native_anchor=[x,y],pair=md['pair'],upper_mid=upper,lower_mid=lower,whole_rgba_sha256=pixel(exact),whole_object_exact=True))
 data={g:review.source(cache,g)for g in GAMES};updates={pier_path:[],ladder_path:[]};furniture=[];changes=[];scenes={}
 def verify(row,xy):
  d=data[row['game']];md=d['maps'][row['map']];x,y=xy;bid=md['blocks'][y//2*md['width']+x//2];q=y%2*2+x%2
  assert(row['id'],row['quadrant'])==(bid,q)
  c=review.cell_info(cache,row['game'],d,row['tileset'],bid,q)
  assert row['sourceHash']==c['sourceHash']and row['sourceCollision']==c['collision']
  assert row['sourceFiles']==d['fingerprints'][row['tileset']]
  assert row['sourcePriority']==[bool(v.get('priority'))for v in c['attributes']]
  assert row['sourcePalettes']==[v.get('palette',1)for v in c['attributes']]
  scenes[row['game']+':'+row['map']]=sha(json.dumps(md,sort_keys=True,separators=(',',':')).encode())
  return c
 for old in selected:
  xy=old['x'],old['y'];verify(old,xy);mid=route['grid'][old['y']*route['width']+old['x']+4]&1023
  ocean=next(r for r in pier_rows if r['game']==old['game']and r['style']=='gen3'and r.get('map')=='ROUTE_32'and r.get('role')=='coastal_ocean_water_interior'and r.get('donor',{}).get('id')==368)
  new=copy.deepcopy(old)
  for field in('donor','parts','assetFrames','assetPixelHash','animation','base'):new.pop(field,None)
  new.update(kind='third_party',base=copy.deepcopy(ocean['donor']),animated=True,animation=copy.deepcopy(ocean['animation']),
   sourceOceanBounds=copy.deepcopy(ocean['sourceOceanBounds']),credit='CrystalDust / Sierraffinity and contributors',sourceUrl='https://github.com/Sierraffinity/CrystalDust',**art[mid])
  new['nativePierReview']=dict(native_map='g00_m019',native_cell=[old['x']+4,old['y']],mid=mid,whole_native_plane=True,
   direction_and_junction_topology_preserved=True,native_water_background_excluded=True,selected_ocean_frames=8)
  new['evidence']='Complete1:1 native CrystalDust timber pier. Actual native Route32 topology is identical at x+4 with unchanged y: north/south runs, fishing spurs, all four whole junction quadrants and full edge-shadow modules. Whole native wood planes retain every hardware pixel. Native palette6 water tiles are background, never baked into the wood; all transparent gaps use the existing reviewed Emerald368 ocean and original8-frame clock, including Mixed chooser grouping. Source collision, actors, fishing and route geometry are unchanged.'
  new['compositionPixelHash']=pixel(preview.replacement_image(cache,new,packed,mod));updates[pier_path].append(new)
  changes.append(dict(game=old['game'],map=old['map'],xy=list(xy),sourceHash=old['sourceHash'],module=pier_path,kind='pier',native_mid=mid,old_RGBA_sha256=pixel(preview.replacement_image(cache,old,packed,base)),new_RGBA_sha256=new['compositionPixelHash']))
 anchors=(('UNION_CAVE_B1F',7,19),('UNION_CAVE_B1F',3,33),('UNION_CAVE_B2F',5,3),('SLOWPOKE_WELL_B1F',17,15),('SLOWPOKE_WELL_B2F',9,11))
 for game in GAMES:
  for name,x,y in anchors:
   md=data[game]['maps'][name];bid=md['blocks'][y//2*md['width']+x//2]
   old=next(r for r in ladder_rows if r['game']==game and r['style']=='gen3'and r.get('map')==name and r['id']==bid and r['quadrant']==3)
   verify(old,(x,y));assert old['role']=='cave_ascending_ladder'and old['sourceCollision']==114 and old['sourceCells']==[[x,y]]
   new=copy.deepcopy(old)
   for field in('parts','base','kind','compositionPixelHash','asset','assetFileHash','assetPixelHash'):new.pop(field,None)
   new.update(donor=copy.deepcopy(old['base']),role='crystaldust_complete_union_ladder_native_floor',evidence='Keep the already reviewed native regional ground at the unchanged source ladder warp. The complete233-pixel native CrystalDust16x32 ladder is depth-sorted separately at this exact anchor; no glyph is cropped or scaled, and no warp, collision, actor or script is changed.')
   new['compositionPixelHash']=pixel(preview.replacement_image(cache,new,packed,mod));updates[ladder_path].append(new)
   upper=review.cell_info(cache,game,data[game],md['tileset'],bid,1)
   for sy,ref in enumerate(well_art if name.startswith('SLOWPOKE_WELL_')else ladder_art):
    r={k:copy.deepcopy(v)for k,v in old.items()if k.startswith('source')}
    r.update({k:old[k]for k in('game','style','tileset','id','quadrant')})
    r.update(furniture='union_cave_ladder',kind='third_party',status='reviewed',role='crystaldust_complete_union_cave_ladder',map=name,
     anchorX=x,anchorY=y,x=x,y=y-1+sy,frontY=(y+1)*16,upperX=x,upperY=y-1,upperId=bid,upperQuadrant=1,upperHash=upper['sourceHash'],upperCollision=upper['collision'],
     evidence='Complete native CrystalDust16x32 upright ladder, preserving all233 original opaque pixels in two whole16px TOP modules at native scale and regional colors. The unchanged lower source warp is the anchor; the guarded upper cell is quadrant1 of that same immutable source block. Transparent pixels reveal the existing reviewed floor or north rim. The finite physical base sorts the complete ladder correctly behind or in front of actors. Source collision114, exact warp destinations, upper source pixels/collision, NPCs, callbacks, encounters and native gameplay geometry are unchanged; no ladder pixel is cropped, recolored or scaled.',
     credit='CrystalDust / Sierraffinity and contributors',sourceUrl='https://github.com/Sierraffinity/CrystalDust',**ref)
    furniture.append(r)
   changes.append(dict(game=game,map=name,xy=[x,y],sourceHash=old['sourceHash'],module=ladder_path,kind='ladder_floor',decorative_cells=[[x,y-1],[x,y]],native_opaque_pixels=233,old_RGBA_sha256=pixel(preview.replacement_image(cache,old,packed,base)),new_RGBA_sha256=new['compositionPixelHash']))
 receipts={}
 for path,rows in updates.items():
  body,_=review.write_compact([canonical(r)for r in rows],None)
  code='local nativeUpdates=(function()\n'+body+'end)()\n'+'''local function nativeKey(r)return table.concat({r.game,r.style,r.tileset,r.map or '',r.id,r.quadrant,r.x or '',r.y or ''},':')end
local nativeIndex={}for i,r in ipairs(rows)do nativeIndex[nativeKey(r)]=i end
for _,r in ipairs(nativeUpdates)do local i=assert(nativeIndex[nativeKey(r)],'Missing native Route32/Union source key');assert(rows[i].sourceHash==r.sourceHash);rows[i]=r end'''
  receipts[path]=dict(sha256=sha((mod/path).read_bytes()),rows=len(rows),footer_sha256=footer(mod/path,code,'NATIVE CRYSTALDUST ROUTE32 UNION'))
  receipts[path]['sha256']=sha((mod/path).read_bytes())
 from lupa.luajit21 import LuaRuntime
 schema=LuaRuntime(unpack_returned_tuples=True);validate=schema.execute((mod/'lib/mapping.lua').read_text())['validate']
 for r in furniture:
  checked=copy.deepcopy(r);checked['x'],checked['y']=r['anchorX'],r['anchorY']
  result=validate(schema.table_from(checked,recursive=True))
  assert result is True,(r['game'],r['map'],r['anchorX'],r['anchorY'],result)
 body,_=review.write_compact([canonical(r)for r in furniture],None)
 code='local nativeLadders=(function()\n'+body+'end)()\nfor _,r in ipairs(nativeLadders)do rows[#rows+1]=r end'
 path='lib/johto_furniture.lua';receipts[path]=dict(rows=len(furniture),footer_sha256=footer(mod/path,code,'NATIVE CRYSTALDUST UNION LADDERS'),sha256=sha((mod/path).read_bytes()))
 provenance=dict(format=1,credit='CrystalDust / Sierraffinity and contributors',sourceUrl='https://github.com/Sierraffinity/CrystalDust',source_rom_sha256=ROM,
  files=files,pieces=origins,native_catalog_sha256=sha((native/'catalog.json').read_bytes()),native_atlas_files={pair+'/'+layer+'.png':sha((native/'pairs'/pair/(layer+'.png')).read_bytes())for pair,layer in atlases},
  ladder=dict(size=[16,32],rgba_sha256=pixel(complete),opaque_pixels=233,alpha_bounds=list(complete.getbbox()),complete_unique_art_preserved=True),
  well_ladder=dict(size=[16,32],rgba_sha256=pixel(complete_well),opaque_pixels=233,alpha_bounds=list(complete_well.getbbox()),native_pair=well['pair'],palette_correct_native_planes=True),
  native_ladder_contexts=native_ladder_contexts,
  pier=dict(native_map='g00_m019',source_to_native_offset=[4,0],whole_native_modules=12,source_cells_per_game=54,water_background_not_imported=True))
 atomic(dest/'provenance.json',(json.dumps(provenance,indent=2)+'\n').encode())
 valid=review.validate_batch(updates[pier_path]+updates[ladder_path],SimpleNamespace(cache=cache,engine=a.engine,output=out),mod)
 assert valid['rows_accepted']==177 and valid['rejected']==0
 proof=dict(status='passed',authored_mapping_rows=177,pier_rows=162,ladder_floor_rows=15,furniture_rows=30,changes=changes,
  changed_mapping_modules=receipts,native_pngs=len(files),source_definition_sha256=scenes,native_validation=valid,
  whole_ladder_rgba_sha256=pixel(complete),source_geometry_npcs_warps_collision_callbacks_unchanged=True,
  whole_well_ladder_rgba_sha256=pixel(complete_well),complete_ladder_instances=15,
  furniture_rows_validated_with_real_mapping_schema=len(furniture),
  pending_validation='Bounded union_cave_ladder runtime case and actual native actor-depth / all6 water choices are verified on the integrated candidate.')
 (out/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
 print(json.dumps({k:v for k,v in proof.items()if k not in('changes','changed_mapping_modules','source_definition_sha256')},indent=2))
if __name__=='__main__':main()
