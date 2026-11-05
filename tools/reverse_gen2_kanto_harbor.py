"""Author the complete Sevii ferry-terminal facade and metal safety rail."""

import argparse
import json

from PIL import Image

import catalog
import preview
from classic_geometry_review import art as classic_art
from reverse_gen2_kanto_final import DECISIONS, OUT, Final
from reverse_kanto_review import runs


PAIR = "harbor"
FACADE = (
    648, 649, 650, 656, 657, 658, 664, 665, 666, 704, 705, 706,
    707, 708, 709, 710, 712, 713, 714, 715, 716, 717, 718,
)
RAIL = (652, 653, 654, 655, 660, 661, 662, 663, 669, 677)
MATERIALS = (641, 685)
SHORES = {
    288: ("PALLET_TOWN", 29, 0, (0, 1, 2)),
    289: ("PALLET_TOWN", 30, 1, (0, 1, 3)),
    304: ("ROUTE_27", 122, 1, (1,)),
    305: ("ROUTE_27", 121, 0, (0,)),
}

BLACK = (0, 0, 0)
SHADE = (107, 107, 107)
METAL = (156, 156, 156)
HIGHLIGHT = (247, 230, 214)
PALETTE = (BLACK, SHADE, METAL, HIGHLIGHT)
COLORS = {
    (0, 0, 0): BLACK,
    (58, 58, 107): BLACK,
    (58, 156, 115): SHADE,
    (74, 132, 197): SHADE,
    (82, 82, 107): BLACK,
    (99, 99, 123): SHADE,
    (99, 165, 222): METAL,
    (107, 115, 115): SHADE,
    (107, 206, 165): METAL,
    (115, 189, 247): HIGHLIGHT,
    (123, 123, 123): SHADE,
    (123, 123, 132): SHADE,
    (140, 140, 156): METAL,
    (148, 156, 156): METAL,
    (156, 165, 189): METAL,
    (173, 173, 165): METAL,
    (181, 189, 189): HIGHLIGHT,
    (189, 206, 230): HIGHLIGHT,
    (197, 189, 99): SHADE,
    (197, 247, 230): HIGHLIGHT,
    (206, 214, 214): HIGHLIGHT,
    (206, 222, 239): HIGHLIGHT,
    (222, 107, 99): METAL,
    (222, 214, 123): HIGHLIGHT,
    (239, 247, 255): HIGHLIGHT,
    (255, 181, 148): HIGHLIGHT,
}
PAVEMENT_COLORS = {
    (107, 115, 115), (148, 156, 156), (181, 189, 189), (206, 214, 214),
}

# Visible ordinary pavement on the landward half of the four rail returns,
# and below the two terminal end posts. Internal rail bays remain intact.
PAVEMENT_RECTS = {
    652: (0, 0, 8, 16),
    654: (8, 0, 8, 16),
    660: (0, 0, 8, 16),
    662: (8, 0, 8, 16),
    716: (0, 8, 16, 8),
    718: (0, 8, 16, 8),
}


def source_image(review, game, mid):
    cell = review.imp.cell_index(game)[PAIR, mid]
    ref = dict(game=game, tileset=PAIR, id=mid, hash=cell["pixel_sha256"])
    return preview.native_donor(review.cache, ref, review.packed)


def pavement_masks(review, game, mid):
    if mid not in PAVEMENT_RECTS:
        return {}
    left, top, width, height = PAVEMENT_RECTS[mid]
    mids, palette, planes = review.packed[game, PAIR]
    slot = mids.index(mid)
    masks = {}
    for name, packed_plane in planes.items():
        rgba = catalog.rgba_native(
            packed_plane[slot * 256:(slot + 1) * 256], palette, name != "under"
        )
        bits = []
        for index, pixel in enumerate(rgba.get_flattened_data()):
            x, y = index % 16, index // 16
            in_pavement = left <= x < left + width and top <= y < top + height
            bits.append("1" if in_pavement and pixel[3] and pixel[:3] in PAVEMENT_COLORS else "0")
        if "1" in bits:
            masks[name] = "".join(bits)
    return masks


def shore_corner(review, game, mid):
    map_id, block, quadrant, rock_quadrants = SHORES[mid]
    rock = review.gb_ref("crystal", map_id, block, quadrant)
    donor = review.gb_image(rock)
    water_ref = review.gb_ref("crystal", "PALLET_TOWN", 29, 3)
    water_colors = set(review.gb_image(water_ref).get_flattened_data())
    mask = []
    for index, pixel in enumerate(donor.get_flattened_data()):
        x, y = index % 16, index // 16
        quad = y // 8 * 2 + x // 8
        if quad not in rock_quadrants:
            assert pixel in water_colors, ("Unexpected native foreground outside tip", mid, x, y)
        mask.append(quad in rock_quadrants and pixel not in water_colors)
    if mid in (288, 289):
        assert sum(mask) == 192, ("Incomplete native concave bank", mid)
    else:
        assert 0 < sum(mask) <= 64, ("Native convex tip should have clear exterior", mid)
    water = review.current[game, "gen2", PAIR, 299, None]
    art = review.art_of(water)
    for span in runs(mask):
        art["parts"].append(dict(
            span, donor=rock, srcX=span["x"], srcY=span["y"],
        ))
    art["role"] = "classic_gen2_complete_sevii_harbor_bank_corner"
    art["overMask"] = "0" * 256
    return art


