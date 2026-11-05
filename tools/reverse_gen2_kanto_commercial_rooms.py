"""Complete the Game Corners, prize room, hotel and restaurant."""
from collections import Counter
from pathlib import Path
import argparse
import json

import preview
from johto_remaining_review import artwork
from reverse_common import ROOT, ReverseReview
from reverse_gen2_kanto_department import Review as Interior, BLUE, RED, STONE, TIMBER

GAMES = ('firered', 'leafgreen')
OUTPUT = ROOT.parent / '.work/tileshift-v0360-commercial-rooms'
TARGET = ROOT / 'mappings/reverse_gen2_kanto_commercial_rooms.lua'
GUARDS = Path(__file__).with_name('reverse_gen2_kanto_commercial_rooms_guards.json')
PAIRS = {
    'arcades': dict(firered='building__rom_082d4cec', leafgreen='building__rom_082d4ccc'),
    'hotel': dict(firered='building__rom_082d4f44', leafgreen='building__rom_082d4f24'),
}
FLOOR = {
    'arcades': {648, 656, 659, 684, 692, 693, 694, 712, 713, 720, 722, 736, 738, 739, 740,
                748, 749, 750, 751, 760, 780, 786},
    'hotel': {669, 670, 680, 689, 708, 709, 719, 721, 724, 730, 731, 732},
}
PLANTS = {'arcades': {718: 71, 725: 71, 726: 79, 743: 71, 744: 71, 745: 71, 746: 71,
                      752: 79, 753: 79, 754: 79},
          'hotel': {641: 71, 649: 79}}
MATS = {'arcades': {26, 27, 28, 721, 778, 779}, 'hotel': {26, 27, 28, 677, 678, 679, 725, 726, 727}}

# Each group was identified in the joined source room before choosing its
# original Crystal material. Mechanical labels and fixture silhouettes stay exact.
GROUPS = {
    'arcades': (
        ({642, 643, 644, 647, 695, 742, 747, 763, 764, 765, 766, 767, 775, 776, 777}, 'wall_and_window', BLUE),
        ({670, 671, 734, 735}, 'handed_stair_and_threshold', STONE),
        ({680, 681, 685, 686, 687, 703, 714, 715, 716, 717, 727, 728, 729, 730}, 'complete_game_machine', RED),
        ({98, 645, 646, 650, 651, 652, 653, 654, 700, 701, 702, 708, 710, 711, 731, 732,
          755, 756, 757, 758, 761, 762, 768, 769, 770, 771, 772, 773, 774, 781, 782, 783,
          784, 785, 787, 788, 789, 790, 791}, 'complete_console_or_minigame_terminal', BLUE),
        ({661, 662, 665, 668, 672, 674, 676, 677, 678, 679, 719}, 'complete_prize_counter', TIMBER),
    ),
    'hotel': (
        ({642, 643, 644, 645, 646, 647, 648, 650, 651, 652, 653, 654, 655, 660, 661, 662, 663,
          681, 682, 683, 684, 692, 693, 694, 695, 700, 701, 702, 703, 712, 720, 728, 729}, 'wall_window_and_desk', TIMBER),
        ({656, 657, 664, 665, 672, 673, 674, 675, 676}, 'handed_stair_and_threshold', STONE),
        ({658, 659, 666, 667, 668, 697, 698, 699, 705, 706, 707, 743}, 'complete_round_table_and_place_setting', TIMBER),
        ({671, 688, 696, 704, 713, 717, 718, 741, 742}, 'complete_handed_dining_chair', BLUE),
        ({710, 711, 714, 715, 722, 723, 736, 737, 738, 739, 740}, 'joined_kitchen_range_and_service_counter', BLUE),
    ),
}


