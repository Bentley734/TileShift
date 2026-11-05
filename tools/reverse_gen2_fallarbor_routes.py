"""Build the complete guarded Fallarbor route background batch."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from classic_geometry_review import art as classic_art
from gb_theme_animation import specification
from reverse_gen2_hoenn_city_complete import Review as City
from reverse_gen2_hoenn_outdoor_finish import digest
from reverse_hoenn_review import ground_ref
from reverse_kanto_review import runs
from reverse_oldale_review import exterior

PAIR='general__fallarbor'
GUARD=Path(__file__).with_name('reverse_gen2_fallarbor_routes_guards.json')
EVIDENCE={
    'tree':'Complete native Crystal National Park crowns and root quarters retain their original shape and scale. The joined native trees keep matching ash, rock, or animated water beneath genuine exterior corners.',
    'bridge':'The complete original Crystal S.S. Aqua wooden deck glyph keeps its original plank direction and the actual bridge footprint. Its verified native background and foreground corners expose matching animated water.',
    'boulder':'An intact original Crystal stone glyph or pair keeps the observed complete source feature count. The donor exterior is transparent and uses the selected ash or rock behind it.',
    'rock':'A complete native Crystal cliff or ledge profile retains the original side, visible slope, and exact exterior contour. Native ash, ground, or animated water shows through its outside corners.',
    'ash_edge':'The original Crystal gray ash material meets selected native lawn at the observed source footprint, without a rectangle of the old terrain.',
    'shore':'The matching native Crystal sand retains the actual shoreline footprint. Complete native water surrounds the dry sand with its original Crystal animation.',
    'house':'The complete native Crystal timber facade and full rectangular roof use the same intact modules as the adjacent Fallarbor house cells. The complete doorway and window pair stay at their original scale.',
    'sign':'The complete original Crystal outdoor sign face and legs retain their native scale. Its genuine exterior uses the matching ash.',
    'surface':'The full original Crystal sand keeps this complete ordinary walkable source surface in its original role.',
    'geometry':'The named joined original fossil cut or seedling plot retains its complete shape, feature outlines and layer priority in the reviewed four-color Crystal material, with independently selected backing.',
}

def emit(review,guard=GUARD):
    gray=[[222,255,222],[173,173,173],[107,107,107],[58,58,58]]
    field=ground_ref(review,'gen2')
    sand=review.raw_ref('TILESET_KANTO',(48,57,57,48),'PALLET_TOWN')
    ash=review.gb_ref('crystal','UNION_CAVE_1F',2,0)
    ash['palettes']=[copy.deepcopy(gray)for _ in range(8)]
    water=review.gb_ref('crystal','UNION_CAVE_1F',15,0)
    program=specification(review.cache,water,'program')
    assert program
    boards=review.gb_at('crystal','FAST_SHIP_1F',16,6)
    rock=review.gb_ref('crystal','UNION_CAVE_1F',4,3)
    large=review.gb_ref('crystal','UNION_CAVE_1F',24,0)
    small=review.gb_ref('crystal','UNION_CAVE_1F',4,2)
    terrain=dict(field=field,sand=sand,ash=ash,rock=rock)
    house=City.town_model(review,4,2,door=1,windows=(2,),base=ash)
    def parts_for(ref,mask):
        parts=[dict(donor=ref,srcX=p['x'],srcY=p['y'],**p)for p in runs([bit=='1'for bit in mask])]
        assert 1<=len(parts)<=32
        return parts
    def backed(base,parts,role):
        if base!='water':
            return review.composite(terrain[base],parts,role)
        sea=dict(donor=water,x=0,y=0,w=16,h=16,animated=True)
        art=review.composite(None,[sea,*parts],role)
        art.update(animated=True,animation=program,animationCategory='water')
        return art

    left=[6,4,3,2,1,1,1,0,0,0,0,0,0,1,1,2]
    right=[11,12,13,14,15,15,16,16,16,16,16,16,16,16,15,13]
    round_mask=''.join('1'if left[y]<=x<right[y]else'0'for y in range(16)for x in range(16))
    small_glyph=review.gb_image(small).crop((0,0,8,8))
    corner_colors={small_glyph.getpixel(xy)for xy in ((0,0),(7,0),(0,7),(7,7))}
    outside=exterior(small_glyph,corner_colors)
    small_mask=''.join('1'if x<8 and y<8 and (x,y)not in outside else'0'for y in range(16)for x in range(16))
    sign=review.gb_at('crystal','PALLET_TOWN',3,5)
    sign_floor=review.gb_at('crystal','PALLET_TOWN',3,4)
    sign_outside=exterior(review.gb_image(sign),set(review.gb_image(sign_floor).get_flattened_data()))
    sign_mask=''.join('1'if (x,y)not in sign_outside else'0'for y in range(16)for x in range(16))

    records=[]
    for item in json.loads(guard.read_text()):
        game,mid=item['game'],item['mid']
        assert item['pair']==PAIR
        source=review.imp.cell_index(game)[PAIR,mid]
        assert source['pixel_sha256']==item['sourceHash']
        assert source['behavior']==item['sourceBehavior']
        assert source['layer_sha256']==item['sourceLayers']
        kind,plan=item['kind'],item.get('plan')
        role=f'reverse_gen2_fallarbor_routes_{kind}_{mid}'
        if kind=='tree':
            quadrant,base=plan
            tree=review.park_tree_art(quadrant,field)
            art=backed(base,tree['parts'],role)
            art['overMask']=tree['overMask']
        elif kind=='bridge':
            if item['mask']=='1'*256:art=review.native(boards,role)
            else:art=backed(plan,parts_for(boards,item['mask']),role)
            art['overMask']=item['priority']
        elif kind=='boulder':
            count,base=plan
            if count==16:
                parts=parts_for(large,round_mask)
            else:
                parts=[]
                positions=((4,4),) if count==1 else ((0,4),(8,4))
                for dx,dy in positions:
                    for piece in parts_for(small,small_mask):
                        piece.update(x=piece['x']+dx,y=piece['y']+dy);parts.append(piece)
            art=backed(base,parts,role)
        elif kind=='rock':
            bid,q,base=plan
            ref=review.gb_ref('crystal','UNION_CAVE_1F',bid,q)
            if mid in (726,727,810,811,812,817,818,819,820,825,827,828,829,831,834,835,849):
                ref['palettes']=[copy.deepcopy(gray)for _ in range(8)]
            if item['mask']=='1'*256:art=review.native(ref,role)
            else:art=backed(base,parts_for(ref,item['mask']),role)
        elif kind=='ash_edge':
            art=review.native(ash,role)if item['mask']=='1'*256 else backed('field',parts_for(ash,item['mask']),role)
        elif kind=='shore':
            art=backed('water',parts_for(sand,item['mask']),role)
        elif kind=='house':
            art=copy.deepcopy(house[tuple(plan)])
        elif kind=='sign':
            art=backed(plan,parts_for(sign,sign_mask),role)
        elif kind=='surface':
            art=review.native(terrain[plan],role)
        else:
            assert kind=='geometry'
            colors={tuple(x[:3]):tuple(x[3:])for x in item['colorMap']}
            art=classic_art(review,game,PAIR,mid,item['feature'],item['palette'],colors,role,
                            ground=item['ground'],source_animation=item.get('sourceAnimation'))
        art['role']=role
        if kind!='geometry':art.setdefault('overMask','0'*256)
        row=review.row(game,PAIR,mid,'gen2',art,EVIDENCE[kind]+
                       ' Every source layer and behavior is checked. Native layouts, collision, height, encounters, movement, actors, events and entrances are preserved.')
        row['hoennOutdoorRemainingReview']=dict(kind=kind,source_family=PAIR,pixel_scale=1,
                                                contract_sha256=digest(item))
        records.append(dict(game=game,pair=PAIR,mid=mid,sourceHash=row['sourceHash'],
                            sourceBehavior=row['sourceBehavior'],compositionPixelHash=row['compositionPixelHash'],
                            occurrences=review.counts[game,PAIR,mid]))
    review.proofs['fallarbor_routes']=records
    return records
