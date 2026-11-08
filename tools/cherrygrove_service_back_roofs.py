"""Restore complete Cherrygrove service roofs beyond the north map edge.

Copy the same unscaled roof modules used by the corresponding Violet City
buildings. The decorative row uses a fingerprinted first-row source anchor;
the native map, entrances, collisions and neighboring-map layout stay intact.
"""
from pathlib import Path
import argparse, copy, json, os, sys
from types import SimpleNamespace

HERE=Path(__file__).resolve()
WORKSPACE=next(p for p in [Path.cwd(),*HERE.parents] if (p/'.tools/python').is_dir())
sys.path[:0]=[str(WORKSPACE/'.tools/python')]
import catalog, preview, gen2_extended_review as ext

MARKER=b'-- BEGIN CHERRYGROVE COMPLETE NORTH ROOF ROWS\n'

def lua(value):
    if isinstance(value,str):return json.dumps(value,ensure_ascii=False)
    if isinstance(value,bool):return 'true' if value else 'false'
    if isinstance(value,(int,float)):return str(value)
    if isinstance(value,(list,tuple)):return '{'+','.join(lua(v) for v in value)+'}'
    return '{'+','.join('['+lua(k)+']='+lua(value[k]) for k in sorted(value))+'}'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mod',type=Path,default=HERE.parents[1])
    p.add_argument('--cache',type=Path,default=Path(os.environ['APPDATA'])/'pokemon-love2d')
    p.add_argument('--engine',type=Path,default=WORKSPACE/'.work/tileshift-engine-0410')
    p.add_argument('--output',type=Path,default=WORKSPACE/'.work/tileshift-mart-shelf-fix/roof-review')
    p.add_argument('--activate',action='store_true')
    a=p.parse_args();mod=a.mod.resolve();a.output.mkdir(parents=True,exist_ok=True)
    target=mod/'lib/center_mart_roofs.lua';raw=target.read_bytes()
    pristine=raw.split(MARKER,1)[0].rstrip()
    if MARKER in raw:pristine+=b'\nreturn rows'
    assert pristine.endswith(b'return rows')
    base=catalog.plain(catalog.LUA.execute(pristine.decode('utf-8')))
    sides=preview.read_reviewed(mod/'lib/side_catalog.lua')
    rows=[];packed={}
    for game in ('gold','silver','crystal'):
        source=ext.source(a.cache,game);definition=source['maps']['CHERRYGROVE_CITY']
        blocks=catalog.lua_array(definition['blocks'])
        for role,origin,width,template_x,template_y in [
            ('larger_mart',22,4,8,13),('larger_center',27,5,29,21)]:
            for dx in range(width):
                tx=template_x+dx
                candidates=sides if role=='larger_center' and dx==0 else base
                template=next(r for r in candidates if r.get('game')==game
                    and r.get('map')=='VIOLET_CITY' and r.get('role')==role
                    and r.get('x')==tx and r.get('y')==template_y)
                row=copy.deepcopy(template)
                for key in ('side','buildingCompact','canopy','frontY'):
                    row.pop(key,None)
                x=origin+dx;bid=blocks[x//2];q=x%2
                cell=ext.cell_info(a.cache,game,source,definition['tileset'],bid,q)
                row.update(map='CHERRYGROVE_CITY',tileset=definition['tileset'],x=x,y=-1,
                    sourceX=x,sourceY=0,buildingX=22 if role=='larger_mart' else 28,
                    buildingY=0,buildingW=4,buildingH=4,id=bid,quadrant=q,
                    sourceCells=[[x,0]],sourceHash=cell['sourceHash'],
                    sourceFiles=source['fingerprints'][definition['tileset']],
                    sourceCollision=cell['collision'],
                    sourcePalettes=[v.get('palette',1) for v in cell['attributes']],
                    sourcePriority=[bool(v.get('priority')) for v in cell['attributes']],
                    evidence='Restore the complete native back roof row at1:1 pixel scale above Cherrygrove. '
                    'The same intact Violet City service-building modules retain their original alpha and pixel size. '
                    'Drawing y=-1 is bounded to the existing building envelope and independently fingerprinted '
                    'against source row0. Original doors, collision, events and neighboring maps remain native. '
                    'Expanded Center artwork follows the existing compact/expanded choice.')
                row['compositionPixelHash']=catalog.sha(preview.replacement_image(a.cache,row,packed,mod).tobytes())
                rows.append(row)
    assert len(rows)==27
    # The decoration validator checks the source anchor, never a fabricated
    # negative source cell. R.new performs this same anchored validation.
    anchored=copy.deepcopy(rows)
    for row in anchored:row['y']=row['sourceY'];row['x']=row['sourceX']
    validation=ext.validate_batch(anchored,SimpleNamespace(cache=a.cache,engine=a.engine,output=a.output),mod)
    assert validation['rows_accepted']==27 and validation['rejected']==0
    body=pristine[:-len(b'return rows')].rstrip()+b'\n'+MARKER
    body+=('add((function()return '+lua(rows[:14])+' end)())\n').encode('utf-8')
    body+=('add((function()return '+lua(rows[14:])+' end)())\nreturn rows\n').encode('utf-8')
    result=catalog.plain(catalog.LUA.execute(body.decode('utf-8')))
    assert len(result)==len(base)+27
    (a.output/'rows.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
    (a.output/'proof.json').write_text(json.dumps({'status':'reviewed','rows':27,
        'source_anchor_validation':validation,'source_row':0,'draw_row':-1,
        'old_rows':len(base),'new_rows':len(result),'native_module_scale':1},indent=2)+'\n',encoding='utf-8')
    if a.activate:target.write_bytes(body)
    print(json.dumps({'rows':27,'validation':validation,'activated':a.activate},indent=2))

if __name__=='__main__':main()
