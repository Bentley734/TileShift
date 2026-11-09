"""Fit whole native CrystalDust clinic counters to unchanged classic room layouts."""
from pathlib import Path
from collections import Counter
from types import SimpleNamespace
import argparse,copy,hashlib,json,re,sys
W=next(p for p in Path(__file__).resolve().parents if(p/'.tools/python').is_dir())
sys.path.insert(0,str(W/'.tools/python'))
from PIL import Image
GAMES=('red','blue','yellow','gold','silver','crystal')
MODULE='mappings/gen2_crystaldust_center_counters.lua'
INDIGO='mappings/gen1_commercial_finish.lua'
ASSETS='assets/third_party/johto-hacks/pokecenter-native-counters'
MARKER='NATIVE CRYSTALDUST COMPLETE CLINIC COUNTERS'
ROM='51196cba923c315d0088b747b5cdee704f2ac057cd493f9ddf226fb7227302cf'
PAIR='083df884_083df8b4'
sha=lambda b:hashlib.sha256(b).hexdigest()
pixel=lambda im:sha(im.convert('RGBA').tobytes())

def clinic(name):return 'POKECENTER'in name or 'POKECOM_CENTER'in name or name=='INDIGO_PLATEAU_LOBBY'
def held(name):return 'BETA'in name or 'ADMIN_OFFICE'in name
def canonical(v):
    if isinstance(v,dict):return{k:canonical(x)for k,x in sorted(v.items())}
    if isinstance(v,list):return[canonical(x)for x in v]
    return v
