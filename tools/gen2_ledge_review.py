"""Privately distinguish Gen2 ledge-approach ground from visible cliff art.

The native hop byte belongs to the ordinary ground before the refused step.
This review maps only exact complete ground glyphs; neighboring cliff art and
every native movement byte remain unchanged. Production writes require the
explicit --write-reviewed flag for the approved approach-ground batch.
"""
from __future__ import annotations
import argparse
import copy
import json
import os
from pathlib import Path
import sys

WORKSPACE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(WORKSPACE/'.tools/python'))
from PIL import Image,ImageDraw,ImageFont
from lupa.luajit21 import LuaRuntime
import catalog
import preview
import gen2_extended_review as ext


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=Path(os.environ['APPDATA'])/'pokemon-love2d')
    parser.add_argument('--engine',type=Path,default=WORKSPACE/'.tools/engine-0395')
    parser.add_argument('--output',type=Path,default=WORKSPACE/'.work/tileshift-gen2-ledge-review')
    parser.add_argument('--write-reviewed',action='store_true',help='Merge the approved approach-ground batch after live checks')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    before=Path.cwd()
    try:
        os.chdir(args.engine.resolve());lua=LuaRuntime(unpack_returned_tuples=True)
        facings=lua.execute("local V=require('src.core.GameVersion');local P=require('src.world.gen2.Permissions');return function(game,coll)V.set(game);return P.ledgeFacings(coll)end")
    finally:os.chdir(before)
    mod=WORKSPACE/'TileShift';old=ext.active_rows(mod);rows=[];examples={};summaries=[]
    for game in ext.GAMES:
        data=ext.source(args.cache,game);known={}
        for row in old:
            if row['game']==game and row['tileset'] in ext.SETS and row['role'] in {'short_nonencounter_grass','open_grassy_ground'}:
                cell=ext.cell_info(args.cache,game,data,row['tileset'],row['id'],row['quadrant'])
                key=(cell['sourceHash'],ext.identity(cell)[2]);known[key]=row
        for name,definition in sorted(data['maps'].items()):
            if not isinstance(definition,dict) or definition.get('tileset') not in ext.SETS:continue
            if definition.get('environment')=='CAVE' and name!='ILEX_FOREST':continue
            ts=definition['tileset'];selected={}
            for row in old:
                if row['game']==game and row['tileset']==ts and row.get('map',name)==name:selected[row['id'],row['quadrant']]=row
            grid={};occurrences={}
            for index,bid in enumerate(catalog.lua_array(definition['blocks'])):
                for q in range(4):
                    xy=(index%definition['width']*2+q%2,index//definition['width']*2+q//2)
                    cell=ext.cell_info(args.cache,game,data,ts,bid,q);grid[xy]=cell
                    occurrences.setdefault((bid,q),[]).append(xy)
            count=0
            for (bid,q),coords in sorted(occurrences.items()):
                cell=grid[coords[0]]
                if not 0xa0<=cell['collision']<=0xa7 or (bid,q) in selected:continue
                template=known.get((cell['sourceHash'],ext.identity(cell)[2]))
                if not template:continue
                directions=sorted(name for name,yes in facings(game,cell['collision']).items() if yes)
                assert directions
                row=copy.deepcopy(template)
                row.update(game=game,tileset=ts,map=name,id=bid,quadrant=q,role='ledge_approach_ground',
                           sourceHash=cell['sourceHash'],sourceFiles=data['fingerprints'][ts],sourceCollision=cell['collision'],
                           sourceCells=[list(c) for c in coords],sourceHopDirections=directions,
                           sourcePriority=[bool(a.get('priority')) for a in cell['attributes']],
                           sourcePalettes=[a.get('palette',1) for a in cell['attributes']])
                row['evidence']='Complete plain grass/ground graphic at a native Gen2 hop approach. Source glyph, palette slots and priority exactly match the reviewed normal-ground counterpart. Actual Permissions.ledgeFacings supplies sourceHopDirections. Gen2 places this marker on the ground before a refused neighboring step; visible cliff/bank graphics occupy separate source cells and are not moved into this cell. All native jump directions, side-wall checks, collisions and movement behavior remain unchanged.'
                rows.append(row);count+=len(coords)
                if game=='crystal':examples.setdefault((cell['sourceHash'],cell['collision'],ts),(row,cell,definition,data,grid))
            if count:summaries.append({'game':game,'map':name,'approach_cells':count})
    columns=2;cw,ch=720,270
    canvas=Image.new('RGB',(columns*cw,65+((len(examples)+1)//2)*ch),'#18202c');draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17)
    draw.text((15,12),'Gen2 ledge-approach ground: native direction and visible cliff positions remain exact',font=font,fill='white')
    draw.text((15,40),'Left: native3x3 context. Right: replace only the boxed16px approach ground; every neighboring source pixel stays in place.',fill='#ccd7e5')
    for index,(row,cell,definition,data,grid) in enumerate(examples.values()):
        ox,oy=index%columns*cw+15,index//columns*ch+70;x,y=row['sourceCells'][0]
        context=Image.new('RGBA',(48,48))
        for dy in range(-1,2):
            for dx in range(-1,2):
                other=grid.get((x+dx,y+dy))
                if other:context.paste(ext.source_image(args.cache,'crystal',data,other,definition),((dx+1)*16,(dy+1)*16))
        revised=context.copy();revised.paste(preview.replacement_image(args.cache,row,{},mod),(16,16))
        for column,image in enumerate((context,revised)):
            px,py=ox+column*212,oy+45
            canvas.paste(image.resize((192,192),Image.Resampling.NEAREST),(px,py))
            draw.rectangle((px+64,py+64,px+127,py+127),outline='#fff293',width=2)
        draw.text((ox,oy),f"{row['map']} {row['id']}:{row['quadrant']} at({x},{y}) / 0x{cell['collision']:02x}",font=font,fill='white')
        draw.text((ox+435,oy+55),'Native hop:',fill='#ccd7e5')
        draw.text((ox+435,oy+75),', '.join(row['sourceHopDirections']),fill='#e5ce9a')
        draw.text((ox+435,oy+105),'Complete ground glyph',fill='#ccd7e5')
        draw.text((ox+435,oy+125),str(cell['tiles']),fill='#ccd7e5')
        draw.text((ox+435,oy+155),'Visible edge stays',fill='#ccd7e5')
        draw.text((ox+435,oy+175),'in its source cell.',fill='#ccd7e5')
    canvas.save(args.output/'native-ledge-approach-context.png')
    validation=ext.validate_batch(rows,args,mod)
    (args.output/'candidate-approach-rows.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    (args.output/'validation.json').write_text(json.dumps({'live':validation,'maps':summaries},indent=2),encoding='utf-8')
    print('Private rows',len(rows),'source cells',sum(r['approach_cells'] for r in summaries),validation)
    if args.write_reviewed:
        stats=ext.merge_reviewed(rows,mod/'mappings/gen2_outdoor_extended.lua')
        (args.output/'activation.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
        print('Approved approach-ground activation',stats)


if __name__=='__main__':main()
