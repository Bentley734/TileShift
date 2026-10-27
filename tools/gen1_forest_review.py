"""Review actual Gen1 forest ground against the native FRLG counterpart.

The generated candidates stay private until their labeled art/context review.
Identical pictures never replace source raw-material/behavior evidence.
"""
from __future__ import annotations
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import zlib
from PIL import Image,ImageDraw,ImageFont
import catalog
import preview
import review
import gen1_extended_review as extended
from building_review import decode_layout

ROOT=Path(__file__).resolve().parents[2]
CACHE=Path(catalog.os.environ['APPDATA'])/'pokemon-love2d'
OUT=ROOT/'.work/tileshift-gen1-forest-review'
ROLES={'forest_open_ground','forest_tall_grass'}
MAPS=('VIRIDIAN_FOREST','SAFARI_ZONE_CENTER','SAFARI_ZONE_EAST','SAFARI_ZONE_WEST','SAFARI_ZONE_NORTH')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--write-approved-ground-grass',action='store_true')
    args=p.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    native_root=CACHE/'firered/data/generated/gba/native'
    manifest=catalog.read_lua(native_root/'manifest.lua')
    records=json.loads((ROOT/'.work/tileshift-catalog/firered.json').read_text())['cells']
    records={(r['pair'],r['mid']):r for r in records}
    effect=(CACHE/'firered/data/generated/gba/field_effects/tall_grass.rgba').read_bytes()
    if len(effect)!=5120:effect=zlib.decompress(effect)
    assert len(effect)==5120
    effect_meta=catalog.read_lua(CACHE/'firered/data/generated/gba/field_effects/tall_grass.meta')
    assert {k:effect_meta[k]for k in ('w','h','frames','fw','fh')}=={'w':16,'h':80,'frames':5,'fw':16,'fh':16}
    effect_frames=[{'frame':frame,'rgba_pixel_sha256':catalog.sha(effect[frame*1024:(frame+1)*1024]),
                    'nontransparent_pixels':sum(effect[frame*1024+i*4+3]>0 for i in range(256))}for frame in range(5)]
    assert all(f['nontransparent_pixels']>0 for f in effect_frames)
    foreground={'game':'firered','effect':'tall_grass','hash':catalog.sha(effect)}
    rows=[];proofs=[];packed={};red_examples={};scenes={}
    for game in ('red','blue','yellow'):
        root=CACHE/game;maps=catalog.read_lua(root/'data/generated/maps.lua')
        ts=catalog.read_lua(root/'data/generated/tilesets.lua')['FOREST']
        sheet=Image.open(root/ts['image'])
        data=json.loads((ROOT/f'.work/tileshift-catalog/{game}.json').read_text())
        cells={(r['block_id'],r['quadrant']):r for r in data['cells']if r['tileset']=='FOREST'}
        files=next(t['fingerprints']for t in data['tilesets']if t['tileset']=='FOREST')
        assert ts['grassTile']==32
        for name in MAPS:
            m=maps[name];assert m['tileset']=='FOREST'
            spec=manifest['layouts']['FR_'+name];pair=spec['pair']
            def ref(mid):return {'game':'firered','tileset':pair,'id':mid,'hash':records[pair,mid]['pixel_sha256']}
            occurrences=Counter((bid,q)for bid in m['blocks']for q in range(4))
            ground_grass=[]
            for (bid,q),uses in sorted(occurrences.items()):
                cell=cells[bid,q];raw=cell['tiles']
                if raw==[48]*4:
                    role,mid='forest_open_ground',1
                    assert cell['walkable_tiles']==[True]*4 and not cell['grass_tile_present']
                elif set(raw)<={32,52}and 32 in raw:
                    role,mid='forest_tall_grass',13
                    assert cell['walkable_tiles']==[True]*4 and cell['grass_tile_present']
                    assert raw[2]==32,'Native source foot/encounter material must remain tall grass'
                else:continue
                assert not cell['warp_tile_present']
                row={'game':game,'style':'gen3','tileset':'FOREST','map':name,'id':bid,'quadrant':q,
                     'role':role,'status':'reviewed','sourceHash':cell['grayscale_pixel_sha256'],'sourceFiles':files,
                     'donor':ref(mid),'nativeContext':{'map':'FR_'+name,'pair':pair},
                     'evidence':'Complete native FRLG counterpart forest terrain, reviewed in actual source and remake map context. '
                       'Exact source raw materials, full pixel fingerprint and walk/grass/warp flags are checked. '
                       'Raw48 is actual walkable open ground; identical unused raw0 blocked pixels are explicitly excluded. '
                       'Full raw32/52 tall-grass variants retain native source encounter and foot material32; '
                       'the original source geometry, encounters, grass/Cut rules and events remain authoritative.'}
                if mid==13:row.update(foreground=copy.deepcopy(foreground),occludes=True)
                rows.append(row);ground_grass.append(row)
                proofs.append({'game':game,'map':name,'source':[bid,q],'raw':raw,
                               'walkable8':cell['walkable_tiles'],'role':role,'occurrences':uses,
                               'donor':row['donor'],'source_grass_bottom_left':raw[2]==32})
                if game=='red':red_examples.setdefault(tuple(raw),(cell,preview.native_cell(sheet,ts,ts['blocks'][bid],q)))
            if game=='red'and name in ('VIRIDIAN_FOREST','SAFARI_ZONE_WEST'):
                index={(r['id'],r['quadrant']):r for r in ground_grass}
                native=Image.new('RGBA',(m['width']*32,m['height']*32));candidate=native.copy()
                for pos,bid in enumerate(m['blocks']):
                    for q in range(4):
                        x,y=pos%m['width']*32+q%2*16,pos//m['width']*32+q//2*16
                        image=preview.native_cell(sheet,ts,ts['blocks'][bid],q);native.paste(image,(x,y))
                        r=index.get((bid,q));candidate.paste(preview.replacement_image(CACHE,r,packed,ROOT/'TileShift')if r else image,(x,y))
                native.save(OUT/f'red-{name}-source.png');candidate.save(OUT/f'red-{name}-ground-grass-candidate.png')
                scenes[name]=(native,candidate)
    # Independent live source/foreground/decoder checks, including each cartridge.
    catalogs={g:json.loads((ROOT/f'.work/tileshift-catalog/{g}.json').read_text())for g in('red','blue','yellow','firered')}
    assert preview.verify(rows,CACHE,catalogs,ROOT/'TileShift')==len(rows)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
    canvas=Image.new('RGB',(1380,790),'#18212b');draw=ImageDraw.Draw(canvas)
    draw.text((12,12),'FOREST GROUND AND TALL GRASS - exact source materials and actual FRLG forest/Safari counterparts',font=font,fill='white')
    draw.text((12,40),'Walkable raw48 ground; full grass raw32/52. Unused blocked raw0 is excluded despite identical pixels. No raised plane/trees inferred.',font=font,fill='#c4cdd8')
    for col,(raw,(cell,image))in enumerate(sorted(red_examples.items())):
        x=12+col*190;canvas.paste(image.resize((96,96),Image.Resampling.NEAREST),(x,90))
        draw.multiline_text((x,194),f"Source {cell['block_id']}:{cell['quadrant']}\nraw{list(raw)}\nwalkable all4",font=font,fill='white',spacing=3)
    for n,(label,name)in enumerate((('ViridianForest','FR_VIRIDIAN_FOREST'),('SafariZone','FR_SAFARI_ZONE_WEST'))):
        spec=manifest['layouts'][name];pair=spec['pair'];layout=decode_layout(native_root/spec['file'])
        for col,mid in enumerate((1,13)):
            ref={'game':'firered','tileset':pair,'id':mid,'hash':records[pair,mid]['pixel_sha256']}
            x=12+n*650+col*180;y=290
            tile=preview.native_donor(CACHE,ref,packed);canvas.paste(tile.resize((96,96),Image.Resampling.NEAREST),(x,y))
            draw.text((x,y+102),label+' native'+str(mid),font=font,fill='white')
            positions=[(i%layout['width'],i//layout['width'])for i,m in enumerate(layout['mids'])if m==mid]
            assert positions
            def score(pos):
                x,y=pos
                return sum(layout['mids'][yy*layout['width']+xx]==mid for yy in range(max(0,y-1),min(layout['height'],y+2))for xx in range(max(0,x-1),min(layout['width'],x+2)))
            cx,cy=max(positions,key=score);context=Image.new('RGBA',(48,48))
            for dy in range(-1,2):
                for dx in range(-1,2):
                    xx,yy=cx+dx,cy+dy
                    if 0<=xx<layout['width']and 0<=yy<layout['height']:
                        m=layout['mids'][yy*layout['width']+xx]
                        r={'game':'firered','tileset':pair,'id':m,'hash':records[pair,m]['pixel_sha256']}
                        context.paste(preview.native_donor(CACHE,r,packed),((dx+1)*16,(dy+1)*16))
            canvas.paste(context.resize((144,144),Image.Resampling.NEAREST),(x,y+142))
            draw.text((x,y+290),'Actual '+str((cx,cy)),font=font,fill='#c4cdd8')
    mask=Image.frombytes('RGBA',(16,80),effect).crop((0,72,16,80))
    draw.text((1070,290),'Native grass foot cover',font=font,fill='white')
    bg=Image.new('RGBA',(16,16),(255,0,255,255));bg.alpha_composite(mask,(0,8))
    canvas.paste(bg.resize((128,128),Image.Resampling.NEAREST),(1070,322))
    draw.multiline_text((1070,468),'Unchanged native frame4\nbottom8px over actor feet\nfull field-effect hash checked',font=font,fill='white',spacing=5)
    counts=Counter()
    for p in proofs:counts[p['game'],p['role']]+=p['occurrences']
    draw.multiline_text((12,662),'Per-cart source cells: '+str({role:counts['red',role]for role in sorted(ROLES)})
                        +'\nAll source layout, raw8px flags, encounter material and original Cut restrictions remain unchanged.'
                        +'\nPrivate proposal; native complete16 cells and native foreground only, no graphics painted or scaled in production.',font=font,fill='white',spacing=7)
    canvas.save(OUT/'forest-ground-grass-source-native-review.png')
    (OUT/'forest-ground-grass-candidates.lua').write_text('return '+review.lua_value(rows)+'\n',encoding='utf-8')
    (OUT/'forest-ground-grass-proof.json').write_text(json.dumps({'status':'private_visual_review_required','rows':len(rows),
       'occurrences':{game:{role:counts[game,role]for role in sorted(ROLES)}for game in('red','blue','yellow')},
       'foreground':foreground,'foreground_native_frames':effect_frames,
       'native_foot_cover_frame':4,'native_foot_cover_rect':[0,72,16,8],'proofs':proofs},indent=2))
    if args.write_approved_ground_grass:
        retained=[r for r in preview.read_reviewed(extended.TARGET)if r['role']not in ROLES]
        extended.write_groups(retained+rows)
    print(json.dumps({'rows':len(rows),'red_occurrences':sum(counts['red',r]for r in ROLES),
                      'production_written':args.write_approved_ground_grass},indent=2))


if __name__=='__main__':main()
