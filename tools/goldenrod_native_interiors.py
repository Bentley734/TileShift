"""Polish only Goldenrod Gym, Flower Shop and the Bike Shop tools wall."""
from pathlib import Path
import argparse,copy,hashlib,json,os,re,sys
W=next(p for p in Path(__file__).resolve().parents if(p/'.tools/python').is_dir())
sys.path.insert(0,str(W/'.tools/python'))
from PIL import Image
SHA=lambda b:hashlib.sha256(b).hexdigest()
ROM='51196cba923c315d0088b747b5cdee704f2ac057cd493f9ddf226fb7227302cf'
HOUSE='083df884_083df9a4';BIKE='083df884_083dfb6c'
MARKER='NATIVE CRYSTALDUST GOLDENROD INTERIOR DETAILS'
MAPS={'GOLDENROD_GYM':'g11_m003','GOLDENROD_FLOWER_SHOP':'g11_m008','GOLDENROD_BIKE_SHOP':'g11_m004'}
MODULES=('mappings/johto_gyms_finish.lua','mappings/johto_rooms_finish.lua')

def canonical(v):
    if isinstance(v,dict):return{k:canonical(x)for k,x in sorted(v.items())}
    if isinstance(v,list):return[canonical(x)for x in v]
    return v

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--catalog-dir',type=Path,required=True)
    p.add_argument('--mod-root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    base,cat,mod,out=(v.resolve()for v in(a.baseline,a.catalog_dir,a.mod_root,a.output));assert base!=mod;out.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(mod/'tools'));import preview,gen2_extended_review as review
    cache=Path(os.environ['APPDATA'])/'pokemon-love2d';packed={};data={};planes={};assets={};scope=[];allfixed=[];supers=[]
    catalog=json.loads((cat/'catalog.json').read_text(encoding='utf8'));assert catalog['rom_sha256']==ROM
    for name,native in MAPS.items():assert next(m for m in catalog['maps']if m['id']==native)['pair']==(BIKE if name=='GOLDENROD_BIKE_SHOP'else HOUSE)
    folder=mod/'assets/third_party/johto-hacks/crystaldust-goldenrod-interiors';folder.mkdir(parents=True,exist_ok=True)
    native_receipts={}
    def native(mid,plane='top',pair=HOUSE):
        key=pair,plane
        if key not in planes:planes[key]=Image.open(cat/'pairs'/pair/(plane+'.png')).convert('RGBA')
        box=(mid%16*16,mid//16*16,mid%16*16+16,mid//16*16+16);image=planes[key].crop(box)
        native_receipts[f'{pair}:{plane}:{mid}']=dict(pair=pair,plane=plane,mid=mid,atlas_xyxy=box,atlas_sha256=SHA((cat/'pairs'/pair/(plane+'.png')).read_bytes()),RGBA_sha256=SHA(image.tobytes()),opaque_pixels=sum(v[3]!=0 for v in image.get_flattened_data()))
        return image
    def backed(floor,ink):
        image=native(floor,'bottom');result=Image.alpha_composite(image,ink)
        for result_pixel,floor_pixel,ink_pixel in zip(result.get_flattened_data(),image.get_flattened_data(),ink.get_flattened_data()):assert result_pixel==(ink_pixel if ink_pixel[3]else floor_pixel)
        return result
    def retained_foreground(r):
        copyrow=copy.deepcopy(r);copyrow.pop('base',None);return preview.replacement_image(cache,copyrow,packed,base)
    def candidate(r):
        name,role=r['map'],r.get('role','');game=r['game']
        if game not in data:data[game]=review.source(cache,game)
        c=review.cell_info(cache,game,data[game],r['tileset'],r['id'],r['quadrant'])
        if name=='GOLDENROD_GYM':
            if role=='johto_house_complete_single_flowerpot':
                assert c['tiles']in([7,8,23,24],[62,63,23,24]);mid=703 if c['tiles'][:2]==[62,63]else 694
                return backed(696,native(mid,'mid')),dict(family='gym_flower_planter'if mid==703 else'gym_green_planter',floor=[HOUSE,'bottom',696],whole_native_foreground=[HOUSE,'mid',mid])
            if role=='johto_bug_gym_clear_path':return native(696,'bottom'),dict(family='gym_pink_floor',whole_native_tile=[HOUSE,'bottom',696])
            if role in('johto_gym_complete_statue_head','johto_gym_complete_statue_plinth'):
                mid=700 if role.endswith('_head')else 701;return backed(696,native(mid)),dict(family='gym_statue_'+('head'if mid==700 else'base'),floor=[HOUSE,'bottom',696],whole_native_foreground=[HOUSE,'top',mid])
            if role.startswith('household_rug_'):return backed(696,retained_foreground(r)),dict(family='gym_retained_'+role,floor=[HOUSE,'bottom',696],retained_native_parts=r['parts'])
            raise AssertionError(('Unknown Gym source role',role))
        if name=='GOLDENROD_FLOWER_SHOP':
            if role=='johto_house_plain_floor':return native(530,'bottom'),dict(family='flower_gray_floor',whole_native_tile=[HOUSE,'bottom',530])
            if role=='johto_house_complete_single_flowerpot':return backed(530,native(690)),dict(family='flower_single_display',floor=[HOUSE,'bottom',530],whole_native_foreground=[HOUSE,'top',690])
            if role=='johto_house_native_potted_flowers':
                assert c['tiles']in([42,43,84,85],[84,85,94,95]);mid=656 if c['tiles'][:2]==[42,43]else 617
                return backed(530,native(mid)),dict(family='flower_tall_display_'+('head'if mid==656 else'base'),floor=[HOUSE,'bottom',530],whole_native_foreground=[HOUSE,'top',mid])
            if role.startswith('johto_house_complete_table_'):
                q=int(role.rsplit('_',1)[1]);mid=(541,543,549,551)[q]
                return backed(530,native(mid)),dict(family='flower_complete_table_'+str(q),floor=[HOUSE,'bottom',530],whole_native_foreground=[HOUSE,'top',mid])
            if role=='johto_house_native_potted_plant':
                assert r['donor']['id']in(87,95);mid=560 if r['donor']['id']==87 else 568
                return backed(530,native(mid)),dict(family='flower_complete_plant_'+('head'if mid==560 else'base'),floor=[HOUSE,'bottom',530],whole_native_foreground=[HOUSE,'top',mid])
            if role in('johto_house_chair_left','johto_house_entry_rug'):
                return backed(530,retained_foreground(r)),dict(family='flower_retained_'+role,floor=[HOUSE,'bottom',530],retained_native_parts=r['parts'])
            return None
        if name=='GOLDENROD_BIKE_SHOP':
            cells=r.get('sourceCells',[])
            if len(cells)!=1:return None
            x,y=cells[0]
            if 2<=x<=5 and y in(0,1):
                mid=((539,526,548,526),(522,534,524,521))[y][x-2]
                return native(mid,'flat',BIKE),dict(family=f'bike_complete_tool_wall_{x-2}_{y}',whole_native_tile=[BIKE,'flat',mid],source_native_xy=[x,y+1])
        return None
    for module in MODULES:
        oldrows=preview.read_reviewed(base/module);fixed=[]
        for index,old in enumerate(oldrows):
            if old.get('game')not in('gold','silver','crystal')or old.get('map')not in MAPS:continue
            chosen=candidate(old)
            if chosen is None:continue
            image,recipe=chosen;assert image.size==(16,16)and all(v[3]==255 for v in image.get_flattened_data())
            pixel=SHA(image.tobytes());name='cell-'+pixel[:16]+'.png';path=folder/name
            if name not in assets:
                image.save(path);assets[name]=dict(asset=path.relative_to(mod).as_posix(),assetFileHash=SHA(path.read_bytes()),assetPixelHash=pixel,native_size=[16,16],native_scale=1,recipes=[])
            if recipe not in assets[name]['recipes']:assets[name]['recipes'].append(recipe)
            art=assets[name];new=copy.deepcopy(old)
            for key in('parts','donor','base','animated','animation','frames','assetFrames','foreground','occludes','artOverlay','flora'):new.pop(key,None)
            new.update(kind='third_party',asset=art['asset'],assetFileHash=art['assetFileHash'],assetPixelHash=pixel,compositionPixelHash=pixel,
                credit='Pokemon CrystalDust / Sierraffinity and DoMoreAwesome Games; retained native Gen3 rug/chair artwork where noted.',sourceUrl='https://github.com/Sierraffinity/CrystalDust',
                role='goldenrod_native_'+recipe['family'],evidence='Complete native CrystalDust room fixtures and matching native backing at1:1. Every selected native module is whole; no rescale, color mask, partial table/front/side cut, actor relocation or source collision/warp/script change. Original Gym maze blocker cells, FlowerShop displays/table footprint, and BikeShop tool-wall positions are unchanged. Other room objects remain intact.')
            if old['map']=='GOLDENROD_BIKE_SHOP':new['x'],new['y']=old['sourceCells'][0]
            assert SHA(preview.replacement_image(cache,new,packed,mod).tobytes())==pixel
            fixed.append(canonical(new));allfixed.append(canonical(new));supers.append(dict(module=module,index=index,original_row=old,candidate_row=new))
            for xy in old['sourceCells']:scope.append(dict(game=old['game'],map=old['map'],xy=xy,id=old['id'],quadrant=old['quadrant'],sourceHash=old['sourceHash'],sourceCollision=old['sourceCollision'],sourceFiles=old['sourceFiles'],sourcePalettes=old['sourcePalettes'],sourcePriority=old['sourcePriority'],world_bounds=[xy[0]*16,xy[1]*16,xy[0]*16+16,xy[1]*16+16],old_RGBA_sha256=SHA(preview.replacement_image(cache,old,packed,base).tobytes()),new_RGBA_sha256=pixel,recipe=recipe))
        assert fixed
        keys=[(r['game'],r['map'],r['id'],r['quadrant'])for r in fixed]
        assert len(keys)==len(set(keys)), 'Ambiguous Goldenrod source supersession key'
        raw=(base/module).read_bytes();assert MARKER.encode()not in raw;tail=re.search(br'\r?\nreturn rows\s*$',raw);assert tail
        compact=review.write_compact(fixed,None)[0]
        # Existing positioned rows are superseded in place; ordinary rows retain their exact source scope.
        footer='\n-- BEGIN '+MARKER+'\ndo\nlocal fixes=(function()\n'+compact+'\nend)()\nlocal function key(r)return r.game..":"..r.map..":"..r.id..":"..r.quadrant end\nlocal lookup={}\nfor _,r in ipairs(fixes)do assert(not lookup[key(r)],"Duplicate Goldenrod source supersession key");lookup[key(r)]=r end\nlocal n=0\nfor i,r in ipairs(rows)do if r.map and lookup[key(r)]then rows[i]=lookup[key(r)];n=n+1 end end\nassert(n=='+str(len(fixed))+',"Goldenrod native interior source scope changed")\nend\n-- END '+MARKER+'\nreturn rows\n'
        text=footer.encode('utf8');text=text.replace(b'\n',b'\r\n')if b'\r\n'in raw else text;(mod/module).write_bytes(raw[:tail.start()]+text)
    from types import SimpleNamespace
    validation=review.validate_batch(allfixed,SimpleNamespace(cache=cache,engine=W/'.work/tileshift-engine-0420'),mod);assert validation['rows_accepted']==len(allfixed)and validation['rejected']==0
    provenance=dict(origin='Whole native CrystalDust Goldenrod fixtures and native room backing, with existing complete Gen3 entrance rug/chair foreground retained.',
        rom_sha256=ROM,source_maps=MAPS,credit='Pokemon CrystalDust / Sierraffinity and DoMoreAwesome Games',sourceUrl='https://github.com/Sierraffinity/CrystalDust',native_scale=1,
        processing='Whole16x16 native planes or full FLAT modules only; compose all opaque native foreground pixels over the selected whole native floor. No resizing, drawing, clipping or color-key masks. Complete32x32 table uses541/543/549/551, tall display uses656/617, potted plant560/568 and Gym pedestal700/701. Bike tool-wall uses full two-row native modules; existing shelf, bikes and public counter are untouched.',
        native_modules=native_receipts,source_modules=assets)
    (folder/'provenance.json').write_text(json.dumps(canonical(provenance),indent=2)+'\n',encoding='utf8')
    (out/'supersessions.json').write_text(json.dumps(canonical(supers),indent=2)+'\n',encoding='utf8')
    proof=dict(status='passed',changed_rows=len(allfixed),physical_source_cells=len(scope),changed_maps=list(MAPS),native_pixel_scale=1,all_selected_native_foreground_pixels_and_frames_retained=True,
        source_collision_priorities_palettes_hashes_NPCs_warps_scripts_unchanged=True,no_main_runtime_or_library_changes=True,no_artwork_outside_native_source_map_bounds=True,native_validation=validation,
        selected_source_cells=scope,assets=assets,native_modules=native_receipts)
    (out/'proof.json').write_text(json.dumps(canonical(proof),indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in proof.items()if k not in('selected_source_cells','assets','native_modules')}))

if __name__=='__main__':main()
