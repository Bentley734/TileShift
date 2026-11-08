local root=assert(arg[1])
local Clinic=assert(loadfile(root..'/lib/clinic_chansey.lua'))()
local catalog=assert(loadfile(root..'/lib/clinic_chansey_catalog.lua'))()
local checks=0
local function eq(a,b,why) checks=checks+1;assert(a==b,why or(tostring(a)..' ~= '..tostring(b))) end
local function copy(t) local out={};for k,v in pairs(t) do out[k]=type(v)=='table' and copy(v) or v end;return out end

local function fixture(record)
  local f={game=record.game,style='gen3',active=true,sourceValid=true,epoch=1,bus={},
    newSprites=0,assetReads=0,quads=0,providerCalls=0,resolveCalls=0,paletteCalls=0,
    nativeDraws={},draws={},marks={},guardCalls=0}
  local G={}
  function G.push() end;function G.pop() end;function G.translate() end;function G.scale() end
  function G.setShader() end;function G.setColor() end
  function G.draw(...) f.draws[#f.draws+1]={...} end
  local Renderer={}
  local Palettes={}
  function Palettes.monColors(data,species,shiny)
    f.paletteCalls=f.paletteCalls+1;eq(species,'CHANSEY');eq(shiny,false)
    local entry=data and data.pokemon and data.pokemon[species]
    local pair=entry and entry.normal
    if not pair then return nil end
    return {{255,255,255},copy(pair[1]),copy(pair[2]),{0,0,0}}
  end
  function Renderer.new(def)
    f.newSprites=f.newSprites+1;f.assetReads=f.assetReads+1;f.quads=f.quads+6
    local r={def=def,frameWidth=16,frameHeight=16,anchorX=8,anchorY=16}
    function r:setObjPalette(colors,group) self.colors,self.group=colors,group end
    function r:resolveImage() self.prewarmed=true;return self end
    function r:draw(px,py,cx,cy,facing,phase,flip,top,force,frame,row)
      eq(self.prewarmed,true,'native sprite OBJ image was prewarmed')
      f.nativeDraws[#f.nativeDraws+1]={px=px,py=py,facing=facing,row=row}
    end
    return r
  end
  local World={}
  function World:drawPersonEntry(entry,s)
    f.order[#f.order+1]=entry.entity
    if entry.drawSprite then entry.drawSprite(nil,entry.sx,entry.sy,s)
    elseif entry.entity.draw then entry.entity:draw(entry.sx,entry.sy,s) end
    return 'native-entry'
  end
  function World:setMap() return true,nil,'set',nil,'tail' end
  function World:rebuildPeople() self.npcs={copy(f.nurse)};return 7,nil,false end
  function World:applyPalettes() return 1,nil,3 end
  local nurse={def=copy(record.nurse),facing='down',px=record.nurse.x*16,py=record.nurse.y*16}
  f.nurse=nurse
  local width=10;local blocks={}
  for _,cell in ipairs(record.cells) do blocks[math.floor(cell.y/2)*width+math.floor(cell.x/2)+1]=cell.id end
  local world=setmetatable({map={id=record.map,def={tileset=record.tileset,width=width,blocks=blocks}},
    sprites={SPRITE_FAIRY={id='SPRITE_FAIRY',image='fairy',frames=6,paletteId=0}},
    npcs={nurse},entities={nurse},daytime='DAY',
    palettes={pokemon={CHANSEY={normal={{255,165,198},{198,74,107}}}}}}, {__index=World})
  function world:applySpritePalette(entity)
    entity.sprite:setObjPalette({{255,255,255},{255,100,150},{200,0,0},{0,0,0}},'gen2:DAY:0')
  end
  f.world,f.World=world,World;f.order={}
  local old=World.drawPersonEntry;f.oldDraw=old
  f.module=Clinic.install{World=World,catalog=catalog,SpriteRenderer=Renderer,Palettes=Palettes,graphics=G,
    style=function() return f.style end,version=function() return f.game end,
    active=function() return f.active end,
    providerEpoch=function() return f.bus,f.epoch end,
    valid=function(w,r) f.guardCalls=f.guardCalls+1;return f.sourceValid end,
    resolveProvider=function() f.resolveCalls=f.resolveCalls+1;return f.provider end,
    markTrueColor=function(...) f.marks[#f.marks+1]={...} end}
  function f:draw(entity,row)
    self.order={};local entry={entity=entity or self.world.npcs[1],ox=0,oy=0,sx=3,sy=5,s=2}
    if row then
      local proxy=self.module:resident(self.world);proxy.facing=(entity or self.world.npcs[1]).facing
      proxy:draw(3,5,2,row);return
    end
    return self.world:drawPersonEntry(entry,2)
  end
  function f:providerDescriptor(source)
    local p={image='image-'..source,width=32,height=24,scale=1,anchorX=16,anchorY=24,
      footY=12,trueColor=true,source=source,live=true,quads={},
      oamQuads={top={},bottom={}},oamOffsetY={top=0,bottom=16},oamHeight={top=16,bottom=8}}
    for _,face in ipairs({'down','up','left','right'}) do
      p.quads[face]=source..'-'..face;p.oamQuads.top[face]=source..'-top-'..face
      p.oamQuads.bottom[face]=source..'-bottom-'..face
    end
    function p.isValid() return p.live end
    return p
  end
  function f:api(p,rawSource)
    local choice=rawSource or p.source
    return {version=1,prepare=function(national,options)
      self.providerCalls=self.providerCalls+1
      eq(national,113);eq(options.role,'resident')
      eq(options.sourceOverrides.companion,'ee','only the clinic Companion variant is substituted')
      eq(options.sourceOverrides.g9,nil);eq(options.sourceOverrides.ee,nil)
      eq(p.source,options.sourceOverrides[choice] or choice)
      return p
    end}
  end
  return f
end

eq(#catalog,66,'only actual Nurse/healer clinics are selected')
local seen={}
for _,record in ipairs(catalog) do
  eq(record.map~='POKECOM_CENTER_ADMIN_OFFICE_MOBILE',true)
  local f=fixture(record);local w=f.world;local npcs,entities,blocks=w.npcs,w.entities,w.map.def.blocks
  local a,b,c,d,e=w:setMap()
  eq(a,true);eq(b,nil);eq(c,'set');eq(d,nil);eq(e,'tail','map hook preserves every native return')
  local resident,nurse=f.module:resident(w)
  eq(nurse,w.npcs[1]);eq(resident.px,32);eq(resident.py,record.y*16)
  eq(resident.cellX,2);eq(resident.cellY,record.y);eq(resident.nativeSprite.prewarmed,true)
  eq(resident.paletteSource,'chansey');eq(resident.nativeSprite.colors[2][1],255)
  eq(resident.nativeSprite.colors[2][2],165);eq(resident.nativeSprite.colors[2][3],198)
  eq(resident.nativeSprite.colors[3][1],198);eq(resident.nativeSprite.colors[3][2],74)
  eq(resident.nativeSprite.colors[3][3],107)
  eq(resident.nativeSprite.group:match('^tileshift:clinic_chansey:')~=nil,true)
  local reads,quads,guards,resolves,paletteCalls=f.assetReads,f.quads,f.guardCalls,f.resolveCalls,f.paletteCalls
  for _,face in ipairs({'down','left','up','right','left','down','up','down'}) do
    nurse.facing=face;eq(f:draw(),'native-entry')
    eq(resident.facing,face,'resident follows actual script/faceplayer facing at draw time')
    eq(f.nativeDraws[#f.nativeDraws].facing,face)
    eq(#f.order,2);eq(f.order[1],resident);eq(f.order[2],nurse)
  end
  eq(w.npcs,npcs);eq(w.entities,entities);eq(w.map.def.blocks,blocks)
  eq(#w.npcs,1);eq(#w.entities,1,'render-only resident never becomes a gameplay object')
  eq(nurse.px,record.nurse.x*16);eq(nurse.py,record.nurse.y*16)
  for _=1,120 do f:draw();eq(f.module:poll(w),false) end
  eq(f.assetReads,reads);eq(f.quads,quads);eq(f.guardCalls,guards)
  eq(f.resolveCalls,resolves,'missing WildFollowers is not looked up again on every update')
  eq(f.paletteCalls,paletteCalls,'native species palette is resolved outside warm drawing')
  w.peopleHidden=true;f:draw();eq(#f.order,1);w.peopleHidden=false
  nurse.hiddenByMovement=true;f:draw();eq(#f.order,1);nurse.hiddenByMovement=false
  w.spriteFilter=function(actor) return actor.national~=113 end;f:draw();eq(#f.order,1);w.spriteFilter=nil
  w.daytime='DARK';f:draw();eq(#f.order,1);w.daytime='DAY'
  local other={def={index=99,sprite='SPRITE_CLERK'}};f:draw(other);eq(#f.order,1)
  local index=math.floor(record.y/2)*w.map.def.width+2
  blocks[index]=999;f:draw();eq(#f.order,1,'changed native block fails closed');blocks[index]=2
  f.active=false;f:draw();eq(#f.order,1);f.active=true
  f.style='original';f.module:refresh(w);f:draw();eq(#f.order,1);eq(f.module:resident(w),nil)
  f.style='gen3';f.module:refresh(w);f:draw();eq(#f.order,2)
  local oldNurse=w.npcs[1];local ra,rb,rc=w:rebuildPeople()
  eq(ra,7);eq(rb,nil);eq(rc,false);eq(w.npcs[1]~=oldNurse,true)
  local _,newNurse=f.module:resident(w);eq(newNurse,w.npcs[1]);f:draw(oldNurse);eq(#f.order,1)
  f:draw(newNurse);eq(#f.order,2,'new native nurse identity is rebound after rebuild')
  local p1,p2,p3=w:applyPalettes();eq(p1,1);eq(p2,nil);eq(p3,3)
  f.module:dispose();eq(f.World.drawPersonEntry,f.oldDraw);f.module:dispose()
  eq(f.module:resident(w),nil);f:draw();eq(#f.order,1)
  seen[record.game]=true
end
eq(seen.gold,true);eq(seen.silver,true);eq(seen.crystal,true)

local f=fixture(catalog[1]);local w=f.world
f.module:prepare(w)
local p=f:providerDescriptor('g9');f.provider=f:api(p);f.epoch=f.epoch+1
eq(f.module:poll(w),true,'hot-enabled provider is prepared outside drawing')
local proxy=f.module:resident(w);eq(proxy.preparedProvider,p)
local reads,quads,calls,resolves=f.assetReads,f.quads,f.providerCalls,f.resolveCalls
for _,face in ipairs({'down','left','up','right'}) do
  w.npcs[1].facing=face;f:draw();eq(proxy.drawSource,'g9')
  eq(f.draws[#f.draws][2],p.quads[face],'selected pack uses its actual four directional quads')
end
for _=1,120 do f:draw();eq(f.module:poll(w),false) end
eq(f.assetReads,reads);eq(f.quads,quads);eq(f.providerCalls,calls);eq(f.resolveCalls,resolves)
f:draw(nil,'bottom');local last=f.draws[#f.draws];eq(last[2],p.oamQuads.bottom[proxy.facing])
eq(last[3],3+(32+8)*2-16*2);eq(last[4],5+(proxy.py+12)*2-24*2+16*2)
eq(f.marks[#f.marks][4],8*2,'true-color exemption covers just the actual OAM slice')
for _,source in ipairs({'ee','companion'}) do
  local actual=source=='companion' and 'ee' or source
  p.live=false;p=f:providerDescriptor(actual);f.provider=f:api(p,source);f.module:refresh(w)
  f:draw();eq(proxy.drawSource,actual,'the requested clinic variation follows each selected pack')
end
p.live=false;f.provider=nil;f.epoch=f.epoch+1;reads=f.assetReads;quads=f.quads
f:draw();eq(proxy.drawSource,'native','revoked provider immediately uses already warm native fallback')
eq(f.assetReads,reads);eq(f.quads,quads);eq(f.module:poll(w),true)
calls,resolves=f.providerCalls,f.resolveCalls
for _=1,120 do f:draw();eq(f.module:poll(w),false) end
eq(f.providerCalls,calls);eq(f.resolveCalls,resolves,'revoked/absent provider is not retried each frame')
local replacement=f:providerDescriptor('g9');f.provider=f:api(replacement);f.epoch=f.epoch+1
eq(f.module:poll(w),true);f:draw();eq(proxy.drawSource,'g9','hot reenable obtains the new owner lease')
w.npcs={copy(f.nurse)};f:draw();eq(#f.order,1);eq(f.module:poll(w),true);f:draw();eq(#f.order,2)
f.sourceValid=false;f.module:refresh(w);eq(f.module:resident(w),nil);f:draw();eq(#f.order,1)
f.sourceValid=true;f.module:refresh(w)
local external=f.World.drawPersonEntry
f.World.drawPersonEntry=function(...) return external(...) end
local externalOwner=f.World.drawPersonEntry;f.module:dispose()
eq(f.World.drawPersonEntry,externalOwner,'dispose does not erase a later mod wrapper')
f:draw();eq(#f.order,1,'disposed inner wrapper becomes a plain native draw')

local negative=fixture(catalog[1]);negative.world.map.id='POKECOM_CENTER_ADMIN_OFFICE_MOBILE'
eq(negative.module:prepare(negative.world),false);eq(negative.newSprites,0)
negative.module:dispose()
local late=fixture(catalog[1]);late.active=false
eq(late.module:prepare(late.world),false)
late.active=true;eq(late.module:poll(late.world),true,'initial ownership activation is prepared on update')
late:draw();eq(#late.order,2)
late.module:dispose()
local colors=fixture(catalog[1]);local cw=colors.world
local nurseColors={{255,255,255},{255,180,70},{190,90,15},{0,0,0}}
cw.npcs[1].sprite={colors=nurseColors};cw.npcs[1].def.palette=10
colors.module:prepare(cw);local cp=colors.module:resident(cw)
local expected={{255,255,255},{255,165,198},{198,74,107},{0,0,0}}
for i=1,4 do for j=1,3 do eq(cp.nativeSprite.colors[i][j],expected[i][j]) end end
eq(cw.npcs[1].sprite.colors,nurseColors);eq(nurseColors[2][2],180,'Chansey does not recolor the nurse')
eq(cw.npcs[1].def.palette,10,'Chansey ignores rather than rewrites the nurse palette override')
local group=cp.nativeSprite.group;local original=cw.palettes.pokemon.CHANSEY.normal
cw.palettes.pokemon.CHANSEY.normal={{246,170,202},{190,80,112}}
cw:applyPalettes();eq(cp.nativeSprite.group~=group,true,'species RGB fingerprint keeps palette caches separate')
eq(cp.nativeSprite.colors[2][1],246);eq(cp.nativeSprite.colors[3][3],112)
eq(original[1][1],255,'imported palette values were never rewritten')
cw.palettes.pokemon.CHANSEY=nil;cw:applyPalettes()
eq(cp.paletteSource,'native');eq(cp.nativeSprite.group,'gen2:DAY:0')
eq(cp.nativeSprite.colors[2][2],100,'missing species palette keeps native generic object colors')
local nativeCalls=colors.paletteCalls;local sourceReads,quadCount=colors.assetReads,colors.quads
for _=1,100 do colors:draw() end
eq(colors.paletteCalls,nativeCalls);eq(colors.assetReads,sourceReads);eq(colors.quads,quadCount)
colors.module:dispose()
print('clinic_chansey_test: '..checks..' checks')
