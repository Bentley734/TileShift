"""Private Gen1/2 interior source and actual Gen3 counterpart review.

Produces maps and numbered cell contacts only. Nothing is approved or activated
by inspecting frequency, collision, or this tool's suggested room pairing.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import zlib

from PIL import Image, ImageDraw, ImageFont
import catalog
import preview
from building_review import decode_layout
from newbark_building_review import lua


WORKSPACE = Path(__file__).resolve().parents[2]
PAIRS = (
    ("red-home1", "red", "REDS_HOUSE_1F", "firered", "FR_PLAYERS_HOUSE_1F"),
    ("red-home2", "red", "REDS_HOUSE_2F", "firered", "FR_PLAYERS_HOUSE_2F"),
    ("red-house", "red", "BLUES_HOUSE", "firered", "FR_RIVALS_HOUSE"),
    ("red-lab", "red", "OAKS_LAB", "firered", "FR_OAKS_LAB"),
    ("red-center", "red", "VIRIDIAN_POKECENTER", "firered", "FR_VIRIDIAN_CITY_POKEMON_CENTER_1F"),
    ("red-mart", "red", "VIRIDIAN_MART", "firered", "FR_VIRIDIAN_CITY_MART"),
    ("red-facility", "red", "SILPH_CO_1F", "firered", "FR_SILPH_CO_1F"),
    ("red-tower", "red", "POKEMON_TOWER_1F", "firered", "FR_POKEMON_TOWER_1F"),
    ("crystal-home1", "crystal", "PLAYERS_HOUSE_1F", "firered", "FR_PLAYERS_HOUSE_1F"),
    ("crystal-home2", "crystal", "PLAYERS_HOUSE_2F", "firered", "FR_PLAYERS_HOUSE_2F"),
    ("crystal-house", "crystal", "GUIDE_GENTS_HOUSE", "firered", "FR_RIVALS_HOUSE"),
    ("crystal-center", "crystal", "CHERRYGROVE_POKECENTER_1F", "firered", "FR_VIRIDIAN_CITY_POKEMON_CENTER_1F"),
    ("crystal-mart", "crystal", "CHERRYGROVE_MART", "firered", "FR_VIRIDIAN_CITY_MART"),
    ("crystal-lab", "crystal", "ELMS_LAB", "emerald", "EM_LITTLEROOT_TOWN_PROFESSOR_BIRCHS_LAB"),
    ("red-rocket", "red", "ROCKET_HIDEOUT_B1F", "firered", "FR_ROCKET_HIDEOUT_B1F"),
    ("red-mansion", "red", "POKEMON_MANSION_1F", "firered", "FR_POKEMON_MANSION_1F"),
    ("red-power", "red", "POWER_PLANT", "firered", "FR_POWER_PLANT"),
    ("red-gate", "red", "ROUTE_11_GATE_1F", "firered", "FR_ROUTE_11_EAST_ENTRANCE_1F"),
    ("red-tunnel", "red", "UNDERGROUND_PATH_NORTH_SOUTH", "firered", "FR_UNDERGROUND_PATH_NORTH_SOUTH_TUNNEL"),
    ("red-ship", "red", "SS_ANNE_1F", "firered", "FR_SSANNE_1F_CORRIDOR"),
    ("red-shiproom", "red", "SS_ANNE_1F_ROOMS", "firered", "FR_SSANNE_1F_ROOM1"),
    ("red-celadongym", "red", "CELADON_GYM", "firered", "FR_CELADON_CITY_GYM"),
    ("red-dojo", "red", "FIGHTING_DOJO", "firered", "FR_SAFFRON_CITY_DOJO"),
    ("red-cinnabargym", "red", "CINNABAR_GYM", "firered", "FR_CINNABAR_ISLAND_GYM"),
    ("red-saffrongym", "red", "SAFFRON_GYM", "firered", "FR_SAFFRON_CITY_GYM"),
    ("red-museum", "red", "MUSEUM_1F", "firered", "FR_PEWTER_CITY_MUSEUM_1F"),
    ("red-fanclub", "red", "POKEMON_FAN_CLUB", "firered", "FR_VERMILION_CITY_POKEMON_FAN_CLUB"),
    ("red-labroom", "red", "CINNABAR_LAB", "firered", "FR_CINNABAR_ISLAND_POKEMON_LAB_ENTRANCE"),
    ("red-dept", "red", "CELADON_MART_1F", "firered", "FR_CELADON_CITY_DEPARTMENT_STORE_1F"),
    ("red-gamecorner", "red", "GAME_CORNER", "firered", "FR_CELADON_CITY_GAME_CORNER"),
    ("red-lance", "red", "LANCES_ROOM", "firered", "FR_POKEMON_LEAGUE_LANCES_ROOM"),
    ("red-bruno", "red", "BRUNOS_ROOM", "firered", "FR_POKEMON_LEAGUE_BRUNOS_ROOM"),
    ("red-agatha", "red", "AGATHAS_ROOM", "firered", "FR_POKEMON_LEAGUE_AGATHAS_ROOM"),
    ("red-lorelei", "red", "LORELEIS_ROOM", "firered", "FR_POKEMON_LEAGUE_LORELEIS_ROOM"),
    ("red-champion", "red", "CHAMPIONS_ROOM", "firered", "FR_POKEMON_LEAGUE_CHAMPIONS_ROOM"),
    ("crystal-dept", "crystal", "CELADON_DEPT_STORE_1F", "firered", "FR_CELADON_CITY_DEPARTMENT_STORE_1F"),
    ("crystal-gate", "crystal", "ROUTE_5_SAFFRON_GATE", "firered", "FR_ROUTE_5_SOUTH_ENTRANCE"),
    ("crystal-tunnel", "crystal", "UNDERGROUND_PATH", "firered", "FR_UNDERGROUND_PATH_NORTH_SOUTH_TUNNEL"),
    ("crystal-rocket", "crystal", "TEAM_ROCKET_BASE_B2F", "firered", "FR_ROCKET_HIDEOUT_B1F"),
    ("crystal-silph", "crystal", "SILPH_CO_1F", "firered", "FR_SILPH_CO_1F"),
    ("crystal-power", "crystal", "POWER_PLANT", "firered", "FR_POWER_PLANT"),
    ("crystal-ship", "crystal", "FAST_SHIP_1F", "firered", "FR_SSANNE_1F_CORRIDOR"),
    ("crystal-shiproom", "crystal", "FAST_SHIP_CABINS_SE_SSE_CAPTAINS_CABIN", "firered", "FR_SSANNE_1F_ROOM1"),
    ("crystal-dojo", "crystal", "FIGHTING_DOJO", "firered", "FR_SAFFRON_CITY_DOJO"),
    ("crystal-celadongym", "crystal", "CELADON_GYM", "firered", "FR_CELADON_CITY_GYM"),
    ("crystal-saffrongym", "crystal", "SAFFRON_GYM", "firered", "FR_SAFFRON_CITY_GYM"),
    ("crystal-bruno", "crystal", "BRUNOS_ROOM", "firered", "FR_POKEMON_LEAGUE_BRUNOS_ROOM"),
    ("crystal-lance", "crystal", "LANCES_ROOM", "firered", "FR_POKEMON_LEAGUE_LANCES_ROOM"),
    ("crystal-gamecorner", "crystal", "CELADON_GAME_CORNER", "firered", "FR_CELADON_CITY_GAME_CORNER"),
)

# These complete plain floor cells were visually checked beside their actual
# native room counterparts. Scope is explicit room function, never collision.
FLOORS = {
    "red-home1": (15, 0, 1), "red-home2": (15, 0, 1),
    "red-house": (15, 0, 1), "red-lab": (5, 0, 649),
    "red-center": (15, 0, 641), "red-mart": (15, 0, 641),
    "red-facility": (14, 0, 820), "red-tower": (14, 0, 642),
    "crystal-home1": (3, 0, 1), "crystal-home2": (5, 0, 1),
    "crystal-house": (15, 0, 1), "crystal-center": (4, 0, 641),
    "crystal-mart": (43, 0, 641), "crystal-lab": (1, 0, 514),
    "red-rocket": (14, 0, 641), "red-mansion": (14, 0, 644),
    "red-power": (14, 0, 671), "red-gate": (31, 2, 641),
    "red-tunnel": (4, 0, 649), "red-ship": (4, 0, 664),
    "red-shiproom": (11, 0, 796), "red-celadongym": (5, 0, 677),
    "red-dojo": (5, 0, 704), "red-cinnabargym": (14, 0, 641),
    "red-saffrongym": (47, 0, 641), "red-museum": (0, 0, 641),
    "red-fanclub": (3, 0, 648), "red-labroom": (7, 0, 129),
    "red-dept": (11, 0, 704), "red-gamecorner": (32, 0, 657),
    "red-lance": (5, 0, 784), "red-bruno": (5, 0, 720),
    "red-agatha": (54, 0, 752), "red-lorelei": (24, 0, 680),
    "red-champion": (5, 0, 911), "crystal-dept": (4, 0, 704),
    "crystal-gate": (1, 0, 641), "crystal-tunnel": (12, 1, 649),
    "crystal-rocket": (54, 2, 641), "crystal-silph": (7, 0, 820),
    "crystal-power": (7, 0, 671), "crystal-shiproom": (11, 0, 796),
    "crystal-dojo": (28, 0, 704), "crystal-celadongym": (28, 0, 677),
    "crystal-saffrongym": (15, 0, 641), "crystal-bruno": (56, 0, 720),
    "crystal-lance": (49, 0, 784), "crystal-gamecorner": (1, 0, 657),
}


def floor_scope(stem, map_id, definition, source_tileset, source_map):
    if definition["tileset"] != source_tileset:
        return False
    role = stem.split("-", 1)[1]
    if role in ("home1", "home2"):
        return map_id in ({"REDS_HOUSE_1F", "COPYCATS_HOUSE_1F"} if stem.startswith("red") and role == "home1" else
                         {"REDS_HOUSE_2F", "COPYCATS_HOUSE_2F"} if stem.startswith("red") else
                         {"PLAYERS_HOUSE_1F", "REDS_HOUSE_1F", "COPYCATS_HOUSE_1F", "ELMS_HOUSE"} if role == "home1" else
                         {"PLAYERS_HOUSE_2F", "REDS_HOUSE_2F", "COPYCATS_HOUSE_2F"})
    if role == "house":
        return ("HOUSE" in map_id or map_id in {"NAME_RATERS_HOUSE", "GOLDENROD_NAME_RATER", "LAVENDER_NAME_RATER"}) and not any(
            word in map_id for word in ("SCHOOL", "TRAINER_HOUSE", "SOUL_HOUSE", "BETA"))
    if role == "center":
        return "POKECENTER" in map_id and "2F" not in map_id
    if role == "mart":
        return map_id.endswith("_MART")
    if role == "facility":
        return map_id.startswith("SILPH_CO_")
    if role == "tower":
        return map_id.startswith("POKEMON_TOWER_")
    if role == "rocket":
        return map_id.startswith("ROCKET_HIDEOUT_" if stem.startswith("red") else "TEAM_ROCKET_BASE_")
    if role == "mansion":
        return map_id.startswith("POKEMON_MANSION_")
    if role == "gate":
        return "GATE" in map_id and "BETA" not in map_id
    if role == "tunnel":
        return map_id in {"UNDERGROUND_PATH_NORTH_SOUTH", "UNDERGROUND_PATH_WEST_EAST", "UNDERGROUND_PATH"}
    if role == "ship":
        return map_id in {"SS_ANNE_1F", "SS_ANNE_2F", "SS_ANNE_3F", "SS_ANNE_B1F", "FAST_SHIP_1F", "FAST_SHIP_B1F"}
    if role == "shiproom":
        return map_id.endswith("_ROOMS") if stem.startswith("red") else map_id.startswith("FAST_SHIP_CABINS_")
    if role == "museum":
        return map_id in {"MUSEUM_1F", "MUSEUM_2F"}
    if role == "labroom":
        return map_id.startswith("CINNABAR_LAB")
    if role == "dept":
        return (map_id.startswith("CELADON_MART_") or "DEPT_STORE_" in map_id) and "ROOF" not in map_id and "ELEVATOR" not in map_id
    return map_id == source_map


def reviewed_floors(imports, output, references, activate=False):
    rows, held, scopes = [], [], []
    for item in references:
        stem = item["id"]
        if stem not in FLOORS:
            continue
        source_meta, donor_meta = item["source"], item["donor"]
        block_id, quadrant, mid = FLOORS[stem]
        seed = imports.cell_index(source_meta["game"])[source_meta["tileset"], block_id, quadrant]
        native = imports.cell_index(donor_meta["game"])[donor_meta["tileset"], mid]
        spec = imports.table(donor_meta["game"], "gba/native/manifest")["layouts"][donor_meta["map"]]
        layout_file = imports.cache / donor_meta["game"] / "data/generated/gba/native" / spec["file"]
        for game in (("red", "blue", "yellow") if source_meta["game"] == "red" else ("gold", "silver", "crystal")):
            index = imports.cell_index(game)
            ts_name = source_meta["tileset"]
            fingerprints = next(r["fingerprints"] for r in json.loads((imports.catalogs / f"{game}.json").read_text())["tilesets"] if r["tileset"] == ts_name)
            candidates = {}
            for (name, bid, q), cell in index.items():
                if name != ts_name or cell["grayscale_pixel_sha256"] != seed["grayscale_pixel_sha256"]:
                    continue
                if cell["collision"] != seed["collision"] or cell.get("walkable_tiles") != seed.get("walkable_tiles"):
                    continue
                if cell.get("grass_tile_present") or cell.get("warp_tile_present") or not cell["source_pixels_complete"]:
                    continue
                candidates[bid, q] = cell
            for map_id, definition in imports.table(game, "maps").items():
                if not floor_scope(stem, map_id, definition, ts_name, source_meta["map"]):
                    continue
                used = set(definition["blocks"])
                selected = [(key, cell) for key, cell in candidates.items() if key[0] in used]
                if not selected:
                    held.append({"game": game, "map": map_id, "template": stem, "reason": "No exact reviewed complete floor pixel/behavior identity"})
                scopes.append({"game": game, "map": map_id, "template": stem, "rows": len(selected)})
                for (bid, q), cell in selected:
                    rows.append({"game": game, "style": "gen3", "map": map_id, "tileset": ts_name,
                                 "id": bid, "quadrant": q, "role": "interior_" + stem.split("-", 1)[1] + "_floor",
                                 "status": "reviewed", "sourceHash": cell["grayscale_pixel_sha256"],
                                 "sourceFiles": fingerprints,
                                 "donor": {"game": donor_meta["game"], "tileset": donor_meta["tileset"], "id": mid, "hash": native["pixel_sha256"]},
                                 "nativeContext": {"map": donor_meta["map"], "layoutFileHash": catalog.sha(layout_file.read_bytes())},
                                 "evidence": "Complete plain floor visually reviewed beside the actual native Gen3 room counterpart. Explicit room-function scope; exact source pixels and native behavior checked independently for each cartridge. Furniture, shadows, warp mats and wall fragments are excluded. Native source layout, collision, warps and events remain unchanged."})
    keys = [(r["game"], r["map"], r["tileset"], r["id"], r["quadrant"]) for r in rows]
    assert len(keys) == len(set(keys)), "Overlapping room-function floor scopes"
    report = {"rows": len(rows), "scopes": scopes, "held": held}
    (output / "reviewed-floor-rows.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (output / "reviewed-floor-scope-proof.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    target = WORKSPACE / "TileShift/mappings/interiors.lua" if activate else output / "reviewed-floors.lua"
    write_rows(rows, target)
    print("Reviewed room-floor rows:", len(rows), "maps:", len(scopes), "held variant maps:", len(held), "activated:", activate)
    return rows


def write_rows(rows, target):
    groups, grouped = [], {}
    for row in rows:
        common = {k: v for k, v in row.items() if k not in ("id", "quadrant")}
        key = json.dumps(common, sort_keys=True, separators=(",", ":"))
        if key not in grouped:
            grouped[key] = len(groups)
            groups.append({"common": common, "cells": []})
        groups[grouped[key]]["cells"].append([row["id"], row["quadrant"]])
    body = "-- Reviewed native Gen3 interiors, scoped by actual room function.\nlocal groups={}\nlocal function append(batch)for _,group in ipairs(batch)do groups[#groups+1]=group end end\n"
    for start in range(0, len(groups), 24):
        body += "append((function()return {\n" + "\n".join("  " + lua(group) + "," for group in groups[start:start + 24]) + "\n}end)())\n"
    body += """local rows={}
