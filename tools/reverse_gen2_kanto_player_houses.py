"""Complete the original FireRed and LeafGreen shared home rooms in Crystal art."""
from collections import Counter
from pathlib import Path
import argparse
import copy
import json

import catalog
import preview
from classic_geometry_review import art as geometry_art
from johto_remaining_review import artwork
from reverse_common import ROOT, ReverseReview
from reverse_gen2_hoenn_outdoor_complete import Review as Layouts

PAIR = 'player_house'
GAMES = ('firered', 'leafgreen')
OUTPUT = ROOT.parent / '.work/tileshift-v0360-player-houses'
TARGET = ROOT / 'mappings/reverse_gen2_kanto_player_houses.lua'
GUARDS = Path(__file__).with_name('reverse_gen2_kanto_player_houses_guards.json')

STAIRS = {5, 6, 7, 13, 14, 15, 21, 22, 23, 29, 30, 31, 37, 38, 39,
          218, 219, 220, 226, 227, 234, 235, 236, 242, 243, 244, 250, 251, 252}
WINDOWS = {33, 34, 41, 42, 184, 192, 240, 241, 248, 249, 353, 361}
WALL = {32, 40, 45, 150, 155, 163, 168, 176, 216, 217, 257}
KITCHEN_TOP = {46, 47, 172, 173}
KITCHEN_BASE = {57, 58, 232, 233, 328, 329}
CUPBOARD = {43, 44, 48, 51, 52, 55, 56, 59, 60, 62, 63, 171, 174, 179,
            180, 181, 182, 185, 187, 188, 189, 190, 193, 256, 284, 285}
ELECTRONICS = {53, 61, 166, 170, 175, 186, 282, 368, 369, 376, 377,
               641, 642, 647, 649, 654, 655, 656, 657, 662, 663}
BED = {643, 644, 645, 651, 652, 653, 659, 660, 661}
DOOR_MAT = {18, 19, 20, 26, 27, 28, 223, 231, 239, 319, 327, 335}
FLOOR = {9, 90, 207, 646}
PLANTS = {71: 71, 79: 79, 87: 71, 95: 79, 245: 71, 246: 71, 253: 79, 254: 79,
          341: 71, 342: 71, 349: 79, 350: 79}
TABLES = {
    'gold': {195: 67, 196: 68, 197: 70, 198: 75, 199: 78, 200: 76, 201: 77,
             203: 83, 205: 86, 208: 84, 209: 85, 211: 91, 212: 92, 213: 94},
    'blue': {291: 67, 292: 68, 293: 70, 294: 75, 295: 78, 296: 76, 297: 77,
             299: 83, 301: 86, 304: 84, 305: 85, 307: 91, 308: 92, 309: 94},
}
MATERIALS = {
    'timber': [(58, 58, 58), (132, 107, 25), (173, 140, 58), (214, 197, 140)],
    'metal': [(58, 58, 58), (107, 107, 107), (173, 173, 173), (222, 255, 222)],
    'blue': [(58, 58, 58), (74, 90, 123), (156, 181, 206), (247, 247, 255)],
    'red': [(58, 58, 58), (165, 49, 41), (247, 82, 49), (255, 156, 197)],
    'gold': [(58, 58, 58), (132, 107, 25), (214, 197, 140), (247, 230, 214)],
    'green': [(58, 58, 58), (41, 115, 0), (99, 206, 8), (181, 255, 82)],
}


