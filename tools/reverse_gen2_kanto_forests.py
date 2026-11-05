"""Complete the shared Viridian Forest and Pattern Bush Crystal background."""
from collections import Counter
from pathlib import Path
import argparse
import json

import preview
from reverse_common import ROOT, ReverseReview
from reverse_gen2_kanto_celadon import Review as Celadon, ARCH_PALETTE
from reverse_kanto_review import runs

GAMES = ('firered', 'leafgreen')
PAIRS = dict(firered='general__rom_082d4dc4', leafgreen='general__rom_082d4da4')
OUTPUT = ROOT.parent / '.work/tileshift-v0360-forests'
TARGET = ROOT / 'mappings/reverse_gen2_kanto_forests.lua'
GUARDS = Path(__file__).with_name('reverse_gen2_kanto_forests_guards.json')
FENCES = {234, 241, 242, 243, 249, 651, 653, 678, 679}
TREES = {654, 655, 662, 670}
PATHS = {211, 262, 646, 647, 659, 660, 661, 668, 669}
FOLIAGE = [(58, 58, 58), (41, 115, 0), (99, 206, 8), (181, 255, 82)]


class Review(Celadon):
    pairs = PAIRS

    def __init__(self):
        ReverseReview.__init__(self, 'gen2-kanto-forests', GAMES)
        self.out = OUTPUT
        self.layouts = {}
        self.layout_hashes = {}
        self.guards = json.loads(GUARDS.read_text(encoding='utf-8'))
        self.ground = self.gb_at('crystal', 'ROUTE_16', 6, 3)
        self.tall = self.raw_ref('TILESET_JOHTO', (4,) * 4, 'NEW_BARK_TOWN')
        self.path = self.raw_ref('TILESET_KANTO', (48, 57, 57, 48), 'PALLET_TOWN')
        self.flowers = self.gb_at('crystal', 'ILEX_FOREST', 24, 0)
        self.sources = {}
        self.water = None
        for name in sorted({row['alias']['module'] for row in self.guards if 'alias' in row}):
            for row in preview.read_reviewed(ROOT / name):
                self.sources[row['game'], row['tileset'], row['id']] = row

    def recipe(self, item, field):
        game, mid = item['game'], item['mid']
        if 'alias' in item:
            return self.exact_alias(item), (
                'Complete native forest trail or gate section with identical original pixels, layers and behavior.')
        if mid == 93:
            ref = self.gb_at('crystal', 'ROUTE_16', 11, 7)
            return self.native(ref, 'reverse_gen2_forests_complete_native_gate_wall'), (
                'The complete Crystal brick wall repeat continues the native gate facade.')
        if mid in {641, 644}:
            return self.native(self.tall, 'reverse_gen2_forests_complete_native_encounter_grass'), (
                'Complete original Crystal encounter grass joins the surrounding tall grass.')
        if mid == 642:
            colors = {(181, 255, 82, 255), (99, 206, 8, 255), (41, 115, 0, 255)}
            pixels = list(self.gb_image(self.flowers).get_flattened_data())
            assert any(r > g + 40 for r, g, _, _ in pixels)
            mask = [p not in colors for p in pixels]
            assert 0 < sum(mask) < 256
            parts = [dict(donor=self.flowers, srcX=p['x'], srcY=p['y'], **p) for p in runs(mask)]
            return self.composite(self.ground, parts, 'reverse_gen2_forests_complete_native_flowers'), (
                'Whole original Crystal Ilex flowers sit over the selected forest ground.')
        if mid in PATHS:
            return self.native(self.path, 'reverse_gen2_forests_complete_native_trail'), (
                'Complete original Crystal dirt continues the wooded walking trail.')
        if mid in TREES:
            feature, palette = 'forest_complete_tree_foliage_join', FOLIAGE
        elif mid in FENCES:
            feature, palette = 'forest_joined_handed_wooden_posts', ARCH_PALETTE
        else:
            assert mid in {643, 652}, mid
            feature, palette = 'forest_complete_brick_and_tree_boundary', ARCH_PALETTE
        return self.shape(game, mid, feature, palette, self.ground, field), (
            'The complete named forest boundary retains its original contour and priority. '
            'Exact exterior grass pixels show the same native ground as neighboring cells.')

    def build(self):
        for game in GAMES:
            field = self.source_colors(game, (1, 8, 9, 16, 17))
            for item in self.guards:
                if item['game'] != game:
                    continue
                pair, mid = item['pair'], item['mid']
                assert pair == PAIRS[game] and (game, pair, mid) not in self.sources
                source = self.imp.cell_index(game)[pair, mid]
                assert (source['pixel_sha256'], source['layer_sha256'], source['behavior']) == (
                    item['sourceHash'], item['sourceLayers'], item['sourceBehavior'])
                for use in item['contexts']:
                    layout = self.native_layout(game, use['map'])
                    assert layout['pair'] == pair and layout['mids'].count(mid) == use['cells']
                art, evidence = self.recipe(item, field)
                if art['kind'] != 'classic_native_geometry':
                    art.setdefault('overMask', '0' * 256)
                row = self.row(game, pair, mid, 'gen2', art, evidence)
                if 'alias' in item:
                    assert row['compositionPixelHash'] == item['alias']['output']
        assert Counter(game for game, _, _, _, _ in self.rows) == Counter({game: 65 for game in GAMES})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    review = Review()
    review.build()
    proof = review.validate()
    review.write(OUTPUT / 'candidate.lua')
    if args.activate:
        review.write(TARGET)
    print(json.dumps(dict(rows=len(review.rows), cells=sum(item['cells'] for item in review.guards),
                          proof=proof, activated=args.activate)))


if __name__ == '__main__':
    main()
