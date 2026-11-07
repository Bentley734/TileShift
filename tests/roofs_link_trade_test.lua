local root=assert(arg[1])
local Roofs=assert(loadfile(root..'/lib/roofs.lua'))()
local Mapping=assert(loadfile(root..'/lib/mapping.lua'))()
local checks=0
local function eq(a,b,why)checks=checks+1;assert(a==b,why or(tostring(a)..' ~= '..tostring(b)))end
local function clone(v)if type(v)~='table'then return v end;local out={};for k,a in pairs(v)do out[k]=clone(a)end;return out end
local function hash(c)return string.rep(c,64)end
local sourceHash='1e0be084305e405fe6e6e55e3043b19e7d100bfac0d4dc496d3661c07ef29ccb'
local battleHash='1a1c7d4b890f991a1290f715332ee869b8c2eb211929e52a0f5dc95284ddfe5d'
local function row(game,map,x,y)
 local battle=map=='COLOSSEUM'
 return{game=game,style='gen3',kind='third_party',map=map,tileset='TILESET_GATE',
 furniture=battle and'link_battle_apparatus'or'link_trade_apparatus',anchorX=4,anchorY=4,id=battle and 29 or 33,quadrant=0,sourceHash=battle and battleHash or sourceHash,sourceCollision=battle and 7 or 144,
 sourceFiles={image=hash('1'),metadata=hash('2'),maps=hash('3')},
 role=battle and'crystaldust_native_link_battle_apparatus'or'crystaldust_native_link_trade_apparatus',status='reviewed',evidence='Complete native machine fixture, native chairs remain behind seated actors.',
 x=x,y=y,frontY=76,asset='assets/third_party/link-machine-'..x..'-'..y..'.png',assetFileHash=hash('a'),
 credit='Synthetic complete native machine fixture',sourceUrl='https://example.com/link'}
