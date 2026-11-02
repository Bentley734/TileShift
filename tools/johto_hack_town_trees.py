"""Use a complete native three-cell FireGold pine for GSC's narrow town trees.

No scaling or tier removal. Middle and roots retain the original two-cell
footprint; the complete top cell becomes a cached transparent overhang.
"""
import argparse
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace

from PIL import Image
import catalog
import preview
import gen2_extended_review as review
from johto_hack_extras import connected_mask, clear_background
from johto_hack_flora import cell, write_changed_rows
from newbark_building_review import lua

ROOT = Path(__file__).resolve().parents[1]
EXTRACTS = ROOT.parent / '.work/tileshift-firegold/firegold'
OUT = ROOT.parent / '.work/tileshift-two-cell-trees/authoring'
DEST = ROOT / 'assets/third_party/johto-hacks/town-trees'
PAIR = '082d4a94_082d4b54'
ROM_SHA = 'c65f698ffb844b99836a36dc0752e8b57ebd45be53be364cb3cfe52aa0cc74ce'
SOURCE_SHA = '11c9fd74cc6f5fc8635cccb3568a669db70fbbb434ac0dbc9a95ffaada3732f1'
URL = 'https://www.pokecommunity.com/threads/pok%C3%A9mon-fire-gold-1-4.473130/'
ROLES = {'dense_conifer_crown': 'middle.png', 'dense_conifer_trunk': 'bottom.png'}


