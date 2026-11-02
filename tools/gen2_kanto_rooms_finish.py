"""Propagate unique reviewed standard-room counterparts into Kanto in GSC.

Only the same cartridge, source tileset, original8px tile pattern, neutral
pixels, collision, palette slots and priority signature qualify. Native artwork is
copied from reviewed recipes; floor compatibility is checked before objects.
Ambiguous recipes and special room features are held for separate review.
"""
import argparse
import copy
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

import catalog
import preview
import gen2_extended_review as review
from center_mart_overhang_review import write_rows
from johto_remaining_review import artwork
from interior_review import Imports
from native_room_parts import RoomParts
from gen2_kanto_room_details import RoomDetails

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'mappings/gen2_kanto_rooms_finish.lua'
OUT = ROOT.parent / '.work/tileshift-kanto-rooms-finish'
TILESETS = {'TILESET_POKECENTER', 'TILESET_MART', 'TILESET_HOUSE',
            'TILESET_TRADITIONAL_HOUSE', 'TILESET_PLAYERS_HOUSE',
            'TILESET_PLAYERS_ROOM', 'TILESET_GATE'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def native_artwork(row):
    result = artwork(row)
    # Legacy direct-donor rows omit kind; they are the same native recipe as
    # an otherwise identical row explicitly labelled kind='native'.
    if result.get('donor') and result.get('kind') in (None, 'native'):
        result['kind'] = 'native'
    return result


def stable(value):
    if isinstance(value, dict):
        return {key: stable(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, list):
        return [stable(item) for item in value]
    return value


def background(row):
    return row.get('donor') if any(tag in row['role'] for tag in (
        'floor', 'wall', 'tatami', 'counter_top', 'counter_back', 'desk_surface', 'table_surface')) else None


def source_signature(cell):
    return cell['tileset'], tuple(cell['tiles']), review.identity(cell)


def room_class(name, tileset):
    # Different existing native designs intentionally distinguish ordinary
    # shops from department-store floors, roof gardens and lift cabins.
    if tileset == 'TILESET_MART':
        if name.endswith('_MART'): return 'mart'
        if name.endswith('_ROOF'): return 'department_roof'
        if name.endswith('_ELEVATOR'): return 'department_elevator'
        if '_DEPT_STORE_' in name: return 'department'
    return tileset


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate', action='store_true')
    parser.add_argument('--activate', action='store_true')
    parser.add_argument('--previews', action='store_true')
    args = parser.parse_args()
    assert not args.activate or args.validate, 'Activation requires source/donor validation'
    OUT.mkdir(parents=True, exist_ok=True)
    cache = Path(os.environ['APPDATA']) / 'pokemon-love2d'
    paths = list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]", (ROOT / 'main.lua').read_text())))
    active = [row for path in paths if (ROOT / path) != TARGET
              for row in preview.read_reviewed(ROOT / path)]
    # A separate native-size review may already have replaced a staircase in
    # this exact room with its authorized source-geometry palette fallback.
    # Preserve those scoped corrections rather than transplanting their floor
    # colors to other rooms or restoring the former reduced stair asset.
    preserved = {(r['game'], r.get('map'), r['tileset'], r['id'], r['quadrant']): r
                 for r in (preview.read_reviewed(TARGET) if TARGET.exists() else [])
                 if r.get('kind')=='source_palette' and r.get('nativeSizeOriginalAsset')}
    imports = Imports(cache, ROOT.parent/'.work/tileshift-catalog')
    indigo = RoomParts(imports, 'firered', 'FR_INDIGO_PLATEAU_POKEMON_CENTER_1F')
    department = RoomParts(imports, 'firered', 'FR_CELADON_CITY_DEPARTMENT_STORE_1F')
    details = RoomDetails(ROOT, cache, imports, active, {})
    all_added, held, maps_summary, packed = [], [], [], {}
    for game in ('gold', 'silver', 'crystal'):
        data = review.source(cache, game)
        landmarks = catalog.read_lua(cache / game / 'data/generated/landmarks.lua')
        limit = landmarks['landmarks']['LANDMARK_PALLET_TOWN']['index']
        current_game = [r for r in active if r.get('game') == game and r.get('style') == 'gen3']
        pool = defaultdict(lambda: defaultdict(list))
        exact_pool = defaultdict(lambda: defaultdict(list))
        for row in current_game:
            if row['tileset'] not in TILESETS or row.get('kind') == 'source_palette': continue
            art = native_artwork(row)
            if not art: continue
            cell = review.cell_info(cache, game, data, row['tileset'], row['id'], row['quadrant'])
            assert cell['sourceHash'] == row['sourceHash'], 'Reviewed source pixels changed'
            key = source_signature(cell)
            pool[key][canonical(art)].append(row)
            exact_pool[row['tileset'], row['id'], row['quadrant'], row['sourceHash']][canonical(art)].append(row)
        for name, definition in sorted(data['maps'].items()):
            if not isinstance(definition, dict) or definition.get('tileset') not in TILESETS: continue
            # The actual shared upstairs/link reception has landmark zero;
            # it is an active room rather than one of the unused beta aliases.
            if definition.get('landmark', 0) < limit and name not in ('POKECENTER_2F','TIME_CAPSULE','TRADE_CENTER','COLOSSEUM'): continue
            tileset = definition['tileset']
            current = [r for r in current_game if r['tileset'] == tileset and r.get('map', name) == name]
            generic = {(r['id'], r['quadrant']) for r in current if r.get('x') is None}
            positioned = {(r['id'], r['quadrant'], r['x'], r['y']) for r in current if r.get('x') is not None}
            gaps = defaultdict(list)
            for index, block in enumerate(definition['blocks']):
                for q in range(4):
                    x = index % definition['width'] * 2 + q % 2
                    y = index // definition['width'] * 2 + q // 2
                    if (block, q) not in generic and (block, q, x, y) not in positioned:
                        gaps[block, q].append([x, y])
            if not gaps: continue
            selected = {}; retained_fallbacks = set(); explicit_keys = set()
            for (block, q), coordinates in sorted(gaps.items()):
                source = review.cell_info(cache, game, data, tileset, block, q)
                prior = preserved.get((game, name, tileset, block, q))
                if prior and prior['sourceHash']==source['sourceHash']:
                    selected[block, q] = prior, source, coordinates
                    retained_fallbacks.add((block, q))
                    continue
                if name in ('TIME_CAPSULE','TRADE_CENTER','COLOSSEUM'):
                    # These landmark-zero rooms have the gate source graphics
                    # but a different actual native link-room material. Select
                    # their checked complete link-room modules before generic
                    # public-gate floor aliases can claim them.
                    source['files']=data['fingerprints'][tileset]
                    explicit=details.override(game,name,source,coordinates,data,definition)
                    if explicit:
                        seed=dict(game=game,map=name,tileset=tileset,id=block,quadrant=q,
                            sourceHash=source['sourceHash'],**explicit)
                        selected[block,q]=seed,source,coordinates;explicit_keys.add((block,q))
                        continue
                native = None
                if name=='INDIGO_PLATEAU_POKECENTER_1F':
                    raw = tuple(source['tiles'])
                    if raw==(61, 61, 61, 61) and source['collision']==7:
                        native = dict(kind='native', donor=indigo.ref(0),
                            role='kanto_indigo_clinic_outside_void',
                            reviewedNativeCounterpart=dict(game='firered', map=indigo.map,
                                role='black outside void surrounding the L-shaped clinic', pixel_scale=1))
                    elif block==44 and source['collision']==7 and raw==(
                            (92, 93, 94, 95) if q<2 else (94, 95, 42, 43)):
                        native = dict(kind='native_composite',
                            parts=indigo.rect(352+q%2*16, 136+q//2*16, 16, 16),
                            role='kanto_indigo_clinic_complete_stock_bookcase_'+str(q),
                            reviewedNativeCounterpart=dict(game='firered', map=indigo.map,
                                whole_native_rect=[352,136,32,32], source_quadrant=q,
                                role='complete native pharmacy stock bookcase', pixel_scale=1))
                if native:
                    seed = dict(game=game, map=name, tileset=tileset, id=block, quadrant=q,
                                sourceHash=source['sourceHash'], **native)
                    selected[block, q] = seed, source, coordinates
                    explicit_keys.add((block, q))
                    continue
                alternatives = exact_pool.get((tileset, block, q, source['sourceHash']), {})
                classified = {}
                for art_key, seeds in alternatives.items():
                    compatible = [r for r in seeds if room_class(r.get('map', ''), tileset) == room_class(name, tileset)]
                    if compatible: classified[art_key] = compatible
                if not classified:
                    for art_key, seeds in pool.get(source_signature(source), {}).items():
                        compatible = [r for r in seeds if room_class(r.get('map', ''), tileset) == room_class(name, tileset)]
                        if compatible: classified[art_key] = compatible
                if len(classified) != 1:
                    source['files']=data['fingerprints'][tileset]
                    explicit=details.override(game,name,source,coordinates,data,definition)
                    if explicit:
                        seed=dict(game=game,map=name,tileset=tileset,id=block,quadrant=q,
                            sourceHash=source['sourceHash'],**explicit)
                        selected[block,q]=seed,source,coordinates
                        explicit_keys.add((block,q))
                        continue
                    held.append(dict(game=game, map=name, tileset=tileset, id=block, quadrant=q,
                        coordinates=coordinates, reason='No unique reviewed same-source room-family recipe',
                        alternative_recipes=len(classified), sourceHash=source['sourceHash']))
                    continue
                seeds = next(iter(classified.values()))
                seed = min(seeds, key=lambda r: (r.get('map', ''), r.get('y', -1), r.get('x', -1), r['role']))
                checked = review.cell_info(cache, game, data, seed['tileset'], seed['id'], seed['quadrant'])
                assert review.identity(checked) == review.identity(source)
                if seed.get('sourceCollision') is not None: assert seed['sourceCollision'] == source['collision']
                if seed.get('sourcePalettes') is not None: assert seed['sourcePalettes'] == [v.get('palette', 1) for v in source['attributes']]
                if seed.get('sourcePriority') is not None: assert seed['sourcePriority'] == [bool(v.get('priority')) for v in source['attributes']]
                selected[block, q] = (seed, source, coordinates)
            for key,(seed,source,coordinates) in list(selected.items()):
                if (name=='MOUNT_MOON_GIFT_SHOP' and tuple(source['tiles'])==(17,17,17,17)):
                    source['files']=data['fingerprints'][tileset]
                    explicit=details.override(game,name,source,coordinates,data,definition)
                    assert explicit
                    seed=dict(game=game,map=name,tileset=tileset,id=key[0],quadrant=key[1],
                        sourceHash=source['sourceHash'],**explicit)
                    selected[key]=seed,source,coordinates;explicit_keys.add(key)
                elif details.book_context(name,coordinates):
                    seed=copy.deepcopy(seed);variants=[]
                    for x,y in coordinates:
                        art=details.book_art(x,y) if 7<=x<=8 and 9<=y<=10 else native_artwork(seed)
                        variants.append(dict(x=x,y=y,art=art))
                    seed['contextVariants']=variants
                    seed['reviewedNativeCounterpart']=dict(role='Complete native 32x32 book table with all caps, legs and book pages',pixel_scale=1)
                    selected[key]=seed,source,coordinates;explicit_keys.add(key)
                elif name=='MOUNT_MOON_GIFT_SHOP' and 'bookcase' in seed['role']:
                    seed=copy.deepcopy(seed);variants=[]
                    native_wall=details.imports.cell_index('firered')['pewter_gym',705]
                    native_floor=details.imports.cell_index('firered')['pewter_gym',704]
                    for x,y in coordinates:
                        art=native_artwork(seed)
                        mid,record=(705,native_wall) if y==0 else (704,native_floor)
                        art['base']=dict(game='firered',tileset='pewter_gym',id=mid,hash=record['pixel_sha256'])
                        details.remove_background_parts(art)
                        variants.append(dict(x=x,y=y,art=art))
                    seed.update(variants[0]['art']);seed['contextVariants']=variants
                    seed['reviewedNativeCounterpart']=dict(role='Complete native bookcase with literal background-only parts removed and actual wall/wood by position',pixel_scale=1)
                    selected[key]=seed,source,coordinates;explicit_keys.add(key)
            # The room's existing backgrounds and newly identified exact
            # floor/wall cells establish the allowed object bases. An unknown
            # or different background never inherits an unrelated room floor.
            background_refs = {canonical(ref): ref for row in current if (ref := background(row))}
            for seed, _, _ in selected.values():
                ref = background(seed)
                if ref and not seed.get('base'): background_refs[canonical(ref)] = ref
            added = []; floor_held = 0
            for (block, q), (seed, source, coordinates) in sorted(selected.items()):
                base = seed.get('base')
                selected_base = base
                base_equivalence = None
                declared_wall = (tileset=='TILESET_MART' and room_class(name, tileset) in ('department','department_elevator')
                    and seed['role'] in ('johto_shop_johto_house_complete_window',
                        'johto_shop_complete_floor_directory', 'johto_shop_lift_call_panel')
                    and source['collision']==7 and base==department.ref(643))
                if declared_wall:
                    # Celadon is the actual native source of this reviewed
                    # department-store wall/window family. Windows occupy the
                    # entire source wall band, leaving no separate plain-wall
                    # alias to establish its already known wall reference.
                    background_refs[canonical(base)] = base
                if base and canonical(base) not in background_refs:
                    base_pixels = preview.native_donor(cache, base, packed).tobytes()
                    equivalent = [(key, ref) for key, ref in background_refs.items()
                                  if preview.native_donor(cache, ref, packed).tobytes() == base_pixels]
                    if equivalent:
                        selected_base = min(equivalent)[1]
                        base_equivalence = catalog.sha(base_pixels)
                    elif selected_base==base:
                        selected_base = None
                if base and selected_base is None:
                    held.append(dict(game=game, map=name, tileset=tileset, id=block, quadrant=q,
                        coordinates=coordinates, reason='Reviewed object background does not match this room',
                        role=seed['role'], seed_map=seed.get('map'), base=base))
                    floor_held += len(coordinates)
                    continue
                if (block, q) in retained_fallbacks:
                    row = copy.deepcopy(seed)
                    row['sourceCells'] = coordinates
                    added.append(stable(row))
                    continue
                row = dict(game=game, style='gen3', map=name, tileset=tileset,
                    id=block, quadrant=q, sourceCells=coordinates,
                    sourceHash=source['sourceHash'], sourceFiles=data['fingerprints'][tileset],
                    sourceCollision=source['collision'],
                    sourcePalettes=[a.get('palette', 1) for a in source['attributes']],
                    sourcePriority=[bool(a.get('priority')) for a in source['attributes']],
                    role=seed['role'], status='reviewed',
                    reviewedSeed=dict(game=game, map=seed.get('map'), tileset=seed['tileset'],
                                      id=seed['id'], quadrant=seed['quadrant'], sourceHash=seed['sourceHash']),
                    evidence='Exact same cartridge, source room tileset, all four original8px tile IDs, neutral source pixels, '
                    'collision, palette slots and priority as the unique reviewed standard-room counterpart. '
                    'The native artwork and complete object sections are reused at their existing pixel size. '
                    'Object bases match this room\'s checked floor/wall references. Original geometry, collision, '
                    'warps, scripts and interactions remain unchanged; ambiguous or unmatched details are held.')
                row.update(native_artwork(seed))
                if (block, q) in explicit_keys:
                    row.pop('reviewedSeed', None)
                    row['reviewedNativeCounterpart'] = seed['reviewedNativeCounterpart']
                    row['evidence'] = ('Explicit complete native object modules or clearly labelled original-GSC geometry fallback '
                        'reviewed in the actual source room. Complete table caps, repeated surfaces, legs, chairs, beds and doorway frames '
                        'remain at their original pixel size. Original floor or wall pieces are replaced with this room\'s native backgrounds. '
                        'All actual source map positions, palette slots, priority and collision are fingerprinted. '
                        'No source geometry, collisions, warps, scripts or actor positions change.')
                    if seed['role'].startswith('kanto_indigo_clinic'):
                        row['evidence']+=' The actual native Indigo Plateau stock bookcase includes all four 16px sections of its complete32x32 shape, including the unaligned y=136 header cap.'
                    for key in ('originalGeometryFallback',):
                        if key in seed:row[key]=copy.deepcopy(seed[key])
                if base_equivalence:
                    row['base'] = selected_base
                    row.get('reviewedSeed',row.get('reviewedNativeCounterpart'))['equivalentRoomBasePixelHash'] = base_equivalence
                elif base and selected_base!=base:
                    row['base']=selected_base
                    row['reviewedRoomBaseOverride']=dict(reason='Complete native bookcase against this room\'s reviewed traditional lattice wall',base=selected_base)
                variants=seed.get('contextVariants')
                if variants:
                    for variant in variants:
                        placed=copy.deepcopy(row);placed.update(variant['art'],x=variant['x'],y=variant['y'],sourceCells=[[variant['x'],variant['y']]])
                        placed['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,placed,packed,ROOT).tobytes())
                        added.append(stable(placed))
                else:
                    row['compositionPixelHash'] = catalog.sha(preview.replacement_image(cache, row, packed, ROOT).tobytes())
                    added.append(stable(row))
            total_gaps = sum(map(len, gaps.values()))
            added_cells = sum(len(r['sourceCells']) for r in added)
            maps_summary.append(dict(game=game, map=name, tileset=tileset, source_cells=definition['width']*definition['height']*4,
                prior_remaining_cells=total_gaps, new_rows=len(added), new_cells=added_cells,
                remaining_cells=total_gaps-added_cells, floor_context_held_cells=floor_held))
            all_added.extend(added)
    details.write_provenance()
    (OUT / 'candidates.json').write_text(json.dumps(all_added, indent=2)+'\n')
    (OUT / 'held.json').write_text(json.dumps(held, indent=2)+'\n')
    summary = dict(rows=len(all_added), maps_with_new_cells=sum(m['new_cells']>0 for m in maps_summary),
        new_cells=sum(m['new_cells'] for m in maps_summary), newly_complete_maps=sum(m['remaining_cells']==0 for m in maps_summary),
        remaining_cells_in_target_rooms=sum(m['remaining_cells'] for m in maps_summary), held_aliases=len(held),
        by_tileset={t:dict(maps=sum(m['tileset']==t and m['new_cells']>0 for m in maps_summary),
                          new_cells=sum(m['new_cells'] for m in maps_summary if m['tileset']==t)) for t in sorted(TILESETS)},
        maps=maps_summary)
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    if args.previews:
        for name in ('CELADON_POKECENTER_1F', 'SAFFRON_POKECENTER_1F', 'CERULEAN_MART',
                     'CELADON_DEPT_STORE_1F', 'ROUTE_5_SAFFRON_GATE', 'BLUES_HOUSE', 'REDS_HOUSE_1F',
                     'POKECENTER_2F','POKEMON_FAN_CLUB','SOUL_HOUSE','TRAINER_HOUSE_1F','REDS_HOUSE_2F','MOUNT_MOON_GIFT_SHOP',
                     'TIME_CAPSULE','TRADE_CENTER','COLOSSEUM'):
            maps = catalog.read_lua(cache / 'crystal/data/generated/maps.lua')
            if name in maps: preview.map_preview(cache, OUT, 'crystal', name, name, active+all_added, packed, 3, ROOT)
    if args.validate:
        proof = review.validate_batch(all_added, SimpleNamespace(cache=cache, engine=ROOT.parent/'.tools/engine-0395', output=OUT), ROOT)
        proof.update(rows=len(all_added), new_cells=summary['new_cells'], newly_complete_maps=summary['newly_complete_maps'])
        (OUT / 'proof.json').write_text(json.dumps(proof, indent=2)+'\n')
        if args.activate: write_rows(TARGET, all_added)
    print(json.dumps({k:v for k,v in summary.items() if k!='maps'}, indent=2))


if __name__ == '__main__': main()
