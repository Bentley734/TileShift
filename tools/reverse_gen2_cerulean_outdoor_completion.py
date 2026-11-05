"""Finish the Crystal outdoor tiles shared by Cerulean and its five routes."""
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
from gb_theme_animation import specification
from reverse_gen2_hoenn_city_complete import Review as City
from reverse_gen2_kanto_final import Final, ROOT
from reverse_gen2_kanto_finish import PARK_TREE_BOUNDS
from reverse_gen2_mt_ember_completion import geometry_frame_proof, masked_parts
from reverse_kanto_review import exterior, runs

GUARD = Path(__file__).with_name('reverse_gen2_cerulean_outdoor_guards.json')
TARGET = 'mappings/reverse_gen2_cerulean_outdoor_completion.lua'
OUTPUT = ROOT.parent / '.work/tileshift-v0360-cerulean-outdoors-completion'
PAIRS = {'firered': 'general__rom_082d4af4', 'leafgreen': 'general__rom_082d4ad4'}
SAND = set(range(86, 93))
ROCK = {20, 25, 26, 27, 28, 29, 30}
LEAF = {1, 2, 3, 4, 5, 6}
WATER = {65, 66, 67, 68, 69, 70, 71, 97, 98, 99, 100, 101, 102, 103}
GOLD = ((255, 255, 181), (197, 148, 58), (140, 107, 49), (58, 58, 58))
GROUPS = {
    'field': (194, 205, 207),
    'sandy_path': (208, 209, 210, 211, 216, 218, 226, 254, 255, 258, 259, 260, 261, 262, 263),
    'jump_and_cliff_edges': (111, 133, 134, 141, 142, 143, 150, 151, 158, 161, 168, 184, 185, 193, 200, 307, 497, 498, 499, 500, 527, 535, 770, 773),
    'boulder': (159,),
    'tree_and_cliff': (180, 181, 250, 251),
    'wooden_fence': (214, 215, 223, 236, 237, 238, 239, 246, 247, 252, 253, 309, 310, 645, 646, 648, 649, 743),
    'river_and_banks': (266, 267, 289, 290, 292, 296),
    'low_hedge': (317, 318, 319, 326, 333, 343),
    'brick_patio': (354, 355, 356, 362, 364, 370, 371, 372),
    'outdoor_sign': (361, 762),
    'gate_approach': (376, 377, 378, 408, 409, 410),
    'center_roof_backdrop': (379, 380, 381, 382, 383, 640, 641, 642, 643, 644),
    'house_roof_backdrop': (657, 665, 672, 673, 674, 675, 676, 677, 678, 679, 683, 684, 685, 686, 687, 691, 692, 693, 699),
    'nugget_bridge': (709, 710, 711, 717, 718, 719, 725, 726, 727, 733, 734, 735, 741, 742, 749, 750, 751),
    'cerulean_bicycle': (744, 745),
}
FEATURE_BY_MID = {mid: name for name, mids in GROUPS.items() for mid in mids}
assert len(FEATURE_BY_MID) == sum(map(len, GROUPS.values()))


def mask_bytes(values, selected, under=False):
    return ''.join('1' if value in selected and (value or under) else '0' for value in values)


def mapped_parts(ref, values, selected):
    return masked_parts(ref, mask_bytes(values, selected, under=True))


def source_indices(review, game, pair, mid, record):
    ref = dict(game=game, tileset=pair, id=mid, hash=record['pixel_sha256'])
    preview.native_donor(review.cache, ref, review.packed)
    mids, palette, planes = review.packed[game, pair]
    at = mids.index(mid) * 256
    return palette, {name: data[at:at + 256] for name, data in planes.items()}


