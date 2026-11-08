local root=assert(arg[1])
local Fixture=assert(loadfile(root..'/tests/furniture_fixture.lua'))()
local native=assert(loadfile(root..'/tests/oak_desk_native_alpha.lua'))()
local catalog=assert(loadfile(root..'/lib/johto_furniture.lua'))()
local rows={};for _,r in ipairs(catalog)do if r.furniture=='mr_pokemon_pc'then rows[#rows+1]=r end end
local checks=0
local function eq(a,b,why)checks=checks+1;assert(a==b,why or(tostring(a)..' ~= '..tostring(b)))end
local function clone(r)local out={};for k,v in pairs(r)do out[k]=v end;return out end
eq(#rows,12)
local f=Fixture.new(root,rows,native);eq(f.sourceReads,0);eq(f.assetReads,0)
for _,game in ipairs({'gold','silver','crystal'})do
 f:select(game,'MR_POKEMONS_HOUSE');f:map()
 local nativePixels=0
 for _,entry in pairs(native.assets)do for i=1,#entry.mask do if entry.mask:sub(i,i)=='1'then nativePixels=nativePixels+1 end end end
 local pixels=0;for _ in pairs(f.surface)do pixels=pixels+1 end
 eq(nativePixels,687);eq(pixels,nativePixels,'every complete native PC pixel survives at1:1')
 eq(f:ink(96,48),nil,'native padding stays transparent over the walking floor')
 eq(f:ink(96,79),nil,'left exterior corner stays transparent')
 for _,x in ipairs({96,112})do
  local actor={px=x,py=48,sprite={frameWidth=16,frameHeight=16,anchorX=8,anchorY=16}}
  f:actor(actor)
  eq(next(f.surface)~=nil,true,'reachable north approach is behind the complete workstation')
  eq(f:ink(x,48),nil,'transparent corners leave a rear actor visible')
  actor.py=80;actor.sprite.frameHeight=48;actor.sprite.anchorY=48;f:actor(actor)
  eq(next(f.surface),nil,'Oak source standing row5 is fully in front of the desk')
  actor.spriteYOffset=-20;f:actor(actor)
  eq(next(f.surface),nil,'jump height keeps physical feet in front of the desk')
 end
end
f:select('crystal','MR_POKEMONS_HOUSE');f:map()
local sr,ar,images=f.sourceReads,f.assetReads,f.images
for i=1,100 do f:map();f:actor({px=96,py=48})end
eq(f.sourceReads,sr);eq(f.assetReads,ar);eq(f.images,images,'warm foreground reuses cached assets/textures')
f:clear(6,4);f:map();eq(next(f.surface),nil,'changed source anchor removes the desk foreground')
f:clear(6,4,40);f:map();eq(next(f.surface)~=nil,true);eq(f.images,images)
sr,ar=f.sourceReads,f.assetReads
f.valid=false;f.revision=2;f:map();eq(next(f.surface),nil);eq(f.assetReads,ar,'source mismatch fails before artwork access')
f.valid=true;f.revision=3;f:map();eq(next(f.surface)~=nil,true)
f.active=false;f:map();eq(next(f.surface),nil,'Original style has no replacement foreground')
f.active=true
local original;for _,row in ipairs(rows)do if row.game=='crystal'then original=row;break end end
for _,field in ipairs({'id','quadrant','anchorX','anchorY','frontY','sourceCollision'})do
 local r=clone(original);r[field]=r[field]+1;eq(f:reject(r),false,'bounded source guard rejects '..field)
end
for _,field in ipairs({'map','tileset','sourceHash','role'})do
 local r=clone(original);r[field]='invalid';eq(f:reject(r),false,'bounded source guard rejects '..field)
end
for _,xy in ipairs({{5,3},{8,4},{6,2},{7,5}})do
 local r=clone(original);r.x,r.y=xy[1],xy[2];eq(f:reject(r),false,'workstation cannot escape reviewed2x2 envelope')
end
f.roofs:dispose();eq(f.releases,images);f:map();eq(next(f.surface),nil)
print('roofs_mr_pokemon_pc_test: '..checks..' checks')
