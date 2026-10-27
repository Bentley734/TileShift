"""Finalize a built-in imagegen Sprout Tower candidate at the source footprint.

Only crop, nearest-neighbor reduction and tile packing are performed here.
The original native ledges remain runtime imports, never redistributed pixels.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / '.tools/python'))
import catalog
from newbark_building_review import lua


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    source = ROOT.parent / '.work/tileshift-sprout-generated-reference.png'
    image = Image.open(source).convert('RGBA')
    assert image.size == (1122, 1402)
    folder = ROOT / 'assets/original/sprout-tower'
    folder.mkdir(exist_ok=True)
    # Upper tower is one complete design. The full lower facade is reduced
    # separately to 48px so its posts fit BETWEEN the existing 8px ledges.
    whole = Image.new('RGBA', (64, 80))
    whole.paste(image.crop((68, 6, 1056, 1055)).resize((64, 63), Image.Resampling.NEAREST), (0, 0))
    whole.paste(image.crop((165, 1055, 960, 1340)).resize((48, 17), Image.Resampling.NEAREST), (8, 63))
    whole.save(folder / 'tower.png')
    tiles = {}
    for y in range(5):
        for x in range(4):
            path = folder / f'cell-{x}-{y}.png'
            tile = whole.crop((x * 16, y * 16, (x + 1) * 16, (y + 1) * 16))
            tile.save(path)
            assert Image.open(path).tobytes() == tile.tobytes()
            tiles[x, y] = {'asset': path.relative_to(ROOT).as_posix(),
                           'hash': hashlib.sha256(path.read_bytes()).hexdigest(), 'preserveRects': []}
    rows = catalog.plain(catalog.LUA.execute((ROOT / 'mappings/buildings_extended.lua').read_text(encoding='utf-8-sig')))
    replacements = {}
    for row in rows:
        if row['role'] != 'architecture_sprout_pagoda':
            continue
        x, y = row['x'] - 22, row['y'] - 1
        assert 0 <= x < 4 and 0 <= y < 5 and row['base']['id'] == 1
        overlay = dict(tiles[x, y])
        if y == 4 and x in (0, 3):
            overlay['preserveRects'] = [[0 if x == 0 else 8, 0, 8, 16]]
        row['artOverlay'] = overlay
        row['evidence'] += ' User-supplied Gemini tower design refined with built-in imagegen; complete tower fitted to original64x80 source footprint, full lower facade48x17 between the existing8px native side ledges. Original ledge strips, source cells, door warp23,5 and all surrounding town pixels remain unchanged. Overlay PNGs have independent SHA256 guards.'
        replacements[row['game'], row['x'], row['y']] = row
    assert len(replacements) == 60
    provenance = {'origin': 'Built-in imagegen, based on two user-supplied Gemini images',
        'source_references': ['Gemini_Generated_Image_h9vcnxh9vcnxh9vc.jpg', 'Gemini_Generated_Image_z2nypgz2nypgz2ny.jpg'],
        'generated_source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'size_px': [64, 80], 'source_map': 'VIOLET_CITY', 'source_rect_cells': [22, 1, 4, 5],
        'native_ledge_rectangles_preserved': [[0, 64, 8, 16], [56, 64, 8, 16]],
        'lower_facade_box_px': [8, 63, 48, 17], 'original_entrance_cell': [23, 5],
        'processing': 'Crop, nearest-neighbor reduction of complete upper/lower components, lossless16px tile packing; no drawn pixels or source gameplay edits',
        'prompt': 'Refine only the reference Sprout Tower, three stories, warm brown tiled upper hip roof and two narrow eaves, cream walls, dark barred windows, wooden posts and full left-of-center entrance; transparent background, no trees, ledges, paths, signs or scenery. Fit logical64x80 footprint, door in bottom cell x16..31.',
        'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.glob('*.png'))}}
    (folder / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    if args.activate:
        target = ROOT / 'mappings/buildings_extended.lua'
        lines = target.read_text(encoding='utf-8-sig').splitlines(keepends=True)
        changed = 0
        for i, line in enumerate(lines):
            if '"architecture_sprout_pagoda"' not in line:
                continue
            old = catalog.plain(catalog.LOAD('return ' + line.strip().rstrip(','), 'sprout-row'))
            lines[i] = '  ' + lua(replacements[old['game'], old['x'], old['y']]) + ',\n'
            changed += 1
        assert changed == 60
        target.write_text(''.join(lines), encoding='utf-8')
    print(json.dumps({'tiles': 20, 'guarded_rows': 60, 'activated': args.activate, 'provenance': str(folder / 'provenance.json')}))


if __name__ == '__main__':
    main()
