"""Build reviewed Crystal counterparts for the remaining FireRed and LeafGreen gym interiors."""

from reverse_gen2_kanto_house_completion import Review as KantoInteriorReview, ROOT, run_review


PAIR_FAMILIES = {
    'viridian': ('building__rom_082d4cbc', 'building__rom_082d4c9c'),
    'cerulean': ('building__rom_082d4d1c', 'building__rom_082d4cfc'),
    'vermilion': ('building__rom_082d4d34', 'building__rom_082d4d14'),
    'celadon': ('building__rom_082d4d4c', 'building__rom_082d4d2c'),
    'saffron': ('building__rom_082d4d64', 'building__rom_082d4d44'),
    'cinnabar': ('building__rom_082d4d7c', 'building__rom_082d4d5c'),
    'pewter': ('pewter_gym', 'pewter_gym'),
}
PAIRS = {pair for sources in PAIR_FAMILIES.values() for pair in sources}
TARGET = ROOT / 'mappings/reverse_gen2_kanto_gyms_completion.lua'
GUARDS = ROOT / 'tools/reverse_gen2_kanto_gyms_completion_guards.json'
OUT = ROOT.parent / '.work/tileshift-v0360-kanto-gyms-completion'


class Review(KantoInteriorReview):
    mapping_path = TARGET
    guards_path = GUARDS
    output_path = OUT
    proof_key = 'kantoGymsCompletion'

    def accepts_pair(self, pair):
        return pair in PAIRS


if __name__ == '__main__':
    run_review(Review, __doc__)
