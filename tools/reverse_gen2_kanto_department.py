"""Complete the Celadon Department Store's original interior and rooftop."""
from collections import Counter
from pathlib import Path
import argparse
import json

import catalog
import preview
from classic_geometry_review import art as geometry_art
from johto_remaining_review import artwork
from reverse_common import ROOT, ReverseReview
from reverse_gen2_hoenn_outdoor_complete import Review as Layouts

GAMES = ('firered', 'leafgreen')
PAIRS = dict(firered='building__rom_082d4e6c', leafgreen='building__rom_082d4e4c')
OUTPUT = ROOT.parent / '.work/tileshift-v0360-department'
TARGET = ROOT / 'mappings/reverse_gen2_kanto_department.lua'
GUARDS = Path(__file__).with_name('reverse_gen2_kanto_department_guards.json')

STAIRS = {663, 664, 665, 666, 669, 670, 671, 672, 673, 674, 675, 676, 677, 679,
          864, 865, 869, 872, 873, 874, 875, 876, 877, 880, 881, 882, 883, 884, 885}
WINDOWS = {641, 643, 644, 645, 646, 647, 649, 650, 651, 652, 653, 654, 659, 660, 662, 667,
           668, 680, 685, 686, 687, 688, 689, 693, 694, 695, 862, 863}
FLOOR_LABELS = {655, 656, 657, 658, 661}
ENTRY_MAT = {682, 683, 684, 690, 691, 692}
PLANTS = {702: 71, 703: 71, 710: 79, 711: 79, 795: 71, 803: 79}
FLOOR = {712, 713, 714, 720, 721, 722, 728, 729, 730, 732, 740, 741, 753, 754,
         760, 761, 762, 771, 776, 777, 778, 784, 785, 791, 792, 793, 802, 806}
COUNTERS = {715, 716, 717, 718, 723, 724, 725, 726, 731, 733, 734, 738, 739,
            742, 744, 745, 746, 747, 748, 750, 763, 772, 779, 780, 787, 788, 796, 804}
STOCK = {719, 727, 735, 736, 737, 743, 751, 755, 759, 767, 768, 769, 770, 774, 775,
         781, 782, 783, 786, 790, 794, 798, 799, 800, 801, 807, 808, 809, 817}
ROOF_SLAB = {648, 696, 699}
ROOF_SKY = {855}
ROOF_BUILDING = {756, 757, 758, 764, 765, 766, 805, 813, 814, 815, 824, 825, 826,
                 827, 828, 829, 830, 832, 833, 834, 835, 837, 838, 839, 840, 841,
                 845, 846, 847, 848, 849, 850, 851, 852, 853, 854, 856, 857, 858, 861}
ROOF_OBJECTS = {810, 811, 812, 818, 819, 820, 821, 836, 843, 844, 859, 860, 867}
ROOF_PATIO = {822, 823, 831}

TIMBER = [(58, 58, 58), (132, 107, 25), (197, 148, 58), (247, 230, 214)]
STONE = [(0, 0, 0), (58, 58, 58), (156, 156, 156), (247, 230, 214)]
BLUE = [(58, 58, 58), (74, 74, 255), (123, 132, 255), (247, 230, 214)]
RED = [(0, 0, 0), (165, 49, 41), (247, 82, 49), (255, 156, 197)]


