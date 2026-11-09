"""Reproduce complete native CrystalDust Kurt cupboards and framed wall map.

Whole native foregrounds are translated eight pixels upward inside their
existing source footprints. Only transparent native padding is left outside:
all cupboard hardware (32x29 envelope) and map (22x14) remain at native scale.
"""
from pathlib import Path
import argparse, copy, hashlib, json, os, re, sys
W = next(p for p in Path(__file__).resolve().parents if (p/'.tools/python').is_dir())
sys.path.insert(0, str(W/'.tools/python'))
from PIL import Image

SHA = lambda b: hashlib.sha256(b).hexdigest()
ROM = '51196cba923c315d0088b747b5cdee704f2ac057cd493f9ddf226fb7227302cf'
PAIR = '083df884_083dfb6c'
MARKER = '-- BEGIN COMPLETE KURT NATIVE DOMESTIC DETAILS'
GAMES = ('gold', 'silver', 'crystal')

def canonical(v):
    if isinstance(v, dict): return {k: canonical(x) for k, x in sorted(v.items())}
    if isinstance(v, list): return [canonical(x) for x in v]
    return v

def key(r):
    return tuple(r.get(k) for k in ('game', 'style', 'tileset', 'map', 'id', 'quadrant', 'x', 'y'))

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--baseline', type=Path, required=True)
    ap.add_argument('--catalog-dir', type=Path, required=True)
    ap.add_argument('--mod-root', type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    base, mod, cat, out = (p.resolve() for p in (a.baseline, a.mod_root, a.catalog_dir, a.output))
    assert base != mod
    out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(mod/'tools'))
    import catalog, preview, gen2_extended_review as review
    catdata = json.loads((cat/'catalog.json').read_text(encoding='utf8'))
    assert catdata['rom_sha256'] == ROM
    cm = next(m for m in catdata['maps'] if m['id'] == 'g03_m004')
    assert cm['pair'] == PAIR and (cm['width'], cm['height']) == (17, 9)
    assert cm['warps'] == [dict(x=3, y=7, elevation=0, dest_warp=0, dest_num=11, dest_group=0)]
    top = Image.open(cat/'pairs'/PAIR/'top.png').convert('RGBA')
    grid = [cm['grid'][y*17:(y+1)*17] for y in range(9)]
    native = Image.new('RGBA', (17*16, 9*16))
    cols = top.width//16
    for y in range(9):
        for x in range(17):
            mid = grid[y][x] & 1023
            native.paste(top.crop((mid % cols*16, mid//cols*16, mid % cols*16+16, mid//cols*16+16)), (x*16, y*16))
    assert [[grid[y][x]&1023 for x in (2,3)] for y in range(3)] == [[221,222],[229,230],[237,238]]
    assert [[grid[y][x]&1023 for x in (8,9)] for y in range(2)] == [[397,398],[405,406]]
    cupboard_all = native.crop((32, 0, 64, 48))
    picture_all = native.crop((128, 0, 160, 32))
    assert cupboard_all.getbbox() == (1,11,32,40)
    assert picture_all.getbbox() == (5,9,27,23)
    whole = {'cupboard': cupboard_all.crop((0,8,32,40)), 'map': picture_all.crop((0,8,32,24))}
    assert whole['cupboard'].getbbox() == (1,3,32,32)
    assert whole['map'].getbbox() == (5,1,27,15)
    assert sum(p[3] != 0 for p in cupboard_all.get_flattened_data()) == sum(p[3] != 0 for p in whole['cupboard'].get_flattened_data())
    assert sum(p[3] != 0 for p in picture_all.get_flattened_data()) == sum(p[3] != 0 for p in whole['map'].get_flattened_data())
    folder = mod/'assets/third_party/johto-hacks/azalea-native-domestic'
    folder.mkdir(parents=True, exist_ok=True)
    assets, objects = {}, {}
    for name, im in whole.items():
        im.save(out/f'complete-native-{name}.png')
        pieces = []
        for y in range(im.height//16):
            for x in range(2):
                piece = im.crop((x*16,y*16,x*16+16,y*16+16))
                f = folder/f'{name}-{x}-{y}.png'; piece.save(f)
                entry = dict(asset=f.relative_to(mod).as_posix(), assetFileHash=SHA(f.read_bytes()), assetPixelHash=SHA(piece.tobytes()), native_object=name,
                    source_map='g03_m004', donor_pair=PAIR, donor_plane='top', source_rect_xyxy=[32,8,64,40] if name=='cupboard' else [128,8,160,24],
                    piece_xy=[x,y], native_scale=1, translation_y_pixels=-8)
                assets[name,x,y] = entry
                pieces.append(entry)
        objects[name] = dict(native_size=list(im.size), alpha_bounds=im.getbbox(), native_opaque_pixels=sum(p[3]!=0 for p in im.get_flattened_data()), pieces=pieces,
            full_source_foreground_pixels_preserved=True, new_RGBA_sha256=SHA(im.tobytes()))
    provenance = dict(origin='Exact complete native CrystalDust Kurt wooden bookcase and framed wall map foregrounds.',
        credit='Pokemon CrystalDust / Sierraffinity and DoMoreAwesome Games', sourceUrl='https://github.com/Sierraffinity/CrystalDust', rom_sha256=ROM,
        source_map='g03_m004', donor_pair=PAIR, source_top_sha256=SHA((cat/'pairs'/PAIR/'top.png').read_bytes()),
        processing='Native1:1 TOP plane; translate whole object eight pixels upward using only transparent padding. No scale, recolor, redraw or hardware clipping.',
        source_modules={f'{n}-{x}-{y}':v for (n,x,y),v in assets.items()}, objects=objects)
    (folder/'provenance.json').write_text(json.dumps(provenance, indent=2)+'\n', encoding='utf8')
    paths = list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]", (base/'main.lua').read_text(encoding='utf8'))))
    modules = {p: preview.read_reviewed(base/p) for p in paths}
    cache = Path(os.environ['APPDATA'])/'pokemon-love2d'
    changes, updates, packed, validations = [], {}, {}, []
    for game in GAMES:
        d = review.source(cache, game); md = d['maps']['KURTS_HOUSE']; ts = d['sets'][md['tileset']]
        assert md['width']==8 and md['height']==4 and md['tileset']=='TILESET_TRADITIONAL_HOUSE'
        sheet = Image.open(cache/game/ts['image']).convert('RGBA')
        active = {}
        for p, rs in modules.items():
            for i, r in enumerate(rs):
                if r.get('game')==game and r.get('style')=='gen3' and r.get('map')=='KURTS_HOUSE':
                    active[r['id'],r['quadrant']] = (p,i,r)
        for y in range(2):
            for x in (2,3,4,5,10,11):
                bid = catalog.lua_array(md['blocks'])[(y//2)*md['width']+x//2]; q=y%2*2+x%2
                p,i,old = active[bid,q]
                assert old['kind']=='third_party' and old['asset'].startswith('assets/third_party/johto-hacks/crystaldust-bookcases/blue-bookcase-cell-')
                asset = assets['cupboard',x%2,y]
                row = copy.deepcopy(old)
                row.update(kind='third_party', asset=asset['asset'], assetFileHash=asset['assetFileHash'], assetPixelHash=asset['assetPixelHash'],
                           role='azalea_complete_crystaldust_wooden_bookcase')
                apply(game,x,y,p,i,old,row,asset,md,ts,sheet,cache,base,mod,packed,preview,catalog,changes,updates,validations)
        for x in (8,9):
            y=0; bid=catalog.lua_array(md['blocks'])[x//2]; q=x%2; p,i,old=active[bid,q]
            assert old['role']=='johto_domestic_complete_kurt_wall_map'
            wall=copy.deepcopy(active[49,0][2]['donor'])
            asset=assets['map',x%2,0]; row=copy.deepcopy(old)
            for f in ('parts','donor','compositionPixelHash'): row.pop(f,None)
            row.update(kind='third_party',base=wall,asset=asset['asset'],assetFileHash=asset['assetFileHash'],assetPixelHash=asset['assetPixelHash'],role='azalea_complete_crystaldust_framed_wall_map')
            apply(game,x,y,p,i,old,row,asset,md,ts,sheet,cache,base,mod,packed,preview,catalog,changes,updates,validations)
    assert len(changes)==42 and len(updates)==2
    for p, rs in updates.items():
        data=(base/p).read_text(encoding='utf8'); assert MARKER not in data
        tail=re.search(r'\nreturn rows\s*$',data); assert tail,p
        compact=review.write_compact([canonical(r) for r in rs.values()],None)[0]
        footer='\n'+MARKER+'\ndo\nlocal reviewed=(function()\n'+compact+'\nend)()\nlocal lookup={}\nlocal function key(r) return table.concat({r.game,r.style,r.tileset,r.map,tostring(r.id),tostring(r.quadrant)},"|") end\nfor _,r in ipairs(reviewed) do lookup[key(r)]=r end\nlocal n=0\nfor i,r in ipairs(rows) do local replacement=lookup[key(r)]; if replacement then rows[i]=replacement;n=n+1 end end\nassert(n=='+str(len(rs))+',"Kurt native domestic source scope changed")\nend\n-- END COMPLETE KURT NATIVE DOMESTIC DETAILS\nreturn rows\n'
        (mod/p).write_text(data[:tail.start()]+footer,encoding='utf8')
    # Native Lua donor validation checks source fingerprints and every native base.
    from types import SimpleNamespace
    val = review.validate_batch(validations, SimpleNamespace(cache=cache, engine=W/'.work/tileshift-engine-0420'), mod)
    assert val.get('rows_accepted')==42, val
    # Inspect the registered world, rather than just validating a private batch.
    from lupa.luajit21 import LuaRuntime
    final = {p:preview.read_reviewed(mod/p) for p in paths}
    expected = {(z['module'],key(r)) for z in changes for r in updates[z['module']].values()
                if r['game']==z['game'] and r['id']==z['id'] and r['quadrant']==z['quadrant']}
    actual = set()
    count = 0
    for path, oldrows in modules.items():
        newrows = final[path]; assert len(newrows)==len(oldrows)
        for old,new in zip(oldrows,newrows):
            count += 1
            if old!=new:
                assert key(old)==key(new)
                actual.add((path,key(new)))
    assert actual==expected and len(actual)==42
    runtime=LuaRuntime(encoding=None)
    runtime.globals()[b'source']=lambda p:(mod/p.decode()).read_bytes()
    registered=runtime.execute(b"local rows={};for _,p in ipairs({"+b','.join(b"'"+p.encode()+b"'" for p in paths)+b"})do for _,r in ipairs(assert(load(source(p),'@'..p))())do rows[#rows+1]=r end end;local M=assert(load(source('lib/mapping.lua'),'@mapping.lua'))();local _,e=M.index(rows);assert(#e==0,table.concat(e,'\\n'));return #rows")
    assert registered==count
    proof=dict(status='passed', baseline=str(base),mod_root=str(mod),changed_cells=42,changed_rows=42,changed_maps=['KURTS_HOUSE'],
        objects=objects,selected_source_cells=changes,source_mechanics_and_source_files_unchanged=True,native_validation=val,
        source_scope='Only six Kurt cupboard columns in rows0..1 and two framed-map cells at8..9,row0; all three GSC variants.',
        changed_mapping_files=sorted(updates), no_runtime_API_changes=True, registered_rows=registered,index_errors=0,
        unchanged_registered_rows=registered-42,all_other_registered_rows_exactly_equal=True)
    (out/'proof.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:proof[k] for k in ('status','changed_cells','changed_rows','changed_maps','native_validation')}))

def apply(game,x,y,path,index,old,row,asset,md,ts,sheet,cache,base,mod,packed,preview,catalog,changes,updates,validations):
    block=catalog.lua_array(catalog.dict_at(ts['blocks'],old['id']+1))
    original=preview.native_cell(sheet,ts,block,old['quadrant'])
    assert SHA(original.tobytes())==old['sourceHash']
    for field,file in (('metadata','data/generated/tilesets.lua'),('maps','data/generated/maps.lua'),('image',ts['image'])):
        assert old['sourceFiles'][field]==SHA((cache/game/file).read_bytes())
    assert row['base']['id']==(705 if y==0 else 715)
    row['credit']='Pokemon CrystalDust / Sierraffinity and DoMoreAwesome Games'
    row['sourceUrl']='https://github.com/Sierraffinity/CrystalDust'
    row['azaleaNativeDomesticReview']=dict(native_object=asset['native_object'],native_scale=1,complete_foreground=True,translation_y_pixels=-8)
    row['evidence'] += ' Complete authentic CrystalDust Kurt '+asset['native_object']+' native TOP foreground. Entire native object translated eight pixels upward inside the existing source footprint using transparent padding only; every frame, shelf, base and opaque pixel retained at1:1. Native alpha reveals matching adjacent room wall or floor. Source collision, BG interaction, NPC states and warps remain unchanged.'
    im=preview.replacement_image(cache,row,packed,mod); bg=preview.native_donor(cache,row['base'],packed); fg=Image.open(mod/row['asset']).convert('RGBA')
    assert im.tobytes()==Image.alpha_composite(bg,fg).tobytes()
    row['compositionPixelHash']=SHA(im.tobytes())
    for f in old:
        if f.startswith('source') or f in ('game','style','tileset','map','id','quadrant','x','y'): assert row.get(f)==old[f]
    assert index not in updates.setdefault(path,{});updates[path][index]=canonical(row)
    v=copy.deepcopy(row);v['x'],v['y']=x,y;v['sourceCells']=[dict(x=x,y=y)];validations.append(v)
    changes.append(dict(game=game,map='KURTS_HOUSE',xy=[x,y],module=path,index=index,id=old['id'],quadrant=old['quadrant'],sourceHash=old['sourceHash'],
        sourceCollision=old.get('sourceCollision'),sourcePalettes=old.get('sourcePalettes'),sourceFiles=old['sourceFiles'],base=row['base'],asset=row['asset'],assetPixelHash=row['assetPixelHash'],
        old_RGBA_sha256=SHA(preview.replacement_image(cache,old,packed,base).tobytes()),new_RGBA_sha256=SHA(im.tobytes())))

if __name__=='__main__': main()
