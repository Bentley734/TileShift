"""Review the joined Seafoam/Icefall snow surfaces and directed water banks."""

import argparse
import json

from PIL import ImageChops

import catalog
import preview
from classic_geometry_review import art as classic_art
from gb_theme_animation import frames, specification
from reverse_gen2_kanto_final import DECISIONS, OUT, ROOT
from reverse_gen2_kanto_room_materials import EMPTY_OVER, Rooms
from reverse_kanto_review import exterior, runs


PREFIX = "kanto_seafoam_"
PAIRS = {
    "firered": "general__rom_082d4e24",
    "leafgreen": "general__rom_082d4e04",
}
SNOW_FLOORS = (
    673, 720, 721, 722, 723, 724, 725, 726, 728, 730, 731, 732, 733,
    734, 735, 736, 738, 740, 755, 756, 760, 763, 765, 768, 771, 772, 773,
)
ICE_FACES = {
    651: (13, 2, "front"),
    672: (17, 2, "west_inner_turn"),
    674: (16, 3, "east_inner_turn"),
    710: (8, 0, "west"),
    711: (10, 1, "east"),
    751: (13, 2, "front"),
    829: (8, 0, "west"),
}
ICE_PALETTE = ((41, 0, 74), (132, 90, 255), (74, 230, 255), (206, 255, 255))
SNOW_PILE_COLORS = {
    (90, 156, 197): ICE_PALETTE[1],
    (99, 123, 173): ICE_PALETTE[0],
    (123, 181, 230): ICE_PALETTE[1],
    (181, 206, 239): ICE_PALETTE[2],
    (206, 230, 239): ICE_PALETTE[3],
    (239, 239, 247): ICE_PALETTE[3],
}
SNOW_PILE_EXTERIOR = {(206, 230, 239, 255), (239, 239, 247, 255)}
WATER_BODY = {780: "north", 781: "south", 783: "east"}
WATER_BANKS = {
    **dict.fromkeys((784, 785, 786, 787, 788, 789, 790), "north"),
    791: "east",
    **dict.fromkeys((800, 801, 802, 803, 804, 805, 806), "south"),
}
FALLS = (295, 303, 311, 795, 796)
SHORE_ROCK_COLORS = {
    (90, 58, 66), (123, 74, 74), (148, 107, 107), (189, 148, 140), (222, 197, 165),
}


