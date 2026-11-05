"""Use Saffron's complete native Crystal Silph facade and street surfaces."""

import argparse
import json
from collections import defaultdict

from PIL import Image

import catalog
from classic_geometry_review import art as classic_art
from reverse_gen2_kanto_final import DECISIONS, OUT
from reverse_gen2_kanto_room_materials import EMPTY_OVER, Rooms


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
