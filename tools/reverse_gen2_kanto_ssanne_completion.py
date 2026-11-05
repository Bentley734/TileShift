"""Build reviewed Crystal counterparts for FireRed and LeafGreen S.S. Anne rooms and decks."""

from reverse_gen2_kanto_house_completion import Review as KantoInteriorReview, ROOT, run_review


PAIRS = {'firered': 'general__rom_082d4d94', 'leafgreen': 'general__rom_082d4d74'}
TARGET = ROOT / 'mappings/reverse_gen2_kanto_ssanne_completion.lua'
GUARDS = ROOT / 'tools/reverse_gen2_kanto_ssanne_completion_guards.json'
OUT = ROOT.parent / '.work/tileshift-v0360-kanto-ssanne-completion'


class Review(KantoInteriorReview):
    mapping_path = TARGET
    guards_path = GUARDS
    output_path = OUT
    proof_key = 'kantoSSAnneCompletion'

    def accepts_pair(self, pair):
        return pair in PAIRS.values()


if __name__ == '__main__':
    run_review(Review, __doc__)
