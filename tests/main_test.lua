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
  function state:replacements(v,tileset,def)return {version=v,tileset=tileset,def=def,style=self.style}end
  fixture.decoder={invalidate=function()fixture.invalidations=fixture.invalidations+1 end}
  fixture.donor={new=function(ctx)fixture.donorCtx=ctx;return fixture.decoder end}
  fixture.composition={new=function(ctx)
    fixture.composerCreations=(fixture.composerCreations or 0)+1;fixture.composerCtx=ctx
    return {cell=function(_,row)fixture.staticRow=row;return 'static composition'end,
      frames=function(_,row)fixture.animatedRow=row;return 'animated composition'end}
  end}
  fixture.session={new=function(ctx)fixture.sessionCtx=ctx;return state end}
  for gen=1,3 do
    local selectedGen=gen
    fixture.adapters[gen]={install=function(ctx)
      fixture.installed=selectedGen;fixture.adapterCtx=ctx
      return function()fixture.closed=fixture.closed+1 end
    end}
  end
  _G.__tileMainFixture=fixture
  local modules={['lib/mapping.lua']='mapping',['mappings/reviewed.lua']='reviewed',
    ['lib/donor.lua']='donor',['lib/session.lua']='session',['lib/composition.lua']='composition'}
  local stored,schemas,hooks,listeners={},nil,{},{}
  local function emit(name,payload)
    for _,fn in ipairs(listeners[name] or {})do fn(payload)end
  end
  local game={generation=generation,options={},save={options={}},mods={modOptions={}},writes=0}
  function game:writeOptions()self.writes=self.writes+1 end
  game.world={map={id='CURRENT'},neighbors={{id='NEIGHBOR'}},imageFor=function(_,id)return 'native-'..id end}
  local mod={id='tileshift',generation=generation,exports={},game=game,
    options={define=function(_,rows)schemas=rows end,get=function()return 1 end},
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
    if path=='mappings/trees.lua' then
      return fixture.trees and 'return __tileMainFixture.trees' or nil
    end
    if path=='mappings/posts.lua' or path=='mappings/water.lua' or path=='mappings/coasts.lua'
      or path=='mappings/pallet_buildings.lua' or path=='mappings/pallet_details.lua'
      or path=='mappings/gen1_outdoor.lua' or path=='mappings/gen2_outdoor.lua'
      or path=='mappings/gen1_caves.lua' or path=='mappings/gen2_buildings.lua'
      or path=='mappings/gen1_extended.lua' or path=='mappings/gen2_outdoor_extended.lua'
      or path=='mappings/buildings_extended.lua' or path=='mappings/interiors.lua'
      or path=='mappings/gen2_caves.lua' then return nil end
    if path=='mappings/reviewed.lua' then
      return 'local out={} for i,row in ipairs(__tileMainFixture.reviewed)do out[i]=row end return out'
    end
    if modules[path] then return 'return __tileMainFixture.'..modules[path] end
    local gen=tonumber(path:match('^lib/gen([123])%.lua$'))
    assert(gen,'unexpected module read '..path)
    return 'return __tileMainFixture.adapters['..gen..']'
  end
  entry(mod)
  eq(fixture.composerCreations,nil,'native compositor stays lazy at startup')
  local compositionRow={kind='native_composite'}
  eq(fixture.sessionCtx.composeFrames(compositionRow),'animated composition','main dispatches animated composite through frames API')
  eq(fixture.animatedRow,compositionRow);eq(fixture.composerCreations,1)
  eq(fixture.sessionCtx.compose(compositionRow),'static composition')
  eq(fixture.staticRow,compositionRow);eq(fixture.composerCreations,1,'static and animated paths share the lazy compositor')
  eq(fixture.composerCtx.donor,fixture.decoder);eq(type(fixture.composerCtx.newImageData),'function')
  eq(type(fixture.donorCtx.identityToken),'function');eq(fixture.donorCtx.identityToken(),0,'import digest cache begins in its first frame')
  eq(fixture.installed,generation,'only active generation adapter installed')
  eq(next(fixture.sessionCtx.mappings),nil,'optional missing tree module leaves reviewed set usable')
  eq(fixture.adapterCtx.version(),gameId)
  eq(fixture.adapterCtx.active(),true,'active hook marks ownership')
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
  eq(vanillaCalls,1);eq(#rows,3);eq(rows[1].id,'native');eq(rows[2].value(),'ORIGINAL')
  eq(rows[3].label,'COVERAGE');eq(rows[3].value(),'IN PROGRESS');eq(rows[3].step(),false)
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
  eq(fixture.donorCtx.identityToken(),1,'each native update advances the identity sampling token')
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
_G.__tileMainFixture=nil
for name,value in pairs(originalLoaded)do package.loaded[name]=value end
load=originalLoad
print('PASS entry-point lifecycle and settings: '..count..' assertions across eleven games')
