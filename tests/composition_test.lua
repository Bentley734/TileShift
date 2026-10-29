local root=assert(arg and arg[1],'TileShift directory required')
local Composition=assert(loadfile(root..'/lib/composition.lua'))()
local count=0
local function eq(a,b,message)
  count=count+1;assert(a==b,(message or 'mismatch')..': '..tostring(a)..' ~= '..tostring(b))
end
local function near(a,b,message)
  count=count+1;assert(math.abs(a-b)<1e-9,(message or 'mismatch')..': '..tostring(a)..' ~= '..tostring(b))
end
local function newData(w,h)
  local d={w=w,h=h,pixels={}}
  function d:getDimensions()return self.w,self.h end
  function d:getPixel(x,y)
    assert(x%1==0 and y%1==0 and x>=0 and x<self.w and y>=0 and y<self.h,'Read outside image')
    local p=self.pixels[y*self.w+x] or {0,0,0,0};return p[1],p[2],p[3],p[4]
  end
  function d:setPixel(x,y,r,g,b,a)
    assert(x%1==0 and y%1==0 and x>=0 and x<self.w and y>=0 and y<self.h,'Write outside image')
    self.pixels[y*self.w+x]={r,g,b,a}
  end
  return d
end
local hashA,hashB,hashC=string.rep('a',64),string.rep('b',64),string.rep('c',64)
local function ref(id,hash)return {game='firered',tileset='PAIR',id=id,hash=hash or hashA}end
local pieces={}
for id=1,3 do
  local p={hash=id==3 and hashB or hashA,under=newData(16,16),mid=newData(16,16),over=newData(16,16)}
  for y=0,15 do for x=0,15 do
    p.under:setPixel(x,y,x/15,y/15,id/4,1)
  end end
  pieces[id]=p
