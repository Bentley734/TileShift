"""Restore the whole native CrystalDust west-entry mat in Day Care only."""
from pathlib import Path
import argparse,copy,hashlib,json,os,re,sys
W=next(p for p in Path(__file__).resolve().parents if(p/'.tools/python').is_dir())
sys.path.insert(0,str(W/'.tools/python'))
from PIL import Image
SHA=lambda b:hashlib.sha256(b).hexdigest()
ROM='51196cba923c315d0088b747b5cdee704f2ac057cd493f9ddf226fb7227302cf'
PAIR='083df884_083df9a4'
MIDS=(682,685,683,686,684,707)
BOX=(11,12,29,36)
MARKER='COMPLETE NATIVE CRYSTALDUST DAY CARE WEST MAT'

def canonical(v):
    if isinstance(v,dict):return{k:canonical(x)for k,x in sorted(v.items())}
    if isinstance(v,list):return[canonical(x)for x in v]
    return v

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,required=True);p.add_argument('--catalog-dir',type=Path,required=True)
    p.add_argument('--mod-root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    base,cat,mod,out=(v.resolve()for v in(a.baseline,a.catalog_dir,a.mod_root,a.output));assert base!=mod;out.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(mod/'tools'));import preview,gen2_extended_review as review
    c=json.loads((cat/'catalog.json').read_text(encoding='utf8'));assert c['rom_sha256']==ROM
    source=next(m for m in c['maps']if m['id']=='g22_m000');assert source['pair']==PAIR
    assert [source['grid'][y*source['width']+x]&1023 for y in(3,4,5)for x in(0,1)]==list(MIDS)
    planes={n:Image.open(cat/'pairs'/PAIR/(n+'.png')).convert('RGBA')for n in('top','bottom','flat')}
    assembled={n:Image.new('RGBA',(32,48))for n in planes}
    for q,mid in enumerate(MIDS):
        box=(mid%16*16,mid//16*16,mid%16*16+16,mid//16*16+16)
        for n,atlas in planes.items():assembled[n].paste(atlas.crop(box),(q%2*16,q//2*16))
    top=assembled['top'];assert top.getbbox()==BOX
    whole=top.crop(BOX);assert whole.size==(18,24)and all(p[3]==255 for p in whole.get_flattened_data())
    assert SHA(whole.tobytes())=='bda660a842d9b8f76f3ff4aaedc051a73c5d157bc3e7445a61c12df10d98b63a'
    assert whole.tobytes()==assembled['flat'].crop(BOX).tobytes()
    # Exterior-only alpha removal retains every one of the six TOP modules' native pixels.
    assert sum(p[3]!=0 for p in top.get_flattened_data())==432
    canvas=Image.new('RGBA',(32,32));canvas.paste(whole,(0,4));whole.save(out/'complete-native-west-mat18x24.png')
    folder=mod/'assets/third_party/johto-hacks/crystaldust-daycare-west-mat';folder.mkdir(parents=True,exist_ok=True)
    parts={}
    for y in range(2):
        for x in range(2):
            piece=canvas.crop((x*16,y*16,x*16+16,y*16+16));path=folder/f'cell-{x}-{y}.png';piece.save(path)
            parts[(x,y)]=dict(asset=path.relative_to(mod).as_posix(),assetFileHash=SHA(path.read_bytes()),assetPixelHash=SHA(piece.tobytes()),native_size=[16,16],native_scale=1,whole_mat_slice=[x*16,y*16,x*16+16,y*16+16])
    provenance=dict(origin='Complete native CrystalDust Day Care west-entry mat, including its full connected frame and shadow.',
        credit='Pokemon CrystalDust / Sierraffinity and DoMoreAwesome Games',sourceUrl='https://github.com/Sierraffinity/CrystalDust',
        rom_sha256=ROM,source_map='g22_m000',pair=PAIR,source_top_sha256=SHA((cat/'pairs'/PAIR/'top.png').read_bytes()),
        source_flat_sha256=SHA((cat/'pairs'/PAIR/'flat.png').read_bytes()),source_bottom_sha256=SHA((cat/'pairs'/PAIR/'bottom.png').read_bytes()),
        source_mids=list(MIDS),source_native_cells=[[x,y]for y in(3,4,5)for x in(0,1)],source_assembly_size=[32,48],whole_native_bounds=list(BOX),
        native_size=[18,24],native_opaque_pixels=432,whole_RGBA_sha256=SHA(whole.tobytes()),native_scale=1,world_xy=[0,84],
        processing='Reassemble all six whole native TOP modules682/685/683/686/684/707. The entire18x24 opaque native mat is the assembly alpha bounds; every native pixel equals FLAT. Remove only empty exterior alpha, translate unscaled to(0,84), then partition a transparent32x32 canvas into four16x16 mapping cells. All432pixels, complete continuous frame, corners and shadow remain. Existing local floor backs all592transparent pixels. No mirroring, rotation, resizing, drawing, hardware clipping, source interaction or actor/collision/warp change.',
        source_modules={f'cell-{x}-{y}':z for(x,y),z in parts.items()})
    (folder/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf8')
    path='mappings/johto_rooms_finish.lua';rows=preview.read_reviewed(base/path);fixed=[];scope=[];packed={};cache=Path(os.environ['APPDATA'])/'pokemon-love2d'
    wanted={(0,5),(1,5),(0,6),(1,6)}
    for old in rows:
        if old.get('map')!='DAY_CARE'or old.get('game')not in('gold','silver','crystal'):continue
        cells=old.get('sourceCells',[])
        if len(cells)!=1 or tuple(cells[0])not in wanted:continue
        x,y=cells[0];assert 'x'not in old and'y'not in old
        assert (old['id'],old['quadrant'])=={(0,5):(23,2),(1,5):(23,3),(0,6):(27,0),(1,6):(27,1)}[(x,y)]
        assert old['sourceHash']==('cf53eb42896d98252c6ffa963bb0827228c6ad3e3d8b5c9aed92aaf6751184de'if x==0 else'1544172bfb611243682067ae86c1fc829b5a9a9ef70cb3ad5f0954b74bb78f76')
        assert old['role']==('johto_house_side_entry_rug'if x==0 else'johto_house_plain_floor')
        assert old['sourceCollision']==(118 if x==0 else 0)
        r=copy.deepcopy(old);floor=copy.deepcopy(old.get('base',old.get('donor')));assert floor['id']==1 and floor['hash']=='eba7bafe3b8bf236ae3602939529c34fad55c66c94aed6bb6cb4681b08fe2af6'
        for k in('parts','donor','animated','animation','frames','foreground','occludes'):r.pop(k,None)
        z=parts[(x,y-5)];r.update(x=x,y=y,kind='third_party',base=floor,asset=z['asset'],assetFileHash=z['assetFileHash'],assetPixelHash=z['assetPixelHash'],
            credit=provenance['credit'],sourceUrl=provenance['sourceUrl'],role=f'daycare_complete_crystaldust_west_mat_{x}_{y-5}',
            evidence='Complete native CD west-facing entrance mat, all432 native pixels and continuous frame/shadow, at1:1 world(0,84). Full18x24 mat centered in the two original west-warp rows;2px frame continues into adjacent existing floor. All source glyph metadata, original floor, table/chairs, keepers, collisions, scripts and warps unchanged.')
        image=preview.replacement_image(cache,r,packed,mod)
        floor_image=preview.native_donor(cache,floor,packed);foreground=Image.open(mod/z['asset']).convert('RGBA')
        for a,b,f in zip(image.get_flattened_data(),floor_image.get_flattened_data(),foreground.get_flattened_data()):assert a==(f if f[3]else b)
        r['compositionPixelHash']=SHA(image.tobytes());fixed.append(canonical(r))
        scope.append(dict(game=r['game'],map=r['map'],id=r['id'],quadrant=r['quadrant'],x=x,y=y,xy=[x,y],sourceHash=r['sourceHash'],sourceCollision=r['sourceCollision'],sourceFiles=r['sourceFiles'],sourcePalettes=r['sourcePalettes'],sourcePriority=r['sourcePriority'],base=floor,asset=r['asset'],old_RGBA_sha256=SHA(preview.replacement_image(cache,old,packed,base).tobytes()),new_RGBA_sha256=r['compositionPixelHash']))
    assert len(fixed)==12 and len({(r['game'],r['id'],r['quadrant'])for r in fixed})==12
    raw=(base/path).read_bytes();assert MARKER.encode()not in raw;tail=re.search(br'\r?\nreturn rows\s*$',raw);assert tail
    compact=review.write_compact(fixed,None)[0]
    text='\n-- BEGIN '+MARKER+'\ndo\nlocal fixed=(function()\n'+compact+'\nend)()\nassert(#fixed==12,"DayCare west mat source scope changed")\nfor _,r in ipairs(fixed)do\n assert(r.x==r.sourceCells[1][1]and r.y==r.sourceCells[1][2],"DayCare west mat position changed")\n rows[#rows+1]=r\nend\nend\n-- END '+MARKER+'\nreturn rows\n'
    suffix=text.encode('utf8');suffix=suffix.replace(b'\n',b'\r\n')if b'\r\n'in raw else suffix;(mod/path).write_bytes(raw[:tail.start()]+suffix)
    from types import SimpleNamespace
    validation=review.validate_batch(fixed,SimpleNamespace(cache=cache,engine=W/'.work/tileshift-engine-0420'),mod);assert validation['rows_accepted']==12 and validation['rejected']==0
    proof=dict(status='passed',changed_rows=12,added_positioned_rows=12,all_baseline_regular_rows_retained=True,changed_maps=['DAY_CARE'],whole_native_size=[18,24],whole_native_opaque_pixels=432,whole_native_RGBA_sha256=SHA(whole.tobytes()),world_bounds=[0,84,18,108],
        all_six_TOP_modules_whole_native_ink_preserved=True,whole_native_FLAT_equality=True,no_crop_mirror_rotation_resize_or_drawing=True,local_floor_under_all592_alpha_pixels=True,
        all_source_guards_table_chairs_keepers_collision_scripts_warps_preserved=True,no_runtime_API_or_furniture_changes=True,selected_source_cells=scope,native_validation=validation)
    (out/'proof.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in proof.items()if k!='selected_source_cells'}))

if __name__=='__main__':main()
