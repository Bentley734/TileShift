-- ROM-free actor fixtures; real imported-source QA runs separately.
local root=assert(arg and arg[1], 'TileShift directory required')
local berryModule=assert(loadfile(root..'/lib/berry_theme.lua'))()
local berryCatalog={format=1,varieties={},sources={}}
local nativeManifests={}
local payloads, hashes={},{}
local nextHash=1
local function fakeHash(bytes)
  local value=hashes[bytes]
  if not value then value=string.format('%064x',nextHash);nextHash=nextHash+1;hashes[bytes]=value end
  return value
end
local function frames()
  local result={}
  for i=0,8 do
    result[i+1]={w=16,h=i<3 and 16 or 32,y=i<3 and i*16 or 48+(i-3)*32}
  end
  return result
end
for i=1,43 do berryCatalog.varieties[i]={name='fixture-'..i,asset='assets/original/berries/gen2/fixture-'..i..'.png',hash=string.rep('0',64)} end
for _,game in ipairs({'ruby','sapphire','emerald'})do
  local data={};payloads[game]=data
  local manifest='fixture-manifest-'..game
  data['data/generated/gba/berry_trees/manifest.lua']=manifest
  local expected={manifestHash=fakeHash(manifest),trees={}}
  berryCatalog.sources[game]=expected;nativeManifests[game]={trees={}}
  for i=1,43 do
    local stem=(game=='emerald'and'emerald-fixture-'or'fixture-')..i
    local file,idx=stem..'.rgba',stem..'.idx'
    local rgba,indices=string.rep(string.char(i),16*240*4),string.rep(string.char(i),16*240)
    data['data/generated/gba/berry_trees/'..file]=rgba
    data['data/generated/gba/berry_trees/'..idx]=indices
    expected.trees[i]={file=file,idx=idx,rgbaHash=fakeHash(rgba),idxHash=fakeHash(indices),width=16,height=240,frames=frames()}
    nativeManifests[game].trees[i]={berry=i,file=file,idx=idx,width=16,height=240,frames=frames()}
  end
