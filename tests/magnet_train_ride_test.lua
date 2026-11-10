local root=assert(arg[1]);local Theme=assert(loadfile(root..'/lib/magnet_train_ride.lua'))()
local count=0
local function eq(a,b,n)count=count+1;assert(a==b,(n or'mismatch')..': '..tostring(a)..' ~= '..tostring(b))end
local function image(w,h,pixel)
  local out={w=w,h=h,p={},released=false}
  function out:getDimensions()return self.w,self.h end
  function out:getPixel(x,y)assert(x>=0 and y>=0 and x<self.w and y<self.h);local p=self.p[y*self.w+x];if p then return p[1],p[2],p[3],p[4]end;return 0,0,0,0 end
  function out:setPixel(x,y,r,g,b,a)assert(x>=0 and y>=0 and x<self.w and y<self.h);self.p[y*self.w+x]={r,g,b,a}end
  function out:paste(src,dx,dy,sx,sy,pw,ph)for y=0,ph-1 do for x=0,pw-1 do self:setPixel(dx+x,dy+y,src:getPixel(sx+x,sy+y))end end end
  function out:release()eq(self.released,false,'release once');self.released=true end
  if pixel then for y=0,h-1 do for x=0,w-1 do out:setPixel(x,y,pixel(x,y))end end end
  return out
