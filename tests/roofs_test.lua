local root=assert(arg[1])
local R=assert(loadfile(root..'/lib/roofs.lua'))()
local checks=0
local function eq(a,b,s)checks=checks+1;assert(a==b,s or(tostring(a)..' ~= '..tostring(b)))end
local draws,images,releases,reads,sourceReads=0,0,0,0,0
local G={push=function()end,pop=function()end,setShader=function()end,setColor=function()end}
function G.newImage(data)images=images+1;return {setFilter=function()end,replacePixels=function()end,release=function()releases=releases+1 end}end
function G.newQuad()return{setViewport=function(_,x,y,w,h)eq(x>=0 and y>=0 and x+w<=16 and y+h<=16,true)end,release=function()end}end
function G.draw(...)draws=draws+1 end
local image={}
local row={game='crystal',style='gen3',kind='original',map='TOWN',tileset='T',x=1,y=0,
 buildingY=1,id=7,quadrant=1,sourceHash=string.rep('a',64),asset='assets/original/test.png',assetFileHash=string.rep('b',64)}
local def={id='TOWN',tileset='T',width=2,height=2,blocks={7,8,9,10}}
local originalBlocks=def.blocks
local active,revision,valid,warnings=true,1,true,0
local ctx={rows={row},graphics=G,active=function()return active end,revision=function()return revision end,
 version=function()return'crystal'end,validate=function()return true end,
 donor={cell=function(_,ref)sourceReads=sourceReads+1;eq(ref.hash,row.sourceHash);eq(ref.map,def);eq(ref.hashOnly,true);return valid and{}or nil,'changed source'end},
 original=function(path,hash)reads=reads+1;eq(path,row.asset);eq(hash,row.assetFileHash);return image end,
 warn=function()warnings=warnings+1 end}
local roofs=R.new(ctx)
eq(reads,0,'assets stay lazy');eq(sourceReads,0)
local world={camera={x=0,y=0},viewW=64,viewH=64,daytime='DAY'}
local map={def=def};local actor={px=16,py=4,sprite={frameWidth=16,frameHeight=16,anchorX=8,anchorY=16}}
roofs:map(world,def,0,0,1);eq(draws,1);eq(reads,1);eq(sourceReads,1);eq(images,1)
roofs:actor(map,actor,0,0,1,false,0,world);eq(draws,2,'roof redraws over full actor body')
local before=draws
for i=1,100 do roofs:map(world,def,0,0,1);roofs:actor(map,actor,0,0,1,false,0,world)end
eq(draws-before,200);eq(sourceReads,1,'warm draws never recheck imports');eq(reads,1,'warm draws never reread images');eq(images,1)
world.camera.x=100;before=draws;roofs:map(world,def,0,0,1);eq(draws,before,'offscreen roofs culled');world.camera.x=0
actor.px=48;roofs:actor(map,actor,0,0,1,false,0,world);eq(draws,before,'unrelated actors untouched');actor.px=16
world.daytime='DARK';roofs:map(world,def,0,0,1);roofs:actor(map,actor,0,0,1,false,0,world);eq(draws,before,'native dark visibility retained');world.daytime='DAY'
active=false;roofs:map(world,def,0,0,1);roofs:actor(map,actor,0,0,1,false,0,world);eq(draws,before,'Original/ownership loss hides roofs');active=true
revision=2;valid=false;roofs:map(world,def,0,0,1);eq(draws,before,'changed source cannot render');eq(warnings,1);eq(reads,1,'failed source prevents asset load')
revision=3;valid=true;roofs:map(world,def,0,0,1);eq(images,1,'revision reuses checked texture')
eq(def.blocks,originalBlocks);eq(def.blocks[1],7,'no tile/collision replacement')
roofs:dispose();eq(releases,1);before=draws;roofs:map(world,def,0,0,1);roofs:actor(map,actor,0,0,1,false,0,world);eq(draws,before);roofs:dispose();eq(releases,1,'unload is idempotent')
local bad={};for k,v in pairs(row)do bad[k]=v end;bad.buildingY=3
ctx.rows={bad};eq(pcall(R.new,ctx),false,'more than one upper row is rejected')
-- Side decorations may reach one column beyond the original map image, but
-- their fingerprints must anchor to real source cells. Nothing extends the
-- source map, writes collision or repeatedly reads imports on warm draws.
local function sideRow(side)
 return {game='crystal',style='gen3',kind='original',map='TOWN',tileset='T',
  side=side,x=side=='left'and 1 or 4,y=1,sourceX=side=='left'and 1 or 3,
  buildingX=2,buildingY=1,buildingW=2,buildingH=2,id=side=='left'and 7 or 8,
  quadrant=3,sourceHash=string.rep('c',64),asset='assets/original/side.png',assetFileHash=string.rep('d',64)}
