# Artwork credits

## Crystal berry plants and dirt

The 43 berry plant sheets and the berry-soil material in
`assets/original/berries/gen2/` were generated independently with the built-in
OpenAI image-generation tool at the user's request on 2026-11-03. Each variety
uses its original Gen 3 berry identity and native growth poses as reference,
with Crystal-style pixels and a small declared palette. Native reference art
and high-resolution working outputs are not bundled.

All 387 frames retain the native16x240 sheet layout and original anchors.
Technical processing uses recorded integer nearest-neighbor normalization,
transparent padding, palette conformance and binary alpha. The generated soil
material is clipped only to the original rounded dirt shapes. The consolidated
`provenance.json` records exact prompts, raw/output hashes, crop and palette
rules, source bounds and frame checks. Native planting and growth code is
unchanged; only the selected theme's ground and berry actor pixels change.

The Gen3 theme on Gen2 hosts (v0.29.0 onward) uses the user-supplied Johto ROM hacks credited below. This file also preserves historical provenance for retained files and Gen1 options; the generated Gen2 replacements described in those historical sections are superseded, except the roofed Slowpoke Well kept at the user's request. Radios and the beacon preserve original Gen2 geometry in matching Gen3 colors where the hacks have no corresponding background object.

## Selectable foliage and Sprout Tower

The two JPEGs in `assets/user_flora` were supplied by the user as Gemini-generated
artwork, with explicit permission to include the designs as selectable trees,
flowers and grasses. Their original bytes are preserved; the runtime samples
16×16 cells and removes their mint backgrounds. Designs use simple numbered selection labels; stable internal IDs preserve saved choices.

Sprout Tower uses the user's Gemini design and assembled reference, refined
with the built-in image-generation tool. Complete upper and lower components
are reduced with nearest-neighbor sampling to fit the original footprint.
The native entrance and side ledges remain unchanged. Its provenance includes
the prompt, dimensions and fingerprints. No generated scenery is used.

## Selectable water

