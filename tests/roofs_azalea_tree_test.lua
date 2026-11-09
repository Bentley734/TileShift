local root=assert(arg[1])
local Fixture=assert(loadfile(root..'/tests/furniture_fixture.lua'))()
local native=assert(loadfile(root..'/tests/azalea_tree_native_alpha.lua'))()
local all=assert(loadfile(root..'/lib/johto_furniture.lua'))()
local rows={};for _,r in ipairs(all)do if r.furniture=='azalea_gym_tree'then rows[#rows+1]=r end end
local checks=0
local function eq(a,b,why)checks=checks+1;assert(a==b,why or(tostring(a)..' ~= '..tostring(b)))end
local phase,calls=1,0;local images={}
local function frames(row)
 calls=calls+1;local part=(row.y-5)*2+row.x-4
 if images[part]then return images[part]end
 local result={}
 for i,z in ipairs(native.phases[part+1])do
  local im={path=z.path,getDimensions=function()return 16,16 end}
  function im.ink(x,y)return z.mask:sub(y*16+x+1,y*16+x+1)=='1'end
  function im:getPixel(x,y)return 1,1,1,self.ink(x,y)and 1 or 0 end
  result[i]=im
 end
 images[part]=result;return result
end
eq(#rows,12)
local f=Fixture.new(root,rows,native,{treeFrames=frames,treePhase=function()return phase end})
for _,game in ipairs({'gold','silver','crystal'})do
 f:select(game,'AZALEA_GYM')
 for wind=1,4 do
  phase=wind;f:map();local pixels=0;for _ in pairs(f.surface)do pixels=pixels+1 end
  local expected=0;for _,parts in ipairs(native.phases)do local _,n=parts[wind].mask:gsub('1','');expected=expected+n end
  eq(pixels,expected,'every complete selected-tree pixel is moved north16')
  for y=112,127 do for x=64,95 do eq(f:ink(x,y),nil,'old walking-row tree artwork is cleared')end end
  f:actor({px=80,py=96});eq(next(f.surface),nil,'east corridor row6 stays in front')
  f:actor({px=80,py=112});eq(next(f.surface),nil,'Bugsy and east corridor row7 stay fully in front')
  f:actor({px=80,py=80});eq(next(f.surface)~=nil,true,'north approach stays behind the canopy')
 end
end
f:select('crystal','AZALEA_GYM');f:map();local sr,ar,textureCount,frameCalls=f.sourceReads,f.assetReads,f.images,calls
for i=1,100 do phase=i%4+1;f:map();f:actor({px=80,py=96})end
eq(f.sourceReads,sr);eq(f.assetReads,ar);eq(f.images,textureCount);eq(calls,frameCalls,'wind draws reuse cached complete sprite frames')
f:clear(0,0,99);f:map();eq(next(f.surface)~=nil,true,'unrelated neighboring block does not hide the tree')
f:clear(4,6);f:map();eq(next(f.surface),nil,'changed source tree anchor removes complete foreground')
f:clear(4,6,33);f:map();eq(next(f.surface)~=nil,true)
f.failHash='ff97f81649dcf1055be0ebeef7baf65bfdf5a231a0166e7f3d1d2a9f81fc3fb9';f.revision=f.revision+1;f:map();eq(next(f.surface),nil,'a changed non-anchor glyph rejects the whole source tree')
f.failHash=nil;f.revision=f.revision+1;f:map();eq(next(f.surface)~=nil,true)
f.active=false;f:map();eq(next(f.surface),nil,'Original style is untouched');f.active=true
local original=rows[1]
for _,field in ipairs({'id','quadrant','anchorX','anchorY','frontY','sourceCollision'})do local r={};for k,v in pairs(original)do r[k]=v end;r[field]=r[field]+1;eq(f:reject(r),false,'reject changed '..field)end
for _,xy in ipairs({{3,5},{6,5},{4,4},{5,7}})do local r={};for k,v in pairs(original)do r[k]=v end;r.x,r.y=xy[1],xy[2];eq(f:reject(r),false,'reject out-of-envelope placement')end
f.roofs:dispose();eq(f.releases,textureCount);f:map();eq(next(f.surface),nil)
print('roofs_azalea_tree_test: '..checks..' checks')
