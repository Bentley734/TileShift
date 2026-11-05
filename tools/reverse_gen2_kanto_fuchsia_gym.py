"""Complete the Fuchsia Gym maze floor, room fixtures and platform."""

import argparse
import json
from collections import deque

from PIL import Image

import catalog
import preview
from classic_geometry_review import art as classic_art
from reverse_gen2_kanto_final import DECISIONS, OUT, Final, previous


MAP = "FR_FUCHSIA_CITY_GYM"
CRYSTAL_MAP = "FUCHSIA_GYM"
PLATFORM = (643, 644, 645, 651, 652, 653, 659, 660, 661)
BACK_WALL = (646, 647, 654, 655, 662, 664, 665, 671, 672, 673)
MAT = (656, 657, 658, 666, 667, 668)
MAZE = (642, 650)
STATUE = (648, 663)
FEATURE = "fuchsia_gym_complete_body"

CREAM = (247, 230, 214)
DARK = (58, 58, 58)
GRAY = (107, 107, 107)
GOLD = (173, 140, 58)
BLUE = (74, 74, 255)
LIGHT_BLUE = (123, 132, 255)
FLOOR_COLORS = {
    (173, 132, 115), (181, 140, 123), (197, 156, 148), (206, 165, 156),
    (239, 181, 165), (255, 222, 197),
}
PLATFORM_COLORS = {
    (82, 82, 107): DARK,
    (132, 132, 132): GRAY,
    (181, 181, 165): CREAM,
    (197, 156, 148): GRAY,
    (206, 165, 156): GRAY,
    (239, 181, 165): CREAM,
    (255, 197, 99): GOLD,
    (255, 222, 197): CREAM,
}
WALL_COLORS = {
    (41, 107, 82): DARK,
    (58, 132, 115): BLUE,
    (82, 82, 107): DARK,
    (115, 173, 222): LIGHT_BLUE,
    (123, 123, 123): BLUE,
    (156, 132, 58): BLUE,
    (156, 206, 247): CREAM,
    (173, 132, 115): BLUE,
    (181, 140, 123): LIGHT_BLUE,
    (181, 181, 165): LIGHT_BLUE,
    (197, 156, 148): LIGHT_BLUE,
    (214, 197, 107): LIGHT_BLUE,
    (222, 230, 255): CREAM,
    (239, 181, 165): CREAM,
    (247, 239, 148): CREAM,
    (255, 255, 255): CREAM,
}


def source_image(review, game, pair, mid):
    cell = review.imp.cell_index(game)[pair, mid]
    donor = dict(game=game, tileset=pair, id=mid, hash=cell["pixel_sha256"])
    return preview.native_donor(review.cache, donor, review.packed)


def exact_floor_masks(review, game, pair, mid):
    mids, palette, planes = review.packed[game, pair]
    slot = mids.index(mid)
    masks = {}
    for name, blob in planes.items():
        pixels = catalog.rgba_native(
            blob[slot * 256:(slot + 1) * 256], palette, name != "under"
        )
        mask = "".join(
            "1" if pixel[3] and pixel[:3] in FLOOR_COLORS else "0"
            for pixel in pixels.get_flattened_data()
        )
        if "1" in mask:
            masks[name] = mask
    return masks


def mat_art(review, floor, mid):
    index = MAT.index(mid)
    cell_x, cell_y = index % 3 * 16, index // 3 * 16
    parts = []
    # The complete 32x16 native rug fits around the source center warp.
    for column in range(2):
        rug_x, rug_y = 8 + column * 16, 4
        left = max(cell_x, rug_x)
        right = min(cell_x + 16, rug_x + 16)
        top = max(cell_y, rug_y)
        bottom = min(cell_y + 16, rug_y + 16)
        if left < right and top < bottom:
            donor = review.gb_at("crystal", CRYSTAL_MAP, 4 + column, 17)
            parts.append(dict(
                donor=donor, srcX=left - rug_x, srcY=top - rug_y,
                x=left - cell_x, y=top - cell_y, w=right - left, h=bottom - top,
            ))
    base = floor if cell_y == 0 else review.black_ref()
    art = review.composite(base, parts, "classic_gen2_complete_fuchsia_entry_mat")
    art["overMask"] = "0" * 256
    return art


