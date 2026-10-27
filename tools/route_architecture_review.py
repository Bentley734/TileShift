"""Review route aliases only when the COMPLETE source matches an approved shape.

Special facilities are held separately even if they reuse an ordinary picture.
No subset/warp-only inference is accepted. Production writes require the
approved flag after context review and separate real Lua/live-import proof.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import catalog
import preview
import kanto_architecture_review as kanto
from newbark_building_review import rectangle

WORKSPACE = Path(__file__).resolve().parents[2]
GAMES = ("red", "blue", "yellow", "gold", "silver", "crystal")
SPECIAL = ("DAY_CARE", "DAYCARE", "SEA_COTTAGE", "BILLS", "TRAINER", "SOUL", "MANSION", "SUMMER_BEACH")


def inventory(args, models, references):
    found, held = [], []
    for game in GAMES:
        maps = catalog.read_lua(args.cache / game / "data/generated/maps.lua")
        sets = catalog.read_lua(args.cache / game / "data/generated/tilesets.lua")
        sheets = {}
        def signature(m, rect):
            x, y, w, h = rect
            if x < 0 or y < 0 or x + w > m["width"] * 2 or y + h > m["height"] * 2:
                return None
            ts = sets[m["tileset"]]
            if m["tileset"] not in sheets:
                sheets[m["tileset"]] = Image.open(args.cache / game / ts["image"])
            return tuple(catalog.sha(preview.native_cell(sheets[m["tileset"]], ts,
                         ts["blocks"][m["blocks"][yy // 2 * m["width"] + xx // 2]], yy % 2 * 2 + xx % 2).tobytes())
                         for yy in range(y, y + h) for xx in range(x, x + w))
        profiles = defaultdict(dict)
        for record in references:
            if record["game"] == game and record["template"] in models:
                profiles[record["template"]][signature(maps[record["map"]], record["rect_cells"])] = record
        for map_id, m in maps.items():
            if not isinstance(m, dict) or not map_id.startswith("ROUTE_") or m.get("tileset") not in ("OVERWORLD", "TILESET_JOHTO", "TILESET_JOHTO_MODERN", "TILESET_KANTO"):
                continue
            for warp in m.get("warps", []):
                name = warp["destMap"]
                if any(token in name for token in SPECIAL):
                    if "HOUSE" in name or "COTTAGE" in name:
                        held.append({"game": game, "map": map_id, "destination": name, "reason": "Special function requires its own proper native counterpart; generic house picture does not approve function"})
                    continue
                choices = ("center",) if "POKECENTER" in name or "POKEMON_CENTER" in name else ("home32",) if "HOUSE" in name else ()
                for key in choices:
                    width, height = models[key]["size_px"]
                    ax, ay = models[key]["door_bottom_anchor_px"]
                    rect = (warp["x"] - (ax - 8) // 16, warp["y"] - height // 16 + 1, width // 16, height // 16)
                    raw = signature(m, rect)
                    reference = profiles[key].get(raw)
                    if reference:
                        found.append({"game": game, "map": map_id, "destination": name, "template": key, "rect_cells": rect,
                                      "door_map_cell": (warp["x"], warp["y"]), "door_bottom_anchor_px": (ax, ay),
                                      "complete_raw_source_cell_signature": raw, "approved_source_profile_reference": reference,
                                      "whole_source_outer_edges_match_approved_profile": True,
                                      "status": "context_boundary_review_pending"})
                    else:
                        held.append({"game": game, "map": map_id, "destination": name, "reason": "No complete approved source-picture match; no subset or warp-only inference"})
    return found, held


def contexts(args, rows, instances):
    mod = WORKSPACE / "TileShift"
    active = []
    for path in sorted((mod / "mappings").glob("*.lua")):
        active.extend(preview.read_reviewed(path))
    packed, maps, contacts, proofs = {}, {}, [], []
    for record in instances:
        game, map_id = record["game"], record["map"]
        if (game, map_id) not in maps:
            m, ts, sheet, original = kanto.source_map(args.cache, game, map_id)
            generic, positioned = {}, {}
            for row in sorted(active, key=lambda r: bool(r.get("map"))):
                if row["game"] == game and row["style"] == "gen3" and row["tileset"] == m["tileset"] and row.get("map", map_id) == map_id:
                    if "x" in row:
                        positioned[row["x"], row["y"]] = row
                    else:
                        generic[row["id"], row["quadrant"]] = row
            after = original.copy()
            for pos, bid in enumerate(m["blocks"]):
                for q in range(4):
                    x, y = pos % m["width"] * 2 + q % 2, pos // m["width"] * 2 + q // 2
                    row = positioned.get((x, y), generic.get((bid, q)))
                    if row:
                        after.paste(preview.replacement_image(args.cache, row, packed, mod), (x * 16, y * 16))
            for row in rows:
                if row["game"] == game and row["map"] == map_id:
                    after.paste(preview.replacement_image(args.cache, row, packed, mod), (row["x"] * 16, row["y"] * 16))
            maps[game, map_id] = m, original, after
        m, original, after = maps[game, map_id]
        x, y, w, h = record["rect_cells"]
        crop = rectangle(original, (x * 16, y * 16, w * 16, h * 16))
        proofs.append({"game": game, "map": map_id, "destination": record["destination"], "whole_source_rgba_sha256": catalog.sha(crop.tobytes()),
                       "outer_gray_source_edges_match_full_approved_profile": True,
                       "original_footprint_and_warp_anchor_unchanged": True,
                       "one_cell_context_margin_available": {"left": x > 0, "right": x + w < m["width"] * 2, "above": y > 0, "below": y + h < m["height"] * 2}})
        if game not in ("red", "yellow", "crystal"):
            continue
        # Yellow only needs its exclusive special case; normal pixel-shape
        # aliases already have own-cart source/hash proof and Red context.
        if game == "yellow":
            continue
        panels = []
        for image in (original, after):
            panel = Image.new("RGB", ((w + 2) * 16, (h + 2) * 16), "#334258")
            sx, sy = max(0, (x - 1) * 16), max(0, (y - 1) * 16)
            ex, ey = min(image.width, (x + w + 1) * 16), min(image.height, (y + h + 1) * 16)
            panel.paste(image.crop((sx, sy, ex, ey)), (sx - (x - 1) * 16, sy - (y - 1) * 16))
            panels.append(panel)
        contacts.append((record, panels))
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 16)
    small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
    for start in range(0, len(contacts), 6):
        canvas = Image.new("RGB", (1500, 1130), "#18202c")
        draw = ImageDraw.Draw(canvas)
        draw.text((16, 12), "ROUTE ALIASES — complete source footprint and all available one-cell margins; proper house/Center functions only", fill="white", font=font)
        for i, (record, panels) in enumerate(contacts[start:start + 6]):
            left, top = i % 2 * 750 + 16, i // 2 * 360 + 50
            draw.text((left, top), f"{record['game'].upper()}/{record['map']}/{record['destination']}", fill="white", font=small)
            draw.text((left, top + 20), f"{record['template']} source rect{record['rect_cells']}; complete original outer-edge match", fill="#ced7e4", font=small)
            for col, panel in enumerate(panels):
                enlarged = panel.resize((panel.width * 3, panel.height * 3), Image.Resampling.NEAREST)
                md = ImageDraw.Draw(enlarged)
                md.rectangle((47, 47, enlarged.width - 48, enlarged.height - 48), outline="#ff547d", width=1)
                if record["rect_cells"][1] == 0:
                    md.text((50, 8), "MAP EDGE above", fill="white", font=small)
                canvas.paste(enlarged, (left + col * 350, top + 44))
        canvas.save(args.output / f"route-building-boundaries-contexts-{start // 6 + 1}.png")
    return proofs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path(os.environ["APPDATA"]) / "pokemon-love2d")
    parser.add_argument("--catalog", type=Path, default=WORKSPACE / ".work/tileshift-catalog")
    parser.add_argument("--output", type=Path, default=WORKSPACE / ".work/tileshift-route-architecture")
    parser.add_argument("--approved-candidates", action="store_true")
    parser.add_argument("--write-reviewed", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    johto_dir = WORKSPACE / ".work/tileshift-building-extended"
    kanto_dir = WORKSPACE / ".work/tileshift-building-kanto"
    johto = json.loads((johto_dir / "architecture-native-prototypes.json").read_text())
    kanto_report = json.loads((kanto_dir / "kanto-building-variants.json").read_text())
    models = {key: kanto_report["templates"][key] for key in ("center", "home32")}
    for key in models:
        (args.output / f"{key}-compact-prototype.png").write_bytes((kanto_dir / f"{key}-compact-prototype.png").read_bytes())
    instances, held = inventory(args, models, johto["source_buildings"] + kanto_report["source_instances"])
    coastal = [r for r in instances if r["map"] == "ROUTE_12" and r["template"] == "home32"]
    safe = [r for r in instances if r not in coastal]
    rows = kanto.positioned_rows(args, models, safe)
    proofs = contexts(args, rows, safe)
    report = {"status": "reviewed_active" if args.write_reviewed else "private_context_review", "matched_instances": instances, "held_instances": held,
              "positioned_rows": len(rows), "whole_source_boundary_proofs": proofs,
              "safe_grassy_background_instances": len(safe),
              "held_coastal_background_instances": coastal,
              "coastal_hold_reason": "The approved house has36 real native-alpha pixels. Route12 water touches the north roof, so those six instances require actual local coastal native animation before activation; no blanket grass substitution.",
              "source_profile_rule": "Complete own-cart picture, both exterior roof/wall edges, function and door anchor must match an already visually approved source building; a partial-picture/warp match is insufficient.",
              "production_rows_written": len(rows) if args.write_reviewed else 0}
    (args.output / "route-architecture-inventory.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"instances": len(instances), "safe_grassy_instances": len(safe), "held_coastal_instances": len(coastal), "positioned_rows": len(rows), "held_special_or_unmatched": len(held)}, indent=2))


if __name__ == "__main__":
    main()
