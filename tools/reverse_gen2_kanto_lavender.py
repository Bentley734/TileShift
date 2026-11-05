"""Review the original Crystal Route 12 boardwalk and Lavender atlas families."""

import argparse
from collections import Counter
import json

import catalog
import preview
import reverse_gen2_kanto_final as final
from classic_geometry_review import art as classic_art
from gb_theme_animation import frames
from reverse_gen2_kanto_final import DECISIONS, OUT, ROOT
from reverse_gen2_kanto_room_materials import Rooms
from reverse_gen2_kanto_safari import Safari
from reverse_kanto_review import exterior


PREFIX = "kanto_lavender_"
PAIR = {"firered": "general__rom_082d4b0c", "leafgreen": "general__rom_082d4aec"}
ROUTE_12 = "FR_ROUTE_12"
ROUTE_13 = "FR_ROUTE_13"
ROUTE_8 = "FR_ROUTE_8"
TOWN = "FR_LAVENDER_TOWN"
ROUTE_10 = "FR_ROUTE_10"
BRIDGE_DECK = (
    752, 753, 754, 755, 756, 757, 760, 762, 764, 765, 768, 769, 770, 772, 773,
    784, 785, 786, 787, 788, 789, 835, 837, 838, 839, 840, 841, 842, 843, 847,
)
BRIDGE_BELOW = (776, 777, 778, 779)
ROCK = {(90, 58, 66), (123, 74, 74), (148, 107, 107), (189, 148, 140), (222, 197, 165)}
GATE = (68, 69, 70, 76, 77, 78, 92, 94, 100, 101, 102, 312, 316, 320, 324, 328, 332,
        387, 388, 389, 392, 393, 394, 397, 398, 400, 401, 402, 437, 438, 439)
FISH_HOUSE = (
    (758, 45, 45, 45, 759),
    (52, 53, 54, 54, 55),
    (60, 61, 66, 67, 63),
)
HOUSE_FACE = ((656, 657, 657, 657, 660), (664, 665, 666, 667, 668), (672, 673, 674, 675, 676))
HOUSE_CAP = ((648, 649, 650, 651, 652), (648, 641, 642, 643, 652))
PLANT = (
    (645, 805, 646, 805, 646, 805, 646, 805, 647),
    (812, 813, 804, 813, 804, 813, 804, 813, 814),
    (661, 662, 659, 662, 659, 662, 659, 662, 663),
    (724, 766, 792, 793, 793, 793, 795, 766, 725),
    (732, 774, 800, 801, 801, 801, 803, 774, 733),
    (740, 782, 808, 809, 794, 810, 811, 782, 741),
)
DOME = (
    (681, 682, 683, 684, 685, 686, 687),
    (689, 690, 691, 692, 693, 694, 695),
    (697, 698, 699, 700, 701, 702, 703),
    (705, 706, 707, 708, 709, 710, 711),
    (713, 714, 715, 716, 717, 718, 719),
)
TOWER = (
    (721, 722, 723, 723, 723, 726, 727),
    (729, 722, 723, 723, 723, 726, 735),
    (729, 722, 723, 723, 723, 726, 735),
    (737, 738, 739, 739, 739, 742, 743),
    (745, 746, 747, 747, 747, 750, 751),
    (807, 767, 824, 825, 826, 767, 820),
    (815, 775, 832, 783, 834, 775, 821),
)
DOME_PALETTE = ((58, 58, 58), (107, 107, 107), (173, 173, 173), (222, 255, 222))
DOME_FIELD = {(66, 181, 140), (115, 206, 165), (140, 222, 189), (165, 230, 197)}
DOME_CLIFF = ROCK | {(239, 214, 197)}
DOME_COLORS = {
    (66, 74, 107): DOME_PALETTE[0], (90, 115, 90): DOME_PALETTE[0],
    (107, 140, 107): DOME_PALETTE[1], (132, 165, 132): DOME_PALETTE[1],
    (140, 173, 140): DOME_PALETTE[2], (148, 181, 148): DOME_PALETTE[2],
    (173, 173, 107): DOME_PALETTE[1], (181, 206, 181): DOME_PALETTE[3],
    (197, 222, 197): DOME_PALETTE[3], (214, 214, 148): DOME_PALETTE[2],
    (230, 247, 239): DOME_PALETTE[3], (255, 255, 255): DOME_PALETTE[3],
    **{color: DOME_PALETTE[0] for color in DOME_FIELD | DOME_CLIFF},
}
SHARED_NATIVE = (
    132, 142, 151, 196, 205, 207, 211, 214, 215, 236, 237, 238, 246,
    252, 253, 258, 259, 260, 261, 264, 265, 290, 296, 297, 307,
)
SAND_JOIN = (208, 209, 210, 216, 218, 224, 226, 254, 255, 263)
SAND_GBA = {(173, 148, 74), (197, 173, 107), (214, 197, 132), (230, 222, 165)}
LAND_CLIFF = {
    161: (108, 0), 180: (109, 2), 181: (109, 2),
    497: (108, 0), 498: (109, 1), 499: (108, 0), 500: (109, 1),
    527: (108, 0), 535: (109, 1), 720: (109, 2), 845: (109, 2),
}


