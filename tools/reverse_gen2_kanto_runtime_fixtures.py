"""Build the reviewed Crystal states of FRLG scripted indoor fixtures."""

import argparse
from collections import defaultdict
import copy
import json
from pathlib import Path

import catalog
from classic_geometry_review import art as geometry
from coverage import active_rows
import preview
from reverse_common import ROOT, ReverseReview
from reverse_gen2_hoenn_outdoor_complete import Review as LayoutReview


TARGET = ROOT / 'mappings/reverse_gen2_kanto_runtime_fixtures.lua'
GUARDS = Path(__file__).with_name('reverse_gen2_kanto_runtime_fixtures_guards.json')
GAMES = ('firered', 'leafgreen')
PAIRS = {
    'silph': ('building__rom_082d4ecc', 'building__rom_082d4eac'),
    'league': ('building__rom_082d50c4', 'building__rom_082d50a4'),
    'gym': ('building__rom_082d4d34', 'building__rom_082d4d14'),
    'mansion': ('building__rom_082d4f2c', 'building__rom_082d4f0c'),
}
ELEVATOR = {745: 744, 746: 744, 753: 752, 754: 752, 761: 760, 762: 760}
ROCKET = {718: 642, 719: 641, 726: 642, 727: 641}
SILPH = {944: 821, 945: 820, 952: 821, 953: 820,
         960: None, 961: None, 962: 821, 963: 821, 964: 820, 965: 820}
LEAGUE = {654: 651, 669: 666, 670: 667, 671: 668, 677: 674, 678: 675, 679: 676}
GYM = {659: 681, 660: 682, 661: 683, 662: 684, 667: 689, 668: 690,
       669: 691, 670: 692, 699: 681, 700: 682, 701: 645, 702: 683,
       703: 684, 707: 689, 708: 690, 709: 653, 710: 691, 711: 692}
MANSION = {845: 788, 847: 790}
IDS = {'silph': set(ELEVATOR) | set(ROCKET) | set(SILPH), 'league': set(LEAGUE),
       'gym': set(GYM), 'mansion': set(MANSION)}
ACTUAL_STATUES = {'FR_POKEMON_MANSION_1F': {(845, 5, 4)},
                  'FR_POKEMON_MANSION_2F': {(845, 2, 15)},
                  'FR_POKEMON_MANSION_3F': {(845, 12, 4)},
                  'FR_POKEMON_MANSION_B1F': {(847, 24, 28), (847, 27, 4)}}


