"""Finish Celadon City and its FireRed and LeafGreen approach tiles."""
from collections import Counter
from pathlib import Path
import argparse
import json
import zlib

import catalog
import preview
from classic_geometry_review import art as geometry_art, source_under_frames
from gb_theme_animation import specification
from johto_remaining_review import artwork
from reverse_common import ROOT, ReverseReview
from reverse_gen2_hoenn_outdoor_complete import Review as Layouts

GAMES = ('firered', 'leafgreen')
PAIRS = dict(firered='general__rom_082d4b3c', leafgreen='general__rom_082d4b1c')
OUTPUT = ROOT.parent / '.work/tileshift-v0360-celadon'
TARGET = ROOT / 'mappings/reverse_gen2_kanto_celadon.lua'
GUARDS = Path(__file__).with_name('reverse_gen2_kanto_celadon_guards.json')

# Each group uses full original Crystal cells at native size. The source's
# repeated interiors use the same native panel at every repeated position.
STORE = {
    641: (2, 2), 642: (3, 2), 643: (7, 2), 645: (3, 2), 646: (4, 2), 647: (6, 2),
    649: (2, 3), 650: (4, 3), 651: (7, 3), 653: (3, 3), 654: (4, 3), 655: (6, 3),
    661: (3, 3), 662: (4, 3), 663: (6, 3), 657: (2, 4), 658: (3, 4), 659: (7, 4),
    669: (3, 4), 670: (4, 4), 671: (6, 4), 665: (2, 5), 666: (3, 5), 667: (5, 5),
    668: (7, 5), 648: (4, 5), 656: (4, 5), 673: (2, 6), 674: (3, 6), 675: (5, 6),
    676: (7, 6), 644: (4, 6), 664: (5, 6), 672: (4, 7), 652: (5, 7),
    681: (2, 9), 682: (3, 9), 683: (6, 9), 684: (7, 9), 660: (4, 9),
}
TOWNHOUSES = {
    729: (8, 4), 730: (9, 4), 731: (9, 4), 732: (11, 4), 734: (8, 4), 735: (9, 4),
    736: (8, 5), 737: (9, 5), 738: (9, 5), 739: (10, 5), 740: (11, 5),
    744: (8, 6), 745: (9, 6), 746: (10, 6), 747: (10, 6), 748: (11, 6),
    749: (8, 4), 750: (9, 4), 757: (10, 4), 758: (11, 4), 774: (11, 4),
    752: (8, 7), 753: (9, 7), 754: (10, 7), 755: (10, 7), 756: (11, 7),
    760: (8, 9), 761: (9, 9), 762: (10, 9), 763: (10, 9), 764: (11, 9),
    768: (9, 6), 769: (9, 6), 770: (10, 6), 771: (10, 6),
    751: (9, 9), 759: (10, 9), 765: (9, 9), 766: (10, 9), 767: (9, 8),
    772: (10, 7), 773: (9, 7), 776: (9, 7), 777: (9, 7), 778: (10, 7), 779: (10, 7),
    780: (9, 9), 781: (10, 9), 784: (8, 6), 785: (9, 6), 786: (10, 6), 787: (11, 6),
    788: (8, 7), 789: (9, 7), 790: (10, 7), 741: (8, 9), 743: (10, 9),
}
ARCADE = {
    688: (16, 16), 689: (18, 16), 690: (21, 16), 691: (18, 17), 692: (19, 17),
    696: (16, 17), 697: (18, 17), 698: (20, 17), 699: (19, 17), 700: (19, 17),
    704: (16, 17), 705: (19, 17), 706: (21, 17), 693: (18, 18), 694: (20, 18),
    695: (18, 18), 711: (18, 18), 712: (16, 18), 713: (19, 18), 714: (21, 18),
    701: (17, 19), 702: (20, 19), 703: (17, 19), 707: (16, 19), 708: (21, 19),
}
HOUSE = {44: (8, 4), 45: (9, 4), 47: (11, 4), 52: (8, 5), 53: (9, 5), 54: (10, 5),
         55: (11, 5), 60: (8, 6), 61: (18, 19), 63: (11, 6), 6: (9, 6), 7: (10, 6),
         66: (9, 6), 67: (10, 6), 861: (8, 4), 862: (11, 4)}
