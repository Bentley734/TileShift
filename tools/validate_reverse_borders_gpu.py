"""Check isolated native Gen3 MAP-header borders under a classic theme.

The fixture deliberately samples the header pattern rather than connected-map
seams. Native definitions/connections are untouched; only the private Map graph
and its viewport cache are bounded to the current header. One mod index per
cartridge is reused for original, themed, and cleanup capture phases.
"""
import argparse
import json
from pathlib import Path
import sys
import validate_gpu

BODY=r"""
 local theme=@THEME@
 report.type='native Gen3 '..theme..' border viewport validation';report.theme='reverse'
 report.limits='Actual Dataset/Map/FieldView MAP-mode borders from imported native layout headers. Unreviewed border art must remain exactly native. No source layout, actor, event or save writes.'
 local scenes=Json.decode(@SCENES@)
 local expectedKeys=Json.decode(@KEYS@);local sampledKeys={}
 local Native=require('src.core.game3.tileset_native');local Anim=require('src.core.game3.tileset_anim')
 local Versions=require('src.import.gba.versions');local Paths=require('src.core.game3.cache_paths')
 local Dataset=require('src.core.game3.dataset');local Map=require('src.core.game3.map')
 local View=require('src.core.game3.field_view');local Void=require('src.core.game3.void_fill')
 local FieldPlan=require('src.core.game3.field_plan')
 local oldMode=Void.mode;Void.setMode('map')
 report.selection=scenes;report.header_keys_expected=#expectedKeys;report.mod_instances={}
 report.fixture_graph_traces={};report.phases={'original','gen2','cleanup'}
 report.totals={scenes=0,checked_pixels=0,replaced_border_pixels=0,native_border_pixels=0,warm_frames=0,mod_indices=0}
 local function immutable(c)
  return hash(tableString(c.layout.cells)..tableString(c.layout.borderMids)..tableString(c.def.warps)
   ..tableString(c.def.objects)..tableString(c.def.connections))
 end
 local function bind(c,isolate)
  local id,def,layout,host=c.id,c.def,c.layout,c.host
  Map._def=def;Map._currentDef=def;Map.current=id;Map.neighborList={};Map.neighbors={}
  if isolate then
   -- FieldView.draw calls refreshWorld. Matching its private reach cache keeps
   -- this header-only graph intact instead of rebuilding connected seams.
   Map.world={{id=id,def=def,ox=0,oy=0}};Map._worldRoot=id
   Map._worldReachW=c.width/16;Map._worldReachH=c.height/16
  else
   Map.world={};Map._worldRoot=nil;Map._worldReachW=nil;Map._worldReachH=nil
  end
  -- Invalidate the viewport plan, not the resident native tile atlases. The
  -- native renderer checks layout/pair/texture identity when rebuilding its
  -- batches; dropping every atlas here would recompose a pair per header.
  FieldPlan.invalidate();View._nativeDirty=true;View._voidFrom=nil;View._voidMapDef=nil
  View._flashMapId=id;View.setFlashLevel(0)
  Native.get(c.pair);Anim.setVisiblePairs({[c.pair]=true});Anim.enterMap(c.pair,false)
 end
 local function draw(c)
  return capture(c.width,c.height,function()View.draw(c.host,c.width,c.height,{skipActors=true})end)
 end
 local function isolated(c)
  check(Map._worldRoot==c.id and #Map.world==1 and Map.world[1].def==c.def
   and Map.world[1].ox==0 and Map.world[1].oy==0 and #Map.neighborList==0,
   'MAP-header fixture unexpectedly sampled a connected world')
 end
 local games,byGame={},{}
 for _,scene in ipairs(scenes)do
  if not byGame[scene.game]then games[#games+1]=scene.game;byGame[scene.game]={}end
  byGame[scene.game][#byGame[scene.game]+1]=scene
 end
 for _,game in ipairs(games)do
  GV.set(game);assetGame=game;clock=0
  local cache={read=function(_,p)return cacheRead(game..'/'..p)end,exists=function(self,p)return self:read(p)~=nil end}
  Versions.selectCache(game,cache);Paths.reset();Dataset.cacheRootOverride=nil;Dataset.mountExtractRoots();Native.install(cache)
  View.invalidate()
  local maps=Dataset.buildMaps();local contexts={}
  -- Capture every original before loading the mod. The expensive validated
  -- mapping index is then constructed exactly once for this cartridge.
  for _,scene in ipairs(byGame[game])do
   local id=scene.map;local def=assert(maps[id]);Dataset.attachMidLayouts({[id]=def},cache)
   local layout=assert(def.midLayout);local pair=assert(def.pair or layout.pair)
   local bw,bh=layout.borderWidth,layout.borderHeight;check(bw>0 and bh>0,'Native border pattern is empty')
   local width,height=(bw+2)*16,(bh+2)*16;local cx,cy=-bw*16,-bh*16
   local host={data={maps=maps},save={position={map=id},flags={},vars={},options={}},options={},
    world={map={id=id},player={px=cx+width/2-8,py=cy+height/2-8,facing='down'}}}
   local c={id=id,def=def,layout=layout,pair=pair,width=width,height=height,cx=cx,cy=cy,host=host}
   c.immutable=immutable(c);contexts[#contexts+1]=c
   if game=='ruby'and id=='RU_ROUTE121'then
    bind(c,false);local connected=draw(c)
    local mid,srcPair,isVoid=Map.worldMidAt(-bw,-bh,def)
    local r,g,b,a=connected:getPixel(0,0)
    c.graphTrace={game=game,map=id,header_mid=layout:midAt(-bw,-bh),header_pair=pair,
     connected_mid=mid,connected_pair=srcPair,connected_void=isVoid==true,connected_world_entries=#Map.world,
     connected_first_rgba={r,g,b,a}}
   end
   bind(c,true);c.before=draw(c);isolated(c)
   check(immutable(c)==c.immutable,'Original MAP capture changed source headers or connections')
   write('progress.json',Json.encode({phase='original',game=game,map=id,captured=#contexts,scenes=#report.fixtures}))
  end
  local mod=startMod(game,3);mod.save.set=function()end;mod.game=contexts[1].host
  assert(mod.exports.select(theme));report.totals.mod_indices=report.totals.mod_indices+1
  report.mod_instances[#report.mod_instances+1]={game=game,count=1,scenes=#contexts}
  for _,c in ipairs(contexts)do
  local id,def,layout,pair=c.id,c.def,c.layout,c.pair
  local width,height,cx,cy=c.width,c.height,c.cx,c.cy
  clock=0;mod.game=c.host;bind(c,true)
  local before=c.before;local after=draw(c);isolated(c)
  local art=mod.exports.state:replacements(game,pair)or{}
  check(View._nativeCamX==cx and View._nativeCamY==cy,'Native border camera differs from requested viewport')
  local checked,replaced,native=0,0,0;local used={}
  for y=0,height-1 do for x=0,width-1 do
   local wx,wy=math.floor((x+cx)/16),math.floor((y+cy)/16)
   if wx<0 or wy<0 then
    local mid=layout:midAt(wx,wy);local row=art[mid];used[mid]=true
    local actualMid,actualPair,isVoid=Map.worldMidAt(wx,wy,def)
    check(actualMid==mid and actualPair==pair and isVoid==true,'Header oracle sampled a connected-map cell')
    sampledKeys[game..':'..pair..':'..mid]=true
    if row then equalPixel(after,x,y,row.under,(x+cx)%16,(y+cy)%16,'Classic MAP border differs');replaced=replaced+1
    else equalPixel(after,x,y,before,x,y,'Unreviewed native MAP border changed');native=native+1 end
    checked=checked+1
   end
  end end
  for _,mid in ipairs(layout.borderMids)do check(used[mid],'Native border pattern was not completely sampled')end
  if @REQUIRE_COMPLETE@ then check(native==0,'Themed MAP border still contains native pixels')end
  local reads,accepted=importReads,mod.exports.state.accepted
  local warmStep=1/60
  for _,row in pairs(art)do if row.frames then warmStep=math.max(warmStep,row.period*1.125)end end
  for i=1,12 do clock=i*warmStep;draw(c)end
  isolated(c)
  check(importReads==reads and mod.exports.state.accepted==accepted,'Warm border viewport rebuilt mappings or reread imports')
  check(mod.exports.state.rejected==0 and c.immutable==immutable(c),
   'Border theme changed source mechanics or rejected a reviewed source')
  if c.graphTrace then
   local trace=c.graphTrace;local mid,srcPair,isVoid=Map.worldMidAt(-layout.borderWidth,-layout.borderHeight,def)
   local r,g,b,a=after:getPixel(0,0)
   trace.isolated_mid=mid;trace.isolated_pair=srcPair;trace.isolated_void=isVoid==true
   trace.isolated_world_entries=#Map.world;trace.themed_first_rgba={r,g,b,a}
   trace.native_header_only=true;report.fixture_graph_traces[#report.fixture_graph_traces+1]=trace
   trace.before=encodePng(before,game..'-'..id..'-header-native.png')
   trace.after=encodePng(after,game..'-'..id..'-header-'..theme..'.png')
  end
  c.fixture={game=game,map=id,pair=pair,checked_pixels=checked,replaced_border_pixels=replaced,
   native_border_pixels=native,source_headers_unchanged=true,source_connections_unchanged=true,
   isolated_header_graph=true,warm_frames=12,warm_clock_step=warmStep}
  report.fixtures[#report.fixtures+1]=c.fixture
  report.totals.scenes=report.totals.scenes+1;report.totals.checked_pixels=report.totals.checked_pixels+checked
  report.totals.replaced_border_pixels=report.totals.replaced_border_pixels+replaced
  report.totals.native_border_pixels=report.totals.native_border_pixels+native;report.totals.warm_frames=report.totals.warm_frames+12
  write('progress.json',Json.encode({phase=theme,scenes=#report.fixtures,game=game,map=id}))
  end
  mod.exports.dispose();clock=0
  for _,c in ipairs(contexts)do
   bind(c,true);check(draw(c):getString()==c.before:getString(),'Border cleanup did not restore native pixels')
   isolated(c);check(immutable(c)==c.immutable,'Border cleanup changed source headers or connections')
   c.fixture.cleanup_restored_native=true
   write('progress.json',Json.encode({phase='cleanup',scenes=#report.fixtures,game=game,map=c.id}))
  end
 end
 local sampled=0;for _ in pairs(sampledKeys)do sampled=sampled+1 end
 for _,key in ipairs(expectedKeys)do check(sampledKeys[key],'Selected native header key was not sampled: '..key)end
 check(sampled==#expectedKeys,'Native header key inventory differs from selected source inventory')
 report.header_keys_sampled=sampled
 Void.setMode(oldMode);check(#report.warnings==0,'Unexpected border mapping warning')
 report.status='passed';write('report.json',Json.encode(report))
end
"""


