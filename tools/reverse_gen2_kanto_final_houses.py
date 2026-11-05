"""Finish the Sea Cottage, damaged Cerulean house and Seven Island house."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from PIL import Image

import catalog
import preview
from classic_geometry_review import art as classic_art
from reverse_gen2_cerulean_outdoor_completion import mask_bytes, source_indices
from reverse_gen2_kanto_department import BLUE, STONE, TIMBER
from reverse_gen2_kanto_final import Final, ROOT
from reverse_gen2_mt_ember_completion import masked_parts
from reverse_kanto_review import exterior, runs

OUTPUT = ROOT.parent / '.work/tileshift-v0400-sea-cottage-damaged-seven-house'
TARGET = 'mappings/reverse_gen2_kanto_final_houses.lua'
GUARD = Path(__file__).with_name('reverse_gen2_kanto_final_houses_guards.json')
PAIRS = {
    'firered': {'building__rom_082d4eb4': 'sea_cottage', 'building__rom_082d4fa4': 'damaged_house',
                'building__rom_082d4e24': 'seven_island_house'},
    'leafgreen': {'building__rom_082d4e94': 'sea_cottage', 'building__rom_082d4f84': 'damaged_house',
                  'building__rom_082d4e04': 'seven_island_house'},
}
WOOD = {89, 90, 91, 92}
SEA_WOOD = {154, 155, 156, 157, 158, 159}
RUG = [(58, 58, 58), (74, 74, 255), (123, 132, 255), (247, 230, 214)]
TECH = [(58, 58, 58), (82, 132, 132), (165, 189, 189), (247, 230, 214)]
GREEN = [(58, 58, 58), (66, 132, 90), (132, 197, 132), (214, 247, 214)]
LANDSCAPE = [(58, 58, 58), (49, 115, 82), (115, 173, 230), (247, 230, 214)]
PODS = {646, 647, 649, 650, 651, 654, 655, 657, 658, 659, 661, 662, 663}
SEVEN_CABINET = ((325, 326), (333, 334))
SEA_WALL = {641, 642, 643, 644, 645, 664, 665, 666, 673}
DAMAGE_RUG = {291, 292, 293, 299, 301, 307, 308, 309, 696}
VOID_MAT = {26, 27, 28}


class HouseArtwork:
    def __init__(self, review):
        self.review = review
        self.floor = review.gb_ref('crystal', 'PLAYERS_HOUSE_1F', 3, 0)
        self.wall = review.gb_at('crystal', 'BILLS_HOUSE', 4, 0)
        void_row = review.current['firered', 'gen2', 'building__rom_082d4eb4', 8, None]
        assert void_row['role'] == 'classic_gen2_exact_native_black_canvas'
        self.void = json.loads(json.dumps(void_row['donor'], sort_keys=True))
        self.blue_rug = review.gb_ref('crystal', 'GUIDE_GENTS_HOUSE', 15, 0)
        self.blue_rug['palettes'] = [[[74, 74, 255]] * 4 for _ in range(8)]
        self.native_plants = self.plant_arts()
        self.mat = self.entry_mat()
        self.cabinet = self.object_art('ELMS_LAB', (6, 0), (2, 2), (5, 3), self.floor)
        self.table = self.object_art('GUIDE_GENTS_HOUSE', (3, 3), (2, 2), (4, 6), self.floor)

    def native(self, ref):
        return dict(self.review.native(ref, ''), overMask='0' * 256)

    def composite(self, floor, parts, over='0' * 256):
        assert 0 < len(parts) <= 32
        return dict(self.review.composite(floor, parts, ''), overMask=over)

    def object_art(self, map_name, origin, dimensions, floor_cell, base):
        width, height = dimensions
        coords = [(x, y) for y in range(height) for x in range(width)]
        refs = {(x, y): self.review.gb_at('crystal', map_name, origin[0] + x, origin[1] + y) for x, y in coords}
        whole = Image.new('RGBA', (16 * width, 16 * height))
        for (x, y), ref in refs.items():
            whole.paste(self.review.gb_image(ref), (16 * x, 16 * y))
        donor_floor = self.review.gb_at('crystal', map_name, *floor_cell)
        outside = exterior(whole, set(self.review.gb_image(donor_floor).get_flattened_data()))
        result = []
        for (x, y), ref in refs.items():
            mask = ''.join('0' if (16 * x + dx, 16 * y + dy) in outside else '1' for dy in range(16) for dx in range(16))
            art = self.composite(base, masked_parts(ref, mask))
            actual = self.review.render(art)
            expected = self.review.gb_image(ref)
            assert all(actual.getpixel((i % 16, i // 16)) == expected.getpixel((i % 16, i // 16))
                       for i, value in enumerate(mask) if value == '1')
            result.append(art)
        return result

    def plant_arts(self):
        path = ROOT / 'mappings/reverse_gen2_kanto_house_completion.lua'
        rows = [row for row in preview.read_reviewed(path) if row['tileset'] == 'house' and row['style'] == 'gen2'
                and row['game'] == 'firered' and row['id'] in (71, 79)]
        assert len(rows) == 2 and all('potted_tree' in row['role'] for row in rows)
        plants = {}
        for row in rows:
            art = json.loads(json.dumps(self.review.art_of(row), sort_keys=True))
            art['base'] = self.floor
            plants[row['id']] = art
        return plants

    def entry_mat(self):
        result = {i: [] for i in range(3)}
        source = [self.review.gb_at('crystal', 'PLAYERS_HOUSE_1F', 6 + col, 7) for col in range(2)]
        whole = Image.new('RGBA', (32, 16))
        for x, ref in enumerate(source):
            whole.paste(self.review.gb_image(ref), (x * 16, 0))
        outside = exterior(whole, set(self.review.gb_image(self.floor).get_flattened_data()))
        for donor_col, ref in enumerate(source):
            for target_col in range(3):
                mask = [(donor_col * 16 + x, y) not in outside and (donor_col * 16 + x + 8) // 16 == target_col
                        for y in range(16) for x in range(16)]
                for span in runs(mask):
                    result[target_col].append(dict(span, donor=ref, srcX=span['x'], srcY=span['y'],
                                                   x=span['x'] + 16 * donor_col + 8 - 16 * target_col))
        return [self.composite(self.floor, parts) for parts in result.values()]

    def derivative(self, game, pair, mid, palette, planes, feature, colors, base=None, exterior_indices=(), ranks=None):
        ranks = ranks or {}
        used = {i for layer, values in planes.items() for i in values if i or layer == 'under'}
        rgb = {}
        for i in sorted(used):
            r, g, b = palette[i]
            brightness = (54 * r + 183 * g + 19 * b) / 256
            rgb[r, g, b] = colors[ranks.get(i, sum(brightness >= limit for limit in (83, 145, 207)))]
        masks = {name: mask_bytes(values, exterior_indices, under=name == 'under') for name, values in planes.items()}
        ground = dict(donor=base, masks=masks) if base and any('1' in mask for mask in masks.values()) else None
        return classic_art(self.review, game, pair, mid, feature, colors, rgb, ground=ground)

    def art(self, item, palette, planes):
        game, pair, mid = (item[k] for k in ('game', 'pair', 'mid'))
        scope = PAIRS[game][pair]
        if mid in VOID_MAT:
            return 'black_beyond_complete_entry_rug', self.native(self.void)
        if mid in (342, 350, 667, 675) and (scope != 'damaged_house' or mid < 640):
            return 'whole_native_potted_tree', copy.deepcopy(self.native_plants[71 if mid in (342, 667) else 79])
        mat = (669, 670, 671) if scope == 'sea_cottage' else (319, 327, 335)
        if mid in mat:
            return 'whole_native_entry_rug', copy.deepcopy(self.mat[mat.index(mid)])
        if scope == 'sea_cottage':
            return self.cottage(game, pair, mid, palette, planes)
        if scope == 'seven_island_house':
            return self.seven(game, pair, mid, palette, planes)
        return self.damaged(game, pair, mid, palette, planes)

    def cottage(self, game, pair, mid, palette, planes):
        if mid in SEA_WALL:
            return 'native_sea_cottage_wall', self.native(self.wall)
        if mid in (648, 656):
            return 'native_sea_cottage_wood_floor', self.native(self.floor)
        if mid in PODS:
            top = mid in (646, 647, 649, 650, 651)
            return 'complete_bill_transporter_pod', self.derivative(game, pair, mid, palette, planes,
                'complete_bill_transporter_pod', TECH, self.wall if top else self.floor,
                {147, 148, 149, 150, 151} if top else SEA_WOOD)
        if mid == 692:
            return 'whole_bill_transporter_conduit', self.derivative(game, pair, mid, palette, planes,
                'whole_bill_transporter_conduit', GREEN, self.floor, SEA_WOOD)
        if mid in (672, 680, 674):
            top = mid != 680
            return 'complete_sea_cottage_wall_console', self.derivative(game, pair, mid, palette, planes,
                'complete_sea_cottage_wall_console', TECH, self.wall if top else self.floor,
                {147, 148, 149, 150, 151} if top else SEA_WOOD)
        if mid in (652, 653, 668, 676, 679, 687, 688, 691):
            return 'whole_sea_cottage_lab_supplies', self.derivative(game, pair, mid, palette, planes,
                'whole_sea_cottage_lab_supplies', BLUE, self.floor, SEA_WOOD)
        if mid in (677, 678, 685, 686):
            return 'whole_bill_transporter_pc', self.derivative(game, pair, mid, palette, planes,
                'whole_bill_transporter_pc', TECH, self.floor, SEA_WOOD)
        assert mid in (681, 682, 683, 684), mid
        return 'complete_sea_cottage_floor_documents', self.derivative(game, pair, mid, palette, planes,
            'complete_sea_cottage_floor_documents', TIMBER, self.floor, SEA_WOOD)

    def seven(self, game, pair, mid, palette, planes):
        if mid in (317, 318, 264, 272, 336, 337):
            return 'native_seven_island_house_wall', self.native(self.wall)
        shelves = tuple(mid for row in SEVEN_CABINET for mid in row)
        if mid in shelves:
            return 'complete_native_seven_island_cabinet', copy.deepcopy(self.cabinet[shelves.index(mid)])
        table = (357, 358, 365, 366)
        if mid in table:
            return 'whole_native_seven_island_table', copy.deepcopy(self.table[table.index(mid)])
        if mid in (359, 367):
            ref = self.review.gb_at('crystal', 'PLAYERS_HOUSE_1F', 7 if mid == 359 else 4, 3)
            return 'complete_native_seven_island_stool', self.native(ref)
        if mid in (379, 380, 381):
            return 'complete_seven_island_rear_door_frame', self.derivative(game, pair, mid, palette, planes,
                'complete_seven_island_rear_door_frame', STONE, self.wall, {82, 83, 84, 85, 86})
        if mid in (385, 386):
            return 'whole_seven_island_door_blocking_crates', self.derivative(game, pair, mid, palette, planes,
                'whole_seven_island_door_blocking_crates', TIMBER, self.floor, WOOD | {82})
        assert mid in (344, 345), mid
        return 'whole_seven_island_framed_picture', self.derivative(game, pair, mid, palette, planes,
            'whole_seven_island_framed_picture', LANDSCAPE, self.wall, {82, 83, 84, 85, 86})

    def damaged(self, game, pair, mid, palette, planes):
        if mid in (216, 217, 641, 642, 645, 646, 647):
            return 'complete_damaged_house_wall', self.native(self.wall)
        if mid in (224, 225):
            return 'complete_native_damaged_house_sink', self.native(self.review.gb_at('crystal', 'PLAYERS_HOUSE_1F', mid - 224, 1))
        if mid in (328, 329):
            return 'native_floor_below_complete_sink', self.native(self.floor)
        cabinets = {649: 0, 650: 1, 657: 2, 658: 3, 653: 0, 654: 1, 661: 2, 662: 3}
        if mid in cabinets:
            return 'whole_native_damaged_house_cabinet', copy.deepcopy(self.cabinet[cabinets[mid]])
        if mid in (353, 361):
            return 'whole_damaged_house_wall_picture', self.derivative(game, pair, mid, palette, planes,
                'whole_damaged_house_wall_picture', BLUE, self.wall, {81, 82, 83, 84, 85, 86})
        if mid in (643, 644, 651, 652):
            return 'whole_damaged_house_broken_wall_opening', self.derivative(game, pair, mid, palette, planes,
                'whole_damaged_house_broken_wall_opening', STONE, self.wall, {70, 71, 72}, ranks={65: 0, 81: 0})
        if mid in DAMAGE_RUG:
            return 'whole_damaged_house_blue_rug', self.derivative(game, pair, mid, palette, planes,
                'whole_damaged_house_blue_rug', RUG, self.floor, WOOD, ranks={56: 1, 58: 3})
        table = (296, 297, 688, 305)
        if mid in table:
            art = copy.deepcopy(self.table[table.index(mid)])
            art['base'] = self.blue_rug
            return 'complete_native_table_on_blue_rug', art
        if mid in (666, 667, 674, 675):
            return 'whole_damaged_house_tipped_chairs', self.derivative(game, pair, mid, palette, planes,
                'whole_damaged_house_tipped_chairs', TECH, self.blue_rug, {56})
        if mid in (686, 687):
            return 'whole_damaged_house_tipped_planter', self.derivative(game, pair, mid, palette, planes,
                'whole_damaged_house_tipped_planter', GREEN, self.floor, WOOD)
        if mid in (664, 668, 672, 673, 680, 681, 684, 685):
            return 'complete_damaged_house_floor_tracks', self.derivative(game, pair, mid, palette, planes,
                'complete_damaged_house_floor_tracks', STONE, self.floor, WOOD)
        assert mid in (655, 663, 669, 670, 678), mid
        return 'whole_damaged_house_scattered_fixtures', self.derivative(game, pair, mid, palette, planes,
            'whole_damaged_house_scattered_fixtures', TECH, self.floor, WOOD)


def emit(review, guard=GUARD):
    contract = json.loads(guard.read_text())
    artwork = HouseArtwork(review)
    for scene in contract['scenes']:
        game, name = scene['game'], scene['map']
        spec, layout = review.layouts[game, name]
        assert spec['pair'] == scene['pair'] and layout['file_sha256'] == scene['layoutSHA256']
        assert len(layout['mids']) == scene['cells']
    records = []
    for item in contract['rows']:
        game, pair, mid = (item[q] for q in ('game', 'pair', 'mid'))
        assert (game, 'gen2', pair, mid, None) not in review.current
        source = review.imp.cell_index(game)[pair, mid]
        assert (source['pixel_sha256'], source['layer_sha256'], source['behavior']) == (
            item['sourceHash'], item['sourceLayers'], item['sourceBehavior'])
        assert review.usage[game, pair, mid] == [dict(map=r['map'], count=r['count']) for r in item['locations']]
        for place in item['locations']:
            _, layout = review.layouts[game, place['map']]
            width = layout['width']
            assert [[i % width, i // width] for i, m in enumerate(layout['mids']) if m == mid] == place['coordinates']
        palette, planes = source_indices(review, game, pair, mid, source)
        feature, art = artwork.art(item, palette, planes)
        art['role'] = 'reverse_gen2_final_house_' + feature + '_' + str(mid)
        if art['kind'] == 'classic_native_geometry':
            evidence = 'The complete named fixture retains its original outline and priority in four Crystal colors. '
        else:
            evidence = 'The complete native Crystal furniture or surface retains its original pixel size. '
        row = review.row(game, pair, mid, 'gen2', art, evidence +
                         'Original room layout, collision, furniture positions, entrances, scripts and actors are preserved.')
        row['finalHouseReview'] = dict(feature=feature, pixelScale=1)
        records.append(dict(game=game, pair=pair, mid=mid, occurrences=item['occurrences'], feature=feature,
                            sourceHash=row['sourceHash'], compositionPixelHash=row['compositionPixelHash']))
    active = review.current | review.rows
    total = 0
    for scene in contract['scenes']:
        game, name, pair = (scene[q] for q in ('game', 'map', 'pair'))
        _, layout = review.layouts[game, name]
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
    report = dict(rows=len(records), new_cells=sum(r['occurrences'] for r in records),
                  all_body_cells=total, validation=review.validate())
    (args.output / 'new-keys.json').write_text(json.dumps(records, indent=2) + '\n')
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
