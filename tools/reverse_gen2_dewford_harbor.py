"""Build guarded Crystal Dewford-area routes, island harbors and Petalburg edges."""
from __future__ import annotations

import copy
import json
from collections import Counter
from pathlib import Path

from classic_geometry_review import art as classic_art
from gb_theme_animation import specification
from johto_remaining_review import artwork
from reverse_gen2_hoenn_outdoor_finish import digest
from reverse_hoenn_review import ground_ref
from reverse_kanto_review import runs
from reverse_oldale_review import exterior

GUARD = Path(__file__).with_name('reverse_gen2_dewford_harbor_guards.json')
TRIANGLE_PRIOR = {464: 4, 466: 4, 472: 2, 473: 35, 474: 2, 481: 9}
EVIDENCE = {
    'alias': 'The named reviewed native counterpart has byte-identical source RGBA, all priority planes and behavior.',
    'cliff': 'The original Crystal rock module retains the independently reviewed handed cliff edge.',
    'deck': 'Complete original Crystal S.S. Aqua plank modules keep the gangway aligned in the source direction.',
    'geometry': 'The named complete regional feature retains its precise original contours, doorway, materials and priority layers in the reviewed four-color Crystal material. Explicit exterior masks reveal the matching native ground.',
    'sand_cliff': 'Complete Crystal beach and stone materials follow the verified shoreline and rock contours. Only original water remains visible outside both silhouettes.',
    'shrub': 'The complete original Crystal small tree keeps the original topiary footprint and matching native ground.',
    'sign': 'The intact original Crystal freestanding sign keeps the complete sign panel and original interaction anchor.',
    'surface': 'This verified open lawn, walking surface, rock face or water uses a complete matching native Crystal glyph.',
    'tower_native': 'This ordinary window or foundation module is an intact original Crystal Battle Tower facade cell at its original pixel scale.',
    'tree': 'The complete original Crystal tree crown retains its foreground priority and the verified surroundings remain visible outside its silhouette.',
    'wet_rock': 'The original Crystal rock material retains the actual handed shoreline silhouette and reveals animated native water at its outside corners.',
}


