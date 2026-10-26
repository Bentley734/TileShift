"""Prepare map-scoped shoreline geometry review from local native imports.

Generated pictures remain private review material. Candidate mappings are never
activated here, and collision/behavior is recorded only as supporting context.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import sys
import zlib

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE / ".tools/python"))
from PIL import Image, ImageDraw, ImageFont
import catalog
import preview

SOURCES = {
    "red": {"map": "PALLET_TOWN", "crop": (3, 13, 6, 5),
            "cells": ((29, 0), (29, 1), (30, 0), (30, 1), (29, 2), (101, 0), (101, 2), (30, 3), (100, 1), (100, 3))},
    "crystal": {"map": "NEW_BARK_TOWN", "crop": (17, 5, 3, 6),
                "cells": ((84, 0), (84, 1), (84, 2), (88, 0), (88, 2))},
}


def unpack(path: Path) -> bytes:
    raw = path.read_bytes()
    try:
        return zlib.decompress(raw)
    except zlib.error:
        return raw


def source_records(cache: Path, output: Path):
    records = []
    for game, source in SOURCES.items():
        maps = catalog.read_lua(cache / game / "data/generated/maps.lua")
        sets = catalog.read_lua(cache / game / "data/generated/tilesets.lua")
        map_id = source["map"]
        definition = maps[map_id]
        tileset = sets[definition["tileset"]]
        atlas = Image.open(cache / game / tileset["image"]).convert("RGBA")
        palettes = None
        if game == "crystal":
            palettes = preview.palette_set(catalog.read_lua(cache / game / "data/generated/palettes.lua"), definition)
        coordinates = defaultdict(list)
        native = Image.new("RGBA", (definition["width"] * 32, definition["height"] * 32))
        for index, block_id in enumerate(definition["blocks"]):
            block = tileset["blocks"][block_id]
            for quadrant in range(4):
                x = index % definition["width"] * 2 + quadrant % 2
                y = index // definition["width"] * 2 + quadrant // 2
                coordinates[block_id, quadrant].append([x, y])
                cell = preview.native_cell(atlas, tileset, block, quadrant, palettes)
                native.paste(cell, (x * 16, y * 16))
        x, y, w, h = source["crop"]
        crop = native.crop((x * 16, y * 16, (x + w) * 16, (y + h) * 16))
        enlarged = crop.resize((w * 96, h * 96), Image.Resampling.NEAREST).convert("RGB")
        grid = Image.new("RGB", (enlarged.width + 70, enlarged.height + 65), "#18202c")
        grid.paste(enlarged, (60, 55));draw = ImageDraw.Draw(grid)
        draw.text((10, 8), f"{game} / {map_id} native shore; zero-based16px cells", fill="white")
        for cx in range(w): draw.text((60 + cx * 96 + 40, 35), str(x + cx), fill="white")
        for cy in range(h): draw.text((25, 55 + cy * 96 + 42), str(y + cy), fill="white")
        for cx in range(w + 1): draw.line((60 + cx * 96, 55, 60 + cx * 96, 55 + h * 96), fill="#7a80a0")
        for cy in range(h + 1): draw.line((60, 55 + cy * 96, 60 + w * 96, 55 + cy * 96), fill="#7a80a0")
        grid.save(output / f"{game}-shore-context.png")
        native.save(output / f"{game}-native-map.png")
        for block_id, quadrant in source["cells"]:
            block = tileset["blocks"][block_id]
            raw = preview.native_cell(atlas, tileset, block, quadrant)
            colored = preview.native_cell(atlas, tileset, block, quadrant, palettes)
            ox, oy = quadrant % 2 * 2, quadrant // 2 * 2
            ids = [block[oy * 4 + ox], block[oy * 4 + ox + 1], block[(oy + 1) * 4 + ox], block[(oy + 1) * 4 + ox + 1]]
            collision = tileset["collision"][block_id][quadrant] if game == "crystal" else ids[2]
            path = output / f"{game}-{block_id}-{quadrant}.png"
            colored.save(path)
            records.append({"game": game, "map": map_id, "tileset": definition["tileset"],
                            "id": block_id, "quadrant": quadrant, "coordinates": coordinates[block_id, quadrant],
                            "tiles": ids, "collision": collision, "sourceHash": catalog.sha(raw.tobytes()),
                            "image": str(path.resolve())})
    return records


def native_frames(root: Path, mid: int, base_under: Image.Image, base_over: Image.Image, bank, palette):
    mids = bank.get("mids", [])
    over_mids = bank.get("overMids", [])
    if mid not in mids and mid not in over_mids:
        return [Image.alpha_composite(base_under, base_over)]
    under_blob = unpack(root / bank["file"]) if bank.get("file") and mids else None
    over_blob = unpack(root / bank["overFile"]) if bank.get("overFile") and over_mids else None
    images = []
    for frame in range(bank["frames"]):
        under, over = base_under.copy(), base_over.copy()
        for layer, blob, ids, masks in ((under, under_blob, mids, bank.get("quads")),
                                       (over, over_blob, over_mids, bank.get("overQuads"))):
            if mid not in ids:
                continue
            index = ids.index(mid)
            offset = (frame * len(ids) + index) * 256
            piece = catalog.rgba_native(blob[offset:offset + 256], palette, layer is over)
            mask = masks[index] if masks else 15
            for q in range(4):
                if (mask >> q) & 1:
                    x, y = q % 2 * 8, q // 2 * 8
                    layer.paste(piece.crop((x, y, x + 8, y + 8)), (x, y))
        images.append(Image.alpha_composite(under, over))
    return images


def donor_records(cache: Path, pair: str, output: Path):
    root = cache / "emerald/data/generated/gba/native" / pair
    mids, pixels, _ = catalog.read_idx(root / "mids.idx")
    over_mids, over_pixels, _ = catalog.read_idx(root / "mids_over.idx")
    assert mids == over_mids
    palette = catalog.read_palettes(root / "palettes.bin")
    manifest_bytes = (root / "anim_manifest.lua").read_bytes()
    manifest = catalog.read_lua(root / "anim_manifest.lua")
    water_bank = next(row for row in manifest["banks"] if row["name"] == "general_water")
    catalog_file = json.loads((WORKSPACE / ".work/tileshift-catalog/emerald.json").read_text())
    hashes = {r["mid"]: r["pixel_sha256"] for r in catalog_file["cells"] if r["pair"] == pair}
    targets = sorted(set(water_bank.get("mids", [])) | set(water_bank.get("overMids", [])))
    records = []
    for mid in targets:
        slot = mids.index(mid)
        under = catalog.rgba_native(pixels[slot * 256:(slot + 1) * 256], palette)
        over = catalog.rgba_native(over_pixels[slot * 256:(slot + 1) * 256], palette, True)
        frames = native_frames(root, mid, under, over, water_bank, palette)
        records.append({"mid": mid, "hash": hashes[mid], "frames": frames,
                        "mask": water_bank["quads"][water_bank["mids"].index(mid)] if mid in water_bank["mids"] else 0})
    columns, cw, ch = 12, 83, 92
    overview = Image.new("RGB", (columns * cw + 20, math.ceil(len(records) / columns) * ch + 65), "#18202c")
    draw = ImageDraw.Draw(overview)
    draw.text((10, 8), f"Emerald {pair}: every native general_water target, frame0", fill="white")
    draw.text((10, 27), "Shape and material need visual review. Native behavior alone does not prove equivalence.", fill="#bfc9d9")
    for i, record in enumerate(records):
        x, y = 10 + i % columns * cw, 58 + i // columns * ch
        overview.paste(record["frames"][0].resize((64, 64), Image.Resampling.NEAREST), (x, y))
        draw.text((x, y + 65), f"mid{record['mid']} q{record['mask']}", fill="white")
    overview.save(output / "emerald-water-targets.png")
    animation = {"bank": "general_water", "hash": catalog.sha(unpack(root / water_bank["file"])),
                 "manifestHash": catalog.sha(manifest_bytes), "period": water_bank["period"],
                 "phase": water_bank["phase"], "frames": water_bank["frames"]}
    return records, animation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path(catalog.os.environ["APPDATA"]) / "pokemon-love2d")
    parser.add_argument("--output", type=Path, default=WORKSPACE / ".work/tileshift-coast-review")
    parser.add_argument("--pair", default="general__petalburg")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    sources = source_records(args.cache, args.output)
    targets, animation = donor_records(args.cache, args.pair, args.output)
    payload = {"sources": sources, "donor": {"game": "emerald", "tileset": args.pair, "animation": animation},
               "targets": [{k: v for k, v in r.items() if k != "frames"} for r in targets],
               "status": "visual review in progress; no candidates activated"}
    (args.output / "shoreline-inventory.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Prepared {len(sources)} used source cells and {len(targets)} native animated-water targets in {args.output}")


if __name__ == "__main__":
    main()
