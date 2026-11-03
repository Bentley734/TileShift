"""Validate selected complete R/B/Y maps in the actual native TileRenderer.

Checks two animation frames, every visible pixel, untouched source mechanics,
warm render caching, compact/expanded Center facades and exact cleanup.
"""
import argparse
import json
from pathlib import Path
import re
import sys
import validate_gpu

BODY=r"""
 report.type='native Gen1 complete-map Gen3 art GPU validation'
 report.limits='Actual imported R/B/Y maps, native TileRenderer and main/Session adapters. Source mechanics and exact visible pixels are checked after native darkness gates permit replacement; no interactive playthrough or save writes.'
 local selected=Json.decode(@SELECTION@)
 report.selection=selected;report.totals={scenes=0,source_cells=0,replaced_cells=0,remaining_cells=0,checked_pixels=0,warm_frames=0}
 local Map=require('src.world.Map')
 local T=require('src.render.TileRenderer')
 local FX=require('src.render.PaletteFX')
 local centerRows={}
 for path in assert(read(MOD..'/main.lua')):gmatch("'([^']+%.lua)'")do
  if path:match('^mappings/')then
   for _,row in ipairs(mappingRows(path))do
    if row.buildingCompact and row.role=='larger_center'then
     local k=row.game..':'..row.map;centerRows[k]=centerRows[k]or{};centerRows[k][#centerRows[k]+1]=row
    end
   end
  end
 end
 local function checkCenters(mod,game,def,draw,expanded,map)
  local rows=centerRows[game..':'..def.id]
  if not rows then return nil end
  local checked=0;local before,events=snapshot(map,1),eventSnapshot(map)
  for _,row in ipairs(rows)do
   local expected=nativeComposition(row)
   for y=0,15 do for x=0,15 do
    equalPixel(expanded,row.x*16+x,row.y*16+y,expected,x,y,'Expanded Gen1 Center artwork differs');checked=checked+1
   end end
  end
  local save=mod.save.set;mod.save.set=function()end
  mod._probeEvents:emit('mod.options_changed',{mod='tileshift',key='center_style',value=1})
  local compact=draw()
  for _,row in ipairs(rows)do
   local expected=nativeComposition(row.buildingCompact)
   for y=0,15 do for x=0,15 do
    equalPixel(compact,row.x*16+x,row.y*16+y,expected,x,y,'Compact Gen1 Center artwork differs');checked=checked+1
   end end
  end
  local decorations=mod.exports.roofs:cells(game,def)
  for _,cell in pairs(decorations and decorations.grid or{})do
   while cell do check(cell.role~='larger_center','Compact Gen1 Center retained expanded decoration');cell=cell.next end
  end
  mod._probeEvents:emit('mod.options_changed',{mod='tileshift',key='center_style',value=2});mod.save.set=save
  check(draw():getString()==expanded:getString(),'Gen1 Center style roundtrip changed unrelated pixels')
  check(snapshot(map,1)==before and eventSnapshot(map)==events,'Center style changed Gen1 mechanics')
  return {checked_pixels=checked,compact_and_expanded=true,round_trip_identical=true,compact_hides_expanded_decorations=true,
   compact=encodePng(compact,game..'-'..def.id..'-compact-centers-gpu.png')}
 end
 for _,scene in ipairs(selected)do
  local game,id=scene.game,scene.map
  GV.set(game);assetGame=game;clock=0;FX.setDarkWorld(false)
  local maps,sets=generated(game,'maps'),generated(game,'tilesets')
  local def=assert(maps[id],'Missing selected native map: '..game..'/'..id)
  local definition=tableString(def)
  local map=Map.new(def,sets[def.tileset]);local renderer=T.new(map,{maps=maps,tilesets=sets});map.renderer=renderer
  local function draw()
   return capture(def.width*32,def.height*32,function()
    FX.clearTrueColor();FX.setPass('world');renderer:drawWindow(0,0,def.width*32,def.height*32);FX.setPass(nil)
   end)
  end
  local before=draw();local mechanics,events=snapshot(map,1),eventSnapshot(map)
  local mod=startMod(game,1)
  local art=assert(mod.exports.state:replacements(game,def.tileset,def))
  check(mod.exports.state.rejected==0,'Gen1 reviewed source/donor row rejected: '..game..'/'..id)
  local c=coverage(def,art)
  check(c.preserved_native_occurrences==0,'Complete Gen1 scene retains unmapped cells: '..game..'/'..id)
  local after=draw();check(after:getString()~=before:getString(),'Gen1 scene has no visible Gen3 change: '..game..'/'..id)
  local pixels=verifyCoveredPixels(def,art,after,game..'/'..id)
  local centers=checkCenters(mod,game,def,draw,after,map)
  clock=17/60;pixels=pixels+verifyCoveredPixels(def,art,draw(),game..'/'..id..' animation')
  local reads,accepted=importReads,mod.exports.state.accepted;local ownReads,assetReads=0,0
  local oldRead,oldPath=mod.read,mod.assets.path
  mod.read=function(self,...)ownReads=ownReads+1;return oldRead(self,...)end
  mod.assets.path=function(self,...)assetReads=assetReads+1;return oldPath(self,...)end
  for frame=1,12 do clock=frame/60;draw()end
  mod.read,mod.assets.path=oldRead,oldPath
  check(importReads==reads and ownReads==0 and assetReads==0,'Warm Gen1 rendering reread files')
  check(mod.exports.state.accepted==accepted,'Warm Gen1 rendering rebuilt mappings')
  check(snapshot(map,1)==mechanics and eventSnapshot(map)==events and tableString(def)==definition,'Gen1 artwork changed source definitions/mechanics')
  mod.exports.dispose();clock=0
  check(draw():getString()==before:getString(),'Gen1 cleanup failed to restore original native pixels')
  report.fixtures[#report.fixtures+1]={game=game,map=id,coverage=c,native_renderer='src.render.TileRenderer:drawWindow',
   checked_gpu_pixels=pixels,source_definition_unchanged=true,source_collision_events_unchanged=true,
   warm_frames=12,warm_import_reads=0,warm_asset_reads=0,warm_mapping_rebuilds=0,cleanup_restored_native=true,center_styles=centers,
   before=encodePng(before,game..'-'..id..'-native-gpu.png'),after=encodePng(after,game..'-'..id..'-gen3-gpu.png')}
  report.totals.scenes=report.totals.scenes+1;report.totals.source_cells=report.totals.source_cells+c.visible_cells
  report.totals.replaced_cells=report.totals.replaced_cells+c.replaced_occurrences
  report.totals.remaining_cells=report.totals.remaining_cells+c.preserved_native_occurrences
  report.totals.checked_pixels=report.totals.checked_pixels+pixels;report.totals.warm_frames=report.totals.warm_frames+12
  write('progress.json',Json.encode({fixtures=#report.fixtures,checks=report.checks,game=game,map=id}))
 end
 check(#report.fixtures==#selected and #report.warnings==0,'Gen1 scene matrix incomplete or source warnings occurred')
 report.status='passed';write('report.json',Json.encode(report))
end
"""


def main():
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--scenes-json',type=Path,required=True)
    args,remaining=parser.parse_known_args();sys.argv[1:]=remaining
    scenes=json.loads(args.scenes_json.read_text())
    assert scenes and all(s['game']in('red','blue','yellow')and re.fullmatch(r'[A-Z][A-Z0-9_]*',s['map'])for s in scenes)
    source=validate_gpu.LUA
    prefix=source[:source.index(' -- Native Gen1 TileRenderer on real Red Pallet Town.')]
    suffix=source[source.index('\nfunction love.load()'):]
    validate_gpu.LUA=prefix+BODY.replace('@SELECTION@',json.dumps(json.dumps(scenes)))+suffix
    return validate_gpu.main()


if __name__=='__main__':raise SystemExit(main())
