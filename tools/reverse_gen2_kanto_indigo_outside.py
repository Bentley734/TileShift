"""Complete Route 23's gates and the Indigo Plateau exterior in Crystal style."""
from collections import Counter
from pathlib import Path
import argparse
import json
import zlib

import catalog
import preview
from classic_geometry_review import source_under_frames
from gb_theme_animation import specification
from reverse_common import ROOT, ReverseReview
from reverse_gen2_kanto_celadon import Review as Celadon, ARCH_PALETTE, STONE_PALETTE
from reverse_kanto_review import runs

GAMES = ('firered', 'leafgreen')
PAIRS = dict(firered='general__rom_082d4b84', leafgreen='general__rom_082d4b64')
OUTPUT = ROOT.parent / '.work/tileshift-v0360-indigo-outside'
TARGET = ROOT / 'mappings/reverse_gen2_kanto_indigo_outside.lua'
GUARDS = Path(__file__).with_name('reverse_gen2_kanto_indigo_outside_guards.json')

ROOF = {752: (2, 2), 753: (4, 2), 754: (7, 2), 760: (2, 2), 761: (4, 2),
        762: (7, 2), 768: (2, 3), 769: (4, 3), 770: (7, 3), 783: (4, 2)}
FRONT = {755: (3, 5), 756: (4, 5), 757: (5, 5), 776: (2, 5), 777: (4, 5), 778: (7, 5),
         779: (3, 5), 780: (4, 5), 781: (5, 5), 784: (2, 6), 785: (4, 6), 786: (7, 6),
         787: (3, 6), 788: (4, 6), 789: (5, 6), 792: (2, 8), 794: (7, 8), 795: (3, 8), 797: (5, 8)}
PLATEAU_TREES = {763, 764, 765, 771, 772, 773}
BOULDERS = {159, 710, 711, 744, 745, 746, 747}
STATUES = {663, 671, 694, 695, 728, 736, 751, 775, 796}
STAIRS = {712, 713, 714, 715, 716, 717, 718, 719, 721, 722, 723, 724, 725, 726, 727,
          729, 730, 731, 732, 737, 738}
CHECKPOINTS = {660, 661, 664, 665, 668, 669, 672, 673, 674, 704, 705, 706, 707}
CLIFFS = {739, 740, 748, 749, 750}
PLAZA = {648, 741, 742, 743}
FORECOURT = {758, 759, 766, 767, 774, 782}
FOLIAGE = [(58, 58, 58), (41, 115, 0), (99, 206, 8), (181, 255, 82)]
SHORE = {269, 656, 666, 667, 675, 677, 678, 686, 687, 790, 791, 798, 799, 800, 801,
         803, 804, 805, 806, 807, 808, 809, 810, 811, 812, 813, 814, 815}


