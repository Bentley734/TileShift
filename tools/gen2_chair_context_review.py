"""Offline, source-scoped Gen2 chair facing; no runtime map scans or redraw work."""
import argparse
import copy
import json
import os
import re
import subprocess
from collections import Counter,defaultdict
from pathlib import Path
from types import SimpleNamespace

import catalog
import preview
import gen2_extended_review as review
from interior_review import Imports
from native_room_parts import RoomParts
from newbark_building_review import lua
from johto_hack_flora import write_changed_rows
from johto_remaining_review import artwork

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'.work/tileshift-chair-context'
BEGIN='-- BEGIN OFFLINE CHAIR CONTEXT OVERRIDES\n'
END='-- END OFFLINE CHAIR CONTEXT OVERRIDES\n'
DIRECTIONS=(('east',1,0),('west',-1,0),('north',0,-1),('south',0,1))


def clean_module(text):
    if BEGIN not in text:return text
    start=text.index(BEGIN);end=text.index(END,start)+len(END)
    return text[:start]+text[end:]


def is_chair(row):
    role=row['role']
    return 'chair' in role and not any(tag in role for tag in ('foot_floor','lounge','row_of','chairman','student_chair_base'))


def target_kind(row,map_name=None):
    role=row['role']
    if any(tag in role for tag in ('machine_bank','slot_machine')):return 'gaming_machine'
    if 'drink_dispenser' in role:return 'equipment'
    if ('counter' in role and 'encounter' not in role) or any(tag in role for tag in ('reception_front','desk_surface')):return 'counter'
    if 'table' in role and not any(tag in role for tag in ('chair','floor_only')):return 'table'
    if 'workbench' in role:return 'table'
    if role=='johto_gate_desk_foot':return 'table'
    if role=='johto_gate_johto_complete_pc_1':return 'equipment'
    if role=='gen2_ship_original_complete_compact_furniture' and map_name and map_name.startswith('FAST_SHIP'):
        return 'table'
    return None


