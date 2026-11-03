"""Capture every selected R/B/Y and G/S/C area with the native GPU renderers.

This is a gallery capture, not the exhaustive per-pixel regression probe. Each
bounded batch shares one indexed mod. Source definitions, collision/events and
exact native cleanup are checked; imports and saves remain read-only.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

import validate_gpu


GAMES = ('red', 'blue', 'yellow', 'gold', 'silver', 'crystal')

BODY = r"""
 report.type='native GPU all-area forward gallery capture'
 report.limits='Actual native TileRenderer / Gen2 World frame-zero background readbacks. Source definition, collision/event snapshots and cleanup are checked. No actors, interactive playthrough, all-pixel replacement assertions or warm-frame performance claims.'
 local inventory=Json.decode(@INVENTORY@)
 local batchSize=@BATCH_SIZE@
 report.inventory=inventory;report.unrenderable={};report.batches={}
 report.totals={inventory_records=#inventory,scenes=0,unrenderable=0,source_cells=0,replaced_cells=0,remaining_cells=0,indexed_mod_starts=0}
 local Map=require('src.world.Map')
 local T=require('src.render.TileRenderer')
 local FX=require('src.render.PaletteFX')
 local World=require('src.world.gen2.World')
 local Map2=require('src.world.gen2.Map')
 local Palettes=require('src.world.gen2.Palettes')
 FX.mode='og';FX.setDarkWorld(false)
 -- Restore graphics state even when an incomplete, unused native beta map
 -- cannot bake. Never repair or manufacture source pixels to hide that error.
 capture=function(width,height,draw)
  local canvas=G.newCanvas(width,height,{dpiscale=1,format='rgba8'})
  canvas:setFilter('nearest','nearest')
  G.push('all');G.setCanvas(canvas);G.origin();G.setScissor();G.setShader()
  G.clear(0,0,0,0);G.setColor(1,1,1,1)
  local ok,err=xpcall(draw,debug.traceback)
  G.pop()
  if not ok then canvas:release();error(err,0)end
  local out=canvas:newImageData();canvas:release();return out
 end
 local function png(image,path)
  local ref=encodePng(image,path);ref.png_sha256=hash(assert(read(ref.path)))
  return ref
 end
 local function sceneKey(scene)return scene.game..'/'..scene.map end
 local function progress(phase,scene)
  write('progress.json',Json.encode({phase=phase,game=scene.game,map=scene.map,
   fixtures=#report.fixtures,unrenderable=#report.unrenderable,checks=report.checks,indexed_mod_starts=report.totals.indexed_mod_starts}))
 end
 for _,game in ipairs({'red','blue','yellow','gold','silver','crystal'})do
  local scenes={};for _,scene in ipairs(inventory)do if scene.game==game then scenes[#scenes+1]=scene end end
  if #scenes>0 then
   GV.set(game);assetGame=game;clock=0;FX.setDarkWorld(false)
   -- Decode each imported table once per game, not once per map.
   local maps,sets=generated(game,'maps'),generated(game,'tilesets')
   local generation=({red=1,blue=1,yellow=1})[game]or 2
   local palettes,roofs
   if generation==2 then palettes,roofs=generated(game,'palettes'),generated(game,'roofs')end
   local sourceTables=hash(tableString(maps)..tableString(sets))
   local function context(scene,mod)
    local def=assert(maps[scene.map],'Missing gallery source '..sceneKey(scene))
    check(def.width*32==scene.width and def.height*32==scene.height,'Gallery source dimensions changed: '..sceneKey(scene))
    check(#def.blocks==def.width*def.height,'Incomplete gallery source block array: '..sceneKey(scene))
    if generation==1 then
     local map=Map.new(def,assert(sets[def.tileset]));local renderer=T.new(map,{maps=maps,tilesets=sets});map.renderer=renderer
     return map,def,function()
      return capture(scene.width,scene.height,function()
       FX.clearTrueColor();FX.setPass('world')
       local ok,err=pcall(renderer.drawWindow,renderer,0,0,scene.width,scene.height)
       FX.setPass(nil);if not ok then error(err,0)end
      end)
     end,nil,'Original monochrome; lit background preview'
    end
    local map=Map2.new(def,assert(sets[def.tileset]))
    local daytime=Palettes.daytimeFor(def,12,true)
    check(daytime~='DARK','Gallery must use the native Flash-lit palette')
    local world=setmetatable({game={save={version=game,options={}},options={}},maps=maps,tilesets=sets,
     palettes=palettes,roofs=roofs,atlasCache={},mapImages={},animCells={},bgSets={},blockEdits={},
     daytime=daytime,flashUsed=true,clockHour=12,flickerPhase=1,camera={x=0,y=0},animClock=0,animTimer=0,
     neighbors={},map=map,viewW=scene.width,viewH=scene.height},{__index=World})
    if mod then mod.game.world=world end
    return map,def,function()
     return capture(scene.width,scene.height,function()
      world.mapImage=world:imageFor(map.id)
      G.draw(assert(world.mapImage,'Native map image missing'),0,0)
      world:drawAnimCells(map.id,0,0,1)
     end)
    end,world,daytime
   end
   for first=1,#scenes,batchSize do
    local last=math.min(#scenes,first+batchSize-1)
    local originals={};local batch={game=game,first=first,last=last,scenes=0,unrenderable=0}
    -- Capture native originals before installing this batch's single mod.
    for index=first,last do
     local scene=scenes[index];clock=0;progress('native',scene)
     local map,def,draw,world,daytime=context(scene)
     local mechanics,events,definition=snapshot(map,generation),eventSnapshot(map),hash(tableString(def))
     local ok,image=pcall(draw)
     check(snapshot(map,generation)==mechanics and eventSnapshot(map)==events and hash(tableString(def))==definition,
      'Native gallery render changed source mechanics: '..sceneKey(scene))
     if not ok then
      check(scene.incomplete_import_native_retained==true and scene.map=='SAFARI_ZONE_BETA'and(game=='gold'or game=='silver'),
       'Playable source gallery failed: '..sceneKey(scene)..': '..tostring(image))
      report.unrenderable[#report.unrenderable+1]={game=game,map=scene.map,width=scene.width,height=scene.height,
       status='unrenderable',unused_beta=true,incomplete_import_native_retained=true,native_art_retained=true,
       reason=tostring(image),source_definition_unchanged=true,source_collision_events_unchanged=true,actors_rendered=false}
      batch.unrenderable=batch.unrenderable+1
     else
      originals[index]={scene=scene,mechanics=mechanics,events=events,definition=definition,daytime=daytime,
       before=png(image,game..'-'..scene.map..'-native-gpu.png')}
      image:release()
     end
     collectgarbage('step',128)
    end
    local mod=startMod(game,generation);report.totals.indexed_mod_starts=report.totals.indexed_mod_starts+1
    for index=first,last do
     local original=originals[index]
     if original then
      local scene=original.scene;clock=0;progress('gen3',scene)
      local map,def,draw=context(scene,mod)
      local art=assert(mod.exports.state:replacements(game,def.tileset,def))
      check(mod.exports.state.rejected==0,'Gallery source/donor row rejected: '..sceneKey(scene))
      local c=coverage(def,art)
      if not scene.incomplete_import_native_retained then
       check(c.preserved_native_occurrences==0,'Playable gallery map retains unmapped cells: '..sceneKey(scene))
      end
      local image=draw();local after=png(image,game..'-'..scene.map..'-gen3-gpu.png');image:release()
      check(snapshot(map,generation)==original.mechanics and eventSnapshot(map)==original.events
       and hash(tableString(def))==original.definition,'Gen3 gallery changed source mechanics: '..sceneKey(scene))
      local notes={}
      if scene.incomplete_import_native_retained then notes[#notes+1]='Unused Safari beta; incomplete imported graphics; native art intentionally retained.'end
      if generation==1 then notes[#notes+1]='Original four-shade monochrome. Lit background preview; no darkness mask.'
      else notes[#notes+1]='Native '..original.daytime..' palette at noon; Flash-lit context for dark maps.'end
      local fixture={game=game,map=scene.map,source_daytime=generation==2 and original.daytime or nil,
       coverage=c,before=original.before,after=after,source_definition_sha256=original.definition,
       source_mechanics_sha256=original.mechanics,source_events_sha256=original.events,
       source_definition_unchanged=true,source_collision_events_unchanged=true,actors_rendered=false,
       native_renderer=generation==1 and'src.render.TileRenderer:drawWindow'or'src.world.gen2.World:imageFor + drawAnimCells',
       unused_beta=scene.unused_beta,incomplete_import_native_retained=scene.incomplete_import_native_retained,notes=notes}
      originals[index].fixture=fixture;report.fixtures[#report.fixtures+1]=fixture;batch.scenes=batch.scenes+1
      report.totals.scenes=report.totals.scenes+1;report.totals.source_cells=report.totals.source_cells+c.visible_cells
      report.totals.replaced_cells=report.totals.replaced_cells+c.replaced_occurrences
      report.totals.remaining_cells=report.totals.remaining_cells+c.preserved_native_occurrences
      collectgarbage('step',128)
     end
    end
    check(mod.exports.state.rejected==0,'Gallery rejected a reviewed mapping')
    mod.game.world=nil;mod.exports.dispose();mod=nil;clock=0;collectgarbage('collect')
    -- A fresh native context after disposal must reproduce every original.
    for index=first,last do
     local original=originals[index]
     if original then
      local scene=original.scene;progress('cleanup',scene)
      local map,def,draw=context(scene);local image=draw()
      check(hash(image:getString())==original.before.rgba_sha256,'Gallery cleanup changed original pixels: '..sceneKey(scene));image:release()
      check(snapshot(map,generation)==original.mechanics and eventSnapshot(map)==original.events
       and hash(tableString(def))==original.definition,'Gallery cleanup changed mechanics: '..sceneKey(scene))
      original.fixture.cleanup_restored_native=true
     end
     collectgarbage('step',128)
    end
    report.batches[#report.batches+1]=batch
    check(hash(tableString(maps)..tableString(sets))==sourceTables,'Gallery modified imported map/tileset definitions: '..game)
    -- Only fully cleaned-up batches enter this recovery file. The final
    -- launcher or --verify-checkpoint independently checks runtime bytes.
    report.checkpoint=true;report.checkpoint_complete_fixtures=#report.fixtures
    write('checkpoint-report.json',Json.encode(report))
   end
  end
 end
 report.totals.unrenderable=#report.unrenderable
 check(#report.fixtures+#report.unrenderable==#inventory,'Gallery inventory incomplete')
 check(#report.warnings==0,'Gallery reported source/asset warnings')
 report.checkpoint=nil;report.status='passed';report.capture_status='native readbacks, source snapshots and exact cleanup passed'
 write('report.json',Json.encode(report))
end
"""


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--games', help='Optional comma-separated game IDs')
    parser.add_argument('--limit-per-game', type=int, help='Small native pilot only')
    parser.add_argument('--batch-size', type=int, default=64)
    parser.add_argument('--resume-report', type=Path, help='Skip only fully cleaned-up scenes from a checked completed-batch report; aggregate both reports when building the gallery')
    parser.add_argument('--verify-checkpoint', type=Path, help='Verify and seal a recovery report, then exit without starting a native process')
    parser.add_argument('--verified-output', type=Path, help='Destination for the sealed completed-batch report')
    args, remaining = parser.parse_known_args()
    sys.argv[1:] = remaining
    completed = set()
    if args.resume_report or args.verify_checkpoint:
        path = args.verify_checkpoint or args.resume_report
        recovery = json.loads(path.read_text(encoding='utf-8'))
        assert recovery['type'] == 'native GPU all-area forward gallery capture'
        assert recovery['runtime_inputs'] == validate_gpu.runtime_fingerprint(Path(__file__).resolve().parents[1])
        assert recovery['status'] == 'passed' or recovery.get('checkpoint') is True
        assert not recovery['warnings']
        for fixture in recovery['fixtures']:
            assert all(fixture.get(k) is True for k in ('cleanup_restored_native', 'source_definition_unchanged', 'source_collision_events_unchanged'))
            for ref in (fixture['before'], fixture['after']):
                assert hashlib.sha256(Path(ref['path']).read_bytes()).hexdigest() == ref['png_sha256']
            key = fixture['game'], fixture['map']
            assert key not in completed
            completed.add(key)
        for failure in recovery.get('unrenderable', []):
            key = failure['game'], failure['map']
            assert key in {('gold', 'SAFARI_ZONE_BETA'), ('silver', 'SAFARI_ZONE_BETA')}
            assert failure['source_definition_unchanged'] and failure['source_collision_events_unchanged']
            assert key not in completed
            completed.add(key)
        assert completed
        if args.verify_checkpoint:
            assert args.verified_output and args.verified_output.resolve() != path.resolve()
            recovery.update(status='passed', runtime_inputs_unchanged_during_probe=True,
                            capture_status='Completed batches: native readbacks, source snapshots, exact cleanup and external runtime fingerprint verified',
                            checkpoint_source_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            recovery['inventory'] = [s for s in recovery['inventory'] if (s['game'], s['map']) in completed]
            recovery['totals']['inventory_records'] = len(completed)
            args.verified_output.parent.mkdir(parents=True, exist_ok=True)
            args.verified_output.write_text(json.dumps(recovery, indent=2) + '\n', encoding='utf-8')
            print(json.dumps({'verified_scenes': len(completed), 'output': str(args.verified_output)}))
            return 0
    document = json.loads(args.inventory.read_text(encoding='utf-8'))
    scenes = document['scenes'] if isinstance(document, dict) else document
    selected_games = set(args.games.split(',')) if args.games else set(GAMES)
    assert selected_games and selected_games <= set(GAMES)
    assert 1 <= args.batch_size <= 128
    counts = Counter()
    selected = []
    for scene in scenes:
        game, name = scene['game'], scene['map']
        assert game in GAMES and re.fullmatch('[A-Z][A-Z0-9_]*', name)
        assert scene['width'] > 0 and scene['height'] > 0
        if game not in selected_games:
            continue
        if (game, name) in completed:
            continue
        if args.limit_per_game is not None and counts[game] >= args.limit_per_game:
            continue
        counts[game] += 1
        selected.append(scene)
    assert selected and len({(s['game'], s['map']) for s in selected}) == len(selected)
    source = validate_gpu.LUA
    prefix = source[:source.index(' local function requireCompletePallet')]
    suffix = source[source.index('\nfunction love.load()'):]
    validate_gpu.LUA = prefix + BODY.replace('@INVENTORY@', json.dumps(json.dumps(selected))).replace(
        '@BATCH_SIZE@', str(args.batch_size)) + suffix
    return validate_gpu.main()


if __name__ == '__main__':
    raise SystemExit(main())
