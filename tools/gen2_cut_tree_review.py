"""Privately inventory actual Gen2 Cut trees, independently from Headbutt trees.

Reads native cache data only and writes comparison/provenance under .work.
No production mapping rows are emitted by this tool.
"""
from __future__ import annotations
from collections import defaultdict
import argparse
import json
import os
from pathlib import Path
import sys

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE / ".tools/python"))
from PIL import Image, ImageDraw, ImageFont
import catalog
import preview
import gen2_outdoor_review

CUT = {0x12, 0x1A}
HEADBUTT = {0x15, 0x1D}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-reviewed', action='store_true', help='Validate and append the visually approved actual Cut-tree rows')
    args = parser.parse_args()
    cache = Path(os.environ["APPDATA"]) / "pokemon-love2d"
    output = WORKSPACE / ".work/tileshift-gen2-cut-tree-review"
    output.mkdir(parents=True, exist_ok=True)
    all_records, samples = [], {}
    for game in ("gold", "silver", "crystal"):
        root = cache / game
        maps_path, sets_path = root / "data/generated/maps.lua", root / "data/generated/tilesets.lua"
        maps, sets = catalog.read_lua(maps_path), catalog.read_lua(sets_path)
        pals = catalog.read_lua(root / "data/generated/palettes.lua")
        images, records = {}, {}
        for map_id, definition in maps.items():
            if not isinstance(definition, dict) or "blocks" not in definition:
                continue
            ts_name = definition["tileset"]
            ts = sets[ts_name]
            if ts_name not in images:
                images[ts_name] = Image.open(root / ts["image"]).convert("RGBA")
            sheet = images[ts_name]
            palettes = None
            for pos, block_id in enumerate(catalog.lua_array(definition["blocks"])):
                collision = catalog.lua_array(catalog.dict_at(ts["collision"], block_id + 1))
                if not any(value in CUT for value in collision):
                    continue
                block = catalog.lua_array(catalog.dict_at(ts["blocks"], block_id + 1))
                for q, value in enumerate(collision):
                    if value not in CUT:
                        continue
                    key = ts_name, block_id, q
                    if key not in records:
                        raw = preview.native_cell(sheet, ts, block, q)
                        x, y = q % 2 * 2, q // 2 * 2
                        ids = [block[y * 4 + x], block[y * 4 + x + 1], block[(y + 1) * 4 + x], block[(y + 1) * 4 + x + 1]]
                        records[key] = {"game": game, "tileset": ts_name, "id": block_id, "quadrant": q,
                                        "collision": value, "sourceHash": catalog.sha(raw.tobytes()), "tiles": ids,
                                        "maps": defaultdict(list), "sourceFiles": {"metadata": catalog.sha(sets_path.read_bytes()),
                                            "image": catalog.sha((root / ts["image"]).read_bytes()), "maps": catalog.sha(maps_path.read_bytes())}}
                    coordinates = [pos % definition["width"] * 2 + q % 2, pos // definition["width"] * 2 + q // 2]
                    records[key]["maps"][map_id].append(coordinates)
                    if (game, ts_name) not in samples:
                        palettes = palettes or preview.palette_set(pals, definition)
                        samples[game, ts_name] = (preview.native_cell(sheet, ts, block, q, palettes), map_id, block_id, q)
        for row in records.values():
            row["maps"] = dict(row["maps"])
            row["count"] = sum(map(len, row["maps"].values()))
        all_records.extend(records.values())
    refs = json.loads((WORKSPACE / ".work/tileshift-gen2-outdoor-review/native-cuttable-tree-refs.json").read_text())
    donors = []
    for ref in refs[:2]:
        donor = {"game": ref["game"], "kind": "field_object", "tileset": "ow", "id": ref["id"], "frame": 0,
                 "hash": ref["pixelHash"], "metaHash": ref["metaHash"], "rgbaHash": ref["rgbaHash"]}
        donors.append((donor, preview.native_field_object(cache, donor, {})))
    canvas = Image.new("RGB", (1170, 200 + len(samples) * 145), "#18202c")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 17)
    draw.text((15, 12), "Actual Gen2 Cut-tree equivalence review: collision0x12 / 0x1a only", font=font, fill="white")
    draw.text((15, 40), "Headbutt0x15 /0x1d excluded. All used source aliases below have the same native grayscale silhouette.", fill="#ccd7e5")
    for index, ((game, ts_name), (image, map_id, block_id, q)) in enumerate(samples.items()):
        y = 90 + index * 145
        canvas.paste(image.resize((96, 96), Image.Resampling.NEAREST), (20, y))
        draw.text((130, y), f"{game} / {ts_name}", font=font, fill="white")
        draw.text((130, y + 24), f"{block_id}:{q} in {map_id}", fill="#ccd7e5")
        group = [row for row in all_records if row["game"] == game and row["tileset"] == ts_name]
        draw.text((130, y + 46), f"{len(group)} source aliases; {sum(row['count'] for row in group)} actual tree cells", fill="#ccd7e5")
        for dx, (ref, sprite) in enumerate(donors):
            composed = Image.alpha_composite(Image.new("RGBA", (16, 16), "#73c5a5"), sprite)
            x = 650 + dx * 220
            canvas.paste(composed.resize((96, 96), Image.Resampling.NEAREST), (x, y))
            draw.text((x, y + 101), f"Native {ref['game']} object{ref['id']}", fill="#e5ce9a")
    draw.text((15, canvas.height - 65), "Compare complete native silhouettes, not collision alone. Both target canvases16x16; frame0 is intact with alpha.", fill="#e5ce9a")
    draw.text((15, canvas.height - 42), "Production remains unchanged pending visual review. Future rows must retain sourceCut replacement blocks and grass terrain.", fill="#ccd7e5")
    canvas.save(output / "actual-cut-tree-counterparts.png")
    report = {"status": "visual_review_pending", "cut_collisions": sorted(CUT), "excluded_headbutt_collisions": sorted(HEADBUTT),
              "source_aliases": all_records, "native_object_refs": refs}
    if args.write_reviewed:
        approved = next(ref for ref in refs if ref['game'] == 'firered')
        donor = {"game": "firered", "kind": "field_object", "tileset": "ow", "id": approved['id'], "frame": 0,
                 "hash": approved['pixelHash'], "metaHash": approved['metaHash'], "rgbaHash": approved['rgbaHash']}
        base = {"game": "emerald", "tileset": "general__petalburg", "id": 1,
                "hash": "1c7acc0ebc7c5878e77e1dfbbc2828e1a2745c0ded470f1f0152f67193222ed1"}
        cut_rows = []
        for source in all_records:
            assert source['collision'] in CUT and source['collision'] not in HEADBUTT
            cut_rows.append({"game": source['game'], "style": "gen3", "tileset": source['tileset'],
                             "id": source['id'], "quadrant": source['quadrant'], "sourceHash": source['sourceHash'],
                             "sourceFiles": source['sourceFiles'], "sourceCollision": source['collision'],
                             "sourceMaps": source['maps'], "role": "cuttable_small_tree", "status": "reviewed",
                             "kind": "native_composite", "base": base,
                             "parts": [{"donor": donor, "srcX": 0, "srcY": 0, "w": 16, "h": 16, "x": 0, "y": 0}],
                             "evidence": "Actual Gen2 Cut-tree source, independently checked in each live cartridge: collision0x12 (Cut0x12/0x1a), never Headbutt0x15/0x1d. All used aliases share the complete native two-branched16px sapling silhouette. The actual native FireRed Cut-tree object95 frame0 is the visually approved functional counterpart: full16x16 canvas, no scaling, clipping or repainting. Its transparent pixels compose over fingerprint-checked Emerald1 ground. Native Gen2 Cut eligibility, block replacement, collision refresh and map re-entry restoration remain untouched. All source map occurrences and donor metadata/RGBA/frame hashes are recorded."})
        mod = WORKSPACE / 'TileShift'
        target = mod / 'mappings/gen2_outdoor.lua'
        preserved = [row for row in preview.read_reviewed(target) if row['role'] != 'cuttable_small_tree']
        production = preserved + cut_rows
        validation_args = argparse.Namespace(cache=cache, engine=WORKSPACE / '.tools/engine-0395')
        validation = gen2_outdoor_review.validate_native(production, validation_args, mod)
        target.write_text('-- Reviewed Gen2 outdoor terrain and actual Cut trees.\n'
                          '-- New Bark terrain is map-scoped; Cut aliases have verified pixels, behavior and map use.\n'
                          '-- Native Gen3 imports only; original source gameplay remains unchanged.\nreturn {\n' +
                          '\n'.join('  ' + gen2_outdoor_review.detail_review.lua(row) + ',' for row in production) + '\n}\n', encoding='utf-8')
        report['status'] = 'reviewed'
        report['active_cut_rows'] = len(cut_rows)
        report['validation'] = validation
        print('Activated', len(cut_rows), 'actual Cut-tree aliases; validation', validation)
    (output / "actual-cut-tree-inventory.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    for game in ("gold", "silver", "crystal"):
        rows = [row for row in all_records if row["game"] == game]
        print(game, len(rows), "aliases", sum(row["count"] for row in rows), "physical Cut-tree cells")
        print("Nearby:", [(row["tileset"], row["id"], row["quadrant"], {name: coords for name, coords in row["maps"].items() if name in {"ROUTE_29", "ROUTE_30", "ROUTE_31", "ILEX_FOREST"}}) for row in rows if any(name in {"ROUTE_29", "ROUTE_30", "ROUTE_31", "ILEX_FOREST"} for name in row["maps"])])


if __name__ == "__main__":
    main()
