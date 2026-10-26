"""Validate TileShift with native LÖVE GPU renderers in a private probe process.

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
local report={status='running',theme='gen3',checks=0,fixtures={},warnings={},writes='private probe output only',
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
 local function cacheRead(relative)
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
   options={define=function()end,get=function()return 2 end},
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
 local function coverage(def,art)
  local replaced,unique=0,{}
  for _,id in ipairs(def.blocks)do
   local block=art[id]
   for q=0,3 do
    if block and (not block.coverage or block.coverage[q])then
     replaced=replaced+1;unique[id..':'..q]=true
    end
   end
  end
  local count=0;for _ in pairs(unique)do count=count+1 end
  return {visible_cells=def.width*def.height*4,replaced_occurrences=replaced,
   preserved_native_occurrences=def.width*def.height*4-replaced,unique_mappings_used=count,
   animation_frame=0,actors_rendered=false,source='actual session replacement coverage on native imported map'}
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
   ..tableString(map.def.objects or {}))
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
   local block=assert(art[id]);local expected=block.frames and block.frames[1] or block.image
   for y=0,31 do for x=0,31 do
    equalPixel(frame,bx*32+x,by*32+y,expected,x,y,game..' reviewed RGB/position mismatch')
    checked=checked+1
   end end
  end end
  return checked
 end
 local nativeBuildingSources={}
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
   local features,entrances,clearances={},0,0
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
    features[#features+1]={feature=feature.feature,source_rect_xywh=sr,target_rect_xywh=tr,
     exact_native_gpu_pixels=true,rgba_sha256=hash(targetCrop:getString())}
   end
   check(entrances>0,'Approved building must include a complete native entrance context proof')
   check(clearances>0,'Approved building must include its native wall clearance strip proof')
   proofs[#proofs+1]={id=building.id,footprint_px={r[3]*16,r[4]*16},
    map_rect_cells=r,door_bottom_anchor_px={ax,ay},door_destination=door.destMap,
    exact_approved_native_pixels=true,rgba_sha256=hash(actual:getString()),
    native_features=features,native_source_gpu=source.readback,
    image=encodePng(actual,game..'-pallet-'..building.id..'-gpu.png')}
  end
  return proofs
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
 red.collision_after=snapshot(map,1)
 check(red.collision_after==beforeCollision,'Gen1 collision, layout or tileset mutated')
 red.events_after=eventSnapshot(map)
 check(red.events_after==beforeEvents,'Red source warps, signs or objects changed')
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

 -- Optional map-only tree fixture uses the same real renderer and entry point.
 -- It also proves third-party alpha is composited over imported Emerald ground.
 local treeDef=maps.VIRIDIAN_CITY
 if treeDef then
  GV.set('red');assetGame='red';clock=0
  local treeMap=Map.new(treeDef,sets[treeDef.tileset])
  local treeCollision=snapshot(treeMap,1)
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
   third_party_tree={opaque_pixels=treeOpaque,transparent_ground_pixels=treeTransparent,
    translucent_blended_pixels=treeTranslucent,
    credit='J-Treecko252; additional palette contributions credited to Zyxeion'}}
  check(treeFixture.collision_before==treeFixture.collision_after,'Viridian collision/layout changed')
  treeMod.exports.dispose()
  local nativeAgain=capture(treeDef.width*32,treeDef.height*32,drawTrees)
  check(nativeAgain:getString()==nativeTree:getString(),'Viridian cleanup changed native GPU pixels')
  treeFixture.cleanup_restored_native=true
  report.fixtures[#report.fixtures+1]=treeFixture
 end

 -- Real Crystal World:bakeMapImage (native palette shader/attributes/roof).
 GV.set('crystal');assetGame='crystal'
 local World=require('src.world.gen2.World')
 local Map2=require('src.world.gen2.Map')
 local maps2,sets2,pals=generated('crystal','maps'),generated('crystal','tilesets'),generated('crystal','palettes')
 local def2=maps2.NEW_BARK_TOWN
 local map2=Map2.new(def2,sets2[def2.tileset])
 local game={save={version='crystal',options={}},options={}}
 local world=setmetatable({game=game,maps=maps2,tilesets=sets2,palettes=pals,
  roofs=generated('crystal','roofs'),atlasCache={},mapImages={},animCells={},bgSets={},daytime='DAY',
  flickerPhase=1,camera={x=0,y=0},animClock=0,animTimer=0,neighbors={},map=map2,
  viewW=def2.width*32,viewH=def2.height*32},{__index=World})
 local before2Collision=snapshot(map2,2)
 local nativeCanvas=world:bakeMapImage(map2,'DAY',1)
 check(nativeCanvas~=nil,'Crystal native map bake failed')
 local before2=nativeCanvas:newImageData()
 local mod2=startMod('crystal',2,world)
 local afterCanvas=world:bakeMapImage(map2,'DAY',1)
 local after2=afterCanvas:newImageData()
 local art2=assert(mod2.exports.state:replacements('crystal',def2.tileset,def2))
 check(mod2.exports.state.rejected==0,'Crystal reviewed mappings unexpectedly rejected')
 local palettePixels=0
 for id,block in pairs(art2)do
  for q,included in pairs(block.coverage or {})do if included then
   local wx,wy=findCell(def2,id,q)
   if wx then
    for y=0,15 do for x=0,15 do
     equalPixel(after2,wx+x,wy+y,block.image,q%2*16+x,math.floor(q/2)*16+y,'Crystal donor quantized or positioned incorrectly')
     palettePixels=palettePixels+1
    end end
   end
  end end
 end
 check(palettePixels>0,'No real Crystal donor color pixels sampled')
 local crystal={game='crystal',map=def2.id,native_renderer='src.world.gen2.World:bakeMapImage',
  before=encodePng(before2,'crystal-newbark-native-gpu.png'),after=encodePng(after2,'crystal-newbark-gen3-gpu.png'),
  accepted=mod2.exports.state.accepted,checked_donor_pixels=palettePixels,
  native_palette_shader_available=require('src.render.GbcPalette').available(),
  collision_before=before2Collision,collision_after=snapshot(map2,2),coverage=coverage(def2,art2)}
 check(crystal.native_palette_shader_available,'Native Crystal palette shader did not compile')
 check(crystal.collision_before==crystal.collision_after,'Gen2 collision/layout/tileset changed')
 mod2.exports.dispose()
 local restored2=world:bakeMapImage(map2,'DAY',1):newImageData()
 check(restored2:getString()==before2:getString(),'Gen2 cleanup did not restore native GPU bake')
 crystal.cleanup_restored_native=true
 report.fixtures[#report.fixtures+1]=crystal
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
        parser.error("The native LÖVE executable and engine source must exist")
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
    payload = cache / "updates/gen1recomp-0.3.96.love"
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
            parser.error("The private native renderer source differs from installed 0.3.96")
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
