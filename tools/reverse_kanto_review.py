"""Reviewed native GB counterparts for FireRed/LeafGreen's native tile pairs.

Only explicit semantic forward-review provenance is reused. Cropped composites,
palette-only fallbacks and source-layout-specific object fragments are excluded.
Private contact sheets/previews are extracted review material, never mod assets.
"""
from __future__ import annotations

import argparse
import copy
from collections import defaultdict
import json
from pathlib import Path

from PIL import Image
import catalog
import preview
from reverse_common import ReverseReview, STYLES, ROOT


EXACT_ROLES = {
    'short_nonencounter_grass', 'open_grassy_ground', 'forest_open_ground',
    'tall_grass', 'decorative_flower_northwest', 'decorative_flower_southeast',
    'garden_fence_pair', 'gen2_pallet_garden_fence_pair', 'gen2_pallet_open_lawn',
    'gen1_kanto_nonencounter_sandy_ground',
    'interior_house_floor', 'interior_home1_floor', 'interior_home2_floor',
    'interior_center_floor', 'interior_mart_floor', 'interior_lab_floor',
    'interior_facility_floor', 'interior_gate_floor', 'interior_tunnel_floor',
    'interior_ship_floor', 'interior_shiproom_floor', 'interior_tower_floor',
    'interior_mansion_floor', 'interior_museum_floor', 'interior_dept_floor',
    'interior_rocket_floor', 'interior_gamecorner_floor', 'interior_power_floor',
    'interior_dojo_floor', 'interior_celadongym_floor', 'interior_saffrongym_floor',
    'interior_lance_floor', 'interior_bruno_floor', 'interior_agatha_floor',
    'interior_lorelei_floor', 'interior_champion_floor', 'interior_exterior_void',
}
ROLE_PREFIXES = ('coastal_rock_shore_', 'coastal_ocean_', 'rocky_coast_',
                 'freshwater_pond_', 'south_ledge_', 'cave_',
                 'gen1_kanto_complete_native_cliff_')
TREE_SOURCE = {'gen1': ('red', 'VIRIDIAN_FOREST', 2),
               'gen2': ('crystal', 'ILEX_FOREST', 5)}


def semantic_role(row):
    role = row['role']
    if role not in EXACT_ROLES and not role.startswith(ROLE_PREFIXES):
        return False
    # Route23's unique monuments are architectural columns, not cliff faces.
    if row['tileset'] == 'PLATEAU':
        return False
    return True


def donor_map(review, row):
    maps = review.imp.table(row['game'], 'maps')
    for name in (row.get('map'), row.get('sourceMap')):
        if isinstance(name, str) and name in maps and maps[name]['tileset'] == row['tileset']:
            return name
    preferred = {'OVERWORLD': 'PALLET_TOWN', 'FOREST': 'VIRIDIAN_FOREST',
                 'CAVERN': 'MT_MOON_1F', 'TILESET_KANTO': 'PALLET_TOWN',
                 'TILESET_FOREST': 'ILEX_FOREST', 'TILESET_JOHTO': 'NEW_BARK_TOWN',
                 'TILESET_CAVE': 'UNION_CAVE_1F', 'TILESET_ICE_PATH': 'ICE_PATH_B1F'}
    candidate = preferred.get(row['tileset'])
    if candidate in maps and maps[candidate]['tileset'] == row['tileset']:
        return candidate
    return next(name for name, m in sorted(maps.items())
                if isinstance(m, dict) and m.get('tileset') == row['tileset'])


def exterior(image, colors):
    """Whole-object flood mask retains enclosed highlights and details."""
    w, h = image.size
    outside, queue = set(), []
    for y in range(h):
        for x in range(w):
            if (x in (0, w-1) or y in (0, h-1)) and image.getpixel((x,y)) in colors:
                outside.add((x,y)); queue.append((x,y))
    for x,y in queue:
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            p=x+dx,y+dy
            if 0<=p[0]<w and 0<=p[1]<h and p not in outside and image.getpixel(p) in colors:
                outside.add(p); queue.append(p)
    return outside


