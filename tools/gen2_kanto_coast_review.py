"""Private GSC Pallet sea-inlet comparison against the actual FRLG remake.

The16 native source water cells occupy the same coordinates and oriented bank
roles as Red's reviewed Pallet inlet. Source pixels, palettes, collision and
priority are independently checked for Gold, Silver and Crystal. Production
writes require --write-reviewed; no other regional water is inferred here.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
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

RAW={
    'coastal_rock_shore_northwest':(51,51,51,20),
    'coastal_rock_shore_north':(51,51,20,20),
    'coastal_rock_shore_northeast':(51,51,20,84),
    'coastal_rock_shore_west':(51,20,51,20),
    'coastal_rock_shore_east':(20,84,20,84),
    'coastal_ocean_water_interior':(20,20,20,20),
}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=Path(os.environ['APPDATA'])/'pokemon-love2d')
    parser.add_argument('--engine',type=Path,default=WORKSPACE/'.tools/engine-0395')
    parser.add_argument('--output',type=Path,default=WORKSPACE/'.work/tileshift-gen2-kanto-water-review')
    parser.add_argument('--write-reviewed',action='store_true',help='Merge the approved Pallet inlet after all live checks')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    mod=WORKSPACE/'TileShift';old=ext.active_rows(mod)
    templates={(r['id'],r['quadrant']):r for r in old if r['game']=='red' and r.get('map')=='PALLET_TOWN' and r['role'] in RAW}
    definition=catalog.read_lua(args.cache/'red/data/generated/maps.lua')['PALLET_TOWN'];at={}
    for i,bid in enumerate(catalog.lua_array(definition['blocks'])):
        for q in range(4):
            if (bid,q) in templates:at[i%definition['width']*2+q%2,i//definition['width']*2+q//2]=templates[bid,q]
    assert len(at)==16
    rows=[];samples={};packed={}
    for game in ext.GAMES:
        data=ext.source(args.cache,game);definition=data['maps']['PALLET_TOWN'];ts=definition['tileset'];occurrences=defaultdict(list)
        assert ts=='TILESET_KANTO'
        for i,bid in enumerate(catalog.lua_array(definition['blocks'])):
            for q in range(4):
                cell=ext.cell_info(args.cache,game,data,ts,bid,q)
                if cell['collision']==0x29:occurrences[bid,q].append((i%definition['width']*2+q%2,i//definition['width']*2+q//2))
        assert sum(len(v) for v in occurrences.values())==16
        for (bid,q),coords in sorted(occurrences.items()):
            assert all(xy in at for xy in coords)
            roles={at[xy]['role'] for xy in coords};assert len(roles)==1
            role=next(iter(roles));template=at[coords[0]];cell=ext.cell_info(args.cache,game,data,ts,bid,q)
            assert tuple(cell['tiles'])==RAW[role] and not any(a.get('priority') for a in cell['attributes'])
            row=copy.deepcopy(template)
            row.update(game=game,tileset=ts,id=bid,quadrant=q,status='candidate',sourceHash=cell['sourceHash'],
                       sourceFiles=data['fingerprints'][ts],sourceCollision=cell['collision'],sourceCells=[list(xy) for xy in coords],
                       sourcePriority=[bool(a.get('priority')) for a in cell['attributes']],
                       sourcePalettes=[a.get('palette',1) for a in cell['attributes']])
            row['evidence']=f'Proposed GSC Pallet sea inlet only. Actual {game} source cell shape,0x29water collision, per8px palette/priority and map coordinates{coords} checked independently. The inlet retains the same oriented NW/N/NE/W/E/full-water roles and exact16-cell footprint as native Red Pallet; actual FR Pallet supplies its matching regional graphics. The existing reviewed FR water bank, all8frames,16tick period/phase1 and decoded bank/manifest hashes are retained. No inland/other-region water is inferred. Surf, encounters, collisions, map connections and events remain native.'
            rows.append(row)
            if game=='crystal':samples.setdefault(role,(row,cell,data,definition))
    canvas=Image.new('RGB',(1480,80+len(samples)*132),'#18202c');draw=ImageDraw.Draw(canvas);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    draw.text((14,12),'GSC Pallet sea inlet: exact same regional counterpart, original16-cell shoreline footprint',font=font,fill='white')
    draw.text((14,40),'Native GSC source at left; all8 actual FR Pallet water frames at right. Each shore keeps its material and orientation.',fill='#ccd7e5')
    for i,(row,cell,data,definition) in enumerate(samples.values()):
        y=86+i*132;source=ext.source_image(args.cache,'crystal',data,cell,definition)
        canvas.paste(source.resize((96,96),Image.Resampling.NEAREST),(16,y))
        draw.text((128,y+4),row['role'].replace('coastal_','').replace('_',' '),font=font,fill='white')
        draw.text((128,y+31),f"Source {row['id']}:{row['quadrant']} raw{cell['tiles']}",fill='#ccd7e5')
        draw.text((128,y+53),f"Pallet {row['sourceCells']} / native col0x29",fill='#ccd7e5')
        frames=preview.native_water_frames(args.cache,row,packed);assert len(frames)==8
        for n,frame in enumerate(frames):
            x=650+n*100;canvas.paste(frame.resize((96,96),Image.Resampling.NEAREST),(x,y))
            draw.text((x,y+99),f"{row['donor']['id']} / frame{n}",fill='#ccd7e5')
    canvas.save(args.output/'pallet-kanto-source-native-all-frames.png')
    (args.output/'pallet-kanto-water-candidates.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    probe=copy.deepcopy(rows)
    for row in probe:row['status']='reviewed'
    proof=ext.validate_batch(probe,args,mod)
    (args.output/'candidate-runtime-checks.json').write_text(json.dumps({
        'scope':'Private candidate fixture only; visual review remains pending','liveDonorCompositionSession':proof},indent=2),encoding='utf-8')
    preview.map_preview(args.cache,args.output,'crystal','PALLET_TOWN','pallet-crystal-coast-proposal',old+rows,packed,1,mod)
    print('Private Pallet coast rows',len(rows),'source occurrences',sum(len(r['sourceCells']) for r in rows),proof,'production writes: 0')
    if args.write_reviewed:
        for row in probe:row['evidence']=row['evidence'].replace('Proposed GSC','Visually reviewed GSC',1)
        stats=ext.merge_reviewed(probe,mod/'mappings/gen2_outdoor_extended.lua')
        (args.output/'activation.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
        print('Approved GSC Pallet coast activation',stats)


if __name__=='__main__':main()
