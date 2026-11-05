"""Finish the native Crystal Cinnabar coast and Pallet approach tiles."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import catalog
import preview
from classic_geometry_review import source_under_frames
from reverse_gen2_cerulean_outdoor_completion import GOLD, ROCK, SAND, WATER, mapped_parts, source_indices
from reverse_gen2_four_five_outdoor_completion import IslandArtwork
from reverse_gen2_hoenn_city_complete import Review as City
from reverse_gen2_kanto_final import Final, ROOT
from reverse_gen2_mt_ember_completion import geometry_frame_proof
from reverse_kanto_review import exterior, runs

GUARD = Path(__file__).with_name('reverse_gen2_cinnabar_pallet_guards.json')
TARGET = 'mappings/reverse_gen2_cinnabar_pallet_completion.lua'
OUTPUT = ROOT.parent / '.work/tileshift-v0390-cinnabar-pallet'
PAIRS = {'firered': {'general__rom_082d4b6c', 'pallet_outdoor'},
         'leafgreen': {'general__rom_082d4b4c', 'pallet_outdoor'}}
MANSION = ((648, 649, 649, 649, 649, 649, 650), (656, 655, 657, 655, 657, 655, 658),
           (664, 663, 665, 663, 665, 663, 666), (667, 668, 669, 651, 652, 653, 654),
           (675, 676, 677, 659, 660, 661, 662))
LAB = ((672, 701, 702, 683, 673, 674, 684), (680, 681, 682, 691, 681, 682, 692),
       (688, 689, 690, 699, 689, 690, 700), (696, 697, 698, 685, 686, 687, 693))
PATHS = {208, 209, 210, 216, 218, 224, 226, 254, 255, 263, 640}


class CoastalArtwork:
    def __init__(self, review):
        self.review = review
        self.island = IslandArtwork(review)
        self.native = self.island.native
        self.buildings = self.facades()

    def facades(self):
        review, native = self.review, self.native
        result = {}

        def bind(feature, matrix, model):
            for y, row in enumerate(matrix):
                for x, mid in enumerate(row):
                    art = model[x, y]
                    assert mid not in result or result[mid][1] == art, (feature, mid, x, y)
                    result[mid] = feature, art

        palettes = review.imp.table('crystal', 'palettes')
        maps = review.imp.table('crystal', 'maps')
        tint = preview.palette_set(palettes, maps['ECRUTEAK_CITY'], 'DAY')[6]
        mansion = City.town_model(review, 7, 3, 3, (1, 2, 4, 5), base=native.field, roof_palette=tint)
        bind('connected_pokemon_mansion', MANSION, mansion)
        for mid in (670, 678):
            result[mid] = 'mansion_door_landing', native.native(native.field)
        result[671] = 'mansion_south_stone_steps', native.native(native.steps)

        lab = City.town_model(review, 7, 2, 3, (1, 2, 4, 5), modern=True, base=native.field)
        sign = review.gb_at('crystal', 'PALLET_TOWN', 3, 5)
        pixels = review.gb_image(sign)
        outside = exterior(pixels, set(review.gb_image(native.field).get_flattened_data()))
        # Keep the complete native sign centered over the two original sign
        # anchors. Its full native frame is split only at the shared tile seam.
        for side, col in enumerate((4, 5)):
            mask = [(x, y) not in outside and x // 8 == side for y in range(16) for x in range(16)]
            sign_parts = [dict(part, donor=sign, srcX=part['x'], srcY=part['y'], x=part['x'] + 8 - side * 16)
                          for part in runs(mask)]
            assert sign_parts
            lab[col, 3] = native.composition(native.field, lab[col, 3]['parts'] + sign_parts)
        bind('complete_cinnabar_research_lab', LAB, lab)
        for mid in (694, 695):
            result[mid] = 'matching_field_under_complete_lab_sign', native.native(native.field)
        return result

    def surf(self, game, pair, mid, planes):
        native = self.native
        water = native.water
        spray = copy.deepcopy(water)
        spray['palettes'] = [[[222, 255, 222], [181, 197, 255], [140, 165, 255], [82, 107, 206]] for _ in range(8)]
        name, _, digest = self.island.phases(game, pair, mid)
        assert name == 'water'
        _, changed, overlap = source_under_frames(self.review.cache, game, pair, mid, self.review.packed,
                                                   dict(mode='water_mask', bank=name, hash=digest))
        spray_colors = {65, 72, 73, 74, 75}
        assert changed and all(planes['under'][i] in WATER | spray_colors for i in changed)
        assert all(planes['mid'][i] in WATER | spray_colors for i in overlap)
        values = bytes(m or u for m, u in zip(planes['mid'], planes['under']))
        base = dict(donor=water, x=0, y=0, w=16, h=16, animated=True)
        foam = [dict(piece, animated=True) for piece in mapped_parts(spray, values, spray_colors)]
        rock = mapped_parts(native.rock, values, ROCK)
        return dict(native.composition(None, [base, *foam, *rock]), animated=True,
                    animation=native.program, animationCategory='water')

    def pallet_tree_rail(self, mid):
        native = self.native
        left = mid in (683, 698)
        tree = native.trees[0 if left else 1]
        return native.composition(native.field, tree['parts'] + [native.rail_part(10 if left else 1)], tree['overMask'])

    def art(self, item, palette, planes):
        game, pair, mid = (item[q] for q in ('game', 'pair', 'mid'))
        native = self.native
        under = planes['under']
        if 'alias' in item:
            return 'exact_reviewed_counterpart', self.island.alias(item)
        if pair == 'pallet_outdoor':
            if mid in (264, 265):
                return 'rock_bank_and_native_breaking_surf', self.surf(game, pair, mid, planes)
            if mid in (682, 683, 690, 698):
                return 'complete_park_tree_and_route_rail', self.pallet_tree_rail(mid)
            if mid in (192, 193, 200, 201):
                return 'handed_south_jump_ledge', native.terrain(mid, under)
            assert mid in (211, 258, 259, 260, 261)
            return 'matching_native_sand_path', native.composition(native.field, mapped_parts(native.sand, under, SAND))
        if mid in self.buildings:
            feature, art = self.buildings[mid]
            return feature, copy.deepcopy(art)
        if mid in (152, 154, 307, 308, 645, 646, 647):
            rock = mapped_parts(native.rock, under, ROCK)
            sand = mapped_parts(native.sand, under, SAND)
            return 'joined_cliff_and_path_edge', native.composition(native.field, [*sand, *rock])
        if mid in PATHS:
            return 'matching_native_sand_path', native.composition(native.field, mapped_parts(native.sand, under, SAND))
        if mid in (279, 288, 297):
            ranks = {25: 0, 26: 0, 27: 1, 28: 2, 29: 2, 30: 3}
            return 'exact_cinnabar_rock_silhouette', self.island.derivative(game, pair, mid, palette, planes,
                'joined_cinnabar_rocky_shore', GOLD, ranks, wet=True)
        assert mid in (379, 380, 381, 382, 383), (game, pair, mid)
        return 'matching_clinic_roof_backdrop', native.native(native.field)


def emit(review, guard=GUARD):
    contract = json.loads(guard.read_text())
    companion = preview.read_reviewed(ROOT / 'mappings/reverse_gen2_kanto_final.lua')
    prior = review.current | {(r['game'], r['style'], r['tileset'], r['id'], r.get('map')): r for r in companion}
    for game in PAIRS:
        links = review.imp.table(game, 'gba/connections')
        assert dict(dir='north', map='FR_ROUTE_21_SOUTH', offset=0) in links['FR_CINNABAR_ISLAND']
        warps = review.imp.table(game, 'gba/warps')['FR_CINNABAR_ISLAND']
        assert [(w['x'], w['y']) for w in warps if w['destMap'] in ('FR_POKEMON_MANSION_1F', 'FR_CINNABAR_ISLAND_POKEMON_LAB_ENTRANCE')] == [(8, 3), (8, 9)]
    for join in contract['joins']:
        game, name, x, y = (join[q] for q in ('game', 'map', 'x', 'y'))
        spec, layout = review.layouts[game, name]
        w = layout['width']
        assert spec['pair'] in PAIRS[game]
        assert [layout['mids'][(y + i) * w + x:(y + i) * w + x + len(row)]
                for i, row in enumerate(join['matrix'])] == join['matrix'], join
    artwork = CoastalArtwork(review)
    records = []
    for item in contract['rows']:
        game, pair, mid = (item[q] for q in ('game', 'pair', 'mid'))
        assert pair in PAIRS[game] and (game, 'gen2', pair, mid, None) not in prior
        source = review.imp.cell_index(game)[pair, mid]
        assert (source['pixel_sha256'], source['layer_sha256'], source['behavior']) == (
            item['sourceHash'], item['sourceLayers'], item['sourceBehavior'])
        count = sum(place['count'] for place in review.usage[game, pair, mid])
        assert count == item['occurrences'] > 0
        palette, planes = source_indices(review, game, pair, mid, source)
        feature, art = artwork.art(item, palette, planes)
        art['role'] = f'reverse_gen2_cinnabar_pallet_{feature}_{mid}'
        if 'alias' in item:
            evidence = 'The actual native context, source RGBA, all layers, behavior and original animation phases match the reviewed counterpart.'
        elif art['kind'] == 'classic_native_geometry':
            evidence = 'The exact rocky shoreline silhouette retains the original shape in four Crystal shades over native animated water.'
        else:
            evidence = 'The complete Cinnabar and Pallet features use intact original Crystal modules at native size.'
        row = review.row(game, pair, mid, 'gen2', art, evidence +
                         ' The original layouts, connections, collision, movement, entrances and actors are preserved.')
        row['cinnabarPalletReview'] = dict(feature=feature, pixelScale=1)
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
