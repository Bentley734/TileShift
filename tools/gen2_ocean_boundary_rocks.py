"""Replace only authenticated Kanto ocean boundary posts with native CD rocks.

The shared source glyph is also used on land. Resolve every effective source
cell first, select only the reviewed marine runs and enclosed fence corners,
and retain all inland tree choices. Complete native rock pixels remain 1:1.
"""
from __future__ import annotations
from pathlib import Path
from collections import Counter, defaultdict
from types import SimpleNamespace
import argparse, copy, hashlib, json, os, re, sys

W=next(p for p in Path(__file__).resolve().parents if(p/'.tools/python').is_dir()and(p/'.work').is_dir())
sys.path.insert(0,str(W/'.tools/python'))
from PIL import Image

GAMES=('gold','silver','crystal')
SOURCE='4ec880e982f6369d74a38c1e74dd5d8404dfc78fd5ceca86b304cdc1dc84682f'
TARGET='mappings/gen2_outdoor_extended.lua'
MARKER=b'-- BEGIN NATIVE OCEAN BOUNDARY ROCKS'
ASSET='assets/third_party/johto-hacks/crystaldust-route19-rockfall/rock16.png'
COUNTS={'ROUTE_12':68,'ROUTE_13':36,'ROUTE_17':46,'ROUTE_18':23,'ROUTE_19':76,
        'ROUTE_20':145,'ROUTE_21':79,'VERMILION_CITY':99,'CINNABAR_ISLAND':47,'PALLET_TOWN':1}
sha=lambda b:hashlib.sha256(b).hexdigest()

def key(r):return tuple(r.get(k)for k in('game','style','tileset','map','id','quadrant','x','y'))
def canonical(v):
    if isinstance(v,dict):return{k:canonical(x)for k,x in sorted(v.items())}
    if isinstance(v,list):return[canonical(x)for x in v]
    return v
