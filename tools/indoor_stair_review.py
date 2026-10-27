"""Private primary-native stair references: whole context and actual warp cell.

The warp cell is explicitly not assumed to contain the complete stair graphic.
No mappings, art assets or imported data are changed.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import catalog
import preview
from building_review import decode_layout

WORKSPACE = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path(os.environ["APPDATA"]) / "pokemon-love2d")
    parser.add_argument("--catalog", type=Path, default=WORKSPACE / ".work/tileshift-catalog")
    parser.add_argument("--output", type=Path, default=WORKSPACE / ".work/tileshift-indoor-stair-review")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    packed, maps, manifests, records = {}, {}, {}, {}
    def render(game, map_id):
        key = game, map_id
        if key in maps:
            return maps[key]
        if game not in manifests:
            manifests[game] = catalog.read_lua(args.cache / game / "data/generated/gba/native/manifest.lua")
            records[game] = {(r["pair"], r["mid"]): r for r in json.loads((args.catalog / f"{game}.json").read_text())["cells"]}
        native = args.cache / game / "data/generated/gba/native"
        spec = manifests[game]["layouts"][map_id]
        layout = decode_layout(native / spec["file"])
        image = Image.new("RGBA", (layout["width"] * 16, layout["height"] * 16))
        decoded = {}
        for pos, mid in enumerate(layout["mids"]):
            if mid not in decoded:
                ref = {"game": game, "tileset": spec["pair"], "id": mid, "hash": records[game][spec["pair"], mid]["pixel_sha256"]}
                decoded[mid] = preview.native_donor(args.cache, ref, packed)
            image.paste(decoded[mid], (pos % layout["width"] * 16, pos // layout["width"] * 16))
        maps[key] = image, spec, layout
        return maps[key]
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 16)
    small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
    homes, candidates = [], []
    home_maps = {"firered": ("FR_PLAYERS_HOUSE_1F", "FR_PLAYERS_HOUSE_2F", "FR_SAFFRON_CITY_COPYCATS_HOUSE_1F", "FR_SAFFRON_CITY_COPYCATS_HOUSE_2F"),
                 "emerald": ("EM_LITTLEROOT_TOWN_BRENDANS_HOUSE_1F", "EM_LITTLEROOT_TOWN_BRENDANS_HOUSE_2F",
                             "EM_LITTLEROOT_TOWN_MAYS_HOUSE_1F", "EM_LITTLEROOT_TOWN_MAYS_HOUSE_2F")}
    for game, map_ids in home_maps.items():
        warps = catalog.read_lua(args.cache / game / "data/generated/gba/warps.lua")
        for map_id in map_ids:
            image, spec, layout = render(game, map_id)
            image.save(args.output / f"{game}-{map_id}-native.png")
            stairs = [w for w in warps[map_id] if w["destMap"] in map_ids and w["destMap"] != map_id]
            for warp in stairs:
                mid = layout["mids"][warp["y"] * layout["width"] + warp["x"]]
                homes.append({"game": game, "map": map_id, "warp_xy": [warp["x"], warp["y"]], "destination": warp["destMap"],
                              "pair": spec["pair"], "mid": mid, "warp_cell_hash": records[game][spec["pair"], mid]["pixel_sha256"],
                              "source_layout_file_sha256": layout["file_sha256"],
                              "native_map_rgba_sha256": catalog.sha(image.tobytes()), "status": "whole_stair_geometry_requires_visual_review"})
    for start in range(0, len(homes), 4):
        canvas = Image.new("RGB", (1500, 1080), "#18202c")
        draw = ImageDraw.Draw(canvas)
        draw.text((16, 12), "ACTUAL HOME STAIRS — full room and outlined warp cell, no footprint inference from behavior alone", fill="white", font=font)
        for i, record in enumerate(homes[start:start + 4]):
            left, top = i % 2 * 750 + 16, i // 2 * 520 + 54
            image, spec, layout = render(record["game"], record["map"])
            draw.text((left, top), record["game"] + "/" + record["map"], fill="white", font=small)
            marked = image.convert("RGB").resize((image.width * 2, image.height * 2), Image.Resampling.NEAREST)
            md = ImageDraw.Draw(marked)
            x, y = record["warp_xy"]
            md.rectangle((x * 32, y * 32, x * 32 + 31, y * 32 + 31), outline="#ff3bff", width=1)
            canvas.paste(marked, (left, top + 27))
            draw.text((left, top + 27 + marked.height + 10), f"Warp({x},{y}) / mid{record['mid']}; magenta square is only16px", fill="#ced7e4", font=small)
            cell = image.crop((x * 16, y * 16, x * 16 + 16, y * 16 + 16))
            canvas.paste(cell.resize((96, 96), Image.Resampling.NEAREST), (left + 528, top + 80))
            draw.text((left + 528, top + 184), "actual warp cell6x", fill="white", font=small)
        canvas.save(args.output / f"native-home-stairs-{start // 4 + 1}.png")
    # Include every unique actually-used indoor FR/LG stair-warp cell, each with
    # its whole80px neighborhood, so a landing cannot be mistaken for a glyph.
    game = "firered"
    lookup = {}
    for map_id, spec in manifests[game]["layouts"].items():
        if spec["pair"] not in {pair for pair, mid in records[game] if "STAIR_WARP" in (records[game][pair, mid].get("behavior_hint") or "")}:
            continue
        native = args.cache / game / "data/generated/gba/native"
        layout = decode_layout(native / spec["file"])
        for pos, mid in enumerate(layout["mids"]):
            record = records[game][spec["pair"], mid]
            if "STAIR_WARP" in (record.get("behavior_hint") or ""):
                lookup.setdefault((spec["pair"], mid), (map_id, pos % layout["width"], pos // layout["width"]))
    for (pair, mid), (map_id, x, y) in sorted(lookup.items()):
        image, spec, layout = render(game, map_id)
        record = records[game][pair, mid]
        cell = image.crop((x * 16, y * 16, x * 16 + 16, y * 16 + 16))
        context = image.crop(((x - 2) * 16, (y - 2) * 16, (x + 3) * 16, (y + 3) * 16))
        candidates.append(({"game": game, "pair": pair, "mid": mid, "map": map_id, "cell_xy": [x, y],
                            "behavior_hint": record["behavior_hint"], "hash": record["pixel_sha256"],
                            "status": "private_geometry_review_only_not_a_complete16px_stair_claim"}, cell, context))
    for start in range(0, len(candidates), 6):
        canvas = Image.new("RGB", (1500, 1000), "#18202c")
        draw = ImageDraw.Draw(canvas)
        draw.text((16, 12), "INDOOR STAIR GEOMETRY CANDIDATES — actual16px cell beside whole80px neighborhood", fill="white", font=font)
        for i, (record, cell, context) in enumerate(candidates[start:start + 6]):
            left, top = i % 2 * 750 + 16, i // 2 * 310 + 54
            draw.text((left, top), record["pair"] + ":" + str(record["mid"]) + " / " + record["behavior_hint"], fill="white", font=small)
            draw.text((left, top + 22), record["map"] + " @ " + str(record["cell_xy"]), fill="#ced7e4", font=small)
            canvas.paste(cell.resize((96, 96), Image.Resampling.NEAREST), (left, top + 58))
            canvas.paste(context.resize((240, 240), Image.Resampling.NEAREST), (left + 144, top + 46))
            md = ImageDraw.Draw(canvas)
            md.rectangle((left + 240, top + 142, left + 287, top + 189), outline="#ff3bff", width=1)
        canvas.save(args.output / f"native-indoor-stair-candidates-{start // 6 + 1}.png")
    report = {"status": "private_primary_source_review_no_active_rows", "home_references": homes,
              "actually_used_stair_warp_cells": [r for r, _, _ in candidates],
              "limits": "Stair behavior identifies a warp destination, not the complete graphic. Whole context is mandatory before declaring any16px equivalent. No scaling or partial stair glyphs are proposed."}
    (args.output / "native-indoor-stair-geometry.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"home_references": len(homes), "unique_used_stair_warp_cells": len(candidates)}, indent=2))


if __name__ == "__main__":
    main()
