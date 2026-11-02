"""Validate native 16x32 Johto town trees in every affected GSC map.

Only private GPU readbacks and reports are written. Source pixels, imported
maps, installed mods and saves remain unchanged. Native-source preservation is
audited separately from this renderer, source-guard and two-cell geometry test.
"""
import sys
from pathlib import Path

import validate_gpu


FOCUSED = r"""
 report.type='native two-cell Johto town-tree GPU validation'
 report.limits='Actual Gen2 World map backgrounds and collision/event snapshots. No actors or interactive playthrough. Native-source pixel preservation is audited separately.'
 report.version=Json.decode(assert(read(MOD..'/manifest.json'))).version
 local folder='assets/third_party/johto-hacks/town-trees/'
 local provenance=Json.decode(assert(read(MOD..'/'..folder..'provenance.json')))
 check(provenance.source_pair=='082d4a94_082d4dc4'and provenance.source_metatiles[1]==696
  and provenance.source_metatiles[2]==552 and provenance.source_map=='g44_m042'
  and provenance.top_cell[1]==26 and provenance.top_cell[2]==29 and provenance.pixel_scale==1,
  'Town-tree provenance no longer identifies the reviewed unscaled native pair')
 local assets={}
 for _,name in ipairs({'whole.png','top.png','bottom.png'})do
  local bytes=assert(read(MOD..'/'..folder..name))
  local expected=assert(provenance.files[name],'Tree provenance is missing a PNG file fingerprint')
  check(hash(bytes)==expected,'Town-tree PNG differs from its recorded fingerprint')
  local image=love.image.newImageData(love.filesystem.newFileData(bytes,name))
  check(image:getWidth()==16 and image:getHeight()==(name=='whole.png'and 32 or 16),'Town-tree source dimensions changed')
  assets[name]={image=image,hash=expected}
 end
 local whole=assets['whole.png'].image
 local opaque,transparent,left,top,right,bottom=0,0,16,32,-1,-1
 for y=0,31 do for x=0,15 do
  local _,_,_,a=whole:getPixel(x,y)
  check(a==0 or a==1,'Native town-tree alpha must remain pixel-exact')
  if a>0 then
   opaque=opaque+1;left=math.min(left,x);right=math.max(right,x);top=math.min(top,y);bottom=math.max(bottom,y)
  else transparent=transparent+1 end
  local half=assets[y<16 and'top.png'or'bottom.png'].image
  equalPixel(whole,x,y,half,x,y%16,'Town-tree halves do not reconstruct the whole16x32 artwork')
 end end
 check(opaque>0 and transparent>0 and bottom-top+1>16,'Town tree must retain a visible complete two-cell silhouette')
 check(opaque==provenance.opaque_source_pixels_retained,'Town-tree opaque count differs from the native-source audit')
 -- Every source field coordinate cleared by the outside-connected mask must
 -- remain transparent. The independent authoring audit establishes which
 -- source pixels belong to that mask and preserves every other source pixel.
 local fieldMask=assert(provenance.outside_connected_field_mask or provenance.omitted_field_coordinates,
  'Town-tree provenance must record its outside-connected field mask')
 check(#fieldMask>0,'Native field-removal mask is empty')
 for _,point in ipairs(fieldMask)do
  check(type(point[1])=='number'and type(point[2])=='number'and point[1]>=0 and point[1]<16 and point[2]>=0 and point[2]<32,
   'Native field mask has an invalid coordinate')
  local _,_,_,a=whole:getPixel(point[1],point[2]);check(a==0,'Outside-connected source field remains baked into the town tree')
 end
 report.source_art={dimensions={16,32},visible_alpha_bounds={left,top,right+1,bottom+1},
  opaque_pixels=opaque,transparent_pixels=transparent,outside_connected_field_pixels_checked=#fieldMask,
  halves_reconstruct_whole_exactly=true,source_pair={tileset='082d4a94_082d4dc4',top=696,bottom=552},
  files={whole=assets['whole.png'].hash,top=assets['top.png'].hash,bottom=assets['bottom.png'].hash}}
 local Mapping=assert(load(assert(read(MOD..'/lib/mapping.lua'))))()
 local rowFiles={'mappings/gen2_outdoor.lua','mappings/gen2_outdoor_extended.lua','mappings/johto_shared_finish.lua'}
 local byGame={gold={},silver={},crystal={}}
 local targetRows=0
 report.mapping_files={}
 for _,file in ipairs(rowFiles)do
  local count=0
  for _,row in ipairs(mappingRows(file))do
   if byGame[row.game]and(row.role=='dense_conifer_crown'or row.role=='dense_conifer_trunk')then
    local valid,why=Mapping.validate(row);check(valid,tostring(why))
    local name=row.role=='dense_conifer_crown'and'top.png'or'bottom.png'
    check(row.kind=='third_party'and row.asset==folder..name and row.assetFileHash==assets[name].hash,
     'Town-tree row does not use the correct checked native half')
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
 report.target_rows=targetRows
 report.totals={map_variants=0,accepted_target_rows=0,crown_cells=0,trunk_cells=0,
  complete_tree_pairs=0,independent_tree_pixels=0,native_gpu_tree_pixels=0,decorative_overlay_pixels=0,checked_gpu_pixels=0}
 local compositionCache={}
 local function expectedTile(row)
  local key=row.asset..tableString(row.base)
  if not compositionCache[key]then compositionCache[key]=nativeComposition(row)end
  return compositionCache[key]
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
    independent_tree_pixels=0,native_gpu_tree_pixels=0,decorative_overlay_pixels=0}
   f.checked_gpu_pixels=verifyCoveredPixels(def,art,after,game..' '..id..' native two-cell trees')
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
     cells[key]={x=cx,y=cy,role=row.role}
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
   f.collision_after=snapshot(map,2);f.events_after=eventSnapshot(map)
   check(f.collision_after==mechanics and f.events_after==events,'Town-tree artwork modified source collision/events or interactions')
   f.source_collision_events_unchanged=true
   mod.exports.dispose();world.mapImages={};world.animCells={};world.mapImage=world:imageFor(map.id)
   check(drawWorld2(world):getString()==native:getString(),'Town-tree cleanup failed to restore the original native background')
   f.cleanup_restored_native=true
   for _,key in ipairs({'crown_cells','trunk_cells','complete_tree_pairs','independent_tree_pixels','native_gpu_tree_pixels','decorative_overlay_pixels','checked_gpu_pixels'})do
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
        output = Path(__file__).resolve().parents[2] / ".work/tileshift-v0292-town-gpu"
        sys.argv.extend(["--output", str(output)])
    return validate_gpu.main()


if __name__ == "__main__":
    raise SystemExit(main())
