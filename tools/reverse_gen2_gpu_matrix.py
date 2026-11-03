"""Select actual Gen3 scenes covering every used Crystal-theme source key.

This is a deterministic set-cover planner, not a validation result. Its scenes
are consumed by validate_reverse_gpu.py after the production mappings freeze.
Border-only and procedural keys are listed separately for their native probes.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import struct
import zlib

import catalog
import preview
from reverse_common import ReverseReview, ROOT
from validate_gpu import runtime_fingerprint

GAMES = ('firered', 'leafgreen', 'ruby', 'sapphire', 'emerald')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--extra-module', action='append', default=[])
    parser.add_argument('--batches', type=int, default=3)
    args = parser.parse_args()
    assert 1 <= args.batches <= 10
    args.output.mkdir(parents=True, exist_ok=True)
    inputs = runtime_fingerprint(ROOT)
    modules = list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]", (ROOT/'main.lua').read_text())))
    rows, digests = {}, {}
    for name in modules + args.extra_module:
        path = Path(name)
        if not path.is_absolute():
            path = ROOT/path
        digests[name] = catalog.sha(path.read_bytes())
        for row in preview.read_reviewed(path):
            if row['game'] not in GAMES or row['style'] != 'gen2':
                continue
            assert row.get('map') is None, 'Native GBA atlas rows must be pair-global'
            key = row['game'], row['tileset'], row['id']
            if key in rows:
                assert name in args.extra_module, 'Duplicate registered Crystal source key'
                assert rows[key]['sourceHash'] == row['sourceHash']
                assert rows[key].get('sourceBehavior') is None or rows[key]['sourceBehavior'] == row.get('sourceBehavior')
            rows[key] = row
    f = ReverseReview('gen2-gpu-matrix', GAMES)
    maps, used = [], set()
    for game in GAMES:
        cells = f.imp.cell_index(game)
        for map_id, spec in sorted(f.imp.table(game, 'gba/native/manifest')['layouts'].items()):
            raw = (f.cache/game/'data/generated/gba/native'/spec['file']).read_bytes()
            blob = raw if raw[:4] == b'SVML' else zlib.decompress(raw)
            assert blob[:4] == b'SVML'
            pw, ph, w, h = struct.unpack_from('<HHHH', blob, 6)
            w, h = w or pw, h or ph
            assert 0 < w <= pw and 0 < h <= ph
            offset = 16 + blob[14]*blob[15]*2
            counts = Counter(struct.unpack_from('<H', blob, offset+(y*pw+x)*4)[0]
                             for y in range(h) for x in range(w))
            covered = set()
            replaced = 0
            for mid, count in counts.items():
                key = game, spec['pair'], mid
                if key not in rows:
                    continue
                source = cells[spec['pair'], mid]
                assert rows[key]['sourceHash'] == source['pixel_sha256']
                covered.add(key)
                replaced += count
            used.update(covered)
            maps.append(dict(game=game, map=map_id, pair=spec['pair'], source_cells=w*h,
                             replaced_cells=replaced, complete=replaced == w*h,
                             layout_sha256=catalog.sha(raw), keys=covered))
    selected, remaining = [], set(used)
    # Keep the original completed town witnesses even if a larger route would
    # cover their shared source keys. They exercise known complete-map claims.
    anchors = {'FR_PALLET_TOWN', 'RU_LITTLEROOT_TOWN', 'SA_LITTLEROOT_TOWN',
               'EM_LITTLEROOT_TOWN', 'RU_OLDALE_TOWN', 'SA_OLDALE_TOWN', 'EM_OLDALE_TOWN'}
    for item in maps:
        if item['map'] in anchors:
            selected.append(item)
            remaining.difference_update(item['keys'])
    while remaining:
        item = max((m for m in maps if m not in selected),
                   key=lambda m: (len(m['keys'] & remaining), -m['source_cells'], m['game'], m['map']))
        assert item['keys'] & remaining, 'Used source key has no actual native map witness'
        selected.append(item)
        remaining.difference_update(item['keys'])
    assert set().union(*(m['keys'] for m in selected)) == used
    assert {m['game'] for m in selected} == set(GAMES)
    scene = lambda m: {k: m[k] for k in ('game', 'map', 'complete')}
    selected.sort(key=lambda m: (m['game'], m['map']))
    (args.output/'scenes.json').write_text(json.dumps([scene(m) for m in selected], indent=2)+'\n')
    batches = [[] for _ in range(args.batches)]
    costs = [0]*args.batches
    for item in sorted(selected, key=lambda m: (-m['source_cells'], m['game'], m['map'])):
        index = min(range(args.batches), key=lambda i: (costs[i], i))
        batches[index].append(scene(item))
        costs[index] += item['source_cells']
    for i, batch in enumerate(batches, 1):
        batch.sort(key=lambda m: (m['game'], m['map']))
        (args.output/f'scenes-{i:02}.json').write_text(json.dumps(batch, indent=2)+'\n')
    report = dict(type='actual native-map Crystal-theme GPU scene plan; not a test result',
                  runtime_inputs=inputs, module_hashes=digests, source_maps=len(maps),
                  selected_scenes=len(selected), used_source_keys=len(used), uncovered_source_keys=0,
                  scenes=[{k: v for k, v in m.items() if k != 'keys'} for m in selected],
                  non_body_keys=[dict(game=g, pair=p, id=mid) for g, p, mid in sorted(set(rows)-used)],
                  batch_source_cells=costs, per_game=dict(Counter(m['game'] for m in selected)))
    assert runtime_fingerprint(ROOT) == inputs, 'Production changed during planning'
    for name, digest in digests.items():
        path = Path(name)
        assert catalog.sha((path if path.is_absolute() else ROOT/path).read_bytes()) == digest
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: report[k] for k in ('source_maps', 'selected_scenes', 'used_source_keys', 'uncovered_source_keys', 'per_game')}))


if __name__ == '__main__':
    main()
