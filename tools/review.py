"""Produce an auditable, local visual review of a small Emerald mapping set.

The JSON contains references and fingerprints only. Extracted review artwork is
kept under .work and must not be included in a distributable mod package.
No candidate becomes an approved runtime mapping by running this tool.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import textwrap
import zlib

from PIL import Image, ImageDraw, ImageFont
import catalog

WORKSPACE = Path(__file__).resolve().parents[2]
PAIR = "general__petalburg"
SPECS = [
    ("red", "OVERWORLD", 1, 0, 1, "open_grassy_ground", "Complete flat ground. Native grass tufts become the Emerald ground texture.", "visual_review_pending"),
    ("red", "OVERWORLD", 1, 1, 1, "open_grassy_ground", "Complete blank ground variant. Emerald adds its normal ground tufts; no border or object geometry changes.", "visual_review_pending"),
    ("red", "OVERWORLD", 11, 0, 13, "tall_grass", "Full tall-grass cell in both games. Needs the donor foreground effect before enabling.", "foreground_integration_needed"),
    ("red", "OVERWORLD", 8, 3, 3, "freestanding_sign", "Both are complete 16px freestanding signboards with supports; source interaction remains native.", "visual_review_pending"),
    ("red", "OVERWORLD", 4, 0, 161, "open_water", "Both are complete water interiors, without a bank. This candidate must remain disabled until donor animation frames are supported.", "animation_integration_needed"),
    ("crystal", "TILESET_JOHTO", 1, 0, 1, "open_grassy_ground", "Complete flat ground without an edge or object; donor uses Emerald grass tufts.", "visual_review_pending"),
    ("crystal", "TILESET_JOHTO", 3, 0, 13, "tall_grass", "Full tall-grass cell in both games. Source collision is tall grass (0x18). Needs donor foreground effect.", "foreground_integration_needed"),
    ("crystal", "TILESET_JOHTO", 69, 0, 3, "freestanding_sign", "Both are complete freestanding signboards; compare support positions and border proportions before approval.", "visual_review_pending"),
    ("crystal", "TILESET_JOHTO", 7, 2, 161, "open_water", "Both are complete open-water cells, without a bank. Source collision0x29. Donor water animation still needs integration.", "animation_integration_needed"),
    ("yellow", "OVERWORLD", 1, 0, 1, "open_grassy_ground", "Yellow has a different tuft pattern from Red. It is still a complete ground interior without a border or object.", "visual_review_pending"),
    ("yellow", "OVERWORLD", 11, 0, 13, "tall_grass", "Yellow has its own tall-grass drawing. Complete tall-grass cell in both games; donor foreground still required.", "foreground_integration_needed"),
    ("yellow", "OVERWORLD", 8, 3, 3, "freestanding_sign", "Yellow's sign is a complete 16px signboard with two supports; reviewed separately from Red's different pixels.", "visual_review_pending"),
    ("red", "OVERWORLD", 8, 0, 1, "open_grassy_ground", "Complete ground with denser tufts: four native tile57 cells, all walkable. No building, bank or edge pixels.", "visual_review_pending"),
    ("yellow", "OVERWORLD", 8, 0, 1, "open_grassy_ground", "Yellow's independently checked dense ground texture: four tile57 cells, all walkable. No building or shore geometry.", "visual_review_pending"),
]
# Explicitly inspected source cells. A future candidate sharing a role is not
# automatically approved. Water is absent until animation is reviewed.
APPROVED = {(g, ts, block, q) for g, ts, block, q in (
    ("red", "OVERWORLD", 1, 0), ("red", "OVERWORLD", 1, 1),
    ("red", "OVERWORLD", 11, 0), ("red", "OVERWORLD", 8, 3),
    ("crystal", "TILESET_JOHTO", 1, 0), ("crystal", "TILESET_JOHTO", 3, 0),
    ("crystal", "TILESET_JOHTO", 69, 0), ("yellow", "OVERWORLD", 1, 0),
    ("yellow", "OVERWORLD", 11, 0), ("yellow", "OVERWORLD", 8, 3),
    ("red", "OVERWORLD", 8, 0), ("yellow", "OVERWORLD", 8, 0))}


def behavior_key(row):
    if row["generation"] == 2:
        return row["collision"], tuple(bool(a.get("priority")) for a in row["tile_attributes"])
    return tuple(row["walkable_tiles"]), row["grass_tile_present"], row["warp_tile_present"]


def gb_image(cache, game, ts_name, row, tilesets):
    ts = tilesets[game][ts_name]
    sheet = Image.open(cache / game / ts["image"])
    out = Image.new("RGBA", (16, 16))
    for i, raw in enumerate(row["tiles"]):
        tile, _ = catalog.gb_tile(sheet, ts, raw)
        out.paste(tile, (i % 2 * 8, i // 2 * 8))
    return out


def gba_image(cache, mid):
    native = cache / "emerald/data/generated/gba/native" / PAIR
    mids, pixels, _ = catalog.read_idx(native / "mids.idx")
    slot = mids.index(mid)
    palette = catalog.read_palettes(native / "palettes.bin")
    out = catalog.rgba_native(pixels[slot * 256:(slot + 1) * 256], palette)
    for layer in ("mid", "over"):
        path = native / f"mids_{layer}.idx"
        if path.exists():
            layer_mids, layer_pixels, _ = catalog.read_idx(path)
            assert layer_mids == mids
            out = Image.alpha_composite(out, catalog.rgba_native(layer_pixels[slot * 256:(slot + 1) * 256], palette, True))
    return out


def tile_patch(tile):
    patch = Image.new("RGBA", (48, 48))
    for y in range(3):
        for x in range(3):
            patch.paste(tile, (x * 16, y * 16))
    return patch.resize((96, 96), Image.Resampling.NEAREST)


def lua_value(value):
    if value is None:
        return "nil"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=True)
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "{" + ",".join(lua_value(v) for v in value) + "}"
    return "{" + ",".join(f"[{lua_value(k)}]={lua_value(v)}" for k, v in value.items()) + "}"


def reviewed_groups(candidates, games):
    groups = []
    for row in candidates:
        if row["status"] != "reviewed":
            continue
        seed = next(r for r in games[row["game"]]["cells"] if r["tileset"] == row["tileset"] and r["block_id"] == row["id"] and r["quadrant"] == row["quadrant"])
        targets = ("red", "blue", "yellow") if row["game"] == "red" else ("gold", "silver", "crystal") if row["game"] == "crystal" else ("yellow",)
        for game in targets:
            aliases = [r for r in games[game]["cells"] if r["tileset"] == row["tileset"] and r["used_by_map_count"] > 0
                       and r["source_pixels_complete"] and r["grayscale_pixel_sha256"] == row["sourceHash"]
                       and behavior_key(r) == behavior_key(seed)]
            if not aliases:
                continue
            source_info = next(t for t in games[game]["tilesets"] if t["tileset"] == row["tileset"])
            group = {"game": game, "style": "gen3", "tileset": row["tileset"], "role": row["role"],
                     "sourceHash": row["sourceHash"], "sourceFiles": source_info["fingerprints"],
                     "donor": {k: v for k, v in row["donor"].items() if k != "layerHashes"},
                     "evidence": row["evidence"] + " Visually approved 2026-10-26; per-game aliases have identical pixels, native behavior and priority.",
                     "cells": [[r["block_id"], r["quadrant"]] for r in aliases]}
            if row.get("foreground"):
                group["occludes"] = True
                group["foreground"] = row["foreground"]
            groups.append(group)
    seen = set()
    for group in groups:
        for cell in group["cells"]:
            key = group["game"], group["tileset"], *cell
            assert key not in seen, f"Duplicate reviewed mapping: {key}"
            seen.add(key)
    return groups


def write_reviewed(path, groups):
    header = """-- Visually reviewed Emerald outdoor equivalents, 2026-10-26.
