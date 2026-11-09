"""Reproduce the complete native CrystalDust L workbench, including all sides."""
from pathlib import Path
import argparse,copy,hashlib,json,re,sys
W=next(p for p in Path(__file__).resolve().parents if(p/'.tools/python').is_dir())
sys.path.insert(0,str(W/'.tools/python'))
from PIL import Image
SHA=lambda b:hashlib.sha256(b).hexdigest()
PAIR='083df884_083dfb6c'
ROM='51196cba923c315d0088b747b5cdee704f2ac057cd493f9ddf226fb7227302cf'
MARKER='COMPLETE NATIVE KURT WORKBENCH SIDES'

def canonical(v):
    if isinstance(v,dict):return{k:canonical(x)for k,x in sorted(v.items())}
    if isinstance(v,list):return[canonical(x)for x in v]
    return v

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--catalog-dir',type=Path,required=True)
    p.add_argument('--mod-root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    base,cat,mod,out=(v.resolve()for v in(a.baseline,a.catalog_dir,a.mod_root,a.output));assert base!=mod;out.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(mod/'tools'));import catalog,preview,gen2_extended_review as review
    from newbark_building_review import lua
    c=json.loads((cat/'catalog.json').read_text(encoding='utf8'));assert c['rom_sha256']==ROM
    m=next(v for v in c['maps']if v['id']=='g03_m004');assert m['pair']==PAIR
    top=Image.open(cat/'pairs'/PAIR/'top.png').convert('RGBA');flat=Image.open(cat/'maps/g03_m004-flat.png').convert('RGBA')
    folder=Path('assets/third_party/johto-hacks/azalea-native-workbench');prov=json.loads((base/folder/'provenance.json').read_text(encoding='utf8'))
    old=Image.new('RGBA',(64,96))
    for z in prov['source_modules'].values():
        f=base/z['asset'];assert SHA(f.read_bytes())==z['assetFileHash'];im=Image.open(f).convert('RGBA');assert SHA(im.tobytes())==z['assetPixelHash'];x,y=z['native_xy'];old.paste(im,(x*16,y*16))
    assert sum(v[3]!=0 for v in old.get_flattened_data())==3469
    # Reconstruct the WHOLE physical object, not a palette or missing-pixel mask.
    # All native TOP modules retain the tools, cabinet fascia, feet and support.
    whole=Image.new('RGBA',(64,96))
    for y in range(6):
        for x in range(4):
            mid=m['grid'][y*17+13+x]&1023
            if(x,y)==(2,4):assert mid==561;continue # independent native chair
            whole.paste(top.crop((mid%16*16,mid//16*16,mid%16*16+16,mid//16*16+16)),(x*16,y*16))
    whole.paste(flat.crop((222,6,266,37)),(14,6)) # complete framed pegboard
    whole.paste(flat.crop((208,64,224,80)),(0,64)) # complete native shaft567
    for x0,y0,x1,y1 in((0,38,64,58),(0,54,16,88)):
        whole.paste(flat.crop((208+x0,y0,208+x1,y1)),(x0,y0))
    assert whole.getbbox()==(0,6,64,96)and SHA(whole.tobytes())=='53500fc2ee369c8decd54ea0082386c2b565058df1eb0d0c69bce43823c4cdac'
    added=[]
    for y in range(96):
        for x in range(64):
            before,after=old.getpixel((x,y)),whole.getpixel((x,y))
            if before[3]:assert before==after
            elif after[3]:assert after==flat.getpixel((208+x,y));added.append([x,y])
    assert len(added)==28 and sum(v[3]!=0 for v in whole.get_flattened_data())==3497
    runs=((0,38,88),(15,58,88),(63,38,56))
    for x,y0,y1 in runs:
        for y in range(y0,y1):assert whole.getpixel((x,y))==(82,82,107,255)
    whole.save(out/'complete-native-workbench-with-sides.png');updated={}
    for z in prov['source_modules'].values():
        x,y=z['native_xy'];im=whole.crop((x*16,y*16,x*16+16,y*16+16));f=mod/z['asset'];im.save(f)
        z.update(assetFileHash=SHA(f.read_bytes()),assetPixelHash=SHA(im.tobytes()),opaque_pixels=sum(v[3]!=0 for v in im.get_flattened_data()));updated[z['asset']]=z
    prov.update(native_opaque_pixels=3497,whole_RGBA_sha256=SHA(whole.tobytes()),native_body_and_sides_review=dict(
        complete_native_tabletop_and_rim_rectangles=[[0,38,64,58],[0,54,16,88]],native_shaft_mid=567,
        all3469_prior_pixels_unchanged=True,restored_native_side_pixels=28,continuous_side_runs=runs,
        complete_native_front_fascia_supports_and_endcap_preserved=True),processing='Full native TOP tools, front fascia, supports and feet; complete native framed pegboard and shaft567; full native FLAT tabletop/rim and return regions. Restores28real side pixels without drawing or scaling. Native floor, generic wall and independent chair remain excluded. All source geometry, depth and NPC poses unchanged.')
    (mod/folder/'provenance.json').write_text(json.dumps(prov,indent=2)+'\n',encoding='utf8')
    allrows=preview.read_reviewed(base/'lib/johto_furniture.lua');fixed=[]
    for r in allrows:
        if r.get('furniture')!='kurt_workbench':continue
        z=updated[r['asset']];r.update(assetFileHash=z['assetFileHash'],assetPixelHash=z['assetPixelHash'],compositionPixelHash=z['assetPixelHash'],
            evidence='Complete native CrystalDust L workbench: all TOP tools, front fascia, supports and endcap, full framed pegboard, native shaft567, and full native tabletop/return side regions. All3469prior pixels preserved;28original side-edge pixels restored. Continuous authentic left/right outlines through the entire return and horizontal counter. Native1:1; source geometry, NPC poses, collision, scripts, warp and foreground depth unchanged.')
        fixed.append(canonical(r))
    assert len(fixed)==54
    text=(base/'lib/johto_furniture.lua').read_text(encoding='utf8');assert MARKER not in text;tail=re.search(r'\nreturn rows\s*$',text);assert tail
    compact=review.write_compact(fixed,None)[0]
    footer='\n-- BEGIN '+MARKER+'\ndo\nlocal fixed=(function()\n'+compact+'\nend)()\nlocal lookup={}\nlocal function key(r)return table.concat({r.game,r.map,tostring(r.x),tostring(r.y)},"|")end\nfor _,r in ipairs(fixed)do lookup[key(r)]=r end\nlocal n=0\nfor i,r in ipairs(rows)do if r.furniture=="kurt_workbench"then rows[i]=assert(lookup[key(r)]);n=n+1 end end\nassert(n==54,"Kurt side source scope changed")\nend\n-- END '+MARKER+'\nreturn rows\n'
    (mod/'lib/johto_furniture.lua').write_text(text[:tail.start()]+footer,encoding='utf8')
    fixture=catalog.read_lua(base/'tests/kurt_workbench_native_alpha.lua')
    for asset,z in updated.items():
        im=Image.open(mod/asset).convert('RGBA');fixture['assets'][asset]=dict(hash=z['assetFileHash'],mask=''.join('1'if v[3]else'0'for v in im.get_flattened_data()))
    (mod/'tests/kurt_workbench_native_alpha.lua').write_text('-- Complete native CrystalDust workbench sides, body, tools and surface.\nreturn '+lua(canonical(fixture))+'\n',encoding='utf8')
    proof=dict(status='passed',changed_workbench_rows=54,old_native_pixels_preserved=3469,restored_native_side_pixels=28,new_native_opaque_pixels=3497,
        whole_RGBA_sha256=SHA(whole.tobytes()),added_native_pixels=added,continuous_side_runs=runs,source_world_origin=[192,-16],
        native_front_fascia_supports_endcap_and_pegboard_complete=True,table_source_cushions_NPC_poses_collision_warps_and_depth_unchanged=True)
    (out/'proof.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in proof.items()if k!='added_native_pixels'}))

if __name__=='__main__':main()
