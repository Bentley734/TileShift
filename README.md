# TileShift

TileShift brings Gen 3 world art to Gen1Recomp with individually reviewed tile
matches. Version 0.25.0 completes the backgrounds of **every Red, Blue and Yellow
map: 667 map variants and 284,740 cells**. All Kanto towns, routes, Safari Zone,
caves, houses, Centers, shops, gates, laboratories, gyms, Pokemon Tower, museums,
Rocket/Silph facilities and the S.S. Anne are covered, including Yellow's beach
house. Johto remains complete across Gold, Silver and Crystal: 612 map variants
and 263,308 cells. Source layouts, collision, warps, puzzle rules and interactions
stay unchanged; characters and Pokemon sprites retain their original artwork.

Native Gen3 counterparts keep their original pixel size and complete frames,
window panels, doorways, furniture and statue silhouettes. Unique objects
without suitable counterparts retain every original pixel in matching Gen3
colors, including Kanto's fossil displays, laboratory instruments and League
monument details, plus Johto's Unown inscriptions, Magnet Train, studio
microphones and Dragon Shrine mural. Recoloring runs once when checked map
artwork is built and cached. Imported native pixels are read from your own game
imports and are not bundled in the mod.

Gen 2 Pokemon Centers retain selectable compact/expanded designs. Bell Tower uses the supplied original reference.
Its partial side tiles preserve the trees, ground and native map border underneath;
the original entrance and collision footprint stay unchanged.
Goldenrod uses the actual MetalFlygon08 Johto Gen3 Game Corner artwork,
with complete original pixels and a full96x64 building footprint. Goldenrod City's
outdoor map is completely retiled in Gold, Silver and Crystal, including its department
store, station, Radio Tower, florist, underground entrances, background houses,
railway, paving and coastline. Each version keeps its original flower-shop
position. Johto route replacements include full native gates,
cave entrances, animated inland banks and thin cliff edges.
Mt. Silver Outside is complete, including its cliff family,
animated freshwater shoreline and original cave entrance. Blackthorn City and
Lake of Rage are also complete.
Ecruteak City is complete with original Gen3 buildings based
on the supplied Johto reference, including its blue-roof homes, Dance Theater,
Bell Tower, temple entrance and version-specific Burned Tower exterior.
New building replacements keep their intended pixel scale and complete details.
Decorative artwork may overhang neighbouring cells, with genuinely transparent
unused portions; original entrances and collision footprints stay unchanged.
Gen 2 Pokemon Centers offer **COMPACT** and **EXPANDED** under
**POKEMON CENTERS** in the mod options. Compact restores the original native
64x64 design. Expanded keeps the native roof unchanged and adds a redesigned
front with blue-glass windows, trim and an entrance surround. The door remains
at the original map position. Style changes are cached and preserve collision.
Pallet's houses and lab also use the row above them, retaining their complete
windows and entrance frames. Gen 2 Marts gain additional native roofing.
Full roofs can extend one decorative tile above the unchanged building footprint,
covering parts of the original trees and any actors behind them. No new collision
is added; existing Headbutt trees retain their original interactions.
Olivine City is complete, including a new lighthouse, the cafe,
port passage, railings and coherent animated coastline. The original lighthouse
entrance and both base windows are preserved. Johto rock
and retaining-wall matches share source entries to keep runtime work small. Mixed designs follow connected
areas; grass can react to footsteps, and plant foregrounds surround character feet. Custom water choices are animated. It completely retiles the **Pallet Town, Viridian City, Route 1 and
Viridian Forest backgrounds in Red, Blue and Yellow**, all 19 maps using
their cave tileset, and **Pallet Town, New Bark Town, Cherrygrove City, Violet City, Azalea Town, Mahogany Town, Cianwood City, Olivine City, Ecruteak City, Blackthorn City, Goldenrod City, Lake of Rage and Mt. Silver Outside in Gold, Silver and Crystal**.
Red's downstairs room, Blue's house and many ordinary Kanto homes are also
fully retiled. Pallet includes compact houses and Oak's
lab, trees, fences, signs, grass, animated flowers, water and shoreline. Route 1
adds matching lawns, flowers, directional jump ledges and walkable steps.
Johto Routes 29 through 46 are completely retiled
in Gold, Silver and Crystal. Original gate entrances, cave destinations,
encounters and source movement rules are retained.

