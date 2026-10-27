local root=assert(arg and arg[1],'TileShift directory required')
local M=assert(loadfile(root..'/lib/mapping.lua'))()
local count=0
local function eq(a,b,message)
  count=count+1;assert(a==b,(message or 'mismatch')..': '..tostring(a)..' ~= '..tostring(b))
end
local function clone(value)
  if type(value)~='table' then return value end
  local out={};for k,v in pairs(value)do out[k]=clone(v)end;return out
end
local a,b=string.rep('a',64),string.rep('b',64)
local base={game='red',style='gen3',tileset='OVERWORLD',id=7,quadrant=0,
  role='plain grass',status='reviewed',evidence='visually compared native cells',sourceHash=a,
  donor={game='emerald',tileset='PAIR',id=1,hash=b}}
eq(M.validate(base),true)
local function rejects(mutator,message)
  local row=clone(base);mutator(row)
  local ok,why=M.validate(row);eq(ok,nil,message);eq(type(why),'string')
end
rejects(function(r)r.quadrant=nil end,'GB source quadrant must be explicit')
rejects(function(r)r.quadrant=4 end)
rejects(function(r)r.quadrant=-1 end)
rejects(function(r)r.quadrant=.5 end)
rejects(function(r)r.quadrant='0' end)
rejects(function(r)r.game='unknown'end)
rejects(function(r)r.style='original'end)
rejects(function(r)r.tileset=''end)
rejects(function(r)r.id=-1 end)
rejects(function(r)r.id=65536 end)
rejects(function(r)r.id=.5 end)
rejects(function(r)r.role=''end)
rejects(function(r)r.evidence=''end)
rejects(function(r)r.status='candidate'end)
rejects(function(r)r.sourceHash=string.rep('A',64)end)
rejects(function(r)r.sourceHash=string.rep('x',64)end)
rejects(function(r)r.sourceHash=a:sub(2)end)
rejects(function(r)r.donor.game='gold'end,'pooled Gen3 theme cannot borrow a GB donor')
rejects(function(r)r.donor.id=-1 end)
rejects(function(r)r.donor.tileset=''end)
rejects(function(r)r.donor.hash=string.rep('x',64)end)
rejects(function(r)r.asset='assets/original/extra.png'end,'exactly one artwork origin')
local gba=clone(base);gba.game='ruby';gba.tileset='PAIR';gba.quadrant=nil
eq(M.validate(gba),true,'Gen3 native metatile does not need GB quadrant')
local gbDonor=clone(base);gbDonor.style='gold';gbDonor.donor={game='gold',tileset='TILESET_JOHTO',id=1,quadrant=4,hash=b}
eq(M.validate(gbDonor),nil,'GB donor quadrant bounds enforced')
local original=clone(base);original.donor=nil;original.kind='original';original.asset='assets/original/dive.png'
eq(M.validate(original),true)
local unknown=clone(original);unknown.kind=nil;eq(M.validate(unknown),nil,'asset origin required')
for _,path in ipairs({'assets/third_party/tree.png','assets/original/../tree.png',
  '/assets/original/tree.png','assets/original/tree.jpg','assets/original/tree.png/extra'})do
  local row=clone(original);row.asset=path;eq(M.validate(row),nil,'asset path validation')
end
local third=clone(original);third.kind='third_party';third.asset='assets/third_party/tree.png'
third.credit='Named artist';third.sourceUrl='https://example.com/tiles'
eq(M.validate(third),true,'credited third-party artwork accepted')
for _,field in ipairs({'credit','sourceUrl'})do
  local row=clone(third);row[field]=nil;eq(M.validate(row),nil,'third-party credit and source required')
