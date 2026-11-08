"""Restore Crystal's sixteen Alph item stands with complete native CrystalDust art.

The exact native pedestal occupies two intact16px FLAT modules (632,640).
Its lower base is in the native BOTTOM plane, so TOP632 alone is incomplete.
Use the original blocked source stand and its clear approach-floor cell. Native
floor520 exactly equals the room's existing Tanoby648 floor. No actor, item,
collision, event, source layout, runtime API or priority data changes.
"""
from __future__ import annotations
import argparse,copy,hashlib,json,os,re,sys
from pathlib import Path
from types import SimpleNamespace
sys.dont_write_bytecode=True
W=next(p for p in Path(__file__).resolve().parents if(p/'.tools/python').is_dir())
sys.path.insert(0,str(W/'.tools/python'))
from PIL import Image
ROM='51196cba923c315d0088b747b5cdee704f2ac057cd493f9ddf226fb7227302cf'
PAIR='083df884_083df9ec'
MODULE='mappings/johto_ruins_finish.lua'
PREFIX='assets/third_party/johto-hacks/alph-native-pedestals'
NAMES=tuple('RUINS_OF_ALPH_'+s+'_ITEM_ROOM'for s in('HO_OH','KABUTO','OMANYTE','AERODACTYL'))
MARKER='-- BEGIN COMPLETE NATIVE ALPH ITEM PEDESTALS'
INPUTS={
 'catalog.json':'fd8fbaf6eb4ee3774e3fe046bf3b506e7f638ab4cd9297c9f62a8bb1189bc740',
 'pairs/'+PAIR+'/metatiles.json':'63a238e0b47bc044f1317319f3da7a784c8f8b6cf63c3087eeb0fdafe4844b74',
 'pairs/'+PAIR+'/flat.png':'54efead706b3ba169e7668e8b0b1a42bdc06aa6570a5da54e086998b2424ebe6',
 'pairs/'+PAIR+'/bottom.png':'74436a85b04f33af60d986228d0fdf668fdca5b0b2937dc4b15be8417b78ca0c',
 'pairs/'+PAIR+'/top.png':'e90dae20ac3b7446e6fc199b0ce3833c1dd534a7df30cb0ee6b01edb07c147d1',
 'maps/g24_m089-flat.png':'a6a10c4669a7da724a074f205bce58df07acf2f43d0b53b399e90b26852df714'}
GUARDS=('game','style','map','tileset','id','quadrant','sourceHash','sourceCells','sourceFiles',
        'sourceCollision','sourcePriority','sourcePalettes','sourceWarps')
sha=lambda b:hashlib.sha256(b).hexdigest()
def canonical(v):
    if isinstance(v,dict):return{k:canonical(v[k])for k in sorted(v)}
    if isinstance(v,list):return[canonical(x)for x in v]
    return v
