"""Use Saffron's complete native Crystal Silph facade and street surfaces."""

import argparse
import json
from collections import defaultdict

from PIL import Image

import catalog
from classic_geometry_review import art as classic_art
from reverse_gen2_kanto_final import DECISIONS, OUT
from reverse_gen2_kanto_room_materials import EMPTY_OVER, Rooms
from reverse_kanto_review import exterior, runs


PREFIX = "kanto_saffron_"
CITY = "FR_SAFFRON_CITY"
CONNECTION = "FR_SAFFRON_CITY_CONNECTION"
NATIVE_CITY = "SAFFRON_CITY"
PAVEMENT = (737, 739, 740, 741, 744, 746, 747, 749, 753, 755, 757)
WALL_ROW = [712, 713, 714, 714, 714, 714, 714, 715, 716]
ROOF_ROW = [688, 689, 689, 717, 718, 719, 689, 689, 690]
TOWER = [
    [680, 681, 681, 709, 710, 711, 681, 681, 682],
    ROOF_ROW, ROOF_ROW, ROOF_ROW,
    [696, 697, 697, 725, 726, 727, 697, 697, 698],
    [704, 705, 706, 706, 706, 706, 706, 707, 708],
    *[WALL_ROW] * 6,
    [712, 713, 714, 683, 684, 685, 714, 715, 716],
    [720, 721, 714, 691, 692, 693, 714, 722, 723],
    [728, 729, 724, 699, 700, 701, 724, 730, 731],
]
INTERIOR_COLUMNS = (16, 17, 19, 19, 19, 19, 19, 22, 23)
ENTRY_UPPER = {720: 16, 721: 17, 691: 17, 692: 18, 693: 19, 722: 21, 723: 23}
ENTRY_LOWER = {728: 16, 729: 17, 724: 20, 699: 17, 700: 18, 701: 19, 730: 22, 731: 23}
OUTSIDE = (222, 255, 222, 255)
HOUSE_ROOF = {
    661: (16, 10, False), 662: (18, 10, False), 663: (23, 10, False),
    669: (16, 10, True), 670: (18, 10, True), 671: (23, 10, True),
    677: (16, 11, False), 678: (18, 11, False), 655: (18, 11, False),
    679: (23, 11, False), 647: (18, 11, False),
    733: (18, 10, False), 734: (23, 10, False),
}
HOUSE_FACADE = {
    664: (16, 14), 665: (17, 14), 666: (19, 14), 667: (22, 14), 668: (23, 14),
    672: (16, 21), 673: (17, 21), 674: (20, 21), 675: (22, 21), 676: (23, 21),
    694: (17, 14), 695: (22, 14), 702: (16, 14), 703: (17, 14), 687: (22, 14),
    686: (16, 21), 644: (27, 29), 652: (22, 21), 651: (17, 21),
}
HOUSE_NEIGHBORS = set(HOUSE_ROOF) | set(HOUSE_FACADE) | {648, 649, 653, 654, 656, 657, 658, 659, 660}
UTILITY_ROOF = [[641, 642, 642, 645, 646], [648, 649, 649, 653, 654], [656, 657, 658, 659, 660]]
UTILITY_PALETTE = ((58, 58, 58), (107, 107, 107), (173, 173, 173), (222, 255, 222))
UTILITY_COLORS = {
    (0, 0, 0): UTILITY_PALETTE[0],
    (82, 82, 107): UTILITY_PALETTE[0],
    (123, 123, 132): UTILITY_PALETTE[1],
    (165, 156, 16): UTILITY_PALETTE[1],
    (140, 189, 148): UTILITY_PALETTE[2],
    (140, 156, 173): UTILITY_PALETTE[2],
    (206, 197, 107): UTILITY_PALETTE[2],
    (214, 206, 33): UTILITY_PALETTE[2],
    (74, 132, 197): UTILITY_PALETTE[3],
    (247, 239, 74): UTILITY_PALETTE[3],
    (255, 255, 148): UTILITY_PALETTE[3],
    (255, 255, 255): UTILITY_PALETTE[3],
}
FENCE_COLUMNS = {
    781: (0, 8), 793: (0, 8), 809: (0, 8),
    **dict.fromkeys((792, 794, 796, 797, 798, 800, 802, 803, 805, 806, 808, 810, 813, 814), (4,)),
}
GATE_SHELL = {
    68: (10, 4), 69: (11, 4), 70: (13, 4),
    76: (10, 4), 77: (11, 4), 78: (13, 4),
    387: (10, 5), 388: (11, 5), 389: (13, 5),
    438: (10, 6), 437: (11, 6), 439: (13, 6),
    100: (10, 7), 101: (11, 7), 102: (13, 7),
    320: (9, 6), 328: (9, 7), 324: (14, 6), 332: (14, 7),
}
GATE_FRONT = {
    92: (4, 0), 94: (9, 0),
    392: (5, 0), 393: (7, 0), 394: (8, 0),
    400: (5, 1), 402: (8, 1),
}
GATE_RECTANGLES = ((32, 0, 38, 7), (32, 44, 38, 55), (0, 23, 13, 30), (54, 23, 66, 30))
GATE_FLOOR = (211, 238, 239, 312, 316, 397, 398)
DOJO = [
    [816, 817, 799, 817, 799, 818],
    [824, 825, 825, 825, 825, 826],
    [832, 833, 833, 833, 833, 834],
    [821, 822, 823, 811, 812, 827],
    [829, 830, 831, 819, 820, 835],
]
STREET_DETAILS = {
    142: {(4, 29)}, 236: {(5, 29), (37, 53)}, 237: {(32, 53)},
    246: {(24, 1), (32, 8)}, 247: {(5, 33), (43, 1)},
    732: {(22, 18), (27, 35), (42, 18)},
    776: {(50, 8)}, 777: {(51, 8)}, 778: {(52, 8)}, 779: {(53, 8)},
    790: {(14, 44)}, 791: {(53, 44)}, 807: {(40, 37)},
    815: {(40, 38)}, 828: {(18, 30)},
    836: {(28, 23), (28, 24)}, 837: {(38, 23), (38, 24)},
    838: {(28, 22)}, 839: {(38, 22)},
}
SERVICES = (
    (
        "mart", "FR_SAFFRON_CITY_MART", (40, 21),
        [[760, 761, 762, 763], [48, 49, 50, 51], [56, 57, 58, 59], [758, 65, 98, 759]],
        {760: 40, 761: 41, 762: 42, 763: 43, 758: 64, 759: 99},
    ),
    (
        "center", "FR_SAFFRON_CITY_POKEMON_CENTER_1F", (24, 38),
        [
            [764, 765, 766, 774, 767], [72, 73, 74, 75, 391],
            [80, 81, 82, 83, 399], [88, 89, 90, 91, 407], [735, 97, 98, 390, 775],
        ],
        {764: 688, 765: 689, 766: 690, 774: 691, 767: 692, 735: 96, 775: 415},
    ),
)


