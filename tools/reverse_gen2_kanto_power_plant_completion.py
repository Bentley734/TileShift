"""Build reviewed Crystal counterparts for the FireRed and LeafGreen Power Plant."""

from reverse_gen2_kanto_house_completion import Review as KantoInteriorReview, ROOT, run_review


PAIRS = {'firered': 'building__rom_082d4e9c', 'leafgreen': 'building__rom_082d4e7c'}
TARGET = ROOT / 'mappings/reverse_gen2_kanto_power_plant_completion.lua'
GUARDS = ROOT / 'tools/reverse_gen2_kanto_power_plant_completion_guards.json'
OUT = ROOT.parent / '.work/tileshift-v0360-kanto-power-plant-completion'


class Review(KantoInteriorReview):
    mapping_path = TARGET
    guards_path = GUARDS
    output_path = OUT
    proof_key = 'kantoPowerPlantCompletion'

    def accepts_pair(self, pair):
        return pair in PAIRS.values()


if __name__ == '__main__':
    run_review(Review, __doc__)
