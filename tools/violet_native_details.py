"""Extract the reviewed native CrystalDust Violet gym and tower details.

The catalog is private, user-supplied extraction data. Only the three selected
16px native TOP modules and their provenance are packaged. No resampling,
recoloring, background masking, map edits, or runtime animation is performed.

Usage: python tools/violet_native_details.py --catalog-dir PATH/TO/crystaldust
"""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'assets/third_party/johto-hacks/violet-native-details'
ROM_SHA256 = '51196cba923c315d0088b747b5cdee704f2ac057cd493f9ddf226fb7227302cf'
SOURCE_URL = 'https://github.com/Sierraffinity/CrystalDust'
INPUTS = {
    'catalog.json': 'fd8fbaf6eb4ee3774e3fe046bf3b506e7f638ab4cd9297c9f62a8bb1189bc740',
    'pairs/083df884_083dfb3c/metatiles.json': '86a5ee36a739952c4484127e4ca137e6a8cb498ac2e8a7479ff07a24601ca48c',
    'pairs/083df884_083dfb3c/flat.png': '54a68711c23cfc9d16cb21998629f2bb9198edfee035a7ee54632e2ad179dac5',
    'pairs/083df884_083dfb3c/top.png': '68e3fdc5b0bced2b0afe89adc3230f4d5857883c50a749e0bf376667ea58a4f2',
    'pairs/083df884_083dfa94/metatiles.json': '733bf842b36410457f01fdc46f2352883c176af985bb8fec7e7c979120a2750c',
    'pairs/083df884_083dfa94/flat.png': '22e6b92617908ae1c5f1212ea5e0959f2b64cb5d4081413ba3188ba4255eeabc',
    'pairs/083df884_083dfa94/top.png': '2d00abc21db5fc9bfe659312c20516bba1532a6fc7b341043947a4fc793f02db',
    'maps/g08_m001-flat.png': '0c99978e517329ed0fd89d2100a834a3594d89050b5dcec3c423949298751a3a',
    'maps/g24_m025-flat.png': 'edff2b80155b74d4ed4f56dd289abc7d6787e114449cc425ba1ee164829a5e5c',
}
RECIPES = {
    'gym-compact-statue': ('g08_m001', '083df884_083dfb3c', 766),
    'sprout-painting-left': ('g24_m025', '083df884_083dfa94', 528),
    'sprout-painting-right': ('g24_m025', '083df884_083dfa94', 520),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pixel_hash(image):
    return hashlib.sha256(image.convert('RGBA').tobytes()).hexdigest()


def tile(atlas, mid):
    x, y = mid % 16 * 16, mid // 16 * 16
    return atlas.crop((x, y, x + 16, y + 16))


def rebuild(atlas, spec):
    image = Image.new('RGBA', (spec['width'] * 16, spec['height'] * 16))
    for index, value in enumerate(spec['grid']):
        image.paste(tile(atlas, value & 0x3ff),
                    (index % spec['width'] * 16, index // spec['width'] * 16))
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog-dir', type=Path, required=True,
                        help='Private extracted CrystalDust directory containing catalog.json and pairs/')
    args = parser.parse_args()
    private = args.catalog_dir.resolve()
    for relative, expected in INPUTS.items():
        assert digest(private / relative) == expected, 'Unexpected donor input: ' + relative
    catalog = json.loads((private / 'catalog.json').read_text(encoding='utf-8'))
    assert catalog['rom_sha256'] == ROM_SHA256
    maps = {spec['id']: spec for spec in catalog['maps']}
    records = {}
    tops = {}
    complete_native_maps = {}
    DEST.mkdir(parents=True, exist_ok=True)
    for name, (map_id, pair, mid) in RECIPES.items():
        spec = maps[map_id]
        assert spec['pair'] == pair
        directory = private / 'pairs' / pair
        flat = Image.open(directory / 'flat.png').convert('RGBA')
        top = Image.open(directory / 'top.png').convert('RGBA')
        metadata = json.loads((directory / 'metatiles.json').read_text(encoding='utf-8'))
        assert pixel_hash(tile(flat, mid)) == metadata[mid]['pixel_sha256']
        original_map = Image.open(private / 'maps' / (map_id + '-flat.png')).convert('RGBA')
        assert rebuild(flat, spec).tobytes() == original_map.tobytes()
        image = tile(top, mid)
        assert image.size == (16, 16)
        assert set(image.getchannel('A').get_flattened_data()) <= {0, 255}
        target = DEST / (name + '.png')
        image.save(target)
        coords = [[index % spec['width'], index // spec['width']]
                  for index, value in enumerate(spec['grid']) if value & 0x3ff == mid]
        assert coords
        records[name] = {
            'asset': target.relative_to(ROOT).as_posix(),
            'assetFileHash': digest(target),
            'assetPixelHash': pixel_hash(image),
            'source_rom_sha256': ROM_SHA256,
            'source_rom_name': catalog['rom_name'],
            'source_map': map_id,
            'source_map_flat_png_sha256': digest(private / 'maps' / (map_id + '-flat.png')),
            'native_map_coords': coords,
            'donor_pair': pair,
            'donor_mid': mid,
            'donor_plane': 'top',
            'donor_xyxy': [mid % 16 * 16, mid // 16 * 16,
                           mid % 16 * 16 + 16, mid // 16 * 16 + 16],
            'source_atlas_sha256': digest(directory / 'top.png'),
            'source_metatile_flat_rgba_sha256': metadata[mid]['pixel_sha256'],
            'logical_size': [16, 16],
            'opaque_bounds': list(image.getbbox()),
            'pixel_scale': 1,
            'native_alpha_unchanged': True,
            'whole_native_metatile_layer': True,
        }
        tops[name] = image
        complete_native_maps[map_id] = rebuild(top, spec)

    # The native painting is centred on the boundary between cells 7 and 8.
    # Retain both whole native cells for runtime placement. The 16px picture
    # spans right 8px of MID 528 and left 8px of MID 520, including its full
    # original frame, with native timber outside it in the full-cell assets.
    picture = Image.new('RGBA', (16, 16))
    picture.paste(tops['sprout-painting-left'].crop((8, 0, 16, 16)), (0, 0))
    picture.paste(tops['sprout-painting-right'].crop((0, 0, 8, 16)), (8, 0))
    native_crop = complete_native_maps['g24_m025'].crop((120, 16, 136, 32))
    assert picture.tobytes() == native_crop.tobytes()
    assert pixel_hash(picture) == 'd97f83f82cbb55218584a670e6507142a4cd1f2eeca0bb491f7170b4bd9f347e'
    proof = {
        'origin': 'Exact native CrystalDust Violet gym compact carved panel and Sprout Tower Bellsprout picture; complete original native TOP modules.',
        'credit': 'Pokemon CrystalDust / Sierraffinity and DoMoreAwesome Games; native Johto room artwork.',
        'sourceUrl': SOURCE_URL,
        'rom_sha256': ROM_SHA256,
        'rom_name': catalog['rom_name'],
        'input_files_sha256': INPUTS,
        'source_modules': records,
        'whole_frame_bounds_proof': {
            'source_map': 'g24_m025',
            'source_top_xyxy': [120, 16, 136, 32],
            'dimensions': [16, 16],
            'rgba_sha256': pixel_hash(picture),
            'left_asset_source_xyxy': [8, 0, 16, 16],
            'right_asset_source_xyxy': [0, 0, 8, 16],
            'assembled_equals_exact_native_map_top_crop': True,
            'whole_runtime_cell_pair': [528, 520],
            'native_timber_outside_frame_retained': True,
            'feature_crop_or_scale': False,
        },
        'limits': ['Static native background extraction; no actors or runtime animation callbacks executed.',
                   'Source collision, warps, actor placements, story and interaction scripts are not changed by this extractor.'],
    }
    (DEST / 'provenance.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'passed', 'assets': len(records),
                      'whole_frame_native_rgba_sha256': pixel_hash(picture)}))


if __name__ == '__main__':
    main()
