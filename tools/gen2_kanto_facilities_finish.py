"""Review the remaining Gen2 ship, port, station and facility counterparts.

Only this tool's new mapping module is written. Counterparts are explicit room
families and whole native modules; source layouts and gameplay are never edited.
Unique compact maritime trim/furnishings retain the original cartridge pixels
in the already user-approved Gen3 palettes rather than cropping larger objects.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace

import catalog
from center_mart_overhang_review import write_rows
from gen1_native_plant import native_plant_parts
import gen2_extended_review as review
from interior_review import Imports
from johto_remaining_review import artwork
from native_room_parts import RoomParts
import preview


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'mappings/gen2_kanto_facilities_finish.lua'
OUT = ROOT.parent / '.work/tileshift-gen2-kanto-facilities'
BASELINE = ROOT.parent / '.work/tileshift-gen2-next-baseline/report.json'
SETS = {'TILESET_LIGHTHOUSE', 'TILESET_PORT', 'TILESET_TRAIN_STATION', 'TILESET_FACILITY'}
STEEL = [[247, 247, 247], [189, 206, 214], [132, 148, 156], [0, 0, 0]]
BLUE = [[247, 247, 247], [173, 206, 230], [99, 132, 181], [49, 66, 107]]
WOOD = [[247, 239, 206], [222, 214, 140], [181, 173, 99], [0, 0, 0]]
GOLD = [[255, 239, 181], [239, 189, 82], [189, 123, 49], [82, 66, 49]]
OCEAN = [[107, 132, 214], [82, 107, 214], [58, 82, 156], [41, 66, 140]]

# These are the inspected unique GS maritime frames and compact combined
# furnishings. Ordinary clocks, doors, beds, stairs, chairs and floors below
# are resolved to native counterparts before this explicit fallback list.
SHIP_COMPACT = {
    (2, 3, 9, 10), (2, 3, 45, 61), (9, 10, 25, 26), (9, 10, 25, 44),
    (10, 10, 68, 69), (10, 12, 44, 28), (16, 16, 10, 12), (16, 16, 84, 85),
    (16, 33, 18, 49), (19, 62, 54, 43), (20, 26, 59, 60), (20, 130, 11, 128),
    (20, 130, 59, 60), (25, 44, 25, 44), (25, 64, 25, 80), (26, 28, 44, 28),
    (32, 16, 48, 18), (54, 43, 59, 60), (65, 28, 81, 28), (66, 67, 23, 24),
    (72, 73, 88, 89), (82, 83, 92, 93), (130, 53, 59, 60),
    (130, 53, 129, 11), (130, 130, 11, 11), (20, 44, 11, 59),
    (44, 53, 60, 11), (44, 53, 59, 60), (20, 44, 59, 60), (44, 44, 11, 11),
}
SHIP_TRIM = {1, 5, 6, 17, 18, 19, 21, 22, 33, 34, 37, 38, 50, 51}


class Reviewer:
    def __init__(self):
        self.cache = Path(os.environ['APPDATA']) / 'pokemon-love2d'
        self.imp = Imports(self.cache, ROOT.parent / '.work/tileshift-catalog')
        self.packed = self.imp.packed
        self.active = [row for path in sorted((ROOT / 'mappings').glob('*.lua')) if path != MODULE
                       for row in preview.read_reviewed(path)]
        self.templates = {row['role']: row for row in self.active if row['game'] == 'crystal'}
        for row in self.active:
            if row['game'] == 'red':
                self.templates.setdefault(row['role'], row)
        self.index = defaultdict(list)
        for row in self.active:
            self.index[row['game'], row.get('map'), row.get('sourceHash')].append(row)
        self.rooms = {}

    def room(self, name, game='firered'):
        key = game, name
        if key not in self.rooms:
            self.rooms[key] = RoomParts(self.imp, game, name)
        return self.rooms[key]

    @staticmethod
    def native(ref, role):
        return {'kind': 'native', 'donor': copy.deepcopy(ref), 'role': role}

    @staticmethod
    def comp(base, parts, role):
        return {'kind': 'native_composite', 'base': copy.deepcopy(base), 'parts': copy.deepcopy(parts), 'role': role}

    def template(self, role, base=None):
        seed = self.templates[role]
        value = artwork(seed); value['role'] = role
        value['_reviewed_source'] = {key: seed[key] for key in ('game', 'map', 'id', 'quadrant', 'sourceHash') if key in seed}
        value['_reviewed_evidence'] = seed.get('evidence', '')
        if base is not None and 'base' in value:
            value['base'] = copy.deepcopy(base)
        return value

    def same_source(self, cell, maps, game='crystal', preferred=None):
        candidates = [row for name in maps for row in self.index[game, name, cell['sourceHash']]]
        if game == 'crystal':
            candidates = [row for row in candidates if row.get('tileset') == cell['tileset']
                          and row.get('sourceCollision') == cell['collision']
                          and row.get('sourcePriority') == [bool(a.get('priority')) for a in cell['attributes']]
                          and row.get('sourcePalettes') == [a.get('palette', 1) for a in cell['attributes']]]
        if preferred:
            chosen = [row for row in candidates if preferred in row['role']]
            if chosen:
                candidates = chosen
        if candidates and len({row.get('compositionPixelHash') for row in candidates}) == 1:
            row = candidates[0]
            value = artwork(row); value['role'] = row['role']
            value['_reviewed_source'] = {key: row[key] for key in ('game', 'map', 'id', 'quadrant', 'sourceHash')}
            value['_reviewed_evidence'] = row.get('evidence', '')
            return value
        return None

    def raw_at(self, cell, x, y, definition, data):
        if not 0 <= x < definition['width'] * 2 or not 0 <= y < definition['height'] * 2:
            return ()
        block = definition['blocks'][y // 2 * definition['width'] + x // 2]
        return tuple(review.cell_info(self.cache, cell['game'], data, definition['tileset'], block,
                                      y % 2 * 2 + x % 2)['tiles'])

    def rug(self, cell, x, y, definition, data, base):
        raw = tuple(cell['tiles'])
        right = raw == (13, 21, 29, 14) or self.raw_at(cell, x - 1, y, definition, data) == raw
        return self.template('household_rug_right' if right else 'household_rug_left', base)

    def stairs(self, up, base):
        return self.template('johto_gate_stairs_' + ('up' if up else 'down'), base)

    def maritime(self, cell, x, y, name, definition, data):
        raw = tuple(cell['tiles'])
        cabin = self.room('FR_SSANNE_1F_ROOM1')
        captain = self.room('FR_SSANNE_CAPTAINS_OFFICE')
        lower = self.room('EM_SS_TIDAL_LOWER_DECK', 'emerald')
        floor = cabin.ref(796)
        if raw == (1, 1, 1, 1):
            return self.native(cabin.ref(0), 'gen2_ship_native_outside_void')
        if raw in ((4, 4, 4, 4), (4, 4, 35, 35), (35, 35, 4, 4)):
            return self.native(captain.ref(664), 'gen2_ship_native_timber_corridor_floor')
        if raw == (13, 29, 29, 13):
            return self.native(floor, 'gen2_ship_native_cabin_floor')
        if raw == (46, 47, 47, 46):
            return self.native(lower.ref(525), 'gen2_ship_native_lower_deck_floor')
        if raw in ((27, 63, 47, 46), (63, 63, 47, 46)):
            return self.native(lower.ref(525), 'gen2_ship_native_lower_deck_floor_below_bulkhead')
        if raw == (14, 15, 30, 31):
            return self.native(cabin.ref(641), 'gen2_ship_complete_native_cabin_door')
        if raw in ((16, 16, 18, 18),):
            return self.native(cabin.ref(652), 'gen2_ship_complete_native_bulkhead_panel')
        if raw == (2, 3, 18, 18):
            return self.native(cabin.ref(826), 'gen2_ship_complete_native_wall_clock')
        if raw == (70, 71, 86, 87):
            return self.template('johto_lighthouse_complete_native_bed_head', floor)
        if raw in ((131, 132, 133, 134), (86, 87, 59, 60)):
            return self.template('johto_lighthouse_complete_native_bed_foot', floor)
        if raw == (7, 8, 23, 24):
            return self.template('johto_house_chair_left', floor)
        if raw in ((39, 40, 55, 56), (41, 42, 57, 58)):
            return self.stairs(raw[0] == 41, lower.ref(525) if name == 'FAST_SHIP_B1F' else captain.ref(664))
        if raw == (36, 36, 52, 52):
            return self.rug(cell, x, y, definition, data, floor)
        if raw in SHIP_COMPACT or all(tile in SHIP_TRIM for tile in raw):
            # Source slot6 is the surrounding cabin floor, slot5 food/brass,
            # and slot7 blue cloth/steel. Match the actual native floor colors
            # rather than leaving original pink room pixels around the table.
            image = preview.native_donor(self.cache, floor, self.packed)
            colors = sorted({pixel[:3] for pixel in image.get_flattened_data()}, key=sum, reverse=True)
            assert len(colors) == 2
            floor_colors = [list(colors[0]), list(colors[0]), list(colors[1]), list(colors[1])]
            palettes = [floor_colors if attr.get('palette') == 6 else GOLD if attr.get('palette') == 5
                        else BLUE if raw in SHIP_COMPACT else STEEL for attr in cell['attributes']]
            return {'kind': 'source_palette', 'sourceColors': copy.deepcopy(palettes),
                    'role': 'gen2_ship_original_complete_compact_furniture' if raw in SHIP_COMPACT else 'gen2_ship_original_narrow_bulkhead_trim'}
        return None

    def facility(self, cell, x, y, name, definition, data):
        raw = tuple(cell['tiles'])
        room = self.room('FR_POWER_PLANT' if name == 'POWER_PLANT' else 'FR_SILPH_CO_1F'
                         if name == 'SILPH_CO_1F' else 'FR_SAFFRON_CITY_DOJO')
        floor = room.ref(671 if name == 'POWER_PLANT' else 820 if name == 'SILPH_CO_1F' else 704)
        wall = room.ref(661 if name == 'POWER_PLANT' else 816 if name == 'SILPH_CO_1F' else 705)
        if cell['collision'] == 0 and (set(raw) <= {1, 38} or raw == (28, 28, 28, 28)):
            return self.native(floor, 'gen2_facility_context_native_floor')
        if raw in ((34, 34, 34, 34), (34, 34, 64, 66)):
            return self.native(wall, 'gen2_facility_complete_native_back_wall')
        if raw == (50, 51, 67, 68):
            return self.stairs(True, floor)
        if raw == (39, 39, 55, 55):
            return self.rug(cell, x, y, definition, data, floor)
        preferred = ('complete_native_table_0_0' if raw == (64, 65, 80, 81)
                     else 'whole_research_workstation' if raw in ((6, 7, 38, 1), (8, 9, 38, 1)) else None)
        value = self.same_source(cell, ('MR_POKEMONS_HOUSE', 'RUINS_OF_ALPH_RESEARCH_CENTER',
                                      'TEAM_ROCKET_BASE_B2F', 'TEAM_ROCKET_BASE_B3F'), preferred=preferred)
        if value and 'base' in value:
            value['base'] = copy.deepcopy(floor)
        return value

    def station(self, cell, x, y, definition, data):
        raw = tuple(cell['tiles']); mart = self.room('FR_VIRIDIAN_CITY_MART'); floor = mart.ref(641)
        if raw == (14, 14, 30, 30):
            return self.rug(cell, x, y, definition, data, floor)
        if raw in ((53, 54, 55, 56), (57, 58, 59, 60)):
            rows = [r for r in self.index['crystal', 'GOLDENROD_MAGNET_TRAIN_STATION', cell['sourceHash']]
                    if r['role'] == 'johto_station_complete_gate_side_rail']
            desired = 244 if x < 9 else 245
            row = next(r for r in rows if r['parts'][0]['donor']['id'] == desired)
            value = artwork(row); value['role'] = row['role']; return value
        if raw in ((80, 81, 84, 85),):
            return self.template('johto_house_complete_single_flowerpot', floor)
        if raw == (64, 65, 66, 67):
            return self.template('johto_station_complete_waiting_chair', floor)
        if raw == (84, 85, 61, 61):
            return self.comp(floor, native_plant_parts(self.imp, False), 'gen2_station_complete_native_plant_pot')
        return self.same_source(cell, ('GOLDENROD_MAGNET_TRAIN_STATION',))

    def port(self, cell, name):
        value = self.same_source(cell, ('OLIVINE_PORT',))
        if value:
            return value
        if tuple(cell['tiles']) == (34, 34, 20, 20):
            return {'kind': 'source_palette', 'sourceColors': [copy.deepcopy(WOOD), copy.deepcopy(WOOD),
                    copy.deepcopy(OCEAN), copy.deepcopy(OCEAN)],
                    'role': 'gen2_port_original_complete_compact_boarding_ladder'}
        return None

    def gym(self, cell, x, y, name, definition, data):
        raw = tuple(cell['tiles'])
        room = self.room('FR_CERULEAN_CITY_GYM' if name == 'CERULEAN_GYM' else 'FR_CELADON_CITY_GYM'
                         if name == 'CELADON_GYM' else 'FR_SAFFRON_CITY_DOJO' if name == 'FIGHTING_DOJO'
                         else 'FR_VIRIDIAN_CITY_GYM')
        floor = room.ref(704 if name == 'FIGHTING_DOJO' else 670 if name == 'CELADON_GYM' else 641)
        if raw in ((14, 14, 30, 30), (12, 13, 28, 29), (13, 21, 29, 14)):
            return self.rug(cell, x, y, definition, data, floor)
        if raw == (72, 73, 88, 89):
            return self.template('gen1_gym_complete_rhydon_statue_head', floor)
        if raw == (74, 75, 90, 91):
            return self.template('gen1_gym_complete_rhydon_statue_plinth', floor)
        if name == 'CERULEAN_GYM':
            if raw in ((20, 20, 20, 20), (11, 11, 20, 20)):
                return self.native(room.ref(657), 'freshwater_pond_gen2_cerulean_gym_pool')
            if raw == (34, 34, 20, 20):
                return self.native(room.ref(701), 'gen2_cerulean_complete_native_floating_walkway_support')
            if raw == (5, 5, 5, 5):
                return self.native(room.ref(690), 'gen2_cerulean_complete_native_floating_walkway_deck')
            if raw == (10, 10, 10, 10):
                return self.native(floor, 'gen2_cerulean_native_poolside_floor')
            if raw == (15, 15, 15, 15):
                return self.native(room.ref(646), 'gen2_cerulean_native_upper_wall')
            if raw == (22, 23, 24, 25):
                return self.template('gen1_gym_complete_rhydon_statue_head', floor)
            if raw == (6, 7, 22, 23):
                return self.template('gen1_gym_complete_rhydon_statue_head', floor)
            if raw == (8, 9, 24, 25):
                return self.template('gen1_gym_complete_rhydon_statue_plinth', floor)
        if name == 'CELADON_GYM':
            if raw == (48, 48, 48, 48):
                return self.native(room.ref(643), 'gen2_celadon_complete_native_upper_wall')
            if raw == (87, 87, 87, 87):
                return self.native(room.ref(641), 'gen2_celadon_native_flat_turf')
            if raw == (76, 77, 92, 93):
                return self.template('cuttable_small_tree', room.ref(641))
            if raw == (80, 81, 82, 83):
                return self.comp(room.ref(641), native_plant_parts(self.imp, True), 'gen2_celadon_complete_native_planter_crown')
            if raw in ((80, 81, 84, 85),):
                return self.template('johto_house_complete_single_flowerpot', room.ref(641))
            if raw in ((84, 85, 87, 87), (82, 83, 84, 85)):
                return self.comp(room.ref(641), native_plant_parts(self.imp, False), 'gen2_celadon_complete_native_planter_pot')
        if name == 'VIRIDIAN_GYM':
            if raw == (61, 61, 61, 61):
                return self.native(floor, 'gen2_viridian_native_tiled_floor')
            wall = room.ref(657)
            if set(raw) <= {2, 3, 18, 19, 33, 61}:
                parts = []
                for q, tile in enumerate(raw):
                    ref = floor if tile == 61 else wall
                    parts.append({'donor': ref, 'srcX': q % 2 * 8,
                                  'srcY': 8 if tile in (18, 19, 33) else q // 2 * 8,
                                  'w': 8, 'h': 8, 'x': q % 2 * 8, 'y': q // 2 * 8})
                return self.comp(floor, parts, 'gen2_viridian_native_modular_partition')
        if name == 'FIGHTING_DOJO':
            if raw == (48, 48, 48, 48):
                return self.native(room.ref(705), 'gen2_dojo_complete_native_upper_wall')
            if raw == (78, 79, 94, 95):
                return {'kind': 'source_palette', 'sourceColors': [copy.deepcopy(WOOD) for _ in range(4)],
                        'role': 'gen2_dojo_original_complete_framed_calligraphy'}
            if raw in ((16, 1, 90, 91),):
                return self.template('gen1_gym_complete_rhydon_statue_plinth', floor)
        # Match only already reviewed source pixels in this same gym. Unknown
        # calligraphy or new GS symbols are held instead of guessing a glyph.
        return self.same_source(cell, (name,), game='red')

    def choose(self, cell, x, y, name, definition, data):
        if not all(attr.get('source_pixels_complete') for attr in cell['attributes']):
            return None
        if name.startswith('FAST_SHIP'):
            return self.maritime(cell, x, y, name, definition, data)
        if name in ('POWER_PLANT', 'SILPH_CO_1F', 'TRAINER_HOUSE_B1F'):
            return self.facility(cell, x, y, name, definition, data)
        if name == 'SAFFRON_MAGNET_TRAIN_STATION':
            return self.station(cell, x, y, definition, data)
        if name == 'VERMILION_PORT':
            return self.port(cell, name)
        return self.gym(cell, x, y, name, definition, data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate', action='store_true')
    parser.add_argument('--validate', action='store_true')
    parser.add_argument('--no-previews', action='store_true')
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    tool = Reviewer()
    baseline = json.loads(BASELINE.read_text())
    targets = {(row['game'], row['map']) for row in baseline['maps']
               if row['tileset'] in SETS and row['remaining_cells']}
    rows, held, stats = [], [], []
    for game in review.GAMES:
        data = review.source(tool.cache, game)
        for name in sorted(name for g, name in targets if g == game):
            definition = data['maps'][name]
            existing = [r for r in tool.active if r['game'] == game and r['tileset'] == definition['tileset']
                        and (r.get('map') is None or r['map'] == name)]
            generic = {(r['id'], r['quadrant']) for r in existing if r.get('x') is None}
            positioned = {(r['x'], r['y']) for r in existing if r.get('x') is not None}
            groups = {}
            for y in range(definition['height'] * 2):
                for x in range(definition['width'] * 2):
                    bid = definition['blocks'][y // 2 * definition['width'] + x // 2]
                    quadrant = y % 2 * 2 + x % 2
                    if (bid, quadrant) in generic or (x, y) in positioned:
                        continue
                    cell = review.cell_info(tool.cache, game, data, definition['tileset'], bid, quadrant)
                    value = tool.choose(cell, x, y, name, definition, data)
                    if value is None:
                        held.append({'game': game, 'map': name, 'id': bid, 'quadrant': quadrant,
                                     'x': x, 'y': y, 'raw': cell['tiles'], 'collision': cell['collision'],
                                     'sourceHash': cell['sourceHash'],
                                     'reason': 'Source hole or no unambiguous reviewed whole native counterpart'})
                        continue
                    seed = value.pop('_reviewed_source', None)
                    reviewed_evidence = value.pop('_reviewed_evidence', '')
                    row = {'game': game, 'style': 'gen3', 'map': name, 'tileset': definition['tileset'],
                           'id': bid, 'quadrant': quadrant, 'sourceHash': cell['sourceHash'],
                           'sourceFiles': data['fingerprints'][definition['tileset']],
                           'sourceCollision': cell['collision'],
                           'sourcePriority': [bool(a.get('priority')) for a in cell['attributes']],
                           'sourcePalettes': [a.get('palette', 1) for a in cell['attributes']],
                           'status': 'reviewed', 'sourceCells': [[x, y]],
                           'evidence': 'Explicit whole Gen3 maritime, station, facility or gym counterpart at native pixel size. '
                           'Only same-function reviewed source identities are transferred. Original maps, collision, holes, '
                           'transport, boarding, NPC interactions, controls and warps remain unchanged.'}
                    row.update(value)
                    if 'kind' not in row:
                        assert 'donor' in row, 'Legacy template has no explicit native artwork'
                        row['kind'] = 'native'
                    if row['kind'] == 'source_palette':
                        row['evidence'] = ('Original complete cartridge geometry retained in the already user-approved Gen3 color ramps; '
                            'not claimed as extracted hack artwork. The complete source pixels and per8px palette separation remain '
                            'unchanged. Original maps, collision, boarding, transport events, furniture interactions and warps remain unchanged.')
                        if reviewed_evidence:
                            row['evidence'] += ' Reviewed equivalent recipe: ' + reviewed_evidence
                        if row['role'].startswith('gen2_ship_original_'):
                            row['evidence'] += ' Cabin-floor palette slots use the exact checked native cabin-floor colors.'
                        row.setdefault('credit', 'Original Pokemon Gold/Silver/Crystal cartridge pixels recolored to match native Gen3 colors.')
                        row.setdefault('sourceUrl', 'https://github.com/pret/pokecrystal')
                        if row['role'] == 'gen2_dojo_original_complete_framed_calligraphy':
                            row['evidence'] = ('Original framed dojo calligraphy retains every original character, frame and source pixel '
                                'in the already approved Gen3 timber palette. The larger native FireRed scroll would cut or replace '
                                'these literal characters. This is recolored original cartridge geometry, not hack-native artwork. '
                                'Original room floor, collision, interactions, source map and warps remain unchanged.')
                            row['credit'] = 'Original Pokemon Gold/Silver/Crystal dojo calligraphy pixels in Gen3 timber colors.'
                    if seed:
                        row['reviewedSeed'] = seed
                    row['compositionPixelHash'] = catalog.sha(preview.replacement_image(tool.cache, row, tool.packed, ROOT).tobytes())
                    key = bid, quadrant, json.dumps(artwork(row), sort_keys=True)
                    if key in groups:
                        groups[key]['sourceCells'].append([x, y])
                    else:
                        groups[key] = row
            # A source alias with position-dependent artwork remains explicit.
            variants = Counter((r['id'], r['quadrant']) for r in groups.values())
            current = []
            for row in groups.values():
                if variants[row['id'], row['quadrant']] > 1:
                    for x, y in row['sourceCells']:
                        item = copy.deepcopy(row); item.update(x=x, y=y, sourceCells=[[x, y]]); current.append(item)
                else:
                    current.append(row)
            rows.extend(current)
            stats.append({'game': game, 'map': name, 'rows': len(current),
                          'new_source_cells': sum(len(row['sourceCells']) for row in current),
                          'remaining_cells': sum(r['game'] == game and r['map'] == name for r in held)})
    proof = review.validate_batch(rows, SimpleNamespace(cache=tool.cache,
              engine=ROOT.parent / '.tools/engine-0395', output=OUT), ROOT)
    (OUT / 'candidates.json').write_text(json.dumps(rows, indent=2) + '\n')
    (OUT / 'held.json').write_text(json.dumps(held, indent=2) + '\n')
    summary = {'rows': len(rows), 'added_source_cells': sum(len(r['sourceCells']) for r in rows),
               'remaining_cells': len(held), 'complete_map_variants': sum(s['remaining_cells'] == 0 for s in stats),
               'maps': stats, 'validation': proof, 'activated': args.activate}
    (OUT / 'proof.json').write_text(json.dumps(summary, indent=2) + '\n')
    if not args.no_previews:
        for name in ('FAST_SHIP_1F', 'FAST_SHIP_B1F', 'FAST_SHIP_CABINS_SE_SSE_CAPTAINS_CABIN',
                     'VERMILION_PORT', 'SAFFRON_MAGNET_TRAIN_STATION', 'POWER_PLANT', 'SILPH_CO_1F',
                     'TRAINER_HOUSE_B1F', 'CERULEAN_GYM', 'CELADON_GYM', 'FIGHTING_DOJO', 'VIRIDIAN_GYM'):
            preview.map_preview(tool.cache, OUT, 'crystal', name, 'staged-' + name,
                                tool.active + rows, tool.packed, 2, ROOT)
    if args.activate:
        write_rows(MODULE, rows)
    print(json.dumps({key: value for key, value in summary.items() if key != 'maps'}, indent=2))


if __name__ == '__main__':
    main()
