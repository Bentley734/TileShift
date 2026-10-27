"""Finalize built-in imagegen designs with whole-pixel crops and integer reduction.

Transparent-matte noise is removed, then each retained plant uses a GBA-sized
palette. The native game assets are16/32px; the runtime never resizes them.
"""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('C:/Users/LSDMTHC/.codex/generated_images/01a1779e-1657-7893-8b0a-94f8fb9ac828')
SPECS = (
    ('johto-meadow-grass', 'JOHTO MEADOW', 'grass', 16, 1024, 'exec-bf660b60-f0e1-414a-9484-94b1a3cd9200.png', 'Dense pointed meadow encounter grass, lime highlights, emerald blades, dark roots; native16px whole-pixel design.'),
    ('johto-clover-grass', 'JOHTO CLOVER', 'grass', 16, 1024, 'exec-283f6d0a-8115-4e0b-9b9d-4e0788450c92.png', 'Dense wild encounter grass with rounded clover leaves between upright blades; native16px whole-pixel design.'),
    ('johto-red-flowers', 'JOHTO RED BLOOMS', 'flowers', 16, 1024, 'exec-cb3073d3-b9f8-422a-b590-f6600ed1e467.png', 'Three red five-petal ground flowers with golden centers and short green stems; native16px whole-pixel design.'),
    ('johto-blue-ground-flowers', 'JOHTO BLUE CUPS', 'flowers', 16, 768, 'exec-2631c6b8-22e8-4abf-b55c-b21a7f22aa20.png', 'Refine the blue-violet/lilac reference into three UPRIGHT ground flowers, short stems, leaves below near the soil; no hanging pose. Native16px whole-pixel design.'),
    ('johto-oak32', 'JOHTO OAK', 'big_trees', 32, 1024, 'exec-b8f6bcf2-cd78-465f-b32d-caa31cfb7ed5.png', 'Complete compact Gen3/Johto forest oak: domed green canopy, visible short brown trunk and roots, native32x32, full canopy and roots inside the2x2 tile footprint.'),
    ('johto-pine32', 'JOHTO PINE', 'big_trees', 32, 768, 'exec-d2846d15-a5d4-432b-b0fc-9e5cab06d442.png', 'Complete compact Gen3/Johto conifer: three jade-green tiers, full top tip, trunk and roots, native32x32 inside the2x2 tile footprint.'),
)


def main():
    folder = ROOT / 'assets/original/flora'
    folder.mkdir(exist_ok=True)
    records, entries = [], {}
    for identifier, label, category, size, side, filename, prompt in SPECS:
        path = SOURCE / filename
        source = Image.open(path).convert('RGBA')
        assert source.size == (1254, 1254) and side % size == 0
        start = (source.width - side) // 2
        box = (start, start, start + side, start + side)
        alpha = source.getchannel('A').point(lambda value: 255 if value >= 128 else 0)
        bounds = alpha.getbbox()
        assert bounds and box[0] <= bounds[0] and box[1] <= bounds[1] and box[2] >= bounds[2] and box[3] >= bounds[3], identifier + ' would clip a visible plant feature'
        source.putalpha(alpha)
        native = source.crop(box).resize((size, size), Image.Resampling.NEAREST)
        native = native.quantize(colors=16, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).convert('RGBA')
        assert native.getchannel('A').getextrema() == (0, 255)
        assert len(native.getcolors(maxcolors=17)) <= 16
        target = folder / (identifier + '.png')
        native.save(target)
        record = {'id': identifier, 'label': label, 'category': category, 'size': size,
                  'source_file': filename, 'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                  'crop_xyxy': box, 'visible_alpha_bounds': bounds, 'integer_reduction': side // size,
                  'final_alpha_bounds': native.getbbox(), 'prompt': prompt,
                  'png_sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
        records.append(record)
        entries[identifier] = {'id': identifier, 'label': label, 'size': size,
                               'asset': target.relative_to(ROOT).as_posix(), 'hash': record['png_sha256']}
        if category == 'big_trees':
            for q in range(4):
                cell = folder / f'{identifier}-q{q}.png'
                native.crop((q % 2 * 16, q // 2 * 16, q % 2 * 16 + 16, q // 2 * 16 + 16)).save(cell)
    provenance = {'origin': 'Original project designs generated with the built-in imagegen tool',
        'processing': 'Center crop contains every alpha>=128 plant pixel. Generated transparent-matte noise below128 is discarded. Nearest-neighbor reduction uses integer factors only; colors quantized to16 incl transparency without dithering. Complete canopies, petals, stems and roots retained. Native runtime PNGs are never resized.',
        'animation': 'Flower choices use four integer-pixel sway frames; bottom two occupied rows stay anchored and no shifted row clips a petal or leaf.',
        'records': records, 'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.glob('*.png'))}}
    (folder / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    output = ROOT.parent / '.work/tileshift-original-flora'
    output.mkdir(exist_ok=True)
    (output / 'entries.json').write_text(json.dumps(entries, indent=2) + '\n')
    canvas = Image.new('RGB', (6 * 176, 230), '#18212b')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15)
    for i, (identifier, label, _, size, *_rest) in enumerate(SPECS):
        image = Image.open(folder / (identifier + '.png'))
        scaled = image.resize((160, 160), Image.Resampling.NEAREST)
        draw.text((i * 176 + 8, 10), label, fill='white', font=font)
        canvas.paste(scaled, (i * 176 + 8, 40), scaled)
        draw.text((i * 176 + 8, 205), f'{size}x{size} native pixels', fill='#c4cdd8', font=font)
    canvas.save(output / 'native-design-contact.png')
    print(json.dumps(entries, indent=2))


if __name__ == '__main__':
    main()