-- Generated by tools/review.py --write-reviewed from explicit inspected seeds.
-- All aliases are checked per cartridge for identical source pixels, native
-- behavior and priority. Runtime checks each cell's source and donor hashes.
-- SourceFiles are provenance; pixel hashes are the runtime acceptance gate.
-- Native Emerald tall-grass foreground: frame4, bottom8px, placed at cell y+8.
-- Water, shores, ledges, trees, roofs and interiors remain unresolved.
local groups = {
"""
    footer = """}
local rows = {}
for _, group in ipairs(groups) do
  for _, cell in ipairs(group.cells) do
    rows[#rows + 1] = {
      game=group.game, style=group.style, tileset=group.tileset,
      id=cell[1], quadrant=cell[2], role=group.role, status='reviewed',
      sourceHash=group.sourceHash, sourceFiles=group.sourceFiles,
      donor=group.donor, evidence=group.evidence,
      occludes=group.occludes, foreground=group.foreground,
    }
  end
end
return rows
"""
    path.write_text(header + "".join("  " + lua_value(group) + ",\n" for group in groups) + footer, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path(catalog.os.environ["APPDATA"]) / "pokemon-love2d")
    parser.add_argument("--catalog", type=Path, default=WORKSPACE / ".work/tileshift-catalog")
    parser.add_argument("--output", type=Path, default=WORKSPACE / ".work/tileshift-review")
    parser.add_argument("--candidates", type=Path, default=WORKSPACE / "TileShift/mappings/candidates.json")
    parser.add_argument("--write-reviewed", action="store_true", help="Write mappings/reviewed.lua from the explicit inspected/approved seeds")
    args = parser.parse_args()
    games = {game: json.loads((args.catalog / f"{game}.json").read_text()) for game in ("red", "blue", "yellow", "gold", "silver", "crystal", "emerald")}
    tilesets = {game: catalog.read_lua(args.cache / game / "data/generated/tilesets.lua") for game in ("red", "yellow", "crystal")}
    candidates, previews = [], []
    for number, (game, ts, block, quadrant, mid, role, note, reason) in enumerate(SPECS, 1):
        source = next(r for r in games[game]["cells"] if r["tileset"] == ts and r["block_id"] == block and r["quadrant"] == quadrant)
        donor = next(r for r in games["emerald"]["cells"] if r["pair"] == PAIR and r["mid"] == mid)
        assert source["source_pixels_complete"]
        aliases = [r for r in games[game]["cells"] if r["tileset"] == ts and r["used_by_map_count"] > 0
                   and r["source_pixels_complete"] and r["grayscale_pixel_sha256"] == source["grayscale_pixel_sha256"]
                   and behavior_key(r) == behavior_key(source)]
        source_info = next(t for t in games[game]["tilesets"] if t["tileset"] == ts)
        donor_info = next(t for t in games["emerald"]["tilesets"] if t["pair"] == PAIR)
        row = {"game": game, "style": "gen3", "tileset": ts, "id": block, "quadrant": quadrant,
               "role": role, "status": "candidate", "blocking_reason": reason,
               "sourceHash": source["grayscale_pixel_sha256"],
               "donor": {"game": "emerald", "tileset": PAIR, "id": mid, "hash": donor["pixel_sha256"], "layerHashes": donor["layer_sha256"]},
               "sourceFiles": source_info["fingerprints"], "donorFiles": donor_info["fingerprints"],
               "evidence": f"tools/review.py review sheet row {number}: {note}",
               "same_geometry": "16px complete interior or object; no cell-boundary transformation",
               "aliases": [{"id": r["block_id"], "quadrant": r["quadrant"], "sourceHash": r["grayscale_pixel_sha256"]} for r in aliases],
               "alias_policy": "Same tileset, exact grayscale pixels, matching native behavior and priority; no cross-tileset inference."}
        if (game, ts, block, quadrant) in APPROVED:
            row["status"] = "reviewed"
            row.pop("blocking_reason")
            row["evidence"] += " Visually approved 2026-10-26."
        if role == "tall_grass":
            row["occludes"] = True
            row["foreground_candidate"] = {"game": "emerald", "file": "data/generated/gba/field_effects/tall_grass.rgba", "frame": 4,
                                            "crop": [0, 8, 16, 8], "placement": [0, 8], "format": "zlib compressed raw RGBA16x80",
                                            "sha256": catalog.sha((args.cache / "emerald/data/generated/gba/field_effects/tall_grass.rgba").read_bytes()),
                                            "engine_evidence": "src/core/game3/field_effects.lua: quadsFront bottom8px, static frame4 for NPCs; FEET_H=8"}
            if row["status"] == "reviewed":
                raw = (args.cache / "emerald/data/generated/gba/field_effects/tall_grass.rgba").read_bytes()
                if len(raw) != 16 * 80 * 4:
                    raw = zlib.decompress(raw)
                assert len(raw) == 16 * 80 * 4
                row["foreground"] = {"game": "emerald", "effect": "tall_grass", "hash": catalog.sha(raw)}
                note = "Complete tall-grass cell. Approved with exact native Emerald frame4 bottom8px feet cover; no invented mask."
                row["evidence"] = f"tools/review.py review sheet row {number}: {note} Visually approved 2026-10-26."
        if role == "open_water":
            row["animated"] = True
        candidates.append(row)
        previews.append((row, gb_image(args.cache, game, ts, source, tilesets), gba_image(args.cache, mid), note))
    width, row_h = 1120, 140
    canvas = Image.new("RGB", (width, 125 + len(previews) * row_h + 150), "#18202c")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 17)
    small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
    draw.text((15, 12), "TileShift: Emerald art on Gen1/2 — visual mapping review", fill="white", font=font)
    draw.text((15, 39), "GB shown in original source grayscale. Ground, signs and grass approved; water remains a candidate.", fill="#ced7e4", font=small)
    draw.text((15, 62), "Grass uses the exact native Emerald foreground. Water animation, roofs, trees and ledges remain unresolved.", fill="#ced7e4", font=small)
    for x, label in ((15, "Source cell"), (245, "Source"), (329, "Emerald"), (414, "Source repeated"), (530, "Emerald repeated"), (650, "Review notes")):
        draw.text((x, 95), label, fill="white", font=small)
    for i, (row, src, dst, note) in enumerate(previews):
        y = 125 + i * row_h
        draw.line((10, y - 8, width - 10, y - 8), fill="#344259")
        draw.text((15, y), f"{i+1}. {row['game']} / {row['status']}\n{row['tileset']}\n{row['id']}:{row['quadrant']} → Emerald {row['donor']['id']}\n{row['role']}", font=small, fill="white", spacing=6)
        canvas.paste(src.resize((64, 64), Image.Resampling.NEAREST), (245, y + 8))
        canvas.paste(dst.resize((64, 64), Image.Resampling.NEAREST), (329, y + 8))
        canvas.paste(tile_patch(src), (414, y))
        canvas.paste(tile_patch(dst), (530, y))
        message = note + f" Same-pixel/behavior source aliases: {len(row['aliases'])}."
        draw.text((650, y), "\n".join(textwrap.wrap(message, 57)), fill="#d4dfec", font=small, spacing=5)
    fx_path = args.cache / "emerald/data/generated/gba/field_effects/tall_grass.rgba"
    fx_raw = fx_path.read_bytes()
    if len(fx_raw) != 16 * 80 * 4:
        fx_raw = zlib.decompress(fx_raw)
    fx_sheet = Image.frombytes("RGBA", (16, 80), fx_raw)
    y = 125 + len(previews) * row_h
    draw.text((15, y), "Native Emerald tall-grass foreground sheet; bottom8px/frame4 is the static NPC feet cover.", fill="white", font=small)
    for frame in range(5):
        image = fx_sheet.crop((0, frame * 16, 16, frame * 16 + 16)).resize((64, 64), Image.Resampling.NEAREST)
        canvas.paste(image, (30 + frame * 110, y + 32), image)
        draw.text((30 + frame * 110, y + 104), f"frame {frame}", fill="white", font=small)
    args.output.mkdir(parents=True, exist_ok=True)
    canvas.save(args.output / "emerald-candidates.png")
    args.candidates.parent.mkdir(parents=True, exist_ok=True)
    args.candidates.write_text(json.dumps({"format": 1, "status": "mixed_reviewed_and_pending", "review_sheet": ".work/tileshift-review/emerald-candidates.png (generated locally by tools/review.py)",
                                          "rows": candidates}, indent=2), encoding="utf-8")
    groups = reviewed_groups(candidates, games)
    if args.write_reviewed:
        write_reviewed(WORKSPACE / "TileShift/mappings/reviewed.lua", groups)
    coverage = {}
    for game in ("red", "blue", "yellow", "gold", "silver", "crystal"):
        selected = [g for g in groups if g["game"] == game]
        coverage[game] = {"reviewed_cells": sum(len(g["cells"]) for g in selected),
                          "map_used_cells": sum(r["used_by_map_count"] > 0 for r in games[game]["cells"]),
                          "roles": {role: sum(len(g["cells"]) for g in selected if g["role"] == role) for role in ("open_grassy_ground", "tall_grass", "freestanding_sign")}}
    (args.output / "coverage.json").write_text(json.dumps(coverage, indent=2), encoding="utf-8")
    print(json.dumps({"reviewed_cells": sum(r["reviewed_cells"] for r in coverage.values()), "coverage": coverage,
                      "pending": [r["role"] for r in candidates if r["status"] == "candidate"],
                      "review_sheet": str(args.output / "emerald-candidates.png")}, indent=2))


if __name__ == "__main__":
    main()