def art_key(r):return json.dumps({k:r[k]for k in('base','animation','asset','sourceOceanBounds')if k in r},sort_keys=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--mod-root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--engine',type=Path,default=W/'.work/tileshift-engine-0420')
    a=p.parse_args();base=a.baseline.resolve();mod=a.mod_root.resolve();out=a.output.resolve()
    assert base!=mod;out.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(mod/'tools'))
    import catalog,preview,gen2_extended_review as review
    from lupa.luajit21 import LuaRuntime
    cache=Path(os.environ['APPDATA'])/'pokemon-love2d'
    paths=list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(base/'main.lua').read_text())))
    modules={path:preview.read_reviewed(base/path)for path in paths}
    generic=defaultdict(dict);scoped=defaultdict(dict);positions=defaultdict(dict)
    for path,rs in modules.items():
      for index,r in enumerate(rs):
        if r['game']not in GAMES or r['style']!='gen3':continue
        tile=r['id'],r['quadrant'];v=(path,index,r)
        if'x'in r:positions[r['game'],r['map']][(*tile,r['x'],r['y'])]=v
        elif r.get('map'):scoped[r['game'],r['map']][tile]=v
        else:generic[r['game'],r['tileset']][tile]=v
    rock=Image.open(mod/ASSET).convert('RGBA');assert rock.size==(16,16)
    assert sha(rock.tobytes())=='e3baee7ad5d6d1f729d164959bdad917435c89e3af15195271a1b71971d72160'
    alpha=list(rock.getchannel('A').get_flattened_data());assert set(alpha)=={0,255}
    packed={};groups=defaultdict(list);scope=[];retained=Counter();summ=Counter();source_data={}
    for game in GAMES:
      d=source_data[game]=review.source(cache,game)
      for name,md in sorted(d['maps'].items()):
        selected=generic[game,md['tileset']].copy();selected.update(scoped[game,name]);active={}
        for i,bid in enumerate(catalog.lua_array(md['blocks'])):
          for q in range(4):
            xy=i%md['width']*2+q%2,i//md['width']*2+q//2
            v=positions[game,name].get((bid,q,*xy),selected.get((bid,q)))
            if v:active[xy]=v
        hits={xy for xy,(_,_,r)in active.items()if r['sourceHash']==SOURCE}
        if not hits:continue
        # Exact source identity alone never implies a marine location.
        water={xy for xy,(_,_,r)in active.items()if r.get('sourceCollision')==41
            and r['role'].startswith(('coastal','rocky_coast'))}
        chosen={xy for xy in hits if any((xy[0]+dx,xy[1]+dy)in water for dy in(-1,0,1)for dx in(-1,0,1))}
        changed=True
        while changed:
          changed=False
          for xy in sorted(hits-chosen):
            around={(xy[0]+dx,xy[1]+dy)for dy in(-1,0,1)for dx in(-1,0,1)if dx or dy}
            if around&chosen and around&set(active)<=(hits|water):chosen.add(xy);changed=True
        retained[game]+=len(hits-chosen)
        if not chosen:continue
        assert name in COUNTS and len(chosen)==COUNTS[name],(game,name,len(chosen))
        full_water=[(xy,r)for xy,(_,_,r)in active.items()if r['role']=='coastal_ocean_water_interior'
            and r.get('sourceCollision')==41 and r.get('animated')and r.get('donor')]
        assert full_water,(game,name,'No authenticated full marine water')
        assert all(r['animation']['frames']==8 for xy,r in full_water)
        for x,y in sorted(chosen,key=lambda xy:(xy[1],xy[0])):
          path,index,old=active[x,y];assert path==TARGET and old['role']=='boundary_tree'
          c=review.cell_info(cache,game,d,md['tileset'],old['id'],old['quadrant'])
          assert md['tileset']=='TILESET_KANTO'and c['sourceHash']==SOURCE and c['collision']==old['sourceCollision']==7
          assert c['tiles']==[42,43,58,59]and old['sourcePalettes']==[1]*4 and old['sourcePriority']==[False]*4
          assert [z.get('palette',1)for z in c['attributes']]==old['sourcePalettes']
          assert [bool(z.get('priority'))for z in c['attributes']]==old['sourcePriority']
          assert d['fingerprints'][md['tileset']]==old['sourceFiles']
          reference,water_row=min(full_water,key=lambda item:(abs(item[0][0]-x)+abs(item[0][1]-y),item[0][1],item[0][0]))
          r=copy.deepcopy(old)
          for k in('donor','base','asset','assetFileHash','assetPixelHash','parts','animated','animation','foreground',
                   'occludes','artOverlay','canopy','flora','buildingCompact','frames','compositionPixelHash','sourceOceanBounds','reviewedSeed'):
            r.pop(k,None)
          r.update(kind='third_party',asset=ASSET,assetFileHash=sha((mod/ASSET).read_bytes()),assetPixelHash=sha(rock.tobytes()),
              base=copy.deepcopy(water_row['donor']),animated=True,animation=copy.deepcopy(water_row['animation']),
              role='rocky_coast_native_boundary_rock',credit='CrystalDust by Sierraffinity and contributors; complete native MID514 middle-plane rock, 1:1.',
              sourceUrl='https://github.com/Sierraffinity/CrystalDust')
          if'sourceOceanBounds'in water_row:r['sourceOceanBounds']=copy.deepcopy(water_row['sourceOceanBounds'])
          r['evidence']='Reviewed this exact original gray capped Kanto boundary post at its marine map position. Complete native CrystalDust16px rock MID514 is used without cropping, resizing or recoloring. All transparent exterior pixels show the exact same-map full ocean donor and eight ordered native frames as the checked reference cell. Only posts touching marine water and enclosed fence corners are selected; inland foliage and real tree source glyphs remain unchanged. Source hash, collision7, palette, priority, NPCs, warps, scripts, encounters and all interactions remain native. Water retains its existing Default/Random/Mixed and three explicit style choices; tree choices do not modify rocks.'
          r['oceanBoundaryReview']=dict(reference_cell=list(reference),complete_native_rock=True,source_tiles=c['tiles'],
              native_rock_RGBA_sha256=sha(rock.tobytes()),transparent_pixels=alpha.count(0),native_frames=8)
          frames=preview.replacement_frames(cache,r,packed,mod)
          backgrounds=preview.native_water_frames(cache,water_row,packed)
          assert len(frames)==len(backgrounds)==8
          for frame,background in zip(frames,backgrounds):
            assert frame.tobytes()==Image.alpha_composite(background,rock).tobytes()
            assert all(new==(fg if aa else bg)for new,fg,aa,bg in zip(frame.get_flattened_data(),rock.get_flattened_data(),alpha,background.get_flattened_data()))
          r['compositionPixelHash']=sha(frames[0].tobytes())
          groups[path,index].append(((x,y),r));summ[game,name]+=1
          scope.append(dict(game=game,map=name,xy=[x,y],module=path,id=r['id'],quadrant=r['quadrant'],sourceHash=SOURCE,
              sourceCollision=7,sourcePalettes=r['sourcePalettes'],sourcePriority=r['sourcePriority'],sourceFiles=r['sourceFiles'],
              reference_cell=list(reference),base=r['base'],animation=r['animation'],native_rock_RGBA_sha256=sha(rock.tobytes()),
              transparent_pixels=alpha.count(0),all_opaque_native_pixels_unchanged=True,all_transparent_pixels_match_local_water=True,
              old_RGBA_sha256=sha(preview.replacement_image(cache,old,packed,mod).tobytes()),new_RGBA_sha256=r['compositionPixelHash']))
    assert sum(summ.values())==1860 and set(summ)=={(g,n)for g in GAMES for n in COUNTS}
    assert all(retained[g]==1382 for g in GAMES),retained
    replacements={};extras=[]
    for(path,index),items in sorted(groups.items()):
      old=modules[path][index];coords={xy for xy,r in items}
      assert coords<={tuple(xy)for xy in old['sourceCells']}
      if coords=={tuple(xy)for xy in old['sourceCells']}and len({art_key(r)for xy,r in items})==1:
        r=items[0][1];r['sourceCells']=copy.deepcopy(old['sourceCells']);replacements[key(old)]=r
      else:
        for(x,y),r in items:r.update(x=x,y=y,sourceCells=[[x,y]]);extras.append(r)
    changed_rows=canonical(list(replacements.values())+extras)
    raw=(base/TARGET).read_bytes();assert MARKER not in raw
    nl=b'\r\n'if b'\r\n'in raw else b'\n';assert raw.endswith(b'return rows'+nl)
    body,compact=review.write_compact(changed_rows,None)
    footer=MARKER.decode()+'''\nlocal nativeOceanUpdates=(function()\n'''+body+'''end)()
local function nativeOceanKey(r)return table.concat({r.game,r.style,r.tileset,r.map or '',r.id,r.quadrant,r.x or '',r.y or ''},':')end
local nativeOceanIndex={}for i,r in ipairs(rows)do nativeOceanIndex[nativeOceanKey(r)]=i end
local replaced,added=0,0
for _,r in ipairs(nativeOceanUpdates)do
  local i=nativeOceanIndex[nativeOceanKey(r)]
  if i then rows[i]=r;replaced=replaced+1 else rows[#rows+1]=r;added=added+1 end
end
'''+f"assert(replaced=={len(replacements)} and added=={len(extras)},'Native ocean post source set changed')\n"+'''-- END NATIVE OCEAN BOUNDARY ROCKS
return rows
'''
    delta=footer.replace('\n',nl.decode()).encode();(mod/TARGET).write_bytes(raw[:-len(b'return rows'+nl)]+delta)
    (out/'gen2_outdoor_extended.lua.footer').write_bytes(delta)
    after=preview.read_reviewed(mod/TARGET);expected={key(r):replacements.get(key(r),r)for r in modules[TARGET]}
    expected.update({key(r):r for r in extras});assert len(after)==len(expected)and{key(r):r for r in after}==expected
    # Resolve every map again. A generic source key must never spill a coastal
    # change onto another position, including the land occurrences of this glyph.
    new_scoped=defaultdict(dict);new_positions=defaultdict(dict)
    for r in after:
      if r['game']not in GAMES or r['style']!='gen3':continue
      if'x'in r:new_positions[r['game'],r['map']][(r['id'],r['quadrant'],r['x'],r['y'])]=r
      else:new_scoped[r['game'],r['map']][r['id'],r['quadrant']]=r
    allowed={(r['game'],r['map'],*r['xy'])for r in scope};actual=set();world_checks=Counter()
    for game,d in source_data.items():
      for name,md in d['maps'].items():
        regular=generic[game,md['tileset']].copy();regular.update(scoped[game,name])
        world_checks['maps']+=1
        for i,bid in enumerate(catalog.lua_array(md['blocks'])):
          for q in range(4):
            x,y=i%md['width']*2+q%2,i//md['width']*2+q//2
            old_v=positions[game,name].get((bid,q,x,y),regular.get((bid,q)))
            old=old_v[2]if old_v else None;new=old
            if old_v and old_v[0]==TARGET:
              new=new_positions[game,name].get((bid,q,x,y),new_scoped[game,name].get((bid,q),old))
            world_checks['source_cells']+=1
            if old==new:world_checks['identical_effective_rows']+=1;continue
            location=game,name,x,y;assert location in allowed
            for k in('game','style','tileset','id','quadrant','sourceHash','sourceCollision','sourcePriority','sourcePalettes','sourceFiles'):
              assert old.get(k)==new.get(k),(location,k)
            assert old['role']=='boundary_tree'and new['role']=='rocky_coast_native_boundary_rock'
            actual.add(location);world_checks['changed_effective_rows']+=1
    assert actual==allowed and world_checks['maps']==1124 and world_checks['source_cells']==434252
    runtime=LuaRuntime(unpack_returned_tuples=True);runtime.globals().paths=runtime.table_from(paths)
    runtime.globals().source=lambda name:(mod/name).read_text(encoding='utf-8-sig')
    total=runtime.execute('''local rows={}
      for _,path in ipairs(paths)do for _,r in ipairs(assert(load(source(path),'@'..path))())do rows[#rows+1]=r end end
      local M=assert(load(source('lib/mapping.lua'),'@lib/mapping.lua'))();local _,errors=M.index(rows)
      assert(#errors==0,table.concat(errors,'\\n'));return #rows''')
    live=review.validate_batch(changed_rows,SimpleNamespace(cache=cache,engine=a.engine,output=out),mod)
    assert live['rows_accepted']==len(changed_rows)and live['rejected']==0
    proof=dict(status='passed',changed_cells=len(scope),changed_rows=len(changed_rows),replaced_rows=len(replacements),
        added_positioned_rows=len(extras),selected_source_cells=scope,retained_inland_instances=dict(retained),
        all_other_existing_rows_identical=True,native_scale=1,whole_rock=True,native_animation_frames=8,
        registered_rows=total,index_errors=0,native_validation=live,no_new_assets_or_runtime_API=True,
        effective_world_scope=dict(world_checks),all_source_metadata_unchanged=True,
        module=TARGET,module_sha256=sha((mod/TARGET).read_bytes()),footer_sha256=sha(delta),
        helper_sha256=sha(Path(__file__).read_bytes()),compact=compact,
        game_maps=[dict(game=g,map=n,cells=count)for(g,n),count in sorted(summ.items())])
    (out/'proof.json').write_text(json.dumps(canonical(proof),indent=2)+'\n')
    (out/'scenes.json').write_text(json.dumps([dict(game=g,map=n,complete=True)for(g,n)in sorted(summ)],indent=2)+'\n')
    for n in COUNTS:
      allrows=[r for path,rs in modules.items()for r in(after if path==TARGET else rs)]
      preview.map_preview(cache,out,'crystal',n,n,allrows,packed,2,mod)
    print(json.dumps(dict(status='passed',changed_cells=len(scope),changed_rows=len(changed_rows),replaced_rows=len(replacements),
        added_positioned_rows=len(extras),registered_rows=total,index_errors=0,native_validation=live)))

if __name__=='__main__':main()
