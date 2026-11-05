"""Build complete, reviewed FireRed and LeafGreen house and gate counterparts."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections import Counter

from classic_geometry_review import art as classic_art
import preview
import reverse_gen2_kanto_final as kanto_final
from reverse_gen2_kanto_final import Final, ROOT


PAIR = 'house'
TARGET = ROOT / 'mappings/reverse_gen2_kanto_house_completion.lua'
GUARDS = ROOT / 'tools/reverse_gen2_kanto_house_completion_guards.json'
OUT = ROOT.parent / '.work/tileshift-v0360-kanto-house-completion'


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Review(Final):
    def __init__(self):
        super().__init__()
        self.out = OUT
        self.out.mkdir(parents=True, exist_ok=True)
        own_module = TARGET.relative_to(ROOT).as_posix()
        self.current = {key: row for key, row in self.current.items() if self.origins[id(row)][0] != own_module}
        source = kanto_final.DECISIONS
        approved = json.loads(source.read_text())
        scoped = dict(format=approved['format'], aliases=[], forest=[])
        for alias in approved['aliases']:
            targets = [target for target in alias['targets'] if target['pair'] == PAIR]
            if targets:
                scoped['aliases'].append(dict(copy.deepcopy(alias), targets=targets))
        for section in ('geometry', 'native_modules', 'native_objects'):
            scoped[section] = [row for row in approved.get(section, []) if row['pair'] == PAIR]
        baseline_decisions = self.out / 'approved-house-baseline-decisions.json'
        baseline_decisions.write_text(json.dumps(scoped, indent=2) + '\n')
        kanto_final.DECISIONS = baseline_decisions
        try:
            self.stage()
        finally:
            kanto_final.DECISIONS = source
        self.baseline = {key: row for key, row in (self.current | self.rows).items() if key[2] == PAIR}
        self.rows = {}
        self.maps = [dict(m, mids=self.layouts[m['game'], m['map']][1]['mids'],
                          file=self.layouts[m['game'], m['map']][0]['file']) for m in self.maps if m['pair'] == PAIR]
        self.layouts_sha256 = {f"{m['game']}/{m['file']}": sha((self.cache / m['game'] /
            'data/generated/gba/native' / m['file']).read_bytes()) for m in self.maps}
        self.active = {(game, pair, mid): row for (game, _, pair, mid, _), row in self.baseline.items()}

    def render(self, row):
        return preview.replacement_image(self.cache, row, self.packed, ROOT)

    def inventory(self):
        result = []
        for key, uses in sorted(self.usage.items()):
            game, pair, mid = key
            count = sum(use['count'] for use in uses)
            if not count or pair != PAIR or key in self.active:
                continue
            cell = self.imp.cell_index(game)[pair, mid]
            result.append(dict(game=game, pair=pair, id=mid, sourceHash=cell['pixel_sha256'],
                               sourceBehavior=cell.get('behavior'), layer_sha256=cell['layer_sha256'],
                               body_cells=count, header_cells=sum(bool(use.get('border')) for use in uses),
                               source_maps={use['map']: use['count'] for use in uses if use['count']}))
        (self.out / 'source-inventory.json').write_text(json.dumps(result, indent=2) + '\n')
        return result

    def build(self):
        guards = json.loads(GUARDS.read_text())
        assert guards['format'] == 1 and guards['layout_sha256'] == self.layouts_sha256
        current = {(s['game'], s['pair'], s['id']): s for s in self.inventory()}
        for contract in guards['sources']:
            game, pair, mid = key = contract['game'], contract['pair'], contract['id']
            assert pair == PAIR and key not in self.active
            for name, value in current[key].items():
                assert value == contract[name]
            if 'art' in contract:
                recipe = contract['art']
            else:
                colors = {tuple(e[:3]): tuple(e[3:]) for e in contract['colorMap']}
                recipe = classic_art(self, game, pair, mid, contract['feature'], contract['palette'], colors,
                                     ground=contract.get('ground'), source_animation=contract.get('sourceAnimation'))
                assert recipe['classicGeometry']['animationManifestHash'] == contract['animationManifestHash']
            row = self.row(game, pair, mid, 'gen2', recipe, contract['review'])
            assert row['compositionPixelHash'] == contract['expected_output_sha256']
            row['kantoHouseCompletion'] = dict(feature=contract['feature'], actualBodyOccurrences=contract['body_cells'],
                                              exactSourceContexts=sorted(contract['source_maps']))
        self.rows = dict(sorted(self.rows.items()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    assert not args.activate or args.build
    review = Review()
    inventory = review.inventory()
    report = dict(missing_keys=len(inventory), missing_cells=sum(row['body_cells'] for row in inventory),
                  affected_maps=len({(r['game'], name) for r in inventory for name in r['source_maps']}))
    if args.build:
        review.build()
        review.write(review.out / 'candidate.lua')
        report['neutral'] = review.validate()
        rows = list(review.rows.values())
        report.update(new_keys=len(rows), new_cells=sum(row['kantoHouseCompletion']['actualBodyOccurrences'] for row in rows))
        if args.activate:
            review.write(TARGET)
            report['sha256'] = sha(TARGET.read_bytes())
    (review.out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
