"""Build reviewed Crystal counterparts for the FireRed and LeafGreen cable rooms."""

from reverse_gen2_kanto_house_completion import Review as KantoInteriorReview, ROOT, run_review


PAIR_FAMILIES = {
    'cable_rooms': ('building__rom_082d4c44', 'building__rom_082d4c24'),
}
PAIRS = {pair for sources in PAIR_FAMILIES.values() for pair in sources}
TARGET = ROOT / 'mappings/reverse_gen2_kanto_cable_rooms_completion.lua'
GUARDS = ROOT / 'tools/reverse_gen2_kanto_cable_rooms_completion_guards.json'
OUT = ROOT.parent / '.work/tileshift-v0360-kanto-cable-rooms-completion'


class Review(KantoInteriorReview):
    mapping_path = TARGET
    guards_path = GUARDS
    output_path = OUT
    proof_key = 'kantoCableRoomsCompletion'

    def accepts_pair(self, pair):
        return pair in PAIRS


if __name__ == '__main__':
    run_review(Review, __doc__)