**Gen 2 areas outside Johto remain partially converted.** Viridian now includes its
freshwater pond, lawns, flowers, fences and ledges. New Bark has complete Gen 3
buildings, forest trees, grass, animated flowers and coastline. Reviewed ground,
trees, flowers, signs and grass now extend through many more Johto and Kanto maps.
Reviewed public buildings and homes now extend through more Johto and Kanto
towns. Gen 1 caves have reviewed floors, raised rock surfaces, directional walls,
stairs, ladders, animated water and switch-controlled Victory Road barriers.
Gen 2 caves add regional rock surfaces, complete rock masses, correctly joined
corners, ladders, and distinct snowy floors and slippery ice. Cherrygrove has complete shoreline corners, animated sea-rock barriers,
blocked outcrops and its separate walkable island surface. Violet includes
a Sprout Tower facade refined from the user's supplied pagoda design,
complete freshwater ponds, paving, raised ground and all building facades.
Gold and Silver retain their taller school footprint; Crystal retains its
shorter school and the original Headbutt-tree row above it.
Fighting Dojos, Bike Shops, the Fan Club and coastal houses retain their
complete entrances, windows and original footprints. Interior floors use the
matching house, lab, clinic, shop, ship, museum, Gym or facility art. Reviewed
household furniture keeps complete frames, shelves, paintings and plant crowns.
Unique regional features without suitable counterparts retain
their complete original shapes in matching Gen3 colors. Characters and Pokemon sprites are
unchanged. The single **Gen 3** style combines Emerald and FireRed/LeafGreen
art; separate cartridge styles and reverse conversions are future work.

## Install

1. Import **Emerald and FireRed** into Gen1Recomp. TileShift reads native donor
   art from your own imports; neither ROMs nor extracted native artwork are
   bundled.
