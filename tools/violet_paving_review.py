"""Review Violet paving together with its two pavement-backed Center corners."""
import argparse
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
from PIL import Image
import catalog
import preview
import gen2_extended_review as ext
import architecture_review as common

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    cache = Path(os.environ['APPDATA']) / 'pokemon-love2d'
    mod = ROOT / 'TileShift'
    output = ROOT / '.work/tileshift-violet-paving-review'
    output.mkdir(exist_ok=True)
    paving = json.loads((ROOT / '.work/tileshift-gen2-outdoor-cliff-review/violet-paving-candidates.json').read_text())
    assert len(paving) == 45
    for row in paving:
        row.update(status='reviewed', evidence=row['evidence'].replace('Private Violet paved-walkway proposal.', 'Reviewed Violet paved walkway and adjacent roof background.'))
    base = paving[0]['donor']
    assert all(r['donor'] == base for r in paving)
    target = mod / 'mappings/buildings_extended.lua'
    architecture = preview.read_reviewed(target)
    changes, packed, proof = [], {}, []
    for old in architecture:
        if old['game'] in ext.GAMES and old.get('map') == 'VIOLET_CITY' and old['role'] == 'architecture_center' and old['x'] in (30, 31) and old['y'] == 22:
            source = ext.source(cache, old['game'])
            definition = source['maps']['VIOLET_CITY']
            x, y = old['x'], old['y'] - 1
            bid = definition['blocks'][y // 2 * definition['width'] + x // 2]
            north = ext.cell_info(cache, old['game'], source, definition['tileset'], bid, y % 2 * 2 + x % 2)
            assert north['tiles'] == [6, 6, 6, 6] and north['collision'] == 0, 'Northwest roof must back onto original paving'
            for nx in (32, 33):
                nbid = definition['blocks'][y // 2 * definition['width'] + nx // 2]
                neighbor = ext.cell_info(cache, old['game'], source, definition['tileset'], nbid, y % 2 * 2 + nx % 2)
                assert neighbor['tiles'] == [5, 5, 5, 5], 'Northeast roof must retain its original grassy plot'
            row = copy.deepcopy(old)
            row['base'] = copy.deepcopy(base)
            before = preview.replacement_image(cache, old, packed, mod)
            after = preview.replacement_image(cache, row, packed, mod)
            native = Image.new('RGBA', (16, 16))
            for part in row['parts']:
                piece = preview.native_donor(cache, part['donor'], packed, part.get('layers'), part.get('layerHashes'))
                sx, sy = part.get('srcX', 0), part.get('srcY', 0)
                native.alpha_composite(piece.crop((sx, sy, sx + part['w'], sy + part['h'])), (part['x'], part['y']))
            ground = preview.native_donor(cache, base, packed)
            holes = retained = 0
            for y in range(16):
                for x in range(16):
                    alpha = native.getpixel((x, y))[3]
                    assert alpha in (0, 255)
                    if alpha:
                        assert after.getpixel((x, y)) == before.getpixel((x, y)) == native.getpixel((x, y))
                        retained += 1
                    else:
                        assert after.getpixel((x, y)) == ground.getpixel((x, y))
                        holes += 1
            assert holes > 0
            row['compositionPixelHash'] = catalog.sha(after.tobytes())
            row['evidence'] += ' Violet local background correction: the two northwest Center roof cells back onto the actual public paved path. Only transparent roof pixels use native Pewter449 paving; every opaque roof pixel is unchanged. The northeast roof remains grass-backed. Native source layout, warps and collision are unchanged.'
            changes.append((old, row))
            proof.append({'game': row['game'], 'x': row['x'], 'y': row['y'], 'paved_background_pixels': holes, 'opaque_roof_pixels_unchanged': retained})
    assert len(changes) == 6
    changed = {(r['game'], r['map'], r['x'], r['y']): r for _, r in changes}
    complete_buildings = [changed.get((r['game'], r.get('map'), r.get('x'), r.get('y')), r) for r in architecture
                          if r['game'] in ext.GAMES and r.get('map') == 'VIOLET_CITY' and r['role'] == 'architecture_center']
    assert len(complete_buildings) == 48
    probe = copy.deepcopy(complete_buildings + paving)
    for row in probe:
        if 'x' in row:
            row['sourceCells'] = [[row['x'], row['y']]]
    live = ext.validate_batch(probe, SimpleNamespace(cache=cache, engine=ROOT / '.tools/engine-0395', output=output), mod)
    all_rows = []
    for path in sorted((mod / 'mappings').glob('*.lua')):
        for row in preview.read_reviewed(path):
            key = (row['game'], row.get('map'), row.get('x'), row.get('y'))
            all_rows.append(changed.get(key, row) if path.name == 'buildings_extended.lua' else row)
    all_rows += paving
    contexts = [preview.map_preview(cache, output, game, 'VIOLET_CITY', game + '-violet-paved', all_rows, packed, 2, mod) for game in ext.GAMES]
    (output / 'proof.json').write_text(json.dumps({'status': 'private_combined_context_review', 'roof_changes': proof,
        'paving_rows': 45, 'whole_center_rows_live_checked': 48, 'live': live, 'contexts': contexts}, indent=2))
    if args.activate:
        replacements = {(old['game'], old['x'], old['y']): (old, new) for old, new in changes}
        lines, found = [], set()
        for raw in target.read_bytes().splitlines(keepends=True):
            if b'VIOLET_CITY' in raw and b'architecture_center' in raw and raw.lstrip().startswith(b'{'):
                literal = raw.decode().strip().removesuffix(',')
                old = catalog.plain(catalog.LUA.execute('return ' + literal))
                key = (old['game'], old['x'], old['y'])
                if key in replacements:
                    expected, new = replacements[key]
                    assert old == expected and key not in found
                    ending = b'\r\n' if raw.endswith(b'\r\n') else b'\n'
                    raw = ('  ' + common.lua(new) + ',').encode() + ending
                    found.add(key)
            lines.append(raw)
        assert found == set(replacements), 'Expected reviewed literal rows not found exactly once'
        target.write_bytes(b''.join(lines))
        result = preview.read_reviewed(target)
        assert len(result) == len(architecture)
        assert sum(a != b for a, b in zip(result, architecture)) == 6
        stats = ext.merge_reviewed(paving, mod / 'mappings/gen2_outdoor_extended.lua')
        (output / 'activation.json').write_text(json.dumps({'roof_rows_corrected': 6, 'paving': stats, 'live': live}, indent=2))
    print(json.dumps({'roof_changes': proof, 'live': live, 'active': args.activate}))


if __name__ == '__main__':
    main()
