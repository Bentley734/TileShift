"""Review regional Gen2 outdoor cells against explicit native Gen3 references.

Imported images and candidate tables remain private under .work. Initial
operation inventories source graphics and repeats only already reviewed roles,
requiring exact source pixels, behavior, palette slot, priority and tree geometry.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import sys

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE / '.tools/python'))
from PIL import Image, ImageDraw, ImageFont
import catalog
import preview
import gen2_outdoor_review

GAMES = ('gold', 'silver', 'crystal')
SETS = {'TILESET_JOHTO','TILESET_JOHTO_MODERN','TILESET_KANTO','TILESET_FOREST'}
REGIONS = {
    'early_johto': ('ROUTE_29','ROUTE_30','ROUTE_31','ROUTE_46','CHERRYGROVE_CITY','VIOLET_CITY','ROUTE_32',
                    'ROUTE_33','AZALEA_TOWN','ILEX_FOREST','ROUTE_34','ROUTE_35','ROUTE_36','ROUTE_37','ECRUTEAK_CITY'),
    'rest_johto': (),
    'kanto': (),
}
SCENES={'early_johto':('ROUTE_29','ROUTE_30','ROUTE_33','ILEX_FOREST'),
        'rest_johto':('GOLDENROD_CITY','OLIVINE_CITY','LAKE_OF_RAGE','ROUTE_45'),
        'kanto':('PALLET_TOWN','VIRIDIAN_CITY','ROUTE_2','FUCHSIA_CITY')}
REPEATABLE = {'short_nonencounter_grass','open_grassy_ground','decorative_flower_southeast',
              'decorative_flower_northwest','dense_conifer_crown','dense_conifer_trunk',
              'headbutt_small_tree','cuttable_small_tree','tall_grass','freestanding_sign','dense_round_tree','boundary_tree'}


def active_rows(mod):
    rows=[]
    for path in sorted((mod/'mappings').glob('*.lua')):
        rows.extend(preview.read_reviewed(path))
    return rows


def source(cache,game):
    root=cache/game
    return {'maps':catalog.read_lua(root/'data/generated/maps.lua'),
            'sets':catalog.read_lua(root/'data/generated/tilesets.lua'),
            'palettes':catalog.read_lua(root/'data/generated/palettes.lua'),
            'sheets':{},'cells':{},'fingerprints':{}}


def cell_info(cache,game,data,tileset,block_id,q):
    key=tileset,block_id,q
    if key in data['cells']:return data['cells'][key]
    ts=data['sets'][tileset]
    if tileset not in data['sheets']:
        data['sheets'][tileset]=Image.open(cache/game/ts['image']).convert('RGBA')
        data['fingerprints'][tileset]={
            'metadata':catalog.sha((cache/game/'data/generated/tilesets.lua').read_bytes()),
            'image':catalog.sha((cache/game/ts['image']).read_bytes()),
            'maps':catalog.sha((cache/game/'data/generated/maps.lua').read_bytes())}
    block=catalog.lua_array(catalog.dict_at(ts['blocks'],block_id+1));x,y=q%2*2,q//2*2
    ids=[block[i] for i in (y*4+x,y*4+x+1,(y+1)*4+x,(y+1)*4+x+1)]
    attrs=[catalog.gb_tile(data['sheets'][tileset],ts,tile)[1] for tile in ids]
    pixels=preview.native_cell(data['sheets'][tileset],ts,block,q)
    collision=catalog.lua_array(catalog.dict_at(ts['collision'],block_id+1))[q]
    row={'game':game,'tileset':tileset,'id':block_id,'quadrant':q,'tiles':ids,'attributes':attrs,
         'collision':collision,'sourceHash':catalog.sha(pixels.tobytes())}
    data['cells'][key]=row
    return row


def identity(cell):
    return (cell['sourceHash'],cell['collision'],tuple((bool(a.get('priority')),a.get('palette',1)) for a in cell['attributes']))


def source_image(cache,game,data,cell,definition):
    ts=data['sets'][cell['tileset']]
    palettes=preview.palette_set(data['palettes'],definition)
    return preview.native_cell(data['sheets'][cell['tileset']],ts,
        catalog.lua_array(catalog.dict_at(ts['blocks'],cell['id']+1)),cell['quadrant'],palettes)


def validate_batch(rows,args,mod):
    # A complete native family, not similar-looking isolated crops, defines
    # these reviewed roles. Reject the old lower-corner-as-straight-side error
    # before asking the runtime to decode any candidate or production batch.
    emerald_cave_roles={'cave_rock_mass_west_side':528,'cave_rock_mass_east_side':530,
        'cave_convex_northwest':520,'cave_convex_northeast':522,
        'cave_convex_southwest':536,'cave_convex_southeast':538}
    for row in rows:
        ref=row.get('donor',{})
        if ref.get('game')=='emerald' and ref.get('tileset')=='general__cave' and row['role'] in emerald_cave_roles:
            assert ref['id']==emerald_cave_roles[row['role']],('Native cave topology mismatch',row['role'],ref['id'])
    from lupa.luajit21 import LuaRuntime
    import zlib
    from validate_animation import IMAGE_FIXTURE
    runtime=LuaRuntime(unpack_returned_tuples=True,encoding=None)
    cache=args.cache.resolve()
    def read(relative):
        path=(cache/relative.decode()).resolve();assert path.is_relative_to(cache)
        if not path.is_file():return None
        raw=path.read_bytes()
        if path.suffix in ('.idx','.rgba'):
            try:return zlib.decompress(raw)
            except zlib.error:pass
        return raw
    original=Path.cwd()
    try:
        os.chdir(args.engine.resolve());runtime.execute(IMAGE_FIXTURE.encode())
        def load_image(relative,_raw):
            image=Image.open(cache/relative.decode()).convert('RGBA')
            return runtime.globals()[b'makeData'](image.width,image.height,b'rgba8',image.tobytes())
        ctx=runtime.table_from({b'read':read,b'prefix':lambda game:game+b'/',
            b'hash':lambda raw:hashlib.sha256(raw).hexdigest().encode(),
            b'newImageData':runtime.globals()[b'makeData'],b'loadImage':load_image})
        decoder=runtime.execute((mod/'lib/donor.lua').read_bytes())[b'new'](ctx)
        layer_hash_checks=[0]
        def hash_image(image):
            layer_hash_checks[0]+=1
            return hashlib.sha256(image[b'getString'](image)).hexdigest().encode()
        composer=runtime.execute((mod/'lib/composition.lua').read_bytes())[b'new'](runtime.table_from({
            b'donor':decoder,b'newImageData':runtime.globals()[b'makeData'],b'hashImage':hash_image}))
        runtime.globals()[b'extRows']=runtime.execute(write_compact(rows,None)[0].encode())
        runtime.globals()[b'extMapping']=runtime.execute((mod/'lib/mapping.lua').read_bytes())
        runtime.globals()[b'extSession']=runtime.execute((mod/'lib/session.lua').read_bytes())
        runtime.globals()[b'extDecoder']=decoder;runtime.globals()[b'extComposer']=composer
        runtime.globals()[b'extRead']=read
        runtime.globals()[b'extHash']=ctx[b'hash']
        def original_art(relative,expected):
            path=(mod/relative.decode()).resolve();assert path.is_relative_to(mod)
            raw=path.read_bytes()
            if expected:assert hashlib.sha256(raw).hexdigest().encode()==expected
            image=Image.open(path).convert('RGBA');assert image.size==(16,16)
            return runtime.globals()[b'makeData'](16,16,b'rgba8',image.tobytes())
        runtime.globals()[b'extOriginal']=original_art
        map_definitions={}
        def source_definition(game,map_id):
            if game not in map_definitions:
                map_definitions[game]=runtime.execute((cache/game.decode()/'data/generated/maps.lua').read_bytes())
            definition=map_definitions[game][map_id]
            assert definition is not None,'Missing source map definition'
            if definition[b'id'] is None:definition[b'id']=map_id
            return definition
        runtime.globals()[b'extDefinition']=source_definition
        accepted=runtime.execute(br'''
local indexed,errors=extMapping.index(extRows);assert(#errors==0,table.concat(errors,'\n'))
local foregrounds={}
local function foreground(ref)
  local key=ref.game..':'..ref.effect..':'..ref.hash
  if not foregrounds[key] then
    assert(ref.effect=='tall_grass')
    local raw=assert(extRead(ref.game..'/data/generated/gba/field_effects/tall_grass.rgba'))
    assert(#raw==16*80*4 and extHash(raw)==ref.hash,'Native grass foreground changed')
    local sheet=makeData(16,80,'rgba8',raw)
    local image=makeData(16,16);image:paste(sheet,0,8,0,72,16,8)
    foregrounds[key]=image
  end
  return foregrounds[key]
end
local state=extSession.new({mappings=indexed,donor=extDecoder,newImageData=makeData,
  generations=extMapping.generations,validate=extMapping.validate,foreground=foreground,original=extOriginal,
  compose=function(row)return extComposer:cell(row)end,
  composeFrames=function(row)return extComposer:frames(row)end,warn=function(message)error(message)end})
state:select('gen3')
local visited={}
for _,row in ipairs(extRows)do
  local key=row.game..':'..row.tileset..':'..row.map
  if not visited[key] then
    visited[key]=true;assert(state:replacements(row.game,row.tileset,extDefinition(row.game,row.map)))
  end
end
assert(state.rejected==0 and state.accepted==#extRows,'Extended terrain rows did not decode completely')
return state.accepted
''')
        for name in runtime.eval(b'package.loaded').keys():
            assert not name.startswith((b'src.core.game3.',b'src.world.gen2.')),name
        return {'rows_accepted':accepted,'rejected':0,'neutral_imports_only':True,
                'all_explicit_source_and_donor_hashes_checked':True,
                'foreground_sheets_hashed_and_native_foot_strip_selected':True,
                'selected_native_layer_hash_checks':layer_hash_checks[0]}
    finally:os.chdir(original)


def write_compact(rows,target):
    """Share immutable review/artwork records; preserve every expanded M.key."""
    artwork_keys={'donor','base','parts','kind','animated','animation','foreground','occludes',
                  'frames','asset','assetFileHash','assetPixelHash','credit','sourceUrl'}
    origins,artworks,groups=[],[],[]
    origin_index,artwork_index,group_index={},{},{}
    def intern(value,values,index):
        key=json.dumps(value,sort_keys=True,separators=(',',':'))
        if key not in index:index[key]=len(values)+1;values.append(value)
        return index[key]
    for row in rows:
        metadata={k:v for k,v in row.items() if k not in artwork_keys|{'id','quadrant','sourceCells','sourceFiles'}}
        art={k:v for k,v in row.items() if k in artwork_keys}
        metadata['files']=intern(row['sourceFiles'],origins,origin_index)
        metadata['art']=intern(art,artworks,artwork_index)
        key=json.dumps(metadata,sort_keys=True,separators=(',',':'))
        if key not in group_index:
            group_index[key]=len(groups);groups.append({**metadata,'cells':[]})
        groups[group_index[key]]['cells'].append([row['id'],row['quadrant'],row.get('sourceCells',[])])
    lua=gen2_outdoor_review.detail_review.lua
    body='-- Reviewed map-scoped Gen2 tile graphics; immutable shared proof/artwork.\n'
    body+='local files='+lua(origins)+'\nlocal art='+lua(artworks)+'\nlocal groups={}\n'
    body+='local function append(batch)for _,group in ipairs(batch)do groups[#groups+1]=group end end\n'
    # LuaJIT has a per-function constant limit. Separate bounded data chunks
    # keep large coordinate/provenance sets compilable without flattening away
    # their source geometry or changing the expanded rows.
    for start in range(0,len(groups),32):
        body+='append((function()return {\n'+'\n'.join('  '+lua(group)+',' for group in groups[start:start+32])+'\n}end)())\n'
    body+='''local rows={}
for _,group in ipairs(groups)do
  for _,cell in ipairs(group.cells)do
    local row={id=cell[1],quadrant=cell[2],sourceCells=cell[3],sourceFiles=files[group.files]}
    for key,value in pairs(group)do
      if key~='files' and key~='art' and key~='cells' then row[key]=value end
    end
    for key,value in pairs(art[group.art])do row[key]=value end
    rows[#rows+1]=row
  end
end
return rows
'''
    expanded=catalog.plain(catalog.LUA.execute(body))
    key=lambda row:(row['game'],row['style'],row['tileset'],row['id'],row['quadrant'],row.get('map'),row.get('x'),row.get('y'))
    assert {key(r):r for r in expanded}=={key(r):r for r in rows},'Compact expansion changed mapping semantics'
    assert len({key(r) for r in expanded})==len(rows),'Duplicate compact mapping key'
    stats={'expanded_rows':len(rows),'proof_groups':len(groups),'artwork_records':len(artworks),
            'source_file_records':len(origins),'bytes':len(body.encode())}
    if target is None:return body,stats
    target.write_text(body,encoding='utf-8')
    stats['bytes']=target.stat().st_size
    return stats


def merge_reviewed(rows,target):
    """Append explicitly approved rows without losing existing review batches."""
    existing=preview.read_reviewed(target) if target.is_file() else []
    key=lambda row:(row['game'],row['style'],row['tileset'],row['id'],row['quadrant'],row.get('map'),row.get('x'),row.get('y'))
    indexed={key(row):row for row in existing};assert len(indexed)==len(existing)
    added=0
    for row in rows:
        assert row['status']=='reviewed','Pending proposals cannot enter production mappings'
        identity=key(row)
        if identity in indexed:
            assert indexed[identity]==row,'Conflicting replacement for an existing reviewed key'
        else:indexed[identity]=row;added+=1
    stats=write_compact(list(indexed.values()),target)
    stats.update(previous_rows=len(existing),added_rows=added)
    return stats


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=Path(os.environ['APPDATA'])/'pokemon-love2d')
    parser.add_argument('--output',type=Path,default=WORKSPACE/'.work/tileshift-gen2-extended-review')
    parser.add_argument('--region',choices=REGIONS,default='early_johto')
    parser.add_argument('--engine',type=Path,default=WORKSPACE/'.tools/engine-0395')
    parser.add_argument('--validate',action='store_true',help='Validate live native imports and every map-scoped Session replacement')
    parser.add_argument('--write-reviewed',action='store_true')
    parser.add_argument('--new-tree-variants',action='store_true',help='Include separately reviewed modern conifers and complete32px forest-tree sources')
    parser.add_argument('--new-kanto-variants',action='store_true',help='Review new Kanto lawn, flowers, grass and complete leafy-tree glyphs')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    mod=WORKSPACE/'TileShift';old=active_rows(mod);staged=[];reports=[];samples={}
    for game in GAMES:
        data=source(args.cache,game)
        known={}
        for row in old:
            if row['game']==game and row['style']=='gen3' and row['tileset'] in SETS and row['role'] in REPEATABLE:
                cell=cell_info(args.cache,game,data,row['tileset'],row['id'],row['quadrant'])
                assert cell['sourceHash']==row['sourceHash']
                known[identity(cell)]=row
        geometry={}
        if args.new_tree_variants:
            donor_catalogs={g:json.loads((WORKSPACE/'.work/tileshift-catalog'/f'{g}.json').read_text()) for g in ('emerald','firered')}
            variants=[('TILESET_JOHTO_MODERN',5,0,'dense_conifer_crown','emerald','general__petalburg',14),
                      ('TILESET_JOHTO_MODERN',5,2,'dense_conifer_trunk','emerald','general__petalburg',22)]
            for q,mid in enumerate((28,29,36,37)):
                variants.append(('TILESET_FOREST',5,q,'dense_forest_tree_'+('northwest','northeast','southwest','southeast')[q],
                                 'firered','pallet_outdoor',mid))
            forest_shapes={}
            for ts_name,bid,q,role,donor_game,pair,mid in variants:
                cell=cell_info(args.cache,game,data,ts_name,bid,q)
                assert cell['collision']==7 and not any(a.get('priority') for a in cell['attributes'])
                record=next(r for r in donor_catalogs[donor_game]['cells'] if r['pair']==pair and r['mid']==mid)
                template={'game':game,'style':'gen3','tileset':ts_name,'id':bid,'quadrant':q,'role':role,'status':'reviewed',
                          'sourceHash':cell['sourceHash'],'sourceFiles':data['fingerprints'][ts_name],
                          'donor':{'game':donor_game,'tileset':pair,'id':mid,'hash':record['pixel_sha256']},
                          'evidence':'Complete native Gen3 tree, separately compared with the exact complete source footprint.'}
                if ts_name=='TILESET_FOREST':
                    asset=mod/'assets/original/flora'/f'johto-oak32-q{q}.png'
                    base=next(r for r in donor_catalogs['emerald']['cells'] if r['pair']=='general__petalburg' and r['mid']==1)
                    template.pop('donor')
                    template.update(kind='original',asset=asset.relative_to(mod).as_posix(),
                        assetFileHash=hashlib.sha256(asset.read_bytes()).hexdigest(),
                        base={'game':'emerald','tileset':'general__petalburg','id':1,'hash':base['pixel_sha256']},
                        evidence='Complete original32px Johto Oak, all four16px cells retained over the reviewed Emerald forest lawn.')
                known[identity(cell)]=template
                if ts_name=='TILESET_FOREST':forest_shapes[q]=identity(cell)
            for q,shape in forest_shapes.items():geometry[shape]=(q,forest_shapes)
        if args.new_kanto_variants:
            native={r['mid']:r for r in json.loads((WORKSPACE/'.work/tileshift-catalog/emerald.json').read_text())['cells']
                    if r['pair']=='general__petalburg'}
            base=next(r for r in old if r['game']==game and r['role']=='short_nonencounter_grass')
            flower=next(r for r in old if r['game']==game and r['role']=='decorative_flower_southeast')
            grass=next(r for r in old if r['game']==game and r['role']=='tall_grass')
            tree=next(r for r in old if r['game']=='red' and r['role']=='dense_round_tree')
            boundary=next(r for r in old if r['game']=='red' and r['role']=='boundary_tree')
            for bid,q,role,template,collision in ((10,0,'short_nonencounter_grass',base,0),
                    (116,0,'decorative_flower_southeast',flower,0),(116,2,'decorative_flower_northwest',flower,0),
                    (11,0,'tall_grass',grass,0x18),(15,0,'dense_round_tree',tree,7),
                    (24,0,'boundary_tree',boundary,7)):
                cell=cell_info(args.cache,game,data,'TILESET_KANTO',bid,q)
                assert cell['collision']==collision and not any(a.get('priority') for a in cell['attributes'])
                copyrow=copy.deepcopy(template)
                copyrow.update(game=game,tileset='TILESET_KANTO',id=bid,quadrant=q,role=role,sourceHash=cell['sourceHash'],
                               sourceFiles=data['fingerprints']['TILESET_KANTO'])
                copyrow.pop('map',None);known[identity(cell)]=copyrow
        # A large-tree quadrant is never repeated without the other three,
        # even when its reviewed template was loaded from a previous batch.
        forest_shapes={q:identity(cell_info(args.cache,game,data,'TILESET_FOREST',5,q)) for q in range(4)}
        for q,shape in forest_shapes.items():geometry[shape]=(q,forest_shapes)
        names=REGIONS[args.region]
        if args.region=='rest_johto':
            names=tuple(name for name,m in sorted(data['maps'].items()) if isinstance(m,dict) and
                        m.get('tileset') in {'TILESET_JOHTO','TILESET_JOHTO_MODERN'} and
                        name not in REGIONS['early_johto'] and name!='NEW_BARK_TOWN')
        elif args.region=='kanto':
            names=tuple(name for name,m in sorted(data['maps'].items()) if isinstance(m,dict) and m.get('tileset')=='TILESET_KANTO')
        for name in names:
            definition=data['maps'].get(name)
            if not definition or definition['tileset'] not in SETS:continue
            if definition.get('environment')=='CAVE' and name!='ILEX_FOREST':continue
            tileset=definition['tileset'];selected={}
            for row in sorted(old,key=lambda r:bool(r.get('map'))):
                if row['game']==game and row['style']=='gen3' and row['tileset']==tileset and row.get('map',name)==name:
                    selected[row['id'],row['quadrant']]=row
            occurrences=defaultdict(list);grid={}
            for pos,bid in enumerate(catalog.lua_array(definition['blocks'])):
                for q in range(4):
                    x,y=pos%definition['width']*2+q%2,pos//definition['width']*2+q//2
                    cell=cell_info(args.cache,game,data,tileset,bid,q)
                    occurrences[bid,q].append([x,y]);grid[x,y]=cell
            made=[];remaining=[]
            for (bid,q),coords in sorted(occurrences.items()):
                cell=cell_info(args.cache,game,data,tileset,bid,q)
                if (bid,q) in selected:continue
                template=known.get(identity(cell))
                if template and template['role'] in ('dense_conifer_crown','dense_conifer_trunk'):
                    neighbor_role='dense_conifer_trunk' if template['role']=='dense_conifer_crown' else 'dense_conifer_crown'
                    dy=1 if template['role']=='dense_conifer_crown' else -1
                    if any(known.get(identity(grid.get((x,y+dy),cell)),{}).get('role')!=neighbor_role for x,y in coords):
                        template=None
                if template and identity(cell) in geometry:
                    quarter,shapes=geometry[identity(cell)]
                    if any(any((x-quarter%2+q2%2,y-quarter//2+q2//2) not in grid or
                                   identity(grid[x-quarter%2+q2%2,y-quarter//2+q2//2])!=shape
                                   for q2,shape in shapes.items()) for x,y in coords):template=None
                if template:
                    row=copy.deepcopy(template)
                    row.update(game=game,map=name,tileset=tileset,id=bid,quadrant=q,
                               sourceHash=cell['sourceHash'],sourceFiles=data['fingerprints'][tileset],sourceCollision=cell['collision'])
                    row.pop('sourceMaps',None)
                    row['reviewedSeed']={'game':template['game'],'tileset':template['tileset'],'id':template['id'],
                                         'quadrant':template['quadrant']}
                    if template.get('map'):row['reviewedSeed']['map']=template['map']
                    row['sourceCells']=coords
                    row['sourcePriority']=[bool(a.get('priority')) for a in cell['attributes']]
                    row['sourcePalettes']=[a.get('palette',1) for a in cell['attributes']]
                    row['evidence']=f"Region {args.region}: explicit {name} positions recorded in sourceCells. Rechecked identical native pixels, collision0x{cell['collision']:02x}, palette slots and per8px priority against the independently reviewed {template['role']} source. The exact native counterpart and frame/mask references are retained. "
                    if template['role'] in ('dense_conifer_crown','dense_conifer_trunk'):
                        row['evidence']+='Every occurrence has its matching crown/trunk neighbor, preserving the complete16x32 source tree footprint. '
                    if template['role'].startswith('dense_forest_tree_'):
                        row['evidence']+='Every occurrence belongs to the complete matching2x2 source tree. Complete original32px Johto Oak retains canopy corners, trunk and roots; all four16px quadrants stay joined without fractional scaling. '
                    if template['role']=='headbutt_small_tree':
                        row['evidence']+='User chose native Emerald82 art for these complete16px Headbutt trees; source Headbutt encounters, blocking and whole-frame shake stay native. '
                    if template['role']=='boundary_tree':
                        row['evidence']+='The GSC Kanto round town/road boundary family is context-matched to the previously reviewed Gen1 Pallet border and actual FRLG perimeter trees. The standing user choice is the complete16px B4 tree; distinct cliff/boulder glyphs are excluded. '
                    row['evidence']+='Map geometry, collision, interactions, events and progression are never modified.'
                    made.append(row);staged.append(row)
                else:
                    remaining.append({**cell,'map':name,'coordinates':coords,'count':len(coords)})
                    if game=='crystal':samples.setdefault(identity(cell),(cell,name,source_image(args.cache,game,data,cell,definition)))
            covered=sum(len(coords) for key,coords in occurrences.items() if key in selected)
            added=sum(len(occurrences[r['id'],r['quadrant']]) for r in made)
            reports.append({'game':game,'map':name,'tileset':tileset,'total':len(grid),'existing':covered,'candidate_additions':added,
                            'candidate_rows':len(made),'remaining':remaining})
    # Independent labeled source/native contacts; source adjacency checks above
    # ensure that a copied tree half cannot silently create a clipped canopy.
    representatives={}
    for row in staged:representatives.setdefault(row['role'],row)
    width=1280;canvas=Image.new('RGB',(width,70+len(representatives)*165),'#18202c');draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17);packed={}
    draw.text((15,12),f"Gen2 {args.region}: context-checked repeats of reviewed outdoor counterparts",font=font,fill='white')
    draw.text((15,40),'Exact source shape + collision + palette slot + priority; full tree neighbors checked. Water and architecture not inferred.',fill='#ccd7e5')
    for index,(role,row) in enumerate(sorted(representatives.items())):
        y=75+index*165;data=source(args.cache,row['game']);cell=cell_info(args.cache,row['game'],data,row['tileset'],row['id'],row['quadrant'])
        image=source_image(args.cache,row['game'],data,cell,data['maps'][row['map']]);canvas.paste(image.resize((96,96),Image.Resampling.NEAREST),(20,y))
        draw.text((135,y),role.replace('_',' '),font=font,fill='white')
        draw.text((135,y+25),f"{row['game']} {row['map']} / {row['id']}:{row['quadrant']}",fill='#ccd7e5')
        draw.text((135,y+46),f"tiles{cell['tiles']} / collision0x{cell['collision']:02x}",fill='#ccd7e5')
        if row.get('animated'):frames=preview.native_water_frames(args.cache,row,packed)
        else:frames=[preview.replacement_image(args.cache,row,packed,mod)]
        for frame,image in enumerate(frames):
            canvas.paste(image.resize((88,88),Image.Resampling.NEAREST),(510+frame*105,y))
            draw.text((510+frame*105,y+93),f'frame {frame}',fill='#ccd7e5')
    canvas.save(args.output/f'{args.region}-reviewed-role-repeats.png')
    columns,cw,ch=9,135,136
    contact=Image.new('RGB',(columns*cw,55+math.ceil(len(samples)/columns)*ch),'#18202c');draw=ImageDraw.Draw(contact)
    draw.text((12,12),f'Crystal {args.region}: distinct remaining source shapes after safe repeats; context labels below',fill='white')
    for index,(cell,name,image) in enumerate(samples.values()):
        x,y=index%columns*cw+8,index//columns*ch+50
        contact.paste(image.resize((64,64),Image.Resampling.NEAREST),(x,y))
        draw.text((x+69,y),f"{cell['id']}:{cell['quadrant']}",fill='white')
        draw.text((x+69,y+18),f"col{cell['collision']:02x}",fill='white')
        draw.text((x,y+69),' '.join(map(str,cell['tiles'])),fill='#ccd7e5')
        draw.text((x,y+86),name[:21],fill='#ccd7e5')
        draw.text((x,y+102),cell['tileset'].removeprefix('TILESET_'),fill='#e5ce9a')
    contact.save(args.output/f'{args.region}-remaining-source-shapes.png')
    (args.output/f'{args.region}-inventory.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
    (args.output/f'{args.region}-candidates.json').write_text(json.dumps(staged,indent=2),encoding='utf-8')
    if args.validate or args.write_reviewed:
        validation=validate_batch(staged,args,mod)
        (args.output/f'{args.region}-validation.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
        print(json.dumps(validation))
        packed={}
        scenes=[]
        for name in SCENES[args.region]:
            if any(r['map']==name for r in staged):
                scenes.append(preview.map_preview(args.cache,args.output,'crystal',name,f'crystal-{name}',old+staged,packed,1,mod))
        (args.output/f'{args.region}-map-previews.json').write_text(json.dumps(scenes,indent=2),encoding='utf-8')
    if args.write_reviewed:
        target=mod/'mappings/gen2_outdoor_extended.lua'
        previous=preview.read_reviewed(target) if target.is_file() else []
        keys={(r['game'],r['tileset'],r['id'],r['quadrant'],r.get('map'),r.get('x'),r.get('y')) for r in staged}
        retained=[r for r in previous if (r['game'],r['tileset'],r['id'],r['quadrant'],r.get('map'),r.get('x'),r.get('y')) not in keys]
        production=retained+staged
        compact=write_compact(production,target)
        print('Compact data:',compact)
    print('Candidate rows',len(staged),'roles',dict(Counter(r['role'] for r in staged)))
    for r in reports:
        if r['game']=='crystal':print(r['map'],r['existing'],'+',r['candidate_additions'],'/',r['total'])
    print('Distinct remaining shapes',len(samples),'Production written' if args.write_reviewed else 'Private candidates only')


if __name__=='__main__':main()
