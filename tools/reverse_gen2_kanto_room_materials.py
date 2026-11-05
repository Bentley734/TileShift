"""Author whole gate-carpet, household-furnishing and link-room families."""

import argparse
import json

from PIL import Image

import catalog
import preview
from classic_geometry_review import art as classic_art
from reverse_gen2_hoenn_interior_finish import Review as NativeObjects
from reverse_gen2_kanto_final import DECISIONS, OUT, Final


FEATURE_PREFIX = "kanto_room_material_"
PRIVATE = OUT / "room-materials"
EMPTY_OVER = catalog.sha(bytes(1024))
GATE_CARPET = (666, 667, 674, 675, 706, 707, 708, 714, 715, 791, 796, 797)
LINK_MARKERS = (
    (872, 873, 874), (880, 881, 882), (888, 889, 890),
    (876,), (883, 884, 885), (892, 893),
)
CLINIC_WALL_ANGLES = (672, 678, 680, 686, 688, 694, 800, 830)
CLINIC_FLOOR_EDGES = (673, 674)
CLINIC_SIDE_FLOOR = (801,)
BLACK = (0, 0, 0)
NAVY = (74, 74, 255)
BLUE = (123, 132, 255)
DARK = (58, 58, 58)
CREAM = (247, 230, 214)
GOLD_DARK = (132, 107, 25)
GOLD_MID = (173, 140, 58)
GOLD_LIGHT = (214, 197, 140)
CARPET_FIELD = {(189, 165, 82), (222, 197, 107), (230, 222, 156)}
CARPET_COLORS = {
    (115, 156, 181): BLUE,
    (123, 123, 123): DARK,
    (214, 206, 156): NAVY,
    (247, 239, 189): CREAM,
    **{rgb: DARK for rgb in CARPET_FIELD},
}
CLINIC_FIELD = {
    (197, 181, 140), (214, 206, 156), (230, 222, 156),
    (239, 239, 173), (247, 247, 206),
}
MARKER_COLORS = {
    (165, 173, 165): GOLD_MID,
    (255, 255, 255): CREAM,
    **{rgb: GOLD_LIGHT for rgb in CLINIC_FIELD},
}
CLINIC_WALL_DARK = (107, 107, 107)
CLINIC_WALL_LIGHT = (156, 156, 156)
CLINIC_CORNER_COLORS = {
    BLACK: BLACK,
    (82, 82, 107): DARK,
    (132, 132, 140): DARK,
    (189, 99, 74): DARK,
    (197, 189, 214): CLINIC_WALL_DARK,
    (230, 140, 99): CLINIC_WALL_DARK,
    (230, 189, 115): CLINIC_WALL_DARK,
    (247, 239, 165): CLINIC_WALL_LIGHT,
    (255, 255, 255): CLINIC_WALL_LIGHT,
    **{rgb: DARK for rgb in CLINIC_FIELD},
}