class Saffron(Rooms):
    def __init__(self):
        super().__init__()
        self.out = OUT / "saffron"
        self.out.mkdir(exist_ok=True)

    def pavement(self, game, pair):
        donor = self.current[game, "gen2", pair, 745, None]["donor"]
        assert (donor["game"], donor["map"], donor["id"], donor["quadrant"]) == (
            "crystal", NATIVE_CITY, 119, 0,
        )
        for mid in PAVEMENT:
            self.source(game, pair, mid)
            cell = self.imp.cell_index(game)[pair, mid]
            assert cell["behavior_hint"] == "MB_NORMAL"
            assert cell["layer_sha256"]["over"] == EMPTY_OVER
            assert all(name in (CITY, CONNECTION) for name, _, _, _ in self.placements(game, pair, mid))
            feature = PREFIX + "street_pavement"
            art = self.native(donor, feature)
            art["overMask"] = "0" * 256
            self.record(
                "native_modules", game, pair, mid, feature, art,
                "Complete ordinary paved Saffron streets and pale surface joins "
                "share the selected original Crystal paving with the surrounding "
                "street. Building walls, fences, signs and steps are separate.",
            )
        return donor

    def tower_origin(self, game):
        definition = self.imp.table(game, "gba/warps")[CITY]
        entrance = next(w for w in definition if w["destMap"] == "FR_SILPH_CO_1F")
        assert (entrance["x"], entrance["y"]) == (33, 30)
        source = self.imp.table("crystal", "maps")[NATIVE_CITY]
        native = next(w for w in source["warps"] if w["destMap"] == "SILPH_CO_1F")
        assert (native["x"], native["y"]) == (18, 21)
        return entrance["x"] - 4, entrance["y"] - len(TOWER) + 1

    def building_placements(self, game, pair, footprint, origin, mids):
        allowed = defaultdict(set)
        for name in (CITY, CONNECTION):
            spec, layout = self.layouts[game, name]
            assert spec["pair"] == pair
            w = layout["width"]
            origins = [
                (i % w, i // w) for i, mid in enumerate(layout["mids"])
                if mid == footprint[0][0] and self.matches_layout(layout, footprint, i % w, i // w)
            ]
            assert len(origins) == 1, (game, name, origins)
            if name == CITY:
                assert origins[0] == origin
            x, y = origins[0]
            allowed[name].update(
                (x + dx, y + dy) for dy in range(len(footprint)) for dx in range(len(footprint[0]))
            )
        for mid in mids:
            assert all(
                (x, y) in allowed[name]
                for name, _, x, y in self.placements(game, pair, mid)
            ), (game, mid)

    def tower_donor(self, mid, x, y):
        if y < 5:
            column = 16 if x == 0 else 23 if x == 8 else 18
            return column, 11 if y == 4 else 10, y in (1, 2, 3)
        if y == 13 and mid in ENTRY_UPPER:
            return ENTRY_UPPER[mid], 20, False
        if y == 14:
            return ENTRY_LOWER[mid], 21, False
        return INTERIOR_COLUMNS[x], 12 if y == 5 else 14, False

    def tower_art(self, floor, column, row, repeat, feature):
        donor = self.gb_at("crystal", NATIVE_CITY, column, row)
        image = self.gb_image(donor)
        parts = []
        mask = []
        for y in range(16):
            sy = 8 + y % 8 if repeat else y
            side = 0
            if column in (16, 23):
                side = 1 if row >= 12 else 4 if row == 10 and sy == 0 else 3
            x = side if column == 16 else 0
            width = 16 - side
            excluded = range(side) if column == 16 else range(16 - side, 16)
            assert all(image.getpixel((i, sy)) == OUTSIDE for i in excluded), (column, row, sy)
            mask.extend(x <= px < x + width for px in range(16))
            last = parts[-1] if parts else None
            if (
                last and last["x"] == x and last["w"] == width
                and last["srcY"] + last["h"] == sy
            ):
                last["h"] += 1
            else:
                parts.append(dict(donor=donor, srcX=x, srcY=sy, x=x, y=y, w=width, h=1))
        art = self.composite(floor, parts, feature)
        art["_objectMask"] = "".join("1" if inside else "0" for inside in mask)
        return art

    def tower(self, game, pair, floor):
        mids = set(mid for line in TOWER for mid in line)
        self.building_placements(game, pair, TOWER, self.tower_origin(game), mids)
        self.feature = PREFIX + "complete_silph_facade"
        self.family = TOWER
        source = Image.new("RGBA", (len(TOWER[0]) * 16, len(TOWER) * 16))
        donors = {}
        for y, line in enumerate(TOWER):
            for x, mid in enumerate(line):
                source.paste(self.source(game, pair, mid), (x * 16, y * 16))
                donor = self.tower_donor(mid, x, y)
                assert donor == donors.setdefault(mid, donor), (game, mid, donor)
        self.whole_hash = catalog.sha(source.tobytes())
        for mid, (x, y, repeat) in donors.items():
            art = self.tower_art(floor, x, y, repeat, self.feature)
            self.add(
                game, pair, mid, self.prepare_art(game, pair, mid, art),
                "The full actual nine-by-fifteen Silph exterior uses its original "
                "Crystal roof, complete left and right facade frames, full glass "
                "window modules, and intact door surround. Only the plain native "
                "eight-pixel roof bands and whole inside window panels repeat. "
                "The doorway stays on the actual FireRed/LeafGreen warp. The "
                "exterior margins expose the selected Saffron pavement.",
            )

    def service_buildings(self, game, pair, floor):
        canonical_pair = self.layouts[game, "FR_VIRIDIAN_CITY"][0]["pair"]
        warps = self.imp.table(game, "gba/warps")[CITY]
        for kind, destination, doorway, layout, missing in SERVICES:
            entrance = next(w for w in warps if w["destMap"] == destination)
            assert (entrance["x"], entrance["y"]) == doorway
            origin = doorway[0] - 2, doorway[1] - len(layout) + 1
            self.building_placements(game, pair, layout, origin, missing)
            self.family = layout
            self.feature = PREFIX + "completed_" + kind
            source = Image.new("RGBA", (len(layout[0]) * 16, len(layout) * 16))
            for y, line in enumerate(layout):
                for x, mid in enumerate(line):
                    source.paste(self.source(game, pair, mid), (x * 16, y * 16))
                    if mid not in missing:
                        previous = self.current[game, "gen2", pair, mid, None]
                        assert previous["role"] in (
                            "classic_gen2_whole_" + kind + "_native_modules",
                            "classic_gen2_whole_center_native_modules",
                        )
            self.whole_hash = catalog.sha(source.tobytes())
            for mid, canonical_mid in missing.items():
                previous = self.current[game, "gen2", canonical_pair, canonical_mid, None]
                assert previous["role"] == "classic_gen2_whole_" + kind + "_native_modules"
                art = self.art_of(previous)
                art.update(role=self.feature, base=floor)
                art["_objectMask"] = "".join(
                    "1" if any(
                        part["x"] <= x < part["x"] + part["w"]
                        and part["y"] <= y < part["y"] + part["h"]
                        for part in art["parts"]
                    ) else "0"
                    for y in range(16) for x in range(16)
                )
                self.add(
                    game, pair, mid, self.prepare_art(game, pair, mid, art),
                    "The complete warp-anchored Saffron service building shares "
                    "the already selected whole Crystal facade. These exact "
                    "missing upper roof and lower frame variants use the same "
                    "approved native modules and matching Saffron pavement.",
                )

    def townhouses(self, game, pair, floor):
        # The closed Saffron houses share the complete native roof and wall
        # modules used in the tall original office. Verify their donor pixels
        # before assembling the wider regional repetition.
        for closed, office in (
            ((4, 8), (16, 10)), ((5, 8), (17, 10)), ((7, 8), (23, 10)),
            ((4, 9), (16, 11)), ((5, 9), (17, 11)), ((7, 9), (23, 11)),
            ((4, 11), (16, 21)), ((5, 11), (17, 21)), ((7, 11), (23, 21)),
        ):
            image = self.gb_image(self.gb_at("crystal", NATIVE_CITY, *closed))
            assert image.tobytes() == self.gb_image(self.gb_at("crystal", NATIVE_CITY, *office)).tobytes()
        warps = self.imp.table(game, "gba/warps")[CITY]
        door_locations = {
            (warp["x"], warp["y"]) for warp in warps
            if "HOUSE" in warp["destMap"] or "FAN_CLUB" in warp["destMap"]
        }
        modules = HOUSE_ROOF | {mid: (*coord, False) for mid, coord in HOUSE_FACADE.items()}
        self.family = [
            [661, 662, 662, 663], [669, 670, 670, 671], [677, 678, 655, 679],
            [664, 665, 667, 668], [672, 673, 675, 676],
        ]
        self.feature = PREFIX + "complete_townhouse_modules"
        original = Image.new("RGBA", (64, 80))
        for y, line in enumerate(self.family):
            for x, mid in enumerate(line):
                original.paste(self.source(game, pair, mid), (x * 16, y * 16))
        self.whole_hash = catalog.sha(original.tobytes())
        for mid, (x, y, repeat) in modules.items():
            self.source(game, pair, mid)
            placements = list(self.placements(game, pair, mid))
            assert placements
            for name, layout, sx, sy in placements:
                assert name in (CITY, CONNECTION)
                if mid == 644 and name == CITY:
                    assert (sx, sy) in door_locations, (game, sx, sy)
                assert self.house_neighbor(layout, sx, sy), (game, name, mid, sx, sy)
            art = self.tower_art(floor, x, y, repeat, self.feature)
            self.add(
                game, pair, mid, self.prepare_art(game, pair, mid, art),
                "The joined Saffron townhouse uses the complete original Crystal "
                "closed-house roof, framed side and interior window modules, "
                "and native base. One repeat of the plain native roof band "
                "preserves the taller source footprint. Actual source house "
                "doors keep the original complete Crystal door and their exact "
                "source warp. All visible exterior margins match the street.",
            )

    def utility_roofs(self, game, pair):
        mids = {mid for line in UTILITY_ROOF for mid in line}
        for name in (CITY, CONNECTION):
            _, layout = self.layouts[game, name]
            w = layout["width"]
            footprint = set()
            for i, mid in enumerate(layout["mids"]):
                x, y = i % w, i // w
                if mid == 641 and self.matches_layout(layout, UTILITY_ROOF, x, y):
                    footprint.update((x + dx, y + dy) for dy in range(3) for dx in range(5))
            actual = {(i % w, i // w) for i, mid in enumerate(layout["mids"]) if mid in mids}
            assert actual == footprint, (game, name, actual - footprint)
        for mid in sorted(mids):
            feature = PREFIX + "whole_utility_roof"
            art = classic_art(self, game, pair, mid, feature, UTILITY_PALETTE, UTILITY_COLORS)
            self.record(
                "geometry", game, pair, mid, feature, art,
                "The complete regional five-column utility roof keeps its full "
                "original casing, rooftop unit, frame, and vent pattern. The "
                "corresponding Crystal city has ordinary roofs without this "
                "complete regional utility feature. Four exact native Crystal "
                "roof shades unify it with the adjacent native facade.",
            )

    def fences(self, game, pair, floor):
        donor = self.gb_ref("crystal", NATIVE_CITY, 119, 2)
        image = self.gb_image(donor)
        assert image.crop((0, 0, 8, 16)).tobytes() == image.crop((8, 0, 16, 16)).tobytes()
        outside = exterior(image, {OUTSIDE})
        left = [(x, y) not in outside and x < 8 for y in range(16) for x in range(16)]
        self.feature = PREFIX + "complete_street_fence"
        self.family = [[792, 793, 793], [800, 745, 745]]
        source = Image.new("RGBA", (48, 32))
        for y, line in enumerate(self.family):
            for x, mid in enumerate(line):
                source.paste(self.source(game, pair, mid), (x * 16, y * 16))
        self.whole_hash = catalog.sha(source.tobytes())
        for mid, columns in FENCE_COLUMNS.items():
            self.source(game, pair, mid)
            for name, _, _, _ in self.placements(game, pair, mid):
                assert name in (CITY, CONNECTION), (game, mid, name)
            parts = [
                dict(donor=donor, srcX=rect["x"], srcY=rect["y"],
                     w=rect["w"], h=rect["h"], x=column + rect["x"], y=rect["y"])
                for column in columns for rect in runs(left)
            ]
            mask = "".join(
                "1" if any(0 <= x-column < 8 and left[y * 16 + x-column] for column in columns) else "0"
                for y in range(16) for x in range(16)
            )
            art = self.composite(floor, parts, self.feature)
            art["_objectMask"] = mask
            self.add(
                game, pair, mid, self.prepare_art(game, pair, mid, art),
                "The original complete Crystal Saffron wooden pickets form the "
                "joined horizontal runs, ends and side returns of this street "
                "fence. Centered end posts and vertical posts share their "
                "actual alignment. Only the exterior ground around the native "
                "picket is transparent over the selected street pavement.",
            )

    def gates(self, game, pair, floor):
        warps = self.imp.table(game, "gba/warps")[CITY]
        expected = {(34, 5), (35, 5), (34, 46), (35, 46), (8, 27), (58, 27)}
        assert {(w["x"], w["y"]) for w in warps if "ENTRANCE" in w["destMap"]} == expected
        self.feature = PREFIX + "complete_gate_exterior"
        self.family = [
            [68, 69, 69, 69, 69, 70], [76, 77, 77, 77, 77, 78],
            [387, 388, 388, 388, 388, 389], [438, 437, 437, 437, 437, 439],
            [92, 392, 393, 393, 394, 94], [100, 400, 401, 401, 402, 102],
        ]
        _, city = self.layouts[game, CITY]
        assert self.matches_layout(city, self.family, 32, 0)
        image = Image.new("RGBA", (96, 96))
        for y, line in enumerate(self.family):
            for x, mid in enumerate(line):
                image.paste(self.source(game, pair, mid), (x * 16, y * 16))
        self.whole_hash = catalog.sha(image.tobytes())
        for mid in sorted(set(GATE_SHELL) | set(GATE_FRONT) | set(GATE_FLOOR) | {376, 377, 378, 401, 408, 409, 410}):
            for name, _, x, y in self.placements(game, pair, mid):
                assert name in (CITY, CONNECTION)
                if name == CONNECTION:
                    x, y = x + 10, y + 7
                assert mid in (238, 239) or any(
                    x0 <= x < x1 and y0 <= y < y1 for x0, y0, x1, y1 in GATE_RECTANGLES
                ), (
                    game, name, mid, x, y,
                )
            art = self.gate_art(game, pair, mid, floor)
            self.add(
                game, pair, mid, self.prepare_art(game, pair, mid, art),
                "Complete original Crystal Gate roof, edge frames, front wall "
                "and both correctly facing side thresholds are used at native "
                "scale. The wide front entrance repeats its plain inner "
                "opening, with the jambs placed only at the outside. All four "
                "real gate approaches preserve their original warp positions.",
            )

    def gate_art(self, game, pair, mid, floor):
        if mid == 211:
            art = self.native(floor, self.feature)
            art["overMask"] = "0" * 256
            return art
        if mid in (238, 239):
            source = self.current[game, "gen2", pair, 245 if mid == 238 else 244, None]
            assert source["role"].startswith("classic_gen2_complete_low_vertical_curb_")
            art = self.art_of(source)
            art.update(base=floor, role=self.feature)
            return art
        if mid in (312, 316, 397, 398):
            left = mid in (312, 397)
            donor = self.gb_at("crystal", "ROUTE_16", 10 if left else 13, 5 if mid in (312, 316) else 4)
            x = 12 if left else 0
            art = self.composite(floor, [
                dict(donor=donor, srcX=2 if left else 10, srcY=0, w=4, h=16, x=x, y=0),
            ], self.feature)
            art["_objectMask"] = ("0" * 12 + "1" * 4 if x else "1" * 4 + "0" * 12) * 16
            return art
        if mid in GATE_SHELL:
            donor = self.gb_at("crystal", "ROUTE_16", *GATE_SHELL[mid])
            if mid in (76, 77, 78):
                # The taller source roof has one extra blank eight-pixel
                # shingle band between the complete native cap and eave.
                parts = [
                    dict(donor=donor, srcX=0, srcY=8, w=16, h=8, x=0, y=y)
                    for y in (0, 8)
                ]
                art = self.composite(floor, parts, self.feature)
                art["_objectMask"] = "1" * 256
                return art
        elif mid in GATE_FRONT:
            donor = self.gb_at("crystal", "ROUTE_6", *GATE_FRONT[mid])
            if mid in (400, 402):
                door = self.gb_at("crystal", "ROUTE_6", 6, 1)
                parts = [
                    dict(donor=donor, srcX=0, srcY=0, w=16, h=16, x=0, y=0),
                    dict(donor=door, srcX=0 if mid == 400 else 12, srcY=0,
                         w=4, h=16, x=12 if mid == 400 else 0, y=0),
                ]
                art = self.composite(floor, parts, self.feature)
                art["_objectMask"] = "1" * 256
                return art
        elif mid == 401:
            door = self.gb_at("crystal", "ROUTE_6", 6, 1)
            return self.gate_plain_center(floor, door)
        else:
            if mid in (376, 377, 378):
                donor = self.gb_at("crystal", NATIVE_CITY, 16, 33)
                position = mid - 376
            else:
                donor = self.gb_ref("crystal", "UNION_CAVE_1F", 18, 3)
                position = mid - 408
                if position == 1:
                    return self.gate_plain_center(floor, donor)
            if position != 1:
                x = 8 if position == 0 else 0
                art = self.composite(floor, [
                    dict(donor=donor, srcX=8-x, srcY=0, w=8, h=16, x=x, y=0),
                ], self.feature)
                art["_objectMask"] = ("0" * 8 + "1" * 8 if x else "1" * 8 + "0" * 8) * 16
                return art
        art = self.native(donor, self.feature)
        art["_objectMask"] = "1" * 256
        return art

    def gate_plain_center(self, floor, donor):
        parts = [
            dict(donor=donor, srcX=8, srcY=0, w=1, h=16, x=x, y=0)
            for x in range(16)
        ]
        art = self.composite(floor, parts, self.feature)
        art["_objectMask"] = "1" * 256
        return art

    def tree_overlaps(self, game, pair, floor):
        facade = {742: (16, 14), 743: (23, 14), 750: (17, 14), 751: (22, 14)}
        for mid in sorted(set(facade) | {782, 783}):
            self.source(game, pair, mid)
            for name, layout, x, y in self.placements(game, pair, mid):
                assert name in (CITY, CONNECTION)
                w = layout["width"]
                below = layout["mids"][(y+1)*w + x]
                assert below in (30, 31), (game, name, mid, below)
                key = game, "gen2", pair, below, None
                assert "tree" in (self.rows.get(key) or self.current[key])["role"]
            self.whole_source(game, pair, [[mid]], PREFIX + "tree_overlap")
            self.feature = PREFIX + "whole_tree_overlap"
            if mid in facade:
                column, row = facade[mid]
                art = self.tower_art(floor, column, row, False, self.feature)
            else:
                art = self.native(floor, self.feature)
                art["overMask"] = "0" * 256
            self.add(
                game, pair, mid, self.prepare_art(game, pair, mid, art),
                "The old upper leaf sliver is above the same complete native "
                "Crystal tree in every occurrence. This exposed region restores "
                "the selected street or the correct interior/outer native house "
                "window module around the full tree already drawn below.",
            )

    def dojo(self, game, pair, floor):
        entrance = next(
            w for w in self.imp.table(game, "gba/warps")[CITY]
            if w["destMap"] == "FR_SAFFRON_CITY_DOJO"
        )
        native = next(
            w for w in self.imp.table("crystal", "maps")[NATIVE_CITY]["warps"]
            if w["destMap"] == "FIGHTING_DOJO"
        )
        assert (entrance["x"], entrance["y"], native["x"], native["y"]) == (40, 12, 26, 3)
        self.building_placements(game, pair, DOJO, (37, 8), {m for row in DOJO for m in row})
        self.feature = PREFIX + "complete_fighting_dojo"
        self.family = DOJO
        donors = {}
        source = Image.new("RGBA", (len(DOJO[0]) * 16, len(DOJO) * 16))
        for row, mids in enumerate(DOJO):
            for column, mid in enumerate(mids):
                source.paste(self.source(game, pair, mid), (column * 16, row * 16))
                dx = column
                if row < 3 and 0 < dx < 5:
                    dx = 2
                if row == 4 and dx in (3, 4):
                    dx = 7 - dx
                donor = (22 + dx, max(0, row - 1), row == 1)
                assert donors.setdefault(mid, donor) == donor
        self.whole_hash = catalog.sha(source.tobytes())
        for mid, (column, row, repeat) in sorted(donors.items()):
            donor = self.gb_at("crystal", NATIVE_CITY, column, row)
            image = self.gb_image(donor)
            parts = []
            mask = []
            for y in range(16):
                sy = 8 + y % 8 if repeat else y
                left, right = 0, 16
                if column == 22:
                    while image.getpixel((left, sy)) == OUTSIDE:
                        left += 1
                if column == 27:
                    while image.getpixel((right - 1, sy)) == OUTSIDE:
                        right -= 1
                mask.extend(left <= x < right for x in range(16))
                last = parts[-1] if parts else None
                if (
                    last and last["x"] == left and last["w"] == right - left
                    and last["srcY"] + last["h"] == sy
                ):
                    last["h"] += 1
                else:
                    parts.append(dict(donor=donor, srcX=left, srcY=sy,
                                      x=left, y=y, w=right - left, h=1))
            art = self.composite(floor, parts, self.feature)
            art["_objectMask"] = "".join("1" if pixel else "0" for pixel in mask)
            self.add(
                game, pair, mid, self.prepare_art(game, pair, mid, art),
                "The original complete Crystal Fighting Dojo keeps its native "
                "roof edge, sign, windows and doorway. The additional source "
                "roof height repeats an interior eight-pixel band. The complete "
                "door and neighboring interior wall exchange positions to align "
                "the door with the actual FireRed and LeafGreen warp.",
            )

    @staticmethod
    def detail_mask(parts):
        return "".join(
            "1" if any(
                p["x"] <= x < p["x"] + p["w"] and p["y"] <= y < p["y"] + p["h"]
                for p in parts
            ) else "0"
            for y in range(16) for x in range(16)
        )

    def street_details(self, game, pair, floor):
        ground = self.current[game, "gen2", pair, 8, None]["donor"]
        assert (ground["map"], ground["id"], ground["quadrant"]) == ("PALLET_TOWN", 1, 0)
        for mid, locations in STREET_DETAILS.items():
            positions = list(self.placements(game, pair, mid))
            assert {(x, y) for n, _, x, y in positions if n == CITY} == locations
            assert all(
                name == CITY or name == CONNECTION and (x + 10, y + 7) in locations
                for name, _, x, y in positions
            )
            self.whole_source(game, pair, [[mid]], "saffron_detail")
            art, detail = self.street_detail_art(game, pair, mid, ground, floor, positions)
            self.feature = PREFIX + detail
            art["role"] = self.feature
            self.add(
                game, pair, mid, self.prepare_art(game, pair, mid, art),
                "The actual Saffron street detail is reviewed in every city "
                "and mirrored connection placement. Complete native Crystal "
                "stone, fence, curb, tree, roof and sign pixels meet the "
                "selected Saffron paving or original native Kanto field.",
            )

    def street_detail_art(self, game, pair, mid, ground, floor, positions):
        parts = []
        base = ground
        if mid == 142:
            donor = self.gb_ref("crystal", "ROUTE_1", 26, 3)
            grass = {(115, 206, 165), (66, 181, 140)}
            source = self.source(game, pair, mid)
            for p in runs([px[:3] not in grass for px in source.get_flattened_data()]):
                # Rock occupies the full lower half of the original ledge.
                # Reuse the same eight-pixel mineral pattern up the side.
                for y in range(p["y"], p["y"] + p["h"]):
                    parts.append(dict(donor=donor, srcX=p["x"], srcY=8 + y % 8,
                                      x=p["x"], y=y, w=p["w"], h=1))
            detail = "stone_ledge_end"
        elif mid in (236, 237):
            curb_mid = 244 if mid == 236 else 245
            curb = self.current[game, "gen2", pair, curb_mid, None]
            assert curb["role"].startswith("classic_gen2_complete_low_vertical_curb_")
            parts.extend(curb["parts"])
            donor = self.gb_ref("crystal", NATIVE_CITY, 119, 2)
            image = self.gb_image(donor)
            outside = exterior(image, {OUTSIDE})
            parts.extend(
                dict(donor=donor, srcX=p["x"], srcY=p["y"], **p)
                for p in runs([(x, y) not in outside for y in range(16) for x in range(16)])
            )
            detail = "fence_and_curb_junction"
        elif mid in (246, 247):
            x = 8 if mid == 246 else 0
            donor = self.gb_ref("crystal", NATIVE_CITY, 69 if x else 68, 3 if x else 2)
            parts.append(dict(donor=donor, srcX=x, srcY=0, x=x, y=0, w=8, h=16))
            detail = "lower_curb_end"
        elif mid == 732:
            for _, layout, x, y in positions:
                assert layout["mids"][y * layout["width"] + x + 1] == 733
            return self.tower_art(floor, 16, 10, False, ""), "complete_roof_corner"
        elif mid in (776, 777, 778, 779):
            top = 28 + mid % 2
            for _, layout, x, y in positions:
                assert layout["mids"][(y - 1) * layout["width"] + x] == top
                assert layout["mids"][(y + 1) * layout["width"] + x] in (669, 670, 671)
            tree = self.current[game, "gen2", pair, top - 6, None]
            assert tree["role"].startswith("classic_gen2_verified_complete_park_tree32_")
            roof = self.tower_art(floor, (16, 17, 18, 23)[mid - 776], 10, False, "")
            for row, offset in ((tree, 0), (roof, 8)):
                parts.extend(
                    dict(p, y=p["y"] + offset, h=min(p["h"], 8 - p["y"]))
                    for p in row["parts"] if p["y"] < 8
                )
            base = floor
            detail = "tree_and_complete_roof_join"
        elif mid in (790, 791):
            for _, layout, x, y in positions:
                assert layout["mids"][(y + 1) * layout["width"] + x] in (30, 31)
            source = self.source(game, pair, mid)
            paving = {(181, 181, 165), (206, 206, 189), (222, 222, 206)}
            parts = [
                dict(donor=floor, srcX=p["x"], srcY=p["y"], **p)
                for p in runs([px[:3] in paving for px in source.get_flattened_data()])
            ]
            detail = "street_to_tree_lawn"
        elif mid in (807, 815, 828):
            base = floor
            if mid == 807:
                for _, layout, x, y in positions:
                    assert layout["mids"][(y + 1) * layout["width"] + x] == 815
            else:
                donor = self.gb_at("crystal", NATIVE_CITY, 25, 29)
                assert (donor["id"], donor["quadrant"]) == (86, 3)
                image = self.gb_image(donor)
                outside = exterior(image, {OUTSIDE})
                parts = [
                    dict(donor=donor, srcX=p["x"], srcY=p["y"], **p)
                    for p in runs([(x, y) not in outside for y in range(16) for x in range(16)])
                ]
            detail = "complete_street_sign"
        else:
            assert mid in (836, 837, 838, 839)
            base = floor
            if mid in (838, 839):
                for _, layout, x, y in positions:
                    assert layout["mids"][(y + 1) * layout["width"] + x] == mid - 2
            donor = self.gb_ref("crystal", NATIVE_CITY, 39 if mid < 838 else 73, 0)
            parts.append(dict(donor=donor, srcX=0, srcY=0, x=4, y=0, w=8, h=16))
            detail = "complete_silph_side_rail"
        art = self.composite(base, parts, "") if parts else self.native(base, "")
        art["_objectMask"] = "0" * 256 if mid in (790, 791) else self.detail_mask(parts)
        return art, detail

    def scene_coverage(self):
        proof = []
        for game in self.games:
            for name in (CITY, CONNECTION):
                spec, layout = self.layouts[game, name]
                keys = [(game, "gen2", spec["pair"], mid, None) for mid in layout["mids"]]
                missing = sorted({
                    key[3] for key in keys
                    if key not in self.replacements and key not in self.current
                    and (key not in self.rows or self.rows[key]["role"].startswith(PREFIX))
                })
                assert not missing, (game, name, missing)
                proof.append(dict(game=game, map=name, cells=len(keys), covered=len(keys)))
        (self.out / "scene-coverage.json").write_text(json.dumps(proof, indent=2) + "\n")

    @staticmethod
    def house_neighbor(layout, x, y):
        w, h = layout["width"], layout["height"]
        return any(
            0 <= x + dx < w and 0 <= y + dy < h
            and layout["mids"][(y + dy) * w + x + dx] in HOUSE_NEIGHBORS
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1))
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    options = parser.parse_args()
    review = Saffron()
    review.stage()
    for game in review.games:
        pair = review.layouts[game, CITY][0]["pair"]
        floor = review.pavement(game, pair)
        review.tower(game, pair, floor)
        review.service_buildings(game, pair, floor)
        review.townhouses(game, pair, floor)
        review.utility_roofs(game, pair)
        review.fences(game, pair, floor)
        review.gates(game, pair, floor)
        review.tree_overlaps(game, pair, floor)
        review.dojo(game, pair, floor)
        review.street_details(game, pair, floor)
    review.scene_coverage()
    review.previews((CITY, CONNECTION))
    decisions = json.loads(DECISIONS.read_text())
    for section, records in review.frozen.items():
        decisions[section] = [
            row for row in decisions.get(section, [])
            if not row.get("feature", "").startswith(PREFIX)
        ] + records
    if options.freeze:
        DECISIONS.write_text(json.dumps(decisions, indent=2) + "\n")
    cells = sum(sum(u["count"] for u in review.usage[g, p, m]) for g, _, p, m, _ in review.replacements)
    print(json.dumps(dict(rows=len(review.replacements), cells=cells, frozen=options.freeze)))


if __name__ == "__main__":
    main()
