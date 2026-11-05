"""Complete FireRed and LeafGreen Trainer Tower's lobby, floors and roof."""
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
PAIRS = dict(firered='building__rom_082d5094', leafgreen='building__rom_082d5074')
OUTPUT = ROOT.parent / '.work/tileshift-v0360-trainer-tower'
TARGET = ROOT / 'mappings/reverse_gen2_kanto_trainer_tower.lua'
GUARDS = Path(__file__).with_name('reverse_gen2_kanto_trainer_tower_guards.json')

LOBBY_FLOOR = {641, 643, 644, 645, 646, 647, 672, 686, 687, 689, 716, 735, 739}
LOBBY_WALL = {648: (0, 0), 649: (1, 0), 650: (2, 0), 651: (5, 0), 652: (7, 0),
              656: (0, 0), 657: (1, 0), 658: (7, 0), 660: (7, 0)}
LOBBY_COUNTER = {653, 654, 655, 661, 662, 669, 670, 671, 673, 674, 675, 676, 677, 678, 679,
                 680, 681, 682, 683, 684, 685, 690, 694, 695, 696, 703, 704, 705, 711, 886, 887}
LOBBY_DEVICES = {98, 692, 693, 697, 698, 699, 700, 701, 702, 706, 707, 708, 709, 710, 715, 717,
                 718, 719, 720, 721, 728, 729, 752}
LOBBY_STAIR = {727, 736, 737, 738, 740, 741, 742, 743, 744}
LOBBY_MEDALLION = {722, 723, 724, 730, 731, 732}
ENTRY_MAT = {26, 27, 28, 712, 713, 714}
PLANTS = {725: 71, 726: 71, 733: 79, 734: 79}
BATTLE_WALL = {745: (0, 0), 746: (1, 0), 747: (2, 0), 749: (5, 0), 754: (0, 0), 755: (2, 0), 757: (5, 0)}
BATTLE_FLOOR = {759, 773, 777, 783, 786, 906}
BATTLE_STAIR = {768, 769, 770, 771, 772, 774, 775, 776, 778, 779, 780, 781, 782, 784, 785}
BATTLE_PANEL = {753, 760, 761, 763, 765, 898, 912, 914, 915, 916, 917, 918, 919, 920, 921, 922,
                923, 924, 925, 926, 927}
BATTLE_POST = {896, 904, 905}
ROOF_SKY = {794, 827, 828, 859}
ROOF_DECK = {787, 788, 789, 792, 793, 858, 863, 869}
ROOF_STAIR = {864, 865, 866, 867, 868, 870, 871}
ROOF_POST = {872, 873, 874, 880, 881, 882, 883, 884, 888, 889, 890, 891, 892}
ROOF_FACADE = {796, 798, 799, 801, 802, 803, 804, 805, 806, 808, 809, 810, 811, 812, 813,
               814, 816, 817, 818, 819, 820, 821, 822, 824, 825, 826, 829, 830, 832, 833, 835,
               837, 838, 839, 841, 842, 843, 845, 846, 847, 848, 849, 850, 851, 852, 853, 854,
               855, 875, 876, 877}

STONE = [(58, 58, 58), (107, 107, 107), (156, 156, 156), (247, 230, 214)]
TIMBER = [(58, 58, 58), (132, 107, 25), (197, 148, 58), (247, 230, 214)]
BLUE = [(58, 58, 58), (58, 90, 123), (115, 140, 255), (222, 255, 222)]
RED = [(58, 58, 58), (165, 49, 41), (247, 82, 49), (255, 156, 197)]
PANELS = [(58, 58, 58), (74, 90, 123), (247, 82, 49), (247, 230, 214)]


