"""Recreate G/S/C's 64x32 Cherrygrove island with native CrystalDust modules.

This builder only replaces existing position-scoped artwork rows. It never
edits imported maps, collision, objects, scripts, warps or saved game data.
"""
from __future__ import annotations
import argparse
import copy
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

HERE = Path(__file__).resolve()
WORKSPACE = next((p for p in [Path.cwd(), *HERE.parents] if (p / '.tools/python').is_dir()), Path.cwd())
sys.path.insert(0, str(WORKSPACE / '.tools/python'))
from PIL import Image
import catalog
import preview
import gen2_extended_review as ext

GAMES = ('gold', 'silver', 'crystal')
MAP = 'CHERRYGROVE_CITY'
MARKER = b'-- BEGIN REVIEWED CRYSTALDUST CHERRYGROVE ISLAND\n'
REMOVE_BANKS = {(3, 10), (3, 11), (6, 10), (6, 11)}
NORTH_ROCKS = {(2, 4), (3, 4), (8, 4), (9, 4), (10, 4), (11, 4)}
ISLAND = {(x, y) for x in range(3, 9) for y in range(12, 15)}
ART_FIELDS = {'donor', 'base', 'parts', 'asset', 'kind', 'artOverlay', 'compositionPixelHash',
              'assetFileHash', 'assetPixelHash', 'credit', 'sourceUrl', 'assetFrames',
              'foreground', 'occludes', 'frames', 'animation', 'animated'}


