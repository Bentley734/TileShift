"""Validate TileShift with native LÃ–VE GPU renderers in a private probe process.

The launcher, installed mods and game saves are never changed. Imported cache
files are read only. The probe uses its own identity and writes PNG readbacks
and diagnostics only below --output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile


CONF = r"""function love.conf(t)
 t.identity='tileshift-gpu-validation'
 t.console=false;t.gammacorrect=false
 t.window.title='TileShift private GPU validation'
 t.window.width=400;t.window.height=320;t.window.visible=false;t.window.vsync=0
 t.modules.audio=false;t.modules.joystick=false;t.modules.physics=false;t.modules.video=false
end
"""

LUA = r"""
local CACHE,MOD,OUT=@CACHE@,@MOD@,@OUT@
local G=love.graphics
local report={status='running',theme='gen3',checks=0,fixtures={},interactions={},lighting={},warnings={},writes='private probe output only',
 limits='Native TileRenderer and Gen2 World background GPU methods plus a synthetic actor rectangle; no full gameplay or UI automation.',
 gpu_pixel_tolerance_bytes=1}
local function read(path)
 local f=io.open(path,'rb');if not f then return nil end
 local bytes=f:read('*a');f:close();return bytes
end
local function write(path,bytes)
 local f=assert(io.open(OUT..'/'..path,'wb'));f:write(bytes);f:close()
end
function love.errhand(message)
 write('error.txt',tostring(message));love.event.quit(1)
 return function()return 1 end
end
local function check(ok,message)
 report.checks=report.checks+1
 assert(ok,message)
end
local function hash(bytes)return love.data.encode('string','hex',love.data.hash('sha256',bytes))end
local function encodePng(image,path)
 local file=image:encode('png');write(path,file:getString())
 return {path=OUT..'/'..path,width=image:getWidth(),height=image:getHeight(),rgba_sha256=hash(image:getString())}
