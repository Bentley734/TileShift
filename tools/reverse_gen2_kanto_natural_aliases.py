"""Check exact shared Kanto terrain against actual neighboring map features."""

import argparse
import json
from collections import Counter

import catalog
from gb_theme_animation import frames
from reverse_gen2_kanto_final import DECISIONS, OUT
from reverse_gen2_kanto_room_materials import EMPTY_OVER, Rooms


PREFIX = "kanto_natural_alias_"
INPUT = OUT.parent / "tileshift-v0360-alias-audit" / "candidates.json"
LANDFORMS = {
    "kanto_sevii_rock_raised_rear_cap", "kanto_sevii_rock_left_inner_fold",
    "kanto_sevii_rock_rock_top_corner", "kanto_sevii_rock_right_inner_fold",
    "kanto_sevii_rock_straight_upper_cap", "kanto_sevii_rock_left_rock_face",
}
GROUND_PROPS = {
    "kanto_sevii_rock_sandy_ground_corner", "kanto_sevii_rock_standalone_round_boulder",
    "kanto_sevii_rock_sandy_walking_surface",
}
LEDGE = "classic_gen2_complete_south_jump_ledge"
WATER_CORNER = "classic_gen2_complete_sevii_harbor_bank_corner"
WATERFALL = "kanto_seafoam_waterfall"
ROCK_NEIGHBORS = {
    104, 105, 106, 107, 108, 109, 112, 113, 114, 115, 117,
    120, 121, 122, 123, 124, 125, 128, 129, 130, 136, 138,
    144, 146, 168, 169, 170, 178, 179, 186, 187,
}


