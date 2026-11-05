"""Complete FireRed and LeafGreen's five Indigo League battle rooms."""
from collections import Counter
from pathlib import Path
import argparse
import copy
import json

import catalog
import preview
from classic_geometry_review import art as geometry_art
from reverse_common import ROOT, ReverseReview
from reverse_gen2_hoenn_outdoor_complete import Review as Layouts

GAMES = ('firered', 'leafgreen')
PAIRS = dict(firered='building__rom_082d50c4', leafgreen='building__rom_082d50a4')
OUTPUT = ROOT.parent / '.work/tileshift-v0360-league'
TARGET = ROOT / 'mappings/reverse_gen2_kanto_league.lua'
GUARDS = Path(__file__).with_name('reverse_gen2_kanto_league_guards.json')

WALL = {643: (1, 0), 644: (0, 1), 646: (1, 1), 645: (0, 2), 647: (1, 2), 656: (1, 0)}
DOORS = {650, 651, 652, 658, 659, 660, 666, 667, 668, 674, 675, 676, 816, 817, 818,
         819, 820, 821, 822, 823, 824, 825, 826, 827, 828, 829, 830, 831, 832, 840}
PLAIN = {
    'LORELEIS': {680, 681, 682, 683, 689, 690},
    'BRUNOS': {721, 722, 723, 727, 728, 837, 838},
    'AGATHAS': {753, 754, 755, 759, 760},
    'LANCES': {785, 786, 787, 791, 792, 793},
    'CHAMPIONS': {937},
}
PILLARS = {
    'LORELEIS': {724, 725, 833, 834, 835, 836, 841, 842, 845},
    'BRUNOS': {729, 730, 843, 844, 848, 849, 850, 851, 856, 857, 859},
    'AGATHAS': {756, 757, 852, 853, 854, 864, 865, 866, 867},
    'LANCES': {576, 577, 585, 642, 761, 762, 847, 855, 872, 873, 874, 875, 880, 881, 882, 883, 888, 889},
    'CHAMPIONS': {944, 945, 946, 947, 967, 968, 970, 971, 976, 977, 978, 979, 980, 981,
                  984, 985, 986, 987, 988, 989, 992, 993, 994, 995},
}
EMBLEMS = {
    'LORELEIS': set(range(691, 715)),
    'BRUNOS': set(range(731, 752)) | {715, 716, 717},
    'AGATHAS': set(range(763, 784)) | {673, 718, 719},
    'LANCES': set(range(795, 816)) | {664, 665, 672},
    'CHAMPIONS': {949, 950, 951, 952, 953, 954, 955, 957, 958, 959, 998, 999, 1006, 1007,
                  1014, 1015, 1022, 1023},
}
CHAMPION_HALL = {662, 896, 897, 898, 899, 900, 901, 902, 904, 905, 906, 907, 908, 909,
                 910, 911, 912, 913, 914, 915, 916, 917, 918, 919, 920, 921, 922, 923, 924,
                 925, 926, 927, 928, 930, 931, 932, 933, 934, 935, 936, 938, 939, 941, 942,
                 943, 960, 961, 962, 963, 964, 965, 966, 969, 972, 973, 974, 1000, 1001,
                 1008, 1009, 1010, 1016, 1017, 1018, 1019, 1020, 1021}

STONE = [(58, 58, 58), (107, 107, 107), (156, 156, 156), (247, 230, 214)]
ICE = [(58, 58, 58), (58, 90, 123), (115, 140, 255), (222, 255, 222)]
GOLD = [(58, 58, 58), (132, 107, 25), (197, 148, 58), (247, 230, 214)]
VIOLET = [(58, 58, 58), (74, 74, 255), (123, 132, 255), (247, 230, 214)]
CHAMPION = [(0, 0, 0), (58, 58, 58), (156, 156, 156), (247, 230, 214)]
ROOM_PALETTES = dict(LORELEIS=ICE, BRUNOS=GOLD, AGATHAS=VIOLET, LANCES=ICE, CHAMPIONS=CHAMPION)