class Review(Layouts):
    def __init__(self):
        ReverseReview.__init__(self, 'gen2-kanto-player-houses', GAMES)
        self.out = OUTPUT
        self.layouts = {}
        self.layout_hashes = {}
        self.guards = json.loads(GUARDS.read_text(encoding='utf-8'))
        self.wood = self.gb_ref('crystal', 'PLAYERS_HOUSE_1F', 3, 0)
        self.wall = self.gb_at('crystal', 'PLAYERS_HOUSE_1F', 5, 0)
        self.rug = self.gb_ref('crystal', 'GUIDE_GENTS_HOUSE', 15, 0)
        self.void = self.gb_ref('crystal', 'FAST_SHIP_CABINS_SE_SSE_CAPTAINS_CABIN', 12, 0)
        self.references = {}
        for filename in ('reverse_gen2_kanto_finish', 'reverse_gen2_kanto_house_completion',
                         'reverse_gen2_kanto_final'):
            for row in preview.read_reviewed(ROOT / 'mappings' / (filename + '.lua')):
                key = row['game'], row['tileset'], row['id']
                if row['game'] in GAMES and row['style'] == 'gen2' and row['tileset'] in (PAIR, 'house'):
                    self.references[key] = row

    def render(self, row):
        return preview.replacement_image(self.cache, row, self.packed, ROOT)

    def carpet(self, color):
        if color == 'pink':
            return self.rug
        ref = copy.deepcopy(self.rug)
        ref['palettes'] = [[list(rgb) for rgb in reversed(MATERIALS[color])] for _ in range(8)]
        return ref

    def table(self, game, color, mid):
        original = self.references[game, PAIR, TABLES[color][mid]]
        assert original['role'] == 'classic_gen2_complete_house_table_rug_and_stools'
        art = artwork(original)
        for part in art['parts']:
            if part['donor'] == self.rug:
                part['donor'] = self.carpet(color)
        art['overMask'] = original['overMask']
        art['role'] = 'reverse_gen2_house_complete_native_table_and_rug'
        return art

    def source_planes(self, game, mid):
        source = self.imp.cell_index(game)[PAIR, mid]
        preview.native_donor(self.cache, dict(game=game, tileset=PAIR, id=mid, hash=source['pixel_sha256']), self.packed)
        ids, palette, blobs = self.packed[game, PAIR]
        offset = ids.index(mid) * 256
        return {name: catalog.rgba_native(data[offset:offset + 256], palette, name != 'under')
                for name, data in blobs.items()}

    def geometry(self, game, mid, feature, material, backing=None, exterior=()):
        palette = MATERIALS[material]
        masks, colors = {}, {}
        planes = self.source_planes(game, mid)
        for layer, image in planes.items():
            pixels = list(image.get_flattened_data())
            # Only backing colors exposed at the edge are eligible. The same
            # RGB in a cabinet, frame, or rug motif stays opaque.
            if backing:
                edges = {(x, y) for y in range(16) for x in range(16) if x in (0, 15) or y in (0, 15)}
                outside = set()
                while edges:
                    x, y = edges.pop()
                    pixel = pixels[y * 16 + x]
                    if (x, y) in outside or not pixel[3] or pixel[:3] not in exterior:
                        continue
                    outside.add((x, y))
                    edges.update((xx, yy) for xx, yy in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
                                 if 0 <= xx < 16 and 0 <= yy < 16 and (xx, yy) not in outside)
                if outside:
                    masks[layer] = ''.join('1' if (i % 16, i // 16) in outside else '0' for i in range(256))
            for r, g, b, a in pixels:
                if a:
                    light = (54 * r + 183 * g + 19 * b) / 256
                    colors[r, g, b] = palette[sum(light >= bound for bound in (86, 148, 204))]
        ground = dict(donor=backing, masks=masks) if masks else None
        return geometry_art(self, game, PAIR, mid, feature, palette, colors, ground=ground)

    def colors_at(self, game, mids):
        return {p[:3] for mid in mids for p in self.source_planes(game, mid)['under'].get_flattened_data()}

    def recipe(self, game, mid, floor_colors, wall_colors):
        if mid in FLOOR:
            return self.native(self.wood, 'reverse_gen2_home_native_parquet'), 'Complete native timber floor.'
        if mid in WALL:
            return self.native(self.wall, 'reverse_gen2_home_native_timber_wall'), 'Complete original timber wall module.'
        for color, members in TABLES.items():
            if mid in members:
                return self.table(game, color, mid), (
                    'The complete native Crystal table, four stools and exposed rug use their joined source footprint. '
                    'This carpet is the separate native-colored Gold or Blue variant of the original home rug.')
        if mid in {69, 204}:
            color = 'pink' if mid == 69 else 'gold'
            return self.native(self.carpet(color), 'reverse_gen2_home_native_plain_rug'), 'Complete carpet center continues the surrounding original Crystal rug.'
        if mid in PLANTS:
            witness = self.references[game, 'house', PLANTS[mid]]
            assert 'potted_tree' in witness['role']
            art = artwork(witness)
            art['base'] = self.wood
            art['role'] = 'reverse_gen2_home_complete_native_potted_plant'
            art['overMask'] = witness.get('overMask', '0' * 256)
            return art, 'The native Crystal potted plant keeps its complete canopy and pot on the matching timber floor.'
        if mid in KITCHEN_TOP:
            return self.native(self.wall, 'reverse_gen2_home_native_above_range'), 'Native timber wall continues above the complete Crystal sink and stove.'
        if mid in KITCHEN_BASE:
            return self.native(self.wood, 'reverse_gen2_home_native_below_range'), 'The floor below the complete native sink and stove uses the neighboring timber.'
        if mid == 180:
            donor = self.references[game, PAIR, 54]['donor']
            return self.native(donor, 'reverse_gen2_home_native_cupboard'), 'Complete native Crystal cupboard at the matching cabinet position.'

        if mid in STAIRS:
            feature, palette, base, outside = 'home_handed_stair_flight', 'timber', self.wood, floor_colors
        elif mid in WINDOWS:
            feature, palette, base, outside = 'home_joined_window_frame', 'blue', self.wall, wall_colors
        elif mid in CUPBOARD:
            feature, palette, base, outside = 'home_joined_cupboard_and_books', 'timber', self.wood, floor_colors
        elif mid in ELECTRONICS:
            feature, palette, base, outside = 'home_complete_television_and_wall_fixtures', 'metal', self.wall, wall_colors
            if mid in {641, 642, 654, 662}:
                color = 'gold' if mid in {641, 642} else 'pink'
                base = self.carpet(color)
                outside = self.colors_at(game, (204 if color == 'gold' else 69,))
        elif mid in BED:
            feature, palette, base, outside = 'home_complete_player_bed', 'blue', self.wood, floor_colors
        elif mid in DOOR_MAT:
            feature, palette = 'home_joined_doorway_mat', 'red'
            if mid in {26, 27, 28}:
                base, outside = self.void, {(0, 0, 0)}
            else:
                base, outside = self.wood, floor_colors
        elif mid in {194, 202, 210}:
            feature, palette, base, outside = 'home_tall_copycat_planter', 'green', self.wall, wall_colors
        elif mid in {183, 191}:
            feature, palette, base, outside = 'home_copycat_refrigerator', 'red', self.wall, wall_colors
        else:
            assert mid == 134
            feature, palette, base, outside = 'home_complete_bedside_checker_table', 'gold', self.wood, floor_colors
        return self.geometry(game, mid, feature, palette, base, outside), (
            'This named part of the original joined home feature keeps the complete contours, original pixel scale '
            'and original priority. Exact exposed backing pixels use the selected Crystal room material.')

    def build(self):
        for game in GAMES:
            floor = self.colors_at(game, (1, 9, 169, 177, 265, 273))
            wall = self.colors_at(game, (32, 40, 155, 163, 168, 176))
            for item in self.guards:
                if item['game'] != game:
                    continue
                mid = item['mid']
                source = self.imp.cell_index(game)[PAIR, mid]
                assert (source['pixel_sha256'], source['layer_sha256'], source['behavior']) == (
                    item['sourceHash'], item['sourceLayers'], item['sourceBehavior'])
                assert (game, PAIR, mid) not in self.references
                for witness in item['contexts']:
                    layout = self.native_layout(game, witness['map'])
                    assert layout['pair'] == PAIR and layout['mids'].count(mid) == witness['cells']
                art, evidence = self.recipe(game, mid, floor, wall)
                if art['kind'] != 'classic_native_geometry':
                    art.setdefault('overMask', '0' * 256)
                self.row(game, PAIR, mid, 'gen2', art, evidence)
        assert Counter(game for game, _, _, _, _ in self.rows) == Counter({game: 182 for game in GAMES})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    review = Review()
    review.build()
    proof = review.validate()
    review.write(OUTPUT / 'candidate.lua')
    if args.activate:
        review.write(TARGET)
    print(json.dumps(dict(rows=len(review.rows), cells=sum(item['cells'] for item in review.guards),
                          proof=proof, activated=args.activate)))


if __name__ == '__main__':
    main()
