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
-- A generic town-tree crown expands into one cached canopy per real source
-- occurrence. Its extra tile can cross the north map edge, while its source
-- fingerprint and physical front line remain anchored to the original tree.
local Mapping=assert(loadfile(root..'/lib/mapping.lua'))()
local function clone(value)
 local out={};for k,v in pairs(value)do out[k]=type(v)=='table'and clone(v)or v end;return out
end
local treeTemplate={game='crystal',style='gen3',kind='third_party',map='CANOPIES',tileset='T',
 id=7,quadrant=0,role='dense_conifer_crown',status='reviewed',evidence='Synthetic complete native48px tree crown.',
 sourceHash=string.rep('a',64),asset='assets/third_party/johto-hacks/town-trees/middle.png',assetFileHash=string.rep('b',64),
 credit='Native test artwork',sourceUrl='https://example.com/native-tree',
 base={game='emerald',tileset='T',id=1,hash=string.rep('c',64)},
 canopy={asset='assets/third_party/johto-hacks/town-trees/top.png',hash=string.rep('d',64)}}
local canopyData=solid('green',4,11)
local buildingData=solid('blue',0,7)
local function canopyCase(buildingHeight)
 local template=clone(treeTemplate)
 local treeDef={id='CANOPIES',tileset='T',width=2,height=3,blocks={7,8,7,8,9,10}}
 local treeWorld={camera={x=0,y=0},viewW=64,viewH=96,daytime='DAY'}
 local treeMap={def=treeDef}
 local building={game='crystal',style='gen3',kind='third_party',map='CANOPIES',tileset='T',
  side='left',x=0,y=1,sourceX=0,buildingX=1,buildingY=0,buildingW=1,buildingH=buildingHeight,
  id=7,quadrant=2,role='canopy-adjacent-building',status='reviewed',evidence='Synthetic side with a checked native front line.',
  sourceHash=string.rep('e',64),asset='assets/third_party/building-blue.png',assetFileHash=string.rep('f',64),
  credit='Native test artwork',sourceUrl='https://example.com/native-building'}
 local sourceCalls,assetCalls,treeCalls,buildingCalls,canopyWarnings=0,0,0,0,0
 local canopyRevision,sourceValid=1,true
 local treeCtx={rows={building},treeRows={template},graphics=PG,
  active=function()return true end,revision=function()return canopyRevision end,
  version=function()return'crystal'end,validate=Mapping.validate,
  donor={cell=function(_,ref)
   sourceCalls=sourceCalls+1;eq(ref.map,treeDef);eq(ref.id,7);eq(ref.hashOnly,true)
   if ref.quadrant==0 then treeCalls=treeCalls+1;eq(ref.hash,template.sourceHash)
   else buildingCalls=buildingCalls+1;eq(ref.quadrant,2);eq(ref.hash,building.sourceHash)end
   return sourceValid and{}or nil,'changed native source'
  end},original=function(path,hash)
   assetCalls=assetCalls+1
   if path==template.canopy.asset then eq(hash,template.canopy.hash);return canopyData end
   eq(path,building.asset);eq(hash,building.assetFileHash);return buildingData
  end,warn=function()canopyWarnings=canopyWarnings+1 end}
 local treeRoofs=R.new(treeCtx)
 eq(sourceCalls,0,'generic tree templates remain lazy before a map is used')
 local treeCells=treeRoofs:cells('crystal',treeDef)
 local borderCanopy=assert(treeCells.grid[-65536],'source crown at y0 needs its canopy at y-1')
 eq(borderCanopy.x,0);eq(borderCanopy.y,-1);eq(borderCanopy.frontY,32)
 eq(borderCanopy.data,canopyData);eq(borderCanopy.next,nil)
 local sharedCanopy=assert(treeCells.grid[65536])
 local first,second=sharedCanopy,sharedCanopy.next
 eq(second~=nil,true,'an interior canopy keeps the existing side entry')
 eq(second.next,nil,'the shared cell contains exactly its side and canopy')
 if buildingHeight*16<64 then
  eq(first.data,buildingData,'a farther building side remains behind the nearer tree')
  eq(second.data,canopyData)
 else
  eq(first.data,canopyData,'nearer building sides and ties cover the tree canopy')
  eq(second.data,buildingData)
 end
 surface={};treeRoofs:map(treeWorld,treeDef,0,0,1)
 eq(ink(1,20),'blue','side-only pixels survive tree transparency')
 eq(ink(5,20),buildingHeight*16<64 and'green'or'blue','map order matches physical canopy/side depth')
 eq(ink(10,20),'green','complete canopy remains visible through side transparency')
 eq(ink(14,20),'magenta','unused transparent corners keep the backing pixels')
 treeWorld.camera.y=-16;surface={};treeRoofs:map(treeWorld,treeDef,0,0,1)
 eq(ink(5,4),'green','north-border y-1 canopy draws when its actual pixels enter the viewport')
 treeWorld.camera.y=0
 local treeActor={px=0,py=51,sprite={frameWidth=16,frameHeight=64,anchorX=8,anchorY=64}}
 surface={};treeRoofs:actor(treeMap,treeActor,0,0,1,false,0,treeWorld)
 eq(ink(5,20),buildingHeight*16<64 and'green'or'blue','actor redraw follows the same per-cell depth order as the map')
 eq(ink(10,20),'green','an actor behind the physical tree front is covered by its leaves')
 eq(ink(14,20),'magenta','transparent canopy/side corners do not erase actor pixels')
 treeActor.py=52;surface={};treeRoofs:actor(treeMap,treeActor,0,0,1,false,0,treeWorld)
 eq(ink(5,20),buildingHeight*16>64 and'blue'or'magenta','feet at the tree front stay in front of the canopy')
 eq(ink(10,20),'magenta','an actor in front of the tree keeps canopy-only body pixels')
 treeActor.spriteYOffset=-12;surface={};treeRoofs:actor(treeMap,treeActor,0,0,1,false,0,treeWorld)
 eq(ink(10,20),'magenta','a jump offset never changes physical front/behind order')
 treeActor.py=80;treeActor.spriteYOffset=nil;treeActor.sprite.frameHeight=96;treeActor.sprite.anchorY=96
 surface={};treeRoofs:actor(treeMap,treeActor,0,0,1,false,0,treeWorld)
 eq(ink(5,20),'magenta','a tall actor in front of both objects remains in front of both')
 -- A south neighbor's extra north row lies over the current map's last
 --16px band. Replay it after the current canvas, including for an actor whose
 -- current map has no canopy rows of its own.
 local primaryDef={id='PRIMARY',tileset='T',width=2,height=2,blocks={9,10,9,10}}
 local primaryMap={id='PRIMARY',def=primaryDef}
 treeWorld.maps={PRIMARY=primaryDef,CANOPIES=treeDef}
 treeWorld.map=primaryMap;treeWorld.neighbors={{id='CANOPIES',ox=16,oy=primaryDef.height*32}}
 treeWorld.viewW,treeWorld.viewH=96,128
 local neighborSources,neighborAssets=sourceCalls,assetCalls
 surface={};treeRoofs:borders(treeWorld,1)
 eq(ink(21,52),'green','the southern neighbor canopy survives a current-map canvas drawn over the connection')
 eq(ink(30,52),'magenta','translated border canopy preserves transparent pixels')
 eq(ink(21,84),'magenta','neighbor replay includes only its outside row, not its interior canopies or side art')
 local neighborActor={px=16,py=52,sprite={frameWidth=16,frameHeight=16,anchorX=8,anchorY=16}}
 surface={};treeRoofs:actor(primaryMap,neighborActor,0,0,1,false,0,treeWorld)
 eq(ink(21,52),'green','a primary-map actor behind the neighboring tree receives the translated canopy')
 eq(ink(30,52),'magenta','neighbor canopy holes retain the primary actor pixels')
 neighborActor.py=84;neighborActor.sprite.frameHeight=64;neighborActor.sprite.anchorY=64
 surface={};treeRoofs:actor(primaryMap,neighborActor,0,0,1,false,0,treeWorld)
 eq(ink(21,52),'magenta','translated physical frontY lets an actor at the neighboring root front remain in front')
 eq(ink(17,84),'magenta','neighbor actor replay does not repaint unrelated interior building sides')
 neighborActor.py=52;neighborActor.sprite.frameHeight=16;neighborActor.sprite.anchorY=16
 for i=1,100 do
  surface={};treeRoofs:borders(treeWorld,1)
  treeRoofs:actor(primaryMap,neighborActor,0,0,1,false,0,treeWorld)
  eq(ink(21,52),'green','warm connected-map canopy stays visible')
 end
 eq(sourceCalls,neighborSources,'neighbor border and actor passes do not recheck source imports after warmup')
 eq(assetCalls,neighborAssets,'neighbor border and actor passes do not reload native artwork')
 treeWorld.maps=nil;treeWorld.neighbors=nil;treeWorld.map=nil;treeWorld.viewW,treeWorld.viewH=64,96
 local warmSources,warmAssets,warmImages=sourceCalls,assetCalls,pixelImages
 local originalTreeBlocks=treeDef.blocks
 treeDef.blocks={}
 -- Replacing the block list with an empty table exposes any accidental warm
 -- expansion: cached map/actor draws must still find both existing canopies.
 for i=1,100 do
  surface={};treeRoofs:map(treeWorld,treeDef,0,0,1)
  eq(ink(10,20),'green','warm draws retain cached source occurrences without rescanning blocks')
  treeRoofs:actor(treeMap,treeActor,0,0,1,false,0,treeWorld)
 end
 eq(treeRoofs:cells('crystal',treeDef),treeCells,'warm map lookup returns the same cached expansion')
 eq(sourceCalls,warmSources,'warm canopy draws never recheck imported source data')
 eq(assetCalls,warmAssets,'warm canopy draws never reread native PNGs')
 eq(pixelImages,warmImages,'all occurrences reuse checked GPU textures')
 treeDef.blocks=originalTreeBlocks
 canopyRevision=2;sourceValid=false;local failed=treeRoofs:cells('crystal',treeDef)
 eq(next(failed.grid),nil,'failed native crown/building guards cannot paint an overhang')
 eq(assetCalls,warmAssets,'failed source guards prevent artwork loading')
 eq(canopyWarnings>0,true,'a changed native source is reported')
 canopyRevision=3;sourceValid=true
 local restored=treeRoofs:cells('crystal',treeDef)
 eq(restored.grid[-65536]~=nil,true,'a successful source revalidation restores the north canopy')
 eq(pixelImages,warmImages,'revision changes reuse the same canopy and side textures')
 eq(treeDef.blocks,originalTreeBlocks,'canopy expansion never replaces the source block table')
 eq(originalTreeBlocks[1],7);eq(originalTreeBlocks[3],7)
 treeRoofs:dispose()
end
canopyCase(3) -- Farther side front48; tree front64.
canopyCase(4) -- Equal front64; the existing building wins the tie.
canopyCase(5) -- Nearer side front80; tree front64.
local invalidCanopyCases={
 function(r)r.canopy.hash='unverified'end,
 function(r)r.canopy.asset='assets/third_party/../escaped.png'end,
 function(r)r.role='dense_conifer_trunk'end,
 function(r)r.game='red'end,
 function(r)r.y=-1;r.x=0 end,
 function(r)r.credit=nil end,
}
for _,change in ipairs(invalidCanopyCases)do
 local invalid=clone(treeTemplate);change(invalid)
 local ok=Mapping.validate(invalid);eq(ok,nil,'invalid canopy metadata fails the strict mapping validator')
 eq(pcall(R.new,{rows={},treeRows={invalid},graphics=PG,validate=Mapping.validate}),false,
  'invalid tree template is rejected before any map or texture is touched')
end
print('roof overhang checks: '..checks)
