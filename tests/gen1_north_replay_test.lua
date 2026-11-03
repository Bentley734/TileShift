local root=assert(arg[1])
local Adapter=assert(loadfile(root..'/lib/gen1.lua'))()
local Roofs=assert(loadfile(root..'/lib/roofs.lua'))()
local Mapping=assert(loadfile(root..'/lib/mapping.lua'))()
local checks=0
local function eq(a,b,why)checks=checks+1;assert(a==b,why or(tostring(a)..' ~= '..tostring(b)))end
local function fingerprint(c)return string.rep(c,64)end
local version,pass,active,dark='red','world',true,false
local sources,assets,images,draws,releases=0,0,0,0,0
local graphics={push=function()end,pop=function()end,setShader=function()end,setColor=function()end}
function graphics.newImage()
 images=images+1;return{setFilter=function()end,release=function()releases=releases+1 end}
end
function graphics.draw()draws=draws+1 end
local row={game='red',style='gen3',kind='original',status='reviewed',role='north-clinic-roof',evidence='Whole native north roof.',
 map='ROOT',tileset='T',id=7,quadrant=0,sourceHash=fingerprint('a'),x=0,y=-1,sourceY=0,
 buildingX=0,buildingY=0,buildingW=4,buildingH=3,
 asset='assets/original/north-test.png',assetFileHash=fingerprint('b')}
local def={id='ROOT',tileset='T',width=2,height=2,blocks={7,8,9,10}}
local neighborDef={id='NEIGHBOR',tileset='T',width=2,height=2,blocks={8,8,8,8}}
local mapPool={ROOT=def,NEIGHBOR=neighborDef}
local originalBlocks=def.blocks
local actualRoofs=Roofs.new({rows={row},validate=Mapping.validate,graphics=graphics,
 active=function()return active end,revision=function()return 1 end,version=function()return version end,
 donor={cell=function(_,ref)
  sources=sources+1;eq(ref.map,def);eq(ref.id,7);eq(ref.quadrant,0);eq(ref.hash,fingerprint('a'))
  return{}
 end},original=function(path,hash)
  assets=assets+1;eq(path,row.asset);eq(hash,row.assetFileHash);return{}
 end})
local calls={}
local roofBridge={map=function(_,view,source,ox,oy,s,mode)
 calls[#calls+1]={view=view,source=source,x=view.camera.x,y=view.camera.y,w=view.viewW,h=view.viewH,mode=mode}
 actualRoofs:map(view,source,ox,oy,s,mode)
end}
local native={border=0,window=0,neighbor=0}
local T={}
function T:drawBorderFill()native.border=native.border+1;return'border',nil,8 end
function T:drawWindow()native.window=native.window+1;return'window',nil,7 end
function T:drawMapOnly(cx,cy,w,h)
 native.neighbor=native.neighbor+1;self:drawWindow(cx,cy,w,h);return'neighbor',nil,9
end
function T.borderBlockFor()return false end
local original={};for k,v in pairs(T)do original[k]=v end
local function renderer(d,pool)
 local map={def=d}
 function map:blockAt(x,y)return self.def.blocks[y*self.def.width+x+1]or 0 end
 return setmetatable({map=map,data={maps=pool}},{__index=T})
end
local current=renderer(def,mapPool);local neighbor=renderer(neighborDef,mapPool)
local FX={darkWorld=function()return dark end,darkKey=function()return''end,pass=function()return pass end}
local cleanup=Adapter.install({renderer=T,palette=FX,graphics=graphics,roofs=roofBridge,
 version=function()return version end,active=function()return active end,replacements=function()return{}end})
local function border(w,h)
 local a,b,c=current:drawBorderFill(0,-16,w,h);eq(a,'border');eq(b,nil);eq(c,8)
end
local function body(self,cy,w,h)
 local a,b,c=self:drawMapOnly(0,cy,w or 96,h or 64);eq(a,'neighbor');eq(b,nil);eq(c,9)
end
local function replayCount()
 local n=0;for _,c in ipairs(calls)do if c.mode=='onlyBorder'then n=n+1 end end;return n
end
border(96,64);current:drawWindow(0,-16,96,64);body(neighbor,48)
eq(replayCount(),1,'a southern root keeps its north roof after the northern neighbor body')
local replay=calls[#calls]
eq(replay.source,def,'replay always uses the source root definition, never the neighbor')
eq(replay.x,0);eq(replay.y,-16);eq(replay.w,96);eq(replay.h,64)
eq(sources,1);eq(assets,1);eq(images,1)
local borderView=replay.view;local normalView=calls[1].view
eq(borderView==normalView,false,'the root border view is independent from the mutable neighbor window view')
local count=replayCount()
for i=1,100 do
 border(96,64);current:drawWindow(0,-16,96,64);body(neighbor,48)
 eq(calls[#calls].view,borderView,'warm replays reuse the same root viewport table')
end
eq(replayCount()-count,100);eq(sources,1,'warm replays never reread source imports')
eq(assets,1,'warm replays never reread artwork');eq(images,1,'warm replays retain the cached GPU texture')
eq(def.blocks,originalBlocks);eq(originalBlocks[1],7,'connected rendering does not modify source blocks')
local function noReplay(fn,why)
 local before=replayCount();fn();eq(replayCount(),before,why)
end
noReplay(function()body(current,-16)end,'the current root is not mistaken for a connected neighbor')
noReplay(function()body(renderer(neighborDef,{}),48)end,'unrelated source map pools cannot reuse the root viewport')
noReplay(function()body(neighbor,48,97,64)end,'an unrelated view width cannot trigger replay')
noReplay(function()body(neighbor,48,96,65)end,'an unrelated view height cannot trigger replay')
pass='sprites';noReplay(function()body(neighbor,48)end,'sprite/UI passes do not replay world roof pixels');pass='world'
noReplay(function()body(neighbor,-16)end,'same-origin bodies cannot overlap the outside north row')
noReplay(function()body(neighbor,64)end,'a neighbor ending exactly at y-16 does not overlap the roof row')
noReplay(function()body(neighbor,80)end,'a more distant north body cannot repaint this source root')
version='blue';noReplay(function()body(neighbor,48)end,'an old root viewport cannot cross game versions');version='red'
border(nil,nil);noReplay(function()body(neighbor,48)end,'border draws without a bounded viewport clear the old root')
dark=true;border(96,64);dark=false
noReplay(function()body(neighbor,48)end,'a hidden native cave border never arms a stale replay')
border(96,64);count=replayCount();body(neighbor,63)
eq(replayCount()-count,1,'a one-pixel overlap with the north row still replays its clipped roof')
eq(calls[#calls].view,borderView);eq(calls[#calls].y,-16)
local retained=T.drawMapOnly;cleanup()
for k,v in pairs(original)do eq(T[k],v,'cleanup restores every original renderer method')end
count=replayCount();neighbor:drawMapOnly(0,48,96,64);eq(replayCount(),count)
retained(neighbor,0,48,96,64);eq(replayCount(),count,'a later owner retaining our wrapper gets native behavior after disposal')
cleanup();actualRoofs:dispose();eq(releases,images)
eq(def.blocks,originalBlocks);eq(neighbor.data.maps,mapPool);eq(current.data.maps,mapPool)
print('Gen1 connected north-roof replay checks: '..checks)
