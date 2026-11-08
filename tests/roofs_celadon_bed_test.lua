local root=assert(arg[1])
local Fixture=assert(loadfile(root..'/tests/furniture_fixture.lua'))()
local native=assert(loadfile(root..'/tests/celadon_bed_native_alpha.lua'))()
local rows={}
for _,row in ipairs(assert(loadfile(root..'/lib/johto_furniture.lua'))())do
 if row.furniture=='celadon_mansion_bed'then rows[#rows+1]=row end
end
assert(#rows==12,'Complete four-cell foreground must exist in all three cartridges')
local checks=0
local function eq(a,b,why)checks=checks+1;assert(a==b,why or(tostring(a)..' ~= '..tostring(b)))end
local function count(surface)local n=0;for _ in pairs(surface)do n=n+1 end;return n end
local function clone(value)
 if type(value)~='table'then return value end
 local out={};for k,v in pairs(value)do out[k]=clone(v)end;return out
end
local f=Fixture.new(root,rows,native)
for _,game in ipairs({'gold','silver','crystal'})do
 local def=f:select(game,'CELADON_MANSION_2F')
 local original=clone(def.blocks)
 f:map()
 eq(count(f.surface),522,'Every native bed pixel is drawn once, including its four-pixel right extension')
 for key,asset in pairs(f.surface)do
  local x,y=key%4096,math.floor(key/4096)
  eq(x>=0 and x<20 and y>=99 and y<128,true,'The entire native bed remains in its finite room envelope')
 end
 local mapSurface=clone(f.surface)
 local sr,ar,ni=f.sourceReads,f.assetReads,f.images
 f:map();eq(f.sourceReads,sr,'Warm draws do not decode source cells');eq(f.assetReads,ar);eq(f.images,ni)
 local actor={px=16,py=96,sprite={frameWidth=32,frameHeight=64,anchorX=16,anchorY=64}}
 f:actor(actor)
 eq(count(f.surface)>0,true,'An actor in the original legal right aisle is behind the native bed edge')
 for key,asset in pairs(f.surface)do eq(mapSurface[key],asset,'Only actual native-alpha pixels cover a rear actor')end
 eq(f:ink(20,100),nil,'Transparent exterior preserves a neighbouring actor')
 actor.px=0;actor.py=128
 f:actor(actor);eq(next(f.surface),nil,'The original south inspection square remains in front of the bed')
 actor.spriteYOffset=-32;f:actor(actor);eq(next(f.surface),nil,'Jump height cannot change physical furniture depth')
 f.failHash=rows[1].footHash;f.revision=f.revision+1
 local assetReads=f.assetReads;f:map();eq(next(f.surface),nil,'A changed source foot fails closed')
 eq(f.assetReads,assetReads,'Source foot is verified before artwork is opened')
 f.failHash=nil;f.revision=f.revision+1;f:map();eq(count(f.surface),522)
 f:clear(0,6);f:map();eq(next(f.surface),nil,'Changing the original bed block removes the complete foreground')
 def.blocks[math.floor(6/2)*def.width+1]=20;f:map();eq(count(f.surface),522)
 for i,value in ipairs(original)do eq(def.blocks[i],value,'Furniture rendering never edits source blocks')end
end
local sample=rows[1]
for _,field in ipairs({'map','tileset','sourceHash','footHash','role'})do
 local bad=clone(sample);bad[field]='unchecked';eq(f:reject(bad),false,'A different finite source identity is rejected')
end
for _,field in ipairs({'id','quadrant','anchorX','anchorY','footId','footQuadrant','footX','footY','frontY'})do
 local bad=clone(sample);bad[field]=99;eq(f:reject(bad),false,'A changed bed anchor or physical front is rejected')
end
local bad=clone(sample);bad.x=2;eq(f:reject(bad),false,'The foreground cannot escape its right cell')
bad=clone(sample);bad.y=5;eq(f:reject(bad),false,'The foreground cannot escape its upper cell')
bad=clone(sample);bad.game='red';eq(f:reject(bad),false,'The bed scope is G/S/C only')
local badContext=clone(f.ctx)
badContext.furnitureRows=rows
badContext.original=function()
 return{getDimensions=function()return 16,16 end,getPixel=function()return 1,1,1,1 end,
        ink=function()return true end}
end
local Roofs=assert(loadfile(root..'/lib/roofs.lua'))()
local invalidArt=Roofs.new(badContext);f.surface={}
invalidArt:map(f.world,f.def,0,0,1)
eq(next(f.surface),nil,'Opaque pixels outside the actual complete bed silhouette envelope fail closed')
invalidArt:dispose()
f.roofs:dispose();eq(f.releases,f.images,'All native textures release on unload')
print('roofs_celadon_bed_test: '..checks..' checks')