def write_rows(path, rows, indexes):
    raw = path.read_bytes()
    if b'add((function()return {' in raw:
        write_changed_rows(path, rows, indexes)
        return
    assert b'return {' in raw
    lines = []; number = 0
    for line in raw.decode().splitlines(keepends=True):
        if line.startswith('  {'):
            if number in indexes:
                line = '  ' + lua(rows[number]) + (',\r\n' if line.endswith('\r\n') else ',\n')
            number += 1
        lines.append(line)
    assert number == len(rows)
    path.write_bytes(''.join(lines).encode())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    info = json.loads((EXTRACTS / 'catalog.json').read_text())
    assert info['rom_sha256'] == ROM_SHA
    native_map = next(m for m in info['maps'] if m['id'] == 'g46_m099')
    assert native_map['pair'] == PAIR
    assert [native_map['grid'][(18 + y) * native_map['width'] + 23] & 1023 for y in range(3)] == [600, 601, 608]
    atlas = Image.open(EXTRACTS / 'pairs' / PAIR / 'flat.png').convert('RGBA')
    original = Image.new('RGBA', (16, 48))
    for y, mid in enumerate((600, 601, 608)):
        original.paste(cell(atlas, mid), (0, y * 16))
    native = Image.open(EXTRACTS / 'maps/g46_m099-flat.png').convert('RGBA')
    assert original.tobytes() == native.crop((23*16, 18*16, 24*16, 21*16)).tobytes()
    assert catalog.sha(original.tobytes()) == SOURCE_SHA
    field_colors = set(cell(atlas, 8).get_flattened_data()) | set(cell(atlas, 9).get_flattened_data())
    mask = connected_mask(original, field_colors)
    sprite = clear_background(original, mask)
    assert sprite.size == (16, 48)
    images = {'whole.png': sprite, 'top.png': sprite.crop((0, 0, 16, 16)),
              'middle.png': sprite.crop((0, 16, 16, 32)), 'bottom.png': sprite.crop((0, 32, 16, 48))}
    joined = Image.new('RGBA', (16, 48))
    for y, name in enumerate(('top.png', 'middle.png', 'bottom.png')): joined.paste(images[name], (0, y*16))
    assert joined.tobytes() == sprite.tobytes()
    retained = sum(1 for pixel in sprite.get_flattened_data() if pixel[3])
    assert retained == 662
    folder = DEST if args.activate else OUT
    folder.mkdir(parents=True, exist_ok=True)
    for name, image in images.items(): image.save(folder / name)
    hashes = {name: catalog.sha((folder / name).read_bytes()) for name in images}
    provenance = dict(origin='Complete native three-cell narrow tree from the user-supplied FireGold1.4 ROM.',
        credit='FireGold1.4 by Tzx211 and contributors.', sourceUrl=URL,
        rom_sha256=ROM_SHA, source_pair=PAIR, source_map='g46_m099', top_cell=[23, 18],
        source_metatiles=[600, 601, 608], native_dimensions=[16, 48], pixel_scale=1,
        source_rgba_sha256=SOURCE_SHA, joined_actual_map_cells_exact=True,
        canopy_trunk_and_shadow_retained=True, removed_foliage_tiers=0,
        field_metatiles=[8, 9], core_sections=['middle.png', 'bottom.png'], decorative_top_cell_offset=[0, -1],
        omitted_field_coordinates=[list(p) for p in sorted(mask, key=lambda p: (p[1], p[0]))],
        omitted_field_colors=[list(c) for c in sorted(field_colors)],
        opaque_source_pixels_retained=retained, alpha_bounds=sprite.getchannel('A').getbbox(),
        files=hashes, roms_not_bundled=True)
    (folder / 'provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')
    if not args.activate:
        print(json.dumps(dict(output=str(folder), files=hashes, native_pixels_retained=retained)))
        return
    cache = Path(os.environ['APPDATA']) / 'pokemon-love2d'; packed = {}; staged = {}; checked = []; definitions = {}
    ground = next(copy.deepcopy(r['donor']) for r in preview.read_reviewed(ROOT / 'mappings/gen2_outdoor.lua')
                  if r['role']=='short_nonencounter_grass' and r['donor']['id']==1)
    for path in sorted((ROOT / 'mappings').glob('*.lua')):
        rows = preview.read_reviewed(path); indexes = set()
        for number, row in enumerate(rows):
            if row.get('game') not in ('gold', 'silver', 'crystal') or row.get('role') not in ROLES:
                continue
            if 'sourceCells' not in row:
                game = row['game']
                if game not in definitions:
                    definitions[game] = catalog.read_lua(cache / game / 'data/generated/maps.lua')
                definition = definitions[game][row['map']]
                row['sourceCells'] = [[i % definition['width'] * 2 + row['quadrant'] % 2,
                                       i // definition['width'] * 2 + row['quadrant'] // 2]
                                      for i, block in enumerate(definition['blocks']) if block == row['id']]
                assert row['sourceCells']
            name = ROLES[row['role']]
            row.update(kind='third_party', asset=(DEST / name).relative_to(ROOT).as_posix(),
                       assetFileHash=hashes[name], base=copy.deepcopy(row.get('base') or ground),
                       credit=provenance['credit'], sourceUrl=URL,
                       evidence='Complete native FireGold16x48 town pine: original top600, middle601 and roots608. '
                       'The original two-cell core retains middle and roots; the intact top overhangs one cell above, '
                       'including over the trunk of the tree above it. All native pixels retain their original size '
                       'without scaling or omitted foliage. Only native field pixels become transparent over checked ground. '
                       'Original source collision, map roles, layouts, interactions and events remain unchanged.')
            row.pop('donor', None); row.pop('assetPixelHash', None)
            if row['role']=='dense_conifer_crown':
                row['canopy'] = dict(asset=(DEST / 'top.png').relative_to(ROOT).as_posix(), hash=hashes['top.png'])
            row['compositionPixelHash'] = catalog.sha(preview.replacement_image(cache, row, packed, ROOT).tobytes())
            indexes.add(number); checked.append(row)
        if indexes: staged[path] = rows, indexes
    assert len(checked) == 338
    proof = review.validate_batch(checked, SimpleNamespace(cache=cache, engine=ROOT.parent / '.tools/engine-0395', output=OUT), ROOT)
    assert proof['rows_accepted'] == 338 and proof['rejected'] == 0
    for path, (rows, indexes) in staged.items(): write_rows(path, rows, indexes)
    proof.update(native_pixel_scale=1, removed_foliage_tiers=0, native_pixels_retained=retained,
                 exact_three_sections_join=True, updated_files={p.name:len(i) for p, (_, i) in staged.items()})
    (OUT / 'proof.json').write_text(json.dumps(proof, indent=2)+'\n')
    print(json.dumps(proof))


if __name__ == '__main__': main()