class Rooms(Final):
    neutral = NativeObjects.neutral
    prepare_art = NativeObjects.prepare_art
    object_family = NativeObjects.object_family

    def __init__(self):
        super().__init__()
        self.out = PRIVATE
        self.out.mkdir(exist_ok=True)
        self.contracts = []
        self.frozen = {"geometry": [], "native_modules": [], "native_objects": []}
        self.replacements = {}

    def source(self, game, pair, mid):
        cell = self.imp.cell_index(game)[pair, mid]
        ref = dict(game=game, tileset=pair, id=mid, hash=cell["pixel_sha256"])
        return preview.native_donor(self.cache, ref, self.packed)

    def record(self, section, game, pair, mid, feature, art, evidence, **extra):
        key = game, "gen2", pair, mid, None
        assert key not in self.replacements, key
        assert key not in self.current, key
        if key in self.rows:
            assert self.rows[key]["reverseGen2KantoFinal"].get("feature") == feature, key
        cell = self.imp.cell_index(game)[pair, mid]
        self.frozen[section].append(dict(
            game=game, pair=pair, mid=mid, rgba=cell["pixel_sha256"],
            behavior=cell["behavior"], layers=cell["layer_sha256"],
            feature=feature, art=art, evidence=evidence, **extra,
        ))
        self.replacements[key] = self.render(dict(
            art, game=game, style="gen2", tileset=pair, id=mid,
            sourceHash=cell["pixel_sha256"], sourceBehavior=cell["behavior"],
        ))

    def add(self, game, pair, mid, art, evidence):
        self.record(
            "native_objects", game, pair, mid, self.feature, art, evidence,
            source_family=self.family, whole_source_rgba_sha256=self.whole_hash,
        )

    def placements(self, game, pair, mid):
        for use in self.usage[game, pair, mid]:
            if not use["count"]:
                continue
            _, layout = self.layouts[game, use["map"]]
            for i, value in enumerate(layout["mids"]):
                if value == mid:
                    yield use["map"], layout, i % layout["width"], i // layout["width"]

    def whole_source(self, game, pair, layout, label, alternatives=()):
        width, height = len(layout[0]), len(layout)
        for row, ids in enumerate(layout):
            assert len(ids) == width
            for column, mid in enumerate(ids):
                occurrences = list(self.placements(game, pair, mid))
                assert occurrences, (game, pair, mid)
                for name, scene, x, y in occurrences:
                    matches = self.matches_layout(scene, layout, x - column, y - row)
                    if not matches:
                        matches = any(
                            self.matches_layout(scene, alternate, x - ax, y - ay)
                            for alternate in alternatives
                            for ay, line in enumerate(alternate)
                            for ax, alternate_mid in enumerate(line)
                            if alternate_mid == mid
                        )
                    assert matches, (game, name, mid, x, y)
        self.family = layout
        self.feature = FEATURE_PREFIX + label
        whole = Image.new("RGBA", (width * 16, height * 16))
        for y, ids in enumerate(layout):
            for x, mid in enumerate(ids):
                whole.paste(self.source(game, pair, mid), (x * 16, y * 16))
        self.whole_hash = catalog.sha(whole.tobytes())
        whole.resize((whole.width * 4, whole.height * 4), Image.Resampling.NEAREST).save(
            self.out / f"{game}-{label}-source.png"
        )

    @staticmethod
    def matches_layout(scene, expected, x, y):
        w, h = scene["width"], scene["height"]
        width, height = len(expected[0]), len(expected)
        if not (0 <= x <= w - width and 0 <= y <= h - height):
            return False
        actual = [scene["mids"][j * w + x:j * w + x + width] for j in range(y, y + height)]
        return actual == expected

    def ground(self, game, pair, mid, ref, colors):
        mids, palette, planes = self.packed[game, pair]
        start = mids.index(mid) * 256
        masks = {}
        for name, blob in planes.items():
            image = catalog.rgba_native(blob[start:start + 256], palette, name != "under")
            bits = "".join(
                "1" if p[3] and p[:3] in colors else "0"
                for p in image.get_flattened_data()
            )
            if "1" in bits:
                masks[name] = bits
        return dict(donor=ref, masks=masks) if masks else None

    def materials(self):
        for game in self.games:
            pair = "house"
            ref = self.current[game, "gen2", pair, 641, None]["donor"]
            for mid in GATE_CARPET + (643,):
                for name, _, _, _ in self.placements(game, pair, mid):
                    assert name.startswith(("FR_ROUTE_", "FR_UNDERGROUND_PATH_")), (mid, name)
                self.source(game, pair, mid)
                if mid in GATE_CARPET:
                    feature = FEATURE_PREFIX + "gate_runner"
                    art = classic_art(
                        self, game, pair, mid, feature, (DARK, NAVY, BLUE, CREAM),
                        CARPET_COLORS, ground=self.ground(game, pair, mid, ref, CARPET_FIELD),
                    )
                    self.record(
                        "geometry", game, pair, mid, feature, art,
                        "The full linked blue runner in the Kanto gates retains its complete "
                        "border, square corners and length in the native source plan. The "
                        "corresponding Crystal gates use small separate entry mats. Four "
                        "original Crystal gate colors distinguish this whole regional runner, "
                        "with the existing gray checker at every actual exterior floor pixel.",
                    )
                else:
                    feature = FEATURE_PREFIX + "gate_checker"
                    art = self.native(ref, feature)
                    assert self.imp.cell_index(game)[pair, mid]["layer_sha256"]["over"] == EMPTY_OVER
                    art["overMask"] = "0" * 256
                    self.record(
                        "native_modules", game, pair, mid, feature, art,
                        "Complete plain Kanto gate floor join uses the existing native "
                        "Crystal gray checker, with the full original motif at native scale.",
                    )

            pair = "network"
            ref = self.current[game, "gen2", pair, 641, None]["donor"]
            for mid in (m for line in LINK_MARKERS for m in line):
                for name, _, _, _ in self.placements(game, pair, mid):
                    assert name.endswith(("_POKEMON_CENTER_2F", "_POKECENTER_2F")), (mid, name)
                self.source(game, pair, mid)
                feature = FEATURE_PREFIX + "link_floor_markings"
                ground = self.ground(game, pair, mid, ref, CLINIC_FIELD)
                assert ground is not None
                art = classic_art(
                    self, game, pair, mid, feature,
                    (GOLD_DARK, GOLD_MID, GOLD_LIGHT, CREAM), MARKER_COLORS, ground=ground,
                )
                self.record(
                    "geometry", game, pair, mid, feature, art,
                    "The complete native link-floor Ball and wire markings are specific "
                    "to these Kanto communication rooms. Original Crystal upstairs uses "
                    "a different link-floor plan. Native Crystal gold ink preserves each "
                    "shape and alignment over the exact existing pink public floor.",
                )

    def furniture(self):
        house_floor = self.gb_at("crystal", "PLAYERS_HOUSE_1F", 4, 2)
        planter_floor = self.gb_at("crystal", "GUIDE_GENTS_HOUSE", 3, 1)
        ship_floor = self.gb_at("crystal", "FAST_SHIP_CABINS_NNW_NNE_NE", 0, 5)
        clinic_floor = self.gb_ref("crystal", "CHERRYGROVE_POKECENTER_1F", 4, 0)
        for game in self.games:
            pair = "house"
            family = [[342], [350]]
            self.whole_source(game, pair, family, "house_planter")
            self.object_family(
                pair, family, "GUIDE_GENTS_HOUSE", (0, 6), planter_floor, house_floor,
                "complete Kanto household planter", only_game=game,
                source_bounds=[0, 0, 16, 32], foot_anchor=31,
            )
            family = [[357, 358], [365, 366]]
            self.whole_source(game, pair, family, "house_dining_table")
            self.object_family(
                pair, family, "FAST_SHIP_CABINS_NNW_NNE_NE", (2, 5), ship_floor, house_floor,
                "complete Kanto household dining table", only_game=game,
                source_bounds=[0, 0, 32, 32], foot_anchor=31,
            )
            for mid, offset, facing, table in (
                (367, 1, "east", (357, 365)), (359, -1, "west", (358, 366)),
            ):
                for name, scene, x, y in self.placements(game, pair, mid):
                    w = scene["width"]
                    assert 0 <= x + offset < w and scene["mids"][y * w + x + offset] in table, (name, mid)
                self.whole_source(game, pair, [[mid]], "house_chair_" + facing)
                role = "reverse_gen2_complete_backed_chair_" + facing
                approved = next(row for row in self.active if row.get("role") == role)
                art = self.art_of(approved)
                art.update(role=self.feature, base=house_floor, overMask="0" * 256)
                assert self.imp.cell_index(game)[pair, mid]["layer_sha256"]["over"] == EMPTY_OVER
                self.add(
                    game, pair, mid, art,
                    "Complete native Crystal seat, backrest and leg modules assembled "
                    "in the same side view already reviewed for Hoenn. The source chair "
                    "is checked against the actual adjacent dining-table edge at every "
                    "placement. Surrounding wood matches the room at native scale.",
                )

            pair = "network"
            family = [[768], [769]]
            alternate = [[832], [769]]
            self.whole_source(game, pair, family, "clinic_planter", (alternate,))
            self.object_family(
                pair, family, "GUIDE_GENTS_HOUSE", (0, 6), planter_floor, clinic_floor,
                "complete Kanto clinic planter", only_game=game,
                source_bounds=[0, 0, 16, 32], foot_anchor=31,
            )
            top = self.frozen["native_objects"][-2]["art"]
            self.whole_source(game, pair, alternate, "clinic_planter_indigo", (family,))
            alternate_art = dict(top)
            # The Indigo cap shares the plant shape, with a different priority
            # split. Determine the mask from the exact source plane independently.
            alternate_art["_objectMask"] = "".join(
                "1" if any(
                    part["x"] <= x < part["x"] + part["w"]
                    and part["y"] <= y < part["y"] + part["h"]
                    for part in top["parts"]
                ) else "0"
                for y in range(16) for x in range(16)
            )
            self.add(
                game, pair, 832, self.prepare_art(game, pair, 832, alternate_art),
                "Indigo uses a different ground behind the same complete upper planter. "
                "Its actual two-cell planter stays joined over the selected pink floor.",
            )

    def gate_walls(self):
        pair = "house"
        upper = self.gb_at("crystal", "ROUTE_16_GATE", 3, 0)
        lower = self.gb_at("crystal", "ROUTE_16_GATE", 3, 1)
        original_window_wall = self.gb_at("crystal", "GUIDE_GENTS_HOUSE", 4, 0)
        for game in self.games:
            for mid, donor in ((647, upper), (655, lower)):
                for name, _, _, _ in self.placements(game, pair, mid):
                    assert name.startswith(("FR_ROUTE_", "FR_UNDERGROUND_PATH_")), (mid, name)
                self.source(game, pair, mid)
                assert self.imp.cell_index(game)[pair, mid]["layer_sha256"]["over"] == EMPTY_OVER
                feature = FEATURE_PREFIX + "gate_wall"
                art = self.native(donor, feature)
                art["overMask"] = "0" * 256
                self.record(
                    "native_modules", game, pair, mid, feature, art,
                    "The full ordinary header and its lower shadow use the original "
                    "Crystal Route 16 gate counterpart. Window frames, doors and "
                    "wall-mounted fixtures have independent source families.",
                )
            for family, label in (
                ([[664, 665], [672, 673]], "gate_window"),
                ([[766, 767], [774, 775]], "gate_window_overhead"),
            ):
                self.whole_source(game, pair, family, label)
                self.object_family(
                    pair, family, "GUIDE_GENTS_HOUSE", (5, 0), original_window_wall, [upper, lower],
                    "complete native Kanto gate window", only_game=game,
                    row_pixels=[None] * 8 + list(range(16)) + [None] * 8,
                    column_pixels=[None] * 8 + list(range(16)) + [None] * 8,
                    preserve_rects=[(9, 8, 14, 16)],
                    source_bounds=[8, 8, 16, 16], foot_anchor=23,
                )

    def clinic_perimeters(self):
        pair = "network"
        palette = BLACK, DARK, CLINIC_WALL_DARK, CLINIC_WALL_LIGHT
        for game in self.games:
            floor = self.current[game, "gen2", pair, 641, None]["donor"]
            for mid in CLINIC_WALL_ANGLES + CLINIC_FLOOR_EDGES + CLINIC_SIDE_FLOOR:
                for name, _, _, _ in self.placements(game, pair, mid):
                    assert "POKEMON_CENTER" in name or "POKECENTER" in name, (mid, name)
                self.source(game, pair, mid)
                if mid in CLINIC_SIDE_FLOOR:
                    feature = FEATURE_PREFIX + "clinic_side_floor"
                    art = self.native(floor, feature)
                    assert self.imp.cell_index(game)[pair, mid]["layer_sha256"]["over"] == EMPTY_OVER
                    art["overMask"] = "0" * 256
                    self.record(
                        "native_modules", game, pair, mid, feature, art,
                        "Complete empty floor beside the stair or diagonal wall uses "
                        "the adjacent original Crystal public pink checker.",
                    )
                else:
                    feature = FEATURE_PREFIX + "clinic_clipped_perimeter"
                    art = classic_art(
                        self, game, pair, mid, feature, palette, CLINIC_CORNER_COLORS,
                        ground=self.ground(game, pair, mid, floor, CLINIC_FIELD),
                    )
                    self.record(
                        "geometry", game, pair, mid, feature, art,
                        "The complete clipped room perimeter uses the same native "
                        "Crystal gray wall shades as the straight clinic back wall. "
                        "The original Crystal rooms have straight upper corners. The "
                        "exact native Kanto diagonal, outside black, floor edge, and "
                        "priority split remain intact, with the existing pink checker "
                        "in each actual inside-floor pixel.",
                    )

    def previews(self, names):
        for game in self.games:
            for name in names:
                spec, layout = self.layouts[game, name]
                pair = spec["pair"]
                width, height = layout["width"], layout["height"]
                scene = Image.new("RGBA", (width * 16, height * 16))
                tiles = {}
                for index, mid in enumerate(layout["mids"]):
                    key = game, "gen2", pair, mid, None
                    if mid not in tiles:
                        row = self.rows.get(key) or self.current.get(key)
                        tiles[mid] = self.replacements.get(key)
                        if tiles[mid] is None:
                            tiles[mid] = self.render(row) if row else self.source(game, pair, mid)
                    scene.paste(tiles[mid], (index % width * 16, index // width * 16))
                scene.save(self.out / f"{game}-{name}.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    options = parser.parse_args()
    rooms = Rooms()
    rooms.stage()
    rooms.materials()
    rooms.furniture()
    rooms.gate_walls()
    rooms.clinic_perimeters()
    rooms.previews((
        "FR_ROUTE_16_NORTH_ENTRANCE_1F", "FR_ROUTE_22_NORTH_ENTRANCE",
        "FR_CERULEAN_CITY_HOUSE1", "FR_FIVE_ISLAND_HOUSE1",
        "FR_CELADON_CITY_POKEMON_CENTER_2F", "FR_INDIGO_PLATEAU_POKEMON_CENTER_1F",
    ))
    decisions = json.loads(DECISIONS.read_text())
    for section, records in rooms.frozen.items():
        decisions[section] = [
            row for row in decisions.get(section, [])
            if not row.get("feature", "").startswith(FEATURE_PREFIX)
        ] + records
    if options.freeze:
        DECISIONS.write_text(json.dumps(decisions, indent=2) + "\n")
    (rooms.out / "contracts.json").write_text(json.dumps(rooms.contracts, indent=2) + "\n")
    count = sum(sum(u["count"] for u in rooms.usage[g, p, m]) for g, _, p, m, _ in rooms.replacements)
    print(json.dumps(dict(rows=len(rooms.replacements), cells=count, frozen=options.freeze)))


if __name__ == "__main__":
    main()
