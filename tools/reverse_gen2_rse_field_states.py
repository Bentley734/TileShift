"""Build reviewed Ruby, Sapphire and Emerald Crystal-theme field alternates."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import struct
import zlib

import catalog
import preview
from classic_geometry_review import art as classic_art
from reverse_common import ReverseReview, ROOT
from reverse_gen2_cerulean_outdoor_completion import source_indices


GAMES = ('ruby', 'sapphire', 'emerald')
GUARD = Path(__file__).with_name('reverse_gen2_rse_field_states_guards.json')
OUTPUT = ROOT.parent / '.work/tileshift-v0430-rse-field-states/replay'
ICE = ((239, 255, 255), (140, 214, 247), (66, 140, 181), (0, 0, 0))
TRUCK = ((247, 247, 255), (181, 189, 197), (99, 115, 132), (0, 0, 0))
ART_FIELDS = ('kind', 'donor', 'base', 'parts', 'overMask', 'foreground', 'occludes')


def stable(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def art_fields(row):
    return {key: copy.deepcopy(row[key]) for key in ART_FIELDS if key in row}


def display_light(review, base, family):
    """Relight only the existing complete Crystal display's inner glass."""
    if family == 'pc_power':
        screen = (3, 5, 13, 10)
        colors = {(58, 58, 58): (74, 123, 123), (107, 107, 107): (123, 173, 173)}
    else:
        screen = (3, 3, 13, 13)
        colors = {(74, 74, 255): (123, 132, 255), (123, 132, 255): (181, 189, 255)}
    art = art_fields(base)
    parts = []
    for original in art['parts']:
        x, y = original.get('x', 0), original.get('y', 0)
        x0, y0 = max(screen[0], x), max(screen[1], y)
        x1, y1 = min(screen[2], x + original['w']), min(screen[3], y + original['h'])
        if x0 >= x1 or y0 >= y1:
            continue
        donor = copy.deepcopy(original['donor'])
        game = donor['game']
        palettes = donor.get('palettes') or preview.palette_set(review.imp.table(game, 'palettes'),
                    review.imp.table(game, 'maps')[donor['map']], donor.get('daytime', 'DAY'))
        donor['palettes'] = [[list(colors.get(tuple(rgb), tuple(rgb))) for rgb in p] for p in palettes]
        parts.append(dict(donor=donor, srcX=original.get('srcX', 0) + x0 - x,
                          srcY=original.get('srcY', 0) + y0 - y, w=x1-x0, h=y1-y0, x=x0, y=y0))
    assert parts
    art['parts'].extend(parts)
    return art, screen


def layer_colors(review, game, pair, mid):
    source = review.imp.cell_index(game)[pair, mid]
    palette, planes = source_indices(review, game, pair, mid, source)
    indices = {i for layer, pixels in planes.items() for i in pixels if i or layer == 'under'}
    return {i: palette[i] for i in sorted(indices)}


def make_art(review, item, base):
    game, pair, mid, family = (item[k] for k in ('game', 'pair', 'mid', 'feature'))
    if family in ('pc_power', 'television_power'):
        return display_light(review, base, family)
    if family == 'cut_grass':
        sources = review.imp.cell_index(game)
        target, donor = sources[pair, mid], sources[base['tileset'], base['id']]
        for field in ('pixel_sha256', 'layer_sha256', 'behavior'):
            assert target[field] == donor[field], (game, pair, mid, field)
        return art_fields(base), None

    source = layer_colors(review, game, pair, mid)
    if family == 'moving_truck_exit':
        palette = TRUCK
        ranks = {97: 1, 98: 2, 99: 2, 104: 2}
        colors = {source[index]: palette[ranks[index]] for index in source}
    elif family == 'sootopolis_ice':
        palette = ICE
        ranks = {97: 0, 98: 0, 99: 1, 100: 1, 101: 2, 102: 2, 105: 2, 106: 3}
        colors = {source[index]: palette[ranks[index]] for index in source}
    else:
        assert family == 'lottery_laptop'
        old = base['classicGeometry']
        palette = tuple(map(tuple, old['palette']))
        base_colors = {tuple(c[:3]): tuple(c[3:]) for c in old['colorMap']}
        colors = {color: base_colors[color] for color in source.values()}
    return classic_art(review, game, pair, mid, 'rse_field_' + family + '_' + str(mid), palette, colors), None


