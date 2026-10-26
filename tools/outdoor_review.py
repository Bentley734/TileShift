"""Inventory Gen1 outdoor gaps and extract labeled native terrain references.

Review artwork is local under .work; this script never writes active mappings.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import argparse
import copy
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import building_review
import catalog
import preview
import review

WORKSPACE = Path(__file__).resolve().parents[2]
CACHE = Path(catalog.os.environ["APPDATA"]) / "pokemon-love2d"
OUTPUT = WORKSPACE / ".work/tileshift-outdoor-review"
MAPS = ("ROUTE_1", "VIRIDIAN_CITY")
SPECS = (
    (10, 0, 1, "short_nonencounter_grass", "Whole flat lawn; source grass44 is not encounter grass82."),
    (116, 0, 4, "decorative_flower_southeast", "Complete decorative flower cell; native five-frame flower cycle retained."),
    (116, 2, 4, "decorative_flower_northwest", "Opposite source8px flower corner; same whole decorative flower role."),
    (27, 0, 644, "garden_fence_pair", "Complete pair of upright garden-fence posts with rail; source fence footprint stays blocked."),
    (7, 2, 135, "south_ledge_center", "Upper8px lawn; lower8px south-facing jump ledge. Native MB_JUMP_SOUTH equivalent."),
    (26, 3, 135, "south_ledge_center_tufted", "Tufted lawn above the same straight south-facing jump ledge."),
    (26, 2, 176, "south_ledge_left_cap", "Left endpoint of south-facing ledge, curving down toward its right neighbor."),
    (66, 2, 177, "south_ledge_right_cap", "Right endpoint of south-facing ledge, curving up into lawn on its right."),
)


def approved_supplements(existing):
    """Root-reviewed walkable stair strips and the actual static Viridian pond."""
    fr = json.loads((WORKSPACE / ".work/tileshift-catalog/firered.json").read_text())
    donors = {(r["pair"], r["mid"]): r for r in fr["cells"]}
    def donor(pair, mid):
        return {"game": "firered", "tileset": pair, "id": mid, "hash": donors[pair, mid]["pixel_sha256"]}
    ground = donor("pallet_outdoor", 1)
    stairs = donor("general__rom_082d4b54", 137)
    image = preview.native_donor(CACHE, ground, {})
    image.paste(preview.native_donor(CACHE, stairs, {}).crop((0, 8, 16, 16)), (0, 8))
    stairs_hash = catalog.sha(image.tobytes())
    proposed = []
    for game in ("red", "blue", "yellow"):
        data = json.loads((WORKSPACE / f".work/tileshift-catalog/{game}.json").read_text())
        cells = {(r["block_id"], r["quadrant"]): r for r in data["cells"] if r["tileset"] == "OVERWORLD"}
        source_files = next(t["fingerprints"] for t in data["tilesets"] if t["tileset"] == "OVERWORLD")
        maps = catalog.read_lua(CACHE / game / "data/generated/maps.lua")
        specs = [(mapid, 47, 3, None, "walkable_stairs_bottom_half") for mapid in MAPS]
        specs += [("VIRIDIAN_CITY", block, q, mid, role) for block, q, mid, role in (
            (29, 0, 421, "freshwater_pond_northwest_bank"),
            (29, 1, 422, "freshwater_pond_north_bank"),
            (30, 1, 423, "freshwater_pond_northeast_bank"),
            (29, 2, 429, "freshwater_pond_west_bank"),
            (29, 3, 430, "freshwater_pond_interior"),
            (30, 3, 431, "freshwater_pond_east_bank"))]
        for mapid, block, q, mid, role in specs:
            seed = cells[block, q]
            used = {(id, quadrant) for id in maps[mapid]["blocks"] for quadrant in range(4)}
            selected = {(r["id"], r["quadrant"]) for r in existing if r["game"] == game
                        and r["tileset"] == "OVERWORLD" and r.get("map", mapid) == mapid}
            aliases = sorted(key for key in used - selected
                             if cells[key]["grayscale_pixel_sha256"] == seed["grayscale_pixel_sha256"]
                             and review.behavior_key(cells[key]) == review.behavior_key(seed))
            for id, quadrant in aliases:
                row = {"game": game, "style": "gen3", "map": mapid, "tileset": "OVERWORLD",
                       "id": id, "quadrant": quadrant, "role": role, "status": "reviewed",
                       "sourceHash": seed["grayscale_pixel_sha256"], "sourceFiles": source_files}
                if mid is None:
                    row.update(kind="native_composite", base=ground,
                               parts=[{"donor": stairs, "srcX": 0, "srcY": 8, "w": 16, "h": 8, "x": 0, "y": 8}],
                               compositionPixelHash=stairs_hash,
                               evidence="Root visually reviewed walkable-stairs-proposal.png. Source47:3 [44,44,60,60] "
                               "is walkable, not a jump ledge. Exact native FRLG rockstairs137 lower16x8 strip over lawn1 "
                               "preserves its upper8px lawn and bottom8px steps. No scaling, painting or mechanics edits.")
                else:
                    row.update(donor=donor("viridian_outdoor", mid),
                               evidence="Root visually reviewed viridian-pond-review.png: actual native FRLG Viridian "
                               "enclosed freshwater pond counterpart, MB_POND_WATER, correct bank orientation. Native0.3.96 "
                               "animator verified unchanged through640ticks/1280under-over snapshots/0palette mutations; "
                               "these pond mids are absent from every bank. Native static background retained; no ocean animation.")
                row["evidence"] += " Per-cartridge aliases require identical source pixels, walk/grass/warp behavior and actual map use."
                proposed.append(row)
    return proposed


def terrain_proposals(existing, write=False):
    catalogs = {g: json.loads((WORKSPACE / f".work/tileshift-catalog/{g}.json").read_text())
                for g in ("red", "blue", "yellow", "firered")}
    donors = {r["mid"]: r for r in catalogs["firered"]["cells"] if r["pair"] == "pallet_outdoor"}
    donor_refs = {mid: {"game": "firered", "tileset": "pallet_outdoor", "id": mid,
                        "hash": donors[mid]["pixel_sha256"]} for _, _, mid, _, _ in SPECS}
    flower = next(r for r in existing if r["game"] == "red" and r["role"] == "decorative_flower_southeast")
    proposed, pictures = [], []
    for game in ("red", "blue", "yellow"):
        maps = catalog.read_lua(CACHE / game / "data/generated/maps.lua")
        sets = catalog.read_lua(CACHE / game / "data/generated/tilesets.lua")
        ts = sets["OVERWORLD"]
        atlas = Image.open(CACHE / game / ts["image"])
        cells = {(r["block_id"], r["quadrant"]): r for r in catalogs[game]["cells"] if r["tileset"] == "OVERWORLD"}
        source_files = next(t["fingerprints"] for t in catalogs[game]["tilesets"] if t["tileset"] == "OVERWORLD")
        for block, q, mid, role, note in SPECS:
            seed = cells[block, q]
            pictures.append({"game": game, "seed": [block, q], "role": role, "note": note,
                             "source": preview.native_cell(atlas, ts, ts["blocks"][block], q),
                             "donor": preview.native_donor(CACHE, donor_refs[mid], {}), "mid": mid})
            for mapid in MAPS:
                used = {key for id in maps[mapid]["blocks"] for key in ((id, 0), (id, 1), (id, 2), (id, 3))}
                selected = {(r["id"], r["quadrant"]) for r in existing if r["game"] == game
                            and r["tileset"] == "OVERWORLD" and r.get("map", mapid) == mapid}
                aliases = sorted(key for key in used - selected
                                 if cells[key]["grayscale_pixel_sha256"] == seed["grayscale_pixel_sha256"]
                                 and review.behavior_key(cells[key]) == review.behavior_key(seed))
                for id, quadrant in aliases:
                    row = {"game": game, "style": "gen3", "map": mapid, "tileset": "OVERWORLD",
                           "id": id, "quadrant": quadrant, "role": role, "status": "reviewed",
                           "sourceHash": seed["grayscale_pixel_sha256"], "sourceFiles": source_files,
                           "donor": donor_refs[mid],
                           "evidence": f"tools/outdoor_review.py {game} {mapid} seed{block}:{q}. {note} "
                           "Native source and donor16px cells visually inspected side by side. Aliases require exact per-cartridge pixels, "
                           "matching native walk/grass/warp behavior and actual use in this map. Graphics only; ledge rules, collision, encounters and events stay native."}
                    if mid == 4:
                        row["animated"] = True
                        row["animation"] = copy.deepcopy(flower["animation"])
                    proposed.append(row)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 17)
    small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
    for section, selected in (("flat-features", pictures[:4] + pictures[8:12] + pictures[16:20]),
                              ("south-ledges", pictures[4:8] + pictures[12:16] + pictures[20:24])):
        panel = Image.new("RGB", (1180, 64 + len(selected) * 126), "#18212b")
        draw = ImageDraw.Draw(panel)
        draw.text((16, 12), "GEN1 OUTDOOR MATCH REVIEW — source left / native FireRed donor right", font=font, fill="white")
        for n, entry in enumerate(selected):
            y = 57 + n * 126
            panel.paste(entry["source"].resize((96, 96), Image.Resampling.NEAREST), (16, y))
            panel.paste(entry["donor"].resize((96, 96), Image.Resampling.NEAREST), (137, y))
            draw.text((252, y), f"{entry['game'].upper()} {entry['seed']} → FR pallet_outdoor:{entry['mid']} / {entry['role']}", font=font, fill="white")
            draw.text((252, y + 32), entry["note"], font=small, fill="#c4cdd8")
        panel.save(OUTPUT / (section + "-review.png"))
    proposed.extend(approved_supplements(existing))
    (OUTPUT / "proposed-clear-mappings.json").write_text(json.dumps(proposed, indent=2))
    if write:
        target = WORKSPACE / "TileShift/mappings/gen1_outdoor.lua"
        target.write_text("-- Reviewed Route1 and Viridian terrain. Native imported pixels only.\n"
                          "-- Generated by tools/outdoor_review.py --write-reviewed. No mechanics changes.\nreturn {\n" +
                          "".join("  " + review.lua_value(row) + ",\n" for row in proposed) + "}\n", encoding="utf-8")
    return proposed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-reviewed", action="store_true", help="Activate the explicitly inspected clear terrain matches")
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rows = [row for path in (WORKSPACE / "TileShift/mappings").glob("*.lua")
            for row in preview.read_reviewed(path)]
    source = json.loads((WORKSPACE / ".work/tileshift-catalog/red.json").read_text())
    maps = catalog.read_lua(CACHE / "red/data/generated/maps.lua")
    sets = catalog.read_lua(CACHE / "red/data/generated/tilesets.lua")
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 17)
    small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
    report = {"status": "inventory_only", "maps": {}}
    for mapid in MAPS:
        definition = maps[mapid]
        ts = sets[definition["tileset"]]
        atlas = Image.open(CACHE / "red" / ts["image"])
        index = {(r["block_id"], r["quadrant"]): r for r in source["cells"]
                 if r["tileset"] == definition["tileset"]}
        selected = {(r["id"], r["quadrant"]) for r in rows if r["game"] == "red"
                    and r["tileset"] == definition["tileset"] and r.get("map", mapid) == mapid}
        locations = defaultdict(list)
        for i, block in enumerate(definition["blocks"]):
            for q in range(4):
                if (block, q) not in selected:
                    locations[block, q].append([i % definition["width"] * 2 + q % 2,
                                                i // definition["width"] * 2 + q // 2])
        groups = defaultdict(list)
        for key in locations:
            groups[index[key]["grayscale_pixel_sha256"]].append(key)
        entries = []
        for fingerprint, keys in groups.items():
            cell = index[keys[0]]
            entries.append({"sourceHash": fingerprint, "keys": keys, "tiles": cell["tiles"],
                            "walkable_tiles": cell["walkable_tiles"],
                            "grass_tile_present": cell["grass_tile_present"],
                            "occurrences": sum(len(locations[k]) for k in keys),
                            "locations": [xy for k in keys for xy in locations[k]]})
        panel = Image.new("RGB", (1080, 74 + len(entries) * 116), "#18212b")
        draw = ImageDraw.Draw(panel)
        draw.text((16, 12), f"RED / {mapid}: unmatched native16px cells; no proposed equivalence yet", font=font, fill="white")
        for i, entry in enumerate(entries):
            y = 64 + i * 116
            block, q = entry["keys"][0]
            image = preview.native_cell(atlas, ts, ts["blocks"][block], q)
            panel.paste(image.resize((96, 96), Image.Resampling.NEAREST), (16, y))
            draw.text((132, y), f"#{i+1}: {entry['keys']} | {entry['occurrences']} map occurrences", font=font, fill="white")
            draw.text((132, y + 27), f"8px tiles {entry['tiles']} | walkable {entry['walkable_tiles']}", font=small, fill="#c4cdd8")
            draw.text((132, y + 50), "Cell locations " + str(entry["locations"][:10]), font=small, fill="#c4cdd8")
            draw.text((132, y + 75), "SHA256 " + entry["sourceHash"], font=small, fill="#c4cdd8")
        panel.save(OUTPUT / f"red-{mapid.lower()}-unmatched.png")
        report["maps"][mapid] = {"visible_cells": definition["width"] * definition["height"] * 4,
                                  "unmatched_occurrences": sum(len(p) for p in locations.values()), "groups": entries}
        preview.map_preview(CACHE, OUTPUT, "red", mapid, "red-" + mapid.lower(), rows, {}, 2, WORKSPACE / "TileShift")
    fr = json.loads((WORKSPACE / ".work/tileshift-catalog/firered.json").read_text())
    refs = {(r["pair"], r["mid"]): {"game": "firered", "tileset": r["pair"], "id": r["mid"], "hash": r["pixel_sha256"]}
            for r in fr["cells"]}
    root = CACHE / "firered/data/generated/gba/native"
    manifest = catalog.read_lua(root / "manifest.lua")
    for mapid in ("FR_ROUTE_1", "FR_VIRIDIAN_CITY"):
        spec = manifest["layouts"][mapid]
        layout = building_review.decode_layout(root / spec["file"])
        image = Image.new("RGBA", (layout["width"] * 16, layout["height"] * 16))
        packed = {}
        for i, mid in enumerate(layout["mids"]):
            image.paste(preview.native_donor(CACHE, refs[spec["pair"], mid], packed),
                        (i % layout["width"] * 16, i // layout["width"] * 16))
        image.save(OUTPUT / f"firered-{mapid.lower()}-native.png")
        grid = image.resize((image.width * 3, image.height * 3), Image.Resampling.NEAREST)
        draw = ImageDraw.Draw(grid)
        for i, mid in enumerate(layout["mids"]):
            draw.text((i % layout["width"] * 48 + 2, i // layout["width"] * 48 + 1), str(mid),
                      font=small, fill="white", stroke_fill="black", stroke_width=1)
        grid.convert("RGB").save(OUTPUT / f"firered-{mapid.lower()}-grid.png")
    (OUTPUT / "inventory.json").write_text(json.dumps(report, indent=2))
    proposal_existing = [row for path in (WORKSPACE / "TileShift/mappings").glob("*.lua")
                         if path.name != "gen1_outdoor.lua" for row in preview.read_reviewed(path)]
    proposed = terrain_proposals(proposal_existing, args.write_reviewed)
    print("Clear terrain proposals:", len(proposed), dict(Counter(r["role"] for r in proposed)))
    print(json.dumps({m: {k: v for k, v in data.items() if k != "groups"} for m, data in report["maps"].items()}, indent=2))


if __name__ == "__main__":
    main()
