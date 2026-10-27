"""Review Mt. Moon's fixed dense rock fill separately from switch barriers."""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import zlib
from PIL import Image,ImageDraw,ImageFont
import catalog
import preview
import review
import gen1_extended_review as extended
from gen1_cave_joins_review import render_map
from building_review import decode_layout

ROOT=Path(__file__).resolve().parents[2]
CACHE=Path(catalog.os.environ['APPDATA'])/'pokemon-love2d'
OUT=ROOT/'.work/tileshift-gen1-cave-joins-review'
ROLE='cave_mtmoon_fixed_bedrock_fill'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-approved-fill',action='store_true')
    args=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    active=[r for file in(ROOT/'TileShift/mappings').glob('*.lua')for r in preview.read_reviewed(file)if r['role']!=ROLE]
    native=CACHE/'firered/data/generated/gba/native';manifest=catalog.read_lua(native/'manifest.lua')
    spec=manifest['layouts']['FR_MT_MOON_B2F'];pair=spec['pair'];layout=decode_layout(native/spec['file'])
    records=json.loads((ROOT/'.work/tileshift-catalog/firered.json').read_text())['cells']
    records={r['mid']:r for r in records if r['pair']==pair}
    def ref(mid):return {'game':'firered','tileset':pair,'id':mid,'hash':records[mid]['pixel_sha256']}
    positions=[(i%layout['width'],i//layout['width'])for i,v in enumerate(layout['mids'])if v==718]
    raw=(native/spec['file']).read_bytes()
    if raw[:4]!=b'SVML':raw=zlib.decompress(raw)
    offset=16+raw[14]*raw[15]*2
    collision=sorted({raw[offset+(y*layout['width']+x)*4+2]for x,y in positions})
    assert positions and collision==[7]
    assert all(layout['mids'][x]==718 for x in range(40)),'Native718 is the actual fixed outer bedrock border'
    rows=[];source_proofs=[];packed={}
    for game in ('red','blue','yellow'):
        data=json.loads((ROOT/f'.work/tileshift-catalog/{game}.json').read_text())
        cells={(r['block_id'],r['quadrant']):r for r in data['cells']if r['tileset']=='CAVERN'}
        files=next(t['fingerprints']for t in data['tilesets']if t['tileset']=='CAVERN')
        m=catalog.read_lua(CACHE/game/'data/generated/maps.lua')['MT_MOON_B2F']
        used=Counter((bid,q)for bid in m['blocks']for q in range(4))
        aliases=[(bid,q)for bid,q in sorted(used)if cells[bid,q]['tiles']==[6,39,36,1]]
        assert {bid for bid,q in aliases}=={47,51,56,71,74,75}
        count=sum(used[key]for key in aliases)
        assert count==148
        for bid,q in aliases:
            source=cells[bid,q]
            assert source['tiles']==[6,39,36,1]and source['walkable_tiles']==[False]*4
            assert not source['warp_tile_present']and not source['grass_tile_present']
            rows.append({'game':game,'style':'gen3','tileset':'CAVERN','map':'MT_MOON_B2F','id':bid,'quadrant':q,
                'role':ROLE,'status':'reviewed','sourceHash':source['grayscale_pixel_sha256'],'sourceFiles':files,
                'donor':ref(718),'nativeContext':{'map':'FR_MT_MOON_B2F','pair':pair,'normalizedCollision':7},
                'evidence':'Reviewed fixed dense bedrock fill in actual MtMoonB2F: whole sourceblock47 and the exact half-block boundary aliases51/56/71/74/75 repeat the same fully blocked16px material. This map has148 initial uses, no grass/warp material and no VictoryRoad switch barrier script. Complete native regional718 is the actual blocked outer rock border on the corresponding FRMtMoonB2F; all native placements have normalized collision7. Source37/55 VictoryRoad barrier occurrences are explicitly excluded despite shared source pixels. Original cave paths, collision, source scripts and switch states remain unchanged.'})
        source_proofs.append({'game':game,'map':'MT_MOON_B2F','source_aliases':aliases,
                              'occurrences':count,'raw':[6,39,36,1],'walkable8':[False]*4,'warp':False})
    catalogs={g:json.loads((ROOT/f'.work/tileshift-catalog/{g}.json').read_text())for g in ('red','blue','yellow','firered')}
    assert preview.verify(rows,CACHE,catalogs,ROOT/'TileShift')==len(rows)
    before,current,current_count=render_map('red','MT_MOON_B2F',active,packed)
    _,candidate,candidate_count=render_map('red','MT_MOON_B2F',active+rows,packed)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17)
    canvas=Image.new('RGB',(before.width*3+64,before.height+205),'#18212b');draw=ImageDraw.Draw(canvas)
    draw.text((12,12),'MT MOON B2F - fixed dense bedrock fill; actual source map and native same-region outer border718',font=font,fill='white')
    draw.text((12,40),'Only actual MtMoon fixed-fill aliases47/51/56/71/74/75, all8px blocked/no warp. Victory Road switch barriers37/55 keep their separate models.',font=font,fill='#c4cdd8')
    for col,(label,image)in enumerate((('Original source',before),('Current reviewed stage',current),('Candidate: complete fixed native718',candidate))):
        x=16+col*(before.width+16);draw.text((x,77),label,font=font,fill='white');canvas.paste(image,(x,108))
    draw.text((12,before.height+125),f'Current{current_count}/{before.width*before.height//256}; candidate{candidate_count}/{before.width*before.height//256}. All148 original fill cells use the complete native16px bedrock texture.',font=font,fill='white')
    draw.text((12,before.height+155),'This is fixed impassable rock mass, not a separate movable boulder, fall hole or event-controlled switch barrier.',font=font,fill='white')
    canvas.save(OUT/'mtmoon-fixed-bedrock-full-map-review.png');candidate.save(OUT/'red-MT_MOON_B2F-fixed-bedrock-candidate.png')
    contact=Image.new('RGB',(1250,520),'#18212b');d=ImageDraw.Draw(contact)
    d.text((12,12),'MtMoon fixed fill: source47 and corresponding native718 border; isolated rock642 is shown for role comparison',font=font,fill='white')
    ts=catalog.read_lua(CACHE/'red/data/generated/tilesets.lua')['CAVERN'];sheet=Image.open(CACHE/'red'/ts['image'])
    for col,(label,image)in enumerate((('Source47:0 fixed rock fill',preview.native_cell(sheet,ts,ts['blocks'][47],0)),
                                      ('Native718 fixed bedrock face',preview.native_donor(CACHE,ref(718),packed)),
                                      ('Native642 individual rock',preview.native_donor(CACHE,ref(642),packed)))):
        x=12+col*270;d.text((x,70),label,font=font,fill='white');contact.paste(image.resize((128,128),Image.Resampling.NEAREST),(x,105))
    # Actual remake top-edge context, including its rock face/raised-plane border.
    nx,ny=20,0;context=Image.new('RGBA',(96,64))
    for dy in range(4):
        for dx in range(6):
            mid=layout['mids'][(ny+dy)*layout['width']+nx+dx]
            context.paste(preview.native_donor(CACHE,ref(mid),packed),(dx*16,dy*16))
    contact.paste(context.resize((384,256),Image.Resampling.NEAREST),(840,92))
    d.multiline_text((12,290),'Source actual148 cells/cart: raw[6,39;36,1], all blocked, no grass/warp.\nNative718 actual162 cells on corresponding MtMoonB2F: all normalizedCOLL7(blocked).\nNative718 forms long outer-border runs and impassable solid rock mass.\nIndividual rock642/cluster643 and switch775/791 have separate source roles.',font=font,fill='white',spacing=12)
    d.text((840,365),'Actual FR_MT_MOON_B2F(20,0)',font=font,fill='white')
    contact.save(OUT/'mtmoon-fixed-bedrock-source-native-context-review.png')
    (OUT/'mtmoon-fixed-bedrock-candidates.lua').write_text('return '+review.lua_value(rows)+'\n',encoding='utf-8')
    (OUT/'mtmoon-fixed-bedrock-proof.json').write_text(json.dumps({'status':'private_visual_review_required','rows':len(rows),
       'native_donor':ref(718),'native_context_map':'FR_MT_MOON_B2F','native_positions':positions,
       'native_collision_values':collision,'source_proofs':source_proofs,'candidate_coverage':[candidate_count,before.width*before.height//256]},indent=2))
    if args.write_approved_fill:
        retained=[r for r in preview.read_reviewed(extended.TARGET)if r['role']!=ROLE]
        extended.write_groups(retained+rows)
    print(json.dumps({'rows':len(rows),'native718_placements':len(positions),'native_collision':collision,
                     'candidate_coverage':[candidate_count,before.width*before.height//256],
                     'production_written':args.write_approved_fill},indent=2))


if __name__=='__main__':main()
