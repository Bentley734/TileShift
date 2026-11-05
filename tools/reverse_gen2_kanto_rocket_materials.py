"""Author connected native Rocket walls and complete Silph potted plants."""

import argparse
import copy
import json

from PIL import Image

import catalog
from classic_geometry_review import art as classic_art
from reverse_gen2_kanto_final import DECISIONS, OUT
from reverse_gen2_kanto_room_materials import Rooms
from reverse_kanto_review import runs


FEATURE_PREFIX = "kanto_rocket_material_"
PAIR_BY_GAME = {
    "firered": "building__rom_082d4ecc",
    "leafgreen": "building__rom_082d4eac",
}
OUTER_SHELL = (648, 652, 664, 665, 666, 668)
SHELL_COLORS = {
    (0, 0, 0): (0, 0, 0),
    (82, 82, 107): (58, 58, 58),
    (123, 123, 123): (107, 107, 107),
    (181, 181, 165): (107, 107, 107),
    (255, 255, 255): (247, 230, 214),
}
SHELL_PALETTE = ((0, 0, 0), (58, 58, 58), (107, 107, 107), (247, 230, 214))
LOWER_EDGE_FIELD = {(132, 132, 82), (165, 165, 99), (197, 197, 156)}
SHELL_COLORS.update({rgb: (107, 107, 107) for rgb in LOWER_EDGE_FIELD})
VENT_COLORS = {
    (82, 82, 107): (58, 58, 58),
    (123, 123, 123): (107, 107, 107),
    (181, 181, 165): (107, 107, 107),
    (230, 230, 230): (156, 156, 156),
}
PHONE_COLORS = {
    (82, 82, 107): (58, 58, 58),
    (140, 140, 148): (156, 156, 156),
    (181, 181, 165): (156, 156, 156),
    (214, 214, 214): (156, 156, 156),
    (255, 255, 255): (247, 230, 214),
    (82, 222, 123): (148, 197, 74),
}
WAREHOUSE_SEAT_COLORS = {
    (82, 82, 107): (58, 58, 58),
    (123, 123, 123): (58, 58, 58),
    (140, 99, 74): (132, 107, 25),
    (181, 99, 25): (132, 107, 25),
    (230, 148, 66): (173, 140, 58),
    (230, 173, 90): (214, 197, 140),
    (255, 206, 140): (214, 197, 140),
}


