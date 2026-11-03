"""Check the actual R/B/Y Vermilion/Route6 north-roof connection on native GPU.

Uses the normal current-border/current-body/neighbor-body draw order, imported
maps and actual main/Session adapters. Writes only private proof output.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
import validate_gpu


BODY=r"""
 report.type='native Gen1 connected north-overhang GPU validation'
 report.limits='Actual imported R/B/Y Vermilion/Route6 connection and native TileRenderer methods in normal Overworld order, plus the original native Player/SpriteRenderer Surf actor at four reachable water cells. No NPC is relocated; original NPC definitions/facing/scripts, source mechanics and import files remain unchanged.'
 report.totals={games=0,checked_pixels=0,opaque_pixels=0,transparent_pixels=0,meaningful_replayed_pixels=0,warm_frames=0}
 local Map=require('src.world.Map');local T=require('src.render.TileRenderer');local FX=require('src.render.PaletteFX')
 for _,game in ipairs({'red','blue','yellow'})do
  GV.set(game);assetGame=game;clock=0;FX.setDarkWorld(false)
  local maps,sets=generated(game,'maps'),generated(game,'tilesets')
  local def=assert(maps.VERMILION_CITY);local connection=assert(def.connections.north)
  check(connection.map=='ROUTE_6'and connection.offset==5,'Native Vermilion north connection changed')
  local neighborDef=assert(maps[connection.map]);local ox,oy=connection.offset*32,-neighborDef.height*32
  local data={maps=maps,tilesets=sets,sprites=generated(game,'sprites'),field=generated(game,'field')}
  local map=Map.new(def,sets[def.tileset]);local neighbor=Map.new(neighborDef,sets[neighborDef.tileset])
  local renderer=T.new(map,data);local neighborRenderer=T.new(neighbor,data)
  map.renderer=renderer;neighbor.renderer=neighborRenderer
  local cx,cy,vw,vh=128,-32,160,96
  local definition=tableString(def)..tableString(neighborDef)
  local mechanics=snapshot(map,1)..snapshot(neighbor,1)
  local events=eventSnapshot(map)..eventSnapshot(neighbor)
  local function draw(replay)
   return capture(vw,vh,function()
    FX.clearTrueColor();FX.setPass('world')
    renderer:drawBorderFill(cx,cy,vw,vh)
    renderer:draw(cx,cy,vw,vh)
    if replay~=false then neighborRenderer:drawMapOnly(cx-ox,cy-oy,vw,vh)
    else
     -- Independent backing image: same native neighbor body, deliberately
     -- bypassing only the new drawMapOnly replay hook in this private process.
     neighborRenderer:drawWindow(cx-ox,cy-oy,vw,vh)
    end
    FX.setPass(nil)
   end)
  end
  local before=draw();local mod=startMod(game,1)
  local art=assert(mod.exports.state:replacements(game,def.tileset,def))
  local neighborArt=assert(mod.exports.state:replacements(game,neighborDef.tileset,neighborDef))
  check(mod.exports.state.rejected==0 and art and neighborArt,'Native connected scene rejected reviewed artwork')
  local after=draw();local backing=draw(false);local expected={}
  for _,row in ipairs(mappingRows('lib/gen1_building_audit_roofs.lua'))do
   if row.game==game and row.map==def.id and row.y==-1 and row.role=='larger_center'then
    check(row.sourceY==0,'North roof source anchor is not the native first source row')
    expected[#expected+1]={row=row,image=nativeComposition(row)}
   end
  end
  check(#expected>=4,'Native clinic north-cap catalog is incomplete')
  local opaque,transparent,changed,checked=0,0,0,0
  local function verify(frame,ground)
   local n=0
   for _,item in ipairs(expected)do
    local row,image=item.row,item.image
    for y=0,15 do for x=0,15 do
     local dx,dy=row.x*16+x-cx,-16+y-cy
     local r,g,b,a=image:getPixel(x,y)
     check(a==0 or a==1,'Retained native cap alpha must be binary at1:1')
     if a==1 then equalPixel(frame,dx,dy,image,x,y,'Neighbor body erased an opaque native clinic roof pixel')
     else equalPixel(frame,dx,dy,ground,dx,dy,'Transparent native roof corners changed the real backing')end
     n=n+1
    end end
   end
   return n
  end
  checked=checked+verify(after,backing)
  for _,item in ipairs(expected)do
   for y=0,15 do for x=0,15 do
    local row,image=item.row,item.image;local _,_,_,a=image:getPixel(x,y)
    local dx,dy=row.x*16+x-cx,-16+y-cy
    if a==1 then
     opaque=opaque+1
     local ar,ag,ab=after:getPixel(dx,dy);local br,bg,bb=backing:getPixel(dx,dy)
     if math.abs(ar-br)>1/255 or math.abs(ag-bg)>1/255 or math.abs(ab-bb)>1/255 then changed=changed+1 end
    else transparent=transparent+1 end
   end end
  end
  check(opaque>0 and transparent>0,'Native cap fixture lacks opaque or transparent evidence')
  check(changed>0,'This native connection did not actually exercise the erased-cap defect')
  local oldSave=mod.save.set;mod.save.set=function()end
  mod._probeEvents:emit('mod.options_changed',{mod='tileshift',key='center_style',value=1})
  local compact=draw();check(compact:getString()~=after:getString(),'Compact clinic option did not change the native scene')
  local compactCells=mod.exports.roofs:cells(game,def)
  for _,entry in pairs(compactCells and compactCells.grid or{})do
   while entry do check(entry.role~='larger_center','Compact clinic retained the expanded north cap');entry=entry.next end
  end
  mod._probeEvents:emit('mod.options_changed',{mod='tileshift',key='center_style',value=2});mod.save.set=oldSave
  clock=0;check(draw():getString()==after:getString(),'Compact/expanded connection roundtrip changed native pixels')
  local cells=mod.exports.roofs:cells(game,def)
  local imports,accepted=importReads,mod.exports.state.accepted
  local ownReads,assetReads=0,0;local oldRead,oldPath=mod.read,mod.assets.path
  mod.read=function(self,...)ownReads=ownReads+1;return oldRead(self,...)end
  mod.assets.path=function(self,...)assetReads=assetReads+1;return oldPath(self,...)end
  for frame=1,20 do clock=frame/60;draw()end
  mod.read,mod.assets.path=oldRead,oldPath
  check(importReads==imports and ownReads==0 and assetReads==0,'Warm connected north replay reread imports/assets')
  check(mod.exports.state.accepted==accepted,'Warm connected north replay rebuilt mappings')
  check(mod.exports.roofs:cells(game,def)==cells,'Warm connected north replay rebuilt the roof grid')
  -- Now make Route6 the current native map. The clinic belongs to its
  -- southern neighbor, and a real imported Surf sprite stands behind its cap.
  -- Reload only private native classes so their path-keyed sprite caches do
  -- not accidentally reuse Red's sheet for Blue/Yellow in this one process.
  package.loaded['src.render.SpriteRenderer']=nil;package.loaded['src.world.Player']=nil
  local Player=require('src.world.Player');local Game=require('src.core.Game')
  local oldLogicStep=Game.logicStep;Game.logicStep=1
  local player=Player.new(data,0,35,'down');player.surfing=true
  -- The native lower Surf bob is the frame where the bottom opaque sprite
  -- row crosses the clinic ridge. Freeze its actual native phase, not a
  -- synthetic sprite position or enlarged actor.
  player.bobTimer=16;player.bobStep=Game.logicStep
  check(player.surfSprite~=nil,'Native imported Surf actor is unavailable')
  local rawPlayerDraw=player.draw
  local routeWorld={map=neighbor,player=player,entities={},npcs={},
   neighbors={{map=map,ox=-ox,oy=-oy}}}
  mod.exports.vegetation:bind(routeWorld)
  local routeCx,routeCy=cx-ox,cy-oy
  local function actorScene(occluded)
   return capture(vw,vh,function()
    FX.clearTrueColor();FX.setPass('world')
    neighborRenderer:drawBorderFill(routeCx,routeCy,vw,vh)
    neighborRenderer:draw(routeCx,routeCy,vw,vh)
    renderer:drawMapOnly(cx,cy,vw,vh)
    if occluded then player:draw(routeCx,routeCy)else rawPlayerDraw(player,routeCx,routeCy)end
    FX.setPass(nil)
   end)
  end
  local actorOpaque,actorClear,actorChanged,actorChecks=0,0,0,0
  local nativeActorFrame,nativeActorOnTop
  for x=0,3 do
   check(neighbor:isWaterCell(x,35),'Native surfer fixture must remain original surfable water')
   player.cellX=x;player.px=x*16
   local actorState=tableString({player.cellX,player.cellY,player.px,player.py,player.facing,player.surfing,player.moving,player.progress})
   local sprite=capture(vw,vh,function()FX.setPass('world');rawPlayerDraw(player,routeCx,routeCy);FX.setPass(nil)end)
   local onTop=actorScene(false);local covered=actorScene(true)
   for _,item in ipairs(expected)do for yy=0,15 do for xx=0,15 do
    local dx,dy=item.row.x*16+xx-cx,-16+yy-cy
    local _,_,_,a=item.image:getPixel(xx,yy);local _,_,_,sa=sprite:getPixel(dx,dy)
    if a==1 then
     equalPixel(covered,dx,dy,item.image,xx,yy,'Southern clinic roof did not cover the current Route6 Surf actor')
     if sa>0 then
      actorOpaque=actorOpaque+1
      local r,g,b=covered:getPixel(dx,dy);local rr,gg,bb=onTop:getPixel(dx,dy)
      if math.abs(r-rr)>1/255 or math.abs(g-gg)>1/255 or math.abs(b-bb)>1/255 then actorChanged=actorChanged+1 end
     end
    else
     equalPixel(covered,dx,dy,onTop,dx,dy,'Native roof transparency erased the current-map Surf actor')
     if sa>0 then actorClear=actorClear+1 end
    end
    actorChecks=actorChecks+1
   end end end
   check(actorState==tableString({player.cellX,player.cellY,player.px,player.py,player.facing,player.surfing,player.moving,player.progress}),
    'Roof actor redraw changed native player position/facing/movement state')
   if x==1 then nativeActorFrame=covered;nativeActorOnTop=onTop end
  end
  check(actorOpaque>0 and actorClear>0 and actorChanged>0,'Native Surf actor did not exercise opaque and transparent neighboring cap pixels: '..actorOpaque..'/'..actorClear..'/'..actorChanged)
  local actorImports,actorAccepted=importReads,mod.exports.state.accepted
  local actorCells=mod.exports.roofs:cells(game,def)
  ownReads,assetReads=0,0
  mod.read=function(self,...)ownReads=ownReads+1;return oldRead(self,...)end
  mod.assets.path=function(self,...)assetReads=assetReads+1;return oldPath(self,...)end
  for frame=1,20 do clock=frame/60;actorScene(true)end
  mod.read,mod.assets.path=oldRead,oldPath
  check(importReads==actorImports and ownReads==0 and assetReads==0,'Warm neighboring actor redraw reread native files')
  check(mod.exports.state.accepted==actorAccepted and mod.exports.roofs:cells(game,def)==actorCells,'Warm neighboring actor redraw rebuilt source/art grids')
  local actors={native_class='src.world.Player',native_sprite_renderer='src.render.SpriteRenderer',
   source_sprite='SPRITE_SEEL',positions={{0,35},{1,35},{2,35},{3,35}},facing='down',native_surf_bob_phase=16,
   checked_pixels=actorChecks,actor_pixels_under_opaque_cap=actorOpaque,actor_pixels_through_transparency=actorClear,
   meaningfully_covered_actor_pixels=actorChanged,warm_frames=20,warm_reads=0,warm_rebuilds=0,
   private_actor_state_unchanged=true,actors_rendered=true,
   after=encodePng(nativeActorFrame,game..'-route6-native-surfer-behind-clinic-gpu.png'),
   without_actor_replay=encodePng(nativeActorOnTop,game..'-route6-native-surfer-without-occlusion-gpu.png')}
  Game.logicStep=oldLogicStep
  check(definition==tableString(def)..tableString(neighborDef),'Connected roof changed imported map/NPC definitions')
  check(mechanics==snapshot(map,1)..snapshot(neighbor,1),'Connected roof changed original collision/grass/water')
  check(events==eventSnapshot(map)..eventSnapshot(neighbor),'Connected roof changed original NPC positions/facing/scripts/events')
  mod.exports.dispose();clock=0
  check(player.draw==rawPlayerDraw,'Cleanup did not restore the exact original native Player.draw method')
  check(draw():getString()==before:getString(),'North replay cleanup did not restore exact native connected pixels')
  report.fixtures[#report.fixtures+1]={game=game,map=def.id,neighbor=neighborDef.id,
   connection={offset_blocks=connection.offset,ox=ox,oy=oy},viewport={x=cx,y=cy,width=vw,height=vh},
   native_methods={'TileRenderer.drawBorderFill','TileRenderer.draw','TileRenderer.drawWindow','TileRenderer.drawMapOnly'},
   native_cap_cells=#expected,checked_pixels=checked,opaque_pixels=opaque,transparent_pixels=transparent,
   meaningful_replayed_pixels=changed,compact_expanded_roundtrip=true,source_collision_events_unchanged=true,
   original_npc_definitions_unchanged=true,actors_rendered=false,native_actor_proof=actors,cleanup_restored_native=true,
   warm_frames=20,warm_import_reads=0,warm_asset_reads=0,warm_mapping_rebuilds=0,warm_roof_grid_rebuilds=0,
   before=encodePng(before,game..'-vermilion-route6-original-gpu.png'),
   after=encodePng(after,game..'-vermilion-route6-expanded-gpu.png'),
   compact=encodePng(compact,game..'-vermilion-route6-compact-gpu.png'),
   without_replay=encodePng(backing,game..'-vermilion-route6-without-replay-gpu.png')}
  report.totals.games=report.totals.games+1;report.totals.checked_pixels=report.totals.checked_pixels+checked
  report.totals.opaque_pixels=report.totals.opaque_pixels+opaque;report.totals.transparent_pixels=report.totals.transparent_pixels+transparent
  report.totals.meaningful_replayed_pixels=report.totals.meaningful_replayed_pixels+changed;report.totals.warm_frames=report.totals.warm_frames+20
  report.totals.actor_checked_pixels=(report.totals.actor_checked_pixels or 0)+actorChecks
  report.totals.covered_native_actor_pixels=(report.totals.covered_native_actor_pixels or 0)+actorOpaque
  report.totals.visible_native_actor_pixels=(report.totals.visible_native_actor_pixels or 0)+actorClear
  report.totals.meaningful_actor_replay_pixels=(report.totals.meaningful_actor_replay_pixels or 0)+actorChanged
  report.totals.actor_warm_frames=(report.totals.actor_warm_frames or 0)+20
  write('progress.json',Json.encode({game=game,fixtures=#report.fixtures,checks=report.checks}))
 end
 check(#report.fixtures==3 and #report.warnings==0,'Native connected roof matrix is incomplete or warned')
 report.status='passed';write('report.json',Json.encode(report))
end
"""


def main():
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[2]/'.work/tileshift-gpu')
    args,_=parser.parse_known_args()
    source=validate_gpu.LUA
    prefix=source[:source.index(' -- Native Gen1 TileRenderer on real Red Pallet Town.')]
    suffix=source[source.index('\nfunction love.load()'):]
    validate_gpu.LUA=prefix+BODY+suffix
    validate_gpu.CONF=validate_gpu.CONF.replace('tileshift-gpu-validation','tileshift-gen1-north-validation')
    result=validate_gpu.main()
    invocation=args.output.resolve()/'invocation.json'
    if invocation.exists():
        metadata=json.loads(invocation.read_text(encoding='utf-8'))
        metadata['identity']='tileshift-gen1-north-validation'
        actor_paths=('src/world/Player.lua','src/render/SpriteRenderer.lua')
        engine=Path(metadata['engine_source'])
        metadata['native_actor_source_sha256']={name:hashlib.sha256((engine/name).read_bytes()).hexdigest() for name in actor_paths}
        payload=metadata.get('reference_payload')
        if payload:
            with zipfile.ZipFile(payload) as archive:
                matches={name:archive.read(name)==(engine/name).read_bytes() for name in actor_paths}
            metadata['native_actor_source_matches_installed_0398']=matches
            report=args.output.resolve()/'report.json'
            if report.exists():
                proof=json.loads(report.read_text(encoding='utf-8'))
                proof['native_actor_source_sha256']=metadata['native_actor_source_sha256']
                proof['native_actor_source_matches_installed_0398']=matches
                if not all(matches.values()):
                    proof['status']='failed';proof['error']='Native actor source differs from installed0.3.98';result=1
                report.write_text(json.dumps(proof,indent=2),encoding='utf-8')
        invocation.write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':raise SystemExit(main())
