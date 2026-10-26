"""Audit actual TileShift main/Session coverage for every Gen1/Gen2 map.

Runs in the same private native LOVE process as validate_gpu. Imported source
maps, neutral donors and real Composition/Session code are used; maps are not
GPU-rasterized. Initial used cell coverage resolves actual position variants.
"""
from pathlib import Path
import sys
import validate_gpu


COVERAGE = r"""
 report.type='authoritative main/Session all-map coverage'
 report.limits='Actual main-listed modules, neutral Donor/Composition and real Session. No map GPU raster, actors, gameplay or save writes. Coverage is reviewed art available after native lighting gates permit replacement; unlit maps retain native visibility.'
 report.games={};report.maps={};report.tilesets={};report.modules={}
 report.totals={maps=0,source_cells=0,replaced_cells=0,remaining_cells=0,complete_maps=0,
  accepted_decodes=0,rejected_decodes=0,positioned_source_cells=0}
 local checkedModules={}
 for _,game in ipairs({'red','blue','yellow','gold','silver','crystal'})do
  local generation=(game=='red'or game=='blue'or game=='yellow')and 1 or 2
  local mod=startMod(game,generation)
  local state=mod.exports.state
  for path,info in pairs(mod.auditReads or {})do if not checkedModules[path]then
   local rows=assert(load(assert(read(MOD..'/'..path)),'@coverage/'..path))()
   report.modules[#report.modules+1]={path=path,rows=#rows,sha256=info.sha256,bytes=info.bytes}
   checkedModules[path]=true
  end end
  local maps=generated(game,'maps');local names={}
  for id,def in pairs(maps)do
   if type(id)=='string'and type(def)=='table'and type(def.tileset)=='string'
    and type(def.width)=='number'and def.width>0 and type(def.height)=='number'and def.height>0
    and type(def.blocks)=='table'then names[#names+1]=id end
  end
  table.sort(names,function(a,b)
   local x,y=maps[a].tileset,maps[b].tileset
   if x~=y then return x<y end;return a<b
  end)
  local summary={game=game,maps=0,source_cells=0,replaced_cells=0,remaining_cells=0,complete_maps=0,
   accepted_decodes=0,rejected_decodes=0,positioned_source_cells=0}
  local previousTileset,batch=nil,0
  for _,id in ipairs(names)do
   local original=maps[id]
   -- Cache batches bound ImageData memory while preserving the actual main
   -- state, indexed modules, neutral decoder and published Session behavior.
   if previousTileset and(previousTileset~=original.tileset or batch>=25)then
    state:select('original');state:select('gen3');collectgarbage('collect');batch=0
   end
   previousTileset=original.tileset;batch=batch+1
   local def={};for key,value in pairs(original)do def[key]=value end;def.id=id
   check(#def.blocks==def.width*def.height,'Incomplete source map block array: '..game..'/'..id)
   local unchanged=hash(tableString(def))
   local accepted,rejected=state.accepted,state.rejected
   local art=state:replacements(game,def.tileset,def)or{}
   local c=coverage(def,art)
   local positions=0
   for index,blockId in ipairs(def.blocks)do
    local bx,by=(index-1)%def.width,math.floor((index-1)/def.width)
    local block=artAt(art,blockId,bx,by)
    if block and block~=art[blockId]then
     for q=0,3 do if not block.coverage or block.coverage[q]then positions=positions+1 end end
    end
   end
   check(unchanged==hash(tableString(def)),'Session mutated source map definition: '..game..'/'..id)
   local entry={game=game,map=id,tileset=def.tileset,width_blocks=def.width,height_blocks=def.height,
    source_cells=c.visible_cells,replaced_cells=c.replaced_occurrences,remaining_cells=c.preserved_native_occurrences,
    unique_mappings_used=c.unique_mappings_used,positioned_source_cells=positions,
    accepted_decodes=state.accepted-accepted,rejected_decodes=state.rejected-rejected,
    original_palette=def.palette,source_definition_sha256=unchanged,source_definition_unchanged=true}
   report.maps[#report.maps+1]=entry
   local tskey=game..':'..def.tileset
   local ts=report.tilesets[tskey]
   if not ts then
    ts={game=game,tileset=def.tileset,maps=0,source_cells=0,replaced_cells=0,remaining_cells=0,complete_maps=0,
     accepted_decodes=0,rejected_decodes=0,positioned_source_cells=0};report.tilesets[tskey]=ts
   end
   for _,destination in ipairs({summary,ts,report.totals})do
    destination.maps=destination.maps+1
    if entry.remaining_cells==0 then destination.complete_maps=destination.complete_maps+1 end
    for _,key in ipairs({'source_cells','replaced_cells','remaining_cells','accepted_decodes','rejected_decodes','positioned_source_cells'})do
     destination[key]=destination[key]+entry[key]
    end
   end
   if summary.maps%25==0 then
    write('progress.json',Json.encode({game=game,maps_checked=summary.maps,maps_in_game=#names,
     total_maps_checked=report.totals.maps,total_replaced=report.totals.replaced_cells,total_remaining=report.totals.remaining_cells}))
   end
  end
  summary.fraction=summary.replaced_cells/summary.source_cells
  report.games[#report.games+1]=summary
  mod.exports.dispose();state:select('original');mod=nil;state=nil;collectgarbage('collect')
  write('progress.json',Json.encode({completed_games=#report.games,total_maps_checked=report.totals.maps,
   total_replaced=report.totals.replaced_cells,total_remaining=report.totals.remaining_cells}))
 end
 table.sort(report.modules,function(a,b)return a.path<b.path end)
 report.remaining_maps={}
 for _,entry in ipairs(report.maps)do if entry.remaining_cells>0 then report.remaining_maps[#report.remaining_maps+1]=entry end end
 table.sort(report.remaining_maps,function(a,b)
  if a.remaining_cells~=b.remaining_cells then return a.remaining_cells>b.remaining_cells end
  return a.game..':'..a.map<b.game..':'..b.map
 end)
 report.totals.fraction=report.totals.replaced_cells/report.totals.source_cells
 report.status=report.totals.rejected_decodes==0 and #report.warnings==0 and 'passed'or'failed'
 if report.status~='passed'then report.error='Actual Session rejected source/donor rows; inspect map rejection deltas and warnings.'end
 write('report.json',Json.encode(report))
end
"""


def main() -> int:
    base = validate_gpu.LUA
    prefix = base[:base.index(" -- Native Gen1 TileRenderer on real Red Pallet Town.")]
    old = "function mod:read(path)return read(MOD..'/'..path)end"
    new = """function mod:read(path)
 local bytes=read(MOD..'/'..path)
 if bytes and path:match('^mappings/.*%.lua$')then
  self.auditReads=self.auditReads or {};self.auditReads[path]={bytes=#bytes,sha256=hash(bytes)}
 end
 return bytes
end"""
    assert old in prefix
    prefix = prefix.replace(old, new)
    validate_gpu.LUA = prefix + COVERAGE + base[base.index("\nfunction love.load()") :]
    if "--output" not in sys.argv:
        sys.argv.extend(["--output", str(Path(__file__).resolve().parents[2] / ".work/tileshift-runtime-coverage")])
    return validate_gpu.main()


if __name__ == "__main__":
    raise SystemExit(main())
