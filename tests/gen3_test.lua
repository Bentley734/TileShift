-- Pure graphics fixtures: no ROM art or gameplay mutations are required.
local root = (arg and arg[1]) or 'TileShift'
local Adapter = assert(loadfile(root .. '/lib/gen3.lua'))()
local checks = 0
local imageAllocations,pastes=0,0
local function eq(actual, expected, message)
  checks = checks + 1
  assert(actual == expected, (message or 'unexpected value') .. ': ' .. tostring(actual)
    .. ' ~= ' .. tostring(expected))
end
local function data(w, h, fill)
  imageAllocations=imageAllocations+1
  local d = {w = w, h = h, pixels = {}}
  for i = 1, w * h do d.pixels[i] = fill or 0 end
  function d:getDimensions() return self.w, self.h end
  function d:paste(source, dx, dy, sx, sy, sw, sh)
    pastes=pastes+1
    sx, sy = sx or 0, sy or 0
    sw, sh = sw or source.w, sh or source.h
    for y = 0, sh - 1 do
      for x = 0, sw - 1 do
        assert(dx+x >= 0 and dx+x < self.w and dy+y >= 0 and dy+y < self.h)
        self.pixels[(dy+y)*self.w+dx+x+1] = source.pixels[(sy+y)*source.w+sx+x+1]
      end
    end
  end
  function d:sample(x, y) return self.pixels[y*self.w+x+1] end
  return d
end
local function fillSlot(d, slot, color)
  d:paste(data(16, 16, color), slot*16, 0)
end
local function atlas()
  local t = {cols = 2, midToSlot = {[0] = 0, [12] = 1}, imageData = data(32, 16, 1),
    overImageData = data(32, 16, 2), midImageData = data(32, 16, 3),
    uploads = 0, pair = 'fixture'}
  t.midImage = {replacePixels=function(_, source)
    t.gpuMid=data(32,16); t.gpuMid:paste(source,0,0)
  end}
  t.midImageAlt = {replacePixels=function(_, source)
    t.gpuMidAlt=data(32,16); t.gpuMidAlt:paste(source,0,0)
  end}
  return t
end
local ts, native, animation, view = atlas(), {}, {}, {}
native._pairs = {fixture = ts}
function native.markDirty(t, over, slot)
  assert(type(over)=='boolean','native markDirty takes a boolean overhead flag')
  local key = over and '_dirtyOver' or '_dirtyUnder'
  t[key] = t[key] or {}; t[key][slot] = true
end
function native.flush(t, under, over)
  t.uploads = t.uploads + 1
  if under then t.gpuUnder = data(32,16); t.gpuUnder:paste(t.imageData,0,0) end
  if over then t.gpuOver = data(32,16); t.gpuOver:paste(t.overImageData,0,0) end
  t._dirtyUnder, t._dirtyOver = nil, nil
  return 'flushed', nil, 3
end
function native.get(pair) return native._pairs[pair], 'second return' end
function native.setSlotPalette(t, _, color)
  fillSlot(t.imageData, 0, color)
  fillSlot(t.overImageData, 0, color+1)
  fillSlot(t.midImageData, 0, color+2)
  native.flush(t, true, true)
  return true
end
function native.resetSlotPalette(t) return native.setSlotPalette(t, 0, 7) end
local entry = {atlas = ts}
function animation._applyKind(e, _, frame, defer)
  if frame == -1 then return nil end
  -- Actual0.3.97 FRLG/RSE writers mark each plane BEFORE a full/8px paste.
  native.markDirty(e.atlas, false, 0)
  fillSlot(e.atlas.imageData, 0, frame)
  native.markDirty(e.atlas, false, 1)
  fillSlot(e.atlas.imageData, 1, frame+1)
  native.markDirty(e.atlas, true, 0)
  fillSlot(e.atlas.overImageData, 0, frame+2)
  if not defer then native.flush(e.atlas, true, true) end
  return frame, nil, 'tail'
end
function animation.bindPair(_, t)
  animation._applyKind({atlas = t}, 'water', 8, true)
  native.flush(t, true, true)
  return true
end
function animation.stepRse()
  animation._applyKind(entry, 'water', 10, true)
  native.setSlotPalette(ts, 0, 11)
  native.flush(ts, true, true)
end
function animation.step() return animation.stepRse() end
function animation.setVisiblePairs() return animation._applyKind(entry, 'water', 12) end
function view.draw() return 'drawn', nil, 2 end

