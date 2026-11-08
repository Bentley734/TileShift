"""Use the complete native fence middle plane over each map's actual grass.

FireRed Pallet MID644 has174 genuine hardware/shadow pixels and82 native
transparent background pixels. The previous flattened donor baked its own
grass into those gaps. No recoloring, drawing or silhouette cropping is needed.
"""
from pathlib import Path
from collections import defaultdict,Counter
from types import SimpleNamespace
import argparse,copy,hashlib,json,os,re,sys
W=next(p for p in Path(__file__).resolve().parents if(p/'.tools/python').is_dir()and(p/'.work').is_dir())
sys.path.insert(0,str(W/'.tools/python'))
from PIL import Image
GAMES=('red','blue','yellow','gold','silver','crystal')
FENCE='03087e017ab190f3aafa4f07ae258d16cbf4e6a243241899c171e506cdc58ebd'
MID='a93049b5cd6a1dec9f2d7aea74a40f20d8a71608770fb7b731996db50551c40e'
GRASS={('emerald','general__petalburg',1),('firered','pallet_outdoor',1)}
MARKER=b'-- BEGIN NATIVE TRANSPARENT FENCE BACKGROUNDS'
sha=lambda b:hashlib.sha256(b).hexdigest()
def canonical(v):
 if isinstance(v,dict):return{k:canonical(x)for k,x in sorted(v.items())}
 if isinstance(v,list):return[canonical(x)for x in v]
 return v