def runs(mask):
    spans=[]
    for y in range(16):
        x=0
        while x<16:
            if not mask[y*16+x]: x+=1; continue
            end=x+1
            while end<16 and mask[y*16+end]: end+=1
            previous=next((v for v in spans if v['x']==x and v['w']==end-x and v['y']+v['h']==y),None)
            if previous: previous['h']+=1
            else: spans.append({'x':x,'y':y,'w':end-x,'h':1})
            x=end
    return spans


def tree_art(review, style, q, ground):
    """Intact32px native GB tree; no scaling or missing upper canopy."""
    game, map_id, block = TREE_SOURCE[style]
    key=('tree32',style)
    if key not in review._gb:
        image=Image.new('RGBA',(32,32))
        for quadrant in range(4):
            image.paste(review.gb_image(review.gb_ref(game,map_id,block,quadrant)),
                        (quadrant%2*16,quadrant//2*16))
        colors={(255,255,255,255)} if game=='red' else set(review.gb_image(review.gb_at(game,map_id,10,4)).get_flattened_data())
        outside=exterior(image,colors)
        review._gb[key]=(image,outside)
    image,outside=review._gb[key]
    mask=[(q%2*16+x,q//2*16+y) not in outside for y in range(16) for x in range(16)]
    ref=review.gb_ref(game,map_id,block,q)
    parts=[dict(v,donor=ref,srcX=v['x'],srcY=v['y']) for v in runs(mask)]
    assert len(parts)<=32
    art=review.composite(ground,parts,'classic_complete_native_tree32_'+str(q))
    art['overMask']=''.join('1' if v else '0' for v in mask)
    return art


def ground_ref(review, style):
    if style=='gen1':
        return review.gb_ref('red','PALLET_TOWN',1,0)
    return review.gb_ref('crystal','PALLET_TOWN',1,0)


def aliases(review, ref):
    """Only identical source ID, full pixels, layers AND native behavior alias."""
    original=review.imp.cell_index('firered')[ref['tileset'],ref['id']]
    if not hasattr(review,'_material_aliases'):
        review._material_aliases={};review._walk_profiles={}
        import zlib
        for game in review.games:
            signatures=defaultdict(list);profiles=defaultdict(set)
            for spec in review.imp.table(game,'gba/native/manifest')['layouts'].values():
                raw=(review.cache/game/'data/generated/gba/native'/spec['file']).read_bytes()
                if raw[:4]!=b'SVML':raw=zlib.decompress(raw)
                width=int.from_bytes(raw[6:8],'little');height=int.from_bytes(raw[8:10],'little')
                offset=16+raw[14]*raw[15]*2
                for pos in range(width*height):
                    i=offset+pos*4;mid=int.from_bytes(raw[i:i+2],'little')
                    profiles[spec['pair'],mid].add(bool(review.imp.permissions.isWalkable(raw[i+2])))
            for (pair,mid),cell in review.imp.cell_index(game).items():
                signature=cell['pixel_sha256'],cell['behavior'],json.dumps(cell['layer_sha256'],sort_keys=True)
                signatures[signature].append((pair,mid))
            review._material_aliases[game]=signatures;review._walk_profiles[game]=profiles
    if not hasattr(review,'_context_aliases'):
        review._context_aliases={}
        source=review.imp.table('firered','gba/native/manifest')['layouts']
        for game in review.games:
            target=review.imp.table(game,'gba/native/manifest')['layouts'];known=defaultdict(set)
            for name,a in source.items():
                b=target.get(name)
                if not b or(a['width'],a['height'])!=(b['width'],b['height']):continue
                left=(review.cache/'firered/data/generated/gba/native'/a['file']).read_bytes()
                right=(review.cache/game/'data/generated/gba/native'/b['file']).read_bytes()
                if catalog.sha(left)==catalog.sha(right):known[a['pair']].add(b['pair'])
            review._context_aliases[game]=known
    for game in review.games:
        signature=original['pixel_sha256'],original['behavior'],json.dumps(original['layer_sha256'],sort_keys=True)
        for pair,mid in review._material_aliases[game].get(signature,[]):
            cell=review.imp.cell_index(game)[pair,mid]
            contextual=pair in review._context_aliases[game].get(ref['tileset'],set())
            material=(ref.get('material') and review._walk_profiles['firered'].get((ref['tileset'],ref['id']))
                      ==review._walk_profiles[game].get((pair,mid)))
            if ((material or mid==ref['id'] and (mid<640 or contextual))
                and cell['pixel_sha256']==original['pixel_sha256']
                and cell['behavior']==original['behavior']
                and cell['layer_sha256']==original['layer_sha256']):
                yield game,pair,mid


def reviewed_direct(review):
    grouped=defaultdict(list)
    for path in sorted((ROOT/'mappings').glob('*.lua')):
        if path.name.startswith('reverse_'): continue
        for row in preview.read_reviewed(path):
            ref=row.get('donor',{})
            if row['game'] not in ('red','crystal') or ref.get('game')!='firered' or row.get('kind') not in ('native',None) or not semantic_role(row): continue
            source=review.imp.cell_index('firered')[ref['tileset'],ref['id']]
            key=(row['game'],'',0,ref['hash'],source['behavior'],
                 json.dumps(source['layer_sha256'],sort_keys=True))
            grouped[key].append(row)
    held=[];seeds=[]
    for (game,pair,mid,sha,behavior,layers),choices in sorted(grouped.items()):
        hashes={r['sourceHash'] for r in choices}
        if len(hashes)!=1:
            held.append({'donor_game':game,'pair':pair,'mid':mid,'reason':'Different originalGB motifs need explicit canonical review','roles':sorted({r['role'] for r in choices})})
            continue
        contexts=set()
        for candidate in choices:
            context_ref=review.gb_ref(game,donor_map(review,candidate),candidate['id'],candidate['quadrant'])
            contexts.add(catalog.sha(review.gb_image(context_ref).tobytes()))
        if len(contexts)!=1:
            held.append({'donor_game':game,'pair':pair,'mid':mid,'reason':'Different GB palette/room contexts remain held','roles':sorted({r['role']for r in choices})})
            continue
        # Map context controls Crystal color. Equal neutral pixels alone do not
        # approve a different roof/palette: one reviewed context remains exact.
        row=sorted(choices,key=lambda r:(r.get('map') is None,r.get('map',''),r['role']))[0]
        map_id=donor_map(review,row)
        ref=review.gb_ref(game,map_id,row['id'],row['quadrant'])
        assert ref['hash']==row['sourceHash']
        style='gen1'if game=='red'else'gen2'
        art=review.native(ref,'classic_'+row['role'])
        original=dict(row['donor'],material=True)
        for source_game,source_pair,source_mid in aliases(review,original):
            review.row(source_game,source_pair,source_mid,style,art,
                       'Explicit semantic material counterpart previously reviewed in the original and FireRed native context: '+row['role']+'. Complete original16px GB quadrant retained at1:1. Material aliases require exact RGBA, all three layer hashes, native behavior and layout walkability profile; mixed originalGB motifs or colored room contexts remain held. Numeric IDs are not evidence of equivalence. Source map layout, collision, events and scripts are not modified.')
        seeds.append({'game':game,'map':map_id,'source':original,'role':row['role'],'GB':ref})
    (review.out/'held-ambiguous.json').write_text(json.dumps(held,indent=2),encoding='utf-8')
    (review.out/'reviewed-direct-seeds.json').write_text(json.dumps(seeds,indent=2),encoding='utf-8')


def canonical_room_floors(review):
    """Canonical pure floor proofs retain explicit actual-room counterparts."""
    from interior_review import FLOORS, PAIRS
    assigned=set()
    for stem,game,map_id,native_game,native_map in PAIRS:
        if game not in ('red','crystal')or native_game!='firered'or stem not in FLOORS:continue
        bid,q,mid=FLOORS[stem];style='gen1'if game=='red'else'gen2'
        native=review.imp.table('firered','gba/native/manifest')['layouts'][native_map]
        ref=review.gb_ref(game,map_id,bid,q)
        for source_game,pair,alias in aliases(review,{'tileset':native['pair'],'id':mid}):
            key=source_game,style,pair,alias
            if key in assigned:continue
            assigned.add(key)
            replace_row(review,source_game,pair,alias,style,review.native(ref,'classic_'+stem.replace('-','_')+'_plain_floor'),
                'Explicit complete plain-floor proof from the actual original/remake room pairing '+map_id+' / '+native_map+'. No furniture, wall/shadow, doorway or carpet fragments are used. Shared native material IDs choose one canonical original floor (main house before upstairs variants) rather than inferring meaning from collision or frequency. Original source movement and events remain unchanged.')
    # The original Gen1 cavern's uniform ordinary floor is raw32 (block1q0),
    # distinct from elevated speckled rock5 and hatched/solid border materials.
    ref=review.gb_ref('red','MT_MOON_1F',1,0)
    seeds=json.loads((review.out/'reviewed-direct-seeds.json').read_text())
    contexts={(r['source']['tileset'],r['source']['id'])for r in seeds if r['role']=='cave_rock_floor'}
    # Ambiguous forward groups can still identify the actual native cave
    # floor; choosing the known canonical raw32 source resolves geometry only.
    for path in sorted((ROOT/'mappings').glob('gen1_cave*.lua')):
        for row in preview.read_reviewed(path):
            d=row.get('donor',{})
            if d.get('game')=='firered'and row['role']=='cave_rock_floor':contexts.add((d['tileset'],d['id']))
    for pair,mid in contexts:
        for game,source_pair,alias in aliases(review,{'tileset':pair,'id':mid}):
            replace_row(review,game,source_pair,alias,'gen1',review.native(ref,'classic_cave_ordinary_floor'),
                'Actual original Gen1 cavern ordinary floor: uniform raw32, block1q0, reviewed separately from elevated rock5 and hatched borders. Replaces only the existing explicit native cave-floor counterpart; sand, special holes, dark pits and puzzle glyphs are excluded. All native walking, sand/encounter effects and source scripts are preserved.')


def trees(review):
    index=review.imp.cell_index('firered')
    for mid,q in ((28,0),(29,1),(30,0),(31,1),(20,2),(21,3),(22,2),(23,3),(36,2),(37,3),(38,2),(39,3)):
        source=index['pallet_outdoor',mid]
        original={'tileset':'pallet_outdoor','id':mid,'hash':source['pixel_sha256']}
        for style in STYLES:
            art=tree_art(review,style,q,ground_ref(review,style))
            # The occupied native32px body is BG1, not decorative BG2.
            # Dense bridge tiles contain the NEXT tree's BG2 cap; remove it
            # rather than putting the GB trunk over a character in front.
            art['overMask']='0'*256
            for game,pair,alias in aliases(review,original):
                review.row(game,pair,alias,style,art,
                    'Complete native32x32 GB tree: Red FOREST block2 or Crystal FOREST block5, all four quadrants reviewed together. Original pixel size, canopy, trunk and root silhouette retained. Whole-object exterior flood removes only outside ground, retaining internal highlights. The full silhouette is used for image composition; the occupied tree body retains native BG1 ordering and the unused next-tree BG2 cap is cleared. Uncovered pixels retain selected GB ground and actors. Dense native bridge variants keep the original32px occupied footprint. All original source collision and events remain unchanged.')
    for mid in (14,15):
        source=index['pallet_outdoor',mid]
        original={'tileset':'pallet_outdoor','id':mid,'hash':source['pixel_sha256']}
        for style in STYLES:
            art=review.native(ground_ref(review,style),'classic_tree_unused_decorative_cap_ground')
            art['overMask']='0'*256
            for game,pair,alias in aliases(review,original):
                replace_row(review,game,pair,alias,style,art,
                    'Original standalone16px GBA decorative tree cap lies above the occupied32x32 tree body. The complete nativeGB32x32 tree remains anchored to that body; this unused upper extension restores GB ground and clears BG2, adding no collision or invisible foreground.')


def replace_row(review,game,pair,mid,style,art,evidence):
    review.rows.pop((game,style,pair,mid,None),None)
    return review.row(game,pair,mid,style,art,evidence)


def canonical_terrain(review):
    """Manual whole-cell counterparts reviewed against Pallet's native atlas."""
    for style,game in STYLES.items():
        ground=ground_ref(review,style)
        path=review.gb_ref('red','PALLET_TOWN',1,2)if style=='gen1'else review.gb_at('crystal','PALLET_TOWN',2,3)
        flower=review.gb_ref('red','PALLET_TOWN',116,0)if style=='gen1'else review.gb_ref('crystal','NEW_BARK_TOWN',4,0)
        water=review.gb_ref(game,'PALLET_TOWN',29,3)
        sign=review.gb_at(game,'PALLET_TOWN',3,5)
        specs={}
        for mid in (1,8,9,17,671):specs[mid]=(ground,'ordinary_tufted_ground')
        for mid in (645,646,648,652,654,655,656,661,662,663,670,678,679,686,687,694,701,702,703,710,711,718):specs[mid]=(path,'open_path_or_path_edge')
        specs[4]=(flower,'complete_native_flower_patch')
        specs[299]=(water,'coastal_ocean_water_interior')
        specs[2]=(sign,'freestanding_sign');specs[3]=(sign,'freestanding_wooden_sign');specs[685]=(sign,'home_label_mailbox_counterpart')
        fence=review.rows['firered',style,'pallet_outdoor',644,None]['donor']
        specs[647]=(fence,'garden_fence_pair')
        for mid,(ref,role)in specs.items():
            original={'tileset':'pallet_outdoor','id':mid,'material':role in('ordinary_tufted_ground','open_path_or_path_edge','coastal_ocean_water_interior')}
            if ('pallet_outdoor',mid)not in review.imp.cell_index('firered'):continue
            art=review.native(ref,'classic_'+role)
            if mid in(2,3,685):
                image=review.gb_image(sign)
                bg=set(review.gb_image(review.gb_at(game,'PALLET_TOWN',3,4)).get_flattened_data())
                outside=exterior(image,bg)
                mask=[(x,y)not in outside for y in range(16)for x in range(16)]
                parts=[dict(p,donor=sign,srcX=p['x'],srcY=p['y'])for p in runs(mask)]
                art=review.composite(path if mid==685 else ground,parts,'classic_'+role)
                art['overMask']='0'*256
            for source_game,pair,alias in aliases(review,original):
                replace_row(review,source_game,pair,alias,style,art,
                    'Manual native Pallet/route material review: '+role+'. Ordinary walkable GB ground uses actual Pallet tufted flooring, not the similarly named blocked gray border hatching. Path/open-ground, native complete flowers, water and signs use their original16px counterparts without scaling. Plain material aliases require exact pixels, all layer hashes, native behavior and layout walkability; architectural secondary IDs stay in proven paired map contexts.')
        for source_game,pair,alias in aliases(review,{'tileset':'pallet_outdoor','id':677}):
            art=review.native(path,'classic_house_label_unused_mailbox_cap');art['overMask']='0'*256
            replace_row(review,source_game,pair,alias,style,art,
                'The source mailbox is32px high; its original GB house-label counterpart is a complete16px sign anchored to the original lower cell. Clear only the unused decorative upper dome to matching GB ground, retaining original interaction/collision and no invisible BG2 rectangle.')
        # Gen1 and Gen2 tall grass use their real encounter-grass art, not
        # ordinary green flooring. Encounter and walking flags stay original.
        if game=='red':
            ts=review.imp.table(game,'tilesets')['OVERWORLD'];wanted=ts['grassTile'];grass=None
            for bid,b in enumerate(catalog.lua_array(ts['blocks'])):
                b=catalog.lua_array(b)
                for q in range(4):
                    x,y=q%2*2,q//2*2
                    if [b[y*4+x],b[y*4+x+1],b[(y+1)*4+x],b[(y+1)*4+x+1]]==[wanted]*4:
                        grass=review.gb_ref(game,'ROUTE_1',bid,q);break
                if grass:break
        else:grass=review.gb_ref('crystal','ROUTE_33',3,0)
        assert grass
        for mid in (11,12,13):
            seed=next((c for (p,i),c in review.imp.cell_index('firered').items()
                       if i==mid and c['behavior_hint']=='MB_TALL_GRASS'and p.startswith('general__')),None)
            assert seed
            for source_game,pair,alias in aliases(review,{'tileset':seed['pair'],'id':mid}):
                replace_row(review,source_game,pair,alias,style,review.native(grass,'classic_tall_grass'),
                    'Actual native FireRed tall-grass variants11/12/13 reviewed as encounter grass, replaced by a complete native GB encounter-grass quadrant at1:1. Original native encounter, footstep and movement behavior remains unchanged.')


def clip_parts(parts, mask):
    result=[]
    for r in runs(mask):
        for p in parts:
            x=max(r['x'],p.get('x',0));y=max(r['y'],p.get('y',0))
            right=min(r['x']+r['w'],p.get('x',0)+p['w']);bottom=min(r['y']+r['h'],p.get('y',0)+p['h'])
            if right>x and bottom>y:
                v=copy.deepcopy(p);v.update(x=x,y=y,w=right-x,h=bottom-y,
                    srcX=p.get('srcX',0)+x-p.get('x',0),srcY=p.get('srcY',0)+y-p.get('y',0));result.append(v)
    assert len(result)<=32, len(result)
    return result


def pallet_homes(review):
    # Actual native roof/window/door family for both Pallet homes. The source
    # door is relative(1,4); every original entrance remains at that position.
    native_rows=((641,642,642,642,643),(649,650,650,650,651),
                 (657,659,658,658,660),(664,665,666,667,668),
                 (672,675,674,673,676))
    for style,game in STYLES.items():
        parts_by_cell={};whole=Image.new('RGBA',(80,80))
        def full(x,y):return review.gb_rect(game,'PALLET_TOWN',x*16,y*16,16,16)
        def boards(edge=None,foundation=False):
            parts=[]
            for yy in (0,8):
                for xx in (0,8):
                    sx=72;sy=80
                    if edge=='left'and xx==0:sx=64
                    if edge=='right'and xx==8:sx=120
                    parts+=review.gb_rect(game,'PALLET_TOWN',sx,sy,8,8,xx,yy)
            if foundation:
                # Preserve the complete original native footing/bottom edge.
                parts=clip_parts(parts,[y<12 for y in range(16)for x in range(16)])
                parts+=review.gb_rect(game,'PALLET_TOWN',96,92,16,4,0,12)
            return parts
        for y,row in enumerate(native_rows):
            for x,mid in enumerate(row):
                if y==0:parts=full(4 if x==0 else 7 if x==4 else 5,3)
                elif y==1:parts=full(4 if x==0 else 7 if x==4 else 5,4)
                elif y==2:parts=boards('left'if x==0 else'right'if x==4 else None)
                elif y==3:
                    parts=boards('left'if x==0 else'right'if x==4 else None)if x in(0,4)else full(6,5)
                else:
                    parts=full(4,5)if x==0 else full(5,5)if x==1 else full(7,5)if x==4 else boards(foundation=True)if x==2 else full(6,5)
                parts_by_cell[x,y]=parts
                whole.paste(review.render(review.composite(None,parts,'house_draft')),(x*16,y*16))
        bg=set(review.gb_image(review.gb_ref('red','PALLET_TOWN',1,2)if game=='red'else review.gb_at(game,'PALLET_TOWN',2,3)).get_flattened_data())
        if game=='crystal':bg.update(review.gb_image(ground_ref(review,style)).get_flattened_data())
        outside=exterior(whole,bg)
        for y,row in enumerate(native_rows):
            for x,mid in enumerate(row):
                mask=[(x*16+xx,y*16+yy)not in outside for yy in range(16)for xx in range(16)]
                path=review.gb_ref('red','PALLET_TOWN',1,2)if game=='red'else review.gb_at('crystal','PALLET_TOWN',2,3)
                art=review.composite(path,clip_parts(parts_by_cell[x,y],mask),'classic_fullsize_pallet_home')
                original={'tileset':'pallet_outdoor','id':mid};source=review.imp.cell_index('firered')['pallet_outdoor',mid]
                empty=catalog.sha(bytes(1024))
                art['overMask']=''.join('1'if v else'0'for v in mask)if source['layer_sha256']['over']!=empty else'0'*256
                for source_game,pair,alias in aliases(review,original):
                    key=(source_game,style,pair,alias,None)
                    if key in review.rows and review.rows[key]['role']=='classic_fullsize_pallet_home':
                        assert review.rows[key]['compositionPixelHash']==catalog.sha(review.render(art).tobytes()),('Native repeated house cell needs distinct artwork',mid,x,y)
                        continue
                    replace_row(review,source_game,pair,alias,style,art,
                        'Original complete GB Pallet roof, window panels, doorway frame and foundation retained at native pixel size. Native repeatable8px plain siding and whole window/roof modules extend the facade to the original80x80 FireRed footprint; no downscaling or clipped unique features. Door stays at relative1,4. Whole-building exterior flood keeps unused corners transparent to selected GB ground; BG2 occlusion follows the opaque counterpart within the original source overhang layers. Original source collisions, scripts and warps remain untouched.')
        whole.save(review.out/(style+'-fullsize-home-source.png'))


def pallet_lab(review):
    """Complete native GB Oak's Lab, extended only with repeating brick/roof."""
    native_rows=((680,681,681,681,681,701,693),
                 (688,689,689,689,689,691,692),
                 (696,697,697,697,697,699,700),
                 (704,705,720,706,707,708,709),
                 (712,713,728,684,715,716,717))
    for style,game in STYLES.items():
        whole=Image.new('RGBA',(112,80));parts_by_cell={}
        def full(x,y):return review.gb_rect(game,'PALLET_TOWN',x*16,y*16,16,16)
        def roof_texture(edge=None):
            # Native8px repeatable diamond texture/vertical side shingles.
            # The ridge, lower roof band and sloping eaves remain intact in
            # their original complete source rows on either side of this.
            sx=160 if edge=='left'else 240 if edge=='right'else 176
            return (review.gb_rect(game,'PALLET_TOWN',sx,144,16,8,0,0)
                    +review.gb_rect(game,'PALLET_TOWN',sx,144,16,8,0,8))
        for y,row in enumerate(native_rows):
            for x,mid in enumerate(row):
                if y==0:parts=full(10 if x==0 else 15 if x==6 else 11,8)
                elif y==1:parts=roof_texture('left'if x==0 else'right'if x==6 else None)
                elif y==2:parts=full(10 if x==0 else 15 if x==6 else 11,9)
                elif y==3:parts=full((10,11,12,12,13,14,15)[x],10)
                else:parts=full((10,11,11,12,13,14,15)[x],11)
                parts_by_cell[x,y]=parts
                whole.paste(review.render(review.composite(None,parts,'lab_draft')),(x*16,y*16))
        path=review.gb_ref('red','PALLET_TOWN',1,2)if game=='red'else review.gb_at('crystal','PALLET_TOWN',2,3)
        bg=set(review.gb_image(path).get_flattened_data())
        if game=='crystal':bg.update(review.gb_image(ground_ref(review,style)).get_flattened_data())
        outside=exterior(whole,bg)
        for y,row in enumerate(native_rows):
            for x,mid in enumerate(row):
                mask=[(x*16+xx,y*16+yy)not in outside for yy in range(16)for xx in range(16)]
                art=review.composite(path,clip_parts(parts_by_cell[x,y],mask),'classic_fullsize_pallet_lab')
                # The classic complete roof fills the original top-row
                # chimney recess. It is decorative and can cover an actor
                # behind the roof without changing the original walkability.
                source=review.imp.cell_index('firered')['pallet_outdoor',mid]
                art['overMask']=''.join('1'if v else'0'for v in mask)if y==0 or source['layer_sha256']['over']!=catalog.sha(bytes(1024))else'0'*256
                for source_game,pair,alias in aliases(review,{'tileset':'pallet_outdoor','id':mid}):
                    key=(source_game,style,pair,alias,None)
                    if key in review.rows and review.rows[key]['role']=='classic_fullsize_pallet_lab':
                        assert review.rows[key]['compositionPixelHash']==catalog.sha(review.render(art).tobytes()),('Lab repeated native cell requires distinct art',mid,x,y)
                        continue
                    replace_row(review,source_game,pair,alias,style,art,
                        'Whole original GB Oak laboratory: complete two-row roof, both full window banks, original brick courses, entrance frame and foundation remain at1:1. Repeat only plain roof/brick sections and whole window modules to fill the original112x80 FireRed visual footprint. Door remains at originalrelative3,4. The actual Gen1/Gen2 laboratory counterpart has no Gen3 chimney; its complete roof fills that decorative recess with transparent outside pixels. Original collision, warps, labels and scripts remain unchanged; actors can pass behind its opaque top-row roof.')
        whole.save(review.out/(style+'-fullsize-lab-source.png'))


def native_animations(review):
    """Use the imported cartridge's actual8px water/flower animation banks."""
    from gb_theme_animation import specification
    specs={};count=defaultdict(int)
    for row in review.rows.values():
        ref=row.get('donor')
        if not ref:continue
        bank='flower'if 'flower'in row['role']else'water'if any(s in row['role']for s in('water','pond','coast'))else None
        if bank is None:continue
        ts=review.imp.table(ref['game'],'tilesets')[ref['tileset']]
        block=catalog.lua_array(catalog.dict_at(ts['blocks'],ref['id']+1));q=ref.get('quadrant',0);x,y=q%2*2,q//2*2
        materials=[block[y*4+x],block[y*4+x+1],block[(y+1)*4+x],block[(y+1)*4+x+1]]
        if(3 if bank=='flower'else 20)not in materials:continue
        key=ref['game'],ref['tileset'],bank
        if key not in specs:specs[key]=specification(review.cache,ref,bank)
        if specs[key] is None:continue
        row.update(animated=True,animation=copy.deepcopy(specs[key]),animationCategory='flowers'if bank=='flower'else'water')
        row['compositionPixelHash']=catalog.sha(review.render(row).tobytes())
        row['evidence']+=' Native imported GB '+bank+' frames are fingerprinted and cached; only the actual animated8px materials change, with static land/furniture preserved.'
        count[row['style'],bank]+=1
    (review.out/'animation-summary.json').write_text(json.dumps({str(k):v for k,v in count.items()},indent=2),encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--validate',action='store_true');parser.add_argument('--activate',action='store_true');args=parser.parse_args()
    assert not args.activate or args.validate
    review=ReverseReview('kanto',('firered','leafgreen'))
    reviewed_direct(review);canonical_room_floors(review);trees(review);canonical_terrain(review);pallet_homes(review);pallet_lab(review);native_animations(review)
    if args.validate:review.validate()
    target=ROOT/'mappings/reverse_kanto.lua'if args.activate else review.out/'candidate.lua'
    review.write(target)
    results=[]
    for game in review.games:
        for name in ('FR_PALLET_TOWN','FR_VIRIDIAN_CITY','FR_ROUTE_1','FR_PLAYERS_HOUSE_1F','FR_VIRIDIAN_CITY_POKEMON_CENTER_1F','FR_MT_MOON_1F'):
            if name not in review.imp.table(game,'gba/native/manifest')['layouts']:continue
            for style in STYLES:results.append(review.map_preview(game,name,style))
    print(json.dumps({'rows':len(review.rows),'target':str(target),'maps':results},indent=2))


if __name__=='__main__':main()
