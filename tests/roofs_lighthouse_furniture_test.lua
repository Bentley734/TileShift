local root=assert(arg[1])
local Roofs=assert(loadfile(root..'/lib/roofs.lua'))()
local Mapping=assert(loadfile(root..'/lib/mapping.lua'))()
local checks=0
local function eq(a,b,why)checks=checks+1;assert(a==b,why or(tostring(a)..' ~= '..tostring(b)))end
local function clone(v)if type(v)~='table'then return v end;local out={};for k,a in pairs(v)do out[k]=clone(a)end;return out end
local function hash(c)return string.rep(c,64)end
local bedHash={gold='c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150',silver='c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150',crystal='174172f8f6fb3eac98ca33e52ae4b8b4e8912eddb47077444b3435fb520c16e3'}
local tableHash={gold='f1f1a9a311726cb727513dc98898528e04138e2ae5c26afc42bf176cad9b4d4a',silver='f1f1a9a311726cb727513dc98898528e04138e2ae5c26afc42bf176cad9b4d4a',crystal='cd6d3daa76f4aa557f43655289dd483fee61c29a4341e9c9af1f1385c1c559ca'}
local function row(game,feature,x,y)
 local bed=feature=='bed'
 return {game=game,style='gen3',kind='third_party',map='OLIVINE_LIGHTHOUSE_6F',tileset='TILESET_LIGHTHOUSE',
 furniture='lighthouse_'..feature,anchorX=bed and 11 or 6,anchorY=bed and 6 or 9,id=bed and 54 or 6,quadrant=bed and 1 or 2,
 sourceHash=(bed and bedHash or tableHash)[game],sourceCollision=7,
 sourceFiles={image=hash('1'),metadata=hash('2'),maps=hash('3')},
 role='olivine_crystaldust_native_'..(bed and'medical_bed'or'table'),status='reviewed',evidence='Complete native-scale bounded lighthouse furniture.',
 x=x,y=y,frontY=bed and 128 or 192,asset='assets/third_party/lighthouse-'..feature..'-'..x..'-'..y..'.png',assetFileHash=hash('a'),
 credit='Synthetic native-scale bounded lighthouse fixture',sourceUrl='https://example.com/lighthouse'}
