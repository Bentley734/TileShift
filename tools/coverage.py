"""Audit every Gen1/2 background map against the modules actually loaded by TileShift.

This reports remaining work from the local import catalog. A mapping counts only
when its source fingerprint agrees; live donor/GPU verification is separate.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import re

import catalog
import preview
from review import behavior_key


GAMES = ("red", "blue", "yellow", "gold", "silver", "crystal")


def active_rows(root: Path):
    modules = list(dict.fromkeys(re.findall(r"['\"](mappings/[\w/-]+\.lua)['\"]", (root / "main.lua").read_text())))
    loaded = [name for name in modules if (root / name).is_file()]
    rows = [row for name in loaded for row in preview.read_reviewed(root / name)]
    return loaded, rows


def audit(root: Path, cache: Path, catalogs: Path, games):
    modules, rows = active_rows(root)
    generic, scoped, positioned = {}, {}, {}
    for row in rows:
        if row["style"] != "gen3" or row["status"] != "reviewed":
            continue
        key = (row["game"], row["tileset"], row["id"], row["quadrant"])
        if row.get("x") is not None:
            key = (*key, row["map"], row["x"], row["y"])
            assert key not in positioned, f"Duplicate active source position: {key}"
            positioned[key] = row
        elif row.get("map"):
            key = (*key, row["map"])
            assert key not in scoped, f"Duplicate active source scope: {key}"
            scoped[key] = row
        else:
            assert key not in generic, f"Duplicate active source: {key}"
            generic[key] = row
    reports = []
    for game in games:
        c = json.loads((catalogs / f"{game}.json").read_text())
        cells = {(r["tileset"], r["block_id"], r["quadrant"]): r for r in c["cells"]}
        maps = catalog.read_lua(cache / game / "data/generated/maps.lua")
        map_reports, sets = [], defaultdict(lambda: {"total": 0, "replaced": 0, "groups": {}, "maps": []})
        missing_groups = defaultdict(lambda: {"occurrences": 0, "maps": set(), "source_cells": set()})
        mismatches = set()
        for map_id, definition in sorted(maps.items()):
            ts = definition["tileset"]
            total = len(definition["blocks"]) * 4
            replaced = 0
            remaining = Counter()
            for index, block_id in enumerate(definition["blocks"]):
                for q in range(4):
                    source = cells[(ts, block_id, q)]
                    key = (game, ts, block_id, q)
                    x, y = index % definition["width"] * 2 + q % 2, index // definition["width"] * 2 + q // 2
                    row = positioned.get((*key, map_id, x, y), scoped.get((*key, map_id), generic.get(key)))
                    if row and row["sourceHash"] == source["grayscale_pixel_sha256"]:
                        replaced += 1
                        continue
                    if row:
                        mismatches.add((ts, block_id, q, map_id))
                    group = (ts, source["grayscale_pixel_sha256"], repr(behavior_key(source)))
                    remaining[group] += 1
                    item = missing_groups[group]
                    item["occurrences"] += 1
                    item["maps"].add(map_id)
                    item["source_cells"].add((block_id, q))
            map_reports.append({"map": map_id, "tileset": ts, "total": total,
                                "replaced": replaced, "remaining": total - replaced,
                                "remaining_distinct_visual_behavior_groups": len(remaining)})
            item = sets[ts]
            item["total"] += total
            item["replaced"] += replaced
            item["maps"].append(map_id)
        groups = []
        for (ts, fingerprint, behavior), item in missing_groups.items():
            groups.append({"tileset": ts, "sourceHash": fingerprint, "behavior": behavior,
                           "occurrences": item["occurrences"], "maps": sorted(item["maps"]),
                           "source_cells": [list(pair) for pair in sorted(item["source_cells"])]})
        for ts, item in sets.items():
            item.pop("groups")
            item["remaining"] = item["total"] - item["replaced"]
            item["remaining_distinct_visual_behavior_groups"] = sum(g["tileset"] == ts for g in groups)
        total, replaced = sum(m["total"] for m in map_reports), sum(m["replaced"] for m in map_reports)
        reports.append({"game": game, "total": total, "replaced": replaced,
                        "remaining": total - replaced,
                        "fully_replaced_maps": sum(m["remaining"] == 0 for m in map_reports),
                        "map_count": len(map_reports), "source_mismatches": sorted(mismatches),
                        "tilesets": dict(sorted(sets.items(), key=lambda pair: -pair[1]["remaining"])),
                        "maps": map_reports, "remaining_groups": sorted(groups, key=lambda g: -g["occurrences"])})
    return {"kind": "source_catalog_coverage", "limits": "Catalog source identity audit; not a donor or GPU validation.",
            "active_modules": modules, "reviewed_mapping_rows": len(rows), "games": reports}


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path(os.environ["APPDATA"]) / "pokemon-love2d")
    parser.add_argument("--catalog", type=Path, default=root.parent / ".work/tileshift-catalog")
    parser.add_argument("--output", type=Path, default=root.parent / ".work/tileshift-coverage.json")
    parser.add_argument("--games", choices=GAMES, nargs="+", default=GAMES)
    args = parser.parse_args()
    report = audit(root, args.cache, args.catalog, args.games)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Active reviewed mappings:", report["reviewed_mapping_rows"])
    for game in report["games"]:
        print(f"{game['game']}: {game['replaced']}/{game['total']} cells; "
              f"{game['fully_replaced_maps']}/{game['map_count']} complete maps; {game['remaining']} remaining")
    print("Coverage ledger:", args.output.resolve())


if __name__ == "__main__":
    main()
