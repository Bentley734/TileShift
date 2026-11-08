"""Replace the two Violet-house GSC radio recolors with complete CrystalDust radios.

The intact native 16x32 radio and stand reuse already credited New Bark assets.
The original wall, floor, collision and radio interactions stay unchanged.
"""
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace
import argparse,copy,hashlib,json,os,re,sys

W=next(p for p in Path(__file__).resolve().parents if(p/'.tools/python').is_dir()and(p/'.work').is_dir())
sys.path.insert(0,str(W/'.tools/python'))
from PIL import Image
MODULE='mappings/johto_domestic_finish.lua'
MAPS=('VIOLET_KYLES_HOUSE','VIOLET_NICKNAME_SPEECH_HOUSE')
GAMES=('gold','silver','crystal')
PREFIX='assets/third_party/johto-hacks/newbark-crystaldust'
MARKER='-- BEGIN VIOLET COMPLETE NATIVE RADIOS'
sha=lambda b:hashlib.sha256(b).hexdigest()

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
    before=preview.read_reviewed(base/MODULE);updates={};new_rows=[];changes=[];packed={};source_receipts=[]
    native_whole=Image.new('RGBA',(16,32))
    pieces={}
    for y in(0,1):
        path=mod/PREFIX/f'domestic-radio-0-{y}.png'
        im=Image.open(path).convert('RGBA');assert im.size==(16,16)
        assert set(im.getchannel('A').get_flattened_data())<={0,255}
        pieces[y]=im;native_whole.paste(im,(0,y*16))
    for game in GAMES:
        data=review.source(cache,game);updates[game]={}
        for map_id in MAPS:
            md=data['maps'][map_id];assert(md['width']*2,md['height']*2)==(8,8)
            source_receipts.append(dict(game=game,map=map_id,definition_sha256=sha(json.dumps(canonical(md),separators=(',',':')).encode()),
                bg_events=md.get('bgEvents',[]),objects=md.get('objects',[]),warps=md.get('warps',[])))
            updates[game][map_id]={}
            old_rows=[r for r in before if r.get('game')==game and r.get('map')==map_id and r.get('style')=='gen3'and r.get('role')in('johto_domestic_radio_head','johto_domestic_radio')]
            assert len(old_rows)==2
            for old in old_rows:
                x,y=old['sourceCells'][0];assert x==2 and y in(0,1)and old['sourceCells']==[[x,y]]
                assert old['sourceCollision']==(7 if y==0 else 148)
                cell=review.cell_info(cache,game,data,md['tileset'],old['id'],old['quadrant'])
                assert cell['sourceHash']==old['sourceHash']and cell['collision']==old['sourceCollision']
                assert data['fingerprints'][md['tileset']]==old['sourceFiles']
                assert[bool(v.get('priority'))for v in cell['attributes']]==old['sourcePriority']
                assert[v.get('palette',1)for v in cell['attributes']]==old['sourcePalettes']
                asset=f'{PREFIX}/domestic-radio-0-{y}.png';native=pieces[y]
                row=copy.deepcopy(old)
                row.update(asset=asset,assetFileHash=sha((mod/asset).read_bytes()),assetPixelHash=sha(native.tobytes()),
                    role='violet_complete_crystaldust_radio_'+str(y),
                    credit='CrystalDust by Sierraffinity and contributors; complete native radio and stand at original pixel size.',
                    sourceUrl='https://github.com/Sierraffinity/CrystalDust',
                    evidence='Violet Kyle and Nickname Speech houses only. Replace the old recolored GSC radio with the complete native CrystalDust radio and stand16x32, retaining all native foreground pixels in original blocked cells(2,0)/(2,1). Original matching wall/floor bases, radio interaction, source collision, NPCs, warps, layout, palettes and priorities stay unchanged.')
                result=preview.replacement_image(cache,row,packed,mod);assert result.size==(16,16)
                assert all(not px[3]or px==actual for px,actual in zip(native.get_flattened_data(),result.get_flattened_data()))
                old_asset=Image.open(base/old['asset']).convert('RGBA')
                old_result=preview.replacement_image(cache,old,packed,base)
                assert all(op[3]or np[3]or oldp==newp for op,np,oldp,newp in zip(old_asset.get_flattened_data(),native.get_flattened_data(),old_result.get_flattened_data(),result.get_flattened_data()))
                row['compositionPixelHash']=sha(result.tobytes())
                key=str(old['id'])+':'+str(old['quadrant']);assert key not in updates[game][map_id]
                updates[game][map_id][key]=row;new_rows.append(row)
                changes.append(dict(game=game,map=map_id,xy=[x,y],id=row['id'],quadrant=row['quadrant'],
                    native_asset=asset,asset_RGBA_sha256=sha(native.tobytes()),all_native_opaque_pixels_retained=True,
                    original_base_unchanged=row['base']==old['base'],source_collision=row['sourceCollision'],
                    old_RGBA_sha256=sha(old_result.tobytes()),new_RGBA_sha256=sha(result.tobytes())))
    original=(base/MODULE).read_bytes();nl=b'\r\n'if b'\r\n'in original else b'\n'
    assert MARKER.encode()not in original and original.endswith(b'return rows'+nl)
    footer=(MARKER+'\nlocal updates='+lua(canonical(updates))+'\nlocal changed=0\n'
        'for index,row in ipairs(rows)do\n'
        "  local map=updates[row.game]and updates[row.game][row.map]\n"
        "  local replacement=row.style=='gen3'and map and map[tostring(row.id)..':'..tostring(row.quadrant)]\n"
        '  if replacement then rows[index]=replacement;changed=changed+1 end\nend\n'
        "assert(changed==12,'Violet native radio source set changed')\n"
        '-- END VIOLET COMPLETE NATIVE RADIOS\nreturn rows\n')
    (mod/MODULE).write_bytes(original[:-len(b'return rows'+nl)]+footer.replace('\n',nl.decode()).encode())
    after=preview.read_reviewed(mod/MODULE);assert len(after)==len(before)
    count=0
    for old,row in zip(before,after):
        replacement=updates.get(old.get('game'),{}).get(old.get('map'),{}).get(str(old['id'])+':'+str(old['quadrant']))if old.get('style')=='gen3'else None
        if replacement:assert row==replacement;count+=1
        else:assert row==old,'Unrelated domestic row changed'
    assert count==12
    paths=list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(mod/'main.lua').read_text())))
    runtime=LuaRuntime(unpack_returned_tuples=True);runtime.globals().paths=runtime.table_from(paths)
    runtime.globals().source=lambda name:(mod/name).read_text(encoding='utf-8-sig')
    total=runtime.execute('''local rows={}
      for _,path in ipairs(paths)do for _,r in ipairs(assert(load(source(path),'@'..path))())do rows[#rows+1]=r end end
      local M=assert(load(source('lib/mapping.lua'),'@lib/mapping.lua'))();local _,errors=M.index(rows)
      assert(#errors==0,table.concat(errors,'\\n'));return #rows''')
    valid=review.validate_batch(new_rows,SimpleNamespace(cache=cache,engine=a.engine,output=out),mod)
    assert valid['rows_accepted']==12 and valid['rejected']==0
    report=dict(status='passed',maps=list(MAPS),changed_rows=12,source_receipts=source_receipts,changes=changes,
        native_whole_size=[16,32],native_whole_RGBA_sha256=sha(native_whole.tobytes()),
        all_other_domestic_rows_unchanged=True,no_new_assets_or_runtime_API=True,
        registered_rows=total,index_errors=0,native_validation=valid,
        mapping_sha256=sha((mod/MODULE).read_bytes()),helper_sha256=sha(Path(__file__).read_bytes()))
    (out/'proof.json').write_text(json.dumps(canonical(report),indent=2)+'\n')
    allrows=[]
    for path in paths:allrows.extend(preview.read_reviewed(mod/path))
    for name in MAPS:preview.map_preview(cache,out,'crystal',name,name,allrows,packed,4,mod)
    print(json.dumps(dict(status='passed',changed_rows=12,registered_rows=total,index_errors=0,native_validation=valid)))

if __name__=='__main__':main()
