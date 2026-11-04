"""Normalize individually generated berry artwork with explicit integer crops.

Only technical palette/alpha conformance is performed here. Creative artwork
comes from the recorded built-in image_gen generation, whose original is kept
privately outside the release. A recipe pins its hash, every complete frame
rectangle, one integer scale, and the separately reviewed variety identity.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT.parent / '.work/tileshift-v0350-berries'
LEAF = ['#102810', '#305018', '#588820', '#8CB830', '#D0E890', '#F0E8C0']
SOIL = ['#7B4A31', '#AD7342', '#C69C63', '#DEBD84']
PAIRS = ((1, 2), (3, 4), (5, 6), (7, 8))
TITLES = ('planted', 'sprout A', 'sprout B', 'taller A', 'taller B',
          'flower A', 'flower B', 'berries A', 'berries B')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def rgb(color):
    assert len(color) == 7 and color.startswith('#')
    return tuple(int(color[i:i+2], 16) for i in (1, 3, 5))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def load_prompts(path):
    paths=[path]
    if path.name=='imagegen-prompts.json':
        for filename in ('imagegen-prompts-agent.json','imagegen-prompts-ever.json'):
            peer=path.with_name(filename)
            if peer.exists():paths.append(peer)
    entries={}
    for current in paths:
        for entry in json.loads(current.read_text())['generations']:
            key=entry['asset']
            if key in entries:
                assert entries[key]['prompt']==entry['prompt'] and entries[key]['raw_path']==entry['raw_path'], 'Conflicting generation records'
            entries[key]=entry
    return dict(mode='built-in image_gen',generations=list(entries.values()))


def source_cells(image):
    width, height = image.size
    return [(column*width//3, row*height//3, (column+1)*width//3, (row+1)*height//3)
            for row in range(3) for column in range(3)]


def inspect_source(name, source):
    image = Image.open(source).convert('RGBA')
    records = []
    for i, cell in enumerate(source_cells(image)):
        mask = image.crop(cell).getchannel('A').point(lambda alpha: 255 if alpha >= 128 else 0)
        records.append(dict(frame=i, cell=cell, solid_bounds=mask.getbbox()))
    return dict(name=name, source=str(source), source_sha256=sha(source.read_bytes()),
                source_dimensions=image.size, alpha_histogram=dict(Counter(image.getchannel('A').get_flattened_data())),
                frames=records, status='inspection only; explicit native-grid recipe and visual review required')


def normalize(recipe, prompts, batch, publish=False):
    name = recipe['name']
    item = next(item for item in batch['varieties'] if item['name'] == name)
    assert recipe['berry'] == item['berry']
    assert recipe['alpha_threshold'] == 128
    source = Path(recipe['raw_path'])
    if not source.is_absolute(): source=ROOT.parent/source
    original = source.read_bytes()
    assert sha(original) == recipe['raw_sha256'], 'Generated source changed'
    image = Image.open(source).convert('RGBA')
    assert list(image.size) == recipe['source_dimensions']
    scale = recipe['integer_scale']
    assert type(scale) is int and scale >= 1
    crops = recipe['frame_crops']
    assert len(crops) == 9
    generation = next(entry for entry in prompts['generations'] if entry['asset'] == recipe['prompt_asset'])
    generation_source=Path(generation['raw_path'])
    if not generation_source.is_absolute(): generation_source=ROOT.parent/generation_source
    assert generation_source.resolve() == source.resolve(), 'Prompt belongs to another generated image'
    assert len(item['fruit_palette']) == 2
    leaf = [rgb(color) for color in LEAF]
    soil = [rgb(color) for color in SOIL]
    fruit = [rgb(color) for color in item['fruit_palette']]
    frames = []
    records = []
    cells = recipe.get('source_cells') or source_cells(image)
    assert len(cells) == 9
    padding = recipe.get('frame_padding') or [[0, 0, 0, 0] for _ in range(9)]
    assert len(padding) == 9
    for i, (cell, crop, pad) in enumerate(zip(cells, crops, padding)):
        left, top, right, bottom = crop
        assert all(type(n) is int for n in crop)
        assert all(type(n) is int and n >= 0 for n in pad)
        assert right-left+pad[0]+pad[2] == 16*scale and bottom-top+pad[1]+pad[3] == 32*scale
        assert cell[0] <= left < right <= cell[2] and cell[1] <= top < bottom <= cell[3]
        native_core = image.crop(cell).getchannel('A').point(lambda alpha: 255 if alpha >= 128 else 0).getbbox()
        assert native_core, ('Missing source plant', name, i)
        whole_core = tuple(native_core[j] + cell[j % 2] for j in range(4))
        assert left <= whole_core[0] <= whole_core[2] <= right and top <= whole_core[1] <= whole_core[3] <= bottom, ('A crop cuts a source feature', name, i)
        extracted = Image.new('RGBA', (16*scale, 32*scale))
        extracted.paste(image.crop(crop), (pad[0], pad[1]))
        if i < 3:
            assert extracted.crop((0, 0, 16*scale, 16*scale)).getchannel('A').point(lambda a: 255 if a >= 128 else 0).getbbox() is None, 'Early frame upper padding contains a plant feature'
        sample = extracted.resize((16, 32), Image.Resampling.NEAREST)
        palette = soil if i == 0 else leaf + fruit
        pixels = []
        for r, g, b, alpha in sample.get_flattened_data():
            if alpha < 128:
                pixels.append((0, 0, 0, 0))
            else:
                pixels.append(min(palette, key=lambda q: (r-q[0])**2 + (g-q[1])**2 + (b-q[2])**2) + (255,))
        sample.putdata(pixels)
        opaque_colors=set(pixel[:3] for pixel in pixels if pixel[3])
        assert opaque_colors <= set(palette)
        if i:
            assert not (opaque_colors & set(soil)), 'Soil color leaked into a plant frame'
        else:
            assert opaque_colors <= set(soil), 'Planted mound contains a non-soil color'
        bounds = sample.getbbox()
        assert bounds, ('Logical plant is empty', name, i)
        if i < 3:
            assert sample.crop((0, 0, 16, 16)).getbbox() is None
            packed = sample.crop((0, 16, 16, 32))
        else:
            packed = sample
        packed_bounds = packed.getbbox()
        bottom_support = [x for x in range(16) if packed.getpixel((x, packed_bounds[3]-1))[3]]
        frames.append(packed)
        records.append(dict(frame=i, role=TITLES[i], source_cell=cell, source_crop=crop,
                            transparent_padding=pad,
                            source_core_bounds=whole_core, all_source_solid_features_retained=True,
                            uniform_integer_scale=scale, native_canvas=[16, 32], packed_size=list(packed.size),
                            plant_bounds=bounds, packed_plant_bounds=packed_bounds,
                            bottom_support=bottom_support, colors=sorted(set(pixel[:3] for pixel in pixels if pixel[3])),
                            color_count=len(set(pixel[:3] for pixel in pixels if pixel[3])),
                            palette_counts={'#'+''.join(f'{c:02X}' for c in color):count
                                            for color,count in sorted(Counter(pixel[:3] for pixel in pixels if pixel[3]).items())},
                            rgba_sha256=sha(packed.tobytes())))
    paired = []
    for a, b in PAIRS:
        first, second = records[a], records[b]
        assert first['packed_plant_bounds'][3] == second['packed_plant_bounds'][3], ('Sway changes the ground anchor', name, a, b)
        assert 8 in first['bottom_support'] and 8 in second['bottom_support'], ('Sway base leaves its native center', name, a, b)
        assert first['rgba_sha256'] != second['rgba_sha256'], ('Sway frames collapsed to identical pixels', name, a, b)
        paired.append(dict(frames=[a, b], same_bottom=True, common_native_center_x=8, distinct_sway_pixels=True))
    sheet = Image.new('RGBA', (16, 240))
    y = 0
    for frame in frames:
        sheet.paste(frame, (0, y))
        y += frame.height
    assert y == 240 and set(sheet.getchannel('A').get_flattened_data()) == {0, 255}
    out = WORK / 'normalized' / name
    out.mkdir(parents=True, exist_ok=True)
    target = out / (name + '.png')
    sheet.save(target)
    assert Image.open(target).convert('RGBA').tobytes() == sheet.tobytes(), 'PNG readback changed pixels'
    canvas = Image.new('RGB', (480, 864), '#d2d0bd')
    draw = ImageDraw.Draw(canvas)
    for i, frame in enumerate(frames):
        full = Image.new('RGBA', (16, 32)); full.paste(frame, (0, 32-frame.height))
        enlarged = full.resize((128, 256), Image.Resampling.NEAREST)
        x, y = i % 3 * 160 + 16, i // 3 * 288 + 24
        draw.text((x, y-18), f'{i}: {TITLES[i]}', fill='black')
        canvas.paste(enlarged, (x, y), enlarged)
    canvas.save(out / (name + '-nine-frame8x.png'))
    private_sources = WORK / 'generated-sources'
    private_sources.mkdir(exist_ok=True)
    private = private_sources / f'{item["berry"]:02d}-{name}-{sha(original)[:12]}.png'
    if private.exists(): assert private.read_bytes() == original
    else: private.write_bytes(original)
    proof = dict(status='normalized and pixel-checked; visual approval required', berry=item['berry'], name=name,
                 target_native_sheet=[16, 240], asset=item['target_asset'],
                 asset_file_sha256=sha(target.read_bytes()), asset_rgba_sha256=sha(sheet.tobytes()),
                 source_private_path=str(private.relative_to(ROOT.parent)), source_sha256=sha(original), source_dimensions=list(image.size),
                 generation=dict(mode='built-in image_gen', prompt=generation['prompt'],
                                 prompt_sha256=sha(generation['prompt'].encode()), references=generation.get('references', [])),
                 recipe=recipe, leaf_flower_palette=LEAF, soil_palette=SOIL, fruit_palette=item['fruit_palette'],
                 frame0_soil_palette_only=True, brown_soil_only_frame0=True, palette_mode='nearest declared RGB only', alpha_threshold=128,
                 all_source_solid_features_retained=True, fractional_scaling_used=False, shapes_redrawn=False,
                 first_three_upper16_rows_transparent=True, paired_anchors=paired, frames=records,
                 png_rgba_roundtrip_identical=True)
    if publish:
        assert recipe.get('visual_reviewed'), 'Record visual review before copying a production asset'
        production = ROOT / item['target_asset']
        assert production.resolve()==(ROOT/'assets/original/berries/gen2'/(name+'.png')).resolve()
        production.parent.mkdir(parents=True, exist_ok=True)
        assert (not production.exists() or production.read_bytes() == target.read_bytes()
                or sha(production.read_bytes()) == recipe.get('replace_asset_sha256')), 'Existing asset differs; keep a versioned candidate for review or pin the explicitly authorized old hash'
        shutil.copyfile(target, production)
        proof['status'] = 'visually reviewed and copied to production asset'
        write_json(production.with_suffix('.provenance.json'), proof)
    write_json(out / (name + '-qa.json'), proof)
    return dict(name=name, status=proof['status'], asset_file_sha256=proof['asset_file_sha256'],
                native_sheet=str(target), preview=str(out / (name + '-nine-frame8x.png')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inspect', type=Path)
    parser.add_argument('--name')
    parser.add_argument('--recipe', type=Path)
    parser.add_argument('--prompts', type=Path, default=WORK/'imagegen-prompts.json')
    parser.add_argument('--batch', type=Path, default=WORK/'berry-batch-spec.json')
    parser.add_argument('--publish', action='store_true')
    parser.add_argument('--from-provenance', type=Path,
                        help='Rebuild one or all normalized trees from the consolidated public provenance and private original images')
    args = parser.parse_args()
    if args.from_provenance:
        document=json.loads(args.from_provenance.read_text(encoding='utf-8'))
        records=[record for record in document['varieties'] if not args.name or record['name']==args.name]
        assert records, 'No matching recorded variety'
        for record in records:
            recipe=record['recipe']
            item=dict(name=record['name'],berry=record['berry'],fruit_palette=record['declared_palette']['fruit'],
                      target_asset=record['asset'])
            generation=dict(asset=recipe['prompt_asset'],prompt=record['generation']['prompt'],
                            references=record['generation']['references'],raw_path=recipe['raw_path'])
            print(json.dumps(normalize(recipe,dict(generations=[generation]),dict(varieties=[item]),args.publish)))
    elif args.inspect:
        print(json.dumps(inspect_source(args.name, args.inspect)))
    else:
        assert args.recipe, 'An explicit source-hashed integer-grid recipe is required'
        print(json.dumps(normalize(json.loads(args.recipe.read_text()), load_prompts(args.prompts),
                                   json.loads(args.batch.read_text()), args.publish)))


if __name__ == '__main__':
    main()
