"""Exercise live Gen2 cached backgrounds at mod enable, revision and unload.

Uses native World drawGround, real imports and the production mod. Unlike a
static map capture, it never repairs mapImage on the mod's behalf. All writes
are private test outputs; no saves, installed mods or imports are changed.
"""
import argparse
import json
from pathlib import Path
import sys
import validate_gpu


BODY = r'''
 report.type='native Gen2 live cached-background lifecycle'
 report.limits='Native World drawGround with live pre-existing current/neighbor canvases; background lifecycle and source-mechanics checks, not a playthrough.'
 local selected=Json.decode(@SELECTION@)
 for _,game in ipairs(selected.games)do
  for _,id in ipairs(selected.maps)do
   GV.set(game);assetGame=game;clock=0
   local world,map,def=world2(game,id)
   local neighborId=id=='ECRUTEAK_CITY'and'ROUTE_37'or'ECRUTEAK_CITY'
   local neighbor=assert(world.maps[neighborId])
   world.mapImage=world:imageFor(id)
   world.neighbors={{id=neighborId,ox=0,oy=world.viewH,image=world:imageFor(neighborId)}}
   local nativeImage,nativeNeighbor=world.mapImage,world.neighbors[1].image
   local mechanics,events=snapshot(map,2),eventSnapshot(map)
   local function ground()
    return capture(world.viewW,world.viewH,function()world:drawGround(1)end)
   end
   local original=ground()
   local mod=startMod(game,2,world)
   -- The existing background references are intentionally left untouched.
   local actual=ground()
   local art=assert(mod.exports.state:replacements(game,def.tileset,def))
   local live=encodePng(actual,game..'-'..id..'-live-gen3.png')
   local native=encodePng(original,game..'-'..id..'-native.png')
   local counts=coverage(def,art)
   check(world.mapImage~=nativeImage,'Enabling TileShift left the native current-map canvas attached')
   check(world.neighbors[1].image~=nativeNeighbor,'Enabling TileShift left a native connected-map canvas attached')
   local expected=world:imageFor(id)
   check(world.mapImage==expected,'Current-map canvas is not the selected revision')
   check(world.neighbors[1].image==world:imageFor(neighborId),'Connected canvas is not the selected revision')
   -- Verify the current map on its own: a neighbor's legitimate north-edge
   -- canopy can cover its bottom row in the connected drawGround capture.
   verifyCoveredPixels(def,art,drawWorld2(world),game..' '..id..' live enable')
   -- Reproduce a stale reference restored by another loading/connection path.
   world.mapImage=nativeImage;world.neighbors[1].image=nativeNeighbor
   check(ground():getString()==actual:getString(),'A restored native canvas mixed with replacement extensions')
   -- Actual theme changes must update all attached canvases before drawing.
   mod.exports.state:select('original')
   check(ground():getString()==original:getString(),'Original theme retained replacement artwork')
   mod.exports.state:select('gen3')
   actual=ground()
   verifyCoveredPixels(def,assert(mod.exports.state:replacements(game,def.tileset,def)),drawWorld2(world),game..' live reselect')
   -- Unchanged draws stay on the same canvases and do no import/asset reads.
   local beforeReads=importReads;local own,assets,bakes=0,0,0
   local r,p,b=mod.read,mod.assets.path,world.bakeMapImage
   mod.read=function(self,...)own=own+1;return r(self,...)end
   mod.assets.path=function(self,...)assets=assets+1;return p(self,...)end
   world.bakeMapImage=function(self,...)bakes=bakes+1;return b(self,...)end
   local attached=world.mapImage
   for i=1,12 do ground()end
   mod.read,mod.assets.path,world.bakeMapImage=r,p,b
   check(importReads==beforeReads and own==0 and assets==0 and bakes==0 and attached==world.mapImage,'Warm live draws rebuilt or reread artwork')
   check(snapshot(map,2)==mechanics and eventSnapshot(map)==events,'Live refresh changed source mechanics')
   mod.exports.dispose()
   check(ground():getString()==original:getString(),'Unload did not restore native live backgrounds')
   check(world.mapImage==nativeImage and world.neighbors[1].image==nativeNeighbor,'Unload did not restore original current/neighbor references')
   report.fixtures[#report.fixtures+1]={game=game,map=id,live=live,before=native,after=live,coverage=counts,
    native_renderer='src.world.gen2.World:drawGround',late_enable_replaced_cached_native=true,
    stale_reference_repaired=true,connected_neighbor_refreshed=true,original_reselect_restored=true,
    warm_frames=12,warm_import_reads=0,warm_asset_reads=0,warm_bakes=0,source_collision_events_unchanged=true,cleanup_restored_native=true}
   write('progress.json',Json.encode({fixtures=#report.fixtures,checks=report.checks,game=game,map=id}))
  end
 end
 check(#report.fixtures==#selected.games*#selected.maps and #report.warnings==0,'Incomplete live lifecycle matrix or warning')
 report.status='passed';write('report.json',Json.encode(report))
end
'''


def main():
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--games',nargs='+',choices=('gold','silver','crystal'),default=['gold','silver','crystal'])
    parser.add_argument('--maps',nargs='+',choices=('ECRUTEAK_CITY','ROUTE_37'),default=['ECRUTEAK_CITY','ROUTE_37'])
    args,remaining=parser.parse_known_args()
    source=validate_gpu.LUA
    prefix=source[:source.index(' -- Native Gen1 TileRenderer on real Red Pallet Town.')]
    setup=source[source.index(' -- Real Gold/Silver/Crystal World bake'):source.index(' local function verifyGen2Ladders')]
    validate_gpu.LUA=prefix+setup+BODY.replace('@SELECTION@',json.dumps(json.dumps(vars(args))))+source[source.index('\nfunction love.load()'):]
    sys.argv[1:]=remaining
    if '--output'not in remaining:
        sys.argv.extend(['--output',str(Path(__file__).resolve().parents[2]/'.work/tileshift-gen2-lifecycle-gpu')])
    return validate_gpu.main()


if __name__=='__main__':raise SystemExit(main())
