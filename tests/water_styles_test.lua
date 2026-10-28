local root=assert(arg[1]);local unpack=table.unpack or unpack
local W=assert(loadfile(root..'/lib/water_styles.lua'))()
local checks=0
local function eq(a,b,message)checks=checks+1;assert(a==b,(message or 'mismatch')..': '..tostring(a)..' ~= '..tostring(b))end
local function image(w,h,fill)
 local pixels={};local out={}
 function out:getDimensions()return w,h end
 function out:getPixel(x,y)return unpack(pixels[y*w+x] or fill or {0,0,0,0})end
 function out:setPixel(x,y,...)pixels[y*w+x]={...}end
 function out:paste(source,dx,dy,sx,sy,sw,sh)
  for y=0,sh-1 do for x=0,sw-1 do self:setPixel(dx+x,dy+y,source:getPixel(sx+x,sy+y))end end
 end
 return out
end
local reads=0
local water=W.new({newImageData=image,image=function(path,expected)
 reads=reads+1;eq(#expected,64)
 local n=assert(tonumber(path:match('frame%-(%d+)')))
 return image(464,208,{n/10,.8,.9,1})
end,donor={cell=function()return {mid=image(16,16,{.1,.2,.9,1})}end}})
local native=image(16,16,{.05,.3,.8,1})
native:setPixel(0,0,.5,.4,.2,1) -- bank
native:setPixel(1,0,.4,.45,.5,1) -- grey rock
native:setPixel(2,0,1,1,1,1) -- foam
local piece={under=native}
local ripple={id='ripple',sheet='magiscarf',x=64,y=32}
local result,sequence=water:finish(ripple,piece)
eq(#sequence.frames,8,'all custom water has eight real animation frames')
for x=0,2 do
 local r,g,b,a=native:getPixel(x,0);local rr,gg,bb,aa=result.under:getPixel(x,0)
 eq(r,rr,'bank/rock/foam retained');eq(g,gg);eq(b,bb);eq(a,aa)
end
local r,g,b=result.under:getPixel(3,0);eq(r,.1);eq(g,.8);eq(b,.9)
eq(native:getPixel(3,0),.05,'shared native donor was not painted into')
local _,animated=water:finish(ripple,piece)
eq(#animated.frames,8);eq(animated.period,.1)
eq(animated.frames[1].under:getPixel(3,0),.1);eq(animated.frames[8].under:getPixel(3,0),.8)
local nativeSequence={frames={piece,piece,piece,piece,piece,piece,piece,piece},period=16/60,bank='water',offset=1/60}
local _,retained=water:finish(ripple,piece,nativeSequence)
eq(retained.period,16/60);eq(retained.bank,'water');eq(retained.offset,1/60)
eq(nativeSequence.frames[1],piece,'native cached sequence remains untouched')
-- A blue window in an over-water building must never become a water surface.
local guarded=water:finish(ripple,piece,nil,{parts={{donor={},layers={'mid'},x=3,y=0,w=1,h=1}}})
eq(guarded.under:getPixel(3,0),.05,'native facade pixels protected even when blue')
local glass=image(16,16);glass:setPixel(3,0,.05,.3,.8,1)
local _,assetWater=water:finish(ripple,{under=native,over=glass},nativeSequence,{asset='assets/original/fixture.png'})
for i,frame in ipairs(assetWater.frames)do
 local rr,gg,bb,aa=frame.under:getPixel(3,0);eq(rr,.05,'blue original window cannot become ripple water');eq(gg,.3);eq(bb,.8);eq(aa,1)
 eq(frame.under:getPixel(4,0),i/10,'transparent original pixels reveal animated custom water')
end
local _,_,_,untouched=glass:getPixel(4,0);eq(untouched,0,'shared original sprite remains transparent')
local foam1,foam2=image(16,16),image(16,16)
foam1:setPixel(3,0,.1,.4,.9,1);foam2:setPixel(4,0,.1,.4,.9,1)
local phases={frames={{under=native,over=foam1},{under=native,over=foam2}},period=.1}
local _,moving=water:finish(ripple,phases.frames[1],phases,{asset='assets/original/foam.png'})
eq(moving.frames[1].under:getPixel(3,0),.1,'current blue foam remains intact')
eq(moving.frames[2].under:getPixel(3,0),.2,'water behind departed foam receives selected second phase')
eq(moving.frames[2].under:getPixel(4,0),.1,'second foam position remains intact')

print('water style checks: '..checks)
