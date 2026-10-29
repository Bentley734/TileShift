"""Native Gen3 FieldView checks for reviewed Gen1/Gen2 theme counterparts."""
from pathlib import Path
import sys
import validate_gpu

BODY = r"""
 local Native=require('src.core.game3.tileset_native')
 local Anim=require('src.core.game3.tileset_anim')
 local Versions=require('src.import.gba.versions')
 local CachePaths=require('src.core.game3.cache_paths')
 local Dataset=require('src.core.game3.dataset')
 local Map=require('src.core.game3.map')
 local View=require('src.core.game3.field_view')
 report.theme='reverse';report.limits='Actual Gen3 FieldView backgrounds and source-layout/event snapshots; actors and field effects retain native Gen3 art. No saves or interactive playthrough.'
 for _,game in ipairs({'firered','leafgreen','ruby','sapphire','emerald'})do
  GV.set(game);assetGame=game;clock=0
  local cache={read=function(_,path)return cacheRead(game..'/'..path)end,exists=function(self,path)return self:read(path)~=nil end}
  Versions.selectCache(game,cache);CachePaths.reset();Dataset.cacheRootOverride=nil;Dataset.mountExtractRoots();Native.install(cache)
  local maps=Dataset.buildMaps()
  local prefix=game=='ruby'and'RU_'or game=='sapphire'and'SA_'or'EM_'
  local ids=(game=='firered'or game=='leafgreen')and{'FR_PALLET_TOWN','FR_ROUTE_1','FR_VIRIDIAN_CITY','FR_MT_MOON_1F','FR_PLAYERS_HOUSE_1F'}or
   {prefix..'LITTLEROOT_TOWN',prefix..'OLDALE_TOWN',prefix..'ROUTE101',prefix..'ROUTE102',prefix..'LITTLEROOT_TOWN_BRENDANS_HOUSE_1F',prefix..'LITTLEROOT_TOWN_PROFESSOR_BIRCHS_LAB'}
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
   for _,theme in ipairs({'gen1','gen2'})do
    assert(mod.exports.select(theme));clock=0
    local after=draw();local art=mod.exports.state:replacements(game,pair)
    local covered,checked,unique=verify(after,art,theme)
    local total=layout.width*layout.height
    if id:find('PALLET_TOWN',1,true)or id:find('LITTLEROOT_TOWN',1,true)and not id:find('_HOUSE_',1,true)and not id:find('_LAB',1,true)then
     check(covered==total,'Starter town is not fully retiled')
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
    report.fixtures[#report.fixtures+1]={game=game,map=id,pair=pair,style=theme,
     before=encodePng(before,game..'-'..id..'-native-gpu.png'),after=encodePng(after,game..'-'..id..'-'..theme..'-gpu.png'),
     coverage={visible_cells=total,replaced_occurrences=covered,preserved_native_occurrences=total-covered,unique_mappings_used=unique,animation_frame=0,actors_rendered=false},
     checked_pixels=checked,animations=animations,actual_native_field_view=true,source_layout_and_events_unchanged=true}
    assert(mod.exports.select('original'));clock=0
    check(draw():getString()==before:getString(),'Reverse theme cleanup did not restore original FieldView pixels')
    write('progress.json',Json.encode({fixtures=#report.fixtures,game=game,map=id,theme=theme,covered=covered,total=total}))
   end
  end
  mod.exports.dispose()
 end
 report.status='passed';write('report.json',Json.encode(report))
end
"""

def main():
    base=validate_gpu.LUA
    prefix=base[:base.index(' -- Native Gen1 TileRenderer on real Red Pallet Town.')]
    validate_gpu.LUA=prefix+BODY+base[base.index('\nfunction love.load()'):]
    if '--output' not in sys.argv:
        sys.argv.extend(['--output',str(Path(__file__).resolve().parents[2]/'.work/tileshift-reverse-gpu')])
    return validate_gpu.main()

if __name__=='__main__':
    raise SystemExit(main())
