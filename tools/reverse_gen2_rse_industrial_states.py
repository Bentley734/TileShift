"""Build the reviewed Hoenn machinery, household, and curtain state swaps."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import catalog
from reverse_common import ROOT
from reverse_gen2_rse_scripted_interiors import Review as InteriorReview


TARGET = ROOT / 'mappings/reverse_gen2_rse_industrial_states.lua'
GUARDS = Path(__file__).with_name('reverse_gen2_rse_industrial_states_guards.json')
PAIRS = {
    'general__bike_shop': {591, 617, 625, 641, 753, 754, 756, 757, 758, 759},
    'general__facility': {788, 789, 790, 796, 797, 798},
    'building__brendans_mays_house': {616, 624, 659},
}
CURTAIN = {513, 514, 515, 521, 523, 545, 546, 547, 553, 555, 577, 578, 579, 585, 587}


class Review(InteriorReview):
    def __init__(self):
        super().__init__()
        self.out = ROOT.parent / '.work/tileshift-reverse-rse-industrial-states'
        self.out.mkdir(parents=True, exist_ok=True)

    def verify_context(self, game, pair, mid, context):
        super().verify_context(game, pair, mid, context)
        origin = context['origin']['kind']
        if origin == 'script':
            return
        assert origin == 'pike_curtain' and game == 'emerald' and pair == 'building__battle_pike'
        px, py = context['trigger']
        column, row = context['x'] - px + 1, context['y'] - py + 3
        assert 0 <= column < 3 and 0 <= row < 4 and 0 <= context['frame'] < 3
        assert mid == 513 + column + 8 * row + 32 * context['frame']
        assert not context['impassable']


def build(review):
    doc = json.loads(GUARDS.read_text(encoding='utf-8'))
    assert doc['format'] == 1
    expected_keys = {(game, pair, mid) for game in review.games for pair, mids in PAIRS.items() for mid in mids}
    expected_keys.update(('emerald', 'building__battle_pike', mid) for mid in CURTAIN)
    expected_keys.add(('emerald', 'general__facility', 996))
    keys = []
    witnesses = []
    for saved in doc['sources']:
        game, pair, mid = saved['game'], saved['pair'], saved['mid']
        source, _, _ = review.source_data(game, pair, mid)
        assert (source['pixel_sha256'], source.get('behavior'), source['layer_sha256']) == (
            saved['sourceHash'], saved['sourceBehavior'], saved['sourceLayers'])
        for context in saved['contexts']:
            review.verify_context(game, pair, mid, context)
        row = review.row(game, pair, mid, 'gen2', saved['recipe'], saved['review'])
        assert row['compositionPixelHash'] == saved['expectedOutputHash'], (game, pair, mid)
        identity = dict(game=game, pair=pair, mid=mid)
        keys.append(identity)
        witness = saved['contexts'][0]
        witnesses.append(dict(identity, **{field: witness[field] for field in
                                          ('map', 'x', 'y', 'before_mid', 'impassable')}))
    assert {(key['game'], key['pair'], key['mid']) for key in keys} == expected_keys
    assert len(review.rows) == len(keys) == len(expected_keys)
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
    (review.out / 'keys.json').write_text(json.dumps(keys, indent=2) + '\n', encoding='utf-8')
    (review.out / 'script-witnesses.json').write_text(json.dumps(witnesses, indent=2) + '\n', encoding='utf-8')
    report = dict(new_keys=len(keys), logical_cells_added=0, neutral=neutral,
                  source_map_variants=len(doc['layoutHashes']), sha256=catalog.sha(candidate.read_bytes()))
    (review.out / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
