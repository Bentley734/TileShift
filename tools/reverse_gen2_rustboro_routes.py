"""Build guarded Crystal Rustboro buildings, urban details and coastal paths."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from PIL import Image
from classic_geometry_review import art as classic_art
from gb_theme_animation import specification
from reverse_gen2_hoenn_city_complete import Review as City
from reverse_gen2_hoenn_outdoor_finish import digest
from reverse_hoenn_review import ground_ref
from reverse_kanto_review import runs
from reverse_oldale_review import exterior, mask_piece, native_piece

PAIR = 'general__rustboro'
GUARD = Path(__file__).with_name('reverse_gen2_rustboro_routes_guards.json')
EVIDENCE = {
    'model': 'This original-size complete native Crystal building module keeps the reviewed footprint, continuous roof trim, window roles and original entrance.',
    'surface': 'The independently reviewed flat surface uses the matching whole native Crystal ground or paving glyph.',
    'paving': 'The full native Crystal pavement glyph follows the reviewed source outline, with matching Crystal lawn in all outside corners.',
    'wood': 'The complete native Crystal S.S. Aqua dock plank glyph retains its original pixels. The verified original water outline and foreground placement are retained.',
    'water': 'Complete native animated Crystal water fills this verified open-water cell.',
    'tree': 'The complete selected Crystal tree crown or root remains at native size with matching ground outside its silhouette.',
    'rim': 'The complete selected Crystal rock texture follows the reviewed cliff outline, with matching original Crystal water or grass in the outside corners.',
    'ordinary_wall': 'An intact native Crystal gray roof edge or blank middle wall preserves the existing window and facade pattern.',
    'geometry': 'The named complete Rustboro-area structure or decorative feature retains its original source geometry and alpha in a reviewed four-color Crystal material. Matched native ground shows through verified exterior pixels.',
}


def emit(review, guard=GUARD):
    contract = json.loads(guard.read_text())
    for game, joins in contract['joins'].items():
        for item in joins:
            layout = review.native_layout(game, item['map'])
            x, y, matrix = item['x'], item['y'], item['matrix']
            assert layout['pair'] == PAIR
            actual = [layout['mids'][row * layout['width'] + x:row * layout['width'] + x + len(matrix[0])]
                      for row in range(y, y + len(matrix))]
            assert actual == matrix, ('Rustboro native building layout changed', game, item)

    field = ground_ref(review, 'gen2')
    pave = review.active_art('emerald', PAIR, 699)['donor']
    shade = review.active_art('emerald', PAIR, 707)['donor']
    road = review.raw_ref('TILESET_JOHTO', (6, 6, 6, 6), 'VIOLET_CITY')
    water = review.gb_ref('crystal', 'UNION_CAVE_1F', 15, 0)
    program = specification(review.cache, water, 'program')
    assert program
    boards = review.gb_at('crystal', 'FAST_SHIP_1F', 16, 6)
    rock = review.gb_ref('crystal', 'UNION_CAVE_1F', 4, 3)
    canopy = review.active_art('emerald', 'general__lavaridge', 206)
    roots = review.active_art('emerald', 'general__lavaridge', 198)
    ground = dict(field=field, pave=pave, road=road, shade=shade, rock=rock)
    models = {
        'shop': City.town_model(review, 6, 2, 2, (1, 3, 4), base=field),
        'cottage': City.town_model(review, 5, 2, 2, (1, 3), base=field),
    }
    school = City.town_model(review, 9, 2, 4, (1, 3, 5, 7), modern=True, base=field)
    ordinary = {569: school[2, 2], 575: school[8, 0], 583: school[8, 1]}
    field_colors = set(review.gb_image(field).get_flattened_data()) | {(222, 255, 222, 255)}
    for name in ('center', 'mart'):
        whole = Image.new('RGBA', (64, 64))
        modules = {}
        for y in range(4):
            for x in range(4):
                modules[x, y] = native_piece(review, 'gen2', name, x, y)
                whole.paste(review.render(modules[x, y]), (x * 16, y * 16))
        outside = exterior(whole, field_colors)
        models[name] = {}
        for (x, y), art in modules.items():
            mask = [(x * 16 + xx, y * 16 + yy) not in outside for yy in range(16) for xx in range(16)]
            models[name][x, y] = mask_piece(review, art, mask, pave, y < 2)

    def masked_parts(ref, bits):
        parts = [dict(donor=ref, srcX=p['x'], srcY=p['y'], **p) for p in runs([bit == '1' for bit in bits])]
        assert 1 <= len(parts) <= 32
        return parts

    def animated(art):
        art.update(animated=True, animation=program, animationCategory='water')
        return art

    def sea_with(parts, role):
        sea = dict(donor=water, x=0, y=0, w=16, h=16, animated=True)
        return animated(review.composite(None, [sea, *parts], role))

    records = []
    for item in contract['cells']:
        game, mid = item['game'], item['mid']
        assert item['pair'] == PAIR
        source = review.imp.cell_index(game)[PAIR, mid]
        assert source['pixel_sha256'] == item['sourceHash']
        assert source['behavior'] == item['sourceBehavior']
        assert source['layer_sha256'] == item['sourceLayers']
        kind, plan = item['kind'], item.get('plan')
        role = f'reverse_gen2_rustboro_routes_{kind}_{mid}'
        if kind == 'model':
            name, x, y = plan
            art = copy.deepcopy(models[name][x, y])
        elif kind == 'surface':
            art = review.native(ground[plan], role)
        elif kind == 'paving':
            art = review.composite(field, masked_parts(ground[plan], item['mask']), role)
        elif kind == 'wood':
            if item['mask'] == '1' * 256:
                art = review.native(boards, role)
            else:
                art = sea_with(masked_parts(boards, item['mask']), role)
            art['overMask'] = item['priority']
        elif kind == 'water':
            art = animated(review.native(water, role))
        elif kind == 'tree':
            section, base = plan
            original = canopy if section == 0 else roots
            art = review.composite(ground[base], copy.deepcopy(original['parts']), role)
            art['overMask'] = original['overMask']
        elif kind == 'rim':
            bid, q, base = plan
            ref = review.gb_ref('crystal', 'UNION_CAVE_1F', bid, q)
            parts = masked_parts(ref, item['mask'])
            art = sea_with(parts, role) if base == 'water' else review.composite(ground[base], parts, role)
        elif kind == 'ordinary_wall':
            art = copy.deepcopy(ordinary[plan])
        else:
            assert kind == 'geometry'
            colors = {tuple(x[:3]): tuple(x[3:]) for x in item['colorMap']}
            art = classic_art(review, game, PAIR, mid, item['feature'], item['palette'], colors, role,
                              ground=item['ground'], source_animation=item.get('sourceAnimation'))
        art['role'] = role
        if kind != 'geometry':
            art.setdefault('overMask', '0' * 256)
        row = review.row(game, PAIR, mid, 'gen2', art, EVIDENCE[kind] +
                         ' Source layers and behavior are verified. Native layouts, collision, height, encounters, movement, actors, events and entrances are preserved.')
        row['hoennOutdoorRemainingReview'] = dict(kind=kind, source_family=PAIR, pixel_scale=1,
                                                   contract_sha256=digest(item))
        records.append(dict(game=game, pair=PAIR, mid=mid, sourceHash=row['sourceHash'],
                            sourceBehavior=row['sourceBehavior'], compositionPixelHash=row['compositionPixelHash'],
                            occurrences=review.counts[game, PAIR, mid]))
    review.proofs['rustboro_routes'] = records
    return records
