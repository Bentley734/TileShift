"""Author Crystal counterparts for exact Cinnabar, Joyful and Viridian script cells."""
from pathlib import Path
import argparse
import json

import preview
from classic_geometry_review import art as geometry_art
from johto_remaining_review import artwork
from reverse_common import ROOT, ReverseReview
from reverse_gen2_kanto_department import Review as Interior


GAMES = ('firered', 'leafgreen')
OUT = ROOT.parent / '.work/tileshift-frlg-script-cells'
GUARDS = Path(__file__).with_name('reverse_gen2_kanto_script_cells_guards.json')
MODULES = ('reverse_gen2_kanto_gyms_completion', 'reverse_gen2_kanto_commercial_rooms',
           'reverse_gen2_kanto_marts_completion')
STARTING_TILES = {710: 670, 711: 669, 718: 678, 719: 677, 721: 663,
                  709: 739, 737: 739, 759: 761, 703: 681, 704: 689}


class Review(Interior):
    def __init__(self, base):
        ReverseReview.__init__(self, 'gen2-kanto-script-cells', GAMES)
        self.out = OUT
        self.layouts = {}
        self.layout_hashes = {}
        self.guards = json.loads(GUARDS.read_text(encoding='utf-8'))
        self.existing = {(r['game'], r['tileset'], r['id']): r
                         for module in MODULES for r in preview.read_reviewed(base / 'mappings' / (module + '.lua'))
                         if r['style'] == 'gen2'}

    def rebuild_geometry(self, game, pair, mid, previous):
        existing = previous['classicGeometry']
        palette = existing['palette']
        literal = {tuple(entry[:3]): entry[3:] for entry in existing['colorMap']}
        source = self.planes(game, mid)
        used = {p[:3] for image in source.values() for p in image.get_flattened_data() if p[3]}
        starting_colors = tuple(literal)
        for pixel in sorted(used - literal.keys()):
            closest = min(starting_colors, key=lambda sample: sum((a - b) ** 2 for a, b in zip(sample, pixel)))
            literal[pixel] = literal[closest]
        ground = None
        if mid in {710, 711, 718, 719}:
            # All exposed floor is under the handed jamb, including the dark
            # native bottom-left threshold. The closed door's rails stay intact.
            floor = self.existing[game, pair, 669]['classicGeometry']['ground']['donor']
            exposed = ''.join('0' if p[3] else '1' for p in source['mid'].get_flattened_data())
            ground = dict(donor=floor, masks=dict(under=exposed))
        if mid == 703:
            # The alternate counter keeps the same backing where the graphics
            # are identical and retains the new counter face where they differ.
            old = self.planes(game, previous['id'])
            backing = existing['ground']
            masks = {}
            for name, mask in backing['masks'].items():
                surviving = ''.join(bit if a == b else '0' for bit, a, b in zip(
                    mask, old[name].get_flattened_data(), source[name].get_flattened_data()))
                if '1' in surviving:
                    masks[name] = surviving
            if masks:
                ground = dict(donor=backing['donor'], masks=masks)
        return geometry_art(self, game, pair, mid, previous['role'] + '_script_state', palette, literal, ground=ground)

    def build(self):
        for guard in self.guards:
            game, pair, mid, map_id = (guard[k] for k in ('game', 'pair', 'mid', 'map'))
            self.pairs = {game: pair}
            layout = self.native_layout(game, map_id)
            assert layout['pair'] == pair and mid not in layout['mids']
            assert all(layout['mids'][r['y'] * layout['width'] + r['x']] == r['before_mid'] for r in guard['origins'])
            source = self.imp.cell_index(game)
            record = source[pair, mid]
            assert all(record[field] == guard[field] for field in ('pixel_sha256', 'layer_sha256', 'behavior'))
            old_mid = STARTING_TILES[mid]
            previous = self.existing[game, pair, old_mid]
            assert previous['sourceHash'] == source[pair, old_mid]['pixel_sha256']
            if mid in {709, 737, 759}:
                assert all(record[field] == source[pair, old_mid][field] for field in ('pixel_sha256', 'layer_sha256', 'behavior'))
                art = artwork(previous)
                for name in ('classicGeometry', 'overMask'):
                    if name in previous:
                        art[name] = previous[name]
                art['role'] = previous['role'] + '_script_state'
            else:
                art = self.rebuild_geometry(game, pair, mid, previous)
            self.row(game, pair, mid, 'gen2', art,
                     'The imported script writes this guarded alternate. Its foreground geometry and backing match the surrounding Crystal artwork.')
        assert len(self.rows) == len(self.guards) == 20


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, default=ROOT)
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    review = Review(args.base)
    review.build()
    proof = review.validate()
    review.write(OUT / 'candidate.lua')
    if args.activate:
        review.write(ROOT / 'mappings/reverse_gen2_kanto_script_cells.lua')
    print(json.dumps(proof))


if __name__ == '__main__':
    main()