def statue_art(review, floor, mid):
    donor = review.gb_at("crystal", CRYSTAL_MAP, 3, 14 + STATUE.index(mid))
    art = review.native(donor, "classic_gen2_complete_fuchsia_statue")
    if mid == 663:
        art["overMask"] = "0" * 256
        return art

    sprite = review.gb_image(donor)
    field = review.gb_image(floor)
    outside = set()
    to_visit = deque()
    for y in range(16):
        for x in range(16):
            if (x in (0, 15) or y in (0, 15)) and sprite.getpixel((x, y)) == field.getpixel((x, y)):
                outside.add((x, y))
                to_visit.append((x, y))
    while to_visit:
        x, y = to_visit.popleft()
        for point in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            px, py = point
            if (
                0 <= px < 16 and 0 <= py < 16 and point not in outside
                and sprite.getpixel(point) == field.getpixel(point)
            ):
                outside.add(point)
                to_visit.append(point)
    assert 0 < len(outside) < 128 and (8, 8) not in outside
    art["overMask"] = "".join(
        "0" if (index % 16, index // 16) in outside else "1" for index in range(256)
    )
    return art


def record(review, game, pair, mid, art, evidence, feature=FEATURE):
    cell = review.imp.cell_index(game)[pair, mid]
    result = dict(
        game=game, pair=pair, mid=mid, rgba=cell["pixel_sha256"],
        behavior=cell["behavior"], layers=cell["layer_sha256"],
        feature=feature, art=art, evidence=evidence,
    )
    old = review.current.get((game, "gen2", pair, mid, None))
    if old:
        result["replace_prior_row_sha256"] = catalog.sha(previous.stable(old).encode())
    return result


def review_gym(review):
    geometry = []
    native_modules = []
    native_objects = []
    replaced_aliases = set()
    for game in review.games:
        spec, layout = review.layouts[game, MAP]
        pair = spec["pair"]
        assert all(
            name == MAP for (host, name), (other, _) in review.layouts.items()
            if host == game and other["pair"] == pair
        )
        floor = review.current[game, "gen2", pair, 641, None]["donor"]
        invisible = review.gb_at("crystal", CRYSTAL_MAP, 4, 3)
        native_collision = review.imp.cell_index("crystal")[
            invisible["tileset"], invisible["id"], invisible["quadrant"]
        ]["collision"]
        assert native_collision == 7
        replacement = {}
        for mid in MAZE + MAT + PLATFORM + BACK_WALL + STATUE:
            source_image(review, game, pair, mid)
            key = game, "gen2", pair, mid, None
            if mid in MAZE:
                art = review.native(invisible, "classic_gen2_fuchsia_invisible_wall_floor")
                art["overMask"] = "0" * 256
                note = (
                    "The complete dashed floor cue comes from an actual invisible wall "
                    "in Crystal Fuchsia Gym. Its native gray stripes meet the rest of "
                    "the selected floor, while the original maze positions, behavior "
                    "and collision keep their exact source guards."
                )
                native_modules.append(record(review, game, pair, mid, art, note))
            elif mid in MAT:
                art = mat_art(review, floor, mid)
                note = (
                    "The entire native Crystal Fuchsia entry rug sits at the original "
                    "south warp's center, with its original 32x16 art at 1:1. The upper "
                    "section reveals the selected native gym floor and the lower section "
                    "reveals the original black void around the mat."
                )
                native_modules.append(record(review, game, pair, mid, art, note))
            elif mid in STATUE:
                art = statue_art(review, floor, mid)
                note = (
                    "The complete original Crystal Fuchsia statue, including its base "
                    "and readable plaque shape, occupies the same 16x32 source envelope. "
                    "The upper priority mask follows the actual statue silhouette. The "
                    "gray floor and both plaque interaction anchors keep their source roles."
                )
                whole = Image.new("RGBA", (16, 32))
                for y, member in enumerate(STATUE):
                    whole.paste(source_image(review, game, pair, member), (0, y * 16))
                value = record(review, game, pair, mid, art, note)
                value.update(
                    source_family=[[648], [663]],
                    whole_source_rgba_sha256=catalog.sha(whole.tobytes()),
                )
                native_objects.append(value)
                if key in review.rows:
                    replaced_aliases.add((game, pair, mid))
            else:
                platform = mid in PLATFORM
                palette = (DARK, GRAY, GOLD, CREAM) if platform else (DARK, BLUE, LIGHT_BLUE, CREAM)
                colors = PLATFORM_COLORS if platform else WALL_COLORS
                feature = "fuchsia_gym_battle_platform" if platform else "fuchsia_gym_ornate_wall"
                masks = exact_floor_masks(review, game, pair, mid) if platform or mid == 662 else {}
                ground = dict(donor=floor, masks=masks) if masks else None
                art = classic_art(review, game, pair, mid, feature, palette, colors, ground=ground)
                note = (
                    "The complete octagonal Gen3 battle platform is a single reviewed "
                    "feature. Its full edge, visible gold center and floor contact use "
                    "explicit Crystal shades and the selected native striped floor."
                    if platform else
                    "The complete Gen3 Fuchsia rear wall includes its columns, windows "
                    "and round crest. The Crystal gym's cream and blue shades keep the "
                    "source geometry legible. The exposed post feet meet the selected "
                    "native striped floor."
                )
                geometry.append(record(review, game, pair, mid, art, note, feature))
            cell = review.imp.cell_index(game)[pair, mid]
            replacement[mid] = review.render(dict(
                art, game=game, style="gen2", tileset=pair, id=mid,
                sourceHash=cell["pixel_sha256"], sourceBehavior=cell["behavior"],
            ))
            if mid == 644 and key in review.current:
                assert "wall_header" in review.current[key]["role"]
        width, height = layout["width"], layout["height"]
        scene = Image.new("RGBA", (width * 16, height * 16))
        for index, mid in enumerate(layout["mids"]):
            if mid not in replacement:
                key = game, "gen2", pair, mid, None
                selected = review.rows.get(key) or review.current[key]
                replacement[mid] = review.render(selected)
            scene.paste(replacement[mid], (index % width * 16, index // width * 16))
        scene.save(OUT / f"{game}-fuchsia-gym-complete-body.png")
    return geometry, native_modules, native_objects, replaced_aliases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    options = parser.parse_args()
    review = Final()
    review.stage()
    geometry, native_modules, native_objects, replaced_aliases = review_gym(review)
    if options.freeze:
        decisions = json.loads(DECISIONS.read_text())
        decisions["geometry"] = [
            item for item in decisions.get("geometry", [])
            if not item["art"]["classicGeometry"]["feature"].startswith("fuchsia_gym_")
        ] + geometry
        for section, records in (("native_modules", native_modules), ("native_objects", native_objects)):
            decisions[section] = [
                item for item in decisions.get(section, []) if item["feature"] != FEATURE
            ] + records
        for alias in decisions["aliases"]:
            alias["targets"] = [
                target for target in alias["targets"]
                if (target["game"], target["pair"], target["mid"]) not in replaced_aliases
            ]
        decisions["aliases"] = [alias for alias in decisions["aliases"] if alias["targets"]]
        DECISIONS.write_text(json.dumps(decisions, indent=2) + "\n")
    print(json.dumps(dict(
        rows=len(geometry) + len(native_modules) + len(native_objects),
        replaced_aliases=sorted(replaced_aliases), frozen=options.freeze,
    )))


if __name__ == "__main__":
    main()
