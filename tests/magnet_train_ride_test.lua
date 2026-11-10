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
  local f={style='original',game='crystal',revision=1,phase=1,active=true,reads=0,allocs=0,textures=0,warnings=0,trees={},nativeCalls=0}
  local catalog=assert(loadfile(root..'/lib/magnet_train_ride_catalog.lua'))()
  local host=catalog.hosts.crystal
  local function copy(a)local b={};for i,v in ipairs(a)do b[i]=v end;return b end
  local gfx={bgTiles=copy(host.bgTiles),tilemap=copy(host.tilemap)}
  local ts={image=host.sheet};local data={gen2Field={magnetTrain=gfx},gen2Tilesets={TILESET_TRAIN_STATION=ts}}
  local Class={}
  function Class:backgrounds()f.nativeCalls=f.nativeCalls+1;return'native-base','native-overlay'end
  function Class:backdrop()return{1,2,3}end
  function Class:finish()f.finishes=(f.finishes or 0)+1;self.finished=true;return'finished'end
  f.Class=Class;f.native=Class.backgrounds
  f.scene=setmetatable({data=data,game={data=data},tileset=ts,ride={bgTiles=gfx.bgTiles,fgTilemap=gfx.tilemap},bgCanvas='engine-owned',bgOverlayCanvas='engine-overlay',sheet='engine-sheet'}, {__index=Class})
  local function tile(r,g,b)return image(16,16,function()return r,g,b,1 end)end
  f.edge=tile(.2,.2,.2)
  f.tree=image(32,32,function(x,y)if x>=2 and x<=29 then return .1,.8,.2,1 end;return 0,0,0,0 end)
  f.sheet=image(host.width,host.height,function(x,y)local v=((x+2*y)%4)/3;return v,v,v,1 end)
  f.ctx={catalog=catalog,require=function()return Class end,style=function()return f.style end,
    game=function()return f.scene.game end,version=function()return f.game end,active=function()return f.active end,revision=function()return f.revision end,
    phase=function()return f.phase end,warn=function()f.warnings=f.warnings+1 end,
    source=function(_,path)f.reads=f.reads+1;if f.missing then return nil end;return host.files[path]end,
    hash=function(bytes)return bytes end,
    sourceSheet=function()return image(host.width,host.height,function(x,y)return f.sheet:getPixel(x,y)end)end,
    newData=function(w,h)f.allocs=f.allocs+1;return image(w,h)end,
    native=function(ref)if ref==catalog.ground then return tile(.3,.7,.2)end;return tile(.5,.5,.5)end,
    compose=function()return{under=f.edge}end,
    asset=function(path)if path==catalog.rails[1].asset then return tile(.7,.4,.1)end;return tile(.8,.5,.2)end,
    tree=function(key)f.trees[#f.trees+1]=key;return f.tree end,
    texture=function(data)f.textures=f.textures+1;return image(256,144,function(x,y)return data:getPixel(x,y)end)end}
  f.theme=Theme.install(f.ctx)
  return f
end
local f=fixture();eq(f.scene:backgrounds(),'native-base');eq(f.reads,0);eq(f.allocs,0);eq(f.textures,0)
f.game='red';f.style='gen3';eq(f.scene:backgrounds(),'native-base');eq(f.reads,0);f.game='crystal'
local base,overlay=f.scene:backgrounds();eq(f.theme.prepared,1);eq(f.theme.builds,4);eq(f.textures,8);eq(#f.trees,16)
eq(f.trees[1],'crystal:MAGNET_TRAIN:big_trees:0:0');eq(f.trees[16],'crystal:MAGNET_TRAIN:big_trees:224:112')
eq(f.scene.bgCanvas,'engine-owned');eq(f.scene.bgOverlayCanvas,'engine-overlay');eq(f.scene.sheet,'engine-sheet')
local host=f.ctx.catalog.hosts.crystal;local mask=0;local retained=0
for y=0,143 do for x=0,255 do
  local row,col=math.floor(y/8),math.floor(x/8)
  local tid=(row>=6 and row<10 and col<20)and host.tilemap[(row-6)*20+col+1]or host.bgTiles[row*2+col%2+1]
  local raw=f.sheet:getPixel(tid%16*8+x%8,math.floor(tid/16)*8+y%8)
  local _,_,_,alpha=overlay:getPixel(x,y);eq(alpha,raw==1 and 0 or 1,'native OAM shade aperture')
  if y>=48 and y<80 and x<160 then
    local n=f.ctx.catalog.exterior[y-47];local r,g,b=base:getPixel(x,y)
    if x<n or x>=160-n then mask=mask+1;eq(r,y<64 and .7 or .8,'rail visible outside silhouette')
    else
      retained=retained+1
      local colors=(y>=64 and y<72 and x>=56 and x<104)and f.ctx.catalog.gold or f.ctx.catalog.metal
      local c=colors[math.floor((1-raw)*3+.5)+1];eq(r,c[1]/255);eq(g,c[2]/255);eq(b,c[3]/255)
    end
  end
end end
eq(mask,258);eq(retained,4862)
for _,y in ipairs({47,95})do local a,b,c,d=base:getPixel(0,y);for x=1,255 do local r,g,bb,aa=base:getPixel(x,y);eq(r,a);eq(g,b);eq(bb,c);eq(aa,d)end end
local reads,allocs,textureCount=f.reads,f.allocs,f.textures
local frames={base};for i=1,100 do f.phase=(i%4)+1;frames[f.phase]=f.scene:backgrounds();f.scene:backdrop()end
eq(f.reads,reads);eq(f.allocs,allocs);eq(f.textures,textureCount);eq(f.theme.prepared,1,'warm frames never rebake')
f.phase=1;eq(f.scene:backgrounds(),base);eq(f.tree.released,false);eq(f.edge.released,false)
f.revision=2;local updated=f.scene:backgrounds();eq(base.released,true);eq(updated==base,false);eq(f.theme.prepared,2)
f.style='original';eq(f.scene:backgrounds(),'native-base');eq(updated.released,true)
local cold=f.reads;f.scene:backgrounds();eq(f.reads,cold,'cold Original delegates without theme reads')
f.style='gen3';local final=f.scene:backgrounds();local finalReads,finalBakes=f.reads,f.theme.builds;eq(f.scene:finish(),'finished');eq(f.finishes,1)
eq(f.scene:backgrounds(),final,'last completed frame uses existing textures');eq(f.reads,finalReads);eq(f.theme.builds,finalBakes)
local owned=f.Class.backgrounds;local later=function(scene)return owned(scene)end;f.Class.backgrounds=later
f.theme:dispose();eq(f.Class.backgrounds,later,'later wrapper retained');eq(f.scene:backgrounds(),'native-base');eq(f.Class.finish(f.scene),'finished');eq(f.finishes,2)
eq(f.tree.released,false);eq(f.edge.released,false)
local bad=fixture();bad.style='gen3';bad.missing=true;eq(bad.scene:backgrounds(),'native-base');local attempted=bad.reads
for _=1,10 do eq(bad.scene:backgrounds(),'native-base')end;eq(bad.reads,attempted);eq(bad.warnings,1,'failed source is memoized')
bad.missing=false;bad.revision=2;eq(bad.scene:backgrounds()=='native-base',false);bad.active=false;eq(bad.scene:backgrounds(),'native-base');bad.theme:dispose()
local changed=fixture();changed.style='gen3';changed.scene.ride.fgTilemap[1]=999
eq(changed.scene:backgrounds(),'native-base');eq(changed.reads,0,'reject changed live source before reading donors');changed.theme:dispose()
local foreign=fixture();foreign.style='gen3';foreign.ctx.game=function()return{data=foreign.scene.data}end
eq(foreign.scene:backgrounds(),'native-base');eq(foreign.reads,0,'reject a different active game even with identical imported data');foreign.theme:dispose()
local switched=fixture();switched.style='gen3';local stale=switched.scene:backgrounds();local priorReads=switched.reads
switched.ctx.game=function()return{data=switched.scene.data}end
eq(switched.scene:backgrounds(),'native-base','warm cache cannot survive active-game identity change');eq(switched.reads,priorReads)
eq(stale.released,true,'stale cached texture released instead of returned');switched.theme:dispose()
local unavailable=0;local silent=Theme.install({catalog={},style=function()return'gen3'end,version=function()return'crystal'end,active=function()return true end,
  require=function()error('old engine')end,warn=function()unavailable=unavailable+1 end})
eq(unavailable,1);silent:dispose();silent:dispose()
f.theme:dispose()
print('magnet_train_ride_test: '..count..' checks')
