local root=assert(arg[1])
local Fixture=assert(loadfile(root..'/tests/furniture_fixture.lua'))()
local native=assert(loadfile(root..'/tests/department_counters_native_alpha.lua'))()
local catalog=assert(loadfile(root..'/lib/johto_furniture.lua'))()
local rows={};for _,r in ipairs(catalog)do if r.furniture=='department_counter'then rows[#rows+1]=r end end
local checks=0
local function eq(a,b,why)checks=checks+1;assert(a==b,why or(tostring(a)..' ~= '..tostring(b)))end
local function clone(r)local out={};for k,v in pairs(r)do out[k]=v end;return out end
eq(#rows,189)
local f=Fixture.new(root,rows,native)
local expected={GOLDENROD_DEPT_STORE_1F=1808,GOLDENROD_DEPT_STORE_2F=3528,GOLDENROD_DEPT_STORE_3F=1808,GOLDENROD_DEPT_STORE_4F=1576,GOLDENROD_DEPT_STORE_5F=3016}
local function select(game,name)
 f:select(game,name)
 for i,b in ipairs(native.maps[game][name].blocks)do f.def.blocks[i]=b end
 f:map()
end
for _,game in ipairs({'gold','silver','crystal'})do
 for name,count in pairs(expected)do
  select(game,name);local n=0;for _ in pairs(f.surface)do n=n+1 end
  eq(n,count,'every native cap, rim, side, front/base and complete glass pixel survives')
 end
 select(game,'GOLDENROD_DEPT_STORE_1F')
 eq(f:ink(152,14)~=nil,true,'complete rounded rear cap retained')
 eq(f:ink(152,47)~=nil,true,'complete green front foot retained')
 f:actor({px=160,py=16});eq(f:ink(166,27)~=nil,true,'native rim hides receptionist last shoe row')
 eq(f:ink(166,26),nil,'staff body remains clear above actual native rim')
 f:actor({px=160,py=48,sprite={frameWidth=32,frameHeight=32,anchorX=16,anchorY=32}})
 eq(next(f.surface),nil,'tall customer remains entirely in front of the counter')
 select(game,'GOLDENROD_DEPT_STORE_3F')
 f:actor({px=96,py=16});eq(f:ink(102,27)~=nil,true,'third-floor rim hides actual clerk shoe row')
 select(game,'GOLDENROD_DEPT_STORE_2F')
 f:actor({px=208,py=80,sprite={frameWidth=32,frameHeight=32,anchorX=16,anchorY=32}})
 eq(f:ink(213,78),nil,'upper bar stays behind inside staff head')
 f:actor({px=208,py=96});eq(f:ink(213,107)~=nil,true,'whole lower rear rim has its own lower front depth')
 select(game,'GOLDENROD_DEPT_STORE_4F')
 eq(f:ink(200,95)~=nil,true,'isolated return has the authentic closed610 foot')
 f:actor({px=208,py=80});eq(f:ink(213,78),nil,'L-counter staff stays in front of upper face')
 select(game,'GOLDENROD_DEPT_STORE_5F')
 f:actor({px=112,py=80});eq(f:ink(118,91)~=nil,true,'lower booth rear rim retains correct cashier depth')
 eq(f:ink(118,90),nil,'cashier remains clear above the native rear rim')
 f:actor({px=112,py=112,sprite={frameWidth=32,frameHeight=32,anchorX=16,anchorY=32}})
 eq(next(f.surface),nil,'tall front customer cannot be covered by a blanket booth depth')
end
select('crystal','GOLDENROD_DEPT_STORE_2F')
local sourceReads,assetReads,images=f.sourceReads,f.assetReads,f.images
for _=1,100 do f:map();f:actor({px=208,py=80})end
eq(f.sourceReads,sourceReads,'warm foreground uses no source reads')
eq(f.assetReads,assetReads,'warm foreground uses no artwork reads')
eq(f.images,images,'warm foreground creates no textures')
for _,xy in ipairs({{12,3},{15,5},{13,6},{12,7}})do
 select('crystal','GOLDENROD_DEPT_STORE_2F')
 local index=math.floor(xy[2]/2)*f.def.width+math.floor(xy[1]/2)+1;local old=f.def.blocks[index]
 f:clear(xy[1],xy[2]);f:map();eq(next(f.surface),nil,'any altered counter source block removes the entire guarded foreground')
 f:clear(xy[1],xy[2],old);f:map();eq(next(f.surface)~=nil,true,'restored source restores native furniture')
end
select('crystal','GOLDENROD_DEPT_STORE_1F')
f.active=false;f:map();eq(next(f.surface),nil,'Original has no native counter foreground');f.active=true
local sample;for _,r in ipairs(rows)do if r.game=='crystal'then sample=r;break end end
for _,field in ipairs({'id','quadrant','anchorX','anchorY','frontY','sourceCollision'})do
 local r=clone(sample);r[field]=r[field]+1;eq(f:reject(r),false,'reject changed '..field)
end
for _,field in ipairs({'map','tileset','sourceHash','role','assetFileHash'})do
 local r=clone(sample);r[field]='invalid';eq(f:reject(r),false,'reject changed '..field)
end
local r=clone(sample);r.x=0;r.y=7;eq(f:reject(r),false,'no furniture outside the exact source counter footprint')
f.roofs:dispose();eq(f.releases,images);f:map();eq(next(f.surface),nil)
print('roofs_department_counters_test: '..checks..' checks')