end
local sideReads,sideSources,sideWarnings=0,0,0
local sideData={}
local sideCtx={rows={sideRow('left'),sideRow('right')},graphics=G,
 active=function()return true end,revision=function()return 1 end,version=function()return'crystal'end,
 validate=function(r)eq(r.x,r.sourceX,'side validation uses its real source anchor');return true end,donor={cell=function(_,ref)
  sideSources=sideSources+1;eq(ref.id==7 or ref.id==8,true);eq(ref.quadrant,3)
  eq(ref.map,def);eq(ref.hashOnly,true);return{}
 end},original=function(path,hash)
  sideReads=sideReads+1;eq(path,'assets/original/side.png');eq(hash,string.rep('d',64));return sideData
 end,warn=function()sideWarnings=sideWarnings+1 end}
local sides=R.new(sideCtx);world.viewW=96;before=draws
sides:map(world,def,0,0,1);eq(draws-before,2,'both adjacent columns render, including the right map edge')
eq(sideSources,2);eq(sideReads,2);eq(def.blocks,originalBlocks)
before=draws
for i=1,100 do sides:map(world,def,0,0,1)end
eq(draws-before,200);eq(sideSources,2,'side overlays do not reread imports every frame');eq(sideReads,2)
local sideActor={px=56,py=20,sprite={frameWidth=16,frameHeight=16,anchorX=8,anchorY=16}}
before=draws;sides:actor(map,sideActor,0,0,1,false,0,world)
eq(draws-before,1,'right edge redraw clips to the overlapping actor pixels')
sideActor.px=24;before=draws;sides:actor(map,sideActor,0,0,1,false,0,world)
eq(draws-before,1,'left neighbour redraw clips to the overlapping actor pixels')
world.daytime='DARK';before=draws;sides:map(world,def,0,0,1);eq(draws,before);world.daytime='DAY'
sideActor.py=48;sideActor.sprite.frameHeight=48;sideActor.sprite.anchorY=48
before=draws;sides:actor(map,sideActor,0,0,1,false,0,world)
eq(draws,before,'a tall actor standing in front remains in front of side artwork')
sideActor.spriteYOffset=-12;sides:actor(map,sideActor,0,0,1,false,0,world)
eq(draws,before,'jump offset does not change physical front/behind order')
sides:dispose();before=draws;sides:map(world,def,0,0,1);eq(draws,before)
local far=sideRow('right');far.x=6;sideCtx.rows={far}
eq(pcall(R.new,sideCtx),false,'three or more adjacent columns are rejected')
local second=sideRow('right');second.x=5;sideCtx.rows={second}
local secondSides=R.new(sideCtx);before=draws
secondSides:map(world,def,0,0,1);eq(draws-before,1,'a second adjacent column uses the original nearest-edge fingerprint')
secondSides:dispose()
second=sideRow('left');second.x=0;second.sourceX=0;second.quadrant=2;sideCtx.rows={second}
local previousDonor=sideCtx.donor
sideCtx.donor={cell=function(_,ref)eq(ref.id,7);eq(ref.quadrant,2);return{}end}
secondSides=R.new(sideCtx);before=draws
secondSides:map(world,def,0,0,1);eq(draws-before,1,'second left column renders from its exact real source quadrant')
secondSides:dispose();sideCtx.donor=previousDonor
far=sideRow('left');far.x=-1;far.sourceX=0;sideCtx.rows={far}
eq(pcall(R.new,sideCtx),false,'a third left column is rejected')
local low=sideRow('left');low.y=0;sideCtx.rows={low}
eq(pcall(R.new,sideCtx),false,'side rows cannot extend above their building')
local zero=sideRow('left');zero.buildingW=0;sideCtx.rows={zero}
eq(pcall(R.new,sideCtx),false,'empty building footprints are rejected')
local anchor=sideRow('right');anchor.sourceX=2;sideCtx.rows={anchor}
local rejected=R.new(sideCtx);before=draws;local oldReads=sideReads
rejected:map(world,def,0,0,1);eq(draws,before);eq(sideReads,oldReads);eq(sideWarnings,1,'wrong edge fingerprint anchor fails closed');rejected:dispose()
local outside=sideRow('right');outside.buildingW=3;outside.x=5;sideCtx.rows={outside}
rejected=R.new(sideCtx);before=draws
rejected:map(world,def,0,0,1);eq(draws,before);eq(sideWarnings,2,'the original building must remain within its map');rejected:dispose()
-- Native roof pieces use the cached normal composer with no baked ground.
local native={};for k,v in pairs(row)do native[k]=v end
native.kind='native_composite';native.asset=nil;native.assetFileHash=nil;native.parts={{}}
local calls=0
ctx.rows={native};ctx.compose=function(r)calls=calls+1;eq(r,native);eq(r.base,nil);return{under=image}end
local nativeRoofs=R.new(ctx);before=draws;nativeRoofs:map(world,def,0,0,1)
eq(draws-before,1,'native alpha roof draws');eq(calls,1)
for i=1,100 do nativeRoofs:map(world,def,0,0,1)end
eq(calls,1,'native roof composition stays cached across warm frames')
local nativeImages=images
for i=1,5 do revision=revision+1;nativeRoofs:map(world,def,0,0,1)end
eq(images,nativeImages,'option changes reuse one GPU texture per native roof row')
eq(calls,6,'option changes still revalidate and recompose native donor references')
nativeRoofs:dispose()
-- A shared cell keeps both native images in map order, while the actor pass
-- independently respects each building's physical front line and alpha.
local pixelSources,pixelAssets,pixelImages,pixelDraws=0,0,0,0
local surface={}
local function ink(x,y)return surface[y*64+x]or'magenta'end
local function solid(value,lo,hi)
 return{pixel=function(x,y)return x>=lo and x<=hi and value or nil end}
