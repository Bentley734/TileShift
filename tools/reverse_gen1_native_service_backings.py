"""Match explicit clinic and Mart backing masks to the selected original Red floor."""

from __future__ import annotations

import argparse
import copy
import json
from collections import defaultdict
from pathlib import Path

from PIL import Image

import catalog
from coverage import active_rows
from reverse_gen1_native_service_rooms import GAMES, GUARDS as NATIVE_GUARDS, ROOT, Review as Rooms


TARGET = ROOT / 'mappings/reverse_gen1_native_service_backings.lua'
GUARDS = ROOT / 'tools/reverse_gen1_native_service_backings_guards.json'
SHADES = ((0, 0, 0), (85, 85, 85), (170, 170, 170), (255, 255, 255))
FLOOR_ROLES = {'native_red_clinic_floor', 'native_red_mart_floor'}


def shade(rgb):
    """The same four cutoffs as lib/monochrome.lua on integer RGB8."""
    r, g, b = rgb
    light = 54 * r + 183 * g + 19 * b
    return SHADES[sum(light >= 256 * cutoff for cutoff in (80, 145, 210))]


class Review(Rooms):
    def __init__(self):
        super().__init__()
        self.out = ROOT.parent / '.work/tileshift-reverse-gen1-service-backings'
        self.out.mkdir(exist_ok=True)

    def source_planes(self, row):
        game, pair, mid = row['game'], row['tileset'], row['id']
        source, _ = self.source(game, pair, mid)
        assert source['pixel_sha256'] == row['sourceHash']
        mids, palette, native = self.packed[game, pair]
        start = mids.index(mid) * 256
        original = {name: catalog.rgba_native(raw[start:start + 256], palette, name != 'under')
                    for name, raw in native.items()}
        original.setdefault('over', Image.new('RGBA', (16, 16)))
        spec = row['classicGeometry']
        assert spec['sourceLayers'] == {name: catalog.sha(image.tobytes()) for name, image in original.items()}
        manifest = self.cache / game / 'data/generated/gba/native' / pair / 'anim_manifest.lua'
        assert catalog.sha(manifest.read_bytes() if manifest.is_file() else b'') == spec['animationManifestHash']
        return original

    def layers(self, row):
        spec = row['classicGeometry']
        original = self.source_planes(row)
        literal = {tuple(entry[:3]): tuple(entry[3:]) for entry in spec['colorMap']}
        ground = spec['ground']
        donor = self.gb_image(ground['donor']).get_flattened_data()
        output = {}
        for name, image in original.items():
            mask = ground['masks'].get(name, '0' * 256)
            assert len(mask) == 256 and set(mask) <= {'0','1'}
            pixels = []
            for i, pixel in enumerate(image.get_flattened_data()):
                if mask[i] == '1':
                    assert pixel[3] == donor[i][3] == 255
                    pixels.append(donor[i])
                else:
                    pixels.append(literal[pixel[:3]] + (255,) if pixel[3] else pixel)
            layer = Image.new('RGBA', (16, 16))
            layer.putdata(pixels)
            assert image.getchannel('A').tobytes() == layer.getchannel('A').tobytes()
            output[name] = layer
        return output

    def render(self, row):
        if row.get('style') != 'gen1' or row['kind'] != 'classic_native_geometry':
            return super().render(row)
        layers = self.layers(row)
        result = Image.new('RGBA', (16, 16))
        for name in ('under', 'mid', 'over'):
            if name in layers:
                result.alpha_composite(layers[name])
        return result


def active_index(baseline):
    _, rows = active_rows(baseline)
    return {(r['game'], r['style'], r['tileset'], r['id']): r for r in rows
            if r['game'] in GAMES and not r.get('map')}


def floor_witnesses(review, native, active):
    floors = defaultdict(lambda: defaultdict(list))
    for row in native:
        if row['recipe']['role'] not in FLOOR_ROLES:
            continue
        game, pair, mid = row['game'], row['pair'], row['mid']
        counterpart = active[game, 'gen2', pair, mid]
        assert counterpart['kind'] == 'native' and counterpart['role'] == row['counterpartRole']
        assert counterpart['compositionPixelHash'] == row['counterpartHash']
        donor = counterpart['donor']
        digest = catalog.sha(review.gb_image(donor).tobytes())
        assert digest == counterpart['compositionPixelHash']
        floors[game, pair][digest].append(mid)
    return floors