class Review(ReverseReview):
    native_layout = LayoutReview.native_layout

    def __init__(self, stage):
        super().__init__('gen2-kanto-runtime-fixtures', GAMES)
        self.stage = stage
        self.layouts, self.layout_hashes = {}, {}
        self.sources = {}
        self.witnesses = {}
        names = {pair for pairs in PAIRS.values() for pair in pairs}
        _, rows = active_rows(stage)
        self.active = {(r['game'], r['tileset'], r['id'], r.get('map')): r for r in rows
                       if r['game'] in GAMES and r['style'] == 'gen2' and r['tileset'] in names}

    def source(self, game, pair, mid):
        key = game, pair, mid
        if key not in self.sources:
            cell = self.imp.cell_index(game)[pair, mid]
            preview.native_donor(self.cache, dict(game=game, tileset=pair, id=mid,
                                 hash=cell['pixel_sha256']), self.packed)
            ids, palette, layers = self.packed[game, pair]
            start = ids.index(mid) * 256
            self.sources[key] = {name: list(catalog.rgba_native(
                layer[start:start+256], palette, name != 'under').get_flattened_data())
                for name, layer in layers.items()}
        return self.sources[key]

    def anchor(self, game, pair, mid):
        key = game, pair, mid, None
        row = self.active[key]
        assert row['sourceHash'] == self.imp.cell_index(game)[pair, mid]['pixel_sha256']
        self.witnesses[f'{game}/{pair}/{mid}'] = catalog.sha(
            json.dumps(row, sort_keys=True).encode())
        return row

    @staticmethod
    def recipe(row):
        art = row['classicGeometry']
        return [tuple(rgb) for rgb in art['palette']], {
            tuple(rgb[:3]): tuple(rgb[3:]) for rgb in art['colorMap']}

    def floor(self, game, pair, mid, donor, predicate):
        masks = {}
        for name, pixels in self.source(game, pair, mid).items():
            bits = ''.join('1' if p[3] and predicate(name, i, p) else '0'
                           for i, p in enumerate(pixels))
            if '1' in bits:
                masks[name] = bits
        assert masks, (game, pair, mid)
        return dict(donor=copy.deepcopy(donor), masks=masks)

    def anchored_floor(self, game, pair, mid, reference, area):
        anchor = self.anchor(game, pair, reference)
        original = self.source(game, pair, reference)
        return self.floor(game, pair, mid, anchor['donor'], lambda name, i, p:
                          name in ('under', 'mid') and area(i % 16, i // 16)
                          and p == original['under'][i])

    def fixture(self, game, pair, mid, family):
        if family == 'league':
            palette, colors = self.recipe(self.anchor(game, pair, LEAGUE[mid]))
            for ref in (651, 668, 674, 676):
                _, companion = self.recipe(self.anchor(game, pair, ref))
                colors.update(companion)
            return geometry(self, game, pair, mid, 'kanto_league_scripted_shutter', palette, colors)
        if family == 'gym':
            if mid == 701:
                return self.native(self.anchor(game, pair, 641)['donor'],
                                   'kanto_vermilion_scripted_clear_beam_floor')
            palette, colors = self.recipe(self.anchor(game, pair, GYM[mid]))
            colors.update({(82, 82, 107): palette[3], (206, 82, 66): palette[1],
                           (255, 132, 115): palette[0]})
            shades = {(165, 165, 99), (189, 181, 107), (206, 197, 123), (222, 222, 148)}
            ground = self.floor(game, pair, mid, self.anchor(game, pair, 641)['donor'],
                                lambda name, i, p: name != 'over' and p[:3] in shades)
            return geometry(self, game, pair, mid, 'kanto_vermilion_scripted_beam_state',
                            palette, colors, ground=ground)
        if family == 'mansion':
            ref = MANSION[mid]
            anchor = self.anchor(game, pair, ref)
            palette, colors = self.recipe(anchor)
            original = self.source(game, pair, ref)
            source = self.source(game, pair, mid)
            red = {(181, 0, 0), (255, 0, 0)}
            assert source.keys() == original.keys()
            for name in source:
                changes = [(a, b) for a, b in zip(original[name], source[name]) if a != b]
                assert all(a[3] == b[3] and b[:3] in red for a, b in changes)
                assert len(changes) == (8 if name == 'over' else 0), (mid, name, len(changes))
            # Share the existing green stone and exact floor. Its bright stone
            # shade shares the middle value so red can occupy one palette slot.
            colors = {src: palette[1] if rgb == palette[0] else rgb for src, rgb in colors.items()}
            colors.update({(181, 0, 0): palette[3], (255, 0, 0): (255, 82, 82)})
            palette[0] = (255, 82, 82)
            return geometry(self, game, pair, mid, 'kanto_mansion_scripted_glowing_switch_statue',
                            palette, colors, ground=anchor['classicGeometry']['ground'])
        if mid in ELEVATOR:
            palette, colors = self.recipe(self.anchor(game, pair, ELEVATOR[mid]))
            return geometry(self, game, pair, mid, 'kanto_scripted_elevator_window_frame', palette, colors)
        if mid in ROCKET:
            palette, _ = self.recipe(self.anchor(game, pair, 713))
            cream, lit, dark, edge = palette
            colors = {(82, 82, 107): edge, (123, 123, 123): edge, (132, 132, 82): dark,
                      (148, 148, 165): dark, (165, 165, 99): lit, (197, 197, 156): cream,
                      (222, 156, 140): lit, (239, 214, 173): cream, (255, 255, 255): cream}
            floor = self.anchor(game, pair, ROCKET[mid])['donor']
            ground = self.floor(game, pair, mid, floor, lambda name, i, p:
                                name in ('under', 'mid') and (mid < 726 or i // 16 >= 14))
            return geometry(self, game, pair, mid, 'kanto_rocket_scripted_security_barrier',
                            palette, colors, ground=ground)
        palette, colors = self.recipe(self.anchor(game, pair, 825))
        for ref in (838, 839):
            _, wall_colors = self.recipe(self.anchor(game, pair, ref))
            colors.update(wall_colors)
        lit, face, edge, _ = palette
        colors.update({(107, 156, 165): face, (115, 115, 115): edge, (115, 156, 148): face,
                       (189, 197, 197): face, (206, 214, 214): lit, (230, 214, 115): lit})
        ref = SILPH[mid]
        areas = {944: lambda x, y: True, 945: lambda x, y: True,
                 962: lambda x, y: x < 12, 963: lambda x, y: x >= 4,
                 964: lambda x, y: y < 8, 965: lambda x, y: y < 8}
        ground = None
        if mid in (952, 953):
            floor = self.anchor(game, pair, ref)['donor']
            ground = self.floor(game, pair, mid, floor, lambda name, i, p: name == 'under' and i // 16 >= 14)
        elif ref:
            ground = self.anchored_floor(game, pair, mid, ref, areas[mid])
        return geometry(self, game, pair, mid, 'kanto_silph_scripted_card_key_barrier',
                        palette, colors, ground=ground)

    def source_context(self, game, pair, mid, hits):
        contexts = []
        scripts = self.imp.table(game, 'gba/scripts/scripts')
        for name, kind, address, index, x, y in hits:
            layout = self.native_layout(game, name)
            assert layout['pair'] == pair and 0 <= x < layout['width'] and 0 <= y < layout['height']
            cell = layout['cells'][y*layout['width']+x]
            command = scripts[address][index]
            if kind == 'script':
                assert command['op'] == 'setmetatile' and (command['1'], command['2'], command['3']) == (x, y, mid)
                if mid in MANSION and pair in PAIRS['mansion']:
                    assert cell[0] == MANSION[mid], (name, mid, cell)
            else:
                assert kind == 'elevator' and mid in ELEVATOR
                assert command['op'] == 'special' and command.get('id', command.get('1')) == 273
                assert cell[0] == ELEVATOR[mid], (name, mid, cell)
            contexts.append(dict(map=name, x=x, y=y, original=list(cell), script=address,
                                 instruction=index, command=command))
        return contexts

    def build(self, hits):
        members = []
        for family, pairs in PAIRS.items():
            for game, pair in zip(GAMES, pairs):
                for mid in sorted(IDS[family]):
                    key = game, pair, mid
                    assert not any(k[:3] == key for k in self.active), key
                    contexts = self.source_context(*key, hits['/'.join((game, pair, str(mid)))])
                    assert contexts, key
                    art = self.fixture(*key, family)
                    row = self.row(*key, 'gen2', art,
                                   'Reachable indoor script state keeps the reviewed material of its complete fixture. '
                                   'Original graphic placement, color-bearing pixel geometry and priority planes are retained.')
                    cell = self.imp.cell_index(game)[pair, mid]
                    members.append(dict(game=game, pair=pair, mid=mid, contexts=contexts,
                                        source_hash=cell['pixel_sha256'], source_layers=cell['layer_sha256'],
                                        source_behavior=cell['behavior'], output_hash=row['compositionPixelHash']))
        assert len(self.rows) == 94
        return dict(hits=hits, layouts=self.layout_hashes, anchors=self.witnesses, members=members)


def from_audit(path):
    hits = defaultdict(list)
    for item in json.loads(path.read_text(encoding='utf-8')):
        game, name, pair, mid = (item[k] for k in ('game', 'map', 'pair', 'mid'))
        if not item['atlas'] or item['body'] or item['border'] or item['valid']:
            continue
        family = next((name for name, pairs in PAIRS.items() if pair in pairs), None)
        if family is None or mid not in IDS[family]:
            continue
        key = f'{game}/{pair}/{mid}'
        for kind, address, index, *args in item['origins']:
            if kind == 'script':
                x, y = args
                if family != 'mansion' or (mid, x, y) in ACTUAL_STATUES[name]:
                    hits[key].append([name, kind, address, index, x, y])
            else:
                assert kind == 'special' and args == ['AnimateElevator'] and mid in ELEVATOR
                y = (mid - 745) // 8
                for x in range(1, 4):
                    hits[key].append([name, 'elevator', address, index, x, y])
    return {key: sorted(values) for key, values in sorted(hits.items())}


def gpu_witnesses(members):
    for row in members:
        game, pair, mid = (row[key] for key in ('game', 'pair', 'mid'))
        hit = next(hit for hit in row['contexts'] if hit['original'][0] != mid)
        command = hit['command']
        yield dict(game=game, pair=pair, mid=mid, map=hit['map'], x=hit['x'], y=hit['y'],
                   before_mid=hit['original'][0], impassable=command['op'] == 'special' or bool(command['4']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, default=ROOT)
    parser.add_argument('--freeze-from-audit', type=Path)
    parser.add_argument('--validate', action='store_true')
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    assert not args.activate or args.validate
    review = Review(args.baseline.resolve())
    if args.freeze_from_audit:
        proof = review.build(from_audit(args.freeze_from_audit))
        GUARDS.write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    else:
        expected = json.loads(GUARDS.read_text(encoding='utf-8'))
        proof = review.build(expected['hits'])
        assert proof == expected, 'Reviewed script, body layout, source pixels or output changed'
    review.write(review.out / 'candidate.lua')
    witnesses = list(gpu_witnesses(proof['members']))
    (review.out / 'script-witnesses.json').write_text(json.dumps(witnesses, indent=2) + '\n', encoding='utf-8')
    keys = [{key: witness[key] for key in ('game', 'pair', 'mid')} for witness in witnesses]
    (review.out / 'keys.json').write_text(json.dumps(keys, indent=2) + '\n', encoding='utf-8')
    result = review.validate() if args.validate else None
    if args.activate:
        review.write(TARGET)
    print(json.dumps(dict(rows=len(review.rows), proof=result, activated=args.activate)))


if __name__ == '__main__':
    main()