class Review(Layouts):
    def __init__(self):
        ReverseReview.__init__(self, 'gen2-kanto-league', GAMES)
        self.out = OUTPUT
        self.layouts = {}
        self.layout_hashes = {}
        self.guards = json.loads(GUARDS.read_text(encoding='utf-8'))
        self.floors = dict(LORELEIS=self.gb_at('crystal', 'WILLS_ROOM', 1, 7),
                           BRUNOS=self.gb_at('crystal', 'BRUNOS_ROOM', 2, 8),
                           AGATHAS=self.gb_at('crystal', 'KARENS_ROOM', 2, 8),
                           LANCES=self.gb_at('crystal', 'LANCES_ROOM', 2, 8),
                           CHAMPIONS=self.gb_at('crystal', 'LANCES_ROOM', 2, 8))
        for name in ('reverse_kanto', 'reverse_gen2_kanto_finish', 'reverse_gen2_kanto_complete'):
            for row in preview.read_reviewed(ROOT / 'mappings' / (name + '.lua')):
                if row['style'] != 'gen2' or row['tileset'] != PAIRS.get(row['game']):
                    continue
                room = {720: 'BRUNOS', 752: 'AGATHAS', 784: 'LANCES'}.get(row['id'])
                if room:
                    self.floors[room] = copy.deepcopy(row['donor'])
        self.floors['CHAMPIONS'] = self.floors['LANCES']

    def render(self, row):
        return preview.replacement_image(self.cache, row, self.packed, ROOT)

    def planes(self, game, mid):
        pair = PAIRS[game]
        item = self.imp.cell_index(game)[pair, mid]
        preview.native_donor(self.cache, dict(game=game, tileset=pair, id=mid, hash=item['pixel_sha256']), self.packed)
        ids, colors, blobs = self.packed[game, pair]
        start = ids.index(mid) * 256
        return {name: catalog.rgba_native(blob[start:start + 256], colors, name != 'under')
                for name, blob in blobs.items()}

    def colors(self, game, mid):
        return {pixel[:3] for pixel in self.planes(game, mid)['under'].get_flattened_data()}

    def feature(self, game, mid, name, palette, floor=None, source_floor=None):
        colors, masks = {}, {}
        for layer, plane in self.planes(game, mid).items():
            pixels = list(plane.get_flattened_data())
            for r, g, b, a in pixels:
                if a:
                    light = (54 * r + 183 * g + 19 * b) / 256
                    colors[r, g, b] = palette[sum(light >= cut for cut in (80, 142, 203))]
                    if (r, g, b) == (0, 0, 0) and palette is CHAMPION:
                        colors[r, g, b] = (0, 0, 0)
            if floor:
                mask = ''.join('1' if p[3] and p[:3] in source_floor else '0' for p in pixels)
                if '1' in mask:
                    masks[layer] = mask
        backing = dict(donor=floor, masks=masks) if masks else None
        return geometry_art(self, game, PAIRS[game], mid, name, palette, colors, ground=backing)

    def recipe(self, item, source_floors):
        game, mid = item['game'], item['mid']
        if mid in WALL:
            return self.native(self.gb_at('crystal', 'WILLS_ROOM', *WALL[mid]), 'reverse_gen2_league_native_castle_wall'), (
                'Complete original Crystal Indigo Plateau castle wall and footing at native scale.')
        if mid in DOORS:
            return self.feature(game, mid, 'indigo_league_complete_stair_or_doorway', STONE), (
                'The complete original stair treads or doorway frame stay aligned in their source orientation. '
                'The source warp and collision retain their original position.')
        rooms = {use['map'].split('_')[-2] for use in item['contexts']}
        assert len(rooms) == 1, (mid, rooms)
        room, = rooms
        floor = self.floors[room]
        if mid in PLAIN[room] or mid == 911:
            return self.native(floor, 'reverse_gen2_league_native_arena_floor'), (
                'Complete original Crystal arena floor joins the matching native floor already selected for this room.')
        if mid in PILLARS[room]:
            name = 'indigo_league_complete_pillar_statue_or_light'
        elif mid in EMBLEMS[room]:
            name = 'indigo_league_complete_arena_emblem_and_border'
        else:
            assert room == 'CHAMPIONS' and mid in CHAMPION_HALL, (room, mid)
            name = 'indigo_league_joined_champion_hall'
        return self.feature(game, mid, name, ROOM_PALETTES[room], floor, source_floors[room]), (
            'The exact original joined arena detail retains its complete silhouette, interior outline and priority '
            "in the room's Crystal material. Exact exterior floor pixels show the matching native arena floor.")

    def build(self):
        for game in GAMES:
            source_floors = {name: self.colors(game, mid) for name, mid in
                             dict(LORELEIS=680, BRUNOS=720, AGATHAS=752, LANCES=784, CHAMPIONS=911).items()}
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
                art, evidence = self.recipe(item, source_floors)
                if art['kind'] != 'classic_native_geometry':
                    art['overMask'] = '0' * 256
                self.row(game, pair, mid, 'gen2', art, evidence)
        assert Counter(game for game, _, _, _, _ in self.rows) == Counter({game: 313 for game in GAMES})


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
