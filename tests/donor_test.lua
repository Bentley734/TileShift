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
-- Field-object donors read the neutral versioned SVOW/RGBA cache directly.
-- Their complete 16px silhouette is preserved, including transparency.
local function u16(n)return string.char(n%256,math.floor(n/256))end
local objectRoot='emerald/data/generated/gba/ow/82'
local objectMeta='SVOW'..string.char(4,1)..u16(82)..u16(16)..u16(16)..u16(2)..string.rep('\0',106)
local objectFrame=string.char(0,0,0,0)..string.rep(string.char(17,85,204,255),255)
local objectOther=string.rep(string.char(204,85,17,255),256)
files[objectRoot..'.meta']=objectMeta;files[objectRoot..'.rgba']=objectFrame..objectOther
local objectRef={game='emerald',kind='field_object',tileset='ow',id=82,frame=0,
  hash=hash(objectFrame),metaHash=hash(objectMeta),rgbaHash=hash(objectFrame..objectOther)}
local object,err=reader:cell(objectRef);assert(object,err)
eq(object.under:getString(),objectFrame);eq(object.sourceHash,objectRef.hash)
eq(object.hash,objectRef.hash);eq(object.frame,0);eq(object.kind,'field_object')
r,g,b,a=object.under:getPixel(0,0);eq(a,0)
r,g,b,a=object.under:getPixel(1,0);eq(r,17/255);eq(g,85/255);eq(b,204/255);eq(a,1)
r,g,b,a=object.over:getPixel(1,0);eq(a,0);eq(object.mid,nil)
local function objectReference(changes)
  local ref={};for k,v in pairs(objectRef)do ref[k]=v end
  for k,v in pairs(changes or {})do ref[k]=v end
  return ref
end
local nextObject=assert(reader:cell(objectReference({frame=1,hash=hash(objectOther)})))
eq(nextObject.under:getString(),objectOther,'frame-major object data uses the selected frame')
local function objectFail(changes,message)
  local failed,why=reader:cell(objectReference(changes));eq(failed,nil)
  eq(why:find(message,1,true)~=nil,true,why)
end
objectFail({metaHash='stale'},'metadata fingerprint changed')
objectFail({rgbaHash='stale'},'RGBA fingerprint changed')
objectFail({hash='stale'},'tile fingerprint changed')
objectFail({frame=2},'frame is unavailable');objectFail({frame=-1},'frame is unavailable')
objectFail({frame=.5},'frame is unavailable')
objectFail({game='gold'},'Gen3 ow reference');objectFail({tileset='PAIR'},'Gen3 ow reference')
objectFail({quadrant=0},'Gen3 ow reference');objectFail({kind='unknown'},'Unknown donor kind')
objectFail({cacheIdentity='stale'},'import identity changed')
local missingHash=objectReference();missingHash.metaHash=nil
local noObject,noObjectWhy=reader:cell(missingHash);eq(noObject,nil)
eq(noObjectWhy:find('source fingerprints are required',1,true)~=nil,true)
local function malformedObject(meta,rgba,message)
  files[objectRoot..'.meta']=meta;files[objectRoot..'.rgba']=rgba;reader:invalidate()
  objectFail({metaHash=hash(meta),rgbaHash=hash(rgba)},message)
  files[objectRoot..'.meta']=objectMeta;files[objectRoot..'.rgba']=objectFrame..objectOther;reader:invalidate()
