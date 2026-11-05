local root=assert(arg and arg[1])
local Mapping=assert(loadfile(root..'/lib/mapping.lua'))()
local Composition=assert(loadfile(root..'/lib/composition.lua'))()
local Session=assert(loadfile(root..'/lib/session.lua'))()
local Donor=assert(loadfile(root..'/lib/donor.lua'))()
local checks=0
local function eq(a,b,why)checks=checks+1;assert(a==b,why or(tostring(a)..' ~= '..tostring(b)))end
local function copy(t)local o={};for k,v in pairs(t)do o[k]=type(v)=='table'and copy(v)or v end;return o end
local function data(w,h)
 local d={pixels={}}
 function d:getDimensions()return w,h end
 function d:getPixel(x,y)local p=self.pixels[y*w+x]or{0,0,0,0};return p[1],p[2],p[3],p[4]end
 function d:setPixel(x,y,r,g,b,a)assert(x>=0 and x<w and y>=0 and y<h);self.pixels[y*w+x]={r,g,b,a}end
 function d:paste(source,x,y)
  local width,height=source:getDimensions()
  for yy=0,height-1 do for xx=0,width-1 do self:setPixel(x+xx,y+yy,source:getPixel(xx,yy))end end
 end
 function d:getString()local o={};for y=0,h-1 do for x=0,w-1 do local r,g,b,a=self:getPixel(x,y);o[#o+1]=string.char(math.floor(r*255+.5),math.floor(g*255+.5),math.floor(b*255+.5),math.floor(a*255+.5))end end;return table.concat(o)end
 return d
end
local function hash(s)local n=0;for i=1,#s do n=(n+s:byte(i)*i)%100000007 end;return string.rep(string.format('%08x',n),8)end
local source={under=data(16,16),mid=data(16,16),over=data(16,16),staticClassic=true}
for y=0,15 do for x=0,15 do source.under:setPixel(x,y,1,0,0,1)end end
source.mid:setPixel(2,7,0,1,0,1);source.over:setPixel(12,3,0,0,1,1)
source.over:setPixel(8,9,3/255,5/255,7/255,0)
source.hash=hash(source.under:getString()..source.mid:getString()..source.over:getString());source.sourceHash=source.hash
source.animationManifestHash=hash('static-manifest')
local palette={{248,248,224},{160,192,96},{80,104,48},{24,40,24}}
local row={game='emerald',style='gen2',tileset='PAIR',id=77,kind='classic_native_geometry',role='whole_machine',status='reviewed',evidence='Named complete machine fixture',sourceHash=source.hash,compositionPixelHash=hash('independent-output'),classicGeometry={version=1,static=true,feature='whole_machine',palette=palette,colorMap={{255,0,0,248,248,224},{0,255,0,160,192,96},{0,0,255,24,40,24}},sourceLayers={},animationManifestHash=source.animationManifestHash}}
for _,name in ipairs({'under','mid','over'})do row.classicGeometry.sourceLayers[name]=hash(source[name]:getString())end
eq(Mapping.validate(row),true)
local function invalid(change)local r=copy(row);change(r);eq(Mapping.validate(r),nil)end
invalid(function(r)r.donor={}end);invalid(function(r)r.parts={}end);invalid(function(r)r.overMask=string.rep('0',256)end)
invalid(function(r)r.animated=true end);invalid(function(r)r.style='gen1'end);invalid(function(r)r.game='crystal'end)
invalid(function(r)r.compositionPixelHash=nil end);invalid(function(r)r.classicGeometry.static=false end)
invalid(function(r)r.classicGeometry.unchecked=true end);invalid(function(r)r.classicGeometry.sourceLayers.extra=hash('x')end)
invalid(function(r)r.classicGeometry.sourceLayers.over=nil end);invalid(function(r)r.classicGeometry.palette[4]=copy(palette[1])end)
invalid(function(r)r.classicGeometry.colorMap[2]=copy(r.classicGeometry.colorMap[1])end)
invalid(function(r)r.classicGeometry.colorMap[1][4]=17 end);invalid(function(r)r.classicGeometry.feature='../unsafe'end)
invalid(function(r)r.classicGeometry.colorMap[1][7]=0 end);invalid(function(r)r.classicGeometry.palette[1][1]=.5 end)
local calls=0;local decoder={}
function decoder:invalidate()end
local floor={under=data(16,16),hash=hash('native-floor')}
for y=0,15 do for x=0,15 do floor.under:setPixel(x,y,x/255,y/255,99/255,1)end end
function decoder:cell(ref)
 calls=calls+1
 if ref.game=='crystal'then return floor end
 eq(ref.staticClassic,true);eq(ref.animationManifestHash,source.animationManifestHash);return source
end
local composer=Composition.new{donor=decoder,newImageData=data,validateRow=Mapping.validate,hashImage=function(im)return hash(im:getString())end}
local before={};for _,name in ipairs({'under','mid','over'})do before[name]=source[name]:getString()end
local result=assert(composer:cell(row));eq(calls,1)
for _,name in ipairs({'under','mid','over'})do
 eq(source[name]:getString(),before[name],'source plane mutated')
 for y=0,15 do for x=0,15 do
  local sr,sg,sb,sa=source[name]:getPixel(x,y);local r,g,b,a=result[name]:getPixel(x,y);eq(a,sa,'alpha/priority geometry changed')
  if sa==0 then eq(r,sr);eq(g,sg);eq(b,sb)
  else local rgb=sr==1 and palette[1]or sg==1 and palette[2]or palette[4];eq(r,rgb[1]/255);eq(g,rgb[2]/255);eq(b,rgb[3]/255)end
 end end
end
local function failed(r,s)local p,why=composer:cell(r,s);eq(p,nil);assert(type(why)=='string')end
local altered=copy(row);altered.classicGeometry.colorMap[2]=nil;failed(altered,source)
altered=copy(row);altered.classicGeometry.colorMap={altered.classicGeometry.colorMap[1]};failed(altered,source)
altered=copy(row);altered.classicGeometry.sourceLayers.mid=hash('wrong');failed(altered,source)
local saved=source.staticClassic;source.staticClassic=false;failed(row,source);source.staticClassic=saved
saved=source.animationManifestHash;source.animationManifestHash=hash('changed');failed(row,source);source.animationManifestHash=saved
saved=source.hash;source.hash=hash('changed');source.sourceHash=source.hash;failed(row,source);source.hash=saved;source.sourceHash=saved
source.mid:setPixel(2,7,0,1,0,.5);altered=copy(row);altered.classicGeometry.sourceLayers.mid=hash(source.mid:getString());failed(altered,source);source.mid:setPixel(2,7,0,1,0,1)
local grounded=copy(row)
grounded.classicGeometry.ground={donor={game='crystal',tileset='TILESET_TEST',id=0,quadrant=0,hash=floor.hash},masks={under='1'..string.rep('0',255)}}
eq(Mapping.validate(grounded),true)
local groundResult=assert(composer:cell(grounded,source));eq(groundResult.under:getString():sub(1,4),floor.under:getString():sub(1,4))
eq(groundResult.under:getString():sub(5),result.under:getString():sub(5),'floor mask changed feature pixels')
eq(groundResult.over:getString(),result.over:getString(),'floor mask changed priority')
grounded.classicGeometry.ground.masks.over='1'..string.rep('0',255);failed(grounded,source)
grounded.classicGeometry.ground.masks.over=nil;grounded.classicGeometry.ground.donor.game='emerald';eq(Mapping.validate(grounded),nil)
local indexed=assert(Mapping.index({row}));local session=Session.new{mappings=indexed,donor=decoder,newImageData=data,generations=Mapping.generations,themes=Mapping.themes,normalizeStyle=Mapping.normalizeStyle,validate=Mapping.validate,compose=function(r,s)return composer:cell(r,s)end,warn=error}
session:select('gen2');local rows=session:replacements('emerald','PAIR');eq(session.accepted,1);eq(session.rejected,0)
local merged=data(16,16);merged:paste(result.under,0,0);merged:setPixel(2,7,result.mid:getPixel(2,7))
eq(rows[77].under:getString(),merged:getString(),'Native background lost visible middle-layer pixels')
eq(rows[77].mid:getString(),data(16,16):getString(),'Native atlas receives a duplicate middle layer')
eq(rows[77].over:getString(),result.over:getString(),'Session flattened the foreground priority plane')
local warm=calls;eq(session:replacements('emerald','PAIR'),rows);eq(calls,warm,'warm access decodes again')
session:select('original');eq(session:replacements('emerald','PAIR'),nil)
-- Static architecture remains on its original priority plane while both
-- duplicate water backgrounds follow the selected native GB frame sequence.
local ones=string.rep('1',256)
local animated=copy(row);animated.id=78
local animatedSource={under=source.under,mid=source.under,over=source.over,staticClassic=true,
 animationManifestHash=source.animationManifestHash,classicGroundMaskKey=ones..':'..ones..':'}
animatedSource.hash=hash(animatedSource.under:getString()..animatedSource.mid:getString()..animatedSource.over:getString());animatedSource.sourceHash=animatedSource.hash
animated.sourceHash=animatedSource.hash
animated.classicGeometry.sourceLayers.mid=hash(animatedSource.mid:getString())
animated.classicGeometry.ground={donor={game='crystal',tileset='TEST',id=0,quadrant=0,hash=floor.hash},masks={under=ones,mid=ones},
 animation={kind='gb',bank='water',hash=hash('water-frames'),manifestHash=hash('gb-metadata')}}
eq(Mapping.validate(animated),true)
local frame2={under=data(16,16)}
for y=0,15 do for x=0,15 do frame2.under:setPixel(x,y,(255-x)/255,(255-y)/255,55/255,1)end end
local frameCalls=0;local staticCell=decoder.cell
function decoder:cell(ref)
 if ref.id==78 and ref.game=='emerald'then calls=calls+1;assert(ref.classicGroundMasks.under==ones and ref.classicGroundMasks.mid==ones);return animatedSource end
 return staticCell(self,ref)
end
function decoder:frames(ref,spec)
 frameCalls=frameCalls+1;eq(ref.game,'crystal');eq(spec.hash,hash('water-frames'))
 return{frames={floor,frame2},period=.25,offset=.125,bank='water'}
end
local sequence=assert(composer:frames(animated));eq(#sequence.frames,2);eq(sequence.period,.25);eq(sequence.offset,.125)
for index,expected in ipairs({floor,frame2})do
 for _,name in ipairs({'under','mid'})do eq(sequence.frames[index][name]:getString(),expected.under:getString(),'animated ground freezes or changes duplicate-plane geometry')end
 eq(sequence.frames[index].over:getString(),result.over:getString(),'animated ground changed static architecture or hidden transparent RGB')
end
eq(assert(composer:cell(animated)).under:getString(),sequence.frames[1].under:getString(),'static/Off frame differs from native frame0')
altered=copy(animated);altered.classicGeometry.ground.animation.kind='unchecked';eq(Mapping.validate(altered),nil)
altered=copy(animated);altered.classicGeometry.ground.masks.mid='0'..ones:sub(2);eq(composer:frames(altered,animatedSource),nil)
local repeated=copy(animated);repeated.classicGeometry.ground.animation.bank='program';repeated.classicGeometry.ground.repeatWidth=8
local repeatedSequence=assert(composer:frames(repeated));eq(#repeatedSequence.frames,2)
for _,frame in ipairs(repeatedSequence.frames)do
 for y=0,15 do for x=0,7 do
  local r,g,b,a=frame.under:getPixel(x,y);local rr,gg,bb,aa=frame.under:getPixel(x+8,y)
  eq(r,rr);eq(g,gg);eq(b,bb);eq(a,aa)
 end end
end
repeated.classicGeometry.ground.repeatWidth=7;eq(Mapping.validate(repeated),nil)
local animatedIndex=assert(Mapping.index({animated}));local animatedState=Session.new{mappings=animatedIndex,donor=decoder,newImageData=data,
 generations=Mapping.generations,themes=Mapping.themes,normalizeStyle=Mapping.normalizeStyle,validate=Mapping.validate,
 compose=function(r,s)return composer:cell(r,s)end,composeFrames=function(r,s)return composer:frames(r,s)end,warn=error}
animatedState:select('gen2');local animatedRows=animatedState:replacements('emerald','PAIR');local replacement=animatedRows[78]
eq(animatedState.accepted,1);eq(animatedState.rejected,0);eq(#replacement.frames,2);eq(replacement.category,'water');eq(replacement.period,.25);eq(replacement.offset,.125)
for index,expected in ipairs(sequence.frames)do
 local frame=replacement.frames[index]
 eq(frame.under:getString(),expected.under:getString(),'Session changed animated background')
 eq(frame.mid:getString(),data(16,16):getString(),'Native atlas receives a duplicate middle layer')
 eq(frame.over:getString(),expected.over:getString(),'Session changed animated foreground')
end
local warmFrames,warmCalls=frameCalls,calls;eq(animatedState:replacements('emerald','PAIR'),animatedRows);eq(frameCalls,warmFrames);eq(calls,warmCalls)
animatedState:select('original');eq(animatedState:replacements('emerald','PAIR'),nil)
local preserved=copy(row);preserved.id=79
preserved.classicGeometry.nativeOver={bank='steam',hash=hash('over-bank')}
preserved.classicGeometry.colorMap[3]=nil
eq(Mapping.validate(preserved),true)
local preservedSource={under=source.under,mid=source.mid,over=source.over,hash=source.hash,
 animationManifestHash=source.animationManifestHash,staticClassic=true,classicNativeOver='steam:'..hash('over-bank')}
local animatedCell=decoder.cell
function decoder:cell(ref)
 if ref.id==79 then
  eq(ref.classicNativeOver.bank,'steam');eq(ref.classicNativeOver.hash,hash('over-bank'))
  return preservedSource
 end
 return animatedCell(self,ref)
end
local kept=assert(composer:cell(preserved));eq(kept.over:getString(),source.over:getString(),'Native effect RGB or alpha was rewritten')
local preservedIndex=assert(Mapping.index({preserved}));local preservedState=Session.new{mappings=preservedIndex,donor=decoder,newImageData=data,
 generations=Mapping.generations,themes=Mapping.themes,normalizeStyle=Mapping.normalizeStyle,validate=Mapping.validate,
 compose=function(r,s)return composer:cell(r,s)end,warn=error}
preservedState:select('gen2');local retained=preservedState:replacements('emerald','PAIR')[79]
eq(retained.over,nil,'Theme would overwrite native foreground animation')
eq(retained.under:getString(),merged:getString(),'Native background lost visible middle-layer pixels')
eq(retained.mid:getString(),data(16,16):getString(),'Native atlas receives a duplicate middle layer')
altered=copy(preserved);altered.classicGeometry.ground={donor={game='crystal',tileset='TEST',id=0,quadrant=0,hash=floor.hash},masks={over=ones}}
eq(Mapping.validate(altered),nil)
local shoreline=copy(animated);shoreline.id=80
shoreline.classicGeometry.nativeOver=preserved.classicGeometry.nativeOver
shoreline.classicGeometry.sourceAnimation={mode='water_mask',bank='water',hash=hash('native-water')}
eq(Mapping.validate(shoreline),true)
local shoreSource={}
for key,value in pairs(animatedSource)do shoreSource[key]=value end
shoreSource.classicNativeOver=preservedSource.classicNativeOver
shoreSource.classicSourceAnimation='water_mask:water:'..hash('native-water')
local shoreCell=decoder.cell
function decoder:cell(ref)
 if ref.id==80 then return shoreSource end
 return shoreCell(self,ref)
end
local shoreState=Session.new{mappings=assert(Mapping.index({shoreline})),donor=decoder,newImageData=data,
 generations=Mapping.generations,themes=Mapping.themes,normalizeStyle=Mapping.normalizeStyle,validate=Mapping.validate,
 compose=function(r,s)return composer:cell(r,s)end,composeFrames=function(r,s)return composer:frames(r,s)end,warn=error}
shoreState:select('gen2')
local shore=shoreState:replacements('emerald','PAIR')[80]
eq(shore.over,nil,'Animated background must leave native foreground available')
for index,frame in ipairs(shore.frames)do
 eq(frame.over,nil,'Background frame must never overwrite retained foreground')
 eq(frame.under:getString(),sequence.frames[index].under:getString(),'Retained foreground changes animated background')
end
altered=copy(shoreline);altered.classicGeometry.sourceAnimation.mode='native_under'
eq(Mapping.validate(altered),nil)
-- The real donor rejects static artwork on both tile and palette animation
-- banks, including legacy FR/LG banks and transparent overlay palette zeros.
local manifest={banks={}};local reads=0;local withMid,withOver=false,false
local bankBytes=string.rep('q',512)
local lightBytes=string.rep(string.char(1),256)..string.char(2)..string.rep(string.char(1),255)
local pixels={};for i=1,256 do pixels[i]=1 end
local pack={decodePalettes=function()return{}end,palsToRgb8=function()return{[0]={[0]={5,7,9},[1]={255,0,0},[2]={0,255,0}}}end,
 decodeIdx=function()return{midIds={77},pixels=pixels}end}
local d=Donor.new{read=function(path)
 reads=reads+1
 if(path:find('mids_mid')and not withMid)or(path:find('mids_over')and not withOver)or path:find('rom%-cache')or path:find('meta.json',1,true)then return nil end
 if path:find('steam.idx',1,true)then return bankBytes end
 if path:find('lights.idx',1,true)then return lightBytes end
 return path:find('anim_manifest',1,true)and'manifest'or'pixels'
 end,
 prefix=function(g)return g..'/'end,decode=function()return manifest end,newImageData=data,hash=hash,nativePack=pack,identityToken=function()return 1 end}
local ref={game='emerald',tileset='PAIR',id=77,animationManifestHash=hash('manifest'),staticClassic=true}
eq(assert(d:cell(ref)).staticClassic,true);local readWarm=reads;assert(d:cell(ref));eq(reads,readWarm,'warm manifest check reads disk')
manifest.banks={{kind='tiles',mids={77}}};d:invalidate();eq(d:cell(ref),nil)
manifest.banks={{kind='tiles',overMids={77}}};d:invalidate();eq(d:cell(ref),nil)
manifest.banks={{kind='palette',paletteSlot=0}};d:invalidate();eq(d:cell(ref),nil)
manifest={water={mids={77}}};ref.game='firered';d:invalidate();eq(d:cell(ref),nil)
manifest={banks={}};ref.animationManifestHash=hash('changed');d:invalidate();eq(d:cell(ref),nil)
ref.game='emerald';ref.animationManifestHash=hash('manifest');manifest={banks={{kind='tiles',mids={77},quads={1}}}}
local quarter={};for y=0,15 do for x=0,15 do quarter[#quarter+1]=x<8 and y<8 and'1'or'0'end end
ref.classicGroundMasks={under=table.concat(quarter)};d:invalidate();eq(assert(d:cell(ref)).classicGroundMaskKey,ref.classicGroundMasks.under..'::')
ref.classicGroundMasks.under='0'..ref.classicGroundMasks.under:sub(2);eq(d:cell(ref),nil,'uncovered animated pixel accepted')
ref.classicGroundMasks.under=ones;withMid=true;d:invalidate();eq(d:cell(ref),nil,'duplicate middle plane would freeze water')
ref.classicGroundMasks.mid=ones;eq(assert(d:cell(ref)).staticClassic,true)
manifest={banks={{kind='palette',paletteSlot=0}}};d:invalidate();eq(assert(d:cell(ref)).staticClassic,true)
ref.classicGroundMasks.mid='0'..ones:sub(2);eq(d:cell(ref),nil,'uncovered native palette pixel accepted')
ref.classicGroundMasks=nil;ref.classicNativeOver={bank='steam',hash=hash(bankBytes)};withOver=true
manifest={banks={{kind='tiles',name='steam',frames=2,overFile='steam.idx',overMids={77},overQuads={15}}}}
d:invalidate();eq(assert(d:cell(ref)).classicNativeOver,'steam:'..hash(bankBytes))
ref.classicNativeOver.hash=hash('wrong');eq(d:cell(ref),nil,'changed native effect bank accepted')
ref.classicNativeOver.hash=hash(bankBytes);manifest.banks[1].file='under.idx';d:invalidate();eq(d:cell(ref),nil,'mixed under/over bank accepted')
ref.classicNativeOver=nil;withOver=false
manifest={family='rse',banks={{kind='tiles',name='lights',frames=2,file='lights.idx',mids={77},quads={15}}}}
local first='1'..string.rep('0',255)
ref.classicSourceAnimation={mode='water_mask',bank='lights',hash=hash(lightBytes)}
ref.classicGroundMasks={under=first,mid=first};d:invalidate()
eq(assert(d:cell(ref)).staticClassic,true,'constant pixels inside a flagged quadrant must stay available')
ref.classicGroundMasks.mid=nil;eq(d:cell(ref),nil,'water phase would be hidden by duplicate middle pixel')
ref.classicGroundMasks=nil;eq(d:cell(ref),nil,'uncovered actual source change accepted')
ref.classicSourceAnimation.mode='native_under'
local lightSource=assert(d:cell(ref))
eq(#lightSource.classicSourceFrames,2);eq(lightSource.classicSourceMiddleOverlap[1],true)
eq(lightSource.classicSourceVariation[2],nil,'stable source pixel treated as a moving pixel')
eq(lightSource.classicSourceFrames[2]:getString():sub(1,4),string.char(0,255,0,255))
local lights=copy(row);lights.sourceHash=lightSource.hash
lights.classicGeometry.sourceAnimation=copy(ref.classicSourceAnimation)
for _,name in ipairs({'under','mid','over'})do lights.classicGeometry.sourceLayers[name]=hash(lightSource[name]:getString())end
lights.classicGeometry.animationManifestHash=lightSource.animationManifestHash
local lightComposer=Composition.new{donor=d,newImageData=data,validateRow=Mapping.validate,hashImage=function(im)return hash(im:getString())end}
local phases=assert(lightComposer:frames(lights,lightSource));eq(#phases.sourceUnderBytes,2)
eq(phases.frames[2].under:getString():sub(1,4),string.char(160,192,96,255))
eq(phases.frames[2].mid:getString():sub(1,4),string.char(0,0,0,0),'duplicated middle freezes moving source pixel')
eq(phases.frames[2].mid:getString():sub(5,8),phases.base.mid:getString():sub(5,8),'static middle pixel changed')
local lightIndex=assert(Mapping.index({lights}));local lightSession=Session.new{mappings=lightIndex,donor=d,newImageData=data,
 generations=Mapping.generations,themes=Mapping.themes,normalizeStyle=Mapping.normalizeStyle,validate=Mapping.validate,
 composeFrames=function(r,s)return lightComposer:frames(r,s)end,warn=error}
lightSession:select('gen2');local lightReplacement=lightSession:replacements('emerald','PAIR')[77]
eq(lightReplacement.nativeUnder[phases.sourceUnderBytes[2]]:getString(),phases.frames[2].under:getString())
eq(lightReplacement.frames,nil,'native source animation must not run a second clock')
altered=copy(lights);altered.classicGeometry.sourceAnimation.hash=hash('wrong')
eq(lightComposer:frames(altered),nil,'changed under animation bank accepted')
altered=copy(lights);altered.classicGeometry.ground=copy(grounded.classicGeometry.ground)
altered.classicGeometry.ground.donor.game='crystal'
eq(lightComposer:frames(altered,lightSource),nil,'static backing masks a moving source pixel')
ref.classicSourceAnimation.mode='static_equivalent'
eq(d:cell(ref),nil,'varying native source accepted as static')
manifest.banks[1].quads={2};d:invalidate()
eq(assert(d:cell(ref)).classicSourceFrames,nil,'visually static native bank creates animation frames')
manifest.banks[1].overMids={78};manifest.banks[1].overFile='over.idx';d:invalidate()
eq(assert(d:cell(ref)).staticClassic,true,'unrelated native OVER cell blocks a safe UNDER source')
manifest.banks[1].overMids={77};d:invalidate()
eq(d:cell(ref),nil,'one cell cannot claim independent UNDER and OVER under the source contract')
print('classic geometry checks: '..checks)
