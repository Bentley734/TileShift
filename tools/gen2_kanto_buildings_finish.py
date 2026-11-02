"""Place complete native exterior objects on reviewed whole source footprints.

Complete GSC source signatures and destination attributes are guarded. Explicit
whole-object motif aliases additionally record their original town contexts,
native art rectangle and entrance purpose/offset. Closed buildings stay closed.
This never matches isolated doors or roof/window tiles by numeric ID. Small
homes gain an intact native48px design with a transparent extra upper row.
"""
import argparse,copy,json,os,hashlib
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
import catalog,preview,gen2_extended_review as e
from johto_remaining_review import artwork
from center_mart_overhang_review import write_rows

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'.work/tileshift-gen2-kanto-buildings'
TARGET=ROOT/'mappings/gen2_kanto_buildings_finish.lua'
ROOFS=ROOT/'lib/gen2_kanto_building_roofs.lua'
CATALOGS=('roof_catalog.lua','side_catalog.lua','center_mart_roofs.lua','goldenrod_roofs.lua','pallet_roofs.lua','johto_roofs.lua')

def stable(value):
    if isinstance(value,dict):return {key:stable(value[key])for key in sorted(value,key=str)}
    if isinstance(value,list):return [stable(item)for item in value]
    return value

def art(r):
    result=artwork(r)
    for field in ('buildingCompact',):
        if field in r:result[field]=copy.deepcopy(r[field])
    return result

def building(r):
    role=r['role']
    return r.get('x') is not None and ('architecture_' in role or role in('larger_center','larger_mart',
        'newbark_player_building','newbark_ordinary_building','newbark_lab_building') or
        role.startswith(('ecruteak_original_','goldenrod_native_','pallet_larger_')))

def safe_native_art(row):
    """A Gen1 review must never reintroduce its generated assets into GSC."""
    if row.get('kind')=='source_palette':return False
    def safe(value):
        if isinstance(value,str):
            return not value.startswith(('assets/original/','assets/user_flora/','assets/generated/'))
        if isinstance(value,dict):return all(safe(v)for v in value.values())
        if isinstance(value,list):return all(safe(v)for v in value)
        return True
    return safe(art(row))

def source_shape(cache,game,data,tileset,bid,q):
    """Compare palette-neutral shade indices, never cross-generation collision IDs."""
    shapes=data.setdefault('building_shapes',{})
    key=(tileset,bid,q)
    if key in shapes:return shapes[key]
    ts=data['sets'][tileset]
    if tileset not in data['sheets']:
        data['sheets'][tileset]=__import__('PIL.Image',fromlist=['Image']).open(cache/game/ts['image']).convert('RGBA')
        data['fingerprints'][tileset]={
            'metadata':catalog.sha((cache/game/'data/generated/tilesets.lua').read_bytes()),
            'image':catalog.sha((cache/game/ts['image']).read_bytes()),
            'maps':catalog.sha((cache/game/'data/generated/maps.lua').read_bytes())}
    sheet=data['sheets'][tileset]
    levels=data.setdefault('building_levels',{}).get(tileset)
    if levels is None:
        levels=sorted({p[0]for p in sheet.get_flattened_data()},reverse=True)
        assert len(levels)==4 and all(p[0]==p[1]==p[2]for p in sheet.get_flattened_data())
        data['building_levels'][tileset]=levels
    image=preview.native_cell(sheet,ts,catalog.lua_array(catalog.dict_at(ts['blocks'],bid+1)),q)
    neutral=bytes(levels.index(p[0])for p in image.get_flattened_data())
    shapes[key]=(hashlib.sha256(neutral).hexdigest(),catalog.sha(image.tobytes()))
    return shapes[key]

