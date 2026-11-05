"""Build the guarded Slateport and adjacent beach/sea feature batch."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from classic_geometry_review import art as classic_art
from gb_theme_animation import specification
from johto_remaining_review import artwork
from reverse_gen2_hoenn_city_complete import Review as City
from reverse_gen2_hoenn_outdoor_finish import digest
from reverse_hoenn_review import ground_ref
from reverse_kanto_review import runs
from reverse_oldale_review import exterior

PAIR = 'general__slateport'
GUARD = Path(__file__).with_name('reverse_gen2_slateport_guards.json')
EVIDENCE = {
    'paving': 'The complete native Crystal stone walking path and brick dock paving remain separate materials. The native field appears through the verified source pavement border, preserving its direction and connected paved area.',
    'curb': 'The complete native Crystal low city curb retains its original matching straight or corner modules. It borders the actual connected dock paving or lawn. No posts or stairs are rotated into different roles.',
    'rock': 'A complete native Crystal cliff material follows the reviewed source contour. Native sand or animated sea appears outside the silhouette, including at the exact coast corner.',
    'structure': 'The whole building uses complete native Crystal roof caps, exterior frames and doorway modules at their original scale. Only plain roof material repeats to reach the source footprint. Its entire roof edge and actual doorway stay aligned.',
    'geometry': 'This explicitly named complete regional feature retains its native source silhouette, all original geometry and priority with four selected Crystal colors. Its verified exterior ground uses the matching native surface, including the surrounding animated Crystal water where present.',
    'shrub': 'The complete original 16-pixel Crystal decorative tree keeps every leaf and root at native size. Only the exterior of the original silhouette exposes the same native lawn as its neighbors.',
    'sign': 'The complete original Crystal outdoor sign retains its native face and legs. Its exterior exposes the same native beach sand as its neighbors.',
    'facade': 'The complete native Crystal plain facade module matches the neighboring house wall and foundation. It retains the original roof eave and regular plain wall without introducing an extra side trim or doorway.',
    'picket': 'The original Crystal picket modules remain intact in the verified left, right or joined alignment. The outside remains the selected matching native field.',
}


def emit(review, guard=GUARD):
    contract = json.loads(guard.read_text())
    for game, joins in contract['joins'].items():
        for item in joins:
            layout = review.native_layout(game, item['map'])
            x, y, matrix = item['x'], item['y'], item['matrix']
            assert layout['pair'] == PAIR
            actual = [layout['mids'][row*layout['width']+x:row*layout['width']+x+len(matrix[0])]
                      for row in range(y, y+len(matrix))]
            assert actual == matrix, ('Slateport complete structure layout changed', game, item)

    field = ground_ref(review, 'gen2')
    sand = review.raw_ref('TILESET_KANTO', (48, 57, 57, 48), 'PALLET_TOWN')
    street = review.raw_ref('TILESET_JOHTO', (6,) * 4, 'VIOLET_CITY')
    deck = review.gb_ref('crystal', 'GOLDENROD_CITY', 6, 0)
    gray = [[222, 255, 222], [173, 173, 173], [107, 107, 107], [58, 58, 58]]
    deck['palettes'] = [copy.deepcopy(gray) for _ in range(8)]
    water = review.gb_ref('crystal', 'UNION_CAVE_1F', 15, 0)
    program = specification(review.cache, water, 'program')
    assert program
    grounds = dict(field=field, sand=sand, street=street, deck=deck)
    native_structures = {
        'contest': City.town_model(review, 5, 3, door=2, windows=(1,3), modern=True),
        'battle_tent': City.town_model(review, 5, 3, door=2, windows=(1,3), modern=True),
        'harbor': City.town_model(review, 7, 4, door=3, windows=(1,2,4,5), modern=True),
        'beach_house': City.town_model(review, 5, 2, door=2, windows=(1,3), base=sand),
    }
    flat_wall = City.town_model(review, 5, 2, door=1, windows=(2,), base=deck)[1,2]
    native_curb = {}
    for direction in ('n','s','w','e','nw','ne','sw','se'):
        role = 'reverse_gen2_hoenn_native_city_curb_' + direction + '_paving'
        native_curb[direction] = artwork(next(row for row in review.prior
                                               if row['style']=='gen2' and row.get('role')==role))

    def parts_for(ref, mask):
        parts = [dict(donor=ref, srcX=span['x'], srcY=span['y'], **span) for span in runs(mask)]
        assert 1 <= len(parts) <= 32
        return parts

    def complete_object(ref, backdrop, base, role):
        pixels = review.gb_image(ref)
        outside = exterior(pixels, set(review.gb_image(backdrop).get_flattened_data()))
        return review.composite(base, parts_for(ref, [(x,y) not in outside for y in range(16)
                                                      for x in range(16)]), role)

    records=[]
    for item in contract['cells']:
        game, mid = item['game'], item['mid']
        assert item['pair']==PAIR
        source = review.imp.cell_index(game)[PAIR,mid]
        assert source['pixel_sha256']==item['sourceHash']
        assert source['behavior']==item['sourceBehavior']
        assert source['layer_sha256']==item['sourceLayers']
        kind, plan = item['kind'], item.get('plan')
        role = f'reverse_gen2_slateport_{kind}_{mid}'
        if kind=='paving':
            ref = grounds[plan[0]]
            if item['mask']=='1'*256:
                art=review.native(ref,role)
            else:
                art=review.composite(field,parts_for(ref,[bit=='1' for bit in item['mask']]),role)
        elif kind=='curb':
            direction,base=plan
            art=copy.deepcopy(native_curb[direction])
            art['base']=grounds[base]
        elif kind=='rock':
            base,bid,quadrant=plan
            ref=review.gb_ref('crystal','UNION_CAVE_1F',bid,quadrant)
            parts=parts_for(ref,[bit=='1' for bit in item['mask']])
            if base=='water':
                sea=dict(donor=water,x=0,y=0,w=16,h=16,animated=True)
                art=review.composite(None,[sea,*parts],role)
                art.update(animated=True,animation=program,animationCategory='water')
            else:
                art=review.composite(grounds[base],parts,role)
        elif kind=='structure':
            name,x,y,door_x,door_y=plan
            if mid in (475,710,731,915):
                assert (x,y)==(door_x,door_y)
            art=copy.deepcopy(native_structures[name][x,y])
        elif kind=='shrub':
            ref=review.raw_ref('TILESET_JOHTO',(30,31,62,63),'NEW_BARK_TOWN')
            art=complete_object(ref,field,field,role)
        elif kind=='sign':
            ref=review.gb_at('crystal','PALLET_TOWN',3,5)
            background=review.gb_at('crystal','PALLET_TOWN',3,4)
            art=complete_object(ref,background,sand,role)
        elif kind=='facade':
            if mid==20:
                art=review.active_art(game,PAIR,19)
                art['base']=deck
            else:
                assert mid==715
                art=copy.deepcopy(flat_wall)
        elif kind=='picket':
            art=review.active_art('emerald','general__mauville',plan[0])
            art['base']=field
        else:
            assert kind=='geometry'
            colors={tuple(entry[:3]):tuple(entry[3:]) for entry in item['colorMap']}
            art=classic_art(review,game,PAIR,mid,item['feature'],item['palette'],colors,
                            role,ground=item['ground'],source_animation=item.get('sourceAnimation'))
        art['role']=role
        if kind!='geometry':
            art.setdefault('overMask','0'*256)
        row=review.row(game,PAIR,mid,'gen2',art,EVIDENCE[kind]+
                       ' Every source plane and behavior is checked. The original source collision, terrain, movement, scripts, events and layout remain intact.')
        row['hoennOutdoorRemainingReview']=dict(kind=kind,contract_sha256=digest(item),
                                                source_family=PAIR,pixel_scale=1)
        records.append(dict(game=game,pair=PAIR,mid=mid,sourceHash=row['sourceHash'],
                            sourceBehavior=row['sourceBehavior'],compositionPixelHash=row['compositionPixelHash'],
                            occurrences=review.counts[game,PAIR,mid]))
    review.proofs['slateport_reviewed']=records
    return records
