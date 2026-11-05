"""Finish the Safari offices, rest houses and Lorelei's house in Crystal art."""
from collections import Counter
from pathlib import Path
import argparse
import copy
import json

import preview
from johto_remaining_review import artwork
from reverse_common import ROOT, ReverseReview
from reverse_gen2_kanto_department import Review as Interior, BLUE, RED, STONE, TIMBER

GAMES = ('firered', 'leafgreen')
PAIRS = dict(firered='building__rom_082d4f14', leafgreen='building__rom_082d4ef4')
OUTPUT = ROOT.parent / '.work/tileshift-v0360-safari-rooms'
TARGET = ROOT / 'mappings/reverse_gen2_kanto_safari_rooms.lua'
GUARDS = Path(__file__).with_name('reverse_gen2_kanto_safari_rooms_guards.json')

FLOOR = {646, 647, 664, 685, 686, 693, 707, 728}
WALL = {264, 267, 268, 269, 272, 280, 352, 360, 641, 642, 643, 644, 645, 649, 651,
        652, 653, 680, 681, 696, 697, 712, 713, 714, 715, 762, 763}
KITCHEN = {275, 276, 277, 288, 720, 721, 722}
PLANTS = {654: 71, 655: 71, 662: 79, 663: 79, 690: 71, 703: 79}
GREEN_PATH = {648, 658, 659, 665, 666, 667, 673, 702}
YELLOW_PATH = {660, 661, 668, 669, 674, 676, 677, 694}
CABINETS = {670, 671, 675, 678, 679, 687, 698, 699, 708, 709, 710, 749, 750, 751,
            757, 758, 759, 688, 689, 764, 765, 766, 767}
CHAIRS = {657, 672, 706, 735, 739}
MAT = {26, 27, 28, 682, 683, 684, 700, 701, 725, 726, 727}
RUG = {732, 733, 734, 736, 737, 738, 740, 741, 742}
BED = {704, 705, 744, 745, 746, 752, 753, 754}
TABLES = {716: 76, 717: 77, 718: 84, 719: 85, 747: 76, 748: 77, 755: 84, 756: 85}
GREEN = [(58, 58, 58), (41, 115, 0), (99, 206, 8), (181, 255, 82)]
GOLD = [(58, 58, 58), (132, 107, 25), (197, 148, 58), (255, 255, 58)]


class Review(Interior):
    pairs = PAIRS

    def __init__(self):
        ReverseReview.__init__(self, 'gen2-kanto-safari-rooms', GAMES)
        self.out = OUTPUT
        self.layouts = {}
        self.layout_hashes = {}
        self.guards = json.loads(GUARDS.read_text(encoding='utf-8'))
        self.floor = self.gb_ref('crystal', 'PLAYERS_HOUSE_1F', 3, 0)
        self.void = self.gb_ref('crystal', 'FAST_SHIP_CABINS_SE_SSE_CAPTAINS_CABIN', 12, 0)
        self.rug = self.gb_ref('crystal', 'GUIDE_GENTS_HOUSE', 15, 0)
        self.tables = {}
        self.plants = {}
        for file, dest, pair, ids in (
            ('reverse_gen2_kanto_house_completion', self.plants, 'house', {71, 79}),
            ('reverse_gen2_kanto_finish', self.tables, 'player_house', set(TABLES.values())),
        ):
            for row in preview.read_reviewed(ROOT / 'mappings' / (file + '.lua')):
                if row['game'] in GAMES and row['style'] == 'gen2' and row['tileset'] == pair and row['id'] in ids:
                    dest[row['game'], row['id']] = row

    def table(self, game, mid):
        row = self.tables[game, TABLES[mid]]
        assert row['role'] == 'classic_gen2_complete_house_table_rug_and_stools'
        parts = [copy.deepcopy(p) for p in row['parts'] if p['donor'] != self.rug]
        assert parts
        base = self.rug if mid >= 747 else self.floor
        art = self.composite(base, parts, 'reverse_gen2_safari_complete_native_table')
        art['overMask'] = row['overMask']
        return art

    def recipe(self, game, mid, floor):
        if mid in FLOOR:
            return self.native(self.floor, 'reverse_gen2_safari_native_timber_floor'), (
                'Complete original Crystal timber floor continues the neighboring Safari rooms.')
        if mid in PLANTS:
            row = self.plants[game, PLANTS[mid]]
            assert 'potted_tree' in row['role']
            art = dict(sorted(artwork(row).items()))
            art.update(base=self.floor, role='reverse_gen2_safari_complete_native_planter', overMask=row['overMask'])
            return art, 'The complete native Crystal canopy and pot sit on the matching timber floor.'
        if mid in TABLES:
            return self.table(game, mid), (
                'The complete native Crystal table retains the original two-cell width and table-foot alignment.')
        groups = (
            (WALL, 'safari_joined_wall_and_window', BLUE, self.floor, floor),
            (KITCHEN, 'lorelei_joined_kitchenette', TIMBER, self.floor, floor),
            (GREEN_PATH, 'safari_entrance_complete_green_walkway', GREEN, self.floor, floor),
            (YELLOW_PATH, 'safari_entrance_complete_gold_walkway', GOLD, self.floor, floor),
            (CABINETS, 'safari_joined_cabinet_and_bookcase', TIMBER, self.floor, floor),
            (CHAIRS, 'safari_complete_handed_chair_and_stool', TIMBER, self.floor, floor),
            (RUG, 'lorelei_complete_framed_area_rug', RED, self.floor, floor),
            (BED, 'safari_complete_bed_and_worktable', BLUE, self.floor, floor),
        )
        for ids, name, palette, base, exterior in groups:
            if mid in ids:
                break
        else:
            assert mid in MAT, mid
            name, palette = 'safari_joined_red_entrance_mat', RED
            base, exterior = (self.void, {(0, 0, 0)}) if mid in {26, 27, 28} else (self.floor, floor)
        return self.feature(game, mid, name, palette, base, exterior), (
            'The complete named interior feature keeps the original contour and priority. '
            'Exact outside pixels show the selected Crystal room material.')

    def build(self):
        for game in GAMES:
            floor = self.colors(game, (646, 647, 656, 664))
            for item in self.guards:
                if item['game'] != game:
                    continue
                pair, mid = item['pair'], item['mid']
                assert pair == PAIRS[game]
                source = self.imp.cell_index(game)[pair, mid]
                assert (source['pixel_sha256'], source['layer_sha256'], source['behavior']) == (
                    item['sourceHash'], item['sourceLayers'], item['sourceBehavior'])
                for use in item['contexts']:
                    layout = self.native_layout(game, use['map'])
                    assert layout['pair'] == pair and layout['mids'].count(mid) == use['cells']
                art, evidence = self.recipe(game, mid, floor)
                if art['kind'] != 'classic_native_geometry':
                    art.setdefault('overMask', '0' * 256)
                self.row(game, pair, mid, 'gen2', art, evidence)
        assert Counter(game for game, _, _, _, _ in self.rows) == Counter({game: 128 for game in GAMES})


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
