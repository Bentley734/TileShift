"""Extract complete native CrystalDust Mart shelf modules from a local ROM extract."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

HERE = Path(__file__).resolve()
WORKSPACE = next((p for p in [Path.cwd(), *HERE.parents] if (p / '.tools/python').is_dir()), Path.cwd())
sys.path.insert(0, str(WORKSPACE / '.tools/python'))
from PIL import Image

PAIR = '083df884_083df89c'
MAP = 'g02_m004'
MODULES = {'top-left': 567, 'top-center': 571, 'top-right': 572,
           'bottom-left': 577, 'bottom-center': 576, 'bottom-right': 578}
FOLDER = 'assets/third_party/johto-hacks/mart-front-shelves'
CREDIT = 'CrystalDust by Sierraffinity and contributors; complete native Mart glass display modules.'
URL = 'https://github.com/Sierraffinity/CrystalDust'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mod', type=Path, default=HERE.parents[1])
    parser.add_argument('--native-root', type=Path, default=WORKSPACE / '.work/tileshift-firegold')
    parser.add_argument('--metadata', type=Path)
    args = parser.parse_args()
    mod, native = args.mod.resolve(), args.native_root.resolve() / 'crystaldust'
    output = mod / FOLDER
    output.mkdir(parents=True, exist_ok=True)
    catalog_path = native / 'catalog.json'
    catalog = json.loads(catalog_path.read_text(encoding='utf-8'))
    definition = next(m for m in catalog['maps'] if m['id'] == MAP)
    assert definition['pair'] == PAIR
    plane_path = native / 'pairs' / PAIR / 'top.png'
    plane = Image.open(plane_path).convert('RGBA')
    meta_path = plane_path.parent / 'metatiles.json'
    metatiles = {m['id']: m for m in json.loads(meta_path.read_text(encoding='utf-8'))}
    assets, files = {}, {}
    for name, mid in MODULES.items():
        sx, sy = mid % 16 * 16, mid // 16 * 16
        piece = plane.crop((sx, sy, sx + 16, sy + 16))
        assert piece.size == (16, 16) and piece.getbbox()
        assert set(piece.getchannel('A').get_flattened_data()) <= {0, 255}
        filename = 'shelf-' + name + '.png'
        target = output / filename
        piece.save(target)
        assert Image.open(target).convert('RGBA').tobytes() == piece.tobytes()
        files[filename] = sha(target.read_bytes())
        assets[name] = {'asset': FOLDER + '/' + filename, 'assetFileHash': files[filename],
                        'assetPixelHash': sha(piece.tobytes()), 'credit': CREDIT, 'sourceUrl': URL,
                        'source_rom_sha256': catalog['rom_sha256'], 'source_pair': PAIR,
                        'source_map': MAP, 'donor_mid': mid, 'donor_plane': 'top',
                        'source_rect': [sx, sy, 16, 16], 'logical_size': [16, 16],
                        'native_alpha_unchanged': True, 'integer_scale': 1,
                        'source_metatile_flat_sha256': metatiles[mid]['pixel_sha256']}
    assert set(files) == {path.name for path in output.glob('*.png')}
    provenance = {'origin': CREDIT, 'sourceUrl': URL,
                  'purpose': 'Complete native shelf ends and center modules for original G/S/C 32x32 and 64x32 front fixtures.',
                  'rom_sha256': catalog['rom_sha256'], 'source_map': MAP, 'source_pair': PAIR,
                  'catalog_sha256': sha(catalog_path.read_bytes()),
                  'source_top_plane_sha256': sha(plane_path.read_bytes()),
                  'source_metatiles_sha256': sha(meta_path.read_bytes()),
                  'recipe': 'Copy six complete 16x16 native TOP planes at 1:1 pixel scale. Preserve every native alpha and RGB byte. Keep left/right end modules at outer ends, repeat only complete center modules for wider fixtures. No floor RGB, cropping within a tile, recoloring, generated pixels or fractional scaling.',
                  'native_small_grid': [[567, 572], [577, 578]],
                  'native_wide_grid': [[567, 571, 571, 572], [577, 576, 576, 578]],
                  'source_modules': assets, 'files': files}
    (output / 'provenance.json').write_text(json.dumps(provenance, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    if args.metadata:
        args.metadata.parent.mkdir(parents=True, exist_ok=True)
        args.metadata.write_text(json.dumps({'asset_dir': FOLDER, 'assets': assets}, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({'native_modules': len(assets), 'native_source': 'CrystalDust', 'size': '16x16',
                      'output': str(output)}, indent=2))


if __name__ == '__main__':
    main()
