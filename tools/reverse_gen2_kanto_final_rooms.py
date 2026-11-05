"""Complete the Hall of Fame, Union Room, school and rooftop room."""
from collections import Counter
from pathlib import Path
import argparse
import json

import preview
from johto_remaining_review import artwork
from reverse_common import ROOT, ReverseReview
from reverse_gen2_kanto_department import Review as Interior, BLUE, RED, STONE, TIMBER

GAMES = ('firered', 'leafgreen')
OUTPUT = ROOT.parent / '.work/tileshift-v0360-final-rooms'
TARGET = ROOT / 'mappings/reverse_gen2_kanto_final_rooms.lua'
GUARDS = Path(__file__).with_name('reverse_gen2_kanto_final_rooms_guards.json')
PAIRS = {
    'league': dict(firered='building__rom_082d50dc', leafgreen='building__rom_082d50bc'),
    'school': dict(firered='building__rom_082d4f5c', leafgreen='building__rom_082d4f3c'),
}

HALL_WALL = set(range(641, 667)) | {683, 684, 691, 696, 697, 698, 699}
HALL_CONSOLE = {672, 673, 674, 675, 676, 677, 679, 680, 681, 682, 685, 687}
HALL_LIGHTS = {689, 690, 692, 693, 694}
HALL_EMBLEM = {700, 701, 702, 704, 705, 706, 707, 708, 709}
UNION_WALL = {703, 711, 712, 713, 714, 715, 716, 720, 721, 722, 723, 724}
UNION_FRAME = {717, 718, 725, 726, 727, 728, 729, 730, 731, 732, 733, 734,
               736, 737, 739, 740}
UNION_EMBLEM = {741, 742, 743, 744, 745, 746, 749, 750, 751, 752, 753, 754, 755, 756, 757}
SCHOOL_PLANTS = {641: 71, 642: 71, 649: 79, 650: 79}
SCHOOL_WALL = {643, 644, 645, 646, 647, 653, 654, 655, 661, 662, 663, 672, 673, 680, 681}
SCHOOL_BOARD = {651, 652, 659, 660}
SCHOOL_FURNITURE = {648, 656, 657, 658, 665, 666, 667, 668, 675, 676, 684, 685}
SCHOOL_MAT = {26, 27, 28, 677, 678, 679}
GREEN = [(58, 58, 58), (41, 115, 0), (99, 206, 8), (181, 255, 82)]


class Review(Interior):
    def __init__(self):
        ReverseReview.__init__(self, 'gen2-kanto-final-rooms', GAMES)
        self.out = OUTPUT
        self.layouts = {}
        self.layout_hashes = {}
        self.guards = json.loads(GUARDS.read_text(encoding='utf-8'))
        self.hall = self.gb_ref('crystal', 'HALL_OF_FAME', 43, 0)
        self.union = self.gb_ref('crystal', 'COLOSSEUM', 23, 0)
        self.school = self.gb_ref('crystal', 'CELADON_MANSION_1F', 3, 0)
        self.void = self.gb_ref('crystal', 'FAST_SHIP_CABINS_SE_SSE_CAPTAINS_CABIN', 12, 0)
        self.plants = {(row['game'], row['id']): row
                       for row in preview.read_reviewed(ROOT / 'mappings/reverse_gen2_kanto_house_completion.lua')
                       if row['style'] == 'gen2' and row['tileset'] == 'house' and row['id'] in {71, 79}}

    def recipe(self, room, game, mid, floor):
        if room == 'school' and mid in SCHOOL_PLANTS:
            previous = self.plants[game, SCHOOL_PLANTS[mid]]
            assert 'potted_tree' in previous['role']
            art = dict(sorted(artwork(previous).items()))
            art.update(base=self.school, role='reverse_gen2_final_rooms_native_planter', overMask=previous['overMask'])
            return art, 'Complete original Crystal potted plant over the selected timber floor.'
        if room == 'school' and mid in {669, 670}:
            return self.native(self.school, 'reverse_gen2_final_rooms_native_mansion_floor'), (
                'The complete original Crystal mansion flooring repeats throughout the shared room.')
        if room == 'union' and mid == 738:
            return self.native(self.union, 'reverse_gen2_final_rooms_native_link_room_floor'), (
                'Complete original Crystal cable-room floor continues through the Union Room.')
        groups = {
            'hall': ((HALL_WALL, 'hall_joined_walls_and_entry', STONE),
                     (HALL_CONSOLE, 'hall_complete_registration_console', BLUE),
                     (HALL_LIGHTS, 'hall_complete_ceremonial_lights', BLUE),
                     (HALL_EMBLEM, 'hall_complete_floor_medallion', TIMBER)),
            'union': ((UNION_WALL, 'union_joined_room_wall_and_board', RED),
                      (UNION_FRAME, 'union_complete_handed_floor_frame', GREEN),
                      (UNION_EMBLEM, 'union_complete_floor_medallion_and_entry', GREEN)),
            'school': ((SCHOOL_WALL, 'school_complete_window_and_wall', TIMBER),
                       (SCHOOL_BOARD, 'school_complete_green_chalkboard', GREEN),
                       (SCHOOL_FURNITURE, 'school_joined_desk_and_bookcase', TIMBER),
                       (SCHOOL_MAT, 'school_joined_entry_mat', RED)),
        }
        base = {'hall': self.hall, 'union': self.union, 'school': self.school}[room]
        if room == 'school' and mid in {26, 27, 28}:
            base, floor = self.void, {(0, 0, 0)}
        for ids, name, palette in groups[room]:
            if mid in ids:
                return self.feature(game, mid, name, palette, base, floor), (
                    'This exact named feature preserves the complete original silhouette, alignment and priority. '
                    'Its exposed backing continues the selected Crystal material.')
        raise ValueError((room, mid))

    def build(self):
        for scope, pairs in PAIRS.items():
            self.pairs = pairs
            for game in GAMES:
                floor_ids = {'hall': 688, 'union': 738} if scope == 'league' else {'school': 670}
                floors = {name: self.colors(game, (mid,)) for name, mid in floor_ids.items()}
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
                    room = 'school' if scope == 'school' else 'union' if item['contexts'][0]['map'].endswith('UNION_ROOM') else 'hall'
                    art, evidence = self.recipe(room, game, mid, floors[room])
                    if art['kind'] != 'classic_native_geometry':
                        art.setdefault('overMask', '0' * 256)
                    self.row(game, pair, mid, 'gen2', art, evidence)
        assert len(self.rows) == len(self.guards)
        assert Counter(game for game, _, _, _, _ in self.rows) == Counter({game: 146 for game in GAMES})


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
