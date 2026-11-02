"""Use an intact native FireGold two-cell pine for GSC's narrow town trees.

No scaling, tier removal or runtime changes. The source tree is an actual
vertically adjacent16x16 pair, independently checked in its native map.
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
PAIR = '082d4a94_082d4dc4'
ROM_SHA = 'c65f698ffb844b99836a36dc0752e8b57ebd45be53be364cb3cfe52aa0cc74ce'
SOURCE_SHA = 'f8e569303546e1fe49a1b66c2a8973ad9198c5786018874ef7d36978d2b59af6'
URL = 'https://www.pokecommunity.com/threads/pok%C3%A9mon-fire-gold-1-4.473130/'
ROLES = {'dense_conifer_crown': 'top.png', 'dense_conifer_trunk': 'bottom.png'}


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
    native_map = next(m for m in info['maps'] if m['id'] == 'g44_m042')
    assert native_map['pair'] == PAIR
    assert [native_map['grid'][(29 + y) * native_map['width'] + 26] & 1023 for y in (0, 1)] == [696, 552]
    atlas = Image.open(EXTRACTS / 'pairs' / PAIR / 'flat.png').convert('RGBA')
    original = Image.new('RGBA', (16, 32))
    for y, mid in enumerate((696, 552)):
        original.paste(cell(atlas, mid), (0, y * 16))
    native = Image.open(EXTRACTS / 'maps/g44_m042-flat.png').convert('RGBA')
    assert original.tobytes() == native.crop((26*16, 29*16, 27*16, 31*16)).tobytes()
    assert catalog.sha(original.tobytes()) == SOURCE_SHA
    field_colors = set(cell(atlas, 1).get_flattened_data())
    mask = connected_mask(original, field_colors)
    sprite = clear_background(original, mask)
    assert sprite.size == (16, 32)
    images = {'whole.png': sprite, 'top.png': sprite.crop((0, 0, 16, 16)),
              'bottom.png': sprite.crop((0, 16, 16, 32))}
    joined = Image.new('RGBA', (16, 32))
    joined.paste(images['top.png'], (0, 0)); joined.paste(images['bottom.png'], (0, 16))
    assert joined.tobytes() == sprite.tobytes()
    retained = sum(1 for pixel in sprite.get_flattened_data() if pixel[3])
    assert retained > 200
    folder = DEST if args.activate else OUT
    folder.mkdir(parents=True, exist_ok=True)
    for name, image in images.items(): image.save(folder / name)
    hashes = {name: catalog.sha((folder / name).read_bytes()) for name in images}
    provenance = dict(origin='Complete native narrow two-cell tree from the user-supplied FireGold1.4 ROM.',
        credit='FireGold1.4 by Tzx211 and contributors.', sourceUrl=URL,
        rom_sha256=ROM_SHA, source_pair=PAIR, source_map='g44_m042', top_cell=[26, 29],
        source_metatiles=[696, 552], native_dimensions=[16, 32], pixel_scale=1,
        source_rgba_sha256=SOURCE_SHA, joined_actual_map_cells_exact=True,
        canopy_trunk_and_shadow_retained=True, removed_foliage_tiers=0,
        field_metatile=1, omitted_field_coordinates=[list(p) for p in sorted(mask, key=lambda p: (p[1], p[0]))],
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
                       evidence='Intact native FireGold16x32 town pine, original adjacent metatiles696 above552. '
                       'The complete crown, trunk and shadow retain their exact native pixels. No scaling, tier removal '
                       'or footprint change. Only outside-connected field pixels become transparent over checked ground. '
                       'Original source collision, map roles, layouts, interactions and events remain unchanged.')
            row.pop('donor', None); row.pop('assetPixelHash', None)
            row['compositionPixelHash'] = catalog.sha(preview.replacement_image(cache, row, packed, ROOT).tobytes())
            indexes.add(number); checked.append(row)
        if indexes: staged[path] = rows, indexes
    assert len(checked) == 338
    proof = review.validate_batch(checked, SimpleNamespace(cache=cache, engine=ROOT.parent / '.tools/engine-0395', output=OUT), ROOT)
    assert proof['rows_accepted'] == 338 and proof['rejected'] == 0
    for path, (rows, indexes) in staged.items(): write_rows(path, rows, indexes)
    proof.update(native_pixel_scale=1, removed_foliage_tiers=0, native_pixels_retained=retained,
                 exact_two_halves_join=True, updated_files={p.name:len(i) for p, (_, i) in staged.items()})
    (OUT / 'proof.json').write_text(json.dumps(proof, indent=2)+'\n')
    print(json.dumps(proof))


if __name__ == '__main__': main()
