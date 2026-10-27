"""Exact reviewed freshwater shapes in Violet's inland ponds; no ocean inference."""
import argparse
import copy
import json
import os
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
import preview
import gen2_extended_review as ext
from interior_review import Imports
from gen2_cave_review import contact

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    cache = Path(os.environ['APPDATA']) / 'pokemon-love2d'
    mod = ROOT / 'TileShift'
    output = ROOT / '.work/tileshift-violet-pond-review'
    output.mkdir(exist_ok=True)
    active = ext.active_rows(mod)
    imports = Imports(cache, ROOT / '.work/tileshift-catalog')
    native_corner = imports.cell_index('firered')['general__rom_082d4e24', 436]
    corner_ref = {'game': 'firered', 'tileset': 'general__rom_082d4e24', 'id': 436, 'hash': native_corner['pixel_sha256']}
    native_image, native_rows, native_tiles, _ = imports.gba('firered', 'FR_FOUR_ISLAND_ICEFALL_CAVE_ENTRANCE')
    native_at = {(x, y): row['id'] for row in native_rows for x, y in row['coordinates']}
    assert native_at[13, 25] == 436 and native_at[13, 24] == 429 and native_at[12, 25] == 422
    assert native_at[14, 25] == 430 and native_at[13, 26] == 430
    packed = {}
    for mid in (422, 429, 430):
        old = imports.cell_index('firered')['viridian_outdoor', mid]
        new = imports.cell_index('firered')['general__rom_082d4e24', mid]
        assert old['pixel_sha256'] == new['pixel_sha256'], 'Native inward corner must join the exact already-reviewed bank family'
    corner = preview.native_donor(cache, corner_ref, packed)
    context = native_image.crop((12 * 16, 24 * 16, 15 * 16, 27 * 16))
    contact(output / 'whole-native-inward-corner-context.png', 'Actual native NW inward pond corner436: north429, west422 and other neighbors430 exactly match the reviewed bank family',
        [('Whole native16px corner', corner), ('Actual FR Icefall entrance3x3', context)], columns=2)
    rows, summary = [], []
    for game in ext.GAMES:
        data = ext.source(cache, game)
        definition = data['maps']['VIOLET_CITY']
        known = {}
        for old in active:
            if old['game'] != game or old.get('map') != 'ROUTE_30' or not old['role'].startswith('freshwater_pond_'):
                continue
            source = ext.cell_info(cache, game, data, old['tileset'], old['id'], old['quadrant'])
            key = ext.identity(source)
            assert key not in known or known[key]['donor'] == old['donor']
            known[key] = old
        assert len({r['role'] for r in known.values()}) == 6
        occurrences = defaultdict(list)
        for i, bid in enumerate(definition['blocks']):
            for q in range(4):
                occurrences[bid, q].append([i % definition['width'] * 2 + q % 2, i // definition['width'] * 2 + q // 2])
        current = []
        for (bid, q), coords in occurrences.items():
            source = ext.cell_info(cache, game, data, definition['tileset'], bid, q)
            template = known.get(ext.identity(source))
            inward = source['tiles'] == [77, 20, 20, 20]
            if inward:
                assert coords == [[30, 10]] and source['collision'] == 0x29
                def source_at(x, y):
                    block = definition['blocks'][y // 2 * definition['width'] + x // 2]
                    return ext.cell_info(cache, game, data, definition['tileset'], block, y % 2 * 2 + x % 2)
                assert source_at(30, 9)['tiles'] == [61, 20, 61, 20]
                assert source_at(29, 10)['tiles'] == [76, 76, 20, 20]
                assert source_at(31, 10)['tiles'] == source_at(30, 11)['tiles'] == [20, 20, 20, 20]
                template = next(r for r in known.values() if r['role'] == 'freshwater_pond_interior')
            if not template:
                continue
            assert source['collision'] == 0x29
            assert all((10 <= x <= 17 and 0 <= y <= 15) or (26 <= x <= 33 and 2 <= y <= 13) for x, y in coords), 'Freshwater proposal escaped the actual two inland ponds'
            row = copy.deepcopy(template)
            row.update(map='VIOLET_CITY', tileset=definition['tileset'], id=bid, quadrant=q,
                sourceHash=source['sourceHash'], sourceFiles=data['fingerprints'][definition['tileset']],
                sourceCells=coords, sourceCollision=source['collision'],
                sourcePalettes=[a.get('palette', 1) for a in source['attributes']],
                sourcePriority=[bool(a.get('priority')) for a in source['attributes']],
                sourceBody='two bounded inland ponds in Violet City', status='reviewed')
            row['evidence'] = 'Reviewed Violet inland pond counterpart. Both full source ponds are bounded in the actual town context, excluding ocean, bridge, current and waterfall art. Exact rendered source pixels, movement byte0x29, palette slots and priority match the reviewed Route30/31 inland pond shapes independently per cartridge. Complete native FR Viridian pond banks preserve their brown rock material and orientation; native430 supplies calm pond interior. Source Surf, fishing, encounters, collision and map layout stay unchanged. The unmatched inward shoreline corner remains original until independently reviewed.'
            if inward:
                row.update(role='freshwater_pond_inward_northwest_bank', donor=corner_ref,
                    nativeContext={'map': 'FR_FOUR_ISLAND_ICEFALL_CAVE_ENTRANCE', 'cell': [13, 25], 'north': 429, 'west': 422, 'east': 430, 'south': 430})
                row['evidence'] = 'Reviewed complete native16px inward northwest pond corner436, actually used at FRFourIslandIcefallCaveEntrance13,25. Its actual native north429, west422, east430 and south430 have byte-identical pixels to the already reviewed Viridian pond bank/interior family. Original Violet30,10 has precisely the same topology: west-bank cell above, north-bank cell left, open pond right/below, and only the upper-left8px source corner contains rock. Each cartridge source pixels, collision0x29, palette/priority and actual neighboring source cells are independently checked. The entire native cell is retained without cropping, mirroring or scaling. Source Surf, fishing, collision, map layout and events remain unchanged.'
            current.append(row)
        rows += current
        summary.append({'game': game, 'rows': len(current), 'source_cells': sum(len(r['sourceCells']) for r in current)})
    live = ext.validate_batch(rows, SimpleNamespace(cache=cache, engine=ROOT / '.tools/engine-0395', output=output), mod)
    for game in ext.GAMES:
        preview.map_preview(cache, output, game, 'VIOLET_CITY', game + '-violet-ponds', active + rows, {}, 2, mod)
    (output / 'candidates.json').write_text(json.dumps(rows, indent=2))
    (output / 'proof.json').write_text(json.dumps({'status': 'private_full_context_review', 'summary': summary, 'live': live}, indent=2))
    if args.activate:
        result = ext.merge_reviewed(rows, mod / 'mappings/gen2_outdoor_extended.lua')
        (output / 'activation.json').write_text(json.dumps({'mapping': result, 'live': live, 'summary': summary}, indent=2))
    print(json.dumps({'summary': summary, 'live': live, 'active': args.activate}))


if __name__ == '__main__':
    main()