class Review(Interior):
    def __init__(self):
        ReverseReview.__init__(self, 'gen2-kanto-commercial-rooms', GAMES)
        self.out = OUTPUT
        self.layouts = {}
        self.layout_hashes = {}
        self.guards = json.loads(GUARDS.read_text(encoding='utf-8'))
        self.floor = self.gb_at('crystal', 'CELADON_CAFE', 5, 3)
        self.carpet = self.gb_ref('crystal', 'GUIDE_GENTS_HOUSE', 15, 0)
        self.arcade = self.gb_at('crystal', 'CELADON_GAME_CORNER', 5, 3)
        self.void = self.gb_ref('crystal', 'FAST_SHIP_CABINS_SE_SSE_CAPTAINS_CABIN', 12, 0)
        self.plants = {(row['game'], row['id']): row
                       for row in preview.read_reviewed(ROOT / 'mappings/reverse_gen2_kanto_house_completion.lua')
                       if row['style'] == 'gen2' and row['tileset'] == 'house' and row['id'] in {71, 79}}
        for name in ('reverse_kanto', 'reverse_gen2_kanto_finish', 'reverse_gen2_kanto_final'):
            for row in preview.read_reviewed(ROOT / 'mappings' / (name + '.lua')):
                if (row['game'], row['style'], row['tileset'], row['id']) == (
                    'firered', 'gen2', PAIRS['arcades']['firered'], 657,
                ) and row.get('donor'):
                    self.arcade = row['donor']

    def recipe(self, scope, game, mid, base, floor):
        if mid in FLOOR[scope]:
            return self.native(base, 'reverse_gen2_commercial_complete_native_floor'), (
                'The complete original Crystal floor matches the surrounding room.')
        if mid in PLANTS[scope]:
            previous = self.plants[game, PLANTS[scope][mid]]
            assert 'potted_tree' in previous['role']
            art = dict(sorted(artwork(previous).items()))
            art.update(base=base, role='reverse_gen2_commercial_complete_native_plant', overMask=previous['overMask'])
            return art, 'The complete native Crystal canopy and pot sit on the matching room floor.'
        for group, name, palette in GROUPS[scope]:
            if mid in group:
                break
        else:
            assert mid in MATS[scope], (scope, mid)
            name, palette = 'joined_entry_mat', RED
            if mid in {26, 27, 28}:
                base, floor = self.void, {(0, 0, 0)}
        return self.feature(game, mid, scope + '_' + name, palette, base, floor), (
            'The complete named room feature keeps its original outline, position and priority. '
            'Exact outside pixels use the matching Crystal room material.')

    def build(self):
        for scope, pairs in PAIRS.items():
            self.pairs = pairs
            for game in GAMES:
                if scope == 'arcades':
                    floors = dict(corner=self.colors(game, (657, 658)), island=self.colors(game, (736,)))
                else:
                    floors = dict(hotel=self.colors(game, (670,)), restaurant=self.colors(game, (724, 719)))
                for item in self.guards:
                    if item['game'] != game or item['pair'] != pairs[game]:
                        continue
                    pair, mid = item['pair'], item['mid']
                    source = self.imp.cell_index(game)[pair, mid]
                    assert (source['pixel_sha256'], source['layer_sha256'], source['behavior']) == (
                        item['sourceHash'], item['sourceLayers'], item['sourceBehavior'])
                    for use in item['contexts']:
                        layout = self.native_layout(game, use['map'])
                        assert layout['pair'] == pair and layout['mids'].count(mid) == use['cells']
                    maps = {use['map'] for use in item['contexts']}
                    if scope == 'arcades':
                        base = self.arcade
                        floor = floors['island'] if all('JOYFUL' in name for name in maps) else floors['corner']
                    elif all('HOTEL' in name for name in maps):
                        base, floor = self.carpet, floors['hotel']
                    else:
                        base, floor = self.floor, floors['restaurant']
                    art, evidence = self.recipe(scope, game, mid, base, floor)
                    if art['kind'] != 'classic_native_geometry':
                        art.setdefault('overMask', '0' * 256)
                    self.row(game, pair, mid, 'gen2', art, evidence)
        assert Counter(game for game, _, _, _, _ in self.rows) == Counter({game: 218 for game in GAMES})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    OUTPUT.mkdir(exist_ok=True)
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