def emit(review, baseline, guard):
    contract = json.loads(guard.read_text())
    assert contract['version'] == 1
    files = {}
    for entry in contract['nativeFiles']:
        raw = (review.cache / entry['game'] / entry['file']).read_bytes()
        assert catalog.sha(raw) == entry['sha256'], ('Imported field-state file changed', entry)
        files[entry['game'], entry['file']] = raw
    modules = {}
    records = []
    for item in contract['rows']:
        game, pair, mid = (item[k] for k in ('game', 'pair', 'mid'))
        source = review.imp.cell_index(game)[pair, mid]
        assert (source['pixel_sha256'], source['layer_sha256'], source['behavior']) == (
            item['sourceHash'], item['sourceLayers'], item['sourceBehavior'])
        for context in item['contexts']:
            spec = review.imp.table(game, 'gba/native/manifest')['layouts'][context['map']]
            assert spec['pair'] == pair
            raw = files[game, 'data/generated/gba/native/' + spec['file']]
            raw = raw if raw[:4] == b'SVML' else zlib.decompress(raw)
            assert raw[:4] == b'SVML'
            width, height, logical_width, logical_height = struct.unpack_from('<HHHH', raw, 6)
            x, y = context['x'], context['y']
            assert 0 <= x < (logical_width or width) and 0 <= y < (logical_height or height)
            cell = struct.unpack_from('<HBB', raw, 16 + 2 * raw[14] * raw[15] + 4 * (width * y + x))
            assert cell == (context['before_mid'], context['source_collision'], context['elevation']), ('Native map witness changed', context)
        proof = item['base']
        module = proof['module']
        if module not in modules:
            modules[module] = {(r['game'],r['style'],r['tileset'],r['id']): r
                               for r in preview.read_reviewed(baseline/module) if r.get('map') is None}
        base = modules[module][game, 'gen2', proof['pair'], proof['mid']]
        assert catalog.sha(stable(base).encode()) == proof['sha256'], ('Reviewed adjacent artwork changed', proof)
        prior = review.render(base)
        assert catalog.sha(prior.tobytes()) == base['compositionPixelHash']
        art, screen = make_art(review, item, base)
        art['role'] = 'reverse_gen2_rse_field_' + item['feature']
        row = review.row(game, pair, mid, 'gen2', art,
                         'Verified imported field action selects this complete alternate tile. The art preserves its source identity and the engine owns its collision, coordinates and timing.')
        result = review.render(row)
        changed = [i for i, (a,b) in enumerate(zip(prior.get_flattened_data(), result.get_flattened_data())) if a != b]
        if screen:
            assert changed and all(screen[0] <= i % 16 < screen[2] and screen[1] <= i // 16 < screen[3] for i in changed)
        elif item['feature'] != 'cut_grass':
            assert changed, (game, pair, mid, 'Alternate phase cannot be distinguished')
        row['rseFieldStateReview'] = dict(feature=item['feature'], baseMID=base['id'], contexts=item['contexts'])
        records.append(dict(game=game, pair=pair, mid=mid, feature=item['feature'], changedPixels=len(changed),
                            compositionPixelHash=row['compositionPixelHash']))
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, default=ROOT)
    parser.add_argument('--guard', type=Path, default=GUARD)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    review = ReverseReview('gen2-rse-field-states', GAMES)
    review.out = args.output
    records = emit(review, args.baseline, args.guard)
    review.write(args.output/'candidate.lua')
    validation = review.validate()
    (args.output/'report.json').write_text(json.dumps(dict(rows=records, validation=validation), indent=2) + '\n')
    print(json.dumps(dict(rows=len(records), validation=validation)))


if __name__ == '__main__':
    main()
