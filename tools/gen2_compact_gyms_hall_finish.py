"""Review the compact GSC Pewter/Seafoam gyms and Hall of Fame at 1:1."""
import argparse
import copy
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
from PIL import Image

import catalog
import preview
import gen2_extended_review as review
from center_mart_overhang_review import write_rows
from gen2_kanto_rooms_finish import canonical, native_artwork, source_signature, stable
from interior_review import Imports
from native_room_parts import RoomParts

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'mappings/gen2_compact_gyms_hall_finish.lua'
OUT=ROOT.parent/'.work/tileshift-compact-gyms-hall-finish'
DEST=ROOT/'assets/third_party/native-kanto-interiors'
MAPS=('PEWTER_GYM','SEAFOAM_GYM','HALL_OF_FAME')
STEEL=[[240,248,240],[168,192,208],[88,112,152],[48,56,80]]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate',action='store_true')
    parser.add_argument('--activate',action='store_true')
    parser.add_argument('--previews',action='store_true')
    args=parser.parse_args();assert not args.activate or args.validate
    OUT.mkdir(parents=True,exist_ok=True)
    cache=Path(os.environ['APPDATA'])/'pokemon-love2d'
    imports=Imports(cache,ROOT.parent/'.work/tileshift-catalog')
    pewter=RoomParts(imports,'firered','FR_PEWTER_CITY_GYM')
    hall=RoomParts(imports,'firered','FR_POKEMON_LEAGUE_HALL_OF_FAME')
    paths=list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(ROOT/'main.lua').read_text())))
    active=[r for path in paths if ROOT/path!=TARGET for r in preview.read_reviewed(ROOT/path)]
    packed={};rows=[];held=[];stats=[]
    wood=pewter.ref(682)
    # These complete native sculptures occupy exactly 16x16 and 16x32.
    # Remove only their old exterior floor colors, preserving every gray
    # sculpture pixel and leaving the chosen wood continuous underneath.
    native_soil=preview.native_donor(cache,pewter.ref(660),packed)
    native_wood=preview.native_donor(cache,wood,packed)
    exterior_colors=set(native_soil.get_flattened_data())|set(native_wood.get_flattened_data())
    pewter_art={};provenance=[]
    native_pewter=imports.gba('firered',pewter.map)[0]
    DEST.mkdir(parents=True,exist_ok=True)
    for role,sx,sy in (('fixed_rock',64,80),('complete_statue_head',64,176),('complete_statue_plinth',64,192)):
        original=native_pewter.crop((sx,sy,sx+16,sy+16))
        pixels=[pixel if pixel not in exterior_colors else (0,0,0,0) for pixel in original.get_flattened_data()]
        cutout=Image.new('RGBA',(16,16));cutout.putdata(pixels)
        assert all(before==after for before,after in zip(original.get_flattened_data(),cutout.get_flattened_data()) if after[3])
        path=DEST/('firered-pewter-'+role.replace('_','-')+'.png');cutout.save(path)
        pewter_art[role]=dict(kind='third_party',base=wood,asset=path.relative_to(ROOT).as_posix(),
            assetFileHash=catalog.sha(path.read_bytes()),credit='Pokemon FireRed / Game Freak; exact native import pixels with exterior floor removed.',
            sourceUrl='https://github.com/pret/pokefirered')
        provenance.append(dict(asset=path.relative_to(ROOT).as_posix(),assetFileHash=catalog.sha(path.read_bytes()),
            game='firered',map=pewter.map,pair=pewter.pair,native_rect=[sx,sy,16,16],
            source_layout_hash=pewter.layout['file_sha256'],pixel_scale=1,dimensions=[16,16],
            original_rgba_hash=catalog.sha(original.tobytes()),cutout_rgba_hash=catalog.sha(cutout.tobytes()),
            retained_pixels=sum(pixel[3]>0 for pixel in pixels),
            exact_retained_native_pixels=True,removed_only_native_soil_or_wood_exterior_palette=True))
    (DEST/'provenance.json').write_text(json.dumps(dict(origin='Exact complete native FRLG Pewter Gym sculptures; no generated artwork or scaling.',assets=provenance),indent=2)+'\n')
    hall_floor=preview.native_donor(cache,hall.ref(688),packed)
    assert len(set(hall_floor.get_flattened_data()))==1
    green=list(hall_floor.getpixel((0,0))[:3]);flat_green=[green]*4
    for game in review.GAMES:
        data=review.source(cache,game)
        # Johto's reviewed warm-rock family is the correct material for
        # Blaine's bare cave gym. The FRLG Seafoam ice family was inspected
        # and deliberately rejected because this GSC room is not frozen.
        cave_pool=defaultdict(lambda:defaultdict(list))
        for seed in active:
            if seed['game']!=game or seed.get('style')!='gen3' or seed['tileset']!='TILESET_CAVE':continue
            art=native_artwork(seed);ref=art.get('base')or art.get('donor')or{}
            if ref.get('game')!='emerald' or ref.get('tileset')!='general__cave':continue
            source=review.cell_info(cache,game,data,seed['tileset'],seed['id'],seed['quadrant'])
            assert source['sourceHash']==seed['sourceHash']
            cave_pool[source_signature(source)][canonical(art)].append(seed)
        for name in MAPS:
            definition=data['maps'][name];tileset=definition['tileset'];occ=defaultdict(list)
            for index,block in enumerate(definition['blocks']):
                for q in range(4):occ[block,q].append([index%definition['width']*2+q%2,index//definition['width']*2+q//2])
            new=0
            for (block,q),coordinates in sorted(occ.items()):
                source=review.cell_info(cache,game,data,tileset,block,q);raw=tuple(source['tiles']);col=source['collision']
                art=None;role=None;extra={}
                if name=='PEWTER_GYM':
                    if raw==(2,2,2,2) and col==0:art=dict(kind='native',donor=wood);role='original_wood_floor'
                    elif raw==(4,5,20,21) and col==7:art=copy.deepcopy(pewter_art['fixed_rock']);role='fixed_rock'
                    elif raw==(34,35,50,51) and col==7:art=copy.deepcopy(pewter_art['complete_statue_head']);role='complete_statue_head'
                    elif raw==(38,39,54,55) and col==7:art=copy.deepcopy(pewter_art['complete_statue_plinth']);role='complete_statue_plinth'
                    elif raw in ((7,8,23,24),(8,9,24,25)) and col==112:
                        offset=0 if raw[0]==7 else 16
                        art=dict(kind='native_composite',parts=pewter.rect(88+offset,224,16,16));role='complete_exit_mat_'+str(offset//16)
                    extra=dict(nativeContext=dict(map=pewter.map,layoutFileHash=pewter.layout['file_sha256'],pixel_scale=1))
                elif name=='SEAFOAM_GYM':
                    alternatives=cave_pool[source_signature(source)]
                    if len(alternatives)==1:
                        seed=min(next(iter(alternatives.values())),key=lambda r:(r.get('map',''),r['id'],r['quadrant']))
                        if not seed.get('sourceWhole32Profile') or seed['sourceWhole32Profile']==catalog.lua_array(catalog.dict_at(data['sets'][tileset]['blocks'],block+1)):
                            art=native_artwork(seed);role=seed['role']
                            extra=dict(reviewedSeed=dict(map=seed.get('map'),tileset=seed['tileset'],id=seed['id'],quadrant=seed['quadrant'],sourceHash=seed['sourceHash']))
                            if seed.get('sourceWhole32Profile'):extra['sourceWhole32Profile']=seed['sourceWhole32Profile']
                elif name=='HALL_OF_FAME':
                    if raw==(12,13,28,29) and col in (0,112):art=dict(kind='native',donor=hall.ref(688));role='native_hall_floor'
                    elif raw==(38,39,54,55) and col==7:art=dict(kind='native',donor=hall.ref(678));role='complete_native_registration_console_top'
                    elif raw==(69,70,28,29) and col==0:art=dict(kind='native',donor=hall.ref(686));role='complete_native_registration_console_bottom'
                    elif set(raw)<={12,13,14,15,28,29,30,31,40,41,44,45,46,47,56,57,62,63,71,72,73,74,75,76,77,78,79,82,83,84,85,86,87,88,89,90,91,92,93,94,95}:
                        # The original GSC recording dais/steel-wall assembly
                        # has no complete native module in its 64x48 footprint.
                        # Keep every detail at 1:1 with the authorized fallback;
                        # all old floor-only 8px tiles become exactly the new
                        # flat native hall-floor color, including its corners.
                        colors=[copy.deepcopy(flat_green if tile in (12,13,28,29) else STEEL) for tile in raw]
                        art=dict(kind='source_palette',sourceColors=colors,credit='Original Pokemon Gold/Silver/Crystal / Game Freak; palette recolor only.',sourceUrl='https://github.com/pret/pokecrystal')
                        role='original_geometry_recording_dais_and_steel_wall'
                        extra['originalGeometryFallback']=dict(reason='Unique GSC recording dais and associated steel wall; complete native FRLG machine has different geometry',pixel_scale=1,native_palette_reference=hall.map)
                    extra['nativeContext']=dict(map=hall.map,layoutFileHash=hall.layout['file_sha256'],pixel_scale=1)
                if not art:
                    held.append(dict(game=game,map=name,id=block,quadrant=q,raw=source['tiles'],collision=col,coordinates=coordinates));continue
                row=dict(game=game,style='gen3',map=name,tileset=tileset,id=block,quadrant=q,sourceCells=coordinates,
                    sourceHash=source['sourceHash'],sourceFiles=data['fingerprints'][tileset],sourceCollision=col,
                    sourcePalettes=[a.get('palette',1)for a in source['attributes']],sourcePriority=[bool(a.get('priority'))for a in source['attributes']],
                    role='kanto_special_'+role,status='reviewed',
                    evidence='Actual named-room native FRLG counterparts or the exact reviewed warm-rock Johto cave family, matched by complete source geometry and semantics. '
                        'All objects remain at original pixel size; complete statue/console pairs and the entire native 32px entrance mat are retained. '
                        'Only exterior floor pixels are omitted around sculptures so the correct room floor continues behind them. '
                        'The unique GSC Hall of Fame recording dais and steel-wall assembly use the clearly labelled authorized original-geometry Gen3 palette fallback; '
                        'its floor-only 8px pieces exactly match the native new floor. Original collision, warps, scripts and actor placement remain unchanged.')
                row.update(art);row.update(extra)
                row['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,row,packed,ROOT).tobytes())
                rows.append(stable(row));new+=len(coordinates)
            stats.append(dict(game=game,map=name,total_cells=definition['width']*definition['height']*4,new_cells=new,remaining_cells=definition['width']*definition['height']*4-new))
    summary=dict(rows=len(rows),new_cells=sum(len(r['sourceCells'])for r in rows),maps=stats,remaining_cells=sum(s['remaining_cells']for s in stats))
    (OUT/'candidates.json').write_text(json.dumps(rows,indent=2)+'\n')
    (OUT/'held.json').write_text(json.dumps(held,indent=2)+'\n')
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    if args.previews:
        for name in MAPS:preview.map_preview(cache,OUT,'crystal',name,name,active+rows,packed,4,ROOT)
    if args.validate:
        proof=review.validate_batch(rows,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=OUT),ROOT)
        proof.update(rows=len(rows),new_cells=summary['new_cells'],remaining_cells=summary['remaining_cells'])
        (OUT/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
        if args.activate:write_rows(TARGET,rows)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
