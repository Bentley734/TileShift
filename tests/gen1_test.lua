-- Asymmetric source crops exercise the same 8px span contract as TileRenderer.
local root=assert(arg and arg[1], 'TileShift directory required')
local Adapter=assert(loadfile(root..'/lib/gen1.lua'))()
local count=0
local function eq(a,b,message)
  count=count+1
  assert(a==b,(message or 'mismatch')..': '..tostring(a)..' ~= '..tostring(b))
end
local function data(label,w,h)
  return {label=label,getDimensions=function()return w or 32,h or 32 end,
    sample=function(_,x,y)return label..':'..x..','..y end}
end
local drawCalls, marks, stripCalls, redrawCalls, nativeCalls={},{},{},{},{}
local shader,colors,clip='source-shader',{.2,.3,.4,.5},{1,2,3,4}
local stack,created,quadCount={}, {},0
local G={}
function G.push(mode)
  eq(mode,'all');stack[#stack+1]={shader=shader,colors=colors,clip=clip}
end
function G.pop()
  local old=assert(table.remove(stack));shader,colors,clip=old.shader,old.colors,old.clip
end
function G.setShader(value)shader=value end
function G.setColor(...)colors={...}end
function G.newImage(d)
  local im={source=d,getDimensions=d.getDimensions,filter=nil,
    setFilter=function(self,a,b)self.filter={a,b}end,
    release=function(self)self.released=true;self.releaseCount=(self.releaseCount or 0)+1 end}
  created[#created+1]=im;return im
end
function G.newQuad(sx,sy,w,h,iw,ih)
  quadCount=quadCount+1;return {sx=sx,sy=sy,w=w,h=h,iw=iw,ih=ih}
end
function G.draw(im,q,x,y)
  if im.source and im.source.fail then error('fixture drawing failure') end
  drawCalls[#drawCalls+1]={image=im,quad=q,x=x,y=y,shader=shader,
    pixel=(im.source or im):sample(q.sx,q.sy)}
end
local FX={markTrueColor=function(x,y,w,h)marks[#marks+1]={x=x,y=y,w=w,h=h}end}
local T={}
function T:drawWindow(cx,cy,w,h)
  nativeCalls[#nativeCalls+1]={kind='window',self=self,cx=cx,cy=cy,w=w,h=h}
  if self.failNative then error('fixture native failure')end
  return 'native-window',nil,7
end
function T:drawBorderFill(cx,cy,w,h)
  nativeCalls[#nativeCalls+1]={kind='border',self=self,cx=cx,cy=cy,w=w,h=h}
  return 'native-border',nil,8
end
function T.borderBlockFor(map)
  if map.black then return false end
  return map.def.borderBlock
end
-- This is the native TileRenderer.eachStripSpan geometry, including negative
-- coordinates and source offsets for crops that start inside an 8px tile.
function T.eachStripSpan(x0,y0,x1,y1,fn)
  for ty=math.floor(y0/8),math.floor((y1-1)/8) do
    local top,bottom=math.max(y0,ty*8),math.min(y1,ty*8+8)
    for tx=math.floor(x0/8),math.floor((x1-1)/8) do
      local left,right=math.max(x0,tx*8),math.min(x1,tx*8+8)
      fn(tx,ty,left,top,left-tx*8,top-ty*8,right-left,bottom-top)
    end
  end
end
function T:drawStripRaw(x0,y0,x1,y1,cx,cy)
  stripCalls[#stripCalls+1]={x0=x0,y0=y0,x1=x1,y1=y1,cx=cx,cy=cy}
  return 'native-strip'
end
function T:markStripRedraw(x0,y0,x1,y1,cx,cy,ramp)
  redrawCalls[#redrawCalls+1]={x0=x0,y0=y0,x1=x1,y1=y1,cx=cx,cy=cy,ramp=ramp}
  return 'native-redraw'
end
local function blocks()
  local out={}
  for id=0,8 do out[id+1]={};for i=1,16 do out[id+1][i]=i end end
  out[6][15]=99 -- source block 5, bottom-right quadrant, player feet tile
  return out
end
local ts={blocks=blocks(),grassTile=99}
local def={id='MAIN',tileset='TEST',width=2,height=2,blocks={4,5,6,7},borderBlock=8}
local map={def=def,tileset=ts}
function map:blockAt(bx,by)
  if bx<0 or by<0 or bx>=self.def.width or by>=self.def.height then return self.def.borderBlock end
  return self.def.blocks[by*self.def.width+bx+1]
end
local sourceBlocks,sourceTileBlocks=def.blocks,ts.blocks
local renderer=setmetatable({map=map},{__index=T})
local bg,bg1,bg2=data('background'),data('background-1'),data('background-2')
local fg,fg1,fg2=data('foreground'),data('foreground-1'),data('foreground-2')
local art={
  [4]={image=bg,foreground=fg,frames={bg1,bg2},foregroundFrames={fg1,fg2},
    coverage={[3]=true},period=.2},
  [5]={image=data('grass-partial'),coverage={[0]=true}},
  [6]=data('full-block'),
  [8]={image=data('border'),foreground=data('border-foreground'),coverage={[3]=true}},
}
local time,warnings=.35,{}
local originals={};for key,value in pairs(T)do originals[key]=value end
local close=Adapter.install({renderer=T,palette=FX,graphics=G,version=function()return 'red'end,
  time=function()return time end,warn=function(w)warnings[#warnings+1]=w end,
  replacements=function(version,tileset,actual)
    eq(version,'red');eq(tileset,actual.tileset)
    if actual.id=='NEIGHBOR' then return {[4]={image=data('neighbor'),coverage={[1]=true}}} end
    eq(actual,def);return art
  end})
local nativeShader,nativeColor,nativeClip=shader,colors,clip
local function reset()
  drawCalls,marks,stripCalls,redrawCalls,nativeCalls={},{},{},{},{}
end
local function stateRestored()
  eq(shader,nativeShader,'shader restored');eq(colors,nativeColor,'color restored')
  eq(clip,nativeClip,'clip restored');eq(#stack,0,'graphics stack balanced')
end

-- Fractional negative camera must use native floor alignment, independently on
-- X and Y. Distinct source coordinates detect transposed/flipped crops.
local r1,r2,r3=renderer:drawWindow(-3.7,-5.2,64,64)
eq(r1,'native-window');eq(r2,nil);eq(r3,7)
eq(#nativeCalls,1);eq(#drawCalls,3);eq(#marks,3)
local first=drawCalls[1]
eq(first.image.source,bg2,'donor animation frame')
eq(first.quad.sx,16);eq(first.quad.sy,16);eq(first.quad.w,16);eq(first.quad.h,16)
eq(first.pixel,'background-2:16,16','asymmetric source position')
eq(first.x,20);eq(first.y,22);eq(first.shader,nil,'donor full color')
eq(marks[1].x,20);eq(marks[1].y,22);eq(marks[1].w,16);eq(marks[1].h,16)
eq(drawCalls[2].x,36);eq(drawCalls[2].y,6)
eq(drawCalls[2].quad.sx,0);eq(drawCalls[2].quad.sy,0)
eq(drawCalls[3].quad.w,32,'legacy fullblock width');eq(drawCalls[3].quad.h,32)
eq(marks[3].w,32,'legacy fullblock color mask')
stateRestored()
local allocated=quadCount
reset();renderer:drawWindow(-3.7,-5.2,64,64)
eq(quadCount,allocated,'repeated background draws reuse quads')
reset();renderer:drawWindow(32,0,32,32)
eq(#drawCalls,1,'exact viewport edge does not include next block')
eq(drawCalls[1].image.source,art[5].image)
reset();renderer:drawWindow(0,0)
eq(#drawCalls,3,'nil viewport draws map body')
eq(def.blocks,sourceBlocks);eq(ts.blocks,sourceTileBlocks)
eq(def.blocks[1],4);eq(ts.blocks[6][15],99,'source grass identity intact')

-- Four blocks and quadrants meet inside this strip. Only the reviewed cell
-- suppresses its native span; uncovered neighbor grass and seams stay native.
reset();renderer:drawStripRaw(28,30,36,34,-3.7,-5.2)
eq(#drawCalls,1,'one donor foreground span')
eq(#stripCalls,2,'uncovered spans retain native rendering')
first=drawCalls[1]
eq(first.image.source,fg2,'foreground animates independently')
eq(first.pixel,'foreground-2:28,30','foreground source offset is not block origin')
eq(first.quad.sx,28);eq(first.quad.sy,30);eq(first.quad.w,4);eq(first.quad.h,2)
eq(first.x,32);eq(first.y,36)
eq(stripCalls[1].x0,32);eq(stripCalls[1].y0,30)
eq(stripCalls[1].x1,36);eq(stripCalls[1].y1,32)
eq(stripCalls[2].x0,32);eq(stripCalls[2].y0,32)
stateRestored()
allocated=quadCount
renderer:drawStripRaw(28,30,36,34,-3.7,-5.2)
eq(quadCount,allocated,'repeated foreground crops reuse quads')
local ramp={10,20,30,40}
renderer:markStripRedraw(28,30,36,34,-3.7,-5.2,ramp)
eq(#redrawCalls,2,'source palette redraw excludes reviewed cells')
eq(redrawCalls[1].x0,32);eq(redrawCalls[1].y0,30);eq(redrawCalls[1].ramp,ramp)
eq(redrawCalls[2].x0,32);eq(redrawCalls[2].y0,32)

-- Negative world spans use positive modulo source coordinates in border art.
reset();renderer:drawStripRaw(-5,-3,3,2,-2.7,-8.1)
eq(#drawCalls,1);eq(#stripCalls,3)
first=drawCalls[1]
eq(first.pixel,'border-foreground:27,29')
eq(first.quad.sx,27);eq(first.quad.sy,29);eq(first.quad.w,5);eq(first.quad.h,3)
eq(first.x,-2);eq(first.y,6)
eq(marks[1].x,-2);eq(marks[1].y,6);eq(marks[1].w,5);eq(marks[1].h,3)
reset();r1,r2,r3=renderer:drawBorderFill(-4,-6,40,40)
eq(r1,'native-border');eq(r2,nil);eq(r3,8)
eq(#drawCalls,5,'border replaces outside blocks only')
eq(drawCalls[1].pixel,'border:16,16');eq(drawCalls[1].x,-12);eq(drawCalls[1].y,-10)
for _,mark in ipairs(marks)do eq(mark.w,16);eq(mark.h,16)end
reset();map.black=true;renderer:drawBorderFill(-4,-6,40,40)
eq(#drawCalls,0,'black void fill never falls back to header border')
map.black=nil

-- Connected renderers use their own map-local coordinate system and data.
local neighborDef={id='NEIGHBOR',tileset='OTHER',width=1,height=2,blocks={4,7},borderBlock=8}
local neighborMap={def=neighborDef,tileset=ts,blockAt=map.blockAt}
local neighbor=setmetatable({map=neighborMap},{__index=T})
reset();neighbor:drawWindow(-34,0,64,32)
eq(#drawCalls,1);eq(drawCalls[1].pixel,'neighbor:16,0')
eq(drawCalls[1].x,50);eq(drawCalls[1].y,0)
eq(drawCalls[1].quad.w,16);eq(marks[1].w,16)

-- Grass outside a reviewed quadrant is harmless; covering source grass needs
-- an explicit alpha foreground, including the native palette redraw path.
art[5].coverage={[3]=true}
reset();renderer:drawWindow(32,0,32,32);renderer:drawWindow(32,0,32,32)
eq(#drawCalls,0,'unsafe grass replacement rejected')
eq(#warnings,1,'unsafe foreground warning deduplicated')
renderer:drawStripRaw(48,24,64,32,0,0)
eq(#stripCalls,2,'rejected grass stays native over sprite feet')
renderer:markStripRedraw(48,24,64,32,0,0,ramp)
eq(#redrawCalls,2,'rejected grass keeps source palette redraw')
art[5].foregroundFrames={data('grass-alpha-1'),data('grass-alpha-2')}
reset();renderer:drawStripRaw(48,24,64,32,0,0)
eq(#drawCalls,2,'explicit foreground frames allow grass')
eq(drawCalls[1].pixel,'grass-alpha-2:16,24')
eq(#stripCalls,0)

-- Without foreground, a safe non-grass replacement must not redraw an opaque
-- background rectangle over an actor, including animated background records.
art[4].foreground=nil;art[4].foregroundFrames=nil
reset();renderer:drawStripRaw(16,24,32,32,0,0)
eq(#drawCalls,0,'background frames are not used as a foreground')
eq(#stripCalls,0,'covered native strip remains suppressed')
art[4].foreground=fg
art[4].coverage={[0]=true,[3]=true}
reset();renderer:drawWindow(0,0,32,32)
eq(#drawCalls,2);eq(#marks,2)
eq(marks[1].x,0);eq(marks[1].y,0);eq(marks[1].w,16)
eq(marks[2].x,16);eq(marks[2].y,16);eq(marks[2].w,16)

-- A donor drawing or validation failure must not leave the source shader,
-- color, scissor or graphics stack changed.
bg2.fail=true
reset();local ok,err=pcall(renderer.drawWindow,renderer,0,0,32,32)
eq(ok,false);eq(tostring(err):find('fixture drawing failure',1,true)~=nil,true)
stateRestored();bg2.fail=nil
local saved=art[4]
art[4]={image=data('bad-size',16,32)}
ok,err=pcall(renderer.drawWindow,renderer,0,0,32,32)
eq(ok,false);eq(tostring(err):find('must be 32x32',1,true)~=nil,true)
stateRestored();art[4]=saved
renderer.failNative=true
ok,err=pcall(renderer.drawWindow,renderer,0,0,32,32)
eq(ok,false);eq(tostring(err):find('fixture native failure',1,true)~=nil,true)
stateRestored();renderer.failNative=nil

local borrowed=data('borrowed')
function borrowed:typeOf(name)return name=='Texture'end
function borrowed:setFilter()end
function borrowed:release()self.released=true end
art[6]=borrowed
reset();renderer:drawWindow(0,32,32,32)
eq(drawCalls[1].image,borrowed,'borrowed GPU texture accepted')
local staleWrapper=T.drawWindow
local later=function()return 'later wrapper'end
T.drawWindow=later
close();close()
eq(T.drawWindow,later,'cleanup preserves another mod wrapper')
eq(T.drawBorderFill,originals.drawBorderFill)
eq(T.drawStripRaw,originals.drawStripRaw)
eq(T.markStripRedraw,originals.markStripRedraw)
eq(borrowed.released,nil,'borrowed GPU texture not released')
for _,im in ipairs(created)do eq(im.released,true,'owned texture released')end
reset();eq(staleWrapper(renderer,0,0,32,32),'native-window')
eq(#drawCalls,0,'old wrapper becomes harmless after cleanup')
eq(#nativeCalls,1)
eq(def.blocks,sourceBlocks);eq(ts.blocks,sourceTileBlocks)
eq(ts.blocks[6][15],99)

-- Match the donor's fixed-step phase: phase1 lasts through tick16, then tick17
-- changes to phase2. Foreground and background use the same explicit offset.
T.drawWindow=originals.drawWindow
local phase1,phase2=data('phase-1'),data('phase-2')
local front1,front2=data('phase-front-1'),data('phase-front-2')
local phaseArt={image=phase1,foreground=front1,frames={phase1,phase2},
  foregroundFrames={front1,front2},period=16/60,offset=1/60,coverage={[3]=true}}
local owner,phaseTime=true,0
local firstOwned=#created+1
local phaseClose=Adapter.install({renderer=T,palette=FX,graphics=G,version='red',
  time=function()return phaseTime end,active=function()return owner end,
  replacements=function()
    assert(owner,'disabled renderer must not request replacements')
    return {[4]=phaseArt}
  end})
for _,sample in ipairs({{-1,1},{0,1},{1/60,1},{16/60,1},{17/60,2},{32/60,2},{33/60,1}}) do
  phaseTime=sample[1]
  reset();renderer:drawWindow(0,0,32,32)
  eq(#drawCalls,1)
  eq(drawCalls[1].image.source,sample[2]==1 and phase1 or phase2,
    'background fixed-step phase at '..phaseTime)
  reset();renderer:drawStripRaw(16,24,32,32,0,0)
  eq(#drawCalls,2)
  eq(drawCalls[1].image.source,sample[2]==1 and front1 or front2,
    'foreground fixed-step phase at '..phaseTime)
  stateRestored()
end

-- Disabling through the manager may leave another mod's wrapper above ours.
-- That chain remains installed; our retained link frees actual owned textures
-- and forwards native results without drawing any art or collecting masks.
local retained=T.drawWindow
local chainCalls=0
local chained=function(self,...)
  chainCalls=chainCalls+1
  return retained(self,...)
end
T.drawWindow=chained
owner=false
reset();r1,r2,r3=renderer:drawWindow(0,0,32,32)
eq(r1,'native-window');eq(r2,nil);eq(r3,7)
eq(#nativeCalls,1);eq(#drawCalls,0,'disabled ownership draws no donor art')
eq(#marks,0,'disabled ownership collects no donor masks')
eq(chainCalls,1);eq(T.drawWindow,chained,'later wrapper chain is preserved')
eq(T.drawBorderFill,originals.drawBorderFill)
eq(T.drawStripRaw,originals.drawStripRaw)
eq(T.markStripRedraw,originals.markStripRedraw)
eq(#created>=firstOwned,true,'owned GPU images actually existed')
for i=firstOwned,#created do
  eq(created[i].released,true,'disable releases owned GPU image')
  eq(created[i].releaseCount,1,'disable releases each owned GPU image once')
end
phaseClose();phaseClose()
reset();renderer:drawWindow(0,0,32,32)
eq(#drawCalls,0);eq(#marks,0);eq(chainCalls,2)
for i=firstOwned,#created do eq(created[i].releaseCount,1,'cleanup remains idempotent')end
owner=true
reset();renderer:drawWindow(0,0,32,32)
eq(#drawCalls,0,'closed retained link cannot reactivate released textures')
stateRestored()
print('PASS Gen 1 graphics adapter: '..count..' assertions')
return count
