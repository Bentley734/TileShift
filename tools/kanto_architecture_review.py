"""Private Kanto architecture variants for both Gen1 and Gen2 source geometry."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import catalog
import preview
import architecture_review as common
from newbark_building_review import native_reference, rectangle

WORKSPACE = Path(__file__).resolve().parents[2]
RIGHT_COLUMNS = (0, 1, 2, 3, 4, 9, 10, 5, 6, 7, 8, 11)
WIDE_COLUMNS = (0, 1, 2, 3, 4, 9, 10, 9, 10, 9, 10, 5, 6, 7, 8, 11)


def templates():
    result = {key: deepcopy(common.TEMPLATES[key]) for key in ("center", "mart", "home32")}
    gym = deepcopy(common.TEMPLATES["gym"])
    gym.update(facade_columns=RIGHT_COLUMNS, row_columns={3: RIGHT_COLUMNS}, anchor=(72, 64),
               features=(("complete32x40 native Gym entrance, awning, frame and steps", (40, 40, 32, 40), (56, 24, 32, 40)),
                         ("whole32x32 GYM nameplate and upper window panel", (8, 48, 32, 32), (8, 32, 32, 32)),
                         ("whole16x32 native side window and wall panel", (72, 48, 16, 32), (40, 32, 16, 32))),
               notes="Actual native Gym components; complete entrance moves16px right to match the Kanto anchor. Nameplate and all window units remain whole.")
    result["gym_right"] = gym
    wide = deepcopy(gym)
    wide.update(size=(128, 64), roof_columns=(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 7, 8, 9, 10, 11),
                facade_columns=WIDE_COLUMNS, row_columns={3: WIDE_COLUMNS}, anchor=(104, 64),
                features=(("complete32x40 native Gym entrance, awning, frame and steps", (40, 40, 32, 40), (88, 24, 32, 40)),
                          ("whole32x32 GYM nameplate and upper window panel", (8, 48, 32, 32), (8, 32, 32, 32)),
                          ("complete side window1 and wall panel", (72, 48, 16, 32), (40, 32, 16, 32)),
                          ("complete side window2 and wall panel", (72, 48, 16, 32), (56, 32, 16, 32)),
                          ("complete side window3 and wall panel", (72, 48, 16, 32), (72, 32, 16, 32))),
                notes="Wide native Gym reconstruction. Repeated roof area and complete native window panels fill128px; the original104px entrance anchor, full nameplate and whole entrance are preserved.")
    result["gym_wide"] = wide
    for width in (96, 128):
        house = deepcopy(result["home32"])
        facade = [0, 1, 2, 3]
        window_starts = []
        for n in range(2 if width == 96 else 3):
            window_starts.append(len(facade) * 8)
            facade.extend((5, 6, 7))
            if n != (1 if width == 96 else 2):
                facade.append(4)
        facade.append(9)
        assert len(facade) * 8 == width
        features = [("complete16x17 entrance frame and door", (16, 47, 16, 17), (16, 15, 16, 17))]
        features.extend((f"whole24x17 native window{n+1}, including all frame/cap pixels", (40, 47, 24, 17), (x, 15, 24, 17)) for n, x in enumerate(window_starts))
        house.update(size=(width, 32), roof_columns=(0,) + (4,) * (width // 8 - 2) + (9,), facade_columns=tuple(facade),
                     features=tuple(features), notes="Actual one-story residence parts. Complete24px windows are repeated as whole units to fit the original wide house; no window or doorway is cropped.")
        result[f"home{width}"] = house
    return result


def source_map(cache, game, map_id):
    if game not in ("red", "blue", "yellow"):
        return common.render_source(cache, game, map_id)
    root = cache / game
    m = catalog.read_lua(root / "data/generated/maps.lua")[map_id]
    ts = catalog.read_lua(root / "data/generated/tilesets.lua")[m["tileset"]]
    sheet = Image.open(root / ts["image"])
    image = Image.new("RGBA", (m["width"] * 32, m["height"] * 32))
    for pos, bid in enumerate(m["blocks"]):
        for q in range(4):
            image.paste(preview.native_cell(sheet, ts, ts["blocks"][bid], q),
                        (pos % m["width"] * 32 + q % 2 * 16, pos // m["width"] * 32 + q // 2 * 16))
    return m, ts, sheet, image


def inventory_remaining(args, records, definitions):
    gen1_towns = {"VIRIDIAN_CITY", "PEWTER_CITY", "CERULEAN_CITY", "LAVENDER_TOWN", "VERMILION_CITY", "CELADON_CITY",
                  "FUCHSIA_CITY", "SAFFRON_CITY", "CINNABAR_ISLAND", "INDIGO_PLATEAU"}
    matches, held = [], []
    for game in ("red", "blue", "yellow", "gold", "silver", "crystal"):
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
        profiles = {}
        for record in records:
            if record["game"] == game:
                profiles.setdefault(record["template"], []).append(signature(maps[record["map"]], record["rect_cells"]))
        for map_id, m in maps.items():
            if not isinstance(m, dict):
                continue
            if game in ("red", "blue", "yellow"):
                if map_id not in gen1_towns:
                    continue
            elif m.get("environment") != "TOWN" or m.get("tileset") != "TILESET_KANTO" or map_id == "PALLET_TOWN":
                continue
            for warp in m.get("warps", []):
                name = warp["destMap"]
                if name in {"SOUL_HOUSE", "TRAINER_HOUSE_1F", "VIRIDIAN_SCHOOL_HOUSE"}:
                    choices = ()
                elif "HOUSE" in name and "DAY_CARE" not in name:
                    choices = ("home32", "home96", "home128")
                elif "POKECENTER" in name or "POKEMON_CENTER" in name:
                    choices = ("center",)
                elif name.endswith("_MART"):
                    choices = ("mart",)
                elif name.endswith("_GYM") or name.endswith("_GYM_1F"):
                    choices = ("gym_right", "gym_wide")
                else:
                    choices = ()
                found = False
                for key in choices:
                    if key not in profiles:
                        continue
                    width, height = definitions[key]["size"]
                    ax, ay = definitions[key]["anchor"]
                    rect = (warp["x"] - (ax - 8) // 16, warp["y"] - height // 16 + 1, width // 16, height // 16)
                    if signature(m, rect) in profiles[key]:
                        matches.append({"game": game, "map": map_id, "destination": name, "template": key, "rect_cells": rect,
                                        "door_map_cell": (warp["x"], warp["y"]), "door_bottom_anchor_px": (ax, ay),
                                        "source_shape_exact_reference_match": True, "status": "private_context_review_pending"})
                        found = True
                        break
                if not found:
                    held.append({"game": game, "map": map_id, "destination": name,
                                 "door_map_cell": (warp["x"], warp["y"]), "reason": "Special function, different source geometry, or an additional bare-terrain/rear warp; no automatic building inferred"})
    report = {"status": "private_inventory_no_active_rows", "matched_instances": matches, "held_instances": held,
              "limits": "Exact raw source-shape/warp matches only. A front-structure match does not invent graphics for an additional invisible rear/terrain warp. Special facilities and memorials are not classified as ordinary houses."}
    (args.output / "kanto-remaining-architecture-inventory.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return {"exact_source_shape_instances": len(matches), "held_portals": len(held)}


def positioned_rows(args, models, instances):
    """Own-cart source hashes and warp-anchored native parts for private context QA."""
    rows, loaded = [], {}
    for record in instances:
        game, map_id, key = record["game"], record["map"], record["template"]
        if (game, map_id) not in loaded:
            m, ts, sheet, _ = source_map(args.cache, game, map_id)
            root = args.cache / game
            paths = {"metadata": "data/generated/tilesets.lua", "maps": "data/generated/maps.lua", "image": ts["image"]}
            if game not in ("red", "blue", "yellow"):
                paths.update(palettes="data/generated/palettes.lua", roofs="data/generated/roofs.lua")
            files = {name: catalog.sha((root / path).read_bytes()) for name, path in paths.items()}
            cells = json.loads((args.catalog / f"{game}.json").read_text())["cells"]
            indexed = {(r["block_id"], r["quadrant"]): r for r in cells if r.get("tileset") == m["tileset"]}
            loaded[game, map_id] = m, ts, sheet, files, indexed
        m, ts, sheet, files, indexed = loaded[game, map_id]
        model = models[key]
        ox, oy, w, h = record["rect_cells"]
        target = Image.open(args.output / f"{key}-compact-prototype.png").convert("RGBA")
        assert target.size == (w * 16, h * 16)
        for y in range(h):
            for x in range(w):
                xx, yy = ox + x, oy + y
                bid, q = m["blocks"][yy // 2 * m["width"] + xx // 2], yy % 2 * 2 + xx % 2
                source = indexed[bid, q]
                assert catalog.sha(preview.native_cell(sheet, ts, ts["blocks"][bid], q).tobytes()) == source["grayscale_pixel_sha256"]
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
                       "sourceHash": source["grayscale_pixel_sha256"], "sourceFiles": files,
                       "role": "architecture_" + key, "kind": "native_composite",
                       "status": "reviewed" if args.approved_candidates or args.write_reviewed else "candidate", "parts": parts,
                       "compositionPixelHash": catalog.sha(rectangle(target, (x * 16, y * 16, 16, 16)).tobytes()),
                       "evidence": model["notes"] + " Actual source destination:" + record["destination"]
                                   + ". Own-cartridge complete source shape, destination function and original warp anchor verified. Whole native windows, frame caps, signs and entrance features pass exact-pixel assertions. Roof empty areas use selected native alpha over exact cell-local Emerald1 ground. No scaling or map/collision/script changes."}
                if any(p.get("layers") for p in parts):
                    row["base"] = model["base"]
                rows.append(row)
    rows.sort(key=lambda r: (r["game"], r["map"], r["y"], r["x"]))
    assert len(rows) == len({(r["game"], r["map"], r["x"], r["y"]) for r in rows})
    (args.output / "kanto-staged-rows.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    if args.write_reviewed:
        target = WORKSPACE / "TileShift/mappings/buildings_extended.lua"
        current = preview.read_reviewed(target)
        replacements = {(r["game"], r["map"], r["x"], r["y"]): r for r in rows}
        for row in current:
            replacements.setdefault((row["game"], row["map"], row["x"], row["y"]), row)
        combined = sorted(replacements.values(), key=lambda r: (r["game"], r["map"], r["y"], r["x"]))
        assert len(combined) >= len(current)
        # Separate function bodies avoid LuaJIT's65,536-constant limit as the
        # verified architecture inventory grows. Each chunk contains only refs.
        text = "-- Reviewed complete native Gen3 public buildings and homes, with own-source warp/position proof.\nlocal rows={}\nlocal function add(list) for _,row in ipairs(list) do rows[#rows+1]=row end end\n"
        for start in range(0, len(combined), 500):
            text += "add((function() return {\n" + "".join("  " + common.lua(row) + ",\n" for row in combined[start:start + 500]) + "} end)())\n"
        target.write_text(text + "return rows\n", encoding="utf-8")
    return rows


def city_contexts(args, candidate_rows, instances):
    """Actual per-cell candidate images, with existing terrain and front joins visible."""
    mod = WORKSPACE / "TileShift"
    active = []
    for path in sorted((mod / "mappings").glob("*.lua")):
        active.extend(preview.read_reviewed(path))
    reports, fronts = [], []
    packed = {}
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)
    small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 15)
    # Red and Crystal cover both source layouts, wider Gen2 homes and every template.
    selected = sorted({(r["game"], r["map"]) for r in instances if r["game"] in ("red", "crystal")})
    for game, map_id in selected:
        m, ts, sheet, original = source_map(args.cache, game, map_id)
        generic, positioned = {}, {}
        for row in sorted(active, key=lambda r: bool(r.get("map"))):
            if row["game"] == game and row["style"] == "gen3" and row["tileset"] == m["tileset"] and row.get("map", map_id) == map_id:
                if "x" in row:
                    positioned[row["x"], row["y"]] = row
                else:
                    generic[row["id"], row["quadrant"]] = row
        before = original.copy()
        covered = set()
        for pos, bid in enumerate(m["blocks"]):
            for q in range(4):
                x, y = pos % m["width"] * 2 + q % 2, pos // m["width"] * 2 + q // 2
                row = positioned.get((x, y), generic.get((bid, q)))
                if row:
                    before.paste(preview.replacement_image(args.cache, row, packed, mod), (x * 16, y * 16))
                    covered.add((x, y))
        after, previous = before.copy(), len(covered)
        for row in candidate_rows:
            if row["game"] == game and row["map"] == map_id:
                after.paste(preview.replacement_image(args.cache, row, packed, mod), (row["x"] * 16, row["y"] * 16))
                covered.add((row["x"], row["y"]))
        after.save(args.output / f"{game}-{map_id}-development-after.png")
        scale = 2 if after.width <= 480 else 1
        width, height = after.width * scale, after.height * scale
        canvas = Image.new("RGB", (width * 2 + 56, height + 160), "#18202c")
        draw = ImageDraw.Draw(canvas)
        draw.text((18, 12), f"DEVELOPMENT — {game.upper()} / {map_id}: original native source and reviewed Gen3 architecture candidates", fill="white", font=font)
        draw.text((18, 42), f"{len(covered)}/{len(m['blocks']) * 4} cells covered; {len(m['blocks']) * 4 - len(covered)} source cells remain. Original footprints and warp anchors; actors omitted.", fill="#ced7e4", font=small)
        draw.text((18, 80), f"Original {game.upper()} source" + (" DAY" if game == "crystal" else ""), fill="white", font=small)
        draw.text((38 + width, 80), "Gen3 candidates plus current reviewed terrain", fill="white", font=small)
        canvas.paste(original.resize((width, height), Image.Resampling.NEAREST), (18, 110))
        canvas.paste(after.resize((width, height), Image.Resampling.NEAREST), (38 + width, 110))
        filename = f"{game}-{map_id}-development-comparison.png"
        canvas.save(args.output / filename)
        reports.append({"game": game, "map": map_id, "comparison": filename, "previously_covered_cells": previous,
                        "candidate_covered_cells": len(covered), "total_cells": len(m["blocks"]) * 4,
                        "candidate_pixel_sha256": catalog.sha(after.tobytes()), "source_geometry_unchanged": True})
        for instance in instances:
            if instance["game"] == game and instance["map"] == map_id:
                x, y, w, h = instance["rect_cells"]
                # Entire building and one real cell row below: door/ground joins are visible.
                rect = (x * 16, y * 16, w * 16, min(h * 16 + 16, after.height - y * 16))
                fronts.append((instance, rectangle(original, rect), rectangle(after, rect)))
    # Every template/source-layout family appears in a compact, enlarged join sheet.
    chosen, seen = [], set()
    for item in fronts:
        family = "gen1" if item[0]["game"] == "red" else "gen2"
        key = family, item[0]["template"]
        if key not in seen:
            seen.add(key)
            chosen.append(item)
    for start in range(0, len(chosen), 4):
        canvas = Image.new("RGB", (1500, 1240), "#18202c")
        draw = ImageDraw.Draw(canvas)
        draw.text((16, 12), "KANTO FRONT JOINS — full building footprint, complete entrance and actual map ground below", fill="white", font=font)
        for i, (instance, source, target) in enumerate(chosen[start:start + 4]):
            top = 60 + i * 290
            draw.text((16, top), f"{instance['game'].upper()} / {instance['map']} / {instance['template']} / {instance['destination']}", fill="white", font=small)
            for col, image in enumerate((source, target)):
                canvas.paste(image.resize((image.width * 3, image.height * 3), Image.Resampling.NEAREST), (24 + col * 740, top + 26))
        canvas.save(args.output / f"kanto-building-front-joins-{start // 4 + 1}.png")
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path(catalog.os.environ["APPDATA"]) / "pokemon-love2d")
    parser.add_argument("--catalog", type=Path, default=WORKSPACE / ".work/tileshift-catalog")
    parser.add_argument("--output", type=Path, default=WORKSPACE / ".work/tileshift-building-kanto")
    parser.add_argument("--approved-candidates", action="store_true", help="Mark private data reviewed after the context review")
    parser.add_argument("--write-reviewed", action="store_true", help="Append approved Kanto rows while preserving every existing architecture position")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    g = next(r for r in json.loads((args.catalog / "emerald.json").read_text())["cells"] if r.get("pair") == "general__petalburg" and r["mid"] == 1)
    ground_ref = {"game": "emerald", "tileset": "general__petalburg", "id": 1, "hash": g["pixel_sha256"]}
    packed = {}
    ground = preview.native_donor(args.cache, ground_ref, packed)
    definitions = templates()
    targets, natives, models = {}, {}, {}
    for key, config in definitions.items():
        source, native = native_reference(args, key, config, packed)
        natives[key] = source
        targets[key], models[key] = common.compose(args, key, config, source, native, ground, ground_ref, packed)
    records = []
    for game in ("red", "blue", "yellow", "gold", "silver", "crystal"):
        gen1 = game in ("red", "blue", "yellow")
        specs = [("VIRIDIAN_CITY", "center", "VIRIDIAN_POKECENTER" if gen1 else "VIRIDIAN_POKECENTER_1F", (22, 22, 4, 4)),
                 ("VIRIDIAN_CITY", "mart", "VIRIDIAN_MART", (28, 16, 4, 4)),
                 ("VIRIDIAN_CITY", "gym_right", "VIRIDIAN_GYM", (28, 4, 6, 4)),
                 ("VIRIDIAN_CITY", "home32", "VIRIDIAN_NICKNAME_HOUSE" if gen1 else "VIRIDIAN_NICKNAME_SPEECH_HOUSE", (20, 8, 4, 2)),
                 ("PEWTER_CITY", "gym_right", "PEWTER_GYM", (12, 14, 6, 4)),
                 ("CERULEAN_CITY", "gym_wide", "CERULEAN_GYM", (24, 16 if gen1 else 20, 8, 4)),
                 ("CERULEAN_CITY", "home96", "CERULEAN_MELANIES_HOUSE" if game == "yellow" else "CERULEAN_TRADE_HOUSE" if gen1 else "CERULEAN_TRADE_SPEECH_HOUSE", (12, 14 if gen1 else 18, 6, 2)),
                 ("CERULEAN_CITY", "home96" if gen1 else "home128", "CERULEAN_BADGE_HOUSE" if gen1 else "CERULEAN_GYM_BADGE_SPEECH_HOUSE", (8, 10, 6, 2) if gen1 else (6, 14, 8, 2))]
        rendered = {}
        for map_id, key, destination, rect in specs:
            if map_id not in rendered:
                rendered[map_id] = source_map(args.cache, game, map_id)
            m, ts, sheet, image = rendered[map_id]
            x, y, w, h = rect
            candidates = [v for v in m["warps"] if v["destMap"] == destination and v["y"] == y + h - 1]
            assert candidates, (game, map_id, destination, rect, m["warps"])
            warp = candidates[0]
            assert ((warp["x"] - x) * 16 + 8, h * 16) == definitions[key]["anchor"], (game, destination, rect)
            assert (w * 16, h * 16) == definitions[key]["size"]
            crop = rectangle(image, (x * 16, y * 16, w * 16, h * 16))
            crop.save(args.output / f"{game}-{destination}-source.png")
            records.append({"game": game, "map": map_id, "destination": destination, "template": key, "rect_cells": rect,
                            "door_map_cell": (warp["x"], warp["y"]), "door_bottom_anchor_px": definitions[key]["anchor"],
                            "source_rgba_sha256": catalog.sha(crop.tobytes())})
    for page, keys in enumerate((("center", "mart", "gym_right", "gym_wide"), ("home32", "home96", "home128"))):
        canvas = Image.new("RGB", (1500, 1300 if len(keys) == 4 else 1020), "#18202c")
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)
        small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 15)
        draw.text((16, 12), "KANTO SOURCE GEOMETRY — Gen1/2 native roles and complete Gen3 feature variants", fill="white", font=font)
        for col, label in enumerate(("Actual source example", "Whole native Gen3 source", "Native-part candidate")):
            draw.text((col * 500 + 16, 56), label, fill="white", font=font)
        for row, key in enumerate(keys):
            record = next(v for v in records if v["template"] == key)
            original = Image.open(args.output / f"{record['game']}-{record['destination']}-source.png").convert("RGBA")
            baseline = 340 + row * 300
            for col, image in enumerate((original, natives[key], targets[key])):
                x = col * 500 + (500 - image.width * 3) // 2
                canvas.paste(image.resize((image.width * 3, image.height * 3), Image.Resampling.NEAREST), (x, baseline - image.height * 3))
                draw.line((col * 500 + 16, baseline + 2, col * 500 + 484, baseline + 2), fill="#9cb2cc")
                draw.text((col * 500 + 16, baseline + 14), f"{key}:{image.width}x{image.height}px", fill="white", font=small)
            draw.text((16, baseline + 40), definitions[key]["notes"], fill="#e5c68d", font=small)
        canvas.save(args.output / f"kanto-building-variants-{page + 1}.png")
    common.complete_feature_sheets(args, natives, targets, models)
    inventory = inventory_remaining(args, records, definitions)
    instances = json.loads((args.output / "kanto-remaining-architecture-inventory.json").read_text())["matched_instances"]
    rows = positioned_rows(args, models, instances)
    contexts = city_contexts(args, rows, instances)
    report = {"status": "private_variants_not_activated", "source_instances": records, "templates": models,
              "production_rows_written": len(rows) if args.write_reviewed else 0, "private_positioned_rows": len(rows),
              "contexts": contexts, "all_source_warp_anchors_verified": True,
              "remaining_source_inventory": inventory,
              "limits": "Special facilities, school/window-plant compaction and uninspected source footprints are not inferred."}
    (args.output / "kanto-building-variants.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"private_templates": len(models), "source_instances": len(records), "whole_native_features_verified": sum(len(m["features_checked"]) for m in models.values())}, indent=2))


if __name__ == "__main__":
    main()
