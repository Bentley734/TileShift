-- The four original cafe guests follow their translated Gen3 table chairs.
-- Only live entity coordinates change. Imported object/map definitions and
-- all identities, scripts, movement state, sprites and facings stay native.
local Seating={}
local MAP='CELADON_CAFE'
local BLOCKS={2,45,40,41,19,4,5,46,6,5,22,4,1,44,1,5,23,24,5,46,6,12,25,25}
local KEYS={[2]='CELADON_CAFE_obj_2',[3]='CELADON_CAFE_obj_3',
  [4]='CELADON_CAFE_obj_4',[5]='CELADON_CAFE_obj_5'}
local PEOPLE={
  [2]={x=4,y=6,movement=8,palette=0,spriteId=58,sprite='SPRITE_FISHER'},
  [3]={x=1,y=7,movement=9,palette=10,spriteId=58,sprite='SPRITE_FISHER'},
  [4]={x=1,y=2,movement=9,palette=0,spriteId=58,sprite='SPRITE_FISHER'},
  [5]={x=4,y=3,movement=8,palette=0,spriteId=41,sprite='SPRITE_TEACHER'},
}
local SCRIPTS={
  gold={[2]={25645,'5e:642d'},[3]={25662,'5e:643e'},[4]={25679,'5e:644f'},[5]={25696,'5e:6460'}},
  silver={[2]={25645,'5e:642d'},[3]={25662,'5e:643e'},[4]={25679,'5e:644f'},[5]={25696,'5e:6460'}},
  crystal={[2]={28753,'1c:7051'},[3]={28770,'1c:7062'},[4]={28787,'1c:7073'},[5]={28804,'1c:7084'}},
}
local function sourceObject(obj,index,game)
  local p,s=PEOPLE[index],SCRIPTS[game]and SCRIPTS[game][index]
  return p and s and type(obj)=='table'and not obj.runtime and obj.owner==nil
    and obj.index==index and obj.x==p.x and obj.y==p.y and obj.type==0 and obj.sight==0
    and obj.sprite==p.sprite and obj.spriteId==p.spriteId and obj.palette==p.palette
    and obj.movement==p.movement and obj.script==s[1]and obj.scriptKey==s[2]
    and obj.eventFlag==65535 and obj.hours and obj.hours[1]==-1 and obj.hours[2]==-1
    and obj.radius and obj.radius.x==0 and obj.radius.y==0
end
local function translate(npc,dy)
  npc.cellY=npc.cellY+dy;npc.py=npc.py+dy*16;npc.homeY=npc.homeY+dy
  if type(npc.targetY)=='number'then npc.targetY=npc.targetY+dy end
end

