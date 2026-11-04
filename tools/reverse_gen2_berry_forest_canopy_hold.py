"""Restore native Berry Forest canopy where twelve old cave aliases were unsafe.

Run after legacy Kanto authoring. Only the twelve reviewed row literals and
their following commas are removed; every other byte is retained. The current
source canopy remains native, including all original layers and collision.
No new artwork, geometry alias, floor replacement or source667 change is made.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import zlib

from PIL import Image, ImageChops, ImageDraw

import catalog
from gen2_side_threshold_orientation import literal_rows
from interior_review import Imports
from newbark_building_review import lua
import preview
import reverse_common
from reverse_common import ROOT, ReverseReview

BASE_COMMIT = '9a2181306689624ff3d574036179d16bbc24b06f'
MODULE = 'mappings/reverse_gen2_kanto_finish.lua'
GAMES = ('firered', 'leafgreen')
PAIRS = {'firered': 'general__rom_082d5004', 'leafgreen': 'general__rom_082d4fe4'}
IDS = (656, 657, 658, 664, 665, 666)
MAP = 'FR_THREE_ISLAND_BERRY_FOREST'
COUNTS = {656: 200, 657: 202, 658: 155, 664: 221, 665: 268, 666: 221}
OUT = ROOT.parent / '.work/tileshift-v0350-berry-forest-hold'
REVIEWED_BINDING = 'cec57b937fcb1aaff2adf4b820d2cf289f23a3aef18852b7c6a467d2656f9560'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def key(row):
    return tuple(row.get(name) for name in ('game', 'style', 'tileset', 'id', 'map', 'quadrant', 'x', 'y'))


def target(row):
    return (row.get('game') in GAMES and row.get('style') == 'gen2'
            and row.get('tileset') == PAIRS[row['game']] and row.get('id') in IDS)


class Review(ReverseReview):
    def __init__(self, cache):
        self.cache = Path(cache).resolve()
        reverse_common.CACHE = self.cache
        self.out = OUT
        OUT.mkdir(parents=True, exist_ok=True)
        self.games = GAMES
        self.name = 'v0350-berry-forest-hold'
        self.imp = Imports(self.cache, ROOT.parent / '.work/tileshift-catalog')
        self.packed = self.imp.packed
        self._gb, self._refs, self.rows = {}, {}, {}
        published = subprocess.check_output([
            'git', '-c', 'safe.directory=' + ROOT.as_posix(), '-C', str(ROOT),
            'show', BASE_COMMIT + ':' + MODULE]).decode('utf-8')
        self.old = {key(row): row for _, _, row in literal_rows(published) if target(row)}
        assert len(self.old) == 12
        assert all(row.get('map') is None and row['kind'] == 'native' for row in self.old.values())
        self.layouts = {}

    def source_binding(self):
        cells = []
        for identity, row in sorted(self.old.items()):
            cell = self.imp.cell_index(row['game'])[row['tileset'], row['id']]
            assert row['sourceHash'] == cell['pixel_sha256']
            assert row['sourceBehavior'] == cell['behavior']
            cells.append(dict(key=list(identity), original_row_sha256=digest(row),
                              source_rgba_sha256=cell['pixel_sha256'],
                              source_layer_sha256=cell['layer_sha256'], source_behavior=cell['behavior']))
        scenes = []
        for game in GAMES:
            manifest = self.imp.table(game, 'gba/native/manifest')['layouts']
            witnesses = [name for name, spec in manifest.items() if spec['pair'] == PAIRS[game]]
            assert witnesses == [MAP], ('Unexpected shared Berry Forest source context', game, witnesses)
            spec = manifest[MAP]
            path = self.cache / game / 'data/generated/gba/native' / spec['file']
            raw = path.read_bytes()
            blob = raw if raw[:4] == b'SVML' else zlib.decompress(raw)
            assert blob[:4] == b'SVML'
            width, height, tw, th = struct.unpack_from('<HHHH', blob, 6)
            columns, lines = tw or width, th or height
            bw, bh = blob[14], blob[15]
            offset = 16 + bw * bh * 2
            matrix = [[struct.unpack_from('<H', blob, offset + (y * width + x) * 4)[0]
                       for x in range(columns)] for y in range(lines)]
            counts = Counter(mid for line in matrix for mid in line)
            assert {mid: counts[mid] for mid in IDS} == COUNTS
            border = [struct.unpack_from('<H', blob, 16 + i * 2)[0] for i in range(bw * bh)]
            assert (bw, bh) == (3, 2) and border == [664, 665, 666, 656, 657, 658]
            coordinates = [dict(x=x, y=y, id=mid,
                                collision=blob[offset + (y * width + x) * 4 + 2],
                                elevation=blob[offset + (y * width + x) * 4 + 3])
                           for y, line in enumerate(matrix) for x, mid in enumerate(line) if mid in IDS]
            assert (columns, lines) == (57, 47) and len(coordinates) == 1267
            self.layouts[game] = matrix
            scenes.append(dict(game=game, map=MAP, pair=PAIRS[game], width=columns, height=lines,
                               logical_layout_sha256=catalog.sha(raw), source_counts=dict(COUNTS),
                               restored_native_canopy_cells=len(coordinates), coordinates=coordinates,
                               border_width=bw, border_height=bh, border_mids=border,
                               warps=self.imp.table(game, 'gba/warps').get(MAP, [])))
        binding = dict(published_baseline_commit=BASE_COMMIT, source_cells=cells, scenes=scenes,
                       reason='Native Berry Forest canopy is not a Crystal cave-bank counterpart',
                       held_key_count=12, restored_native_canopy_cells=2534,
                       source667_excluded=True)
        result = digest(binding)
        if REVIEWED_BINDING is not None:
            assert result == REVIEWED_BINDING, ('Reviewed Berry Forest source binding changed', result)
        (OUT / 'source-binding.json').write_text(json.dumps(dict(sha256=result, binding=binding), sort_keys=True, indent=2) + '\n')
        (OUT / 'affected-scenes.json').write_text(json.dumps([dict(game=g, map=MAP) for g in GAMES], indent=2) + '\n')
        header = dict(all_border=[dict(game=g, pair=PAIRS[g], id=mid, maps=[MAP],
                                     removed_unsafe_mapping=True) for g in GAMES for mid in IDS])
        (OUT / 'native-header-inventory.json').write_text(json.dumps(header, sort_keys=True, indent=2) + '\n')
        (OUT / 'native-header-scenes.json').write_text(json.dumps([dict(game=g, map=MAP) for g in GAMES], indent=2) + '\n')
        (OUT / 'native-header-supplement.json').write_text(json.dumps(dict(needed=True,
            sampled_all_header_keys=12, scenes=[dict(game=g, map=MAP) for g in GAMES], inventory=header,
            reason='Removed canopy keys remain actual native3x2 header witnesses; do not pass absent mappings to the current-key atlas selector.'),
            sort_keys=True, indent=2) + '\n')
        (OUT / 'held-keys.json').write_text(json.dumps([dict(game=r['game'], style='gen2', pair=r['tileset'], mid=r['id'],
            module=MODULE, original_row_sha256=digest(r), sourceHash=r['sourceHash'], sourceBehavior=r['sourceBehavior'])
            for _, r in sorted(self.old.items())], sort_keys=True, indent=2) + '\n')
        (OUT / 'old-rows.json').write_text(json.dumps(list(self.old.values()), sort_keys=True, indent=2) + '\n')
        return result, scenes

    def candidate(self, activate):
        original = (ROOT / MODULE).read_bytes().decode('utf-8')
        rows = list(literal_rows(original))
        remaining = {key(row): row for _, _, row in rows if target(row)}
        assert len(remaining) in (0, 12), 'Refusing a partially edited hold inventory'
        spans = []
        for start, end, row in rows:
            if not target(row):
                continue
            assert key(row) in self.old and digest(row) == digest(self.old[key(row)]), ('Unsafe row independently changed', key(row))
            assert original[end] == ',', 'Expected the reviewed bounded batch comma'
            spans.append((start, end + 1))
        chunks, cursor = [], 0
        for start, end in spans:
            chunks.append(original[cursor:start])
            cursor = end
        chunks.append(original[cursor:])
        fixed = ''.join(chunks)
        old_other = {key(row): row for _, _, row in rows if not target(row)}
        new_rows = list(literal_rows(fixed))
        assert not any(target(row) for _, _, row in new_rows)
        assert {key(row): row for _, _, row in new_rows} == old_other
        # The candidate is made exclusively from unmodified original byte spans.
        assert fixed.encode('utf-8') == b''.join(chunk.encode('utf-8') for chunk in chunks)
        path = OUT / 'candidate-module.lua'
        path.write_bytes(fixed.encode('utf-8'))
        if activate:
            (ROOT / MODULE).write_bytes(fixed.encode('utf-8'))
        return dict(module=MODULE, removed_rows=len(remaining), already_applied=not remaining,
                    held_keys=12, unchanged_rows=len(old_other),
                    all_other_rows_structurally_identical=True,
                    all_bytes_outside_twelve_literals_and_delimiters_identical=True,
                    unchanged_chunks_sha256=catalog.sha(b''.join(c.encode('utf-8') for c in chunks)),
                    before_sha256=catalog.sha(original.encode('utf-8')),
                    after_sha256=catalog.sha(fixed.encode('utf-8')), activated=activate)

    def current_pair_rows(self):
        selected = {}
        choose = catalog.LUA.eval('function(rows)local out={}for _,r in ipairs(rows)do '
            'if r.style=="gen2"and((r.game=="firered"and r.tileset=="general__rom_082d5004")or'
            '(r.game=="leafgreen"and r.tileset=="general__rom_082d4fe4"))then out[#out+1]=r end end return out end')
        modules = dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]", (ROOT / 'main.lua').read_text()))
        for module in modules:
            text = (ROOT / module).read_text(encoding='utf-8-sig')
            if not any(pair in text for pair in PAIRS.values()):
                continue
            rows = catalog.plain(choose(catalog.LUA.execute(text)))
            for row in rows if isinstance(rows, list) else []:
                if target(row):
                    continue
                assert key(row) not in selected
                selected[key(row)] = row
        return selected

    def validate_fallback(self, previews):
        self.rows = self.current_pair_rows()
        neutral = self.validate()
        assert neutral['rejected'] == 0
        totals = []
        for game in GAMES:
            current = {row['id']: row for row in self.rows.values() if row['game'] == game}
            assert not set(current).intersection(IDS)
            matrix = self.layouts[game]
            source = Image.new('RGBA', (57 * 16, 47 * 16))
            before, after, cache = source.copy(), source.copy(), {}
            restored = 0
            for y, line in enumerate(matrix):
                for x, mid in enumerate(line):
                    if mid not in cache:
                        cell = self.imp.cell_index(game)[PAIRS[game], mid]
                        native = preview.native_donor(self.cache, dict(game=game, tileset=PAIRS[game], id=mid,
                                                       hash=cell['pixel_sha256']), self.packed)
                        selected = self.render(current[mid]) if mid in current else native
                        previous = self.render(self.old[game, 'gen2', PAIRS[game], mid, None, None, None, None]) if mid in IDS else selected
                        cache[mid] = native, previous, selected
                    native, previous, selected = cache[mid]
                    point = x * 16, y * 16
                    source.paste(native, point); before.paste(previous, point); after.paste(selected, point)
                    if mid in IDS:
                        assert selected.tobytes() == native.tobytes()
                        restored += 1
                    else:
                        assert previous.tobytes() == selected.tobytes()
            assert restored == 1267
            totals.append(dict(game=game, map=MAP, source_cells=57 * 47,
                restored_native_canopy_cells=restored, before_replaced_cells=sum(mid in current or mid in IDS for line in matrix for mid in line),
                after_replaced_cells=sum(mid in current for line in matrix for mid in line),
                complete=False, all_held_cells_exact_original_source=True, all_other_scene_cells_unchanged=True))
            if previews:
                for label, image in (('source', source), ('previous', before), ('native-canopy', after)):
                    image.save(OUT / (game + '-' + label + '.png'))
                panel = Image.new('RGB', (57 * 32 + 56, 47 * 16 + 56), '#18212b')
                draw = ImageDraw.Draw(panel)
                draw.text((18, 12), game.title() + ' Berry Forest: previous unsafe cave banks / original native canopy restored', fill='white')
                panel.paste(before, (18, 38)); panel.paste(after, (38 + 57 * 16, 38))
                panel.save(OUT / (game + '-comparison.png'))
        assert sum(s['restored_native_canopy_cells'] for s in totals) == 2534
        return dict(neutral=neutral, scenes=totals, restored_native_canopy_cells=2534,
                    held_keys_absent_from_candidate_session=12, no_fabricated_native_alias=True)

    def verify_native_report(self, path):
        from gpu_comparison import readback
        from validate_gpu import runtime_fingerprint
        report = json.loads(path.read_text())
        assert report['status'] == 'passed' and not report['warnings']
        assert report['runtime_inputs'] == runtime_fingerprint(ROOT)
        assert report['runtime_inputs_unchanged_during_probe'] is True
        fixtures = {(f['game'], f['map']): f for f in report['fixtures'] if f.get('style') == 'gen2'}
        checked = []
        for game in GAMES:
            f = fixtures[game, MAP]
            assert f['actual_native_field_view'] and f['source_layout_and_events_unchanged'] and f['cleanup_restored_native']
            before, after = readback(f['before']), readback(f['after'])
            assert before.size == after.size == (57 * 16, 47 * 16)
            restored = 0
            for y, line in enumerate(self.layouts[game]):
                for x, mid in enumerate(line):
                    if mid not in IDS:
                        continue
                    box = x * 16, y * 16, (x + 1) * 16, (y + 1) * 16
                    assert ImageChops.difference(before.crop(box), after.crop(box)).getbbox() is None
                    restored += 1
            assert restored == 1267
            checked.append(dict(game=game, map=MAP, restored_native_canopy_cells=restored,
                                every_held_cell_exact_native_gpu_rgb=True, source_layout_and_events_unchanged=True))
        result = dict(status='passed', native_report=str(path), native_report_sha256=catalog.sha(path.read_bytes()),
                      runtime_inputs_sha256=report['runtime_inputs']['sha256'], scenes=checked,
                      restored_native_canopy_cells=2534, checked_native_gpu_pixels=2534 * 256)
        (OUT / 'native-fallback-proof.json').write_text(json.dumps(result, indent=2) + '\n')
        return result

    def verify_native_headers(self, path):
        from validate_gpu import runtime_fingerprint
        report = json.loads(path.read_text())
        assert report['status'] == 'passed' and not report['warnings']
        assert report['runtime_inputs'] == runtime_fingerprint(ROOT)
        assert report['runtime_inputs_unchanged_during_probe'] is True
        fixtures = {(f['game'], f['map']): f for f in report['fixtures']}
        checked = []
        for game in GAMES:
            f = fixtures[game, MAP]
            assert f['source_headers_unchanged'] and f['source_connections_unchanged']
            assert f['isolated_header_graph'] and f['cleanup_restored_native']
            assert f['replaced_border_pixels'] == 0 and f['native_border_pixels'] == f['checked_pixels'] == 4096
            checked.append(dict(game=game, map=MAP, all_six_native_header_canopy_keys_sampled=True,
                                replaced_border_pixels=0, exact_native_header_pixels=4096))
        result = dict(status='passed', native_report=str(path), native_report_sha256=catalog.sha(path.read_bytes()),
                      runtime_inputs_sha256=report['runtime_inputs']['sha256'], scenes=checked,
                      held_native_header_keys=12, exact_native_header_pixels=8192)
        (OUT / 'native-header-fallback-proof.json').write_text(json.dumps(result, indent=2) + '\n')
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=reverse_common.CACHE)
    parser.add_argument('--validate', action='store_true')
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--activate', action='store_true')
    parser.add_argument('--native-report', type=Path)
    parser.add_argument('--native-header-report', type=Path)
    args = parser.parse_args()
    assert not args.activate or (args.validate and REVIEWED_BINDING is not None)
    review = Review(args.cache)
    binding, scenes = review.source_binding()
    change = review.candidate(False)
    proof = dict(status='candidate', binding_sha256=binding, patch=change,
                 remaining_native_correction_work='Berry Forest source667 path/grass edge is outside this canopy-only hold.')
    if args.validate:
        proof['fallback'] = review.validate_fallback(args.preview)
        proof['status'] = 'passed'
    if args.activate:
        proof['patch'] = review.candidate(True)
    if args.native_report:
        assert not any(target(row) for _, _, row in literal_rows((ROOT / MODULE).read_text()))
        proof['native_gpu'] = review.verify_native_report(args.native_report)
    if args.native_header_report:
        assert not any(target(row) for _, _, row in literal_rows((ROOT / MODULE).read_text()))
        proof['native_headers_gpu'] = review.verify_native_headers(args.native_header_report)
    (OUT / 'proof.json').write_text(json.dumps(proof, sort_keys=True, indent=2) + '\n')
    print(json.dumps(dict(status=proof['status'], held_keys=12, restored_native_canopy_cells=2534,
                         binding_sha256=binding, module_sha256=proof['patch']['after_sha256'], activated=args.activate)))


if __name__ == '__main__':
    main()
