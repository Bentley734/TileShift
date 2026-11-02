"""Render the completed Gen2 Kanto/shared rooms and interior cleanup natively.

Private imports and real World/Session adapters are used without gameplay or
save writes. Coverage, every visible replacement pixel, source mechanics,
warm-cache behavior and native cleanup are checked for every selected scene.
"""
import argparse
import json
import re
import sys
from pathlib import Path
import validate_gpu

MAPS=('PALLET_TOWN','VIRIDIAN_CITY','PEWTER_CITY','CERULEAN_CITY','LAVENDER_TOWN',
 'VERMILION_CITY','CELADON_CITY','FUCHSIA_CITY','SAFFRON_CITY','CINNABAR_ISLAND',
 'ROUTE_1','ROUTE_2','ROUTE_5','ROUTE_6','ROUTE_7','ROUTE_8','ROUTE_9','ROUTE_10_NORTH','ROUTE_10_SOUTH',
 'ROUTE_11','ROUTE_12','ROUTE_15','ROUTE_16','ROUTE_17','ROUTE_18','ROUTE_19','ROUTE_20','ROUTE_28',
 'ROUTE_22','ROUTE_23','ROUTE_24','ROUTE_25','ROUTE_26','ROUTE_27','MOUNT_MOON_SQUARE',
 'POKECENTER_2F','TIME_CAPSULE','TRADE_CENTER','COLOSSEUM','MOBILE_TRADE_ROOM','MOBILE_BATTLE_ROOM',
 'MOUNT_MOON','DIGLETTS_CAVE','ROCK_TUNNEL_B1F','VICTORY_ROAD',
 'CELADON_DEPT_STORE_1F','CELADON_DEPT_STORE_3F','CELADON_DEPT_STORE_ELEVATOR',
 'OAKS_LAB','REDS_HOUSE_1F','REDS_HOUSE_2F','COPYCATS_HOUSE_2F','POKEMON_FAN_CLUB','SOUL_HOUSE',
 'CELADON_MANSION_1F','CELADON_MANSION_2F','CELADON_MANSION_3F','CELADON_MANSION_ROOF',
 'CELADON_CAFE','CELADON_GAME_CORNER','CELADON_GAME_CORNER_PRIZE_ROOM',
 'VERMILION_GYM','FUCHSIA_GYM','SAFFRON_GYM','PEWTER_GYM','SEAFOAM_GYM','HALL_OF_FAME',
 'VERMILION_PORT','VERMILION_PORT_PASSAGE','FAST_SHIP_1F','FAST_SHIP_B1F',
 'FAST_SHIP_CABINS_NNW_NNE_NE','FAST_SHIP_CABINS_SE_SSE_CAPTAINS_CABIN','FAST_SHIP_CABINS_SW_SSW_NW',
 'SAFFRON_MAGNET_TRAIN_STATION','POWER_PLANT','SILPH_CO_1F','TRAINER_HOUSE_B1F','LAV_RADIO_TOWER_1F',
 'WILLS_ROOM','KOGAS_ROOM','BRUNOS_ROOM','KARENS_ROOM','LANCES_ROOM',
 'AZALEA_GYM','SPROUT_TOWER_3F','OLIVINE_LIGHTHOUSE_2F','OLIVINE_LIGHTHOUSE_6F',
 'RADIO_TOWER_1F','GOLDENROD_UNDERGROUND','POKECOM_CENTER_ADMIN_OFFICE_MOBILE')

