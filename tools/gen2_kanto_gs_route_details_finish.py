"""Propagate the exact reviewed Crystal fishing-pier edges into GS Routes26/27."""
import argparse
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import catalog
import preview
import gen2_extended_review as review
from gen2_kanto_rooms_finish import source_signature, stable
from johto_remaining_review import artwork
from center_mart_overhang_review import write_rows

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'mappings/gen2_kanto_gs_route_details_finish.lua'
OUT=ROOT.parent/'.work/tileshift-gs-route-review'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate',action='store_true')
    parser.add_argument('--activate',action='store_true')
    args=parser.parse_args();assert not args.activate or args.validate
    OUT.mkdir(parents=True,exist_ok=True)
    cache=Path(os.environ['APPDATA'])/'pokemon-love2d';packed={}
    active=[r for path in (ROOT/'mappings').glob('*.lua')if path!=TARGET for r in preview.read_reviewed(path)]
    crystal=review.source(cache,'crystal');rows=[]
    for game in ('gold','silver'):
        data=review.source(cache,game)
        for name in ('ROUTE_26','ROUTE_27'):
            definition=data['maps'][name];ts=definition['tileset'];assert ts=='TILESET_JOHTO'
            water_positions=[]
            for index,block in enumerate(definition['blocks']):
                for q in range(4):
                    if review.cell_info(cache,game,data,ts,block,q)['collision']==41:
                        water_positions.append((index%definition['width']*2+q%2,index//definition['width']*2+q//2))
            bounds=[min(x for x,y in water_positions),min(y for x,y in water_positions),max(x for x,y in water_positions),max(y for x,y in water_positions)]
            for q in (0,1):
                source=review.cell_info(cache,game,data,ts,67,q)
                assert source['tiles']==[73,73,20,20] and source['collision']==41
                seeds=[r for r in active if r['game']=='crystal'and r.get('style')=='gen3'and r.get('map')==name
                    and r['tileset']==ts and r['id']==67 and r['quadrant']==q and r['role']=='johto_fishing_pier_edge']
                assert len(seeds)==1;seed=seeds[0]
                checked=review.cell_info(cache,'crystal',crystal,ts,seed['id'],seed['quadrant'])
                assert source_signature(source)==source_signature(checked)
                assert seed['sourceHash']==source['sourceHash'] and seed['sourceCollision']==source['collision']
                assert seed['sourcePalettes']==[a.get('palette',1)for a in source['attributes']]
                assert seed['sourcePriority']==[bool(a.get('priority'))for a in source['attributes']]
                assert seed['animated'] and seed['animation']['frames']==8 and seed['base']['game']=='firered'
                coordinates=[]
                for index,block in enumerate(definition['blocks']):
                    if block==67:coordinates.append([index%definition['width']*2+q%2,index//definition['width']*2+q//2])
                row=dict(game=game,style='gen3',map=name,tileset=ts,id=67,quadrant=q,sourceCells=coordinates,
                    sourceHash=source['sourceHash'],sourceFiles=data['fingerprints'][ts],sourceCollision=source['collision'],
                    sourcePalettes=[a.get('palette',1)for a in source['attributes']],sourcePriority=[bool(a.get('priority'))for a in source['attributes']],
                    role=seed['role'],status='reviewed',sourceOceanBounds=bounds,
                    reviewedSeed=dict(game='crystal',map=name,id=67,quadrant=q,sourceHash=checked['sourceHash']),
                    reviewedMarineExtent=dict(source_water_bounds=bounds,purpose='Coastal sea and pier edges follow the same connected marine Mixed style'),
                    evidence='Exact original fishing-pier edge: same source tileset, all four original8px tile IDs, neutral16px pixels, Surf collision, palette slots and priority match the already reviewed Crystal counterpart. '
                        'The complete existing pier overlay is retained over all eight native FireRed animated sea frames at1:1 pixels. '
                        'Actual Gold/Silver map positions and marine extent are fingerprinted; no building rows, source geometry, collision, encounters, events or scripts change.')
                row.update(copy.deepcopy(artwork(seed)))
                row['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,row,packed,ROOT).tobytes())
                rows.append(stable(row))
    summary=dict(rows=len(rows),new_cells=sum(len(r['sourceCells'])for r in rows),maps=4)
    (OUT/'route-candidates.json').write_text(json.dumps(rows,indent=2)+'\n')
    (OUT/'route-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    if args.validate:
        proof=review.validate_batch(rows,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=OUT),ROOT)
        proof.update(summary);(OUT/'route-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
        if args.activate:write_rows(TARGET,rows)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
