"""Present verified native GPU map readbacks without altering their pixels."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont
from validate_gpu import runtime_fingerprint


NAMES = {
    ("red", "PALLET_TOWN"): ("Red / Pallet Town", "Pallet", "Original monochrome"),
    ("crystal", "NEW_BARK_TOWN"): ("Crystal / New Bark Town", "NewBark", "Original Crystal DAY colors"),
    ("red", "VIRIDIAN_CITY"): ("Red / Viridian City", "Viridian", "Original monochrome"),
    ("red", "ROUTE_1"): ("Red / Route 1", "Route1", "Original monochrome"),
    ("red", "MT_MOON_1F"): ("Red / Mt. Moon 1F", "MtMoon", "Original monochrome"),
    ("red", "SEAFOAM_ISLANDS_1F"): ("Red / Seafoam Islands 1F", "Seafoam", "Original monochrome"),
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
    scale, padding, gap, top, bottom = 2, 18, 20, 116, 56
    size = (before.width * scale, before.height * scale)
    left = before.resize(size, Image.Resampling.NEAREST)
    right = after.resize(size, Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (padding * 2 + gap + size[0] * 2, top + size[1] + bottom), "#18212b")
    draw = ImageDraw.Draw(canvas)
    font_dir = Path("C:/Windows/Fonts")
    title_font = ImageFont.truetype(str(font_dir / "arial.ttf"), 20)
    body_font = ImageFont.truetype(str(font_dir / "arial.ttf"), 15)
    draw.text((padding, 13), "DEVELOPMENT — " + title, font=title_font, fill="#f5f7fa")
    complete = replaced == total
    complete_names = {"Pallet": "Pallet", "Route1": "Route 1", "NewBark": "New Bark Town"}
    scope = (f"Fully retiled {complete_names[stem]} background."
             if complete and stem in complete_names else "This is a partial tileset replacement.")
    draw.text((padding, 42), "Actual native GPU background renders; nearest-neighbor pixels. " + scope, font=body_font, fill="#c4cdd8")
    status = "All background cells replaced." if complete else "Unresolved cells keep native art."
    draw.text((padding, 64), "Animation frame 0. Reviewed replacements only. " + status + " No actors rendered.", font=body_font, fill="#c4cdd8")
    draw.text((padding, 86), source_label, font=body_font, fill="#f5f7fa")
    rx = padding + size[0] + gap
    draw.text((rx, 86), "Gen 3 style — reviewed cells only", font=body_font, fill="#f5f7fa")
    canvas.paste(left, (padding, top))
    canvas.paste(right, (rx, top))
    native_status = f"Remaining {preserved} cells keep native art. " if preserved else ""
    caption = (f"Replaced {replaced}/{total} visible cells ({replaced / total:.1%}); "
               f"{coverage['unique_mappings_used']} unique mappings. {native_status}No actors rendered.")
    draw.text((padding, top + size[1] + 15), caption, font=body_font, fill="#c4cdd8")
    credit = (fixture.get("third_party_tree") or fixture.get("boundary_tree") or {}).get("credit")
    if credit:
        draw.text((padding, top + size[1] + 35), "Compact tree: " + credit + ".", font=body_font, fill="#c4cdd8")
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