for _,group in ipairs(groups)do
  for _,cell in ipairs(group.cells)do
    local row={id=cell[1],quadrant=cell[2]}
    for key,value in pairs(group.common)do row[key]=value end
    rows[#rows+1]=row
  end
end
return rows
"""
    expanded = catalog.plain(catalog.LUA.execute(body))
    assert expanded == rows, "Compact interior references changed expanded rows"
    target.write_text(body, encoding="utf-8")


class Imports:
    def __init__(self, cache: Path, catalogs: Path):
        self.cache, self.catalogs = cache, catalogs
        self.tables, self.cells, self.packed, self.sheets = {}, {}, {}, {}
        self.permissions = catalog.LOAD((WORKSPACE / ".tools/engine-0395/src/core/CollPermissions.lua").read_text(), "@native/CollPermissions.lua")

    def table(self, game, name):
        key = game, name
        if key not in self.tables:
            self.tables[key] = catalog.read_lua(self.cache / game / f"data/generated/{name}.lua")
        return self.tables[key]

    def cell_index(self, game):
        if game not in self.cells:
            data = json.loads((self.catalogs / f"{game}.json").read_text())
            if game in ("red", "blue", "yellow", "gold", "silver", "crystal"):
                self.cells[game] = {(r["tileset"], r["block_id"], r["quadrant"]): r for r in data["cells"]}
            else:
                self.cells[game] = {(r["pair"], r["mid"]): r for r in data["cells"]}
        return self.cells[game]

    def gb(self, game, map_id):
        definition = self.table(game, "maps")[map_id]
        name = definition["tileset"]
        ts = self.table(game, "tilesets")[name]
        path = self.cache / game / ts["image"]
        if path not in self.sheets:
            self.sheets[path] = Image.open(path).convert("RGBA")
        sheet = self.sheets[path]
        palettes = preview.palette_set(self.table(game, "palettes"), definition) if game in ("gold", "silver", "crystal") else None
        image = Image.new("RGBA", (definition["width"] * 32, definition["height"] * 32))
        coordinates = defaultdict(list)
        pictures = {}
        for i, block_id in enumerate(definition["blocks"]):
            block = catalog.lua_array(catalog.dict_at(ts["blocks"], block_id + 1))
            for q in range(4):
                key = block_id, q
                if key not in pictures:
                    pictures[key] = preview.native_cell(sheet, ts, block, q, palettes)
                x, y = i % definition["width"] * 2 + q % 2, i // definition["width"] * 2 + q // 2
                coordinates[key].append([x, y])
                image.paste(pictures[key], (x * 16, y * 16))
        rows = []
        for key, coords in sorted(coordinates.items(), key=lambda item: -len(item[1])):
            cell = self.cell_index(game)[name, *key]
            rows.append({"id": key[0], "quadrant": key[1], "count": len(coords), "coordinates": coords,
                         "sourceHash": cell["grayscale_pixel_sha256"], "tiles": cell["tiles"],
                         "collision": cell["collision"], "walkable_tiles": cell.get("walkable_tiles"),
                         "grass": cell.get("grass_tile_present"), "warp": cell.get("warp_tile_present"),
                         "attributes": cell["tile_attributes"]})
        return image, rows, pictures, {"game": game, "map": map_id, "tileset": name}

    def gba(self, game, map_id):
        spec = self.table(game, "gba/native/manifest")["layouts"][map_id]
        layout = decode_layout(self.cache / game / "data/generated/gba/native" / spec["file"])
        raw = (self.cache / game / "data/generated/gba/native" / spec["file"]).read_bytes()
        if raw[:4] != b"SVML":
            raw = zlib.decompress(raw)
        offset = 16 + raw[14] * raw[15] * 2
        collisions = [raw[offset + i * 4 + 2] for i in range(len(layout["mids"]))]
        refs = self.cell_index(game)
        image = Image.new("RGBA", (layout["width"] * 16, layout["height"] * 16))
        coordinates, pictures, layout_collisions = defaultdict(list), {}, defaultdict(set)
        for i, mid in enumerate(layout["mids"]):
            if mid not in pictures:
                cell = refs[spec["pair"], mid]
                ref = {"game": game, "tileset": spec["pair"], "id": mid, "hash": cell["pixel_sha256"]}
                pictures[mid] = preview.native_donor(self.cache, ref, self.packed)
            x, y = i % layout["width"], i // layout["width"]
            coordinates[mid].append([x, y]); image.paste(pictures[mid], (x * 16, y * 16))
            layout_collisions[mid].add(collisions[i])
        rows = []
        for mid, coords in sorted(coordinates.items(), key=lambda item: -len(item[1])):
            cell = refs[spec["pair"], mid]
            rows.append({"id": mid, "count": len(coords), "coordinates": coords,
                         "hash": cell["pixel_sha256"], "layerHashes": cell["layer_sha256"],
                         "behavior": cell["behavior"], "behavior_hint": cell["behavior_hint"],
                         "layout_collisions": sorted(layout_collisions[mid]),
                         "layout_walkable": any(self.permissions.isWalkable(value) for value in layout_collisions[mid]),
                         "category": cell["native_category"]})
        return image, rows, pictures, {"game": game, "map": map_id, "tileset": spec["pair"]}


def contacts(imports, output, pair):
    stem, game, map_id, donor_game, donor_map = pair
    source, source_rows, source_cells, source_meta = imports.gb(game, map_id)
    donor, donor_rows, donor_cells, donor_meta = imports.gba(donor_game, donor_map)
    for label, image in (("source", source), ("donor", donor)):
        image.save(output / f"{stem}-{label}.png")
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
    title = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)
    width = max(source.width * 2 + 40, 400) + max(donor.width * 2 + 40, 400)
    split = max(source.width * 2 + 40, 400)
    canvas = Image.new("RGB", (width, max(source.height, donor.height) * 2 + 98), "#18212b")
    draw = ImageDraw.Draw(canvas)
    draw.text((16, 12), "INTERIOR ROLE REVIEW — source and actual native counterpart", fill="white", font=title)
    draw.text((16, 46), game + " / " + map_id, fill="white", font=font)
    draw.text((split + 16, 46), donor_game + " / " + donor_map, fill="white", font=font)
    canvas.paste(source.resize((source.width * 2, source.height * 2), Image.Resampling.NEAREST), (16, 76))
    canvas.paste(donor.resize((donor.width * 2, donor.height * 2), Image.Resampling.NEAREST), (split + 16, 76))
    canvas.save(output / f"{stem}-map-review.png")
    n = 32
    contact = Image.new("RGB", (1280, 70 + ((n + 3) // 4) * 128), "#18212b")
    draw = ImageDraw.Draw(contact)
    draw.text((16, 12), stem + " — common complete cells; frequency does not establish equivalence", fill="white", font=title)
    for side, (records, pictures) in enumerate(((source_rows, source_cells), (donor_rows, donor_cells))):
        for i, cell in enumerate(records[:n]):
            x, y = side * 640 + i % 4 * 160 + 12, 66 + i // 4 * 128
            key = (cell["id"], cell["quadrant"]) if side == 0 else cell["id"]
            contact.paste(pictures[key].resize((64, 64), Image.Resampling.NEAREST), (x, y))
            label = f"{cell['id']}:{cell['quadrant']}" if side == 0 else f"mid{cell['id']}"
            draw.text((x, y + 67), label + f" ({cell['count']} cells)", fill="white", font=font)
            detail = str(cell["tiles"]) if side == 0 else cell["behavior_hint"] or str(cell["behavior"])
            draw.text((x, y + 86), detail, fill="#c6d1df", font=font)
    contact.save(output / f"{stem}-cell-review.png")
    return {"id": stem, "status": "reference_only", "source": source_meta, "donor": donor_meta,
            "source_cells": source_rows, "donor_cells": donor_rows}


def floor_contacts(imports, output, references):
    canvas = Image.new("RGB", (1200, 72 + len(references) * 104), "#18212b")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
    title = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)
    draw.text((14, 12), "INTERIOR FLOOR CANDIDATES — source walkable cell and native candidates; visual approval required", font=title, fill="white")
    proposals = []
    for index, item in enumerate(references):
        source_meta, donor_meta = item["source"], item["donor"]
        _, _, source_images, _ = imports.gb(source_meta["game"], source_meta["map"])
        _, _, donor_images, _ = imports.gba(donor_meta["game"], donor_meta["map"])
        source = [r for r in item["source_cells"] if r["collision"] == 0 or
                  (r.get("walkable_tiles") and r["walkable_tiles"][2] and not r.get("grass") and not r.get("warp"))]
        native = [r for r in item["donor_cells"] if r["layout_walkable"] and
                  any(high > 0 for low, high in donor_images[r["id"]].convert("RGB").getextrema())]
        y = 68 + index * 104
        draw.text((14, y), item["id"], font=title, fill="white")
        if source:
            r = source[0]
            canvas.paste(source_images[r["id"], r["quadrant"]].resize((64, 64), Image.Resampling.NEAREST), (220, y))
            draw.text((220, y + 66), f"{r['id']}:{r['quadrant']} / {r['count']} cells", font=font, fill="white")
        for i, r in enumerate(native[:4]):
            x = 420 + i * 190
            canvas.paste(donor_images[r["id"]].resize((64, 64), Image.Resampling.NEAREST), (x, y))
            draw.text((x, y + 66), f"mid{r['id']} / {r['count']} cells", font=font, fill="white")
        proposals.append({"id": item["id"], "source": source_meta, "donor": donor_meta,
                          "source_candidates": source[:8], "native_candidates": native[:12], "status": "visual_review_pending"})
    canvas.save(output / "initial-interior-floor-candidates.png")
    (output / "initial-interior-floor-candidates.json").write_text(json.dumps(proposals, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path(os.environ["APPDATA"]) / "pokemon-love2d")
    parser.add_argument("--catalog", type=Path, default=WORKSPACE / ".work/tileshift-catalog")
    parser.add_argument("--output", type=Path, default=WORKSPACE / ".work/tileshift-interior-review")
    parser.add_argument("--pairs", nargs="+", choices=[row[0] for row in PAIRS])
    parser.add_argument("--reviewed-floors", action="store_true", help="Build the explicitly reviewed complete floor references")
    parser.add_argument("--write-reviewed", action="store_true", help="Activate visually reviewed floors after live validation")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    imports = Imports(args.cache, args.catalog)
    results = []
    for pair in PAIRS:
        if args.pairs and pair[0] not in args.pairs:
            continue
        results.append(contacts(imports, args.output, pair))
    (args.output / "interior-references.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    floor_contacts(imports, args.output, results)
    if args.reviewed_floors or args.write_reviewed:
        reviewed_floors(imports, args.output, results, args.write_reviewed)
    print("Private interior map/cell references:", len(results), args.output.resolve())


if __name__ == "__main__":
    main()
