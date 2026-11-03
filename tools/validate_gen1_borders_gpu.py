"""Check real Gen1 border-fill pixels, including water/tree/black void modes."""
import argparse
import json
from pathlib import Path
import sys
import validate_gpu

BODY=r"""
 report.type='native Gen1 border-fill and void-mode GPU validation'
 report.limits='Actual TileRenderer.drawBorderFill on reviewed edge cases; no map/script/save writes.'
 local scenes=Json.decode(@SCENES@)
 local Map=require('src.world.Map');local T=require('src.render.TileRenderer');local FX=require('src.render.PaletteFX')
 local originalMode=T.voidFill
 report.border_cases={};report.totals={cases=0,checked_pixels=0,warm_frames=0}
 for _,scene in ipairs(scenes)do
  local game,id=scene.game,scene.map;GV.set(game);assetGame=game;clock=0;FX.setDarkWorld(false)
  local maps,sets=generated(game,'maps'),generated(game,'tilesets');local def=assert(maps[id])
  local map=Map.new(def,sets[def.tileset]);local renderer=T.new(map,{maps=maps,tilesets=sets})
  T.setVoidFill(scene.mode=='map'and'trees'or scene.mode)
  local function draw()
   return capture(64,64,function()
    FX.clearTrueColor();FX.setPass('world');renderer:drawBorderFill(-32,-32,64,64);FX.setPass(nil)
   end)
  end
  local before=draw();local mechanics,events=snapshot(map,1),eventSnapshot(map)
  local mod=startMod(game,1);local art=assert(mod.exports.state:replacements(game,def.tileset,def))
  check(mod.exports.state.rejected==0,'Border reviewed source row rejected')
  local bid=T.borderBlockFor(map);local selected=bid~=false and bid~=nil and art[bid]or nil
  local after=draw();local pixels=0
  if bid~=false and bid~=nil then
   check(selected and selected.image,'Visible native border lacks Gen3 artwork: '..game..'/'..id..'/'..tostring(bid))
   for q=0,3 do check(not selected.coverage or selected.coverage[q],'Visible border quadrant unmapped')end
   for _,time in ipairs({0,17/60})do
    clock=time;local frame=draw()
    for y=0,63 do for x=0,63 do
     local sx,sy=(x-32)%32,(y-32)%32;local q=math.floor(sy/16)*2+math.floor(sx/16)
     local sequence=selected.cellAnimations and selected.cellAnimations[q]or selected
     local expected=sequence.frames and sequence.frames[math.floor(math.max(0,clock-(sequence.offset or 0))/(sequence.period or .2))%#sequence.frames+1]or selected.image
     if x<32 or y<32 then
      equalPixel(frame,x,y,expected,sx,sy,'Native border retains wrong or unconverted pixels')
     else
      equalPixel(frame,x,y,before,x,y,'Border fill painted over the current map interior')
     end
     pixels=pixels+1
    end end
   end
  else
   for y=0,63 do for x=0,63 do local r,g,b=after:getPixel(x,y);check(r==0 and g==0 and b==0,'Black void changed color');pixels=pixels+1 end end
  end
  local reads,accepted=importReads,mod.exports.state.accepted
  for i=1,12 do clock=i/60;draw()end
  check(importReads==reads and mod.exports.state.accepted==accepted,'Warm border rendering reread imports/rebuilt mappings')
  check(snapshot(map,1)==mechanics and eventSnapshot(map)==events,'Border artwork changed source mechanics')
  mod.exports.dispose();clock=0;check(draw():getString()==before:getString(),'Border cleanup failed to restore native pixels')
  report.border_cases[#report.border_cases+1]={game=game,map=id,mode=scene.mode,block=bid,checked_pixels=pixels,
   complete_reviewed_border=bid~=false,source_mechanics_unchanged=true,cleanup_restored_native=true,warm_frames=12}
  report.totals.cases=report.totals.cases+1;report.totals.checked_pixels=report.totals.checked_pixels+pixels;report.totals.warm_frames=report.totals.warm_frames+12
  write('progress.json',Json.encode({cases=#report.border_cases,game=game,map=id,checks=report.checks}))
 end
 T.setVoidFill(originalMode)
 check(#report.warnings==0,'Native border probe reported a mapping warning')
 report.status='passed';write('report.json',Json.encode(report))
end
"""


def main():
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--inventory',type=Path,required=True)
    args,remaining=parser.parse_known_args();sys.argv[1:]=remaining
    inventory=json.loads(args.inventory.read_text())
    scenes={(r['game'],r['map'],r['mode'])for r in inventory['nonblack_missing']}
    scenes.update((game,'PALLET_TOWN',mode)for game in('red','blue','yellow')for mode in('trees','water','black'))
    selected=[dict(game=g,map=m,mode=mode)for g,m,mode in sorted(scenes)]
    source=validate_gpu.LUA;prefix=source[:source.index(' -- Native Gen1 TileRenderer on real Red Pallet Town.')]
    suffix=source[source.index('\nfunction love.load()'):]
    validate_gpu.LUA=prefix+BODY.replace('@SCENES@',json.dumps(json.dumps(selected)))+suffix
    return validate_gpu.main()


if __name__=='__main__':raise SystemExit(main())
