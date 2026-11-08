"""Place the complete native CrystalDust bed in Celadon Mansion's second floor.

The existing 20x29 native bed is left-aligned in the original 16x32 blocked
bed footprint, with only four decorative pixels extending into the right
aisle. Original collision, actors, scripts and warps remain authoritative.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import sys

W = next(p for p in Path(__file__).resolve().parents if (p / '.tools/python').is_dir())
sys.path.insert(0, str(W / '.tools/python'))
from PIL import Image

MAP = 'CELADON_MANSION_2F'
MODULE = 'mappings/gen2_kanto_apartments_finish.lua'
FURNITURE = 'lib/johto_furniture.lua'
PREFIX = 'assets/third_party/johto-hacks/celadon-mansion-bed'
SOURCE = 'assets/third_party/johto-hacks/crystaldust-ship-beds/complete-native-bed20x29.png'
HEAD = '3de9891e182a5340ff15d420f5383fdde549c73df43b59d672ca52da02da00fc'
FOOT = '76fb1ccc1b4a6b279f94bfdbf3d736034a1c500a9ceb8449f08eed6f79a3903f'
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def canonical(value):
    if isinstance(value, dict): return {k: canonical(v) for k, v in sorted(value.items())}
    if isinstance(value, list): return [canonical(v) for v in value]
    return value


def append(root, base, relative, marker, body):
    raw = (base / relative).read_bytes()
    newline = b'\r\n' if raw.endswith(b'\r\n') else b'\n'
    ending = b'return rows' + newline
    assert marker.encode() not in raw and raw.endswith(ending)
    footer = marker + '\n' + body + '\n-- END CELADON COMPLETE NATIVE BED\nreturn rows\n'
    (root / relative).write_bytes(raw[:-len(ending)] + footer.replace('\n', newline.decode()).encode())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline', required=True, type=Path)
    p.add_argument('--mod-root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    base, mod, out = a.baseline.resolve(), a.mod_root.resolve(), a.output.resolve()
    assert base != mod and out not in (base, mod)
    sys.path.insert(0, str(mod / 'tools'))
    import preview, catalog, gen2_extended_review as review
    from newbark_building_review import lua
    cache = Path(os.environ['APPDATA']) / 'pokemon-love2d'
    source = mod / SOURCE
    assert sha(source.read_bytes()) == '1e5a35e2d7a916ad1cbaf236b6ace4d6ba91dd9a4e828ef2d0fd333e9d926bfd'
    bed = Image.open(source).convert('RGBA')
    assert bed.size == (20, 29) and sha(bed.tobytes()) == 'aec6d2d04969f910fe6540188d8b06efaac4dcd81b3407a0e86f072fe07e5654'
    canvas = Image.new('RGBA', (32, 32)); canvas.paste(bed, (0, 3))
    assert canvas.crop((0, 3, 20, 32)).tobytes() == bed.tobytes()
    folder = mod / PREFIX; folder.mkdir(parents=True, exist_ok=True); out.mkdir(parents=True, exist_ok=True)
    assets, pieces = {}, {}
    for y in range(2):
        for x in range(2):
            image = canvas.crop((x * 16, y * 16, x * 16 + 16, y * 16 + 16))
            path = folder / f'bed-foreground-{x}-{y}.png'; image.save(path)
            assert Image.open(path).convert('RGBA').tobytes() == image.tobytes()
            pieces[x,y] = image
            assets[x,y] = dict(asset=path.relative_to(mod).as_posix(), assetFileHash=sha(path.read_bytes()),
                               assetPixelHash=sha(image.tobytes()), cell=[x,y])
    assert sum(bool(px[3]) for im in pieces.values() for px in im.get_flattened_data()) == 522
    before = preview.read_reviewed(base / MODULE)
    updates, foregrounds, receipts, changed_rows = {}, [], [], []
    guards = ('game','style','map','tileset','id','quadrant','sourceHash','sourceFiles','sourceCells',
              'sourceCollision','sourcePriority','sourcePalettes','sourceWarps')
    for game in ('gold','silver','crystal'):
        data = review.source(cache, game); md = data['maps'][MAP]
        assert md['width'] == 4 and md['height'] == 5 and not md['objects']
        scoped = [r for r in before if r.get('game') == game and r.get('style') == 'gen3' and r.get('map') == MAP]
        at = lambda x,y: next(r for r in scoped if [x,y] in r.get('sourceCells',[]))
        head, foot, right = at(0,6), at(0,7), at(1,6)
        assert head['id'] == foot['id'] == 20 and head['quadrant'] == 0 and foot['quadrant'] == 2
        assert head['sourceHash'] == HEAD and foot['sourceHash'] == FOOT
        assert right['sourceCollision'] == at(1,7)['sourceCollision'] == 0
        assert right['donor'] == at(1,7)['donor']
        for x,y in ((0,6),(0,7),(1,6),(1,7)):
            row = at(x,y); cell = review.cell_info(cache,game,data,md['tileset'],row['id'],row['quadrant'])
            assert cell['sourceHash'] == row['sourceHash'] and cell['collision'] == row['sourceCollision']
            assert data['fingerprints'][md['tileset']] == row['sourceFiles']
            assert [bool(v.get('priority')) for v in cell['attributes']] == row['sourcePriority']
            assert [v.get('palette',1) for v in cell['attributes']] == row['sourcePalettes']
        assert not any(w['x'] <= 1 and 6 <= w['y'] <= 7 for w in md['warps'])
        receipts.append(dict(game=game,objects=md['objects'],bgEvents=md['bgEvents'],warps=md['warps'],
            map_definition_sha256=sha(json.dumps(canonical(md),separators=(',',':')).encode())))
        updates[game] = {}
        for old in (head, foot):
            row = copy.deepcopy(old); row.pop('sourceColors',None)
            row.update(kind='native', donor=copy.deepcopy(right['donor']), role='celadon_native_bed_matching_carpet',
                compositionPixelHash=right['compositionPixelHash'],
                reviewedNativeCounterpart=dict(role='bed_background_matching_room_carpet',pixel_scale=1,
                    geometry='Original bed core cleared to its exact checked neighboring native carpet'),
                evidence='Clear only the original blocked bed core to the exact neighboring native carpet, under the complete native20x29 CrystalDust bed foreground. Collision, actors, warps, scripts, original palettes and priorities stay unchanged.')
            assert all(row.get(k) == old.get(k) for k in guards)
            updates[game][str(old['quadrant'])] = row; changed_rows.append(row)
        for (x,y), asset in assets.items():
            row = {k:copy.deepcopy(head[k]) for k in guards if k in head}
            row.update({k:v for k,v in asset.items() if k != 'cell'})
            row.update(kind='third_party', furniture='celadon_mansion_bed', anchorX=0, anchorY=6,
                x=x,y=y+6,frontY=128,footX=0,footY=7,footId=20,footQuadrant=2,footHash=FOOT,
                role='crystaldust_complete_celadon_mansion_bed',status='reviewed',
                credit='CrystalDust by Sierraffinity and contributors; complete native20x29 medical bed at original pixel size.',
                sourceUrl='https://github.com/Sierraffinity/CrystalDust',
                evidence='Complete native bed left-aligned at0,99 in original blocked cells0,6/0,7. Only4 native pixels extend into the source-clear right aisle. No native pixels are cropped, scaled or recolored. Both source core hashes are checked; physical front128 preserves actor depth. Room has no NPCs and its warps/interactions remain unchanged.')
            foregrounds.append(row)
    body = 'local updates=' + lua(canonical(updates)) + '''\nlocal changed=0
for index,row in ipairs(rows)do
 local game=updates[row.game]
 local replacement=game and row.style=='gen3'and row.map=='CELADON_MANSION_2F'and row.id==20 and game[tostring(row.quadrant)]
 if replacement then rows[index]=replacement;changed=changed+1 end
end
assert(changed==6,'Celadon bed source core changed')'''
    append(mod,base,MODULE,'-- BEGIN CELADON COMPLETE NATIVE BED',body)
    append(mod,base,FURNITURE,'-- BEGIN CELADON COMPLETE NATIVE BED',
           'for _,row in ipairs('+lua(canonical(foregrounds))+')do rows[#rows+1]=row end')
    after = preview.read_reviewed(mod / MODULE)
    assert len(before) == len(after) and sum(x != y for x,y in zip(before,after)) == 6
    assert all(x == y or all(x.get(k) == y.get(k) for k in guards) for x,y in zip(before,after))
    native_fixture = dict(assets={item['asset']:dict(hash=item['assetFileHash'],mask=''.join('1' if px[3] else '0'
                          for px in pieces[key].get_flattened_data())) for key,item in assets.items()},
                          maps={game:{MAP:dict(tileset='TILESET_MANSION',width=4,height=5)}for game in updates})
    (mod/'tests/celadon_bed_native_alpha.lua').write_text('return '+lua(canonical(native_fixture))+'\n')
    proof = dict(status='passed',source_asset=SOURCE,source_png_sha256=sha(source.read_bytes()),
        source_rgba_sha256=sha(bed.tobytes()),source_size=[20,29],source_rom_sha256='51196cba923c315d0088b747b5cdee704f2ac057cd493f9ddf226fb7227302cf',
        whole_native_opaque_pixels=522,complete_native_pixel_scale=1,alpha_unchanged=True,
        complete_native_RGBA_preserved=True,
        source_provenance='assets/third_party/johto-hacks/crystaldust-ship-beds/provenance.json',
        source_provenance_sha256=sha((mod/'assets/third_party/johto-hacks/crystaldust-ship-beds/provenance.json').read_bytes()),
        placement_xy=[0,99],bounds_xyxy=[0,99,20,128],source_blocked_core=[[0,6],[0,7]],
        decorative_right_extension_pixels=4,source_clear_right_cells=[[1,6],[1,7]],
        source_core_rows_changed=6,foreground_rows_added=12,source_guards_unchanged=list(guards),
        no_NPC_or_warp_overlap=True,source_map_receipts=receipts,assets=list(assets.values()))
    (folder/'provenance.json').write_text(json.dumps(canonical(proof),indent=2)+'\n')
    (out/'proof.json').write_text(json.dumps(canonical(proof),indent=2)+'\n')
    print(json.dumps(dict(status='passed',source_rows=6,foreground_rows=12,native_opaque_pixels=522)))


if __name__ == '__main__': main()
