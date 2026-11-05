"""Build guarded Crystal outdoor routes for the Fortree secondary atlas."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from classic_geometry_review import art as classic_art
from gb_theme_animation import specification
from johto_remaining_review import artwork
from reverse_gen2_hoenn_outdoor_finish import digest
from reverse_hoenn_review import ground_ref
from reverse_kanto_review import runs

PAIR='general__fortree'
GUARD=Path(__file__).with_name('reverse_gen2_fortree_routes_guards.json')
EVIDENCE={
    'long_grass':'The complete original Crystal encounter grass glyph keeps the original tall grass behavior and native foot-level foreground.',
    'native_surface':'This independently reviewed full open pool or wet lawn uses its complete original Crystal water or nonencounter ground glyph.',
    'pond_corner':'Original Crystal animated water meets the exact handed pond footprint. Native lawn appears outside the selected water instead of a rectangular ground patch.',
    'bridge':'The entire native Crystal S.S. Aqua wooden deck glyph keeps its original plank direction and scale. The verified source foreground silhouette retains the actual joins and exposes native water, rock or lawn through outside corners.',
    'rock':'The complete native Crystal cliff profile keeps the selected raised side and wet or dry corner. Only original rock foreground covers actors. Water or grass remains visible outside the verified rock contour.',
    'tree':'The complete original Crystal tree crown or root module retains every native leaf and trunk pixel at its original scale. The verified surroundings show matching native water, stone or lawn through the silhouette.',
    'geometry':'The independently named whole original regional feature retains its precise joined geometry and native layers in a reviewed four-color Crystal material. Its explicit backing mask uses the matching native surface.',
}

def emit(review,guard=GUARD):
    field=ground_ref(review,'gen2')
    water=review.gb_ref('crystal','UNION_CAVE_1F',15,0)
    animation=specification(review.cache,water,'program')
    assert animation
    rock=review.gb_ref('crystal','UNION_CAVE_1F',4,3)
    boards=review.gb_at('crystal','FAST_SHIP_1F',16,6)
    terrain=dict(field=field,water=water,rock=rock)
    canopy=review.active_art('emerald','general__lavaridge',206)
    roots=review.active_art('emerald','general__lavaridge',198)
    grass=next(row for row in review.prior if row['style']=='gen2'and
               row.get('role')=='reverse_gen2_hoenn_complete_classic_encounter_grass')
    grass_art=artwork(grass)
    grass_art['overMask']=grass['overMask']

    def parts_for(ref,bits):
        parts=[dict(donor=ref,srcX=p['x'],srcY=p['y'],**p)for p in runs([bit=='1'for bit in bits])]
        assert 1<=len(parts)<=32
        return parts
    def animate(art):
        art.update(animated=True,animation=animation,animationCategory='water')
        return art
    def backed(base,parts,role):
        if base!='water':
            return review.composite(terrain[base],parts,role)
        sea=dict(donor=water,x=0,y=0,w=16,h=16,animated=True)
        return animate(review.composite(None,[sea,*parts],role))

    records=[]
    for item in json.loads(guard.read_text()):
        game,mid=item['game'],item['mid']
        assert item['pair']==PAIR
        source=review.imp.cell_index(game)[PAIR,mid]
        assert source['pixel_sha256']==item['sourceHash']
        assert source['behavior']==item['sourceBehavior']
        assert source['layer_sha256']==item['sourceLayers']
        kind,plan=item['kind'],item.get('plan')
        role=f'reverse_gen2_fortree_routes_{kind}_{mid}'
        if kind=='long_grass':
            art=copy.deepcopy(grass_art)
        elif kind=='native_surface':
            art=review.native(terrain[plan],role)
            if plan=='water':animate(art)
        elif kind=='pond_corner':
            parts=parts_for(water,item['mask'])
            for part in parts:part['animated']=True
            art=animate(review.composite(field,parts,role))
        elif kind=='bridge':
            if item['mask']=='1'*256:
                art=review.native(boards,role)
            else:
                art=backed(plan,parts_for(boards,item['mask']),role)
            art['overMask']=item['priority']
        elif kind=='rock':
            base,bid,q=plan
            ref=review.gb_ref('crystal','UNION_CAVE_1F',bid,q)
            if item['mask']=='1'*256:
                art=review.native(ref,role)
            else:
                art=backed(base,parts_for(ref,item['mask']),role)
            art['overMask']=item['priority']
        elif kind=='tree':
            base,section=plan
            tree=canopy if section==0 else roots
            art=backed(base,copy.deepcopy(tree['parts']),role)
            art['overMask']=tree['overMask']
        else:
            assert kind=='geometry'
            colors={tuple(x[:3]):tuple(x[3:])for x in item['colorMap']}
            art=classic_art(review,game,PAIR,mid,item['feature'],item['palette'],colors,role,
                            ground=item['ground'],source_animation=item.get('sourceAnimation'))
        art['role']=role
        if kind!='geometry':art.setdefault('overMask','0'*256)
        row=review.row(game,PAIR,mid,'gen2',art,EVIDENCE[kind]+
                       ' Every source plane and behavior is checked. Native layouts, collision, height, encounters, movement, actors, events and entrances are preserved.')
        row['hoennOutdoorRemainingReview']=dict(kind=kind,source_family=PAIR,pixel_scale=1,
                                                contract_sha256=digest(item))
        records.append(dict(game=game,pair=PAIR,mid=mid,sourceHash=row['sourceHash'],
                            sourceBehavior=row['sourceBehavior'],compositionPixelHash=row['compositionPixelHash'],
                            occurrences=review.counts[game,PAIR,mid]))
    review.proofs['fortree_routes']=records
    return records
