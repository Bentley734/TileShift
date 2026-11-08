"""Review the complete native CrystalDust Violet glyphs and Bellsprout frame.

Use violet_native_details.py to reproduce the credited source assets first.
Only Violet Gym compact glyphs and the Sprout3F mural are changed. Source
collision, NPCs, interaction coordinates, warps and original geometry remain.
"""
from __future__ import annotations
import argparse,copy,hashlib,json,os,re,sys
from pathlib import Path
from types import SimpleNamespace

W=next(p for p in Path(__file__).resolve().parents if(p/'.tools/python').is_dir()and(p/'.work').is_dir())
sys.path.insert(0,str(W/'.tools/python'))
from PIL import Image

GAMES=('gold','silver','crystal')
PREFIX='assets/third_party/johto-hacks/violet-native-details'
TARGETS={
    'mappings/gen2_facility_floor_audit.lua':('VIOLET_GYM','facility_complete_original_violet_compact_statue'),
    'mappings/johto_tower_finish.lua':('SPROUT_TOWER_3F','johto_tower_complete_bellsprout_painting'),
}
GYM_CELLS={(2,2),(3,2),(6,2),(7,2),(0,12),(1,12),(8,12),(9,12),(0,14),(1,14),(8,14),(9,14)}
GYM_FLOOR=dict(game='firered',tileset='building__rom_082d4cbc',id=641,
    hash='454eb278b23aad627b15eb73d65a390385199be283f4a647710d2163e5d9001f')
TOWER_FLOOR=dict(game='firered',tileset='pewter_gym',id=704,
    hash='1bdabe55382936b12d2fb873c24c4e92d72fa876a79e37906742c1b7d0f75694')