def current_facing(row):
    if row.get('chairFacing')in ('east','west','north','south'):return row['chairFacing']
    for part in row.get('parts',[]):
        ref=part.get('donor',{})
        if ref.get('game')=='firered':
            if ref.get('tileset')in ('house','player_house')and ref.get('id')in(75,78):return 'east'if ref['id']==75 else'west'
            if ref.get('tileset')=='building__rom_082d4cec'and ref.get('id')in(682,683):return 'east'if ref['id']==682 else'west'
    return None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate',action='store_true')
    parser.add_argument('--activate',action='store_true')
    parser.add_argument('--cafe-only',action='store_true')
    parser.add_argument('--baseline-ref',help='Optional committed review baseline when regenerating already activated positional rows')
    args=parser.parse_args();assert not args.activate or args.validate
    OUT.mkdir(parents=True,exist_ok=True)
    cache=Path(os.environ['APPDATA'])/'pokemon-love2d';imports=Imports(cache,ROOT.parent/'.work/tileshift-catalog');packed={}
    modules=list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(ROOT/'main.lua').read_text())))
    source_rows={};originals={};all_rows=[];by_family=defaultdict(list);live_by_family=defaultdict(list)
    for module in modules:
        path=ROOT/module;raw=path.read_text()
        baseline=clean_module(subprocess.check_output(['git','show',args.baseline_ref+':'+module],cwd=ROOT).decode('utf-8').replace('\r\n','\n')if args.baseline_ref else raw)
        originals[module]=(raw,baseline)
        rows=catalog.plain(catalog.LUA.execute(baseline))
        if rows=={}:rows=[]
        assert isinstance(rows,list)
        source_rows[module]=rows
        live_rows=rows if raw==baseline else catalog.plain(catalog.LUA.execute(raw))
        if live_rows=={}:live_rows=[]
        for index,row in enumerate(live_rows):
            if row.get('game')in review.GAMES and row.get('style')=='gen3':live_by_family[row['game'],row['tileset']].append((row,module,index))
        for index,row in enumerate(rows):
            all_rows.append(row)
            if row.get('game') in review.GAMES and row.get('style')=='gen3':by_family[row['game'],row['tileset']].append((row,module,index))
    native=RoomParts(imports,'firered','FR_CELADON_CITY_GAME_CORNER')
    primitives={};house_primitives={}
    for direction,mid in (('east',682),('west',683)):
        record=imports.cell_index('firered')[native.pair,mid]
        primitives[direction]=dict(donor=native.ref(mid),layers=['mid'],layerHashes={'mid':record['layer_sha256']['mid']},x=0,y=0,w=16,h=16)
        image=preview.native_donor(cache,native.ref(mid),packed,['mid'],{'mid':record['layer_sha256']['mid']})
        assert sum(p[3]>0 for p in image.get_flattened_data())==141
        assert image.getchannel('A').getbbox()==(2,0,14,16)
    for direction,mid in (('east',75),('west',78)):
        record=imports.cell_index('firered')['player_house',mid]
        ref=dict(game='firered',tileset='player_house',id=mid,hash=record['pixel_sha256'])
        house_primitives[direction]=dict(donor=ref,layers=['mid'],layerHashes={'mid':record['layer_sha256']['mid']},x=0,y=0,w=16,h=16)
        image=preview.native_donor(cache,ref,packed,['mid'],{'mid':record['layer_sha256']['mid']})
        assert sum(p[3]>0 for p in image.get_flattened_data())==149
    # A native NORTH/SOUTH primitive is added only after independent source
    # and footprint review. Until then those contexts remain explicitly held.
    extra_path=OUT/'vertical-primitives.json'
    if extra_path.exists():primitives.update(json.loads(extra_path.read_text()))
    staged=defaultdict(list);held=[];contexts=[];already_correct=[];replaced=defaultdict(dict);appended=defaultdict(list)
    slot_proofs=[];cafe_proofs=[];source_data={game:review.source(cache,game) for game in review.GAMES}
    def selected_cells(game,name,definition,active=False):
        family=[item for item in (live_by_family if active else by_family)[game,definition['tileset']]if item[0].get('map',name)==name]
        generic={};positioned={}
        for row,module,index in family:
            key=(row['id'],row['quadrant'])
            if row.get('x')is None:generic[key]=(row,module,index)
            else:positioned[key+(row['x'],row['y'])]=(row,module,index)
        cells={}
        for index,block in enumerate(definition['blocks']):
            for q in range(4):
                x,y=index%definition['width']*2+q%2,index//definition['width']*2+q//2
                chosen=positioned.get((block,q,x,y),generic.get((block,q)))
                if chosen:cells[x,y]=chosen
        return cells
    def queue_row(row,prior,module,index):
        if prior.get('x')is not None:replaced[module][index]=row
        else:appended[module].append(row)
        staged[module].append(row)
    cafe_tables={(x,y)for x in(1,4)for y in(2,3,6,7)}
    cafe_floor_cells={(x,y)for x in(1,4)for y in(1,5)}
    cafe_bar_west={(x,6)for x in range(8,12)}
    cafe_bar={(7,y)for y in range(2,6)}|cafe_bar_west
    for game in review.GAMES:
        data=source_data[game]
        for name,definition in sorted(data['maps'].items()):
            if not isinstance(definition,dict)or definition.get('environment')!='INDOOR':continue
            if args.cafe_only and name!='CELADON_CAFE':continue
            family=[item for item in by_family[game,definition['tileset']]if item[0].get('map',name)==name]
            if not any(is_chair(item[0])for item in family):continue
            cells=selected_cells(game,name,definition)
            cafe_live=selected_cells(game,name,definition,active=True)if name=='CELADON_CAFE'else None
            if game in ('gold','silver') and name in ('CELADON_GAME_CORNER','GOLDENROD_GAME_CORNER'):
                crystal=source_data['crystal'];native_cells=selected_cells('crystal',name,crystal['maps'][name])
                for (x,y),(prior,module,index)in list(cells.items()):
                    counterpart=native_cells.get((x,y))
                    if 'drink_dispenser'not in prior['role']or not counterpart:continue
                    seed=counterpart[0];match=re.search(r'whole_machine_bank_([01])_([12])$',seed['role'])
                    if not match:continue
                    side,part=map(int,match.groups());left=x-side;top=y;bottom=y
                    def bank_at(yy):
                        return all((p:=native_cells.get((xx,yy)))and'whole_machine_bank_'in p[0]['role']for xx in(left,left+1))
                    while bank_at(top-1):top-=1
                    while bank_at(bottom+1):bottom+=1
                    assert bottom-top+1>=3 and bank_at(top)
                    # Verify an actual continuous bank in the GS source above
                    # these aliased bottoms. Standalone vending machines never
                    # satisfy this position/whole-bank context guard.
                    assert any((p:=cells.get((xx,yy)))and'whole_machine_bank_'in p[0]['role']for xx in(left,left+1)for yy in range(top,y))
                    envelope=[]
                    for yy in range(top,bottom+1):
                        for xx in(left,left+1):
                            bid=definition['blocks'][yy//2*definition['width']+xx//2];q=yy%2*2+xx%2
                            c=review.cell_info(cache,game,data,definition['tileset'],bid,q)
                            envelope.append(dict(position=[xx,yy],sourceHash=c['sourceHash'],tiles=c['tiles'],collision=c['collision']))
                    source=review.cell_info(cache,game,data,definition['tileset'],prior['id'],prior['quadrant'])
                    assert source['sourceHash']==prior['sourceHash']
                    row=copy.deepcopy(prior)
                    for key in ('asset','assetFileHash','assetPixelHash','assetFrames','donor','parts','animated','animation','artOverlay','sourceColors','foreground','occludes'):
                        row.pop(key,None)
                    row.update(artwork(seed));row.update(map=name,x=x,y=y,sourceCells=[[x,y]],role=seed['role'],
                        sourceFiles=data['fingerprints'][definition['tileset']],sourceCollision=source['collision'],
                        sourcePalettes=[a.get('palette',1)for a in source['attributes']],sourcePriority=[bool(a.get('priority'))for a in source['attributes']],
                        slotBankContext=dict(envelope=[left,top,2,bottom-top+1],sourceCells=envelope,
                            nativeReviewedCounterpart=dict(game='crystal',map=name,position=[x,y],role=seed['role'],compositionPixelHash=seed.get('compositionPixelHash'))),
                        evidence='Explicit continuous original GS slot-machine bank at its exact source coordinates; lower reused glyphs are machine body/foot here, while the same glyphs remain drink dispensers elsewhere. '
                            'Complete already reviewed native Gen3 slot-bank repeat/end/foot modules retain all pixels at1:1 over the actual casino floor. '
                            'The whole source two-column bank context is fingerprinted. Original position, collision, scripts, gambling interactions and events remain unchanged.')
                    row['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,row,packed,ROOT).tobytes())
                    queue_row(row,prior,module,index);cells[x,y]=(row,module,index)
                    slot_proofs.append(dict(game=game,map=name,position=[x,y],old_role=prior['role'],new_role=seed['role'],bank_envelope=[left,top,2,bottom-top+1]))
            for (x,y),(prior,module,row_index) in sorted(cells.items()):
                if not is_chair(prior):continue
                candidates=[];neighbors=[]
                for direction,dx,dy in DIRECTIONS:
                    other=cells.get((x+dx,y+dy))
                    if other:neighbors.append(dict(direction=direction,position=[x+dx,y+dy],role=other[0]['role']))
                    if other and (kind:=target_kind(other[0],name)):
                        candidates.append(dict(direction=direction,position=[x+dx,y+dy],kind=kind,role=other[0]['role'],
                            sourceHash=other[0]['sourceHash'],id=other[0]['id'],quadrant=other[0]['quadrant']))
                record=dict(game=game,map=name,position=[x,y],module=module,prior_role=prior['role'],adjacent_targets=candidates,cardinal_neighbors=neighbors)
                if len(candidates)>1 and current_facing(prior)in {target['direction']for target in candidates}:
                    # An existing chair between a table and a counter already
                    # satisfies the request when it faces either one of them.
                    already_correct.append(dict(**record,facing=current_facing(prior),reason='Existing complete chair already faces an adjacent reviewed table/counter'));continue
                if not candidates and name=='FAST_SHIP_CABINS_SE_SSE_CAPTAINS_CABIN' and (x,y)==(6,17):
                    # The staggered captain-cabin seat is one cell below the
                    # right corner of its complete32x32 table, clearly on its
                    # right side. Its nearest table corner is(5,16).
                    other=cells.get((5,16));assert other and target_kind(other[0],name)=='table'
                    candidates=[dict(direction='west',position=[5,16],kind='table',role=other[0]['role'],
                        sourceHash=other[0]['sourceHash'],id=other[0]['id'],quadrant=other[0]['quadrant'],
                        source_context='Visually reviewed staggered seat on right side of captain-cabin table')]
                    record['adjacent_targets']=candidates
                if len(candidates)!=1:
                    held.append(dict(**record,reason='No single unambiguous cardinally adjacent table, bar or gaming machine'));continue
                target=candidates[0];direction=target['direction']
                if name=='CELADON_CAFE'and(x,y)in cafe_bar_west:
                    direction='west'
                    record['user_facing_override']=dict(facing='west',reason='User explicitly selected left-facing chairs below the bar; position remains fixed')
                record.update(facing=direction,target=target)
                contexts.append(record)
                if direction not in primitives:
                    held.append(dict(**record,reason='Complete native directional primitive pending independent review'));continue
                base=prior.get('base')
                if not base and name=='RADIO_TOWER_2F' and (x,y)==(5,6):
                    # The old complete native clinic stool carries the public
                    # blue floor in its under image. The adjacent reviewed
                    # floor is byte-identical outside its foreground mask.
                    floor=cells[5,7][0];assert floor['role']=='johto_radio_public_floor'
                    base=floor['donor'];ref=prior['donor']
                    old=preview.native_donor(cache,ref,packed)
                    ground=preview.native_donor(cache,base,packed)
                    foreground=preview.native_donor(cache,ref,packed,['mid'],{'mid':imports.cell_index(ref['game'])[ref['tileset'],ref['id']]['layer_sha256']['mid']})
                    assert all(a==b for a,b,p in zip(old.get_flattened_data(),ground.get_flattened_data(),foreground.get_flattened_data())if p[3]==0)
                    record['existing_embedded_floor']=copy.deepcopy(base)
                if not base:
                    held.append(dict(**record,reason='No explicit reviewed room-floor base'));continue
                source=review.cell_info(cache,game,data,definition['tileset'],prior['id'],prior['quadrant'])
                assert source['sourceHash']==prior['sourceHash']
                row=copy.deepcopy(prior)
                row['base']=copy.deepcopy(base)
                for key in ('asset','assetFileHash','assetPixelHash','assetFrames','donor','parts','animated','animation','artOverlay','sourceColors','foreground','occludes'):
                    row.pop(key,None)
                household=any(p.get('donor',{}).get('tileset') in ('house','player_house') and p['donor']['id'] in(75,78) for p in prior.get('parts',[]))
                primitive=house_primitives[direction] if household and direction in house_primitives else primitives[direction]
                if 'asset' in primitive:
                    row.update(kind='third_party',asset=primitive['asset'],assetFileHash=primitive['assetFileHash'],
                        credit=primitive['credit'],sourceUrl=primitive['sourceUrl'])
                else:row.update(kind='native_composite',parts=[copy.deepcopy(primitive)])
                row.update(map=name,x=x,y=y,sourceCells=[[x,y]],sourceFiles=data['fingerprints'][definition['tileset']],
                    sourceCollision=source['collision'],sourcePalettes=[a.get('palette',1)for a in source['attributes']],
                    sourcePriority=[bool(a.get('priority'))for a in source['attributes']],chairFacing=direction,
                    chairContext=dict(target=target,original_role=prior['role'],original_module=module,
                        original_composition_hash=prior.get('compositionPixelHash'),pixel_scale=1,
                        scope='Offline explicit source-cell context; no runtime scan or new gameplay rule'),
                    evidence='Complete native Gen3 directional chair faces the one cardinally adjacent reviewed table, counter or gaming-machine cell. '
                        'The full native chair silhouette and all its unique pixels remain at1:1 scale over the unchanged explicit room floor. '
                        'Facing is authored offline at this exact fingerprinted source coordinate. Source position, collision, warp, actor, script and interaction metadata remain unchanged.')
                if record.get('existing_embedded_floor'):
                    row['chairContext']['existing_embedded_floor']=record['existing_embedded_floor']
                if record.get('user_facing_override'):
                    row['chairContext']['userFacingOverride']=record['user_facing_override']
                    row['evidence']='The user explicitly selected WEST facing for this lower-bar seat, overriding automatic table/counter facing without moving its source cell. '+row['evidence'].replace('faces the one cardinally adjacent reviewed table, counter or gaming-machine cell','uses the selected west-facing native artwork')
                row['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,row,packed,ROOT).tobytes())
                before=catalog.sha(preview.replacement_image(cache,prior,packed,ROOT).tobytes())
                if before==row['compositionPixelHash']:
                    already_correct.append(record);continue
                queue_row(row,prior,module,row_index)
            if name=='CELADON_CAFE':
                final={pos:item[0]for pos,item in cells.items()}
                for group in staged.values():
                    for row in group:
                        if row['game']==game and row.get('map')==name:final[row['x'],row['y']]=row
                assert {pos for pos,row in final.items()if is_chair(row)}==cafe_tables|cafe_bar
                for pos in cafe_bar:assert final[pos]==cafe_live[pos][0],('Bar chair changed',game,pos)
                for x,y in cafe_tables:assert final[x,y]['chairFacing']==('east'if x==1 else'west')
                for pos in cafe_bar_west:
                    assert final[pos]['chairFacing']=='west'and final[pos]['parts']==[primitives['west']]
                    assert final[pos]['chairContext']['userFacingOverride']['facing']=='west'
                floor=native.ref(657)
                for pos in cafe_floor_cells:
                    assert catalog.sha(preview.replacement_image(cache,final[pos],packed,ROOT).tobytes())==floor['hash']
                source_fields=('game','tileset','id','quadrant','sourceHash','sourceFiles','sourceCollision','sourcePalettes','sourcePriority')
                for pos in cafe_tables|cafe_floor_cells|cafe_bar:
                    for key in source_fields:assert final[pos].get(key)==cells[pos][0].get(key),(game,pos,key)
                assert not any('chairRelocation'in row for row in final.values())
                cafe_proofs.append(dict(game=game,passed=True,table_chair_positions=[list(p)for p in sorted(cafe_tables)],
                    empty_floor_positions=[list(p)for p in sorted(cafe_floor_cells)],bar_chair_positions=[list(p)for p in sorted(cafe_bar)],
                    table_chairs_at_original_source_positions=True,bar_rows_unchanged=True,relocation_metadata_absent=True,
                    all_source_guards_and_collision_preserved=True))
    rows=[r for group in staged.values()for r in group]
    cafe=Counter(r['chairFacing']for r in rows if r['game']=='crystal'and r['map']=='CELADON_CAFE'and r.get('chairFacing'))
    expected=Counter(east=8,west=8)
    cafe_contexts={game:Counter(c['facing']for c in contexts if c['game']==game and c['map']=='CELADON_CAFE')for game in review.GAMES}
    for game,actual in cafe_contexts.items():assert actual==expected,(game,actual,expected)
    summary=dict(rows=len(rows),contexts=len(contexts),already_correct=len(already_correct),held=len(held),maps=len({(r['game'],r['map'])for r in rows}),
        directions=dict(Counter(r['chairFacing']for r in rows if r.get('chairFacing'))),slot_bank_rows=len(slot_proofs),cafe_crystal=dict(cafe),all_cafe_contexts={game:dict(counts)for game,counts in cafe_contexts.items()},
        modules={module:len(rows)for module,rows in staged.items()})
    (OUT/'candidates.json').write_text(json.dumps(rows,indent=2)+'\n')
    (OUT/'contexts.json').write_text(json.dumps(contexts,indent=2)+'\n')
    (OUT/'already-correct.json').write_text(json.dumps(already_correct,indent=2)+'\n')
    (OUT/'held.json').write_text(json.dumps(held,indent=2)+'\n')
    (OUT/'slot-bank-fixes.json').write_text(json.dumps(slot_proofs,indent=2)+'\n')
    (OUT/'cafe-seating-proof.json').write_text(json.dumps(cafe_proofs,indent=2)+'\n')
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    for name in ('CELADON_CAFE','OLIVINE_CAFE','CELADON_GAME_CORNER','GOLDENROD_GAME_CORNER','POKEMON_FAN_CLUB','TRAINER_HOUSE_1F'):
        preview.map_preview(cache,OUT,'crystal',name,name,all_rows+rows,packed,3,ROOT)
    if args.validate:
        proof=review.validate_batch(rows,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=OUT),ROOT)
        proof.update(summary);(OUT/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
        proposed={};probe_dir=OUT/'modules';probe_dir.mkdir(exist_ok=True)
        for module,(raw,baseline) in originals.items():
            if module not in staged:continue
            path=probe_dir/Path(module).name;path.write_text(baseline)
            if replaced[module]:
                module_rows=copy.deepcopy(source_rows[module])
                for index,row in replaced[module].items():module_rows[index]=row
                write_changed_rows(path,module_rows,set(replaced[module]))
            text=path.read_text();overrides=appended[module]
            if overrides:
                assert text.rstrip().endswith('return rows'),module
                position=text.rfind('return rows');tail=BEGIN
                for n in range(0,len(overrides),20):tail+='for _,r in ipairs((function()return '+lua(overrides[n:n+20])+' end)())do rows[#rows+1]=r end\n'
                tail+=END;text=text[:position]+tail+text[position:];path.write_text(text)
            proposed[module]=text
        # Exercise the exact combined main-loaded index before touching any
        # production file. Positioned scopes replace existing positioned rows;
        # they are never appended as duplicate keys.
        combined=catalog.LUA.table();number=0
        for module in modules:
            batch=catalog.LUA.execute(proposed.get(module,originals[module][0]))
            for index in range(1,len(batch)+1):number+=1;combined[number]=batch[index]
        mapping=catalog.LUA.execute((ROOT/'lib/mapping.lua').read_text())
        _,errors=mapping.index(combined);errors=catalog.plain(errors)
        assert not errors,errors
        proof['integrated_main_rows_indexed']=number;proof['integrated_index_errors']=0
        (OUT/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
        if args.activate:
            for module,text in proposed.items():
                assert (ROOT/module).read_text()==originals[module][0],'Concurrent module update'
                (ROOT/module).write_text(text)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
