"""Build the remaining explicitly reviewed RSE cave tile replacements."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import zlib
from collections import Counter, defaultdict

from classic_geometry_review import art as classic_art
import preview
from reverse_common import ROOT, ReverseReview


PAIR = 'general__cave'
GAMES = ('ruby', 'sapphire', 'emerald')
TARGET = ROOT / 'mappings/reverse_gen2_hoenn_cave_completion.lua'
GUARDS = ROOT / 'tools/reverse_gen2_hoenn_cave_completion_guards.json'
OUT = ROOT.parent / '.work/tileshift-v0360-hoenn-cave-completion'


def sha(value):
    return hashlib.sha256(value).hexdigest()


class Review(ReverseReview):
    def __init__(self):
        super().__init__('gen2-hoenn-cave-completion', GAMES)
        self.out = OUT
        self.out.mkdir(parents=True, exist_ok=True)
        self.active = {}
        modules = dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]", (ROOT / 'main.lua').read_text()))
        modules['mappings/reverse_gen2_hoenn_outdoor_remaining.lua'] = None
        for module in modules:
            path = ROOT / module
            if path == TARGET or not path.exists():
                continue
            for row in preview.read_reviewed(path):
                if row['game'] not in GAMES or row['style'] != 'gen2' or row.get('map'):
                    continue
                key = row['game'], row['tileset'], row['id']
                if row['tileset'] == PAIR:
                    assert key not in self.active
                    self.active[key] = row
        self.used, self.headers = Counter(), Counter()
        self.contexts = defaultdict(Counter)
        self.maps = []
        for game in GAMES:
            manifest = self.imp.table(game, 'gba/native/manifest')['layouts']
            for name, spec in sorted(manifest.items()):
                if spec['pair'] != PAIR:
                    continue
                raw = (self.cache / game / 'data/generated/gba/native' / spec['file']).read_bytes()
                blob = raw if raw[:4] == b'SVML' else zlib.decompress(raw)
                assert blob[:4] == b'SVML'
                stride, rows, width, height = struct.unpack_from('<HHHH', blob, 6)
                width, height = width or stride, height or rows
                border_count = blob[14] * blob[15]
                offset = 16 + border_count * 2
                mids = [struct.unpack_from('<H', blob, offset + (y * stride + x) * 4)[0]
                        for y in range(height) for x in range(width)]
                for mid in mids:
                    self.used[game, PAIR, mid] += 1
                    self.contexts[game, PAIR, mid][name] += 1
                for mid in struct.unpack_from(f'<{border_count}H', blob, 16):
                    self.headers[game, PAIR, mid] += 1
                self.maps.append(dict(game=game, pair=PAIR, map=name, file=spec['file'], width=width,
                                      height=height, mids=mids, layout_sha256=sha(raw)))

    def render(self, row):
        return preview.replacement_image(self.cache, row, self.packed, ROOT)

    def layouts(self):
        return {f"{m['game']}/{m['file']}": m['layout_sha256'] for m in self.maps}

    def inventory(self):
        result = []
        for key, occurrences in sorted(self.used.items()):
            if key in self.active:
                continue
            game, pair, mid = key
            source = self.imp.cell_index(game).get((pair, mid))
            if source is not None:
                result.append(dict(game=game, pair=pair, id=mid, sourceHash=source['pixel_sha256'],
                                   sourceBehavior=source.get('behavior'), layer_sha256=source['layer_sha256'],
                                   body_cells=occurrences, header_cells=self.headers[key],
                                   source_maps=dict(self.contexts[key])))
        (self.out / 'cave-source-keys.json').write_text(json.dumps(result, indent=2) + '\n')
        return result

    def build(self):
        document = json.loads(GUARDS.read_text())
        assert document['format'] == 1 and document['layout_sha256'] == self.layouts()
        for contract in document['sources']:
            game, pair, mid = contract['game'], contract['pair'], contract['id']
            key = game, pair, mid
            assert pair == PAIR and key not in self.active
            source = self.imp.cell_index(game)[pair, mid]
            assert source['pixel_sha256'] == contract['sourceHash'] and source.get('behavior') == contract['sourceBehavior']
            assert source['layer_sha256'] == contract['layer_sha256']
            assert self.used[key] == contract['body_cells'] and self.headers[key] == contract['header_cells']
            assert dict(self.contexts[key]) == contract['source_maps']
            if 'art' in contract:
                recipe = contract['art']
            else:
                colors = {tuple(row[:3]): tuple(row[3:]) for row in contract['colorMap']}
                recipe = classic_art(self, game, pair, mid, contract['feature'], contract['palette'], colors,
                                     ground=contract.get('ground'), source_animation=contract.get('sourceAnimation'))
                assert recipe['classicGeometry']['animationManifestHash'] == contract['animationManifestHash']
            row = self.row(game, pair, mid, 'gen2', recipe, contract['review'])
            assert row['compositionPixelHash'] == contract['expected_output_sha256']
            if 'expected_phase_sha256' in contract:
                assert [sha(frame.tobytes()) for frame in preview.replacement_frames(self.cache, row, self.packed, ROOT)] == contract['expected_phase_sha256']
            row['hoennCaveCompletion'] = dict(namedFeature=contract['feature'], bodyOccurrences=contract['body_cells'],
                                              sourceContexts=sorted(contract['source_maps']))
        self.rows = dict(sorted(self.rows.items()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    assert not args.activate or args.build
    review = Review()
    inventory = review.inventory()
    report = dict(missing_keys=len(inventory), missing_cells=sum(row['body_cells'] for row in inventory))
    if args.build:
        review.build()
        review.write(review.out / 'candidate.lua')
        report['neutral'] = review.validate()
        rows = list(review.rows.values())
        report.update(new_keys=len(rows), new_cells=sum(row['hoennCaveCompletion']['bodyOccurrences'] for row in rows))
        if args.activate:
            review.write(TARGET)
            report['sha256'] = sha(TARGET.read_bytes())
    (review.out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
