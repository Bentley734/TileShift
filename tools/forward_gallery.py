"""Build a per-game comparison gallery from all-area native GPU captures.

Every source game/map stays in the index, including explicitly unrenderable
unused imports. Saved panels are verified against the actual GPU readbacks;
the archive is then read back and every comparison hash is checked again.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import html
import json
from pathlib import Path
import zipfile

from gpu_comparison import NAMES, make
from validate_gpu import runtime_fingerprint


ROOT = Path(__file__).resolve().parents[1]
GAMES = ('red', 'blue', 'yellow', 'gold', 'silver', 'crystal')


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, nargs='+', required=True)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--build', type=Path, default=ROOT / 'build')
    parser.add_argument('--allow-subset', action='store_true', help='Private pilot only; never call it the all-areas release')
    args = parser.parse_args()
    source_inventory = json.loads(args.inventory.read_text(encoding='utf-8'))
    expected = source_inventory['scenes']
    expected_keys = {(s['game'], s['map']) for s in expected}
    assert len(expected_keys) == len(expected)
    assert Counter(s['game'] for s in expected) == Counter(source_inventory['games'])
    assert len(expected) == source_inventory['total']
    inputs = runtime_fingerprint(ROOT)
    version = json.loads((ROOT / 'manifest.json').read_text())['version']
    fixtures, failures, sources = {}, {}, []
    for path in args.report:
        report = json.loads(path.read_text(encoding='utf-8'))
        assert report['status'] == 'passed' and report['theme'] == 'gen3', path
        assert report['type'] == 'native GPU all-area forward gallery capture', path
        assert report['runtime_inputs'] == inputs and report['runtime_inputs_unchanged_during_probe'], 'Runtime changed since native capture'
        assert not report['warnings']
        for fixture in report['fixtures']:
            key = fixture['game'], fixture['map']
            assert key in expected_keys and key not in fixtures and key not in failures
            for field in ('source_definition_unchanged', 'source_collision_events_unchanged', 'cleanup_restored_native'):
                assert fixture[field] is True
            assert fixture['actors_rendered'] is False
            if not fixture.get('incomplete_import_native_retained'):
                assert fixture['coverage']['preserved_native_occurrences'] == 0
            for ref in (fixture['before'], fixture['after']):
                assert digest(Path(ref['path'])) == ref['png_sha256'], 'Native PNG bytes changed'
            fixtures[key] = fixture
        for failure in report.get('unrenderable', []):
            key = failure['game'], failure['map']
            assert key in expected_keys and key not in fixtures and key not in failures
            assert key in {('gold', 'SAFARI_ZONE_BETA'), ('silver', 'SAFARI_ZONE_BETA')}
            assert failure['status'] == 'unrenderable' and failure['native_art_retained'] is True
            assert failure['source_definition_unchanged'] and failure['source_collision_events_unchanged']
            failures[key] = failure
        sources.append({'report': str(path.resolve()), 'report_sha256': digest(path),
                        'capture_checks': report['checks'], 'totals': report['totals']})
    actual_keys = set(fixtures) | set(failures)
    assert actual_keys and actual_keys <= expected_keys
    if not args.allow_subset:
        assert actual_keys == expected_keys, f'Missing gallery scenes: {sorted(expected_keys - actual_keys)}'
    args.output.mkdir(parents=True, exist_ok=True)
    args.build.mkdir(parents=True, exist_ok=True)
    comparisons, records = [], []
    for scene in expected:
        key = scene['game'], scene['map']
        if key not in actual_keys:
            continue
        record = copy.deepcopy(scene)
        if key in failures:
            failure = failures[key]
            record.update(status='unrenderable', reason=failure['reason'], native_art_retained=True,
                          note='Unused Safari beta with incomplete imported graphics; native renderer could not bake it. No replacement image was invented.')
            records.append(record)
            continue
        fixture = copy.deepcopy(fixtures[key])
        game, name = key
        directory = args.output / game
        directory.mkdir(exist_ok=True)
        title = name.replace('_', ' ').title()
        label = ('Original four-shade monochrome' if game in GAMES[:3]
                 else f"Original {game.capitalize()} native {fixture['source_daytime']} colors")
        if scene['incomplete_import_native_retained']:
            title += ' (unused beta; native art retained)'
            label += ' — incomplete unused import'
            fixture['comparison_after_label'] = 'Gen 3 selected — native beta art retained'
        else:
            fixture['comparison_after_label'] = 'Gen 3 — complete background'
        NAMES[key] = (game.capitalize() + ' / ' + title, game + '-' + name, label)
        # Explicitly label Flash-lit context rather than pretending a dark cave
        # is shown in its unlit gameplay state.
        fixture['comparison_before_label'] = label + (' (lit preview)' if game in GAMES[:3] else ' (Flash-lit where needed)')
        result = make(fixture, directory.resolve())
        target = Path(result['output'])
        result.update(output=target.relative_to(args.output.resolve()).as_posix(), actors_rendered=False,
                      source_definition_unchanged=True, source_collision_events_unchanged=True,
                      cleanup_restored_native=True, notes=fixture['notes'],
                      before_native_png_sha256=fixture['before']['png_sha256'],
                      after_native_png_sha256=fixture['after']['png_sha256'])
        comparisons.append(result)
        record.update(status='captured', output=result['output'], comparison_png_sha256=result['comparison_png_sha256'],
                      coverage=fixture['coverage'], notes=fixture['notes'])
        records.append(record)
    counts = dict(Counter(s['game'] for s in records))
    capture_counts = dict(Counter(s['game'] for s in comparisons))
    assert len({r['output'] for r in comparisons}) == len(comparisons)
    assert len(records) == len(actual_keys)
    inventory = {'total': len(records), 'games': counts, 'scenes': records,
                 'source_inventory_total': len(expected), 'source_inventory_sha256': digest(args.inventory),
                 'captured': len(comparisons), 'unrenderable': len(failures), 'complete_inventory': actual_keys == expected_keys}
    inventory_path = args.output / 'all-area-inventory.json'
    inventory_path.write_text(json.dumps(inventory, indent=2) + '\n', encoding='utf-8')
    metadata = {'status': 'passed', 'version': version, 'type': 'all-area native GPU forward comparison gallery',
                'runtime_inputs_sha256': inputs['sha256'], 'native_capture_reports': sources,
                'inventory': {'path': inventory_path.name, 'sha256': digest(inventory_path), 'total': len(records),
                              'games': counts, 'captured': capture_counts, 'unrenderable': len(failures),
                              'complete': actual_keys == expected_keys},
                'actors_rendered': False, 'pixel_scale': 2, 'resampling': 'nearest-neighbor',
                'comparisons': comparisons}
    (args.output / 'comparison-verification.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    (args.output / 'README.txt').write_text(
        f'TileShift {version} — Gen 1 and Gen 2 all-area comparisons\n\n'
        f'{len(records)} distinct cartridge/map records, {len(comparisons)} native side-by-side images.\n'
        'Open index.html, or browse the red/blue/yellow/gold/silver/crystal folders.\n'
        'Every imported area has its own index entry; images are not deduplicated.\n'
        'Left: original native GPU background. Right: selected Gen 3 background.\n'
        'Panels use exactly 2x nearest-neighbor pixels, frame zero, default flora,\n'
        'and expanded Pokemon Centers. No actors are rendered. Gen 1 is original\n'
        'four-shade monochrome; Gen 2 uses native noon/header palettes. Dark caves\n'
        'use their native lit/Flash-lit palette in both panels.\n'
        'This capture checks source definitions, collision/events and exact native\n'
        'cleanup; it does not claim a new per-pixel or interactive playthrough test.\n'
        'Unused Gold/Silver Safari beta maps have incomplete source imports and\n'
        'intentionally retain native art. If native rendering fails, their index\n'
        'records explain the error; no replacement image is invented.\n'
        'The PNG panels, image hashes and ZIP roundtrip were verified.\n', encoding='utf-8')
    parts = ['<!doctype html><meta charset="utf-8"><title>TileShift all-area comparisons</title>',
             '<style>body{font:16px system-ui;background:#18212b;color:#eee;margin:24px}a{color:#9ed5ff}li{margin:5px 0}img{max-width:100%;height:auto;image-rendering:pixelated}details{margin:8px 0}</style>',
             f'<h1>TileShift {html.escape(version)} — all Gen 1 and Gen 2 areas</h1>',
             f'<p>{len(records)} map records; {len(comparisons)} images. Original / Gen 3; no actors. Dark areas use lit background previews.</p>',
             '<p>' + ' · '.join(f'<a href="#{g}">{g.capitalize()} ({counts.get(g, 0)})</a>' for g in GAMES if counts.get(g)) + '</p>']
    for game in GAMES:
        group = [r for r in records if r['game'] == game]
        if not group:
            continue
        parts.append(f'<h2 id="{game}">{game.capitalize()} — {len(group)} areas</h2>')
        for record in group:
            name = html.escape(record['map'].replace('_', ' ').title())
            if record['status'] == 'captured':
                path = html.escape(record['output'], quote=True)
                parts.append(f'<details><summary>{name} — <a href="{path}">open image</a></summary><img loading="lazy" src="{path}" alt="{name}: original and Gen 3"></details>')
            else:
                parts.append(f'<details><summary>{name} — unused beta; native renderer unavailable</summary><p>{html.escape(record["note"])}</p><pre>{html.escape(record["reason"])}</pre></details>')
    (args.output / 'index.html').write_text('\n'.join(parts) + '\n', encoding='utf-8')
    series = 'Pilot-' if args.allow_subset else ''
    archive = args.build / f'TileShift-{series}Gen1-Gen2-All-Areas-Comparisons-v{version}.zip'
    names = [r['output'] for r in comparisons] + ['README.txt', 'index.html', 'comparison-verification.json', 'all-area-inventory.json']
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for name in sorted(names):
            entry = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            bundle.writestr(entry, (args.output / name).read_bytes(), compresslevel=9)
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None and set(bundle.namelist()) == set(names)
        for result in comparisons:
            assert hashlib.sha256(bundle.read(result['output'])).hexdigest() == result['comparison_png_sha256']
        assert json.loads(bundle.read('all-area-inventory.json')) == inventory
        assert json.loads(bundle.read('comparison-verification.json')) == metadata
    sha = digest(archive)
    archive.with_suffix('.zip.sha256').write_text(sha + '  ' + archive.name + '\n', encoding='utf-8')
    print(json.dumps({'archive': str(archive.resolve()), 'bytes': archive.stat().st_size, 'sha256': sha,
                      'records': len(records), 'images': len(comparisons), 'unrenderable': len(failures), 'games': counts}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
