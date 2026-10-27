# TileShift

TileShift brings Gen 3 world art to Gen1Recomp with individually reviewed tile
matches. Version 0.6.0 completely retiles the **Pallet Town, Route 1 and
Viridian Forest backgrounds in Red, Blue and Yellow**, all 19 maps using
their cave tileset, and **New Bark Town and Violet City in Gold, Silver and Crystal**.
Red's downstairs room, Blue's house and many ordinary Kanto homes are also
fully retiled. Pallet includes compact houses and Oak's
lab, trees, fences, signs, grass, animated flowers, water and shoreline. Route 1
adds matching lawns, flowers, directional jump ledges and walkable steps.

**Other Gen 1/2 maps remain partially converted.** Viridian now includes its
freshwater pond, lawns, flowers, fences and ledges. New Bark has complete Gen 3
buildings, forest trees, grass, animated flowers and coastline. Reviewed ground,
trees, flowers, signs and grass now extend through many more Johto and Kanto maps.
Reviewed public buildings and homes now extend through more Johto and Kanto
towns. Gen 1 caves have reviewed floors, raised rock surfaces, directional walls,
stairs, ladders, animated water and switch-controlled Victory Road barriers.
Gen 2 caves add regional rock surfaces, complete rock masses, correctly joined
corners, ladders, and distinct snowy floors and slippery ice. Violet includes
an original Sprout Tower composition built from native Gen 3 materials,
complete freshwater ponds, paving, raised ground and all building facades.
Gold and Silver retain their taller school footprint; Crystal retains its
shorter school and the original Headbutt-tree row above it.
Fighting Dojos, Bike Shops, the Fan Club and coastal houses retain their
complete entrances, windows and original footprints. Interior floors use the
matching house, lab, clinic, shop, ship, museum, Gym or facility art. Reviewed
household furniture keeps complete frames, shelves, paintings and plant crowns.
Other furniture and many regional features still use
their original art. Characters and Pokemon sprites are
unchanged. The single **Gen 3** style combines Emerald and FireRed/LeafGreen
art; separate cartridge styles and reverse conversions are future work.

## Install

1. Import **Emerald and FireRed** into Gen1Recomp. TileShift reads native donor
   art from your own imports; neither ROMs nor extracted native artwork are
   bundled.
2. Download `TileShift-v0.6.0.zip` from [the latest release](https://github.com/Bentley734/TileShift/releases/latest).
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
Roof corners show the surrounding grass or native animated coastal water,
using native transparent roof layers. Both complete lab windows and awnings, including their
top corners, are checked independently alongside the complete door frames.
New Bark uses Birch's native laboratory, a Littleroot player home and complete
one-story Kanto homes. Windows, entrances and the laboratory dish retain their
full native pixels. Position-specific graphics distinguish buildings that share
the same source tiles; the original map data is never rewritten.
Actual Gen 2 Cut trees use the native FireRed sapling artwork at its complete
16px size; source Cut behavior and removal remain native. New Bark's small
Headbutt trees use the complete native Emerald small-tree artwork, keeping
their original Headbutt eligibility, encounters, blocking and shake animation.

Gen 1 town boundaries and compact forest trees use a 16px tree by **J-Treecko252**,
with additional palette credit to **Zyxeion**, under the artist's permission.
See [CREDITS.md](CREDITS.md). This follows the remake's tree interpretation of
the round Gen 1 boundary objects. No generated artwork is included in this release.

Every mapping records a source fingerprint, semantic role, reviewed donor
reference or credited asset, and review evidence. Source metadata, map files
and images are fingerprinted as well as rendered source pixels; native donor
layers and animation banks have separate checks. Unexpected source or donor
data cause that mapping to be skipped. Unreviewed cells retain native art.
Map layouts, collision, encounters, warps, scripts and save progression remain
unchanged. Tall grass keeps a foreground layer over the player's feet.
Unlit Flash caves retain the source game's exact darkness and entrance flicker;
the selected artwork appears after Flash restores visibility. Bright donor
graphics cannot bypass native darkness.

| Background fixture | Reviewed cells |
| --- | --- |
| Pallet Town, Red/Blue/Yellow | 360/360 |
| Route 1, Red/Blue/Yellow | 720/720 |
| Viridian City, Red/Blue/Yellow | 1,306/1,440 |
| Viridian Forest, Red/Blue/Yellow | 1,632/1,632 |
| Red's House 1F and Blue's House, Red/Blue/Yellow | 64/64 each |
| New Bark Town, Gold/Silver/Crystal | 360/360 |
| Cherrygrove City, Crystal | 636/720 |
| Violet City, Gold/Silver/Crystal | 1,440/1,440 |
| Mt. Moon 1F, Red | 1,440/1,440 |
| Seafoam Islands 1F, Red | 540/540 |

Many Gen 2 cave entrances, water edges and regional features remain native.
Other cave floors can have different coverage; individual matches are scoped
to the source map and the corresponding donor cave family.

The complete map audit loads the actual mod and checks available replacements
for all 1,791 imported Gen 1/2 maps. Version 0.6.0 covers 378,480 of 718,992
initial background cells (52.6%), including 133 complete maps, with zero
rejected mappings or warnings.
This audit checks actual replacement availability and position scope; it does
not render every map or constitute a full playthrough.

The longer-term goal includes Gen 1/2 themes and conversions between games.
Red/Blue artwork will use the original four-shade monochrome palette. Features
without a correct equivalent will need reviewed artwork in the selected style.

## Validation and development

The release is checked through the installed 0.3.96 loader for all eleven games,
Lua regression fixtures, live-import fingerprint checks, native donor animation
comparisons, and isolated native LOVE GPU rendering. This release passes
9,734,648 checks across 34 background fixtures, including every native water
frame behind the Fan Club and Route 12 roof corners. Pallet's Red/Blue/Yellow
background fixtures and Gold/Silver/Crystal New Bark must replace all 360 visible 16px cells, and Route 1 all
720 cells. Checks preserve native map and collision data, and restore original rendering when disabled. These
checks are background-render fixtures, not full interactive playthroughs.

From the parent workspace:

```text
python TileShift/tests/run.py
python TileShift/tools/validate_boot.py --payload PATH_TO_0.3.96.love
python TileShift/tools/preview.py --include-trees --include-posts --include-water --include-details --include-buildings --include-outdoors --tree-fixtures
python TileShift/tools/validate_animation.py --game firered
python TileShift/tools/validate_animation.py --game leafgreen
python TileShift/tools/validate_gpu.py
python TileShift/tools/gpu_comparison.py
python TileShift/tools/build_release.py
```

Review tools require the player's local imports and the workspace engine/test
runtime. Catalogs and native-art comparisons belong in the parent workspace's
`.work` folder and are excluded from the playable package and source repository.
The release builder requires a passing GPU report for the current runtime files.
The code is MIT licensed; third-party artwork retains its separate terms.