class Artwork:
    def __init__(self, review):
        self.review = review
        self.field = review.gb_ref('crystal', 'PALLET_TOWN', 1, 0)
        self.sand = review.gb_ref('crystal', 'CIANWOOD_CITY', 1, 0)
        self.ledge = review.gb_ref('crystal', 'ROUTE_1', 26, 2)
        self.rock = review.gb_ref('crystal', 'UNION_CAVE_1F', 6, 3)
        self.plateau = review.gb_ref('crystal', 'UNION_CAVE_1F', 4, 3)
        self.water = review.gb_ref('crystal', 'UNION_CAVE_1F', 15, 0)
        self.program = specification(review.cache, self.water, 'program')
        assert self.program
        self.plank = review.gb_at('crystal', 'FAST_SHIP_1F', 16, 6)
        self.steps = review.gb_ref('crystal', 'UNION_CAVE_1F', 18, 3)
        self.wood = review.gb_ref('crystal', 'PALLET_TOWN', 119, 2)
        self.rail = review.gb_at('crystal', 'ROUTE_38', 14, 9)
        self.leaf = review.gb_at('crystal', 'NATIONAL_PARK', 6, 48)
        self.brick = review.gb_at('crystal', 'ROUTE_25', 46, 6)
        self.trees = {q: self.park_tree(q) for q in range(4)}
        self.boulder = review.gb_ref('crystal', 'UNION_CAVE_1F', 24, 0)
        self.architecture = self.buildings()
        self.bicycles = self.bicycle_parts()
        self.source_banks = {}

    def native(self, ref):
        return dict(self.review.native(ref, ''), overMask='0' * 256)

    def composition(self, base, parts, priority=None):
        if not parts:
            return self.native(base)
        assert len(parts) <= 32, ('Too many native pieces', len(parts))
        return dict(self.review.composite(base, parts, ''), overMask=priority or '0' * 256)

    def park_tree(self, quadrant):
        ref = self.review.gb_ref('crystal', 'NATIONAL_PARK', 6, quadrant)
        mask = ''.join('1' if left <= x + quadrant % 2 * 16 <= right else '0'
                       for left, right in PARK_TREE_BOUNDS[quadrant // 2 * 16:quadrant // 2 * 16 + 16]
                       for x in range(16))
        return self.composition(self.field, masked_parts(ref, mask), mask)

    def native_tile(self, name, x, y, priority=False):
        ref = self.review.gb_at('crystal', name, x, y)
        art = self.native(ref)
        if priority:
            image = self.review.gb_image(ref)
            outside = exterior(image, set(self.review.gb_image(self.field).get_flattened_data()))
            art['overMask'] = ''.join('0' if (x, y) in outside else '1' for y in range(16) for x in range(16))
        return art

    def roof_band(self, name, x, y):
        ref = self.review.gb_at('crystal', name, x, y)
        source = self.native_tile(name, x, y, True)
        return self.composition(None, [dict(donor=ref, srcX=0, srcY=8, x=0, y=dy, w=16, h=8) for dy in (0, 8)],
                                source['overMask'][128:] * 2)

    def compact_wall(self, upper, lower, window):
        parts = []
        for source, first, dy in ((upper, 8 if window else 0, 0), (lower, 8, 8)):
            for part in source['parts']:
                top = max(first, part['y'])
                bottom = min(first + 8, part['y'] + part['h'])
                if top < bottom:
                    parts.append(dict(part, srcY=part.get('srcY', 0) + top - part['y'], y=dy + top - first, h=bottom - top))
        return self.composition(self.field, parts)

    def buildings(self):
        out = {}

        def bind(feature, matrix, model):
            for y, row in enumerate(matrix):
                for x, mid in enumerate(row):
                    if mid is None:
                        continue
                    art = model[x, y]
                    assert mid not in out or out[mid][1] == art, (feature, mid)
                    out[mid] = feature, art

        review = self.review
        palettes = review.imp.table('crystal', 'palettes')
        maps = review.imp.table('crystal', 'maps')
        blue = preview.palette_set(palettes, maps['CERULEAN_CITY'], 'DAY')[6]
        orange = preview.palette_set(palettes, maps['ROUTE_5'], 'DAY')[6]
        house = City.town_model(review, 7, 2, 2, (4, 5), base=self.field, roof_palette=blue)
        for x in (1, 2, 3):
            house[x, 1] = house[4, 1]
        compact = {(x, y): art for (x, y), art in house.items() if y < 2}
        compact.update({(x, 2): self.compact_wall(house[x, 2], house[x, 3], x in (4, 5)) for x in (0, 1, 3, 4, 5, 6)})
        compact[2, 2] = house[2, 3]
        bind('cerulean_blue_houses', ((680, 681, 681, 681, 681, 681, 682),
             (688, 707, 656, 708, 689, 689, 690), (696, 705, 664, 706, 694, 695, 698)), compact)
        for mid, x in ((701, 4), (702, 4), (703, 5), (704, 4)):
            out[mid] = 'cerulean_blue_houses', compact[x, 2]

        cottage = City.town_model(review, 5, 2, 2, (1, 3), base=self.field, roof_palette=blue)
        bind('bills_complete_cottage', ((712, 713, 714, 715, 716), (720, 721, 722, 723, 724),
             (728, 729, 730, 731, 732), (736, 737, None, 739, 740)), cottage)

        day = City.town_model(review, 5, 3, 2, (1, 3), base=self.field, roof_palette=orange)
        for x in range(5):
            day[x, 0] = self.native(self.field)
        day[2, 3] = self.compact_wall(day[2, 3], day[1, 4], False)
        bind('route_five_day_care', ((752, 753, 754, 753, 755), (760, 761, 761, 761, 763),
             (768, 769, 769, 769, 771), (756, 757, 766, 758, 759), (764, 765, None, 772, 767)), day)

        bike = {}
        for x in range(4):
            sx = 28 + x
            bike[x, 0] = self.native_tile('GOLDENROD_CITY', sx, 26, True)
            bike[x, 1] = self.roof_band('GOLDENROD_CITY', 28 if x == 0 else 31 if x == 3 else 29, 26)
            bike[x, 2] = self.native_tile('GOLDENROD_CITY', 28 if x == 0 else 31 if x == 3 else 29, 27, True)
            bike[x, 3] = self.native_tile('GOLDENROD_CITY', 28 if x == 0 else 31 if x == 3 else 30, 28)
            bike[x, 4] = self.native_tile('GOLDENROD_CITY', 28 if x == 0 else 31 if x == 3 else 29, 29)
            bike[x, 5] = self.native(self.sand)
        bind('complete_bicycle_shop_front', ((650, 651, 647, 652), (658, 659, 659, 660),
             (666, 667, 667, 668), (653, 654, 654, 655), (661, 662, 662, 663), (669, None, None, 671)), bike)

        gate = {}
        for x in range(6):
            sx = 16 if x == 0 else 21 if x == 5 else 17
            gate[x, 0] = self.native_tile('SAFFRON_CITY', sx, 0, True)
            gate[x, 1] = self.roof_band('SAFFRON_CITY', sx, 0)
            gate[x, 2] = self.native_tile('SAFFRON_CITY', sx, 1, True)
            gate[x, 3] = self.native_tile('SAFFRON_CITY', sx, 2)
            gate[x, 4] = self.native_tile('SAFFRON_CITY', sx if x in (0, 5) else 18, 2)
            gate[x, 5] = self.native_tile('SAFFRON_CITY', 16 if x == 0 else 21 if x == 5 else 18 if x in (2, 3) else 17, 3)
        bind('complete_saffron_north_gate', ((68, 69, 69, 69, 69, 70), (76, 77, 77, 77, 77, 78),
             (387, 388, 388, 388, 388, 389), (438, 437, 437, 437, 437, 439),
             (92, 392, 393, 393, 394, 94), (100, 400, 401, 401, 402, 102)), gate)
        passage = {(x, 0): self.native_tile('SAFFRON_CITY', 16 if x == 0 else 21 if x == 3 else 17, 1, True)
                   for x in range(4)}
        passage[1, 1] = self.native_tile('ROUTE_5', 17, 15)
        passage[2, 1] = self.native_tile('ROUTE_5', 18, 15)
        bind('complete_underground_path_entrance', ((84, 103, 85, 86), (None, 61, 101, None)), passage)
        return out

    def bicycle_parts(self):
        review = self.review
        donor = [review.gb_at('red', 'BIKE_SHOP', x, 1) for x in (0, 1)]
        whole = Image.new('RGBA', (32, 16))
        for x, ref in enumerate(donor):
            whole.paste(review.gb_image(ref), (x * 16, 0))
        # The complete 24-pixel bicycle ends before the checkerboard shop floor.
        assert all(whole.getpixel((x, y))[0] in (0, 85, 170, 255) for x in range(24) for y in range(16))
        parts = {0: [], 1: []}
        for source in (0, 1):
            for target in (0, 1):
                mask = [((x + source * 16) < 24 and (x + source * 16 + 4) // 16 == target
                         and whole.getpixel((x + source * 16, y))[0] < 255)
                        for y in range(16) for x in range(16)]
                for run in runs(mask):
                    parts[target].append(dict(run, donor=donor[source], donorStyle='gen1', srcX=run['x'], srcY=run['y'],
                                              x=run['x'] + source * 16 + 4 - target * 16))
        for target in (0, 1):
            actual = review.render(self.composition(None, parts[target])).get_flattened_data()
            expected = []
            for y in range(16):
                for x in range(16):
                    sx = target * 16 + x - 4
                    pixel = whole.getpixel((sx, y)) if 0 <= sx < 24 else (0, 0, 0, 0)
                    expected.append(pixel if pixel[0] < 255 else (0, 0, 0, 0))
            assert list(actual) == expected, 'Complete native Cerulean bicycle changed'
        return parts

    def water_geometry(self, game, pair, mid, palette, planes, role):
        directory = self.review.cache / game / 'data/generated/gba/native' / pair
        if game not in self.source_banks:
            manifest = catalog.read_lua(directory / 'anim_manifest.lua')
            bank = manifest['water']
            raw = (directory / 'anim_water.rgba').read_bytes()
            size = bank['frames'] * len(bank['mids']) * 1024
            if len(raw) != size:
                raw = zlib.decompress(raw)
            assert len(raw) == size and bank['frames'] == 8
            self.source_banks[game] = bank, catalog.sha(raw)
        bank, digest = self.source_banks[game]
        assert bank['mids'].count(mid) == 1
        animation = dict(mode='water_mask', bank='water', hash=digest)
        _, changed, duplicate = source_under_frames(self.review.cache, game, pair, mid, self.review.packed, animation)
        masks = {name: mask_bytes(values, WATER, under=name == 'under') for name, values in planes.items() if name != 'over'}
        assert all(masks['under'][i] == '1' for i in changed)
        assert all(masks['mid'][i] == '1' for i in duplicate)
        if mid in (266, 267):
            # The whole native canopy in the next source row already includes
            # its apex. Only this obsolete portion over open water is removed.
            assert set(planes['under']) <= WATER and set(planes['mid']) <= WATER
            return dict(self.native(self.water), animated=True, animation=self.program, animationCategory='water')
        ranks = {26: 0, 27: 1, 28: 2, 29: 2, 30: 3, 31: 3}
        mapping = {palette[i]: GOLD[ranks.get(i, 0)] for i in WATER | ranks.keys()}
        return classic_art(self.review, game, pair, mid, 'joined_cerulean_rock_river_bank', GOLD, mapping, role,
                           ground=dict(donor=self.water, masks=masks, animation=self.program),
                           source_animation=animation)

    def terrain(self, mid, values):
        if mid in (143, 151, 184, 185):
            return self.native(self.ledge)
        if mid == 773:
            return self.native(self.plateau)
        if mid in (133, 134):
            donor = self.review.gb_ref('crystal', 'ROUTE_38', 108 if mid == 133 else 110, 0 if mid == 133 else 1)
        elif mid in (497, 498, 499, 500, 527, 535):
            donor = self.plateau
        else:
            donor = self.rock
        rock = mapped_parts(donor, values, ROCK)
        return self.composition(self.field, mapped_parts(self.sand, values, SAND) + rock)

    def fence(self, mid, values):
        parts = mapped_parts(self.rock, values, ROCK)
        if mid in (214, 215, 223, 236, 237, 252, 253, 309, 310, 683, 684, 685, 699, 743):
            return self.composition(self.field, parts + self.fence_parts(0, 8))
        column = 8 if mid in (238, 246, 645, 648) else 0
        if mid in (238, 239, 246, 247, 645, 646, 648, 649):
            return self.composition(self.field, parts + [self.rail_part(column + 2)])
        return self.composition(self.field, parts + self.fence_parts(column))

    def fence_parts(self, *columns):
        return [dict(donor=self.wood, srcX=0, srcY=0, w=8, h=16, x=x, y=0) for x in columns]

    def rail_part(self, x):
        return dict(donor=self.rail, srcX=1, srcY=0, w=5, h=16, x=x, y=0)

    def bridge(self, mid, values):
        if mid in (718, 741, 742):
            return self.native(self.plank)
        if mid in (710, 726, 733, 734, 749):
            return self.native(self.steps)
        parts = mapped_parts(self.rock, values, ROCK)
        deck = set(range(81, 93)) | {33, 34, 35, 36, 37, 38, 39}
        parts += mapped_parts(self.plank, values, deck)
        parts.append(self.rail_part(9 if mid in (709, 717, 725, 750) else 2))
        return self.composition(self.field, parts)

    def recipe(self, game, pair, mid, palette, planes):
        if mid in self.architecture:
            feature, art = self.architecture[mid]
            return feature, copy.deepcopy(art)
        feature = FEATURE_BY_MID[mid]
        under = planes['under']
        visible = bytes(over or middle or base for over, middle, base in zip(planes['over'], planes['mid'], under))
        if feature == 'river_and_banks':
            art = self.water_geometry(game, pair, mid, palette, planes, 'reverse_gen2_cerulean_' + feature)
        elif feature == 'field':
            art = self.native(self.field)
        elif feature in ('sandy_path', 'gate_approach'):
            art = self.composition(self.field, mapped_parts(self.sand, under, SAND))
        elif feature == 'jump_and_cliff_edges':
            art = self.terrain(mid, visible)
        elif feature == 'boulder':
            left = (6, 4, 3, 2, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 2)
            right = (11, 12, 13, 14, 15, 15, 16, 16, 16, 16, 16, 16, 16, 16, 15, 13)
            shape = ''.join('1' if left[y] <= x < right[y] else '0' for y in range(16) for x in range(16))
            art = self.composition(self.field, masked_parts(self.boulder, shape))
        elif feature == 'tree_and_cliff':
            if mid in (180, 181):
                art = self.native(self.rock)
            else:
                tree = self.trees[mid - 250]
                art = self.composition(self.field, mapped_parts(self.rock, under, ROCK) + tree['parts'], tree['overMask'])
        elif feature == 'wooden_fence':
            art = self.fence(mid, under)
        elif feature == 'low_hedge':
            parts = mapped_parts(self.leaf, visible, LEAF)
            art = self.composition(self.field, parts, mask_bytes(planes['over'], LEAF))
        elif feature == 'brick_patio':
            art = self.composition(self.field, mapped_parts(self.brick, under, SAND))
        elif feature == 'outdoor_sign':
            if mid == 762:
                art = copy.deepcopy(self.trees[3])
            else:
                ref = self.review.gb_at('crystal', 'PALLET_TOWN', 3, 5)
                donor = self.review.gb_image(ref)
                outside = exterior(donor, set(self.review.gb_image(self.field).get_flattened_data()))
                shape = ''.join('0' if (x, y) in outside else '1' for y in range(16) for x in range(16))
                art = self.composition(self.field, masked_parts(ref, shape))
        elif feature == 'center_roof_backdrop':
            art = self.native(self.rock if mid >= 640 else self.field)
        elif feature == 'house_roof_backdrop':
            if mid in (675, 676, 677, 678):
                art = copy.deepcopy(self.trees[2 + (mid - 675) % 2])
            elif mid in (657, 683, 684, 685, 699):
                art = self.fence(mid, under)
            else:
                art = self.composition(self.field, mapped_parts(self.sand, under, SAND))
        elif feature == 'nugget_bridge':
            art = self.bridge(mid, visible)
        else:
            assert feature == 'cerulean_bicycle'
            base = mapped_parts(self.sand, under, SAND)
            art = self.composition(self.field, base + self.bicycles[mid - 744])
        return feature, art


def emit(review, guard=GUARD):
    contract = json.loads(guard.read_text())
    companion = preview.read_reviewed(ROOT / 'mappings/reverse_gen2_kanto_final.lua')
    prior = review.current | {(r['game'], r['style'], r['tileset'], r['id'], r.get('map')): r for r in companion}
    for join in contract['joins']:
        spec, layout = review.layouts[join['game'], join['map']]
        w = layout['width']
        x, y = join['x'], join['y']
        assert spec['pair'] == PAIRS[join['game']]
        assert [layout['mids'][(y + i) * w + x:(y + i) * w + x + len(row)]
                for i, row in enumerate(join['matrix'])] == join['matrix'], join
    artwork = Artwork(review)
    records = []
    for item in contract['rows']:
        game, pair, mid = (item[k] for k in ('game', 'pair', 'mid'))
        assert PAIRS[game] == pair
        source = review.imp.cell_index(game)[pair, mid]
        assert source['pixel_sha256'] == item['sourceHash'] and source['layer_sha256'] == item['sourceLayers']
        assert source['behavior'] == item['sourceBehavior']
        assert (game, 'gen2', pair, mid, None) not in prior
        count = sum(entry['count'] for entry in review.usage[game, pair, mid])
        assert count == item['occurrences'] > 0
        palette, planes = source_indices(review, game, pair, mid, source)
        feature, art = artwork.recipe(game, pair, mid, palette, planes)
        art['role'] = f'reverse_gen2_cerulean_{feature}_{mid}'
        if art['kind'] == 'classic_native_geometry':
            evidence = 'Native Crystal animated water meets the exact original rocky bank silhouette in four reviewed Crystal shades.'
        elif feature == 'cerulean_bicycle':
            evidence = 'The complete original Red Cerulean Bike Shop bicycle retains native pixel size and exact frame and wheel pixels.'
        else:
            evidence = 'The reviewed joined Cerulean feature uses complete original Crystal native pixel modules.'
        row = review.row(game, pair, mid, 'gen2', art, evidence +
                         ' The guarded source footprint and original layout, movement, collision, warps and actors are preserved.')
        row['ceruleanOutdoorReview'] = dict(feature=feature, pixelScale=1)
        proof = dict(game=game, pair=pair, mid=mid, sourceHash=row['sourceHash'], sourceBehavior=row['sourceBehavior'],
                     compositionPixelHash=row['compositionPixelHash'], occurrences=count, feature=feature)
        if feature == 'river_and_banks':
            if row['kind'] == 'classic_native_geometry':
                frames = preview.classic_geometry_frames(review.cache, row, review.packed)
                geometry_frame_proof(review, row, frames)
            else:
                frames = preview.replacement_frames(review.cache, row, review.packed, ROOT)
                assert len({frame.tobytes() for frame in frames}) > 1
            proof['frames'] = [catalog.sha(frame.tobytes()) for frame in frames]
        records.append(proof)
    active = prior | review.rows
    total = 0
    for scene in contract['scenes']:
        game, name, pair = (scene[k] for k in ('game', 'map', 'pair'))
        _, layout = review.layouts[game, name]
        assert len(layout['mids']) == scene['cells']
        count = sum((game, 'gen2', pair, mid, name) in active or (game, 'gen2', pair, mid, None) in active for mid in layout['mids'])
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
    report = dict(rows=len(records), new_cells=sum(r['occurrences'] for r in records),
                  all_body_cells=total, checked_frame_pixels=sum(256 * len(r.get('frames', [])) for r in records),
                  validation=review.validate())
    (args.output / 'new-keys.json').write_text(json.dumps(records, indent=2) + '\n')
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
