local root=assert(arg and arg[1],'TileShift directory required')
local Animation=assert(loadfile(root..'/lib/gb_animation.lua'))()
local checks=0
local function eq(a,b,message)
 checks=checks+1;assert(a==b,(message or'mismatch')..': '..tostring(a)..' ~= '..tostring(b))
end
local function image(w,h)
 local out={w=w,h=h,pixels={}}
 function out:getDimensions()return self.w,self.h end
 function out:getPixel(x,y)
  assert(x>=0 and y>=0 and x<self.w and y<self.h,'pixel bounds')
  local p=self.pixels[y*self.w+x]or{0,0,0,0};return p[1],p[2],p[3],p[4]
 end
 function out:setPixel(x,y,r,g,b,a)self.pixels[y*self.w+x]={r,g,b,a or 1}end
 function out:getString()
  local b={};for y=0,self.h-1 do for x=0,self.w-1 do
   local r,g,blue,a=self:getPixel(x,y);b[#b+1]=string.char(math.floor(r*255+.5),math.floor(g*255+.5),math.floor(blue*255+.5),math.floor(a*255+.5))
  end end;return table.concat(b)
 end
 return out
end
local function hash(bytes)
 local n=0;for i=1,#bytes do n=(n+bytes:byte(i)*i)%1000000007 end;return 'H'..n
end
local atlas=image(128,128)
for y=0,127 do for x=0,127 do atlas:setPixel(x,y,1,1,1,1)end end
for y=0,7 do for x=0,7 do
 local v=(x%4)/3;atlas:setPixel(32+x,8+y,v,v,v,(y+1)/8)
end end
local strip=image(8,32)
for f=0,3 do for y=0,7 do for x=0,7 do
 local v=((x+f)%4)/3;strip:setPixel(x,f*8+y,v,v,v,1)
end end end
local block={20,20,7,7,20,20,7,7,7,7,7,7,7,7,7,7}
local ts={blocks={block},image='assets/generated/tilesets/gb.png',tilesPerRow=16,animation='TILEANIM_WATER_FLOWER',
 anim={period=13,frames={{func='AnimateWaterTile',tile=20},{func='StandingTileFrame8'}}}}
local sets={TEST=ts,waterFrames='assets/generated/tilesets/water_frames.png'}
local sourceBytes,stripBytes,metadata='atlas bytes','strip bytes','metadata bytes'
local overridesSeen={}
local contexts={}
local ref={game='red',tileset='TEST',id=0,quadrant=0,monochrome=true}
local function context()
 return {module=function(game,path)eq(path,'data/generated/tilesets.lua');return sets,metadata end,
  sheet=function(game,path)
   if path==ts.image then return atlas,sourceBytes end
   eq(path,sets.waterFrames);return strip,stripBytes
  end,hash=hash,newImageData=image,
  decode=function(reference,overrides)
   eq(reference,ref,'original donor context forwarded unchanged')
   eq(overrides[20].w,8);eq(overrides[20].h,8)
   overridesSeen[#overridesSeen+1]=overrides[20]
   local out={under=image(16,16),over=image(16,16)}
   for y=0,15 do for x=0,15 do
    local q=math.floor(y/8)*2+math.floor(x/8)
    local v=overrides[20]:getPixel(x%8,y%8)
    local r,g,b=v,v,v
    if reference.game=='crystal'then
     -- Four distinct output palettes make flattening/losing a quadrant's
     -- selected native GBC palette visible without depending on ROM art.
     r,g,b=q==0 and v or 0,q==1 and v or 0,q>=2 and v or 0
    end
    out.under:setPixel(x,y,r,g,b,1)
   end end
   return out
  end}
end
local spec={kind='gb',bank='water',manifestHash=hash(metadata),hash=hash(sourceBytes)}
local atlasBefore=atlas:getString();local ctx=context()
local sequence=Animation.frames(ctx,ref,spec)
eq(#sequence.frames,8);eq(sequence.ticks,21);eq(sequence.period,21/60);eq(sequence.offset,0)
eq(sequence.bank,'gb_water');eq(sequence.category,'water')
local expected={1,2,3,2,1,0,7,0}
for frame=1,8 do for y=0,7 do for x=0,7 do
 local r,g,b,a=overridesSeen[frame]:getPixel((x+expected[frame])%8,y)
 local er,eg,eb,ea=atlas:getPixel(32+x,8+y)
 eq(r,er,'native Gen1 horizontal rotation');eq(g,eg);eq(b,eb);eq(a,ea,'source alpha preserved')
end end end
eq(atlas:getString(),atlasBefore,'animation construction never modifies imported source image')
ts.animation='TILEANIM_WATER'
sequence=Animation.frames(ctx,ref,spec);eq(sequence.ticks,20);eq(sequence.period,20/60)

ref.game='crystal';spec.hash=hash(stripBytes);overridesSeen={}
local stripBefore=strip:getString()
sequence=Animation.frames(ctx,ref,spec)
eq(#sequence.frames,4);eq(sequence.ticks,26);eq(sequence.period,26/60)
for frame=1,4 do for y=0,7 do for x=0,7 do
 local r,g,b,a=overridesSeen[frame]:getPixel(x,y)
 local er,eg,eb,ea=strip:getPixel(x,(frame-1)*8+y)
 eq(r,er,'native Gen2 frame row');eq(g,eg);eq(b,eb);eq(a,ea)
end end end
local r,g,b=sequence.frames[2].under:getPixel(0,0)
eq(r,1/3,'first GBC quadrant retains its own red palette');eq(g,0);eq(b,0)
r,g,b=sequence.frames[2].under:getPixel(8,0)
eq(r,0);eq(g,1/3,'second GBC quadrant retains its own green palette');eq(b,0)
r,g,b=sequence.frames[2].under:getPixel(0,8)
eq(r,0);eq(g,0);eq(b,1/3,'lower GBC quadrant retains its own blue palette')
eq(strip:getString(),stripBefore,'native Gen2 water strip remains unchanged')
ts.anim.period=19;sequence=Animation.frames(ctx,ref,spec);eq(sequence.ticks,38,'cave timing comes from its actual tileset program')
local function rejects(change,undo,needle)
 change();local ok,why=pcall(Animation.frames,ctx,ref,spec);undo()
 eq(ok,false,'unsafe/unsupported native water input rejected')
 eq(tostring(why):find(needle,1,true)~=nil,true,why)
end
rejects(function()spec.manifestHash='bad'end,function()spec.manifestHash=hash(metadata)end,'metadata fingerprint')
rejects(function()spec.hash='bad'end,function()spec.hash=hash(stripBytes)end,'strip fingerprint')
rejects(function()ts.anim.frames[1].tile=21 end,function()ts.anim.frames[1].tile=20 end,'no native water')
rejects(function()ts.anim.period=0 end,function()ts.anim.period=19 end,'no native animation program')
rejects(function()ref.quadrant=3 end,function()ref.quadrant=0 end,'contains no native animated water')
rejects(function()sets.waterFrames='../secret.png'end,function()sets.waterFrames='assets/generated/tilesets/water_frames.png'end,'strip is unavailable')
rejects(function()block[2]=3;ts.anim.frames[2]={func='AnimateFlowerTile'}end,
 function()block[2]=20;ts.anim.frames[2]={func='StandingTileFrame8'}end,'another native tile animation')
rejects(function()block[2]=7;ts.anim.frames[2]={func='AnimateWhirlpoolTile',tile=7}end,
 function()block[2]=20;ts.anim.frames[2]={func='StandingTileFrame8'}end,'another native tile animation')
local complete=strip
rejects(function()strip=image(8,31)end,function()strip=complete end,'four complete8x8')
rejects(function()spec.bank='lava'end,function()spec.bank='water'end,'specification required')
rejects(function()ref.game='emerald'end,function()ref.game='crystal'end,'Invalid GB water')
ref.game='red';spec.hash=hash(sourceBytes)
rejects(function()ts.animation='TILEANIM_NONE'end,function()ts.animation='TILEANIM_WATER'end,'no native water')
rejects(function()ts.animatedTiles={}end,function()ts.animatedTiles=nil end,'Custom GB tile animation')
rejects(function()spec.hash='bad'end,function()spec.hash=hash(sourceBytes)end,'atlas fingerprint')
ts.animation='TILEANIM_WATER_FLOWER'
rejects(function()block[2]=3 end,function()block[2]=20 end,'another native tile animation')
-- Native flowers use their own source program and frame files. Do not
-- borrow water timing/frames or flatten the caller's native GBC palettes.
for _,i in ipairs({1,2,5,6})do block[i]=3 end
local flowers={image(8,8),image(8,8),image(8,8)}
local flowerBytes={'flower one bytes','flower two bytes','flower three bytes'}
for f=1,3 do for y=0,7 do for x=0,7 do
 local v=((x+f-1)%4)/3;flowers[f]:setPixel(x,y,v,v,v,1)
end end end
local flowerStrip=image(8,32)
for f=0,3 do for y=0,7 do for x=0,7 do
 local v=((x+f)%4)/3;flowerStrip:setPixel(x,f*8+y,v,v,v,1)
end end end
local flowerStripBytes='native CGB flower strip bytes'
sets.flowerFrames='assets/generated/tilesets/flower_frames.png';sets.flowerCgbFrames={2,4}
ts.anim.frames={{func='AnimateWaterTile',tile=20},{func='AnimateFlowerTile'}};ts.anim.period=13
local flowerDecodeCalls=0
local flowerContext={module=function()return sets,metadata end,hash=hash,newImageData=image,
 sheet=function(game,path)
  local n=tonumber(path:match('/flower([123])%.png$'))
  if n then return flowers[n],flowerBytes[n]end
  eq(path,sets.flowerFrames);return flowerStrip,flowerStripBytes
 end,
 decode=function(reference,overrides)
  eq(reference,ref);eq(overrides[20],nil,'flower sequence only overrides the native flower tile')
  eq(overrides[3].w,8);eq(overrides[3].h,8);flowerDecodeCalls=flowerDecodeCalls+1
  local out={under=image(16,16),over=image(16,16)}
  for y=0,15 do for x=0,15 do
   local q=math.floor(y/8)*2+math.floor(x/8)
   local cell=block[math.floor(y/8)*4+math.floor(x/8)+1]
   local v=cell==3 and overrides[3]:getPixel(x%8,y%8)or 2/3
   local r,g,b=v,v,v
   if reference.game=='crystal'then r,g,b=q==0 and v or 0,q==1 and v or 0,q>=2 and v or 0 end
   out.under:setPixel(x,y,r,g,b,1)
  end end
  return out
 end}
ref.game='red';ts.animation='TILEANIM_WATER_FLOWER'
local flowerSpec={kind='gb',bank='flower',manifestHash=hash(metadata),hash=hash(table.concat(flowerBytes))}
local flower=Animation.frames(flowerContext,ref,flowerSpec)
eq(#flower.frames,8);eq(flower.ticks,21);eq(flower.period,21/60);eq(flower.category,'flowers');eq(flower.bank,'gb_flower')
eq(flowerDecodeCalls,3,'repeated native flower phases reuse the same three decoded images')
local flowerOrder={1,2,3,1,1,2,3,1}
for frame=1,8 do for y=0,7 do for x=0,7 do
 local r,g,b,a=flower.frames[frame].under:getPixel(x,y)
 local er,eg,eb,ea=flowers[flowerOrder[frame]]:getPixel(x,y)
 eq(r,er,'native Gen1 flower sequence');eq(g,eg);eq(b,eb);eq(a,ea)
end end end
block[2]=7
flower=Animation.frames(flowerContext,ref,flowerSpec)
for frame=1,8 do eq(flower.frames[frame].under:getPixel(8,0),2/3,'static neighboring tile remains static')end
block[2]=3
ref.game='crystal';flowerSpec.hash=hash(flowerStripBytes)
flower=Animation.frames(flowerContext,ref,flowerSpec)
eq(#flower.frames,2);eq(flower.ticks,26);eq(flower.period,26/60)
for frame,row in ipairs({2,4})do for y=0,7 do for x=0,7 do
 local r=flower.frames[frame].under:getPixel(x,y);local er=flowerStrip:getPixel(x,(row-1)*8+y)
 eq(r,er,'native GBC flower uses only selected CGB strip rows')
end end end
local r,g,b=flower.frames[1].under:getPixel(8,0)
eq(r,0);eq(g,1/3,'flower green quadrant palette preserved');eq(b,0)
sets.flowerCgbFrames={4,2}
flower=Animation.frames(flowerContext,ref,flowerSpec)
eq(flower.frames[1].under:getPixel(0,0),1,'CGB flower row order comes from checked metadata')
sets.flowerCgbFrames=nil
flower=Animation.frames(flowerContext,ref,flowerSpec)
eq(flower.frames[1].under:getPixel(0,0),1/3,'native missing-row metadata fallback is2,4')
sets.flowerCgbFrames={2,4}
local function rejectsFlower(change,undo,needle)
 change();local ok,why=pcall(Animation.frames,flowerContext,ref,flowerSpec);undo()
 eq(ok,false);eq(tostring(why):find(needle,1,true)~=nil,true,why)
end
rejectsFlower(function()flowerSpec.hash='bad'end,function()flowerSpec.hash=hash(flowerStripBytes)end,'strip fingerprint')
rejectsFlower(function()flowerSpec.manifestHash='bad'end,function()flowerSpec.manifestHash=hash(metadata)end,'metadata fingerprint')
rejectsFlower(function()sets.flowerCgbFrames={0,4}end,function()sets.flowerCgbFrames={2,4}end,'CGB flower rows are invalid')
rejectsFlower(function()block[2]=20 end,function()block[2]=3 end,'another native tile animation')
rejectsFlower(function()ts.anim.frames[2].func='StandingTileFrame8'end,function()ts.anim.frames[2].func='AnimateFlowerTile'end,'no native flower animation')
rejectsFlower(function()ref.quadrant=3 end,function()ref.quadrant=0 end,'no native animated flower')
ref.game='red';flowerSpec.hash=hash(table.concat(flowerBytes))
rejectsFlower(function()flowerBytes[1]='changed'end,function()flowerBytes[1]='flower one bytes'end,'frames fingerprint')
rejectsFlower(function()ts.animation='TILEANIM_WATER'end,function()ts.animation='TILEANIM_WATER_FLOWER'end,'no native flower animation')
rejectsFlower(function()block[2]=20 end,function()block[2]=3 end,'another native tile animation')
print('Native GB water/flower animation: '..checks..' checks passed')
return checks
