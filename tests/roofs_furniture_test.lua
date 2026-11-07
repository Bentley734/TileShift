local root=assert(arg[1])
local Roofs=assert(loadfile(root..'/lib/roofs.lua'))()
local Mapping=assert(loadfile(root..'/lib/mapping.lua'))()
local checks=0
local function eq(a,b,why)checks=checks+1;assert(a==b,why or(tostring(a)..' ~= '..tostring(b)))end
local function clone(v)
 if type(v)~='table'then return v end
 local out={};for k,value in pairs(v)do out[k]=clone(value)end;return out
end
local function hash(c)return string.rep(c,64)end
local sourceFiles={metadata=hash('1'),image=hash('2'),maps=hash('3')}
local function bed(id,x,y,game)
 return {game=game or'crystal',style='gen3',kind='third_party',map='PLAYERS_HOUSE_2F',tileset='TILESET_PLAYERS_ROOM',
  furniture='bed',anchorX=0,anchorY=4,id=id,quadrant=0,sourceHash=hash('a'),sourceFiles=sourceFiles,
  role='native_bed_foreground',status='reviewed',evidence='Complete24x34 synthetic native bed at original scale.',
  x=x,y=y,frontY=96,asset='assets/third_party/bed-'..id..'-'..x..'-'..y..'.png',assetFileHash=hash('b'),
  credit='Native synthetic test art',sourceUrl='https://example.com/bed'}
end
local function pc(x,y)
 local row=bed(33,x,y);row.furniture='elm_pc';row.map='ELMS_LAB';row.tileset='TILESET_LAB';row.anchorX=2
 row.asset='assets/third_party/pc-'..x..'-'..y..'.png';row.role='native_pc_foreground';return row
end
local function carpet(id,x,y,game)
 local row=bed(id,x,y,game);row.furniture='carpet';row.anchorX=x;row.anchorY=2;row.quadrant=x%2
 row.frontY=nil;row.asset='assets/third_party/rug-'..id..'-'..x..'-'..y..'.png';row.role='native_carpet_border';return row
end
local surface,draws,sourceReads,assetReads,images,releases,validations={},{},0,0,0,0,0
local function ink(x,y)return surface[y*256+x]or'actor-or-floor'end
local G={push=function()end,pop=function()end,setShader=function()end,setColor=function()end}
function G.newImage(data)
 images=images+1
 return {data=data,setFilter=function()end,release=function()releases=releases+1 end}
