-- Gen 2 visual adapter.  Source maps, block IDs, collisions and attributes are
-- never changed.  Replacement art is already composed in source 32px blocks.
--
-- install {
--   replacements = function(version, tilesetId, mapDef) return {[blockId]=art} end,
--   version = function() return 'crystal' end, -- optional, defaults to GameVersion
--   revision = function() return revision end, -- optional; change after settings
-- }
-- art = ImageData | {image=ImageData, foreground=ImageData?, frames={...}?,
--                   foregroundFrames={...}?, period=0.2?}
-- Images are 32x32. Grass blocks require an explicit alpha foreground so the
-- replacement cannot accidentally paint an opaque rectangle over sprite feet.
local Adapter = {}

function Adapter.install(ctx)
  assert(type(ctx) == 'table' and type(ctx.replacements) == 'function',
    'TileShift Gen 2 requires reviewed replacements')
  local World = ctx.worldClass or require('src.world.gen2.World')
  local Border = ctx.borderFill or require('src.world.gen2.BorderFill')
  local Palette = ctx.palette or require('src.render.GbcPalette')
  local version = ctx.version or require('src.core.GameVersion').get
  local G = ctx.graphics or love.graphics
  local previous, wrappers, worlds = {}, {}, setmetatable({}, {__mode='k'})
  local closed=false
  local cleanup
  local images, quads = setmetatable({}, {__mode='k'}), setmetatable({}, {__mode='k'})
  local borderComposites, ownedCanvases = setmetatable({}, {__mode='k'}), {}
  local warned, serial = {}, tostring({})
  local function revision()
    return '|tileshift|' .. serial .. '|' .. tostring(ctx.revision and ctx.revision() or 0)
  end
  local function unlit(self)
    -- DARK is a source-pixel palette mask, not a uniform RGB multiplier.
    -- The native bake also contains the blinking yellow entrance cue. Keep
    -- that exact visibility until native Flash resolves the daytime to NITE.
    return self.daytime == 'DARK'
  end
  local function warn(key, message)
    if not warned[key] then
      warned[key] = true
      if ctx.warn then ctx.warn(message) end
    end
  end
  local function artImage(data)
    if not data then return nil end
    local image = images[data]
    if image then return image end
    local w,h = data:getDimensions()
    assert(w == 32 and h == 32, 'TileShift Gen 2 block art must be 32x32')
    -- Accept GPU images too, useful for generated runtime compositions.
    image = data.typeOf and data:typeOf('Texture') and data or G.newImage(data)
    image:setFilter('nearest','nearest')
    images[data] = image
    return image
  end
  local function recordFor(self, def, blockId,bx,by)
    if not (def and def.tileset) then return nil end
    local all = ctx.replacements(version(), def.tileset, def)
    local art = all and all[blockId]
    if not art then return nil end
    if type(art)=='table' and art.positions and bx~=nil and by~=nil then art=art.positions[bx..':'..by] or art end
    if art.getDimensions then art = {image=art} end
    if not art.image then return nil end
    local ts = self.tilesets and self.tilesets[def.tileset]
    local colls = ts and ts.collision and ts.collision[blockId+1]
    if colls and not art.foreground then
      for quadrant,coll in ipairs(colls) do
        local n = coll % 256
        local included=art.coverage==nil or art.coverage[quadrant-1]
        if included and (n == 0x10 or n == 0x14 or n == 0x18 or n == 0x1c) then
          warn(def.tileset..':'..blockId,
            'Grass replacement needs an alpha foreground: '..def.tileset..':'..blockId)
          return nil
        end
      end
    end
    return art
  end
  local function covered(art,x,y)
    return art and (art.coverage==nil or
      art.coverage[math.floor((y%32)/16)*2+math.floor((x%32)/16)]==true)
  end
  local function frameFor(self, art, foreground, q)
    if art.cellAnimations and art.cellAnimations[q] then art=art.cellAnimations[q] end
    local frames = foreground and art.foregroundFrames or art.frames
    if frames and #frames > 0 then
      local t = ctx.time and ctx.time(self) or
        (love and love.timer and love.timer.getTime and love.timer.getTime()) or 0
      return artImage(frames[math.floor(math.max(0,t-(art.offset or 0)) / (art.period or .2)) % #frames + 1])
    end
    return artImage(foreground and art.foreground or art.image)
  end
  local function blockAt(map, tx,ty)
    local bx,by = math.floor(tx/32), math.floor(ty/32)
    if bx < 0 or by < 0 or bx >= map.width or by >= map.height then return nil end
    return Border.blockFor(map.blocks[by*map.width+bx+1], map.borderBlock)
  end
  local function drawCrop(image,sx,sy,w,h,x,y,scale)
    if not image then return end
    local key = sx..','..sy..','..w..','..h
    local byImage = quads[image]
    if not byImage then byImage={};quads[image]=byImage end
    local quad=byImage[key]
    if not quad then
      quad=G.newQuad(sx,sy,w,h,image:getDimensions());byImage[key]=quad
    end
    G.draw(image,quad,x,y,0,scale or 1,scale or 1)
  end
  local function drawTrue(fn)
    G.push('all');G.setShader();G.setColor(1,1,1,1)
    local ok,err = pcall(fn)
    G.pop()
    if not ok then error(err,0) end
  end
  local function drawBlock(art,img,x,y,s,self)
    if not art.coverage then G.draw(img,x,y,0,s or 1,s or 1);return end
    for quadrant=0,3 do
      if art.coverage[quadrant] then
        local sx,sy=quadrant%2*16,math.floor(quadrant/2)*16
        drawCrop(self and frameFor(self,art,false,quadrant) or img,sx,sy,16,16,x+sx*(s or 1),y+sy*(s or 1),s)
      end
    end
  end
  local function wrap(name, make)
    previous[name]=World[name]
    if not previous[name] then return end
    local native=previous[name]
    local active=make(native)
    local fn=function(...)
      -- A later mod may retain this wrapper inside its own chain. Its
      -- continued existence must not access released art after unloading.
      if closed then return native(...) end
      return active(...)
    end
    wrappers[name]=fn;World[name]=fn
  end
  wrap('mapCacheKey',function(old)
    return function(self,mapId)
      worlds[self]=true
      return old(self,mapId)..revision()
    end
  end)
  wrap('bakeMapImage',function(old)
    return function(self,map,daytime,flicker)
      worlds[self]=true
      local canvas,bg=old(self,map,daytime,flicker)
      if not canvas or daytime == 'DARK' then return canvas,bg end
      canvas:renderTo(function()
        drawTrue(function()
          G.origin();G.setScissor()
          for by=0,map.height-1 do for bx=0,map.width-1 do
            local block=Border.blockFor(map.blocks[by*map.width+bx+1],map.borderBlock)
            local art=recordFor(self,map.def,block,bx,by)
            if art then drawBlock(art,artImage(art.image),bx*32,by*32) end
          end end
        end)
      end)
      return canvas,bg
    end
  end)
  wrap('animCellsFor',function(old)
    return function(self,map,tileset)
      local native=old(self,map,tileset)
      if unlit(self) then return native end
      if not native then return nil end
      local result={}
      for tile,list in pairs(native) do
        local copy={};for k,v in pairs(list) do copy[k]=v end
        copy.cells={}
        for i=1,#list.cells,2 do
          local x,y=list.cells[i],list.cells[i+1]
          local block=blockAt(map,x,y)
          if block == nil or not covered(recordFor(self,map.def,block,math.floor(x/32),math.floor(y/32)),x,y) then
            copy.cells[#copy.cells+1]=x;copy.cells[#copy.cells+1]=y
          end
        end
        if #copy.cells>0 then result[tile]=copy end
      end
      return next(result) and result or nil
    end
  end)
  wrap('drawAnimCells',function(old)
    return function(self,mapId,ox,oy,s)
      if unlit(self) then return old(self,mapId,ox,oy,s) end
      old(self,mapId,ox,oy,s)
      local def=self.maps and self.maps[mapId]
      if not def then return end
      local cam=self.camera or {x=0,y=0};s=s or 1
      -- Only inspect the visible block rectangle. Large sea routes can have
      -- thousands of blocks, while the viewport intersects a few dozen.
      local firstX=math.max(0,math.floor((cam.x-ox-32)/32))
      local firstY=math.max(0,math.floor((cam.y-oy-32)/32))
      local lastX=math.min(def.width-1,math.floor((cam.x-ox+(self.viewW or 160))/32))
      local lastY=math.min(def.height-1,math.floor((cam.y-oy+(self.viewH or 144))/32))
      drawTrue(function()
        for by=firstY,lastY do for bx=firstX,lastX do
          local block=Border.blockFor(def.blocks[by*def.width+bx+1],def.borderBlock)
          local art=recordFor(self,def,block,bx,by)
          if art and art.frames and #art.frames>0 then
            local x,y=bx*32+ox-cam.x,by*32+oy-cam.y
            if x+32>=0 and y+32>=0 and x<=(self.viewW or 160)
                and y<=(self.viewH or 144) then
              drawBlock(art,frameFor(self,art,false),math.floor(x*s),math.floor(y*s),s,self)
            end
          end
        end end
      end)
    end
  end)
  wrap('borderImageFor',function(old)
    return function(self,mapId)
      if unlit(self) then return old(self,mapId) end
      local def=self.maps and self.maps[mapId]
      if not def then return old(self,mapId) end
      local fill=Border.fillBlock(def)
      if fill==false then return old(self,mapId) end
      local block=Border.blockFor(0,fill)
      local art=recordFor(self,def,block)
      if not art then return old(self,mapId) end
      local image=frameFor(self,art,false)
      if art.coverage then
        -- The source border may be an animated or palette-baked image. Preserve
        -- it in uncovered quadrants; transparent donor art alone would erase it.
        local native=old(self,mapId)
        if not native then return native end
        local bySource=borderComposites[image]
        if not bySource then bySource={};borderComposites[image]=bySource end
        local byRevision=bySource[native]
        if not byRevision then byRevision={};bySource[native]=byRevision end
        local key=tostring(revision())
        for q=0,3 do
          local cell=art.cellAnimations and art.cellAnimations[q]
          if cell then
            local t=ctx.time and ctx.time(self) or (love and love.timer and love.timer.getTime and love.timer.getTime()) or 0
            key=key..':'..math.floor(math.max(0,t-(cell.offset or 0))/(cell.period or .2))%#cell.frames
          end
        end
        local composite=byRevision[key]
        if not composite then
          local create=ctx.newCanvas or require('src.render.PixelCanvas').new
          composite=create(32,32,'nearest')
          composite:renderTo(function()
            drawTrue(function()
              G.origin();G.setScissor();G.clear(0,0,0,0)
              G.draw(native,0,0);drawBlock(art,image,0,0,nil,self)
            end)
          end)
          composite:setFilter('nearest','nearest')
          composite:setWrap('repeat','repeat')
          byRevision[key]=composite;ownedCanvases[#ownedCanvases+1]=composite
        end
        return composite
      end
      image:setWrap('repeat','repeat')
      return image
    end
  end)
  wrap('blitBgOverRegionLocal',function(old)
    return function(self,def,originX,originY,rx0,ry0,rx1,ry1,keyed,filter,scale)
      if unlit(self) then
        return old(self,def,originX,originY,rx0,ry0,rx1,ry1,keyed,filter,scale)
      end
      local map=self.map
      if not map then return old(self,def,originX,originY,rx0,ry0,rx1,ry1,keyed,filter,scale) end
      scale=scale or 1
      for ty=math.floor(ry0/8)*8,math.floor((ry1-1)/8)*8,8 do
        for tx=math.floor(rx0/8)*8,math.floor((rx1-1)/8)*8,8 do
          local block=blockAt(map,tx,ty)
          local art=block~=nil and recordFor(self,def,block,math.floor(tx/32),math.floor(ty/32))
          local dx=math.floor(originX+(tx-rx0)*scale)
          local dy=math.floor(originY+(ty-ry0)*scale)
          if covered(art,tx,ty) then
            local ts=self.tilesets[def.tileset]
            local info=self:bgTileAttrAt(map,ts,tx,ty)
            if info and (not filter or filter(info)) then
              drawTrue(function()
                drawCrop(frameFor(self,art,keyed,math.floor((ty%32)/16)*2+math.floor((tx%32)/16)),tx%32,ty%32,8,8,dx,dy,scale)
              end)
            end
          else
            old(self,def,dx,dy,tx,ty,tx+8,ty+8,keyed,filter,scale)
          end
        end
      end
    end
  end)
  wrap('drawGrassOverGoldSilver',function(old)
    return function(self,entity,ox,oy,s)
      if unlit(self) then return old(self,entity,ox,oy,s) end
      local map=self.map
      if not (entity and entity.inGrass and map) then return old(self,entity,ox,oy,s) end
      local atlas,tileset=self:grassAtlasFor(map.def)
      if not (atlas and tileset) then return end
      local bg=self.bgSets and self.bgSets[self:mapCacheKey(map.id)]
      local palettes=tileset.tilePalettes
      local perRow=tileset.tilesPerRow or 16
      local rx,ry=entity.px,entity.py+4;s=s or 1
      G.push('all');G.setColor(1,1,1,1)
      for ty=math.floor(ry/8)*8,math.floor((ry+7)/8)*8,8 do
        for tx=math.floor(rx/8)*8,math.floor((rx+15)/8)*8,8 do
          local tile=self:bgTileAt(map,tileset,tx,ty)
          if tile then
            local x0,y0=math.max(rx,tx),math.max(ry,ty)
            local w,h=math.min(rx+16,tx+8)-x0,math.min(ry+8,ty+8)-y0
            if w>0 and h>0 then
              local block=blockAt(map,tx,ty)
              local art=block~=nil and recordFor(self,map.def,block,math.floor(tx/32),math.floor(ty/32))
              G.setShader()
              if covered(art,tx,ty) then
                drawCrop(frameFor(self,art,true,math.floor((y0%32)/16)*2+math.floor((x0%32)/16)),x0%32,y0%32,w,h,
                  math.floor(ox+x0*s),math.floor(oy+y0*s),s)
              else
                local colors=bg and Palette.available() and bg[palettes and palettes[tile+1] or 1]
                if colors then Palette.use(colors) end
                local aw,ah=atlas:getDimensions()
                local q=G.newQuad((tile%perRow)*8+(x0-tx),
                  math.floor(tile/perRow)*8+(y0-ty),w,h,aw,ah)
                G.draw(atlas,q,math.floor(ox+x0*s),math.floor(oy+y0*s),0,s,s)
              end
            end
          end
        end
      end
      G.pop()
    end
  end)
  wrap('draw',function(old)
    return function(self,...)
      worlds[self]=true
      -- Ownership can disappear when the mod manager disables or reloads a
      -- mod without calling its exports. The cached mapImage must be replaced
      -- before native drawing uses it, not merely stop requesting new art.
      if ctx.active and not ctx.active() then cleanup() end
      return old(self,...)
    end
  end)
  cleanup=function()
    if closed then return end;closed=true
    for name,fn in pairs(wrappers) do
      if World[name]==fn then World[name]=previous[name] end
    end
    for world in pairs(worlds) do
      for _,name in ipairs({'mapImages','animCells','bgSets'}) do
        for key in pairs(world[name] or {}) do
          if type(key)=='string' and key:find('|tileshift|'..serial,1,true) then
            world[name][key]=nil
          end
        end
      end
      -- Next normal draw must obtain an unmodified bake after unloading.
      if world.map and world.imageFor then
        world.mapImage=world:imageFor(world.map.id)
        for _,nb in ipairs(world.neighbors or {}) do nb.image=world:imageFor(nb.id) end
      end
    end
    for data,image in pairs(images) do
      if image~=data and image.release then image:release() end
    end
    for _,canvas in ipairs(ownedCanvases) do if canvas.release then canvas:release() end end
  end
  return cleanup
end

return Adapter
