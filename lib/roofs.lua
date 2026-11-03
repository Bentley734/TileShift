-- Bounded decorative roof/sides. Never modifies source tiles or collision.
local R={}
function R.new(ctx)
  local G=ctx.graphics or love.graphics
  local groups,trees,cache,textures={},{},{},{}
  local closed,revision,quad=false,nil,nil
  local staticBorders=false
  for _,row in ipairs(ctx.rows or{})do
    -- A side may render outside the map-image canvas; validate its real
    -- fingerprint anchor with the same strict mapping validator. This copy
    -- is made once at construction, never in the draw/update path.
    local checked=row
    if row.side or row.sourceY~=nil or row.sourceX~=nil then
      checked={};for k,v in pairs(row)do checked[k]=v end
      checked.x=row.sourceX or row.x;checked.y=row.sourceY or row.y
    end
    assert(ctx.validate(checked),'Invalid reviewed decorative tile')
    local side=row.side=='left'or row.side=='right'
    local boundedSide=side and type(row.buildingX)=='number'and type(row.buildingY)=='number'
      and type(row.buildingW)=='number'and type(row.buildingH)=='number'
      and row.buildingX>=0 and row.buildingY>=0 and row.buildingW>0 and row.buildingH>0
      and row.buildingX%1==0 and row.buildingY%1==0 and row.buildingW%1==0 and row.buildingH%1==0
      and type(row.x)=='number'and row.x%1==0
      and ((row.side=='left'and row.x>=row.buildingX-2 and row.x<row.buildingX)
        or(row.side=='right'and row.x>=row.buildingX+row.buildingW and row.x<=row.buildingX+row.buildingW+1))
      and row.y>=row.buildingY and row.y<row.buildingY+row.buildingH
      and type(row.sourceX)=='number'and row.sourceX%1==0
    local above=row.side==nil and row.buildingY==row.y+1
    if row.sourceY~=nil then
      assert(above and row.y==-1 and row.buildingY==0 and row.sourceY==0,
        'Static north overhang must use the first source row')
    end
    if row.sourceX~=nil then
      assert(type(row.sourceX)=='number'and row.sourceX%1==0 and row.sourceX>=0,
        'Invalid decorative source column')
    end
    if row.sourceY~=nil or(row.sourceX~=nil and not row.side)then
      assert(above and type(row.buildingX)=='number'and row.buildingX>=0 and row.buildingX%1==0
        and type(row.buildingW)=='number'and row.buildingW>0 and row.buildingW%1==0
        and type(row.buildingH)=='number'and row.buildingH>0 and row.buildingH%1==0
        and row.x>=row.buildingX-2 and row.x<=row.buildingX+row.buildingW+1,
        'Anchored upper decoration must remain within its building envelope')
    end
    assert((row.game=='red'or row.game=='blue'or row.game=='yellow'or row.game=='gold'or row.game=='silver'or row.game=='crystal')and row.style=='gen3'
      and (row.kind=='original'or row.kind=='third_party'or row.kind=='native_composite')
      and row.map and row.x and row.y and(above or boundedSide),
      'Decoration must occupy one upper row or at most two adjacent side columns')
    local games=groups[row.game]or{};groups[row.game]=games
    local maps=games[row.map]or{};games[row.map]=maps
    maps[#maps+1]=row
    if row.side or row.sourceY~=nil or row.sourceX~=nil then staticBorders=true end
  end
  for _,row in ipairs(ctx.treeRows or{})do
    assert(ctx.validate(row)and row.canopy and row.role=='dense_conifer_crown'
      and row.style=='gen3'and(row.game=='gold'or row.game=='silver'or row.game=='crystal')
      and row.map and row.x==nil and row.y==nil,'Invalid reviewed tree canopy')
    local games=trees[row.game]or{};trees[row.game]=games
    local maps=games[row.map]or{};games[row.map]=maps
    local block=maps[row.id]or{};maps[row.id]=block
    assert(block[row.quadrant]==nil,'Duplicate tree canopy source alias')
    block[row.quadrant]=row
  end
  local self={}
  function self:cells(game,def)
    if closed or not def then return nil end
    local list=groups[game]and groups[game][def.id]
    local treeList=trees[game]and trees[game][def.id]
    if(not list and not treeList)or not ctx.active()then return nil end
    local rev=ctx.revision()
    if rev~=revision then cache={};revision=rev end
    local games=cache[game]or{};cache[game]=games
    if games[def]then return games[def]end
    local result={rows={},grid={},minY=0};games[def]=result
    local function append(row,x,y,sourceY,canopy)
      if not ctx.enabled or ctx.enabled(row)then
      local ok,data=pcall(function()
        local sx,sy=row.sourceX or x,sourceY or row.sourceY or y
        if row.side then
          assert(row.buildingX+row.buildingW<=def.width*2 and row.buildingY+row.buildingH<=def.height*2,
            'Decorative building footprint lies outside source map')
          sx=math.max(0,math.min(def.width*2-1,row.x))
          assert(row.sourceX==sx,'Decorative side anchor changed')
        elseif row.sourceX~=nil then
          assert(row.sourceX==math.max(0,math.min(def.width*2-1,x)),
            'Upper decoration source anchor changed')
        end
        if row.sourceY~=nil then
          assert(row.buildingX+row.buildingW<=def.width*2 and row.buildingY+row.buildingH<=def.height*2,
            'North-edge building footprint lies outside source map')
        end
        assert(row.tileset==def.tileset and sx>=0 and sy>=0
          and sx<def.width*2 and sy<def.height*2,'Decoration lies outside checked source map')
        if canopy then assert(y==sy-1 and sy+1<def.height*2,'Canopy must sit one cell above its two-cell tree')end
        local bid=def.blocks[math.floor(sy/2)*def.width+math.floor(sx/2)+1]
        assert(bid==row.id and row.quadrant==sy%2*2+sx%2,'Decoration source position changed')
        local source,why=ctx.donor:cell({game=game,tileset=row.tileset,id=row.id,
          quadrant=row.quadrant,hash=row.sourceHash,hashOnly=true,map=def,
          monochrome=true,sourceFiles=row.sourceFiles})
        assert(source,why or'Roof source fingerprint changed')
        if row.parts then
          local piece,why=ctx.compose(row)
          assert(piece,why or'Decorative native composition unavailable')
          return piece.under
        end
        return ctx.original(canopy and row.canopy.asset or row.asset,canopy and row.canopy.hash or row.assetFileHash)
      end)
      if ok and data then
        -- Native compositions can produce fresh ImageData after an option
        -- revision. Keep one GPU texture per reviewed row, not per rebuild.
        local textureKey=row.parts and row or data
        local texture=textures[textureKey]
        if texture and row.parts then texture:replacePixels(data)end
        if not texture then texture=G.newImage(data);texture:setFilter('nearest','nearest');textures[textureKey]=texture end
        local entry={x=x,y=y,data=data,texture=texture,role=canopy and'dense_conifer_canopy'or row.role,
          treeCanopy=canopy or nil,sourceY=canopy and sourceY or nil,
          outside=x<0 or y<0 or x>=def.width*2 or y>=def.height*2,
          frontY=canopy and(sourceY+2)*16 or(row.side and(row.buildingY+row.buildingH)*16 or nil)}
        result.minY=math.min(result.minY,y)
        -- Adjacent native buildings may share a decorative cell. Retain their
        -- draw order and separate physical front/behind boundaries. This
        -- linked stack is constructed once, never rebuilt in map/actor draws.
        local key=y*65536+x
        local previous=result.grid[key]
        if canopy and previous then
          -- Keep existing building order. A nearer canopy covers a farther
          -- side; buildings win equal-depth ties and overhead roofs stay above.
          local before,current=nil,previous
          while current and current.frontY and current.frontY<entry.frontY do before=current;current=current.next end
          entry.next=current
          if before then before.next=entry else result.grid[key]=entry end
          local depth=0;current=result.grid[key]
          while current do depth=depth+1;current=current.next end
          assert(depth<=4,'More than four overlapping decorative entries')
        elseif previous then
          local depth=1
          while previous.next do previous=previous.next;depth=depth+1 end
          assert(depth<4,'More than four overlapping decorative entries')
          previous.next=entry
        else result.grid[key]=entry end
      elseif ctx.warn then ctx.warn('TileShift skipped roof overhang: '..tostring(data))end
      end
    end
    for i=1,list and #list or 0 do
      local row=list[i];append(row,row.x,row.y)
    end
    if treeList then
      -- Expand the actual source block grid once per map/revision. Generic
      -- aliases retain their real source guards, including a y=-1 canopy.
      for index,bid in ipairs(def.blocks)do
        local aliases=treeList[bid]
        if aliases then for q=0,3 do
          local row=aliases[q]
          if row then
            local x=(index-1)%def.width*2+q%2
            local sy=math.floor((index-1)/def.width)*2+math.floor(q/2)
            append(row,x,sy-1,sy,true)
          end
        end end
      end
    end
    local roots={}
    for _,entry in pairs(result.grid)do
      local line=roots[entry.y]or{};roots[entry.y]=line;line[#line+1]=entry
    end
    for y,line in pairs(roots)do
      table.sort(line,function(a,b)return a.x<b.x end)
      local ordered={};result.rows[y]=ordered
      for _,entry in ipairs(line)do
        while entry do ordered[#ordered+1]=entry;entry=entry.next end
      end
    end
    return result
  end
  function self:map(world,def,ox,oy,s,edgeMode)
    if not world or world.daytime=='DARK'then return end
    local cells=self:cells(ctx.version(),def);if not cells then return end
    local cam=world.camera;s=s or 1;ox,oy=ox or 0,oy or 0
    local cx,cy=cam and cam.x or 0,cam and cam.y or 0
    local first=math.max(cells.minY,math.floor((cy-oy)/16)-1)
    local last=math.min(def.height*2-1,math.floor((cy-oy+(world.viewH or 144))/16))
    if edgeMode=='onlyBorder'then
      if cells.minY~=-1 then return end
      first,last=-1,-1
    end
    G.push('all');G.setShader();G.setColor(1,1,1,1)
    for y=first,last do
      local line=cells.rows[y]
      for i=1,line and #line or 0 do
        local e=line[i]
        local x=e.x*16+ox-cx
        if(edgeMode~='withoutBorder'or y>=0)and x+16>=0 and x<=(world.viewW or 160)then
          local dx,dy=math.floor(x*s),math.floor((y*16+oy-cy)*s)
          G.draw(e.texture,dx,dy,0,s,s)
          if ctx.markTrueColor then ctx.markTrueColor(dx,dy,16*s,16*s)end
        end
      end
    end
    G.pop()
  end
  function self:borders(world,s)
    if closed or not ctx.active()or not next(trees)or not world or not world.maps or world.daytime=='DARK'then return end
    -- Neighbors' canvases are drawn before the current map. Replay only their
    -- one outside canopy row afterward, so it cannot disappear at a connection.
    for _,neighbor in ipairs(world.neighbors or{})do
      local def=world.maps[neighbor.id]
      if def then self:map(world,def,neighbor.ox,neighbor.oy,s,'onlyBorder')end
    end
  end
  function self:actor(map,entity,ox,oy,s,moved,now,world,originX,originY,borderOnly,actorOriginX,actorOriginY)
    if closed or not ctx.active()or not map or not entity or not world or world.daytime=='DARK'then return end
    local def=map.def or map
    local cells=self:cells(ctx.version(),def)
    local primary=originX==nil
    originX,originY=originX or 0,originY or 0
    actorOriginX,actorOriginY=actorOriginX or 0,actorOriginY or 0
    local sprite=entity.sprite
    local fw,fh=sprite and sprite.frameWidth or 16,sprite and sprite.frameHeight or 16
    local ax,ay=sprite and sprite.anchorX or fw/2,sprite and sprite.anchorY or fh
    local x0=math.floor(entity.px+actorOriginX+8-ax)-originX
    local y0=math.floor(entity.py+actorOriginY+(entity.spriteYOffset or 0)+12-ay)-originY
    local x1,y1=x0+fw,y0+fh;s=s or 1;ox,oy=ox or 0,oy or 0
    if cells then for ty=math.floor(y0/16),math.floor((y1-1)/16)do
      for tx=math.floor(x0/16),math.floor((x1-1)/16)do
        local entry=cells.grid[ty*65536+tx]
        if entry then
          local xx,yy=math.max(x0,tx*16),math.max(y0,ty*16)
          local w,h=math.min(x1,tx*16+16)-xx,math.min(y1,ty*16+16)-yy
          if not quad then quad=G.newQuad(0,0,16,16,16,16)end
          quad:setViewport(xx-tx*16,yy-ty*16,w,h,16,16)
          while entry do
            if(not borderOnly or entry.outside)
              and(not entry.frontY or entity.py+actorOriginY+12<entry.frontY+originY)then
              G.push('all');G.setShader();G.setColor(1,1,1,1)
              G.draw(entry.texture,quad,math.floor(ox+(xx+originX)*s),math.floor(oy+(yy+originY)*s),0,s,s);G.pop()
              if ctx.markTrueColor then ctx.markTrueColor(math.floor(ox+(xx+originX)*s),math.floor(oy+(yy+originY)*s),w*s,h*s)end
            end
            entry=entry.next
          end
        end
      end
    end end
    if primary and(staticBorders or next(trees))and world.neighbors then
      for _,neighbor in ipairs(world.neighbors)do
        -- Gen1 neighbors retain loaded native Map objects; Gen2 keeps their
        -- definitions by ID. Only cached decorations outside that source map
        -- can cross over an actor in the current map.
        local neighborDef=neighbor.map and(neighbor.map.def or neighbor.map)
          or(world.maps and world.maps[neighbor.id])
        if neighborDef then
          local ownMap=neighbor.ox==actorOriginX and neighbor.oy==actorOriginY
          self:actor(neighborDef,entity,ox,oy,s,moved,now,world,neighbor.ox,neighbor.oy,not ownMap,actorOriginX,actorOriginY)
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
