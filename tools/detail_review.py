"""Review the remaining Pallet lawn, garden fences and decorative flowers.

Default operation writes private comparison/provenance files only. Production
mapping rows are emitted only with --write-reviewed after the contact is reviewed.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import sys
import zlib

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE / ".tools/python"))
from PIL import Image, ImageDraw
import catalog
import preview
import validate_animation

ROLES = (
    ("short_nonencounter_grass", "Short non-encounter grass", (44, 44, 44, 44), 1),
    ("garden_fence_pair", "Garden fence pair", (14, 14, 85, 85), 644),
    ("decorative_flower_southeast", "Flower in lower-right corner", (44, 44, 44, 3), 4),
    ("decorative_flower_northwest", "Flower in upper-left corner", (3, 44, 44, 44), 4),
)


def lua(value):
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=True)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "{" + ",".join(lua(v) for v in value) + "}"
    if isinstance(value, dict):
        return "{" + ",".join("[" + lua(k) + "]=" + lua(v) for k, v in value.items()) + "}"
    raise TypeError(type(value))


def advanced_source(sheet, tileset, block, quadrant, world):
    output = Image.new("RGBA", (16, 16))
    ox, oy = quadrant % 2 * 2, quadrant // 2 * 2
    positions = (oy * 4 + ox, oy * 4 + ox + 1, (oy + 1) * 4 + ox, (oy + 1) * 4 + ox + 1)
    for i, position in enumerate(positions):
        tile_id = block[position]
        tile, _ = catalog.gb_tile(sheet, tileset, tile_id)
        group = world["tileGroups"]["OVERWORLD"][str(tile_id)]
        colors = world["groupColors"]["OVERWORLD"][group]
        tile.putdata([tuple(colors[0 if r > 211 else 1 if r > 127 else 2 if r > 43 else 3]) + (a,)
                      for r, g, b, a in tile.get_flattened_data()])
        output.paste(tile, (i % 2 * 8, i // 2 * 8))
    return output


def validate_native(mappings, args, mod):
    from lupa.luajit21 import LuaRuntime
    runtime = LuaRuntime(unpack_returned_tuples=True, encoding=None)
    cache = args.cache.resolve()

    def read(relative):
        path = (cache / relative.decode()).resolve()
        assert path.is_relative_to(cache)
        if not path.is_file():
            return None
        raw = path.read_bytes()
        if path.suffix in (".idx", ".rgba"):
            try:
                return zlib.decompress(raw)
            except zlib.error:
                pass
        return raw

    before = Path.cwd()
    try:
        os.chdir(args.engine.resolve())
        runtime.execute(validate_animation.IMAGE_FIXTURE.encode())

        def load_image(relative, _raw):
            with Image.open(cache / relative.decode()) as source:
                image = source.convert("RGBA")
                return runtime.globals()[b"makeData"](image.width, image.height, b"rgba8", image.tobytes())

        context = runtime.table_from({b"read": read, b"prefix": lambda game: game + b"/",
                                      b"hash": lambda raw: hashlib.sha256(raw).hexdigest().encode(),
                                      b"newImageData": runtime.globals()[b"makeData"], b"loadImage": load_image})
        donor_module = runtime.execute((mod / "lib/donor.lua").read_bytes())
        decoder = donor_module[b"new"](context)
        mapping = runtime.execute((mod / "lib/mapping.lua").read_bytes())
        session = runtime.execute((mod / "lib/session.lua").read_bytes())
        runtime.globals()[b"detailRows"] = runtime.execute(("return " + lua(mappings)).encode())
        runtime.globals()[b"detailMapping"] = mapping
        runtime.globals()[b"detailSession"] = session
        runtime.globals()[b"detailDecoder"] = decoder
        accepted = runtime.execute(br'''
local indexed,errors=detailMapping.index(detailRows);assert(#errors==0,table.concat(errors,'\n'))
local state=detailSession.new({mappings=indexed,donor=detailDecoder,newImageData=makeData,
  generations=detailMapping.generations,validate=detailMapping.validate,
  warn=function(message)error(message)end})
state:select('gen3')
for _,game in ipairs({'red','blue','yellow'})do
  local rows=state:replacements(game,'OVERWORLD',{id='PALLET_TOWN'})
  for _,block in pairs(rows)do
    if block.frames then
      assert(#block.frames==5 and block.period==16/60 and block.offset==2/60,
        'Flower timing differs from the native bank')
    end
  end
end
assert(state.rejected==0 and state.accepted==#detailRows,'Detail mapping did not decode completely')
return state.accepted
''')
        flower = next(row for row in mappings if row.get("animated"))
        ref = runtime.execute(("return " + lua(flower["donor"])).encode())
        recipe = runtime.execute(("return " + lua(flower["animation"])).encode())
        base = decoder[b"cell"](decoder, ref)
        sequence = decoder[b"frames"](decoder, ref, recipe)
        assert not isinstance(base, tuple) and not isinstance(sequence, tuple), (base, sequence)
        assert len(sequence[b"frames"]) == 5
        for name in runtime.eval(b"package.loaded").keys():
            assert not name.startswith((b"src.core.game3.", b"src.world.gen2.")), name
        runtime.globals()[b"readImported"] = read
        runtime.globals()[b"selectedGame"] = b"firered"
        runtime.globals()[b"selectedPair"] = b"pallet_outdoor"
        runtime.globals()[b"selectedMid"] = 4
        runtime.globals()[b"base"] = base
        runtime.globals()[b"sequence"] = sequence
        snapshots = runtime.execute(validate_animation.COMPARE.encode())
        return {"decoded_rows": accepted, "rejected": 0, "native_flower_layer_snapshots": snapshots,
                "frames": 5, "ticks": 16, "phase": 2, "source_generation_runtime_loaded": False}
    finally:
        os.chdir(before)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path(catalog.os.environ["APPDATA"]) / "pokemon-love2d")
    parser.add_argument("--engine", type=Path, default=WORKSPACE / ".tools/engine-0395")
    parser.add_argument("--output", type=Path, default=WORKSPACE / ".work/tileshift-detail-review")
    parser.add_argument("--grass-mid", type=int, choices=(1, 17), default=1)
    parser.add_argument("--write-reviewed", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    mod = WORKSPACE / "TileShift"
    pair = "pallet_outdoor"
    native_root = args.cache / "firered/data/generated/gba/native" / pair
    manifest_bytes = (native_root / "anim_manifest.lua").read_bytes()
    manifest = catalog.read_lua(native_root / "anim_manifest.lua")
    raw = (native_root / "anim_flower.rgba").read_bytes()
    try:
        raw = zlib.decompress(raw)
    except zlib.error:
        pass
    bank = manifest["flower"]
    assert bank["frames"] == 5 and 4 in bank["mids"]
    assert len(raw) == len(bank["mids"]) * 5 * 1024
    flower_index = bank["mids"].index(4)
    flower_frames = [Image.frombytes("RGBA", (16, 16), raw[(f * len(bank["mids"]) + flower_index) * 1024:
                                                            (f * len(bank["mids"]) + flower_index + 1) * 1024]) for f in range(5)]
    flower_recipe = {"bank": "flower", "hash": catalog.sha(raw), "manifestHash": catalog.sha(manifest_bytes),
                     "counter": "global", "counterMax": 640, "period": 16, "phase": 2, "frames": 5,
                     "format": "rgba8", "frame0Hash": catalog.sha(flower_frames[0].tobytes())}
    target_catalog = json.loads((WORKSPACE / ".work/tileshift-catalog/firered.json").read_text())
    targets = {r["mid"]: {"game": "firered", "tileset": pair, "id": r["mid"], "hash": r["pixel_sha256"]}
               for r in target_catalog["cells"] if r["pair"] == pair}
    packed = {}
    target_images = {mid: preview.native_donor(args.cache, targets[mid], packed) for mid in (1, 17, 644, 4)}
    advanced_path = args.engine / "data/palettes_gbc.lua"
    world = catalog.read_lua(advanced_path)["world"]
    assert world["tileGroups"]["OVERWORLD"]["44"] == 2
    assert world["tileGroups"]["OVERWORLD"]["35"] == 0
    records, mappings, contact = [], [], {}
    role_ids = {raw_ids: (role, label, args.grass_mid if role == "short_nonencounter_grass" else mid)
                for role, label, raw_ids, mid in ROLES}
    for game in ("red", "blue", "yellow"):
        map_file = args.cache / game / "data/generated/maps.lua"
        tileset_file = args.cache / game / "data/generated/tilesets.lua"
        definition = catalog.read_lua(map_file)["PALLET_TOWN"]
        tileset = catalog.read_lua(tileset_file)[definition["tileset"]]
        sheet_path = args.cache / game / tileset["image"]
        atlas = Image.open(sheet_path).convert("RGBA")
        found = defaultdict(list)
        for index, block_id in enumerate(definition["blocks"]):
            block = tileset["blocks"][block_id]
            for quadrant in range(4):
                ox, oy = quadrant % 2 * 2, quadrant // 2 * 2
                ids = tuple(block[p] for p in (oy * 4 + ox, oy * 4 + ox + 1, (oy + 1) * 4 + ox, (oy + 1) * 4 + ox + 1))
                if ids in role_ids:
                    found[block_id, quadrant, ids].append([index % definition["width"] * 2 + quadrant % 2,
                                                          index // definition["width"] * 2 + quadrant // 2])
        for (block_id, quadrant, ids), coordinates in sorted(found.items()):
            role, label, mid = role_ids[ids]
            source = preview.native_cell(atlas, tileset, tileset["blocks"][block_id], quadrant)
            source_color = advanced_source(atlas, tileset, tileset["blocks"][block_id], quadrant, world)
            contact.setdefault((game, role), (source, source_color, block_id, quadrant))
            assert ids[2] in tileset["walkable"] or role == "garden_fence_pair"
            assert tileset["grassTile"] not in ids, "Decorative grass cannot become tall encounter grass"
            row = {"game": game, "style": "gen3", "tileset": "OVERWORLD", "map": "PALLET_TOWN",
                   "id": block_id, "quadrant": quadrant, "role": role,
                   "status": "reviewed" if args.write_reviewed else "candidate", "sourceHash": catalog.sha(source.tobytes()),
                   "sourceFiles": {"metadata": catalog.sha(tileset_file.read_bytes()), "image": catalog.sha(sheet_path.read_bytes()),
                                   "maps": catalog.sha(map_file.read_bytes())}, "donor": targets[mid],
                   "evidence": f"Native {game} PALLET_TOWN {label.lower()} at16px cells {coordinates}. Exact8px source-tile tuple {list(ids)} and footprint reviewed against native FireRed Pallet art; source collision and encounter flags remain native."}
            if mid == 4:
                row.update(animated=True, animation=flower_recipe)
            mappings.append(row)
            records.append({"game": game, "role": role, "block": block_id, "quadrant": quadrant,
                            "coordinates": coordinates, "source_tiles": list(ids), "cellTile": ids[2],
                            "walkable": ids[2] in tileset["walkable"], "encounter_grass": False,
                            "sourceHash": row["sourceHash"], "donor": targets[mid]})
    assert len(mappings) == 57
    counts = {game: sum(len(r["coordinates"]) for r in records if r["game"] == game) for game in ("red", "blue", "yellow")}
    assert set(counts.values()) == {80}
    canvas = Image.new("RGB", (1120, 950), "#18202c")
    draw = ImageDraw.Draw(canvas)
    draw.text((12, 9), "Pallet detail checkpoint: native Gen3 lawn, garden fences and flowers", fill="white")
    draw.text((12, 29), "Review candidate only:80 source cells per game,57 scoped mapping aliases across Red/Blue/Yellow.", fill="#ced7e4")
    draw.text((12, 49), "Source meaning uses pixels, placement and Advanced color groups. Source44 is green short grass; encounter grass is82.", fill="#ced7e4")
    for i, (role, label, ids, mid) in enumerate(ROLES):
        y = 95 + i * 200
        draw.text((12, y), label, fill="white")
        draw.text((12, y + 21), f"source IDs {list(ids)}", fill="#ced7e4")
        for j, game in enumerate(("red", "yellow")):
            gray, colored, block_id, quadrant = contact[game, role]
            for k, image in enumerate((gray, colored)):
                x = 12 + j * 220 + k * 104
                canvas.paste(image.resize((96, 96), Image.Resampling.NEAREST), (x, y + 48))
                draw.text((x, y + 146), f"{game} {block_id}:{quadrant}" if k == 0 else "Advanced", fill="#ced7e4")
        if mid == 4:
            for frame, image in enumerate(flower_frames):
                x = 480 + frame * 123
                canvas.paste(image.resize((112, 112), Image.Resampling.NEAREST), (x, y + 28))
                draw.text((x, y + 143), f"native frame{frame}", fill="#ced7e4")
            draw.text((480, y + 165), "FireRed4 uses a complete16px flowerbed cell; Gen1's flower is one8px corner.", fill="#e8ce95")
            draw.text((480, y + 181), "Review the denser bloom inside the unchanged bed footprint. Five frames,16ticks,phase2.", fill="#e8ce95")
        else:
            candidates = (1, 17) if role == "short_nonencounter_grass" else (644,)
            for j, candidate in enumerate(candidates):
                x = 490 + j * 200
                canvas.paste(target_images[candidate].resize((112, 112), Image.Resampling.NEAREST), (x, y + 28))
                draw.text((x, y + 143), f"FireRed {candidate}", fill="white")
            if role == "short_nonencounter_grass":
                draw.text((490, y + 169), "1: general short lawn. 17: same grass used within native Pallet.", fill="#ced7e4")
            else:
                draw.text((490, y + 169), "644 is the native Pallet flower-garden fence at x5..8,y11.", fill="#ced7e4")
    canvas.save(args.output / "pallet-details-comparison.png")
    report = {"status": "reviewed" if args.write_reviewed else "awaiting_visual_review", "physical_cells_per_game": counts,
              "mapping_aliases": len(mappings), "roles": records, "flower_animation": flower_recipe,
              "advanced_palette_evidence": {"path": str(advanced_path.resolve()), "sha256": catalog.sha(advanced_path.read_bytes()),
                                            "source44group": 2, "source35group": 0, "source_encounter_grass_tile": 82},
              "mappings": mappings}
    if args.write_reviewed:
        report["validation"] = validate_native(mappings, args, mod)
    (args.output / "detail-candidates.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.write_reviewed:
        target = mod / "mappings/pallet_details.lua"
        target.write_text("-- Reviewed Pallet lawn, garden fences and flowers; native Gen3 donors.\n"
                          "-- Scoped Red/Blue/Yellow only. No map, collision or encounter edits.\nreturn {\n" +
                          "\n".join("  " + lua(row) + "," for row in mappings) + "\n}\n", encoding="utf-8")
    print(f"Prepared {len(mappings)} aliases,80 cells per source map; comparison {args.output / 'pallet-details-comparison.png'}")
    print("Production mapping written." if args.write_reviewed else "No production mapping was created; visual review is pending.")


if __name__ == "__main__":
    main()
