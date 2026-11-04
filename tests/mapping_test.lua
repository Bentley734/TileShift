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
local wetAsset=clone(base);wetAsset.base=wetAsset.donor;wetAsset.donor=nil
wetAsset.kind='original';wetAsset.asset='assets/original/fixture.png';wetAsset.assetFileHash=b
wetAsset.animated=true;wetAsset.animation={bank='general_water',hash=b,manifestHash=a}
eq(M.validate(wetAsset),true,'fingerprinted native animation beneath an original asset is valid')
local noAssetBase=clone(wetAsset);noAssetBase.base=nil
eq(M.validate(noAssetBase),nil,'animated original artwork requires its native base')
local badAssetBank=clone(wetAsset);badAssetBank.animation.manifestHash='stale'
eq(M.validate(badAssetBank),nil,'animated original artwork requires a bank fingerprint')
local foam=clone(wetAsset)
foam.assetFrames={{asset=foam.asset,hash=foam.assetFileHash},{asset='assets/original/phase2.png',hash=a}}
eq(M.validate(foam),true,'original overlay phases have checked paths and hashes')
for _,mutate in ipairs({function(r)r.assetFrames[1].hash=a end,
 function(r)r.assetFrames[2].hash='stale'end,function(r)r.assetFrames[2].asset='assets/original/../escape.png'end,
 function(r)r.assetFrames[4]=r.assetFrames[2]end,function(r)r.animated=false end,
 function(r)r.assetFrames={}end})do
 local bad=clone(foam);mutate(bad);eq(M.validate(bad),nil,'invalid overlay phases fail closed')
end
local recolored=clone(base);recolored.donor=nil;recolored.kind='source_palette'
recolored.sourceColors={}
for q=1,4 do recolored.sourceColors[q]={{248,240,216},{176,184,168},{96,112,120},{32,40,56}} end
eq(M.validate(recolored),true,'reviewed source can retain its exact art with four checked quadrant palettes')
for _,mutate in ipairs({function(r)r.sourceColors=nil end,function(r)r.sourceColors={}end,
 function(r)r.sourceColors[2]=nil end,function(r)r.sourceColors.extra={}end,
 function(r)r.sourceColors[0]=r.sourceColors[1]end,function(r)r.sourceColors[5]=r.sourceColors[1]end,
 function(r)r.sourceColors[1][2]=nil end,function(r)r.sourceColors[1][5]={1,2,3}end,
 function(r)r.sourceColors[1][1][2]=nil end,function(r)r.sourceColors[1][1][4]=255 end,
 function(r)r.sourceColors[1][1][1]=-1 end,function(r)r.sourceColors[1][1][1]=256 end,
 function(r)r.sourceColors[1][1][1]=1.5 end,function(r)r.sourceColors[1][1][1]='248'end,
 function(r)r.sourceColors[1][1][1]=math.huge end,function(r)r.sourceColors[1][1][1]=0/0 end,
 function(r)r.game='ruby'end,function(r)r.style='gold'end,
 function(r)r.donor=clone(base.donor)end,function(r)r.base=clone(base.donor)end,
 function(r)r.asset='assets/original/extra.png'end,function(r)r.parts={}end,
 function(r)r.animated=true end,function(r)r.animation={}end,
 function(r)r.foreground={}end,function(r)r.artOverlay={}end})do
 local bad=clone(recolored);mutate(bad);eq(M.validate(bad),nil,'source recolors reject malformed palettes, mixed origins and geometry changes')
