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
local report={status='running',theme='gen3',checks=0,fixtures={},interactions={},warnings={},writes='private probe output only',
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
   local block=assert(art[id]);local expected=block.frames and block.frames[1] or block.image
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
   local block=art[def.blocks[by*def.width+bx+1]]
   if block then
    local expected=block.frames and block.frames[1] or block.image
    for q=0,3 do if not block.coverage or block.coverage[q] then
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
  for _,block in pairs(art)do if block.frames and block.bank==bank then
   check(#block.frames==frames and block.period==16/60 and block.offset==phase/60,'Native donor animation schedule changed')
   count=count+1
  end end
  check(count>0,'Expected native animation bank is absent: '..bank)
  local checkpoints={}
  for f=0,frames do
   -- Sample one native tick into each frame, then the complete repeated cycle.
   local tick=phase+f*16+1;clock=tick/60
   local image=draw();local sampled=0
   for id,block in pairs(art)do if block.frames and block.bank==bank then
    for pos,sourceId in ipairs(def.blocks)do if sourceId==id then
     local bx,by=(pos-1)%def.width,math.floor((pos-1)/def.width)
     for q,included in pairs(block.coverage)do if included then
      for y=0,15 do for x=0,15 do
       equalPixel(image,bx*32+q%2*16+x,by*32+math.floor(q/2)*16+y,
        block.frames[f%frames+1],q%2*16+x,math.floor(q/2)*16+y,bank..' native GPU animation mismatch')
      end end
      sampled=sampled+1
     end end
    end end
   end end
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
 -- matching reviewed FR/LG palette families. Uncovered art remains native.
 for _,spec in ipairs({{id='MT_MOON_1F',stem='mtmoon',minimum=943},
  {id='SEAFOAM_ISLANDS_1F',stem='seafoam',minimum=473},
  {id='DIGLETTS_CAVE_ROUTE_2',stem='diglett',minimum=25}})do
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
  check(c.replaced_occurrences>=spec.minimum,'Approved cave coverage decreased')
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
  local c=coverage(def2,art);check(c.visible_cells==360 and c.replaced_occurrences==304,'Approved NewBark Headbutt coverage must be304/360')
  local fixture={game=game,map=def2.id,native_renderer='src.world.gen2.World:bakeMapImage + drawAnimCells',
   before=encodePng(native,game..'-newbark-native-gpu.png'),after=encodePng(after2,game..'-newbark-gen3-gpu.png'),
   accepted=mod2.exports.state.accepted,checked_donor_pixels=verifyCoveredPixels(def2,art,after2,game),coverage=c,
   native_palette_shader_available=require('src.render.GbcPalette').available(),
   native_trees=verifyGen2Objects(game,def2,map2,after2),collision_before=mechanics,events_before=events}
  check(fixture.native_trees.native_tree_pairs>0,'No native16x32 NewBark tree pair was sampled')
  check(fixture.native_palette_shader_available,'Native Gen2 palette shader did not compile')
  fixture.flower_all_frames=verifyAnimationFrames(def2,art,function()return drawWorld2(world)end,'general_flower',4,0)
  fixture.water_all_frames=verifyAnimationFrames(def2,art,function()return drawWorld2(world)end,'general_water',8,1)
  fixture.headbutt=verifyHeadbutt(game,world,map2,def2,after2)
  fixture.collision_after=snapshot(map2,2);fixture.events_after=eventSnapshot(map2)
  check(fixture.collision_before==fixture.collision_after,'NewBark source collision/layout changed')
  check(fixture.events_before==fixture.events_after,'NewBark source events changed')
  mod2.exports.dispose();clock=0
  check(world:bakeMapImage(map2,'DAY',1):newImageData():getString()==native:getString(),
   'Gen2 cleanup did not restore native GPU bake')
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