BODY=r"""
 report.type='native Gen2 Kanto/shared rooms and interior cleanup GPU validation'
 report.limits='Actual source imports, World background bake/animation and real main/Session adapters. Exact visible pixel and source-mechanics snapshots; no interactive playthrough.'
 local selected=Json.decode(@SELECTION@)
 report.selection=selected;report.skipped_absent_maps={}
 report.totals={scenes=0,source_cells=0,replaced_cells=0,remaining_cells=0,checked_pixels=0,warm_frames=0}
 for _,game in ipairs(selected.games)do
  for _,id in ipairs(selected.maps)do
   local definition=generated(game,'maps')[id]
   if not definition then
    report.skipped_absent_maps[#report.skipped_absent_maps+1]={game=game,map=id}
   else
    GV.set(game);assetGame=game;clock=0
    local world,map,def=world2(game,id)
    world.mapImage=world:imageFor(map.id)
    local before=drawWorld2(world);local mechanics,events=snapshot(map,2),eventSnapshot(map)
    local mod=startMod(game,2,world);world.mapImage=world:imageFor(map.id)
    local art=assert(mod.exports.state:replacements(game,def.tileset,def))
    local after=drawWorld2(world);local c=coverage(def,art)
    check(mod.exports.state.rejected==0,'Reviewed row rejected: '..game..'/'..id)
    check(c.preserved_native_occurrences==0,'Selected complete scene retains native cells: '..game..'/'..id)
    local pixels=verifyCoveredPixels(def,art,after,game..'/'..id)
    check(before:getString()~=after:getString(),'Completed scene has no visible change: '..game..'/'..id)
    clock=17/60
    local animated=drawWorld2(world)
    pixels=pixels+verifyCoveredPixels(def,art,animated,game..'/'..id..' animation')
    local beforeWarm=importReads;local ownReads,assetReads,bakes=0,0,0
    local readOwn,pathOwn,bakeOwn=mod.read,mod.assets.path,world.bakeMapImage
    mod.read=function(self,...)ownReads=ownReads+1;return readOwn(self,...)end
    mod.assets.path=function(self,...)assetReads=assetReads+1;return pathOwn(self,...)end
    world.bakeMapImage=function(self,...)bakes=bakes+1;return bakeOwn(self,...)end
    local accepted=mod.exports.state.accepted;local image=world.mapImage
    local decorations=mod.exports.roofs:cells(game,def)
    capture(160,144,function()
     for i=1,12 do clock=i/60;world.mapImage=world:imageFor(map.id);G.draw(world.mapImage,0,0);world:drawAnimCells(map.id,0,0,1)end
    end)
    mod.read,mod.assets.path,world.bakeMapImage=readOwn,pathOwn,bakeOwn
    check(importReads==beforeWarm and ownReads==0 and assetReads==0,'Warm scene reread files: '..game..'/'..id)
    check(bakes==0 and world.mapImage==image,'Warm scene rebuilt native background: '..game..'/'..id)
    check(mod.exports.state.accepted==accepted and mod.exports.roofs:cells(game,def)==decorations,'Warm scene rebuilt mappings/decorations: '..game..'/'..id)
    check(snapshot(map,2)==mechanics and eventSnapshot(map)==events,'Artwork changed source mechanics: '..game..'/'..id)
    local fixture={game=game,map=id,source_daytime='DAY',coverage=c,
     native_renderer='src.world.gen2.World:bakeMapImage + drawAnimCells',
     checked_gpu_pixels=pixels,source_collision_events_unchanged=true,
     warm_frames=12,warm_import_reads=0,warm_asset_reads=0,warm_bakes=0,warm_mapping_rebuilds=0,
     before=encodePng(before,game..'-'..id..'-native-gpu.png'),
     after=encodePng(after,game..'-'..id..'-gen3-gpu.png')}
    if id=='SAFFRON_CITY'then
     clock=0
     fixture.center_styles=verifyCenterStyles(game,def,after,world,mod,function()return drawWorld2(world)end)
    end
    mod.exports.dispose();clock=0;world.mapImage=world:imageFor(map.id)
    check(drawWorld2(world):getString()==before:getString(),'Cleanup failed to restore source pixels: '..game..'/'..id)
    fixture.cleanup_restored_native=true;report.fixtures[#report.fixtures+1]=fixture
    report.totals.scenes=report.totals.scenes+1;report.totals.source_cells=report.totals.source_cells+c.visible_cells
    report.totals.replaced_cells=report.totals.replaced_cells+c.replaced_occurrences
    report.totals.remaining_cells=report.totals.remaining_cells+c.preserved_native_occurrences
    report.totals.checked_pixels=report.totals.checked_pixels+pixels;report.totals.warm_frames=report.totals.warm_frames+12
    write('progress.json',Json.encode({fixtures=#report.fixtures,checks=report.checks,game=game,map=id}))
   end
  end
 end
 check(#report.fixtures>0 and #report.warnings==0,'Empty probe or reported warning')
 report.status='passed';write('report.json',Json.encode(report))
end
"""

def main():
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--games',nargs='+',choices=('gold','silver','crystal'),default=['gold','silver','crystal'])
    parser.add_argument('--maps',nargs='+',default=MAPS)
    args,remaining=parser.parse_known_args();sys.argv[1:]=remaining
    assert args.maps and all(re.fullmatch(r'[A-Z][A-Z0-9_]*',name)for name in args.maps),'Invalid native map ID'
    source=validate_gpu.LUA
    prefix=source[:source.index(' -- Native Gen1 TileRenderer on real Red Pallet Town.')]
    setup=source[source.index(' -- Real Gold/Silver/Crystal World bake'):source.index(' local function verifyGen2Ladders')]
    selection=dict(games=args.games,maps=args.maps)
    validate_gpu.LUA=prefix+setup+BODY.replace('@SELECTION@',json.dumps(json.dumps(selection)))+source[source.index('\nfunction love.load()'):]
    if '--output'not in sys.argv:sys.argv.extend(['--output',str(Path(__file__).resolve().parents[2]/'.work/tileshift-v0300-gen2-gpu')])
    return validate_gpu.main()

if __name__=='__main__':raise SystemExit(main())
