"""Author the approved native CrystalDust New Bark domestic furniture privately."""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
from types import SimpleNamespace

from PIL import Image, ImageDraw, ImageFont

WORKSPACE = next(path for path in Path(__file__).resolve().parents
                 if (path / '.tools/python').is_dir() and (path / '.work').is_dir())
BASE_RUNTIME = '33dc56e167d517da229f37ecc749057ab7b6ff256795854af6bc1564757e6497'
BASE_FREEZE = WORKSPACE / '.work/tileshift-v0442-checkpoint/frozen.json'
DEFAULT_OUT = WORKSPACE / '.work/tileshift-newbark-crystaldust/domestic'
DONORS = WORKSPACE / '.work/tileshift-newbark-furniture-options/crystaldust'
CACHE = Path('C:/Users/LSDMTHC/AppData/Roaming/pokemon-love2d')
ASSET_DIR = 'assets/third_party/johto-hacks/newbark-crystaldust'
STEM = 'newbark_crystaldust_domestic'
GAMES = ('gold', 'silver', 'crystal')
MAPS = ('PLAYERS_HOUSE_1F', 'PLAYERS_HOUSE_2F', 'PLAYERS_NEIGHBORS_HOUSE', 'ELMS_HOUSE')
REVIEWED_BINDING = 'f99747d9a50fbaf37dd31a773fe40b647a66011fd93672ac530cd9256bd1d146'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n', encoding='utf-8')


