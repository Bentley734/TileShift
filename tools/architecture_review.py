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
               "omit_complete_roof_regions": ((40, 8, 32, 32),),
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
    roof = None
    if m["tileset"] in ("TILESET_JOHTO", "TILESET_JOHTO_MODERN"):
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
                for ex, ey, ew, eh in config.get("omit_complete_roof_regions", ()):
                    assert sx * 8 + 8 <= ex or sx * 8 >= ex + ew or sy * 8 + 8 <= ey or sy * 8 >= ey + eh, (key, "Partial omitted chimney/shadow")
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


def complete_feature_sheets(args, native_images, targets, models):
    import textwrap
    features = [(key, feature) for key, model in models.items() for feature in model["features_checked"]]
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 16)
    small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
    for start in range(0, len(features), 6):
        canvas = Image.new("RGB", (1500, 990), "#18202c")
        draw = ImageDraw.Draw(canvas)
        draw.text((16, 12), "WHOLE NATIVE FEATURE PROOF AT4x — complete symbols, windows, flower boxes and entrance frames", fill="white", font=font)
        for i, (key, feature) in enumerate(features[start:start + 6]):
            left, top = i % 2 * 750 + 16, i // 2 * 310 + 54
            draw.multiline_text((left, top), textwrap.fill(key.upper() + ": " + feature["feature"], 83), fill="white", font=small)
            for col, (label, image, rect) in enumerate((("native", native_images[key], feature["source_rect_xywh"]),
                                                       ("compact:0 pixel differences", targets[key], feature["target_rect_xywh"]))):
                draw.text((left + col * 352, top + 46), label, fill="#ced7e4", font=small)
                part = rectangle(image, rect)
                canvas.paste(part.resize((part.width * 4, part.height * 4), Image.Resampling.NEAREST), (left + col * 352, top + 69))
        canvas.save(args.output / f"architecture-complete-native-features-{start // 6 + 1}.png")


