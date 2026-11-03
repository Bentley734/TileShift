local root=assert(arg and arg[1])
local Animation=assert(loadfile(root..'/lib/gb_animation.lua'))()
local checks=0
local function check(value,message)checks=checks+1;assert(value,message)end
local function image(w,h)
 local im={w=w,h=h,p={}}
 function im:getDimensions()return self.w,self.h end
 function im:setPixel(x,y,r,g,b,a)self.p[y*self.w+x]={r,g,b,a}end
 function im:getPixel(x,y)
  check(x>=0 and y>=0 and x<self.w and y<self.h,'pixel bounds')
  local p=self.p[y*self.w+x]or{0,0,0,0};return p[1],p[2],p[3],p[4]
 end
 return im
end
local atlas=image(128,128);local lava=image(8,32);local whirl=image(8,32)
for y=0,127 do for x=0,127 do atlas:setPixel(x,y,x/128,y/128,0,1)end end
for y=0,31 do for x=0,7 do lava:setPixel(x,y,math.floor(y/8)/4,x/8,y%8/8,1);whirl:setPixel(x,y,x/8,math.floor(y/8)/4,0,1)end end
local path='assets/generated/tilesets/test.png';local lp='assets/generated/tilesets/anim/lava.png';local wp='assets/generated/tilesets/anim/whirlpool.png'
local block={56,91,7,7,64,50,7,7,7,7,7,7,7,7,7,7}
local ts={image=path,tilesPerRow=16,blocks={block},anim={period=19,frames={
 {func='AnimateLavaBubbleTile2',tile=56,frames=4,sheet=lp},
 {func='AnimateLavaBubbleTile1',tile=91,frames=4,sheet=lp},
 {func='ReadTileToAnimBuffer',tile=64},{func='ScrollTileDown'},
 {func='WriteTileFromAnimBuffer',tile=64,scroll={h=1,v=3}},
 {func='AnimateWhirlpoolTile',tile=50,frames=4,sheet=wp},{func='DoneTileAnimation'}}}}
local sets={TEST=ts};local metadata='source metadata';local sources={[path]='atlas',[lp]='lava',[wp]='whirlpool'}
local sheets={[path]=atlas,[lp]=lava,[wp]=whirl};local seen={};local calls=0
local function hash(s)return 'H'..s end
local ref={game='crystal',tileset='TEST',id=0,quadrant=0}
local ctx={module=function()return sets,metadata end,sheet=function(_,p)return sheets[p],sources[p]end,
 hash=hash,newImageData=image,decode=function(r,overrides)
  check(r==ref,'unchanged donor reference');calls=calls+1;seen[calls]=overrides
  check(overrides[7]==nil,'static glyph was animated')
  return{under=image(16,16)}
 end}
local spec={kind='gb',bank='program',manifestHash=hash(metadata),hash=hash('lava'..'whirlpool'..'atlas')}
-- Sorted resource paths put anim/lava, anim/whirlpool, then test.png.
local result=Animation.frames(ctx,ref,spec)
check(#result.frames==8 and result.period==19/60 and result.ticks==19,'native program schedule')
check(result.bank=='gb_program'and result.category=='water','program category')
local horizontal={0,1,2,3,2,1,0,-1}
for timer=0,7 do
 local o=seen[timer+1]
 for y=0,7 do for x=0,7 do
  local r=o[56]:getPixel(x,y);check(r==math.floor(timer/2)/4,'lava2 native phase')
  r=o[91]:getPixel(x,y);check(r==((math.floor(timer/2)+2)%4)/4,'lava1 opposite phase')
  local _,g=o[50]:getPixel(x,y);check(g==(timer%4)/4,'whirlpool native row')
  local sr,sg=atlas:getPixel(x,32+y)
  local ar,ag=o[64]:getPixel((x+horizontal[timer+1])%8,(y+timer*3)%8)
  check(ar==sr and ag==sg,'native horizontal/vertical scroll and wrapping')
 end end
end
local function rejects(change,restore,needle)
 change();local ok,why=pcall(Animation.frames,ctx,ref,spec);restore()
 check(not ok and tostring(why):find(needle,1,true),'unsafe program accepted: '..tostring(why))
end
rejects(function()spec.hash='bad'end,function()spec.hash=hash('lava'..'whirlpool'..'atlas')end,'fingerprint')
rejects(function()spec.manifestHash='bad'end,function()spec.manifestHash=hash(metadata)end,'metadata fingerprint')
rejects(function()ref.game='red'end,function()ref.game='crystal'end,'Invalid Gen2')
rejects(function()ts.anim.period=0 end,function()ts.anim.period=19 end,'native animation program')
rejects(function()ts.anim.frames[1].sheet='../secret.png'end,function()ts.anim.frames[1].sheet=lp end,'strip is unavailable')
rejects(function()sheets[lp]=image(8,31)end,function()sheets[lp]=lava end,'strip dimensions')
rejects(function()ts.anim.frames[1].func='AnimateMysteryTile'end,function()ts.anim.frames[1].func='AnimateLavaBubbleTile2'end,'Unsupported native')
rejects(function()ref.quadrant=3 end,function()ref.quadrant=0 end,'no supported native program tile')
-- Hoenn's forced currents keep each complete Crystal scrolling-water glyph.
-- The four explicit source directions must differ without changing any color,
-- cadence, static source buffer, or glyph pixel count.
ts.blocks[1]={20,20,7,7,20,20,7,7,7,7,7,7,7,7,7,7}
ts.anim.frames={{func='WriteTileFromAnimBuffer',tile=20,scroll={h=1,v=0}}}
spec.hash=hash('atlas')
for direction,vector in pairs({north={0,-1},south={0,1},east={1,0},west={-1,0}})do
 spec.flowDirection=direction;calls=0;seen={}
 local flow=Animation.frames(ctx,ref,spec)
 check(#flow.frames==8 and flow.period==19/60,'current changed native cadence')
 for timer=0,7 do for y=0,7 do for x=0,7 do
  local sr,sg=atlas:getPixel(32+x,8+y)
  local r,g=seen[timer+1][20]:getPixel((x+timer*vector[1])%8,(y+timer*vector[2])%8)
  check(r==sr and g==sg,'current direction lost or resampled a native source pixel')
 end end end
end
spec.flowDirection='diagonal'
local ok,why=pcall(Animation.frames,ctx,ref,spec)
check(not ok and tostring(why):find('Directional GB flow',1,true),'unknown current direction accepted')
spec.flowDirection='east';ts.anim.frames[1].scroll.v=2
ok,why=pcall(Animation.frames,ctx,ref,spec)
check(not ok and tostring(why):find('Directional GB flow',1,true),'nonwater program became forced current')
ts.anim.frames[1].scroll.v=0;ts.blocks[1][1]=7
ok,why=pcall(Animation.frames,ctx,ref,spec)
check(not ok and tostring(why):find('pure water20',1,true),'mixed land/current donor accepted')
print('GB native program animation checks: '..checks)
