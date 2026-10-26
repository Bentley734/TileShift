"""Exercise native Gen1 Cut and cave puzzle updates in a private GPU process.

Candidate cave/Cut object art is injected only into the private mod state. The
actual engine map, script hooks, block swaps, renderer and adapter run normally.
No production mapping, imported cache, installed game or save is written.
"""
from pathlib import Path
import sys
import validate_gpu


DYNAMIC = r"""
 local Map=require('src.world.Map')
 local T=require('src.render.TileRenderer')
 local FX=require('src.render.PaletteFX')
 local Overworld=require('src.world.OverworldController')
 local nativeDraw=T.drawWindow
 local story=require('data.scripts.story')
 local function copy(source)local out={};for k,v in pairs(source or {})do out[k]=v end;return out end
 local function privateWorld(game,mapId)
  GV.set(game);assetGame=game;clock=0;FX.setDarkWorld(false)
  local maps,sets=generated(game,'maps'),generated(game,'tilesets')
  local def=copy(maps[mapId]);def.blocks=copy(def.blocks)
  local map=Map.new(def,sets[def.tileset]);maps[mapId]=def
  local renderer=T.new(map,{maps=maps,tilesets=sets});map.renderer=renderer
  local state=setmetatable({map=map,npcs={},entities={}},{__index=Overworld})
  local function draw(native)
   return capture(def.width*32,def.height*32,function()
    FX.clearTrueColor();FX.setPass('world')
    if native then nativeDraw(renderer,0,0,def.width*32,def.height*32)
    else renderer:drawWindow(0,0,def.width*32,def.height*32)end
    FX.setPass(nil)
   end)
  end
  return state,map,def,draw
 end
 local function cropped(frame,x,y,w,h)
  local image=love.image.newImageData(w,h);image:paste(frame,0,0,x,y,w,h);return image
 end
 local function inject(mod,game,def,art)
  local original=mod.exports.state.replacements
  mod.exports.state.replacements=function(self,g,tileset,mapDef)
   if g==game and tileset==def.tileset and mapDef and mapDef.id==def.id then return art end
   return original(self,g,tileset,mapDef)
  end
 end
 local function positionArt(art,id,bx,by,image,coverage)
  local existed=art[id]~=nil
  local generic=copy(art[id]);generic.image=generic.image or love.image.newImageData(32,32)
  if generic.coverage then generic.coverage=copy(generic.coverage)elseif not existed then generic.coverage={}end
  generic.positions=copy(generic.positions)
  generic.positions[bx..':'..by]={image=image,coverage=coverage or {[0]=true,[1]=true,[2]=true,[3]=true}}
  art[id]=generic
 end
 local function bindGame(fn,host)
  for i=1,50 do
   local key,value=debug.getupvalue(fn,i)
   if not key then break end
   if key=='Game' then
    debug.setupvalue(fn,i,host)
    return function()debug.setupvalue(fn,i,value)end
   end
  end
  error('Native method has no game-host upvalue')
 end
 local cavePair='general__rom_082d4bfc'
 local nativeRefs={}
 local catalog=Json.decode(assert(read(MOD..'/../.work/tileshift-catalog/firered.json')))
 for _,cell in ipairs(catalog.cells)do if cell.pair==cavePair then
  nativeRefs[cell.mid]={game='firered',tileset=cavePair,id=cell.mid,hash=cell.pixel_sha256}
 end end
 local function blockImage(mids)
  local image=love.image.newImageData(32,32)
  for q=0,3 do image:paste(nativeCellImage(assert(nativeRefs[mids[q+1]])),q%2*16,math.floor(q/2)*16,0,0,16,16)end
  return image
 end
 report.dynamic={}
 for _,game in ipairs({'red','blue','yellow'})do
  for _,spec in ipairs({{map='VICTORY_ROAD_1F',bx=4,by=6,before=37,after=29,button={17,13},flag='EVENT_VICTORY_ROAD_1_BOULDER_ON_SWITCH'},
   {map='VICTORY_ROAD_2F',bx=11,by=7,before=37,after=29,button={9,16},flag='EVENT_VICTORY_ROAD_2_BOULDER_ON_SWITCH2'},
   {map='VICTORY_ROAD_3F',bx=3,by=5,before=37,after=29,button={3,5},flag='EVENT_VICTORY_ROAD_3_BOULDER_ON_SWITCH1'},
   {map='VICTORY_ROAD_2F',bx=3,by=4,before=55,after=21,button={1,16},flag='EVENT_VICTORY_ROAD_2_BOULDER_ON_SWITCH1'}})do
   local state,map,def,draw=privateWorld(game,spec.map)
   local index=spec.by*def.width+spec.bx+1
   check(def.blocks[index]==spec.before,'Actual source barrier position/block changed')
   local originalBlocks=copy(def.blocks);local events=eventSnapshot(map)
   local mod=startMod(game,1);local art=copy(assert(mod.exports.state:replacements(game,def.tileset,def)))
   local before=blockImage(spec.before==55 and {657,775,657,791}or{657,775,665,791})
   if spec.before==37 then
    before:paste(nativeComposition({parts={
     {donor=nativeRefs[775],srcX=0,srcY=0,w=16,h=8,x=0,y=0},
     {donor=nativeRefs[791],srcX=0,srcY=8,w=16,h=8,x=0,y=8}}}),16,0,0,0,16,16)
    before:paste(nativeCellImage(nativeRefs[665]),16,16,0,0,16,16)
   end
   local after=blockImage(spec.after==21 and {649,649,657,657}or{657,657,665,665})
   local realBefore=artAt(art,spec.before,spec.bx,spec.by)
   local realAfter=artAt(art,spec.after,spec.bx,spec.by)
   local production=realBefore and realAfter
   for q=0,3 do production=production and realBefore.coverage[q]and realAfter.coverage[q]end
   if not production then
    positionArt(art,spec.before,spec.bx,spec.by,before)
    positionArt(art,spec.after,spec.bx,spec.by,after);inject(mod,game,def,art)
   end
   local sourceBefore=map:cellTile(spec.bx*2+1,spec.by*2)
   check(not map:isWalkableCell(spec.bx*2+1,spec.by*2),'Source barrier is not blocking before the switch')
   local frameBefore=draw()
   check(cropped(frameBefore,spec.bx*32,spec.by*32,32,32):getString()==before:getString(),'Native barrier775/791 composition shifted before the event')
   local host={save={flags={}}}
   story[def.id].onBoulderMoved(host,state,{cellX=spec.button[1],cellY=spec.button[2]})
   check(host.save.flags[spec.flag]==true and map:blockAt(spec.bx,spec.by)==spec.after,
    'Actual native switch script did not set its event and replace the whole barrier block')
   for i,id in ipairs(def.blocks)do check(id==(i==index and spec.after or originalBlocks[i]),'Switch mutated an unrelated map block')end
   check(map:isWalkableCell(spec.bx*2+1,spec.by*2),'Native cleared barrier did not become source-walkable')
   local frameAfter=draw()
   check(cropped(frameAfter,spec.bx*32,spec.by*32,32,32):getString()==after:getString(),
    'Block-ID adapter retained static barrier artwork after the actual switch event')
   check(eventSnapshot(map)==events,'Barrier graphic changed original warp/object/script definitions')
   local expectedNative=draw(true);mod.exports.dispose()
   check(draw():getString()==expectedNative:getString(),'Barrier cleanup did not restore native updated-map pixels')
   report.dynamic[#report.dynamic+1]={game=game,map=def.id,test='native switch event/barrier clear',
    native_methods={'data.scripts.story.onBoulderMoved','OverworldState.replaceBlock','Map.setBlock','TileRenderer.rebuild'},
    source_block_before=spec.before,source_block_after=spec.after,block={spec.bx,spec.by},switch_cell=spec.button,
    native_event_flag=spec.flag,source_collision_tile_before=sourceBefore,source_collision_tile_after=map:cellTile(spec.bx*2+1,spec.by*2),
    source_walkable_before=false,source_walkable_after=true,only_native_target_block_changed=true,
    no_stale_donor_art=true,cleanup_restored_native=true,
    before=encodePng(cropped(frameBefore,spec.bx*32,spec.by*32,32,32),game..'-'..def.id..'-'..spec.before..'-before-gpu.png'),
    after=encodePng(cropped(frameAfter,spec.bx*32,spec.by*32,32,32),game..'-'..def.id..'-'..spec.before..'-after-gpu.png'),
    production_reviewed_rows=production and true or false,
    private_fixture=not production and 'Exact reviewed native FR775/791 compact16 or full32 barrier plus regional657/665/649; private position records only.'or false}
  end
 end
 local cutObject
 for _,row in ipairs(mappingRows('mappings/gen2_outdoor.lua'))do
  for _,part in ipairs(row.parts or {})do if part.donor.kind=='field_object' and part.donor.game=='firered' and part.donor.id==95 then
   cutObject=row;break
  end end
  if cutObject then break end
 end
 check(cutObject~=nil,'Reviewed native Cut95 object source is absent')
 for _,game in ipairs({'red','blue','yellow'})do
  for _,kind in ipairs({'tree','grass'})do
   local state,map,def,draw=privateWorld(game,kind=='grass' and 'ROUTE_1' or 'ROUTE_2')
   local field=generated(game,'field');local swaps={};for _,swap in ipairs(field.cutTreeSwaps)do swaps[swap.before]=swap.after end
   local x,y,bx,by,id,q
   for cy=0,map.heightCells-1 do for cx=0,map.widthCells-1 do
    local tile=map:cellTile(cx,cy);local block=map:blockAt(math.floor(cx/2),math.floor(cy/2))
    local afterBlock=swaps[block]and map.tileset.blocks[swaps[block]+1]
    local afterTile=afterBlock and afterBlock[(cy%2*2+1)*4+cx%2*2+1]
    local standing=false
    for _,delta in ipairs({{-1,0},{1,0},{0,-1},{0,1}})do
     local sx,sy=cx+delta[1],cy+delta[2]
     if map:inBounds(sx,sy)and map:isWalkableCell(sx,sy)then standing=true end
    end
    if not x and afterTile and afterTile~=tile and standing and tile==(kind=='grass' and 0x52 or 0x3d)then
     x,y,bx,by,id,q=cx,cy,math.floor(cx/2),math.floor(cy/2),block,cy%2*2+cx%2
    end
   end end
   check(x~=nil,'Actual Gen1 Cut '..kind..' source position is absent')
   local index=by*def.width+bx+1;local originalBlocks=copy(def.blocks);local events=eventSnapshot(map)
   local sourceCollision=map:cellTile(x,y);local sourceHashCell,why=sourceDecoder():cell({game=game,tileset=def.tileset,id=id,quadrant=q})
   check(sourceHashCell~=nil,tostring(why))
   local mod=startMod(game,1);local art=copy(assert(mod.exports.state:replacements(game,def.tileset,def)))
   if kind=='tree' then
    local original=artAt(art,id,bx,by);local image=original and original.image:clone()or love.image.newImageData(32,32)
    local coverage=copy(original and original.coverage);coverage[q]=true
    image:paste(nativeComposition(cutObject),q%2*16,math.floor(q/2)*16,0,0,16,16)
    positionArt(art,id,bx,by,image,coverage);inject(mod,game,def,art)
   end
   local before=draw()
   local host={save={flags={}},data={field=field,text={}},stack={}}
   local TextBox=require('src.render.TextBox');local previousNew=TextBox.new
   TextBox.new=function(game,text,onDone)return{acknowledge=onDone}end
   host.stack.push=function(self,item)if item.acknowledge then item.acknowledge()end end
   local restore=bindGame(Overworld.tryCut,host)
   state.partyKnows=function()return{nickname='GPU Cut',species='BULBASAUR'}end
   local animations=0
   state.startDustAnim=function()animations=animations+1 end
   state.startCutTreeAnim=function()animations=animations+1 end
   check(state:tryCut(x,y),'Actual native tryCut rejected the source '..kind)
   restore();TextBox.new=previousNew
   check(animations==1 and map:blockAt(bx,by)==swaps[id],'Native Cut did not replace its whole source block before animation')
   check(state.cutBlocks[def.id][1].block==id,'Native Cut restoration record was lost')
   check(map:cellTile(x,y)~=(kind=='grass' and 0x52 or 0x3d),'Native Cut target still contains its original tree/grass tile')
   if kind=='grass'then check(not map:isGrassCell(x,y),'Mowed grass retained native grass/encounter classification')end
   for i,block in ipairs(def.blocks)do check(block==(i==index and swaps[id]or originalBlocks[i]),'Cut changed an unrelated map block')end
   local after=draw();local blockArt=assert(artAt(art,swaps[id],bx,by),'Native Cut after-block has no reviewed art')
   check(blockArt.coverage==nil or blockArt.coverage[q],'Native Cut after-cell lacks reviewed ground/remaining tree art')
   for py=0,15 do for px=0,15 do equalPixel(after,x*16+px,y*16+py,blockArt.image,q%2*16+px,math.floor(q/2)*16+py,'Cut retained stale tree/grass donor pixels')end end
   check(cropped(before,x*16,y*16,16,16):getString()~=cropped(after,x*16,y*16,16,16):getString(),'Cut left the original donor feature visible')
   check(eventSnapshot(map)==events,'Cut graphics changed source warp/object/script definitions')
   local expectedNative=draw(true);mod.exports.dispose();check(draw():getString()==expectedNative:getString(),'Cut cleanup did not restore updated native pixels')
   report.dynamic[#report.dynamic+1]={game=game,map=def.id,test='native tryCut '..kind,
    native_methods={'OverworldState.tryCut','Map.setBlock','TileRenderer.rebuild'},
    source_block_before=id,source_block_after=swaps[id],cell={x,y},quadrant=q,source_rgba_sha256=sourceHashCell.sourceHash,
    source_collision_tile_before=sourceCollision,source_collision_tile_after=map:cellTile(x,y),
    source_grass_after=map:isGrassCell(x,y),native_cut_restoration_record=true,only_native_target_block_changed=true,
    no_stale_donor_art=true,cleanup_restored_native=true,
    before=encodePng(cropped(before,bx*32,by*32,32,32),game..'-cut-'..kind..'-before-gpu.png'),
    after=encodePng(cropped(after,bx*32,by*32,32,32),game..'-cut-'..kind..'-after-gpu.png'),
    private_fixture=kind=='tree' and 'One source Cut-tree cell uses the already reviewed full nativeFR95 object overEmerald1; private position only.' or false,
    limits='Native Cut block swap/text callback; text immediately acknowledged and dust/tree-split animation entry recorded without running visual FX/audio.'}
  end
 end
 for _,game in ipairs({'red','blue','yellow'})do
  local state,map,def,draw=privateWorld(game,'SEAFOAM_ISLANDS_B2F')
  local field=generated(game,'field');local host={save={flags={}},data={field=field}}
  local restore=bindGame(Overworld.boulderIntoHole,host)
  local sourceBefore=snapshot(map,1);local events=eventSnapshot(map)
  local mod=startMod(game,1);local art=copy(assert(mod.exports.state:replacements(game,def.tileset,def)))
  local holeRef={game='firered',tileset='general__rom_082d4e24',id=646,hash='7de68b16225465d14d63ea1f3a50af4133266643b240f6cdafd0b47af5d8bfa2'}
  local holes=state:seafoamHolesFor(def.id);check(#holes==2,'SeafoamB2F native special hole set changed')
  local production=true
  for _,entry in ipairs(holes)do
   local h=entry.hole;local bx,by=math.floor(h.x/2),math.floor(h.y/2);local id=map:blockAt(bx,by);local q=h.y%2*2+h.x%2
   local original=artAt(art,id,bx,by);local image=original and original.image:clone()or love.image.newImageData(32,32)
   if not(original and original.coverage[q])then
    production=false
    local coverage=copy(original and original.coverage);coverage[q]=true
    image:paste(nativeCellImage(holeRef),q%2*16,math.floor(q/2)*16,0,0,16,16)
    positionArt(art,id,bx,by,image,coverage)
   end
  end
  if not production then inject(mod,game,def,art)end
  local before=draw();local pathCalls=0
  local currentState=setmetatable({map={id='SEAFOAM_ISLANDS_B3F'},player={cellX=18,cellY=7,surfing=true}}, {__index=Overworld})
  currentState.runSpinnerMoves=function(self,moves)pathCalls=pathCalls+1;check(#moves==3,'Native Seafoam current path changed')end
  check(currentState:checkSeafoamCurrent()and pathCalls==1,'Native Seafoam current is not active before both boulders fall')
  for _,entry in ipairs(holes)do
   local h=entry.hole;local npc={cellX=h.x,cellY=h.y};state.npcs={npc};state.entities={npc}
   check(state:boulderIntoHole(npc),'Actual native boulderIntoHole rejected its field-defined hole')
   check(host.save.flags[h.boulderEvent]and #state.npcs==0 and #state.entities==0,'Native boulder event/removal changed')
  end
  check(not currentState:checkSeafoamCurrent()and pathCalls==1,'Native Seafoam current did not stop after both expected events')
  restore()
  local after=draw()
  check(snapshot(map,1)==sourceBefore and eventSnapshot(map)==events,'Seafoam plugging changed source blocks/collision/warps/scripts')
  check(before:getString()==after:getString(),'Native boulder-hole event must leave the source hole background open')
  for _,entry in ipairs(holes)do
   local h=entry.hole
   for y=0,15 do for x=0,15 do equalPixel(after,h.x*16+x,h.y*16+y,nativeCellImage(holeRef),x,y,'Native646 hole art changed after boulder fell')end end
  end
  local expectedNative=draw(true);mod.exports.dispose();check(draw():getString()==expectedNative:getString(),'Seafoam cleanup retained private hole art')
  report.dynamic[#report.dynamic+1]={game=game,map=def.id,test='native Seafoam boulder holes and current flags',
   native_methods={'OverworldState.boulderIntoHole','OverworldState.seafoamHolesFor','OverworldState.checkSeafoamCurrent'},
   holes=2,native_boulder_events_set=true,native_boulder_objects_removed=true,current_active_before=true,current_active_after=false,
   source_background_holes_remain_open=true,source_blocks_collision_warps_events_unchanged=true,
   exact_native646_pixels=true,cleanup_restored_native=true,
   production_reviewed_rows=production,
   private_fixture=not production and 'Two actual special holes use complete same-regionalFR646 through private position records only; no production writes.'or false}
 end
 check(#report.warnings==0,'Dynamic probe mapping warnings occurred')
 report.status='passed';write('report.json',Json.encode(report))
end
"""


def main() -> int:
    marker = " -- Native Gen1 TileRenderer on real Red Pallet Town."
    base = validate_gpu.LUA
    prefix = base[:base.index(marker)]
    suffix = base[base.index("\nfunction love.load()") :]
    validate_gpu.LUA = prefix + DYNAMIC + suffix
    if "--output" not in sys.argv:
        sys.argv.extend(["--output", str(Path(__file__).resolve().parents[2] / ".work/tileshift-gen1-dynamic-gpu")])
    return validate_gpu.main()


if __name__ == "__main__":
    raise SystemExit(main())
