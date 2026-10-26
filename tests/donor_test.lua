local root=assert(arg and arg[1],'TileShift directory required')
local Donor=assert(loadfile(root..'/lib/donor.lua'))()
local count=0
local function eq(a,b,message)
  count=count+1;assert(a==b,(message or 'mismatch')..': '..tostring(a)..' ~= '..tostring(b))
end
local function newData(w,h)
  assert(type(w)=='number','Tests load donor images through injected loader')
  local image={w=w,h=h,pixels={}}
  function image:getDimensions()return self.w,self.h end
  function image:getPixel(x,y)
    assert(x>=0 and x<self.w and y>=0 and y<self.h,'source pixels out of bounds')
    local p=self.pixels[y*self.w+x] or {0,0,0,0};return p[1],p[2],p[3],p[4]
  end
  function image:setPixel(x,y,r,g,b,a)self.pixels[y*self.w+x]={r,g,b,a or 1}end
  function image:getString()
    local out={}
    for y=0,self.h-1 do for x=0,self.w-1 do
      local r,g,b,a=self:getPixel(x,y)
      out[#out+1]=string.char(math.floor(r*255+.5),math.floor(g*255+.5),math.floor(b*255+.5),math.floor(a*255+.5))
    end end
    return table.concat(out)
  end
  return image
end
local function hash(bytes)
  local sum=0;for i=1,#bytes do sum=(sum+bytes:byte(i)*i)%100000007 end
  return 'hash'..sum
end
local sheet=newData(128,128)
for y=0,127 do for x=0,127 do
  local shade=math.floor(x/8)%4/3
  sheet:setPixel(x,y,shade,shade,shade,1)
end end
-- Different bank and flip corners are intentionally distinguishable.
sheet:setPixel(0,64,1/3,1/3,1/3,1)
sheet:setPixel(7,64,2/3,2/3,2/3,1)
local colors={{255,255,255},{255,0,0},{0,255,0},{0,0,255}}
local bgSet={};for slot=1,8 do bgSet[slot]=colors end
local block={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15}
local tilesets={TEST={image='assets/generated/test.png',tilesPerRow=16,blocks={block}},
  TILESET_JOHTO={image='assets/generated/test.png',tilesPerRow=16,blocks={block}}}
local palettes={bg={[1]=colors},environments={TOWN={DAY={1,1,1,1,1,1,1,1},NITE={1,1,1,1,1,1,1,1}}}}
local files,decoded={},{}
local function module(game,path,value)
  local full=game..'/'..path;files[full]=full;decoded[full]=value
end
for _,game in ipairs({'red','gold','crystal'})do
  module(game,'data/generated/tilesets.lua',tilesets)
  module(game,'data/generated/palettes.lua',palettes)
  module(game,'data/generated/maps.lua',{TEST_MAP={tileset='TEST',environment='TOWN',palette='PALETTE_AUTO',group=1},
    JOHTO={tileset='TILESET_JOHTO',environment='TOWN',palette='PALETTE_AUTO',group=1}})
  files[game..'/assets/generated/test.png']='png'..game
  files[game..'/rom-cache.complete']='import-marker'
end
local root3='emerald/data/generated/gba/native/PAIR/'
for _,file in ipairs({'palettes.bin','mids.idx','mids_mid.idx','mids_over.idx'})do files[root3..file]=file end
files['emerald/rom-cache.complete']='marker3';files['emerald/data/generated/gba/meta.json']='meta3'
local pixelUnder,pixelMid,pixelOver={},{},{}
for i=1,256 do pixelUnder[i]=1;pixelMid[i]=0;pixelOver[i]=0 end
pixelMid[1]=2;pixelOver[2]=3
local nativePack={}
function nativePack.decodePalettes(bytes)return {}end
function nativePack.palsToRgb8()
  return {[0]={[0]={255,255,255},[1]={255,0,0},[2]={0,255,0},[3]={0,0,255}}}
end
function nativePack.decodeIdx(bytes)
  return {midIds={77},pixels=bytes=='mids.idx' and pixelUnder or bytes=='mids_mid.idx' and pixelMid or pixelOver}
end
local reads={}
local reader=Donor.new({read=function(path)reads[#reads+1]=path;return files[path] end,
  decode=function(bytes)return decoded[bytes]end,prefix=function(game)return game..'/'end,
  newImageData=newData,loadImage=function(path,bytes)return sheet end,hash=hash,nativePack=nativePack})
local red,err=reader:cell({game='red',tileset='TEST',id=0,quadrant=0})
assert(red,err);eq(red.sourceHash,red.hash)
local r,g,b,a=red.under:getPixel(0,0);eq(r,0);eq(g,0);eq(b,0);eq(a,1)
r,g,b,a=red.under:getPixel(8,0);eq(r,85/255);eq(a,1)
r,g,b,a=red.over:getPixel(0,0);eq(a,0)
eq(red.quadrant,0);eq(red.cacheIdentity,hash('import-marker\n'))
local failed,why=reader:cell({game='red',tileset='TEST',id=0,hash='wrong'})
eq(failed,nil);eq(why:find('fingerprint changed',1,true)~=nil,true)
local gold,err=reader:cell({game='gold',tileset='TEST',id=0,map='TEST_MAP'})
assert(gold,err);eq(gold.daytime,'DAY')
r,g,b,a=gold.under:getPixel(0,0);eq(r,0);eq(g,0);eq(b,1)
eq(gold.sourceHash,red.sourceHash,'palette does not alter catalog fingerprint')
local explicit=assert(reader:cell({game='gold',tileset='TEST',id=0,palettes=bgSet}))
eq(explicit.sourceHash,gold.sourceHash)
local noMap,noMapWhy=reader:cell({game='gold',tileset='TEST',id=0})
eq(noMap,nil);eq(noMapWhy:find('needs a map',1,true)~=nil,true)
local sourceOnly=assert(reader:cell({game='gold',tileset='TEST',id=0,hashOnly=true,hash=gold.sourceHash}))
eq(sourceOnly.sourceHash,gold.sourceHash,'hash-only lookup needs no Gen2 palette context')
r,g,b,a=sourceOnly.under:getPixel(0,0);eq(r,0);eq(g,0);eq(b,0)
local wrongMap,why=reader:cell({game='gold',tileset='TILESET_JOHTO',id=0,map='TEST_MAP'})
eq(wrongMap,nil);eq(why:find('different tileset',1,true)~=nil,true)
tilesets.TEST.tileAttrs={[1]={palette=1,vramBank=1,xFlip=true,priority=true}}
reader:invalidate()
local crystal,err=reader:cell({game='crystal',tileset='TEST',id=0,map='TEST_MAP'})
assert(crystal,err)
r,g,b,a=crystal.under:getPixel(0,0);eq(r,1);eq(g,0);eq(b,0,'bank1 and horizontal flip used')
local pr,pg,pb,pa=crystal.over:getPixel(0,0);eq(pa,1);eq(pr,r);eq(pg,g);eq(pb,b)
eq(crystal.sourceHash~=red.sourceHash,true,'fingerprint includes bank and flip')
local native,err=reader:cell({game='emerald',tileset='PAIR',id=77})
assert(native,err)
r,g,b,a=native.under:getPixel(0,0);eq(r,1);eq(g,0);eq(b,0);eq(a,1)
r,g,b,a=native.mid:getPixel(0,0);eq(r,0);eq(g,1);eq(b,0);eq(a,1)
r,g,b,a=native.over:getPixel(1,0);eq(r,0);eq(g,0);eq(b,1);eq(a,1)
r,g,b,a=native.over:getPixel(0,0);eq(a,0,'overlay zero is transparent')
local flat=newData(16,16)
for y=0,15 do for x=0,15 do flat:setPixel(x,y,1,0,0,1)end end
flat:setPixel(0,0,0,1,0,1);flat:setPixel(1,0,0,0,1,1)
eq(native.sourceHash,hash(flat:getString()),'catalog fingerprint composites all layers')
eq(native.cacheIdentity,hash('marker3\nmeta3'))
local verified=assert(reader:cell({game='emerald',tileset='PAIR',id=77,hash=native.sourceHash,
  fingerprints={['mids.idx']=hash('mids.idx')},cacheIdentity=native.cacheIdentity}))
eq(verified.sourceHash,native.sourceHash)
local bad,why=reader:cell({game='emerald',tileset='PAIR',id=77,cacheIdentity='stale'})
eq(bad,nil);eq(why:find('identity changed',1,true)~=nil,true)
local missing,why=reader:cell({game='emerald',tileset='PAIR',id=78})
eq(missing,nil);eq(why:find('metatile is unavailable',1,true)~=nil,true)
local traversal=reader:cell({game='red',tileset='../TEST',id=0})
eq(traversal,nil)
local noPixels=reader:cell({game='red',tileset='TEST',id=99})
eq(noPixels,nil)
-- RSE tiles/mod bank fixture mirrors native rse_piece's frame-major packing.
-- The second, unused mid makes an incorrect frame stride visible immediately.
local animBank={name='general_water',kind='tiles',fn='mod',period=16,phase=1,
  frames=2,counter='primary',mids={77,88},quads={1,15},overMids={77},overQuads={8},
  file='anim_water.idx',overFile='anim_water_over.idx'}
local animManifest={family='rse',banks={animBank}}
module('emerald','data/generated/gba/native/PAIR/anim_manifest.lua',animManifest)
local underBlob=string.rep(string.char(2),256)..string.rep(string.char(3),256)..
  string.rep(string.char(3),256)..string.rep(string.char(1),256)
local overBlob=string.rep(string.char(3),256)..string.rep(string.char(0),256)
files[root3..'anim_water.idx']=underBlob;files[root3..'anim_water_over.idx']=overBlob
local recipe={bank='general_water',hash=hash(underBlob),overHash=hash(overBlob),
  manifestHash=hash(files[root3..'anim_manifest.lua'])}
local animatedRef={game='emerald',tileset='PAIR',id=77,hash=native.sourceHash}
local sequence,err=reader:frames(animatedRef,recipe);assert(sequence,err)
eq(#sequence.frames,2);eq(sequence.ticks,16);eq(sequence.period,16/60)
eq(sequence.phase,1);eq(sequence.offset,1/60);eq(sequence.counter,'primary')
r,g,b,a=sequence.frames[1].under:getPixel(0,0);eq(r,0);eq(g,1);eq(b,0);eq(a,1)
r,g,b,a=sequence.frames[2].under:getPixel(0,0);eq(r,0);eq(g,0);eq(b,1)
r,g,b,a=sequence.frames[2].under:getPixel(8,0);eq(r,1);eq(g,0);eq(b,0,'unmasked native under quadrant preserved')
r,g,b,a=sequence.frames[1].over:getPixel(8,8);eq(r,0);eq(g,0);eq(b,1);eq(a,1)
r,g,b,a=sequence.frames[2].over:getPixel(8,8);eq(r,0);eq(g,0);eq(b,0);eq(a,0,'over animation index zero clears pixels')
r,g,b,a=sequence.frames[2].over:getPixel(1,0);eq(b,1);eq(a,1,'unmasked static over art preserved')
eq(sequence.frames[1].mid,nil,'static mid is not redrawn over the native composite under animation')
r,g,b,a=native.under:getPixel(0,0);eq(r,1);eq(g,0);eq(b,0,'static donor pixels unchanged')
eq(reader:frames(animatedRef,recipe),sequence,'verified animation decoded once')
local function failFrames(changes,expected)
  local changed={};for k,v in pairs(recipe)do changed[k]=v end
  for k,v in pairs(changes)do changed[k]=v end
  local missing,why=reader:frames(animatedRef,changed)
  eq(missing,nil);eq(why:find(expected,1,true)~=nil,true)
end
failFrames({hash='stale'},'bank fingerprint changed')
failFrames({manifestHash='stale'},'manifest fingerprint changed')
failFrames({overHash='stale'},'over-layer fingerprint')
failFrames({bank='unavailable'},'bank is unavailable')
local unsupported,why=reader:frames({game='ruby',tileset='PAIR',id=77},recipe)
eq(unsupported,nil);eq(why:find('cartridge is unsupported',1,true)~=nil,true)
local function mutationFails(change,restore,expected)
  change();reader:invalidate()
  local missing,why=reader:frames(animatedRef,recipe)
  eq(missing,nil);eq(why:find(expected,1,true)~=nil,true)
  restore();reader:invalidate()
end
mutationFails(function()animBank.kind='palette'end,function()animBank.kind='tiles'end,'Palette animation')
mutationFails(function()animBank.fn='slot'end,function()animBank.fn='mod'end,'scheduling function')
mutationFails(function()animBank.mids={88,89};animBank.overMids={99}end,
  function()animBank.mids={77,88};animBank.overMids={77}end,'not targeted')
mutationFails(function()animBank.period=0 end,function()animBank.period=16 end,'Invalid animation period')
mutationFails(function()animBank.quads={16,15}end,function()animBank.quads={1,15}end,'quadrant mask')
mutationFails(function()animManifest.banks[2]={name='other',kind='tiles',mids={77}}end,
  function()animManifest.banks[2]=nil end,'multiple animation banks')
mutationFails(function()animManifest.banks[2]={name='palette',kind='palette',paletteSlot=0}end,
  function()animManifest.banks[2]=nil end,'unsupported palette animation')
files[root3..'anim_water.idx']=underBlob:sub(2);reader:invalidate()
failFrames({hash=hash(underBlob:sub(2))},'under pixels are incomplete')
files[root3..'anim_water.idx']=underBlob;reader:invalidate()
local restored=assert(reader:frames(animatedRef,recipe));eq(#restored.frames,2)
-- FR/LG traditional banks store complete RGBA under tiles, frame-major and
-- then metatile-major. Their static BG2 layer must remain unchanged.
local classicManifest={anim_version=1,water={frames=8,mids={88,77}},
  sand={frames=8,mids={}},flower={frames=5,mids={99}}}
local function rgbaFrame(frame,index)
  return string.rep(string.char(frame*30,index==1 and 0 or 255-frame*20,frame*7,255),256)
end
local rgba={}
for frame=0,7 do for index=1,2 do rgba[#rgba+1]=rgbaFrame(frame,index)end end
local classicBlob=table.concat(rgba)
for _,game in ipairs({'firered','leafgreen'})do
  local prefix=game..'/data/generated/gba/native/PAIR/'
  for _,file in ipairs({'palettes.bin','mids.idx','mids_mid.idx','mids_over.idx'})do files[prefix..file]=file end
  module(game,'data/generated/gba/native/PAIR/anim_manifest.lua',classicManifest)
  files[prefix..'anim_water.rgba']=classicBlob;files[game..'/rom-cache.complete']='classic-import'
end
local classicRecipe={bank='water',hash=hash(classicBlob),
  manifestHash=hash(files['firered/data/generated/gba/native/PAIR/anim_manifest.lua'])}
local classicRef={game='firered',tileset='PAIR',id=77,hash=native.sourceHash}
local classic,err=reader:frames(classicRef,classicRecipe);assert(classic,err)
eq(#classic.frames,8);eq(classic.ticks,16);eq(classic.phase,1);eq(classic.offset,1/60)
eq(classic.counter,'global');eq(classic.bank,'water')
for frame=0,7 do
  r,g,b,a=classic.frames[frame+1].under:getPixel(3,4)
  eq(r,frame*30/255);eq(g,(255-frame*20)/255);eq(b,frame*7/255);eq(a,1)
  eq(classic.frames[frame+1].over:getString(),native.over:getString(),'native static over layer preserved')
  eq(classic.frames[frame+1].mid,nil,'composed RGBA under does not acquire a stale middle layer')
end
eq(reader:frames(classicRef,classicRecipe),classic)
local leafRecipe={bank='water',hash=hash(classicBlob),
  manifestHash=hash(files['leafgreen/data/generated/gba/native/PAIR/anim_manifest.lua'])}
local leafSequence,err=reader:frames({game='leafgreen',tileset='PAIR',id=77,hash=native.sourceHash},leafRecipe)
assert(leafSequence,err);eq(#leafSequence.frames,8);eq(leafSequence~=classic,true,'cartridge caches remain separate')
local legacyBad,why=reader:frames(classicRef,{bank='water',hash='stale',manifestHash=classicRecipe.manifestHash})
eq(legacyBad,nil);eq(why:find('bank fingerprint changed',1,true)~=nil,true)
legacyBad,why=reader:frames(classicRef,{bank='water',hash=classicRecipe.hash,manifestHash='stale'})
eq(legacyBad,nil);eq(why:find('manifest fingerprint changed',1,true)~=nil,true)
legacyBad,why=reader:frames(classicRef,{bank='palette',hash=classicRecipe.hash,manifestHash=classicRecipe.manifestHash})
eq(legacyBad,nil);eq(why:find('Legacy animation bank is unsupported',1,true)~=nil,true)
classicManifest.water.frames=7;reader:invalidate()
legacyBad,why=reader:frames(classicRef,classicRecipe)
eq(legacyBad,nil);eq(why:find('frame count is unsupported',1,true)~=nil,true)
classicManifest.water.frames=8
files['firered/data/generated/gba/native/PAIR/anim_water.rgba']=classicBlob:sub(2);reader:invalidate()
legacyBad,why=reader:frames(classicRef,{bank='water',hash=hash(classicBlob:sub(2)),manifestHash=classicRecipe.manifestHash})
eq(legacyBad,nil);eq(why:find('RGBA pixels are incomplete',1,true)~=nil,true)
files['firered/data/generated/gba/native/PAIR/anim_water.rgba']=classicBlob
classicManifest.water.mids={88};classicManifest.sand.mids={77};reader:invalidate()
local sandBlob={};for frame=0,7 do sandBlob[#sandBlob+1]=rgbaFrame(frame,2)end;sandBlob=table.concat(sandBlob)
files['firered/data/generated/gba/native/PAIR/anim_sand.rgba']=sandBlob
local sand,err=reader:frames(classicRef,{bank='sand',hash=hash(sandBlob),manifestHash=classicRecipe.manifestHash})
assert(sand,err);eq(sand.ticks,8);eq(sand.phase,0);eq(sand.period,8/60)
classicManifest.sand.mids={};classicManifest.flower.mids={77};reader:invalidate()
local flowerBlob={};for frame=0,4 do flowerBlob[#flowerBlob+1]=rgbaFrame(frame,2)end;flowerBlob=table.concat(flowerBlob)
files['firered/data/generated/gba/native/PAIR/anim_flower.rgba']=flowerBlob
local flower,err=reader:frames(classicRef,{bank='flower',hash=hash(flowerBlob),manifestHash=classicRecipe.manifestHash})
assert(flower,err);eq(flower.ticks,16);eq(flower.phase,2);eq(flower.offset,2/60);eq(#flower.frames,5)
for _,path in ipairs(reads)do
  local cartridge=path:match('^([^/]+)/')
  eq(cartridge=='red' or cartridge=='gold' or cartridge=='crystal' or cartridge=='emerald'
    or cartridge=='firered' or cartridge=='leafgreen',true,
    'reads stay in the explicitly selected cartridge')
  eq(path:sub(1,1)~='/',true,'all cache reads are relative')
end
print('PASS cross-generation donor decoder: '..count..' assertions')
