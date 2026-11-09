local root=assert(arg[1])
local Fixture=assert(loadfile(root..'/tests/furniture_fixture.lua'))()
local native=assert(loadfile(root..'/tests/native_cave_ladder_alpha.lua'))()
local catalog=assert(loadfile(root..'/lib/johto_furniture.lua'))()
local rows={};for _,r in ipairs(catalog)do if r.furniture=='union_cave_ladder'then rows[#rows+1]=r end end
local checks=0
local function eq(a,b,why)checks=checks+1;assert(a==b,why or(tostring(a)..' ~= '..tostring(b)))end
local function clone(r)local out={};for k,v in pairs(r)do out[k]=v end;return out end
eq(#rows,30)
local f=Fixture.new(root,rows,native)
for _,game in ipairs({'gold','silver','crystal'})do
 for _,map in ipairs({'UNION_CAVE_B1F','UNION_CAVE_B2F','SLOWPOKE_WELL_B1F','SLOWPOKE_WELL_B2F'})do
  f:select(game,map);f:map()
  local anchors=map=='UNION_CAVE_B1F'and 2 or 1
  local pixels=0;for _ in pairs(f.surface)do pixels=pixels+1 end
  eq(pixels,anchors*233,'every complete native ladder pixel survives at1:1')
  local sr,ar,images=f.sourceReads,f.assetReads,f.images
  for n=1,100 do f:map()end
  eq(f.sourceReads,sr,'warm map reads no source data');eq(f.assetReads,ar,'warm map reads no files');eq(f.images,images,'warm map allocates no images')
  for _,r in ipairs(rows)do if r.game==game and r.map==map and r.y==r.anchorY then
   f:actor({px=r.anchorX*16,py=r.anchorY*16,sprite={frameWidth=16,frameHeight=16,anchorX=8,anchorY=16}})
   eq(next(f.surface)~=nil,true,'rear approach has normal ladder foreground')
   f:actor({px=r.anchorX*16,py=(r.anchorY+1)*16,sprite={frameWidth=16,frameHeight=32,anchorX=8,anchorY=32}})
   eq(next(f.surface),nil,'front approach is fully in front of the complete ladder')
  end end
 end
end
-- Same source block contains the upperQ1 and warpQ3. Wrong imported upper
-- glyph must remove both pieces even when the lower warp glyph still matches.
for _,hash in ipairs({'9bd2df64df770d82c85fa1539199ff530962ccb1869ced60e2f520f4607d59de','48c0a551f12607b1c1d59c1c8ab67046e07d45c9a18a93da2931d87d6b4aef8f'})do
 local map=hash:sub(1,4)=='9bd2'and'SLOWPOKE_WELL_B2F'or'SLOWPOKE_WELL_B1F'
 f:select('crystal',map);f:map();local ar=f.assetReads
 f.failHash=hash;f.revision=f.revision+1;f:map();eq(next(f.surface),nil,'changed upper glyph hides complete ladder');eq(f.assetReads,ar,'reject before artwork access')
 f.failHash=nil;f.revision=f.revision+1;f:map();eq(next(f.surface)~=nil,true)
end
local original;for _,r in ipairs(rows)do if r.game=='crystal'and r.map=='SLOWPOKE_WELL_B1F'then original=r;break end end
for _,field in ipairs({'id','quadrant','anchorX','anchorY','frontY','sourceCollision','upperX','upperY','upperId','upperQuadrant','upperCollision'})do
 local r=clone(original);r[field]=r[field]+1;eq(f:reject(r),false,'reject altered source guard '..field)
end
for _,field in ipairs({'map','tileset','sourceHash','upperHash','role'})do
 local r=clone(original);r[field]='invalid';eq(f:reject(r),false,'reject altered source guard '..field)
end
for _,field in ipairs({'upperX','upperY'})do
 local r=clone(original);r[field]=nil;eq(f:reject(r),false,'missing explicit upper coordinate must reject at startup')
end
f.active=false;f:map();eq(next(f.surface),nil,'Original style remains untouched');f.active=true
local images=f.images;f.roofs:dispose();eq(f.releases,images);f:map();eq(next(f.surface),nil)
print('roofs_native_cave_ladders_test: '..checks..' checks')
