"""Build verified TileShift ZIP; selected user-authorized hack artwork only, never ROMs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from validate_gpu import runtime_fingerprint


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=root / "build")
    parser.add_argument("--gpu-report", type=Path, default=root.parent / ".work/tileshift-gpu/report.json")
    parser.add_argument("--reverse-gpu-report", type=Path, default=root.parent / ".work/tileshift-reverse-gpu/report.json")
    args = parser.parse_args()
    proof = json.loads(args.gpu_report.read_text(encoding="utf-8"))
    inputs = runtime_fingerprint(root)
    assert proof["status"] == "passed", "Native GPU validation must pass before packaging"
    assert proof.get("theme") == "gen3", "Forward Gen3-theme native GPU validation must pass"
    assert proof["runtime_inputs"] == inputs, "Native GPU proof is stale; validate the current runtime files first"
    reverse = json.loads(args.reverse_gpu_report.read_text(encoding="utf-8"))
    assert reverse["status"] == "passed" and reverse.get("theme") == "reverse", "Classic-theme native GPU validation must pass"
    assert reverse["runtime_inputs"] == inputs, "Classic-theme GPU proof is stale"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["id"] == "tileshift"
    version = manifest["version"]
    assert version and all(c.isdigit() or c == "." for c in version)
    files = [root / name for name in
             ("manifest.json", "main.lua", "README.md", "CREDITS.md", "LICENSE")]
    files += sorted((root / "lib").glob("*.lua"))
    files += sorted((root / "mappings").glob("*.lua"))
    asset_files = sorted(path for path in (root / 'assets').rglob('*') if path.is_file())
    allowed = ('third_party/j-treecko252/',
               'third_party/magiscarf/', 'third_party/metalflygon08/', 'user_flora/', 'original/sprout-tower/', 'original/flora/', 'original/slowpoke-well/', 'original/olivine-lighthouse/', 'original/compact-conifer/', 'original/ecruteak-v2/', 'original/bell-wide/', 'original/center-expanded/')
    allowed += ('third_party/johto-hacks/', 'original/classic-vent/', 'original/ilex-shrine/', 'original/whirlpool/', 'original/park-bench/', 'third_party/peekychew/')
    allowed += ('third_party/native-kanto-interiors/', 'third_party/gsc-room-geometry/',
                'third_party/gamefreak/gsc-apartments/', 'third_party/kanto-landmarks/')
    interior_folders = ('original/azalea-lawn', 'original/interior-beacon', 'original/interior-computer', 'original/interior-flowerpot', 'original/interior-lattice', 'original/interior-painting', 'original/interior-pillar', 'original/interior-planter', 'original/interior-radio', 'original/interior-railpost', 'original/interior-stairs', 'original/interior-tower-modules')
    allowed += tuple(folder + '/' for folder in interior_folders)
    for path in asset_files:
        assert path.relative_to(root / 'assets').as_posix().startswith(allowed), 'Unreviewed asset folder'
        assert path.suffix in ('.png', '.jpg', '.json', '.txt'), 'Unreviewed asset format'
    for folder in ('original/classic-vent', 'user_flora', 'third_party/magiscarf', 'third_party/metalflygon08', 'original/sprout-tower', 'original/flora', 'original/slowpoke-well', 'original/olivine-lighthouse', 'original/compact-conifer', 'original/ecruteak-v2', 'original/bell-wide', 'original/center-expanded', 'original/ilex-shrine', 'original/whirlpool', 'original/park-bench', 'third_party/peekychew'):
        provenance = json.loads((root / 'assets' / folder / 'provenance.json').read_text(encoding='utf-8'))
        for name, digest in provenance['files'].items():
            assert hashlib.sha256((root / 'assets' / folder / name).read_bytes()).hexdigest() == digest, 'Artwork provenance fingerprint changed'
    for folder in interior_folders:
        provenance = json.loads((root / 'assets' / folder / 'provenance.json').read_text(encoding='utf-8'))
        for name, digest in provenance['files'].items():
            assert hashlib.sha256((root / 'assets' / folder / name).read_bytes()).hexdigest() == digest, 'Interior artwork provenance fingerprint changed'
    for record in (root / 'assets/third_party/johto-hacks').rglob('provenance.json'):
        provenance = json.loads(record.read_text(encoding='utf-8'))
        for name, digest in provenance['files'].items():
            assert hashlib.sha256((record.parent / name).read_bytes()).hexdigest() == digest, 'Hack artwork provenance changed'
    landmark_folder = root / 'assets/third_party/kanto-landmarks'
    landmark_provenance = json.loads((landmark_folder / 'provenance.json').read_text(encoding='utf-8'))
    for name, digest in landmark_provenance['files'].items():
        path = landmark_folder / name
        assert path.resolve().is_relative_to(landmark_folder.resolve()), 'Landmark artwork leaves its reviewed folder'
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, 'Native landmark artwork changed'
    assert set(landmark_provenance['files']) == {path.relative_to(landmark_folder).as_posix()
        for path in landmark_folder.rglob('*.png')}, 'Native landmark PNG lacks provenance'
    # Complete native sculptures and the explicitly credited original-GSC
    # geometry derivatives have distinct provenance schemas. Every packaged
    # PNG must be accounted for, rather than simply allowing a new folder.
    for folder in ('native-kanto-interiors', 'gsc-room-geometry', 'gamefreak/gsc-apartments'):
        directory = root / 'assets/third_party' / folder
        provenance = json.loads((directory / 'provenance.json').read_text(encoding='utf-8'))
        records = provenance['assets']
        checked = set()
        for name, item in (records.items() if isinstance(records, dict)
                           else ((item['asset'], item) for item in records)):
            path = root / name if name.startswith('assets/') else directory / name
            assert path.resolve().is_relative_to(directory.resolve()), 'Provenance asset leaves its reviewed folder'
            expected_hash = item.get('assetFileHash') or item.get('png_sha256')
            assert expected_hash and hashlib.sha256(path.read_bytes()).hexdigest() == expected_hash, 'Native interior derivative changed'
            checked.add(path.resolve())
        assert checked == {path.resolve() for path in directory.rglob('*.png')}, 'Native interior PNG lacks provenance'
    fan = root / 'assets/third_party/j-treecko252'
    provenance = json.loads((fan / 'provenance.json').read_text(encoding='utf-8'))
    assert hashlib.sha256((fan / 'compact-tree.png').read_bytes()).hexdigest() == provenance['extraction']['png_sha256']
    files += asset_files
    assert len(files) == len(set(files)) and all(path.is_file() for path in files)
    args.output.mkdir(parents=True, exist_ok=True)
    archive = args.output / f"TileShift-v{version}.zip"
    expected = {}
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in files:
            name = "tileshift/" + path.relative_to(root).as_posix()
            content = path.read_bytes()
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, content, compresslevel=9)
            expected[name] = hashlib.sha256(content).hexdigest()
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        assert set(bundle.namelist()) == set(expected)
        for name, digest in expected.items():
            assert hashlib.sha256(bundle.read(name)).hexdigest() == digest
        assert json.loads(bundle.read("tileshift/manifest.json"))["version"] == version
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum = archive.with_suffix(".zip.sha256")
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    report = {"version": version, "archive": str(archive.resolve()),
              "bytes": archive.stat().st_size, "sha256": digest,
              "files": expected, "zip_roundtrip_verified": True,
              "validated_runtime_sha256": inputs["sha256"], "native_gpu_checks": proof["checks"], "reverse_native_gpu_checks": reverse["checks"]}
    (args.output / "package-verification.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "files"}, indent=2))


if __name__ == "__main__":
    main()