end
local calls={}
local donor={}
function donor:cell(reference)
  calls[#calls+1]=reference
  if reference.id==99 then error('decoder thrown failure') end
  if reference.id==98 then return nil,'decoder rejected fingerprint' end
  return pieces[reference.id]
end
local composer=Composition.new({donor=donor,newImageData=newData})
local function row(parts,base)return {kind='native_composite',parts=parts,base=base}end
local function part(id,sx,sy,w,h,x,y)
  return {donor=ref(id),srcX=sx,srcY=sy,w=w,h=h,x=x,y=y}
end
local function pixel(image,x,y,r,g,b,a,label)
  local ar,ag,ab,aa=image:getPixel(x,y)
  near(ar,r,label);near(ag,g,label);near(ab,b,label);near(aa,a,label)
end
-- Asymmetric coordinates expose transposed crops, wrong source strides and
-- accidental whole-cell copies. A later piece also tests overlap order.
local first=part(1,9,2,3,5,1,10)
local second=part(2,2,11,5,2,10,1)
local overlap=part(2,14,13,1,1,2,12)
local result,err=composer:cell(row({first,second,overlap}));assert(result,err)
eq(#calls,3);eq(calls[1],first.donor,'exact reference reaches fingerprint decoder')
for dy=0,4 do for dx=0,2 do
  if not (dx==1 and dy==2) then pixel(result.under,1+dx,10+dy,(9+dx)/15,(2+dy)/15,1/4,1) end
end end
for dy=0,1 do for dx=0,4 do pixel(result.under,10+dx,1+dy,(2+dx)/15,(11+dy)/15,2/4,1)end end
pixel(result.under,2,12,14/15,13/15,2/4,1,'last piece wins')
pixel(result.under,0,10,0,0,0,0,'untouched cell is transparent')
pixel(result.under,4,10,0,0,0,0,'crop right boundary')
pixel(result.under,1,15,0,0,0,0,'crop bottom boundary')
eq(result.mid,nil)
for y=0,15 do for x=0,15 do pixel(result.over,x,y,0,0,0,0,'returned over stays transparent')end end

-- Straight-alpha compositing must retain chroma even on transparent output.
local p=pieces[1]
p.under:setPixel(7,6,1,0,0,.5)
p.mid:setPixel(7,6,0,1,0,.5)
p.over:setPixel(7,6,0,0,1,.5)
p.under:setPixel(8,6,.9,.8,.7,0)
p.mid:setPixel(8,6,.6,.5,.4,0)
p.over:setPixel(8,6,.3,.2,.1,0)
local alphaRow=row({part(1,7,6,2,1,3,4)})
local alpha=assert(composer:cell(alphaRow))
pixel(alpha.under,3,4,1/7,2/7,4/7,7/8,'under then middle then over')
pixel(alpha.under,4,4,0,0,0,0,'fully transparent source contributes no hidden RGB')
pieces[2].under:setPixel(3,4,.25,.5,.75,.5)
pieces[2].mid:setPixel(3,4,1,1,0,.5)
local withBase=assert(composer:cell(row(alphaRow.parts,ref(2))))
-- Base at (3,4): (0.75,5/6,0.25,0.75), followed by the
-- flattened (1/7,2/7,4/7,7/8) piece. Compute independently.
local baseAlpha=.5+.5*.5
local br=(1*.5+.25*.5*.5)/baseAlpha
local bg=(1*.5+.5*.5*.5)/baseAlpha
local bb=(0*.5+.75*.5*.5)/baseAlpha
local outAlpha=7/8+baseAlpha/8
pixel(withBase.under,3,4,((1/7)*(7/8)+br*baseAlpha/8)/outAlpha,
  ((2/7)*(7/8)+bg*baseAlpha/8)/outAlpha,((4/7)*(7/8)+bb*baseAlpha/8)/outAlpha,outAlpha,
  'flattened source blends over flattened base')
pixel(withBase.under,4,4,4/15,4/15,.5,1,'transparent piece preserves base')
pixel(withBase.under,15,15,1,1,.5,1,'base covers entire output')

local function snapshot(image)
  local out={}
  for y=0,15 do for x=0,15 do
    local r,g,b,a=image:getPixel(x,y);out[#out+1]=table.concat({r,g,b,a},',')
  end end
  return table.concat(out,';')
end
local before={}
for id=1,3 do for _,layer in ipairs({'under','mid','over'})do
  before[id..layer]=snapshot(pieces[id][layer])
end end
local a=assert(composer:cell(row({part(1,0,0,16,16,0,0)},ref(2))))
local b=assert(composer:cell(row({{donor=ref(1),w=16,h=16}})))
eq(a.under~=b.under,true,'output image is newly owned')
a.under:setPixel(0,0,.125,.25,.375,.5)
for id=1,3 do for _,layer in ipairs({'under','mid','over'})do
  eq(snapshot(pieces[id][layer]),before[id..layer],'source images are immutable')
end end

local function fails(input,expected,noReads)
  local n=#calls
  local failed,why=composer:cell(input)
  eq(failed,nil);eq(type(why),'string')
  eq(why:find(expected,1,true)~=nil,true,why)
  if noReads then eq(#calls,n,'bad row rejected before any source reads')end
end
fails(nil,'row is required',true)
fails({parts={first}},'row is required',true)
fails(row({}),'1 to 16 parts',true)
local seventeen={};for i=1,17 do seventeen[i]=first end
fails(row(seventeen),'1 to 16 parts',true)
fails(row({[1]=first,[3]=second}),'dense array',true)
fails(row({first,extra=second}),'dense array',true)
fails(row({false}),'part is required',true)
fails(row({{w=8,h=8}}),'reference is required',true)
local noHash=part(1,0,0,1,1,0,0);noHash.donor.hash=nil
fails(row({noHash}),'fingerprint is required',true)
local malformed=part(1,0,0,1,1,0,0);malformed.donor.hash=string.rep('Z',64)
fails(row({malformed}),'fingerprint is required',true)
fails(row({first},false),'reference is required',true)
for _,change in ipairs({{srcX=-1},{srcY=16},{x=.5},{y=0/0},{srcX=math.huge},{srcX=false},{y='0'},
  {w=0},{h=-1},{w=17},{h=.5},{srcX=9,w=8},{srcY=9,h=8},{x=9,w=8},{y=9,h=8},
  {w=false},{h='8'}}) do
  local bad=part(1,0,0,8,8,0,0)
  for key,value in pairs(change)do bad[key]=value end
  fails(row({first,bad}),'rectangle exceeds',true)
end
fails(row({part(98,0,0,1,1,0,0)}),'decoder rejected fingerprint')
fails(row({part(99,0,0,1,1,0,0)}),'decoder thrown failure')
fails(row({first},ref(98)),'decoder rejected fingerprint')
fails(row({part(3,0,0,1,1,0,0)}),'fingerprint changed')
fails(row({first},ref(3)),'fingerprint changed')
pieces[3].hash=hashA;pieces[3].under=newData(15,16)
fails(row({part(3,0,0,1,1,0,0)}),'16 by 16')
pieces[3].under=nil
fails(row({part(3,0,0,1,1,0,0)}),'under layer is unavailable')
pieces[3].under=newData(16,16);pieces[3].mid={}
fails(row({part(3,0,0,1,1,0,0)}),'pixels are unavailable')
pieces[3].mid=nil;pieces[3].hash=nil;pieces[3].sourceHash=hashA
eq(composer:cell(row({part(3,0,0,1,1,0,0)}))~=nil,true,'sourceHash decoder contract is accepted')
-- Sixteen bounded parts and edge coordinates are legal.
local sixteen={};for i=1,16 do sixteen[i]=part(1,15,15,1,1,(i-1)%16,15)end
eq(composer:cell(row(sixteen))~=nil,true)
-- Roof art must retain its exact alpha mask while the selected ground shows
-- through. The flattened donor fingerprint alone cannot protect that mask.
local overSnapshot=snapshot(pieces[1].over)
local layerComposer=Composition.new({donor=donor,newImageData=newData,
  hashImage=function(image)return snapshot(image)==overSnapshot and hashC or hashB end})
local roofPart=part(1,7,6,2,1,3,4)
roofPart.layers={'over'};roofPart.layerHashes={over=hashC}
local roof=assert(layerComposer:cell(row({roofPart},ref(2))))
local combined=.5+baseAlpha*.5
pixel(roof.under,3,4,br*baseAlpha*.5/combined,bg*baseAlpha*.5/combined,
  (.5+bb*baseAlpha*.5)/combined,combined,'selected roof over the independent base')
pixel(roof.under,4,4,4/15,4/15,.5,1,'transparent roof reveals ground')
local function layerFails(changes,needle,reads)
  local bad=part(1,0,0,16,16,0,0)
  for key,value in pairs(changes)do bad[key]=value end
  local n=#calls
  local failed,why=layerComposer:cell(row({bad}))
  eq(failed,nil);eq(why:find(needle,1,true)~=nil,true,why)
  if not reads then eq(#calls,n,'invalid layer specification fails before reads')end
end
layerFails({layers={}},'fingerprints are required')
layerFails({layers={'over'}},'fingerprints are required')
layerFails({layerHashes={over=hashC}},'explicit layer selection')
layerFails({layers={'unknown'},layerHashes={unknown=hashC}},'rendering order')
layerFails({layers={'over','over'},layerHashes={over=hashC}},'rendering order')
layerFails({layers={'over','mid'},layerHashes={over=hashC,mid=hashC}},'rendering order')
layerFails({layers={'over',extra='mid'},layerHashes={over=hashC}},'dense array')
layerFails({layers={'over'},layerHashes={over=hashC,mid=hashC}},'Unselected')
layerFails({layers={'over'},layerHashes={over=hashC:sub(2)}},'fingerprint is required')
layerFails({layers={'over'},layerHashes={over=hashB}},'fingerprint changed',true)
pieces[1].over:setPixel(0,0,1,0,0,1)
local missingRoof,maskError=layerComposer:cell(row({roofPart},ref(2)))
eq(missingRoof,nil);eq(maskError:find('fingerprint changed',1,true)~=nil,true,
  'alpha separation mutation rejected even while full donor fingerprint stays the same')
pieces[1].over:setPixel(0,0,0,0,0,0)
-- A static roof crop overlays every native water frame. Deliberately use
-- asymmetric source/destination coordinates and mixed alpha so the exposed
-- water, native chroma and selected static layer can be checked independently.
local nativeFrames={}
for i=1,8 do
  local base={under=newData(16,16),over=newData(16,16)}
  for y=0,15 do for x=0,15 do base.under:setPixel(x,y,i/8,x/15,y/15,1)end end
  nativeFrames[i]=base
end
local roofPiece={hash=hashB,under=newData(16,16),over=newData(16,16)}
for y=3,7 do for x=2,5 do roofPiece.over:setPixel(x,y,.9,.2,.1,(x+y)%3/2)end end
local reads,frameReads=0,0
local animatedDonor={cell=function(_,r)
  reads=reads+1
  if r.id==10 then return {hash=hashA,under=nativeFrames[1].under,over=nativeFrames[1].over}end
  return roofPiece
end,frames=function(_,r,spec)
  frameReads=frameReads+1;eq(r.id,10);eq(spec.bank,'water')
  if spec.hash~=hashB then return nil,'bank fingerprint changed'end
  return {frames=nativeFrames,bank='water',counter='global',ticks=16,period=16/60,phase=1,offset=1/60,identity='native fixture'}
end}
local animatedComposer=Composition.new({donor=animatedDonor,newImageData=newData,
  hashImage=function(image)return image==roofPiece.over and hashB or hashC end})
local animatedRoof={game='red',kind='native_composite',animated=true,
  base=ref(10),animation={bank='water',hash=hashB,manifestHash=hashA,frame0Hash=hashC},
  parts={{donor=ref(20,hashB),srcX=2,srcY=3,w=4,h=5,x=7,y=8,layers={'over'},layerHashes={over=hashB}}}}
local nativeBefore={};for i,p in ipairs(nativeFrames)do nativeBefore[i]=snapshot(p.under)end
local roofBefore=snapshot(roofPiece.over)
local animated=assert(animatedComposer:frames(animatedRoof))
eq(reads,2,'base and static donor decoded once');eq(frameReads,1);eq(#animated.frames,8)
for _,key in ipairs({'bank','counter','ticks','period','phase','offset','identity'})do
  local expected={bank='water',counter='global',ticks=16,period=16/60,phase=1,offset=1/60,identity='native fixture'}
  eq(animated[key],expected[key],'native animation metadata preserved')
end
for i,p in ipairs(animated.frames)do
  pixel(p.under,0,0,i/8,0,0,1,'outside roof retains each native water frame')
  pixel(p.under,7,8,.9,.2,.1,1,'opaque roof stays static')
  pixel(p.under,8,8,i/8,8/15,8/15,1,'transparent selected roof reveals current water')
  pixel(p.under,8,9,.9*.5+i/8*.5,.2*.5+8/15*.5,.1*.5+9/15*.5,1,'semi-alpha roof blends over each frame')
  pixel(p.over,7,8,0,0,0,0,'composed output owns no stale over layer')
  eq(snapshot(nativeFrames[i].under),nativeBefore[i],'native animation images are immutable')
end
eq(snapshot(roofPiece.over),roofBefore,'static selected donor remains immutable')
animated.frames[1].under:setPixel(0,0,1,1,1,1)
pixel(animated.frames[2].under,0,0,2/8,0,0,1,'output frames own independent pixels')
eq(snapshot(nativeFrames[1].under),nativeBefore[1],'output cannot mutate native frame0')
local function clone(value)
  if type(value)~='table'then return value end
  local copy={};for k,v in pairs(value)do copy[k]=clone(v)end;return copy
end
local function animationFails(change,needle)
  local bad=clone(animatedRoof);change(bad)
  local out,why=animatedComposer:frames(bad)
  eq(out,nil);eq(type(why),'string');eq(why:find(needle,1,true)~=nil,true,why)
end
animationFails(function(r)r.game='emerald'end,'GB host')
animationFails(function(r)r.animated=nil end,'GB host')
animationFails(function(r)r.base=nil end,'metatile base')
animationFails(function(r)r.base.hash=hashB end,'fingerprint changed')
animationFails(function(r)r.animation.hash=hashC end,'bank fingerprint changed')
animationFails(function(r)r.animation.frame0Hash=hashA end,'base frame fingerprint changed')
animationFails(function(r)r.parts[1].layerHashes.over=hashC end,'layer fingerprint changed')
animationFails(function(r)r.parts[1].w=17 end,'rectangle exceeds')
animationFails(function(r)r.donor=ref(1)end,'one artwork source')
local originalSequence=animatedDonor.frames
animatedDonor.frames=function()return {frames={nativeFrames[1]},period=16/60}end
animationFails(function()end,'sequence is invalid')
animatedDonor.frames=function(self,r,spec)
  local sequence=originalSequence(self,r,spec)
  sequence.frames={nativeFrames[1],nativeFrames[2],extra=nativeFrames[3]};return sequence
end
animationFails(function()end,'dense array')
animatedDonor.frames=function()return {frames=nativeFrames,period=0/0}end
animationFails(function()end,'sequence is invalid')
animatedDonor.frames=function()error('native bank missing')end
animationFails(function()end,'native bank missing')
animatedDonor.frames=function(self,r,spec)
  local sequence=originalSequence(self,r,spec);sequence.bank='flower';return sequence
end
animationFails(function()end,'sequence is invalid')
animatedDonor.frames=function(self,r,spec)
  local sequence=originalSequence(self,r,spec);sequence.offset=0;return sequence
end
animationFails(function()end,'sequence is invalid')
animatedDonor.frames=function(self,r,spec)
  local sequence=originalSequence(self,r,spec);sequence.frames={nativeFrames[1],{under=newData(15,16)}};return sequence
end
animationFails(function()end,'16 by 16')
animatedDonor.frames=nil
animationFails(function()end,'animation decoder is unavailable')
animatedDonor.frames=originalSequence
-- GB flower glyphs animate inside an independent, unchanged ground cell.
local ground=newData(16,16)
for y=0,15 do for x=0,15 do ground:setPixel(x,y,.1,.2,.3,1)end end
local gbFrames={}
for i=1,2 do
 local frame=newData(16,16)
 for y=0,15 do for x=0,15 do frame:setPixel(x,y,i/2,0,1-i/2,1)end end
 gbFrames[i]={under=frame}
end
local classicDonor={cell=function()return{under=ground,hash=hashA}end,
 frames=function()return{frames=gbFrames,period=.35,offset=0,bank='gb_flower',category='flowers'}end}
local classicComposer=Composition.new({donor=classicDonor,newImageData=newData})
local glyph={donor={game='red',tileset='OVERWORLD',id=1,quadrant=0,hash=hashA,monochrome=true},srcX=8,srcY=0,w=8,h=8,x=4,y=4,animated=true}
local classicRow={game='emerald',style='gen1',kind='native_composite',base=glyph.donor,parts={glyph},animated=true,animation={kind='gb',bank='flower'}}
local sequence,why=classicComposer:frames(classicRow);assert(sequence,why)
eq(#sequence.frames,2);eq(sequence.period,.35);eq(sequence.category,'flowers')
for i,frame in ipairs(sequence.frames)do
 pixel(frame.under,0,0,.1,.2,.3,1,'Flower animation preserves surrounding ground')
 pixel(frame.under,4,4,i/2,0,1-i/2,1,'Whole eight-pixel glyph animates without scaling')
 pixel(frame.under,11,11,i/2,0,1-i/2,1,'Complete glyph bottom corner retained')
 pixel(frame.under,12,11,.1,.2,.3,1,'No hatched donor floor outside flower')
end
-- Reject ambiguous GB animation before reading any donor pixels, including
-- callers using the composition module directly rather than Mapping.validate.
local guardedReads,guardedFrames=0,0
local guardedComposer=Composition.new({donor={cell=function(...)
 guardedReads=guardedReads+1;return classicDonor.cell(...)
end,frames=function(...)
 guardedFrames=guardedFrames+1;return classicDonor.frames(...)
end},newImageData=newData})
for _,mutate in ipairs({function(r)r.animated=nil end,function(r)r.animated=false end,
 function(r)r.parts[1].animated=nil end,function(r)r.parts[1].animated=false end,
 function(r)r.parts[1].animated=1 end,function(r)r.animation=true end,
 function(r)r.parts[1].layers={'under'};r.parts[1].layerHashes={under=hashA}end})do
 local bad=clone(classicRow);mutate(bad)
 for _,method in ipairs({'cell','frames'})do
  local out,message=guardedComposer[method](guardedComposer,bad)
  eq(out,nil,'invalid GB animation '..method);eq(type(message),'string')
 end
 eq(guardedReads,0,'invalid GB composition fails before donor reads')
 eq(guardedFrames,0,'invalid GB composition fails before animation reads')
end
print('composition: '..count..' assertions passed')
