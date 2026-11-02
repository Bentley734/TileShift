"""Review facility object floors against their actual GSC room context.

Only this tool's new mapping module is authored. Source layouts and gameplay
metadata remain unchanged; existing rows are listed separately for integration.
"""
import argparse
import copy
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace

from PIL import Image, ImageDraw, ImageFont
import catalog
import preview
import gen2_extended_review as source
from interior_review import Imports
from johto_remaining_review import artwork
from center_mart_overhang_review import write_rows

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / '.work/tileshift-facility-floor-audit'
TARGET = ROOT / 'mappings/gen2_facility_floor_audit.lua'
DOMESTIC = {'TILESET_HOUSE', 'TILESET_TRADITIONAL_HOUSE', 'TILESET_PLAYERS_HOUSE',
            'TILESET_PLAYERS_ROOM', 'TILESET_MANSION', 'TILESET_HOTEL'}
NATURAL = {'TILESET_CAVE', 'TILESET_DARK_CAVE', 'TILESET_ICE_PATH', 'TILESET_FOREST',
           'TILESET_JOHTO', 'TILESET_JOHTO_MODERN', 'TILESET_PARK'}


def stable(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def scope(definition):
    return (definition.get('environment') in ('INDOOR', 'GATE', 'DUNGEON')
            and definition['tileset'] not in DOMESTIC | NATURAL)


class Audit:
    def __init__(self):
        self.cache = Path(os.environ['APPDATA']) / 'pokemon-love2d'
        self.imports = Imports(self.cache, ROOT.parent / '.work/tileshift-catalog')
        self.packed = self.imports.packed
        paths = list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]", (ROOT / 'main.lua').read_text())))
        self.rows = []
        self.origin = {}
        self.lookup = {}
        for name in paths:
            if ROOT / name == TARGET:
                continue
            for index, row in enumerate(preview.read_reviewed(ROOT / name), 1):
                self.rows.append(row)
                self.origin[id(row)] = (name, index)
                self.lookup[name, index] = row
        self.data = {game: source.source(self.cache, game) for game in source.GAMES}
        self.by_game = {game: [r for r in self.rows if r['game'] == game and r['style'] == 'gen3']
                        for game in source.GAMES}
        self.images = {}
        self.floors = {}

    def ref(self, game, pair, mid):
        return dict(game=game, tileset=pair, id=mid,
                    hash=self.imports.cell_index(game)[pair, mid]['pixel_sha256'])

    def selected(self, game, name, definition):
        generic, positioned = {}, {}
        for row in sorted(self.by_game[game], key=lambda r: bool(r.get('map'))):
            if row['tileset'] != definition['tileset'] or row.get('map', name) != name:
                continue
            if 'x' in row:
                positioned[row['id'], row['quadrant'], row['x'], row['y']] = row
            else:
                generic[row['id'], row['quadrant']] = row
        cells = {}
        for index, block in enumerate(definition['blocks']):
            for q in range(4):
                x, y = index % definition['width'] * 2 + q % 2, index // definition['width'] * 2 + q // 2
                cells[x, y] = positioned.get((block, q, x, y), generic.get((block, q)))
        return cells

    def image(self, row):
        key = id(row)
        if key not in self.images:
            self.images[key] = preview.replacement_image(self.cache, row, self.packed, ROOT)
        return self.images[key]

    def render(self, game, name):
        data = self.data[game]
        definition = data['maps'][name]
        cells = self.selected(game, name, definition)
        before = Image.new('RGBA', (definition['width'] * 32, definition['height'] * 32))
        after = before.copy()
        originals = {}
        for (x, y), row in cells.items():
            bid = definition['blocks'][y // 2 * definition['width'] + x // 2]
            q = y % 2 * 2 + x % 2
            if (bid, q) not in originals:
                cell = source.cell_info(self.cache, game, data, definition['tileset'], bid, q)
                originals[bid, q] = source.source_image(self.cache, game, data, cell, definition)
            before.paste(originals[bid, q], (x * 16, y * 16))
            after.paste(self.image(row) if row else originals[bid, q], (x * 16, y * 16))
        return before, after

    def contacts(self, names):
        font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15)
        for name in names:
            before, after = self.render('crystal', name)
            canvas = Image.new('RGB', (before.width * 4 + 36, before.height * 2 + 48), '#18212b')
            draw = ImageDraw.Draw(canvas)
            draw.text((8, 6), 'Crystal / ' + name + ' — source / current Gen3 (private pixel reconstruction)', fill='white', font=font)
            canvas.paste(before.resize((before.width * 2, before.height * 2), Image.Resampling.NEAREST), (8, 32))
            canvas.paste(after.resize((after.width * 2, after.height * 2), Image.Resampling.NEAREST), (before.width * 2 + 28, 32))
            canvas.save(OUT / (name + '-current.png'))

    def opaque_contacts(self, inventory):
        """Flag opaque donor surroundings; this inventory does not approve fixes."""
        proposals = {}
        lookup = {(name, index): row for row in self.rows
                  for name, index in [self.origin[id(row)]]}
        for item in inventory['unique_rows']:
            if item['game'] != 'crystal' or not item.get('parts') or any(
                    word in item['role'] for word in ('chair', 'stool', 'lounge', 'student', 'seat')):
                continue
            row = lookup[item['module'], item['index']]
            trial = copy.deepcopy(row)
            affected = []
            for index, part in enumerate(trial['parts']):
                ref = part['donor']
                if part.get('layers') or ref['game'] not in ('firered', 'emerald') or ref.get('kind'):
                    continue
                rec = self.imports.cell_index(ref['game'])[ref['tileset'], ref['id']]
                layers = [name for name in ('mid', 'over')
                          if rec['layer_sha256'].get(name)]
                if not layers:
                    continue
                opaque = preview.native_donor(self.cache, ref, self.packed)
                foreground = preview.native_donor(self.cache, ref, self.packed, layers,
                    {name: rec['layer_sha256'][name] for name in layers})
                sx, sy = part.get('srcX', 0), part.get('srcY', 0)
                box = (sx, sy, sx + part.get('w', 16), sy + part.get('h', 16))
                fg = foreground.crop(box)
                count = sum(p[3] > 0 for p in fg.get_flattened_data())
                if not 0 < count < fg.width * fg.height:
                    continue
                assert all(fg.getpixel((x, y))[3] == 0 or fg.getpixel((x, y)) == opaque.getpixel((sx + x, sy + y))
                           for y in range(fg.height) for x in range(fg.width))
                part.update(layers=layers, layerHashes={name: rec['layer_sha256'][name] for name in layers})
                affected.append(dict(part=index, retained=count, removed=fg.width * fg.height - count, donor=ref))
            if not affected:
                continue
            before = self.image(row)
            after = preview.replacement_image(self.cache, trial, self.packed, ROOT)
            if before.tobytes() == after.tobytes():
                continue
            key = stable([item['role'], row['sourceHash'], artwork(row)])
            if key in proposals:
                proposals[key]['instances'].append(dict(game=item['game'], map=item['map'], coordinates=item['coordinates']))
                continue
            data = self.data[item['game']]
            definition = data['maps'][item['map']]
            cell = source.cell_info(self.cache, item['game'], data, definition['tileset'], row['id'], row['quadrant'])
            original = source.source_image(self.cache, item['game'], data, cell, definition)
            proposals[key] = dict(item=item, affected=affected, original=original, before=before, after=after,
                instances=[dict(game=item['game'], map=item['map'], coordinates=item['coordinates'])])
        font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 13)
        values = list(proposals.values())
        for offset in range(0, len(values), 12):
            chunk = values[offset:offset + 12]
            canvas = Image.new('RGB', (1080, len(chunk) * 96 + 30), '#18212b')
            draw = ImageDraw.Draw(canvas)
            draw.text((4, 4), 'AUDIT ONLY — source / current / detached native MID+OVER candidate (not yet approved)', font=font, fill='white')
            for local, item in enumerate(chunk):
                y = 30 + local * 96
                for col, name in enumerate(('original', 'before', 'after')):
                    canvas.paste(item[name].resize((80, 80), Image.Resampling.NEAREST), (col * 90 + 4, y))
                label = item['item']
                draw.text((280, y + 2), str(offset + local) + '  ' + label['map'] + '  ' + str(label['coordinates'][:3]), font=font, fill='white')
                draw.text((280, y + 23), label['role'], font=font, fill='white')
                draw.text((280, y + 44), 'Parts: ' + str([(p['donor']['tileset'], p['donor']['id'], p['removed']) for p in item['affected']]), font=font, fill='white')
                draw.text((280, y + 65), str(len(item['instances'])) + ' room-context aliases', font=font, fill='white')
            canvas.save(OUT / ('opaque-candidates-' + str(offset // 12 + 1).zfill(2) + '.png'))
        (OUT / 'opaque-candidates.json').write_text(json.dumps([
            dict(number=index, item=value['item'], affected=value['affected'], instances=value['instances'])
            for index, value in enumerate(values)], indent=2))
        return len(values)

    def inventory(self):
        maps, rows, excluded = [], [], []
        for game, data in self.data.items():
            for name, definition in sorted(data['maps'].items()):
                if not isinstance(definition, dict):
                    continue
                if not scope(definition):
                    excluded.append(dict(game=game, map=name, environment=definition.get('environment'), tileset=definition['tileset']))
                    continue
                cells = self.selected(game, name, definition)
                unique = {}
                for xy, row in cells.items():
                    if row:
                        unique.setdefault(id(row), [row, []])[1].append(list(xy))
                maps.append(dict(game=game, map=name, tileset=definition['tileset'],
                    environment=definition['environment'], cells=len(cells), missing=sum(r is None for r in cells.values()),
                    unique_rows=len(unique), kinds=dict(Counter(r.get('kind', 'native') for r, _ in unique.values()))))
                for row, coords in unique.values():
                    module, index = self.origin[id(row)]
                    rows.append(dict(game=game, map=name, tileset=definition['tileset'],
                        module=module, index=index, role=row['role'], kind=row.get('kind', 'native'),
                        coordinates=coords, base=row.get('base'), donor=row.get('donor'),
                        asset=row.get('asset'), parts=row.get('parts'), sourceColors=row.get('sourceColors')))
        result = dict(maps=maps, unique_rows=rows, excluded_maps=excluded,
                      totals=dict(maps=len(maps), cells=sum(m['cells'] for m in maps), missing=sum(m['missing'] for m in maps)))
        (OUT / 'inventory.json').write_text(json.dumps(result, indent=2))
        return result

    def floor(self, game, name, definition, cells):
        # These rooms have one inspected material below freestanding furniture.
        # Wall and counter references are deliberately not inferred as floors.
        key = game, name
        if key in self.floors:
            return copy.deepcopy(self.floors[key])
        if definition['tileset'] == 'TILESET_GAME_CORNER':
            self.floors[key] = self.ref('firered', 'building__rom_082d4cec', 657)
            return copy.deepcopy(self.floors[key])
        choices, casino = {}, {}
        for row in cells.values():
            if row and row.get('donor') and any(word in row['role'] for word in ('floor', 'flat_turf', 'flat_grass')):
                choices[stable(row['donor'])] = row['donor']
                if row['role'] == 'interior_gamecorner_floor':
                    casino[stable(row['donor'])] = row['donor']
        if definition['tileset'] == 'TILESET_GAME_CORNER' and len(casino) == 1:
            choices = casino
        self.floors[key] = next(iter(choices.values())) if len(choices) == 1 else None
        if len(choices) == 1:
            return copy.deepcopy(next(iter(choices.values())))
        return None

    def detached(self, row):
        """Use checked native foreground alpha; never cut or scale a sprite."""
        result = copy.deepcopy(row)
        changed = []
        for index, part in enumerate(result.get('parts', [])):
            ref = part['donor']
            if part.get('layers') or ref['game'] not in ('firered', 'emerald') or ref.get('kind'):
                continue
            rec = self.imports.cell_index(ref['game'])[ref['tileset'], ref['id']]
            layers = [name for name in ('mid', 'over') if rec['layer_sha256'].get(name)]
            if not layers:
                continue
            image = preview.native_donor(self.cache, ref, self.packed, layers,
                {name: rec['layer_sha256'][name] for name in layers})
            sx, sy = part.get('srcX', 0), part.get('srcY', 0)
            crop = image.crop((sx, sy, sx + part.get('w', 16), sy + part.get('h', 16)))
            retained = sum(p[3] > 0 for p in crop.get_flattened_data())
            if retained > 0:
                part.update(layers=layers, layerHashes={name: rec['layer_sha256'][name] for name in layers})
                changed.append(dict(part=index, retained_native_pixels=retained,
                    outside_native_pixels=crop.width * crop.height - retained, donor=copy.deepcopy(ref),
                    layers=layers, layerHashes=copy.deepcopy(part['layerHashes'])))
        return result, changed

    def fix(self, row, game, name, definition, cells, xy):
        role = row['role']
        if any(word in role for word in ('chair', 'stool', 'lounge', 'student', 'seat')):
            return None
        floor = self.floor(game, name, definition, cells)
        stair = (definition['tileset'] == 'TILESET_POKECENTER'
                 and role == 'johto_center_counter_left_end' and row.get('sourceCollision') == 114)
        statue = (name == 'VIOLET_GYM' and role == 'johto_gym_whole_strength_boulder'
                  and row.get('sourceCollision') == 7)
        if stair or statue:
            cell = source.cell_info(self.cache, game, self.data[game], definition['tileset'], row['id'], row['quadrant'])
            expected = (68, 69, 84, 85) if stair else (85, 86, 87, 88)
            assert tuple(cell['tiles']) == expected, (game, name, role, cell['tiles'])
            warps = [w for w in definition.get('warps', []) if (w['x'], w['y']) == xy]
            if stair:
                assert len(warps) == 1 and isinstance(warps[0]['destMap'], str) and warps[0]['destMap'], (game, name, xy, warps)
            ramp = [[240, 248, 240], [184, 200, 208], [104, 128, 144], [48, 56, 80]]
            result = copy.deepcopy(row)
            for key in ('donor', 'base', 'parts', 'asset', 'assetFileHash', 'assetFrames', 'animated',
                        'animation', 'foreground', 'occludes', 'artOverlay'):
                result.pop(key, None)
            result.update(kind='source_palette', sourceColors=[copy.deepcopy(ramp) for _ in range(4)],
                role='facility_complete_original_clinic_stairs' if stair else 'facility_complete_original_violet_compact_statue',
                credit='Original Pokemon Gold/Silver/Crystal / Game Freak; geometry-preserving palette recolor only.',
                sourceUrl='https://github.com/pret/pokecrystal')
            result['evidence'] = ('Complete original compact diagonal staircase/exit with its checked native warp, not a counter or flower display.' if stair else
                'Complete original compact 16px gym statue, not a loose strength boulder.') + ' No complete native Gen3 counterpart fits this compact source slot; the already authorized original-geometry recolor retains all source pixels at1:1. Original source geometry, collision, warp and interactions are unchanged.'
            result['facilityFloorAudit'] = dict(family='source_geometry_clinic_stairs' if stair else 'source_geometry_violet_statue',
                pixel_scale=1, original_role=role, original_source_tiles=cell['tiles'],
                rule='Preserve the complete original compact glyph, with checked source metadata, in the authorized Gen3 stone palette.')
            if warps:
                result['facilityFloorAudit']['source_warps'] = warps
            result['compositionPixelHash'] = catalog.sha(preview.replacement_image(self.cache, result, self.packed, ROOT).tobytes())
            return result
        family = None
        if 'plant' in role and row.get('donor') and not row.get('parts') and floor and xy[1] > 0:
            ref = row['donor']
            if ref['game'] in ('firered', 'emerald') and not ref.get('kind'):
                rec = self.imports.cell_index(ref['game'])[ref['tileset'], ref['id']]
                selected = [layer for layer in ('mid', 'over') if rec['layer_sha256'].get(layer)]
                foreground = preview.native_donor(self.cache, ref, self.packed, selected,
                    {layer: rec['layer_sha256'][layer] for layer in selected})
                count = sum(p[3] > 0 for p in foreground.get_flattened_data())
                if 0 < count < 256:
                    family = 'whole_native_plant_surroundings'
        if family is not None:
            pass
        elif role == 'johto_shop_complete_potted_plant' and '_DEPT_STORE_' in name:
            family = 'department_plant_foreground'
        elif role == 'johto_casino_complete_potted_plant':
            family = 'casino_plant_foreground'
        elif name == 'ELMS_LAB' and role.startswith('johto_center_whole_healing_machine_'):
            family = 'standalone_lab_healing_machine'
        elif role in ('johto_complete_native_region_map', 'johto_shop_complete_floor_directory',
                       'johto_gate_wall_directory', 'johto_radio_complete_wall_notice',
                       'kanto_casino_complete_native_wall_notice', 'johto_radio_complete_audio_control_panel'):
            family = 'wall_notice_native_surroundings'
        elif role.startswith(('johto_house_bookcase_', 'johto_domestic_complete_single_bay_bookcase_')):
            family = 'complete_bookcase_native_surroundings'
        elif role == 'johto_shop_complete_stock_display' and '_DEPT_STORE_' in name:
            family = 'department_stock_native_surroundings'
        elif role == 'johto_casino_plain_floor_beneath_equipment':
            family = 'casino_clear_floor'
        elif (definition['tileset'] == 'TILESET_GAME_CORNER' and row.get('base')
              and row['base'].get('id') == 641 and xy[1] > 0
              and not any(word in role for word in ('wall_notice', 'region_map', 'window'))):
            family = 'casino_room_floor_rebase'
        if family is None:
            return None
        result, layers = self.detached(row)
        if family == 'whole_native_plant_surroundings':
            ref = copy.deepcopy(row['donor'])
            result.pop('donor')
            result.update(kind='native_composite', base=copy.deepcopy(floor),
                parts=[dict(donor=ref, layers=selected,
                    layerHashes={layer: rec['layer_sha256'][layer] for layer in selected}, w=16, h=16)])
            layers = [dict(part=0, retained_native_pixels=count, outside_native_pixels=256-count,
                donor=ref, layers=selected, layerHashes=copy.deepcopy(result['parts'][0]['layerHashes']))]
        if family == 'casino_room_floor_rebase':
            # Countertop colors and cropped rug pieces remain whole. Only the
            # separately authored host material changes in this family.
            result = copy.deepcopy(row);layers = []
            result['base'] = copy.deepcopy(floor)
        if family == 'casino_clear_floor':
            assert floor
            result['donor'] = copy.deepcopy(floor)
        old_base = copy.deepcopy(row.get('base'))
        x, y = xy
        bookcase = family == 'complete_bookcase_native_surroundings'
        if family in ('department_plant_foreground', 'casino_plant_foreground', 'standalone_lab_healing_machine'):
            assert floor, (game, name, role, 'No unambiguous inspected floor')
            result['base'] = copy.deepcopy(floor)
        if bookcase:
            # Top-row bookcase caps sit against the room wall; every other
            # occurrence, including the feet directly below that cap, sits on
            # the room floor. The full frame/books remain unchanged.
            if y > 0 and floor:
                result['base'] = copy.deepcopy(floor)
            for part in result.get('parts', []):
                ref = part['donor']
                if (ref == old_base or
                    ref['game'] == 'firered' and ref['tileset'] in ('house', 'player_house') and ref['id'] in (1, 40)):
                    part['donor'] = copy.deepcopy(result['base'])
                    part.pop('layers', None)
                    part.pop('layerHashes', None)
        before = self.image(row)
        after = preview.replacement_image(self.cache, result, self.packed, ROOT)
        if before.tobytes() == after.tobytes():
            return None
        # A complete native foreground layer is the authoritative object mask,
        # rather than a color flood fill that could erase matching object color.
        foreground = Image.new('RGBA', (16, 16))
        for part in result.get('parts', []):
            ref = part['donor']
            if not part.get('layers') or ref == result.get('base'):
                continue
            pixels = preview.native_donor(self.cache, ref, self.packed, part['layers'], part['layerHashes'])
            sx, sy = part.get('srcX', 0), part.get('srcY', 0)
            piece = pixels.crop((sx, sy, sx + part.get('w', 16), sy + part.get('h', 16)))
            foreground.alpha_composite(piece, (part.get('x', 0), part.get('y', 0)))
        retained = 0
        for py in range(16):
            for px in range(16):
                if foreground.getpixel((px, py))[3]:
                    assert before.getpixel((px, py)) == after.getpixel((px, py)), (name, role, 'Foreground changed', px, py)
                    retained += 1
        assert retained > 0 or family in ('casino_clear_floor', 'casino_room_floor_rebase'), (name, role, 'No verified native foreground')
        result['facilityFloorAudit'] = dict(family=family, pixel_scale=1, originalBase=old_base or copy.deepcopy(row.get('donor')),
            actualBase=copy.deepcopy(result.get('base') or result.get('donor')), retained_native_foreground_pixels=retained,
            rule='Checked native MID/OVER foreground pixels stay unchanged; only unrelated opaque donor surroundings and explicit background filler use this actual room material.')
        if layers:
            result['facilityFloorAudit']['detached_layers'] = layers
        result['evidence'] = row.get('evidence', '') + ' Facility floor audit: exact native object layers retain every foreground pixel at1:1; unrelated donor floor/wall pixels use the inspected room background. Source collision, palette/priority guards, maps, events and interactions are unchanged.'
        result['compositionPixelHash'] = catalog.sha(after.tobytes())
        return result

    def stage(self):
        rows, removals, changes = [], {}, []
        for game, data in self.data.items():
            for name, definition in sorted(data['maps'].items()):
                if not isinstance(definition, dict) or not scope(definition) or name == 'AZALEA_GYM':
                    continue
                cells = self.selected(game, name, definition)
                grouped = defaultdict(list)
                for xy, old in cells.items():
                    if old:
                        grouped[id(old)].append(xy)
                for coords in grouped.values():
                    old = cells[coords[0]]
                    planned = []
                    for xy in coords:
                        fixed = self.fix(old, game, name, definition, cells, xy)
                        if fixed:
                            planned.append((xy, fixed))
                    if not planned:
                        continue
                    same = len(planned) == len(coords) and len({stable(artwork(r)) for _, r in planned}) == 1
                    if same and old.get('x') is None:
                        chosen = copy.deepcopy(planned[0][1]);chosen['map'] = name
                        chosen.pop('x', None);chosen.pop('y', None)
                        chosen['sourceCells'] = [list(xy) for xy, _ in planned]
                        made = [chosen]
                    else:
                        made = []
                        for xy, fixed in planned:
                            fixed['map'] = name;fixed['x'], fixed['y'] = xy
                            fixed['sourceCells'] = [list(xy)];made.append(fixed)
                    module, index = self.origin[id(old)]
                    # Existing generic map templates may remain underneath a
                    # new position-specific override. Identical index keys must
                    # instead be removed by the integrating owner.
                    if old.get('map') == name and (same or old.get('x') is not None):
                        removals[module, index] = dict(module=module, index=index,
                            old_row_sha256=hashlib.sha256(stable(old).encode()).hexdigest(), old_row=old)
                    for row in made:
                        row['facilityFloorAudit']['prior'] = dict(module=module, index=index,
                            old_row_sha256=hashlib.sha256(stable(old).encode()).hexdigest())
                        rows.append(row)
                    changes.append(dict(game=game, map=name, role=old['role'], coordinates=[list(xy) for xy, _ in planned],
                        prior_module=module, prior_index=index, new_rows=len(made),
                        family=planned[0][1]['facilityFloorAudit']['family']))
        (OUT / 'candidates.json').write_text(json.dumps(rows, indent=2))
        (OUT / 'remove-old-rows.json').write_text(json.dumps(list(removals.values()), indent=2))
        integration = []
        for index, row in enumerate(rows, 1):
            prior = row['facilityFloorAudit']['prior']
            old = self.lookup[prior['module'], prior['index']]
            integration.append(dict(oldmodule=prior['module'], oldindex=prior['index'], oldrow=old,
                old_row_sha256=prior['old_row_sha256'], newmodule=TARGET.relative_to(ROOT).as_posix(),
                newindex=index, newrow=row,
                remove_old=(prior['module'], prior['index']) in removals))
        (OUT / 'integration-manifest.json').write_text(json.dumps(integration, indent=2))
        summary = dict(rows=len(rows), changed_cells=sum(len(c['coordinates']) for c in changes),
            maps=len({(c['game'], c['map']) for c in changes}),
            by_family=dict(Counter(c['family'] for c in changes)), changes=changes,
            removal_hash_algorithm='SHA256 of UTF-8 JSON with sorted keys, compact separators and ensure_ascii=False; index is one-based')
        (OUT / 'changes.json').write_text(json.dumps(summary, indent=2))
        return rows, summary

    def staged_contacts(self, rows):
        chosen = [('crystal', 'GOLDENROD_DEPT_STORE_1F'), ('crystal', 'GOLDENROD_DEPT_STORE_2F'),
                  ('crystal', 'ELMS_LAB'), ('crystal', 'RUINS_OF_ALPH_RESEARCH_CENTER'),
                  ('gold', 'GOLDENROD_GAME_CORNER'), ('gold', 'OLIVINE_CAFE'),
                  ('crystal', 'AZALEA_POKECENTER_1F'), ('crystal', 'VIOLET_GYM')]
        font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 16)
        for game, name in chosen:
            _, before = self.render(game, name)
            after = before.copy()
            for row in rows:
                if row['game'] == game and row['map'] == name:
                    image = preview.replacement_image(self.cache, row, self.packed, ROOT)
                    for x, y in row['sourceCells']:
                        after.paste(image, (x * 16, y * 16))
            canvas = Image.new('RGB', (before.width * 4 + 36, before.height * 2 + 48), '#18212b')
            ImageDraw.Draw(canvas).text((8, 6), game.title() + ' / ' + name + ' — current / staged facility floor fixes', fill='white', font=font)
            canvas.paste(before.resize((before.width * 2, before.height * 2), Image.Resampling.NEAREST), (8, 32))
            canvas.paste(after.resize((after.width * 2, after.height * 2), Image.Resampling.NEAREST), (before.width * 2 + 28, 32))
            canvas.save(OUT / (game + '-' + name + '-staged.png'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contacts', nargs='*', default=[])
    parser.add_argument('--opaque-contacts', action='store_true')
    parser.add_argument('--stage', action='store_true')
    parser.add_argument('--validate', action='store_true')
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    audit = Audit()
    result = audit.inventory()
    audit.contacts(args.contacts)
    if args.opaque_contacts:
        result['totals']['opaque_candidates'] = audit.opaque_contacts(result)
    if args.stage or args.validate or args.activate:
        rows, summary = audit.stage()
        audit.staged_contacts(rows)
        result['totals']['staged'] = {k: v for k, v in summary.items() if k != 'changes'}
        if args.validate or args.activate:
            proof = source.validate_batch(rows, SimpleNamespace(cache=audit.cache,
                engine=ROOT.parent / '.tools/engine-0395', output=OUT), ROOT)
            (OUT / 'proof.json').write_text(json.dumps(proof, indent=2))
        if args.activate:
            assert args.validate, 'Activation requires validation'
            write_rows(TARGET, rows)
    print(json.dumps(result['totals']))


if __name__ == '__main__':
    main()