end
local insecure=clone(third);insecure.sourceUrl='http://example.com/tiles';eq(M.validate(insecure),nil)
local wrongPrefix=clone(third);wrongPrefix.asset='assets/original/tree.png';eq(M.validate(wrongPrefix),nil)
third.base={game='emerald',tileset='PAIR',id=1,hash=b}
eq(M.validate(third),true,'asset ground donor accepted')
local badGround=clone(third);badGround.base.game='gold';eq(M.validate(badGround),nil,'ground style must match')
badGround=clone(third);badGround.base.tileset='';eq(M.validate(badGround),nil,'ground tileset required')
badGround=clone(third);badGround.base.hash=string.rep('x',64);eq(M.validate(badGround),nil,'ground fingerprint must be hex')
badGround=clone(third);badGround.style='gold';badGround.base={game='gold',tileset='TILESET_JOHTO',id=1,quadrant=4,hash=b}
eq(M.validate(badGround),nil,'GB ground quadrant bounds enforced')
local occluding=clone(base);occluding.occludes=true;eq(M.validate(occluding),nil,'occlusion requires explicit mask')
occluding.foreground={effect='reviewed-mask'};eq(M.validate(occluding),true)
local animated=clone(base);animated.animated=true;eq(M.validate(animated),nil)
animated.frames={1,2};eq(M.validate(animated),true,'animation structure must be explicit before runtime support check')
local second=clone(base);second.quadrant=3
local indexed,errors=M.index({base,second})
eq(#errors,0);eq(indexed[M.key(base)],base);eq(indexed[M.key(second)],second)
eq(M.key(base)~=M.key(second),true,'quadrants have distinct identities')
local duplicate,duplicateErrors=M.index({base,clone(base)})
eq(duplicate[M.key(base)],base,'duplicate never silently replaces approved first row')
eq(#duplicateErrors,1);eq(duplicateErrors[1]:find('duplicate mapping',1,true)~=nil,true)
local invalid=clone(base);invalid.status='candidate'
local validOnly,invalidErrors=M.index({invalid,base})
eq(validOnly[M.key(base)],base);eq(#invalidErrors,1)
eq(#M.games,11);eq(M.generations.red,1);eq(M.generations.crystal,2);eq(M.generations.emerald,3)
local scoped=clone(base);scoped.map='PALLET_TOWN';eq(M.validate(scoped),true)
for _,scope in ipairs({'','../PALLET','map/path',17})do
  local bad=clone(base);bad.map=scope;eq(M.validate(bad),nil,'source map scope must be a native ID')
end
local otherScope=clone(scoped);otherScope.map='NEW_BARK_TOWN'
eq(M.key(scoped)~=M.key(otherScope),true,'map scopes have distinct mapping identities')
local mapIndex,mapErrors=M.index({base,scoped,otherScope})
eq(#mapErrors,0);eq(mapIndex[M.key(scoped)],scoped);eq(mapIndex[M.key(base)],base)
local hashed=clone(third);hashed.assetFileHash=b;eq(M.validate(hashed),true)
hashed.assetFileHash=string.rep('B',64);eq(M.validate(hashed),nil,'asset fingerprints are normalized hex')
hashed.assetFileHash=b:sub(2);eq(M.validate(hashed),nil)
local bank=clone(base);bank.animated=true
bank.animation={bank='general_water',hash=b,manifestHash=a}
eq(M.validate(bank),true,'verified native animation metadata accepted without fabricated frame assets')
local badBank=clone(bank);badBank.animation.hash=string.rep('x',64);eq(M.validate(badBank),nil)
badBank=clone(bank);badBank.animation.manifestHash=string.rep('x',64);eq(M.validate(badBank),nil)
badBank=clone(bank);badBank.animation.bank='../water';eq(M.validate(badBank),nil)
badBank=clone(bank);badBank.style='gold';badBank.donor={game='gold',tileset='TILESET_JOHTO',id=1,hash=b}
eq(M.validate(badBank),nil,'native RSE animation metadata cannot target a GB donor')
for _,game in ipairs({'ruby','sapphire','emerald','firered','leafgreen'})do
  local pooled=clone(base);pooled.donor.game=game
  eq(M.validate(pooled),true,'pooled Gen3 theme accepts '..game..' tile origin')
  local pooledGround=clone(third);pooledGround.base.game=game
  eq(M.validate(pooledGround),true,'pooled Gen3 ground accepts '..game)
  eq(M.normalizeStyle(game),'gen3','legacy cartridge style alias normalizes')
end
for _,game in ipairs({'red','blue','yellow','gold','silver','crystal'})do
  local exact=clone(base);exact.style=game
  exact.donor={game=game,tileset='TEST',id=1,quadrant=0,hash=b}
  eq(M.validate(exact),true,'GB theme retains exact cartridge origin')
  exact.donor.game=game=='red' and 'blue' or 'red'
  eq(M.validate(exact),nil,'GB themes do not pool different games')
end
eq(M.themes.gen3,3);eq(M.themes.emerald,nil);eq(M.themes.firered,nil)
eq(M.generations.gen3,nil,'theme IDs are not cartridge IDs')
local cartridgeStyle=clone(base);cartridgeStyle.style='emerald'
eq(M.validate(cartridgeStyle),nil,'mapping data uses themes rather than legacy cartridge aliases')
local object=clone(base)
object.donor={kind='field_object',game='emerald',tileset='ow',id=82,frame=0,hash=b,metaHash=a,rgbaHash=b}
eq(M.validate(object),true,'fingerprinted native cut-tree object is a valid donor')
for _,change in ipairs({{kind='unknown'},{tileset='PAIR'},{quadrant=0},{frame=-1},{frame=.5},
  {metaHash='bad'},{rgbaHash='bad'}})do
  local bad=clone(object);for key,value in pairs(change)do bad.donor[key]=value end
  eq(M.validate(bad),nil,'native objects require their exact origin, frame and blob fingerprints')
end
local layered=clone(base);layered.donor=nil;layered.kind='native_composite'
layered.base=clone(base.donor)
layered.parts={{donor=clone(base.donor),w=16,h=16,layers={'over'},layerHashes={over=b}}}
eq(M.validate(layered),true,'fingerprinted native roof layer is accepted over ground')
for _,change in ipairs({{layers={}},{layers={'bogus'},layerHashes={bogus=b}},
  {layers={'over','mid'},layerHashes={over=b,mid=b}},
  {layers={'over','over'}},{layers={'over',extra='mid'}},
  {layerHashes={over='bad'}},{layerHashes={over=b,mid=a}}})do
  local bad=clone(layered);for key,value in pairs(change)do bad.parts[1][key]=value end
  eq(M.validate(bad),nil,'unverifiable or ambiguous layer selection is rejected')
end
local noHashes=clone(layered);noHashes.parts[1].layerHashes=nil;eq(M.validate(noHashes),nil)
local noLayers=clone(layered);noLayers.parts[1].layers=nil;eq(M.validate(noLayers),nil)
local objectPart=clone(layered);objectPart.parts[1].donor=clone(object.donor)
objectPart.parts[1].layers=nil;objectPart.parts[1].layerHashes=nil
eq(M.validate(objectPart),true,'object graphic can compose over original donor ground')
local positioned=clone(base);positioned.map='NEW_BARK_TOWN';positioned.x=0;positioned.y=0
eq(M.validate(positioned),true,'map-cell position may distinguish a reused source graphic')
local elsewhere=clone(positioned);elsewhere.x=2
eq(M.key(positioned)~=M.key(elsewhere),true,'two occurrences have distinct mapping identities')
for _,change in ipairs({{map=false},{x=-1},{x=.5},{x=65536},{y='0'},{quadrant=3},{game='ruby'}})do
  local bad=clone(positioned);for key,value in pairs(change)do bad[key]=value end
  eq(M.validate(bad),nil,'positional art requires a bounded, quadrant-aligned GB map position')
end
local unscoped=clone(positioned);unscoped.map=nil;eq(M.validate(unscoped),nil)
local incomplete=clone(positioned);incomplete.y=nil;eq(M.validate(incomplete),nil)
local wetRoof=clone(layered);wetRoof.animated=true;wetRoof.animation=clone(bank.animation)
eq(M.validate(wetRoof),true,'a native roof may compose over a fingerprinted animated native base')
for _,game in ipairs({'red','blue','yellow','gold','silver','crystal'})do
  local supported=clone(wetRoof);supported.game=game;eq(M.validate(supported),true,'animated composition GB host '..game)
end
for _,change in ipairs({{game='ruby'},{base=false},{animation=false},{donor=clone(base.donor)},
  {asset='assets/original/extra.png'},{parts={wetRoof.parts[1],extra=wetRoof.parts[1]}}})do
  local bad=clone(wetRoof);for key,value in pairs(change)do bad[key]=value end
  eq(M.validate(bad),nil,'animated composites retain GB scope and a single explicit artwork source')
end
for _,key in ipairs({'hash','manifestHash','overHash','frame0Hash'})do
  local bad=clone(wetRoof);bad.animation[key]='changed';eq(M.validate(bad),nil,'animation fingerprints remain required: '..key)
end
local noBase=clone(wetRoof);noBase.base=nil;eq(M.validate(noBase),nil,'animated parts require their own base')
local noBank=clone(wetRoof);noBank.animation=nil;noBank.frames={1,2};eq(M.validate(noBank),nil,'fabricated frames cannot replace the native base bank')
local objectBase=clone(wetRoof);objectBase.base=clone(object.donor);eq(M.validate(objectBase),nil,'animated base must be a metatile, not an object frame')
local arrow=clone(base)
arrow.donor={game='firered',kind='field_effect',tileset='arrow',id=0,metaHash=a,rgbaHash=b,hash=b}
eq(M.validate(arrow),true,'named native static arrow frame is an explicit graphics source')
for _,change in ipairs({{kind='effect'},{tileset='tall_grass'},{id=8},{id=-1},{id=.5},{frame=0},{quadrant=0},
  {metaHash='stale'},{rgbaHash='stale'},{game='gold'}})do
  local bad=clone(arrow);for key,value in pairs(change)do bad.donor[key]=value end
  eq(M.validate(bad),nil,'arrow references require the exact name, native frame and both source fingerprints')
end
local arrowPart=clone(layered);arrowPart.parts={{donor=clone(arrow.donor),w=16,h=16}}
eq(M.validate(arrowPart),true,'transparent static arrow may overlay native ground')
local blinking=clone(arrow);blinking.animated=true;blinking.animation=clone(bank.animation)
eq(M.validate(blinking),nil,'static effect frames never acquire a native tile-bank animation')
local guarded=clone(base);guarded.sourceFiles={metadata=a,image=b,maps=a,palettes=b,roofs=a}
eq(M.validate(guarded),true,'recorded source file fingerprints include optional palette and roof tables')
for _,change in ipairs({{sourceFiles=false},{sourceFiles={}},{game='ruby'},
  {sourceFiles={metadata=a,image=b}},{sourceFiles={metadata=a,image=b,maps=a,unknown=b}},
  {sourceFiles={metadata=a,image=b,maps=a,roofs='stale'}}})do
  local bad=clone(guarded);for key,value in pairs(change)do bad[key]=value end
  eq(M.validate(bad),nil,'provided source guards are complete, known and fingerprinted')
end
print('PASS strict mapping validation: '..count..' assertions')