end
local rows={}
for _,game in ipairs({'gold','silver','crystal'})do
 for y=6,7 do for x=10,11 do rows[#rows+1]=row(game,'bed',x,y)end end
 for y=8,11 do for x=6,7 do rows[#rows+1]=row(game,'table',x,y)end end
end
local pixels,surface={},{}
local sourceReads,assetReads,newImages,releases=0,0,0,0
local function ink(x,y)return surface[y*1024+x]or'actor-or-ground'end
local function nativeInk(feature,x,y)
 if feature=='bed'then
  if x>=172 and x<192 and y>=99 and y<128 and not(x==172 and y==99)then return'complete-bed'end
 elseif x>=96 and x<128 and y>=141 and y<192 then
  if y<184 or(x>=98 and x<102)or(x>=122 and x<126)then return'complete-table'end
 end
end
local G={push=function()end,pop=function()end,setShader=function()end,setColor=function()end}
function G.newImage(data)newImages=newImages+1;return{data=data,setFilter=function()end,release=function()releases=releases+1 end}end
function G.newQuad()return{setViewport=function(s,x,y,w,h)s.x,s.y,s.w,s.h=x,y,w,h end,release=function()end}end
function G.draw(texture,q,x,y)
 local sx,sy,w,h
 if type(q)=='table'then sx,sy,w,h=q.x,q.y,q.w,q.h else x,y=q,x;sx,sy,w,h=0,0,16,16 end
 for yy=0,h-1 do for xx=0,w-1 do local c=texture.data.ink(sx+xx,sy+yy);if c then surface[(y+yy)*1024+x+xx]=c end end end
end
local function picture(r)
 if pixels[r.asset]then return pixels[r.asset]end
 local feature=r.furniture=='lighthouse_bed'and'bed'or'table'
 local im={getDimensions=function()return 16,16 end,ink=function(x,y)return nativeInk(feature,r.x*16+x,r.y*16+y)end}
 function im:getPixel(x,y)return 1,1,1,self.ink(x,y)and 1 or 0 end
 pixels[r.asset]=im;return im
end
local game,active,revision,valid='crystal',true,1,true
local def={id='OLIVINE_LIGHTHOUSE_6F',tileset='TILESET_LIGHTHOUSE',width=10,height=9,blocks={}}
for i=1,90 do def.blocks[i]=1 end
local bedAnchor,tableAnchor=36,44;def.blocks[bedAnchor]=54;def.blocks[tableAnchor]=6
local originalBlocks=def.blocks
local world={camera={x=0,y=0},viewW=320,viewH=288,daytime='DAY'}
local ctx={graphics=G,rows={},furnitureRows=rows,version=function()return game end,active=function()return active end,revision=function()return revision end,
 validate=function(r)eq(r.x,r.anchorX,'source validator uses checked furniture anchor');eq(r.y,r.anchorY);return Mapping.validate(r)end,
 donor={cell=function(_,ref)
  sourceReads=sourceReads+1;local bed=ref.id==54
  eq(ref.id==54 or ref.id==6,true);eq(ref.quadrant,bed and 1 or 2);eq(ref.hashOnly,true);eq(ref.monochrome,true)
  eq(ref.hash,(bed and bedHash or tableHash)[game]);eq(ref.map,def);return valid and{}or nil,'source changed'
 end},original=function(path,expected)
  assetReads=assetReads+1;eq(expected,hash('a'));for _,r in ipairs(rows)do if r.asset==path then return picture(r)end end;error('unexpected asset')
 end,warn=function()end}
local roofs=Roofs.new(ctx);eq(sourceReads,0);eq(assetReads,0)
for _,cart in ipairs({'gold','silver','crystal'})do
 game=cart;surface={};roofs:map(world,def,0,0,1)
 for y=96,127 do for x=160,191 do eq(ink(x,y),nativeInk('bed',x,y)or'actor-or-ground','native bed extent and exterior transparency survive')end end
 for y=128,191 do for x=96,127 do eq(ink(x,y),nativeInk('table',x,y)or'actor-or-ground','full native table includes its3px cap and feet')end end
end
eq(ink(172,99),'actor-or-ground');eq(ink(110,190),'actor-or-ground','native gap between table feet preserves floor')
local sr,ar,ni=sourceReads,assetReads,newImages
for i=1,100 do roofs:map(world,def,0,0,1)end
eq(sourceReads,sr);eq(assetReads,ar);eq(newImages,ni,'warm draws never read/allocate geometry or art')
def.blocks[1]=2;roofs:map(world,def,0,0,1);eq(sourceReads,sr,'only two bounded anchors invalidate this room')
local actor={px=160,py=96,sprite={frameWidth=16,frameHeight=32,anchorX=8,anchorY=32}}
surface={};roofs:actor({def=def},actor,0,0,1,false,0,world)
eq(ink(173,105),'complete-bed','source-legal left bedside10,6 respects the4px complete-bed extension')
eq(ink(171,105),'actor-or-ground','true bed exterior never erases an actor')
actor.px=176;actor.py=128;actor.sprite.frameWidth=32;actor.sprite.anchorX=16;actor.sprite.frameHeight=64;actor.sprite.anchorY=64
surface={};roofs:actor({def=def},actor,0,0,1,false,0,world)
eq(next(surface),nil,'legal south bed inspection/front cell11,8 (feet140) stays in front')
actor.spriteYOffset=-32;surface={};roofs:actor({def=def},actor,0,0,1,false,0,world);eq(next(surface),nil,'jump height does not change physical depth')
actor.spriteYOffset=0;actor.px=80;actor.py=144
surface={};roofs:actor({def=def},actor,0,0,1,false,0,world)
eq(ink(99,150),'complete-table','source-legal side5,9 with a wide actor is behind the complete table')
actor.px=128;actor.py=192;surface={};roofs:actor({def=def},actor,0,0,1,false,0,world)
eq(next(surface),nil,'legal southern aisle8,12 (feet204) stays in front of table')
actor.px=128;actor.py=128;actor.sprite.frameWidth=16;actor.sprite.anchorX=8;actor.sprite.frameHeight=32;actor.sprite.anchorY=32
surface={};roofs:actor({def=def},actor,0,0,1,false,0,world);eq(next(surface),nil,'actual Jasmine8,8 is neither shifted nor spuriously overpainted')
def.blocks[bedAnchor]=1;surface={};roofs:map(world,def,0,0,1);eq(ink(173,105),'actor-or-ground');eq(ink(110,145),'complete-table','changing bed anchor leaves independent table active')
def.blocks[tableAnchor]=1;surface={};roofs:map(world,def,0,0,1);eq(next(surface),nil,'both cleared anchors remove all cached furniture')
def.blocks[bedAnchor]=54;def.blocks[tableAnchor]=6;surface={};roofs:map(world,def,0,0,1);eq(ink(173,105),'complete-bed');eq(newImages,ni,'restoring source anchors reuses textures')
sr,ar=sourceReads,assetReads;world.daytime='DARK';surface={};roofs:map(world,def,0,0,1);eq(next(surface),nil);eq(sourceReads,sr)
world.daytime='DAY';active=false;roofs:map(world,def,0,0,1);eq(next(surface),nil);eq(sourceReads,sr,'Original/ownership loss performs no artwork IO')
active=true;valid=false;revision=2;roofs:map(world,def,0,0,1);eq(next(surface),nil);eq(assetReads,ar,'source mismatch fails before opening art')
valid=true;revision=3;roofs:map(world,def,0,0,1);eq(ink(173,105),'complete-bed')
eq(def.blocks,originalBlocks);eq(def.blocks[bedAnchor],54);eq(def.blocks[tableAnchor],6,'all source layout writes remain outside renderer')
local released=newImages;roofs:dispose();eq(releases,released);surface={};roofs:map(world,def,0,0,1);eq(next(surface),nil);roofs:dispose();eq(releases,released,'unload is idempotent')
local function rejected(feature,change)
 local r=row('crystal',feature,feature=='bed'and 10 or 6,feature=='bed'and 6 or 8);change(r);local bad=clone(ctx);bad.furnitureRows={r}
 eq(pcall(Roofs.new,bad),false,'invalid finite lighthouse contract is rejected')
end
for _,feature in ipairs({'bed','table'})do
 rejected(feature,function(r)r.map='OTHER'end);rejected(feature,function(r)r.game='red'end)
 rejected(feature,function(r)r.tileset='TILESET_FOREST'end);rejected(feature,function(r)r.id=53 end)
 rejected(feature,function(r)r.quadrant=0 end);rejected(feature,function(r)r.anchorX=1 end)
 rejected(feature,function(r)r.anchorY=1 end);rejected(feature,function(r)r.sourceHash=hash('b')end)
 rejected(feature,function(r)r.sourceCollision=0 end);rejected(feature,function(r)r.x=0 end)
 rejected(feature,function(r)r.y=0 end);rejected(feature,function(r)r.frontY=400 end)
 rejected(feature,function(r)r.base={}end);rejected(feature,function(r)r.role='unchecked_furniture'end)
end
for _,feature in ipairs({'bed','table'})do
 local bad=clone(ctx);bad.furnitureRows={row('crystal',feature,feature=='bed'and 10 or 6,feature=='bed'and 6 or 8)}
 bad.original=function()return{getDimensions=function()return 16,16 end,getPixel=function()return 1,1,1,1 end}end
 local badArt=Roofs.new(bad);surface={};badArt:map(world,def,0,0,1);eq(next(surface),nil,'opaque pixels outside finite native bbox fail closed');badArt:dispose()
end
print('roofs_lighthouse_furniture_test: '..checks..' checks')
