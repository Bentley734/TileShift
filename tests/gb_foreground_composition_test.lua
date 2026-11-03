local root=assert(arg and arg[1])
local Composition=assert(loadfile(root..'/lib/composition.lua'))()
local Mapping=assert(loadfile(root..'/lib/mapping.lua'))()
local checks,calls=0,0
local function check(value,message)checks=checks+1;assert(value,message)end
local function image(w,h,color)
 local im={w=w,h=h,p={}}
 function im:getDimensions()return self.w,self.h end
 function im:getPixel(x,y)
  check(x>=0 and y>=0 and x<self.w and y<self.h,'pixel bounds')
  local p=self.p[y*self.w+x]or color or{0,0,0,0};return p[1],p[2],p[3],p[4]
 end
 function im:setPixel(x,y,r,g,b,a)self.p[y*self.w+x]={r,g,b,a}end
 return im
end
local digest=string.rep('a',64)
local base=image(16,16,{0,0,1,1});local opaque=image(16,16,{1,0,0,1})
local first=image(16,16);first:setPixel(1,1,1,1,1,1);first:setPixel(2,2,0,1,0,1)
local second=image(16,16);second:setPixel(2,1,1,1,1,1);second:setPixel(3,2,1,0,1,1)
local sequence={frames={{under=opaque,foreground=first},{under=opaque,foreground=second}},period=.2,offset=0}
local donor={cell=function(_,ref)
 calls=calls+1
 return{hash=digest,under=ref.id==0 and base or opaque,foreground=first}
end,frames=function()return sequence end}
local comp=Composition.new({donor=donor,newImageData=image})
local function ref(id)return{game='crystal',tileset='TEST',id=id,quadrant=0,map='TEST_ROOM',hash=digest}end
local row={game='emerald',style='gen2',tileset='building__house',id=513,sourceHash=digest,
 kind='native_composite',status='reviewed',role='test_complete_native_flower',evidence='checked native glyph fixture',
 base=ref(0),parts={{donor=ref(1),x=0,y=0,w=16,h=16,gbForeground=true}}}
local function pixel(im,x,y,r,g,b,a)
 local ar,ag,ab,aa=im:getPixel(x,y);check(ar==r and ag==g and ab==b and aa==a,'foreground composition pixel mismatch')
end
check(Mapping.validate(row),'checked static GB foreground row must validate')
local result,why=comp:cell(row);check(result~=nil,why)
pixel(result.under,0,0,0,0,1,1)
pixel(result.under,1,1,1,1,1,1) -- A nonzero source shade can map to white: never RGB-key it away.
pixel(result.under,2,2,0,1,0,1)
pixel(opaque,0,0,1,0,0,1);pixel(base,0,0,0,0,1,1)
row.animated=true;row.animation={kind='gb',bank='flower',hash=digest,manifestHash=digest};row.parts[1].animated=true
check(Mapping.validate(row),'checked animated GB foreground row must validate')
result,why=comp:frames(row);check(result~=nil,why);check(#result.frames==2,'native frame count')
pixel(result.frames[1].under,1,1,1,1,1,1);pixel(result.frames[1].under,2,1,0,0,1,1)
pixel(result.frames[2].under,1,1,0,0,1,1);pixel(result.frames[2].under,2,1,1,1,1,1)
pixel(result.frames[2].under,3,2,1,0,1,1)
local function rejects(change,restore)
 change();local before=calls;local valid=Mapping.validate(row);local value=comp:cell(row)
 check(not valid and value==nil,'invalid foreground selection accepted');check(calls==before,'invalid input decoded donor pixels');restore()
end
rejects(function()row.parts[1].gbForeground='yes'end,function()row.parts[1].gbForeground=true end)
rejects(function()row.parts[1].donor.game='emerald'end,function()row.parts[1].donor.game='crystal'end)
rejects(function()row.parts[1].layers={'under'};row.parts[1].layerHashes={under=digest}end,
 function()row.parts[1].layers=nil;row.parts[1].layerHashes=nil end)
print('GB foreground composition checks: '..checks)