end
local function tableString(value)
 if type(value)~='table' then return tostring(value) end
 local keys={};for key in pairs(value)do keys[#keys+1]=key end
 table.sort(keys,function(a,b)return tostring(a)<tostring(b)end)
 local out={'{'};for _,key in ipairs(keys)do out[#out+1]=tostring(key)..'='..tableString(value[key])..';'end
 out[#out+1]='}';return table.concat(out)
end
local function run()
 G.setDefaultFilter('nearest','nearest')
 report.renderer={G.getRendererInfo()}
 local Json=require('src.link.Json')
 report.runtime_inputs=Json.decode(@RUNTIME_INPUT@)
 local Blob=require('src.import.CacheBlob')
 local GV=require('src.core.GameVersion')
 local Serializer=require('src.core.SaveSerializer')
 local CacheFs=require('src.import.CacheFs')
 local nativeData=love.image.newImageData
 local assetGame='red'
 local importReads=0
 local function cacheRead(relative)
  importReads=importReads+1
  assert(not relative:find('..',1,true) and relative:sub(1,1)~='/' and not relative:find(':',1,true),'invalid private import path')
  return Blob.decode(relative,read(CACHE..'/'..relative))
 end
 -- These changes affect this dedicated process only; no cache mount is changed.
 CacheFs.readAt=cacheRead
 local function fileData(relative)
  local bytes=cacheRead(relative)
  return bytes and love.filesystem.newFileData(bytes,relative:match('[^/]+$'))
 end
 local function generatedPath(path)
  if type(path)~='string' then return nil end
  if path:sub(1,17)=='assets/generated/' then return assetGame..'/'..path end
  local game,rest=path:match('^([%w_]+)/(.+)$')
  if game and GV.VERSIONS[game] and rest:sub(1,17)=='assets/generated/' then return path end
 end
 love.image.newImageData=function(first,...)
  local relative=generatedPath(first)
  if relative then return nativeData(assert(fileData(relative),'missing import image '..relative)) end
  return nativeData(first,...)
 end
 local Assets=require('src.render.Assets')
 local imageCache={}
 Assets.imageData=function(path)
  local relative=generatedPath(path)
  if relative then return nativeData(assert(fileData(relative),'missing import image '..relative)) end
  return nativeData(path)
 end
 Assets.image=function(path)
  local relative=generatedPath(path)
  if not relative then return G.newImage(path) end
  if not imageCache[relative]then
   imageCache[relative]=G.newImage(Assets.imageData(path));imageCache[relative]:setFilter('nearest','nearest')
  end
  return imageCache[relative]
 end
 Assets.exists=function(path)
  local relative=generatedPath(path)
  return relative and cacheRead(relative)~=nil or love.filesystem.getInfo(path)~=nil
 end
 local function generated(game,name)
  local bytes=assert(cacheRead(game..'/data/generated/'..name..'.lua'))
  return assert(Serializer.decode(bytes,{allowArray=true,allowComments=true,maxBytes=16*1024*1024,
   maxDepth=64,maxNodes=2000000,maxStringBytes=8*1024*1024,maxTableEntries=500000}))
 end
 local Runtime=require('src.mods.Runtime')
 local Hooks=require('src.mods.Hooks')
 local Events=require('src.mods.Events')
 local clock=0
 love.timer.getTime=function()return clock end
 local function startMod(game,generation,world)
  GV.set(game);assetGame=game
  local hooks,events=Hooks.new(),Events.new();Runtime.install(events,hooks,{})
  local mod={id='tileshift',generation=generation,exports={},game={world=world},
   options={define=function()end,get=function(_,key)return key=='style' and 2 or (key:match('^speed_') and 3 or 1) end},
   save={get=function()end,set=function()error('unexpected persistence write')end},
   log={warn=function(_,fmt,s)report.warnings[#report.warnings+1]=s or fmt end},
   assets={path=function(_,path)return love.filesystem.newFileData(assert(read(MOD..'/'..path)),path:match('[^/]+$'))end},
   hooks={wrap=function(_,name,fn,priority)return hooks:wrap(name,fn,priority,'tileshift')end},
   events={on=function(_,name,fn,priority)return events:on(name,fn,priority,'tileshift')end}}
  function mod:read(path)return read(MOD..'/'..path)end
  assert(load(assert(mod:read('main.lua')),'@TileShift/main.lua'))()(mod)
  check(mod.exports.state.style=='gen3','GPU probe requires the canonical pooled Gen3 theme')
  return mod
 end
 local function capture(width,height,draw)
  local canvas=G.newCanvas(width,height,{dpiscale=1,format='rgba8'})
  canvas:setFilter('nearest','nearest')
  G.push('all');G.setCanvas(canvas);G.origin();G.setScissor();G.setShader()
  G.clear(0,0,0,0);G.setColor(1,1,1,1)
  draw()
  G.pop()
  return canvas:newImageData()
 end
 local function equalPixel(actual,ax,ay,expected,ex,ey,message)
  local ar,ag,ab,aa=actual:getPixel(ax,ay)
  local er,eg,eb,ea=expected:getPixel(ex,ey)
  check(math.abs(ar-er)<=1/255+.00001 and math.abs(ag-eg)<=1/255+.00001
   and math.abs(ab-eb)<=1/255+.00001 and math.abs(aa-ea)<=1/255+.00001,
   message..' at '..ax..','..ay..' expected '..er..','..eg..','..eb..','..ea
    ..' actual '..ar..','..ag..','..ab..','..aa)
 end
 local function findCell(def,id,q)
  for by=0,def.height-1 do for bx=0,def.width-1 do
   if def.blocks[by*def.width+bx+1]==id then return bx*32+(q%2)*16,by*32+math.floor(q/2)*16 end
  end end
 end
 local function artAt(art,id,bx,by)
  local block=art[id]
  return block and block.positions and block.positions[bx..':'..by] or block
 end
 local function coverage(def,art)
  local replaced,unique=0,{}
  for index,id in ipairs(def.blocks)do
   local bx,by=(index-1)%def.width,math.floor((index-1)/def.width)
   local block=artAt(art,id,bx,by)
   for q=0,3 do
    if block and (not block.coverage or block.coverage[q])then
     replaced=replaced+1;unique[id..':'..q..(block~=art[id] and ':'..bx..':'..by or '')]=true
    end
   end
  end
  local count=0;for _ in pairs(unique)do count=count+1 end
  return {visible_cells=def.width*def.height*4,replaced_occurrences=replaced,
   preserved_native_occurrences=def.width*def.height*4-replaced,unique_mappings_used=count,
   animation_frame=0,actors_rendered=false,source='actual session replacement coverage on native imported map'}
 end
 local function verifyUnchangedGround(map,before,after,label)
  local cells=0
  for y=0,map.heightCells-1 do for x=0,map.widthCells-1 do
   if map:isWalkableCell(x,y) or map:isGrassCell(x,y) then
    for py=0,15 do for px=0,15 do
     equalPixel(after,x*16+px,y*16+py,before,x*16+px,y*16+py,label..' changed non-tree ground pixels')
    end end
    cells=cells+1
   end
  end end
  check(cells>0,label..' has no ground samples')
  return cells
 end
 local function snapshot(map,generation)
  local out={}
  for cy=0,map.heightCells-1 do for cx=0,map.widthCells-1 do
   if generation==1 then
    out[#out+1]=table.concat({map:cellTile(cx,cy),tostring(map:isWalkableCell(cx,cy)),
     tostring(map:isWaterCell(cx,cy)),tostring(map:isGrassCell(cx,cy))},',')
   else out[#out+1]=tostring(map:cellCollision(cx,cy)) end
  end end
  return hash(table.concat(out,';')..tableString(map.def)..tableString(map.tileset.blocks)
   ..tableString(map.tileset.collision or {}))
 end
 local function eventSnapshot(map)
  return hash(tableString(map.def.warps or {})..tableString(map.def.signs or {})
   ..tableString(map.def.objects or {})..tableString(map.def.bgEvents or {})
   ..tableString(map.def.coordEvents or {})..tableString(map.def.sceneScripts or {})
   ..tableString(map.def.callbacks or {})..tableString(map.def.events or {})..tableString(map.def.scripts or {}))
 end
 local function requireCompletePallet(def,art)
  local c=coverage(def,art)
  check(c.visible_cells==360 and c.replaced_occurrences==360 and c.preserved_native_occurrences==0,
   'Final Pallet fixture must replace all 360 visible background cells')
  return c
 end
 local function verifyPalletPixels(def,art,frame,game)
  local checked=0
  -- Check every occurrence, including repeated tiles, quadrant seams and
  -- building edges, against the exact frame-zero session output.
  for by=0,def.height-1 do for bx=0,def.width-1 do
   local id=def.blocks[by*def.width+bx+1]
   local block=assert(artAt(art,id,bx,by));local expected=block.frames and block.frames[1] or block.image
   for y=0,31 do for x=0,31 do
    equalPixel(frame,bx*32+x,by*32+y,expected,x,y,game..' reviewed RGB/position mismatch')
    checked=checked+1
   end end
  end end
  return checked
 end
 local function verifyCoveredPixels(def,art,frame,game)
  local checked=0
  for by=0,def.height-1 do for bx=0,def.width-1 do
   local block=artAt(art,def.blocks[by*def.width+bx+1],bx,by)
   if block then
    for q=0,3 do if not block.coverage or block.coverage[q] then
     local sequence=block.cellAnimations and block.cellAnimations[q] or block
     local expected=sequence.frames and sequence.frames[math.floor(math.max(0,clock-(sequence.offset or 0))/(sequence.period or .2))%#sequence.frames+1] or block.image
     local sx,sy=q%2*16,math.floor(q/2)*16
     for y=0,15 do for x=0,15 do
      equalPixel(frame,bx*32+sx+x,by*32+sy+y,expected,sx+x,sy+y,game..' reviewed GPU pixels changed')
      checked=checked+1
     end end
    end end
   end
  end end
  return checked
 end
 local function verifyPlantActors(mod,def,map,draw,renderer,world)
  local flora=mod.exports.flora
  local catalog=assert(load(assert(read(MOD..'/lib/flora_catalog.lua'))))()
  flora:select('grass',catalog.grass[#catalog.grass].id)
  flora:select('flowers',catalog.flowers[#catalog.flowers].id)
  mod.exports.state:invalidateVisual();clock=0
  if world then world.mapImage=world:imageFor(map.id)end
  local art=mod.exports.state:replacements(GV.get(),def.tileset,def)
  local found={}
  for by=0,def.height-1 do for bx=0,def.width-1 do
   local block=artAt(art,def.blocks[by*def.width+bx+1],bx,by)
   if block then for q,group in pairs(block.vegetation or {})do
    if (group=='grass' or group=='flowers') and not found[group] then
     found[group]={x=bx*32+q%2*16,y=by*32+math.floor(q/2)*16,q=q,block=block}
    end
   end end
  end end
  check(found.grass or found.flowers,'Plant actor fixture needs grass or flowers')
  local savedRenderer=map.renderer;if renderer then map.renderer=renderer end
  local FX=require('src.render.PaletteFX')
  local savedMode=FX.mode;if renderer then FX.mode='ogred' end
  local replay=renderer and FX.usesSpriteObp() or false
  local checks,proof,changed=0,{},0
  for _,group in ipairs({'grass','flowers'})do if found[group] then
   local cell=found[group];clock=0
   local background=G.newImage(draw());background:setFilter('nearest','nearest')
   local bodyData=love.image.newImageData(16,16);bodyData:mapPixel(function()return 1,0,1,1 end)
   local body=G.newImage(bodyData)
   local top=G.newQuad(0,0,16,8,16,16);local bottom=G.newQuad(0,8,16,8,16,16)

   for _,kind in ipairs({'player','wild','follower','npc'})do
    local actor={px=cell.x,py=cell.y+4,inGrass=group=='grass',moving=false}
    actor.draw=function(e,ox,oy,scale,oamRow)
     G.setColor(1,1,1,1)
     if oamRow=='top' then G.draw(body,top,e.px,e.py-4)
     elseif oamRow=='bottom' then G.draw(body,bottom,e.px,e.py+4)
     else G.draw(body,e.px,e.py-4)end
     if replay then FX.markSpriteRedraw(body,nil,e.px,e.py-4,1)end
    end
    local scene={map=map,entities={actor},player=actor,tilesets=world and world.tilesets}
    mod.exports.vegetation:bind(scene)
    local image=capture(def.width*32,def.height*32,function()
     G.draw(background,0,0)
     if renderer then FX.clearSpriteRedraws();FX.setPass('world')end
     if world then
      world:drawPersonEntry({entity=actor,sx=0,sy=0,ox=0,oy=0,
       drawSprite=function(row,ox,oy,scale)actor:draw(ox,oy,scale,row)end},1)
     else actor:draw(0,0,1)end
     if renderer then
      FX.setPass(nil)
      for _,r in ipairs(FX.spriteRedraws())do
       G.setShader();G.setColor(1,1,1,1)
       if r.quad then G.draw(r.image,r.quad,r.x,r.y,0,r.sx or 1,1)
       else G.draw(r.image,r.x,r.y,0,r.sx or 1,1)end
      end
     end
    end)
    local frame=cell.block.cellAnimations[cell.q].foregroundFrames[1]
    local expected=love.image.newImageData(16,16);local hidden,visible=0,0
    for y=0,15 do for x=0,15 do
     local r,g,b,a=frame:getPixel(cell.q%2*16+x,math.floor(cell.q/2)*16+y)
     if y<8 then a=0 end
     expected:setPixel(x,y,r*a+1-a,g*a,b*a+1-a,1)
     equalPixel(image,cell.x+x,cell.y+y,expected,x,y,kind..' must walk through '..group)
     checks=checks+1;if a>0 then hidden=hidden+1 else visible=visible+1 end
    end end
    check(hidden>0 and visible>0,'Plant foreground must retain both leaves and visible actor gaps')
    if kind=='player' then proof[group]=encodePng(image,GV.get()..'-'..group..'-walk-through-gpu.png')end
   end
   if renderer then FX.clearSpriteRedraws()end
   body:release();background:release()
  end end
  -- Walk-triggered grass stays static before contact and settles afterwards.
  if found.grass then
  mod.exports.vegetation:setMode('walked');clock=0
  local still=draw();clock=.21;local idle=draw();local cell=found.grass
  for y=0,15 do for x=0,15 do equalPixel(idle,cell.x+x,cell.y+y,still,cell.x+x,cell.y+y,'Untouched grass animated')end end
  mod.exports.vegetation:touch(def.id,cell.x/16,cell.y/16,.21,.8)
  clock=.42;local disturbed=draw();changed=0
  for y=0,15 do for x=0,15 do
   local r,g,b=still:getPixel(cell.x+x,cell.y+y)
   local rr,gg,bb=disturbed:getPixel(cell.x+x,cell.y+y)
   if r~=rr or g~=gg or b~=bb then changed=changed+1 end
  end end
  check(changed>0,'Walking through custom grass did not animate that cell')
  clock=2;local settled=draw()
  for y=0,15 do for x=0,15 do equalPixel(settled,cell.x+x,cell.y+y,still,cell.x+x,cell.y+y,'Grass did not settle after walking')end end
  end
  mod.exports.vegetation:setMode('always')
  flora:select('grass','default');flora:select('flowers','default')
  mod.exports.state:invalidateVisual();clock=0;if world then world.mapImage=world:imageFor(map.id)end
  map.renderer=savedRenderer;FX.mode=savedMode
  return {foreground_pixel_checks=checks,actors={'player','wild','follower','npc'},
   gen1_sprite_replay_keeps_foreground=replay,custom_grass_untouched_stays_still=found.grass~=nil,disturbed_pixels=changed,settles_after_contact=found.grass~=nil,images=proof,
   scope='Synthetic opaque actor bodies through the common entity bridge, real Gen1 OBJ replay and native Gen2 World.drawPersonEntry; original source collision/events retained.'}
 end
 local function verifyWarmDraws(mod,draw,label)
  draw()
  local reads,accepted=importReads,mod.exports.state.accepted
  for i=1,120 do clock=i/60;draw()end
  clock=0
  check(importReads==reads,label..' steady draws performed import file reads')
  check(mod.exports.state.accepted==accepted,label..' steady draws rebuilt reviewed rows')
  return {frames=120,import_file_reads=importReads-reads,mapping_rebuilds=0,
   scope='Real native background rendering, after warmup; graphics readback fixtures are not an FPS benchmark.'}
 end
 local graphicsDecoder,nativeCells
 nativeCells={}
 local function sourceDecoder()
  if not graphicsDecoder then
   local Decoder=assert(load(assert(read(MOD..'/lib/donor.lua'))))()
   graphicsDecoder=Decoder.new()
  end
  return graphicsDecoder
 end
 local function nativeCellImage(ref,layers,layerHashes)
  local key=tableString(ref)..tableString(layers)..tableString(layerHashes)
  if nativeCells[key] then return nativeCells[key] end
  local cell,why=sourceDecoder():cell(ref)
  check(cell~=nil,'Independent native donor failed: '..tostring(why))
  local textures={}
  for _,name in ipairs(layers or {'under','mid','over'})do if cell[name] then
   if layerHashes then check(hash(cell[name]:getString())==layerHashes[name],'Independent native layer fingerprint changed') end
   local texture=G.newImage(cell[name]);texture:setFilter('nearest','nearest');textures[#textures+1]=texture
  end end
  local image=capture(16,16,function()for _,texture in ipairs(textures)do G.draw(texture,0,0)end end)
  for _,texture in ipairs(textures)do texture:release()end
  nativeCells[key]=image
  return image
 end
 local function nativeComposition(row)
  local textures,draws={},{}
  local function add(ref,x,y,sx,sy,w,h,layers,hashes)
   local texture=G.newImage(nativeCellImage(ref,layers,hashes));texture:setFilter('nearest','nearest')
   textures[#textures+1]=texture
   local quad=G.newQuad(sx or 0,sy or 0,w or 16,h or 16,16,16)
   draws[#draws+1]={texture,quad,x or 0,y or 0}
  end
  if row.base then add(row.base)end
  if row.donor then add(row.donor)end
  if row.asset then
   local bytes=assert(read(MOD..'/'..row.asset))
   check(hash(bytes)==row.assetFileHash,'Independent local art fingerprint changed')
   local texture=G.newImage(love.filesystem.newFileData(bytes,row.asset:match('[^/]+$')))
   texture:setFilter('nearest','nearest');textures[#textures+1]=texture
   draws[#draws+1]={texture,G.newQuad(0,0,16,16,16,16),0,0}
  end
  for _,part in ipairs(row.parts or {})do
   add(part.donor,part.x,part.y,part.srcX,part.srcY,part.w,part.h,part.layers,part.layerHashes)
  end
  local image=capture(16,16,function()
   for _,draw in ipairs(draws)do G.draw(draw[1],draw[2],draw[3],draw[4])end
  end)
  for _,texture in ipairs(textures)do texture:release()end
  return image
 end
 local function mappingRows(path)
  local source=read(MOD..'/'..path)
  return source and assert(load(source,'@probe/'..path))() or {}
 end
 local function sourceGeometry(map,cx,cy)
  return {tile=map:cellTile(cx,cy),walkable=map:isWalkableCell(cx,cy),
   water=map:isWaterCell(cx,cy),grass=map:isGrassCell(cx,cy)}
 end
 local function verifyGen1Terrain(game,def,map,frame)
  local field=generated(game,'field');local ledges=field.ledges
  local function canJump(standing,tile)
   for _,ledge in ipairs(ledges or {})do
    if ledge.facing=='down' and ledge.input=='down' and ledge.standingTile==standing
      and ledge.ledgeTile==tile then return true end
   end
   return false
  end
  local proof={ledge_occurrences=0,walkable_stair_occurrences=0,pond_occurrences=0,
   checked_native_pixels=0,source_ledge_rules_sha256=hash(tableString(ledges)),
   limits='Native map/field interaction predicates are audited; no player or event simulation.'}
  for _,row in ipairs(mappingRows('mappings/gen1_outdoor.lua'))do
   if row.game==game and row.map==def.id and (row.role:find('south_ledge',1,true)
    or row.role=='walkable_stairs_bottom_half' or row.role:find('freshwater_pond',1,true)) then
    local expected=nativeComposition(row)
    for pos,id in ipairs(def.blocks)do if id==row.id then
     local cx=(pos-1)%def.width*2+row.quadrant%2
     local cy=math.floor((pos-1)/def.width)*2+math.floor(row.quadrant/2)
     for y=0,15 do for x=0,15 do
      equalPixel(frame,cx*16+x,cy*16+y,expected,x,y,'Independent native terrain composition mismatch')
      proof.checked_native_pixels=proof.checked_native_pixels+1
     end end
     local source=sourceGeometry(map,cx,cy)
     if row.role:find('south_ledge',1,true) then
      check(canJump(map:cellTile(cx,cy-1),source.tile),'Source south ledge lost its native down-hop predicate')
      check(not source.walkable,'Source jump ledge unexpectedly became freely walkable')
      proof.ledge_occurrences=proof.ledge_occurrences+1
     elseif row.role=='walkable_stairs_bottom_half' then
      check(source.tile==60 and source.walkable and not canJump(map:cellTile(cx,cy-1),source.tile),
       'Walkable stairs were confused with a jump ledge')
      proof.walkable_stair_occurrences=proof.walkable_stair_occurrences+1
     else
      check(source.water,'Freshwater pond lost its native water/shore predicate')
      proof.pond_occurrences=proof.pond_occurrences+1
     end
    end end
   end
  end
  return proof
 end
 local function verifyAnimationFrames(def,art,draw,bank,frames,phase)
  local count=0
  for pos,id in ipairs(def.blocks)do
   local block=artAt(art,id,(pos-1)%def.width,math.floor((pos-1)/def.width))
   if block and block.frames and block.bank==bank then
   check(#block.frames==frames and block.period==16/60 and block.offset==phase/60,'Native donor animation schedule changed')
   count=count+1
   end
  end
  check(count>0,'Expected native animation bank is absent: '..bank)
  local checkpoints={}
  for f=0,frames do
   -- Sample one native tick into each frame, then the complete repeated cycle.
   local tick=phase+f*16+1;clock=tick/60
   local image=draw();local sampled=0
   for pos,sourceId in ipairs(def.blocks)do
     local bx,by=(pos-1)%def.width,math.floor((pos-1)/def.width)
     local block=artAt(art,sourceId,bx,by)
     if block and block.frames and block.bank==bank then
     for q,included in pairs(block.coverage)do if included then
      for y=0,15 do for x=0,15 do
       equalPixel(image,bx*32+q%2*16+x,by*32+math.floor(q/2)*16+y,
        block.frames[f%frames+1],q%2*16+x,math.floor(q/2)*16+y,bank..' native GPU animation mismatch')
      end end
      sampled=sampled+1
     end end
     end
   end
   checkpoints[#checkpoints+1]={tick=tick,frame=f%frames,visible_cells_sampled=sampled}
  end
  clock=0
  return {bank=bank,frames=frames,period_ticks=16,phase_ticks=phase,checkpoints=checkpoints}
 end
 local nativeBuildingSources={}
 local function verifyRoofBackground(candidate,actual)
  local review=assert(candidate.roof_empty_background,'Approved roof background proof missing')
  local base=nativeCellImage(assert(candidate.base))
  local roofParts,opaque,empty,changed=0,0,0,0
  for _,part in ipairs(candidate.parts)do if part.layers then
   check(#part.layers==1 and part.layers[1]=='over','Roof proof expects original native over artwork')
   local cell,why=sourceDecoder():cell(part.donor);check(cell~=nil,tostring(why))
   check(hash(cell.over:getString())==part.layerHashes.over,'Original roof layer fingerprint changed')
   local original=nativeCellImage(part.donor)
   local sx=part.srcX or (part.donor.quadrant or 0)%2*8
   local sy=part.srcY or math.floor((part.donor.quadrant or 0)/2)*8
   local tx,ty=part.target_xy_px[1],part.target_xy_px[2]
   for y=0,(part.h or 8)-1 do for x=0,(part.w or 8)-1 do
    local _,_,_,a=cell.over:getPixel(sx+x,sy+y)
    if a==0 then
     equalPixel(actual,tx+x,ty+y,base,(tx+x)%16,(ty+y)%16,'Empty roof corner differs from surrounding Emerald ground')
     local orr,org,orb=original:getPixel(sx+x,sy+y)
     local br,bg,bb=base:getPixel((tx+x)%16,(ty+y)%16)
     if orr~=br or org~=bg or orb~=bb then changed=changed+1 end
     empty=empty+1
    else
     check(a==1,'Native roof unexpectedly contains translucent material')
     equalPixel(actual,tx+x,ty+y,cell.over,sx+x,sy+y,'Opaque roof/eave pixel changed')
     opaque=opaque+1
    end
   end end
   roofParts=roofParts+1
  end end
  check(roofParts==review.roof_parts and changed==review.changed_empty_background_pixels,
   'Roof corner/background review count changed')
  check(review.changed_native_roof_pixels==0,'Approved roof proof permits modified roof pixels')
  return {native_roof_parts=roofParts,opaque_roof_pixels_unchanged=opaque,
   empty_pixels_match_emerald_ground=empty,changed_empty_background_pixels=changed,
   ground_donor=candidate.base,roof_geometry_unchanged=true}
 end
 local function nativeBuildingSource(kind,reviewRoot)
  if nativeBuildingSources[kind] then return nativeBuildingSources[kind] end
  local references=Json.decode(assert(read(reviewRoot..'gen1-vs-frlg-buildings-reference.json')))
  local id=kind=='home' and 'firered-home' or 'firered-oak-lab'
  local selected
  for _,ref in ipairs(references.native_references)do if ref.id==id then selected=ref end end
  check(selected~=nil,'Native building reference is missing')
  local Decoder=assert(load(assert(read(MOD..'/lib/donor.lua'))))()
  local decoder=Decoder.new();local cells,textures={},{}
  for _,row in ipairs(selected.metatiles_by_row)do for _,mid in ipairs(row)do
   if not cells[mid] then
    local cell,why=decoder:cell({game=selected.game,tileset=selected.pair,id=mid})
    check(cell~=nil,'Native building source could not be decoded: '..tostring(why))
    cells[mid]={}
    for _,layer in ipairs({'under','mid','over'})do if cell[layer] then
     local texture=G.newImage(cell[layer]);texture:setFilter('nearest','nearest')
     cells[mid][#cells[mid]+1]=texture;textures[#textures+1]=texture
    end end
   end
  end end
  local image=capture(selected.width_px,selected.height_px,function()
   for y,row in ipairs(selected.metatiles_by_row)do for x,mid in ipairs(row)do
    for _,texture in ipairs(cells[mid])do G.draw(texture,(x-1)*16,(y-1)*16) end
   end end
  end)
  for _,texture in ipairs(textures)do texture:release() end
  check(hash(image:getString())==selected.crop_pixel_sha256,'Native building GPU reference fingerprint changed')
  local result={image=image,reference=selected,
   readback=encodePng(image,'firered-'..kind..'-native-reference-gpu.png')}
  nativeBuildingSources[kind]=result
  return result
 end
 local function verifyBuildings(def,frame,game)
  local reviewRoot=MOD..'/../.work/tileshift-building-review/'
  local review=Json.decode(assert(read(reviewRoot..'compact-frlg-native-parts-review.json')))
  local prototypes,candidates={},{}
  for _,candidate in ipairs(review.candidates)do
   local image=love.image.newImageData(love.filesystem.newFileData(
    assert(read(reviewRoot..'compact-frlg-'..candidate.id..'-prototype.png')),candidate.id..'.png'))
   check(hash(image:getString())==candidate.output_pixel_sha256,'Approved building prototype pixels changed')
   prototypes[candidate.id]=image
   candidates[candidate.id]=candidate
  end
  local proofs={}
  for _,building in ipairs({
   {id='trainer_home',kind='home',rect={4,3,4,3},destination='REDS_HOUSE_1F',anchor={24,48}},
   {id='rival_home',kind='home',rect={12,3,4,3},destination='BLUES_HOUSE',anchor={24,48}},
   {id='professor_lab',kind='lab',rect={10,8,6,4},destination='OAKS_LAB',anchor={40,64}}})do
   local r=building.rect
   local expected=assert(prototypes[building.kind])
   check(expected:getWidth()==r[3]*16 and expected:getHeight()==r[4]*16,'Building footprint changed')
   local actual=love.image.newImageData(r[3]*16,r[4]*16)
   actual:paste(frame,0,0,r[1]*16,r[2]*16,r[3]*16,r[4]*16)
   check(actual:getString()==expected:getString(),game..' '..building.id..' GPU pixels differ from approved native prototype')
   local door
   for _,warp in ipairs(def.warps or {})do
    if warp.destMap==building.destination then check(not door,'Building has duplicate source door warps');door=warp end
   end
   check(door~=nil,'Source building door warp is missing')
   local ax,ay=(door.x-r[1])*16+8,(door.y-r[2]+1)*16
   check(ax==building.anchor[1] and ay==building.anchor[2],'Building source door anchor changed')
   -- Compare complete entrance trim and the other reviewed motifs directly
   -- against a GPU render of original native donor cells, independently of
   -- the compact prototype and its production composition rectangles.
   local source=nativeBuildingSource(building.kind,reviewRoot)
   local features,entrances,clearances,windows={},0,0,{}
   for _,feature in ipairs(candidates[building.kind].features_checked)do
    local sr,tr=feature.source_rect_xywh,feature.target_rect_xywh
    check(sr[3]==tr[3] and sr[4]==tr[4],'Native feature crop was scaled')
    local targetCrop=love.image.newImageData(tr[3],tr[4])
    targetCrop:paste(actual,0,0,tr[1],tr[2],tr[3],tr[4])
    local sourceCrop=love.image.newImageData(sr[3],sr[4])
    sourceCrop:paste(source.image,0,0,sr[1],sr[2],sr[3],sr[4])
    check(targetCrop:getString()==sourceCrop:getString(),game..' '..building.id..' native '..feature.feature..' context changed')
    local name=feature.feature:lower()
    if name:find('complete entrance frame',1,true) then
     check(tr[3]==16 and tr[4]==17,'Entrance proof must include the complete native 16 by 17 pixel frame')
     entrances=entrances+1
    end
    if name:find('native wall clearance',1,true) then clearances=clearances+1 end
    if building.kind=='lab' and tr[3]==24 and tr[4]==24 and tr[2]==40
      and (tr[1]==8 or tr[1]==56) then windows[tr[1]]=true end
    features[#features+1]={feature=feature.feature,source_rect_xywh=sr,target_rect_xywh=tr,
     exact_native_gpu_pixels=true,rgba_sha256=hash(targetCrop:getString())}
   end
   check(entrances>0,'Approved building must include a complete native entrance context proof')
   if building.kind=='home' then
    check(clearances>0,'Approved home must include its native wall clearance strip proof')
   else
    check(windows[8] and windows[56],'Laboratory proof must include both complete 24 by 24 pixel windows and awnings')
   end
   proofs[#proofs+1]={id=building.id,footprint_px={r[3]*16,r[4]*16},
    map_rect_cells=r,door_bottom_anchor_px={ax,ay},door_destination=door.destMap,
    exact_approved_native_pixels=true,rgba_sha256=hash(actual:getString()),
    native_features=features,native_source_gpu=source.readback,
    roof_background=verifyRoofBackground(candidates[building.kind],actual),
    image=encodePng(actual,game..'-pallet-'..building.id..'-gpu.png')}
  end
  return proofs
 end
 local publicBuildingSources={}
 local function nativeBuildingSource(n)
  local key=tableString(n)
  if publicBuildingSources[key]then return publicBuildingSources[key]end
  local manifest=generated(n.game,'gba/native/manifest')
  local spec=assert(manifest.layouts[n.map],'Public native building layout is missing')
  check(spec.pair==n.pair,'Public building native pair changed')
  local relative=n.game..'/data/generated/gba/native/'..spec.file
  check(hash(assert(read(CACHE..'/'..relative)))==n.layout_file_sha256,'Public building native layout fingerprint changed')
  local layout,why=require('src.import.gba.native_pack').decodeMidLayout(assert(cacheRead(relative)))
  check(layout~=nil,tostring(why));local r=n.rect_cells;local textures,mids={},{}
  for y=0,r[4]-1 do for x=0,r[3]-1 do
   local mid=assert(layout.cells[(r[2]+y)*layout.width+r[1]+x+1]).mid
   mids[y*r[3]+x+1]=mid
   if not textures[mid]then textures[mid]=G.newImage(nativeCellImage({game=n.game,tileset=n.pair,id=mid}));textures[mid]:setFilter('nearest','nearest')end
  end end
  local image=capture(r[3]*16,r[4]*16,function()
   for y=0,r[4]-1 do for x=0,r[3]-1 do G.draw(textures[mids[y*r[3]+x+1]],x*16,y*16)end end
  end)
  for _,texture in pairs(textures)do texture:release()end
  check(hash(image:getString())==n.source_pixel_sha256,'Original public building GPU source crop changed')
  if n.destination and n.door_anchor then
   local bytes=assert(cacheRead(n.game..'/data/generated/gba/warps.lua'))
   local literal=assert(bytes:match('\n  '..n.map..' = ({.-\n  })'))
   local warps=assert(Serializer.decode('return '..literal,{allowArray=true,allowComments=true}))
   local found=false
   for _,w in ipairs(warps)do if w.destMap==n.destination then
    if(w.x-r[1])*16+8==n.door_anchor[1]and(w.y-r[2]+1)*16==n.door_anchor[2]then found=true end
   end end
   check(found,'Original public building native entrance anchor changed')
  end
  local result={image=image,readback=encodePng(image,'public-native-'..n.source_pixel_sha256:sub(1,12)..'-reference-gpu.png')}
  publicBuildingSources[key]=result;return result
 end
 local function verifyPublicBuildings(game,def,frame)
  local proofs={}
  local function crop(image,r)
   local out=love.image.newImageData(r[3],r[4]);out:paste(image,0,0,r[1],r[2],r[3],r[4]);return out
  end

  for _,family in ipairs({{folder='tileshift-building-extended',file='architecture-native-prototypes.json',instances='source_buildings'},
   {folder='tileshift-building-kanto',file='kanto-building-variants.json',instances='source_instances'},
   {folder='tileshift-violet-facade-review',file='decorative-native-model.json',instances='source_instances'},
   {folder='tileshift-violet-school-review',file='school-tall-model.json',instances='source_instances'}})do
   local root=MOD..'/../.work/'..family.folder..'/'
   local bytes=read(root..family.file)
   if bytes then
    local review=Json.decode(bytes)
    for _,record in ipairs(review[family.instances])do if record.game==game and record.map==def.id
     and not(def.id=='VIOLET_CITY'and record.template=='school'and(game=='gold'or game=='silver'))then
     local model=assert(review.templates[record.template]);local r=record.rect_cells
     check(r[3]*16==model.size_px[1]and r[4]*16==model.size_px[2],'Public building source footprint changed')
     local actual=crop(frame,{r[1]*16,r[2]*16,r[3]*16,r[4]*16})
     local prototype=love.image.newImageData(love.filesystem.newFileData(
      assert(read(root..record.template..'-compact-prototype.png')),record.template..'.png'))
     check(hash(prototype:getString())==model.rgba_pixel_sha256,'Public building approved prototype fingerprint changed')
     local base=nativeCellImage(model.base)
     local paved
     if def.id=='VIOLET_CITY'and(record.template=='center'or record.no_source_warp)then
      paved=nativeCellImage({game='firered',tileset='pewter_outdoor',id=449,
       hash='5532a7b6aa1c066481a8e2c322a0ddf832f322dc1ad1314f4034e650dd8f3586'})
     end
     local function groundAt(x,y)return paved and x<32 and y<16 and paved or base end
     if paved then
      for _,part in ipairs(model.parts)do if part.layers then
       local cell=assert(sourceDecoder():cell(part.donor))
       local tx,ty=part.target_xy[1],part.target_xy[2]
       for y=0,part.h-1 do for x=0,part.w-1 do
        local _,_,_,a=cell.over:getPixel(part.srcX+x,part.srcY+y)
        if a==0 then
         local background=groundAt(tx+x,ty+y)
         prototype:setPixel(tx+x,ty+y,background:getPixel((tx+x)%16,(ty+y)%16))
        end
       end end
      end end
     end
     check(actual:getString()==prototype:getString(),game..' '..def.id..' '..record.template..' GPU output differs from the approved whole building')
     local door
     if record.no_source_warp then
      for _,w in ipairs(def.warps or{})do
       check(not(w.x>=r[1]and w.x<r[1]+r[3]and w.y>=r[2]and w.y<r[2]+r[4]),
        'Decorative Violet house gained an entrance event')
      end
      door={x=record.door_map_cell[1],y=record.door_map_cell[2]}
     else
      for _,w in ipairs(def.warps or {})do
       if w.destMap==record.destination and(not record.door_map_cell or(w.x==record.door_map_cell[1]and w.y==record.door_map_cell[2]))then door=w;break end
      end
      check(door~=nil,'Public building original source entrance is missing')
     end
     local anchor={(door.x-r[1])*16+8,(door.y-r[2]+1)*16}
     check(anchor[1]==record.door_bottom_anchor_px[1]and anchor[2]==record.door_bottom_anchor_px[2]
      and anchor[1]==model.door_bottom_anchor_px[1]and anchor[2]==model.door_bottom_anchor_px[2],
      'Public building source door/warp anchor moved')
     local source=nativeBuildingSource(model.native);local features={}
     for _,feature in ipairs(model.features_checked)do
      local sr,tr=feature.source_rect_xywh,feature.target_rect_xywh
      check(sr[3]==tr[3]and sr[4]==tr[4],'Public native feature was scaled')
      local expected=crop(source.image,sr);local result=crop(actual,tr)
      check(result:getString()==expected:getString(),game..' '..def.id..' '..record.template..' clips/changes '..feature.feature)
      features[#features+1]={feature=feature.feature,source_rect_xywh=sr,target_rect_xywh=tr,
       exact_original_native_gpu_pixels=true,rgba_sha256=hash(result:getString())}
     end
     check(#features>0,'Public building has no complete native feature proof')
     local holes,opaque=0,0
     for _,part in ipairs(model.parts)do if part.layers then
      check(#part.layers==1 and part.layers[1]=='over','Public building selected an unexpected roof layer')
      local cell,why=sourceDecoder():cell(part.donor);check(cell~=nil,tostring(why))
      check(hash(cell.over:getString())==part.layerHashes.over,'Public roof native alpha layer changed')
      local tx,ty=part.target_xy[1],part.target_xy[2]
      for y=0,part.h-1 do for x=0,part.w-1 do
       local sx,sy=part.srcX+x,part.srcY+y;local _,_,_,alpha=cell.over:getPixel(sx,sy)
       if alpha==0 then
        equalPixel(actual,tx+x,ty+y,groundAt(tx+x,ty+y),(tx+x)%16,(ty+y)%16,'Public roof empty corner is not its actual local ground')
        holes=holes+1
       else
        check(alpha==1,'Public native roof contains unexpected semi-transparency')
        equalPixel(actual,tx+x,ty+y,cell.over,sx,sy,'Public native roof/eave pixel changed')
        opaque=opaque+1
       end
      end end
     end end
     check(holes==model.roof_empty_pixels_checked and model.all_roof_empty_pixels_exact_ground
      and model.native_roof_pixel_differences==0,'Public roof alpha-mask review count changed')
     proofs[#proofs+1]={template=record.template,destination=record.destination,map_rect_cells=r,
      source_door_bottom_anchor_px=anchor,whole_building_exact=true,rgba_sha256=hash(actual:getString()),
      native_features=features,native_source_gpu=source.readback,
      roof={empty_pixels_exact_local_ground=holes,opaque_native_selected_pixels_unchanged=opaque,paved_northwest=paved~=nil},
      review_metadata_sha256=hash(bytes),
      image=encodePng(actual,game..'-'..def.id..'-'..record.destination..'-building-gpu.png')}
    end end
   end
  end
  return proofs
 end

 local function verifyAnimatedBuildings(game,def,draw)
  local folder=MOD..'/../.work/'
  local fan=Json.decode(assert(read(folder..'tileshift-special-buildings/fanclub-activation/fanclub-expected-frame-hashes.json')))
  local route=Json.decode(assert(read(folder..'tileshift-route12-houses/route12-coastal-house-model.json')))
  local selected={}
  for _,row in ipairs(mappingRows('mappings/buildings_extended.lua'))do
   if row.game==game and row.map==def.id and row.x~=nil then
    local key=game..':'..def.id..':'..row.x..':'..row.y
    if fan[key]then selected[#selected+1]={row=row,hashes=fan[key]}end
    if def.id=='ROUTE_12'then
     for _,instance in ipairs(route.source_instances)do
      if instance.game==game and instance.map==def.id then
       local r=instance.rect_cells
       if row.x>=r[1]and row.x<r[1]+r[3]and row.y>=r[2]and row.y<r[2]+r[4]then
        selected[#selected+1]={row=row,rect=r}
       end
      end
     end
    end
   end
  end
  check(#selected>0,'No approved animated-building context selected')
  local results={}
  for f=0,7 do
   clock=(f*16+2)/60
   local actual=draw();local expected
   if def.id=='ROUTE_12'then
    local path=folder..'tileshift-route12-houses/route12-native-frame-'..f..'.png'
    expected=love.image.newImageData(love.filesystem.newFileData(assert(read(path)),'route12.png'))
    check(hash(expected:getString())==route.template.whole_building_frame_rgba_sha256[f+1],
     'Independent whole coastal-house prototype changed')
   end
   for _,entry in ipairs(selected)do
    local row=entry.row
    local cell=love.image.newImageData(16,16)
    cell:paste(actual,0,0,row.x*16,row.y*16,16,16)
    if entry.hashes then
     check(hash(cell:getString())==entry.hashes[#entry.hashes==1 and 1 or f+1],
      'GPU Fan Club roof/wall differs from independently reviewed native frame')
    else
     local r=entry.rect
     for y=0,15 do for x=0,15 do
      equalPixel(cell,x,y,expected,(row.x-r[1])*16+x,(row.y-r[2])*16+y,
       'GPU coastal roof/frame differs from complete native prototype')
     end end
    end
   end
   results[#results+1]={frame=f,cells=#selected,tick=f*16+2}
  end
  clock=0
  return {complete_native_frames=8,static_facades_and_animated_roof_corners=true,checkpoints=results}
 end
 local function verifyHousehold(game,def,frame)
   check(game=='red' and def.id=='REDS_HOUSE_1F','Household probe requires the original Red home')
   local fw,fh=frame:getDimensions()
   check(fw==128 and fh==128,'Household frame must use unscaled source-map coordinates')
   local sourceBefore=Json.encode(def)
   local byRole,refs={},{ }
   local function add(ref)
     if ref then refs[ref.game..':'..ref.tileset..':'..ref.id]=ref end
   end
   for _,row in ipairs(mappingRows('mappings/interiors.lua'))do
     if row.game==game and row.map==def.id and row.x~=nil and row.role:match('^household_')then
       byRole[row.role]=byRole[row.role]or{};byRole[row.role][#byRole[row.role]+1]=row
       add(row.donor);add(row.base)
       for _,part in ipairs(row.parts or{})do add(part.donor)end
     end
   end
   local images={}
   local function tile(id,cartridge,tileset)
     cartridge,tileset=cartridge or'firered',tileset or'player_house'
     local key=cartridge..':'..tileset..':'..id
     check(refs[key]~=nil,'Required complete-frame native reference is absent: '..key)
     if not images[key]then images[key]=nativeCellImage(refs[key])end
     return images[key]
   end
   local function at(row,x,y,image,sx,sy,label)
     equalPixel(frame,row.x*16+x,row.y*16+y,image,sx,sy,label)
   end
   local function wall(row,x,y,label)
     at(row,x,y,tile(y<8 and 32 or 40),x,y,label)
   end
   local function rows(role,count)
     local found=byRole['household_'..role]or{}
     check(#found==count,'Unexpected complete household feature count: '..role)
     return found
   end
   local proof={}
   local televisions=rows('television',1)
   for _,row in ipairs(televisions)do
     local n,outside=0,0
     for y=0,15 do for x=0,15 do
       local image,sy
       if y==0 and x>=3 and x<=12 then image,sy=tile(45),13
       elseif y==1 and x>=2 and x<=13 then image,sy=tile(45),14
       elseif y==2 then image,sy=tile(45),15
       elseif y>=3 and y<=4 then image,sy=tile(53),y-3
       elseif y>=5 and y<=14 then image,sy=tile(53),y+1
       elseif y==15 then image,sy=tile(61),0 end
       if image then at(row,x,y,image,x,sy,'Complete TV cap, screen, bevel and controls');n=n+1
       else at(row,x,y,tile(1),x,y,'TV outside cap retains exact room wood');outside=outside+1 end
     end end
     check(n==246 and outside==10,'Complete TV glyph/wood footprint changed')
     for y=2,5 do for x=0,15 do
       equalPixel(tile(53),x,y,tile(53),x,1,'Only identical blank TV perspective rows were omitted')
     end end
   end
   proof.television={features=1,retainedNativePixels=246,outsideWoodPixels=10,removedIdenticalRows=4,nativeHeight=20,targetHeight=16}
   for _,row in ipairs(rows('window',3))do
     local n,outside=0,0
     for y=0,15 do for x=0,15 do
       local image,sy
       if y==2 and x<=14 then image,sy=tile(542,'emerald','building__brendans_mays_house'),8
       elseif y>=3 and y<=9 then image,sy=tile(542,'emerald','building__brendans_mays_house'),y+6
       elseif y>=10 and y<=12 then image,sy=tile(550,'emerald','building__brendans_mays_house'),y-10
       elseif y==13 and x>=1 then image,sy=tile(550,'emerald','building__brendans_mays_house'),3 end
       if image then at(row,x,y,image,x,sy,'Complete native window frame, glass and highlight');n=n+1
       else wall(row,x,y,'All window outside pixels retain compact native wall');outside=outside+1 end
     end end
     check(n==190 and outside==66,'Complete window glyph/wall footprint changed')
   end
   proof.window={features=3,retainedNativePixelsPerFeature=190,outsideWallPixelsPerFeature=66,nativeSize={16,12}}
   local bookcases=rows('bookcase_head',2);local bases=rows('bookcase_base',2)
   for _,row in ipairs(bookcases)do
     local base
     for _,candidate in ipairs(bases)do if candidate.x==row.x and candidate.y==row.y+1 then base=candidate end end
     check(base~=nil,'Complete native bookcase lower cell is missing')
     local n,outside=0,0
     for y=0,31 do for x=0,15 do
       local included=y>=5 or(y==0 and((x>=1 and x<=4)or(x>=11 and x<=14)))
         or(y==1 and x>=1 and x<=14)or(y>=2 and y<=4 and x>=1)
       local target=y<16 and row or base
       if included then
         local sy=y<5 and y+11 or y+16
         local ids={{43,44},{51,52},{59,60}}
         local id=ids[math.floor(sy/16)+1][x<8 and 1 or 2]
         at(target,x,y%16,tile(id),x,sy%16,'Complete bookcase cap, shelves, lower frame and all native shadow');n=n+1
       else wall(target,x,y%16,'Bookcase outside cap retains compact wall');outside=outside+1 end
     end end
     check(n==499 and outside==13,'Complete bookcase glyph/wall footprint changed')
     for y=0,4 do for x=0,15 do
       local image=tile(x<8 and 51 or 52)
       equalPixel(image,x,y,image,x,0,'Only identical blank bookcase panel rows were omitted')
     end end
   end
   proof.bookcase={features=2,retainedNativePixelsPerFeature=499,outsideWallPixelsPerFeature=13,removedIdenticalRows=5,nativeHeight=37,targetHeight=32,fullFloorShadowRetained=true}
   local left,right=rows('rug_left',1)[1],rows('rug_right',1)[1]
   check(right.x==left.x+1 and right.y==left.y,'Entry mat must remain one complete32px source profile')
   local mat=0
   for y=0,15 do for x=0,31 do
     local target=x<16 and left or right
     if x>=3 and x<=28 then
       local sx,sy=x+8,y+4
       local id=18+math.floor(sx/16)+math.floor(sy/16)*8
       at(target,x%16,y,tile(id),sx%16,sy%16,'Complete26px native entry mat including border and lower shadow');mat=mat+1
     else at(target,x%16,y,tile(1),x%16,y,'Entry-mat outside pixels retain room wood')end
   end end
   check(mat==416,'Complete entry mat pixel count changed')
   proof.entryMat={nativePixels=416,width=26,height=16,sourceWidth=32}
   local masks={chair_left={75,2,149},chair_right={78,2,149},table_nw={76,1,224},
     table_ne={77,1,224},table_sw={84,1,229},table_se={85,1,229}}
   local furniture=0
   for role,spec in pairs(masks)do
     for _,row in ipairs(rows(role,spec[2]))do
       local part=row.parts and row.parts[1]
       check(part and #row.parts==1 and part.donor.id==spec[1]and part.layers[1]=='mid',
         'Furniture must use the complete reviewed native middle layer')
       local glyph=nativeCellImage(part.donor,part.layers,part.layerHashes);local n=0
       for y=0,15 do for x=0,15 do
         local _,_,_,a=glyph:getPixel(x,y)
         if a>0 then at(row,x,y,glyph,x,y,'Complete native chair/table silhouette');n=n+1
         else at(row,x,y,tile(1),x,y,'Chair/table outside pixels retain native room wood')end
       end end
       check(n==spec[3],'Complete native chair/table mask count changed');furniture=furniture+n
     end
   end
   proof.furniture={chairPixelsPerFeature=149,chairs=4,completeTablePixels=906,checkedNativePixels=furniture}
   local stair=rows('upstairs',1)[1];local native=nativeCellImage(stair.donor)
   for y=0,15 do for x=0,15 do at(stair,x,y,native,x,y,'Complete native upstairs glyph')end end
   local up,exits=0,0
   for _,warp in ipairs(def.warps or{})do
     if warp.x==stair.x and warp.y==stair.y then
       check(warp.destMap=='REDS_HOUSE_2F'and warp.destWarp==1,'Original upstairs destination changed');up=up+1
     elseif warp.destMap=='LAST_MAP'then exits=exits+1 end
   end
   check(up==1 and exits==2 and #(def.warps or{})==3,'Original household up/exit warp layout changed')
   check(Json.encode(def)==sourceBefore,'Household proof must not change the original source map')
   proof.originalSourceWarps={upstairs=1,exits=2,destination='REDS_HOUSE_2F',unchanged=true}
   return proof
 end
 local function verifyAzaleaWell(game,def,frame)
  local whole=love.image.newImageData(love.filesystem.newFileData(assert(read(MOD..'/assets/original/slowpoke-well/well.png')),'well.png'))
  check(whole:getWidth()==48 and whole:getHeight()==48,'Well must retain its native3x3 footprint')
  local rows={}
  for _,row in ipairs(mappingRows('mappings/azalea.lua'))do
   if row.game==game and row.role=='azalea_slowpoke_well'then rows[#rows+1]=row end
  end
  check(#rows==9,'Well must have exactly9 source cells')
  local ground=nativeCellImage(rows[1].base)
  local expected=capture(48,48,function()
   local bg=G.newImage(ground);local top=G.newImage(whole)
   for y=0,2 do for x=0,2 do G.draw(bg,x*16,y*16)end end
   G.draw(top,0,0);bg:release();top:release()
  end)
  for y=0,47 do for x=0,47 do equalPixel(frame,30*16+x,6*16+y,expected,x,y,'Whole original well composition changed')end end
  local entrance=false
  for _,warp in ipairs(def.warps or{})do
   if warp.x==31 and warp.y==7 then check(warp.destMap=='SLOWPOKE_WELL_B1F','Well entrance destination changed');entrance=true end
  end
  check(entrance,'Native well entrance missing')
  for _,row in ipairs(rows)do
   check(row.x>=30 and row.x<=32 and row.y>=6 and row.y<=8,'Well overhangs original footprint')
   local want=(row.x==31 and row.y==7)and 123 or(row.x==31 and row.y==8)and 0 or 7
   check(row.sourceCollision==want,'Well source collision/step layout changed')
  end
  return {whole_sprite_checked_pixels=2304,footprint={30,6,3,3},entrance={31,7},steps={31,8},source_warp_unchanged=true}
 end
 local function verifySprout(game,def,frame)
  local folder=MOD..'/../.work/tileshift-sprout-native-material/sloped-roof-hybrid/'
  local bytes=assert(read(folder..'sprout-original-native-material-model.json'))
  local model=Json.decode(bytes);local r=model.source_rect_cells
  check(def.id==model.source_map,'Sprout GPU fixture uses the wrong source map')
  local actual=love.image.newImageData(r[3]*16,r[4]*16)
  actual:paste(frame,0,0,r[1]*16,r[2]*16,r[3]*16,r[4]*16)
  local overlays={}
  for _,row in ipairs(mappingRows('mappings/buildings_extended.lua'))do
   if row.game==game and row.map==def.id and row.role=='architecture_sprout_pagoda' and row.artOverlay then overlays[#overlays+1]=row end
  end
  if #overlays>0 then
   check(#overlays==20,'Generated Sprout must retain its complete4x5 source footprint')
   local whole=love.image.newImageData(love.filesystem.newFileData(assert(read(MOD..'/assets/original/sprout-tower/tower.png')),'tower.png'))
   check(whole:getWidth()==64 and whole:getHeight()==80,'Generated tower footprint changed')
   local ground=nativeCellImage(overlays[1].base)
   local previous=love.image.newImageData(love.filesystem.newFileData(assert(read(folder..'sprout_pagoda-compact-prototype.png')),'previous.png'))
   local retained=0
   for y=0,79 do for x=0,63 do
    local expected,ex,ey=whole,x,y
    if y>=64 and (x<8 or x>=56) then expected,ex,ey=previous,x,y;retained=retained+1
    else
     local rr,gg,bb,aa=whole:getPixel(x,y)
     local gr,ggg,gb,ga=ground:getPixel(x%16,y%16)
     local pixel=love.image.newImageData(1,1)
     pixel:setPixel(0,0,rr*aa+gr*(1-aa),gg*aa+ggg*(1-aa),bb*aa+gb*(1-aa),aa+ga*(1-aa))
     expected,ex,ey=pixel,0,0
    end
    equalPixel(actual,x,y,expected,ex,ey,'Generated Sprout or its retained native ledges changed')
   end end
   local door
   for _,warp in ipairs(def.warps or{})do if warp.destMap=='SPROUT_TOWER_1F' then door=warp;break end end
   check(door and door.x==23 and door.y==5,'Generated tower entrance moved away from source warp')
   return {artwork='User Gemini references refined with built-in imagegen',whole_approved_building_exact=true,
    retained_native_ledge_pixels=retained,source_warp_anchor={24,80},rgba_sha256=hash(actual:getString()),
    image=encodePng(actual,game..'-sprout-refined-gpu.png')}
  end
  check(hash(actual:getString())==model.final_compiled_rgba_sha256,'Sprout complete approved architecture changed')
  local prototype=love.image.newImageData(love.filesystem.newFileData(assert(read(folder..'sprout_pagoda-compact-prototype.png')),'sprout.png'))
  check(actual:getString()==prototype:getString(),'Sprout whole GPU building differs from approved native-material prototype')
  local features={}
  for _,feature in ipairs(model.features_checked)do
   local source=nativeBuildingSource(assert(model.native_materials[feature.native_source]))
   local sr,tr=feature.source_rect_xywh,feature.target_rect_xywh
   check(sr[3]==tr[3]and sr[4]==tr[4],'Sprout complete native feature was scaled')
   for y=0,tr[4]-1 do for x=0,tr[3]-1 do
    equalPixel(actual,tr[1]+x,tr[2]+y,source.image,sr[1]+x,sr[2]+y,'Sprout native complete frame/window changed')
   end end
   features[#features+1]={feature=feature.feature,source=feature.native_source,
    source_rect_xywh=sr,target_rect_xywh=tr,exact_native_gpu_pixels=true}
  end
  check(#features==6,'Sprout must retain all five whole window units and its complete entrance')
  local strips={}
  for i,reference in ipairs(model.approved_outdoor_platform_references)do
   local target=assert(model.preserved_terrain_strips[i]);local image=nativeCellImage(reference.donor)
   local manifest=generated(reference.donor.game,'gba/native/manifest')
   local spec=assert(manifest.layouts[reference.nativeMap]);check(spec.pair==reference.donor.tileset,'Sprout outdoor material family changed')
   local layout=assert(require('src.import.gba.native_pack').decodeMidLayout(assert(cacheRead(reference.donor.game..'/data/generated/gba/native/'..spec.file))))
   local position=reference.nativeCell
   check(layout.cells[position[2]*layout.width+position[1]+1].mid==reference.donor.id,'Sprout side material is not the actual reviewed outdoor face')
   local crop=love.image.newImageData(reference.w,reference.h)
   crop:paste(image,0,0,reference.srcX,reference.srcY,reference.w,reference.h)
   check(hash(crop:getString())==reference.stripPixelHash,'Sprout complete outdoor strip changed')
   for y=0,target[4]-1 do for x=0,target[3]-1 do
    equalPixel(actual,target[1]+x,target[2]+y,crop,x,y,'Sprout terrain strip differs from native outdoor material')
   end end
   strips[#strips+1]={role=reference.role,exact_native_gpu_pixels=true,target=target}
  end
  local door
  for _,w in ipairs(def.warps or{})do if w.destMap=='SPROUT_TOWER_1F'then door=w;break end end
  check(door and(door.x-r[1])*16+8==24 and(door.y-r[2]+1)*16==80,'Sprout original source entrance anchor changed')
  return {whole_approved_building_exact=true,rgba_sha256=hash(actual:getString()),native_features=features,
   outdoor_platform_strips=strips,source_warp_anchor={24,80},review_metadata_sha256=hash(bytes),
   image=encodePng(actual,game..'-sprout-native-material-gpu.png')}
 end
 local function verifyForest(game,def,map,art,renderer,FX)
  local checked,whole,boundary,arrows,cache=0,0,0,0,{}
  for _,row in ipairs(mappingRows('mappings/gen1_extended.lua'))do
   if row.game==game and row.map==def.id and row.tileset=='FOREST'and
    (row.role:find('forest_whole_broadleaf_tree_',1,true)or row.asset or row.role:find('forest_static_direction_marker_',1,true))then
    local key=tableString({base=row.base,donor=row.donor,parts=row.parts,asset=row.asset,assetFileHash=row.assetFileHash})
    if not cache[key]then cache[key]=nativeComposition(row)end
    local expected=cache[key]
    for pos,id in ipairs(def.blocks)do if id==row.id then
     local cx=(pos-1)%def.width*2+row.quadrant%2;local cy=math.floor((pos-1)/def.width)*2+math.floor(row.quadrant/2)
     if row.x==nil or(row.x==cx and row.y==cy)then
      local block=artAt(art,id,math.floor(cx/2),math.floor(cy/2));check(block and block.coverage[row.quadrant],'Forest reviewed feature was not published')
      for y=0,15 do for x=0,15 do
       equalPixel(block.image,row.quadrant%2*16+x,math.floor(row.quadrant/2)*16+y,expected,x,y,'Independent forest native feature changed')
       checked=checked+1
      end end
      if row.role:find('forest_whole_broadleaf_tree_',1,true)then whole=whole+1
      elseif row.asset then boundary=boundary+1 else arrows=arrows+1 end
     end
    end end
   end
  end
  check(whole>0 and whole%4==0 and boundary>0,'Forest whole tree neighborhoods were not exercised')
  local gx,gy,q,front
  for pos,id in ipairs(def.blocks)do if not gx then
   local block=artAt(art,id,(pos-1)%def.width,math.floor((pos-1)/def.width))
   if block then for quadrant=0,3 do
    local cx=(pos-1)%def.width*2+quadrant%2;local cy=math.floor((pos-1)/def.width)*2+math.floor(quadrant/2)
    if block.coverage[quadrant]and map:cellTile(cx,cy)==32 then
     gx,gy,q,front=cx*16,cy*16,quadrant,block.foreground;break
    end
   end end
  end end
  check(gx~=nil,'Forest native grass fixture is missing')
  local sheet=love.image.newImageData(16,80,'rgba8',assert(cacheRead('firered/data/generated/gba/field_effects/tall_grass.rgba')))
  local actor=capture(48,48,function()
   FX.clearTrueColor();renderer:drawWindow(gx-16,gy-16,48,48)
   G.setShader();G.setColor(1,0,1,1);G.rectangle('fill',16,16,16,16);G.setColor(1,1,1,1)
   renderer:drawStripRaw(gx,gy+8,gx+16,gy+16,gx-16,gy-16)
  end)
  local expected=love.image.newImageData(16,16);local cover,gaps=0,0
  for y=0,15 do for x=0,15 do
   local r,g,b,a=0,0,0,0
   if y>=8 then r,g,b,a=sheet:getPixel(x,64+y)end
   local fr,fg,fb,fa=front:getPixel(q%2*16+x,math.floor(q/2)*16+y)
   check(a==fa and(a==0 or(r==fr and g==fg and b==fb)),'Forest foot mask differs from complete native FR grass frame4')
   if a>0 then expected:setPixel(x,y,r,g,b,1);cover=cover+1
   else expected:setPixel(x,y,1,0,1,1);gaps=gaps+1 end
   equalPixel(actor,16+x,16+y,expected,x,y,'Forest native grass foot-cover GPU mismatch')
  end end
  check(cover>0 and gaps>0,'Forest actor proof lacks grass and open pixels')
  return {independent_native_pixels=checked,complete_native32px_trees=whole/4,compact_boundary_cells=boundary,
   static_native_direction_cues=arrows,native_grass_actor={covered=cover,visible_actor=gaps,
    image=encodePng(actor,game..'-'..def.id..'-native-grass-actor-gpu.png'),
    limits='Synthetic16px magenta actor; actual native FR frame4 feet mask and TileRenderer.drawStripRaw.'}}
 end

 -- Native Gen1 TileRenderer on real Red Pallet Town.
 GV.set('red');assetGame='red'
 local maps,sets=generated('red','maps'),generated('red','tilesets')
 local def=maps.PALLET_TOWN
 local Map=require('src.world.Map')
 local T=require('src.render.TileRenderer')
 local FX=require('src.render.PaletteFX')
 local map=Map.new(def,sets[def.tileset])
 local beforeCollision=snapshot(map,1)
 local beforeEvents=eventSnapshot(map)
 local renderer=T.new(map,{maps=maps,tilesets=sets})
 local function drawMap()
  FX.clearTrueColor();FX.setPass('world')
  renderer:drawWindow(0,0,def.width*32,def.height*32)
  FX.setPass(nil)
 end
 local before=capture(def.width*32,def.height*32,drawMap)
 local mod=startMod('red',1)
 local art=assert(mod.exports.state:replacements('red',def.tileset,def))
 check(mod.exports.state.rejected==0,'Red reviewed mappings unexpectedly rejected')
 local palletCoverage=requireCompletePallet(def,art)
 local after=capture(def.width*32,def.height*32,drawMap)
 local colorRects=FX.trueColorRects('world')
 check(#colorRects>0,'Gen1 native true-color opt-out collector stayed empty')
 for _,rect in ipairs(colorRects)do
  check(rect.colors==false and rect.w==16 and rect.h==16,
   'Reviewed quadrant reported a broader native palette opt-out rectangle')
 end
 local red={game='red',map=def.id,native_renderer='src.render.TileRenderer',
  before=encodePng(before,'red-pallet-native-gpu.png'),after=encodePng(after,'red-pallet-gen3-gpu.png'),
  accepted=mod.exports.state.accepted,collision_before=beforeCollision,
  native_palette_opt_out_rectangles=#colorRects,coverage=palletCoverage,
  events_before=beforeEvents,buildings=verifyBuildings(def,after,'red'),
  checked_donor_pixels=verifyPalletPixels(def,art,after,'red')}
 check(before:getString()~=after:getString(),'Red GPU background unchanged')
 local colors={}
 for id,block in pairs(art)do
  for q,included in pairs(block.coverage or {})do if included then
   local wx,wy=findCell(def,id,q)
   if wx then
    local sx,sy=q%2*16,math.floor(q/2)*16
    local expected=block.frames and block.frames[1] or block.image
    for y=0,15 do for x=0,15 do
     equalPixel(after,wx+x,wy+y,expected,sx+x,sy+y,'Red donor color/position lost')
     local r,g,b=after:getPixel(wx+x,wy+y);colors[math.floor(r*255+.5)..','..math.floor(g*255+.5)..','..math.floor(b*255+.5)]=true
    end end
   end
  end end
 end
 local n=0;for _ in pairs(colors)do n=n+1 end
 check(n>4,'Red donor colors collapsed to four shades');red.reviewed_color_count=n
 local px,py=findCell(def,77,1)
 check(px~=nil,'Actual Pallet legacy boundary-tree fixture missing')
 local boundaryTree=love.image.newImageData(love.filesystem.newFileData(
  assert(read(MOD..'/assets/third_party/j-treecko252/compact-tree.png')),'boundary-tree.png'))
 local Donor=assert(load(assert(read(MOD..'/lib/donor.lua'))))()
 local donor=Donor.new()
 local ground=donor:cell({game='emerald',tileset='general__petalburg',id=1}).under
 local transparent,opaque,translucent=0,0,0
 local expectedBoundary=love.image.newImageData(16,16)
 for y=0,15 do for x=0,15 do
  local r,g,b,alpha=boundaryTree:getPixel(x,y)
  local gr,gg,gb,ga=ground:getPixel(x,y)
  expectedBoundary:setPixel(x,y,r*alpha+gr*(1-alpha),g*alpha+gg*(1-alpha),
   b*alpha+gb*(1-alpha),alpha+ga*(1-alpha))
  equalPixel(after,px+x,py+y,expectedBoundary,x,y,'Boundary tree alpha failed to blend over Emerald ground')
  if alpha==0 then transparent=transparent+1
  elseif alpha<1 then translucent=translucent+1
  else opaque=opaque+1 end
 end end
 check(opaque>0 and transparent>0 and translucent>0,'Boundary tree alpha fixture is not meaningful')
 red.boundary_tree={transparent_ground_pixels=transparent,opaque_pixels=opaque,
  translucent_blended_pixels=translucent,
  credit='J-Treecko252; additional palette contributions credited to Zyxeion',
  source_cell='Legacy Pallet boundary cell 77:1; compact Gen3 tree confirmed by the user'}

 -- Actual native drawStripRaw over a synthetic magenta actor, with imported
 -- Emerald grass effect pixels. This isolates feet occlusion from NPC behavior.
 local gx,gy=findCell(def,11,0)
 check(gx~=nil,'Pallet tall-grass fixture missing')
 local front=art[11].foreground
 local actor=capture(48,48,function()
  renderer:drawWindow(gx-16,gy-16,48,48)
  G.setShader();G.setColor(1,0,1,1);G.rectangle('fill',16,16,16,16);G.setColor(1,1,1,1)
  renderer:drawStripRaw(gx,gy+8,gx+16,gy+16,gx-16,gy-16)
 end)
 local actorExpected=love.image.newImageData(16,16)
 local cover,gaps=0,0
 for y=0,15 do for x=0,15 do
  local r,g,b,a=front:getPixel(x,y)
  if y<8 or a==0 then actorExpected:setPixel(x,y,1,0,1,1);gaps=gaps+1
  else actorExpected:setPixel(x,y,r,g,b,1);cover=cover+1 end
  equalPixel(actor,16+x,16+y,actorExpected,x,y,'Native grass strip covered wrong actor pixels')
 end end
 check(cover>0 and gaps>0,'Grass foreground fixture lacks opaque and transparent samples')
 red.actor_foreground={image=encodePng(actor,'red-grass-actor-gpu.png'),covered=cover,visible_actor=gaps,
  actor_kind='synthetic16px magenta rectangle; real imported grass mask and real TileRenderer.drawStripRaw'}

 clock=17/60
 local nextWater=capture(def.width*32,def.height*32,drawMap)
 local animated=0
 for id,block in pairs(art)do if block.frames and type(block.bank)=='string' and block.bank:find('water',1,true) then
  for q,included in pairs(block.coverage)do if included then
   local wx,wy=findCell(def,id,q)
   if wx then
    for y=0,15 do for x=0,15 do equalPixel(nextWater,wx+x,wy+y,block.frames[2],q%2*16+x,math.floor(q/2)*16+y,'Water GPU phase17 mismatch')end end
    animated=animated+1
   end
  end end
 end end
 check(animated>0,'No actual Pallet coastal water sampled');red.animated_cells_sampled=animated
 red.water_phase17=encodePng(nextWater,'red-pallet-water-phase17-gpu.png')
 -- FR/LG flowers advance one tick later than water: frame 0 persists through
 -- tick 17, frame 1 begins at 18. Check all five frames and their loop using
 -- explicit native tick expectations rather than the adapter's calculation.
 local flowerBlocks={}
 for id,block in pairs(art)do
  if block.frames and block.bank=='flower' then
   check(#block.frames==5 and block.period==16/60 and block.offset==2/60,
    'FR/LG flower schedule changed')
   flowerBlocks[id]=block
  end
 end
 if next(flowerBlocks) then
  local phases={{0,1},{1,1},{2,1},{17,1},{18,2},{33,2},{34,3},
   {49,3},{50,4},{65,4},{66,5},{81,5},{82,1}}
  local flowerChecks={}
  for _,phase in ipairs(phases)do
   clock=phase[1]/60
   local frame=capture(def.width*32,def.height*32,drawMap)
   local sampled=0
   for id,block in pairs(flowerBlocks)do
    for q,included in pairs(block.coverage)do if included then
     local wx,wy=findCell(def,id,q)
     if wx then
      for y=0,15 do for x=0,15 do
       equalPixel(frame,wx+x,wy+y,block.frames[phase[2]],q%2*16+x,math.floor(q/2)*16+y,
        'Flower GPU tick '..phase[1]..' frame '..(phase[2]-1)..' mismatch')
      end end
      sampled=sampled+1
     end
    end end
   end
   check(sampled>0,'Flower animation fixture has no visible cells')
   flowerChecks[#flowerChecks+1]={tick=phase[1],frame=phase[2]-1,unique_mappings_sampled=sampled}
   if phase[1]==18 then red.flower_phase18=encodePng(frame,'red-pallet-flower-phase18-gpu.png') end
  end
  red.flower_animation={bank='flower',period_ticks=16,offset_ticks=2,frames=5,checkpoints=flowerChecks}
 end
 red.water_all_frames=verifyAnimationFrames(def,art,function()
  return capture(def.width*32,def.height*32,drawMap)
 end,'water',8,1)
 red.collision_after=snapshot(map,1)
 check(red.collision_after==beforeCollision,'Gen1 collision, layout or tileset mutated')
 red.events_after=eventSnapshot(map)
 check(red.events_after==beforeEvents,'Red source warps, signs or objects changed')
 report.performance={gen1=verifyWarmDraws(mod,function()return capture(def.width*32,def.height*32,drawMap)end,'Gen1')}
 report.customizations={}
 local flora=mod.exports.flora
 local catalog=assert(load(assert(read(MOD..'/lib/flora_catalog.lua'))))()
 for _,category in ipairs({'trees','flowers','grass'})do
  local entries=catalog[category]
  local atlas=capture(960,math.ceil(#entries/12)*104+32,function()
   G.clear(.09,.12,.15,1);G.print(category:upper()..' â€” USER SHEET DESIGNS AT NATIVE 16PX',12,8)
   for i,entry in ipairs(entries)do
    local sprite=flora:sprite(entry);local image=G.newImage(sprite);image:setFilter('nearest','nearest')
    local x=(i-1)%12*80+8;local y=math.floor((i-1)/12)*104+32
    G.setColor(.35,.65,.49,1);G.rectangle('fill',x,y,64,64);G.setColor(1,1,1,1)
    G.draw(image,x,y,0,4,4);G.print(tostring(i),x,y+67)
    check(sprite:getWidth()==16 and sprite:getHeight()==16,'Flora escaped native cell dimensions')
   end
  end)
  report.customizations[#report.customizations+1]={category=category,designs=#entries,
   contact_sheet=encodePng(atlas,'flora-'..category..'-contact.png')}
 end
 for _,selection in ipairs({
  {id='new-boundary',trees='natural-1-1'},
  {id='trees-mixed-only',trees='mixed'},
  {id='ripple-blue',water='ripple-blue'},
  {id='ripple-teal',water='ripple-teal'},
  {id='ripple-olive',water='ripple-olive'},
  {id='mixed',trees='mixed',flowers='mixed',grass='mixed',water='mixed'},
 })do
  for _,category in ipairs({'trees','flowers','grass','water'})do
   flora:select(category,selection[category] or 'default')
  end
  mod.exports.state:invalidate();clock=0
  local customArt=mod.exports.state:replacements('red',def.tileset,def)
  check(mod.exports.state.rejected==0,'Custom artwork rejected a guarded source mapping')
  local custom=capture(def.width*32,def.height*32,drawMap)
  local checked=verifyCoveredPixels(def,customArt,custom,'Pallet custom '..selection.id)
  check(snapshot(map,1)==beforeCollision and eventSnapshot(map)==beforeEvents,'Custom artwork changed Pallet gameplay')
  local groundChecked
  if selection.id=='trees-mixed-only' then groundChecked=verifyUnchangedGround(map,after,custom,'Pallet Mixed trees') end
  if selection.water and selection.water~='mixed' then
   clock=17/60
   check(capture(def.width*32,def.height*32,drawMap):getString()~=custom:getString(),'Selected ripple water did not animate')
  end
  if selection.id=='mixed' then
   local animation={encodePng(custom,'red-pallet-wind-1.png')}
   for i,t in ipairs({.21,.41,.71,1.06})do
    clock=t
    local moving=capture(def.width*32,def.height*32,drawMap)
    checked=checked+verifyCoveredPixels(def,customArt,moving,'Pallet independent wind '..i)
    check(moving:getString()~=custom:getString(),'Mixed flora animation did not move')
    animation[#animation+1]=encodePng(moving,'red-pallet-wind-'..(i+1)..'.png')
   end
   report.wind_frames=animation
   for _,rate in ipairs({0,.5,1,2})do
    for _,group in ipairs({'trees','flowers','grass','water'})do flora:speed(group,rate) end
    mod.exports.state:invalidate();clock=0
    local speedArt=mod.exports.state:replacements('red',def.tileset,def)
    local initial=capture(def.width*32,def.height*32,drawMap)
    for _,t in ipairs({.22,.72})do
     clock=t;local frame=capture(def.width*32,def.height*32,drawMap)
     checked=checked+verifyCoveredPixels(def,speedArt,frame,'Pallet speed '..rate)
     if rate==0 then check(frame:getString()==initial:getString(),'Off speed still animated') end
    end
   end
   for _,group in ipairs({'trees','flowers','grass','water'})do flora:speed(group,1) end
   mod.exports.state:invalidate()

  end
  local bytes=custom:getString()
  mod.exports.state:invalidate();clock=0
  mod.exports.state:replacements('red',def.tileset,def)
  check(capture(def.width*32,def.height*32,drawMap):getString()==bytes,'Mixed/custom artwork changed after rebuilding the map')
  report.customizations[#report.customizations+1]={id=selection.id,game='red',map=def.id,
   before=red.after,after=encodePng(custom,'red-pallet-'..selection.id..'-gpu.png'),coverage=palletCoverage,
   checked_gpu_pixels=checked,source_collision_events_unchanged=true,stable_after_map_rebuild=true,
   unchanged_walkable_ground_cells=groundChecked}
 end
 mod.exports.dispose();clock=0
 local restored=capture(def.width*32,def.height*32,drawMap)
 check(restored:getString()==before:getString(),'Gen1 cleanup did not restore native GPU background')
 red.cleanup_restored_native=true
 report.fixtures[#report.fixtures+1]=red

 -- The three Gen1 imports have independent source fingerprints and may have
 -- different art. Exercise each real imported renderer rather than inferring
 -- Blue/Yellow correctness from Red's aliases.
 for _,game in ipairs({'blue','yellow'})do
  GV.set(game);assetGame=game;clock=0
  local sourceMaps,sourceSets=generated(game,'maps'),generated(game,'tilesets')
  local sourceDef=sourceMaps.PALLET_TOWN
  local sourceMap=Map.new(sourceDef,sourceSets[sourceDef.tileset])
  local nativeRenderer=T.new(sourceMap,{maps=sourceMaps,tilesets=sourceSets})
  local function drawSource()
   FX.clearTrueColor();FX.setPass('world')
   nativeRenderer:drawWindow(0,0,sourceDef.width*32,sourceDef.height*32)
   FX.setPass(nil)
  end
  local mechanicsBefore,eventsBefore=snapshot(sourceMap,1),eventSnapshot(sourceMap)
  local native=capture(sourceDef.width*32,sourceDef.height*32,drawSource)
  local sourceMod=startMod(game,1)
  local sourceArt=assert(sourceMod.exports.state:replacements(game,sourceDef.tileset,sourceDef))
  check(sourceMod.exports.state.rejected==0,game..' Pallet mapping was rejected')
  local c=requireCompletePallet(sourceDef,sourceArt)
  local replaced=capture(sourceDef.width*32,sourceDef.height*32,drawSource)
  local checked=verifyPalletPixels(sourceDef,sourceArt,replaced,game)
  local fixture={game=game,map=sourceDef.id,native_renderer='src.render.TileRenderer',
   before=encodePng(native,game..'-pallet-native-gpu.png'),
   after=encodePng(replaced,game..'-pallet-gen3-gpu.png'),coverage=c,
   accepted=sourceMod.exports.state.accepted,checked_donor_pixels=checked,
   collision_before=mechanicsBefore,collision_after=snapshot(sourceMap,1),
   events_before=eventsBefore,events_after=eventSnapshot(sourceMap),
   buildings=verifyBuildings(sourceDef,replaced,game)}
  check(fixture.collision_before==fixture.collision_after,game..' source collision/layout changed')
  check(fixture.events_before==fixture.events_after,game..' source warps/signs/objects changed')
  sourceMod.exports.dispose()
  local again=capture(sourceDef.width*32,sourceDef.height*32,drawSource)
  check(again:getString()==native:getString(),game..' cleanup changed native GPU pixels')
  fixture.cleanup_restored_native=true
  report.fixtures[#report.fixtures+1]=fixture
 end

 -- Route1 has its own ledges and walkable stair openings. Validate every
 -- map pixel and original down-hop predicate on all three native imports.
 for _,game in ipairs({'red','blue','yellow'})do
  GV.set(game);assetGame=game;clock=0
  local sourceMaps,sourceSets=generated(game,'maps'),generated(game,'tilesets')
  local sourceDef=sourceMaps.ROUTE_1
  local sourceMap=Map.new(sourceDef,sourceSets[sourceDef.tileset])
  local routeRenderer=T.new(sourceMap,{maps=sourceMaps,tilesets=sourceSets})
  local function drawRoute()
   FX.clearTrueColor();FX.setPass('world')
   routeRenderer:drawWindow(0,0,sourceDef.width*32,sourceDef.height*32)
   FX.setPass(nil)
  end
  local mechanicsBefore,eventsBefore=snapshot(sourceMap,1),eventSnapshot(sourceMap)
  local native=capture(sourceDef.width*32,sourceDef.height*32,drawRoute)
  local routeMod=startMod(game,1)
  local routeArt=assert(routeMod.exports.state:replacements(game,sourceDef.tileset,sourceDef))
  check(routeMod.exports.state.rejected==0,game..' Route1 mapping was rejected')
  local c=coverage(sourceDef,routeArt)
  check(c.visible_cells==720 and c.replaced_occurrences==720 and c.preserved_native_occurrences==0,
   'Route1 must replace all720 background cells')
  local replaced=capture(sourceDef.width*32,sourceDef.height*32,drawRoute)
  local terrain=verifyGen1Terrain(game,sourceDef,sourceMap,replaced)
  check(terrain.ledge_occurrences==42 and terrain.walkable_stair_occurrences==2,'Route1 ledge/stair footprint changed')
  local fixture={game=game,map=sourceDef.id,native_renderer='src.render.TileRenderer',
   before=encodePng(native,game..'-route1-native-gpu.png'),
   after=encodePng(replaced,game..'-route1-gen3-gpu.png'),coverage=c,
   checked_donor_pixels=verifyPalletPixels(sourceDef,routeArt,replaced,game),outdoor=terrain,
   accepted=routeMod.exports.state.accepted,collision_before=mechanicsBefore,events_before=eventsBefore}
  fixture.flower_animation=verifyAnimationFrames(sourceDef,routeArt,function()
   return capture(sourceDef.width*32,sourceDef.height*32,drawRoute)
  end,'flower',5,2)
  fixture.plant_actors=verifyPlantActors(routeMod,sourceDef,sourceMap,function()return capture(sourceDef.width*32,sourceDef.height*32,drawRoute)end,routeRenderer)
  fixture.collision_after=snapshot(sourceMap,1);fixture.events_after=eventSnapshot(sourceMap)
  check(fixture.collision_before==fixture.collision_after,game..' Route1 source collision/layout changed')
  check(fixture.events_before==fixture.events_after,game..' Route1 source events changed')
  routeMod.exports.dispose();clock=0
  check(capture(sourceDef.width*32,sourceDef.height*32,drawRoute):getString()==native:getString(),
   game..' Route1 cleanup changed native pixels')
  fixture.cleanup_restored_native=true
  report.fixtures[#report.fixtures+1]=fixture
 end

 -- Optional map-only tree fixture uses the same real renderer and entry point.
 -- It also proves third-party alpha is composited over imported Emerald ground.
 local treeDef=maps.VIRIDIAN_CITY
 if treeDef then
  GV.set('red');assetGame='red';clock=0
  local treeMap=Map.new(treeDef,sets[treeDef.tileset])
  local treeCollision=snapshot(treeMap,1)
  local treeEvents=eventSnapshot(treeMap)
  local treeRenderer=T.new(treeMap,{maps=maps,tilesets=sets})
  local function drawTrees()
   FX.clearTrueColor();FX.setPass('world')
   treeRenderer:drawWindow(0,0,treeDef.width*32,treeDef.height*32)
   FX.setPass(nil)
  end
  local nativeTree=capture(treeDef.width*32,treeDef.height*32,drawTrees)
  local treeMod=startMod('red',1)
  local treeArt=assert(treeMod.exports.state:replacements('red',treeDef.tileset,treeDef))
  local replacedTree=capture(treeDef.width*32,treeDef.height*32,drawTrees)
  check(treeMod.exports.state.rejected==0,'Viridian reviewed mappings unexpectedly rejected')
  local tx,ty=findCell(treeDef,15,0)
  check(tx~=nil,'Viridian native tree-wall fixture missing')
  local compact=love.image.newImageData(love.filesystem.newFileData(
   assert(read(MOD..'/assets/third_party/j-treecko252/compact-tree.png')),'compact-tree.png'))
  local treeOpaque,treeTransparent,treeTranslucent=0,0,0
  local expectedTree=love.image.newImageData(16,16)
  for y=0,15 do for x=0,15 do
   local r,g,b,alpha=compact:getPixel(x,y)
   local gr,gg,gb,ga=ground:getPixel(x,y)
   expectedTree:setPixel(x,y,r*alpha+gr*(1-alpha),g*alpha+gg*(1-alpha),
    b*alpha+gb*(1-alpha),alpha+ga*(1-alpha))
   equalPixel(replacedTree,tx+x,ty+y,expectedTree,x,y,'Fan tree source alpha did not blend over Emerald ground')
   if alpha==0 then treeTransparent=treeTransparent+1
   elseif alpha<1 then treeTranslucent=treeTranslucent+1
   else treeOpaque=treeOpaque+1 end
  end end
  check(treeOpaque>0 and treeTransparent>0,'Fan tree alpha fixture lacks meaningful samples')
  local treeFixture={game='red',map=treeDef.id,native_renderer='src.render.TileRenderer',
   before=encodePng(nativeTree,'red-viridian-native-gpu.png'),
   after=encodePng(replacedTree,'red-viridian-gen3-gpu.png'),
   collision_before=treeCollision,collision_after=snapshot(treeMap,1),
   accepted=treeMod.exports.state.accepted,coverage=coverage(treeDef,treeArt),
   events_before=treeEvents,events_after=eventSnapshot(treeMap),
   checked_donor_pixels=verifyCoveredPixels(treeDef,treeArt,replacedTree,'red Viridian'),
   outdoor=verifyGen1Terrain('red',treeDef,treeMap,replacedTree),
   architecture=verifyPublicBuildings('red',treeDef,replacedTree),
   third_party_tree={opaque_pixels=treeOpaque,transparent_ground_pixels=treeTransparent,
    translucent_blended_pixels=treeTranslucent,
    credit='J-Treecko252; additional palette contributions credited to Zyxeion'}}
  check(treeFixture.collision_before==treeFixture.collision_after,'Viridian collision/layout changed')
  check(treeFixture.events_before==treeFixture.events_after,'Viridian source events changed')
  check(treeFixture.outdoor.pond_occurrences==24,'Viridian freshwater pond footprint changed')
  clock=129/60
  local pondLater=capture(treeDef.width*32,treeDef.height*32,drawTrees)
  treeFixture.static_pond_after_129_ticks=verifyGen1Terrain('red',treeDef,treeMap,pondLater).pond_occurrences
  clock=0
  treeMod.exports.dispose()
  local nativeAgain=capture(treeDef.width*32,treeDef.height*32,drawTrees)
  check(nativeAgain:getString()==nativeTree:getString(),'Viridian cleanup changed native GPU pixels')
  treeFixture.cleanup_restored_native=true
  report.fixtures[#report.fixtures+1]=treeFixture
 end

 -- Representative regional caves exercise the actual source maps and the
 -- matching reviewed FR/LG palette families. All CAVERN cells are reviewed.
 for _,spec in ipairs({{id='MT_MOON_1F',stem='mtmoon'},
  {id='MT_MOON_B2F',stem='mtmoonb2'},
  {id='SEAFOAM_ISLANDS_1F',stem='seafoam'},
  {id='DIGLETTS_CAVE_ROUTE_2',stem='diglett'}})do
  GV.set('red');assetGame='red';clock=0
  local caveDef=maps[spec.id];check(caveDef~=nil,'Approved cave fixture is absent: '..spec.id)
  local caveMap=Map.new(caveDef,sets[caveDef.tileset])
  local caveRenderer=T.new(caveMap,{maps=maps,tilesets=sets})
  local function drawCave()
   FX.clearTrueColor();FX.setPass('world')
   caveRenderer:drawWindow(0,0,caveDef.width*32,caveDef.height*32);FX.setPass(nil)
  end
  local mechanics,events=snapshot(caveMap,1),eventSnapshot(caveMap)
  local native=capture(caveDef.width*32,caveDef.height*32,drawCave)
  local caveMod=startMod('red',1)
  local caveArt=assert(caveMod.exports.state:replacements('red',caveDef.tileset,caveDef))
  check(caveMod.exports.state.rejected==0,'Cave mapping source/donor was rejected')
  local afterCave=capture(caveDef.width*32,caveDef.height*32,drawCave)
  local c=coverage(caveDef,caveArt)
  check(c.replaced_occurrences==c.visible_cells and c.preserved_native_occurrences==0,'Complete cave fixture has unresolved graphics')
  local fixture={game='red',map=caveDef.id,native_renderer='src.render.TileRenderer',coverage=c,
   before=encodePng(native,'red-'..spec.stem..'-native-gpu.png'),
   after=encodePng(afterCave,'red-'..spec.stem..'-gen3-gpu.png'),
   checked_donor_pixels=verifyCoveredPixels(caveDef,caveArt,afterCave,'red '..spec.id),
   accepted=caveMod.exports.state.accepted,collision_before=mechanics,collision_after=snapshot(caveMap,1),
   events_before=events,events_after=eventSnapshot(caveMap)}
  check(fixture.collision_before==fixture.collision_after,'Cave source collision/layout changed')
  check(fixture.events_before==fixture.events_after,'Cave source warps/events changed')
  caveMod.exports.dispose()
  check(capture(caveDef.width*32,caveDef.height*32,drawCave):getString()==native:getString(),
   'Cave cleanup did not restore original native GPU pixels')
  fixture.cleanup_restored_native=true;report.fixtures[#report.fixtures+1]=fixture
 end

 -- Additional Gen1 public architecture, a representative interior and the
 -- newly reviewed compact barrier/water cells on their actual source maps.
 for _,spec in ipairs({{id='CERULEAN_CITY',stem='cerulean',architecture=true},
  {id='VERMILION_CITY',stem='vermilion',animated_buildings=true},
  {id='ROUTE_12',stem='route12',animated_buildings=true},
  {id='REDS_HOUSE_1F',stem='redshouse',household=true,complete=true},
  {id='BLUES_HOUSE',stem='blueshouse',complete=true},
  {id='VIRIDIAN_FOREST',stem='viridianforest',forest=true,complete=true},
  {id='SAFARI_ZONE_WEST',stem='safariwest',forest=true},
  {id='VIRIDIAN_MART',stem='viridianmart'},
  {id='VICTORY_ROAD_1F',stem='victoryroad'},
  {id='SEAFOAM_ISLANDS_B4F',stem='seafoamb4',water=true}})do
  GV.set('red');assetGame='red';clock=0
  local def=assert(maps[spec.id]);local map=Map.new(def,sets[def.tileset])
  local renderer=T.new(map,{maps=maps,tilesets=sets})
  local function draw()
   return capture(def.width*32,def.height*32,function()
    FX.clearTrueColor();FX.setPass('world');renderer:drawWindow(0,0,def.width*32,def.height*32);FX.setPass(nil)
   end)
  end
  local mechanics,events=snapshot(map,1),eventSnapshot(map)
  local native=draw();local mod=startMod('red',1)
  local art=assert(mod.exports.state:replacements('red',def.tileset,def));local after=draw()
  check(mod.exports.state.rejected==0,'Additional Gen1 fixture rejected reviewed art')
  local fixture={game='red',map=def.id,native_renderer='src.render.TileRenderer',coverage=coverage(def,art),
   accepted=mod.exports.state.accepted,checked_donor_pixels=verifyCoveredPixels(def,art,after,'red '..def.id),
   before=encodePng(native,'red-'..spec.stem..'-native-gpu.png'),after=encodePng(after,'red-'..spec.stem..'-gen3-gpu.png'),
   collision_before=mechanics,collision_after=snapshot(map,1),events_before=events,events_after=eventSnapshot(map)}
  if spec.complete then check(fixture.coverage.replaced_occurrences==fixture.coverage.visible_cells,'Complete Gen1 fixture has unresolved background art')end
  if spec.architecture then
   fixture.architecture=verifyPublicBuildings('red',def,after)
   check(#fixture.architecture>0,'Kanto wide-Gym/public architecture was not exercised')
  end
  if spec.water then fixture.water_all_frames=verifyAnimationFrames(def,art,draw,'water',8,1)end
  if spec.forest then fixture.forest=verifyForest('red',def,map,art,renderer,FX)end
  if spec.id=='VIRIDIAN_FOREST' then
   for _,choice in ipairs({'default','mixed','johto-pine32'})do
    mod.exports.flora:select('big_trees',choice);mod.exports.state:invalidate();clock=0
    local selected=mod.exports.state:replacements('red',def.tileset,def)
    for _,t in ipairs({0,.36,.71,1.06})do
     clock=t;local frame=draw()
     verifyCoveredPixels(def,selected,frame,'Whole Big Trees '..choice)
     if t==.36 then encodePng(frame,'red-forest-big-'..choice..'-wind.png') end
    end
   end
   mod.exports.flora:select('big_trees','default');mod.exports.state:invalidate();clock=0
  end
  if spec.household then fixture.household=verifyHousehold('red',def,after)end
  if spec.animated_buildings then fixture.animated_buildings=verifyAnimatedBuildings('red',def,draw)end
  check(fixture.collision_before==fixture.collision_after and fixture.events_before==fixture.events_after,
   'Additional Gen1 fixture changed source collision/warps/events')
  mod.exports.dispose();clock=0
  check(draw():getString()==native:getString(),'Additional Gen1 cleanup failed to restore native pixels')
  fixture.cleanup_restored_native=true;report.fixtures[#report.fixtures+1]=fixture
 end

 -- Real Gold/Silver/Crystal World bake plus its actual drawAnimCells pass.
 local World=require('src.world.gen2.World')
 local Map2=require('src.world.gen2.Map')
 local function world2(game,mapId)
  local sourceMaps,sourceSets=generated(game,'maps'),generated(game,'tilesets')
  local def=sourceMaps[mapId];local map=Map2.new(def,sourceSets[def.tileset])
  local host={save={version=game,options={}},options={}}
  return setmetatable({game=host,maps=sourceMaps,tilesets=sourceSets,palettes=generated(game,'palettes'),
   roofs=generated(game,'roofs'),atlasCache={},mapImages={},animCells={},bgSets={},blockEdits={},daytime='DAY',
   flickerPhase=1,camera={x=0,y=0},animClock=0,animTimer=0,neighbors={},map=map,
   viewW=def.width*32,viewH=def.height*32},{__index=World}),map,def
 end
 local function drawWorld2(world)
  return capture(world.viewW,world.viewH,function()
   G.draw(world.mapImage,0,0);world:drawAnimCells(world.map.id,0,0,1)
  end)
 end
 local function verifyGen2Ladders(game,def,map,frame)
  local Permissions=require('src.world.gen2.Permissions')
  local proof={ascending=0,descending=0,native_glyph_pixels_checked=0,background_pixels_checked=0,instances={}}
  for _,row in ipairs(mappingRows('mappings/gen2_caves.lua'))do
   if row.game==game and row.map==def.id and(row.role=='cave_ascending_ladder'or row.role=='cave_descending_ladder')then
    local ascending=row.role=='cave_ascending_ladder';local glyphRef=assert(row.parts[1].donor)
    local cell,why=sourceDecoder():cell(glyphRef);check(cell~=nil,tostring(why))
    local glyph=nativeCellImage(glyphRef);local base=nativeCellImage(row.base)
    local floorColors={}
    if not ascending then
     check(glyphRef.game=='firered'and glyphRef.id==645,'Descending ladder no longer uses the reviewed full native645 glyph')
     local bytes=assert(cacheRead('firered/data/generated/gba/native/'..glyphRef.tileset..'/palettes.bin'))
     local pack=require('src.import.gba.native_pack')
     local palettes=pack.palsToRgb8(assert(pack.decodePalettes(bytes)))
     for index=2,4 do local c=palettes[9][index];floorColors[c[1]..':'..c[2]..':'..c[3]]=true end
    else
     check(glyphRef.game=='emerald'and glyphRef.id==574 and cell.mid,'Ascending ladder lost its whole native574 middle layer')
     check(hash(cell.mid:getString())==row.parts[1].layerHashes.mid,'Ascending ladder native layer fingerprint changed')
    end
    local function isGlyph(x,y)
     if ascending then local _,_,_,a=cell.mid:getPixel(x,y);return a>0 end
     local r,g,b=glyph:getPixel(x,y)
     return not floorColors[math.floor(r*255+.5)..':'..math.floor(g*255+.5)..':'..math.floor(b*255+.5)]
    end
    local glyphCount=0;for y=0,15 do for x=0,15 do if isGlyph(x,y)then glyphCount=glyphCount+1 end end end
    check(glyphCount==(ascending and 165 or 227),'Independent complete native ladder glyph mask changed')
    for pos,id in ipairs(def.blocks)do if id==row.id then
     local cx=(pos-1)%def.width*2+row.quadrant%2
     local cy=math.floor((pos-1)/def.width)*2+math.floor(row.quadrant/2)
     if row.x==nil or(row.x==cx and row.y==cy)then
      local coll=map:cellCollision(cx,cy);local warp=map:warpAtCell(cx,cy)
      check(coll==row.sourceCollision and Permissions.isWarpCollision(coll)and warp~=nil,
       'Native source ladder collision or warp link changed')
      local warpDef=warp.def or warp;local expectedWarp
      for _,sourceWarp in ipairs(row.sourceWarps or {})do
       if sourceWarp.x==cx and sourceWarp.y==cy then expectedWarp=sourceWarp;break end
      end
      check(expectedWarp and warpDef.destMap==expectedWarp.destMap and warpDef.destWarp==expectedWarp.destWarp,
       'Native ladder destination differs from its independently reviewed source link')
      for y=0,15 do for x=0,15 do
       if isGlyph(x,y)then
        equalPixel(frame,cx*16+x,cy*16+y,ascending and cell.mid or glyph,x,y,'Complete native ladder/rim pixel changed in the real host renderer')
        proof.native_glyph_pixels_checked=proof.native_glyph_pixels_checked+1
       else
        equalPixel(frame,cx*16+x,cy*16+y,base,x,y,'Ladder outside floor differs from the approved regional plane')
        proof.background_pixels_checked=proof.background_pixels_checked+1
       end
      end end
      local direction=ascending and'ascending'or'descending';proof[direction]=proof[direction]+1
      proof.instances[#proof.instances+1]={cell={cx,cy},direction=direction,source_collision=coll,
       original_destination=warpDef.destMap,original_destination_warp=warpDef.destWarp,complete_native_glyph_pixels=glyphCount,
       outside_pixels_match_regional_plane=true,
       glyph_mask=ascending and'original native mid alpha'or'original palette9 glyph; only floor indexes2..4 excluded'}
     end
    end end
   end
  end
  check(proof.ascending>0 and proof.descending>0,'Requested cave fixture did not exercise both complete ladder directions')
  return proof
 end
 local newBarkNativeSources={}
 local function verifyNewBarkBuildings(game,def,art,frame)
  local reviewRoot=MOD..'/../.work/tileshift-newbark-buildings/'
  local review=Json.decode(assert(read(reviewRoot..'newbark-native-building-prototypes.json')))
  check(review.status=='reviewed_buildings_activated' and review.production_rows==168,
   'NewBark architecture review is incomplete')
  local models={};for _,candidate in ipairs(review.candidates)do models[candidate.id]=candidate end
  local function crop(image,r)
   local out=love.image.newImageData(r[3],r[4]);out:paste(image,0,0,r[1],r[2],r[3],r[4]);return out
  end
  local function nativeSource(candidate)
   if newBarkNativeSources[candidate.id] then return newBarkNativeSources[candidate.id] end
   local n=candidate.native
   local manifest=generated(n.game,'gba/native/manifest')
   local spec=assert(manifest.layouts[n.map],'Original native building layout is missing')
   check(spec.pair==n.pair,'Native building tileset pair changed')
   local relative=n.game..'/data/generated/gba/native/'..spec.file
   check(hash(assert(read(CACHE..'/'..relative)))==n.layout_file_sha256,'Native building layout file fingerprint changed')
   local layout,why=require('src.import.gba.native_pack').decodeMidLayout(assert(cacheRead(relative)))
   check(layout~=nil,'Original native building layout could not be decoded: '..tostring(why))
   local r=n.rect_cells;local textures,mids={},{}
   for y=0,r[4]-1 do for x=0,r[3]-1 do
    local mid=assert(layout.cells[(r[2]+y)*layout.width+r[1]+x+1]).mid
    mids[y*r[3]+x+1]=mid
    if not textures[mid] then
     local image=nativeCellImage({game=n.game,tileset=n.pair,id=mid})
     textures[mid]=G.newImage(image);textures[mid]:setFilter('nearest','nearest')
    end
   end end
   local image=capture(r[3]*16,r[4]*16,function()
    for y=0,r[4]-1 do for x=0,r[3]-1 do G.draw(textures[mids[y*r[3]+x+1]],x*16,y*16)end end
   end)
   for _,texture in pairs(textures)do texture:release()end
   check(hash(image:getString())==n.source_pixel_sha256,'Whole original native building GPU pixels changed')
   -- Some unrelated Gen3 elevator warps contain unresolved nil destinations.
   -- Decode only this original map's literal table with the safe data parser.
   local warpSource=assert(cacheRead(n.game..'/data/generated/gba/warps.lua'))
   local warpTable=assert(warpSource:match('\n  '..n.map..' = ({.-\n  })'),'Original native warp map is missing')
   local warps=assert(Serializer.decode('return '..warpTable,{allowArray=true,allowComments=true}))
   local door
   for _,warp in ipairs(warps)do
    if warp.destMap==n.destination then check(not door,'Duplicate native reference entrance');door=warp end
   end
   check(door and (door.x-r[1])*16+8==n.door_anchor[1]
    and (door.y-r[2]+1)*16==n.door_anchor[2],'Original native reference door anchor changed')
   local result={image=image,readback=encodePng(image,candidate.id..'-newbark-native-reference-gpu.png'),
    game=n.game,map=n.map,layout_file_sha256=n.layout_file_sha256}
   newBarkNativeSources[candidate.id]=result;return result
  end
  local function roofProof(candidate,actual,source)
   local reviewed=assert(candidate.roof_background)
   local base=nativeCellImage(candidate.base)
   local roofHeight=(reviewed.native_roof_pixels_preserved+reviewed.empty_pixels_checked)/candidate.size_px[1]
   check(roofHeight==math.floor(roofHeight),'Native roof mask area is not rectangular')
   local empty,opaque,selected,seen,holes=0,0,0,{},{}
   for _,part in ipairs(candidate.parts)do
    local tx,ty=part.target_xy[1],part.target_xy[2]
    if ty<roofHeight then
     local original=nativeCellImage(part.donor)
     local layer
     if part.layers then
      check(#part.layers==1 and part.layers[1]=='over','NewBark roof uses an unexpected native layer')
      local cell,why=sourceDecoder():cell(part.donor);check(cell~=nil,tostring(why));layer=cell.over
      check(hash(layer:getString())==part.layerHashes.over,'NewBark original roof alpha-layer hash changed')
      selected=selected+1
     end
     for y=0,part.h-1 do for x=0,part.w-1 do
      local px,py=tx+x,ty+y;local sx,sy=part.srcX+x,part.srcY+y
      check(py<roofHeight and not seen[px..':'..py],'NewBark roof parts overlap or escape the approved mask')
      seen[px..':'..py]=true
      equalPixel(original,sx,sy,source.image,part.native_source_rect[1]+x,part.native_source_rect[2]+y,
       'Roof part differs from the original complete native building')
      local a=1;if layer then local lr,lg,lb;lr,lg,lb,a=layer:getPixel(sx,sy)end
      if a==0 then
       equalPixel(actual,px,py,base,px%16,py%16,'NewBark empty roof corner differs from the adjacent Emerald ground')
       holes[px..':'..py]=true;empty=empty+1
      else
       check(a==1,'NewBark native roof contains unexpected semi-transparency')
       equalPixel(actual,px,py,original,sx,sy,'NewBark opaque native roof or eave pixel changed')
       opaque=opaque+1
      end
     end end
    end
   end
   local expectedSelected={lab=37,player=21,ordinary=8}
   check(selected==expectedSelected[candidate.id],'NewBark selected roof part count changed')
   check(empty==reviewed.empty_pixels_checked and opaque==reviewed.native_roof_pixels_preserved,
    'NewBark independent native roof mask count changed')
   check(reviewed.native_roof_pixel_differences==0 and reviewed.all_empty_pixels_exact_local_ground,
    'Approved NewBark roof review permits altered native pixels')
   check(#reviewed.empty_pixel_positions==empty,'NewBark roof empty-position count changed')
   for _,pos in ipairs(reviewed.empty_pixel_positions)do
    check(holes[pos[1]..':'..pos[2]],'NewBark reviewed roof hole disagrees with native alpha')
   end
   return {selected_native_over_parts=selected,opaque_roof_pixels_unchanged=opaque,
    empty_pixels_match_emerald_ground=empty,roof_height_px=roofHeight,ground_donor=candidate.base}
  end
  local proofs,occurrences,baseHashes={}, {},{}
  for id,block in pairs(art)do if block.positions then baseHashes[id]=hash(block.image:getString())end end
  for _,record in ipairs(review.source_records)do if record.game==game then
   local kind=models[record.building] and record.building or 'ordinary';local candidate=assert(models[kind])
   local r=record.source_rect_cells
   check(r[3]*16==candidate.size_px[1] and r[4]*16==candidate.size_px[2],'NewBark source building footprint changed')
   local actual=crop(frame,{r[1]*16,r[2]*16,r[3]*16,r[4]*16})
   local expected=love.image.newImageData(love.filesystem.newFileData(
    assert(read(reviewRoot..kind..'-compact-prototype.png')),kind..'.png'))
   check(hash(expected:getString())==candidate.pixel_sha256,'Approved NewBark prototype fingerprint changed')
   check(actual:getString()==expected:getString(),game..' '..record.building..' native GPU differs from the approved prototype')
   local door
   for _,warp in ipairs(def.warps or {})do if warp.destMap==record.destination then
    check(not door,'Duplicate NewBark building warp');door=warp
   end end
   check(door and door.x==record.door_map_cell[1] and door.y==record.door_map_cell[2],
    'NewBark original building warp moved')
   local anchor={(door.x-r[1])*16+8,(door.y-r[2]+1)*16}
   check(anchor[1]==record.door_anchor_px[1] and anchor[2]==record.door_anchor_px[2]
    and anchor[1]==candidate.door_bottom_anchor_px[1] and anchor[2]==candidate.door_bottom_anchor_px[2],
    'NewBark original building entrance anchor changed')
   local source=nativeSource(candidate);local features={};local entrance,windows,dish=0,0,0
   for _,feature in ipairs(candidate.features_checked)do
    local sr,tr=feature.source_rect_xywh,feature.target_rect_xywh
    check(sr[3]==tr[3] and sr[4]==tr[4],'NewBark native feature was scaled')
    local targetCrop=crop(actual,tr);local sourceCrop=crop(source.image,sr)
    check(targetCrop:getString()==sourceCrop:getString(),game..' '..record.building..' '..feature.feature..' has clipped or changed native pixels')
    local label=feature.feature:lower()
    if label:find('entrance',1,true)then
     check((kind=='ordinary' and tr[3]==16 and tr[4]==17)or(kind~='ordinary' and tr[3]==32 and tr[4]==24),
      'NewBark entrance proof omits its complete native frame');entrance=entrance+1
    end
    if label:find('window',1,true)then windows=windows+1 end
    if label:find('satellite',1,true)then
     check(tr[3]==32 and tr[4]==32,'NewBark lab proof clips the whole native dish');dish=dish+1
    end
    features[#features+1]={feature=feature.feature,source_rect_xywh=sr,target_rect_xywh=tr,
     exact_native_gpu_pixels=true,rgba_sha256=hash(targetCrop:getString())}
   end
   check(entrance==1 and windows==(kind=='lab' and 2 or 1) and (kind~='lab' or dish==1),
    'NewBark building proof omits a complete native entrance, window or dish')
   for y=0,r[4]-1 do for x=0,r[3]-1 do
    local cx,cy=r[1]+x,r[2]+y;local bx,by=math.floor(cx/2),math.floor(cy/2)
    local id=def.blocks[by*def.width+bx+1];local q=cy%2*2+cx%2
    local key=id..':'..q;local block=artAt(art,id,bx,by)
    check(block and block~=art[id] and art[id].positions[bx..':'..by]==block,
     'NewBark positioned building resolved generic or another building artwork')
    occurrences[key]=occurrences[key] or {}
    occurrences[key][record.building]={block=block,bx=bx,by=by,
     pixels=crop(actual,{x*16,y*16,16,16}):getString()}
   end end
   proofs[#proofs+1]={id=record.building,kind=kind,map_rect_cells=r,door_destination=door.destMap,
    door_bottom_anchor_px=anchor,exact_approved_native_pixels=true,rgba_sha256=hash(actual:getString()),
    native_features=features,native_source_gpu=source.readback,roof_background=roofProof(candidate,actual,source),
    image=encodePng(actual,game..'-newbark-'..record.building..'-gpu.png')}
  end end
  check(#proofs==4,'NewBark proof must cover all four buildings')
  local shared,different,keys=0,0,{}
  for _,key in ipairs(review.required_position_scope.source_shared_keys)do
   local name=key[1]..':'..key[2];local pair=assert(occurrences[name]);local lab,player=pair.lab,pair.player
   check(lab and player and lab.block~=player.block and (lab.bx~=player.bx or lab.by~=player.by),
    'Lab/player shared source roof key bled across its position scope')
   local pixelsDiffer=lab.pixels~=player.pixels;if pixelsDiffer then different=different+1 end
   keys[#keys+1]={source_id=key[1],quadrant=key[2],lab_block={lab.bx,lab.by},player_block={player.bx,player.by},
    distinct_position_records=true,distinct_gpu_pixels=pixelsDiffer};shared=shared+1
  end
  check(shared==12 and different>0,'NewBark GPU proof did not exercise distinct roofs sharing source keys')
  for id,beforeHash in pairs(baseHashes)do
   check(hash(art[id].image:getString())==beforeHash,'Positioned drawing mutated the generic source-key artwork')
  end
  local town
  for _,candidate in ipairs(review.town_candidates)do if candidate.game==game then town=candidate end end
  check(town and town.target_covered_cells==360 and hash(frame:getString())==town.candidate_pixel_sha256,
   'Full NewBark GPU background differs from the independently reviewed 360-cell scene')
  return {buildings=proofs,shared_roof_keys={checked=shared,distinct_gpu_graphics=different,keys=keys,
   generic_art_unchanged=true},full_scene_exact=true,rgba_sha256=hash(frame:getString())}
 end
 local function verifyGen2Objects(game,def,map,frame)
  local proof={native_tree_pairs=0,native_objects=0,native_pixels_checked=0}
  for _,row in ipairs(mappingRows('mappings/gen2_outdoor.lua'))do
   if row.game==game and (row.map==nil or row.map==def.id) then
    local nativeObject=false
    if row.donor and row.donor.kind=='field_object' then nativeObject=true end
    for _,part in ipairs(row.parts or {})do if part.donor.kind=='field_object' then nativeObject=true end end
    if row.role=='dense_conifer_crown' or nativeObject then
     local expected=nativeComposition(row)
     for pos,id in ipairs(def.blocks)do if id==row.id then
      local cx=(pos-1)%def.width*2+row.quadrant%2
      local cy=math.floor((pos-1)/def.width)*2+math.floor(row.quadrant/2)
      for y=0,15 do for x=0,15 do
       equalPixel(frame,cx*16+x,cy*16+y,expected,x,y,'Native Gen2 tree/object GPU pixels changed')
       proof.native_pixels_checked=proof.native_pixels_checked+1
      end end
      if row.role=='dense_conifer_crown' then
       local trunk=nativeCellImage({game='emerald',tileset='general__petalburg',id=22,
        hash='c30bbf65a789a158df93d106697d0a9487b1e7c4ebdac76837d89f36c6eb8456'})
       for y=0,15 do for x=0,15 do
        equalPixel(frame,cx*16+x,(cy+1)*16+y,trunk,x,y,'Native16x32 tree trunk shifted, clipped or scaled')
        proof.native_pixels_checked=proof.native_pixels_checked+1
       end end
       check(map:cellCollision(cx,cy)==7 and map:cellCollision(cx,cy+1)==7,'Native tree blocking geometry changed')
       proof.native_tree_pairs=proof.native_tree_pairs+1
      else proof.native_objects=proof.native_objects+1 end
     end end
    end
   end
  end
  return proof
 end
 local function verifyHeadbutt(game,world,map,def,unshaken)
  local Permissions=require('src.world.gen2.Permissions')
  local FieldMoves=require('src.world.gen2.FieldMoves')
  local positions,alpha={},{transparent=0,opaque=0,translucent=0}
  local expectedSource
  for _,row in ipairs(mappingRows('mappings/gen2_outdoor.lua'))do
   if row.game==game and row.map==def.id and row.role=='headbutt_small_tree' then
    check(row.base and row.base.game=='emerald' and row.base.id==1,'Headbutt tree ground donor changed')
    check(#row.parts==1 and row.parts[1].donor.game=='emerald' and row.parts[1].donor.id==82
     and row.parts[1].donor.kind=='field_object' and row.parts[1].donor.frame==0,
     'Approved Emerald82 Headbutt visual source changed')
    local expected=nativeComposition(row)
    if not expectedSource then
     expectedSource=row.parts[1].donor
     local original,why=sourceDecoder():cell(expectedSource);check(original~=nil,tostring(why))
     for y=0,15 do for x=0,15 do
      local _,_,_,a=original.under:getPixel(x,y)
      if a==0 then alpha.transparent=alpha.transparent+1
      elseif a==1 then alpha.opaque=alpha.opaque+1 else alpha.translucent=alpha.translucent+1 end
     end end
    end
    for pos,id in ipairs(def.blocks)do if id==row.id then
     local cx=(pos-1)%def.width*2+row.quadrant%2
     local cy=math.floor((pos-1)/def.width)*2+math.floor(row.quadrant/2)
     local collision=map:cellCollision(cx,cy)
     check(collision==0x15 and Permissions.isHeadbuttTree(collision) and World.isHeadbuttTree(collision),
      'Small tree lost its native Headbutt-tree classification')
     check(not Permissions.isCutTree(collision) and not map:isWalkableCell(cx,cy),
      'Headbutt tree inherited donor Cut or walkable behavior')
     local action=FieldMoves.headbuttFromMenu({facingColl=collision})
     check(action.ok and action.action=='headbutt','Native Headbutt field-move eligibility changed')
     for y=0,15 do for x=0,15 do
      equalPixel(unshaken,cx*16+x,cy*16+y,expected,x,y,'Emerald82 alpha/ground composition changed')
     end end
     positions[#positions+1]={x=cx,y=cy,expected=expected}
    end end
   end
  end
  check(#positions==10 and alpha.transparent>0 and alpha.opaque>0,'Approved NewBark Headbutt footprint or meaningful alpha is missing')
  local collisionBefore,eventsBefore=snapshot(map,2),eventSnapshot(map)
  local savedText,savedSound,savedEncounter=world.showText,world.playSfx,world.tryHeadbutt
  local textCalls,soundCalls,encounterCalls=0,0,0
  world.showText=function(self,body,onDone)textCalls=textCalls+1;if onDone then onDone()end end
  world.playSfx=function()soundCalls=soundCalls+1 end
  local target=positions[1]
  world.tryHeadbutt=function(self,x,y)
   check(x==target.x and y==target.y,'Native Headbutt encounter hook received a different tree')
   encounterCalls=encounterCalls+1;return 'nothing'
  end
  world:runHeadbutt(target.x,target.y,{nickname='GPU fixture'})
  check(world.game.stringBuffer=='GPU fixture','Native Headbutt nickname preparation changed')
  check(world.headbutt and world.headbutt.timer==32 and world.shake and world.shake.left==32
   and world.shake.amplitude==2,'Native Headbutt did not start its32frame whole-frame shake')
  local phases,shakeImages,final={},{},nil
  clock=0
  for tick=1,33 do
   if world.shake then world:updateShake()end
   world:updateHeadbutt()
   local phase=world.shake and world.shake.phase or 0
   world.camera.y=phase
   local image=capture(world.viewW,world.viewH,function()world:drawGround(1)end)
   for _,tree in ipairs(positions)do for y=0,15 do for x=0,15 do
    equalPixel(image,tree.x*16+x,tree.y*16+y-phase,tree.expected,x,y,
     'Native Headbutt ground shake erased, shifted or recolored replacement tree art')
   end end end
   phases[phase]=true
   local phaseKey=tostring(phase)
   if not shakeImages[phaseKey] then
    shakeImages[phaseKey]=encodePng(image,game..'-headbutt-shake-'..phase..'-gpu.png')
   end
   final=image
  end
  world.camera.y=0
  check(phases[-2] and phases[2] and phases[0],'Native Headbutt shake phases were not exercised')
  check(world.headbutt==nil and world.shake==nil and encounterCalls==1 and soundCalls==1 and textCalls==2,
   'Native Headbutt shake/encounter sequence did not complete normally')
  check(final:getString()==unshaken:getString(),'Headbutt did not restore the unshifted custom background')
  check(snapshot(map,2)==collisionBefore and eventSnapshot(map)==eventsBefore,'Headbutt changed source collision/layout/events')
  world.showText,world.playSfx,world.tryHeadbutt=savedText,savedSound,savedEncounter
  return {source_collision=0x15,native_headbutt_classification=true,native_cut_classification=false,
   visible_trees=#positions,donor=expectedSource,alpha_pixels=alpha,
   native_methods={'runHeadbutt','earthquake','updateShake','updateHeadbutt','drawGround'},
   shake_frames=32,shake_amplitude=2,phases={-2,0,2},shake_images=shakeImages,
   source_collision_events_unchanged=true,custom_art_preserved_during_shake=true,encounter_hook_calls=encounterCalls,
   limits='Private native methods; text is acknowledged immediately, audio is recorded, encounter outcome is stubbed to nothing. No full gameplay/UI or wild battle simulation.'}
 end
 for _,game in ipairs({'gold','silver','crystal'})do
  GV.set(game);assetGame=game;clock=0
  local world,map2,def2=world2(game,'NEW_BARK_TOWN')
  local mechanics,events=snapshot(map2,2),eventSnapshot(map2)
  local nativeCanvas=assert(world:bakeMapImage(map2,'DAY',1),'Native NewBark map bake failed')
  local native=nativeCanvas:newImageData()
  local mod2=startMod(game,2,world)
  world.mapImage=world:imageFor(map2.id)
  local art=assert(mod2.exports.state:replacements(game,def2.tileset,def2))
  local after2=drawWorld2(world)
  check(mod2.exports.state.rejected==0,'NewBark reviewed mapping rejected')
  local c=coverage(def2,art);check(c.visible_cells==360 and c.replaced_occurrences==360,'Complete NewBark background must replace360/360 cells')
  local fixture={game=game,map=def2.id,native_renderer='src.world.gen2.World:bakeMapImage + drawAnimCells',
   before=encodePng(native,game..'-newbark-native-gpu.png'),after=encodePng(after2,game..'-newbark-gen3-gpu.png'),
   accepted=mod2.exports.state.accepted,checked_donor_pixels=verifyCoveredPixels(def2,art,after2,game),coverage=c,
   architecture=verifyNewBarkBuildings(game,def2,art,after2),
   native_palette_shader_available=require('src.render.GbcPalette').available(),
   native_trees=verifyGen2Objects(game,def2,map2,after2),collision_before=mechanics,events_before=events}
  check(fixture.native_trees.native_tree_pairs>0,'No native16x32 NewBark tree pair was sampled')
  check(fixture.native_palette_shader_available,'Native Gen2 palette shader did not compile')
  fixture.flower_all_frames=verifyAnimationFrames(def2,art,function()return drawWorld2(world)end,'general_flower',4,0)
  fixture.water_all_frames=verifyAnimationFrames(def2,art,function()return drawWorld2(world)end,'general_water',8,1)
  fixture.warm_draws=verifyWarmDraws(mod2,function()return drawWorld2(world)end,game)
  fixture.headbutt=verifyHeadbutt(game,world,map2,def2,after2)
  fixture.plant_actors=verifyPlantActors(mod2,def2,map2,function()return drawWorld2(world)end,nil,world)
  fixture.collision_after=snapshot(map2,2);fixture.events_after=eventSnapshot(map2)
  check(fixture.collision_before==fixture.collision_after,'NewBark source collision/layout changed')
  check(fixture.events_before==fixture.events_after,'NewBark source events changed')
  mod2.exports.dispose();clock=0
  check(world:bakeMapImage(map2,'DAY',1):newImageData():getString()==native:getString(),
   'Gen2 cleanup did not restore native GPU bake')
  fixture.cleanup_restored_native=true;report.fixtures[#report.fixtures+1]=fixture
 end

 -- Public Johto/Kanto architecture, a representative interior floor, and
 -- complete up/down glyphs on their actual Union Cave/Ice Path source maps.
 for _,spec in ipairs({{id='AZALEA_TOWN',stem='azalea',complete=true},
  {game='gold',id='AZALEA_TOWN',stem='azalea',complete=true},
  {game='silver',id='AZALEA_TOWN',stem='azalea',complete=true},
  {id='CHERRYGROVE_CITY',stem='cherrygrove',architecture=true,complete=true,water=true},
  {game='gold',id='CHERRYGROVE_CITY',stem='cherrygrove',architecture=true,complete=true,water=true},
  {game='silver',id='CHERRYGROVE_CITY',stem='cherrygrove',architecture=true,complete=true,water=true},
  {id='ILEX_FOREST',stem='ilex'},
  {game='gold',id='ILEX_FOREST',stem='ilex'},
  {game='silver',id='ILEX_FOREST',stem='ilex'},
  {id='VIOLET_CITY',stem='violet',architecture=true,complete=true},
  {game='gold',id='VIOLET_CITY',stem='violet',architecture=true,complete=true},
  {game='silver',id='VIOLET_CITY',stem='violet',architecture=true,complete=true},
  {id='CERULEAN_CITY',stem='cerulean',architecture=true},
  {id='VERMILION_CITY',stem='vermilion',animated_buildings=true},
  {id='ROUTE_12',stem='route12',animated_buildings=true},
  {id='ELMS_LAB',stem='elmslab'},
  {id='UNION_CAVE_B1F',stem='unioncave',ladders=true},
  {id='ICE_PATH_B1F',stem='icepath',ladders=true}})do
  local game=spec.game or'crystal'
  GV.set(game);assetGame=game;clock=0
  local world,map,def=world2(game,spec.id);world.clockHour=12
  world.daytime=require('src.world.gen2.Palettes').daytimeFor(def,12,false)
  check(world.daytime~='DARK','Additional lit GPU fixture unexpectedly requires native Flash')
  local function draw()return drawWorld2(world)end
  world.mapImage=world:imageFor(map.id)
  local native=draw();local mechanics,events=snapshot(map,2),eventSnapshot(map)
  local mod=startMod(game,2,world);world.mapImage=world:imageFor(map.id)
  local art=assert(mod.exports.state:replacements(game,def.tileset,def));local after=draw()
  check(mod.exports.state.rejected==0,'Additional Gen2 fixture rejected reviewed art')
  local fixture={game=game,map=def.id,native_renderer='src.world.gen2.World:imageFor + drawAnimCells',
   coverage=coverage(def,art),accepted=mod.exports.state.accepted,source_daytime=world.daytime,source_animation_timer=0,
   before=encodePng(native,game..'-'..spec.stem..'-native-gpu.png'),after=encodePng(after,game..'-'..spec.stem..'-gen3-gpu.png'),
   checked_donor_pixels=verifyCoveredPixels(def,art,after,game..' '..def.id),
   collision_before=mechanics,collision_after=snapshot(map,2),events_before=events,events_after=eventSnapshot(map)}
  if spec.architecture then
   fixture.architecture=verifyPublicBuildings(game,def,after)
   check(#fixture.architecture>0,'Public architecture GPU fixture contains no reviewed buildings')
  end
  if spec.complete then check(fixture.coverage.replaced_occurrences==fixture.coverage.visible_cells,'Complete Violet fixture has unresolved art')end
  if spec.ladders then fixture.complete_native_ladders=verifyGen2Ladders(game,def,map,after)end
  if spec.id=='AZALEA_TOWN'then fixture.well=verifyAzaleaWell(game,def,after)end
  if spec.id=='VIOLET_CITY'then fixture.sprout=verifySprout(game,def,after)end
  if spec.water then fixture.water_all_frames=verifyAnimationFrames(def,art,draw,'general_water',8,1)end
  if spec.id=='ILEX_FOREST' then
   for _,choice in ipairs({'default','mixed','johto-pine32'})do
    mod.exports.flora:select('big_trees',choice);mod.exports.state:invalidate();clock=0;world.mapImage=world:imageFor(map.id)
    local selected=mod.exports.state:replacements(game,def.tileset,def)
    for _,t in ipairs({0,.36,.71,1.06})do
     clock=t;verifyCoveredPixels(def,selected,draw(),game..' complete Ilex trees '..choice)
    end
   end
   mod.exports.flora:select('big_trees','default');mod.exports.state:invalidate();clock=0;world.mapImage=world:imageFor(map.id)
  end
  if spec.animated_buildings then fixture.animated_buildings=verifyAnimatedBuildings(game,def,draw)end
  check(fixture.collision_before==fixture.collision_after and fixture.events_before==fixture.events_after,
   'Additional Gen2 fixture changed native collision/warps/events')
  if spec.id=='VIOLET_CITY' then
   for _,category in ipairs({'trees','flowers','grass','water'})do mod.exports.flora:select(category,'mixed')end
   mod.exports.state:invalidate();clock=0;world.mapImage=world:imageFor(map.id)
   local customArt=mod.exports.state:replacements(game,def.tileset,def)
   local custom=draw()
   local checked=verifyCoveredPixels(def,customArt,custom,game..' mixed Violet')
   check(mod.exports.state.rejected==0,'Mixed Gen2 customization rejected reviewed mappings')
   check(snapshot(map,2)==mechanics and eventSnapshot(map)==events,'Mixed Gen2 artwork changed source gameplay')
   for _,t in ipairs({.21,.41,.71,1.06})do
    clock=t;checked=checked+verifyCoveredPixels(def,customArt,draw(),game..' independent flora wind')
   end
   clock=0
   local saved=custom:getString()
   mod.exports.state:invalidate();world.mapImage=world:imageFor(map.id)
   check(draw():getString()==saved,'Mixed Gen2 artwork changed on map revisit')
   for _,category in ipairs({'trees','flowers','grass','water'})do mod.exports.flora:select(category,'default')end
   mod.exports.state:invalidate();world.mapImage=world:imageFor(map.id)
   check(draw():getString()==after:getString(),'Default Gen2 options did not restore exact reviewed artwork')
   report.customizations[#report.customizations+1]={id=game..'-violet-mixed',game=game,map=def.id,
    before=fixture.after,after=encodePng(custom,game..'-violet-mixed-gpu.png'),coverage=fixture.coverage,
    checked_gpu_pixels=checked,source_collision_events_unchanged=true,stable_after_map_rebuild=true}
   mod.exports.flora:select('trees','mixed');mod.exports.state:invalidate();world.mapImage=world:imageFor(map.id)
   local treesOnly=draw()
   local groundChecked=verifyUnchangedGround(map,after,treesOnly,game..' Violet Mixed trees')
   report.customizations[#report.customizations+1]={id=game..'-violet-trees-only',game=game,map=def.id,
    before=fixture.after,after=encodePng(treesOnly,game..'-violet-trees-only-gpu.png'),coverage=fixture.coverage,
    unchanged_walkable_ground_cells=groundChecked}
   mod.exports.flora:select('trees','default');mod.exports.state:invalidate();world.mapImage=world:imageFor(map.id)
  end
  mod.exports.dispose();clock=0;world.mapImage=world:imageFor(map.id)
  check(draw():getString()==native:getString(),'Additional Gen2 cleanup did not restore original native pixels')
  fixture.cleanup_restored_native=true;report.fixtures[#report.fixtures+1]=fixture
 end

 -- Invoke the actual native Cut block swap on a private imported Route29.
 -- Only neighbour construction is omitted: map refresh, cache invalidation,
 -- attribute-grid rebuilding and the source collision swap run natively.
 for _,game in ipairs({'gold','silver','crystal'})do
  GV.set(game);assetGame=game;clock=0
  local world,map2,def2=world2(game,'ROUTE_29')
  local private={};for key,value in pairs(def2)do private[key]=value end
  private.blocks={};for i,id in ipairs(def2.blocks)do private.blocks[i]=id end
  def2=private;world.maps[def2.id]=def2;map2=Map2.new(def2,world.tilesets[def2.tileset]);world.map=map2
  world.rebuildNeighbors=function(self)self.neighbors={}end
  local FieldMoves=require('src.world.gen2.FieldMoves')
  local replacement=FieldMoves.CUT_BLOCKS[def2.tileset][95]
  check(replacement and replacement[1]==61 and replacement[2]==0,'Native Route29 Cut replacement changed')
  local index
  for i,id in ipairs(def2.blocks)do if id==95 then index=i;break end end
  check(index~=nil,'Actual Route29 Cut-tree block95 is missing')
  local bx,by=(index-1)%def2.width,math.floor((index-1)/def2.width)
  local events=eventSnapshot(map2);local originalBlocks={};for i,id in ipairs(def2.blocks)do originalBlocks[i]=id end
  local mod2=startMod(game,2,world)
  world.mapImage=world:imageFor(map2.id)
  report.plant_actors=report.plant_actors or {}
  report.plant_actors[#report.plant_actors+1]=verifyPlantActors(mod2,def2,map2,function()return drawWorld2(world)end,nil,world)
  local beforeCut=drawWorld2(world)
  local sourceCollision=map2:cellCollision(bx*2+1,by*2+1)
  local objectProof=verifyGen2Objects(game,def2,map2,beforeCut)
  check(objectProof.native_objects>0,'Approved actual Cut-tree object mapping was not drawn')
  check(world:replaceBlock(index,replacement[1]),'Actual native World:replaceBlock rejected Cut swap')
  local afterCut=drawWorld2(world)
  check(world.blockEdits[def2.id][index]==95,'Native Cut restoration record was lost')
  for i,id in ipairs(def2.blocks)do check(id==(i==index and 61 or originalBlocks[i]),'Cut mutated an unrelated source block')end
  local targetCollision=world.tilesets[def2.tileset].collision[62][4]
  check(map2:cellCollision(bx*2+1,by*2+1)==targetCollision,'Cut collision did not become native replacement collision')
  check(FieldMoves.CUT_BLOCKS[def2.tileset][map2:blockId(bx,by)]==nil,'Native Cut target still contains a Cut-tree block')
  local fresh=world:bakeMapImage(map2,'DAY',1):newImageData()
  for y=0,15 do for x=0,15 do
   equalPixel(afterCut,bx*32+16+x,by*32+16+y,fresh,bx*32+16+x,by*32+16+y,
    'Cut target retained stale object pixels instead of a fresh native replacement bake')
  end end
  check(eventSnapshot(map2)==events,'Cut graphic changed source warps/events')
  local changed=0
  for y=0,world.viewH-1 do for x=0,world.viewW-1 do
   local ar,ag,ab,aa=beforeCut:getPixel(x,y);local br,bg,bb,ba=afterCut:getPixel(x,y)
   if ar~=br or ag~=bg or ab~=bb or aa~=ba then
    check(x>=bx*32 and x<(bx+1)*32 and y>=by*32 and y<(by+1)*32,'Cut repainted outside its source32px block')
    changed=changed+1
   end
  end end
  check(changed>0,'Cut left stale tree pixels in the native map cache')
  local fixture={game=game,map=def2.id,test='native World.replaceBlock Cut removal',
   source_block=95,replacement_block=61,block_index=index,cell={bx*2+1,by*2+1},
   collision_before=sourceCollision,collision_after=targetCollision,changed_gpu_pixels=changed,
   native_object_proof=objectProof,events_unchanged=true,unrelated_blocks_unchanged=true,
   edited_cell_matches_fresh_native_refresh=true,cuttable_after=false,
   before=encodePng(beforeCut,game..'-cut-tree-before-gpu.png'),
   after=encodePng(afterCut,game..'-cut-tree-after-gpu.png')}
  mod2.exports.dispose()
  local expected=world:bakeMapImage(map2,'DAY',1):newImageData()
  check(world:imageFor(map2.id):newImageData():getString()==expected:getString(),
   'Cut cleanup retained mod graphics in the native replacement bake')
  fixture.cleanup_restored_native=true;report.interactions[#report.interactions+1]=fixture
 end
 -- Native darkness is a palette/visibility mask over source pixels. Preserve
 -- it exactly until the game's own Flash entry point changes the light state.
 local function verifyGen1Flash(game)
  GV.set(game);assetGame=game;clock=0
  local oldMode=FX.mode;FX.mode='og'
  local sourceMaps,sourceSets=generated(game,'maps'),generated(game,'tilesets')
  local def=assert(sourceMaps.ROCK_TUNNEL_1F)
  local map=Map.new(def,sourceSets[def.tileset])
  local renderer=T.new(map,{maps=sourceMaps,tilesets=sourceSets})
  local Overworld=require('src.world.OverworldController')
  local state=setmetatable({map=map,dark=false},{__index=Overworld})
  local function draw()
   return capture(def.width*32,def.height*32,function()
    FX.clearTrueColor();FX.setPass('world')
    FX.setShadeMap(FX.darkWorld() and FX.DARK_BGP or nil)
    local shader=FX.shader();check(shader~=nil,'Native Gen1 palette shader did not compile')
    G.setShader(shader);FX.sendColors(shader,FX.GRAYS)
    renderer:drawWindow(0,0,def.width*32,def.height*32)
    G.setShader();FX.setPass(nil);FX.setShadeMap(nil)
   end)
  end
  local mechanics,events=snapshot(map,1),eventSnapshot(map)
  state:setDark(false);local nativeLit=draw()
  state:setDark(true);local nativeDark=draw()
  check(nativeDark:getString()~=nativeLit:getString(),'RockTunnel native darkness fixture is ineffective')
  local mod=startMod(game,1)
  local art=assert(mod.exports.state:replacements(game,def.tileset,def))
  check(coverage(def,art).replaced_occurrences>0,'Dark RockTunnel has no reviewed art to test')
  local dark=draw()
  check(dark:getString()==nativeDark:getString(),'Gen1 donor art bypassed the native unlit source mask')
  check(#FX.trueColorRects('world')==0,'Unlit Gen1 donor art marked a true-color bypass region')
  -- Inject only the private game host and immediate text acknowledgement;
  -- useFlashFieldMove, setDark and the real white-flash object stay native.
  local TextBox=require('src.render.TextBox');local previousNew=TextBox.new
  local textCalls,pushes=0,0
  TextBox.new=function(host,text,onDone)textCalls=textCalls+1;return {acknowledge=onDone}end
  local host={save={},data={text={}},stack={}}
  host.stack.push=function(self,item)pushes=pushes+1;if item.acknowledge then item.acknowledge()end end
  local upvalue,oldHost
  for index=1,40 do
   local name,value=debug.getupvalue(Overworld.useFlashFieldMove,index)
   if not name then break end
   if name=='Game' then upvalue,oldHost=index,value;break end
  end
  check(upvalue~=nil,'Native Flash game-host upvalue is unavailable')
  debug.setupvalue(Overworld.useFlashFieldMove,upvalue,host)
  check(state:useFlashFieldMove(),'Native Gen1 Flash entry point rejected the private fixture')
  debug.setupvalue(Overworld.useFlashFieldMove,upvalue,oldHost);TextBox.new=previousNew
  check(host.save.flashLit==true and state.dark==false and not FX.darkWorld() and FX.darkKey()=='',
   'Native Gen1 Flash did not clear the world darkness state')
  check(textCalls==1 and pushes==2,'Native Gen1 Flash text/white-flash sequence changed')
  local lit=draw()
  local checked=verifyCoveredPixels(def,art,lit,game..' postFlash RockTunnel')
  check(lit:getString()~=nativeLit:getString() and #FX.trueColorRects('world')>0,
   'Gen1 reviewed art did not return after native Flash')
  check(snapshot(map,1)==mechanics and eventSnapshot(map)==events,'Gen1 Flash graphics changed source collision/warps/events')
  mod.exports.dispose()
  check(draw():getString()==nativeLit:getString(),'Gen1 Flash cleanup did not restore native lit pixels')
  report.lighting[#report.lighting+1]={game=game,map=def.id,generation=1,
   native_methods={'OverworldState.useFlashFieldMove','OverworldState.setDark','PaletteFX.sendColors','TileRenderer.drawWindow'},
   native_unlit_exact=true,unlit_donor_bypass_rectangles=0,native_flash_flag_set=true,
   checked_postflash_donor_pixels=checked,source_collision_events_unchanged=true,cleanup_restored_native=true,
   native_unlit=encodePng(nativeDark,game..'-rocktunnel-native-dark-gpu.png'),
   mod_unlit=encodePng(dark,game..'-rocktunnel-gen3-dark-gpu.png'),
   post_flash=encodePng(lit,game..'-rocktunnel-gen3-flash-gpu.png'),
   limits='Native source palette shader in monochrome mode. Private game-host upvalue and immediate text acknowledgement; no full gameplay/UI.'}
  FX.mode=oldMode
 end
 for _,game in ipairs({'red','blue','yellow'})do verifyGen1Flash(game)end
 local function verifyGen2Flash(game)
  GV.set(game);assetGame=game;clock=0
  local world,map,def=world2(game,'DARK_CAVE_VIOLET_ENTRANCE')
  world.clockHour=12;world.flashUsed=false;world.flickerClock=0
  world.rebuildNeighbors=function(self)self.neighbors={}end
  local mechanics,events=snapshot(map,2),eventSnapshot(map)
  local function sample(phase,timer)
   world.daytime='DARK';world.flickerPhase=phase;world.animTimer=timer
   world.mapImage=world:imageFor(map.id)
   local frame=drawWorld2(world)
   local border=world:borderImageFor(map.id)
   local borderImage=border and capture(32,32,function()G.draw(border,0,0)end)
   local priority=capture(world.viewW,world.viewH,function()
    world:blitBgOverRegionLocal(def,0,0,0,0,world.viewW,world.viewH,true,nil,1)
   end)
   return {frame=frame,border=borderImage,priority=priority}
  end
  world.daytime='NITE';world.animTimer=0;world.mapImage=world:imageFor(map.id)
  local nativeLit=drawWorld2(world)
  local native={}
  for phase=1,2 do for timer=0,7 do native[phase..':'..timer]=sample(phase,timer)end end
  local cells=world:animCellsFor(map,world.tilesets[def.tileset]);local animated=0
  for _,list in pairs(cells or {})do animated=animated+#list.cells/2 end
  check(animated>0,'DarkCave fixture has no native animated cells')
  local mod=startMod(game,2,world)
  local art=assert(mod.exports.state:replacements(game,def.tileset,def))
  local injected
  if coverage(def,art).replaced_occurrences==0 then
   -- The production dataset has no DarkCave rows yet. An explicitly private
   -- replacement of one actual ordinary floor cell makes the darkness guard
   -- observable without publishing an unreviewed mapping or editing imports.
   local index
   for pos,id in ipairs(def.blocks)do
    local bx,by=(pos-1)%def.width,math.floor((pos-1)/def.width)
    if id==9 and bx>1 and by>1 and bx<def.width-2 and by<def.height-2 then index=pos;break end
   end
   check(index~=nil,'Private DarkCave plain-floor block9 is unavailable')
   local bx,by=(index-1)%def.width,math.floor((index-1)/def.width)
   local sourceRef={game=game,tileset=def.tileset,id=9,quadrant=0,map=def.id,
    hash='2cd3b53fec070a64035f079f2b7d76f8b61a42e5dffa4a39b4ec42ceefd603e3'}
   local original,why=sourceDecoder():cell(sourceRef);check(original~=nil,tostring(why))
   local sourceTiles=world.tilesets[def.tileset].blocks[10]
   for _,n in ipairs({1,2,5,6})do check(sourceTiles[n]==22,'Private DarkCave source floor is not the reviewed plain22 graphic')end
   check(map:cellCollision(bx*2,by*2)==0 and map:isWalkableCell(bx*2,by*2),
    'Private DarkCave replacement is not an ordinary native walkable floor')
   local donor={game='firered',tileset='general__rom_082d4bfc',id=641,
    hash='e0e6ed6f56a255b27ee4a06ca075d597b61a463212899a806a5e19e3d5c99855'}
   local floor=nativeCellImage(donor);local image=love.image.newImageData(32,32)
   image:paste(floor,0,0,0,0,16,16)
   local positioned={image=image,coverage={[0]=true}}
   art={[9]={image=love.image.newImageData(32,32),coverage={},positions={[bx..':'..by]=positioned}}}
   local previous=mod.exports.state.replacements
   mod.exports.state.replacements=function(self,cart,tileset,mapDef)
    if cart==game and tileset==def.tileset and mapDef and mapDef.id==def.id then return art end
    return previous(self,cart,tileset,mapDef)
   end
   injected={scope='private GPU process only; no production mapping/import writes',source=sourceRef,
    source_collision=0,source_8px_tiles={22,22,22,22},source_walkable=true,cell={bx*2,by*2},donor=donor,
    image='one complete native16px cave-floor cell through the actual mod state/adapter'}
  end
  check(coverage(def,art).replaced_occurrences>0,'DarkCave has no donor-art fixture to test')
  local checkpoints={}
  for phase=1,2 do for timer=0,7 do
   local expected=native[phase..':'..timer];local actual=sample(phase,timer)
   check(actual.frame:getString()==expected.frame:getString(),'Gen2 donor art bypassed unlit native animation/flicker pixels')
   check(actual.priority:getString()==expected.priority:getString(),'Gen2 unlit priority/feet blit changed native source pixels')
   check((actual.border==nil)==(expected.border==nil),'Gen2 native unlit border availability changed')
   if expected.border then check(actual.border:getString()==expected.border:getString(),'Gen2 unlit border changed native source pixels')end
   checkpoints[#checkpoints+1]={flicker_phase=phase,animation_timer=timer,exact_native_gpu_pixels=true}
  end end
  world.flickerPhase=1;world.flickerClock=0;world.animTimer=0;world.mapImage=world:imageFor(map.id)
  world:pollCaveFlicker();world:pollCaveFlicker()
  check(world.flickerPhase==2 and drawWorld2(world):getString()==native['2:0'].frame:getString(),
   'Native two-tick cave entrance flicker did not preserve unlit source pixels')
  check(native['1:0'].frame:getString()~=nativeLit:getString(),'Gen2 native DARK and NITE fixture look identical')
  local textCalls,soundCalls=0,0
  world.showText=function(self,text,onDone)textCalls=textCalls+1;onDone()end
  world.playSfx=function()soundCalls=soundCalls+1 end
  world:runFlash({text='Private GPU Flash fixture'})
  check(world.flashUsed==true and world.daytime=='NITE' and textCalls==1 and soundCalls==1,
   'Native World.runFlash did not set the flag and restore NITE palettes')
  world.animTimer=0;local lit=drawWorld2(world)
  local checked=verifyCoveredPixels(def,art,lit,game..' postFlash DarkCave')
  check(lit:getString()~=nativeLit:getString(),'Gen2 donor art did not return after native Flash')
  check(snapshot(map,2)==mechanics and eventSnapshot(map)==events,'Gen2 Flash graphics changed source collision/warps/events')
  mod.exports.dispose();world.mapImage=world:imageFor(map.id)
  check(drawWorld2(world):getString()==nativeLit:getString(),'Gen2 Flash cleanup did not restore native NITE pixels')
  report.lighting[#report.lighting+1]={game=game,map=def.id,generation=2,
   native_methods={'World.runFlash','World.applyPalettes','World.refreshMapImages','World.pollCaveFlicker',
    'World.drawAnimCells','World.borderImageFor','World.blitBgOverRegionLocal'},
   native_unlit_exact=true,native_animated_cells=animated,unlit_checkpoints=checkpoints,
   private_floor_fixture=injected,
   native_flash_flag_set=true,postflash_daytime=world.daytime,checked_postflash_donor_pixels=checked,
   source_collision_events_unchanged=true,cleanup_restored_native=true,
   native_unlit=encodePng(native['1:0'].frame,game..'-darkcave-native-dark-gpu.png'),
   native_unlit_flicker2=encodePng(native['2:0'].frame,game..'-darkcave-native-dark-flicker2-gpu.png'),
   post_flash=encodePng(lit,game..'-darkcave-gen3-flash-gpu.png'),
   limits='Native methods on private imported maps; text acknowledged immediately and audio recorded. No full gameplay/UI.'}
 end
 for _,game in ipairs({'gold','silver','crystal'})do verifyGen2Flash(game)end
 check(#report.warnings==0,'Probe reported rejected mapping warnings')
 report.status='passed'
 write('report.json',Json.encode(report))
end
function love.load()
 local ok,err=xpcall(run,debug.traceback)
 if not ok then
  report.status='failed';report.error=tostring(err)
  write('error.txt',tostring(err))
  local good,Json=pcall(require,'src.link.Json')
  if good then write('report.json',Json.encode(report))end
 end
 love.event.quit(ok and 0 or 1)
end
"""


def ps_quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def runtime_fingerprint(mod_root: Path) -> dict:
    """Hash production runtime inputs using a reproducible path/size/SHA list."""
    paths = [mod_root / "main.lua", mod_root / "manifest.json"]
    for directory in ("lib", "mappings"):
        paths.extend((mod_root / directory).rglob("*.lua"))
    paths.extend(path for path in (mod_root / "assets").rglob("*") if path.is_file())
    files = []
    for path in sorted(set(paths), key=lambda p: p.relative_to(mod_root).as_posix()):
        contents = path.read_bytes()
        files.append({"path": path.relative_to(mod_root).as_posix(), "bytes": len(contents),
                      "sha256": hashlib.sha256(contents).hexdigest()})
    canonical = "".join(f"{item['path']}\t{item['bytes']}\t{item['sha256']}\n" for item in files)
    return {"algorithm": "sha256(path TAB byte_count TAB file_sha256 LF), sorted by relative path",
            "scope": "main.lua, manifest.json, lib/**/*.lua, mappings/**/*.lua, assets/**/*",
            "sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(), "files": files}


def main() -> int:
    mod_root = Path(__file__).resolve().parents[1]
    workspace = mod_root.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", type=Path, default=workspace / ".tools/engine-0395")
    parser.add_argument("--love", type=Path, default=workspace / ".tools/love-audio-runtime/love-probe.exe")
    parser.add_argument("--cache", type=Path, default=Path(os.environ["APPDATA"]) / "pokemon-love2d")
    parser.add_argument("--output", type=Path, default=workspace / ".work/tileshift-gpu")
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()
    engine, love, cache, output = (p.resolve() for p in (args.engine, args.love, args.cache, args.output))
    if not love.is_file() or not (engine / "src/render/TileRenderer.lua").is_file():
        parser.error("The native LÃ–VE executable and engine source must exist")
    output.mkdir(parents=True, exist_ok=True)
    # A failed launch must never reuse an earlier successful report.
    for name in ("report.json", "error.txt"):
        (output / name).unlink(missing_ok=True)
    runtime_inputs = runtime_fingerprint(mod_root)
    source = LUA.replace("@CACHE@", json.dumps(cache.as_posix())).replace(
        "@MOD@", json.dumps(mod_root.as_posix())).replace("@OUT@", json.dumps(output.as_posix())).replace(
        "@RUNTIME_INPUT@", json.dumps(json.dumps(runtime_inputs, separators=(",", ":"))))
    (output / "probe.lua").write_text(source, encoding="utf-8")
    archive = output / "native-probe.love"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as bundle:
        for directory in ("src", "assets", "data"):
            for path in (engine / directory).rglob("*"):
                if path.is_file():
                    bundle.write(path, path.relative_to(engine).as_posix())
        bundle.writestr("main.lua", source)
        bundle.writestr("conf.lua", CONF)
    metadata = {
        "engine_source": str(engine), "love_executable": str(love),
        "identity": "tileshift-gpu-validation", "private_archive": str(archive),
        "mod_main_sha256": hashlib.sha256((mod_root / "main.lua").read_bytes()).hexdigest(),
        "read_only_imports": str(cache), "output": str(output),
        "runtime_inputs": runtime_inputs,
    }
    payload = cache / "updates/gen1recomp-0.3.97.love"
    native_paths = (
        "src/render/TileRenderer.lua", "src/world/gen2/World.lua",
        "src/world/Map.lua", "src/world/gen2/Map.lua",
    )
    metadata["native_renderer_sha256"] = {
        name: hashlib.sha256((engine / name).read_bytes()).hexdigest() for name in native_paths
    }
    if payload.is_file():
        with zipfile.ZipFile(payload) as bundle:
            matches = {
                name: bundle.read(name) == (engine / name).read_bytes() for name in native_paths
            }
        metadata["reference_payload"] = str(payload)
        metadata["reference_payload_renderer_matches"] = matches
        if not all(matches.values()):
            parser.error("The private native renderer source differs from installed 0.3.97")
    (output / "invocation.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    script = (
        "$p=Start-Process -WindowStyle Hidden -FilePath " + ps_quote(str(love))
        + " -ArgumentList " + ps_quote('"' + str(archive) + '"')
        + " -WorkingDirectory " + ps_quote(str(output))
        + " -RedirectStandardOutput " + ps_quote(str(output / "stdout.txt"))
        + " -RedirectStandardError " + ps_quote(str(output / "stderr.txt")) + " -PassThru; "
        + f"if(-not $p.WaitForExit({args.timeout * 1000})){{$p.Kill();throw 'Private GPU probe timed out'}};exit $p.ExitCode"
    )
    result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                            timeout=args.timeout + 20, check=False)
    report_file = output / "report.json"
    if report_file.exists():
        report = json.loads(report_file.read_text(encoding="utf-8"))
        unchanged = runtime_inputs == runtime_fingerprint(mod_root)
        report["runtime_inputs_unchanged_during_probe"] = unchanged
        if not unchanged:
            report["status"] = "failed"
            report["error"] = "Production runtime inputs changed during the private GPU probe; rerun after edits finish."
        report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 0 if result.returncode == 0 and report.get("status") == "passed" else 1
    error = output / "error.txt"
    if error.exists():
        print(error.read_text(encoding="utf-8", errors="replace"))
    else:
        print(f"Native GPU probe exited {result.returncode}; no report at {report_file}")
        for name in ("stdout.txt", "stderr.txt"):
            path = output / name
            if path.exists():
                print(path.read_text(encoding="utf-8", errors="replace")[-5000:])
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
