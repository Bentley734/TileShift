"""Build reviewed Crystal counterparts for the FireRed and LeafGreen labs, museum, and exhibit houses."""

from reverse_gen2_kanto_house_completion import Review as KantoInteriorReview, ROOT, run_review


PAIR_FAMILIES = {
    'lab': ('oak_lab', 'oak_lab'),
    'museum': ('building__rom_082d4c2c', 'building__rom_082d4c0c'),
}
PAIRS = {pair for sources in PAIR_FAMILIES.values() for pair in sources}
TARGET = ROOT / 'mappings/reverse_gen2_kanto_labs_museum_completion.lua'
GUARDS = ROOT / 'tools/reverse_gen2_kanto_labs_museum_completion_guards.json'
OUT = ROOT.parent / '.work/tileshift-v0360-kanto-labs-museum-completion'


class Review(KantoInteriorReview):
    mapping_path = TARGET
    guards_path = GUARDS
    output_path = OUT
    proof_key = 'kantoLabsMuseumCompletion'

    def accepts_pair(self, pair):
        return pair in PAIRS


if __name__ == '__main__':
    run_review(Review, __doc__)
