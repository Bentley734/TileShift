local root=assert(arg and arg[1],'TileShift directory required')
local Seating=assert(loadfile(root..'/lib/npc_seating.lua'))()
local checks=0
local function eq(a,b,message)checks=checks+1;assert(a==b,(message or'mismatch')..': '..tostring(a)..' ~= '..tostring(b))end
local function copy(value)
  if type(value)~='table'then return value end
  local out={};for k,v in pairs(value)do out[k]=copy(v)end;return out
end
local blocks={2,45,40,41,19,4,5,46,6,5,22,4,1,44,1,5,23,24,5,46,6,12,25,25}
local function fixture(version)
  local crystal=version=='crystal'
  local def={id='CELADON_CAFE',tileset='TILESET_GAME_CORNER',width=6,height=4,blocks=copy(blocks),objects={}}
  local poses={{9,3,8,11,'SPRITE_SUPER_NERD',43},{4,6,8,0,'SPRITE_FISHER',58},
    {1,7,9,10,'SPRITE_FISHER',58},{1,2,9,0,'SPRITE_FISHER',58},{4,3,8,0,'SPRITE_TEACHER',41}}
  local gs={{25637,'5e:6425'},{25645,'5e:642d'},{25662,'5e:643e'},{25679,'5e:644f'},{25696,'5e:6460'}}
  local cy={{28745,'1c:7049'},{28753,'1c:7051'},{28770,'1c:7062'},{28787,'1c:7073'},{28804,'1c:7084'}}
  local world={map={id=def.id,def=def},maps={[def.id]=def},npcPool={},npcs={},entities={}}
  local function actor(obj)
    return {id='CELADON_CAFE_obj_'..obj.index,mapId='CELADON_CAFE',def=obj,
      cellX=obj.x,cellY=obj.y,homeX=obj.x,homeY=obj.y,px=obj.x*16,py=obj.y*16,
      facing=obj.movement==8 and'left'or'right',moving=false,progress=0,
      sprite={outfit='native'},spriteDef={id=obj.sprite},palette={native=true},timer=71,frozen=true}
  end
  local rows,art={},{}
  for i,p in ipairs(poses)do
    local script=(crystal and cy or gs)[i]
    local obj={index=i,x=p[1],y=p[2],movement=p[3],palette=p[4],sprite=p[5],spriteId=p[6],
      type=0,sight=0,eventFlag=65535,hours={-1,-1},radius={x=0,y=0},script=script[1],scriptKey=script[2]}
    def.objects[i]=obj;local npc=actor(obj);world.npcPool[npc.id]=npc;world.npcs[i]=npc;world.entities[i]=npc
    if i>1 then
      rows[#rows+1]={game=version,style='gen3',map=def.id,role='gen2_celadon_cafe_table_chair',
        sourceCollision=0,x=obj.x,y=obj.y-1,chairRelocation={fromPosition={obj.x,obj.y},translation={0,-1}}}
      local x,y=obj.x,obj.y-1;local id=blocks[math.floor(y/2)*6+math.floor(x/2)+1]
      art[id]=art[id]or{image={},coverage={}};art[id].coverage[y%2*2+x%2]=true
    end
  end
  local state={active=true,revision=1,artworkCalls=0,rejected=0,version=version}
  local helper=Seating.new({rows=rows,validate=function()return true end,
    active=function()return state.active end,revision=function()return state.revision end,
    version=function()return state.version end,artwork=function()state.artworkCalls=state.artworkCalls+1;return art,state.rejected end})
  return helper,world,state,rows,art,actor
end

for _,version in ipairs({'gold','silver','crystal'})do
  local helper,world,state=fixture(version)
  local snapshots={}
  for i,npc in ipairs(world.npcs)do snapshots[i]={npc=npc,def=npc.def,sprite=npc.sprite,spriteDef=npc.spriteDef,
    palette=npc.palette,x=npc.cellX,y=npc.cellY,home=npc.homeY,py=npc.py,facing=npc.facing,script=npc.def.script,scriptKey=npc.def.scriptKey}end
  helper:bind(world)
  eq(helper.stats.translated,4,'Only four source table guests translate in '..version)
  for i,npc in ipairs(world.npcs)do
    local s=snapshots[i];local dy=i==1 and 0 or-1
    eq(npc,s.npc);eq(npc.def,s.def);eq(npc.sprite,s.sprite);eq(npc.spriteDef,s.spriteDef);eq(npc.palette,s.palette)
    eq(npc.cellX,s.x);eq(npc.cellY,s.y+dy);eq(npc.homeY,s.home+dy);eq(npc.py,s.py+dy*16)
    eq(npc.facing,s.facing,'Seating never writes native facing');eq(npc.def.x,s.x);eq(npc.def.y,s.y)
    eq(npc.def.script,s.script);eq(npc.def.scriptKey,s.scriptKey);eq(npc.timer,71);eq(npc.frozen,true)
  end
  local builds,reads=helper.stats.guardBuilds,state.artworkCalls
  for _=1,120 do
    helper:bind(world)
    for i=2,5 do local npc=world.npcs[i];helper:npc(world,'CELADON_CAFE',npc.def,npc)end
  end
  eq(helper.stats.translated,4,'Pooled reuse never repeats an offset')
  eq(helper.stats.guardBuilds,builds,'Warm actor lookups do not scan source map blocks')
  eq(state.artworkCalls,reads,'Warm actor lookups do not rebuild/read art')
  state.active=false;state.revision=state.revision+1;helper:bind(world)
  for i,npc in ipairs(world.npcs)do eq(npc.cellY,snapshots[i].y);eq(npc.py,snapshots[i].py);eq(npc.facing,snapshots[i].facing)end
  eq(helper.stats.restored,4,'Original restores existing source objects')
  state.active=true;state.revision=state.revision+1;helper:bind(world)
  eq(helper.stats.translated,8,'Re-enabling applies one offset')
  helper:dispose();helper:dispose()
  for i,npc in ipairs(world.npcs)do eq(npc.cellY,snapshots[i].y);eq(npc.homeY,snapshots[i].home);eq(npc.py,snapshots[i].py)end
