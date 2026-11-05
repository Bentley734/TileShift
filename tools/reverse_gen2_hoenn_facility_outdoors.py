"""Review the Abandoned Ship deck and the remaining Mt. Pyre outdoor cells."""
from collections import Counter
from pathlib import Path
import argparse
import json
import zlib

import catalog
import preview
from classic_geometry_review import art as geometry_art
from gb_theme_animation import specification
from reverse_common import ROOT
from reverse_gen2_hoenn_outdoor_remaining import Review as Outdoor
from reverse_hoenn_review import ground_ref
from reverse_kanto_review import runs


PAIR = 'general__facility'
OUTPUT = ROOT.parent / '.work/tileshift-v0360-facility-outdoors'
TARGET = ROOT / 'mappings/reverse_gen2_hoenn_facility_outdoors.lua'
GUARDS = Path(__file__).with_name('reverse_gen2_hoenn_facility_outdoors_guards.json')
STAIRS = {718, 719, 808, 809, 816, 817}
GRASS = {815, 818, 823, 824, 825, 830, 831, 832}
WALLS = {826: 'e', 827: 'e', 828: 'e', 829: 'w'}
SKY_EDGES = {833, 834, 835}
ALTAR = {810, 811, 812, 813, 814}
HULL = {702, 703, 819, 820, 861, 947, 968, 969, 970, 971, 972, 973}
SUNLIT_GRASS = {(115, 197, 165), (165, 214, 197), (66, 181, 132)}
ALL_GRASS = SUNLIT_GRASS | {(25, 165, 107), (58, 140, 49)}
SHALLOW_WATER = {(156, 165, 189), (173, 197, 230), (107, 132, 214)}
DECK_COLORS = {(132, 148, 115), (173, 181, 148), (107, 123, 66), (222, 222, 197)}
SOURCE_SKY = (115, 189, 247, 255)


def luminance(rgb):
    r, g, b = rgb
    return (54 * r + 183 * g + 19 * b) / 256


