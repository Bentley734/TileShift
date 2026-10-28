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

The user rejected the generated Goldenrod arcade prototypes. Its current
replacement uses intact MetalFlygon08 Johto artwork at1:1 pixel scale, with a
complete wall/window module repeated to reach the original building width.
