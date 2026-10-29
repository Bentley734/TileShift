"""Native Gen3 FieldView checks for reviewed Gen1/Gen2 theme counterparts.

By default all 56 scenes run. Optional --games and --maps filters select a
subset; --maps uses exact known native map suffixes, without RU_/SA_/EM_/FR_.
--require-complete-map checks every selected instance in both GB themes.
"""
import argparse
import json
from pathlib import Path
import sys
import validate_gpu

GAMES = ('firered', 'leafgreen', 'ruby', 'sapphire', 'emerald')
KANTO_MAPS = ('PALLET_TOWN', 'ROUTE_1', 'VIRIDIAN_CITY', 'MT_MOON_1F', 'PLAYERS_HOUSE_1F')
HOENN_MAPS = ('LITTLEROOT_TOWN', 'OLDALE_TOWN', 'ROUTE101', 'ROUTE102',
              'LITTLEROOT_TOWN_BRENDANS_HOUSE_1F', 'LITTLEROOT_TOWN_PROFESSOR_BIRCHS_LAB')
MAP_SUFFIXES = tuple(dict.fromkeys(KANTO_MAPS + HOENN_MAPS))
PREFIXES = {'firered': 'FR_', 'leafgreen': 'FR_', 'ruby': 'RU_', 'sapphire': 'SA_', 'emerald': 'EM_'}


def selection(games, maps=None, required=None):
    """Resolve exact fixture IDs before launching the native probe."""
    selected_maps = set(maps or MAP_SUFFIXES)
    required_maps = set(required or ())
    fixtures, matched, complete = [], set(), {}
    for game in dict.fromkeys(games):
        suffixes = KANTO_MAPS if game in ('firered', 'leafgreen') else HOENN_MAPS
        ids = []
        for suffix in suffixes:
            if suffix in selected_maps:
                map_id = PREFIXES[game] + suffix
                ids.append(map_id)
                matched.add(suffix)
                if suffix in required_maps:
                    complete[map_id] = True
        if ids:
            fixtures.append({'game': game, 'maps': ids})
    if maps and selected_maps - matched:
        raise ValueError('Map filters have no fixture in the selected games: ' + ', '.join(sorted(selected_maps - matched)))
    if required_maps - matched:
        raise ValueError('Required complete maps are not selected: ' + ', '.join(sorted(required_maps - matched)))
    if not fixtures:
        raise ValueError('The filters selected no native map fixtures')
    return {'fixtures': fixtures, 'require_complete': complete,
            'expected_scenes': sum(len(item['maps']) for item in fixtures) * 2,
            'games': list(dict.fromkeys(games)), 'map_suffixes': list(maps or ()),
            'require_complete_map_suffixes': list(required or ())}


