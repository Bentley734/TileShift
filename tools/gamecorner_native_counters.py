"""Reproduce complete CrystalDust Goldenrod counter surfaces/fronts/cases."""
from pathlib import Path
from collections import defaultdict
import argparse,copy,hashlib,json,os,re,sys
W=next(p for p in Path(__file__).resolve().parents if(p/'.tools/python').is_dir())
sys.path.insert(0,str(W/'.tools/python'))
from PIL import Image
MARKER='COMPLETE NATIVE CRYSTALDUST GOLDENROD COUNTERS'
MODULE='mappings/johto_gamecorner_finish.lua';PAIR='083df884_083dfb84'
ROM='51196cba923c315d0088b747b5cdee704f2ac057cd493f9ddf226fb7227302cf'
sha=lambda b:hashlib.sha256(b).hexdigest()
def canonical(v):
    if isinstance(v,dict):return{k:canonical(x)for k,x in sorted(v.items())}
    if isinstance(v,list):return[canonical(x)for x in v]
    return v
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,required=True);p.add_argument('--catalog-dir',type=Path,required=True)
    p.add_argument('--mod-root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();base,cat,mod,out=[v.resolve()for v in(a.baseline,a.catalog_dir,a.mod_root,a.output)]
    assert base!=mod and json.loads((base/'manifest.json').read_text())['version']=='0.46.15'
    out.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(mod/'tools'))
    import preview,gen2_extended_review as review
    from types import SimpleNamespace
    cache=Path(os.environ['APPDATA'])/'pokemon-love2d';packed={}
    catalog=json.loads((cat/'catalog.json').read_text());assert catalog['rom_sha256']==ROM
    native_map=next(m for m in catalog['maps']if m['id']=='g10_m003');assert native_map['pair']==PAIR
    paths=list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(base/'main.lua').read_text())))
    records=[]
    for path in paths:
        for i,r in enumerate(preview.read_reviewed(base/path)):
            if r['game']in('gold','silver','crystal')and r['style']=='gen3'and r.get('map')=='GOLDENROD_GAME_CORNER':records.append(dict(module=path,index=i,row=r))
    planes={};native_proof={}
    def native(mid,plane='flat'):
        path=cat/'pairs'/PAIR/(plane+'.png')
        if plane not in planes:planes[plane]=Image.open(path).convert('RGBA')
        x,y=mid%16*16,mid//16*16;im=planes[plane].crop((x,y,x+16,y+16))
        native_proof[f'{plane}:{mid}']=dict(pair=PAIR,plane=plane,mid=mid,source_rect=[x,y,16,16],atlas_sha256=sha(path.read_bytes()),RGBA_sha256=sha(im.tobytes()))
        return im
    specs={(7,1):(519,'top'),(14,1):(519,'top')}
    for x,mid in enumerate((580,583,564,565,659,664,537,527)):specs[x,2]=(mid,'top')
    for x,mid,plane in((14,535,'top'),(15,537,'over'),(16,603,'over'),(17,660,'over'),(18,537,'over'),(19,660,'over')):specs[x,2]=(mid,plane)
    for x,mid in enumerate((545,546,572,573,574,544,545,547)):specs[x,3]=(mid,'flat')
    for x,mid in enumerate((539,545,548,545,545,545),14):specs[x,3]=(mid,'flat')
    assert len(specs)==30
    floor_colors=set(native(529).get_flattened_data());folder=mod/'assets/third_party/johto-hacks/crystaldust-gamecorner-counters';folder.mkdir(parents=True,exist_ok=True)
    assets={};rows=[];scope=[];backings={};scenes=[];extra=[];supers=[]
    glass=Image.new('RGBA',(48,32));glass_pieces={}
    for gy,line in enumerate(((564,565,659),(572,573,574))):
        for gx,mid in enumerate(line):
            im=native(mid,'top');glass.paste(im,(gx*16,gy*16))
    assert glass.getbbox()==(0,12,48,32)
    glass.save(out/'glass-native48x32-envelope.png');glass.crop(glass.getbbox()).save(out/'glass-native48x20.png')
    for game in('gold','silver','crystal'):
        data=review.source(cache,game);md=data['maps']['GOLDENROD_GAME_CORNER'];generic={};positioned={}
        for z in records:
            r=z['row']
            if r['game']!=game:continue
            if'x'in r:positioned[r['id'],r['quadrant'],r['x'],r['y']]=z
            else:generic[r['id'],r['quadrant']]=z
        def active(x,y):
            bid=md['blocks'][y//2*md['width']+x//2];q=y%2*2+x%2
            return positioned.get((bid,q,x,y),generic.get((bid,q)))
        floor=copy.deepcopy(active(8,2)['row'])
        assert floor['sourceCollision']==0 and floor.get('donor')==dict(game='firered',id=657,tileset='building__rom_082d4cec',hash='c469420b11c0d16a2e52eb27b3cf349520e628d0163a5f99851f40db4e0599f5')
        floor_image=preview.replacement_image(cache,floor,packed,base);backings[game]=dict(row=floor,RGBA_sha256=sha(floor_image.tobytes()))
        before=Image.new('RGBA',(md['width']*32,md['height']*32));after=before.copy()
        for y in range(md['height']*2):
            for x in range(md['width']*2):
                z=active(x,y);assert z;old=z['row'];old_image=preview.replacement_image(cache,old,packed,base);image=old_image
                if(x,y)in specs:
                    mid,plane=specs[x,y];ink=native(mid,plane);exterior=[]
                    if mid in(539,547):
                        for yy in range(16):
                            for xx in range(16):
                                if ink.getpixel((xx,yy))in floor_colors:exterior.append([xx,yy]);ink.putpixel((xx,yy),(0,0,0,0))
                    backing=old_image if old['sourceCollision']==0 else floor_image
                    image=Image.alpha_composite(backing,ink)
                    digest=sha(image.tobytes());filename='counter-'+digest[:16]+'.png';path=folder/filename
                    recipe=dict(native_plane=[PAIR,plane,mid],exterior_floor_mask=exterior,
                                floor_row=old if old['sourceCollision']==0 else floor,
                                whole_native_hardware_pixels_preserved=sum(v[3]>0 for v in ink.get_flattened_data()))
                    if filename not in assets:image.save(path);assets[filename]=dict(asset=path.relative_to(mod).as_posix(),assetFileHash=sha(path.read_bytes()),assetPixelHash=digest,recipes=[])
                    if recipe not in assets[filename]['recipes']:assets[filename]['recipes'].append(recipe)
                    row=copy.deepcopy(old)
                    for field in('kind','donor','base','parts','asset','assetFileHash','assetPixelHash','sourceColors','foreground','occludes','overMask','artOverlay','animated','animation','frames','assetFrames','flora'):row.pop(field,None)
                    row.update(game=game,map='GOLDENROD_GAME_CORNER',x=x,y=y,sourceCells=[[x,y]],kind='third_party',
                        asset=assets[filename]['asset'],assetFileHash=assets[filename]['assetFileHash'],assetPixelHash=digest,compositionPixelHash=digest,
                        credit='CrystalDust / Sierraffinity and DoMoreAwesome Games; original matching native floor retained.',sourceUrl='https://github.com/Sierraffinity/CrystalDust',
                        role='crystaldust_gamecorner_complete_counter',status='reviewed',
                        evidence='Whole native counter TOP/OVER surfaces plus complete BOTTOM/FLAT front/body/corner modules. The48x20glass showcase includes its full lid/frame/front/feet; service register uses complete native upper/lower pad. Only exterior native floor triangles are transparent over the existing matching room floor. Original cashier positions, counters, player approaches, collision, BG events, machines and scripts remain unchanged.')
                    live=review.cell_info(cache,game,data,md['tileset'],row['id'],row['quadrant'])
                    assert live['sourceHash']==row['sourceHash']and live['collision']==row['sourceCollision']
                    assert[bool(v.get('priority'))for v in live['attributes']]==row['sourcePriority']
                    assert[v.get('palette',1)for v in live['attributes']]==row['sourcePalettes']
                    assert sha(preview.replacement_image(cache,row,packed,mod).tobytes())==digest
                    rows.append(canonical(row))
                    if'x'in old:
                        assert z['module']=='mappings/gen2_native_public_counters.lua'
                        supers.append(dict(module=z['module'],index=z['index'],original_row=old,candidate_row=canonical(row)))
                    else:extra.append(canonical(row))
                    scope.append(dict(game=game,map=row['map'],xy=[x,y],id=row['id'],quadrant=row['quadrant'],sourceHash=row['sourceHash'],sourceCollision=row['sourceCollision'],sourcePriority=row['sourcePriority'],sourcePalettes=row['sourcePalettes'],sourceFiles=row['sourceFiles'],old_row=old,old_module=z['module'],old_index=z['index'],old_RGBA_sha256=sha(old_image.tobytes()),new_RGBA_sha256=digest,recipe=recipe))
                before.paste(old_image,(x*16,y*16));after.paste(image,(x*16,y*16))
        before.save(out/(game+'-before.png'));after.save(out/(game+'-after.png'));scenes.append(dict(game=game,path=str(out/(game+'-after.png')),RGBA_sha256=sha(after.tobytes())))
    assert len(rows)==len(scope)==90 and len(extra)==62 and len(supers)==28
    raw=(base/MODULE).read_bytes();assert MARKER.encode()not in raw
    tail=re.search(br'\r?\nreturn rows\s*$',raw);assert tail
    compact=review.write_compact(extra,None)[0]
    footer='\n-- BEGIN '+MARKER+'\ndo\nlocal extra=(function()\n'+compact+'\nend)()\nlocal function key(r)return r.game..":"..(r.map or"*")..":"..r.id..":"..r.quadrant..":"..tostring(r.x)..":"..tostring(r.y)end\nlocal seen={}\nfor _,r in ipairs(rows)do seen[key(r)]=true end\nfor _,r in ipairs(extra)do assert(not seen[key(r)],"Duplicate Game Corner counter position");rows[#rows+1]=r;seen[key(r)]=true end\nend\n-- END '+MARKER+'\nreturn rows\n'
    footer=footer.encode();footer=footer.replace(b'\n',b'\r\n')if b'\r\n'in raw else footer
    (mod/MODULE).write_bytes(raw[:tail.start()]+footer)
    replacement_module='mappings/gen2_native_public_counters.lua'
    raw=(base/replacement_module).read_bytes();tail=re.search(br'\r?\nreturn rows\s*$',raw)
    if tail:replacement_prefix=raw[:tail.start()]
    else:
        assert re.match(br'\s*return\s*\{',raw)
        eol=b'\r\n'if b'\r\n'in raw else b'\n'
        replacement_prefix=b'local rows=(function()'+eol+raw+eol+b'end)()'+eol
    compact=review.write_compact([v['candidate_row']for v in supers],None)[0]
    footer='\n-- BEGIN '+MARKER+'\ndo\nlocal fixes=(function()\n'+compact+'\nend)()\nlocal function key(r)return r.game..":"..(r.map or"*")..":"..r.id..":"..r.quadrant..":"..tostring(r.x)..":"..tostring(r.y)end\nlocal lookup={}\nfor _,r in ipairs(fixes)do assert(not lookup[key(r)]);lookup[key(r)]=r end\nlocal n=0\nfor i,r in ipairs(rows)do if lookup[key(r)]then rows[i]=lookup[key(r)];lookup[key(r)]=nil;n=n+1 end end\nassert(n==28 and next(lookup)==nil,"Game Corner exact counter supersession changed")\nend\n-- END '+MARKER+'\nreturn rows\n'
    footer=footer.encode();footer=footer.replace(b'\n',b'\r\n')if b'\r\n'in raw else footer
    (mod/replacement_module).write_bytes(replacement_prefix+footer)
    validation=review.validate_batch(rows,SimpleNamespace(cache=cache,engine=W/'.work/tileshift-engine-0420'),mod)
    assert validation['rows_accepted']==90 and validation['rejected']==0
    provenance=dict(origin='Complete native CrystalDust GameCorner counters, surfaces, curved bodies and glass showcase',rom_sha256=ROM,native_map='g10_m003',pair=PAIR,native_scale=1,
        native_modules=native_proof,source_modules=assets,room_floor_backings=backings,
        full_glass_showcase=dict(source_native_planes=[['top',564],['top',565],['top',659],['top',572],['top',573],['top',574]],native_full_bounds=[32,44,80,64],dimensions=[48,20],source_destination_bounds=[32,44,80,64],envelope_dimensions=[48,32],envelope_RGBA_sha256=sha(glass.tobytes()),whole_RGBA_sha256=sha(glass.crop(glass.getbbox()).tobytes()),opaque_pixels=sum(v[3]>0 for v in glass.get_flattened_data())),
        processing='Whole16px native planes only. Existing floor is retained behind transparent native components; only explicit exterior native gold floor pixels of corner539/547 are omitted. No body, surface, front, frame or hardware pixels are clipped or recolored. Other room fixtures and source mechanics unchanged.')
    (folder/'provenance.json').write_text(json.dumps(canonical(provenance),indent=2)+'\n')
    (out/'supersessions.json').write_text(json.dumps(canonical(supers),indent=2)+'\n')
    result=dict(status='passed',added_positioned_rows=62,replaced_existing_positioned_rows=28,physical_source_cells=90,added_foreground_catalog_rows=0,complete_glass_world_bounds=[32,44,80,64],all_regular_rows_retained=True,
        selected_source_cells=scope,source_guard_fields_unchanged=True,native_validation=validation,assets=assets,native_modules=native_proof,scenes=scenes)
    (out/'proof.json').write_text(json.dumps(canonical(result),indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k not in('selected_source_cells','assets','native_modules','scenes')},indent=2))
if __name__=='__main__':main()