end
malformedObject('BAD!'..objectMeta:sub(5),objectFrame..objectOther,'Invalid field-object metadata')
malformedObject(objectMeta:sub(1,4)..string.char(3)..objectMeta:sub(6),objectFrame..objectOther,'metadata version')
malformedObject(objectMeta:sub(1,6)..u16(83)..objectMeta:sub(9),objectFrame..objectOther,'graphics ID changed')
malformedObject(objectMeta:sub(1,8)..u16(32)..objectMeta:sub(11),objectFrame..objectOther,'complete 16 by 16')
malformedObject(objectMeta:sub(1,10)..u16(32)..objectMeta:sub(13),objectFrame..objectOther,'complete 16 by 16')
malformedObject(objectMeta:sub(1,12)..u16(0)..objectMeta:sub(15),objectFrame..objectOther,'frame count')
malformedObject(objectMeta:sub(1,12)..u16(257)..objectMeta:sub(15),objectFrame..objectOther,'frame count')
malformedObject(objectMeta,objectFrame,'RGBA pixels are incomplete')
local checkedObject=assert(reader:cell(objectReference({fingerprints={['82.meta']=hash(objectMeta)}})))
eq(checkedObject.cacheIdentity,hash('marker3\nmeta3'))
objectFail({fingerprints={['82.meta']='stale'}},'Donor source changed')
files['emerald/rom-cache.complete']='new-object-import'
files[objectRoot..'.rgba']=objectOther..objectFrame
local reimported,err=reader:cell(objectReference({hash=hash(objectOther),rgbaHash=hash(objectOther..objectFrame)}))
assert(reimported,err);eq(reimported.under:getString(),objectOther,'reimport identity selects fresh object bytes')
eq(reimported.cacheIdentity,hash('new-object-import\nmeta3'))
files['emerald/rom-cache.complete']='marker3';files[objectRoot..'.rgba']=objectFrame..objectOther;reader:invalidate()
-- Static arrows use only their named neutral RGBA cache and metadata. The
-- native frame index, complete sheet and exact16px output are fingerprinted.
local arrowRoot='firered/data/generated/gba/field_effects/arrow'
local arrowMeta={w=16,h=128,fw=16,fh=16,frames=8,indexed=false,format=2}
module('firered','data/generated/gba/field_effects/arrow.meta',arrowMeta)
local arrowMetaBytes=files[arrowRoot..'.meta'];local arrowFrames={}
for frame=0,7 do
  local bytes={}
  for y=0,15 do for x=0,15 do
    bytes[#bytes+1]=string.char(frame*17,x*13,y*11,(x==0 and y==0)and 0 or(x==2 and y==3)and 128 or 255)
  end end
  arrowFrames[#arrowFrames+1]=table.concat(bytes)
end
local arrowBlob=table.concat(arrowFrames);files[arrowRoot..'.rgba']=arrowBlob
local arrowRef={game='firered',kind='field_effect',tileset='arrow',id=0,
  hash=hash(arrowFrames[1]),metaHash=hash(arrowMetaBytes),rgbaHash=hash(arrowBlob)}
local function arrowReference(changes)
  local ref={};for k,v in pairs(arrowRef)do ref[k]=v end
  for k,v in pairs(changes or {})do ref[k]=v end;return ref
end
for frame=0,7 do
  local effect=assert(reader:cell(arrowReference({id=frame,hash=hash(arrowFrames[frame+1])})))
  eq(effect.under:getString(),arrowFrames[frame+1],'entire native frameRGBA, including hidden transparent RGB, is unchanged')
  eq(effect.sourceHash,hash(arrowFrames[frame+1]));eq(effect.kind,'field_effect');eq(effect.frame,frame)
  eq(select(4,effect.over:getPixel(2,3)),0)
end
local function arrowFail(changes,message)
  local failed,why=reader:cell(arrowReference(changes));eq(failed,nil)
  eq(why:find(message,1,true)~=nil,true,why)
end
arrowFail({metaHash='stale'},'metadata fingerprint changed')
arrowFail({rgbaHash='stale'},'sheet fingerprint changed')
arrowFail({hash='stale'},'tile fingerprint changed')
arrowFail({id=8},'frame is unavailable');arrowFail({game='gold'},'named Gen3 arrow reference')
arrowFail({tileset='cut_grass'},'named Gen3 arrow reference')
arrowFail({quadrant=0},'without a quadrant');arrowFail({frame=0},'frame override')
arrowFail({cacheIdentity='stale'},'import identity changed')
local missingArrow=arrowReference();missingArrow.metaHash=nil
local missing,why=reader:cell(missingArrow);eq(missing,nil);eq(why:find('fingerprints are required',1,true)~=nil,true)
local function malformedArrow(changes,blob,message)
  local meta={};for k,v in pairs(arrowMeta)do meta[k]=v end
  for k,v in pairs(changes)do meta[k]=v end
  decoded[arrowMetaBytes]=meta;files[arrowRoot..'.rgba']=blob or arrowBlob;reader:invalidate()
  arrowFail({rgbaHash=hash(blob or arrowBlob)},message)
  decoded[arrowMetaBytes]=arrowMeta;files[arrowRoot..'.rgba']=arrowBlob;reader:invalidate()
end
for _,changes in ipairs({{fw=0},{fw=17},{fh=17},{w=15},{h=127},{frames=0},{frames=7},{frames=9}})do
  malformedArrow(changes,nil,'eight complete native frames')
end
malformedArrow({format=1},nil,'pixel format');malformedArrow({indexed='true'},nil,'pixel format')
malformedArrow({},arrowBlob:sub(2),'RGBA pixels are incomplete')
local small={w=8,h=64,fw=8,fh=8,frames=8,indexed=true,format=2}
local smallFrame=string.rep(string.char(23,67,199,255),64)
decoded[arrowMetaBytes]=small;files[arrowRoot..'.rgba']=string.rep(smallFrame,8);reader:invalidate()
local padded=newData(16,16)
for y=0,7 do for x=0,7 do padded:setPixel(x+4,y+4,23/255,67/255,199/255,1)end end
local smallEffect=assert(reader:cell(arrowReference({hash=hash(padded:getString()),rgbaHash=hash(files[arrowRoot..'.rgba'])})))
eq(smallEffect.under:getString(),padded:getString(),'smaller native canvas is centered with transparent padding, never scaled')
decoded[arrowMetaBytes]=arrowMeta;files[arrowRoot..'.rgba']=arrowBlob;reader:invalidate()
local checkedArrow=assert(reader:cell(arrowReference({fingerprints={['arrow.meta']=hash(arrowMetaBytes),['arrow.rgba']=hash(arrowBlob)}})))
eq(checkedArrow.under:getString(),arrowFrames[1])
local noAnimation,animationError=reader:frames(arrowRef,{bank='water',hash='x',manifestHash='y'})
eq(noAnimation,nil);eq(animationError:find('metatile donor',1,true)~=nil,true,'effect frame cannot start a tile-bank timeline')
-- Source file guards protect behavior and event data even when the pixels
-- decode identically. Hashes are cached per import identity and invalidation.
local function sourceHash(bytes)
  return string.rep('0',56)..string.format('%08x',tonumber(hash(bytes):sub(5)))
end
local sourceReads,sourceImages={},0
local guardedReader=Donor.new({read=function(path)sourceReads[path]=(sourceReads[path]or 0)+1;return files[path]end,
 decode=function(bytes)return decoded[bytes]end,prefix=function(game)return game..'/'end,
 newImageData=newData,loadImage=function()sourceImages=sourceImages+1;return sheet end,
 hash=sourceHash,nativePack=nativePack})
local metadataPath='red/data/generated/tilesets.lua'
local mapsPath='red/data/generated/maps.lua'
local imagePath='red/assets/generated/test.png'
-- Use the strict native image namespace required by recorded source guards.
local oldImageName=tilesets.TEST.image;tilesets.TEST.image='assets/generated/tilesets/test.png'
local sourceImagePath='red/'..tilesets.TEST.image;files[sourceImagePath]=files[imagePath]
local guards={metadata=sourceHash(files[metadataPath]),maps=sourceHash(files[mapsPath]),image=sourceHash(files[sourceImagePath])}
local guardedRef={game='red',tileset='TEST',id=0,quadrant=0,hashOnly=true,sourceFiles=guards}
local verified=assert(guardedReader:cell(guardedRef));local unchangedPixels=verified.hash
local counts={};for k,v in pairs(sourceReads)do counts[k]=v end
assert(guardedReader:cell(guardedRef))
eq(sourceReads[mapsPath],counts[mapsPath],'map bytes hashed once per import identity')
eq(sourceReads[sourceImagePath],counts[sourceImagePath],'image hash and image decode cached')
eq(sourceImages,1)
local function sourceFailure(name,newBytes)
  local path=name=='metadata'and metadataPath or name=='maps'and mapsPath or sourceImagePath
  local previous=files[path];files[path]=newBytes;decoded[newBytes]=decoded[previous]
  guardedReader:invalidate();local before=sourceImages
  local failed,why=guardedReader:cell(guardedRef);eq(failed,nil)
  eq(why:find('Source file fingerprint changed: '..name,1,true)~=nil,true,why)
  eq(sourceImages,before,'changed source is rejected before loading any source picture')
  local legacy={game='red',tileset='TEST',id=0,quadrant=0,hashOnly=true}
  eq(assert(guardedReader:cell(legacy)).hash,unchangedPixels,'changed source bytes can leave all decoded pixels identical')
  files[path]=previous;guardedReader:invalidate()
end
local previousWalkable=tilesets.TEST.walkable;tilesets.TEST.walkable={255}
sourceFailure('metadata','changed-walkability-metadata')
tilesets.TEST.walkable=previousWalkable
local sourceMapTable=decoded[files[mapsPath]];local previousEvents=sourceMapTable.TEST_MAP.coordEvents
sourceMapTable.TEST_MAP.coordEvents={{x=1,y=1,flag='different-event'}}
sourceFailure('maps','changed-source-event-map')
sourceMapTable.TEST_MAP.coordEvents=previousEvents
sourceFailure('image','different-PNG-encoding-with-identical-pixels')
assert(guardedReader:cell(guardedRef))
local previousMarker=files['red/rom-cache.complete'];local previousMaps=files[mapsPath]
files['red/rom-cache.complete']='new-source-import';files[mapsPath]='different-import-map-bytes'
local rechecked,why=guardedReader:cell(guardedRef)
eq(rechecked,nil);eq(why:find('fingerprint changed: maps',1,true)~=nil,true,'new import identity cannot reuse old raw-file hashes')
files['red/rom-cache.complete']=previousMarker;files[mapsPath]=previousMaps;guardedReader:invalidate()
local optional={};for k,v in pairs(guards)do optional[k]=v end
optional.palettes=sourceHash(files['red/data/generated/palettes.lua'])
module('red','data/generated/roofs.lua',{roofs={}});optional.roofs=sourceHash(files['red/data/generated/roofs.lua'])
guardedRef.sourceFiles=optional;assert(guardedReader:cell(guardedRef))
for _,name in ipairs({'palettes','roofs'})do
  local path='red/data/generated/'..name..'.lua';local bytes=files[path]
  files[path]=bytes..'-changed';guardedReader:invalidate()
  local before=sourceImages;local failed,why=guardedReader:cell(guardedRef)
  eq(failed,nil);eq(why:find('fingerprint changed: '..name,1,true)~=nil,true);eq(sourceImages,before)
  files[path]=bytes;guardedReader:invalidate()
end
guardedRef.sourceFiles=guards
local removed=files[mapsPath];files[mapsPath]=nil;guardedReader:invalidate()
local failed,why=guardedReader:cell(guardedRef);eq(failed,nil);eq(why:find('import missing',1,true)~=nil,true)
files[mapsPath]=removed;guardedReader:invalidate()
guards.unknown=guards.maps
failed,why=guardedReader:cell(guardedRef);eq(failed,nil);eq(why:find('Invalid source file fingerprint',1,true)~=nil,true)
guards.unknown=nil;tilesets.TEST.image=oldImageName
local identityToken,markerReads=0,0
local batched=Donor.new({read=function(path)
 if path=='red/rom-cache.complete'then markerReads=markerReads+1 end
 return files[path]
end,decode=function(bytes)return decoded[bytes]end,prefix=function(game)return game..'/'end,
 newImageData=newData,hash=sourceHash,identityToken=function()return identityToken end})
local firstIdentity=assert(batched:sourceIdentity('red'))
for i=1,200 do eq(batched:sourceIdentity('red'),firstIdentity,'same update reuses its import marker digest')end
eq(markerReads,1,'visible blocks do not reopen the import marker')
local oldMarker=files['red/rom-cache.complete'];files['red/rom-cache.complete']='next-frame-import'
identityToken=identityToken+1
eq(batched:sourceIdentity('red')~=firstIdentity,true,'next update observes a changed import')
eq(markerReads,2)
batched:invalidate();assert(batched:sourceIdentity('red'))
eq(markerReads,3,'explicit invalidation drops the token cache immediately')
files['red/rom-cache.complete']=oldMarker
for _,path in ipairs(reads)do
  local cartridge=path:match('^([^/]+)/')
  eq(cartridge=='red' or cartridge=='gold' or cartridge=='crystal' or cartridge=='emerald'
    or cartridge=='firered' or cartridge=='leafgreen',true,
    'reads stay in the explicitly selected cartridge')
  eq(path:sub(1,1)~='/',true,'all cache reads are relative')
end
print('PASS cross-generation donor decoder: '..count..' assertions')
