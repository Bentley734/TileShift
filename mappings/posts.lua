-- Default one-cell tree revised: complete compact Emerald-style conifer; see assets/original/compact-conifer/provenance.json. Historical source-review evidence below remains recorded.
-- Gen 1's round town-boundary objects use compact Gen 3 trees.
-- The user approved following FR/LG's actual tree boundary on 2026-10-26.
-- This supersedes the earlier stone-post interpretation and generated artwork.
-- Source seed OVERWORLD 77:1 uses 8px tiles [42,43,58,59]; per-game hashes gate it.
-- Permitted native-size fan tree art is composed over checked Gen 3 ground.
local groups={
  {["game"]="red",["sourceHash"]="49f39f6059fef5e0ab5353dce0b47ef94e07f15d1219bba0b758939b71d74d52",["sourceFiles"]={["metadata"]="0c88e9ab0699a718f66d1ebb78ae7fe0c4bbc984a0dc8b9b18be542a0307b1d5",["image"]="7ed34ea824a79bf49520135c587d62182169b94855bf1958880778eb5c74f5c0",["maps"]="747230ee475113dda4d79df68ea96b3237c8c9022a80a57f43b9f3c5db707a0d"},["cells"]={{19,0},{19,1},{19,2},{19,3},{20,0},{20,2},{20,3},{21,1},{21,2},{21,3},{24,0},{24,2},{25,1},{25,3},{64,0},{65,2},{77,1},{77,3},{78,0},{78,2},{79,1},{79,2},{79,3},{80,0},{80,2},{80,3},{81,0},{81,1},{82,2},{82,3},{97,2},{97,3},{98,0},{98,1},{98,2},{99,0},{99,1},{99,3},{103,0},{103,2},{106,1},{106,3},{107,2},{107,3}}},
  {["game"]="blue",["sourceHash"]="49f39f6059fef5e0ab5353dce0b47ef94e07f15d1219bba0b758939b71d74d52",["sourceFiles"]={["metadata"]="b96cfa57ab7dd51f1e0e586b8127ad1c555f14c42310e0c3e3d6319f91229d5f",["image"]="7ed34ea824a79bf49520135c587d62182169b94855bf1958880778eb5c74f5c0",["maps"]="1ba67f8108a73e7c7ea7ab116e44d57f35dbe281b11499b81ab504b58f5e66e4"},["cells"]={{19,0},{19,1},{19,2},{19,3},{20,0},{20,2},{20,3},{21,1},{21,2},{21,3},{24,0},{24,2},{25,1},{25,3},{64,0},{65,2},{77,1},{77,3},{78,0},{78,2},{79,1},{79,2},{79,3},{80,0},{80,2},{80,3},{81,0},{81,1},{82,2},{82,3},{97,2},{97,3},{98,0},{98,1},{98,2},{99,0},{99,1},{99,3},{103,0},{103,2},{106,1},{106,3},{107,2},{107,3}}},
  {["game"]="yellow",["sourceHash"]="120a13afeedc52a7449f349f864551c3b624fc77cc4676e5f227fa752308a604",["sourceFiles"]={["metadata"]="5ab9e4659dc288389896334cb3f0cef372a70796cddb6f59c182a41391849c32",["image"]="5ca471616ea6f08baf3afeea7691cca4b9441d00c6bdf676a8428794044415e6",["maps"]="e926952399888dc032e2ca8e8a40205d4a1e73dc2c3036ec30449a65e5f3f55c"},["cells"]={{19,0},{19,1},{19,2},{19,3},{20,0},{20,2},{20,3},{21,1},{21,2},{21,3},{24,0},{24,2},{25,1},{25,3},{64,0},{65,2},{77,1},{77,3},{78,0},{78,2},{79,1},{79,2},{79,3},{80,0},{80,2},{80,3},{81,0},{81,1},{82,2},{82,3},{97,2},{97,3},{98,0},{98,1},{98,2},{99,0},{99,1},{99,3},{103,0},{103,2},{106,1},{106,3},{107,2},{107,3}}},
}
local base={["game"]="emerald",["tileset"]="general__petalburg",["id"]=1,["hash"]="1c7acc0ebc7c5878e77e1dfbbc2828e1a2745c0ded470f1f0152f67193222ed1"}
local rows={}
for _,group in ipairs(groups) do
  for _,cell in ipairs(group.cells) do
    rows[#rows+1]={
      game=group.game,style='gen3',tileset='OVERWORLD',id=cell[1],quadrant=cell[2],
      role='boundary_tree',status='reviewed',
      sourceHash=group.sourceHash,sourceFiles=group.sourceFiles,
      kind='original',asset='assets/original/compact-conifer/tree.png',
      assetFileHash="99f45e9cf6a7e9b18249c75533b4ff7c964c2675811249f689fd4b4544f0f9b2",
      assetPixelHash="24c0f42cd4f3f84917920659122e87443946b8618db591577197c9f39b1e0dba",
      credit='Original compact Emerald-style conifer; built-in imagegen',
      sourceUrl='https://github.com/Bentley734/TileShift/tree/main/assets/original/compact-conifer',
      base=base,
      evidence='The user approved compact Gen 3 trees following FireRed/LeafGreen after inspecting their actual Pallet outer-town tree boundary. This supersedes the earlier stone-post interpretation. These 44 aliases per cartridge have identical inspected source pixels; the complete native-size permitted fan tree fits the original 16px cell. Generated post artwork is no longer used. Source collision and scripts stay native.',
    }
  end
end
return rows
