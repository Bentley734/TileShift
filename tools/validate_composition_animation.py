"""Verify native animated composition bases and published Session frames.

Uses actual imports and the production decoder/compositor/session. Independent
Pillow source-over composition checks every output pixel, then the native GBA
animator checks each selected base across129 ticks. No game/save/import writes.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys
import zlib
from PIL import Image
import catalog
import preview
import review
import validate_animation

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'.tools/python'))
from lupa.luajit21 import LuaRuntime


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mapping',required=True,type=Path)
    parser.add_argument('--output',type=Path,default=ROOT/'.work/tileshift-special-buildings/fanclub-composite-animation-proof.json')
    parser.add_argument('--prototype-prefix',type=Path,help='Optional whole-building frame PNG prefix, followed by0..7.png')
    args=parser.parse_args();path=args.mapping.resolve();mod=ROOT/'TileShift'
    prototype_prefix=args.prototype_prefix.resolve()if args.prototype_prefix else None
    all_rows=preview.read_reviewed(path)
    rows=[r for r in all_rows if r.get('parts')and r.get('animated')]
    assert rows,'No animated native compositions in selected mappings'
    contexts={(r['game'],r['tileset'],r.get('map'))for r in rows}
    all_rows=[r for r in all_rows if(r['game'],r['tileset'],r.get('map'))in contexts]
    cache=Path(os.environ['APPDATA'])/'pokemon-love2d';lua=LuaRuntime(unpack_returned_tuples=True,encoding=None)
    def read(relative):
        file=(cache/relative.decode()).resolve();assert file.is_relative_to(cache)
        if not file.is_file():return None
        raw=file.read_bytes()
        if file.suffix in ('.idx','.rgba'):
            try:return zlib.decompress(raw)
            except zlib.error:pass
        return raw
    def image(relative,_bytes):
        im=Image.open(cache/relative.decode()).convert('RGBA')
        return lua.globals()[b'makeData'](im.width,im.height,b'rgba8',im.tobytes())
    def sha(raw):return hashlib.sha256(raw).hexdigest()
    def checked(value):
        assert not isinstance(value,tuple),value
        return value
    before=Path.cwd();proofs=[];packed={};bases={};pixel_checks=static_checks=whole_checks=0;whole_hashes={}
    try:
        os.chdir(ROOT/'.tools/engine-0395');lua.execute(validate_animation.IMAGE_FIXTURE.encode())
        ctx=lua.table_from({b'read':read,b'prefix':lambda game:game+b'/',b'hash':lambda raw:sha(raw).encode(),
                            b'newImageData':lua.globals()[b'makeData'],b'loadImage':image})
        donor=lua.execute((mod/'lib/donor.lua').read_bytes())[b'new'](ctx)
        composer=lua.execute((mod/'lib/composition.lua').read_bytes())[b'new'](lua.table_from({
            b'donor':donor,b'newImageData':lua.globals()[b'makeData'],
            b'hashImage':lambda im:sha(im[b'getString'](im)).encode()}))
        lua.globals()[b'animationRows']=lua.execute(('return '+review.lua_value(rows)).encode())
        lua.globals()[b'compositionRows']=lua.execute(('return '+review.lua_value(all_rows)).encode())
        lua.globals()[b'animationRead']=read;lua.globals()[b'animationDonor']=donor;lua.globals()[b'animationComposer']=composer
        lua.globals()[b'animationMapping']=lua.execute((mod/'lib/mapping.lua').read_bytes())
        lua.globals()[b'animationSession']=lua.execute((mod/'lib/session.lua').read_bytes())
        session=lua.execute(br'''
local indexed,errors=animationMapping.index(compositionRows);assert(#errors==0,table.concat(errors,'\n'))
local state=animationSession.new({mappings=indexed,donor=animationDonor,newImageData=makeData,
 generations=animationMapping.generations,validate=animationMapping.validate,
 compose=function(row)return animationComposer:cell(row)end,
 composeFrames=function(row)return animationComposer:frames(row)end,
 warn=function(message)error(message)end})
state:select('gen3')
local definitions,records,allRecords={},{},{}
local function blockFor(row)
 if not definitions[row.game]then
  definitions[row.game]=assert(require('src.core.SaveSerializer').decode(
   assert(animationRead(row.game..'/data/generated/maps.lua')),
   {allowArray=true,allowComments=true,maxBytes=16*1024*1024,maxDepth=64,maxNodes=2000000,
    maxStringBytes=8*1024*1024,maxTableEntries=500000}))
 end
 local original=assert(definitions[row.game][row.map]);local def={}
 for key,value in pairs(original)do def[key]=value end;def.id=row.map
 local snapshot=require('src.link.Json').encode(def)
 local block=assert(state:replacements(row.game,row.tileset,def)[row.id])
 if row.x~=nil then block=assert(block.positions[math.floor(row.x/2)..':'..math.floor(row.y/2)])end
 assert(block.coverage[row.quadrant],'Native composition was not published')
 assert(require('src.link.Json').encode(def)==snapshot,'Session changed native source definition')
 return block
end
for i,row in ipairs(compositionRows)do allRecords[i]=blockFor(row)end
for i,row in ipairs(animationRows)do
 records[i]=blockFor(row);assert(records[i].frames,'Animated composition has no frames')
end
assert(state.accepted==#compositionRows and state.rejected==0,'Actual Session rejected native compositions')
return {records=records,allRecords=allRecords,accepted=state.accepted,rejected=state.rejected}
''')
        for i,row in enumerate(rows,1):
            lua_row=lua.globals()[b'animationRows'][i]
            sequence=checked(composer[b'frames'](composer,lua_row));n=len(sequence[b'frames'])
            assert n==8 and sequence[b'ticks']==16 and sequence[b'phase']==1
            base_frames=preview.native_water_frames(cache,{'donor':row['base'],'animated':True,'animation':row['animation']},packed)
            assert len(base_frames)==n
            overlay=Image.new('RGBA',(16,16))
            for part in row['parts']:
                native=preview.native_donor(cache,part['donor'],packed,part.get('layers'),part.get('layerHashes'))
                sx,sy=part.get('srcX',0),part.get('srcY',0)
                overlay.alpha_composite(native.crop((sx,sy,sx+part['w'],sy+part['h'])),(part.get('x',0),part.get('y',0)))
            block=session[b'records'][i];assert len(block[b'frames'])==n
            output=[];qx,qy=row['quadrant']%2*16,row['quadrant']//2*16
            for frame in range(n):
                expected=Image.alpha_composite(base_frames[frame],overlay)
                piece=sequence[b'frames'][frame+1];actual=piece[b'under'][b'getString'](piece[b'under'])
                assert actual==expected.tobytes(),f'Independent native composition disagrees: row{i},frame{frame}'
                published=block[b'frames'][frame+1];raw=published[b'getString'](published)
                published=Image.frombytes('RGBA',(32,32),raw).crop((qx,qy,qx+16,qy+16))
                assert published.tobytes()==expected.tobytes(),f'Session frame disagrees: row{i},frame{frame}'
                output.append(expected);pixel_checks+=512
            opaque=exposed=changing=0
            for y in range(16):
                for x in range(16):
                    colors={im.getpixel((x,y))for im in output};alpha=overlay.getpixel((x,y))[3]
                    if alpha==255:assert len(colors)==1;opaque+=1
                    else:
                        exposed+=1;changing+=len(colors)>1
            assert exposed>0,'Solid static facade must not require an animated base'
            proofs.append({'game':row['game'],'map':row.get('map'),'source':[row['id'],row['quadrant']],
                'position':[row.get('x'),row.get('y')],'frames':n,'native_opaque_roof_pixels_static':opaque,
                'exposed_native_base_pixels':exposed,'visible_water_pixels_changing':changing,
                'frame_rgba_sha256':[sha(im.tobytes())for im in output]})
            key=json.dumps({'base':row['base'],'animation':row['animation']},sort_keys=True)
            bases[key]=(lua_row[b'base'],lua_row[b'animation'])
        for i,row in enumerate(all_rows,1):
            if row.get('animated'):continue
            block=session[b'allRecords'][i];frames=block[b'frames']
            expected=preview.replacement_image(cache,row,packed,mod)
            qx,qy=row['quadrant']%2*16,row['quadrant']//2*16
            for frame in range(len(frames)if frames is not None else 1):
                image=frames[frame+1]if frames is not None else block[b'image']
                raw=image[b'getString'](image)
                actual=Image.frombytes('RGBA',(32,32),raw).crop((qx,qy,qx+16,qy+16))
                assert actual.tobytes()==expected.tobytes(),'Static neighboring facade changed inside animated block'
                static_checks+=256
        if prototype_prefix:
            prefix=prototype_prefix
            for game in sorted({r['game']for r in all_rows}):
                selected=[(i,r)for i,r in enumerate(all_rows,1)if r['game']==game]
                assert all('x'in r and 'y'in r for _,r in selected)
                minx,miny=min(r['x']for _,r in selected),min(r['y']for _,r in selected)
                width=max(r['x']for _,r in selected)-minx+1;height=max(r['y']for _,r in selected)-miny+1
                hashes=[]
                for frame in range(8):
                    scene=Image.new('RGBA',(width*16,height*16))
                    for i,r in selected:
                        block=session[b'allRecords'][i];frames=block[b'frames']
                        image=frames[frame+1]if frames is not None else block[b'image']
                        raw=image[b'getString'](image);qx,qy=r['quadrant']%2*16,r['quadrant']//2*16
                        cell=Image.frombytes('RGBA',(32,32),raw).crop((qx,qy,qx+16,qy+16))
                        scene.paste(cell,((r['x']-minx)*16,(r['y']-miny)*16))
                    expected=Image.open(str(prefix)+str(frame)+'.png').convert('RGBA')
                    assert scene.size==expected.size and scene.tobytes()==expected.tobytes(),f'Whole native building frame changed:{game},frame{frame}'
                    hashes.append(sha(scene.tobytes()));whole_checks+=scene.width*scene.height
                whole_hashes[game]=hashes
        assert sum(p['visible_water_pixels_changing']for p in proofs)>0,'Native water was frozen beneath exposed roof corners'
        for name in lua.eval(b'package.loaded').keys():
            assert not name.startswith((b'src.core.game3.',b'src.world.gen2.')),'Neutral composition imported gameplay runtime'
        snapshots=0
        for ref,spec in bases.values():
            lua.globals()[b'base']=checked(donor[b'cell'](donor,ref))
            lua.globals()[b'sequence']=checked(donor[b'frames'](donor,ref,spec))
            lua.globals()[b'selectedGame']=ref[b'game'];lua.globals()[b'selectedPair']=ref[b'tileset'];lua.globals()[b'selectedMid']=ref[b'id']
            lua.globals()[b'readImported']=read
            snapshots+=lua.execute(validate_animation.COMPARE.encode())
        accepted,rejected=session[b'accepted'],session[b'rejected']
    finally:os.chdir(before)
    report={'status':'passed','mapping':str(path),'mapping_sha256':sha(path.read_bytes()),
       'animated_composite_rows':len(rows),'accepted':accepted,'rejected':rejected,
       'independent_composition_and_session_pixels_checked':pixel_checks,'native_animation_layer_snapshots':snapshots,
       'static_neighboring_facade_pixels_checked':static_checks,'whole_prototype_pixels_checked':whole_checks,
       'whole_building_frame_hashes':whole_hashes,
       'native_water_banks_checked':len(bases),'native_animation_ticks':129,
       'source_definition_unchanged':True,'source_imports_read_only':True,
       'runtime_modules':{file:sha((mod/file).read_bytes())for file in('main.lua','lib/mapping.lua','lib/composition.lua','lib/session.lua','lib/donor.lua')},
       'rows':proofs}
    args.output.resolve().parent.mkdir(parents=True,exist_ok=True);args.output.resolve().write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items()if k not in('rows','runtime_modules')},indent=2))


if __name__=='__main__':main()