class RocketRooms(Rooms):
    def __init__(self):
        super().__init__()
        self.out = OUT / "rocket-materials"
        self.out.mkdir(exist_ok=True)

    def rocket_walls(self):
        wall = self.gb_at("crystal", "TEAM_ROCKET_BASE_B1F", 2, 0)
        image = self.gb_image(wall)
        body_color = (8, 33, 255)
        assert set(image.crop((0, 10, 16, 11)).get_flattened_data()) == {body_color + (255,)}
        body = self.solid(wall, body_color)
        wall_parts = {
            649: dict(donor=wall, srcX=0, srcY=0, w=16, h=11, x=0, y=0),
            657: dict(donor=wall, srcX=0, srcY=11, w=16, h=5, x=0, y=11),
        }
        for game, pair in PAIR_BY_GAME.items():
            self.feature = FEATURE_PREFIX + "plain_connected_back_wall"
            self.family = [[649], [657]]
            whole = Image.new("RGBA", (16, 32))
            for y, mid in enumerate((649, 657)):
                whole.paste(self.source(game, pair, mid), (0, y * 16))
            self.whole_hash = catalog.sha(whole.tobytes())
            for mid, part in wall_parts.items():
                for name, _, _, _ in self.placements(game, pair, mid):
                    assert "ROCKET_HIDEOUT" in name or "ROCKET_WAREHOUSE" in name, (name, mid)
                art = self.composite(body, [part], self.feature)
                art["_sourceOverMask"] = True
                self.add(
                    game, pair, mid, self.prepare_art(game, pair, mid, art),
                    "The connected complete original Crystal Rocket Base wall uses "
                    "both of its native horizontal halves at 1:1. A single plain "
                    "blue body band extends the wall to the source's full two-cell "
                    "height, keeping the white upper cap and lower dark base exactly "
                    "once. The precise source foreground plane is checked separately.",
                )

            self.wall_fixtures(game, pair, wall, body, wall_parts)
            self.warehouse_couch_body(game, pair)

            floor = self.current[game, "gen2", pair, 642, None]["donor"]
            for mid in OUTER_SHELL:
                for name, _, _, _ in self.placements(game, pair, mid):
                    assert any(room in name for room in (
                        "ROCKET_HIDEOUT", "ROCKET_WAREHOUSE", "SILPH_CO",
                    )), (name, mid)
                self.source(game, pair, mid)
                feature = FEATURE_PREFIX + "clipped_room_perimeter"
                ground = self.ground(game, pair, mid, floor, LOWER_EDGE_FIELD)
                assert bool(ground) == (mid in (665, 666))
                art = classic_art(
                    self, game, pair, mid, feature, SHELL_PALETTE, SHELL_COLORS, ground=ground,
                )
                self.record(
                    "geometry", game, pair, mid, feature, art,
                    "The unusual half-cell Kanto room-perimeter ends retain their "
                    "exact exposed floor, narrow straight metal frames, and native "
                    "void silhouette. The original Crystal Rocket Base has a different "
                    "lower perimeter design. The exterior remains black and the small "
                    "walkable fragments match the already selected Crystal floor.",
                )

    def solid(self, donor, color):
        ref = copy.deepcopy(donor)
        ref["palettes"] = [[list(color) for _ in range(4)] for _ in range(8)]
        assert set(self.gb_image(ref).get_flattened_data()) == {color + (255,)}
        return ref

    def ink_parts(self, donor, pixels):
        sections = {
            color: runs([pixel == color for pixel in pixels])
            for color in sorted(set(pixels) - {None})
        }
        primary = max(sections, key=lambda color: len(sections[color]))
        sections[primary] = runs([p is not None for p in pixels])
        parts = []
        for color in [primary] + [c for c in sections if c != primary]:
            brush = self.solid(donor, color)
            parts.extend(dict(donor=brush, srcX=0, srcY=0, **rect) for rect in sections[color])
        return parts

    def wall_fixtures(self, game, pair, wall, body, wall_parts):
        for family, label, palette, expected, seat_mid in (
            ([[650], [658]], "vent", VENT_COLORS, (80, 64), 1013),
            ([[651], [659]], "wall_phone", PHONE_COLORS, (72, 89), 1014),
        ):
            alternate = [[family[0][0]], [seat_mid]]
            self.whole_source(game, pair, family, label, (alternate,))
            self.feature = FEATURE_PREFIX + label
            for row, base_mid, pixel_count in zip(family, (649, 657), expected):
                mid = row[0]
                source = self.source(game, pair, mid)
                background = self.source(game, pair, base_mid)
                fixture = [
                    palette[pixel[:3]] if pixel != base else None
                    for pixel, base in zip(source.get_flattened_data(), background.get_flattened_data())
                ]
                assert sum(color is not None for color in fixture) == pixel_count
                parts = [wall_parts[base_mid]] + self.ink_parts(wall, fixture)
                assert len(parts) <= 32, (label, game, mid, len(parts))
                art = self.composite(body, parts, self.feature)
                art["_sourceOverMask"] = True
                self.add(
                    game, pair, mid, self.prepare_art(game, pair, mid, art),
                    "The exact complete Kanto wall fixture spans two cells over "
                    "the same complete Crystal Rocket wall. Original Crystal "
                    "does not have this full fixture. Its shape and anchors are "
                    "preserved pixel-for-pixel with native Crystal ink colors. "
                    "The wall behind it uses the identical neighboring program.",
                )
            seat = self.source(game, pair, seat_mid)
            delta = [
                WAREHOUSE_SEAT_COLORS[pixel[:3]] if pixel != base else None
                for pixel, base in zip(seat.get_flattened_data(), source.get_flattened_data())
            ]
            assert sum(color is not None for color in delta) == 95
            assert all(color is None for color in delta[:6 * 16])
            self.whole_source(game, pair, alternate, label + "_with_seat", (family,))
            self.feature = FEATURE_PREFIX + label + "_with_seat"
            parts += self.ink_parts(wall, delta)
            assert len(parts) <= 32, (label, game, seat_mid, len(parts))
            art = self.composite(body, parts, self.feature)
            art["_sourceOverMask"] = True
            self.add(
                game, pair, seat_mid, self.prepare_art(game, pair, seat_mid, art),
                "The unique Rocket Warehouse fixture keeps the same complete wall "
                "glyph behind the native overlap of the couch. The complete visible "
                "upper couch contour retains its true position in four Crystal colors.",
            )

    def warehouse_couch_body(self, game, pair):
        warehouse = [[1013, 1014], [808, 810]]
        hideout = [[800, 801, 802], [808, 809, 810]]
        office = [[925, 926, 927], [808, 809, 810]]
        self.whole_source(game, pair, warehouse, "warehouse_couch", (hideout, office))
        self.whole_source(game, pair, hideout, "hideout_couch", (warehouse, office))
        self.whole_source(game, pair, office, "silph_couch", (warehouse, hideout))
        rocket_floor = self.current[game, "gen2", pair, 642, None]["donor"]
        office_floor = self.gb_ref("crystal", "SILPH_CO_1F", 7, 0)
        office_field = {(107, 156, 165), (132, 189, 197)}
        colors = WAREHOUSE_SEAT_COLORS | {
            rgb: (58, 58, 58) for rgb in LOWER_EDGE_FIELD | office_field
        }
        palette = tuple(sorted(set(WAREHOUSE_SEAT_COLORS.values())))
        for mid in (800, 801, 802, 808, 809, 810, 925, 926, 927):
            feature = FEATURE_PREFIX + "warehouse_couch"
            ground = None
            if mid in hideout[0]:
                ground = self.ground(game, pair, mid, rocket_floor, LOWER_EDGE_FIELD)
            elif mid in office[0]:
                ground = self.ground(game, pair, mid, office_floor, office_field)
            art = classic_art(
                self, game, pair, mid, feature, palette, colors, ground=ground,
            )
            self.record(
                "geometry", game, pair, mid, feature, art,
                "The complete Warehouse, Rocket Hideout, and Silph couch variants "
                "share their native arm, back, seat and apron art. The exact width, "
                "original source pixels and anchors are retained in the same four "
                "Crystal shades. Each top variant uses its correct selected floor.",
            )

    def office_planters(self):
        native_map = "GUIDE_GENTS_HOUSE"
        original_floor = self.gb_at("crystal", native_map, 3, 1)
        floor = self.gb_ref("crystal", "SILPH_CO_1F", 7, 0)
        wall = self.gb_ref("crystal", "SILPH_CO_1F", 1, 0)
        for game, pair in PAIR_BY_GAME.items():
            for family, label in (([[845], [853]], "office_planter"), ([[846], [854]], "office_planter_shadow")):
                alternatives = ([[847], [854]],) if family[0][0] == 846 else ()
                self.whole_source(game, pair, family, FEATURE_PREFIX + label, alternatives)
                self.feature = FEATURE_PREFIX + label
                self.object_family(
                    pair, family, native_map, (0, 6), original_floor, floor,
                    "complete Kanto Silph potted tree", only_game=game,
                    source_bounds=[0, 0, 16, 32], foot_anchor=31,
                )
            source_art = self.frozen["native_objects"][-2]["art"]
            self.whole_source(
                game, pair, [[847], [854]], FEATURE_PREFIX + "office_planter_wall",
                ([[846], [854]],),
            )
            self.feature = FEATURE_PREFIX + "office_planter_wall"
            art = dict(source_art, base=wall, role=self.feature)
            art["_objectMask"] = "".join(
                "1" if any(
                    part["x"] <= x < part["x"] + part["w"]
                    and part["y"] <= y < part["y"] + part["h"]
                    for part in art["parts"]
                ) else "0"
                for y in range(16) for x in range(16)
            )
            self.add(
                game, pair, 847, self.prepare_art(game, pair, 847, art),
                "This complete native upper potted tree is the same plant in a "
                "continuous Silph window-wall row. It joins the shared pot body "
                "at its original anchor and exposes the selected wall around it.",
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    options = parser.parse_args()
    rooms = RocketRooms()
    rooms.stage()
    rooms.rocket_walls()
    rooms.office_planters()
    rooms.previews((
        "FR_ROCKET_HIDEOUT_B1F", "FR_ROCKET_HIDEOUT_B2F", "FR_ROCKET_HIDEOUT_B4F",
        "FR_FIVE_ISLAND_ROCKET_WAREHOUSE", "FR_SILPH_CO_1F", "FR_SILPH_CO_3F",
    ))
    decisions = json.loads(DECISIONS.read_text())
    for section, records in rooms.frozen.items():
        decisions[section] = [
            row for row in decisions.get(section, [])
            if not row.get("feature", "").startswith(FEATURE_PREFIX)
        ] + records
    if options.freeze:
        DECISIONS.write_text(json.dumps(decisions, indent=2) + "\n")
    count = sum(sum(u["count"] for u in rooms.usage[g, p, m]) for g, _, p, m, _ in rooms.replacements)
    print(json.dumps(dict(rows=len(rooms.replacements), cells=count, frozen=options.freeze)))


if __name__ == "__main__":
    main()
