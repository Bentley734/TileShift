"""Private GSC cave corner geometry; no production mappings are written.

Each source corner is shown in actual context. Compact32px profiles are
considered only as a complete original32px block, never as free corner aliases.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import copy
import json
import os
from pathlib import Path
import sys

WORKSPACE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(WORKSPACE/'.tools/python'))
from PIL import Image,ImageDraw,ImageFont
import catalog
import preview
import gen2_extended_review as ext
import gen2_cave_review as cave
from building_review import decode_layout

CORNERS=(('northwest',(4,0),(1,5,5,21),648,520),
         ('northeast',(6,1),(7,1,23,7),650,522),
         ('southwest',(12,2),(21,37,37,38),664,536),
         ('southeast',(14,3),(39,23,38,39),666,538))
PROFILE=[5,36,36,7,21,22,22,23,21,22,22,23,37,38,38,39]


def source_context(cache,game,data,definition,x0,y0):
    out=Image.new('RGBA',(48,48));blocks=catalog.lua_array(definition['blocks'])
    for dy in range(-1,2):
        for dx in range(-1,2):
            x,y=x0+dx,y0+dy
            if 0<=x<definition['width']*2 and 0<=y<definition['height']*2:
                bid=blocks[y//2*definition['width']+x//2];cell=ext.cell_info(cache,game,data,definition['tileset'],bid,y%2*2+x%2)
                out.paste(cave.source_image(cache,game,data,cell,definition),((dx+1)*16,(dy+1)*16))
    return out


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=Path(os.environ['APPDATA'])/'pokemon-love2d')
    parser.add_argument('--engine',type=Path,default=WORKSPACE/'.tools/engine-0395')
    parser.add_argument('--output',type=Path,default=WORKSPACE/'.work/tileshift-gen2-corner-review')
    parser.add_argument('--write-reviewed',action='store_true',help='Activate only the approved continuous-side correction and convex corners; complete32px profiles remain private')
    parser.add_argument('--write-compact-reviewed',action='store_true',help='Merge the separately approved complete32px mass recipes')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    active=ext.active_rows(WORKSPACE/'TileShift');records={};manifests={};packed={};rows=[];held=[];examples={};profiles=[];compact_rows=[];compact_examples={}
    for game in ('emerald','firered'):
        records[game]={(r['pair'],r['mid']):r for r in json.loads((WORKSPACE/f'.work/tileshift-catalog/{game}.json').read_text())['cells']}
        manifests[game]=catalog.read_lua(args.cache/game/'data/generated/gba/native/manifest.lua')
    corrections=[]
    for original in active:
        donor=original.get('donor',{})
        if donor.get('game')!='emerald' or donor.get('tileset')!='general__cave':continue
        roles={'cave_rock_mass_west_side':(536,528),'cave_rock_mass_east_side':(538,530)}
        if original['role'] not in roles:continue
        old,new=roles[original['role']]
        if donor['id']==new:continue
        assert donor['id']==old
        row=copy.deepcopy(original);row['donor']['id']=new
        row['donor']['hash']=records['emerald']['general__cave',new]['pixel_sha256']
        row['status']='candidate'
        row['evidence']='Continuous vertical cave side, corrected after full native-family topology review: Emerald520/522 north corners,528/530 continuous sides,536/538 south corners. Complete source raw21 or23 sides retain original geometry, collision, palette, priority and map scope. No corner art is repeated as a straight wall.'
        corrections.append(row)
    for game in ext.GAMES:
        data=ext.source(args.cache,game)
        for name,(donor_game,native_name) in cave.TERRAIN_CASES.items():
            definition=data['maps'][name];ts=definition['tileset'];spec=manifests[donor_game]['layouts'][native_name]
            seeds={}
            for direction,(bid,q),raw,fr_mid,em_mid in CORNERS:
                cell=ext.cell_info(args.cache,game,data,ts,bid,q);assert tuple(cell['tiles'])==raw and cell['collision']==7
                seeds[ext.identity(cell)]=(direction,fr_mid if donor_game=='firered' else em_mid)
            mapped={(r['id'],r['quadrant']) for r in active if r['game']==game and r['tileset']==ts and r.get('map',name)==name}
            occurrences=defaultdict(list)
            for i,bid in enumerate(catalog.lua_array(definition['blocks'])):
                for q in range(4):occurrences[bid,q].append([i%definition['width']*2+q%2,i//definition['width']*2+q//2])
            for (bid,q),coords in sorted(occurrences.items()):
                cell=ext.cell_info(args.cache,game,data,ts,bid,q);match=seeds.get(ext.identity(cell))
                if not match or (bid,q) in mapped:continue
                direction,mid=match;record=records[donor_game].get((spec['pair'],mid))
                if not record:
                    held.append({'game':game,'map':name,'source':[bid,q],'direction':direction,'reason':'No reviewed native corner in this imported regional bank','mid':mid});continue
                ref={'game':donor_game,'tileset':spec['pair'],'id':mid,'hash':record['pixel_sha256']}
                row={'game':game,'style':'gen3','map':name,'tileset':ts,'id':bid,'quadrant':q,
                     'role':'cave_convex_'+direction,'status':'candidate','sourceHash':cell['sourceHash'],
                     'sourceFiles':data['fingerprints'][ts],'sourceCells':coords,'sourceCollision':cell['collision'],
                     'sourcePriority':[bool(a.get('priority')) for a in cell['attributes']],
                     'sourcePalettes':[a.get('palette',1) for a in cell['attributes']],
                     'donor':ref,'nativeContext':native_name,
                     'evidence':'Private convex cave-corner proposal. Complete source glyph, material, handedness and actual neighboring floor/rock surfaces are displayed. Source pixels, collision7, palette slots and per8px priority match the displayed seed. Scope is explicit; no inward corner or compact-platform quarter is inferred. Original geometry, collision and all events remain native.'}
                rows.append(row)
                if game=='crystal':examples.setdefault((ts,spec['pair'],direction),(row,cell,data,definition))
            block=catalog.lua_array(catalog.dict_at(data['sets'][ts]['blocks'],50));assert block==PROFILE
            coordinates=[[i%definition['width']*2,i//definition['width']*2] for i,b in enumerate(catalog.lua_array(definition['blocks'])) if b==49]
            if coordinates:
                if all((49,q)in mapped for q in range(4)):continue
                assert not any((49,q)in mapped for q in range(4)),'Complete compact mass has only partial existing coverage'
                corners=(648,650,664,666) if donor_game=='firered' else (520,522,536,538)
                center=657 if donor_game=='firered' else 529
                def ref(mid):return {'game':donor_game,'tileset':spec['pair'],'id':mid,'hash':records[donor_game][spec['pair'],mid]['pixel_sha256']}
                candidate=[]
                for q in range(4):
                    cell=ext.cell_info(args.cache,game,data,ts,49,q);assert cell['collision']==7
                    assert (49,q) not in mapped,'Complete compact profile partly mapped; review layering before proceeding'
                    row={'game':game,'style':'gen3','map':name,'tileset':ts,'id':49,'quadrant':q,
                        'role':'complete_compact_cave_plateau_'+str(q),'kind':'native_composite','status':'candidate',
                        'sourceHash':cell['sourceHash'],'sourceFiles':data['fingerprints'][ts],
                        'sourceCells':[[x+q%2,y+q//2]for x,y in coordinates],
                        'sourceCollision':cell['collision'],'sourcePriority':[bool(a.get('priority'))for a in cell['attributes']],
                        'sourcePalettes':[a.get('palette',1)for a in cell['attributes']],
                        'sourceWhole32Profile':PROFILE,
                        'parts':[{'donor':ref(corners[q]),'w':16,'h':16},
                                 {'donor':ref(center),'srcX':q%2*8,'srcY':q//2*8,'w':8,'h':8,
                                  'x':8-q%2*8,'y':8-q//2*8}],
                        'nativeContext':name,
                        'evidence':'Private complete32px raised-rock mass proposal. Only original full32profile [5,36,36,7 /21,22,22,23 /21,22,22,23 /37,38,38,39] is eligible, with all four quadrant fingerprints, collision7, palette and priority checked together. Four complete native corners retain the outer contour and a native central16px top joins them at(8,8), compacting only the repeated inner rock mass. No free corner-quarter aliases or larger platform are inferred. Original source geometry and all behavior remain unchanged.'}
                    candidate.append(row);compact_rows.append(row)
                if game=='crystal':
                    profiles.append({'game':game,'map':name,'tileset':ts,'block':49,'whole32Raw':block,'cells':coordinates,'status':'needs_complete_profile_review'})
                    compact_examples.setdefault((donor_game,spec['pair']),(candidate,data,definition))
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    groups=defaultdict(list)
    for item in examples.values():groups[item[0]['tileset'],item[0]['donor']['tileset']].append(item)
    for (ts,pair),items in groups.items():
        canvas=Image.new('RGB',(1440,80+len(items)*246),'#18202c');d=ImageDraw.Draw(canvas)
        d.text((14,12),'Convex cave corners: actual source context, native context, staged full neighborhood',font=font,fill='white')
        d.text((14,42),f'{ts} / {pair}; a proposed new geometry batch, with inward corners and compact32px profiles held.',fill='#ccd7e5')
        for i,(row,cell,data,definition) in enumerate(items):
            y=86+i*246;x0,y0=row['sourceCells'][0];source=source_context(args.cache,'crystal',data,definition,x0,y0)
            donor=row['donor'];target=preview.native_donor(args.cache,donor,packed)
            spec=manifests[donor['game']]['layouts'][row['nativeContext']]
            layout=decode_layout(args.cache/donor['game']/'data/generated/gba/native'/spec['file'])
            positions=[(i%layout['width'],i//layout['width']) for i,mid in enumerate(layout['mids'])
                       if mid==donor['id'] and 0<i%layout['width']<layout['width']-1
                       and 0<i//layout['width']<layout['height']-1]
            assert positions,(row['nativeContext'],donor['id'])
            nx,ny=positions[0];native=Image.new('RGBA',(48,48));revised=source.copy()
            selected={}
            for mapping in sorted(active+corrections+rows,key=lambda r:(r.get('map') is not None,r.get('x') is not None)):
                if mapping['game']=='crystal' and mapping['tileset']==ts and mapping.get('map',row['map'])==row['map']:
                    selected[mapping['id'],mapping['quadrant'],mapping.get('x'),mapping.get('y')]=mapping
            blocks=catalog.lua_array(definition['blocks'])
            for dy in range(-1,2):
                for dx in range(-1,2):
                    mid=layout['mids'][(ny+dy)*layout['width']+nx+dx]
                    ref={'game':donor['game'],'tileset':spec['pair'],'id':mid,
                         'hash':records[donor['game']][spec['pair'],mid]['pixel_sha256']}
                    native.paste(preview.native_donor(args.cache,ref,packed),((dx+1)*16,(dy+1)*16))
                    x,z=x0+dx,y0+dy
                    if 0<=x<definition['width']*2 and 0<=z<definition['height']*2:
                        bid=blocks[z//2*definition['width']+x//2];q=z%2*2+x%2
                        replacement=selected.get((bid,q,x,z)) or selected.get((bid,q,None,None))
                        if replacement:revised.paste(preview.replacement_image(args.cache,replacement,packed,WORKSPACE/'TileShift'),((dx+1)*16,(dy+1)*16))
            d.text((14,y),row['role'].replace('_',' '),font=font,fill='white')
            for x,image in ((14,source),(600,native),(1160,revised)):
                canvas.paste(image.resize((192,192),Image.Resampling.NEAREST),(x,y+29));d.rectangle((x+64,y+93,x+127,y+156),outline='#fff293',width=2)
            d.text((224,y+47),f"{row['map']} {row['id']}:{row['quadrant']} at({x0},{y0})",fill='#ccd7e5')
            d.text((224,y+71),f"Source raw{cell['tiles']} / collision0x07",fill='#ccd7e5')
            d.text((806,y+47),f"{donor['game']} {donor['id']} at({nx},{ny})",fill='white')
            d.text((806,y+71),row['nativeContext'],fill='#ccd7e5')
        canvas.save(args.output/f'convex-context-{ts}-{pair}.png')
    # Show topology as a complete family and every changed continuous-side
    # role in actual source/native neighborhoods. This prevents visually
    # similar diagonal north variants from being mistaken for south corners.
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    family=Image.new('RGB',(1450,1190),'#18202c');d=ImageDraw.Draw(family)
    d.text((14,12),'Emerald Granite Cave: complete native raised-rock family and continuous-side correction',font=font,fill='white')
    for i,mid in enumerate((520,521,522,528,529,530,536,537,538)):
        x,y=14+i%3*116,64+i//3*140
        ref={'game':'emerald','tileset':'general__cave','id':mid,'hash':records['emerald']['general__cave',mid]['pixel_sha256']}
        family.paste(preview.native_donor(args.cache,ref,packed).resize((96,96),Image.Resampling.NEAREST),(x,y));d.text((x,y+102),str(mid),fill='white')
    d.text((395,75),'520 / 522 = north corners',font=font,fill='white')
    d.text((395,110),'528 / 530 = continuous west / east sides',font=font,fill='white')
    d.text((395,145),'536 / 538 = south corners; 537 joins their front face',font=font,fill='white')
    d.text((395,190),'Previous straight-side rows used the lower corners; those 127 rows are proposed for correction.',fill='#ffd391')
    d.text((395,220),'544 / 546 are alternate NORTH corners, not south corners. They are excluded.',fill='#ccd7e5')
    source_data=ext.source(args.cache,'crystal');definition=source_data['maps']['UNION_CAVE_1F']
    spec=manifests['emerald']['layouts']['EM_GRANITE_CAVE_1F'];layout=decode_layout(args.cache/'emerald/data/generated/gba/native'/spec['file'])
    native_map=Image.new('RGBA',(layout['width']*16,layout['height']*16))
    for i,mid in enumerate(layout['mids']):
        ref={'game':'emerald','tileset':spec['pair'],'id':mid,'hash':records['emerald'][spec['pair'],mid]['pixel_sha256']}
        native_map.paste(preview.native_donor(args.cache,ref,packed),(i%layout['width']*16,i//layout['width']*16))
    family.paste(native_map.resize((1008,384),Image.Resampling.NEAREST),(395,267))
    for i,role in enumerate(('cave_rock_mass_west_side','cave_rock_mass_east_side')):
        row=next(r for r in corrections+active if r['game']=='crystal' and r['map']=='UNION_CAVE_1F' and r['role']==role)
        x0,y0=row['sourceCells'][0];source=source_context(args.cache,'crystal',source_data,definition,x0,y0)
        old=copy.deepcopy(row);old['donor']['id']=536 if i==0 else 538
        old['donor']['hash']=records['emerald']['general__cave',old['donor']['id']]['pixel_sha256']
        old_image=source.copy();new_image=source.copy()
        old_image.paste(preview.native_donor(args.cache,old['donor'],packed),(16,16));new_image.paste(preview.native_donor(args.cache,row['donor'],packed),(16,16))
        y=710+i*234;d.text((14,y),f"{role.replace('_',' ')}: raw {21 if i==0 else 23} / collision 0x07",font=font,fill='white')
        for x,image,label in ((14,source,'Source'),(490,old_image,f"Old {old['donor']['id']}"),(980,new_image,f"Proposed {row['donor']['id']}")):
            d.text((x,y+27),label,fill='#ccd7e5');family.paste(image.resize((192,192),Image.Resampling.NEAREST),(x,y+45))
            d.rectangle((x+64,y+109,x+127,y+172),outline='#fff293',width=2)
    family.save(args.output/'emerald-complete-cave-family-correction.png')
    compact_sheet=Image.new('RGB',(1430,70+len(compact_examples)*280),'#18202c');d=ImageDraw.Draw(compact_sheet)
    d.text((14,12),'Complete source32px raised-rock masses: full native48px family compacted within the same32px footprint',font=font,fill='white')
    compact_proofs=[]
    for i,((donor_game,pair),(candidates,data,definition))in enumerate(compact_examples.items()):
        y=76+i*280;source=Image.new('RGBA',(32,32));target=Image.new('RGBA',(32,32))
        for q,row in enumerate(candidates):
            source.paste(cave.source_image(args.cache,'crystal',data,ext.cell_info(args.cache,'crystal',data,row['tileset'],49,q),definition),(q%2*16,q//2*16))
            target.paste(preview.replacement_image(args.cache,row,packed,WORKSPACE/'TileShift'),(q%2*16,q//2*16))
        mids=(648,649,650,656,657,658,664,665,666)if donor_game=='firered'else(520,521,522,528,529,530,536,537,538)
        native=Image.new('RGBA',(48,48))
        for j,mid in enumerate(mids):
            ref={'game':donor_game,'tileset':pair,'id':mid,'hash':records[donor_game][pair,mid]['pixel_sha256']}
            native.paste(preview.native_donor(args.cache,ref,packed),(j%3*16,j//3*16))
        for x,img,label in ((14,source,'Original complete32px profile'),(510,native,'Native full48px family'),(1005,target,'Proposed32px complete profile')):
            d.text((x,y),label,fill='white');compact_sheet.paste(img.resize((192,192),Image.Resampling.NEAREST),(x,y+28))
        d.text((230,y+45),f"CRYSTAL {candidates[0]['map']} block49",fill='#ccd7e5')
        d.text((230,y+70),'Four blocked quadrants; no free corner aliases',fill='#ccd7e5')
        d.text((715,y+45),f'{donor_game} / {pair}',fill='#ccd7e5')
        d.text((1005,y+230),'Outer contour retained; center16px native top',fill='#ccd7e5')
        compact_proofs.append({'game':donor_game,'tileset':pair,'sourceMap':candidates[0]['map'],
                               'completeTarget32Hash':catalog.sha(target.tobytes()),'sourceWhole32Hash':catalog.sha(source.tobytes())})
    compact_sheet.save(args.output/'compact-complete32-profile-proposal.png')
    probe=copy.deepcopy(corrections+rows+compact_rows)
    for row in probe:row['status']='reviewed'
    proof=ext.validate_batch(probe,args,WORKSPACE/'TileShift')
    (args.output/'convex-candidates.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    (args.output/'continuous-side-corrections.json').write_text(json.dumps(corrections,indent=2),encoding='utf-8')
    (args.output/'compact-complete32-candidates.json').write_text(json.dumps(compact_rows,indent=2),encoding='utf-8')
    (args.output/'compact-complete32-proof.json').write_text(json.dumps(compact_proofs,indent=2),encoding='utf-8')
    (args.output/'held.json').write_text(json.dumps(held,indent=2),encoding='utf-8')
    (args.output/'compact-profile-inventory.json').write_text(json.dumps(profiles,indent=2),encoding='utf-8')
    (args.output/'runtime-checks.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    print('Private convex rows',len(rows),'source cells',sum(len(r['sourceCells']) for r in rows),'continuous-side corrections',len(corrections),'whole32profile rows',len(compact_rows),proof,'production writes: 0')
    if args.write_reviewed or args.write_compact_reviewed:
        target=WORKSPACE/'TileShift/mappings/gen2_caves.lua';previous=preview.read_reviewed(target)
        def key(row):return tuple(row.get(k)for k in ('game','style','tileset','id','quadrant','map','x','y'))
        indexed={key(row):row for row in previous};unchanged=copy.deepcopy(indexed);changed=set()
        for row in corrections if args.write_reviewed else []:
            revised=copy.deepcopy(row);revised['status']='reviewed';original=indexed[key(row)]
            for field in original:
                if field not in ('donor','evidence'):assert revised[field]==original[field],field
            assert set(revised)==set(original)
            indexed[key(row)]=revised;changed.add(key(row))
        additions=(rows if args.write_reviewed else [])+(compact_rows if args.write_compact_reviewed else [])
        for row in additions:
            assert key(row) not in indexed
            revised=copy.deepcopy(row);revised['status']='reviewed';revised['evidence']=revised['evidence'].replace('Private convex cave-corner proposal.','Visually reviewed complete convex cave corner.',1).replace('Private complete32px raised-rock mass proposal.','Visually reviewed complete32px raised-rock mass.',1)
            indexed[key(row)]=revised
        for row_key,original in unchanged.items():
            if row_key not in changed:assert indexed[row_key]==original
        live=ext.validate_batch(list(indexed.values()),args,WORKSPACE/'TileShift')
        stats=ext.write_compact(list(indexed.values()),target)
        parsed={key(row):row for row in preview.read_reviewed(target)};assert parsed==indexed
        (args.output/'approved-activation.json').write_text(json.dumps({'file':stats,'changedExistingRows':len(changed),
            'addedConvexRows':len(rows)if args.write_reviewed else 0,'addedCompactRows':len(compact_rows)if args.write_compact_reviewed else 0,
            'previousRowsUnchanged':len(unchanged)-len(changed),'live':live},indent=2),encoding='utf-8')
        print('Approved cave topology/corner activation',stats,live)


if __name__=='__main__':main()
