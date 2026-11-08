"""Use the adjacent native static pond water beneath Route 31's intact shore corner.

Run against an unmodified 0.46.2 source checkout and an isolated candidate.
Only three existing Gold/Silver/Crystal rows change; source maps stay read-only.
"""
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace
import argparse,copy,hashlib,json,os,re,sys

W=next(p for p in Path(__file__).resolve().parents if(p/'.tools/python').is_dir()and(p/'.work').is_dir())
sys.path.insert(0,str(W/'.tools/python'))
from PIL import Image

MODULE='mappings/johto_terrain_repeats.lua'
MARKER='-- BEGIN ROUTE31 NATIVE STATIC POND CORNER'
GAMES=('gold','silver','crystal')
sha=lambda b:hashlib.sha256(b).hexdigest()
def canonical(value):
    if isinstance(value,dict):return{k:canonical(v)for k,v in sorted(value.items())}
    if isinstance(value,list):return[canonical(v)for v in value]
    return value
def target(r):return r.get('game')in GAMES and r.get('style')=='gen3'and r.get('map')=='ROUTE_31'and r.get('id')==122 and r.get('quadrant')==1

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--mod-root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--engine',type=Path,default=W/'.work/tileshift-engine-0420')
    a=p.parse_args();base=a.baseline.resolve();mod=a.mod_root.resolve();out=a.output.resolve()
    assert base!=mod and out not in(base,mod)
    assert json.loads((base/'manifest.json').read_text())['version']=='0.46.2'
    sys.path.insert(0,str(mod/'tools'))
    import catalog,preview,gen2_extended_review as review
    from newbark_building_review import lua
    from lupa.luajit21 import LuaRuntime
    cache=Path(os.environ['APPDATA'])/'pokemon-love2d';out.mkdir(parents=True,exist_ok=True)
    before=preview.read_reviewed(base/MODULE)
    old=[r for r in before if target(r)];assert len(old)==3 and{r['game']for r in old}==set(GAMES)
    water=dict(game='firered',tileset='viridian_outdoor',id=430,
        hash='037c2cb2c4abb18bbba3e60a79453cae96784fed6e76f85190ae331182488844')
    bank=copy.deepcopy(old[0]['donor']);assert bank==dict(game='emerald',tileset='general__petalburg',id=410,
        hash='ddb9eb3a8d13891e384ffabde65c5af4a693f7361fac94040e32f5c13b83aec9')
    packed={};background=preview.native_donor(cache,water,packed)
    original=preview.native_donor(cache,bank,packed)
    mids,palette,layers=packed[(bank['game'],bank['tileset'])];slot=mids.index(bank['id'])
    bank_layers={name:catalog.rgba_native(raw[slot*256:(slot+1)*256],palette,True)
        for name,raw in layers.items()if name in('mid','over')}
    assert set(bank_layers)=={'mid','over'}
    shore=Image.new('RGBA',(16,16))
    for name in('mid','over'):shore=Image.alpha_composite(shore,bank_layers[name])
    part=dict(donor=bank,layers=['mid','over'],layerHashes={name:sha(image.tobytes())for name,image in bank_layers.items()},
        x=0,y=0,srcX=0,srcY=0,w=16,h=16)
    composed=Image.alpha_composite(background,shore)
    protected=0;water_pixels=0
    for y in range(16):
        for x in range(16):
            s=shore.getpixel((x,y));actual=composed.getpixel((x,y))
            assert s[3]in(0,255)
            if s[3]:
                assert actual==s==original.getpixel((x,y))
                assert not(s[2]-s[0]>48 and s[2]-s[1]>8),'Blue source water must never enter the protected shore'
                protected+=1
            else:
                assert actual==background.getpixel((x,y));water_pixels+=1
    assert protected>0 and water_pixels>0 and protected+water_pixels==256
    evidence=('Route31 inward northeast shore corner at cell21,4 only. Preserve the complete existing native Emerald410 '
        'MID/OVER shore alpha and every opaque bank pixel at1:1. Its former animated Emerald surface mismatched the '
        'surrounding enclosed static FireRed pond. Use the exact adjacent Viridian430 static water beneath this intact '
        'shore, with no generated pixels or removed bank detail. The freshwater role and explicit native shore parts '
        'retain all selectable water styles. Source map, Surf/collision41, NPCs, encounters, warps and scripts stay native.')
    payload=dict(kind='native_composite',base=water,parts=[part],role='freshwater_pond_inner_northeast_corner',
        compositionPixelHash=sha(composed.tobytes()),evidence=evidence,sourceBody='enclosed inland pond')
    source_raw=(base/MODULE).read_bytes();newline=b'\r\n'if b'\r\n'in source_raw else b'\n'
    assert MARKER.encode()not in source_raw and source_raw.endswith(b'return rows'+newline)
    footer=(MARKER+'\nlocal changed=0\nfor _,row in ipairs(rows)do\n'
        "  if (row.game=='gold'or row.game=='silver'or row.game=='crystal')and row.style=='gen3'\n"
        "    and row.map=='ROUTE_31'and row.id==122 and row.quadrant==1 then\n"
        "    assert(row.donor and row.donor.game=='emerald'and row.donor.tileset=='general__petalburg'and row.donor.id==410)\n"
        '    row.donor=nil;row.animated=nil;row.animation=nil\n'
        '    local update='+lua(canonical(payload))+'\n'
        '    for key,value in pairs(update)do row[key]=value end\n'
        '    changed=changed+1\n  end\nend\nassert(changed==3,\'Route31 corner source set changed\')\n'
        '-- END ROUTE31 NATIVE STATIC POND CORNER\nreturn rows\n')
    (mod/MODULE).write_bytes(source_raw[:-len(b'return rows'+newline)]+footer.replace('\n',newline.decode()).encode())
    after=preview.read_reviewed(mod/MODULE)
    assert len(before)==len(after)
    delta=[]
    for original_row,row in zip(before,after):
        if not target(row):assert row==original_row;continue
        game=row['game'];data=review.source(cache,game);md=data['maps']['ROUTE_31']
        assert md['blocks'][(4//2)*md['width']+21//2]==122
        coords=[]
        for index,bid in enumerate(md['blocks']):
            if bid==122:coords.append([index%md['width']*2+1,index//md['width']*2])
        assert coords==row['sourceCells']==[[21,4]]
        cell=review.cell_info(cache,game,data,md['tileset'],122,1)
        assert cell['sourceHash']==row['sourceHash']and cell['collision']==row['sourceCollision']==41
        assert data['fingerprints'][md['tileset']]==row['sourceFiles']
        assert [bool(v.get('priority'))for v in cell['attributes']]==row['sourcePriority']
        assert [v.get('palette',1)for v in cell['attributes']]==row['sourcePalettes']
        assert not row.get('animated')and not row.get('animation')and row['parts']==[part]
        assert preview.replacement_image(cache,row,packed,mod).tobytes()==composed.tobytes()
        delta.append(dict(game=game,xy=[21,4],sourceHash=row['sourceHash'],sourceFiles=row['sourceFiles'],
            collision=row['sourceCollision'],original_donor=bank,water=water,shore_pixels=protected,water_pixels=water_pixels))
    registered=list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(mod/'main.lua').read_text())))
    runtime=LuaRuntime(unpack_returned_tuples=True)
    runtime.globals().paths=runtime.table_from(registered)
    runtime.globals().source=lambda name:(mod/name).read_text(encoding='utf-8-sig')
    count=runtime.execute('''local rows={}
      for _,path in ipairs(paths)do for _,r in ipairs(assert(load(source(path),'@'..path))())do rows[#rows+1]=r end end
      local M=assert(load(source('lib/mapping.lua'),'@lib/mapping.lua'))();local _,errors=M.index(rows)
      assert(#errors==0,table.concat(errors,'\\n'));return #rows''')
    checks=review.validate_batch([r for r in after if target(r)],SimpleNamespace(cache=cache,engine=a.engine,output=out),mod)
    assert checks['rows_accepted']==3 and checks['rejected']==0
    original.save(out/'corner-before.png');composed.save(out/'corner-after.png');shore.save(out/'shore-alpha.png')
    report=dict(status='passed',scope='Only Route31 cell21,4 in Gold/Silver/Crystal',rows=delta,
        registered_modules=len(registered),registered_rows=count,index_errors=0,native_validation=checks,
        every_other_expanded_terrain_row_unchanged=True,shore_RGBA_sha256=sha(shore.tobytes()),
        composition_RGBA_sha256=sha(composed.tobytes()),part=part,water=water,
        helper_sha256=sha(Path(__file__).read_bytes()),mapping_sha256=sha((mod/MODULE).read_bytes()))
    (out/'proof.json').write_text(json.dumps(canonical(report),indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k]for k in('status','registered_rows','index_errors','native_validation')}))

if __name__=='__main__':main()
