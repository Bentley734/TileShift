-- Replace pixels after the native background has drawn. The source map,
-- tile numbers, event scripts and collision definitions are never edited.
local G = {}
local unpack=table.unpack or unpack
local function pack(...) return {n=select('#',...),...} end

function G.install(ctx)
  assert(type(ctx)=='table' and type(ctx.replacements)=='function',
    'TileShift Gen 1 requires reviewed replacements')
  local T = ctx.renderer or require('src.render.TileRenderer')
  local FX = ctx.palette or require('src.render.PaletteFX')
  local graphics = ctx.graphics or love.graphics
  local originals, wrappers = {}, {}
  local images = setmetatable({}, {__mode='k'})
  local quads = setmetatable({}, {__mode='k'})
  local owned, warned = {}, {}
  local closed = false
  local cleanup
  local function active()
    if closed then return false end
    if ctx.active and not ctx.active() then
      cleanup()
      return false
    end
    return true
  end
  local function version()
    return type(ctx.version)=='function' and ctx.version() or ctx.version
  end
  local function rows(self)
    if not active() or not self.map or not self.map.def then return nil end
    -- FadePal2 hides the native cave through source-shade masks, including
    -- animated and sprite-foot redraws. A full-color overlay cannot reproduce
    -- that mask by dimming RGB uniformly. Keep the exact native unlit pixels
    -- until the engine clears darkWorld after Flash; do not change its state.
    if (FX.darkWorld and FX.darkWorld()) or
        (FX.darkKey and FX.darkKey() ~= '') then return nil end
    return ctx.replacements(version(), self.map.def.tileset, self.map.def)
  end
  local function image(data)
    if not data then return nil end
    if not images[data] then
      local img = data.typeOf and data:typeOf('Texture') and data or graphics.newImage(data)
      img:setFilter('nearest','nearest')
      images[data] = img
      if img~=data then owned[img]=true end
    end
    return images[data]
  end
  local function art(row, foreground)
    if not row then return nil end
    if type(row)=='table' and row.image then
      local frames
      if foreground then frames=row.foregroundFrames else frames=row.frames end
      if frames and #frames>0 then
        local now = ctx.time and ctx.time() or
          (love and love.timer and love.timer.getTime and love.timer.getTime()) or 0
        local period=row.period or .2
        assert(type(period)=='number' and period>0,'TileShift animation period must be positive')
        return image(frames[math.floor(math.max(0,now-(row.offset or 0)) / period) % #frames + 1])
      end
      if foreground then return image(row.foreground) end
      return image(row.image)
    end
    return not foreground and image(row) or nil
  end
  local function covered(row,x,y)
    return row and (type(row)~='table' or row.coverage==nil or
      row.coverage[math.floor((y%32)/16)*2+math.floor((x%32)/16)]==true)
  end
  local function record(self,replacements,id,bx,by)
    local row=replacements and replacements[id]
    if not row then return nil end
    if type(row)=='table' and row.positions and bx~=nil and by~=nil then row=row.positions[bx..':'..by] or row end
    local ts=self.map.tileset
    local grass=ts and ts.grassTile
    local block=ts and ts.blocks and ts.blocks[id+1]
    local foreground=type(row)=='table' and (row.foreground or
      (row.foregroundFrames and #row.foregroundFrames>0))
    if grass~=nil and block and not foreground then
      -- Player grass reads bottom-left; NPC grass reads top-right. Checking
      -- every covered 8px source tile also preserves either native rule.
      for i,tile in ipairs(block) do
        if tile==grass and covered(row,(i-1)%4*8,math.floor((i-1)/4)*8) then
          local key=tostring(self.map.def.tileset)..':'..tostring(id)
          if not warned[key] then
            warned[key]=true
            if ctx.warn then ctx.warn('Grass replacement needs an alpha foreground: '..key) end
          end
          return nil
        end
      end
    end
    return row
  end
  local function painted(row, bx, by, cx, cy, sx, sy, sw, sh, foreground)
    local img = art(row, foreground)
    if not img then return false end
    sx, sy, sw, sh = sx or 0, sy or 0, sw or 32, sh or 32
    local w,h=img:getDimensions()
    assert(w==32 and h==32,'TileShift Gen 1 art must be 32x32')
    local x,y=bx*32+sx-math.floor(cx),by*32+sy-math.floor(cy)
    local key=sx..','..sy..','..sw..','..sh
    local byImage=quads[img]
    if not byImage then byImage={};quads[img]=byImage end
    local q=byImage[key]
    if not q then q=graphics.newQuad(sx,sy,sw,sh,w,h);byImage[key]=q end
    graphics.draw(img,q,x,y)
    if FX.markTrueColor then FX.markTrueColor(x,y,sw,sh) end
    return true
  end
  local function paintBlock(row,bx,by,cx,cy)
    if type(row)~='table' or row.coverage==nil then
      painted(row,bx,by,cx,cy)
      return
    end
    for q=0,3 do
      if row.coverage[q]==true then
        painted(row,bx,by,cx,cy,q%2*16,math.floor(q/2)*16,16,16)
      end
    end
  end
  local function plain(fn)
    graphics.push('all')
    graphics.setShader()
    graphics.setColor(1,1,1,1)
    local ok,err=pcall(fn)
    graphics.pop()
    if not ok then error(err,0) end
  end
  local function wrap(name, callback)
    if type(T[name])~='function' then return end
    originals[name]=T[name]
    wrappers[name]=function(self,...)
      -- A later mod may retain this wrapper after TileShift loses ownership.
      -- Release our textures before drawing and make that retained link native.
      if not active() then return originals[name](self,...) end
      return callback(originals[name],self,...)
    end
    T[name]=wrappers[name]
  end
  wrap('drawWindow',function(native,self,cx,cy,vw,vh)
    local result=pack(native(self,cx,cy,vw,vh))
    local replacements=rows(self)
    if not replacements then return unpack(result,1,result.n) end
    local def=self.map.def
    vw,vh=vw or def.width*32,vh or def.height*32
    local camX,camY=math.floor(cx),math.floor(cy)
    local x0,y0=math.max(0,math.floor(camX/32)),math.max(0,math.floor(camY/32))
    local x1,y1=math.min(def.width-1,math.ceil((camX+vw)/32)-1),math.min(def.height-1,math.ceil((camY+vh)/32)-1)
    plain(function()
      for by=y0,y1 do for bx=x0,x1 do
        local id=self.map:blockAt(bx,by)
        local row=record(self,replacements,id,bx,by)
        if row then paintBlock(row,bx,by,cx,cy) end
      end end
    end)
    return unpack(result,1,result.n)
  end)
  wrap('drawBorderFill',function(native,self,cx,cy,vw,vh)
    local result=pack(native(self,cx,cy,vw,vh))
    local replacements=rows(self)
    if not replacements then return unpack(result,1,result.n) end
    local id
    if T.borderBlockFor then id=T.borderBlockFor(self.map) else id=self.map.def.borderBlock end
    local row=id~=false and id~=nil and record(self,replacements,id)
    if not row then return unpack(result,1,result.n) end
    local def=self.map.def
    if not vw or not vh then return unpack(result,1,result.n) end
    local camX,camY=math.floor(cx),math.floor(cy)
    plain(function()
      for by=math.floor(camY/32),math.ceil((camY+vh)/32)-1 do
        for bx=math.floor(camX/32),math.ceil((camX+vw)/32)-1 do
          if bx<0 or by<0 or bx>=def.width or by>=def.height then paintBlock(row,bx,by,cx,cy) end
        end
      end
    end)
    return unpack(result,1,result.n)
  end)
  -- Source grass/flower graphics must not reappear across a sprite's feet.
  -- Only an explicitly authored alpha foreground can cover the sprite.
  wrap('drawStripRaw',function(native,self,x0,y0,x1,y1,cx,cy)
    local replacements=rows(self)
    if not replacements then return native(self,x0,y0,x1,y1,cx,cy) end
    T.eachStripSpan(x0,y0,x1,y1,function(tx,ty,x,y,ox,oy,w,h)
      local bx,by=math.floor(tx/4),math.floor(ty/4)
      local row=record(self,replacements,self.map:blockAt(bx,by),bx,by)
      if covered(row,tx%4*8,ty%4*8) then
        plain(function() painted(row,bx,by,cx,cy,tx%4*8+ox,ty%4*8+oy,w,h,true) end)
      else native(self,x,y,x+w,y+h,cx,cy) end
    end)
  end)
  -- A native palette redraw would reintroduce the source grass on top of the
  -- already-painted donor foreground. Keep it only on uncovered source spans.
  wrap('markStripRedraw',function(native,self,x0,y0,x1,y1,cx,cy,colors)
    local replacements=rows(self)
    if not replacements then return native(self,x0,y0,x1,y1,cx,cy,colors) end
    T.eachStripSpan(x0,y0,x1,y1,function(tx,ty,x,y,ox,oy,w,h)
      local bx,by=math.floor(tx/4),math.floor(ty/4)
      local row=record(self,replacements,self.map:blockAt(bx,by),bx,by)
      if not covered(row,tx%4*8,ty%4*8) then
        native(self,x,y,x+w,y+h,cx,cy,colors)
      end
    end)
  end)
  cleanup=function()
    if closed then return end
    closed=true
    for name,wrapper in pairs(wrappers) do if T[name]==wrapper then T[name]=originals[name] end end
    for img in pairs(owned) do if img.release then img:release() end end
  end
  return cleanup
end

return G
