"""Review the connected rocky corners and sandy ground of the lower Sevii bank."""

import argparse
import json

from native_gen2_rock_masks import (
    BOULDER_HASH, BOULDER_MASK, KANTO_CORNER_HASHES, KANTO_CORNER_MASKS,
)
from reverse_gen2_kanto_final import DECISIONS, OUT
from reverse_gen2_kanto_finish import CLIFF_MODULES
from reverse_gen2_kanto_room_materials import EMPTY_OVER, Rooms
from reverse_kanto_review import runs


PREFIX = "kanto_sevii_rock_"
PAIRS = {
    "firered": "general__rom_082d507c",
    "leafgreen": "general__rom_082d505c",
}
ROCK_CORNERS = {
    107: (104, "rock_top"),
    109: (106, "rock_top"),
    128: (104, "sandy_ground"),
    130: (106, "sandy_ground"),
    144: (120, "sandy_ground"),
    146: (122, "sandy_ground"),
}
ROCK_MODULES = {
    129: (105, "straight_upper_cap"),
    136: (112, "left_rock_face"),
    178: (125, "right_inner_fold"),
    179: (123, "left_inner_fold"),
}
ROCK_REAR_CAPS = {186: (106, 1), 187: (107, 0)}
SMALL_BOULDERS = (175, 183)
PLAIN_SAND = (519, 837, 840, 848, 849)


class SeviiRock(Rooms):
    def __init__(self):
        super().__init__()
        self.out = OUT / "sevii-rock"
        self.out.mkdir(exist_ok=True)

    def cliff_ref(self, mid):
        map_id, block, quadrant, _ = CLIFF_MODULES[mid]
        return self.gb_ref("crystal", map_id, block, quadrant)

    def check_uses(self, game, pair, mid):
        self.source(game, pair, mid)
        uses = list(self.placements(game, pair, mid))
        assert uses
        for name, _, _, _ in uses:
            assert name.startswith((
                "FR_SIX_ISLAND", "FR_SEVEN_ISLAND", "FR_BIRTH_ISLAND",
            )), (game, pair, mid, name)
        assert self.imp.cell_index(game)[pair, mid]["layer_sha256"]["over"] == EMPTY_OVER

    def selected_ground(self, game, pair):
        key = game, "gen2", pair, 841, None
        row = self.rows.get(key) or self.current[key]
        assert row.get("kind") == "native" and row["donor"]["game"] == "crystal"
        return row["donor"]

    def terrain(self):
        raised = self.cliff_ref(113)
        boulder = self.gb_ref("crystal", "MOUNT_MOON", 24, 0)
        assert boulder["hash"] == BOULDER_HASH
        boulder_parts = [
            dict(donor=boulder, srcX=rect["x"], srcY=rect["y"], **rect)
            for rect in runs(BOULDER_MASK)
        ]
        for game, pair in PAIRS.items():
            floor = self.selected_ground(game, pair)
            for mid, (native_mid, backing) in ROCK_CORNERS.items():
                self.check_uses(game, pair, mid)
                donor = self.cliff_ref(native_mid)
                assert donor["hash"] == KANTO_CORNER_HASHES[native_mid]
                foreground = KANTO_CORNER_MASKS[native_mid]
                parts = [
                    dict(donor=donor, srcX=rect["x"], srcY=rect["y"], **rect)
                    for rect in runs(foreground)
                ]
                feature = PREFIX + backing + "_corner"
                art = self.composite(raised if backing == "rock_top" else floor, parts, feature)
                art["overMask"] = "0" * 256
                self.record(
                    "native_modules", game, pair, mid, feature, art,
                    "The full original Crystal Route 27 stepped corner is placed "
                    "in the same handed position in the source rocky silhouette. "
                    "The true exterior pixels expose the matching selected ground. "
                    "Interior higher folds expose the corresponding native plateau. "
                    "All native rock highlights and outline pixels remain at 1:1.",
                )
            for mid, (native_mid, role) in ROCK_MODULES.items():
                self.check_uses(game, pair, mid)
                feature = PREFIX + role
                art = self.native(self.cliff_ref(native_mid), feature)
                art["overMask"] = "0" * 256
                self.record(
                    "native_modules", game, pair, mid, feature, art,
                    "Actual joined Sevii mountain context establishes the whole "
                    "source cap, wall face or interior fold and its handed "
                    "direction. The complete matching Crystal Kanto rock module "
                    "retains native scale, texture, and shading.",
                )
            for mid, (block, quadrant) in ROCK_REAR_CAPS.items():
                self.check_uses(game, pair, mid)
                source = self.source(game, pair, mid)
                plateau = self.source(game, pair, 105)
                assert source.crop((0, 2, 16, 16)).tobytes() == plateau.crop((0, 2, 16, 16)).tobytes()
                feature = PREFIX + "raised_rear_cap"
                donor = self.gb_ref("crystal", "ROUTE_27", block, quadrant)
                art = self.native(donor, feature)
                art["overMask"] = "0" * 256
                self.record(
                    "native_modules", game, pair, mid, feature, art,
                    "The native upper cliff corner continues into fourteen "
                    "unchanged source plateau rows. The corresponding complete "
                    "Crystal Route 27 back cap retains its original thin upper "
                    "seam over the matching rock texture at 1:1.",
                )
            for mid in SMALL_BOULDERS:
                self.check_uses(game, pair, mid)
                feature = PREFIX + "standalone_round_boulder"
                art = self.composite(floor, boulder_parts, feature)
                art["overMask"] = "0" * 256
                self.record(
                    "native_modules", game, pair, mid, feature, art,
                    "The complete standalone sixteen-pixel boulder uses the "
                    "original Crystal Mount Moon rock. Its exact closed outline "
                    "retains all native highlights and shadows at 1:1. The "
                    "exterior corners expose the selected sandy ground.",
                )
            for mid in PLAIN_SAND:
                self.check_uses(game, pair, mid)
                feature = PREFIX + "sandy_walking_surface"
                art = self.native(floor, feature)
                art["overMask"] = "0" * 256
                self.record(
                    "native_modules", game, pair, mid, feature, art,
                    "Ordinary walkable sand and short grass join use the same "
                    "complete selected Crystal open ground as the actual adjacent "
                    "plain source path. Each native grass patch retains its own "
                    "separate encounter tile.",
                )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    options = parser.parse_args()
    review = SeviiRock()
    review.stage()
    review.terrain()
    review.previews((
        "FR_SEVEN_ISLAND_SEVAULT_CANYON", "FR_SEVEN_ISLAND_SEVAULT_CANYON_ENTRANCE",
        "FR_SEVEN_ISLAND_TANOBY_RUINS", "FR_SIX_ISLAND_WATER_PATH",
        "FR_SIX_ISLAND_RUIN_VALLEY", "FR_BIRTH_ISLAND_EXTERIOR",
    ))
    decisions = json.loads(DECISIONS.read_text())
    decisions["native_modules"] = [
        row for row in decisions.get("native_modules", [])
        if not row.get("feature", "").startswith(PREFIX)
    ] + review.frozen["native_modules"]
    if options.freeze:
        DECISIONS.write_text(json.dumps(decisions, indent=2) + "\n")
    cells = sum(sum(u["count"] for u in review.usage[g, p, m]) for g, _, p, m, _ in review.replacements)
    print(json.dumps(dict(rows=len(review.replacements), cells=cells, frozen=options.freeze)))


if __name__ == "__main__":
    main()
