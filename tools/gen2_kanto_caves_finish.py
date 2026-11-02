"""Finish GSC Kanto caves with exact source signatures and regional context.

Only one reviewed recipe with the same source tileset, four original tile IDs,
neutral pixels, collision, palette slots and priority can propagate. Regional
native cave palettes, object backgrounds and whole-block topology stay scoped.
"""
import argparse
import copy
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace

import catalog
import preview
import gen2_extended_review as review
import gen2_cave_review as cave
from center_mart_overhang_review import write_rows
from gen2_kanto_rooms_finish import canonical, native_artwork, source_signature, stable
from interior_review import Imports

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT/'mappings/gen2_kanto_caves_finish.lua'
OUT = ROOT.parent/'.work/tileshift-kanto-caves-finish'
SETS = {'TILESET_CAVE', 'TILESET_DARK_CAVE', 'TILESET_ICE_PATH'}
NATIVE_MAPS = {'MOUNT_MOON':'FR_MT_MOON_1F', 'DIGLETTS_CAVE':'FR_DIGLETTS_CAVE_B1F',
    'VICTORY_ROAD':'FR_VICTORY_ROAD_1F', 'ROCK_TUNNEL_1F':'FR_ROCK_TUNNEL_1F',
    'ROCK_TUNNEL_B1F':'FR_ROCK_TUNNEL_B1F'}


def regional_counterpart(seed, region, imports):
    """Explicit visually checked whole-shape equivalents, never ID equality."""
    if region[0]!='firered': return None
    art=native_artwork(seed)
    def ref(mid):
        record=imports.cell_index('firered')[region[1],mid]
        return dict(game='firered',tileset=region[1],id=mid,hash=record['pixel_sha256'])
    donor=art.get('donor',{})
    if donor.get('game')=='emerald' and donor.get('tileset')=='general__cave':
        # These are the complete oriented wall shapes seen side-by-side in
        # the actual native Mt Moon family and already reviewed Johto family.
        shapes={539:(667,'southwest inward wall corner'),540:(668,'southeast inward wall corner'),
            516:(644,'complete stone steps'),513:(641,'ordinary cave floor with original movement'),
            0:(0,'outside black void')}
        if donor['id'] in shapes:
            mid,role=shapes[donor['id']]
            return dict(kind='native',donor=ref(mid)),role
        if donor['id']==594:
            return dict(kind='native_composite',base=ref(641),parts=[dict(donor=ref(665),
                srcX=0,srcY=8,x=0,y=8,w=16,h=8)]),'lower-half wall front with complete original upper floor'
        if donor['id']==555:
            # FRLG's arch spans two cells. Use the already reviewed complete
            # one-cell native Emerald portal instead of clipping either half.
            return art,'complete native one-cell rock portal'
    base=art.get('base',{})
    if base.get('game')=='emerald' and base.get('tileset')=='general__cave':
        parts=art.get('parts',[])
        if base.get('id')==529 and len(parts)==1 and parts[0]['donor'].get('id')==601:
            art['base']=ref(657)
            return art,'complete native entrance-light header on regional raised stone'
        if base.get('id')==513 and len(parts)==1 and parts[0]['donor'].get('id')in(528,530):
            piece=parts[0];piece['donor']=ref(656 if piece['donor']['id']==528 else 658)
            art['base']=ref(641)
            return art,'original half-width oriented rock face on regional cave floor'
    return None


def explicit_remaining(source, region, imports):
    """Small original footprints reviewed in the complete Kanto cave maps."""
    raw,col=tuple(source['tiles']),source['collision']
    def ref(mid):
        record=imports.cell_index('firered')[region[1],mid]
        return dict(game='firered',tileset=region[1],id=mid,hash=record['pixel_sha256'])
    if raw==(1,1,1,1) and col in (160,161,163,164,165):
        return dict(kind='native',donor=ref(641)),'ordinary original cave floor retaining special movement'
    if raw==(16,16,16,16) and col==96:
        return dict(kind='native',donor=ref(646)),'complete native fall-warp hole'
    if raw==(1,1,38,38) and col==7:
        return dict(kind='native_composite',base=ref(641),parts=[dict(donor=ref(665),
            srcX=0,srcY=8,x=0,y=8,w=16,h=8)]),'original lower-half wall face and upper-half cave floor'
    if raw==(21,1,21,1) and col in (7,41):
        return dict(kind='native_composite',base=ref(641),parts=[dict(donor=ref(656),
            srcX=8,srcY=0,x=0,y=0,w=8,h=16)]),'original left-half rock face with full right-half floor'
    return None


