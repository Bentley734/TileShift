-- Default one-cell tree revised: complete compact Emerald-style conifer; see assets/original/compact-conifer/provenance.json. Historical source-review evidence below remains recorded.
-- Visually reviewed compact tree substitutions, 2026-10-26.
-- OVERWORLD 15:0 is the engine's TREE_WALL_BLOCK (0x0f), a leafy dense tree.
-- Only identical used source pixels AND native behavior aliases are included.
-- Pallet BODY cylinders (for example 77:1/[42,43,58,59]) are not this tree;
-- the user later approved compact Gen 3 boundary trees following FR/LG.
-- Their separate pixel identities are mapped by the legacy posts.lua file.
-- The live off-map trees void-fill uses 0x0f independently of Pallet's header.
-- Artist sheet is not included; provenance.json records exact extraction.
local groups={
  {["game"]="red",["sourceHash"]="bb4085a06671c8b9efed7b208816c1b9adac283c60207460b7613b384268431b",["sourceFiles"]={["metadata"]="0c88e9ab0699a718f66d1ebb78ae7fe0c4bbc984a0dc8b9b18be542a0307b1d5",["image"]="7ed34ea824a79bf49520135c587d62182169b94855bf1958880778eb5c74f5c0",["maps"]="747230ee475113dda4d79df68ea96b3237c8c9022a80a57f43b9f3c5db707a0d"},["cells"]={{15,0},{15,1},{15,2},{15,3},{28,2},{28,3},{50,0},{50,2},{51,0},{51,1},{52,2},{52,3},{53,2},{54,0},{54,1},{54,3},{66,1},{66,3},{76,2},{96,1},{96,3},{108,0},{108,1},{109,0},{109,2},{110,1},{110,3},{111,2},{111,3}}},
  {["game"]="blue",["sourceHash"]="bb4085a06671c8b9efed7b208816c1b9adac283c60207460b7613b384268431b",["sourceFiles"]={["metadata"]="b96cfa57ab7dd51f1e0e586b8127ad1c555f14c42310e0c3e3d6319f91229d5f",["image"]="7ed34ea824a79bf49520135c587d62182169b94855bf1958880778eb5c74f5c0",["maps"]="1ba67f8108a73e7c7ea7ab116e44d57f35dbe281b11499b81ab504b58f5e66e4"},["cells"]={{15,0},{15,1},{15,2},{15,3},{28,2},{28,3},{50,0},{50,2},{51,0},{51,1},{52,2},{52,3},{53,2},{54,0},{54,1},{54,3},{66,1},{66,3},{76,2},{96,1},{96,3},{108,0},{108,1},{109,0},{109,2},{110,1},{110,3},{111,2},{111,3}}},
  {["game"]="yellow",["sourceHash"]="61c24cec283839ac50e4af8454e3af10c843b1c2984c490e6ec92d96ab92d319",["sourceFiles"]={["metadata"]="5ab9e4659dc288389896334cb3f0cef372a70796cddb6f59c182a41391849c32",["image"]="5ca471616ea6f08baf3afeea7691cca4b9441d00c6bdf676a8428794044415e6",["maps"]="e926952399888dc032e2ca8e8a40205d4a1e73dc2c3036ec30449a65e5f3f55c"},["cells"]={{15,0},{15,1},{15,2},{15,3},{28,2},{28,3},{50,0},{50,2},{51,0},{51,1},{52,2},{52,3},{53,2},{54,0},{54,1},{54,3},{66,1},{66,3},{76,2},{96,1},{96,3},{108,0},{108,1},{109,0},{109,2},{110,1},{110,3},{111,2},{111,3}}},
}
local rows={}
local base={["game"]="emerald",["tileset"]="general__petalburg",["id"]=1,["hash"]="1c7acc0ebc7c5878e77e1dfbbc2828e1a2745c0ded470f1f0152f67193222ed1"}
for _,group in ipairs(groups) do
  for _,cell in ipairs(group.cells) do
    rows[#rows+1]={
      game=group.game,style='gen3',tileset='OVERWORLD',
      id=cell[1],quadrant=cell[2],role='dense_round_tree',status='reviewed',
      sourceHash=group.sourceHash,sourceFiles=group.sourceFiles,
      kind='original',asset='assets/original/compact-conifer/tree.png',
      assetFileHash="99f45e9cf6a7e9b18249c75533b4ff7c964c2675811249f689fd4b4544f0f9b2",
      assetPixelHash="24c0f42cd4f3f84917920659122e87443946b8618db591577197c9f39b1e0dba",
      credit='Original compact Emerald-style conifer; built-in imagegen',
      sourceUrl='https://github.com/Bentley734/TileShift/tree/main/assets/original/compact-conifer',
      base=base,
      evidence='Source 0x0f leafy dense forest tree inspected in each cartridge. Artist candidate B4 is a complete compact 16px round tree with visible trunk; visually approved 2026-10-26. Aliases retain identical source pixels and native behavior. Transparent tree is composited over fingerprint-checked Emerald ground; source mechanics remain native.',
    }
  end
end
return rows
