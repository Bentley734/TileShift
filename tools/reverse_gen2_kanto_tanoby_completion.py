"""Build reviewed Crystal counterparts for FireRed and LeafGreen Tanoby chambers."""

from reverse_gen2_kanto_house_completion import Review as KantoInteriorReview, ROOT, run_review


PAIRS = {'firered': 'building__rom_082d5034', 'leafgreen': 'building__rom_082d5014'}
TARGET = ROOT / 'mappings/reverse_gen2_kanto_tanoby_completion.lua'
GUARDS = ROOT / 'tools/reverse_gen2_kanto_tanoby_completion_guards.json'
OUT = ROOT.parent / '.work/tileshift-v0360-kanto-tanoby-completion'


class Review(KantoInteriorReview):
    mapping_path = TARGET
    guards_path = GUARDS
    output_path = OUT
    proof_key = 'kantoTanobyCompletion'

    def accepts_pair(self, pair):
        return pair in PAIRS.values()


if __name__ == '__main__':
    run_review(Review, __doc__)
