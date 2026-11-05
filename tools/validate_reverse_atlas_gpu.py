"""Native FieldView atlas fixtures for every actually used Crystal-theme key.

Real used MIDs are arranged in private 8-column grids, preserving an actual
source cell's collision/elevation as a witness. This verifies rendering and
animations, not actual-map geometry or gameplay. Source maps remain untouched.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import sys
import zlib

import catalog
import preview
import validate_gpu

GAMES = ('firered', 'leafgreen', 'ruby', 'sapphire', 'emerald')


def selection(root: Path, cache: Path, planner: Path, games: list[str], pilot: bool,
              only_modules: list[str] | None = None, only_keys: Path | None = None) -> dict:
    inputs = validate_gpu.runtime_fingerprint(root)
    paths = list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]", (root / 'main.lua').read_text())))
    requested = []
    for value in only_modules or []:
        path = Path(value)
        path = (root / path).resolve() if not path.is_absolute() else path.resolve()
        assert path.is_relative_to(root.resolve()) and path.suffix == '.lua', 'Delta modules must be Lua files within the selected mod'
        name = path.relative_to(root.resolve()).as_posix()
        assert name in paths, 'Requested delta module is not loaded by current main: ' + name
        if name not in requested:
            requested.append(name)
    assert not (requested and only_keys), 'Select whole modules or an exact key inventory'
    selected_keys = None
    if only_keys:
        inventory = json.loads(only_keys.read_text())
        assert isinstance(inventory, list) and inventory, 'An exact key inventory must be a nonempty list'
        selected_keys = {(r['game'], r['pair'], r['mid']) for r in inventory}
        assert len(selected_keys) == len(inventory), 'Exact key inventory repeats a source key'
        assert all(g in GAMES and isinstance(p, str) and type(m) is int for g,p,m in selected_keys), 'Invalid exact source key'
    scoped = bool(requested) or selected_keys is not None
    plan = None if scoped else json.loads(planner.read_text())
    if plan is not None:
        assert inputs == plan['runtime_inputs'], 'The native matrix plan belongs to a different runtime snapshot'
    rows, owners, module_counts = {}, {}, {}
    for name in paths:
        count = 0
        for row in preview.read_reviewed(root / name):
            if row['style'] != 'gen2' or row['game'] not in GAMES:
                continue
            assert row.get('map') is None, 'Native GBA atlas themes must be pair-global'
            key = row['game'], row['tileset'], row['id']
            assert key not in rows, 'Current main has duplicate Gen2 GBA key: ' + str(key)
            rows[key], owners[key] = row, name
            count += 1
        if name in requested:
            module_counts[name] = count
    if selected_keys is not None:
        assert selected_keys.issubset(rows), 'Exact inventory contains keys not loaded by current main'
        requested = sorted({owners[key] for key in selected_keys})
        module_counts = {name: sum(owner == name for owner in owners.values()) for name in requested}
    delta_keys = selected_keys if selected_keys is not None else {key for key, name in owners.items() if name in requested}
    if scoped:
        assert delta_keys and all(module_counts.values()), 'Every delta module must contain current Gen2 GBA rows'
        assert all(re.fullmatch(r'[0-9a-f]{64}', rows[key].get('compositionPixelHash', '')) for key in delta_keys), 'Every delta row needs its independently authored RGBA hash'
    manifests = {g: catalog.read_lua(cache / g / 'data/generated/gba/native/manifest.lua')['layouts'] for g in GAMES}
    scenes = ([dict(game=g, map=n) for g in GAMES for n in sorted(manifests[g])]
              if scoped else plan['scenes'])
    witnesses, header_witnesses, source_files = {}, defaultdict(list), {}
    all_headers = {}
    body_keys = set()
    for scene in scenes:
        game, name = scene['game'], scene['map']
        spec = manifests[game][name]
        path = cache / game / 'data/generated/gba/native' / spec['file']
        data = path.read_bytes()
        checksum = hashlib.sha256(data).hexdigest()
        if plan is not None:
            assert checksum == scene['layout_sha256'], 'Actual source layout changed since matrix planning'
        blob = data if data[:4] == b'SVML' else zlib.decompress(data)
        assert blob[:4] == b'SVML'
        width, height, tw, th = struct.unpack_from('<HHHH', blob, 6)
        columns, lines = tw or width, th or height
        border_width, border_height = blob[14], blob[15]
        offset = 16 + border_width * border_height * 2
        if scoped:
            actual_header = set()
            for i in range(border_width * border_height):
                mid = struct.unpack_from('<H', blob, 16 + i * 2)[0]
                key = game, spec['pair'], mid
                actual_header.add(key)
                if key in delta_keys and game in games:
                    header_witnesses[key].append(dict(map=name, x=i % border_width, y=i // border_width,
                                                       width=border_width, height=border_height,
                                                       layout_sha256=checksum))
            all_headers[game, name] = actual_header
        for y in range(lines):
            for x in range(columns):
                at = offset + (y * width + x) * 4
                mid = struct.unpack_from('<H', blob, at)[0]
                key = game, spec['pair'], mid
                body_keys.add(key)
                if key in rows and (not scoped or key in delta_keys) and key not in witnesses:
                    witnesses[key] = dict(map=name, x=x, y=y, mid=mid, coll=blob[at + 2], elev=blob[at + 3])
        source_files[path.relative_to(cache).as_posix()] = checksum
    if scoped:
        assert set(witnesses) == delta_keys.intersection(body_keys), 'Actual native body scan omitted a delta key'
    else:
        assert len(witnesses) == plan['used_source_keys'], 'Used-key matrix is incomplete'
    grouped = defaultdict(list)
    animation_cache = {}
    for (game, pair, mid), witness in sorted(witnesses.items()):
        row = rows[game, pair, mid]
        item = dict(witness, sourceHash=row['sourceHash'])
        if row.get('compositionPixelHash'):
            item['compositionPixelHash'] = row['compositionPixelHash']
        ground = row.get('classicGeometry', {}).get('ground', {})
        if ground.get('animation'):
            frames = preview.classic_geometry_frames(cache, row, animation_cache)
            item['classicFrameHashes'] = [catalog.sha(frame.tobytes()) for frame in frames]
            assert item['classicFrameHashes'][0] == item['compositionPixelHash']
        source_animation = row.get('classicGeometry', {}).get('sourceAnimation', {})
        if source_animation.get('mode') == 'native_under':
            from classic_geometry_review import source_under_frames
            preview.classic_geometry_layers(cache, row, animation_cache)
            native_frames, _, _ = source_under_frames(cache, game, pair, mid, animation_cache, source_animation)
            themed_frames = preview.classic_geometry_frames(cache, row, animation_cache)
            assert len(native_frames) == len(themed_frames)
            frame_hashes = {catalog.sha(native.tobytes()): catalog.sha(themed.tobytes())
                            for native, themed in zip(native_frames, themed_frames)}
            assert len(frame_hashes) >= 2
            manifest = catalog.read_lua(cache / game / 'data/generated/gba/native' / pair / 'anim_manifest.lua')
            bank = next(bank for bank in manifest['banks'] if bank['name'] == source_animation['bank'])
            counter = bank.get('counter', 'primary')
            assert counter in ('primary', 'secondary')
            ticks = bank['period'] * (bank['frames'] + bank.get('slot', 0) + 2)
            assert 0 < ticks <= 65536
            item['nativeUnder'] = dict(frameHashes=frame_hashes, counter=counter, period=bank['period'],
                                       phase=bank.get('phase', 0), ticks=ticks)
        native_over = row.get('classicGeometry', {}).get('nativeOver')
        if native_over:
            layers = preview.classic_geometry_layers(cache, row, animation_cache)
            item['retainedOverHex'] = layers['over'].tobytes().hex()
            manifest = catalog.read_lua(cache / game / 'data/generated/gba/native' / pair / 'anim_manifest.lua')
            bank = next(bank for bank in manifest['banks'] if bank['name'] == native_over['bank'])
            item['retainedOverSchedule'] = {key: bank[key] for key in ('period', 'phase', 'frames')}
        if scoped:
            item['source_module'] = owners[game, pair, mid]
        grouped[game, pair].append(item)
    fixtures = []
    for game in games:
        pairs = [dict(pair=pair, source_map=items[0]['map'], items=items)
                 for (g, pair), items in sorted(grouped.items()) if g == game]
        if pilot:
            wanted = 'general__petalburg' if game in ('ruby', 'sapphire', 'emerald') else 'pallet_outdoor'
            preferred = [p for p in pairs if p['pair'] == wanted]
            pairs = preferred or pairs[:1]
            assert pairs
        fixtures.append(dict(game=game, pairs=pairs))
    result = dict(fixtures=fixtures, expected_keys=sum(len(p['items']) for f in fixtures for p in f['pairs']),
                  full_planner_used_keys=len(witnesses), pilot=pilot, source_file_sha256=source_files,
                  runtime_sha256=inputs['sha256'])
    if scoped:
        requested_game_keys = {k for k in delta_keys if k[0] in games}
        header = [dict(game=g, pair=p, mid=m, module=owners[g,p,m],
                       body_used=(g,p,m) in body_keys, witnesses=items)
                  for (g,p,m), items in sorted(header_witnesses.items())]
        result['delta'] = dict(modules=requested, module_gen2_gba_row_counts=module_counts,
                               total_module_keys=sum(module_counts.values()), selected_inventory_keys=len(delta_keys),
                               requested_game_keys=len(requested_game_keys),
                               actual_body_used_keys=sum(k[0] in games for k in witnesses),
                               selected_fixture_keys=result['expected_keys'], scanned_native_layouts=len(scenes),
                               excluded_no_body_witness=[dict(game=g,pair=p,mid=m,module=owners[g,p,m],
                                                            header_used=(g,p,m) in header_witnesses)
                                                         for g,p,m in sorted(requested_game_keys-body_keys)],
                               current_main_exact_module_keys=selected_keys is None,
                               current_main_exact_inventory_keys=selected_keys is not None,
                               key_inventory_sha256=hashlib.sha256(only_keys.read_bytes()).hexdigest() if only_keys else None,
                               actual_used_key_set_complete=True)
        result['native_header_plan'] = dict(touched_keys=len(header), keys=header,
                                           needed=bool(header), all_native_headers_scanned=True,
                                           source='Actual SVML borderWidth/borderHeight and uint16 header MIDs, not map-edge body inference')
        missing = set(header_witnesses)
        candidates = {key: values.intersection(missing) for key, values in all_headers.items() if values.intersection(missing)}
        selected_scenes = []
        while missing:
            key = max(candidates, key=lambda value: (len(candidates[value].intersection(missing)), value))
            assert candidates[key].intersection(missing), 'Delta header set-cover omitted a touched key'
            selected_scenes.append(key)
            missing.difference_update(candidates[key])
        sampled_keys = set().union(*(all_headers[key] for key in selected_scenes)) if selected_scenes else set()
        result['native_header_plan']['scenes'] = [dict(game=g, map=n) for g,n in selected_scenes]
        result['native_header_plan']['sampled_all_header_keys'] = len(sampled_keys)
        result['native_header_plan']['inventory'] = dict(all_border=[
            dict(game=g, pair=p, id=mid, touched_by_delta=(g,p,mid) in header_witnesses,
                 maps=[name for game,name in selected_scenes if game == g and (g,p,mid) in all_headers[game,name]])
            for g,p,mid in sorted(sampled_keys)])
    assert inputs == validate_gpu.runtime_fingerprint(root), 'Runtime changed while constructing the native key plan; retry after integration is frozen'
    return result


BODY = r"""
 local Native=require('src.core.game3.tileset_native')
 local Anim=require('src.core.game3.tileset_anim')
 local Versions=require('src.import.gba.versions')
 local CachePaths=require('src.core.game3.cache_paths')
 local Dataset=require('src.core.game3.dataset')
 local Map=require('src.core.game3.map')
 local LayoutNative=require('src.core.game3.layout_native')
 local View=require('src.core.game3.field_view')
 local selected=Json.decode(@SELECTION@)
 report.theme='native_gen2_used_atlas_fixtures';report.selection=selected
 report.limits='Actual native FieldView on PRIVATE 8-column atlas grids containing only real used MIDs with actual-cell witnesses. Not actual-map layout/joins, gameplay or collision semantics. Every original imported source map/events stays unchanged; actual-map witnesses are validated separately.'
 local function clone(value,seen)
  if type(value)~='table'then return value end
  seen=seen or{};if seen[value]then return seen[value]end
  local out={};seen[value]=out;for k,v in pairs(value)do out[k]=clone(v,seen)end
  return setmetatable(out,getmetatable(value))
 end
 local function sourceContent(def)
  return hash(tableString(def.midLayout.cells)..tableString(def.midLayout.overrides)..tableString(def.warps)..tableString(def.objects)..tableString(def.coordEvents))
 end
 local bytesCache,foregroundCache,compositeCache,retainedOver={},{},{},{}
 local magentaPixel=string.char(255,0,255,255)
 local function bytes(image)
  if not bytesCache[image]then bytesCache[image]=image:getString()end
  return bytesCache[image]
 end
 local function currentFrame(row)
  if not row.frames then return row end
  local elapsed=math.max(0,clock-(row.offset or 0))
  return row.frames[math.floor(elapsed/row.period)%#row.frames+1]
 end
 local function retainForeground(row,image)
  retainedOver[row]=image;compositeCache[row]=nil
  for _,frame in ipairs(row.frames or{})do
   retainedOver[frame]=image;compositeCache[frame]=nil
  end
 end
 local function compositeBytes(frame)
  if compositeCache[frame]then return compositeCache[frame]end
  local under=bytes(frame.under)
  local middle=frame.mid and bytes(frame.mid)
  local top=frame.over or retainedOver[frame]
  local over=top and bytes(top)
  local pixels={}
  for offset=1,#under,4 do
   local pixel=under:sub(offset,offset+3)
   if middle and middle:byte(offset+3)~=0 then
    check(middle:byte(offset+3)==255,'Classic middle plane must have binary alpha')
    pixel=middle:sub(offset,offset+3)
   end
   if over and over:byte(offset+3)~=0 then
    check(over:byte(offset+3)==255,'Classic over plane must have binary alpha')
    pixel=over:sub(offset,offset+3)
   end
   pixels[#pixels+1]=pixel
  end
  local result=table.concat(pixels)
  compositeCache[frame]=result
  return result
 end
 local function foregroundBytes(image)
  if not image then return magentaPixel:rep(256)end
  local raw=bytes(image);if foregroundCache[raw]then return foregroundCache[raw]end
  local out={}
  for i=1,#raw,4 do
   local a=raw:byte(i+3);check(a==0 or a==255,'Classic foreground must have binary alpha')
   out[#out+1]=a==255 and raw:sub(i,i+3)or magentaPixel
  end
  local result=table.concat(out);foregroundCache[raw]=result;return result
 end
 local function expectedBytes(room,art,over)
  local out={}
  for y=0,room.rows-1 do for yy=0,15 do
   for x=0,7 do
    local mid=room.layout:midAt(x,y);local row=assert(art[mid],'Used source key has no cached Gen2 image')
    local frame=currentFrame(row)
    local raw=over and foregroundBytes(frame.over or retainedOver[frame])or compositeBytes(frame)
    out[#out+1]=raw:sub(yy*64+1,yy*64+64)
   end
  end end
  return table.concat(out)
 end
 local exactPixels,tolerantPixels,independentHashes,verifiedKeys,independentAnimationFrames=0,0,0,0,0
 local nativeOverChecks,nativeUnderChecks,nativeUnderKeys=0,0,0
 local function verifyImage(actual,expected,message)
  local raw=actual:getString();check(#raw==#expected,'Atlas RGBA byte count differs')
  if raw==expected then exactPixels=exactPixels+#raw/4;check(true,message..' byte-exact');return end
  -- A GPU conversion may round a component by one byte. Check EVERY byte
  -- independently in that case; never replace full verification with a sample.
  for i=1,#raw do check(math.abs(raw:byte(i)-expected:byte(i))<=1,message..' at RGBA byte'..i)end
  tolerantPixels=tolerantPixels+#raw/4
 end
 for _,fixture in ipairs(selected.fixtures)do
  local game=fixture.game;GV.set(game);assetGame=game;clock=0
  local cache={read=function(_,path)return cacheRead(game..'/'..path)end,exists=function(self,path)return self:read(path)~=nil end}
  Versions.selectCache(game,cache);CachePaths.reset();Dataset.cacheRootOverride=nil;Dataset.mountExtractRoots();Native.install(cache)
  local originals=Dataset.buildMaps();local maps={};for k,v in pairs(originals)do maps[k]=v end
  local mod=startMod(game,3);mod.save.set=function()end
  local host={data={maps=maps},save={flags={},vars={},options={}},options={},world={map={},player={facing='down'}}};mod.game=host
  local rooms={}
  for _,bank in ipairs(fixture.pairs)do
   local source=assert(originals[bank.source_map]);Dataset.attachMidLayouts({[bank.source_map]=source},cache)
   local sourceHash=sourceContent(source);local def=clone(source);local n=#bank.items;local rows=math.ceil(n/8);local cells={}
   for i=1,rows*8 do
    local item=bank.items[i]or bank.items[1]
    cells[i]={mid=item.mid,coll=item.coll,elev=item.elev}
   end
   def.midLayout=LayoutNative.fromDecoded({width=8,height=rows,trueWidth=8,trueHeight=rows,borderWidth=1,borderHeight=1,
    borderMids={bank.items[1].mid},cells=cells},bank.source_map,bank.pair)
   def.width=4;def.height=math.ceil(rows/2);def.pair=bank.pair
   check(sourceContent(source)==sourceHash,'Building private atlas mutated actual map/events')
   assert(Native.get(bank.pair))
   rooms[#rooms+1]={bank=bank,source=source,sourceHash=sourceHash,def=def,layout=def.midLayout,rows=rows}
  end
  local function bind(room)
   local id=room.bank.source_map;maps[id]=room.def
   host.save.position={map=id};host.world.map={id=id};host.world.player.px=56;host.world.player.py=room.rows*8-8
   Map._def=room.def;Map._currentDef=room.def;Map.current=id;Map.neighborList={};Map.neighbors={}
   Anim.setVisiblePairs({[room.bank.pair]=true});Anim.enterMap(room.bank.pair,false)
   View.invalidate();View._flashMapId=id;View.setFlashLevel(0)
  end
  local function draw(room,marker)
   local calls=0
   local opts={skipActors=not marker}
   if marker then opts.endUnderActors=function()
    calls=calls+1;G.setColor(1,0,1,1);G.rectangle('fill',0,0,128,room.rows*16);G.setColor(1,1,1,1)
   end end
   local image=capture(128,room.rows*16,function()View.draw(host,128,room.rows*16,opts)end)
   if marker then check(calls==1,'Atlas marker missed the native normal-actor boundary')end
   return image
  end
  local function warmDraw(room)
   if not room.canvas then room.canvas=G.newCanvas(128,room.rows*16,{dpiscale=1,format='rgba8'})end
   G.push('all');G.setCanvas(room.canvas);G.origin();G.setScissor();G.setShader();G.clear(0,0,0,0);G.setColor(1,1,1,1)
   View.draw(host,128,room.rows*16,{skipActors=true});G.pop()
  end
  assert(mod.exports.select('original'))
  for _,room in ipairs(rooms)do bind(room);room.before=draw(room)end
  assert(mod.exports.select('gen2'));clock=0
  for _,room in ipairs(rooms)do
   bind(room);local after=draw(room);local art=assert(mod.exports.state:replacements(game,room.bank.pair))
   local rowHashes=0;local schedules,times={},{}
   times['0']=0
   for _,item in ipairs(room.bank.items)do
    local row=assert(art[item.mid],'Actual used source MID was rejected or skipped')
    if item.retainedOverHex then
     check(row.over==nil,'Theme owns the retained native foreground')
     local raw=love.data.decode('string','hex',item.retainedOverHex)
     retainForeground(row,love.image.newImageData(16,16,'rgba8',raw))
    end
    if item.compositionPixelHash then
     local first=row.frames and row.frames[1]or row
     check(hash(compositeBytes(first))==item.compositionPixelHash,'Cached frame0 differs from independent authored compositionPixelHash: '..game..'/'..room.bank.pair..'/'..item.mid)
     independentHashes=independentHashes+1;rowHashes=rowHashes+1
    end
    verifiedKeys=verifiedKeys+1
    if row.frames then
     local count,period,offset=#row.frames,row.period,row.offset or 0
     check(period and period>0 and count>=1,'Invalid cached animation schedule')
     local key=count..'/'..string.format('%.12g',period)..'/'..string.format('%.12g',offset)
     schedules[key]={frames=count,period=period,offset=offset,bank=row.bank}
     if item.classicFrameHashes then
      check(#item.classicFrameHashes==count,'Classic ground frame count differs from independent native program')
      for index,expected in ipairs(item.classicFrameHashes)do
       check(hash(compositeBytes(row.frames[index]))==expected,'Classic ground frame differs from independent native program: '..game..'/'..room.bank.pair..'/'..item.mid..' frame '..index)
       independentAnimationFrames=independentAnimationFrames+1
      end
     end
     for i=0,count-1 do
      local at=i*period+offset+.00001
      while at<0 do at=at+count*period end
      times[string.format('%.12g',at)]=at
     end
    end
   end
   local ordered={};for _,at in pairs(times)do ordered[#ordered+1]=at end;table.sort(ordered)
   for _,at in ipairs(ordered)do
    clock=at;verifyImage(draw(room),expectedBytes(room,art,false),'Actual FieldView atlas under pixels differ from cached/literal-verified art')
    verifyImage(draw(room,true),expectedBytes(room,art,true),'Actual FieldView foreground differs from selected classic mask/frame')
   end
   clock=0;after=draw(room)
   local accepted=mod.exports.state.accepted;local reads,ownReads,assetReads=importReads,0,0;local savedRead,savedPath=mod.read,mod.assets.path
   mod.read=function(self,...)ownReads=ownReads+1;return savedRead(self,...)end
   mod.assets.path=function(self,...)assetReads=assetReads+1;return savedPath(self,...)end
   for frame=1,4 do clock=frame*.371;warmDraw(room)end
   mod.read,mod.assets.path=savedRead,savedPath;clock=0
   check(importReads==reads and ownReads==0 and assetReads==0,'Warm native atlas rendering reread artwork')
   check(mod.exports.state.accepted==accepted and mod.exports.state.rejected==0,'Warm atlas rendering rebuilt/rejected source rows')
   check(sourceContent(room.source)==room.sourceHash,'Private native atlas changed actual source map/events')
   report.fixtures[#report.fixtures+1]={game=game,pair=room.bank.pair,source_map=room.bank.source_map,used_keys=#room.bank.items,
    private_atlas_dimensions={width=8,height=room.rows,padding_repeats=room.rows*8-#room.bank.items},
    independent_composition_hashes=rowHashes,animation_schedules=schedules,checked_phase_times=#ordered,
    original=encodePng(room.before,game..'-'..room.bank.pair..'-native-atlas.png'),gen2=encodePng(after,game..'-'..room.bank.pair..'-gen2-atlas.png'),
    all_used_keys_verified=true,all_native_animation_phases_verified=true,foreground_marker_verified=true,
    source_maps_and_events_unchanged=true,warm_import_reads=0,warm_asset_reads=0,warm_mapping_rebuilds=0}
   write('progress.json',Json.encode({fixtures=#report.fixtures,verified_keys=verifiedKeys,game=game,pair=room.bank.pair}))
  end
  -- An option change deliberately invalidates cached theme art. Exercise each
  -- option once for the game, rather than rebuilding all earlier banks for
  -- every fixture; every bank still receives its own independent Off check.
  for _,key in ipairs({'speed_water','speed_flowers'})do mod._probeEvents:emit('mod.options_changed',{mod='tileshift',key=key,value=1})end
  for index,room in ipairs(rooms)do
   bind(room);clock=0;local frozen=draw(room);clock=9.37
   check(draw(room):getString()==frozen:getString(),'Off speed animated an atlas fixture')
   report.fixtures[#report.fixtures-#rooms+index].off_speed_verified=true
  end
  for _,key in ipairs({'speed_water','speed_flowers'})do mod._probeEvents:emit('mod.options_changed',{mod='tileshift',key=key,value=3})end
  assert(mod.exports.select('original'));clock=0
  for _,room in ipairs(rooms)do bind(room);check(draw(room):getString()==room.before:getString(),'Atlas theme cleanup did not restore original native pixels')end
  local function sourceOver(room,mid)
   local atlas=assert(Native.get(room.bank.pair))
   local slot=assert(atlas.midToSlot[mid])
   local tile=love.image.newImageData(16,16)
   tile:paste(atlas.overImageData,0,0,(slot%atlas.cols)*16,math.floor(slot/atlas.cols)*16,16,16)
   return tile
  end
  local function witnessTile(image,index)
   local tile=love.image.newImageData(16,16)
   tile:paste(image,0,0,((index-1)%8)*16,math.floor((index-1)/8)*16,16,16)
   return tile
  end
  local preserved={}
  for _,room in ipairs(rooms)do
   local items,indices,phaseTimes,lastTick={},{},{},0
   for index,item in ipairs(room.bank.items)do
    local schedule=item.retainedOverSchedule
    if schedule then
     items[#items+1]=item
     indices[item.mid]=index
     local start=schedule.phase==0 and schedule.period or schedule.phase
     for frame=0,schedule.frames do
      local tick=start+frame*schedule.period
      phaseTimes[tick]=true
      lastTick=math.max(lastTick,tick)
     end
    end
   end
   if #items>0 then
    bind(room);draw(room)
    local baseline,lastByMid,changed={},{},false
    for tick=1,lastTick do
     Anim.stepRse()
     if phaseTimes[tick]then
      baseline[tick]={}
      for _,item in ipairs(items)do
       local value=hash(bytes(sourceOver(room,item.mid)))
       if lastByMid[item.mid] and lastByMid[item.mid]~=value then changed=true end
       lastByMid[item.mid]=value;baseline[tick][item.mid]=value
      end
     end
    end
    check(changed,'Native retained foreground did not animate')
    preserved[#preserved+1]={room=room,items=items,indices=indices,baseline=baseline,lastTick=lastTick}
   end
  end
  if #preserved>0 then
   assert(mod.exports.select('gen2'))
   for _,proof in ipairs(preserved)do
    local room=proof.room
    bind(room);draw(room)
    local art=assert(mod.exports.state:replacements(game,room.bank.pair))
    for tick=1,proof.lastTick do
     Anim.stepRse()
     if proof.baseline[tick]then
      for _,item in ipairs(proof.items)do
       local row=assert(art[item.mid]);check(row.over==nil,'Retained foreground was copied into the theme atlas')
       local image=sourceOver(room,item.mid)
       check(hash(bytes(image))==proof.baseline[tick][item.mid],'Native foreground playback changed under the theme')
       retainForeground(row,image);nativeOverChecks=nativeOverChecks+1
      end
      local foreground,complete=draw(room,true),draw(room)
      for _,item in ipairs(proof.items)do
       local frame=currentFrame(art[item.mid]);local index=proof.indices[item.mid]
       verifyImage(witnessTile(foreground,index),foregroundBytes(retainedOver[frame]),
        'Retained native foreground crossed the actor boundary')
       verifyImage(witnessTile(complete,index),compositeBytes(frame),
        'Retained native foreground did not combine with the themed background')
      end
     end
    end
   end
   assert(mod.exports.select('original'))
   for _,proof in ipairs(preserved)do
    bind(proof.room);draw(proof.room)
    for tick=1,proof.lastTick do
     Anim.stepRse()
     for _,item in ipairs(proof.items)do
      if proof.baseline[tick]then
       check(hash(bytes(sourceOver(proof.room,item.mid)))==proof.baseline[tick][item.mid],
        'Cleanup changed retained foreground animation')
      end
     end
    end
   end
  end
  local function nativeUnder(room,mid)
   local atlas=assert(Native.get(room.bank.pair));local slot=assert(atlas.midToSlot[mid])
   local tile=love.image.newImageData(16,16)
   tile:paste(atlas.imageData,0,0,(slot%atlas.cols)*16,math.floor(slot/atlas.cols)*16,16,16)
   return hash(tile:getString())
  end
  for _,room in ipairs(rooms)do
   local items,lastTick={},0
   for index,item in ipairs(room.bank.items)do
    if item.nativeUnder then
     items[#items+1]={item=item,index=index,seen={}}
     lastTick=math.max(lastTick,item.nativeUnder.ticks)
     nativeUnderKeys=nativeUnderKeys+1
    end
   end
   if #items>0 then
    -- Drawing after binding attaches the native bank before its first tick.
    bind(room);draw(room)
    local baseline={}
    for tick=1,lastTick do
     Anim.stepRse()
     for _,witness in ipairs(items)do
      local item=witness.item;local program=item.nativeUnder
      if Anim._rse[program.counter]%program.period==program.phase then
       local source=nativeUnder(room,item.mid)
       check(program.frameHashes[source]~=nil,'Native animation differs from its checked bank: '..room.bank.pair..'/'..item.mid)
       witness.seen[source]=true
       local samples=baseline[tick]or{};baseline[tick]=samples
       samples[#samples+1]={witness=witness,source=source}
      end
     end
    end
    for _,witness in ipairs(items)do
     for source in pairs(witness.item.nativeUnder.frameHashes)do
      check(witness.seen[source],'A guarded native animation phase was never rendered')
     end
    end
    assert(mod.exports.select('gen2'));bind(room);draw(room)
    for tick=1,lastTick do
     Anim.stepRse()
     if baseline[tick]then
      local image=draw(room)
      for _,sample in ipairs(baseline[tick])do
       local witness=sample.witness;local item=witness.item
       check(hash(witnessTile(image,witness.index):getString())==item.nativeUnder.frameHashes[sample.source],
        'Themed animation changed its native cadence or pixels: '..room.bank.pair..'/'..item.mid)
       nativeUnderChecks=nativeUnderChecks+256
      end
     end
    end
    assert(mod.exports.select('original'));bind(room);draw(room)
    for tick=1,lastTick do
     Anim.stepRse()
     for _,sample in ipairs(baseline[tick]or{})do
      check(nativeUnder(room,sample.witness.item.mid)==sample.source,'Cleanup changed the original animation phase')
     end
    end
   end
  end
  mod.exports.dispose()
 end
 check(verifiedKeys==selected.expected_keys,'Some actual used source keys were skipped')
 report.verified_source_keys=verifiedKeys;report.independent_composition_hashes=independentHashes
 report.independent_classic_animation_frames=independentAnimationFrames
 report.retained_native_foreground_checks=nativeOverChecks
 report.native_under_animation_keys=nativeUnderKeys;report.native_under_gpu_pixels=nativeUnderChecks
 report.byte_exact_gpu_pixels=exactPixels;report.tolerance_checked_gpu_pixels=tolerantPixels
 report.status='passed';write('report.json',Json.encode(report))
end
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    parser.add_argument('--games', nargs='+', choices=GAMES, default=list(GAMES))
    parser.add_argument('--planner', type=Path, default=Path(__file__).resolve().parents[2] / '.work/tileshift-v0320-final-reverse-matrix/report.json')
    parser.add_argument('--pilot', action='store_true')
    parser.add_argument('--only-module', action='append', default=[],
                        help='Repeat for exact current main modules whose actually used Gen2 keys should be tested')
    parser.add_argument('--keys-json', type=Path,
                        help='Exact nonempty list of game/pair/mid keys loaded by current main; mutually exclusive with --only-module')
    parser.add_argument('--plan-only', action='store_true', help='Write exact body/header delta inventory without launching a GPU probe')
    args, remaining = parser.parse_known_args()
    root = Path(remaining[remaining.index('--mod-root') + 1]).resolve() if '--mod-root' in remaining else Path(__file__).resolve().parents[1]
    cache = Path(remaining[remaining.index('--cache') + 1]).resolve() if '--cache' in remaining else Path(os.environ['APPDATA']) / 'pokemon-love2d'
    chosen = selection(root, cache, args.planner, args.games, args.pilot, args.only_module, args.keys_json)
    if '--output' not in remaining:
        remaining.extend(['--output', str(root.parent / '.work/tileshift-reverse-atlas-gpu')])
    output = Path(remaining[remaining.index('--output') + 1]).resolve();output.mkdir(parents=True, exist_ok=True)
    (output / 'selection.json').write_text(json.dumps(chosen, indent=2) + '\n')
    if chosen.get('native_header_plan') is not None:
        (output / 'native-header-plan.json').write_text(json.dumps(chosen['native_header_plan'], indent=2) + '\n')
        (output / 'native-header-inventory.json').write_text(json.dumps(chosen['native_header_plan']['inventory'], indent=2) + '\n')
        (output / 'native-header-scenes.json').write_text(json.dumps(chosen['native_header_plan']['scenes'], indent=2) + '\n')
    if args.plan_only:
        print(json.dumps(dict(status='planned', banks=sum(len(f['pairs']) for f in chosen['fixtures']),
                              used_keys=chosen['expected_keys'], delta=chosen.get('delta'),
                              header_touched_keys=chosen.get('native_header_plan', {}).get('touched_keys'),
                              runtime_sha256=chosen['runtime_sha256'], output=str(output))))
        return 0
    base = validate_gpu.LUA
    validate_gpu.LUA = base[:base.index(' -- Native Gen1 TileRenderer on real Red Pallet Town.')] + BODY.replace('@SELECTION@', json.dumps(json.dumps(chosen, separators=(',', ':')))) + base[base.index('\nfunction love.load()'):]
    sys.argv[1:] = remaining
    with (output / 'runner-output.json').open('w', encoding='utf-8') as log, contextlib.redirect_stdout(log):
        result = validate_gpu.main()
    unchanged = all(hashlib.sha256((cache / name).read_bytes()).hexdigest() == expected for name, expected in chosen['source_file_sha256'].items())
    inventory_unchanged = args.keys_json is None or hashlib.sha256(args.keys_json.read_bytes()).hexdigest() == chosen['delta']['key_inventory_sha256']
    path = output / 'report.json'
    if path.exists():
        report = json.loads(path.read_text());report['source_layout_files_unchanged'] = unchanged
        report['key_inventory_unchanged'] = inventory_unchanged
        if not unchanged or not inventory_unchanged:report['status'] = 'failed'
        path.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(dict(status=report['status'], verified_source_keys=report.get('verified_source_keys'),
                              independent_hashes=report.get('independent_composition_hashes'),
                              exact_pixels=report.get('byte_exact_gpu_pixels'), tolerant_pixels=report.get('tolerance_checked_gpu_pixels'),
                              error=report.get('error'), report=str(path))))
    return result if unchanged and inventory_unchanged else 1


if __name__ == '__main__':
    raise SystemExit(main())
