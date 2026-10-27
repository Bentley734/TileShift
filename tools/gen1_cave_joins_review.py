"""Review remaining connected cave corners at their exact source positions."""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import catalog
import cave_review
import preview
import review
import gen1_extended_review as extended

ROOT=Path(__file__).resolve().parents[2]
CACHE=Path(catalog.os.environ['APPDATA'])/'pokemon-love2d'
OUT=ROOT/'.work/tileshift-gen1-cave-joins-review'
ROLES={'cave_connected_mass_'+str(q)+'_corner'for q in range(4)}
CORNER_MIDS=(648,650,664,666)
EXPECTED_WALK=([False,False,False,True],[False,False,True,False],
               [False,True,False,False],[True,False,False,False])


def indices(rows,game,name):
    selected={};positioned={}
    for r in sorted(rows,key=lambda r:bool(r.get('map'))):
        if r['game']==game and r['tileset']=='CAVERN'and r.get('map',name)==name:
            if 'x'in r:positioned[r['id'],r['quadrant'],r['x'],r['y']]=r
            else:selected[r['id'],r['quadrant']]=r
    return selected,positioned


def render_map(game,name,rows,packed):
    root=CACHE/game;maps=catalog.read_lua(root/'data/generated/maps.lua');m=maps[name]
    ts=catalog.read_lua(root/'data/generated/tilesets.lua')['CAVERN'];sheet=Image.open(root/ts['image'])
    selected,positioned=indices(rows,game,name)
    source=Image.new('RGBA',(m['width']*32,m['height']*32));after=source.copy();covered=0
    for pos,bid in enumerate(m['blocks']):
        for q in range(4):
            x,y=pos%m['width']*2+q%2,pos//m['width']*2+q//2
            original=preview.native_cell(sheet,ts,ts['blocks'][bid],q);source.paste(original,(x*16,y*16))
            row=positioned.get((bid,q,x,y),selected.get((bid,q)))
            after.paste(preview.replacement_image(CACHE,row,packed,ROOT/'TileShift')if row else original,(x*16,y*16))
            covered+=bool(row)
    return source,after,covered


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--write-approved-corners',action='store_true')
    args=p.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    active=[r for file in(ROOT/'TileShift/mappings').glob('*.lua')for r in preview.read_reviewed(file)if r['role']not in ROLES]
    records=json.loads((ROOT/'.work/tileshift-catalog/firered.json').read_text())['cells']
    records={(r['pair'],r['mid']):r for r in records}
    manifest=catalog.read_lua(CACHE/'firered/data/generated/gba/native/manifest.lua')
    rows=[];proofs=[];packed={};examples={}
    for game in ('red','blue','yellow'):
        root=CACHE/game;maps=catalog.read_lua(root/'data/generated/maps.lua')
        ts=catalog.read_lua(root/'data/generated/tilesets.lua')['CAVERN'];sheet=Image.open(root/ts['image'])
        data=json.loads((ROOT/f'.work/tileshift-catalog/{game}.json').read_text())
        cells={(r['block_id'],r['quadrant']):r for r in data['cells']if r['tileset']=='CAVERN'}
        files=next(t['fingerprints']for t in data['tilesets']if t['tileset']=='CAVERN')
        for name,m in maps.items():
            if not isinstance(m,dict)or m.get('tileset')!='CAVERN':continue
            pair=manifest['layouts'][cave_review.counterpart(name)]['pair']
            selected,positioned=indices(active,game,name)
            def ref(mid):return {'game':'firered','tileset':pair,'id':mid,'hash':records[pair,mid]['pixel_sha256']}
            for pos,bid in enumerate(m['blocks']):
                for q in range(4):
                    x,y=pos%m['width']*2+q%2,pos//m['width']*2+q//2
                    if(bid,q)in selected or(bid,q,x,y)in positioned:continue
                    source=cells[bid,q]
                    for seedq,mid in enumerate(CORNER_MIDS):
                        seed=cells[2,seedq]
                        if source['tiles']!=seed['tiles']or source['grayscale_pixel_sha256']!=seed['grayscale_pixel_sha256']or review.behavior_key(source)!=review.behavior_key(seed):continue
                        assert bid!=2,'Actual complete source32px profile must remain separately mapped'
                        assert source['walkable_tiles']==EXPECTED_WALK[seedq]
                        assert not source['grass_tile_present']and not source['warp_tile_present']
                        assert source['tiles'][3-seedq]==5
                        inside_x,inside_y=(8 if seedq%2==0 else 0),(8 if seedq//2==0 else 0)
                        row={'game':game,'style':'gen3','tileset':'CAVERN','map':name,'id':bid,'quadrant':q,'x':x,'y':y,
                             'role':'cave_connected_mass_'+str(seedq)+'_corner','status':'reviewed',
                             'sourceHash':source['grayscale_pixel_sha256'],'sourceFiles':files,'kind':'native_composite',
                             'parts':[{'donor':ref(mid),'srcX':0,'srcY':0,'w':16,'h':16,'x':0,'y':0},
                                      {'donor':ref(657),'srcX':seedq%2*8,'srcY':seedq//2*8,'w':8,'h':8,'x':inside_x,'y':inside_y}],
                             'evidence':'Reviewed connected raised-mass corner at its actual source occurrence. Exact four source8px materials and all walk/grass/warp flags match the oriented corner. Full native regional outer-corner16 is retained with native657 only in the exact original8x8 flat tile5 quadrant. The original standing plane remains8px wide; no full32px profile or neighboring cell is inferred. Original cave geometry, collision, events and warp anchors remain source-owned.'}
                        image=preview.replacement_image(CACHE,row,packed,ROOT/'TileShift')
                        plane=preview.native_donor(CACHE,ref(657),packed)
                        assert image.crop((inside_x,inside_y,inside_x+8,inside_y+8)).tobytes()==plane.crop((seedq%2*8,seedq//2*8,seedq%2*8+8,seedq//2*8+8)).tobytes()
                        row['compositionPixelHash']=catalog.sha(image.tobytes());rows.append(row)
                        proof={'game':game,'map':name,'cell':[x,y],'source':[bid,q],'corner':seedq,'raw':source['tiles'],
                               'walkable8':source['walkable_tiles'],'flat_rect':[inside_x,inside_y,8,8],
                               'native_pair':pair,'native_corner':mid,'flat_native_pixels_unchanged':64,'output_sha256':row['compositionPixelHash']}
                        proofs.append(proof)
                        if game=='red':examples.setdefault(seedq,(source,preview.native_cell(sheet,ts,ts['blocks'][bid],q),ref(mid),image))
                        break
    catalogs={g:json.loads((ROOT/f'.work/tileshift-catalog/{g}.json').read_text())for g in ('red','blue','yellow','firered')}
    assert preview.verify(rows,CACHE,catalogs,ROOT/'TileShift')==len(rows)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
    canvas=Image.new('RGB',(1280,810),'#18212b');draw=ImageDraw.Draw(canvas)
    draw.text((12,12),'CONNECTED CAVE CORNERS - actual remaining source occurrences, exact8px flat standing plane',font=font,fill='white')
    draw.text((12,40),'Complete32px block2 profiles are excluded. Only the original tile5 quadrant receives flat657; all surrounding cells keep their reviewed art.',font=font,fill='#c4cdd8')
    for q,(source,original,ref,image)in sorted(examples.items()):
        x=12+q*310
        draw.text((x,80),f'Corner{q}: source{source["block_id"]}:{source["quadrant"]}',font=font,fill='white')
        for n,(label,im)in enumerate((('Original source',original),('Native full corner'+str(ref['id']),preview.native_donor(CACHE,ref,packed)),('Native+exact8px plane',image))):
            y=110+n*190;canvas.paste(im.resize((128,128),Image.Resampling.NEAREST),(x,y));draw.text((x,y+136),label,font=font,fill='white')
        draw.multiline_text((x,700),str(source['tiles'])+'\nwalk'+str(source['walkable_tiles']),font=font,fill='white',spacing=6)
    canvas.save(OUT/'cave-connected-corner-eight-pixel-review.png')
    contexts=[('MT_MOON_1F',(0,0,14,12)),('SEAFOAM_ISLANDS_1F',(8,0,14,12)),('CERULEAN_CAVE_B1F',(0,6,16,10))]
    for name,(x,y,w,h)in contexts:
        source,current,_=render_map('red',name,active,packed)
        _,candidate,covered=render_map('red',name,active+rows,packed)
        bounds=(x*16,y*16,(x+w)*16,(y+h)*16)
        image=Image.new('RGB',(3*(w*32+16)+16,h*32+114),'#18212b');d=ImageDraw.Draw(image)
        d.text((12,12),name+' - connected corners, per-source8px flat footprint. No collision or neighboring feature moved.',font=font,fill='white')
        for col,(label,im)in enumerate((('Original source',source),('Current reviewed stage',current),('Candidate native corner joins',candidate))):
            xx=16+col*(w*32+16);d.text((xx,47),label,font=font,fill='white');image.paste(im.crop(bounds).resize((w*32,h*32),Image.Resampling.NEAREST),(xx,77))
        image.save(OUT/f'red-{name}-connected-corners-context.png');candidate.save(OUT/f'red-{name}-connected-corners-full.png')
    (OUT/'connected-corner-candidates.lua').write_text('return '+review.lua_value(rows)+'\n',encoding='utf-8')
    (OUT/'connected-corner-proof.json').write_text(json.dumps({'status':'private_visual_review_required','rows':len(rows),
          'counts_by_game':dict(Counter(r['game']for r in rows)),'all_exact_flat_quarters':True,'proofs':proofs},indent=2))
    if args.write_approved_corners:
        retained=[r for r in preview.read_reviewed(extended.TARGET)if r['role']not in ROLES]
        extended.write_groups(retained+rows)
    print(json.dumps({'rows':len(rows),'counts_by_game':dict(Counter(r['game']for r in rows)),
                      'production_written':args.write_approved_corners},indent=2))


if __name__=='__main__':main()
