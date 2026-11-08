"""Replace Route 31's rug-shaped gate counters with whole native counter modules.

The native FireRed house counter family includes the cream counter fronts used
pixel-for-pixel by CrystalDust's gate. Full 16px corners and returns preserve
the original two U-shaped collision footprints, with no decorative overhang.
The upper-left inner join uses a continuous straight post, rather than a
terminal return whose border stops before reaching the front counter.
"""
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace
import argparse,copy,hashlib,json,os,re,sys

W=next(p for p in Path(__file__).resolve().parents if(p/'.tools/python').is_dir()and(p/'.work').is_dir())
sys.path.insert(0,str(W/'.tools/python'))
from PIL import Image
MODULE='mappings/johto_gate_finish.lua';MAP='ROUTE_31_VIOLET_GATE'
MARKER='-- BEGIN ROUTE31 WHOLE NATIVE GATE COUNTERS'
GAMES=('gold','silver','crystal')
RIGHT_MAT=dict(game='firered',tileset='house',id=730,
    hash='8387298e67faa99820ed2fe5589f867b010acaf09151e4a65fe2aa67f79702fd')
HASHES={
653:'4b5739a5dc27019185547b1002b5d3c41ed8f889e0a159a063a892655d5816c9',
660:'ef71522dd45c5893e260eee1c80c93b042364fd7608b7912811df7127793e6ac',
662:'41e7fea10bcd9dc0ca73e7277cdae06f3113df63273b0448263a755fa2248fdb',
668:'ae4cd6dc09a6b045ff596b7e2c9d6ae3622af3c35083f81a46e7315a9e7e209e',
670:'a5b45908ddbbfcb809449a0942686a1bee4eeb6d03bcb8f5637228456b2ef1dc',
676:'6ee549cb6815f8c61d435f17bdb51cd5595b6c2704adc7647f30a5aa7a35fc93',
677:'f50b7a4487eb9d69d7a7c17581cdb24c0f202fb24482691a0f20910e8fe0907f',
678:'0278f7aaf9605bc2a8173cade61206d980f97e8d2f365848349c12a55e235819',
}
LAYOUT={(2,1):653,(7,1):653,(2,2):653,(7,2):670,
    (2,3):676,(3,3):677,(4,3):677,(5,3):677,(6,3):677,(7,3):678,
    (2,6):660,(3,6):677,(4,6):677,(5,6):677,(6,6):677,(7,6):662,(2,7):653,(7,7):653}
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
    assert json.loads((base/'manifest.json').read_text())['version']=='0.46.3'
    sys.path.insert(0,str(mod/'tools'))
    import catalog,preview,gen2_extended_review as review
    from newbark_building_review import lua
    from lupa.luajit21 import LuaRuntime
    cache=Path(os.environ['APPDATA'])/'pokemon-love2d';out.mkdir(parents=True,exist_ok=True)
    before=preview.read_reviewed(base/MODULE);updates={};new_rows=[];changes=[];source_receipts=[];packed={};mat_receipts=[]
    right_mat=preview.native_donor(cache,RIGHT_MAT,packed)
    mirrored_mat=right_mat.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    mat_parts=[dict(donor=copy.deepcopy(RIGHT_MAT),x=x,y=0,srcX=15-x,srcY=0,w=1,h=16)for x in range(16)]
    reconstructed=Image.new('RGBA',(16,16))
    for part in mat_parts:reconstructed.paste(right_mat.crop((part['srcX'],0,part['srcX']+1,16)),(part['x'],0))
    assert reconstructed.tobytes()==mirrored_mat.tobytes()
    evidence=('Route31 Violet Gate only: replace the former blue carpet interior and rug-edge counter stand-ins '
        'with complete native FireRed cream counter tops, grey front bodies, outside ends and inside returns. '
        'Front modules676/677/678 are pixel-identical to CrystalDust gate modules548/549/550. All complete16x16 '
        'FLAT native pixels, including the front body in the base layer, remain intact at1:1. Both original '
        'U-shaped COLL_COUNTER footprints remain visible; no blocked floor or protruding artwork is introduced. '
        'The original whole16px FireGold monitor and keyboard alpha remains on the right return. Guard, lady, entrances, counter '
        'talk-through interaction, room layout, source collision, source NPC positions and scripts are unchanged.')
    for game in GAMES:
        data=review.source(cache,game);md=data['maps'][MAP]
        assert(md['width']*2,md['height']*2)==(10,8)
        selected={(r['id'],r['quadrant']):r for r in before if r.get('game')==game and r.get('style')=='gen3'and r.get('map')==MAP}
        counter_cells=set();source_receipts.append(dict(game=game,definition_sha256=sha(json.dumps(canonical(md),separators=(',',':')).encode()),objects=md['objects'],warps=md['warps']))
        for y in range(8):
            for x in range(10):
                bid=md['blocks'][y//2*md['width']+x//2];q=y%2*2+x%2
                cell=review.cell_info(cache,game,data,md['tileset'],bid,q)
                if cell['collision']==0x90:counter_cells.add((x,y))
                if y in(4,5):assert cell['collision']in(0,0x76,0x7e),'Keep the entire east-west walkway clear'
        assert counter_cells==set(LAYOUT)
        updates[game]={}
        for(x,y),mid in sorted(LAYOUT.items()):
            bid=md['blocks'][y//2*md['width']+x//2];q=y%2*2+x%2;old=selected[bid,q]
            assert old.get('x')is None and old.get('y')is None and old['sourceCells']==[[x,y]]
            cell=review.cell_info(cache,game,data,md['tileset'],bid,q)
            assert cell['sourceHash']==old['sourceHash']and cell['collision']==old['sourceCollision']==0x90
            assert data['fingerprints'][md['tileset']]==old['sourceFiles']
            assert[bool(v.get('priority'))for v in cell['attributes']]==old['sourcePriority']
            assert[v.get('palette',1)for v in cell['attributes']]==old['sourcePalettes']
            donor=dict(game='firered',tileset='house',id=mid,hash=HASHES[mid]);native=preview.native_donor(cache,donor,packed)
            assert native.size==(16,16)and native.getchannel('A').getextrema()==(255,255)
            row=copy.deepcopy(old)
            for field in('donor','base','parts','asset','assetFileHash','assetPixelHash','credit','sourceUrl','nativeContext','animated','animation','assetFrames','frames','artOverlay'):
                row.pop(field,None)
            row.update(status='reviewed',evidence=evidence,role='route31_gate_complete_native_counter_'+str(mid))
            if(x,y)==(7,2):
                assert old['kind']=='third_party'and old['asset']=='assets/third_party/johto-hacks/interiors/firegold-lab-computer.png'
                for field in('asset','assetFileHash','assetPixelHash','credit','sourceUrl'):
                    if field in old:row[field]=copy.deepcopy(old[field])
                row.update(kind='third_party',base=donor,role='route31_gate_native_counter_with_monitor_keyboard')
                fg=Image.open(mod/old['asset']).convert('RGBA');expected=Image.alpha_composite(native,fg)
                assert any(p[3]for p in fg.get_flattened_data())
                assert all(not p[3]or p==v for p,v in zip(fg.get_flattened_data(),expected.get_flattened_data()))
            else:
                row.update(kind='native',donor=donor);expected=native
            result=preview.replacement_image(cache,row,packed,mod)
            assert result.tobytes()==expected.tobytes()
            row['compositionPixelHash']=sha(result.tobytes())
            key=str(bid)+':'+str(q);assert key not in updates[game];updates[game][key]=row
            new_rows.append(row)
            changes.append(dict(game=game,xy=[x,y],id=bid,quadrant=q,sourceHash=old['sourceHash'],
                counter_donor=donor,native_RGBA_sha256=sha(native.tobytes()),whole_FLAT_pixels_preserved=True,
                composition_RGBA_sha256=sha(result.tobytes()),pc_foreground_preserved=(x,y)==(7,2)))
        for y in(4,5):
            bid=md['blocks'][y//2*md['width']];q=y%2*2;old=selected[bid,q]
            right_bid=md['blocks'][y//2*md['width']+9//2];right_q=y%2*2+1
            right_row=selected[right_bid,right_q]
            assert old['sourceCells']==[[0,y]]and old['sourceCollision']==0x76
            assert right_row['sourceCells']==[[9,y]]and right_row['sourceCollision']==0x7e
            assert right_row['kind']=='native'and right_row['donor']==RIGHT_MAT
            cell=review.cell_info(cache,game,data,md['tileset'],bid,q)
            assert cell['sourceHash']==old['sourceHash']and cell['collision']==old['sourceCollision']==0x76
            assert data['fingerprints'][md['tileset']]==old['sourceFiles']
            assert[bool(v.get('priority'))for v in cell['attributes']]==old['sourcePriority']
            assert[v.get('palette',1)for v in cell['attributes']]==old['sourcePalettes']
            row=copy.deepcopy(old)
            for field in('donor','base','parts','asset','assetFileHash','assetPixelHash','credit','sourceUrl','nativeContext','animated','animation','assetFrames','frames','artOverlay'):
                row.pop(field,None)
            row.update(kind='native_composite',parts=copy.deepcopy(mat_parts),
                role='route31_gate_mirrored_native_entrance_mat',status='reviewed',
                compositionPixelHash=sha(mirrored_mat.tobytes()),
                evidence='User-requested exact horizontal mirror of the corresponding right entrance mat. Retain all256 native FireRed730 FLAT RGBA pixels at1:1, placing its16 full-height native columns in reverse order through the existing cached compositor. No generated pixels, rescaling, missing outline or new runtime transform. Preserve the original left warp collision118, source cells, palette/priority, destination and source map; the right mat remains byte-unchanged.')
            assert preview.replacement_image(cache,row,packed,mod).tobytes()==mirrored_mat.tobytes()
            key=str(bid)+':'+str(q);assert key not in updates[game];updates[game][key]=row;new_rows.append(row)
            mat_receipts.append(dict(game=game,left_xy=[0,y],right_xy=[9,y],sourceHash=row['sourceHash'],
                collision=row['sourceCollision'],right_source=RIGHT_MAT,right_RGBA_sha256=sha(right_mat.tobytes()),
                left_RGBA_sha256=sha(mirrored_mat.tobytes()),all256pixels_horizontally_mirrored=True))
    original=(base/MODULE).read_bytes();nl=b'\r\n'if b'\r\n'in original else b'\n'
    assert MARKER.encode()not in original and original.endswith(b'return rows'+nl)
    footer=(MARKER+'\nlocal updates='+lua(canonical(updates))+'\nlocal changed=0\n'
        'for index,row in ipairs(rows)do\n'
        "  if row.style=='gen3'and row.map=='ROUTE_31_VIOLET_GATE'and updates[row.game]then\n"
        "    local replacement=updates[row.game][tostring(row.id)..':'..tostring(row.quadrant)]\n"
        '    if replacement then rows[index]=replacement;changed=changed+1 end\n  end\nend\n'
        "assert(changed==60,'Route31 gate counter/mat source set changed')\n"
        '-- END ROUTE31 WHOLE NATIVE GATE COUNTERS\nreturn rows\n')
    (mod/MODULE).write_bytes(original[:-len(b'return rows'+nl)]+footer.replace('\n',nl.decode()).encode())
    after=preview.read_reviewed(mod/MODULE);assert len(after)==len(before)
    count=0
    for old,row in zip(before,after):
        replace=old.get('game')in updates and old.get('style')=='gen3'and old.get('map')==MAP and(str(old['id'])+':'+str(old['quadrant']))in updates[old['game']]
        if replace:
            assert row==updates[old['game']][str(old['id'])+':'+str(old['quadrant'])];count+=1
        else:assert row==old,'Unrelated gate row changed'
    assert count==60
    paths=list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(mod/'main.lua').read_text())))
    runtime=LuaRuntime(unpack_returned_tuples=True);runtime.globals().paths=runtime.table_from(paths)
    runtime.globals().source=lambda name:(mod/name).read_text(encoding='utf-8-sig')
    total=runtime.execute('''local rows={}
      for _,path in ipairs(paths)do for _,r in ipairs(assert(load(source(path),'@'..path))())do rows[#rows+1]=r end end
      local M=assert(load(source('lib/mapping.lua'),'@lib/mapping.lua'))();local _,errors=M.index(rows)
      assert(#errors==0,table.concat(errors,'\\n'));return #rows''')
    valid=review.validate_batch(new_rows,SimpleNamespace(cache=cache,engine=a.engine,output=out),mod)
    assert valid['rows_accepted']==60 and valid['rejected']==0
    report=dict(status='passed',map=MAP,source_receipts=source_receipts,changes=changes,mirrored_mats=mat_receipts,
        original_counter_cells=sorted([list(x)for x in LAYOUT]),walkway_cells=[[x,y]for y in(4,5)for x in range(10)],
        registered_rows=total,index_errors=0,native_validation=valid,other_gate_rows_identical=True,
        no_added_overhangs_or_foreground_API=True,mapping_sha256=sha((mod/MODULE).read_bytes()),helper_sha256=sha(Path(__file__).read_bytes()))
    (out/'proof.json').write_text(json.dumps(canonical(report),indent=2)+'\n')
    allrows=[]
    for path in paths:allrows.extend(preview.read_reviewed(mod/path))
    preview.map_preview(cache,out,'crystal',MAP,'crystal-gate',allrows,packed,4,mod)
    print(json.dumps(dict(status='passed',changed_rows=60,registered_rows=total,index_errors=0,native_validation=valid)))

if __name__=='__main__':main()
