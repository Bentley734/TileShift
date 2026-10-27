# Artwork credits

## Selectable foliage and Sprout Tower

The two JPEGs in `assets/user_flora` were supplied by the user as Gemini-generated
artwork, with explicit permission to include the designs as selectable trees,
flowers and grasses. Their original bytes are preserved; the runtime samples
16×16 cells and removes their mint backgrounds. Stable selection labels use
sheet initials, row and column because the printed IDs repeat.

Sprout Tower uses the user's Gemini design and assembled reference, refined
with the built-in image-generation tool. Complete upper and lower components
are reduced with nearest-neighbor sampling to fit the original footprint.
The native entrance and side ledges remain unchanged. Its provenance includes
the prompt, dimensions and fingerprints. No generated scenery is used.

## Selectable water

**Beach and Sea Tiles** by **PeekyChew**, also crediting **EVoLiNa** and
**The-Red-eX**, supplies the clear shallow/deep water surfaces. The artist
released the tiles for others to use; the user's resource index specifies
noncommercial use and attribution.
[Original source](https://www.deviantart.com/peekychew/art/Beach-and-Sea-Tiles-642129192).

**Next Animated Water Tiles** by **Magiscarf** supplies blue, teal and olive
ripples. The artist specifies noncommercial use; the page's image metadata
licenses the artwork under [CC BY-NC-SA 3.0](https://creativecommons.org/licenses/by-nc-sa/3.0/).
Eight original GIF frames are decoded losslessly into PNGs. Existing native
water/shore schedules remain in use where present; otherwise frames use the
original 100ms period. No animation frames are invented.
[Original source](https://www.deviantart.com/magiscarf/art/Next-Animated-Water-Tiles-830567034).

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