BODY = r"""
 local Native=require('src.core.game3.tileset_native')
 local Anim=require('src.core.game3.tileset_anim')
 local Versions=require('src.import.gba.versions')
 local CachePaths=require('src.core.game3.cache_paths')
 local Dataset=require('src.core.game3.dataset')
 local Map=require('src.core.game3.map')
 local View=require('src.core.game3.field_view')
 local selection=Json.decode(@SELECTION@)
 report.selection=selection
 report.theme='reverse';report.limits='Actual Gen3 FieldView backgrounds and source-layout/event snapshots. Oldale foreground checks use a synthetic magenta marker at the native normal-actor boundary, not an interactive actor. Native actor/field-effect art is unchanged; no saves or interactive playthrough.'
 for _,fixture in ipairs(selection.fixtures)do
  local game=fixture.game
  GV.set(game);assetGame=game;clock=0
  local cache={read=function(_,path)return cacheRead(game..'/'..path)end,exists=function(self,path)return self:read(path)~=nil end}
  Versions.selectCache(game,cache);CachePaths.reset();Dataset.cacheRootOverride=nil;Dataset.mountExtractRoots();Native.install(cache)
  local maps=Dataset.buildMaps()
  local ids=fixture.maps
  local mod=startMod(game,3)
  mod.save.set=function()end -- Only this private in-memory option fixture.
  for _,id in ipairs(ids)do
   local def=assert(maps[id],'Native map unavailable '..id);Dataset.attachMidLayouts({[id]=def},cache)
   local layout=assert(def.midLayout);local pair=assert(def.pair or layout.pair)
   local ts=assert(Native.get(pair),'Native atlas unavailable '..game..'/'..pair);Anim.setVisiblePairs({[pair]=true});Anim.enterMap(pair,false)
   local width,height=layout.width*16,layout.height*16
   local host={data={maps=maps},save={position={map=id},flags={},vars={},options={}},options={},world={map={id=id},player={px=width/2-8,py=height/2-8,facing='down'}}}
   Map._def=def;Map._currentDef=def;Map.current=id;Map.neighborList={};Map.neighbors={}
   View.invalidate();View._flashMapId=id;View.setFlashLevel(0)
   mod.game=host;clock=0;assert(mod.exports.select('original'))
   local function draw(opts)return capture(width,height,function()View.draw(host,width,height,opts or{skipActors=true})end)end
   local before=draw();local immutable=hash(tableString(layout.cells)..tableString(def.warps)..tableString(def.objects)..tableString(def.coordEvents))
   local oldale=id:match('^[A-Z][A-Z]_OLDALE_TOWN$')~=nil
   local entranceAnchors
   if oldale then
    check(type(def.warps)=='table'and #def.warps==4,'Oldale must expose its four native building entrances')
    entranceAnchors={}
    for i,warp in ipairs(def.warps)do
     check(type(warp.x)=='number'and type(warp.y)=='number','Oldale entrance coordinates unavailable')
     entranceAnchors[i]={index=i,x=warp.x,y=warp.y,source=tableString(warp)}
    end
   end
   local function verify(frame,art,theme)
    local covered,checked,used=0,0,{}
    for y=0,layout.height-1 do for x=0,layout.width-1 do
     local mid=layout:midAt(x,y);local row=art[mid]
     if row then
      covered=covered+1
      used[mid]=true
      local index=row.frames and(math.floor((clock+(row.offset or 0))/(row.period or 1))%#row.frames+1)or 1
      local image=row.frames and row.frames[index].under or row.under
      for dy=0,15 do for dx=0,15 do
       equalPixel(frame,x*16+dx,y*16+dy,image,dx,dy,'Actual FieldView counterpart pixels differ')
       if theme=='gen1'then
        local r,g,b,a=image:getPixel(dx,dy)
        local shade=math.floor(r*255+.5)
        check(r==g and g==b and(a==0 or a==1)and(shade==0 or shade==85 or shade==170 or shade==255),'Gen1 counterpart lost four-shade monochrome/binary alpha')
       end
       checked=checked+1
      end end
     else
      for dy=0,15 do for dx=0,15 do
       equalPixel(frame,x*16+dx,y*16+dy,before,x*16+dx,y*16+dy,'Unreviewed source cell changed')
      end end
     end
    end end
    local unique=0;for _ in pairs(used)do unique=unique+1 end
    return covered,checked,unique
   end
   local function oldaleForeground(art,background)
    if not oldale then return nil end
    local samples={}
    for _,roi in ipairs({{name='pokemon_center',x0=5,y0=13,x1=8,y1=16},
      {name='poke_mart',x0=13,y0=3,x1=16,y1=6}})do
     local opaque,corner
     for x=roi.x0,roi.x1 do
      local mid=layout:midAt(x,roi.y0);local row=assert(art[mid],'Oldale roof has no reviewed replacement')
      check(row.over~=nil,'Oldale roof has no explicit foreground plane')
      for dy=0,15 do for dx=0,15 do
       local _,_,_,a=row.over:getPixel(dx,dy)
       if not opaque and a==1 then opaque={x=x*16+dx,y=roi.y0*16+dy,mid=mid}end
       local outerCorner=(x==roi.x0 and dx<8)or(x==roi.x1 and dx>=8)
       if not corner and outerCorner and dy<8 and a==0 then
        corner={x=x*16+dx,y=roi.y0*16+dy,mid=mid}
       end
      end end
     end
     check(opaque~=nil,'Oldale '..roi.name..' upper roof row needs an opaque foreground sample')
     check(corner~=nil,'Oldale '..roi.name..' upper roof corner needs a transparent sample')
     samples[#samples+1]={building=roi.name,roi=roi,opaque=opaque,transparent_corner=corner}
    end
    local callbacks=0
    local marked=draw({skipActors=false,endUnderActors=function()
     callbacks=callbacks+1
     G.setColor(1,0,1,1)
     for _,sample in ipairs(samples)do
      local roi=sample.roi
      G.rectangle('fill',roi.x0*16,roi.y0*16,(roi.x1-roi.x0+1)*16,(roi.y1-roi.y0+1)*16)
     end
     G.setColor(1,1,1,1)
    end})
    check(callbacks==1,'Oldale synthetic marker did not run at the native normal-actor boundary')
    local magenta=nativeData(1,1);magenta:setPixel(0,0,1,0,1,1)
    for _,sample in ipairs(samples)do
     local opaque,corner=sample.opaque,sample.transparent_corner
     equalPixel(marked,opaque.x,opaque.y,background,opaque.x,opaque.y,
      'Oldale opaque '..sample.building..' roof failed to cover the normal-priority marker')
     equalPixel(marked,corner.x,corner.y,magenta,0,0,
      'Oldale transparent '..sample.building..' roof corner hid the normal-priority marker')
     sample.opaque_hides_marker=true;sample.transparent_corner_exposes_marker=true
    end
    check(#def.warps==#entranceAnchors,'Oldale entrance count changed')
    for _,anchor in ipairs(entranceAnchors)do
     local warp=def.warps[anchor.index]
     check(warp.x==anchor.x and warp.y==anchor.y and tableString(warp)==anchor.source,
      'Oldale native entrance anchor or warp destination changed')
    end
    return {kind='synthetic magenta marker; not an interactive actor',
     pipeline='FieldView.draw endUnderActors callback before native drawNativeOverTiles',
     native_callback_count=callbacks,buildings=samples,entrance_anchors=entranceAnchors,
     entrance_anchors_unchanged=true,
     image=encodePng(marked,game..'-'..id..'-'..mod.exports.state.style..'-foreground-marker-gpu.png')}
   end
   for _,theme in ipairs({'gen1','gen2'})do
    assert(mod.exports.select(theme));clock=0
    local after=draw();local art=mod.exports.state:replacements(game,pair)
    local covered,checked,unique=verify(after,art,theme)
    local total=layout.width*layout.height
    if id:find('PALLET_TOWN',1,true)or id:find('LITTLEROOT_TOWN',1,true)and not id:find('_HOUSE_',1,true)and not id:find('_LAB',1,true)then
     check(covered==total,'Starter town is not fully retiled')
    end
    if selection.require_complete[id]then
     check(covered==total,'Required map is not fully retiled: '..game..'/'..id..'/'..theme..' ('..covered..'/'..total..')')
    end
    local animations={}
    for _,category in ipairs({'water','flowers'})do
     local sequence
     for _,row in pairs(art)do if row.frames and row.category==category then sequence=row;break end end
     if sequence then
      for frame=0,#sequence.frames-1 do clock=frame*sequence.period+.00001;verify(draw(),art,theme)end
      animations[category]={frames=#sequence.frames,period=sequence.period,all_native_frames_verified=true}
     end
    end
    clock=0
    for _,key in ipairs({'speed_water','speed_flowers'})do mod._probeEvents:emit('mod.options_changed',{mod='tileshift',key=key,value=1})end
    local frozen=draw();clock=9.37;check(draw():getString()==frozen:getString(),'Off animation must retain its first frame')
    for _,key in ipairs({'speed_water','speed_flowers'})do mod._probeEvents:emit('mod.options_changed',{mod='tileshift',key=key,value=3})end
    clock=0;after=draw()
    check(mod.exports.state.rejected==0,'Reverse theme rejected reviewed source/donor rows')
    check(hash(tableString(layout.cells)..tableString(def.warps)..tableString(def.objects)..tableString(def.coordEvents))==immutable,'Reverse theme changed native source layout/events')
    local foreground=oldaleForeground(art,after)
    report.fixtures[#report.fixtures+1]={game=game,map=id,pair=pair,style=theme,
     before=encodePng(before,game..'-'..id..'-native-gpu.png'),after=encodePng(after,game..'-'..id..'-'..theme..'-gpu.png'),
     coverage={visible_cells=total,replaced_occurrences=covered,preserved_native_occurrences=total-covered,unique_mappings_used=unique,animation_frame=0,actors_rendered=false},
     checked_pixels=checked,animations=animations,foreground=foreground,actual_native_field_view=true,source_layout_and_events_unchanged=true}
    assert(mod.exports.select('original'));clock=0
    check(draw():getString()==before:getString(),'Reverse theme cleanup did not restore original FieldView pixels')
    write('progress.json',Json.encode({fixtures=#report.fixtures,game=game,map=id,theme=theme,covered=covered,total=total}))
   end
  end
  mod.exports.dispose()
 end
 check(#report.fixtures==selection.expected_scenes,'Selected native scenes were skipped')
 report.status='passed';write('report.json',Json.encode(report))
end
"""

