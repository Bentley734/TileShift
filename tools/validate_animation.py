"""Compare neutral donor water frames with the actual Emerald or FR/LG animator.

Reads local cartridge imports only. Images and native upload calls use memory
fixtures; no game, imported content, options, or installed mods are changed.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import os
from pathlib import Path
import sys
import zlib

IMAGE_FIXTURE = r'''
bit=require('bit')
function makeData(w,h,format,raw)
  local pixels={};local data={}
  function data:getDimensions()return w,h end
  function data:getPixel(x,y)
    assert(x>=0 and y>=0 and x<w and y<h,'image fixture bounds')
    local p=pixels[y*w+x]
    if p then return p[1],p[2],p[3],p[4] end
    if raw then
      local i=(y*w+x)*4+1
      return raw:byte(i)/255,raw:byte(i+1)/255,raw:byte(i+2)/255,raw:byte(i+3)/255
    end
    return 0,0,0,0
  end
  function data:setPixel(x,y,r,g,b,a)pixels[y*w+x]={r,g,b,a or 1}end
  function data:paste(source,dx,dy,sx,sy,sw,sh)
    local sourceW,sourceH=source:getDimensions()
    sx,sy,sw,sh=sx or 0,sy or 0,sw or sourceW,sh or sourceH
    for y=0,sh-1 do for x=0,sw-1 do
      self:setPixel(dx+x,dy+y,source:getPixel(sx+x,sy+y))
    end end
  end
  function data:getString()
    local out={}
    for y=0,h-1 do for x=0,w-1 do
      local r,g,b,a=self:getPixel(x,y)
      out[#out+1]=string.char(math.floor(r*255+.5),math.floor(g*255+.5),
        math.floor(b*255+.5),math.floor(a*255+.5))
    end end
    return table.concat(out)
  end
  return data
end
love={image={newImageData=makeData}}
'''

COMPARE = r'''
local GV=require('src.core.GameVersion');GV.set(selectedGame)
local Versions=require('src.import.gba.versions');Versions.select(selectedGame)
_G.__tileAnimationUploads=_G.__tileAnimationUploads or {count=0}
local uploadCounter=_G.__tileAnimationUploads
local beforeUploads=uploadCounter.count
-- The actual animation implementation still performs its normal pixel
-- decoding, phase scheduling and quadrant pastes; only GPU uploads are inert.
_G.__tileAnimationBackend=_G.__tileAnimationBackend or {
  markDirty=function()end,flush=function()uploadCounter.count=uploadCounter.count+1 end,
  ensureAlt=function()end,prepareSlot=function()end}
package.loaded['src.core.game3.tileset_native']=_G.__tileAnimationBackend
package.loaded['src.core.game3.warm']={add=function()end,yield=function()end}
local Anim=require('src.core.game3.tileset_anim')
local cache={read=function(_,path)return readImported(selectedGame..'/'..path)end}
local atlas={cols=1,midToSlot={[selectedMid]=0},imageData=makeData(16,16),overImageData=makeData(16,16)}
atlas.imageData:paste(base.under,0,0);atlas.overImageData:paste(base.over,0,0)
Anim.install(cache);assert(Anim.bindPair(selectedPair,atlas))
local checks=0
for tick=1,129 do
  if selectedGame=='emerald' then Anim.stepRse() else Anim.step() end
  local index=math.floor(math.max(0,tick-sequence.phase)/sequence.ticks)%#sequence.frames+1
  local expected=sequence.frames[index]
  assert(atlas.imageData:getString()==expected.under:getString(),
    'native under animation disagrees at tick '..tick..', frame '..index)
  assert(atlas.overImageData:getString()==expected.over:getString(),
    'native over animation disagrees at tick '..tick..', frame '..index)
  checks=checks+2
end
assert(uploadCounter.count>beforeUploads,'native animator was not exercised')
return checks
'''


def main() -> int:
    mod_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", type=Path, default=mod_root.parent / ".tools/engine-0395")
    parser.add_argument("--cache", type=Path, default=Path(os.environ.get("APPDATA", "~")) / "pokemon-love2d")
    parser.add_argument("--lupa-path", type=Path, default=mod_root.parent / ".tools/python")
    parser.add_argument("--game", choices=("emerald", "firered", "leafgreen"), default="emerald")
    parser.add_argument("--pair", help="Native tileset pair; defaults to the selected game's coastal pair")
    parser.add_argument("--mid", type=int, action="append", help="Repeat to select mids; default Emerald52 or all six FR/LG Pallet water roles")
    parser.add_argument("--mappings", type=Path, action="append",
                        help="Optional reviewed GB-host water mappings to decode through the real session")
    args = parser.parse_args()
    cache = args.cache.resolve()
    engine = args.engine.resolve()
    mapping_paths = [p.resolve() for p in args.mappings or
                     (mod_root / "mappings/water.lua", mod_root / "mappings/coasts.lua") if p.is_file()]
    pair = args.pair or ("general__petalburg" if args.game == "emerald" else "pallet_outdoor")
    selected_mids = args.mid or ([52] if args.game == "emerald" else [721, 291, 722, 298, 299, 300])
    sys.path.insert(0, str(args.lupa_path.resolve()))
    LuaRuntime = importlib.import_module("lupa.luajit21").LuaRuntime

    def read_imported(relative: bytes):
        path = (cache / relative.decode()).resolve()
        if not path.is_relative_to(cache) or not path.is_file():
            return None
        raw = path.read_bytes()
        if path.suffix in (".idx", ".rgba"):
            try:
                return zlib.decompress(raw)
            except zlib.error:
                pass
        return raw

    before_cwd = Path.cwd()
    accepted = None
    try:
        os.chdir(engine)
        lua = LuaRuntime(unpack_returned_tuples=True, encoding=None)
        lua.execute(IMAGE_FIXTURE.encode())
        lua.globals()[b"readImported"] = read_imported
        ctx = lua.table_from({
            b"read": read_imported,
            b"prefix": lambda game: game + b"/",
            b"hash": lambda raw: hashlib.sha256(raw).hexdigest().encode(),
            b"newImageData": lua.globals()[b"makeData"],
        })
        module = lua.execute((mod_root / "lib/donor.lua").read_bytes())
        decoder = module[b"new"](ctx)
        native_root = f"{args.game}/data/generated/gba/native/{pair}/".encode()
        bank = b"general_water" if args.game == "emerald" else b"water"
        bank_file = b"anim_general_water.idx" if args.game == "emerald" else b"anim_water.rgba"
        recipe = lua.table_from({
            b"bank": bank,
            b"hash": hashlib.sha256(read_imported(native_root + bank_file)).hexdigest().encode(),
            b"manifestHash": hashlib.sha256(read_imported(native_root + b"anim_manifest.lua")).hexdigest().encode(),
        })
        comparisons = []
        for mid in selected_mids:
            ref = lua.table_from({b"game": args.game.encode(), b"tileset": pair.encode(), b"id": mid})
            base = decoder[b"cell"](decoder, ref)
            if isinstance(base, tuple):
                raise AssertionError(base)
            ref[b"hash"] = base[b"sourceHash"]
            sequence = decoder[b"frames"](decoder, ref, recipe)
            if isinstance(sequence, tuple):
                raise AssertionError(sequence)
            assert len(sequence[b"frames"]) == 8 and sequence[b"ticks"] == 16
            comparisons.append((mid, base, sequence))
        if args.game == "emerald":
            pond = decoder[b"frames"](decoder, lua.table_from({
                b"game": b"emerald", b"tileset": pair.encode(), b"id": 161,
            }), recipe)
            assert isinstance(pond, tuple) and pond[0] is None and b"not targeted" in pond[1], pond
        # Neutral decoder must not have loaded any generation runtime modules.
        for name in lua.eval(b"package.loaded").keys():
            assert not name.startswith((b"src.core.game3.", b"src.world.gen2.")), name
        if mapping_paths:
            from PIL import Image

            def load_image(relative: bytes, _raw: bytes):
                with Image.open(cache / relative.decode()) as source:
                    image = source.convert("RGBA")
                    return lua.globals()[b"makeData"](image.width, image.height, b"rgba8", image.tobytes())

            ctx[b"loadImage"] = load_image
            session_decoder = module[b"new"](ctx)
            mapping = lua.execute((mod_root / "lib/mapping.lua").read_bytes())
            session = lua.execute((mod_root / "lib/session.lua").read_bytes())
            all_rows = []
            for path in mapping_paths:
                rows = lua.execute(path.read_bytes())
                all_rows.extend(rows[i] for i in range(1, len(rows) + 1))
            water = lua.table_from(all_rows)
            lua.globals()[b"waterMappings"] = water
            lua.globals()[b"mappingRules"] = mapping
            lua.globals()[b"sessionModule"] = session
            lua.globals()[b"sessionDecoder"] = session_decoder
            accepted = lua.execute(br'''
local index,errors=mappingRules.index(waterMappings);assert(#errors==0,table.concat(errors,'\n'))
local state=sessionModule.new({mappings=index,donor=sessionDecoder,newImageData=makeData,
  generations=mappingRules.generations,validate=mappingRules.validate,
  warn=function(message)error(message)end})
state:select('gen3')
local done={}
for _,row in ipairs(waterMappings)do
  local key=row.game..':'..row.tileset..':'..tostring(row.map)
  if not done[key] then
    done[key]=true
    local blocks=state:replacements(row.game,row.tileset,{id=row.map})
    for _,block in pairs(blocks)do
      if block.frames then
        assert(#block.frames==8 and block.period==16/60 and block.offset==1/60,
          'GB host animation timing differs from native water bank')
      end
    end
  end
end
assert(state.rejected==0,'Reviewed water mappings rejected')
assert(state.accepted==#waterMappings,'Reviewed water mapping coverage is incomplete')
return state.accepted
''')
        lua.globals()[b"selectedGame"] = args.game.encode()
        lua.globals()[b"selectedPair"] = pair.encode()
        results = []
        for mid, base, sequence in comparisons:
            lua.globals()[b"base"] = base
            lua.globals()[b"sequence"] = sequence
            lua.globals()[b"selectedMid"] = mid
            results.append((mid, lua.execute(COMPARE.encode())))
    finally:
        os.chdir(before_cwd)
    for mid, checks in results:
        print(f"PASS {args.game} mid{mid}: {checks} exact layer snapshots across129 native ticks; eight frames, phase1,16 ticks/frame.")
    if args.game == "emerald":
        print("PASS Emerald pond mid161 rejected as static.")
    print("PASS neutral decoder loaded no generation runtime modules; no filesystem writes.")
    if accepted is not None:
        print(f"PASS {accepted} reviewed GB-host water/coast mappings decoded and composed through the real session; zero rejected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