def identity(row):
    return tuple(row.get(key) for key in ('game', 'style', 'tileset', 'id', 'quadrant', 'map', 'x', 'y'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mod-root', type=Path, required=True, help='Exact published v0.44.2 source stage')
    parser.add_argument('--output', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--inventory', action='store_true')
    parser.add_argument('--validate', action='store_true')
    args = parser.parse_args()
    root, out = args.mod_root.resolve(), args.output.resolve()
    assert out.is_relative_to(WORKSPACE / '.work') and out != root
    out.mkdir(parents=True, exist_ok=True)
    frozen = read(BASE_FREEZE)
    assert frozen['runtime_inputs']['sha256'] == BASE_RUNTIME
    assert read(root / 'manifest.json')['version'] == '0.44.2'
    assert all(sha(root / name) == value for name, value in frozen['source_files'].items())
    sys.path[:0] = [str(WORKSPACE / '.tools/python'), str(root / 'tools')]
    import catalog
    import preview
    import gen2_extended_review as neutral
    from center_mart_overhang_review import write_rows
    import interior_review
    interior_review.WORKSPACE = WORKSPACE
    from interior_review import Imports
    from validate_gpu import runtime_fingerprint

    assert runtime_fingerprint(root) == frozen['runtime_inputs']
    provenance = read(DONORS / 'provenance.json')
    approved = {row['id']: row for row in provenance['candidates']}
    for key in ('CD-03', 'CD-04', 'CD-05', 'CD-06', 'CD-07'):
        assert sha(DONORS / approved[key]['output']) == approved[key]['output_png_sha256']
    images = {key: Image.open(DONORS / approved[key]['output']).convert('RGBA')
              for key in ('CD-03', 'CD-04', 'CD-05', 'CD-06', 'CD-07')}
    assert images['CD-03'].size == images['CD-04'].size == images['CD-05'].size == (16, 32)
    kitchen = Image.new('RGBA', (48, 32))
    # Preserve CrystalDust's complete joined native sink/hob arrangement.
    for column, key in enumerate(('CD-03', 'CD-04', 'CD-05')):
        kitchen.alpha_composite(images[key], (column * 16, 0))
    television, radio = Image.new('RGBA', (16, 32)), Image.new('RGBA', (16, 32))
    television.alpha_composite(images['CD-06'], (0, 6))
    radio.alpha_composite(images['CD-07'], (0, 8))
    assert all(kitchen.getpixel((x, y))[3] == 255 for y in range(8, 23) for x in (14, 15, 16, 17)), 'Interior counter/base join is transparent'
    for key, canvas, offset in (('CD-06', television, (0, 6)), ('CD-07', radio, (0, 8))):
        assert canvas.crop((*offset, offset[0] + images[key].width, offset[1] + images[key].height)).tobytes() == images[key].tobytes()
        assert sum(pixel[3] > 0 for pixel in canvas.get_flattened_data()) == sum(pixel[3] > 0 for pixel in images[key].get_flattened_data())
    module_names = list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]", (root / 'main.lua').read_text())))
    active = []
    for module in module_names:
        for row in preview.read_reviewed(root / module):
            if row['game'] in GAMES and row['style'] == 'gen3':
                active.append((module, row))
    imp = Imports(CACHE, WORKSPACE / '.work/tileshift-catalog')
    source_maps = {game: imp.table(game, 'maps') for game in GAMES}

    def selected(game, map_id, x, y):
        definition = source_maps[game][map_id]
        bid = definition['blocks'][y // 2 * definition['width'] + x // 2]
        q = y % 2 * 2 + x % 2
        applicable = [(name, row) for name, row in active if row['game'] == game
                      and row['tileset'] == definition['tileset'] and row['id'] == bid
                      and row.get('quadrant') == q and row.get('map', map_id) == map_id
                      and (row.get('x') is None or (row['x'] // 2, row['y'] // 2) == (x // 2, y // 2))]
        applicable.sort(key=lambda item: (item[1].get('map') is not None, item[1].get('x') is not None))
        assert applicable, (game, map_id, x, y)
        return applicable[-1]

    placements = [dict(map='PLAYERS_HOUSE_1F', kind='kitchen', x=0, y=0, width=48, height=32,
                       interaction_cells=dict(stove=[0, 1], sink=[1, 1], fridge=[2, 1]))]
    placements += [dict(map=map_id, kind='television', x=x, y=0, width=16, height=32,
                        native_object_offset=[0, 6], source_tv_cell=[x, 1])
                   for map_id, x in (('PLAYERS_HOUSE_1F', 4), ('PLAYERS_HOUSE_2F', 4),
                                     ('PLAYERS_NEIGHBORS_HOUSE', 2), ('ELMS_HOUSE', 4))]
    placements += [dict(map=map_id, kind='radio', x=x, y=0, width=16, height=32,
                        native_object_offset=[0, 8], interaction_cells=dict(radio=[x, 1]))
                   for map_id, x in (('PLAYERS_HOUSE_2F', 3), ('PLAYERS_NEIGHBORS_HOUSE', 7))]
    canvases = dict(kitchen=kitchen, television=television, radio=radio)
    sources = []
    for game in GAMES:
        for map_id in MAPS:
            definition = source_maps[game][map_id]
            sources.append(dict(game=game, map=map_id, definition_sha256=digest(definition),
                                dimensions=[definition['width'] * 32, definition['height'] * 32],
                                warps=definition.get('warps', []), objects=definition.get('objects', []),
                                bg_events=definition.get('bgEvents', []), callbacks=definition.get('callbacks', [])))
    changes = []
    for game in GAMES:
        for placement in placements:
            for cy in range(placement['height'] // 16):
                for cx in range(placement['width'] // 16):
                    x, y = placement['x'] + cx, placement['y'] + cy
                    module, old = selected(game, placement['map'], x, y)
                    definition = source_maps[game][placement['map']]
                    source = imp.cell_index(game)[definition['tileset'], old['id'], old['quadrant']]
                    assert old['sourceHash'] == source['grayscale_pixel_sha256']
                    ref = dict(game=game, tileset=definition['tileset'], id=old['id'], quadrant=old['quadrant'],
                               hash=old['sourceHash'], monochrome=True, map=placement['map'], daytime='DAY')
                    preview.native_donor(CACHE, ref, imp.packed)
                    base = copy.deepcopy(old.get('base') or old.get('donor'))
                    if not base or base.get('game') != 'firered' or base.get('id') not in (1, 40):
                        base = dict(game='firered', tileset='player_house', id=40 if y == 0 else 1,
                                    hash='fd38c64864714cf6648e89dc3b28fa2ca879022c1d969074d488812eb23d6816' if y == 0
                                    else 'eba7bafe3b8bf236ae3602939529c34fad55c66c94aed6bb6cb4681b08fe2af6')
                    assert base['id'] == (40 if y == 0 else 1), (game, placement, x, y, base)
                    changes.append(dict(game=game, map=placement['map'], x=x, y=y,
                                        kind=placement['kind'], canvas_cell=[cx, cy], module=module,
                                        old_row=old, old_row_sha256=digest(old), base=base))
    import_files = {game + '/' + name: sha(CACHE / game / 'data/generated' / name)
                    for game in GAMES for name in ('maps.lua', 'tilesets.lua', 'palettes.lua', 'scripts.lua',
                                                   'text.lua', 'sprites.lua', 'constants.lua', 'initial_events.lua')}
    binding = dict(baseline_runtime=BASE_RUNTIME, maps=sources, placements=placements, import_files=import_files,
                   old_rows=[dict(game=c['game'], map=c['map'], x=c['x'], y=c['y'], module=c['module'],
                                  row_sha256=c['old_row_sha256'], base=c['base']) for c in changes],
                   donor_options={key: approved[key] for key in images})
    binding_sha = digest(binding)
    write(out / 'source-binding.json', dict(sha256=binding_sha, binding=binding))
    write(out / 'placements.json', placements)
    if args.inventory:
        print(json.dumps(dict(status='inventory', binding=binding_sha, source_cells=len(changes), placements=placements)))
        return
    assert binding_sha == REVIEWED_BINDING, ('New Bark domestic source/donor binding changed', binding_sha)

    validation = out / 'validation-root'
    for name in ('donor.lua', 'composition.lua', 'mapping.lua', 'session.lua'):
        path = validation / 'lib' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / 'lib' / name, path)
    asset_files = {}
    for kind, image in canvases.items():
        image.save(out / (kind + '-whole-native-foreground.png'))
        for cy in range(image.height // 16):
            for cx in range(image.width // 16):
                tile = image.crop((cx * 16, cy * 16, cx * 16 + 16, cy * 16 + 16))
                name = 'domestic-' + kind + '-' + str(cx) + '-' + str(cy) + '.png'
                target = ASSET_DIR + '/' + name
                path = out / target
                path.parent.mkdir(parents=True, exist_ok=True)
                tile.save(path)
                copied = validation / target
                copied.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, copied)
                asset_files[kind, cx, cy] = dict(asset=target, assetFileHash=sha(path),
                                               assetPixelHash=hashlib.sha256(tile.tobytes()).hexdigest())

    candidates, new_rows, supersessions = [], [], []
    existing = {identity(row): (module, row) for module, row in active}
    for change in changes:
        old = change['old_row']
        x, y, game, map_id = change['x'], change['y'], change['game'], change['map']
        row = {key: copy.deepcopy(value) for key, value in old.items() if key.startswith('source')}
        row.update(game=game, style='gen3', map=map_id, tileset=old['tileset'], id=old['id'], quadrant=old['quadrant'],
                   x=x, y=y, sourceCells=[[x, y]], status='reviewed', kind='third_party', base=change['base'],
                   role='newbark_crystaldust_domestic_' + change['kind'],
                   credit='CrystalDust by Sierraffinity and contributors. Native artwork from the user-supplied ROM.',
                   sourceUrl='https://github.com/Sierraffinity/CrystalDust',
                   evidence='Approved complete native CrystalDust furniture at original pixel size in the original New Bark room footprint. '
                            'Original stove, sink, fridge, TV and radio interaction coordinates are retained. Native source-layer alpha '
                            'reveals the selected original wall/floor donor. Source graphics, map layout, collision, events and NPC records '
                            'are frozen. Elm house computer-front stool removal remains intact.',
                   newBarkFurnitureReview=dict(binding=REVIEWED_BINDING, original_row_sha256=change['old_row_sha256'],
                                               original_module=change['module'], object_kind=change['kind'], pixel_scale=1))
        if change['kind'] == 'kitchen':
            row['newBarkFurnitureReview']['native_column_order'] = ['sink', 'stove', 'fridge']
            row['evidence'] += (' The approved native CrystalDust run retains sink left, stove middle and fridge right. '
                                'The original background scripts identify stove at0,1 and sink at1,1; integration must resolve '
                                'that text association for this selected visual arrangement.')
        row.update(asset_files[change['kind'], *change['canvas_cell']])
        image = preview.replacement_image(CACHE, row, imp.packed, validation)
        row['compositionPixelHash'] = hashlib.sha256(image.tobytes()).hexdigest()
        assert set(image.getchannel('A').get_flattened_data()) == {255}
        row = json.loads(json.dumps(row, sort_keys=True))
        candidates.append(row)
        if identity(row) in existing:
            module, original = existing[identity(row)]
            supersessions.append(dict(module=module, original_row=original,
                                      original_row_sha256=digest(original), candidate_row=row))
        else:
            new_rows.append(row)
    assert len(candidates) == 54
    assert len({identity(row) for row in candidates}) == 54
    write_rows(out / (STEM + '.lua'), new_rows)
    write(out / 'rows.json', candidates)
    write(out / 'supersessions.json', supersessions)

    # The stool removal is explicitly outside the furniture footprint.
    for game in GAMES:
        _, stool = selected(game, 'ELMS_HOUSE', 0, 2)
        assert stool['role'] == 'elms_house_pc_front_floor' and stool['donor']['id'] == 1
    neutral_result = None
    if args.validate:
        neutral_result = neutral.validate_batch(candidates, SimpleNamespace(cache=CACHE,
            engine=WORKSPACE / '.work/tileshift-engine-0400', output=out), validation)
        assert neutral_result['rows_accepted'] == 54 and neutral_result['rejected'] == 0

    candidate_index = {(row['game'], row['map'], row['x'], row['y']): row for row in candidates}
    render_cache = {}

    def render(row, candidate=False):
        key = digest(row)
        if key not in render_cache:
            render_cache[key] = preview.replacement_image(CACHE, row, imp.packed, validation if candidate else root)
        return render_cache[key]

    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15)
    previews = []
    for game in GAMES:
        for map_id in MAPS:
            original, cells, _, _ = imp.gb(game, map_id)
            before, after = original.copy(), original.copy()
            touched = []
            for cell in cells:
                for x, y in cell['coordinates']:
                    _, prior = selected(game, map_id, x, y)
                    before.paste(render(prior), (x * 16, y * 16))
                    candidate = candidate_index.get((game, map_id, x, y))
                    after.paste(render(candidate, True) if candidate else render(prior), (x * 16, y * 16))
                    if candidate:
                        touched.append((x, y))
            for y in range(after.height):
                for x in range(after.width):
                    if before.getpixel((x, y)) != after.getpixel((x, y)):
                        assert (x // 16, y // 16) in touched
            scale = 3
            width, height = original.size
            sheet = Image.new('RGB', (width * scale * 3 + 64, height * scale + 74), '#18212b')
            draw = ImageDraw.Draw(sheet)
            for index, (label, image) in enumerate((('Original ' + game, original), ('Published v0.44.2', before), ('CrystalDust proposal', after))):
                px = 16 + index * (width * scale + 16)
                draw.text((px, 12), label, font=font, fill='white')
                sheet.paste(image.resize((width * scale, height * scale), Image.Resampling.NEAREST), (px, 42))
            path = out / (game + '-' + map_id + '-comparison.png')
            sheet.save(path)
            after.save(out / (game + '-' + map_id + '-after.png'))
            previews.append(dict(game=game, map=map_id, path=path.name, png_sha256=sha(path)))
    asset_manifest = [dict(source=str(out / record['asset']), target=record['asset']) for record in asset_files.values()]
    asset_manifest = sorted({row['target']: row for row in asset_manifest}.values(), key=lambda row: row['target'])
    def portable(value):
        if isinstance(value, dict):
            return {key: portable(item) for key, item in value.items()}
        if isinstance(value, list):
            return [portable(item) for item in value]
        if isinstance(value, str):
            prefix = str(WORKSPACE / '.work/tileshift-firegold') + '\\'
            if value.startswith(prefix):
                return value[len(prefix):].replace('\\', '/')
        return value

    asset_proof = dict(status='passed', source_rom_sha256=provenance['source_rom_sha256'],
                       source_catalog_sha256=provenance['source_catalog_sha256'], source_options=portable({key: approved[key] for key in images}),
                       placements=placements, binding=REVIEWED_BINDING,
                       kitchen_column_order=['CD-03 sink', 'CD-04 hob', 'CD-05 fridge'],
                       kitchen_source_interactions=dict(stove=[0, 1], sink=[1, 1], fridge=[2, 1]),
                       kitchen_visible_appliances=dict(sink=[0, 1], stove=[1, 1], fridge=[2, 1]),
                       all_complete_objects_native_scale=True, source_alpha_preserved=True,
                       television_pad_top=6, radio_pad_top=8, source_cells_unchanged=True,
                       assets=[dict(asset=row['target'], png_sha256=sha(Path(row['source']))) for row in asset_manifest])
    provenance_path = out / ASSET_DIR / 'domestic-provenance.json'
    write(provenance_path, asset_proof)
    asset_manifest.append(dict(source=str(provenance_path), target=ASSET_DIR + '/domestic-provenance.json'))
    integration = dict(mapping_stem=STEM, candidate=str(out / (STEM + '.lua')),
                       assets=asset_manifest, tools=[dict(source=str(Path(__file__).resolve()), target='tools/author_newbark_domestic.py')],
                       supersessions=str(out / 'supersessions.json'), placements=str(out / 'placements.json'))
    write(out / 'integration.json', integration)
    report = dict(status='passed' if args.validate else 'candidate', rows=54, new_rows=len(new_rows),
                  supersessions=len(supersessions), cells=54, maps=12, assets=len(asset_files),
                  baseline_runtime=BASE_RUNTIME, binding=REVIEWED_BINDING, neutral=neutral_result,
                  original_stool_removal_preserved=True, only_approved_cells_changed=True, previews=previews)
    write(out / 'report.json', report)
    assert runtime_fingerprint(root) == frozen['runtime_inputs']
    print(json.dumps({key: value for key, value in report.items() if key != 'previews'}))


if __name__ == '__main__':
    main()