class Review(Outdoor):
    def __init__(self):
        super().__init__(OUTPUT)
        self.field = ground_ref(self, 'gen2')
        self.stairs = self.gb_ref('crystal', 'UNION_CAVE_1F', 18, 3)
        self.deck = self.gb_ref('crystal', 'BATTLE_TOWER_1F', 1, 0)
        self.water = self.gb_ref('crystal', 'UNION_CAVE_1F', 15, 0)
        self.water_program = specification(self.cache, self.water, 'program')
        assert self.water_program
        self.sky = self.raw_ref('TILESET_JOHTO', (0,) * 4, 'VIOLET_CITY')
        self.sky['palettes'] = [[[189, 189, 255], [148, 156, 255], [107, 99, 255], [58, 58, 58]] for _ in range(8)]
        assert len(set(self.gb_image(self.sky).get_flattened_data())) == 1
        self.cap = self.raw_ref('TILESET_JOHTO', (60,) * 4, 'VIOLET_CITY')
        self.guards = json.loads(GUARDS.read_text(encoding='utf-8'))

    def native_parts(self, donor, mask):
        return [dict(donor=donor, srcX=rect['x'], srcY=rect['y'], **rect) for rect in runs(mask)]

    def grave(self, mid):
        ref = self.gb_at('crystal', 'SOUL_HOUSE', 0, 2)
        image = self.gb_image(ref)
        colors = sorted(set(image.get_flattened_data()))
        assert colors == [(58, 58, 58, 255), (132, 107, 25, 255), (173, 140, 58, 255), (214, 197, 140, 255)]
        bounds = [(4, 10), (3, 11), (2, 12), (2, 12), (2, 12), (2, 12), (0, 14)] + [(0, 12)] * 7 + [(0, 10)] * 2
        mask = [bounds[y][0] <= x < bounds[y][1] or image.getpixel((x, y)) in colors[:2]
                for y in range(16) for x in range(16)]
        if mid == 805:
            ref['palettes'] = [[[247, 247, 255], [156, 181, 206], [107, 132, 173], [58, 58, 58]] for _ in range(8)]
        return self.composite(self.field, self.native_parts(ref, mask), 'reverse_gen2_mt_pyre_soul_house_memorial')

    def shape(self, game, mid, planes, feature, palette, backing=None, exterior=(), ranks=None, animation=None):
        masks = {}
        colors = {}
        for name, plane in planes.items():
            pixels = list(plane.get_flattened_data())
            mask = ''.join('1' if p[3] and p[:3] in exterior else '0' for p in pixels)
            if '1' in mask:
                masks[name] = mask
            for p in pixels:
                if p[3]:
                    rank = sum(luminance(p[:3]) >= cut for cut in (85, 143, 202))
                    colors[p[:3]] = palette[(ranks or {}).get(p[:3], rank)]
        ground = dict(donor=backing, masks=masks) if masks else None
        if animation:
            assert ground and backing == self.water
            ground['animation'] = self.water_program
        return geometry_art(self, game, PAIR, mid, feature, palette, colors,
                            ground=ground, source_animation=animation)

    def water_edge(self, game, mid, planes, palette):
        directory = self.cache / game / 'data/generated/gba/native' / PAIR
        manifest = catalog.read_lua(directory / 'anim_manifest.lua')
        bank, = [b for b in manifest['banks'] if mid in b.get('mids', ())]
        assert bank['name'] == 'general_water' and bank['kind'] == 'tiles'
        path = directory / bank['file']
        assert path.parent == directory
        raw = path.read_bytes()
        length = bank['frames'] * len(bank['mids']) * 256
        if len(raw) != length:
            raw = zlib.decompress(raw)
        assert len(raw) == length
        animation = dict(mode='water_mask', bank=bank['name'], hash=catalog.sha(raw))
        return self.shape(game, mid, planes, 'abandoned_ship_post_in_surf', palette,
                          self.water, SHALLOW_WATER, animation=animation)

    def recipe(self, game, mid, source, planes):
        if mid == 161:
            assert set(source.get_flattened_data()) == {SOURCE_SKY}
            return self.native(self.sky, 'reverse_gen2_mt_pyre_native_open_sky'), (
                'The complete Crystal sky cell is used above the summit rock and in the matching native border. '
                'These cells are solid sky in the original and never belong to the ocean animation.')
        if mid in STAIRS:
            return self.native(self.stairs, 'reverse_gen2_facility_complete_north_south_stairs'), (
                'A complete north-south Crystal stone stair cell continues the joined source flight at its original width. '
                'It uses the same original treads as the stairs above and below this threshold.')
        if mid in (804, 805):
            return self.grave(mid), (
                'The complete original Crystal Soul House memorial sits over the same grass as its surroundings. '
                'Its plaque, pedestal and stippled shadow remain visible in the two source grave color variants.')
        if mid in SKY_EDGES:
            mask = [pixel != SOURCE_SKY for pixel in source.get_flattened_data()]
            assert 0 < sum(mask) < 256
            return self.composite(self.sky, self.native_parts(self.cap, mask), 'reverse_gen2_mt_pyre_rock_over_sky'), (
                'Original Crystal cliff cap artwork fills the exact mountain silhouette. The exposed corner pixels '
                'show the same solid native sky used by the summit backdrop.')
        if mid in WALLS:
            mask = [p[:3] not in ALL_GRASS for p in source.get_flattened_data()]
            assert 0 < sum(mask) < 256
            shape = WALLS[mid]
            return self.shape(game, mid, planes, 'mt_pyre_narrow_cliff_' + shape,
                              [(58, 58, 58), (165, 123, 25), (197, 148, 58), (222, 255, 222)],
                              self.field, ALL_GRASS), (
                'The narrow handed cliff retains its exact corridor outline in the surrounding original Crystal '
                'golden rock palette. Matching route grass occupies only the source grass pixels outside the cliff.')
        if mid in GRASS:
            return self.shape(game, mid, planes, 'mt_pyre_shaded_grass_join',
                              [(41, 115, 0), (66, 156, 0), (99, 206, 8), (181, 255, 82)],
                              self.field, SUNLIT_GRASS, {(58, 140, 49): 0, (25, 165, 107): 1}), (
                'Native Crystal grass joins the sunlit ground. The original shaded corridor and its handed '
                'entrance transitions retain their exact boundaries in the same grass colors.')
        if mid in ALTAR:
            return self.shape(game, mid, planes, 'mt_pyre_complete_summit_altar',
                              [(58, 58, 58), (107, 107, 107), (173, 173, 173), (222, 255, 222)],
                              self.field, ALL_GRASS), (
                'The complete Mt. Pyre altar keeps its circular plinths, individual stones and joined carved '
                'front. The original silhouette and all priority planes use the native Crystal stone palette.')
        assert mid in HULL
        palette = [(58, 58, 58), (74, 90, 123), (156, 181, 206), (247, 247, 255)]
        if mid == 820:
            art = self.water_edge(game, mid, planes, palette)
        elif mid in {702, 703, 819, 968}:
            art = self.shape(game, mid, planes, 'abandoned_ship_breach_and_deck_joints', palette,
                             self.deck, DECK_COLORS, {(58, 58, 58): 0, (132, 90, 49): 1, (197, 90, 66): 2})
        else:
            art = self.shape(game, mid, planes, 'abandoned_ship_joined_hull_and_portholes', palette,
                             ranks={(132, 148, 115): 2, (74, 181, 99): 1, (58, 132, 82): 0})
        return art, ('The original Abandoned Ship hull keeps its joined panels, complete portholes, rusted '
                     'deck holes and steel supports. The selected Crystal deck and animated water show through the '
                     'exact exterior masks, matching the neighboring floor and water.')

    def build(self):
        for item in self.guards:
            game, mid = item['game'], item['mid']
            c = self.imp.cell_index(game)[PAIR, mid]
            assert (c['pixel_sha256'], c['layer_sha256'], c['behavior']) == (
                item['sourceHash'], item['sourceLayers'], item['sourceBehavior'])
            prior = self.locations.get((game, 'gen2', PAIR, mid, None))
            if mid == 161:
                assert prior and prior[0] == item['supersedes']['module']
                assert catalog.sha(json.dumps(prior[2], sort_keys=True, separators=(',', ':')).encode()) == item['supersedes']['sha256']
                assert len(item['contexts']) == 1 and item['contexts'][0]['map'].endswith('_MT_PYRE_SUMMIT')
            else:
                assert prior is None
            for witness in item['contexts']:
                layout = self.native_layout(game, witness['map'])
                assert layout['pair'] == PAIR
                width = layout['width']
                coords = [(i % width, i // width) for i, value in enumerate(layout['mids']) if value == mid]
                assert coords == [tuple(p) for p in witness['coords']]
            source = preview.native_donor(self.cache, dict(game=game, tileset=PAIR, id=mid, hash=c['pixel_sha256']), self.packed)
            ids, native_palette, blobs = self.packed[game, PAIR]
            offset = ids.index(mid) * 256
            planes = {name: catalog.rgba_native(data[offset:offset + 256], native_palette, name != 'under')
                      for name, data in blobs.items()}
            art, evidence = self.recipe(game, mid, source, planes)
            if art['kind'] != 'classic_native_geometry':
                art['overMask'] = '0' * 256
            self.row(game, PAIR, mid, 'gen2', art, evidence)
        assert Counter(game for game, _, _, _, _ in self.rows) == Counter({game: 41 for game in self.games})


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
    body = sum(row['body_cells'] for row in review.guards if row['mid'] != 161)
    print(json.dumps(dict(rows=len(review.rows), new_body_cells=body, proof=proof, activated=args.activate)))


if __name__ == '__main__':
    main()
