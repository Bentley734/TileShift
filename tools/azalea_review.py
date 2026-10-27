"""Finalize the original 3x3 well and activate the reviewed complete town.

The two terrain/facade candidate batches remain private review inputs. Native
art is read from the user's imports; only the original well PNGs are packaged.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

from PIL import Image
import catalog
import gen2_extended_review as ext
import preview
from newbark_building_review import lua

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT.parent / '.work'
PROMPT = (
    'Create a NEW compact 3x3-tile Slowpoke Well exterior sprite for a Pokemon '
    'Emerald/FireRed-style Johto overworld. Reference image is style and subject '
    'reference only; redesign from scratch for a square48x48 logical-pixel '
    'footprint. Transparent background, crisp GBA pixel art, no scenery, grass, '
    'soil, labels or text. Pale mossy yellow-grey stone, olive-grey masonry, '
    'slate outlines, black shaft, short muted golden-olive ladder, pale stone '
    'steps. Complete stone rim in the upper third; centered16x16 entrance in '
    'the middle tile; two or three complete steps in the bottom center tile. '
    'Keep all corners and side walls inside the square. No bucket, crank, '
    'pump, roof, characters or ornaments. Enlarged hard square pixels with '
    'transparent margins, intended for integer reduction to48x48.'
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finalize(source):
    folder = ROOT / 'assets/original/slowpoke-well'
    folder.mkdir(parents=True, exist_ok=True)
    image = Image.open(source).convert('RGBA')
    assert image.size == (1254, 1254), 'Re-review a changed generated canvas'
    alpha = image.getchannel('A').point(lambda a: 255 if a >= 128 else 0)
    bounds = alpha.getbbox()
    side = 960
    start = (image.width - side) // 2
    box = (start, start, start + side, start + side)
    assert bounds and all((box[0] <= bounds[0], box[1] <= bounds[1],
                           box[2] >= bounds[2], box[3] >= bounds[3]))
    image.putalpha(alpha)
    whole = image.crop(box).resize((48, 48), Image.Resampling.NEAREST)
    whole = whole.quantize(colors=16, method=Image.Quantize.FASTOCTREE,
                           dither=Image.Dither.NONE).convert('RGBA')
    assert whole.getchannel('A').getextrema() == (0, 255)
    assert len(whole.getcolors(17)) <= 16
    whole.save(folder / 'well.png')
    assets = {}
    for y in range(3):
        for x in range(3):
            path = folder / f'cell-{x}-{y}.png'
            cell = whole.crop((x * 16, y * 16, x * 16 + 16, y * 16 + 16))
            cell.save(path)
            assets[x, y] = {'asset': path.relative_to(ROOT).as_posix(),
                            'assetFileHash': digest(path)}
    provenance = {
        'origin': 'New original project design made with built-in imagegen',
        'user_choice': 'Create a new3x3 well in the same Gen3 style; do not squash the existing3x4 well',
        'style_reference': 'MetalFlygon08 / SkidMarc25 Johto well, reference only',
        'reference_url': 'https://imgur.com/gallery/testing-out-gen-3-style-tiles-johto-6A43Cji',
        'creator_post': 'https://www.reddit.com/r/PokemonRMXP/comments/yf90qb/full_johto_gen_3_tileset_tile_set_at_the_bottom/',
        'source_file': source.name, 'source_sha256': digest(source),
        'prompt': PROMPT, 'generated_size': list(image.size),
        'visible_alpha_bounds': bounds, 'crop_xyxy': box,
        'integer_reduction': 20, 'runtime_size': [48, 48],
        'processing': 'Whole visible design retained. Transparent-matte noise below128 discarded; uniform20:1 nearest-neighbor reduction,16 colors incl transparency, no dithering. Runtime sprites are never resized.',
        'source_map': 'AZALEA_TOWN', 'source_rect_cells': [30, 6, 3, 3],
        'unchanged_entrance_cell': [31, 7], 'unchanged_step_cell': [31, 8],
        'files': {p.name: digest(p) for p in sorted(folder.glob('*.png'))},
    }
    (folder / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    return assets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    assets = finalize(args.source.resolve())
    folder = WORK / 'tileshift-azalea-foundation-review'
    rows = json.loads((folder / 'candidates.json').read_text())
    rows += json.loads((folder / 'except-well-candidates.json').read_text())
    cache = Path(os.environ['APPDATA']) / 'pokemon-love2d'
    ground = {'game': 'emerald', 'tileset': 'general__petalburg', 'id': 1,
              'hash': '1c7acc0ebc7c5878e77e1dfbbc2828e1a2745c0ded470f1f0152f67193222ed1'}
    for row in rows:
        row['evidence'] = row['evidence'].replace('PRIVATE ', 'Reviewed ')
    for game in ext.GAMES:
        data = ext.source(cache, game)
        definition = data['maps']['AZALEA_TOWN']
        for y in range(3):
            for x in range(3):
                cx, cy = 30 + x, 6 + y
                bid = definition['blocks'][cy // 2 * definition['width'] + cx // 2]
                q = cy % 2 * 2 + cx % 2
                cell = ext.cell_info(cache, game, data, definition['tileset'], bid, q)
                assert cell['collision'] == (0x7b if (x, y) == (1, 1) else 0 if (x, y) == (1, 2) else 7)
                row = {'game': game, 'style': 'gen3', 'map': 'AZALEA_TOWN',
                       'tileset': definition['tileset'], 'id': bid, 'quadrant': q,
                       'x': cx, 'y': cy, 'sourceCells': [[cx, cy]],
                       'sourceHash': cell['sourceHash'],
                       'sourceFiles': data['fingerprints'][definition['tileset']],
                       'sourceCollision': cell['collision'],
                       'sourcePalettes': [a.get('palette', 1) for a in cell['attributes']],
                       'sourcePriority': [bool(a.get('priority')) for a in cell['attributes']],
                       'kind': 'original', 'base': copy.deepcopy(ground),
                       'role': 'azalea_slowpoke_well', 'status': 'reviewed',
                       'evidence': 'New original48x48 Gen3-style well, explicitly chosen by the user instead of squeezing the reference3x4 asset. Complete rim, short ladder and three front steps fit exactly the source3x3 footprint. Native entrance31,7, walkable step31,8, surrounding collisions, NPCs, warps and story scripts remain unchanged.',
                       **assets[x, y]}
                rows.append(row)
        warp = next(w for w in definition['warps'] if w['x'] == 31 and w['y'] == 7)
        assert warp['destMap'] == 'SLOWPOKE_WELL_B1F'
    assert len(rows) == 180
    proof = ext.validate_batch(rows, SimpleNamespace(cache=cache,
        engine=ROOT.parent / '.tools/engine-0395', output=folder), ROOT)
    active = [row for path in sorted((ROOT / 'mappings').glob('*.lua')) if path.name != 'azalea.lua' for row in preview.read_reviewed(path)]
    contexts = [preview.map_preview(cache, folder, game, 'AZALEA_TOWN',
                game + '-complete', active + rows, {}, 2, ROOT) for game in ext.GAMES]
    assert all(c['replaced_occurrences'] == c['visible_cells'] == 720 for c in contexts)
    (folder / 'complete-candidates.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
    (folder / 'complete-proof.json').write_text(json.dumps({'rows': len(rows),
        'live': proof, 'contexts': contexts}, indent=2), encoding='utf-8')
    if args.activate:
        text = '-- Reviewed complete Azalea background, native terrain/gate plus original3x3 well.\nlocal rows={}\nlocal function add(batch)for _,row in ipairs(batch)do rows[#rows+1]=row end end\n'
        for i in range(0, len(rows), 20):
            text += 'add((function()return ' + lua(rows[i:i+20]) + ' end)())\n'
        text += 'return rows\n'
        (ROOT / 'mappings/azalea.lua').write_text(text, encoding='utf-8')
    print(json.dumps({'rows': len(rows), 'live': proof, 'coverage': '720/720 each GSC',
                      'activated': args.activate}))


if __name__ == '__main__':
    main()