ROOF_FILL = {
    649: (2, 2), 650: (4, 2), 651: (7, 2), 653: (3, 2), 654: (4, 2), 655: (6, 2),
    736: (8, 4), 737: (9, 4), 738: (9, 4), 739: (10, 4), 740: (11, 4),
    691: (18, 16), 692: (19, 16), 696: (16, 16), 697: (18, 16), 698: (20, 16),
    699: (19, 16), 700: (19, 16), 704: (16, 16), 705: (19, 16), 706: (21, 16),
}
CURB = {214, 215, 232, 234, 240, 241, 242, 243, 252, 814, 815, 822, 823, 851, 852}
GRASS = {205, 207, 677, 678, 679, 680, 686, 709, 710, 742, 782, 783, 791, 799, 824, 826,
         827, 829, 835, 837, 840, 843, 845, 846, 848, 849}
PATH = {258, 259, 260, 261, 847}
SHORE = {264, 265, 271, 274, 275, 279, 282, 283, 287, 290, 292, 296, 297, 484, 871}
STEEP = {132, 134, 161, 168, 306, 307, 308}
WALKWAYS = {734, 792, 793, 794, 795, 796, 797, 798, 800, 801, 802, 806, 816, 817, 818}
GATES = {84, 85, 86, 93, 103}
FOUNTAIN = set(range(717, 729))
TRACK = {803, 804, 805, 811, 812, 813, 819, 820, 821}
ARCH_PALETTE = [(58, 58, 58), (132, 107, 25), (197, 148, 58), (222, 255, 222)]
STONE_PALETTE = [(58, 58, 58), (107, 107, 107), (173, 173, 173), (222, 255, 222)]
BLUE_PALETTE = [(58, 58, 58), (58, 90, 123), (115, 140, 255), (222, 255, 222)]
RAIL_PALETTE = [(58, 58, 58), (165, 49, 41), (247, 82, 49), (255, 156, 197)]


