"""Review complete Cherrygrove coastal shapes at their original footprints."""
import argparse
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import catalog
import preview
import gen2_extended_review as ext
from interior_review import Imports
from newbark_building_review import lua

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    cache, mod = Path(os.environ['APPDATA']) / 'pokemon-love2d', ROOT / 'TileShift'
    output = ROOT / '.work/tileshift-cherrygrove-coast-finish-review'
    output.mkdir(exist_ok=True)
    imports = Imports(cache, ROOT / '.work/tileshift-catalog')
    active = ext.active_rows(mod)
    remaining = json.loads((ROOT / '.work/tileshift-map-remaining/crystal-CHERRYGROVE_CITY/remaining-source-cells.json').read_text())
    assert remaining['remaining_cells'] == 76
    ocean = next(r for r in active if r['role'] == 'coastal_ocean_water_interior' and r['donor']['game'] == 'emerald')
    refs, animations = {}, {}

    def ref(game, pair, mid):
        key = game, pair, mid
        if key not in refs:
            record = imports.cell_index(game)[pair, mid]
            refs[key] = {'game': game, 'tileset': pair, 'id': mid, 'hash': record['pixel_sha256']}
        return copy.deepcopy(refs[key])

    def emerald(mid):
        return ref('emerald', 'general__petalburg', mid)

    def animation(mid):
        if mid not in animations:
            row = copy.deepcopy(ocean)
            row['donor'] = emerald(mid)
            row['animation'].pop('frame0Hash', None)
            # All selected water-family members target every native quadrant.
            bank = imports.table('emerald', 'gba/native/general__petalburg/anim_manifest')
            native_bank = next(b for b in bank['banks'] if b['name'] == 'general_water')
            slot = native_bank['mids'].index(mid)
            row['animation']['quadMask'] = native_bank['quads'][slot]
            frames = preview.native_water_frames(cache, row, imports.packed)
            row['animation']['frame0Hash'] = catalog.sha(frames[0].tobytes())
            animations[mid] = row['animation']
        return copy.deepcopy(animations[mid])

    def part(game, pair, mid):
        record = imports.cell_index(game)[pair, mid]
        return {'donor': ref(game, pair, mid), 'layers': ['mid'],
                'layerHashes': {'mid': record['layer_sha256']['mid']},
                'srcX': 0, 'srcY': 0, 'x': 0, 'y': 0, 'w': 16, 'h': 16}

    rows, updates = [], []
    for old in active:
        if old.get('map') != 'CHERRYGROVE_CITY' or not old.get('donor'):
            continue
        mid = old['donor']['id']
        if old['donor']['game'] != 'emerald' or mid not in (44, 52):
            continue
        if old['role'] not in ('rocky_coast_west', 'coastal_ocean_water_interior'):
            continue
        row = copy.deepcopy(old)
        target = 400 if mid == 44 else 368
        row['donor'], row['animation'] = emerald(target), animation(target)
        row['evidence'] += ' Complete coherent native Emerald coastal family: Route114 inward corners408/410 adjoin400/402,393 and368. Use the corresponding native368 water and400 west wall throughout this coastal body;52 and44 are distinct native variants and are not assumed interchangeable. All8 actual native frames and source mechanics remain checked.'
        updates.append(row)
    assert updates
    for game in ext.GAMES:
        data = ext.source(cache, game)
        definition = data['maps']['CHERRYGROVE_CITY']
        for source in remaining['cells']:
            for x, y in source['coordinates']:
                bid = definition['blocks'][y // 2 * definition['width'] + x // 2]
                q = y % 2 * 2 + x % 2
                cell = ext.cell_info(cache, game, data, definition['tileset'], bid, q)
                assert cell['tiles'] == source['tiles'] and cell['collision'] == source['collision']
                row = {'game': game, 'style': 'gen3', 'map': 'CHERRYGROVE_CITY', 'tileset': definition['tileset'],
                       'id': bid, 'quadrant': q, 'x': x, 'y': y,
                       'sourceHash': cell['sourceHash'], 'sourceFiles': data['fingerprints'][definition['tileset']],
                       'sourceCells': [[x, y]], 'sourceCollision': cell['collision'],
                       'sourceOceanBounds': [0, 4, 17, 17], 'status': 'reviewed'}
                tiles = tuple(cell['tiles'])
                if bid == 10:
                    assert cell['collision'] == 7
                    mid = (104, 106, 120, 122)[q]
                    row.update(role='rocky_coast_whole_outcrop_' + str(q), kind='native_composite',
                               base=emerald(368), parts=[part('firered', 'pewter_outdoor', mid)],
                               animated=True, animation=animation(368))
                    evidence = 'The complete32x32 source rocky outcrop uses all four complete16px native FRPewter convex cliff corners104/106/120/122, on the corresponding source quadrants. Native middle planes retain every rock pixel with no cropping, scaling or flipping; only their original grass underlay is replaced with the coherent animated Emerald coastal water. The seven original32px footprints remain blocked; the adjacent walkable island is separate.'
                elif tiles == (88, 88, 88, 88):
                    assert cell['collision'] == 0x27
                    row.update(role='rocky_coast_sea_rock_barrier', kind='native_composite',
                               base=emerald(368), parts=[part('emerald', 'general__petalburg', 404)],
                               animated=True, animation=animation(368))
                    evidence = 'The source16px permanent sea-rock barrier is distinct from walkable water (collision0x27, not0x29). Complete Emerald404 is actually used as a standalone16px rock at Lilycove61,4, surrounded on all four sides by414 shallow water. Its205 opaque middle-plane pixels match every non-water pixel of the full native rock; all51 outside pixels become matching animated coastal water. No native rock pixel is removed and its blocking behavior remains native.'
                elif tiles == (60, 60, 60, 60):
                    assert cell['collision'] == 0
                    row.update(role='coastal_walkable_rock_top', donor=emerald(401))
                    evidence = 'This plain source rock-top interior is walkable collision0, unlike the blocked outcrops. Native Emerald401 is an actual walkable MOUNTAIN_TOP surface at Route119/Fortree24..26,47, and has identical full native pixels in the selected Petalburg primary family. Complete16px material retains the original island landing area, items, movement and event logic.'
                else:
                    mid = {(20, 59, 20, 59): 402, (20, 75, 20, 20): 410, (77, 20, 20, 20): 408}[tiles]
                    assert cell['collision'] == 0x29
                    role = {402: 'east', 410: 'inward_northeast', 408: 'inward_northwest'}[mid]
                    row.update(role='rocky_coast_' + role, donor=emerald(mid), animated=True, animation=animation(mid))
                    evidence = 'Actual native coherent Emerald coastal counterpart, handedness preserved. Route114 inwardNW408 at14,29 has north400/west393/east368/south368; inwardNE410 at12,17 has north402/west368/east393/south368. All referenced native shapes have identical full RGBA pixels between Fallarbor and Petalburg. Position scope keeps the northeast freshwater pond separate from shared marine source IDs. All8 native frames are used; source water collision0x29, Surf, fishing and map geometry remain native.'
                row['evidence'] = 'PRIVATE bounded Cherrygrove finish. ' + evidence
                if row.get('parts'):
                    row['compositionPixelHash'] = catalog.sha(preview.replacement_image(cache, row, imports.packed, mod).tobytes())
                rows.append(row)
    assert len(rows) == 228
    # Build the staged set with original-key replacements, preserving unrelated rows.
    def key(r):
        return tuple(r.get(k) for k in ('game', 'style', 'tileset', 'map', 'id', 'quadrant', 'x', 'y'))
    changed = {key(r): r for r in updates}
    staged = [changed.get(key(r), r) for r in active] + rows
    live = ext.validate_batch(updates + rows, SimpleNamespace(cache=cache, engine=ROOT / '.tools/engine-0395', output=output), mod)
    contexts = [preview.map_preview(cache, output, game, 'CHERRYGROVE_CITY', game + '-complete-coast', staged, {}, 2, mod) for game in ext.GAMES]
    assert all(c['replaced_occurrences'] == 720 for c in contexts), contexts
    (output / 'candidates.json').write_text(json.dumps(updates + rows, indent=2, sort_keys=True))
    (output / 'mapping.lua').write_text('return ' + lua(updates + rows), encoding='utf-8')
    (output / 'proof.json').write_text(json.dumps({'new_rows': 228, 'family_updates': len(updates), 'live': live, 'contexts': contexts}, indent=2))
    if args.activate:
        target = mod / 'mappings/gen2_outdoor_extended.lua'
        original = target.read_bytes()
        assert original.rstrip().endswith(b'return rows')
        # Keep the existing9231+24 mappings byte-for-byte; replace only exact
        # Cherrygrove keys, then append new position-specific coastal rows.
        text = "local function coastKey(row)return table.concat({row.game,row.style,row.tileset,row.map or '',row.id,row.quadrant,row.x or '',row.y or ''},':')end\nlocal coastChanges={}\nlocal function coastAdd(batch)for _,row in ipairs(batch)do coastChanges[#coastChanges+1]=row end end\n"
        for batch in range(0, len(updates + rows), 24):
            text += 'coastAdd((function()return ' + lua((updates + rows)[batch:batch+24]) + ' end)())\n'
        text += "local coastIndex={} for i,row in ipairs(rows)do coastIndex[coastKey(row)]=i end\nfor _,row in ipairs(coastChanges)do local i=coastIndex[coastKey(row)] if i then rows[i]=row else rows[#rows+1]=row end end\nreturn rows\n"
        target.write_bytes(original.rstrip()[:-len(b'return rows')] + text.replace('\n', '\r\n').encode('utf-8'))
    print(json.dumps({'new_rows': len(rows), 'family_updates': len(updates), 'live': live, 'activated': args.activate}))


if __name__ == '__main__':
    main()
