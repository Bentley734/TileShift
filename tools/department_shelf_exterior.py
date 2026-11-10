"""Remove legacy blue UNDER-floor triangles outside complete native shelf hardware."""
from pathlib import Path
from types import SimpleNamespace
import argparse,copy,hashlib,json,os,re,sys
W=next(p for p in Path(__file__).resolve().parents if(p/'.tools/python').is_dir())
sys.path.insert(0,str(W/'.tools/python'))
SHA=lambda b:hashlib.sha256(b).hexdigest()
MODULE='mappings/gen2_facility_floor_audit.lua'
MARKER='NATIVE DEPARTMENT SHELF EXTERIOR FLOOR'
MAPS={'GOLDENROD_DEPT_STORE_2F','GOLDENROD_DEPT_STORE_3F','GOLDENROD_DEPT_STORE_4F'}

def canonical(v):
    if isinstance(v,dict):return{k:canonical(x)for k,x in sorted(v.items())}
    if isinstance(v,list):return[canonical(x)for x in v]
    return v

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--mod-root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();base,mod,out=(v.resolve()for v in(a.baseline,a.mod_root,a.output));assert base!=mod
    out.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(mod/'tools'))
    import preview,gen2_extended_review as review
    from newbark_building_review import lua
    cache=Path(os.environ['APPDATA'])/'pokemon-love2d';packed={};fixes=[];scope=[]
    oldrows=preview.read_reviewed(base/MODULE)
    for index,old in enumerate(oldrows):
        if old['game']not in('gold','silver','crystal')or old.get('map')not in MAPS:continue
        if old['role']!='johto_shop_complete_stock_display':continue
        if not any(p.get('donor',{}).get('id')==674 for p in old.get('parts',[])):continue
        assert old.get('x')is None and len(old['parts'])==8
        first=old['parts'][0]
        assert first['donor']['game']=='firered'and first['donor']['tileset']=='building__rom_082d4bcc'
        assert first['layers']==['mid','over']and first['x']==first['y']==first['srcX']==first['srcY']==0
        assert first['w']==16 and first['h']==9
        ink=preview.native_donor(cache,first['donor'],packed,first['layers'],first['layerHashes'])
        assert sum(v[3]>0 for v in ink.get_flattened_data())==128 and ink.getbbox()==(0,0,16,8)
        new=copy.deepcopy(old);new['parts']=[copy.deepcopy(first)];new['parts'][0]['h']=16
        prior=preview.replacement_image(cache,old,packed,base);image=preview.replacement_image(cache,new,packed,mod)
        floor=preview.native_donor(cache,old['base'],packed)
        removed=[];retained=0
        for y in range(16):
            for x in range(16):
                native=ink.getpixel((x,y));before=prior.getpixel((x,y));after=image.getpixel((x,y))
                if native[3]:assert before==after==native;retained+=1
                else:
                    assert after==floor.getpixel((x,y))
                    if before!=after:removed.append([x,y])
        assert retained==128 and len(removed)==84 and all(y>=9 for x,y in removed)
        new['compositionPixelHash']=SHA(image.tobytes())
        audit=new.get('facilityFloorAudit',{})
        for layer in audit.get('detached_layers',[]):
            if layer.get('part')==0:layer['outside_native_pixels']=128;layer['retained_native_pixels']=128
        new['departmentShelfExterior']={'native_foreground_pixels':128,'removed_unrelated_under_floor_pixels':84,
            'native_layer_hashes':first['layerHashes'],'native_donor':first['donor'],'scale':1,'local_floor':old['base']}
        new['evidence']=old['evidence']+' Department shelf exterior correction: complete fingerprinted MID+OVER across all16 rows retains all128 native shelf/glass/frame/gray-foot pixels. The84 legacy UNDER-floor triangle pixels are excluded; the existing checked orange floor shows through. No color-key mask, recolor, hardware crop, source geometry or interaction change.'
        fixes.append(canonical(new))
        for xy in old['sourceCells']:
            scope.append({'game':old['game'],'map':old['map'],'xy':xy,'id':old['id'],'quadrant':old['quadrant'],
                'sourceHash':old['sourceHash'],'sourceCollision':old['sourceCollision'],'sourceFiles':old['sourceFiles'],
                'sourcePalettes':old['sourcePalettes'],'sourcePriority':old['sourcePriority'],'old_row':old,'new_row':new,
                'removed_local_pixels':removed,'retained_native_pixels':128,'old_RGBA_sha256':SHA(prior.tobytes()),'new_RGBA_sha256':SHA(image.tobytes())})
    assert len(fixes)==9 and len(scope)==21
    raw=(base/MODULE).read_bytes();tail=re.search(br'\r?\nreturn rows\s*$',raw);assert tail and MARKER.encode()not in raw
    code='\n-- BEGIN '+MARKER+'\ndo\nlocal fixes='+lua(canonical(fixes))+'''
local function key(r)return r.game..':'..r.map..':'..r.id..':'..r.quadrant end
local lookup={};for _,r in ipairs(fixes)do assert(not lookup[key(r)]);lookup[key(r)]=r end
local n=0
for i,r in ipairs(rows)do if r.map then local fix=lookup[key(r)];if fix then rows[i]=fix;n=n+1 end end end
assert(n==9,'Department shelf exterior source scope changed')
end
-- END '''+MARKER+'\nreturn rows\n'
    if b'\r\n'in raw:code=code.replace('\n','\r\n')
    (mod/MODULE).write_bytes(raw[:tail.start()]+code.encode())
    validation=review.validate_batch(fixes,SimpleNamespace(cache=cache,engine=W/'.work/tileshift-engine-0420'),mod)
    assert validation['rows_accepted']==9 and validation['rejected']==0
    proof={'status':'passed','replaced_existing_rows':9,'physical_source_cells':21,'removed_blue_floor_pixels':1764,
        'complete_native_hardware_pixels_retained':2688,'native_pixel_scale':1,'source_scope':scope,'native_validation':validation,
        'no_shared_PNG_or_runtime_changes':True,'all_untargeted_rows_unchanged':True,'source_collision_NPC_warps_scripts_unchanged':True}
    (out/'proof.json').write_text(json.dumps(canonical(proof),indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in proof.items()if k!='source_scope'}))

if __name__=='__main__':main()
