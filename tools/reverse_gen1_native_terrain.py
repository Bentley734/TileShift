"""Author native Red terrain for exact reviewed classic material references."""
from collections import Counter
from pathlib import Path
import argparse
import json

from coverage import active_rows
from johto_remaining_review import artwork
from reverse_common import ROOT, ReverseReview


GAMES = ('firered', 'leafgreen', 'ruby', 'sapphire', 'emerald')
OUT = ROOT.parent / '.work/tileshift-reverse-gen1-native-terrain'
GUARDS = Path(__file__).with_name('reverse_gen1_native_terrain_guards.json')
TERRAIN = {
    ('PALLET_TOWN', 1, 0): ('PALLET_TOWN', 1, 0),
    ('PALLET_TOWN', 1, 2): ('PALLET_TOWN', 1, 2),
    ('CIANWOOD_CITY', 1, 0): ('PALLET_TOWN', 1, 2),
    ('SAFFRON_CITY', 119, 0): ('PALLET_TOWN', 1, 2),
}
TRANSPARENT = '5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6ef'


def ref_key(ref):
    return ref.get('map'), ref.get('id'), ref.get('quadrant')


class Review(ReverseReview):
    def __init__(self, baseline):
        super().__init__('gen1-native-terrain', GAMES)
        self.out = OUT
        _, rows = active_rows(baseline)
        self.current = {(r['game'], r['style'], r['tileset'], r['id']): r for r in rows
                        if r['game'] in GAMES and r['style'] in ('gen1', 'gen2')}
        self.refs = {key: self.gb_ref('crystal', *key) for key in TERRAIN}
        self.materials = {key: self.gb_ref('red', *target) for key, target in TERRAIN.items()}

    def material(self, ref):
        key = ref_key(ref)
        return self.materials[key] if key in self.refs and ref == self.refs[key] else None

    def choose(self, row):
        if row.get('animated') or row.get('artOverlay') or row.get('overMask', '').strip('0'):
            return None
        if row['kind'] == 'native':
            donor = self.material(row['donor'])
            if donor:
                return self.native(donor, 'gen1_native_field_or_path_material')
        if row['kind'] == 'native_composite' and row.get('base'):
            base = self.material(row['base'])
            parts = [dict(part, donor=self.material(part['donor'])) for part in row['parts']]
            if base and all(part['donor'] and not part.get('donorStyle') for part in parts):
                return self.composite(base, parts, 'gen1_native_field_path_join')
        return None

    def inventory(self, missing, excluded):
        guards = []
        for key, use in sorted(missing.items()):
            game, pair, mid = key
            if key in excluded:
                continue
            previous = self.current.get((game, 'gen2', pair, mid))
            if previous is None or (game, 'gen1', pair, mid) in self.current:
                continue
            source = self.imp.cell_index(game)[pair, mid]
            if source['layer_sha256'].get('over') != TRANSPARENT:
                continue
            if self.choose(previous):
                guards.append(dict(game=game, pair=pair, mid=mid, cells=use['body_cells'], contexts=use['contexts'],
                                   sourceHash=source['pixel_sha256'], sourceLayers=source['layer_sha256'],
                                   sourceBehavior=source['behavior'], crystalRole=previous['role']))
        return guards

    def build(self, guards):
        for guard in guards:
            game, pair, mid = (guard[field] for field in ('game', 'pair', 'mid'))
            source = self.imp.cell_index(game)[pair, mid]
            assert source['pixel_sha256'] == guard['sourceHash']
            assert source['layer_sha256'] == guard['sourceLayers'] and source['behavior'] == guard['sourceBehavior']
            assert (game, 'gen1', pair, mid) not in self.current
            previous = self.current[game, 'gen2', pair, mid]
            assert previous['role'] == guard['crystalRole'] and previous['sourceHash'] == guard['sourceHash']
            art = self.choose(previous)
            assert art
            self.row(game, pair, mid, 'gen1', art,
                     'Exact native Red ground or path replaces the same reviewed classic material. Joined cells keep their original masks and edges.')
        assert len(self.rows) == len(guards)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, default=ROOT)
    parser.add_argument('--inventory', type=Path)
    parser.add_argument('--exclude', type=Path, action='append', default=[])
    args = parser.parse_args()
    review = Review(args.baseline)
    if args.inventory:
        entries = json.loads(args.inventory.read_text(encoding='utf-8'))['keys']
        key = lambda row: (row['game'], row['pair'], row['mid'])
        missing = {key(row): row for row in entries if row['style'] == 'gen1'}
        excluded = {key(row) for path in args.exclude for row in json.loads(path.read_text(encoding='utf-8'))}
        guards = review.inventory(missing, excluded)
        (OUT / 'draft-guards.json').write_text(json.dumps(guards, indent=2) + '\n', encoding='utf-8')
    else:
        guards = json.loads(GUARDS.read_text(encoding='utf-8'))
        review.build(guards)
        print(review.validate())
        review.write(OUT / 'candidate.lua')
    cells = Counter()
    for row in guards:
        cells[row['game']] += row['cells']
    print(len(guards), sum(cells.values()), dict(cells))


if __name__ == '__main__':
    main()
