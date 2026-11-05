"""Review the full native Crystal tree, fence and grass joins in the Safari Zone."""

import argparse
import json

import catalog
import preview
from gb_theme_animation import frames
from reverse_gen2_kanto_final import DECISIONS, OUT, ROOT
from reverse_gen2_kanto_room_materials import Rooms
from reverse_kanto_review import exterior, runs


PREFIX = "kanto_safari_"
PAIR = {"firered": "general__rom_082d4b54", "leafgreen": "general__rom_082d4b34"}
AREAS = {"FR_SAFARI_ZONE_" + area for area in ("CENTER", "EAST", "NORTH", "WEST")}
TOWN = "FR_FUCHSIA_CITY"
ROUTE_15 = "FR_ROUTE_15"
ROUTE_19 = "FR_ROUTE_19"
TREE_SECTIONS = {
    # Original target, exact supporting neighbor, permitted source modules.
    764: (759, "left", {758}),
    772: (767, "left", {766, 793}),
    779: (773, "right", {774}),
    780: (775, "left", {758, 774}),
    792: (789, "right", {766, 793, 798}),
    793: (790, "left", {792}),
    794: (791, "left", {766, 793, 798}),
    800: (757, "right", {758, 801}),
    801: (758, "left", {757, 800}),
    802: (759, "left", {758, 801}),
    803: (765, "right", {766, 798}),
}
FIELDS_AND_FENCES = {
    768: (13, "above", {13}), 769: (13, "above", {13}), 770: (13, "above", {13}),
    776: (230, "below", {792}), 777: (230, "below", {793}), 778: (230, "below", {794}),
    784: (8, "below", {792}), 785: (8, "below", {793}), 786: (8, "below", {772, 794}),
}
FIELD_JOINS = (195, 196, 203, 204, 205, 207)
PATH_JOINS = (211, 741, 742, 744, 745, 746, 747, 749, 750, 816, 817)
SAND_JOINS = (258, 259, 260, 261, 826)
ROCK_COLORS = {
    (90, 58, 66), (123, 74, 74), (148, 107, 107), (189, 148, 140),
    (222, 197, 165), (239, 214, 197),
}
LAWN_COLORS = {(115, 206, 165), (66, 181, 140), (165, 230, 197)}
BOULDER_COLORS = {
    (90, 90, 115), (123, 123, 132), (173, 189, 206), (206, 222, 239), (230, 247, 255),
}
LAND_CLIFFS = {
    131: (108, 0, "left_top"), 132: (109, 1, "right_top"),
    133: (108, 0, "left_straight"), 134: (109, 1, "right_straight"),
    141: (108, 2, "left_turn"), 142: (109, 3, "right_turn"),
    168: (109, 3, "right_coast"),
}
WATER_SHORE = (264, 265, 279, 289, 290, 292, 296, 297, 795, 796, 804, 819, 820, 821)
NATIVE_TOWN = "FUCHSIA_CITY"
ROUTE_GATE_SHELL = (
    (68, 69, 69, 69, 69, 70), (76, 77, 77, 77, 77, 78),
    (387, 388, 388, 388, 388, 389), (438, 437, 437, 437, 437, 439),
    (100, 101, 101, 101, 101, 102),
)
ROUTE_GATE_SIDES = (312, 316, 320, 324, 328, 332, 397, 398)
HOUSES = (
    (672, 673, 674, 674, 675), (676, 677, 678, 677, 679), (684, 685, 686, 670, 687),
)
HOUSE_WALL = (
    (680, 681, 681, 681, 682), (688, 689, 690, 691, 683), (696, 703, 697, 698, 699),
)
SAFARI_MAIN = (
    (700, 701, 701, 701, 701, 702), (704, 705, 705, 705, 705, 706),
    (712, 713, 714, 715, 726, 719), (720, 721, 722, 723, 727, 707),
)
SAFARI_SHELTER = ((700, 701, 701, 701, 702), (708, 695, 709, 709, 710))
SAFARI_OFFICE = ((700, 701, 701, 701, 701, 702), (708, 709, 695, 709, 709, 710))
SHELTER_CAPS = {
    692: (16, "field"), 693: (18, "field"), 694: (21, "field"),
    736: (16, "field"), 737: (18, "field"), 738: (21, "field"),
    748: (16, "cliff"), 743: (18, "cliff"), 751: (21, "cliff"),
    808: (16, "tree"), 809: (18, "tree"), 810: (18, "tree"),
    811: (18, "tree"), 812: (18, "tree"), 813: (21, "tree"),
    730: (16, "fence"), 818: (18, "fence"), 734: (21, "fence"),
    731: (18, "left_stair"), 732: (18, "center_stair"), 733: (18, "right_stair"),
}
SLATE_BUILDING = {
    700: (16, 0, True), 701: (18, 0, True), 702: (21, 0, True),
    704: (16, 1, False), 705: (18, 1, False), 706: (21, 1, False),
    708: (16, 1, False), 695: (18, 1, False), 709: (19, 1, False), 710: (21, 1, False),
    712: (16, 2, False), 713: (17, 2, False), 714: (18, 2, False),
    715: (19, 2, False), 726: (20, 2, False), 719: (21, 2, False),
    720: (16, 3, False), 721: (17, 3, False), 723: (19, 3, False),
    727: (20, 3, False), 707: (21, 3, False),
    716: (16, 3, False), 711: (19, 3, False), 717: (19, 3, False), 718: (21, 3, False),
}