class NaturalAliases(Rooms):
    def __init__(self):
        super().__init__()
        self.out = OUT / "natural-aliases"
        self.out.mkdir(exist_ok=True)
        self.programs = {}
        self.rejected = []

    def effective(self, game, pair, mid):
        key = game, "gen2", pair, mid, None
        return self.rows.get(key) or self.current.get(key)

    def neighbors(self, layout, x, y, radius=1):
        width, height = layout["width"], layout["height"]
        for dx, dy in ((-radius, 0), (radius, 0), (0, -radius), (0, radius)):
            px, py = x + dx, y + dy
            if 0 <= px < width and 0 <= py < height:
                yield layout["mids"][py * width + px]

    def water_signature(self, row):
        if not row or not row.get("animated") or row.get("animationCategory") != "water":
            return None
        donor = row.get("donor")
        if donor is None:
            animated = [part["donor"] for part in row.get("parts", []) if part.get("animated")]
            if len(animated) != 1:
                return None
            donor = animated[0]
        if donor["game"] != "crystal":
            return None
        signature = json.dumps([donor, row["animation"]], sort_keys=True)
        if signature not in self.programs:
            self.programs[signature] = tuple(
                catalog.sha(image.tobytes())
                for image in frames(self.cache, donor, row["animation"], self.packed)
            )
        return self.programs[signature]

    def matches_context(self, candidate, witness, role):
        game, pair, mid = (candidate[key] for key in ("game", "pair", "mid"))
        scopes = list(self.placements(game, pair, mid))
        assert Counter(name for name, _, _, _ in scopes) == {
            context["map"]: context["cells"] for context in candidate["contexts"]
        }
        cell = self.imp.cell_index(game)[pair, mid]
        if role == LEDGE:
            return cell["behavior_hint"] == "MB_JUMP_SOUTH"
        if role == WATERFALL:
            return cell["behavior_hint"] == "MB_WATERFALL"
        if role in LANDFORMS:
            return mid == witness["id"] and all(
                any(n in ROCK_NEIGHBORS for n in self.neighbors(layout, x, y))
                for _, layout, x, y in scopes
            )
        if role in GROUND_PROPS:
            floor = witness.get("base") or witness.get("donor")
            expected = self.gb_image(floor).tobytes()
            for _, layout, x, y in scopes:
                local = list(self.neighbors(layout, x, y)) + list(self.neighbors(layout, x, y, 2))
                neighbors = [self.effective(game, pair, neighbor) for neighbor in local]
                if not any(
                    row and row["kind"] == "native" and not row.get("animated")
                    and row["donor"]["game"] == "crystal" and self.render(row).tobytes() == expected
                    for row in neighbors
                ):
                    return False
            return True
        if role == WATER_CORNER:
            expected = self.water_signature(witness)
            assert expected
            return all(
                any(
                    self.water_signature(self.effective(game, pair, n)) == expected
                    for n in self.neighbors(layout, x, y)
                )
                for _, layout, x, y in scopes
            )
        return False

    def review_aliases(self):
        accepted = Counter()
        candidates = json.loads(INPUT.read_text())
        supported = LANDFORMS | GROUND_PROPS | {LEDGE, WATER_CORNER, WATERFALL}
        for candidate in candidates:
            if candidate["game"] not in self.games or candidate["style"] != "gen2":
                continue
            origin = candidate["witness"]
            role = origin["role"]
            if role not in supported or not candidate["body_cells"]:
                continue
            game, pair, mid = (candidate[key] for key in ("game", "pair", "mid"))
            feature = PREFIX + role
            existing = self.effective(game, pair, mid)
            if existing and existing.get("reverseGen2KantoFinal", {}).get("feature") != feature:
                continue
            cell = self.imp.cell_index(game)[pair, mid]
            if cell["layer_sha256"]["over"] != EMPTY_OVER:
                continue
            witness = self.effective(origin["game"], origin["pair"], origin["mid"])
            if (
                not witness or witness["role"] != role
                or witness["compositionPixelHash"] != origin["compositionPixelHash"]
            ):
                self.rejected.append(dict(game=game, pair=pair, mid=mid, reason="witness changed"))
                continue
            old_cell = self.imp.cell_index(origin["game"])[origin["pair"], origin["mid"]]
            assert cell["pixel_sha256"] == old_cell["pixel_sha256"] == candidate["sourceHash"]
            assert cell["layer_sha256"] == old_cell["layer_sha256"] == candidate["sourceLayers"]
            assert cell["behavior"] == old_cell["behavior"] == candidate["sourceBehavior"]
            self.source(game, pair, mid)
            if not self.matches_context(candidate, witness, role):
                self.rejected.append(dict(game=game, pair=pair, mid=mid, reason="neighbor context"))
                continue
            art = self.art_of(witness)
            assert art["kind"] in ("native", "native_composite")
            art["role"] = feature
            self.record(
                "native_modules", game, pair, mid, feature, art,
                "The complete exact shared source is independently checked "
                "against its actual outdoor placements and the reviewed "
                "terrain counterpart. Every source color, native plane, "
                "and behavior matches the original witness. The same native "
                "Crystal output, transparent edges, and motion remain intact.",
                reviewed_alias={
                    "source_witness": origin,
                    "compositionPixelHash": origin["compositionPixelHash"],
                    "checked_contexts": candidate["contexts"],
                },
            )
            assert catalog.sha(self.replacements[game, "gen2", pair, mid, None].tobytes()) == origin["compositionPixelHash"]
            accepted[role] += candidate["body_cells"]
        return accepted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    options = parser.parse_args()
    review = NaturalAliases()
    review.stage()
    accepted = review.review_aliases()
    review.previews((
        "FR_ROUTE_4", "FR_ROUTE_9", "FR_ROUTE_12", "FR_ROUTE_20",
        "FR_CERULEAN_CITY", "FR_FIVE_ISLAND_MEMORIAL_PILLAR",
    ))
    decisions = json.loads(DECISIONS.read_text())
    decisions["native_modules"] = [
        row for row in decisions.get("native_modules", [])
        if not row.get("feature", "").startswith(PREFIX)
    ] + review.frozen["native_modules"]
    if options.freeze:
        DECISIONS.write_text(json.dumps(decisions, indent=2) + "\n")
    (review.out / "held.json").write_text(json.dumps(review.rejected, indent=2) + "\n")
    print(json.dumps(dict(
        rows=len(review.replacements), cells=accepted.total(), roles=accepted,
        held=len(review.rejected), frozen=options.freeze,
    )))


if __name__ == "__main__":
    main()
