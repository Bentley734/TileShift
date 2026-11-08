local root=assert(arg and arg[1],'TileShift directory required')
-- The real mod sandbox exposes a string-capable load on Lua 5.1 too.
local originalLoad=load
if _VERSION=='Lua 5.1' then load=loadstring end
local entry=assert(loadfile(root..'/main.lua'))()
local count=0
local function eq(a,b,message)
  count=count+1;assert(a==b,(message or 'mismatch')..': '..tostring(a)..' ~= '..tostring(b))
end
local originalLoaded={}
for _,name in ipairs({'src.core.GameVersion','src.mods.Runtime','src.import.CacheFs'})do
  originalLoaded[name]=package.loaded[name]
end
local mapping=assert(loadfile(root..'/lib/mapping.lua'))()
local nativeHashes,nativeReads={},{}
love={image={newImageData=function(w,h,format,bytes)
  if type(w)=='string' then return {getDimensions=function()return 16,16 end} end
  return {w=w,h=h,format=format,bytes=bytes,getDimensions=function()return w,h end,
    paste=function(self,...)self.pasted={...}end}
end},data={hash=function(algorithm,bytes)nativeHashes[#nativeHashes+1]={algorithm,bytes};return 'digest'end,
  encode=function(_,_,bytes)return bytes end}}
local selections={red=1,blue=1,yellow=1,gold=2,silver=2,crystal=2,ruby=3,sapphire=3,emerald=3,firered=3,leafgreen=3}
local games={'red','blue','yellow','gold','silver','crystal','ruby','sapphire','emerald','firered','leafgreen'}
for _,gameId in ipairs(games)do
  local generation=selections[gameId]
  local runtime={hooks={chains={}}}
  if gameId=='red' then runtime.hooks.epoch=0;runtime.hooks.ownerEpoch=function(self)return self.epoch end end
  local gv={get=function()return gameId end,cachePrefix=function(v)return v..'/'end}
  package.loaded['src.core.GameVersion']=gv;package.loaded['src.mods.Runtime']=runtime
  package.loaded['src.import.CacheFs']={readAt=function(path)
    nativeReads[#nativeReads+1]=path;return string.rep('x',16*80*4)
  end}
  local fixture={mapping=mapping,reviewed={},adapters={},reads={},closed=0,invalidations=0}
  local state={style='original',revision=0}
  function state:select(style)
    if style==self.style then return false end
    self.style=style;self.revision=self.revision+1;return true
  end
  function state:invalidate()self.revision=self.revision+1 end
  function state:checkSource()fixture.polls=(fixture.polls or 0)+1 end
  function state:replacements(v,tileset,def)return {version=v,tileset=tileset,def=def,style=self.style}end
  fixture.decoder={invalidate=function()fixture.invalidations=fixture.invalidations+1 end}
  fixture.donor={new=function(ctx)fixture.donorCtx=ctx;return fixture.decoder end}
  fixture.composition={new=function(ctx)
    fixture.composerCreations=(fixture.composerCreations or 0)+1;fixture.composerCtx=ctx
    return {cell=function(_,row)fixture.staticRow=row;return 'static composition'end,
      frames=function(_,row)fixture.animatedRow=row;return 'animated composition'end}
  end}
  fixture.session={new=function(ctx)fixture.sessionCtx=ctx;return state end}
  fixture.berryCatalog={fixture=true}
  fixture.clinicCatalog={}
  fixture.clinicModule={install=function(ctx)
    fixture.clinicCtx=ctx
    return {prepare=function()fixture.clinicPrepares=(fixture.clinicPrepares or 0)+1 end,
      refresh=function()fixture.clinicRefreshes=(fixture.clinicRefreshes or 0)+1 end,
      poll=function()fixture.clinicPolls=(fixture.clinicPolls or 0)+1 end,
      dispose=function()fixture.clinicDisposes=(fixture.clinicDisposes or 0)+1 end}
  end}
  fixture.berryModule={install=function(ctx)
    fixture.berryCtx=ctx
    return {prepare=function(_,version)
      eq(version,gameId);fixture.berryPrepares=(fixture.berryPrepares or 0)+1
    end,checkSource=function(_,version)
      eq(version,gameId);fixture.berryChecks=(fixture.berryChecks or 0)+1
    end,dispose=function()fixture.berryDisposes=(fixture.berryDisposes or 0)+1 end}
  end}
  for gen=1,3 do
    local selectedGen=gen
    fixture.adapters[gen]={install=function(ctx)
      fixture.installed=selectedGen;fixture.adapterCtx=ctx
      return function()fixture.closed=fixture.closed+1 end
    end}
  end
  _G.__tileMainFixture=fixture
  local modules={['lib/mapping.lua']='mapping',['mappings/reviewed.lua']='reviewed',
    ['lib/donor.lua']='donor',['lib/session.lua']='session',['lib/composition.lua']='composition',
    ['lib/berry_catalog.lua']='berryCatalog',['lib/berry_theme.lua']='berryModule',
    ['lib/clinic_chansey_catalog.lua']='clinicCatalog',['lib/clinic_chansey.lua']='clinicModule'}
  local stored,schemas,hooks,listeners={},nil,{},{}
  local function emit(name,payload)
    for _,fn in ipairs(listeners[name] or {})do fn(payload)end
  end
  local game={generation=generation,options={},save={options={}},mods={modOptions={}},writes=0}
  function game:writeOptions()self.writes=self.writes+1 end
  game.world={map={id='CURRENT'},neighbors={{id='NEIGHBOR'}},imageFor=function(_,id)return 'native-'..id end}
  local mod={id='tileshift',generation=generation,exports={},game=game,
    options={define=function(_,rows)schemas=rows end,get=function(_,key)if key=='berry_style'then return nil end;return 1 end},
    save={get=function(_,key)return stored[key]end,set=function(_,key,value)stored[key]=value end},
    assets={path=function(_,path)return 'mods/tileshift/'..path end},
    hooks={wrap=function(_,name,fn,priority)
      hooks[name]=fn;runtime.hooks.chains[name]={{owner='tileshift',callback=fn,priority=priority}}
    end},events={on=function(_,name,fn)
      local list=listeners[name] or {};listeners[name]=list;list[#list+1]=fn
      return function()for i,candidate in ipairs(list)do if candidate==fn then table.remove(list,i);break end end end
    end},log={warn=function()end}}
  function mod:read(path)
    fixture.reads[#fixture.reads+1]=path
    if path=='lib/johto_furniture.lua'then return 'return{}'end
    if path=='lib/gen1_building_audit_roofs.lua'then return 'return{}'end
    if path=='mappings/gen1_outdoor_audit.lua'or path=='mappings/gen1_facility_audit.lua'
      or path=='mappings/gen1_seating_domestic_audit.lua'then return nil end
    if path=='lib/roof_catalog.lua'or path=='lib/side_catalog.lua'or path=='lib/center_mart_roofs.lua'or path=='lib/goldenrod_roofs.lua'or path=='lib/pallet_roofs.lua'or path=='lib/johto_roofs.lua'or path=='lib/gen2_kanto_building_roofs.lua'or path=='lib/gen2_kanto_landmark_decorations.lua'then return 'return{}'end
    if path:match('^mappings/gen2_kanto_.*_finish%.lua$') or path=='mappings/gen2_compact_gyms_hall_finish.lua' then return nil end
    if path=='mappings/reverse_kanto.lua'or path=='mappings/reverse_hoenn.lua'or path=='mappings/reverse_oldale.lua'then return nil end
    if path:match('^mappings/reverse_gen2_.*_finish%.lua$')or path:match('^mappings/reverse_gen2_.*_complete%.lua$')then return nil end
    if path=='mappings/reverse_gen2_kanto_final.lua'or path=='mappings/reverse_gen2_hoenn_outdoor_remaining.lua'
      or path=='mappings/reverse_gen2_hoenn_interiors_completion.lua'
      or path=='mappings/reverse_gen2_lilycove_remaining.lua'
      or path=='mappings/reverse_gen2_frontier_outside.lua'
      or path=='mappings/reverse_gen2_hoenn_cave_completion.lua'
      or path=='mappings/reverse_gen2_kanto_house_completion.lua'
      or path=='mappings/reverse_gen2_hoenn_dome_lights.lua'
      or path=='mappings/reverse_gen2_hoenn_elite_lights.lua'
      or path=='mappings/reverse_gen2_hoenn_facility_outdoors.lua'
      or path=='mappings/reverse_gen2_kanto_network_completion.lua'
      or path=='mappings/reverse_gen2_kanto_mansion_completion.lua'
      or path=='mappings/reverse_gen2_kanto_silph_rocket_completion.lua'
      or path=='mappings/reverse_gen2_kanto_player_houses.lua'
      or path=='mappings/reverse_gen2_kanto_celadon.lua'
      or path=='mappings/reverse_gen2_kanto_league.lua'
      or path=='mappings/reverse_gen2_kanto_power_plant_completion.lua'
      or path=='mappings/reverse_gen2_kanto_tanoby_completion.lua'
      or path=='mappings/reverse_gen2_kanto_ssanne_completion.lua'
      or path=='mappings/reverse_gen2_sevii_outdoor_completion.lua'
      or path=='mappings/reverse_gen2_kanto_gyms_completion.lua'
      or path=='mappings/reverse_gen2_kanto_marts_completion.lua'
      or path=='mappings/reverse_gen2_mt_ember_completion.lua'
      or path=='mappings/reverse_gen2_kanto_trainer_tower.lua'
      or path=='mappings/reverse_gen2_kanto_department.lua'
      or path=='mappings/reverse_gen2_kanto_condominiums.lua'
      or path=='mappings/reverse_gen2_kanto_indigo_outside.lua'
      or path=='mappings/reverse_gen2_kanto_forests.lua'
      or path=='mappings/reverse_gen2_kanto_tunnels_completion.lua'
      or path=='mappings/reverse_gen2_kanto_pokemon_tower_completion.lua'
      or path=='mappings/reverse_gen2_kanto_caves_completion.lua'
      or path=='mappings/reverse_gen2_kanto_regional_caves_completion.lua'
      or path=='mappings/reverse_gen2_cerulean_outdoor_completion.lua'
      or path=='mappings/reverse_gen2_kanto_navel_dotted_completion.lua'
      or path=='mappings/reverse_gen2_four_five_outdoor_completion.lua'
      or path=='mappings/reverse_gen2_kanto_safari_rooms.lua'
      or path=='mappings/reverse_gen2_kanto_labs_museum_completion.lua'
      or path=='mappings/reverse_gen2_kanto_cable_rooms_completion.lua'
      or path=='mappings/reverse_gen2_cinnabar_pallet_completion.lua'
      or path=='mappings/reverse_gen2_kanto_commercial_rooms.lua'
      or path=='mappings/reverse_gen2_kanto_final_rooms.lua'
      or path=='mappings/reverse_gen2_kanto_final_houses.lua'
      or path=='mappings/reverse_gen2_frlg_runtime_alternates.lua'
      or path=='mappings/reverse_gen2_frlg_field_states.lua'
      or path=='mappings/reverse_gen2_kanto_runtime_fixtures.lua'
      or path=='mappings/reverse_gen2_kanto_script_cells.lua'
      or path=='mappings/reverse_gen1_kanto_gyms.lua'
      or path=='mappings/reverse_gen1_kanto_services.lua'
      or path=='mappings/reverse_gen1_kanto_landmarks.lua'
      or path=='mappings/reverse_gen1_native_terrain.lua'
      or path=='mappings/reverse_gen1_native_service_rooms.lua'
      or path=='mappings/reverse_gen1_native_service_backings.lua'
      or path=='mappings/reverse_gen2_rse_field_states.lua'
      or path=='mappings/reverse_gen2_rse_scripted_interiors.lua'
      or path=='mappings/reverse_gen2_rse_industrial_states.lua'
      or path=='mappings/reverse_gen2_hoenn_alternate_layouts.lua'
      or path=='mappings/reverse_gen2_rse_doors_elevators.lua'
      or path=='mappings/reverse_gen2_hoenn_script_aliases.lua'
      or path=='mappings/reverse_gen2_rse_outdoor_states.lua'
      or path=='mappings/reverse_gen2_emerald_weather_closure.lua' then return nil end
    if path=='mappings/reverse_classic_gyms_finish.lua'or path=='mappings/reverse_classic_berry_soil.lua'then return nil end
    if path=='lib/gb_animation.lua'then return 'return {}'end
    if path=='lib/roofs.lua' or path=='lib/vegetation.lua' or path=='lib/flora.lua' or path=='lib/flora_catalog.lua' or path=='lib/johto_hack_flora.lua' or path=='lib/water_styles.lua' or path=='lib/monochrome.lua' then
      local file=assert(io.open(root..'/'..path,'rb'));local source=file:read('*a');file:close();return source
    end
    if path=='mappings/trees.lua' then
      return fixture.trees and 'return __tileMainFixture.trees' or nil
    end
    if path=='mappings/newbark_crystaldust_domestic.lua' or path=='mappings/gen2_newbark_crystaldust_lab.lua' or path=='mappings/newbark_crystaldust_divider.lua' or path=='mappings/johto_bedroom_decorations.lua' then return nil end
    if path=='mappings/crystaldust_slowpoke_sweep.lua' or path=='mappings/crystaldust_field_states.lua'
      or path=='mappings/crystaldust_special_runtime.lua' or path=='mappings/crystaldust_route19_rockfall.lua'
      or path=='mappings/gen2_crystaldust_bookcases.lua' or path=='mappings/gen2_crystaldust_interior_callback_states.lua' then return nil end
    if path=='mappings/gen2_domestic_floor_audit.lua' or path=='mappings/gen2_facility_floor_audit.lua'
      or path=='mappings/gen2_interior_chair_audit.lua' then return nil end
    if path=='mappings/posts.lua' or path=='mappings/cut_trees.lua' or path=='mappings/water.lua' or path=='mappings/coasts.lua'
      or path=='mappings/pallet_buildings.lua' or path=='mappings/pallet_details.lua'
      or path=='mappings/gen1_outdoor.lua' or path=='mappings/gen2_outdoor.lua'
      or path=='mappings/gen1_caves.lua' or path=='mappings/gen2_buildings.lua'
      or path=='mappings/gen1_extended.lua' or path=='mappings/gen2_outdoor_extended.lua' or path=='mappings/azalea.lua' or path=='mappings/viridian.lua' or path=='mappings/gen2_pallet.lua' or path=='mappings/mahogany.lua' or path=='mappings/johto_terrain.lua' or path=='mappings/cianwood.lua' or path=='mappings/olivine.lua' or path=='mappings/ecruteak.lua' or path=='mappings/north_johto.lua' or path=='mappings/silver_cave_outside.lua' or path=='mappings/johto_terrain_repeats.lua' or path=='mappings/johto_route_details.lua' or path=='mappings/goldenrod_arcade.lua'
      or path=='mappings/buildings_extended.lua' or path=='mappings/building_overhangs.lua' or path=='mappings/goldenrod.lua' or path=='mappings/pallet_overhangs.lua' or path=='mappings/johto_remaining.lua' or path=='mappings/interiors.lua'
      or path=='mappings/gen2_house_context_cleanup.lua' or path=='mappings/gen2_caves.lua' or path=='mappings/park.lua' or path=='mappings/johto_cave_finish.lua' or path=='mappings/johto_rooms_finish.lua' or path=='mappings/johto_gate_finish.lua' or path=='mappings/johto_shared_finish.lua' or path=='mappings/johto_lighthouse_finish.lua' or path=='mappings/johto_tower_finish.lua' or path=='mappings/johto_gamecorner_finish.lua' or path=='mappings/gen1_center_finish.lua' or path=='mappings/gen1_commercial_finish.lua' or path=='mappings/gen1_domestic_finish.lua' or path=='mappings/gen1_facilities_finish.lua' or path=='mappings/gen1_galleries_finish.lua' or path=='mappings/gen1_gates_finish.lua' or path=='mappings/gen1_lab_finish.lua' or path=='mappings/gen1_overworld_finish.lua' or path=='mappings/gen1_plateau_finish.lua' or path=='mappings/gen1_safari_finish.lua' or path=='mappings/gen1_ship_finish.lua' or path=='mappings/gen1_special_finish.lua' or path=='mappings/gen1_temples_finish.lua' or path=='mappings/johto_unique_objects_finish.lua' or path=='mappings/johto_shrine_finish.lua' or path=='mappings/johto_port_finish.lua' or path=='mappings/johto_pokecom_finish.lua' or path=='mappings/johto_facility_finish.lua' or path=='mappings/johto_battle_outside_finish.lua' or path=='mappings/johto_station_finish.lua' or path=='mappings/johto_ruins_finish.lua' or path=='mappings/johto_radio_finish.lua' or path=='mappings/johto_gyms_finish.lua' or path=='mappings/johto_labrooms_finish.lua' or path=='mappings/johto_domestic_finish.lua' or path=='mappings/johto_mart_finish.lua' or path=='mappings/johto_dragonden_finish.lua' or path=='mappings/johto_battle_inside_finish.lua' or path=='mappings/johto_underground_finish.lua' then return nil end
    if path=='mappings/reviewed.lua' then
      return 'local out={} for i,row in ipairs(__tileMainFixture.reviewed)do out[i]=row end return out'
    end
    if modules[path] then return 'return __tileMainFixture.'..modules[path] end
    local gen=tonumber(path:match('^lib/gen([123])%.lua$'))
    assert(gen,'unexpected module read '..path)
    return 'return __tileMainFixture.adapters['..gen..']'
  end
  entry(mod)
  local hackCatalogRead=false
  for _,path in ipairs(fixture.reads)do if path=='lib/johto_hack_flora.lua'then hackCatalogRead=true end end
  eq(hackCatalogRead,generation==2,'native Johto foliage routes only to Gen2; other game preferences stay unchanged')
  local furnitureRead=false
  for _,path in ipairs(fixture.reads)do if path=='lib/johto_furniture.lua'then furnitureRead=true end end
  eq(furnitureRead,generation==2,'bounded Johto furniture catalog only loads for Gen2 hosts')
  local treeChoices=mod.exports.flora:choices('trees')
  eq(treeChoices[2][2],'random');eq(treeChoices[3][2],'mixed','native Johto choices retain connected-area customization modes')
  if generation==2 then
    eq(treeChoices[4][2],'johto-hack-crystaldust-conifer','Gen2 numbered choices begin with checked native foliage')
  else
    eq(treeChoices[4][2],'natural-1-1','other generations retain their original numbered artwork choices')
  end
  eq(fixture.composerCreations,nil,'native compositor stays lazy at startup')
  local compositionRow={kind='native_composite'}
  eq(fixture.sessionCtx.composeFrames(compositionRow),'animated composition','main dispatches animated composite through frames API')
  eq(fixture.animatedRow,compositionRow);eq(fixture.composerCreations,1)
  eq(fixture.sessionCtx.compose(compositionRow),'static composition')
  eq(fixture.staticRow,compositionRow);eq(fixture.composerCreations,1,'static and animated paths share the lazy compositor')
  eq(fixture.composerCtx.donor,fixture.decoder);eq(type(fixture.composerCtx.newImageData),'function')
  eq(type(fixture.donorCtx.identityToken),'function');eq(fixture.donorCtx.identityToken(),0,'import digest cache begins in its first frame')
  eq(fixture.installed,generation,'only active generation adapter installed')
  eq(mod.exports.clinicChansey~=nil,generation==2,'clinic residents only install on Gen2 hosts')
  if generation==2 then
    eq(fixture.clinicCtx.catalog,fixture.clinicCatalog)
    eq(fixture.clinicCtx.version(),gameId)
    eq(fixture.clinicCtx.style(),state.style)
    eq(fixture.clinicCtx.active(),true)
    eq(fixture.clinicCtx.resolveProvider(),nil,'WildFollowers remains optional')
  end
  eq(next(fixture.sessionCtx.mappings),nil,'optional missing tree module leaves reviewed set usable')
  eq(fixture.adapterCtx.version(),gameId)
  eq(fixture.adapterCtx.active(),true,'active hook marks ownership')
  if runtime.hooks.ownerEpoch then
    local chains=runtime.hooks.chains
    runtime.hooks.chains=setmetatable({},{__index=function()error('render must not scan hook chains')end})
    eq(fixture.adapterCtx.active(),true,'ownership epochs avoid hook-chain access')
    runtime.hooks.chains=chains
  end
  if generation==3 then
    local berryHost=gameId=='ruby'or gameId=='sapphire'or gameId=='emerald'
    eq(mod.exports.berryTheme~=nil,berryHost,'only native RSE hosts install berry actor artwork')
    if berryHost then
      eq(fixture.berryCtx.catalog,fixture.berryCatalog)
      eq(fixture.berryCtx.version(),gameId);eq(fixture.berryCtx.style(),state.style)
      eq(fixture.berryCtx.active(),true);eq(fixture.berryPrepares,1,'berry startup preparation is outside draw')
      eq(fixture.berryCtx.berryStyle(),'crystal','fresh berry artwork defaults to Crystal')
      eq(type(fixture.berryCtx.source),'function');eq(type(fixture.berryCtx.sheet),'function')
    end
    eq(#schemas,berryHost and 4 or 3);eq(#schemas[1].choices,4)
    eq(schemas[1].choices[3][1],'GEN 1');eq(schemas[1].choices[4][1],'GEN 2')
    eq(schemas[2].key,'speed_flowers');eq(schemas[3].key,'speed_water')
    local rows=hooks['ui.options.rows'](function(_,out)out[#out+1]={id='native'};return out end,game,{})
    eq(#rows,berryHost and 6 or 5);eq(rows[2].value(),'ORIGINAL');eq(rows[3].label,'FLOWERS SPEED');eq(rows[4].label,'WATER SPEED')
    local coverageRow=rows[#rows]
    eq(coverageRow.id,'tileshift:coverage');eq(coverageRow.label,'MAP TILES')
    eq(coverageRow.value(),'COMPLETE');eq(coverageRow.step(),false)
    if berryHost then
      eq(schemas[4].key,'berry_style');eq(schemas[4].default,2)
      eq(schemas[4].choices[1][1],'NATIVE');eq(schemas[4].choices[1][2],1)
      eq(schemas[4].choices[2][1],'CRYSTAL');eq(schemas[4].choices[2][2],2)
      eq(rows[5].id,'tileshift:berry_style');eq(rows[5].label,'BERRY TREES');eq(rows[5].value(),'CRYSTAL')
    end
    for _,style in ipairs({'gen3','gen1','gen2','original'})do rows[2].step({game=game},1);eq(state.style,style)end
    eq(mod.exports.select('gen1'),true);eq(state.style,'gen1');eq(rows[2].value(),'GEN 1')
    eq(mod.exports.select('gen2'),true);eq(state.style,'gen2');eq(rows[2].value(),'GEN 2')
    if berryHost then
      eq(fixture.berryCtx.style(),'gen2');eq(fixture.berryPrepares>1,true,'style changes prepare/restore berry art immediately')
      local revision,prepares=state.revision,fixture.berryPrepares
      emit('mod.options_changed',{mod='tileshift',key='berry_style',value=1})
      eq(fixture.berryCtx.berryStyle(),'native');eq(stored.berry_style,1);eq(rows[5].value(),'NATIVE')
      eq(state.style,'gen2');eq(state.revision,revision,'berry preference does not invalidate map backgrounds')
      eq(fixture.berryPrepares,prepares+1,'Native immediately requests pooled actor restoration')
      emit('mod.options_changed',{mod='tileshift',key='berry_style',value=0/0})
      eq(fixture.berryCtx.berryStyle(),'native','invalid manager values retain the berry preference')
      mod.exports.select('original');mod.exports.select('gen2')
      eq(fixture.berryCtx.berryStyle(),'native','background changes retain independent Native preference')
      rows[5].step({game=game},1)
      eq(fixture.berryCtx.berryStyle(),'crystal');eq(stored.berry_style,2);eq(rows[5].value(),'CRYSTAL')
      eq(game.options.modOptions.tileshift.berry_style,2);eq(game.save.options.modOptions.tileshift.berry_style,2)
      eq(game.mods.modOptions.tileshift.berry_style,2)
    end
    hooks['core.update'](function()return 'berry-update'end,game,1.05)
    eq(fixture.berryChecks or 0,berryHost and 1 or 0,'source revalidation runs in the update poll')
    eq(fixture.adapterCtx.animationSpeed('water'),0)
    rows[4].step({game=game},1);eq(fixture.adapterCtx.animationSpeed('water'),.5)
    local art={{role='tree',style='gen1'}}
    eq(fixture.sessionCtx.customizeRows(art,gameId,{}),art,'Gen3 host keeps the selected GB artwork')
    emit('mod.options_changed',{mod='tileshift',key='style',value=3});eq(state.style,'gen1')
    emit('mod.options_changed',{mod='tileshift',key='style',value=4});eq(state.style,'gen2')
    emit('mod.options_changed',{mod='tileshift',key='style',value=2});eq(state.style,'gen3','stored Gen3 index stayscompatible')
    runtime.hooks.chains['core.update']={}
    eq(fixture.adapterCtx.replacements(gameId,'TEST'),nil)
    emit('mod.options_changed',{mod='tileshift',key='style',value=3});eq(state.style,'gen3')
    mod.exports.dispose();mod.exports.dispose();eq(fixture.closed,1)
    eq(fixture.berryDisposes or 0,berryHost and 1 or 0,'berry actor disposal runs exactly once')
    eq(#listeners['mod.options_changed'],0)
    mod.options.get=function()return 999 end;entry(mod);eq(state.style,'gen2')
    if berryHost then eq(fixture.berryCtx.berryStyle(),'crystal','invalid stored berry preference falls back to Crystal')end
    mod.exports.dispose()
    if berryHost then
      mod.options.get=function()return nil end;stored.berry_style=1
      entry(mod);eq(fixture.berryCtx.berryStyle(),'native','saved Native preference survives reload')
      mod.exports.dispose()
      stored.berry_style=nil;entry(mod)
      eq(fixture.berryCtx.berryStyle(),'crystal','missing preference uses the fresh Crystal default')
      mod.exports.dispose()
    end
  else
  eq(mod.exports.state,state);eq(state.style,'original');eq(schemas[1].key,'style')
  eq(schemas[1].default,2);eq(schemas[1].type,'choice');eq(#schemas[1].choices,2)
  eq(schemas[1].choices[1][1],'ORIGINAL');eq(schemas[1].choices[1][2],1)
  eq(schemas[1].choices[2][1],'GEN 3');eq(schemas[1].choices[2][2],2)
  for _,choice in ipairs(schemas[1].choices)do
    eq(choice[1]~='EMERALD' and choice[1]~='FIRERED' and choice[1]~='LEAFGREEN'
      and choice[1]~='RUBY' and choice[1]~='SAPPHIRE',true,'GBA origins do not appear as separate menu themes')
  end
  eq(type(runtime._tileShiftDispose),'function')
  local actual=fixture.adapterCtx.replacements(gameId,'TEST',{id='DEF'})
  eq(actual.version,gameId);eq(actual.tileset,'TEST')
  local vanillaCalls=0
  local rows=hooks['ui.options.rows'](function(g,out)
    eq(g,game);vanillaCalls=vanillaCalls+1;out[#out+1]={id='native'};return out
  end,game,{})
  eq(vanillaCalls,1);eq(#rows,15);eq(rows[1].id,'native');eq(rows[2].value(),'ORIGINAL')
  local centerRow=table.remove(rows,3)
  eq(centerRow.label,'POKEMON CENTERS');eq(centerRow.value(),'COMPACT')
  local compactRow={id=0,quadrant=0,role='larger_center',parts={'expanded'},asset='expanded.png',buildingCompact={kind='native_composite',parts={'compact'}}}
  local compactRows=fixture.sessionCtx.customizeRows({compactRow},gameId,{})
  eq(compactRows[1].parts[1],'compact');eq(compactRows[1].asset,nil)
  eq(compactRow.parts[1],'expanded','switching never mutates reviewed mappings')
  centerRow.step({game=game},1);eq(centerRow.value(),'EXPANDED');eq(stored.center_style,2)
  local expandedRows=fixture.sessionCtx.customizeRows({compactRow},gameId,{})
  eq(expandedRows[1],compactRow)
  centerRow.step({game=game},-1);eq(stored.center_style,1);game.writes=0
  eq(rows[14].label,'MAP TILES');eq(rows[14].value(),'COMPLETE');eq(rows[14].step(),false)
  eq(rows[3].label,'TREES');eq(rows[4].label,'BIG TREES');eq(rows[5].label,'CUT TREES')
  eq(rows[6].label,'FLOWERS');eq(rows[7].label,'TALL GRASS');eq(rows[8].label,'WATER')
  eq(rows[9].label,'TREES SPEED');eq(rows[10].label,'FLOWERS SPEED')
  eq(rows[11].label,'GRASS SPEED');eq(rows[12].label,'WATER SPEED')
  eq(rows[9].value(),'OFF');rows[9].step({game=game},1)
  eq(rows[9].value(),'SLOW');eq(stored.speed_trees,2);eq(game.writes,1);game.writes=0
  eq(rows[3].value(),'DEFAULT');eq(schemas[8].key,'flora_water');eq(#schemas[8].choices,6)
  eq(schemas[8].choices[4][2],6,'animated blue water keeps its existing stored ID')
  eq(rows[2].step({game=game},1),false)
  eq(state.style,'gen3');eq(rows[2].value(),'GEN 3');eq(stored.style,2)
  eq(game.options.modOptions.tileshift.style,2);eq(game.save.options.modOptions.tileshift.style,2)
  eq(game.mods.modOptions.tileshift.style,2);eq(game.writes,1)
  eq(rows[2].step({game=game},-1),false);eq(state.style,'original');eq(stored.style,1)
  eq(rows[2].step({game=game},-1),false);eq(state.style,'gen3');eq(stored.style,2)
  for _,unsupported in ipairs({'red','blue','yellow','gold','silver','crystal','unknown'})do
    local bad,why=mod.exports.select(unsupported)
    eq(bad,nil);eq(why,'Unknown tileset style');eq(state.style,'gen3','unimplemented theme stays unavailable')
  end
  for _,alias in ipairs({'ruby','sapphire','emerald','firered','leafgreen'})do
    eq(mod.exports.select(alias),true);eq(state.style,'gen3');eq(rows[2].value(),'GEN 3')
  end
  eq(mod.exports.select('original'),true)
  local value=hooks['core.update'](function(g,dt)eq(g,game);eq(dt,.25);return 'updated'end,game,.25)
  eq(value,'updated')
  eq(fixture.donorCtx.identityToken(),0,'ordinary updates do not reopen import markers')
  if generation==2 then
    eq(game.world.mapImage,'native-CURRENT');eq(game.world.neighbors[1].image,'native-NEIGHBOR')
  end
  emit('mod.options_changed',{mod='other',key='style',value=2});eq(state.style,'original')
  emit('mod.options_changed',{mod='tileshift',key='other',value=2});eq(state.style,'original')
  emit('mod.options_changed',nil);eq(state.style,'original')
  emit('mod.options_changed',{mod='tileshift',key='style',value=0/0});eq(state.style,'original')
  if generation==2 then game.world.mapImage='stale';game.world.neighbors[1].image='stale' end
  emit('mod.options_changed',{mod='tileshift',key='style',value=2})
  eq(state.style,'gen3','mod-manager option event applies art selection immediately')
  eq(stored.style,2);eq(rows[2].value(),'GEN 3')
  for i=1,4 do hooks['core.update'](function()end,game,.25)end
  eq(fixture.polls or 0,generation<3 and 1 or 0,'imports are polled once per second, never per draw')
  eq(rows[13].label,'GRASS MOTION');eq(rows[13].value(),'ALWAYS')
  if generation==2 then
    eq(game.world.mapImage,'native-CURRENT','manager option refreshes cached Gen2 buffer')
    eq(game.world.neighbors[1].image,'native-NEIGHBOR')
  end
  -- Mask decoder enforces native effect references and preserves the reviewed
  -- eight-pixel foot strip rather than substituting a whole opaque grass tile.
  local mask,why=fixture.sessionCtx.foreground({game='emerald',effect='tall_grass',hash='digest'})
  eq(why,nil);eq(mask.w,16);eq(mask.h,16);eq(mask.pasted[2],0);eq(mask.pasted[3],8)
  eq(mask.pasted[4],0);eq(mask.pasted[5],72);eq(mask.pasted[6],16);eq(mask.pasted[7],8)
  local readCount=#nativeReads
  eq(fixture.sessionCtx.foreground({game='emerald',effect='tall_grass',hash='digest'}),mask)
  eq(#nativeReads,readCount,'validated effect cached')
  local stale,staleWhy=fixture.sessionCtx.foreground({game='emerald',effect='tall_grass',hash='stale'})
  eq(stale,nil,'a cached foreground must not bypass the next mapping fingerprint')
  eq(staleWhy,'Native grass effect fingerprint changed')
  runtime.hooks.chains['core.update']={}
  if runtime.hooks.ownerEpoch then runtime.hooks.epoch=runtime.hooks.epoch+1 end
  eq(fixture.adapterCtx.active(),false,'removed hook loses ownership')
  eq(fixture.adapterCtx.replacements(gameId,'TEST'),nil,'deactivated mod supplies no art')
  emit('mod.options_changed',{mod='tileshift',key='style',value=3})
  eq(state.style,'gen3','unowned mod ignores subsequent manager events')
  mod.exports.dispose();mod.exports.dispose()
  eq(fixture.closed,1);eq(fixture.invalidations,1);eq(runtime._tileShiftDispose,nil)
  eq(fixture.adapterCtx.active(),false)
  eq(#listeners['mod.options_changed'],0,'dispose removes owned option listener')
  fixture.trees={{game='red',style='gen3',tileset='OVERWORLD',id=17,quadrant=2,
    role='tree crown',status='reviewed',evidence='tree fixture',sourceHash=string.rep('a',64),
    kind='third_party',asset='assets/third_party/tree.png',credit='Fixture artist',
    sourceUrl='https://example.com/tree.png',base={game='emerald',tileset='PAIR',id=1,hash=string.rep('b',64)}}}
  local oldDisposed=0;runtime._tileShiftDispose=function()oldDisposed=oldDisposed+1 end
  entry(mod);eq(oldDisposed,1,'previous adapter disposed before installing replacement')
  local treeKey=mapping.key(fixture.trees[1])
  eq(fixture.sessionCtx.mappings[treeKey],fixture.trees[1],'optional tree module appended before validation')
  mod.options.get=function()return 999 end
  entry(mod);eq(state.style,'gen3','out-of-range stored selection clamps to implemented style')
  schemas=nil
  mod.options.get=function()return schemas and schemas[1].default end;stored.style=1
  entry(mod);eq(state.style,'original','saved Original preference stays respected')
  mod.options.get=function()return nil end;stored.style=nil
  entry(mod);eq(state.style,'gen3','fresh install defaults to implemented Gen3 theme')
  mod.exports.dispose()
  end
end
_G.__tileMainFixture=nil
for name,value in pairs(originalLoaded)do package.loaded[name]=value end
load=originalLoad
print('PASS entry-point lifecycle and settings: '..count..' assertions across eleven games')
