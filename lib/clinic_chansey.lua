-- A render-only clinic resident. Native actors, scripts and collision remain
-- owned by the game; the live nurse supplies every facing, including healing.
local Clinic = {}
local HOSTS = {gold=true,silver=true,crystal=true}
local FACINGS = {'down','up','left','right'}
local DIRECTIONS = {down=true,up=true,left=true,right=true}
local unpack_ = unpack or table.unpack

local function finite(n)
  return type(n)=='number' and n==n and n~=math.huge and n~=-math.huge
end

local function providerReady(p)
  if type(p)~='table' or not p.image or not finite(p.width) or p.width<=0
    or not finite(p.height) or p.height<=0 or not finite(p.scale) or p.scale<=0
    or not finite(p.anchorX) or not finite(p.anchorY) or not finite(p.footY)
    or type(p.isValid)~='function' or type(p.quads)~='table'
    or type(p.oamQuads)~='table' or type(p.oamOffsetY)~='table'
    or type(p.oamHeight)~='table' then return false end
  for _,facing in ipairs(FACINGS) do
    if not p.quads[facing] then return false end
    for _,row in ipairs({'top','bottom'}) do
      if type(p.oamQuads[row])~='table' or not finite(p.oamHeight[row])
        or p.oamHeight[row]<0 or (p.oamHeight[row]>0 and not p.oamQuads[row][facing])
        or not finite(p.oamOffsetY[row]) then return false end
    end
  end
  return true
end

