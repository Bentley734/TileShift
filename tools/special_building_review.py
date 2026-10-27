"""Private review of proper Gen3 counterparts for remaining special buildings.

Whole native units and original source warp anchors are checked before any
production mapping can be proposed. This tool has no production writer.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
from types import SimpleNamespace
from PIL import Image, ImageDraw, ImageFont
import catalog
import preview
import architecture_review as common
import kanto_architecture_review as kanto
from newbark_building_review import native_reference, rectangle

WORKSPACE = Path(__file__).resolve().parents[2]
CONFIGS = {
    "fighting_dojo": {"native": ("firered", "FR_SAFFRON_CITY", "FR_SAFFRON_CITY_DOJO", (37, 8, 6, 5)),
                       "size": (96, 64), "rows": (1, 2, 3, 5, 6, 7, 8, 9), "roof_rows": 4,
                       "roof_columns": tuple(range(12)), "facade_columns": (0, 1, 2, 3, 4, 9, 9, 5, 6, 7, 8, 11),
                       "force_over_rows": (0,), "anchor": (72, 64),
                       "features": (("whole32x32 actual Dojo entrance, Pokeball plaque, full frame and opening", (40, 48, 32, 32), (56, 32, 32, 32)),
                                    ("whole24x17 actual Dojo window panel including full upper cap and lower wall", (16, 55, 24, 17), (16, 39, 24, 17)),
                                    ("entire24x32 native window/facade panel", (16, 48, 24, 32), (16, 32, 24, 32)),
                                    ("complete8x32 native left gold column", (8, 48, 8, 32), (8, 32, 8, 32)),
                                    ("complete8x32 native right outer wall", (88, 48, 8, 32), (88, 32, 8, 32))),
                       "notes": "Actual FireRed Fighting Dojo. The COMPLETE original96x64 source building is x22..27, not its right64px subset. The neighboring Saffron Gym begins atx28. One native8px top terrain band and one repeated plain roof row are omitted. Whole32px entrance moves16px right to the original72px warp anchor; whole left window/facade panel and outer wall units remain. One optional right gold column is omitted whole and plain wall spacing fills the center; no window/entrance frame is cropped."},
    "pokemon_fan_club": {"native": ("emerald", "EM_SLATEPORT_CITY", "EM_SLATEPORT_CITY_POKEMON_FAN_CLUB", (2, 22, 5, 5)),
                         "size": (64, 64), "rows": (1, 2, 4, 5, 6, 7, 8, 9), "roof_rows": 4,
                         "roof_columns": (0, 1, 2, 3, 4, 5, 8, 9), "facade_columns": (0, 3, 4, 5, 6, 7, 8, 9),
                         "force_over_rows": (0,), "anchor": (24, 64),
                         "features": (("complete32x32 actual Fan Club awning, full entrance and steps", (24, 48, 32, 32), (8, 32, 32, 32)),
                                      ("whole16x24 right Fan Club window and full frame/wall panel", (56, 48, 16, 24), (40, 32, 16, 24)),
                                      ("complete8x32 left outer wall and native side post", (0, 48, 8, 32), (0, 32, 8, 32)),
                                      ("complete8x32 right outer wall and native side post", (72, 48, 8, 32), (56, 32, 8, 32))),
                         "notes": "Actual Emerald Pokemon Fan Club. The complete32px entrance/awning/steps moves16px left to the original source anchor24. The whole optional native left16px window/panel is omitted; the entire right window and both outer wall/post units remain intact. Only repeated plain roof rows/columns and the top terrain band are removed. No window/frame, planter or entrance is partially cut."},
    "bike_shop": {"native": ("emerald", "EM_MAUVILLE_CITY", "EM_MAUVILLE_CITY_BIKE_SHOP", (34, 2, 5, 4)),
                  "size": (64, 64), "rows": tuple(range(8)), "roof_rows": 4,
                  "roof_columns": (0, 1, 2, 3, 4, 5, 8, 9), "facade_columns": (0, 1, 2, 3, 4, 6, 7, 9),
                  "force_over_rows": (0,), "anchor": (24, 64),
                  "features": (("complete32x32 actual Bike Shop entrance, header, door and wall context", (8, 32, 32, 32), (8, 32, 32, 32)),
                               ("whole16x24 native arched Bike Shop window including all outer trim", (48, 40, 16, 24), (40, 40, 16, 24)),
                               ("complete8x32 native left outer wall and support", (0, 32, 8, 32), (0, 32, 8, 32)),
                               ("complete8x32 native right outer wall and support", (72, 32, 8, 32), (56, 32, 8, 32))),
                  "notes": "Actual Emerald Rydel Bike Shop. Native height and complete32px roof shape remain unchanged; only repeated plain roof columns and two plain facade spacing columns are omitted to fit the original64x64 source building. Complete32px entrance and whole arched window/side supports remain intact at original warp24,64. Exterior bikes/posts outside the source footprint are separate terrain/object reviews."}
}
SOURCE = {"fighting_dojo": ("SAFFRON_CITY", "FIGHTING_DOJO", (22, 0, 6, 4)),
          "pokemon_fan_club": ("VERMILION_CITY", "POKEMON_FAN_CLUB", (8, 10, 4, 4)),
          "bike_shop": ("CERULEAN_CITY", "BIKE_SHOP", (12, 22, 4, 4))}


def native_source(args, key, config, packed):
    image, native = native_reference(args, key, config, packed)
    extra = config.get("padding_bottom_cells", 0)
    if extra:
        old_height = image.height
        extended = Image.new("RGBA", (image.width, old_height + extra * 16))
        extended.paste(image, (0, 0))
        x, y, w, h = native["rect_cells"]
        for yy in range(extra):
            for xx in range(w):
                mid = native["layout"]["mids"][(y + h + yy) * native["layout"]["width"] + x + xx]
                ref = {"game": native["game"], "tileset": native["pair"], "id": mid, "hash": native["records"][mid]["pixel_sha256"]}
                extended.paste(preview.native_donor(args.cache, ref, packed), (xx * 16, old_height + yy * 16))
        image = extended
        native["rect_cells"] = (x, y, w, h + extra)
        native["source_pixel_sha256"] = catalog.sha(image.tobytes())
        image.save(args.output / f"{key}-native-gen3.png")
    return image, native


def compose_candidate(args, key, config, source, native, ground, ground_ref, packed):
    if not config.get("replacements"):
        return common.compose(args, key, config, source, native, ground, ground_ref, packed)
    initial = deepcopy(config)
    initial["features"] = ()
    target, model = common.compose(args, key, initial, source, native, ground, ground_ref, packed)
    for (sx, sy, w, h), (tx, ty) in config["replacements"]:
        target.paste(rectangle(source, (sx, sy, w, h)), (tx, ty))
        y = 0
        while y < h:
            x = 0
            gy = native["pixel_origin"][1] + sy + y
            hh = min(h - y, 16 - gy % 16, 16 - (ty + y) % 16)
            while x < w:
                gx = native["pixel_origin"][0] + sx + x
                ww = min(w - x, 16 - gx % 16, 16 - (tx + x) % 16)
                mid = native["layout"]["mids"][gy // 16 * native["layout"]["width"] + gx // 16]
                ref = {"game": native["game"], "tileset": native["pair"], "id": mid, "hash": native["records"][mid]["pixel_sha256"]}
                model["parts"].append({"donor": ref, "srcX": gx % 16, "srcY": gy % 16, "w": ww, "h": hh,
                                       "target_xy": (tx + x, ty + y), "native_source_rect": (sx + x, sy + y, ww, hh)})
                x += ww
            y += hh
    for label, src, dst in config["features"]:
        assert rectangle(source, src).tobytes() == rectangle(target, dst).tobytes(), (key, label)
        model["features_checked"].append({"feature": label, "source_rect_xywh": src, "target_rect_xywh": dst, "native_pixel_differences": 0})
    model["rgba_pixel_sha256"] = catalog.sha(target.tobytes())
    model["max_parts_per_cell"] = max(sum(px // 16 == x and py // 16 == y for px, py in (p["target_xy"] for p in model["parts"])) for y in range(target.height // 16) for x in range(target.width // 16))
    assert model["max_parts_per_cell"] <= 16
    target.save(args.output / f"{key}-compact-prototype.png")
    return target, model


def source_boundary_review(args, instances):
    """Expose complete original outer edges and all available one-cell margins.

    Door parity and a matching subset are insufficient to establish a source
    footprint. These sheets require explicit visual whole-boundary review.
    """
    proofs = []
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 16)
    small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
    for key in CONFIGS:
        selected = [r for r in instances if r["template"] == key]
        canvas = Image.new("RGB", (1500, 950), "#18202c")
        draw = ImageDraw.Draw(canvas)
        draw.text((16, 12), "WHOLE SOURCE BOUNDARY REVIEW — original roof/wall edges and a one-cell margin; subset/warp tests are insufficient", fill="white", font=font)
        for i, record in enumerate(selected):
            left, top = i % 3 * 500 + 16, i // 3 * 440 + 54
            game, map_id = record["game"], record["map"]
            m, ts, sheet, image = kanto.source_map(args.cache, game, map_id)
            x, y, w, h = record["rect_cells"]
            whole = rectangle(image, (x * 16, y * 16, w * 16, h * 16))
            context = Image.new("RGBA", ((w + 2) * 16, (h + 2) * 16), "#334258")
            sx, sy = max(0, (x - 1) * 16), max(0, (y - 1) * 16)
            ex, ey = min(image.width, (x + w + 1) * 16), min(image.height, (y + h + 1) * 16)
            context.paste(image.crop((sx, sy, ex, ey)), (sx - (x - 1) * 16, sy - (y - 1) * 16))
            marked = context.convert("RGB").resize((context.width * 3, context.height * 3), Image.Resampling.NEAREST)
            md = ImageDraw.Draw(marked)
            # The outline is outside the source building, never over its edge.
            md.rectangle((47, 47, (w + 1) * 48, (h + 1) * 48), outline="#ff547d", width=1)
            if y == 0:
                md.text((52, 12), "MAP EDGE / no source cell above", fill="white", font=small)
            draw.text((left, top), f"{game.upper()} / {map_id} / {key}", fill="white", font=small)
            draw.text((left, top + 22), f"whole source x{x}..{x+w-1},y{y}..{y+h-1}; {w*16}x{h*16}px", fill="#ced7e4", font=small)
            canvas.paste(marked, (left, top + 48))
            draw.text((left, top + 58 + marked.height), "Pink boundary sits outside ALL original roof/wall edges.", fill="#ced7e4", font=small)
            strips = {"left8": (0, 0, 8, whole.height), "right8": (whole.width - 8, 0, 8, whole.height),
                      "top8": (0, 0, whole.width, 8), "bottom8": (0, whole.height - 8, whole.width, 8)}
            proofs.append({"game": game, "map": map_id, "template": key, "source_rect_cells": record["rect_cells"],
                           "whole_source_rgba_sha256": catalog.sha(whole.tobytes()),
                           "outer_source_strip_hashes": {name: catalog.sha(rectangle(whole, rect).tobytes()) for name, rect in strips.items()},
                           "context_margin_cells": 1, "available_margins": {"left": x > 0, "right": x + w < m["width"] * 2,
                                                                           "above": y > 0, "below": y + h < m["height"] * 2},
                           "map_edge_limits": "A missing margin at the map boundary is explicitly shaded/labeled; no adjacent source graphics are invented.",
                           "status": "explicit_whole_boundary_visual_review_required"})
        canvas.save(args.output / f"{key}-whole-source-boundaries.png")
    return proofs


def stage_fanclub(args, models, instances, natives):
    """Actual native ocean behind roof-only alpha, with every feature static."""
    private = args.output / "fanclub-activation"
    private.mkdir(exist_ok=True)
    model = deepcopy(models["pokemon_fan_club"])
    selected = [r for r in instances if r["template"] == "pokemon_fan_club"]
    (private / "pokemon_fan_club-compact-prototype.png").write_bytes((args.output / "pokemon_fan_club-compact-prototype.png").read_bytes())
    stage = SimpleNamespace(cache=args.cache, catalog=args.catalog, output=private, approved_candidates=True, write_reviewed=False)
    rows = kanto.positioned_rows(stage, {"pokemon_fan_club": model}, selected)
    specification = json.loads((args.output / "fanclub-animation-base.json").read_text())
    packed, expected, animated = {}, {}, 0
    for row in rows:
        mask = deepcopy(row)
        mask.pop("base", None)
        pixels = preview.replacement_image(args.cache, mask, packed, WORKSPACE / "TileShift")
        if min(pixels.getchannel("A").get_flattened_data()) < 255:
            origin = next(r for r in selected if r["game"] == row["game"])
            assert row["y"] - origin["rect_cells"][1] < 2, "Only actual roof alpha may expose coastal water"
            row.update(base=specification["base"], animated=True, animation=specification["animation"])
            row["evidence"] += " Native roof alpha exposes actual Vermilion ocean299; every native water-bank frame animates beneath unchanged roof parts, with exact local-bank/manifest fingerprints and the native global1/16-tick schedule. Facade/steps remain static on the grassy front plane."
            animated += 1
        frames = preview.replacement_frames(args.cache, row, packed, WORKSPACE / "TileShift")
        assert len(frames) == (8 if row.get("animated") else 1)
        assert all(set(f.getchannel("A").get_flattened_data()) == {255} for f in frames)
        row["compositionPixelHash"] = catalog.sha(frames[0].tobytes())
        expected[f"{row['game']}:{row['map']}:{row['x']}:{row['y']}"] = [catalog.sha(f.tobytes()) for f in frames]
    (private / "kanto-staged-rows.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (private / "fanclub-candidates.lua").write_text("return " + common.lua(rows) + "\n", encoding="utf-8")
    (private / "fanclub-expected-frame-hashes.json").write_text(json.dumps(expected, indent=2), encoding="utf-8")
    complete = []
    origin = next(r for r in selected if r["game"] == "red")
    ox, oy, _, _ = origin["rect_cells"]
    native = natives["pokemon_fan_club"]
    for i in range(8):
        image = Image.new("RGBA", (64, 64))
        for row in rows:
            if row["game"] == "red":
                frames = preview.replacement_frames(args.cache, row, packed, WORKSPACE / "TileShift")
                image.paste(frames[i if row.get("animated") else 0], ((row["x"] - ox) * 16, (row["y"] - oy) * 16))
        for feature in model["features_checked"]:
            assert rectangle(native, feature["source_rect_xywh"]).tobytes() == rectangle(image, feature["target_rect_xywh"]).tobytes(), feature["feature"]
        image.save(private / f"fanclub-native-frame-{i}.png")
        complete.append(image)
    model.update(status="reviewed_art_private_native_animation_proof_pending", animated_base=specification,
                 whole_building_frame_rgba_sha256=[catalog.sha(f.tobytes()) for f in complete],
                 rgba_pixel_sha256=catalog.sha(complete[0].tobytes()), all4_complete_features_checked_on_all8_final_frames=True)
    complete[0].save(private / "pokemon_fan_club-compact-prototype.png")
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 16)
    canvas = Image.new("RGB", (1060, 620), "#18202c")
    draw = ImageDraw.Draw(canvas)
    draw.text((16, 12), "FAN CLUB — actual Vermilion8-frame ocean through native roof alpha; whole facade/features stay exact", fill="white", font=font)
    for i, frame in enumerate(complete):
        x, y = 16 + i % 4 * 260, 64 + i // 4 * 275
        draw.text((x, y), f"native frame{i}, global clock16 ticks", fill="#ced7e4", font=font)
        canvas.paste(frame.resize((192, 192), Image.Resampling.NEAREST), (x, y + 28))
    canvas.save(private / "fanclub-all8-native-water-frames.png")
    contexts = kanto.city_contexts(stage, rows, selected)
    report = {"status": "private_reviewed_art_native_animation_proof_pending", "rows": len(rows), "animated_roof_cells": animated,
              "static_facade_and_opaque_roof_cells": len(rows) - animated, "template": model, "source_instances": selected,
              "contexts": contexts, "production_rows_written": 0,
              "limits": "Source/collision/warp geometry is unchanged. Full native Composer/Session8-frame and native animator proof must pass before activation. Remaining city water outside the building stays source-native until its separate coastal batch."}
    (private / "fanclub-native-animated-model.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.write_reviewed_fan_club:
        peer = json.loads((args.output / "fanclub-composite-animation-proof.json").read_text())
        live = json.loads((private / "fanclub-production-proof.json").read_text())
        assert peer["status"] == "passed" and peer["accepted"] == len(rows) and peer["rejected"] == 0
        assert peer["mapping_sha256"] == catalog.sha((private / "fanclub-candidates.lua").read_bytes()), "Independent8-frame proof must cover these exact candidate bytes"
        assert live["session_rejected"] == 0 and live["private_candidate_file_sha256"] == catalog.sha((private / "kanto-staged-rows.json").read_bytes()), "Live source proof must cover this exact dataset"
        target = WORKSPACE / "TileShift/mappings/buildings_extended.lua"
        existing = preview.read_reviewed(target)
        key = lambda r: (r["game"], r["map"], r["x"], r["y"])
        indexed = {key(r): r for r in existing}
        overlaps = [r for r in rows if key(r) in indexed]
        if overlaps:
            assert len(overlaps) == len(rows) and all(indexed[key(r)] == r for r in rows), "Refusing to replace unrelated existing architecture"
        else:
            text = target.read_text(encoding="utf-8").rstrip()
            assert text.endswith("return rows")
            text = text[:-len("return rows")] + "add((function() return {\n" + "".join("  " + common.lua(row) + ",\n" for row in rows) + "} end)())\nreturn rows\n"
            target.write_text(text, encoding="utf-8")
        report["status"] = "reviewed_active_all8_native_frames_verified"
        report["production_rows_written"] = len(rows)
        (private / "fanclub-native-animated-model.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return {"rows": len(rows), "animated_roof_cells": animated, "all8_frames_opaque_and_all4_complete_features_exact": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path(os.environ["APPDATA"]) / "pokemon-love2d")
    parser.add_argument("--catalog", type=Path, default=WORKSPACE / ".work/tileshift-catalog")
    parser.add_argument("--output", type=Path, default=WORKSPACE / ".work/tileshift-special-buildings")
    parser.add_argument("--stage-reviewed-dojo", action="store_true", help="Privately stage the explicitly reviewed Dojo only; other designs remain candidates")
    parser.add_argument("--stage-candidate-dojo", action="store_true", help="Privately stage a revised Dojo that still requires full boundary/context review")
    parser.add_argument("--write-reviewed-dojo", action="store_true", help="Append only the reviewed/live-verified Dojo rows after context verification")
    parser.add_argument("--stage-reviewed-fan-club", action="store_true", help="Private exact8-frame native-water roof candidates; no production writer")
    parser.add_argument("--write-reviewed-fan-club", action="store_true", help="Append reviewed candidates only when exact live and independent8-frame proof hashes pass")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    packed, images, natives, models, instances = {}, {}, {}, {}, []
    record = next(r for r in json.loads((args.catalog / "emerald.json").read_text())["cells"] if r.get("pair") == "general__petalburg" and r["mid"] == 1)
    ground_ref = {"game": "emerald", "tileset": "general__petalburg", "id": 1, "hash": record["pixel_sha256"]}
    ground = preview.native_donor(args.cache, ground_ref, packed)
    for key, config in CONFIGS.items():
        source, native = native_source(args, key, config, packed)
        natives[key] = source
        images[key], models[key] = compose_candidate(args, key, config, source, native, ground, ground_ref, packed)
        for game in ("red", "blue", "yellow", "gold", "silver", "crystal"):
            map_id, destination, rect = SOURCE[key]
            if key == "bike_shop" and game in ("gold", "silver", "crystal"):
                map_id, destination, rect = "GOLDENROD_CITY", "GOLDENROD_BIKE_SHOP", (28, 26, 4, 4)
            if key == "pokemon_fan_club" and game in ("gold", "silver", "crystal"):
                rect = (6, 10, 4, 4)
            m, ts, sheet, image = kanto.source_map(args.cache, game, map_id)
            x, y, w, h = rect
            warp = next(v for v in m["warps"] if v["destMap"] == destination and v["y"] == y + h - 1)
            assert ((warp["x"] - x) * 16 + 8, h * 16) == config["anchor"]
            assert (w * 16, h * 16) == images[key].size
            crop = rectangle(image, (x * 16, y * 16, w * 16, h * 16))
            crop.save(args.output / f"{game}-{destination}-source.png")
            instances.append({"game": game, "map": map_id, "destination": destination, "template": key, "rect_cells": rect,
                              "door_map_cell": (warp["x"], warp["y"]), "door_bottom_anchor_px": config["anchor"],
                              "source_rgba_sha256": catalog.sha(crop.tobytes())})
    common.complete_feature_sheets(args, natives, images, models)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)
    small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 15)
    canvas = Image.new("RGB", (1500, 1430), "#18202c")
    draw = ImageDraw.Draw(canvas)
    draw.text((16, 12), "PRIVATE PROPER SPECIAL COUNTERPARTS — complete native features, original footprint and entrance anchors", fill="white", font=font)
    for row, key in enumerate(CONFIGS):
        source = Image.open(args.output / f"red-{SOURCE[key][1]}-source.png").convert("RGBA")
        for col, (label, image) in enumerate((("Original Red function/footprint", source), ("Whole actual Gen3 counterpart", natives[key]), ("Private native-part composition", images[key]))):
            left, baseline = col * 500 + 16, 390 + row * 430
            draw.text((left, 70 + row * 430), label, fill="white", font=font)
            canvas.paste(image.resize((image.width * 3, image.height * 3), Image.Resampling.NEAREST), (left, baseline - image.height * 3))
            draw.text((left, baseline + 16), f"{key}: {image.width}x{image.height}px", fill="#ced7e4", font=small)
    canvas.save(args.output / "special-native-counterparts.png")
    report = {"status": "private_not_activated", "templates": models, "source_instances": instances,
              "all_source_warp_anchors_verified": True, "production_rows_written": 0,
              "limits": "Native function and full feature geometry reviewed privately. Whole city/terrain joins and live source/session proof are required before any activation."}
    report["whole_source_boundary_proofs"] = source_boundary_review(args, instances)
    if args.stage_reviewed_dojo or args.stage_candidate_dojo or args.write_reviewed_dojo:
        private = args.output / "dojo-activation"
        private.mkdir(exist_ok=True)
        (private / "fighting_dojo-compact-prototype.png").write_bytes((args.output / "fighting_dojo-compact-prototype.png").read_bytes())
        stage = SimpleNamespace(cache=args.cache, catalog=args.catalog, output=private,
                                approved_candidates=args.stage_reviewed_dojo or args.write_reviewed_dojo, write_reviewed=args.write_reviewed_dojo)
        approved = {"fighting_dojo": models["fighting_dojo"]}
        selected = [r for r in instances if r["template"] in approved]
        rows = kanto.positioned_rows(stage, approved, selected)
        contexts = kanto.city_contexts(stage, rows, selected)
        report["staged_dojo"] = {"rows": len(rows), "contexts": contexts, "production_written": args.write_reviewed_dojo,
                                 "status": "reviewed" if args.stage_reviewed_dojo or args.write_reviewed_dojo else "candidate_full_boundary_review_required"}
    if args.stage_reviewed_fan_club or args.write_reviewed_fan_club:
        report["staged_fan_club"] = stage_fanclub(args, models, instances, natives)
    (args.output / "special-native-counterparts.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"templates": len(models), "source_instances": len(instances), "full_native_features_verified": sum(len(m["features_checked"]) for m in models.values())}, indent=2))


if __name__ == "__main__":
    main()