def emit(review, guard=GUARD):
    contract = json.loads(guard.read_text())
    for item in contract['joins']:
        source = review.native_layout(item['game'], item['map'])
        x, y, matrix = item['x'], item['y'], item['matrix']
        assert source['pair'] == item['pair']
        actual = [source['mids'][row * source['width'] + x:row * source['width'] + x + len(matrix[0])]
                  for row in range(y, y + len(matrix))]
        assert actual == matrix, ('Dewford area joined layout changed', item['game'], item['map'])
    revises_triangle = any(row.get('replacesExisting') for row in contract['cells'])
    if revises_triangle:
        for name in review.imp.table('emerald', 'gba/native/manifest')['layouts']:
            source = review.native_layout('emerald', name)
            if source['pair'] == 'general__dewford':
                actual = Counter(mid for mid in source['mids'] if mid in TRIANGLE_PRIOR)
                expected = TRIANGLE_PRIOR if name == 'EM_BIRTH_ISLAND_EXTERIOR' else {}
                assert actual == expected, ('Original Birth Island triangle scope changed', name, actual)

    field = ground_ref(review, 'gen2')
    sand = review.raw_ref('TILESET_KANTO', (48, 57, 57, 48), 'PALLET_TOWN')
    paving = review.raw_ref('TILESET_JOHTO', (6, 6, 6, 6), 'VIOLET_CITY')
    water = review.gb_ref('crystal', 'UNION_CAVE_1F', 15, 0)
    program = specification(review.cache, water, 'program')
    assert program
    cliff = review.gb_ref('crystal', 'UNION_CAVE_1F', 6, 3)
    terrace = review.gb_ref('crystal', 'UNION_CAVE_1F', 4, 3)
    deck = review.gb_at('crystal', 'FAST_SHIP_1F', 16, 6)
    terrain = dict(field=field, sand=sand, water=water, pavement=paving, rock_face=cliff, rock=terrace)
    sign = review.gb_at('crystal', 'PALLET_TOWN', 3, 5)
    sign_bg = review.gb_at('crystal', 'PALLET_TOWN', 3, 4)
    shrub = review.raw_ref('TILESET_JOHTO', (30, 31, 62, 63), 'NEW_BARK_TOWN')
    tree = review.active_art('emerald', 'general__dewford', 569)

    def masked(ref, mask):
        parts = [dict(donor=ref, srcX=p['x'], srcY=p['y'], **p) for p in runs([b == '1' for b in mask])]
        assert 1 <= len(parts) <= 32
        return parts

    def silhouette(ref, background):
        outside = exterior(review.gb_image(ref), set(review.gb_image(background).get_flattened_data()))
        return ''.join('0' if (x, y) in outside else '1' for y in range(16) for x in range(16))

    def animated(art):
        art.update(animated=True, animation=program, animationCategory='water')
        return art

    def with_water(parts, role):
        sea = dict(donor=water, x=0, y=0, w=16, h=16, animated=True)
        assert 1 + len(parts) <= 32
        return animated(review.composite(None, [sea, *parts], role))

    def exact_alias(source, plan):
        game, pair, mid = plan
        witness = review.imp.cell_index(game)[pair, mid]
        assert all(witness[k] == source[k] for k in ('pixel_sha256', 'behavior', 'layer_sha256'))
        generated = review.rows.get((game, 'gen2', pair, mid, None))
        if not generated:
            return review.active_art(game, pair, mid)
        art = artwork(generated)
        for name in ('overMask', 'animationCategory', 'assetPixelHash'):
            if name in generated:
                art[name] = copy.deepcopy(generated[name])
        return art

    records = []
    for item in contract['cells']:
        game, pair, mid = (item[k] for k in ('game', 'pair', 'mid'))
        source = review.imp.cell_index(game)[pair, mid]
        assert source['pixel_sha256'] == item['sourceHash']
        assert source['behavior'] == item['sourceBehavior']
        assert source['layer_sha256'] == item['sourceLayers']
        kind, plan = item['kind'], item.get('plan')
        role = f'reverse_gen2_hoenn_small_outdoor_{kind}_{mid}'
        if kind == 'alias':
            art = exact_alias(source, plan)
        elif kind == 'cliff':
            art = review.classic_cliff(*plan)
        elif kind == 'deck':
            art = review.native(deck, role)
        elif kind == 'sand_cliff':
            art = with_water(masked(sand, item['beachMask']) + masked(cliff, item['rockMask']), role)
        elif kind == 'shrub':
            art = review.composite(field, masked(shrub, silhouette(shrub, field)), role)
        elif kind == 'sign':
            art = review.composite(sand, masked(sign, silhouette(sign, sign_bg)), role)
        elif kind == 'surface':
            art = review.native(terrain[plan], role)
            if plan == 'water':
                animated(art)
        elif kind == 'tower_native':
            art = review.native(review.gb_at('crystal', 'BATTLE_TOWER_OUTSIDE', *plan), role)
        elif kind == 'tree':
            parts = copy.deepcopy(tree['parts'])
            art = with_water(parts, role) if plan == 'water' else review.composite(terrain[plan], parts, role)
            art['overMask'] = tree['overMask']
        elif kind == 'wet_rock':
            art = with_water(masked(review.gb_ref('crystal', 'UNION_CAVE_1F', *plan), item['mask']), role)
        else:
            assert kind == 'geometry'
            colors = {tuple(x[:3]): tuple(x[3:]) for x in item['colorMap']}
            art = classic_art(review, game, pair, mid, item['feature'], item['palette'], colors, role,
                              ground=item['ground'], source_animation=item.get('sourceAnimation'))
        art['role'] = role
        if kind != 'geometry':
            art.setdefault('overMask', '0' * 256)
        row = review.row(game, pair, mid, 'gen2', art, EVIDENCE[kind] +
                         ' Every source layer and behavior is verified. Original collision, heights, encounter data, movement, actors, events and entrances are preserved.')
        row['hoennOutdoorRemainingReview'] = dict(kind=kind, source_family=pair, pixel_scale=1,
                                                   contract_sha256=digest(item))
        record = dict(game=game, pair=pair, mid=mid, sourceHash=row['sourceHash'],
                      sourceBehavior=row['sourceBehavior'], compositionPixelHash=row['compositionPixelHash'],
                      occurrences=review.counts[game, pair, mid])
        if item.get('replacesExisting'):
            assert game == 'emerald' and pair == 'general__dewford' and mid in TRIANGLE_PRIOR
            record['occurrences'] = 0
            record['revisedOccurrences'] = TRIANGLE_PRIOR[mid]
        records.append(record)
    review.proofs['dewford_harbor_petalburg'] = records
    return records