class Seafoam(Rooms):
    def __init__(self):
        super().__init__()
        self.out = OUT / "seafoam"
        self.out.mkdir(exist_ok=True)
        self.animations = {}
        self.frame_proof = []

    def checked_source(self, game, pair, mid):
        uses = list(self.placements(game, pair, mid))
        assert uses and all(
            name.startswith(("FR_SEAFOAM_ISLANDS_", "FR_FOUR_ISLAND_ICEFALL_CAVE_"))
            for name, _, _, _ in uses
        ), (game, pair, mid, uses[:1])
        cell = self.imp.cell_index(game)[pair, mid]
        assert cell["layer_sha256"]["over"] == EMPTY_OVER, (game, pair, mid)
        return cell, self.source(game, pair, mid)

    def snow(self):
        for game, pair in PAIRS.items():
            ref = self.current[game, "gen2", pair, 641, None]["donor"]
            assert ref["game"] == "crystal" and ref["map"] == "ICE_PATH_1F"
            for mid in SNOW_FLOORS:
                cell, _ = self.checked_source(game, pair, mid)
                assert cell["behavior_hint"] in ("MB_CAVE", "MB_NORMAL"), (game, mid)
                feature = PREFIX + "ordinary_snow_floor"
                art = self.native(ref, feature)
                art["overMask"] = "0" * 256
                self.record(
                    "native_modules", game, pair, mid, feature, art,
                    "Complete ordinary snow, light/shade and thin surface-join "
                    "variants in the same walkable cave system use the already "
                    "selected native Crystal Ice Path floor. The visible raised "
                    "bank and stairs remain separate from this surface.",
                )

            for mid, (block, quadrant, direction) in ICE_FACES.items():
                cell, _ = self.checked_source(game, pair, mid)
                assert cell["behavior_hint"] == "MB_NORMAL"
                feature = PREFIX + "ice_bank_" + direction
                donor = self.gb_ref("crystal", "ICE_PATH_1F", block, quadrant)
                art = self.native(donor, feature)
                art["overMask"] = "0" * 256
                self.record(
                    "native_modules", game, pair, mid, feature, art,
                    "The whole native source is a continuous front, side, "
                    "or interior turn of the same Seafoam/Icefall ice bank. "
                    "It uses the matching whole original Crystal Ice Path "
                    "module in the same orientation and scale.",
                )

            cell, _ = self.checked_source(game, pair, 646)
            assert cell["behavior_hint"] == "MB_FALL_WARP"
            feature = PREFIX + "floor_hole"
            hole = self.gb_ref("crystal", "ICE_PATH_1F", 23, 3)
            art = self.native(hole, feature)
            art["overMask"] = "0" * 256
            self.record(
                "native_modules", game, pair, 646, feature, art,
                "The complete original Crystal Ice Path hole is aligned "
                "with the actual Seafoam fall warp. All of the native "
                "opening, dark rim, and snowy surroundings remain at 1:1.",
            )

            for mid in (719, 727):
                cell, source = self.checked_source(game, pair, mid)
                assert cell["behavior_hint"] == "MB_NORMAL"
                outside = exterior(source, SNOW_PILE_EXTERIOR)
                assert 0 < len(outside) < 256
                mids, palette, planes = self.packed[game, pair]
                start = mids.index(mid) * 256
                masks = {}
                for name, data in planes.items():
                    plane = catalog.rgba_native(data[start:start + 256], palette, name != "under")
                    mask = "".join(
                        "1" if pixel[3] and (i % 16, i // 16) in outside else "0"
                        for i, pixel in enumerate(plane.get_flattened_data())
                    )
                    if "1" in mask:
                        masks[name] = mask
                feature = PREFIX + "whole_snow_pile"
                art = classic_art(
                    self, game, pair, mid, feature, ICE_PALETTE, SNOW_PILE_COLORS,
                    ground=dict(donor=ref, masks=masks),
                )
                self.record(
                    "geometry", game, pair, mid, feature, art,
                    "Seafoam's complete three-lobed miniature snow pile has "
                    "no matching complete shape in Crystal. Its original "
                    "lumps and the optional upper bank lip keep their exact "
                    "shape in four Crystal Ice Path colors. Only exterior "
                    "connected snow reveals the selected native floor.",
                )

    def water(self):
        water = self.gb_ref("crystal", "UNION_CAVE_1F", 15, 0)
        falls = self.gb_ref("crystal", "TOHJO_FALLS", 44, 0)
        rock = self.gb_ref("crystal", "TOHJO_FALLS", 4, 0)
        rock_pixels = list(self.gb_image(rock).get_flattened_data())
        rock_colors = {pixel[:3] for pixel in rock_pixels}
        assert rock_colors == {(58, 58, 58), (165, 123, 25), (197, 148, 58), (222, 255, 222)}
        for game, pair in PAIRS.items():
            manifest = self.cache / game / "data/generated/gba/native" / pair / "anim_manifest.lua"
            original_bank = catalog.read_lua(manifest)["water"]
            for mid, direction in (WATER_BODY | WATER_BANKS | dict.fromkeys(FALLS, None)).items():
                cell, source = self.checked_source(game, pair, mid)
                assert mid in original_bank["mids"] and original_bank["frames"] == 8
                hint = f"MB_{direction.upper()}WARD_CURRENT" if direction else "MB_WATERFALL"
                assert cell["behavior_hint"] == hint, (game, pair, mid, cell["behavior_hint"])
                if direction not in self.animations:
                    donor = water if direction else falls
                    animation = specification(self.cache, donor, "program", flow_direction=direction)
                    assert animation
                    native_frames = frames(self.cache, donor, animation, self.packed)
                    assert len({catalog.sha(im.tobytes()) for im in native_frames}) > 1
                    if direction:
                        dx, dy = {"north": (0, -1), "south": (0, 1), "east": (1, 0)}[direction]
                        original = native_frames[0].crop((0, 0, 8, 8))
                        assert all(
                            ImageChops.offset(original, phase * dx, phase * dy).tobytes()
                            == image.crop((0, 0, 8, 8)).tobytes()
                            for phase, image in enumerate(native_frames)
                        ), direction
                    self.animations[direction] = donor, animation, native_frames
                donor, animation, native_frames = self.animations[direction]
                foreground = []
                for r, g, b, a in source.get_flattened_data():
                    assert a == 255
                    rgb = r, g, b
                    foreground.append(rgb in SHORE_ROCK_COLORS)
                    if rgb not in SHORE_ROCK_COLORS:
                        assert b >= max(r, g), (game, mid, rgb)
                bank = any(foreground)
                assert bank == (mid in WATER_BANKS or mid in (795, 796)), (game, mid)
                feature = PREFIX + ("waterfall" if direction is None else direction + "_current")
                if bank:
                    parts = [dict(donor=donor, x=0, y=0, w=16, h=16, animated=True)]
                    parts.extend(
                        dict(donor=rock, srcX=part["x"], srcY=part["y"], **part)
                        for part in runs(foreground)
                    )
                    assert len(parts) <= 32, (game, pair, mid, len(parts))
                    art = self.composite(None, parts, feature)
                else:
                    art = self.native(donor, feature)
                art.update(
                    animated=True, animation=animation, animationCategory="water",
                    overMask="0" * 256,
                )
                actual_frames = preview.replacement_frames(self.cache, art, self.packed, ROOT)
                assert len(actual_frames) == len(native_frames)
                for actual, native in zip(actual_frames, native_frames):
                    expected = [
                        stone if is_rock else wave
                        for is_rock, stone, wave in zip(foreground, rock_pixels, native.get_flattened_data())
                    ]
                    assert list(actual.get_flattened_data()) == expected, (game, pair, mid)
                self.frame_proof.append(dict(
                    game=game, pair=pair, mid=mid, direction=direction,
                    rock_pixels=sum(foreground),
                    frames=[catalog.sha(im.tobytes()) for im in actual_frames],
                ))
                self.record(
                    "native_modules", game, pair, mid, feature, art,
                    "The joined actual Seafoam/Icefall current or waterfall "
                    "uses the complete original Crystal animation program. Its "
                    "direction is checked from this tile's source behavior. "
                    "Unique narrow rocky joins preserve their exact source "
                    "outline with original Crystal cave-rock pixels over the same "
                    "animated water, with clear exterior corners.",
                )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    options = parser.parse_args()
    review = Seafoam()
    review.stage()
    review.snow()
    review.water()
    (review.out / "frame-proof.json").write_text(json.dumps(review.frame_proof, indent=2) + "\n")
    review.previews((
        "FR_SEAFOAM_ISLANDS_1F", "FR_SEAFOAM_ISLANDS_B3F", "FR_SEAFOAM_ISLANDS_B4F",
        "FR_FOUR_ISLAND_ICEFALL_CAVE_ENTRANCE", "FR_FOUR_ISLAND_ICEFALL_CAVE_BACK",
    ))
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