def templates_for(cache,game,data,active):
    grouped=defaultdict(dict)
    for r in active:
        if r['game']==game and building(r)and safe_native_art(r):
            grouped[r['map'],r['role']][r['x'],r['y']]=r
    templates=[]
    for(name,role),points in sorted(grouped.items()):
        todo=set(points)
        while todo:
            start=min(todo);todo.remove(start);queue=[start];component={start}
            for x,y in queue:
                for point in((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                    if point in todo:todo.remove(point);component.add(point);queue.append(point)
            x0,y0=min(x for x,y in component),min(y for x,y in component)
            w,h=max(x for x,y in component)-x0+1,max(y for x,y in component)-y0+1
            if len(component)!=w*h or w<4 or h<2:continue
            definition=data['maps'][name]
            warps=[z for z in definition.get('warps',[])if x0<=z['x']<x0+w and y0<=z['y']<y0+h]
            # Adjacent4x2 ordinary homes can share their roof edge. Separate
            # complete four-cell homes around their independently checked doors.
            rectangles=[(x0,y0,w,h)]
            if role=='architecture_home32'and h==2 and w%4==0 and len(warps)==w//4:
                rectangles=[(z['x']-1,y0,4,2)for z in warps]
            for ox,oy,rw,rh in rectangles:
                if any((ox+x,oy+y)not in points for y in range(rh)for x in range(rw)):continue
                doors=[z for z in definition.get('warps',[])if ox<=z['x']<ox+rw and oy<=z['y']<oy+rh]
                if len(doors)!=1 or doors[0]['y']!=oy+rh-1:continue
                rows=[points[ox+x,oy+y]for y in range(rh)for x in range(rw)]
                shape=[]
                for r in rows:
                    normalized,raw=source_shape(cache,game,data,definition['tileset'],r['id'],r['quadrant'])
                    assert raw==r['sourceHash'],'Reviewed complete building source pixels changed'
                    shape.append(normalized)
                templates.append(dict(game=game,map=name,role=role,x=ox,y=oy,w=rw,h=rh,rows=rows,shape=shape,
                    door=[doors[0]['x']-ox,doors[0]['y']-oy],purpose=purpose(doors[0]['destMap']),tileset=definition['tileset']))
    return templates

def purpose(name):
    if 'NAME_RATER' in name or 'WARDENS_HOME' in name:return 'house'
    if name.endswith('GAME_CORNER'):return 'arcade'
    if 'GAME_CORNER_PRIZE_ROOM' in name:return 'prize_room'
    if name.endswith(('_CAFE','_DINER')):return 'cafe'
    if 'POKECENTER' in name:return 'center'
    if name.endswith('_MART')or 'DEPT_STORE' in name:return 'mart'
    if '_GYM' in name or 'DOJO' in name:return 'gym'
    if '_LAB' in name:return 'lab'
    if '_GATE' in name:return 'gate'
    if 'FAN_CLUB' in name:return 'fan_club'
    if 'HOUSE' in name:return 'house'
    return name

def reviewed_kanto_aliases(cache,game,data,red,active):
    """Whole native Kanto structures reviewed in both original town contexts.

    GSC changed the window/brick drawing, not these complete silhouettes.
    Each alias uses a complete Red-reviewed native rectangle at 1:1. These
    references are explicit; isolated door/roof similarity never approves one.
    """
    specs=(
        ('brick_house', (26,26,4,4), (28,26,4,4), [1,3], 'house'),
        ('closed_brick_house', (4,8,4,4), (0,32,4,4), [0,3], '__CLOSED__'),
        ('closed_tall_brick_house', (6,16,4,6), (6,16,4,6), [0,5], '__CLOSED__'),
        ('silph_office', (16,10,8,12), (16,10,8,12), [2,11], 'SILPH_CO_1F'),
        ('celadon_mansion', (14,4,6,6), (22,4,6,6), [2,5], 'CELADON_MANSION_1F',
            dict(map='CELADON_CITY',native_map='CELADON_CITY')),
        ('celadon_arcade', (16,16,6,4), (26,16,6,4), [2,3], 'arcade',
            dict(map='CELADON_CITY',native_map='CELADON_CITY')),
        ('celadon_prize_house', (22,16,4,4), (32,16,4,4), [1,3], 'prize_room',
            dict(map='CELADON_CITY',native_map='CELADON_CITY')),
        ('celadon_cafe', (24,26,4,4), (30,24,4,4), [1,3], 'cafe',
            dict(map='CELADON_CITY',native_map='CELADON_CITY')),
        ('soul_house', (12,8,6,4), (28,26,4,4), [1,3], 'house',
            dict(map='LAVENDER_TOWN',columns=[0,1,2,2,2,3])),
        ('closed_museum_main', (10,2,8,6), (10,2,8,6), [0,5], '__CLOSED__',
            dict(map='PEWTER_CITY',native_map='PEWTER_CITY',close_source_door=True)),
        ('closed_museum_annex', (18,2,6,4), (18,2,6,4), [0,3], '__CLOSED__',
            dict(map='PEWTER_CITY',native_map='PEWTER_CITY',close_source_door=True)),
    )
    result=[]
    for spec in specs:
        role,target_rect,art_rect,door,destination=spec[:5];options=spec[5]if len(spec)>5 else{}
        name=options.get('map','SAFFRON_CITY');native_name=options.get('native_map','SAFFRON_CITY')
        definition=data['maps'][name];native=red['maps'][native_name]
        selected=[r for r in active if r['game']=='red' and r['tileset']==native['tileset'] and r.get('map',native_name)==native_name]
        x0,y0,w,h=target_rect;rx,ry,rw,rh=art_rect;columns=options.get('columns',list(range(w)))
        assert h==rh and len(columns)==w and set(columns)==set(range(rw))
        target_doors=[z for z in definition.get('warps',[])if x0<=z['x']<x0+w and y0<=z['y']<y0+h]
        assert (not target_doors)if destination=='__CLOSED__'else(len(target_doors)==1 and
            [target_doors[0]['x']-x0,target_doors[0]['y']-y0]==door and purpose(target_doors[0]['destMap'])==destination)
        source_doors=[z for z in native.get('warps',[])if rx<=z['x']<rx+w and ry<=z['y']<ry+h]
        assert (not source_doors or options.get('close_source_door'))if destination=='__CLOSED__'else(len(source_doors)==1 and
            [source_doors[0]['x']-rx,source_doors[0]['y']-ry]==door and purpose(source_doors[0]['destMap'])==destination)
        rows=[];shape=[];native_shape=[]
        for y in range(h):
            for x in range(w):
                xx,yy=rx+columns[x],ry+y;bid=native['blocks'][yy//2*native['width']+xx//2];q=yy%2*2+xx%2
                source_was_door=any(z['x']==xx and z['y']==yy for z in source_doors)
                if options.get('close_source_door')and source_was_door:
                    # The GSC museum is closed. A complete native plain siding
                    # module replaces the old Red entrance, never a fake door.
                    replacement_map=red['maps']['SAFFRON_CITY'];xx,yy=1,35
                    bid=replacement_map['blocks'][yy//2*replacement_map['width']+xx//2];q=yy%2*2+xx%2
                candidates=[r for r in selected if r['id']==bid and r['quadrant']==q and
                    (r.get('x')is None or(r['x'],r['y'])==(xx,yy))]
                candidates.sort(key=lambda r:(r.get('map')is not None,r.get('x')is not None))
                assert candidates,('Missing complete native source building cell',role,xx,yy)
                r=candidates[-1];assert safe_native_art(r),('Generated/held artwork cannot cross generations',role,xx,yy)
                assert r['role'].startswith('gen1_kanto_')and any(v in r['role']for v in('roof','wall','siding','window','door'))
                neutral,raw=source_shape(cache,'red',red,native['tileset'],bid,q);assert raw==r['sourceHash']
                rows.append(r);native_shape.append(neutral)
                xx,yy=x0+x,y0+y;bid=definition['blocks'][yy//2*definition['width']+xx//2];q=yy%2*2+xx%2
                shape.append(source_shape(cache,game,data,definition['tileset'],bid,q)[0])
        result.append(dict(game='red',map=native_name,role='reviewed_'+role,x=rx,y=ry,w=w,h=h,rows=rows,shape=shape,
            door=door,purpose=destination,tileset=definition['tileset'],manualAlias=dict(game=game,map=name,origin=[x0,y0],
                size=[w,h],native_art_origin=[rx,ry],native_source_shape_sha256=hashlib.sha256(''.join(native_shape).encode()).hexdigest(),
                closed_source_doors=bool(options.get('close_source_door')),
                review='Complete roof, full exterior jambs, complete framed windows and facade were checked '
                    'in both original town contexts. GSC window/brick motifs differ; silhouettes and entry offset are explicit '
                    'whole-object aliases. Closed buildings contain no door. No source pixels are treated as collision IDs.')))
        if w!=rw:result[-1]['manualAlias']['repeated_complete_native_columns']=columns
    return result

def reviewed_native_facilities(cache,game,data,templates):
    """Explicit same-size counterpart aliases between fully reviewed GSC objects."""
    result=[]
    for name,rect,role,template_role,destination in(
        ('CELADON_CITY',(2,2,6,8),'celadon_department','goldenrod_native_department','mart'),
        ('FUCHSIA_CITY',(26,25,4,3),'wardens_home','architecture_home48','house'),
    ):
        x0,y0,w,h=rect;definition=data['maps'][name]
        doors=[z for z in definition.get('warps',[])if x0<=z['x']<x0+w and y0<=z['y']<y0+h]
        assert len(doors)==1 and purpose(doors[0]['destMap'])==destination
        door=[doors[0]['x']-x0,doors[0]['y']-y0]
        source=next(t for t in templates if t['game']==game and t['role']==template_role and
            [t['w'],t['h']]==[w,h]and t['door']==door)
        value=copy.deepcopy(source);value['role']='reviewed_'+role;value['shape']=[]
        for y in range(h):
            for x in range(w):
                xx,yy=x0+x,y0+y;bid=definition['blocks'][yy//2*definition['width']+xx//2];q=yy%2*2+xx%2
                value['shape'].append(source_shape(cache,game,data,definition['tileset'],bid,q)[0])
        value['manualAlias']=dict(game=game,map=name,origin=[x0,y0],size=[w,h],
            native_art_origin=[source['x'],source['y']],native_art_map=source['map'],
            review='The complete source building, all facade/roof bounds and original bottom entrance were reviewed in town '
                'context. This is the same-size whole native Gen3 counterpart of the same purpose, with all original pixels, '
                'window frames and entrance parts preserved at 1:1; only GSC exterior motifs differ.')
        result.append(value)
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--validate',action='store_true');p.add_argument('--activate',action='store_true');a=p.parse_args();assert not a.activate or a.validate
    OUT.mkdir(parents=True,exist_ok=True);cache=Path(os.environ['APPDATA'])/'pokemon-love2d';packed={}
    active=[r for f in sorted((ROOT/'mappings').glob('*.lua'))if f!=TARGET for r in preview.read_reviewed(f)]
    decorations=[r for n in CATALOGS for r in preview.read_reviewed(ROOT/'lib'/n)]
    output,roofs,proofs,held=[],[],[],[]
    red_data=e.source(cache,'red')
    red_templates=templates_for(cache,'red',red_data,active)
    for game in e.GAMES:
        data=e.source(cache,game);limit=catalog.read_lua(cache/game/'data/generated/landmarks.lua')['landmarks']['LANDMARK_PALLET_TOWN']['index']
        templates=templates_for(cache,game,data,active)+red_templates+reviewed_kanto_aliases(cache,game,data,red_data,active)
        templates+=reviewed_native_facilities(cache,game,data,templates)
        native_home=next((t for t in templates if t['role']=='architecture_home48'and t['w']==4 and t['h']==3),None)
        seen=set();occupied=set()
        for name,m in sorted(data['maps'].items()):
            if not isinstance(m,dict)or m.get('environment')not in('TOWN','ROUTE')or 0<m.get('landmark',999)<limit:continue
            current=[r for r in active if r['game']==game and r['tileset']==m['tileset']and r.get('map',name)==name]
            generic={(r['id'],r['quadrant'])for r in current if r.get('x')is None}
            positioned={(r['id'],r['quadrant'],r['x'],r['y'])for r in current if r.get('x')is not None}
            anchors=list(m.get('warps',[]))
            # A closed facade still requires an entire roof/wall/corner family.
            # Match its complete reviewed rectangle, with zero original warps.
            closed=[t for t in templates if t['purpose']=='__CLOSED__']
            for t in closed:
                for yy in range(m['height']*2-t['h']+1):
                    for xx in range(m['width']*2-t['w']+1):
                        bid=m['blocks'][yy//2*m['width']+xx//2];q=yy%2*2+xx%2
                        if source_shape(cache,game,data,m['tileset'],bid,q)[0]==t['shape'][0]:
                            anchors.append(dict(x=xx,y=yy+t['h']-1,destMap='__CLOSED__',closedTemplate=t['role']))
            for warp in anchors:
                matched=False
                for t in sorted(templates,key=lambda t:(bool(t.get('manualAlias')),t['game']!=game,
                    t['role']!='architecture_home32',t['map'],t['role'])):
                    if t['purpose']!=purpose(warp['destMap']):continue
                    if warp.get('closedTemplate')and warp['closedTemplate']!=t['role']:continue
                    ox,oy=warp['x']-t['door'][0],warp['y']-t['door'][1];key=game,name,ox,oy,t['w'],t['h']
                    if key in seen or ox<0 or oy<0 or ox+t['w']>m['width']*2 or oy+t['h']>m['height']*2:continue
                    footprint={(name,ox+x,oy+y)for y in range(t['h'])for x in range(t['w'])}
                    if footprint&occupied:continue
                    actual_doors=[z for z in m.get('warps',[])if ox<=z['x']<ox+t['w']and oy<=z['y']<oy+t['h']]
                    side_gate_doors=[z for z in m.get('warps',[])if z['x']in(ox-1,ox+t['w'])
                        and oy<=z['y']<oy+t['h']and purpose(z['destMap'])=='gate']
                    # A transit gate's paired source portals sit immediately
                    # outside its closed front. It is not a closed residence,
                    # even though there is no front warp inside this rectangle.
                    # The complete handed gate model is owned by landmarks.
                    if warp['destMap']=='__CLOSED__'and side_gate_doors:continue
                    if warp['destMap']=='__CLOSED__':
                        if actual_doors:continue
                    elif len(actual_doors)!=1 or actual_doors[0]!=warp:continue
                    cells=[];missing=0;valid=True
                    for y in range(t['h']):
                        for x in range(t['w']):
                            xx,yy=ox+x,oy+y;bid=m['blocks'][yy//2*m['width']+xx//2];q=yy%2*2+xx%2
                            c=e.cell_info(cache,game,data,m['tileset'],bid,q);cells.append(c)
                            if source_shape(cache,game,data,m['tileset'],bid,q)[0]!=t['shape'][y*t['w']+x]:valid=False;break
                            if(bid,q)not in generic and(bid,q,xx,yy)not in positioned:missing+=1
                        if not valid:break
                    if not valid:continue
                    matched=True
                    if missing==0:break
                    seen.add(key);expanded=t['role']=='architecture_home32'and t['w']==4 and t['h']==2 and native_home is not None
                    occupied.update(footprint)
                    for y in range(t['h']):
                        for x in range(t['w']):
                            xx,yy=ox+x,oy+y;c=cells[y*t['w']+x];source=native_home['rows'][(y+1)*4+x]if expanded else t['rows'][y*t['w']+x]
                            r=dict(game=game,style='gen3',map=name,tileset=m['tileset'],id=c['id'],quadrant=c['quadrant'],x=xx,y=yy,
                                sourceCells=[[xx,yy]],sourceHash=c['sourceHash'],sourceFiles=data['fingerprints'][m['tileset']],sourceCollision=c['collision'],
                                sourcePriority=[bool(z.get('priority'))for z in c['attributes']],sourcePalettes=[z.get('palette',1)for z in c['attributes']],
                                status='reviewed',role=t['role']if t['role']in('larger_center','larger_mart')else'kanto_native_'+t['role'],
                                evidence='The complete original building rectangle and entrance offset/purpose match a reviewed '
                                'whole-footprint reference. Explicit whole-object motif aliases are recorded separately. '
                                'Destination GSC attributes/collision are '
                                'checked independently; collision numbers and palettes are not treated as equivalent across generations. '
                                'Native artwork retains complete doors/windows at original '
                                'pixel size; source collision, entrance destination, layout and scripts remain unchanged.',
                                reviewedBuilding=dict(game=t['game'],map=t['map'],role=t['role'],origin=[t['x'],t['y']],
                                    size=[t['w'],t['h']],door=t['door'],whole_normalized_source_sha256=hashlib.sha256(''.join(t['shape']).encode()).hexdigest()))
                            if t.get('manualAlias'):r['reviewedBuilding']['manualAlias']=t['manualAlias']
                            r.update(art(source));r['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,r,packed,ROOT).tobytes());output.append(r)
                    if expanded:
                        for x in range(4):
                            if oy==0:continue
                            xx,yy=ox+x,oy-1;bid=m['blocks'][yy//2*m['width']+xx//2];q=yy%2*2+xx%2;c=e.cell_info(cache,game,data,m['tileset'],bid,q)
                            r=copy.deepcopy(output[-t['w']*t['h']+x]);r.update(id=bid,quadrant=q,x=xx,y=yy,buildingY=oy,
                                sourceCells=[[xx,yy]],sourceHash=c['sourceHash'],sourceCollision=c['collision'],
                                sourcePriority=[bool(z.get('priority'))for z in c['attributes']],sourcePalettes=[z.get('palette',1)for z in c['attributes']],role='kanto_native_house_roof')
                            r.update(art(native_home['rows'][x]));r.pop('base',None);r.pop('compositionPixelHash',None)
                            assert r.get('parts')and all(p.get('layers')==['over']for p in r['parts']),'Extra roof must preserve native exterior alpha'
                            roofs.append(r)
                    else:
                        for old in decorations:
                            if old['game']!=t['game']or old['map']!=t['map']:continue
                            if old.get('side'):
                                if (old.get('buildingX'),old.get('buildingY'),old.get('buildingW'),old.get('buildingH'))!=(t['x'],t['y'],t['w'],t['h']):continue
                            elif old.get('buildingY')!=t['y']or not t['x']<=old['x']<t['x']+t['w']:continue
                            assert safe_native_art(old),'Generated Gen1 decoration cannot be copied into GSC'
                            r=copy.deepcopy(old);dx,dy=ox-t['x'],oy-t['y'];r.update(game=game,map=name,tileset=m['tileset'],x=old['x']+dx,y=old['y']+dy)
                            if r['y']<0:continue
                            for field,offset in(('buildingX',dx),('buildingY',dy)):
                                if field in r:r[field]+=offset
                            sx=max(0,min(m['width']*2-1,r['x']));sy=r['y'];bid=m['blocks'][sy//2*m['width']+sx//2];q=sy%2*2+sx%2;c=e.cell_info(cache,game,data,m['tileset'],bid,q)
                            r.update(id=bid,quadrant=q,sourceHash=c['sourceHash'],sourceFiles=data['fingerprints'][m['tileset']],sourceCollision=c['collision'],sourceCells=[[sx,sy]],
                                sourcePriority=[bool(z.get('priority'))for z in c['attributes']],sourcePalettes=[z.get('palette',1)for z in c['attributes']])
                            if r.get('side'):r['sourceX']=sx
                            roofs.append(r)
                    proofs.append(dict(game=game,map=name,origin=[ox,oy],size=[t['w'],t['h']],door=[warp['x'],warp['y']],
                        destination=warp['destMap'],template_game=t['game'],template=t['map'],role=t['role'],new_source_cells=missing,
                        extra_native_upper_row=expanded,all_source_pixels_matched=not bool(t.get('manualAlias')),
                        whole_source_alias=t.get('manualAlias'),destination_attributes_independently_guarded=True))
                    break
                if not matched and not warp.get('closedTemplate'):held.append(dict(game=game,map=name,door=[warp['x'],warp['y']],destination=warp['destMap'],
                    reason='No reviewed complete building rectangle with an exact palette-neutral pixel match and matching entrance purpose/offset.'))
    (OUT/'instances.json').write_text(json.dumps(proofs,indent=2))
    (OUT/'held.json').write_text(json.dumps(held,indent=2))
    (OUT/'candidates.json').write_text(json.dumps(output,indent=2));(OUT/'roofs.json').write_text(json.dumps(roofs,indent=2))
    if a.validate:
        proof=e.validate_batch(output+roofs,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=OUT),ROOT)
        (OUT/'proof.json').write_text(json.dumps(proof,indent=2))
        if a.activate:write_rows(TARGET,stable(output));write_rows(ROOFS,stable(roofs))
    print(json.dumps(dict(buildings=len(proofs),core_rows=len(output),decorative_rows=len(roofs),new_source_cells=sum(p['new_source_cells']for p in proofs))))

if __name__=='__main__':main()
