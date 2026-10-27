return function(mod)
  local function readModule(path)
    return assert(load(assert(mod:read(path)), '@tileshift/'..path))()
  end
  local GV=require('src.core.GameVersion')
  local Runtime=require('src.mods.Runtime')
  if Runtime._tileShiftDispose then Runtime._tileShiftDispose() end
  local Mapping=readModule('lib/mapping.lua')
  local reviewed=readModule('mappings/reviewed.lua')
  for _,path in ipairs({
    'mappings/trees.lua','mappings/posts.lua','mappings/water.lua','mappings/coasts.lua',
    'mappings/pallet_buildings.lua','mappings/pallet_details.lua',
    'mappings/gen1_outdoor.lua','mappings/gen2_outdoor.lua','mappings/gen1_caves.lua',
    'mappings/gen2_buildings.lua','mappings/gen1_extended.lua','mappings/gen2_outdoor_extended.lua',
    'mappings/buildings_extended.lua','mappings/interiors.lua','mappings/gen2_caves.lua',
  }) do
    local source=mod:read(path)
    if source then
      for _,row in ipairs(assert(load(source,'@tileshift/'..path))()) do reviewed[#reviewed+1]=row end
    end
  end
  local indexed,errors=Mapping.index(reviewed)
  assert(#errors==0,table.concat(errors,'\n'))
  local Donor=readModule('lib/donor.lua')
  -- Render paths may resolve the same rows once per visible block. Sample
  -- import identities once per update instead of reopening marker files there.
  local identityToken=0
  local decoder=Donor.new({identityToken=function()return identityToken end})
  local nativeFS=require('src.import.CacheFs')
  local function newData(w,h) return love.image.newImageData(w,h) end
  local composer
  local function getComposer()
    if not composer then composer=readModule('lib/composition.lua').new({donor=decoder,newImageData=newData}) end
    return composer
  end
  local function compose(row)return getComposer():cell(row)end
  local function composeFrames(row)return getComposer():frames(row)end
  local originals,effects={},{}
  local function original(path,expectedHash)
    local key=path..':'..tostring(expectedHash or '')
    if not originals[key] then
      if expectedHash then
        local bytes=assert(mod:read(path),'Missing TileShift asset '..path)
        local actual=love.data.encode('string','hex',love.data.hash('sha256',bytes))
        assert(actual==expectedHash,'TileShift asset fingerprint changed: '..path)
      end
      originals[key]=love.image.newImageData(mod.assets:path(path))
    end
    local data=originals[key]
    local w,h=data:getDimensions()
    assert(w==16 and h==16,'Original TileShift assets must be 16x16 pixels')
    return data
  end
  local function foreground(ref)
    assert(type(ref)=='table' and Mapping.generations[ref.game]==3,'Unsupported foreground source')
    assert(ref.effect=='tall_grass','Unreviewed foreground effect')
    local key=ref.game..':'..ref.effect..':'..tostring(ref.hash or '')
    if effects[key] then return effects[key] end
    local path='data/generated/gba/field_effects/tall_grass.rgba'
    local bytes=nativeFS.readAt(GV.cachePrefix(ref.game)..path)
    if not bytes or #bytes~=16*80*4 then return nil,'Native Emerald grass effect is unavailable' end
    if ref.hash then
      local actual=love.data.encode('string','hex',love.data.hash('sha256',bytes))
      if actual~=ref.hash then return nil,'Native grass effect fingerprint changed' end
    end
    local sheet=love.image.newImageData(16,80,'rgba8',bytes)
    local image=newData(16,16)
    image:paste(sheet,0,8,0,4*16+8,16,8)
    effects[key]=image
    return image
  end
  local state=readModule('lib/session.lua').new({mappings=indexed,donor=decoder,
    newImageData=newData,generations=Mapping.generations,themes=Mapping.themes,
    normalizeStyle=Mapping.normalizeStyle,validate=Mapping.validate,
    original=original,foreground=foreground,compose=compose,composeFrames=composeFrames,
    warn=function(s)mod.log:warn('%s',s)end})
  local styleNames={'ORIGINAL','GEN 3'}
  local styleIds={'original','gen3'}
  local styleChoices={}
  for i,label in ipairs(styleNames)do styleChoices[i]={label,i} end
  -- Read stored preferences before registering the schema's fresh-install default.
  local selection=tonumber(mod.options:get('style')) or tonumber(mod.save:get('style')) or 2
  mod.options:define({{key='style',label='TILESET',type='choice',choices=styleChoices,default=2}})
  selection=math.max(1,math.min(#styleIds,math.floor(selection)))
  state:select(styleIds[selection])
  local callback,dispose,disposed,stopOptions
  local function owned()
    if disposed then return false end
    local hooks=Runtime.hooks and Runtime.hooks.chains
    for _,entry in ipairs(hooks and hooks['core.update'] or {}) do
      if entry.owner==mod.id and entry.callback==callback then return true end
    end
    return false
  end
  local lastRevision=state.revision
  local function refresh(game)
    local world=game and game.world
    if mod.generation==2 and world and world.map and world.imageFor then
      world.mapImage=world:imageFor(world.map.id)
      for _,neighbor in ipairs(world.neighbors or {}) do neighbor.image=world:imageFor(neighbor.id) end
    end
  end
  callback=function(nextFn,game,dt)
    identityToken=identityToken+1
    if lastRevision~=state.revision then refresh(game);lastRevision=state.revision end
    return nextFn(game,dt)
  end
  mod.hooks:wrap('core.update',callback,125)
  local adapter=readModule('lib/gen'..mod.generation..'.lua')
  local close=adapter.install({version=GV.get,revision=function()return state.revision end,active=owned,
    replacements=function(game,tileset,def)
      if not owned() then return nil end
      return state:replacements(game,tileset,def)
    end,warn=function(s)mod.log:warn('%s',s)end})
  dispose=function()
    if disposed then return end
    disposed=true;close();decoder:invalidate()
    if stopOptions then stopOptions();stopOptions=nil end
    if Runtime._tileShiftDispose==dispose then Runtime._tileShiftDispose=nil end
  end
  Runtime._tileShiftDispose=dispose
  stopOptions=mod.events:on('mod.options_changed',function(payload)
    if type(payload)~='table' or payload.mod~=mod.id or payload.key~='style' or not owned() then return end
    local value=tonumber(payload.value)
    if not value or value~=value or value==math.huge or value==-math.huge then return end
    selection=math.max(1,math.min(#styleIds,math.floor(value)))
    state:select(styleIds[selection]);mod.save:set('style',selection)
    refresh(mod.game);lastRevision=state.revision
  end)
  local function persist(ctx,dir)
    local game=(ctx and ctx.game) or ctx or mod.game
    selection=1+(selection-1+(dir and dir<0 and -1 or 1))%#styleIds
    state:select(styleIds[selection]);mod.save:set('style',selection)
    if game then
      local options=game.options or (game.save and game.save.options) or {}
      options.modOptions=options.modOptions or {}
      options.modOptions[mod.id]=options.modOptions[mod.id] or {}
      options.modOptions[mod.id].style=selection
      if game.mods then game.mods.modOptions[mod.id]=options.modOptions[mod.id] end
      if game.save and game.save.options then game.save.options.modOptions=options.modOptions end
      if game.writeOptions then game:writeOptions() end
    end
    refresh(game);return false
  end
  local function addOptions(nextFn,game,out)
    out=nextFn(game,out)
    if type(out)~='table' then return out end
    out[#out+1]={id='tileshift:style',label='TILESET',value=function()return styleNames[selection]end,step=persist}
    out[#out+1]={id='tileshift:coverage',label='COVERAGE',value=function()return 'IN PROGRESS' end,
      step=function()return false end}
    return out
  end
  mod.hooks:wrap('ui.options.rows',addOptions,125)
  mod.exports.state=state
  mod.exports.dispose=dispose
  mod.exports.select=function(style)
    style=Mapping.normalizeStyle(style)
    for i,id in ipairs(styleIds) do if style==id then selection=i;state:select(style);refresh(mod.game);return true end end
    return nil,'Unknown tileset style'
  end
end
