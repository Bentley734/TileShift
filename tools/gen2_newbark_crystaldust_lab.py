"""Prepare the selected native CrystalDust CD-09 Elm research PC privately.

Reads --mod-root only. Outputs four positioned Crystal rows and a small files/
tree for root integration. Gold/Silver lack this source feature and stay alone.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import os
import shutil
import sys
from types import SimpleNamespace

WORKSPACE = next(parent for parent in Path(__file__).resolve().parents
                 if (parent / '.tools/python').is_dir()
                 and (parent / '.work/tileshift-firegold').is_dir())
FROZEN = WORKSPACE / '.work/tileshift-v0442-checkpoint/frozen.json'
FROZEN_DATA = json.loads(FROZEN.read_text())
PARSER = argparse.ArgumentParser(description=__doc__)
PARSER.add_argument('--mod-root', type=Path, default=Path(FROZEN_DATA['stage']))
PARSER.add_argument('--output', type=Path, default=WORKSPACE / '.work/tileshift-newbark-crystaldust/lab')
ARGS = PARSER.parse_args()
MOD = ARGS.mod_root.resolve()
OUT = ARGS.output.resolve()
assert not OUT.is_relative_to(MOD), 'Authoring output must stay outside the input mod'
sys.path.insert(0, str(MOD / 'tools'))
sys.path.insert(0, str(WORKSPACE / '.tools/python'))
from PIL import Image, ImageDraw, ImageFont
import catalog
import preview
import gen2_extended_review as review
from newbark_building_review import lua

CACHE = Path(os.environ['APPDATA']) / 'pokemon-love2d'
HACK = WORKSPACE / '.work/tileshift-firegold/crystaldust'
OPTIONS = WORKSPACE / '.work/tileshift-newbark-furniture-options/crystaldust'
PREFIX = Path('assets/third_party/johto-hacks/newbark-cd-lab')
MODULE = Path('mappings/gen2_newbark_crystaldust_lab.lua')
WHOLE_SHA = '426b104748a418859197009a65cce7589a3bc6cf1ed7cb3d51ecf3452a03b17d'
SOURCE_HASHES = [
    '01a93fe47c647216ac1aa1f278855c1f38f3a7b64869788210973ae475a2635c',
    '2d0352a907dadf6893c7dc63ecdf5c3419813f6f41cdff240559e9dcccc5c5e1',
    '262d20e81dc39afaa33752f3289bb63e8c9171e9960d8af9a3a81011aa78c076',
    'a177cfba698bbf054581628670cb2acac14c3177cea84d865d3b7e977c5f1512',
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pixels(image):
    return hashlib.sha256(image.convert('RGBA').tobytes()).hexdigest()


def semantic(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def native_option(record):
    whole = Image.new('RGBA', tuple(record['native_canvas']))
    for part in record['native_parts']:
        path = Path(part['source_atlas'])
        assert path.is_relative_to(HACK) and sha(path) == part['source_atlas_sha256']
        x, y, w, h = part['source_atlas_rect_xywh']
        piece = Image.open(path).convert('RGBA').crop((x, y, x + w, y + h))
        assert pixels(piece) == part['source_rgba_sha256']
        whole.alpha_composite(piece, tuple(part['destination_xy']))
    if record.get('padding_trim_only'):
        whole = whole.crop(tuple(record['transparent_padding_bbox']))
    assert list(whole.size) == record['native_size']
    assert pixels(whole) == record['output_rgba_sha256']
    assert whole.tobytes() == Image.open(OPTIONS / record['output']).convert('RGBA').tobytes()
    return whole


def healing_source(hack, map_id, cells):
    root = WORKSPACE / '.work/tileshift-firegold' / hack
    metadata = json.loads((root / 'catalog.json').read_text())
    definition = next(m for m in metadata['maps'] if m['id'] == map_id)
    layer = 'mid' if hack == 'crystaldust' else 'top'
    atlas_path = root / 'pairs' / definition['pair'] / (layer + '.png')
    atlas = Image.open(atlas_path).convert('RGBA')
    whole = Image.new('RGBA', (32, 48))
    x, y = cells
    ids = []
    for dy in range(3):
        line = []
        for dx in range(2):
            mid = definition['grid'][(y + dy) * definition['width'] + x + dx] & 1023
            line.append(mid)
            sx, sy = mid % 16 * 16, mid // 16 * 16
            whole.alpha_composite(atlas.crop((sx, sy, sx + 16, sy + 16)), (dx * 16, dy * 16))
        ids.append(line)
    assert whole.getbbox() == (0, 9, 32, 48)
    assert sum(p[3] > 0 for p in whole.get_flattened_data()) == 1064
    source_path = root / 'maps' / (map_id + '-flat.png')
    context = Image.open(source_path).convert('RGBA').crop((x * 16, y * 16, (x + 2) * 16, (y + 3) * 16))
    assert all(not a[3] or a == b for a, b in zip(whole.get_flattened_data(), context.get_flattened_data()))
    return whole, dict(hack=hack, rom_sha256=metadata['rom_sha256'], map=map_id,
        pair=definition['pair'], map_cells_xywh=[x, y, 2, 3], metatiles=ids,
        native_layer=layer, atlas_sha256=sha(atlas_path), map_png_sha256=sha(source_path),
        complete_canvas_size=[32, 48], opaque_bbox=[0, 9, 32, 48], opaque_pixels=1064,
        canvas_rgba_sha256=pixels(whole), trimmed_native_size=[32, 39],
        trimmed_rgba_sha256=pixels(whole.crop((0, 9, 32, 48))))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = OUT / 'files'
    assets = files / PREFIX
    assets.mkdir(parents=True, exist_ok=True)
    provenance = json.loads((OPTIONS / 'provenance.json').read_text())
    chosen = next(row for row in provenance['candidates'] if row['id'] == 'CD-09')
    assert chosen['native_size'] == [32, 26] and chosen['output_rgba_sha256'] == WHOLE_SHA
    hack_meta = json.loads((HACK / 'catalog.json').read_text())
    assert hack_meta['rom_sha256'] == '51196cba923c315d0088b747b5cdee704f2ac057cd493f9ddf226fb7227302cf'
    whole = Image.new('RGBA', (32, 26))
    for part in chosen['native_parts']:
        path = Path(part['source_atlas'])
        assert path.is_relative_to(HACK) and sha(path) == part['source_atlas_sha256']
        atlas = Image.open(path).convert('RGBA')
        x, y, w, h = part['source_atlas_rect_xywh']
        piece = atlas.crop((x, y, x + w, y + h))
        assert pixels(piece) == part['source_rgba_sha256']
        whole.alpha_composite(piece, tuple(part['destination_xy']))
    assert pixels(whole) == WHOLE_SHA
    assert whole.tobytes() == Image.open(OPTIONS / 'CD-09.png').convert('RGBA').tobytes()
    # Exact source-map coordinate independently proves the five selected native
    # layer pieces make one intact feature rather than a rearranged furniture kit.
    context = chosen['source']
    source_map = Path(context['map_png'])
    assert sha(source_map) == context['map_png_sha256']
    sx, sy, sw, sh = context['map_rect_xywh']
    source_crop = Image.open(source_map).convert('RGBA').crop((sx, sy, sx + sw, sy + sh))
    for actual, original in zip(whole.get_flattened_data(), source_crop.get_flattened_data()):
        if actual[3]:
            assert actual == original
    whole.save(assets / 'rear-pc-whole32x26.png')
    padded = Image.new('RGBA', (32, 32))
    padded.alpha_composite(whole, (0, 6))
    assert sum(p[3] > 0 for p in padded.get_flattened_data()) == sum(p[3] > 0 for p in whole.get_flattened_data())
    padded.save(OUT / 'whole-bottom-anchored32x32.png')
    cell_assets = {}
    for q in range(4):
        cell = padded.crop((q % 2 * 16, q // 2 * 16, q % 2 * 16 + 16, q // 2 * 16 + 16))
        name = 'rear-pc-cell-' + str(q % 2) + '-' + str(q // 2) + '.png'
        cell.save(assets / name)
        cell_assets[q] = (PREFIX / name).as_posix()
    active = []
    active_all = []
    origins = []
    for path in sorted((MOD / 'mappings').glob('*.lua')):
        raw = path.read_bytes()
        if b'TILESET_LAB' not in raw:
            continue
        for row in preview.read_reviewed(path):
            if row['game'] in review.GAMES and row['style'] == 'gen3' and row['tileset'] == 'TILESET_LAB' and row.get('map', 'ELMS_LAB') == 'ELMS_LAB':
                active_all.append(row)
                if row['game'] == 'crystal':
                    active.append(row)
                if row['game'] == 'crystal' and row.get('map') == 'ELMS_LAB' and row['id'] == 33:
                    origins.append(dict(module=path.relative_to(MOD).as_posix(), row=row, semantic_sha256=semantic(row)))
    assert len(origins) == 4 and {o['row']['quadrant'] for o in origins} == set(range(4))
    assert all(o['row'].get('x') is None and o['row'].get('y') is None for o in origins)
    data = review.source(CACHE, 'crystal')
    definition = data['maps']['ELMS_LAB']
    event, = [ev for ev in definition['bgEvents'] if (ev['x'], ev['y']) == (3, 5)]
    assert event['kind'] == 2 and event['scriptKey'] == '1e:4f5e'
    assert definition['blocks'].count(33) == 1
    rows = []
    floor = dict(game='emerald', tileset='building__lab', id=514,
                 hash='157f28c35a6a7823723ce8d37541a6c2dcf82d61a16c55bc818ba6795090367e')
    base_image = preview.native_donor(CACHE, floor, {})
    expected_patch = Image.new('RGBA', (32, 32))
    for q in range(4):
        x, y = 2 + q % 2, 4 + q // 2
        cell = review.cell_info(CACHE, 'crystal', data, definition['tileset'], 33, q)
        assert cell['sourceHash'] == SOURCE_HASHES[q]
        assert cell['collision'] == (0 if q < 2 else 7)
        prior, = [o['row'] for o in origins if o['row']['quadrant'] == q]
        assert prior['sourceHash'] == cell['sourceHash'] and prior['base'] == floor
        row = dict(game='crystal', style='gen3', map='ELMS_LAB', tileset='TILESET_LAB',
                   id=33, quadrant=q, x=x, y=y, sourceCells=[[x, y]],
                   sourceHash=cell['sourceHash'], sourceFiles=data['fingerprints']['TILESET_LAB'],
                   sourceCollision=cell['collision'],
                   sourcePriority=[bool(a.get('priority')) for a in cell['attributes']],
                   sourcePalettes=[a.get('palette', 1) for a in cell['attributes']],
                   kind='third_party', asset=cell_assets[q], assetFileHash=sha(files / cell_assets[q]),
                   base=copy.deepcopy(floor), status='reviewed', role='newbark_cd09_rear_research_pc',
                   credit='CrystalDust / Sierraffinity and contributors; complete native rear-facing research PC and desk.',
                   sourceUrl='https://github.com/Sierraffinity/CrystalDust',
                   evidence='User-selected CrystalDust CD-09 complete32x26 rear-facing monitor, CPU and desk at1:1. Bottom-anchored inside original Crystal32x32 central workstation at cells2..3,4..5 with six transparent upper pixels; no scaling or clipping. Exterior transparency shows the existing Emerald lab floor. The original north-side interaction at3,5, player stand3,4 facingdown, source collision and NPC definitions stay unchanged.')
        composite = Image.alpha_composite(base_image, Image.open(files / row['asset']).convert('RGBA'))
        row['compositionPixelHash'] = pixels(composite)
        expected_patch.paste(composite, (q % 2 * 16, q // 2 * 16))
        rows.append(row)
    expected_patch.save(OUT / 'expected-lab-patch32x32.png')
    north_choice = next(row for row in provenance['candidates'] if row['id'] == 'CD-10')
    north_pc = native_option(north_choice)
    assert north_pc.size == (32, 26)
    north_pc.save(assets / 'wall-pc-whole32x26.png')
    north_canvas = Image.new('RGBA', (32, 48))
    north_canvas.alpha_composite(north_pc, (0, 6))
    machines = []
    for hack, map_id, cells in [('crystaldust', 'g01_m004', (0, 0)),
                                ('firegold', 'g44_m005', (1, 3)),
                                ('liquidcrystal', 'g04_m003', (8, 11))]:
        source_machine, source_proof = healing_source(hack, map_id, cells)
        machines.append((source_machine, source_proof))
    healer = machines[0][0]
    assert pixels(healer) == '513cdf4728ef882e418ec3ce8a7bff6f99e1a28c4c5eb51d6b29f6ad66c719b8'
    assert all(image.tobytes() == healer.tobytes() for image, _ in machines)
    healer.crop((0, 9, 32, 48)).save(assets / 'lab-healer-whole32x39.png')
    hardware_assets = {}
    for name, canvas, height in [('wall-pc', north_canvas, 2), ('lab-healer', healer, 3)]:
        for dy in range(height):
            for dx in range(2):
                cell_path = PREFIX / (name + '-cell-' + str(dx) + '-' + str(dy) + '.png')
                canvas.crop((dx * 16, dy * 16, dx * 16 + 16, dy * 16 + 16)).save(files / cell_path)
                hardware_assets[name, dx, dy] = cell_path.as_posix()
    hardware_witnesses = []
    expected_north = {}
    hardware_scope = []
    wall = dict(game='firered', tileset='oak_lab', id=669,
                hash='400f6f1c5ef121fbba65e164544b8dd6bd23d7a2084db3d8106d08457fedbdcc')
    for game in review.GAMES:
        source = review.source(CACHE, game)
        source_map_def = source['maps']['ELMS_LAB']
        control, = [ev for ev in source_map_def['bgEvents'] if (ev['x'], ev['y']) == (2, 1)]
        assert control['kind'] == 0
        hardware_scope.append(dict(game=game, source_event=control, standing_cell=[2, 2],
            event_semantics='Original healing-machine control workstation script, not a separate personal-PC interaction.',
            original_objects=copy.deepcopy(source_map_def['objects'])))
        expected_north[game] = Image.new('RGBA', (64, 48))
        for y in range(3):
            for x in range(4):
                bid = source_map_def['blocks'][y // 2 * source_map_def['width'] + x // 2]
                q = y % 2 * 2 + x % 2
                applicable = [r for r in active_all if r['game'] == game and r['id'] == bid and r['quadrant'] == q
                              and (r.get('x') is None or (r['x'], r['y']) == (x, y))]
                assert applicable
                applicable.sort(key=lambda r: (bool(r.get('map')), r.get('x') is not None))
                previous = applicable[-1]
                assert previous.get('x') is None, 'Existing positioned source key needs an explicit supersession'
                backing = previous.get('base') or previous.get('donor')
                assert backing == (wall if y == 0 else floor), (game, x, y, backing)
                cell = review.cell_info(CACHE, game, source, 'TILESET_LAB', bid, q)
                assert cell['sourceHash'] == previous['sourceHash']
                row = dict(game=game, style='gen3', map='ELMS_LAB', tileset='TILESET_LAB', id=bid,
                    quadrant=q, x=x, y=y, sourceCells=[[x, y]], sourceHash=cell['sourceHash'],
                    sourceFiles=source['fingerprints']['TILESET_LAB'], sourceCollision=cell['collision'],
                    sourcePriority=[bool(a.get('priority')) for a in cell['attributes']],
                    sourcePalettes=[a.get('palette', 1) for a in cell['attributes']], status='reviewed')
                if x >= 2 and y == 2:
                    row.update(kind='native', donor=copy.deepcopy(backing), role='newbark_north_workstation_vacated_floor',
                        evidence='User requested moving the north-wall control workstation artwork upward16px. Restore the two old decorative desk-foot cells to their existing native Emerald laboratory floor. All original source collision, interaction and NPC coordinates remain unchanged.')
                    composite = preview.native_donor(CACHE, backing, {})
                else:
                    name = 'lab-healer' if x < 2 else 'wall-pc'
                    asset = hardware_assets[name, x % 2, y]
                    row.update(kind='third_party', asset=asset, assetFileHash=sha(files / asset), base=copy.deepcopy(backing),
                        role='newbark_cd_lab_healer' if x < 2 else 'newbark_cd_north_control_workstation',
                        credit='CrystalDust / Sierraffinity and contributors; complete native laboratory equipment.',
                        sourceUrl='https://github.com/Sierraffinity/CrystalDust',
                        evidence=('Complete native CrystalDust32x39 laboratory healing capsule, including every Pokeball cap, side support and lower foot pixel, at1:1. Its unchanged bottom is48px and top9px; only transparent outer padding is omitted. '
                                  if x < 2 else
                                  'Complete native CrystalDust CD-10 front-facing monitor, CPU and desk32x26 at1:1, moved exactly16px upward to origin32,6 and bottom32. The original source healing-machine control event remains at2,1. ')
                                  + 'Native transparency reveals the destination-selected wall in row0 and existing lab floor below. No floor-colored wall rectangle, unique-pixel clipping, scaling, collision change, event or NPC movement.')
                    composite = Image.alpha_composite(preview.native_donor(CACHE, backing, {}), Image.open(files / asset).convert('RGBA'))
                row['compositionPixelHash'] = pixels(composite)
                rows.append(row)
                expected_north[game].paste(composite, (x * 16, y * 16))
                hardware_witnesses.append(dict(game=game, x=x, y=y, source_cell=cell,
                    previous_row=previous, previous_semantic_sha256=semantic(previous), destination_backing=backing))
        expected_north[game].save(OUT / (game + '-expected-north64x48.png'))
    assert len(rows) == 40
    # Rebuild the previous four isolated FireRed layer cells independently.
    # The complete native CD10 silhouette has exactly the same687 opaque pixels;
    # only its world origin moves from(32,22) to(32,6), precisely one source row.
    old_pc = Image.new('RGBA', (32, 32))
    for witness in hardware_witnesses:
        if witness['game'] != 'crystal' or witness['x'] not in (2, 3) or witness['y'] not in (1, 2):
            continue
        foreground = Image.new('RGBA', (16, 16))
        for part in witness['previous_row']['parts']:
            donor = preview.native_donor(CACHE, part['donor'], {}, part.get('layers'), part.get('layerHashes'))
            sx, sy = part.get('srcX', 0), part.get('srcY', 0)
            foreground.alpha_composite(donor.crop((sx, sy, sx + part['w'], sy + part['h'])),
                                       (part.get('x', 0), part.get('y', 0)))
        old_pc.alpha_composite(foreground, ((witness['x'] - 2) * 16, (witness['y'] - 1) * 16))
    assert old_pc.getbbox() == (0, 6, 32, 32)
    assert old_pc.getchannel('A').tobytes() == north_canvas.crop((0, 0, 32, 32)).getchannel('A').tobytes()
    assert sum(p[3] > 0 for p in old_pc.get_flattened_data()) == 687
    old_pc.save(OUT / 'previous-north-pc-isolated32x32.png')
    (OUT / 'prior-north-generic-witnesses.json').write_text(json.dumps(hardware_witnesses, indent=2, sort_keys=True) + '\n')
    comparison = Image.new('RGB', (1050, 350), '#18232e')
    draw = ImageDraw.Draw(comparison)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 17)
    draw.text((18, 15), 'Complete native lab healing machines (4x zoom; all three are pixel-identical)', font=font, fill='white')
    for index, (image, item) in enumerate(machines):
        x = 18 + index * 350
        draw.text((x, 60), item['hack'] + ' 32x39 native pixels', font=font, fill='white')
        crop = image.crop((0, 9, 32, 48)).resize((128, 156), Image.Resampling.NEAREST)
        comparison.paste(crop, (x, 105), crop)
    comparison.save(OUT / 'healing-machine-source-comparison.png')
    module = files / MODULE
    module.parent.mkdir(parents=True, exist_ok=True)
    canonical_rows = json.loads(json.dumps(rows, sort_keys=True))
    module.write_text('-- Selected native CrystalDust lab hardware, source-positioned; original layouts and interactions retained.\nreturn ' + lua(canonical_rows) + '\n')
    assert preview.read_reviewed(module) == rows
    (OUT / 'candidates.json').write_text(json.dumps(rows, indent=2, sort_keys=True) + '\n')
    (OUT / 'supersessions.json').write_text('[]\n')
    (OUT / 'prior-generic-witnesses.json').write_text(json.dumps(origins, indent=2, sort_keys=True) + '\n')
    # Reuse frozen neutral library bytes, plus only assets referenced by this
    # map, so no input checkout or frozen release is changed during validation.
    neutral = OUT / 'neutral-mod'
    shutil.copytree(MOD / 'lib', neutral / 'lib', dirs_exist_ok=True)
    def asset_paths(value):
        if isinstance(value, dict):
            for item in value.values():
                yield from asset_paths(item)
        elif isinstance(value, list):
            for item in value:
                yield from asset_paths(item)
        elif isinstance(value, str) and value.startswith('assets/'):
            yield value
    for relative in sorted(set(asset_paths(active_all))):
        source = MOD / relative
        if source.is_file():
            target = neutral / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    for path in files.rglob('*'):
        if path.is_file():
            target = neutral / path.relative_to(files)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    proof = review.validate_batch(rows, SimpleNamespace(cache=CACHE,
        engine=WORKSPACE / '.work/tileshift-engine-0400', output=OUT), neutral)
    assert proof['rows_accepted'] == 40 and proof['rejected'] == 0
    coexist = review.validate_batch([o['row'] for o in origins] + rows, SimpleNamespace(cache=CACHE,
        engine=WORKSPACE / '.work/tileshift-engine-0400', output=OUT), neutral)
    assert coexist['rows_accepted'] == 44 and coexist['rejected'] == 0
    before_preview = preview.map_preview(CACHE, OUT, 'crystal', 'ELMS_LAB', 'previous', active, {}, 2, neutral)
    after_preview = preview.map_preview(CACHE, OUT, 'crystal', 'ELMS_LAB', 'candidate', active + rows, {}, 2, neutral)
    before = Image.open(OUT / 'previous-after-native.png').convert('RGBA')
    after = Image.open(OUT / 'candidate-after-native.png').convert('RGBA')
    assert after.crop((32, 64, 64, 96)).tobytes() == expected_patch.tobytes()
    for y in range(after.height):
        for x in range(after.width):
            if not ((32 <= x < 64 and 64 <= y < 96) or (x < 64 and y < 48)):
                assert before.getpixel((x, y)) == after.getpixel((x, y))
    preview_proofs = []
    for game in review.GAMES:
        applicable = [r for r in active_all if r['game'] == game]
        before_info = preview.map_preview(CACHE, OUT, game, 'ELMS_LAB', game + '-previous', applicable, {}, 2, neutral)
        after_info = preview.map_preview(CACHE, OUT, game, 'ELMS_LAB', game + '-candidate', applicable + rows, {}, 2, neutral)
        old_scene = Image.open(OUT / (game + '-previous-after-native.png')).convert('RGBA')
        new_scene = Image.open(OUT / (game + '-candidate-after-native.png')).convert('RGBA')
        assert new_scene.crop((0, 0, 64, 48)).tobytes() == expected_north[game].tobytes()
        for y in range(new_scene.height):
            for x in range(new_scene.width):
                if not ((x < 64 and y < 48) or (game == 'crystal' and 32 <= x < 64 and 64 <= y < 96)):
                    assert old_scene.getpixel((x, y)) == new_scene.getpixel((x, y))
        preview_proofs.append(dict(game=game, previous=before_info, candidate=after_info,
            expected_north_rgba_sha256=pixels(expected_north[game]),
            only_reviewed_hardware_bounds_changed=True))
    distinctions = []
    for game in ('gold', 'silver', 'crystal'):
        original = catalog.read_lua(CACHE / game / 'data/generated/maps.lua')['ELMS_LAB']
        distinctions.append(dict(game=game, map='ELMS_LAB', source_maps_sha256=sha(CACHE / game / 'data/generated/maps.lua'),
            original_block_at_1_2=original['blocks'][2 * original['width'] + 1],
            central_events=[ev for ev in original['bgEvents'] if 2 <= ev['x'] <= 3 and 4 <= ev['y'] <= 5],
            original_objects=copy.deepcopy(original['objects']), replacement_enabled=game == 'crystal'))
    assert distinctions[0]['original_block_at_1_2'] == distinctions[1]['original_block_at_1_2'] == 1
    assert not distinctions[0]['central_events'] and not distinctions[1]['central_events']
    source_proof = dict(origin='User-selected native CrystalDust CD-09; exact source layer pixels only.',
        source_rom_name=hack_meta['rom_name'], source_rom_sha256=hack_meta['rom_sha256'],
        source_option=chosen, native_whole_rgba_sha256=WHOLE_SHA, native_whole_size=[32, 26],
        target_map='ELMS_LAB', target_game='crystal', target_cells_xywh=[2, 4, 2, 2],
        target_pixel_origin=[32, 70], padding_top=6, target_bottom_pixel=96,
        actual_source_event=event, standing_cell=[3, 4], required_facing='down',
        scaling=False, unique_pixel_clipping=False, redrawing=False,
        exterior_transparency='Exact native top-layer alpha; six transparent upper padding rows added.',
        selected_floor=floor, assets={path.name:sha(path) for path in assets.glob('*.png')},
        scope_distinction=distinctions,
        north_workstation=dict(selected_option=north_choice, native_size=[32, 26],
            target_pixel_origin=[32, 6], target_bottom_pixel=32, upward_movement_pixels=16,
            old_native_bounds=[32, 22, 32, 26], vacated_floor_cells=[[2,2],[3,2]],
            native_silhouette_matches_previous_exactly=True, opaque_pixels_retained=687,
            original_control_events=hardware_scope),
        healing_machine=dict(selected_source=machines[0][1], alternatives=[item for _, item in machines],
            all_three_source_artworks_pixel_identical=True, native_size=[32, 39],
            target_pixel_origin=[0, 9], target_bottom_pixel=48, no_native_pixel_clipping=True,
            comparison_file='healing-machine-source-comparison.png',
            comparison_sha256=sha(OUT / 'healing-machine-source-comparison.png')),
        destination_backings=dict(north_row0=wall, rows1_and2=floor,
            rule='Only isolated native hardware moves; source-selected wall/floor backing remains in its destination row.'),
        source_definitions_modified=False, mod_input_modified=False)
    source_proof['files'] = {path.name:sha(path) for path in sorted(assets.glob('*.png'))}
    (assets / 'provenance.json').write_text(json.dumps(source_proof, indent=2, sort_keys=True) + '\n')
    result = dict(status='passed', module=MODULE.as_posix(), module_sha256=sha(module),
        positioned_rows=40, exact_key_supersessions=0, generic_rows_retained=40,
        neutral=proof, neutral_with_prior_generic_rows=coexist,
        previous_coverage=before_preview, candidate_coverage=after_preview,
        complete_native_object_rgba_sha256=WHOLE_SHA,
        exact_expected_patch_rgba_sha256=pixels(expected_patch),
        only_reviewed_hardware_bounds_changed=True, npc_positions_and_interaction_unchanged=True,
        whole_scene_previews=preview_proofs,
        all_three_source_distinctions_checked=True, gold_silver_source_absence_preserved=True,
        supplied_assets=[str(path.relative_to(files)) for path in sorted(assets.iterdir()) if path.is_file()],
        input_mod=str(MOD), input_module_sha256=sha(MOD / 'mappings/johto_labrooms_finish.lua'),
        files={path.relative_to(files).as_posix():sha(path) for path in files.rglob('*') if path.is_file()},
        limits='Neutral session and exact CPU whole-map pixel preview; root owns native actor/player GPU and publication.')
    (OUT / 'proof.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    integration = dict(mapping_stem=MODULE.stem, candidate=str(module),
        assets=[dict(source=str(path), target=path.relative_to(files).as_posix(), sha256=sha(path))
                for path in sorted(assets.iterdir()) if path.is_file()],
        tools=[dict(source=str(Path(__file__).resolve()), target='tools/gen2_newbark_crystaldust_lab.py',
                    sha256=sha(Path(__file__)))],
        supersessions=[], proof=str(OUT / 'proof.json'), module_sha256=sha(module),
        rows=40, games=list(review.GAMES), map='ELMS_LAB',
        central_crystal_cells=[[2,4],[3,4],[2,5],[3,5]],
        shared_north_cells=[[x,y] for y in range(3) for x in range(4)],
        gold_silver_source_absence_preserved=True)
    (OUT / 'integration.json').write_text(json.dumps(integration, indent=2, sort_keys=True) + '\n')
    print(json.dumps({key:result[key] for key in ('status','module','module_sha256','positioned_rows','exact_key_supersessions','gold_silver_source_absence_preserved')}))


if __name__ == '__main__':
    main()
