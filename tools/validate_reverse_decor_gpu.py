"""Exercise real RSE decoration placement and procedural FieldView rendering.

Only private cloned layouts receive furniture. Imported layouts, definitions,
saves, launcher state and mod files remain unchanged. The optional pilot uses
the original SMALL DESK/SMALL CHAIR. Full runs also cover16 actual TrainerHill
mode/floor layouts; --pyramid adds deterministic native Pyramid witnesses.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import zlib

import catalog
import validate_gpu

GAMES = ('ruby', 'sapphire', 'emerald')
BANKS = ('red_cave', 'blue_cave', 'brown_cave', 'yellow_cave', 'shrub', 'tree')
SHAPES = ((1, 1), (2, 1), (3, 1), (4, 2), (2, 2), (1, 2), (1, 3), (2, 4), (3, 3), (3, 2))


def selection(cache: Path, games: list[str], banks: list[str], pilot: bool, procedural: bool = True,
              pyramid: bool = False) -> dict:
    fixtures = []
    source_files = {}
    for game in games:
        root = cache / game / 'data/generated'
        manifest_path = root / 'gba/secret_base/manifest.lua'
        definitions_path = root / 'gba/decorations/decorations.lua'
        native_path = root / 'gba/native/manifest.lua'
        manifest = catalog.read_lua(manifest_path)
        definitions = catalog.read_lua(definitions_path)['decorations']
        layouts = catalog.read_lua(native_path)['layouts']
        for path in (manifest_path, definitions_path, native_path, root / 'gba/objects/pack.lua'):
            source_files[path.relative_to(cache).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        designs = []
        for index in range(1, 121):
            definition = catalog.dict_at(definitions, index)
            if not definition or definition.get('category') not in (0, 1):
                continue
            if pilot and index not in (1, 10):
                continue
            tiles = catalog.lua_array(catalog.dict_at(manifest['decorTiles'], index))
            shape = list(SHAPES[definition['shape']])
            assert len(tiles) == shape[0] * shape[1]
            assert definition['permission'] in (0, 1), 'Desk/chair unexpectedly uses a wall/sprite permission'
            designs.append(dict(id=index, name=definition['name'], permission=definition['permission'],
                                shape=shape, metatiles=[tile + 512 for tile in tiles]))
        assert len(designs) == (2 if pilot else 18), 'Actual imported desk/chair inventory differs'
        rooms = []
        for bank in banks:
            pair = 'secret_base__secret_base_' + bank
            options = []
            for name, spec in layouts.items():
                if spec['pair'] != pair:
                    continue
                path = root / 'gba/native' / spec['file']
                data = path.read_bytes()
                blob = data if data[:4] == b'SVML' else zlib.decompress(data)
                width, height, true_width, true_height = struct.unpack_from('<HHHH', blob, 6)
                columns, rows = true_width or width, true_height or height
                offset = 16 + blob[14] * blob[15] * 2
                floor = sum(struct.unpack_from('<H', blob, offset + (y * width + x) * 4)[0] == 522
                            for y in range(rows) for x in range(columns))
                options.append((floor, columns * rows, name, path))
            assert options, f'No actual native map for {game}/{pair}'
            _, _, name, path = max(options)
            source_files[path.relative_to(cache).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
            bank_root = root / 'gba/native' / pair
            for path in bank_root.iterdir():
                if path.is_file():
                    source_files[path.relative_to(cache).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
            rooms.append(dict(map=name, pair=pair, bank=bank))
        hill = game == 'emerald' and procedural and not pilot
        if hill:
            path = root / 'gba/rse/trainer_hill/manifest.lua'
            source_files[path.relative_to(cache).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
            for floor in range(1, 5):
                spec = layouts[f'EM_TRAINER_HILL_{floor}F']
                path = root / 'gba/native' / spec['file']
                source_files[path.relative_to(cache).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
                for path in (root / 'gba/native' / spec['pair']).iterdir():
                    if path.is_file():
                        source_files[path.relative_to(cache).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        pyramid_enabled = pyramid and game == 'emerald' and not pilot
        if pyramid_enabled:
            path = root / 'gba/rse/pyramid/manifest.lua'
            source_files[path.relative_to(cache).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
            for name, spec in layouts.items():
                if name == 'EM_BATTLE_FRONTIER_BATTLE_PYRAMID_FLOOR' or name.startswith('EM_BATTLE_PYRAMID_SQUARE'):
                    path = root / 'gba/native' / spec['file']
                    source_files[path.relative_to(cache).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in (root / 'gba/native' / spec['pair']).iterdir():
                        if path.is_file():
                            source_files[path.relative_to(cache).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        fixtures.append(dict(game=game, designs=designs, rooms=rooms, procedural_hill=hill, procedural_pyramid=pyramid_enabled))
    return dict(fixtures=fixtures, pilot=pilot, expected_cases=sum(len(f['designs']) * len(f['rooms']) for f in fixtures),
                expected_procedural_cases=(16 if any(f['procedural_hill'] for f in fixtures) else 0)
                + (4 if any(f['procedural_pyramid'] for f in fixtures) else 0),
                source_file_sha256=source_files)


BODY = r"""
 local Native=require('src.core.game3.tileset_native')
 local Anim=require('src.core.game3.tileset_anim')
 local Versions=require('src.import.gba.versions')
 local CachePaths=require('src.core.game3.cache_paths')
 local Dataset=require('src.core.game3.dataset')
 local Map=require('src.core.game3.map')
 local View=require('src.core.game3.field_view')
 local Collision=require('src.core.game3.collision')
 local Field=require('src.core.game3.field')
 local Decor=require('src.core.game3.rse.decoration')
 local DecorInv=require('src.core.game3.rse.decoration_inventory')
 local SB=require('src.core.game3.rse.secret_base')
 local MB=require('src.core.game3.mb')
 local Interactions=require('src.core.game3.scripting.interaction_scripts')
 local selected=Json.decode(@SELECTION@)
 report.procedural_fixtures={}
 local extraProceduralCases=0
 report.theme=selected.expected_cases>0 and'reverse_gen2_runtime_decorations'or'reverse_gen2_runtime_procedural';report.selection=selected
 report.limits='Private cloned native RSE fixtures. Decoration cases use real Decor.showOnMap/SB.fieldGrid/Field.setMetatile/LayoutNative/FieldView and synthetic normal-actor markers. Procedural cases use actual native composeLayout selectors and FieldView; no facility playthrough, lighting session or NPC generation. No placement menu, saves or imported layout edits.'
 local function clone(value,seen)
  if type(value)~='table'then return value end
  seen=seen or{};if seen[value]then return seen[value]end
  local out={};seen[value]=out
  for k,v in pairs(value)do out[k]=clone(v,seen)end
  return setmetatable(out,getmetatable(value))
 end
 local function content(def)
  return hash(tableString(def.midLayout.cells)..tableString(def.midLayout.overrides)..tableString(def.warps)..tableString(def.objects)..tableString(def.coordEvents))
 end
 local magenta=nativeData(1,1);magenta:setPixel(0,0,1,0,1,1)
 for _,fixture in ipairs(selected.fixtures)do
  local game=fixture.game;GV.set(game);assetGame=game;clock=0
  local cache={read=function(_,path)return cacheRead(game..'/'..path)end,exists=function(self,path)return self:read(path)~=nil end}
  Versions.selectCache(game,cache);CachePaths.reset();Dataset.cacheRootOverride=nil;Dataset.mountExtractRoots();Native.install(cache)
  Interactions.install(generated(game,'gba/objects/pack'))
  Decor.reset();Decor.install(generated(game,'gba/secret_base/manifest'),generated(game,'gba/decorations/decorations'))
  local definitionHash=hash(tableString(Decor.manifest())..tableString(DecorInv.data()))
  local originals=Dataset.buildMaps();local maps={};for key,value in pairs(originals)do maps[key]=value end
  local rooms={}
  for _,entry in ipairs(fixture.rooms)do
   local source=assert(originals[entry.map]);Dataset.attachMidLayouts({[entry.map]=source},cache)
   local sourceHash=content(source);local def=clone(source);maps[entry.map]=def
   check(def.midLayout~=source.midLayout and def.midLayout.cells~=source.midLayout.cells,'Fixture must own a private layout and cells')
   local layout=def.midLayout;local columns,rows=layout.trueWidth or layout.width,layout.trueHeight or layout.height
   check((def.pair or layout.pair)==entry.pair,'Decoration bank does not match the actual source map')
   assert(Native.get(entry.pair));rooms[#rooms+1]={entry=entry,source=source,sourceHash=sourceHash,def=def,layout=layout,columns=columns,rows=rows,cases={}}
  end
  local mod=startMod(game,3);mod.save.set=function()end -- Private in-memory option sink; no persistence implementation.
  local host={data={maps=maps},save={flags={},vars={},options={}},options={},world={map={},player={facing='down'}}}
  mod.game=host
  local savedField={game=Field._game,session=Field._session,overrides=Field.metatileOverrides,layouts=Field._overrideLayouts}
  local function bind(room)
   local id=room.entry.map;local width,height=room.columns*16,room.rows*16
   maps[id]=room.def -- Every procedural mode owns a separate private definition.
   host.save.position={map=id};host.world.map={id=id};host.world.player.px=width/2-8;host.world.player.py=height/2-8
   Field._game=host;Field._session={map=id,version=game};Field.metatileOverrides={};Field._overrideLayouts={}
   Map._def=room.def;Map._currentDef=room.def;Map.current=id;Map.neighborList={};Map.neighbors={}
   Anim.setVisiblePairs({[room.entry.pair]=true});Anim.enterMap(room.entry.pair,false)
   Collision.bindMap(host,id,room.def);View.invalidate();View._flashMapId=id;View.setFlashLevel(0)
  end
  local function reset(room)
   room.layout:clearOverrides();bind(room)
  end
  local function draw(room,opts)
   return capture(room.columns*16,room.rows*16,function()View.draw(host,room.columns*16,room.rows*16,opts or{skipActors=true})end)
  end
  local function warmDraw(room)
   -- Exercise exactly the native draw path without an unnecessary GPU
   -- readback: warm checks measure reads/rebuilds, not new pixel results.
   if not room.warmCanvas then room.warmCanvas=G.newCanvas(room.columns*16,room.rows*16,{dpiscale=1,format='rgba8'})end
   G.push('all');G.setCanvas(room.warmCanvas);G.origin();G.setScissor();G.setShader();G.clear(0,0,0,0);G.setColor(1,1,1,1)
   View.draw(host,room.columns*16,room.rows*16,{skipActors=true});G.pop()
  end
  local function outsideHash(image,p)
   local raw=image:getString();local stride=image:getWidth()*4;local out={}
   local top,bottom=p.y-p.h+1,p.y
   for y=0,image:getHeight()-1 do
    local first=y*stride+1
    if y<top*16 or y>=(bottom+1)*16 then out[#out+1]=raw:sub(first,first+stride-1)
    else
     out[#out+1]=raw:sub(first,first+p.x*64-1)
     out[#out+1]=raw:sub(first+(p.x+p.w)*64,first+stride-1)
    end
   end
   return hash(table.concat(out))
  end
  local function actorMarker(room,p)
   local calls=0
   local image=draw(room,{skipActors=false,endUnderActors=function()
    calls=calls+1;G.setColor(1,0,1,1)
    G.rectangle('fill',p.x*16,(p.y-p.h+1)*16,p.w*16,p.h*16)
    G.setColor(1,1,1,1)
   end})
   check(calls==1,'Placed furniture actor marker missed native normal-actor draw boundary')
   return image
  end
  local function findFloor(room,w,h)
   for y=1,room.rows-h-1 do for x=1,room.columns-w-1 do
    local ok=true
    for yy=y,y+h-1 do for xx=x,x+w-1 do
     if Collision.behavior(xx,yy)~=MB.id('NORMAL')or room.layout:collAt(xx,yy)~=0 then ok=false end
    end end
    if ok then return x,y+h-1 end
   end end
   error('No actual native normal-floor rectangle for '..game..'/'..room.entry.map..' '..w..'x'..h)
  end
  local function place(room,design,position)
   local info=assert(Decor.info(design.id));local w,h=Decor.dims(design.id)
   check(info.name==design.name and info.permission==design.permission,'Actual per-game native decoration definition differs')
   check(w==design.shape[1]and h==design.shape[2]and #info.tiles==w*h,'Actual native decoration shape differs')
   check(info.category==Decor.CAT.DESK or info.category==Decor.CAT.CHAIR,'Probe must place the actual desk/chair categories')
   local x,y
   if position then x,y=position.x,position.y else x,y=findFloor(room,w,h)end
   local grid=SB.fieldGrid()
   check(Decor.showOnMap(grid,x,y,design.id)==true,'Actual native Decor.showOnMap rejected fixture')
   local cells={}
   for j=0,h-1 do for i=0,w-1 do
    local at=j*w+i+1;local cx,cy=x+i,y-h+1+j;local expected=design.metatiles[at]
    check(info.tiles[at]+512==expected,'Actual imported decoration tile slot+512 differs from selected source contract')
    check(room.layout:midAt(cx,cy)==expected,'Actual native placement wrote the wrong source MID or wall variant')
    cells[#cells+1]={x=cx,y=cy,mid=expected,coll=room.layout:collAt(cx,cy),elev=room.layout:elevAt(cx,cy)}
   end end
   return{x=x,y=y,w=w,h=h,cells=cells}
  end
  local proceduralRooms={};local hillManifestHash;local pyramidManifestHash;local pyramidSources={};local savedRuntimeGame
  if fixture.procedural_hill then
   local Hill=require('src.core.game3.rse.trainer_hill')
   hillManifestHash=hash(tableString(Hill.manifest()))
   for mode=0,3 do for floor=1,4 do
    local id='EM_TRAINER_HILL_'..floor..'F';local source=assert(originals[id]);Dataset.attachMidLayouts({[id]=source},cache)
    local sourceHash=content(source);local def=clone(source)
    local session={map=id,version=game,trainerHill={mode=mode}}
    local metadata=assert(Hill.floor(session));local expected=clone(metadata.map.metatiles)
    def.midLayout=Hill.composeLayout(session,def)
    local layout=def.midLayout;local pair=assert(def.pair or layout.pair)
    check(pair=='building__trainer_hill','Procedural TrainerHill uses the wrong native atlas pair')
    check(layout.trueWidth==16 and layout.trueHeight==21,'Actual TrainerHill logical dimensions changed')
    for y=0,15 do for x=0,15 do
     check(layout:midAt(x,y+5)==expected[y*16+x+1]+512,'Actual Hill.composeLayout wrote the wrong imported mode/floor metatile')
    end end
    check(content(source)==sourceHash,'Actual Hill.composeLayout mutated original floor/header events')
    assert(Native.get(pair))
    proceduralRooms[#proceduralRooms+1]={entry={map=id,pair=pair},source=source,sourceHash=sourceHash,def=def,
     layout=layout,columns=16,rows=21,mode=mode,floor=floor,kind='trainer_hill',stem='trainer-hill-mode'..mode..'-floor'..floor,
     metadata_sha256=hash(tableString(metadata)),geometry_sha256=hash(tableString(layout.cells)..tableString(layout.overrides))}
   end end
  end
  if fixture.procedural_pyramid then
   local Pyramid=require('src.core.game3.rse.frontier.pyramid')
   local GameRuntime=require('src.core.game3.runtime');savedRuntimeGame={value=GameRuntime._game};GameRuntime._game=host
   pyramidManifestHash=hash(tableString(Pyramid.manifest()))
   local squareMids={};local sampled={}
   for id,def in pairs(originals)do if id:match('^EM_BATTLE_PYRAMID_SQUARE%d%d$')then
    Dataset.attachMidLayouts({[id]=def},cache);pyramidSources[#pyramidSources+1]={def=def,hash=content(def)}
    local offset=tonumber(id:match('(%d%d)$'))-1;squareMids[offset]={}
    for _,cell in ipairs(def.midLayout.cells)do squareMids[offset][cell.mid]=true end
   end end
   local source=assert(originals[Pyramid.FLOOR_MAP]);Dataset.attachMidLayouts({[Pyramid.FLOOR_MAP]=source},cache)
   local sourceHash=content(source)
   local function appendPyramid(seed,floor,randoms)
    local def=clone(source)
    local session={map=Pyramid.FLOOR_MAP,version=game,frontier={pyramidRandoms=randoms,curChallengeBattleNum=floor}}
    local offsets=Pyramid.layoutOffsets(session)
    def.midLayout=Pyramid.composeLayout(session,def.midLayout,true)
    local layout=def.midLayout;local pair=assert(def.pair or layout.pair)
    check(pair=='building__battle_pyramid','Actual Pyramid uses the wrong native atlas pair')
    check(layout.trueWidth==32 and layout.trueHeight==32,'Actual Pyramid logical dimensions changed')
    check(content(source)==sourceHash,'Actual Pyramid.composeLayout mutated its original base floor')
    for _,cell in ipairs(layout.cells)do sampled[cell.mid]=true end
    assert(Native.get(pair))
    proceduralRooms[#proceduralRooms+1]={entry={map=Pyramid.FLOOR_MAP,pair=pair},source=source,sourceHash=sourceHash,def=def,
     layout=layout,columns=32,rows=32,kind='battle_pyramid',stem='pyramid-seed'..seed,seed=seed,floor=floor,randoms=randoms,
     metadata_sha256=hash(tableString(Pyramid.floorTemplate(session))..tableString(offsets)),geometry_sha256=hash(tableString(layout.cells)..tableString(layout.overrides))}
   end
   for seed=0,3 do appendPyramid(seed,seed,{17+seed*257,42+seed*129,1337+seed*37,499+seed*83})end
   -- Ask the actual native metadata selector for rare square14/15 and3
   -- witnesses. Only compose extra layouts when they add a missing MID;
   -- never inject a source glyph directly into a procedural fixture.
   local function completeRareWitnesses()
    for floor=0,6 do for tail=0,99 do
     if sampled[613]and sampled[619]then return end
     local randoms={30292,12816,17767,tail}
     local session={map=Pyramid.FLOOR_MAP,version=game,frontier={pyramidRandoms=randoms,curChallengeBattleNum=floor}}
     local adds=false
     for _,offset in ipairs(Pyramid.layoutOffsets(session))do
      local ids=squareMids[offset]or{}
      if(not sampled[613]and ids[613])or(not sampled[619]and ids[619])then adds=true end
     end
     if adds then appendPyramid(1000+floor*100+tail,floor,randoms);extraProceduralCases=extraProceduralCases+1 end
    end end
   end
   completeRareWitnesses()
   local ids={};for mid in pairs(sampled)do ids[#ids+1]=mid end;table.sort(ids)
   report.pyramid_sampled_source_mids=ids
   report.pyramid_rare_source_witnesses={mid613=sampled[613]==true,mid619=sampled[619]==true}
   for _,row in ipairs(pyramidSources)do check(content(row.def)==row.hash,'Actual Pyramid composition mutated an imported square layout/events')end
  end
  -- Capture every actual native placement first, then select Gen2 once.
  -- One indexed mod and one warm source/decoder namespace per game.
  assert(mod.exports.select('original'))
  for _,room in ipairs(rooms)do
   reset(room);room.empty=draw(room)
   for _,design in ipairs(fixture.designs)do
    reset(room);local p=place(room,design);local before=draw(room);local nativeMarker=actorMarker(room,p)
    -- All18 actually authored desk/chair designs use native under-only
    -- source artwork. Check that through the original FieldView rather
    -- than assuming the selected replacement mask defines source priority.
    for _,cell in ipairs(p.cells)do for y=0,15 do for x=0,15 do
     equalPixel(nativeMarker,cell.x*16+x,cell.y*16+y,magenta,0,0,'Original placed furniture unexpectedly occluded a normal actor')
    end end end
    room.cases[#room.cases+1]={design=design,placement=p,before=before,nativeMarker=nativeMarker,physics=hash(tableString(p.cells))}
    check(content(room.source)==room.sourceHash,'Native decoration fixture changed the original imported layout/events')
   end
   reset(room);check(draw(room):getString()==room.empty:getString(),'Removing fixture placements did not restore native original room')
  end
  for _,room in ipairs(proceduralRooms)do reset(room);room.before=draw(room)end
  assert(mod.exports.select('gen2'));clock=0
  for _,room in ipairs(rooms)do
   reset(room);local baseline=draw(room)
   local art=assert(mod.exports.state:replacements(game,room.entry.pair),'No cached Gen2 decoration bank')
   -- Verify the entire room once. Each placement then checks every
   -- furniture pixel plus a byte-exact hash of ALL pixels outside it.
   for y=0,room.rows-1 do for x=0,room.columns-1 do
    local row=art[room.layout:midAt(x,y)]
    local expected=row and(row.frames and row.frames[1].under or row.under)or room.empty
    for yy=0,15 do for xx=0,15 do
     equalPixel(baseline,x*16+xx,y*16+yy,expected,row and xx or x*16+xx,row and yy or y*16+yy,'Initial complete native room differs from cached Gen2 art/original source')
    end end
   end end
   local accepted=mod.exports.state.accepted
   for _,case in ipairs(room.cases)do
    reset(room);local placement=place(room,case.design,case.placement)
    check(hash(tableString(placement.cells))==case.physics,'Gen2 theme changed actual native placement collision/elevation/MIDs')
    local after=draw(room);local covered,opaque,transparent=0,0,0
    for _,cell in ipairs(placement.cells)do
     local row=assert(art[cell.mid],'Authored dynamic desk/chair MID lacks a selected Gen2 replacement')
     local image=row.frames and row.frames[1].under or row.under
     for yy=0,15 do for xx=0,15 do equalPixel(after,cell.x*16+xx,cell.y*16+yy,image,xx,yy,'Placed decoration native FieldView differs from cached Gen2 art')end end
     covered=covered+1
    end
    check(outsideHash(after,placement)==outsideHash(baseline,placement),'Actual decoration placement changed pixels outside its complete source footprint')
    check(covered==placement.w*placement.h,'Placed complete desk/chair footprint was skipped')
    local marker=actorMarker(room,placement)
    for _,cell in ipairs(placement.cells)do
     local row=assert(art[cell.mid]);local over=row.frames and row.frames[1].over or row.over
     for y=0,15 do for x=0,15 do
      local a=0;if over then local _,_,_,alpha=over:getPixel(x,y);a=alpha end
      check(a==0 or a==1,'Gen2 furniture foreground must have binary alpha')
      if a==1 then opaque=opaque+1;equalPixel(marker,cell.x*16+x,cell.y*16+y,after,cell.x*16+x,cell.y*16+y,'Furniture foreground failed to cover actor marker')
      else transparent=transparent+1;equalPixel(marker,cell.x*16+x,cell.y*16+y,magenta,0,0,'Furniture transparent foreground hid actor marker')end
      equalPixel(marker,cell.x*16+x,cell.y*16+y,case.nativeMarker,cell.x*16+x,cell.y*16+y,'Gen2 furniture changed original normal-actor priority')
     end end
    end
    local reads,ownReads,assetReads=importReads,0,0;local savedRead,savedPath=mod.read,mod.assets.path
    mod.read=function(self,...)ownReads=ownReads+1;return savedRead(self,...)end
    mod.assets.path=function(self,...)assetReads=assetReads+1;return savedPath(self,...)end
    for frame=1,4 do clock=frame/60;warmDraw(room)end
    mod.read,mod.assets.path=savedRead,savedPath;clock=0
    check(importReads==reads and ownReads==0 and assetReads==0,'Warm placed furniture reread native imports or artwork')
    check(mod.exports.state.accepted==accepted,'Dynamic furniture placement rebuilt cached source rows')
    check(mod.exports.state.rejected==0,'Placed decoration rejected a source/donor recipe')
    check(content(room.source)==room.sourceHash,'Furniture rendering changed actual source layout/events')
    local stem=game..'-'..room.entry.bank..'-decor'..case.design.id
    report.fixtures[#report.fixtures+1]={game=game,map=room.entry.map,pair=room.entry.pair,decoration=case.design,
     private_placement=placement,original=encodePng(case.before,stem..'-native.png'),gen2=encodePng(after,stem..'-gen2.png'),
     native_actor_marker=encodePng(case.nativeMarker,stem..'-native-actor-marker.png'),
     actor_marker=encodePng(marker,stem..'-actor-marker.png'),foreground_opaque_pixels=opaque,foreground_transparent_pixels=transparent,
     actual_native_decor_showOnMap=true,actual_native_field_grid=true,actual_native_field_view=true,
     source_layout_and_events_unchanged=true,source_collision_and_elevation_unchanged=true,source_normal_actor_priority_unchanged=true,
     all_outside_placement_pixels_byte_exact=true,
     warm_frames=4,warm_import_reads=0,warm_asset_reads=0,warm_mapping_rebuilds=0}
    write('progress.json',Json.encode({fixtures=#report.fixtures,game=game,bank=room.entry.bank,decoration=case.design.id}))
   end
   reset(room)
  end
  for _,room in ipairs(proceduralRooms)do
   reset(room);local after=draw(room);local art=assert(mod.exports.state:replacements(game,room.entry.pair))
   local accepted=mod.exports.state.accepted;local used,covered,unreviewed={},0,0
   for y=0,room.rows-1 do for x=0,room.columns-1 do
    local mid=room.layout:midAt(x,y);used[mid]=true;local row=art[mid]
    if row then
     covered=covered+1;local image=row.frames and row.frames[1].under or row.under
     for yy=0,15 do for xx=0,15 do equalPixel(after,x*16+xx,y*16+yy,image,xx,yy,'Actual procedural FieldView differs from cached Gen2 artwork')end end
    else
     unreviewed=unreviewed+1
     for yy=0,15 do for xx=0,15 do equalPixel(after,x*16+xx,y*16+yy,room.before,x*16+xx,y*16+yy,'Unreviewed procedural source pixels changed')end end
    end
   end end
   local reads,ownReads,assetReads=importReads,0,0;local savedRead,savedPath=mod.read,mod.assets.path
   mod.read=function(self,...)ownReads=ownReads+1;return savedRead(self,...)end
   mod.assets.path=function(self,...)assetReads=assetReads+1;return savedPath(self,...)end
   for frame=1,4 do clock=frame/60;warmDraw(room)end
   mod.read,mod.assets.path=savedRead,savedPath;clock=0
   check(importReads==reads and ownReads==0 and assetReads==0,'Warm procedural reread artwork')
   check(mod.exports.state.accepted==accepted and mod.exports.state.rejected==0,'Warm procedural rebuilt/rejected mappings')
   check(hash(tableString(room.layout.cells)..tableString(room.layout.overrides))==room.geometry_sha256,'Gen2 rendering changed actual procedural layout collision/elevation/MIDs')
   check(content(room.source)==room.sourceHash,'Procedural rendering mutated original imported floor/events')
   local ids={};for mid in pairs(used)do ids[#ids+1]=mid end;table.sort(ids)
   local stem=game..'-'..room.stem
   report.procedural_fixtures[#report.procedural_fixtures+1]={game=game,map=room.entry.map,pair=room.entry.pair,kind=room.kind,mode=room.mode,floor=room.floor,
    seed=room.seed,private_pyramid_randoms=room.randoms,
    actual_native_composeLayout=true,actual_native_field_view=true,source_metadata_sha256=room.metadata_sha256,
    source_layout_and_events_unchanged=true,source_collision_and_elevation_unchanged=true,source_metatiles=ids,
    original=encodePng(room.before,stem..'-native.png'),gen2=encodePng(after,stem..'-gen2.png'),
    coverage={visible_cells=room.columns*room.rows,replaced_occurrences=covered,preserved_native_occurrences=unreviewed},
    warm_frames=4,warm_import_reads=0,warm_asset_reads=0,warm_mapping_rebuilds=0}
  end
  if hillManifestHash then check(hash(tableString(require('src.core.game3.rse.trainer_hill').manifest()))==hillManifestHash,'Procedural TrainerHill changed its actual imported challenge metadata')end
  if pyramidManifestHash then check(hash(tableString(require('src.core.game3.rse.frontier.pyramid').manifest()))==pyramidManifestHash,'Procedural Pyramid changed its actual imported floor metadata')end
  for _,row in ipairs(pyramidSources)do check(content(row.def)==row.hash,'Procedural Pyramid rendering changed original source square layout/events')end
  assert(mod.exports.select('original'));clock=0
  for _,room in ipairs(rooms)do
   reset(room);check(draw(room):getString()==room.empty:getString(),'Theme cleanup did not restore actual native empty-room GPU pixels')
   check(content(room.source)==room.sourceHash,'Cleanup mutated the original source layout/events')
  end
  for _,room in ipairs(proceduralRooms)do reset(room);check(draw(room):getString()==room.before:getString(),'Procedural cleanup did not restore original native GPU pixels')end
  check(hash(tableString(Decor.manifest())..tableString(DecorInv.data()))==definitionHash,'Native decoration definitions were mutated')
  Field._game=savedField.game;Field._session=savedField.session;Field.metatileOverrides=savedField.overrides;Field._overrideLayouts=savedField.layouts
  if savedRuntimeGame then require('src.core.game3.runtime')._game=savedRuntimeGame.value end
  mod.exports.dispose()
 end
 check(#report.fixtures==selected.expected_cases,'Some actual decoration/game/bank combinations were skipped')
 check(#report.procedural_fixtures==selected.expected_procedural_cases+extraProceduralCases,'Some actual procedural mode/floor/seed combinations were skipped')
 report.status='passed';write('report.json',Json.encode(report))
end
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    parser.add_argument('--games', nargs='+', choices=GAMES, default=list(GAMES))
    parser.add_argument('--banks', nargs='+', choices=BANKS, default=list(BANKS))
    parser.add_argument('--pilot', action='store_true')
    parser.add_argument('--skip-procedural', action='store_true')
    parser.add_argument('--pyramid', action='store_true', help='Also render deterministic private Pyramid source witnesses')
    parser.add_argument('--pyramid-only', action='store_true', help='Run only deterministic Emerald Pyramid source witnesses')
    args, remaining = parser.parse_known_args()
    cache_arg = remaining[remaining.index('--cache') + 1] if '--cache' in remaining else os.environ['APPDATA'] + '/pokemon-love2d'
    cache = Path(cache_arg).resolve()
    chosen = selection(cache, ['emerald'] if args.pyramid_only else args.games,
                       [] if args.pyramid_only else args.banks, args.pilot,
                       not args.skip_procedural and not args.pyramid_only, args.pyramid or args.pyramid_only)
    if args.pyramid_only:
        for fixture in chosen['fixtures']:
            fixture['designs'] = []
        chosen['expected_cases'] = 0
    if '--output' not in remaining:
        remaining.extend(['--output', str(Path(__file__).resolve().parents[2] / '.work/tileshift-reverse-decor-gpu')])
    output = Path(remaining[remaining.index('--output') + 1]).resolve()
    base = validate_gpu.LUA
    prefix = base[:base.index(' -- Native Gen1 TileRenderer on real Red Pallet Town.')]
    validate_gpu.LUA = prefix + BODY.replace('@SELECTION@', json.dumps(json.dumps(chosen, separators=(',', ':')))) + base[base.index('\nfunction love.load()'):]
    sys.argv[1:] = remaining
    output.mkdir(parents=True, exist_ok=True)
    with (output / 'runner-output.json').open('w', encoding='utf-8') as log, contextlib.redirect_stdout(log):
        result = validate_gpu.main()
    source_unchanged = all(hashlib.sha256((cache / name).read_bytes()).hexdigest() == expected
                           for name, expected in chosen['source_file_sha256'].items())
    report_path = output / 'report.json'
    if report_path.exists():
        report = json.loads(report_path.read_text())
        report['imported_source_files_unchanged'] = source_unchanged
        report['checked_source_files'] = len(chosen['source_file_sha256'])
        if not source_unchanged:
            report['status'] = 'failed'
        report_path.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(dict(status=report['status'], fixtures=len(report.get('fixtures', [])),
                              procedural_fixtures=len(report.get('procedural_fixtures', [])),
                              checks=report.get('checks'), source_files_unchanged=source_unchanged,
                              error=report.get('error'), report=str(report_path))))
    return result if source_unchanged else 1


if __name__ == '__main__':
    raise SystemExit(main())
