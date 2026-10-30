"""Reapply the reviewed Azalea floor recipes after regenerating gym mappings.

Run with --activate to save; all three games are validated before any write.
The explicit source fingerprints and coordinates remain those of the maps.
"""
import argparse
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace

import catalog
import preview
import gen2_extended_review as e
from center_mart_overhang_review import write_rows
from johto_remaining_review import ART

ROOT = Path(__file__).resolve().parents[1]
PINK_PLANTERS = {(1, 6), (1, 7), (8, 6), (8, 7)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    cache = Path(os.environ['APPDATA']) / 'pokemon-love2d'
    recipes = json.loads((ROOT / 'tools/azalea_floor_art.json').read_text())['recipes']
    output = ROOT.parent / '.work/tileshift-azalea-approved-review'
    output.mkdir(exist_ok=True)
    files, checked, packed = {}, [], {}
    for name in ('johto_gyms_finish', 'johto_shared_finish'):
        path = ROOT / 'mappings' / (name + '.lua')
        rows = []
        for source in preview.read_reviewed(path):
            if source.get('map') != 'AZALEA_GYM':
                rows.append(source)
                continue
            role = source['role']
            assert role in recipes, ('Unreviewed Azalea role', role)
            cells = source['sourceCells']
            groups = [[cell] for cell in cells] if 'flowerpot' in role else [cells]
            for group in groups:
                row = copy.deepcopy(source)
                for key in ART:
                    row.pop(key, None)
                key = role + (':pink' if 'flowerpot' in role and tuple(group[0]) in PINK_PLANTERS else '')
                row.update(copy.deepcopy(recipes[key]))
                row['sourceCells'] = copy.deepcopy(group)
                if 'flowerpot' in role:
                    row['x'], row['y'] = group[0]
                row['compositionPixelHash'] = catalog.sha(preview.replacement_image(cache, row, packed, ROOT).tobytes())
                rows.append(row)
                checked.append(row)
        files[path] = rows
    print(e.validate_batch(checked, SimpleNamespace(cache=cache, engine=ROOT.parent / '.tools/engine-0395', output=output), ROOT))
    all_rows = [row for path in (ROOT / 'mappings').glob('*.lua') for row in files.get(path, preview.read_reviewed(path))]
    for game in ('gold', 'silver', 'crystal'):
        preview.map_preview(cache, output, game, 'AZALEA_GYM', game + '-azalea', all_rows, packed, 3, ROOT)
    if args.activate:
        for path, rows in files.items():
            write_rows(path, rows)


if __name__ == '__main__':
    main()
