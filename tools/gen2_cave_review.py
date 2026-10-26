"""Private Gen2 cave inventory and native Gen3 context; no production writes.

Dark caves are pictured after native Flash (NITE), because the runtime keeps
the original source darkness and entrance flicker before Flash. These contacts
are references for visual review, never collision-only automatic substitutions.
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


def terrain_candidates(args):
    """Only three complete roles; source geometry/palette/priority are gated.

    This remains a proposal. Native cave side walls, diagonal banks, ladders,
    exits, water, ice and puzzle objects are deliberately not inferred here.
    """
    candidates=[];held=[];samples={};packed={};native={}
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
            for role,cave_seed,dark_seed,raw,collision,fr_mid,em_mid in TERRAIN_ROLES:
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
                candidates.append(row)
                if game=='crystal':samples.setdefault((ts,spec['pair'],role),(row,cell,data,definition))
    canvas=Image.new('RGB',(1340,72+len(samples)*134),'#18202c');draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    draw.text((14,12),'Gen2 cave terrain proposal: complete floor / raised-rock top / vertical rock front',font=font,fill='white')
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
    canvas.save(args.output/'complete-terrain-source-native-proposal.png')
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
        text.text((14,12),f'{name}: only three complete terrain roles proposed; all other pixels remain native',font=font,fill='white')
        text.text((14,44),'Native lit source',fill='#ccd7e5');text.text((before.width+34,44),'Private terrain proposal',fill='#ccd7e5')
        sheet.paste(before,(14,74));sheet.paste(after,(before.width+34,74));sheet.save(args.output/f'{name}-terrain-proposal-context.png')
    (args.output/'terrain-candidates.json').write_text(json.dumps(candidates,indent=2),encoding='utf-8')
    (args.output/'terrain-held.json').write_text(json.dumps(held,indent=2),encoding='utf-8')
    if args.validate_candidates:
        # Exercise the reviewed-row runtime path in a private fixture without
        # changing the proposals' pending-review state or any production file.
        probe=copy.deepcopy(candidates)
        for row in probe:row['status']='reviewed'
        proof=ext.validate_batch(probe,args,WORKSPACE/'TileShift')
        (args.output/'terrain-candidate-runtime-checks.json').write_text(json.dumps({
            'scope':'Private candidate fixture only; visual review remains pending',
            'liveDonorCompositionSession':proof},indent=2),encoding='utf-8')
        print('Private candidate runtime fixture',proof)
    print('Private terrain candidates',len(candidates),'source occurrences',sum(len(r['sourceCells']) for r in candidates),'production rows written: 0')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=Path(os.environ['APPDATA'])/'pokemon-love2d')
    parser.add_argument('--output',type=Path,default=WORKSPACE/'.work/tileshift-gen2-cave-review')
    parser.add_argument('--engine',type=Path,default=WORKSPACE/'.tools/engine-0395')
    parser.add_argument('--terrain-candidates',action='store_true',help='Prepare three-role proposals for visual review; no production writes')
    parser.add_argument('--validate-candidates',action='store_true',help='Privately exercise candidate hashes/runtime without activating them')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
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


if __name__=='__main__':main()
