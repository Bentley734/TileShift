"""Reproduce the native Ilex Shrine, Park bench and whirlpool replacements.

Default writes only to a private authoring output. --verify-existing checks
every generated image against the installed mod assets without editing them.
--activate writes assets only after ROM identities and native-pixel invariants
have passed. ROM binaries and full map exports are never included in a mod ZIP.
"""
from pathlib import Path
from collections import deque
import argparse
import hashlib
import json
from PIL import Image
from firegold_extract import Rom

ROOT = Path(__file__).resolve().parents[1]
EXTRACTS = ROOT.parent / '.work/tileshift-firegold'
ASSETS = ROOT / 'assets/third_party/johto-hacks/extras'
CD_SHA = '51196cba923c315d0088b747b5cdee704f2ac057cd493f9ddf226fb7227302cf'
LC_SHA = '925cd6bd824e3e903636340e5f3519bc9ecb2f5f75c0bb87248213250514c965'
WHIRLPOOL_DESCRIPTOR = 0xF22080
WHIRLPOOL_FRAME_TABLE = 0xF1F7C8
WHIRLPOOL_FRAMES = (0xF1F5C8, 0xF1F648, 0xF1F6C8, 0xF1F748)


def sha(raw): return hashlib.sha256(raw).hexdigest()


def connected_mask(image, colors, seeds=None):
    w, h = image.size
    if seeds is None:
        seeds = [(x, y) for y in range(h) for x in range(w)
                 if x in (0, w-1) or y in (0, h-1)]
    seen = {p for p in seeds if image.getpixel(p) in colors}
    queue = deque(seen)
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            p = x+dx, y+dy
            if 0 <= p[0] < w and 0 <= p[1] < h and p not in seen and image.getpixel(p) in colors:
                seen.add(p)
                queue.append(p)
    return seen