def main():
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    parser.add_argument('--games', nargs='+', type=str.lower, choices=GAMES)
    parser.add_argument('--maps', nargs='+', type=str.upper, choices=MAP_SUFFIXES)
    parser.add_argument('--require-complete-map', nargs='+', type=str.upper, choices=MAP_SUFFIXES)
    args, remaining = parser.parse_known_args()
    try:
        selected = selection(args.games or GAMES, args.maps, args.require_complete_map)
    except ValueError as exc:
        parser.error(str(exc))
    sys.argv[1:] = remaining
    # Keep the common native-probe flags and their help in validate_gpu.main.
    # Its description also documents the additional filters consumed here.
    validate_gpu.__doc__ = (__doc__ + '\nOptional filter flags: --games GAME [GAME ...]; '
                           '--maps SUFFIX [SUFFIX ...]; '
                           '--require-complete-map SUFFIX [SUFFIX ...]. '
                           'Supported games: ' + ', '.join(GAMES) + '. '
                           'Known map suffixes: ' + ', '.join(MAP_SUFFIXES) + '.')
    base=validate_gpu.LUA
    prefix=base[:base.index(' -- Native Gen1 TileRenderer on real Red Pallet Town.')]
    body=BODY.replace('@SELECTION@',json.dumps(json.dumps(selected,separators=(',',':'))))
    validate_gpu.LUA=prefix+body+base[base.index('\nfunction love.load()'):]
    if '--output' not in sys.argv:
        sys.argv.extend(['--output',str(Path(__file__).resolve().parents[2]/'.work/tileshift-reverse-gpu')])
    return validate_gpu.main()

if __name__=='__main__':
    raise SystemExit(main())
