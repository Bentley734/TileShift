"""Reviewed flat-water and street-material counterparts for remaining Kanto.

Only explicit source glyph/interaction pairs are selected. Shore corners and
whole buildings remain owned by their geometry reviews, never filled as water.
"""
import argparse,copy,json,os
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
import catalog,preview,gen2_extended_review as e
from johto_remaining_review import artwork
from center_mart_overhang_review import write_rows

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'.work/tileshift-gen2-kanto-water'
TARGET=ROOT/'mappings/gen2_kanto_water_finish.lua'
MARINE={'PALLET_TOWN','VERMILION_CITY','CINNABAR_ISLAND','ROUTE_11','ROUTE_12','ROUTE_13',
        'ROUTE_17','ROUTE_18','ROUTE_19','ROUTE_20','ROUTE_21','ROUTE_21_NORTH','ROUTE_21_SOUTH','ROUTE_26','ROUTE_27'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--validate',action='store_true');p.add_argument('--activate',action='store_true');a=p.parse_args();assert not a.activate or a.validate
    OUT.mkdir(parents=True,exist_ok=True);cache=Path(os.environ['APPDATA'])/'pokemon-love2d';packed={}
    active=[r for f in sorted((ROOT/'mappings').glob('*.lua'))if f!=TARGET for r in preview.read_reviewed(f)]
    rows=[];stats=[]
    for game in e.GAMES:
        data=e.source(cache,game);limit=catalog.read_lua(cache/game/'data/generated/landmarks.lua')['landmarks']['LANDMARK_PALLET_TOWN']['index']
        water=next(r for r in active if r['game']==game and r['role']=='coastal_ocean_water_interior'and r.get('animated')and r.get('donor',{}).get('game')=='firered')
        paving=next(r for r in active if r['game']==game and r['role']=='goldenrod_brick_road')
        for name,m in sorted(data['maps'].items()):
            if not isinstance(m,dict)or m.get('tileset')not in('TILESET_KANTO','TILESET_JOHTO')or m.get('environment')not in('TOWN','ROUTE')or 0<m.get('landmark',999)<limit:continue
            current=[r for r in active if r['game']==game and r['tileset']==m['tileset']and r.get('map',name)==name]
            generic={(r['id'],r['quadrant'])for r in current if r.get('x')is None};positions={(r['id'],r['quadrant'],r['x'],r['y'])for r in current if r.get('x')is not None}
            missing=defaultdict(list)
            for index,bid in enumerate(m['blocks']):
                for q in range(4):
                    x,y=index%m['width']*2+q%2,index//m['width']*2+q//2
                    if(bid,q)not in generic and(bid,q,x,y)not in positions:missing[bid,q].append([x,y])
            made=0
            for(bid,q),coordinates in missing.items():
                c=e.cell_info(cache,game,data,m['tileset'],bid,q);raw=tuple(c['tiles']);seed=None
                if raw==(20,20,20,20)and c['collision']==41:
                    seed=water;role='coastal_ocean_water_interior'if name in MARINE else'freshwater_pond_interior'
                    reason='The original full-cell water glyph and Surf interaction identify a plain surface, not a bank or waterfall. '
                    reason+='The native animated FireRed water retains all8 frames. Coastal sea contexts share the existing marine Mixed group; enclosed city ponds remain freshwater connected areas.'
                elif m['tileset']=='TILESET_KANTO'and raw==(91,91,91,91)and c['collision']==0:
                    seed=paving;role='kanto_native_brick_road'
                    reason='The original four matching horizontal masonry tiles form a walkable brick street. The already reviewed complete Gen3 brick paving is the matching native material, distinct from solid brick walls and roof tiles.'
                if seed is None:continue
                r=dict(game=game,style='gen3',map=name,tileset=m['tileset'],id=bid,quadrant=q,sourceCells=coordinates,
                    sourceHash=c['sourceHash'],sourceFiles=data['fingerprints'][m['tileset']],sourceCollision=c['collision'],
                    sourcePriority=[bool(z.get('priority'))for z in c['attributes']],sourcePalettes=[z.get('palette',1)for z in c['attributes']],
                    status='reviewed',role=role,evidence=reason+' Original collision, layout, source palette/priority metadata, interactions, encounters and events remain unchanged.')
                r.update(artwork(seed));r['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,r,packed,ROOT).tobytes());rows.append(r);made+=len(coordinates)
            if made:stats.append(dict(game=game,map=name,new_cells=made))
    (OUT/'candidates.json').write_text(json.dumps(rows,indent=2));(OUT/'summary.json').write_text(json.dumps(dict(rows=len(rows),cells=sum(len(r['sourceCells'])for r in rows),maps=len(stats),stats=stats),indent=2))
    if a.validate:
        proof=e.validate_batch(rows,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=OUT),ROOT)
        (OUT/'proof.json').write_text(json.dumps(proof,indent=2))
        if a.activate:write_rows(TARGET,rows)
    print(json.dumps(dict(rows=len(rows),cells=sum(len(r['sourceCells'])for r in rows),maps=len(stats))))

if __name__=='__main__':main()