**Next Animated Water Tiles** by **Magiscarf** supplies blue, teal and olive
ripples. The artist specifies noncommercial use; the page's image metadata
licenses the artwork under [CC BY-NC-SA 3.0](https://creativecommons.org/licenses/by-nc-sa/3.0/).
Eight original GIF frames are decoded losslessly into PNGs. Existing native
water/shore schedules remain in use where present; otherwise frames use the
original 100ms period. No animation frames are invented.
[Original source](https://www.deviantart.com/magiscarf/art/Next-Animated-Water-Tiles-830567034).

The static PeekyChew water options and their bundled source sheet were removed
in v0.8.0 at the user's request. Earlier v0.7.0 assets retain the credits in
that release's provenance and CREDITS file.

These artworks retain their respective terms and are excluded from the MIT
license for TileShift's code. Full credits, permission evidence, processing
details and hashes accompany each asset folder. The mod is free and noncommercial.

## Default compact tree

The compact round tree in `assets/third_party/j-treecko252/compact-tree.png`
comes from **Tree Tiles Ver.02** by **J-Treecko252**. The artist also credits
**Zyxeion** for additional color palettes.

Source: [Tree Tiles Ver.02 on DeviantArt](https://www.deviantart.com/j-treecko252/art/Tree-Tiles-Ver-02-884751013).

The artwork description permits use and edits with credit: “Free to Edit/Use,
just give credit.” Permission was checked on October 26, 2026. The tree is
included in this free, noncommercial mod under that author permission.

Only one approved complete tree was extracted. Its original 32×32 crop uses
exactly duplicated 2×2 pixels; removing that duplication produces the native
16×16 graphic without changing its colors or pixel shapes. Original alpha
transparency is retained. The full artist sheet is not distributed.
The adjacent `provenance.json` records the source, crop coordinates and hashes.

Any Emerald ground beneath the tree is read from the player's own imported
game and is not included with this artwork.

The same compact tree also replaces the round Gen 1 town-boundary objects,
following the user's choice to use FireRed/LeafGreen's tree interpretation.

## Original foliage

The native 16x16 grasses and ground flowers, and complete 32x32 oak and pine,
are original project designs generated with the built-in image-generation tool.
Their complete visible silhouettes were cropped before integer nearest-neighbor
reduction and palette cleanup. No fractional runtime scaling is used. The blue
flowers were revised to upright ground flowers. Full processing records and
final hashes are in assets/original/flora/provenance.json. Custom flora uses
four integer-pixel wind frames, with roots and tree trunks anchored.

## Original Slowpoke Well

The new 48×48 well was generated with the built-in image-generation tool and
finalized by integer nearest-neighbor reduction. It was designed for the original
Gen 2 3×3 footprint, with its entrance and steps unchanged.
MetalFlygon08’s [Gen 3 Johto artwork](https://www.reddit.com/r/PokemonRMXP/comments/yf90qb/full_johto_gen_3_tileset_tile_set_at_the_bottom/)
provided the style reference; its well bitmap is not distributed. The prompt,
processing details and asset hashes are in assets/original/slowpoke-well/provenance.json.

## Original Olivine lighthouse

The new 64×224 lighthouse was made with the built-in image-generation tool.
MetalFlygon08’s [Gen 3 Johto sheet](https://www.reddit.com/r/PokemonRMXP/comments/yf90qb/full_johto_gen_3_tileset_tile_set_at_the_bottom/)
provided a style reference only. The complete new design retains both base
windows and the original entry anchor, with uniform 7:1 nearest-neighbor
reduction and no runtime scaling. The reference crop is not distributed.
The prompt, processing record and hashes are in
assets/original/olivine-lighthouse/provenance.json.

## Original compact conifer

The default one-cell tree is an original compact redesign of the complete
taller Emerald tree, made with the built-in image-generation tool. Its pointed
canopy and trunk fit a16×16 cell. The full sprite uses uniform78:1 integer
nearest-neighbor reduction, binary transparency and a12-color palette.
The prompt, processing record and hashes are saved in
assets/original/compact-conifer/provenance.json.
The previous J-Treecko252 tree remains credited and packaged as historical
artwork; the default now uses this original compact conifer.

## Original Ecruteak buildings

The new blue-roof homes, Dance Theater, temple entrance, Bell Tower and
version-specific Burned Tower exteriors were made with built-in image generation.
MetalFlygon08’s Johto artwork supplied style and subject references only.
Reference bitmaps are not distributed. The new designs retain the original
map footprints and entrance positions. Finalization uses uniform integer
nearest-neighbor reduction and binary transparency. Full roofs may extend one decorative row above the original building.
Existing trees remain underneath; source collisions and interactions stay unchanged.
Only plain exterior columns are repeated to match the original building width.
Prompts, source hashes, processing steps and final asset hashes are in
assets/original/ecruteak-v2/provenance.json.

## MetalFlygon08 Johto Game Corner

The Goldenrod Game Corner uses MetalFlygon08’s actual Johto Gen3 artwork
from https://imgur.com/gallery/testing-out-gen-3-style-tiles-johto-6A43Cji .
The author states that the tileset is free to use and prefers MetalFlygon08
for credit: https://www.reddit.com/r/PokemonRMXP/comments/yf90qb/full_johto_gen_3_tileset_tile_set_at_the_bottom/ .
All original80x64 pixels are retained at1:1 scale. One complete16px
roof/window/wall section repeats to match the original96x64 map footprint;
the entrance stays at40,64. No generated arcade artwork is included.
Crop coordinates, source columns, permission links and hashes are recorded
in assets/third_party/metalflygon08/provenance.json.

## Wider Bell Tower reference

Bell Tower now uses the same original generated artwork that the user supplied
again as the desired reference, with uniform9:1 integer nearest-neighbour
reduction and binary transparency. Its visible width grows to78 pixels,
with a96px canvas containing transparent portions in the two adjacent tiles.
The original64px collision footprint and doorway remain unchanged. The tower
continues north beyond the original map edge. The reference hash, crop,
palette processing and asset hashes are recorded in
assets/original/bell-wide/provenance.json.

## Goldenrod modular buildings and redesigned clinic front

Additional Goldenrod architecture uses MetalFlygon08's public Johto tileset
under the same author permission cited above. Complete windows, entrances,
parapets, clock/lattice mast and dish components remain at native pixel scale;
plain roof/wall modules repeat where needed. Asset hashes and source rectangles
are recorded in assets/third_party/metalflygon08/provenance.json.

The expanded Pokemon Center facade is original artwork made with the built-in
image-generation tool at the user's request. It is normalized using uniform
18:1 nearest-neighbour reduction, binary alpha and a limited palette without
dithering. The native Emerald roof is assembled separately from fingerprinted
donor references and is not regenerated. The original compact native building
remains selectable. Processing and hashes are recorded in
assets/original/center-expanded/provenance.json.

## Ilex Forest, National Park and Route 32

The shrine, park bench and transparent animated whirlpool foam are original
artwork made with the built-in image-generation tool, normalized with uniform
integer nearest-neighbour reduction and binary alpha. Their complete visible
silhouettes, processing details and hashes are recorded in the corresponding
assets/original provenance files. Whirlpool phases use exact quarter turns.

National Park uses MetalFlygon08's complete native40x45 fountain at1:1 scale,
under the same author permission cited above. No part of its base is cropped.
The fountain and basin keep all original source movement permissions.

Route32 uses native16x16 wooden pier boards from Peekychew's public standard
route sheet, supplied and explicitly authorized by the user. Artist:
https://www.deviantart.com/peekychew . Source hash, unscaled crop, edge recipe
and output hashes are recorded in assets/third_party/peekychew/provenance.json.
Most native Gen3 graphics remain fingerprinted references to the player's own
imports. The selected exact native interior cutouts described below are packaged
with their source coordinates and file hashes.

## Johto interiors

Native Gen3 room, cave, casino, shop, laboratory, school, gym, tower and port
artwork remains fingerprinted references to the player's own imports. Complete
objects retain their native pixels; only repeating plain sections are rearranged.
Historical generated interior artwork remains credited in the original provenance
files. Those designs are inactive in the Gen 2 theme; the generated roofed
Slowpoke Well is retained at the user's request. Current potted flowers and
ascending ladders keep complete native pixels at1:1. Compact original GSC
stairs, service equipment, paintings and ornaments use the authorized original
geometry recolor when a complete native counterpart does not fit.
Unique Unown inscriptions and unmatched transport/studio details use the
user-requested native-pixel palette recoloring. Their original imported source
pixels are normally read from the player's cache through color values and
fingerprinted references. The current-version notes below identify the small
credited derivatives that are packaged with native background corrections.

## Kanto completion

Red, Blue and Yellow backgrounds use checked native Emerald/FireRed references
for towns, routes, Safari Zone, homes, clinics, shops, gates, laboratories,
facilities, gyms, museums and the S.S. Anne. Complete objects retain their
native pixel size and frames. Only repeating roof, wall, cabinet and floor
sections are rearranged to preserve the original map footprint and entrances.
Unique fossil displays, ship fittings, compact laboratory instruments, League
monument details and unmatched symbols retain the original imported geometry
in user-approved Gen3 colors. Most matches package only palettes and source fingerprints and read imported
pixels from the player's cache. The current-version notes identify the selected
credited derivative PNGs included for irregular transparent backgrounds.

## Classic themes on Gen3

Gen1 and Gen2 background counterparts are checked references to the player's
Red and Crystal imports; no extracted GB artwork is bundled. Native windows,
doors, tree silhouettes and complete furniture retain their original pixels.
Only repeating roof/wall sections are arranged to retain Gen3 building footprints.
The expanded Crystal theme in v0.32.0 and v0.33.0 also assembles complete native foliage,
furniture, shoreline and cave modules from the player's import. Original Game
Freak/Nintendo artwork is not bundled by these recipes. The original Crystal
animation programs supply water, flowers, lava and related native frames;
unidirectional current animation is a TileShift adaptation of the native wave
glyph. Underwater terrain and shadowed paving use explicit four-shade palettes.
Small missing furniture motifs, directional panels and clinic emblems are
code-authored Gen2-style counterparts, using native modules and colors at their
logical pixel size. These are not claimed as original stock Crystal objects.
The two classic laboratory vents are original built-in imagegen artwork. Their
full prompts, source hashes, uniform integer 26 normalization, binary alpha and
four-color palettes are recorded in assets/original/classic-vent/provenance.json.

Azalea Gym's pink patterned floor and oak ground shadow are original code-authored assets. The existing original oak pixels are preserved unchanged above the shadow; native FR/LG lawn artwork is read from the player's import. File fingerprints are recorded in assets/original/azalea-lawn/provenance.json.

## User-supplied Johto ROM hacks

Selected artwork was extracted at the user's request from their supplied FireGold 1.4 (Tzx211), CrystalDust (Sierraffinity and contributors), and Liquid Crystal (Linkandzelda, Synyster Zeikku and contributors) ROMs. These project credits do not imply an open license. Only selected checked graphics are packaged; the ROM binaries are never included. Per-object source ROM hashes, native crop bounds, alpha masks, compact tree module placements and any exact integer reductions are recorded under assets/third_party/johto-hacks/*/provenance.json.

New Bark's selected kitchen units, cafe counter divider, TV cabinets, radio stands, Elm Lab healing machine and workstations use complete native CrystalDust artwork by Sierraffinity and contributors. The selected pieces retain their original pixel size. Individual source rectangles, background masks and asset hashes are recorded with these furniture assets.

The player bedroom decoration counterparts use complete CrystalDust and LiquidCrystal bed and plant artwork, native CrystalDust rug modules, and individually identified native Gen 3 cloth and Pokemon portrait sources. Pink, polkadot and Pikachu beds, colored rugs and named portrait posters are documented compositions of those sources, rather than items claimed to exist unchanged in the hacks. Complete frames and figures retain their original pixel size. The compact staircase retains its credited original GSC geometry over the selected Gen 3 surroundings. Exact source rectangles, exterior masks, native hashes and all installed artwork hashes are recorded in assets/third_party/johto-hacks/bedroom-complete/provenance.json.

The selected T1 small round tree also comes from the supplied CrystalDust ROM. Its complete native 16×16 foreground replaces the existing small Headbutt-tree artwork over each location's selected ground. Exact source pixels and hashes are recorded with the tree asset.

The narrow town pine retains all three original FireGold cells (600 canopy, 601 middle and 608 roots) at native 16x48 size. The middle and root cells occupy the original source footprint while the complete canopy forms a one-cell decorative overhang. No pixel scaling, foliage-tier removal or native-map changes are used. Only outside-connected native field pixels are omitted so the selected ground remains visible. The exact native map coordinates, removed field-pixel mask, source hashes and PNG hashes are recorded in assets/third_party/johto-hacks/town-trees/provenance.json.

Project references: https://www.pokecommunity.com/threads/pok%C3%A9mon-fire-gold-1-4.473130/ , https://github.com/Sierraffinity/CrystalDust , https://www.pokecommunity.com/threads/pok%C3%A9mon-liquid-crystal-3-3-xxxxx-live-beta.242023/ .


## Gen 2 Kanto and shared interiors (0.30.0)

Native FR/LG/Pokemon Emerald floors, complete furniture, sculptures, casino
machines, transport equipment and architecture are matched to the original
GSC footprints and room purposes. Only plain repeatable sections are rearranged.
Original GSC compact or unique geometry is explicitly credited as a palette
recolor, including League ornaments, link hardware and small staircase frames.
Original collision, events, warps, source layouts and interaction points remain
unchanged.

Exact native sculpture cutouts are recorded in
assets/third_party/native-kanto-interiors/provenance.json. Exact native clock and
original-GSC office-cabinet derivatives are recorded in
assets/third_party/gamefreak/gsc-apartments/provenance.json. The original-GSC
recolored service/cabinet/table ornament derivatives with checked native floor
pieces are recorded in assets/third_party/gsc-room-geometry/provenance.json.
These derivatives preserve original pixel size and record every omitted exterior
floor pixel or replaced floor-only8px piece. Pokemon artwork: Game Freak.
No ROM binaries are bundled.

The full native Kanto landmark recipes and selected checked pixels (Saffron's
station, Lavender's tower, the Cerulean police house and League entrance) are
recorded in assets/third_party/kanto-landmarks/provenance.json. Sources are the
player's FireRed import, the user-supplied FireGold and the previously authorized
MetalFlygon08 Johto artwork. Complete native features keep their original size;
only plain repeat sections are rearranged. Transparent unused pixels preserve
the selected background.


Gen 2 directional chairs use complete native FireRed house/casino/restaurant
views. The north-facing chair retains the complete native Emerald S.S. Tidal
geometry at 1:1, with a literal substitution of the native casino blue palette.
Only unrelated desk-board pixels are removed. Source, mask, palette and pixel
hashes are recorded in assets/third_party/native-kanto-chairs/provenance.json.
Saffron pavement and unchanged native foreground derivatives are recorded in
assets/third_party/saffron-paving/provenance.json; original collision and native
building/window pixels remain unchanged.

Gen 2 interior floor corrections retain complete native furniture foregrounds
and place them over each source room's selected floor. Exact derivative pixels
and source recipes are recorded in assets/third_party/gen2-domestic-floor-audit/
provenance.json. Native interior cushions and lounge/waiting-seat artwork are
credited in assets/third_party/native-interior-seats/provenance.json.

The Gen 1 completion audit uses native FireRed/Emerald room objects and the
user-authorized FireGold clinic, plus the approved full-size League fit.
Native foregrounds, exact source geometry for unmatched compact details,
source-room masks and file hashes are recorded in assets/third_party/
gen1-outdoor-audit/, gen1-seating-domestic/ and gamefreak/rby-facility-floor/
provenance.json. No original layout, entrance or NPC coordinates are moved.

The Hoenn submarine replacement uses one original vessel created with the built-in image generator. Its whole 64×48 canvas was normalized with uniform integer nearest-neighbor reduction and split at native 16-pixel boundaries. Generation and piece fingerprints are in `assets/original/classic-submarine/provenance.json`. Other named regional four-color derivatives are drawn at runtime from the player’s own imported native geometry.
