"""Private inland-pond equivalence review; never writes production mappings."""
from __future__ import annotations
import argparse
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

TARGETS={'northwest_bank':421,'north_bank':422,'northeast_bank':423,'west_bank':429,'interior':430,'east_bank':431}
SEEDS={'TILESET_JOHTO':{'northwest_bank':(84,0),'north_bank':(84,1),'northeast_bank':(85,1),
                       'west_bank':(84,2),'interior':(84,3),'east_bank':(85,3)},
       'TILESET_FOREST':{'northwest_bank':(7,0),'north_bank':(7,1),'northeast_bank':(13,0),
                        'west_bank':(7,2),'interior':(7,3),'east_bank':(13,3)}}
MAPS=('ROUTE_30','ROUTE_31','ILEX_FOREST')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=Path(os.environ['APPDATA'])/'pokemon-love2d')
    parser.add_argument('--engine',type=Path,default=WORKSPACE/'.tools/engine-0395')
    parser.add_argument('--output',type=Path,default=WORKSPACE/'.work/tileshift-gen2-water-review')
    args=parser.parse_args();args.output.mkdir(exist_ok=True,parents=True)
    mod=WORKSPACE/'TileShift';old=ext.active_rows(mod)
    native={r['mid']:r for r in json.loads((WORKSPACE/'.work/tileshift-catalog/firered.json').read_text())['cells'] if r['pair']=='viridian_outdoor'}
    rows=[];samples={};coverage=[]
    for game in ext.GAMES:
        data=ext.source(args.cache,game)
        for name in MAPS:
            definition=data['maps'][name];ts=definition['tileset'];roles={}
            for role,(bid,q) in SEEDS[ts].items():
                cell=ext.cell_info(args.cache,game,data,ts,bid,q)
                assert cell['collision']==0x29
                roles[ext.identity(cell)]=role
            selected={(r['id'],r['quadrant']) for r in old if r['game']==game and r['tileset']==ts and r.get('map',name)==name}
            occurrences={}
            for index,bid in enumerate(definition['blocks']):
                for q in range(4):occurrences.setdefault((bid,q),[]).append([index%definition['width']*2+q%2,index//definition['width']*2+q//2])
            count=0
            for (bid,q),coords in sorted(occurrences.items()):
                cell=ext.cell_info(args.cache,game,data,ts,bid,q);role=roles.get(ext.identity(cell))
                if not role or (bid,q) in selected:continue
                mid=TARGETS[role];donor={'game':'firered','tileset':'viridian_outdoor','id':mid,'hash':native[mid]['pixel_sha256']}
                assert native[mid]['behavior_hint']=='MB_POND_WATER'
                row={'game':game,'style':'gen3','map':name,'tileset':ts,'id':bid,'quadrant':q,
                     'role':'freshwater_pond_'+role,'status':'reviewed','sourceHash':cell['sourceHash'],
                     'sourceFiles':data['fingerprints'][ts],'sourceCollision':cell['collision'],'sourceCells':coords,
                     'sourcePriority':[bool(a.get('priority')) for a in cell['attributes']],
                     'sourcePalettes':[a.get('palette',1) for a in cell['attributes']],
                     'donor':donor,'sourceBody':'enclosed inland pond',
                     'evidence':f'Explicit inland pond in {name}; exact native source shape, brown rocky-bank material, orientation, collision0x29 and per8px priority checked. The actual FRLG Viridian pond bank family provides the complete same-role16px graphic. Native pond mids421/422/423/429/430/431 are static and absent from animation banks; existing native640tick pond proof is retained. Coastal/ocean animation and bridge/pier art are excluded. Source water encounters, Surf, collisions and map geometry remain untouched.'}
                rows.append(row);count+=len(coords)
                if game=='crystal':samples.setdefault((ts,role),(row,cell,definition,data))
            coverage.append({'game':game,'map':name,'new_pond_cells':count})
    canvas=Image.new('RGB',(1320,60+len(samples)*150),'#18202c');draw=ImageDraw.Draw(canvas);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17);packed={}
    draw.text((15,12),'Gen2 enclosed inland ponds: rocky banks, exact orientation and native static freshwater art',font=font,fill='white')
    draw.text((15,40),'Source and donor are full16px cells. Native actual FR pond family is separate from ocean-wave banks and wooden piers.',fill='#ccd7e5')
    for index,(row,cell,definition,data) in enumerate(samples.values()):
        y=65+index*150;source=ext.source_image(args.cache,'crystal',data,cell,definition);target=preview.native_donor(args.cache,row['donor'],packed)
        canvas.paste(source.resize((104,104),Image.Resampling.NEAREST),(20,y+15));canvas.paste(target.resize((104,104),Image.Resampling.NEAREST),(800,y+15))
        draw.text((140,y+15),row['role'].replace('_',' '),font=font,fill='white')
        draw.text((140,y+40),f"{row['map']} / {row['tileset']} {row['id']}:{row['quadrant']}",fill='#ccd7e5')
        draw.text((140,y+61),f"Source {cell['tiles']} at {row['sourceCells'][0]} / col0x29",fill='#ccd7e5')
        draw.text((920,y+30),f"Native FR Viridian {row['donor']['id']}",fill='white')
        draw.text((920,y+54),'POND_WATER / static native art',fill='#e5ce9a')
    canvas.save(args.output/'inland-pond-source-native-review.png')
    validation=ext.validate_batch(rows,args,mod)
    (args.output/'inland-pond-candidates.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    (args.output/'inland-pond-validation.json').write_text(json.dumps({'live':validation,'maps':coverage},indent=2),encoding='utf-8')
    for name in MAPS:preview.map_preview(args.cache,args.output,'crystal',name,f'pond-crystal-{name}',old+rows,packed,1,mod)
    print('Private pond rows',len(rows),'water cells',sum(r['new_pond_cells'] for r in coverage),validation)


if __name__=='__main__':main()
