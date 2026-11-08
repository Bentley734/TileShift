"""Replace complete G/S/C Mart front displays with native CrystalDust cabinets.

Ordinary cabinets retain their 32x32 source footprint. Department-store 64x32
units repeat only complete middle modules and retain both native end panels.
The builder changes artwork only, leaving imported maps and scripts intact.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import copy
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

HERE = Path(__file__).resolve()
WORKSPACE = next((p for p in [Path.cwd(), *HERE.parents] if (p / '.tools/python').is_dir()), Path.cwd())
sys.path.insert(0, str(WORKSPACE / '.tools/python'))
from PIL import Image
import catalog
import preview
import gen2_extended_review as ext

GAMES = ('gold', 'silver', 'crystal')
MARTS = tuple(name + '_MART' for name in ('CHERRYGROVE', 'VIOLET', 'AZALEA', 'ECRUTEAK',
    'OLIVINE', 'BLACKTHORN', 'VIRIDIAN', 'PEWTER', 'CERULEAN', 'LAVENDER', 'VERMILION', 'SAFFRON', 'FUCHSIA'))
DEPARTMENTS = ('GOLDENROD_DEPT_STORE_4F', 'CELADON_DEPT_STORE_4F')
MODULES = ('mappings/johto_mart_finish.lua', 'mappings/gen2_kanto_rooms_finish.lua',
           'mappings/gen2_facility_floor_audit.lua')
MARKER = b'-- BEGIN REVIEWED CRYSTALDUST MART FRONT SHELVES'
ART_FIELDS = {'donor', 'base', 'parts', 'asset', 'kind', 'artOverlay', 'compositionPixelHash',
              'assetFileHash', 'assetPixelHash', 'credit', 'sourceUrl', 'assetFrames',
              'foreground', 'occludes', 'frames', 'animation', 'animated'}


def key(row):
    return tuple(row.get(name) for name in ('game', 'style', 'tileset', 'map', 'id', 'quadrant', 'x', 'y'))


def fixtures(name):
    return [(0, 4, 2, 2)] if name in MARTS else [(2, 4, 4, 2), (12, 6, 2, 2)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mod', type=Path, default=HERE.parents[1])
    parser.add_argument('--cache', type=Path, default=Path(os.environ['APPDATA']) / 'pokemon-love2d')
    parser.add_argument('--engine', type=Path, default=WORKSPACE / '.work/tileshift-engine-0410')
    parser.add_argument('--output', type=Path, default=WORKSPACE / '.work/tileshift-mart-shelf-fix/audit/review')
    parser.add_argument('--validate', action='store_true')
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    mod, cache, output = args.mod.resolve(), args.cache.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    provenance_path = mod / 'assets/third_party/johto-hacks/mart-front-shelves/provenance.json'
    provenance = json.loads(provenance_path.read_text(encoding='utf-8'))
    assets = {}
    for name, module in provenance['source_modules'].items():
        image = Image.open(mod / module['asset']).convert('RGBA')
        assert image.size == (16, 16) and set(image.getchannel('A').get_flattened_data()) <= {0, 255}
        assert catalog.sha((mod / module['asset']).read_bytes()) == module['assetFileHash']
        assert catalog.sha(image.tobytes()) == module['assetPixelHash']
        assert module['native_alpha_unchanged']
        assets[name] = module
    assert set(assets) == {'top-left','top-center','top-right','bottom-left','bottom-center','bottom-right'}
    originals, baselines, owners = {}, {}, {}
    for relative in MODULES:
        original = (mod / relative).read_bytes()
        newline = b'\r\n' if b'\r\n' in original else b'\n'
        pristine = original.split(MARKER, 1)[0] + b'return rows' + newline if MARKER in original else original
        assert pristine.rstrip().endswith(b'return rows')
        baseline = catalog.plain(catalog.LUA.execute(pristine.decode('utf-8-sig')))
        originals[relative] = pristine
        baselines[relative] = baseline
        for row in baseline:
            assert key(row) not in owners, 'Do not create ambiguous mapping precedence'
            owners[key(row)] = (relative, row)
    generic = {(r['game'], r.get('map'), r['id'], r['quadrant']):(name,r)
               for name, rows in baselines.items() for r in rows
               if r['game'] in GAMES and r.get('map') in MARTS + DEPARTMENTS
               and r['tileset'] == 'TILESET_MART' and r['id'] == 21 and 'x' not in r}
    assert len(generic) == 180
    updates, scope, guards = defaultdict(dict), [], {}
    packed = {}
    for game in GAMES:
        data = ext.source(cache, game)
        for name in MARTS + DEPARTMENTS:
            definition = data['maps'][name]
            assert definition['tileset'] == 'TILESET_MART'
            blocks = catalog.lua_array(definition['blocks'])
            for fx, fy, width, height in fixtures(name):
                assert height == 2 and width in (2, 4)
                for dy in range(height):
                    for dx in range(width):
                        x, y = fx + dx, fy + dy
                        bid = blocks[y // 2 * definition['width'] + x // 2]
                        q = y % 2 * 2 + x % 2
                        assert bid == 21
                        relative, source = generic[game, name, bid, q]
                        cell = ext.cell_info(cache, game, data, definition['tileset'], bid, q)
                        assert cell['sourceHash'] == source['sourceHash']
                        assert cell['collision'] == source['sourceCollision']
                        assert data['fingerprints'][definition['tileset']] == source['sourceFiles']
                        assert [x, y] in source['sourceCells']
                        assert [bool(a.get('priority')) for a in cell['attributes']] == source['sourcePriority']
                        assert [a.get('palette', 1) for a in cell['attributes']] == source['sourcePalettes']
                        centered = width == 4 and dx in (1, 2)
                        row = copy.deepcopy(source)
                        base = copy.deepcopy(row['base'])
                        for field in ART_FIELDS:
                            row.pop(field, None)
                        if centered:
                            row.update(x=x, y=y, sourceCells=[[x, y]])
                        piece = ('top-' if dy == 0 else 'bottom-') + ('center' if centered else 'left' if dx == 0 else 'right')
                        module = assets[piece]
                        row.update(kind='third_party', asset=module['asset'], assetFileHash=module['assetFileHash'],
                                   assetPixelHash=module['assetPixelHash'], credit=module['credit'], sourceUrl=module['sourceUrl'],
                                   base=base, role='johto_shop_crystaldust_front_shelf_' + piece.replace('-', '_'), status='reviewed')
                        row['evidence'] = ('Reviewed complete native CrystalDust Mart display module ' + str(module['donor_mid'])
                            + '/top, retaining every native frame, side-panel, foot and transparent exterior pixel at1:1 scale. '
                            'The ordinary32x32 and department-store32x32/64x32 source cabinet footprints remain unchanged. '
                            'Wider cabinets repeat only complete native center modules between intact left/right end panels. '
                            'The existing reviewed room floor remains visible through the original native alpha. '
                            'Source block21 only; the distinct narrow back-counter display and Gen1 stock cases are not replaced. '
                            'Original source geometry, collision, palette/priority, map events, shop scripts and actors are unchanged.')
                        row['compositionPixelHash'] = catalog.sha(preview.replacement_image(cache, row, packed, mod).tobytes())
                        k = key(row)
                        assert k not in updates[relative] or updates[relative][k] == row
                        updates[relative][k] = row
                        scope.append({'game':game,'map':name,'x':x,'y':y,'id':bid,'quadrant':q,
                                      'asset':module['asset'],'module':relative,'sourceKey':list(key(source))})
                        guards[game, name] = source['sourceFiles']
    all_updates = [row for group in updates.values() for row in group.values()]
    assert len(scope) == 228 and len(all_updates) == 204
    assert Counter(r['game'] for r in scope) == {game:76 for game in GAMES}
    assert sum(key(row) in owners for row in all_updates) == 180
    assert sum(key(row) not in owners for row in all_updates) == 24
    validation = ext.validate_batch(all_updates, SimpleNamespace(cache=cache, engine=args.engine, output=output), mod) if args.validate else None
    stats, results = {}, {}
    for relative in MODULES:
        baseline = baselines[relative]
        changed = updates[relative]
        body, compact = ext.write_compact(list(changed.values()), None)
        ending = b'\r\n' if b'\r\n' in originals[relative] else b'\n'
        prefix = originals[relative].rstrip()[:-len(b'return rows')]
        footer = '''local function shelfKey(row)return table.concat({row.game,row.style,row.tileset,row.map or '',row.id,row.quadrant,row.x or '',row.y or ''},':')end
local shelfUpdates=(function()
''' + body + '''end)()
local shelfIndex={}for i,row in ipairs(rows)do shelfIndex[shelfKey(row)]=i end
for _,row in ipairs(shelfUpdates)do local i=shelfIndex[shelfKey(row)];if i then rows[i]=row else rows[#rows+1]=row end end
return rows
'''
        result = prefix + MARKER + ending + footer.replace('\n', ending.decode()).encode('utf-8')
        expanded = catalog.plain(catalog.LUA.execute(result.decode('utf-8-sig')))
        expected = {key(row): changed.get(key(row), row) for row in baseline}
        expected.update(changed)
        assert len(expanded) == len(expected) and {key(row):row for row in expanded} == expected
        replaced = sum(key(row) in owners for row in changed.values())
        added = len(changed) - replaced
        stats[relative] = {'before':len(baseline),'after':len(expanded),'replaced':replaced,'added':added,
                           'compact':compact,'sha256':catalog.sha(result)}
        results[relative] = result
    (output / 'candidates.json').write_text(json.dumps(all_updates, indent=2)+'\n', encoding='utf-8')
    (output / 'scope.json').write_text(json.dumps(scope, indent=2)+'\n', encoding='utf-8')
    (output / 'scenes.json').write_text(json.dumps([{'game':game,'map':name,'complete':True} for game in GAMES for name in MARTS+DEPARTMENTS], indent=2)+'\n', encoding='utf-8')
    proof = {'status':'reviewed_native_crystaldust_mart_front_shelves','effective_cells':228,'cells_per_game':76,
             'maps_per_game':15,'map_variants':45,'existing_rows_replaced':180,'new_position_rows':24,
             'native_modules':6,'fixtures_per_game':{'32x32':15,'64x32':2},'mapping_stats':stats,
             'source_guards':{game+':'+name:files for (game,name),files in guards.items()},
             'live_decoder':validation,'provenance_sha256':catalog.sha(provenance_path.read_bytes())}
    if args.activate:
        for relative, result in results.items():
            (mod / relative).write_bytes(result)
    (output / 'proof.json').write_text(json.dumps(proof, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'effective_cells':228,'rows':204,'live_decoder':validation,'activated':args.activate},indent=2))


if __name__ == '__main__':
    main()
