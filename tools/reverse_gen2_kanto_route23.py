"""Review the Route 23 checkpoint masonry and the matching league entry arch."""

import argparse
import json

from PIL import Image

import catalog
import preview
from classic_geometry_review import art as classic_art
from reverse_gen2_kanto_final import DECISIONS, OUT, Final


ROUTE = "FR_ROUTE_23"
LEAGUE = "FR_INDIGO_PLATEAU_EXTERIOR"
ARCHITECTURE = (
    644, 645, 646, 647, 652, 653, 654, 680, 681, 682, 683, 684, 685,
    688, 689, 690, 691, 692, 693, 696, 697, 698, 699, 700, 701, 702, 703,
    733, 734, 735,
)
PAVEMENT = (641, 642, 643, 649, 651, 657, 658, 659)

DARK = (58, 58, 58)
SHADE = (107, 107, 107)
STONE = (156, 156, 156)
LIGHT = (222, 255, 222)
PALETTE = (DARK, SHADE, STONE, LIGHT)
FIELD_COLORS = {
    (25, 165, 107), (66, 181, 140), (115, 206, 165),
    (140, 222, 189), (165, 230, 197),
}
WATERSIDE = (701, 702, 703)
LOW_BANK_COLORS = {(148, 107, 107), (189, 148, 140), (222, 197, 165)}
COLORS = {
    (0, 0, 0): DARK,
    (82, 82, 107): DARK,
    (123, 123, 132): SHADE,
    (148, 148, 140): SHADE,
    (181, 181, 165): STONE,
    (206, 206, 214): STONE,
    (214, 214, 222): LIGHT,
    (222, 222, 230): LIGHT,
    (255, 255, 255): LIGHT,
    **{rgb: SHADE for rgb in FIELD_COLORS | LOW_BANK_COLORS},
}


def source_image(review, game, pair, mid):
    cell = review.imp.cell_index(game)[pair, mid]
    ref = dict(game=game, tileset=pair, id=mid, hash=cell["pixel_sha256"])
    return preview.native_donor(review.cache, ref, review.packed)


def field_masks(review, game, pair, mid):
    mids, palette, planes = review.packed[game, pair]
    slot = mids.index(mid)
    colors = FIELD_COLORS | LOW_BANK_COLORS if mid in WATERSIDE else FIELD_COLORS
    masks = {}
    for name, blob in planes.items():
        image = catalog.rgba_native(
            blob[slot * 256:(slot + 1) * 256], palette, name != "under"
        )
        mask = "".join(
            "1" if pixel[3] and pixel[:3] in colors else "0"
            for pixel in image.get_flattened_data()
        )
        if "1" in mask:
            masks[name] = mask
    return masks


def stage_review(review, decisions):
    geometry = []
    modules = []
    replacements = {}
    owned = {
        (entry["game"], "gen2", entry["pair"], entry["mid"], None)
        for entry in decisions.get("geometry", []) + decisions.get("native_modules", [])
        if entry.get("feature", "").startswith("kanto_checkpoint_")
    }
    empty_over = catalog.sha(bytes(1024))
    for game in review.games:
        pair = review.layouts[game, ROUTE][0]["pair"]
        assert review.layouts[game, LEAGUE][0]["pair"] == pair
        field_key = game, "gen2", pair, 8, None
        pavement_key = game, "gen2", pair, 650, None
        field = (review.rows.get(field_key) or review.current[field_key])["donor"]
        pavement = (review.rows.get(pavement_key) or review.current[pavement_key])["donor"]
        for mid in ARCHITECTURE + PAVEMENT:
            key = game, "gen2", pair, mid, None
            assert key not in review.current and (key not in review.rows or key in owned)
            usages = [u for u in review.usage[game, pair, mid] if u["count"]]
            assert usages and all(use["map"] in (ROUTE, LEAGUE) for use in usages)
            source_image(review, game, pair, mid)
            cell = review.imp.cell_index(game)[pair, mid]
            record = dict(
                game=game, pair=pair, mid=mid, rgba=cell["pixel_sha256"],
                behavior=cell["behavior"], layers=cell["layer_sha256"],
            )
            if mid in PAVEMENT:
                assert cell["layer_sha256"]["over"] == empty_over
                feature = "kanto_checkpoint_pavement"
                art = review.native(pavement, "classic_gen2_" + feature)
                art["overMask"] = "0" * 256
                note = (
                    "The full ordinary path and its grass joins use the complete "
                    "same native Crystal paving as the neighboring source650 cells. "
                    "The selected pale ground follows the source path positions and "
                    "keeps their original movement guards."
                )
                modules.append(dict(record, feature=feature, art=art, evidence=note))
            else:
                feature = "kanto_checkpoint_masonry"
                masks = field_masks(review, game, pair, mid)
                ground = dict(donor=field, masks=masks) if masks else None
                art = classic_art(review, game, pair, mid, feature, PALETTE, COLORS, ground=ground)
                note = (
                    "The linked Route23 badge checkpoint walls, stone shafts, open "
                    "arches, braces and the matching Indigo Plateau gate are explicit "
                    "regional features. The original Crystal checkpoint has a different "
                    "building plan. The four selected Crystal stone shades retain each "
                    "complete source shape and priority coordinate. The ground inside "
                    "open arches and at the lower waterside joins matches the already "
                    "selected native Crystal field. The source gate positions and movement "
                    "keep their full native guards."
                )
                geometry.append(dict(record, feature=feature, art=art, evidence=note))
            replacements[key] = review.render(dict(
                art, game=game, style="gen2", tileset=pair, id=mid,
                sourceHash=cell["pixel_sha256"], sourceBehavior=cell["behavior"],
            ))
    return geometry, modules, replacements


def write_previews(review, replacements):
    for game in review.games:
        for name in (ROUTE, LEAGUE):
            spec, layout = review.layouts[game, name]
            pair = spec["pair"]
            width, height = layout["width"], layout["height"]
            scene = Image.new("RGBA", (width * 16, height * 16))
            rendered = {}
            for index, mid in enumerate(layout["mids"]):
                key = game, "gen2", pair, mid, None
                if mid not in rendered:
                    image = replacements.get(key)
                    if image is None:
                        row = review.rows.get(key) or review.current.get(key)
                        image = review.render(row) if row else source_image(review, game, pair, mid)
                    rendered[mid] = image
                scene.paste(rendered[mid], (index % width * 16, index // width * 16))
            scene.save(OUT / f"{game}-{name}-checkpoint-complete.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    options = parser.parse_args()
    review = Final()
    review.stage()
    decisions = json.loads(DECISIONS.read_text())
    geometry, modules, replacements = stage_review(review, decisions)
    write_previews(review, replacements)
    if options.freeze:
        for section, records in (("geometry", geometry), ("native_modules", modules)):
            decisions[section] = [
                entry for entry in decisions.get(section, [])
                if not entry.get("feature", "").startswith("kanto_checkpoint_")
            ] + records
        DECISIONS.write_text(json.dumps(decisions, indent=2) + "\n")
    cells = sum(
        sum(use["count"] for use in review.usage[entry["game"], entry["pair"], entry["mid"]])
        for entry in geometry + modules
    )
    print(json.dumps(dict(rows=len(replacements), cells=cells, frozen=options.freeze)))


if __name__ == "__main__":
    main()
