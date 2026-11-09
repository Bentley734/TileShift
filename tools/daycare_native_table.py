"""Replace only Day Care's four-cell table with the complete native CD family."""
from pathlib import Path
import argparse,copy,hashlib,json,os,re,sys
W=next(p for p in Path(__file__).resolve().parents if(p/'.tools/python').is_dir())
sys.path.insert(0,str(W/'.tools/python'))
from PIL import Image
SHA=lambda b:hashlib.sha256(b).hexdigest()
ROM='51196cba923c315d0088b747b5cdee704f2ac057cd493f9ddf226fb7227302cf'
PAIR='083df884_083df9a4'
MIDS=(541,543,549,551)
MARKER='COMPLETE NATIVE CRYSTALDUST DAY CARE TABLE'

def canonical(v):
    if isinstance(v,dict):return{k:canonical(x)for k,x in sorted(v.items())}
    if isinstance(v,list):return[canonical(x)for x in v]
    return v

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--catalog-dir',type=Path,required=True)
    p.add_argument('--mod-root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    base,cat,mod,out=(v.resolve()for v in(a.baseline,a.catalog_dir,a.mod_root,a.output));assert base!=mod;out.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(mod/'tools'));import preview,catalog,gen2_extended_review as review
    c=json.loads((cat/'catalog.json').read_text(encoding='utf8'));assert c['rom_sha256']==ROM
    source=next(m for m in c['maps']if m['id']=='g22_m000');assert source['pair']==PAIR
    assert [source['grid'][y*source['width']+x]&1023 for x,y in((6,4),(7,4),(6,5),(7,5))]==[541,543,665,551]
    top=Image.open(cat/'pairs'/PAIR/'top.png').convert('RGBA');flat=Image.open(cat/'pairs'/PAIR/'flat.png').convert('RGBA')
    whole=Image.new('RGBA',(32,32));reference=Image.new('RGBA',(32,32));parts={}
    folder=mod/'assets/third_party/johto-hacks/crystaldust-daycare-table';folder.mkdir(parents=True,exist_ok=True)
    for q,mid in enumerate(MIDS):
        box=(mid%16*16,mid//16*16,mid%16*16+16,mid//16*16+16);piece=top.crop(box);x,y=q%2,q//2
        whole.paste(piece,(x*16,y*16));reference.paste(flat.crop(box),(x*16,y*16));path=folder/f'cell-{x}-{y}.png';piece.save(path)
        parts[q]=dict(asset=path.relative_to(mod).as_posix(),assetFileHash=SHA(path.read_bytes()),assetPixelHash=SHA(piece.tobytes()),
            native_mid=mid,native_plane='top',native_atlas_xyxy=box,native_size=[16,16],native_scale=1)
    assert whole.getbbox()==(0,0,32,32)and sum(v[3]!=0 for v in whole.get_flattened_data())==1022
    # Whole TOP already includes every surface, lower front, feet and shadow.
    # The only two holes are actual carpet pixels outside the upper corners.
    holes=[b for a,b in zip(whole.get_flattened_data(),reference.get_flattened_data())if not a[3]]
    assert holes==[(206,148,197,255)]*2
    whole.save(out/'complete-native-daycare-table32.png')
    provenance=dict(origin='Whole native CrystalDust Day Care low table with complete front, feet and shadow.',
        credit='Pokemon CrystalDust / Sierraffinity and DoMoreAwesome Games',sourceUrl='https://github.com/Sierraffinity/CrystalDust',
        rom_sha256=ROM,source_map='g22_m000',pair=PAIR,source_top_sha256=SHA((cat/'pairs'/PAIR/'top.png').read_bytes()),
        source_flat_sha256=SHA((cat/'pairs'/PAIR/'flat.png').read_bytes()),native_size=[32,32],native_opaque_pixels=1022,
        whole_RGBA_sha256=SHA(whole.tobytes()),native_scale=1,unobstructed_native_lower_left_variant=dict(mid=549,replaces_counter_contact_mid=665),
        processing='Four entire16x16 TOP modules541/543/549/551 at1:1. Native549 is the unobstructed lower-left table variant; native DayCare665 contains a touching counter and is intentionally not used. Complete lower front/feet/shadow retained. Only2genuine outside carpet corners are transparent. No drawing, resizing, clipping, copied carpet or furniture/collision/NPC relocation.',
        source_modules={f'cell-{q%2}-{q//2}':z for q,z in parts.items()})
    (folder/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf8')
    path='mappings/johto_rooms_finish.lua';rows=preview.read_reviewed(base/path);fixed=[];scope=[];packed={};cache=Path(os.environ['APPDATA'])/'pokemon-love2d'
    for old in rows:
        if old.get('map')!='DAY_CARE'or old.get('game')not in('gold','silver','crystal')or not old.get('role','').startswith('johto_house_complete_table_'):continue
        q=int(old['role'].rsplit('_',1)[1]);assert q in parts
        r=copy.deepcopy(old)
        for k in('parts','donor','animated','animation','frames','foreground','occludes'):r.pop(k,None)
        z=parts[q];r.update(kind='third_party',asset=z['asset'],assetFileHash=z['assetFileHash'],assetPixelHash=z['assetPixelHash'],
            credit=provenance['credit'],sourceUrl=provenance['sourceUrl'],role='daycare_complete_crystaldust_table_'+str(q),
            evidence='Complete native CrystalDust DayCare32x32 low table541/543/549/551. Every native surface, lower front, feet and shadow retained at1:1; unobstructed549 excludes the contacting counter665. Original four table cells, exact selected floor backing, bothkeepers, allfour chairs, source collision, interactions and warps unchanged.')
        r['compositionPixelHash']=SHA(preview.replacement_image(cache,r,packed,mod).tobytes());fixed.append(canonical(r))
        scope.append(dict(game=r['game'],map=r['map'],id=r['id'],quadrant=r['quadrant'],xy=[3+q%2,3+q//2],sourceHash=r['sourceHash'],
            sourceCollision=r['sourceCollision'],sourceFiles=r['sourceFiles'],sourcePalettes=r['sourcePalettes'],sourcePriority=r['sourcePriority'],base=r['base'],
            asset=r['asset'],native_mid=MIDS[q],old_RGBA_sha256=SHA(preview.replacement_image(cache,old,packed,base).tobytes()),new_RGBA_sha256=r['compositionPixelHash']))
    assert len(fixed)==12
    raw=(base/path).read_bytes();assert MARKER.encode()not in raw;tail=re.search(br'\r?\nreturn rows\s*$',raw);assert tail
    compact=review.write_compact(fixed,None)[0]
    text='\n-- BEGIN '+MARKER+'\ndo\nlocal fixed=(function()\n'+compact+'\nend)()\nlocal lookup={}\nlocal function key(r)return r.game..":"..r.id..":"..r.quadrant end\nfor _,r in ipairs(fixed)do lookup[key(r)]=r end\nlocal n=0\nfor i,r in ipairs(rows)do if r.map=="DAY_CARE"and r.role and r.role:match("^johto_house_complete_table_[0-3]$")then rows[i]=assert(lookup[key(r)]);n=n+1 end end\nassert(n==12,"DayCare table source scope changed")\nend\n-- END '+MARKER+'\nreturn rows\n'
    suffix=text.encode('utf8');suffix=suffix.replace(b'\n',b'\r\n')if b'\r\n'in raw else suffix
    (mod/path).write_bytes(raw[:tail.start()]+suffix)
    from types import SimpleNamespace
    validation=review.validate_batch(fixed,SimpleNamespace(cache=cache,engine=W/'.work/tileshift-engine-0420'),mod);assert validation['rows_accepted']==12 and validation['rejected']==0
    proof=dict(status='passed',changed_rows=12,changed_maps=['DAY_CARE'],whole_native_size=[32,32],whole_native_opaque_pixels=1022,
        whole_native_RGBA_sha256=SHA(whole.tobytes()),all_four_whole_native_modules_retained=True,all_transparent_pixels_are_exterior_background=True,
        source_NPC_positions_four_chairs_collision_interactions_warps_and_floor_unchanged=True,no_runtime_API_or_furniture_geometry_changes=True,
        selected_source_cells=scope,native_validation=validation)
    (out/'proof.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in proof.items()if k!='selected_source_cells'}))

if __name__=='__main__':main()
