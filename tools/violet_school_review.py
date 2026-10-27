"""Retain Gold/Silver's full school footprint; Crystal has a shorter building."""
import argparse
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
from PIL import Image, ImageDraw, ImageFont
import catalog
import preview
import architecture_review as common
import kanto_architecture_review as kanto
from newbark_building_review import native_reference

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    cache, mod = Path(os.environ['APPDATA']) / 'pokemon-love2d', ROOT / 'TileShift'
    output = ROOT / '.work/tileshift-violet-school-review'
    output.mkdir(exist_ok=True)
    stage = SimpleNamespace(cache=cache, catalog=ROOT / '.work/tileshift-catalog', output=output,
        approved_candidates=True, write_reviewed=False)
    config = copy.deepcopy(common.TEMPLATES['school'])
    config.update(size=(96, 64), rows=tuple(range(8)), roof_rows=6, anchor=(40, 64))
    config['features'] = tuple((name, src, (dst[0], dst[1] + 16, dst[2], dst[3])) for name, src, dst in config['features'])
    config['notes'] = 'Gold/Silver school variant: complete original96x64 footprint including its extra north roof row. Actual native FRViridian Pokemon School retains its entire64px height; repeated plain roof/wall spacing fills96px width. The whole optional chimney/shadow component stays omitted, matching the reviewed Crystal style. All four complete facade/flower-box/window/door units retain every native pixel. Source40,64 door anchor and actual Earl Academy warp are unchanged. Crystal retains its independently reviewed96x48 school and the six Headbutt trees north of it.'
    packed = {}
    ground_ref = json.loads((ROOT / '.work/tileshift-building-extended/architecture-native-prototypes.json').read_text())['templates']['school']['base']
    ground = preview.native_donor(cache, ground_ref, packed)
    native, source = native_reference(stage, 'school_tall', config, packed)
    prototype, model = common.compose(stage, 'school_tall', config, native, source, ground, ground_ref, packed)
    instances = []
    for game in ('gold', 'silver'):
        definition, _, _, original = kanto.source_map(cache, game, 'VIOLET_CITY')
        warp = next(w for w in definition['warps'] if w['destMap'] == 'EARLS_POKEMON_ACADEMY')
        assert (warp['x'], warp['y']) == (30, 17) and warp['destWarp'] == 1
        instances.append({'game': game, 'map': 'VIOLET_CITY', 'destination': 'EARLS_POKEMON_ACADEMY',
            'template': 'school_tall', 'rect_cells': [28, 14, 6, 4], 'door_map_cell': [30, 17], 'door_bottom_anchor_px': [40, 64]})
        margin = original.crop((27 * 16, 13 * 16, 35 * 16, 19 * 16)).resize((512, 384), Image.Resampling.NEAREST).convert('RGB')
        draw = ImageDraw.Draw(margin)
        draw.rectangle((64, 64, 447, 319), outline='#ff80be', width=2)
        margin.save(output / (game + '-whole-school-source-boundary.png'))
    rows = kanto.positioned_rows(stage, {'school_tall': model}, instances)
    assert len(rows) == 48
    (output / 'school-tall-model.json').write_text(json.dumps({'templates': {'school_tall': model}, 'source_instances': instances}, indent=2))
    (output / 'kanto-staged-rows.json').write_text(json.dumps(rows, indent=2, sort_keys=True))
    all_rows = []
    for path in (mod / 'mappings').glob('*.lua'):
        all_rows += preview.read_reviewed(path)
    contexts = [preview.map_preview(cache, output, game, 'VIOLET_CITY', game + '-violet-school-complete', all_rows + rows, packed, 2, mod) for game in ('gold', 'silver', 'crystal')]
    assert all(r['visible_cells'] == r['replaced_occurrences'] == 1440 for r in contexts)
    (output / 'whole-source-contexts.json').write_text(json.dumps(contexts, indent=2))
    if args.activate:
        proof = json.loads((output / 'school-production-proof.json').read_text())
        assert proof['session_rejected'] == 0 and proof['actual_positioned_session_cells_verified'] == 48
        assert proof['private_candidate_file_sha256'] == catalog.sha((output / 'kanto-staged-rows.json').read_bytes())
        target = mod / 'mappings/buildings_extended.lua'
        before, lines, removed = preview.read_reviewed(target), [], []
        for raw in target.read_bytes().splitlines(keepends=True):
            if b'VIOLET_CITY' in raw and b'architecture_school' in raw and raw.lstrip().startswith(b'{'):
                row = catalog.plain(catalog.LUA.execute('return ' + raw.decode().strip().removesuffix(',')))
                if row['game'] in ('gold', 'silver') and row['role'] == 'architecture_school':
                    assert 28 <= row['x'] <= 33 and 15 <= row['y'] <= 17
                    removed.append(row)
                    continue
            lines.append(raw)
        assert len(removed) == 36
        body = b''.join(lines).rstrip()
        assert body.endswith(b'return rows')
        body = body[:-len(b'return rows')] + ('add((function() return {\n' + ''.join('  ' + common.lua(r) + ',\n' for r in rows) + '} end)())\nreturn rows\n').encode()
        compiled = catalog.plain(catalog.LUA.execute(body.decode()))
        assert len(compiled) == len(before) + 12
        retained = [r for r in before if r not in removed]
        assert compiled[:len(retained)] == retained and compiled[len(retained):] == rows
        target.write_bytes(body)
        (output / 'activation.json').write_text(json.dumps({'removed_partial_height_rows': 36, 'whole_footprint_rows': 48,
            'crystal_rows_unchanged': True, 'production_total': len(compiled), 'all_three_towns_complete': True}, indent=2))
    print(json.dumps({'rows': len(rows), 'complete_native_features': len(model['features_checked']),
        'whole_gold_silver_footprint': [96, 64], 'all_three_towns_complete': True, 'active': args.activate}))


if __name__ == '__main__':
    main()
