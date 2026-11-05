"""Build reviewed alternate-only FireRed/LeafGreen field states."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import catalog
import preview
from classic_geometry_review import art as classic_art
from reverse_gen2_cerulean_outdoor_completion import mask_bytes, source_indices
from reverse_gen2_kanto_final import Final, ROOT, previous

GUARD = Path(__file__).with_name('reverse_gen2_frlg_field_states_guards.json')
TARGET = 'mappings/reverse_gen2_frlg_field_states.lua'
OUTPUT = ROOT.parent / '.work/tileshift-v0410-conditional-state-art'
PAIR_FEATURES = {
    'firered': {'building__rom_082d4eb4': 'bill', 'general__rom_082d4e24': 'icefall',
                'general__rom_082d507c': 'dotted_hole', 'general__rom_082d4bfc': 'victory_road',
                'general__rom_082d5064': 'warehouse'},
    'leafgreen': {'building__rom_082d4e94': 'bill', 'general__rom_082d4e04': 'icefall',
                  'general__rom_082d505c': 'dotted_hole', 'general__rom_082d4bdc': 'victory_road',
                  'general__rom_082d5044': 'warehouse'},
}
BASE_MIDS = {
    'bill': {693: 650, 694: 650, 695: 662, 696: 662, 697: 645, 698: 692},
    'icefall': {858: 857, 859: 857}, 'dotted_hole': {856: 855},
    'victory_road': {775: 792, 791: 792}, 'warehouse': {687: 779},
}
TEAL = (82, 132, 132)
STEEL = (165, 189, 189)
CREAM = (247, 230, 214)
AQUA = (123, 239, 255)
LIGHT_AQUA = (222, 255, 255)


def source_planes(review, game, pair, mid):
    source = review.imp.cell_index(game)[pair, mid]
    return source_indices(review, game, pair, mid, source)


def source_image(review, game, pair, mid):
    source = review.imp.cell_index(game)[pair, mid]
    return preview.native_donor(review.cache, dict(game=game, tileset=pair, id=mid, hash=source['pixel_sha256']), review.packed)


def exact_backing(donor, planes, colors):
    masks = {name: mask_bytes(values, colors, under=name == 'under') for name, values in planes.items()}
    assert any('1' in mask for mask in masks.values())
    return dict(donor=donor, masks=masks)


def color_map(row):
    return {tuple(item[:3]): tuple(item[3:]) for item in row['classicGeometry']['colorMap']}


def stable_copy(item):
    return json.loads(json.dumps(item, sort_keys=True))


def art(review, game, pair, mid, feature, base):
    palette, planes = source_planes(review, game, pair, mid)
    used = {i for name, values in planes.items() for i in values if i or name == 'under'}
    background = None
    if feature == 'warehouse':
        source = review.imp.cell_index(game)[pair, mid]
        prior = review.imp.cell_index(game)[pair, base['id']]
        assert source['pixel_sha256'] == prior['pixel_sha256'] and source['layer_sha256'] == prior['layer_sha256']
        assert source['behavior'] != prior['behavior']
        return stable_copy(review.art_of(base))
    if feature == 'bill':
        if mid in (693, 694):
            accent = (247, 230, 156) if mid == 693 else (247, 148, 58)
            shades = (TEAL, STEEL, CREAM, accent)
            colors = color_map(base)
            first = 172 if mid == 693 else 174
            colors[palette[first]] = STEEL
            colors[palette[first + 1]] = accent
        elif mid in (695, 696):
            accent = (107, 247, 230) if mid == 695 else (165, 255, 239)
            shades = (TEAL, STEEL, LIGHT_AQUA, accent)
            colors = color_map(base)
            colors[palette[183]] = LIGHT_AQUA
            colors[palette[186 if mid == 695 else 187]] = accent
        elif mid == 697:
            shades = ((66, 132, 90), (132, 197, 132), AQUA, LIGHT_AQUA)
            pulse = {195: 3, 196: 2, 197: 3, 198: 2}
            colors = {palette[i]: shades[pulse.get(i, 0)] for i in sorted(used)}
            background = exact_backing(stable_copy(base['donor']), planes, used - pulse.keys())
        else:
            shades = ((66, 132, 90), (132, 197, 132), AQUA, LIGHT_AQUA)
            ranks = {193: 0, 195: 3, 196: 2, 197: 3, 198: 2, 202: 1, 203: 1}
            colors = {palette[i]: shades[ranks.get(i, 0)] for i in sorted(used)}
            background = exact_backing(stable_copy(base['classicGeometry']['ground']['donor']), planes, {154, 155, 156})
    elif feature == 'icefall':
        ice = [tuple(c) for c in base['classicGeometry']['palette']]
        shades = tuple(ice if mid == 858 else [*ice[:3], (0, 0, 0)])
        colors = color_map(base)
        colors[palette[187]] = shades[3 if mid == 858 else 2]
        if mid == 859:
            colors[palette[188]] = shades[2]
            colors[palette[191]] = shades[3]
    elif feature == 'dotted_hole':
        shades = ((173, 173, 173), (107, 107, 107), (58, 58, 58), (0, 0, 0))
        colors = color_map(base)
        void = review.gb_ref('crystal', 'FAST_SHIP_CABINS_SE_SSE_CAPTAINS_CABIN', 12, 0)
        void['palettes'] = [[[255, 255, 255], [170, 170, 170], [85, 85, 85], [0, 0, 0]] for _ in range(8)]
        assert set(review.gb_image(void).get_flattened_data()) == {(0, 0, 0, 255)}
        native = source_image(review, game, pair, base['id']).get_flattened_data()
        opened = source_image(review, game, pair, mid).get_flattened_data()
        masks = {layer: ''.join('1' if i == 21 and native[p] != opened[p] else '0' for p, i in enumerate(values))
                 for layer, values in planes.items()}
        assert masks['under'].count('1') > 100
        background = dict(donor=void, masks=masks)
    else:
        assert feature == 'victory_road'
        shades = tuple(map(tuple, base['classicGeometry']['palette']))
        colors = color_map(base)
        assert set(palette[i] for i in used) <= colors.keys()
        background = exact_backing(stable_copy(base['classicGeometry']['ground']['donor']), planes, {130, 131})
    colors = {palette[i]: colors[palette[i]] for i in sorted(used)}
    return classic_art(review, game, pair, mid, 'frlg_scripted_' + feature + '_' + str(mid), shades, colors, ground=background)


def emit(review, guard=GUARD, baseline=ROOT):
    contract = json.loads(guard.read_text())
    for entry in contract['scriptFiles']:
        source = review.cache / entry['game'] / entry['path']
        assert catalog.sha(source.read_bytes()) == entry['sha256'], ('Imported script reachability changed', source)
    modules = {}
    records = []
    for item in contract['rows']:
        game, pair, mid = (item[q] for q in ('game', 'pair', 'mid'))
        feature = PAIR_FEATURES[game][pair]
        assert not review.usage.get((game, pair, mid)), ('Conditional tile has a static body use', game, pair, mid)
        source = review.imp.cell_index(game)[pair, mid]
        assert (source['pixel_sha256'], source['layer_sha256'], source['behavior']) == (
            item['sourceHash'], item['sourceLayers'], item['sourceBehavior'])
        for context in item['contexts']:
            spec, layout = review.layouts[game, context['map']]
            assert spec['pair'] == pair and layout['file_sha256'] == context['layoutSHA256']
            assert layout['mids'][context['y'] * layout['width'] + context['x']] == context['before_mid']
        witness = item['base']
        assert BASE_MIDS[feature][mid] == witness['mid']
        path = witness['module']
        if path not in modules:
            modules[path] = {(r['game'], r['style'], r['tileset'], r['id'], r.get('map')): r
                             for r in preview.read_reviewed(baseline / path)}
        base = modules[path][game, 'gen2', pair, witness['mid'], None]
        assert catalog.sha(previous.stable(base).encode()) == witness['semanticSHA256']
        assert catalog.sha(review.render(base).tobytes()) == base['compositionPixelHash']
        recipe = art(review, game, pair, mid, feature, base)
        recipe['role'] = 'reverse_gen2_frlg_scripted_' + feature + '_' + str(mid)
        row = review.row(game, pair, mid, 'gen2', recipe,
            'Actual imported field script or native task selects this complete alternate tile. The replacement preserves its exact source behavior and priority. The engine owns its coordinates, collision and timing.')
        row['frlgFieldStateReview'] = dict(feature=feature, baseMID=base['id'], contexts=item['contexts'])
        changed = None
        if feature in ('bill', 'dotted_hole', 'warehouse'):
            native = source_image(review, game, pair, base['id']).get_flattened_data()
            variant = source_image(review, game, pair, mid).get_flattened_data()
            chosen = review.render(base).get_flattened_data()
            actual = review.render(row).get_flattened_data()
            assert all(a == b for a, b, c, d in zip(chosen, actual, native, variant) if c == d), (game, feature, mid)
            changed = sum(a != b for a, b in zip(chosen, actual))
            assert (changed == 0) == (feature == 'warehouse')
        records.append(dict(game=game, pair=pair, mid=mid, feature=feature, changedPixels=changed,
                            compositionPixelHash=row['compositionPixelHash'], contexts=item['contexts']))
    for game, pairs in PAIR_FEATURES.items():
        pair = next(pair for pair, feature in pairs.items() if feature == 'bill')
        for first, second in ((693, 694), (695, 696)):
            assert review.rows[game, 'gen2', pair, first, None]['compositionPixelHash'] != review.rows[game, 'gen2', pair, second, None]['compositionPixelHash']
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--guard', type=Path, default=GUARD)
    parser.add_argument('--baseline', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    review = Final()
    review.out = args.output
    records = emit(review, args.guard, args.baseline)
    review.write(args.output / 'candidate.lua')
    result = dict(rows=len(records), body_cells=0, records=records, validation=review.validate())
    (args.output / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'records'}))


if __name__ == '__main__':
    main()
