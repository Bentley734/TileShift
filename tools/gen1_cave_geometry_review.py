"""Stage reviewed cave features with exact source occurrence/layer proofs.

The upward ladder, Strength switches and special fall holes were visually
reviewed with the native event/GPU fixtures. New geometry stays private until
its own review. No ROM graphics are copied into production assets.
"""
from __future__ import annotations
import argparse
from collections import Counter
import copy
import json
import zlib
from pathlib import Path
import catalog
import cave_review
import gen1_extended_review as extended
import preview
import review
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'.work/tileshift-gen1-extended-review'
CACHE=Path(catalog.os.environ['APPDATA'])/'pokemon-love2d'
APPROVED_ROLES={'cave_ascending_ladder','cave_strength_button','cave_special_fall_hole'}
BUTTONS=(('VICTORY_ROAD_1F',17,13),('VICTORY_ROAD_2F',1,16),('VICTORY_ROAD_2F',9,16),('VICTORY_ROAD_3F',3,5))
DIRECTIONS=((20,1,649,'cave_north_mass_edge'),(20,2,656,'cave_west_mass_face'),(22,3,658,'cave_east_mass_face'),
            (23,2,656,'cave_west_half_face'),(23,3,658,'cave_east_half_face'),(32,3,665,'cave_south_half_face'),
            (20,0,648,'cave_large_nw_corner'),(22,1,650,'cave_large_ne_corner'),
            (28,2,664,'cave_large_sw_corner'),(30,3,666,'cave_large_se_corner'),
            (43,2,667,'cave_inner_sw_corner'),(44,3,668,'cave_inner_se_corner'),
            (76,0,643,'cave_jagged_fixed_rock_cluster'))
APPROVED_ROLES.update(s[3]for s in DIRECTIONS)
APPROVED_ROLES.update({'cave_compact_plateau_corner_'+str(q)for q in range(4)})
APPROVED_ROLES.update({'cave_cerulean_rock_stairs','cave_plain_water','cave_victory_barrier_compact','cave_victory_barrier_head','cave_victory_barrier_foot'})


