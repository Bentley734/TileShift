"""Present verified native GPU map readbacks without altering their pixels."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont
from validate_gpu import runtime_fingerprint


NAMES = {
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
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    assert report["status"] == "passed", "Native GPU probe must pass before creating comparisons"
    assert report.get("theme") == "gen3", "Re-run the GPU probe after the pooled Gen3 theme migration"
    assert report.get("runtime_inputs") == runtime_fingerprint(Path(__file__).resolve().parents[1]), "Runtime files changed since GPU validation; rerun the probe"
    args.output.mkdir(parents=True, exist_ok=True)
    results = [make(fixture, args.output.resolve()) for fixture in report["fixtures"]
               if (fixture["game"], fixture["map"]) in NAMES]
    assert results, "No supported native GPU map fixtures found"
    verification = {"source": str(args.report.resolve()), "gpu_checks": report["checks"],
                    "runtime_inputs_sha256": report["runtime_inputs"]["sha256"], "comparisons": results}
    args.report.with_name("comparison-verification.json").write_text(json.dumps(verification, indent=2), encoding="utf-8")
    print(json.dumps(verification, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