def freeze(review, baseline):
    active = active_index(baseline)
    native = json.loads(NATIVE_GUARDS.read_text())['sources']
    floors = floor_witnesses(review, native, active)
    native_keys = {(r['game'], r['pair'], r['mid']) for r in native}
    rows, composites = [], []
    for game, pair, mid in sorted(review.uses):
        key = game, pair, mid
        if key in native_keys or (game,'gen1',pair,mid) in active:
            continue
        old = active.get((game,'gen2',pair,mid))
        if not old:
            continue
        prior = old.get('classicGeometry', {})
        ground = prior.get('ground')
        donor = ground['donor'] if ground else old.get('base')
        if not donor or donor['game'] != 'crystal':
            continue
        digest = catalog.sha(review.gb_image(donor).tobytes())
        matched = floors[game,pair].get(digest)
        if not matched:
            continue
        if old['kind'] == 'native_composite':
            composites.append(dict(game=game, pair=pair, mid=mid, role=old['role'], floor_mids=sorted(matched),
                                   maps=dict(sorted(review.uses[key].items())), reason='Part-embedded floor pixels need an exact whole-fixture check.'))
            continue
        assert old['kind'] == 'classic_native_geometry' and ground and prior['static'] is True
        if prior.get('nativeOver') or prior.get('sourceAnimation') or ground.get('animation'):
            continue
        assert set(ground) == {'donor','masks'}
        spec = copy.deepcopy(prior)
        spec['ground']['donor'] = copy.deepcopy(review.floor)
        spec['palette'] = [list(rgb) for rgb in SHADES]
        spec['colorMap'] = [entry[:3] + list(shade(entry[3:])) for entry in prior['colorMap']]
        recipe = dict(kind='classic_native_geometry', role='native_red_exact_service_fixture_floor_backing', classicGeometry=spec)
        evidence = ('Every original fixture pixel follows the four neutral shades of the verified counterpart. '
                    'The exact reviewed open-floor mask uses the same complete original Red floor as neighboring cells. '
                    'The original shape, alpha, priority and room placement are preserved.')
        row = review.row(game,pair,mid,'gen1',recipe,evidence)
        source, _ = review.source(game,pair,mid)
        assert row['sourceHash'] == old['sourceHash'] and row.get('sourceBehavior') == old.get('sourceBehavior')
        old_layers = review.layers(old)
        new_layers = review.layers(row)
        red_pixels = review.gb_image(review.floor).get_flattened_data()
        mask_pixels = 0
        for name, image in old_layers.items():
            mask = ground['masks'].get(name, '0'*256)
            observed = new_layers[name].get_flattened_data()
            for i, pixel in enumerate(image.get_flattened_data()):
                expected = red_pixels[i] if mask[i] == '1' else shade(pixel[:3]) + (255,) if pixel[3] else pixel
                assert observed[i] == expected, (key,name,i)
            mask_pixels += mask.count('1')
        rows.append(dict(game=game,pair=pair,mid=mid,sourceHash=row['sourceHash'],sourceBehavior=row.get('sourceBehavior'),
                         sourceLayers=source['layer_sha256'],maps=dict(sorted(review.uses[key].items())),recipe=recipe,
                         review=evidence,priorRole=old['role'],priorHash=old['compositionPixelHash'],
                         priorFloorHash=digest,matchedOpenFloorMids=sorted(matched),checkedBackingPixels=mask_pixels,
                         expectedOutputHash=row['compositionPixelHash']))
    assert rows
    maps = {(r['game'], name) for r in rows for name in r['maps']}
    map_hashes = {f'{game}/{name}': digest for game,pair in review.maps
                  for name,_,_,_,digest in review.maps[game,pair] if (game,name) in maps}
    doc = dict(format=1, nativeFloorGuardHash=catalog.sha(NATIVE_GUARDS.read_bytes()),
               baselineMainHash=catalog.sha((baseline/'main.lua').read_bytes()),
               layoutHashes=map_hashes, sources=rows)
    GUARDS.write_text(json.dumps(doc, indent=2, sort_keys=True)+'\n')
    (review.out/'composite-followups.json').write_text(json.dumps(composites, indent=2, sort_keys=True)+'\n')


def build(review):
    doc = json.loads(GUARDS.read_text())
    assert doc['format'] == 1 and doc['nativeFloorGuardHash'] == catalog.sha(NATIVE_GUARDS.read_bytes())
    hashes = {f'{game}/{name}': digest for game,pair in review.maps for name,_,_,_,digest in review.maps[game,pair]}
    assert all(hashes[k] == v for k,v in doc['layoutHashes'].items())
    for saved in doc['sources']:
        game,pair,mid = saved['game'],saved['pair'],saved['mid']
        source,_ = review.source(game,pair,mid)
        assert (source['pixel_sha256'],source.get('behavior'),source['layer_sha256']) == (
            saved['sourceHash'],saved['sourceBehavior'],saved['sourceLayers'])
        assert review.uses[game,pair,mid] == saved['maps']
        art = saved['recipe']
        assert art['classicGeometry']['ground']['donor'] == review.floor and saved['matchedOpenFloorMids']
        row = review.row(game,pair,mid,'gen1',art,saved['review'])
        assert row['compositionPixelHash'] == saved['expectedOutputHash']
    assert len(review.rows) == len(doc['sources'])
    return doc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze', type=Path, metavar='BASELINE_MOD')
    parser.add_argument('--neutral', action='store_true', help='Run against the Gen1-capable native runtime')
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    review = Review()
    if args.freeze:
        freeze(review,args.freeze)
        review.rows = {}
    doc = build(review)
    proof = review.validate() if args.neutral else None
    if proof:
        assert proof['accepted']['gen1'] == len(review.rows) and not proof['rejected'], proof
    candidate = review.out/TARGET.name
    review.write(candidate)
    if args.activate:
        assert proof, 'Activation requires native neutral validation'
        TARGET.write_bytes(candidate.read_bytes())
    keys = [{k:r[k] for k in ('game','pair','mid')} for r in doc['sources']]
    (review.out/'keys.json').write_text(json.dumps(keys,indent=2)+'\n')
    report = dict(new_keys=len(keys),body_cells=sum(sum(r['maps'].values()) for r in doc['sources']),
                  maps=len(doc['layoutHashes']),sha256=catalog.sha(candidate.read_bytes()),neutral=proof,
                  independent_fixture_and_backing_pixels=sum(r['checkedBackingPixels'] for r in doc['sources']))
    (review.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
