"""Close the nine remaining native Berry Forest body tiles per cartridge."""

import argparse
import json

from PIL import Image

import catalog
import preview
from gb_theme_animation import frames
from reverse_gen2_kanto_final import DECISIONS, OUT, Final


MAP = "FR_THREE_ISLAND_BERRY_FOREST"
PAIRS = {"firered": "general__rom_082d5004", "leafgreen": "general__rom_082d4fe4"}
MIDS = {176, 177, 194, 548, 549, 550, 641, 642, 644}
COHORT = {641: 8, 644: 13}
POND = {548: 429, 549: 430, 550: 431}


def source_image(review, game, pair, mid):
    cell = review.imp.cell_index(game)[pair, mid]
    donor = dict(game=game, tileset=pair, id=mid, hash=cell["pixel_sha256"])
    return preview.native_donor(review.cache, donor, review.packed)


def flowers(review, game, field):
    pair = "general__rom_082d4af4" if game == "firered" else "general__rom_082d4ad4"
    old = review.current[game, "gen2", pair, 4, None]
    assert old["role"] == "classic_complete_native_flower_patch"
    flower = old["donor"]
    colors = {(222, 255, 222, 255), (247, 82, 49, 255), (255, 156, 197, 255)}
    for frame in frames(review.cache, flower, old["animation"], review.packed):
        assert set(frame.crop((8, 8, 16, 16)).get_flattened_data()) == colors
    parts = [
        dict(donor=flower, srcX=8, srcY=8, w=8, h=8, x=x, y=y, animated=True)
        for y in (0, 8) for x in (0, 8)
    ]
    art = review.composite(field, parts, "classic_gen2_complete_berry_forest_native_flowers")
    art.update(animated=True, animation=old["animation"], animationCategory="flowers")
    return art


def selected_art(review, game, pair, mid):
    field_row = review.current[game, "gen2", pair, 8, None]
    if mid in (176, 177):
        old = review.current[game, "gen2", pair, 135, None]
        art = review.art_of(old)
        note = (
            "The complete original Crystal Route1 south jump lip is used for the "
            "two terminal tiles. The genuine Crystal horizontal stone glyph reaches "
            "the edge of its cell and joins the neighboring selected lip at native "
            "size. The original southward jump behavior and footprint are guarded."
        )
    elif mid in POND:
        old = review.current[game, "gen2", pair, POND[mid], None]
        art = review.art_of(old)
        art["role"] = "classic_gen2_complete_berry_forest_lower_pond_edge"
        note = (
            "Whole lower pond row reviewed against the adjacent native source banks. "
            "Crystal's Route30 pond has water meeting the field along the bottom. "
            "The complete matching side banks continue through the two corners and "
            "the selected animated water continues across the middle. The source "
            "freshwater behavior and whole pond footprint are guarded."
        )
    elif mid == 642:
        art = flowers(review, game, field_row["donor"])
        note = (
            "The full four-flower ground patch uses four complete original Crystal "
            "8px blossoms at native size. Their native pale background joins the "
            "existing forest field. Each bloom uses the selected Crystal flower "
            "animation and retains its source quadrant."
        )
    elif mid in COHORT:
        old = review.current[game, "gen2", pair, COHORT[mid], None]
        art = review.art_of(old)
        note = (
            "Every source occurrence is directly above the center of a complete "
            "48px native Ilex crown. The extra upper slice of the original Gen3 "
            "crown is replaced by the ordinary selected field or tall grass for "
            "this cell. The complete Crystal crown and its actor priority are in "
            "the next cell below, and the original movement and encounter behavior "
            "stay guarded."
        )
    else:
        assert mid == 194
        art = review.art_of(field_row)
        note = (
            "The whole native source is ordinary tufts in the Berry Forest clearing. "
            "The exact neighboring selected Crystal field keeps the clearing's "
            "original walkable context and removes the unmatched grass patch."
        )
    art["overMask"] = "0" * 256
    return art, note


def review_forest(review, decisions):
    staged = {}
    modules = []
    objects = []
    owned = {
        (entry["game"], "gen2", entry["pair"], entry["mid"], None)
        for section in ("native_modules", "native_objects")
        for entry in decisions.get(section, [])
        if entry["feature"] == "berry_forest_final_body"
    }
    empty_over = catalog.sha(bytes(1024))
    for game, pair in PAIRS.items():
        spec, layout = review.layouts[game, MAP]
        assert spec["pair"] == pair
        width = layout["width"]
        pending = set()
        for mid in layout["mids"]:
            key = game, "gen2", pair, mid, None
            if key not in review.current and (key not in review.rows or key in owned):
                pending.add(mid)
        assert pending == MIDS, (game, "Unexpected remaining forest tiles", pending)

        for mid in sorted(MIDS):
            cell = review.imp.cell_index(game)[pair, mid]
            art, evidence = selected_art(review, game, pair, mid)
            record = dict(
                game=game, pair=pair, mid=mid, rgba=cell["pixel_sha256"],
                behavior=cell["behavior"], layers=cell["layer_sha256"],
                feature="berry_forest_final_body", art=art, evidence=evidence,
            )
            if mid in COHORT:
                occurrences = [i for i, value in enumerate(layout["mids"]) if value == mid]
                assert occurrences and all(layout["mids"][i + width] == 665 for i in occurrences)
                complete = review.rows[game, "gen2", pair, 665, None]
                assert "complete_native_forest_tree_48" in complete["role"]
                assert cell["layer_sha256"]["over"] != empty_over
                whole = Image.new("RGBA", (16, 32))
                whole.paste(source_image(review, game, pair, mid), (0, 0))
                whole.paste(source_image(review, game, pair, 665), (0, 16))
                record.update(
                    source_family=[[mid], [665]],
                    whole_source_rgba_sha256=catalog.sha(whole.tobytes()),
                )
                objects.append(record)
            else:
                assert cell["layer_sha256"]["over"] == empty_over
                modules.append(record)
            staged[game, mid] = review.render(dict(
                art, game=game, style="gen2", tileset=pair, id=mid,
                sourceHash=cell["pixel_sha256"], sourceBehavior=cell["behavior"],
            ))
        scene = Image.new("RGBA", (width * 16, layout["height"] * 16))
        rendered = {}
        for index, mid in enumerate(layout["mids"]):
            if mid not in rendered:
                key = game, "gen2", pair, mid, None
                tile = staged.get((game, mid))
                if tile is None:
                    row = review.rows.get(key) or review.current[key]
                    tile = review.render(row)
                rendered[mid] = tile
            scene.paste(rendered[mid], (index % width * 16, index // width * 16))
        scene.save(OUT / f"{game}-berry-forest-complete-body.png")
    return modules, objects


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    options = parser.parse_args()
    review = Final()
    review.stage()
    decisions = json.loads(DECISIONS.read_text())
    modules, objects = review_forest(review, decisions)
    if options.freeze:
        for section, records in (("native_modules", modules), ("native_objects", objects)):
            decisions[section] = [
                entry for entry in decisions.get(section, [])
                if entry["feature"] != "berry_forest_final_body"
            ] + records
        DECISIONS.write_text(json.dumps(decisions, indent=2) + "\n")
    records = modules + objects
    cells = sum(
        sum(use["count"] for use in review.usage[record["game"], record["pair"], record["mid"]])
        for record in records
    )
    print(json.dumps(dict(rows=len(records), cells=cells, frozen=options.freeze)))


if __name__ == "__main__":
    main()