def clear_background(image, mask):
    result = image.copy()
    for p in mask: result.putpixel(p, (0, 0, 0, 0))
    for y in range(image.height):
        for x in range(image.width):
            if (x, y) not in mask: assert result.getpixel((x, y)) == image.getpixel((x, y))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--crystaldust', type=Path, default=Path('C:/Users/LSDMTHC/Desktop/Pokémon CrystalDust.gba'))
    parser.add_argument('--liquid-crystal', type=Path, default=Path('C:/Users/LSDMTHC/Desktop/pokemon_liquid_crystal_beta_3.3.00100.gba'))
    parser.add_argument('--extracts', type=Path, default=EXTRACTS)
    parser.add_argument('--output', type=Path, default=EXTRACTS/'extras-authoring')
    parser.add_argument('--verify-existing', action='store_true')
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    cd, lc = Rom(args.crystaldust, 'rse'), Rom(args.liquid_crystal, 'frlg')
    assert cd.sha256 == CD_SHA and lc.sha256 == LC_SHA, 'This authoring recipe requires the exact reviewed user ROMs'
    for game, expected in (('crystaldust', CD_SHA), ('liquidcrystal', LC_SHA)):
        metadata = json.loads((args.extracts/game/'catalog.json').read_text())
        assert metadata['rom_sha256'] == expected, 'Map exports belong to a different ROM'
    images, records = {}, {}

    # The native shrine is24x34. Exact2x nearest-neighbor reduction preserves
    # its whole roof/door/legs; the resulting12x17 object fits the16x32 source.
    path = args.extracts/'liquidcrystal/maps/g01_m000-flat.png'
    image = Image.open(path).convert('RGBA').crop((300, 589, 324, 623))
    grass = {c for c in image.get_flattened_data() if c[1] > c[0] and c[1] > c[2]}
    mask = connected_mask(image, grass)
    silhouette = clear_background(image, mask)
    shrine = Image.new('RGBA', (16, 32))
    shrine.paste(silhouette.resize((12, 17), Image.Resampling.NEAREST), (2, 15))
    images['ilex-shrine.png'] = shrine
    for q in range(2): images[f'ilex-shrine-{q}.png'] = shrine.crop((0, q*16, 16, q*16+16))
    records['shrine'] = {'rom_sha256': LC_SHA, 'map': 'g01_m000', 'source_png_sha256': sha(path.read_bytes()),
        'source_rect_px': [300, 589, 24, 34], 'integer_reduction': 2, 'target_offset_px': [2, 15],
        'removed_connected_sourcegrass_pixels': len(mask), 'whole_object_preserved': True}

    # This32x32 source contains one complete gray-blue bench. Warm paving
    # colors are background even in the enclosed openings between slats.
    path = args.extracts/'crystaldust/maps/g00_m036-flat.png'
    source = Image.open(path).convert('RGBA')
    image = source.crop((160, 640, 192, 672))
    paving = set(source.crop((160, 672, 192, 688)).get_flattened_data())
    mask = {(x, y) for y in range(32) for x in range(32) if image.getpixel((x, y)) in paving}
    bench = clear_background(image, mask)
    images['park-bench.png'] = bench
    for q in range(4): images[f'park-bench-{q}.png'] = bench.crop((q%2*16, q//2*16, q%2*16+16, q//2*16+16))
    records['bench'] = {'rom_sha256': CD_SHA, 'map': 'g00_m036', 'source_png_sha256': sha(path.read_bytes()),
        'source_rect_px': [160, 640, 32, 32], 'ground_reference_rect_px': [160, 672, 32, 16],
        'integer_reduction': 1, 'removed_source_paving_pixels': len(mask), 'whole_object_preserved': True}

    # Native metatile409 uses8px graphics474..477, palette4. Verify the exact
    # animation descriptor and four raw frames before decoding each phase.
    assert cd.u32(WHIRLPOOL_DESCRIPTOR) == 0x08000000+WHIRLPOOL_FRAME_TABLE
    assert cd.u16(WHIRLPOOL_DESCRIPTOR+8) == 474 and cd.u16(WHIRLPOOL_DESCRIPTOR+12) == 4
    assert tuple(cd.off(cd.u32(WHIRLPOOL_FRAME_TABLE+i*4)) for i in range(4)) == WHIRLPOOL_FRAMES
    census = cd.discover()
    violet = next(m for m in census['maps'] if m['id'] == 'g00_m000')
    pair = violet['primary_tileset'], violet['secondary_tileset']
    primary = cd.tileset(pair[0]); original = primary['tile_bytes']
    frames, corner_masks = [], []
    corners = ((0, 0), (15, 0), (0, 15), (15, 15))
    for address in WHIRLPOOL_FRAMES:
        raw = bytearray(original)
        raw[474*32:478*32] = cd.raw[address:address+128]
        primary['tile_bytes'] = bytes(raw); cd.pair_cache.clear()
        image = cd.pair(*pair)[409]['flat']
        frames.append(image)
        corner_masks.append(connected_mask(image, {image.getpixel(p) for p in corners}, corners))
    outside = set.intersection(*corner_masks)
    assert len(outside) == 24, 'Native animated whirlpool corner silhouette changed'
    for i, image in enumerate(frames): images[f'whirlpool-{i}.png'] = clear_background(image, outside)
    records['whirlpool'] = {'rom_sha256': CD_SHA, 'metatile': 409, 'native_attribute': 235,
        'animation_descriptor_offset': WHIRLPOOL_DESCRIPTOR, 'frame_pointer_table_offset': WHIRLPOOL_FRAME_TABLE,
        'raw_4bpp_frame_offsets': WHIRLPOOL_FRAMES, 'raw_frame_sha256': [sha(cd.raw[p:p+128]) for p in WHIRLPOOL_FRAMES],
        'integer_reduction': 1, 'transparent_background_coordinates': sorted(map(list, outside)),
        'mask': 'Shared corner-connected native water background only; complete vortex and foam retained.',
        'eight_phase_sequence': [0, 0, 1, 1, 2, 2, 3, 3]}

    args.output.mkdir(parents=True, exist_ok=True)
    staged = args.output/'assets'; staged.mkdir(exist_ok=True)
    for name, image in images.items():
        assert image.size in ((16, 16), (16, 32), (32, 32))
        assert {c[3] for c in image.get_flattened_data()} <= {0, 255}
        image.save(staged/name)
    verified = []
    if args.verify_existing:
        for name, image in images.items():
            existing = Image.open(ASSETS/name).convert('RGBA')
            assert existing.size == image.size and existing.tobytes() == image.tobytes(), name
            verified.append(name)
    proof = {'roms_verified': [CD_SHA, LC_SHA], 'objects': records, 'files': {name: sha((staged/name).read_bytes()) for name in images},
        'native_pixels_preserved': True, 'binary_alpha': True, 'existing_images_exact': verified}
    (args.output/'source-proof.json').write_text(json.dumps(proof, indent=2)+'\n')
    if args.activate:
        # ROM identity, native descriptor data, unchanged retained pixels,
        # binary alpha and optional current-asset comparisons all passed above.
        ASSETS.mkdir(parents=True, exist_ok=True)
        for name in images: (ASSETS/name).write_bytes((staged/name).read_bytes())
        (ASSETS/'provenance.json').write_text(json.dumps(proof, indent=2)+'\n')
    print(json.dumps({'images': len(images), 'existing_exact': len(verified), 'activated': args.activate,
                      'proof': str(args.output/'source-proof.json')}))


if __name__ == '__main__': main()