class Review(Layouts):
    pairs = PAIRS

    def __init__(self):
        ReverseReview.__init__(self, 'gen2-kanto-department', GAMES)
        self.out = OUTPUT
        self.layouts = {}
        self.layout_hashes = {}
        self.guards = json.loads(GUARDS.read_text(encoding='utf-8'))
        self.floor = self.gb_ref('crystal', 'CELADON_DEPT_STORE_1F', 4, 0)
        self.roof = self.gb_at('crystal', 'GOLDENROD_DEPT_STORE_ROOF', 4, 3)
        self.void = self.gb_ref('crystal', 'FAST_SHIP_CABINS_SE_SSE_CAPTAINS_CABIN', 12, 0)
        self.sky = self.raw_ref('TILESET_JOHTO', (0,) * 4, 'VIOLET_CITY')
        self.sky['palettes'] = [[[189, 189, 255], [148, 156, 255], [107, 99, 255], [58, 58, 58]] for _ in range(8)]
        self.plants = {(row['game'], row['id']): row
                       for row in preview.read_reviewed(ROOT / 'mappings/reverse_gen2_kanto_house_completion.lua')
                       if row['style'] == 'gen2' and row['tileset'] == 'house' and row['id'] in {71, 79}}

    def render(self, row):
        return preview.replacement_image(self.cache, row, self.packed, ROOT)

    def planes(self, game, mid):
        pair = self.pairs[game]
        source = self.imp.cell_index(game)[pair, mid]
        preview.native_donor(self.cache, dict(game=game, tileset=pair, id=mid, hash=source['pixel_sha256']), self.packed)
        ids, palette, blobs = self.packed[game, pair]
        start = ids.index(mid) * 256
        return {name: catalog.rgba_native(blob[start:start + 256], palette, name != 'under') for name, blob in blobs.items()}

    def colors(self, game, mids):
        return {p[:3] for mid in mids for p in self.planes(game, mid)['under'].get_flattened_data()}

    def feature(self, game, mid, name, palette, base=None, exterior=()):
        colors, masks = {}, {}
        for layer, image in self.planes(game, mid).items():
            pixels = list(image.get_flattened_data())
            for r, g, b, a in pixels:
                if a:
                    light = (54 * r + 183 * g + 19 * b) / 256
                    colors[r, g, b] = palette[sum(light >= limit for limit in (83, 145, 207))]
            if base:
                mask = ''.join('1' if p[3] and p[:3] in exterior else '0' for p in pixels)
                if '1' in mask:
                    masks[layer] = mask
        ground = dict(donor=base, masks=masks) if masks else None
        return geometry_art(self, game, self.pairs[game], mid, name, palette, colors, ground=ground)

    def recipe(self, game, mid, backing):
        for group, ref, name in ((FLOOR, self.floor, 'interior_floor'), (ROOF_SLAB | ROOF_PATIO, self.roof, 'rooftop_paving'),
                                 (ROOF_SKY, self.sky, 'rooftop_sky')):
            if mid in group:
                return self.native(ref, 'reverse_gen2_department_native_' + name), (
                    'The complete original Crystal surface joins the matching neighboring department store cells.')
        if mid in PLANTS:
            previous = self.plants[game, PLANTS[mid]]
            assert 'potted_tree' in previous['role']
            art = dict(sorted(artwork(previous).items()))
            art.update(base=self.floor, role='reverse_gen2_department_complete_native_plant', overMask=previous['overMask'])
            return art, 'The complete original Crystal potted plant sits on the same native checker floor.'
        if mid == 817:
            return self.feature(game, mid, 'department_blue_stock_shelf_foot', BLUE, self.floor, backing['floor']), (
                'The blue foot and shelf edge continue the adjacent native Azalea stock shelf.')
        groups = (
            (STAIRS, 'department_joined_handed_stairs', STONE, self.floor, backing['floor']),
            (WINDOWS, 'department_joined_window_and_wall_panels', BLUE, self.floor, backing['floor']),
            (FLOOR_LABELS, 'department_exact_floor_number_sign', RED, None, ()),
            (COUNTERS, 'department_complete_wraparound_counter', BLUE, self.floor, backing['floor']),
            (STOCK, 'department_complete_display_and_register', TIMBER, self.floor, backing['floor']),
            (ROOF_BUILDING, 'department_joined_roof_and_vending_wall', STONE, self.sky, backing['sky']),
            (ROOF_OBJECTS, 'department_complete_roof_table_and_fixtures', STONE, self.roof, backing['roof']),
        )
        for group, name, palette, base, exterior in groups:
            if mid in group:
                break
        else:
            assert mid in ENTRY_MAT, mid
            name, palette = 'department_joined_entry_mat', RED
            base, exterior = (self.void, {(0, 0, 0)}) if mid >= 690 else (self.floor, backing['floor'])
        return self.feature(game, mid, name, palette, base, exterior), (
            'This exact department store feature retains its original complete silhouette and alignment. '
            'The Crystal material carries the source priority, while exposed backing pixels show the surrounding surface.')

    def build(self):
        for game in GAMES:
            backing = {key: self.colors(game, mids) for key, mids in
                       dict(floor=(704, 707, 708), roof=(696, 699), sky=(855,)).items()}
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
        assert Counter(game for game, _, _, _, _ in self.rows) == Counter({game: 219 for game in GAMES})


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
