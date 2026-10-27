"""Violet's decorative house and two real east-gate warp-carpet markers."""
import argparse
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
from PIL import Image
import catalog
import preview
import gen2_extended_review as ext
import kanto_architecture_review as kanto
from interior_review import Imports

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    cache, mod = Path(os.environ['APPDATA']) / 'pokemon-love2d', ROOT / 'TileShift'
    output = ROOT / '.work/tileshift-violet-facade-review'
    output.mkdir(exist_ok=True)
    imports = Imports(cache, ROOT / '.work/tileshift-catalog')
    original = ROOT / '.work/tileshift-building-kanto'
    model = json.loads((original / 'kanto-building-variants.json').read_text())['templates']['home32']
    assert model['size_px'] == [64, 32] and model['door_bottom_anchor_px'] == [24, 32]
    (output / 'home32-compact-prototype.png').write_bytes((original / 'home32-compact-prototype.png').read_bytes())
    active = ext.active_rows(mod)
    paving = next(r['donor'] for r in active if r['role'] == 'violet_paved_walkway')
    arrow = next(p['donor'] for r in active for p in r.get('parts', [])
                 if p['donor'].get('kind') == 'field_effect' and p['donor'].get('id') == 6)
    packed, instances = {}, []
    for game in ext.GAMES:
        data = ext.source(cache, game)
        definition = data['maps']['VIOLET_CITY']
        assert not any(2 <= w['x'] <= 5 and 28 <= w['y'] <= 29 for w in definition.get('warps', [])), 'Decorative house gained an entrance event'
        for y in (24, 25):
            warp = next(w for w in definition['warps'] if (w['x'], w['y']) == (39, y))
            assert warp['destMap'] == 'ROUTE_31_VIOLET_GATE' and warp['destWarp'] == y - 23
        instances.append({'game': game, 'map': 'VIOLET_CITY', 'destination': 'decorative house, no source entrance event',
            'template': 'home32', 'rect_cells': [2, 28, 4, 2], 'door_map_cell': [3, 29], 'door_bottom_anchor_px': [24, 32]})
    stage = SimpleNamespace(cache=cache, catalog=imports.catalogs, output=output, approved_candidates=True, write_reviewed=False)
    buildings = kanto.positioned_rows(stage, {'home32': model}, instances)
    (output / 'decorative-native-model.json').write_text(json.dumps({'templates': {'home32': model},
        'source_instances': [{**r, 'destination': 'DECORATIVE_HOUSE_NO_WARP', 'no_source_warp': True} for r in instances]}, indent=2))
    assert len(buildings) == 24
    for row in buildings:
        row['role'] = 'architecture_decorative_home32'
        row['sourceDecorativeFacade'] = {'entrance_event_present': False, 'physical_door_cell': [3, 29]}
        row['evidence'] = 'PRIVATE complete64x32 decorative Violet house facade. The original physical door is at3,29, but no warp event exists anywhere in this source building; it remains inaccessible. The previously reviewed compact native FR home32 retains its entire17px door/window frames, complete roof and sidewalls without scaling, using the same24,32 physical door anchor. Each cartridge source files, pixels and exact positions are checked. The northwestern roof backs onto original paved cells while the northeastern roof backs onto forest; only empty native roof pixels change background. No warp, map layout, collision, actor, script or event is added or changed.'
        if row['y'] == 28 and row['x'] in (2, 3):
            before = preview.replacement_image(cache, row, packed, mod)
            row['base'] = copy.deepcopy(paving)
            after = preview.replacement_image(cache, row, packed, mod)
            row['compositionPixelHash'] = catalog.sha(after.tobytes())
            assert before.tobytes() != after.tobytes(), 'Expected a real empty roof corner on the paved side'
    prototype = Image.open(output / 'home32-compact-prototype.png').convert('RGBA')
    for game in ext.GAMES:
        whole = Image.new('RGBA', (64, 32))
        for row in buildings:
            if row['game'] == game:
                whole.paste(preview.replacement_image(cache, row, packed, mod), ((row['x'] - 2) * 16, (row['y'] - 28) * 16))
        for feature in model['features_checked']:
            x, y, w, h = feature['target_rect_xywh']
            assert whole.crop((x, y, x + w, y + h)).tobytes() == prototype.crop((x, y, x + w, y + h)).tobytes(), 'Whole native house frame changed'
    markers = []
    for game in ext.GAMES:
        data = ext.source(cache, game)
        definition = data['maps']['VIOLET_CITY']
        for y in (24, 25):
            x = 39
            bid = definition['blocks'][y // 2 * definition['width'] + x // 2]
            q = y % 2 * 2 + x % 2
            cell = ext.cell_info(cache, game, data, definition['tileset'], bid, q)
            assert cell['tiles'] == [64] * 4 and cell['collision'] == 0x7e
            row = {'game': game, 'style': 'gen3', 'map': 'VIOLET_CITY', 'tileset': definition['tileset'],
                'id': bid, 'quadrant': q, 'x': x, 'y': y, 'sourceCells': [[x, y]], 'sourceHash': cell['sourceHash'],
                'sourceFiles': data['fingerprints'][definition['tileset']], 'sourceCollision': cell['collision'],
                'status': 'reviewed', 'role': 'violet_east_gate_warp_marker', 'kind': 'native_composite', 'base': paving,
                'parts': [{'donor': arrow, 'srcX': 0, 'srcY': 0, 'w': 16, 'h': 16, 'x': 0, 'y': 0}],
                'evidence': 'PRIVATE complete native FR right-arrow frame6 over Violet paving for original east-gate warp carpets. Source0x7e is COLL_WARP_CARPET_RIGHT in the native Gen2 permissions table, and both exact cells39,24/25 have original Route31VioletGate warp events1/2. The full native14x13 arrow silhouette stays inside the original16px cell with no clipping or scaling and remains static, matching the source permanent exit indication. Original gate destination, step direction, movement and event behavior remain native; no new transition or warp is created.'}
            image = preview.replacement_image(cache, row, packed, mod)
            row['compositionPixelHash'] = catalog.sha(image.tobytes())
            markers.append(row)
    probe = copy.deepcopy(buildings + markers)
    for row in probe:
        row.setdefault('sourceCells', [[row['x'], row['y']]])
    live = ext.validate_batch(probe, SimpleNamespace(cache=cache, engine=ROOT / '.tools/engine-0395', output=output), mod)
    results = [preview.map_preview(cache, output, game, 'VIOLET_CITY', game + '-violet-complete', active + buildings + markers, packed, 2, mod) for game in ext.GAMES]
    assert next(r for r in results if r['game'] == 'crystal')['replaced_occurrences'] == 1440
    assert all(r['visible_cells'] == 1440 and r['replaced_occurrences'] >= 1434 for r in results)
    complete = all(r['replaced_occurrences'] == 1440 for r in results)
    (output / 'kanto-staged-rows.json').write_text(json.dumps(buildings, indent=2, sort_keys=True))
    (output / 'marker-candidates.json').write_text(json.dumps(markers, indent=2))
    (output / 'proof.json').write_text(json.dumps({'status': 'private_full_town_review', 'buildings': len(buildings),
        'markers': len(markers), 'live': live, 'complete_towns': results, 'decorative_house_has_no_entrance': True}, indent=2))
    if args.activate:
        verified = json.loads((output / 'facade-production-proof.json').read_text())
        assert verified['session_rejected'] == 0 and verified['actual_positioned_session_cells_verified'] == 24
        assert verified['private_candidate_file_sha256'] == catalog.sha((output / 'kanto-staged-rows.json').read_bytes())
        for row in buildings + markers:
            row['evidence'] = row['evidence'].replace('PRIVATE complete', 'Reviewed complete')
        path = mod / 'mappings/buildings_extended.lua'
        text = path.read_text().rstrip()
        assert text.endswith('return rows')
        old = preview.read_reviewed(path)
        keys = {(r['game'], r.get('map'), r.get('x'), r.get('y')) for r in old}
        assert all((r['game'], r['map'], r['x'], r['y']) not in keys for r in buildings)
        text = text[:-len('return rows')] + 'add((function() return {\n' + ''.join('  ' + kanto.common.lua(r) + ',\n' for r in buildings) + '} end)())\nreturn rows\n'
        path.write_text(text)
        assert preview.read_reviewed(path)[:len(old)] == old
        stats = ext.merge_reviewed(markers, mod / 'mappings/gen2_outdoor_extended.lua')
        (output / 'activation.json').write_text(json.dumps({'added_building_rows': len(buildings), 'markers': stats, 'live': live}, indent=2))
    print(json.dumps({'buildings': len(buildings), 'markers': len(markers), 'live': live,
        'all_three_towns_complete': complete, 'active': args.activate}))


if __name__ == '__main__':
    main()
