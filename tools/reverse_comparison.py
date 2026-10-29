"""Create exact-pixel comparisons from a passing classic-theme GPU report."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

import gpu_comparison
from validate_gpu import runtime_fingerprint


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    workspace = root.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, default=workspace / '.work/tileshift-reverse-gpu/report.json')
    parser.add_argument('--coverage', type=Path, default=workspace / '.work/tileshift-reverse-coverage/report.json')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--package', action='store_true')
    args = parser.parse_args()
    version = json.loads((root / 'manifest.json').read_text())['version']
    output = (args.output or workspace / f'TileShift-Classic-Comparisons-v{version}').resolve()
    report = json.loads(args.report.read_text())
    coverage = json.loads(args.coverage.read_text())
    assert report['status'] == coverage['status'] == 'passed'
    assert report['theme'] == 'reverse'
    assert report['runtime_inputs'] == coverage['runtime_inputs'] == runtime_fingerprint(root)
    output.mkdir(parents=True, exist_ok=True)
    comparisons = []
    for fixture in report['fixtures']:
        game, map_id, style = fixture['game'], fixture['map'], fixture['style']
        assert style in ('gen1', 'gen2') and fixture['actual_native_field_view']
        town = map_id.split('_', 1)[1].replace('_', ' ').title()
        label = 'Gen 1 monochrome' if style == 'gen1' else 'Gen 2 Crystal colors'
        stem = f'{game}-{map_id}-{style}'
        gpu_comparison.NAMES[game, map_id] = (f'{game.capitalize()} / {town}', stem, f'Original {game.capitalize()}')
        fixture = dict(fixture, comparison_after_label=label + ' — reviewed cells')
        record = gpu_comparison.make(fixture, output)
        old = Path(record['output'])
        target = output / f'TileShift-Classic-{stem}-comparison.png'
        old.replace(target)
        record.update(output=target.name, style=style)
        comparisons.append(record)
    assert comparisons and len({record['output'] for record in comparisons}) == len(comparisons)
    expected = {record['output'] for record in comparisons}
    assert {path.name for path in output.glob('*.png')} == expected
    for record in comparisons:
        assert hashlib.sha256((output / record['output']).read_bytes()).hexdigest() == record['comparison_png_sha256']
    metadata = {'version': version, 'source': 'Actual native Gen3 FieldView GPU backgrounds',
                'gpu_checks': report['checks'], 'runtime_inputs_sha256': report['runtime_inputs']['sha256'],
                'limits': report['limits'], 'scope': coverage['totals'], 'comparisons': comparisons}
    (output / 'comparison-verification.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    (output / 'README.txt').write_text(
        f'TileShift v{version} - Gen1/Gen2 themes in Gen3 games\n'
        'Actual native GPU backgrounds at 2x nearest-neighbour scale.\n'
        'Each image reports its own replaced/native cell counts. Other Gen3 maps remain partially converted.\n'
        'Pallet and Littleroot backgrounds are complete in both classic themes.\n'
        'Actors and field effects retain native Gen3 artwork; actors are omitted from these captures.\n'
        'The installable mod is the separate TileShift ZIP.\n', encoding='utf-8')
    result = {'output': str(output), 'comparisons': len(comparisons), 'panels_exact_gpu_rgb': True}
    if args.package:
        archive = root / f'build/TileShift-Classic-Comparisons-v{version}.zip'
        archive.parent.mkdir(exist_ok=True)
        package_names = expected | {'comparison-verification.json', 'README.txt'}
        files = {name: (output / name).read_bytes() for name in package_names}
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
            for name, data in sorted(files.items()):
                info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                bundle.writestr(info, data, compresslevel=9)
        with zipfile.ZipFile(archive) as bundle:
            assert bundle.testzip() is None and set(bundle.namelist()) == set(files)
            for name, data in files.items():
                assert bundle.read(name) == data
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        archive.with_suffix('.zip.sha256').write_text(f'{digest}  {archive.name}\n', encoding='utf-8')
        result.update(archive=str(archive), bytes=archive.stat().st_size, sha256=digest, zip_roundtrip_verified=True)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
