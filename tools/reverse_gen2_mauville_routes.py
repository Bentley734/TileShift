"""Build reviewed Crystal replacements for the general Mauville route atlas."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from classic_geometry_review import art as classic_art
from gb_theme_animation import specification
from reverse_gen2_hoenn_outdoor_finish import digest
from reverse_hoenn_review import ground_ref
from reverse_kanto_review import runs

PAIR='general__mauville'
GUARD=Path(__file__).with_name('reverse_gen2_mauville_routes_guards.json')
EVIDENCE={
    'surface':'A verified ordinary lawn or sand surface uses the full native Crystal terrain glyph.',
    'flower':'A complete original Crystal flower cluster keeps its native foreground shape and animation on matching lawn.',
    'picket':'Complete native Crystal picket modules retain the observed alignment and expose the matching selected lawn.',
    'conifer':'This verified canopy or root section keeps its complete original Crystal narrow-tree module and selected ground.',
    'wet_tree':'The complete original Crystal tree crown remains above animated Crystal water. The verified native tree silhouette exposes water at all outside corners.',
    'cliff':'A complete native Crystal cliff profile follows the individually verified raised edge. Matching field or sand shows through outside each corner.',
    'beach':'Native Crystal beach sand follows the exact joined shore footprint. Animated native Crystal water surrounds the complete dry shore edge.',
    'house':'An intact native roof or wall module matches the adjacent original-scale facade. The lower roof line runs straight over the original doorway.',
    'geometry':'This named regional feature keeps its complete source geometry and priority in a reviewed four-color Crystal material. The individually verified exterior mask retains the matching selected ground or native animated water.',
}

def emit(review,guard=GUARD):
    records=[]
    field=ground_ref(review,'gen2')
    sand=review.raw_ref('TILESET_KANTO',(48,57,57,48),'PALLET_TOWN')
    water=review.gb_ref('crystal','UNION_CAVE_1F',15,0)
    animation=specification(review.cache,water,'program')
    assert animation
    grounds=dict(field=field,sand=sand)
    canopy=review.active_art('emerald','general__lavaridge',206)
    roots=review.active_art('emerald','general__lavaridge',198)
    def parts_for(ref,bits):
        result=[dict(donor=ref,srcX=p['x'],srcY=p['y'],**p)for p in runs([bit=='1' for bit in bits])]
        assert 1<=len(result)<=32
        return result
    def sea_with(parts,role):
        art=review.composite(None,[dict(donor=water,x=0,y=0,w=16,h=16,animated=True),*parts],role)
        art.update(animated=True,animation=animation,animationCategory='water')
        return art
    for item in json.loads(guard.read_text()):
        game,mid=item['game'],item['mid']
        assert item['pair']==PAIR
        source=review.imp.cell_index(game)[PAIR,mid]
        assert source['pixel_sha256']==item['sourceHash']
        assert source['behavior']==item['sourceBehavior']
        assert source['layer_sha256']==item['sourceLayers']
        kind,plan=item['kind'],item.get('plan')
        role=f'reverse_gen2_mauville_routes_{kind}_{mid}'
        if kind=='surface':
            art=review.native(grounds[plan],role)
        elif kind=='flower':
            art=review.active_art('emerald',PAIR,4)
        elif kind in ('picket','house'):
            art=review.active_art('emerald',PAIR,plan)
        elif kind=='conifer':
            art=copy.deepcopy(canopy if plan==0 else roots)
        elif kind=='wet_tree':
            art=sea_with(copy.deepcopy(canopy['parts']),role)
            art['overMask']=canopy['overMask']
        elif kind=='beach':
            art=sea_with(parts_for(sand,item['mask']),role)
        elif kind=='cliff':
            bid,q,base=plan
            ref=review.gb_ref('crystal','UNION_CAVE_1F',bid,q)
            art=review.composite(grounds[base],parts_for(ref,item['mask']),role)
        else:
            assert kind=='geometry'
            colors={tuple(x[:3]):tuple(x[3:])for x in item['colorMap']}
            art=classic_art(review,game,PAIR,mid,item['feature'],item['palette'],colors,role,
                            ground=item['ground'],source_animation=item.get('sourceAnimation'))
        art['role']=role
        if kind!='geometry':art.setdefault('overMask','0'*256)
        row=review.row(game,PAIR,mid,'gen2',art,EVIDENCE[kind]+
                       ' Every source layer and behavior is checked. Native layouts, collision, terrain, movement, scripts, events and actual entrances are preserved.')
        row['hoennOutdoorRemainingReview']=dict(kind=kind,source_family=PAIR,pixel_scale=1,
                                                contract_sha256=digest(item))
        records.append(dict(game=game,pair=PAIR,mid=mid,sourceHash=row['sourceHash'],
                            sourceBehavior=row['sourceBehavior'],compositionPixelHash=row['compositionPixelHash'],
                            occurrences=review.counts[game,PAIR,mid]))
    review.proofs['mauville_routes']=records
    return records
