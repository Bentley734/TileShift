"""Mirror nine G/S/C gates' left side-door mats from their complete right mat.

The full native 16px FireRed mat is retained using sixteen cached full-height
columns in reverse order. Bottom doorway rugs already have exact mirrored
foregrounds and are intentionally left alone. No assets or runtime API change.
Run after other same-release mapping authoring; only this footer is regenerated.
"""
from pathlib import Path
from types import SimpleNamespace
import argparse,copy,hashlib,json,os,re,sys
W=next(p for p in Path(__file__).resolve().parents if(p/'.tools/python').is_dir()and(p/'.work').is_dir())
sys.path.insert(0,str(W/'.tools/python'))
from PIL import Image
GAMES=('gold','silver','crystal')
MAPS=('ROUTE_38_ECRUTEAK_GATE','ROUTE_17_ROUTE_18_GATE','ROUTE_32_RUINS_OF_ALPH_GATE',
    'ROUTE_8_SAFFRON_GATE','ROUTE_7_SAFFRON_GATE','ILEX_FOREST_AZALEA_GATE',
    'ROUTE_42_ECRUTEAK_GATE','ROUTE_16_GATE','ROUTE_15_FUCHSIA_GATE')
GUARDS=('game','style','map','tileset','id','quadrant','sourceHash','sourceFiles','sourceCells',
    'sourceCollision','sourcePriority','sourcePalettes','sourceWarps','x','y')
