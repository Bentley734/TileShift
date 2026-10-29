"""Audit actual main/Session Gen1/Gen2 theme coverage over all native Gen3 maps.

Native Dataset.buildMaps and immutable16px layout packs supply source cells;
generated/maps.lua is deliberately not used. No map/actor GPU raster is needed.
"""
from pathlib import Path
import argparse
import json
import sys
import validate_gpu

AUDIT = r"""
 report.type='authoritative reverse main/Session native-map coverage'
 report.theme='gen1/gen2 on Gen3'
 report.limits='Actual main-listed mappings, Donor/Composition/Session and native Dataset.buildMaps. Count true map-body16px metatile occurrences; padding/borders excluded. No GPU map raster, actors, gameplay, persistence or import writes. Initial support is intentionally partial.'
 report.filters={games=auditGames,styles=auditStyles,pairs=auditPairs,require_complete=auditComplete}
 report.games={};report.maps={};report.modules={};report.manifests={};report.pairs={}
 report.totals={maps=0,source_maps=0,source_cells=0,replaced_cells=0,remaining_cells=0,complete_maps=0,
  accepted_decodes=0,rejected_decodes=0,styles=#auditStyles,game_theme_combinations=0}
 local Dataset=require('src.core.game3.dataset')
 local Native=require('src.core.game3.tileset_native')
 local NativePack=require('src.import.gba.native_pack')
 local Versions=require('src.import.gba.versions')
 local modules,moduleRows={},{}
 local function definitionHash(def)
  local data={};for key,value in pairs(def)do if key~='midLayout'then data[key]=value end end
  return hash(tableString(data))
 end
 for _,game in ipairs(auditGames)do
  GV.set(game);assetGame=game
  local cache={read=function(_,path)return cacheRead(game..'/'..path)end,
   exists=function(self,path)return self:read(path)~=nil end,write=function()error('Unexpected native coverage cache write')end}
  Versions.selectCache(game,cache);Dataset.mountExtractRoots();Native.install(cache)
  local manifestBytes=assert(cache:read('data/generated/gba/native/manifest.lua'),'Missing native manifest '..game)
  local manifest=assert(Serializer.decode(manifestBytes,{allowArray=true,allowComments=true,maxBytes=16*1024*1024,
   maxDepth=64,maxNodes=2000000,maxStringBytes=8*1024*1024,maxTableEntries=500000}))
  check(type(manifest.layouts)=='table','Native manifest has no layouts: '..game)
  local maps=Dataset.buildMaps();Dataset.attachMidLayouts(maps,cache)
  local names,grids={},{}
  for id,spec in pairs(manifest.layouts)do
   if not auditPairs or auditPairs[spec.pair]then
    check(type(maps[id])=='table','Dataset omitted a native manifest map: '..game..'/'..id)
    names[#names+1]=id
   end
  end
  table.sort(names,function(a,b)
   local x,y=manifest.layouts[a].pair,manifest.layouts[b].pair
   return x==y and a<b or x<y
  end)
  check(#names>0,'No native source maps matched the audit filters: '..game)
  report.totals.source_maps=report.totals.source_maps+#names
  report.manifests[#report.manifests+1]={game=game,sha256=hash(manifestBytes),maps=#names,source='native/manifest.lua + Dataset.buildMaps'}
  -- A single real mod instance indexes only the modules main actually loads.
  local mod=startMod(game,3);local state=mod.exports.state
  for path,info in pairs(mod.auditReads or{})do
   if not modules[path]then
    local rows=assert(load(assert(read(MOD..'/'..path)),'@reverse-coverage/'..path))()
    modules[path]=true;moduleRows[path]=rows
    report.modules[#report.modules+1]={path=path,rows=#rows,sha256=info.sha256,bytes=info.bytes}
   end
  end
  for _,style in ipairs(auditStyles)do
   check(mod.exports.select(style),'Actual main did not expose theme '..style)
   local summary={game=game,style=style,maps=0,source_cells=0,replaced_cells=0,remaining_cells=0,
    complete_maps=0,accepted_decodes=0,rejected_decodes=0}
   local currentPair,art,accepted,rejected,checkedPairs=nil,nil,0,0,{}
   local function loadPair(pair)
    state:select('original');state:select(style);collectgarbage('collect')
    art=state:replacements(game,pair)or{}
    accepted,rejected=state.accepted,state.rejected
    summary.accepted_decodes=summary.accepted_decodes+accepted
    summary.rejected_decodes=summary.rejected_decodes+rejected
    report.totals.accepted_decodes=report.totals.accepted_decodes+accepted
    report.totals.rejected_decodes=report.totals.rejected_decodes+rejected
    report.pairs[#report.pairs+1]={game=game,style=style,pair=pair,accepted_decodes=accepted,rejected_decodes=rejected}
    checkedPairs[pair]=true;currentPair=pair
   end
   for _,id in ipairs(names)do
    local spec,def=manifest.layouts[id],maps[id];local pair=spec.pair
    if currentPair~=pair then loadPair(pair)end
    local grid=grids[id]
    if not grid then
     local relative='data/generated/gba/native/'..assert(spec.file,'Native layout filename missing')
     local blob=assert(cache:read(relative),'Native layout missing '..game..'/'..relative)
     local decoded,why=NativePack.decodeMidLayout(blob)
     check(decoded~=nil,'Native layout decode failed '..game..'/'..id..': '..tostring(why))
     check(#decoded.cells==decoded.width*decoded.height,'Native source layout cell array is incomplete '..id)
     local w=decoded.trueWidth and decoded.trueWidth>0 and decoded.trueWidth or decoded.width
     local h=decoded.trueHeight and decoded.trueHeight>0 and decoded.trueHeight or decoded.height
     check(w>0 and h>0 and w<=decoded.width and h<=decoded.height,'Invalid native source dimensions '..id)
     -- Force the runtime lazy handle to confirm the same body dimensions.
     local layout=def.midLayout
     check(layout and layout.trueWidth==w and layout.trueHeight==h and def.width==w and def.height==h,
      'Runtime Dataset/layout dimensions disagree '..game..'/'..id)
     grid={decoded=decoded,width=w,height=h,sha256=hash(blob),definition_sha256=definitionHash(def)};grids[id]=grid
    end
    local d,w,h=grid.decoded,grid.width,grid.height
    local replaced,used=0,{}
    for y=0,h-1 do for x=0,w-1 do
     local cell=d.cells[y*d.width+x+1]
     check(cell and type(cell.mid)=='number'and type(cell.coll)=='number'and type(cell.elev)=='number',
      'Incomplete native source cell '..game..'/'..id)
     local replacement=art[cell.mid]
     if replacement and(replacement.under or replacement.over or replacement.mid)then replaced=replaced+1;used[cell.mid]=true end
    end end
    check(grid.definition_sha256==definitionHash(def),'Mod changed source map metadata '..game..'/'..id)
    local total=w*h;local unique=0;for _ in pairs(used)do unique=unique+1 end
    local entry={game=game,style=style,map=id,pair=pair,width_cells=w,height_cells=h,
     source_cells=total,replaced_cells=replaced,remaining_cells=total-replaced,unique_mappings_used=unique,
     layout_sha256=grid.sha256,source_definition_sha256=grid.definition_sha256,source_definition_unchanged=true}
    report.maps[#report.maps+1]=entry
    for _,target in ipairs({summary,report.totals})do
     target.maps=target.maps+1;target.source_cells=target.source_cells+total
     target.replaced_cells=target.replaced_cells+replaced;target.remaining_cells=target.remaining_cells+total-replaced
     if replaced==total then target.complete_maps=target.complete_maps+1 end
    end
    if summary.maps%25==0 then
     write('progress.json',Json.encode({game=game,style=style,maps_checked=summary.maps,maps_in_game=#names,
      total_map_theme_variants=report.totals.maps,total_replaced=report.totals.replaced_cells,total_remaining=report.totals.remaining_cells}))
    end
   end
   -- Validate even a main-listed pair that accidentally has no source map.
   -- Such rows cannot hide a missing/bad donor behind the map traversal.
   local extra={}
   for _,rows in pairs(moduleRows)do for _,row in ipairs(rows)do
    if row.game==game and row.style==style and(not auditPairs or auditPairs[row.tileset])and not checkedPairs[row.tileset]then extra[row.tileset]=true end
   end end
   local extraNames={};for pair in pairs(extra)do extraNames[#extraNames+1]=pair end;table.sort(extraNames)
   for _,pair in ipairs(extraNames)do loadPair(pair)end
   summary.fraction=summary.replaced_cells/summary.source_cells
   report.games[#report.games+1]=summary;report.totals.game_theme_combinations=report.totals.game_theme_combinations+1
   state:select('original');collectgarbage('collect')
  end
  mod.exports.dispose();mod=nil;state=nil;grids=nil;maps=nil;collectgarbage('collect')
  write('progress.json',Json.encode({completed_game_theme_combinations=#report.games,total_map_theme_variants=report.totals.maps,
   total_replaced=report.totals.replaced_cells,total_remaining=report.totals.remaining_cells}))
 end
 table.sort(report.modules,function(a,b)return a.path<b.path end)
 report.totals.fraction=report.totals.replaced_cells/report.totals.source_cells
 report.status=report.totals.rejected_decodes==0 and #report.warnings==0 and'passed'or'failed'
 if report.status~='passed'then report.error='Actual main/Session rejected reverse mappings; inspect pair diagnostics and warnings.'end
 if auditComplete and report.totals.remaining_cells>0 then report.status='failed';report.error='Requested complete native coverage still has unresolved cells.'end
 write('report.json',Json.encode(report))
end
"""


