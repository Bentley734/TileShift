"""Match transparent Gen2 bookcase surroundings to the actual native room.

Complete native bookcase artwork and all gameplay/source metadata stay intact.
Only exposed backing changes: native705 walls at the six affected room headers,
and checked same-row native704/723 floors around free-standing traditional-room
shelves. Old player_house40 parts are backing, never bookcase object pixels.
"""
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace
from collections import defaultdict,Counter
import argparse,copy,hashlib,json,os,re,sys

W=next(p for p in Path(__file__).resolve().parents if(p/'.tools/python').is_dir()and(p/'.work').is_dir())
sys.path.insert(0,str(W/'.tools/python'))
from PIL import Image
GAMES=('gold','silver','crystal')
HEAD_MAPS={'ECRUTEAK_ITEMFINDER_HOUSE','ECRUTEAK_LUGIA_SPEECH_HOUSE','KURTS_HOUSE',
    'MAHOGANY_MART_1F','VIOLET_KYLES_HOUSE','VIOLET_NICKNAME_SPEECH_HOUSE'}
LOWER_MAPS={'MAHOGANY_MART_1F','MOUNT_MOON_GIFT_SHOP'}
MARKER='-- BEGIN MATCHED NATIVE BOOKCASE BACKDROPS'
sha=lambda b:hashlib.sha256(b).hexdigest()

def canonical(value):
    if isinstance(value,dict):return{k:canonical(v)for k,v in sorted(value.items())}
    if isinstance(value,list):return[canonical(v)for v in value]
    return value