def key(row):
    return tuple(row.get(name) for name in ('game', 'style', 'tileset', 'map', 'id', 'quadrant', 'x', 'y'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mod', type=Path, default=HERE.parents[1])
    parser.add_argument('--cache', type=Path, default=Path(os.environ['APPDATA']) / 'pokemon-love2d')
    parser.add_argument('--engine', type=Path, default=WORKSPACE / '.work/tileshift-engine-0410')
    parser.add_argument('--output', type=Path, default=WORKSPACE / '.work/tileshift-cherrygrove-island-fix/audit/review')
    parser.add_argument('--validate', action='store_true')
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    mod, cache, output = args.mod.resolve(), args.cache.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    provenance_path = mod / 'assets/third_party/johto-hacks/cherrygrove-coast/provenance.json'
    provenance = json.loads(provenance_path.read_text(encoding='utf-8'))
    assets = {}
    for module in provenance['source_modules'].values():
        image = Image.open(mod / module['asset']).convert('RGBA')
        assert image.size == (16, 16), 'Keep complete native 16px modules'
        assert catalog.sha((mod / module['asset']).read_bytes()) == module['assetFileHash']
        assert catalog.sha(image.tobytes()) == module['assetPixelHash']
        assert module['native_alpha_unchanged']
        for x, y in module['target_cells']:
            assert (x, y) not in assets
            assets[x, y] = module
    assert set(assets) == ISLAND and len(assets) == 18
    for y in (12, 13):
        for x in range(4, 8):
            assert Image.open(mod / assets[x, y]['asset']).convert('RGBA').getchannel('A').getextrema() == (255, 255)

    target = mod / 'mappings/gen2_outdoor_extended.lua'
    original = target.read_bytes()
    if MARKER in original:
        pristine = original.split(MARKER, 1)[0] + b'return rows\n'
        baseline = catalog.plain(catalog.LUA.execute(pristine.decode('utf-8-sig')))
    else:
        assert original.rstrip().endswith(b'return rows')
        pristine = original
        baseline = preview.read_reviewed(target)
    old = {key(row): row for row in baseline}
    assert len(old) == len(baseline), 'Existing duplicate position rows are not acceptable'
    active = ext.active_rows(mod)
    # The source file's pre-update rows are authoritative for this builder.
    active = [old.get(key(row), row) for row in active]
    all_keys = [key(row) for row in active]
    assert len(set(all_keys)) == len(all_keys), 'Do not introduce ambiguous mapping precedence'
    packed, updates, geometry = {}, [], {}

    def native_animation(template, donor):
        spec = copy.deepcopy(template)
        spec.pop('frame0Hash', None)
        frame = preview.native_water_frames(cache, {'donor': donor, 'animation': spec}, packed)[0]
        spec['frame0Hash'] = catalog.sha(frame.tobytes())
        return spec

    for game in GAMES:
        data = ext.source(cache, game)
        definition = data['maps'][MAP]
        assert (definition['width'], definition['height'], definition['tileset']) == (20, 9, 'TILESET_JOHTO')
        block_ids = catalog.lua_array(definition['blocks'])
        positioned = {(row['x'], row['y']): row for row in baseline
                      if row['game'] == game and row.get('map') == MAP and row['style'] == 'gen3' and 'x' in row}
        generic = {(row['id'], row['quadrant']): row for row in baseline
                   if row['game'] == game and row.get('map') == MAP and row['style'] == 'gen3' and 'x' not in row}
        ocean = copy.deepcopy(next(row for row in baseline if row['game'] == game and row.get('map') == MAP
                                   and row['role'] == 'coastal_ocean_water_interior' and row.get('donor', {}).get('id') == 368))
        bank = copy.deepcopy(next(row for row in baseline if row['game'] == game and row.get('map') == MAP
                                  and row['role'] == 'rocky_coast_north' and row.get('donor', {}).get('id') == 393))
        assert ocean['donor']['id'] == 368 and bank['donor']['id'] == 393
        water_animation = native_animation(ocean['animation'], ocean['donor'])
        bank_animation = native_animation(bank['animation'], bank['donor'])
        dry_floor = []
        for x, y in sorted(ISLAND | REMOVE_BANKS | NORTH_ROCKS, key=lambda value: (value[1], value[0])):
            bid = block_ids[y // 2 * definition['width'] + x // 2]
            q = y % 2 * 2 + x % 2
            position_exists = (x, y) in positioned
            row = copy.deepcopy(positioned[x, y] if position_exists else generic[bid, q])
            cell = ext.cell_info(cache, game, data, definition['tileset'], bid, q)
            assert row['id'] == bid and row['quadrant'] == q
            assert row['sourceHash'] == cell['sourceHash'] and row['sourceCollision'] == cell['collision']
            assert row['sourceFiles'] == data['fingerprints'][definition['tileset']]
            assert (row['sourceCells'] == [[x, y]]) if position_exists else [x, y] in row['sourceCells']
            row.update(x=x, y=y, sourceCells=[[x, y]])
            if (x, y) in ISLAND:
                for field in ART_FIELDS:
                    row.pop(field, None)
                module = assets[x, y]
                floor = x in range(4, 8) and y in (12, 13)
                assert cell['collision'] == (0 if floor else 0x29)
                if floor:
                    dry_floor.append([x, y])
                row.update(kind='third_party', asset=module['asset'], assetFileHash=module['assetFileHash'],
                           assetPixelHash=module['assetPixelHash'], credit=module['credit'], sourceUrl=module['sourceUrl'],
                           base=copy.deepcopy(ocean['donor']), animation=copy.deepcopy(water_animation), animated=True,
                           role='coastal_rock_shore_crystaldust_' + Path(module['asset']).stem)
                row['evidence'] = ('Reviewed CrystalDust Cherrygrove native16px module, donor ' + str(module['donor_mid'])
                    + '/' + module['donor_plane'] + '. Complete native pixels and native alpha retained at1:1 scale. '
                    'The original G/S/C64x32 walkable floor remains x4..7,y12..13, including Fisher(7,12); '
                    'only the ten surrounding native-water cells carry decorative shore fringes. No native water RGB '
                    'is baked into the alpha module: current selected animated water shows through all exterior pixels. '
                    'The small CrystalDust map island is not scaled or copied as a whole. Exact source coordinates, '
                    'source pixels, palette and priority, all collision and source map/event fingerprints remain native.')
            elif (x, y) in REMOVE_BANKS:
                assert cell['collision'] == 0x29
                for field in ART_FIELDS:
                    row.pop(field, None)
                row.update(donor=copy.deepcopy(ocean['donor']), animated=True, animation=copy.deepcopy(water_animation),
                           role='coastal_ocean_water_interior')
                row['evidence'] = ('Reviewed exact Cherrygrove water cells flanking only the island boulder atx4..5,y10..11. '
                    'Remove the two disconnected vertical shore strips atx3/6,y10..11. Complete native Emerald368 '
                    'ocean frames and selected water artwork remain continuous; original water collision0x29, '
                    'source geometry, Surf/fishing and map events are unchanged. No shared bank ID is globally replaced.')
            else:
                assert bid == 10 and q in (0, 1) and cell['collision'] == 7
                assert row['kind'] == 'native_composite' and row.get('parts')
                row['base'] = copy.deepcopy(bank['donor'])
                row['animation'] = copy.deepcopy(bank_animation)
                row['evidence'] = ('Reviewed the three northern Cherrygrove boulders atx2..3/8..9/10..11,y4..5. '
                    'Retain every existing complete FireRed rock middle-plane pixel and its unchanged32x32 blocked '
                    'footprint. Only the upper two source cells per boulder use complete Emerald393 shoreline as '
                    'their animated base, continuing the adjacent north bank behind transparent rock corners. '
                    'The lower two cells retain ocean368. This exact-position correction does not alter the four '
                    'other whole outcrops, the island boulder, source collision7 or source maps/events.')
            row['status'] = 'reviewed'
            row['compositionPixelHash'] = catalog.sha(preview.replacement_image(cache, row, packed, mod).tobytes())
            updates.append(row)
        assert len(dry_floor) == 8 and [7, 12] in dry_floor
        geometry[game] = {'sourceFiles': data['fingerprints'][definition['tileset']],
                          'walkable_floor_cells': dry_floor, 'walkable_floor_pixels': [64, 32],
                          'fisher': next(obj for obj in definition['objects'] if obj['x'] == 7 and obj['y'] == 12)}
    assert len(updates) == 84 and len({key(row) for row in updates}) == 84
    changes = {key(row): row for row in updates}
    additions = [row for row in updates if key(row) not in old]
    assert len(additions) == 12 and all(row['y'] == 14 and row['x'] in range(4, 8) for row in additions)
    changed = [changes.get(key(row), row) for row in baseline]
    assert sum(left != right for left, right in zip(baseline, changed)) == 72
    changed += additions
    staged = [changes.get(key(row), row) for row in active] + additions
    validation = ext.validate_batch(updates, SimpleNamespace(cache=cache, engine=args.engine, output=output), mod) if args.validate else None
    body, compact = ext.write_compact(updates, None)
    prefix = pristine.rstrip()[:-len(b'return rows')].rstrip() + b'\n'
    footer = '''local function islandKey(row)return table.concat({row.game,row.style,row.tileset,row.map or '',row.id,row.quadrant,row.x or '',row.y or ''},':')end
local islandUpdates=(function()
''' + body + '''end)()
local islandIndex={}for i,row in ipairs(rows)do islandIndex[islandKey(row)]=i end
local islandApplied=0
for _,row in ipairs(islandUpdates)do local i=islandIndex[islandKey(row)];if i then rows[i]=row else rows[#rows+1]=row end;islandApplied=islandApplied+1 end
assert(islandApplied==84,'Incomplete reviewed Cherrygrove island update')
return rows
'''
    result = prefix + MARKER + footer.encode('utf-8')
    expanded = catalog.plain(catalog.LUA.execute(result.decode('utf-8-sig')))
    assert {key(row): row for row in expanded} == {key(row): row for row in changed}
    assert len(expanded) == len(baseline) + 12 and len({key(row) for row in expanded}) == len(expanded)
    (output / 'candidates.json').write_text(json.dumps(updates, indent=2) + '\n', encoding='utf-8')
    (output / 'candidate-mapping.lua').write_bytes(result)
    report = {'status': 'reviewed_native_crystaldust_island', 'changed_rows': 84,
              'rows_per_game': 28, 'island_cells_per_game': 18, 'removed_bank_cells_per_game': 4,
              'shore_under_rock_cells_per_game': 6, 'source_geometry': geometry,
              'existing_position_rows_replaced': 72, 'new_position_rows': 12,
              'unrelated_rows_unchanged': len(baseline)-72, 'mapping_rows_before_after': [len(baseline), len(expanded)],
              'duplicate_keys': 0, 'live_decoder': validation, 'compact': compact,
              'source_mapping_before_sha256': catalog.sha(original), 'source_mapping_after_sha256': catalog.sha(result),
              'provenance_sha256': catalog.sha(provenance_path.read_bytes())}
    if args.activate:
        target.write_bytes(result)
    (output / 'proof.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'changed_rows': 84, 'live_decoder': validation, 'activated': args.activate}, indent=2))


if __name__ == '__main__':
    main()
