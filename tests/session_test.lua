local root=assert(arg and arg[1],'TileShift directory required')
local Session=assert(loadfile(root..'/lib/session.lua'))()
local Mapping=assert(loadfile(root..'/lib/mapping.lua'))()
local count=0
local function eq(a,b,message)
  count=count+1;assert(a==b,(message or 'mismatch')..': '..tostring(a)..' ~= '..tostring(b))
end
local function newData(w,h)
  local d={w=w,h=h,pixels={}}
  function d:getDimensions()return self.w,self.h end
  function d:getPixel(x,y)
    local p=self.pixels[y*self.w+x] or {0,0,0,0};return p[1],p[2],p[3],p[4]
  end
  function d:setPixel(x,y,r,g,b,a)self.pixels[y*self.w+x]={r,g,b,a or 1}end
  function d:paste(source,dx,dy,sx,sy,sw,sh)
    sx,sy=sx or 0,sy or 0;sw,sh=sw or source.w,sh or source.h
    for y=0,sh-1 do for x=0,sw-1 do self:setPixel(dx+x,dy+y,source:getPixel(sx+x,sy+y))end end
  end
  return d
end
local function fill(r,g,b,a)
  local d=newData(16,16)
  for y=0,15 do for x=0,15 do d:setPixel(x,y,r,g,b,a)end end
  return d
end
local hashA,hashB,hashC=string.rep('a',64),string.rep('b',64),string.rep('c',64)
local function row(id,quadrant)
  return {game='red',style='gen3',tileset='OVERWORLD',id=id,quadrant=quadrant,
    role='reviewed floor',status='reviewed',evidence='visual fixture',sourceHash=hashA,
    donor={game='emerald',tileset='PAIR',id=id,hash=hashB}}