local originalGet, originalFlush, originalDraw = native.get, native.flush, view.draw
local originalApply, originalStep = animation._applyKind, animation.step
local revision, mapRevision, game = 0, 0, 'firered'
local map = {[0] = {under = data(16,16,90), over = data(16,16,91), mid = data(16,16,92)}}
local remove = Adapter.install({native=native, animation=animation, view=view,
  newImageData=data, version=function() return game end,
  revision=function() return revision end,
  replacements=function(version, pair)
    eq(pair, 'fixture', 'pair identity')
    return version == 'firered' and map or nil, mapRevision
  end})
eq(ts.imageData:sample(0,0),90,'under installed')
eq(ts.overImageData:sample(0,0),91,'over installed')
eq(ts.midImageData:sample(0,0),92,'middle installed')
eq(ts.gpuMid:sample(0,0),92,'middle uploaded')
eq(ts.gpuMidAlt:sample(0,0),92,'middle alternate texture refreshed')
eq(ts.midImageData:sample(16,0),3,'unmapped middle retained')
eq(ts.imageData:sample(16,0),1,'unmapped pixels kept')
eq(ts.midToSlot[0],0,'zero slot retained')
eq(ts.midToSlot[12],1,'other ids retained')
local got, second = native.get('fixture')
eq(got,ts); eq(second,'second return')

local a,b,c = animation._applyKind(entry,'water',5)
eq(a,5); eq(b,nil); eq(c,'tail')
eq(ts.imageData:sample(0,0),90,'source animation cannot overwrite donor')
eq(ts.overImageData:sample(0,0),91)
eq(ts.gpuUnder:sample(0,0),90,'upload protected')
eq(ts.gpuOver:sample(0,0),91,'over upload protected')
eq(ts.midImageData:sample(0,0),92,'middle animation protected')
eq(ts.gpuMid:sample(0,0),92,'middle upload protected')
eq(ts.midImageData:sample(16,0),3,'native animator does not mutate the separate middle plane')
eq(ts.imageData:sample(16,0),6,'unmapped source animates')
local uploads = ts.uploads
animation._applyKind(entry,'water',-1)
eq(ts.uploads,uploads,'no-op native animation causes no extra GPU upload')
local warmPastes,warmImages=pastes,imageAllocations
for i=1,1000 do animation._applyKind(entry,'water',-1);view.draw()end
eq(pastes,warmPastes,'1000 unchanged frames perform no atlas/source pixel copying')
eq(imageAllocations,warmImages,'1000 unchanged frames allocate no image buffers')
local f1,f2,f3 = native.flush(ts,true,true)
eq(f1,'flushed'); eq(f2,nil); eq(f3,3)
eq(native.get('missing'),nil,'missing atlas remains missing')

animation.bindPair('fixture',ts)
eq(ts.imageData:sample(0,0),90,'bind catch-up protected')
eq(ts.imageData:sample(16,0),9,'bind catch-up preserved')
animation.step()
eq(ts.imageData:sample(0,0),90,'nested RSE/palette mutation protected')
eq(ts.midImageData:sample(0,0),92,'nested middle palette mutation protected')
eq(ts.gpuMid:sample(0,0),92,'nested middle GPU upload protected')
eq(ts.imageData:sample(16,0),11,'RSE uncovered native updates')
native.resetSlotPalette(ts)
eq(ts.imageData:sample(0,0),90,'palette restore protected')
animation.setVisiblePairs({fixture=true})
eq(ts.imageData:sample(0,0),90,'visibility catch-up protected')

-- Remove an override while the atlas stays cached: recover its CURRENT frame.
map[0] = nil; revision = revision+1
local d,e,f = view.draw()
eq(d,'drawn'); eq(e,nil); eq(f,2)
eq(ts.imageData:sample(0,0),12,'current native frame restored after unmapping')
eq(ts.overImageData:sample(0,0),14,'current native over frame restored')
eq(ts.midImageData:sample(0,0),9,'current native middle restored')
eq(ts.gpuMid:sample(0,0),9,'native middle restoration uploaded')
eq(ts.gpuUnder:sample(0,0),12,'native restoration uploaded')

-- Invalid ids and pieces cannot silently replace another tile.
map = {[-1]={under=data(16,16,50)}, [999]={under=data(16,16,50)},
  [12]={under=data(8,8,50)}, ['12']={under=data(16,16,50)}}
