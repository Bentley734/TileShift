"""Build reviewed Crystal counterparts for both FireRed and LeafGreen Underground Path tunnels."""

from reverse_gen2_kanto_house_completion import Review as KantoInteriorReview, ROOT, run_review


PAIRS = {'firered': 'building__rom_082d4ee4', 'leafgreen': 'building__rom_082d4ec4'}
TARGET = ROOT / 'mappings/reverse_gen2_kanto_tunnels_completion.lua'
GUARDS = ROOT / 'tools/reverse_gen2_kanto_tunnels_completion_guards.json'
OUT = ROOT.parent / '.work/tileshift-v0360-kanto-tunnels-completion'


class Review(KantoInteriorReview):
    mapping_path = TARGET
    guards_path = GUARDS
    output_path = OUT
    proof_key = 'kantoTunnelsCompletion'

    def accepts_pair(self, pair):
        return pair in PAIRS.values()


if __name__ == '__main__':
    run_review(Review, __doc__)