end
function G.newQuad()return{setViewport=function(self,x,y,w,h)self.x,self.y,self.w,self.h=x,y,w,h end,release=function()end}end
function G.draw(texture,q,x,y)
 local sx,sy,w,h
 if type(q)=='table'then sx,sy,w,h=q.x,q.y,q.w,q.h else x,y=q,x;sx,sy,w,h=0,0,16,16 end
 draws[#draws+1]={texture=texture,x=x,y=y}
 for yy=0,h-1 do for xx=0,w-1 do
  local color=texture.data.ink(sx+xx,sy+yy)
  if color then surface[(y+yy)*256+x+xx]=color end
 end end
end
local pixels={}
local function picture(row)
 local data=pixels[row.asset]
 if data then return data end
 data={getDimensions=function()return 16,16 end}
 function data.ink(x,y)
  if row.furniture=='bed'then
   local px,py=row.x*16+x,row.y*16+y
   if px<24 and py>=62 and py<96 and not(px==20 and py==70)then return row.id==27 and'bed27'or'bed28'end
  elseif row.furniture=='carpet'then return row.id==9 and'rug9'or'rug12'
  elseif x>=2 and x<=13 and y>=2 and y<=13 then return'pc'end
 end
 function data:getPixel(x,y)return 1,1,1,data.ink(x,y)and 1 or 0 end
 pixels[row.asset]=data;return data
end
local active,revision,game,valid=true,1,'crystal',true
local warnings={}
local rows={}
for _,cart in ipairs({'gold','silver','crystal'})do for _,id in ipairs({27,28})do
 for y=3,5 do for x=0,1 do rows[#rows+1]=bed(id,x,y,cart)end end
end end
for y=4,5 do for x=2,3 do rows[#rows+1]=pc(x,y)end end
for _,cart in ipairs({'gold','silver','crystal'})do for _,id in ipairs({9,12})do
 for y=2,3 do for _,x in ipairs({0,5})do rows[#rows+1]=carpet(id,x,y,cart)end end
end end
local def={id='PLAYERS_HOUSE_2F',tileset='TILESET_PLAYERS_ROOM',width=4,height=3,
 blocks={4,1,3,2,5,6,5,5,5,5,7,5}}
local blocks=def.blocks
local world={camera={x=0,y=0},viewW=128,viewH=96,daytime='DAY'}
local ctx={rows={},furnitureRows=rows,graphics=G,version=function()return game end,
 active=function()return active end,revision=function()return revision end,
 validate=function(row)
  validations=validations+1
  eq(row.x,row.anchorX,'mapping validation uses the real source anchor')
  eq(row.y,row.anchorY);return Mapping.validate(row)
 end,
 donor={cell=function(_,ref)
  sourceReads=sourceReads+1
  if ref.id==9 or ref.id==12 then eq(ref.quadrant==0 or ref.quadrant==1,true)else eq(ref.quadrant,0)end
  eq(ref.hash,hash('a'));eq(ref.hashOnly,true)
  eq(ref.monochrome,true);eq(ref.sourceFiles,sourceFiles);eq(ref.map==def or ref.map.id=='ELMS_LAB',true)
  return valid and{}or nil,'changed native source'
 end},
 original=function(path,expected)
  assetReads=assetReads+1;eq(expected,hash('b'))
  for _,row in ipairs(rows)do if row.asset==path then return picture(row)end end
  error('unexpected asset')
 end,warn=function(message)warnings[#warnings+1]=message end}
local roofs=Roofs.new(ctx)
eq(sourceReads,0);eq(assetReads,0)
local bare=roofs:cells(game,def)
eq(next(bare.grid),nil,'bare-first warmup creates no furniture')
eq(sourceReads,0);eq(assetReads,0)
def.blocks[9]=27 -- The native decoration callback, not the overlay, owns this edit.
local decorated=roofs:cells(game,def)
eq(decorated~=bare,true,'a tiny anchor change invalidates a bare cached result')
eq(#decorated.rows[3],2);eq(#decorated.rows[4],2);eq(#decorated.rows[5],2)
eq(sourceReads,6);eq(assetReads,6);eq(images,6)
surface={};roofs:map(world,def,0,0,1)
eq(ink(0,61),'actor-or-floor','transparent upper padding preserves source floor')
eq(ink(0,62),'bed27','both native overhang rows are intact')
eq(ink(23,95),'bed27','the full24x34 native rectangle survives')
eq(ink(24,95),'actor-or-floor','right-side transparency leaves walkable backing visible')
eq(ink(20,70),'actor-or-floor','transparent gaps never erase backing')
local readsBefore,assetsBefore,imagesBefore,validBefore=sourceReads,assetReads,images,validations
for i=1,100 do roofs:map(world,def,0,0,1);roofs:cells(game,def)end
eq(sourceReads,readsBefore,'warm frames do not decode source imports')
eq(assetReads,assetsBefore,'warm frames do not read assets');eq(images,imagesBefore);eq(validations,validBefore)
def.blocks[1]=8;eq(roofs:cells(game,def),decorated,'unrelated carpet blocks do not rebuild furniture')
def.blocks[9]=28;surface={};roofs:map(world,def,0,0,1)
eq(ink(23,95),'bed28','alternate bed changes its complete foreground')
eq(images,12,'each checked native asset gets only one GPU texture')
def.blocks[9]=5;surface={};roofs:map(world,def,0,0,1)
eq(ink(1,64),'actor-or-floor','put-away removes cached foreground immediately')
def.blocks[9]=27;surface={};roofs:map(world,def,0,0,1)
eq(ink(23,95),'bed27');eq(images,12,'switching back reuses prior textures')
for _,cart in ipairs({'gold','silver'})do
 game=cart;surface={};roofs:map(world,def,0,0,1);eq(ink(23,95),'bed27','all three GSC hosts use their own source guards')
end
game='crystal'
def.blocks[5],def.blocks[7]=9,9
surface={};roofs:map(world,def,0,0,1)
eq(ink(0,40),'rug9','left border gets its exact position-dependent ground artwork')
eq(ink(80,40),'rug9','right border gets its separate end artwork')
eq(ink(32,40),'actor-or-floor','ground overlays never cover the central PC/table cells')
eq(ink(0,61),'rug9','rug keeps its ground pixels below the bed overhang')
eq(ink(0,62),'bed27','bed overhang stays above a later-added ground-only row')
local rugActor={px=0,py=32,sprite={frameWidth=16,frameHeight=16,anchorX=8,anchorY=16}}
surface={};roofs:actor({def=def},rugActor,0,0,1,false,0,world)
eq(ink(0,40),'actor-or-floor','ground-only carpet borders never replay over actors')
def.blocks[5],def.blocks[7]=12,12;surface={};roofs:map(world,def,0,0,1)
eq(ink(0,40),'rug12');eq(ink(80,40),'rug12','carpet state changes invalidate both bounded anchors')
local rugSources,rugAssets=sourceReads,assetReads
for i=1,100 do roofs:map(world,def,0,0,1)end
eq(sourceReads,rugSources);eq(assetReads,rugAssets,'warm rug borders do not read imports/assets')
local ordered=clone(ctx)
ordered.furnitureRows={carpet(12,0,3),bed(27,0,3)}
local groundFirst=Roofs.new(ordered);surface={};groundFirst:map(world,def,0,0,1)
eq(ink(0,61),'rug12');eq(ink(0,62),'bed27','bed also remains above an earlier-added ground-only row')
groundFirst:dispose()
def.blocks[5],def.blocks[7]=5,5;surface={};roofs:map(world,def,0,0,1)
eq(ink(0,40),'actor-or-floor','put-away immediately removes both rug borders')
local actor={px=16,py=64,sprite={frameWidth=16,frameHeight=32,anchorX=8,anchorY=32}}
surface={};roofs:actor({def=def},actor,0,0,1,false,0,world)
eq(ink(17,70),'bed27','walkable right source quadrant still respects opaque native bed extension')
eq(ink(24,70),'actor-or-floor','unused extension pixels preserve an actor')
local pcDef={id='ELMS_LAB',tileset='TILESET_LAB',width=5,height=6,blocks={}}
for i=1,30 do pcDef.blocks[i]=1 end
pcDef.blocks[12]=33 -- block1,2; source cell2,4.
local elm={px=48,py=64,sprite={frameWidth=16,frameHeight=32,anchorX=8,anchorY=32}}
surface={};roofs:actor({def=pcDef},elm,0,0,1,false,0,world)
eq(ink(51,70),'pc','the complete rear monitor occludes Elm behind the desk')
eq(ink(48,70),'actor-or-floor','transparent monitor surroundings preserve Elm')
elm.py=84;elm.sprite.frameHeight=64;elm.sprite.anchorY=64
surface={};roofs:actor({def=pcDef},elm,0,0,1,false,0,world)
eq(ink(51,70),'actor-or-floor','physical feet on the front boundary remain in front')
elm.spriteYOffset=-20;surface={};roofs:actor({def=pcDef},elm,0,0,1,false,0,world)
eq(ink(51,70),'actor-or-floor','jumping offsets do not reverse physical depth')
elm.py=64;elm.spriteYOffset=0
for _,cart in ipairs({'gold','silver'})do
 game=cart;surface={};roofs:actor({def=pcDef},elm,0,0,1,false,0,world)
 eq(ink(51,70),'actor-or-floor','Gold/Silver retain the original empty central lab area')
end
game='crystal'
local oldReads=sourceReads
world.daytime='DARK';surface={};roofs:map(world,def,0,0,1);roofs:actor({def=pcDef},elm,0,0,1,false,0,world)
eq(next(surface),nil,'native DARK visibility is untouched');eq(sourceReads,oldReads)
world.daytime='DAY';active=false;surface={};roofs:map(world,def,0,0,1);roofs:actor({def=pcDef},elm,0,0,1,false,0,world)
eq(next(surface),nil,'Original/ownership loss hides furniture');eq(sourceReads,oldReads)
active=true;revision=2;valid=false;surface={};local oldAssets=assetReads
roofs:map(world,def,0,0,1);eq(next(surface),nil,'changed source fails closed');eq(assetReads,oldAssets)
eq(#warnings,6,'each rejected source row is diagnosed outside the warm path')
revision=3;valid=true;surface={};roofs:map(world,def,0,0,1);eq(ink(23,95),'bed27')
eq(def.blocks,blocks,'overlay preserves the source block table identity');eq(def.blocks[9],27)
local released=images;roofs:dispose();eq(releases,released)
local chainedCalls=0
local laterWrapper=function()chainedCalls=chainedCalls+1;roofs:map(world,def,0,0,1);return'native-wrapper'end
surface={};eq(laterWrapper(),'native-wrapper');eq(chainedCalls,1);eq(next(surface),nil,'retained wrapper cannot use released textures')
roofs:dispose();eq(releases,released,'unload remains idempotent')
local function rejected(change)
 local row=bed(27,0,3);change(row)
 local bad=clone(ctx);bad.furnitureRows={row};eq(pcall(Roofs.new,bad),false,'invalid furniture contract rejected')
end
rejected(function(r)r.furniture='canopy'end)
rejected(function(r)r.game='red'end)
rejected(function(r)r.map='OTHER'end)
rejected(function(r)r.anchorY=3 end)
rejected(function(r)r.quadrant=1 end)
rejected(function(r)r.x=2 end)
rejected(function(r)r.y=2 end)
rejected(function(r)r.y=3.5 end)
rejected(function(r)r.frontY=10000 end)
rejected(function(r)r.sourceFiles=nil end)
rejected(function(r)r.assetFileHash=nil end)
rejected(function(r)r.base={}end)
local function rejectedCarpet(change)
 local row=carpet(9,0,2);change(row)
 local bad=clone(ctx);bad.furnitureRows={row};eq(pcall(Roofs.new,bad),false,'invalid ground-only carpet contract rejected')
end
rejectedCarpet(function(r)r.id=10 end)
rejectedCarpet(function(r)r.frontY=96 end)
rejectedCarpet(function(r)r.x=1 end)
rejectedCarpet(function(r)r.y=0 end)
rejectedCarpet(function(r)r.anchorX=2 end)
rejectedCarpet(function(r)r.quadrant=1 end)
local duplicate=clone(ctx);duplicate.furnitureRows={bed(27,0,3),bed(27,0,3)}
eq(pcall(Roofs.new,duplicate),false,'duplicate active source/cell alias is rejected')
local wrong=clone(ctx);wrong.furnitureRows={bed(27,1,3)};wrong.warn=function()end
wrong.original=function()return{getDimensions=function()return 32,16 end}end
local bad=Roofs.new(wrong);surface={};bad:map(world,def,0,0,1);eq(next(surface),nil,'wrong asset dimensions fail closed');bad:dispose()
wrong.original=function()return{getDimensions=function()return 16,16 end,getPixel=function()return 1,1,1,1 end}end
bad=Roofs.new(wrong);surface={};bad:map(world,def,0,0,1);eq(next(surface),nil,'opaque pixels beyond native24x34 bounds fail closed');bad:dispose()
print('roofs_furniture_test: '..checks..' checks')