end

-- Existing actors are adjusted without replacing their scripts or motion.
do
  local helper,world,state=fixture('crystal');local npc=world.npcs[2]
  npc.moving=true;npc.progress=7;npc.py=99.5;npc.targetY=7;npc.targetX=4;npc.facing='up';npc.spriteYOffset=-3
  helper:bind(world)
  eq(npc.cellY,5);eq(npc.homeY,5);eq(npc.py,83.5);eq(npc.targetY,6)
  eq(npc.progress,7);eq(npc.moving,true);eq(npc.targetX,4);eq(npc.facing,'up');eq(npc.spriteYOffset,-3)
  helper:dispose();eq(npc.cellY,6);eq(npc.py,99.5);eq(npc.targetY,7);eq(npc.progress,7);eq(npc.facing,'up')
end
-- The native pool can respawn its objects, or return the same table again.
do
  local helper,world,state,rows,art,actor=fixture('gold');helper:bind(world)
  local new=actor(world.map.def.objects[2]);world.npcPool[new.id]=new
  helper:npc(world,'CELADON_CAFE',new.def,new);eq(new.cellY,5)
  helper:npc(world,'CELADON_CAFE',new.def,new);eq(new.cellY,5)
  helper:dispose();eq(new.cellY,6)
end
-- Strong source and art guards: a missing row, failed donor, changed source
-- map or different script never silently moves a different person.
for _,case in ipairs({'missing_marker','missing_art','rejected_art','changed_map','changed_script','other_game'})do
  local helper,world,state,rows,art=fixture('crystal')
  if case=='missing_marker'then
    rows[1].chairRelocation.translation[2]=0
    helper=Seating.new({rows=rows,active=function()return true end,version=function()return'crystal'end,
      revision=function()return 1 end,artwork=function()return art,0 end})
  elseif case=='missing_art'then for _,block in pairs(art)do block.coverage={}end
  elseif case=='rejected_art'then state.rejected=1
  elseif case=='changed_map'then world.map.def.blocks[1]=99
  elseif case=='changed_script'then world.map.def.objects[2].scriptKey='different-script'
  elseif case=='other_game'then state.version='red'end
  helper:bind(world)
  eq(world.npcs[2].cellY,6,'Refused seating after '..case)
  helper:dispose()
end
-- Neither guests nor a source object that was explicitly moved elsewhere
-- is pulled onto a cafe seat; a later absolute script move wins on cleanup.
do
  local helper,world,state,rows,art,actor=fixture('silver')
  local guest=actor(copy(world.map.def.objects[2]));helper:npc(world,'CELADON_CAFE',guest.def,guest);eq(guest.cellY,6)
  world.player=actor(world.map.def.objects[2]);helper:npc(world,'CELADON_CAFE',world.player.def,world.player);eq(world.player.cellY,6)
  local npc=world.npcs[2];npc.cellY=0;npc.homeY=0;npc.py=0;helper:bind(world);eq(npc.cellY,0)
  helper:dispose()
  helper,world,state=fixture('silver');helper:bind(world);npc=world.npcs[2]
  npc.def.y=0;npc.cellY=0;npc.homeY=0;npc.py=0;helper:dispose();eq(npc.cellY,0);eq(npc.py,0)
end
-- The adapter owns/unwinds the one existing native spawn/pool hook, including
-- a later mod retaining its wrapper after TileShift has been disposed.
do
  local Adapter=assert(loadfile(root..'/lib/gen2.lua'))()
  local nativeCalls,calls,closed=0,0,0;local actor={id='native'}
  local World={pooledNpc=function(_,mapId,obj)nativeCalls=nativeCalls+1;return actor end}
  local native=World.pooledNpc
  local seating={npc=function(_,world,mapId,obj,npc)calls=calls+1;eq(npc,actor);return npc end,
    dispose=function()closed=closed+1 end}
  local dispose=Adapter.install({worldClass=World,borderFill={},palette={},graphics={},version=function()return'crystal'end,
    replacements=function()return nil end,seating=seating})
  local world=setmetatable({},{__index=World});eq(world:pooledNpc('CELADON_CAFE',{}),actor);eq(calls,1)
  local wrapper=World.pooledNpc;World.pooledNpc=function(...)return wrapper(...)end
  dispose();eq(closed,1);eq(world:pooledNpc('CELADON_CAFE',{}),actor);eq(calls,1,'Disposed retained wrapper is inert')
  eq(nativeCalls,2);eq(World.pooledNpc==native,false,'Later mod wrapper is not overwritten')
end
print('npc_seating_test: '..checks..' checks passed')
