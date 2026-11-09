"""Restore native CrystalDust Kurt worktop surfaces and complete dining table."""
from pathlib import Path
import argparse,copy,hashlib,json,os,re,sys
W=next(p for p in Path(__file__).resolve().parents if(p/'.tools/python').is_dir())
sys.path.insert(0,str(W/'.tools/python'))
from PIL import Image
SHA=lambda b:hashlib.sha256(b).hexdigest()
ROM='51196cba923c315d0088b747b5cdee704f2ac057cd493f9ddf226fb7227302cf'
PAIR='083df884_083dfb6c'
MARKER='NATIVE KURT COMPLETE TABLE SURFACES'

def canonical(v):
    if isinstance(v,dict):return{k:canonical(x)for k,x in sorted(v.items())}
    if isinstance(v,list):return[canonical(x)for x in v]
    return v

def replace_rows(basepath,target,replacements,review):
    data=basepath.read_text(encoding='utf8');assert MARKER not in data
    tail=re.search(r'\nreturn rows\s*$',data);assert tail,basepath
    compact=review.write_compact([canonical(r)for r in replacements],None)[0]
    body='\n-- BEGIN '+MARKER+'\ndo\nlocal fixed=(function()\n'+compact+'\nend)()\nlocal lookup={}\nlocal function key(r)return table.concat({r.game,r.map,tostring(r.id),tostring(r.quadrant),tostring(r.x),tostring(r.y)},"|")end\nfor _,r in ipairs(fixed)do lookup[key(r)]=r end\nlocal n=0\nfor i,r in ipairs(rows)do local v=lookup[key(r)];if v then rows[i]=v;n=n+1 end end\nassert(n=='+str(len(replacements))+',"Kurt native surface scope changed")\nend\n-- END '+MARKER+'\nreturn rows\n'
    target.write_text(data[:tail.start()]+body,encoding='utf8')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--baseline',type=Path,required=True);ap.add_argument('--catalog-dir',type=Path,required=True)
    ap.add_argument('--mod-root',type=Path,default=Path(__file__).resolve().parents[1]);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    base,cat,mod,out=(v.resolve()for v in(a.baseline,a.catalog_dir,a.mod_root,a.output));assert base!=mod;out.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(mod/'tools'));import preview,catalog,gen2_extended_review as review
    data=json.loads((cat/'catalog.json').read_text(encoding='utf8'));assert data['rom_sha256']==ROM
    native=next(v for v in data['maps']if v['id']=='g03_m004');assert native['pair']==PAIR
    flat=Image.open(cat/'maps/g03_m004-flat.png').convert('RGBA');top=Image.open(cat/'pairs'/PAIR/'top.png').convert('RGBA')
    folder=mod/'assets/third_party/johto-hacks/azalea-native-workbench';prov=json.loads((base/folder.relative_to(mod)/'provenance.json').read_text(encoding='utf8'))
    old=Image.new('RGBA',(64,96));pieces={}
    for name,z in prov['source_modules'].items():
        f=base/z['asset'];assert SHA(f.read_bytes())==z['assetFileHash'];im=Image.open(f).convert('RGBA');assert SHA(im.tobytes())==z['assetPixelHash']
        x,y=z['native_xy'];old.paste(im,(x*16,y*16));pieces[name]=copy.deepcopy(z)
    assert sum(v[3]!=0 for v in old.get_flattened_data())==2837
    for y in range(96):
        for x in range(64):
            if old.getpixel((x,y))[3]:assert old.getpixel((x,y))==flat.getpixel((208+x,y))
    # These are the checker-gold interiors of the complete L-shaped counter.
    # Native TOP contains its tools/edges but leaves these BOTTOM pixels open.
    boxes=((1,38,63,58),(1,54,15,88));backing=Image.new('RGBA',old.size)
    for x0,y0,x1,y1 in boxes:backing.paste(flat.crop((208+x0,y0,208+x1,y1)),(x0,y0))
    whole=Image.alpha_composite(backing,old);added=[]
    for y in range(96):
        for x in range(64):
            before,after=old.getpixel((x,y)),whole.getpixel((x,y))
            if before[3]:assert after==before
            elif after[3]:
                assert after==flat.getpixel((208+x,y));assert after[:3]in((214,197,107),(247,239,148));added.append([x,y])
    assert len(added)==632 and sum(v[3]!=0 for v in whole.get_flattened_data())==3469
    whole.save(out/'complete-workbench-with-surface.png');updated={}
    for name,z in pieces.items():
        x,y=z['native_xy'];im=whole.crop((x*16,y*16,x*16+16,y*16+16));f=mod/z['asset'];im.save(f)
        z.update(assetFileHash=SHA(f.read_bytes()),assetPixelHash=SHA(im.tobytes()),opaque_pixels=sum(v[3]!=0 for v in im.get_flattened_data()));updated[z['asset']]=z
    prov.update(native_opaque_pixels=3469,whole_RGBA_sha256=SHA(whole.tobytes()),surface_restoration=dict(native_map='g03_m004',native_plane='bottom',native_local_rectangles=boxes,
        added_native_surface_pixels=632,all2837_previous_hardware_pixels_unchanged=True,all_added_pixels_are_native_checker_gold=True),source_modules=pieces,
        processing='Complete original pegboard, native TOP tools, edges and return retained. Restore632 exact native BOTTOM checker-gold surface pixels through its interior L mask. Generic exterior wall and floor remain transparent; independent chair561 stays excluded whole. Native1:1; no recolor, resize, source mechanics or furniture depth change.')
    (folder/'provenance.json').write_text(json.dumps(prov,indent=2)+'\n',encoding='utf8')
    # Update only the finite Kurt workbench asset receipts; retain all other catalog data.
    furniture=preview.read_reviewed(base/'lib/johto_furniture.lua');count=0;fixed_furniture=[]
    for r in furniture:
        if r.get('furniture')!='kurt_workbench':continue
        z=updated[r['asset']];r.update(assetFileHash=z['assetFileHash'],assetPixelHash=z['assetPixelHash'],compositionPixelHash=z['assetPixelHash'])
        r['evidence']='Complete native CrystalDust Kurt pegboard and L workbench. Native TOP tools/edges plus the exact BOTTOM checker-gold countertop and full return total3469opaque pixels. All2837previous hardware pixels preserved;632native surface pixels restored. Exterior wall/floor stays transparent; independent native chair remains omitted. All original source guards, NPC poses, collision, interactions, warp and depth stay unchanged.';count+=1;fixed_furniture.append(r)
    assert count==54
    replace_rows(base/'lib/johto_furniture.lua',mod/'lib/johto_furniture.lua',fixed_furniture,review)
    fixture=catalog.read_lua(base/'tests/kurt_workbench_native_alpha.lua')
    for asset,z in updated.items():
        im=Image.open(mod/asset).convert('RGBA');fixture['assets'][asset]=dict(hash=z['assetFileHash'],mask=''.join('1'if v[3]else'0'for v in im.get_flattened_data()))
    from newbark_building_review import lua
    (mod/'tests/kurt_workbench_native_alpha.lua').write_text('-- Complete native CrystalDust workbench including bottom-plane counter surfaces.\nreturn '+lua(canonical(fixture))+'\n',encoding='utf8')
    # The native dining table has four complete TOP modules, including its lower frame.
    table=Image.new('RGBA',(32,32));mids=[]
    for y in range(2):
        for x in range(2):
            mid=native['grid'][(4+y)*17+8+x]&1023;mids.append(mid);table.paste(top.crop((mid%16*16,mid//16*16,mid%16*16+16,mid//16*16+16)),(x*16,y*16))
    assert mids==[200,201,208,209]and table.getbbox()==(1,1,31,32);table.save(out/'complete-native-dining-table.png')
    tf=mod/'assets/third_party/johto-hacks/kurt-native-table';tf.mkdir(parents=True,exist_ok=True);ta={}
    for y in range(2):
        for x in range(2):
            im=table.crop((x*16,y*16,x*16+16,y*16+16));f=tf/f'cell-{x}-{y}.png';im.save(f)
            ta[x,y]=dict(asset=f.relative_to(mod).as_posix(),assetFileHash=SHA(f.read_bytes()),assetPixelHash=SHA(im.tobytes()),native_mid=mids[y*2+x],native_plane='top',native_map='g03_m004',native_xy=[8+x,4+y])
    tp=dict(origin='Complete native CrystalDust Kurt dining table, all four TOP modules including lower front and feet.',credit='Pokemon CrystalDust / Sierraffinity and DoMoreAwesome Games',sourceUrl='https://github.com/Sierraffinity/CrystalDust',rom_sha256=ROM,pair=PAIR,source_top_sha256=SHA((cat/'pairs'/PAIR/'top.png').read_bytes()),native_size=[32,32],alpha_bounds=table.getbbox(),native_opaque_pixels=928,whole_RGBA_sha256=SHA(table.tobytes()),native_scale=1,source_modules={f'cell-{x}-{y}':z for(x,y),z in ta.items()})
    (tf/'provenance.json').write_text(json.dumps(tp,indent=2)+'\n',encoding='utf8')
    path='mappings/gen2_domestic_floor_audit.lua';rows=preview.read_reviewed(base/path);changes=[];checks=[];packed={};cache=Path(os.environ['APPDATA'])/'pokemon-love2d'
    for r in rows:
        if r.get('map')!='KURTS_HOUSE'or r.get('game')not in('gold','silver','crystal'):continue
        xy={(27,3):(0,0),(28,2):(1,0),(24,1):(0,1),(25,0):(1,1)}.get((r['id'],r['quadrant']))
        if xy is None:continue
        z=ta[xy];oldrow=copy.deepcopy(r);r.update(kind='third_party',asset=z['asset'],assetFileHash=z['assetFileHash'],assetPixelHash=z['assetPixelHash'],credit=tp['credit'],sourceUrl=tp['sourceUrl'],role='kurt_complete_crystaldust_dining_table')
        r['evidence']='Complete native CrystalDust Kurt32x32 dining table TOP200/201/208/209 including the continuous lower front and feet. Original four table source cells and both adjacent source cushions retained. No scale, partial modules, floor replacement, NPC movement, collision, scripts or warp changes.'
        r['compositionPixelHash']=SHA(preview.replacement_image(cache,r,packed,mod).tobytes());checks.append(r)
        changes.append(dict(game=r['game'],map=r['map'],id=r['id'],quadrant=r['quadrant'],xy=[7+xy[0],3+xy[1]],sourceHash=r['sourceHash'],old_asset=oldrow['asset'],new_asset=r['asset'],compositionPixelHash=r['compositionPixelHash']))
    assert len(changes)==12
    replace_rows(base/path,mod/path,checks,review)
    from types import SimpleNamespace
    validation=review.validate_batch(checks,SimpleNamespace(cache=cache,engine=W/'.work/tileshift-engine-0420'),mod);assert validation['rows_accepted']==12 and validation['rejected']==0
    proof=dict(status='passed',table_rows=12,workbench_furniture_rows=54,table_source_cells=changes,workbench_surface_pixels_added=632,
        workbench_opaque_pixels=3469,old_workbench_hardware_pixels_unchanged=2837,workbench_added_native_pixels=added,native_validation=validation,
        source_cushions_NPCs_collision_events_and_warps_unchanged=True,no_furniture_geometry_or_depth_changes=True)
    (out/'proof.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in proof.items()if k not in('table_source_cells','workbench_added_native_pixels')}))

if __name__=='__main__':main()
