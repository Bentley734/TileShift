"""Build reviewed Crystal counterparts for the remaining regional FireRed and LeafGreen cave tiles."""

from reverse_gen2_kanto_house_completion import Review as KantoInteriorReview, ROOT, run_review


PAIR_FAMILIES = {
    'moon_victory': ('general__rom_082d4bfc', 'general__rom_082d4bdc'),
    'seafoam_icefall': ('general__rom_082d4e24', 'general__rom_082d4e04'),
    'diglett_tanoby': ('general__rom_082d4e0c', 'general__rom_082d4dec'),
}
PAIRS = {pair for sources in PAIR_FAMILIES.values() for pair in sources}
TARGET = ROOT / 'mappings/reverse_gen2_kanto_regional_caves_completion.lua'
GUARDS = ROOT / 'tools/reverse_gen2_kanto_regional_caves_completion_guards.json'
OUT = ROOT.parent / '.work/tileshift-v0360-kanto-regional-caves-completion'


class Review(KantoInteriorReview):
    mapping_path = TARGET
    guards_path = GUARDS
    output_path = OUT
    proof_key = 'kantoRegionalCavesCompletion'

    def accepts_pair(self, pair):
        return pair in PAIRS


if __name__ == '__main__':
    run_review(Review, __doc__)