end
local rows={}
for _,game in ipairs({'gold','silver','crystal'})do for _,map in ipairs({'TRADE_CENTER','TIME_CAPSULE','COLOSSEUM'})do
 for _,xy in ipairs({{3,3},{3,4},{4,2},{4,3},{4,4},{5,2},{5,3},{5,4},{6,3},{6,4}})do rows[#rows+1]=row(game,map,xy[1],xy[2])end
end end
local pixels,surface={},{}
local sourceReads,assetReads,newImages,releases=0,0,0,0
local function ink(x,y)return surface[y*256+x]or'actor-or-ground'end
local function nativeInk(x,y)
 if (x>=61 and x<99 and y>=43 and y<80 and not(x==75 and y==51))or(x>=49 and x<61 and y>=59 and y<77)or(x>=99 and x<111 and y>=59 and y<77)then return'native-apparatus'end
end
local G={push=function()end,pop=function()end,setShader=function()end,setColor=function()end}
function G.newImage(data)newImages=newImages+1;return{data=data,setFilter=function()end,release=function()releases=releases+1 end}end
function G.newQuad()return{setViewport=function(s,x,y,w,h)s.x,s.y,s.w,s.h=x,y,w,h end,release=function()end}end
function G.draw(texture,q,x,y)
 local sx,sy,w,h
 if type(q)=='table'then sx,sy,w,h=q.x,q.y,q.w,q.h else x,y=q,x;sx,sy,w,h=0,0,16,16 end
 for yy=0,h-1 do for xx=0,w-1 do local c=texture.data.ink(sx+xx,sy+yy);if c then surface[(y+yy)*256+x+xx]=c end end end
end
local function picture(r)
 if pixels[r.asset]then return pixels[r.asset]end
 local im={getDimensions=function()return 16,16 end,ink=function(x,y)return nativeInk(r.x*16+x,r.y*16+y)end}
 function im:getPixel(x,y)return 1,1,1,self.ink(x,y)and 1 or 0 end
 pixels[r.asset]=im;return im
end
local game,active,revision,valid='crystal',true,1,true
local def={id='TRADE_CENTER',tileset='TILESET_GATE',width=5,height=4,blocks={}}
for i=1,20 do def.blocks[i]=1 end
local anchor=13;def.blocks[anchor]=33
local originalBlocks=def.blocks
local world={camera={x=0,y=0},viewW=160,viewH=128,daytime='DAY'}
local ctx={graphics=G,rows={},furnitureRows=rows,version=function()return game end,active=function()return active end,revision=function()return revision end,
 validate=function(r)eq(r.x,4);eq(r.y,4,'checked source anchor, never decorative output position');return Mapping.validate(r)end,
 donor={cell=function(_,ref)local battle=def.id=='COLOSSEUM';sourceReads=sourceReads+1;eq(ref.id,battle and 29 or 33);eq(ref.quadrant,0);eq(ref.hashOnly,true);eq(ref.monochrome,true);eq(ref.hash,battle and battleHash or sourceHash);eq(ref.map,def);return valid and{}or nil,'source changed'end},
 original=function(path,expected)assetReads=assetReads+1;eq(expected,hash('a'));for _,r in ipairs(rows)do if r.asset==path then return picture(r)end end;error('unexpected asset')end,warn=function()end}
local roofs=Roofs.new(ctx);eq(sourceReads,0);eq(assetReads,0)
for _,cart in ipairs({'gold','silver','crystal'})do
 game=cart
 for _,map in ipairs({'TRADE_CENTER','TIME_CAPSULE','COLOSSEUM'})do
  def.id=map;def.blocks[anchor]=map=='COLOSSEUM'and 29 or 33;surface={};roofs:map(world,def,0,0,1)
  for y=32,79 do for x=48,111 do
   -- Empty corner cells are deliberately absent from the reviewed catalog.
   local corner=(x<64 or x>=96)and y<48
   eq(ink(x,y),(not corner and nativeInk(x,y))or'actor-or-ground','complete finite machine preserves its real exterior')
  end end
 end
end
local sr,ar,ni=sourceReads,assetReads,newImages
for i=1,100 do roofs:map(world,def,0,0,1)end
eq(sourceReads,sr);eq(assetReads,ar);eq(newImages,ni,'warm frame does not read or allocate')
def.blocks[1]=2;roofs:map(world,def,0,0,1);eq(sourceReads,sr,'one bounded link anchor controls cache invalidation')
local actor={px=64,py=48,sprite={frameWidth=16,frameHeight=32,anchorX=8,anchorY=32}}
surface={};roofs:actor({def=def},actor,0,0,1,false,0,world)
eq(ink(70,50),'native-apparatus','north actor physicalfeet60 is behind native machine')
eq(ink(75,51),'actor-or-ground','native transparent gap preserves actor')
for _,px in ipairs({48,96})do
 actor.px=px;actor.py=48;actor.sprite.frameWidth=32;actor.sprite.anchorX=16
 surface={};roofs:actor({def=def},actor,0,0,1,false,0,world)
 eq(ink(px+3,59),'native-apparatus','source-legal rear3/6,3 wide actor is behind native chair upper overhang')
 actor.px=px;actor.py=64;actor.sprite.frameWidth=48;actor.sprite.anchorX=24;actor.sprite.frameHeight=64;actor.sprite.anchorY=64
 surface={};roofs:actor({def=def},actor,0,0,1,false,0,world)
 eq(next(surface),nil,'source seated actor3/6,4 physicalfeet76 remains in front; chairs are never foreground')
 actor.spriteYOffset=-24;surface={};roofs:actor({def=def},actor,0,0,1,false,0,world);eq(next(surface),nil,'visual offset cannot reverse seated source depth')
 actor.spriteYOffset=0
end
actor.px=64;actor.py=80;surface={};roofs:actor({def=def},actor,0,0,1,false,0,world);eq(next(surface),nil,'source southfront row5 physicalfeet92 remains infront')
def.blocks[anchor]=1;surface={};roofs:map(world,def,0,0,1);eq(next(surface),nil,'cleared native anchor removes warm machine')
def.blocks[anchor]=29;surface={};roofs:map(world,def,0,0,1);eq(ink(70,50),'native-apparatus');eq(newImages,ni,'restoring source anchor reuses native textures')
sr,ar=sourceReads,assetReads;world.daytime='DARK';surface={};roofs:map(world,def,0,0,1);eq(next(surface),nil);eq(sourceReads,sr)
world.daytime='DAY';active=false;roofs:map(world,def,0,0,1);eq(next(surface),nil);eq(sourceReads,sr,'Original/ownership loss remains native')
active=true;valid=false;revision=2;roofs:map(world,def,0,0,1);eq(next(surface),nil);eq(assetReads,ar,'source guard fails before artwork load')
valid=true;revision=3;roofs:map(world,def,0,0,1);eq(ink(70,50),'native-apparatus');eq(def.blocks,originalBlocks);eq(def.blocks[anchor],29)
local released=newImages;roofs:dispose();eq(releases,released);surface={};roofs:map(world,def,0,0,1);eq(next(surface),nil);roofs:dispose();eq(releases,released)
local function rejected(change)
 local r=row('crystal','TRADE_CENTER',4,2);change(r);local bad=clone(ctx);bad.furnitureRows={r};eq(pcall(Roofs.new,bad),false,'invalid bounded link machine rejected')
end
rejected(function(r)r.game='red'end);rejected(function(r)r.map='COLOSSEUM'end);rejected(function(r)r.tileset='TILESET_LAB'end)
rejected(function(r)r.id=32 end);rejected(function(r)r.quadrant=1 end);rejected(function(r)r.anchorX=3 end);rejected(function(r)r.anchorY=3 end)
rejected(function(r)r.sourceHash=hash('b')end);rejected(function(r)r.sourceCollision=0 end);rejected(function(r)r.x=2 end);rejected(function(r)r.y=1 end)
rejected(function(r)r.frontY=80 end);rejected(function(r)r.base={}end);rejected(function(r)r.role='generic_machine'end)
local bad=clone(ctx);bad.furnitureRows={row('crystal','TRADE_CENTER',4,2)}
bad.original=function()return{getDimensions=function()return 16,16 end,getPixel=function()return 1,1,1,1 end}end
def.id='TRADE_CENTER';def.blocks[anchor]=33
local badArt=Roofs.new(bad);surface={};badArt:map(world,def,0,0,1);eq(next(surface),nil,'opaque pixels outside complete native envelope are rejected');badArt:dispose()
local invalidBattle=row('crystal','COLOSSEUM',4,2);invalidBattle.sourceHash=sourceHash
bad=clone(ctx);bad.furnitureRows={invalidBattle};eq(pcall(Roofs.new,bad),false,'Colosseum cannot borrow Trade source guard')
print('roofs_link_trade_test: '..checks..' checks')