end
local red,blue=solid('red',0,7),solid('blue',4,11)
local PG={push=function()end,pop=function()end,setShader=function()end,setColor=function()end}
function PG.newImage(data)
 pixelImages=pixelImages+1
 return{data=data,setFilter=function()end,release=function()end}
end
function PG.newQuad()return{setViewport=function(self,x,y,w,h)self.x,self.y,self.w,self.h=x,y,w,h end,release=function()end}end
function PG.draw(texture,q,x,y)
 pixelDraws=pixelDraws+1
 local sx,sy,w,h
 if type(q)=='table'then sx,sy,w,h=q.x,q.y,q.w,q.h
 else x,y=q,x;sx,sy,w,h=0,0,16,16 end
 for yy=0,h-1 do for xx=0,w-1 do
  local color=texture.data.pixel(sx+xx,sy+yy)
  if color then surface[(y+yy)*64+x+xx]=color end
 end end
end
local side=sideRow('left');side.y=0;side.buildingY=0;side.buildingH=2;side.quadrant=1
side.asset='assets/original/side-red.png';side.role='side-red'
local top={};for k,v in pairs(row)do top[k]=v end
top.asset='assets/original/top-blue.png';top.role='top-blue'
local stacks=R.new({rows={side,top},graphics=PG,active=function()return true end,
 revision=function()return 1 end,version=function()return'crystal'end,validate=function()return true end,
 donor={cell=function()pixelSources=pixelSources+1;return{}end},
 original=function(path)pixelAssets=pixelAssets+1;return path==side.asset and red or blue end})
world.viewW=64
stacks:map(world,def,0,0,1)
eq(ink(17,4),'red','lower native building remains visible through upper transparency')
eq(ink(21,4),'blue','later native roof wins only at its opaque pixels')
eq(ink(29,4),'magenta','transparent pixels preserve the actual backing')
local cells=stacks:cells('crystal',def);local shared=cells.grid[1]
eq(shared.role,'side-red');eq(shared.next.role,'top-blue');eq(shared.next.next,nil)
surface={};actor.px,actor.py=16,4
stacks:actor(map,actor,0,0,1,false,0,world)
eq(ink(17,4),'red');eq(ink(21,4),'blue');eq(ink(29,4),'magenta','transparent native corners never paint the actor')
surface={}
local tall={px=16,py=20,sprite={frameWidth=16,frameHeight=48,anchorX=8,anchorY=48}}
stacks:actor(map,tall,0,0,1,false,0,world)
eq(ink(17,4),'magenta','actor in front of the side keeps its body pixels')
eq(ink(21,4),'blue','same actor remains behind the independent upper roof')
for i=1,100 do stacks:map(world,def,0,0,1);stacks:actor(map,actor,0,0,1,false,0,world)end
eq(pixelSources,2,'overlap stacks do not reread source maps in warm frames')
eq(pixelAssets,2,'overlap stacks do not reread source artwork in warm frames')
eq(pixelImages,2,'overlap stacks reuse both native textures')
stacks:dispose()
print('roof overhang checks: '..checks)
