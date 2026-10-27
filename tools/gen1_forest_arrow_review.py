"""Review unchanged native arrow frames for static Gen1 forest direction cues."""
from __future__ import annotations
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sys
import zlib
from PIL import Image,ImageDraw,ImageFont
import catalog
import preview
import review
import gen1_extended_review as extended
from gen1_forest_review import MAPS
from gen1_forest_tree_review import scene
import validate_animation

ROOT=Path(__file__).resolve().parents[2]
CACHE=Path(os.environ['APPDATA'])/'pokemon-love2d'
OUT=ROOT/'.work/tileshift-gen1-forest-review'
DIRECTIONS={80:('up',0),81:('down',2),82:('left',4),83:('right',6)}
ROLES={'forest_static_direction_marker_'+d for d,_ in DIRECTIONS.values()}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write-approved-arrows',action='store_true')
    args=p.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    root=CACHE/'firered/data/generated/gba/field_effects'
    meta_bytes=(root/'arrow.meta').read_bytes();meta=catalog.read_lua(root/'arrow.meta')
    blob=(root/'arrow.rgba').read_bytes()
    if len(blob)!=8192:blob=zlib.decompress(blob)
    assert len(blob)==8192 and meta=={'w':16,'h':128,'frames':8,'fw':16,'fh':16,'indexed':False,'format':2}
    frames=[Image.frombytes('RGBA',(16,16),blob[i*1024:(i+1)*1024])for i in range(8)]
    refs=[{'game':'firered','kind':'field_effect','tileset':'arrow','id':i,
           'metaHash':catalog.sha(meta_bytes),'rgbaHash':catalog.sha(blob),'hash':catalog.sha(im.tobytes())}for i,im in enumerate(frames)]
    # Actual production neutral decoder: all eight complete frames must match
    # the imported native RGBA byte-for-byte, with no gameplay runtime load.
    sys.path.insert(0,str(ROOT/'.tools/python'));from lupa.luajit21 import LuaRuntime
    lua=LuaRuntime(unpack_returned_tuples=True,encoding=None)
    def read(relative):
        path=(CACHE/relative.decode()).resolve();assert path.is_relative_to(CACHE)
        if not path.is_file():return None
        raw=path.read_bytes()
        if path.suffix=='.rgba':
            try:return zlib.decompress(raw)
            except zlib.error:pass
        return raw
    before=Path.cwd()
    try:
        os.chdir(ROOT/'.tools/engine-0395');lua.execute(validate_animation.IMAGE_FIXTURE.encode())
        donor=lua.execute((ROOT/'TileShift/lib/donor.lua').read_bytes())[b'new'](lua.table_from({
            b'read':read,b'prefix':lambda game:game+b'/',b'newImageData':lua.globals()[b'makeData'],
            b'hash':lambda raw:catalog.sha(raw).encode()}))
        for i,ref in enumerate(refs):
            value=donor[b'cell'](donor,lua.execute(('return '+review.lua_value(ref)).encode()))
            assert not isinstance(value,tuple),value
            assert value[b'under'][b'getString'](value[b'under'])==frames[i].tobytes()
        for name in lua.eval(b'package.loaded').keys():assert not name.startswith((b'src.core.game3.',b'src.world.gen2.'))
    finally:os.chdir(before)
    native=json.loads((ROOT/'.work/tileshift-catalog/firered.json').read_text())['cells']
    native={(r['pair'],r['mid']):r for r in native};mf=catalog.read_lua(CACHE/'firered/data/generated/gba/native/manifest.lua')
    rows=[];proofs=[];counts=Counter();examples={};packed={}
    for game in ('red','blue','yellow'):
        base=CACHE/game;maps=catalog.read_lua(base/'data/generated/maps.lua')
        ts=catalog.read_lua(base/'data/generated/tilesets.lua')['FOREST'];atlas=Image.open(base/ts['image'])
        data=json.loads((ROOT/f'.work/tileshift-catalog/{game}.json').read_text())
        cells={(r['block_id'],r['quadrant']):r for r in data['cells']if r['tileset']=='FOREST'}
        files=next(t['fingerprints']for t in data['tilesets']if t['tileset']=='FOREST')
        assert catalog.sha((base/'data/generated/tilesets.lua').read_bytes())==files['metadata']
        assert catalog.sha((base/'data/generated/maps.lua').read_bytes())==files['maps']
        assert catalog.sha((base/ts['image']).read_bytes())==files['image']
        for name in MAPS:
            m=maps[name];uses=Counter((bid,q)for bid in m['blocks']for q in range(4));pair=mf['layouts']['FR_'+name]['pair']
            ground={'game':'firered','tileset':pair,'id':1,'hash':native[pair,1]['pixel_sha256']}
            for (bid,q),n in sorted(uses.items()):
                source=cells[bid,q];raw=source['tiles'];arrows=[t for t in raw if t in DIRECTIONS]
                if not arrows:continue
                assert len(arrows)==1 and all(t==48 or t in DIRECTIONS for t in raw)
                direction,frame=DIRECTIONS[arrows[0]]
                assert source['walkable_tiles']==[t in ts['walkable']for t in raw]
                assert not source['grass_tile_present']and not source['warp_tile_present']
                original=preview.native_cell(atlas,ts,ts['blocks'][bid],q)
                assert catalog.sha(original.tobytes())==source['grayscale_pixel_sha256']
                row={'game':game,'style':'gen3','tileset':'FOREST','map':name,'id':bid,'quadrant':q,
                    'role':'forest_static_direction_marker_'+direction,'status':'reviewed','sourceHash':source['grayscale_pixel_sha256'],
                    'sourceFiles':files,'kind':'native_composite','base':ground,
                    'parts':[{'donor':refs[frame],'srcX':0,'srcY':0,'w':16,'h':16,'x':0,'y':0}],
                    'evidence':'Reviewed static directional marker: exact native FireRed arrow effect frame'+str(frame)+' points '+direction+'. The original source raw'+str(arrows[0])+' cue stays static; no blinking, warp rule or effect runtime is added. Full native16px frame, including its entire outline, remains unchanged within the original16px source cell. Metadata/whole-sheet/frame fingerprints are mandatory; source raw8px walk flags, grass/warp flags and actual map use are checked. Native counterpart lawn1 is visible through the original native alpha; source collision, event/warp destinations and map geometry remain unchanged.'}
                rows.append(row);counts[game,direction]+=n
                proofs.append({'game':game,'map':name,'source':[bid,q],'raw':raw,'walkable8':source['walkable_tiles'],
                    'direction':direction,'native_frame':frame,'static':True,'occurrences':n,'native_bbox':frames[frame].getbbox()})
                if game=='red':examples.setdefault(direction,(original,row))
    def image(row):return Image.alpha_composite(preview.native_donor(CACHE,row['base'],packed),frames[row['parts'][0]['donor']['id']])
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    canvas=Image.new('RGB',(1300,690),'#18212b');d=ImageDraw.Draw(canvas)
    d.text((12,12),'STATIC FOREST DIRECTION CUES - complete native arrow frame, no resizing/clipping or animation',font=font,fill='white')
    d.text((12,40),'Source8px marker and native14px glyph both remain inside the same original16px cell. Collision and warp/event behavior are unchanged.',font=font,fill='#c4cdd8')
    for col,direction in enumerate(('up','down','left','right')):
        original,row=examples[direction];x=12+col*320;frame=row['parts'][0]['donor']['id']
        d.text((x,90),direction.upper()+' - source native cue',font=font,fill='white');canvas.paste(original.resize((128,128),Image.Resampling.NEAREST),(x,125))
        d.text((x,285),'Whole native frame'+str(frame)+' over lawn',font=font,fill='white');canvas.paste(image(row).resize((128,128),Image.Resampling.NEAREST),(x,322))
        d.multiline_text((x,470),'Native canvas16x16\nFull glyph bbox'+str(frames[frame].getbbox())+'\nSource cue stays static\nNo source cell spill or new warp',font=font,fill='white',spacing=9)
    d.text((12,638),'All8 native frames are independently byte-checked against production Donor; selected fixed frames0/2/4/6 follow native FRLG direction ordering.',font=font,fill='white')
    canvas.save(OUT/'forest-static-native-arrow-direction-footprint-review.png')
    active=[r for p in(ROOT/'TileShift/mappings').glob('*.lua')for r in preview.read_reviewed(p)if r['role']not in ROLES]
    source,current,_=scene('red','VIRIDIAN_FOREST',active,packed);candidate=current.copy()
    m=catalog.read_lua(CACHE/'red/data/generated/maps.lua')['VIRIDIAN_FOREST'];selected={(r['id'],r['quadrant']):r for r in rows if r['game']=='red'and r['map']=='VIRIDIAN_FOREST'}
    added=0
    for pos,bid in enumerate(m['blocks']):
        for q in range(4):
            row=selected.get((bid,q))
            if row:candidate.paste(image(row),(pos%m['width']*32+q%2*16,pos//m['width']*32+q//2*16));added+=1
    assert added==2
    candidate.save(OUT/'red-VIRIDIAN_FOREST-static-arrows-candidate.png')
    # Zoomed actual entrance context keeps the complete original16px scope visible.
    crop=(14*16,44*16,20*16,48*16);zoom=Image.new('RGB',(840,390),'#18212b');z=ImageDraw.Draw(zoom)
    z.text((12,12),'Actual ViridianForest south entrance: two static UP cues; original source warp anchors remain below.',font=font,fill='white')
    for col,(label,im)in enumerate((('Current source markers',current),('Complete native static frames',candidate))):
        x=12+col*410;z.text((x,55),label,font=font,fill='white');zoom.paste(im.crop(crop).resize((384,256),Image.Resampling.NEAREST),(x,90))
    zoom.save(OUT/'viridian-forest-arrow-actual-entrance-context.png')
    (OUT/'forest-arrow-candidates.lua').write_text('return '+review.lua_value(rows)+'\n',encoding='utf-8')
    (OUT/'forest-arrow-native-proof.json').write_text(json.dumps({'status':'private_visual_review_required','rows':len(rows),
        'metadata':meta,'metadata_file_sha256':catalog.sha(meta_bytes),'whole_rgba_sheet_sha256':catalog.sha(blob),
        'all8_native_frames_byte_identical':True,'native_frame_refs':refs,'native_gameplay_modules_loaded':False,
        'direction_order_reference':'src/core/game3/warp_arrow.lua FRLG_ANIMS: up0/1,down2/3,left4/5,right6/7',
        'counts':{game:{d:counts[game,d]for d,_ in DIRECTIONS.values()}for game in('red','blue','yellow')},'source_proofs':proofs},indent=2))
    if args.write_approved_arrows:
        retained=[r for r in preview.read_reviewed(extended.TARGET)if r['role']not in ROLES];extended.write_groups(retained+rows)
    print(json.dumps({'rows':len(rows),'source_cues_per_cart':sum(counts['red',d]for d,_ in DIRECTIONS.values()),
                      'all8_native_frames_match':True,'production_written':args.write_approved_arrows},indent=2))


if __name__=='__main__':main()
