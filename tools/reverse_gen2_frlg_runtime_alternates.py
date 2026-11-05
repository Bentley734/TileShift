"""Build guarded Crystal counterparts for the original FRLG clinic and PC states."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import catalog
from classic_geometry_review import art as classic_art
from coverage import active_rows
import preview
from reverse_common import ROOT, ReverseReview


TARGET = ROOT / 'mappings/reverse_gen2_frlg_runtime_alternates.lua'
GUARDS = ROOT / 'tools/reverse_gen2_frlg_runtime_alternates_guards.json'
GAMES = ('firered', 'leafgreen')

# These pairs follow the engine's SpecialFieldAnim tables. The engine chooses
# the current MID, so these replacements do not create a second animation.
ESCALATORS = {
    720: (778, 776),
    721: (779, 777),
    728: (786, 784),
    729: (787, 785),
    739: (790, 788),
    740: (791, 789),
    747: (798, 796),
}
CELIO = {858: 856, 859: 857, 861: 860, 863: 862}
WITNESSES = {('network', mid): normal for normal, alts in ESCALATORS.items() for mid in alts}
WITNESSES.update({('network', mid): normal for mid, normal in CELIO.items()})
WITNESSES.update({('network', 99): 98, ('network', 759): 761, ('player_house', 650): 655})
EXTRA_PC_PAIRS = {
    'firered': ('building__rom_082d4f74', 'building__rom_082d4cec', 'oak_lab',
                'building__rom_082d5094', 'building__rom_082d4ecc'),
    'leafgreen': ('building__rom_082d4f54', 'building__rom_082d4ccc', 'oak_lab',
                  'building__rom_082d5074', 'building__rom_082d4eac'),
}


def source_witnesses(game):
    return WITNESSES | {(pair, 99): 98 for pair in EXTRA_PC_PAIRS[game]}

CREAM = (247, 230, 214)
DARK = (58, 58, 58)
GRAY = (107, 107, 107)
SILVER = (156, 156, 156)
BLUE = (123, 132, 255)
NAVY = (74, 74, 255)
GREEN = (82, 148, 49)
RED = (247, 82, 49)
PALE_GREEN = (222, 255, 222)
FLOOR_INDICES = {198, 199, 200, 201, 202}
SOURCE_FLOOR_COLORS = {
    (197, 181, 140): SILVER,
    (214, 206, 156): SILVER,
    (230, 222, 156): CREAM,
    (239, 239, 173): CREAM,
    (247, 247, 206): CREAM,
}
STAIR_COLORS = {
    (82, 82, 107): DARK,
    (123, 123, 140): DARK,
    (140, 181, 173): SILVER,
    (148, 148, 165): SILVER,
    (156, 115, 90): DARK,
    (197, 222, 206): CREAM,
    (206, 189, 197): CREAM,
    (255, 99, 49): RED,
    (255, 255, 255): CREAM,
    **SOURCE_FLOOR_COLORS,
}


class Review(ReverseReview):
    def __init__(self):
        super().__init__('frlg-runtime-alternates', GAMES)

    def source(self, game, pair, mid):
        cell = self.imp.cell_index(game)[pair, mid]
        preview.native_donor(self.cache, dict(game=game, tileset=pair, id=mid, hash=cell['pixel_sha256']), self.packed)
        mids, palette, atlas = self.packed[game, pair]
        offset = 256 * mids.index(mid)
        indices = {name: data[offset:offset + 256] for name, data in atlas.items()}
        planes = {name: catalog.rgba_native(values, palette, name != 'under') for name, values in indices.items()}
        return cell, indices, planes

    def exact_geometry(self, game, pair, mid, name, palette, color_map, ground=None):
        _, _, planes = self.source(game, pair, mid)
        colors = {pixel[:3] for plane in planes.values() for pixel in plane.get_flattened_data() if pixel[3]}
        assert colors <= color_map.keys(), (game, pair, mid, sorted(colors - color_map.keys()))
        return classic_art(self, game, pair, mid, name, palette,
                           {rgb: color_map[rgb] for rgb in sorted(colors)}, ground=ground)

    def floor(self, game, pair, mid, donor):
        if not donor:
            return None
        _, indices, planes = self.source(game, pair, mid)
        masks = {}
        for name, image in planes.items():
            mask = ''.join('1' if pixel[3] and indices[name][offset] in FLOOR_INDICES else '0'
                           for offset, pixel in enumerate(image.get_flattened_data()))
            if '1' in mask:
                masks[name] = mask
        return dict(donor=donor, masks=masks) if masks else None

    def pc_source_planes(self, game, pair, mid, base):
        _, _, old_source = self.source(game, pair, base['id'])
        _, _, new_source = self.source(game, pair, mid)
        assert old_source.keys() == new_source.keys()
        assert all(old_source[name].getchannel('A').tobytes() == new_source[name].getchannel('A').tobytes()
                   for name in old_source)
        return old_source, new_source

    def lit_native_pc(self, game, pair, mid, base):
        self.pc_source_planes(game, pair, mid, base)
        if pair == 'network':
            parts = copy.deepcopy(base['parts'])
            backing = None
            regions = ((parts[-2], 5, 8), (parts[-1], 8, 10))
            left, right = 3, 13
            rgb = {DARK: BLUE, GRAY: (189, 206, 255), SILVER: PALE_GREEN}
            role = 'classic_gen2_clinic_lit_crystal_pc'
        else:
            assert base['role'] == 'kanto_club_shop_complete_native_daycare_furniture'
            backing = base['donor']
            parts = []
            regions = ((dict(donor=backing, srcY=0, y=0), 13, 16),)
            left, right = 4, 12
            rgb = {DARK: BLUE, NAVY: (189, 206, 255), BLUE: PALE_GREEN}
            role = 'classic_gen2_daycare_lit_crystal_pc'
        screen = set()
        for part, top, bottom in regions:
            donor = copy.deepcopy(part['donor'])
            palettes = preview.palette_set(self.imp.table('crystal', 'palettes'),
                                           self.imp.table('crystal', 'maps')[donor['map']], donor['daytime'])
            donor['palettes'] = [[list(rgb.get(tuple(shade), tuple(shade))) for shade in palette]
                                 for palette in palettes]
            parts.append(dict(donor=donor, srcX=left, srcY=part['srcY'] + top - part['y'],
                              x=left, y=top, w=right - left, h=bottom - top))
            screen.update(y * 16 + x for y in range(top, bottom) for x in range(left, right))
        art = self.composite(backing, parts, role)
        art['overMask'] = base['overMask']
        original, lit = self.render(base), self.render(art)
        changes = {i for i, (a, b) in enumerate(zip(original.get_flattened_data(), lit.get_flattened_data())) if a != b}
        assert len(changes) >= len(screen) * 0.8 and changes <= screen
        return art

    def lit_source_pc(self, game, pair, mid, base):
        old, lit = self.pc_source_planes(game, pair, mid, base)
        changed_source = set()
        for name in old:
            changed_source.update(i for i, (a, b) in enumerate(zip(old[name].get_flattened_data(),
                                                                   lit[name].get_flattened_data())) if a != b)
        geometry = base['classicGeometry']
        color_map = {tuple(row[:3]): tuple(row[3:]) for row in geometry['colorMap']}
        palette = tuple(tuple(rgb) for rgb in geometry['palette'])
        if base['role'] == 'lobby_complete_terminal_or_elevator':
            assert DARK not in color_map.values()
            palette = tuple(BLUE if rgb == DARK else rgb for rgb in palette)
        shadow = SILVER if pair == 'oak_lab' else BLUE
        color_map.update({(140, 181, 222): shadow, (189, 230, 255): CREAM})
        art = self.exact_geometry(game, pair, mid, 'original_room_pc_power_on', palette,
                                  color_map, geometry.get('ground'))
        original = self.render(base)
        rendered = self.render(dict(art, game=game, style='gen2', tileset=pair, id=mid,
                                    sourceHash=self.imp.cell_index(game)[pair, mid]['pixel_sha256']))
        changed_output = {i for i, (a, b) in enumerate(zip(original.get_flattened_data(),
                                                            rendered.get_flattened_data())) if a != b}
        assert len(changed_output) >= 40 and changed_output <= changed_source, (game, pair, mid)
        return art

    def variant(self, game, pair, mid, base):
        if mid == 99:
            recipe = (self.lit_source_pc(game, pair, mid, base) if base['kind'] == 'classic_native_geometry'
                      else self.lit_native_pc(game, pair, mid, base))
            opening = ('The original clinic PC-on metatile lights the exact screen inside the already selected complete Crystal cabinet. '
                       if pair == 'network' else
                       'The original PC-on metatile lights the exact screen inside the already selected complete cabinet. ')
            return recipe, (opening +
                            'The case, monitor glass boundary, keyboard and layer masks stay aligned through each original flicker.')

        geometry = base['classicGeometry']
        color_map = {tuple(row[:3]): tuple(row[3:]) for row in geometry['colorMap']}
        palette = tuple(tuple(rgb) for rgb in geometry['palette'])
        donor = geometry.get('ground', {}).get('donor')
        ground = self.floor(game, pair, mid, donor) if pair == 'network' else geometry.get('ground')
        if pair == 'player_house':
            assert mid == 650
            color_map.update({(82, 148, 197): SILVER if SILVER in palette else (173, 173, 173),
                              (156, 214, 255): PALE_GREEN})
            feature, evidence = 'bedroom_pc_power_on', (
                'The native bedroom PC-on state lights the complete original screen in the same four-tone cabinet. '
                'The exact frame and room floor are retained, with the established pale Crystal monitor color.')
        elif mid in CELIO:
            if mid in (858, 859):
                palette = (CREAM, NAVY, DARK, GREEN)
                color_map[(0, 230, 115)] = GREEN
            elif mid == 861:
                palette = (CREAM, NAVY, DARK, RED)
                color_map.update({(132, 181, 206): NAVY, (206, 49, 0): RED, (255, 66, 0): RED})
            else:
                color_map.update({(0, 58, 197): NAVY, (8, 90, 255): BLUE})
            feature, evidence = 'celio_machine_status_lights', (
                'The original One Island Network Machine keeps its complete case, blue panels and native signal positions. '
                'The exact green screen pattern and the red and blue status indicators follow the scripted states.')
        elif mid == 759:
            palette = (CREAM, SILVER, RED, DARK)
            color_map.update(SOURCE_FLOOR_COLORS)
            color_map.update({(181, 181, 165): SILVER, (189, 99, 74): RED,
                              (206, 82, 66): RED, (255, 132, 115): RED})
            feature, evidence = 'link_desk_entry_state', (
                'The complete upstairs cable club desk state retains the original lowered marker and the matching Crystal floor.')
        else:
            assert mid in {alt for phases in ESCALATORS.values() for alt in phases}
            palette = (CREAM, SILVER, RED, DARK)
            color_map = STAIR_COLORS
            feature, evidence = 'clinic_escalator_original_step_phase', (
                'This is the exact original alternate position of the complete clinic escalator treads and rail. '
                'The same floor and Crystal tones meet the adjoining landings, with the native step order and direction.')
        recipe = self.exact_geometry(game, pair, mid, feature, palette, color_map, ground)
        return recipe, evidence

    def verify_phases(self, witnesses):
        for game in self.games:
            for normal, alternates in ESCALATORS.items():
                key = game, 'network', normal
                hashes = [witnesses[key]['compositionPixelHash']]
                hashes.extend(self.rows[game, 'gen2', 'network', mid, None]['compositionPixelHash'] for mid in alternates)
                assert len(set(hashes)) == 3, ('An escalator phase lost a visible step position', key)


def freeze(review, baseline, audit):
    _, rows = active_rows(baseline)
    wanted = {(game, pair, mid) for game in GAMES for pair, mid in source_witnesses(game)}
    sources = {}
    for item in json.loads(audit.read_text()):
        key = item['game'], item['pair'], item['mid']
        if key not in wanted:
            continue
        assert item['atlas'] and not item['body'] and not item['border'] and not item['valid'], key
        sources.setdefault(key, {})[item['map']] = sorted(item['origins'], key=json.dumps)
    assert sources.keys() == wanted
    active = {(row['game'], row['tileset'], row['id']): row for row in rows
              if row['game'] in GAMES and row.get('style') == 'gen2' and not row.get('map')}
    assert not (wanted & active.keys())
    result = []
    for game, pair, mid in sorted(wanted):
        base = active[game, pair, source_witnesses(game)[pair, mid]]
        source, _, _ = review.source(game, pair, mid)
        recipe, evidence = review.variant(game, pair, mid, base)
        row = review.row(game, pair, mid, 'gen2', recipe, evidence)
        result.append(dict(game=game, pair=pair, mid=mid, sourceHash=source['pixel_sha256'],
                           sourceBehavior=source.get('behavior'), sourceLayers=source['layer_sha256'],
                           witnessMid=base['id'], witnessOutputHash=base['compositionPixelHash'],
                           source_maps=sources[game, pair, mid], recipe=recipe, review=evidence,
                           expectedOutputHash=row['compositionPixelHash']))
    review.verify_phases(active)
    document = dict(format=1, auditSha256=catalog.sha(audit.read_bytes()), sources=result)
    GUARDS.write_text(json.dumps(document, indent=2, sort_keys=True) + '\n')


def build(review):
    guards = json.loads(GUARDS.read_text())
    assert guards['format'] == 1
    for saved in guards['sources']:
        game, pair, mid = saved['game'], saved['pair'], saved['mid']
        source, _, _ = review.source(game, pair, mid)
        assert saved['witnessMid'] == source_witnesses(game)[pair, mid] and saved['source_maps']
        assert (source['pixel_sha256'], source.get('behavior'), source['layer_sha256']) == (
            saved['sourceHash'], saved['sourceBehavior'], saved['sourceLayers'])
        row = review.row(game, pair, mid, 'gen2', saved['recipe'], saved['review'])
        assert row['compositionPixelHash'] == saved['expectedOutputHash'], (game, pair, mid)
    expected = {(game, 'gen2', pair, mid, None) for game in GAMES for pair, mid in source_witnesses(game)}
    assert review.rows.keys() == expected
    return guards


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze', type=Path, metavar='BASELINE_MOD')
    parser.add_argument('--audit', type=Path)
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    review = Review()
    if args.freeze:
        assert args.audit, 'A frozen runtime script and layout audit is required'
        freeze(review, args.freeze, args.audit)
        review.rows = {}
    guards = build(review)
    neutral = review.validate()
    assert neutral['accepted']['gen2'] == len(review.rows) and not neutral['rejected'], neutral
    candidate = review.out / TARGET.name
    review.write(candidate)
    if args.activate:
        TARGET.write_bytes(candidate.read_bytes())
    report = dict(new_keys=len(review.rows), logical_cells_added=0, neutral=neutral,
                  source_map_variants=len({(s['game'], name) for s in guards['sources'] for name in s['source_maps']}),
                  sha256=catalog.sha(candidate.read_bytes()))
    (review.out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
