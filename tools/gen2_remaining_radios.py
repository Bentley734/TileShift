"""Replace the five remaining G/S/C domestic radio recolors with CrystalDust.

Reuse the complete native 16x24 radio and stand with its existing 8px top
padding in the original two blocked source cells. Mount Moon's upper cell
currently has a plain wall recipe; its source fingerprint is the same radio
header as the other rooms. No source maps, actors, interactions, or assets change.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from types import SimpleNamespace

W = next(p for p in Path(__file__).resolve().parents
         if (p / '.tools/python').is_dir() and (p / '.work').is_dir())
sys.path.insert(0, str(W / '.tools/python'))
from PIL import Image

GAMES = ('gold', 'silver', 'crystal')
PREFIX = 'assets/third_party/johto-hacks/newbark-crystaldust'
TARGETS = {
    'ECRUTEAK_ITEMFINDER_HOUSE': ('mappings/johto_domestic_finish.lua', 2),
    'ECRUTEAK_LUGIA_SPEECH_HOUSE': ('mappings/johto_domestic_finish.lua', 2),
    'KURTS_HOUSE': ('mappings/johto_domestic_finish.lua', 6),
    'MAHOGANY_MART_1F': ('mappings/johto_domestic_finish.lua', 0),
    'MOUNT_MOON_GIFT_SHOP': ('mappings/gen2_kanto_rooms_finish.lua', 0),
}
MARKER = '-- BEGIN REMAINING COMPLETE NATIVE RADIOS'
GUARDS = ('game', 'style', 'map', 'tileset', 'id', 'quadrant', 'sourceHash',
          'sourceCells', 'sourceFiles', 'sourceCollision', 'sourcePriority',
          'sourcePalettes', 'sourceWarps')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    if isinstance(value, dict):
        return {key: canonical(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [canonical(item) for item in value]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--mod-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--engine', type=Path, default=W / '.work/tileshift-engine-0420')
    args = parser.parse_args()
    base, mod, out = args.baseline.resolve(), args.mod_root.resolve(), args.output.resolve()
    assert base != mod and out not in (base, mod)
    assert json.loads((base / 'manifest.json').read_text())['version'] == '0.46.6'
    sys.path.insert(0, str(mod / 'tools'))
    import gen2_extended_review as review
    import preview
    from newbark_building_review import lua
    from lupa.luajit21 import LuaRuntime
    cache = Path(os.environ['APPDATA']) / 'pokemon-love2d'
    out.mkdir(parents=True, exist_ok=True)
    modules = list(dict.fromkeys(module for module, _ in TARGETS.values()))
    before = {module: preview.read_reviewed(base / module) for module in modules}
    updates = {module: {} for module in modules}
    packed, changes, new_rows, receipts = {}, [], [], []
    native_whole = Image.new('RGBA', (16, 32))
    pieces = {}
    provenance = json.loads((mod / PREFIX / 'domestic-provenance.json').read_text())
    assert provenance['source_rom_sha256'] == '51196cba923c315d0088b747b5cdee704f2ac057cd493f9ddf226fb7227302cf'
    for y in (0, 1):
        path = mod / PREFIX / f'domestic-radio-0-{y}.png'
        image = Image.open(path).convert('RGBA')
        assert image.size == (16, 16)
        assert set(image.getchannel('A').get_flattened_data()) <= {0, 255}
        pieces[y] = image
        native_whole.paste(image, (0, y * 16))
    assert sha(native_whole.tobytes()) == '6bbce221aec7d4caf4e0668c1c25f05eeac49995845d0ac5e80901219a5ca6be'
    for game in GAMES:
        data = review.source(cache, game)
        for map_id, (module, x) in TARGETS.items():
            md = data['maps'][map_id]
            assert md['height'] * 2 == 8 and md['width'] * 2 == (16 if map_id == 'KURTS_HOUSE' else 8)
            selected = [row for row in before[module]
                        if row.get('game') == game and row.get('map') == map_id
                        and row.get('style') == 'gen3'
                        and row.get('sourceCells') in ([[x, 0]], [[x, 1]])]
            assert len(selected) == 2
            receipts.append(dict(game=game, map=map_id,
                definition_sha256=sha(json.dumps(canonical(md), separators=(',', ':')).encode()),
                bg_events=md.get('bgEvents', []), objects=md.get('objects', []), warps=md.get('warps', [])))
            for old in selected:
                y = old['sourceCells'][0][1]
                assert old['sourceCollision'] == (7 if y == 0 else 148)
                assert old['role'] == ('kanto_room_complete_traditional_wall' if map_id == 'MOUNT_MOON_GIFT_SHOP' and y == 0
                                       else 'johto_domestic_radio_head' if y == 0 else 'johto_domestic_radio')
                if y == 0:
                    assert old['sourceHash'] == '163baf529e26334e733c3257a1213edc955641eb9aa1f4f4da44b715746b308b'
                cell = review.cell_info(cache, game, data, md['tileset'], old['id'], old['quadrant'])
                assert cell['sourceHash'] == old['sourceHash'] and cell['collision'] == old['sourceCollision']
                assert data['fingerprints'][md['tileset']] == old['sourceFiles']
                assert [bool(value.get('priority')) for value in cell['attributes']] == old['sourcePriority']
                assert [value.get('palette', 1) for value in cell['attributes']] == old['sourcePalettes']
                row = copy.deepcopy(old)
                # The Mount Moon head currently is the room's native wall.
                # Keep that exact wall donor as the transparent radio's base.
                backdrop = copy.deepcopy(old.get('base') or old.get('donor'))
                assert backdrop
                row.pop('donor', None)
                asset = f'{PREFIX}/domestic-radio-0-{y}.png'
                row.update(kind='third_party', base=backdrop, asset=asset,
                    assetFileHash=sha((mod / asset).read_bytes()), assetPixelHash=sha(pieces[y].tobytes()),
                    role='gen2_complete_crystaldust_domestic_radio_' + str(y),
                    credit='CrystalDust by Sierraffinity and contributors; complete native radio and stand at original pixel size.',
                    sourceUrl='https://github.com/Sierraffinity/CrystalDust',
                    reviewedNativeCounterpart=dict(role='complete_native_radio_and_stand', pixel_scale=1,
                        geometry='Complete16x24 native object with8px transparent top padding in the original16x32 footprint'),
                    evidence='Complete native CrystalDust radio and wooden stand,16x24 unchanged artwork padded8px above into two original blocked source cells. The existing checked per-room wall and floor backdrops remain. Mount Moon Gift Shop radio header has the exact same source fingerprint as the approved domestic radio headers. Original radio interaction, collision, NPCs, warps, layout, palettes and priorities stay unchanged.')
                result = preview.replacement_image(cache, row, packed, mod)
                assert result.size == (16, 16)
                assert all(not native[3] or native == actual
                           for native, actual in zip(pieces[y].get_flattened_data(), result.get_flattened_data()))
                assert all(row.get(key) == old.get(key) for key in GUARDS)
                row['compositionPixelHash'] = sha(result.tobytes())
                key = str(old['id']) + ':' + str(old['quadrant'])
                table = updates[module].setdefault(game, {}).setdefault(map_id, {})
                assert key not in table
                table[key] = row
                new_rows.append(row)
                changes.append(dict(module=module, game=game, map=map_id, xy=[x, y], id=row['id'],
                    quadrant=row['quadrant'], original_role=old['role'], native_asset=asset,
                    native_opaque_pixels_exact=True, original_wall_or_floor_donor_unchanged=True,
                    source_collision=row['sourceCollision'], compositionPixelHash=row['compositionPixelHash']))
    assert len(new_rows) == 30
    for module in modules:
        original = (base / module).read_bytes()
        newline = b'\r\n' if b'\r\n' in original else b'\n'
        assert MARKER.encode() not in original and original.endswith(b'return rows' + newline)
        count = sum(change['module'] == module for change in changes)
        footer = (MARKER + '\nlocal updates=' + lua(canonical(updates[module])) + '\nlocal changed=0\n'
            'for index,row in ipairs(rows)do\n'
            '  local map=updates[row.game]and updates[row.game][row.map]\n'
            "  local replacement=row.style=='gen3'and map and map[tostring(row.id)..':'..tostring(row.quadrant)]\n"
            '  if replacement then rows[index]=replacement;changed=changed+1 end\nend\n'
            f"assert(changed=={count},'Remaining native radio source set changed')\n"
            '-- END REMAINING COMPLETE NATIVE RADIOS\nreturn rows\n')
        (mod / module).write_bytes(original[:-len(b'return rows' + newline)] + footer.replace('\n', newline.decode()).encode())
        after = preview.read_reviewed(mod / module)
        assert len(before[module]) == len(after)
        changed = 0
        for old, new in zip(before[module], after):
            if old == new:
                continue
            assert new == updates[module][old['game']][old['map']][str(old['id']) + ':' + str(old['quadrant'])]
            assert all(old.get(key) == new.get(key) for key in GUARDS)
            changed += 1
        assert changed == count
    paths = list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]", (mod / 'main.lua').read_text())))
    runtime = LuaRuntime(unpack_returned_tuples=True)
    runtime.globals().paths = runtime.table_from(paths)
    runtime.globals().source = lambda name: (mod / name).read_text(encoding='utf-8-sig')
    total = runtime.execute('''local rows={}
      for _,path in ipairs(paths)do for _,r in ipairs(assert(load(source(path),'@'..path))())do rows[#rows+1]=r end end
      local M=assert(load(source('lib/mapping.lua'),'@lib/mapping.lua'))();local _,errors=M.index(rows)
      assert(#errors==0,table.concat(errors,'\\n'));return #rows''')
    valid = review.validate_batch(new_rows, SimpleNamespace(cache=cache, engine=args.engine, output=out), mod)
    assert valid['rows_accepted'] == 30 and valid['rejected'] == 0
    report = dict(status='passed', maps=list(TARGETS), changed_rows=30, source_receipts=receipts, changes=changes,
        registered_rows=total, index_errors=0, native_validation=valid, all_other_rows_unchanged=True,
        source_guards_unchanged=list(GUARDS), no_new_assets_or_runtime_API=True,
        complete_native_object_size=[16,24], transparent_padding_top=8, source_footprint=[16,32],
        native_whole_RGBA_sha256=sha(native_whole.tobytes()),
        mapping_sha256={module:sha((mod/module).read_bytes()) for module in modules},
        helper_sha256=sha(Path(__file__).read_bytes()))
    (out / 'proof.json').write_text(json.dumps(canonical(report), indent=2) + '\n')
    all_rows = []
    for path in paths:
        all_rows.extend(preview.read_reviewed(mod / path))
    for name in TARGETS:
        preview.map_preview(cache, out, 'crystal', name, name, all_rows, packed, 4, mod)
    print(json.dumps(dict(status='passed', changed_rows=30, registered_rows=total, index_errors=0, native_validation=valid)))


if __name__ == '__main__':
    main()
