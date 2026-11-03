"""Run the complete Gen1 native pixel regression with a shared batch index.

Retains the original validator's every-pixel, two-frame, Center option, source
mechanics, warm-cache and exact-cleanup checks. Only capture/index lifetime is
batched: native originals, one indexed mod, then native cleanup for each batch.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

import validate_gpu
from validate_gen1_maps_gpu import BODY as ORIGINAL_BODY


RUN = r"""
 report.type='native Gen1 complete-map Gen3 art batched GPU validation'
 report.totals.indexed_mod_starts=0;report.batches={}
 local batchSize=@BATCH_SIZE@
 -- Readbacks own their bytes after the temporary canvas is released.
 capture=function(width,height,draw)
  local canvas=G.newCanvas(width,height,{dpiscale=1,format='rgba8'});canvas:setFilter('nearest','nearest')
  G.push('all');G.setCanvas(canvas);G.origin();G.setScissor();G.setShader()
  G.clear(0,0,0,0);G.setColor(1,1,1,1)
  local ok,err=xpcall(draw,debug.traceback);G.pop()
  if not ok then canvas:release();error(err,0)end
  local image=canvas:newImageData();canvas:release();return image
 end
 local function progress(phase,game,id)
  write('progress.json',Json.encode({phase=phase,fixtures=#report.fixtures,checks=report.checks,game=game,map=id,
   indexed_mod_starts=report.totals.indexed_mod_starts}))
 end
 for _,game in ipairs({'red','blue','yellow'})do
  local scenes={};for _,scene in ipairs(selected)do if scene.game==game then scenes[#scenes+1]=scene end end
  if #scenes>0 then
   GV.set(game);assetGame=game;clock=0;FX.setDarkWorld(false)
   local maps,sets=generated(game,'maps'),generated(game,'tilesets')
   local function context(id)
    local def=assert(maps[id],'Missing selected native map: '..game..'/'..id)
    local map=Map.new(def,sets[def.tileset]);local renderer=T.new(map,{maps=maps,tilesets=sets});map.renderer=renderer
    local function draw()
     return capture(def.width*32,def.height*32,function()
      FX.clearTrueColor();FX.setPass('world')
      local ok,err=pcall(renderer.drawWindow,renderer,0,0,def.width*32,def.height*32)
      FX.setPass(nil);if not ok then error(err,0)end
     end)
    end
    return map,def,draw
   end
   for first=1,#scenes,batchSize do
    local last=math.min(#scenes,first+batchSize-1);local originals={}
    for i=first,last do
     local id=scenes[i].map;clock=0;progress('native',game,id)
     local map,def,draw=context(id);local before=draw()
     originals[i]={mechanics=snapshot(map,1),events=eventSnapshot(map),definition=tableString(def),
      before=encodePng(before,game..'-'..id..'-native-gpu.png')}
     before:release();collectgarbage('step',128)
    end
    local mod=startMod(game,1);report.totals.indexed_mod_starts=report.totals.indexed_mod_starts+1
    for i=first,last do
     local id=scenes[i].map;local original=originals[i];clock=0;progress('gen3',game,id)
     local map,def,draw=context(id)
     local art=assert(mod.exports.state:replacements(game,def.tileset,def))
     check(mod.exports.state.rejected==0,'Gen1 reviewed source/donor row rejected: '..game..'/'..id)
     local c=coverage(def,art)
     check(c.preserved_native_occurrences==0,'Complete Gen1 scene retains unmapped cells: '..game..'/'..id)
     local after=draw();check(hash(after:getString())~=original.before.rgba_sha256,'Gen1 scene has no visible Gen3 change: '..game..'/'..id)
     local pixels=verifyCoveredPixels(def,art,after,game..'/'..id)
     local centers=checkCenters(mod,game,def,draw,after,map)
     clock=17/60;local animated=draw()
     pixels=pixels+verifyCoveredPixels(def,art,animated,game..'/'..id..' animation');animated:release()
     local reads,accepted=importReads,mod.exports.state.accepted;local ownReads,assetReads=0,0
     local oldRead,oldPath=mod.read,mod.assets.path
     mod.read=function(self,...)ownReads=ownReads+1;return oldRead(self,...)end
     mod.assets.path=function(self,...)assetReads=assetReads+1;return oldPath(self,...)end
     for frame=1,12 do clock=frame/60;local warm=draw();warm:release()end
     mod.read,mod.assets.path=oldRead,oldPath
     check(importReads==reads and ownReads==0 and assetReads==0,'Warm Gen1 rendering reread files')
     check(mod.exports.state.accepted==accepted,'Warm Gen1 rendering rebuilt mappings')
     check(snapshot(map,1)==original.mechanics and eventSnapshot(map)==original.events and tableString(def)==original.definition,
      'Gen1 artwork changed source definitions/mechanics')
     local fixture={game=game,map=id,coverage=c,native_renderer='src.render.TileRenderer:drawWindow',
      checked_gpu_pixels=pixels,source_definition_unchanged=true,source_collision_events_unchanged=true,
      warm_frames=12,warm_import_reads=0,warm_asset_reads=0,warm_mapping_rebuilds=0,center_styles=centers,
      before=original.before,after=encodePng(after,game..'-'..id..'-gen3-gpu.png')}
     after:release();original.fixture=fixture;report.fixtures[#report.fixtures+1]=fixture
     report.totals.scenes=report.totals.scenes+1;report.totals.source_cells=report.totals.source_cells+c.visible_cells
     report.totals.replaced_cells=report.totals.replaced_cells+c.replaced_occurrences
     report.totals.remaining_cells=report.totals.remaining_cells+c.preserved_native_occurrences
     report.totals.checked_pixels=report.totals.checked_pixels+pixels;report.totals.warm_frames=report.totals.warm_frames+12
     collectgarbage('step',128)
    end
    mod.exports.dispose();mod=nil;clock=0;collectgarbage('collect')
    for i=first,last do
     local id=scenes[i].map;local original=originals[i];progress('cleanup',game,id)
     local map,def,draw=context(id);local native=draw()
     check(hash(native:getString())==original.before.rgba_sha256,'Gen1 cleanup failed to restore original native pixels');native:release()
     check(snapshot(map,1)==original.mechanics and eventSnapshot(map)==original.events and tableString(def)==original.definition,
      'Gen1 cleanup changed source definitions/mechanics')
     original.fixture.cleanup_restored_native=true;collectgarbage('step',128)
    end
    report.batches[#report.batches+1]={game=game,first=first,last=last,scenes=last-first+1}
    write('checkpoint-report.json',Json.encode(report))
   end
  end
 end
 check(#report.fixtures==#selected and #report.warnings==0,'Gen1 scene matrix incomplete or source warnings occurred')
 report.status='passed';write('report.json',Json.encode(report))
end
"""


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--scenes-json', type=Path, required=True)
    parser.add_argument('--batch-size', type=int, default=64)
    args, remaining = parser.parse_known_args()
    sys.argv[1:] = remaining
    scenes = json.loads(args.scenes_json.read_text(encoding='utf-8'))
    assert scenes and len({(s['game'], s['map']) for s in scenes}) == len(scenes)
    assert all(s['game'] in ('red', 'blue', 'yellow') and re.fullmatch('[A-Z][A-Z0-9_]*', s['map']) for s in scenes)
    assert 1 <= args.batch_size <= 128
    header = ORIGINAL_BODY[:ORIGINAL_BODY.index(' for _,scene in ipairs(selected)do')]
    body = (header + RUN).replace('@SELECTION@', json.dumps(json.dumps(scenes))).replace('@BATCH_SIZE@', str(args.batch_size))
    source = validate_gpu.LUA
    prefix = source[:source.index(' -- Native Gen1 TileRenderer on real Red Pallet Town.')]
    suffix = source[source.index('\nfunction love.load()'):]
    validate_gpu.LUA = prefix + body + suffix
    return validate_gpu.main()


if __name__ == '__main__':
    raise SystemExit(main())