def main():
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--style',choices=('gen1','gen2'),default='gen2')
    parser.add_argument('--require-complete',action='store_true')
    parser.add_argument('--inventory',type=Path,required=True)
    parser.add_argument('--games',nargs='+',choices=('ruby','sapphire','emerald','firered','leafgreen'))
    parser.add_argument('--scenes-json',type=Path,help='Explicit {game,map} list for bounded native pilots')
    args,remaining=parser.parse_known_args();sys.argv[1:]=remaining
    data=json.loads(args.inventory.read_text());candidates={}
    for row in data['all_border']:
        if args.games and row['game']not in args.games:continue
        for map_id in row['maps']:candidates.setdefault((row['game'],map_id),set()).add((row['game'],row['pair'],row['id']))
    assert candidates,'No native border scenes selected'
    if args.scenes_json:
        scenes=json.loads(args.scenes_json.read_text())
        assert scenes and len({(row['game'],row['map'])for row in scenes})==len(scenes)
        assert all((row['game'],row['map'])in candidates for row in scenes),'Pilot scene is absent from the selected source inventory'
    else:
        missing=set().union(*candidates.values());scenes=[]
        while missing:
            key=max(candidates,key=lambda key:len(candidates[key]&missing))
            missing-=candidates[key];scenes.append(dict(game=key[0],map=key[1]))
    keys=sorted(':'.join(map(str,key))for key in set().union(*(candidates[row['game'],row['map']]for row in scenes)))
    source=validate_gpu.LUA
    prefix=source[:source.index(' -- Native Gen1 TileRenderer on real Red Pallet Town.')]
    body=BODY.replace('@SCENES@',json.dumps(json.dumps(scenes))).replace('@KEYS@',json.dumps(json.dumps(keys)))
    body=body.replace('@THEME@',json.dumps(args.style)).replace('@REQUIRE_COMPLETE@',str(args.require_complete).lower())
    validate_gpu.LUA=prefix+body+source[source.index('\nfunction love.load()'):]
    return validate_gpu.main()


if __name__=='__main__':raise SystemExit(main())
