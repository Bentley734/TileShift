-- Theme only the native ride's cached artwork. Its routine, three scroll bands,
-- player OAM, music, timing and engine-owned resources remain native.
local Theme={}
local SHIFTS={0,1,0,-1}
local function same(a,b)
  if type(a)~='table' or #a~=#b then return false end
  for i,v in ipairs(b)do if a[i]~=v then return false end end
  return true
end
local function release(value)
  if value and value.release then value:release()end
end
function Theme.install(ctx)
  assert(ctx and ctx.catalog and ctx.style and ctx.version and ctx.active,'Ride services required')
  local self={prepared=0,builds=0,draws=0}
  local closed=false
  local warned={}
  local function warn(key,message)
    if not warned[key]then warned[key]=true;if ctx.warn then ctx.warn(message)end end
  end
  local ok,Class=pcall(ctx.require or require,'src.ui.gen2.MagnetTrainRide')
  if not(ok and type(Class)=='table'and type(Class.backgrounds)=='function'
    and type(Class.backdrop)=='function')then
    warn('class','Magnet Train artwork unavailable on this engine; using its native ride')
    function self:dispose()closed=true end
    return self
  end
  local native={backgrounds=Class.backgrounds,backdrop=Class.backdrop}
  local wrapped={}
  local scenes=setmetatable({},{__mode='k'})
  local function clear(scene)
    local memo=scenes[scene]
    if memo then for _,frame in ipairs(memo.frames or {})do release(frame[1]);release(frame[2])end end
    scenes[scene]=nil
  end
  local function enabled()
    return not closed and ctx.style()=='gen3'and ctx.active()
  end
  local function guard(scene,host)
    local data=scene.data
    local gfx=data and data.gen2Field and data.gen2Field.magnetTrain
    local ts=data and data.gen2Tilesets and data.gen2Tilesets.TILESET_TRAIN_STATION
    return scene.game and(not ctx.game or ctx.game()==scene.game)and scene.game.data==data and scene.tileset==ts and ts and ts.image==host.sheet
      and scene.ride and same(gfx and gfx.bgTiles,host.bgTiles)and same(gfx and gfx.tilemap,host.tilemap)
      and same(scene.ride.bgTiles,host.bgTiles)and same(scene.ride.fgTilemap,host.tilemap)
  end
  local function rawSource(scene,game,host)
    for path,expected in pairs(host.files)do
      local bytes=assert(ctx.source(game,path),'Magnet Train source missing: '..path)
      assert(ctx.hash(bytes)==expected,'Magnet Train source changed: '..path)
    end
    local sheet=assert(ctx.sourceSheet(game,host.sheet))
    local w,h=sheet:getDimensions();assert(w==host.width and h==host.height,'Magnet Train sheet dimensions changed')
    local raw=ctx.newData(256,144)
    for y=0,17 do for x=0,31 do
      local id=(y>=6 and y<10 and x<20)and host.tilemap[(y-6)*20+x+1]or host.bgTiles[y*2+x%2+1]
      assert(type(id)=='number'and id%1==0 and id>=0 and math.floor(id/16)*8+8<=h,'Invalid native train tile')
      raw:paste(sheet,x*8,y*8,id%16*8,math.floor(id/16)*8,8,8)
    end end
    release(sheet)
    return raw
  end
  local function blend(out,x,y,r,g,b,a)
    if a<=0 then return end
    if a<1 then local br,bg,bb=out:getPixel(x,y);r=r*a+br*(1-a);g=g*a+bg*(1-a);b=b*a+bb*(1-a)end
    out:setPixel(x,y,r,g,b,1)
  end
  local function build(scene,game,host,memo)
    assert(guard(scene,host),'Magnet Train live source differs from its reviewed layout')
    local raw=rawSource(scene,game,host)
    local art=ctx.catalog
    local ground=assert(ctx.native(art.ground))
    local concrete=assert(ctx.native(art.concrete))
    local edge=assert(ctx.compose(art.edge).under)
    local rails={ctx.asset(art.rails[1].asset,art.rails[1].hash),ctx.asset(art.rails[2].asset,art.rails[2].hash)}
    local trees={}
    for _,y in ipairs({0,112})do for x=0,224,32 do
      local sprite=assert(ctx.tree(game..':MAGNET_TRAIN:big_trees:'..x..':'..y))
      local w,h=sprite:getDimensions();assert(w==32 and h==32,'Ride tree must remain complete native32x32')
      local rows={}
      for sy=0,31 do
        local lo,hi=32,-1
        for sx=0,31 do local _,_,_,a=sprite:getPixel(sx,sy);if a>0 then lo=math.min(lo,sx);hi=math.max(hi,sx)end end
        rows[sy]={lo,hi}
      end
      trees[#trees+1]={x=x,y=y,image=sprite,rows=rows}
    end end
    for phase,offset in ipairs(SHIFTS)do
      local base=ctx.newData(256,144)
      for y=0,128,16 do for x=0,240,16 do base:paste(ground,x,y,0,0,16,16)end end
      for _,tree in ipairs(trees)do for y=0,31 do
        local shift=y>=19 and 0 or offset
        if tree.rows[y][1]+shift<0 or tree.rows[y][2]+shift>=32 then shift=0 end
        for x=0,31 do blend(base,tree.x+x+shift,tree.y+y,tree.image:getPixel(x,y))end
      end end
      for x=0,240,16 do
        base:paste(edge,x,32,0,0,16,16);base:paste(rails[1],x,48,0,0,16,16)
        base:paste(rails[2],x,64,0,0,16,16);base:paste(concrete,x,80,0,0,16,16)
        base:paste(edge,x,96,0,0,16,16)
      end
      for y=0,31 do for x=0,159 do
        local n=art.exterior[y+1]
        if x>=n and x<160-n then
          local r,g,b,a=raw:getPixel(x,y+48)
          assert(r==g and g==b and a==1,'Train source must retain neutral native indices')
          local shade=math.floor((1-r)*3+.5)+1
          local colors=(y>=16 and y<24 and x>=56 and x<104)and art.gold or art.metal
          local c=assert(colors[shade]);base:setPixel(x,y+48,c[1]/255,c[2]/255,c[3]/255,1)
        end
      end end
      local overlay=ctx.newData(256,144)
      for y=0,143 do for x=0,255 do
        local r,g,b=base:getPixel(x,y);local shade=raw:getPixel(x,y)
        overlay:setPixel(x,y,r,g,b,shade==1 and 0 or 1)
      end end
      local textures={}
      memo.frames[#memo.frames+1]=textures
      textures[1]=assert(ctx.texture(base));textures[2]=assert(ctx.texture(overlay))
      release(base);release(overlay)
      self.builds=self.builds+1
    end
    release(raw);release(ground);release(concrete)
    self.prepared=self.prepared+1
  end
  local function current(scene)
    -- Inactive/Original never touches source files, donors or themed images.
    if not enabled()then clear(scene);return nil end
    if ctx.game and ctx.game()~=scene.game then clear(scene);return nil end
    local game=ctx.version();local host=ctx.catalog.hosts[game]
    if not host then clear(scene);return nil end
    local revision=ctx.revision()
    local memo=scenes[scene]
    if memo and(memo.revision~=revision or memo.data~=scene.data or memo.game~=game)then clear(scene);memo=nil end
    if not memo then
      memo={revision=revision,data=scene.data,game=game,frames={}}
      scenes[scene]=memo
      local success,err=pcall(build,scene,game,host,memo)
      if not success then
        for _,frame in ipairs(memo.frames)do release(frame[1]);release(frame[2])end
        memo.frames={};memo.failed=true
        warn(game..':'..tostring(revision),'Magnet Train artwork unavailable; using native ride: '..tostring(err))
      end
    end
    if memo.failed then return nil end
    local phase=math.max(1,math.min(4,math.floor(ctx.phase()or 1)))
    return memo.frames[phase]
  end
  wrapped.backgrounds=function(scene,...)
    local frame=current(scene)
    if not frame then return native.backgrounds(scene,...)end
    self.draws=self.draws+1;return frame[1],frame[2]
  end
  wrapped.backdrop=function(scene,...)
    if current(scene)then return ctx.catalog.metal[1]end
    return native.backdrop(scene,...)
  end
  for name,fn in pairs(wrapped)do Class[name]=fn end
  function self:dispose()
    if closed then return end
    closed=true
    for scene in pairs(scenes)do clear(scene)end
    -- A later mod may retain this wrapper: leave its chain intact and inert.
    for name,fn in pairs(wrapped)do if Class[name]==fn then Class[name]=native[name]end end
  end
  return self
end
return Theme
