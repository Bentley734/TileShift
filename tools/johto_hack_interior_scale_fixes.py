"""Restore full native-size interior ladder, stair and mural details.

The complete16px Emerald ascending-ladder layer is an exact native counterpart.
The available house staircases and vertical portrait cannot fit these compact
GSC cells without losing unique details. Those objects use the user-authorized
original-GSC-geometry palette fallback, explicitly credited as such. No source
layout, collision, entrance or source fingerprint is changed.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

from PIL import Image, ImageDraw, ImageFont

import catalog
import gen2_extended_review as review
import preview
from building_review import decode_layout
from johto_hack_flora import write_changed_rows


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / '.work/tileshift-interior-next/scale-fixes'
DEST = ROOT / 'assets/third_party/johto-hacks/interior-details'
OLD_ROOT = 'assets/third_party/johto-hacks/interiors/'
LADDER = OLD_ROOT + 'crystaldust-ladder-up.png'
STAIRS = {OLD_ROOT + 'firegold-stairs-up.png', OLD_ROOT + 'firegold-stairs-down.png'}
PORTRAITS = {OLD_ROOT + 'crystaldust-painting-left.png', OLD_ROOT + 'crystaldust-painting-right.png'}
TARGETS = STAIRS | PORTRAITS | {LADDER}
WOOD = [[248, 232, 176], [208, 176, 104], [144, 104, 56], [56, 40, 32]]
METAL = [[240, 248, 240], [176, 192, 192], [96, 120, 128], [40, 48, 56]]
MURAL_HEAD = [[248, 240, 184], [232, 200, 96], [152, 136, 56], [56, 72, 40]]
MURAL_STEM = [[232, 248, 216], [176, 216, 112], [88, 144, 72], [40, 72, 48]]
GSC_URL = 'https://github.com/pret/pokecrystal'
EMERALD_URL = 'https://github.com/pret/pokeemerald'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_ladder(cache):
    payload = json.loads((ROOT.parent / '.work/tileshift-catalog/emerald.json').read_text())
    record = next(item for item in payload['cells']
                  if item['pair'] == 'general__cave' and item['mid'] == 574)
    ref = dict(game='emerald', tileset=record['pair'], id=574, hash=record['pixel_sha256'])
    sprite = preview.native_donor(cache, ref, {}, ['mid'], {'mid': record['layer_sha256']['mid']})
    assert sprite.size == (16, 16)
    assert catalog.sha(sprite.tobytes()) == record['layer_sha256']['mid']
    assert sum(pixel[3] > 0 for pixel in sprite.get_flattened_data()) == 165
    assert set(sprite.getchannel('A').get_flattened_data()) == {0, 255}
    path = DEST / 'emerald-ascending-ladder16.png'
    sprite.save(path)
    assert Image.open(path).convert('RGBA').tobytes() == sprite.tobytes()
    base = cache / 'emerald/data/generated/gba/native'
    manifest = catalog.read_lua(base / 'manifest.lua')
    warps = catalog.read_lua(base.parent / 'warps.lua')
    evidence = []
    for map_id in ('EM_GRANITE_CAVE_B1F', 'EM_GRANITE_CAVE_B2F'):
        spec = manifest['layouts'][map_id]
        assert spec['pair'] == ref['tileset']
        layout = decode_layout(base / spec['file'])
        coords = [[i % layout['width'], i // layout['width']]
                  for i, mid in enumerate(layout['mids']) if mid == 574]
        stairs = [warp for warp in warps[map_id] if [warp['x'], warp['y']] in coords]
        assert len(stairs) == len(coords) and coords
        assert all(w['destMap'] == ('EM_GRANITE_CAVE_1F' if map_id.endswith('B1F')
                                    else 'EM_GRANITE_CAVE_B1F') for w in stairs)
        evidence.append(dict(map=map_id, coordinates=coords, native_warps=stairs,
                             layout_file_sha256=layout['file_sha256']))
    return path, dict(asset=path.relative_to(ROOT).as_posix(), assetFileHash=sha(path),
                     source='original_emerald_native_import', credit='Pokemon Emerald / Game Freak',
                     sourceUrl=EMERALD_URL, donor=ref, native_layer='mid',
                     native_layer_rgba_sha256=record['layer_sha256']['mid'],
                     dimensions=[16, 16], pixel_scale=1, opaque_pixels=165,
                     exact_complete_native_layer=True, native_map_evidence=evidence,
                     native_pack_files={name: sha(base / ref['tileset'] / name)
                                        for name in ('mids.idx', 'mids_mid.idx', 'palettes.bin')})


def palette_for(row, original_asset):
    if original_asset in PORTRAITS:
        # Preserve both original halves in place. Source8px tiles17/33 are
        # the timber/wall border;72/73 and88/89 contain the upper/lower mural.
        if original_asset.endswith('painting-left.png'):
            return copy.deepcopy([WOOD, MURAL_HEAD, WOOD, MURAL_STEM])
        return copy.deepcopy([MURAL_HEAD, WOOD, MURAL_STEM, WOOD])
    palette = WOOD if 'domestic' in row['role'] else METAL
    return copy.deepcopy([palette, palette, palette, palette])


def guarded_fields(row):
    return {key: copy.deepcopy(row.get(key)) for key in (
        'game', 'style', 'map', 'tileset', 'id', 'quadrant', 'x', 'y', 'role',
        'sourceHash', 'sourceFiles', 'sourceCells', 'sourceCollision',
        'sourcePriority', 'sourcePalettes', 'sourceWarps')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    DEST.mkdir(parents=True, exist_ok=True)
    cache = Path(os.environ['APPDATA']) / 'pokemon-love2d'
    ladder_path, ladder_proof = extract_ladder(cache)
    packed, staged, changes, records, examples = {}, {}, [], [], {}
    counts = dict(native_ladders=0, recolored_stairs=0, recolored_mural_cells=0)
    all_target_rows = []
    for path in sorted((ROOT / 'mappings').glob('*.lua')):
        rows = preview.read_reviewed(path)
        changed = set()
        for number, prior in enumerate(rows):
            if prior.get('game') not in review.GAMES:
                continue
            old = prior.get('nativeSizeOriginalAsset') or prior.get('asset')
            if old not in TARGETS:
                continue
            row = copy.deepcopy(prior)
            row['nativeSizeOriginalAsset'] = old
            before = preview.replacement_image(cache, prior, packed, ROOT)
            original_fields = guarded_fields(prior)
            if old == LADDER:
                row.update(kind='third_party', asset=ladder_path.relative_to(ROOT).as_posix(),
                           assetFileHash=ladder_proof['assetFileHash'],
                           credit='Pokemon Emerald / Game Freak; complete native ascending-ladder layer.',
                           sourceUrl=EMERALD_URL)
                row.pop('sourceColors', None)
                row['evidence'] = ('Complete native16x16 upward wooden ladder, including every rail, rung and rim pixel, '
                                   'taken from Emerald general__cave574 MID at1:1. The native warp contexts lead '
                                   'from Granite CaveB1F/B2F to the floor above. Transparent native surroundings '
                                   'retain the previously reviewed host floor. Original GSC collision, warp, '
                                   'source layout and interactions remain unchanged.')
                counts['native_ladders'] += 1
            else:
                for key in ('asset', 'assetFileHash', 'assetPixelHash', 'base', 'parts', 'donor',
                            'artOverlay', 'assetFrames', 'foreground', 'occludes', 'animation', 'animated', 'frames'):
                    row.pop(key, None)
                row.update(kind='source_palette', sourceColors=palette_for(row, old),
                           credit='Original Pokemon Gold/Silver/Crystal / Game Freak; palette recolor only.',
                           sourceUrl=GSC_URL)
                row['evidence'] = ('User-authorized original-GSC-geometry fallback where native Gen3 candidates '
                                   'would require shrinking a larger staircase/portrait or clipping unique frame '
                                   'details. Recolor the exact guarded source pixels at1:1; all original steps, '
                                   'rails, shadows and mural details remain in their original positions. '
                                   'This is credited original GSC artwork, not hack-native or generated art. '
                                   'Source layout, collision, entrances and interactions remain unchanged.')
                counts['recolored_mural_cells' if old in PORTRAITS else 'recolored_stairs'] += 1
            row.pop('assetPixelHash', None)
            after = preview.replacement_image(cache, row, packed, ROOT)
            row['compositionPixelHash'] = catalog.sha(after.tobytes())
            assert guarded_fields(row) == original_fields
            all_target_rows.append(row)
            records.append(dict(game=row['game'], map=row['map'], tileset=row['tileset'],
                                source_block=row['id'], source_quadrant=row['quadrant'],
                                source_pixel_sha256=row['sourceHash'], prior_art=old,
                                origin='native_emerald_ladder' if old == LADDER else 'original_gsc_palette_recolor',
                                palette=row.get('sourceColors'), pixel_scale=1,
                                rgba_sha256=row['compositionPixelHash']))
            key = (old, row['sourceHash'])
            if key not in examples:
                examples[key] = (before, after, row['map'], row['sourceHash'])
            if row != prior:
                rows[number] = row
                changed.add(number)
                changes.append(row)
        if changed:
            staged[path] = (rows, changed)
    assert all_target_rows, 'No reviewed interior-scale targets found'
    validation = review.validate_batch(all_target_rows, SimpleNamespace(
        cache=cache, engine=ROOT.parent / '.tools/engine-0395', output=OUT), ROOT)
    assert validation['rows_accepted'] == len(all_target_rows) and validation['rejected'] == 0
    provenance = dict(origin='Full native-size interior detail replacements and explicitly credited original-GSC palette fallbacks.',
                      no_generated_designs=True, no_resizing=True, no_rearranged_mural_halves=True,
                      native_ladder=ladder_proof, replacements=records,
                      files={ladder_path.name: ladder_proof['assetFileHash']})
    (DEST / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 13)
    contact = Image.new('RGBA', (900, ((len(examples) + 3) // 4) * 155), '#18212b')
    draw = ImageDraw.Draw(contact)
    for index, ((old, source_hash), (before, after, map_id, _)) in enumerate(examples.items()):
        x, y = index % 4 * 225, index // 4 * 155
        draw.text((x + 4, y + 3), map_id[:29], fill='white', font=font)
        draw.text((x + 4, y + 21), source_hash[:12], fill='white', font=font)
        contact.alpha_composite(before.resize((80, 80), Image.Resampling.NEAREST), (x + 8, y + 45))
        contact.alpha_composite(after.resize((80, 80), Image.Resampling.NEAREST), (x + 113, y + 45))
        draw.text((x + 8, y + 130), 'Previous', fill='white', font=font)
        draw.text((x + 113, y + 130), 'Native size', fill='white', font=font)
    contact_path = OUT / 'interior-details-before-after.png'
    if changes or not contact_path.exists():
        contact.save(contact_path)
    if args.activate:
        for path, (rows, changed) in staged.items():
            write_changed_rows(path, rows, changed)
    proof = dict(activated=args.activate, changed_rows=len(changes), counts=counts,
                 target_maps=len({(r['game'], r['map']) for r in all_target_rows}),
                 files={path.name: len(changed) for path, (_, changed) in staged.items()},
                 validation=validation, source_geometry_unchanged=True)
    (OUT / 'proof.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(proof, indent=2))


if __name__ == '__main__':
    main()
