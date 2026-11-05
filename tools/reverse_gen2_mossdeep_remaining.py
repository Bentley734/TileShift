"""Explicit complete Mossdeep buildings and the adjoining ocean terrain."""
from __future__ import annotations

import copy
import json
from collections import Counter
from pathlib import Path

import catalog
import preview
from classic_geometry_review import art as classic_art
from gb_theme_animation import specification
from reverse_gen2_hoenn_city_complete import Review as City
from reverse_hoenn_review import ground_ref
from reverse_kanto_review import runs
from reverse_gen2_hoenn_outdoor_finish import digest

GRAY = [[222, 255, 222], [173, 173, 173], [107, 107, 107], [58, 58, 58]]
PAIR = 'general__mossdeep'
GUARD = Path(__file__).with_name('reverse_gen2_mossdeep_guards.json')

EVIDENCE = {
    'house': 'Whole native Crystal New Bark exterior roofs, door frames, window pairs and wall modules replace the complete Mossdeep houses at the original pixel scale and doorway positions. The wide house repeats only ordinary roof and facade modules. All retained native pixels are exact, and the visible lawn follows the complete roof and wall silhouettes.',
    'sand_house': 'The complete Route124 Diving Treasure Hunter house keeps its four native Crystal side caps, complete existing native roof, window and doorway. Only the exterior of the newly installed side caps exposes the matching native Crystal sand.',
    'surface': 'The actual complete stone plateau, shaded vertical face or deep empty caldera has its separately selected, intact native Crystal terrain tile. The full flat gray limestone and ordinary warmer coastal rock use distinct native palettes.',
    'shore': 'The native Crystal raised coastal stone and water keep the source wet edge and its exact orientation. Native selected water appears only outside the stone profile and runs on the same Crystal water animation as the open sea. Each dry side exposes the actual selected field.',
    'tree': 'This source is one section of a complete original 32-pixel round coastal tree. The intact native Crystal National Park tree keeps its original canopy, roots and transparent exterior. Selected animated water, native sand, lawn or coastal rock shows through the verified silhouette.',
    'geometry': 'This named complete regional feature has a source-geometry derivative with four selected native Crystal colors. The full rocket, launch gantry and station or the distinct stepped limestone caldera and oversized coastal tree forms retain their exact original geometry, pixel scale and layer priority. Individually reviewed exterior ground masks expose the selected native water or lawn.',
}


def emit(review, guard=GUARD):
    contract = json.loads(guard.read_text())
    for game, buildings in contract['joins'].items():
        for item in buildings:
            source = review.native_layout(game, item['map'])
            x, y, matrix = item['x'], item['y'], item['matrix']
            assert source['pair'] == PAIR
            actual = [source['mids'][row*source['width']+x:row*source['width']+x+len(matrix[0])]
                      for row in range(y, y + len(matrix))]
            assert actual == matrix, ('Mossdeep complete structure layout changed', game, item)

    field = ground_ref(review, 'gen2')
    sand = review.raw_ref('TILESET_KANTO', (48, 57, 57, 48), 'PALLET_TOWN')
    water = review.gb_ref('crystal', 'UNION_CAVE_1F', 15, 0)
    program = specification(review.cache, water, 'program')
    assert program

    def rock(bid, quadrant, gray=False):
        ref = review.gb_ref('crystal', 'UNION_CAVE_1F', bid, quadrant)
        if gray:
            ref['palettes'] = [copy.deepcopy(GRAY) for _ in range(8)]
        return ref

    blank = review.raw_ref('TILESET_JOHTO', (0,) * 4, 'VIOLET_CITY')
    blank['palettes'] = [[GRAY[3], GRAY[2], GRAY[1], GRAY[0]] for _ in range(8)]
    assert set(review.gb_image(blank).get_flattened_data()) == {tuple(GRAY[3]) + (255,)}
    terrain = dict(field=field, sand=sand, water=water, floor=rock(4, 3, True),
                   pink_plateau=rock(4, 3), gray_wall=rock(6, 3, True), blank=blank)
    palette = preview.palette_set(review.imp.table('crystal','palettes'),
                                 review.imp.table('crystal','maps')['OLIVINE_CITY'], 'DAY')[6]
    houses = {
        4: City.town_model(review, 4, 2, door=1, windows=(2,), roof_palette=palette),
        5: City.town_model(review, 5, 3, door=1, windows=(2,3), roof_palette=palette),
    }
    island = City.town_model(review, 4, 2, door=1, windows=(2,), base=sand)

    def backed(base, parts, role):
        if base != 'water':
            return review.composite(terrain[base], parts, role)
        whole_water = dict(donor=water, x=0, y=0, w=16, h=16, animated=True)
        art = review.composite(None, [whole_water, *parts], role)
        art.update(animated=True, animation=program, animationCategory='water')
        return art

    records = []
    for item in contract['cells']:
        game, mid = item['game'], item['mid']
        assert item['pair'] == PAIR
        source = review.imp.cell_index(game)[PAIR, mid]
        assert source['pixel_sha256'] == item['sourceHash']
        assert source['behavior'] == item['sourceBehavior']
        assert source['layer_sha256'] == item['sourceLayers']
        kind, plan = item['kind'], item.get('plan')
        role = f'reverse_gen2_mossdeep_{kind}_{mid}'
        if kind == 'house':
            width, roof_rows, x, y = plan
            assert roof_rows == width - 2
            art = copy.deepcopy(houses[width][x,y])
        elif kind == 'sand_house':
            art = copy.deepcopy(island[tuple(plan)])
        elif kind == 'surface':
            art = review.native(terrain[plan[0]], role)
        elif kind == 'shore':
            base, bid, quadrant, gray = plan
            ref = rock(bid, quadrant, gray)
            parts = [dict(donor=ref, srcX=p['x'], srcY=p['y'], **p)
                     for p in runs([value == '1' for value in item['mask']])]
            art = backed(base, parts, role)
        elif kind == 'tree':
            quadrant, base = plan
            tree = review.park_tree_art(quadrant, field)
            art = backed(base, tree['parts'], role)
            art['overMask'] = tree['overMask']
        else:
            assert kind == 'geometry'
            colors = {tuple(entry[:3]): tuple(entry[3:]) for entry in item['colorMap']}
            art = classic_art(review, game, PAIR, mid, item['feature'], item['palette'], colors,
                              role, ground=item['ground'])
        art['role'] = role
        if kind != 'geometry':
            art.setdefault('overMask', '0' * 256)
        row = review.row(game, PAIR, mid, 'gen2', art, EVIDENCE[kind] +
                         ' Every source layer and original behavior is verified. All source collisions, elevations, encounters, movement, events, entrances and layouts are preserved.')
        row['hoennOutdoorRemainingReview'] = dict(kind=kind, contract_sha256=digest(item),
                                                 source_family=PAIR, pixel_scale=1)
        records.append(dict(game=game, pair=PAIR, mid=mid, sourceHash=row['sourceHash'],
                            sourceBehavior=row['sourceBehavior'], compositionPixelHash=row['compositionPixelHash'],
                            occurrences=review.counts[game,PAIR,mid]))
    review.proofs['mossdeep_reviewed'] = records
    return records
