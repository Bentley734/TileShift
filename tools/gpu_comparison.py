"""Present verified native GPU map readbacks without altering their pixels."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont
from validate_gpu import runtime_fingerprint


NAMES = {
    ("crystal", "AZALEA_GYM"): ("Crystal / Azalea Gym", "AzaleaGym", "Original Crystal native colors"),
    ("crystal", "RADIO_TOWER_2F"): ("Crystal / Radio Tower 2F", "RadioTower2F", "Original Crystal native colors"),
    ("crystal", "BILLS_HOUSE"): ("Crystal / Bill's House", "BillsHouse", "Original Crystal native colors"),
    ("crystal", "ILEX_FOREST"): ("Crystal / Ilex Forest", "Ilex", "Original Crystal native colors"),
    ("crystal", "NATIONAL_PARK"): ("Crystal / National Park", "NationalPark", "Original Crystal native colors"),
    ("crystal", "RUINS_OF_ALPH_OUTSIDE"): ("Crystal / Ruins of Alph", "RuinsOfAlph", "Original Crystal native colors"),
    ("crystal", "ROUTE_32"): ("Crystal / Route 32", "Route32", "Original Crystal native colors"),
    ("crystal", "ROUTE_34"): ("Crystal / Route 34", "Route34", "Original Crystal native colors"),
    ("crystal", "ROUTE_38"): ("Crystal / Route 38", "Route38", "Original Crystal native colors"),
    ("crystal", "ROUTE_39"): ("Crystal / Route 39", "Route39", "Original Crystal native colors"),
    ("crystal", "ROUTE_40"): ("Crystal / Route 40", "Route40", "Original Crystal native colors"),
    ("crystal", "ROUTE_41"): ("Crystal / Route 41", "Route41", "Original Crystal native colors"),

    ("crystal", "GOLDENROD_CITY"): ("Crystal / Goldenrod City", "Goldenrod", "Original Crystal native colors"),
    ("gold", "GOLDENROD_CITY"): ("Gold / Goldenrod City", "Gold-Goldenrod", "Original Gold native colors"),
    ("silver", "GOLDENROD_CITY"): ("Silver / Goldenrod City", "Silver-Goldenrod", "Original Silver native colors"),
    ("crystal", "ROUTE_29"): ("Crystal / Route 29", "Route29", "Original Crystal native colors"),
    ("crystal", "ROUTE_35"): ("Crystal / Route 35", "Route35", "Original Crystal native colors"),
    ("crystal", "ROUTE_31"): ("Crystal / Route 31", "Route31", "Original Crystal native colors"),
    ("crystal", "ROUTE_33"): ("Crystal / Route 33", "Route33", "Original Crystal native colors"),
    ("crystal", "ROUTE_36"): ("Crystal / Route 36", "Route36", "Original Crystal native colors"),
    ("crystal", "ROUTE_42"): ("Crystal / Route 42", "Route42", "Original Crystal native colors"),
    ("crystal", "ROUTE_43"): ("Crystal / Route 43", "Route43", "Original Crystal native colors"),
    ("crystal", "ROUTE_44"): ("Crystal / Route 44", "Route44", "Original Crystal native colors"),
    ("crystal", "ROUTE_45"): ("Crystal / Route 45", "Route45", "Original Crystal native colors"),
    ("crystal", "ROUTE_46"): ("Crystal / Route 46", "Route46", "Original Crystal native colors"),
    ("crystal", "SILVER_CAVE_OUTSIDE"): ("Crystal / Mt. Silver Outside", "MtSilver", "Original Crystal native colors"),
    ("crystal", "BLACKTHORN_CITY"): ("Crystal / Blackthorn City", "Blackthorn", "Original Crystal native colors"),
    ("crystal", "LAKE_OF_RAGE"): ("Crystal / Lake of Rage", "LakeOfRage", "Original Crystal native colors"),
    ("crystal", "ECRUTEAK_CITY"): ("Crystal / Ecruteak City", "Ecruteak", "Original Crystal native colors"),
    ("gold", "ECRUTEAK_CITY"): ("Gold / Ecruteak City", "Gold-Ecruteak", "Original Gold native colors"),
    ("crystal", "OLIVINE_CITY"): ("Crystal / Olivine City", "Olivine", "Original Crystal native colors"),
    ("crystal", "CIANWOOD_CITY"): ("Crystal / Cianwood City", "Cianwood", "Original Crystal native colors"),
    ("crystal", "MAHOGANY_TOWN"): ("Crystal / Mahogany Town", "Mahogany", "Original Crystal native colors"),
    ("crystal", "PALLET_TOWN"): ("Crystal / Pallet Town", "Crystal-Pallet", "Original Crystal native colors"),
    ("crystal", "AZALEA_TOWN"): ("Crystal / Azalea Town", "Azalea", "Original Crystal native colors"),
    ("red", "PALLET_TOWN"): ("Red / Pallet Town", "Pallet", "Original monochrome"),
    ("crystal", "NEW_BARK_TOWN"): ("Crystal / New Bark Town", "NewBark", "Original Crystal DAY colors"),
    ("red", "VIRIDIAN_CITY"): ("Red / Viridian City", "Viridian", "Original monochrome"),
    ("red", "ROUTE_1"): ("Red / Route 1", "Route1", "Original monochrome"),
    ("red", "MT_MOON_1F"): ("Red / Mt. Moon 1F", "MtMoon", "Original monochrome"),
    ("red", "MT_MOON_B2F"): ("Red / Mt. Moon B2F", "MtMoonB2", "Original monochrome"),
    ("red", "VIRIDIAN_FOREST"): ("Red / Viridian Forest", "ViridianForest", "Original monochrome"),
    ("red", "SAFARI_ZONE_WEST"): ("Red / Safari Zone West", "SafariWest", "Original monochrome"),
    ("red", "REDS_HOUSE_1F"): ("Red / Red's House 1F", "RedsHouse", "Original monochrome"),
    ("red", "BLUES_HOUSE"): ("Red / Blue's House", "BluesHouse", "Original monochrome"),
    ("red", "VERMILION_CITY"): ("Red / Vermilion City", "Vermilion", "Original monochrome"),
    ("red", "ROUTE_12"): ("Red / Route 12", "Route12", "Original monochrome"),
    ("red", "SEAFOAM_ISLANDS_1F"): ("Red / Seafoam Islands 1F", "Seafoam", "Original monochrome"),
    ("red", "SEAFOAM_ISLANDS_B4F"): ("Red / Seafoam Islands B4F", "SeafoamB4", "Original monochrome"),
    ("red", "CERULEAN_CITY"): ("Red / Cerulean City", "Cerulean", "Original monochrome"),
    ("red", "VIRIDIAN_MART"): ("Red / Viridian Mart", "ViridianMart", "Original monochrome"),
    ("red", "VICTORY_ROAD_1F"): ("Red / Victory Road 1F", "VictoryRoad", "Original monochrome"),
    ("crystal", "CHERRYGROVE_CITY"): ("Crystal / Cherrygrove City", "Cherrygrove", "Original Crystal native colors"),
    ("crystal", "VIOLET_CITY"): ("Crystal / Violet City", "Violet", "Original Crystal native colors"),
    ("gold", "VIOLET_CITY"): ("Gold / Violet City", "Gold-Violet", "Original Gold native colors"),
    ("silver", "VIOLET_CITY"): ("Silver / Violet City", "Silver-Violet", "Original Silver native colors"),
    ("crystal", "CERULEAN_CITY"): ("Crystal / Cerulean City", "Crystal-Cerulean", "Original Crystal native colors"),
    ("crystal", "VERMILION_CITY"): ("Crystal / Vermilion City", "Crystal-Vermilion", "Original Crystal native colors"),
    ("crystal", "ROUTE_12"): ("Crystal / Route 12", "Crystal-Route12", "Original Crystal native colors"),
    ("crystal", "ELMS_LAB"): ("Crystal / Elm's Lab", "ElmsLab", "Original Crystal native colors"),
    ("crystal", "UNION_CAVE_B1F"): ("Crystal / Union Cave B1F", "UnionCave", "Original Crystal native colors"),
    ("crystal", "ICE_PATH_B1F"): ("Crystal / Ice Path B1F", "IcePath", "Original Crystal native colors"),
}


for _map in ('PLAYERS_HOUSE_1F', 'PLAYERS_HOUSE_2F', 'EARLS_POKEMON_ACADEMY', 'KURTS_HOUSE', 'DANCE_THEATER', 'VIOLET_POKECENTER_1F', 'GOLDENROD_GAME_CORNER', 'OLIVINE_CAFE', 'GOLDENROD_DEPT_STORE_2F', 'GOLDENROD_DEPT_STORE_6F', 'GOLDENROD_DEPT_STORE_ROOF', 'GOLDENROD_DEPT_STORE_ELEVATOR', 'GOLDENROD_UNDERGROUND_WAREHOUSE', 'TEAM_ROCKET_BASE_B1F', 'TEAM_ROCKET_BASE_B2F', 'TEAM_ROCKET_BASE_B3F', 'RUINS_OF_ALPH_RESEARCH_CENTER', 'POKECOM_CENTER_ADMIN_OFFICE_MOBILE', 'SPROUT_TOWER_3F', 'TIN_TOWER_6F', 'TIN_TOWER_ROOF', 'OLIVINE_LIGHTHOUSE_6F', 'GOLDENROD_GYM', 'ECRUTEAK_GYM', 'MAHOGANY_GYM', 'BLACKTHORN_GYM_1F', 'GOLDENROD_BIKE_SHOP', 'BATTLE_TOWER_OUTSIDE', 'BATTLE_TOWER_1F', 'BATTLE_TOWER_HALLWAY', 'BATTLE_TOWER_ELEVATOR', 'BATTLE_TOWER_BATTLE_ROOM', 'DRAGONS_DEN_B1F', 'WHIRL_ISLAND_LUGIA_CHAMBER', 'TOHJO_FALLS', 'OLIVINE_PORT', 'GOLDENROD_MAGNET_TRAIN_STATION', 'RADIO_TOWER_5F', 'RUINS_OF_ALPH_INNER_CHAMBER', 'RUINS_OF_ALPH_KABUTO_CHAMBER', 'RUINS_OF_ALPH_KABUTO_WORD_ROOM', 'DRAGON_SHRINE'):
    NAMES['crystal', _map] = ('Crystal / ' + _map.replace('_', ' ').title(), 'Johto-' + _map.title().replace('_', ''), 'Original Crystal native colors')


# All completed Gen1 towns and representative interior GPU fixtures.
for _game in ('red', 'blue', 'yellow'):
    for _map in ('PEWTER_CITY', 'LAVENDER_TOWN', 'CELADON_CITY', 'FUCHSIA_CITY', 'SAFFRON_CITY', 'CINNABAR_ISLAND', 'INDIGO_PLATEAU', 'ROUTE_2', 'ROUTE_3', 'ROUTE_9', 'ROUTE_10', 'ROUTE_17', 'ROUTE_19', 'ROUTE_20', 'ROUTE_21', 'ROUTE_23', 'ROUTE_24', 'ROUTE_25', 'SAFARI_ZONE_NORTH', 'SAFARI_ZONE_EAST', 'SAFARI_ZONE_CENTER', 'REDS_HOUSE_2F', 'CERULEAN_TRASHED_HOUSE', 'OAKS_LAB', 'CINNABAR_LAB', 'POKEMON_FAN_CLUB', 'GAME_CORNER', 'CELADON_MART_3F', 'CELADON_MART_ROOF', 'CELADON_MART_ELEVATOR', 'CELADON_HOTEL', 'VIRIDIAN_POKECENTER', 'ROUTE_11_GATE_1F', 'ROUTE_22_GATE', 'UNDERGROUND_PATH_NORTH_SOUTH', 'SILPH_CO_3F', 'SILPH_CO_11F', 'ROCKET_HIDEOUT_B2F', 'POWER_PLANT', 'POKEMON_MANSION_1F', 'MUSEUM_1F', 'MUSEUM_2F', 'POKEMON_TOWER_3F', 'LANCES_ROOM', 'SAFFRON_GYM', 'VERMILION_GYM', 'CELADON_GYM', 'SS_ANNE_1F', 'SS_ANNE_KITCHEN', 'SS_ANNE_1F_ROOMS', 'SS_ANNE_B1F_ROOMS', 'SS_ANNE_CAPTAINS_ROOM', 'VERMILION_DOCK', 'SUMMER_BEACH_HOUSE'):
        NAMES.setdefault((_game, _map), (_game.capitalize() + ' / ' + _map.replace('_', ' ').title(), _game.capitalize() + '-' + _map.title().replace('_', ''), 'Original monochrome'))


def readback(ref: dict) -> Image.Image:
    path = Path(ref["path"])
    image = Image.open(path).convert("RGBA")
    assert image.size == (ref["width"], ref["height"]), f"GPU size changed: {path}"
    assert hashlib.sha256(image.tobytes()).hexdigest() == ref["rgba_sha256"], f"GPU readback changed: {path}"
    assert image.getchannel("A").getextrema() == (255, 255), "Map panels must be opaque native readbacks"
    return image.convert("RGB")


def make(fixture: dict, output: Path) -> dict:
    title, stem, source_label = NAMES[(fixture["game"], fixture["map"])]
    before, after = readback(fixture["before"]), readback(fixture["after"])
    assert before.size == after.size
    coverage = fixture["coverage"]
    assert coverage["animation_frame"] == 0 and not coverage["actors_rendered"]
    assert coverage["visible_cells"] == before.width * before.height // 256
    replaced, total = coverage["replaced_occurrences"], coverage["visible_cells"]
    preserved = coverage["preserved_native_occurrences"]
    assert replaced + preserved == total
    scale, padding, gap = 2, 18, 20
    size = (before.width * scale, before.height * scale)
    left = before.resize(size, Image.Resampling.NEAREST)
    right = after.resize(size, Image.Resampling.NEAREST)
    font_dir = Path("C:/Windows/Fonts")
    title_font = ImageFont.truetype(str(font_dir / "arial.ttf"), 20)
    body_font = ImageFont.truetype(str(font_dir / "arial.ttf"), 15)
    width = padding * 2 + gap + size[0] * 2
    def lines(text: str, font, available: int) -> list[str]:
        result, current = [], ""
        for word in text.split():
            candidate = (current + " " + word).strip()
            if current and font.getlength(candidate) > available:
                result.append(current)
                current = word
            else:
                current = candidate
        return result + ([current] if current else [])

    complete = replaced == total
    scope = (f"Fully retiled {title.split(' / ', 1)[1]} background."
             if complete else "This is a partial tileset replacement.")
    status = "All background cells replaced." if complete else "Unresolved cells keep native art."
    if fixture.get("source_daytime"):
        source_label = f"Original {fixture['game'].capitalize()} native {fixture['source_daytime']} colors"
    source_label = fixture.get('comparison_before_label', source_label)
    heading_lines = lines("DEVELOPMENT — " + title, title_font, width - padding * 2)
    info_lines = lines("Actual native GPU background renders; nearest-neighbor pixels. " + scope, body_font, width - padding * 2)
    status_lines = lines("Animation frame 0. Reviewed replacements only. " + status + " No actors rendered.", body_font, width - padding * 2)
    left_labels = lines(source_label, body_font, size[0])
    right_labels = lines(fixture.get('comparison_after_label', "Gen 3 style — reviewed cells only"), body_font, size[0])
    labels_y = 13 + len(heading_lines) * 25 + 4 + len(info_lines) * 18 + 4 + len(status_lines) * 18 + 4
    top = labels_y + max(len(left_labels), len(right_labels)) * 18 + 12
    native_status = f"Remaining {preserved} cells keep native art. " if preserved else ""
    caption = (f"Replaced {replaced}/{total} visible cells ({replaced / total:.1%}); "
               f"{coverage['unique_mappings_used']} unique mappings. {native_status}No actors rendered.")
    caption_lines = lines(caption, body_font, width - padding * 2)
    credit = (fixture.get("third_party_tree") or fixture.get("boundary_tree") or {}).get("credit")
    credit_lines = lines("Compact tree: " + credit + ".", body_font, width - padding * 2) if credit else []
    bottom = max(56, 15 + len(caption_lines) * 18 + (2 + len(credit_lines) * 18 if credit_lines else 0) + 3)
    canvas = Image.new("RGB", (width, top + size[1] + bottom), "#18212b")
    draw = ImageDraw.Draw(canvas)
    y = 13
    for group, font, step, color in ((heading_lines, title_font, 25, "#f5f7fa"),
                                    (info_lines, body_font, 18, "#c4cdd8"),
                                    (status_lines, body_font, 18, "#c4cdd8")):
        for line in group:
            draw.text((padding, y), line, font=font, fill=color)
            y += step
        y += 4
    rx = padding + size[0] + gap
    for x, group in ((padding, left_labels), (rx, right_labels)):
        for i, line in enumerate(group):
            draw.text((x, labels_y + i * 18), line, font=body_font, fill="#f5f7fa")
    canvas.paste(left, (padding, top))
    canvas.paste(right, (rx, top))
    y = top + size[1] + 15
    for line in caption_lines:
        draw.text((padding, y), line, font=body_font, fill="#c4cdd8")
        y += 18
    y += 2
    for line in credit_lines:
        draw.text((padding, y), line, font=body_font, fill="#c4cdd8")
        y += 18
    target = output / f"TileShift-Gen3-{stem}-comparison.png"
    canvas.save(target)
    # Verify saved panels, not just intermediate images, against exact GPU RGB.
    saved = Image.open(target).convert("RGB")
    for panel, x in ((left, padding), (right, rx)):
        actual = saved.crop((x, top, x + size[0], top + size[1]))
        assert ImageChops.difference(actual, panel).getbbox() is None, "Comparison panel pixels changed"
    return {"game": fixture["game"], "map": fixture["map"], "output": str(target),
            "coverage": coverage, "scale": scale, "panels_exact_gpu_rgb": True,
            "before_gpu_rgba_sha256": fixture["before"]["rgba_sha256"],
            "after_gpu_rgba_sha256": fixture["after"]["rgba_sha256"],
            "comparison_png_sha256": hashlib.sha256(target.read_bytes()).hexdigest()}


def main() -> int:
    workspace = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=workspace / ".work/tileshift-gpu/report.json")
    parser.add_argument("--output", type=Path, default=workspace)
    parser.add_argument("--games", help="Optional comma-separated cartridge IDs to include")
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    assert report["status"] == "passed", "Native GPU probe must pass before creating comparisons"
    assert report.get("theme") == "gen3", "Re-run the GPU probe after the pooled Gen3 theme migration"
    assert report.get("runtime_inputs") == runtime_fingerprint(Path(__file__).resolve().parents[1]), "Runtime files changed since GPU validation; rerun the probe"
    games = set(args.games.split(",")) if args.games else None
    if games is not None:
        assert games and games <= {"red", "blue", "yellow", "gold", "silver", "crystal"}, "Unsupported comparison game"
    args.output.mkdir(parents=True, exist_ok=True)
    results = [make(fixture, args.output.resolve()) for fixture in report["fixtures"]
               if (fixture["game"], fixture["map"]) in NAMES and (games is None or fixture["game"] in games)]
    assert results, "No supported native GPU map fixtures found"
    verification = {"source": str(args.report.resolve()), "gpu_checks": report["checks"],
                    "runtime_inputs_sha256": report["runtime_inputs"]["sha256"], "comparisons": results}
    args.report.with_name("comparison-verification.json").write_text(json.dumps(verification, indent=2), encoding="utf-8")
    print(json.dumps(verification, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
