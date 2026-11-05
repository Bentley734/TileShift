"""Build guarded native-scale Sootopolis terraces, houses and crater water."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from PIL import Image
from classic_geometry_review import art as classic_art
from gb_theme_animation import specification
from reverse_gen2_hoenn_outdoor_finish import digest
from reverse_hoenn_review import ground_ref
from reverse_kanto_review import runs
from reverse_oldale_review import exterior,mask_piece,native_piece

PAIR='general__sootopolis'
GUARD=Path(__file__).with_name('reverse_gen2_sootopolis_routes_guards.json')
EVIDENCE={
    'floor':'The complete selected native Crystal limestone terrace replaces the whole source plateau or pale floor material.',
    'house':'A complete selected native Crystal Sootopolis roof, wall, base, or compact roof cap matches the adjacent whole building. Native frames and doorway shapes remain intact at their original pixel scale.',
    'service':'The complete native Crystal service-building roof or facade uses its original glyphs and existing doorway anchor. Only exterior corners expose matching native limestone.',
    'water':'The matching original animated Crystal water retains the verified shallows and deep-water footprint inside the Sootopolis crater.',
    'rock':'Native Crystal stone and lake water meet the actual shoreline or rock-tier contour. Original palette variants distinguish the white limestone from the inner rocky crater rim.',
    'geometry':'The independently reviewed complete limestone balustrade or Cave of Origin entrance retains all of its original shape and priority with four selected Crystal colors. Complete native limestone shows through the reviewed outside masks.',
}

def emit(review,guard=GUARD):
    contract=json.loads(guard.read_text())
    for game,joins in contract['joins'].items():
        for item in joins:
            layout=review.native_layout(game,item['map'])
            x,y,matrix=item['x'],item['y'],item['matrix']
            assert layout['pair']==PAIR
            actual=[layout['mids'][row*layout['width']+x:row*layout['width']+x+len(matrix[0])]
                    for row in range(y,y+len(matrix))]
            assert actual==matrix,('Sootopolis native service layout changed',game,item)
    gray=[[222,255,222],[173,173,173],[107,107,107],[58,58,58]]
    dark=[[189,189,255],[123,132,222],[74,82,189],[41,41,107]]
    floor=review.active_art('emerald',PAIR,729)['donor']
    field=ground_ref(review,'gen2')
    water=review.gb_ref('crystal','UNION_CAVE_1F',15,0)
    program=specification(review.cache,water,'program')
    assert program
    deep=copy.deepcopy(water)
    deep['palettes']=[copy.deepcopy(dark)for _ in range(8)]
    service={}
    for name in ('mart','center'):
        whole=Image.new('RGBA',(64,64))
        raw={}
        for y in range(4):
            for x in range(4):
                raw[x,y]=native_piece(review,'gen2',name,x,y)
                whole.paste(review.render(raw[x,y]),(x*16,y*16))
        outside=exterior(whole,set(review.gb_image(field).get_flattened_data())|{(222,255,222,255)})
        for (x,y),art in raw.items():
            mask=[(x*16+xx,y*16+yy)not in outside for yy in range(16)for xx in range(16)]
            service[name,x,y]=mask_piece(review,art,mask,floor,y<2)

    def parts_for(ref,bits):
        parts=[dict(donor=ref,srcX=p['x'],srcY=p['y'],**p)for p in runs([bit=='1'for bit in bits])]
        assert 1<=len(parts)<=32
        return parts
    def animate(art):
        art.update(animated=True,animation=program,animationCategory='water')
        return art
    def sea_with(parts,role):
        sea=dict(donor=water,x=0,y=0,w=16,h=16,animated=True)
        return animate(review.composite(None,[sea,*parts],role))

    records=[]
    for item in contract['cells']:
        game,mid=item['game'],item['mid']
        assert item['pair']==PAIR
        source=review.imp.cell_index(game)[PAIR,mid]
        assert source['pixel_sha256']==item['sourceHash']
        assert source['behavior']==item['sourceBehavior']
        assert source['layer_sha256']==item['sourceLayers']
        kind,plan=item['kind'],item.get('plan')
        role=f'reverse_gen2_sootopolis_routes_{kind}_{mid}'
        if kind=='floor':
            art=review.native(floor,role)
        elif kind=='house':
            art=review.active_art('emerald',PAIR,plan)
        elif kind=='service':
            art=copy.deepcopy(service[tuple(plan)])
        elif kind=='water':
            mask=item['mask']
            if mask=='1'*256:
                art=animate(review.native(deep,role))
            elif mask=='0'*256:
                art=animate(review.native(water,role))
            else:
                parts=parts_for(deep,mask)
                for part in parts:part['animated']=True
                art=sea_with(parts,role)
        elif kind=='rock':
            bid,q,shape=plan
            ref=review.gb_ref('crystal','UNION_CAVE_1F',bid,q)
            if shape=='gray':ref['palettes']=[copy.deepcopy(gray)for _ in range(8)]
            if item['mask']=='1'*256:
                art=review.native(ref,role)
            else:
                parts=parts_for(ref,item['mask'])
                art=sea_with(parts,role)if shape=='water'else review.composite(floor,parts,role)
        else:
            assert kind=='geometry'
            colors={tuple(x[:3]):tuple(x[3:])for x in item['colorMap']}
            art=classic_art(review,game,PAIR,mid,item['feature'],item['palette'],colors,role,ground=item['ground'])
        art['role']=role
        if kind!='geometry':art.setdefault('overMask','0'*256)
        row=review.row(game,PAIR,mid,'gen2',art,EVIDENCE[kind]+
                       ' Every source layer and behavior is verified. Native layouts, collision, height, encounters, movement, actors, events and entrances are preserved.')
        row['hoennOutdoorRemainingReview']=dict(kind=kind,source_family=PAIR,pixel_scale=1,
                                                contract_sha256=digest(item))
        records.append(dict(game=game,pair=PAIR,mid=mid,sourceHash=row['sourceHash'],
                            sourceBehavior=row['sourceBehavior'],compositionPixelHash=row['compositionPixelHash'],
                            occurrences=review.counts[game,PAIR,mid]))
    review.proofs['sootopolis_routes']=records
    return records