class Safari(Rooms):
    def __init__(self):
        super().__init__()
        self.out = OUT / "safari"
        self.out.mkdir(exist_ok=True)
        self.frame_proof = []

    @staticmethod
    def adjacent(layout, x, y, direction):
        dx, dy = {"left": (-1, 0), "right": (1, 0), "above": (0, -1), "below": (0, 1)}[direction]
        w, h = layout["width"], layout["height"]
        return layout["mids"][(y + dy) * w + x + dx] if 0 <= x + dx < w and 0 <= y + dy < h else 0

    def previous(self, game, pair, mid):
        key = game, "gen2", pair, mid, None
        return self.rows.get(key) or self.current[key]

    def fits(self, scene, family, x, y):
        return self.matches_layout(scene, [list(line) for line in family], x, y)

    def canopy(self, game, pair):
        for mid, (canonical, direction, neighbors) in (TREE_SECTIONS | FIELDS_AND_FENCES).items():
            for name, layout, x, y in self.placements(game, pair, mid):
                assert name in AREAS, (game, name, mid)
                actual = self.adjacent(layout, x, y, direction)
                assert actual in neighbors, (game, name, mid, x, y, direction, actual)
            self.whole_source(game, pair, [[mid]], f"safari_native_tree_join_{mid}")
            previous = self.previous(game, pair, canonical)
            art = self.art_of(previous)
            if mid in TREE_SECTIONS:
                assert previous["role"].startswith("classic_gen2_complete_native_forest_tree_64_")
                self.feature = PREFIX + "native_complete_canopy_variant"
                evidence = (
                    "The original full Safari tree occupies three columns. This "
                    "exposed crown, center, or outer foliage section joins the "
                    "neighboring source tree modules in every Safari placement. "
                    "Use the corresponding complete native Crystal Ilex canopy "
                    "or branch section already approved for this exact tree bank."
                )
                parts = art["parts"]
                art["_objectMask"] = "".join(
                    "1" if any(
                        p["x"] <= x < p["x"] + p["w"]
                        and p["y"] <= y < p["y"] + p["h"] for p in parts
                    ) else "0"
                    for y in range(16) for x in range(16)
                )
            elif mid in (768, 769, 770):
                assert self.imp.cell_index(game)[pair, mid]["behavior_hint"] == "MB_TALL_GRASS"
                assert "grass" in previous["role"]
                self.feature = PREFIX + "complete_tall_grass_at_canopy"
                evidence = (
                    "The whole native Crystal tall-grass square joins the same "
                    "grass above and the complete native tree crown below. "
                    "Encounter grass and its source placement are retained."
                )
            elif mid in (776, 777, 778):
                assert "fence" in previous["role"]
                self.feature = PREFIX + "complete_wooden_fence_at_canopy"
                evidence = (
                    "The original Safari wood post run uses both complete "
                    "native Crystal pickets. The native tree crown in the cell "
                    "below keeps the fence foreground clear."
                )
            else:
                assert previous["role"] == "classic_ordinary_tufted_ground"
                self.feature = PREFIX + "complete_ground_above_canopy"
                evidence = (
                    "Ordinary classic lawn meets the approved full native tree "
                    "crown immediately below. The old source sliver would "
                    "double the canopy in this non-tree cell."
                )
            art["role"] = self.feature
            self.add(game, pair, mid, self.prepare_art(game, pair, mid, art), evidence)

    def emit_detail(self, game, pair, mid, art, role, evidence):
        self.whole_source(game, pair, [[mid]], f"safari_{role}_{mid}")
        self.feature = PREFIX + role
        art["role"] = self.feature
        if not {"overMask", "_objectMask"} & art.keys():
            parts = art.get("parts", [])
            art["_objectMask"] = "".join(
                "1" if any(
                    p["x"] <= x < p["x"]+p["w"] and p["y"] <= y < p["y"]+p["h"]
                    for p in parts
                ) else "0"
                for y in range(16) for x in range(16)
            )
        self.add(game, pair, mid, self.prepare_art(game, pair, mid, art), evidence)

    @staticmethod
    def mask_parts(donor, mask):
        return [dict(donor=donor, srcX=p["x"], srcY=p["y"], **p) for p in runs(mask)]

    def materials(self, game, pair):
        for mids, canonical, area, feature in (
            (FIELD_JOINS, 206, {TOWN}, "continuous_fuchsia_park_ground"),
            (PATH_JOINS, 212, AREAS | {TOWN, ROUTE_15}, "continuous_safari_plain_path"),
            (SAND_JOINS, 220, AREAS | {TOWN, ROUTE_15}, "continuous_safari_sandy_path"),
        ):
            art = self.art_of(self.previous(game, pair, canonical))
            for mid in mids:
                for name, _, _, _ in self.placements(game, pair, mid):
                    assert name in area, (game, name, mid)
                hint = self.imp.cell_index(game)[pair, mid]["behavior_hint"]
                assert hint == "MB_NORMAL" or hint.endswith("_ARROW_WARP"), (game, mid, hint)
                self.emit_detail(
                    game, pair, mid, dict(art), feature,
                    "A plain, curved, or shadowed portion of the actual park "
                    "surface joins its approved original Crystal lawn, "
                    "ordinary path, or sandy Cianwood walking ground. No "
                    "fence, building, rock, grass encounter or water tile "
                    "is part of these exact source material keys.",
                )

    def curbs(self, game, pair):
        ground = self.previous(game, pair, 8)["donor"]
        pickets = self.previous(game, pair, 231)["donor"]
        native = self.gb_image(pickets)
        open_pixels = exterior(native, {(222, 255, 222, 255)})
        fence = self.mask_parts(pickets, [(x, y) not in open_pixels for y in range(16) for x in range(16)])
        for mid in (214, 215, 236, 237, 238, 246, 252, 253, 496, 822, 823, 831):
            uses = list(self.placements(game, pair, mid))
            assert all(name in (TOWN, ROUTE_15) for name, _, _, _ in uses)
            parts = []
            if mid in (236, 237, 238, 246, 252, 253, 496, 823, 831):
                right = mid in (237, 238, 246, 253, 496, 823, 831)
                x = 8 if right else 0
                block, quadrant = ((69, 3) if right else (68, 2)) if mid == 246 else (39, int(right))
                curb = self.gb_ref("crystal", "SAFFRON_CITY", block, quadrant)
                parts.append(dict(donor=curb, srcX=x, srcY=0, x=x, y=0, w=8, h=16))
            if mid in (214, 215, 236, 237, 252, 253, 822, 823):
                parts.extend(fence)
            art = self.composite(ground, parts, "")
            self.emit_detail(
                game, pair, mid, art, "native_fuchsia_fence_or_curb",
                "Whole original Crystal pickets and correctly handed low "
                "curbs match the physical source runs, lower cap, and "
                "fence junctions. Only the native foreground overlaps at a "
                "junction, with the same native lawn in the exterior.",
            )

    def ledges(self, game, pair):
        field = self.previous(game, pair, 8)["donor"]
        sand = self.previous(game, pair, 220)["donor"]
        for mid, (block, quadrant, side) in LAND_CLIFFS.items():
            source = self.source(game, pair, mid)
            allowed = {ROUTE_19} if mid == 168 else {TOWN}
            assert all(name in allowed for name, _, _, _ in self.placements(game, pair, mid))
            pixels = [p[:3] for p in source.get_flattened_data()]
            mask = [p in ROCK_COLORS for p in pixels]
            assert 0 < sum(mask) < 256
            rock = self.gb_ref("crystal", "ROUTE_27", block, quadrant)
            parts = self.mask_parts(rock, mask)
            art = self.composite(sand if mid == 168 else field, parts, "")
            art["_objectMask"] = "".join("1" if v else "0" for v in mask)
            self.emit_detail(
                game, pair, mid, art, f"native_stone_ledge_{side}",
                "The original side-facing cliff keeps its exact rock "
                "silhouette. Original Crystal stone in the same orientation "
                "meets the native lawn or beach, with the exposed exterior "
                "corners clear of any brown fill.",
            )
        mid = 151
        assert all(n == ROUTE_19 for n, _, _, _ in self.placements(game, pair, mid))
        lip = self.gb_ref("crystal", "ROUTE_1", 26, 2)
        art = self.composite(sand, [dict(donor=lip, srcX=0, srcY=8, x=0, y=8, w=16, h=8)], "")
        self.emit_detail(
            game, pair, mid, art, "native_sandy_south_ledge",
            "The full original Crystal south-facing stone ledge sits over "
            "the same native sandy material as the surrounding beach. The "
            "original one-way south hop retains its direction.",
        )

    def wet_shore(self, game, pair):
        field = self.previous(game, pair, 8)["donor"]
        canonical = self.previous(game, pair, 299)
        animation = canonical["animation"]
        water = canonical["parts"][0]["donor"]
        moving = frames(self.cache, water, animation, self.packed)
        assert len({catalog.sha(frame.tobytes()) for frame in moving}) > 1
        coast = self.gb_ref("crystal", "ROUTE_27", 109, 2)
        side_left = self.gb_ref("crystal", "ROUTE_27", 108, 0)
        side_right = self.gb_ref("crystal", "ROUTE_27", 109, 1)
        for mid in WATER_SHORE:
            source = self.source(game, pair, mid)
            cell = self.imp.cell_index(game)[pair, mid]
            assert cell["behavior_hint"] in ("MB_NORMAL", "MB_OCEAN_WATER", "MB_POND_WATER")
            uses = list(self.placements(game, pair, mid))
            assert all(name in AREAS | {TOWN, ROUTE_19} for name, _, _, _ in uses)
            pixels = [p[:3] for p in source.get_flattened_data()]
            assert all(
                p in ROCK_COLORS or p in LAWN_COLORS or p in BOULDER_COLORS or p[2] > p[1] >= p[0]
                for p in pixels
            ), (game, mid)
            mineral = [p in ROCK_COLORS for p in pixels]
            lawn = [p in LAWN_COLORS for p in pixels]
            assert 0 < sum(mineral) < 256
            rock = side_left if mid in (290, 297, 795, 819) else side_right if mid in (279, 289, 292, 296, 804, 821) else coast
            parts = [dict(donor=water, x=0, y=0, w=16, h=16, animated=True)]
            parts.extend(self.mask_parts(rock, mineral))
            parts.extend(self.mask_parts(field, lawn))
            if mid in (264, 265):
                q = mid - 264
                target = 280 + q
                assert all(self.adjacent(l, x, y, "below") == target for _, l, x, y in uses)
                lower = self.previous(game, pair, target)
                assert lower["role"] == f"classic_gen2_complete_coastal_small_rock_quarter_{q+2}"
                rock_ref = lower["parts"][1]["donor"]
                assert (rock_ref["map"], rock_ref["id"], rock_ref["quadrant"]) == ("CHERRYGROVE_CITY", 52, 0)
                quarter = self.gb_image(rock_ref).crop((q*4, 0, q*4+4, 4))
                outside = exterior(quarter, {p for p in quarter.get_flattened_data() if p[2] > p[1]})
                parts.extend(
                    dict(donor=rock_ref, srcX=q*4+p["x"], srcY=p["y"],
                         x=(0 if q else 12)+p["x"], y=12+p["y"], w=p["w"], h=p["h"])
                    for p in runs([
                        x < 4 and y < 4 and (x, y) not in outside
                        for y in range(16) for x in range(16)
                    ])
                )
            assert len(parts) <= 32, (game, mid, len(parts))
            art = self.composite(None, parts, "")
            art.update(animated=True, animation=animation, animationCategory="water", overMask="0"*256)
            native_frames = preview.replacement_frames(self.cache, art, self.packed, ROOT)
            for rendered, wave in zip(native_frames, moving, strict=True):
                expected = wave.copy()
                for part in parts[1:]:
                    x, y = part["srcX"], part["srcY"]
                    image = self.gb_image(part["donor"])
                    expected.paste(image.crop((x, y, x+part["w"], y+part["h"])), (part["x"], part["y"]))
                assert rendered.tobytes() == expected.tobytes(), (game, mid)
            self.frame_proof.append(dict(game=game, mid=mid, hashes=[catalog.sha(i.tobytes()) for i in native_frames]))
            self.emit_detail(
                game, pair, mid, art, "native_animated_shore_contour",
                "The exact connected pond or ocean edge uses the surrounding "
                "animated Crystal water and original native stone. Its rocky "
                "silhouette and open corners are independent of the water "
                "frame. The paired Route 19 pieces complete the approved "
                "native water boulder above its original lower quarters.",
            )

        for mid in (307, 671):
            source = self.source(game, pair, mid)
            uses = list(self.placements(game, pair, mid))
            assert all(name in AREAS | {TOWN} for name, _, _, _ in uses)
            assert all(self.adjacent(l, x, y, "above") in (298, 299, 300, 429, 430, 431) for _, l, x, y in uses)
            mask = [p[:3] in ROCK_COLORS for p in source.get_flattened_data()]
            assert 0 < sum(mask) < 256
            parts = self.mask_parts(coast, mask)
            if mid == 671:
                tree = self.previous(game, pair, 756)
                assert tree["role"] == "classic_gen2_complete_native_small_decorative_tree"
                parts.extend(tree["parts"])
            art = self.composite(field, parts, "")
            self.emit_detail(
                game, pair, mid, art, "native_safari_dry_bank",
                "The narrow dry shore continues the adjacent pond with the "
                "original native stone texture and exact grass beneath. The "
                "two occupied bank cells use the same complete native shrub "
                "as the neighboring original shrub row.",
            )

    def route_gate(self, game, pair):
        _, scene = self.layouts[game, ROUTE_15]
        assert self.fits(scene, ROUTE_GATE_SHELL, 10, 8)
        warps = self.imp.table(game, "gba/warps")[ROUTE_15]
        assert {(w["x"], w["y"], w["destMap"]) for w in warps} == {
            (9, 11, "FR_ROUTE_15_WEST_ENTRANCE_1F"), (16, 11, "FR_ROUTE_15_WEST_ENTRANCE_1F"),
        }
        gcell = self.imp.cell_index(game)
        previous_pair = self.layouts[game, "FR_SAFFRON_CITY"][0]["pair"]
        field = self.previous(game, pair, 8)["donor"]
        mids = sorted({m for line in ROUTE_GATE_SHELL for m in line} | set(ROUTE_GATE_SIDES))
        for mid in mids:
            source, prior = gcell[pair, mid], gcell[previous_pair, mid]
            assert all(source[k] == prior[k] for k in ("pixel_sha256", "layer_sha256", "behavior"))
            assert all(n == ROUTE_15 for n, _, _, _ in self.placements(game, pair, mid))
            previous = self.previous(game, previous_pair, mid)
            assert previous["role"] == "kanto_saffron_complete_gate_exterior"
            art = self.art_of(previous)
            if art.get("base"):
                art["base"] = field
            self.emit_detail(
                game, pair, mid, art, "native_route_15_gate",
                "The exact same complete side-facing Gate shell has both "
                "actual west and east source doorway warps. Matching whole "
                "Crystal cap, eave, jambs, walls, and facing native thresholds "
                "reuse the verified Saffron gate artwork over this route's field.",
            )

    def architecture_strip(
        self, ground, column, row, repeat=False, prefix_rows=0, bottom_half=False,
        extend_plain_roof=False,
    ):
        donor = self.gb_at("crystal", NATIVE_TOWN, column, row)
        image = self.gb_image(donor)
        parts = []
        for y in range(prefix_rows, 16):
            if bottom_half:
                sy = y - prefix_rows
            elif extend_plain_roof and y < 8:
                sy = 7
            elif repeat:
                sy = 8 + y % 8
            else:
                sy = y
            left, right = 0, 16
            # Only the original outside frame can expose background.
            if column in (16, 26):
                while left < 16 and image.getpixel((left, sy)) == (222, 255, 222, 255):
                    left += 1
            if column in (21, 29):
                while right > left and image.getpixel((right - 1, sy)) == (222, 255, 222, 255):
                    right -= 1
            if right == left:
                continue
            prev = parts[-1] if parts else None
            if prev and prev["x"] == left and prev["w"] == right-left and prev["srcY"] + prev["h"] == sy:
                prev["h"] += 1
            else:
                parts.append(dict(donor=donor, srcX=left, srcY=sy, x=left, y=y, w=right-left, h=1))
        return self.composite(ground, parts, "")

    def town_houses(self, game, pair):
        field = self.previous(game, pair, 8)["donor"]
        cliff = self.previous(game, pair, 113)["donor"]
        _, scene = self.layouts[game, TOWN]
        warp_map = self.imp.table(game, "gba/warps")[TOWN]
        actual = {(w["x"], w["y"]) for w in warp_map if "_HOUSE" in w["destMap"]}
        assert {(14, 31), (19, 31), (33, 31), (38, 31), (39, 28), (39, 29)} <= actual
        for x, y, caps in ((13, 28, HOUSES[0]), (18, 28, HOUSES[0]), (32, 28, HOUSES[1]), (37, 28, HOUSES[2])):
            assert self.fits(scene, (caps, *HOUSE_WALL), x, y)
        for group, surface in zip(HOUSES, (cliff, field, field), strict=True):
            for mid, x in zip(group, (26, 27, 28, 28, 29), strict=True):
                key = game, "gen2", pair, mid, None
                if key in self.replacements:
                    continue
                art = self.architecture_strip(surface, x, 25, prefix_rows=8, bottom_half=True)
                if mid == 686:
                    assert all((n, x, y) == (TOWN, 39, 28) for n, _, x, y in self.placements(game, pair, mid))
                    stairs = self.gb_ref("crystal", "UNION_CAVE_1F", 18, 3)
                    art["parts"].insert(0, dict(donor=stairs, srcX=0, srcY=0, x=0, y=0, w=16, h=8))
                self.emit_detail(
                    game, pair, mid, art, "native_fuchsia_house_roof_cap",
                    "The complete original Crystal Warden's house roof cap "
                    "joins all four actual source houses. Native cliff or field "
                    "shows at the original outside edge. The back entrance "
                    "keeps the original south-facing step at the source warp.",
                )
        donors = {
            680: (26, 25, True), 681: (28, 25, True), 682: (29, 25, True),
            688: (26, 26, False), 689: (27, 26, False), 690: (28, 26, False),
            691: (28, 26, False), 683: (29, 26, False),
            696: (26, 27, False), 703: (27, 27, False), 697: (28, 27, False),
            698: (28, 27, False), 699: (29, 27, False),
        }
        for mid, (x, y, repeat) in donors.items():
            assert all(n in AREAS | {TOWN} for n, _, _, _ in self.placements(game, pair, mid))
            art = self.architecture_strip(field, x, y, extend_plain_roof=repeat)
            self.emit_detail(
                game, pair, mid, art, "native_fuchsia_house_walls",
                "The full original Crystal Warden's house roof, wall and "
                "door modules fill the source building. Only plain roof "
                "and interior window modules repeat. Outside wall frames "
                "appear only at the matching building edges.",
            )
        for mid in (640, 641, 642, 643, 644):
            assert all(
                n == TOWN and y == 27 and 23 <= x <= 27
                for n, _, x, y in self.placements(game, pair, mid)
            )
            self.emit_detail(
                game, pair, mid, self.native(cliff, ""), "complete_cliff_behind_native_center",
                "The full native Pokemon Center roof starts immediately "
                "below. The exposed row above it uses the same native "
                "continuous cliff as the surrounding raised ground.",
            )

    def safari_buildings(self, game, pair):
        field = self.previous(game, pair, 8)["donor"]
        cliff = self.previous(game, pair, 113)["donor"]
        native_warps = self.imp.table("crystal", "maps")[NATIVE_TOWN]["warps"]
        assert any(
            (w["x"], w["y"], w["destMap"]) == (18, 3, "SAFARI_ZONE_FUCHSIA_GATE_BETA")
            for w in native_warps
        )
        maps = self.imp.table(game, "gba/warps")
        for name in sorted(AREAS | {TOWN}):
            _, scene = self.layouts[game, name]
            warps = maps[name]
            for warp in warps:
                target, x, y = warp["destMap"], warp["x"], warp["y"]
                if name == TOWN and target == "FR_FUCHSIA_CITY_SAFARI_ZONE_ENTRANCE":
                    assert (x, y) == (24, 5)
                    assert self.fits(scene, SAFARI_MAIN, x-2, y-3)
                elif target == "FR_SAFARI_ZONE_SECRET_HOUSE":
                    assert self.fits(scene, SAFARI_MAIN, x-2, y-3)
                elif target.endswith("REST_HOUSE"):
                    assert self.fits(scene, SAFARI_SHELTER, x-1, y-2)
                elif name == TOWN and target.endswith("SAFARI_ZONE_OFFICE"):
                    assert self.fits(scene, SAFARI_OFFICE, x-2, y-2)
        for mid, (x, y, repeat) in SLATE_BUILDING.items():
            assert all(n in AREAS | {TOWN} for n, _, _, _ in self.placements(game, pair, mid))
            art = self.architecture_strip(field, x, y, repeat=repeat)
            self.emit_detail(
                game, pair, mid, art, "native_safari_building_shell",
                "The original Crystal Fuchsia Safari entrance supplies the "
                "complete slate roof, wall bands, outer frames and windows. "
                "Only the interior roof fill or plain window bands repeat "
                "within the exact original source footprints.",
            )
        door = self.gb_at("crystal", NATIVE_TOWN, 22, 13)
        for mid in (722, 724, 725, 814, 815):
            if mid == 722:
                art = self.native(door, "")
            else:
                path = self.previous(game, pair, 212)["donor"]
                art = self.native(path, "")
            self.emit_detail(
                game, pair, mid, art, "native_safari_front_threshold",
                "The full original Crystal Safari office door is visible "
                "at the actual source entrance. Its exterior walkable trim "
                "joins the approved path in front of the building.",
            )
        for mid, (x, region) in SHELTER_CAPS.items():
            assert all(n in AREAS | {TOWN} for n, _, _, _ in self.placements(game, pair, mid))
            ground = cliff if region == "cliff" else field
            art = self.architecture_strip(ground, x, 0, prefix_rows=8, bottom_half=True)
            if region == "tree":
                tree = self.previous(game, pair, 757 + (mid - 808) % 3)
                cap = [dict(p, h=min(p["h"], 8-p["y"])) for p in tree["parts"] if p["y"] < 8]
                art["parts"] = cap + art["parts"]
            elif region == "fence":
                posts = self.previous(game, pair, 230)["donor"]
                art["parts"].insert(0, dict(donor=posts, srcX=0, srcY=0, x=0, y=0, w=16, h=8))
            elif region.endswith("stair"):
                stairs = self.gb_ref("crystal", "UNION_CAVE_1F", 18, 3)
                if region == "center_stair":
                    parts = [
                        dict(donor=stairs, srcX=8, srcY=8, x=i, y=0, w=1, h=8)
                        for i in range(16)
                    ]
                else:
                    ox = 8 if region == "left_stair" else 0
                    parts = [dict(donor=stairs, srcX=8-ox, srcY=8, x=ox, y=0, w=8, h=8)]
                art["parts"] = parts + art["parts"]
            assert len(art["parts"]) <= 32
            self.emit_detail(
                game, pair, mid, art, "native_safari_roof_approach",
                "The complete original slate roof cap meets the actual "
                "field, cliff, tree crown, fence, or correctly oriented "
                "north-south stairs in the exposed approach. The source "
                "entrance and each original warp coordinate stay aligned.",
            )

    def exhibit_fences(self, game, pair):
        field = self.previous(game, pair, 8)["donor"]
        horizontal = self.gb_at("crystal", "NATIONAL_PARK", 13, 3)
        front = self.gb_at("crystal", "NATIONAL_PARK", 15, 46)
        vertical = self.gb_at("crystal", "NATIONAL_PARK", 11, 4)
        sign = self.gb_at("crystal", "NATIONAL_PARK", 14, 44)
        outside_colors = {
            (222, 255, 222, 255), (173, 173, 173, 255),
            (181, 255, 82, 255), (99, 206, 8, 255), (41, 115, 0, 255),
        }
        def clipped(donor):
            image = self.gb_image(donor)
            outside = exterior(image, outside_colors)
            return self.mask_parts(donor, [(x, y) not in outside for y in range(16) for x in range(16)])

        for mid in (654, 655, 656, 657, 658, 659, 660, 661, 662, 664, 667, 668, 824, 825):
            uses = list(self.placements(game, pair, mid))
            assert all(name == TOWN for name, _, _, _ in uses)
            if mid in (656, 658, 664):
                left = mid != 658
                side = self.gb_at("crystal", "NATIONAL_PARK", 11 if left else 24, 3)
                image = self.gb_image(side)
                outside = exterior(image, outside_colors)
                shift = -4 if left else 4
                parts = [
                    dict(p, x=p["x"]+shift) for p in self.mask_parts(side, [
                        (x, y) not in outside and 0 <= x+shift < 16
                        for y in range(16) for x in range(16)
                    ])
                ]
                parts.append(dict(donor=horizontal, srcX=12 if left else 0, srcY=8,
                                  x=12 if left else 0, y=8, w=4, h=8))
            elif mid == 657:
                parts = clipped(horizontal)
            elif mid in (659, 661, 667, 668):
                parts = [dict(donor=vertical, srcX=8, srcY=0, x=4, y=0, w=8, h=8 if mid == 668 else 16)]
                if mid == 668:
                    parts.extend(clipped(front))
            elif mid in (655, 662, 825):
                parts = clipped(front) + clipped(sign)
            elif mid in (654, 824):
                parts = clipped(front)
            else:
                assert mid == 660
                assert all(self.adjacent(l, x, y, "above") == 657 for _, l, x, y in uses)
                parts = []
            art = self.composite(field, parts, "") if parts else self.native(field, "")
            self.emit_detail(
                game, pair, mid, art, "native_complete_fuchsia_habitat_rail",
                "The original Crystal National Park railing supplies the "
                "complete exposed habitat rails, joined corners and actual "
                "sign plaques. The same native width and facing continue "
                "through the whole enclosure, with clear surrounding field.",
            )

    def remaining_details(self, game, pair):
        field = self.previous(game, pair, 8)["donor"]
        sand = self.previous(game, pair, 220)["donor"]
        sign = self.gb_at("crystal", NATIVE_TOWN, 27, 29)
        for mid in (353, 361, 500, 650):
            if mid in (353, 361):
                expected = (31, 30 if mid == 353 else 31)
                assert all((x, y) == expected and n == TOWN for n, _, x, y in self.placements(game, pair, mid))
                if mid == 353:
                    art = self.native(field, "")
                else:
                    image = self.gb_image(sign)
                    outside = exterior(image, {(222, 255, 222, 255), (173, 173, 173, 255)})
                    parts = self.mask_parts(sign, [(x, y) not in outside for y in range(16) for x in range(16)])
                    art = self.composite(field, parts, "")
                self.emit_detail(
                    game, pair, mid, art, "complete_native_wardens_house_sign",
                    "The complete original Crystal Warden's house sign "
                    "is aligned with the actual source sign. Its exterior "
                    "reveals the same surrounding field.",
                )
            else:
                assert all(n == ROUTE_19 for n, _, _, _ in self.placements(game, pair, mid))
                q = 2 if mid == 500 else 3
                rock = self.gb_ref("crystal", "ROUTE_27", 109, q)
                source = self.source(game, pair, mid)
                mask = [p[:3] in ROCK_COLORS for p in source.get_flattened_data()]
                assert 0 < sum(mask) < 256
                art = self.composite(sand, self.mask_parts(rock, mask), "")
                self.emit_detail(
                    game, pair, mid, art, "native_sandy_ledge_ends",
                    "Native Crystal stone ends the actual repeated beach "
                    "ledge with the original source rock outline. Open "
                    "corners expose the selected native sand.",
                )

    def coverage(self):
        results = {}
        for (game, name), (spec, layout) in self.layouts.items():
            if spec["pair"] != PAIR[game]:
                continue
            keys = [(game, "gen2", spec["pair"], mid, None) for mid in layout["mids"]]
            unresolved = [
                key[3] for key in keys
                if key not in self.replacements and key not in self.current
                and (key not in self.rows or self.rows[key]["role"].startswith(PREFIX))
            ]
            results[f"{game}:{name}"] = dict(cells=len(keys), remaining=len(unresolved), missing=sorted(set(unresolved)))
        (self.out / "candidate-coverage.json").write_text(json.dumps(results, indent=2) + "\n")
        return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    options = parser.parse_args()
    r = Safari()
    r.stage()
    for game, pair in PAIR.items():
        r.canopy(game, pair)
        r.materials(game, pair)
        r.curbs(game, pair)
        r.ledges(game, pair)
        r.wet_shore(game, pair)
        r.route_gate(game, pair)
        r.town_houses(game, pair)
        r.safari_buildings(game, pair)
        r.exhibit_fences(game, pair)
        r.remaining_details(game, pair)
    r.previews(sorted(AREAS | {TOWN, ROUTE_15, ROUTE_19}))
    coverage = r.coverage()
    remaining = sum(scene["remaining"] for scene in coverage.values())
    (r.out / "safari-water-frame-proof.json").write_text(json.dumps(r.frame_proof, indent=2) + "\n")
    if options.freeze:
        assert remaining == 0, remaining
        decisions = json.loads(DECISIONS.read_text())
        for section, records in r.frozen.items():
            decisions[section] = [
                row for row in decisions.get(section, [])
                if not row.get("feature", "").startswith(PREFIX)
            ] + records
        DECISIONS.write_text(json.dumps(decisions, indent=2) + "\n")
    print(json.dumps(dict(
        rows=len(r.replacements),
        cells=sum(sum(u["count"] for u in r.usage[g, p, m]) for g, _, p, m, _ in r.replacements),
        remaining=remaining,
        frozen=options.freeze,
    )))


if __name__ == "__main__":
    main()
