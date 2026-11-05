"""Build reviewed Crystal counterparts for FireRed and LeafGreen Pokemon Tower interiors."""

from reverse_gen2_kanto_house_completion import Review as KantoInteriorReview, ROOT, run_review


PAIRS = {'firered': 'building__rom_082d4efc', 'leafgreen': 'building__rom_082d4edc'}
TARGET = ROOT / 'mappings/reverse_gen2_kanto_pokemon_tower_completion.lua'
GUARDS = ROOT / 'tools/reverse_gen2_kanto_pokemon_tower_completion_guards.json'
OUT = ROOT.parent / '.work/tileshift-v0360-kanto-pokemon-tower-completion'


class Review(KantoInteriorReview):
    mapping_path = TARGET
    guards_path = GUARDS
    output_path = OUT
    proof_key = 'kantoPokemonTowerCompletion'

    def accepts_pair(self, pair):
        return pair in PAIRS.values()


if __name__ == '__main__':
    run_review(Review, __doc__)