view.draw()
eq(ts.imageData:sample(16,0),13,'invalid rows ignored')
map = {[12]={under=data(16,16,70)}}; view.draw()
eq(ts.imageData:sample(16,0),70,'new map identity refreshes')
eq(ts.overImageData:sample(16,0),2,'unspecified over layer preserved')
map[12].under=data(16,16,71); mapRevision=mapRevision+1; view.draw()
eq(ts.imageData:sample(16,0),71,'second-return revision refreshes in-place edits')
map[12].mid=data(16,16,73); mapRevision=mapRevision+1; view.draw()
eq(ts.midImageData:sample(16,0),73,'middle can be added to a cached mapping')
game='emerald'; view.draw()
eq(ts.imageData:sample(16,0),13,'game change restores source')
eq(ts.midImageData:sample(16,0),3,'game change restores native middle')
game='firered'; view.draw()
eq(ts.imageData:sample(16,0),71)
eq(ts.midImageData:sample(16,0),73)

-- Native error remains an error, but donor art is put back before propagation.
-- Exercise through the wrapped original function's own callback path.
local didThrow = false
-- A failing nested native mutation is simulated by making flush throw once.
local originalMark = native.markDirty
native.markDirty = function(t, over, slot)
  originalMark(t,over,slot)
  if slot == 1 and not didThrow then didThrow=true; error('native fixture failure') end
end
local ok, err = pcall(animation._applyKind,entry,'water',20)
eq(ok,false,'native error propagated')
assert(tostring(err):find('native fixture failure',1,true))
native.markDirty=originalMark
eq(ts.imageData:sample(16,0),71,'donor restored after native failure')
eq(ts.midImageData:sample(16,0),73,'middle restored after native failure')

remove(); remove()
eq(native.get,originalGet,'get restored')
eq(native.flush,originalFlush,'flush restored')
eq(view.draw,originalDraw,'draw restored')
eq(animation._applyKind,originalApply,'animator restored')
eq(animation.step,originalStep,'step restored')
eq(ts.imageData:sample(16,0),13,'cleanup restores the last source frame when native fails before its paste')
eq(ts.midImageData:sample(16,0),3,'cleanup restores current native middle')
eq(ts.gpuMid:sample(16,0),3,'cleanup uploads current native middle')
eq(ts.midToSlot[0],0); eq(ts.midToSlot[12],1)

-- Evicted images are not touched or revived by refresh/cleanup.
local ts2 = atlas(); native._pairs.fixture=ts2
local dispose = Adapter.install({native=native,animation=animation,view=view,
  version='firered',replacements=function() return {[0]={under=data(16,16,99)}} end,
  newImageData=data})
native._pairs.fixture=nil; ts2.imageData=nil
dispose()

-- Palette operations can load an atlas for the first time inside a mutation.
local late
native.get = function(pair)
  eq(pair,'late')
  if not late then late=atlas(); native._pairs.late=late end
  return late
end
native.setSlotPalette = function(pair, _, color)
  local loaded=native.get(pair)
  fillSlot(loaded.imageData,0,color)
  native.flush(loaded,true,false)
end
local finish = Adapter.install({native=native,animation=animation,view=view,
  version='ruby',replacements=function() return {[0]={under=data(16,16,99)}} end,
  newImageData=data})
native.setSlotPalette('late',0,55)
eq(late.imageData:sample(0,0),99,'first-load palette donor protected')
eq(late.gpuUnder:sample(0,0),99,'first-load palette upload protected')
finish()
eq(late.imageData:sample(0,0),55,'first-load palette source restored on cleanup')

local middleOnly=atlas(); native._pairs={fixture=middleOnly}
local endMiddle=Adapter.install({native=native,animation=animation,view=view,
  version='emerald',replacements=function() return {[0]={mid=data(16,16,80)}} end,
  newImageData=data})
eq(middleOnly.imageData:sample(0,0),1,'middle-only leaves under intact')
eq(middleOnly.overImageData:sample(0,0),2,'middle-only leaves overhead intact')
eq(middleOnly.midImageData:sample(0,0),80,'middle-only accepted')
eq(middleOnly.gpuMid:sample(0,0),80,'middle-only upload reaches middle texture')
eq(middleOnly.uploads,0,'middle-only avoids native under/over flush')
endMiddle()
eq(middleOnly.midImageData:sample(0,0),3,'middle-only cleanup restores source')
eq(middleOnly.gpuMid:sample(0,0),3,'middle-only cleanup uploaded')

