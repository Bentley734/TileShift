"""Author reviewed complete native counters for G/S/C public rooms.

The first nine gates share Route31's exact collision footprint. Additional
reviewed room plans are explicit native-cell recipes, never guessed at runtime.
All source objects, collision, scripts, source art guards and warps are retained.
"""
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace
from collections import defaultdict
import argparse,copy,hashlib,json,os,re,sys

W=next(p for p in Path(__file__).resolve().parents if(p/'.tools/python').is_dir()and(p/'.work').is_dir())
sys.path.insert(0,str(W/'.tools/python'))
from PIL import Image
from route31_gate_counters import HASHES,LAYOUT
HASHES={**HASHES,661:'2524081891f5cf4b894680c5dfc256288f5492a5b8650658993bda361d508b5e'}
STANDARD_MAPS=('ROUTE_38_ECRUTEAK_GATE','ROUTE_17_ROUTE_18_GATE','ROUTE_32_RUINS_OF_ALPH_GATE',
    'ROUTE_8_SAFFRON_GATE','ROUTE_7_SAFFRON_GATE','ILEX_FOREST_AZALEA_GATE',
    'ROUTE_42_ECRUTEAK_GATE','ROUTE_16_GATE','ROUTE_15_FUCHSIA_GATE')
GAMES=('gold','silver','crystal')
REPLACE_MODULES={'mappings/johto_gate_finish.lua','mappings/johto_shared_finish.lua',
    'mappings/gen2_kanto_special_rooms_finish.lua','mappings/gen2_kanto_facilities_finish.lua'}
OVERRIDES='mappings/gen2_native_public_counters.lua'
MARKER='-- BEGIN REVIEWED GEN2 WHOLE NATIVE PUBLIC COUNTERS'
sha=lambda b:hashlib.sha256(b).hexdigest()

def canonical(value):
    if isinstance(value,dict):return{k:canonical(v)for k,v in sorted(value.items())}
    if isinstance(value,list):return[canonical(v)for v in value]
    return value

def row_key(r):return':'.join(str(r.get(k,-1))for k in('game','map','id','quadrant','x','y'))

