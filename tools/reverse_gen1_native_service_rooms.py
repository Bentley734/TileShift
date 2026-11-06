"""Build original Red room materials and complete fixtures for native GBA service rooms."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
import struct
import zlib

import catalog
from coverage import active_rows
import preview
from reverse_common import ROOT, ReverseReview


HOENN = ('ruby', 'sapphire', 'emerald')
KANTO = ('firered', 'leafgreen')
GAMES = KANTO + HOENN
MARTS = {'firered': 'building__rom_082d4bcc', 'leafgreen': 'building__rom_082d4bac'}
TARGET = ROOT / 'mappings/reverse_gen1_native_service_rooms.lua'
GUARDS = ROOT / 'tools/reverse_gen1_native_service_rooms_guards.json'

CLINIC_FLOOR = {
    'reverse_gen2_hoenn_public_clinic_floor', 'reverse_gen2_hoenn_clinic_plain_shared_floor',
    'reverse_gen2_clinic_full_floor_variation', 'reverse_gen2_clinic_staff_floor',
    'classic_crystal_center_plain_floor', 'classic_gen2_complete_ordinary_clinic_floor_and_light_patch',
    'classic_gen2_complete_clinic_staff_floor', 'classic_gen2_complete_ordinary_clinic_staff_floor_shadow',
}
MART_FLOOR = {
    'classic_crystal_mart_plain_floor', 'kanto_mart_native_regular_walkway',
    'reverse_gen2_hoenn_shop_floor', 'reverse_gen2_hoenn_mart_patterned_tiles',
}
CLINIC_WALL = {
    'reverse_gen2_complete_clinic_wall', 'classic_gen2_complete_ordinary_clinic_back_wall',
    'classic_gen2_indigo_native_back_wall',
}
BLACK_ROLES = {'classic_gen2_exact_native_black_canvas', 'reverse_gen2_exact_black_canvas'}


def eligible_pairs(game):
    if game in HOENN:
        return {'building__pokemon_center', 'building__shop'}
    return {'network', MARTS[game]}


def read_layout(path):
    data = path.read_bytes()
    blob = data if data[:4] == b'SVML' else zlib.decompress(data)
    assert blob[:4] == b'SVML'
    stride, height, logical_width, logical_height = struct.unpack_from('<HHHH', blob, 6)
    border_count = blob[14] * blob[15]
    offset = 16 + border_count * 2
    width, lines = logical_width or stride, logical_height or height
    mids = [struct.unpack_from('<H', blob, offset + (y * stride + x) * 4)[0]
            for y in range(lines) for x in range(width)]
    return width, lines, mids, catalog.sha(data)


class Review(ReverseReview):
    def __init__(self):
        super().__init__('gen1-service-rooms', GAMES)
        self.maps = defaultdict(list)
        self.uses = defaultdict(Counter)
        for game in GAMES:
            native = self.cache / game / 'data/generated/gba/native'
            layouts = catalog.read_lua(native / 'manifest.lua')['layouts']
            for name, spec in sorted(layouts.items()):
                pair = spec['pair']
                if pair not in eligible_pairs(game):
                    continue
                width, height, mids, digest = read_layout(native / spec['file'])
                self.maps[game, pair].append((name, width, height, mids, digest))
                for mid, count in Counter(mids).items():
                    self.uses[game, pair, mid][name] = count
        self.floor = self.gb_at('red', 'VIRIDIAN_POKECENTER', 2, 4)
        self.black = self.gb_ref('red', 'VIRIDIAN_POKECENTER', 0, 0)
        self.wall = self.gb_at('red', 'VIRIDIAN_POKECENTER', 8, 0)
        assert catalog.sha(self.gb_image(self.floor).tobytes()) == '322f3949d4499dfb32de284e189bd18d8c700a72e29a601392356e48ff9c002c'
        assert self.gb_image(self.floor).tobytes() == self.gb_image(self.gb_at('red', 'VIRIDIAN_MART', 2, 2)).tobytes()
        assert self.gb_image(self.black).getcolors() == [(256, (0, 0, 0, 255))]

    def source(self, game, pair, mid):
        source = self.imp.cell_index(game)[pair, mid]
        preview.native_donor(self.cache, dict(game=game, tileset=pair, id=mid, hash=source['pixel_sha256']), self.packed)
        mids, _, layers = self.packed[game, pair]
        slot = mids.index(mid) * 256
        over = layers.get('over', b'')[slot:slot + 256] or bytes(256)
        return source, ''.join('1' if v else '0' for v in over)

    def surface(self, pair, mid, counterpart):
        if counterpart['kind'] != 'native':
            return None
        role = counterpart['role']
        clinic = pair in ('network', 'building__pokemon_center')
        if role in BLACK_ROLES:
            return self.black, 'blank_map_canvas', 'The original black exterior stays solid black using the exact Red room void module.'
        if clinic and role in CLINIC_WALL:
            return self.wall, 'plain_clinic_wall', 'Complete Red clinic wall bands replace only ordinary undecorated back-wall modules.'
        if clinic and role in CLINIC_FLOOR:
            return self.floor, 'clinic_floor', 'Complete native Red diamond floor replaces the verified ordinary clinic walking surface.'
        if not clinic and role in MART_FLOOR:
            if pair == 'building__shop' and mid not in {513,514,515,516,518,520,522,523,527}:
                return None
            return self.floor, 'mart_floor', 'Complete native Red diamond floor replaces the verified ordinary Poke Mart walking surface.'
        return None

    def complete_family(self, game, pair, shape, clipped_right=False):
        wanted = {mid for row in shape for mid in row}
        covered = Counter()
        for name, width, height, mids, _ in self.maps[game, pair]:
            for i, mid in enumerate(mids):
                if mid not in wanted:
                    continue
                x, y = i % width, i // width
                actual = False
                for dy, row in enumerate(shape):
                    for dx, label in enumerate(row):
                        if mid != label:
                            continue
                        ox, oy = x - dx, y - dy
                        if not (0 <= ox < width and 0 <= oy <= height - len(shape)):
                            continue
                        visible = min(len(row), width - ox)
                        if visible != len(row) and not clipped_right:
                            continue
                        actual |= all(mids[(oy + sy) * width + ox:(oy + sy) * width + ox + visible] == list(source[:visible])
                                      for sy, source in enumerate(shape))
                if not actual:
                    return False, (game, pair, name, mid, x, y)
                covered[mid] += 1
        return wanted == covered.keys(), dict(covered)

    def shelf(self, rows, column, row):
        # The Red 32px fixture is two complete native modules. Extra source
        # height is filled with a complete internal 16px band of ordinary shelves.
        donor_rows = [0] + [8] * (rows - 2) + [16]
        sy = 48 + donor_rows[row]
        pieces = self.gb_rect('red', 'VIRIDIAN_MART', 64 + column * 16, sy, 16, 16)
        return self.composite(None, pieces, 'native_red_complete_mart_stock_aisle')

    def objects(self):
        for game in GAMES:
            if game in HOENN:
                yield game, 'building__pokemon_center', ((515,516),), False, 'entry', 'complete clinic entry mat'
                yield game, 'building__pokemon_center', ((546,547),(554,555)), False, 'healer', 'complete clinic healing machine'
                yield game, 'building__pokemon_center', ((606,),(614,)), False, 'plant', 'complete clinic potted plant'
                yield game, 'building__shop', ((549,),(557,)), False, 'plant', 'complete Mart potted plant'
                yield game, 'building__shop', ((555,556),(563,564),(571,572)), True, 'shelf', 'complete Mart aisle stock shelves'
            else:
                yield game, 'network', ((682,683),(690,691)), False, 'healer', 'complete clinic healing machine'
                yield game, MARTS[game], ((662,663),(670,671),(678,679),(686,687)), True, 'shelf', 'complete Mart aisle stock shelves'

    def object_recipe(self, feature, rows, x, y):
        if feature == 'entry':
            return self.native(self.gb_at('red', 'VIRIDIAN_POKECENTER', 3 + x, 7), 'native_red_complete_clinic_entry_mat')
        if feature == 'healer':
            return self.native(self.gb_at('red', 'VIRIDIAN_POKECENTER', 1 + x, y), 'native_red_complete_clinic_healing_machine')
        if feature == 'plant':
            return self.native(self.gb_at('red', 'VIRIDIAN_POKECENTER', 0, 6 + y), 'native_red_complete_service_room_potted_plant')
        assert feature == 'shelf'
        return self.shelf(rows, x, y)


def freeze(review, baseline):
    _, all_rows = active_rows(baseline)
    active = {(r['game'], r['style'], r['tileset'], r['id']): r for r in all_rows if r['game'] in GAMES and not r.get('map')}
    written, withheld = {}, []

    def save(game, pair, mid, recipe, explanation):
        key = game, 'gen1', pair, mid
        assert key not in active and key not in written, key
        source, over = review.source(game, pair, mid)
        assert review.uses[game, pair, mid]
        prior = active[game, 'gen2', pair, mid]
        assert prior['sourceHash'] == source['pixel_sha256'] and prior.get('sourceBehavior') == source.get('behavior')
        recipe = dict(recipe, overMask=over)
        row = review.row(game, pair, mid, 'gen1', recipe, explanation)
        written[key] = dict(game=game, pair=pair, mid=mid, sourceHash=source['pixel_sha256'],
                            sourceBehavior=source.get('behavior'), sourceLayers=source['layer_sha256'],
                            counterpartRole=prior['role'], counterpartHash=prior['compositionPixelHash'],
                            maps=dict(sorted(review.uses[game, pair, mid].items())), recipe=recipe,
                            review=explanation, expectedOutputHash=row['compositionPixelHash'])

    for game, pair, mid in sorted(review.uses):
        if (game, 'gen1', pair, mid) in active:
            continue
        counterpart = active.get((game, 'gen2', pair, mid))
        if not counterpart:
            continue
        item = review.surface(pair, mid, counterpart)
        if item:
            donor, role, evidence = item
            save(game, pair, mid, review.native(donor, 'native_red_' + role), evidence)

    for game, pair, shape, clip, feature, label in review.objects():
        complete, proof = review.complete_family(game, pair, shape, clip)
        if not complete:
            withheld.append(dict(game=game, pair=pair, family=label, context=proof))
            continue
        for y, source in enumerate(shape):
            for x, mid in enumerate(source):
                evidence = ('The ' + label + ' uses its complete original Red counterpart at native scale. '
                            'The exact source footprint, anchor and priority are verified at every occupied layout cell.')
                if feature == 'shelf':
                    evidence += ' Only the complete ordinary middle shelf bands repeat within the existing rack height.'
                save(game, pair, mid, review.object_recipe(feature, len(shape), x, y), evidence)
    records = [written[k] for k in sorted(written)]
    assert records
    hashes = {f'{game}/{name}': digest for game, pair in review.maps
              for name, _, _, _, digest in review.maps[game, pair]
              if any(name in row['maps'] and (game,pair)==(row['game'],row['pair']) for row in records)}
    document = dict(format=1, baselineMainHash=catalog.sha((baseline/'main.lua').read_bytes()),
                    layoutHashes=hashes, withheld=withheld, sources=records)
    GUARDS.write_text(json.dumps(document, indent=2, sort_keys=True) + '\n')


def build(review):
    doc = json.loads(GUARDS.read_text())
    assert doc['format'] == 1
    loaded_layouts = {f'{game}/{name}': digest for game, pair in review.maps
                      for name, _, _, _, digest in review.maps[game, pair]}
    assert all(loaded_layouts[k] == v for k, v in doc['layoutHashes'].items())
    for saved in doc['sources']:
        game, pair, mid = saved['game'], saved['pair'], saved['mid']
        source, over = review.source(game, pair, mid)
        assert (source['pixel_sha256'], source.get('behavior'), source['layer_sha256']) == (
            saved['sourceHash'], saved['sourceBehavior'], saved['sourceLayers'])
        assert review.uses[game, pair, mid] == saved['maps'] and saved['recipe']['overMask'] == over
        row = review.row(game, pair, mid, 'gen1', saved['recipe'], saved['review'])
        assert row['compositionPixelHash'] == saved['expectedOutputHash'], (game, pair, mid)
    assert len(review.rows) == len(doc['sources'])
    return doc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze', type=Path, metavar='BASELINE_MOD')
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    review = Review()
    if args.freeze:
        freeze(review, args.freeze)
        review.rows = {}
    doc = build(review)
    proof = review.validate()
    assert proof['accepted']['gen1'] == len(review.rows) and not proof['rejected'], proof
    candidate = review.out / TARGET.name
    review.write(candidate)
    if args.activate:
        TARGET.write_bytes(candidate.read_bytes())
    keys = [{k: r[k] for k in ('game','pair','mid')} for r in doc['sources']]
    (review.out/'keys.json').write_text(json.dumps(keys, indent=2) + '\n')
    result = dict(new_keys=len(keys), body_cells=sum(sum(r['maps'].values()) for r in doc['sources']),
                  maps=len(doc['layoutHashes']), sha256=catalog.sha(candidate.read_bytes()),
                  proof=proof, withheld=doc['withheld'])
    (review.out/'report.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