def key(r):return tuple(r.get(k)for k in('game','style','tileset','map','id','quadrant','x','y'))
def refkey(r):return r.get('game'),r.get('tileset'),r.get('id')

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True)
 p.add_argument('--mod-root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True)
 p.add_argument('--engine',type=Path,default=W/'.work/tileshift-engine-0420');a=p.parse_args()
 base,mod,out=a.baseline.resolve(),a.mod_root.resolve(),a.output.resolve();assert base!=mod;out.mkdir(parents=True,exist_ok=True)
 sys.path.insert(0,str(mod/'tools'));import preview,catalog,gen2_extended_review as review
 from lupa.luajit21 import LuaRuntime
 cache=Path(os.environ['APPDATA'])/'pokemon-love2d'
 paths=list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(base/'main.lua').read_text(encoding='utf-8'))))
 modules={p:preview.read_reviewed(base/p)for p in paths};glob=defaultdict(dict);scoped=defaultdict(dict);positions=defaultdict(dict)
 for path,rs in modules.items():
  for i,r in enumerate(rs):
   if r['game']not in GAMES or r['style']!='gen3':continue
   k=r['id'],r['quadrant'];v=path,i,r
   if'x'in r:positions[r['game'],r['map']][(*k,r['x'],r['y'])]=v
   elif r.get('map'):scoped[r['game'],r['map']][k]=v
   else:glob[r['game'],r['tileset']][k]=v
 packed={};data={};groups=defaultdict(list);changes=[];ground_refs={};map_receipts=[];all_active={};before_row={}
 fence_ref=next(r['donor']for rs in modules.values()for r in rs if r.get('donor',{}).get('hash')==FENCE and r['style']=='gen3')
 fence=preview.native_donor(cache,fence_ref,packed,['mid'],{'mid':MID});alpha=list(fence.getchannel('A').get_flattened_data())
 assert alpha.count(255)==174 and alpha.count(0)==82 and set(alpha)=={0,255}
 for game in GAMES:
  d=data[game]=review.source(cache,game)
  for name,md in sorted(d['maps'].items()):
   regular=glob[game,md['tileset']].copy();regular.update(scoped[game,name]);active={}
   for i,bid in enumerate(catalog.lua_array(md['blocks'])):
    for q in range(4):
     x,y=i%md['width']*2+q%2,i//md['width']*2+q//2
     v=positions[game,name].get((bid,q,x,y),regular.get((bid,q)))
     if v:active[x,y]=v
   all_active[game,name]=active;targets={xy:v for xy,v in active.items()if v[2].get('donor',{}).get('hash')==FENCE}
   if not targets:continue
   grass=[(xy,r['donor'],r['role'])for xy,(_,_,r)in active.items()if refkey(r.get('donor',{}))in GRASS]
   assert grass,(game,name,'No actual grass reference')
   map_receipts.append(dict(game=game,map=name,source_definition_sha256=sha(json.dumps(canonical(md),separators=(',',':')).encode())))
   ts=d['sets'][md['tileset']];sheet=Image.open(cache/game/ts['image']).convert('RGBA')
   for(x,y),(path,index,old)in sorted(targets.items(),key=lambda z:(z[0][1],z[0][0])):
    distance,nx,ny,ground,role=min((abs(xx-x)+abs(yy-y),xx,yy,g,rr)for(xx,yy),g,rr in grass)
    assert distance<=8,(game,name,x,y,distance)
    block=catalog.lua_array(catalog.dict_at(ts['blocks'],old['id']+1));source=preview.native_cell(sheet,ts,block,old['quadrant'])
    assert sha(source.tobytes())==old['sourceHash']
    for field,file in(('metadata','data/generated/tilesets.lua'),('maps','data/generated/maps.lua'),('image',ts['image'])):
     assert old['sourceFiles'][field]==sha((cache/game/file).read_bytes())
    row=copy.deepcopy(old);row.pop('donor');row.update(kind='native_composite',base=copy.deepcopy(ground),parts=[dict(
       donor=copy.deepcopy(fence_ref),layers=['mid'],layerHashes={'mid':MID},srcX=0,srcY=0,w=16,h=16,x=0,y=0)])
    row['nativeFenceBackgroundReview']=dict(native_full_donor_sha256=FENCE,native_middle_plane_sha256=MID,
        opaque_hardware_and_shadow_pixels=174,transparent_gap_pixels=82,complete_native_plane=True)
    row['evidence']+=' Use the complete unscaled native FireRedPallet644 middle plane, not its flattened native grass backing. All174native post,cap,rail and cast-shadow pixels remain exact; all82exterior and enclosed gap pixels reveal this source map\'s checked adjacent plain-grass profile. No color deletion, silhouette crop, collision, NPC, event, warp or script changes.'
    ground_im=preview.native_donor(cache,ground,packed);result=preview.replacement_image(cache,row,packed,mod)
    assert result.tobytes()==Image.alpha_composite(ground_im,fence).tobytes()
    assert all(p==(fg if aa else bg)for p,fg,aa,bg in zip(result.get_flattened_data(),fence.get_flattened_data(),alpha,ground_im.get_flattened_data()))
    row['compositionPixelHash']=sha(result.tobytes());ground_refs[refkey(ground)]=copy.deepcopy(ground)
    groups[path,index].append(((game,name,x,y),row));before_row[game,name,x,y]=old
    changes.append(dict(game=game,map=name,xy=[x,y],module=path,id=old['id'],quadrant=old['quadrant'],sourceHash=old['sourceHash'],
        sourceFiles=old['sourceFiles'],sourceCollision=old.get('sourceCollision'),sourcePalettes=old.get('sourcePalettes'),
        sourcePriority=old.get('sourcePriority'),native_fence_mid_sha256=MID,reference_cell=[nx,ny],reference_role=role,base=ground,
        opaque_native_pixels_retained=174,transparent_pixels_show_actual_grass=82,
        old_RGBA_sha256=sha(preview.replacement_image(cache,old,packed,base).tobytes()),new_RGBA_sha256=row['compositionPixelHash']))
 assert len(changes)==3243 and len(map_receipts)==132,(len(changes),len(map_receipts))
 assert len(ground_refs)==2
 updates=defaultdict(dict);extras=defaultdict(list);validation=[]
 for(path,index),items in sorted(groups.items()):
  old=modules[path][index];profiles=Counter(refkey(r['base'])for loc,r in items)
  preferred=('emerald','general__petalburg',1);chosen=preferred if preferred in profiles else profiles.most_common(1)[0][0]
  row=copy.deepcopy(next(r for loc,r in items if refkey(r['base'])==chosen));row['sourceCells']=copy.deepcopy(old.get('sourceCells',{}))
  updates[path][key(old)]=canonical(row)
  for(g,n,x,y),r in items:
   if refkey(r['base'])!=chosen:
    assert old.get('map')is None,'Only exact global aliases require mixed-ground splits'
    r.update(map=n,x=x,y=y,sourceCells=[[x,y]]);extras[path].append(canonical(r))
   v=copy.deepcopy(r);v.update(map=n,x=x,y=y,sourceCells=[[x,y]]);validation.append(v)
 assert all(refkey(r['base'])in GRASS for rs in extras.values()for r in rs)
 stats={};new_modules={}
 for path,replacements in sorted(updates.items()):
  raw=(base/path).read_bytes();assert MARKER not in raw;nl=b'\r\n'if b'\r\n'in raw else b'\n'
  if raw.endswith(b'return rows'+nl):prefix=raw[:-len(b'return rows'+nl)];prefix_mode='existing_rows_footer'
  else:
   assert len(re.findall(br'(?m)^return[ \t]+\{',raw))==1 and raw.rstrip().endswith(b'}')
   prefix=re.sub(br'(?m)^return[ \t]+\{',b'local rows={',raw,count=1);prefix_mode='top_level_table_bound_to_rows'
  changed=canonical(list(replacements.values())+extras[path]);body,compact=review.write_compact(changed,None)
  footer=MARKER.decode()+'\nlocal fenceUpdates=(function()\n'+body+'''end)()
local function fenceKey(r)return table.concat({r.game,r.style,r.tileset,r.map or '',r.id,r.quadrant,r.x or '',r.y or ''},':')end
local fenceIndex={}for i,r in ipairs(rows)do fenceIndex[fenceKey(r)]=i end
local replaced,added=0,0
for _,r in ipairs(fenceUpdates)do local i=fenceIndex[fenceKey(r)];if i then rows[i]=r;replaced=replaced+1 else rows[#rows+1]=r;added=added+1 end end
'''+f"assert(replaced=={len(replacements)} and added=={len(extras[path])},'Native transparent fence source set changed')\n"+'''-- END NATIVE TRANSPARENT FENCE BACKGROUNDS
return rows
'''
  delta=footer.replace('\n',nl.decode()).encode();(mod/path).write_bytes(prefix+delta);(out/(Path(path).name+'.footer')).write_bytes(delta)
  after=preview.read_reviewed(mod/path);expected={key(r):replacements.get(key(r),r)for r in modules[path]};expected.update({key(r):r for r in extras[path]})
  assert len(after)==len(expected)and{key(r):r for r in after}==expected;new_modules[path]=after
  stats[path]=dict(replaced=len(replacements),added=len(extras[path]),module_sha256=sha((mod/path).read_bytes()),footer_sha256=sha(delta),compact=compact,prefix_mode=prefix_mode)
 # Resolve all actual source cells again using the official position precedence.
 new_scope=defaultdict(dict);new_pos=defaultdict(dict);new_global=defaultdict(dict)
 for path,rs in modules.items():
  for r in new_modules.get(path,rs):
   if r['game']not in GAMES or r['style']!='gen3':continue
   k=r['id'],r['quadrant']
   if'x'in r:new_pos[r['game'],r['map']][(*k,r['x'],r['y'])]=r
   elif r.get('map'):new_scope[r['game'],r['map']][k]=r
   else:new_global[r['game'],r['tileset']][k]=r
 allowed={(c['game'],c['map'],*c['xy'])for c in changes};actual=set();world=Counter()
 for g,d in data.items():
  for n,md in d['maps'].items():
   regular=new_global[g,md['tileset']].copy();regular.update(new_scope[g,n]);world['maps']+=1
   for i,bid in enumerate(catalog.lua_array(md['blocks'])):
    for q in range(4):
     x,y=i%md['width']*2+q%2,i//md['width']*2+q//2;old_v=all_active[g,n].get((x,y));old=old_v[2]if old_v else None
     new=new_pos[g,n].get((bid,q,x,y),regular.get((bid,q)));world['source_cells']+=1
     if old==new:world['identical_effective_rows']+=1;continue
     assert(g,n,x,y)in allowed,(g,n,x,y)
     for k in('game','style','tileset','id','quadrant','sourceHash','sourceCollision','sourcePalettes','sourcePriority','sourceFiles'):assert old.get(k)==new.get(k)
     actual.add((g,n,x,y));world['changed_effective_rows']+=1
 assert actual==allowed
 runtime=LuaRuntime(unpack_returned_tuples=True);runtime.globals().paths=runtime.table_from(paths);runtime.globals().source=lambda p:(mod/p).read_text(encoding='utf-8-sig')
 total=runtime.execute('''local rows={};for _,p in ipairs(paths)do for _,r in ipairs(assert(load(source(p),'@'..p))())do rows[#rows+1]=r end end
 local M=assert(load(source('lib/mapping.lua'),'@mapping.lua'))();local _,errors=M.index(rows);assert(#errors==0,table.concat(errors,'\\n'));return #rows''')
 live=review.validate_batch(canonical(validation),SimpleNamespace(cache=cache,engine=a.engine,output=out),mod);assert live['rejected']==0
 # Two authenticated contrasting grass profiles exercise all native alpha gaps.
 contrasts=[]
 for profile,ref in sorted(ground_refs.items()):
  bg=preview.native_donor(cache,ref,packed);im=Image.alpha_composite(bg,fence)
  assert all(p==(fg if aa else under)for p,fg,aa,under in zip(im.get_flattened_data(),fence.get_flattened_data(),alpha,bg.get_flattened_data()))
  contrasts.append(dict(base=ref,native_fence_hardware_pixels_exact=174,actual_ground_pixels_revealed=82,RGBA_sha256=sha(im.tobytes())))
 proof=dict(status='passed',changed_cells=len(changes),changed_rows=sum(len(v)for v in updates.values())+sum(len(v)for v in extras.values()),
   added_positioned_rows=sum(len(v)for v in extras.values()),selected_source_cells=changes,game_maps=map_receipts,
   native_full_fence_sha256=FENCE,native_mid_plane_sha256=MID,whole_native_fence=True,opaque_pixels_preserved=174,alpha_gap_pixels=82,
   contrasting_native_ground_proofs=contrasts,effective_world_scope=dict(world),all_source_metadata_unchanged=True,
   all_other_existing_rows_identical=True,no_new_assets_or_runtime_API=True,registered_rows=total,index_errors=0,
   native_validation=live,module_receipts=stats,helper_sha256=sha(Path(__file__).read_bytes()))
 (out/'proof.json').write_text(json.dumps(canonical(proof),indent=2)+'\n',encoding='utf-8')
 combined=[r for path,rs in modules.items()for r in new_modules.get(path,rs)]
 for g,n in(('crystal','PALLET_TOWN'),('red','PALLET_TOWN'),('red','SAFFRON_CITY'),('crystal','ROUTE_13')):
  preview.map_preview(cache,out,g,n,g+'-'+n,combined,packed,3,mod)
 print(json.dumps({k:proof[k]for k in('status','changed_cells','changed_rows','added_positioned_rows','registered_rows','index_errors','native_validation','effective_world_scope')}))

if __name__=='__main__':main()
