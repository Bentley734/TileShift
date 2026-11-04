# Building artwork preference

The user reaffirmed on 2026-10-27 that the wider Bell Tower method applies to
all buildings going forward. Do not shrink building artwork to fit the old
collision footprint.

- Keep the artwork's intended gameplay pixel scale, proportions, complete
  roofs, window panels and doorway frames. Do not use fractional scaling or
  cut off unique features to squeeze a building into its original cells.
- Let decorative artwork extend above and into neighbouring side tiles when
  needed. Keep unused pixels genuinely transparent so the existing selected
  trees, grass, water, buildings or native map border remain visible.
- Preserve the original entrance position, source collision, map layout,
  scripts and interactions. Decorative extensions do not add collision.
- Redraw opaque extensions over overlapping player, wild, follower and NPC
  sprite pixels; transparent portions must leave those sprite pixels visible.
- Prefer intact native/reference artwork or complete modular sections. If a
  purpose-made replacement is needed, design it at its intended logical pixel
  size instead of downsizing an existing building. High-resolution references
  may be normalized with uniform integer nearest-neighbour reduction.
- A building that naturally continues beyond a map boundary may remain cut
  by that boundary. Verify extensions at the real native map border as well
  as inside the map image.
- Keep extension metadata bounded and source-fingerprinted. Cache assets and
  geometry; do not rebuild rows, load files or scan maps every frame.

On 2026-10-27 the user explicitly included Pokemon Centers and Poke Marts:
give these buildings the additional one-tile decorative top row as well,
so their artwork can be larger while their entrances and collisions stay put.
The user subsequently clarified that Pokemon Centers must put the additional
height into the front wall beneath their normal-sized roof, not stretch or
repeat the roof. Keep the complete native roof and emblem intact. The same
decorative-overhang treatment is also requested for Pallet's houses and lab.
The original compact Pokemon Center must remain selectable alongside the
redesigned expanded front. The mod option is POKEMON CENTERS: COMPACT/EXPANDED.

The user rejected the generated Goldenrod arcade prototypes. Its current
replacement uses intact MetalFlygon08 Johto artwork at1:1 pixel scale, with a
complete wall/window module repeated to reach the original building width.

# Classic Gym roofs and Mauville details

On 2026-11-03 the user requested plain rectangular roofs for Gen 3 Gyms
displayed in the Gen 1 or Gen 2 theme. Remove the projecting extra roof piece
above the entrance; preserve the complete native doorway, windows and GYM
lettering, and keep source entrances and collision unchanged. Gym signs must
use the selected generation's actual outdoor sign, not a computer or machine.
When flattening the projecting piece, move its lower roof edge/shadow up to
align with the neighboring edge. Keep that border continuous above the door;
plain roof fill must not leave a gap in the shadow.
Wide Gym facades must repeat interior wall/window modules. Use the right edge
tile only at the building's outer right edge; do not repeat its vertical frame
strips beside the doorway.

The user also requested connected Crystal-style fences in Mauville, preferring
suitable native fence tiles; generate matching pieces only when native art
cannot provide the needed joins. Replace the rejected compact frontal bicycle
glyphs with the bicycles from Cerulean City's Bike Shop, retaining complete
native bicycle silhouettes and pixel scale.

Crystal-style boulders and cliffs/mountains must retain their native rock
silhouettes with transparent exterior corners. Remove the donor's brown
background outside the rock, so the surrounding selected water or ground shows
through. Preserve actual rock shading and enclosed detail; do not erase a
matching color throughout the object.

Expanded native Poké Mart roofs must extend plain lower roofing panels. Do not
repeat the roof's horizontal top border inside the added height: the user
rejected the two resulting dark seams on Blackthorn's Mart and all shared uses.

The user requested Crystal-style dirt and a distinct tree for every Gen 3 berry
variety. Keep the original rounded dirt silhouettes over the exact selected
field, with no native cyan grass rectangle. Use the 43 individually generated
plant sheets, not one reused vanilla Crystal tree or recolors of one plant.
Preserve all nine native frame rectangles, native anchors and the engine's
planting, watering, growth, harvesting, sorting and effect logic. Source checks,
asset loads and quad construction belong outside warm draw work.
Expose a separate persisted BERRY TREES: NATIVE/CRYSTAL option in R/S/E,
defaulting to Crystal. Native must immediately restore pooled native images
and quads while the selected background remains unchanged. Only the Gen 2
background theme enables Crystal plants; other background themes keep native
actors. Review complete dirt plots, including secondary regional tile IDs:
both halves must use the same generated material and matching exterior grass.
