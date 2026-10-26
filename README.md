# TileShift

TileShift brings Gen 3 world art to Gen1Recomp with individually reviewed tile
matches. Version 0.1.0 completely retiles the **Pallet Town background in Red,
Blue and Yellow**, including compact houses and Oak's lab, trees, fences,
signs, grass, animated flowers, water and shoreline.

**Other Gen 1/2 maps remain partially converted.** Interiors and many regional
features still use their original art. Characters and Pokemon sprites are
unchanged. The single **Gen 3** style combines Emerald and FireRed/LeafGreen
art; separate cartridge styles and reverse conversions are future work.

## Install

1. Import **Emerald and FireRed** into Gen1Recomp. TileShift reads native donor
   art from your own imports; neither ROMs nor extracted native artwork are
   bundled.
2. Download `TileShift-v0.1.0.zip` from [the latest release](https://github.com/Bentley734/TileShift/releases/latest).
3. Extract the `tileshift` folder into Gen1Recomp's `mods` directory, enable
   **TileShift**, and restart the game.
4. Open Options and set **Tileset** to **Gen 3**. This is the default on a fresh
   installation; **Original** restores the host game's art.

Requires **Gen1Recomp 0.3.96**, within the 0.3.x series. Reviewed replacements
currently target Red, Blue, Yellow, Gold, Silver and Crystal. The mod can load
under all eleven supported games; Gen 3 hosts keep their native art with the
Gen 3 style selected. Missing or changed donor cells are skipped, leaving the
host artwork visible.

## Artwork and matching

Pallet's buildings use native FireRed pieces rearranged to fit the original
Gen 1 footprints. Door leaves and their complete lintels retain their native
pixels, and entrances stay at the original warp positions. No building art is
scaled. Water, shoreline and flowers use verified native animation frames.

Town boundaries and forest trees use a compact 16px tree by **J-Treecko252**,
with additional palette credit to **Zyxeion**, under the artist's permission.
See [CREDITS.md](CREDITS.md). This follows the remake's tree interpretation of
the round Gen 1 boundary objects. The earlier generated stone-post draft is
retired; no generated artwork is active in this release.

Every mapping records a source fingerprint, semantic role, reviewed donor
reference or credited asset, and review evidence. Unexpected source or donor
pixels cause that mapping to be skipped. Unreviewed cells retain native art.
Map layouts, collision, encounters, warps, scripts and save progression remain
unchanged. Tall grass keeps a foreground layer over the player's feet.

The longer-term goal includes Gen 1/2 themes and conversions between games.
Red/Blue artwork will use the original four-shade monochrome palette. Features
without a correct equivalent will need reviewed artwork in the selected style.

## Validation and development

The release is checked through the installed 0.3.96 loader for all eleven games,
Lua regression fixtures, live-import fingerprint checks, native donor animation
comparisons, and isolated native LOVE GPU rendering. Pallet's Red/Blue/Yellow
background fixtures must replace all 360 visible 16px cells, preserve native
map and collision data, and restore original rendering when disabled. These
checks are background-render fixtures, not full interactive playthroughs.

From the parent workspace:

```text
python TileShift/tests/run.py
python TileShift/tools/validate_boot.py --payload PATH_TO_0.3.96.love
python TileShift/tools/preview.py --include-trees --include-posts --include-water --include-details --include-buildings --tree-fixtures
python TileShift/tools/validate_animation.py --game firered
python TileShift/tools/validate_animation.py --game leafgreen
python TileShift/tools/validate_gpu.py
python TileShift/tools/gpu_comparison.py
```

Review tools require the player's local imports and the workspace engine/test
runtime. Catalogs and native-art comparisons belong in the parent workspace's
`.work` folder and are excluded from the playable package and source repository.
The code is MIT licensed; third-party artwork retains its separate terms.