class Review(Layouts):
    def __init__(self):
        ReverseReview.__init__(self, 'gen2-kanto-trainer-tower', GAMES)
        self.out = OUTPUT
        self.layouts = {}
        self.layout_hashes = {}
        self.guards = json.loads(GUARDS.read_text(encoding='utf-8'))
        self.lobby = self.gb_ref('crystal', 'BATTLE_TOWER_1F', 1, 0)
        self.battle = self.gb_ref('crystal', 'BATTLE_TOWER_BATTLE_ROOM', 10, 0)
        self.roof = self.gb_at('crystal', 'LANCES_ROOM', 2, 8)
        self.void = self.gb_ref('crystal', 'FAST_SHIP_CABINS_SE_SSE_CAPTAINS_CABIN', 12, 0)
        self.sky = self.raw_ref('TILESET_JOHTO', (0,) * 4, 'VIOLET_CITY')
        self.sky['palettes'] = [[[189, 189, 255], [148, 156, 255], [107, 99, 255], [58, 58, 58]] for _ in range(8)]
        assert len(set(self.gb_image(self.sky).get_flattened_data())) == 1
        self.plants = {}
        path = ROOT / 'mappings/reverse_gen2_kanto_house_completion.lua'
        for row in preview.read_reviewed(path):
            if row['style'] == 'gen2' and row['tileset'] == 'house' and row['id'] in {71, 79}:
                assert 'potted_tree' in row['role']
                self.plants[row['game'], row['id']] = row

    def render(self, row):
        return preview.replacement_image(self.cache, row, self.packed, ROOT)

    def planes(self, game, mid):
        pair = PAIRS[game]
        source = self.imp.cell_index(game)[pair, mid]
        preview.native_donor(self.cache, dict(game=game, tileset=pair, id=mid, hash=source['pixel_sha256']), self.packed)
        ids, colors, blobs = self.packed[game, pair]
        start = ids.index(mid) * 256
        return {name: catalog.rgba_native(blob[start:start + 256], colors, name != 'under')
                for name, blob in blobs.items()}

    def colors(self, game, mid):
        return {pixel[:3] for pixel in self.planes(game, mid)['under'].get_flattened_data()}

    def feature(self, game, mid, name, palette, base=None, floor_colors=()):
        colors, masks = {}, {}
        for layer, plane in self.planes(game, mid).items():
            pixels = list(plane.get_flattened_data())
            for r, g, b, a in pixels:
                if a:
                    light = (54 * r + 183 * g + 19 * b) / 256
                    level = sum(light >= cut for cut in (83, 142, 202))
                    if palette is PANELS and r >= 156 and r - b >= 35 and r - g >= 24:
                        level = 2
                    colors[r, g, b] = palette[level]
            if base:
                mask = ''.join('1' if p[3] and p[:3] in floor_colors else '0' for p in pixels)
                if '1' in mask:
                    masks[layer] = mask
        ground = dict(donor=base, masks=masks) if masks else None
        return geometry_art(self, game, PAIRS[game], mid, name, palette, colors, ground=ground)

    def recipe(self, game, mid, backing):
        direct = ((LOBBY_FLOOR, self.lobby, 'lobby_floor'), (BATTLE_FLOOR, self.battle, 'battle_floor'),
                  (ROOF_SKY, self.sky, 'roof_sky'), (ROOF_DECK, self.roof, 'roof_deck'))
        for ids, donor, name in direct:
            if mid in ids:
                return self.native(donor, 'reverse_gen2_trainer_tower_native_' + name), (
                    'Complete original Crystal tile matches the adjacent floor, sky or deck material.')
        for ids in (LOBBY_WALL, BATTLE_WALL):
            if mid in ids:
                return self.native(self.gb_at('crystal', 'BATTLE_TOWER_BATTLE_ROOM', *ids[mid]), 'reverse_gen2_trainer_tower_native_wall'), (
                    'Complete original Crystal Battle Tower wall panel continues the joined room wall.')
        if mid in PLANTS:
            previous = self.plants[game, PLANTS[mid]]
            art = dict(sorted(artwork(previous).items()))
            art.update(base=self.lobby, role='reverse_gen2_trainer_tower_native_potted_plant', overMask=previous['overMask'])
            return art, 'The complete original Crystal potted plant sits on the matching Battle Tower floor.'
        groups = (
            (LOBBY_COUNTER, 'lobby_complete_service_counter', TIMBER, self.lobby, backing['lobby']),
            (LOBBY_DEVICES, 'lobby_complete_terminal_or_elevator', PANELS, self.lobby, backing['lobby']),
            (LOBBY_STAIR, 'lobby_joined_handed_stair_treads', STONE, self.lobby, backing['lobby']),
            (LOBBY_MEDALLION, 'lobby_complete_floor_medallion', BLUE, self.lobby, backing['lobby']),
            (BATTLE_STAIR, 'battle_handed_stair_and_threshold', STONE, self.battle, backing['battle']),
            (BATTLE_PANEL, 'battle_complete_indicator_panel', PANELS, self.battle, backing['battle']),
            (BATTLE_POST, 'battle_complete_tracking_post', PANELS, self.battle, backing['battle']),
            (ROOF_STAIR, 'roof_handed_stairs_and_threshold', STONE, self.roof, backing['deck']),
            (ROOF_POST, 'roof_complete_railing_and_telescope', STONE, self.roof, backing['deck']),
            (ROOF_FACADE, 'roof_joined_tower_exterior', BLUE, self.sky, backing['sky']),
        )
        for ids, name, palette, base, colors in groups:
            if mid in ids:
                break
        else:
            assert mid in ENTRY_MAT, mid
            name, palette = 'lobby_complete_entry_mat', RED
            base, colors = (self.void, {(0, 0, 0)}) if mid in {26, 27, 28} else (self.lobby, backing['lobby'])
        return self.feature(game, mid, name, palette, base, colors), (
            'This named joined Trainer Tower feature keeps its full source contours, priority and original scale. '
            'Exact exposed backing pixels continue the native Crystal room or sky material.')

    def build(self):
        for game in GAMES:
            backing = {key: self.colors(game, mid) for key, mid in dict(lobby=641, battle=750, deck=787, sky=859).items()}
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
        assert Counter(game for game, _, _, _, _ in self.rows) == Counter({game: 236 for game in GAMES})


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
