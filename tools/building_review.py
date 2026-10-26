"""Extract complete native building references without creating mappings/art.

Every crop is a visually checked16px tile rectangle. Door-bottom anchors come
from the imported native warp table. Outputs remain local under .work.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import zlib

from PIL import Image, ImageDraw, ImageFont
import catalog
import preview

WORKSPACE = Path(__file__).resolve().parents[2]
REFERENCES = [
    ("red-home", "red", "PALLET_TOWN", "REDS_HOUSE_1F", [4, 3, 4, 3], "Pallet: trainer's home", "source trainer home"),
    ("red-rival-home", "red", "PALLET_TOWN", "BLUES_HOUSE", [12, 3, 4, 3], "Pallet: rival's home", "source rival home"),
    ("red-oak-lab", "red", "PALLET_TOWN", "OAKS_LAB", [10, 8, 6, 4], "Pallet: Oak's laboratory", "source professor laboratory"),
    ("emerald-brendan-home", "emerald", "EM_LITTLEROOT_TOWN", "EM_LITTLEROOT_TOWN_BRENDANS_HOUSE_1F", [2, 4, 5, 5], "Littleroot: Brendan's home", "native trainer home"),
    ("emerald-may-home", "emerald", "EM_LITTLEROOT_TOWN", "EM_LITTLEROOT_TOWN_MAYS_HOUSE_1F", [13, 4, 5, 5], "Littleroot: May's home", "native trainer/rival home"),
    ("emerald-birch-lab", "emerald", "EM_LITTLEROOT_TOWN", "EM_LITTLEROOT_TOWN_PROFESSOR_BIRCHS_LAB", [3, 12, 7, 5], "Littleroot: Birch's laboratory", "native professor laboratory"),
    ("emerald-oldale-home", "emerald", "EM_OLDALE_TOWN", "EM_OLDALE_TOWN_HOUSE1", [4, 4, 4, 4], "Oldale: ordinary brown-roof home", "native ordinary home"),
    ("emerald-petalburg-home", "emerald", "EM_PETALBURG_CITY", "EM_PETALBURG_CITY_HOUSE1", [9, 16, 4, 4], "Petalburg: ordinary red-roof home", "native ordinary home"),
    ("emerald-wally-home", "emerald", "EM_PETALBURG_CITY", "EM_PETALBURG_CITY_WALLYS_HOUSE", [5, 2, 5, 4], "Petalburg: Wally's larger home", "native larger home"),
]


def decode_layout(path):
    file_bytes = path.read_bytes()
    raw = file_bytes if file_bytes[:4] == b"SVML" else zlib.decompress(file_bytes)
    assert raw[:4] == b"SVML" and len(raw) >= 16
    width, height = struct.unpack_from("<HH", raw, 6)
    offset = 16 + raw[14] * raw[15] * 2
    assert len(raw) >= offset + width * height * 4
    mids = [struct.unpack_from("<H", raw, offset + i * 4)[0] for i in range(width * height)]
    return {"width": width, "height": height, "mids": mids,
            "file_sha256": catalog.sha(file_bytes), "decoded_sha256": catalog.sha(raw)}


def roof_seam_review(args, candidates, before_ground, ground_ref, ground):
    """Show every Pallet roof/background seam in the actual mapped context."""
    mod = Path(__file__).resolve().parents[1]
    native_map_path = args.cache / "red/data/generated/maps.lua"
    native_map = catalog.read_lua(native_map_path)["PALLET_TOWN"]
    mappings = []
    for name in ("reviewed.lua", "trees.lua", "posts.lua", "water.lua", "coasts.lua", "pallet_buildings.lua", "pallet_details.lua"):
        mappings.extend(preview.read_reviewed(mod / "mappings" / name))
    selected = {}
    for row in sorted(mappings, key=lambda r: bool(r.get("map"))):
        if row["game"] == "red" and row["style"] == "gen3" and row["tileset"] == "OVERWORLD" and row.get("map", "PALLET_TOWN") == "PALLET_TOWN":
            selected[row["id"], row["quadrant"]] = row
    before = Image.new("RGBA", (native_map["width"] * 32, native_map["height"] * 32))
    packed = {}
    for pos, block in enumerate(native_map["blocks"]):
        for q in range(4):
            assert (block, q) in selected
            cell = preview.replacement_image(args.cache, selected[block, q], packed, mod)
            before.paste(cell, (pos % native_map["width"] * 32 + q % 2 * 16, pos // native_map["width"] * 32 + q // 2 * 16))
    after = before.copy()
    for name, x, y in (("home", 64, 48), ("home", 192, 48), ("lab", 160, 128)):
        before.paste(before_ground[name], (x, y))
        after.paste(candidates[name], (x, y))
    changed = [(x, y) for y in range(after.height) for x in range(after.width) if before.getpixel((x, y)) != after.getpixel((x, y))]
    assert len(changed) == 146
    assert all(after.getpixel((x, y)) == ground.getpixel((x % 16, y % 16)) for x, y in changed)
    after.save(args.output / "red-pallet-roof-ground-prototype.png")
    before.save(args.output / "red-pallet-before-roof-ground.png")
    canvas = Image.new("RGB", (1340, 1180), "#18202c")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)
    small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 15)
    draw.text((16, 14), "PALLET ROOF CORNERS — exact Emerald ground beneath preserved native FireRed roof pixels", fill="white", font=font)
    draw.text((16, 44), "Local background fixture. Only146 empty-corner pixels change across the two homes and lab; roof outlines, windows and doors are unchanged.", fill="#ced7e4", font=small)
    for col, (label, image) in enumerate((("Before: pale FireRed corner ground", before), ("After: surrounding Emerald ground", after))):
        draw.text((16 + col * 670, 79), label, fill="white", font=font)
        canvas.paste(image.resize((640, 576), Image.Resampling.NEAREST), (16 + col * 670, 110))
    for i, (label, x, y) in enumerate((("Trainer home: northwest", 56, 40), ("Trainer home: northeast", 112, 40),
                                      ("Rival home: northwest", 184, 40), ("Rival home: northeast", 240, 40),
                                      ("Oak lab: northwest", 152, 120), ("Oak lab: northeast", 240, 120))):
        left, top = 16 + i % 3 * 440, 742 + i // 3 * 205
        draw.text((left, top), label, fill="white", font=small)
        for col, (tag, image) in enumerate((("before", before), ("after", after))):
            draw.text((left + col * 150, top + 23), tag, fill="#ced7e4", font=small)
            canvas.paste(image.crop((x, y, x + 32, y + 32)).resize((128, 128), Image.Resampling.NEAREST), (left + col * 150, top + 46))
    canvas.save(args.output / "pallet-roof-ground-seams.png")
    report = {"status": "native_roof_background_verified", "map": "PALLET_TOWN", "game": "red", "changed_pixels": len(changed),
              "changed_background_pixels_all_match_adjacent_ground": True, "roof_pixels_changed": 0, "building_geometry_changed": False,
              "ground_donor": ground_ref, "full_map_pixel_sha256": catalog.sha(after.tobytes()),
              "source_map_sha256": catalog.sha(native_map_path.read_bytes()), "roof_part_layers": ["over"]}
    (args.output / "pallet-roof-ground-seams.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def frlg_references(args, source_records, source_crops):
    """Verify both remake imports and show their actual Kanto counterparts."""
    definitions = (
        ("home", "FR_PLAYERS_HOUSE_1F", [5, 3, 5, 5], "Trainer's Pallet home"),
        ("rival-home", "FR_RIVALS_HOUSE", [14, 3, 5, 5], "Rival's Pallet home"),
        ("oak-lab", "FR_OAKS_LAB", [13, 9, 7, 5], "Oak's laboratory"),
    )
    records, crops, packed = [], {}, {}
    for game in ("firered", "leafgreen"):
        root = args.cache / game / "data/generated/gba"
        native = root / "native"
        manifest = catalog.read_lua(native / "manifest.lua")
        spec = manifest["layouts"]["FR_PALLET_TOWN"]
        layout = decode_layout(native / spec["file"])
        warps = catalog.read_lua(root / "warps.lua")["FR_PALLET_TOWN"]
        catalog_cells = json.loads((args.catalog / f"{game}.json").read_text())["cells"]
        refs = {r["mid"]: {"game": game, "tileset": spec["pair"], "id": r["mid"], "hash": r["pixel_sha256"]}
                for r in catalog_cells if r["pair"] == spec["pair"]}
        image = Image.new("RGBA", (layout["width"] * 16, layout["height"] * 16))
        cells = {}
        for i, mid in enumerate(layout["mids"]):
            if mid not in cells:
                cells[mid] = preview.native_donor(args.cache, refs[mid], packed)
            image.paste(cells[mid], (i % layout["width"] * 16, i // layout["width"] * 16))
        image.save(args.output / f"{game}-FR_PALLET_TOWN-native.png")
        for name, destination, rect, label in definitions:
            x, y, w, h = rect
            crop = image.crop((x * 16, y * 16, (x + w) * 16, (y + h) * 16))
            door = next(warp for warp in warps if warp["destMap"] == destination)
            local_door = [door["x"] - x, door["y"] - y]
            assert 0 <= local_door[0] < w and local_door[1] == h - 1
            key = game + "-" + name
            crop.save(args.output / f"{key}-native.png")
            crops[key] = crop
            mids = [[layout["mids"][cy * layout["width"] + cx] for cx in range(x, x + w)] for cy in range(y, y + h)]
            records.append({"id": key, "game": game, "map": "FR_PALLET_TOWN", "label": label,
                            "pair": spec["pair"], "native_tile_rect_xywh": rect,
                            "native_pixel_rect_xywh": [x * 16, y * 16, w * 16, h * 16],
                            "width_px": w * 16, "height_px": h * 16,
                            "door_map_cell_xy": [door["x"], door["y"]], "door_local_cell_xy": local_door,
                            "door_bottom_anchor_px_xy": [local_door[0] * 16 + 8, h * 16],
                            "door_destination": destination, "metatiles_by_row": mids,
                            "crop_pixel_sha256": catalog.sha(crop.tobytes()),
                            "source_fingerprints": {"layout_file_sha256": layout["file_sha256"],
                                                    "layout_decoded_sha256": layout["decoded_sha256"],
                                                    "palettes_sha256": catalog.sha((native / spec["pair"] / "palettes.bin").read_bytes()),
                                                    "warp_metadata_sha256": catalog.sha((root / "warps.lua").read_bytes())},
                            "direct_whole_building_fit": False,
                            "native_crop_file": f"{key}-native.png"})
    equality = {name: crops["firered-" + name].tobytes() == crops["leafgreen-" + name].tobytes() for name, *_ in definitions}
    assert all(equality.values()), "FR/LG differ; show separate references instead of pooling their art"
    house_identical = crops["firered-home"].tobytes() == crops["firered-rival-home"].tobytes()
    selected_records = source_records[:3] + records[:3]
    selected_crops = source_crops[:3] + [crops[r["id"]] for r in records[:3]]
    cw, ch, header, scale = 390, 390, 100, 3
    canvas = Image.new("RGB", (cw * 3, header + ch * 2 + 80), "#18202c")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 17)
    small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
    draw.text((16, 12), "DIRECT KANTO COUNTERPARTS — Gen1 versus actual FireRed/LeafGreen Pallet buildings", fill="white", font=font)
    draw.text((16, 39), "FireRed and LeafGreen crops independently verified pixel-identical. Same3x nearest-neighbor scale; door bottoms aligned.", fill="#ced7e4", font=small)
    draw.text((16, 62), "These are native imported buildings, not new artwork. Crop coordinates are16px map cells(x,y,width,height).", fill="#ced7e4", font=small)
    for i, (record, crop) in enumerate(zip(selected_records, selected_crops)):
        left, top = i % 3 * cw, header + i // 3 * ch
        baseline = top + 308
        draw.rectangle((left + 7, top + 4, left + cw - 7, top + ch - 4), outline="#344259")
        title = record["label"] if record["game"] == "red" else "FR/LG: " + record["label"]
        draw.text((left + 16, top + 14), title, fill="white", font=font)
        draw.text((left + 16, top + 40), f"{record['width_px']}×{record['height_px']}px | crop{record['native_tile_rect_xywh']}", fill="#ced7e4", font=small)
        display = crop.resize((crop.width * scale, crop.height * scale), Image.Resampling.NEAREST)
        dx = left + (cw - display.width) // 2
        canvas.paste(display, (dx, baseline - display.height))
        anchor = dx + record["door_bottom_anchor_px_xy"][0] * scale
        draw.line((left + 15, baseline + 2, left + cw - 15, baseline + 2), fill="#9cb2cc")
        draw.polygon(((anchor, baseline - 2), (anchor - 4, baseline + 8), (anchor + 4, baseline + 8)), fill="#f2c36c")
        draw.text((left + 16, baseline + 15), f"Door map{record['door_map_cell_xy']}; local{record['door_local_cell_xy']}", fill="#ced7e4", font=small)
        draw.text((left + 16, baseline + 36), f"Door-bottom anchor{record['door_bottom_anchor_px_xy']}px", fill="#ced7e4", font=small)
        if record["game"] != "red":
            draw.text((left + 16, baseline + 57), "Closest Kanto function; compact parts needed", fill="#e5c68d", font=small)
    draw.text((16, header + ch * 2 + 12), "Native remake homes80×80 vs Gen1 homes64×48. Native remake Oaklab112×80 vs Gen1 Oaklab96×64. No unchanged whole-building fit.", fill="white", font=small)
    draw.text((16, header + ch * 2 + 38), "Home door x24 already matches. Oaklab door x56 must remain at the Gen1 anchor x40 after a reviewed compact composition.", fill="#ced7e4", font=small)
    canvas.save(args.output / "gen1-vs-frlg-buildings-reference.png")
    report = {"status": "reference_only_no_building_mapping", "native_references": records,
              "firered_leafgreen_crop_pixel_identity": equality, "trainer_and_rival_native_crops_pixel_identical": house_identical,
              "findings": {"closest_functional_counterparts": "Actual FireRed/LeafGreen Pallet trainer/rival homes and Oaklab",
                           "native_home_size": [80, 80], "source_home_target": [64, 48],
                           "native_lab_size": [112, 80], "source_lab_target": [96, 64],
                           "home_door_x_native_and_source": 24, "lab_door_x_native": 56, "lab_door_x_source": 40,
                           "unchanged_whole_building_fit": False,
                           "next_step": "Review compact8px-part composition; preserve source footprints, door bottoms and warp cells. No arbitrary scaling."}}
    (args.output / "gen1-vs-frlg-buildings-reference.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def compact_frlg_prototypes(args, frlg_report):
    """Local candidates made solely by copying existing8px native rectangles."""
    configs = {
        "home": {"source_id": "firered-home", "target_size": [64, 48],
                 "row_sources": [1, 5, 6, 7, 8, 9],
                 "column_sources": [[0, 1, 2, 3, 4, 5, 8, 9]] * 2
                    + [[0, 2, 3, 4, 5, 6, 7, 9]] * 2
                    + [[0, 1, 2, 3, 5, 6, 7, 9]] * 2,
                 "door_source_rect": [16, 64, 16, 16], "door_target_rect": [16, 32, 16, 16],
                 "frame_source_rect": [16, 63, 16, 17], "frame_target_rect": [16, 31, 16, 17],
                 "context_source_rect": [8, 56, 32, 24], "context_target_rect": [8, 24, 32, 24],
                 "correctives": [("complete native entrance cap", [16, 63, 16, 1], [16, 31]),
                                  ("clear displaced cap with native wall", [8, 63, 8, 1], [8, 31])],
                 "feature_rects": [("complete visible upper window group1 and sill", [16, 48, 24, 10], [8, 16, 24, 10]),
                                   ("complete visible upper window group2 and sill", [40, 48, 24, 10], [32, 16, 24, 10]),
                                   ("lower window", [40, 64, 24, 16], [32, 32, 24, 16]),
                                   ("complete entrance frame including native lintel", [16, 63, 16, 17], [16, 31, 16, 17]),
                                   ("native wall clearance at old displaced lintel", [8, 63, 8, 1], [8, 31, 8, 1])],
                 "limits": "Native8px parts retain the visible windows and footprint. Two additional existing native1px strips restore the whole entrance cap at the door's actual position and replace the displaced cap with native wall. No painted pixels."},
        "lab": {"source_id": "firered-oak-lab", "target_size": [96, 64],
                "row_sources": [1, 2, 3, 5, 6, 7, 8, 9],
                "column_sources": [[0, 1, 2, 3, 6, 7, 8, 9, 10, 11, 12, 13]] * 4
                    + [[0, 9, 10, 11, 12, 6, 8, 9, 10, 11, 12, 13]] * 2
                    + [[0, 9, 10, 11, 6, 7, 8, 9, 10, 11, 12, 13]] * 2,
                "door_source_rect": [48, 64, 16, 16], "door_target_rect": [32, 48, 16, 16],
                "frame_source_rect": [48, 63, 16, 17], "frame_target_rect": [32, 47, 16, 17],
                "context_source_rect": [40, 56, 32, 24], "context_target_rect": [24, 40, 32, 24],
                "correctives": [("complete native entrance cap", [48, 63, 16, 1], [32, 47])],
                "feature_rects": [("left circular vent1: complete visible glyph and shadow", [72, 50, 16, 12], [8, 34, 16, 12]),
                                  ("left circular vent2: complete visible glyph and shadow", [88, 50, 16, 12], [24, 34, 16, 12]),
                                  ("right circular vent1: complete visible glyph and shadow", [72, 50, 16, 12], [56, 34, 16, 12]),
                                  ("right circular vent2: complete visible glyph and shadow", [88, 50, 16, 12], [72, 34, 16, 12]),
                                  ("left complete24x24 window and full awning including both corners", [72, 56, 24, 24], [8, 40, 24, 24]),
                                  ("right complete24x24 window and full awning including both corners", [72, 56, 24, 24], [56, 40, 24, 24]),
                                  ("complete left facade frame", [0, 48, 8, 32], [0, 32, 8, 32]),
                                  ("left vent1 visible10px glyph", [72, 50, 16, 10], [8, 34, 16, 10]),
                                  ("left vent2 visible10px glyph", [88, 50, 16, 10], [24, 34, 16, 10]),
                                  ("whole chimney", [80, 8, 24, 32], [64, 0, 24, 32]),
                                  ("complete entrance frame including native lintel", [48, 63, 16, 17], [32, 47, 16, 17])],
                "limits": "Both complete24x24 native window/awning rectangles, including their top-right corners, retain every pixel. The four vent glyphs, full left frame and chimney remain intact. One native16x1 strip restores the entrance cap. No wall cleanup covers either window; the left awning ends immediately beside the entrance without overlapping it. Original96x64 footprint and door-bottom anchor(40,64) are unchanged."},
    }
    records = {r["id"]: r for r in frlg_report["native_references"]}
    native_root = args.cache / "firered/data/generated/gba/native"
    layout_spec = catalog.read_lua(native_root / "manifest.lua")["layouts"]["FR_PALLET_TOWN"]
    layout = decode_layout(native_root / layout_spec["file"])
    catalog_rows = json.loads((args.catalog / "firered.json").read_text())["cells"]
    native_records = {r["mid"]: r for r in catalog_rows if r["pair"] == layout_spec["pair"]}
    mid_hash = {mid: r["pixel_sha256"] for mid, r in native_records.items()}
    over_ids, over_pixels, _ = catalog.read_idx(native_root / layout_spec["pair"] / "mids_over.idx")
    native_palette = catalog.read_palettes(native_root / layout_spec["pair"] / "palettes.bin")
    over_cells = {}
    for mid, record in native_records.items():
        slot = over_ids.index(mid)
        over = catalog.rgba_native(over_pixels[slot * 256:(slot + 1) * 256], native_palette, True)
        assert catalog.sha(over.tobytes()) == record["layer_sha256"]["over"]
        over_cells[mid] = over
    emerald_records = json.loads((args.catalog / "emerald.json").read_text())["cells"]
    ground_record = next(r for r in emerald_records if r.get("pair") == "general__petalburg" and r["mid"] == 1)
    ground_ref = {"game": "emerald", "tileset": "general__petalburg", "id": 1, "hash": ground_record["pixel_sha256"]}
    ground = preview.native_donor(args.cache, ground_ref, {})
    candidates, candidate_images, entrance_reviews, roof_reviews, before_ground_images = [], {}, [], [], {}
    for name, config in configs.items():
        record = records[config["source_id"]]
        source = Image.open(args.output / record["native_crop_file"]).convert("RGBA")
        target = Image.new("RGBA", tuple(config["target_size"]))
        for gy in range(0, target.height, 16):
            for gx in range(0, target.width, 16):
                target.paste(ground, (gx, gy))
        parts = []
        source_x, source_y = record["native_pixel_rect_xywh"][:2]
        for dy, source_row in enumerate(config["row_sources"]):
            for dx, source_col in enumerate(config["column_sources"][dy]):
                sr = 4 if name == "lab" and dy == 3 and 8 <= dx <= 10 else source_row
                native_quad = source.crop((source_col * 8, sr * 8, source_col * 8 + 8, sr * 8 + 8))
                gx, gy = source_x + source_col * 8, source_y + sr * 8
                mx, my = gx // 16, gy // 16
                mid = layout["mids"][my * layout["width"] + mx]
                roof = dy < (2 if name == "home" else 4)
                quad = over_cells[mid].crop((gx % 16, gy % 16, gx % 16 + 8, gy % 16 + 8)) if roof else native_quad
                if roof:
                    assert all(p[3] in (0, 255) for p in quad.get_flattened_data())
                    assert all(a == b for a, b in zip(quad.get_flattened_data(), native_quad.get_flattened_data()) if a[3])
                target.alpha_composite(quad, (dx * 8, dy * 8))
                part = {"target_xy_px": [dx * 8, dy * 8], "source_crop_quad_xy": [source_col, sr],
                              "donor": {"game": "firered", "tileset": layout_spec["pair"], "id": mid,
                                        "quadrant": (gy % 16 // 8) * 2 + gx % 16 // 8, "hash": mid_hash[mid]},
                              "srcX": gx % 16, "srcY": gy % 16, "w": 8, "h": 8,
                              "quad_pixel_sha256": catalog.sha(quad.tobytes())}
                if roof:
                    part.update(layers=["over"], layerHashes={"over": native_records[mid]["layer_sha256"]["over"]})
                parts.append(part)
        before_repair = target.copy()
        for label, source_rect, target_xy in config["correctives"]:
            sx, sy, width, height = source_rect
            tx, ty = target_xy
            strip = source.crop((sx, sy, sx + width, sy + height))
            target.paste(strip, (tx, ty))
            gx, gy = source_x + sx, source_y + sy
            assert gx % 16 + width <= 16 and gy % 16 + height <= 16
            assert tx % 16 + width <= 16 and ty % 16 + height <= 16
            mid = layout["mids"][gy // 16 * layout["width"] + gx // 16]
            parts.append({"target_xy_px": target_xy, "source_crop_rect_xywh": source_rect,
                          "donor": {"game": "firered", "tileset": layout_spec["pair"], "id": mid, "hash": mid_hash[mid]},
                          "srcX": gx % 16, "srcY": gy % 16, "w": width, "h": height,
                          "native_strip": label, "quad_pixel_sha256": catalog.sha(strip.tobytes())})
        def region(image, rect):
            x, y, w, h = rect
            return image.crop((x, y, x + w, y + h)).tobytes()
        assert region(source, config["door_source_rect"]) == region(target, config["door_target_rect"])
        feature_checks = []
        for label, source_rect, target_rect in config["feature_rects"]:
            identical = region(source, source_rect) == region(target, target_rect)
            assert identical, f"Feature was clipped or changed: {name}/{label}"
            feature_checks.append({"feature": label, "source_rect_xywh": source_rect,
                                   "target_rect_xywh": target_rect, "pixels_identical": identical})
        target.save(args.output / f"compact-frlg-{name}-prototype.png")
        before_ground = target.copy()
        roof_mask = Image.new("L", target.size)
        for part in parts:
            if not part.get("layers"):
                continue
            sx, sy = part["source_crop_quad_xy"]
            tx, ty = part["target_xy_px"]
            before_ground.paste(source.crop((sx * 8, sy * 8, sx * 8 + 8, sy * 8 + 8)), (tx, ty))
            roof_mask.paste(over_cells[part["donor"]["id"]].crop((part["srcX"], part["srcY"], part["srcX"] + 8, part["srcY"] + 8)).getchannel("A"), (tx, ty))
        differences = [(x, y) for y in range(target.height) for x in range(target.width) if before_ground.getpixel((x, y)) != target.getpixel((x, y))]
        assert len(differences) == (72 if name == "home" else 2)
        assert all(not roof_mask.getpixel((x, y)) and target.getpixel((x, y)) == ground.getpixel((x % 16, y % 16)) for x, y in differences)
        before_ground.save(args.output / f"compact-frlg-{name}-before-roof-ground.png")
        before_ground_images[name] = before_ground
        roof_reviews.append({"id": name, "roof_parts": sum(bool(p.get("layers")) for p in parts),
                             "selected_layers": ["over"], "selected_layer_hashes_checked": True,
                             "changed_empty_background_pixels": len(differences), "changed_native_roof_pixels": 0,
                             "all_changed_pixels_match_surrounding_ground": True, "ground_donor": ground_ref,
                             "before_pixel_sha256": catalog.sha(before_ground.tobytes()), "after_pixel_sha256": catalog.sha(target.tobytes())})
        candidate_images[name] = target
        dr = config["door_target_rect"]
        candidates.append({"id": name, "status": "visually_approved", "size_px": config["target_size"],
                           "door_bottom_anchor_px": [dr[0] + dr[2] // 2, dr[1] + dr[3]],
                           "door_pixels_identical": True, "features_checked": feature_checks,
                           "parts": parts, "base": ground_ref, "roof_empty_background": roof_reviews[-1],
                           "native_8px_parts_copied": len(parts) - len(config["correctives"]),
                           "native_corrective_strips_copied": len(config["correctives"]), "synthetic_pixels": 0,
                           "output_pixel_sha256": catalog.sha(target.tobytes()), "limits": config["limits"]})
        frame_source = source.crop(tuple((lambda r: (r[0], r[1], r[0] + r[2], r[1] + r[3]))(config["frame_source_rect"])))
        frame_before = before_repair.crop(tuple((lambda r: (r[0], r[1], r[0] + r[2], r[1] + r[3]))(config["frame_target_rect"])))
        frame_after = target.crop(tuple((lambda r: (r[0], r[1], r[0] + r[2], r[1] + r[3]))(config["frame_target_rect"])))
        differences_before = sum(a != b for a, b in zip(frame_source.get_flattened_data(), frame_before.get_flattened_data()))
        differences_after = sum(a != b for a, b in zip(frame_source.get_flattened_data(), frame_after.get_flattened_data()))
        assert differences_after == 0
        entrance_reviews.append({"id": name, "source_rect_xywh": config["frame_source_rect"],
                                 "target_rect_xywh": config["frame_target_rect"],
                                 "context_source_rect_xywh": config["context_source_rect"],
                                 "context_target_rect_xywh": config["context_target_rect"],
                                 "different_complete_frame_pixels_before": differences_before,
                                 "different_complete_frame_pixels_after": differences_after,
                                 "native_strips": config["correctives"]})
        before_repair.save(args.output / f"compact-frlg-{name}-before-entrance-repair.png")
    # Reproduce the previous destructive cleanup as a regression fixture. The
    # full24x24 checks above deliberately include both awning corners rather
    # than approving only the window body or a partial horizontal span.
    lab_source = Image.open(args.output / records[configs["lab"]["source_id"]]["native_crop_file"]).convert("RGBA")
    lab_after = candidate_images["lab"]
    lab_before = lab_after.copy()
    lab_before.paste(lab_source.crop((40, 62, 48, 64)), (24, 46))
    lab_before.save(args.output / "compact-frlg-lab-before-window-corner-repair.png")
    window_checks = []
    for feature, source_rect, target_rect in configs["lab"]["feature_rects"]:
        if "window" not in feature and "entrance" not in feature:
            continue
        original = region(lab_source, source_rect)
        before = region(lab_before, target_rect)
        after = region(lab_after, target_rect)
        before_diff = sum(a != b for a, b in zip(Image.frombytes("RGBA", tuple(source_rect[2:]), original).get_flattened_data(),
                                                Image.frombytes("RGBA", tuple(target_rect[2:]), before).get_flattened_data()))
        after_diff = sum(a != b for a, b in zip(Image.frombytes("RGBA", tuple(source_rect[2:]), original).get_flattened_data(),
                                               Image.frombytes("RGBA", tuple(target_rect[2:]), after).get_flattened_data()))
        assert after_diff == 0
        window_checks.append({"feature": feature, "source_rect_xywh": source_rect, "target_rect_xywh": target_rect,
                              "native_pixel_differences_before": before_diff, "native_pixel_differences_after": after_diff})
    changed_pixels = sum(a != b for a, b in zip(lab_before.get_flattened_data(), lab_after.get_flattened_data()))
    assert changed_pixels == 16 and [c["native_pixel_differences_before"] for c in window_checks] == [16, 0, 0]
    window_review = {"status": "complete_native_awnings_and_entrance_verified", "layout_changed": False,
                     "synthetic_pixels": 0, "changed_rgba_pixels": changed_pixels,
                     "before_pixel_sha256": catalog.sha(lab_before.tobytes()),
                     "after_pixel_sha256": catalog.sha(lab_after.tobytes()), "protected_features": window_checks,
                     "fix": "Omit the8x2 plain-wall overlay that erased the left awning's top-right corner. All16 restored pixels already belong to the base native window composition. No feature moves; no scale, footprint or door-anchor change."}
    (args.output / "lab-window-corner-repair.json").write_text(json.dumps(window_review, indent=2), encoding="utf-8")
    window_zoom = Image.new("RGB", (1440, 1010), "#18202c")
    wd = ImageDraw.Draw(window_zoom)
    wfont = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)
    wsmall = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 15)
    wd.text((16, 14), "LAB WINDOW CORNER REPAIR — complete native awnings and entrance, unchanged layout", fill="white", font=wfont)
    wd.text((16, 44), "Exactly16 native pixels restored by removing one wall overlay. Both24x24 windows and the full16x17 lintel/door match native artwork.", fill="#ced7e4", font=wsmall)
    for column, (label, image, rect) in enumerate((("Native FR/LG facade", lab_source, [0, 48, 112, 32]),
                                                  ("Before: erased awning corner", lab_before, [0, 32, 96, 32]),
                                                  ("After: full native window restored", lab_after, [0, 32, 96, 32]))):
        x = 16 + column * 480
        wd.text((x, 84), label, fill="white", font=wfont)
        rx, ry, rw, rh = rect
        window_zoom.paste(image.crop((rx, ry, rx + rw, ry + rh)).resize((rw * 4, rh * 4), Image.Resampling.NEAREST), (x, 116))
    for row, (feature, source_rect, target_rect) in enumerate((configs["lab"]["feature_rects"][4], configs["lab"]["feature_rects"][-1])):
        y = 330 + row * 335
        wd.text((16, y - 34), ("LEFT: whole24x24 window + awning at8x" if row == 0 else "ENTRANCE: whole16x17 lintel + door at8x"), fill="#e5c68d", font=wfont)
        for column, (image, rect) in enumerate(((lab_source, source_rect), (lab_before, target_rect), (lab_after, target_rect))):
            rx, ry, rw, rh = rect
            window_zoom.paste(image.crop((rx, ry, rx + rw, ry + rh)).resize((rw * 8, rh * 8), Image.Resampling.NEAREST), (16 + column * 480, y))
    wd.text((16, 951), "Regression: left window16 differences before /0 after; right window0/0; complete entrance0/0. No window pixels are replaced by wall cleanup.", fill="#ced7e4", font=wsmall)
    window_zoom.save(args.output / "lab-window-corner-repair.png")
    seam_review = roof_seam_review(args, candidate_images, before_ground_images, ground_ref, ground)
    # Same source ID/quadrant may be used twice only when the desired art agrees.
    red_map = catalog.read_lua(args.cache / "red/data/generated/maps.lua")["PALLET_TOWN"]
    def source_keys(rect):
        x, y, w, h = rect
        return {(red_map["blocks"][cy // 2 * red_map["width"] + cx // 2], cy % 2 * 2 + cx % 2)
                for cy in range(y, y + h) for cx in range(x, x + w)}
    home_keys = source_keys([4, 3, 4, 3])
    rival_keys = source_keys([12, 3, 4, 3])
    lab_keys = source_keys([10, 8, 6, 4])
    collision = {"home_keys": [list(k) for k in sorted(home_keys)], "lab_keys": [list(k) for k in sorted(lab_keys)],
                 "home_rival_keys_identical": home_keys == rival_keys,
                 "home_lab_overlapping_keys": [list(k) for k in sorted(home_keys & lab_keys)],
                 "native_home_rival_art_pixel_identical": frlg_report["trainer_and_rival_native_crops_pixel_identical"],
                 "pallet_x_y_override_required": False}
    assert not collision["home_lab_overlapping_keys"] and collision["home_rival_keys_identical"]
    canvas = Image.new("RGB", (1500, 1040), "#18202c")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)
    small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 15)
    draw.text((16, 12), "APPROVED NATIVE-PIXEL BUILDINGS — complete lintels, window glyphs and original door anchors", fill="white", font=font)
    draw.text((16, 41), "Same4x nearest-neighbor scale; native door bottoms aligned. No painted pixels, arbitrary rescaling, window clipping or door reshaping.", fill="#ced7e4", font=small)
    headings = ("Original Gen1 footprint", "Whole native FR/LG counterpart", "Compact8px-part reconstruction")
    for column, heading in enumerate(headings):
        draw.text((16 + column * 500, 78), heading, fill="white", font=font)
    for row, name in enumerate(("home", "lab")):
        baseline = 445 + row * 440
        original = Image.open(args.output / ("red-home-native.png" if name == "home" else "red-oak-lab-native.png")).convert("RGBA")
        native = Image.open(args.output / records[configs[name]["source_id"]]["native_crop_file"]).convert("RGBA")
        compact = candidate_images[name]
        anchors = ([24, 48], [24, 80], [24, 48]) if name == "home" else ([40, 64], [56, 80], [40, 64])
        for col, (image, anchor) in enumerate(zip((original, native, compact), anchors)):
            dx = col * 500 + (500 - image.width * 4) // 2
            canvas.paste(image.resize((image.width * 4, image.height * 4), Image.Resampling.NEAREST), (dx, baseline - image.height * 4))
            draw.line((col * 500 + 15, baseline + 3, col * 500 + 485, baseline + 3), fill="#9cb2cc")
            ax = dx + anchor[0] * 4
            draw.polygon(((ax, baseline), (ax - 4, baseline + 11), (ax + 4, baseline + 11)), fill="#f2c36c")
            draw.text((col * 500 + 16, baseline + 19), f"{name}: {image.width}×{image.height}px; door-bottom{anchor}", fill="white", font=small)
        note = "HOME APPROVED:48 native8px parts +2 native1px strips. Visible windows intact; actual16x17 entrance frame byte-exact." if name == "home" else "LAB:96 native8px parts +1 native1px cap. Both full24x24 windows/awnings and whole16x17 entrance frame byte-exact."
        draw.text((16, baseline + 52), note, fill="#e5c68d", font=small)
    draw.text((16, 997), "Pallet source mapping feasibility:12 home keys and24 lab keys have no overlap; both homes share identical source keys and identical native remake art.", fill="#ced7e4", font=small)
    canvas.save(args.output / "compact-frlg-native-parts-review.png")
    # Enlarged context demonstrates the repaired lintels without pretending
    # intentionally repositioned windows match the original surrounding wall.
    zoom = Image.new("RGB", (1170, 790), "#18202c")
    zd = ImageDraw.Draw(zoom)
    zd.text((16, 12), "ENTRANCE CONTEXT AT8x — native frame versus misplaced cap versus native-strip repair", fill="white", font=font)
    zd.text((16, 42), "Frame proof is the complete16x17 cap+door. Wider32x24 wall/window context is shown for visual continuity.", fill="#ced7e4", font=small)
    for row, name in enumerate(("home", "lab")):
        config = configs[name]
        source = Image.open(args.output / records[config["source_id"]]["native_crop_file"]).convert("RGBA")
        before = Image.open(args.output / f"compact-frlg-{name}-before-entrance-repair.png").convert("RGBA")
        after = candidate_images[name]
        y = 120 + row * 325
        for column, (label, image, rect) in enumerate((("Original native context", source, config["context_source_rect"]),
                                                       ("Before repair", before, config["context_target_rect"]),
                                                       ("Native-strip repair", after, config["context_target_rect"]))):
            x = 16 + column * 390
            rx, ry, rw, rh = rect
            zd.text((x, y - 28), name.upper() + ": " + label, fill="white", font=font)
            zoom.paste(image.crop((rx, ry, rx + rw, ry + rh)).resize((rw * 8, rh * 8), Image.Resampling.NEAREST), (x + 48, y))
        check = next(r for r in entrance_reviews if r["id"] == name)
        zd.text((16, y + 210), f"{name}: complete-frame differences {check['different_complete_frame_pixels_before']} before / {check['different_complete_frame_pixels_after']} after; existing native strips only.", fill="#e5c68d", font=small)
    zoom.save(args.output / "entrance-context-repair.png")
    (args.output / "entrance-context-repair.json").write_text(json.dumps(entrance_reviews, indent=2), encoding="utf-8")
    report = {"status": "approved_frame_corrected_home_and_laboratory", "candidates": candidates,
              "source_key_collision_analysis": collision, "native_base_parts_are_copied_8px_quads": True,
              "native_corrective_strips_are_cropped_existing_pixels": True,
              "entrance_reviews": entrance_reviews, "window_corner_review": window_review,
              "roof_background_reviews": roof_reviews, "pallet_roof_seams": seam_review, "root_review_required": False}
    (args.output / "compact-frlg-native-parts-review.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def write_approved_buildings(args, compact):
    """Write approved Pallet homes/lab for all three independently checked GB imports."""
    models = {c["id"]: c for c in compact["candidates"]}
    approved = {name for name, model in models.items() if model["status"] == "visually_approved"}
    assert "home" in approved
    rows = []
    for game in ("red", "blue", "yellow"):
        base = args.cache / game
        maps = catalog.read_lua(base / "data/generated/maps.lua")
        m = maps["PALLET_TOWN"]
        ts = catalog.read_lua(base / "data/generated/tilesets.lua")["OVERWORLD"]
        source_sheet = Image.open(base / ts["image"])
        c = json.loads((args.catalog / f"{game}.json").read_text())
        source_index = {(r["block_id"], r["quadrant"]): r for r in c["cells"] if r.get("tileset") == "OVERWORLD"}
        fingerprints = next(t["fingerprints"] for t in c["tilesets"] if t["tileset"] == "OVERWORLD")
        for name, source_rect, role, description in (
            ("home", [4, 3, 4, 3], "pallet_kanto_home", "Original64x48 footprint and door-bottom anchor(24,48), visible upper window glyphs/sills and lower24px window are preserved. The complete16x17 entrance including its1px lintel is byte-identical to native artwork; a second native wall strip removes the displaced lintel. Both Gen1 homes share these source keys; the native remake homes are pixel-identical."),
            ("lab", [10, 8, 6, 4], "pallet_oak_laboratory", "Original96x64 footprint and door-bottom anchor(40,64), complete left frame, four full circular vent glyphs/shadows, both complete24x24 windows with full awnings/corners, and whole24x32 chimney retain native pixels. The complete16x17 entrance frame is byte-identical. One native lintel strip repairs the cap; no wall cleanup overwrites any window pixel."),
        ):
            if name not in approved:
                continue
            model = models[name]
            target = Image.open(args.output / f"compact-frlg-{name}-prototype.png").convert("RGBA")
            ox, oy, width, height = source_rect
            for ty in range(height):
                for tx in range(width):
                    mx, my = ox + tx, oy + ty
                    block = m["blocks"][my // 2 * m["width"] + mx // 2]
                    quadrant = my % 2 * 2 + mx % 2
                    source = source_index[(block, quadrant)]
                    actual = preview.native_cell(source_sheet, ts, ts["blocks"][block], quadrant)
                    assert catalog.sha(actual.tobytes()) == source["grayscale_pixel_sha256"]
                    parts = []
                    for part in model["parts"]:
                        px, py = part["target_xy_px"]
                        if px // 16 != tx or py // 16 != ty:
                            continue
                        ref = {k: v for k, v in part["donor"].items() if k != "quadrant"}
                        q = part["donor"].get("quadrant", 0)
                        parts.append({"donor": ref, "srcX": part.get("srcX", q % 2 * 8), "srcY": part.get("srcY", q // 2 * 8),
                                      "w": part.get("w", 8), "h": part.get("h", 8), "x": px % 16, "y": py % 16})
                        for optional in ("layers", "layerHashes"):
                            if optional in part:
                                parts[-1][optional] = part[optional]
                    assert 4 <= len(parts) <= 6 and {(p["x"], p["y"]) for p in parts[:4]} == {(0, 0), (8, 0), (0, 8), (8, 8)}
                    cell = target.crop((tx * 16, ty * 16, tx * 16 + 16, ty * 16 + 16))
                    assert set(cell.getchannel("A").get_flattened_data()) == {255}
                    rows.append({"game": game, "style": "gen3", "map": "PALLET_TOWN", "tileset": "OVERWORLD",
                                 "id": block, "quadrant": quadrant, "role": role, "kind": "native_composite",
                                 "status": "reviewed", "sourceHash": source["grayscale_pixel_sha256"],
                                 "sourceFiles": fingerprints, "parts": parts, "compositionPixelHash": catalog.sha(cell.tobytes()),
                                 "evidence": "Actual native FireRed/LeafGreen Kanto counterpart, compacted solely from existing8px parts. Visually approved2026-10-26. " + description + " No painted pixels or arbitrary scaling. Scoped to Pallet Town; source footprint, collision, scripts and warp cells remain native."})
                    if any(p.get("layers") for p in parts):
                        rows[-1]["base"] = model["base"]
                        rows[-1]["evidence"] += " Roof parts retain only their fingerprint-checked native over layer; transparent background corners reveal exact adjacent Emerald1 ground. All opaque roof/eave pixels are unchanged."
    def lua(value):
        if isinstance(value, str):
            return json.dumps(value)
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, list):
            return "{" + ",".join(lua(v) for v in value) + "}"
        return "{" + ",".join("[" + lua(k) + "]=" + lua(v) for k, v in value.items()) + "}"
    keys = {(r["game"], r["map"], r["id"], r["quadrant"]) for r in rows}
    expected = 3 * sum(12 if name == "home" else 24 for name in approved)
    assert len(rows) == len(keys) == expected
    header = "-- Approved compact native FR/LG Pallet buildings: " + ",".join(sorted(approved)) + ".\n-- Generated by tools/building_review.py --write-approved-buildings.\n-- Home and laboratory entrance/frame corrections are visually approved and independently fingerprinted.\n-- Artwork resolves from the player's native imports; no ROM art is packaged.\nreturn {\n"
    (Path(__file__).resolve().parents[1] / "mappings/pallet_buildings.lua").write_text(header + "".join("  " + lua(row) + ",\n" for row in rows) + "}\n", encoding="utf-8")
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path(catalog.os.environ["APPDATA"]) / "pokemon-love2d")
    parser.add_argument("--catalog", type=Path, default=WORKSPACE / ".work/tileshift-catalog")
    parser.add_argument("--output", type=Path, default=WORKSPACE / ".work/tileshift-building-review")
    parser.add_argument("--write-approved-home", action="store_true", help="Legacy alias: write all currently approved Pallet building rows")
    parser.add_argument("--write-approved-buildings", action="store_true", help="Write only currently approved native building/entrance repairs; exclude pending drafts")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    red_maps = catalog.read_lua(args.cache / "red/data/generated/maps.lua")
    red_sets = catalog.read_lua(args.cache / "red/data/generated/tilesets.lua")
    native_root = args.cache / "emerald/data/generated/gba/native"
    manifest = catalog.read_lua(native_root / "manifest.lua")
    emerald_warps = catalog.read_lua(args.cache / "emerald/data/generated/gba/warps.lua")
    cells = json.loads((args.catalog / "emerald.json").read_text())["cells"]
    refs = {(r["pair"], r["mid"]): {"game": "emerald", "tileset": r["pair"], "id": r["mid"], "hash": r["pixel_sha256"]} for r in cells}
    rendered, layouts, tile_images, packed = {}, {}, {}, {}
    records, crops = [], []
    for key, game, map_id, destination, rect, label, role in REFERENCES:
        x, y, w, h = rect
        if (game, map_id) not in rendered:
            if game == "red":
                m = red_maps[map_id]
                ts = red_sets[m["tileset"]]
                sheet = Image.open(args.cache / game / ts["image"])
                image = Image.new("RGBA", (m["width"] * 32, m["height"] * 32))
                for i, block_id in enumerate(m["blocks"]):
                    for q in range(4):
                        cell = preview.native_cell(sheet, ts, ts["blocks"][block_id], q)
                        image.paste(cell, (i % m["width"] * 32 + q % 2 * 16, i // m["width"] * 32 + q // 2 * 16))
            else:
                spec = manifest["layouts"][map_id]
                layout = decode_layout(native_root / spec["file"])
                layouts[map_id] = layout
                assert layout["width"] == spec["width"] and layout["height"] == spec["height"]
                image = Image.new("RGBA", (layout["width"] * 16, layout["height"] * 16))
                for i, mid in enumerate(layout["mids"]):
                    tile_key = spec["pair"], mid
                    if tile_key not in tile_images:
                        tile_images[tile_key] = preview.native_donor(args.cache, refs[tile_key], packed)
                    image.paste(tile_images[tile_key], (i % layout["width"] * 16, i // layout["width"] * 16))
            rendered[(game, map_id)] = image
        image = rendered[(game, map_id)]
        pixel_rect = [x * 16, y * 16, w * 16, h * 16]
        crop = image.crop((x * 16, y * 16, (x + w) * 16, (y + h) * 16))
        warps = red_maps[map_id]["warps"] if game == "red" else emerald_warps[map_id]
        door = next(warp for warp in warps if warp["destMap"] == destination)
        local_door = [door["x"] - x, door["y"] - y]
        assert 0 <= local_door[0] < w and local_door[1] == h - 1, f"Crop must include full building and end at door bottom: {key}"
        crop.save(args.output / f"{key}-native.png")
        source = {"map_metadata_sha256": catalog.sha((args.cache / "red/data/generated/maps.lua").read_bytes()),
                  "tileset_metadata_sha256": catalog.sha((args.cache / "red/data/generated/tilesets.lua").read_bytes()),
                  "tileset_png_sha256": catalog.sha((args.cache / "red" / red_sets[red_maps[map_id]["tileset"]]["image"]).read_bytes())} if game == "red" else {
                      "layout_file_sha256": layouts[map_id]["file_sha256"],
                      "layout_decoded_sha256": layouts[map_id]["decoded_sha256"],
                      "pair": manifest["layouts"][map_id]["pair"],
                      "palettes_sha256": catalog.sha((native_root / manifest["layouts"][map_id]["pair"] / "palettes.bin").read_bytes()),
                      "warp_metadata_sha256": catalog.sha((args.cache / "emerald/data/generated/gba/warps.lua").read_bytes())}
        record = {"id": key, "label": label, "game": game, "map": map_id, "function": role,
                  "native_tile_rect_xywh": rect, "native_pixel_rect_xywh": pixel_rect,
                  "width_px": w * 16, "height_px": h * 16,
                  "door_map_cell_xy": [door["x"], door["y"]], "door_destination": destination,
                  "door_local_cell_xy": local_door,
                  "door_bottom_anchor_px_xy": [local_door[0] * 16 + 8, h * 16],
                  "crop_pixel_sha256": catalog.sha(crop.tobytes()), "source_fingerprints": source,
                  "crop_policy": "Complete native building in a16px tile rectangle; original corner-background pixels retained. No repainting or rescaling.",
                  "direct_fit_into_gen1_target": None if game == "red" else False,
                  "native_crop_file": f"{key}-native.png"}
        records.append(record)
        crops.append(crop)
    # All images share a3x nearest-neighbor pixel scale. Align the bottom of
    # each crop/door to a common baseline within its reference row.
    cw, ch, pad, header, scale = 390, 390, 16, 100, 3
    canvas = Image.new("RGB", (cw * 3, header + ch * 3 + 70), "#18202c")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 17)
    small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
    draw.text((pad, 12), "NATIVE BUILDING REFERENCES — real Emerald buildings versus Gen1 footprints", fill="white", font=font)
    draw.text((pad, 39), "All artwork at the same3x nearest-neighbor scale; each row aligned at native door bottom. No new building art or mappings.", fill="#ced7e4", font=small)
    draw.text((pad, 62), "Crop coordinates are16px map cells(x,y,width,height). Red is original monochrome; Emerald uses imported native palettes.", fill="#ced7e4", font=small)
    for i, (record, crop) in enumerate(zip(records, crops)):
        col, row = i % 3, i // 3
        left, top = col * cw, header + row * ch
        baseline = top + 308
        draw.rectangle((left + 7, top + 4, left + cw - 7, top + ch - 4), outline="#344259")
        draw.text((left + pad, top + 14), record["label"], fill="white", font=font)
        draw.text((left + pad, top + 40), f"{record['width_px']}×{record['height_px']}px  |  crop{record['native_tile_rect_xywh']}", fill="#ced7e4", font=small)
        display = crop.resize((crop.width * scale, crop.height * scale), Image.Resampling.NEAREST)
        display_x = left + (cw - display.width) // 2
        canvas.paste(display, (display_x, baseline - display.height))
        anchor_x = display_x + record["door_bottom_anchor_px_xy"][0] * scale
        draw.line((left + 15, baseline + 2, left + cw - 15, baseline + 2), fill="#9cb2cc")
        draw.polygon(((anchor_x, baseline - 2), (anchor_x - 4, baseline + 8), (anchor_x + 4, baseline + 8)), fill="#f2c36c")
        draw.text((left + pad, baseline + 15), f"Door map{record['door_map_cell_xy']}; local{record['door_local_cell_xy']}", fill="#ced7e4", font=small)
        draw.text((left + pad, baseline + 36), f"Door-bottom anchor{record['door_bottom_anchor_px_xy']}px", fill="#ced7e4", font=small)
        if record["game"] == "emerald":
            draw.text((left + pad, baseline + 57), "Does not fit unchanged Gen1 footprint", fill="#e5c68d", font=small)
    footer_y = header + ch * 3 + 10
    draw.text((pad, footer_y), "Target footprints: Pallet homes64×48; Oaklab96×64. Littleroot homes80×80; Birchlab112×80. Ordinary Oldale/Petalburg homes64×64.", fill="white", font=small)
    draw.text((pad, footer_y + 25), "Littleroot is the closest functional home/lab counterpart. Every shown Emerald counterpart needs compact art or explicit tile recomposition.", fill="#ced7e4", font=small)
    canvas.save(args.output / "native-buildings-reference.png")
    report = {"status": "art_direction_reference_only", "references": records,
              "findings": {"gen1_home_target": [64, 48], "gen1_lab_target": [96, 64],
                           "closest_functional_home": ["emerald-brendan-home", "emerald-may-home"],
                           "closest_functional_lab": "emerald-birch-lab",
                           "direct_whole_building_fit": False,
                           "reason": "Littleroot houses exceed Gen1 width and height; Birchlab exceeds both dimensions and has a different door offset. Ordinary Oldale/Petalburg houses match the64px home width but exceed its height by16px. Native map footprints and warp coordinates must remain unchanged."}}
    (args.output / "native-buildings-reference.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    frlg = frlg_references(args, records, crops)
    compact = compact_frlg_prototypes(args, frlg)
    written = write_approved_buildings(args, compact) if args.write_approved_home or args.write_approved_buildings else 0
    print(json.dumps({"references": len(records), "sheet": str(args.output / "native-buildings-reference.png"),
                      "dimensions": {r["id"]: [r["width_px"], r["height_px"]] for r in records},
                      "frlg_native_references": len(frlg["native_references"]),
                      "frlg_sheet": str(args.output / "gen1-vs-frlg-buildings-reference.png"),
                      "compact_candidates": len(compact["candidates"]),
                      "approved_building_rows_written": written,
                      "compact_sheet": str(args.output / "compact-frlg-native-parts-review.png")}, indent=2))


if __name__ == "__main__":
    main()