end
local unrelated=clone(base);unrelated.sourceColors=clone(recolored.sourceColors)
eq(M.validate(unrelated),nil,'source colors cannot silently attach to another artwork origin')
-- Native GB animation in a composite must mark its changing source explicitly.
local classic=clone(gba);classic.style='gen1';classic.donor=nil;classic.kind='native_composite'
classic.base={game='red',tileset='OVERWORLD',id=4,quadrant=0,hash=b,monochrome=true}
classic.parts={{donor=clone(classic.base),w=8,h=8,animated=true}}
classic.animated=true;classic.animation={kind='gb',bank='flower',hash=b,manifestHash=a}
eq(M.validate(classic),true,'checked GB glyph animates inside a Gen3 composition')
local current=clone(classic);current.style='gen2'
current.base={game='crystal',tileset='TILESET_CAVE',id=15,quadrant=0,hash=b}
current.parts[1].donor=clone(current.base);current.animation.bank='program'
for _,direction in ipairs({'north','south','east','west'})do
 current.animation.flowDirection=direction
 eq(M.validate(current),true,'explicit native-glyph current direction is supported')
end
current.animation.flowDirection='diagonal'
eq(M.validate(current),nil,'unknown current direction is rejected')
current.animation.flowDirection='east';current.animation.bank='water'
eq(M.validate(current),nil,'directional flow cannot change an unrelated animation bank')
for _,mutate in ipairs({function(r)r.animated=nil end,function(r)r.animated=false end,
 function(r)r.animation=true end,function(r)r.parts[1].animated=nil end,
 function(r)r.parts[1].animated=false end,function(r)r.parts[1].animated=1 end,
 function(r)r.parts[1].layers={'under'};r.parts[1].layerHashes={under=b}end})do
 local bad=clone(classic);mutate(bad)
 local ok,why=M.validate(bad);eq(ok,nil,'ambiguous GB animation composition fails at validation');eq(type(why),'string')
end
local badProfile=clone(bank);badProfile.animation=true
eq(M.validate(badProfile),nil,'non-table animation profile is rejected without an exception')
-- Imported hack artwork retains its third-party origin even when it is an
-- animated transparent overlay above a checked native background bank.
local imported=clone(foam);imported.kind='third_party'
imported.credit='Named hack artist';imported.sourceUrl='https://example.com/hack'
imported.asset='assets/third_party/hack/foam-1.png'
imported.assetFrames[1].asset=imported.asset
imported.assetFrames[2].asset='assets/third_party/hack/foam-2.png'
eq(M.validate(imported),true,'credited third-party overlay phases use the existing checked bank')
for _,mutate in ipairs({function(r)r.credit=nil end,function(r)r.sourceUrl=nil end,
 function(r)r.sourceUrl='http://example.com/hack'end,
 function(r)r.assetFrames[2].asset='assets/original/phase2.png'end,
 function(r)r.assetFrames[2].asset='assets/third_party/hack/../escape.png'end,
 function(r)r.assetFrames[2].hash='stale'end,
 function(r)r.assetFrames[1].asset='assets/third_party/hack/other.png'end,
 function(r)r.assetFrames[4]=r.assetFrames[2]end})do
 local bad=clone(imported);mutate(bad)
 eq(M.validate(bad),nil,'third-party phase origin, credit, first frame, bounds and fingerprints remain strict')
end
local importedOverlay=clone(layered)
importedOverlay.credit=imported.credit;importedOverlay.sourceUrl=imported.sourceUrl
importedOverlay.artOverlay={kind='third_party',asset='assets/third_party/hack/tree.png',
 hash=a,mode='over',preserveRects={{0,0,4,4}}}
eq(M.validate(importedOverlay),true,'native recipes may preserve exact pixels above an explicit third-party overlay')
for _,mutate in ipairs({function(r)r.credit=nil end,function(r)r.sourceUrl=nil end,
 function(r)r.sourceUrl='file:///hack'end,function(r)r.artOverlay.kind=nil end,
 function(r)r.artOverlay.kind='unknown'end,
 function(r)r.artOverlay.asset='assets/original/tree.png'end,
 function(r)r.artOverlay.asset='assets/third_party/hack/../escape.png'end,
 function(r)r.artOverlay.hash='stale'end,
 function(r)r.artOverlay.mode='blend'end,
 function(r)r.artOverlay.preserveRects={{15,0,2,16}}end})do
 local bad=clone(importedOverlay);mutate(bad)
 eq(M.validate(bad),nil,'third-party overlays retain origin, credit, hashes and retained rectangle boundaries')
