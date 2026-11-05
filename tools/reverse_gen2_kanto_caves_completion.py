"""Build reviewed Crystal counterparts for Rock Tunnel, Altering Cave, and Cerulean Cave."""

from reverse_gen2_kanto_house_completion import Review as KantoInteriorReview, ROOT, run_review


PAIR_FAMILIES = {
    'rock_tunnel': ('general__rom_082d4df4', 'general__rom_082d4dd4'),
    'cerulean_cave': ('general__rom_082d4e54', 'general__rom_082d4e34'),
}
PAIRS = {pair for sources in PAIR_FAMILIES.values() for pair in sources}
TARGET = ROOT / 'mappings/reverse_gen2_kanto_caves_completion.lua'
GUARDS = ROOT / 'tools/reverse_gen2_kanto_caves_completion_guards.json'
OUT = ROOT.parent / '.work/tileshift-v0360-kanto-caves-completion'


class Review(KantoInteriorReview):
    mapping_path = TARGET
    guards_path = GUARDS
    output_path = OUT
    proof_key = 'kantoCavesCompletion'

    def accepts_pair(self, pair):
        return pair in PAIRS


if __name__ == '__main__':
    run_review(Review, __doc__)