def main() -> int:
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--games',default='firered,leafgreen,ruby,sapphire,emerald')
    parser.add_argument('--styles',default='gen1,gen2')
    parser.add_argument('--pairs')
    parser.add_argument('--require-complete',action='store_true')
    args,remaining=parser.parse_known_args()
    games=args.games.split(',');styles=args.styles.split(',')
    assert games and len(set(games))==len(games)and all(x in ('firered','leafgreen','ruby','sapphire','emerald')for x in games)
    assert styles and len(set(styles))==len(styles)and all(x in ('gen1','gen2')for x in styles)
    pairs=args.pairs.split(',')if args.pairs else None
    assert pairs is None or all(x and x.replace('_','').isalnum()for x in pairs)
    sys.argv=[sys.argv[0],*remaining]
    base=validate_gpu.LUA
    prefix=base[:base.index(' -- Native Gen1 TileRenderer on real Red Pallet Town.')]
    old="function mod:read(path)return read(MOD..'/'..path)end"
    new="""function mod:read(path)
 local bytes=read(MOD..'/'..path)
 if bytes and path:match('^mappings/.*%.lua$')then
  self.auditReads=self.auditReads or{};self.auditReads[path]={bytes=#bytes,sha256=hash(bytes)}
 end
 return bytes
end"""
    assert old in prefix
    prefix=prefix.replace(old,new)
    settings='\n local auditGames={'+','.join(json.dumps(x)for x in games)+'}\n local auditStyles={'+','.join(json.dumps(x)for x in styles)+'}\n'
    settings+=' local auditPairs='+('nil'if pairs is None else'{'+','.join('['+json.dumps(x)+']=true'for x in pairs)+'}')+'\n'
    settings+=' local auditComplete='+str(args.require_complete).lower()+'\n'
    validate_gpu.LUA=prefix+settings+AUDIT+base[base.index('\nfunction love.load()'):]
    if '--output'not in sys.argv:
        sys.argv+=['--output',str(Path(__file__).resolve().parents[2]/'.work/tileshift-reverse-coverage')]
    return validate_gpu.main()

if __name__=='__main__':
    raise SystemExit(main())