end
local function readSource(game,path)return assert(payloads[game][path],path)end
local function checkedHash(bytes)return hashes[bytes]or string.rep('f',64)end
local results=(function()

local module = berryModule
local counters = {source=0, hash=0, sheet=0, image=0, quad=0, releasedImages=0, releasedQuads=0}
local game, style, owner = 'ruby', 'gen2', true
local berryStyle='crystal'
local badPath, badGeometry
local sourceOverrides={}
local warnings = 0
local nativeImage, nativeQuad = {}, {}
local currentObject, currentActor, unrelated = {}, {}, {}
local nativeSnapshots = {}
local effects = {}
function effects.berryManifest()return nativeManifests[game]end
local original = function(actors)
  local bt=currentObject.berryTree
  local frame=bt.tree.frames[bt.anim.frame+1]
  currentActor.fxObject=currentObject
  currentActor.fxImage=nativeImage;currentActor.fxQuad=bt.quad
  currentActor.x=currentObject.px+(16-frame.w)/2+3.25
  currentActor.y=currentObject.py+16-frame.h-7.5
  currentActor.sortY=currentObject.py;currentActor.elevation=7
  currentActor.priority=4;currentActor.subpriority=13
  currentActor.fxFade='native-fade';currentActor.draw='native-draw'
  actors[#actors+1]=currentActor
  unrelated.fxObject=currentObject;unrelated.fxImage='unrelated';unrelated.fxQuad='other-quad'
  unrelated.x=12;unrelated.y=24;actors[#actors+1]=unrelated
  return 11,'native-return',true
end
effects.collectActors=original
local ctx={effects=effects,catalog=berryCatalog,
  version=function()return game end,style=function()return style end,active=function()return owner end,
  berryStyle=function()return berryStyle end,
  source=function(g,path)
    counters.source=counters.source+1
    local bytes=sourceOverrides[g..':'..path] or readSource(g,path)
    return badPath==path and bytes..'changed' or bytes
  end,
  hash=function(bytes)counters.hash=counters.hash+1;return checkedHash(bytes)end,
  sheet=function(path,hash)
    counters.sheet=counters.sheet+1
    return {path=path,getDimensions=function()return badGeometry and 17 or 16,240 end}
  end,
  newImage=function(data)
    counters.image=counters.image+1
    return {data=data,setFilter=function(self,a,b)assert(a=='nearest'and b=='nearest')end,
      release=function()counters.releasedImages=counters.releasedImages+1 end}
  end,
  newQuad=function(x,y,w,h,iw,ih)
    counters.quad=counters.quad+1
    return {x=x,y=y,w=w,h=h,iw=iw,ih=ih,
      release=function()counters.releasedQuads=counters.releasedQuads+1 end}
  end,
  warn=function()warnings=warnings+1 end}
local theme=module.install(ctx)
local cases=0
for _,g in ipairs({'ruby','sapphire','emerald'})do
  game=g;assert(theme:prepare(game))
  local before={source=counters.source,hash=counters.hash,sheet=counters.sheet,image=counters.image,quad=counters.quad}
  for berry=1,43 do for frame=0,8 do
    local entry=nativeManifests[game].trees[berry]
    local bt={visible=true,tree=entry,anim={frame=frame,timer=17},quad=nativeQuad,id=55,animNum=4,gfxKey='unchanged'}
    currentObject={px=40.5,py=90.25,berryTree=bt,gameplay='unchanged'}
    currentActor={};local actors={}
    local a,b,c=effects.collectActors(actors)
    assert(a==11 and b=='native-return'and c==true)
    assert(#actors==2 and actors[1]==currentActor and actors[2]==unrelated)
    local rectangle=entry.frames[frame+1]
    assert(currentActor.fxImage~=nativeImage and currentActor.fxQuad~=nativeQuad)
    assert(currentActor.fxImage.data.path==berryCatalog.varieties[berry].asset)
    assert(currentActor.fxQuad.y==rectangle.y and currentActor.fxQuad.w==rectangle.w and currentActor.fxQuad.h==rectangle.h)
    assert(currentActor.x==40.5+(16-rectangle.w)/2+3.25 and currentActor.y==90.25+16-rectangle.h-7.5)
    assert(currentActor.sortY==90.25 and currentActor.elevation==7 and currentActor.priority==4 and currentActor.subpriority==13)
    assert(currentActor.fxFade=='native-fade'and currentActor.draw=='native-draw')
    assert(bt.tree==entry and bt.quad==nativeQuad and bt.anim.frame==frame and bt.anim.timer==17)
    assert(bt.id==55 and bt.animNum==4 and bt.gfxKey=='unchanged'and currentObject.gameplay=='unchanged')
    assert(unrelated.fxImage=='unrelated'and unrelated.fxQuad=='other-quad'and unrelated.x==12 and unrelated.y==24)
    cases=cases+1
  end end
  for key,value in pairs(before)do assert(counters[key]==value,'Warm collection performed '..key..' work')end
end
assert(cases==1161 and counters.image==43 and counters.quad==387)
-- One native memo survives real host-name changes. Only known same-ID,
-- identical-pixel/index/frame/program aliases may bind to the current host.
local normalManifest=effects.berryManifest
local cachedManifest=nativeManifests.ruby
effects.berryManifest=function()return cachedManifest end
local aliasCases=0
for _,host in ipairs({'ruby','sapphire','emerald','ruby'})do
 game=host;assert(theme:checkSource(game))
 local before={source=counters.source,hash=counters.hash,sheet=counters.sheet,image=counters.image,quad=counters.quad}
 for berry=1,43 do for frame=0,8 do
  currentObject={px=40.5,py=90.25,berryTree={visible=true,tree=cachedManifest.trees[berry],anim={frame=frame,timer=17},quad=nativeQuad}}
  currentActor={};effects.collectActors({})
  assert(currentActor.fxImage~=nativeImage and currentActor.fxImage.data.path==berryCatalog.varieties[berry].asset)
  aliasCases=aliasCases+1
 end end
 for key,value in pairs(before)do assert(counters[key]==value,'Warm alias collection performed '..key..' work')end
end
assert(aliasCases==1548)
game='emerald';assert(theme:checkSource(game))
local function rejectedChange(tree,key,value)
 local old=tree[key];tree[key]=value
 assert(not theme:checkSource(game));assert(currentActor.fxImage==nativeImage)
 tree[key]=old;assert(theme:checkSource(game));effects.collectActors({});assert(currentActor.fxImage~=nativeImage)
end
rejectedChange(cachedManifest.trees[1],'file','unlisted.rgba')
rejectedChange(cachedManifest.trees[1],'idx','unlisted.idx')
rejectedChange(cachedManifest.trees[1],'berry',2)
rejectedChange(cachedManifest.trees[1].frames[9],'y',207)
rejectedChange(cachedManifest.trees[1].frames[1],'unlistedMetadata','changed')
rejectedChange(cachedManifest.trees[1],'stages',{{anim={{frame=0,duration=999}}}})
-- Even a legitimately checked current import cannot borrow an old cached
-- filename alias if its decoded pixels differ from the frozen alias group.
local native=berryCatalog.sources.emerald.trees[1]
local path='data/generated/gba/berry_trees/'..native.file
local oldHash=native.rgbaHash;local bytes=readSource('emerald',path)
local changed=string.char((bytes:byte(1)+1)%256)..bytes:sub(2)
sourceOverrides['emerald:'..path]=changed;native.rgbaHash=ctx.hash(changed)
assert(not theme:checkSource(game));assert(currentActor.fxImage==nativeImage)
sourceOverrides['emerald:'..path]=nil;native.rgbaHash=oldHash
assert(theme:checkSource(game));effects.collectActors({});assert(currentActor.fxImage~=nativeImage)
effects.berryManifest=normalManifest
currentObject={px=40.5,py=90.25,berryTree={visible=true,tree=nativeManifests.emerald.trees[43],anim={frame=8,timer=17},quad=nativeQuad}}
currentActor={};assert(theme:checkSource(game));effects.collectActors({})
-- The independent Native preference restores the current pooled actor before
-- another collection, keeps every native frame and performs no source work.
berryStyle='native';local nativeReads=counters.source
assert(not theme:prepare(game));assert(currentActor.fxImage==nativeImage and currentActor.fxQuad==nativeQuad)
local nativeCases=0
for berry=1,43 do for frame=0,8 do
 currentObject={px=40.5,py=90.25,berryTree={visible=true,tree=nativeManifests.emerald.trees[berry],anim={frame=frame,timer=17},quad=nativeQuad}}
 currentActor={};effects.collectActors({})
 assert(currentActor.fxImage==nativeImage and currentActor.fxQuad==nativeQuad)
 nativeCases=nativeCases+1
end end
assert(nativeCases==387 and counters.source==nativeReads)
style='original';assert(not theme:prepare(game));style='gen2'
assert(not theme:prepare(game));effects.collectActors({});assert(currentActor.fxImage==nativeImage)
berryStyle='crystal';assert(theme:prepare(game));effects.collectActors({})
assert(currentActor.fxImage~=nativeImage and counters.image==43 and counters.quad==387)
-- Leaving Crystal or losing ownership restores pooled actors immediately.
style='gen1';local reads=counters.source
assert(not theme:prepare(game));assert(currentActor.fxImage==nativeImage and currentActor.fxQuad==nativeQuad)
effects.collectActors({});assert(currentActor.fxImage==nativeImage and counters.source==reads)
style='original';assert(not theme:checkSource(game));effects.collectActors({});assert(currentActor.fxImage==nativeImage)
style='gen2';owner=false;assert(not theme:prepare(game));effects.collectActors({});assert(currentActor.fxImage==nativeImage)
owner=true;assert(theme:prepare(game));effects.collectActors({});assert(currentActor.fxImage~=nativeImage)
badPath='data/generated/gba/berry_trees/manifest.lua'
assert(not theme:checkSource(game));assert(currentActor.fxImage==nativeImage and currentActor.fxQuad==nativeQuad)
reads=counters.source;effects.collectActors({});assert(currentActor.fxImage==nativeImage and counters.source==reads)
badPath=nil;assert(theme:checkSource(game));effects.collectActors({});assert(currentActor.fxImage~=nativeImage)
badPath='data/generated/gba/berry_trees/'..berryCatalog.sources[game].trees[43].file
assert(not theme:checkSource(game));assert(currentActor.fxImage==nativeImage)
badPath=nil;assert(theme:checkSource(game));effects.collectActors({})
-- A later hook remains installed; the disposed inner wrapper becomes inert.
local inner=effects.collectActors
local later=function(...)return inner(...)end
effects.collectActors=later;theme:dispose()
assert(effects.collectActors==later and currentActor.fxImage==nativeImage and currentActor.fxQuad==nativeQuad)
effects.collectActors({});assert(currentActor.fxImage==nativeImage)
assert(counters.releasedImages==43 and counters.releasedQuads==387)
theme:dispose();assert(counters.releasedImages==43)
-- Invalid generated dimensions fail before any actor pixels can be swapped.
effects.collectActors=original;badGeometry=true
local rejected=module.install(ctx);assert(not rejected:prepare(game));effects.collectActors({})
assert(currentActor.fxImage==nativeImage);rejected:dispose();assert(effects.collectActors==original)
return {cases=cases,known_alias_cases=aliasCases,unknown_or_nonidentical_aliases_rejected=true,warm_source_reads=0,warm_hashes=0,warm_sheet_loads=0,warm_image_allocations=0,warm_quad_allocations=0,
  gen1_and_original_untouched=true,native_animation_and_gameplay_state_unchanged=true,
  native_anchor_priority_and_fade_unchanged=true,bad_source_restores_pooled_actor=true,
  lifecycle_and_later_hook_ownership_passed=true,invalid_dimensions_rejected=true}

end)()
assert(results.cases==1161 and results.known_alias_cases==1548 and results.unknown_or_nonidentical_aliases_rejected)
print('berry_theme_test: '..results.cases..' native frames + '..results.known_alias_cases..' profile aliases; negative boundaries, warm IO, lifecycle and native actor state passed')