local noMiddle=atlas(); noMiddle.midImageData=nil; native._pairs={fixture=noMiddle}
local endAbsent=Adapter.install({native=native,animation=animation,view=view,
  version='ruby',replacements=function() return {[0]={mid=data(16,16,80)}} end,
  newImageData=data})
eq(noMiddle.imageData:sample(0,0),1,'absent middle is not substituted into under')
eq(noMiddle.overImageData:sample(0,0),2,'absent middle is not substituted into overhead')
endAbsent()
-- Explicit transparent BG2/middle planes remove the original GBA object;
-- source animations and style cleanup still recover its latest native frame.
local transparentTs=atlas();native._pairs={fixture=transparentTs};entry.atlas=transparentTs
local blank=data(16,16,0)
local pieces={[0]={under=data(16,16,41),over=blank,mid=blank}}
local now,rate=0,1
local stopTransparent=Adapter.install({native=native,animation=animation,view=view,
  version='firered',replacements=function()return pieces end,newImageData=data})
eq(transparentTs.overImageData:sample(0,0),0,'explicit transparent overlay suppresses native canopy')
eq(transparentTs.midImageData:sample(0,0),0,'explicit transparent middle suppresses native furniture')
animation._applyKind(entry,'water',23)
eq(transparentTs.imageData:sample(0,0),41,'transparent donor under survives source animation')
eq(transparentTs.overImageData:sample(0,0),0,'transparent overlay survives source animation')
stopTransparent()
eq(transparentTs.imageData:sample(0,0),23,'transparent style cleanup restores current native under')
eq(transparentTs.overImageData:sample(0,0),25,'transparent style cleanup restores current native canopy')
eq(transparentTs.midImageData:sample(0,0),3,'transparent middle cleanup restores native pixels')

-- GB water sequences have seconds per frame, shared explicit transparent
-- planes, and only upload when an actual frame image changes.
local animatedTs=atlas();native._pairs={fixture=animatedTs};entry.atlas=animatedTs
local f1={under=data(16,16,61),over=blank,mid=blank}
local f2={under=data(16,16,62),over=blank,mid=blank}
local sequence={[0]={under=f1.under,over=blank,mid=blank,frames={f1,f2},period=.1,category='water'}}
local stopAnimated=Adapter.install({native=native,animation=animation,view=view,
  version='emerald',replacements=function()return sequence end,newImageData=data,
  time=function()return now end,animationSpeed=function(category)eq(category,'water');return rate end})
eq(animatedTs.imageData:sample(0,0),61,'first GB animation frame installed')
now=.05
local samePastes,sameAllocations,sameUploads=pastes,imageAllocations,animatedTs.uploads
view.draw()
eq(pastes,samePastes,'same GB animation frame does not copy pixels')
eq(imageAllocations,sameAllocations,'same GB animation frame allocates no images')
eq(animatedTs.uploads,sameUploads,'same GB animation frame does not upload')
local sharedOver,sharedMiddle=animatedTs.gpuOver,animatedTs.gpuMid
now=.11;view.draw()
eq(animatedTs.gpuOver,sharedOver,'shared blank overlay is not reuploaded on water frame change')
eq(animatedTs.gpuMid,sharedMiddle,'shared blank middle is not reuploaded on water frame change')
eq(animatedTs.imageData:sample(0,0),62,'GB frame advances at its native period')
eq(animatedTs.gpuUnder:sample(0,0),62,'advanced GB frame reaches GPU')
eq(animatedTs.overImageData:sample(0,0),0,'GB frame retains explicit transparent canopy')
local nextPastes,nextUploads=pastes,animatedTs.uploads
now=.15;view.draw()
eq(pastes,nextPastes,'unchanged second GB frame does not copy')
eq(animatedTs.uploads,nextUploads,'unchanged second GB frame does not upload')
rate=0;view.draw()
eq(animatedTs.imageData:sample(0,0),61,'Off selects first GB frame')
animation._applyKind(entry,'water',9)
eq(animatedTs.imageData:sample(0,0),61,'native animation cannot overwrite Off donor frame')
rate=.5;now=.25;view.draw()
eq(animatedTs.imageData:sample(0,0),62,'half speed applies once to GB animation')
stopAnimated()
eq(animatedTs.imageData:sample(0,0),9,'animated cleanup restores current native source')
eq(animatedTs.overImageData:sample(0,0),11,'animated cleanup restores native canopy')
eq(animatedTs.midImageData:sample(0,0),3,'animated cleanup restores native middle')

