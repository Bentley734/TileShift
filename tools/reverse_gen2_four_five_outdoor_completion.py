"""Finish native Crystal terrain and landmarks on Four and Five Island."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import zlib

from PIL import Image

import catalog
import preview
from classic_geometry_review import art as classic_art, source_under_frames
from reverse_gen2_cerulean_outdoor_completion import Artwork, GOLD, ROCK, SAND, WATER, mask_bytes, mapped_parts, source_indices
from reverse_gen2_hoenn_city_complete import Review as City
from reverse_gen2_kanto_final import Final, ROOT
from reverse_gen2_mt_ember_completion import geometry_frame_proof, masked_parts
from reverse_kanto_review import exterior, runs

GUARD = Path(__file__).with_name('reverse_gen2_four_five_outdoor_guards.json')
TARGET = 'mappings/reverse_gen2_four_five_outdoor_completion.lua'
OUTPUT = ROOT.parent / '.work/tileshift-v0390-four-five-outdoors'
PAIRS = {'firered': 'general__rom_082d5064', 'leafgreen': 'general__rom_082d5044'}
HOUSES = {
    'day_care': ((672, 673, 674, 675), (680, 681, 682, 683), (688, 689, 690, 691), (696, 697, 698, 699)),
    'rocket_warehouse': ((684, 685, 685, 685, 685, 686), (692, 693, 693, 693, 693, 694),
                         (700, 701, 701, 679, 701, 702), (708, 709, 738, 779, 738, 707)),
    'resort_home': ((784, 785, 785, 785, 786), (787, 788, 789, 790, 791), (781, None, 782, 783, 780)),
}
POND = (416, 417, 418, 419, 424, 425, 426, 432, 433, 434, 435)
PILLAR = (704, 705, 712, 713, 720, 721, 728, 729)
DOCK = (646, 647, 654, 655, 662, 663, 670, 671, 710, 711, 715, 716, 717, 718, 719,
        723, 724, 725, 726, 727, 731, 732, 733, 734, 735, 739, 740, 741, 742, 743, 747, 748, 749,
        750, 751, 755, 756, 757, 758, 759)
DOCK_ROOF = {715, 716, 717, 723, 724, 725, 731, 732, 733}
BLUE_GRAY = ((222, 230, 230), (165, 181, 181), (107, 123, 140), (49, 58, 74))
METAL_ACCENT = ((222, 230, 230), (148, 165, 173), (58, 58, 74), (189, 66, 49))
RED_ROOF = ((255, 206, 156), (230, 123, 90), (181, 66, 49), (90, 41, 33))
MANUAL = {214, 215, 236, 252, 266, 267, 307, 353, 641, 645, 744, 745, 746}


class IslandArtwork:
    def __init__(self, review):
        self.review = review
        self.native = Artwork(review)
        self.field = self.native.field
        self.water = self.native.water
        self.program = self.native.program
        self.rock = self.native.rock
        self.ledge = self.native.ledge
        self.sand = review.gb_ref('crystal', 'PALLET_TOWN', 121, 0)
        self.plank = self.native.plank
        self.houses = self.house_models()
        self.animations = {}
        self.canonicals = {}

    def house_models(self):
        review, native = self.review, self.native
        palettes = review.imp.table('crystal', 'palettes')
        maps = review.imp.table('crystal', 'maps')
        orange = preview.palette_set(palettes, maps['ROUTE_5'], 'DAY')[6]
        gray = preview.palette_set(palettes, maps['BLACKTHORN_CITY'], 'DAY')[6]
        models = {}
        for feature, width, door, windows, tint in (
            ('day_care', 4, 1, (2,), orange),
            ('rocket_warehouse', 6, 3, (), gray),
            ('resort_home', 5, 1, (2, 3), orange),
        ):
            model = City.town_model(review, width, 2, door, windows, base=self.field, roof_palette=tint)
            if feature == 'resort_home':
                for x in range(width):
                    if x != door:
                        model[x, 2] = native.compact_wall(model[x, 2], model[x, 3], x in windows)
            for y, row in enumerate(HOUSES[feature]):
                for x, mid in enumerate(row):
                    if mid is None:
                        continue
                    art = model[x, y]
                    assert mid not in models or models[mid][1] == art, (feature, mid, x, y)
                    models[mid] = feature, art
        return models

    def banks(self, game, pair):
        if (game, pair) not in self.animations:
            folder = self.review.cache / game / 'data/generated/gba/native' / pair
            path = folder / 'anim_manifest.lua'
            manifest = catalog.read_lua(path) if path.is_file() else {}
            programs = {}
            for name in ('water', 'sand'):
                bank = manifest.get(name)
                if not bank or not bank['mids']:
                    continue
                raw = (folder / f'anim_{name}.rgba').read_bytes()
                size = bank['frames'] * len(bank['mids']) * 1024
                if len(raw) != size:
                    raw = zlib.decompress(raw)
                assert len(raw) == size and bank['frames'] == 8
                programs[name] = bank['mids'], raw, catalog.sha(raw)
            self.animations[game, pair] = programs
        return self.animations[game, pair]

    def phases(self, game, pair, mid):
        hits = [(name, mids, raw, digest) for name, (mids, raw, digest) in self.banks(game, pair).items() if mid in mids]
        assert len(hits) <= 1
        if not hits:
            return None, (), None
        name, mids, raw, digest = hits[0]
        assert mids.count(mid) == 1
        slot = mids.index(mid)
        offsets = [(phase * len(mids) + slot) * 1024 for phase in range(8)]
        return name, tuple(catalog.sha(raw[i:i + 1024]) for i in offsets), digest

    def alias(self, item):
        review = self.review
        witness = item['alias']
        module = witness['module']
        if module not in self.canonicals:
            self.canonicals[module] = {(row['game'], row['style'], row['tileset'], row['id']): row
                                       for row in preview.read_reviewed(ROOT / module) if row.get('map') is None}
        game, pair, mid = (witness[k] for k in ('game', 'pair', 'mid'))
        row = self.canonicals[module][game, 'gen2', pair, mid]
        source = review.imp.cell_index(game)[pair, mid]
        assert row['compositionPixelHash'] == witness['compositionPixelHash'] and row['role'] == witness['role']
        assert (source['pixel_sha256'], source['behavior'], source['layer_sha256']) == (
            item['sourceHash'], item['sourceBehavior'], item['sourceLayers'])
        target = self.phases(item['game'], item['pair'], item['mid'])[:2]
        assert target == self.phases(game, pair, mid)[:2]
        assert tuple(item['legacyPhaseHashes']) == target[1]
        assert row['kind'] in ('native', 'native_composite')
        return json.loads(json.dumps(review.art_of(row), sort_keys=True))

    def derivative(self, game, pair, mid, palette, planes, feature, shades, ranks, wet=False, backing=None):
        ground = None
        animation = None
        name, _, digest = self.phases(game, pair, mid)
        if name:
            animation = dict(mode='water_mask' if wet else 'static_equivalent', bank=name, hash=digest)
        if wet:
            masks = {layer: mask_bytes(values, WATER, under=layer == 'under')
                     for layer, values in planes.items() if layer != 'over'}
            ground = dict(donor=self.water, masks=masks, animation=self.program)
            _, changed, overlap = source_under_frames(self.review.cache, game, pair, mid, self.review.packed, animation)
            assert all(masks['under'][i] == '1' for i in changed) and all(masks['mid'][i] == '1' for i in overlap)
        elif backing:
            ref, indices = backing
            masks = {name: mask_bytes(values, indices, under=name == 'under') for name, values in planes.items()}
            ground = dict(donor=ref, masks=masks)
        used = {i for name, values in planes.items() for i in values if i or name == 'under'}
        known = set(ranks)
        if wet:
            known |= WATER
        if backing:
            known |= backing[1]
        assert used <= known, (feature, mid, used - known)
        mapping = {palette[i]: shades[ranks.get(i, 0)] for i in sorted(used)}
        return classic_art(self.review, game, pair, mid, feature, shades, mapping, ground=ground, source_animation=animation)

    def pond(self, values):
        part = dict(donor=self.water, w=16, h=16, x=0, y=0, animated=True)
        rock = mapped_parts(self.rock, values, ROCK | {31})
        return dict(self.native.composition(None, [part, *rock]), animated=True, animation=self.program, animationCategory='water')

    def shore_foam(self, game, pair, mid, planes):
        foam = copy.deepcopy(self.water)
        foam['palettes'] = [[[222, 255, 222], [181, 197, 255], [140, 165, 255], [82, 107, 206]] for _ in range(8)]
        name, _, digest = self.phases(game, pair, mid)
        assert name == 'sand'
        _, changed, duplicate = source_under_frames(self.review.cache, game, pair, mid, self.review.packed,
                                                     dict(mode='water_mask', bank=name, hash=digest))
        assert changed and all(planes['under'][i] in WATER | {72, 74, 75} for i in changed)
        assert all(planes['mid'][i] in WATER | {72, 74, 75} for i in duplicate)
        visible = bytes(m or u for m, u in zip(planes['mid'], planes['under']))
        part = dict(donor=self.water, w=16, h=16, x=0, y=0, animated=True)
        spray = [dict(piece, animated=True) for piece in mapped_parts(foam, visible, {65, 72, 73, 74, 75})]
        return dict(self.native.composition(None, [part, *spray]), animated=True, animation=self.program, animationCategory='water')

    def palm(self, mid):
        source = [self.review.gb_at('crystal', 'NEW_BARK_TOWN', 0, y) for y in range(2)]
        original = Image.new('RGBA', (16, 32))
        for y, ref in enumerate(source):
            original.paste(self.review.gb_image(ref), (0, y * 16))
        outside = exterior(original, set(self.review.gb_image(self.field).get_flattened_data()))
        y = 0 if mid == 27 else 1
        mask = ''.join('0' if (x, yy + y * 16) in outside else '1' for yy in range(16) for x in range(16))
        assert '1' in mask
        return self.native.composition(self.field, masked_parts(source[y], mask), mask if y == 0 else None)

    def art(self, item, palette, planes):
        game, pair, mid = (item[q] for q in ('game', 'pair', 'mid'))
        native = self.native
        under = planes['under']
        visible = bytes(o or m or u for o, m, u in zip(planes['over'], planes['mid'], under))
        if 'alias' in item:
            return 'exact_reviewed_counterpart', self.alias(item)
        if mid in self.houses:
            feature, art = self.houses[mid]
            return feature, copy.deepcopy(art)
        if mid in (27, 35):
            return 'native_narrow_tree', self.palm(mid)
        if mid in (142, 152, 154, 648, 774, 775):
            return 'complete_handed_cliff', native.terrain(mid, visible)
        if mid in (180, 181):
            return 'cliff_behind_whole_park_tree', native.native(self.rock)
        if mid in (205, 207, 353, 744, 745, 746):
            return 'matching_clear_field', native.native(self.field)
        if mid in (211, 259, 260):
            return 'native_sand_field_join', native.composition(self.field, mapped_parts(self.sand, under, SAND))
        if mid in (214, 215, 236, 252, 703, 765, 766, 767):
            return 'complete_native_wooden_fence', native.composition(self.field, native.fence_parts(0, 8))
        if mid in (250, 251, 643, 644, 656, 664, 676, 677, 678, 776):
            tops = {250: 0, 251: 1, 643: 2, 644: 3, 656: 3, 664: 2, 676: 2, 677: 3, 678: 2, 776: 3}
            tree = native.trees[tops[mid]]
            return 'complete_park_tree_section', native.composition(self.field, mapped_parts(self.rock, under, ROCK) + tree['parts'], tree['overMask'])
        if mid in (266, 267):
            name, _, digest = self.phases(game, pair, mid)
            assert name == 'water' and set(under) <= WATER and set(planes['mid']) <= WATER
            source_under_frames(self.review.cache, game, pair, mid, self.review.packed, dict(mode='water_mask', bank=name, hash=digest))
            return 'animated_water_above_complete_canopy', self.pond(under)
        if mid in (279, 289, 290, 292, 297):
            ranks = {25: 0, 26: 0, 27: 1, 28: 2, 29: 2, 30: 3, 31: 3}
            return 'exact_rocky_shore_profile', self.derivative(game, pair, mid, palette, planes, 'sevii_joined_rocky_shore', GOLD, ranks, wet=True)
        if mid in (306, 307, 308, 752, 753, 754, 763, 764, 768, 769, 770, 771, 772, 773):
            values = visible if mid == 773 else under
            return 'native_cliff_and_field_margin', native.composition(self.field, mapped_parts(self.rock, values, ROCK))
        if mid == 361:
            return native.recipe(game, pair, mid, palette, planes)
        if mid in (379, 380, 381, 382, 383, 641, 642, 645):
            return 'matching_roof_backdrop', native.native(self.field)
        if mid in POND:
            return 'connected_small_freshwater_pond', self.pond(visible)
        if mid in (445, 446, 447, 760, 761, 762):
            return 'complete_native_ferry_gangway', native.native(self.plank)
        if mid in (606, 607):
            return 'legacy_shore_foam', self.shore_foam(game, pair, mid, planes)
        if mid in PILLAR or mid in (706, 714):
            ranks = {34: 0, 35: 0, 36: 1, 37: 2, 38: 2, 39: 3}
            field = {12, 13, 14, 94, 95} | SAND
            return 'complete_memorial_pillar_cairn', self.derivative(game, pair, mid, palette, planes,
                'complete_four_level_memorial_pillar_cairn', BLUE_GRAY, ranks, backing=(self.field, field))
        if mid in DOCK:
            if mid in DOCK_ROOF:
                ranks = {37: 3, 39: 3, 42: 0, 43: 1, 44: 2, 45: 2, 46: 3}
                shades = RED_ROOF
            else:
                ranks = {33: 0, 34: 0, 35: 1, 36: 1, 37: 2, 38: 2, 39: 2,
                         42: 0, 43: 3, 44: 3, 45: 3, 46: 2, 49: 0, 50: 0, 51: 1, 52: 1, 53: 2, 55: 2, 61: 1}
                shades = METAL_ACCENT
            wet = any(i in WATER for i in under)
            return 'complete_sevii_ferry_terminal', self.derivative(game, pair, mid, palette, planes,
                'joined_overwater_sevii_ferry_terminal', shades, ranks, wet=wet)
        if mid in (777, 778):
            rock = self.review.gb_at('crystal', 'CERULEAN_CITY', 5, 6)
            donor = self.review.gb_image(rock)
            outside = exterior(donor, set(self.review.gb_image(self.field).get_flattened_data()))
            mask = ''.join('0' if (x, y) in outside else '1' for y in range(16) for x in range(16))
            assert 24 < mask.count('1') < 245
            return 'complete_memorial_round_boulder', native.composition(self.field, masked_parts(rock, mask))
        raise AssertionError(('No Four/Five Island decision', game, pair, mid))


def emit(review, guard=GUARD):
    contract = json.loads(guard.read_text())
    companion = preview.read_reviewed(ROOT / 'mappings/reverse_gen2_kanto_final.lua')
    prior = review.current | {(row['game'], row['style'], row['tileset'], row['id'], row.get('map')): row for row in companion}
    for feature in contract['joins']:
        game, name, x, y = (feature[q] for q in ('game', 'map', 'x', 'y'))
        spec, layout = review.layouts[game, name]
        assert spec['pair'] == PAIRS[game]
        w = layout['width']
        assert [layout['mids'][(y + i) * w + x:(y + i) * w + x + len(row)]
                for i, row in enumerate(feature['matrix'])] == feature['matrix'], feature
    artwork = IslandArtwork(review)
    records = []
    for item in contract['rows']:
        game, pair, mid = (item[q] for q in ('game', 'pair', 'mid'))
        assert pair == PAIRS[game] and (game, 'gen2', pair, mid, None) not in prior
        source = review.imp.cell_index(game)[pair, mid]
        assert (source['pixel_sha256'], source['layer_sha256'], source['behavior']) == (
            item['sourceHash'], item['sourceLayers'], item['sourceBehavior'])
        count = sum(place['count'] for place in review.usage[game, pair, mid])
        assert count == item['occurrences'] > 0
        palette, planes = source_indices(review, game, pair, mid, source)
        feature, art = artwork.art(item, palette, planes)
        art['role'] = f'reverse_gen2_four_five_{feature}_{mid}'
        if 'alias' in item:
            evidence = 'Actual whole-island context, all source layers, behavior and original animation phases match the reviewed native counterpart.'
        elif art['kind'] == 'classic_native_geometry':
            evidence = 'The entire named island landmark or bank keeps its exact original silhouette in reviewed Crystal shades and native terrain.'
        else:
            evidence = 'The complete named Four/Five Island feature uses original native Crystal sections at their native pixel scale.'
        row = review.row(game, pair, mid, 'gen2', art, evidence +
                         ' Original layout, collision, depth, travel, events and actor coordinates are preserved.')
        row['fourFiveIslandReview'] = dict(feature=feature, pixelScale=1)
        proof = dict(game=game, pair=pair, mid=mid, feature=feature, occurrences=count,
                     sourceHash=row['sourceHash'], compositionPixelHash=row['compositionPixelHash'])
        if row.get('classicGeometry', {}).get('ground', {}).get('animation'):
            frames = preview.classic_geometry_frames(review.cache, row, review.packed)
            geometry_frame_proof(review, row, frames)
            proof['frames'] = [catalog.sha(frame.tobytes()) for frame in frames]
        elif row.get('animated'):
            frames = preview.replacement_frames(review.cache, row, review.packed, ROOT)
            assert len({frame.tobytes() for frame in frames}) > 1
            proof['frames'] = [catalog.sha(frame.tobytes()) for frame in frames]
        records.append(proof)
    active = prior | review.rows
    total = 0
    for scene in contract['scenes']:
        game, name, pair = (scene[q] for q in ('game', 'map', 'pair'))
        spec, layout = review.layouts[game, name]
        assert spec['pair'] == pair and len(layout['mids']) == scene['cells']
        count = sum((game, 'gen2', pair, mid, None) in active for mid in layout['mids'])
        assert count == scene['cells'], (name, count, scene['cells'])
        total += count
    return records, total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--guard', type=Path, default=GUARD)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    review = Final()
    review.current = {key: row for key, row in review.current.items() if review.origins[id(row)][0] != TARGET}
    review.out = args.output
    records, total = emit(review, args.guard)
    review.write(args.output / 'candidate.lua')
    report = dict(rows=len(records), new_cells=sum(r['occurrences'] for r in records), all_body_cells=total,
                  alias_rows=sum(r['feature'] == 'exact_reviewed_counterpart' for r in records),
                  checked_frame_pixels=sum(len(r.get('frames', [])) * 256 for r in records), validation=review.validate())
    (args.output / 'new-keys.json').write_text(json.dumps(records, indent=2) + '\n')
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
