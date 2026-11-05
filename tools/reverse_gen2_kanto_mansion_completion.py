"""Build reviewed Crystal counterparts for all FireRed and LeafGreen Pokemon Mansion floors."""

from reverse_gen2_kanto_house_completion import Review as KantoInteriorReview, ROOT, run_review


PAIRS = {'firered': 'building__rom_082d4f2c', 'leafgreen': 'building__rom_082d4f0c'}
TARGET = ROOT / 'mappings/reverse_gen2_kanto_mansion_completion.lua'
GUARDS = ROOT / 'tools/reverse_gen2_kanto_mansion_completion_guards.json'
OUT = ROOT.parent / '.work/tileshift-v0360-kanto-mansion-completion'


class Review(KantoInteriorReview):
    mapping_path = TARGET
    guards_path = GUARDS
    output_path = OUT
    proof_key = 'kantoMansionCompletion'

    def accepts_pair(self, pair):
        return pair in PAIRS.values()


if __name__ == '__main__':
    run_review(Review, __doc__)
