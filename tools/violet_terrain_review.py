"""Whole Violet raised-ground profile and repeats of the reviewed paved rim."""
import argparse
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
from PIL import Image, ImageDraw, ImageFont
import catalog
import preview
import gen2_extended_review as ext
from interior_review import Imports

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    cache = Path(os.environ['APPDATA']) / 'pokemon-love2d'
    mod = ROOT / 'TileShift'
    output = ROOT / '.work/tileshift-violet-terrain-review'
    output.mkdir(exist_ok=True)
    imports = Imports(cache, ROOT / '.work/tileshift-catalog')
    active = ext.active_rows(mod)
    ground = next(r['base'] for r in active if r.get('base', {}).get('game') == 'emerald' and r['base'].get('tileset') == 'general__petalburg' and r['base']['id'] == 1)
    paving = next(r['donor'] for r in active if r['role'] == 'violet_paved_walkway')
    records = imports.cell_index('firered')
    packed, rows, proofs = {}, [], []
    for game in ext.GAMES:
        data = ext.source(cache, game)
        definition = data['maps']['VIOLET_CITY']
        original, target = Image.new('RGBA', (64, 64)), Image.new('RGBA', (64, 64))
        for dy in range(4):
            for x in range(4):
                y = 22 + dy
                bid = definition['blocks'][y // 2 * definition['width'] + x // 2]
                q = y % 2 * 2 + x % 2
                source = ext.cell_info(cache, game, data, definition['tileset'], bid, q)
                if dy == 0:
                    expected = [44, 44, 60, 60] if x < 3 else [45, 60, 61, 45]
                    collision, mid = (0xb2, 105) if x < 3 else (7, 106)
                elif dy < 3:
                    expected, collision, mid = ([60] * 4, 0, 113) if x < 3 else ([61] * 4, 7, 114)
                else:
                    expected, collision, mid = ([76] * 4, 7, 121) if x < 3 else ([77, 61, 76, 77], 7, 122)
                assert source['tiles'] == expected and source['collision'] == collision
                cell = records['pewter_outdoor', mid]
                ref = {'game': 'firered', 'tileset': 'pewter_outdoor', 'id': mid, 'hash': cell['pixel_sha256']}
                row = {'game': game, 'style': 'gen3', 'map': 'VIOLET_CITY', 'tileset': definition['tileset'],
                    'id': bid, 'quadrant': q, 'x': x, 'y': y, 'sourceCells': [[x, y]], 'sourceHash': source['sourceHash'],
                    'sourceFiles': data['fingerprints'][definition['tileset']], 'sourceCollision': collision,
                    'status': 'reviewed', 'role': 'violet_whole_raised_ground', 'kind': 'native_composite',
                    'base': paving if dy == 3 else ground,
                    'parts': [{'donor': ref, 'layers': ['mid'], 'layerHashes': {'mid': cell['layer_sha256']['mid']},
                               'srcX': 0, 'srcY': 0, 'w': 16, 'h': 16, 'x': 0, 'y': 0}],
                    'evidence': 'PRIVATE whole64x64 Violet raised-ground profile. Full native outdoor105 north rim,106 northeast corner,113 rock top,114 east face,121 front and122 southeast corner retain their complete16px mid-layer features, repeating only the straight rim/top/front sections. The source has no west face inside the map: its raised terrain continues beyond the left map edge. Native outside-alpha pixels use the adjacent grass or paved road rather than imported foreign grass. Original upper boundary0xb2 is a one-way north wall, not a jump ledge; source middle cells remain walkable0, and front/east/corner cells remain blocked7. All source cells, topology, collision, palette/priority and original map boundaries are checked independently per cartridge. Native geometry, encounters, warps and events remain unchanged.'}
                image = preview.replacement_image(cache, row, packed, mod)
                row['compositionPixelHash'] = catalog.sha(image.tobytes())
                native = preview.native_donor(cache, ref, packed, ['mid'], {'mid': cell['layer_sha256']['mid']})
                checked = 0
                for yy in range(16):
                    for xx in range(16):
                        if native.getpixel((xx, yy))[3]:
                            assert image.getpixel((xx, yy)) == native.getpixel((xx, yy))
                            checked += 1
                original.paste(ext.source_image(cache, game, data, source, definition), (x * 16, dy * 16))
                target.paste(image, (x * 16, dy * 16))
                proofs.append({'game': game, 'x': x, 'y': y, 'source_collision': collision, 'native_mid': mid, 'unchanged_native_feature_pixels': checked})
                rows.append(row)
        sheet = Image.new('RGB', (1120, 400), '#18202c')
        draw = ImageDraw.Draw(sheet)
        font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 16)
        draw.text((14, 12), game + ': complete Violet raised ground, original64x64 footprint and source movement', font=font, fill='white')
        draw.text((14, 42), 'Source upper edge blocks upward movement; it is not a jump ledge. Full native outdoor rock features remain unscaled.', fill='#ccd7e5')
        sheet.paste(original.resize((320, 320), Image.Resampling.NEAREST), (14, 76))
        sheet.paste(target.resize((320, 320), Image.Resampling.NEAREST), (574, 76))
        sheet.save(output / (game + '-whole-raised-ground-proposal.png'))
        template = next(r for r in active if r['game'] == game and r['role'] == 'sprout_paved_platform_front_2')
        model = ext.cell_info(cache, game, data, template['tileset'], template['id'], template['quadrant'])
        for x, y in ((26, 23), (28, 23), (29, 23)):
            bid = definition['blocks'][y // 2 * definition['width'] + x // 2]
            q = y % 2 * 2 + x % 2
            cell = ext.cell_info(cache, game, data, definition['tileset'], bid, q)
            assert ext.identity(cell) == ext.identity(model) and cell['tiles'] == [6, 6, 76, 76]
            row = copy.deepcopy(template)
            row.update(id=bid, quadrant=q, x=x, y=y, sourceCells=[[x, y]], sourceHash=cell['sourceHash'],
                role='violet_paved_rock_front', status='reviewed')
            row['evidence'] = 'PRIVATE exact repeat of the already reviewed Sprout paved rock front: identical complete source pixels, movement7, palette slots and priority. The full original upper8px paved approach and lower8px blocked rock face retain the approved native outdoor121 top4/base4 silhouette over native Pewter449 paving. This is not a jump ledge. Exact position in the original Violet map checked; no geometry, collision, warps or events change.'
            rows.append(row)
    live = ext.validate_batch(rows, SimpleNamespace(cache=cache, engine=ROOT / '.tools/engine-0395', output=output), mod)
    for game in ext.GAMES:
        preview.map_preview(cache, output, game, 'VIOLET_CITY', game + '-violet-terrain', active + rows, packed, 2, mod)
    (output / 'candidates.json').write_text(json.dumps(rows, indent=2))
    (output / 'proof.json').write_text(json.dumps({'status': 'private_whole_profile_visual_review', 'rows': len(rows), 'features': proofs, 'live': live}, indent=2))
    if args.activate:
        for row in rows:
            row['evidence'] = row['evidence'].replace('PRIVATE whole', 'Reviewed whole').replace('PRIVATE exact', 'Reviewed exact')
        stats = ext.merge_reviewed(rows, mod / 'mappings/gen2_outdoor_extended.lua')
        (output / 'activation.json').write_text(json.dumps({'mapping': stats, 'live': live}, indent=2))
    print(json.dumps({'rows': len(rows), 'live': live, 'active': args.activate}))


if __name__ == '__main__':
    main()