class Review(Celadon):
    pairs = PAIRS

    def __init__(self):
        ReverseReview.__init__(self, 'gen2-kanto-indigo-outside', GAMES)
        self.out = OUTPUT
        self.layouts = {}
        self.layout_hashes = {}
        self.guards = json.loads(GUARDS.read_text(encoding='utf-8'))
        self.ground = self.gb_at('crystal', 'ROUTE_16', 6, 3)
        self.water = self.gb_ref('crystal', 'UNION_CAVE_1F', 15, 0)
        self.water_program = specification(self.cache, self.water, 'program')
        assert self.water_program
        self.boulder = self.gb_at('crystal', 'CELADON_CITY', 12, 16)
        self.sources = {}
        for name in {r['alias']['module'] for r in self.guards if 'alias' in r}:
            for row in preview.read_reviewed(ROOT / name):
                self.sources[row['game'], row['tileset'], row['id']] = row

    def shore(self, game, mid):
        pair = self.pairs[game]
        path = self.cache / game / 'data/generated/gba/native' / pair
        bank = catalog.read_lua(path / 'anim_manifest.lua')['water']
        assert mid in bank['mids']
        raw = (path / 'anim_water.rgba').read_bytes()
        length = 8 * len(bank['mids']) * 1024
        if len(raw) != length:
            raw = zlib.decompress(raw)
        assert len(raw) == length
        animation = dict(mode='water_mask', bank='water', hash=catalog.sha(raw))
        _, changed, _ = source_under_frames(self.cache, game, pair, mid, self.packed, animation)
        if not changed:
            animation['mode'] = 'static_equivalent'
        shallow = {(140, 165, 255), (107, 165, 230), (82, 156, 230)}
        water = self.source_colors(game, (299, 473)) | shallow
        return self.shape(game, mid, 'route23_handed_shore_or_checkpoint_arch', ARCH_PALETTE,
                          self.water, water, animation)

    def boulder_art(self):
        image = self.gb_image(self.boulder)
        pixels = list(image.get_flattened_data())
        mask = [p != (222, 255, 222, 255) for p in pixels]
        assert 48 <= sum(mask) < 256
        parts = [dict(donor=self.boulder, srcX=part['x'], srcY=part['y'], **part) for part in runs(mask)]
        return self.composite(self.ground, parts, 'reverse_gen2_indigo_complete_native_boulder')

    def recipe(self, item, grass):
        game, mid = item['game'], item['mid']
        if 'alias' in item:
            return self.exact_alias(item), 'Complete native Crystal counterpart with identical source artwork, behavior and layers.'
        if mid in SHORE:
            return self.shore(game, mid), (
                'Exact native wave masks keep the original water cadence around the complete shoreline or gate opening.')
        if mid in ROOF:
            ref = self.gb_at('crystal', 'CELADON_CITY', *ROOF[mid])
            if mid in {768, 769, 770}:
                art = self.native(ref, 'reverse_gen2_indigo_native_roof_eave')
            else:
                parts = [dict(donor=ref, srcX=0, srcY=8, x=0, y=y, w=16, h=8) for y in (0, 8)]
                art = self.composite(self.ground, parts, 'reverse_gen2_indigo_native_continuous_roof')
            return art, 'The complete native gray roof repeats its inner panels and keeps one continuous lower eave.'
        if mid in FRONT:
            donor = self.gb_at('crystal', 'CELADON_CITY', *FRONT[mid])
            return self.native(donor, 'reverse_gen2_indigo_native_league_facade'), (
                'The original Crystal castle facade uses whole windows and wall units around the source entrance.')
        if mid in BOULDERS:
            return self.boulder_art(), 'Whole native Crystal round rock with its original silhouette over the surrounding ground.'
        if mid in PLAZA:
            return self.native(self.ground, 'reverse_gen2_indigo_complete_native_plaza'), (
                'Complete pale Crystal plaza and route paving continues around the source entrances.')
        if mid in PLATEAU_TREES:
            feature, palette = 'indigo_joined_planted_shrub', FOLIAGE
        elif mid in FORECOURT:
            feature, palette = 'indigo_complete_curved_forecourt', STONE_PALETTE
        elif mid in STAIRS:
            feature, palette = 'indigo_complete_handed_stair_and_railing', STONE_PALETTE
        elif mid in STATUES:
            feature, palette = 'indigo_complete_ceremonial_statue', STONE_PALETTE
        elif mid in CLIFFS:
            feature, palette = 'route23_complete_handed_cliff_join', ARCH_PALETTE
        else:
            assert mid in CHECKPOINTS, mid
            feature, palette = 'route23_complete_checkpoint_wall_and_threshold', STONE_PALETTE
        return self.shape(game, mid, feature, palette, self.ground, grass), (
            'The whole named landmark section retains the original outline, orientation and priority. '
            'The exact exposed exterior joins the surrounding Crystal ground.')

    def build(self):
        for game in GAMES:
            grass = self.source_colors(game, (1, 8, 9, 16, 17))
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
                if art['kind'] != 'classic_native_geometry':
                    art.setdefault('overMask', '0' * 256)
                row = self.row(game, pair, mid, 'gen2', art, evidence)
                if 'alias' in item:
                    assert row['compositionPixelHash'] == item['alias']['output']
        assert Counter(game for game, _, _, _, _ in self.rows) == Counter({game: 133 for game in GAMES})


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
