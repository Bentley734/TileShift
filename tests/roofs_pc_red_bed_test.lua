local root=assert(arg[1])
local Fixture=assert(loadfile(root..'/tests/furniture_fixture.lua'))()
local catalog=assert(loadfile(root..'/lib/johto_furniture.lua'))()
local rows={};for _,r in ipairs(catalog)do if r.furniture=='pokecenter_upper_pc'or r.furniture=='red_house_bed'then rows[#rows+1]=r end end
local checks=0
local function eq(a,b,why)checks=checks+1;assert(a==b,why or(tostring(a)..' ~= '..tostring(b)))end
local function clone(r)local out={};for k,v in pairs(r)do out[k]=v end;return out end
eq(#rows,84)
local f=Fixture.new(root,rows);eq(f.sourceReads,0);eq(f.assetReads,0)
for _,game in ipairs({'gold','silver','crystal'})do
 for _,map in ipairs({'POKECENTER_2F','CELADON_POKECENTER_2F_BETA','REDS_HOUSE_2F'})do
  f:select(game,map);f:map()
  if map=='REDS_HOUSE_2F'then
   eq(f:ink(8,95)~=nil,true,'full native2px upper bed cap survives')
   eq(f:ink(20,102)~=nil,true,'all8 native extension columns survive')
   eq(f:ink(24,102),nil,'genuine exterior alpha leaves sidefloor clear')
   local actor={px=16,py=96,sprite={frameWidth=16,frameHeight=32,anchorX=8,anchorY=32}}
   f:actor(actor);eq(f:ink(20,102)~=nil,true,'source-legal sidefloor actor is behind full domestic bed')
   actor.py=128;actor.sprite.frameHeight=64;actor.sprite.anchorY=64;f:actor(actor)
   eq(next(f.surface),nil,'physical feet beyond original blockedfootprint remain in front')
  else
   eq(f:ink(40,20)~=nil,true,'complete PC cap/upper monitor is preserved')
   local actor={px=32,py=16,sprite={frameWidth=16,frameHeight=32,anchorX=8,anchorY=32}}
   f:actor(actor);eq(f:ink(40,20)~=nil,true,'walkable source upper cell2,1 is behind complete PC')
   actor.py=48;actor.sprite.frameHeight=64;actor.sprite.anchorY=64;f:actor(actor)
   eq(next(f.surface),nil,'source-legal menu front2,3 feet60 remains in front')
   actor.spriteYOffset=-24;f:actor(actor);eq(next(f.surface),nil,'jump height does not change PC depth')
  end
 end
end
f:select('crystal','POKECENTER_2F');f:map();local sr,ar,ni=f.sourceReads,f.assetReads,f.images
for i=1,100 do f:map()end
eq(f.sourceReads,sr);eq(f.assetReads,ar);eq(f.images,ni,'warm PC frames do not open or allocate artwork')
f:clear(2,2);f:map();eq(next(f.surface),nil,'removed PC anchor clears old foreground immediately')
f:clear(2,2,50);f:map();eq(f:ink(40,20)~=nil,true);eq(f.images,ni)
sr,ar=f.sourceReads,f.assetReads;f.world.daytime='DARK';f:map();eq(next(f.surface),nil);eq(f.sourceReads,sr)
f.world.daytime='DAY';f.active=false;f:map();eq(next(f.surface),nil);eq(f.sourceReads,sr)
f.active=true;f.valid=false;f.revision=2;f:map();eq(next(f.surface),nil);eq(f.assetReads,ar,'source mismatch fails before image lookup')
f.valid=true;f.revision=3;f:map();eq(f:ink(40,20)~=nil,true)
for _,kind in ipairs({'pokecenter_upper_pc','red_house_bed'})do
 local original;for _,r in ipairs(rows)do if r.game=='crystal'and r.furniture==kind then original=r;break end end
 for _,field in ipairs({'id','quadrant','anchorX','anchorY','frontY','sourceCollision'})do
  local r=clone(original);r[field]=r[field]+1;eq(f:reject(r),false,'source-specific PC/bed guard rejects '..field)
 end
 for _,field in ipairs({'map','tileset','sourceHash','role'})do local r=clone(original);r[field]='invalid';eq(f:reject(r),false,'invalid source guard rejected')end
 local r=clone(original);r.x=30;eq(f:reject(r),false)
end
local releases=f.images;f.roofs:dispose();eq(f.releases,releases);f:map();eq(next(f.surface),nil);f.roofs:dispose();eq(f.releases,releases)
print('roofs_pc_red_bed_test: '..checks..' checks')
