"""Private native cave references and visually selected Gen1 cave mappings.

No collision-only matching. Every source16 is reviewed in its map context;
native counterpart references retain each cave family's imported palette.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import catalog
import preview
from building_review import decode_layout

WORKSPACE = Path(__file__).resolve().parents[2]
NATIVE_MAPS = ("FR_MT_MOON_1F", "FR_MT_MOON_B1F", "FR_MT_MOON_B2F",
               "FR_DIGLETTS_CAVE_B1F", "FR_DIGLETTS_CAVE_NORTH_ENTRANCE",
               "FR_SEAFOAM_ISLANDS_1F", "FR_ROCK_TUNNEL_1F", "FR_CERULEAN_CAVE_1F")
SOURCE_MAPS = ("MT_MOON_1F", "MT_MOON_B1F", "MT_MOON_B2F", "DIGLETTS_CAVE",
               "DIGLETTS_CAVE_ROUTE_2", "SEAFOAM_ISLANDS_1F", "ROCK_TUNNEL_1F", "CERULEAN_CAVE_1F")
ROLES = (("cave_rock_floor", (1, 0), (32, 32, 32, 32), 641),
         ("cave_raised_rock_mass_top", (20, 3), (5, 5, 5, 5), 657),
         ("cave_raised_rock_mass_front", (28, 3), (16, 16, 16, 16), 665),
         ("cave_descending_ladder", (35, 0), (8, 9, 24, 25), None))


def counterpart(name):
    return {"DIGLETTS_CAVE": "FR_DIGLETTS_CAVE_B1F", "DIGLETTS_CAVE_ROUTE_2": "FR_DIGLETTS_CAVE_NORTH_ENTRANCE",
            "DIGLETTS_CAVE_ROUTE_11": "FR_DIGLETTS_CAVE_SOUTH_ENTRANCE"}.get(name, "FR_" + name)


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


def contact(path, heading, rows, cols=8, scale=4):
    cw, ch = 150, 118
    image = Image.new("RGB", (cols * cw, 70 + ((len(rows) + cols - 1) // cols) * ch), "#18202c")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
    draw.text((12, 12), heading, fill="white", font=font)
    draw.text((12, 38), "Native imported pixels; IDs are references, not automatic semantic equivalents.", fill="#ced7e4", font=font)
    for i, (label, tile) in enumerate(rows):
        x, y = i % cols * cw + 10, i // cols * ch + 70
        image.paste(tile.resize((16 * scale, 16 * scale), Image.Resampling.NEAREST), (x, y))
        draw.multiline_text((x, y + 16 * scale + 4), label, fill="white", font=font, spacing=1)
    image.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path(catalog.os.environ["APPDATA"]) / "pokemon-love2d")
    parser.add_argument("--catalog", type=Path, default=WORKSPACE / ".work/tileshift-catalog")
    parser.add_argument("--output", type=Path, default=WORKSPACE / ".work/tileshift-cave-review")
    parser.add_argument("--write-reviewed", action="store_true", help="Write the four reviewed roles after source/donor contact review")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    root = args.cache / "red"
    maps = catalog.read_lua(root / "data/generated/maps.lua")
    ts = catalog.read_lua(root / "data/generated/tilesets.lua")["CAVERN"]
    sheet = Image.open(root / ts["image"])
    cells = json.loads((args.catalog / "red.json").read_text())["cells"]
    cells = [r for r in cells if r.get("tileset") == "CAVERN" and r["used_by_map_count"]]
    grouped = defaultdict(list)
    for cell in cells:
        grouped[cell["grayscale_pixel_sha256"]].append(cell)
    used = Counter()
    contexts = defaultdict(list)
    index = {(r["block_id"], r["quadrant"]): r for r in cells}
    for name, m in maps.items():
        if not isinstance(m, dict) or m.get("tileset") != "CAVERN":
            continue
        image = Image.new("RGBA", (m["width"] * 32, m["height"] * 32))
        for pos, bid in enumerate(m["blocks"]):
            for q in range(4):
                cell = index[bid, q]
                tile = preview.native_cell(sheet, ts, ts["blocks"][bid], q)
                assert catalog.sha(tile.tobytes()) == cell["grayscale_pixel_sha256"]
                x, y = pos % m["width"] * 2 + q % 2, pos // m["width"] * 2 + q // 2
                image.paste(tile, (x * 16, y * 16))
                used[cell["grayscale_pixel_sha256"]] += 1
                if len(contexts[cell["grayscale_pixel_sha256"]]) < 8:
                    contexts[cell["grayscale_pixel_sha256"]].append({"map": name, "cell_xy": [x, y], "block": bid, "quadrant": q})
        if name in SOURCE_MAPS:
            image.save(args.output / f"red-{name}-native.png")
    groups, rows = [], []
    for number, (hash_, aliases) in enumerate(grouped.items()):
        first = aliases[0]
        tile = preview.native_cell(sheet, ts, ts["blocks"][first["block_id"]], first["quadrant"])
        rows.append((f"#{number} {first['block_id']}:{first['quadrant']} ({used[hash_]})\nraw{first['tiles']}", tile))
        groups.append({"number": number, "pixel_sha256": hash_, "seed": [first["block_id"], first["quadrant"]],
                       "tiles": first["tiles"], "visible_occurrences": used[hash_], "contexts": contexts[hash_],
                       "aliases": [[r["block_id"], r["quadrant"]] for r in aliases], "status": "needs_semantic_review"})
    contact(args.output / "red-cavern-unique-contact.png", "RED CAVERN: all32 distinct used source16 graphics", rows)
    native = args.cache / "firered/data/generated/gba/native"
    manifest = catalog.read_lua(native / "manifest.lua")
    donor_records = json.loads((args.catalog / "firered.json").read_text())["cells"]
    packed, pairs = {}, set()
    native_scenes = []
    for name in NATIVE_MAPS:
        spec = manifest["layouts"][name]
        pairs.add(spec["pair"])
        layout = decode_layout(native / spec["file"])
        records = {r["mid"]: r for r in donor_records if r.get("pair") == spec["pair"]}
        image = Image.new("RGBA", (layout["width"] * 16, layout["height"] * 16))
        for i, mid in enumerate(layout["mids"]):
            ref = {"game": "firered", "tileset": spec["pair"], "id": mid, "hash": records[mid]["pixel_sha256"]}
            image.paste(preview.native_donor(args.cache, ref, packed), (i % layout["width"] * 16, i // layout["width"] * 16))
        image.save(args.output / f"firered-{name}-native.png")
        native_scenes.append({"map": name, "pair": spec["pair"], "layout_sha256": layout["file_sha256"],
                              "dimensions": [layout["width"], layout["height"]], "map_pixel_sha256": catalog.sha(image.tobytes())})
    for pair in sorted(pairs):
        rows = []
        for record in donor_records:
            if record.get("pair") != pair:
                continue
            ref = {"game": "firered", "tileset": pair, "id": record["mid"], "hash": record["pixel_sha256"]}
            tile = preview.native_donor(args.cache, ref, packed)
            behavior = (record["behavior_hint"] or "unspecified").removeprefix("MB_")
            rows.append((f"mid{record['mid']}\n{behavior[:20]}", tile))
        contact(args.output / f"firered-{pair}-contact.png", "FIRERED cave native pair: " + pair, rows)
    # Four complete16px roles only. Side-wall edges/corners, up-ladders whose
    # native sprite spans32px, entrances, water and puzzle objects are held.
    donor_index = {(r["pair"], r["mid"]): r for r in donor_records}
    native_warps = catalog.read_lua(args.cache / "firered/data/generated/gba/warps.lua")
    candidate_rows, coverage, held = [], {}, []
    for game in ("red", "blue", "yellow"):
        base = args.cache / game
        game_maps = catalog.read_lua(base / "data/generated/maps.lua")
        sets_path = base / "data/generated/tilesets.lua"
        game_ts = catalog.read_lua(sets_path)["CAVERN"]
        game_sheet = Image.open(base / game_ts["image"])
        catalog_cells = json.loads((args.catalog / f"{game}.json").read_text())["cells"]
        source_index = {(r["block_id"], r["quadrant"]): r for r in catalog_cells if r.get("tileset") == "CAVERN"}
        hashes = {}
        for role, seed, raw, _ in ROLES:
            source = source_index[seed]
            assert tuple(source["tiles"]) == raw
            actual = preview.native_cell(game_sheet, game_ts, game_ts["blocks"][seed[0]], seed[1])
            assert catalog.sha(actual.tobytes()) == source["grayscale_pixel_sha256"]
            hashes[source["grayscale_pixel_sha256"]] = role
        fingerprints = {"metadata": catalog.sha(sets_path.read_bytes()), "image": catalog.sha((base / game_ts["image"]).read_bytes()),
                        "maps": catalog.sha((base / "data/generated/maps.lua").read_bytes())}
        covered, total = 0, 0
        for name, m in game_maps.items():
            if not isinstance(m, dict) or m.get("tileset") != "CAVERN":
                continue
            native_name = counterpart(name)
            spec = manifest["layouts"][native_name]
            layout = decode_layout(native / spec["file"])
            occurrences = Counter((bid, q) for bid in m["blocks"] for q in range(4))
            for key, count in sorted(occurrences.items()):
                source = source_index[key]
                role = hashes.get(source["grayscale_pixel_sha256"])
                total += count
                if not role:
                    continue
                definition = next(r for r in ROLES if r[0] == role)
                assert tuple(source["tiles"]) == definition[2]
                mid = definition[3]
                native_evidence = {"map": native_name, "layoutFileHash": layout["file_sha256"]}
                if mid is None:
                    destinations = set()
                    for w in m.get("warps", []):
                        x, y = w["x"], w["y"]
                        actual_key = m["blocks"][y // 2 * m["width"] + x // 2], y % 2 * 2 + x % 2
                        if actual_key == key:
                            destinations.add(counterpart(w["destMap"]))
                    assert destinations, (game, name, key, "Ladder has no warp evidence")
                    mids_at_warps = {layout["mids"][w["y"] * layout["width"] + w["x"]]
                                    for w in native_warps[native_name] if w["destMap"] in destinations
                                    and donor_index[spec["pair"], layout["mids"][w["y"] * layout["width"] + w["x"]]].get("behavior_hint") == "MB_LADDER"}
                    if not mids_at_warps or not mids_at_warps <= {645, 687}:
                        held.append({"game": game, "map": name, "source": key, "role": role,
                                     "reason": "No unambiguous complete native descending-ladder match", "nativeMids": sorted(mids_at_warps)})
                        continue
                    mid = 645 if 645 in mids_at_warps else 687
                    native_evidence["warpDestinations"] = sorted(destinations)
                    native_evidence["sameFunctionNativeLadderMids"] = sorted(mids_at_warps)
                if mid not in layout["mids"]:
                    held.append({"game": game, "map": name, "source": key, "role": role,
                                 "reason": "Selected cave-family graphic is not used in the exact native counterpart; further context review required", "nativeMid": mid})
                    continue
                donor = donor_index[spec["pair"], mid]
                ref = {"game": "firered", "tileset": spec["pair"], "id": mid, "hash": donor["pixel_sha256"]}
                preview.native_donor(args.cache, ref, packed)
                actual = preview.native_cell(game_sheet, game_ts, game_ts["blocks"][key[0]], key[1])
                assert catalog.sha(actual.tobytes()) == source["grayscale_pixel_sha256"]
                candidate_rows.append({"game": game, "style": "gen3", "map": name, "tileset": "CAVERN", "id": key[0], "quadrant": key[1],
                                       "role": role, "status": "reviewed" if args.write_reviewed else "candidate",
                                       "sourceHash": source["grayscale_pixel_sha256"], "sourceFiles": fingerprints, "donor": ref,
                                       "nativeContext": native_evidence,
                                       "evidence": "Complete16px source graphic reviewed in native cave context. Uses the actual FireRed counterpart's cave-family palette and complete same-role native metatile. Floor, raised rock-mass top/front and descending ladder are distinguished visually; no collision-only matching. Cave walls/corners, up-ladders, entrances, water and puzzles are not inferred. Native layout, collision and warps are preserved."})
                covered += count
            coverage[game] = {"covered_occurrences": covered, "total_occurrences": total}
    (args.output / "gen1-caves-candidates.json").write_text(json.dumps(candidate_rows, indent=2), encoding="utf-8")
    # Honest contextual previews show the unchanged Gen1 footprints and every
    # still-native edge/exit/up-ladder instead of implying a complete cave.
    scene_coverage = {}
    for name in ("MT_MOON_1F", "DIGLETTS_CAVE_ROUTE_2", "SEAFOAM_ISLANDS_1F"):
        m = maps[name]
        selected = {(r["id"], r["quadrant"]): r for r in candidate_rows if r["game"] == "red" and r["map"] == name}
        before = Image.open(args.output / f"red-{name}-native.png").convert("RGBA")
        after = before.copy()
        replaced = 0
        for pos, bid in enumerate(m["blocks"]):
            for q in range(4):
                row = selected.get((bid, q))
                if row:
                    after.paste(preview.native_donor(args.cache, row["donor"], packed),
                                (pos % m["width"] * 32 + q % 2 * 16, pos // m["width"] * 32 + q // 2 * 16))
                    replaced += 1
        after.save(args.output / f"red-{name}-initial-development.png")
        image = Image.new("RGB", (max(700, before.width * 2 + 48), before.height + 130), "#18202c")
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 16)
        draw.text((12, 12), f"DEVELOPMENT — {name}: {replaced}/{len(m['blocks']) * 4} cells replaced", fill="white", font=font)
        draw.text((12, 40), "Source footprints remain. Edges/corners, up-ladders, exits, water and puzzles still use native Gen1 art.", fill="#ced7e4", font=font)
        draw.text((12, 76), "Original source background", fill="white", font=font)
        draw.text((before.width + 30, 76), "Four reviewed complete-cell roles", fill="white", font=font)
        image.paste(before, (12, 110))
        image.paste(after, (before.width + 30, 110))
        image.save(args.output / f"red-{name}-initial-comparison.png")
        scene_coverage[name] = {"replaced": replaced, "total": len(m["blocks"]) * 4}
    if args.write_reviewed:
        target = WORKSPACE / "TileShift/mappings/gen1_caves.lua"
        target.write_text("-- Four visually reviewed complete cave-cell roles, scoped to each native Kanto counterpart.\nreturn {\n"
                          + "".join("  " + lua(row) + ",\n" for row in candidate_rows) + "}\n", encoding="utf-8")
    table = Image.new("RGB", (1260, 720), "#18202c")
    draw = ImageDraw.Draw(table)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 16)
    small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
    draw.text((12, 12), "CAVE INITIAL REVIEW — complete floor, raised mass and descending ladder; no edge/entrance inference", fill="white", font=font)
    columns = ("Gen1 source", "Mt Moon / Victory", "Diglett", "Seafoam", "Rock Tunnel", "Cerulean")
    native_pairs = ("general__rom_082d4bfc", "general__rom_082d4e0c", "general__rom_082d4e24", "general__rom_082d4df4", "general__rom_082d4e54")
    for i, label in enumerate(columns):
        draw.text((i * 210 + 12, 48), label, fill="white", font=font)
    for y, (role, seed, raw, mid) in enumerate(ROLES):
        top = 94 + y * 144
        source = index[seed]
        tile = preview.native_cell(sheet, ts, ts["blocks"][seed[0]], seed[1])
        table.paste(tile.resize((80, 80), Image.Resampling.NEAREST), (12, top))
        draw.text((12, top + 84), role.removeprefix("cave_").replace("_", " "), fill="white", font=small)
        for x, pair in enumerate(native_pairs):
            chosen = mid or (687 if "4e0c" in pair else 645)
            ref = {"game": "firered", "tileset": pair, "id": chosen, "hash": donor_index[pair, chosen]["pixel_sha256"]}
            tile = preview.native_donor(args.cache, ref, packed)
            table.paste(tile.resize((80, 80), Image.Resampling.NEAREST), ((x + 1) * 210 + 12, top))
            draw.text(((x + 1) * 210 + 12, top + 84), "native mid" + str(chosen), fill="white", font=small)
    draw.text((12, 683), "Up-ladders are held: native artwork spans32px. Other held cells include wall edges/corners, rock borders, cave exits, water and puzzles.", fill="#ced7e4", font=small)
    table.save(args.output / "initial-cave-role-review.png")
    report = {"status": "reviewed_initial_batch_activated" if args.write_reviewed else "reference_only_no_active_mapping", "source_groups": groups,
              "source_distinct_graphics": len(groups), "source_used_aliases": len(cells),
              "source_visible_occurrences": sum(used.values()), "native_scenes": native_scenes,
              "candidate_rows": len(candidate_rows), "candidate_coverage": coverage,
              "scene_coverage": scene_coverage, "held_source_rows": held,
              "reviewed_rows_written": len(candidate_rows) if args.write_reviewed else 0}
    (args.output / "cave-reference.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("source_groups", "native_scenes", "held_source_rows")}, indent=2))


if __name__ == "__main__":
    main()
