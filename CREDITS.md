# Artwork credits

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
Other native Gen3 graphics remain fingerprinted references to the player's
own imports, rather than redistributed ROM artwork.

## Johto interiors

Native Gen3 room, cave, casino, shop, laboratory, school, gym, tower and port
artwork remains fingerprinted references to the player's own imports. Complete
objects retain their native pixels; only repeating plain sections are rearranged.
Original compact radios, computers, flowerpots, stairs, beacon, planter, pillar,
rail post, lattice and Bellsprout painting were made with the built-in image
generation tool and normalized with uniform integer nearest-neighbour reduction
and binary alpha. Their prompts, source hashes, processing and file hashes are
recorded in assets/original/interior-*/provenance.json. Tower roof-course
modules derive from the previously approved original Sprout Tower artwork.
Unique Unown inscriptions and unmatched transport/studio details use the
user-requested native-pixel palette recoloring. Their original imported source
pixels remain in the player's cache; only color values and fingerprinted mapping
references are packaged.
