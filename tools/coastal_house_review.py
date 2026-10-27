"""Private Route12 house roof alpha over the actual local native ocean bank.

Only36 pixels at the north edge(y0/1) expose water; every entrance, window,
wall and grassy front pixel remains static. No production writes by default.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import zlib
from types import SimpleNamespace
from PIL import Image, ImageDraw, ImageFont
import catalog
import preview
import kanto_architecture_review as kanto
from building_review import decode_layout
from newbark_building_review import rectangle, lua

WORKSPACE = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path(os.environ["APPDATA"]) / "pokemon-love2d")
    parser.add_argument("--catalog", type=Path, default=WORKSPACE / ".work/tileshift-catalog")
    parser.add_argument("--output", type=Path, default=WORKSPACE / ".work/tileshift-route12-houses")
    parser.add_argument("--write-reviewed", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    reference = json.loads((WORKSPACE / ".work/tileshift-building-kanto/kanto-building-variants.json").read_text())
    model = reference["templates"]["home32"]
    original_native = Image.open(WORKSPACE / ".work/tileshift-building-kanto/home32-native-gen3.png").convert("RGBA")
    assert catalog.sha(original_native.tobytes()) == model["native"]["source_pixel_sha256"]
    instances = json.loads((WORKSPACE / ".work/tileshift-route-architecture/route-architecture-inventory.json").read_text())["held_coastal_background_instances"]
    assert len(instances) == 6 and {r["game"] for r in instances} == {"red", "blue", "yellow", "gold", "silver", "crystal"}
    (args.output / "home32-compact-prototype.png").write_bytes((WORKSPACE / ".work/tileshift-building-kanto/home32-compact-prototype.png").read_bytes())
    stage = SimpleNamespace(cache=args.cache, catalog=args.catalog, output=args.output, approved_candidates=True, write_reviewed=False)
    rows = kanto.positioned_rows(stage, {"home32": model}, instances)
    root = args.cache / "firered/data/generated/gba/native"
    spec = catalog.read_lua(root / "manifest.lua")["layouts"]["FR_ROUTE_12"]
    layout = decode_layout(root / spec["file"])
    native = next(r for r in json.loads((args.catalog / "firered.json").read_text())["cells"] if r.get("pair") == spec["pair"] and r["mid"] == 299)
    assert native["behavior_hint"] == "MB_OCEAN_WATER" and 299 in layout["mids"]
    raw = (root / spec["pair"] / "anim_water.rgba").read_bytes()
    try:
        raw = zlib.decompress(raw)
    except zlib.error:
        pass
    base = {"game": "firered", "tileset": spec["pair"], "id": 299, "hash": native["pixel_sha256"]}
    animation = {"bank": "water", "hash": catalog.sha(raw),
                 "manifestHash": catalog.sha((root / spec["pair"] / "anim_manifest.lua").read_bytes()),
                 "frames": 8, "period": 16, "phase": 1, "counter": "global", "counterMax": 640, "format": "rgba8"}
    packed = {}
    native_frames = preview.native_water_frames(args.cache, {"donor": base, "animation": animation}, packed)
    animation["frame0Hash"] = catalog.sha(native_frames[0].tobytes())
    holes = {}
    for row in rows:
        entry = next(r for r in instances if r["game"] == row["game"])
        ox, oy, _, _ = entry["rect_cells"]
        mask = deepcopy(row)
        mask.pop("base", None)
        overlay = preview.replacement_image(args.cache, mask, packed, WORKSPACE / "TileShift")
        exposed = [((row["x"] - ox) * 16 + x, (row["y"] - oy) * 16 + y)
                   for y in range(16) for x in range(16) if overlay.getpixel((x, y))[3] == 0]
        if exposed:
            assert all(y in (0, 1) for x, y in exposed), "Water may never appear in facade/entrance/window alpha"
            holes.setdefault(row["game"], []).extend(exposed)
            row.update(base=base, animated=True, animation=animation)
            row["evidence"] += " Route12 ocean touches the north roof. Only36 alpha pixels at localy0/1 expose the ACTUAL FireRed FR_ROUTE_12 ocean299 local8-frame bank. Facade, complete17px frames/windows and grassy front remain static. Native bank/manifest/source/position fingerprints are mandatory."
        frames = preview.replacement_frames(args.cache, row, packed, WORKSPACE / "TileShift")
        assert len(frames) == (8 if exposed else 1)
        assert all(set(f.getchannel("A").get_flattened_data()) == {255} for f in frames)
        row["compositionPixelHash"] = catalog.sha(frames[0].tobytes())
    assert all(len(v) == 36 for v in holes.values()) and len(holes) == 6
    whole = []
    entry = next(r for r in instances if r["game"] == "red")
    ox, oy, _, _ = entry["rect_cells"]
    for i in range(8):
        image = Image.new("RGBA", (64, 32))
        for row in rows:
            if row["game"] == "red":
                frames = preview.replacement_frames(args.cache, row, packed, WORKSPACE / "TileShift")
                image.paste(frames[i if row.get("animated") else 0], ((row["x"] - ox) * 16, (row["y"] - oy) * 16))
        for feature in model["features_checked"]:
            assert rectangle(original_native, feature["source_rect_xywh"]).tobytes() == rectangle(image, feature["target_rect_xywh"]).tobytes(), feature["feature"]
        image.save(args.output / f"route12-native-frame-{i}.png")
        whole.append(image)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 16)
    small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
    sheet = Image.new("RGB", (1060, 520), "#18202c")
    draw = ImageDraw.Draw(sheet)
    draw.text((16, 12), "ROUTE12 COASTAL HOUSE — only36 north-edge pixels(y0/1) expose actual local8-frame ocean; all features stay exact", fill="white", font=font)
    for i, image in enumerate(whole):
        x, y = 16 + i % 4 * 260, 70 + i // 4 * 210
        draw.text((x, y), f"native frame{i}, global16ticks", fill="#ced7e4", font=font)
        sheet.paste(image.resize((192, 96), Image.Resampling.NEAREST), (x, y + 28))
        sheet.paste(image.crop((0, 0, 32, 4)).resize((192, 24), Image.Resampling.NEAREST), (x, y + 145))
    sheet.save(args.output / "route12-all8-native-water-frames.png")
    # Native coast context and explicit exposed-pixel mask, with source margins.
    mod = WORKSPACE / "TileShift"
    active = []
    for path in sorted((mod / "mappings").glob("*.lua")):
        active.extend(preview.read_reviewed(path))
    canvas = Image.new("RGB", (1500, 900), "#18202c")
    draw = ImageDraw.Draw(canvas)
    draw.text((16, 12), "ROUTE12 BACKGROUND PLANES — actual water north, static grass/front below, complete source boundary and roof-hole mask", fill="white", font=font)
    for i, game in enumerate(("red", "crystal")):
        entry = next(r for r in instances if r["game"] == game)
        x, y, w, h = entry["rect_cells"]
        m, ts, source_sheet, original = kanto.source_map(args.cache, game, "ROUTE_12")
        generic, positioned = {}, {}
        for row in sorted(active, key=lambda r: bool(r.get("map"))):
            if row["game"] == game and row["tileset"] == m["tileset"] and row.get("map", "ROUTE_12") == "ROUTE_12":
                if "x" in row:
                    positioned[row["x"], row["y"]] = row
                else:
                    generic[row["id"], row["quadrant"]] = row
        original = rectangle(original, ((x - 1) * 16, (y - 1) * 16, 96, 64))
        after = original.copy()
        for yy in range(y - 1, y + h + 1):
            for xx in range(x - 1, x + w + 1):
                bid, q = m["blocks"][yy // 2 * m["width"] + xx // 2], yy % 2 * 2 + xx % 2
                row = positioned.get((xx, yy), generic.get((bid, q)))
                if row:
                    after.paste(preview.replacement_image(args.cache, row, packed, mod), ((xx - x + 1) * 16, (yy - y + 1) * 16))
        after.paste(whole[0], (16, 16))
        marked = whole[0].convert("RGB")
        md = ImageDraw.Draw(marked)
        for px, py in holes[game]:
            md.point((px, py), fill="#ff3bff")
        top = 65 + i * 405
        for col, (label, image) in enumerate(((game.upper() + " actual source + margins", original), ("Native Gen3 frame0 + current terrain", after), ("MAGENTA:36 alpha pixels ONLYy0/1", marked))):
            draw.text((16 + col * 500, top), label, fill="white", font=font)
            canvas.paste(image.resize((image.width * 4, image.height * 4), Image.Resampling.NEAREST), (16 + col * 500, top + 34))
    canvas.save(args.output / "route12-source-coast-and-alpha-plane-review.png")
    (args.output / "kanto-staged-rows.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    candidate = args.output / "route12-candidates.lua"
    candidate.write_text("return " + lua(rows) + "\n", encoding="utf-8")
    model = deepcopy(model)
    model.update(whole_building_frame_rgba_sha256=[catalog.sha(f.tobytes()) for f in whole],
                 all2_complete_native_features_checked_on_all8_final_frames=True)
    report = {"status": "private_native8frame_and_background_review_pending", "rows": len(rows),
              "animated_roof_cells": sum(bool(r.get("animated")) for r in rows),
              "base": base, "animation": animation, "native_source_map": "FR_ROUTE_12",
              "native299_cells": [[pos % layout["width"], pos // layout["width"]] for pos, mid in enumerate(layout["mids"]) if mid == 299][:8],
              "template": model, "source_instances": instances, "alpha_holes_by_game": holes, "production_rows_written": 0}
    (args.output / "route12-coastal-house-model.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.write_reviewed:
        peer = json.loads((args.output / "route12-composite-animation-proof.json").read_text())
        live = json.loads((args.output / "route12-production-proof.json").read_text())
        assert peer["status"] == "passed" and peer["mapping_sha256"] == catalog.sha(candidate.read_bytes()) and peer["accepted"] == len(rows) and peer["rejected"] == 0
        assert live["session_rejected"] == 0 and live["private_candidate_file_sha256"] == catalog.sha((args.output / "kanto-staged-rows.json").read_bytes())
        target = mod / "mappings/buildings_extended.lua"
        existing = preview.read_reviewed(target)
        key = lambda r: (r["game"], r["map"], r["x"], r["y"])
        indexed = {key(r): r for r in existing}
        assert not any(key(r) in indexed for r in rows), "Reviewed coastal houses must not overwrite existing positions"
        text = target.read_text(encoding="utf-8").rstrip()
        assert text.endswith("return rows")
        text = text[:-len("return rows")] + "add((function() return {\n" + "".join("  " + lua(r) + ",\n" for r in rows) + "} end)())\nreturn rows\n"
        target.write_text(text, encoding="utf-8")
        report.update(status="reviewed_active_exact_native8frames", production_rows_written=len(rows))
        (args.output / "route12-coastal-house-model.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"rows": len(rows), "animated_roof_cells": report["animated_roof_cells"], "exposed_pixels_per_building": 36, "production_rows_written": report["production_rows_written"]}, indent=2))


if __name__ == "__main__":
    main()