def ref_key(r):return r.get('game'),r.get('tileset'),r.get('id')
def row_key(r):return':'.join(str(r.get(k,-1))for k in('game','map','id','quadrant','x','y'))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--mod-root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--engine',type=Path,default=W/'.work/tileshift-engine-0420')
    a=p.parse_args();base=a.baseline.resolve();mod=a.mod_root.resolve();out=a.output.resolve()
    assert base!=mod and out not in(base,mod)
    sys.path.insert(0,str(mod/'tools'))
    import preview,catalog,gen2_extended_review as review
    from newbark_building_review import lua
    from lupa.luajit21 import LuaRuntime
    cache=Path(os.environ['APPDATA'])/'pokemon-love2d';out.mkdir(parents=True,exist_ok=True)
    paths=list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(base/'main.lua').read_text())))
    modules={path:preview.read_reviewed(base/path)for path in paths}
    allrows=[(path,index,r)for path,rows in modules.items()for index,r in enumerate(rows)]
    global_=defaultdict(dict);scoped=defaultdict(dict);pos=defaultdict(dict)
    for path,index,r in sorted(allrows,key=lambda item:bool(item[2].get('map'))):
        if r['game']not in GAMES or r['style']!='gen3':continue
        key=r['game'],r.get('map');tile=r['id'],r['quadrant'];art=path,index,r
        if'x'in r:pos[key][(*tile,r['x'],r['y'])]=art
        elif r.get('map'):scoped[key][tile]=art
        else:global_[r['game'],r['tileset']][tile]=art
    packed={};groups=defaultdict(list);changes=[];receipts=[];summary=Counter();reviewed=Counter();source_data={}
    def object_image(r,background_indices=()):
        if r.get('asset'):
            assert sha((mod/r['asset']).read_bytes())==r['assetFileHash']
            return Image.open(mod/r['asset']).convert('RGBA')
        im=Image.new('RGBA',(16,16))
        for part_index,part in enumerate(r.get('parts',[])):
            if part_index in background_indices or ref_key(part['donor'])==('firered','player_house',40):continue
            source=preview.native_donor(cache,part['donor'],packed,part.get('layers'),part.get('layerHashes'))
            sx,sy=part.get('srcX',0),part.get('srcY',0)
            im.alpha_composite(source.crop((sx,sy,sx+part['w'],sy+part['h'])),(part.get('x',0),part.get('y',0)))
        return im
    for game in GAMES:
      d=source_data[game]=review.source(cache,game)
      for name,md in d['maps'].items():
        selected=global_[game,md['tileset']].copy();selected.update(scoped[game,name]);active={}
        for i,bid in enumerate(catalog.lua_array(md['blocks'])):
            for q in range(4):
                x,y=i%md['width']*2+q%2,i//md['width']*2+q//2
                art=pos[game,name].get((bid,q,x,y),selected.get((bid,q)))
                if art:active[x,y]=art
        touched=False
        for(x,y),(path,index,r)in active.items():
            if'bookcase'not in r['role']or not r.get('base')or not(r.get('asset')or r.get('parts')):continue
            foreground=object_image(r);alpha=list(foreground.getchannel('A').get_flattened_data())
            assert set(alpha)<={0,255}
            if not any(v==0 for v in alpha):continue
            reviewed['bookcase_cells_with_transparency']+=1
            potential_header=y==0 and name in HEAD_MAPS and ref_key(r['base'])==('firered','player_house',40)
            potential_lower=y>0 and name in LOWER_MAPS
            if not(potential_header or potential_lower):continue
            neighbors=[]
            for(nx,ny),(np,ni,nr)in active.items():
                if ny!=y or'bookcase'in nr['role']or not nr.get('donor'):continue
                wall=ref_key(nr['donor'])==('firered','pewter_gym',705)
                floor=(nr.get('sourceCollision')==0 and any(t in nr['role']for t in('floor','ground','tatami'))
                    and ref_key(nr['donor'])in(('firered','pewter_gym',704),('firered','pewter_gym',723)))
                if(y==0 and wall)or(y>0 and floor):neighbors.append((abs(nx-x),nx,ny,np,nr))
            if not neighbors:continue
            neighbors.sort(key=lambda item:item[:3]);distance,nx,ny,np,nr=neighbors[0]
            expected_backdrop=preview.replacement_image(cache,nr,packed,mod)
            # A wall/floor must be unambiguous across the exposed row.
            assert all(preview.replacement_image(cache,n,packed,mod).tobytes()==expected_backdrop.tobytes()for _,_,_,_,n in neighbors)
            old_image=preview.replacement_image(cache,r,packed,mod)
            mismatches=sum(a==0 and before!=expected for a,before,expected in zip(alpha,old_image.get_flattened_data(),expected_backdrop.get_flattened_data()))
            if not mismatches:continue
            header=y==0 and name in HEAD_MAPS and ref_key(r['base'])==('firered','player_house',40)
            lower=y>0 and name in LOWER_MAPS
            if not(header or lower):continue
            c=review.cell_info(cache,game,d,md['tileset'],r['id'],r['quadrant'])
            assert c['sourceHash']==r['sourceHash']and c['collision']==r['sourceCollision']
            assert all(r['sourceFiles'][k]==v for k,v in d['fingerprints'][md['tileset']].items())
            assert[bool(v.get('priority'))for v in c['attributes']]==r['sourcePriority']
            assert[v.get('palette',1)for v in c['attributes']]==r['sourcePalettes']
            row=copy.deepcopy(r);row['base']=copy.deepcopy(nr['donor']);replaced_backing_parts=0
            background_indices={i for i,p in enumerate(r.get('parts',[]))if ref_key(p['donor'])==('firered','player_house',40)}
            for old_part,part in zip(r.get('parts',[]),row.get('parts',[])):
                if ref_key(part['donor'])==('firered','player_house',40):
                    assert not part.get('layers')and not part.get('layerHashes')
                    part['donor']=copy.deepcopy(nr['donor']);replaced_backing_parts+=1
                else:assert part==old_part,'Native bookcase object part changed'
            assert object_image(row,background_indices).tobytes()==foreground.tobytes()
            result=preview.replacement_image(cache,row,packed,mod)
            assert all((new==old if a else new==bg)for a,new,old,bg in zip(alpha,result.get_flattened_data(),old_image.get_flattened_data(),expected_backdrop.get_flattened_data()))
            assert all(not a or new==fg for a,new,fg in zip(alpha,result.get_flattened_data(),foreground.get_flattened_data()))
            row['compositionPixelHash']=sha(result.tobytes())
            row['bookcaseBackdropReview']=dict(native_background=copy.deepcopy(nr['donor']),reference_cell=[nx,ny],
                original_base=copy.deepcopy(r['base']),native_opaque_art_unchanged=True,transparent_pixels=alpha.count(0),
                native_foreground_RGBA_sha256=sha(foreground.tobytes()),pure_legacy_wall_parts_rebacked=replaced_backing_parts)
            row['evidence']+=' Match only transparent bookcase surroundings to the actual exposed native wall or floor in this source row. Complete opaque artwork and all non-background native parts remain pixel-identical at1:1. Replace obsolete pure wall40 backing parts where present; source layout, interactions, collision, NPCs, warps, palette and priority stay unchanged.'
            groups[path,index].append(((x,y),row));summary['header_cells'if header else'lower_floor_cells']+=1;touched=True
            changes.append(dict(game=game,map=name,xy=[x,y],module=path,id=r['id'],quadrant=r['quadrant'],
                sourceHash=r['sourceHash'],old_base=r['base'],native_backdrop=nr['donor'],reference_cell=[nx,ny],
                transparent_pixels=alpha.count(0),changed_transparent_pixels=mismatches,all_native_opaque_pixels_unchanged=True,
                all_transparent_pixels_match_room=True,native_foreground_RGBA_sha256=sha(foreground.tobytes()),
                old_RGBA_sha256=sha(old_image.tobytes()),new_RGBA_sha256=sha(result.tobytes())))
        if touched:receipts.append(dict(game=game,map=name,definition_sha256=sha(json.dumps(canonical(md),separators=(',',':')).encode()),objects=md.get('objects',[]),warps=md.get('warps',[]),bg_events=md.get('bgEvents',[])))
    assert dict(summary)==dict(header_cells=72,lower_floor_cells=45),summary
    updates=defaultdict(dict);new_rows=[]
    for(path,index),items in groups.items():
        old=modules[path][index]
        assert{xy for xy,row in items}=={tuple(xy)for xy in old['sourceCells']}
        assert len({json.dumps({k:r[k]for k in('base','parts','asset')if k in r},sort_keys=True)for xy,r in items})==1
        row=items[0][1];row['sourceCells']=copy.deepcopy(old['sourceCells'])
        updates[path][row_key(old)]=row;new_rows.append(row)
    module_hashes={};footers={}
    for path,replacements in updates.items():
        original=(base/path).read_bytes();nl=b'\r\n'if b'\r\n'in original else b'\n'
        assert MARKER.encode()not in original and original.endswith(b'return rows'+nl)
        footer=(MARKER+'\nlocal replacements='+lua(canonical(replacements))+'\nlocal changed=0\n'
            'for index,row in ipairs(rows)do\n'
            "  local key=table.concat({row.game,row.map or -1,row.id,row.quadrant,row.x or -1,row.y or -1},':')\n"
            "  local replacement=row.style=='gen3'and replacements[key]\n"
            '  if replacement then rows[index]=replacement;changed=changed+1 end\nend\n'
            f"assert(changed=={len(replacements)},'Matched native bookcase source set changed')\n"
            '-- END MATCHED NATIVE BOOKCASE BACKDROPS\nreturn rows\n')
        delta=footer.replace('\n',nl.decode()).encode();(mod/path).write_bytes(original[:-len(b'return rows'+nl)]+delta)
        dest=out/(Path(path).name+'.footer');dest.write_bytes(delta);footers[path]=dict(path=str(dest),sha256=sha(delta),rows=len(replacements))
        after=preview.read_reviewed(mod/path);assert len(after)==len(modules[path])
        for old,row in zip(modules[path],after):assert row==replacements.get(row_key(old),old)
        module_hashes[path]=sha((mod/path).read_bytes())
    runtime=LuaRuntime(unpack_returned_tuples=True);runtime.globals().paths=runtime.table_from(paths)
    runtime.globals().source=lambda name:(mod/name).read_text(encoding='utf-8-sig')
    total=runtime.execute('''local rows={}
      for _,path in ipairs(paths)do for _,r in ipairs(assert(load(source(path),'@'..path))())do rows[#rows+1]=r end end
      local M=assert(load(source('lib/mapping.lua'),'@lib/mapping.lua'))();local _,errors=M.index(rows)
      assert(#errors==0,table.concat(errors,'\\n'));return #rows''')
    valid=review.validate_batch(new_rows,SimpleNamespace(cache=cache,engine=a.engine,output=out),mod)
    assert valid['rows_accepted']==len(new_rows)and valid['rejected']==0
    report=dict(status='passed',summary=dict(summary),reviewed=dict(reviewed),changed_cells=len(changes),changed_rows=len(new_rows),
        changes=changes,source_receipts=receipts,registered_rows=total,index_errors=0,native_validation=valid,
        all_other_existing_rows_identical=True,no_new_assets_or_runtime_API=True,all_foreground_art_unchanged=True,
        module_sha256=module_hashes,append_only_footers=footers,helper_sha256=sha(Path(__file__).read_bytes()))
    (out/'proof.json').write_text(json.dumps(canonical(report),indent=2)+'\n')
    combined=[]
    for path in paths:combined.extend(preview.read_reviewed(mod/path))
    for name in sorted({c['map']for c in changes}):preview.map_preview(cache,out,'crystal',name,name,combined,packed,3,mod)
    print(json.dumps(dict(status='passed',changed_cells=len(changes),changed_rows=len(new_rows),summary=dict(summary),registered_rows=total,index_errors=0,native_validation=valid)))

if __name__=='__main__':main()
