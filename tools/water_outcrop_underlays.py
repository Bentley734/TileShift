"""Continue each reviewed local water family beneath fully offshore boulders."""
from pathlib import Path
from collections import defaultdict
import argparse,copy,json,os,sys
from types import SimpleNamespace

HERE=Path(__file__).resolve()
WORKSPACE=next((p for p in [Path.cwd(),*HERE.parents]if(p/'.tools/python').is_dir()),Path.cwd())
sys.path.insert(0,str(WORKSPACE/'.tools/python'))
from PIL import Image
import catalog,preview,gen2_extended_review as ext

MODULES=('mappings/johto_shared_finish.lua','mappings/johto_terrain_repeats.lua','mappings/north_johto.lua')
SEARCH=MODULES+('mappings/gen2_outdoor_extended.lua','mappings/johto_remaining.lua')
MARKER=b'-- BEGIN REVIEWED LOCAL WATER UNDER OFFSHORE BOULDERS'
TARGETS={'ROUTE_32':[(18,42)],'ROUTE_34':[(0,2),(0,10)],
         'ROUTE_41':[(2,24),(12,50),(22,46),(24,6),(26,22),(26,32),(30,46),(42,28),(12,42),(42,48)],
         'ROUTE_42':[(16,10),(36,10)]}
FAMILIES={'ROUTE_32':('firered','pallet_outdoor',299),'ROUTE_34':('emerald','general__petalburg',52),
          'ROUTE_41':('emerald','general__petalburg',52),'ROUTE_42':('emerald','general__petalburg',368)}


