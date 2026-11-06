"""Build reviewed Hoenn outdoor state transitions for the Crystal theme."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import struct
import zlib

import catalog
import preview
from classic_geometry_review import art as classic_art
from reverse_common import ReverseReview, ROOT
from reverse_gen2_cerulean_outdoor_completion import source_indices
from reverse_gen2_rse_field_states import GAMES, stable
from reverse_kanto_review import runs


GUARD = Path(__file__).with_name('reverse_gen2_rse_outdoor_states_guards.json')
OUTPUT = ROOT.parent / '.work/tileshift-v0430-rse-outdoor-states/replay'
COMPOSITION = ('kind', 'base', 'donor', 'parts', 'overMask', 'foreground', 'occludes',
               'animated', 'animation', 'animationCategory')
SECRET_VINE = {33: (181, 255, 115), 34: (82, 173, 25)}
COAST_ROCK = {5: (173, 173, 173), 6: (107, 107, 107), 7: (58, 58, 58)}


def source(review, game, pair, mid):
    row = review.imp.cell_index(game)[pair, mid]
    return source_indices(review, game, pair, mid, row)


def composition(row):
    return {k:copy.deepcopy(row[k]) for k in COMPOSITION if k in row}


def solid(review, rgb):
    donor=review.gb_ref('crystal','FAST_SHIP_CABINS_SE_SSE_CAPTAINS_CABIN',12,0)
    donor['palettes'] = [[list(rgb) for _ in range(4)] for _ in range(8)]
    assert set(review.gb_image(donor).get_flattened_data()) == {(*rgb,255)}
    return donor


def paint(review, base, masks, behind_actors=False):
    """Retain the complete existing Crystal backdrop and paint only known feature pixels."""
    art=composition(base)
    if art['kind']=='native':
        art['base']=art.pop('donor')
        art['kind']='native_composite'
        art['parts']=[]
    assert art['kind']=='native_composite'
    for rgb,mask in masks:
        donor=solid(review,rgb)
        art['parts'].extend(dict(donor=donor,**bounds) for bounds in runs(mask))
    assert 1<=len(art['parts'])<=32, (base['tileset'],base['id'],len(art['parts']))
    if behind_actors and art.get('overMask'):
        art['overMask']=''.join('0' if any(mask[i] for _,mask in masks) else bit for i,bit in enumerate(art['overMask']))
    return art


def preserve_rock_geometry(review, game, pair, mid, base, used, color_indices=None):
    old=base['classicGeometry']
    palette=tuple(map(tuple,old['palette']))
    colors={tuple(entry[:3]):tuple(entry[3:]) for entry in old['colorMap']}
    if color_indices:
        colors.update({used[index]:rgb for index,rgb in color_indices.items() if index in used})
    return classic_art(review,game,pair,mid,'rse_outdoor_stone_'+str(mid),palette,
                       {rgb:colors[rgb] for rgb in used.values()})


def deep_water(review, base, mid):
    art=composition(base)
    assert art['animated'] and art['animation']['kind']=='gb'
    # The existing native water timing and four synchronized quadrants are shared.
    for part in art['parts']:
        if not part.get('animated'):
            continue
        donor=part['donor']
        pals=donor.get('palettes') or preview.palette_set(review.imp.table('crystal','palettes'),
              review.imp.table('crystal','maps')[donor['map']],donor.get('daytime','DAY'))
        colors = ((173,214,247),(74,115,230),(16,32,148),(0,0,99)) if mid==334 else (
                  (140,189,230),(49,82,189),(8,16,115),(0,0,66))
        donor['palettes'] = [list(map(list,colors)) if index==3 else p for index,p in enumerate(pals)]
    return art


def recipe(review, item, base):
    game,pair,mid,feature=(item[k] for k in ('game','pair','mid','feature'))
    palette,planes=source(review,game,pair,mid)
    under=planes['under']
    used={i:palette[i] for layer,pixels in planes.items() for i in pixels if i or layer=='under'}
    if feature=='tree_vine':
        _,original=source(review,game,pair,base['id'])
        masks=[(rgb,[v==index and v!=old for v,old in zip(under,original['under'])]) for index,rgb in SECRET_VINE.items()]
        assert all(any(m) for _,m in masks)
        leaf={i for _,m in masks for i,value in enumerate(m) if value}
        # Keep the dark original vine backing wherever it touches a new leaf.
        stem=[v in (35,36) and v!=original['under'][i] and any(
            abs(i%16-j%16)+abs(i//16-j//16)==1 for j in leaf) for i,v in enumerate(under)]
        return paint(review,base,[((58,82,0),stem),*masks])
    if feature=='shrub_opening':
        mask=[v in (40,152) and 3<=i%16<=13 and 5<=i//16<=11 for i,v in enumerate(under)]
        assert sum(mask)>35
        return paint(review,base,[((41,41,33),mask)],behind_actors=True)
    if feature=='rock_opening':
        old={tuple(entry[:3]):tuple(entry[3:]) for entry in base['classicGeometry']['colorMap']}
        shades=sorted(set(old.values()),key=sum)
        dark,trim=shades[:2]
        mapping={56:dark,184:dark,62:trim,190:trim}
        return preserve_rock_geometry(review,game,pair,mid,base,used,mapping)
    if feature=='harbor_rocks':
        masks=[(rgb,[v==index for v in under]) for index,rgb in COAST_ROCK.items()]
        assert all(any(mask) for _,mask in masks)
        return paint(review,base,masks)
    if feature=='marine_dive':
        return deep_water(review,base,mid)
    if feature=='sky_pillar_door':
        return preserve_rock_geometry(review,game,pair,mid,base,used,{104:(58,58,58)})
    if feature=='route_103_cave':
        # Keep the complete existing cliff, then expose the real two-cell mouth.
        cavity=[v==56 for v in under]
        assert sum(cavity) in (60,158)
        return paint(review,base,[((25,25,25),cavity)],behind_actors=True)
    if feature=='sootopolis_door':
        # The barred behavior selects the same complete building door art.
        return composition(base)
    if feature=='shoal_salt':
        old=base['classicGeometry']
        shades=tuple(map(tuple,old['palette']))
        return preserve_rock_geometry(review,game,pair,mid,base,used,{130:shades[0],131:shades[1],132:shades[2]})
    assert feature=='shoal_shell'
    shades=((222,255,222),(197,148,58),(82,58,16),(41,82,165))
    ranks={99:0,100:1,101:2,114:0,116:1,117:1,118:2,119:2,120:0,121:0,122:3,123:3}
    return classic_art(review,game,pair,mid,'rse_shoal_cave_collectible_shell',shades,
                       {rgb:shades[ranks[i]] for i,rgb in used.items()})


def emit(review, baseline, guard):
    contract=json.loads(guard.read_text())
    assert contract['version']==1
    files={}
    for item in contract['nativeFiles']:
        game,file,expected=(item[k] for k in ('game','file','sha256'))
        raw=(review.cache/game/file).read_bytes()
        assert catalog.sha(raw)==expected,('Imported outdoor field-state file changed',game,file)
        files[game,file]=raw
    modules={}
    records=[]
    for item in contract['rows']:
        game,pair,mid,feature=(item[k] for k in ('game','pair','mid','feature'))
        native=review.imp.cell_index(game)[pair,mid]
        assert (native['pixel_sha256'],native['layer_sha256'],native['behavior'])==(
            item['sourceHash'],item['sourceLayers'],item['sourceBehavior'])
        for w in item['contexts']:
            layout=review.imp.table(game,'gba/native/manifest')['layouts'][w['map']]
            assert layout['pair']==pair
            raw=files[game,'data/generated/gba/native/'+layout['file']]
            raw=raw if raw[:4]==b'SVML' else zlib.decompress(raw)
            assert raw[:4]==b'SVML'
            sw,sh,w0,h0=struct.unpack_from('<HHHH',raw,6)
            x,y=w['x'],w['y'];assert 0<=x<(w0 or sw) and 0<=y<(h0 or sh)
            assert struct.unpack_from('<HBB',raw,16+2*raw[14]*raw[15]+4*(sw*y+x))==(
                w['before_mid'],w['source_collision'],w['elevation'])
        proof=item['base'];module=proof['module']
        if module not in modules:
            modules[module]={(r['game'],r['style'],r['tileset'],r['id']):r for r in preview.read_reviewed(baseline/module) if not r.get('map')}
        base=modules[module][game,'gen2',pair,proof['mid']]
        assert catalog.sha(stable(base).encode())==proof['sha256'],('Existing themed surround changed',proof)
        art=recipe(review,item,base);art['role']='reverse_gen2_rse_outdoor_'+feature
        row=review.row(game,pair,mid,'gen2',art,'Exact imported map event selects this whole alternate state. Its selected Crystal materials, source collision, actual position and native event timing are guarded.')
        row['rseOutdoorStateReview']=dict(feature=feature,baseMID=base['id'],contexts=item['contexts'])
        records.append(dict(game=game,pair=pair,mid=mid,feature=feature,compositionPixelHash=row['compositionPixelHash']))
    return records


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path,default=ROOT)
    parser.add_argument('--guard',type=Path,default=GUARD)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    args=parser.parse_args();args.output=args.output.resolve();args.output.mkdir(parents=True,exist_ok=True)
    review=ReverseReview('gen2-rse-outdoor-states',GAMES);review.out=args.output
    records=emit(review,args.baseline,args.guard)
    review.write(args.output/'candidate.lua')
    result=dict(rows=len(records),validation=review.validate(),records=records)
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='records'}))


if __name__=='__main__':main()