def key(r):return(r['game'],r['map'],r['tileset'],r['id'],r['quadrant'],r.get('x'),r.get('y'))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--mod-root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--native-root',type=Path,default=W/'.work/tileshift-firegold/crystaldust')
    p.add_argument('--output',type=Path,required=True);p.add_argument('--engine',type=Path,default=W/'.work/tileshift-engine-0420');a=p.parse_args()
    base,mod,native,out=[v.resolve()for v in(a.baseline,a.mod_root,a.native_root,a.output)];assert base!=mod
    assert json.loads((base/'manifest.json').read_text())['version']=='0.46.11';out.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(mod/'tools'));import preview,gen2_extended_review as g2,gen1_family_review as g1
    from center_mart_overhang_review import write_rows
    cache=Path('C:/Users/LSDMTHC/AppData/Roaming/pokemon-love2d');paths=list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(base/'main.lua').read_text())))
    rows=[];source_modules={}
    for path in paths:
        raw=(base/path).read_bytes()
        if not any(word in raw for word in(b'POKECENTER',b'POKECOM_CENTER',b'INDIGO_PLATEAU_LOBBY')):continue
        part=[dict(r,source_module=path)for r in preview.read_reviewed(base/path)if r.get('game')in GAMES and clinic(r.get('map',''))]
        if part:rows.extend(part);source_modules[path]=sha(raw)
    index={key(r):r for r in rows}
    catalog=json.loads((native/'catalog.json').read_text());assert catalog['rom_sha256']==ROM
    nm=next(m for m in catalog['maps']if m['id']=='g03_m001');assert nm['pair']==PAIR
    pair=native/'pairs'/PAIR;bottom=Image.open(pair/'bottom.png').convert('RGBA');top=Image.open(pair/'top.png').convert('RGBA')
    images={};origins={}
    for name,mid,plane in [('plain',572,'top'),('service',536,'top'),('left',569,'bottom'),('right',573,'bottom'),('right-flower',573,'flat'),('back-cap',557,'top'),('upright-flower',565,'flat')]:
        box=(mid%16*16,mid//16*16,mid%16*16+16,mid//16*16+16);b,t=bottom.crop(box),top.crop(box)
        im={'bottom':b,'top':t,'flat':Image.alpha_composite(b,t)}[plane];images[name]=im
        origins[name]=dict(native_map=nm['id'],pair=PAIR,native_mid=mid,plane=plane,atlas_xyxy=box,RGBA_sha256=pixel(im),opaque_pixels=sum(p[3]!=0 for p in im.get_flattened_data()),pixel_scale=1)
        assert origins[name]['opaque_pixels']==(128 if name=='back-cap'else 256)
    # The complete empty corners are whole native BOTTOM modules. Their
    # matching TOP differs only by the independent flowerpot foot, not body.
    for mid,name in [(569,'left'),(573,'right')]:
        box=origins[name]['atlas_xyxy'];flat=Image.alpha_composite(bottom.crop(box),top.crop(box));diff=[(x,y)for y in range(16)for x in range(16)if images[name].getpixel((x,y))!=flat.getpixel((x,y))]
        assert len(diff)==52 and all(2<=x<14 and 0<=y<5 for x,y in diff)
    floor_colors=set(bottom.crop((513%16*16,513//16*16,513%16*16+16,513//16*16+16)).get_flattened_data())
    floor_colors|=set(bottom.crop((567%16*16,567//16*16,567%16*16+16,567//16*16+16)).get_flattened_data())
    assert not floor_colors&set(images['right'].get_flattened_data()) and not floor_colors&set(images['left'].get_flattened_data())
    plans=[];checked=[];held_cells=[];rooms={};packed={};datasets={};used=set();source_geometry={}
    evidence='Whole native CrystalDust clinic counter modules retain complete red countertop, gray front and rounded side/body at1:1. Actual source-cell adjacency defines continuous runs; a single native service panel remains below the unchanged Nurse. Full native BOTTOM empty ends omit the entire independent flowerpot, never a cropped pot. Already exact native wall caps/flowers/body and complete upstairs service desks stay unchanged. Source collision, behavior, priority, palettes, scripts, objects, clinic Chansey and warps retain their original imported definitions.'
    for game in GAMES:
        source=g2 if game in GAMES[3:]else g1;data=source.source(cache,game);datasets[game]=data
        for name,md in sorted(data['maps'].items()):
            if not clinic(name):continue
            cells={};objects=md.get('objects',[]);source_geometry[game+':'+name]=sha(json.dumps(md,sort_keys=True,separators=(',',':')).encode())
            for y in range(md['height']*2):
                for x in range(md['width']*2):
                    bid=md['blocks'][y//2*md['width']+x//2];q=y%2*2+x%2;k=(game,name,md['tileset'],bid,q)
                    old=index.get((*k,x,y),index.get((*k,None,None)))
                    if old and old.get('role','').startswith('johto_center_')and 'counter'in old.get('role',''):cells[x,y]=old
            if not cells:continue
            if held(name):
                held_cells.extend(dict(game=game,map=name,xy=[x,y],id=r['id'],quadrant=r['quadrant'],sourceHash=r['sourceHash'])for(x,y),r in cells.items());continue
            front={xy for xy,r in cells.items()if r['role']in('johto_center_nurse_counter','johto_center_counter_left_end','johto_center_counter_right_front')}
            nurses={(o['x'],o['y']+1)for o in objects if o.get('sprite')=='SPRITE_NURSE'}
            if name!='POKECENTER_2F':assert len(nurses)==1 and nurses<=front,(game,name,nurses)
            rooms[game+':'+name]=[list(xy)for xy in cells]
            for(x,y),old in cells.items():
                bid,q=old['id'],old['quadrant'];c=source.cell_info(cache,game,data,md['tileset'],bid,q);assert c['sourceHash']==old['sourceHash']
                if game in GAMES[3:]:assert c['collision']==old['sourceCollision']
                else:assert c['behavior']==old['sourceBehavior']
                role=old['role'];part='plain'
                if role=='johto_center_counter_right_back':part='back-cap'
                elif role=='johto_center_counter_right_flower':part='upright-flower'
                elif(x,y)in nurses:part='service'
                elif(x+1,y)not in front and x+1<md['width']*2:part='right-flower'if cells.get((x,y-1),{}).get('role')=='johto_center_counter_right_flower'else'right'
                elif(x-1,y)not in front and x>0:part='left'
                oldimage=preview.replacement_image(cache,old,packed,base);result=images[part]
                ground=copy.deepcopy(old.get('base'))
                if part=='back-cap':
                    assert len(old['parts'])==1;ground=copy.deepcopy(old['parts'][0]['donor'])
                    result=Image.alpha_composite(preview.native_donor(cache,ground,packed),result)
                    assert result.crop((0,0,16,8)).tobytes()==oldimage.crop((0,0,16,8)).tobytes()
                detail=dict(game=game,map=name,xy=[x,y],id=bid,quadrant=q,sourceHash=old['sourceHash'],source_module=old['source_module'],native_part=part,native_mid=origins[part]['native_mid'],native_plane=origins[part]['plane'],old_RGBA_sha256=pixel(oldimage),new_RGBA_sha256=pixel(result),source_behavior_and_guards_unchanged=True)
                detail['changed']=oldimage.tobytes()!=result.tobytes();checked.append(detail)
                if not detail['changed']:continue
                used.add(part)
                r={k:copy.deepcopy(v)for k,v in old.items()if k.startswith('source')and k not in('sourceUrl','sourceCells','source_module')}
                r.update({k:old[k]for k in('game','style','tileset','id','quadrant')});r.update(map=name,x=x,y=y,sourceCells=[[x,y]],status='reviewed',kind='third_party',role='crystaldust_complete_clinic_counter_'+part,evidence=evidence,credit='Pokemon CrystalDust / Sierraffinity and DoMoreAwesome Games',sourceUrl='https://github.com/Sierraffinity/CrystalDust')
                if ground:r['base']=ground
                r['asset']=ASSETS+'/'+part+'.png';r['assetPixelHash']=pixel(images[part]);r['compositionPixelHash']=pixel(result)
                plans.append((canonical(r),old,detail))
    assert len(rooms)==105 and len(checked)==1037 and len(held_cells)==206
    assert len({(c['game'],c['map'])for c in held_cells})==31
    dest=mod/ASSETS;dest.mkdir(exist_ok=True);assets={}
    for name in sorted(used):
        path=dest/(name+'.png');images[name].save(path);assets[name]=dict(file=path.name,asset=ASSETS+'/'+path.name,assetFileHash=sha(path.read_bytes()),assetPixelHash=pixel(images[name]),**origins[name])
    changes=[];updates=[];extra=[]
    for r,old,detail in plans:
        part=detail['native_part'];r['assetFileHash']=assets[part]['assetFileHash'];assert preview.replacement_image(cache,r,packed,mod).tobytes()==images[part].tobytes()
        if'x'in old:assert old['source_module']==INDIGO;updates.append(r)
        else:extra.append(r)
        changes.append(detail)
    assert len(updates)==33 and all(r['map']=='INDIGO_PLATEAU_LOBBY'for r in updates)
    provenance=dict(origin='Whole native CrystalDust Pokemon Center counter surfaces, service panel and complete empty rounded end/body modules.',credit='Pokemon CrystalDust / Sierraffinity and DoMoreAwesome Games',sourceUrl='https://github.com/Sierraffinity/CrystalDust',rom_sha256=ROM,source_map=nm['id'],pair=PAIR,source_top_sha256=sha((pair/'top.png').read_bytes()),source_bottom_sha256=sha((pair/'bottom.png').read_bytes()),source_modules=assets,retained_byte_identical_native_components={name:origins[name]for name in sorted(set(images)-used)},processing='Complete unscaled16x16 TOP plain/service modules and complete BOTTOM empty end modules. BOTTOM ends already include the entire red surface, gray front and rounded side body; the independent TOP flowerpot is omitted whole for empty counters. Existing equivalent flower/upright/wall-cap rows stay byte-identical. No generated pixel, recolor, resize, cut frame, side or native corner, CD floor patch or source mechanics change.')
    (dest/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    write_rows(mod/MODULE,canonical(extra))
    raw=(base/INDIGO).read_text();assert MARKER not in raw;tail=re.search(r'\nreturn rows\s*$',raw);assert tail
    footer='\n-- BEGIN '+MARKER+'\ndo\nlocal fixed=(function()\n'+g2.write_compact(canonical(updates),None)[0]+'end)()\nlocal lookup={}\nlocal function key(r)return table.concat({r.game,r.map,r.id,r.quadrant,r.x,r.y},"|")end\nfor _,r in ipairs(fixed)do lookup[key(r)]=r end\nlocal n=0\nfor i,r in ipairs(rows)do if r.x~=nil then local v=lookup[key(r)];if v then rows[i]=v;n=n+1 end end end\nassert(n==33,"Indigo clinic counter source scope changed")\nend\n-- END '+MARKER+'\nreturn rows\n'
    (mod/INDIGO).write_text(raw[:tail.start()]+footer)
    path=mod/'main.lua';raw=path.read_bytes();entry=b"    '"+MODULE.encode()+b"',";marker=b"    'mappings/gen2_crystaldust_rocket.lua',"
    if entry not in raw:assert raw.count(marker)==1;raw=raw.replace(marker,marker+b'\r\n'+entry)
    path.write_bytes(raw)
    path=mod/'tests/main_test.lua';raw=path.read_bytes();marker=b"or path=='mappings/gen2_native_public_counters.lua'"
    if MODULE.encode()not in raw:assert raw.count(marker)==1;raw=raw.replace(marker,marker+b" or path=='"+MODULE.encode()+b"'")
    path.write_bytes(raw)
    validation=g2.validate_batch(canonical([r for r,old,d in plans]),SimpleNamespace(cache=cache,engine=a.engine,output=out),mod);assert validation['rejected']==0
    proof=dict(status='passed',checked_counter_cells=len(checked),active_game_map_pairs=len(rooms),actual_changed_counter_cells=len(changes),retained_pixel_identical_cells=len(checked)-len(changes),new_positioned_rows=len(extra),replaced_existing_positioned_rows=len(updates),changed_source_cells=changes,checked_source_cells=checked,held_source_cells=held_cells,held_game_map_pairs=31,approved_cells={name:[c['xy']for c in changes if c['game']+':'+c['map']==name]for name in rooms},source_geometry_sha256=source_geometry,source_mapping_module_sha256=source_modules,native_source_modules=assets,native_validation=validation,all_source_NPCs_Chansey_collision_scripts_warps_priority_palettes_and_behaviors_unchanged=True,only_genuine_pixel_changes_authored=True)
    (out/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    for game,name in [('crystal','AZALEA_POKECENTER_1F'),('red','VIRIDIAN_POKECENTER'),('red','INDIGO_PLATEAU_LOBBY'),('crystal','POKECENTER_2F')]:preview.map_preview(cache,out,game,name,game+'-'+name+'-complete-counter',rows+[r for r,old,d in plans],packed,2,mod)
    print(json.dumps({k:v for k,v in proof.items()if k in('status','checked_counter_cells','active_game_map_pairs','actual_changed_counter_cells','retained_pixel_identical_cells','new_positioned_rows','replaced_existing_positioned_rows','held_game_map_pairs','native_validation')},indent=2))

if __name__=='__main__':main()
