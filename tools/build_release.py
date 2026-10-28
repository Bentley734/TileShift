"""Build and verify the installable TileShift ZIP; never include imported art."""
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
    args = parser.parse_args()
    proof = json.loads(args.gpu_report.read_text(encoding="utf-8"))
    inputs = runtime_fingerprint(root)
    assert proof["status"] == "passed", "Native GPU validation must pass before packaging"
    assert proof["runtime_inputs"] == inputs, "Native GPU proof is stale; validate the current runtime files first"
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
               'third_party/magiscarf/', 'third_party/metalflygon08/', 'user_flora/', 'original/sprout-tower/', 'original/flora/', 'original/slowpoke-well/', 'original/olivine-lighthouse/', 'original/compact-conifer/', 'original/ecruteak-v2/')
    for path in asset_files:
        assert path.relative_to(root / 'assets').as_posix().startswith(allowed), 'Unreviewed asset folder'
        assert path.suffix in ('.png', '.jpg', '.json', '.txt'), 'Unreviewed asset format'
    for folder in ('user_flora', 'third_party/magiscarf', 'third_party/metalflygon08', 'original/sprout-tower', 'original/flora', 'original/slowpoke-well', 'original/olivine-lighthouse', 'original/compact-conifer', 'original/ecruteak-v2'):
        provenance = json.loads((root / 'assets' / folder / 'provenance.json').read_text(encoding='utf-8'))
        for name, digest in provenance['files'].items():
            assert hashlib.sha256((root / 'assets' / folder / name).read_bytes()).hexdigest() == digest, 'Artwork provenance fingerprint changed'
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
              "validated_runtime_sha256": inputs["sha256"], "native_gpu_checks": proof["checks"]}
    (args.output / "package-verification.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "files"}, indent=2))


if __name__ == "__main__":
    main()
