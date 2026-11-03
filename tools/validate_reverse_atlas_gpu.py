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


def selection(root: Path, cache: Path, planner: Path, games: list[str], pilot: bool) -> dict:
    plan = json.loads(planner.read_text())
    inputs = validate_gpu.runtime_fingerprint(root)
    assert inputs == plan['runtime_inputs'], 'The native matrix plan belongs to a different runtime snapshot'
    rows = {}
    for name in dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]", (root / 'main.lua').read_text())):
        for row in preview.read_reviewed(root / name):
            if row['style'] != 'gen2' or row['game'] not in GAMES:
                continue
            assert row.get('map') is None, 'Native GBA atlas themes must be pair-global'
            key = row['game'], row['tileset'], row['id']
            assert key not in rows
            rows[key] = row
    manifests = {g: catalog.read_lua(cache / g / 'data/generated/gba/native/manifest.lua')['layouts'] for g in GAMES}
    witnesses = {}
    source_files = {}
    for scene in plan['scenes']:
        game, name = scene['game'], scene['map']
        spec = manifests[game][name]
        path = cache / game / 'data/generated/gba/native' / spec['file']
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == scene['layout_sha256'], 'Actual source layout changed since matrix planning'
        blob = data if data[:4] == b'SVML' else zlib.decompress(data)
        width, height, tw, th = struct.unpack_from('<HHHH', blob, 6)
        columns, lines = tw or width, th or height
        offset = 16 + blob[14] * blob[15] * 2
        for y in range(lines):
            for x in range(columns):
                at = offset + (y * width + x) * 4
                mid = struct.unpack_from('<H', blob, at)[0]
                key = game, spec['pair'], mid
                if key in rows and key not in witnesses:
                    witnesses[key] = dict(map=name, x=x, y=y, mid=mid, coll=blob[at + 2], elev=blob[at + 3])
        source_files[path.relative_to(cache).as_posix()] = hashlib.sha256(data).hexdigest()
    assert len(witnesses) == plan['used_source_keys'] == 12573, 'Used-key matrix is incomplete'
    grouped = defaultdict(list)
    for (game, pair, mid), witness in sorted(witnesses.items()):
        row = rows[game, pair, mid]
        item = dict(witness, sourceHash=row['sourceHash'])
        if row.get('compositionPixelHash'):
            item['compositionPixelHash'] = row['compositionPixelHash']
        grouped[game, pair].append(item)
    fixtures = []
    for game in games:
        pairs = [dict(pair=pair, source_map=items[0]['map'], items=items)
                 for (g, pair), items in sorted(grouped.items()) if g == game]
        if pilot:
            wanted = 'general__petalburg' if game in ('ruby', 'sapphire', 'emerald') else 'pallet_outdoor'
            pairs = [p for p in pairs if p['pair'] == wanted]
            assert pairs
        fixtures.append(dict(game=game, pairs=pairs))
    return dict(fixtures=fixtures, expected_keys=sum(len(p['items']) for f in fixtures for p in f['pairs']),
                full_planner_used_keys=len(witnesses), pilot=pilot, source_file_sha256=source_files,
                runtime_sha256=inputs['sha256'])


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
 local bytesCache,foregroundCache={},{}
 local magentaPixel=string.char(255,0,255,255)
 local function bytes(image)
  if not bytesCache[image]then bytesCache[image]=image:getString()end
  return bytesCache[image]
 end
 local function frameImage(row,over)
  local image=row
  if row.frames then image=row.frames[math.floor((clock+(row.offset or 0))/(row.period or 1))%#row.frames+1]end
  if over then return image.over end
  return image.under
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
    local image=frameImage(row,over)
    local raw=over and foregroundBytes(image)or bytes(image)
    out[#out+1]=raw:sub(yy*64+1,yy*64+64)
   end
  end end
  return table.concat(out)
 end
 local exactPixels,tolerantPixels,independentHashes,verifiedKeys=0,0,0,0
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
    if item.compositionPixelHash then
     check(hash(bytes(frameImage(row,false)))==item.compositionPixelHash,'Cached frame0 differs from independent authored compositionPixelHash: '..game..'/'..room.bank.pair..'/'..item.mid)
     independentHashes=independentHashes+1;rowHashes=rowHashes+1
    end
    verifiedKeys=verifiedKeys+1
    if row.frames then
     local count,period,offset=#row.frames,row.period,row.offset or 0
     check(period and period>0 and count>=1,'Invalid cached animation schedule')
     local key=count..'/'..string.format('%.12g',period)..'/'..string.format('%.12g',offset)
     schedules[key]={frames=count,period=period,offset=offset,bank=row.bank}
     for i=0,count-1 do
      local at=i*period-offset+.00001
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
  mod.exports.dispose()
 end
 check(verifiedKeys==selected.expected_keys,'Some actual used source keys were skipped')
 report.verified_source_keys=verifiedKeys;report.independent_composition_hashes=independentHashes
 report.byte_exact_gpu_pixels=exactPixels;report.tolerance_checked_gpu_pixels=tolerantPixels
 report.status='passed';write('report.json',Json.encode(report))
end
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    parser.add_argument('--games', nargs='+', choices=GAMES, default=list(GAMES))
    parser.add_argument('--planner', type=Path, default=Path(__file__).resolve().parents[2] / '.work/tileshift-v0320-final-reverse-matrix/report.json')
    parser.add_argument('--pilot', action='store_true')
    args, remaining = parser.parse_known_args()
    root = Path(remaining[remaining.index('--mod-root') + 1]).resolve() if '--mod-root' in remaining else Path(__file__).resolve().parents[1]
    cache = Path(remaining[remaining.index('--cache') + 1]).resolve() if '--cache' in remaining else Path(os.environ['APPDATA']) / 'pokemon-love2d'
    chosen = selection(root, cache, args.planner, args.games, args.pilot)
    if '--output' not in remaining:
        remaining.extend(['--output', str(root.parent / '.work/tileshift-reverse-atlas-gpu')])
    output = Path(remaining[remaining.index('--output') + 1]).resolve();output.mkdir(parents=True, exist_ok=True)
    base = validate_gpu.LUA
    validate_gpu.LUA = base[:base.index(' -- Native Gen1 TileRenderer on real Red Pallet Town.')] + BODY.replace('@SELECTION@', json.dumps(json.dumps(chosen, separators=(',', ':')))) + base[base.index('\nfunction love.load()'):]
    sys.argv[1:] = remaining
    with (output / 'runner-output.json').open('w', encoding='utf-8') as log, contextlib.redirect_stdout(log):
        result = validate_gpu.main()
    unchanged = all(hashlib.sha256((cache / name).read_bytes()).hexdigest() == expected for name, expected in chosen['source_file_sha256'].items())
    path = output / 'report.json'
    if path.exists():
        report = json.loads(path.read_text());report['source_layout_files_unchanged'] = unchanged
        if not unchanged:report['status'] = 'failed'
        path.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(dict(status=report['status'], verified_source_keys=report.get('verified_source_keys'),
                              independent_hashes=report.get('independent_composition_hashes'),
                              exact_pixels=report.get('byte_exact_gpu_pixels'), tolerant_pixels=report.get('tolerance_checked_gpu_pixels'),
                              error=report.get('error'), report=str(path))))
    return result if unchanged else 1


if __name__ == '__main__':
    raise SystemExit(main())