class Review(Layouts):
    def __init__(self):
        ReverseReview.__init__(self, 'gen2-kanto-celadon', GAMES)
        self.out = OUTPUT
        self.layouts = {}
        self.layout_hashes = {}
        self.guards = json.loads(GUARDS.read_text(encoding='utf-8'))
        self.ground = self.gb_at('crystal', 'ROUTE_16', 6, 3)
        assert set(self.gb_image(self.ground).get_flattened_data()) == {(222, 255, 222, 255)}
        self.water = self.gb_ref('crystal', 'UNION_CAVE_1F', 15, 0)
        self.water_program = specification(self.cache, self.water, 'program')
        assert self.water_program
        self.sign = self.gb_at('crystal', 'CELADON_CITY', 13, 9)
        self.sources = {}
        names = {entry['alias']['module'] for entry in self.guards if 'alias' in entry}
        names.add('mappings/reverse_gen2_kanto_final.lua')
        for name in sorted(names):
            for row in preview.read_reviewed(ROOT / name):
                self.sources[row['game'], row['tileset'], row['id']] = row

    def render(self, row):
        return preview.replacement_image(self.cache, row, self.packed, ROOT)

    def planes(self, game, mid):
        pair = PAIRS[game]
        source = self.imp.cell_index(game)[pair, mid]
        preview.native_donor(self.cache, dict(game=game, tileset=pair, id=mid, hash=source['pixel_sha256']), self.packed)
        mids, colors, blobs = self.packed[game, pair]
        start = mids.index(mid) * 256
        return {name: catalog.rgba_native(blob[start:start + 256], colors, name != 'under')
                for name, blob in blobs.items()}

    def source_colors(self, game, mids):
        return {pixel[:3] for mid in mids for pixel in self.planes(game, mid)['under'].get_flattened_data()}

    def exact_alias(self, item):
        game, pair, mid = (item[key] for key in ('game', 'pair', 'mid'))
        alias = item['alias']
        other = self.imp.cell_index(game)[alias['pair'], alias['mid']]
        source = self.imp.cell_index(game)[pair, mid]
        assert all(source[key] == other[key] for key in ('pixel_sha256', 'layer_sha256', 'behavior'))
        row = self.sources[game, alias['pair'], alias['mid']]
        assert row['compositionPixelHash'] == alias['output'] and row['role'] == alias['role']
        art = artwork(row)
        art['role'] = 'reverse_gen2_celadon_complete_native_alias'
        art['overMask'] = row.get('overMask', '0' * 256)
        return art

    def shape(self, game, mid, feature, palette, backing=None, colors=(), animation=None):
        planes = self.planes(game, mid)
        changed, middle = set(), set()
        if animation:
            _, changed, middle = source_under_frames(self.cache, game, PAIRS[game], mid, self.packed, animation)
        forced = {'under': changed, 'mid': middle}
        masks, color_map = {}, {}
        for name, image in planes.items():
            pixels = list(image.get_flattened_data())
            for r, g, b, a in pixels:
                if a:
                    light = (54 * r + 183 * g + 19 * b) / 256
                    color_map[r, g, b] = palette[sum(light >= cut for cut in (86, 148, 205))]
            if backing:
                mask = ''.join('1' if p[3] and (p[:3] in colors or i in forced.get(name, ())) else '0'
                               for i, p in enumerate(pixels))
                if '1' in mask:
                    masks[name] = mask
        ground = dict(donor=backing, masks=masks) if masks else None
        if backing == self.water and (not animation or animation['mode'] == 'water_mask'):
            assert ground
            ground['animation'] = self.water_program
        return geometry_art(self, game, PAIRS[game], mid, feature, palette, color_map,
                            ground=ground, source_animation=animation)

    def shore(self, game, mid):
        pair = PAIRS[game]
        path = self.cache / game / 'data/generated/gba/native' / pair
        bank = catalog.read_lua(path / 'anim_manifest.lua')['water']
        assert mid in bank['mids']
        raw = (path / 'anim_water.rgba').read_bytes()
        size = 8 * len(bank['mids']) * 1024
        if len(raw) != size:
            raw = zlib.decompress(raw)
        assert len(raw) == size
        animation = dict(mode='water_mask', bank='water', hash=catalog.sha(raw))
        _, changed, _ = source_under_frames(self.cache, game, pair, mid, self.packed, animation)
        if not changed:
            animation['mode'] = 'static_equivalent'
        sea = self.source_colors(game, (299, 300, 473))
        return self.shape(game, mid, 'celadon_exact_water_and_stone_boundary', ARCH_PALETTE,
                          self.water, sea, animation)

    def recipe(self, item, grass):
        game, mid = item['game'], item['mid']
        if 'alias' in item:
            return self.exact_alias(item), 'Whole native Crystal cell with the same source pixel art, layers, behavior and visible role.'
        if mid in SHORE:
            return self.shore(game, mid), ('The native Crystal wave animation shows around the original bank or boulder. '
                                           'The exact source shoreline, collision and water phase mask stay aligned.')
        if mid == 733:
            art = self.native(self.water, 'reverse_gen2_celadon_complete_pond_water')
            art.update(animated=True, animation=self.water_program, animationCategory='water')
            return art, 'Complete original Crystal wave cell continues the pond water to its southern edge.'
        if mid in {715, 716}:
            pond_colors = self.source_colors(game, (733,))
            return self.shape(game, mid, 'celadon_handed_pond_corner', ARCH_PALETTE, self.water, pond_colors), (
                'The complete southern pond corner keeps its original shore silhouette over the surrounding Crystal waves.')
        if mid in ROOF_FILL:
            donor = self.gb_at('crystal', 'CELADON_CITY', *ROOF_FILL[mid])
            parts = [dict(donor=donor, srcX=0, srcY=8, x=0, y=y, w=16, h=8) for y in (0, 8)]
            return self.composite(self.ground, parts, 'reverse_gen2_celadon_continuous_roof_fill'), (
                'Whole eight-pixel native roofing and outside edge continue this taller roof. The outer roof '
                'border and eave each appear only once in the joined source building.')
        for modules, name, feature in ((STORE, 'CELADON_CITY', 'department_store'),
                                       (TOWNHOUSES, 'CELADON_CITY', 'townhouse'),
                                       (ARCADE, 'CELADON_CITY', 'game_corner'),
                                       (HOUSE, 'CELADON_CITY', 'cycling_road_house')):
            if mid in modules:
                return self.native(self.gb_at('crystal', name, *modules[mid]), 'reverse_gen2_celadon_native_' + feature), (
                    'A complete original Crystal building module preserves the joined roof, windows, door placement '
                    'and exterior frame at native scale.')
        if mid in GATES:
            position = {84: (10, 6), 85: (11, 6), 86: (13, 6), 93: (11, 7), 103: (12, 6)}[mid]
            return self.native(self.gb_at('crystal', 'ROUTE_16', *position), 'reverse_gen2_celadon_native_route_gate'), (
                'An intact Crystal gate facade panel continues the adjacent verified gate modules.')
        if mid in {807, 853}:
            return self.native(self.sign, 'reverse_gen2_celadon_native_outdoor_sign'), 'Complete original Crystal sign at the source sign position.'
        if mid in GRASS | PATH | WALKWAYS:
            return self.native(self.ground, 'reverse_gen2_celadon_native_pale_ground'), (
                'Complete original Crystal pale route ground joins the surrounding pavement.')
        if mid in FOUNTAIN:
            feature, palette = 'celadon_joined_city_fountain', BLUE_PALETTE
        elif mid in TRACK:
            feature, palette = 'cycling_road_complete_jump_marker', RAIL_PALETTE
        elif mid in CURB:
            feature, palette = 'cycling_road_handed_fence_and_curb', STONE_PALETTE
        elif mid in STEEP:
            feature, palette = 'celadon_handed_stone_ledge', ARCH_PALETTE
        else:
            assert mid in {379, 380, 381, 382, 383}, mid
            return self.native(self.ground, 'reverse_gen2_celadon_center_clear_retired_roof'), (
                'The complete native Crystal Pokemon Center roof already occupies the row below. '
                'The retired upper Gen 3 roof strip uses the surrounding ground.')
        return self.shape(game, mid, feature, palette, self.ground, grass), (
            'The whole named source structure keeps its outline, handed joins and priority in the Crystal material. '
            'Exact outside pixels show the selected surrounding ground.')

    def build(self):
        for game in GAMES:
            grass = self.source_colors(game, (1, 8, 9, 16, 17, 220, 366))
            for item in self.guards:
                if item['game'] != game:
                    continue
                pair, mid = item['pair'], item['mid']
                assert pair == PAIRS[game] and (game, pair, mid) not in self.sources
                source = self.imp.cell_index(game)[pair, mid]
                assert (source['pixel_sha256'], source['layer_sha256'], source['behavior']) == (
                    item['sourceHash'], item['sourceLayers'], item['sourceBehavior'])
                for use in item['contexts']:
                    layout = self.native_layout(game, use['map'])
                    assert layout['pair'] == pair and layout['mids'].count(mid) == use['cells']
                art, evidence = self.recipe(item, grass)
                if art['kind'] != 'classic_native_geometry' and 'overMask' not in art:
                    over = self.planes(game, mid).get('over')
                    if over and over.getbbox():
                        output = self.render(art)
                        art['overMask'] = ''.join('1' if p[3] and q != (222, 255, 222, 255) else '0'
                                                  for p, q in zip(over.get_flattened_data(), output.get_flattened_data()))
                    else:
                        art['overMask'] = '0' * 256
                row = self.row(game, pair, mid, 'gen2', art, evidence)
                if 'alias' in item:
                    assert row['compositionPixelHash'] == item['alias']['output']
        assert Counter(game for game, _, _, _, _ in self.rows) == Counter({game: 290 for game in GAMES})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    review = Review()
    review.build()
    proof = review.validate()
    review.write(OUTPUT / 'candidate.lua')
    if args.activate:
        review.write(TARGET)
    print(json.dumps(dict(rows=len(review.rows), cells=sum(item['cells'] for item in review.guards),
                          proof=proof, activated=args.activate)))


if __name__ == '__main__':
    main()
