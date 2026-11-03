"""Batch the native reverse-theme scene probe without repeating its mod index.

The original per-map probe remains available as a reference. This runner keeps
its pixel, animation, priority, warm-cache and immutable-source checks, with
separate native, themed, animation-Off and cleanup passes per game.
"""
import json
from pathlib import Path
import sys
import validate_reverse_gpu as reference
import validate_gpu


def batch_body(body):
    setup_end=body.index("  for _,id in ipairs(ids)do")
    setup=body[:setup_end]
    helpers=body[body.index("   local oldale=id:match"):body.index("   for _,theme in ipairs(selection.styles")]
    checks=body[body.index("    assert(mod.exports.select(theme));clock=0"):body.index("    assert(mod.exports.select('original'));clock=0")]
    checks=checks.replace("    assert(mod.exports.select(theme));clock=0", "    clock=0")
    off_start=checks.index("    clock=0\n    for _,key in ipairs({'speed_water','speed_flowers'})")
    off_end=checks.index("    check(mod.exports.state.rejected==0",off_start)
    checks=checks[:off_start]+"    clock=0;after=draw()\n"+checks[off_end:]
    checks += "    resultById[id]=report.fixtures[#report.fixtures]\n"
    return setup+PREPARE+helpers+checks+AFTER

PREPARE=r"""
  local FieldPlan=require('src.core.game3.field_plan')
  report.capture_pipeline='per-game native, themed, animation-Off and cleanup passes; one mod index per game'
  local contexts={}
  local function bind(c)
   Map._def=c.def;Map._currentDef=c.def;Map.current=c.id;Map.neighborList={};Map.neighbors={}
   -- Body scenes retain the engine's native connected world. Only its plan is
   -- invalidated: View.invalidate would discard every already-decoded atlas.
   FieldPlan.invalidate();View._nativeDirty=true;View._flashMapId=c.id;View.setFlashLevel(0)
   mod.game=c.host;clock=0
   Anim.setVisiblePairs({[c.pair]=true});Anim.enterMap(c.pair,false)
  end
  assert(mod.exports.select('original'))
  for _,id in ipairs(ids)do
   local def=assert(maps[id],'Native map unavailable '..id);Dataset.attachMidLayouts({[id]=def},cache)
   local layout=assert(def.midLayout);local pair=assert(def.pair or layout.pair)
   assert(Native.get(pair),'Native atlas unavailable '..game..'/'..pair)
   local columns,rows=layout.trueWidth or layout.width,layout.trueHeight or layout.height
   local width,height=columns*16,rows*16
   local host={data={maps=maps},save={position={map=id},flags={},vars={},options={}},options={},world={map={id=id},player={px=width/2-8,py=height/2-8,facing='down'}}}
   local c={id=id,def=def,layout=layout,pair=pair,columns=columns,rows=rows,width=width,height=height,host=host}
   c.draw=function(opts)return capture(width,height,function()View.draw(host,width,height,opts or{skipActors=true})end)end
   contexts[id]=c;bind(c);c.before=c.draw()
   c.immutable=hash(tableString(layout.cells)..tableString(def.warps)..tableString(def.objects)..tableString(def.coordEvents))
   write('progress.json',Json.encode({fixtures=#report.fixtures,game=game,map=id,phase='native'}))
  end
  for _,theme in ipairs(selection.styles or{'gen1','gen2'})do
   assert(mod.exports.select(theme));local resultById={}
   for _,id in ipairs(ids)do
    local c=contexts[id];bind(c)
    local def,layout,pair=c.def,c.layout,c.pair
    local columns,rows,width,height=c.columns,c.rows,c.width,c.height
    local draw,before,immutable=c.draw,c.before,c.immutable
"""

AFTER=r"""
    write('progress.json',Json.encode({fixtures=#report.fixtures,game=game,map=id,theme=theme,phase='themed'}))
   end
   -- Select Off once, then exercise every source scene at two distant times.
   for _,key in ipairs({'speed_water','speed_flowers'})do mod._probeEvents:emit('mod.options_changed',{mod='tileshift',key=key,value=1})end
   for _,id in ipairs(ids)do
    local c=contexts[id];bind(c);clock=0;local frozen=c.draw();clock=9.37
    check(c.draw():getString()==frozen:getString(),'Off animation must retain its first frame')
    check(hash(tableString(c.layout.cells)..tableString(c.def.warps)..tableString(c.def.objects)..tableString(c.def.coordEvents))==c.immutable,'Off changed source layout/events')
    resultById[id].animation_off_verified=true
    write('progress.json',Json.encode({fixtures=#report.fixtures,game=game,map=id,theme=theme,phase='animation-Off'}))
   end
   for _,key in ipairs({'speed_water','speed_flowers'})do mod._probeEvents:emit('mod.options_changed',{mod='tileshift',key=key,value=3})end
  end
  mod.exports.dispose()
  for _,id in ipairs(ids)do
   local c=contexts[id];bind(c)
   check(c.draw():getString()==c.before:getString(),'Reverse theme cleanup did not restore original FieldView pixels')
   check(hash(tableString(c.layout.cells)..tableString(c.def.warps)..tableString(c.def.objects)..tableString(c.def.coordEvents))==c.immutable,'Cleanup changed source layout/events')
   for _,f in ipairs(report.fixtures)do if f.game==game and f.map==id then f.cleanup_restored_native=true end end
   write('progress.json',Json.encode({fixtures=#report.fixtures,game=game,map=id,phase='cleanup'}))
  end
 end
 check(#report.fixtures==selection.expected_scenes,'Selected native scenes were skipped')
 report.status='passed';write('report.json',Json.encode(report))
end
"""


def main():
    reference.BODY=batch_body(reference.BODY)
    return reference.main()

if __name__=='__main__':raise SystemExit(main())
