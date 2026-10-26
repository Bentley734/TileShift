"""Inventory and privately review New Bark Town's native outdoor tiles.

No mappings are activated by the inventory command. Imported images stay in
.work, and source hashes always use uncolored, bank/flip-correct native pixels.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import struct

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE / ".tools/python"))
from PIL import Image, ImageDraw, ImageFont
import catalog
import preview
import detail_review
import shoreline_review

GAMES = ("gold", "silver", "crystal")
MAP_ID = "NEW_BARK_TOWN"
PAIR = "general__petalburg"
SPECS = {
    (5, 5, 5, 5): ("short_nonencounter_grass", 1),
    (5, 5, 5, 3): ("decorative_flower_southeast", 4),
    (3, 5, 5, 5): ("decorative_flower_northwest", 4),
    (30, 31, 46, 47): ("dense_conifer_crown", 14),
    (46, 47, 62, 63): ("dense_conifer_trunk", 22),
    (92, 76, 61, 20): ("rocky_coast_northwest", 392),
    (76, 76, 20, 20): ("rocky_coast_north", 393),
    (61, 20, 61, 20): ("rocky_coast_west", 44),
}


def existing_rows(mod):
    rows = []
    for path in sorted((mod / "mappings").glob("*.lua")):
        if path.name == "gen2_outdoor.lua":
            continue
        rows.extend(preview.read_reviewed(path))
    return rows


def source_inventory(cache, game, rows, output):
    root = cache / game
    maps_path, tilesets_path = root / "data/generated/maps.lua", root / "data/generated/tilesets.lua"
    definition = catalog.read_lua(maps_path)[MAP_ID]
    tileset = catalog.read_lua(tilesets_path)[definition["tileset"]]
    atlas_path = root / tileset["image"]
    atlas = Image.open(atlas_path).convert("RGBA")
    palettes = preview.palette_set(catalog.read_lua(root / "data/generated/palettes.lua"), definition)
    roofs = catalog.read_lua(root / "data/generated/roofs.lua")
    roof_name = catalog.dict_at(roofs["mapGroupRoofs"], definition["group"])
    roof_spec = roofs["roofs"].get(roof_name)
    roof = Image.open(root / roof_spec["image"]) if roof_spec else None
    selected = {}
    for row in sorted(rows, key=lambda row: bool(row.get("map"))):
        if row["game"] == game and row["style"] == "gen3" and row["tileset"] == definition["tileset"] and row.get("map", MAP_ID) == MAP_ID:
            selected[row["id"], row["quadrant"]] = row
    coordinates = defaultdict(list)
    for pos, block_id in enumerate(catalog.lua_array(definition["blocks"])):
        for q in range(4):
            coordinates[block_id, q].append([pos % definition["width"] * 2 + q % 2, pos // definition["width"] * 2 + q // 2])
    images, records = {}, []
    for (block_id, q), cells in sorted(coordinates.items()):
        block = catalog.lua_array(catalog.dict_at(tileset["blocks"], block_id + 1))
        image = preview.native_cell(atlas, tileset, block, q, palettes, roof)
        raw = preview.native_cell(atlas, tileset, block, q)
        ox, oy = q % 2 * 2, q // 2 * 2
        offsets = (oy * 4 + ox, oy * 4 + ox + 1, (oy + 1) * 4 + ox, (oy + 1) * 4 + ox + 1)
        tile_ids = [block[i] for i in offsets]
        attrs = [catalog.gb_tile(atlas, tileset, tile_id)[1] for tile_id in tile_ids]
        collision = catalog.lua_array(catalog.dict_at(tileset["collision"], block_id + 1))[q]
        images[block_id, q] = image
        records.append({"game": game, "tileset": definition["tileset"], "map": MAP_ID,
                        "id": block_id, "quadrant": q, "tiles": tile_ids, "attributes": attrs,
                        "collision": collision, "sourceHash": catalog.sha(raw.tobytes()),
                        "coordinates": cells, "count": len(cells), "covered": (block_id, q) in selected,
                        "existingRole": selected.get((block_id, q), {}).get("role")})
    native = Image.new("RGBA", (definition["width"] * 32, definition["height"] * 32))
    for row in records:
        for x, y in row["coordinates"]:
            native.paste(images[row["id"], row["quadrant"]], (x * 16, y * 16))
    native.save(output / f"{game}-newbark-native.png")
    grid = Image.new("RGB", (native.width * 3 + 70, native.height * 3 + 65), "#18202c")
    grid.paste(native.resize((native.width * 3, native.height * 3), Image.Resampling.NEAREST), (55, 45))
    draw = ImageDraw.Draw(grid)
    for x in range(native.width // 16):
        draw.text((55 + x * 48 + 15, 25), str(x), fill="white")
    for y in range(native.height // 16):
        draw.text((28, 45 + y * 48 + 15), str(y), fill="white")
    for row in records:
        for x, y in row["coordinates"]:
            color = "#55e3bd" if row["covered"] else "#f0ad80"
            draw.rectangle((55 + x * 48, 45 + y * 48, 55 + (x + 1) * 48, 45 + (y + 1) * 48), outline=color)
    draw.text((8, 5), f"{game} / New Bark Town native DAY; green = already covered, orange = remaining", fill="white")
    grid.save(output / f"{game}-newbark-grid.png")
    columns, cw, ch = 8, 156, 148
    contact = Image.new("RGB", (columns * cw, math.ceil(len(records) / columns) * ch + 50), "#18202c")
    draw = ImageDraw.Draw(contact)
    draw.text((12, 10), f"{game}: all used New Bark Town source aliases. Counts are physical map cells.", fill="white")
    for i, row in enumerate(records):
        x, y = i % columns * cw + 12, i // columns * ch + 45
        contact.paste(images[row["id"], row["quadrant"]].resize((64, 64), Image.Resampling.NEAREST), (x, y))
        draw.text((x + 69, y), f"{row['id']}:{row['quadrant']}", fill="white")
        draw.text((x + 69, y + 17), f"count {row['count']}", fill="white")
        draw.text((x + 69, y + 34), f"col {row['collision']:02x}", fill="white")
        draw.text((x, y + 70), " ".join(map(str, row["tiles"])), fill="#ccd7e5")
        draw.text((x, y + 87), "covered" if row["covered"] else "REMAINING", fill="#55e3bd" if row["covered"] else "#f0ad80")
        draw.text((x, y + 104), f"at {row['coordinates'][0]}", fill="#ccd7e5")
    contact.save(output / f"{game}-newbark-source-aliases.png")
    fingerprints = {"metadata": catalog.sha(tilesets_path.read_bytes()), "image": catalog.sha(atlas_path.read_bytes()), "maps": catalog.sha(maps_path.read_bytes())}
    return {"game": game, "map": MAP_ID, "tileset": definition["tileset"], "sourceFiles": fingerprints,
            "visible_cells": sum(row["count"] for row in records),
            "covered_cells": sum(row["count"] for row in records if row["covered"]), "cells": records}


def donor_contact(cache, game, pair, mids, output):
    cat = json.loads((WORKSPACE / ".work/tileshift-catalog" / f"{game}.json").read_text())
    hashes = {row["mid"]: row["pixel_sha256"] for row in cat["cells"] if row["pair"] == pair}
    packed = {}
    columns, cw, ch = 10, 98, 105
    image = Image.new("RGB", (columns * cw, math.ceil(len(mids) / columns) * ch + 45), "#18202c")
    draw = ImageDraw.Draw(image)
    draw.text((10, 10), f"Native donor candidates: {game} / {pair}. Static images; animation needs separate review.", fill="white")
    for i, mid in enumerate(mids):
        if mid not in hashes:
            continue
        donor = preview.native_donor(cache, {"game": game, "tileset": pair, "id": mid, "hash": hashes[mid]}, packed)
        x, y = i % columns * cw + 10, i // columns * ch + 40
        image.paste(donor.resize((80, 80), Image.Resampling.NEAREST), (x, y))
        draw.text((x, y + 82), str(mid), fill="white")
    image.save(output / f"{game}-{pair}-donor-candidates.png")


def candidates(cache, inventories):
    cat = json.loads((WORKSPACE / ".work/tileshift-catalog/emerald.json").read_text())
    hashes = {row["mid"]: row["pixel_sha256"] for row in cat["cells"] if row["pair"] == PAIR}
    root = cache / "emerald/data/generated/gba/native" / PAIR
    manifest_bytes = (root / "anim_manifest.lua").read_bytes()
    manifest = catalog.read_lua(root / "anim_manifest.lua")
    banks = {row["name"]: row for row in manifest["banks"]}
    rows = []
    for inventory in inventories:
        for cell in inventory["cells"]:
            match = SPECS.get(tuple(cell["tiles"]))
            if not match or cell["covered"]:
                continue
            role, mid = match
            row = {"game": inventory["game"], "style": "gen3", "map": MAP_ID, "tileset": inventory["tileset"],
                   "id": cell["id"], "quadrant": cell["quadrant"], "sourceHash": cell["sourceHash"],
                   "sourceFiles": inventory["sourceFiles"], "role": role, "status": "reviewed",
                   "donor": {"game": "emerald", "tileset": PAIR, "id": mid, "hash": hashes[mid]},
                   "evidence": f"New Bark Town-only native visual counterpart. Source16px cells {cell['coordinates']}; native collision0x{cell['collision']:02x}, banks, flips and per-cartridge pixels checked. "}
            if role.startswith("dense_conifer"):
                row["evidence"] += "The complete16x32 source boundary tree retains a16x16 crown above a16x16 trunk. Emerald14+22 are a complete native16x32 tree pair; no clipping, reshaping or scaling."
            elif role == "short_nonencounter_grass":
                row["evidence"] += "Low grassy plot, without the encounter-grass blades of source collision0x18. Native Emerald1 is non-encounter lawn and matches the existing town ground and flower background."
            elif role.startswith("decorative_flower"):
                row["evidence"] += "Decorative corner-flower bed becomes the native complete16px flower cell within the same source cell. All four native flower frames retain the flower role; source encounters remain unchanged."
            else:
                row["evidence"] += "Brown rocky ocean bank, visually matched by corner and handedness. Native Emerald water52 interiors are already installed in this map, so these edge cells use the same palette, wave bank and schedule."
            bank_name = "general_flower" if mid == 4 else "general_water" if role.startswith("rocky_coast") else None
            if bank_name:
                bank = banks[bank_name]
                blob = shoreline_review.unpack(root / bank["file"])
                slot = bank["mids"].index(mid)
                row["animated"] = True
                row["animation"] = {"bank": bank_name, "hash": catalog.sha(blob), "manifestHash": catalog.sha(manifest_bytes),
                                    "period": bank["period"], "phase": bank["phase"], "frames": bank["frames"],
                                    "counter": bank["counter"], "counterMax": manifest["counters"][bank["counter"]]["max"],
                                    "quadMask": bank["quads"][slot]}
            rows.append(row)
    return rows


def candidate_frames(cache, row, packed):
    if not row.get("animated"):
        return [preview.native_donor(cache, row["donor"], packed)]
    ref, spec = row["donor"], row["animation"]
    root = cache / ref["game"] / "data/generated/gba/native" / ref["tileset"]
    palette = catalog.read_palettes(root / "palettes.bin")
    mids, pixels, _ = catalog.read_idx(root / "mids.idx")
    over_mids, over_pixels, _ = catalog.read_idx(root / "mids_over.idx")
    assert mids == over_mids
    slot = mids.index(ref["id"])
    under = catalog.rgba_native(pixels[slot * 256:(slot + 1) * 256], palette)
    over = catalog.rgba_native(over_pixels[slot * 256:(slot + 1) * 256], palette, True)
    manifest = catalog.read_lua(root / "anim_manifest.lua")
    assert catalog.sha((root / "anim_manifest.lua").read_bytes()) == spec["manifestHash"]
    bank = next(bank for bank in manifest["banks"] if bank["name"] == spec["bank"])
    assert catalog.sha(shoreline_review.unpack(root / bank["file"])) == spec["hash"]
    return shoreline_review.native_frames(root, ref["id"], under, over, bank, palette)


def review_contact(cache, inventory, rows, output):
    root = cache / inventory["game"]
    ts = catalog.read_lua(root / "data/generated/tilesets.lua")[inventory["tileset"]]
    definition = catalog.read_lua(root / "data/generated/maps.lua")[MAP_ID]
    palette = preview.palette_set(catalog.read_lua(root / "data/generated/palettes.lua"), definition)
    atlas = Image.open(root / ts["image"]).convert("RGBA")
    selected = {row["role"]: row for row in rows if row["game"] == inventory["game"]}
    source_rows = {row["role"]: next(cell for cell in inventory["cells"] if cell["id"] == row["id"] and cell["quadrant"] == row["quadrant"]) for row in selected.values()}
    packed = {}
    roles = ("short_nonencounter_grass", "decorative_flower_southeast", "decorative_flower_northwest", "dense_conifer_crown", "dense_conifer_trunk", "rocky_coast_northwest", "rocky_coast_north", "rocky_coast_west")
    image = Image.new("RGB", (1360, len(roles) * 168 + 70), "#18202c")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 17)
    draw.text((15, 12), "New Bark Town outdoor comparison — native16px cells; no map geometry edits", font=font, fill="white")
    draw.text((15, 40), "All animation frames shown. Dense tree crown and trunk remain a complete16x32 pair. Cuttable trees reviewed separately.", fill="#ccd7e5")
    for index, role in enumerate(roles):
        row, source = selected[role], source_rows[role]
        block = catalog.lua_array(catalog.dict_at(ts["blocks"], row["id"] + 1))
        original = preview.native_cell(atlas, ts, block, row["quadrant"], palette)
        y = index * 168 + 75
        image.paste(original.resize((96, 96), Image.Resampling.NEAREST), (20, y))
        draw.text((130, y), role.replace("_", " "), font=font, fill="white")
        draw.text((130, y + 24), f"Source {row['id']}:{row['quadrant']} / tiles{source['tiles']}", fill="#ccd7e5")
        draw.text((130, y + 44), f"Map cells{source['coordinates']} / collision0x{source['collision']:02x}", fill="#ccd7e5")
        draw.text((130, y + 64), f"Emerald {row['donor']['id']} / {PAIR}", fill="#e5ce9a")
        frames = candidate_frames(cache, row, packed)
        for frame, candidate in enumerate(frames):
            x = 490 + frame * 105
            image.paste(candidate.resize((88, 88), Image.Resampling.NEAREST), (x, y))
            draw.text((x, y + 92), f"frame {frame}", fill="#ccd7e5")
        if role == "short_nonencounter_grass":
            draw.text((490, y + 115), "Native lawn1 keeps the existing town ground and flower backgrounds seamless.", fill="#e5ce9a")
        if role.startswith("dense_conifer"):
            draw.text((490, y + 115), "Crown14 + trunk22: retain the original two-cell tree height, width and blocking cells.", fill="#e5ce9a")
    image.save(output / "newbark-outdoor-candidates.png")


def headbutt_contact(cache, inventory, output, approved=False):
    image = Image.new("RGB", (1100, 300), "#18202c")
    draw = ImageDraw.Draw(image)
    draw.text((15, 12), "New Bark small Headbutt tree vs native Gen3 cuttable-tree silhouettes", fill="white")
    root = cache / inventory["game"]
    definition = catalog.read_lua(root / "data/generated/maps.lua")[MAP_ID]
    ts = catalog.read_lua(root / "data/generated/tilesets.lua")[inventory["tileset"]]
    atlas = Image.open(root / ts["image"])
    palettes = preview.palette_set(catalog.read_lua(root / "data/generated/palettes.lua"), definition)
    block = catalog.lua_array(catalog.dict_at(ts["blocks"], 99))
    original = preview.native_cell(atlas, ts, block, 1, palettes)
    image.paste(original.resize((144, 144), Image.Resampling.NEAREST), (20, 65))
    draw.text((20, 220), "Crystal98:1 / Headbutt0x15", fill="white")
    records = []
    for x, game, gid in ((250, "emerald", 82), (500, "firered", 95), (750, "leafgreen", 95)):
        base = cache / game / "data/generated/gba/ow"
        meta = (base / f"{gid}.meta").read_bytes()
        raw = shoreline_review.unpack(base / f"{gid}.rgba")
        assert meta[:4] == b"SVOW" and meta[4] == 4
        native_id, w, h, frames = struct.unpack_from("<4H", meta, 6)
        assert native_id == gid and len(raw) == w * h * frames * 4
        frame = Image.frombytes("RGBA", (w, h), raw[:w * h * 4])
        bounds = frame.getchannel("A").getbbox()
        frame.save(output / f"{game}-cuttable-tree-{gid}-frame0.png")
        background = Image.new("RGBA", (w, h), "#73c5a5")
        background = Image.alpha_composite(background, frame)
        image.paste(background.resize((144, 144), Image.Resampling.NEAREST), (x, 65))
        draw.text((x, 220), f"{game} object{gid}", fill="white")
        draw.text((x, 238), f"canvas{w}x{h}, alpha bbox{bounds}", fill="#ccd7e5")
        records.append({"game": game, "id": gid, "width": w, "height": h, "frames": frames,
                        "frame": 0, "alphaBounds": bounds, "metaHash": catalog.sha(meta),
                        "rgbaHash": catalog.sha(raw), "pixelHash": catalog.sha(frame.tobytes())})
    note = ("User selected Emerald82 native small-tree art. Source0x15 remains Headbutt; original interactions and screen shake stay native."
            if approved else "All silhouettes fit16x16. Source0x15 is Headbutt, not Cut; graphic choice needs explicit review. Source interaction stays native.")
    draw.text((15, 275), note, fill="#e5ce9a")
    image.save(output / "newbark-cuttable-tree-native.png")
    (output / "native-cuttable-tree-refs.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    return records


def headbutt_mappings(inventories, refs):
    selected = next(ref for ref in refs if ref["game"] == "emerald")
    donor = {"game": "emerald", "kind": "field_object", "tileset": "ow", "id": selected["id"], "frame": 0,
             "hash": selected["pixelHash"], "metaHash": selected["metaHash"], "rgbaHash": selected["rgbaHash"]}
    base = {"game": "emerald", "tileset": PAIR, "id": 1,
            "hash": "1c7acc0ebc7c5878e77e1dfbbc2828e1a2745c0ded470f1f0152f67193222ed1"}
    rows = []
    for inventory in inventories:
        for cell in inventory["cells"]:
            if tuple(cell["tiles"]) != (30, 31, 62, 63) or cell["covered"]:
                continue
            assert cell["collision"] == 0x15
            rows.append({"game": inventory["game"], "style": "gen3", "map": MAP_ID, "tileset": inventory["tileset"],
                         "id": cell["id"], "quadrant": cell["quadrant"], "sourceHash": cell["sourceHash"],
                         "sourceFiles": inventory["sourceFiles"], "sourceCollision": cell["collision"],
                         "role": "headbutt_small_tree", "status": "reviewed",
                         "kind": "native_composite", "base": base,
                         "parts": [{"donor": donor, "srcX": 0, "srcY": 0, "w": 16, "h": 16, "x": 0, "y": 0}],
                         "evidence": f"Native New Bark small Headbutt-tree16px cells {cell['coordinates']}, source collision0x15 (Permissions.HEADBUTT_TREE, not Cut0x12/0x1a). Gen3 has no field Headbutt-tree mechanic. User selected the native Emerald small-tree visual treatment: complete16x16 cuttable-tree object82 frame0, alpha silhouette bbox(1,1,16,16), without clipping or scaling. Neutral SVOW4 metadata, full decodedRGBA and frame pixels are independently hashed. Alpha is composed over native Emerald1 ground. Original Headbutt interaction, encounters, blocking and native whole-frame earthquake shake remain source-owned; no donor mechanic is imported."})
    return rows


def validate_native(rows, args, mod):
    from lupa.luajit21 import LuaRuntime
    runtime = LuaRuntime(unpack_returned_tuples=True, encoding=None)
    cache = args.cache.resolve()
    def read(relative):
        path = (cache / relative.decode()).resolve()
        assert path.is_relative_to(cache)
        if not path.is_file():
            return None
        return shoreline_review.unpack(path) if path.suffix in (".idx", ".rgba") else path.read_bytes()
    before = Path.cwd()
    try:
        os.chdir(args.engine.resolve())
        runtime.execute(detail_review.validate_animation.IMAGE_FIXTURE.encode())
        def load_image(relative, _raw):
            source = Image.open(cache / relative.decode()).convert("RGBA")
            return runtime.globals()[b"makeData"](source.width, source.height, b"rgba8", source.tobytes())
        context = runtime.table_from({b"read": read, b"prefix": lambda game: game + b"/",
                                      b"hash": lambda raw: hashlib.sha256(raw).hexdigest().encode(),
                                      b"newImageData": runtime.globals()[b"makeData"], b"loadImage": load_image})
        decoder = runtime.execute((mod / "lib/donor.lua").read_bytes())[b"new"](context)
        composition = runtime.execute((mod / "lib/composition.lua").read_bytes())[b"new"](
            runtime.table_from({b"donor": decoder, b"newImageData": runtime.globals()[b"makeData"]}))
        runtime.globals()[b"outdoorRows"] = runtime.execute(("return " + detail_review.lua(rows)).encode())
        runtime.globals()[b"outdoorMapping"] = runtime.execute((mod / "lib/mapping.lua").read_bytes())
        runtime.globals()[b"outdoorSession"] = runtime.execute((mod / "lib/session.lua").read_bytes())
        runtime.globals()[b"outdoorDecoder"] = decoder
        runtime.globals()[b"outdoorComposer"] = composition
        accepted = runtime.execute(br'''
local indexed,errors=outdoorMapping.index(outdoorRows);assert(#errors==0,table.concat(errors,'\n'))
local state=outdoorSession.new({mappings=indexed,donor=outdoorDecoder,newImageData=makeData,
  generations=outdoorMapping.generations,validate=outdoorMapping.validate,
  compose=function(row)return outdoorComposer:cell(row)end,warn=function(message)error(message)end})
state:select('gen3')
local groups={}
for _,row in ipairs(outdoorRows)do
  local key=row.game..':'..row.tileset
  groups[key]=groups[key] or {game=row.game,tileset=row.tileset,id='OUTDOOR_REVIEW'}
  if row.map then groups[key].id=row.map end
end
for _,group in pairs(groups)do
  assert(state:replacements(group.game,group.tileset,{id=group.id}))
end
assert(state.rejected==0 and state.accepted==#outdoorRows,'Outdoor mappings did not decode completely')
return state.accepted
''')
        for name in runtime.eval(b"package.loaded").keys():
            assert not name.startswith((b"src.core.game3.", b"src.world.gen2.")), name
        checked_objects = set()
        for row in rows:
            for part in row.get("parts", []):
                donor = part["donor"]
                if donor.get("kind") != "field_object":
                    continue
                identity = donor["game"], donor["id"], donor.get("frame", 0), donor["hash"]
                if identity in checked_objects:
                    continue
                checked_objects.add(identity)
                ref = runtime.execute(("return " + detail_review.lua(donor)).encode())
                piece = decoder[b"cell"](decoder, ref)
                assert not isinstance(piece, tuple), piece
                picture = preview.native_field_object(args.cache, donor, {})
                assert picture.tobytes() == piece[b"under"][b"getString"](piece[b"under"])
        checked_refs, snapshots, frame_images = set(), 0, 0
        for row in rows:
            if not row.get("animated"):
                continue
            identity = row["donor"]["game"], row["donor"]["id"], row["animation"]["bank"]
            if identity in checked_refs:
                continue
            checked_refs.add(identity)
            ref = runtime.execute(("return " + detail_review.lua(row["donor"])).encode())
            spec = runtime.execute(("return " + detail_review.lua(row["animation"])).encode())
            base = decoder[b"cell"](decoder, ref)
            sequence = decoder[b"frames"](decoder, ref, spec)
            assert not isinstance(base, tuple) and not isinstance(sequence, tuple), (base, sequence)
            pictures = preview.native_water_frames(args.cache, row, {})
            for index, picture in enumerate(pictures, 1):
                piece = sequence[b"frames"][index]
                under = Image.frombytes("RGBA", (16, 16), piece[b"under"][b"getString"](piece[b"under"]))
                over = Image.frombytes("RGBA", (16, 16), piece[b"over"][b"getString"](piece[b"over"]))
                assert picture.tobytes() == Image.alpha_composite(under, over).tobytes(), identity
                frame_images += 1
            runtime.globals()[b"readImported"] = read
            runtime.globals()[b"selectedGame"] = row["donor"]["game"].encode()
            runtime.globals()[b"selectedPair"] = row["donor"]["tileset"].encode()
            runtime.globals()[b"selectedMid"] = row["donor"]["id"]
            runtime.globals()[b"base"], runtime.globals()[b"sequence"] = base, sequence
            snapshots += runtime.execute(detail_review.validate_animation.COMPARE.encode())
        return {"session_rows_accepted": accepted, "rejected": 0, "native_animation_layer_snapshots": snapshots,
                "preview_vs_donor_frame_images": frame_images, "native_object_frames_checked": len(checked_objects),
                "neutral_before_native_animation_check": True}
    finally:
        os.chdir(before)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path(os.environ["APPDATA"]) / "pokemon-love2d")
    parser.add_argument("--output", type=Path, default=WORKSPACE / ".work/tileshift-gen2-outdoor-review")
    parser.add_argument("--engine", type=Path, default=WORKSPACE / ".tools/engine-0395")
    parser.add_argument("--include-headbutt-trees", action=argparse.BooleanOptionalAction, default=True,
                        help="Include the approved small Headbutt-tree visual treatment (default: enabled)")
    parser.add_argument("--write-reviewed", action="store_true", help="Validate and write the approved map-scoped data file")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rows = existing_rows(WORKSPACE / "TileShift")
    records = [source_inventory(args.cache, game, rows, args.output) for game in GAMES]
    donor_contact(args.cache, "emerald", "general__petalburg", list(range(80)) + list(range(128, 176)) + [283, 284, 285, 291, 392, 393, 394], args.output)
    donor_contact(args.cache, "firered", "pallet_outdoor", list(range(80)) + [291, 298, 299, 300, 644, 721, 722], args.output)
    (args.output / "source-inventory.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    staged = candidates(args.cache, records)
    review_contact(args.cache, records[-1], staged, args.output)
    object_refs = headbutt_contact(args.cache, records[-1], args.output, args.include_headbutt_trees)
    if args.include_headbutt_trees:
        staged.extend(headbutt_mappings(records, object_refs))
    (args.output / "candidate-mappings.json").write_text(json.dumps(staged, indent=2), encoding="utf-8")
    mod = WORKSPACE / "TileShift"
    if args.write_reviewed:
        target = mod / "mappings/gen2_outdoor.lua"
        owned_roles = {role for role, mid in SPECS.values()} | {"headbutt_small_tree"}
        preserved = [row for row in preview.read_reviewed(target) if row["role"] not in owned_roles] if target.is_file() else []
        production = staged + preserved
        validation = validate_native(production, args, mod)
        target.write_text("-- Reviewed Gen2 outdoor terrain and interaction-tree graphics.\n"
                          "-- New Bark terrain/Headbutt rows are map-scoped; verified Cut aliases retain original map use.\n"
                          "-- Native Gen3 imports only. All source gameplay remains native.\nreturn {\n" +
                          "\n".join("  " + detail_review.lua(row) + "," for row in production) + "\n}\n", encoding="utf-8")
        (args.output / "native-validation.json").write_text(json.dumps(validation, indent=2), encoding="utf-8")
        print(json.dumps(validation))
        packed = {}
        reports = [preview.map_preview(args.cache, args.output, game, MAP_ID, f"{game}-newbark", rows + production, packed, 2, mod) for game in GAMES]
        (args.output / "map-validation.json").write_text(json.dumps(reports, indent=2), encoding="utf-8")
    for record in records:
        print(f"{record['game']}: {record['covered_cells']}/{record['visible_cells']} covered, {len(record['cells'])} used source aliases")
        pending = [row for row in staged if row["game"] == record["game"]]
        pending_keys = {(row["id"], row["quadrant"]) for row in pending}
        action = "Activated" if args.write_reviewed else "Staged"
        print(f"{action} {len(pending)} terrain aliases, {sum(cell['count'] for cell in record['cells'] if (cell['id'],cell['quadrant']) in pending_keys)} physical cells.")


if __name__ == "__main__":
    main()
