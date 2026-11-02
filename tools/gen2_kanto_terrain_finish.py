"""Extend reviewed outdoor counterparts only onto exact matching GSC source art.

This does not choose art by tile number or collision. Each accepted alias has
the same source tileset, neutral pixels, collision, flips/priority and palette
slots as an unambiguous reviewed terrain recipe. Buildings are held separately.
"""
import argparse
import copy
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace

import catalog
import preview
import gen2_extended_review as review
from johto_remaining_review import artwork
from center_mart_overhang_review import write_rows

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / '.work/tileshift-gen2-kanto-terrain'
TARGET = ROOT / 'mappings/gen2_kanto_terrain_finish.lua'
SETS = {'TILESET_JOHTO','TILESET_JOHTO_MODERN','TILESET_KANTO','TILESET_PARK','TILESET_FOREST'}
EXCLUDE = ('architecture','building','home','center','mart','gym','gate','station','theater','temple',
           'burned','lighthouse','bell','lab','barn','farmhouse','shrine','arcade','department','radio','florist',
           'closed','well','pagoda')


def recipe(row):
    result = artwork(row)
    for name in ('canopy','sourceOceanBounds'):
        if name in row: result[name] = copy.deepcopy(row[name])
    return result


def usable(row):
    return row['tileset'] in SETS and row.get('kind')!='source_palette' and not any(word in row['role'] for word in EXCLUDE)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate', action='store_true')
    parser.add_argument('--validate', action='store_true')
    args = parser.parse_args()
    assert not args.activate or args.validate
    OUT.mkdir(parents=True, exist_ok=True)
    cache = Path(os.environ['APPDATA']) / 'pokemon-love2d'
    active = [r for p in sorted((ROOT/'mappings').glob('*.lua')) if p!=TARGET for r in preview.read_reviewed(p)]
    added, held, stats, packed = [], [], [], {}
    for game in ('gold','silver','crystal'):
        data = review.source(cache, game)
        limit = catalog.read_lua(cache/game/'data/generated/landmarks.lua')['landmarks']['LANDMARK_PALLET_TOWN']['index']
        known = defaultdict(dict)
        for row in active:
            if row['game']!=game or not usable(row): continue
            cell = review.cell_info(cache, game, data, row['tileset'], row['id'], row['quadrant'])
            key = row['tileset'], review.identity(cell)
            art = recipe(row)
            # Water classification also controls Mixed mode, so equal-looking
            # sea/pond recipes are not silently treated as interchangeable.
            semantic = ('freshwater' if row['role'].startswith('freshwater') else 'ocean'
                        if 'coast' in row['role'] or row.get('sourceOceanBounds') else 'terrain')
            known[key][json.dumps([art,semantic],sort_keys=True)] = row
        for name, definition in sorted(data['maps'].items()):
            if not isinstance(definition,dict) or definition.get('tileset') not in SETS: continue
            if definition.get('environment') not in ('TOWN','ROUTE'): continue
            if 0 < definition.get('landmark',999) < limit: continue
            tileset = definition['tileset']
            current = [r for r in active if r['game']==game and r['tileset']==tileset and r.get('map',name)==name]
            generic = {(r['id'],r['quadrant']) for r in current if r.get('x') is None}
            positions = {(r['id'],r['quadrant'],r['x'],r['y']) for r in current if r.get('x') is not None}
            missing = defaultdict(list)
            grid = {}
            for index,bid in enumerate(definition['blocks']):
                for q in range(4):
                    x,y = index%definition['width']*2+q%2,index//definition['width']*2+q//2
                    c = review.cell_info(cache,game,data,tileset,bid,q); grid[x,y] = c
                    if (bid,q) not in generic and (bid,q,x,y) not in positions: missing[bid,q].append([x,y])
            made = 0
            for (bid,q), coordinates in missing.items():
                cell = review.cell_info(cache,game,data,tileset,bid,q)
                choices = known.get((tileset,review.identity(cell)),{})
                if len(choices)!=1:
                    held.append(dict(game=game,map=name,tileset=tileset,id=bid,quadrant=q,
                                     sourceHash=cell['sourceHash'],raw=cell['tiles'],collision=cell['collision'],
                                     coordinates=coordinates,reason='ambiguous' if choices else 'no reviewed terrain recipe'))
                    continue
                seed = next(iter(choices.values()))
                if seed['role'] in ('dense_conifer_crown','dense_conifer_trunk'):
                    partner = 'dense_conifer_trunk' if seed['role']=='dense_conifer_crown' else 'dense_conifer_crown'
                    dy = 1 if seed['role']=='dense_conifer_crown' else -1
                    complete = True
                    for x,y in coordinates:
                        neighbor = grid.get((x,y+dy))
                        candidates = known.get((tileset,review.identity(neighbor)),{}) if neighbor else {}
                        if len(candidates)!=1 or next(iter(candidates.values()))['role']!=partner: complete=False;break
                    if not complete:
                        held.append(dict(game=game,map=name,tileset=tileset,id=bid,quadrant=q,
                            coordinates=coordinates,reason='incomplete crown/trunk geometry'));continue
                row = dict(game=game,style='gen3',map=name,tileset=tileset,id=bid,quadrant=q,
                    sourceCells=coordinates,sourceHash=cell['sourceHash'],sourceFiles=data['fingerprints'][tileset],
                    sourceCollision=cell['collision'],sourcePriority=[bool(a.get('priority')) for a in cell['attributes']],
                    sourcePalettes=[a.get('palette',1) for a in cell['attributes']],role=seed['role'],status='reviewed',
                    reviewedSeed=dict(game=game,map=seed.get('map'),tileset=seed['tileset'],id=seed['id'],quadrant=seed['quadrant']),
                    evidence='Exact same source tileset, neutral pixels, interaction, per8px flips/priority and palette slots '
                    'as one unambiguous already-reviewed outdoor counterpart. Actual original coordinates recorded; '
                    'paired narrow trees retain complete adjacent crown/root geometry. Buildings and ambiguous variants '
                    'are deferred. Original collision, layout, map connections, encounters, scripts and events are unchanged.')
                row.update(recipe(seed))
                row['compositionPixelHash'] = catalog.sha(preview.replacement_image(cache,row,packed,ROOT).tobytes())
                added.append(row);made += len(coordinates)
            stats.append(dict(game=game,map=name,added_cells=made,remaining_cells=sum(len(z['coordinates']) for z in held if z['game']==game and z['map']==name)))
    (OUT/'candidates.json').write_text(json.dumps(added,indent=2))
    (OUT/'held.json').write_text(json.dumps(held,indent=2))
    summary = dict(rows=len(added),cells=sum(len(r['sourceCells']) for r in added),maps=len(stats),
                   completed_maps=sum(s['remaining_cells']==0 for s in stats),roles=dict(Counter(r['role'] for r in added)),stats=stats)
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2))
    if args.validate:
        proof = review.validate_batch(added,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=OUT),ROOT)
        (OUT/'proof.json').write_text(json.dumps(proof,indent=2))
        if args.activate: write_rows(TARGET,added)
    print(json.dumps({k:v for k,v in summary.items() if k not in ('roles','stats')}))


if __name__=='__main__': main()
