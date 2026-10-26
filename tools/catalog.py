"""Inventory locally imported tiles without treating collision as visual identity.

Requires Pillow and lupa. Outputs are local review material containing extracted
game images; do not include the output directory in a mod release. GB cells are
16px quadrants of a 32px block. GBA cells retain all native rendering layers.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import zlib

from lupa import LuaRuntime, lua_type
from PIL import Image, ImageDraw, ImageFont

GAMES = ("red", "blue", "yellow", "gold", "silver", "crystal",
         "ruby", "sapphire", "emerald", "firered", "leafgreen")
GEN2_HINTS = {0x00: "floor", 0x07: "wall", 0x18: "tall_grass",
              0x29: "water", 0x33: "waterfall", 0x60: "pit",
              0x71: "door", 0x7A: "staircase", 0x7B: "cave",
              **{c: "ledge_direction_requires_game_context" for c in range(0xA0, 0xA8)}}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def plain(value):
    if lua_type(value) != "table":
        return value
    keys = list(value.keys())
    if keys and all(isinstance(k, int) for k in keys) and sorted(keys) == list(range(1, len(keys) + 1)):
        return [plain(value[i]) for i in range(1, len(keys) + 1)]
    return {str(k): plain(value[k]) for k in keys}


LUA = LuaRuntime(register_eval=False, register_builtins=False)
LOAD = LUA.eval("function(text, name) return assert(load(text, name, 't', {}))() end")


def read_lua(path: Path):
    return plain(LOAD(path.read_text(encoding="utf-8-sig"), str(path)))


def lua_array(value):
    if isinstance(value, list):
        return value
    return [value[str(i)] for i in range(1, len(value) + 1)]


def dict_at(value, index, default=None):
    if isinstance(value, list):
        return value[index - 1] if 1 <= index <= len(value) else default
    return value.get(str(index), default) if isinstance(value, dict) else default


def read_idx(path: Path):
    raw = path.read_bytes()
    if raw[:4] != b"SVMI":
        raw = zlib.decompress(raw)
    if len(raw) < 12 or raw[:4] != b"SVMI":
        raise ValueError(f"Invalid native atlas: {path}")
    version, flags, count, cols, rows = struct.unpack_from("<BBHHH", raw, 4)
    if version != 1 or not 0 < count <= 4096 or cols * rows > 16384 or len(raw) < 12 + count * 258:
        raise ValueError(f"Invalid native atlas dimensions: {path}")
    mids = struct.unpack_from(f"<{count}H", raw, 12)
    pixels = raw[12 + count * 2:12 + count * 258]
    return mids, pixels, flags


def read_palettes(path: Path):
    raw = path.read_bytes()
    if len(raw) < 520 or raw[:4] != b"SVMP":
        raise ValueError(f"Invalid native palette: {path}")
    rgb = []
    for word in struct.unpack_from("<256H", raw, 8):
        rgb.append(tuple(round(((word >> shift) & 31) * 255 / 31) for shift in (0, 5, 10)))
    return rgb


def layout_mid_ids(path: Path):
    raw = path.read_bytes()
    if raw[:4] != b"SVML":
        raw = zlib.decompress(raw)
    if len(raw) < 16 or raw[:4] != b"SVML":
        raise ValueError(f"Invalid native layout: {path}")
    width, height = struct.unpack_from("<HH", raw, 6)
    border_count = raw[14] * raw[15]
    offset = 16 + border_count * 2
    if width * height > 2_000_000 or len(raw) < offset + width * height * 4:
        raise ValueError(f"Truncated native layout: {path}")
    mids = set(struct.unpack_from(f"<{border_count}H", raw, 16))
    mids.update(struct.unpack_from("<H", raw, offset + i * 4)[0] for i in range(width * height))
    return mids


def rgba_native(pixels: bytes, palette, transparent=False):
    return Image.frombytes("RGBA", (16, 16), b"".join(
        bytes((*palette[p], 0 if transparent and p == 0 else 255)) for p in pixels))


def gb_tile(sheet, tileset, raw_id):
    """Match Crystal MapAttrGrid.normalizeTile and TileAttrs.sheetTileId."""
    attrs = dict_at(tileset.get("tileAttrs"), raw_id + 1)
    if attrs is None and raw_id < 128:
        attrs = dict_at(tileset.get("tileAttrs"), raw_id + 129)
    attrs = dict(attrs or {})
    bank = attrs.get("vramBank") or (1 if raw_id >= 128 else 0)
    tile_id = raw_id if raw_id >= 128 else raw_id + (128 if bank else 0)
    cols = int(tileset.get("tilesPerRow", 16))
    x, y = tile_id % cols * 8, tile_id // cols * 8
    tile = sheet.crop((x, y, x + 8, y + 8)).convert("RGBA")
    if attrs.get("xFlip"):
        tile = tile.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if attrs.get("yFlip"):
        tile = tile.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    attrs.setdefault("palette", dict_at(tileset.get("tilePalettes"), raw_id + 1, 1))
    attrs["sheet_tile_id"] = tile_id
    attrs["source_pixels_complete"] = x + 8 <= sheet.width and y + 8 <= sheet.height
    return tile, attrs


def make_sheet(path: Path, title: str, previews, limit: int):
    seen, selected = set(), []
    for label, image in previews:
        digest = sha(image.tobytes())
        if digest not in seen:
            seen.add(digest)
            selected.append((label, image))
    shown = selected[:limit]
    cols, cw, ch = 12, 84, 88
    canvas = Image.new("RGB", (cols * cw + 16, math.ceil(len(shown) / cols) * ch + 70), "#18202c")
    draw = ImageDraw.Draw(canvas)
    draw.text((10, 8), title, fill="white")
    draw.text((10, 27), f"{len(shown)} of {len(selected)} unique images; labels identify original cells", fill="#bfc9d9")
    draw.text((10, 44), "Native behavior is a search hint, never proof of a visual equivalent.", fill="#bfc9d9")
    for i, (label, tile) in enumerate(shown):
        x, y = 8 + (i % cols) * cw, 65 + (i // cols) * ch
        canvas.paste(tile.resize((48, 48), Image.Resampling.NEAREST), (x + 13, y))
        draw.text((x, y + 50), label, fill="white")
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path)
    return {"path": str(path.resolve()), "unique": len(selected), "shown": len(shown)}


def inventory_gb(cache, game, output, sheets, limit):
    root = cache / game
    source = root / "data/generated/tilesets.lua"
    sets = read_lua(source)
    map_source = root / "data/generated/maps.lua"
    maps = read_lua(map_source) if map_source.exists() else {}
    used_blocks = Counter()
    for map_def in maps.values():
        if not isinstance(map_def, dict):
            continue
        block_ids = set(lua_array(map_def.get("blocks", [])))
        if map_def.get("borderBlock") is not None:
            block_ids.add(map_def["borderBlock"])
        for block_id in block_ids:
            used_blocks[(map_def.get("tileset"), block_id)] += 1
    gen = 1 if game in GAMES[:3] else 2
    records, previews, setinfo = [], {}, []
    for name, ts in sorted(sets.items()):
        if not isinstance(ts, dict) or "blocks" not in ts:
            continue
        image_path = root / ts["image"]
        sheet = Image.open(image_path)
        fingerprints = {"metadata": sha(source.read_bytes()), "image": sha(image_path.read_bytes()),
                        "maps": sha(map_source.read_bytes()) if map_source.exists() else None}
        per_set = []
        walkable = set(lua_array(ts.get("walkable", [])))
        warps = set(lua_array(ts.get("warpTiles", [])))
        tile_cache = {}
        for block_id, block in enumerate(lua_array(ts["blocks"])):
            block = lua_array(block)
            for quadrant in range(4):
                qx, qy = quadrant % 2 * 2, quadrant // 2 * 2
                offsets = (qy * 4 + qx, qy * 4 + qx + 1, (qy + 1) * 4 + qx, (qy + 1) * 4 + qx + 1)
                raw_ids = [block[i] for i in offsets]
                tile = Image.new("RGBA", (16, 16))
                tile_attrs = []
                for i, raw_id in enumerate(raw_ids):
                    if raw_id not in tile_cache:
                        tile_cache[raw_id] = gb_tile(sheet, ts, raw_id)
                    tiny, attr = tile_cache[raw_id]
                    tile.paste(tiny, (i % 2 * 8, i // 2 * 8))
                    tile_attrs.append(attr)
                collision = dict_at(ts.get("collision"), block_id + 1)
                collision = dict_at(collision, quadrant + 1) if collision else None
                hint = GEN2_HINTS.get(collision, "native_collision_" + str(collision)) if gen == 2 else None
                row = {"id": f"{game}:{name}:{block_id}:{quadrant}", "game": game, "generation": gen,
                       "tileset": name, "block_id": block_id, "quadrant": quadrant, "size": 16,
                       "tiles": raw_ids, "tile_attributes": tile_attrs, "collision": collision,
                       "behavior_hint": hint, "grayscale_pixel_sha256": sha(tile.tobytes()),
                       "used_by_map_count": used_blocks[(name, block_id)],
                       "source_pixels_complete": all(a["source_pixels_complete"] for a in tile_attrs),
                       "mapping_status": "needs_visual_review"}
                if gen == 1:
                    row.update(walkable_tiles=[t in walkable for t in raw_ids],
                               grass_tile_present=ts.get("grassTile") in raw_ids,
                               warp_tile_present=any(t in warps for t in raw_ids))
                records.append(row)
                if row["used_by_map_count"] and row["source_pixels_complete"]:
                    per_set.append((f"{block_id}:{quadrant}\n{hint or ''}", tile))
        item = {"tileset": name, "cells": len(lua_array(ts["blocks"])) * 4,
                "used_complete_cells": len(per_set), "fingerprints": fingerprints,
                "preview_palette": "source grayscale; map/time palettes intentionally not inferred",
                "animation": ts.get("anim", ts.get("animation")), "source_image": str(image_path)}
        representative = (gen == 1 and name == "OVERWORLD") or (gen == 2 and name == "TILESET_JOHTO")
        if sheets == "all" or (sheets == "representative" and representative):
            item["contact_sheet"] = make_sheet(output / "contacts" / game / f"{name}.png", f"{game} / {name} (source grayscale)", per_set, limit)
        setinfo.append(item)
    palettes_path = root / "data/generated/palettes.lua"
    palette_metadata = read_lua(palettes_path) if palettes_path.exists() else None
    return records, {"tilesets": setinfo, "palette_metadata": palette_metadata}


def inventory_gba(cache, game, output, engine, sheets, limit):
    root = cache / game / "data/generated/gba"
    mid_index = read_lua(root / "mid_index.lua")
    native = root / "native"
    manifest = read_lua(native / "manifest.lua")
    used_mids = Counter()
    for layout in manifest.get("layouts", {}).values():
        for mid in layout_mid_ids(native / layout["file"]):
            used_mids[(layout["pair"], mid)] += 1
    behavior_path = engine / "src/core/game3/constants" / ("firered" if game in ("firered", "leafgreen") else "ruby" if game in ("ruby", "sapphire") else "emerald") / "metatile_behaviors.lua"
    behavior_names = {int(v): k for k, v in read_lua(behavior_path)["byName"].items()} if behavior_path.exists() else {}
    records, setinfo = [], []
    pair_paths = sorted(native.glob("*/mids.idx"))
    outdoor_paths = [p for p in pair_paths if p.parent.name.startswith("general__")]
    preferred = next((p for p in outdoor_paths if any(x in p.parent.name for x in ("littleroot", "petalburg", "rustboro"))), outdoor_paths[0] if outdoor_paths else None)
    for idx_path in pair_paths:
        pair = idx_path.parent.name
        mids, pixels, flags = read_idx(idx_path)
        palette = read_palettes(idx_path.parent / "palettes.bin")
        layer_pixels = {}
        for layer in ("mid", "over"):
            layer_path = idx_path.parent / f"mids_{layer}.idx"
            if layer_path.exists():
                layer_mids, layer_data, _ = read_idx(layer_path)
                if layer_mids != mids:
                    raise ValueError(f"Layer IDs disagree: {layer_path}")
                layer_pixels[layer] = layer_data
        pair_index = mid_index.get(pair, {})
        per_set = []
        for slot, mid in enumerate(mids):
            pix = pixels[slot * 256:(slot + 1) * 256]
            image = rgba_native(pix, palette)
            hashes = {"under": sha(image.tobytes())}
            for layer, data in layer_pixels.items():
                overlay = rgba_native(data[slot * 256:(slot + 1) * 256], palette, True)
                hashes[layer] = sha(overlay.tobytes())
                image = Image.alpha_composite(image, overlay)
            info = pair_index.get(str(mid), {})
            behavior = info.get("behavior")
            records.append({"id": f"{game}:{pair}:{mid}", "game": game, "generation": 3,
                            "pair": pair, "mid": mid, "size": 16, "atlas_slot": slot,
                            "behavior": behavior, "behavior_hint": behavior_names.get(behavior),
                            "native_category": info.get("category"), "collision_hint": info.get("coll"),
                            "used_by_map_count": used_mids[(pair, mid)],
                            "pixel_sha256": sha(image.tobytes()), "layer_sha256": hashes,
                            "mapping_status": "needs_visual_review"})
            per_set.append((f"mid {mid}\n{behavior_names.get(behavior, str(behavior)).removeprefix('MB_')[:13]}", image))
        item = {"pair": pair, "cells": len(mids), "flags": flags,
                "fingerprints": {**{p.name: sha(p.read_bytes()) for p in idx_path.parent.iterdir() if p.is_file()},
                                 "manifest": sha((native / "manifest.lua").read_bytes()),
                                 "mid_index": sha((root / "mid_index.lua").read_bytes())},
                "preview_palette": "native palette; all three layers composited; animation initial frame"}
        if sheets == "all" or (sheets == "representative" and idx_path == preferred):
            item["contact_sheet"] = make_sheet(output / "contacts" / game / f"{pair}.png", f"{game} / {pair} (native colors)", per_set, limit)
        setinfo.append(item)
    return records, {"tilesets": setinfo}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path(os.environ.get("APPDATA", "~")) / "pokemon-love2d")
    parser.add_argument("--engine", type=Path, default=Path(__file__).resolve().parents[2] / ".tools/engine-0395")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[2] / ".work/tileshift-catalog")
    parser.add_argument("--games", nargs="+", choices=GAMES, default=GAMES)
    parser.add_argument("--sheets", choices=("none", "representative", "all"), default="representative")
    parser.add_argument("--sheet-limit", type=int, default=1024)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    summary = {"format": 1, "cell_size": 16, "mapping_policy": "No automatically approved semantic equivalents. Pixel duplicates and native behaviors are review hints only.",
               "provenance": "Original ROM imports on this computer; extracted images are local review material only.", "games": {}}
    for game in args.games:
        if game in GAMES[:6]:
            records, info = inventory_gb(args.cache, game, args.output, args.sheets, args.sheet_limit)
        else:
            records, info = inventory_gba(args.cache, game, args.output, args.engine, args.sheets, args.sheet_limit)
        hashes = Counter(r.get("pixel_sha256", r.get("grayscale_pixel_sha256")) for r in records)
        payload = {"format": 1, "game": game, "source_cache": str((args.cache / game).resolve()),
                   "palette_metadata": info.get("palette_metadata"), "tilesets": info["tilesets"], "cells": records}
        (args.output / f"{game}.json").write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        summary["games"][game] = {"tilesets": len(info["tilesets"]), "cells": len(records), "unique_pixel_images": len(hashes),
                                  "reviewed_equivalents": 0, "unreviewed_cells": len(records),
                                  "map_used_cells": sum(1 for r in records if r.get("used_by_map_count", 1) > 0),
                                  "incomplete_source_cells": sum(1 for r in records if not r.get("source_pixels_complete", True)),
                                  "contacts": [t["contact_sheet"] for t in info["tilesets"] if "contact_sheet" in t]}
        print(game, json.dumps({k: v for k, v in summary["games"][game].items() if k != "contacts"}), flush=True)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
