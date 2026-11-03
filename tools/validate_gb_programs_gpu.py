"""Compare checked Crystal tile-program frames with the actual native World."""
import json
from pathlib import Path
import sys
import catalog
from reverse_common import ReverseReview
from gb_theme_animation import program_layers, specification, frames, foreground_frames
import validate_gpu

BODY=r"""
 report.type='native Crystal program animation comparison'
 report.theme='gb-program-decoder'
 report.limits='Original Crystal programs compare against actual native World:bakeMapImage/drawAnimCells. Derived directional currents use complete original cave-water glyphs with independently checked pixel permutations; Crystal has no forced-current counterpart. No synthetic source maps, persistence or source-art edits.'
 local scenes=Json.decode(@SCENES@)
 local flows=Json.decode(@FLOWS@)
 local Decoder=assert(load(assert(read(MOD..'/lib/donor.lua'))))()
 local Animation=assert(load(assert(read(MOD..'/lib/gb_animation.lua'))))()
 local allocations=0
 local decoder=Decoder.new({gbAnimation=Animation,identityToken=function()return 1 end,
  newImageData=function(...)allocations=allocations+1;return love.image.newImageData(...)end})
 report.totals={scenes=0,frames=0,checked_pixels=0,warm_calls=0,derived_current_scenes=0,derived_current_frames=0}
 GV.set('crystal');assetGame='crystal';clock=0
 for _,scene in ipairs(scenes)do
  local world,map,def=world2('crystal',scene.map);world.mapImage=world:imageFor(map.id)
  local mechanics,events=snapshot(map,2),eventSnapshot(map)
  local sequence,why=decoder:frames(scene.ref,scene.spec);check(sequence~=nil,tostring(why))
  check(#sequence.frames==8 and sequence.period==scene.period/60,'Native program timing mismatch')
  for timer=0,7 do
   world.animTimer=timer
   local native=drawWorld2(world);local image=sequence.frames[timer+1].under
   check(hash(image:getString())==scene.hashes[timer+1],'Independent Python program frame differs')
   check(hash(sequence.frames[timer+1].foreground:getString())==scene.foreground_hashes[timer+1],
    'Independent native shade foreground mask differs')
   for y=0,15 do for x=0,15 do
    equalPixel(native,scene.x*16+x,scene.y*16+y,image,x,y,'Native Crystal tile program differs')
   end end
  end
  local count,reads=allocations,importReads
  for i=1,16 do check(decoder:frames(scene.ref,scene.spec)==sequence,'Native program cache identity changed')end
  check(importReads==reads,'Cached GB program reread imports')
  check(snapshot(map,2)==mechanics and eventSnapshot(map)==events,'Program preview changed source map mechanics')
  report.fixtures[#report.fixtures+1]={game='crystal',map=scene.map,tileset=scene.ref.tileset,block=scene.ref.id,
   quadrant=scene.ref.quadrant,layers=scene.layers,frames=8,native_pixels_checked=2048,source_unchanged=true,
   warm_calls=16,warm_import_reads=0,warm_frame_rebuilds=0,
   source_reference_validation_image_allocations=allocations-count}
  report.totals.scenes=report.totals.scenes+1;report.totals.frames=report.totals.frames+8
  report.totals.checked_pixels=report.totals.checked_pixels+2048;report.totals.warm_calls=report.totals.warm_calls+16
 end
 local sequences={}
 for _,scene in ipairs(flows)do
  local world,map=world2('crystal',scene.map);world.mapImage=world:imageFor(map.id)
  local mechanics,events=snapshot(map,2),eventSnapshot(map)
  local sequence,why=decoder:frames(scene.ref,scene.spec);check(sequence~=nil,tostring(why))
  check(#sequence.frames==8 and sequence.period==scene.period/60,'Derived current changed native glyph cadence')
  for direction,prior in pairs(sequences)do check(sequence~=prior,'Native current cache merged '..direction..' and '..scene.direction)end
  sequences[scene.direction]=sequence
  for timer=0,7 do
   local piece=sequence.frames[timer+1]
   check(hash(piece.under:getString())==scene.hashes[timer+1],'Independent directional-water pixel permutation differs')
   check(hash(piece.foreground:getString())==scene.foreground_hashes[timer+1],'Independent directional-water foreground differs')
   -- Every derived direction starts on the exact original source glyph,
   -- not a newly rasterized imitation. Later phases scroll unidirectionally
   -- instead of the original Crystal cave's horizontal oscillation.
   if timer==0 then
    world.animTimer=timer;local native=drawWorld2(world)
    for y=0,15 do for x=0,15 do
     equalPixel(native,scene.x*16+x,scene.y*16+y,piece.under,x,y,'Derived current lost original native source glyph')
    end end
   end
  end
  local reads=importReads
  for i=1,16 do check(decoder:frames(scene.ref,scene.spec)==sequence,'Derived current rebuilt its cached sequence')end
  check(importReads==reads,'Cached current reread native source files')
  check(snapshot(map,2)==mechanics and eventSnapshot(map)==events,'Derived current changed source map mechanics')
  report.fixtures[#report.fixtures+1]={game='crystal',map=scene.map,tileset=scene.ref.tileset,block=scene.ref.id,
   quadrant=scene.ref.quadrant,derived_current_direction=scene.direction,frames=8,
   independent_rgba_frames_checked=8,full_native_source_glyph_retained=true,source_unchanged=true,
   warm_calls=16,warm_import_reads=0,warm_frame_rebuilds=0}
  report.totals.derived_current_scenes=report.totals.derived_current_scenes+1
  report.totals.derived_current_frames=report.totals.derived_current_frames+8
 end
 check(#report.warnings==0,'Unexpected native program warning')
 report.status='passed';write('report.json',Json.encode(report))
end
"""