end
local piece={under=fill(1,0,0,1),mid=newData(16,16),over=newData(16,16),foreground=fill(0,1,0,1)}
piece.mid:setPixel(0,0,0,1,0,1);piece.over:setPixel(1,0,0,0,1,1)
local original=fill(1,1,0,1)
local function make(rows,extra)
  local warnings,calls,invalidations={}, {},0
  local decoder={}
  function decoder:invalidate()invalidations=invalidations+1 end
  function decoder:cell(ref)
    calls[#calls+1]=ref
    if ref.hashOnly then
      if ref.hash~=hashA then return nil,'source fingerprint changed' end
      return {under=fill(.5,.5,.5,1),over=newData(16,16)}
    end
    if ref.hash~=hashB then return nil,'donor fingerprint changed' end
    return {under=piece.under,mid=piece.mid,over=piece.over,foreground=piece.foreground}
  end
  function decoder:frames(ref,animation)
    if animation.hash~=hashB or animation.manifestHash~=hashA then return nil,'animation fingerprint changed' end
    return {frames={{under=fill(.25,.5,.75,1),over=newData(16,16)},
      {under=fill(.75,.5,.25,1),over=newData(16,16)}},bank=animation.bank,counter='primary',
      ticks=animation.bank=='slow' and 32 or 16,period=(animation.bank=='slow' and 32 or 16)/60,
      offset=1/60}
  end
  local ctx={mappings=rows,donor=decoder,newImageData=newData,generations=Mapping.generations,
    validate=Mapping.validate,original=function(path)
      if path=='assets/original/special.png' then return original end
    end,foreground=function(ref)
      if ref.effect=='valid' then return fill(1,0,1,1) end
      return nil,'missing foreground fixture'
    end,warn=function(message)warnings[#warnings+1]=message end}
  for k,v in pairs(extra or {})do ctx[k]=v end
  return Session.new(ctx),warnings,calls,function()return invalidations end
end
local first,last=row(7,0),row(7,3)
local s,warnings,calls,invalidations=make({first,last})
eq(s.style,'original');eq(s:replacements('red','OVERWORLD'),nil);eq(#calls,0)
eq(s:select('gen3'),true);eq(s.revision,1);eq(invalidations(),1)
eq(s:select('gen3'),false);eq(s.revision,1);eq(invalidations(),1)
local def={id='SOURCE_MAP'}
local blocks=s:replacements('red','OVERWORLD',def)
eq(s.accepted,2);eq(s.rejected,0);eq(#warnings,0)
local block=blocks[7]
eq(block.coverage[0],true);eq(block.coverage[3],true)
eq(block.coverage[1],nil);eq(block.coverage[2],nil)
local r,g,b,a=block.image:getPixel(20,1);eq(a,0,'unreviewed quadrants remain transparent')
r,g,b,a=block.image:getPixel(0,0);eq(r,0);eq(g,1);eq(b,0,'middle layer copied')
r,g,b,a=block.image:getPixel(1,0);eq(r,0);eq(g,0);eq(b,1,'over layer copied')
r,g,b,a=block.image:getPixel(16,16);eq(g,1,'second reviewed quadrant assembled independently')
r,g,b,a=block.foreground:getPixel(0,0);eq(g,1);eq(a,1)
eq(calls[1].hashOnly,true);eq(calls[1].hash,hashA)
local before=#calls;eq(s:replacements('red','OVERWORLD',def),blocks)
eq(#calls,before,'repeat draw reuses validated art');eq(s.accepted,2,'cached access does not inflate coverage')
eq(s:replacements('emerald','OVERWORLD'),nil,'same-cartridge style leaves native renderer')
local revision=s.revision;local ok=pcall(function()s:select('unrecognized')end)
eq(ok,false);eq(s.revision,revision);eq(s.style,'gen3')
eq(s:select('original'),true);eq(s.accepted,0);eq(s.rejected,0);eq(invalidations(),2)
eq(s:replacements('red','OVERWORLD',def),nil)
eq(s:select('gen3'),true)
local rebuilt=s:replacements('red','OVERWORLD',def)
eq(rebuilt~=blocks,true,'style switching drops composed art cache')

local badSource,badDonor,unreviewed=row(1,0),row(2,0),row(3,0)
badSource.sourceHash=hashC;badDonor.donor.hash=hashC;unreviewed.status='candidate'
local rejected,warns,refs=make({badSource,badDonor,unreviewed})
rejected:select('gen3')
local out=rejected:replacements('red','OVERWORLD',def)
eq(next(out),nil);eq(rejected.accepted,0);eq(rejected.rejected,3)
eq(#warns,3);eq(#refs,3,'unreviewed mapping never asks donor decoder')
eq(warns[1]:find('fingerprint changed',1,true)~=nil,true)
local rejectedAgain=rejected:replacements('red','OVERWORLD',def)
eq(rejectedAgain,out);eq(#warns,3,'rejected mapping warned only once per reason')

local generated=row(4,1);generated.donor=nil;generated.kind='original';generated.asset='assets/original/special.png'
local generatedState=make({generated});generatedState:select('gen3')
local generatedOut=generatedState:replacements('red','OVERWORLD',def)
r,g,b,a=generatedOut[4].image:getPixel(16,0);eq(r,1);eq(g,1);eq(b,0);eq(a,1)
eq(generatedState.accepted,1,'reviewed original art supported')
local absent=row(4,1);absent.donor=nil;absent.kind='original';absent.asset='assets/original/missing.png'
local missing,warns=make({absent});missing:select('gen3')
eq(next(missing:replacements('red','OVERWORLD',def)),nil)
eq(missing.rejected,1);eq(#warns,1)

local withMask=row(5,2);withMask.occludes=true;withMask.foreground={effect='valid'}
local masked=make({withMask});masked:select('gen3')
local maskedOut=masked:replacements('red','OVERWORLD',def)
r,g,b,a=maskedOut[5].foreground:getPixel(0,16);eq(r,1);eq(g,0);eq(b,1)
local noMask=row(5,2);noMask.occludes=true;noMask.foreground={effect='missing'}
local unsafe,warns=make({noMask});unsafe:select('gen3')
eq(next(unsafe:replacements('red','OVERWORLD',def)),nil);eq(unsafe.rejected,1);eq(#warns,1)
eq(warns[1]:find('missing foreground fixture',1,true)~=nil,true)

local gen2row=row(6,0);gen2row.game='gold';gen2row.tileset='TILESET_JOHTO'
local gen2,_,sourceRefs=make({gen2row});gen2:select('gen3')
local nativeDef={id='NATIVE',tileset='TILESET_JOHTO',environment='ROUTE'}
gen2:replacements('gold','TILESET_JOHTO',nativeDef)
eq(sourceRefs[1].hashOnly,true);eq(sourceRefs[1].map,nativeDef,
  'native Gen2 map context passes by identity without mutations')
eq(nativeDef.environment,'ROUTE')

local gba=row(9,nil);gba.game='ruby';gba.tileset='PAIR';gba.style='red'
gba.donor={game='red',tileset='OVERWORLD',id=1,quadrant=0,hash=hashB}
local layered=make({gba});layered:select('red')
local layeredOut=layered:replacements('ruby','PAIR',def)
eq(layeredOut[9].under,piece.under);eq(layeredOut[9].mid,piece.mid);eq(layeredOut[9].over,piece.over)
eq(layeredOut[9].image,nil,'native Gen3 layer structure is retained')
-- Transparent tree art borrows only a fingerprint-checked ground donor; its
-- clear pixels must show that selected game's ground rather than the source.
local treeArt=newData(16,16);treeArt:setPixel(2,2,1,0,1,1)
local tree=row(11,0);tree.donor=nil;tree.kind='third_party';tree.asset='assets/third_party/tree.png'
tree.credit='Fixture artist';tree.sourceUrl='https://example.com/trees'
tree.base={game='emerald',tileset='PAIR',id=1,hash=hashB}
local treeState=make({tree},{original=function(path)
  eq(path,'assets/third_party/tree.png');return treeArt
end})
treeState:select('gen3');local treeOut=treeState:replacements('red','OVERWORLD',def)
r,g,b,a=treeOut[11].image:getPixel(5,5);eq(r,1);eq(g,0);eq(b,0);eq(a,1,'transparent art shows donor ground')
r,g,b,a=treeOut[11].image:getPixel(0,0);eq(g,1,'ground middle layer included')
r,g,b,a=treeOut[11].image:getPixel(1,0);eq(b,1,'ground over layer included')
r,g,b,a=treeOut[11].image:getPixel(2,2);eq(r,1);eq(g,0);eq(b,1,'third-party art composited over ground')
eq(treeState.accepted,1)
local badTree=row(12,1);badTree.donor=nil;badTree.kind='third_party';badTree.asset=tree.asset
badTree.credit=tree.credit;badTree.sourceUrl=tree.sourceUrl
badTree.base={game='emerald',tileset='PAIR',id=1,hash=hashC}
local staleTree,staleWarnings=make({badTree},{original=function()return treeArt end})
staleTree:select('gen3');eq(next(staleTree:replacements('red','OVERWORLD',def)),nil)
eq(staleTree.accepted,0);eq(staleTree.rejected,1)
eq(staleWarnings[1]:find('donor fingerprint changed',1,true)~=nil,true,'stale ground rejected')
local throwingOriginal,throwWarnings=make({generated},{original=function()error('invalid PNG fixture')end})
throwingOriginal:select('gen3')
eq(next(throwingOriginal:replacements('red','OVERWORLD',def)),nil,'asset decoder exception is contained')
eq(throwingOriginal.rejected,1);eq(throwWarnings[1]:find('invalid PNG fixture',1,true)~=nil,true)
local throwingMask,maskWarnings=make({withMask},{foreground=function()error('mask PNG fixture')end})
throwingMask:select('gen3')
eq(next(throwingMask:replacements('red','OVERWORLD',def)),nil,'foreground decoder exception contained')
eq(throwingMask.rejected,1);eq(maskWarnings[1]:find('mask PNG fixture',1,true)~=nil,true)
local animatedRow=row(13,0);animatedRow.animated=true;animatedRow.frames={1,2}
local unsupportedAnimation,animationWarnings=make({animatedRow})
unsupportedAnimation:select('gen3')
eq(next(unsupportedAnimation:replacements('red','OVERWORLD',def)),nil,'unsupported animation never presented as static artwork')
eq(unsupportedAnimation.rejected,1)
eq(animationWarnings[1]:find('awaiting integration',1,true)~=nil,true)
local shadow=fill(0,0,0,0);shadow:setPixel(1,1,0,0,1,128/255)
local shadowRow=row(14,0);shadowRow.donor=nil;shadowRow.kind='original'
shadowRow.asset='assets/original/shadow.png';shadowRow.assetFileHash=hashB
shadowRow.base={game='emerald',tileset='PAIR',id=1,hash=hashB}
local shadowState=make({shadowRow},{original=function(_,fileHash)
  eq(fileHash,hashB,'asset file fingerprint reaches loader');return shadow
end})
shadowState:select('gen3');local shadowOut=shadowState:replacements('red','OVERWORLD',def)
r,g,b,a=shadowOut[14].image:getPixel(1,1)
eq(r,127/255);eq(g,0);eq(b,128/255);eq(a,1,'semi-transparent artwork source-over blends onto opaque donor ground')
shadowRow.base=nil
local floatingShadow=make({shadowRow},{original=function()return shadow end})
floatingShadow:select('gen3');local floatingOut=floatingShadow:replacements('red','OVERWORLD',def)
r,g,b,a=floatingOut[14].image:getPixel(1,1);eq(r,0);eq(g,0);eq(b,1);eq(a,128/255,
  'source-over onto empty layer retains straight RGB and alpha')

local recipe={bank='general_water',hash=hashB,manifestHash=hashA}
local wet=row(15,0);wet.animated=true;wet.animation=recipe
local dry=row(15,1)
local wetLast=row(15,3);wetLast.animated=true;wetLast.animation=recipe
local animatedState=make({wetLast,dry,wet});animatedState:select('gen3')
local animatedOut=animatedState:replacements('red','OVERWORLD',def)[15]
eq(#animatedOut.frames,2);eq(animatedOut.period,16/60);eq(animatedOut.offset,1/60)
eq(animatedOut.bank,'general_water');eq(animatedState.accepted,3);eq(animatedState.rejected,0)
r,g,b,a=animatedOut.frames[1]:getPixel(0,0);eq(r,.25);eq(g,.5);eq(b,.75)
r,g,b,a=animatedOut.frames[2]:getPixel(0,0);eq(r,.75);eq(g,.5);eq(b,.25)
r,g,b,a=animatedOut.frames[1]:getPixel(20,3);eq(r,1);eq(g,0);eq(b,0)
r,g,b,a=animatedOut.frames[2]:getPixel(20,3);eq(r,1);eq(g,0);eq(b,0,'static neighboring quadrant preserved in every frame')
r,g,b,a=animatedOut.frames[2]:getPixel(0,20);eq(a,0,'unreviewed quadrant remains transparent in all frames')
r,g,b,a=animatedOut.frames[2]:getPixel(16,16);eq(r,.75,'second matching cycle included in same block')
local slow=row(15,3);slow.animated=true
slow.animation={bank='slow',hash=hashB,manifestHash=hashA}
local incompatible,cycleWarnings=make({slow,wet});incompatible:select('gen3')
local compatibleOnly=incompatible:replacements('red','OVERWORLD',def)[15]
eq(compatibleOnly.coverage[0],true);eq(compatibleOnly.coverage[3],true)
eq(incompatible.accepted,2);eq(incompatible.rejected,0)
eq(#cycleWarnings,0)
eq(compatibleOnly.cellAnimations[0].period,16/60)
eq(compatibleOnly.cellAnimations[3]~=nil,true)
local staleAnimation=row(16,0);staleAnimation.animated=true
staleAnimation.animation={bank='general_water',hash=hashC,manifestHash=hashA}
local staleSequence,sequenceWarnings=make({staleAnimation});staleSequence:select('gen3')
eq(next(staleSequence:replacements('red','OVERWORLD',def)),nil)
eq(staleSequence.rejected,1);eq(sequenceWarnings[1]:find('animation fingerprint changed',1,true)~=nil,true)
local gbaAnimation=row(17,nil);gbaAnimation.game='ruby';gbaAnimation.tileset='PAIR'
gbaAnimation.animated=true;gbaAnimation.animation=recipe
local pendingGba,gbaWarnings=make({gbaAnimation});pendingGba:select('gen3')
eq(pendingGba:replacements('ruby','PAIR',def),nil,'Gen3 host already matches pooled theme and retains native tiles')
eq(pendingGba.rejected,0)

local generic,pond,ocean=row(18,0),row(18,0),row(18,0)
pond.map='POND';pond.donor.id=20;ocean.map='OCEAN';ocean.donor.id=21
local scopedDecoder={invalidate=function()end,cell=function(_,ref)
  if ref.hashOnly then return {under=fill(.5,.5,.5,1)} end
  return {under=ref.id==20 and fill(0,1,0,1) or ref.id==21 and fill(0,0,1,1) or fill(1,0,0,1)}
end}
local scoped=make({ocean,pond,generic},{donor=scopedDecoder});scoped:select('gen3')
local pondOut=scoped:replacements('red','OVERWORLD',{id='POND'})[18]
local oceanOut=scoped:replacements('red','OVERWORLD',{id='OCEAN'})[18]
local otherOut=scoped:replacements('red','OVERWORLD',{id='OTHER'})[18]
r,g,b,a=pondOut.image:getPixel(0,0);eq(r,0);eq(g,1);eq(b,0,'pond-specific equivalent overrides generic after deterministic sort')
r,g,b,a=oceanOut.image:getPixel(0,0);eq(r,0);eq(g,0);eq(b,1,'ocean mapping restricted to its source map')
r,g,b,a=otherOut.image:getPixel(0,0);eq(r,1);eq(g,0);eq(b,0,'unrelated map retains generic reviewed equivalent')
eq(pondOut~=oceanOut,true,'map-specific compositions use separate cache entries')
local em,fr,lg=row(19,0),row(19,1),row(19,3)
fr.donor.game='firered';lg.donor.game='leafgreen'
local mixedDecoder={invalidate=function()end,cell=function(_,ref)
  if ref.hashOnly then return {under=fill(.5,.5,.5,1)} end
  return {under=ref.game=='emerald' and fill(1,0,0,1) or ref.game=='firered' and fill(0,1,0,1) or fill(0,0,1,1)}
end}
local pooled=make({lg,em,fr},{donor=mixedDecoder})
eq(pooled:select('emerald'),true);eq(pooled.style,'gen3')
local pooledRevision=pooled.revision
eq(pooled:select('leafgreen'),false,'legacy GBA aliases remain one target theme')
eq(pooled.revision,pooledRevision)
local mixed=pooled:replacements('red','OVERWORLD',def)[19]
r,g,b,a=mixed.image:getPixel(0,0);eq(r,1);eq(g,0);eq(b,0)
r,g,b,a=mixed.image:getPixel(16,0);eq(r,0);eq(g,1);eq(b,0,'FireRed donor can share pooled theme with Emerald')
r,g,b,a=mixed.image:getPixel(16,16);eq(r,0);eq(g,0);eq(b,1,'LeafGreen donor can share same block theme')
eq(pooled.accepted,3);eq(pooled.rejected,0)
for _,game in ipairs({'ruby','sapphire','emerald','firered','leafgreen'})do
  eq(pooled:replacements(game,'PAIR',def),nil,'native Gen3 host keeps original cartridge graphics')
end
-- Shared source blocks must have independent art at each reviewed occurrence.
local function positioned(x,y,path)
  local r=row(7,y%2*2+x%2);r.map='POSITIONED';r.x=x;r.y=y
  r.donor=nil;r.kind='original';r.asset=path or 'assets/original/special.png'
  return r
end
local yellowPath,bluePath='assets/original/special.png','assets/original/blue.png'
local blue=fill(0,0,1,1)
local positionDef={id='POSITIONED',width=2,height=1,blocks={7,7}}
local perPosition,pwarns=make({row(7,0),row(7,3),positioned(0,0),positioned(1,1,bluePath),positioned(2,0,bluePath)},
  {original=function(path)return path==bluePath and blue or original end})
perPosition:select('gen3')
local positionedArt=perPosition:replacements('red','OVERWORLD',positionDef)[7]
local left,right=positionedArt.positions['0:0'],positionedArt.positions['1:0']
eq(#pwarns,0);eq(perPosition.accepted,5)
eq(select(1,positionedArt.image:getPixel(2,2)),1,'generic block keeps its red art')
eq(select(2,left.image:getPixel(2,2)),1,'left occurrence gets yellow instead')
eq(select(3,left.image:getPixel(18,18)),1,'another quadrant shares that occurrence variant')
eq(select(3,right.image:getPixel(2,2)),1,'right occurrence independently gets blue')
eq(select(1,right.image:getPixel(18,18)),1,'unmodified right quadrant inherits generic art')
eq(left.image~=right.image,true);eq(left.image~=positionedArt.image,true)
eq(positionDef.blocks[1],7);eq(positionDef.blocks[2],7,'logical map block IDs remain untouched')
local nonPositioned=perPosition:replacements('red','OVERWORLD',{id='OTHER'})[7]
eq(nonPositioned.positions,nil,'coordinate art cannot leak to another map')
local mismatch,_,mismatchCalls=make({positioned(0,0)})
mismatch:select('gen3')
eq(next(mismatch:replacements('red','OVERWORLD',{id='POSITIONED',width=2,height=1,blocks={8,7}})),nil)
eq(mismatch.rejected,1);eq(#mismatchCalls,0,'layout mismatch rejected before reading art')
local outside,_,outsideCalls=make({positioned(4,0)})
outside:select('gen3');eq(next(outside:replacements('red','OVERWORLD',positionDef)),nil)
eq(#outsideCalls,0,'outside-map art never reaches decoder')
local incomplete=positioned(0,0);incomplete.y=nil
local malformed=make({incomplete});malformed:select('gen3')
eq(next(malformed:replacements('red','OVERWORLD',positionDef)),nil,'invalid coordinates are contained')
local animBase=row(7,0);animBase.animated=true
animBase.animation={bank='general_water',hash=hashB,manifestHash=hashA}
local animatedPosition=make({animBase,positioned(1,1)})
animatedPosition:select('gen3')
local animatedBlock=animatedPosition:replacements('red','OVERWORLD',positionDef)[7]
local variant=animatedBlock.positions['0:0']
eq(variant.bank,animatedBlock.bank);eq(variant.offset,animatedBlock.offset)
eq(select(1,variant.frames[1]:getPixel(2,2)),.25,'generic animation frame0 inherited')
eq(select(1,variant.frames[2]:getPixel(2,2)),.75,'generic animation frame1 inherited')
eq(select(2,variant.frames[1]:getPixel(18,18)),1,'static positional quadrant retained in frame0')
eq(select(2,variant.frames[2]:getPixel(18,18)),1,'static positional quadrant retained in frame1')
eq(select(4,animatedBlock.frames[1]:getPixel(18,18)),0,'generic frame stays transparent outside coverage')
local wetRoof=positioned(1,1)
wetRoof.kind='native_composite';wetRoof.asset=nil
wetRoof.base={game='firered',tileset='OCEAN',id=299,hash=hashB}
wetRoof.parts={{donor={game='emerald',tileset='ROOF',id=4,hash=hashB},w=16,h=16}}
wetRoof.animated=true;wetRoof.animation={bank='general_water',hash=hashB,manifestHash=hashA}
local composeFramesCalls=0
local function composeRoof(r)
  composeFramesCalls=composeFramesCalls+1;eq(r,wetRoof,'full composition reaches animation service')
  local frames={}
  for i=1,2 do
    local under=fill(0,0,i/2,1);under:setPixel(0,0,1,1,0,1)
    frames[i]={under=under,over=newData(16,16)}
  end
  return {frames=frames,bank='general_water',counter='primary',ticks=16,period=16/60,offset=1/60}
end
local roofState,roofWarnings=make({wetRoof,row(7,2),animBase},{composeFrames=composeRoof,
  compose=function()error('animated composition reached static service')end})
roofState:select('gen3')
local roofBlock=roofState:replacements('red','OVERWORLD',positionDef)[7]
local roofVariant=roofBlock.positions['0:0']
eq(#roofWarnings,0);eq(roofState.accepted,3);eq(roofState.rejected,0);eq(composeFramesCalls,1)
eq(roofVariant.bank,roofBlock.bank);eq(roofVariant.period,16/60);eq(roofVariant.offset,1/60)
eq(#roofVariant.frames,2);eq(roofVariant.coverage[3],true);eq(roofBlock.coverage[3],nil)
for i=1,2 do
  eq(select(1,roofVariant.frames[i]:getPixel(0,0)),i==1 and .25 or .75,'generic water inherited by positioned roof')
  eq(select(1,roofVariant.frames[i]:getPixel(16,16)),1,'opaque positioned roof stays static')
  eq(select(3,roofVariant.frames[i]:getPixel(18,18)),i/2,'exposed positioned water changes in every frame')
  eq(select(1,roofVariant.frames[i]:getPixel(1,17)),1,'static neighboring quadrant inherited by every roof frame')
  eq(select(4,roofBlock.frames[i]:getPixel(18,18)),0,'other occurrence cannot inherit positioned roof pixels')
end
eq(positionDef.blocks[1],7);eq(positionDef.blocks[2],7,'animated art never changes logical blocks')
local cachedRoof=roofState:replacements('red','OVERWORLD',positionDef)[7]
eq(cachedRoof,roofBlock);eq(composeFramesCalls,1,'sequence cached with source context')
roofState:select('original');eq(roofState:replacements('red','OVERWORLD',positionDef),nil)
roofState:select('gen3');eq(roofState:replacements('red','OVERWORLD',positionDef)[7]~=roofBlock,true,'theme cleanup drops animated composite images')
local unavailable,unavailableWarnings=make({wetRoof},{compose=function()error('must not freeze animated roof')end})
unavailable:select('gen3');eq(next(unavailable:replacements('red','OVERWORLD',positionDef)),nil)
eq(unavailable.rejected,1);eq(unavailableWarnings[1]:find('animation service is unavailable',1,true)~=nil,true)
for _,service in ipairs({function()return nil,'changed bank fingerprint'end,function()error('missing bank pixels')end,
  function()return {frames={},period=16/60}end})do
  local failed,failedWarnings=make({wetRoof},{composeFrames=service})
  failed:select('gen3');eq(next(failed:replacements('red','OVERWORLD',positionDef)),nil,'failed bank never publishes a static first frame')
  eq(failed.rejected,1);eq(#failedWarnings,1)
end
local incompatible,conflictWarnings=make({animBase,wetRoof},{composeFrames=function()
  local sequence=composeRoof(wetRoof);sequence.bank='other';return sequence
end})
incompatible:select('gen3')
local conflict=incompatible:replacements('red','OVERWORLD',positionDef)[7]
eq(incompatible.accepted,2);eq(incompatible.rejected,0);eq(conflict.positions~=nil,true,'position variant supports independent cycles')
eq(#conflictWarnings,0)
local guardedSource=row(27,0)
guardedSource.sourceFiles={metadata=hashA,image=hashB,maps=hashC}
local guardedState,_,guardedCalls=make({guardedSource});guardedState:select('gen3')
guardedState:replacements('red','OVERWORLD',def)
eq(guardedCalls[1].sourceFiles,guardedSource.sourceFiles,'all recorded source guards reach GB source validation unchanged')
for _,name in ipairs({'metadata','maps','image','palettes','roofs'})do
  local sourceReads,artReads,composeReads,frameReads=0,0,0,0
  local rejected=make({wetRoof},{donor={invalidate=function()end,
    cell=function(_,ref)
      if ref.hashOnly then sourceReads=sourceReads+1;return nil,'Source file fingerprint changed: '..name end
      artReads=artReads+1;error('artwork decoded after source failure')
    end,frames=function()frameReads=frameReads+1;error('native bank decoded after source failure')end},
    compose=function()composeReads=composeReads+1;error('static composition after source failure')end,
    composeFrames=function()composeReads=composeReads+1;error('animated composition after source failure')end})
  rejected:select('gen3');eq(next(rejected:replacements('red','OVERWORLD',positionDef)),nil)
  eq(sourceReads,1);eq(artReads,0);eq(composeReads,0);eq(frameReads,0)
  eq(rejected.accepted,0);eq(rejected.rejected,1,'source change fails closed before any donor/composition service')
end
local identity,sourceGood,identityInvalidations='import1',true,0
local identityDecoder={sourceIdentity=function()return identity,'missing import marker'end,
  invalidate=function()identityInvalidations=identityInvalidations+1 end,
  cell=function(_,ref)
    if ref.hashOnly then
      if not sourceGood then return nil,'Source file fingerprint changed: metadata'end
      return {under=fill(.5,.5,.5,1)}
    end
    return {under=fill(1,0,0,1)}
  end}
local identityState=make({guardedSource},{donor=identityDecoder});identityState:select('gen3')
local firstImport=identityState:replacements('red','OVERWORLD',def)
local initialRevision=identityState.revision
eq(identityState:replacements('red','OVERWORLD',def),firstImport,'same import reuses its verified art cache')
identity='import2';sourceGood=false
local changedImport=identityState:replacements('red','OVERWORLD',def)
eq(next(changedImport),nil,'new import cannot reuse old composed art after metadata changed')
eq(identityState.revision,initialRevision+1,'native renderer refreshes after import identity change')
eq(identityState.accepted,0);eq(identityState.rejected,1);eq(identityInvalidations,2)
identity=nil
eq(next(identityState:replacements('red','OVERWORLD',def)),nil,'unavailable identity fails closed')
eq(identityState.revision,initialRevision+2)
eq(next(identityState:replacements('red','OVERWORLD',def)),nil)
eq(identityState.revision,initialRevision+2,'persistent identity failure does not invalidate every frame')
identity='import3';sourceGood=true
local recovered=identityState:replacements('red','OVERWORLD',def)
eq(recovered[27]~=nil,true);eq(identityState.revision,initialRevision+3)
eq(identityState.accepted,1);eq(identityState.rejected,0,'fresh import guard recovery owns a fresh cache')
print('PASS reviewed mapping session: '..count..' assertions')
