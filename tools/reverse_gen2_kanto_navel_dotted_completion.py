"""Build reviewed Crystal counterparts for FireRed and LeafGreen Navel Rock and Dotted Hole."""

from reverse_gen2_kanto_house_completion import Review as KantoInteriorReview, ROOT, run_review


PAIR_FAMILIES = {
    'navel_dotted': ('general__rom_082d501c', 'general__rom_082d4ffc'),
}
PAIRS = {pair for sources in PAIR_FAMILIES.values() for pair in sources}
TARGET = ROOT / 'mappings/reverse_gen2_kanto_navel_dotted_completion.lua'
GUARDS = ROOT / 'tools/reverse_gen2_kanto_navel_dotted_completion_guards.json'
OUT = ROOT.parent / '.work/tileshift-v0360-kanto-navel-dotted-completion'


class Review(KantoInteriorReview):
    mapping_path = TARGET
    guards_path = GUARDS
    output_path = OUT
    proof_key = 'kantoNavelDottedCompletion'

    def accepts_pair(self, pair):
        return pair in PAIRS


if __name__ == '__main__':
    run_review(Review, __doc__)
