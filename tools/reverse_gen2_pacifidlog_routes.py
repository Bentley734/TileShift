"""Build guarded native Pacifidlog shore and Seafloor Cavern counterparts."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from classic_geometry_review import art as classic_art
from gb_theme_animation import specification
from reverse_gen2_hoenn_outdoor_finish import digest
from reverse_kanto_review import runs

PAIR='general__pacifidlog'
GUARD=Path(__file__).with_name('reverse_gen2_pacifidlog_routes_guards.json')
EVIDENCE={
    'alias':'The independently verified Seafloor Cavern wall has the same full native source RGBA, layer fingerprints and original behavior as the selected reviewed cave-wall counterpart.',
    'floor':'The actual complete ordinary cave floor uses one full original Crystal stone floor at its native size.',
    'current':'Complete native Crystal cave-water glyphs retain the eastward flow direction and replay the original Crystal water program. The source current behavior and movement data remain exact.',
    'shallow':'Whole native Crystal animated shallow and deeper water glyphs follow the exact checked shallow-water boundary and preserve original Surf and walking behavior.',
    'ridge':'A full original Crystal cliff profile preserves the independently reviewed original side and raised face.',
    'wet_rock':'The whole original Crystal rock profile meets animated water at the exact original wet boundary. Every exterior corner exposes water.',
    'sky_bank':'The whole original Crystal rock or cliff face keeps its true outline, exposing the matching native Sky Pillar sand at outside corners.',
    'boulder':'Complete original Crystal small or full round rock glyphs keep the actual source stone count and original scale. Only outside corners expose the selected native cave floor.',
    'geometry':'The complete explicitly named cavern recess and entrance preserves its source shape, frame and layer order in a reviewed four-color Crystal material.',
}

def emit(review,guard=GUARD):
    water=review.gb_ref('crystal','UNION_CAVE_1F',15,0)
    program=specification(review.cache,water,'program')
    assert program
    shallow=copy.deepcopy(water)
    colors=[[222,255,222],[181,197,255],[140,165,255],[82,107,206]]
    shallow['palettes']=[copy.deepcopy(colors)for _ in range(8)]
    current=copy.deepcopy(water)
    current_colors=[[222,255,222],[148,156,255],[107,99,255],[58,58,58]]
    current['palettes']=[copy.deepcopy(current_colors)for _ in range(8)]
    floor=review.gb_ref('crystal','UNION_CAVE_1F',2,0)
    sand=review.raw_ref('TILESET_KANTO',(48,57,57,48),'PALLET_TOWN')
    rock=review.gb_ref('crystal','UNION_CAVE_1F',24,0)
    small=review.gb_ref('crystal','UNION_CAVE_1F',4,2)
    left=[6,4,3,2,1,1,1,0,0,0,0,0,0,1,1,2]
    right=[11,12,13,14,15,15,16,16,16,16,16,16,16,16,15,13]
    rock_mask=''.join('1'if left[y]<=x<right[y]else'0'for y in range(16)for x in range(16))
    def parts_for(ref,bits):
        parts=[dict(donor=ref,srcX=p['x'],srcY=p['y'],**p)for p in runs([bit=='1'for bit in bits])]
        assert 1<=len(parts)<=32
        return parts
    def animate(art,animation=program):
        art.update(animated=True,animation=animation,animationCategory='water')
        return art
    def sea_with(parts,role):
        wave=dict(donor=water,x=0,y=0,w=16,h=16,animated=True)
        return animate(review.composite(None,[wave,*parts],role))

    records=[]
    for item in json.loads(guard.read_text()):
        game,mid=item['game'],item['mid']
        assert item['pair']==PAIR
        source=review.imp.cell_index(game)[PAIR,mid]
        assert source['pixel_sha256']==item['sourceHash']
        assert source['behavior']==item['sourceBehavior']
        assert source['layer_sha256']==item['sourceLayers']
        kind,plan=item['kind'],item.get('plan')
        role=f'reverse_gen2_pacifidlog_routes_{kind}_{mid}'
        if kind=='alias':
            witness=item['witness']
            other_game,other_pair,other_mid=witness['game'],witness['pair'],witness['mid']
            module,_,canonical=review.locations[other_game,'gen2',other_pair,other_mid,None]
            assert module==witness['module']
            assert canonical['role']==witness['role'] and canonical['compositionPixelHash']==witness['compositionPixelHash']
            other=review.imp.cell_index(other_game)[other_pair,other_mid]
            assert all(other[k]==source[k]for k in ('pixel_sha256','layer_sha256','behavior'))
            art=review.active_art(other_game,other_pair,other_mid)
        elif kind=='floor':
            art=review.native(floor,role)
        elif kind=='current':
            art=animate(review.native(current,role),specification(review.cache,current,'program',flow_direction=plan))
        elif kind=='shallow':
            parts=parts_for(shallow,item['mask'])
            for part in parts:part['animated']=True
            art=sea_with(parts,role)
        elif kind in ('ridge','wet_rock','sky_bank'):
            ref=review.gb_ref('crystal','UNION_CAVE_1F',*plan)
            mask=item.get('mask','1'*256)
            if mask=='1'*256:art=review.native(ref,role)
            elif kind=='wet_rock':art=sea_with(parts_for(ref,mask),role)
            else:art=review.composite(sand,parts_for(ref,mask),role)
        elif kind=='boulder':
            if plan==1:parts=parts_for(rock,rock_mask)
            else:
                assert plan==3
                parts=[dict(donor=small,srcX=0,srcY=0,w=8,h=8,x=x,y=y)
                       for x,y in ((0,0),(8,0),(4,8))]
            art=review.composite(floor,parts,role)
        else:
            assert kind=='geometry'
            mapping={tuple(x[:3]):tuple(x[3:])for x in item['colorMap']}
            art=classic_art(review,game,PAIR,mid,item['feature'],item['palette'],mapping,role)
        art['role']=role
        if kind!='geometry':art.setdefault('overMask','0'*256)
        row=review.row(game,PAIR,mid,'gen2',art,EVIDENCE[kind]+
                       ' Every source plane and behavior is checked. Native layouts, collision, movement, height, actors, events and entrances are preserved.')
        row['hoennOutdoorRemainingReview']=dict(kind=kind,source_family=PAIR,pixel_scale=1,
                                                contract_sha256=digest(item))
        records.append(dict(game=game,pair=PAIR,mid=mid,sourceHash=row['sourceHash'],
                            sourceBehavior=row['sourceBehavior'],compositionPixelHash=row['compositionPixelHash'],
                            occurrences=review.counts[game,PAIR,mid]))
    review.proofs['pacifidlog_routes']=records
    return records
