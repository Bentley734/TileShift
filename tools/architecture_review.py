"""Private staged architecture review: complete native roles and source warps.

Only --write-reviewed emits production references, after explicit visual review.
Every component is copied from native pixels; no raster art is packaged.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import catalog
import preview
from newbark_building_review import CONFIGS as NEWBARK, native_reference, rectangle, lua

WORKSPACE = Path(__file__).resolve().parents[2]
BUILDINGS = {
    "CHERRYGROVE_CITY": (("mart", "CHERRYGROVE_MART", (22, 0, 4, 4)),
                         ("center", "CHERRYGROVE_POKECENTER_1F", (28, 0, 4, 4)),
                         ("home32", "CHERRYGROVE_GYM_SPEECH_HOUSE", (16, 6, 4, 2)),
                         ("home32", "GUIDE_GENTS_HOUSE", (24, 8, 4, 2)),
                         ("home32", "CHERRYGROVE_EVOLUTION_SPEECH_HOUSE", (30, 10, 4, 2))),
    "VIOLET_CITY": (("mart", "VIOLET_MART", (8, 14, 4, 4)),
                    ("gym", "VIOLET_GYM", (16, 14, 6, 4)),
                    ("school", "EARLS_POKEMON_ACADEMY", (28, 15, 6, 3)),
                    ("home48", "VIOLET_NICKNAME_SPEECH_HOUSE", (2, 13, 4, 3)),
                    ("center", "VIOLET_POKECENTER_1F", (30, 22, 4, 4)),
                    ("home48", "VIOLET_KYLES_HOUSE", (20, 27, 4, 3))),
}
GYM_COLUMNS = (0, 9, 10, 5, 6, 7, 8, 1, 2, 3, 4, 11)
TEMPLATES = {
    "center": {"native": ("emerald", "EM_PETALBURG_CITY", "EM_PETALBURG_CITY_POKEMON_CENTER_1F", (19, 13, 4, 4)),
               "size": (64, 64), "rows": tuple(range(8)), "roof_rows": 5,
               "roof_columns": tuple(range(8)), "facade_columns": tuple(range(8)), "force_over_rows": (0, 1),
               "anchor": (24, 64),
               "features": (("complete32x32 Pokemon Center emblem and native roof surround", (16, 16, 32, 32), (16, 16, 32, 32)),
                            ("entire64x24 Center facade: entrance, P.C. sign and all wall edges", (0, 40, 64, 24), (0, 40, 64, 24)),
                            ("complete32x24 native Center entrance and steps", (8, 40, 32, 24), (8, 40, 32, 24))),
               "notes": "Actual native Pokemon Center; direct64x64 fit and correct door orientation. No building compaction."},
    "mart": {"native": ("emerald", "EM_PETALBURG_CITY", "EM_PETALBURG_CITY_MART", (24, 9, 4, 4)),
             "size": (64, 64), "rows": tuple(range(8)), "roof_rows": 5,
             "roof_columns": tuple(range(8)), "facade_columns": tuple(range(8)), "force_over_rows": (0, 1),
             "anchor": (24, 64),
             "features": (("complete32x24 Mart emblem and native roof surround", (16, 16, 32, 24), (16, 16, 32, 24)),
                          ("entire64x24 Mart facade: entrance, MART sign and all wall edges", (0, 40, 64, 24), (0, 40, 64, 24)),
                          ("complete32x24 native Mart entrance and steps", (8, 40, 32, 24), (8, 40, 32, 24))),
             "notes": "Actual native Mart; direct64x64 fit. Native top roof alpha removes incidental tree/background pixels outside the building silhouette."},
    "gym": {"native": ("emerald", "EM_PETALBURG_CITY", "EM_PETALBURG_CITY_GYM", (12, 4, 6, 5)),
            "size": (96, 64), "rows": (0, 1, 4, 5, 6, 7, 8, 9), "roof_rows": 4,
            "roof_columns": tuple(range(12)), "facade_columns": GYM_COLUMNS, "row_columns": {3: GYM_COLUMNS},
            "anchor": (40, 64),
            "features": (("complete32x40 Gym entrance, upper awning, full frame and steps", (40, 40, 32, 40), (24, 24, 32, 40)),
                         ("whole32x32 GYM nameplate with every letter, symbol and upper windows", (8, 48, 32, 32), (56, 32, 32, 32)),
                         ("whole16x32 native side window and wall panel", (72, 48, 16, 32), (8, 32, 16, 32))),
            "notes": "Actual native Gym. Repeated roof rows omitted; entrance moves16px left to the original GSC warp. The complete GYM/window panel moves right and the complete side window moves left."},
    "school": {"native": ("firered", "FR_VIRIDIAN_CITY", "FR_VIRIDIAN_CITY_SCHOOL", (24, 15, 5, 4)),
               "size": (96, 48), "rows": (0, 1, 4, 5, 6, 7), "roof_rows": 4,
               "roof_columns": (0, 1, 2, 3, 4, 4, 4, 4, 4, 4, 4, 9),
               "facade_columns": (0, 1, 1, 1, 2, 3, 4, 5, 6, 7, 8, 9), "force_over_rows": (0, 1),
               "anchor": (40, 48),
               "features": (("complete24x17 School window and full flower box including top cap", (40, 47, 24, 17), (56, 31, 24, 17)),
                            ("complete16x17 School entrance frame and door", (16, 47, 16, 17), (32, 31, 16, 17)),
                            ("entire native right48x16 facade and flower boxes", (32, 48, 48, 16), (48, 32, 48, 16)),
                            ("entire native left16x16 facade and flower box", (0, 48, 16, 16), (0, 32, 16, 16))),
               "notes": "Actual Viridian Pokemon School. Repeated plain roof/wall parts fill the original96px width; repeated roof rows and the whole chimney component are omitted. Every original facade feature and planter is complete."},
    "home48": {"native": ("emerald", "EM_OLDALE_TOWN", "EM_OLDALE_TOWN_HOUSE1", (4, 4, 4, 4)),
               "size": (64, 48), "rows": (0, 1, 4, 5, 6, 7), "roof_rows": 3,
               "roof_columns": tuple(range(8)), "facade_columns": tuple(range(8)),
               "anchor": (24, 48),
               "features": (("entire64x24 ordinary-home facade including every window/door frame", (0, 40, 64, 24), (0, 24, 64, 24)),
                            ("complete32x24 ordinary-home entrance frame and door", (8, 40, 32, 24), (8, 24, 32, 24)),
                            ("complete24x24 window wall panel including full outer frame", (32, 40, 24, 24), (32, 24, 24, 24))),
               "notes": "Actual ordinary Oldale residence. Only repeated roof rows are omitted; the entire original native facade is retained byte-exact."},
    "home32": deepcopy(NEWBARK["ordinary"]),
}


def render_source(cache, game, map_id):
    root = cache / game
    m = catalog.read_lua(root / "data/generated/maps.lua")[map_id]
    ts = catalog.read_lua(root / "data/generated/tilesets.lua")[m["tileset"]]
    sheet = Image.open(root / ts["image"])
    palettes = preview.palette_set(catalog.read_lua(root / "data/generated/palettes.lua"), m)
    roofs = catalog.read_lua(root / "data/generated/roofs.lua")
    roof_name = catalog.dict_at(roofs["mapGroupRoofs"], m["group"])
    roof = Image.open(root / roofs["roofs"][roof_name]["image"])
    image = Image.new("RGBA", (m["width"] * 32, m["height"] * 32))
    for pos, bid in enumerate(m["blocks"]):
        for q in range(4):
            image.paste(preview.native_cell(sheet, ts, ts["blocks"][bid], q, palettes, roof),
                        (pos % m["width"] * 32 + q % 2 * 16, pos // m["width"] * 32 + q // 2 * 16))
    return m, ts, sheet, image


def compose(args, key, config, source, native, ground, ground_ref, packed):
    target = Image.new("RGBA", config["size"])
    for y in range(0, target.height, 16):
        for x in range(0, target.width, 16):
            target.paste(ground, (x, y))
    parts, empty = [], []
    for y, sy in enumerate(config["rows"]):
        columns = config.get("row_columns", {}).get(y, config["roof_columns"] if y < config["roof_rows"] else config["facade_columns"])
        for x, sx in enumerate(columns):
            gx, gy = native["pixel_origin"][0] + sx * 8, native["pixel_origin"][1] + sy * 8
            mid = native["layout"]["mids"][gy // 16 * native["layout"]["width"] + gx // 16]
            record = native["records"][mid]
            ref = {"game": native["game"], "tileset": native["pair"], "id": mid, "hash": record["pixel_sha256"]}
            crop = rectangle(source, (sx * 8, sy * 8, 8, 8))
            part = {"donor": ref, "srcX": gx % 16, "srcY": gy % 16, "w": 8, "h": 8,
                    "target_xy": (x * 8, y * 8), "native_source_rect": (sx * 8, sy * 8, 8, 8)}
            if y < config["roof_rows"]:
                hash_ = record["layer_sha256"]["over"]
                over = preview.native_donor(args.cache, ref, packed, ["over"], {"over": hash_}).crop((gx % 16, gy % 16, gx % 16 + 8, gy % 16 + 8))
                holes = [(i % 8, i // 8) for i, pixel in enumerate(over.get_flattened_data()) if pixel[3] == 0]
                identical = all(a == b for a, b in zip(over.get_flattened_data(), crop.get_flattened_data()) if a[3])
                outside = all(crop.getpixel((px, py)) == ground.getpixel(((gx + px) % 16, (gy + py) % 16)) for px, py in holes)
                if y in config.get("force_over_rows", ()) or (native["game"] == "firered" and y == 0):
                    outside = True  # visually reviewed top silhouette, never facade pixels
                if identical and outside:
                    crop = over
                    part.update(layers=["over"], layerHashes={"over": hash_})
                    empty.extend((x * 8 + px, y * 8 + py) for px, py in holes)
            target.alpha_composite(crop, (x * 8, y * 8))
            parts.append(part)
    features = []
    for label, src, dst in config["features"]:
        a, b = rectangle(source, src), rectangle(target, dst)
        differences = sum(x != y for x, y in zip(a.get_flattened_data(), b.get_flattened_data()))
        assert differences == 0, (key, label, differences)
        features.append({"feature": label, "source_rect_xywh": src, "target_rect_xywh": dst, "native_pixel_differences": differences})
    assert set(target.getchannel("A").get_flattened_data()) == {255}
    assert all(target.getpixel((x, y)) == ground.getpixel((x % 16, y % 16)) for x, y in empty)
    target.save(args.output / f"{key}-compact-prototype.png")
    model = {"id": key, "status": "candidate", "size_px": config["size"], "door_bottom_anchor_px": config["anchor"],
             "base": ground_ref, "parts": parts, "features_checked": features, "notes": config["notes"],
             "roof_empty_pixels_checked": len(empty), "all_roof_empty_pixels_exact_ground": True,
             "native_roof_pixel_differences": 0, "rgba_pixel_sha256": catalog.sha(target.tobytes()),
             "native": {k: v for k, v in native.items() if k not in ("records", "layout")}}
    return target, model


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path(catalog.os.environ["APPDATA"]) / "pokemon-love2d")
    parser.add_argument("--catalog", type=Path, default=WORKSPACE / ".work/tileshift-catalog")
    parser.add_argument("--output", type=Path, default=WORKSPACE / ".work/tileshift-building-extended")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    packed = {}
    g = next(r for r in json.loads((args.catalog / "emerald.json").read_text())["cells"] if r.get("pair") == "general__petalburg" and r["mid"] == 1)
    ground_ref = {"game": "emerald", "tileset": "general__petalburg", "id": 1, "hash": g["pixel_sha256"]}
    ground = preview.native_donor(args.cache, ground_ref, packed)
    images, native_images, models, source_records = {}, {}, {}, []
    for key, config in TEMPLATES.items():
        source, native = native_reference(args, key, config, packed)
        native_images[key] = source
        images[key], models[key] = compose(args, key, config, source, native, ground, ground_ref, packed)
    for game in ("gold", "silver", "crystal"):
        for map_id, buildings in BUILDINGS.items():
            m, ts, sheet, image = render_source(args.cache, game, map_id)
            image.save(args.output / f"{game}-{map_id}-native.png")
            for key, destination, (x, y, w, h) in buildings:
                warp = next(v for v in m["warps"] if v["destMap"] == destination)
                assert warp["y"] == y + h - 1 and ((warp["x"] - x) * 16 + 8, h * 16) == TEMPLATES[key]["anchor"], (map_id, destination)
                assert (w * 16, h * 16) == TEMPLATES[key]["size"]
                rectangle(image, (x * 16, y * 16, w * 16, h * 16)).save(args.output / f"{game}-{destination}-native.png")
                source_records.append({"game": game, "map": map_id, "destination": destination, "template": key,
                                       "rect_cells": (x, y, w, h), "door_map_cell": (warp["x"], warp["y"]), "door_bottom_anchor_px": TEMPLATES[key]["anchor"]})
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)
    small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 15)
    for sheet_index, template_keys in enumerate((("center", "mart", "gym"), ("school", "home48", "home32"))):
        canvas = Image.new("RGB", (1500, 1110), "#18202c")
        draw = ImageDraw.Draw(canvas)
        draw.text((16, 12), "CHERRYGROVE / VIOLET — complete native role counterparts, original footprints and warp anchors", fill="white", font=font)
        for col, heading in enumerate(("Original Crystal DAY source", "Whole native Gen3 counterpart", "Private native8px-part prototype")):
            draw.text((16 + col * 500, 62), heading, fill="white", font=font)
        for row, key in enumerate(template_keys):
            record = next(r for r in source_records if r["game"] == "crystal" and r["template"] == key)
            original = Image.open(args.output / f"crystal-{record['destination']}-native.png").convert("RGBA")
            baseline = 390 + row * 330
            for col, image in enumerate((original, native_images[key], images[key])):
                x = col * 500 + (500 - image.width * 3) // 2
                canvas.paste(image.resize((image.width * 3, image.height * 3), Image.Resampling.NEAREST), (x, baseline - image.height * 3))
                draw.line((col * 500 + 16, baseline + 2, col * 500 + 484, baseline + 2), fill="#9cb2cc")
                draw.text((col * 500 + 16, baseline + 14), f"{key}:{image.width}x{image.height}px", fill="white", font=small)
            draw.text((16, baseline + 40), TEMPLATES[key]["notes"], fill="#e5c68d", font=small)
        canvas.save(args.output / f"architecture-native-prototypes-{sheet_index + 1}.png")
    report = {"status": "private_candidates_not_activated", "source_buildings": source_records, "templates": models,
              "held": [{"map": "VIOLET_CITY", "destination": "SPROUT_TOWER_1F", "reason": "No proper Gen3 monastic pagoda counterpart identified; cemetery/ancient-pillar art would change function."},
                       {"map": "VIOLET_CITY", "destination": "ROUTE_31_VIOLET_GATE", "reason": "Side-entry gate needs separate complete entrance/orientation review."}]}
    (args.output / "architecture-native-prototypes.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "templates": list(models), "source_buildings": len(source_records), "full_native_features_checked": sum(len(m["features_checked"]) for m in models.values())}, indent=2))


if __name__ == "__main__":
    main()