def main():
    f=ReverseReview('gen2-program-validation',['emerald']);sets=f.imp.table('crystal','tilesets')
    candidates=[];seen=set();unsupported=set()
    for name,m in sorted(f.imp.table('crystal','maps').items()):
        if not isinstance(m,dict)or not isinstance(m.get('blocks'),list):continue
        ts=sets[m['tileset']]
        for index,bid in enumerate(m['blocks']):
            for q in range(4):
                key=m['tileset'],bid,q
                if key in seen:continue
                seen.add(key)
                ref=dict(id=bid,quadrant=q)
                try:layers=program_layers(sets,ts,ref)
                except ValueError as error:
                    if not str(error).startswith('Unsupported native GB tile program:'):raise
                    unsupported.add(str(error));continue
                if not layers:continue
                targets={(m['tileset'],tile,v['kind'])for tile,v in layers.items()}
                candidates.append(dict(map=name,id=bid,q=q,x=index%m['width']*2+q%2,
                    y=index//m['width']*2+q//2,targets=targets,layers=layers,weight=m['width']*m['height']))
    universe=set().union(*(c['targets']for c in candidates));remaining=universe.copy();selected=[]
    while remaining:
        c=max(candidates,key=lambda c:(len(c['targets']&remaining),-c['weight']))
        remaining-=c['targets'];selected.append(c)
    scenes=[]
    for c in selected:
        ref=f.gb_ref('crystal',c['map'],c['id'],c['q']);spec=specification(f.cache,ref,'program')
        images=frames(f.cache,ref,spec,f.packed)
        foregrounds=foreground_frames(f.cache,ref,spec,f.packed)
        scenes.append(dict(map=c['map'],x=c['x'],y=c['y'],ref=ref,spec=spec,layers=c['layers'],
            period=sets[ref['tileset']]['anim']['period'],hashes=[catalog.sha(im.tobytes())for im in images],
            foreground_hashes=[catalog.sha(im.tobytes())for im in foregrounds]))
    assert {'scroll','whirlpool','lava1','lava2','tower','water','flower'}<={kind for _,_,kind in universe}
    pure=[]
    for c in candidates:
        if c['layers'].keys()!={20}or c['layers'][20]['kind']!='scroll':continue
        ref=f.gb_ref('crystal',c['map'],c['id'],c['q'])
        try:specification(f.cache,ref,'program','south')
        except AssertionError:continue
        pure.append(c)
    assert pure,'No actual native pure scrolling-water source witness'
    c=min(pure,key=lambda c:(c['weight'],c['map'],c['id'],c['q']))
    ref=f.gb_ref('crystal',c['map'],c['id'],c['q']);flows=[]
    for direction in ('north','south','east','west'):
        spec=specification(f.cache,ref,'program',direction)
        images=frames(f.cache,ref,spec,f.packed);foregrounds=foreground_frames(f.cache,ref,spec,f.packed)
        flows.append(dict(map=c['map'],x=c['x'],y=c['y'],ref=ref,spec=spec,direction=direction,
                          period=sets[ref['tileset']]['anim']['period'],hashes=[catalog.sha(im.tobytes())for im in images],
                          foreground_hashes=[catalog.sha(im.tobytes())for im in foregrounds]))
    (f.out/'witnesses.json').write_text(json.dumps(scenes,indent=2)+'\n')
    (f.out/'derived-current-witnesses.json').write_text(json.dumps(flows,indent=2)+'\n')
    (f.out/'unsupported-programs.json').write_text(json.dumps(sorted(unsupported),indent=2)+'\n')
    source=validate_gpu.LUA
    prefix=source[:source.index(' -- Native Gen1 TileRenderer on real Red Pallet Town.')]
    setup=source[source.index(' -- Real Gold/Silver/Crystal World bake'):source.index(' local function verifyGen2Ladders')]
    body=BODY.replace('@SCENES@',json.dumps(json.dumps(scenes))).replace('@FLOWS@',json.dumps(json.dumps(flows)))
    validate_gpu.LUA=prefix+setup+body+source[source.index('\nfunction love.load()'):]
    return validate_gpu.main()


if __name__=='__main__':raise SystemExit(main())
