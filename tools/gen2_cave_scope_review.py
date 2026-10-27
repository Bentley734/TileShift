"""Private extension of exact reviewed cave roles into additional Johto caves.

Only complete terrain and convex geometry already approved for the same source
pixels, movement byte, palette slot and priority qualify. Water, ladders,
entrances, inward corners, puzzles and special constructed chambers stay held.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
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
import gen2_cave_review as cave

HELD_SCENES={'BURNED_TOWER_B1F','DRAGONS_DEN_1F','SEAFOAM_GYM'}
ROLES={'cave_rock_floor','cave_raised_rock_plateau_top','cave_raised_rock_mass_front',
       'cave_raised_plateau_north_rim','cave_rock_mass_west_side','cave_rock_mass_east_side',
       'cave_fixed_small_boulder','cave_convex_northwest','cave_convex_northeast',
       'cave_convex_southwest','cave_convex_southeast'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=Path(os.environ['APPDATA'])/'pokemon-love2d')
    parser.add_argument('--engine',type=Path,default=WORKSPACE/'.tools/engine-0395')
    parser.add_argument('--output',type=Path,default=WORKSPACE/'.work/tileshift-gen2-cave-scope-review')
    parser.add_argument('--write-reviewed',action='store_true',help='Merge the explicitly approved exact-role scope extensions')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    mod=WORKSPACE/'TileShift';active=ext.active_rows(mod);rows=[];summaries=[];examples={};packed={}
    for game in ext.GAMES:
        data=ext.source(args.cache,game);known=defaultdict(dict)
        for original in active:
            donor=original.get('donor',{})
            if original['game']!=game or original['role']not in ROLES or donor.get('game')!='emerald' or donor.get('tileset')!='general__cave':continue
            cell=ext.cell_info(args.cache,game,data,original['tileset'],original['id'],original['quadrant'])
            key=ext.identity(cell);previous=known[original['tileset']].get(key)
            assert previous is None or previous['donor']==donor,'Ambiguous reviewed source identity'
            known[original['tileset']][key]=original
        for name,definition in sorted(data['maps'].items()):
            if not isinstance(definition,dict)or definition.get('tileset')not in known or definition.get('environment')!='CAVE':continue
            if name in cave.TERRAIN_CASES or name in HELD_SCENES:continue
            ts=definition['tileset'];mapped={(r['id'],r['quadrant'])for r in active
                if r['game']==game and r['tileset']==ts and r.get('map',name)==name and r.get('x')is None}
            occurrences=defaultdict(list)
            for i,bid in enumerate(catalog.lua_array(definition['blocks'])):
                for q in range(4):occurrences[bid,q].append([i%definition['width']*2+q%2,i//definition['width']*2+q//2])
            counts=Counter();current=[]
            for (bid,q),coords in sorted(occurrences.items()):
                if (bid,q)in mapped:continue
                cell=ext.cell_info(args.cache,game,data,ts,bid,q);template=known[ts].get(ext.identity(cell))
                if not template:continue
                row=copy.deepcopy(template)
                row.update(map=name,id=bid,quadrant=q,sourceHash=cell['sourceHash'],
                    sourceFiles=data['fingerprints'][ts],sourceCells=coords,status='candidate',
                    sourceCollision=cell['collision'],sourcePalettes=[a.get('palette',1)for a in cell['attributes']],
                    sourcePriority=[bool(a.get('priority'))for a in cell['attributes']])
                row['reviewedSourceTemplate']={'map':template['map'],'id':template['id'],
                    'quadrant':template['quadrant'],'sourceHash':template['sourceHash']}
                row['evidence']='Private regional scope extension of an already reviewed complete natural-cave role. Source rendered16px hash, exact movement byte, all palette slots and all priority bits equal the approved Johto template. Native Emerald Granite Cave supplies the same reviewed material and complete topology; continuous sides528/530 and convex corners520/522/536/538 are distinct. Explicit additional map scope is shown in the full source context. Water, waterfalls, ladders, entrances, inward corners, small32px plateaus and puzzles remain original. Source geometry and behavior are unchanged; unlit Flash caves keep native darkness until Flash.'
                rows.append(row);current.append(row);counts[row['role']]+=len(coords)
            if current:
                summaries.append({'game':game,'map':name,'palette':definition.get('palette'),
                    'rows':len(current),'sourceCells':sum(counts.values()),'roles':dict(counts)})
                if game=='crystal':examples[name]=(data,definition,current)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    for name,(data,definition,current)in examples.items():
        before=Image.new('RGBA',(definition['width']*32,definition['height']*32));after=before.copy()
        selected={(r['id'],r['quadrant']):r for r in current}
        for i,bid in enumerate(catalog.lua_array(definition['blocks'])):
            for q in range(4):
                cell=ext.cell_info(args.cache,'crystal',data,definition['tileset'],bid,q)
                source=cave.source_image(args.cache,'crystal',data,cell,definition)
                xy=(i%definition['width']*32+q%2*16,i//definition['width']*32+q//2*16)
                before.paste(source,xy)
                after.paste(preview.replacement_image(args.cache,selected[bid,q],packed,mod)if(bid,q)in selected else source,xy)
        # Keep full resolution: these are local QA references, never release art.
        sheet=Image.new('RGB',(max(1100,before.width*2+48),before.height+100),'#18202c');d=ImageDraw.Draw(sheet)
        d.text((14,12),f'{name}: exact reviewed natural-cave role repeats; all other source pixels remain original',font=font,fill='white')
        d.text((14,42),'Left: native source after Flash where applicable. Right: private terrain/convex-only proposal; water, ladders and puzzles are held.',fill='#ccd7e5')
        sheet.paste(before,(14,76));sheet.paste(after,(before.width+34,76));sheet.save(args.output/f'{name}-review.png')
    probe=copy.deepcopy(rows)
    for row in probe:row['status']='reviewed'
    validation=ext.validate_batch(probe,args,mod)
    (args.output/'candidates.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    (args.output/'scope-summary.json').write_text(json.dumps(summaries,indent=2),encoding='utf-8')
    (args.output/'runtime-checks.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
    print('Private additional cave scopes:',len(examples),'maps,',len(rows),'rows,',sum(len(r['sourceCells'])for r in rows),'source cells;',validation,'production writes: 0')
    if args.write_reviewed:
        approved=copy.deepcopy(rows)
        for row in approved:
            row['status']='reviewed';row['evidence']=row['evidence'].replace('Private regional scope extension','Visually reviewed regional scope extension',1)
        target=mod/'mappings/gen2_caves.lua';stats=ext.merge_reviewed(approved,target)
        live=ext.validate_batch(preview.read_reviewed(target),args,mod)
        (args.output/'approved-activation.json').write_text(json.dumps({'file':stats,'live':live},indent=2),encoding='utf-8')
        print('Approved cave scope activation:',stats,live)


if __name__=='__main__':main()
