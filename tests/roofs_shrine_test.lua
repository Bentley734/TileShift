local root=assert(arg[1])
local Roofs=assert(loadfile(root..'/lib/roofs.lua'))()
local Mapping=assert(loadfile(root..'/lib/mapping.lua'))()
local checks=0
local function eq(a,b,why)checks=checks+1;assert(a==b,why or(tostring(a)..' ~= '..tostring(b)))end
local function clone(v)if type(v)~='table'then return v end;local out={};for k,a in pairs(v)do out[k]=clone(a)end;return out end
local function hash(c)return string.rep(c,64)end
local function row(game,x,y)
 return {game=game,style='gen3',kind='third_party',map='ILEX_FOREST',tileset='TILESET_FOREST',
 furniture='ilex_shrine',anchorX=8,anchorY=22,id=32,quadrant=0,
 sourceHash='7909c2afb5b8ad5d87ad24345244efdbd3798b6908ec2c32a9ddec904b498b42',
 sourceCollision=7,sourceFiles={image=hash('1'),metadata=hash('2'),maps=hash('3')},
 role='ilex_crystaldust_native_shrine',status='reviewed',evidence='Complete native24x34 shrine fixture at1:1.',
 x=x,y=y,frontY=380,asset='assets/third_party/shrine-'..x..'-'..y..'.png',assetFileHash=hash('a'),
 credit='Synthetic native-scale shrine fixture',sourceUrl='https://example.com/shrine'}
