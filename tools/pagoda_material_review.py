"""Private original Sprout pagoda layout made only from imported native materials.

This is an original structure, not a Battle Palace/Fighting Dojo building swap.
No production mappings, bitmap assets or imported content are written.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from types import SimpleNamespace
from PIL import Image, ImageDraw, ImageFont
import catalog
import preview
import architecture_review
import kanto_architecture_review as kanto
from newbark_building_review import native_reference, rectangle

WORKSPACE = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path(os.environ["APPDATA"]) / "pokemon-love2d")
    parser.add_argument("--catalog", type=Path, default=WORKSPACE / ".work/tileshift-catalog")
    parser.add_argument("--output", type=Path, default=WORKSPACE / ".work/tileshift-sprout-native-material")
    parser.add_argument("--variant", choices=("dojo", "wood", "hybrid"), default="dojo")
    parser.add_argument("--with-platform", action="store_true")
    parser.add_argument("--stage-reviewed", action="store_true")
    parser.add_argument("--write-reviewed", action="store_true")
    args = parser.parse_args()
    if args.variant != "dojo":
        args.output = args.output / ("palace-wood" if args.variant == "wood" else "sloped-roof-hybrid")
    args.output.mkdir(parents=True, exist_ok=True)
    packed = {}
    dojo, dojo_native = native_reference(args, "dojo-material", {"native": ("firered", "FR_SAFFRON_CITY", "FR_SAFFRON_CITY_DOJO", (37, 8, 6, 5))}, packed)
    home, home_native = native_reference(args, "home-door-material", architecture_review.TEMPLATES["home32"], packed)
    ground_record = next(r for r in json.loads((args.catalog / "emerald.json").read_text())["cells"] if r.get("pair") == "general__petalburg" and r["mid"] == 1)
    ground_ref = {"game": "emerald", "tileset": "general__petalburg", "id": 1, "hash": ground_record["pixel_sha256"]}
    ground = preview.native_donor(args.cache, ground_ref, packed)
    target = Image.new("RGBA", (64, 80))
    parts, feature_checks = [], []
    sources = {"dojo": (dojo, dojo_native), "home": (home, home_native)}
    if args.variant != "dojo":
        palace, palace_native = native_reference(args, "palace-material", {"native": ("emerald", "EM_BATTLE_FRONTIER_OUTSIDE_EAST", "EM_BATTLE_FRONTIER_BATTLE_PALACE_LOBBY", (40, 50, 11, 7))}, packed)
        sources["palace"] = palace, palace_native
    def copy(source_name, rect, at, label, roof=False):
        source, native = sources[source_name]
        sx, sy, w, h = rect
        tx, ty = at
        assert 0 <= tx < 64 and 0 <= ty < 80 and tx + w <= 64 and ty + h <= 80
        # Split at both donor and destination16px boundaries. Each emitted part
        # is an exact native rectangle and can be fingerprinted independently.
        y = 0
        while y < h:
            x = 0
            gy = native["pixel_origin"][1] + sy + y
            hh = min(h - y, 16 - gy % 16, 16 - (ty + y) % 16)
            while x < w:
                gx = native["pixel_origin"][0] + sx + x
                ww = min(w - x, 16 - gx % 16, 16 - (tx + x) % 16)
                mid = native["layout"]["mids"][gy // 16 * native["layout"]["width"] + gx // 16]
                record = native["records"][mid]
                ref = {"game": native["game"], "tileset": native["pair"], "id": mid, "hash": record["pixel_sha256"]}
                crop = rectangle(source, (sx + x, sy + y, ww, hh))
                part = {"donor": ref, "srcX": gx % 16, "srcY": gy % 16, "w": ww, "h": hh,
                        "target_xy": (tx + x, ty + y), "native_source_rect": (sx + x, sy + y, ww, hh), "material": source_name, "purpose": label}
                if roof:
                    layer_hash = record["layer_sha256"]["over"]
                    over = preview.native_donor(args.cache, ref, packed, ["over"], {"over": layer_hash}).crop((gx % 16, gy % 16, gx % 16 + ww, gy % 16 + hh))
                    # Do not discard any native roof material merely because
                    # another metatile places architecture on a lower layer.
                    if any(p[3] for p in over.get_flattened_data()) and all(a == b for a, b in zip(over.get_flattened_data(), crop.get_flattened_data()) if a[3]):
                        crop = over
                        part.update(layers=["over"], layerHashes={"over": layer_hash})
                target.alpha_composite(crop, (tx + x, ty + y))
                parts.append(part)
                x += ww
            y += hh
    if args.variant == "dojo":
        # Main roof: keep the complete outer cap/left-right outline; remove only
        # repeated plain gold roof fields. No icon or unrelated facility sign used.
        columns = (0, 1, 2, 3, 6, 7, 10, 11)
        for y, sy in enumerate((1, 2, 3, 5)):
            for x, sx in enumerate(columns):
                copy("dojo", (sx * 8, sy * 8, 8, 8), (x * 8, y * 8), "gold roof material / full outline", roof=True)
        # Two upper wooden stories: each has two complete native paired-window
        # units, plain wall material, timber posts, and its own complete eave strip.
        for y in (32, 48):
            copy("dojo", (16, 64, 24, 8), (8, y), "plain native lower wall material")
            copy("dojo", (16, 64, 24, 8), (32, y), "plain native lower wall material")
            copy("dojo", (8, 56, 8, 16), (0, y), "gold timber post material")
            copy("dojo", (80, 56, 8, 16), (56, y), "gold timber post material")
            for x, sx in enumerate(columns):
                copy("dojo", (sx * 8, 16, 8, 8), (x * 8, y + 8), "whole horizontal native eave material")
            for x in (8, 32):
                copy("dojo", (16, 55, 24, 9), (x, y - 1), "complete paired blue window with all outer cap/frame pixels")
        # The narrow ground facade preserves both incidental terrain side strips.
        # Entrance anchor remains exactly(24,80); a full17px door/frame is copied.
        copy("dojo", (8, 56, 8, 16), (8, 64), "narrow ground-facade left timber")
        copy("dojo", (16, 64, 4, 8), (32, 64), "plain ground-facade wall gap")
        copy("dojo", (16, 64, 4, 8), (32, 72), "plain ground-facade wall gap")
        copy("dojo", (80, 56, 8, 16), (48, 64), "narrow ground-facade right timber")
        copy("home", (16, 47, 16, 17), (16, 63), "complete16x17 wooden entrance/frame")
        # Each12px pane has its own complete native gray surround. This is one
        # framed pane, never a scaled/slivered24px two-pane window.
        copy("dojo", (16, 55, 12, 17), (36, 63), "complete12px pane and lower wall panel")
        features = [("complete16x17 entrance/frame", "home", (16, 47, 16, 17), (16, 63, 16, 17)),
                    ("complete ground-floor12x9 framed pane including upper cap", "dojo", (16, 55, 12, 9), (36, 63, 12, 9))]
        features.extend((f"whole24x9 paired window story{n+1} position{x}", "dojo", (16, 55, 24, 9), (x, y - 1, 24, 9)) for n, y in enumerate((32, 48)) for x in (8, 32))
    elif args.variant == "wood":
        # Original three-story wooden pagoda using Palace roof/wood materials.
        # Complete native8x16 arched windows fit each16px facade story; roof
        # material is recomposed to a shallow16px cap, not scaled or painted.
        # The actual Palace side-roof silhouette is x0..40 inside its48px
        # metatile envelope. The final8px are flowers/the connecting roof.
        # Its top corners have two empty pixels on row0 and one on row1;
        # copy only the native roof scanlines, never the incidental flowers.
        columns = (0, 8, 16, 24, 8, 16, 24, 32)
        for y, sy in enumerate((8, 40)):
            for x, sx in enumerate(columns):
                if y == 0 and x in (0, 7):
                    if x == 0:
                        copy("palace", (sx + 2, sy, 6, 1), (2, 0), "complete native roof top-left scanline")
                        copy("palace", (sx + 1, sy + 1, 7, 1), (1, 1), "complete native roof top-left scanline")
                    else:
                        copy("palace", (sx, sy, 6, 1), (56, 0), "complete native roof top-right scanline")
                        copy("palace", (sx, sy + 1, 7, 1), (56, 1), "complete native roof top-right scanline")
                    copy("palace", (sx, sy + 2, 8, 6), (x * 8, 2), "complete native rounded roof corner")
                else:
                    copy("palace", (sx, sy, 8, 8), (x * 8, y * 8), "shallow golden roof material and native outer outline", roof=True)
        for y in (16, 40):
            for yy in (y, y + 8):
                for x in range(8, 56, 8):
                    copy("palace", (24, 56, 8, 8), (x, yy), "plain red wood facade material")
            copy("palace", (0, 56, 8, 16), (0, y), "whole native timber segment")
            copy("palace", (32, 56, 8, 16), (56, y), "whole native timber segment")
            for x in (16, 40):
                copy("palace", (16, 56, 8, 16), (x, y), "whole8x16 arched window including full sill/frame")
            for x, sx in enumerate(columns):
                copy("palace", (sx, 40, 8, 8), (x * 8, y + 16), "complete golden horizontal eave segment", roof=True)
        for yy in (64, 72):
            for x in range(16, 48, 8):
                copy("palace", (24, 56, 8, 8), (x, yy), "plain narrow ground-facade red wood")
        copy("palace", (0, 56, 8, 16), (8, 64), "narrow lower-facade left timber")
        copy("palace", (32, 56, 8, 16), (48, 64), "narrow lower-facade right timber")
        copy("home", (16, 47, 16, 17), (16, 63), "complete16x17 native wooden entrance/frame")
        copy("palace", (16, 56, 8, 16), (40, 64), "whole ground-floor8x16 arched window including full sill/frame")
        features = [("complete16x17 entrance/frame", "home", (16, 47, 16, 17), (16, 63, 16, 17)),
                    ("complete ground-floor8x16 arched window and sill", "palace", (16, 56, 8, 16), (40, 64, 8, 16))]
        features.extend((f"whole8x16 arched window story{n+1} position{x}", "palace", (16, 56, 8, 16), (x, y, 8, 16)) for n, y in enumerate((16, 40)) for x in (16, 40))
    else:
        #32px visibly sloped roof: complete native cap/left/right outlines,
        # with only one repeated plain roof row omitted. The broad central
        # field repeats one native center strip, retaining a single roof.
        columns = (0, 8, 16, 16, 16, 16, 24, 32)
        for y, sy in enumerate((8, 16, 24, 40)):
            for x, sx in enumerate(columns):
                if y == 0 and x in (0, 7):
                    if x == 0:
                        copy("palace", (sx + 2, sy, 6, 1), (2, 0), "full native rounded roof outline")
                        copy("palace", (sx + 1, sy + 1, 7, 1), (1, 1), "full native rounded roof outline")
                    else:
                        copy("palace", (sx, sy, 6, 1), (56, 0), "full native rounded roof outline")
                        copy("palace", (sx, sy + 1, 7, 1), (56, 1), "full native rounded roof outline")
                    copy("palace", (sx, sy + 2, 8, 6), (x * 8, 2), "full native rounded roof outline")
                else:
                    copy("palace", (sx, sy, 8, 8), (x * 8, y * 8), "complete sloped main-roof material and outline", roof=True)
        for y in (32, 48):
            for x in range(8, 56, 8):
                copy("palace", (24, 56, 8, 8), (x, y), "plain red timber facade material")
            copy("palace", (0, 56, 8, 16), (0, y), "gold and red wood post material")
            copy("palace", (32, 56, 8, 16), (56, y), "gold and red wood post material")
            for x, sx in enumerate(columns):
                copy("palace", (sx, 40, 8, 8), (x * 8, y + 8), "complete gold horizontal eave material", roof=True)
            for x in (8, 32):
                copy("dojo", (16, 55, 24, 9), (x, y - 1), "whole24x9 paired window including native cap and sill")
        for yy in (64, 72):
            for x in range(16, 56, 8):
                copy("palace", (24, 56, 8, 8), (x, yy), "plain red wood narrow ground facade")
        copy("palace", (0, 56, 8, 16), (8, 64), "narrow ground-facade left timber")
        copy("home", (16, 47, 16, 17), (16, 63), "whole16x17 wooden entrance and frame")
        copy("dojo", (16, 55, 24, 9), (32, 63), "whole24x9 ground window with native upper cap and full sill")
        features = [("complete16x17 entrance/frame", "home", (16, 47, 16, 17), (16, 63, 16, 17)),
                    ("whole24x9 ground paired window with full cap/sill", "dojo", (16, 55, 24, 9), (32, 63, 24, 9))]
        features.extend((f"whole24x9 paired window story{n+1} position{x}", "dojo", (16, 55, 24, 9), (x, y - 1, 24, 9)) for n, y in enumerate((32, 48)) for x in (8, 32))
    for label, name, src, dst in features:
        original = rectangle(sources[name][0], src)
        actual = rectangle(target, dst)
        assert original.tobytes() == actual.tobytes(), label
        feature_checks.append({"feature": label, "native_source": name, "source_rect_xywh": src, "target_rect_xywh": dst, "pixel_differences": 0})
    assert set(target.crop((0, 64, 8, 80)).getchannel("A").get_flattened_data()) == {0}
    assert set(target.crop((56, 64, 64, 80)).getchannel("A").get_flattened_data()) == {0}
    platform = []
    if args.with_platform:
        platform_path = WORKSPACE / ".work/tileshift-gen2-outdoor-cliff-review/sprout-platform-side-references.json"
        for reference, tx in zip(json.loads(platform_path.read_text()), (0, 56)):
            assert reference["role"] == ("west face" if tx == 0 else "east face")
            donor = preview.native_donor(args.cache, reference["donor"], packed)
            src = tuple(reference[k] for k in ("srcX", "srcY", "w", "h"))
            strip = rectangle(donor, src)
            assert catalog.sha(strip.tobytes()) == reference["stripPixelHash"]
            assert strip.size == (8, 16) and set(strip.getchannel("A").get_flattened_data()) == {255}
            target.alpha_composite(strip, (tx, 64))
            parts.append({"donor": reference["donor"], "srcX": src[0], "srcY": src[1], "w": 8, "h": 16,
                          "target_xy": (tx, 64), "native_source_rect": src, "material": "outdoor_platform",
                          "purpose": "reviewed outdoor raised-rock " + reference["role"]})
            reference["status"] = "visually_reviewed_root_approved"
            platform.append(reference)
    target.save(args.output / "sprout-original-native-material-prototype.png")
    backdrop = Image.new("RGBA", (64, 80))
    for y in range(0, 80, 16):
        for x in range(0, 64, 16):
            backdrop.paste(ground, (x, y))
    backdrop.alpha_composite(target)
    for feature in feature_checks:
        source_image = sources[feature["native_source"]][0]
        assert rectangle(source_image, feature["source_rect_xywh"]).tobytes() == rectangle(backdrop, feature["target_rect_xywh"]).tobytes(), feature["feature"]
        feature["final_composited_pixel_differences"] = 0
    if args.with_platform:
        assert set(backdrop.getchannel("A").get_flattened_data()) == {255}
        backdrop.save(args.output / "sprout_pagoda-compact-prototype.png")
    m, ts, sheet, source_map = architecture_review.render_source(args.cache, "crystal", "VIOLET_CITY")
    source = rectangle(source_map, (22 * 16, 16, 64, 80))
    context = source_map.copy()
    mod = WORKSPACE / "TileShift"
    active = []
    for path in sorted((mod / "mappings").glob("*.lua")):
        active.extend(preview.read_reviewed(path))
    generic, positioned = {}, {}
    for row in sorted(active, key=lambda r: bool(r.get("map"))):
        if row["game"] == "crystal" and row["style"] == "gen3" and row["tileset"] == m["tileset"] and row.get("map", "VIOLET_CITY") == "VIOLET_CITY":
            if "x" in row:
                positioned[row["x"], row["y"]] = row
            else:
                generic[row["id"], row["quadrant"]] = row
    covered = 0
    for pos, bid in enumerate(m["blocks"]):
        for q in range(4):
            x, y = pos % m["width"] * 2 + q % 2, pos // m["width"] * 2 + q // 2
            row = positioned.get((x, y), generic.get((bid, q)))
            if row:
                context.paste(preview.replacement_image(args.cache, row, packed, mod), (x * 16, y * 16))
                covered += 1
    context.alpha_composite(target, (22 * 16, 16))
    context.save(args.output / "crystal-violet-pagoda-native-material-private-context.png")
    close = context.crop((20 * 16, 0, 28 * 16, 7 * 16))
    close.resize((close.width * 4, close.height * 4), Image.Resampling.NEAREST).save(args.output / "crystal-violet-pagoda-native-material-private-seams.png")
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 17)
    small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
    canvas = Image.new("RGB", (1500, 1000), "#18202c")
    draw = ImageDraw.Draw(canvas)
    draw.text((16, 12), ("REVIEWED" if args.stage_reviewed or args.write_reviewed else "PRIVATE") + " ORIGINAL SPROUT PAGODA — native Gen3 roof/wood/window/door materials; not another facility substituted", fill="white", font=font)
    draw.text((16, 40), "64x80px original footprint / entrance anchor(24,80). Three facade levels and full feature units. Lower side strips are separate raised-rock platform faces.", fill="#ced7e4", font=small)
    for col, (label, image) in enumerate((("Original Crystal source", source), ("Private native-material design", backdrop), ("Actual native material source", palace if args.variant != "dojo" else dojo))):
        draw.text((16 + col * 500, 80), label, fill="white", font=font)
        scale = 2 if col == 2 and args.variant != "dojo" else 4
        canvas.paste(image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST), (16 + col * 500, 115))
    for i, feature in enumerate(feature_checks):
        left, top = 16 + i % 3 * 500, 485 + i // 3 * 245
        draw.text((left, top), feature["feature"], fill="white", font=small)
        for col, (image, rect) in enumerate(((sources[feature["native_source"]][0], feature["source_rect_xywh"]), (target, feature["target_rect_xywh"]))):
            crop = rectangle(image, rect)
            canvas.paste(crop.resize((crop.width * 6, crop.height * 6), Image.Resampling.NEAREST), (left + col * 230, top + 30))
    canvas.save(args.output / "sprout-original-native-material-review.png")
    report = {"status": "reviewed_active" if args.write_reviewed else "reviewed_staged" if args.stage_reviewed else "private_original_architecture_design_not_activated", "size_px": [64, 80], "door_bottom_anchor_px": [24, 80],
              "source_map": "VIOLET_CITY", "source_rect_cells": [22, 1, 4, 5], "output_rgba_sha256": catalog.sha(target.tobytes()),
              "original_design": True, "parts": parts, "features_checked": feature_checks, "base": ground_ref,
              "native_materials": {name: {k: v for k, v in data.items() if k not in ("layout", "records")} for name, (_, data) in sources.items()},
              "preserved_terrain_strips": [[0, 64, 8, 16], [56, 64, 8, 16]],
              "approved_outdoor_platform_references": platform,
              "final_compiled_rgba_sha256": catalog.sha(backdrop.tobytes()),
              "all6_features_checked_on_final_composited_output": True,
              "current_reviewed_context_coverage_cells": covered,
              "max_native_parts_per16px_cell": max(sum(px // 16 == x and py // 16 == y for px, py in (p["target_xy"] for p in parts)) for y in range(5) for x in range(4)),
              "notes": "Original Gen3 native-material Sprout monastic pagoda architecture, visually approved with its complete32px sloped roof, three stories, five whole paired-window units and full17px wooden entrance/frame. The lower outside8px strips use separately reviewed FireRed outdoor raised-rock west/east faces. This is an original tower design, not an unrelated Palace/Dojo building function substituted.",
              "always_base": True,
              "limits": "Original architecture uses fingerprint-checked native materials. All final feature rectangles are checked after every overlay. The front platform-rim cells outside the building remain a separate terrain review; no source collision/warp/map data changed or raster art packaged."}
    if args.stage_reviewed or args.write_reviewed:
        assert args.variant == "hybrid" and args.with_platform, "Only the approved sloped design with approved outdoor faces may stage"
        stage = SimpleNamespace(cache=args.cache, catalog=args.catalog, output=args.output,
                                approved_candidates=True, write_reviewed=args.write_reviewed)
        instances = []
        for game in ("gold", "silver", "crystal"):
            m, ts, sheet, source_image = kanto.source_map(args.cache, game, "VIOLET_CITY")
            warp = next(w for w in m["warps"] if w["destMap"] == "SPROUT_TOWER_1F")
            assert (warp["x"], warp["y"]) == (23, 5)
            instances.append({"game": game, "map": "VIOLET_CITY", "destination": "SPROUT_TOWER_1F", "template": "sprout_pagoda",
                              "rect_cells": (22, 1, 4, 5), "door_map_cell": (23, 5), "door_bottom_anchor_px": (24, 80)})
        rows = kanto.positioned_rows(stage, {"sprout_pagoda": report}, instances)
        report["reviewed_positioned_rows"] = len(rows)
        report["production_rows_written"] = len(rows) if args.write_reviewed else 0
    (args.output / "sprout-original-native-material-model.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"native_material_parts": len(parts), "complete_features_checked": len(feature_checks), "production_rows_written": report.get("production_rows_written", 0)}, indent=2))


if __name__ == "__main__":
    main()