2. Download `TileShift-v0.25.0.zip` from [the latest release](https://github.com/Bentley734/TileShift/releases/latest).
3. Extract the `tileshift` folder into Gen1Recomp's `mods` directory, enable
   **TileShift**, and restart the game.
4. Open Options and set **Tileset** to **Gen 3**. This is the default on a fresh
   installation; **Original** restores the host game's art.

Requires **Gen1Recomp 0.3.96 or newer**, within the 0.3.x series; also validated on 0.3.97. Reviewed replacements
currently target Red, Blue, Yellow, Gold, Silver and Crystal. The mod can load
under all eleven supported games; Gen 3 hosts keep their native art with the
Gen 3 style selected. Missing or changed donor cells are skipped, leaving the
host artwork visible.

## Artwork and matching

### Selectable trees, flowers, grass and water

Options and the mod manager expose **Trees**, **Big Trees**, **Cut Trees**,
**Flowers**, **Tall Grass** and **Water** independently. Each offers **Default**,
numbered designs, **Random** (one design for the session) and **Mixed** (one stable style per connected area). Edge- and corner-touching
tiles in the same category share one design; separate patches can vary. There are 87 small-tree/shrub choices, 89 Big
Trees, 89 Cut Trees, 57 flowers, 14 grass designs and three animated water choices.
Big Trees select one complete 32x32 design per tree, including in Mixed mode.
Custom flowers and grass animate with anchored roots; custom tree leaves sway
above fixed trunks. Grass foregrounds follow the same animation around actors.
Separate **Trees Speed**, **Flowers Speed**, **Grass Speed** and **Water Speed**
controls offer **Off**, **Slow**, **Normal** and **Fast**. Off keeps the selected
artwork still. Tree speed applies to small, Big and Cut Trees together.
**Grass Motion** offers **Always** and **On Walk** (when walked through). In the latter,
only disturbed grass cells animate and then settle. Grass and flower foregrounds
cover characters’ feet with their own matching plant pixels, retaining visible
gaps between leaves. Player, NPC, follower and overworld-wild draws share this
foreground pass. Original collisions and encounters remain unchanged.
Headbutt trees retain their distinct artwork. Cut behavior, encounters and other
source gameplay remain unchanged. Tall Grass changes encounter-grass art;
ordinary lawns remain distinct.

Water offers Magiscarf's animated **Ripple Blue / Teal / Olive**. The two static
clear-water choices were removed at the user's request; existing animated
preferences keep their stored IDs. Removed static preferences fall back to
Default. Mixed water chooses by connected body within
each reviewed map; reviewed coastal bodies share one ocean choice. Existing
bank silhouettes, grey rocks and white foam stay native while the water
surface changes. Over-water building parts are protected, including blue
windows. Water appearance never changes Surf, fishing, depth or encounters.
Only already-reviewed water mappings participate; unresolved tiles remain native.

The default artwork stays available, and **Original** restores the host
game's complete artwork regardless of custom selections. See the asset
credits and provenance for the user-supplied/generated and third-party designs.

Pallet's buildings use native FireRed pieces rearranged to fit the original
Gen 1 footprints. Door leaves and their complete lintels retain their native
pixels, and entrances stay at the original warp positions. Native building pieces
retain their pixel size. The supplied Sprout Tower design is separately fitted to its original
64×80 footprint, retaining the complete lower entrance between the unchanged
native side ledges. Default water, shoreline and flowers use verified native animation frames.
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
the round Gen 1 boundary objects. Optional foliage and the refined tower now
include the user-supplied/generated artwork described above.

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

| Completed background scope | Reviewed cells | Map variants |
| --- | --- | --- |
| Red, Blue and Yellow, every map | 284,740/284,740 | 667/667 |
| Gold, Silver and Crystal, Johto | 263,308/263,308 | 612/612 |

Gen2 Kanto remains in progress. All replacement matches are scoped to their
original source map and native donor family. The complete map audit loads the
actual mod and checks replacement availability, source fingerprints and
position scope; it does not render every map or constitute a full playthrough.

The longer-term goal includes Gen 1/2 themes and conversions between games.
Red/Blue artwork will use the original four-shade monochrome palette. Features
without a correct equivalent will need reviewed artwork in the selected style.

## Performance

Warm map lookups reuse indexed map tables without rebuilding row lists or
allocating cache keys. Ownership uses the engine's constant-time owner epoch;
import-marker polling runs once per second outside rendering. Cosmetic choices
retain the donor decoder cache. Connected-area grouping runs only when a map's
visual replacements are built. Actor bindings inspect list identity/count and
appended entries; unchanged frames do not run another full entity scan.

## Validation and development

The release is checked through the installed 0.3.97 loader for all eleven games,
Lua regression fixtures, live-import fingerprint checks, native donor animation
comparisons, and isolated native LOVE GPU rendering. Version 0.25.0 passes
36 Lua suite runs across three runtimes and 188,601,742 checks across 248 native
GPU scenes. This release verifies
all completed Gen1 and Johto map variants, native donor animation frames,
source fingerprints, collision/events, cleanup restoration, decorative
transparency and plant foreground behavior. The GPU suite exercises all Kanto
towns and representative routes, homes, shops, laboratories, gyms, tower,
ship and facility interiors in the actual native renderer. These are background
and mechanics fixtures, not full interactive playthroughs.

From the parent workspace:

```text
python TileShift/tests/run.py
python TileShift/tools/validate_boot.py --payload PATH_TO_0.3.97.love
python TileShift/tools/preview.py --include-trees --include-posts --include-water --include-details --include-buildings --include-outdoors --tree-fixtures
python TileShift/tools/validate_animation.py --game firered
python TileShift/tools/validate_animation.py --game leafgreen
python TileShift/tools/validate_gpu.py --timeout 900
python TileShift/tools/validate_coverage.py --games red,blue,yellow --require-complete --timeout 900
python TileShift/tools/validate_source_palettes.py
python TileShift/tools/gpu_comparison.py
python TileShift/tools/build_release.py
```

Review tools require the player's local imports and the workspace engine/test
runtime. Catalogs and native-art comparisons belong in the parent workspace's
`.work` folder and are excluded from the playable package and source repository.
The release builder requires a passing GPU report for the current runtime files.
The code is MIT licensed; third-party artwork retains its separate terms.