end
local existingOverlay=clone(layered)
existingOverlay.artOverlay={asset='assets/original/tree.png',hash=a,preserveRects={}}
eq(M.validate(existingOverlay),true,'existing original overlays remain compatible without a new origin field')
-- Cerulean's real Red bicycle is an explicitly borrowed native object; the
-- Crystal theme and all ordinary donor matching remain strict by default.
local borrowed=clone(gba);borrowed.style='gen2';borrowed.donor=nil;borrowed.kind='native_composite'
borrowed.base={game='crystal',tileset='TILESET_JOHTO',id=2,quadrant=0,hash=b}
borrowed.parts={{donor={game='red',tileset='CLUB',id=1,quadrant=0,hash=b,monochrome=true},
  donorStyle='gen1',w=8,h=8}}
eq(M.validate(borrowed),true,'explicit native monochrome Red object may appear on Crystal-themed GBA ground')
for _,game in ipairs({'ruby','sapphire','emerald','firered','leafgreen'})do
 local supported=clone(borrowed);supported.game=game
 eq(M.validate(supported),true,'explicit borrowing is supported only by the five GBA hosts: '..game)
end
eq(M.donorMatches('gen2','red'),false,'the Crystal theme does not globally pool Red donors')
eq(M.donorMatches('gen1','crystal'),false,'borrowing does not change the Gen1 theme')
for _,mutate in ipairs({
 function(r)r.parts[1].donorStyle=nil end,
 function(r)r.parts[1].donorStyle='gen2'end,
 function(r)r.parts[1].donorStyle='gen3'end,
 function(r)r.parts[1].donorStyle='red'end,
 function(r)r.parts[1].donorStyle=false end,
 function(r)r.parts[1].donorStyle=1 end,
 function(r)r.parts[1].donor.monochrome=nil end,
 function(r)r.parts[1].donor.monochrome=false end,
 function(r)r.parts[1].donor.game='blue'end,
 function(r)r.parts[1].donor.game='yellow'end,
 function(r)r.parts[1].donor.game='crystal'end,
 function(r)r.parts[1].donor.kind='field_object'end,
 function(r)r.parts[1].donor.hash='changed'end,
 function(r)r.parts[1].donor.quadrant=4 end,
 function(r)r.kind='original'end,
 function(r)r.game='gold';r.quadrant=0 end,
 function(r)r.game='red';r.quadrant=0 end,
 function(r)r.style='gen1';r.base=clone(r.parts[1].donor)end,
 function(r)r.style='gen3';r.base={game='emerald',tileset='PAIR',id=1,hash=b}end
})do
 local bad=clone(borrowed);mutate(bad)
 local ok,why=M.validate(bad);eq(ok,nil,'unreviewed cross-theme borrowing fails closed');eq(type(why),'string')
end
local borrowedAnimation=clone(borrowed)
borrowedAnimation.animated=true;borrowedAnimation.animation={kind='gb',bank='flower',hash=b,manifestHash=a}
borrowedAnimation.parts[1].animated=true
eq(M.validate(borrowedAnimation),nil,'the borrowed Red object cannot acquire an animation program')
local nativeAnimation=clone(borrowedAnimation)
nativeAnimation.parts[1].donor=clone(borrowed.base);nativeAnimation.parts[1].donorStyle=nil
eq(M.validate(nativeAnimation),true,'ordinary Crystal native animation remains supported')
local borrowedGround=clone(borrowed);borrowedGround.base=clone(borrowed.parts[1].donor)
borrowedGround.base.donorStyle='gen1'
eq(M.validate(borrowedGround),nil,'base donors cannot use the part-only override')
local borrowedDirect=clone(borrowed);borrowedDirect.parts=nil;borrowedDirect.base=nil;borrowedDirect.kind='native'
borrowedDirect.donor=clone(borrowed.parts[1].donor);borrowedDirect.donorStyle='gen1'
eq(M.validate(borrowedDirect),nil,'direct donors cannot use the part-only override')
print('PASS strict mapping validation: '..count..' assertions')