end
local rows={}
for _,game in ipairs({'gold','silver','crystal'})do
 for y=21,23 do for x=7,9 do rows[#rows+1]=row(game,x,y)end end
end
local pixels,surface={},{}
local draws,sourceReads,assetReads,newImages,releases=0,0,0,0,0
local function ink(x,y)return surface[y*1024+x]or'actor-or-ground'end
local function nativeInk(x,y)
 if x>=124 and x<148 and y>=350 and y<384 and not(x==127 and y==368)then return(x+y)%2==0 and'wood'or'roof'end
end
local G={push=function()end,pop=function()end,setShader=function()end,setColor=function()end}
function G.newImage(data)newImages=newImages+1;return{data=data,setFilter=function()end,release=function()releases=releases+1 end}end
function G.newQuad()return{setViewport=function(s,x,y,w,h)s.x,s.y,s.w,s.h=x,y,w,h end,release=function()end}end
function G.draw(texture,q,x,y)
 local sx,sy,w,h
 if type(q)=='table'then sx,sy,w,h=q.x,q.y,q.w,q.h else x,y=q,x;sx,sy,w,h=0,0,16,16 end
 draws=draws+1
 for yy=0,h-1 do for xx=0,w-1 do local color=texture.data.ink(sx+xx,sy+yy);if color then surface[(y+yy)*1024+x+xx]=color end end end
end
local function picture(r)
 if pixels[r.asset]then return pixels[r.asset]end
 local im={getDimensions=function()return 16,16 end,ink=function(x,y)return nativeInk(r.x*16+x,r.y*16+y)end}
 function im:getPixel(x,y)return 1,1,1,self.ink(x,y)and 1 or 0 end
 pixels[r.asset]=im;return im
end
local game,active,revision,valid='crystal',true,1,true
local warnings={}
local def={id='ILEX_FOREST',tileset='TILESET_FOREST',width=15,height=15,blocks={}}
for i=1,225 do def.blocks[i]=1 end
local anchor=11*15+4+1;def.blocks[anchor]=32
local originalBlocks=def.blocks
local world={camera={x=0,y=0},viewW=480,viewH=480,daytime='DAY'}
local ctx={graphics=G,rows={},furnitureRows=rows,version=function()return game end,active=function()return active end,revision=function()return revision end,
 validate=function(r)eq(r.x,8,'source validator uses real shrine anchor');eq(r.y,22);return Mapping.validate(r)end,
 donor={cell=function(_,ref)
  sourceReads=sourceReads+1;eq(ref.id,32);eq(ref.quadrant,0);eq(ref.hashOnly,true);eq(ref.monochrome,true)
  eq(ref.hash,rows[1].sourceHash);eq(ref.map,def);return valid and{}or nil,'source changed'
 end},original=function(path,expected)
  assetReads=assetReads+1;eq(expected,hash('a'));for _,r in ipairs(rows)do if r.asset==path then return picture(r)end end;error('unexpected asset')
 end,warn=function(s)warnings[#warnings+1]=s end}
local roofs=Roofs.new(ctx);eq(sourceReads,0);eq(assetReads,0,'cold construction performs no image IO')
for _,cart in ipairs({'gold','silver','crystal'})do
 game=cart;surface={};roofs:map(world,def,0,0,1)
 for y=336,383 do for x=112,159 do eq(ink(x,y),nativeInk(x,y)or'actor-or-ground','every complete native-scale foreground pixel and alpha gap survives')end end
end
eq(ink(127,368),'actor-or-ground','transparent source exterior does not erase backing')
local sr,ar,ni=sourceReads,assetReads,newImages
for i=1,100 do roofs:map(world,def,0,0,1)end
eq(sourceReads,sr);eq(assetReads,ar);eq(newImages,ni,'warm path does not allocate or read art')
def.blocks[1]=2;roofs:map(world,def,0,0,1);eq(sourceReads,sr,'unrelated blocks do not invalidate the single shrine anchor')
local actor={px=128,py=352,sprite={frameWidth=32,frameHeight=48,anchorX=8,anchorY=48}}
surface={};roofs:actor({def=def},actor,0,0,1,false,0,world)
eq(ink(128,352),nativeInk(128,352),'shrine covers the actor standing behind its front boundary')
eq(ink(148,352),'actor-or-ground','transparent silhouette boundary preserves actor')
actor.py=368;surface={};roofs:actor({def=def},actor,0,0,1,false,0,world)
eq(next(surface),nil,'native walkable interaction cell8,23 (physicalfeet380) remains in front')
actor.spriteYOffset=-16;surface={};roofs:actor({def=def},actor,0,0,1,false,0,world)
eq(next(surface),nil,'jump height cannot reverse physical foreground depth')
def.blocks[anchor]=1;surface={};roofs:map(world,def,0,0,1)
eq(next(surface),nil,'changed source block removes cached shrine');eq(sourceReads,sr,'inactive anchor does not read art')
def.blocks[anchor]=32;surface={};roofs:map(world,def,0,0,1);eq(ink(128,352),nativeInk(128,352));eq(newImages,ni,'restoring anchor reuses GPU images')
sr,ar=sourceReads,assetReads;world.daytime='DARK';surface={};roofs:map(world,def,0,0,1);eq(next(surface),nil);eq(sourceReads,sr,'DARK stays native')
world.daytime='DAY';active=false;roofs:map(world,def,0,0,1);eq(next(surface),nil);eq(sourceReads,sr,'Original mode performs no reads')
active=true;valid=false;revision=2;roofs:map(world,def,0,0,1);eq(next(surface),nil);eq(assetReads,ar,'failed source guard never opens artwork')
valid=true;revision=3;roofs:map(world,def,0,0,1);eq(ink(128,352),nativeInk(128,352))
eq(def.blocks,originalBlocks);eq(def.blocks[anchor],32,'renderer never changes source layout')
local released=newImages;roofs:dispose();eq(releases,released);surface={};roofs:map(world,def,0,0,1);eq(next(surface),nil,'retained wrapper after unload cannot draw released textures');roofs:dispose();eq(releases,released)
local function rejected(change)
 local r=row('crystal',8,22);change(r);local bad=clone(ctx);bad.furnitureRows={r}
 eq(pcall(Roofs.new,bad),false,'invalid shrine contract fails closed')
end
rejected(function(r)r.map='OTHER'end)
rejected(function(r)r.game='red'end)
rejected(function(r)r.tileset='TILESET_JOHTO'end)
rejected(function(r)r.id=31 end)
rejected(function(r)r.quadrant=1 end)
rejected(function(r)r.anchorX=7 end)
rejected(function(r)r.anchorY=23 end)
rejected(function(r)r.sourceHash=hash('b')end)
rejected(function(r)r.sourceCollision=0 end)
rejected(function(r)r.x=6 end)
rejected(function(r)r.y=20 end)
rejected(function(r)r.frontY=400 end)
rejected(function(r)r.base={}end)
rejected(function(r)r.role='unchecked_shrine'end)
local bad=clone(ctx);bad.furnitureRows={row('crystal',7,21)};bad.warn=function()end
bad.original=function()return{getDimensions=function()return 16,16 end,getPixel=function()return 1,1,1,1 end}end
local rejectedArt=Roofs.new(bad);surface={};rejectedArt:map(world,def,0,0,1);eq(next(surface),nil,'opaque pixels outside complete24x34 envelope rejected');rejectedArt:dispose()
bad.original=function()return{getDimensions=function()return 24,34 end}end
rejectedArt=Roofs.new(bad);surface={};rejectedArt:map(world,def,0,0,1);eq(next(surface),nil,'oversized per-cell asset rejected');rejectedArt:dispose()
print('roofs_shrine_test: '..checks..' checks')
