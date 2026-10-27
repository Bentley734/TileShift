"""Private ocean-context repeats of reviewed New Bark water and rock banks.

Source geometry, behavior, palette slots and priority must exactly match the
reviewed New Bark references. Additional coast directions and inland water are
not inferred. No production data is written.
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

SCENES=('CHERRYGROVE_CITY','ROUTE_34','ROUTE_40','ROUTE_41','CIANWOOD_CITY','OLIVINE_CITY')
# Explicit map-context ocean regions. Cherrygrove's northeast Route30 pond
# and Route34's east-side inland water must not inherit marine wave art just
# because their uncolored water cells share the same source fingerprint.
OCEAN_BOUNDS={'CHERRYGROVE_CITY':(0,4,17,17),'ROUTE_34':(0,0,7,43),
              'ROUTE_40':(0,0,19,35),'ROUTE_41':(0,0,49,53),
              'CIANWOOD_CITY':(0,0,29,53),'OLIVINE_CITY':(0,14,39,35)}
ROLES={'rocky_coast_northwest','rocky_coast_north','rocky_coast_west','coastal_ocean_water_interior'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=Path(os.environ['APPDATA'])/'pokemon-love2d')
    parser.add_argument('--engine',type=Path,default=WORKSPACE/'.tools/engine-0395')
    parser.add_argument('--output',type=Path,default=WORKSPACE/'.work/tileshift-gen2-coastal-scope-review')
    parser.add_argument('--write-reviewed',action='store_true',help='Merge the reviewed explicit ocean regions and source equivalents')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    mod=WORKSPACE/'TileShift';active=ext.active_rows(mod);rows=[];summaries=[];examples={};packed={}
    for game in ext.GAMES:
        data=ext.source(args.cache,game);known={}
        for original in active:
            if original['game']!=game or original.get('map')!='NEW_BARK_TOWN' or original['role']not in ROLES:continue
            cell=ext.cell_info(args.cache,game,data,original['tileset'],original['id'],original['quadrant'])
            key=ext.identity(cell)
            if key in known:assert known[key]['donor']==original['donor']
            known[key]=original
        assert {r['role']for r in known.values()}==ROLES
        for name in SCENES:
            definition=data['maps'][name];ts=definition['tileset'];occurrences=defaultdict(list)
            bounds=OCEAN_BOUNDS[name]
            mapped={(r['id'],r['quadrant'])for r in active if r['game']==game and r['tileset']==ts
                    and r.get('map',name)==name and r.get('x')is None}
            for i,bid in enumerate(catalog.lua_array(definition['blocks'])):
                for q in range(4):occurrences[bid,q].append([i%definition['width']*2+q%2,i//definition['width']*2+q//2])
            current=[];counts=Counter()
            for (bid,q),coords in sorted(occurrences.items()):
                if (bid,q)in mapped:continue
                cell=ext.cell_info(args.cache,game,data,ts,bid,q);template=known.get(ext.identity(cell))
                if not template:continue
                eligible=[xy for xy in coords if bounds[0]<=xy[0]<=bounds[2]and bounds[1]<=xy[1]<=bounds[3]]
                if not eligible:continue
                row=copy.deepcopy(template)
                row.update(map=name,tileset=ts,id=bid,quadrant=q,sourceHash=cell['sourceHash'],
                    sourceFiles=data['fingerprints'][ts],sourceCells=coords,status='candidate',sourceCollision=cell['collision'],
                    sourcePalettes=[a.get('palette',1)for a in cell['attributes']],
                    sourcePriority=[bool(a.get('priority'))for a in cell['attributes']])
                row['sourceOceanBounds']=list(bounds)
                row['evidence']='Private explicit ocean-region repetition of the approved New Bark counterpart. Exact rendered16px source hash, movement byte, palette slots and priority equal the reviewed water/NW/N/W rock-bank template. Actual complete source map and sourceOceanBounds identify the sea body; Cherrygrove northeast Route30 pond and Route34 east-side inland water are excluded. Shared source keys crossing a sea/inland boundary use explicit source-cell coordinates. All eight native Emerald frames retain their reviewed bank/manifest fingerprints and phase. No additional shore direction, pond, pier, current or waterfall is inferred. Original Surf, fishing, encounters, map geometry and all events remain native.'
                variants=[row]
                if len(eligible)!=len(coords):
                    variants=[]
                    for x,y in eligible:
                        positioned=copy.deepcopy(row);positioned.update(x=x,y=y,sourceCells=[[x,y]])
                        variants.append(positioned)
                for variant in variants:
                    rows.append(variant);current.append(variant);counts[variant['role']]+=len(variant['sourceCells'])
            summaries.append({'game':game,'map':name,'tileset':ts,'rows':len(current),'sourceCells':sum(counts.values()),
                'roles':dict(counts),'nativeConnections':definition.get('connections')})
            if game=='crystal':examples[name]=(data,definition,current)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    for name,(data,definition,current)in examples.items():
        before=Image.new('RGBA',(definition['width']*32,definition['height']*32));after=before.copy()
        selected={(r['id'],r['quadrant'],r.get('x'),r.get('y')):r for r in current}
        for i,bid in enumerate(catalog.lua_array(definition['blocks'])):
            for q in range(4):
                cell=ext.cell_info(args.cache,'crystal',data,definition['tileset'],bid,q)
                source=ext.source_image(args.cache,'crystal',data,cell,definition)
                xy=(i%definition['width']*32+q%2*16,i//definition['width']*32+q//2*16)
                before.paste(source,xy)
                cx,cy=xy[0]//16,xy[1]//16
                replacement=selected.get((bid,q,cx,cy))or selected.get((bid,q,None,None))
                after.paste(preview.replacement_image(args.cache,replacement,packed,mod)if replacement else source,xy)
        sheet=Image.new('RGB',(max(1150,before.width*2+48),before.height+100),'#18202c');d=ImageDraw.Draw(sheet)
        d.text((14,12),f'{name}: ocean-water interior and exact reviewed NW/N/W rock-bank shapes only',font=font,fill='white')
        d.text((14,42),'Original source / private counterpart proposal. Native donor animations shown at frame0; yellow box marks the explicit marine region.',fill='#ccd7e5')
        sheet.paste(before,(14,76));sheet.paste(after,(before.width+34,76))
        bounds=OCEAN_BOUNDS[name]
        for ox in (14,before.width+34):
            d.rectangle((ox+bounds[0]*16,76+bounds[1]*16,ox+(bounds[2]+1)*16-1,76+(bounds[3]+1)*16-1),outline='#fff293',width=2)
        sheet.save(args.output/f'{name}-review.png')
    probe=copy.deepcopy(rows)
    for row in probe:row['status']='reviewed'
    validation=ext.validate_batch(probe,args,mod)
    frames_sheet=Image.new('RGB',(1430,70+len(ROLES)*130),'#18202c');d=ImageDraw.Draw(frames_sheet)
    d.text((14,12),'All eight already-reviewed native frames: each counterpart retains the same complete shoreline geometry',font=font,fill='white')
    for i,role in enumerate(sorted(ROLES)):
        row=next(r for r in rows if r['game']=='crystal' and r['role']==role)
        frames=preview.native_water_frames(args.cache,row,packed);assert len(frames)==8
        y=72+i*130;d.text((14,y),role.replace('_',' '),font=font,fill='white')
        for j,frame in enumerate(frames):frames_sheet.paste(frame.resize((80,80),Image.Resampling.NEAREST),(450+j*116,y))
    frames_sheet.save(args.output/'all-eight-reviewed-native-frames.png')
    (args.output/'candidates.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    (args.output/'scope-summary.json').write_text(json.dumps(summaries,indent=2),encoding='utf-8')
    (args.output/'runtime-checks.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
    print('Private coastal roles:',len(rows),'rows,',sum(len(r['sourceCells'])for r in rows),'source cells;',validation,'production writes: 0')
    if args.write_reviewed:
        approved=copy.deepcopy(rows)
        for row in approved:
            row['status']='reviewed';row['evidence']=row['evidence'].replace('Private explicit ocean-region repetition','Visually reviewed explicit ocean-region repetition',1)
        target=mod/'mappings/gen2_outdoor_extended.lua';stats=ext.merge_reviewed(approved,target)
        live=ext.validate_batch(preview.read_reviewed(target),args,mod)
        (args.output/'approved-activation.json').write_text(json.dumps({'file':stats,'live':live},indent=2),encoding='utf-8')
        print('Approved coastal scope activation:',stats,live)


if __name__=='__main__':main()