def artwork_key(row):
    return json.dumps({k:row[k]for k in('kind','donor','base','parts','asset','assetFileHash','assetPixelHash','role')if k in row},sort_keys=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--mod-root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--engine',type=Path,default=W/'.work/tileshift-engine-0420')
    a=p.parse_args();base=a.baseline.resolve();mod=a.mod_root.resolve();out=a.output.resolve()
    assert base!=mod and out not in(base,mod)
    assert json.loads((base/'manifest.json').read_text())['version']=='0.46.6'
    sys.path.insert(0,str(mod/'tools'))
    import preview,gen2_extended_review as review
    from newbark_building_review import lua
    from lupa.luajit21 import LuaRuntime
    cache=Path(os.environ['APPDATA'])/'pokemon-love2d';out.mkdir(parents=True,exist_ok=True)
    paths=list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(base/'main.lua').read_text())))
    old_modules={path:preview.read_reviewed(base/path)for path in paths}
    old_all=[(path,index,r)for path,rows in old_modules.items()for index,r in enumerate(rows)]
    monitor_template=next(r for path,index,r in old_all if r.get('asset')=='assets/third_party/johto-hacks/interiors/firegold-lab-computer.png')
    monitor=Image.open(mod/monitor_template['asset']).convert('RGBA')
    assert monitor.size==(16,16)and sha((mod/monitor_template['asset']).read_bytes())==monitor_template['assetFileHash']
    selected=defaultdict(dict);positioned=defaultdict(dict);globals_=defaultdict(dict)
    for path,index,r in sorted(old_all,key=lambda item:bool(item[2].get('map'))):
        if r['game']not in GAMES or r['style']!='gen3':continue
        key=r['game'],r.get('map');art=(path,index,r);tile=r['id'],r['quadrant']
        if 'x'in r:positioned[key][(*tile,r['x'],r['y'])]=art
        elif r.get('map'):selected[key][tile]=art
        else:globals_[r['game'],r['tileset']][tile]=art
    def active(game,name,md,x,y):
        bid=md['blocks'][y//2*md['width']+x//2];q=y%2*2+x%2
        return positioned[game,name].get((bid,q,x,y),selected[game,name].get((bid,q),globals_[game,md['tileset']].get((bid,q))))
    packed={};data={g:review.source(cache,g)for g in GAMES}
    plans={g:{name:{f'{x},{y}':dict(mid=mid,computer=(x,y)==(7,2))for(x,y),mid in LAYOUT.items()}for name in STANDARD_MAPS}for g in GAMES}
    extra=mod/'tools/gen2_public_counter_plans.json'
    if extra.exists():
        additional=json.loads(extra.read_text())
        assert additional['source_version']=='0.46.6'and additional['scale']==1
        for game,maps in additional['plans'].items():
            for name,cells in maps.items():assert name not in plans[game];plans[game][name]=cells
    groups=defaultdict(list);changes=[];receipts=[];native_images={};approved_cells=defaultdict(set)
    def source_guard(game,name,md,x,y,old):
        bid=md['blocks'][y//2*md['width']+x//2];q=y%2*2+x%2
        assert(old['id'],old['quadrant'],old['tileset'])==(bid,q,md['tileset'])
        c=review.cell_info(cache,game,data[game],md['tileset'],bid,q)
        assert c['sourceHash']==old['sourceHash']and c['collision']==old['sourceCollision']
        assert all(old['sourceFiles'][k]==v for k,v in data[game]['fingerprints'][md['tileset']].items())
        assert[bool(v.get('priority'))for v in c['attributes']]==old['sourcePriority']
        assert[v.get('palette',1)for v in c['attributes']]==old['sourcePalettes']
        return c
    def clean(old):
        row=copy.deepcopy(old)
        for field in('donor','base','parts','asset','assetFileHash','assetPixelHash','credit','sourceUrl',
            'nativeContext','animated','animation','assetFrames','frames','artOverlay','sourceColors',
            'nativeSizeOriginalAsset','foreground','occludes','canopy'):
            row.pop(field,None)
        return row
    for game in GAMES:
      for name,cells in plans[game].items():
        md=data[game]['maps'][name]
        receipts.append(dict(game=game,map=name,definition_sha256=sha(json.dumps(canonical(md),separators=(',',':')).encode()),
            objects=md.get('objects',[]),warps=md.get('warps',[]),bg_events=md.get('bgEvents',[])))
        actual_counter=set()
        for y in range(md['height']*2):
            for x in range(md['width']*2):
                bid=md['blocks'][y//2*md['width']+x//2];q=y%2*2+x%2
                if review.cell_info(cache,game,data[game],md['tileset'],bid,q)['collision']==144:actual_counter.add((x,y))
        if name in STANDARD_MAPS:
            assert(md['width']*2,md['height']*2)==(10,8)and actual_counter==set(LAYOUT)
        for coord,recipe in cells.items():
            x,y=map(int,coord.split(','));assert(x,y)in actual_counter
            path,index,old=active(game,name,md,x,y);c=source_guard(game,name,md,x,y,old)
            if 'sourceRole'in recipe:
                assert(old['role'],old['sourceHash'],c['tiles'])==(recipe['sourceRole'],recipe['sourceHash'],recipe['sourceTiles'])
            mid=recipe['mid'];assert mid in HASHES
            donor=dict(game='firered',tileset='house',id=mid,hash=HASHES[mid])
            native=native_images.setdefault(mid,preview.native_donor(cache,donor,packed));assert native.getchannel('A').getextrema()==(255,255)
            row=clean(old);row.update(kind='native',donor=donor,role='gen2_public_complete_native_counter_'+str(mid),
                evidence='Reviewed original COLL_COUNTER footprint: complete native FireRed/CrystalDust cream counter module at1:1, including full top rim, side returns, front body and base. Replace the former floor-carpet stand-in while preserving original blocked cells, counter talk-through, NPCs, scripts, layout, source art identities, palettes, priorities and warps. No rescaling, loose front overlay, decorative overhang or collision edit.')
            expected=native
            if recipe.get('native_back_cap'):
                assert mid==653
                edge=dict(game='firered',tileset='house',id=677,hash=HASHES[677])
                source=preview.native_donor(cache,edge,packed)
                parts=[dict(donor=edge,srcX=0,srcY=8,x=0,y=0,w=16,h=1),
                    dict(donor=edge,srcX=1,srcY=7,x=1,y=1,w=14,h=1)]
                expected=native.copy()
                for part in parts:
                    expected.paste(source.crop((part['srcX'],part['srcY'],part['srcX']+part['w'],part['srcY']+part['h'])),(part['x'],part['y']))
                assert expected.crop((0,2,16,16)).tobytes()==native.crop((0,2,16,16)).tobytes()
                row.pop('donor');row.update(kind='native_composite',base=donor,parts=parts,
                    role='gen2_public_complete_native_counter_post_with_closed_back_rim',
                    evidence='Free-standing Underground counter: complete native FireRed653 counter shaft retains its entire body and both native side borders. Close only its upper two rows using the exact native677 grey outer and white inner structural molding strips at1:1. The existing side-border corners remain intact; every pixel below row2 is unchanged native653. No unique feature, monitor, counter-front body or source event is clipped or scaled. Original COLL_COUNTER cells, layout, NPCs, interactions, source guards and warps are preserved.')
            if recipe.get('preserve_device_parts'):
                assert old.get('parts')and not recipe.get('computer')
                row.pop('donor');row.update(kind='native_composite',base=donor,parts=copy.deepcopy(old['parts']),
                    role='gen2_public_complete_native_counter_retaining_full_existing_device')
                expected=preview.replacement_image(cache,row,packed,mod)
            if recipe.get('computer'):
                assert old.get('asset')==monitor_template['asset']or recipe.get('replace_standing_counter_pc')or recipe.get('replace_fragmented_register')
                for field in('asset','assetFileHash','assetPixelHash','credit','sourceUrl'):
                    if field in monitor_template:row[field]=copy.deepcopy(monitor_template[field])
                row.pop('donor');row.update(kind='third_party',base=donor,role='gen2_public_native_counter_with_complete_monitor_keyboard')
                fg=monitor;expected=Image.alpha_composite(native,fg)
                assert all(not p[3]or p==v for p,v in zip(fg.get_flattened_data(),expected.get_flattened_data()))
            result=preview.replacement_image(cache,row,packed,mod);assert result.tobytes()==expected.tobytes()
            row['compositionPixelHash']=sha(result.tobytes());groups[path,index].append(((x,y),row));approved_cells[game,name].add((x,y))
            changes.append(dict(game=game,map=name,xy=[x,y],source_module=path,id=row['id'],quadrant=row['quadrant'],
                sourceHash=c['sourceHash'],counter_donor=donor,whole_FLAT_pixels_preserved=not(recipe.get('native_back_cap')or recipe.get('preserve_device_parts')or recipe.get('computer')),
                native_counter_body_preserved=True,closed_native_back_rim=bool(recipe.get('native_back_cap')),
                existing_device_parts_preserved=bool(recipe.get('preserve_device_parts')),
                complete_monitor_keyboard=bool(recipe.get('computer')),composition_RGBA_sha256=sha(result.tobytes())))
    updates=defaultdict(dict);overrides=[];new_rows=[]
    for(path,index),items in groups.items():
        old=old_modules[path][index];coords={xy for xy,row in items}
        source_coords={tuple(xy)for xy in old.get('sourceCells',[])}
        if path in REPLACE_MODULES and coords==source_coords and len({artwork_key(row)for xy,row in items})==1:
            row=items[0][1];row['sourceCells']=copy.deepcopy(old['sourceCells'])
            updates[path][row_key(old)]=row;new_rows.append(row)
        else:
            for(x,y),row in items:
                row.update(x=x,y=y,sourceCells=[[x,y]]);overrides.append(row);new_rows.append(row)
    module_hashes={}
    for path,replacements in updates.items():
        original=(base/path).read_bytes();nl=b'\r\n'if b'\r\n'in original else b'\n'
        assert MARKER.encode()not in original and original.endswith(b'return rows'+nl)
        footer=(MARKER+'\nlocal replacements='+lua(canonical(replacements))+'\nlocal changed=0\n'
            'for index,row in ipairs(rows)do\n'
            "  local key=table.concat({row.game,row.map or -1,row.id,row.quadrant,row.x or -1,row.y or -1},':')\n"
            "  local replacement=row.style=='gen3'and replacements[key]\n"
            '  if replacement then rows[index]=replacement;changed=changed+1 end\nend\n'
            f"assert(changed=={len(replacements)},'Reviewed public counter source set changed')\n"
            '-- END REVIEWED GEN2 WHOLE NATIVE PUBLIC COUNTERS\nreturn rows\n')
        (mod/path).write_bytes(original[:-len(b'return rows'+nl)]+footer.replace('\n',nl.decode()).encode())
        after=preview.read_reviewed(mod/path);assert len(after)==len(old_modules[path])
        for old,row in zip(old_modules[path],after):assert row==replacements.get(row_key(old),old)
        module_hashes[path]=sha((mod/path).read_bytes())
    main=(base/'main.lua').read_bytes()
    if overrides:
        (mod/OVERRIDES).write_text('return '+lua(canonical(overrides))+'\n');module_hashes[OVERRIDES]=sha((mod/OVERRIDES).read_bytes())
        anchor=b"    'mappings/gen2_domestic_floor_audit.lua'"
        assert main.count(anchor)==1
        main=main.replace(anchor,("    '"+OVERRIDES+"',\r\n").encode()+anchor)
    (mod/'main.lua').write_bytes(main)
    paths=list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(mod/'main.lua').read_text())))
    runtime=LuaRuntime(unpack_returned_tuples=True);runtime.globals().paths=runtime.table_from(paths)
    runtime.globals().source=lambda name:(mod/name).read_text(encoding='utf-8-sig')
    total=runtime.execute('''local rows={}
      for _,path in ipairs(paths)do for _,r in ipairs(assert(load(source(path),'@'..path))())do rows[#rows+1]=r end end
      local M=assert(load(source('lib/mapping.lua'),'@lib/mapping.lua'))();local _,errors=M.index(rows)
      assert(#errors==0,table.concat(errors,'\\n'));return #rows''')
    valid=review.validate_batch(new_rows,SimpleNamespace(cache=cache,engine=a.engine,output=out),mod)
    assert valid['rows_accepted']==len(new_rows)and valid['rejected']==0
    report=dict(status='passed',source_receipts=receipts,changes=changes,changed_cells=len(changes),changed_rows=len(new_rows),
        existing_rows_replaced=sum(len(v)for v in updates.values()),positioned_rows=len(overrides),
        approved_cells={g+':'+m:sorted([list(xy)for xy in cells])for(g,m),cells in approved_cells.items()},
        registered_rows=total,index_errors=0,native_validation=valid,all_other_existing_rows_identical=True,
        no_new_art_or_runtime_API=True,module_sha256=module_hashes,helper_sha256=sha(Path(__file__).read_bytes()),
        reviewed_plans_sha256=sha(extra.read_bytes())if extra.exists()else None,
        complete_native_back_cap_body_bounds=[0,2,16,16],all_source_collisions_are_counter144=True)
    (out/'proof.json').write_text(json.dumps(canonical(report),indent=2)+'\n')
    allrows=[]
    for path in paths:allrows.extend(preview.read_reviewed(mod/path))
    for name in sorted({name for maps in plans.values()for name in maps}):
        game=next(g for g in('crystal','gold','silver')if name in plans[g])
        stem=name if game=='crystal'else game+'-'+name
        preview.map_preview(cache,out,game,name,stem,allrows,packed,2,mod)
    print(json.dumps(dict(status='passed',changed_rows=len(new_rows),changed_cells=len(changes),registered_rows=total,index_errors=0,native_validation=valid)))

if __name__=='__main__':main()
