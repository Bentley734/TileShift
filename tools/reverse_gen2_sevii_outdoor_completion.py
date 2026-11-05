"""Author exact native Crystal surfaces for the remaining FireRed/LeafGreen Sevii maps."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import zlib

from PIL import Image
import catalog
import preview
from classic_geometry_review import art as classic_art
from gb_theme_animation import specification
from reverse_gen2_hoenn_city_complete import Review as City
from reverse_gen2_kanto_final import Final, ROOT
from reverse_kanto_review import runs
from reverse_oldale_review import exterior, mask_piece

GUARD = Path(__file__).with_name('reverse_gen2_sevii_outdoor_guards.json')
TARGET = 'mappings/reverse_gen2_sevii_outdoor_completion.lua'
OUTPUT = ROOT.parent / '.work/tileshift-v0360-sevii-outdoors-completion'
PAIRS = {
    'firered': {'sevii_outdoor', 'general__rom_082d507c'},
    'leafgreen': {'sevii_outdoor', 'general__rom_082d505c'},
}
ANIMATED = {'water', 'foam', 'swash'}
GROUND_EVIDENCE = {
    'field': 'A complete original Crystal nonencounter lawn replaces the reviewed open field.',
    'sand': 'The whole native Crystal sandy walking surface replaces this reviewed open floor.',
    'field_sand': 'The complete native Crystal lawn and sandy path glyphs meet at the verified original boundary.',
    'sand_rock': 'The actual small rocky margin retains its exact outline over native Crystal sand.',
    'gray_geometry': 'The complete joined Mount Ember or Navel Rock volcanic cliff shape retains its original tiers and separate source planes in the surrounding native Crystal gold-stone palette. Native lawn or sand shows through the exact exterior mask.',
    'gray_boulder': 'The complete original Crystal round boulder keeps its clear corners and native size on the selected matching ground.',
    'gold_boulder': 'The complete original Crystal golden round boulder keeps its clear corners and native size on the selected matching ground.',
    'picket': 'Complete original upright Crystal wooden pickets retain their cap, shaft and foot. The verified source half-cell positions align with adjacent posts.',
    'ferry_deck': 'Complete original Crystal S.S. Aqua wooden planks retain the verified native ferry gangway axis.',
    'feature_geometry': 'The named complete regional feature retains its precise original outline, priority and visual anchors in the reviewed Crystal palette. Verified outside pixels expose the matching native terrain.',
    'building': 'The complete original Crystal modular house or Goldenrod Game Corner keeps its original doorway, whole window glyphs and straight roof lines at native pixel size.',
    'roof_backdrop': 'The verified original lawn, cliff or tree backdrop is exposed where the source roof cap formerly extended into the previous row. The new native roof begins as a complete straight line in its own row.',
    'roof_continuation': 'The complete plain roof panel continues the same gold roof as the adjoining cells. The independently checked lower roof trim runs straight over the entrance.',
    'stairs': 'A complete original Crystal north-south stone stair uses horizontal treads at the source ascent.',
}


def verify_shore_motion(review, item, cache):
    game, pair, mid = (item[k] for k in ('game', 'pair', 'mid'))
    if (game, pair) not in cache:
        directory = review.cache / game / 'data/generated/gba/native' / pair
        manifest = directory / 'anim_manifest.lua'
        cache[game, pair] = (catalog.sha(manifest.read_bytes()), catalog.read_lua(manifest), {})
    manifest_hash, manifest, banks = cache[game, pair]
    assert manifest_hash == item['animationManifestHash']
    names = {name for name in ('water', 'sand', 'flower') if mid in manifest.get(name, {}).get('mids', [])}
    assert names == {entry['name'] for entry in item['sourceMotion']}
    for entry in item['sourceMotion']:
        name = entry['name']
        assert name in ('water', 'sand')
        bank = manifest[name]
        assert bank['mids'].count(mid) == 1 and bank['frames'] == entry['frames'] == 8
        if name not in banks:
            directory = review.cache / game / 'data/generated/gba/native' / pair
            raw = (directory / f'anim_{name}.rgba').read_bytes()
            size = bank['frames'] * len(bank['mids']) * 1024
            if len(raw) != size:
                raw = zlib.decompress(raw)
            assert len(raw) == size
            banks[name] = (raw, catalog.sha(raw))
        raw, digest = banks[name]
        assert digest == entry['rawSHA256']
        slot = bank['mids'].index(mid)
        offsets = [(frame * len(bank['mids']) + slot) * 1024 for frame in range(8)]
        frames = [raw[i:i + 1024] for i in offsets]
        changed = [any(frame[i:i + 4] != frames[0][i:i + 4] for frame in frames[1:]) for i in range(0, 1024, 4)]
        assert sum(changed) == entry['changedPixels'] and len(set(frames)) == entry['distinct']
        assert ''.join('1' if bit else '0' for bit in changed) == entry['mask']
        solid = [mask for name, mask in item['masks'].items() if name not in ANIMATED]
        assert all(not varies or item['priority'][i] == '1' or all(mask[i] == '0' for mask in solid)
                   for i, varies in enumerate(changed))


def emit(review, guard=GUARD):
    contract = json.loads(guard.read_text())
    for join in contract['joins']:
        spec, layout = review.layouts[join['game'], join['map']]
        x, y, matrix = join['x'], join['y'], join['matrix']
        assert spec['pair'] == join['pair']
        actual = [layout['mids'][row * layout['width'] + x:row * layout['width'] + x + len(matrix[0])]
                  for row in range(y, y + len(matrix))]
        assert actual == matrix, ('Original Sevii joined feature changed', join['game'], join['map'])
    water = review.gb_ref('crystal', 'UNION_CAVE_1F', 15, 0)
    wave_program = specification(review.cache, water, 'program')
    assert wave_program

    def tint(ref, palette):
        result = copy.deepcopy(ref)
        result['palettes'] = [copy.deepcopy(palette) for _ in range(8)]
        return result

    rock = review.gb_ref('crystal', 'UNION_CAVE_1F', 6, 3)
    materials = dict(
        field=review.gb_ref('crystal', 'PALLET_TOWN', 1, 0),
        water=water,
        foam=tint(water, [[222,255,222],[181,197,255],[140,165,255],[82,107,206]]),
        swash=tint(water, [[222,255,222],[247,230,156],[181,197,255],[140,165,255]]),
        rock=rock,
        gray_rock=rock,
        sand=review.gb_ref('crystal', 'PALLET_TOWN', 121, 0),
        leaf=review.gb_ref('crystal', 'NATIONAL_PARK', 6, 0),
        plank=review.gb_at('crystal','FAST_SHIP_1F',16,6),
        stairs=review.gb_ref('crystal','UNION_CAVE_1F',18,3),
    )
    blank = review.gb_ref('crystal','UNION_CAVE_1F',0,0)
    roof_gold = tint(blank, [[197,148,58]]*4)
    roof_trim = tint(blank, [[247,82,49]]*4)
    golden_boulder = review.gb_ref('crystal', 'UNION_CAVE_1F', 24, 0)
    gray_boulder = tint(golden_boulder,
                   [[222,255,222],[173,173,173],[107,107,107],[58,58,58]])
    left = (6,4,3,2,1,1,1,0,0,0,0,0,0,1,1,2)
    right = (11,12,13,14,15,15,16,16,16,16,16,16,16,16,15,13)
    boulder_mask = ''.join('1' if left[y] <= x < right[y] else '0' for y in range(16) for x in range(16))
    pickets = {row['id']:row for row in review.active if row['game']=='emerald' and row['style']=='gen2'
               and row['tileset']=='general__mauville' and row['id']in (313,650,657)}
    assert set(pickets) == {313,650,657}
    assert all(row['role'].startswith('mauville_complete_native_crystal_upright_fence_') for row in pickets.values())

    def masked(ref, mask):
        return [dict(donor=ref, srcX=span['x'], srcY=span['y'], **span) for span in runs([bit == '1' for bit in mask])]

    def native_strip(art, top, height, dest=None):
        selected = []
        if dest is None:
            dest = top
        for piece in art['parts']:
            start = max(top, piece['y'])
            end = min(top + height, piece['y'] + piece['h'])
            if start < end:
                selected.append(dict(copy.deepcopy(piece), srcY=piece.get('srcY',0)+start-piece['y'],
                                     y=dest+start-top, h=end-start))
        return selected

    def home(palette_map):
        palette = preview.palette_set(review.imp.table('crystal','palettes'),
                                      review.imp.table('crystal','maps')[palette_map], 'DAY')[6]
        modules = City.town_model(review, 5, 2, 1, (3,), base=materials['field'], roof_palette=palette)
        compact = {(x,y):art for (x,y),art in modules.items() if y<2}
        for x in range(5):
            if x==1:
                compact[x,2] = modules[x,3]
            else:
                facade = native_strip(modules[x,2],8 if x==3 else 0,8,0) + native_strip(modules[x,3],8,8)
                compact[x,2] = review.composite(materials['field'],facade,'complete_compact_crystal_facade')
        return compact

    def joyful_corner():
        facade = {}
        whole = Image.new('RGBA',(80,64))
        plain = review.gb_rect('crystal','GOLDENROD_CITY',224,320,16,16)
        for y in range(4):
            for x in range(5):
                if y < 2:
                    sx = 0 if x == 0 else 80 if x == 4 else 16
                    parts = review.gb_rect('crystal','GOLDENROD_CITY',192+sx,288+y*16,16,16)
                elif y == 2:
                    parts = copy.deepcopy(plain)
                    if x in (0,4):
                        parts += review.gb_rect('crystal','GOLDENROD_CITY',192 if x==0 else 280,320,8,16,0 if x==0 else 8)
                    if x in (1,3):
                        parts += review.gb_rect('crystal','GOLDENROD_CITY',200,328,16,8,0,8)
                else:
                    sx = 0 if x==0 else 80 if x==4 else 32 if x==2 else 48
                    parts = review.gb_rect('crystal','GOLDENROD_CITY',192+sx,336,16,16)
                facade[x,y] = review.composite(None,parts,'complete_crystal_joyful_game_corner')
                whole.paste(review.render(facade[x,y]),(x*16,y*16))
        outside = exterior(whole,{(222,255,222,255)})
        for (x,y),art in list(facade.items()):
            mask = [(x*16+xx,y*16+yy)not in outside for yy in range(16)for xx in range(16)]
            facade[x,y] = mask_piece(review,art,mask,materials['field'],y<2)
        return facade

    models = {}
    if any(item['kind']=='building' for item in contract['cells']):
        violet = home('VIOLET_CITY')
        models = dict(common_house=violet,east_house=violet,red_house=home('ECRUTEAK_CITY'),joyful_corner=joyful_corner())

    def shore(item, role):
        masks = item['masks']
        if not masks:
            art = review.native(water, role)
        else:
            parts = [dict(donor=water, x=0, y=0, w=16, h=16, animated=True)]
            for name, mask in masks.items():
                spans = runs([bit == '1' for bit in mask])
                for span in spans:
                    part = dict(donor=materials[name], srcX=span['x'], srcY=span['y'], **span)
                    if name in ANIMATED:
                        part['animated'] = True
                    parts.append(part)
            assert 1 <= len(parts) <= 32
            art = review.composite(None, parts, role)
        art.update(animated=True, animation=wave_program, animationCategory='water', overMask=item['priority'])
        return art

    def static_ground(item, role):
        game, pair, mid = (item[key] for key in ('game','pair','mid'))
        kind = item['kind']
        if kind in ('field','sand'):
            art = review.native(materials[kind], role)
        elif kind == 'field_sand':
            art = review.composite(materials['field'], masked(materials['sand'], item['sandMask']), role)
        elif kind == 'sand_rock':
            art = review.composite(materials['sand'], masked(rock, item['rockMask']), role)
        elif kind in ('gray_boulder','gold_boulder'):
            boulder = gray_boulder if kind == 'gray_boulder' else golden_boulder
            art = review.composite(materials[item['base']], masked(boulder, boulder_mask), role)
        elif kind == 'ferry_deck':
            art = review.native(materials['plank'], role)
        elif kind == 'building':
            name,x,y = item['plan']
            art = copy.deepcopy(models[name][x,y])
            art['role'] = role
        elif kind == 'roof_backdrop':
            parts = [part for name,mask in item['masks'].items() for part in masked(materials[name],mask)]
            art = review.composite(materials['field'],parts,role) if parts else review.native(materials['field'],role)
        elif kind == 'roof_continuation':
            if 'roofWitness' in item:
                witness = item['roofWitness']
                source = review.imp.cell_index(game)[pair,witness['mid']]
                assert source['pixel_sha256']==witness['sourceHash'] and source['layer_sha256']==witness['sourceLayers']
            trim = masked(roof_trim,item['trim'])
            art = review.composite(roof_gold,trim,role) if trim else review.native(roof_gold,role)
            art['overMask'] = item['priority']
        elif kind == 'stairs':
            art = review.native(materials['stairs'],role)
        elif kind == 'picket':
            source = pickets[{(0,):313,(8,):650,(0,8):657}[tuple(item['columns'])]]
            art = json.loads(json.dumps(review.art_of(source), sort_keys=True))
            art['base'] = materials['field']
            art['role'] = role
            if '1' not in item['priority']:
                art['overMask'] = '0' * 256
        else:
            assert kind in ('gray_geometry', 'feature_geometry')
            mapping = {tuple(entry[:3]):tuple(entry[3:]) for entry in item['colorMap']}
            return classic_art(review, game, pair, mid, item['feature'], item['palette'], mapping, role,
                               ground=item['ground'], source_animation=item.get('sourceAnimation'))
        art.setdefault('overMask','0'*256)
        return art

    records = []
    cache = {}
    frame_proof = []
    native_frames = {name:preview.replacement_frames(review.cache, {
        'kind':'native','donor':materials[name],'animated':True,'animation':wave_program,
    },review.packed,ROOT)for name in ANIMATED}
    for item in contract['cells']:
        game, pair, mid = (item[k] for k in ('game', 'pair', 'mid'))
        assert pair in PAIRS[game]
        source = review.imp.cell_index(game)[pair, mid]
        assert source['pixel_sha256'] == item['sourceHash']
        assert source['behavior'] == item['sourceBehavior']
        assert source['layer_sha256'] == item['sourceLayers']
        assert (game, 'gen2', pair, mid, None) not in review.current
        feature = item.get('feature', item['kind'])
        role = f'reverse_gen2_sevii_{feature}_{mid}'
        actual_frames = None
        if item['kind'] == 'shore':
            verify_shore_motion(review, item, cache)
            art = shore(item, role)
            evidence = 'Complete original Crystal animated water meets the independently reviewed source coastline, surf and terrain silhouette. Only native selected water and swash move.'
            actual_frames = preview.replacement_frames(review.cache, art, review.packed, ROOT)
            assert len(actual_frames) == len(native_frames['water'])
            masks = item['masks']
            expected_static = {name:review.gb_image(materials[name]).get_flattened_data() for name in masks if name not in ANIMATED}
            for phase, frame in enumerate(actual_frames):
                expected = list(native_frames['water'][phase].get_flattened_data())
                for name, mask in masks.items():
                    donor_pixels = native_frames[name][phase].get_flattened_data() if name in ANIMATED else expected_static[name]
                    for index, bit in enumerate(mask):
                        if bit == '1':
                            expected[index] = donor_pixels[index]
                assert tuple(expected) == tuple(frame.get_flattened_data()), (game, pair, mid, phase)
        else:
            art = static_ground(item, role)
            evidence = GROUND_EVIDENCE[item['kind']]
            ground = item.get('ground')
            if ground and ground.get('animation'):
                source_animation = item.get('sourceAnimation')
                if source_animation:
                    evidence += ' The exact original legacy bank and opaque motion footprint are verified across all eight phases.'
        row = review.row(game, pair, mid, 'gen2', art, evidence +
                         ' Original collision, movement, heights, Surf, actors, events and entrances are preserved.')
        row['seviiOutdoorReview'] = dict(feature=feature, pixelScale=1)
        if 'animationManifestHash' in item:
            row['seviiOutdoorReview']['sourceAnimationManifest'] = item['animationManifestHash']
        if row.get('classicGeometry', {}).get('ground', {}).get('animation'):
            actual_frames = preview.classic_geometry_frames(review.cache, row, review.packed)
            assert len(actual_frames) == len(native_frames['water'])
            spec = row['classicGeometry']
            plan = spec['ground']
            mapping = {tuple(entry[:3]):tuple(entry[3:]) for entry in spec['colorMap']}
            refs = dict(game=game, tileset=pair, id=mid, hash=source['pixel_sha256'])
            source_layers = {name:preview.native_donor(review.cache, refs, review.packed, [name], {name:digest}).get_flattened_data()
                             for name,digest in spec['sourceLayers'].items()}
            ground_frames = preview.replacement_frames(review.cache, dict(kind='native', donor=plan['donor'],
                animated=True, animation=plan['animation']), review.packed, ROOT)
            for frame, backing in zip(actual_frames, ground_frames):
                expected = [None] * 256
                for name in ('under','mid','over'):
                    if name not in source_layers:
                        continue
                    mask = plan['masks'].get(name,'0'*256)
                    for index,pixel in enumerate(source_layers[name]):
                        if pixel[3]:
                            expected[index] = backing.getpixel((index % 16,index // 16)) if mask[index]=='1' else mapping[pixel[:3]]+(255,)
                assert tuple(expected) == tuple(frame.get_flattened_data()), (game,pair,mid,'legacy water composition')
        count = sum(u['count'] for u in review.usage[game, pair, mid])
        assert count > 0
        record = dict(game=game, pair=pair, mid=mid, sourceHash=row['sourceHash'], sourceBehavior=row['sourceBehavior'],
                      compositionPixelHash=row['compositionPixelHash'], occurrences=count)
        records.append(record)
        if actual_frames:
            frame_proof.append(dict(record, frames=[catalog.sha(frame.tobytes()) for frame in actual_frames]))
    return records, frame_proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--guard', type=Path, default=GUARD)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    review = Final()
    review.current = {key:row for key,row in review.current.items() if review.origins[id(row)][0]!=TARGET}
    review.out = args.output
    records, frames = emit(review, args.guard)
    review.write(args.output / 'candidate.lua')
    validation = review.validate()
    (args.output / 'new-keys.json').write_text(json.dumps(records, indent=2) + '\n')
    (args.output / 'frame-proof.json').write_text(json.dumps(frames, indent=2) + '\n')
    report = dict(rows=len(records), new_cells=sum(r['occurrences'] for r in records), validation=validation,
                  checked_frame_pixels=sum(len(record['frames']) * 256 for record in frames))
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
