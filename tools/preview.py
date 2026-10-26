"""Render honest development previews from native imports and reviewed mappings.

Outputs are local extracted background-map review images, not game screenshots
or distributable assets. Only fingerprint-checked reviewed cells are replaced.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import struct
import zlib

from PIL import Image, ImageChops, ImageDraw, ImageFont
import catalog

WORKSPACE = Path(__file__).resolve().parents[2]


def read_reviewed(path):
    # This is authored mod code with an ipairs expansion, not a generated data
    # table. It is trusted local source; imported ROM data uses catalog's loader.
    rows = catalog.plain(catalog.LUA.execute(path.read_text(encoding="utf-8-sig")))
    assert isinstance(rows, list), "Reviewed mappings must return an array"
    return rows


def palette_set(palettes, map_def, daytime="DAY"):
    special = palettes.get("specialTilesets", {}).get(map_def["tileset"])
    if map_def["tileset"] == "TILESET_ICE_PATH" and map_def.get("environment") == "INDOOR":
        special = None
    if special:
        result = copy.deepcopy(catalog.lua_array(special))
    else:
        indices = palettes["environments"][map_def["environment"]][daytime]
        result = [copy.deepcopy(catalog.dict_at(palettes["bg"], index)) for index in catalog.lua_array(indices)]
    if map_def.get("environment") in ("TOWN", "ROUTE"):
        roof = catalog.dict_at(palettes.get("roofs"), map_def["group"])
        if roof:
            colors = roof["mornDay" if daytime in ("MORN", "DAY") else "nite"]
            colors = catalog.lua_array(colors)
            slot = palettes.get("roofSlot", 7) - 1
            result[slot][1] = copy.deepcopy(colors[0])
            result[slot][2] = copy.deepcopy(colors[1])
    return result


def native_cell(sheet, ts, block, quadrant, palettes=None, roof=None, animation_tiles=None):
    qx, qy = quadrant % 2 * 2, quadrant // 2 * 2
    offsets = (qy * 4 + qx, qy * 4 + qx + 1, (qy + 1) * 4 + qx, (qy + 1) * 4 + qx + 1)
    out = Image.new("RGBA", (16, 16))
    for i, offset in enumerate(offsets):
        raw = block[offset]
        tile, attrs = catalog.gb_tile(sheet, ts, raw)
        assert attrs["source_pixels_complete"], f"Native map references missing tile {raw}"
        if animation_tiles and raw in animation_tiles:
            tile = animation_tiles[raw]
        if roof is not None and 10 <= raw <= 18:
            tile = roof.crop(((raw - 10) * 8, 0, (raw - 9) * 8, 8)).convert("RGBA")
            if attrs.get("xFlip"):
                tile = tile.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            if attrs.get("yFlip"):
                tile = tile.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        if palettes is not None:
            colors = palettes[attrs.get("palette", 1) - 1]
            tile.putdata([tuple(colors[max(0, min(3, round((255 - r) * 3 / 255)))]) + (a,)
                          for r, g, b, a in tile.get_flattened_data()])
        out.paste(tile, (i % 2 * 8, i // 2 * 8))
    return out


def gen1_animation_tiles(cache, game, ts, sheet, tick=0):
    """Native TileRenderer defaults at a deterministic60Hz animation tick.

    Raw source fingerprints still use the unmodified imported atlas. These
    tiles apply only to the displayed native background, including uncovered
    8px water fragments and flowers inside otherwise unreviewed16px cells.
    """
    animation = ts.get("animation")
    if animation not in ("TILEANIM_WATER", "TILEANIM_WATER_FLOWER"):
        return {}
    has_flowers = animation == "TILEANIM_WATER_FLOWER"
    period = 21 if has_flowers else 20
    offsets = (1, 2, 3, 2, 1, 0, 7, 0)
    water_step = (tick + (1 if has_flowers else 0)) // period % len(offsets)
    water, _ = catalog.gb_tile(sheet, ts, 0x14)
    tiles = {0x14: ImageChops.offset(water, offsets[water_step], 0)}
    if has_flowers:
        sequence = (1, 2, 3, 1, 1, 2, 3, 1)
        flower_frame = sequence[tick // period % len(sequence)]
        flower = Image.open(cache / game / f"assets/generated/tilesets/flower{flower_frame}.png").convert("RGBA")
        assert flower.size == (8, 8)
        tiles[0x03] = flower
    return tiles


def native_donor(cache, ref, packed, selected_layers=None, layer_hashes=None):
    if ref.get("kind") == "field_object":
        image = native_field_object(cache, ref, packed)
        if selected_layers is None:
            return image
        decoded = {"under": image, "over": Image.new("RGBA", (16, 16))}
    else:
        decoded = None
    key = ref["game"], ref["tileset"]
    if decoded is None and key not in packed:
        root = cache / ref["game"] / "data/generated/gba/native" / ref["tileset"]
        palette = catalog.read_palettes(root / "palettes.bin")
        mids, pixels, _ = catalog.read_idx(root / "mids.idx")
        layers = {"under": pixels}
        for layer in ("mid", "over"):
            path = root / f"mids_{layer}.idx"
            if path.exists():
                more_mids, more_pixels, _ = catalog.read_idx(path)
                assert mids == more_mids
                layers[layer] = more_pixels
        packed[key] = mids, palette, layers
    if decoded is None:
        mids, palette, layers = packed[key]
        slot = mids.index(ref["id"])
        decoded = {layer: catalog.rgba_native(pixels[slot * 256:(slot + 1) * 256], palette, layer != "under")
                   for layer, pixels in layers.items()}
    out = Image.new("RGBA", (16, 16))
    for layer in ("under", "mid", "over"):
        if layer in decoded:
            out = Image.alpha_composite(out, decoded[layer])
    assert ref.get("kind") == "field_object" or catalog.sha(out.tobytes()) == ref["hash"], "Donor pixel fingerprint changed"
    if selected_layers is not None:
        assert selected_layers and isinstance(layer_hashes, dict), "Selected layers need fingerprints"
        assert selected_layers == [name for name in ("under", "mid", "over") if name in selected_layers]
        assert set(layer_hashes) == set(selected_layers)
        out = Image.new("RGBA", (16, 16))
        for layer in selected_layers:
            assert layer in decoded, "Selected native layer is unavailable"
            image = decoded[layer]
            assert catalog.sha(image.tobytes()) == layer_hashes[layer], "Selected native layer fingerprint changed"
            out = Image.alpha_composite(out, image)
    return out


def asset_image(row, mod_root):
    path = (mod_root / row["asset"]).resolve()
    assert path.is_relative_to(mod_root.resolve()), "Asset escaped the mod directory"
    raw = path.read_bytes()
    if row.get("assetFileHash"):
        assert catalog.sha(raw) == row["assetFileHash"], f"Third-party asset file hash changed: {row['asset']}"
    image = Image.open(path).convert("RGBA")
    assert image.size == (16, 16), "Reviewed assets must be exactly16x16 pixels"
    if row.get("assetPixelHash"):
        assert catalog.sha(image.tobytes()) == row["assetPixelHash"], f"Third-party asset pixel hash changed: {row['asset']}"
    return image


def native_field_object(cache, ref, packed):
    """Read a complete native16px field-object frame without runtime mounts."""
    assert ref["game"] in ("ruby", "sapphire", "emerald", "firered", "leafgreen") and ref["tileset"] == "ow"
    assert ref.get("quadrant") is None and ref.get("kind") == "field_object"
    key = ("field_object", ref["game"], ref["id"], ref.get("frame", 0), ref["hash"], ref["metaHash"], ref["rgbaHash"])
    if key in packed:
        return packed[key]
    root = cache / ref["game"] / "data/generated/gba/ow"
    meta = (root / f"{ref['id']}.meta").read_bytes()
    assert len(meta) == 120 and meta[:4] == b"SVOW" and meta[4] == 4, "Invalid native field-object metadata"
    assert catalog.sha(meta) == ref["metaHash"], "Native field-object metadata changed"
    gid, width, height, frames = struct.unpack_from("<4H", meta, 6)
    assert gid == ref["id"] and width == 16 and height == 16 and 1 <= frames <= 256
    frame = ref.get("frame", 0)
    assert isinstance(frame, int) and 0 <= frame < frames, "Native field-object frame is unavailable"
    raw = (root / f"{gid}.rgba").read_bytes()
    if len(raw) != width * height * frames * 4:
        raw = zlib.decompress(raw)
    assert len(raw) == width * height * frames * 4, "Native field-object pixels are incomplete"
    assert catalog.sha(raw) == ref["rgbaHash"], "Native field-object RGBA changed"
    image = Image.frombytes("RGBA", (16, 16), raw[frame * 1024:(frame + 1) * 1024])
    assert catalog.sha(image.tobytes()) == ref["hash"], "Native field-object pixels changed"
    packed[key] = image
    return image


def native_water_frames(cache, row, packed):
    """Decode a reviewed native bank, keeping its original frame order."""
    ref, spec = row["donor"], row["animation"]
    key = ("animation", ref["game"], ref["tileset"], ref["id"], ref.get("hash"), json.dumps(spec, sort_keys=True))
    if key in packed:
        return packed[key]
    native_donor(cache, ref, packed)
    root = cache / ref["game"] / "data/generated/gba/native" / ref["tileset"]
    manifest_bytes = (root / "anim_manifest.lua").read_bytes()
    assert catalog.sha(manifest_bytes) == spec["manifestHash"], "Native animation manifest changed"
    manifest = catalog.read_lua(root / "anim_manifest.lua")
    if ref["game"] in ("firered", "leafgreen"):
        schedules = {"water": (16, 1, 8), "sand": (8, 0, 8), "flower": (16, 2, 5)}
        assert spec["bank"] in schedules, "Unreviewed legacy animation bank"
        period, phase, count = schedules[spec["bank"]]
        bank = manifest[spec["bank"]]
        assert bank["frames"] == count and ref["id"] in bank["mids"]
        assert spec.get("period", period) == period and spec.get("phase", phase) == phase
        index = bank["mids"].index(ref["id"])
        raw = (root / f"anim_{spec['bank']}.rgba").read_bytes()
        expected = count * len(bank["mids"]) * 1024
        if len(raw) != expected:
            raw = zlib.decompress(raw)
        assert len(raw) == expected and catalog.sha(raw) == spec["hash"], "Native animation bank changed"
        mids, palette, layers = packed[(ref["game"], ref["tileset"])]
        slot = mids.index(ref["id"])
        overlay = catalog.rgba_native(layers["over"][slot * 256:(slot + 1) * 256], palette, True) if "over" in layers else Image.new("RGBA", (16, 16))
        frames = []
        for frame in range(count):
            offset = (frame * len(bank["mids"]) + index) * 1024
            image = Image.frombytes("RGBA", (16, 16), raw[offset:offset + 1024])
            frames.append(Image.alpha_composite(image, overlay))
        if spec.get("frame0Hash"):
            assert catalog.sha(frames[0].tobytes()) == spec["frame0Hash"], "Native first animation frame changed"
        packed[key] = frames
        return frames
    assert ref["game"] == "emerald" and manifest["family"] == "rse", "Unsupported RSE donor"
    matching = [b for b in manifest["banks"] if b["name"] == spec["bank"]]
    assert len(matching) == 1, "Missing or duplicate native animation bank"
    bank = matching[0]
    assert bank["fn"] == "mod" and bank["kind"] == "tiles", "Unsupported native animation schedule"
    count, period, phase = bank["frames"], bank["period"], bank.get("phase", 0)
    assert isinstance(count, int) and 2 <= count <= 256
    assert isinstance(period, int) and period > 0 and isinstance(phase, int) and 0 <= phase < period
    for field, actual in (("frames", count), ("period", period), ("phase", phase), ("counter", bank.get("counter"))):
        assert field not in spec or spec[field] == actual, "Native animation timing changed"
    if "counterMax" in spec:
        assert manifest["counters"][bank["counter"]]["max"] == spec["counterMax"], "Native animation counter changed"
    under_ids, over_ids = bank.get("mids", []), bank.get("overMids", [])
    assert ref["id"] in under_ids or ref["id"] in over_ids, "Donor is not targeted by this animation bank"
    assert list(under_ids).count(ref["id"]) <= 1 and list(over_ids).count(ref["id"]) <= 1
    assert all(ref["id"] not in b.get("mids", []) and ref["id"] not in b.get("overMids", [])
               for b in manifest["banks"] if b["name"] != spec["bank"])
    mids, palette, layers = packed[(ref["game"], ref["tileset"])]
    slot = mids.index(ref["id"])
    for other in manifest["banks"]:
        if other is not bank and other.get("kind") == "palette" and "paletteSlot" in other:
            for layer, pixels in layers.items():
                assert not any(pixel // 16 == other["paletteSlot"] for pixel in pixels[slot * 256:(slot + 1) * 256]
                               if layer == "under" or pixel != 0), "Donor also uses a palette animation"
    base_under = catalog.rgba_native(layers["under"][slot * 256:(slot + 1) * 256], palette)
    base_over = catalog.rgba_native(layers["over"][slot * 256:(slot + 1) * 256], palette, True) if "over" in layers else Image.new("RGBA", (16, 16))
    blobs = []
    for file, ids, masks, upper in ((bank.get("file"), under_ids, bank.get("quads"), False),
                                    (bank.get("overFile"), over_ids, bank.get("overQuads"), True)):
        if not file:
            assert ref["id"] not in ids, "Native animation pixels are unavailable"
            blobs.append(None)
            continue
        assert Path(file).name == file, "Native animation path escaped its tileset"
        raw = (root / file).read_bytes()
        expected = count * len(ids) * 256
        if len(raw) != expected:
            raw = zlib.decompress(raw)
        assert len(raw) == expected, "Native animation bank pixels are incomplete"
        blobs.append(raw)
    assert blobs[0] is not None or blobs[1] is not None
    assert catalog.sha(blobs[0] if blobs[0] is not None else blobs[1]) == spec["hash"], "Native animation bank changed"
    if blobs[0] is not None and blobs[1] is not None:
        assert catalog.sha(blobs[1]) == spec.get("overHash"), "Native over animation bank changed"
    frames = []
    changed = False
    for frame in range(count):
        under, over = base_under.copy(), base_over.copy()
        for image, raw, ids, masks, upper in ((under, blobs[0], under_ids, bank.get("quads"), False),
                                               (over, blobs[1], over_ids, bank.get("overQuads"), True)):
            if ref["id"] not in ids:
                continue
            index = ids.index(ref["id"])
            mask = masks[index] if masks else 15
            assert isinstance(mask, int) and 0 <= mask <= 15, "Invalid native animation quadrant mask"
            changed = changed or mask != 0
            if not upper and "quadMask" in spec:
                assert spec["quadMask"] == mask, "Native animation coverage changed"
            offset = (frame * len(ids) + index) * 256
            piece = catalog.rgba_native(raw[offset:offset + 256], palette, upper)
            for q in range(4):
                if mask & (1 << q):
                    x, y = q % 2 * 8, q // 2 * 8
                    image.paste(piece.crop((x, y, x + 8, y + 8)), (x, y))
        # Native under already contains BG1; no stale static middle layer.
        frames.append(Image.alpha_composite(under, over))
    assert changed, "Native bank does not change donor pixels"
    if spec.get("frame0Hash"):
        assert catalog.sha(frames[0].tobytes()) == spec["frame0Hash"], "Native first animation frame changed"
    packed[key] = frames
    return frames


def replacement_image(cache, row, packed, mod_root):
    if row.get("donor"):
        if row.get("animated"):
            return native_water_frames(cache, row, packed)[0]
        return native_donor(cache, row["donor"], packed)
    if row.get("parts"):
        out = native_donor(cache, row["base"], packed).copy() if row.get("base") else Image.new("RGBA", (16, 16))
        for part in row["parts"]:
            sx, sy = part.get("srcX", 0), part.get("srcY", 0)
            image = native_donor(cache, part["donor"], packed, part.get("layers"), part.get("layerHashes")).crop(
                (sx, sy, sx + part["w"], sy + part["h"]))
            out.alpha_composite(image, (part.get("x", 0), part.get("y", 0)))
        return out
    image = asset_image(row, mod_root)
    if row.get("base"):
        return Image.alpha_composite(native_donor(cache, row["base"], packed), image)
    return image


def verify(rows, cache, catalogs, mod_root):
    indices = {}
    for game, payload in catalogs.items():
        indices[game] = {r["id"]: r for r in payload["cells"]}
    checked, source_sets, source_sheets, source_maps, packed = 0, {}, {}, {}, {}
    for row in rows:
        assert row["status"] == "reviewed"
        source_id = f"{row['game']}:{row['tileset']}:{row['id']}:{row['quadrant']}"
        source = indices[row["game"]][source_id]
        assert source["grayscale_pixel_sha256"] == row["sourceHash"], f"Source hash changed: {source_id}"
        assert source["source_pixels_complete"]
        # Re-read the live imported metadata and pixels as well as the catalog.
        # Catalog snapshots alone must not allow a changed import to pass.
        game = row["game"]
        if game not in source_sets:
            source_sets[game] = catalog.read_lua(cache / game / "data/generated/tilesets.lua")
        ts = source_sets[game][row["tileset"]]
        source_key = game, row["tileset"]
        if source_key not in source_sheets:
            source_sheets[source_key] = Image.open(cache / game / ts["image"])
        block = catalog.lua_array(catalog.dict_at(ts["blocks"], row["id"] + 1))
        actual_source = native_cell(source_sheets[source_key], ts, block, row["quadrant"])
        assert catalog.sha(actual_source.tobytes()) == row["sourceHash"], f"Live source import changed: {source_id}"
        if row.get("map"):
            if game not in source_maps:
                source_maps[game] = catalog.read_lua(cache / game / "data/generated/maps.lua")
            scoped = source_maps[game][row["map"]]
            assert scoped["tileset"] == row["tileset"] and row["id"] in scoped["blocks"]
            if "x" in row or "y" in row:
                x, y = row["x"], row["y"]
                assert 0 <= x < scoped["width"] * 2 and 0 <= y < scoped["height"] * 2
                assert row["quadrant"] == y % 2 * 2 + x % 2
                assert scoped["blocks"][y // 2 * scoped["width"] + x // 2] == row["id"], "Position source layout changed"
            if row.get("role") == "coastal_ocean_water_interior":
                if row["map"] == "PALLET_TOWN":
                    assert scoped["connections"]["south"]["map"] == "ROUTE_21"
                else:
                    assert row["map"] == "NEW_BARK_TOWN" and scoped["connections"]["east"]["mapId"] == "ROUTE_27"
        donors = [ref for ref in (row.get("donor"), row.get("base")) if ref]
        donors.extend(part["donor"] for part in row.get("parts", []))
        for donor in donors:
            if donor.get("kind") != "field_object":
                donor_id = f"{donor['game']}:{donor['tileset']}:{donor['id']}"
                assert indices[donor["game"]][donor_id]["pixel_sha256"] == donor["hash"], f"Donor hash changed: {donor_id}"
            native_donor(cache, donor, packed)
        if row.get("asset"):
            asset_image(row, mod_root)
            if row.get("kind") == "third_party":
                assert row.get("credit") and row.get("sourceUrl"), "Third-party attribution missing"
        if row.get("animated"):
            native_water_frames(cache, row, packed)
        if row.get("foreground"):
            ref = row["foreground"]
            raw = (cache / ref["game"] / f"data/generated/gba/field_effects/{ref['effect']}.rgba").read_bytes()
            if len(raw) != 16 * 80 * 4:
                raw = zlib.decompress(raw)
            assert catalog.sha(raw) == ref["hash"], "Foreground fingerprint changed"
        checked += 1
    return checked


def map_preview(cache, output, game, map_id, stem, rows, packed, scale, mod_root):
    root = cache / game
    maps = catalog.read_lua(root / "data/generated/maps.lua")
    sets = catalog.read_lua(root / "data/generated/tilesets.lua")
    map_def = maps[map_id]
    ts = sets[map_def["tileset"]]
    sheet = Image.open(root / ts["image"])
    palettes, roof = None, None
    native_animation = gen1_animation_tiles(cache, game, ts, sheet) if game in ("red", "blue", "yellow") else None
    if game not in ("red", "blue", "yellow"):
        palettes = palette_set(catalog.read_lua(root / "data/generated/palettes.lua"), map_def)
        if map_def["tileset"] in ("TILESET_JOHTO", "TILESET_JOHTO_MODERN"):
            roofs = catalog.read_lua(root / "data/generated/roofs.lua")
            name = catalog.dict_at(roofs["mapGroupRoofs"], map_def["group"])
            spec = roofs["roofs"].get(name)
            if spec:
                roof = Image.open(root / spec["image"])
    selected, positioned = {}, {}
    for row in sorted(rows, key=lambda r: bool(r.get("map"))):
        if row["game"] == game and row["style"] == "gen3" and row["tileset"] == map_def["tileset"] and row.get("map", map_id) == map_id:
            if "x" in row:
                positioned[(row["id"], row["quadrant"], row["x"], row["y"])] = row
            else:
                selected[(row["id"], row["quadrant"])] = row
    before = Image.new("RGBA", (map_def["width"] * 32, map_def["height"] * 32))
    after = before.copy()
    coverage, unique, by_role = 0, set(), Counter()
    source_cells, donor_cells = {}, {}
    for pos, block_id in enumerate(catalog.lua_array(map_def["blocks"])):
        block = catalog.lua_array(catalog.dict_at(ts["blocks"], block_id + 1))
        bx, by = pos % map_def["width"] * 32, pos // map_def["width"] * 32
        for q in range(4):
            key = block_id, q
            if key not in source_cells:
                source_cells[key] = native_cell(sheet, ts, block, q, palettes, roof, native_animation)
            original = source_cells[key]
            x, y = bx + q % 2 * 16, by + q // 2 * 16
            before.paste(original, (x, y))
            replacement = positioned.get((*key, x // 16, y // 16), selected.get(key))
            if replacement:
                # Verify raw grayscale pixels at the actual map block, separately
                # from its scene palette and group-specific roof overlay.
                raw_cell = native_cell(sheet, ts, block, q)
                assert catalog.sha(raw_cell.tobytes()) == replacement["sourceHash"]
                artwork_key = (*key, replacement.get("x"), replacement.get("y"))
                if artwork_key not in donor_cells:
                    donor_cells[artwork_key] = replacement_image(cache, replacement, packed, mod_root)
                after.paste(donor_cells[artwork_key], (x, y))
                coverage += 1
                unique.add(artwork_key)
                by_role[replacement["role"]] += 1
            else:
                after.paste(original, (x, y))
    total = len(catalog.lua_array(map_def["blocks"])) * 4
    display_w, display_h = before.width * scale, before.height * scale
    gap, left, top = 20, 18, 116
    canvas = Image.new("RGB", (left * 2 + display_w * 2 + gap, top + display_h + 56), "#18202c")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 19)
    small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 15)
    title = f"DEVELOPMENT — {game.title()} / {map_id.replace('_', ' ').title()}"
    draw.text((left, 12), title, fill="white", font=font)
    draw.text((left, 40), "Native imported background-map preview; nearest-neighbor pixels. This is not a complete tileset replacement.", fill="#ced7e4", font=small)
    if any(r.get("animated") for r in selected.values()):
        draw.text((left, 61), "Native donor animations shown at frame 0.", fill="#ced7e4", font=small)
    source_label = "Original monochrome" if palettes is None else "Original Crystal DAY colors and native roof"
    draw.text((left, 82), source_label, fill="white", font=small)
    draw.text((left + display_w + gap, 82), "Gen 3 style — reviewed cells only", fill="white", font=small)
    canvas.paste(before.resize((display_w, display_h), Image.Resampling.NEAREST), (left, top))
    canvas.paste(after.resize((display_w, display_h), Image.Resampling.NEAREST), (left + display_w + gap, top))
    draw.text((left, top + display_h + 14), f"Replaced {coverage}/{total} visible cells ({coverage/total:.1%}); {len(unique)} unique mappings. Remaining {total-coverage} cells keep native art. No actors rendered.", fill="#ced7e4", font=small)
    credits = sorted({r["credit"] for r in [*selected.values(), *positioned.values()]
                      if r.get("credit") and (r["id"], r["quadrant"], r.get("x"), r.get("y")) in unique})
    if credits:
        draw.text((left, top + display_h + 35), "Tree artwork: " + "; ".join(credits), fill="#ced7e4", font=small)
    path = output / f"{stem}-development.png"
    canvas.save(path)
    before.convert("RGB").save(output / f"{stem}-before-native.png")
    after.convert("RGB").save(output / f"{stem}-after-native.png")
    return {"game": game, "map": map_id, "tileset": map_def["tileset"], "visible_cells": total,
            "replaced_occurrences": coverage, "preserved_native_occurrences": total - coverage,
            "unique_mappings_used": len(unique), "replaced_by_role": dict(by_role),
            "source_palette": "original monochrome" if palettes is None else "native Crystal DAY environment plus group roof",
            "preserved_native_animation_tick": 0 if native_animation is not None else None,
            "credits": credits, "image": str(path.resolve())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path(catalog.os.environ["APPDATA"]) / "pokemon-love2d")
    parser.add_argument("--catalog", type=Path, default=WORKSPACE / ".work/tileshift-catalog")
    parser.add_argument("--reviewed", type=Path, default=WORKSPACE / "TileShift/mappings/reviewed.lua")
    parser.add_argument("--output", type=Path, default=WORKSPACE / ".work/tileshift-preview")
    parser.add_argument("--scale", type=int, default=2, choices=range(1, 5))
    parser.add_argument("--include-trees", action="store_true", help="Include the separate reviewed mappings/trees.lua asset mappings")
    parser.add_argument("--include-posts", action="store_true", help="Include the compact boundary trees from the legacy posts.lua mapping file")
    parser.add_argument("--include-water", action="store_true", help="Include reviewed coastal water, shown at native animation frame0 and respecting map scope")
    parser.add_argument("--include-buildings", action="store_true", help="Include reviewed compact native Pallet buildings")
    parser.add_argument("--include-details", action="store_true", help="Include reviewed Pallet grass, flowers and fences")
    parser.add_argument("--include-outdoors", action="store_true", help="Include reviewed additional Gen1/2 outdoor terrain")
    parser.add_argument("--tree-fixtures", action="store_true", help="Also render Route1 and Viridian tree map fixtures; requires --include-trees")
    args = parser.parse_args()
    rows = read_reviewed(args.reviewed)
    if args.tree_fixtures and not args.include_trees:
        parser.error("--tree-fixtures requires --include-trees")
    if args.include_trees:
        rows.extend(read_reviewed(args.reviewed.parent / "trees.lua"))
    if args.include_posts:
        rows.extend(read_reviewed(args.reviewed.parent / "posts.lua"))
    if args.include_water:
        rows.extend(read_reviewed(args.reviewed.parent / "water.lua"))
        coast = args.reviewed.parent / "coasts.lua"
        if coast.exists():
            rows.extend(read_reviewed(coast))
    for requested, name in ((args.include_buildings, "pallet_buildings.lua"), (args.include_buildings, "gen2_buildings.lua"),
                            (args.include_buildings, "buildings_extended.lua"),
                            (args.include_details, "pallet_details.lua"),
                            (args.include_outdoors, "gen1_outdoor.lua"), (args.include_outdoors, "gen2_outdoor.lua"),
                            (args.include_outdoors, "gen1_caves.lua"), (args.include_outdoors, "gen1_extended.lua"),
                            (args.include_outdoors, "gen2_outdoor_extended.lua"), (args.include_outdoors, "interiors.lua"),
                            (args.include_outdoors, "gen2_caves.lua")):
        if requested and (args.reviewed.parent / name).exists():
            rows.extend(read_reviewed(args.reviewed.parent / name))
    keys = {(r["game"], r["style"], r["tileset"], r["id"], r["quadrant"], r.get("map"), r.get("x"), r.get("y")) for r in rows}
    assert len(keys) == len(rows), "Reviewed mapping files contain duplicate source cells"
    game_ids = {r["game"] for r in rows} | {ref["game"] for r in rows for ref in (r.get("donor"), r.get("base")) if ref}
    game_ids.update(part["donor"]["game"] for row in rows for part in row.get("parts", []))
    catalogs = {game: json.loads((args.catalog / f"{game}.json").read_text()) for game in game_ids}
    mod_root = args.reviewed.parent.parent
    checked = verify(rows, args.cache, catalogs, mod_root)
    args.output.mkdir(parents=True, exist_ok=True)
    packed = {}
    fixtures = [("red", "PALLET_TOWN", "red-pallet"), ("crystal", "NEW_BARK_TOWN", "crystal-newbark")]
    if args.tree_fixtures:
        fixtures.extend((("red", "ROUTE_1", "red-route1-trees"), ("red", "VIRIDIAN_CITY", "red-viridian-trees")))
    results = [map_preview(args.cache, args.output, game, map_id, stem, rows, packed, args.scale, mod_root)
               for game, map_id, stem in fixtures]
    report = {"development": True, "fingerprint_checked_reviewed_rows": checked,
              "live_import_source_and_donor_rows_checked": checked,
              "third_party_asset_rows_file_and_pixel_hash_checked": sum(r.get("kind") == "third_party" for r in rows),
              "asset_rows_file_and_pixel_hash_checked": sum(bool(r.get("asset")) for r in rows),
              "animation_rows_all_native_frames_and_scope_checked": sum(bool(r.get("animated")) for r in rows),
              "maps": results,
              "limits": "Imported background maps only; no actors. Unreviewed source cells remain visible."}
    (args.output / "verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