function Seating.new(ctx)
  assert(type(ctx)=='table'and type(ctx.active)=='function'and type(ctx.version)=='function'
    and type(ctx.revision)=='function'and type(ctx.artwork)=='function','Seating context required')
  local self={stats={guardBuilds=0,artworkChecks=0,translated=0,restored=0}}
  local closed=false
  local records=setmetatable({},{__mode='k'})
  local guards=setmetatable({},{__mode='k'})
  local markers={gold={},silver={},crystal={}}
  local lastWorld,lastMap,lastPool,lastRevision,lastActive,lastVersion
  -- This is a cold pass over already-loaded mappings. Merely retheming the
  -- cafe does not authorize moving actors; the translated chair rows must
  -- actually be present and carry their checked source-to-target relation.
  for _,row in ipairs(ctx.rows or{})do
    if row.map==MAP and row.style=='gen3'and row.role=='gen2_celadon_cafe_table_chair'
      and markers[row.game]and row.sourceCollision==0 and(not ctx.validate or ctx.validate(row))then
      local relocation=row.chairRelocation
      local from,delta=relocation and relocation.fromPosition,relocation and relocation.translation
      if from and delta and delta[1]==0 and delta[2]==-1 then
        for index=2,5 do local p=PEOPLE[index]
          if row.x==p.x and row.y==p.y-1 and from[1]==p.x and from[2]==p.y then
            markers[row.game][index]=true
          end
        end
      end
    end
  end
  local function mapDefinition(world)
    if world and world.map and world.map.id==MAP then return world.map.def end
    return world and world.maps and world.maps[MAP]
  end
  local function ready(world,def,game)
    if not(def and SCRIPTS[game])then return false end
    local revision=ctx.revision()
    local cached=guards[def]
    if cached and cached.revision==revision and cached.game==game then return cached.ready end
    self.stats.guardBuilds=self.stats.guardBuilds+1
    local ok=def.id==MAP and def.tileset=='TILESET_GAME_CORNER'and def.width==6 and def.height==4
      and type(def.blocks)=='table'and #def.blocks==#BLOCKS and type(def.objects)=='table'
    if ok then
      for i=1,#BLOCKS do if def.blocks[i]~=BLOCKS[i]then ok=false;break end end
      for index=2,5 do if not markers[game][index]then ok=false;break end end
    end
    if ok then
      self.stats.artworkChecks=self.stats.artworkChecks+1
      local art,rejected=ctx.artwork(game,def)
      ok=type(art)=='table'and(rejected==nil or rejected==0)
      if ok then for index=2,5 do
        local p=PEOPLE[index];local x,y=p.x,p.y-1
        local bx,by=math.floor(x/2),math.floor(y/2)
        local block=art[def.blocks[by*def.width+bx+1]]
        if block and block.positionRows then block=block.positionRows[by*def.width+bx]or block end
        local q=y%2*2+x%2
        if not(block and block.image and block.coverage and block.coverage[q]==true)then ok=false;break end
      end end
    end
    guards[def]={revision=revision,game=game,ready=ok and true or false}
    return ok and true or false
  end
  local function release(npc,record)
    -- A script/other mod that writes an absolute spawn/home takes ownership.
    -- Do not add an inverse offset to that newly chosen position.
    local obj=npc.def
    if npc.id==record.id and npc.mapId==MAP and obj and obj.x==record.x and obj.y==record.y
      and npc.homeX==record.x and npc.homeY==record.y-1
      and type(npc.cellY)=='number'and type(npc.py)=='number'then
      translate(npc,1);self.stats.restored=self.stats.restored+1
    end
    records[npc]=nil
  end
  function self:npc(world,mapId,obj,npc)
    if closed or not world or not npc or mapId~=MAP then return npc end
    local record=records[npc]
    if record and(npc.homeX~=record.x or npc.homeY~=record.y-1)then
      -- Native moveobject or a new absolute home supersedes our old offset.
      records[npc]=nil;record=nil
    end
    local index=obj and obj.index
    local p=PEOPLE[index]
    local def=mapDefinition(world)
    local game=ctx.version()
    local allowed=p and npc~=world.player and npc.mapId==MAP and npc.id==KEYS[index]
      and npc.def==obj and def and def.objects and def.objects[index]==obj
      and sourceObject(obj,index,game)and ctx.active()and ready(world,def,game)
    if not allowed then if record then release(npc,record)end;return npc end
    if record then return npc end
    -- Only the original seated pose gains the offset. A guest, follower,
    -- wandering actor or script that already moved this NPC is left alone.
    if npc.cellX==p.x and npc.cellY==p.y and npc.homeX==p.x and npc.homeY==p.y
      and type(npc.py)=='number'then
      translate(npc,-1)
      records[npc]={id=KEYS[index],x=p.x,y=p.y}
      self.stats.translated=self.stats.translated+1
    end
    return npc
  end
  function self:sync(world)
    if closed or not world then return end
    local pool=world.npcPool
    if not pool then return end
    for index=2,5 do
      local npc=pool[KEYS[index]]
      if npc then self:npc(world,MAP,npc.def,npc)end
    end
  end
  function self:bind(world)
    if closed or not world then return end
    local revision,active,game=ctx.revision(),ctx.active(),ctx.version()
    if world==lastWorld and world.map==lastMap and world.npcPool==lastPool
      and revision==lastRevision and active==lastActive and game==lastVersion then return end
    lastWorld,lastMap,lastPool,lastRevision,lastActive,lastVersion=world,world.map,world.npcPool,revision,active,game
    self:sync(world)
  end
  function self:offset(npc)return records[npc]and-1 or 0 end
  function self:dispose()
    if closed then return end;closed=true
    for npc,record in pairs(records)do release(npc,record)end
  end
  return self
end
return Seating
