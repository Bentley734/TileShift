local root=assert(arg[1])
local Roofs=assert(loadfile(root..'/lib/roofs.lua'))()
local Mapping=assert(loadfile(root..'/lib/mapping.lua'))()
local checks=0
local function eq(a,b,why)
 checks=checks+1;assert(a==b,why or(tostring(a)..' ~= '..tostring(b)))
end
local function clone(value)
 if type(value)~='table'then return value end
 local out={};for k,v in pairs(value)do out[k]=clone(v)end;return out
end
local function hash(letter)return string.rep(letter,64)end
local sources={metadata=hash('1'),image=hash('2'),maps=hash('3')}
local function tile(x,sourceX,id,q,letter)
 return{game='red',style='gen3',kind='original',map='TOWN',tileset='T',
  x=x,y=-1,sourceX=sourceX,sourceY=0,buildingX=0,buildingY=0,buildingW=4,buildingH=3,
  id=id,quadrant=q,sourceHash=hash(letter),sourceFiles=sources,
  role='reviewed-static-north-roof',status='reviewed',evidence='Complete native-size synthetic roof with a real source anchor.',
  asset='assets/original/north-'..letter..'.png',assetFileHash=hash('f')}
end
local north=tile(1,nil,7,1,'a')
local left=tile(-1,0,7,0,'b')
local right=tile(3,3,8,1,'c')
local upperRight=tile(5,3,8,1,'f')
local secondLeft=tile(-2,0,7,0,'9')
local legacy=tile(1,nil,7,3,'d')
legacy.y=1;legacy.sourceY=nil;legacy.buildingY=2;legacy.buildingH=2
local tree={game='crystal',style='gen3',kind='third_party',map='TOWN',tileset='T',
 id=7,quadrant=0,role='dense_conifer_crown',status='reviewed',evidence='Complete native tree template.',
 sourceHash=hash('e'),sourceFiles=sources,
 base={game='emerald',tileset='T',id=1,hash=hash('f')},
 asset='assets/third_party/johto-hacks/town-trees/middle.png',assetFileHash=hash('f'),
 credit='Native test artwork',sourceUrl='https://example.com/native-tree',
 canopy={asset='assets/third_party/johto-hacks/town-trees/top.png',hash=hash('f')}}
local crystalLegacy=clone(legacy);crystalLegacy.game='crystal'
local def={id='TOWN',tileset='T',width=2,height=2,blocks={7,8,9,10}}
local originalBlocks=def.blocks
local surface,draws,reads,sourceReads,images,releases,composes={},{},0,0,0,0,0
local revision,active,game=1,true,'red'
local warnings={}
local data={pixel=function(x,y)return x>=2 and x<=13 and y>=1 and y<=14 and'roof'or nil end}
local function at(x,y)return surface[y*512+x]or'backing'end
local G={push=function()end,pop=function()end,setShader=function()end,setColor=function()end}
function G.newImage(value)
 images=images+1
 return{data=value,setFilter=function(_,a,b)eq(a,'nearest');eq(b,'nearest')end,
  release=function()releases=releases+1 end}
end
function G.newQuad()
 return{setViewport=function(self,x,y,w,h)
  eq(x>=0 and y>=0 and x+w<=16 and y+h<=16,true,'actor clips stay within the retained16px tile')
  self.x,self.y,self.w,self.h=x,y,w,h
 end,release=function()end}