local absentTs=atlas();absentTs.midImageData=nil;absentTs.overImageData=nil;native._pairs={fixture=absentTs}
now=0;rate=1
local stopAbsentAnimation=Adapter.install({native=native,animation=animation,view=view,
  version='ruby',replacements=function()return sequence end,newImageData=data,time=function()return now end})
now=.11;view.draw()
eq(absentTs.imageData:sample(0,0),62,'absent optional atlas planes do not disable a valid under animation')
stopAbsentAnimation()
eq(absentTs.imageData:sample(0,0),1,'absent-plane animation cleanup preserves original under')

-- RSE writes may replace only an8x8 quarter. Unaffected source pixels must
-- survive, and a bank touching an unrelated slot must not copy donor cells.
local partialTs=atlas();native._pairs={fixture=partialTs}
local quarter=data(8,8,50);local targetSlot=1;local doWrite=true
animation.stepRse=function()
  if not doWrite then return end
  native.markDirty(partialTs,false,targetSlot)
  partialTs.imageData:paste(quarter,targetSlot*16,0,0,0,8,8)
  native.flush(partialTs,true,false)
end
local stopPartial=Adapter.install({native=native,animation=animation,view=view,
  version='ruby',replacements=function()return pieces end,newImageData=data})
local otherPastes=pastes
animation.stepRse()
eq(pastes-otherPastes,2,'unmapped native slot only does its own paste and GPU copy')
eq(partialTs.imageData:sample(0,0),41,'unmapped native animation leaves donor slot intact')
targetSlot=0;animation.stepRse()
eq(partialTs.imageData:sample(0,0),41,'partial native writer cannot erase donor')
doWrite=false
local partialPastes,partialImages=pastes,imageAllocations
for i=1,1000 do animation.stepRse();view.draw()end
eq(pastes,partialPastes,'1000 unchanged RSE steps/draws do no atlas/source copying')
eq(imageAllocations,partialImages,'1000 unchanged RSE steps/draws allocate no images')
stopPartial()
eq(partialTs.imageData:sample(0,0),50,'partial native source quarter restored')
eq(partialTs.imageData:sample(10,10),1,'unmodified native source pixels preserved')

-- Cached palette membership limits restoration to the actual affected slots.
local paletteTs=atlas();native._pairs={fixture=paletteTs}
local prepareCalls=0
native.prepareSlot=function(ts,slot)
  prepareCalls=prepareCalls+1
  return {under={cells={[slot]=true}},over={cells={}}}
end
native.setSlotPalette=function(ts,slot,color)
  fillSlot(ts.imageData,slot,color)
  native.markDirty(ts,false,slot) -- native palette marks AFTER its pixel writes
  native.flush(ts,true,false)
end
local stopPalette=Adapter.install({native=native,animation=animation,view=view,
  version='sapphire',replacements=function()return pieces end,newImageData=data})
local beforeOther=pastes
native.setSlotPalette(paletteTs,1,33)
eq(pastes-beforeOther,2,'unrelated palette only copies its native slot and GPU')
native.setSlotPalette(paletteTs,0,34)
eq(paletteTs.imageData:sample(0,0),41,'palette write cannot replace donor')
native.setSlotPalette(paletteTs,0,35)
eq(prepareCalls,2,'palette membership plan cached per palette slot')
local capturedPalette=native.setSlotPalette
local laterPalette=function(...)return capturedPalette(...)end
native.setSlotPalette=laterPalette
stopPalette()
eq(native.setSlotPalette,laterPalette,'cleanup keeps a later mod wrapper in place')
eq(paletteTs.imageData:sample(0,0),35,'latest native palette restored on cleanup')
eq(paletteTs.imageData:sample(16,0),33,'unmapped palette retains its native update')
native.setSlotPalette(paletteTs,0,36)
eq(paletteTs.imageData:sample(0,0),36,'later wrapper cannot revive disabled donor pixels')
eq(paletteTs.gpuUnder:sample(0,0),36,'later wrapper retains native GPU palette after cleanup')

print('Gen 3 adapter: '..checks..' checks passed')
return checks