RIGHT=dict(game='firered',tileset='house',id=730,hash='8387298e67faa99820ed2fe5589f867b010acaf09151e4a65fe2aa67f79702fd')
LEFT=dict(game='firered',tileset='house',id=729,hash='f678d8560674949428f9bead45be6ce3e12ecab4bc9d7a4cb6bce9bc97b19b70')
MODULES=('mappings/johto_gate_finish.lua','mappings/gen2_kanto_rooms_finish.lua')
START='-- BEGIN GSC COMPLETE MIRRORED SIDE MATS'
END='-- END GSC COMPLETE MIRRORED SIDE MATS'
sha=lambda b:hashlib.sha256(b).hexdigest()
def canonical(v):
    if isinstance(v,dict):return {k:canonical(x)for k,x in sorted(v.items())}
    if isinstance(v,list):return [canonical(x)for x in v]
    return v
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--mod-root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--engine',type=Path,default=W/'.work/tileshift-engine-0420')
    a=p.parse_args();base=a.baseline.resolve();mod=a.mod_root.resolve();out=a.output.resolve()
    assert base!=mod and out not in (base,mod)
    assert json.loads((base/'manifest.json').read_text())['version']=='0.46.6'
    sys.path.insert(0,str(mod/'tools'))
    import preview,gen2_extended_review as review
    from newbark_building_review import lua
    from lupa.luajit21 import LuaRuntime
    cache=Path(os.environ['APPDATA'])/'pokemon-love2d';out.mkdir(parents=True,exist_ok=True)
    packed={};rows={m:preview.read_reviewed(base/m)for m in MODULES}
    donor=preview.native_donor(cache,RIGHT,packed);mirror=donor.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    parts=[dict(donor=copy.deepcopy(RIGHT),x=x,y=0,srcX=15-x,srcY=0,w=1,h=16)for x in range(16)]
    expected=Image.new('RGBA',(16,16))
    for part in parts:expected.paste(donor.crop((part['srcX'],0,part['srcX']+1,16)),(part['x'],0))
    assert expected.tobytes()==mirror.tobytes()
    assert donor.size==(16,16)and donor.getchannel('A').getextrema()==(255,255)
    updates={m:{}for m in MODULES};changes=[];newrows=[];receipts=[]
    for game in GAMES:
      data=review.source(cache,game)
      for name in MAPS:
        md=data['maps'][name];assert (md['width']*2,md['height']*2)==(10,8)
        selected={(r['id'],r['quadrant']):(m,r)for m,rs in rows.items()for r in rs
            if r['game']==game and r['style']=='gen3'and r.get('map')==name and'x'not in r}
        receipts.append(dict(game=game,map=name,definition_sha256=sha(json.dumps(canonical(md),separators=(',',':')).encode()),
            source_objects=md.get('objects',[]),source_warps=md.get('warps',[])))
        for y in (4,5):
            bid=md['blocks'][y//2*md['width']];q=y%2*2
            rb=md['blocks'][y//2*md['width']+4];rq=q+1
            module,old=selected[bid,q];_,right=selected[rb,rq]
            assert old['sourceCells']==[[0,y]]and right['sourceCells']==[[9,y]]
            assert old['sourceCollision']==118 and right['sourceCollision']==126
            assert old['kind']==right['kind']=='native'and old['donor']==LEFT and right['donor']==RIGHT
            cell=review.cell_info(cache,game,data,md['tileset'],bid,q)
            assert cell['sourceHash']==old['sourceHash']and cell['collision']==old['sourceCollision']
            assert data['fingerprints'][md['tileset']]==old['sourceFiles']
            assert [bool(v.get('priority'))for v in cell['attributes']]==old['sourcePriority']
            assert [v.get('palette',1)for v in cell['attributes']]==old['sourcePalettes']
            row=copy.deepcopy(old);row.pop('donor')
            row.update(kind='native_composite',parts=copy.deepcopy(parts),status='reviewed',
                role='gen2_gate_complete_mirrored_native_side_mat',compositionPixelHash=sha(mirror.tobytes()),
                evidence='Nine same-footprint east-west gates: exact horizontal mirror of the complete right native FireRed730 side-door mat. All256 native FLAT pixels remain at1:1, with16 complete1px columns placed in reverse order by the existing cached compositor. This corrects the inward-facing border from left donor729; the source left warp118, source palette/priority, destinations and room layout remain unchanged. Bottom doorway rugs are already mirrored and remain untouched.')
            assert all(row.get(k)==old.get(k)for k in GUARDS)
            assert preview.replacement_image(cache,row,packed,mod).tobytes()==mirror.tobytes()
            updates[module].setdefault(game,{}).setdefault(name,{})[str(bid)+':'+str(q)]=row;newrows.append(row)
            changes.append(dict(module=module,game=game,map=name,xy=[0,y],sourceHash=old['sourceHash'],
                sourceCollision=118,right_xy=[9,y],mirror_RGBA_sha256=sha(mirror.tobytes()),native_all256_pixels_retained=True))
    assert len(newrows)==54
    for module in MODULES:
        path=mod/module;original=path.read_bytes();nl=b'\r\n'if b'\r\n'in original else b'\n'
        assert original.endswith(b'return rows'+nl)
        if START.encode()in original:
            assert original.count(START.encode())==1 and original.count(END.encode())==1
            assert original.endswith(END.encode()+nl+b'return rows'+nl)
            original=original[:original.index(START.encode())]+b'return rows'+nl
        before=preview.read_reviewed(path)
        count=sum(c['module']==module for c in changes)
        footer=(START+'\nlocal updates='+lua(canonical(updates[module]))+'\nlocal changed=0\n'
            'for index,row in ipairs(rows)do\n'
            '  local map=updates[row.game]and updates[row.game][row.map]\n'
            "  local replacement=row.style=='gen3'and map and map[tostring(row.id)..':'..tostring(row.quadrant)]\n"
            '  if replacement then rows[index]=replacement;changed=changed+1 end\nend\n'
            f"assert(changed=={count},'Native side-mat source set changed')\n"+END+'\nreturn rows\n')
        path.write_bytes(original[:-len(b'return rows'+nl)]+footer.replace('\n',nl.decode()).encode())
        after=preview.read_reviewed(path);assert len(before)==len(after)
        for old,row in zip(before,after):
            target=updates[module].get(old['game'],{}).get(old.get('map'),{}).get(str(old['id'])+':'+str(old['quadrant']))if old['style']=='gen3'else None
            assert row==(target if target else old),'Unrelated row changed'
    paths=list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(mod/'main.lua').read_text())))
    vm=LuaRuntime(unpack_returned_tuples=True);vm.globals().paths=vm.table_from(paths)
    vm.globals().source=lambda n:(mod/n).read_text(encoding='utf-8-sig')
    total=vm.execute('''local rows={}for _,p in ipairs(paths)do for _,r in ipairs(assert(load(source(p),'@'..p))())do rows[#rows+1]=r end end
      local M=assert(load(source('lib/mapping.lua'),'@lib/mapping.lua'))();local _,e=M.index(rows)
      assert(#e==0,table.concat(e,'\\n'));return #rows''')
    valid=review.validate_batch(newrows,SimpleNamespace(cache=cache,engine=a.engine,output=out),mod)
    assert valid['rows_accepted']==54 and valid['rejected']==0
    proof=dict(status='passed',maps=MAPS,changed_rows=54,changes=changes,source_receipts=receipts,source_guards_unchanged=GUARDS,
        registered_rows=total,index_errors=0,native_validation=valid,no_new_assets_or_runtime_API=True,
        complete_native_pixel_scale=1,mirror_RGBA_sha256=sha(mirror.tobytes()),
        mapping_sha256={m:sha((mod/m).read_bytes())for m in MODULES},helper_sha256=sha(Path(__file__).read_bytes()))
    (out/'proof.json').write_text(json.dumps(canonical(proof),indent=2)+'\n')
    print(json.dumps(dict(status='passed',changed_rows=54,registered_rows=total,index_errors=0,native_validation=valid)))
if __name__=='__main__':main()
