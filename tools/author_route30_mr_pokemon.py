"""Author the Route30 Mr. Pokemon room using complete CrystalDust furniture.

Run against an unmodified v0.46.0 baseline and an isolated candidate checkout:
  python tools/author_route30_mr_pokemon.py --baseline BASE --mod-root MOD --output OUT
Imported cartridges remain read-only. The output maps are visual-only, bounded
to this room's original cells, with exact source and native-art fingerprints.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from types import SimpleNamespace

WORKSPACE = next(p for p in Path(__file__).resolve().parents
                 if (p / '.tools/python').is_dir() and (p / '.work').is_dir())
sys.path.insert(0, str(WORKSPACE / '.tools/python'))
from PIL import Image, ImageDraw, ImageFont

MAP = 'MR_POKEMONS_HOUSE'
MODULE = 'mappings/route30_mr_pokemon.lua'
PREFIX = 'assets/third_party/johto-hacks/route30-mr-pokemon'
PC_PREFIX = 'assets/third_party/johto-hacks/newbark-cd-lab'
CONTEXT = 'assets/third_party/johto-hacks/route30-mr-pokemon-context'
FACILITY = 'mappings/johto_facility_finish.lua'
BOOKCASES = 'mappings/gen2_crystaldust_bookcases.lua'
GAMES = ('gold', 'silver', 'crystal')
FOOTER = '''-- BEGIN ROUTE30 MR POKEMON MIGRATION
-- This room now uses complete source-guarded CrystalDust artwork in
-- route30_mr_pokemon.lua. The authoring builder also excludes this room.
-- Filter only its superseded records; retain every other facility unchanged.
local retained={}
for _,row in ipairs(rows)do
  if row.map~='MR_POKEMONS_HOUSE' then retained[#retained+1]=row end
end
rows=retained
-- END ROUTE30 MR POKEMON MIGRATION
return rows
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pixels(image):
    return hashlib.sha256(image.convert('RGBA').tobytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def key(row):
    return tuple(row.get(k) for k in ('game', 'style', 'tileset', 'id', 'quadrant', 'map', 'x', 'y'))


def canonical(value):
    if isinstance(value, dict):
        return {k: canonical(value[k]) for k in sorted(value)}
    if isinstance(value, list):
        return [canonical(v) for v in value]
    return value


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline', required=True, type=Path)
    p.add_argument('--mod-root', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--engine', type=Path, default=WORKSPACE / '.work/tileshift-engine-0420')
    args = p.parse_args()
    baseline, mod, out = args.baseline.resolve(), args.mod_root.resolve(), args.output.resolve()
    assert baseline != mod and out != baseline and out != mod
    assert json.loads((baseline / 'manifest.json').read_text())['version'] == '0.46.0'
    sys.path.insert(0, str(mod / 'tools'))
    import catalog
    import preview
    import gen2_extended_review as review
    import interior_review
    interior_review.WORKSPACE = WORKSPACE
    from interior_review import Imports
    from center_mart_overhang_review import write_rows
    cache = Path(os.environ['APPDATA']) / 'pokemon-love2d'
    imp = Imports(cache, WORKSPACE / '.work/tileshift-catalog')
    out.mkdir(parents=True, exist_ok=True)
    native = json.loads((mod / PREFIX / 'provenance.json').read_text())
    assert native['rom_sha256'] == '51196cba923c315d0088b747b5cdee704f2ac057cd493f9ddf226fb7227302cf'
    for name, expected in native['files'].items():
        assert sha(mod / PREFIX / name) == expected, name
    floor = dict(game='firered', tileset='oak_lab', id=129,
                 hash=imp.cell_index('firered')['oak_lab', 129]['pixel_sha256'])
    assert floor['hash'] == 'ec35a71354fcd15e2816b2c8c8dc295dbda227da4f978001311bfe0e5b643b12'
    floor_image = preview.native_donor(cache, floor, imp.packed)
    assert floor_image.tobytes() == Image.open(mod / PREFIX / 'floor-plain.png').convert('RGBA').tobytes()
    wall = Image.open(mod / PREFIX / 'wall-upper.png').convert('RGBA')
    context = mod / CONTEXT
    context.mkdir(parents=True, exist_ok=True)
    context_proof = dict(format=1, origin='CrystalDust / Sierraffinity and contributors',
                         sourceUrl=native['sourceUrl'],
                         recipe='Exact native complete bookcase/computer foreground over exact native wall module; no scaling or color keying.',
                         compositions=[], files={})

    active = []
    names = list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]", (baseline / 'main.lua').read_text())))
    for name in names:
        raw = (baseline / name).read_bytes()
        if b'TILESET_FACILITY' not in raw:
            continue
        active.extend((name, r) for r in preview.read_reviewed(baseline / name)
                      if r['game'] in GAMES and r['style'] == 'gen3'
                      and r['tileset'] == 'TILESET_FACILITY' and r.get('map', MAP) == MAP)

    def selected(game, md, x, y):
        bid = md['blocks'][y // 2 * md['width'] + x // 2]
        q = y % 2 * 2 + x % 2
        choices = [(name, r) for name, r in active if r['game'] == game
                   and r['id'] == bid and r['quadrant'] == q
                   and (r.get('x') is None or (r['x'] // 2, r['y'] // 2) == (x // 2, y // 2))]
        choices.sort(key=lambda item: (item[1].get('map') is not None, item[1].get('x') is not None))
        assert choices, (game, x, y)
        return choices[-1]

    def asset(row, name, role, base=None, context_asset=False, asset_prefix=PREFIX):
        for field in ('donor', 'base', 'parts', 'asset', 'assetFileHash', 'assetPixelHash', 'artOverlay',
                      'compositionPixelHash', 'credit', 'sourceUrl', 'animated', 'animation', 'frames', 'assetFrames'):
            row.pop(field, None)
        path = (CONTEXT if context_asset else asset_prefix) + '/' + name
        row.update(kind='third_party', asset=path, assetFileHash=sha(mod / path),
                   assetPixelHash=pixels(Image.open(mod / path)), role=role,
                   credit='CrystalDust / Sierraffinity and contributors; intact native furniture and room wall at1:1.',
                   sourceUrl=native['sourceUrl'])
        if base:
            row['base'] = copy.deepcopy(base)

    rows, changes, sources, geometry_checks = [], [], [], []
    source_raw_before = {}
    for game in GAMES:
        data = review.source(cache, game)
        md = data['maps'][MAP]
        assert md['tileset'] == 'TILESET_FACILITY' and (md['width'] * 2, md['height'] * 2) == (8, 8)
        source_raw_before[game] = sha(cache / game / 'data/generated/maps.lua')
        sources.append(dict(game=game, map=MAP, definition_sha256=digest(md),
                            warps=md.get('warps', []), objects=md.get('objects', []),
                            bg_events=md.get('bgEvents', []), callbacks=md.get('callbacks', [])))
        for y in range(8):
            for x in range(8):
                module, old = selected(game, md, x, y)
                row = copy.deepcopy(old)
                bid = md['blocks'][y // 2 * md['width'] + x // 2]
                q = y % 2 * 2 + x % 2
                cell = review.cell_info(cache, game, data, md['tileset'], bid, q)
                assert old['sourceHash'] == cell['sourceHash'] and old['sourceCollision'] == cell['collision']
                assert old['sourcePriority'] == [bool(a.get('priority')) for a in cell['attributes']]
                assert old['sourcePalettes'] == [a.get('palette', 1) for a in cell['attributes']]
                row.update(map=MAP, x=x, y=y, sourceCells=[[x, y]],
                           sourceFiles=copy.deepcopy(data['fingerprints'][md['tileset']]))
                row['evidence'] = ('Route30 Mr. Pokemon house only. Complete native CrystalDust front-facing monitor, tower and desk32x26 is padded6px within original blocked32x32 cells6..7,0..1, matching the original big-broken-computer interaction. Unrelated electric-barrier art is removed from original walkable cells6..7,2..3, which use matching plain floor. Complete sofa32x32 occupies existing blocked wall+sofa cells2..3,0..1. Exact matching native checker floor continues beneath retained whole furniture layers. All native artwork remains1:1. Source map, collision, NPC positions, story flags, warps, big computer/bookcases and strange-coins interactions are unchanged.')
                if x in (6, 7) and y in (0, 1):
                    if y == 0:
                        foreground_path = PC_PREFIX + '/wall-pc-cell-' + str(x - 6) + '-0.png'
                        foreground = Image.open(mod / foreground_path).convert('RGBA')
                        whole = Image.alpha_composite(wall, foreground)
                        name = 'computer-wall-' + str(x - 6) + '.png'
                        whole.save(context / name)
                        context_proof['files'][name] = sha(context / name)
                        record = dict(output=name, output_rgba_sha256=pixels(whole),
                                      native_wall=dict(asset=PREFIX + '/wall-upper.png', sha256=sha(mod / PREFIX / 'wall-upper.png')),
                                      native_foreground=dict(asset=foreground_path, sha256=sha(mod / foreground_path), rgba_sha256=pixels(foreground)),
                                      canvas=[16, 16], offset=[0, 0])
                        if record not in context_proof['compositions']:
                            context_proof['compositions'].append(record)
                        asset(row, name, 'route30_cd_complete_native_big_computer', context_asset=True)
                    else:
                        asset(row, 'wall-pc-cell-' + str(x - 6) + '-1.png',
                              'route30_cd_complete_native_big_computer', floor, asset_prefix=PC_PREFIX)
                elif x in (6, 7) and y in (2, 3):
                    assert row['sourceCollision'] == 0
                    for field in ('parts', 'base', 'asset', 'assetFileHash', 'assetPixelHash', 'credit', 'sourceUrl'):
                        row.pop(field, None)
                    row.update(kind='native', donor=copy.deepcopy(floor), role='route30_cd_matching_native_floor')
                elif y == 0 and x not in (2, 3):
                    if x in (0, 1):
                        # Existing bookcases already use complete native foreground
                        # alpha. Preserve all of it over the matching wall header.
                        foreground = Image.open(baseline / old['asset']).convert('RGBA')
                        whole = Image.alpha_composite(wall, foreground)
                        name = 'bookcase-wall-' + pixels(whole)[:16] + '.png'
                        whole.save(context / name)
                        context_proof['files'][name] = sha(context / name)
                        record = dict(output=name, output_rgba_sha256=pixels(whole),
                                      native_wall=dict(asset=PREFIX + '/wall-upper.png', sha256=sha(mod / PREFIX / 'wall-upper.png')),
                                      native_foreground=dict(asset=old['asset'], sha256=sha(baseline / old['asset']), rgba_sha256=pixels(foreground)),
                                      canvas=[16, 16], offset=[0, 0])
                        if record not in context_proof['compositions']:
                            context_proof['compositions'].append(record)
                        assert all(a[3] == 0 or a == b for a, b in zip(foreground.get_flattened_data(), whole.get_flattened_data()))
                        asset(row, name, 'route30_cd_native_bookcase_wall', context_asset=True)
                    else:
                        asset(row, 'wall-upper.png', 'route30_cd_native_back_wall')
                elif x in (2, 3) and y in (0, 1):
                    name = ('sofa-upper-wall-' + str(x - 2) + '.png' if y == 0
                            else 'sofa-' + str(x - 2) + '-1.png')
                    asset(row, name, 'route30_cd_complete_native_sofa')
                elif row['kind'] == 'native':
                    assert row['role'] == 'johto_facility_shared_floor'
                    row['donor'] = copy.deepcopy(floor)
                    row['role'] = 'route30_cd_matching_native_floor'
                else:
                    # Existing explicit native furniture masks retain every
                    # foreground pixel; only their declared base is replaced.
                    assert row.get('base') and (row.get('parts') or row.get('asset'))
                    row['base'] = copy.deepcopy(floor)
                composed = preview.replacement_image(cache, row, imp.packed, mod)
                assert composed.size == (16, 16) and composed.getchannel('A').getextrema() == (255, 255)
                row['compositionPixelHash'] = pixels(composed)
                rows.append(row)
                changes.append(dict(game=game, xy=[x, y], source_id=bid, quadrant=q,
                                    source_hash=cell['sourceHash'], collision=cell['collision'],
                                    previous_module=module, previous_role=old['role'], previous_row_sha256=digest(old),
                                    previous_rgba_sha256=pixels(preview.replacement_image(cache, old, imp.packed, baseline)),
                                    role=row['role'], rgba_sha256=pixels(composed)))
        assert source_raw_before[game] == sha(cache / game / 'data/generated/maps.lua')

        def patch(left, top, width, height):
            canvas = Image.new('RGBA', (width * 16, height * 16))
            for r in rows:
                if r['game'] == game and left <= r['x'] < left + width and top <= r['y'] < top + height:
                    canvas.paste(preview.replacement_image(cache, r, imp.packed, mod),
                                 ((r['x'] - left) * 16, (r['y'] - top) * 16))
            return canvas

        computer = Image.open(mod / PC_PREFIX / 'wall-pc-whole32x26.png').convert('RGBA')
        actual_computer = patch(6, 0, 2, 2).crop((0, 6, 32, 32))
        assert computer.size == actual_computer.size == (32, 26)
        assert all(not a[3] or a == b for a, b in zip(computer.get_flattened_data(), actual_computer.get_flattened_data()))
        sofa = patch(2, 0, 2, 2)
        for dx in (0, 1):
            upper = Image.open(mod / PREFIX / ('sofa-upper-top-' + str(dx) + '.png')).convert('RGBA')
            lower = Image.open(mod / PREFIX / ('sofa-' + str(dx) + '-1.png')).convert('RGBA')
            assert all(not a[3] or a == b for a, b in zip(upper.get_flattened_data(), sofa.crop((dx * 16, 0, dx * 16 + 16, 16)).get_flattened_data()))
            assert lower.tobytes() == sofa.crop((dx * 16, 16, dx * 16 + 16, 32)).tobytes()
        blocked = []
        for left, top, width, height in ((6, 0, 2, 2), (2, 0, 2, 2)):
            for y in range(top, top + height):
                for x in range(left, left + width):
                    r, = [r for r in rows if r['game'] == game and (r['x'], r['y']) == (x, y)]
                    assert r['sourceCollision'] == 7
                    blocked.append([x, y, r['sourceCollision']])
        geometry_checks.append(dict(game=game, computer_native_canvas=[32, 26], computer_native_rgba_sha256=pixels(computer),
                                    computer_every_native_opaque_pixel_retained=True, computer_padding=[0, 6], sofa_native_size=[32, 32],
                                    sofa_every_native_foreground_pixel_retained=True,
                                    existing_blocked_cells=blocked, new_overhangs=0,
                                    original_walkable_strip_retained=[[x, y] for x in (6, 7) for y in (2, 3)]))

    (context / 'provenance.json').write_text(json.dumps(context_proof, indent=2) + '\n')
    write_rows(mod / MODULE, canonical(rows))
    migrations = []
    for module in (FACILITY, BOOKCASES):
        original = (baseline / module).read_text()
        assert original.endswith('return rows\n') and '-- BEGIN ROUTE30 MR POKEMON MIGRATION' not in original
        (mod / module).write_text(original[:-len('return rows\n')] + FOOTER)
        prior_rows = preview.read_reviewed(baseline / module)
        old_other = [r for r in prior_rows if r.get('map') != MAP]
        new_other = preview.read_reviewed(mod / module)
        assert old_other == new_other, 'Unrelated mappings changed: ' + module
        migrations.append(dict(module=module, superseded_mr_pokemon_rows=len(prior_rows) - len(new_other),
                               every_other_expanded_row_unchanged=True))
    # Local composition checks cannot detect another registered module using
    # the same positioned key. Exercise the complete real runtime index too.
    from lupa.luajit21 import LuaRuntime
    runtime = LuaRuntime(unpack_returned_tuples=True)
    runtime.globals().readSource = lambda name: (mod / name).read_text()
    runtime.globals().registeredPaths = runtime.table_from(list(dict.fromkeys(re.findall(
        r"['\"](mappings/[^'\"]+\.lua)['\"]", (mod / 'main.lua').read_text()))))
    indexed_rows = runtime.execute('''
      local all={}
      for _,path in ipairs(registeredPaths)do
        for _,row in ipairs(assert(load(readSource(path),'@'..path))())do all[#all+1]=row end
      end
      local mapping=assert(load(readSource('lib/mapping.lua'),'@lib/mapping.lua'))()
      local indexed,errors=mapping.index(all)
      assert(#errors==0,table.concat(errors,'\\n'))
      return #all
    ''')
    all_source = {k: source_raw_before[k] == sha(cache / k / 'data/generated/maps.lua') for k in GAMES}
    assert all(all_source.values())
    checks = review.validate_batch(rows, SimpleNamespace(cache=cache, engine=args.engine, output=out), mod)
    assert checks['rows_accepted'] == 192 and checks['rejected'] == 0
    (out / 'proof.json').write_text(json.dumps(dict(scope=MAP, rows=len(rows), games=list(GAMES),
        source_maps_unmodified=all_source, source_definitions=sources, validation=checks,
        complete_registered_mapping_index=dict(rows=indexed_rows, errors=0),
        migrated_modules=migrations,
        complete_native_geometry=geometry_checks,
        every_non_mr_pokemon_facility_row_unchanged=True,
        matching_floor=dict(native_reference=floor, identical_to_asset=PREFIX + '/floor-plain.png'),
        placements=dict(computer=dict(xy=[6, 0], canvas_size=[32, 32], native_size=[32, 26], native_padding=[0, 6], original_blocked_xywh=[6, 0, 2, 2]),
                        sofa=dict(xy=[2, 0], size=[32, 32], original_blocked_xywh=[2, 0, 2, 2])),
        changes=changes), indent=2) + '\n')
    for game in GAMES:
        preview.map_preview(cache, out, game, MAP, game + '-mr-pokemon', rows, imp.packed, 3, mod,
                            roof_rows=[])
        complete = Image.open(out / (game + '-mr-pokemon-after-native.png')).convert('RGBA')
        complete.save(out / (game + '-mr-pokemon-complete-native.png'))
    print(json.dumps(dict(rows=len(rows), validation=checks, proof=str(out / 'proof.json'))))


if __name__ == '__main__':
    main()
