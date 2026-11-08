"""Replace Ice Path's isolated rock artwork with its complete native 16px rock."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,copy,json,os,sys
from types import SimpleNamespace

HERE=Path(__file__).resolve()
WORKSPACE=next((p for p in [Path.cwd(),*HERE.parents] if (p/'.tools/python').is_dir()),Path.cwd())
sys.path.insert(0,str(WORKSPACE/'.tools/python'))
from PIL import Image
import catalog,preview,gen2_extended_review as ext

MODULES=('mappings/gen2_caves.lua','mappings/johto_cave_finish.lua')
MARKER=b'-- BEGIN REVIEWED COMPLETE ICE PATH ROCKS'
PAIR='general__rom_082d4e24'
PHOTO_ROCK_HASH='d08a3c70e7ef067046d0c2376a64844d3acbd6b5f81bdd4a3a205352985bce76'


def key(row):
    return tuple(row.get(k)for k in ('game','style','tileset','map','id','quadrant','x','y'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mod',type=Path,default=HERE.parents[1])
    p.add_argument('--cache',type=Path,default=Path(os.environ['APPDATA'])/'pokemon-love2d')
    p.add_argument('--engine',type=Path,default=WORKSPACE/'.work/tileshift-engine-0420')
    p.add_argument('--output',type=Path,default=WORKSPACE/'.work/tileshift-mart-shelf-fix/ice-review/final')
    p.add_argument('--validate',action='store_true')
    p.add_argument('--activate',action='store_true')
    a=p.parse_args();mod=a.mod.resolve();a.output.mkdir(parents=True,exist_ok=True)
    originals,baselines={},{}
    targets=[]
    for rel in MODULES:
        raw=(mod/rel).read_bytes();ending=b'\r\n'if b'\r\n'in raw else b'\n'
        pristine=raw.split(MARKER,1)[0]+b'return rows'+ending if MARKER in raw else raw
        assert pristine.rstrip().endswith(b'return rows')
        rows=catalog.plain(catalog.LUA.execute(pristine.decode('utf-8-sig')))
        assert len({key(r)for r in rows})==len(rows)
        originals[rel]=pristine;baselines[rel]=rows
        for r in rows:
            if r['game']in ext.GAMES and r['style']=='gen3'and r['tileset']=='TILESET_ICE_PATH'and(r['role']=='fixed_ice_boulder'or r['sourceHash']==PHOTO_ROCK_HASH):
                assert r.get('x')is None and r['donor']['game']=='firered'and r['donor']['tileset']==PAIR
                assert r['donor']['id']==(650 if r['sourceHash']==PHOTO_ROCK_HASH else 642)
                targets.append((rel,r))
    assert len(targets)==306
    donor_catalog=json.loads((WORKSPACE/'.work/tileshift-catalog/firered.json').read_text(encoding='utf-8'))
    records={r['mid']:r for r in donor_catalog['cells']if r['pair']==PAIR}
    def ref(mid):return{'game':'firered','tileset':PAIR,'id':mid,'hash':records[mid]['pixel_sha256']}
    packed={}
    rock=preview.native_donor(a.cache,ref(643),packed,['mid'],{'mid':records[643]['layer_sha256']['mid']})
    opaque=[(x,y)for y in range(16)for x in range(16)if rock.getpixel((x,y))[3]]
    assert len(opaque)==161 and set(rock.getchannel('A').get_flattened_data())<={0,255}
    native_full=preview.native_donor(a.cache,ref(643),packed)
    snow=preview.native_donor(a.cache,ref(641),packed)
    assert Image.alpha_composite(snow,rock).tobytes()==native_full.tobytes()
    updates=defaultdict(dict);scope=[];scene_counts=[];pixel_checks=0
    for game in ext.GAMES:
        data=ext.source(a.cache,game)
        names=sorted({r['map']for _,r in targets if r['game']==game})
        assert len(names)==5 and all(n.startswith('ICE_PATH_')for n in names)
        for name in names:
            definition=data['maps'][name];blocks=catalog.lua_array(definition['blocks'])
            width,height=definition['width']*2,definition['height']*2
            def cell_at(x,y):
                if not(0<=x<width and 0<=y<height):return None
                bid=blocks[y//2*definition['width']+x//2];q=y%2*2+x%2
                return ext.cell_info(a.cache,game,data,definition['tileset'],bid,q)
            counts=Counter()
            for rel,old in targets:
                if old['game']!=game or old['map']!=name:continue
                contexts=[]
                for x,y in old['sourceCells']:
                    cell=cell_at(x,y)
                    assert tuple(cell['tiles'])in((6,7,22,23),(196,197,212,213),(130,131,146,147))and cell['collision']==old['sourceCollision']==7
                    assert cell['sourceHash']==old['sourceHash']and old['sourceFiles']==data['fingerprints'][definition['tileset']]
                    assert old['sourcePalettes']==[v.get('palette',1)for v in cell['attributes']]
                    assert old['sourcePriority']==[bool(v.get('priority'))for v in cell['attributes']]
                    neighbours=[cell_at(nx,ny)for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1))]
                    adjacent=[v['collision']for v in neighbours if v is not None]
                    ground=843 if 0x23 in adjacent else 641
                    contexts.append((x,y,ground,adjacent));counts[ground]+=1
                common=843 if all(c[2]==843 for c in contexts)else 641
                row=copy.deepcopy(old)
                for field in ('donor','asset','assetFileHash','assetPixelHash','artOverlay','compositionPixelHash','animation','animated','frames','assetFrames'):
                    row.pop(field,None)
                row.update(kind='native_composite',role='fixed_ice_boulder',base=ref(common),parts=[{'donor':ref(643),'layers':['mid'],
                    'layerHashes':{'mid':records[643]['layer_sha256']['mid']},'srcX':0,'srcY':0,'x':0,'y':0,'w':16,'h':16}])
                row['evidence']='Reviewed complete native16px FireRed Icefall-cave rock643 middle plane, retaining every native highlight, outline, side and foot at1:1 scale. The former642/650 are segments of larger native outcrops. The actual source glyphs6/7/22/23, Crystal196/197/212/213 and Crystal130/131/146/147 each depict a complete single-cell rock; connected cliff glyphs are distinct and unchanged. Blocked collision7, palette/priority and all source/map fingerprints are retained. Native snow641 remains underneath unless this reviewed source placement borders a native0x23 sliding-ice cell, where the already selected native sliding-ice843 continues through all transparent rock corners. This context is resolved once in guarded map-specific data, never by a runtime draw heuristic. Ice sliding, Strength actors, ladders, holes, map events and movement remain native.'
                row['compositionPixelHash']=catalog.sha(preview.replacement_image(a.cache,row,packed,mod).tobytes())
                updates[rel][key(row)]=row
                for x,y,ground,adjacent in contexts:
                    chosen=row
                    if ground!=common:
                        chosen=copy.deepcopy(row);chosen.update(x=x,y=y,sourceCells=[[x,y]],base=ref(ground))
                        chosen['compositionPixelHash']=catalog.sha(preview.replacement_image(a.cache,chosen,packed,mod).tobytes())
                        updates[rel][key(chosen)]=chosen
                    image=preview.replacement_image(a.cache,chosen,packed,mod)
                    base=preview.native_donor(a.cache,ref(ground),packed)
                    assert image.tobytes()==Image.alpha_composite(base,rock).tobytes()
                    for py in range(16):
                        for px in range(16):
                            expected=rock.getpixel((px,py))if rock.getpixel((px,py))[3]else base.getpixel((px,py))
                            assert image.getpixel((px,py))==expected;pixel_checks+=1
                    scope.append({'game':game,'map':name,'x':x,'y':y,'module':rel,'id':old['id'],'quadrant':old['quadrant'],
                                  'sourceHash':old['sourceHash'],'sourceCollision':7,'base':ground,'adjacent_collisions':adjacent})
            scene_counts.append({'game':game,'map':name,'rock_cells':sum(counts.values()),'base_counts':dict(counts)})
    changes=[r for group in updates.values()for r in group.values()]
    assert len(scope)==1793 and len({(r['game'],r['map'],r['x'],r['y'])for r in scope})==1793
    added=sum(r.get('x')is not None for r in changes)
    assert len(changes)==306+added
    live=ext.validate_batch(changes,SimpleNamespace(cache=a.cache,engine=a.engine,output=a.output),mod)if a.validate else None
    stats={}
    for rel in MODULES:
        old=baselines[rel];old_index={key(r):r for r in old};changed=updates[rel]
        expected={k:changed.get(k,v)for k,v in old_index.items()};expected.update(changed)
        body,compact=ext.write_compact(list(changed.values()),None)
        ending=b'\r\n'if b'\r\n'in originals[rel]else b'\n'
        prefix=originals[rel].rstrip()[:-len(b'return rows')]
        footer='''local function iceRockKey(row)return table.concat({row.game,row.style,row.tileset,row.map or '',row.id,row.quadrant,row.x or '',row.y or ''},':')end
local iceRockUpdates=(function()
'''+body+'''end)()
local iceRockIndex={}for i,row in ipairs(rows)do iceRockIndex[iceRockKey(row)]=i end
for _,row in ipairs(iceRockUpdates)do local i=iceRockIndex[iceRockKey(row)];if i then rows[i]=row else rows[#rows+1]=row end end
return rows
'''
        result=prefix+MARKER+ending+footer.replace('\n',ending.decode()).encode('utf-8')
        expanded=catalog.plain(catalog.LUA.execute(result.decode('utf-8-sig')))
        assert len(expanded)==len(expected)and{key(r):r for r in expanded}==expected
        stats[rel]={'before':len(old),'after':len(expanded),'replaced':sum(k in old_index for k in changed),
                    'added':sum(k not in old_index for k in changed),'sha256':catalog.sha(result),'compact':compact}
        (a.output/(Path(rel).stem+'-candidate.lua')).write_bytes(result)
        if a.activate:(mod/rel).write_bytes(result)
    report={'status':'reviewed_complete_native_ice_rocks','source_maps':len(scene_counts),'source_cells':1793,
            'updated_records':len(changes),'existing_records_replaced':306,'new_exact_position_rows':added,
            'complete_native_rock_pixels':161,'transparent_ground_pixels':95,'native_rgba_pixel_checks':pixel_checks,
            'sliding_ice_cells':sum(r['base']==843 for r in scope),'snow_cells':sum(r['base']==641 for r in scope),
            'scenes':scene_counts,'mapping_stats':stats,'live':live,'changed_runtime_libraries':False}
    (a.output/'proof.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    (a.output/'scope.json').write_text(json.dumps(scope,indent=2)+'\n',encoding='utf-8')
    (a.output/'candidates.json').write_text(json.dumps(changes,indent=2)+'\n',encoding='utf-8')
    (a.output/'scenes.json').write_text(json.dumps([{'game':r['game'],'map':r['map'],'complete':True}for r in scene_counts],indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'source_cells':1793,'records':len(changes),'live':live,'activated':a.activate},indent=2))


if __name__=='__main__':main()
