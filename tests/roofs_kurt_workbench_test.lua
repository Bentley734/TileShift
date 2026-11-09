local root=assert(arg[1])
local Fixture=assert(loadfile(root..'/tests/furniture_fixture.lua'))()
local native=assert(loadfile(root..'/tests/kurt_workbench_native_alpha.lua'))()
local catalog=assert(loadfile(root..'/lib/johto_furniture.lua'))()
local rows={};for _,r in ipairs(catalog)do if r.furniture=='kurt_workbench'then rows[#rows+1]=r end end
local checks=0
local function eq(a,b,why)checks=checks+1;assert(a==b,why or(tostring(a)..' ~= '..tostring(b)))end
local function clone(r)local out={};for k,v in pairs(r)do out[k]=v end;return out end
eq(#rows,54)
local f=Fixture.new(root,rows,native)
local function select(game)
 f:select(game,'KURTS_HOUSE')
 local blocks=native.maps[game].KURTS_HOUSE.blocks
 for i,b in ipairs(blocks)do f.def.blocks[i]=b end
 f:map()
end
for _,game in ipairs({'gold','silver','crystal'})do
 select(game)
 local pixels=0;for _ in pairs(f.surface)do pixels=pixels+1 end
 eq(pixels,3497,'all native tools, pegboard and entire L hardware remain at1:1')
 for _,run in ipairs({{0,38,88},{15,58,88},{63,38,56}})do
  for y=run[2],run[3]-1 do eq(f:ink(192+run[1],y-16)~=nil,true,'complete native workbench side must remain continuous')end
 end
 eq(f:ink(206,-10)~=nil,true,'complete top frame above source room survives')
 eq(f:ink(205,-10),nil,'generic exterior wall stays transparent')
 eq(f:ink(216,23)~=nil,true,'native horizontal tabletop is solid under the tools')
 eq(f:ink(198,67)~=nil,true,'native lower return surface stays continuous above its base')
 eq(f:ink(192,48)~=nil,true,'continuous bottom-plane shaft fills the L return')
 eq(f:ink(224,48),nil,'independent native chair is excluded as a complete object')
 -- The authentic working Kurt at tile14,3 must remain in front of his bench.
 f:actor({px=14*16,py=3*16,sprite={frameWidth=16,frameHeight=16,anchorX=8,anchorY=16}})
 eq(next(f.surface),nil,'working Kurt head stays in front of the countertop')
 -- Crystal workshop Twin is immediately left of the return; no clipping.
 f:actor({px=11*16,py=4*16,sprite={frameWidth=16,frameHeight=16,anchorX=8,anchorY=16}})
 eq(next(f.surface),nil,'working Twin stays clear of the whole L return')
 f:actor({px=3*16,py=2*16});eq(next(f.surface),nil,'front-room Kurt state stays clear')
 f:actor({px=5*16,py=3*16});eq(next(f.surface),nil,'front-room Twin state stays clear')
 -- Genuine source rear approach remains behind the distinct return only.
 f:actor({px=12*16,py=3*16});eq(next(f.surface)~=nil,true,'return retains normal foreground depth')
end
select('crystal')
local sr,ar,images=f.sourceReads,f.assetReads,f.images
for i=1,100 do f:map();f:actor({px=14*16,py=3*16})end
eq(f.sourceReads,sr,'warm draws read no source cells')
eq(f.assetReads,ar,'warm draws read no files')
eq(f.images,images,'warm draws allocate no images')
-- Every distinct original source block of the L is watched, not just49.
for _,xy in ipairs({{12,1},{14,1},{12,2},{14,2},{12,4}})do
 select('crystal');local index=math.floor(xy[2]/2)*f.def.width+math.floor(xy[1]/2)+1
 local bid=f.def.blocks[index];local currentAr=f.assetReads;f:clear(xy[1],xy[2]);f:map()
 eq(next(f.surface),nil,'any changed original source L block removes entire hardware')
 eq(f.assetReads,currentAr,'changed source fails before reading art')
 f:clear(xy[1],xy[2],bid);f:map();eq(next(f.surface)~=nil,true)
end
select('crystal');f.failHash='09276ddd3411793b5c8a62ee283232872ba8587040987d2d77f5db775ccbac92';f.revision=f.revision+1;f:map()
eq(next(f.surface),nil,'wrong non-anchor source glyph removes complete workbench')
f.failHash=nil;f.revision=f.revision+1;f:map();eq(next(f.surface)~=nil,true)
f.active=false;f:map();eq(next(f.surface),nil,'Original style has no replacement foreground');f.active=true
local original;for _,r in ipairs(rows)do if r.game=='crystal'then original=r;break end end
for _,field in ipairs({'id','quadrant','anchorX','anchorY','frontY','sourceCollision'})do
 local r=clone(original);r[field]=r[field]+1;eq(f:reject(r),false,'reject changed '..field)
end
for _,field in ipairs({'map','tileset','sourceHash','role'})do
 local r=clone(original);r[field]='invalid';eq(f:reject(r),false,'reject changed '..field)
end
for _,xy in ipairs({{11,0},{16,0},{12,-2},{12,5}})do
 local r=clone(original);r.x,r.y=xy[1],xy[2];eq(f:reject(r),false,'workbench cannot escape its bounded source envelope')
end
f.roofs:dispose();eq(f.releases,images);f:map();eq(next(f.surface),nil)
print('roofs_kurt_workbench_test: '..checks..' checks')
