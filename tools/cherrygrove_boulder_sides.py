"""Continue reviewed coastal banks behind Cherrygrove's shore-attached boulders."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import os
import sys
from types import SimpleNamespace

HERE = Path(__file__).resolve()
WORKSPACE = next((p for p in [Path.cwd(), *HERE.parents] if (p / '.tools/python').is_dir()), Path.cwd())
sys.path.insert(0, str(WORKSPACE / '.tools/python'))
from PIL import Image
import catalog
import preview
import gen2_extended_review as ext

MAP = 'CHERRYGROVE_CITY'
FOLDER = 'assets/third_party/johto-hacks/cherrygrove-boulder-sides'
MARKER = b'-- BEGIN REVIEWED CHERRYGROVE BOULDER SIDE BANKS\n'
NATIVE_BASES = {(11, 4): 394, (16, 12): 393, (17, 12): 394, (17, 13): 402}
COMPOUNDS = {(10, 5): ('south-bank-left-rock', 398), (11, 5): ('south-east-bank-right-rock', 399)}
CREDIT = 'CrystalDust by Sierraffinity and contributors, native coastal bank; Game Freak FireRed, complete original rock middle plane.'
URL = 'https://github.com/Sierraffinity/CrystalDust'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def key(row):
    return tuple(row.get(k) for k in ('game', 'style', 'tileset', 'map', 'id', 'quadrant', 'x', 'y'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mod', type=Path, default=HERE.parents[1])
    parser.add_argument('--cache', type=Path, default=Path(os.environ['APPDATA']) / 'pokemon-love2d')
    parser.add_argument('--native-root', type=Path, default=WORKSPACE / '.work/tileshift-firegold')
    parser.add_argument('--output', type=Path, default=WORKSPACE / '.work/tileshift-mart-shelf-fix/shore-audit')
    parser.add_argument('--validate', action='store_true')
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    mod, cache, output = args.mod.resolve(), args.cache.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    mapping = mod / 'mappings/gen2_outdoor_extended.lua'
    original = mapping.read_bytes()
    if MARKER in original:
        pristine = original.split(MARKER, 1)[0] + b'return rows\n'
        baseline = catalog.plain(catalog.LUA.execute(pristine.decode('utf-8-sig')))
    else:
        pristine = original
        baseline = preview.read_reviewed(mapping)
    assert pristine.rstrip().endswith(b'return rows')
    index = {key(row): row for row in baseline}
    assert len(index) == len(baseline)
    selected = {(r['game'], r['x'], r['y']): r for r in baseline
                if r['game'] in ext.GAMES and r.get('map') == MAP and r['style'] == 'gen3' and 'x' in r}
    cd_root = args.native_root.resolve() / 'crystaldust'
    cd_pair = '083df704_083df71c'
    cd_catalog = json.loads((cd_root / 'catalog.json').read_text(encoding='utf-8'))
    cd_top_path = cd_root / 'pairs' / cd_pair / 'top.png'
    cd_top = Image.open(cd_top_path).convert('RGBA')
    cd_meta_path = cd_top_path.parent / 'metatiles.json'
    assets_path = mod / FOLDER
    assets_path.mkdir(parents=True, exist_ok=True)
    packed, assets, files = {}, {}, {}
    compound_proof = []
    for xy, (name, mid) in COMPOUNDS.items():
        row = selected['crystal', *xy]
        assert row['kind'] == 'native_composite' and len(row['parts']) == 1
        part = row['parts'][0]
        assert [part.get(k, 0) for k in ('srcX', 'srcY', 'x', 'y')] == [0, 0, 0, 0]
        assert [part['w'], part['h']] == [16, 16]
        assert part['donor']['game'] == 'firered' and part['layers'] == ['mid']
        rock = preview.native_donor(cache, part['donor'], packed, part['layers'], part['layerHashes'])
        sx, sy = mid % 16 * 16, mid // 16 * 16
        shore = cd_top.crop((sx, sy, sx + 16, sy + 16))
        assert shore.getbbox() and set(shore.getchannel('A').get_flattened_data()) <= {0, 255}
        image = Image.alpha_composite(shore, rock)
        retained = 0
        for y in range(16):
            for x in range(16):
                pixel = rock.getpixel((x, y))
                assert pixel[3] in (0, 255)
                if pixel[3]:
                    assert image.getpixel((x, y)) == pixel
                    retained += 1
                else:
                    assert image.getpixel((x, y)) == shore.getpixel((x, y))
        path = assets_path / (name + '.png')
        image.save(path)
        assert Image.open(path).convert('RGBA').tobytes() == image.tobytes()
        files[path.name] = sha(path.read_bytes())
        assets[xy] = {'asset': FOLDER + '/' + path.name, 'assetFileHash': files[path.name],
                      'assetPixelHash': sha(image.tobytes()), 'shore_mid': mid, 'shore': shore, 'rock': rock,
                      'part': part, 'credit': CREDIT, 'sourceUrl': URL}
        compound_proof.append({'asset': FOLDER + '/' + path.name, 'assetFileHash': files[path.name],
                               'assetPixelHash': sha(image.tobytes()), 'target': list(xy),
                               'shore_source': {'hack': 'crystaldust', 'pair': cd_pair, 'mid': mid,
                                                'plane': 'top', 'rect': [sx, sy, 16, 16],
                                                'rgba_sha256': sha(shore.tobytes())},
                               'rock_source': part, 'rock_rgba_sha256': sha(rock.tobytes()),
                               'opaque_rock_pixels_retained_exactly': retained, 'logical_size': [16, 16]})
    assert set(files) == {path.name for path in assets_path.glob('*.png')}
    provenance = {'origin': CREDIT, 'sourceUrl': URL,
                  'rom_sha256': cd_catalog['rom_sha256'], 'source_reference_map': 'g00_m010', 'source_pair': cd_pair,
                  'source_reference_reason': 'Cherrygrove uses this exact native pair; its unmodified metatile atlas also contains the south-facing bank modules.',
                  'source_top_plane_sha256': sha(cd_top_path.read_bytes()),
                  'source_metatiles_sha256': sha(cd_meta_path.read_bytes()),
                  'recipe': 'Alpha-compose the complete native CrystalDust south bank TOP plane, then the unchanged complete native FireRed rock MID plane. Preserve every opaque rock pixel and all native bank pixels outside the rock silhouette. Keep all remaining pixels transparent for the current selected animated water. No scaling, recoloring or generated pixels.',
                  'files': files, 'compounds': compound_proof}
    fr_meta_path = cache / 'firered/data/generated/gba/meta.json'
    fr_meta = json.loads(fr_meta_path.read_text(encoding='utf-8'))
    provenance['firered_import'] = {'version': fr_meta['version_id'], 'rom_md5': fr_meta['md5'],
                                  'metadata_sha256': sha(fr_meta_path.read_bytes())}
    (assets_path / 'provenance.json').write_text(json.dumps(provenance, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    donor_catalog = json.loads((WORKSPACE / '.work/tileshift-catalog/emerald.json').read_text(encoding='utf-8'))
    donors = {r['mid']: r for r in donor_catalog['cells'] if r['pair'] == 'general__petalburg'}
    anim_root = cache / 'emerald/data/generated/gba/native/general__petalburg'
    manifest = catalog.read_lua(anim_root / 'anim_manifest.lua')
    bank = next(b for b in manifest['banks'] if b['name'] == 'general_water')
    changes, frame_checks = [], 0
    for game in ext.GAMES:
        source = ext.source(cache, game)
        definition = source['maps'][MAP]
        for xy in sorted(set(NATIVE_BASES) | set(COMPOUNDS), key=lambda p: (p[1], p[0])):
            old = selected[game, *xy]
            row = copy.deepcopy(old)
            cell = ext.cell_info(cache, game, source, row['tileset'], row['id'], row['quadrant'])
            assert cell['collision'] == row['sourceCollision'] == 7 and row['id'] == 10
            assert row['sourceHash'] == cell['sourceHash'] and row['sourceFiles'] == source['fingerprints'][row['tileset']]
            assert row['sourceCells'] == [list(xy)]
            if xy in NATIVE_BASES:
                mid = NATIVE_BASES[xy]
                record = donors[mid]
                row['base'] = {'game': 'emerald', 'tileset': 'general__petalburg', 'id': mid, 'hash': record['pixel_sha256']}
                template = selected[game, 10, 4]['animation']
                spec = copy.deepcopy(template)
                spec['quadMask'] = bank['quads'][bank['mids'].index(mid)]
                spec.pop('frame0Hash', None)
                spec['frame0Hash'] = sha(preview.native_water_frames(cache, {'donor': row['base'], 'animation': spec}, packed)[0].tobytes())
                row['animation'] = spec
                assert row['parts'] == old['parts']
            else:
                item = assets[xy]
                assert old['parts'] == [item['part']]
                row.pop('parts')
                row.update(kind='third_party', asset=item['asset'], assetFileHash=item['assetFileHash'],
                           assetPixelHash=item['assetPixelHash'], credit=CREDIT, sourceUrl=URL)
                assert row['base']['id'] == 368
            row['evidence'] = ('Reviewed the original shore-attached Cherrygrove boulders only. North/east banks continue behind exposed rock side corners; the lower corner uses complete native CrystalDust south-bank geometry with every original FireRed rock pixel retained. Exact position scope preserves the separate island boulder and four sea outcrops. All eight native water frames, selected water styles, original blocked collision7, map layout and NPC/event logic remain unchanged.')
            row['compositionPixelHash'] = sha(preview.replacement_image(cache, row, packed, mod).tobytes())
            frames = preview.replacement_frames(cache, row, packed, mod)
            assert len(frames) == 8
            if xy in COMPOUNDS:
                item = assets[xy]
                water = preview.native_water_frames(cache, {'donor': row['base'], 'animation': row['animation']}, packed)
                for actual, background in zip(frames, water):
                    expected = Image.alpha_composite(Image.alpha_composite(background, item['shore']), item['rock'])
                    assert actual.tobytes() == expected.tobytes()
                    frame_checks += 1
            changes.append(row)
    assert len(changes) == 18 and len({key(r) for r in changes}) == 18
    replacements = {key(row): row for row in changes}
    expected = [replacements.get(key(row), row) for row in baseline]
    assert sum(a != b for a, b in zip(baseline, expected)) == 18
    live = ext.validate_batch(changes, SimpleNamespace(cache=cache, engine=WORKSPACE / '.work/tileshift-engine-0410', output=output), mod) if args.validate else None
    body, compact = ext.write_compact(changes, None)
    prefix = pristine.rstrip()[:-len(b'return rows')].rstrip() + b'\n'
    footer = '''local function boulderSideKey(row)return table.concat({row.game,row.style,row.tileset,row.map or '',row.id,row.quadrant,row.x or '',row.y or ''},':')end
local boulderSideUpdates=(function()
''' + body + '''end)()
local boulderSideIndex={}for i,row in ipairs(rows)do boulderSideIndex[boulderSideKey(row)]=i end
for _,row in ipairs(boulderSideUpdates)do local i=assert(boulderSideIndex[boulderSideKey(row)],'Missing reviewed boulder cell');rows[i]=row end
return rows
'''
    result = prefix + MARKER + footer.encode('utf-8')
    expanded = catalog.plain(catalog.LUA.execute(result.decode('utf-8-sig')))
    assert len(expanded) == len(baseline) and {key(r): r for r in expanded} == {key(r): r for r in expected}
    (output / 'candidates.json').write_text(json.dumps(changes, indent=2) + '\n', encoding='utf-8')
    (output / 'candidate-mapping.lua').write_bytes(result)
    report = {'status': 'reviewed_native_side_banks', 'changed_rows': 18, 'cells_per_game': 6,
              'original_other_rows_unchanged': len(baseline) - 18, 'native_compound_frames_checked': frame_checks,
              'all_native_rock_pixels_retained': True, 'native_water_frames_per_row': 8, 'live': live,
              'mapping_before_sha256': sha(original), 'mapping_after_sha256': sha(result), 'compact': compact}
    if args.activate:
        mapping.write_bytes(result)
    (output / 'proof.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'changed_rows': 18, 'frames_checked': frame_checks, 'live': live, 'activated': args.activate}, indent=2))


if __name__ == '__main__':
    main()
