"""Gen2 cave inventory and native Gen3 context; writes need explicit approval.

Dark caves are pictured after native Flash (NITE), because the runtime keeps
the original source darkness and entrance flicker before Flash. These contacts
are references for visual review, never collision-only automatic substitutions.
Only an explicit --write-reviewed flag merges an approved, live-checked batch.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import copy
import json
import os
from pathlib import Path
import sys

WORKSPACE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(WORKSPACE/'.tools/python'))
from PIL import Image,ImageDraw,ImageFont
import catalog
import preview
import gen2_extended_review as ext
from building_review import decode_layout

SETS={'TILESET_CAVE','TILESET_DARK_CAVE','TILESET_ICE_PATH'}
SOURCE_SCENES=('UNION_CAVE_1F','DARK_CAVE_VIOLET_ENTRANCE','ROCK_TUNNEL_1F',
               'ICE_PATH_1F','MOUNT_MOON','DIGLETTS_CAVE','VICTORY_ROAD')
NATIVE_SCENES={
    'firered':('FR_MT_MOON_1F','FR_ROCK_TUNNEL_1F','FR_DIGLETTS_CAVE_B1F',
               'FR_SEAFOAM_ISLANDS_1F','FR_FOUR_ISLAND_ICEFALL_CAVE_B1F'),
    'emerald':('EM_GRANITE_CAVE_1F','EM_GRANITE_CAVE_B1F','EM_GRANITE_CAVE_B2F',
               'EM_SHOAL_CAVE_LOW_TIDE_ICE_ROOM'),
}
TERRAIN_CASES={
    'MOUNT_MOON':('firered','FR_MT_MOON_1F'),
    'DIGLETTS_CAVE':('firered','FR_DIGLETTS_CAVE_B1F'),
    'VICTORY_ROAD':('firered','FR_VICTORY_ROAD_1F'),
    'ROCK_TUNNEL_1F':('firered','FR_ROCK_TUNNEL_1F'),
    'ROCK_TUNNEL_B1F':('firered','FR_ROCK_TUNNEL_B1F'),
    'UNION_CAVE_1F':('emerald','EM_GRANITE_CAVE_1F'),
    'UNION_CAVE_B1F':('emerald','EM_GRANITE_CAVE_B1F'),
    'UNION_CAVE_B2F':('emerald','EM_GRANITE_CAVE_B2F'),
    'DARK_CAVE_VIOLET_ENTRANCE':('emerald','EM_GRANITE_CAVE_1F'),
    'DARK_CAVE_BLACKTHORN_ENTRANCE':('emerald','EM_GRANITE_CAVE_B1F'),
}
TERRAIN_ROLES=(('cave_rock_floor',(2,0),(24,3),(1,1,1,1),0x00,641,513),
               ('cave_raised_rock_plateau_top',(9,0),(9,0),(22,22,22,22),0x00,657,529),
               ('cave_raised_rock_mass_front',(13,2),(13,2),(38,38,38,38),0x07,665,537))
EDGE_ROLES=(('cave_raised_plateau_north_rim',(4,1),(4,1),(36,36,22,22),0xb2,649,521),
            ('cave_rock_mass_west_side',(4,2),(12,0),(21,21,21,21),0x07,656,528),
            ('cave_rock_mass_east_side',(10,1),(14,1),(23,23,23,23),0x07,658,530),
            ('cave_fixed_small_boulder',(28,0),(24,0),(12,13,28,29),0x07,642,514))


def lit_daytime(definition):
    pinned=definition.get('palette','PALETTE_DAY').removeprefix('PALETTE_')
    return 'NITE' if pinned=='DARK' else ('DAY' if pinned=='AUTO' else pinned)


def source_image(cache,game,data,cell,definition):
    ts=data['sets'][cell['tileset']]
    palettes=preview.palette_set(data['palettes'],definition,lit_daytime(definition))
    return preview.native_cell(data['sheets'][cell['tileset']],ts,
        catalog.lua_array(catalog.dict_at(ts['blocks'],cell['id']+1)),cell['quadrant'],palettes)


def contact(path,title,rows,columns=7):
    cw,ch=205,146
    image=Image.new('RGB',(columns*cw,72+((len(rows)+columns-1)//columns)*ch),'#18202c')
    draw=ImageDraw.Draw(image);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
    draw.text((12,12),title,font=font,fill='white')
    draw.text((12,38),'Native complete cells and actual contexts; reference IDs do not imply equivalence. Dark sources shown after Flash.',font=font,fill='#ccd7e5')
    for i,(label,tile) in enumerate(rows):
        x,y=i%columns*cw+12,i//columns*ch+76
        image.paste(tile.resize((64,64),Image.Resampling.NEAREST),(x,y))
        draw.multiline_text((x,y+68),label,font=font,fill='white',spacing=1)
    image.save(path)


def edge_contexts(args,samples,native,packed):
    groups=defaultdict(list)
    for sample in samples.values():groups[sample[0]['tileset'],sample[0]['donor']['tileset']].append(sample)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    for (tileset,pair),examples in groups.items():
        canvas=Image.new('RGB',(1400,78+len(examples)*246),'#18202c');d=ImageDraw.Draw(canvas)
        d.text((14,12),'Cave edge geometry: actual source and native3x3 contexts; center16px outlined',font=font,fill='white')
        d.text((14,40),f'{tileset} / {pair}: north rim, west/east sides and whole16px fixed boulders; corners and slopes held.',fill='#ccd7e5')
        for i,(row,cell,data,definition) in enumerate(examples):
            y=83+i*246;x0,y0=row['sourceCells'][0];src=Image.new('RGBA',(48,48));blocks=catalog.lua_array(definition['blocks'])
            for dy in range(-1,2):
                for dx in range(-1,2):
                    x,z=x0+dx,y0+dy
                    if 0<=x<definition['width']*2 and 0<=z<definition['height']*2:
                        bid=blocks[z//2*definition['width']+x//2];part=ext.cell_info(args.cache,'crystal',data,row['tileset'],bid,z%2*2+x%2)
                        src.paste(source_image(args.cache,'crystal',data,part,definition),((dx+1)*16,(dy+1)*16))
            donor=row['donor'];target=native[donor['game']];spec=target['manifest']['layouts'][row['nativeContext']['map']]
            layout=decode_layout(target['root']/spec['file']);mid=donor['id'];pos=layout['mids'].index(mid);nx,nz=pos%layout['width'],pos//layout['width'];dst=Image.new('RGBA',(48,48))
            for dy in range(-1,2):
                for dx in range(-1,2):
                    x,z=nx+dx,nz+dy
                    if 0<=x<layout['width'] and 0<=z<layout['height']:
                        other=layout['mids'][z*layout['width']+x];record=target['records'][spec['pair'],other]
                        ref={'game':donor['game'],'tileset':spec['pair'],'id':other,'hash':record['pixel_sha256']}
                        dst.paste(preview.native_donor(args.cache,ref,packed),((dx+1)*16,(dy+1)*16))
            d.text((14,y),row['role'].replace('_',' '),font=font,fill='white')
            for x,image in ((14,src),(705,dst)):
                canvas.paste(image.resize((192,192),Image.Resampling.NEAREST),(x,y+29))
                d.rectangle((x+64,y+93,x+127,y+156),outline='#fff293',width=2)
            d.text((224,y+45),f"{row['map']} {row['id']}:{row['quadrant']}",fill='#ccd7e5')
            d.text((224,y+69),f"Source ({x0},{y0}) / col0x{cell['collision']:02x}",fill='#ccd7e5')
            d.text((915,y+45),f"{donor['game']} {mid} at ({nx},{nz})",fill='#ccd7e5')
            d.text((915,y+69),row['nativeContext']['map'],fill='#ccd7e5')
        canvas.save(args.output/f'edge-context-{tileset}-{pair}.png')


def terrain_candidates(args,edges=False):
    """Complete terrain or straight-edge roles, pending visual approval.

    Both batches gate source geometry/palette/priority. Diagonal banks,
    corners, ladders, exits, water, ice and puzzles are not inferred here.
    """
    candidates=[];held=[];samples={};packed={};native={};prefix='edge' if edges else 'terrain'
    for game in ('firered','emerald'):
        root=args.cache/game/'data/generated/gba/native'
        native[game]={'root':root,'manifest':catalog.read_lua(root/'manifest.lua'),
          'records':{(r['pair'],r['mid']):r for r in json.loads((WORKSPACE/f'.work/tileshift-catalog/{game}.json').read_text())['cells']}}
    for game in ext.GAMES:
        data=ext.source(args.cache,game)
        for name,(donor_game,native_name) in TERRAIN_CASES.items():
            definition=data['maps'][name];ts=definition['tileset'];target=native[donor_game]
            spec=target['manifest']['layouts'][native_name];layout=decode_layout(target['root']/spec['file'])
            seeds={}
            for role,cave_seed,dark_seed,raw,collision,fr_mid,em_mid in (EDGE_ROLES if edges else TERRAIN_ROLES):
                bid,q=dark_seed if ts=='TILESET_DARK_CAVE' else cave_seed
                cell=ext.cell_info(args.cache,game,data,ts,bid,q)
                assert tuple(cell['tiles'])==raw and cell['collision']==collision
                seeds[ext.identity(cell)]=(role,fr_mid if donor_game=='firered' else em_mid)
            occurrences=defaultdict(list)
            for index,bid in enumerate(catalog.lua_array(definition['blocks'])):
                for q in range(4):occurrences[bid,q].append([index%definition['width']*2+q%2,index//definition['width']*2+q//2])
            for (bid,q),coords in sorted(occurrences.items()):
                cell=ext.cell_info(args.cache,game,data,ts,bid,q);match=seeds.get(ext.identity(cell))
                if not match:continue
                role,mid=match
                if mid not in layout['mids']:
                    held.append({'game':game,'map':name,'role':role,'nativeMap':native_name,
                                 'mid':mid,'reason':'Role is absent from actual native reference map'})
                    continue
                record=target['records'][spec['pair'],mid]
                row={'game':game,'style':'gen3','map':name,'tileset':ts,'id':bid,'quadrant':q,
                    'role':role,'status':'candidate','sourceHash':cell['sourceHash'],
                    'sourceFiles':data['fingerprints'][ts],'sourceCells':coords,'sourceCollision':cell['collision'],
                    'sourcePriority':[bool(a.get('priority')) for a in cell['attributes']],
                    'sourcePalettes':[a.get('palette',1) for a in cell['attributes']],
                    'nativeContext':{'map':native_name,'layoutFileHash':layout['file_sha256'],
                                     'contextKind':'same Kanto cave' if donor_game=='firered' else 'Hoenn natural-cave equivalent'},
                    'donor':{'game':donor_game,'tileset':spec['pair'],'id':mid,'hash':record['pixel_sha256']},
                    'evidence':'Proposed complete16px floor, walkable raised-rock plateau top, or blocked vertical rock-mass front. Explicit map scope; exact source pixels, collision, palette slots and per8px priority checked against the displayed seed. The target is used in the actual named Gen3 cave reference. Source floor/raised mass geometry is retained. Side walls, diagonal banks, water, ladders, exits, ice and puzzles remain held. Before native Flash, original darkness and entrance flicker remain intact.'}
                if edges:row['evidence']='Proposed complete16px north rim, west/east vertical wall side, or fixed small boulder. Native source north-rim0xb2 blocks upward crossing, as does the target north rim. Source/native3x3 contexts show handedness. The complete Emerald family is520/521/522 north,528/529/530 middle,536/537/538 south: continuous west/east sides use528/530, never the lower corners536/538. Exact source pixels, collision, palette slots and per8px priority checked, with explicit map scope. No diagonal, corner, water, ladder, exit or puzzle is inferred; native geometry and behavior remain unchanged.'
                candidates.append(row)
                if game=='crystal':samples.setdefault((ts,spec['pair'],role),(row,cell,data,definition))
    canvas=Image.new('RGB',(1340,72+len(samples)*134),'#18202c');draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    draw.text((14,12),'Gen2 cave '+('edge proposal: north rim / west side / east side / fixed boulder' if edges else 'terrain proposal: floor / raised-rock top / vertical rock front'),font=font,fill='white')
    draw.text((14,39),'Source shown with its native lit palette. Kanto uses the actual remake cave; Johto proposes native Granite Cave art.',fill='#ccd7e5')
    for index,(row,cell,data,definition) in enumerate(samples.values()):
        y=77+index*134
        source=source_image(args.cache,'crystal',data,cell,definition)
        target=preview.native_donor(args.cache,row['donor'],packed)
        canvas.paste(source.resize((96,96),Image.Resampling.NEAREST),(16,y))
        canvas.paste(target.resize((96,96),Image.Resampling.NEAREST),(755,y))
        draw.text((128,y+4),row['role'].replace('_',' '),font=font,fill='white')
        draw.text((128,y+29),f"{row['map']} {row['id']}:{row['quadrant']} / col0x{cell['collision']:02x}",fill='#ccd7e5')
        draw.text((128,y+51),f"raw{cell['tiles']} at {row['sourceCells'][0]}",fill='#ccd7e5')
        draw.text((870,y+7),f"{row['donor']['game']} {row['donor']['id']}",font=font,fill='white')
        draw.text((870,y+31),row['nativeContext']['map'],fill='#ccd7e5')
        draw.text((870,y+53),row['nativeContext']['contextKind'],fill='#e5ce9a')
    canvas.save(args.output/f'complete-{prefix}-source-native-proposal.png')
    if edges:edge_contexts(args,samples,native,packed)
    # Show unchanged neighbors: the proposal never shifts an edge into the
    # adjacent walkable ground or moves a native ladder/exit/warp.
    for name in ('MOUNT_MOON','ROCK_TUNNEL_1F','UNION_CAVE_1F'):
        data=ext.source(args.cache,'crystal');definition=data['maps'][name];selected={(r['id'],r['quadrant']):r for r in candidates if r['game']=='crystal' and r['map']==name}
        before=Image.open(args.output/f'crystal-{name}-lit-native.png').convert('RGBA');after=before.copy()
        for index,bid in enumerate(catalog.lua_array(definition['blocks'])):
            for q in range(4):
                row=selected.get((bid,q))
                if row:after.paste(preview.native_donor(args.cache,row['donor'],packed),(index%definition['width']*32+q%2*16,index//definition['width']*32+q//2*16))
        sheet=Image.new('RGB',(max(800,before.width*2+48),before.height+92),'#18202c');text=ImageDraw.Draw(sheet)
        text.text((14,12),f'{name}: only complete {prefix} roles proposed; all other pixels remain native',font=font,fill='white')
        text.text((14,44),'Native lit source',fill='#ccd7e5');text.text((before.width+34,44),'Private terrain proposal',fill='#ccd7e5')
        sheet.paste(before,(14,74));sheet.paste(after,(before.width+34,74));sheet.save(args.output/f'{name}-{prefix}-proposal-context.png')
    (args.output/f'{prefix}-candidates.json').write_text(json.dumps(candidates,indent=2),encoding='utf-8')
    (args.output/f'{prefix}-held.json').write_text(json.dumps(held,indent=2),encoding='utf-8')
    if args.validate_candidates:
        # Exercise the reviewed-row runtime path in a private fixture without
        # changing the proposals' pending-review state or any production file.
        probe=copy.deepcopy(candidates)
        for row in probe:row['status']='reviewed'
        proof=ext.validate_batch(probe,args,WORKSPACE/'TileShift')
        (args.output/f'{prefix}-candidate-runtime-checks.json').write_text(json.dumps({
            'scope':'Private candidate fixture only; visual review remains pending',
            'liveDonorCompositionSession':proof},indent=2),encoding='utf-8')
        print('Private candidate runtime fixture',proof)
    print('Private terrain candidates',len(candidates),'source occurrences',sum(len(r['sourceCells']) for r in candidates),'production rows written: 0')
    if args.write_reviewed:
        approved=copy.deepcopy(candidates)
        for row in approved:
            row['status']='reviewed';row['evidence']=row['evidence'].replace('Proposed complete16px','Visually reviewed complete16px',1)
        stats=ext.merge_reviewed(approved,WORKSPACE/'TileShift/mappings/gen2_caves.lua')
        (args.output/f'{prefix}-activation.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
        print('Approved cave activation',stats)


def ice_candidates(args):
    """Keep ordinary snowy ground, slippery ice and fixed boulders distinct."""
    game='firered';native_name='FR_FOUR_ISLAND_ICEFALL_CAVE_B1F'
    root=args.cache/game/'data/generated/gba/native';manifest=catalog.read_lua(root/'manifest.lua')
    spec=manifest['layouts'][native_name];layout=decode_layout(root/spec['file'])
    records={r['mid']:r for r in json.loads((WORKSPACE/'.work/tileshift-catalog/firered.json').read_text())['cells'] if r['pair']==spec['pair']}
    mids={'snowy_cave_floor':641,'sliding_ice_floor':843,'fixed_ice_boulder':642}
    for mid in mids.values():assert mid in layout['mids']
    assert records[843]['behavior_hint']=='MB_ICE'
    rows=[];samples={};packed={};crystal_data=None
    for game in ext.GAMES:
        data=ext.source(args.cache,game)
        if game=='crystal':crystal_data=data
        ts='TILESET_ICE_PATH'
        ice=ext.cell_info(args.cache,game,data,ts,31,0)
        rock=ext.cell_info(args.cache,game,data,ts,22,0)
        assert ice['tiles']==([198,199,214,215] if game=='crystal' else [8,24,24,8]) and ice['collision']==0x23
        assert rock['tiles']==([196,197,212,213] if game=='crystal' else [6,7,22,23]) and rock['collision']==0x07
        ground_tiles={18,25,154,155,170,171} if game=='crystal' else {18,25}
        ground_palette=7 if game=='crystal' else 6
        for name,definition in sorted(data['maps'].items()):
            if not isinstance(definition,dict) or definition.get('tileset')!=ts or definition.get('environment')!='CAVE':continue
            occurrences=defaultdict(list)
            for index,bid in enumerate(catalog.lua_array(definition['blocks'])):
                for q in range(4):occurrences[bid,q].append([index%definition['width']*2+q%2,index//definition['width']*2+q//2])
            for (bid,q),coords in sorted(occurrences.items()):
                cell=ext.cell_info(args.cache,game,data,ts,bid,q);role=None
                if ext.identity(cell)==ext.identity(ice):role='sliding_ice_floor'
                elif ext.identity(cell)==ext.identity(rock):role='fixed_ice_boulder'
                elif (cell['collision']==0 and set(cell['tiles'])<=ground_tiles
                      and all(a.get('palette')==ground_palette and not a.get('priority') for a in cell['attributes'])):
                    role='snowy_cave_floor'
                if not role:continue
                mid=mids[role]
                row={'game':game,'style':'gen3','map':name,'tileset':ts,'id':bid,'quadrant':q,
                     'role':role,'status':'candidate','sourceHash':cell['sourceHash'],
                     'sourceFiles':data['fingerprints'][ts],'sourceCollision':cell['collision'],'sourceCells':coords,
                     'sourcePriority':[bool(a.get('priority')) for a in cell['attributes']],
                     'sourcePalettes':[a.get('palette',1) for a in cell['attributes']],
                     'donor':{'game':'firered','tileset':spec['pair'],'id':mid,'hash':records[mid]['pixel_sha256']},
                     'nativeContext':{'map':native_name,'layoutFileHash':layout['file_sha256']},
                     'evidence':'Proposed full16px Ice Path terrain. Plain slippery ice preserves the exact complete reflected-stripe shape and native0x23 sliding role, using actual native Icefall hard ice843 rather than thin/cracked ice. Ordinary nonslippery snow-floor patches are only the displayed source8px ground textures (Gold/Silver18,25/palette6; Crystal18,25,154,155,170,171/palette7), no priority, and collision0. The complete16px fixed ice boulder is distinct from two-cell boulders, pushable sprites, walls, holes, ladders and exits. Every source variant and map scope has explicit pixel/behavior/palette/priority proof; source ice movement and puzzles remain unchanged.'}
                rows.append(row)
                samples.setdefault((role,cell['sourceHash']),(row,cell,definition,data))
    examples=[]
    for role in mids:
        selected=[v for (r,_),v in samples.items() if r==role]
        examples.extend(selected[:6] if role=='snowy_cave_floor' else selected)
    canvas=Image.new('RGB',(1280,72+len(examples)*132),'#18202c');draw=ImageDraw.Draw(canvas);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    draw.text((14,12),'Ice Path proposal: nonslippery snowy ground / hard sliding ice / fixed ice boulder',font=font,fill='white')
    draw.text((14,39),'All donor references are used in actual native FireRed Icefall Cave. Thin ice, holes, ladders and wider rock shapes are held.',fill='#ccd7e5')
    for i,(row,cell,definition,data) in enumerate(examples):
        y=77+i*132;source=source_image(args.cache,row['game'],data,cell,definition);target=preview.native_donor(args.cache,row['donor'],packed)
        canvas.paste(source.resize((96,96),Image.Resampling.NEAREST),(16,y));canvas.paste(target.resize((96,96),Image.Resampling.NEAREST),(740,y))
        draw.text((128,y+4),row['role'].replace('_',' '),font=font,fill='white')
        draw.text((128,y+29),f"{row['game']} {row['map']} {row['id']}:{row['quadrant']} / col0x{cell['collision']:02x}",fill='#ccd7e5')
        draw.text((128,y+51),f"raw{cell['tiles']} at {row['sourceCells'][0]}",fill='#ccd7e5')
        draw.text((852,y+7),f"FireRed Icefall {row['donor']['id']}",font=font,fill='white')
        draw.text((852,y+31),records[row['donor']['id']]['behavior_hint'],fill='#ccd7e5')
    canvas.save(args.output/'icepath-source-native-proposal.png')
    name='ICE_PATH_1F';definition=crystal_data['maps'][name];selected={(r['id'],r['quadrant']):r for r in rows if r['game']=='crystal' and r['map']==name}
    before=Image.open(args.output/f'crystal-{name}-lit-native.png').convert('RGBA');after=before.copy()
    for index,bid in enumerate(catalog.lua_array(definition['blocks'])):
        for q in range(4):
            row=selected.get((bid,q))
            if row:after.paste(preview.native_donor(args.cache,row['donor'],packed),(index%definition['width']*32+q%2*16,index//definition['width']*32+q//2*16))
    canvas=Image.new('RGB',(before.width*2+48,before.height+92),'#18202c');draw=ImageDraw.Draw(canvas)
    draw.text((14,12),'ICE_PATH_1F: three complete terrain roles only; geometry and every ice/puzzle state remain native',font=font,fill='white')
    draw.text((14,44),'Native source',fill='#ccd7e5');draw.text((before.width+34,44),'Private terrain proposal',fill='#ccd7e5')
    canvas.paste(before,(14,74));canvas.paste(after,(before.width+34,74));canvas.save(args.output/'ICE_PATH_1F-terrain-proposal-context.png')
    (args.output/'icepath-candidates.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    if args.validate_candidates:
        probe=copy.deepcopy(rows)
        for row in probe:row['status']='reviewed'
        proof=ext.validate_batch(probe,args,WORKSPACE/'TileShift')
        (args.output/'icepath-candidate-runtime-checks.json').write_text(json.dumps({
            'scope':'Private candidate fixture only; visual review remains pending','liveDonorCompositionSession':proof},indent=2),encoding='utf-8')
        print('Private ice candidate runtime fixture',proof)
    print('Private ice candidates',len(rows),'source occurrences',sum(len(r['sourceCells']) for r in rows),'production rows written: 0')
    if args.write_reviewed:
        approved=copy.deepcopy(rows)
        for row in approved:
            row['status']='reviewed';row['evidence']=row['evidence'].replace('Proposed full16px','Visually reviewed full16px',1)
        stats=ext.merge_reviewed(approved,WORKSPACE/'TileShift/mappings/gen2_caves.lua')
        (args.output/'icepath-activation.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
        print('Approved Ice Path activation',stats)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=Path(os.environ['APPDATA'])/'pokemon-love2d')
    parser.add_argument('--output',type=Path,default=WORKSPACE/'.work/tileshift-gen2-cave-review')
    parser.add_argument('--engine',type=Path,default=WORKSPACE/'.tools/engine-0395')
    parser.add_argument('--terrain-candidates',action='store_true',help='Prepare three-role proposals for visual review; no production writes')
    parser.add_argument('--ice-candidates',action='store_true',help='Prepare Ice Path complete-cell proposals; no production writes')
    parser.add_argument('--edge-candidates',action='store_true',help='Prepare cave edge/boulder context proposals; no production writes')
    parser.add_argument('--validate-candidates',action='store_true',help='Privately exercise candidate hashes/runtime without activating them')
    parser.add_argument('--write-reviewed',action='store_true',help='Merge the explicitly approved selected terrain/edge batch after live checks')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    if args.write_reviewed and (not args.validate_candidates or not (args.terrain_candidates or args.edge_candidates or args.ice_candidates)):
        parser.error('--write-reviewed requires a selected batch and --validate-candidates')
    inventory={};summary=[]
    for game in ext.GAMES:
        data=ext.source(args.cache,game);groups=defaultdict(dict)
        for name,definition in sorted(data['maps'].items()):
            if not isinstance(definition,dict) or definition.get('tileset') not in SETS or definition.get('environment')!='CAVE':continue
            ts=definition['tileset'];counts=Counter();scene=Image.new('RGBA',(definition['width']*32,definition['height']*32))
            for index,bid in enumerate(catalog.lua_array(definition['blocks'])):
                for q in range(4):
                    cell=ext.cell_info(args.cache,game,data,ts,bid,q);key=ext.identity(cell)
                    x,y=index%definition['width']*2+q%2,index//definition['width']*2+q//2
                    counts[key]+=1
                    if key not in groups[ts]:
                        groups[ts][key]={'seed':cell,'aliases':set(),'contexts':[], 'occurrences':0}
                    record=groups[ts][key];record['aliases'].add((bid,q));record['occurrences']+=1
                    warp=[w for w in catalog.lua_array(definition.get('warps',[])) if w['x']==x and w['y']==y]
                    if len(record['contexts'])<8 or warp:
                        record['contexts'].append({'map':name,'cell':[x,y],'source':[bid,q],
                            'palette':definition.get('palette'),'litDaytime':lit_daytime(definition),'warps':warp})
                    if game=='crystal' and name in SOURCE_SCENES:
                        scene.paste(source_image(args.cache,game,data,cell,definition),(x*16,y*16))
            summary.append({'game':game,'map':name,'tileset':ts,'palette':definition.get('palette'),
                            'litDaytime':lit_daytime(definition),'sourceCells':sum(counts.values()),'distinctCells':len(counts)})
            if game=='crystal' and name in SOURCE_SCENES:scene.save(args.output/f'{game}-{name}-lit-native.png')
        inventory[game]={}
        for ts,values in sorted(groups.items()):
            records=[];images=[]
            for n,record in enumerate(sorted(values.values(),key=lambda r:(-r['occurrences'],r['seed']['id'],r['seed']['quadrant']))):
                seed=record['seed'];record['aliases']=[list(a) for a in sorted(record['aliases'])]
                record.update(number=n,status='needs_visual_and_native_role_review');records.append(record)
                if game=='crystal':
                    context=record['contexts'][0];definition=data['maps'][context['map']]
                    raw='/'.join(str(t) for t in seed['tiles'])
                    label=f"#{n} {seed['id']}:{seed['quadrant']} x{record['occurrences']} col{seed['collision']:02x}\nraw {raw}\n{context['map'][:23]}"
                    images.append((label,source_image(args.cache,game,data,seed,definition)))
            inventory[game][ts]=records
            if game=='crystal':contact(args.output/f'crystal-{ts}-lit-source-contact.png',f'CRYSTAL {ts}: all {len(records)} used cell identities, lit native palette',images)
    packed={};native_summary=[];ladders=[]
    for game,names in NATIVE_SCENES.items():
        root=args.cache/game/'data/generated/gba/native';manifest=catalog.read_lua(root/'manifest.lua')
        all_records=json.loads((WORKSPACE/f'.work/tileshift-catalog/{game}.json').read_text())['cells']
        records={(r['pair'],r['mid']):r for r in all_records};warps=catalog.read_lua(args.cache/game/'data/generated/gba/warps.lua')
        for name in names:
            spec=manifest['layouts'][name];layout=decode_layout(root/spec['file']);scene=Image.new('RGBA',(layout['width']*16,layout['height']*16));tiles={}
            for index,mid in enumerate(layout['mids']):
                record=records[spec['pair'],mid]
                ref={'game':game,'tileset':spec['pair'],'id':mid,'hash':record['pixel_sha256']}
                tile=preview.native_donor(args.cache,ref,packed);tiles[mid]=tile
                scene.paste(tile,(index%layout['width']*16,index//layout['width']*16))
            scene.save(args.output/f'{game}-{name}-native.png')
            rows=[(f"{mid} {(records[spec['pair'],mid].get('behavior_hint') or 'NONE').removeprefix('MB_')}\nused {layout['mids'].count(mid)} cells",tiles[mid]) for mid in sorted(tiles)]
            contact(args.output/f'{game}-{name}-used-native-contact.png',f'{game.upper()} {name}: actual map cells / {spec["pair"]}',rows)
            native_summary.append({'game':game,'map':name,'pair':spec['pair'],'layoutHash':layout['file_sha256'],
                                   'dimensions':[layout['width'],layout['height']],'mids':sorted(tiles)})
            for warp in catalog.lua_array(warps[name]):
                mid=layout['mids'][warp['y']*layout['width']+warp['x']]
                if records[spec['pair'],mid].get('behavior_hint')!='MB_LADDER':continue
                ladders.append({'game':game,'map':name,'pair':spec['pair'],'mid':mid,'warp':warp})
                if game=='emerald' and name=='EM_GRANITE_CAVE_B1F':
                    x,y=warp['x'],warp['y'];crop=scene.crop(((x-1)*16,(y-1)*16,(x+2)*16,(y+2)*16))
                    crop.resize((384,384),Image.Resampling.NEAREST).save(args.output/f'emerald-ladder{mid}-at{x}-{y}-context.png')
    (args.output/'source-inventory.json').write_text(json.dumps(inventory,indent=2),encoding='utf-8')
    (args.output/'summary.json').write_text(json.dumps({'sources':summary,'nativeScenes':native_summary,'nativeLadders':ladders},indent=2),encoding='utf-8')
    print('Private source maps',len(summary),'cells',sum(r['sourceCells'] for r in summary),
          'native scenes',len(native_summary),'production rows written: 0')
    if args.terrain_candidates:terrain_candidates(args)
    if args.ice_candidates:ice_candidates(args)
    if args.edge_candidates:terrain_candidates(args,True)


if __name__=='__main__':main()