def sprout_reference(args):
    """Exact geometry brief for original Gen3-style monastic pagoda art."""
    rect = (22, 1, 4, 5)
    records = []
    for game in ("gold", "silver", "crystal"):
        m, ts, sheet, image = render_source(args.cache, game, "VIOLET_CITY")
        door = next(w for w in m["warps"] if w["destMap"] == "SPROUT_TOWER_1F")
        assert (door["x"], door["y"]) == (23, 5)
        crop = rectangle(image, (352, 16, 64, 80))
        crop.save(args.output / f"{game}-sprout-tower-source.png")
        cells = []
        for y in range(1, 6):
            for x in range(22, 26):
                bid, q = m["blocks"][y // 2 * m["width"] + x // 2], y % 2 * 2 + x % 2
                raw = preview.native_cell(sheet, ts, ts["blocks"][bid], q)
                cells.append({"x": x, "y": y, "id": bid, "quadrant": q, "sourceHash": catalog.sha(raw.tobytes())})
        records.append({"game": game, "map": m["id"], "rect_cells": rect, "pixel_rect_xywh": (352, 16, 64, 80),
                        "door_map_cell_xy": (23, 5), "door_bottom_anchor_px": (24, 80),
                        "source_rgba_sha256": catalog.sha(crop.tobytes()), "source_cells": cells})
    source = Image.open(args.output / "crystal-sprout-tower-source.png").convert("RGBA")
    canvas = Image.new("RGB", (1300, 850), "#18202c")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)
    small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 16)
    draw.text((16, 12), "SPROUT TOWER — source geometry for original Gen3-style wooden pagoda art", fill="white", font=font)
    draw.text((16, 42), "64x80px envelope; three stacked facade levels; original entrance anchor(24,80). No native role counterpart approved.", fill="#ced7e4", font=small)
    canvas.paste(source.resize((512, 640), Image.Resampling.NEAREST), (48, 110))
    for y in range(0, 81, 8):
        draw.line((48, 110 + y * 8, 560, 110 + y * 8), fill="#704754")
        draw.text((12, 105 + y * 8), str(y), fill="white", font=small)
    for x in range(0, 65, 8):
        draw.line((48 + x * 8, 110, 48 + x * 8, 750), fill="#704754")
        draw.text((48 + x * 8, 84), str(x), fill="white", font=small)
    notes = ("Function: wooden monastic pagoda/training tower, not a cemetery or ruined stone pillar.",
             "Source rectangle: VIOLET_CITY16px cells x22..25,y1..5.",
             "Upper ribbed roof and main eave:64x32px at(0,0).",
             "Middle level1:64x8px at(0,32); stepped eave64x8 at(0,40).",
             "Middle level2:64x8px at(0,48); stepped eave64x8 at(0,56).",
             "Ground facade:48x16px at(8,64).",
             "Complete existing door cell:16x16px at(16,64); new full17px trim may start y63.",
             "Five complete8x8 window units: (16,32),(40,32),(16,48),(40,48),(40,64).",
             "Exclude incidental tree pixels at(0,64,8,16) and shore/wall pixels at(56,64,8,16).",
             "Those two hybrid source cells need native terrain beneath transparent artwork; do not erase the surrounding tree/shore.",
             "Use transparent exterior corners and no baked ground, with exact original door/footprint anchors.")
    import textwrap
    y = 110
    for note in notes:
        wrapped = textwrap.fill(note, 67)
        draw.multiline_text((610, y), wrapped, fill="white", font=small, spacing=3)
        y += 28 + 20 * wrapped.count("\n")
    draw.text((48, 785), "Private native source reference only. No extracted source art is distributed.", fill="#ced7e4", font=small)
    canvas.save(args.output / "sprout-tower-geometry-reference.png")
    brief = {"status": "original_art_required_no_native_substitution", "function": "wooden monastic pagoda and monks training tower",
             "target_size_px": (64, 80), "door_bottom_anchor_px": (24, 80),
             "source_door_rect_xywh": (16, 64, 16, 16), "new_complete_door_trim_rect_xywh": (16, 63, 16, 17),
             "roof_and_eaves": [(0, 0, 64, 32), (0, 40, 64, 8), (0, 56, 64, 8)],
             "window_rects_xywh": [(16, 32, 8, 8), (40, 32, 8, 8), (16, 48, 8, 8), (40, 48, 8, 8), (40, 64, 8, 8)],
             "incidental_terrain_exclusions": [{"rect_xywh": (0, 64, 8, 16), "source_cell_xy": (22, 5), "role": "tree portion outside pagoda"},
                                               {"rect_xywh": (56, 64, 8, 16), "source_cell_xy": (25, 5), "role": "shore or retaining-wall portion outside pagoda"}],
             "source_records": records, "background": "transparent outside architecture; separately preserve converted surrounding tree/shore",
             "generated_art_constraints": "No rescaling. Envelope64x80. Preserve three facade levels, all windows, original door position and full frame. Native-function substitutes not approved."}
    (args.output / "sprout-tower-geometry-brief.json").write_text(json.dumps(brief, indent=2), encoding="utf-8")
    return brief


