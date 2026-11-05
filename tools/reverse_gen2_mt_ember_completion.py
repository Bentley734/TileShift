"""Build the remaining Crystal Mt. Ember caves and Ember Spa counterparts."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import catalog
import preview
from classic_geometry_review import art as classic_art
from gb_theme_animation import specification
from reverse_gen2_kanto_final import Final, ROOT
from reverse_kanto_review import runs

GUARD = Path(__file__).with_name('reverse_gen2_mt_ember_guards.json')
TARGET = 'mappings/reverse_gen2_mt_ember_completion.lua'
OUTPUT = ROOT.parent / '.work/tileshift-v0360-mt-ember-completion'
PAIRS = {'firered':'general__rom_082d4fec','leafgreen':'general__rom_082d4fcc'}
EVIDENCE = {
    'boulder':'The complete native Crystal cave boulder uses its original silhouette over the matching floor, with clear outside corners.',
    'floor':'The complete native Crystal Union Cave floor matches the already selected walkable floor and ordinary gravel.',
    'plateau':'The complete native Crystal raised plateau glyph preserves the actual solid stone top.',
    'spa_pool':'The complete original Crystal water program shows the warm spring in the reviewed pale blue palette.',
    'spa_steps':'The whole native north-south stone tread material retains its original direction. The verified original water footprint shows animated Crystal spring water.',
    'geometry':'The named complete Mt. Ember feature retains exact source contour, engraved details and original priority planes in reviewed Crystal colors. Verified outside pixels show the matching native ground or water.',
}


def masked_parts(ref, mask):
    return [dict(donor=ref, srcX=part['x'], srcY=part['y'], **part)for part in runs([bit=='1'for bit in mask])]


def geometry_frame_proof(review, row, frames):
    """Check every backed phase directly from the source plane bytes and native donor."""
    spec = row['classicGeometry']
    ground = spec['ground']
    source_ref = dict(game=row['game'],tileset=row['tileset'],id=row['id'],hash=row['sourceHash'])
    original = {name:preview.native_donor(review.cache,source_ref,review.packed,[name],{name:digest}).get_flattened_data()
                for name,digest in spec['sourceLayers'].items()}
    colors = {tuple(entry[:3]):tuple(entry[3:])+(255,)for entry in spec['colorMap']}
    water = preview.replacement_frames(review.cache,dict(kind='native',donor=ground['donor'],animated=True,
                                      animation=ground['animation']),review.packed,ROOT)
    assert len(frames)==len(water)
    for frame,backing in zip(frames,water):
        expected=[None]*256
        pixels=backing.get_flattened_data()
        for name in ('under','mid','over'):
            if name not in original:
                continue
            mask=ground['masks'].get(name,'0'*256)
            for i,pixel in enumerate(original[name]):
                if pixel[3]:
                    expected[i]=pixels[i]if mask[i]=='1'else colors[pixel[:3]]
        assert tuple(expected)==tuple(frame.get_flattened_data()), (row['game'],row['id'],'independent spring phase mismatch')


def emit(review, guard=GUARD):
    floor = review.gb_ref('crystal','UNION_CAVE_1F',2,0)
    plateau = review.gb_ref('crystal','UNION_CAVE_1F',4,3)
    boulder = review.gb_ref('crystal','UNION_CAVE_1F',24,0)
    stairs = review.gb_ref('crystal','UNION_CAVE_1F',18,3)
    water = review.gb_ref('crystal','UNION_CAVE_1F',15,0)
    spa = copy.deepcopy(water)
    spa['palettes'] = [[[222,255,222],[181,197,255],[140,165,255],[82,107,206]]for _ in range(8)]
    program = specification(review.cache,spa,'program')
    assert program
    left = (6,4,3,2,1,1,1,0,0,0,0,0,0,1,1,2)
    right = (11,12,13,14,15,15,16,16,16,16,16,16,16,16,15,13)
    boulder_mask = ''.join('1'if left[y]<=x<right[y]else'0'for y in range(16)for x in range(16))
    proof = []
    for item in json.loads(guard.read_text()):
        game,pair,mid = (item[key]for key in ('game','pair','mid'))
        assert pair==PAIRS[game]
        source = review.imp.cell_index(game)[pair,mid]
        assert source['pixel_sha256']==item['sourceHash'] and source['layer_sha256']==item['sourceLayers']
        assert source['behavior']==item['sourceBehavior']
        key=(game,'gen2',pair,mid,None)
        assert key not in review.current
        occurrences=sum(x['count']for x in review.usage[game,pair,mid])
        assert occurrences==item['occurrences']>0
        kind=item['kind']
        feature=item.get('feature',kind)
        role=f'reverse_gen2_{feature}_{mid}'
        if kind=='geometry':
            mapping={tuple(entry[:3]):tuple(entry[3:])for entry in item['colorMap']}
            art=classic_art(review,game,pair,mid,feature,item['palette'],mapping,role,ground=item['ground'])
        elif kind=='boulder':
            art=review.composite(floor,masked_parts(boulder,boulder_mask),role)
        elif kind=='spa_steps':
            wet=dict(donor=spa,x=0,y=0,w=16,h=16,animated=True)
            art=review.composite(None,[wet,*masked_parts(stairs,item['mask'])],role)
        else:
            art=review.native({'floor':floor,'plateau':plateau,'spa_pool':spa}[kind],role)
        if kind!='geometry':
            art['overMask']='0'*256
        if kind in ('spa_steps','spa_pool'):
            art.update(animated=True,animation=program,animationCategory='water')
        row=review.row(game,pair,mid,'gen2',art,EVIDENCE[kind]+
                       ' Every original source layer, behavior, warp, collision, elevation and event is preserved.')
        row['mtEmberCompletionReview']=dict(feature=feature,pixelScale=1)
        record=dict(game=game,pair=pair,mid=mid,sourceHash=row['sourceHash'],sourceBehavior=row['sourceBehavior'],
                    compositionPixelHash=row['compositionPixelHash'],occurrences=occurrences)
        if row.get('classicGeometry',{}).get('ground',{}).get('animation'):
            frames=preview.classic_geometry_frames(review.cache,row,review.packed)
            geometry_frame_proof(review,row,frames)
            record['frames']=[catalog.sha(frame.tobytes())for frame in frames]
        elif kind in ('spa_steps','spa_pool'):
            frames=preview.replacement_frames(review.cache,row,review.packed,ROOT)
            assert len({im.tobytes()for im in frames})>1
            record['frames']=[catalog.sha(frame.tobytes())for frame in frames]
        if feature=='ruby_path_complete_braille_tablet_stone_and_engraved_dots':
            original=preview.native_donor(review.cache,dict(game=game,tileset=pair,id=mid,hash=row['sourceHash']),review.packed)
            positions=[i for i,pixel in enumerate(original.get_flattened_data())if pixel[:3]==(255,230,66)]
            output=review.render(row).get_flattened_data()
            assert positions and all(output[i]==(58,58,58,255)for i in positions)
            record['brailleDotPixels']=len(positions)
        proof.append(record)
    return proof


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--guard',type=Path,default=GUARD)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    args=parser.parse_args()
    args.output=args.output.resolve()
    args.output.mkdir(parents=True,exist_ok=True)
    review=Final()
    review.current={key:row for key,row in review.current.items()if review.origins[id(row)][0]!=TARGET}
    review.out=args.output
    records=emit(review,args.guard)
    review.write(args.output/'candidate.lua')
    validation=review.validate()
    report=dict(rows=len(records),new_cells=sum(x['occurrences']for x in records),
                frame_pixels=sum(256*len(x.get('frames',[]))for x in records),
                braille_dot_pixels=sum(x.get('brailleDotPixels',0)for x in records),validation=validation)
    (args.output/'new-keys.json').write_text(json.dumps(records,indent=2)+'\n')
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
