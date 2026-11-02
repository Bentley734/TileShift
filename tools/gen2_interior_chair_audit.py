"""Offline source/context audit of every Gen2 interior seat and paired desk."""
import argparse
import copy
import json
import os
import re
import zlib
from collections import Counter,defaultdict
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

import catalog
import preview
import gen2_extended_review as review
from gen2_chair_context_review import current_facing,target_kind
from interior_review import Imports
from native_room_parts import RoomParts
from newbark_building_review import lua

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'.work/tileshift-v0303-chair-audit'
MODULE='mappings/gen2_interior_chair_audit.lua'
SOURCE_FIELDS=('game','tileset','id','quadrant','sourceHash','sourceFiles','sourceCollision','sourcePalettes','sourcePriority')


def seat_related(row):
    role=row['role']
    return any(word in role for word in('chair','stool','seat','cushion','lounge','bench','sofa','school_desk','teacher_desk','student_desk'))


def load_rows():
    names=list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(ROOT/'main.lua').read_text())))
    groups=defaultdict(list);rows=[];module_rows={}
    for name in names:
        if name==MODULE:continue
        batch=catalog.plain(catalog.LUA.execute((ROOT/name).read_text()))
        if batch=={}:batch=[]
        module_rows[name]=batch
        for index,row in enumerate(batch):
            rows.append(row)
            if row.get('game')in review.GAMES and row.get('style')=='gen3':
                groups[row['game'],row['tileset']].append((row,name,index))
    return names,groups,rows,module_rows