end
function G.draw(texture,q,x,y)
 local sx,sy,w,h=0,0,16,16
 if type(q)=='table'then sx,sy,w,h=q.x,q.y,q.w,q.h else x,y=q,x end
 draws[#draws+1]={x=x,y=y}
 for yy=0,h-1 do for xx=0,w-1 do
  local color=texture.data.pixel(sx+xx,sy+yy)
  if color then surface[(y+yy)*512+x+xx]=color end
 end end
end
local validated={}
local expected={}
for _,r in ipairs({north,left,right,upperRight,secondLeft,legacy,tree})do expected[r.sourceHash]={id=r.id,q=r.quadrant}end
local ctx={rows={north,left,right,upperRight,secondLeft,legacy,crystalLegacy},treeRows={tree},graphics=G,
 active=function()return active end,revision=function()return revision end,version=function()return game end,
 validate=function(r)
  validated[#validated+1]=r
  local ok,why=Mapping.validate(r);assert(ok,why)
  return true
 end,
 donor={cell=function(_,ref)
  sourceReads=sourceReads+1
  local wanted=assert(expected[ref.hash],'exact guarded source hash is passed')
  eq(ref.game,game);eq(ref.tileset,'T');eq(ref.id,wanted.id);eq(ref.quadrant,wanted.q)
  eq(ref.hashOnly,true);eq(ref.monochrome,true);eq(ref.map,def)
  for k,v in pairs(sources)do eq(ref.sourceFiles[k],v,'exact source-file guard survives anchor copying')end
  return{}
 end},
 original=function(path,fileHash)
  reads=reads+1;eq(fileHash,hash('f'));eq(type(path),'string');return data
 end,
 warn=function(why)warnings[#warnings+1]=why end}
local roofs=Roofs.new(ctx)
eq(reads,0);eq(sourceReads,0,'static source/art reads stay lazy')
eq(validated[1]==north,false,'north anchoring validates a copy')
eq(validated[1].x,1);eq(validated[1].y,0);eq(validated[1].quadrant,1)
eq(validated[2].x,0);eq(validated[2].y,0);eq(validated[2].quadrant,0)
eq(north.y,-1);eq(left.x,-1);eq(left.y,-1,'validation never rewrites draw positions')
eq(legacy.y,1);eq(legacy.sourceY,nil,'ordinary roofs retain their original source positions')
local world={camera={x=-16,y=-16},viewW=112,viewH=96,daytime='DAY'}
roofs:map(world,def,0,0,1)
eq(#draws,6,'north-edge pieces include both bounded side extensions and the unchanged ordinary roof')
eq(sourceReads,6);eq(reads,6);eq(images,1,'one checked PNG data object shares its GPU texture')
eq(at(3,3),'roof','upper-left overhang renders in its own outside cell')
eq(at(0,0),'backing','transparent upper-left corners retain actual backing pixels')
eq(at(35,3),'roof','north y-1 artwork uses source row0 without moving its draw row')
eq(at(67,3),'roof','the rightmost north cell uses its exact block8/quadrant1 anchor')
eq(at(99,3),'roof','the second upper-right column draws from the same exact clamped map-edge anchor')
eq(at(35,35),'roof','ordinary in-map roofs are unchanged')
local cells=roofs:cells('red',def)
eq(cells.minY,-1);eq(cells.grid[-65537].x,-1);eq(cells.grid[-65537].y,-1)
eq(cells.grid[-65538].x,-2,'the second upper-left column retains its outside draw coordinate')
eq(cells.grid[-65531].x,5,'the second upper-right column retains its outside draw coordinate')
eq(cells.grid[-65535].x,1);eq(cells.grid[-65535].frontY,nil)
local actor={px=16,py=-8,sprite={frameWidth=16,frameHeight=16,anchorX=8,anchorY=16}}
surface={};local count=#draws
roofs:actor({def=def},actor,16,16,1,false,0,world)
eq(#draws-count,1,'the north overhang clips and redraws across an actor at the map edge')
eq(at(35,5),'roof');eq(at(32,5),'backing','roof alpha preserves actor pixels in unused corners')
local warmReads,warmSources,warmImages=reads,sourceReads,images
def.blocks={}
for i=1,80 do
 roofs:map(world,def,0,0,1)
 roofs:actor({def=def},actor,16,16,1,false,0,world)
end
eq(roofs:cells('red',def),cells,'warm draws return the same cached static expansion')
eq(reads,warmReads);eq(sourceReads,warmSources,'warm static draws do not rescan source blocks or imports');eq(images,warmImages)
def.blocks=originalBlocks
game='crystal';surface={};count=#draws
local treeCells=roofs:cells('crystal',def)
eq(treeCells.grid[-65536].treeCanopy,true);eq(treeCells.grid[-65536].frontY,32)
eq(treeCells.grid[65537].treeCanopy,nil,'ordinary Crystal roofs stay ordinary')
roofs:map(world,def,0,0,1);eq(#draws-count,2,'the original tree-canopy and ordinary-roof paths remain independent')
eq(at(19,3),'roof');eq(at(35,35),'roof')
eq(def.blocks,originalBlocks);eq(def.blocks[1],7,'no source block or collision data is modified')
active=false;count=#draws;roofs:map(world,def,0,0,1);eq(#draws,count,'Original theme hides overhangs')
active=true;roofs:dispose();eq(releases,images);count=#draws;roofs:map(world,def,0,0,1);eq(#draws,count)
roofs:dispose();eq(releases,images,'dispose releases each texture once')

local function single(row)
 local calls={source=0,asset=0,warnings=0}
 local c={rows={row},graphics=G,active=function()return true end,revision=function()return 1 end,
  version=function()return'red'end,validate=Mapping.validate,
  donor={cell=function()calls.source=calls.source+1;return{}end},
  original=function()calls.asset=calls.asset+1;return data end,
  warn=function(why)calls.warnings=calls.warnings+1;calls.last=why end}
 return c,calls
end
local invalid={
 function(r)r.sourceY=1;r.quadrant=2 end,
 function(r)r.sourceY=-1 end,
 function(r)r.sourceY=0.5 end,
 function(r)r.side='left' end,
 function(r)r.buildingY=1 end,
 function(r)r.x=-3;r.sourceX=0;r.quadrant=0 end,
 function(r)r.x=6;r.sourceX=3;r.quadrant=1 end,
 function(r)r.buildingW=0 end,
 function(r)r.buildingH=0 end,
 function(r)r.buildingW=3.5 end,
 function(r)r.sourceX=-1 end,
 function(r)r.sourceX=0.5 end,
 function(r)r.sourceHash='changed' end,
}
for _,change in ipairs(invalid)do
 local row=clone(north);change(row);local c,calls=single(row)
 eq(pcall(Roofs.new,c),false,'arbitrary source rows/columns, side anchoring and unbounded envelopes are rejected')
 eq(calls.source,0);eq(calls.asset,0,'invalid construction never reads source artwork')
end
local function skipped(row,map,why)
 local c,calls=single(row);local r=Roofs.new(c)
 local first=r:cells('red',map)
 eq(next(first.grid),nil,why);eq(calls.source,0);eq(calls.asset,0);eq(calls.warnings,1)
 eq(type(calls.last),'string')
 for i=1,80 do eq(r:cells('red',map),first)end
 eq(calls.warnings,1,'a failed source position is cached rather than warning every frame')
 r:dispose()
end
local wrongClamp=clone(left);wrongClamp.sourceX=1;wrongClamp.quadrant=1
skipped(wrongClamp,def,'a claimed upper-left source column must equal the real clamped column')
local wrongMap=clone(def);wrongMap.blocks[1]=8
skipped(clone(north),wrongMap,'the actual source block must still match its reviewed ID/quadrant')
local wide=clone(north);wide.buildingW=5
skipped(wide,def,'the complete north-edge building width must fit the real map')
local tall=clone(north);tall.buildingH=5
skipped(tall,def,'the complete north-edge building height must fit the real map')
eq(north.id,7);eq(north.quadrant,1);eq(north.sourceHash,hash('a'))
-- A Gen1 actor belongs to the current native Map; the adjacent Map object
-- owns the clinic roof. No town-tree templates or Gen2 world.maps exist here.
game='red'
local primary={id='ROUTE',tileset='T',width=2,height=2,blocks={9,10,9,10}}
local staticCtx={};for k,v in pairs(ctx)do staticCtx[k]=v end
staticCtx.rows={north};staticCtx.treeRows={}
local staticRoofs=Roofs.new(staticCtx)
local staticWorld={daytime='DAY',neighbors={{map={def=def},ox=0,oy=64}}}
local surfer={px=16,py=52,sprite={frameWidth=16,frameHeight=16,anchorX=8,anchorY=16}}
surface={};staticRoofs:actor({def=primary},surfer,0,0,1,false,0,staticWorld)
eq(at(19,52),'roof','a current-map actor is covered by its native neighbor north roof')
eq(at(16,52),'backing','neighbor roof transparency preserves the actor')
local warmStaticSources,warmStaticAssets=sourceReads,reads
for i=1,80 do
 surface={};staticRoofs:actor({def=primary},surfer,0,0,1,false,0,staticWorld)
 eq(at(19,52),'roof','warm static-neighbor actor redraw remains correct')
end
eq(sourceReads,warmStaticSources,'static-neighbor actors do not reread source rows')
eq(reads,warmStaticAssets,'static-neighbor actors do not reread native art')
staticRoofs:dispose()
local side=clone(north)
side.x,side.y,side.sourceX,side.sourceY=-1,1,0,nil
side.side='left';side.buildingX,side.buildingY,side.buildingW,side.buildingH=0,1,2,2
side.id,side.quadrant,side.sourceHash=7,2,hash('8')
expected[side.sourceHash]={id=7,q=2}
staticCtx.rows={side};staticRoofs=Roofs.new(staticCtx)
staticWorld.neighbors={{map={def=def},ox=64,oy=0}}
local crossing={px=52,py=20,sprite={frameWidth=16,frameHeight=16,anchorX=8,anchorY=16}}
surface={};staticRoofs:actor({def=primary},crossing,0,0,1,false,0,staticWorld)
eq(at(55,20),'roof','a bounded native side outside its source map covers an actor behind its front')
eq(at(62,20),'backing','native side corners retain actor pixels')
crossing.py=36;crossing.sprite.frameHeight=48;crossing.sprite.anchorY=48
surface={};staticRoofs:actor({def=primary},crossing,0,0,1,false,0,staticWorld)
eq(at(55,20),'backing','the same neighboring side respects its original physical front boundary')
staticRoofs:dispose()
print('static roof source-anchor checks: '..checks)