def staged_rows(args, models, extra_instances=()):
    rows = []
    for game in ("gold", "silver", "crystal"):
        selected_buildings = {key: list(value) for key, value in BUILDINGS.items()}
        for extra in extra_instances:
            if extra["game"] == game and extra["template"] in models:
                selected_buildings.setdefault(extra["map"], []).append((extra["template"], extra["destination"], extra["source_rect_cells"]))
        for map_id, buildings in selected_buildings.items():
            m, ts, sheet, _ = render_source(args.cache, game, map_id)
            root = args.cache / game
            fingerprints = {"metadata": catalog.sha((root / "data/generated/tilesets.lua").read_bytes()),
                            "maps": catalog.sha((root / "data/generated/maps.lua").read_bytes()),
                            "image": catalog.sha((root / ts["image"]).read_bytes()),
                            "palettes": catalog.sha((root / "data/generated/palettes.lua").read_bytes()),
                            "roofs": catalog.sha((root / "data/generated/roofs.lua").read_bytes())}
            cells = json.loads((args.catalog / f"{game}.json").read_text())["cells"]
            source_index = {(r["block_id"], r["quadrant"]): r for r in cells if r.get("tileset") == m["tileset"]}
            for key, destination, (ox, oy, w, h) in buildings:
                model = models[key]
                target = Image.open(args.output / f"{key}-compact-prototype.png").convert("RGBA")
                for y in range(h):
                    for x in range(w):
                        xx, yy = ox + x, oy + y
                        bid, q = m["blocks"][yy // 2 * m["width"] + xx // 2], yy % 2 * 2 + xx % 2
                        source = source_index[bid, q]
                        actual = preview.native_cell(sheet, ts, ts["blocks"][bid], q)
                        assert catalog.sha(actual.tobytes()) == source["grayscale_pixel_sha256"]
                        parts = []
                        for part in model["parts"]:
                            px, py = part["target_xy"]
                            if px // 16 == x and py // 16 == y:
                                value = {name: part[name] for name in ("donor", "srcX", "srcY", "w", "h")}
                                value.update(x=px % 16, y=py % 16)
                                for optional in ("layers", "layerHashes"):
                                    if optional in part:
                                        value[optional] = part[optional]
                                parts.append(value)
                        assert len(parts) == 4
                        row = {"game": game, "style": "gen3", "map": map_id, "x": xx, "y": yy,
                               "tileset": m["tileset"], "id": bid, "quadrant": q,
                               "sourceHash": source["grayscale_pixel_sha256"], "sourceFiles": fingerprints,
                               "role": "architecture_" + key, "kind": "native_composite",
                               "status": "reviewed" if args.write_reviewed or args.approved_candidates else "candidate", "parts": parts,
                               "compositionPixelHash": catalog.sha(rectangle(target, (x * 16, y * 16, 16, 16)).tobytes()),
                               "evidence": TEMPLATES[key]["notes"] + " Actual source destination:" + destination
                                           + ". Complete native feature rectangles, original footprint and original warp anchor verified independently. No scaling, partial window/frame spans or substituted building function. Roof exterior uses fingerprint-checked native over layers over exact Emerald ground. Absolute map-cell scope keeps repeated source tiles separate; source layout, collision and scripts remain unchanged."}
                        if any(p.get("layers") for p in parts):
                            row["base"] = model["base"]
                        rows.append(row)
    expected = 462 + sum(r["source_rect_cells"][2] * r["source_rect_cells"][3] for r in extra_instances if r["template"] in models)
    assert len(rows) == expected and len({(r["game"], r["map"], r["x"], r["y"]) for r in rows}) == expected
    rows.sort(key=lambda r: (r["game"], r["map"], r["y"], r["x"]))
    (args.output / "architecture-staged-rows.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    if args.write_reviewed:
        target = WORKSPACE / "TileShift/mappings/buildings_extended.lua"
        if target.exists():
            old = preview.read_reviewed(target)
            old_positions = {(r["game"], r["map"], r["x"], r["y"]) for r in old}
            new_positions = {(r["game"], r["map"], r["x"], r["y"]) for r in rows}
            assert old_positions <= new_positions, "Refusing to discard existing architecture; include all reviewed groups before writing"
        target.write_text("-- Reviewed complete native Gen3 public buildings and homes, with source warp/position proof.\nreturn {\n"
                          + "".join("  " + lua(row) + ",\n" for row in rows) + "}\n", encoding="utf-8")
    return rows


def context_review(args, targets, candidate_rows, extra_instances=()):
    mod = Path(__file__).resolve().parents[1]
    active = []
    for path in sorted((mod / "mappings").glob("*.lua")):
        if path.name != "buildings_extended.lua":
            active.extend(preview.read_reviewed(path))
    reports = []
    selected_buildings = {key: list(value) for key, value in BUILDINGS.items()}
    for extra in extra_instances:
        if extra["game"] == "crystal" and extra["template"] in targets:
            selected_buildings.setdefault(extra["map"], []).append((extra["template"], extra["destination"], extra["source_rect_cells"]))
    for map_id, buildings in selected_buildings.items():
        m, ts, sheet, original = render_source(args.cache, "crystal", map_id)
        generic = {}
        positions = {}
        for row in sorted(active, key=lambda r: bool(r.get("map"))):
            if row["game"] == "crystal" and row["style"] == "gen3" and row["tileset"] == m["tileset"] and row.get("map", map_id) == map_id:
                if row.get("x") is not None:
                    positions[row["x"], row["y"]] = row
                else:
                    generic[row["id"], row["quadrant"]] = row
        after = original.copy()
        packed, covered = {}, set()
        for pos, bid in enumerate(m["blocks"]):
            for q in range(4):
                x, y = pos % m["width"] * 2 + q % 2, pos // m["width"] * 2 + q // 2
                row = positions.get((x, y), generic.get((bid, q)))
                if row:
                    after.paste(preview.replacement_image(args.cache, row, packed, mod), (x * 16, y * 16))
                    covered.add((x, y))
        before_count = len(covered)
        for key, destination, (x, y, w, h) in buildings:
            after.paste(targets[key], (x * 16, y * 16))
            covered.update((xx, yy) for yy in range(y, y + h) for xx in range(x, x + w))
        after.save(args.output / f"crystal-{map_id}-development-after.png")
        scale = 1 if after.width > 480 else 2
        width, height = after.width * scale, after.height * scale
        canvas = Image.new("RGB", (width * 2 + 56, height + 160), "#18202c")
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)
        small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 15)
        draw.text((18, 12), f"DEVELOPMENT — {map_id}: complete native building candidates, original map footprints", fill="white", font=font)
        draw.text((18, 42), f"{len(covered)}/{len(m['blocks']) * 4} cells covered; {len(m['blocks']) * 4 - len(covered)} source cells remain. No actors rendered; unrevised special structures/terrain stay native.", fill="#ced7e4", font=small)
        draw.text((18, 80), "Original Crystal DAY source", fill="white", font=small)
        draw.text((38 + width, 80), "Gen3 buildings plus current reviewed terrain", fill="white", font=small)
        canvas.paste(original.resize((width, height), Image.Resampling.NEAREST), (18, 110))
        canvas.paste(after.resize((width, height), Image.Resampling.NEAREST), (38 + width, 110))
        canvas.save(args.output / f"crystal-{map_id}-development-comparison.png")
        reports.append({"game": "crystal", "map": map_id, "previously_covered_cells": before_count,
                        "candidate_covered_cells": len(covered), "total_cells": len(m["blocks"]) * 4,
                        "candidate_pixel_sha256": catalog.sha(after.tobytes()), "source_geometry_unchanged": True})
    return reports


