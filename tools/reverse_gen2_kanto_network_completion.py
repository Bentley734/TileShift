"""Build complete, reviewed FireRed and LeafGreen clinic and network fixtures."""

from reverse_gen2_kanto_house_completion import Review as KantoInteriorReview, ROOT, run_review


PAIR = 'network'
TARGET = ROOT / 'mappings/reverse_gen2_kanto_network_completion.lua'
GUARDS = ROOT / 'tools/reverse_gen2_kanto_network_completion_guards.json'
OUT = ROOT.parent / '.work/tileshift-v0360-kanto-network-completion'


class Review(KantoInteriorReview):
    source_pair = PAIR
    mapping_path = TARGET
    guards_path = GUARDS
    output_path = OUT
    proof_key = 'kantoNetworkCompletion'


if __name__ == '__main__':
    run_review(Review, __doc__)
