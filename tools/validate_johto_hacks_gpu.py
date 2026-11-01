"""Focused native-renderer checks for the Johto hack artwork migration."""
import sys
from pathlib import Path
import validate_gpu

def main():
 base=validate_gpu.LUA
 prefix=base[:base.index(' -- Native Gen1 TileRenderer on real Red Pallet Town.')]
 setup=base[base.index(' -- Real Gold/Silver/Crystal World bake'):base.index(' local function verifyGen2Ladders')]
 focused=r"""
 for _,game in ipairs({'gold','silver','crystal'})do
  for _,id in ipairs({'CERULEAN_CITY','GOLDENROD_CITY','LAVENDER_TOWN','ECRUTEAK_CITY','OLIVINE_CITY','VIOLET_CITY','AZALEA_GYM','SPROUT_TOWER_1F','NATIONAL_PARK','ILEX_FOREST','ROUTE_41'})do
   GV.set(game);assetGame=game;clock=0
   local world,map,def=world2(game,id)
   world.mapImage=world:imageFor(map.id)
   local native=drawWorld2(world);local mechanics,events=snapshot(map,2),eventSnapshot(map)
   local mod=startMod(game,2,world);world.mapImage=world:imageFor(map.id)
   local function draw()return drawWorld2(world)end
   local art=assert(mod.exports.state:replacements(game,def.tileset,def));local after=draw()
   check(mod.exports.state.rejected==0,'Focused Johto scene rejected artwork')
   local f={game=game,map=id,coverage=coverage(def,art),before=encodePng(native,game..'-'..id..'-native-gpu.png'),after=encodePng(after,game..'-'..id..'-gen3-gpu.png'),checked_donor_pixels=verifyCoveredPixels(def,art,after,game..' '..id)}
   f.centers=verifyCenterStyles(game,def,after,world,mod,draw)
   if id=='CERULEAN_CITY'then f.public=verifyPublicBuildings(game,def,after)end
   if id=='ECRUTEAK_CITY'then f.exteriors=verifyEcruteak(game,def,after,world,mod)end
   if id=='OLIVINE_CITY'then f.exteriors=verifyOlivine(game,def,after,mod)end
   if id=='VIOLET_CITY'then f.exteriors=verifySprout(game,def,after)end
   check(snapshot(map,2)==mechanics and eventSnapshot(map)==events,'Hack artwork modified gameplay source data')
   report.fixtures[#report.fixtures+1]=f;mod.exports.dispose()
  end
 end
 check(#report.warnings==0,'Focused Johto warnings')
 report.status='passed';write('report.json',Json.encode(report))
end
"""
 validate_gpu.LUA=prefix+setup+focused+base[base.index('function love.load()'):]
 if '--output'not in sys.argv:sys.argv.extend(['--output',str(Path(__file__).resolve().parents[2]/'.work/tileshift-firegold/focused-gpu')])
 return validate_gpu.main()
if __name__=='__main__':raise SystemExit(main())