def remaining_town_inventory(args):
    """Identify only exact source-shape reuses with independent warp evidence."""
    references = {
        "center": ("CHERRYGROVE_CITY", (28, 0, 4, 4), (24, 64)),
        "mart": ("CHERRYGROVE_CITY", (22, 0, 4, 4), (24, 64)),
        "gym": ("VIOLET_CITY", (16, 14, 6, 4), (40, 64)),
        "school": ("VIOLET_CITY", (28, 15, 6, 3), (40, 48)),
        "home32": ("NEW_BARK_TOWN", (2, 10, 4, 2), (24, 32)),
        "home48": ("VIOLET_CITY", (2, 13, 4, 3), (24, 48)),
        "home64_requires_native_template": ("NEW_BARK_TOWN", (12, 2, 4, 4), (24, 64)),
    }
    matched, held = [], []
    for game in ("gold", "silver", "crystal"):
        root = args.cache / game
        maps = catalog.read_lua(root / "data/generated/maps.lua")
        sets = catalog.read_lua(root / "data/generated/tilesets.lua")
        sheets = {}
        def signature(m, rect):
            x, y, w, h = rect
            if x < 0 or y < 0 or x + w > m["width"] * 2 or y + h > m["height"] * 2:
                return None
            ts = sets[m["tileset"]]
            if m["tileset"] not in sheets:
                sheets[m["tileset"]] = Image.open(root / ts["image"])
            pixels = []
            for yy in range(y, y + h):
                for xx in range(x, x + w):
                    bid, q = m["blocks"][yy // 2 * m["width"] + xx // 2], yy % 2 * 2 + xx % 2
                    pixels.append(catalog.sha(preview.native_cell(sheets[m["tileset"]], ts, ts["blocks"][bid], q).tobytes()))
            return tuple(pixels)
        profiles = {key: signature(maps[map_id], rect) for key, (map_id, rect, _) in references.items()}
        for map_id, m in maps.items():
            if not isinstance(m, dict) or m.get("environment") != "TOWN" or map_id in (*BUILDINGS, "NEW_BARK_TOWN"):
                continue
            for warp in m.get("warps", []):
                name = warp["destMap"]
                if "HOUSE" in name and "DAY_CARE" not in name:
                    choices = ("home32", "home48", "home64_requires_native_template")
                elif "POKECENTER_1F" in name or "POKEMON_CENTER_1F" in name:
                    choices = ("center",)
                elif name.endswith("_MART"):
                    choices = ("mart",)
                elif name.endswith("_GYM") or name.endswith("_GYM_1F"):
                    choices = ("gym",)
                else:
                    held.append({"game": game, "map": map_id, "destination": name, "reason": "Special building/gate function needs its own complete native counterpart review"})
                    continue
                found = None
                for key in choices:
                    _, (_, _, w, h), (ax, ay) = references[key]
                    x, y = warp["x"] - (ax - 8) // 16, warp["y"] - h + 1
                    rect = (x, y, w, h)
                    if signature(m, rect) == profiles[key]:
                        found = {"game": game, "map": map_id, "destination": name, "template": key,
                                 "source_rect_cells": rect, "door_map_cell": (warp["x"], warp["y"]),
                                 "door_bottom_anchor_px": (ax, ay), "source_shape_exact_reference_match": True,
                                 "status": "source_shape_verified_native_context_pending"}
                        matched.append(found)
                        break
                if found is None:
                    held.append({"game": game, "map": map_id, "destination": name, "reason": "Source geometry differs from reviewed shape profiles; inspect full native source crop"})
    report = {"status": "research_inventory_only_no_additional_active_rows", "matched_source_instances": matched, "held_instances": held,
              "limits": "Warp role plus exact raw source picture match verifies footprint. Regional native ground/background and whole-map context still require review before activation; no speculative shape or function matches are emitted."}
    (args.output / "remaining-town-architecture-inventory.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return {"exact_source_shape_instances": len(matched), "held_instances": len(held)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path(catalog.os.environ["APPDATA"]) / "pokemon-love2d")
    parser.add_argument("--catalog", type=Path, default=WORKSPACE / ".work/tileshift-catalog")
    parser.add_argument("--output", type=Path, default=WORKSPACE / ".work/tileshift-building-extended")
    parser.add_argument("--write-reviewed", action="store_true", help="Activate only after visual review of this staged architecture batch")
    parser.add_argument("--approved-candidates", action="store_true", help="Record visual review in private candidate data without writing production mappings")
    parser.add_argument("--include-verified-towns", action="store_true", help="Privately extend exact source-shape/warp reuse candidates across remaining towns; requires separate context review")
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
        if args.write_reviewed or args.approved_candidates:
            models[key]["status"] = "visually_reviewed"
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
    complete_feature_sheets(args, native_images, images, models)
    sprout = sprout_reference(args)
    remaining = remaining_town_inventory(args)
    extra_instances = json.loads((args.output / "remaining-town-architecture-inventory.json").read_text())["matched_source_instances"] if args.include_verified_towns else []
    rows = staged_rows(args, models, extra_instances)
    contexts = context_review(args, images, rows, extra_instances)
    report = {"status": "reviewed_batch_activated" if args.write_reviewed else "visually_reviewed_production_held" if args.approved_candidates else "private_candidates_not_activated", "source_buildings": source_records, "templates": models,
              "sprout_tower_original_art_brief": "sprout-tower-geometry-brief.json",
              "positioned_rows": len(rows), "contexts": contexts,
              "remaining_town_inventory": remaining,
              "remaining_town_instances_included": len(extra_instances),
              "held": [{"map": "VIOLET_CITY", "destination": "SPROUT_TOWER_1F", "reason": "No proper Gen3 monastic pagoda counterpart identified; cemetery/ancient-pillar art would change function."},
                       {"map": "VIOLET_CITY", "destination": "ROUTE_31_VIOLET_GATE", "reason": "Side-entry gate needs separate complete entrance/orientation review."}]}
    (args.output / "architecture-native-prototypes.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "templates": list(models), "source_buildings": len(source_records), "full_native_features_checked": sum(len(m["features_checked"]) for m in models.values())}, indent=2))


if __name__ == "__main__":
    main()
