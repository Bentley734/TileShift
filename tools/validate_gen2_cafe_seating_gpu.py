"""Actual native GSC cafe NPCs: seating, facing, occupancy and GPU restoration.

This separate artifact deliberately includes the five real imported NPC
sprites. Ordinary background comparison fixtures can remain actor-free.
"""
import sys
from pathlib import Path
import validate_gpu

BODY=r"""
 report.type='native GSC cafe NPC seating and sprite GPU validation'
 report.limits='Real source maps, NPC objects, imported sprite sheets and palettes, native drawPersonEntry, Player.tryMove and facingObject queries. No interactive playthrough or save writes.'
 report.actors_rendered=true
 local NPC=require('src.world.gen2.Npc')
 local Player=require('src.world.gen2.Player')
 local expected={[1]={9,3,'left'},[2]={4,6,'left'},[3]={1,7,'right'},[4]={1,2,'right'},[5]={4,3,'left'}}
 local function drawActor(world,npc)
  return capture(world.viewW,world.viewH,function()
   local entry={entity=npc,sx=0,sy=0,ox=0,oy=0,s=1}
   entry.drawSprite=function(oamRow,ox,oy,s)npc:draw(ox or 0,oy or 0,s or 1,oamRow)end
   world:drawPersonEntry(entry,1)
  end)
 end
 local function drawScene(world)
  return capture(world.viewW,world.viewH,function()
   G.draw(world.mapImage,0,0);world:drawAnimCells(world.map.id,0,0,1)
   for _,npc in ipairs(world.npcs)do
    local entry={entity=npc,sx=0,sy=0,ox=0,oy=0,s=1}
    entry.drawSprite=function(oamRow,ox,oy,s)npc:draw(ox or 0,oy or 0,s or 1,oamRow)end
    world:drawPersonEntry(entry,1)
   end
  end)
 end
 report.totals={source_npcs=0,moved_npcs=0,unchanged_npcs=0,unchanged_bar_npcs=0,checked_sprite_pixels=0,warm_pool_calls=0}
 for _,game in ipairs({'gold','silver','crystal'})do
  GV.set(game);assetGame=game;clock=0
  local world,map,def=world2(game,'CELADON_CAFE')
  local originalDefinition=tableString(def)
  world.sprites=generated(game,'sprites');world.npcPool={};world.npcs={};world.entities={}
  local beforeActor,source={},{ }
  for _,obj in ipairs(def.objects)do
   local npc=assert(world:pooledNpc(def.id,obj),'Native cafe actor did not spawn')
   world.npcs[#world.npcs+1]=npc;world.entities[#world.entities+1]=npc
   source[obj.index]={entity=npc,def=npc.def,sprite=npc.sprite,spriteDef=npc.spriteDef,
    x=npc.cellX,y=npc.cellY,homeX=npc.homeX,homeY=npc.homeY,px=npc.px,py=npc.py,
    facing=npc.facing,script=obj.script,scriptKey=obj.scriptKey,palette=obj.palette}
  end
  check(#world.npcs==5,'Cafe source object count changed')
  world.mapImage=world:imageFor(map.id)
  local before=drawScene(world);local mechanics,events=snapshot(map,2),eventSnapshot(map)
  for _,npc in ipairs(world.npcs)do beforeActor[npc.def.index]=drawActor(world,npc)end
  local mod=startMod(game,2,world)
  check(mod.exports.seating==nil,'Cafe NPC relocation helper must be absent')
  world.mapImage=world:imageFor(map.id)
  local art=assert(mod.exports.state:replacements(game,def.tileset,def))
  check(mod.exports.state.rejected==0,'Cafe source/art validation rejected a reviewed row')
  verifyCoveredPixels(def,art,drawWorld2(world),game..' cafe background')
  local after=drawScene(world)
  local fixture={game=game,map=def.id,actors_rendered=true,native_actor_count=5,actors={},
   native_renderer='World.drawPersonEntry + native Npc.draw/SpriteRenderer, real imported sheets and palettes',
   before=encodePng(before,game..'-cafe-with-native-npcs-original.png'),
   after=encodePng(after,game..'-cafe-with-native-npcs-gen3.png')}
  for index,native in ipairs(source)do
   local npc=world.npcs[index]
   check(npc==native.entity and npc.def==native.def and npc.sprite==native.sprite and npc.spriteDef==native.spriteDef,
    'Retheming replaced a native actor identity/wardrobe')
   check(npc.cellX==native.x and npc.cellY==native.y and npc.px==native.px and npc.py==native.py,
    'Retheming moved a native cafe NPC')
   check(npc.homeX==native.homeX and npc.homeY==native.homeY,'Retheming moved a native cafe home')
   check(npc.facing==native.facing,'Retheming changed original NPC facing')
   check(npc.def.script==native.script and npc.def.scriptKey==native.scriptKey and npc.def.palette==native.palette,
    'Retheming changed source script/event identity or palette')
   local pixels=0;local image=drawActor(world,npc);local original=beforeActor[index]
   for y=0,world.viewH-1 do for x=0,world.viewW-1 do
    local _,_,_,alpha=original:getPixel(x,y)
    if alpha>0 then
     equalPixel(original,x,y,image,x,y,'Retheming changed a native cafe sprite/facing pixel')
     pixels=pixels+1
    end
   end end
   check(pixels>0,'Cafe proof did not render a real source NPC sprite')
   check(image:getString()==original:getString(),'Retheming changed native cafe actor pixels or placement')
   check(npc.cellX==expected[index][1]and npc.cellY==expected[index][2]and npc.facing==expected[index][3],
    'Cafe original source pose changed')
   check(NPC.covers(npc,native.x,native.y)and world:npcAt(native.x,native.y)==npc,
    'Native occupancy missed the original seated NPC')
   world.player=Player.new(native.x-1,native.y,'right')
   check(world:facingObject()==npc,'Native talk targeting missed the original seated NPC')
   local blocked=world.player:tryMove('right',map,world.entities)
   check(blocked=='blocked'and not world.player.moving and world.player.cellX==native.x-1
     and world.player.cellY==native.y and world.player.targetX==nil,
     'Native player collision entered the seated NPC cell')
   world.player=Player.new(native.x-1,native.y,'right')
   local moved=world.player:tryMove('right',map,{})
   check(moved=='moved'and world.player.moving and world.player.targetX==native.x and world.player.targetY==native.y,
     'Cafe occupancy proof was blocked by terrain instead of the native NPC')
   world.player=nil
   report.totals.unchanged_npcs=report.totals.unchanged_npcs+1
   if index==1 then report.totals.unchanged_bar_npcs=report.totals.unchanged_bar_npcs+1 end
   fixture.actors[#fixture.actors+1]={index=index,id=npc.id,sprite_id=npc.def.sprite,script=native.script,
    scriptKey=native.scriptKey,original={native.x,native.y},gen3={npc.cellX,npc.cellY},
    original_home={native.homeX,native.homeY},gen3_home={npc.homeX,npc.homeY},
    original_pixel_position={native.px,native.py},gen3_pixel_position={npc.px,npc.py},
    original_facing=native.facing,gen3_facing=npc.facing,moved=false,checked_sprite_pixels=pixels,
    source_identity_and_wardrobe_unchanged=true,native_occupancy_and_talk_geometry=true}
   report.totals.source_npcs=report.totals.source_npcs+1;report.totals.checked_sprite_pixels=report.totals.checked_sprite_pixels+pixels
  end
  local reads=importReads
  for i=1,120 do
   for index=1,5 do
    local obj=def.objects[index];local npc=world:pooledNpc(def.id,obj)
    check(npc==source[index].entity,'Warm pool replaced source actor')
    check(npc.cellX==source[index].x and npc.cellY==source[index].y,'Warm pool moved a source actor')
   end
  end
  check(importReads==reads,'Warm native actor binding reread imported data')
  fixture.warm_pool_calls=600;fixture.warm_source_art_checks=0;report.totals.warm_pool_calls=report.totals.warm_pool_calls+600
  mod.exports.select('original');world.mapImage=world:imageFor(map.id)
  for index,npc in ipairs(world.npcs)do local native=source[index]
   check(npc.cellX==native.x and npc.cellY==native.y and npc.homeX==native.homeX and npc.homeY==native.homeY
     and npc.px==native.px and npc.py==native.py and npc.facing==native.facing,
     'Original theme changed a native cafe pose/home')
  end
  check(drawScene(world):getString()==before:getString(),'Original theme failed to restore exact native background and actor pixels')
  mod.exports.select('gen3');world.mapImage=world:imageFor(map.id)
  for index=1,5 do
   local npc,native=world.npcs[index],source[index]
   check(npc.cellX==native.x and npc.cellY==native.y and npc.homeX==native.homeX and npc.homeY==native.homeY
     and npc.px==native.px and npc.py==native.py and npc.facing==native.facing,
     'Re-enabled theme moved/changed a native cafe actor')
  end
  check(drawScene(world):getString()==after:getString(),'Theme cycle changed the native cafe actor scene')
  mod.exports.dispose();world.mapImage=world:imageFor(map.id)
  for index,npc in ipairs(world.npcs)do local native=source[index]
   check(npc.cellX==native.x and npc.cellY==native.y and npc.homeX==native.homeX and npc.homeY==native.homeY
     and npc.px==native.px and npc.py==native.py and npc.facing==native.facing,
     'Dispose changed a native cafe pose/home')
  end
  check(drawScene(world):getString()==before:getString(),'Dispose failed to restore exact native background and actors')
  check(tableString(def)==originalDefinition,'Retheming mutated imported map/object definitions')
  check(snapshot(map,2)==mechanics and eventSnapshot(map)==events,'Retheming changed source terrain collision/events')
  fixture.original_restored=true;fixture.dispose_restored=true;fixture.original_map_and_object_definitions_unchanged=true
  fixture.source_collision_events_unchanged=true;report.fixtures[#report.fixtures+1]=fixture
  write('progress.json',Json.encode({fixtures=#report.fixtures,checks=report.checks,game=game,map=def.id}))
 end
 check(#report.fixtures==3 and report.totals.moved_npcs==0 and report.totals.unchanged_npcs==15 and report.totals.unchanged_bar_npcs==3,
  'Native cafe actor matrix is incomplete')
 check(#report.warnings==0,'Native cafe actor probe reported source warnings')
 report.status='passed';write('report.json',Json.encode(report))
end
"""

def main():
    source=validate_gpu.LUA
    prefix=source[:source.index(' -- Native Gen1 TileRenderer on real Red Pallet Town.')]
    setup=source[source.index(' -- Real Gold/Silver/Crystal World bake'):source.index(' local function verifyGen2Ladders')]
    validate_gpu.LUA=prefix+setup+BODY+source[source.index('\nfunction love.load()'):]
    if '--output'not in sys.argv:sys.argv.extend(['--output',str(Path(__file__).resolve().parents[2]/'.work/tileshift-cafe-seating-gpu')])
    return validate_gpu.main()

if __name__=='__main__':raise SystemExit(main())
