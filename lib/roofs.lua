-- Bounded decorative roof/sides. Never modifies source tiles or collision.
local R={}
function R.new(ctx)
  local G=ctx.graphics or love.graphics
  local groups,cache,textures={},{},{}
  local closed,revision,quad=false,nil,nil
  for _,row in ipairs(ctx.rows or{})do
    -- A side may render outside the map-image canvas; validate its real
    -- fingerprint anchor with the same strict mapping validator. This copy
    -- is made once at construction, never in the draw/update path.
    local checked=row
    if row.side then checked={};for k,v in pairs(row)do checked[k]=v end;checked.x=row.sourceX end
    assert(ctx.validate(checked),'Invalid reviewed decorative tile')
    local side=row.side=='left'or row.side=='right'
    local boundedSide=side and type(row.buildingX)=='number'and type(row.buildingY)=='number'
      and type(row.buildingW)=='number'and type(row.buildingH)=='number'
      and row.buildingX>=0 and row.buildingY>=0 and row.buildingW>0 and row.buildingH>0
      and row.buildingX%1==0 and row.buildingY%1==0 and row.buildingW%1==0 and row.buildingH%1==0
      and row.x==(row.side=='left'and row.buildingX-1 or row.buildingX+row.buildingW)
      and row.y>=row.buildingY and row.y<row.buildingY+row.buildingH
      and type(row.sourceX)=='number'and row.sourceX%1==0
    local above=row.side==nil and row.buildingY==row.y+1
    assert((row.game=='red'or row.game=='blue'or row.game=='yellow'or row.game=='gold'or row.game=='silver'or row.game=='crystal')and row.style=='gen3'
      and (row.kind=='original'or row.kind=='third_party'or row.kind=='native_composite')
      and row.map and row.x and row.y and(above or boundedSide),
      'Decoration must occupy one upper row or one adjacent side column')
    local games=groups[row.game]or{};groups[row.game]=games
    local maps=games[row.map]or{};games[row.map]=maps
    maps[#maps+1]=row
  end
  local self={}
  function self:cells(game,def)
    if closed or not def then return nil end
    local list=groups[game]and groups[game][def.id]
    if not list or not ctx.active()then return nil end
    local rev=ctx.revision()
    if rev~=revision then cache={};revision=rev end
    local games=cache[game]or{};cache[game]=games
    if games[def]then return games[def]end
    local result={rows={},grid={}};games[def]=result
    for i=1,list and #list or 0 do
      local row=list[i]
      if not ctx.enabled or ctx.enabled(row)then
      local ok,data=pcall(function()
        local sx=row.x
        if row.side then
          assert(row.buildingX+row.buildingW<=def.width*2 and row.buildingY+row.buildingH<=def.height*2,
            'Decorative building footprint lies outside source map')
          sx=math.max(0,math.min(def.width*2-1,row.x))
          assert(row.sourceX==sx,'Decorative side anchor changed')
        end
        assert(row.tileset==def.tileset and sx>=0 and row.y>=0
          and sx<def.width*2 and row.y<def.height*2,'Decoration lies outside checked source map')
        local bid=def.blocks[math.floor(row.y/2)*def.width+math.floor(sx/2)+1]
        assert(bid==row.id and row.quadrant==row.y%2*2+sx%2,'Decoration source position changed')
        local source,why=ctx.donor:cell({game=game,tileset=row.tileset,id=row.id,
          quadrant=row.quadrant,hash=row.sourceHash,hashOnly=true,map=def,
          monochrome=true,sourceFiles=row.sourceFiles})
        assert(source,why or'Roof source fingerprint changed')
        if row.parts then
          local piece,why=ctx.compose(row)
          assert(piece,why or'Decorative native composition unavailable')
          return piece.under
        end
        return ctx.original(row.asset,row.assetFileHash)
      end)
      if ok and data then
        -- Native compositions can produce fresh ImageData after an option
        -- revision. Keep one GPU texture per reviewed row, not per rebuild.
        local textureKey=row.parts and row or data
        local texture=textures[textureKey]
        if texture and row.parts then texture:replacePixels(data)end
        if not texture then texture=G.newImage(data);texture:setFilter('nearest','nearest');textures[textureKey]=texture end
        local entry={x=row.x,y=row.y,data=data,texture=texture,
          frontY=row.side and(row.buildingY+row.buildingH)*16 or nil}
        local line=result.rows[row.y]or{};result.rows[row.y]=line
        assert(not result.grid[row.y*65536+row.x],'Duplicate roof overhang')
        result.grid[row.y*65536+row.x]=entry;line[#line+1]=entry
      elseif ctx.warn then ctx.warn('TileShift skipped roof overhang: '..tostring(data))end
      end
    end
    return result
  end
  function self:map(world,def,ox,oy,s)
    if not world or world.daytime=='DARK'then return end
    local cells=self:cells(ctx.version(),def);if not cells then return end
    local cam=world.camera;s=s or 1;ox,oy=ox or 0,oy or 0
    local cx,cy=cam and cam.x or 0,cam and cam.y or 0
    local first=math.max(0,math.floor((cy-oy)/16)-1)
    local last=math.min(def.height*2-1,math.floor((cy-oy+(world.viewH or 144))/16))
    G.push('all');G.setShader();G.setColor(1,1,1,1)
    for y=first,last do
      local line=cells.rows[y]
      for i=1,line and #line or 0 do
        local e=line[i]
        local x=e.x*16+ox-cx
        if x+16>=0 and x<=(world.viewW or 160)then
          local dx,dy=math.floor(x*s),math.floor((y*16+oy-cy)*s)
          G.draw(e.texture,dx,dy,0,s,s)
          if ctx.markTrueColor then ctx.markTrueColor(dx,dy,16*s,16*s)end
        end
      end
    end
    G.pop()
  end
  function self:actor(map,entity,ox,oy,s,moved,now,world)
    if not map or not entity or not world or world.daytime=='DARK'then return end
    local cells=self:cells(ctx.version(),map.def);if not cells then return end
    local sprite=entity.sprite
    local fw,fh=sprite and sprite.frameWidth or 16,sprite and sprite.frameHeight or 16
    local ax,ay=sprite and sprite.anchorX or fw/2,sprite and sprite.anchorY or fh
    local x0=math.floor(entity.px+8-ax)
    local y0=math.floor(entity.py+(entity.spriteYOffset or 0)+12-ay)
    local x1,y1=x0+fw,y0+fh;s=s or 1;ox,oy=ox or 0,oy or 0
    for ty=math.floor(y0/16),math.floor((y1-1)/16)do
      for tx=math.floor(x0/16),math.floor((x1-1)/16)do
        local entry=cells.grid[ty*65536+tx]
        if entry and(not entry.frontY or entity.py+12<entry.frontY)then
          local xx,yy=math.max(x0,tx*16),math.max(y0,ty*16)
          local w,h=math.min(x1,tx*16+16)-xx,math.min(y1,ty*16+16)-yy
          if not quad then quad=G.newQuad(0,0,16,16,16,16)end
          quad:setViewport(xx-tx*16,yy-ty*16,w,h,16,16)
          G.push('all');G.setShader();G.setColor(1,1,1,1)
          G.draw(entry.texture,quad,math.floor(ox+xx*s),math.floor(oy+yy*s),0,s,s);G.pop()
          if ctx.markTrueColor then ctx.markTrueColor(math.floor(ox+xx*s),math.floor(oy+yy*s),w*s,h*s)end
        end
      end
    end
  end
  function self:dispose()
    if closed then return end;closed=true;cache={}
    for _,texture in pairs(textures)do texture:release()end
    textures={};if quad and quad.release then quad:release()end
  end
  return self
end
return R
