-- Crystal-style berry pixels over the native RSE berry actors. Native object
-- state, growth commands, watering, sorting and interaction logic stay owned
-- by the engine. Files and sheets are checked/cached outside warm draw work.
local BerryTheme = {}
local HOSTS = {ruby=true, sapphire=true, emerald=true}
local SOURCE_ROOT = 'data/generated/gba/berry_trees/'
local HOST_ORDER = {'ruby','sapphire','emerald'}

local function integer(value, maximum)
  return type(value)=='number' and value>=0 and value%1==0 and value<=maximum
end

local function sameMetadata(a, b)
  if type(a)~=type(b) then return false end
  if type(a)~='table' then return a==b end
  for key,value in pairs(a) do if not sameMetadata(value,b[key]) then return false end end
  for key in pairs(b) do if a[key]==nil then return false end end
  return true
end

local function matchesEntry(tree, native, berry)
  return type(tree)=='table' and tree.berry==berry and tree.file==native.file
    and tree.idx==native.idx and tree.width==native.width and tree.height==native.height
    and sameMetadata(tree.frames,native.frames) and sameMetadata(tree.stages,native.stages)
end

function BerryTheme.install(ctx)
  assert(type(ctx)=='table' and type(ctx.catalog)=='table', 'Berry catalog required')
  assert(ctx.catalog.format==1 and type(ctx.catalog.varieties)=='table'
    and type(ctx.catalog.sources)=='table', 'Unsupported berry catalog')
  assert(type(ctx.style)=='function' and type(ctx.version)=='function'
    and type(ctx.source)=='function' and type(ctx.sheet)=='function', 'Berry services required')
  local effects = ctx.effects or (ctx.require or require)('src.core.game3.field_effects_rse')
  assert(type(effects.collectActors)=='function', 'Native RSE actor collection unavailable')
  local hash = ctx.hash or function(bytes)
    return love.data.encode('string', 'hex', love.data.hash('sha256', bytes))
  end
  local newImage = ctx.newImage or love.graphics.newImage
  local newQuad = ctx.newQuad or love.graphics.newQuad
  local original = effects.collectActors
  local images, quads, sources, warnings = {}, {}, {}, {}
  local touched = setmetatable({}, {__mode='k'})
  local stopped = false
  local self = {swaps=0, rejected=0, loaded=0}

  local function warn(game, message)
    local key = game..':'..message
    if warnings[key] then return end
    warnings[key] = true
    self.rejected = self.rejected+1
    if ctx.warn then ctx.warn('Crystal berry art: '..game..': '..message) end
  end

  local function enabled()
    local game = ctx.version()
    return not stopped and HOSTS[game] and ctx.style()=='gen2'
      and (not ctx.berryStyle or ctx.berryStyle()=='crystal')
      and (not ctx.active or ctx.active()), game
  end

  local function checkedSource(game)
    local expected = ctx.catalog.sources[game]
    if not (expected and expected.trees) then return nil, 'Unreviewed native berry game' end
    local bytes = ctx.source(game, SOURCE_ROOT..'manifest.lua')
    if not (bytes and hash(bytes)==expected.manifestHash) then return nil, 'Native berry manifest changed' end
    local manifest = effects.berryManifest and effects.berryManifest()
    if not (manifest and type(manifest.trees)=='table') then return nil, 'Native berry manifest unavailable' end
    local state = {entries=setmetatable({}, {__mode='k'}), valid=true, aliases=0}
    for berry=1,43 do
      local native, tree = expected.trees[berry], manifest.trees[berry]
      if not (native and type(tree)=='table') then return nil, 'Unreviewed native berry variety' end
      local rgba = ctx.source(game, SOURCE_ROOT..native.file)
      local idx = native.idx and ctx.source(game, SOURCE_ROOT..native.idx)
      local matching = type(rgba)=='string' and #rgba==native.width*native.height*4
        and hash(rgba)==native.rgbaHash
        and (not native.idxHash or (type(idx)=='string' and hash(idx)==native.idxHash))
      if not matching then return nil, 'Native berry pixel/index fingerprint changed' end
      local binding = matchesEntry(tree,native,berry) and game or nil
      if not binding then
        -- R/S/E importer names differ while these reviewed native pixels,
        -- frame records and programs are identical. Accept only a frozen
        -- same-variety alias after checking the CURRENT import above. This
        -- never changes or clears the engine's memoized manifest/images.
        for _,host in ipairs(HOST_ORDER) do
          local profile=ctx.catalog.sources[host]
          local alias=profile and profile.trees and profile.trees[berry]
          if alias and alias.rgbaHash==native.rgbaHash and alias.idxHash==native.idxHash
            and sameMetadata(alias.frames,native.frames) and sameMetadata(alias.stages,native.stages)
            and matchesEntry(tree,alias,berry) then binding=host;break end
        end
      end
      if not binding then return nil, 'Native berry entry has no verified current-profile binding' end
      if binding~=game then state.aliases=state.aliases+1 end
      state.entries[tree] = {native=native,berry=berry,bindingProfile=binding}
    end
    return state
  end

  local function asset(berry, native)
    local spec = ctx.catalog.varieties[berry]
    if not spec then return nil, 'Missing Crystal berry variety' end
    local image = images[berry]
    if not image then
      local ok, data = pcall(ctx.sheet, spec.asset, spec.hash)
      if not ok or not data or type(data.getDimensions)~='function' then
        return nil, 'Crystal berry artwork fingerprint/load failed'
      end
      local width, height = data:getDimensions()
      if width~=native.width or height~=native.height or width~=16 or height~=240 then
        return nil, 'Crystal berry artwork must match the complete native16x240 sheet'
      end
      image = newImage(data)
      if image.setFilter then image:setFilter('nearest', 'nearest') end
      images[berry] = image
      self.loaded = self.loaded+1
    end
    return image
  end

  local function swap(actor, game)
    local object = actor.fxObject
    local bt = object and object.berryTree
    if not (bt and bt.visible and bt.tree and actor.fxQuad==bt.quad) then return end
    local frame = bt.anim and (bt.anim.frame or 0) or 0
    if not integer(frame, 8) then return end
    local state = sources[game]
    local entry = state and state.valid and state.entries[bt.tree]
    if not entry or entry.berry~=bt.tree.berry then return end
    local native, berry = entry.native, entry.berry
    local image = images[berry]
    if not (native and image) then return end
    local rectangle = native.frames[frame+1]
    if not rectangle then warn(game, 'Unreviewed native berry animation frame');return end
    local quad = quads[berry] and quads[berry][frame+1]
    if not quad then return end
    local record = touched[actor]
    if not record then record={};touched[actor]=record end
    record.originalImage, record.originalQuad = actor.fxImage, actor.fxQuad
    record.image, record.quad, record.game = image, quad, game
    actor.fxImage, actor.fxQuad = image, quad
    self.swaps = self.swaps+1
  end

  local wrapper
  wrapper = function(actors, camX, camY, ...)
    local start = #actors
    local a, b, c = original(actors, camX, camY, ...)
    local active, game = enabled()
    if active then
      for i=start+1,#actors do swap(actors[i], game) end
    end
    return a, b, c
  end
  effects.collectActors = wrapper

  local function restore()
    for actor, record in pairs(touched) do
      if actor.fxImage==record.image and actor.fxQuad==record.quad then
        actor.fxImage, actor.fxQuad = record.originalImage, record.originalQuad
      end
    end
  end

  function self:checkSource(game)
    local active, current = enabled()
    game = game or current
    if not active or game~=current then restore();return false end
    local state, why = checkedSource(game)
    if not state then
      sources[game] = {valid=false}
      restore();warn(game, why);return false
    end
    -- All file/image work and every quad allocation happens here, outside
    -- collectActors. Warm actor collection performs cache lookups only.
    for berry=1,43 do
      local native = ctx.catalog.sources[game].trees[berry]
      local image;image, why = asset(berry, native)
      if not image then
        sources[game] = {valid=false}
        restore();warn(game, why);return false
      end
      if not quads[berry] then
        local list = {}
        for i, frame in ipairs(native.frames) do
          list[i] = newQuad(0, frame.y, frame.w, frame.h, native.width, native.height)
        end
        quads[berry] = list
      end
    end
    sources[game] = state
    return true
  end

  function self:prepare(game)
    return self:checkSource(game)
  end

  function self:dispose()
    if stopped then return end
    stopped = true
    if effects.collectActors==wrapper then effects.collectActors=original end
    restore()
    for _, list in pairs(quads) do
      for _, quad in pairs(list) do if quad.release then quad:release() end end
    end
    for _, image in pairs(images) do if image and image.release then image:release() end end
    images, quads, sources, warnings = {}, {}, {}, {}
    touched = setmetatable({}, {__mode='k'})
  end

  return self
end

return BerryTheme
