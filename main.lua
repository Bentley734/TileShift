return function(mod)
  local callback,dispose,disposed,stopOptions,ownerBus,ownerEpoch,owned,adapterContext,state,roofs
  local function readModule(path)
    return assert(load(assert(mod:read(path)), '@tileshift/'..path))()
  end
  local GV=require('src.core.GameVersion')
  local Runtime=require('src.mods.Runtime')
  if Runtime._tileShiftDispose then Runtime._tileShiftDispose() end
  local Mapping=readModule('lib/mapping.lua')
  local reviewed=readModule('mappings/reviewed.lua')
  for _,path in ipairs({
    'mappings/trees.lua','mappings/posts.lua','mappings/cut_trees.lua','mappings/water.lua','mappings/coasts.lua',
    'mappings/pallet_buildings.lua','mappings/pallet_details.lua',
    'mappings/gen1_outdoor.lua','mappings/gen2_outdoor.lua','mappings/gen1_caves.lua',
    'mappings/gen2_buildings.lua','mappings/gen1_extended.lua','mappings/gen2_outdoor_extended.lua','mappings/azalea.lua','mappings/viridian.lua','mappings/gen2_pallet.lua','mappings/mahogany.lua','mappings/johto_terrain.lua','mappings/cianwood.lua','mappings/olivine.lua','mappings/ecruteak.lua','mappings/north_johto.lua','mappings/silver_cave_outside.lua','mappings/johto_terrain_repeats.lua','mappings/johto_route_details.lua','mappings/goldenrod_arcade.lua',
    'mappings/buildings_extended.lua','mappings/building_overhangs.lua','mappings/goldenrod.lua','mappings/pallet_overhangs.lua','mappings/johto_remaining.lua','mappings/park.lua','mappings/interiors.lua','mappings/gen2_caves.lua','mappings/johto_cave_finish.lua','mappings/johto_rooms_finish.lua','mappings/johto_gate_finish.lua','mappings/johto_shared_finish.lua','mappings/johto_lighthouse_finish.lua','mappings/johto_tower_finish.lua','mappings/johto_gamecorner_finish.lua','mappings/gen1_center_finish.lua','mappings/gen1_commercial_finish.lua','mappings/gen1_domestic_finish.lua','mappings/gen1_facilities_finish.lua','mappings/gen1_galleries_finish.lua','mappings/gen1_gates_finish.lua','mappings/gen1_lab_finish.lua','mappings/gen1_overworld_finish.lua','mappings/gen1_plateau_finish.lua','mappings/gen1_safari_finish.lua','mappings/gen1_ship_finish.lua','mappings/gen1_special_finish.lua','mappings/gen1_temples_finish.lua','mappings/johto_unique_objects_finish.lua','mappings/johto_shrine_finish.lua','mappings/johto_port_finish.lua','mappings/johto_pokecom_finish.lua','mappings/johto_facility_finish.lua','mappings/johto_battle_outside_finish.lua','mappings/johto_station_finish.lua','mappings/johto_ruins_finish.lua','mappings/johto_radio_finish.lua','mappings/johto_gyms_finish.lua','mappings/johto_labrooms_finish.lua','mappings/johto_domestic_finish.lua','mappings/johto_mart_finish.lua','mappings/johto_dragonden_finish.lua','mappings/johto_battle_inside_finish.lua','mappings/johto_underground_finish.lua','mappings/reverse_kanto.lua','mappings/reverse_hoenn.lua','mappings/reverse_oldale.lua',
  }) do
    local source=mod:read(path)
    if source then
      for _,row in ipairs(assert(load(source,'@tileshift/'..path))()) do reviewed[#reviewed+1]=row end
    end
  end
  local indexed,errors=Mapping.index(reviewed)
  assert(#errors==0,table.concat(errors,'\n'))
  local Donor=readModule('lib/donor.lua')
  -- Import checks run on a throttled update poll, never on warm render lookups.
  local identityToken=0
  local decoder=Donor.new({identityToken=function()return identityToken end,gbAnimation=readModule('lib/gb_animation.lua')})
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
  local function checkedSheet(path,expected)
    local bytes=assert(mod:read(path),'Missing TileShift artwork '..path)
    local actual=love.data.encode('string','hex',love.data.hash('sha256',bytes))
    assert(actual==expected,'TileShift artwork fingerprint changed: '..path)
    return love.image.newImageData(mod.assets:path(path))
  end
  local waterStyles=readModule('lib/water_styles.lua').new({image=checkedSheet,newImageData=newData,donor=decoder})
  local function nativeSprite(ref)
    local piece=assert(decoder:cell(ref));local out=newData(16,16)
    for _,name in ipairs({'under','mid','over'})do if piece[name] then
      for y=0,15 do for x=0,15 do
        local r,g,b,a=piece[name]:getPixel(x,y)
        if a>0 then out:setPixel(x,y,r,g,b,a) end
      end end
    end end
    return out
  end
  local flora=readModule('lib/flora.lua').new({catalog=readModule('lib/flora_catalog.lua'),
    seed=love.timer and math.floor(love.timer.getTime()*1000000) or 1,
    newImageData=newData,
    sheet=checkedSheet,
    nativeSprite=nativeSprite,foreground=foreground,
    water=function(entry,piece,sequence,row)return waterStyles:finish(entry,piece,sequence,row)end,
    base=nativeSprite})
  local vegetation=readModule('lib/vegetation.lua').new({
    active=function()return state and state.style~='original' and owned and owned()end,
    time=function()return love.timer and love.timer.getTime() or 0 end,
    draw=function(...)
      if adapterContext and adapterContext.drawVegetation then adapterContext.drawVegetation(...)end
      if roofs then
        if mod.generation==1 then
          local map,entity,cx,cy,s,moved,now,world=...
          roofs:actor(map,entity,-(cx or 0)*(s or 1),-(cy or 0)*(s or 1),s,moved,now,world)
        else roofs:actor(...)end
      end
    end})
  local animationRates={trees=1,flowers=1,grass=1,water=1}
  local centerStyle=tonumber(mod.options:get('center_style'))or tonumber(mod.save:get('center_style'))or 2
  if centerStyle~=1 then centerStyle=2 end
  state=readModule('lib/session.lua').new({mappings=indexed,donor=decoder,
    newImageData=newData,generations=Mapping.generations,themes=Mapping.themes,
    normalizeStyle=Mapping.normalizeStyle,validate=Mapping.validate,
    original=original,foreground=foreground,compose=compose,composeFrames=composeFrames,
    customizeRows=function(rows,game,def)
      if mod.generation==3 then return rows end
      if centerStyle==1 then
        local selected={}
        for i,row in ipairs(rows)do
          if row.buildingCompact then
            local copy={};for k,v in pairs(row)do copy[k]=v end
            copy.parts=nil;copy.donor=nil;copy.asset=nil;copy.assetFileHash=nil
            copy.artOverlay=nil;copy.compositionPixelHash=nil;copy.base=nil
            for k,v in pairs(row.buildingCompact)do copy[k]=v end
            selected[i]=copy
          else selected[i]=row end
        end
        rows=selected
      end
      return flora:rows(rows,game,def)
    end,
    floraPiece=function(row)return flora:piece(row)end,
    finishPiece=function(row,piece,sequence)return flora:finish(row,piece,sequence)end,
    animationTiming=function(row,sequence)return flora:timing(row,sequence)end,
    decorateVegetation=function(row,piece,sequence)return flora:decorate(row,piece,sequence)end,
    vegetationCategory=function(row)return flora:category(row)end,
    invalidateCustomization=function()flora:invalidate()end,
    warn=function(s)mod.log:warn('%s',s)end})
  local styleNames={'ORIGINAL','GEN 3'}
  local styleIds={'original','gen3'}
  if mod.generation==3 then
    styleNames[3],styleNames[4]='GEN 1','GEN 2'
    styleIds[3],styleIds[4]='gen1','gen2'
  end
  local styleChoices={}
  for i,label in ipairs(styleNames)do styleChoices[i]={label,i} end
  -- Read stored preferences before registering the schema's fresh-install default.
  local selection=tonumber(mod.options:get('style')) or tonumber(mod.save:get('style')) or 2
  local floraOptions={}
  local schema={{key='style',label='TILESET',type='choice',choices=styleChoices,default=2}}
  floraOptions[#floraOptions+1]={category='center_style',key='center_style',building=true,
    choices={{'COMPACT','compact',1},{'EXPANDED','expanded',2}},selection=centerStyle}
  schema[#schema+1]={key='center_style',label='POKEMON CENTERS',type='choice',choices={{'COMPACT',1},{'EXPANDED',2}},default=2}
  local floraLabels={trees='TREES',big_trees='BIG TREES',cut_trees='CUT TREES',flowers='FLOWERS',grass='TALL GRASS',water='WATER',center_style='POKEMON CENTERS'}
  for _,category in ipairs({'trees','big_trees','cut_trees','flowers','grass','water'})do
    local choices=flora:choices(category)
    local option={category=category,key='flora_'..category,choices=choices,selection=1}
    local stored=tonumber(mod.options:get(option.key)) or tonumber(mod.save:get(option.key)) or 1
    if stored==stored and stored~=math.huge and stored~=-math.huge then
      if category=='water' then
        for i,choice in ipairs(choices)do if choice[3]==stored then option.selection=i;break end end
      else option.selection=math.max(1,math.min(#choices,math.floor(stored))) end
    end
    flora:select(category,choices[option.selection][2])
    local numeric={} for i,choice in ipairs(choices)do numeric[i]={choice[1],choice[3]} end
    schema[#schema+1]={key=option.key,label=floraLabels[category],
      type='choice',choices=numeric,default=1}
    floraOptions[#floraOptions+1]=option
  end
  local speedChoices={{'OFF',0,1},{'SLOW',.5,2},{'NORMAL',1,3},{'FAST',2,4}}
  for _,group in ipairs({'trees','flowers','grass','water'})do
    local key='speed_'..group
    local selected=tonumber(mod.options:get(key)) or tonumber(mod.save:get(key)) or 3
    if selected~=selected or selected==math.huge or selected==-math.huge then selected=3 end
    selected=math.max(1,math.min(4,math.floor(selected)))
    flora:speed(group,speedChoices[selected][2]);animationRates[group]=speedChoices[selected][2]
    local label=(group=='grass' and 'GRASS' or floraLabels[group])..' SPEED'
    local option={category=key,speed=group,key=key,choices=speedChoices,selection=selected}
    floraLabels[key]=label;floraOptions[#floraOptions+1]=option
    schema[#schema+1]={key=key,label=label,type='choice',
      choices={{'OFF',1},{'SLOW',2},{'NORMAL',3},{'FAST',4}},default=3}
  end
  local motionChoices={{'ALWAYS','always',1},{'ON WALK','walked',2}}
  local motion=tonumber(mod.options:get('grass_motion')) or tonumber(mod.save:get('grass_motion')) or 1
  motion=motion==2 and 2 or 1;vegetation:setMode(motionChoices[motion][2])
  floraLabels.grass_motion='GRASS MOTION'
  floraOptions[#floraOptions+1]={category='grass_motion',key='grass_motion',motion=true,choices=motionChoices,selection=motion}
  schema[#schema+1]={key='grass_motion',label='GRASS MOTION',type='choice',choices={{'ALWAYS',1},{'ON WALK',2}},default=1}
  if mod.generation==3 then
    local options,fields={},{}
    for _,option in ipairs(floraOptions)do if option.speed=='water'or option.speed=='flowers'then options[#options+1]=option end end
    for _,field in ipairs(schema)do if field.key=='style'or field.key=='speed_water'or field.key=='speed_flowers'then fields[#fields+1]=field end end
    floraOptions,schema=options,fields
  end
  mod.options:define(schema)
  selection=math.max(1,math.min(#styleIds,math.floor(selection)))
  state:select(styleIds[selection])
  owned=function()
    if disposed then return false end
    if ownerBus and ownerBus.ownerEpoch then
      return Runtime.hooks==ownerBus and ownerBus:ownerEpoch(mod.id)==ownerEpoch
    end
    -- Compatibility fallback for engines without ownership epochs.
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
  local function afterUpdate(game,...)
    if state.style~='original' and mod.generation<3 then vegetation:bind(mod.generation==1 and (game.overworld or game.world) or game.world)end
    return ...
  end
  local pollElapsed=0
  callback=function(nextFn,game,dt)
    pollElapsed=pollElapsed+(dt or 0)
    if pollElapsed>=1 then
      pollElapsed=pollElapsed%1
      if state.style~='original' and (mod.generation<3 or state.style~='gen3') and state.checkSource then
        identityToken=identityToken+1;state:checkSource(GV.get())
      end
    end
    if lastRevision~=state.revision then refresh(game);lastRevision=state.revision end
    return afterUpdate(game,nextFn(game,dt))
  end
  mod.hooks:wrap('core.update',callback,125)
  ownerBus=Runtime.hooks
  if ownerBus and ownerBus.ownerEpoch then ownerEpoch=ownerBus:ownerEpoch(mod.id)end
  local decorationRows=readModule('lib/roof_catalog.lua')
  for _,row in ipairs(readModule('lib/side_catalog.lua'))do decorationRows[#decorationRows+1]=row end
  for _,row in ipairs(readModule('lib/center_mart_roofs.lua'))do decorationRows[#decorationRows+1]=row end
  for _,row in ipairs(readModule('lib/goldenrod_roofs.lua'))do decorationRows[#decorationRows+1]=row end
  for _,row in ipairs(readModule('lib/pallet_roofs.lua'))do decorationRows[#decorationRows+1]=row end
  for _,row in ipairs(readModule('lib/johto_roofs.lua'))do decorationRows[#decorationRows+1]=row end
  roofs=readModule('lib/roofs.lua').new({rows=decorationRows,validate=Mapping.validate,
    donor=decoder,original=original,compose=compose,version=GV.get,revision=function()return state.revision end,
    markTrueColor=function(x,y,w,h)
      if mod.generation==1 then
        local fx=require('src.render.PaletteFX')
        if fx.markTrueColor then fx.markTrueColor(x,y,w,h)end
      end
    end,
    active=function()return state.style=='gen3'and mod.generation<3 and owned()end,
    enabled=function(row)return row.role~='larger_center'or centerStyle~=1 end,
    warn=function(s)mod.log:warn('%s',s)end})
  local adapter=readModule('lib/gen'..mod.generation..'.lua')
  adapterContext={time=function()return love.timer and love.timer.getTime()or 0 end,
    animationSpeed=function(group)return animationRates[group]or 1 end,roofs=roofs,version=GV.get,revision=function()return state.revision end,active=owned,
    grassTime=function(map,x,y,now)return vegetation:time(map,x,y,now)end,
    disturb=function(map,x,y,now,duration)return vegetation:touch(map,x,y,now,duration)end,
    replacements=function(game,tileset,def)
      if not owned() then return nil end
      return state:replacements(game,tileset,def)
    end,warn=function(s)mod.log:warn('%s',s)end}
  local close=adapter.install(adapterContext)
  dispose=function()
    if disposed then return end
    disposed=true;vegetation:dispose();close();roofs:dispose();decoder:invalidate()
    if stopOptions then stopOptions();stopOptions=nil end
    if Runtime._tileShiftDispose==dispose then Runtime._tileShiftDispose=nil end
  end
  Runtime._tileShiftDispose=dispose
  local function applyFlora(option,value,asIndex)
    value=tonumber(value)
    if not value or value~=value or value==math.huge or value==-math.huge then return false end
    if asIndex or option.category~='water' then
      option.selection=math.max(1,math.min(#option.choices,math.floor(value)))
    else
      option.selection=1
      for i,choice in ipairs(option.choices)do if choice[3]==value then option.selection=i;break end end
    end
    local changed
    if option.building then changed=centerStyle~=option.selection;centerStyle=option.selection
    elseif option.motion then changed=vegetation:setMode(option.choices[option.selection][2])
    elseif option.speed then
      animationRates[option.speed]=option.choices[option.selection][2]
      changed=flora:speed(option.speed,animationRates[option.speed])
    else changed=flora:select(option.category,option.choices[option.selection][2]) end
    if changed then
      if state.invalidateVisual then state:invalidateVisual() else state:invalidate() end
    end
    mod.save:set(option.key,option.choices[option.selection][3])
    refresh(mod.game);lastRevision=state.revision
    return true
  end
  stopOptions=mod.events:on('mod.options_changed',function(payload)
    if type(payload)~='table' or payload.mod~=mod.id or not owned() then return end
    for _,option in ipairs(floraOptions)do if payload.key==option.key then applyFlora(option,payload.value);return end end
    if payload.key~='style' then return end
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
    for _,item in ipairs(floraOptions)do
      local option=item
      out[#out+1]={id='tileshift:'..option.key,label=floraLabels[option.category],
        value=function()return option.choices[option.selection][1]end,
        step=function(ctx,dir)
          local value=1+(option.selection-1+(dir and dir<0 and -1 or 1))%#option.choices
          applyFlora(option,value,true)
          local game=(ctx and ctx.game) or ctx or mod.game
          if game then
            local options=game.options or (game.save and game.save.options) or {}
            options.modOptions=options.modOptions or {};options.modOptions[mod.id]=options.modOptions[mod.id] or {}
            options.modOptions[mod.id][option.key]=option.choices[option.selection][3]
            if game.mods then game.mods.modOptions[mod.id]=options.modOptions[mod.id] end
            if game.save and game.save.options then game.save.options.modOptions=options.modOptions end
            if game.writeOptions then game:writeOptions() end
            refresh(game)
          end
          return false
        end}
    end
    out[#out+1]={id='tileshift:coverage',label='COVERAGE',value=function()return 'IN PROGRESS' end,
      step=function()return false end}
    return out
  end
  mod.hooks:wrap('ui.options.rows',addOptions,125)
  mod.exports.state=state
  mod.exports.flora=flora
  mod.exports.roofs=roofs
  mod.exports.vegetation=vegetation
  mod.exports.drawVegetation=function(...)if adapterContext.drawVegetation then return adapterContext.drawVegetation(...)end end
  mod.exports.dispose=dispose
  mod.exports.select=function(style)
    style=Mapping.normalizeStyle(style)
    for i,id in ipairs(styleIds) do if style==id then selection=i;state:select(style);refresh(mod.game);return true end end
    return nil,'Unknown tileset style'
  end
end
