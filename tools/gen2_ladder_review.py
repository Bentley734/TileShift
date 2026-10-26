"""Complete cave-ladder review; production writes need --write-reviewed.

The upward glyph is the native165px Emerald middle layer. The downward FR645
hole has no alpha layer: explicit regional strips retain all227 hole,
rim and ladder pixels while replacing only its29 outside ground pixels.
"""
from __future__ import annotations
import argparse
import copy
import json
import os
from pathlib import Path
import re
import sys

WORKSPACE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(WORKSPACE/'.tools/python'))
from PIL import Image,ImageDraw,ImageFont
import catalog
import preview
import gen2_extended_review as ext
import gen2_cave_review as cave

DOWN_RECTS={
    'general__rom_082d4bfc':((4,0,8,1),(2,1,12,1),(1,2,14,1),(0,3,16,7),(0,10,15,2),
                           (0,12,16,1),(1,13,14,1),(2,14,12,1),(4,15,9,1)),
    'general__rom_082d4e24':((4,0,8,1),(2,1,12,1),(1,2,14,1),(0,3,16,10),
                           (1,13,14,1),(2,14,12,1),(5,15,7,1)),
}
UP_MID_HASH='1fc39422ac218e6436105b329e5d887d1874f00d2e4b81966c5c3524ffc39bff'
CASES=(('MOUNT_MOON',27,'up','cave_rock_floor'),('MOUNT_MOON',31,'down','cave_rock_floor'),
       ('UNION_CAVE_B1F',20,'up','cave_raised_rock_plateau_top'),
       ('UNION_CAVE_1F',21,'down','cave_raised_rock_plateau_top'),
       ('ICE_PATH_B1F',3,'up','snowy_cave_floor'),('ICE_PATH_1F',7,'down','snowy_cave_floor'))


def source_cases(cache,game,data):
    result=[]
    for name,definition in sorted(data['maps'].items()):
        if not isinstance(definition,dict) or definition.get('tileset') not in cave.SETS or definition.get('environment')!='CAVE':continue
        ts=definition['tileset']
        for bid in sorted(set(catalog.lua_array(definition['blocks']))):
            for q in range(4):
                cell=ext.cell_info(cache,game,data,ts,bid,q)
                if cell['collision']!=0x72:continue
                assert q==3,'A ladder outside the reviewed source quadrant needs separate context review'
                if ts=='TILESET_ICE_PATH':
                    directions={(10,11,26,27):'up',(42,43,58,59):'down'}
                    direction=directions[tuple(cell['tiles'])];plane='snowy_cave_floor'
                    allowed={18,25,154,155,170,171} if game=='crystal' else {18,25}
                else:
                    directions={(40,41,56,57):('up','cave_rock_floor'),(32,33,48,49):('down','cave_rock_floor'),
                                (42,43,58,59):('up','cave_raised_rock_plateau_top'),(34,35,50,51):('down','cave_raised_rock_plateau_top')}
                    direction,plane=directions[tuple(cell['tiles'])]
                    allowed={1} if plane=='cave_rock_floor' else {22}
                left=ext.cell_info(cache,game,data,ts,bid,2)
                assert left['collision']==0 and set(left['tiles'])<=allowed
                assert not any(a.get('priority') for a in left['attributes'])
                result.append((name,bid,direction,plane))
    return result


def plane_reference(cache,game,name,plane,active,records):
    row=next((r for r in active if r['game']==game and r.get('map')==name and r['role']==plane and r.get('donor')),None)
    if row:return row['donor']
    assert plane in {'cave_rock_floor','cave_raised_rock_plateau_top'}
    target,native_name=cave.TERRAIN_CASES.get(name,('emerald','EM_GRANITE_CAVE_1F'))
    manifest=catalog.read_lua(cache/target/'data/generated/gba/native/manifest.lua')
    pair=manifest['layouts'][native_name]['pair']
    mid=(641 if plane=='cave_rock_floor' else 657) if target=='firered' else (513 if plane=='cave_rock_floor' else 529)
    return {'game':target,'tileset':pair,'id':mid,'hash':records[target][pair,mid]['pixel_sha256']}


