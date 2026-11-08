"""Use one authentic Emerald ocean family for the eight reviewed G/S/C coasts.

Correct the striped Emerald52 underlay to native368 and retain the unchanged
393/402/410 bank family. Route32's former FireRed299 water and whole-rock
underlays join its actual Emerald393/402 shore. Route41's whirlpool overlays
retain all eight existing asset frame entries and its reachable field-state
rock quarters retain their complete original native object layers.
"""
from __future__ import annotations
import argparse,copy,hashlib,json,os,re,sys
from collections import Counter,defaultdict
from pathlib import Path
from types import SimpleNamespace
sys.dont_write_bytecode=True
W=next(p for p in Path(__file__).resolve().parents if(p/'.tools/python').is_dir())
sys.path.insert(0,str(W/'.tools/python'))
from PIL import Image,ImageDraw
MODULES=('water','gen2_outdoor_extended','cianwood','johto_terrain_repeats',
         'johto_remaining','johto_port_finish','gen2_kanto_facilities_finish','crystaldust_field_states')
MAPS=('NEW_BARK_TOWN','CIANWOOD_CITY','OLIVINE_PORT','VERMILION_PORT','ROUTE_32','ROUTE_34','ROUTE_40','ROUTE_41')
MARKER='-- BEGIN COHERENT NATIVE JOHTO COASTAL WATER FAMILY'
GUARDS=('game','style','map','tileset','id','quadrant','x','y','sourceHash','sourceCells','sourceFiles',
        'sourceCollision','sourcePriority','sourcePalettes','sourceWarps','sourceBehavior','canopy','overMask',
        'parts','asset','assetFileHash','assetPixelHash','assetFrames','fieldStateReview')
ART=('kind','donor','base','parts','animated','animation','asset','assetFileHash','assetPixelHash','assetFrames')
sha=lambda b:hashlib.sha256(b).hexdigest()
def canonical(v):
    if isinstance(v,dict):return{k:canonical(v[k])for k in sorted(v)}
    if isinstance(v,list):return[canonical(x)for x in v]
    return v
