"""Copy complete CrystalDust Mr. Pokemon furniture modules at native pixel scale."""
from __future__ import annotations
from pathlib import Path
import argparse
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
for ancestor in HERE.parents:
    dependencies = ancestor / '.tools/python'
    if dependencies.is_dir():
        sys.path.insert(0, str(dependencies))
        break
from PIL import Image

PAIR = '083df884_083dfb0c'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def rgba(im):
    return hashlib.sha256(im.convert('RGBA').tobytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True,
        help='Read-only CrystalDust extraction containing catalog.json, maps and pairs.')
    parser.add_argument('--output', type=Path,
        default=HERE.parent/'assets/third_party/johto-hacks/route30-mr-pokemon',
        help='Directory for reproducible native asset modules and provenance.')
    args = parser.parse_args()
    SOURCE, OUT = args.source_root.resolve(), args.output.resolve()
    assert SOURCE != OUT and not OUT.is_relative_to(SOURCE), 'Keep source extraction read-only'
    catalog_path = SOURCE / 'catalog.json'
    catalog = json.loads(catalog_path.read_text(encoding='utf-8'))
    definition = next(m for m in catalog['maps'] if m['id'] == 'g02_m006')
    assert (definition['width'], definition['height'], definition['pair']) == (8, 9, PAIR)
    directory = SOURCE / 'pairs' / PAIR
    planes = {n: Image.open(directory / f'{n}.png').convert('RGBA') for n in ('bottom', 'top', 'flat')}
    metadata = {m['id']: m for m in json.loads((directory / 'metatiles.json').read_text(encoding='utf-8'))}
    original = Image.open(SOURCE / 'maps/g02_m006-flat.png').convert('RGBA')
    assert original.size == (128, 144)
    OUT.mkdir(parents=True, exist_ok=True)
    files, modules = {}, {}
    credit = 'CrystalDust by Sierraffinity and contributors'
    url = 'https://github.com/Sierraffinity/CrystalDust'

    def extract(name, x, y, plane):
        word = definition['grid'][y * 8 + x]
        mid = word & 1023
        sx, sy = mid % 16 * 16, mid // 16 * 16
        rect = sx, sy, sx + 16, sy + 16
        native_flat = Image.alpha_composite(planes['bottom'].crop(rect), planes['top'].crop(rect))
        assert native_flat.tobytes() == planes['flat'].crop(rect).tobytes()
        assert rgba(native_flat) == metadata[mid]['pixel_sha256']
        assert native_flat.tobytes() == original.crop((x*16, y*16, x*16+16, y*16+16)).tobytes()
        piece = planes[plane].crop(rect)
        path = OUT / f'{name}.png'
        piece.save(path)
        assert Image.open(path).convert('RGBA').tobytes() == piece.tobytes()
        files[path.name] = sha(path)
        modules[name] = dict(asset=f'assets/third_party/johto-hacks/route30-mr-pokemon/{path.name}',
            assetFileHash=sha(path), assetPixelHash=rgba(piece), credit=credit, sourceUrl=url,
            source_rom_sha256=catalog['rom_sha256'], source_map='g02_m006', source_pair=PAIR,
            source_map_cell=[x,y], native_grid_value=word, donor_mid=mid, donor_plane=plane,
            source_rect=[sx,sy,16,16], source_map_rect=[x*16,y*16,16,16],
            source_metatile_flat_sha256=rgba(native_flat), native_alpha_unchanged=True,
            logical_size=[16,16], integer_scale=1)
        return piece

    assemblies = {}
    specs = {
        'sofa': dict(origin=[2,1], size=[2,2], plane='flat', note='Complete native sofa and its existing wall/floor background. Lower sofa metatiles use native bottom graphics.'),
    }
    for name,spec in specs.items():
        width,height=spec['size']
        full=Image.new('RGBA',(width*16,height*16))
        parts=[]
        for y in range(height):
            for x in range(width):
                key=f'{name}-{x}-{y}'
                piece=extract(key,spec['origin'][0]+x,spec['origin'][1]+y,spec['plane'])
                full.paste(piece,(x*16,y*16))
                parts.append(dict(module=key,destination=[x*16,y*16]))
        path=OUT/f'complete-native-{name}.png';full.save(path);files[path.name]=sha(path)
        assemblies[name]=dict(**spec,parts=parts,asset=path.name,rgba_sha256=rgba(full),
            source_map_rect=[spec['origin'][0]*16,spec['origin'][1]*16,width*16,height*16],
            native_object_bounds=full.getbbox())
    for name,x,y in [('wall-upper',2,0),('wall-lower',4,1),('wall-floor-base',4,2),('floor-plain',1,3)]:
        extract(name,x,y,'flat')
    for x in range(2):
        extract(f'sofa-upper-top-{x}',2+x,1,'top')
    compositions = {}
    for x in range(2):
        base = Image.open(OUT/'wall-upper.png').convert('RGBA')
        overlay = Image.open(OUT/f'sofa-upper-top-{x}.png').convert('RGBA')
        composed = Image.alpha_composite(base,overlay)
        path = OUT/f'sofa-upper-wall-{x}.png';composed.save(path);files[path.name]=sha(path)
        compositions[path.name] = dict(
            asset=f'assets/third_party/johto-hacks/route30-mr-pokemon/{path.name}',
            assetFileHash=sha(path),assetPixelHash=rgba(composed),credit=credit,sourceUrl=url,
            source_rom_sha256=catalog['rom_sha256'],source_map='g02_m006',source_pair=PAIR,
            composition='Exact native wall-upper FLAT + complete native sofa upper TOP, both at (0,0).',
            base_module='wall-upper',overlay_module=f'sofa-upper-top-{x}',
            base_rgba_sha256=rgba(base),overlay_rgba_sha256=rgba(overlay),
            native_overlay_alpha_unchanged=True,logical_size=[16,16],integer_scale=1)
        assert Image.open(path).convert('RGBA').tobytes() == composed.tobytes()
    provenance=dict(format=1,origin=credit,sourceUrl=url,
        purpose='Route 30 Mr. Pokemon house: complete native sofa and matching intact wall/floor modules.',
        recipe='Copy complete native 16x16 modules at 1:1. Optional sofa-upper pieces retain original TOP-plane alpha. Sofa FLAT pieces and matching wall/floor retain exact native FLAT composition. Two sofa-upper-wall pieces alpha-composite intact native sofa TOP over matching native wall-upper FLAT. No color keying, recoloring, partial equipment crops or fractional scaling.',
        rom_sha256=catalog['rom_sha256'],catalog_sha256=sha(catalog_path),
        source_metatiles_sha256=sha(directory/'metatiles.json'),source_map=definition,
        source_map_origin=[0,0],source_map_padding=[0,0,0,0],source_map_pixel_size=[128,144],
        source_map_rgba_sha256=rgba(original),source_planes={n:dict(path=str((directory/f'{n}.png').resolve()),sha256=sha(directory/f'{n}.png'))for n in planes},
        source_alpha_unchanged=True,scale=1,files=files,source_modules=modules,compositions=compositions,assemblies=assemblies)
    (OUT/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status='passed',assets=len(files),modules=len(modules),output=str(OUT.resolve())),indent=2))

if __name__ == '__main__':
    main()