def ice_depth(name):
    match=re.search(r'_B(\d+)F',name)
    return -int(match.group(1)) if match else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=Path(os.environ['APPDATA'])/'pokemon-love2d')
    parser.add_argument('--engine',type=Path,default=WORKSPACE/'.tools/engine-0395')
    parser.add_argument('--output',type=Path,default=WORKSPACE/'.work/tileshift-gen2-ladder-review')
    parser.add_argument('--all-ladders',action='store_true',help='Check all234 actual source warp occurrences and their planes')
    parser.add_argument('--write-reviewed',action='store_true',help='Merge the approved complete-ladder recipes after all live checks')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    mod=WORKSPACE/'TileShift';active=ext.active_rows(mod);packed={};rows=[];examples=[];proofs=[]
    records={game:{(r['pair'],r['mid']):r for r in json.loads((WORKSPACE/f'.work/tileshift-catalog/{game}.json').read_text())['cells']}
             for game in ('emerald','firered')}
    up={'game':'emerald','tileset':'general__cave','id':574,'hash':records['emerald']['general__cave',574]['pixel_sha256']}
    preview.native_donor(args.cache,up,packed)
    up_mid=preview.native_donor(args.cache,up,packed,['mid'],{'mid':UP_MID_HASH})
    assert sum(a>0 for r,g,b,a in up_mid.get_flattened_data())==165
    for game in ext.GAMES:
        data=ext.source(args.cache,game)
        cases=source_cases(args.cache,game,data) if args.all_ladders else CASES
        for name,bid,direction,plane in cases:
            definition=data['maps'][name];ts=definition['tileset'];cell=ext.cell_info(args.cache,game,data,ts,bid,3)
            assert cell['collision']==0x72
            coords=[[i%definition['width']*2+1,i//definition['width']*2+1] for i,b in enumerate(catalog.lua_array(definition['blocks'])) if b==bid]
            assert coords
            warps=[w for w in catalog.lua_array(definition['warps']) if [w['x'],w['y']] in coords]
            assert len(warps)==len(coords)
            if ts=='TILESET_ICE_PATH':
                for warp in warps:
                    assert warp['destMap'].startswith('ICE_PATH_')
                    assert (ice_depth(warp['destMap'])>ice_depth(name))==(direction=='up'),(name,warp,direction)
            left=ext.cell_info(args.cache,game,data,ts,bid,2)
            base=plane_reference(args.cache,game,name,plane,active,records);parts=[]
            if direction=='up':
                parts=[{'donor':up,'srcX':0,'srcY':0,'w':16,'h':16,'x':0,'y':0,
                        'layers':['mid'],'layerHashes':{'mid':UP_MID_HASH}}]
            else:
                # Equal IDs in another regional bank may have a different
                # contour or be unavailable. Keep the approved canonical227px
                # glyph; only Ice Path uses the independently reviewed variant.
                pair='general__rom_082d4e24' if plane=='snowy_cave_floor' else 'general__rom_082d4bfc'
                ref={'game':'firered','tileset':pair,'id':645,'hash':records['firered'][pair,645]['pixel_sha256']}
                image=preview.native_donor(args.cache,ref,packed);mids,pal,layers=packed['firered',pair]
                native=layers['under'][mids.index(645)*256:(mids.index(645)+1)*256]
                rectangles=DOWN_RECTS[pair]
                mask={(x+dx,y+dy) for x,y,w,h in rectangles for dy in range(h) for dx in range(w)}
                assert len(mask)==227
                for y in range(16):
                    for x in range(16):
                        # These checked palette9 entries are precisely the
                        # inspected native hole/wood/rim; outside2..4 is floor.
                        assert ((x,y) in mask)==(5<=native[y*16+x]%16<=12),(pair,x,y,native[y*16+x])
                for x,y,w,h in rectangles:parts.append({'donor':ref,'srcX':x,'srcY':y,'w':w,'h':h,'x':x,'y':y})
            row={'game':game,'style':'gen3','map':name,'tileset':ts,'id':bid,'quadrant':3,
                 'role':'cave_'+('ascending' if direction=='up' else 'descending')+'_ladder',
                 'kind':'native_composite','base':base,'parts':parts,'status':'candidate',
                 'sourceHash':cell['sourceHash'],'sourceFiles':data['fingerprints'][ts],
                 'sourceCells':coords,'sourceCollision':cell['collision'],'sourceWarps':warps,
                 'sourcePriority':[bool(a.get('priority')) for a in cell['attributes']],
                 'sourcePalettes':[a.get('palette',1) for a in cell['attributes']],
                 'sourcePlaneEvidence':{'quadrant':2,'tiles':left['tiles'],'hash':left['sourceHash'],'collision':left['collision']},
                 'sourcePlane':plane,'evidence':'Private complete16px ladder proposal. Source glyph family, actual warp links and surrounding floor/raised/snow plane are displayed independently. Up retains all165 native Emerald574 middle-layer pixels; down retains every one of227 nativeFR645 hole/wood/rim pixels in explicit regional rectangles and substitutes only29 outside floor pixels. Base uses the already reviewed regional plane. No glyph pixel is cropped away, recolored or scaled, and no32px native upward glyph is truncated. Source warps and ladder behavior remain native.'}
            revised=preview.replacement_image(args.cache,row,packed,mod);base_image=preview.native_donor(args.cache,base,packed)
            if direction=='up':
                native_glyph=up_mid
                mask={(x,y) for y in range(16) for x in range(16) if up_mid.getpixel((x,y))[3]}
            else:native_glyph=image
            assert all(revised.getpixel(p)==native_glyph.getpixel(p) for p in mask)
            assert all(revised.getpixel((x,y))==base_image.getpixel((x,y)) for y in range(16) for x in range(16) if (x,y) not in mask)
            proofs.append({'game':game,'map':name,'direction':direction,'source':[bid,3],
                           'completeNativeGlyphPixels':len(mask),'glyphDifferences':0,'outsidePixelsMatchPlane':True,
                           'composedPixelHash':catalog.sha(revised.tobytes())})
            rows.append(row)
            if game=='crystal' and ((name,bid,direction,plane) in CASES or name in {'ROCK_TUNNEL_1F','ROCK_TUNNEL_B1F'}):examples.append((row,cell,data,definition,revised))
    canvas=Image.new('RGB',(1410,78+len(examples)*240),'#18202c');draw=ImageDraw.Draw(canvas);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    draw.text((14,12),'Complete native16px cave ladders over the source-appropriate reviewed regional plane',font=font,fill='white')
    draw.text((14,40),'No glyph pixels removed:165px up /227px down. Source and proposed3x3 contexts preserve all neighboring geometry.',fill='#ccd7e5')
    for i,(row,cell,data,definition,revised) in enumerate(examples):
        y=83+i*240;x0,y0=row['sourceCells'][0];before=Image.new('RGBA',(48,48));after=Image.new('RGBA',(48,48));blocks=catalog.lua_array(definition['blocks'])
        mapping={(r['id'],r['quadrant']):r for r in active if r['game']=='crystal' and r['tileset']==row['tileset'] and r.get('map',row['map'])==row['map']}
        for dy in range(-1,2):
            for dx in range(-1,2):
                x,z=x0+dx,y0+dy
                if 0<=x<definition['width']*2 and 0<=z<definition['height']*2:
                    bid=blocks[z//2*definition['width']+x//2];q=z%2*2+x%2;part=ext.cell_info(args.cache,'crystal',data,row['tileset'],bid,q)
                    source=cave.source_image(args.cache,'crystal',data,part,definition);before.paste(source,((dx+1)*16,(dy+1)*16))
                    other=mapping.get((bid,q));target=preview.replacement_image(args.cache,other,packed,mod) if other else source
                    after.paste(target,((dx+1)*16,(dy+1)*16))
        after.paste(revised,(16,16))
        draw.text((14,y),f"{row['map']} {row['id']}:3 / {row['role']} / {row['sourcePlane']}",font=font,fill='white')
        for x,image in ((14,before),(705,after)):
            canvas.paste(image.resize((192,192),Image.Resampling.NEAREST),(x,y+29));draw.rectangle((x+64,y+93,x+127,y+156),outline='#fff293',width=2)
        draw.text((224,y+51),f"Source raw{cell['tiles']} at({x0},{y0})",fill='#ccd7e5')
        draw.text((224,y+76),'To '+row['sourceWarps'][0]['destMap'],fill='#ccd7e5')
        draw.text((915,y+51),f"Native glyph + {row['base']['game']}{row['base']['id']}",fill='#ccd7e5')
        draw.text((915,y+76),'Complete glyph: 0 different pixels',fill='#e5ce9a')
    canvas.save(args.output/'source-native-complete-ladder-contexts.png')
    probe=copy.deepcopy(rows)
    for row in probe:row['status']='reviewed'
    live=ext.validate_batch(probe,args,mod)
    cells=sum(len(row['sourceCells']) for row in rows)
    if args.all_ladders:assert cells==234,(cells,'Actual source ladder coverage changed')
    grouped={}
    for row in rows:
        key=(row['game'],row['map'],row['tileset'],row['id'],row['quadrant'])
        identity=(row['sourcePlane'],json.dumps(row['base'],sort_keys=True))
        assert key not in grouped or grouped[key]==identity,'Mixed plane context needs positional rows'
        grouped[key]=identity
    (args.output/'ladder-candidates.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    (args.output/'complete-glyph-proof.json').write_text(json.dumps({'live':live,'proofs':proofs,'downRectangles':DOWN_RECTS,
        'sourceWarpOccurrences':cells,'positionalOverridesRequired':0,'iceDepthDirectionsChecked':True},indent=2),encoding='utf-8')
    print('Private complete-ladder rows',len(rows),'source warp occurrences',cells,live,'production writes: 0')
    if args.write_reviewed:
        assert args.all_ladders,'The reviewed activation requires the complete actual-warp audit'
        for row in probe:row['evidence']=row['evidence'].replace('Private complete16px','Visually reviewed complete16px',1)
        stats=ext.merge_reviewed(probe,mod/'mappings/gen2_caves.lua')
        (args.output/'activation.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
        print('Approved complete-ladder activation',stats)


if __name__=='__main__':main()