def key(r):return ':'.join(str(r.get(k,''))for k in('game','style','tileset','map','id','quadrant','x','y'))
def reason(row):
    if row.get('game')not in('gold','silver','crystal')or row.get('style')!='gen3':return None
    for field in('donor','base'):
        d=row.get(field,{})
        if d.get('game')=='emerald'and d.get('tileset')=='general__petalburg'and d.get('id')==52:
            assert row.get('map')in MAPS and('coast'in row['role'])
            return 'marine52',field
    if row.get('map')=='ROUTE_32'and'coast'in row.get('role',''):
        for field in('donor','base'):
            d=row.get(field,{})
            if d.get('game')=='firered'and d.get('id')==299:return 'route32_coherent_family',field
    if row.get('map')=='ROUTE_41':
        d=row.get('base',{})
        if row.get('role')=='rocky_coast_whirlpool'and d.get('game')=='firered'and d.get('id')==299:return 'marine_whirlpool','base'
        if row.get('fieldStateReview')and d.get('game')=='emerald'and d.get('tileset')=='general__cave'and d.get('id')==635:
            return 'reachable_marine_field_state','base'
    return None
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--mod-root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--engine',type=Path,default=W/'.work/tileshift-engine-0420')
    args=p.parse_args();base,mod,out=map(Path.resolve,(args.baseline,args.mod_root,args.output))
    assert base!=mod and out not in(base,mod);out.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(mod/'tools'))
    import preview,catalog,gen2_extended_review as review
    from newbark_building_review import lua
    from lupa.luajit21 import LuaRuntime
    cache=Path(os.environ['APPDATA'])/'pokemon-love2d'
    template_rows=preview.read_reviewed(base/'mappings/gen2_outdoor_extended.lua')
    templates={}
    for game in('gold','silver','crystal'):
        r=next(r for r in template_rows if r['game']==game and r.get('map')=='OLIVINE_CITY'
               and r['role']=='coastal_ocean_water_interior'and r.get('donor',{}).get('id')==368)
        templates[game]=dict(donor=copy.deepcopy(r['donor']),animation=copy.deepcopy(r['animation']))
        assert r['donor']==dict(game='emerald',tileset='general__petalburg',id=368,
            hash='ec68d3123df4f5e023eed01ae132475c32a66718585d629d7c63ce95ff647b07')
        assert r['animation']['bank']=='general_water'and r['animation']['frames']==8
    packed={};native=preview.native_water_frames(cache,dict(**templates['crystal'],animated=True),packed)
    assert len(native)==8
    before={};updates={};changed_rows=[];changes=[];classes={};source_data={};counts=Counter();bank_proofs=[]
    for name in MODULES:
        module='mappings/'+name+'.lua';rows=preview.read_reviewed(base/module);before[module]=rows;updates[module]={}
        for old in rows:
            selected=reason(old)
            if not selected:continue
            why,field=selected;game=old['game'];template=templates[game]
            row=copy.deepcopy(old);row[field]=copy.deepcopy(template['donor']);row['animation']=copy.deepcopy(template['animation']);row['animated']=True
            if why=='reachable_marine_field_state':row['role']='rocky_coast_native_field_rock_barrier'
            row['evidence']='Reviewed coherent native coastal water family. Complete native Emerald368 ocean and all8 original general_water frames match the existing Emerald393/402/410 banks. Only the native water donor/underlay and matching animation metadata change. Original complete rock/shore/whirlpool layers, all8 whirlpool asset-frame entries and order, source hashes/collisions/palettes/priority, field-state destinations, item/NPC positions, maps, Surf/fishing, scripts and native game mechanics remain unchanged. Route32 joins its actual Emerald393/402 marine banks; coherent Kanto FireRed coasts and inland/cave water are excluded.'
            row['coastalWaterFamilyReview']=dict(reason=why,native_ocean_mid=368,original_pixel_scale=1,
                whole_native_overlay_unchanged=True,complete_eight_frame_sequence=True)
            assert all(old.get(k)==row.get(k)for k in GUARDS)
            if game not in source_data:source_data[game]=review.source(cache,game)
            data=source_data[game];md=data['maps'][old['map']]
            cell=review.cell_info(cache,game,data,old['tileset'],old['id'],old['quadrant'])
            assert cell['sourceHash']==old['sourceHash']
            if'sourceCollision'in old:assert cell['collision']==old['sourceCollision']
            assert data['fingerprints'][old['tileset']]==old['sourceFiles']
            if'sourcePriority'in old:assert[bool(a.get('priority'))for a in cell['attributes']]==old['sourcePriority']
            if'sourcePalettes'in old:assert[a.get('palette',1)for a in cell['attributes']]==old['sourcePalettes']
            coords=old.get('sourceCells')
            if coords is None:
                assert old['map']=='NEW_BARK_TOWN'and name=='water'
                coords=[[i%md['width']*2+old['quadrant']%2,i//md['width']*2+old['quadrant']//2]
                        for i,bid in enumerate(catalog.lua_array(md['blocks']))if bid==old['id']]
            if not coords:
                assert why=='reachable_marine_field_state'and old['map']=='ROUTE_41'and old['id']==54
                assert old['quadrant']in(1,3)
                witnesses=old['fieldStateReview']['witnesses'];assert len(witnesses)==4
                blocks=catalog.lua_array(md['blocks'])
                for w in witnesses:
                    x,y=w['block_coordinate'];assert w['action']=='WHIRLPOOL_BLOCKS'and w['replacement_block']==54 and w['source_block']==7
                    assert blocks[y*md['width']+x]==7
            else:
                blocks=catalog.lua_array(md['blocks'])
                for x,y in coords:
                    assert blocks[y//2*md['width']+x//2]==old['id']and y%2*2+x%2==old['quadrant']
            signature=json.dumps([{k:r.get(k)for k in ART}for r in(old,row)],sort_keys=True)
            if signature not in classes:
                oldframes=preview.replacement_frames(cache,old,packed,mod)
                frames=preview.replacement_frames(cache,row,packed,mod)
                assert len(oldframes)==len(frames)==8
                overlays=[]
                if old.get('parts'):
                    transparent=copy.deepcopy(old)
                    for k in('base','animation','animated'):transparent.pop(k,None)
                    overlay=preview.replacement_image(cache,transparent,packed,mod);overlays=[overlay]*8
                elif old.get('asset'):
                    if old.get('assetFrames'):
                        assert len(old['assetFrames'])==8
                        overlays=[preview.asset_image(dict(old,asset=f['asset'],assetFileHash=f['hash']),mod)for f in old['assetFrames']]
                    else:overlays=[preview.asset_image(old,mod)]*8
                else:overlays=[Image.new('RGBA',(16,16))]*8
                opaque=transparent_pixels=0
                for phase,(a,b,overlay,water)in enumerate(zip(oldframes,frames,overlays,native)):
                    assert Image.alpha_composite(water,overlay).tobytes()==b.tobytes()
                    assert set(overlay.getchannel('A').get_flattened_data())<={0,255}
                    for oldpx,newpx,op,wp in zip(a.get_flattened_data(),b.get_flattened_data(),overlay.get_flattened_data(),water.get_flattened_data()):
                        if op[3]:assert oldpx==newpx==op;opaque+=1
                        else:assert newpx==wp;transparent_pixels+=1
                classes[signature]=dict(old_frame_RGBA_sha256=[sha(f.tobytes())for f in oldframes],
                    new_frame_RGBA_sha256=[sha(f.tobytes())for f in frames],opaque_overlay_pixels_checked=opaque,
                    transparent_water_pixels_checked=transparent_pixels,every_native_overlay_pixel_unchanged=True,
                    every_exposed_water_pixel_matches_approved368=True,frame0=sha(frames[0].tobytes()))
            proof=classes[signature];row['compositionPixelHash']=proof['frame0'];counts[why]+=1
            ident=key(old);assert ident not in updates[module]
            updates[module][ident]=dict(field=field,hash=row['compositionPixelHash'],role=row['role'],reason=why)
            changed_rows.append(row);changes.append(dict(module=module,key=ident,game=game,map=old['map'],
                id=old['id'],quadrant=old['quadrant'],x=old.get('x'),y=old.get('y'),sourceCells=coords,
                sourceHash=old['sourceHash'],sourceCollision=cell['collision'],reason=why,
                old_donor=old[field],new_donor=row[field],compositionPixelHash=row['compositionPixelHash'],
                old_frames=proof['old_frame_RGBA_sha256'],new_frames=proof['new_frame_RGBA_sha256'],
                opaque_native_overlay_unchanged=True,all_eight_water_phases_match368=True))
    assert counts=={'marine52':2320,'route32_coherent_family':660,'marine_whirlpool':12,'reachable_marine_field_state':6},counts
    # Route32's actual shore family is already Emerald393/402. Decode all
    # phases against the same imported manifest before changing its interior.
    for old in before['mappings/johto_remaining.lua']:
        if old.get('map')!='ROUTE_32'or old.get('game')!='crystal'or old.get('donor',{}).get('id')not in(393,402,410):continue
        assert old['donor']['game']=='emerald'and old['donor']['tileset']=='general__petalburg'
        for f in('bank','counter','hash','period','counterMax','frames','phase','manifestHash'):
            assert old['animation'][f]==templates['crystal']['animation'][f]
        frames=preview.native_water_frames(cache,old,packed);assert len(frames)==8
        bank_proofs.append(dict(mid=old['donor']['id'],donor=old['donor'],frame_RGBA_sha256=[sha(f.tobytes())for f in frames]))
    assert{p['mid']for p in bank_proofs}=={393,402}
    evidence=changed_rows[0]['evidence']
    for module,selected in updates.items():
        assert selected
        raw=(base/module).read_bytes();nl=b'\r\n'if b'\r\n'in raw else b'\n';ending=b'return rows'+nl
        assert MARKER.encode()not in raw
        if module=='mappings/water.lua':
            assert not raw.endswith(ending)
            prefix,n=re.subn(rb'^return \{',b'local rows={',raw,count=1,flags=re.MULTILINE)
            assert n==1 and prefix.rstrip().endswith(b'}')
        else:
            assert raw.endswith(ending)
            prefix=raw[:-len(ending)]
        footer=(MARKER+'\nlocal waterTemplates='+lua(canonical(templates))+'\nlocal waterUpdates='+lua(canonical(selected))+'\nlocal changed=0\n'
            "local function waterKey(r)return table.concat({r.game,r.style,r.tileset,r.map or '',r.id,r.quadrant,r.x or '',r.y or ''},':')end\n"
            'for index,prior in ipairs(rows)do local u=waterUpdates[waterKey(prior)]\n'
            ' if u then local row={}for k,v in pairs(prior)do row[k]=v end\n'
            '  row[u.field]=waterTemplates[row.game].donor;row.animation=waterTemplates[row.game].animation;row.animated=true\n'
            '  row.role=u.role;row.compositionPixelHash=u.hash\n'
            '  row.coastalWaterFamilyReview={reason=u.reason,native_ocean_mid=368,original_pixel_scale=1,whole_native_overlay_unchanged=true,complete_eight_frame_sequence=true}\n'
            '  row.evidence='+lua(evidence)+'\n  rows[index]=row;changed=changed+1\n end\nend\n'
            f"assert(changed=={len(selected)},'Coastal native water source set changed')\n"
            '-- END COHERENT NATIVE JOHTO COASTAL WATER FAMILY\nreturn rows\n')
        (mod/module).write_bytes(prefix+footer.replace('\n',nl.decode()).encode())
        after=preview.read_reviewed(mod/module);assert len(after)==len(before[module])
        wanted={key(r):r for r in changed_rows if r['map']in MAPS}
        # Module-aware selected keys avoid assuming unique ordering among
        # scoped overrides in different registered source files.
        actual=0
        for old,new in zip(before[module],after):
            if old==new:continue
            assert key(old)in selected and new==wanted[key(old)]
            assert all(old.get(k)==new.get(k)for k in GUARDS);actual+=1
        assert actual==len(selected)
    paths=list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(mod/'main.lua').read_text())))
    rt=LuaRuntime(unpack_returned_tuples=True);rt.globals().paths=rt.table_from(paths);rt.globals().source=lambda n:(mod/n).read_text(encoding='utf-8-sig')
    total=rt.execute('''local rows={}
      for _,p in ipairs(paths)do for _,r in ipairs(assert(load(source(p),'@'..p))())do rows[#rows+1]=r end end
      local M=assert(load(source('lib/mapping.lua')))();local _,errors=M.index(rows)
      assert(#errors==0,table.concat(errors,'\\n'));return #rows''')
    # The legacy water.lua rows predate sourceCells. The existing probe's
    # compact serializer always emits an empty sourceCells table. Supply it
    # only to the decoder fixture; product rows preserve their original keys.
    probe_rows=[dict(r,sourceCells=r.get('sourceCells',{}))for r in changed_rows]
    assert sum('sourceCells'not in r for r in changed_rows)==9
    valid=review.validate_batch(probe_rows,SimpleNamespace(cache=cache,engine=args.engine,output=out),mod)
    assert valid['rows_accepted']==2998 and valid['rejected']==0
    # Original and corrected native water, including every real animation phase.
    old52=next(r for r in before['mappings/gen2_outdoor_extended.lua']if r.get('game')=='crystal'and r.get('map')=='ROUTE_40'and r.get('donor',{}).get('id')==52)
    view=Image.new('RGB',(8*96,2*96+36),'#18232d');draw=ImageDraw.Draw(view)
    draw.text((4,4),'Original striped52 / corrected native368: all eight actual native frames',fill='white')
    for y,frames in enumerate((preview.replacement_frames(cache,old52,packed,mod),native)):
        for i,frame in enumerate(frames):view.paste(frame.resize((96,96),Image.Resampling.NEAREST),(i*96,36+y*96))
    view.save(out/'native-eight-frame-water-comparison.png')
    report=dict(status='passed',changed_authored_rows=len(changed_rows),reason_counts=dict(counts),maps=list(MAPS),
        changes=changes,unique_native_frame_compositions=len(classes),frame_composition_proofs=list(classes.values()),
        source_guards_and_native_object_fields_unchanged=list(GUARDS),all_native_overlays_and_whirlpool_asset_frames_unchanged=True,
        no_assets_or_runtime_API_or_gameplay_changes=True,route32_actual_bank_proof=bank_proofs,
        template=templates,registered_rows=total,index_errors=0,native_validation=valid,
        legacy_probe_only_empty_sourceCells_tables=9,product_source_guard_key_presence_unchanged=True,
        source_module_hashes={p:sha((mod/p).read_bytes())for p in updates},helper_sha256=sha(Path(__file__).read_bytes()))
    (out/'proof.json').write_text(json.dumps(canonical(report),indent=2)+'\n')
    print(json.dumps(dict(status='passed',rows=len(changed_rows),reason_counts=dict(counts),unique_compositions=len(classes),registered_rows=total,native_validation=valid)))
if __name__=='__main__':main()
