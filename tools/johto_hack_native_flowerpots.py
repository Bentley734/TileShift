"""Use a complete native one-cell flowerpot, retaining every source pixel.

Only the selected FireGold MID-layer object is packaged. Native field/map
exports remain private; source maps, floors, collision and events are unchanged.
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
import copy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

import catalog
import gen2_extended_review as review
from johto_hack_flora import write_changed_rows
import preview


ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT.parent / '.work/tileshift-firegold/firegold'
OUTPUT = ROOT.parent / '.work/tileshift-interior-next'
DEST = ROOT / 'assets/third_party/johto-hacks/interior-plants'
OLD_ASSET = 'assets/third_party/johto-hacks/interiors/firegold-flowerbox.png'
ASSET_NAME = 'firegold-potted-flower16.png'
SOURCE_PAIR = '082d4bb4_082d4be4'
SOURCE_MAP = 'g44_m096'
SOURCE_RECT = (64, 37, 80, 53)
SOURCE_ROM_SHA256 = 'c65f698ffb844b99836a36dc0752e8b57ebd45be53be364cb3cfe52aa0cc74ce'
SOURCE_URL = 'https://www.pokecommunity.com/threads/pok%C3%A9mon-fire-gold-1-4.473130/'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def alpha_component(image: Image.Image, seed: tuple[int, int]) -> set[tuple[int, int]]:
    """Identify the complete native object, independently of the final crop."""
    assert image.getpixel(seed)[3]
    seen, queue = {seed}, deque([seed])
    while queue:
        x, y = queue.popleft()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                point = x + dx, y + dy
                if (0 <= point[0] < image.width and 0 <= point[1] < image.height
                        and point not in seen and image.getpixel(point)[3]):
                    seen.add(point)
                    queue.append(point)
    return seen


def extract() -> tuple[dict, Path]:
    data = json.loads((PRIVATE / 'catalog.json').read_text())
    assert data['rom_sha256'] == SOURCE_ROM_SHA256
    source = next(row for row in data['maps'] if row['id'] == SOURCE_MAP)
    assert source['pair'] == SOURCE_PAIR
    assert [source['grid'][y * source['width'] + 4] & 1023 for y in (2, 3)] == [689, 697]
    paths = {layer: PRIVATE / 'maps' / f'{SOURCE_MAP}-{layer}.png'
             for layer in ('under', 'mid', 'over', 'flat')}
    images = {layer: Image.open(path).convert('RGBA') for layer, path in paths.items()}
    strip = images['mid'].crop((64, 32, 80, 64))
    component = alpha_component(strip, (5, 6))
    assert len(component) == 150
    assert (min(x for x, y in component), min(y for x, y in component),
            max(x for x, y in component) + 1, max(y for x, y in component) + 1) == (2, 6, 14, 21)
    # The flower component is separated by three transparent rows from the
    # counter facade, which begins at y24. Neither the counter nor its floor
    # needs color erasure: native MID alpha already isolates the whole pot.
    assert all(not strip.getpixel((x, y))[3] for y in range(21, 24) for x in range(16))
    cropped = {layer: image.crop(SOURCE_RECT) for layer, image in images.items()}
    sprite = cropped['mid']
    assert cropped['over'].getchannel('A').getbbox() is None
    assert Image.alpha_composite(cropped['under'], sprite).tobytes() == cropped['flat'].tobytes()
    assert sprite.size == (16, 16) and sprite.getchannel('A').getbbox() == (2, 1, 14, 16)
    retained = {(x, y + 5) for y in range(16) for x in range(16) if sprite.getpixel((x, y))[3]}
    assert retained == component, 'Crop must retain the entire flower/pot and no neighboring MID pixels'
    for x, y in component:
        assert sprite.getpixel((x, y - 5)) == strip.getpixel((x, y))
    DEST.mkdir(parents=True, exist_ok=True)
    target = DEST / ASSET_NAME
    sprite.save(target)
    record = {
        'origin': 'Complete native FireGold potted flower; no scaled or synthesized pixels.',
        'source': 'firegold', 'source_rom_name': data['rom_name'],
        'source_rom_sha256': data['rom_sha256'], 'source_pair': SOURCE_PAIR,
        'source_map': SOURCE_MAP, 'layer': 'mid', 'source_rect_ltrb': list(SOURCE_RECT),
        'source_metatiles': [689, 697], 'source_map_cells': [[4, 2], [4, 3]],
        'native_source_parts': [
            {'metatile': 689, 'source_rect_xywh': [0, 5, 16, 11], 'destination': [0, 0]},
            {'metatile': 697, 'source_rect_xywh': [0, 0, 16, 5], 'destination': [0, 11]},
        ],
        'source_map_file_sha256': {layer: sha(path) for layer, path in paths.items()},
        'source_atlas_mid_sha256': sha(PRIVATE / 'pairs' / SOURCE_PAIR / 'mid.png'),
        'native_dimensions': [16, 16], 'pixel_scale': 1,
        'complete_object_alpha_component_bounds_in_source_strip': [2, 6, 14, 21],
        'whole_native_object_retained': True, 'unchanged_native_object_pixels': len(component),
        'opaque_source_pixels_retained': len(component), 'alpha_bounds': [2, 1, 14, 16],
        'transparent_exterior_pixels': 256 - len(component), 'floor_color_erasure': False,
        'neighbor_counter_pixels_included': 0,
        'native_under_and_mid_recompose_flat_exactly': True,
        'credit': 'FireGold 1.4 by Tzx211; native potted flower artwork.',
        'sourceUrl': SOURCE_URL,
        'asset': target.relative_to(ROOT).as_posix(), 'assetFileHash': sha(target),
        'rgba_sha256': hashlib.sha256(sprite.tobytes()).hexdigest(),
        'supersedes': OLD_ASSET, 'files': {target.name: sha(target)},
    }
    (DEST / 'provenance.json').write_text(json.dumps(record, indent=2) + '\n')
    return record, target


def mark_historical_provenance(replacement: str) -> None:
    path = ROOT / 'assets/third_party/johto-hacks/interiors/provenance.json'
    record = json.loads(path.read_text())
    for piece in record['pieces']:
        if piece.get('asset') == OLD_ASSET:
            piece['whole_object_retained'] = False
            piece['active_gsc_use'] = False
            piece['superseded_by'] = replacement
            piece['historical_status'] = (
                'Superseded: the old crop contains a partial wide flower cluster and neighboring pixels; '
                'the active replacement is a complete native16x16 pot at original pixel size.')
    record.setdefault('superseded_assets', {})[OLD_ASSET] = replacement
    path.write_text(json.dumps(record, indent=2) + '\n')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    recipe, target = extract()
    cache = Path(os.environ['APPDATA']) / 'pokemon-love2d'
    packed, staged, selected = {}, {}, []
    changes, maps, files = [], Counter(), Counter()
    azalea_pink = 0
    for path in sorted((ROOT / 'mappings').glob('*.lua')):
        rows = preview.read_reviewed(path)
        indexes = set()
        for index, prior in enumerate(rows):
            if prior.get('game') not in ('gold', 'silver', 'crystal'):
                continue
            direct = prior.get('asset') == OLD_ASSET
            overlay = prior.get('artOverlay', {}).get('asset') == OLD_ASSET
            if not (direct or overlay):
                continue
            row = copy.deepcopy(prior)
            if direct:
                row.update(kind='third_party', asset=recipe['asset'], assetFileHash=recipe['assetFileHash'])
            if overlay:
                row['artOverlay'].update(kind='third_party', asset=recipe['asset'], hash=recipe['assetFileHash'])
            row.update(credit=recipe['credit'], sourceUrl=SOURCE_URL)
            row['evidence'] = (
                prior.get('evidence', '') + ' Complete native FireGold potted flower replaces the partial reduced flowerbox. '
                'All150flower, leaf, pot and shadow pixels retain their original size; native MID alpha exposes '
                'the unchanged room floor. No neighboring counter pixels, resizing or new collision.')
            row['compositionPixelHash'] = catalog.sha(preview.replacement_image(cache, row, packed, ROOT).tobytes())
            assert row.get('base') == prior.get('base') and row.get('parts') == prior.get('parts')
            if row.get('map') == 'AZALEA_GYM' and overlay:
                azalea_pink += 1
            rows[index] = row
            indexes.add(index)
            selected.append(row)
            changes.append({'file': path.name, 'row': index, 'game': row['game'], 'map': row['map'],
                            'role': row['role'], 'direct_asset': direct, 'art_overlay': overlay})
            maps[(row['game'], row['map'])] += 1
            files[path.name] += 1
        if indexes:
            staged[path] = rows, indexes
    proof = (review.validate_batch(selected, SimpleNamespace(cache=cache,
             engine=ROOT.parent / '.tools/engine-0395', output=OUTPUT), ROOT)
             if selected else {'rows_accepted': 0, 'rejected': 0})
    report = {'activated': args.activate, 'source_recipe': recipe,
              'changed_rows': len(selected), 'all_base_floors_and_native_parts_preserved': True,
              'azalea_pink_planter_overlays_preserved': azalea_pink,
              'mapping_files': dict(files), 'game_map_variants': len(maps),
              'maps': [{'game': game, 'map': name, 'rows': count}
                       for (game, name), count in sorted(maps.items())],
              'validation': proof, 'changes': changes}
    if args.activate:
        for path, (rows, indexes) in staged.items():
            write_changed_rows(path, rows, indexes)
        mark_historical_provenance(recipe['asset'])
    (OUTPUT / 'native-flowerpot-activation-proof.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items()
                      if key not in ('source_recipe', 'changes', 'maps')}, indent=2))


if __name__ == '__main__':
    main()