def resolve(groups,game,name,definition):
    generic={};positioned={}
    for row,module,index in groups[game,definition['tileset']]:
        if row.get('map',name)!=name:continue
        key=row['id'],row['quadrant']
        if row.get('x')is None:generic[key]=(row,module,index)
        else:positioned[key+(row['x'],row['y'])]=(row,module,index)
    cells={}
    for index,block in enumerate(definition['blocks']):
        for q in range(4):
            x,y=index%definition['width']*2+q%2,index//definition['width']*2+q//2
            value=positioned.get((block,q,x,y),generic.get((block,q)))
            if value:cells[x,y]=value
    return cells


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contacts',action='store_true')
    parser.add_argument('--author',action='store_true')
    args=parser.parse_args();OUT.mkdir(exist_ok=True,parents=True)
    cache=Path(os.environ['APPDATA'])/'pokemon-love2d'
    names,groups,all_rows,module_rows=load_rows()
    inventory=[];maps=[];roles=Counter();packed={};environments=Counter()
    for game in review.GAMES:
        data=review.source(cache,game)
        for name,definition in sorted(data['maps'].items()):
            if not isinstance(definition,dict)or definition.get('environment')not in('INDOOR','GATE','DUNGEON','CAVE'):continue
            environments[definition['environment']]+=1
            cells=resolve(groups,game,name,definition)
            selected=[]
            for pos,(row,module,index)in sorted(cells.items()):
                if not seat_related(row):continue
                neighbors=[]
                for direction,dx,dy in(('east',1,0),('west',-1,0),('north',0,-1),('south',0,1)):
                    other=cells.get((pos[0]+dx,pos[1]+dy))
                    if other:neighbors.append(dict(direction=direction,position=[pos[0]+dx,pos[1]+dy],role=other[0]['role']))
                actors=[copy.deepcopy(obj)for obj in definition.get('objects',[])if abs(obj['x']-pos[0])+abs(obj['y']-pos[1])<=1]
                record=dict(game=game,map=name,position=list(pos),module=module,index=index+1,role=row['role'],
                    neighbors=neighbors,nearby_original_actors=actors,row=copy.deepcopy(row))
                inventory.append(record);selected.append(record);roles[row['role']]+=1
            if selected:
                maps.append(dict(game=game,map=name,seats=len(selected),positions=[r['position']for r in selected],
                    roles=dict(Counter(r['role']for r in selected))))
                if args.contacts and game=='crystal':
                    preview.map_preview(cache,OUT,game,name,name,all_rows,packed,2,ROOT)
    (OUT/'inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
    (OUT/'maps.json').write_text(json.dumps(maps,indent=2)+'\n')
    summary=dict(seat_related_cells=len(inventory),maps=len(maps),interior_maps_scanned=sum(environments.values()),environments=dict(environments),roles=dict(roles),
        crystal_maps=[r for r in maps if r['game']=='crystal'])
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    if args.author:author(cache,inventory,names,groups,all_rows,module_rows)
    print(json.dumps(summary,indent=2))


def author(cache,inventory,names,groups,all_rows,module_rows):
    """Emit source-scoped seat-only overrides; production modules stay untouched."""
    imp=Imports(cache,ROOT.parent/'.work/tileshift-catalog');packed={};sources={g:review.source(cache,g)for g in review.GAMES}
    office=RoomParts(imp,'firered','FR_SILPH_CO_1F');dojo=RoomParts(imp,'firered','FR_SAFFRON_CITY_DOJO')
    casino=RoomParts(imp,'firered','FR_CELADON_CITY_GAME_CORNER');shop=RoomParts(imp,'firered','FR_CELADON_CITY_DEPARTMENT_STORE_1F')
    idx=imp.cell_index('firered')
    def part(ref,sy=0,h=16,y=0):
        record=imp.cell_index(ref['game'])[ref['tileset'],ref['id']]
        return dict(donor=copy.deepcopy(ref),layers=['mid'],layerHashes={'mid':record['layer_sha256']['mid']},srcX=0,srcY=sy,w=16,h=h,x=0,y=y)
    def layer(ref):
        p=part(ref)
        return preview.native_donor(cache,ref,packed,p['layers'],p['layerHashes'])
    # Exact native Emerald object-event168: ROUND_CUSHION, one16x16 frame.
    ow=cache/'emerald/data/generated/gba/ow';meta=imp.table('emerald','gba/ow/manifest')['sprites']['168']
    assert(meta['width'],meta['height'],meta['frameCount'])==(16,16,1)
    rgba=zlib.decompress((ow/'168.rgba').read_bytes());assert len(rgba)==1024
    asset_dir=ROOT/'assets/third_party/native-interior-seats';asset_dir.mkdir(exist_ok=True)
    cushion=asset_dir/'emerald-round-floor-cushion16.png';Image.frombytes('RGBA',(16,16),rgba).save(cushion)
    asset_hash=catalog.sha(cushion.read_bytes())
    provenance=dict(files={cushion.name:asset_hash},sources=[dict(asset=cushion.name,game='emerald',native_object_graphics_id=168,
        native_name='OBJ_EVENT_GFX_ROUND_CUSHION',source='Original native Emerald imported ow/168.rgba',source_file_sha256=catalog.sha((ow/'168.rgba').read_bytes()),
        source_metadata_sha256=catalog.sha((ow/'168.meta').read_bytes()),rgba_sha256=catalog.sha(rgba),width=16,height=16,
        extraction='Complete native RGBA frame; no crop, rotation, resizing, recolor or new pixels',credit='Original Pokemon Emerald / Game Freak',sourceUrl='https://github.com/pret/pokeemerald')])
    (asset_dir/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    # Actual native left-wall lounge at0,9..11. Only duplicate upholstery
    # rows are omitted; its complete cap and all opaque foot pixels survive.
    assert [shop.layout['mids'][y*shop.layout['width']]for y in(9,10,11)]==[790,798,806]
    body=layer(shop.ref(798));foot=layer(shop.ref(806))
    signatures=[body.crop((0,y,16,y+1)).tobytes()for y in range(16)]
    kept=list(range(6))+[14,15]
    assert all(signatures[y]in{signatures[k]for k in kept}for y in range(16))
    assert foot.getchannel('A').crop((0,8,16,16)).getbbox()is None
    lounge_head=[part(shop.ref(790))]
    lounge_foot=[part(shop.ref(798),0,6,0),part(shop.ref(798),14,2,6),part(shop.ref(806),0,8,8)]
    resolved={};new=[];removals={};decisions=[];classifications=Counter();facing_errors=[]
    north_asset=ROOT/'assets/third_party/native-kanto-chairs/north-blue.png'
    south_ref=dict(game='firered',tileset='building__rom_082d4f44',id=741,hash=idx['building__rom_082d4f44',741]['pixel_sha256'])
    floor_roles={'johto_radio_public_floor','johto_radio_recording_room_wood_floor'}
    def room_cells(game,name):
        k=game,name
        if k not in resolved:resolved[k]=resolve(groups,game,name,sources[game]['maps'][name])
        return resolved[k]
    def radio_floor(record):
        cells=room_cells(record['game'],record['map']);origin=tuple(record['position']);front={origin};seen={origin}
        for distance in range(1,6):
            following=set();found=[]
            for x,y in front:
                for dx,dy in((1,0),(-1,0),(0,1),(0,-1)):
                    pos=x+dx,y+dy
                    if pos in seen or pos not in cells:continue
                    seen.add(pos);r=cells[pos][0]
                    if r['role']in floor_roles and r.get('donor'):
                        found.append((pos,r))
                    if r.get('sourceCollision')==0:following.add(pos)
            if found:
                refs={json.dumps(r['donor'],sort_keys=True)for _,r in found}
                if len(refs)>1:
                    # At the studio/service-corridor edge, the actual source
                    # seat's floor subtiles retain the room palette. Combine
                    # that evidence with adjacent reviewed floor cells.
                    score=lambda r:sum(p in r['sourcePalettes']for p in record['row']['sourcePalettes'])
                    maximum=max(score(r)for _,r in found)
                    found=[(pos,r)for pos,r in found if score(r)==maximum]
                    refs={json.dumps(r['donor'],sort_keys=True)for _,r in found}
                assert len(refs)==1,(record['game'],record['map'],origin,found)
                pos,row=found[0]
                return copy.deepcopy(row['donor']),dict(sourceFloorPosition=list(pos),sourceFloorHash=row['sourceHash'],distance=distance,role=row['role'],
                    sourceSeatPalettes=record['row']['sourcePalettes'],sourceFloorPalettes=row['sourcePalettes'])
            front=following
        raise AssertionError(('No unambiguous radio floor',record['game'],record['map'],origin))
    for record in inventory:
        prior=record['row'];game,name=record['game'],record['map'];x,y=record['position'];role=prior['role']
        row=copy.deepcopy(prior);reason=None;detail={}
        # All established backed-chair facings are checked against their
        # actual adjacent source furniture, with the explicit Cafe exception.
        facing=current_facing(prior);targets=[n for n in record['neighbors']if target_kind({'role':n['role']},name)]
        mismatch=facing and len(targets)==1 and facing!=targets[0]['direction']and not(name=='CELADON_CAFE'and y==6 and x>=8)
        if mismatch:
            assert name in('GOLDENROD_UNDERGROUND','TEAM_ROCKET_BASE_B3F'),(game,name,[x,y],targets)
            target=targets[0];direction=target['direction']
            assert(name=='GOLDENROD_UNDERGROUND'and direction=='west')or(name=='TEAM_ROCKET_BASE_B3F'and direction in('north','south'))
            for field in('donor','parts','asset','assetFileHash'):row.pop(field,None)
            if direction=='north':
                row.update(kind='third_party',asset=north_asset.relative_to(ROOT).as_posix(),assetFileHash=catalog.sha(north_asset.read_bytes()),
                    credit='Original Pokemon Emerald/FireRed chair artwork / Game Freak; complete native chair with native casino blue palette',sourceUrl='https://github.com/pret/pokeemerald')
            else:
                ref=south_ref if direction=='south'else dict(game='firered',tileset='player_house',id=78,hash=idx['player_house',78]['pixel_sha256'])
                row.update(kind='native_composite',parts=[part(ref)])
            row['chairFacing']=direction
            row['chairContext']=dict(target=target,scope='Source-reviewed original counter/table geometry; no chair or NPC movement',pixel_scale=1)
            reason='Built dungeon chair faces its actual adjacent source counter/table using complete native directional artwork'
            detail=dict(previousFacing=facing,facing=direction,target=target,footprint=[1,1])
        elif prior['tileset']=='TILESET_TRADITIONAL_HOUSE'and role in('johto_house_chair_left','johto_house_chair_right'):
            row.update(kind='third_party',asset=cushion.relative_to(ROOT).as_posix(),assetFileHash=asset_hash,
                credit='Original Pokemon Emerald / Game Freak; complete native ROUND_CUSHION frame',sourceUrl='https://github.com/pret/pokeemerald')
            for key in('donor','parts','chairFacing','chairContext'):row.pop(key,None)
            row['role']='gen2_audited_native_round_floor_cushion';reason='Original source glyph is a round floor cushion; complete native Emerald ROUND_CUSHION restores the correct equivalent'
            detail=dict(nativeObjectGraphicsId=168,footprint=[1,1],facing='nondirectional',native_rgba_sha256=catalog.sha(rgba))
        elif role=='johto_battle_whole_seat':
            row.update(kind='native_composite',parts=[part(dict(game='firered',tileset='network',id=757,hash=idx['network',757]['pixel_sha256']))])
            row['role']='gen2_audited_complete_padded_waiting_seat';reason='Original cushioned waiting-bank cell uses a complete native padded waiting seat instead of a cropped sideways slot chair'
            detail=dict(footprint=[1,1],facing='nondirectional')
        elif role=='johto_shop_complete_lounge_seat':
            head=prior['sourceHash']=='1ea3a13984a81d07d142f4f732516f179b7b7c3264e47113be30b3cd28d7fd26'
            cells=room_cells(game,name);other=cells.get((x,y+(1 if head else-1)))
            assert other and other[0]['role']==role
            assert(other[0]['sourceHash']=='1ea3a13984a81d07d142f4f732516f179b7b7c3264e47113be30b3cd28d7fd26')is not head
            row.update(kind='native_composite',parts=copy.deepcopy(lounge_head if head else lounge_foot))
            row['role']='gen2_audited_complete_lounge_'+('head'if head else'foot');reason='Original two-cell lounge seat gets one complete native cap/foot pair; no repeated compact chair heads'
            detail=dict(nativeMap='FR_CELADON_CITY_DEPARTMENT_STORE_1F',nativeCells=[[0,9],[0,10],[0,11]],footprint=[1,2],
                nativePaddingRowsKept=kept,omittedRows='Eight identical upholstery rows and eight fully transparent foot rows only',facing='east; established native lounge orientation retained')
        elif name in('GOLDENROD_GAME_CORNER','OLIVINE_CAFE')and role=='johto_casino_whole_native_chair':
            assert facing in('east','west','north','south')
            row['base']=casino.ref(657)
            if facing in('east','west'):
                row.update(kind='native_composite',parts=[part(casino.ref(682 if facing=='east'else 683))])
            reason='Casino/Cafe chair uses the actual casino657 carpet; former641 is a wall tile'
            detail=dict(facing=facing,roomFloor=casino.ref(657),footprint=[1,1])
        elif role in('johto_radio_complete_round_studio_stool','johto_radio_complete_native_chair')and prior.get('donor'):
            base,context=radio_floor(record)
            row.update(kind='native_composite',base=base,parts=[part(prior['donor'])]);row.pop('donor',None)
            reason='Complete native radio seat MID layer over its actual source-room floor, including separated recording rooms'
            detail=dict(roomFloor=base,floorContext=context,footprint=[1,1],facing='nondirectional')
        elif prior.get('parts')and prior.get('base')and role in('johto_center_whole_lounge_chair','johto_station_complete_waiting_chair','johto_labrooms_whole_student_chair_base','johto_labrooms_whole_student_desk_head'):
            refs={json.dumps(p['donor'],sort_keys=True)for p in prior['parts']}
            identity=all(p.get('srcX',0)==p.get('x',0)and p.get('srcY',0)==p.get('y',0)for p in prior['parts'])
            if len(refs)==1 and identity:
                ref=prior['parts'][0]['donor'];row.update(parts=[part(ref)])
                reason='Complete native foreground layer retains every seat/paired-desk pixel and removes opaque donor-floor filler'
                detail=dict(footprint=[1,1],facing='north'if'student'in role else'nondirectional')
        if reason:
            for key in('assetPixelHash','assetFrames','animated','animation','artOverlay','sourceColors','foreground','occludes'):
                row.pop(key,None)
            if row.get('kind')!='third_party':
                for key in('asset','assetFileHash'):row.pop(key,None)
            row.update(map=name,x=x,y=y,sourceCells=[[x,y]])
            row['chairAudit']=dict(reason=reason,original_role=role,original_module=record['module'],original_row_index=record['index'],
                original_composition_hash=prior['compositionPixelHash'],pixel_scale=1,sourcePositionPreserved=True,details=detail)
            row['evidence']=reason+'. All original source position, collision, palettes, priorities, NPCs, scripts and warps remain unchanged. Native pixels remain at1:1.'
            row['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,row,packed,ROOT).tobytes())
            old_hash=catalog.sha(preview.replacement_image(cache,prior,packed,ROOT).tobytes())
            for field in SOURCE_FIELDS:assert row.get(field)==prior.get(field)
            if row['compositionPixelHash']!=old_hash:
                new.append(row);classifications[reason]+=1
                if prior.get('x')is not None:
                    oldkey=record['module'],record['index']
                    oldrowhash=catalog.sha(json.dumps(prior,sort_keys=True,separators=(',',':')).encode())
                    removals[oldkey]=dict(oldmodule=record['module'],oldindex=record['index'],oldrow=prior,oldrow_sha256=oldrowhash,
                        hash_algorithm='sha256(canonical JSON sorted keys, separators comma/colon, UTF8)',newmodule=MODULE,newrow_index=len(new),newrow=row)
                decisions.append(dict(game=game,map=name,position=[x,y],result='corrected',reason=reason,details=detail));continue
        category=('non-seat workbench inspected by the coordinated floor audit'if'workbench'in role else
                  'verified complete native modular sofa retained'if'sofa'in role else
                  'verified explicit original link-console geometry'if'link_court'in role else
                  'verified source-paired student desks face north'if'student'in role else
                  'teacher podium, not a chair'if'teacher_desk'in role else
                  'verified empty floor at compact furniture foot'if'foot_floor'in role else
                  'verified native backed chair faces source furniture'if facing else
                  'verified nondirectional native waiting/studio seat')
        classifications[category]+=1;decisions.append(dict(game=game,map=name,position=[x,y],result='unchanged',reason=category))
    assert not facing_errors,facing_errors
    # Explicit user decisions in Cafe are a fixed contract, not heuristics.
    for game in review.GAMES:
        cells=room_cells(game,'CELADON_CAFE')
        expected={(x,y)for x in(1,4)for y in(2,3,6,7)}|{(7,y)for y in range(2,6)}|{(x,6)for x in range(8,12)}
        assert {pos for pos,item in cells.items()if'chair'in item[0]['role']}==expected
        assert all(cells[x,6][0]['chairFacing']=='west'for x in range(8,12))
        assert not any(r['game']==game and r['map']=='CELADON_CAFE'for r in new)
    (OUT/'candidates.json').write_text(json.dumps(new,indent=2)+'\n')
    (OUT/'old-positioned-rows-to-remove.json').write_text(json.dumps(list(removals.values()),indent=2)+'\n')
    (OUT/'audit-decisions.json').write_text(json.dumps(decisions,indent=2)+'\n')
    proof=review.validate_batch(new,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=OUT),ROOT)
    # Exercise current main-loaded mappings with only the exact positioned
    # old rows removed, then add the staged module once. Root owns that splice.
    combined=catalog.LUA.table();number=0
    for name in names:
        if name==MODULE:continue
        for index,row in enumerate(module_rows[name],1):
            if(name,index)in removals:continue
            number+=1;combined[number]=catalog.LUA.table_from(row,recursive=True)
    for row in new:number+=1;combined[number]=catalog.LUA.table_from(row,recursive=True)
    mapping=catalog.LUA.execute((ROOT/'lib/mapping.lua').read_text());_,errors=mapping.index(combined);assert not catalog.plain(errors)
    output='-- Source-reviewed Gen2 interior seating and exact room floors.\nlocal rows={}\n'
    for index in range(0,len(new),20):output+='for _,r in ipairs((function()return '+lua(new[index:index+20])+' end)())do rows[#rows+1]=r end\n'
    output+='return rows\n';(ROOT/MODULE).write_bytes(output.encode())
    proof.update(passed=True,audited_seat_related_cells=len(inventory),new_rows=len(new),exact_old_positioned_rows_to_remove=len(removals),
        non_seat_workbench_contexts=sum('workbench'in r['role']for r in inventory),
        actual_seating_and_paired_desk_contexts=sum('workbench'not in r['role']for r in inventory),
        maps=len({(r['game'],r['map'])for r in new}),classifications=dict(classifications),integrated_index_errors=0,
        integrated_main_rows_indexed=number,cafe_original_positions_and_west_bar_preserved=True,
        all_source_positions_collision_palettes_priorities_preserved=True,
        native_cushion_asset=cushion.relative_to(ROOT).as_posix(),native_cushion_sha256=asset_hash)
    (OUT/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    targets=[r for name,rows in module_rows.items()for index,r in enumerate(rows,1)if(name,index)not in removals]+new
    for game,name in sorted({(r['game'],r['map'])for r in new}):
        if game=='crystal'or name in('OLIVINE_CAFE','RADIO_TOWER_2F'):
            preview.map_preview(cache,OUT,game,name,game+'-'+name+'-audited',targets,packed,2,ROOT)
    print(json.dumps(proof,indent=2))


if __name__=='__main__':main()