def freeze(review):
    geometry = []
    modules = []
    staged = {}
    source_views = {}
    empty_over = catalog.sha(bytes(1024))
    stair = review.gb_ref("crystal", "UNION_CAVE_1F", 18, 3)
    for game in review.games:
        _, canonical = review.layouts[game, "FR_BIRTH_ISLAND_HARBOR"]
        layouts = [
            layout for (host, _), (spec, layout) in review.layouts.items()
            if host == game and spec["pair"] == PAIR
        ]
        assert len(layouts) == 9
        assert all(layout["mids"] == canonical["mids"] for layout in layouts)
        pavement = review.current[game, "gen2", PAIR, 642, None]["donor"]

        for mid in FACADE + RAIL + MATERIALS + tuple(SHORES):
            key = game, "gen2", PAIR, mid, None
            assert key not in review.current
            source_views[game, mid] = source_image(review, game, mid)
            cell = review.imp.cell_index(game)[PAIR, mid]
            record = dict(
                game=game, pair=PAIR, mid=mid, rgba=cell["pixel_sha256"],
                behavior=cell["behavior"], layers=cell["layer_sha256"],
            )
            if mid in SHORES:
                assert cell["layer_sha256"]["over"] == empty_over
                art = shore_corner(review, game, mid)
                evidence = (
                    "The two pier shoulders and two lower tips were reviewed in their complete "
                    "native harbor orientation. The original Crystal Pallet inset banks and Route27 "
                    "stone tips retain every rock pixel in their native handed modules. Original "
                    "water pixels outside each rock silhouette reveal the same imported, animated "
                    "Crystal ocean base used on the neighboring full sea and straight banks. The "
                    "source sea behavior and pier dimensions retain their exact guards."
                )
                modules.append(dict(
                    record, feature="sevii_harbor_bank_corner", art=art, evidence=evidence,
                ))
            elif mid in MATERIALS:
                assert cell["layer_sha256"]["over"] == empty_over
                feature = "sevii_harbor_pavement" if mid == 641 else "sevii_harbor_stair"
                native = pavement if mid == 641 else stair
                art = review.native(native, "classic_gen2_" + feature)
                art["overMask"] = "0" * 256
                if mid == 641:
                    evidence = "The entire pier deck uses the existing native Crystal stone pavement. The brighter source deck squares are the same ordinary walking surface as the neighboring source642 cells."
                else:
                    evidence = "The pier descent is a single south-facing flight with horizontal treads. The complete native Crystal UNION_CAVE18q3 stone flight keeps the original direction and 16px footprint."
                modules.append(dict(record, feature=feature, art=art, evidence=evidence))
            else:
                feature = "sevii_harbor_terminal" if mid in FACADE else "sevii_harbor_safety_rail"
                masks = pavement_masks(review, game, mid)
                ground = dict(donor=pavement, masks=masks) if masks else None
                art = classic_art(review, game, PAIR, mid, feature, PALETTE, COLORS, ground=ground)
                evidence = (
                    "The complete regional Sevii ferry terminal and joined metal safety rail were "
                    "reviewed across all nine identical native harbor layouts. Their tall facade, "
                    "window glass, sign, doorway, posts and returns have no whole Crystal counterpart. "
                    "Four explicit Crystal industrial shades retain every source geometry and priority "
                    "coordinate. The reviewed landward pavement strips use the same complete native "
                    "Crystal pavement as the pier deck. The original movement, doorway, maps and actors "
                    "retain their source anchors."
                )
                geometry.append(dict(record, art=art, evidence=evidence))
            staged[key] = review.render(dict(
                art, game=game, style="gen2", tileset=PAIR, id=mid,
                sourceHash=cell["pixel_sha256"], sourceBehavior=cell["behavior"],
            ))
    return geometry, modules, staged, source_views


def previews(review, staged, source_views):
    for game in review.games:
        _, layout = review.layouts[game, "FR_BIRTH_ISLAND_HARBOR"]
        width, height = layout["width"], layout["height"]
        scene = Image.new("RGBA", (width * 16, height * 16))
        masks = scene.copy()
        originals = scene.copy()
        for index, mid in enumerate(layout["mids"]):
            position = index % width * 16, index // width * 16
            original = source_views.get((game, mid))
            if original is None:
                original = source_image(review, game, mid)
            key = game, "gen2", PAIR, mid, None
            tile = staged.get(key)
            if tile is None:
                row = review.current.get(key)
                tile = review.render(row) if row else original
            originals.paste(original, position)
            scene.paste(tile, position)
            marker = original.copy()
            changed = pavement_masks(review, game, mid)
            for pixel in range(256):
                if any(mask[pixel] == "1" for mask in changed.values()):
                    marker.putpixel((pixel % 16, pixel // 16), (255, 0, 255, 255))
            masks.paste(marker, position)
        for label, image in (("source", originals), ("staged", scene), ("masks", masks)):
            image.resize((width * 48, height * 48), Image.Resampling.NEAREST).save(
                OUT / f"{game}-harbor-complete-{label}.png"
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    options = parser.parse_args()
    review = Final()
    geometry, modules, staged, source_views = freeze(review)
    previews(review, staged, source_views)
    if options.freeze:
        decisions = json.loads(DECISIONS.read_text())
        decisions["geometry"] = [
            entry for entry in decisions.get("geometry", [])
            if not entry["art"]["classicGeometry"]["feature"].startswith("sevii_harbor_")
        ] + geometry
        decisions["native_modules"] = [
            entry for entry in decisions.get("native_modules", [])
            if not entry["feature"].startswith("sevii_harbor_")
        ] + modules
        DECISIONS.write_text(json.dumps(decisions, indent=2) + "\n")
    cells = sum(
        sum(use["count"] for use in review.usage[entry["game"], PAIR, entry["mid"]])
        for entry in geometry + modules
    )
    print(json.dumps(dict(rows=len(staged), cells=cells, frozen=options.freeze)))


if __name__ == "__main__":
    main()
