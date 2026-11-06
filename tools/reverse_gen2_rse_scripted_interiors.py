"""Build reviewed Crystal counterparts for literal Hoenn interior state changes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import catalog
import preview
from reverse_common import ROOT, ReverseReview
from reverse_gen1_native_service_rooms import read_layout


GAMES = ('emerald', 'ruby', 'sapphire')
TARGET = ROOT / 'mappings/reverse_gen2_rse_scripted_interiors.lua'
GUARDS = Path(__file__).with_name('reverse_gen2_rse_scripted_interiors_guards.json')


class Review(ReverseReview):
    def __init__(self):
        super().__init__('rse-interior-scripted-states', GAMES)
        self.sources = {}
        self.scripts = {}

    def source_data(self, game, pair, mid):
        source = self.imp.cell_index(game)[pair, mid]
        preview.native_donor(self.cache, dict(game=game, tileset=pair, id=mid, hash=source['pixel_sha256']), self.packed)
        mids, palette, planes = self.packed[game, pair]
        offset = mids.index(mid) * 256
        return source, palette, {name: values[offset:offset + 256] for name, values in planes.items()}

    def layout(self, game, name):
        key = game, name
        if key not in self.sources:
            native = self.cache / game / 'data/generated/gba/native'
            definition = self.imp.table(game, 'gba/native/manifest')['layouts'][name]
            self.sources[key] = definition['pair'], read_layout(native / definition['file'])
        return self.sources[key]

    def verify_context(self, game, pair, mid, context):
        name, x, y = context['map'], context['x'], context['y']
        actual_pair, (width, height, mids, _) = self.layout(game, name)
        assert actual_pair == pair and 0 <= x < width and 0 <= y < height, context
        assert mids[y * width + x] == context['before_mid'] and mid not in mids, context
        origin = context['origin']
        if origin['kind'] == 'script':
            if game not in self.scripts:
                self.scripts[game] = catalog.read_lua(self.cache / game / 'data/generated/gba/scripts/scripts.lua')
            command = self.scripts[game][origin['script']][origin['index']]
            operands = origin['operands']
            assert command['op'] == 'setmetatile' and [command[str(i)] for i in range(1, 5)] == operands
            assert operands[:3] == [x, y, mid] and bool(operands[3]) == context['impassable']


def build(review):
    doc = json.loads(GUARDS.read_text())
    assert doc['format'] == 1
    witnesses = []
    keys = []
    for saved in doc['sources']:
        game, pair, mid = saved['game'], saved['pair'], saved['mid']
        assert pair.startswith('building__')
        source, _, _ = review.source_data(game, pair, mid)
        assert (source['pixel_sha256'], source.get('behavior'), source['layer_sha256']) == (
            saved['sourceHash'], saved['sourceBehavior'], saved['sourceLayers'])
        for context in saved['contexts']:
            review.verify_context(game, pair, mid, context)
        row = review.row(game, pair, mid, 'gen2', saved['recipe'], saved['review'])
        assert row['compositionPixelHash'] == saved['expectedOutputHash'], (game, pair, mid)
        if saved.get('expectedPhaseHashes'):
            frames = preview.classic_geometry_frames(review.cache, row, review.packed)
            assert [catalog.sha(frame.tobytes()) for frame in frames] == saved['expectedPhaseHashes']
        identity = dict(game=game, pair=pair, mid=mid)
        keys.append(identity)
        witness = next(c for c in saved['contexts'] if c['origin']['kind'] == 'script')
        witnesses.append(dict(identity, **{field: witness[field]
                                          for field in ('map', 'x', 'y', 'before_mid', 'impassable')}))
    assert len(review.rows) == len(keys)
    actual_hashes = {f'{game}/{name}': value[1][3] for (game, name), value in review.sources.items()}
    assert actual_hashes == doc['layoutHashes']
    return doc, keys, witnesses


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    review = Review()
    doc, keys, witnesses = build(review)
    neutral = review.validate()
    assert neutral['accepted']['gen2'] == len(keys) and not neutral['rejected'], neutral
    candidate = review.out / TARGET.name
    review.write(candidate)
    if args.activate:
        TARGET.write_bytes(candidate.read_bytes())
    (review.out / 'keys.json').write_text(json.dumps(keys, indent=2) + '\n')
    (review.out / 'script-witnesses.json').write_text(json.dumps(witnesses, indent=2) + '\n')
    report = dict(new_keys=len(keys), logical_cells_added=0, neutral=neutral,
                  source_map_variants=len(doc['layoutHashes']), sha256=catalog.sha(candidate.read_bytes()),
                  original_phase_samples=sum(len(r.get('expectedPhaseHashes', ())) for r in doc['sources']))
    (review.out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
