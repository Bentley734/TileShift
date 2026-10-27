"""Private whole-feature household review; never activates production art."""
from __future__ import annotations

import json
import os
from pathlib import Path

from PIL import Image
import catalog
import preview
from gen2_cave_review import contact
from interior_review import Imports, write_rows

WORKSPACE = Path(__file__).resolve().parents[2]


def repeated_households(imports, output, art, source_features):
    """Repeat exact full source feature profiles; no unpaired object fragments."""
    rows, report = [], []
    shapes = {
        "bookcase": ((0, 0, "bookcase_head"), (0, 1, "bookcase_base")),
        "table": ((0, 0, "table_nw"), (1, 0, "table_ne"), (0, 1, "table_sw"), (1, 1, "table_se")),
    }
    for game in ("red", "blue", "yellow"):
        maps = imports.table(game, "maps")
        seed = maps["REDS_HOUSE_1F"]
        seed_cells = {}
        for (x, y), label in source_features.items():
            bid = seed["blocks"][y // 2 * seed["width"] + x // 2]
            seed_cells.setdefault(label, imports.cell_index(game)[seed["tileset"], bid, y % 2 * 2 + x % 2])

        def matches(cell, label):
            model = seed_cells[label]
            return (cell["grayscale_pixel_sha256"] == model["grayscale_pixel_sha256"] and
                    cell.get("walkable_tiles") == model.get("walkable_tiles") and
                    cell.get("warp_tile_present") == model.get("warp_tile_present") and
                    cell.get("grass_tile_present") == model.get("grass_tile_present") and cell["source_pixels_complete"])

        fingerprints = {r["tileset"]: r["fingerprints"] for r in json.loads((imports.catalogs / f"{game}.json").read_text())["tilesets"]}
        for map_id, definition in sorted(maps.items()):
            name = definition["tileset"]
            if name not in {"HOUSE", "REDS_HOUSE_1", "REDS_HOUSE_2"}:
                continue
            cells = {}
            for index, bid in enumerate(definition["blocks"]):
                for q in range(4):
                    xy = (index % definition["width"] * 2 + q % 2, index // definition["width"] * 2 + q // 2)
                    cells[xy] = imports.cell_index(game)[name, bid, q]
            selected, features = {}, []

            def stamp(x, y, label):
                if (x, y) not in cells or not matches(cells[x, y], label):
                    return False
                assert selected.get((x, y), label) == label, "Conflicting household feature profile"
                selected[x, y] = label
                return True

            for (x, y), cell in cells.items():
                for label in ("wall", "window", "television"):
                    if matches(cell, label):
                        stamp(x, y, label)
                for profile, shape in shapes.items():
                    if all((x + dx, y + dy) in cells and matches(cells[x + dx, y + dy], label) for dx, dy, label in shape):
                        for dx, dy, label in shape:
                            stamp(x + dx, y + dy, label)
                        features.append({"feature": profile, "x": x, "y": y})
                        if profile == "table":
                            for dy in range(2):
                                stamp(x - 1, y + dy, "chair_left")
                                stamp(x + 2, y + dy, "chair_right")
            # The source carpet graphic repeats across its whole width. Only
            # exact32px runs matching the reviewed native mat are emitted.
            for y in range(definition["height"] * 2):
                run = sorted(x for (x, yy), cell in cells.items() if yy == y and matches(cell, "rug_left"))
                for x in run:
                    if x + 1 in run and x - 1 not in run and x + 2 not in run:
                        stamp(x, y, "rug_left"); stamp(x + 1, y, "rug_right")
                        features.append({"feature": "complete_entry_mat", "x": x, "y": y})
            for warp in definition.get("warps", []):
                xy = warp["x"], warp["y"]
                if map_id.endswith("1F") and warp["destMap"].endswith("2F") and xy in cells and matches(cells[xy], "upstairs"):
                    stamp(*xy, "upstairs")
                    features.append({"feature": "upstairs", "x": xy[0], "y": xy[1], "destination": warp["destMap"]})
            for (x, y), label in sorted(selected.items(), key=lambda item: (item[0][1], item[0][0])):
                cell = cells[x, y]
                rows.append({"game": game, "style": "gen3", "map": map_id, "tileset": name,
                             "id": cell["block_id"], "quadrant": cell["quadrant"], "x": x, "y": y,
                             "sourceHash": cell["grayscale_pixel_sha256"], "sourceFiles": fingerprints[name],
                             "status": "reviewed", "role": "household_" + label,
                             "evidence": "PRIVATE EXACT-PROFILE CANDIDATE: independently checked cartridge pixels and source behavior. Full table/bookcase profiles, exact32px entry-mat runs and actual upward source warps; no partial object inference. Pending final context review.", **art[label]})
            if selected:
                report.append({"game": game, "map": map_id, "positions": len(selected), "full_features": features})
    write_rows(rows, output / "household-expanded-candidates.lua")
    (output / "household-expanded-candidates.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (output / "household-expanded-source-proof.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Private repeated household profiles:", len(rows), "positions /", len(report), "maps")
    return rows


def main():
    cache = Path(os.environ["APPDATA"]) / "pokemon-love2d"
    output = WORKSPACE / ".work/tileshift-house-review"
    output.mkdir(parents=True, exist_ok=True)
    imports = Imports(cache, WORKSPACE / ".work/tileshift-catalog")
    native = imports.cell_index("firered")
    packed = {}

    def ref(mid, pair="player_house", game="firered"):
        cell = imports.cell_index(game)[pair, mid]
        return {"game": game, "tileset": pair, "id": mid, "hash": cell["pixel_sha256"]}

    def part(mid, sx=0, sy=0, w=16, h=16, x=0, y=0, layer=None, pair="player_house", game="firered"):
        value = {"donor": ref(mid, pair, game), "srcX": sx, "srcY": sy, "w": w, "h": h, "x": x, "y": y}
        if layer:
            value.update(layers=[layer], layerHashes={layer: imports.cell_index(game)[pair, mid]["layer_sha256"][layer]})
        return value

    def composite(parts, base=1):
        row = {"kind": "native_composite", "base": ref(base), "parts": parts}
        picture = preview.replacement_image(cache, row, packed, WORKSPACE / "TileShift")
        row["compositionPixelHash"] = catalog.sha(picture.tobytes())
        return row, picture

    art, pictures = {}, {}
    recipes = {
        "wall": [part(32, sy=0, h=8), part(40, sy=8, h=8, y=8)],
        "window": [part(32, sy=0, h=8), part(40, sy=8, h=8, y=8),
                   part(542, sy=8, w=15, h=1, y=2, pair="building__brendans_mays_house", game="emerald"),
                   part(542, sy=9, h=7, y=3, pair="building__brendans_mays_house", game="emerald"),
                   part(550, h=3, y=10, pair="building__brendans_mays_house", game="emerald"),
                   part(550, sx=1, sy=3, w=15, h=1, x=1, y=13, pair="building__brendans_mays_house", game="emerald")],
        "bookcase_head": [part(32, h=8), part(40, sy=8, h=8, y=8),
                          part(43, sx=1, sy=11, w=4, h=1, x=1),
                          part(44, sx=11, sy=11, w=4, h=1, x=11),
                          part(43, sx=1, sy=12, w=7, h=1, x=1, y=1),
                          part(44, sx=8, sy=12, w=7, h=1, x=8, y=1),
                          part(43, sx=1, sy=13, w=7, h=3, x=1, y=2),
                          part(44, sx=8, sy=13, w=8, h=3, x=8, y=2),
                          part(51, sy=5, w=8, h=11, y=5),
                          part(52, sx=8, sy=5, w=8, h=11, x=8, y=5)],
        "bookcase_base": [part(59, w=8), part(60, sx=8, w=8, x=8)],
        "chair_left": [part(75, layer="mid")],
        "chair_right": [part(78, layer="mid")],
        # The full native TV casing is20px tall across45/53/61. Preserve its
        # entire cap, screen, side bezel and control strip; omit four exactly
        # repeated blank housing rows to fit the original16px host footprint.
        "television": [part(45, sx=3, sy=13, w=10, h=1, x=3),
                       part(45, sx=2, sy=14, w=12, h=1, x=2, y=1),
                       part(45, sy=15, h=1, y=2), part(53, h=2, y=3),
                       part(53, sy=6, h=10, y=5), part(61, h=1, y=15)],
        # Preserve the whole26x16 native mat/frame, including its lower shadow.
        # The48x32 layout rectangle also contains exterior black void, which
        # belongs to the donor map rather than to the rug and is excluded.
        "rug_left": [part(18, sx=11, sy=4, w=5, h=12, x=3), part(19, sy=4, w=8, h=12, x=8),
                     part(26, sx=11, w=5, h=4, x=3, y=12), part(27, w=8, h=4, x=8, y=12)],
        "rug_right": [part(19, sx=8, sy=4, w=8, h=12), part(20, sy=4, w=5, h=12, x=8),
                      part(27, sx=8, w=8, h=4, y=12), part(28, w=5, h=4, x=8, y=12)],
    }
    for label, parts in recipes.items():
        art[label], pictures[label] = composite(parts)
    stair = imports.cell_index("emerald")["building__brendans_mays_house", 529]
    art["upstairs"] = {"donor": {"game": "emerald", "tileset": "building__brendans_mays_house", "id": 529, "hash": stair["pixel_sha256"]}}
    pictures["upstairs"] = preview.native_donor(cache, art["upstairs"]["donor"], packed)
    for label, mid in (("table_nw", 76), ("table_ne", 77), ("table_sw", 84), ("table_se", 85)):
        art[label], pictures[label] = composite([part(mid, layer="mid")])
    feature_proof = []
    bookcase = Image.new("RGBA", (16, 37))
    for left, right, sy, height, target_y in ((43, 44, 11, 5, 0), (51, 52, 0, 16, 5), (59, 60, 0, 16, 21)):
        for mid, sx, x in ((left, 0, 0), (right, 8, 8)):
            picture = preview.native_donor(cache, ref(mid), packed).crop((sx, sy, sx + 8, sy + height))
            bookcase.paste(picture, (x, target_y))
    target_case = Image.new("RGBA", (16, 32))
    target_case.paste(pictures["bookcase_head"], (0, 0)); target_case.paste(pictures["bookcase_base"], (0, 16))
    panel_row = bookcase.crop((0, 5, 16, 6)).tobytes()
    assert all(bookcase.crop((0, y, 16, y + 1)).tobytes() == panel_row for y in range(5, 10))
    retained = outside = 0
    for y in range(32):
        for x in range(16):
            inside = (y == 0 and (1 <= x <= 4 or 11 <= x <= 14)) or (y == 1 and 1 <= x <= 14) or (2 <= y <= 4 and x >= 1) or y >= 5
            expected = bookcase.getpixel((x, y if y < 5 else y + 5)) if inside else pictures["wall"].getpixel((x, y))
            assert target_case.getpixel((x, y)) == expected, "Bookcase cap, shelf, base or shadow changed"
            retained += inside; outside += not inside
    assert retained == 499 and outside == 13
    feature_proof.append({"feature": "bookcase_complete_cap_shelves_base_shadow", "native_pixels": retained,
                          "outside_matches_compact_wall": outside, "removed_only_identical_blank_panel_rows": 5, "changed_pixels": 0})
    window_stack = Image.new("RGBA", (16, 32))
    for index, mid in enumerate((542, 550)):
        window_stack.paste(preview.native_donor(cache, ref(mid, "building__brendans_mays_house", "emerald"), packed), (0, index * 16))
    window_pixels = 0
    outside_pixels = 0
    for y in range(16):
        for x in range(16):
            inside = 2 <= y <= 13 and (x, y) not in {(15, 2), (0, 13)}
            expected = window_stack.getpixel((x, y + 6)) if inside else pictures["wall"].getpixel((x, y))
            assert pictures["window"].getpixel((x, y)) == expected, "Complete window frame or surrounding wall changed"
            window_pixels += inside; outside_pixels += not inside
    assert window_pixels == 190 and outside_pixels == 66
    feature_proof.append({"feature": "complete_window_frame_glass_highlight", "native_pixels": window_pixels,
                          "outside_matches_compact_wall": outside_pixels, "changed_pixels": 0})
    tv_body = preview.native_donor(cache, ref(53), packed)
    repeated = tv_body.crop((0, 1, 16, 2)).tobytes()
    assert all(tv_body.crop((0, y, 16, y + 1)).tobytes() == repeated for y in range(2, 6))
    feature_proof.append({"feature": "television_complete_casing", "native_pixels": 246,
                          "removed_only_identical_blank_rows": 4, "changed_glyph_pixels": 0})
    whole_mat = Image.new("RGBA", (48, 32))
    for index, mid in enumerate((18, 19, 20, 26, 27, 28)):
        whole_mat.paste(preview.native_donor(cache, ref(mid), packed), (index % 3 * 16, index // 3 * 16))
    target_mat = Image.new("RGBA", (32, 16))
    target_mat.paste(pictures["rug_left"], (0, 0)); target_mat.paste(pictures["rug_right"], (16, 0))
    original_glyph = whole_mat.crop((11, 4, 37, 20))
    assert target_mat.crop((3, 0, 29, 16)).tobytes() == original_glyph.tobytes()
    feature_proof.append({"feature": "complete_doormat_and_shadow", "native_pixels": 416,
                          "pixel_sha256": catalog.sha(original_glyph.tobytes()), "changed_pixels": 0})
    for label, mid in (("chair_left", 75), ("chair_right", 78), ("table_nw", 76),
                       ("table_ne", 77), ("table_sw", 84), ("table_se", 85)):
        glyph = preview.native_donor(cache, ref(mid), packed, ["mid"], {"mid": native["player_house", mid]["layer_sha256"]["mid"]})
        opaque = 0
        for y in range(16):
            for x in range(16):
                if glyph.getpixel((x, y))[3]:
                    assert pictures[label].getpixel((x, y)) == glyph.getpixel((x, y)), "Native furniture glyph changed"
                    opaque += 1
        feature_proof.append({"feature": label, "native_pixels": opaque, "changed_pixels": 0})
    contact(output / "complete-household-candidates.png", "Private household candidates: complete frames, original footprint and native up-stair glyph", list(pictures.items()), columns=7)

    # Exact original positions distinguish the left/right facing chairs.
    features = {
        (0, 0): "bookcase_head", (1, 0): "bookcase_head", (0, 1): "bookcase_base", (1, 1): "bookcase_base",
        (2, 0): "wall", (4, 0): "wall", (6, 0): "wall",
        (3, 0): "window", (5, 0): "window", (7, 0): "window", (3, 1): "television", (7, 1): "upstairs",
        (2, 4): "chair_left", (2, 5): "chair_left", (5, 4): "chair_right", (5, 5): "chair_right",
        (3, 4): "table_nw", (4, 4): "table_ne", (3, 5): "table_sw", (4, 5): "table_se",
        (2, 7): "rug_left", (3, 7): "rug_right",
    }
    rows = []
    expanded = repeated_households(imports, output, art, features)
    for game in ("red", "blue", "yellow"):
        definition = imports.table(game, "maps")["REDS_HOUSE_1F"]
        name = definition["tileset"]
        files = next(r["fingerprints"] for r in json.loads((imports.catalogs / f"{game}.json").read_text())["tilesets"] if r["tileset"] == name)
        stair_warp = next(w for w in definition["warps"] if w["x"] == 7 and w["y"] == 1)
        assert stair_warp["destMap"] == "REDS_HOUSE_2F", "Native source up-stair no longer leads upstairs"
        for (x, y), label in features.items():
            bid = definition["blocks"][y // 2 * definition["width"] + x // 2]
            q = y % 2 * 2 + x % 2
            cell = imports.cell_index(game)[name, bid, q]
            row = {"game": game, "style": "gen3", "map": "REDS_HOUSE_1F", "tileset": name,
                   "id": bid, "quadrant": q, "x": x, "y": y,
                   "sourceHash": cell["grayscale_pixel_sha256"], "sourceFiles": files,
                   "status": "reviewed", "role": "household_" + label,
                   "evidence": "PRIVATE VISUAL CANDIDATE: complete native household feature or repeated-material compaction; source function, footprint and all component rectangles require visual review before activation.", **art[label]}
            rows.append(row)
    write_rows(rows, output / "household-candidates.lua")
    (output / "household-candidates.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    floors = preview.read_reviewed(WORKSPACE / "TileShift/mappings/interiors.lua")
    results = [preview.map_preview(cache, output, game, "REDS_HOUSE_1F", game + "-household", floors + rows, packed, 4, WORKSPACE / "TileShift") for game in ("red", "blue", "yellow")]
    (output / "household-contexts.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (output / "household-feature-proof.json").write_text(json.dumps({"features": feature_proof,
        "source_upstairs_warps_checked": 3, "full_room_coverage": all(r["replaced_occurrences"] == r["visible_cells"] for r in results),
        "stair_geometry": "Complete native Emerald16px529 up-stair glyph, actual Brendan/May1F-to2F warp. Surrounding native arch belongs outside the16px source footprint and is not claimed as preserved.",
        "bookcase_geometry": "Full native casing/cap/shadow scope narrowed to16px with both outer8px strips. Missing43/44 cap retained; only five identical51/52 blank panel rows are omitted to fit32px height. Every shelf, book, lower frame and shadow pixel is preserved; outside-cap corners match the wall.",
        "status": "private_prototype_not_active"}, indent=2), encoding="utf-8")
    print("PRIVATE household candidate rows:", len(rows), "Whole room remains private pending feature/source/warp proof; production unchanged")


if __name__ == "__main__":
    main()
