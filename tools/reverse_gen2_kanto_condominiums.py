"""Complete Celadon Condominiums' rooms and rooftop in Crystal style."""
from collections import Counter
from pathlib import Path
import argparse
import json

import preview
from johto_remaining_review import artwork
from reverse_common import ROOT, ReverseReview
from reverse_gen2_kanto_department import Review as Interior, BLUE, RED, STONE, TIMBER

GAMES = ('firered', 'leafgreen')
PAIRS = dict(firered='building__rom_082d4f8c', leafgreen='building__rom_082d4f6c')
OUTPUT = ROOT.parent / '.work/tileshift-v0360-condominiums'
TARGET = ROOT / 'mappings/reverse_gen2_kanto_condominiums.lua'
GUARDS = Path(__file__).with_name('reverse_gen2_kanto_condominiums_guards.json')

FLOOR = {647, 663, 672, 673, 678, 679, 682, 683, 684, 722, 770, 786, 787}
WALL = {648, 651, 652, 656, 657, 659, 660, 668, 676, 680, 686, 688, 696, 697, 698, 699,
        700, 701, 704, 705, 706, 707, 731, 732, 739, 740, 747, 748, 749, 750, 755, 756, 760,
        761, 762, 763, 764, 769, 773}
STAIRS = {674, 675, 685, 687, 693, 694, 695, 702, 703, 768, 776, 777, 780, 781, 784, 785, 788, 789}
COUCHES = {715, 723, 736, 737, 738, 741, 742, 743, 772}
TABLES = {661, 662, 669, 670, 671, 677, 709, 710, 711, 717, 718, 719, 725, 726, 727, 733, 734, 735}
BOOKSHELVES = {751, 757, 758, 759}
MATS = {26, 27, 28, 744, 745, 746}
PLANTS = {712: 71, 713: 71, 714: 71, 720: 79, 721: 79}
ROOF = {774, 775, 783, 790, 791, 793, 794, 800, 801, 802, 809, 810, 814, 821, 822}
ROOF_PLANTS = {832, 833, 834, 835, 840, 841, 842, 843}
ROOF_ARCHITECTURE = {795, 796, 797, 798, 799, 803, 804, 805, 806, 807, 811, 812, 813, 815, 816,
                     817, 818, 819, 823, 824, 825, 826, 827, 828, 829, 830, 831, 836, 837, 844,
                     845, 848, 849, 850, 851, 852, 853, 854}
GARDEN = [(58, 58, 58), (41, 115, 0), (99, 206, 8), (247, 230, 214)]


class Review(Interior):
    pairs = PAIRS

    def __init__(self):
        ReverseReview.__init__(self, 'gen2-kanto-condominiums', GAMES)
        self.out = OUTPUT
        self.layouts = {}
        self.layout_hashes = {}
        self.guards = json.loads(GUARDS.read_text(encoding='utf-8'))
        self.floor = self.gb_ref('crystal', 'CELADON_MANSION_1F', 3, 0)
        self.roof = self.gb_at('crystal', 'CELADON_MANSION_ROOF', 6, 4)
        self.void = self.gb_ref('crystal', 'FAST_SHIP_CABINS_SE_SSE_CAPTAINS_CABIN', 12, 0)
        self.sky = self.raw_ref('TILESET_JOHTO', (0,) * 4, 'VIOLET_CITY')
        self.sky['palettes'] = [[[189, 189, 255], [148, 156, 255], [107, 99, 255], [58, 58, 58]] for _ in range(8)]
        self.plants = {(row['game'], row['id']): row
                       for row in preview.read_reviewed(ROOT / 'mappings/reverse_gen2_kanto_house_completion.lua')
                       if row['style'] == 'gen2' and row['tileset'] == 'house' and row['id'] in {71, 79}}

    def recipe(self, game, mid, backing):
        for group, ref, name in ((FLOOR, self.floor, 'medallion_floor'), (ROOF, self.roof, 'roof_stone'),
                                 ({808}, self.sky, 'roof_sky')):
            if mid in group:
                return self.native(ref, 'reverse_gen2_condominiums_native_' + name), (
                    'Complete original Crystal Celadon mansion material matches the surrounding room or rooftop.')
        if mid in PLANTS:
            previous = self.plants[game, PLANTS[mid]]
            assert 'potted_tree' in previous['role']
            art = dict(sorted(artwork(previous).items()))
            art.update(base=self.floor, role='reverse_gen2_condominiums_native_plant', overMask=previous['overMask'])
            return art, 'The complete original Crystal potted plant sits on the matching mansion floor.'
        groups = (
            (WALL, 'condominiums_joined_windows_walls_and_fixtures', BLUE, self.floor, backing['floor']),
            (STAIRS, 'condominiums_joined_handed_stair_treads', STONE, None, ()),
            (COUCHES, 'condominiums_complete_handed_sofas', BLUE, self.floor, backing['floor']),
            (TABLES, 'condominiums_joined_octagonal_dining_table', TIMBER, self.floor, backing['floor']),
            (BOOKSHELVES, 'condominiums_complete_bookcase', TIMBER, self.floor, backing['floor']),
            (ROOF_PLANTS, 'condominiums_complete_rooftop_planters', GARDEN, self.roof, backing['roof']),
            (ROOF_ARCHITECTURE, 'condominiums_joined_roof_and_wall_shell', STONE, self.sky, backing['sky']),
        )
        for group, name, palette, base, exterior in groups:
            if mid in group:
                break
        else:
            if mid == 692:
                name, palette, base, exterior = 'condominiums_complete_potted_flower', GARDEN, self.floor, backing['floor']
            else:
                assert mid in MATS, mid
                name, palette = 'condominiums_joined_entrance_mat', RED
                base, exterior = (self.void, {(0, 0, 0)}) if mid in {26, 27, 28} else (self.floor, backing['floor'])
        return self.feature(game, mid, name, palette, base, exterior), (
            'The complete named condominium feature keeps its original silhouette, orientation and priority. '
            'Exact exterior pixels use the matching Crystal backing surface.')

    def build(self):
        for game in GAMES:
            backing = {name: self.colors(game, mids) for name, mids in
                       dict(floor=(641, 642), roof=(774, 775), sky=(808,)).items()}
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
                art, evidence = self.recipe(game, mid, backing)
                if art['kind'] != 'classic_native_geometry':
                    art.setdefault('overMask', '0' * 256)
                self.row(game, pair, mid, 'gen2', art, evidence)
        assert Counter(game for game, _, _, _, _ in self.rows) == Counter({game: 175 for game in GAMES})


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
