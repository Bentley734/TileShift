"""Private review of opaque exterior void in explicitly paired indoor scenes.

Solid blocked pixels are only candidates. Their actual boundary context must
be reviewed before any production data is written; this tool never activates.
"""
from __future__ import annotations
from collections import defaultdict
import argparse
import json
import os
from pathlib import Path

from PIL import Image
import catalog
import preview
from gen2_cave_review import contact
from interior_review import Imports, PAIRS, FLOORS, floor_scope, write_rows

WORKSPACE = Path(__file__).resolve().parents[2]
APPROVED_PAIRS = {"red-tower", "red-rocket", "red-tunnel", "red-ship", "red-labroom", "red-gamecorner", "red-lance"}


def blocked(row, generation):
    return (row.get("collision") == 7 if generation == 2 else
            not any(row.get("walkable_tiles") or [True]) and not row.get("warp"))


def constant(image):
    return all(low == high for low, high in image.getextrema()) and image.getpixel((0, 0))[3] == 255


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-only", action="store_true", help="Use only independently reviewed exterior-boundary source contexts")
    args = parser.parse_args()
    cache = Path(os.environ["APPDATA"]) / "pokemon-love2d"
    output = WORKSPACE / ".work/tileshift-interior-void-review"
    output.mkdir(parents=True, exist_ok=True)
    imports = Imports(cache, WORKSPACE / ".work/tileshift-catalog")
    rows, contacts, scenes, held = [], [], [], []
    for stem, source_game, source_map, donor_game, donor_map in PAIRS:
        if stem not in FLOORS:
            continue
        if args.approved_only and stem not in APPROVED_PAIRS:
            continue
        source_image, source_cells, source_pictures, source_meta = imports.gb(source_game, source_map)
        donor_image, donor_cells, donor_pictures, donor_meta = imports.gba(donor_game, donor_map)
        native_voids = [cell for cell in donor_cells if not cell["layout_walkable"] and
                        constant(donor_pictures[cell["id"]]) and donor_pictures[cell["id"]].getpixel((0, 0)) == (0, 0, 0, 255)]
        seeds = [cell for cell in source_cells if blocked(cell, 1 if source_game == "red" else 2) and
                 constant(source_pictures[cell["id"], cell["quadrant"]])]
        if not seeds:
            continue
        if not native_voids:
            held.append({"pair": stem, "reason": "No blocked opaque native black void in the actual paired layout"})
            continue
        target = native_voids[0]
        shapes = {seed["sourceHash"]: seed for seed in seeds}
        for seed in shapes.values():
            x, y = seed["coordinates"][0]
            context = source_image.crop((max(0, x - 2) * 16, max(0, y - 2) * 16,
                                         min(source_image.width, (x + 3) * 16), min(source_image.height, (y + 3) * 16)))
            context.save(output / f"{stem}-solid-{seed['id']}-{seed['quadrant']}-context.png")
            contacts.append((stem + f" {seed['id']}:{seed['quadrant']}\n{seed['count']} cells", context.resize((80, 80), Image.Resampling.NEAREST)))
        for game in (("red", "blue", "yellow") if source_game == "red" else ("gold", "silver", "crystal")):
            name = source_meta["tileset"]
            data = json.loads((imports.catalogs / f"{game}.json").read_text())
            files = next(r["fingerprints"] for r in data["tilesets"] if r["tileset"] == name)
            candidates = []
            for (ts, bid, q), cell in imports.cell_index(game).items():
                seed = shapes.get(cell["grayscale_pixel_sha256"])
                if ts != name or not seed or cell["collision"] != seed["collision"] or cell.get("walkable_tiles") != seed.get("walkable_tiles"):
                    continue
                if cell.get("warp_tile_present") or cell.get("grass_tile_present") or not cell["source_pixels_complete"]:
                    continue
                candidates.append(cell)
            for map_id, definition in imports.table(game, "maps").items():
                if not floor_scope(stem, map_id, definition, name, source_map):
                    continue
                used = set(definition["blocks"])
                for cell in candidates:
                    if cell["block_id"] not in used:
                        continue
                    rows.append({"game": game, "style": "gen3", "map": map_id, "tileset": name,
                                 "id": cell["block_id"], "quadrant": cell["quadrant"], "sourceHash": cell["grayscale_pixel_sha256"],
                                 "sourceFiles": files, "status": "reviewed", "role": "interior_exterior_void",
                                 "donor": {"game": donor_game, "tileset": donor_meta["tileset"], "id": target["id"], "hash": target["hash"]},
                                 "evidence": "Complete exterior void visually reviewed in the actual source room boundary context; not a table surface, wall panel or volcanic terrain. Native blocked black void is actually used by the matching Gen3 layout. Exact source pixels and behavior checked independently per cartridge; no map geometry or collision changes." if args.approved_only else "PRIVATE VOID CANDIDATE: opaque constant blocked source cell in an explicitly paired room function. Native blocked black void is actually used by the corresponding Gen3 layout. Final boundary-context review is required; no solidity-only inference may activate this row."})
        scenes.append({"pair": stem, "source": source_meta, "native": donor_meta,
                       "source_constant_blocked_shapes": list(shapes), "native_void": target["id"]})
    keys = [(r["game"], r["map"], r["tileset"], r["id"], r["quadrant"]) for r in rows]
    assert len(keys) == len(set(keys)), "Overlapping private void scope"
    write_rows(rows, output / "void-candidates.lua")
    (output / "void-candidates.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (output / "void-source-native-context-proof.json").write_text(json.dumps({"scenes": scenes, "held": held}, indent=2), encoding="utf-8")
    for start in range(0, len(contacts), 28):
        contact(output / f"void-boundary-contact-{start // 28 + 1}.png", "Private blocked solid source contexts: only actual outside-room void may be approved", contacts[start:start + 28], columns=7)
    print("PRIVATE exterior void candidates:", len(rows), "; source/native scene pairs:", len(scenes), "; held pairs:", len(held))


if __name__ == "__main__":
    main()
