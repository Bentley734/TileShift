local root=assert(arg[1])
local Fixture=assert(loadfile(root..'/tests/furniture_fixture.lua'))()
local catalog=assert(loadfile(root..'/lib/johto_furniture.lua'))()
local rows,anchors,seen={},{},{}
for _,r in ipairs(catalog)do if r.furniture=='ship_bed'then
 rows[#rows+1]=r
 local key=r.game..'/'..r.map..'/'..r.anchorX..':'..r.anchorY
 if not seen[key]then seen[key]=true;anchors[#anchors+1]=r end
end end
local checks=0
local function eq(a,b,why)checks=checks+1;assert(a==b,why or(tostring(a)..' ~= '..tostring(b)))end
local function clone(r)local out={};for k,v in pairs(r)do out[k]=v end;return out end
local function count(t)local n=0;for _ in pairs(t)do n=n+1 end;return n end
local function targetCount(f,r)
 local n=0
 for y=r.anchorY*16+3,(r.anchorY+2)*16-1 do
  for x=r.anchorX*16-4,r.anchorX*16+15 do if f:ink(x,y)then n=n+1 end end
 end
 return n
end
eq(#rows,228);eq(#anchors,57)
local f=Fixture.new(root,rows);eq(f.sourceReads,0);eq(f.assetReads,0)
local beds={FAST_SHIP_B1F=8,FAST_SHIP_CABINS_NNW_NNE_NE=3,FAST_SHIP_CABINS_SE_SSE_CAPTAINS_CABIN=4,FAST_SHIP_CABINS_SW_SSW_NW=4}
local guards={FAST_SHIP_B1F=8,FAST_SHIP_CABINS_NNW_NNE_NE=4,FAST_SHIP_CABINS_SE_SSE_CAPTAINS_CABIN=6,FAST_SHIP_CABINS_SW_SSW_NW=5}
for _,game in ipairs({'gold','silver','crystal'})do
 for map,n in pairs(beds)do
  f:select(game,map);local originalBlocks=f.def.blocks;f:map()
  eq(count(f.surface),n*522,'every full20x29 bed native pixel survives without omitted columns')
  local sr,ar,ni=f.sourceReads,f.assetReads,f.images
  local reads=0
  f.def.blocks=setmetatable({},{__index=function(_,i)reads=reads+1;return originalBlocks[i]end})
  for i=1,100 do f:map()end
  eq(reads,100*guards[map],'warm cache reads only curated distinct source blocks (at most8)')
  eq(f.sourceReads,sr);eq(f.assetReads,ar);eq(f.images,ni,'warm ship draws never read imports/assets or allocate images')
  f.def.blocks=originalBlocks
 end
end
for _,r in ipairs(anchors)do
 f:select(r.game,r.map)
 local actor={px=(r.anchorX-1)*16,py=r.anchorY*16,sprite={frameWidth=16,frameHeight=32,anchorX=8,anchorY=32}}
 f:actor(actor);eq(targetCount(f,r)>0,true,'labeled opaque boundary actor behind lefthead respects native4px extension')
 actor.py=(r.anchorY+1)*16;f:actor(actor);eq(targetCount(f,r)>0,true,'legal leftfoot depth remains consistent with other blocked-footprint beds')
 actor.py=(r.anchorY+2)*16;actor.sprite.frameHeight=64;actor.sprite.anchorY=64
 f:actor(actor);eq(targetCount(f,r),0,'labeled southern physical boundary is in front independent of sprite height')
 actor.spriteYOffset=-24;f:actor(actor);eq(targetCount(f,r),0,'jump offset cannot reverse physical bed depth')
end
local rest
for _,r in ipairs(anchors)do if r.game=='crystal'and r.map=='FAST_SHIP_CABINS_SW_SSW_NW'and r.anchorX==7 and r.anchorY==1 then rest=r;break end end
assert(rest);eq(rest.frontY,48,'source-legal side BG interaction does not invent a southern-front threshold')
f:select(rest.game,rest.map);f:map()
local footIndex=math.floor(rest.footY/2)*f.def.width+math.floor(rest.footX/2)+1
local originalFoot=f.def.blocks[footIndex];f.def.blocks[footIndex]=0;f:map()
eq(f:ink(rest.anchorX*16-2,rest.anchorY*16+8),nil,'changed separate footblock removes the entire cached bed extension')
f.def.blocks[footIndex]=originalFoot;f:map();eq(count(f.surface),4*522,'restoring footblock restores every complete native bed')
local ar=f.assetReads;f.failHash=rest.footHash;f.revision=f.revision+1;f:map()
eq(next(f.surface),nil,'changed native foot fingerprint fails closed even with unchanged head')
eq(f.assetReads,ar,'foot guard runs before asset decode')
f.failHash=nil;f.revision=f.revision+1;f:map();eq(count(f.surface),4*522)
local sr=f.sourceReads;f.world.daytime='DARK';f:map();eq(next(f.surface),nil);eq(f.sourceReads,sr)
f.world.daytime='DAY';f.active=false;f:map();eq(next(f.surface),nil);eq(f.sourceReads,sr)
f.active=true;f:map();eq(count(f.surface),4*522)
for _,field in ipairs({'id','quadrant','anchorX','anchorY','frontY','sourceCollision','footX','footY','footId','footQuadrant'})do
 local r=clone(rest);r[field]=r[field]+1;eq(f:reject(r),false,'literal ship source guard rejects '..field)
end
for _,field in ipairs({'map','tileset','sourceHash','footHash','role'})do local r=clone(rest);r[field]='invalid';eq(f:reject(r),false,'invalid whole-bed guard rejected')end
local wrong=clone(rest);wrong.x=rest.anchorX-2;eq(f:reject(wrong),false,'source envelope cannot spread into another object')
local arbitrary=clone(rest);arbitrary.anchorX=1;arbitrary.anchorY=1;arbitrary.x=0;arbitrary.y=1;eq(f:reject(arbitrary),false,'unreviewed bed position cannot reuse a valid glyph')
local releases=f.images;f.roofs:dispose();eq(f.releases,releases);f:map();eq(next(f.surface),nil);f.roofs:dispose();eq(f.releases,releases)
print('roofs_ship_beds_test: '..checks..' checks')
