"""Private complete Blue-house feature profiles; production remains unchanged."""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
from PIL import Image, ImageDraw
import catalog
import preview
import gen2_extended_review as ext
from gen2_cave_review import contact
from interior_review import Imports, write_rows

ROOT = Path(__file__).resolve().parents[2]


def main():
    cache = Path(os.environ['APPDATA']) / 'pokemon-love2d'
    mod = ROOT / 'TileShift'
    output = ROOT / '.work/tileshift-house-variant-review'
    output.mkdir(parents=True, exist_ok=True)
    imports = Imports(cache, ROOT / '.work/tileshift-catalog')
    packed = {}
    old = json.loads((ROOT / '.work/tileshift-house-review/household-expanded-candidates.json').read_text())
    art = {}
    for row in old:
        label = row['role'].removeprefix('household_')
        art.setdefault(label, {k: row[k] for k in ('kind', 'base', 'parts', 'donor', 'compositionPixelHash') if k in row})

    def ref(mid):
        cell = imports.cell_index('firered')['house', mid]
        return {'game': 'firered', 'tileset': 'house', 'id': mid, 'hash': cell['pixel_sha256']}

    def part(mid, sx=0, sy=0, w=16, h=16, x=0, y=0):
        return {'donor': ref(mid), 'srcX': sx, 'srcY': sy, 'w': w, 'h': h, 'x': x, 'y': y}

    wall_parts = copy.deepcopy(art['wall']['parts'])
    painting = {'kind': 'native_composite', 'base': ref(1), 'parts': wall_parts + [
        part(388, sx=1, sy=9, w=14, h=7, x=1, y=1),
        part(389, sx=1, w=14, h=7, x=1, y=8)]}
    picture = preview.replacement_image(cache, painting, packed, mod)
    painting['compositionPixelHash'] = catalog.sha(picture.tobytes())
    art['painting'] = painting
    # Full flattened native planes are deliberate: mid alone omits the crown.
    art['plant_head'], art['plant_base'] = {'donor': ref(87)}, {'donor': ref(95)}
    native_painting = Image.new('RGBA', (16, 32))
    for i, mid in enumerate((388, 389)):
        native_painting.paste(preview.native_donor(cache, ref(mid), packed), (0, i * 16))
    assert picture.crop((1, 1, 15, 15)).tobytes() == native_painting.crop((1, 9, 15, 23)).tobytes()
    wall = preview.replacement_image(cache, art['wall'], packed, mod)
    for y in range(16):
        for x in range(16):
            if not (1 <= x < 15 and 1 <= y < 15):
                assert picture.getpixel((x, y)) == wall.getpixel((x, y))
    pictures = {label: preview.replacement_image(cache, row, packed, mod) for label, row in art.items()}
    contact(output / 'complete-extra-household-features.png', 'Whole native painting, plant crown, pot and existing complete household frames', list(pictures.items()), columns=7)

    # Each model is read independently from this cartridge's actual Blue house.
    # Paired furniture is emitted only when every original feature cell matches.
    profiles = [
        ('left_bookcase', ((0, 0, 'bookcase_head'), (0, 1, 'bookcase_base'))),
        ('right_bookcase', ((7, 0, 'bookcase_head'), (7, 1, 'bookcase_base'))),
        ('plain_table', ((3, 3, 'table_nw'), (4, 3, 'table_ne'), (3, 4, 'table_sw'), (4, 4, 'table_se'))),
        ('complete_plant', ((0, 6, 'plant_head'), (0, 7, 'plant_base'))),
        ('complete_entry_mat', ((2, 7, 'rug_left'), (3, 7, 'rug_right'))),
    ]
    singles = [(3, 0, 'painting'), (5, 0, 'window')]
    rows, report = [], []
    active = preview.read_reviewed(mod / 'mappings/interiors.lua')
    active_positions = {(r['game'], r.get('map'), r.get('x'), r.get('y')): r for r in active if r.get('x') is not None}
    for game in ('red', 'blue', 'yellow'):
        maps = imports.table(game, 'maps')
        index = imports.cell_index(game)
        fingerprints = {r['tileset']: r['fingerprints'] for r in json.loads((imports.catalogs / f'{game}.json').read_text())['tilesets']}

        def cells_for(definition):
            return {(i % definition['width'] * 2 + q % 2, i // definition['width'] * 2 + q // 2): index[definition['tileset'], bid, q]
                    for i, bid in enumerate(definition['blocks']) for q in range(4)}

        seed = cells_for(maps['BLUES_HOUSE'])

        def identity(cell):
            return tuple(json.dumps(cell.get(k), sort_keys=True) for k in ('grayscale_pixel_sha256', 'walkable_tiles', 'warp_tile_present', 'grass_tile_present', 'source_pixels_complete'))

        for map_id, definition in sorted(maps.items()):
            if definition['tileset'] not in {'HOUSE', 'REDS_HOUSE_1', 'REDS_HOUSE_2'}:
                continue
            cells, selected, complete = cells_for(definition), {}, []

            def stamp(xy, label):
                assert xy not in selected or selected[xy] == label
                selected[xy] = label

            for (x, y), cell in cells.items():
                for sx, sy, label in singles:
                    if identity(cell) == identity(seed[sx, sy]):
                        stamp((x, y), label)
                for name, shape in profiles:
                    sx, sy, _ = shape[0]
                    if all((x + px - sx, y + py - sy) in cells and identity(cells[x + px - sx, y + py - sy]) == identity(seed[px, py]) for px, py, _ in shape):
                        for px, py, label in shape:
                            stamp((x + px - sx, y + py - sy), label)
                        complete.append({'feature': name, 'x': x, 'y': y})
                        if name == 'plain_table':
                            for dy in range(2):
                                for dx, sl, label in ((-1, 2, 'chair_left'), (2, 5, 'chair_right')):
                                    xy = x + dx, y + dy
                                    if xy in cells and identity(cells[xy]) == identity(seed[sl, 3 + dy]):
                                        stamp(xy, label)
            added = 0
            for (x, y), label in sorted(selected.items(), key=lambda item: (item[0][1], item[0][0])):
                if (game, map_id, x, y) in active_positions:
                    previous = active_positions[game, map_id, x, y]
                    assert all(previous.get(k) == v for k, v in art[label].items()), 'Existing position has different household art'
                    continue
                cell = cells[x, y]
                assert cell['source_pixels_complete']
                rows.append({'game': game, 'style': 'gen3', 'map': map_id, 'tileset': definition['tileset'],
                    'id': cell['block_id'], 'quadrant': cell['quadrant'], 'x': x, 'y': y, 'sourceCells': [[x, y]],
                    'sourceHash': cell['grayscale_pixel_sha256'], 'sourceFiles': fingerprints[definition['tileset']],
                    'status': 'reviewed', 'role': 'household_' + label,
                    'evidence': 'PRIVATE exact complete Blue-house profile candidate. Each cartridge source is independently matched by rendered pixels, complete source image, walkability and warp/grass flags. Whole paired bookcase, plant, table and32px mat profiles; chairs only beside the matching complete table. Painting preserves the native14x14 complete frame, plant uses all native planes to retain the whole leaf crown and pot. Actual town-map pickup remains a native object on the table. Geometry, interactions and events remain unchanged. Pending full room visual review.', **copy.deepcopy(art[label])})
                added += 1
            if added:
                report.append({'game': game, 'map': map_id, 'positions': added, 'complete_features': complete})
    catalogs = {game: json.loads((imports.catalogs / f'{game}.json').read_text()) for game in ('red', 'blue', 'yellow', 'firered', 'emerald')}
    preview.verify(rows, cache, catalogs, mod)
    checks = ext.validate_batch(rows, SimpleNamespace(cache=cache, engine=ROOT / '.tools/engine-0395', output=output), mod)
    write_rows(rows, output / 'candidates.lua')
    (output / 'candidates.json').write_text(json.dumps(rows, indent=2))
    (output / 'source-feature-proof.json').write_text(json.dumps({'rows': len(rows), 'contexts': report,
        'native_painting_complete_pixels': 196, 'painting_changed_pixels': 0,
        'plant_complete_planes': True, 'runtime': checks}, indent=2))
    contexts = [r['map'] for r in report if r['game'] == 'red']
    sheet = Image.new('RGB', (1340, 42 + ((len(contexts) + 4) // 5) * 296), '#18202c')
    draw = ImageDraw.Draw(sheet)
    draw.text((12, 12), 'All23 exact-profile source rooms: private complete furniture; remaining original details stay visible.', fill='white')
    for i, map_id in enumerate(contexts):
        stem = 'red-' + map_id.lower()
        preview.map_preview(cache, output, 'red', map_id, stem, active + rows, packed, 4, mod)
        picture = Image.open(output / (stem + '-after-native.png')).convert('RGB')
        factor = min(256 / picture.width, 256 / picture.height)
        picture = picture.resize((int(picture.width * factor), int(picture.height * factor)), Image.Resampling.NEAREST)
        x, y = 12 + i % 5 * 266, 42 + i // 5 * 296
        draw.text((x, y), map_id, fill='white')
        sheet.paste(picture, (x, y + 24))
    sheet.save(output / 'all-source-room-contexts.png')
    print(json.dumps({'private_rows': len(rows), 'contexts': len(report), 'runtime': checks, 'production_writes': 0}))


if __name__ == '__main__':
    main()
