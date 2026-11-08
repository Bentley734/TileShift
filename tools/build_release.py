"""Build verified TileShift ZIP; selected user-authorized hack artwork only, never ROMs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from validate_gpu import runtime_fingerprint

BERRY_SOIL_NAMES = {f'soil-{tile}.png' for tile in
    (259, 260, 261, 267, 268, 269, 275, 276, 277, 331, 332, 333)} | {
    f'soil-{bank}-{tile}.png' for bank, tiles in (
        ('fortree', (659, 667, 668)),
        ('lilycove', (627, 629, 635, 637, 725, 733, 741))) for tile in tiles}


def validate_submarine_assets(root: Path) -> dict:
    """Verify the whole generated vessel and every installed 16px piece."""
    from PIL import Image

    directory = root / 'assets/original/classic-submarine'
    provenance = json.loads((directory / 'provenance.json').read_text(encoding='utf-8'))
    whole = directory / 'submarine64x48.png'
    assert hashlib.sha256(whole.read_bytes()).hexdigest() == provenance['whole_png_sha256']
    image = Image.open(whole).convert('RGBA')
    assert image.size == (64, 48) and not image.crop((0, 32, 64, 48)).getbbox()
    assert set(image.getchannel('A').get_flattened_data()) <= {0, 255}
    assert {p[:3] for p in image.get_flattened_data() if p[3]} == set(map(tuple, provenance['palette']))
    assert len(provenance['palette']) == 4 and provenance['normalization']['uniform_integer_scale'] == 23
    whole_hash = hashlib.sha256(image.tobytes()).hexdigest()
    assert whole_hash == provenance['whole_rgba_sha256']
    grid = [[740, 741, 742, 743], [736, 737, 738, 739]]
    pieces = {item['mid']: item for item in provenance['cells']}
    assert set(pieces) == set(range(736, 744)) and len(provenance['cells']) == 8
    assert {p.name for p in directory.iterdir()} == {'provenance.json', whole.name} | {f'submarine-{mid}.png' for mid in pieces}
    for y, row in enumerate(grid):
        for x, mid in enumerate(row):
            path = directory / f'submarine-{mid}.png'
            record = pieces[mid]
            assert record['asset'] == path.relative_to(root).as_posix()
            assert hashlib.sha256(path.read_bytes()).hexdigest() == record['file_sha256']
            tile = Image.open(path).convert('RGBA')
            assert tile.size == (16, 16)
            assert tile.tobytes() == image.crop((x*16, y*16, x*16+16, y*16+16)).tobytes()
            assert hashlib.sha256(tile.tobytes()).hexdigest() == record['rgba_sha256']
    return {'whole_rgba_sha256': whole_hash, 'checked_cells': len(pieces)}


def validate_berry_assets(root: Path) -> dict:
    """Account for only the approved native-sized trees and clipped soil art."""
    from lupa import LuaRuntime
    from PIL import Image

    directory = root / 'assets/original/berries/gen2'
    provenance = json.loads((directory / 'provenance.json').read_text(encoding='utf-8'))
    assert provenance['format'] == 1 and provenance['style'] == 'gen2'
    assert provenance['generator'] == 'built-in image_gen'
    assert provenance['variety_count'] == 43 and provenance['native_frames'] == 387
    assert provenance['all_raw_and_native_reference_images_private'] is True
    assert provenance['each_atlas_uses_one_uniform_integer_scale'] is True
    vm = LuaRuntime(unpack_returned_tuples=True)
    catalog = vm.execute((root / 'lib/berry_catalog.lua').read_text(encoding='utf-8'))
    varieties = dict(catalog['varieties'].items())
    assert set(varieties) == set(range(1, 44)), 'Incomplete berry runtime catalog'
    records = provenance['varieties']
    assert len(records) == 43 and {item['berry'] for item in records} == set(varieties)
    checked = {}

    def check_asset(item: dict, size: tuple[int, int], png_hash: str) -> Image.Image:
        relative = item['asset']
        path = root / relative
        assert path.parent == directory and path.resolve().is_relative_to(directory.resolve()), 'Berry provenance leaves its reviewed folder'
        assert path.suffix == '.png' and relative not in checked, 'Duplicate or invalid berry asset'
        assert hashlib.sha256(path.read_bytes()).hexdigest() == png_hash, 'Berry PNG provenance changed'
        with Image.open(path) as encoded:
            assert encoded.format == 'PNG' and encoded.size == size, 'Berry native sheet dimensions changed'
            image = encoded.convert('RGBA')
        rgba_hash = item.get('native_rgba_sha256') or item.get('rgba_sha256')
        assert rgba_hash and hashlib.sha256(image.tobytes()).hexdigest() == rgba_hash, 'Berry RGBA provenance changed'
        assert set(image.getchannel('A').get_flattened_data()) <= {0, 255}, 'Berry artwork lost binary alpha'
        checked[relative] = {'png_sha256': png_hash, 'rgba_sha256': rgba_hash, 'size': list(size)}
        return image

    def check_generation(item: dict) -> None:
        generation = item['generation']
        assert generation['mode'] == 'built-in image_gen'
        assert hashlib.sha256(generation['prompt'].encode('utf-8')).hexdigest() == generation['prompt_sha256'], 'Berry generation prompt changed'

    for item in records:
        entry = varieties[item['berry']]
        expected_asset = f"assets/original/berries/gen2/{item['name']}.png"
        assert item['name'].isascii() and item['name'].isalpha() and item['name'].islower()
        assert item['asset'] == expected_asset == entry['asset'] and item['name'] == entry['name'], 'Berry catalog identity differs from provenance'
        assert item['native_png_sha256'] == entry['hash'], 'Berry catalog fingerprint differs from provenance'
        assert item['native_sheet'] == [16, 240]
        image = check_asset(item, (16, 240), item['native_png_sha256'])
        check_generation(item)
        assert item['recipe']['integer_scale'] >= 1 and isinstance(item['recipe']['integer_scale'], int)
        frames = item['frames']
        assert len(frames) == 9 and [frame['frame'] for frame in frames] == list(range(9))
        for index, frame in enumerate(frames):
            y, height = (index * 16, 16) if index < 3 else (48 + (index - 3) * 32, 32)
            pixels = image.crop((0, y, 16, y + height))
            assert pixels.getbbox() is not None, 'Empty berry growth frame'
            assert frame['packed_size'] == [16, height]
            assert hashlib.sha256(pixels.tobytes()).hexdigest() == frame['rgba_sha256'], 'Berry frame provenance changed'

    material = provenance['soil_material']
    assert material['asset'] == 'assets/original/berries/gen2/soil-material.png'
    assert material['size'] == [16, 16] and material['opaque'] is True
    material_image = check_asset(material, (16, 16), material['native_png_sha256'])
    assert set(material_image.getchannel('A').get_flattened_data()) == {255}
    check_generation(material)
    shapes = material['shape_variants']
    expected_shapes = {'assets/original/berries/gen2/' + name for name in BERRY_SOIL_NAMES}
    assert len(shapes) == 22 and {item['asset'] for item in shapes} == expected_shapes, 'Incomplete berry soil provenance'
    for item in shapes:
        assert item['size'] == [16, 16]
        check_asset(item, (16, 16), item['sha256'])
    soil_rows = vm.execute((root / 'mappings/reverse_classic_berry_soil.lua').read_text(encoding='utf-8'))
    used_shapes = set()
    assert len(soil_rows) == 219, 'Unexpected berry soil key count'
    for row in soil_rows.values():
        assert row['style'] == 'gen2' and row['game'] in ('ruby', 'sapphire', 'emerald')
        assert row['asset'] in expected_shapes, 'Berry soil recipe references unreviewed artwork'
        entry = checked[row['asset']]
        assert row['assetFileHash'] == entry['png_sha256'] and row['assetPixelHash'] == entry['rgba_sha256'], 'Berry soil recipe fingerprint differs from provenance'
        assert row['berrySoilReview']['material_hash'] == material['native_png_sha256']
        used_shapes.add(row['asset'])
    assert used_shapes == expected_shapes
    actual_files = {path.relative_to(root).as_posix() for path in directory.rglob('*') if path.is_file()}
    assert len(checked) == 66
    assert actual_files == set(checked) | {'assets/original/berries/gen2/provenance.json'}, 'Unreviewed berry file or raw master would enter the package'
    return {'trees': 43, 'tree_frames': 387, 'soil_assets': 23, 'pngs': len(checked),
            'provenance_sha256': hashlib.sha256((directory / 'provenance.json').read_bytes()).hexdigest(),
            'files': checked}


def validate_celadon_bed_assets(root: Path) -> dict:
    """Verify the complete native bed and its four bounded transparent pieces."""
    from PIL import Image

    directory = root / 'assets/third_party/johto-hacks/celadon-mansion-bed'
    record = json.loads((directory / 'provenance.json').read_text(encoding='utf-8'))
    source = root / 'assets/third_party/johto-hacks/crystaldust-ship-beds/complete-native-bed20x29.png'
    assert record['status'] == 'passed' and record['complete_native_RGBA_preserved'] is True
    assert record['source_asset'] == source.relative_to(root).as_posix()
    assert record['source_png_sha256'] == hashlib.sha256(source.read_bytes()).hexdigest() == '1e5a35e2d7a916ad1cbaf236b6ace4d6ba91dd9a4e828ef2d0fd333e9d926bfd'
    native = Image.open(source).convert('RGBA')
    assert native.size == (20, 29)
    assert record['source_rgba_sha256'] == hashlib.sha256(native.tobytes()).hexdigest() == 'aec6d2d04969f910fe6540188d8b06efaac4dcd81b3407a0e86f072fe07e5654'
    expected = Image.new('RGBA', (32, 32)); expected.paste(native, (0, 3))
    actual = Image.new('RGBA', (32, 32)); checked = {}; cells = set()
    assert len(record['assets']) == 4
    for item in record['assets']:
        x, y = item['cell']
        assert x in (0, 1) and y in (0, 1) and (x, y) not in cells
        cells.add((x, y))
        name = f'bed-foreground-{x}-{y}.png'
        path = directory / name
        assert item['asset'] == path.relative_to(root).as_posix()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item['assetFileHash']
        piece = Image.open(path).convert('RGBA'); assert piece.size == (16, 16)
        assert hashlib.sha256(piece.tobytes()).hexdigest() == item['assetPixelHash']
        actual.paste(piece, (x * 16, y * 16)); checked[name] = item['assetFileHash']
    assert cells == {(0, 0), (0, 1), (1, 0), (1, 1)}
    assert actual.tobytes() == expected.tobytes(), 'Native Celadon bed was cropped, shifted or altered'
    assert sum(bool(px[3]) for px in actual.get_flattened_data()) == record['whole_native_opaque_pixels'] == 522
    assert set(checked) == {p.name for p in directory.glob('*.png')}
    return checked


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
                'third_party/gamefreak/gsc-apartments/', 'third_party/kanto-landmarks/',
                'third_party/native-kanto-chairs/', 'third_party/saffron-paving/')
    allowed += ('third_party/gen2-domestic-floor-audit/', 'third_party/native-interior-seats/')
    allowed += ('third_party/gen2-interior-callback-states/',)
    allowed += ('third_party/gen1-outdoor-audit/', 'third_party/gen1-seating-domestic/',
                'third_party/gamefreak/rby-facility-floor/')
    interior_folders = ('original/azalea-lawn', 'original/interior-beacon', 'original/interior-computer', 'original/interior-flowerpot', 'original/interior-lattice', 'original/interior-painting', 'original/interior-pillar', 'original/interior-planter', 'original/interior-radio', 'original/interior-railpost', 'original/interior-stairs', 'original/interior-tower-modules')
    allowed += tuple(folder + '/' for folder in interior_folders)
    allowed += ('original/berries/gen2/', 'original/classic-submarine/')
    for path in asset_files:
        assert path.relative_to(root / 'assets').as_posix().startswith(allowed), 'Unreviewed asset folder'
        assert path.suffix in ('.png', '.jpg', '.json', '.txt'), 'Unreviewed asset format'
    berry_assets = validate_berry_assets(root)
    submarine_assets = validate_submarine_assets(root) if (root / 'assets/original/classic-submarine').is_dir() else None
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
        checked_files = provenance.get('files')
        if checked_files is None and record.parent == root / 'assets/third_party/johto-hacks/celadon-mansion-bed':
            checked_files = validate_celadon_bed_assets(root)
        if checked_files is None:
            # Native module records already carry exact PNG fingerprints.
            checked_files = {}
            modules = provenance['source_modules']
            assert isinstance(modules, dict) and modules, 'Missing native module provenance'
            for module in modules.values():
                path = (root / module['asset']).resolve()
                assert path.parent == record.parent.resolve(), 'Native module leaves its reviewed folder'
                assert path.suffix == '.png' and path.name not in checked_files, 'Duplicate or invalid native module'
                checked_files[path.name] = module['assetFileHash']
            assert set(checked_files) == {path.name for path in record.parent.glob('*.png')}, 'Native PNG lacks provenance'
        for name, digest in checked_files.items():
            assert hashlib.sha256((record.parent / name).read_bytes()).hexdigest() == digest, 'Hack artwork provenance changed'
    for folder in ('kanto-landmarks', 'native-kanto-chairs', 'saffron-paving',
                   'gen2-domestic-floor-audit', 'native-interior-seats', 'gen2-interior-callback-states',
                   'gen1-outdoor-audit', 'gen1-seating-domestic', 'gamefreak/rby-facility-floor'):
        directory = root / 'assets/third_party' / folder
        provenance = json.loads((directory / 'provenance.json').read_text(encoding='utf-8'))
        checked_files = provenance['files']
        if isinstance(checked_files, list):
            assert folder == 'gen1-seating-domestic', 'Unexpected native asset provenance schema'
            checked_files = {}
            for record in provenance['files']:
                path = root / record['path']
                assert path.resolve().is_relative_to(directory.resolve()), 'Native provenance leaves its reviewed folder'
                name = path.relative_to(directory).as_posix()
                assert name not in checked_files, 'Duplicate native PNG provenance'
                checked_files[name] = record['sha256']
        assert isinstance(checked_files, dict), 'Invalid native PNG provenance'
        for name, digest in checked_files.items():
            path = directory / name
            assert path.resolve().is_relative_to(directory.resolve()), 'Native artwork leaves its reviewed folder'
            assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, 'Native artwork changed'
        assert set(checked_files) == {path.relative_to(directory).as_posix()
            for path in directory.rglob('*.png')}, 'Native PNG lacks provenance'
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
    report['berry_artwork'] = berry_assets
    if submarine_assets:
        report['submarine_artwork'] = submarine_assets
    (args.output / "package-verification.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "files"}, indent=2))


if __name__ == "__main__":
    main()
