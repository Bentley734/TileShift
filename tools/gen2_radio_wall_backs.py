"""Match all reviewed CrystalDust radio headers to their actual room walls.

Only the transparent header background changes. The native antenna/radio pixels,
lower radio cells, source metadata, actors and interactions remain unchanged.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
W = next(p for p in Path(__file__).resolve().parents if (p / '.tools/python').is_dir())
sys.path.insert(0, str(W / '.tools/python'))
from PIL import Image, ImageDraw

TARGETS = {'VIOLET_NICKNAME_SPEECH_HOUSE':2, 'VIOLET_KYLES_HOUSE':2,
           'ECRUTEAK_ITEMFINDER_HOUSE':2, 'ECRUTEAK_LUGIA_SPEECH_HOUSE':2,
           'KURTS_HOUSE':6, 'MAHOGANY_MART_1F':0, 'MOUNT_MOON_GIFT_SHOP':0}
MODULE = 'mappings/johto_domestic_finish.lua'
HEAD = '163baf529e26334e733c3257a1213edc955641eb9aa1f4f4da44b715746b308b'
GUARDS = ('game','style','map','tileset','id','quadrant','x','y','sourceCells','sourceHash',
          'sourceFiles','sourceCollision','sourcePriority','sourcePalettes','sourceWarps')
sha = lambda raw:hashlib.sha256(raw).hexdigest()


def canonical(value):
    if isinstance(value,dict):return {k:canonical(v) for k,v in sorted(value.items())}
    if isinstance(value,list):return [canonical(v) for v in value]
    return value


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',required=True,type=Path)
    p.add_argument('--mod-root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--engine',type=Path,default=W/'.work/tileshift-engine-0420')
    a=p.parse_args();base,mod,out=a.baseline.resolve(),a.mod_root.resolve(),a.output.resolve()
    assert base!=mod and out not in (base,mod)
    sys.path.insert(0,str(mod/'tools'))
    import catalog,preview,gen2_extended_review as review
    from newbark_building_review import lua
    cache=Path(os.environ['APPDATA'])/'pokemon-love2d';out.mkdir(parents=True,exist_ok=True)
    paths=list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(base/'main.lua').read_text())))
    catalog.LUA.globals().paths=catalog.LUA.table_from(paths)
    catalog.LUA.globals().source=lambda name:(base/name).read_text(encoding='utf-8-sig')
    catalog.LUA.globals().targets=catalog.LUA.table_from({name:True for name in TARGETS})
    selected=catalog.plain(catalog.LUA.execute('''local selected={}
      for _,p in ipairs(paths)do for _,r in ipairs(assert(load(source(p)))())do
       if (r.game=='gold'or r.game=='silver'or r.game=='crystal')and r.style=='gen3'and(not r.map or targets[r.map])then
        selected[#selected+1]=r
       end
      end end return selected'''))
    before=preview.read_reviewed(base/MODULE);packed={};changes=[];updates={};new_rows=[];validated_rows=[];images=[]
    for game in ('gold','silver','crystal'):
        data=review.source(cache,game)
        for name,x in TARGETS.items():
            md=data['maps'][name]
            candidates=[r for r in selected if r['game']==game and r['tileset']==md['tileset']]
            def at(xx,yy):
                bid=md['blocks'][yy//2*md['width']+xx//2];q=yy%2*2+xx%2
                rows=[r for r in candidates if r['id']==bid and r['quadrant']==q
                      and (not r.get('map') or r['map']==name)
                      and ('x'not in r or (r['x'],r['y'])==(xx,yy))]
                return max(rows,key=lambda r:(int('x'in r),int(bool(r.get('map')))))
            old=at(x,0)
            assert old['sourceCells']==[[x,0]] and old['sourceHash']==HEAD and old['sourceCollision']==7
            assert old['kind']=='third_party' and old['asset'].endswith('/domestic-radio-0-0.png')
            walls=[]
            for xx in range(md['width']*2):
                row=at(xx,0)
                if xx!=x and row['sourceHash']==HEAD and row['sourceCollision']==7 and 'wall'in row['role']:
                    walls.append((abs(xx-x),xx,row))
            assert walls
            _,wall_x,wall=min(walls,key=lambda v:(v[0],v[1]))
            assert wall['kind']=='native' and not wall.get('parts') and not wall.get('artOverlay')
            assert wall['donor']['game']=='firered' and wall['donor']['tileset']=='pewter_gym' and wall['donor']['id']==705
            wall_image=preview.replacement_image(cache,wall,packed,base)
            radio=Image.open(mod/old['asset']).convert('RGBA')
            assert sha((mod/old['asset']).read_bytes())==old['assetFileHash']
            assert radio.size==(16,16) and set(radio.getchannel('A').get_flattened_data())<={0,255}
            row=copy.deepcopy(old);changed=row['base']!=wall['donor'];row['base']=copy.deepcopy(wall['donor'])
            if changed:
                row['evidence']='Complete native CrystalDust radio and stand, with transparent header pixels backed by this room\'s exact adjacent native plain-wall counterpart. Every native antenna/radio pixel, the lower radio cell, original source collision, actors, interactions, palettes, priorities and warps stay unchanged.'
            result=preview.replacement_image(cache,row,packed,mod)
            old_image=preview.replacement_image(cache,old,packed,base)
            for native,new,background in zip(radio.get_flattened_data(),result.get_flattened_data(),wall_image.get_flattened_data()):
                assert new==(native if native[3] else background)
            assert all(old.get(k)==row.get(k) for k in GUARDS)
            row['compositionPixelHash']=sha(result.tobytes())
            validated_rows.append(row)
            if changed:
                assert name!='MOUNT_MOON_GIFT_SHOP' and old in before
                updates.setdefault(game,{})[name]={str(old['id'])+':'+str(old['quadrant']):row};new_rows.append(row)
            else:assert name=='MOUNT_MOON_GIFT_SHOP' and row==old
            path=out/f'{game}-{name}-header-before-after-wall.png'
            proof=Image.new('RGBA',(16*3,16));proof.paste(old_image,(0,0));proof.paste(result,(16,0));proof.paste(wall_image,(32,0));proof.save(path)
            changes.append(dict(game=game,map=name,xy=[x,0],changed=changed,reference_wall_xy=[wall_x,0],
                reference_wall=wall['donor'],old_base=old['base'],new_base=row['base'],
                native_radio_asset=old['asset'],native_radio_png_sha256=old['assetFileHash'],
                foreground_opaque_pixels_exact=True,all_transparent_pixels_equal_adjacent_wall=True,
                compositionPixelHash=row['compositionPixelHash'],proof_image=str(path)))
            if game=='crystal':images.append((name,changed,old_image,result,wall_image))
    assert len(changes)==21 and len(new_rows)==18
    raw=(base/MODULE).read_bytes();newline=b'\r\n'if raw.endswith(b'\r\n')else b'\n';ending=b'return rows'+newline
    marker='-- BEGIN MATCHED NATIVE RADIO WALLS';assert marker.encode()not in raw and raw.endswith(ending)
    footer=marker+'\nlocal updates='+lua(canonical(updates))+'''\nlocal changed=0
for index,row in ipairs(rows)do
 local game=updates[row.game];local map=game and game[row.map]
 local replacement=row.style=='gen3'and map and map[tostring(row.id)..':'..tostring(row.quadrant)]
 if replacement then rows[index]=replacement;changed=changed+1 end
end
assert(changed==18,'Native radio header source set changed')
-- END MATCHED NATIVE RADIO WALLS
return rows
'''
    (mod/MODULE).write_bytes(raw[:-len(ending)]+footer.replace('\n',newline.decode()).encode())
    after=preview.read_reviewed(mod/MODULE);assert len(before)==len(after)
    assert sum(a!=b for a,b in zip(before,after))==18
    for old,new in zip(before,after):
        assert old==new or all(old.get(k)==new.get(k) for k in GUARDS)
    catalog.LUA.globals().source=lambda name:(mod/name).read_text(encoding='utf-8-sig')
    total=catalog.LUA.execute('''local rows={}
      for _,p in ipairs(paths)do for _,r in ipairs(assert(load(source(p)))())do rows[#rows+1]=r end end
      local Mapping=assert(load(source('lib/mapping.lua')))();local _,errors=Mapping.index(rows)
      assert(#errors==0,table.concat(errors,'\\n'));return #rows''')
    validation=review.validate_batch(validated_rows,SimpleNamespace(cache=cache,engine=a.engine,output=out),mod)
    assert validation['rows_accepted']==21 and validation['rejected']==0
    sheet=Image.new('RGBA',(580,len(images)*96+30),(24,32,40,255));draw=ImageDraw.Draw(sheet)
    draw.text((8,6),'Native composites: before / corrected / adjacent plain wall',fill='white')
    for i,(name,changed,old,new,wall) in enumerate(images):
        yy=i*96+30;draw.text((8,yy),name+(' (already matched)'if not changed else''),fill='white')
        for n,image in enumerate((old,new,wall)):
            sheet.alpha_composite(image.resize((64,64),Image.Resampling.NEAREST),(8+n*80,yy+18))
    sheet.save(out/'radio-header-native-comparisons.png')
    proof=dict(status='passed',headers_checked=21,headers_corrected=18,already_correct_mount_moon_headers=3,
        changed_rows=18,changed_maps=[n for n in TARGETS if n!='MOUNT_MOON_GIFT_SHOP'],
        lower_radio_rows_unchanged=True,all_other_domestic_rows_unchanged=True,
        all_native_opaque_radio_pixels_unchanged=True,all_transparent_header_pixels_match_actual_plain_wall=True,
        source_guards_unchanged=list(GUARDS),no_assets_or_runtime_API_changes=True,
        changes=changes,registered_rows=total,index_errors=0,native_validation=validation,
        mapping_sha256=sha((mod/MODULE).read_bytes()),helper_sha256=sha(Path(__file__).read_bytes()))
    (out/'proof.json').write_text(json.dumps(canonical(proof),indent=2)+'\n')
    print(json.dumps({k:proof[k] for k in ('status','headers_checked','headers_corrected','registered_rows','index_errors')}))


if __name__=='__main__':main()
