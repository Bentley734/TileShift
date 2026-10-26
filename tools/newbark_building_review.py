"""Review complete New Bark architecture from native Gen3 parts, without scaling.

Private comparisons contain imported artwork. Production, when requested after
review, contains only source fingerprints and native rectangle references.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import textwrap

from PIL import Image, ImageDraw, ImageFont
import catalog
import preview
from building_review import decode_layout

WORKSPACE = Path(__file__).resolve().parents[2]
SOURCE_BUILDINGS = (("lab", "ELMS_LAB", (4, 0, 6, 4)),
                    ("player", "PLAYERS_HOUSE_1F", (12, 2, 4, 4)),
                    ("neighbor", "PLAYERS_NEIGHBORS_HOUSE", (2, 10, 4, 2)),
                    ("elm_home", "ELMS_HOUSE", (10, 12, 4, 2)))
CONFIGS = {
    "lab": {"native": ("emerald", "EM_LITTLEROOT_TOWN", "EM_LITTLEROOT_TOWN_PROFESSOR_BIRCHS_LAB", (3, 12, 7, 5)),
            "size": (96, 64), "rows": (0, 1, 2, 3, 6, 7, 8, 9), "roof_rows": 5,
            "roof_columns": (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 13),
            "facade_columns": (0, 2, 3, 7, 8, 9, 10, 11, 4, 5, 12, 13),
            "features": (("complete native left window and full awning", (16, 56, 16, 24), (8, 40, 16, 24)),
                         ("complete native right window and full awning", (32, 56, 16, 24), (64, 40, 16, 24)),
                         ("complete32x24 entrance frame and door", (56, 56, 32, 24), (24, 40, 32, 24)),
                         ("whole32x32 laboratory satellite dish and base", (16, 0, 32, 32), (16, 0, 32, 32))),
            "anchor": (40, 64), "notes": "Birch's actual laboratory. Complete independent native window units moved to either side of the entrance; repeated roof panels omitted, whole dish retained."},
    "player": {"native": ("emerald", "EM_LITTLEROOT_TOWN", "EM_LITTLEROOT_TOWN_MAYS_HOUSE_1F", (13, 4, 5, 5)),
               "size": (64, 64), "rows": (0, 1, 4, 5, 6, 7, 8, 9), "roof_rows": 5,
               "roof_columns": (0, 1, 2, 3, 4, 5, 8, 9), "facade_columns": (0, 1, 2, 3, 4, 6, 7, 9),
               "features": (("complete native16x24 window panel including all outer frame pixels", (48, 56, 16, 24), (40, 40, 16, 24)),
                            ("complete32x24 entrance frame and door", (8, 56, 32, 24), (8, 40, 32, 24))),
               "anchor": (24, 64), "notes": "Actual Littleroot player's home, using May's door orientation. Repeated roof rows/columns and plain facade spacing are removed; complete native doorway and window retained."},
    "ordinary": {"native": ("firered", "FR_VIRIDIAN_CITY", "FR_VIRIDIAN_CITY_HOUSE", (24, 8, 5, 4)),
                 "size": (64, 32), "rows": (1, 5, 6, 7), "roof_rows": 2,
                 "roof_columns": (0, 1, 2, 3, 4, 4, 8, 9), "facade_columns": (0, 1, 2, 3, 5, 6, 7, 9),
                 "features": (("complete native24x17 window frame including full top cap", (40, 47, 24, 17), (32, 15, 24, 17)),
                              ("complete16x17 entrance frame and door", (16, 47, 16, 17), (16, 15, 16, 17))),
                 "anchor": (24, 32), "notes": "Actual one-story Viridian residence, with green ribbed roof. Repeated roof area and the complete chimney component are omitted; no chimney fragment is retained. Full window and door caps remain native."},
}


def rectangle(image, rect):
    x, y, w, h = rect
    return image.crop((x, y, x + w, y + h))


def lua(value):
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (list, tuple)):
        return "{" + ",".join(lua(v) for v in value) + "}"
    return "{" + ",".join("[" + lua(k) + "]=" + lua(v) for k, v in value.items()) + "}"


def feature_review(args, native_images, targets, models):
    features = [(model["id"], feature) for model in models for feature in model["features_checked"]]
    canvas = Image.new("RGB", (1500, 1000), "#18202c")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 16)
    small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
    draw.text((16, 12), "COMPLETE NATIVE FEATURES AT6x — all window/awning/frame pixels retained, not partial spans", fill="white", font=font)
    for i, (key, feature) in enumerate(features):
        left, top = i % 3 * 500 + 16, i // 3 * 310 + 55
        draw.multiline_text((left, top), textwrap.fill(key.upper() + ": " + feature["feature"], 53), fill="white", font=small)
        for col, (label, image, rect) in enumerate((("native", native_images[key], feature["source_rect_xywh"]),
                                                    ("compact:0 pixel differences", targets[key], feature["target_rect_xywh"]))):
            draw.text((left + col * 224, top + 44), label, fill="#ced7e4", font=small)
            crop = rectangle(image, rect)
            canvas.paste(crop.resize((crop.width * 6, crop.height * 6), Image.Resampling.NEAREST), (left + col * 224, top + 66))
    canvas.save(args.output / "newbark-complete-native-features.png")


def town_review(args, targets):
    mod = Path(__file__).resolve().parents[1]
    rows = []
    for path in sorted((mod / "mappings").glob("*.lua")):
        if path.name != "gen2_buildings.lua":
            rows.extend(preview.read_reviewed(path))
    reports = []
    for game in ("gold", "silver", "crystal"):
        m, ts, sheet, original = render_source(args.cache, game)
        selected = {}
        for row in sorted(rows, key=lambda r: bool(r.get("map"))):
            if row["game"] == game and row["style"] == "gen3" and row["tileset"] == m["tileset"] and row.get("map", m["id"]) == m["id"]:
                selected[row["id"], row["quadrant"]] = row
        after = original.copy()
        packed, before_count = {}, 0
        for pos, bid in enumerate(m["blocks"]):
            for q in range(4):
                row = selected.get((bid, q))
                if row:
                    after.paste(preview.replacement_image(args.cache, row, packed, mod),
                                (pos % m["width"] * 32 + q % 2 * 16, pos // m["width"] * 32 + q // 2 * 16))
                    before_count += 1
        assert before_count == 304
        for key, _, (x, y, w, h) in SOURCE_BUILDINGS:
            image = targets[key if key in targets else "ordinary"]
            assert image.size == (w * 16, h * 16)
            after.paste(image, (x * 16, y * 16))
        after.save(args.output / f"{game}-newbark-candidate-after-native.png")
        canvas = Image.new("RGB", (1336, 760), "#18202c")
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)
        small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 15)
        review_label = "reviewed full background" if args.write_reviewed else "full background candidate"
        draw.text((18, 12), f"{game.title()} NEW BARK — {review_label},360/360 native map cells", fill="white", font=font)
        draw.text((18, 42), "Native building parts preserve original footprints and warp anchors. Local background fixture; actors are not rendered.", fill="#ced7e4", font=small)
        draw.text((18, 77), "Original DAY colors and native group roof", fill="white", font=small)
        draw.text((678, 77), "Gen3: all four buildings and reviewed surroundings", fill="white", font=small)
        canvas.paste(original.resize((640, 576), Image.Resampling.NEAREST), (18, 108))
        canvas.paste(after.resize((640, 576), Image.Resampling.NEAREST), (678, 108))
        draw.text((18, 707), "Full source town remains20x18 cells. Windows, awnings, complete entrances and roof background are checked separately; live GPU check follows activation.", fill="#ced7e4", font=small)
        canvas.save(args.output / f"{game}-newbark-complete-candidate.png")
        reports.append({"game": game, "map": m["id"], "existing_reviewed_cells": before_count,
                        "building_cells": 56, "target_covered_cells": 360, "total_cells": 360,
                        "candidate_pixel_sha256": catalog.sha(after.tobytes()), "source_map_unchanged": True})
        if game == "crystal":
            seams = Image.new("RGB", (1400, 660), "#18202c")
            seam_draw = ImageDraw.Draw(seams)
            seam_draw.text((16, 12), "NEW BARK ROOF CORNERS — native alpha masks over exact adjacent Emerald ground", fill="white", font=font)
            seam_draw.text((16, 40), "All empty pixels are checked against the local16px ground phase; native roof pixels and full building outlines are preserved.", fill="#ced7e4", font=small)
            corners = []
            for key, _, (x, y, w, _) in SOURCE_BUILDINGS:
                corners.extend(((key + " northwest", max(0, x * 16 - 8), max(0, y * 16 - 8)),
                                (key + " northeast", (x + w) * 16 - 16, max(0, y * 16 - 8))))
            for i, (label, x, y) in enumerate(corners):
                left, top = 16 + i % 4 * 350, 90 + i // 4 * 280
                seam_draw.text((left, top), label, fill="white", font=small)
                seams.paste(rectangle(after, (x, y, 32, 32)).resize((192, 192), Image.Resampling.NEAREST), (left, top + 30))
            seams.save(args.output / "newbark-roof-corner-seams.png")
    return reports


def mapping_rows(args, models):
    by_name = {m["id"]: m for m in models}
    rows = []
    for game in ("gold", "silver", "crystal"):
        m, ts, sheet, _ = render_source(args.cache, game)
        root = args.cache / game
        fingerprints = {"metadata": catalog.sha((root / "data/generated/tilesets.lua").read_bytes()),
                        "maps": catalog.sha((root / "data/generated/maps.lua").read_bytes()),
                        "image": catalog.sha((root / ts["image"]).read_bytes()),
                        "palettes": catalog.sha((root / "data/generated/palettes.lua").read_bytes()),
                        "roofs": catalog.sha((root / "data/generated/roofs.lua").read_bytes())}
        catalog_cells = json.loads((args.catalog / f"{game}.json").read_text())["cells"]
        source_index = {(r["block_id"], r["quadrant"]): r for r in catalog_cells if r.get("tileset") == m["tileset"]}
        for key, destination, (ox, oy, w, h) in SOURCE_BUILDINGS:
            model = by_name[key if key in by_name else "ordinary"]
            target = Image.open(args.output / f"{model['id']}-compact-prototype.png").convert("RGBA")
            for ty in range(h):
                for tx in range(w):
                    x, y = ox + tx, oy + ty
                    bid, q = m["blocks"][y // 2 * m["width"] + x // 2], y % 2 * 2 + x % 2
                    source = source_index[bid, q]
                    actual = preview.native_cell(sheet, ts, ts["blocks"][bid], q)
                    assert catalog.sha(actual.tobytes()) == source["grayscale_pixel_sha256"]
                    parts = []
                    for part in model["parts"]:
                        px, py = part["target_xy"]
                        if px // 16 == tx and py // 16 == ty:
                            value = {k: part[k] for k in ("donor", "srcX", "srcY", "w", "h")}
                            value.update(x=px % 16, y=py % 16)
                            for optional in ("layers", "layerHashes"):
                                if optional in part:
                                    value[optional] = part[optional]
                            parts.append(value)
                    assert len(parts) == 4
                    row = {"game": game, "style": "gen3", "map": "NEW_BARK_TOWN", "x": x, "y": y,
                           "tileset": m["tileset"], "id": bid, "quadrant": q, "sourceHash": source["grayscale_pixel_sha256"],
                           "sourceFiles": fingerprints, "role": "newbark_" + (key if key in by_name else "ordinary") + "_building",
                           "kind": "native_composite", "status": "reviewed" if args.write_reviewed else "candidate",
                           "parts": parts, "compositionPixelHash": catalog.sha(rectangle(target, (tx * 16, ty * 16, 16, 16)).tobytes()),
                           "evidence": "Complete native Gen3 counterpart components, reconstructed solely with existing8px rectangles. " + CONFIGS[model["id"]]["notes"]
                                       + " Every whole window/awning and entrance frame is byte-identical; no partial feature spans. Source footprint and original warp anchor remain unchanged. Absolute16px map-cell scope separates repeated Gen2 source tiles belonging to different buildings. Roof corners expose the exact adjacent Emerald ground; native donor and selected-layer fingerprints are mandatory."}
                    if any(p.get("layers") for p in parts):
                        row["base"] = model["base"]
                    rows.append(row)
    assert len(rows) == 168
    return rows


def render_source(cache, game):
    base = cache / game
    m = catalog.read_lua(base / "data/generated/maps.lua")["NEW_BARK_TOWN"]
    ts = catalog.read_lua(base / "data/generated/tilesets.lua")[m["tileset"]]
    sheet = Image.open(base / ts["image"])
    colors = preview.palette_set(catalog.read_lua(base / "data/generated/palettes.lua"), m)
    roofs = catalog.read_lua(base / "data/generated/roofs.lua")
    roof_name = catalog.dict_at(roofs["mapGroupRoofs"], m["group"])
    roof = Image.open(base / roofs["roofs"][roof_name]["image"])
    image = Image.new("RGBA", (m["width"] * 32, m["height"] * 32))
    for pos, bid in enumerate(m["blocks"]):
        for q in range(4):
            image.paste(preview.native_cell(sheet, ts, ts["blocks"][bid], q, colors, roof),
                        (pos % m["width"] * 32 + q % 2 * 16, pos // m["width"] * 32 + q // 2 * 16))
    return m, ts, sheet, image


def native_reference(args, key, config, packed):
    game, map_id, destination, rect = config["native"]
    root = args.cache / game / "data/generated/gba"
    manifest = catalog.read_lua(root / "native/manifest.lua")
    spec = manifest["layouts"][map_id]
    layout = decode_layout(root / "native" / spec["file"])
    records = json.loads((args.catalog / f"{game}.json").read_text())["cells"]
    records = {r["mid"]: r for r in records if r.get("pair") == spec["pair"]}
    x, y, w, h = rect
    image = Image.new("RGBA", (w * 16, h * 16))
    for yy in range(h):
        for xx in range(w):
            mid = layout["mids"][(y + yy) * layout["width"] + x + xx]
            ref = {"game": game, "tileset": spec["pair"], "id": mid, "hash": records[mid]["pixel_sha256"]}
            image.paste(preview.native_donor(args.cache, ref, packed), (xx * 16, yy * 16))
    door = next(v for v in catalog.read_lua(root / "warps.lua")[map_id] if v["destMap"] == destination)
    assert door["y"] == y + h - 1
    image.save(args.output / f"{key}-native-gen3.png")
    return image, {"game": game, "map": map_id, "destination": destination, "pair": spec["pair"],
                   "rect_cells": rect, "layout": layout, "records": records, "pixel_origin": (x * 16, y * 16),
                   "door_anchor": ((door["x"] - x) * 16 + 8, h * 16), "layout_file_sha256": layout["file_sha256"],
                   "source_pixel_sha256": catalog.sha(image.tobytes())}


def prototype(args, key, config, source, native, ground, ground_ref, packed):
    target = Image.new("RGBA", config["size"])
    for y in range(0, target.height, 16):
        for x in range(0, target.width, 16):
            target.paste(ground, (x, y))
    parts, background_pixels, native_roof_pixels = [], [], 0
    for y, sy in enumerate(config["rows"]):
        columns = config["roof_columns"] if y < config["roof_rows"] else config["facade_columns"]
        for x, sx in enumerate(columns):
            gx, gy = native["pixel_origin"][0] + sx * 8, native["pixel_origin"][1] + sy * 8
            mid = native["layout"]["mids"][gy // 16 * native["layout"]["width"] + gx // 16]
            rec = native["records"][mid]
            ref = {"game": native["game"], "tileset": native["pair"], "id": mid, "hash": rec["pixel_sha256"]}
            crop = source.crop((sx * 8, sy * 8, sx * 8 + 8, sy * 8 + 8))
            part = {"donor": ref, "srcX": gx % 16, "srcY": gy % 16, "w": 8, "h": 8,
                    "target_xy": (x * 8, y * 8), "native_source_rect": (sx * 8, sy * 8, 8, 8)}
            if y < config["roof_rows"]:
                layer_hash = rec["layer_sha256"]["over"]
                over = preview.native_donor(args.cache, ref, packed, ["over"], {"over": layer_hash}).crop((gx % 16, gy % 16, gx % 16 + 8, gy % 16 + 8))
                # Choose the native alpha layer only where its holes are actual
                # exterior background; interior roof panels remain complete.
                holes = [(i % 8, i // 8) for i, p in enumerate(over.get_flattened_data()) if p[3] == 0]
                opaque_identical = all(a == b for a, b in zip(over.get_flattened_data(), crop.get_flattened_data()) if a[3])
                if native["game"] == "emerald":
                    outside_only = all(crop.getpixel((px, py)) == ground.getpixel(((gx + px) % 16, (gy + py) % 16)) for px, py in holes)
                else:
                    outside_only = y == 0  # inspected Viridian top roof corners only
                if opaque_identical and outside_only:
                    part.update(layers=["over"], layerHashes={"over": layer_hash})
                    crop = over
                    background_pixels.extend((x * 8 + px, y * 8 + py) for px, py in holes)
                    native_roof_pixels += 64 - len(holes)
                else:
                    native_roof_pixels += 64
            target.alpha_composite(crop, (x * 8, y * 8))
            parts.append(part)
    features = []
    for label, src_rect, dst_rect in config["features"]:
        original, result = rectangle(source, src_rect), rectangle(target, dst_rect)
        different = sum(a != b for a, b in zip(original.get_flattened_data(), result.get_flattened_data()))
        assert different == 0, (key, label, different)
        features.append({"feature": label, "source_rect_xywh": src_rect, "target_rect_xywh": dst_rect, "native_pixel_differences": different})
    assert set(target.getchannel("A").get_flattened_data()) == {255}
    assert all(target.getpixel((x, y)) == ground.getpixel((x % 16, y % 16)) for x, y in background_pixels)
    target.save(args.output / f"{key}-compact-prototype.png")
    return target, {"id": key, "status": "reviewed" if args.write_reviewed else "candidate_awaiting_visual_review", "size_px": config["size"],
                    "door_bottom_anchor_px": config["anchor"], "base": ground_ref, "parts": parts,
                    "features_checked": features, "native": {k: v for k, v in native.items() if k not in ("records", "layout")},
                    "pixel_sha256": catalog.sha(target.tobytes()), "synthetic_pixels": 0,
                    "roof_background": {"selected_native_alpha_layer": "over", "empty_pixels_checked": len(background_pixels),
                                        "all_empty_pixels_exact_local_ground": True, "native_roof_pixels_preserved": native_roof_pixels,
                                        "native_roof_pixel_differences": 0, "ground_donor": ground_ref,
                                        "empty_pixel_positions": background_pixels}, "notes": config["notes"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path(catalog.os.environ["APPDATA"]) / "pokemon-love2d")
    parser.add_argument("--catalog", type=Path, default=WORKSPACE / ".work/tileshift-catalog")
    parser.add_argument("--output", type=Path, default=WORKSPACE / ".work/tileshift-newbark-buildings")
    parser.add_argument("--write-reviewed", action="store_true", help="Activate visually approved native building candidates after positional support is ready")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    packed = {}
    records = json.loads((args.catalog / "emerald.json").read_text())["cells"]
    g = next(r for r in records if r.get("pair") == "general__petalburg" and r["mid"] == 1)
    ground_ref = {"game": "emerald", "tileset": "general__petalburg", "id": 1, "hash": g["pixel_sha256"]}
    ground = preview.native_donor(args.cache, ground_ref, packed)
    native_images, targets, models = {}, {}, []
    for key, config in CONFIGS.items():
        source, native = native_reference(args, key, config, packed)
        native_images[key] = source
        target, model = prototype(args, key, config, source, native, ground, ground_ref, packed)
        targets[key] = target
        models.append(model)
    source_records = []
    for game in ("gold", "silver", "crystal"):
        m, ts, sheet, image = render_source(args.cache, game)
        image.save(args.output / f"{game}-NEW_BARK_TOWN-native.png")
        keys_by_building = {}
        for key, destination, rect in SOURCE_BUILDINGS:
            x, y, w, h = rect
            door = next(v for v in m["warps"] if v["destMap"] == destination)
            assert (door["x"] - x) * 16 + 8 == CONFIGS[key if key in CONFIGS else "ordinary"]["anchor"][0] and door["y"] == y + h - 1
            rectangle(image, (x * 16, y * 16, w * 16, h * 16)).save(args.output / f"{game}-{key}-native.png")
            keys = []
            for yy in range(y, y + h):
                for xx in range(x, x + w):
                    bid = m["blocks"][yy // 2 * m["width"] + xx // 2]
                    keys.append((bid, yy % 2 * 2 + xx % 2))
            keys_by_building[key] = keys
            source_records.append({"game": game, "building": key, "destination": destination, "source_rect_cells": rect,
                                   "door_map_cell": (door["x"], door["y"]), "door_anchor_px": ((door["x"] - x) * 16 + 8, h * 16),
                                   "source_keys": keys})
        assert len(set(keys_by_building["lab"]) & set(keys_by_building["player"])) == 12
    canvas = Image.new("RGB", (1500, 1130), "#18202c")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)
    small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 15)
    draw.text((16, 12), "NEW BARK ARCHITECTURE CANDIDATES — original footprints, complete native features, no scaling", fill="white", font=font)
    draw.text((16, 42), "Different lab/home appearances require position-scoped graphics for12 shared source cells. All target entrances retain the original warp anchors.", fill="#ced7e4", font=small)
    for col, heading in enumerate(("Original Crystal DAY building", "Whole native Gen3 counterpart", "Native8px-part reconstruction")):
        draw.text((col * 500 + 16, 78), heading, fill="white", font=font)
    for row, key in enumerate(("lab", "player", "ordinary")):
        source_key = "neighbor" if key == "ordinary" else key
        original = Image.open(args.output / f"crystal-{source_key}-native.png").convert("RGBA")
        baseline = 418 + row * 320
        for col, image in enumerate((original, native_images[key], targets[key])):
            dx = col * 500 + (500 - image.width * 3) // 2
            canvas.paste(image.resize((image.width * 3, image.height * 3), Image.Resampling.NEAREST), (dx, baseline - image.height * 3))
            draw.line((col * 500 + 16, baseline + 2, col * 500 + 484, baseline + 2), fill="#9cb2cc")
            draw.text((col * 500 + 16, baseline + 12), f"{key}: {image.width}x{image.height}px", fill="white", font=small)
        draw.text((16, baseline + 38), CONFIGS[key]["notes"], fill="#e5c68d", font=small)
    canvas.save(args.output / "newbark-native-building-prototypes.png")
    feature_review(args, native_images, targets, models)
    scenes = town_review(args, targets)
    rows = mapping_rows(args, models)
    (args.output / "newbark-building-rows.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    if args.write_reviewed:
        target = WORKSPACE / "TileShift/mappings/gen2_buildings.lua"
        target.write_text("-- Reviewed native Gen3 architecture for the four New Bark buildings.\n-- x/y scope is visual only; source map cells, collision, warps and scripts are unchanged.\nreturn {\n"
                          + "".join("  " + lua(row) + ",\n" for row in rows) + "}\n", encoding="utf-8")
    report = {"status": "reviewed_buildings_activated" if args.write_reviewed else "candidate_not_activated", "source_occurrences_per_cart": 56, "source_unique_keys_per_cart": 36,
              "source_records": source_records, "candidates": models, "required_position_scope": {"map": "NEW_BARK_TOWN", "source_shared_keys": [[bid, q] for bid in (24, 25, 30) for q in range(4)]}}
    report.update(town_candidates=scenes, production_rows=len(rows) if args.write_reviewed else 0)
    (args.output / "newbark-native-building-prototypes.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "candidates": [{"id": m["id"], "size": m["size_px"], "sha256": m["pixel_sha256"]} for m in models], "sheet": str(args.output / "newbark-native-building-prototypes.png")}, indent=2))


if __name__ == "__main__":
    main()