function Clinic.install(ctx)
  assert(type(ctx)=='table','Clinic services required')
  assert(type(ctx.catalog)=='table' and type(ctx.style)=='function'
    and type(ctx.version)=='function' and type(ctx.valid)=='function','Clinic services required')
  local Require = ctx.require or require
  local World = ctx.World or Require('src.world.gen2.World')
  assert(type(World)=='table','Clinic world required')
  local G = ctx.graphics or love.graphics
  local Renderer = ctx.SpriteRenderer or Require('src.render.SpriteRenderer')
  local Palettes = ctx.Palettes or Require('src.world.gen2.Palettes')
  local runtime=ctx.runtime
  if not runtime and not ctx.providerEpoch then
    local ok,value=pcall(Require,'src.mods.Runtime');if ok then runtime=value end
  end
  local function epoch()
    if ctx.providerEpoch then return ctx.providerEpoch() end
    local hooks=runtime and runtime.hooks
    return hooks,hooks and hooks.ownerEpoch and hooks:ownerEpoch('wildfollowers')
  end
  local indexed = {}
  for _,r in ipairs(ctx.catalog.records or ctx.catalog) do
    assert(HOSTS[r.game] and type(r.map)=='string' and type(r.nurse)=='table')
    local game = indexed[r.game] or {}; indexed[r.game] = game
    assert(not game[r.map],'Duplicate clinic source binding');game[r.map]=r
  end
  local worlds = setmetatable({}, {__mode='k'})
  local attempted = setmetatable({}, {__mode='k'})
  local originals,wrappers = {},{}
  local closed = false
  local self = {prepared=0,draws=0}

  local function enabled()
    return not closed and ctx.style()=='gen3' and (not ctx.active or ctx.active())
  end

  local function binding(world, r)
    local map = world and world.map
    local def = map and map.def
    if not (def and map.id==r.map and def.tileset==r.tileset
      and type(def.width)=='number' and type(def.blocks)=='table') then return false end
    for _,cell in ipairs(r.cells or {}) do
      local index=math.floor(cell.y/2)*def.width+math.floor(cell.x/2)+1
      if def.blocks[index]~=cell.id then return false end
    end
    return true
  end

  local function liveNurse(world,r)
    for _,npc in ipairs(world.npcs or {}) do
      local def=npc.def
      if def and def.index==r.nurse.index and def.sprite==r.nurse.sprite
        and def.x==r.nurse.x and def.y==r.nurse.y
        and (not r.nurse.scriptKey or def.scriptKey==r.nurse.scriptKey) then return npc end
    end
  end

  local function current(memo,world)
    return enabled() and memo and world.daytime~='DARK' and memo.map==world.map and memo.npcs==world.npcs
      and memo.game==ctx.version() and binding(world,memo.record)
  end

  local function palette(world,memo)
    local proxy=memo.proxy
    proxy.sprite=proxy.nativeSprite;proxy.spriteDef=proxy.nativeDef
    proxy.nativeSprite:setObjPalette(nil,'tileshift:clinic_chansey:unresolved')
    if world.applySpritePalette then world:applySpritePalette(proxy) end
    proxy.paletteSource='native'
    -- Keep the native four-facing shape, with this edition's own Chansey
    -- colors rather than the generic fairy's orange-red object palette.
    local ok,colors=pcall(Palettes.monColors,world.palettes,'CHANSEY',false)
    if ok and type(colors)=='table' then
      local pieces={'tileshift:clinic_chansey',memo.game or ctx.version()}
      local valid=true
      for i=1,4 do for j=1,3 do
        local value=type(colors[i])=='table' and colors[i][j]
        if not finite(value) or value<0 or value>255 then valid=false
        else pieces[#pieces+1]=tostring(value) end
      end end
      if valid then
        proxy.nativeSprite:setObjPalette(colors,table.concat(pieces,':'))
        proxy.paletteSource='chansey'
      end
    end
    -- resolveImage performs the native OBJ bake here, never on the first draw.
    if proxy.nativeSprite.resolveImage then proxy.nativeSprite:resolveImage() end
  end

  local function provider()
    local api=ctx.resolveProvider and ctx.resolveProvider()
    api=type(api)=='table' and (api.overworldSprites or api) or nil
    if not (api and api.version==1 and type(api.prepare)=='function') then return nil end
    local ok,p=pcall(api.prepare,113,{role='resident',sourceOverrides={companion='ee'}})
    if ok and providerReady(p) then
      local live,value=pcall(p.isValid);if live and value==true then return p end
    end
  end

  local function drawResident(proxy,ox,oy,s,oamRow)
    s=s or 1
    local p=proxy.preparedProvider
    local valid=false
    if p then local ok,value=pcall(p.isValid);valid=ok and value==true end
    if not valid then
      proxy.drawSource='native';proxy.sprite=proxy.nativeSprite;proxy.spriteDef=proxy.nativeDef
      G.push('all');G.translate(ox or 0,oy or 0);G.scale(s,s)
      proxy.nativeSprite:draw(proxy.px,proxy.py,0,0,proxy.facing,0,false,false,false,nil,oamRow)
      G.pop();return
    end
    proxy.drawSource=p.source or 'wildfollowers';proxy.sprite=proxy.providerSprite
    proxy.spriteDef=proxy.providerDef
    local quad=p.quads[proxy.facing]
    local offset,height=0,p.height
    if oamRow=='top' or oamRow=='bottom' then
      quad=p.oamQuads[oamRow][proxy.facing];offset=p.oamOffsetY[oamRow];height=p.oamHeight[oamRow]
    end
    if not quad or height<=0 then return end
    local scale=p.scale*s
    local x=(ox or 0)+(proxy.px+8)*s-p.anchorX*scale
    local y=(oy or 0)+(proxy.py+p.footY)*s-p.anchorY*scale+offset*scale
    G.push('all');G.setShader();G.setColor(1,1,1,1)
    if ctx.markTrueColor then ctx.markTrueColor(x,y,p.width*scale,height*scale) end
    G.draw(p.image,quad,x,y,0,scale,scale);G.pop()
  end

  function self:prepare(world)
    if not world then return false end
    local game=ctx.version()
    local active=enabled();local bus,token=epoch()
    attempted[world]={map=world.map,npcs=world.npcs,game=game,active=active,bus=bus,epoch=token}
    local r=active and indexed[game] and world.map and indexed[game][world.map.id]
    if not r or not binding(world,r) or not ctx.valid(world,r) then worlds[world]=nil;return false end
    local nurse=liveNurse(world,r)
    local nativeDef=world.sprites and world.sprites.SPRITE_FAIRY
    if not nurse or not nativeDef then worlds[world]=nil;return false end
    local memo=worlds[world]
    if not memo or memo.record~=r or memo.proxy.nativeDef~=nativeDef then
      local proxy={id='tileshift_clinic_chansey',species='CHANSEY',national=113,
        cellX=r.x,cellY=r.y,px=r.x*16,py=r.y*16,
        facing=nurse.facing or 'down',inGrass=false,moving=false,progress=0,spriteYOffset=0,
        def={sprite='SPRITE_FAIRY',palette=0},nativeDef=nativeDef,draw=drawResident}
      proxy.nativeSprite=Renderer.new(nativeDef,'tileshift_clinic_chansey')
      local entry={entity=proxy,ox=0,oy=0,py=proxy.py,seq=0}
      entry.drawSprite=function(oamRow,ox,oy,s)
        proxy:draw(ox or entry.sx,oy or entry.sy,s or entry.s,oamRow)
      end
      memo={record=r,proxy=proxy,entry=entry};worlds[world]=memo
    end
    memo.map=world.map;memo.npcs=world.npcs;memo.nurse=nurse;memo.game=game
    memo.proxy.facing=DIRECTIONS[nurse.facing] and nurse.facing or 'down'
    palette(world,memo)
    local p=provider();memo.provider=p;memo.proxy.preparedProvider=p
    if p then
      memo.proxy.providerSprite={frameWidth=p.width*p.scale,frameHeight=p.height*p.scale,
        anchorX=p.anchorX*p.scale,anchorY=p.anchorY*p.scale}
      memo.proxy.providerDef={id='TILESHIFT_CLINIC_CHANSEY',frames=1,trueColor=true,gbaArt=true}
    end
    memo.bus,memo.epoch=epoch();self.prepared=self.prepared+1
    return true
  end

  function self:refresh(world)
    if world then return self:prepare(world) end
    for w in pairs(worlds) do self:prepare(w) end
  end

  function self:resident(world)
    local memo=worlds[world]
    return memo and memo.proxy,memo and memo.nurse,memo and memo.provider
  end

  -- Called from update, never from a draw. A changed owner token revives a
  -- hot-enabled provider without polling missing sprite files every frame.
  function self:poll(world)
    local memo=worlds[world]
    if not world or not enabled() then return false end
    local bus,token=epoch()
    if not memo then
      local prior=attempted[world]
      if not prior or prior.map~=world.map or prior.npcs~=world.npcs
        or prior.game~=ctx.version() or not prior.active or prior.bus~=bus or prior.epoch~=token then
        return self:prepare(world)
      end
      return false
    end
    if memo.map~=world.map or memo.npcs~=world.npcs then return self:prepare(world) end
    if bus~=memo.bus or token~=memo.epoch then return self:prepare(world) end
    local p=memo.provider
    if p then
      local ok,value=pcall(p.isValid)
      if not ok or value~=true then return self:prepare(world) end
    end
    return false
  end

  local function wrap(name,builder)
    local old=World[name]
    if type(old)~='function' then return end
    local wrapper=builder(old);originals[name]=old;wrappers[name]=wrapper;World[name]=wrapper
  end

  wrap('drawPersonEntry',function(old)
    return function(world,entry,s)
      local memo=worlds[world]
      if current(memo,world) and entry and entry.entity==memo.nurse
        and (entry.ox or 0)==0 and (entry.oy or 0)==0 and not world.peopleHidden
        and not memo.nurse.hiddenByMovement then
        local proxy=memo.proxy
        proxy.facing=DIRECTIONS[memo.nurse.facing] and memo.nurse.facing or 'down'
        if not world.spriteFilter or world.spriteFilter(proxy) then
          local extra=memo.entry;extra.sx=entry.sx;extra.sy=entry.sy;extra.s=s or entry.s or 1
          self.draws=self.draws+1;old(world,extra,extra.s)
        end
      end
      return old(world,entry,s)
    end
  end)

  local function prepared(world,...)
    local result={n=select('#',...),...};self:prepare(world)
    return unpack_(result,1,result.n)
  end
  for _,name in ipairs({'setMap','rebuildPeople'}) do
    wrap(name,function(old)
      return function(world,...) return prepared(world,old(world,...)) end
    end)
  end
  wrap('applyPalettes',function(old)
    local function applied(world,...)
      local result={n=select('#',...),...};local memo=worlds[world]
      if memo and enabled() then palette(world,memo) end
      return unpack_(result,1,result.n)
    end
    return function(world,...) return applied(world,old(world,...)) end
  end)

  function self:dispose()
    if closed then return end;closed=true
    for name,wrapper in pairs(wrappers) do if World[name]==wrapper then World[name]=originals[name] end end
    for world in pairs(worlds) do worlds[world]=nil end
    for world in pairs(attempted) do attempted[world]=nil end
  end
  return self
end

return Clinic
