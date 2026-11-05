"""Build reviewed Crystal counterparts for FireRed and LeafGreen Poke Mart interiors."""

from reverse_gen2_kanto_house_completion import Review as KantoInteriorReview, ROOT, run_review


PAIRS = {'firered': 'building__rom_082d4bcc', 'leafgreen': 'building__rom_082d4bac'}
TARGET = ROOT / 'mappings/reverse_gen2_kanto_marts_completion.lua'
GUARDS = ROOT / 'tools/reverse_gen2_kanto_marts_completion_guards.json'
OUT = ROOT.parent / '.work/tileshift-v0360-kanto-marts-completion'


class Review(KantoInteriorReview):
    mapping_path = TARGET
    guards_path = GUARDS
    output_path = OUT
    proof_key = 'kantoMartsCompletion'

    def accepts_pair(self, pair):
        return pair in PAIRS.values()


if __name__ == '__main__':
    run_review(Review, __doc__)