def approved_features():
    native=json.loads((ROOT/'.work/tileshift-catalog/firered.json').read_text())['cells']
    native={(r['pair'],r['mid']):r for r in native}
    em=json.loads((ROOT/'.work/tileshift-catalog/emerald.json').read_text())['cells']
    ladder=next(r for r in em if r.get('pair')=='general__cave'and r['mid']==574)
    ladder_ref={'game':'emerald','tileset':'general__cave','id':574,'hash':ladder['pixel_sha256']}
    assert ladder['layer_sha256']['mid']=='1fc39422ac218e6436105b329e5d887d1874f00d2e4b81966c5c3524ffc39bff'
    packed={}
    ladder_pixels=preview.native_donor(CACHE,ladder_ref,packed,['mid'],{'mid':ladder['layer_sha256']['mid']})
    assert sum(p[3]>0 for p in ladder_pixels.get_flattened_data())==165
    manifest=catalog.read_lua(CACHE/'firered/data/generated/gba/native/manifest.lua')
    rows=[];proofs=[]
    for game in ('red','blue','yellow'):
        data=json.loads((ROOT/f'.work/tileshift-catalog/{game}.json').read_text())
        cells={(r['block_id'],r['quadrant']):r for r in data['cells']if r['tileset']=='CAVERN'}
        files=next(r['fingerprints']for r in data['tilesets']if r['tileset']=='CAVERN')
        maps=catalog.read_lua(CACHE/game/'data/generated/maps.lua')
        field=catalog.read_lua(CACHE/game/'data/generated/field.lua')
        bases=Counter();count=Counter()
        def source(name,x,y):
            m=maps[name]
            assert m['tileset']=='CAVERN'and 0<=x<m['width']*2 and 0<=y<m['height']*2
            bid=m['blocks'][y//2*m['width']+x//2]
            q=y%2*2+x%2
            return bid,q,cells[bid,q]
        def start(name,x,y,role):
            bid,q,cell=source(name,x,y)
            row={'game':game,'style':'gen3','tileset':'CAVERN','map':name,'x':x,'y':y,'id':bid,'quadrant':q,
                 'role':role,'status':'reviewed','sourceHash':cell['grayscale_pixel_sha256'],'sourceFiles':files}
            count[role]+=1
            return row,cell
        def reference(name,mid):
            pair=manifest['layouts'][cave_review.counterpart(name)]['pair']
            cell=native[pair,mid]
            return {'game':'firered','tileset':pair,'id':mid,'hash':cell['pixel_sha256']}
        seed=cells[61,3]
        for name,m in maps.items():
            if not isinstance(m,dict)or m.get('tileset')!='CAVERN':continue
            for pos,bid in enumerate(m['blocks']):
                for q in range(4):
                    cell=cells[bid,q]
                    if cell['grayscale_pixel_sha256']!=seed['grayscale_pixel_sha256']or review.behavior_key(cell)!=review.behavior_key(seed):continue
                    x,y=pos%m['width']*2+q%2,pos//m['width']*2+q//2
                    assert y>0
                    above=tuple(source(name,x,y-1)[2]['tiles'])
                    assert above in ((5,5,5,5),(32,32,32,32),(2,3,18,19),(41,41,5,5)),above
                    base=657 if above in ((5,5,5,5),(41,41,5,5))else 641
                    bases[base]+=1
                    row,cell=start(name,x,y,'cave_ascending_ladder')
                    assert cell['tiles']==[10,11,26,27]and cell['walkable_tiles'][2]and cell['warp_tile_present']
                    assert next(w for w in m['warps']if w['x']==x and w['y']==y)['destMap']
                    row.update(kind='native_composite',base=reference(name,base),parts=[{
                        'donor':copy.deepcopy(ladder_ref),'srcX':0,'srcY':0,'w':16,'h':16,'x':0,'y':0,
                        'layers':['mid'],'layerHashes':{'mid':ladder['layer_sha256']['mid']}}],
                        evidence='Visually reviewed complete native Emerald574 upward ladder: actual Granite Cave B1F(25,13) warp to1F. '
                         'All165 original selected mid-layer pixels and both rail caps/feet remain byte-identical, no scaling/crop/32px extension. '
                         'Exact original16px source occurrence and warp anchor. Regional native ground641 or raised surface657 follows the audited adjoining source plane. '
                         'Source collision/warp/events remain unchanged; mandatory whole-source and selected-layer fingerprints.')
                    image=preview.replacement_image(CACHE,row,packed,ROOT/'TileShift')
                    row['compositionPixelHash']=catalog.sha(image.tobytes())
                    for a,b in zip(ladder_pixels.get_flattened_data(),image.get_flattened_data()):
                        if a[3]:assert a==b,'Upward ladder native material changed'
                    rows.append(row)
                    proofs.append({'game':game,'map':name,'cell':[x,y],'role':row['role'],'source_tiles':cell['tiles'],
                                   'above_tiles':above,'regional_base':base,'native_ladder_pixels_unchanged':165,
                                   'output_sha256':row['compositionPixelHash']})
        for name,x,y in BUTTONS:
            row,cell=start(name,x,y,'cave_strength_button')
            assert cell['tiles']==[43,44,45,46]and cell['walkable_tiles'][2]and not cell['warp_tile_present']
            row.update(donor=reference(name,704),evidence='Visually reviewed actual circular Strength pressure switch. '
                       'Complete native FireRed704 MB_STRENGTH_BUTTON from the corresponding Victory Road family; actual native map switch contexts verified. '
                       'Position scope names only the four real source switches. Native source boulder/switch flags and whole-block barrier replacement scripts are unchanged; '
                       'real native onBoulderMoved/replaceBlock GPU regression covers37 to29 and55 to21 without stale art.')
            rows.append(row)
            proofs.append({'game':game,'map':name,'cell':[x,y],'role':row['role'],'source_tiles':cell['tiles'],'donor':row['donor']})
        holes={('VICTORY_ROAD_3F',23,15)}
        for name,sf in field['seafoam'].items():
            for h in sf.get('holes',[]):holes.add((name,h['x'],h['y']))
            plug=sf.get('pluggedByHolesOn',{})
            for h in plug.get('holes',[]):holes.add((plug['map'],h['x'],h['y']))
        assert len(holes)==9
        for name,x,y in sorted(holes):
            row,cell=start(name,x,y,'cave_special_fall_hole')
            assert cell['tiles']==[47,47,34,34]and cell['walkable_tiles'][2]and cell['warp_tile_present']
            row.update(donor=reference(name,646),evidence='Visually reviewed special player/boulder fall hole, not a normal doorway. '
                       'Eight Seafoam occurrences exactly match the imported field.seafoam holes/pluggedByHolesOn; Victory Road3F(23,15) matches primary SwitchOrHoleCoords and dungeon warp. '
                       'Complete native same-regional FireRed646 MB_FALL_WARP, actual corresponding native cave-hole map context verified. '
                       'Real native boulderIntoHole/current GPU proof shows the source hole remains open after a boulder falls, only the original event/object/current state changes. '
                       'Original16px footprint, player landing destination, boulder cascade, collision and source event logic are unchanged.')
            rows.append(row)
            proofs.append({'game':game,'map':name,'cell':[x,y],'role':row['role'],'source_tiles':cell['tiles'],'donor':row['donor']})
        expected_bases={657:19,641:21}if game=='yellow'else{657:22,641:18}
        assert bases==expected_bases,(game,bases)
        assert count=={'cave_ascending_ladder':40,'cave_strength_button':4,'cave_special_fall_hole':9},count
    return rows,proofs


def stage_plateaus():
    """Whole block2 only: corner hashes in larger connected masses are excluded."""
    native=json.loads((ROOT/'.work/tileshift-catalog/firered.json').read_text())['cells']
    native={(r['pair'],r['mid']):r for r in native}
    manifest=catalog.read_lua(CACHE/'firered/data/generated/gba/native/manifest.lua')
    rows=[];proofs=[];held=[];scenes={};packed={}
    active=[r for path in (ROOT/'TileShift/mappings').glob('*.lua')for r in preview.read_reviewed(path)]
    for game in ('red','blue','yellow'):
        maps=catalog.read_lua(CACHE/game/'data/generated/maps.lua')
        ts=catalog.read_lua(CACHE/game/'data/generated/tilesets.lua')['CAVERN']
        sheet=Image.open(CACHE/game/ts['image'])
        data=json.loads((ROOT/f'.work/tileshift-catalog/{game}.json').read_text())
        cells={(r['block_id'],r['quadrant']):r for r in data['cells']if r['tileset']=='CAVERN'}
        files=next(r['fingerprints']for r in data['tilesets']if r['tileset']=='CAVERN')
        profile=ts['blocks'][2]
        assert profile==[4,41,41,7,49,5,5,23,49,5,5,23,40,16,16,17]
        complete_ids={i for i,block in enumerate(ts['blocks'])if block==profile}
        assert complete_ids=={2},'Only the actual complete32px source profile is permitted'
        expected_walk=[False,True,False,False]
        for q in range(4):assert cells[2,q]['walkable_tiles'][2]==expected_walk[q]
        for name,m in maps.items():
            if not isinstance(m,dict)or m.get('tileset')!='CAVERN':continue
            pair=manifest['layouts'][cave_review.counterpart(name)]['pair']
            for pos,bid in enumerate(m['blocks']):
                if bid not in complete_ids:continue
                bx,by=pos%m['width'],pos//m['width']
                if not all((pair,mid)in native for mid in (648,650,657,664,666)):
                    held.append({'game':game,'map':name,'block':[bx,by],'reason':'Required complete native regional corner is unavailable'})
                    continue
                def ref(mid):return {'game':'firered','tileset':pair,'id':mid,'hash':native[pair,mid]['pixel_sha256']}
                block_image=Image.new('RGBA',(32,32))
                for q,mid in enumerate((648,650,664,666)):
                    source=cells[bid,q]
                    assert source['grayscale_pixel_sha256']==cells[2,q]['grayscale_pixel_sha256']
                    assert review.behavior_key(source)==review.behavior_key(cells[2,q])
                    row={'game':game,'style':'gen3','tileset':'CAVERN','map':name,'id':bid,'quadrant':q,
                         'x':bx*2+q%2,'y':by*2+q//2,'role':'cave_compact_plateau_corner_'+str(q),'status':'reviewed',
                         'sourceHash':source['grayscale_pixel_sha256'],'sourceFiles':files,'kind':'native_composite',
                         'parts':[{'donor':ref(mid),'srcX':0,'srcY':0,'w':16,'h':16,'x':0,'y':0},
                                  {'donor':ref(657),'srcX':q%2*8,'srcY':q//2*8,'w':8,'h':8,
                                   'x':8 if q%2==0 else 0,'y':8 if q//2==0 else 0}],
                         'evidence':'Visually approved compact32px plateau, limited to the actual complete source block2 profile. '
                          'All16 original8px source tiles, all4 quadrant hashes, original walkability and actual neighbouring cells audited. '
                          'Complete oriented native648/650/664/666 corner cells retain the regional outline; the whole native657 flat16px plane is pasted at(8,8). '
                          'The16x16 flat footprint exactly equals the four central source tile5 materials. No generic corner-hash alias is applied inside larger platforms; '
                          'all4 rows carry actual source map-cell positions. No scaling, painting, source geometry/collision/event mutation or unavailable-donor placeholder.'}
                    image=preview.replacement_image(CACHE,row,packed,ROOT/'TileShift')
                    row['compositionPixelHash']=catalog.sha(image.tobytes())
                    block_image.paste(image,(q%2*16,q//2*16));rows.append(row)
                flat=preview.native_donor(CACHE,ref(657),packed)
                assert block_image.crop((8,8,24,24)).tobytes()==flat.tobytes(),'Native complete flat plane was clipped or shifted'
                assert block_image.getchannel('A').getextrema()==(255,255)
                neighbours=[]
                for cy in range(by*2-1,by*2+3):
                    for cx in range(bx*2-1,bx*2+3):
                        if bx*2<=cx<bx*2+2 and by*2<=cy<by*2+2:continue
                        if not(0<=cx<m['width']*2 and 0<=cy<m['height']*2):continue
                        other=m['blocks'][cy//2*m['width']+cx//2];oq=cy%2*2+cx%2
                        neighbours.append({'cell':[cx,cy],'source':[other,oq],'tiles':cells[other,oq]['tiles'],
                                           'walkable':cells[other,oq]['walkable_tiles'][2]})
                proofs.append({'game':game,'map':name,'block':[bx,by],'source_block_id':bid,'source_tiles':profile,
                               'source_walkability':expected_walk,'flat_source_tile5_positions':[[1,1],[2,1],[1,2],[2,2]],
                               'native_flat_rect_px':[8,8,16,16],'native_flat_sha256':catalog.sha(flat.tobytes()),
                               'output_sha256':catalog.sha(block_image.tobytes()),'native_pair':pair,'neighbours':neighbours})
                if game=='red'and pair not in scenes and bx>0 and by>0 and bx<m['width']-1 and by<m['height']-1:
                    selected={};positioned={}
                    for r in sorted(active,key=lambda r:bool(r.get('map'))):
                        if r['game']!=game or r['tileset']!='CAVERN'or r.get('map',name)!=name:continue
                        if 'x'in r:positioned[r['id'],r['quadrant'],r['x'],r['y']]=r
                        else:selected[r['id'],r['quadrant']]=r
                    original=Image.new('RGBA',(64,64));current=original.copy()
                    for yy in range(4):
                        for xx in range(4):
                            cx,cy=bx*2-1+xx,by*2-1+yy
                            other=m['blocks'][cy//2*m['width']+cx//2];oq=cy%2*2+cx%2
                            cell=preview.native_cell(sheet,ts,ts['blocks'][other],oq)
                            original.paste(cell,(xx*16,yy*16))
                            row=positioned.get((other,oq,cx,cy),selected.get((other,oq)))
                            if row:cell=preview.replacement_image(CACHE,row,packed,ROOT/'TileShift')
                            current.paste(cell,(xx*16,yy*16))
                    candidate=current.copy();candidate.paste(block_image,(16,16))
                    scenes[pair]=(name,bx,by,original,current,candidate)
    (OUT/'plateau-position-candidates.lua').write_text('return '+review.lua_value(rows)+'\n',encoding='utf-8')
    (OUT/'plateau-position-source-proof.json').write_text(json.dumps({'status':'staged_pending_context_activation','rows':len(rows),
        'whole_profiles':len(proofs),'counts_by_game':dict(Counter(p['game']for p in proofs)),
        'no_generic_corner_aliases':True,'held':held,'profiles':proofs},indent=2))
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
    canvas=Image.new('RGB',(960,85+len(scenes)*180),'#18212b');draw=ImageDraw.Draw(canvas)
    draw.text((12,12),'WHOLE SOURCE BLOCK2 ONLY - all4 source corners and exact16px central flat plane, with actual neighbouring cells',font=font,fill='white')
    draw.text((12,40),'Each case is a full32px profile with source collision cells [blocked,walkable,blocked,blocked]; no partial corner aliases are replaced.',font=font,fill='#c4cdd8')
    for n,(pair,(name,bx,by,original,current,candidate))in enumerate(scenes.items()):
        y=80+n*180
        for col,(label,image)in enumerate([('Source original',original),('Current approved stage',current),('Whole-profile candidate',candidate)]):
            x=12+col*200;draw.text((x,y),label,font=font,fill='white');canvas.paste(image.resize((128,128),Image.Resampling.NEAREST),(x,y+28))
        draw.multiline_text((620,y+28),name+'\nsourceblock2 at'+str((bx,by))+'\n'+pair+'\nflat plane at(8,8)16x16\nonly NE collisioncell walkable',font=font,fill='white',spacing=5)
    canvas.save(OUT/'cave-whole-profile-block2-actual-context-review.png')
    return rows,proofs


def approved_geometry():
    native_root=CACHE/'firered/data/generated/gba/native'
    manifest=catalog.read_lua(native_root/'manifest.lua')
    native=json.loads((ROOT/'.work/tileshift-catalog/firered.json').read_text())['cells']
    native={(r['pair'],r['mid']):r for r in native}
    packed={};rows=[];proofs=[];held=[];water_specs={}
    existing=extended.existing_rows()
    for game in ('red','blue','yellow'):
        data=json.loads((ROOT/f'.work/tileshift-catalog/{game}.json').read_text())
        cells={(r['block_id'],r['quadrant']):r for r in data['cells']if r['tileset']=='CAVERN'}
        files=next(r['fingerprints']for r in data['tilesets']if r['tileset']=='CAVERN')
        maps=catalog.read_lua(CACHE/game/'data/generated/maps.lua')
        for name,m in maps.items():
            if not isinstance(m,dict)or m.get('tileset')!='CAVERN':continue
            pair=manifest['layouts'][cave_review.counterpart(name)]['pair']
            def ref(mid):return {'game':'firered','tileset':pair,'id':mid,'hash':native[pair,mid]['pixel_sha256']}
            covered={(r['id'],r['quadrant'])for r in existing if r['game']==game and r['tileset']=='CAVERN'and r.get('map',name)==name and 'x'not in r}
            used={(bid,q)for bid in m['blocks']for q in range(4)}
            specs=list(DIRECTIONS)
            if name.startswith('CERULEAN_CAVE_'):specs.append((41,2,145,'cave_cerulean_rock_stairs'))
            if name in ('CERULEAN_CAVE_1F','CERULEAN_CAVE_B1F','SEAFOAM_ISLANDS_B3F','SEAFOAM_ISLANDS_B4F'):
                specs.append((118,0,299,'cave_plain_water'))
            for b,q,mid,role in specs:
                seed=cells[b,q]
                aliases=[key for key in sorted(used-covered)if cells[key]['grayscale_pixel_sha256']==seed['grayscale_pixel_sha256']
                         and cells[key]['tiles']==seed['tiles']and review.behavior_key(cells[key])==review.behavior_key(seed)]
                if not aliases:continue
                required={mid,657}if role in ('cave_west_half_face','cave_east_half_face','cave_south_half_face')else{mid}
                if not all((pair,i)in native for i in required):
                    held.append({'game':game,'map':name,'role':role,'aliases':aliases,'reason':'Exact regional native reference missing'})
                    continue
                if role=='cave_plain_water'and pair not in water_specs:
                    root=native_root/pair
                    anim=catalog.read_lua(root/'anim_manifest.lua')
                    blob=(root/'anim_water.rgba').read_bytes();length=8*len(anim['water']['mids'])*1024
                    if len(blob)!=length:blob=zlib.decompress(blob)
                    assert len(blob)==length and anim['water']['frames']==8 and 299 in anim['water']['mids']
                    spec={'bank':'water','hash':catalog.sha(blob),'manifestHash':catalog.sha((root/'anim_manifest.lua').read_bytes()),
                          'frames':8,'period':16,'phase':1,'counter':'global','counterMax':640,'format':'rgba8'}
                    frames=preview.native_water_frames(CACHE,{'donor':ref(299),'animated':True,'animation':spec},packed)
                    spec['frame0Hash']=catalog.sha(frames[0].tobytes())
                    assert len(frames)==8 and len({im.tobytes()for im in frames})==8
                    water_specs[pair]=spec
                for bid,quadrant in aliases:
                    row={'game':game,'style':'gen3','tileset':'CAVERN','map':name,'id':bid,'quadrant':quadrant,
                         'role':role,'status':'reviewed','sourceHash':cells[bid,quadrant]['grayscale_pixel_sha256'],'sourceFiles':files,
                         'donor':ref(mid),'nativeContext':{'map':cave_review.counterpart(name),'pair':pair},
                         'evidence':'Visually reviewed actual directional cave material in the corresponding native FRLG regional palette. '
                          'Exact source16px pixels, all4 underlying8px materials and walk/warp/grass flags are required; actual named map use checked. '
                          'North/sides and oriented outer/inward corners retain their actual source terrain role. '
                          'No isolated32px plateau corner aliases are inferred inside larger platforms; complete block2 profiles have separate position rows. '
                          'Original source collision, height, player affordance, field events and scripts remain authoritative.'}
                    if role in ('cave_west_half_face','cave_east_half_face','cave_south_half_face'):
                        row.pop('donor');row['kind']='native_composite'
                        if role=='cave_west_half_face':
                            assert seed['walkable_tiles']==[False,True,False,True]
                            pieces=((656,0,0,8,16,0,0),(657,8,0,8,16,8,0))
                        elif role=='cave_east_half_face':
                            assert seed['walkable_tiles']==[True,False,True,False]
                            pieces=((657,0,0,8,16,0,0),(658,8,0,8,16,8,0))
                        else:
                            assert seed['walkable_tiles']==[True,True,False,False]
                            pieces=((657,0,0,16,8,0,0),(665,0,8,16,8,0,8))
                        row['parts']=[{'donor':ref(i),'srcX':sx,'srcY':sy,'w':w,'h':h,'x':x,'y':y}for i,sx,sy,w,h,x,y in pieces]
                        row['evidence']+=' Source mixed top/face material footprint remains exactly8px per half: native657 fills only the original flat8px area. The east standing cell retains a full8px flat region instead of widening a wall under the player.'
                        row['compositionPixelHash']=catalog.sha(preview.replacement_image(CACHE,row,packed,ROOT/'TileShift').tobytes())
                    elif role=='cave_jagged_fixed_rock_cluster':
                        assert seed['tiles']==[12,13,28,29]and seed['walkable_tiles']==[False]*4
                        assert not seed['warp_tile_present']and not seed['grass_tile_present']
                        reviewed=json.loads((OUT/'cave-jagged76-native643-proof.json').read_text())
                        context=next(p for p in reviewed['native_contexts']if p['donor']['tileset']==pair)
                        assert context['donor']==ref(643)and context['native_collision_values']==[7]
                        spec=manifest['layouts'][context['map']]
                        raw=(native_root/spec['file']).read_bytes()
                        if raw[:4]!=b'SVML':raw=zlib.decompress(raw)
                        width=int.from_bytes(raw[6:8],'little');offset=16+raw[14]*raw[15]*2
                        for cx,cy in context['actual_positions']:
                            p=offset+(cy*width+cx)*4
                            assert int.from_bytes(raw[p:p+2],'little')==643 and raw[p+2]==7
                        row['nativeContext']={'map':context['map'],'pair':pair,'normalizedCollision':7}
                        row['evidence']='Visually approved complete native regional643 fixed jagged rock cluster. Exact source raw12,13,28,29, all four8px materials blocked, no grass/warp/hole flag; only actual matching source uses are aliased. Actual native regional MtMoon/Seafoam/Cerulean/RockTunnel643 placements and normalized collision7 are independently checked. No hole646, movable Strength boulder or Victory Road barrier inference. Original source collision, events, rock footprint and cave-family palette remain unchanged.'
                    elif role=='cave_cerulean_rock_stairs':
                        assert seed['tiles']==[21,22,21,22]and seed['walkable_tiles']==[True,False,True,False]
                        row['evidence']='Visually reviewed complete native Cerulean145 MB_ROCK_STAIRS, actually used on corresponding native Cerulean1F/B1F. The complete source16px staircase has left8px stair-collision material21 walkable and right8px edge material22 blocked; the authoritative bottom-left source collision remains walkable. Original paths, steps, warps and per8px/source-cell movement remain unchanged.'
                    elif role=='cave_plain_water':
                        assert seed['tiles']==[20]*4
                        row.update(animated=True,animation=copy.deepcopy(water_specs[pair]))
                        row['evidence']='Visually reviewed complete plain cave-water interior. All8 original same-regional native FR299 RGBA frames, native16tick/phase1 schedule and per-frame fingerprints verified. Actual native Cerulean1F/B1F and SeafoamB4F plain-water contexts checked. Source SeafoamB3F uses the same plain graphic before/after its current events; plain299 preserves this cue and avoids permanent false directional arrows after currents stop. Source Surf/fishing/current/forced-movement/event logic remains native, including the proven boulder-flag transitions.'
                    rows.append(row)
                    proofs.append({'game':game,'map':name,'source':[bid,quadrant],'role':role,'tiles':seed['tiles'],
                                   'walkable8':seed['walkable_tiles'],'native_pair':pair,'native_mid':mid})
        for name,bx,by,before,flag in (
            ('VICTORY_ROAD_1F',4,6,37,'EVENT_VICTORY_ROAD_1_BOULDER_ON_SWITCH'),
            ('VICTORY_ROAD_2F',11,7,37,'EVENT_VICTORY_ROAD_2_BOULDER_ON_SWITCH2'),
            ('VICTORY_ROAD_3F',3,5,37,'EVENT_VICTORY_ROAD_3_BOULDER_ON_SWITCH1'),
            ('VICTORY_ROAD_2F',3,4,55,'EVENT_VICTORY_ROAD_2_BOULDER_ON_SWITCH1')):
            m=maps[name];pair=manifest['layouts'][cave_review.counterpart(name)]['pair']
            assert m['blocks'][by*m['width']+bx]==before
            def ref(mid):return {'game':'firered','tileset':pair,'id':mid,'hash':native[pair,mid]['pixel_sha256']}
            for q in ([1]if before==37 else[1,3]):
                source=cells[before,q];assert not source['walkable_tiles'][2]
                row={'game':game,'style':'gen3','tileset':'CAVERN','map':name,'id':before,'quadrant':q,'x':bx*2+1,'y':by*2+q//2,
                     'status':'reviewed','sourceHash':source['grayscale_pixel_sha256'],'sourceFiles':files,
                     'evidence':'Visually reviewed actual Victory Road switch barrier occurrence, separate from decorative MtMoon rockfill sharing its source pixels. '
                      'Primary and actual native onBoulderMoved scripts set '+flag+' then replace the whole source block37 to29 or55 to21; real GPU regression verifies the new art follows that native block swap without stale pixels. '
                      'Source37 has one16px barrier: native775 top8 plus791 bottom8 preserve its head/foot in that cell, keeping the lower original blocked cliff face. Source55 has two stacked barrier cells and uses the full native775/791 pair. '
                      'No additional source walkable cell is covered; map collision, scripts and flags remain source-owned.'}
                if before==37:
                    row.update(role='cave_victory_barrier_compact',kind='native_composite',parts=[
                        {'donor':ref(775),'srcX':0,'srcY':0,'w':16,'h':8,'x':0,'y':0},
                        {'donor':ref(791),'srcX':0,'srcY':8,'w':16,'h':8,'x':0,'y':8}])
                    row['compositionPixelHash']=catalog.sha(preview.replacement_image(CACHE,row,packed,ROOT/'TileShift').tobytes())
                else:row.update(role='cave_victory_barrier_head' if q==1 else 'cave_victory_barrier_foot',donor=ref(775 if q==1 else 791))
                rows.append(row);proofs.append({'game':game,'map':name,'cell':[row['x'],row['y']],'source':[before,q],
                                              'role':row['role'],'source_walkable':False,'native_event':flag})
    (OUT/'directional-approved-source-proof.json').write_text(json.dumps({'rows':len(rows),'roles':dict(Counter(r['role']for r in rows)),
        'held':held,'native_water_specs':water_specs,'source_proofs':proofs},indent=2))
    return rows,proofs


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-approved',action='store_true')
    parser.add_argument('--stage-plateaus',action='store_true')
    args=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    rows,proofs=approved_features()
    plateaus,profiles=stage_plateaus()
    geometry,geometry_proofs=approved_geometry()
    rows+=plateaus+geometry
    proofs+=profiles+geometry_proofs
    candidate=OUT/'approved-feature-candidates.lua'
    candidate.write_text('return '+review.lua_value(rows)+'\n',encoding='utf-8')
    (OUT/'approved-feature-source-proof.json').write_text(json.dumps({'rows':len(rows),'roles':dict(Counter(r['role']for r in rows)),
       'source_imports_read_only':True,'native_ladder_mid_pixels':165,'source_proofs':proofs},indent=2))
    water=[row for row in geometry if row.get('animated')]
    (OUT/'approved-cave-water-candidates.lua').write_text('return '+review.lua_value(water)+'\n',encoding='utf-8')
    if args.write_approved:
        old=preview.read_reviewed(extended.TARGET)
        retained=[r for r in old if r['role']not in APPROVED_ROLES]
        extended.write_groups(retained+rows)
    print(json.dumps({'candidate':str(candidate),'approved_rows':len(rows),'roles':dict(Counter(r['role']for r in rows)),
                      'production_written':args.write_approved,'source_proofs':len(proofs)},indent=2))


if __name__=='__main__':main()