def key(r):return tuple(r.get(k)for k in('game','style','tileset','map','id','quadrant','x','y'))
def family(ref):return(ref['game'],ref['tileset'],ref['id'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mod',type=Path,default=HERE.parents[1])
    p.add_argument('--cache',type=Path,default=Path(os.environ['APPDATA'])/'pokemon-love2d')
    p.add_argument('--engine',type=Path,default=WORKSPACE/'.work/tileshift-engine-0420')
    p.add_argument('--output',type=Path,default=WORKSPACE/'.work/tileshift-mart-shelf-fix/water-audit/other-outcrops')
    p.add_argument('--validate',action='store_true');p.add_argument('--activate',action='store_true')
    a=p.parse_args();mod=a.mod.resolve();a.output.mkdir(parents=True,exist_ok=True)
    originals,baselines={},{}
    for rel in SEARCH:
        raw=(mod/rel).read_bytes();ending=b'\r\n'if b'\r\n'in raw else b'\n'
        pristine=raw.split(MARKER,1)[0]+b'return rows'+ending if MARKER in raw else raw
        baselines[rel]=catalog.plain(catalog.LUA.execute(pristine.decode('utf-8-sig')))
        originals[rel]=pristine
    packed={};updates=defaultdict(dict);scope=[];footprints=[];pixel_checks=0
    for game in ext.GAMES:
        source=ext.source(a.cache,game)
        for name,origins in TARGETS.items():
            definition=source['maps'][name];blocks=catalog.lua_array(definition['blocks'])
            generic,positions={},{}
            entries=[(rel,r)for rel,rows in baselines.items()for r in rows
                     if r['game']==game and r['style']=='gen3'and r['tileset']==definition['tileset']and(r.get('map')is None or r['map']==name)]
            for rel,r in sorted(entries,key=lambda item:bool(item[1].get('map'))):
                if r.get('x')is None:generic[r['id'],r['quadrant']]=(rel,r)
                else:positions[r['id'],r['quadrant'],r['x'],r['y']]=(rel,r)
            def cell_at(x,y):
                if not(0<=x<definition['width']*2 and 0<=y<definition['height']*2):return None
                bid=blocks[y//2*definition['width']+x//2];q=y%2*2+x%2
                c=ext.cell_info(a.cache,game,source,definition['tileset'],bid,q)
                owner,r=positions.get((bid,q,x,y),generic.get((bid,q),(None,None)))
                assert r is not None,(game,name,x,y,bid,q)
                return c,owner,r
            for ox,oy in origins:
                perimeter={(x,oy-1)for x in range(ox,ox+2)}|{(x,oy+2)for x in range(ox,ox+2)}
                perimeter|={(ox-1,y)for y in range(oy,oy+2)}|{(ox+2,y)for y in range(oy,oy+2)}
                templates=[];perimeter_proof=[]
                for x,y in sorted(perimeter):
                    item=cell_at(x,y)
                    if item is None:perimeter_proof.append({'x':x,'y':y,'border':True});continue
                    c,owner,r=item
                    assert c['collision']in(0x29,0x27),'Never replace ground under a mixed land/shore boulder'
                    perimeter_proof.append({'x':x,'y':y,'collision':c['collision'],'role':r['role']})
                    if c['collision']==0x29:
                        ref=r.get('base')or r.get('donor')
                        if ref is not None and family(ref)==FAMILIES[name]:templates.append((owner,r))
                assert templates,(game,name,ox,oy,'No matching full-water neighbor')
                _,water=templates[0];ref=water.get('base')or water['donor'];animation=water['animation']
                assert water['animated']and animation['frames']==8
                assert all((r.get('base')or r['donor'])==ref and r['animation']==animation for _,r in templates)
                assert water['role']=='coastal_ocean_water_interior'if name!='ROUTE_42'else water['role'].startswith('freshwater_pond_')
                for q in range(4):
                    x,y=ox+q%2,oy+q//2;c,owner,old=cell_at(x,y)
                    assert owner in MODULES and c['collision']==old['sourceCollision']==7
                    assert old['kind']=='native_composite'and old['base']['id']==1 and 'whole_outcrop'in old['role']
                    assert c['sourceHash']==old['sourceHash']and source['fingerprints'][definition['tileset']]==old['sourceFiles']
                    assert [v.get('palette',1)for v in c['attributes']]==old['sourcePalettes']
                    assert [bool(v.get('priority'))for v in c['attributes']]==old['sourcePriority']
                    row=copy.deepcopy(old)
                    row.update(map=name,x=x,y=y,sourceCells=[[x,y]],base=copy.deepcopy(ref),
                               animated=True,animation=copy.deepcopy(animation),
                               role=('freshwater_pond_'if name=='ROUTE_42'else'rocky_coast_')+'clear_water_whole_outcrop_'+str(q))
                    if name=='ROUTE_42':row.pop('sourceOceanBounds',None)
                    elif water.get('sourceOceanBounds')is not None:row['sourceOceanBounds']=copy.deepcopy(water['sourceOceanBounds'])
                    row['evidence']='Reviewed this exact32x32 boulder footprint against its original source map and every cardinal perimeter cell. All outside neighbors are native water, permanent sea-rock barrier or the map border; mixed land/shore clumps are deliberately excluded. Keep every complete original FireRed rock layer and pixel at1:1 scale. Replace only the former grass base with the same fingerprinted full-water donor and all eight native animation frames used by adjacent water. Route42 retains its freshwater role and local lake family; Route32 retains its own FireRed water profile, while Routes34/41 retain their local Emerald52 profile. Selected water artwork continues through transparent rock corners. Source collision7, source hashes, palettes, priority, maps, NPCs and scripts remain native.'
                    row['compositionPixelHash']=catalog.sha(preview.replacement_image(a.cache,row,packed,mod).tobytes())
                    transparent=copy.deepcopy(old);transparent.pop('base',None);transparent.pop('animation',None);transparent.pop('animated',None)
                    rock=preview.replacement_image(a.cache,transparent,packed,mod)
                    actual=preview.replacement_frames(a.cache,row,packed,mod)
                    background=preview.native_water_frames(a.cache,{'donor':ref,'animation':animation},packed)
                    assert len(actual)==len(background)==8 and row['parts']==old['parts']
                    for frame,ground in zip(actual,background):
                        assert frame.tobytes()==Image.alpha_composite(ground,rock).tobytes()
                        for py in range(16):
                            for px in range(16):
                                pixel=rock.getpixel((px,py));assert pixel[3]in(0,255)
                                assert frame.getpixel((px,py))==(pixel if pixel[3]else ground.getpixel((px,py)))
                                pixel_checks+=1
                    updates[owner][key(row)]=row
                    scope.append({'game':game,'map':name,'x':x,'y':y,'module':owner,'id':row['id'],'quadrant':row['quadrant'],
                                  'sourceHash':row['sourceHash'],'base':ref,'animation':animation,'role':row['role']})
                footprints.append({'game':game,'map':name,'origin':[ox,oy],'water':ref,'water_role':water['role'],'perimeter':perimeter_proof})
    changes=[r for group in updates.values()for r in group.values()]
    assert len(changes)==len(scope)==180 and len(footprints)==45
    live=ext.validate_batch(changes,SimpleNamespace(cache=a.cache,engine=a.engine,output=a.output),mod)if a.validate else None
    stats={}
    for rel in MODULES:
        old=baselines[rel];changed=updates[rel];expected={key(r):changed.get(key(r),r)for r in old};expected.update(changed)
        if not changed:
            stats[rel]={'before':len(old),'after':len(old),'replaced':0,'added':0,
                        'sha256':catalog.sha(originals[rel]),'unchanged':True}
            if a.activate:(mod/rel).write_bytes(originals[rel])
            continue
        body,compact=ext.write_compact(list(changed.values()),None);ending=b'\r\n'if b'\r\n'in originals[rel]else b'\n'
        prefix=originals[rel].rstrip()[:-len(b'return rows')]
        footer='''local function waterRockKey(row)return table.concat({row.game,row.style,row.tileset,row.map or '',row.id,row.quadrant,row.x or '',row.y or ''},':')end
local waterRockUpdates=(function()
'''+body+'''end)()
local waterRockIndex={}for i,row in ipairs(rows)do waterRockIndex[waterRockKey(row)]=i end
for _,row in ipairs(waterRockUpdates)do local i=waterRockIndex[waterRockKey(row)];if i then rows[i]=row else rows[#rows+1]=row end end
return rows
'''
        result=prefix+MARKER+ending+footer.replace('\n',ending.decode()).encode('utf-8')
        rows=catalog.plain(catalog.LUA.execute(result.decode('utf-8-sig')))
        assert len(rows)==len(expected)and{key(r):r for r in rows}==expected
        stats[rel]={'before':len(old),'after':len(rows),'replaced':sum(k in{key(r)for r in old}for k in changed),
                    'added':len(rows)-len(old),'sha256':catalog.sha(result),'compact':compact}
        (a.output/(Path(rel).stem+'-candidate.lua')).write_bytes(result)
        if a.activate:(mod/rel).write_bytes(result)
    (a.output/'proof.json').write_text(json.dumps({'status':'reviewed_local_water_under_offshore_boulders','source_cells':180,
        'footprints':45,'source_map_variants':12,'native_rgba_pixel_checks':pixel_checks,'native_frames_per_row':8,
        'original_rock_pixels_retained':True,'no_mixed_land_or_Goldenrod_changes':True,'mapping_stats':stats,'live':live},indent=2)+'\n',encoding='utf-8')
    (a.output/'scope.json').write_text(json.dumps(scope,indent=2)+'\n',encoding='utf-8')
    (a.output/'footprints.json').write_text(json.dumps(footprints,indent=2)+'\n',encoding='utf-8')
    (a.output/'candidates.json').write_text(json.dumps(changes,indent=2)+'\n',encoding='utf-8')
    (a.output/'scenes.json').write_text(json.dumps([{'game':g,'map':n,'complete':True}for g in ext.GAMES for n in TARGETS],indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'source_cells':180,'footprints':45,'pixel_checks':pixel_checks,'live':live,'activated':a.activate},indent=2))


if __name__=='__main__':main()