def tile(a,mid):
    x,y=mid%16*16,mid//16*16
    return a.crop((x,y,x+16,y+16))
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--mod-root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--catalog-dir',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--engine',type=Path,default=W/'.work/tileshift-engine-0420')
    args=p.parse_args();base,mod,private,out=map(Path.resolve,(args.baseline,args.mod_root,args.catalog_dir,args.output))
    assert base!=mod and out not in(base,mod)
    out.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(mod/'tools'))
    import preview,gen2_extended_review as review
    from newbark_building_review import lua
    from lupa.luajit21 import LuaRuntime
    for name,want in INPUTS.items():assert sha((private/name).read_bytes())==want,name
    native=json.loads((private/'catalog.json').read_text());assert native['rom_sha256']==ROM
    native_maps={m['id']:m for m in native['maps']};nm=native_maps['g24_m089']
    assert nm['pair']==PAIR and(nm['width'],nm['height'])==(24,26)and nm['region']==75
    atlas={n:Image.open(private/'pairs'/PAIR/(n+'.png')).convert('RGBA')for n in('bottom','top','flat')}
    meta=json.loads((private/'pairs'/PAIR/'metatiles.json').read_text())
    # Reconstruct the whole four-chamber native map, with the original native
    # BOTTOM+TOP planes. This proves that the pedestal modules are actual art
    # in the supplied Alph item-room map, rather than guessed catalogue labels.
    assembled={n:Image.new('RGBA',(384,416))for n in atlas}
    for i,raw in enumerate(nm['grid']):
        mid=raw&1023;xy=(i%24*16,i//24*16)
        for n in atlas:assembled[n].paste(tile(atlas[n],mid),xy)
    original=Image.open(private/'maps/g24_m089-flat.png').convert('RGBA')
    assert original.tobytes()==assembled['flat'].tobytes()
    assert Image.alpha_composite(assembled['bottom'],assembled['top']).tobytes()==original.tobytes()
    pieces={};records={};files={};whole=Image.new('RGBA',(16,32))
    dest=mod/PREFIX;dest.mkdir(parents=True,exist_ok=True)
    for y,mid in enumerate((632,640)):
        image=tile(atlas['flat'],mid)
        assert sha(image.tobytes())==meta[mid]['pixel_sha256']
        name=f'pedestal-{y}.png';path=dest/name;image.save(path)
        pieces[y]=image;whole.paste(image,(0,y*16));files[name]=sha(path.read_bytes())
        coords=[[i%24,i//24]for i,raw in enumerate(nm['grid'])if raw&1023==mid]
        assert len(coords)==16
        records[name]=dict(asset=f'{PREFIX}/{name}',assetFileHash=files[name],assetPixelHash=sha(image.tobytes()),
            donor_pair=PAIR,donor_mid=mid,donor_plane='flat',source_atlas_sha256=INPUTS['pairs/'+PAIR+'/flat.png'],
            source_map='g24_m089',native_map_coords=coords,donor_xyxy=[mid%16*16,mid//16*16,mid%16*16+16,mid//16*16+16],
            logical_size=[16,16],whole_native_metatile_layer=True,pixel_scale=1,native_alpha_unchanged=True)
    pairs=[]
    for i,raw in enumerate(nm['grid']):
        if raw&1023!=632:continue
        x,y=i%24,i//24;assert nm['grid'][i+24]&1023==640
        assert original.crop((x*16,y*16,x*16+16,y*16+32)).tobytes()==whole.tobytes()
        pairs.append([x,y])
    assert len(pairs)==16
    floor_hash=sha(tile(atlas['flat'],520).tobytes())
    assert floor_hash=='069d1525a58bb15aa1f4bf85a056ca912c5a37c8079176e9d8876fcc4b182046'
    provenance=dict(origin='Complete native CrystalDust Alph item pedestal with its original base and matching floor; two intact FLAT modules632+640.',
        credit='Pokemon CrystalDust / Sierraffinity and DoMoreAwesome Games; native Johto ruins artwork.',
        sourceUrl='https://github.com/Sierraffinity/CrystalDust',rom_sha256=ROM,rom_name=native['rom_name'],
        input_files_sha256=INPUTS,files=files,source_modules=records,
        complete_object_proof=dict(source_map='g24_m089',source_pair=PAIR,whole_cell_pairs=pairs,
            whole_rectangle=[16,32],whole_rgba_sha256=sha(whole.tobytes()),
            complete_flat_pairs_equal_native_map_rectangles=True,flat_equals_native_bottom_plus_top=True,
            body_top_plane_opaque_bounds=list(tile(atlas['top'],632).getbbox()),
            lower_native_base_is_in_bottom_plane=True,source_floor520_equals_existing_Tanoby648=floor_hash,
            feature_crop_or_scale=False,original_pixel_scale=1),
        counterpart_proof=dict(region=75,native_merged_four_chamber_room=True,
            item_room_return_warps=nm['warps'],
            reciprocal_chambers=[dict(map=n,room_warp=w,return_warp=native_maps[n]['warps'][w['dest_warp']])
                for w in nm['warps'][:2]for n in[f"g{w['dest_group']:02d}_m{w['dest_num']:03d}"]]),
        limits=['Static native extraction; actor/animation/script callbacks were not executed.',
                'Two native item-room chamber return entries are present; the two other native return entries are unused g00_m000 defaults, not claimed to be semantic room identities.',
                'Runtime substitutions retain original Crystal source item anchors and all mechanics. Gold/Silver do not contain these four item-room maps.'])
    (dest/'provenance.json').write_text(json.dumps(canonical(provenance),indent=2)+'\n')
    cache=Path(os.environ['APPDATA'])/'pokemon-love2d';before=preview.read_reviewed(base/MODULE)
    updates={};changes=[];new_rows=[];receipts=[];packed={}
    for game in('gold','silver'):
        data=review.source(cache,game);assert all(n not in data['maps']for n in NAMES)
    data=review.source(cache,'crystal');positions={(2,4),(5,4),(2,6),(5,6)}
    for name in NAMES:
        md=data['maps'][name];assert(md['width']*2,md['height']*2)==(8,10)
        objects=md.get('objects',[]);assert len(objects)==4
        assert{(o['x'],o['y'])for o in objects}==positions
        assert all(o.get('sprite')=='SPRITE_POKE_BALL'and o.get('itemball')for o in objects)
        assert not any((w['x'],w['y'])in positions|{(x,y+1)for x,y in positions}for w in md.get('warps',[]))
        receipts.append(dict(game='crystal',map=name,source_map_definition_sha256=sha(json.dumps(canonical(md),separators=(',',':')).encode()),
            objects=objects,warps=md.get('warps',[]),bg_events=md.get('bgEvents',[]),
            item_anchors_unchanged=True,approach_cells_have_no_objects_or_warps=True))
        selected=[r for r in before if r.get('game')=='crystal'and r.get('style')=='gen3'and r.get('map')==name
                  and(r['id'],r['quadrant'])in((49,0),(50,1),(49,2),(50,3))]
        assert len(selected)==4
        for old in selected:
            part=0 if old['quadrant']in(0,1)else 1
            expected={(2 if old['id']==49 else 5,y+part)for y in(4,6)}
            assert{tuple(xy)for xy in old['sourceCells']}==expected
            assert old['sourceCollision']==(7 if part==0 else 0)
            assert old['role']==('johto_ruins_native_stone_below_complete_statue'if part==0 else'johto_ruins_native_tanoby_stone_floor')
            assert old['donor']['hash']==floor_hash
            cell=review.cell_info(cache,'crystal',data,md['tileset'],old['id'],old['quadrant'])
            assert cell['sourceHash']==old['sourceHash']and cell['collision']==old['sourceCollision']
            assert data['fingerprints'][md['tileset']]==old['sourceFiles']
            assert[bool(a.get('priority'))for a in cell['attributes']]==old['sourcePriority']
            assert[a.get('palette',1)for a in cell['attributes']]==old['sourcePalettes']
            row=copy.deepcopy(old)
            for k in('donor','base','parts','sourceColors','animated','animation'):row.pop(k,None)
            asset=f'{PREFIX}/pedestal-{part}.png'
            row.update(kind='third_party',asset=asset,assetFileHash=files[f'pedestal-{part}.png'],
                assetPixelHash=sha(pieces[part].tobytes()),role=f'gen2_complete_native_alph_pedestal_{part}',
                credit=provenance['credit'],sourceUrl=provenance['sourceUrl'],
                evidence='Complete original CrystalDust Alph item stand: exact native FLAT632 andFLAT640 at1:1, including the base in BOTTOM640. Native floor520 is byte-identical to the existing Tanoby648 floor. Original Crystal item sprites and anchors, blocked head7/clear approach0 collisions, source geometry, priorities, puzzles, event flags, scripts and warps remain unchanged. No feature is cropped, rescaled or substituted with an unrelated statue panel.',
                reviewedNativeCounterpart=dict(source_map='g24_m089',pair=PAIR,mid=632 if part==0 else 640,
                    whole_module_plane='flat',whole_object_cells=[632,640],original_pixel_scale=1,
                    complete_base_preserved=True,native_floor_exact=True))
            result=preview.replacement_image(cache,row,packed,mod)
            assert result.tobytes()==pieces[part].tobytes()
            row['compositionPixelHash']=sha(result.tobytes())
            assert all(row.get(k)==old.get(k)for k in GUARDS)
            updates.setdefault(name,{})[f"{old['id']}:{old['quadrant']}"]=row;new_rows.append(row)
            for xy in old['sourceCells']:
                changes.append(dict(game='crystal',map=name,xy=xy,module=MODULE,id=row['id'],quadrant=row['quadrant'],
                    sourceHash=row['sourceHash'],sourceCollision=row['sourceCollision'],native_mid=632 if part==0 else 640,
                    asset=asset,compositionPixelHash=row['compositionPixelHash'],all_native_pixels_unchanged=True))
    assert len(new_rows)==16 and len(changes)==32
    raw=(base/MODULE).read_bytes();nl=b'\r\n'if b'\r\n'in raw else b'\n';ending=b'return rows'+nl
    assert MARKER.encode()not in raw and raw.endswith(ending)
    footer=(MARKER+'\nlocal updates='+lua(canonical(updates))+'\nlocal changed=0\n'
        'for index,row in ipairs(rows)do\n'
        "  local map=row.game=='crystal'and row.style=='gen3'and updates[row.map]\n"
        "  local replacement=map and map[tostring(row.id)..':'..tostring(row.quadrant)]\n"
        '  if replacement then rows[index]=replacement;changed=changed+1 end\nend\n'
        "assert(changed==16,'Alph item-pedestal source set changed')\n"
        '-- END COMPLETE NATIVE ALPH ITEM PEDESTALS\nreturn rows\n')
    (mod/MODULE).write_bytes(raw[:-len(ending)]+footer.replace('\n',nl.decode()).encode())
    after=preview.read_reviewed(mod/MODULE);assert len(before)==len(after)
    actual=[(a,b)for a,b in zip(before,after)if a!=b];assert len(actual)==16
    for a,b in actual:
        assert b==updates[a['map']][f"{a['id']}:{a['quadrant']}"]
        assert all(a.get(k)==b.get(k)for k in GUARDS)
    paths=list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(mod/'main.lua').read_text())))
    rt=LuaRuntime(unpack_returned_tuples=True);rt.globals().paths=rt.table_from(paths)
    rt.globals().source=lambda n:(mod/n).read_text(encoding='utf-8-sig')
    total=rt.execute('''local rows={}
      for _,p in ipairs(paths)do for _,r in ipairs(assert(load(source(p),'@'..p))())do rows[#rows+1]=r end end
      local M=assert(load(source('lib/mapping.lua')))();local _,errors=M.index(rows)
      assert(#errors==0,table.concat(errors,'\\n'));return #rows''')
    valid=review.validate_batch(new_rows,SimpleNamespace(cache=cache,engine=args.engine,output=out),mod)
    assert valid['rows_accepted']==16 and valid['rejected']==0
    report=dict(status='passed',changed_rows=16,effective_cells=32,complete_pedestals=16,maps=list(NAMES),
        unavailable_games={'gold':list(NAMES),'silver':list(NAMES)},source_receipts=receipts,changes=changes,
        registered_rows=total,index_errors=0,native_validation=valid,source_guards_unchanged=list(GUARDS),
        every_other_module_row_unchanged=True,no_runtime_API_changes=True,native_whole_pair_rgba_sha256=sha(whole.tobytes()),
        full_native_map_reassembly_exact=True,assets_provenance_sha256=sha((dest/'provenance.json').read_bytes()),
        mapping_sha256=sha((mod/MODULE).read_bytes()),helper_sha256=sha(Path(__file__).read_bytes()))
    (out/'proof.json').write_text(json.dumps(canonical(report),indent=2)+'\n')
    # CPU context views use the actual source rows. The native render harness
    # independently checks real actor/item layers after the final freeze.
    all_rows=[r for p in paths for r in preview.read_reviewed(mod/p)]
    for name in NAMES:preview.map_preview(cache,out,'crystal',name,name,all_rows,packed,4,mod)
    print(json.dumps(dict(status='passed',changed_rows=16,effective_cells=32,complete_pedestals=16,
                         registered_rows=total,native_validation=valid)))
if __name__=='__main__':main()
