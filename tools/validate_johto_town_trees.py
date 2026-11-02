"""Validate complete native 16x48 Johto town trees in every affected GSC map.

Only private GPU readbacks and reports are written. Source pixels, imported
maps, installed mods and saves remain unchanged. Native-source preservation is
audited separately from this renderer, source-guard and decorative-canopy test.
"""
import sys
from pathlib import Path

import validate_gpu


FOCUSED = r"""
 report.type='complete native three-cell Johto town-tree GPU validation'
 report.limits='Actual Gen2 World backgrounds, border decorations and collision/event snapshots, plus synthetic actor rectangles through the real decoration replay method. No interactive playthrough. Native-source pixel preservation is audited separately.'
 report.version=Json.decode(assert(read(MOD..'/manifest.json'))).version
 local folder='assets/third_party/johto-hacks/town-trees/'
 local provenance=Json.decode(assert(read(MOD..'/'..folder..'provenance.json')))
 check(provenance.source_pair=='082d4a94_082d4b54'and provenance.source_metatiles[1]==600
  and provenance.source_metatiles[2]==601 and provenance.source_metatiles[3]==608
  and provenance.source_map=='g46_m099'and provenance.top_cell[1]==23
  and provenance.top_cell[2]==18 and provenance.pixel_scale==1,
  'Town-tree provenance no longer identifies the complete reviewed native three-cell tree')
 check(provenance.native_dimensions[1]==16 and provenance.native_dimensions[2]==48,
  'Town tree must retain its complete original16x48 dimensions')
 local assets={}
 for _,name in ipairs({'whole.png','top.png','middle.png','bottom.png'})do
  local bytes=assert(read(MOD..'/'..folder..name))
  local expected=assert(provenance.files[name],'Tree provenance is missing a PNG file fingerprint')
  check(hash(bytes)==expected,'Town-tree PNG differs from its recorded fingerprint')
  local image=love.image.newImageData(love.filesystem.newFileData(bytes,name))
  check(image:getWidth()==16 and image:getHeight()==(name=='whole.png'and 48 or 16),'Town-tree source dimensions changed')
  assets[name]={image=image,hash=expected}
 end
 local whole=assets['whole.png'].image
 local opaque,transparent,left,top,right,bottom=0,0,16,48,-1,-1
 for y=0,47 do for x=0,15 do
  local _,_,_,a=whole:getPixel(x,y)
  check(a==0 or a==1,'Native town-tree alpha must remain pixel-exact')
  if a>0 then
   opaque=opaque+1;left=math.min(left,x);right=math.max(right,x);top=math.min(top,y);bottom=math.max(bottom,y)
  else transparent=transparent+1 end
  local part=assets[y<16 and'top.png'or(y<32 and'middle.png'or'bottom.png')].image
  equalPixel(whole,x,y,part,x,y%16,'Town-tree sections do not reconstruct the whole16x48 artwork')
 end end
 check(opaque>0 and transparent>0 and bottom-top+1>32,'Town tree must retain its complete three-cell silhouette')
 check(opaque==provenance.opaque_source_pixels_retained,'Town-tree opaque count differs from the native-source audit')
 -- Every source field coordinate cleared by the outside-connected mask must
 -- remain transparent. The independent authoring audit establishes which
 -- source pixels belong to that mask and preserves every other source pixel.
 local fieldMask=assert(provenance.outside_connected_field_mask or provenance.omitted_field_coordinates,
  'Town-tree provenance must record its outside-connected field mask')
 check(#fieldMask>0,'Native field-removal mask is empty')
 for _,point in ipairs(fieldMask)do
  check(type(point[1])=='number'and type(point[2])=='number'and point[1]>=0 and point[1]<16 and point[2]>=0 and point[2]<48,
   'Native field mask has an invalid coordinate')
  local _,_,_,a=whole:getPixel(point[1],point[2]);check(a==0,'Outside-connected source field remains baked into the town tree')
 end
 report.source_art={dimensions={16,48},visible_alpha_bounds={left,top,right+1,bottom+1},
  opaque_pixels=opaque,transparent_pixels=transparent,outside_connected_field_pixels_checked=#fieldMask,
  all_three_sections_reconstruct_whole_exactly=true,
  source_pair={tileset='082d4a94_082d4b54',top=600,middle=601,bottom=608},
  files={whole=assets['whole.png'].hash,top=assets['top.png'].hash,middle=assets['middle.png'].hash,bottom=assets['bottom.png'].hash}}
 local Mapping=assert(load(assert(read(MOD..'/lib/mapping.lua'))))()
 local rowFiles={'mappings/gen2_outdoor.lua','mappings/gen2_outdoor_extended.lua','mappings/johto_shared_finish.lua'}
 local byGame={gold={},silver={},crystal={}}
 local targetRows,canopyAliases=0,0
 report.mapping_files={}
 for _,file in ipairs(rowFiles)do
  local count=0
  for _,row in ipairs(mappingRows(file))do
   if byGame[row.game]and(row.role=='dense_conifer_crown'or row.role=='dense_conifer_trunk')then
    local valid,why=Mapping.validate(row);check(valid,tostring(why))
    local name=row.role=='dense_conifer_crown'and'middle.png'or'bottom.png'
    check(row.kind=='third_party'and row.asset==folder..name and row.assetFileHash==assets[name].hash,
     'Town-tree core row does not use the correct checked native middle/root section')
    if row.role=='dense_conifer_crown'then
     check(row.canopy and row.canopy.asset==folder..'top.png'and row.canopy.hash==assets['top.png'].hash,
      'Town-tree crown must carry its exact native upper canopy reference')
     canopyAliases=canopyAliases+1
    else check(row.canopy==nil,'Town-tree roots must not generate a second canopy')end
    check(row.donor==nil and row.parts==nil and row.base~=nil and not row.animated,
     'Town-tree artwork is bypassed by another source or changed the fixed native tree behavior')
    check(row.x==nil and row.y==nil,'Unexpected position-scoped town-tree mapping')
    local rows=byGame[row.game][row.map]or{};byGame[row.game][row.map]=rows
    rows[#rows+1]=row;targetRows=targetRows+1;count=count+1
   end
  end
  report.mapping_files[#report.mapping_files+1]={path=file,rows=count}
 end
 check(targetRows==338,'Expected all338 reviewed crown/trunk source aliases')
 check(canopyAliases==169,'Expected all169 source-anchored native canopy aliases')
 report.target_rows=targetRows
 report.canopy_aliases=canopyAliases
 report.totals={map_variants=0,accepted_target_rows=0,crown_cells=0,trunk_cells=0,
  complete_tree_pairs=0,independent_tree_pixels=0,native_gpu_tree_pixels=0,decorative_overlay_pixels=0,checked_gpu_pixels=0,
  canopy_entries=0,negative_canopy_entries=0,canopy_overlay_pixels=0,border_canopy_pixels=0,
  canopies_over_prior_roots=0,building_overlap_cells=0,building_frontY_ties=0,warm_draw_frames=0}
 local compositionCache={}
 local function expectedTile(row)
  local key=row.asset..tableString(row.base)
  if not compositionCache[key]then compositionCache[key]=nativeComposition(row)end
  return compositionCache[key]
 end
 local function overlayTile(base,overlay)
  local result=love.image.newImageData(16,16);result:paste(base,0,0)
  for y=0,15 do for x=0,15 do
   local r,g,b,a=overlay:getPixel(x,y)
   if a>0 then
    local dr,dg,db,da=result:getPixel(x,y);local alpha=a+da*(1-a)
    result:setPixel(x,y,(r*a+dr*da*(1-a))/alpha,(g*a+dg*da*(1-a))/alpha,(b*a+db*da*(1-a))/alpha,alpha)
   end
  end end
  return result
 end
 local actorGames={}
 local function actorMarker(mod,map,world,entry)
  local top=assets['top.png'].image
  local entity={px=entry.x*16,sprite={frameWidth=16,frameHeight=16,anchorX=8,anchorY=16}}
  local magenta=love.image.newImageData(16,16)
  for y=0,15 do for x=0,15 do magenta:setPixel(x,y,1,0,1,1)end end
  local body=G.newImage(magenta);body:setFilter('nearest','nearest')
  entity.draw=function(e,ox,oy,s)
   G.setColor(1,1,1,1)
   G.draw(body,ox+e.px*s,oy+(e.py+(e.spriteYOffset or 0)-4)*s,0,s,s)
  end
  local function render(front)
   entity.py=entry.frontY-(front and 12 or 13)
   entity.spriteYOffset=entry.y*16-entity.py+4
   return capture(16,16,function()
    world:drawPersonEntry({entity=entity,sx=-entry.x*16,sy=-entry.y*16,ox=0,oy=0,
     drawSprite=function(row,ox,oy,s)entity:draw(ox,oy,s,row)end},1)
   end)
  end
  local behind,front=render(false),render(true);local covered,clear=0,0
  for y=0,15 do for x=0,15 do
   local _,_,_,a=top:getPixel(x,y)
   if a>0 then equalPixel(behind,x,y,top,x,y,'Native canopy did not cover the synthetic actor behind its physical front');covered=covered+1
   else equalPixel(behind,x,y,magenta,x,y,'Transparent canopy pixel hid the synthetic actor');clear=clear+1 end
   equalPixel(front,x,y,magenta,x,y,'Canopy covered the synthetic actor standing at its physical front')
  end end
  check(covered>0 and clear>0,'Canopy actor marker must sample opaque and transparent pixels')
  body:release()
  return {scope='Synthetic magenta entity through native World.drawPersonEntry and canopy replay; not an interactive actor',
   cell={entry.x,entry.y},physical_frontY=entry.frontY,opaque_hides_behind=covered,
   transparent_reveals_behind=clear,front_threshold_reveals_all=256,actual_native_person_entry=true}
 end
 local function warmDecorations(mod,world,def,expectedCells)
  local ownReads,assetReads=0,0;local readOwn,pathOwn=mod.read,mod.assets.path
  mod.read=function(self,...)ownReads=ownReads+1;return readOwn(self,...)end
  mod.assets.path=function(self,...)assetReads=assetReads+1;return pathOwn(self,...)end
  local imports,accepted=importReads,mod.exports.state.accepted
  capture(160,144,function()
   for i=1,8 do mod.exports.roofs:map(world,def,0,0,1)end
  end)
  mod.read,mod.assets.path=readOwn,pathOwn
  check(mod.exports.roofs:cells(GV.get(),def)==expectedCells,'Warm canopy drawing rebuilt decorative geometry')
  check(importReads==imports and ownReads==0 and assetReads==0,'Warm canopy drawing reread source or artwork files')
  check(mod.exports.state.accepted==accepted,'Warm canopy drawing rebuilt guarded mapping rows')
  return {frames=8,import_file_reads=0,own_file_reads=0,asset_file_reads=0,
   accepted_row_rebuilds=0,decorative_geometry_identity_preserved=true,
   scope='Repeated native decoration draws with cached geometry; unit fixtures independently instrument source expansion.'}
 end
 for _,game in ipairs({'gold','silver','crystal'})do
  local names={};for name in pairs(byGame[game])do names[#names+1]=name end;table.sort(names)
  for _,id in ipairs(names)do
   GV.set(game);assetGame=game;clock=0
   local world,map,def=world2(game,id)
   world.mapImage=world:imageFor(map.id)
   local native=drawWorld2(world)
   local mechanics,events=snapshot(map,2),eventSnapshot(map)
   local mod=startMod(game,2,world);world.mapImage=world:imageFor(map.id)
   local art=assert(mod.exports.state:replacements(game,def.tileset,def));local after=drawWorld2(world)
   check(mod.exports.state.rejected==0,'Town-tree map rejected reviewed artwork')
   local cells,sourceRows={},byGame[game][id]
   local f={game=game,map=id,coverage=coverage(def,art),target_source_rows=#sourceRows,
    before=encodePng(native,game..'-'..id..'-native-gpu.png'),
    after=encodePng(after,game..'-'..id..'-gen3-gpu.png'),
    collision_before=mechanics,events_before=events,crown_cells=0,trunk_cells=0,
    independent_tree_pixels=0,native_gpu_tree_pixels=0,decorative_overlay_pixels=0,
    canopy_entries=0,negative_canopy_entries=0,canopy_overlay_pixels=0,border_canopy_pixels=0,
    canopies_over_prior_roots=0,building_overlap_cells=0,building_frontY_ties=0,warm_draw_frames=0}
   f.checked_gpu_pixels=verifyCoveredPixels(def,art,after,game..' '..id..' complete native three-cell trees')
   local roof=roofPixels(def)
   for _,row in ipairs(sourceRows)do
    local source,why=sourceDecoder():cell({game=game,tileset=def.tileset,id=row.id,quadrant=row.quadrant,
     hash=row.sourceHash,hashOnly=true,map=def,monochrome=true,sourceFiles=row.sourceFiles})
    check(source~=nil,'Town-tree source guard failed: '..tostring(why))
    local expected=expectedTile(row);local occurrences=0
    for index,bid in ipairs(def.blocks)do if bid==row.id then
     local bx,by=(index-1)%def.width,math.floor((index-1)/def.width)
     local cx,cy=bx*2+row.quadrant%2,by*2+math.floor(row.quadrant/2)
     local key=cx..':'..cy
     check(cells[key]==nil,'Two town-tree aliases target the same actual source cell')
     cells[key]={x=cx,y=cy,role=row.role,row=row}
     local block=assert(artAt(art,bid,bx,by),'Town-tree source block was not accepted')
     check(block.coverage and block.coverage[row.quadrant],'Town-tree source half was not accepted')
     if row.sourceCollision~=nil then check(map:cellCollision(cx,cy)==row.sourceCollision,'Town-tree native collision differs from the reviewed source')end
     local final=expected;local overlay=roof[cy*65536+cx]
     if overlay then
      final=love.image.newImageData(16,16);final:paste(expected,0,0)
      for y=0,15 do for x=0,15 do
       local r,g,b,a=overlay:getPixel(x,y)
       if a>0 then
        local dr,dg,db,da=final:getPixel(x,y);local alpha=a+da*(1-a)
        final:setPixel(x,y,(r*a+dr*da*(1-a))/alpha,(g*a+dg*da*(1-a))/alpha,(b*a+db*da*(1-a))/alpha,alpha)
        f.decorative_overlay_pixels=f.decorative_overlay_pixels+1
       end
      end end
     end
     for y=0,15 do for x=0,15 do
      equalPixel(block.image,row.quadrant%2*16+x,math.floor(row.quadrant/2)*16+y,
       expected,x,y,'Accepted town-tree source half differs from the independent native artwork')
      equalPixel(after,cx*16+x,cy*16+y,final,x,y,'Rendered town-tree source half differs from the independent native artwork')
      f.independent_tree_pixels=f.independent_tree_pixels+1;f.native_gpu_tree_pixels=f.native_gpu_tree_pixels+1
     end end
     if row.role=='dense_conifer_crown'then f.crown_cells=f.crown_cells+1 else f.trunk_cells=f.trunk_cells+1 end
     occurrences=occurrences+1
    end end
    check(occurrences>0,'Reviewed town-tree source alias has no actual map occurrence')
    report.totals.accepted_target_rows=report.totals.accepted_target_rows+1
   end
   for _,cell in pairs(cells)do
    local crown=cell.role=='dense_conifer_crown'
    local other=cells[cell.x..':'..(cell.y+(crown and 1 or -1))]
    check(other and other.role==(crown and'dense_conifer_trunk'or'dense_conifer_crown'),
     'Actual native town-tree crown/trunk pair is incomplete or displaced')
   end
   check(f.crown_cells==f.trunk_cells and f.crown_cells>0,'Town-tree map does not contain complete two-cell pairs')
   f.complete_tree_pairs=f.crown_cells
   -- Independently resolve every source crown's full extra upper cell, rather
   -- than assuming a complete tree fits inside the original two source cells.
   local expectedCanopies={}
   for _,cell in pairs(cells)do if cell.role=='dense_conifer_crown'then
    local key=(cell.y-1)*65536+cell.x
    check(expectedCanopies[key]==nil,'Two town-tree crowns generate the same canopy position')
    expectedCanopies[key]={x=cell.x,y=cell.y-1,sourceY=cell.y,frontY=(cell.y+2)*16,row=cell.row}
   end end
   local runtime=assert(mod.exports.roofs:cells(game,def),'Native tree canopy cache is absent')
   for _,line in pairs(runtime.rows)do for _,entry in ipairs(line)do if entry.treeCanopy then
    local expected=expectedCanopies[entry.y*65536+entry.x]
    check(expected~=nil and expected.entry==nil,'Native canopy cache contains an extra or duplicate tree')
    check(entry.role=='dense_conifer_canopy'and entry.sourceY==expected.sourceY and entry.frontY==expected.frontY,
     'Native canopy lost its source anchor or physical tree front')
    check(hash(entry.data:getString())==hash(assets['top.png'].image:getString()),
     'Native upper canopy differs from the independent full top600 artwork')
    expected.entry=entry;f.canopy_entries=f.canopy_entries+1
    if entry.y==-1 then f.negative_canopy_entries=f.negative_canopy_entries+1
    else check(entry.y>=0,'Tree canopy extended more than one row beyond the map')end
   end end end
   check(f.canopy_entries==f.crown_cells,'Native tree canopy cache omitted a complete source tree')
   local savedMap=mod.exports.roofs.map;mod.exports.roofs.map=function()end
   local beneath=drawWorld2(world);mod.exports.roofs.map=savedMap
   local markerEntry
   for key,expected in pairs(expectedCanopies)do
    local entry=assert(expected.entry,'Full tree is missing its native upper canopy')
    local stack=assert(runtime.grid[key],'Native canopy is missing from the actor replay grid')
    local found,prior,statics=false,true,0
    while stack do
     if stack==entry then found=true;prior=false
     elseif not stack.treeCanopy then
      statics=statics+1
      if prior then
       check(type(stack.frontY)=='number'and stack.frontY<entry.frontY,
        'A nearer building was drawn before a native canopy')
      else
       check(stack.frontY==nil or stack.frontY>=entry.frontY,
        'A farther building was drawn over a native canopy')
       if stack.frontY==entry.frontY then f.building_frontY_ties=f.building_frontY_ties+1 end
      end
     else check(false,'Two native tree canopies overlap at one source cell')end
     stack=stack.next
    end
    check(found,'Native canopy actor replay grid lost its draw entry')
    if statics>0 then f.building_overlap_cells=f.building_overlap_cells+1
    elseif not markerEntry then markerEntry=entry end
    local rootAbove=cells[entry.x..':'..entry.y]
    if rootAbove and rootAbove.role=='dense_conifer_trunk'then
     f.canopies_over_prior_roots=f.canopies_over_prior_roots+1
    end
    if entry.y>=0 then
     local tile=love.image.newImageData(16,16);tile:paste(beneath,0,0,entry.x*16,entry.y*16,16,16)
     local over=assert(roof[key],'Independent decorative expectation omitted the native canopy')
     local final=overlayTile(tile,over)
     for y=0,15 do for x=0,15 do
      equalPixel(after,entry.x*16+x,entry.y*16+y,final,x,y,
       'Complete native canopy or its ordered building overlap differs from the independent source')
      f.canopy_overlay_pixels=f.canopy_overlay_pixels+1
     end end
    end
   end
   if f.negative_canopy_entries>0 then
    -- Include a real16px viewport strip above the native map canvas. These
    -- entries cannot be verified by a background readback clipped at y=0.
    local border=capture(world.viewW,world.viewH+16,function()
     mod.exports.roofs:map(world,def,0,16,1)
    end)
    for key,expected in pairs(expectedCanopies)do if expected.y==-1 then
     local over=assert(roof[key],'Independent expectation omitted the negative-row canopy')
     for y=0,15 do for x=0,15 do
      equalPixel(border,expected.x*16+x,y,over,x,y,
       'Native canopy above the source-map canvas disappeared or lost transparency')
      f.border_canopy_pixels=f.border_canopy_pixels+1
     end end
    end end
    if id=='NEW_BARK_TOWN'or id=='ECRUTEAK_CITY'then
     f.border_canopies=encodePng(border,game..'-'..id..'-native-canopy-border-gpu.png')
    end
   end
   if markerEntry and not actorGames[game]then
    f.synthetic_actor_canopy=actorMarker(mod,map,world,markerEntry);actorGames[game]=true
   end
   f.warm_draws=warmDecorations(mod,world,def,runtime)
   f.warm_draw_frames=f.warm_draws.frames
   f.collision_after=snapshot(map,2);f.events_after=eventSnapshot(map)
   check(f.collision_after==mechanics and f.events_after==events,'Town-tree artwork modified source collision/events or interactions')
   f.source_collision_events_unchanged=true
   mod.exports.dispose();world.mapImages={};world.animCells={};world.mapImage=world:imageFor(map.id)
   check(drawWorld2(world):getString()==native:getString(),'Town-tree cleanup failed to restore the original native background')
   f.cleanup_restored_native=true
   for _,key in ipairs({'crown_cells','trunk_cells','complete_tree_pairs','independent_tree_pixels','native_gpu_tree_pixels','decorative_overlay_pixels','checked_gpu_pixels',
    'canopy_entries','negative_canopy_entries','canopy_overlay_pixels','border_canopy_pixels','canopies_over_prior_roots','building_overlap_cells','building_frontY_ties','warm_draw_frames'})do
    report.totals[key]=report.totals[key]+f[key]
   end
   report.totals.map_variants=report.totals.map_variants+1
   report.fixtures[#report.fixtures+1]=f
   write('progress.json',Json.encode({fixtures=#report.fixtures,checks=report.checks,game=game,map=id}))
  end
 end
 check(#report.fixtures==82 and report.totals.accepted_target_rows==338,'Town-tree source-map matrix is incomplete')
 check(report.totals.complete_tree_pairs==12150 and report.totals.crown_cells==12150 and report.totals.trunk_cells==12150,
  'Town-tree probe did not check all12150 actual native pairs')
 check(report.totals.canopy_entries==12150 and report.totals.negative_canopy_entries==1478,
  'Town-tree probe missed a complete canopy or one of the1478native border canopies')
 check(report.totals.building_overlap_cells==34,'Town-tree probe did not exercise all34native building/canopy overlaps')
 check(report.totals.canopies_over_prior_roots>0,'Native canopy-over-root overlap was not exercised')
 for _,game in ipairs({'gold','silver','crystal'})do check(actorGames[game],'Synthetic canopy actor replay was not checked in '..game)end
 -- Exercise the real native connected-map draw order: neighbor canvas and
 -- animations first, current-map canvas afterward, then outside-canopy replay.
 -- This catches a tip that is correct on the isolated map but pops away when
 -- the player stands on the map immediately north of that tree.
 report.connected_canopies={}
 for _,game in ipairs({'gold','crystal'})do
  GV.set(game);assetGame=game;clock=0
  local world,map,def=world2(game,'VIOLET_CITY')
  local conn=assert(def.connections and def.connections.south,'Native Violet south connection is absent')
  local neighborId=conn.mapId or conn.map
  check(neighborId=='ROUTE_32','Native connected canopy fixture no longer leads south to Route32')
  local neighborDef=assert(world.maps[neighborId])
  local nb={id=neighborId,ox=(conn.offset or 0)*32,oy=def.height*32}
  world.viewW,world.viewH=160,96;world.camera={x=48,y=nb.oy-48}
  world.mapImage=world:imageFor(map.id);nb.image=world:imageFor(nb.id);world.neighbors={nb}
  local neighborMap=Map2.new(neighborDef,world.tilesets[neighborDef.tileset])
  local beforeCurrent,beforeNeighbor=snapshot(map,2),snapshot(neighborMap,2)
  local eventCurrent,eventNeighbor=eventSnapshot(map),eventSnapshot(neighborMap)
  local function drawGround()return capture(world.viewW,world.viewH,function()world:drawGround(1)end)end
  local original=drawGround();local mod=startMod(game,2,world)
  world.mapImage=world:imageFor(map.id);nb.image=world:imageFor(nb.id)
  local ownCells=mod.exports.roofs:cells(game,def)
  local neighborCells=assert(mod.exports.roofs:cells(game,neighborDef))
  local entry
  for _,candidate in ipairs(neighborCells.rows[-1]or{})do
   local gx,gy=candidate.x*16+nb.ox,candidate.y*16+nb.oy
   if candidate.treeCanopy and gx>=world.camera.x and gx+16<=world.camera.x+world.viewW
    and(not ownCells or not ownCells.grid[math.floor(gy/16)*65536+math.floor(gx/16)])then entry=candidate;break end
  end
  check(entry~=nil,'Connected canopy fixture has no visible unambiguous outside tree tip')
  local replay=assert(mod.exports.roofs.borders,'Native connected-map canopy replay is missing')
  mod.exports.roofs.borders=function()end
  local withoutReplay=drawGround();mod.exports.roofs.borders=replay
  local complete=drawGround();local sx=entry.x*16+nb.ox-world.camera.x
  local sy=entry.y*16+nb.oy-world.camera.y
  check(sy>=0 and sy+16<=world.viewH,'Connected canopy test clipped the native outside row')
  local covered,clear,changed=0,0,0
  for y=0,15 do for x=0,15 do
   local r,g,b,a=assets['top.png'].image:getPixel(x,y)
   if a>0 then
    equalPixel(complete,sx+x,sy+y,assets['top.png'].image,x,y,
     'South-neighbor canopy disappeared under the later current-map canvas')
    covered=covered+1
    local nr,ng,nbc=withoutReplay:getPixel(sx+x,sy+y)
    if math.abs(nr-r)>1/255 or math.abs(ng-g)>1/255 or math.abs(nbc-b)>1/255 then changed=changed+1 end
   else
    equalPixel(complete,sx+x,sy+y,withoutReplay,sx+x,sy+y,
     'South-neighbor canopy painted its empty corner over the current map')
    clear=clear+1
   end
  end end
  check(changed>0 and covered>0 and clear>0,'Connected canopy regression fixture would not detect a missing replay')
  local globalX,globalY=entry.x*16+nb.ox,entry.y*16+nb.oy
  local magenta=love.image.newImageData(16,16)
  for y=0,15 do for x=0,15 do magenta:setPixel(x,y,1,0,1,1)end end
  local body=G.newImage(magenta);body:setFilter('nearest','nearest')
  local actorProofs={}
  for _,ghost in ipairs({false,true})do
   local entity={px=ghost and entry.x*16 or globalX,
    sprite={frameWidth=16,frameHeight=16,anchorX=8,anchorY=16}}
   entity.draw=function(e,ox,oy,s)
    G.setColor(1,1,1,1);G.draw(body,ox+e.px*s,oy+(e.py+(e.spriteYOffset or 0)-4)*s,0,s,s)
   end
   local function marker(front)
    entity.py=entry.frontY+(ghost and 0 or nb.oy)-(front and 12 or 13)
    entity.spriteYOffset=(ghost and entry.y*16 or globalY)-entity.py+4
    local ox,oy=ghost and nb.ox or 0,ghost and nb.oy or 0
    return capture(16,16,function()
     world:drawPersonEntry({entity=entity,sx=ox-globalX,sy=oy-globalY,ox=ox,oy=oy,
      drawSprite=function(row,sx,sy,s)entity:draw(sx,sy,s,row)end},1)
    end)
   end
   local behind,front=marker(false),marker(true)
   for y=0,15 do for x=0,15 do
    local _,_,_,a=assets['top.png'].image:getPixel(x,y)
    equalPixel(behind,x,y,a>0 and assets['top.png'].image or magenta,x,y,
     'Native connected person-entry canopy replay lost its actor origin or transparent pixels')
    equalPixel(front,x,y,magenta,x,y,'Neighbor canopy hid the native person-entry actor at its translated physical front')
   end end
   actorProofs[#actorProofs+1]={kind=ghost and'neighbor-map ghost'or'current-map actor',
    actual_native_person_entry=true,behind_and_transparency_exact=true,front_threshold_exact=true,
    ghost_origin=ghost and{nb.ox,nb.oy}or nil}
  end
  body:release()
  drawGround()
  local ownReads,assetReads=0,0;local originalRead,originalPath=mod.read,mod.assets.path
  mod.read=function(self,...)ownReads=ownReads+1;return originalRead(self,...)end
  mod.assets.path=function(self,...)assetReads=assetReads+1;return originalPath(self,...)end
  local imports,accepted=importReads,mod.exports.state.accepted
  capture(world.viewW,world.viewH,function()for i=1,8 do world:drawGround(1)end end)
  mod.read,mod.assets.path=originalRead,originalPath
  check(importReads==imports and ownReads==0 and assetReads==0,'Warm connected-map canopy replay reread source or artwork files')
  check(mod.exports.state.accepted==accepted and mod.exports.roofs:cells(game,neighborDef)==neighborCells,
   'Warm connected-map canopy replay rebuilt mappings or decorative geometry')
  check(snapshot(map,2)==beforeCurrent and snapshot(neighborMap,2)==beforeNeighbor
   and eventSnapshot(map)==eventCurrent and eventSnapshot(neighborMap)==eventNeighbor,
   'Connected canopy drawing changed either native map geometry or events')
  local connected={game=game,current_map=def.id,neighbor_map=neighborId,
   native_south_offset={nb.ox,nb.oy},canopy_cell={entry.x,entry.y},screen_origin={sx,sy},
   outside_opaque_pixels_visible=covered,outside_transparent_pixels_preserved=clear,
   missing_replay_would_change_pixels=changed,synthetic_actor_neighbor_translation_verified=true,
   synthetic_actor_front_threshold_verified=true,native_person_entry_actors=actorProofs,
   warm_ground_frames=8,warm_source_reads=0,
   warm_own_reads=0,warm_asset_reads=0,source_geometry_events_unchanged=true,
   before=encodePng(original,game..'-VIOLET_ROUTE32-native-connected-gpu.png'),
   after=encodePng(complete,game..'-VIOLET_ROUTE32-gen3-connected-canopy-gpu.png'),
   without_replay=encodePng(withoutReplay,game..'-VIOLET_ROUTE32-no-border-replay-gpu.png')}
  report.connected_canopies[#report.connected_canopies+1]=connected
  if game=='crystal'then report.connected_canopy=connected end
  mod.exports.dispose()
 end
 check(#report.warnings==0,'Town-tree probe reported warnings')
 report.status='passed';write('report.json',Json.encode(report))
end
"""


def main():
    base = validate_gpu.LUA
    prefix = base[:base.index(" -- Native Gen1 TileRenderer on real Red Pallet Town.")]
    setup = base[base.index(" -- Real Gold/Silver/Crystal World bake"):
                 base.index(" local function verifyGen2Ladders")]
    validate_gpu.LUA = prefix + setup + FOCUSED + base[base.index("function love.load()") :]
    if "--output" not in sys.argv:
        output = Path(__file__).resolve().parents[2] / ".work/tileshift-v0293-town-gpu"
        sys.argv.extend(["--output", str(output)])
    return validate_gpu.main()


if __name__ == "__main__":
    raise SystemExit(main())
