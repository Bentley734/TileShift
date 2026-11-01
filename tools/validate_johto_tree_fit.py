"""Check compact Johto Big Trees in the real Gen 2 background renderer.

This probe reads production artwork and imported maps without changing either.
It covers every GSC map family that uses Big Trees, all three numbered choices,
Default/Mixed, sway phases, the Off speed and a fresh background-cache rebuild.
Bounding boxes check visible size only; source-pixel/canopy audits are separate.
"""
import sys
from pathlib import Path

import validate_gpu


FOCUSED = r"""
 report.type='focused compact Johto Big Trees native GPU validation'
 report.limits='Actual Gen2 World backgrounds and source collision/event snapshots. No actors or interactive gameplay. PNG bounds establish visible size, not source-canopy completeness.'
 local manifest=Json.decode(assert(read(MOD..'/manifest.json')))
 report.version=manifest.version
 local catalog=probeFloraCatalog('crystal')
 check(#catalog.big_trees==3,'Expected three compact native Johto Big Trees choices')
 report.source_art={}
 for _,entry in ipairs(catalog.big_trees)do
  local bytes=assert(read(MOD..'/'..entry.asset))
  check(hash(bytes)==entry.hash,'Big Trees PNG hash differs from the active catalog')
  local image=love.image.newImageData(love.filesystem.newFileData(bytes,'tree.png'))
  local width,height=image:getDimensions()
  check(width==32 and height==32 and entry.size==32,'Big Trees must retain the32x32 source footprint')
  local left,top,right,bottom,opaque=32,32,-1,-1,0
  for y=0,31 do for x=0,31 do
   local _,_,_,a=image:getPixel(x,y)
   check(a==0 or a==1,'Compact tree alpha must remain pixel-exact')
   if a>0 then
    left=math.min(left,x);top=math.min(top,y);right=math.max(right,x);bottom=math.max(bottom,y);opaque=opaque+1
   end
  end end
  check(right-left+1>=26 and bottom-top+1>=27,'Big Trees visible artwork is still undersized')
  for _,point in ipairs({{0,0},{31,0},{0,31},{31,31}})do
   local _,_,_,a=image:getPixel(point[1],point[2]);check(a==0,'Unused compact tree corners must remain transparent')
  end
  report.source_art[#report.source_art+1]={id=entry.id,asset=entry.asset,hash=entry.hash,
   dimensions={width,height},visible_alpha_bounds={left,top,right+1,bottom+1},opaque_pixels=opaque,
   all_four_corners_transparent=true,canopy_completeness='Separately audited against native source pixels; not inferred from bounds.'}
 end
 local treeRoles={dense_forest_tree_northwest=true,dense_forest_tree_northeast=true,
  dense_forest_tree_southwest=true,dense_forest_tree_southeast=true}
 local function treeCells(game,def)
  local selected,cells={},{}
  local function add(x,y)
   local key=x..':'..y
   if not selected[key]then selected[key]=true;cells[#cells+1]={x=x,y=y}end
  end
  for _,file in ipairs({'mappings/gen2_outdoor_extended.lua','mappings/johto_gyms_finish.lua','mappings/park.lua'})do
   for _,row in ipairs(mappingRows(file))do
    if row.game==game and row.map==def.id and(treeRoles[row.role]or row.role:match('^forest_whole_broadleaf_tree_[0-3]$'))then
     if row.x~=nil then add(row.x,row.y)
     else for index,id in ipairs(def.blocks)do if id==row.id then
      add((index-1)%def.width*2+row.quadrant%2,math.floor((index-1)/def.width)*2+math.floor(row.quadrant/2))
     end end end
    end
   end
  end
  check(#cells>0 and #cells%4==0,'Native map must exercise complete four-cell Big Trees')
  return cells
 end
 local function sameTreePixels(before,after,cells,label)
  local count=0
  for _,cell in ipairs(cells)do for y=0,15 do for x=0,15 do
   equalPixel(after,cell.x*16+x,cell.y*16+y,before,cell.x*16+x,cell.y*16+y,label)
   count=count+1
  end end end
  return count
 end
 report.customizations={map_variants=0,choice_scenes=0,animated_frames=0,revisit_checks=0,
  speed_off_checks=0,tree_speed_off_pixels=0,checked_gpu_pixels=0}
 for _,game in ipairs({'gold','silver','crystal'})do
  for _,id in ipairs({'ILEX_FOREST','AZALEA_GYM','NATIONAL_PARK','NATIONAL_PARK_BUG_CONTEST'})do
   GV.set(game);assetGame=game;clock=0
   local world,map,def=world2(game,id)
   world.mapImage=world:imageFor(map.id)
   local native=drawWorld2(world)
   local mechanics,events=snapshot(map,2),eventSnapshot(map)
   local mod=startMod(game,2,world)
   local function draw()return drawWorld2(world)end
   local function rebuild()
    mod.exports.state:invalidate()
    world.mapImages={};world.animCells={}
    world.mapImage=world:imageFor(map.id)
    return assert(mod.exports.state:replacements(game,def.tileset,def))
   end
   local cells=treeCells(game,def)
   local art=rebuild();local after=draw()
   check(mod.exports.state.rejected==0,'Compact Johto tree scene rejected reviewed art')
   local f={game=game,map=id,coverage=coverage(def,art),tree_cells=#cells,complete_tree_occurrences=#cells/4,
    before=encodePng(native,game..'-'..id..'-native-gpu.png'),
    after=encodePng(after,game..'-'..id..'-gen3-gpu.png'),choices={},
    collision_before=mechanics,events_before=events}
   local choices={'default','mixed'}
   for _,entry in ipairs(catalog.big_trees)do choices[#choices+1]=entry.id end
   for index,choice in ipairs(choices)do
    check(mod.exports.flora:select('big_trees',choice)~=nil,'Big Trees option selection failed')
    mod.exports.flora:speed('trees',1);clock=0
    local chosen=rebuild()
    local first=draw()
    local c={choice=choice,frame_zero=encodePng(first,game..'-'..id..'-big-'..choice..'-gpu.png'),
     phases={},checked_gpu_pixels=0}
    for _,time in ipairs({0,.36,.71,1.06})do
     clock=time;local frame=draw()
     local pixels=verifyCoveredPixels(def,chosen,frame,game..' '..id..' Big Trees '..choice..' phase '..time)
     c.phases[#c.phases+1]={time=time,checked_gpu_pixels=pixels,rgba_sha256=hash(frame:getString())}
     c.checked_gpu_pixels=c.checked_gpu_pixels+pixels
     report.customizations.animated_frames=report.customizations.animated_frames+1
    end
    -- Force a fresh map-image and animation-cell cache, rather than reusing a
    -- previously baked surface, to exercise stable option/area selection.
    clock=0;rebuild()
    check(draw():getString()==first:getString(),'Big Trees changed after a fresh map background rebuild')
    c.revisit_exact=true;report.customizations.revisit_checks=report.customizations.revisit_checks+1
    mod.exports.flora:speed('trees',0);clock=0
    local stopped=rebuild();local stoppedFirst=draw()
    for _,time in ipairs({.36,1.06,2.6})do
     clock=time;local frame=draw()
     local pixels=verifyCoveredPixels(def,stopped,frame,game..' '..id..' tree speed Off '..choice)
     c.checked_gpu_pixels=c.checked_gpu_pixels+pixels
     report.customizations.tree_speed_off_pixels=report.customizations.tree_speed_off_pixels+
      sameTreePixels(stoppedFirst,frame,cells,'Big Trees moved with animation speed Off')
     report.customizations.speed_off_checks=report.customizations.speed_off_checks+1
    end
    c.speed_off_exact=true
    check(snapshot(map,2)==mechanics and eventSnapshot(map)==events,'Tree choice changed source collision, events or interactions')
    check(mod.exports.state.rejected==0,'Tree customization rejected artwork')
    f.choices[#f.choices+1]=c
    report.customizations.checked_gpu_pixels=report.customizations.checked_gpu_pixels+c.checked_gpu_pixels
    report.customizations.choice_scenes=report.customizations.choice_scenes+1
   end
   mod.exports.flora:speed('trees',1);mod.exports.flora:select('big_trees','default');clock=0;rebuild()
   check(draw():getString()==after:getString(),'Default tree option failed to restore exact reviewed background')
   f.collision_after=snapshot(map,2);f.events_after=eventSnapshot(map)
   check(f.collision_after==mechanics and f.events_after==events,'Tree-fit fixture changed gameplay source data')
   f.source_collision_events_unchanged=true;f.default_restored_exactly=true
   mod.exports.dispose();world.mapImages={};world.animCells={};world.mapImage=world:imageFor(map.id)
   check(draw():getString()==native:getString(),'Tree-fit cleanup failed to restore original native background')
   f.cleanup_restored_native=true
   report.fixtures[#report.fixtures+1]=f
   report.customizations.map_variants=report.customizations.map_variants+1
   write('progress.json',Json.encode({fixtures=#report.fixtures,checks=report.checks,game=game,map=id}))
  end
 end
 check(#report.fixtures==12,'Tree-fit probe did not cover all twelve native map variants')
 check(report.customizations.choice_scenes==60 and report.customizations.animated_frames==240,
  'Tree-fit customization matrix is incomplete')
 check(#report.warnings==0,'Tree-fit probe reported warnings')
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
        output = Path(__file__).resolve().parents[2] / ".work/tileshift-v0291-tree-gpu"
        sys.argv.extend(["--output", str(output)])
    return validate_gpu.main()


if __name__ == "__main__":
    raise SystemExit(main())
