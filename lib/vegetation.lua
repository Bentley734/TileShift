-- Observe existing entity draws; never run another per-frame entity scan.
local V={}
function V.new(ctx)
  local self={mode='always'}
  local patches={}
  local bound=setmetatable({},{__mode='k'})
  local closed=false
  local lastWorld,lastMap,lastEntities,lastNpcs,lastPlayer,lastCount,lastNpcCount
  function self:setMode(mode)
    assert(mode=='always' or mode=='walked','Unknown grass animation mode')
    if mode==self.mode then return false end
    self.mode=mode;patches={};return true
  end
  function self:touch(map,x,y,now,duration)
    if self.mode~='walked' then return end
    local cells=patches[map]
    if not cells then cells={};patches[map]=cells end
    local key=y*65536+x
    local cell=cells[key]
    if not cell or now>=cell.expires then cell={start=now};cells[key]=cell end
    cell.expires=now+duration
  end
  function self:time(map,x,y,now)
    if self.mode=='always' then return now end
    local cells=patches[map];local key=y*65536+x
    local cell=cells and cells[key]
    if not cell then return nil end
    if now>=cell.expires then cells[key]=nil;return nil end
    return now-cell.start
  end
  local function after(record,entity,ox,oy,scale,...)
    if closed or not ctx.active() then return ... end
    local map=record.world.map
    if not map or not entity.px or not entity.py then return ... end
    local x,y=entity.px,entity.py
    local moved=record.map==map and record.x~=nil and
      (x~=record.x or y~=record.y) and
      math.abs(x-record.x)<=16 and math.abs(y-record.y)<=16
      and not entity.jumping and not entity.hopShadowY
    record.x,record.y,record.map=x,y,map
    ctx.draw(map,entity,ox or 0,oy or 0,scale or 1,moved,ctx.time(),record.world)
    return ...
  end
  local function bindEntity(entity,world)
    if not entity or type(entity.draw)~='function' then return end
    local record=bound[entity]
    if record then record.world=world;return end
    record={world=world,original=entity.draw}
    record.wrapper=function(e,...)
      local ox,oy,scale=...
      return after(record,e,ox,oy,scale,record.original(e,...))
    end
    bound[entity]=record;entity.draw=record.wrapper
  end
  function self:bind(world)
    if closed or not world then return end
    local entities,npcs=world.entities,world.npcs
    local count,npcCount=entities and #entities or 0,npcs and #npcs or 0
    if world==lastWorld and world.map==lastMap and entities==lastEntities and
      npcs==lastNpcs and world.player==lastPlayer and count==lastCount and npcCount==lastNpcCount then
      -- Spawners append actors. Catch a same-count remove/add without scanning.
      if count>0 then bindEntity(entities[count],world)end
      if npcCount>0 then bindEntity(npcs[npcCount],world)end
      return
    end
    if world.map~=lastMap then patches={} end
    lastWorld,lastMap,lastEntities,lastNpcs,lastPlayer=world,world.map,entities,npcs,world.player
    lastCount,lastNpcCount=count,npcCount
    bindEntity(world.player,world)
    for _,entity in ipairs(entities or {})do bindEntity(entity,world) end
    for _,entity in ipairs(npcs or {})do bindEntity(entity,world) end
  end
  function self:dispose()
    if closed then return end
    closed=true;patches={}
    for entity,record in pairs(bound)do
      if entity.draw==record.wrapper then entity.draw=record.original end
    end
  end
  return self
end
return V
