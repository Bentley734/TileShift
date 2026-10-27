"""Verify positioned architecture against live imports and real Lua composition/session.

Private evidence only. Does not alter imports, options, production mappings or saves.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import zlib
from PIL import Image
import catalog
import preview
import validate_animation
from newbark_building_review import lua as literal

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE / ".tools/python"))
from lupa.luajit21 import LuaRuntime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=Path, default=WORKSPACE / ".work/tileshift-building-extended/architecture-staged-rows.json")
    parser.add_argument("--output", type=Path, default=WORKSPACE / ".work/tileshift-building-extended/architecture-expanded-production-proof.json")
    parser.add_argument("--cache", type=Path, default=Path(os.environ["APPDATA"]) / "pokemon-love2d")
    parser.add_argument("--exclude-production", action="append", default=["buildings_extended.lua"], help="Replace these active files with the private candidate rows for union schema validation")
    args = parser.parse_args()
    args.rows, args.output, args.cache = args.rows.resolve(), args.output.resolve(), args.cache.resolve()
    mod = WORKSPACE / "TileShift"
    rows = json.loads(args.rows.read_text(encoding="utf-8"))
    assert rows and all(r["kind"] == "native_composite" and r["status"] == "reviewed" for r in rows)
    keys = {(r["game"], r["map"], r["x"], r["y"]) for r in rows}
    assert len(keys) == len(rows)
    catalogs = {g: json.loads((WORKSPACE / ".work/tileshift-catalog" / f"{g}.json").read_text()) for g in {r["game"] for r in rows} | {"emerald", "firered"}}
    checked = preview.verify(rows, args.cache, catalogs, mod)
    file_checks, sets, packed = {}, {}, {}
    for row in rows:
        game = row["game"]
        if game not in sets:
            sets[game] = catalog.read_lua(args.cache / game / "data/generated/tilesets.lua")
        ts = sets[game][row["tileset"]]
        files = {"metadata": "data/generated/tilesets.lua", "maps": "data/generated/maps.lua", "image": ts["image"],
                 "palettes": "data/generated/palettes.lua", "roofs": "data/generated/roofs.lua"}
        for name, expected in row["sourceFiles"].items():
            key = game, files[name]
            file_checks.setdefault(key, catalog.sha((args.cache / game / files[name]).read_bytes()))
            assert file_checks[key] == expected, (game, name, "live source file changed")
        image = preview.replacement_image(args.cache, row, packed, mod)
        assert catalog.sha(image.tobytes()) == row["compositionPixelHash"]
        assert set(image.getchannel("A").get_flattened_data()) == {255}
    runtime = LuaRuntime(unpack_returned_tuples=True, encoding=None)
    def table_rows(values):
        result = runtime.table()
        for start in range(0, len(values), 500):
            chunk = runtime.execute(("return " + literal(values[start:start + 500])).encode())
            for i in range(1, len(chunk) + 1):
                result[start + i] = chunk[i]
        return result
    def read(relative):
        path = (args.cache / relative.decode()).resolve()
        assert path.is_relative_to(args.cache.resolve())
        if not path.is_file():
            return None
        raw = path.read_bytes()
        if path.suffix in (".idx", ".rgba"):
            try:
                return zlib.decompress(raw)
            except zlib.error:
                pass
        return raw
    def load_image(relative, _raw):
        image = Image.open(args.cache / relative.decode()).convert("RGBA")
        return runtime.globals()[b"makeData"](image.width, image.height, b"rgba8", image.tobytes())
    previous = Path.cwd()
    try:
        os.chdir(WORKSPACE / ".tools/engine-0395")
        runtime.execute(validate_animation.IMAGE_FIXTURE.encode())
        context = runtime.table_from({b"read": read, b"prefix": lambda game: game + b"/",
                                      b"hash": lambda raw: hashlib.sha256(raw).hexdigest().encode(),
                                      b"newImageData": runtime.globals()[b"makeData"], b"loadImage": load_image})
        donor = runtime.execute((mod / "lib/donor.lua").read_bytes())[b"new"](context)
        composer = runtime.execute((mod / "lib/composition.lua").read_bytes())[b"new"](runtime.table_from({
            b"donor": donor, b"newImageData": runtime.globals()[b"makeData"],
            b"hashImage": lambda image: hashlib.sha256(image[b"getString"](image)).hexdigest().encode()}))
        runtime.globals()[b"architectureRows"] = table_rows(rows)
        runtime.globals()[b"architectureRead"] = read
        runtime.globals()[b"architectureHash"] = context[b"hash"]
        runtime.globals()[b"architectureDecoder"] = donor
        runtime.globals()[b"architectureComposer"] = composer
        runtime.globals()[b"architectureMapping"] = runtime.execute((mod / "lib/mapping.lua").read_bytes())
        runtime.globals()[b"architectureSession"] = runtime.execute((mod / "lib/session.lua").read_bytes())
        # Check combined production keys as well as the isolated art byteproof.
        active = []
        for path in sorted((mod / "mappings").glob("*.lua")):
            existing = preview.read_reviewed(path)
            if path.name in args.exclude_production:
                existing = [r for r in existing if "x" not in r or (r["game"], r["map"], r["x"], r["y"]) not in keys]
            active.extend(existing)
        combined = active + rows
        runtime.globals()[b"architectureUnion"] = table_rows(combined)
        result = runtime.execute(br'''
local _,unionErrors=architectureMapping.index(architectureUnion)
assert(#unionErrors==0,table.concat(unionErrors,'\n'))
local index,errors=architectureMapping.index(architectureRows)
assert(#errors==0,table.concat(errors,'\n'))
local state=architectureSession.new({mappings=index,donor=architectureDecoder,newImageData=makeData,
 generations=architectureMapping.generations,validate=architectureMapping.validate,
 compose=function(row)return architectureComposer:cell(row)end,
 composeFrames=function(row)return architectureComposer:frames(row)end,warn=function(message)error(message)end})
state:select('gen3')
local maps,contexts,scenes,compositionCount,sessionCount={},{},{},0,0
for _,row in ipairs(architectureRows)do
 local piece,why=architectureComposer:cell(row);assert(piece,why)
 assert(architectureHash(piece.under:getString())==row.compositionPixelHash,'Production composition bytes differ')
 compositionCount=compositionCount+1
 if not maps[row.game]then maps[row.game]=assert(require('src.core.SaveSerializer').decode(
  assert(architectureRead(row.game..'/data/generated/maps.lua')),
  {allowArray=true,allowComments=true,maxBytes=16*1024*1024,maxDepth=64,maxNodes=2000000,
   maxStringBytes=8*1024*1024,maxTableEntries=500000}))end
 local key=row.game..':'..row.map
 local def=assert(maps[row.game][row.map])
 if not contexts[key]then
  contexts[key]=state:replacements(row.game,row.tileset,def)
  scenes[key]={reviewed_building_cells=0,map_total_cells=def.width*def.height*4}
 end
 local bx,by=math.floor(row.x/2),math.floor(row.y/2)
 assert(def.blocks[by*def.width+bx+1]==row.id and row.quadrant==row.y%2*2+row.x%2,'Actual source position changed')
 local block=assert(contexts[key][row.id]);local variant=assert(block.positions and block.positions[bx..':'..by])
 assert(variant.coverage[row.quadrant],'Actual positioned source quadrant is not covered')
 local extracted=makeData(16,16);extracted:paste(variant.image,0,0,row.quadrant%2*16,math.floor(row.quadrant/2)*16,16,16)
 assert(architectureHash(extracted:getString())==row.compositionPixelHash,'Actual Session bytes differ')
 for y=0,15 do for x=0,15 do local _,_,_,a=extracted:getPixel(x,y);assert(a==1,'Architecture contains a transparent hole')end end
 sessionCount=sessionCount+1;scenes[key].reviewed_building_cells=scenes[key].reviewed_building_cells+1
end
assert(state.rejected==0 and state.accepted==#architectureRows,'Rows failed live source/donor/session decoding')
return {composition_count=compositionCount,session_count=sessionCount,rejected=state.rejected,scenes=scenes}
''')
        scenes = {key.decode(): {name.decode(): val for name, val in scene.items()} for key, scene in result[b"scenes"].items()}
        report = {"status": "passed_private_production_Lua_byteproof", "reviewed_candidate_rows": len(rows), "unique_position_keys": len(keys),
                  "schema_errors": 0, "combined_active_mapping_rows": len(active) + len(rows),
                  "live_source_pixel_and_file_hashes_verified": checked, "distinct_live_source_files_verified": len(file_checks),
                  "live_native_full_and_selected_layer_hashes_verified": True,
                  "actual_production_compositions_verified": result[b"composition_count"],
                  "actual_positioned_session_cells_verified": result[b"session_count"], "session_rejected": result[b"rejected"],
                  "source_layout_collision_warps_unchanged": True, "new_assets": 0, "scenes": scenes,
                  "private_candidate_file_sha256": catalog.sha(args.rows.read_bytes()),
                  "limits": "Actual production Lua donor/composition/session exact-cell proof. Whole native features and roof masks are independently checked when prototypes regenerate. Native GPU/lighting verification remains separate."}
    finally:
        os.chdir(previous)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "scenes"}, indent=2))


if __name__ == "__main__":
    main()