end
local function fixture()
  local f={style='original',game='crystal',revision=1,phase=1,active=true,reads=0,allocs=0,textures=0,warnings=0,trees={},calls={},nativeCalls=0,quads=0,shader='incoming-palette',color='incoming-color',stack={}}
  local catalog=assert(loadfile(root..'/lib/magnet_train_ride_catalog.lua'))();local host=catalog.hosts.crystal
  local function copy(a)local b={};for i,v in ipairs(a)do b[i]=v end;return b end
  local gfx={bgTiles=copy(host.bgTiles),tilemap=copy(host.tilemap)}
  local ts={image=host.sheet};local data={gen2Field={magnetTrain=gfx},gen2Tilesets={TILESET_TRAIN_STATION=ts}}
  local Class={}
  function Class:backgrounds()return'native-base','native-overlay'end
  function Class:drawPanel()f.nativeCalls=f.nativeCalls+1;return'native-panel'end
  function Class:drawBands(im)f.calls[#f.calls+1]={kind='bands',image=im,position=self.ride.position,shader=f.shader}end
  function Class:drawPlayer()f.calls[#f.calls+1]={kind='player'};f.shader='native-player-shader';f.color='native-player-color'end
  function Class:backdrop()return{1,2,3}end
  function Class:finish()f.finishes=(f.finishes or 0)+1;self.finished=true;return'finished'end
  f.Class=Class;f.nativePanel=Class.drawPanel;f.nativeBands=Class.drawBands;f.nativeBackgrounds=Class.backgrounds
  f.scene=setmetatable({data=data,game={data=data},tileset=ts,ride={bgTiles=gfx.bgTiles,fgTilemap=gfx.tilemap,scx=72,position=64,offset=166},bgCanvas='engine-owned',bgOverlayCanvas='engine-overlay',sheet='engine-sheet'}, {__index=Class})
  local function tile(r,g,b)return image(16,16,function()return r,g,b,1 end)end
  f.edge=tile(.2,.2,.2)
  f.tree=image(32,32,function(x,y)if x>=2 and x<=29 then return .1,.8,.2,1 end;return 0,0,0,0 end)
  f.sheet=image(host.width,host.height,function(x,y)local v=((x+2*y)%4)/3;return v,v,v,1 end)
  f.ctx={catalog=catalog,require=function()return Class end,style=function()return f.style end,
    game=function()return f.scene.game end,version=function()return f.game end,active=function()return f.active end,
    revision=function()return f.revision end,phase=function()return f.phase end,warn=function()f.warnings=f.warnings+1 end,
    source=function(_,path)f.reads=f.reads+1;if f.missing then return nil end;return host.files[path]end,
    hash=function(bytes)return bytes end,
    sourceSheet=function()return image(host.width,host.height,function(x,y)return f.sheet:getPixel(x,y)end)end,
    newData=function(w,h)f.allocs=f.allocs+1;return image(w,h)end,
    native=function(ref)if ref==catalog.ground then return tile(.3,.7,.2)end;return image(16,16,function(x,y)return x/16,y/16,.5,1 end)end,
    compose=function()return{under=f.edge}end,
    asset=function(path)if path==catalog.rails[1].asset then return tile(.7,.4,.1)end;return tile(.8,.5,.2)end,
    tree=function(key)f.trees[#f.trees+1]=key;return f.tree end,
    texture=function(data)f.textures=f.textures+1;return image(256,144,function(x,y)return data:getPixel(x,y)end)end,
    quad=function(...)
      f.quads=f.quads+1;local q={viewport={...}}
      function q:setViewport(...)self.viewport={...}end
      function q:release()eq(self.released,nil,'quad released once');self.released=true end
      return q
    end,
    graphics={setColor=function(...)f.color={...}end,rectangle=function()end,
      push=function(mode)eq(mode,'all');f.stack[#f.stack+1]={f.shader,f.color}end,
      pop=function()local old=table.remove(f.stack);f.shader,f.color=old[1],old[2]end,
      setShader=function(value)f.shader=value end,
      draw=function(im,q,x,y)f.calls[#f.calls+1]={kind='scenery',image=im,viewport=copy(q.viewport),x=x,y=y,shader=f.shader}end}}
  f.theme=Theme.install(f.ctx)
  function f:render()
    self.calls={};local result=self.scene:drawPanel();if result then return result end
    local scenery,train,priority
    for _,call in ipairs(self.calls)do
      if call.kind=='scenery'then scenery=call.image
      elseif call.kind=='bands'then if not train then train=call.image else priority=call.image end end
    end
    return train,priority,scenery
  end
  return f
end
local f=fixture();eq(f:render(),'native-panel');eq(f.reads,0);eq(f.allocs,0);eq(f.textures,0)
f.game='red';f.style='gen3';eq(f:render(),'native-panel');eq(f.reads,0);f.game='crystal'
local body,overlay,scenery=f:render();eq(f.theme.prepared,1);eq(f.theme.builds,4);eq(f.textures,6);eq(f.quads,1);eq(#f.trees,16)
eq(f.Class.backgrounds,f.nativeBackgrounds);eq(f.Class.drawBands,f.nativeBands,'native train bands method untouched')
eq(f.scene:backgrounds(),'native-base','native backgrounds remain untouched')
eq(f.trees[1],'crystal:MAGNET_TRAIN:big_trees:0:0');eq(f.trees[16],'crystal:MAGNET_TRAIN:big_trees:224:112')
eq(f.scene.bgCanvas,'engine-owned');eq(f.scene.bgOverlayCanvas,'engine-overlay');eq(f.scene.sheet,'engine-sheet')
eq(#f.calls,4);eq(f.calls[1].kind,'scenery');eq(f.calls[1].viewport[1],72,'current latched world offset, not advanced offset*2')
eq(f.shader,'incoming-palette','incoming palette shader restored');eq(f.color,'incoming-color','incoming GPU color restored');eq(#f.stack,0);eq(f.calls[1].shader,nil,'truecolor scenery bypasses incoming palette shader');eq(f.calls[2].shader,nil,'body remains truecolor');eq(f.calls[4].shader,nil,'native player shader cannot recolor hull');
eq(f.calls[2].image,body);eq(f.calls[2].position,64);eq(f.calls[3].kind,'player');eq(f.calls[4].image,overlay)
local host=f.ctx.catalog.hosts.crystal;local mask,retained=0,0
for y=0,143 do for x=0,255 do
  local inBody=y>=48 and y<80 and x<160
  local _,_,_,a=body:getPixel(x,y);local _,_,_,oa=overlay:getPixel(x,y)
  if inBody then
    local row,col=math.floor(y/8),math.floor(x/8);local tid=host.tilemap[(row-6)*20+col+1]
    local raw=f.sheet:getPixel(tid%16*8+x%8,math.floor(tid/16)*8+y%8)
    local n=f.ctx.catalog.exterior[y-47]
    if x<n or x>=160-n then
      mask=mask+1;eq(a,0,'true transparent exterior');eq(oa,0,'no moving rail painted by priority overlay')
    else
      retained=retained+1;eq(a,1,'all native body and window base remains opaque')
      local colors=(y>=64 and y<72 and x>=56 and x<104)and f.ctx.catalog.gold or f.ctx.catalog.metal
      local c=colors[math.floor((1-raw)*3+.5)+1];local r,g,b=body:getPixel(x,y);eq(r,c[1]/255);eq(g,c[2]/255);eq(b,c[3]/255)
      eq(oa,raw==1 and 0 or 1,'source ride-specific window OAM priority')
    end
  else eq(a,0);eq(oa,0,'nothing outside the hull can drag scenery with train')end
  local _,_,_,sa=scenery:getPixel(x,y);eq(sa,1,'whole separate scenery layer remains opaque')
end end
eq(mask,258);eq(retained,4862)
for y=48,79 do for x=0,255 do local r=scenery:getPixel(x,y);eq(r,y<64 and .7 or .8,'rails remain whole and unpainted by body')end end
for y=80,95 do for x=0,255 do local r,g,b=scenery:getPixel(x,y);eq(r,x%16/16);eq(g,y%16/16);eq(b,.5)end end
for _,y in ipairs({47,95})do local a,b,c,d=scenery:getPixel(0,y);if y==47 then for x=1,255 do local r,g,bb,aa=scenery:getPixel(x,y);eq(r,a);eq(g,b);eq(bb,c);eq(aa,d)end end end
local reads,allocs,textureCount,quadCount=f.reads,f.allocs,f.textures,f.quads
for i=1,100 do f.phase=(i%4)+1;local train,priority=f:render();eq(train,body,'body shared across all4 wind frames');eq(priority,overlay)end
eq(f.reads,reads);eq(f.allocs,allocs);eq(f.textures,textureCount);eq(f.quads,quadCount);eq(f.theme.prepared,1,'warm frames never rebake')
f.scene.ride.scx=76;f:render();eq(f.calls[1].viewport[1],76,'scenery advances4px during native hold');eq(f.calls[2].position,64,'holding train does not advance')
f.scene.ride.scx=252;f:render();eq(f.calls[1].viewport[1],252);eq(f.calls[1].viewport[3],4);eq(f.calls[2].kind,'scenery');eq(f.calls[2].x,4);eq(f.calls[2].viewport[3],156,'world wrapping stays inside160px panel')
f.revision=2;local updated=f:render();eq(body.released,true);eq(scenery.released,true);eq(updated==body,false);eq(f.theme.prepared,2)
f.style='original';eq(f:render(),'native-panel');eq(updated.released,true)
local cold=f.reads;f:render();eq(f.reads,cold,'cold Original delegates entire panel without themed reads')
f.style='gen3';local final=f:render();local finalReads,finalBakes=f.reads,f.theme.builds;eq(f.scene:finish(),'finished');eq(f.finishes,1)
eq(f:render(),final,'last completed frame uses existing textures');eq(f.reads,finalReads);eq(f.theme.builds,finalBakes)
local owned=f.Class.drawPanel;local later=function(scene)return owned(scene)end;f.Class.drawPanel=later
f.theme:dispose();eq(f.Class.drawPanel,later,'later wrapper retained');eq(f:render(),'native-panel');eq(f.scene:finish(),'finished');eq(f.finishes,2)
eq(f.tree.released,false);eq(f.edge.released,false)
local bad=fixture();bad.style='gen3';bad.missing=true;eq(bad:render(),'native-panel');local attempted=bad.reads
for _=1,10 do eq(bad:render(),'native-panel')end;eq(bad.reads,attempted);eq(bad.warnings,1,'failed source is memoized')
bad.missing=false;bad.revision=2;eq(bad:render()=='native-panel',false);bad.active=false;eq(bad:render(),'native-panel');bad.theme:dispose()
local changed=fixture();changed.style='gen3';changed.scene.ride.fgTilemap[1]=999
eq(changed:render(),'native-panel');eq(changed.reads,0,'reject changed live source before reading donors');changed.theme:dispose()
local foreign=fixture();foreign.style='gen3';foreign.ctx.game=function()return{data=foreign.scene.data}end
eq(foreign:render(),'native-panel');eq(foreign.reads,0,'reject different active game');foreign.theme:dispose()
local switched=fixture();switched.style='gen3';local stale=switched:render();local priorReads=switched.reads
switched.ctx.game=function()return{data=switched.scene.data}end
eq(switched:render(),'native-panel','warm cache cannot survive active-game identity change');eq(switched.reads,priorReads);eq(stale.released,true);switched.theme:dispose()
local unavailable=0;local silent=Theme.install({catalog={},style=function()return'gen3'end,version=function()return'crystal'end,active=function()return true end,
  require=function()error('old engine')end,warn=function()unavailable=unavailable+1 end})
eq(unavailable,1);silent:dispose();silent:dispose();f.theme:dispose()
print('magnet_train_ride_test: '..count..' checks')