class Lavender(Rooms):
    adjacent = staticmethod(Safari.adjacent)
    previous = Safari.previous
    mask_parts = staticmethod(Safari.mask_parts)

    def __init__(self):
        super().__init__()
        self.out = OUT / "lavender"
        self.out.mkdir(exist_ok=True)
        self.frame_proof = []

    def emit_detail(self, game, pair, mid, art, feature, evidence):
        self.whole_source(game, pair, [[mid]], f"lavender_{feature}_{mid}")
        self.feature = PREFIX + feature
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

    def assert_animated_parts(self, game, mid, art, original):
        rendered = preview.replacement_frames(self.cache, art, self.packed, ROOT)
        for frame, water in zip(rendered, original, strict=True):
            expected = water.copy()
            for p in art["parts"][1:]:
                x, y = p["srcX"], p["srcY"]
                image = self.gb_image(p["donor"])
                expected.paste(image.crop((x, y, x+p["w"], y+p["h"])), (p["x"], p["y"]))
            assert frame.tobytes() == expected.tobytes(), (game, mid)
        self.frame_proof.append(dict(game=game, mid=mid, hashes=[catalog.sha(i.tobytes()) for i in rendered]))

    def bridge(self, game, pair):
        deck = self.gb_at("crystal", "ROUTE_12", 8, 2)
        deck_pixels = set(self.gb_image(deck).get_flattened_data())
        assert 2 <= len(deck_pixels) <= 4 and all(p[3] == 255 for p in deck_pixels), deck_pixels
        assert any(p[0] > p[1] > p[2] for p in deck_pixels)
        threshold = self.gb_at("crystal", "SAFFRON_CITY", 16, 33)
        for mid in BRIDGE_DECK:
            placements = list(self.placements(game, pair, mid))
            assert all(name in (ROUTE_12, ROUTE_13) for name, _, _, _ in placements)
            cell = self.imp.cell_index(game)[pair, mid]
            assert cell["behavior_hint"] == ("MB_SOUTH_ARROW_WARP" if mid == 785 else "MB_NORMAL")
            if mid == 785:
                assert [(name, x, y) for name, _, x, y in placements] == [(ROUTE_12, 14, 15)]
            art = self.native(threshold if mid in (785, 786) else deck, "")
            self.emit_detail(
                game, pair, mid, art, "complete_crystal_route_12_boardwalk_deck",
                "The full original Crystal Route 12 brick deck is used "
                "through each connected bridge section and landing. The "
                "original source orientation, width, platform boundaries "
                "and passable route remain. The actual south warp keeps a "
                "complete native Crystal outdoor entrance threshold.",
            )

        water_row = self.previous(game, pair, 299)
        assert water_row["animationCategory"] == "water"
        animation = water_row["animation"]
        water = water_row["parts"][0]["donor"]
        native_frames = frames(self.cache, water, animation, self.packed)
        assert len({catalog.sha(i.tobytes()) for i in native_frames}) > 1
        support = self.gb_at("crystal", "ROUTE_12", 7, 8)
        native = self.gb_image(support)
        wet = exterior(native, {p for p in native.get_flattened_data() if p[2] > max(p[0], p[1])})
        assert 0 < len(wet) < 256
        supports = self.mask_parts(
            support, [(x, y) not in wet for y in range(16) for x in range(16)],
        )
        cliff = self.gb_ref("crystal", "ROUTE_27", 108, 0)
        for mid in BRIDGE_BELOW:
            placements = list(self.placements(game, pair, mid))
            assert all(name in (ROUTE_12, ROUTE_13) for name, _, _, _ in placements)
            assert all(
                self.adjacent(layout, x, y, "above") in {*BRIDGE_DECK, 100, 102}
                for _, layout, x, y in placements
            )
            assert self.imp.cell_index(game)[pair, mid]["behavior_hint"] == "MB_OCEAN_WATER"
            parts = [dict(donor=water, x=0, y=0, w=16, h=16, animated=True)]
            if mid == 779:
                source = self.source(game, pair, mid)
                mask = [px[:3] in ROCK for px in source.get_flattened_data()]
                assert 0 < sum(mask) < 256
                parts.extend(self.mask_parts(cliff, mask))
            parts.extend(supports)
            assert len(parts) <= 32
            art = self.composite(None, parts, "")
            art.update(animated=True, animation=animation, animationCategory="water", overMask="0"*256)
            self.assert_animated_parts(game, mid, art, native_frames)
            self.emit_detail(
                game, pair, mid, art, "complete_crystal_route_12_boardwalk_support",
                "Every source deck underside uses the complete native "
                "Crystal Route 12 bridge support. Its exterior pixels "
                "reveal every frame of the selected Crystal water program. "
                "The shoreline version retains its distinct rock outline.",
            )

    def route_gates(self, game, pair):
        s_pair = self.layouts[game, "FR_SAFFRON_CITY"][0]["pair"]
        cells = self.imp.cell_index(game)
        warps = self.imp.table(game, "gba/warps")
        for name, destinations in (
            (ROUTE_8, {(7, 10, "FR_ROUTE_8_WEST_ENTRANCE"), (13, 4, "FR_UNDERGROUND_PATH_EAST_ENTRANCE")}),
            (ROUTE_12, {(14, 15, "FR_ROUTE_12_NORTH_ENTRANCE_1F"),
                        (15, 15, "FR_ROUTE_12_NORTH_ENTRANCE_1F"),
                        (14, 21, "FR_ROUTE_12_NORTH_ENTRANCE_1F")}),
        ):
            assert destinations <= {(w["x"], w["y"], w["destMap"]) for w in warps[name]}
        field = self.previous(game, pair, 8)["donor"]
        cliff = self.previous(game, pair, 113)["donor"]
        for mid in GATE:
            uses = list(self.placements(game, pair, mid))
            assert all(n in (ROUTE_8, ROUTE_12) for n, _, _, _ in uses)
            native = cells[pair, mid]
            other = cells[s_pair, mid]
            assert all(native[k] == other[k] for k in ("pixel_sha256", "behavior", "layer_sha256"))
            art = self.art_of(self.previous(game, s_pair, mid))
            if art.get("base"):
                art["base"] = field
            self.emit_detail(
                game, pair, mid, art, "native_complete_route_gate",
                "The complete matching original Crystal gate joins the "
                "same verified roof, window, doorway and framed side modules "
                "as the original gate used in Saffron. Both actual source "
                "routes use the correct facing thresholds.",
            )
        for mid, x in ((827, 10), (828, 11), (829, 13)):
            assert all(n == ROUTE_8 and y == 1 and 12 <= x <= 15 for n, _, x, y in self.placements(game, pair, mid))
            donor = self.gb_at("crystal", "ROUTE_16", x, 4)
            parts = [dict(donor=donor, srcX=0, srcY=0, x=0, y=8, w=16, h=8)]
            self.emit_detail(
                game, pair, mid, self.composite(cliff, parts, ""), "native_underground_gate_roof_edge",
                "The actual underground path entrance keeps its complete "
                "native slate roof cap, with the same original native cliff "
                "surface visible immediately above it.",
            )
        for mid, x in ((84, 10), (103, 11), (85, 12), (86, 13)):
            assert all(n == ROUTE_8 and y == 3 for n, _, _, y in self.placements(game, pair, mid))
            donor = self.gb_at("crystal", "ROUTE_16", x, 6)
            self.emit_detail(
                game, pair, mid, self.native(donor, ""), "native_underground_gate_window_frame",
                "The complete original Crystal window and outer frame "
                "stay aligned above the actual underground path doorway.",
            )

    def fishing_house(self, game, pair):
        _, scene = self.layouts[game, ROUTE_12]
        assert self.matches_layout(scene, [list(line) for line in FISH_HOUSE], 11, 84)
        gate = self.imp.table(game, "gba/warps")[ROUTE_12]
        assert any((w["x"], w["y"], w["destMap"]) == (12, 86, "FR_ROUTE_12_FISHING_HOUSE") for w in gate)
        native = self.imp.table("crystal", "maps")["ROUTE_12"]["warps"]
        assert any((w["x"], w["y"], w["destMap"]) == (11, 33, "ROUTE_12_SUPER_ROD_HOUSE") for w in native)
        field = self.previous(game, pair, 8)["donor"]
        refs = {
            758: (10, 32), 45: (12, 32), 759: (13, 32),
            52: (10, 32), 53: (11, 32), 54: (12, 32), 55: (13, 32),
            60: (10, 33), 61: (11, 33), 66: (12, 33), 67: (12, 33), 63: (13, 33),
        }
        for row, mids in enumerate(FISH_HOUSE):
            for mid in dict.fromkeys(mids):
                uses = list(self.placements(game, pair, mid))
                assert all(
                    n == ROUTE_12 and y == 84+row and 11 <= x <= 15
                    or mid == 61 and (n, x, y) == (ROUTE_8, 13, 4)
                    for n, _, x, y in uses
                )
                x, y = refs[mid]
                donor = self.gb_at("crystal", "ROUTE_12", x, y)
                if row == 0:
                    parts = [dict(donor=donor, srcX=0, srcY=0, x=0, y=8, w=16, h=8)]
                    art = self.composite(field, parts, "")
                elif row == 1:
                    parts = [
                        dict(donor=donor, srcX=0, srcY=7, x=0, y=i, w=16, h=1)
                        for i in range(8)
                    ]
                    parts.append(dict(donor=donor, srcX=0, srcY=8, x=0, y=8, w=16, h=8))
                    art = self.composite(field, parts, "")
                else:
                    art = self.native(donor, "")
                self.emit_detail(
                    game, pair, mid, art, "complete_native_route_12_fishing_house",
                    "The complete original Crystal Route 12 Fishing House "
                    "uses its native roof, windows and door. Only the plain "
                    "roof width and inside window pattern extend. The "
                    "actual doorway remains aligned with the source warp.",
                )

    def native_building_part(self, field, donor, rows, outside=None):
        image = self.gb_image(donor)
        parts = []
        excluded = exterior(image, outside) if outside is not None else set()
        for y, sy in enumerate(rows):
            if sy is None:
                continue
            x = 0
            while x < 16:
                if (x, sy) in excluded:
                    x += 1
                    continue
                end = x + 1
                while end < 16 and (end, sy) not in excluded:
                    end += 1
                previous = next(
                    (p for p in parts if p["x"] == x and p["w"] == end-x
                     and p["y"]+p["h"] == y and p["srcY"]+p["h"] == sy),
                    None,
                )
                if previous:
                    previous["h"] += 1
                else:
                    parts.append(dict(donor=donor, srcX=x, srcY=sy, x=x, y=y, w=end-x, h=1))
                x = end
        assert 0 < len(parts) <= 32
        return self.composite(field, parts, "")

    def lavender_houses(self, game, pair):
        _, scene = self.layouts[game, TOWN]
        warps = self.imp.table(game, "gba/warps")[TOWN]
        for x, y, caps, room in (
            (10, 11, HOUSE_CAP[0], "VOLUNTEER_POKEMON_HOUSE"),
            (5, 16, HOUSE_CAP[0], "HOUSE1"),
            (10, 16, HOUSE_CAP[1], "HOUSE2"),
        ):
            assert any((w["x"], w["y"], w["destMap"]) == (x, y, "FR_LAVENDER_TOWN_"+room) for w in warps)
            assert self.matches_layout(scene, [list(row) for row in (caps, *HOUSE_FACE)], x-2, y-3)
        field = self.previous(game, pair, 8)["donor"]
        plain = self.gb_at("crystal", "LAVENDER_TOWN", 3, 8)
        outside = set(self.gb_image(plain).get_flattened_data())
        donors = {
            648: (4, 8, "cap"), 649: (5, 8, "cap"), 650: (6, 8, "cap"),
            651: (6, 8, "cap"), 652: (7, 8, "cap"),
            641: (5, 8, "cap"), 642: (6, 8, "cap"), 643: (6, 8, "cap"),
            656: (4, 8, "fill"), 657: (6, 8, "fill"), 660: (7, 8, "fill"),
            664: (4, 8, "edge"), 665: (5, 8, "edge"), 666: (6, 8, "edge"),
            667: (6, 8, "edge"), 668: (7, 8, "edge"),
            672: (4, 9, "body"), 673: (6, 9, "body"), 674: (5, 9, "body"),
            675: (6, 9, "body"), 676: (7, 9, "body"),
        }
        rows = {
            "cap": [None]*8 + list(range(8)),
            "fill": [7]*16,
            "edge": [7]*8 + list(range(8, 16)),
            "body": list(range(16)),
        }
        for mid, (x, y, band) in donors.items():
            assert all(name == TOWN for name, _, _, _ in self.placements(game, pair, mid))
            donor = self.gb_at("crystal", "LAVENDER_TOWN", x, y)
            art = self.native_building_part(field, donor, rows[band], outside if x in (4, 7) else None)
            self.emit_detail(
                game, pair, mid, art, "complete_native_lavender_home",
                "The complete original Crystal Lavender house has all its "
                "purple roof, native window frames and intact door modules. "
                "The extra source height extends a plain interior roof row "
                "without another eave. Each actual source door stays aligned.",
            )

        pave = self.gb_at("crystal", "LAVENDER_TOWN", 10, 7)
        assert all(r >= b or r == g == b for r, g, b, _ in self.gb_image(pave).get_flattened_data())
        for mid in (354, 355, 356, 370, 371, 372):
            assert all(name == TOWN for name, _, _, _ in self.placements(game, pair, mid))
            self.emit_detail(
                game, pair, mid, self.native(pave, ""), "complete_native_lavender_forecourt",
                "The original town's repeated exterior stepping-stone "
                "paving covers the matching connected source forecourts.",
            )

    def power_plant(self, game, pair):
        native = "ROUTE_10_NORTH"
        _, scene = self.layouts[game, ROUTE_10]
        warps = self.imp.table(game, "gba/warps")[ROUTE_10]
        assert {(w["x"], w["y"]) for w in warps if w["destMap"] == "FR_POWER_PLANT"} == {(2, 37), (7, 40)}
        donor_warps = self.imp.table("crystal", "maps")[native]["warps"]
        assert any((w["x"], w["y"], w["destMap"]) == (3, 9, "POWER_PLANT") for w in donor_warps)
        assert self.matches_layout(scene, [list(row) for row in PLANT], 3, 35)
        field = self.previous(game, pair, 8)["donor"]
        cliff = self.previous(game, pair, 124)["donor"]
        variants = {}
        for row, line in enumerate(PLANT):
            for x, mid in enumerate(line):
                column = 2 if x == 0 else 11 if x == 8 else 4
                if mid == 794:
                    column = 3
                program = column, (6, 6, 6, 7, 8, 9)[row], row in (1, 2)
                assert variants.setdefault(mid, program) == program
        for mid, (x, y, repeat) in variants.items():
            assert all(
                name == ROUTE_10 and 3 <= sx <= 11 and 35 <= sy <= 40
                for name, _, sx, sy in self.placements(game, pair, mid)
            )
            donor = self.gb_at("crystal", native, x, y)
            rows = [8+i%8 for i in range(16)] if repeat else list(range(16))
            art = self.native_building_part(field, donor, rows)
            self.emit_detail(
                game, pair, mid, art, "complete_native_power_plant_exterior",
                "The actual complete Crystal Power Plant roof, outer "
                "frames, upper windows and brick facade follow the source "
                "footprint. Only plain roof and interior window modules "
                "extend. The original full native door is at the source "
                "front entrance and the roof eave crosses above it evenly.",
            )
        for mid in (797, 848, 851, 816, 817, 818, 819, 802, 850):
            assert all(name == ROUTE_10 for name, _, _, _ in self.placements(game, pair, mid))
            if mid in (797, 848, 851):
                art = self.native(cliff, "")
            elif mid == 850:
                assert [(x, y) for _, _, x, y in self.placements(game, pair, mid)] == [(2, 37)]
                art = self.native(self.gb_at("crystal", "ROUTE_16", 9, 6), "")
            elif mid == 802:
                stair = self.gb_ref("crystal", "UNION_CAVE_1F", 18, 3)
                art = self.composite(field, [dict(donor=stair, srcX=0, srcY=8, x=0, y=0, w=16, h=8)], "")
            else:
                art = self.native(field, "")
            self.emit_detail(
                game, pair, mid, art, "complete_native_power_plant_approach",
                "The correct facing native side threshold or horizontal "
                "front step joins the actual Plant entrance. The selected "
                "native lawn and cliff fill the visible outside of the "
                "complete native structure.",
            )
        sign = self.gb_at("crystal", native, 5, 11)
        for mid in (734, 749, 849, 852, 853, 855):
            assert all(name == ROUTE_10 for name, _, _, _ in self.placements(game, pair, mid))
            if mid in (749, 849, 852):
                image = self.gb_image(sign)
                outside = exterior(image, {(222, 255, 222, 255)})
                parts = self.mask_parts(sign, [(x,y) not in outside for y in range(16) for x in range(16)])
                art = self.composite(field, parts, "")
            else:
                art = self.native(field, "")
            self.emit_detail(
                game, pair, mid, art, "complete_native_power_plant_placard",
                "Each outdoor equipment warning uses the complete original "
                "Crystal Power Plant sign. The adjacent fragments of its "
                "old taller frame reveal the approved surrounding lawn.",
            )

    def tower_dome(self, game, pair):
        _, scene = self.layouts[game, ROUTE_10]
        assert self.matches_layout(scene, [list(row) for row in DOME], 15, 73)
        assert self.matches_layout(scene, [[677, 678, 679]], 17, 72)
        swatch = self.gb_at("crystal", "LAVENDER_TOWN", 13, 8)
        assert set(DOME_PALETTE) == {p[:3] for p in self.gb_image(swatch).get_flattened_data()}
        field = self.previous(game, pair, 8)["donor"]
        for mid in (677, 678, 679, *(m for row in DOME for m in row)):
            uses = list(self.placements(game, pair, mid))
            assert len(uses) == 1
            name, _, x, y = uses[0]
            assert name == ROUTE_10 and 15 <= x <= 21 and 72 <= y <= 77
            self.source(game, pair, mid)
            ids, palette, planes = self.packed[game, pair]
            offset = ids.index(mid) * 256
            masks = {}
            exterior_colors = DOME_FIELD if y <= 73 else DOME_CLIFF
            for plane, data in planes.items():
                image = catalog.rgba_native(data[offset:offset+256], palette, plane != "under")
                mask = "".join("1" if p[3] and p[:3] in exterior_colors else "0" for p in image.get_flattened_data())
                if "1" in mask:
                    masks[plane] = mask
            background = (
                field if y <= 73
                else self.gb_ref("crystal", "ROUTE_27", 108 if x == 15 else 109, 0 if x == 15 else 1)
            )
            ground = dict(donor=background, masks=masks) if masks else None
            feature = PREFIX + "complete_unique_lavender_tower_dome"
            art = classic_art(self, game, pair, mid, feature, DOME_PALETTE, DOME_COLORS, ground=ground)
            self.record(
                "geometry", game, pair, mid, feature, art,
                "The actual complete seven-cell-wide regional dome and "
                "spire have no matching Crystal counterpart. Its original "
                "silhouette, all circular bands, and precise priority "
                "planes use four original Lavender slate colors. Only the "
                "explicit exterior pixels show the selected native grass "
                "or correctly facing cliff at each original coordinate.",
            )

    def tower_facade(self, game, pair):
        _, town = self.layouts[game, TOWN]
        _, route = self.layouts[game, ROUTE_10]
        assert self.matches_layout(town, [list(row) for row in TOWER], 15, 0)
        assert self.matches_layout(route, [
            [688, 722, 723, 723, 723, 726, 696],
            [704, 722, 723, 723, 723, 726, 712],
        ], 15, 78)
        warps = self.imp.table(game, "gba/warps")[TOWN]
        native = self.imp.table("crystal", "maps")["LAVENDER_TOWN"]["warps"]
        assert any((w["x"], w["y"], w["destMap"]) == (18, 6, "FR_POKEMON_TOWER_1F") for w in warps)
        assert any((w["x"], w["y"], w["destMap"]) == (14, 5, "LAV_RADIO_TOWER_1F") for w in native)
        columns = (12, 13, 14, 14, 14, 16, 17)
        donors = {}
        for row, mids in enumerate(TOWER):
            for x, mid in enumerate(mids):
                # Only interior windows repeat. The two outer wall frames
                # and the complete doorway remain at the actual edges.
                native_x = columns[x]
                native_y = 1 if row < 3 else 3 if row < 5 else 4 if row == 5 else 5
                if row == 6:
                    native_x = (12, 13, 13, 14, 15, 16, 17)[x]
                if mid in (767, 775):
                    native_x = 13
                assert donors.setdefault(mid, (native_x, native_y)) == (native_x, native_y)
        donors.update({688:(12,1),696:(17,1),704:(12,1),712:(17,1)})
        for mid, (x, y) in donors.items():
            assert all(
                15 <= sx <= 21 and (n == TOWN and sy < 7 or n == ROUTE_10 and sy >= 78)
                for n, _, sx, sy in self.placements(game, pair, mid)
            )
            ref = self.gb_at("crystal", "LAVENDER_TOWN", x, y)
            self.emit_detail(
                game, pair, mid, self.native(ref, ""), "complete_native_lavender_tower_facade",
                "The continuous original Crystal Lavender Tower facade "
                "uses its exact window frames, all lower wall courses, and "
                "complete entrance at the source warp. Only whole inner "
                "window courses repeat. Both connected source map bodies "
                "keep the same outer frames and continuous structure.",
            )

    def matching_terrain(self, game, pair):
        sources = self.imp.cell_index(game)
        safari = self.layouts[game, "FR_FUCHSIA_CITY"][0]["pair"]
        saffron = self.layouts[game, "FR_SAFFRON_CITY"][0]["pair"]
        for mid in (*SHARED_NATIVE, 239, 247):
            other = saffron if mid in (239, 247) else safari
            one, two = sources[pair, mid], sources[other, mid]
            assert all(one[k] == two[k] for k in ("pixel_sha256", "layer_sha256", "behavior")), (game, mid)
            art = self.art_of(self.previous(game, other, mid))
            if mid in (239, 247):
                art["base"] = self.previous(game, pair, 8)["donor"]
            self.emit_detail(
                game, pair, mid, art, "native_matching_kanto_terrain_variant",
                "The complete native source and all priority planes match "
                "the same independently reviewed Kanto terrain feature. "
                "Actual source placements use the matching directional "
                "stone, full fence, dirt path or water-bank material.",
            )

    def terrain(self, game, pair):
        field = self.previous(game, pair, 8)["donor"]
        sand = self.previous(game, pair, 217)["donor"]
        mountain = self.previous(game, pair, 113)["donor"]
        for mid in SAND_JOIN:
            assert all(name == ROUTE_10 for name, _, _, _ in self.placements(game, pair, mid))
            pixels = [p[:3] for p in self.source(game, pair, mid).get_flattened_data()]
            assert set(pixels) <= SAND_GBA | {(115, 206, 165), (173, 222, 165)}
            if any(p not in SAND_GBA for p in pixels):
                art = self.composite(field, self.mask_parts(sand, [p in SAND_GBA for p in pixels]), "")
                art["_objectMask"] = "0"*256
            else:
                art = self.native(sand, "")
            self.emit_detail(
                game, pair, mid, art, "native_route_10_sand_transition",
                "The exact curved and straight edges of the original sandy "
                "walkway join native Crystal Cianwood sand to the same "
                "surrounding Kanto field.",
            )
        for mid in (194, 271, 379, 380, 381, 382, 383, 542, 543, 669, 670, 671, 680, 744):
            donor = field
            if mid in (271, 542, 543, 669, 670, 671, 680):
                donor = mountain
            if mid in (379, 380, 381, 382, 383, 669, 670, 671, 680):
                for _, layout, x, y in self.placements(game, pair, mid):
                    assert self.adjacent(layout, x, y, "below") in (72, 73, 74, 75, 391)
            if mid == 744:
                assert all(
                    n == "FR_ROUTE_14" and self.adjacent(l, x, y, "below") == 30
                    for n, l, x, y in self.placements(game, pair, mid)
                )
            self.emit_detail(
                game, pair, mid, self.native(donor, ""), "native_continuous_lavender_ground",
                "The complete native field or whole raised stone top "
                "continues the adjoining terrain. A full native tree or "
                "Pokemon Center roof is already drawn in the cell below "
                "each corresponding source overlap.",
            )
        for mid in (143, 192, 193, *LAND_CLIFF):
            source = self.source(game, pair, mid)
            hint = self.imp.cell_index(game)[pair, mid]["behavior_hint"]
            assert hint == ("MB_JUMP_SOUTH" if mid in (143, 192, 193) else "MB_NORMAL")
            base = sand if mid in (143, 161, 192, 193, 499, 500, 527, 535, 845) else field
            rock = self.gb_ref("crystal", "ROUTE_27", *LAND_CLIFF.get(mid, (109, 2)))
            mineral = [p[:3] in DOME_CLIFF or p[:3] == (123, 123, 132)
                       for p in source.get_flattened_data()]
            assert 0 < sum(mineral) <= 256
            art = self.composite(base, self.mask_parts(rock, mineral), "")
            art["_objectMask"] = "".join("1" if b else "0" for b in mineral)
            self.emit_detail(
                game, pair, mid, art, "native_lavender_cliff_silhouette",
                "The full cliff face, end or one-way ledge keeps its original "
                "stone outline. The actual facing of the stone is preserved "
                "with native Crystal rock, leaving its exterior clear over "
                "the matching field or sand.",
            )

    def small_foreground(self, game, pair):
        field = self.previous(game, pair, 8)["donor"]
        sand = self.previous(game, pair, 217)["donor"]
        pickets = self.previous(game, pair, 231)["donor"]
        shrubs = self.art_of(self.previous(game, pair, 5))
        assert shrubs["role"] == "classic_gen2_complete_native_small_decorative_tree"
        for mid in (317, 318, 319):
            assert all(
                n == ROUTE_13 and y == 15 for n, _, _, y in self.placements(game, pair, mid)
            )
            self.emit_detail(
                game, pair, mid, dict(shrubs), "native_coastal_shrub_row",
                "The connected route's whole low decorative shrub row uses "
                "the same complete native Crystal shrub at each source "
                "plant position above the distinct water bank.",
            )
        image = self.gb_image(pickets)
        outside = exterior(image, {(222, 255, 222, 255)})
        full_fence = self.mask_parts(pickets, [(x,y) not in outside for y in range(16) for x in range(16)])
        for mid in (223, 644, 728, 822, 823, 830, 831, 844):
            if mid in (822, 823, 830, 831, 844):
                left = self.previous(game, pair, 244)
                right = self.previous(game, pair, 245)
                assert left["role"].startswith("classic_gen2_complete_low_vertical_curb_")
                assert right["role"].startswith("classic_gen2_complete_low_vertical_curb_")
                parts = list(left["parts"])
                if mid in (822, 823, 830, 831):
                    parts.extend(right["parts"])
                if mid in (822, 823, 831):
                    parts.extend(full_fence)
            else:
                parts = full_fence
            art = self.composite(sand if mid == 728 else field, parts, "")
            self.emit_detail(
                game, pair, mid, art, "complete_native_lavender_fence_join",
                "The complete native pickets and correctly facing paired "
                "curb sections retain the fence run, lower rail connection "
                "and original open route. Forest and shore material remain "
                "separate where the complete native background is visible.",
            )

    def wet_contours(self, game, pair):
        water_row = self.previous(game, pair, 299)
        water = water_row["parts"][0]["donor"]
        animation = water_row["animation"]
        waves = frames(self.cache, water, animation, self.packed)
        ground = self.previous(game, pair, 8)["donor"]
        rock = self.gb_ref("crystal", "ROUTE_27", 109, 2)
        for mid in (274, 282, 287, 856, 857):
            uses = list(self.placements(game, pair, mid))
            assert len(uses) == 1
            name, layout, x, y = uses[0]
            assert name == (ROUTE_10 if mid in (856, 857) else ROUTE_12)
            source = self.source(game, pair, mid)
            mineral = [p[:3] in DOME_CLIFF for p in source.get_flattened_data()]
            assert 0 < sum(mineral) < 256
            parts = [dict(donor=water, x=0, y=0, w=16, h=16, animated=True)]
            parts.extend(self.mask_parts(rock, mineral))
            if mid in (274, 282):
                q = 0 if mid == 274 else 2
                adjacent = self.adjacent(layout, x, y, "right")
                assert adjacent == (273 if mid == 274 else 281)
                canonical = self.previous(game, pair, 272 if mid == 274 else 280)
                assert canonical["role"] == f"classic_gen2_complete_coastal_small_rock_quarter_{q}"
                p = canonical["parts"][1]
                x0, y0 = p["srcX"], p["srcY"]
                image = self.gb_image(p["donor"]).crop((x0,y0,x0+4,y0+4))
                outside = exterior(image, {px for px in image.get_flattened_data() if px[2] > px[1]})
                parts.extend(dict(
                    donor=p["donor"], srcX=x0+xx, srcY=y0+yy,
                    x=p["x"]+xx, y=p["y"]+yy, w=1, h=1,
                ) for yy in range(4) for xx in range(4) if (xx,yy) not in outside)
            assert len(parts) <= 32, (mid,len(parts))
            art = self.composite(None, parts, "")
            art.update(animated=True, animation=animation, animationCategory="water", overMask="0"*256)
            self.assert_animated_parts(game, mid, art, waves)
            self.emit_detail(
                game, pair, mid, art, "native_animated_lavender_shore_contour",
                "The exact original cliff contour and full native coastal "
                "boulder sections sit over the same native animated water. "
                "Water stays visible in every exposed corner across phases.",
            )
        for mid in (306, 308, 736):
            source = self.source(game, pair, mid)
            mask = [p[:3] in DOME_CLIFF for p in source.get_flattened_data()]
            assert 0 < sum(mask) < 256
            parts = self.mask_parts(rock, mask)
            if mid == 736:
                parts.extend(self.previous(game, pair, 5)["parts"])
            art = self.composite(ground, parts, "")
            self.emit_detail(
                game, pair, mid, art, "native_dry_lavender_shore_contour",
                "The exact dry part of the stone bank joins selected "
                "native field. The occupied shore uses the same complete "
                "native shrub as the adjoining source shrub row.",
            )

    def residual(self):
        residual = {}
        for (game, name), (spec, layout) in self.layouts.items():
            pair = spec["pair"]
            if PAIR[game] != pair:
                continue
            missing = Counter()
            for mid in layout["mids"]:
                key = game, "gen2", pair, mid, None
                if key not in self.replacements and key not in self.current:
                    prior = self.rows.get(key)
                    if not prior or prior["role"].startswith(PREFIX):
                        missing[mid] += 1
            residual[f"{game}:{name}"] = dict(cells=len(layout["mids"]), remaining=sum(missing.values()), missing=missing)
        (self.out / "candidate-residual.json").write_text(json.dumps(residual, indent=2) + "\n")
        return sum(scene["remaining"] for scene in residual.values())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--private-validate", action="store_true")
    options = p.parse_args()
    review = Lavender()
    review.stage()
    for game, pair in PAIR.items():
        review.bridge(game, pair)
        review.route_gates(game, pair)
        review.fishing_house(game, pair)
        review.lavender_houses(game, pair)
        review.power_plant(game, pair)
        review.tower_dome(game, pair)
        review.tower_facade(game, pair)
        review.matching_terrain(game, pair)
        review.terrain(game, pair)
        review.small_foreground(game, pair)
        review.wet_contours(game, pair)
    review.previews((ROUTE_8, ROUTE_12, ROUTE_13, TOWN, ROUTE_10))
    remaining = review.residual()
    (review.out / "bridge-water-frame-proof.json").write_text(json.dumps(review.frame_proof, indent=2) + "\n")
    if options.freeze or options.private_validate:
        assert remaining == 0, remaining
        decisions = json.loads(DECISIONS.read_text())
        for section, records in review.frozen.items():
            decisions[section] = [
                row for row in decisions.get(section, [])
                if not row.get("feature", "").startswith(PREFIX)
            ] + records
        destination = DECISIONS
        if options.private_validate:
            destination = review.out / "combined-candidate-decisions.json"
        destination.write_text(json.dumps(decisions, indent=2) + "\n")
    if options.private_validate:
        final.DECISIONS = destination
        candidate = final.Final()
        candidate.out = review.out / "neutral-validation"
        candidate.out.mkdir(exist_ok=True)
        candidate.stage()
        proof = candidate.validate()
        candidate.write(candidate.out / "candidate.lua")
        print(json.dumps(proof), flush=True)
    print(json.dumps(dict(
        rows=len(review.replacements),
        cells=sum(sum(u["count"] for u in review.usage[g, p, m]) for g, _, p, m, _ in review.replacements),
        remaining=remaining,
        frozen=options.freeze,
    )))


if __name__ == "__main__":
    main()