MARKER='-- BEGIN VIOLET COMPLETE NATIVE DETAILS'
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def canonical(value):
    if isinstance(value,dict):return{k:canonical(v)for k,v in sorted(value.items())}
    if isinstance(value,list):return[canonical(v)for v in value]
    return value

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--mod-root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--engine',type=Path,default=W/'.work/tileshift-engine-0420')
    a=p.parse_args();base=a.baseline.resolve();mod=a.mod_root.resolve();out=a.output.resolve()
    assert base!=mod and out not in(base,mod)
    assert json.loads((base/'manifest.json').read_text())['version']=='0.46.5'
    sys.path.insert(0,str(mod/'tools'))
    import preview,gen2_extended_review as review
    from newbark_building_review import lua
    from lupa.luajit21 import LuaRuntime
    cache=Path(os.environ['APPDATA'])/'pokemon-love2d';out.mkdir(parents=True,exist_ok=True)
    provenance=json.loads((mod/PREFIX/'provenance.json').read_text())
    assert provenance['rom_sha256']=='51196cba923c315d0088b747b5cdee704f2ac057cd493f9ddf226fb7227302cf'
    native={}
    for name in('gym-compact-statue','sprout-painting-left','sprout-painting-right'):
        im=Image.open(mod/PREFIX/(name+'.png')).convert('RGBA');assert im.size==(16,16)
        assert set(im.getchannel('A').get_flattened_data())<={0,255}
        receipt=provenance['source_modules'][name]
        assert receipt['asset']==f'{PREFIX}/{name}.png'
        assert receipt['assetFileHash']==sha((mod/receipt['asset']).read_bytes())
        assert receipt['assetPixelHash']==sha(im.tobytes())
        assert receipt['pixel_scale']==1 and receipt['native_alpha_unchanged']and receipt['whole_native_metatile_layer']
        native[name]=im
    portrait=Image.new('RGBA',(16,16))
    portrait.paste(native['sprout-painting-left'].crop((8,0,16,16)),(0,0))
    portrait.paste(native['sprout-painting-right'].crop((0,0,8,16)),(8,0))
    packed={};new_rows=[];changes=[];receipts=[];module_hashes={}
    for module,(map_id,old_role)in TARGETS.items():
        before=preview.read_reviewed(base/module);updates={}
        for game in GAMES:
            data=review.source(cache,game);md=data['maps'][map_id]
            receipts.append(dict(game=game,map=map_id,
                definition_sha256=sha(json.dumps(canonical(md),separators=(',',':')).encode()),
                bg_events=md.get('bgEvents',[]),objects=md.get('objects',[]),warps=md.get('warps',[])))
            selected=[r for r in before if r.get('game')==game and r.get('style')=='gen3'
                and r.get('map')==map_id and r.get('role')==old_role]
            assert len(selected)==2
            actual_cells={tuple(xy)for r in selected for xy in r['sourceCells']}
            assert actual_cells==(GYM_CELLS if map_id=='VIOLET_GYM'else{(9,0),(10,0)})
            updates[game]={map_id:{}}
            for old in selected:
                assert old['kind']=='source_palette'and old['sourceCollision']==7
                cell=review.cell_info(cache,game,data,md['tileset'],old['id'],old['quadrant'])
                assert cell['sourceHash']==old['sourceHash']and cell['collision']==old['sourceCollision']
                assert data['fingerprints'][md['tileset']]==old['sourceFiles']
                assert[bool(v.get('priority'))for v in cell['attributes']]==old['sourcePriority']
                assert[v.get('palette',1)for v in cell['attributes']]==old['sourcePalettes']
                if map_id=='VIOLET_GYM':
                    assert tuple(cell['tiles'])==(85,86,87,88)
                    name='gym-compact-statue';floor=GYM_FLOOR
                    role='violet_complete_native_crystaldust_compact_gym_glyph'
                    evidence=('The entire native CrystalDust Violet Gym16x16 carved gym panel, TOP metatile766, '
                        'fits the original compact blocked glyph footprint at native scale. Both source glyph families '
                        'use this same authentic native panel as the supplied CrystalDust map. Transparent exterior '
                        'retains the unchanged adjoining FRLG gym floor641; no tall statue is cropped or shrunk.')
                else:
                    x,y=old['sourceCells'][0];assert y==0
                    assert tuple(cell['tiles'])==((17,72,33,88)if x==9 else(73,17,89,33))
                    name='sprout-painting-left'if x==9 else'sprout-painting-right';floor=TOWER_FLOOR
                    role='violet_complete_native_crystaldust_bellsprout_frame'
                    evidence=('The complete native16x16 CrystalDust Bellsprout portrait and all four frame corners '
                        'span the centered adjacent8px halves at original blocked cells(9,0)/(10,0). Exact native '
                        'TOP528/520 retain the matching8px timber sides at1:1. The picture is neither shrunk nor '
                        'clipped; the original source read interaction and timber-floor base are preserved.')
                row=copy.deepcopy(old)
                for key in('sourceColors','nativeSizeOriginalAsset','facilityFloorAudit'):
                    row.pop(key,None)
                asset=f'{PREFIX}/{name}.png';im=native[name]
                row.update(kind='third_party',asset=asset,assetFileHash=sha((mod/asset).read_bytes()),
                    assetPixelHash=sha(im.tobytes()),base=copy.deepcopy(floor),role=role,
                    credit='CrystalDust by Sierraffinity and contributors; complete native Violet artwork at original pixel size.',
                    sourceUrl='https://github.com/Sierraffinity/CrystalDust',
                    evidence=evidence+' Source collisions, NPCs, event scripts, map layout, warps, palettes and priorities stay unchanged.')
                result=preview.replacement_image(cache,row,packed,mod)
                assert all(not px[3]or px==actual for px,actual in zip(im.get_flattened_data(),result.get_flattened_data()))
                ground=preview.native_donor(cache,floor,packed)
                assert all(px[3]or actual==bg for px,actual,bg in zip(im.get_flattened_data(),result.get_flattened_data(),ground.get_flattened_data()))
                row['compositionPixelHash']=sha(result.tobytes())
                key=str(row['id'])+':'+str(row['quadrant']);assert key not in updates[game][map_id]
                updates[game][map_id][key]=row;new_rows.append(row)
                changes.append(dict(module=module,game=game,map=map_id,source_cells=old['sourceCells'],
                    id=row['id'],quadrant=row['quadrant'],asset=asset,asset_RGBA_sha256=sha(im.tobytes()),
                    all_native_opaque_pixels_retained=True,native_transparent_pixels_reveal_matching_floor=True,
                    source_collision=7,composition_RGBA_sha256=sha(result.tobytes())))
        original=(base/module).read_bytes();nl=b'\r\n'if b'\r\n'in original else b'\n'
        assert MARKER.encode()not in original and original.endswith(b'return rows'+nl)
        footer=(MARKER+'\nlocal updates='+lua(canonical(updates))+'\nlocal changed=0\n'
            'for index,row in ipairs(rows)do\n'
            '  local map=updates[row.game]and updates[row.game][row.map]\n'
            "  local replacement=row.style=='gen3'and map and map[tostring(row.id)..':'..tostring(row.quadrant)]\n"
            '  if replacement then rows[index]=replacement;changed=changed+1 end\nend\n'
            "assert(changed==6,'Violet complete native detail source set changed')\n"
            '-- END VIOLET COMPLETE NATIVE DETAILS\nreturn rows\n')
        (mod/module).write_bytes(original[:-len(b'return rows'+nl)]+footer.replace('\n',nl.decode()).encode())
        after=preview.read_reviewed(mod/module);assert len(after)==len(before)
        count=0
        for old,row in zip(before,after):
            replacement=updates.get(old.get('game'),{}).get(old.get('map'),{}).get(str(old['id'])+':'+str(old['quadrant']))if old.get('style')=='gen3'else None
            if replacement:assert row==replacement;count+=1
            else:assert row==old,'Unrelated mapping row changed'
        assert count==6;module_hashes[module]=sha((mod/module).read_bytes())
    paths=list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(mod/'main.lua').read_text())))
    runtime=LuaRuntime(unpack_returned_tuples=True);runtime.globals().paths=runtime.table_from(paths)
    runtime.globals().source=lambda name:(mod/name).read_text(encoding='utf-8-sig')
    total=runtime.execute('''local rows={}
      for _,path in ipairs(paths)do for _,r in ipairs(assert(load(source(path),'@'..path))())do rows[#rows+1]=r end end
      local M=assert(load(source('lib/mapping.lua'),'@lib/mapping.lua'))();local _,errors=M.index(rows)
      assert(#errors==0,table.concat(errors,'\\n'));return #rows''')
    valid=review.validate_batch(new_rows,SimpleNamespace(cache=cache,engine=a.engine,output=out),mod)
    assert valid['rows_accepted']==12 and valid['rejected']==0
    report=dict(status='passed',changed_rows=12,source_receipts=receipts,changes=changes,
        whole_native_painting_size=[16,16],whole_native_painting_RGBA_sha256=sha(portrait.tobytes()),
        all_other_mapping_rows_unchanged=True,no_runtime_API_changes=True,
        registered_rows=total,index_errors=0,native_validation=valid,
        module_sha256=module_hashes,helper_sha256=sha(Path(__file__).read_bytes()),
        native_provenance_sha256=sha((mod/PREFIX/'provenance.json').read_bytes()))
    (out/'proof.json').write_text(json.dumps(canonical(report),indent=2)+'\n')
    allrows=[]
    for path in paths:allrows.extend(preview.read_reviewed(mod/path))
    for name in('VIOLET_GYM','SPROUT_TOWER_3F'):
        preview.map_preview(cache,out,'crystal',name,name,allrows,packed,3,mod)
    print(json.dumps(dict(status='passed',changed_rows=12,registered_rows=total,index_errors=0,native_validation=valid)))

if __name__=='__main__':main()