def theme(row):
    ref = row.get('base') or row.get('donor') or row.get('parts', [{}])[0].get('donor', {})
    return ref.get('game'), ref.get('tileset')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate', action='store_true')
    parser.add_argument('--activate', action='store_true')
    parser.add_argument('--previews', action='store_true')
    args = parser.parse_args()
    assert not args.activate or args.validate
    OUT.mkdir(parents=True, exist_ok=True)
    cache = Path(os.environ['APPDATA'])/'pokemon-love2d'
    imports=Imports(cache,ROOT.parent/'.work/tileshift-catalog')
    manifest=imports.table('firered','gba/native/manifest')
    paths = list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]", (ROOT/'main.lua').read_text())))
    active = [r for path in paths if ROOT/path != TARGET for r in preview.read_reviewed(ROOT/path)]
    rows, held, stats, packed = [], [], [], {}
    for game in review.GAMES:
        data = review.source(cache, game)
        landmarks = catalog.read_lua(cache/game/'data/generated/landmarks.lua')
        threshold = landmarks['landmarks']['LANDMARK_PALLET_TOWN']['index']
        current_game = [r for r in active if r['game']==game and r.get('style')=='gen3' and r['tileset'] in SETS]
        pool = defaultdict(list)
        for row in current_game:
            if row.get('kind')=='source_palette': continue
            source = review.cell_info(cache, game, data, row['tileset'], row['id'], row['quadrant'])
            assert source['sourceHash']==row['sourceHash']
            pool[source_signature(source)].append(row)
        for name, definition in sorted(data['maps'].items()):
            if not isinstance(definition, dict) or definition.get('tileset') not in SETS: continue
            if definition.get('environment')!='CAVE' or definition.get('landmark', 0)<threshold: continue
            tileset = definition['tileset']
            current = [r for r in current_game if r['tileset']==tileset and r.get('map', name)==name]
            generic = {(r['id'],r['quadrant']) for r in current if r.get('x') is None}
            positions = {(r['id'],r['quadrant'],r['x'],r['y']) for r in current if r.get('x') is not None}
            themes = Counter(theme(r) for r in current if r.get('donor') or r.get('base'))
            region = themes.most_common(1)[0][0] if themes else None
            bases = {canonical(r['donor']) for r in current if r.get('donor')}
            gaps = defaultdict(list)
            for index, block in enumerate(definition['blocks']):
                for q in range(4):
                    x,y = index%definition['width']*2+q%2,index//definition['width']*2+q//2
                    if (block,q) not in generic and (block,q,x,y) not in positions: gaps[block,q].append([x,y])
            before = sum(map(len,gaps.values())); new = 0
            for (block,q), coordinates in sorted(gaps.items()):
                source = review.cell_info(cache,game,data,tileset,block,q)
                whole = catalog.lua_array(catalog.dict_at(data['sets'][tileset]['blocks'],block+1))
                matches = [r for r in pool[source_signature(source)]
                           if (not r.get('sourceWhole32Profile') or r['sourceWhole32Profile']==whole)
                           and (not region or theme(r)==region)
                           and (not r.get('base') or canonical(r['base']) in bases)]
                alternatives = defaultdict(list)
                for row in matches: alternatives[canonical(native_artwork(row))].append(row)
                explicit=None; direct_native=False
                if not alternatives and region and name in NATIVE_MAPS:
                    assert manifest['layouts'][NATIVE_MAPS[name]]['pair']==region[1]
                    converted=defaultdict(list)
                    for candidate in pool[source_signature(source)]:
                        if candidate.get('sourceWhole32Profile') and candidate['sourceWhole32Profile']!=whole:continue
                        result=regional_counterpart(candidate,region,imports)
                        if result:converted[canonical(result[0])].append((candidate,result[0],result[1]))
                    if len(converted)==1:
                        seed,art,semantic=min(next(iter(converted.values())),key=lambda v:(v[0].get('map',''),v[0]['id'],v[0]['quadrant']))
                        alternatives[canonical(art)]=[seed]
                        explicit=(art,semantic)
                    if not alternatives:
                        direct=explicit_remaining(source,region,imports)
                        if direct:
                            art,semantic=direct
                            seed=dict(game=game,map=name,tileset=tileset,id=block,quadrant=q,
                                sourceHash=source['sourceHash'],role='kanto_cave_'+semantic.replace(' ','_'))
                            alternatives[canonical(art)]=[seed]
                            explicit=direct;direct_native=True
                if len(alternatives)!=1:
                    held.append(dict(game=game,map=name,tileset=tileset,id=block,quadrant=q,
                        coordinates=coordinates,raw=source['tiles'],collision=source['collision'],
                        sourceHash=source['sourceHash'],regional_native_theme=region,
                        alternative_recipes=len(alternatives),reason='No unique exact-source recipe in this native regional cave context'))
                    continue
                seed = min(next(iter(alternatives.values())),key=lambda r:(r.get('map',''),r['id'],r['quadrant'],r['role']))
                checked = review.cell_info(cache,game,data,seed['tileset'],seed['id'],seed['quadrant'])
                assert source_signature(source)==source_signature(checked)
                row = dict(game=game,style='gen3',map=name,tileset=tileset,id=block,quadrant=q,
                    sourceHash=source['sourceHash'],sourceFiles=data['fingerprints'][tileset],sourceCells=coordinates,
                    sourceCollision=source['collision'],sourcePriority=[bool(a.get('priority')) for a in source['attributes']],
                    sourcePalettes=[a.get('palette',1) for a in source['attributes']],role=seed['role'],status='reviewed',
                    reviewedSeed=dict(game=game,map=seed.get('map'),tileset=seed['tileset'],id=seed['id'],
                        quadrant=seed['quadrant'],sourceHash=seed['sourceHash']),
                    evidence='Exact same cartridge, source cave tileset, all four original 8px tile IDs, neutral pixels, collision, '
                        'palette slots and priority match one reviewed native cave recipe in this map\'s existing regional palette. '
                        'Complete native object and wall sections remain at original pixel size; object bases and any whole-block '
                        'topology guards match. Source darkness/Flash, water and waterfall behavior, boulder rules, warps and scripts remain unchanged.')
                row.update(explicit[0] if explicit else native_artwork(seed))
                if explicit:
                    row['nativeContext']=dict(map=NATIVE_MAPS[name],pair=region[1],
                        counterpartRole=explicit[1],pixel_scale=1)
                    row['evidence']+=' Explicit regional counterpart: '+explicit[1]+'. Complete oriented native shapes were visually compared; native reference IDs were never treated as equivalents by coincidence.'
                    if direct_native:
                        row.pop('reviewedSeed')
                        row['reviewedSourceGeometry']=dict(tiles=source['tiles'],collision=source['collision'],pixel_scale=1)
                        row['evidence']='Visually reviewed actual source footprint and complete corresponding native FRLG cave family. '+row['evidence'].split('Explicit regional counterpart:',1)[1]
                if seed.get('sourceWhole32Profile'): row['sourceWhole32Profile']=copy.deepcopy(whole)
                row['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,row,packed,ROOT).tobytes())
                rows.append(stable(row));new+=len(coordinates)
            stats.append(dict(game=game,map=name,tileset=tileset,source_cells=definition['width']*definition['height']*4,
                prior_remaining_cells=before,new_cells=new,remaining_cells=before-new))
    summary = dict(rows=len(rows),new_cells=sum(len(r['sourceCells']) for r in rows),
        maps_with_new_cells=sum(s['new_cells']>0 for s in stats),newly_complete_maps=sum(s['new_cells']>0 and s['remaining_cells']==0 for s in stats),
        remaining_cells=sum(s['remaining_cells'] for s in stats),maps=stats)
    (OUT/'candidates.json').write_text(json.dumps(rows,indent=2)+'\n')
    (OUT/'held.json').write_text(json.dumps(held,indent=2)+'\n')
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    contacts=[]
    data=review.source(cache,'crystal')
    for r in held:
        if r['game']!='crystal':continue
        c=review.cell_info(cache,'crystal',data,r['tileset'],r['id'],r['quadrant'])
        contacts.append((str(len(contacts))+' '+r['map']+'\n'+str(r['raw'])+' col'+str(r['collision'])+'\n'+str(r['coordinates'][:4]),cave.source_image(cache,'crystal',data,c,data['maps'][r['map']])))
    if contacts:cave.contact(OUT/'held-crystal.png','Remaining Kanto cave cells; source artwork and actual positions',contacts)
    if args.previews:
        for name in ('MOUNT_MOON','DIGLETTS_CAVE','VICTORY_ROAD','ROCK_TUNNEL_1F','ROCK_TUNNEL_B1F'):
            preview.map_preview(cache,OUT,'crystal',name,name,active+rows,packed,2,ROOT)
    if args.validate:
        proof=review.validate_batch(rows,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=OUT),ROOT)
        proof.update({k:v for k,v in summary.items() if k!='maps'})
        (OUT/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
        if args.activate:write_rows(TARGET,rows)
    print(json.dumps({k:v for k,v in summary.items() if k!='maps'},indent=2))


if __name__=='__main__': main()
