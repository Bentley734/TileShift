-- Bounded decorative roof/sides. Never modifies source tiles or collision.
local R={}
function R.new(ctx)
  local G=ctx.graphics or love.graphics
  local groups,trees,furniture,cache,textures={},{},{},{},{}
  local closed,revision,quad=false,nil,nil
  local staticBorders=false
  for _,row in ipairs(ctx.rows or{})do
    -- A side may render outside the map-image canvas; validate its real
    -- fingerprint anchor with the same strict mapping validator. This copy
    -- is made once at construction, never in the draw/update path.
    local checked=row
    if row.side or row.sourceY~=nil or row.sourceX~=nil then
      checked={};for k,v in pairs(row)do checked[k]=v end
      checked.x=row.sourceX or row.x;checked.y=row.sourceY or row.y
    end
    assert(ctx.validate(checked),'Invalid reviewed decorative tile')
    local side=row.side=='left'or row.side=='right'
    local boundedSide=side and type(row.buildingX)=='number'and type(row.buildingY)=='number'
      and type(row.buildingW)=='number'and type(row.buildingH)=='number'
      and row.buildingX>=0 and row.buildingY>=0 and row.buildingW>0 and row.buildingH>0
      and row.buildingX%1==0 and row.buildingY%1==0 and row.buildingW%1==0 and row.buildingH%1==0
      and type(row.x)=='number'and row.x%1==0
      and ((row.side=='left'and row.x>=row.buildingX-2 and row.x<row.buildingX)
        or(row.side=='right'and row.x>=row.buildingX+row.buildingW and row.x<=row.buildingX+row.buildingW+1))
      and row.y>=row.buildingY and row.y<row.buildingY+row.buildingH
      and type(row.sourceX)=='number'and row.sourceX%1==0
    local above=row.side==nil and row.buildingY==row.y+1
    if row.sourceY~=nil then
      assert(above and row.y==-1 and row.buildingY==0 and row.sourceY==0,
        'Static north overhang must use the first source row')
    end
    if row.sourceX~=nil then
      assert(type(row.sourceX)=='number'and row.sourceX%1==0 and row.sourceX>=0,
        'Invalid decorative source column')
    end
    if row.sourceY~=nil or(row.sourceX~=nil and not row.side)then
      assert(above and type(row.buildingX)=='number'and row.buildingX>=0 and row.buildingX%1==0
        and type(row.buildingW)=='number'and row.buildingW>0 and row.buildingW%1==0
        and type(row.buildingH)=='number'and row.buildingH>0 and row.buildingH%1==0
        and row.x>=row.buildingX-2 and row.x<=row.buildingX+row.buildingW+1,
        'Anchored upper decoration must remain within its building envelope')
    end
    assert((row.game=='red'or row.game=='blue'or row.game=='yellow'or row.game=='gold'or row.game=='silver'or row.game=='crystal')and row.style=='gen3'
      and (row.kind=='original'or row.kind=='third_party'or row.kind=='native_composite')
      and row.map and row.x and row.y and(above or boundedSide),
      'Decoration must occupy one upper row or at most two adjacent side columns')
    local games=groups[row.game]or{};groups[row.game]=games
    local maps=games[row.map]or{};games[row.map]=maps
    maps[#maps+1]=row
    if row.side or row.sourceY~=nil or row.sourceX~=nil then staticBorders=true end
  end
  for _,row in ipairs(ctx.treeRows or{})do
    assert(ctx.validate(row)and row.canopy and row.role=='dense_conifer_crown'
      and row.style=='gen3'and(row.game=='gold'or row.game=='silver'or row.game=='crystal')
      and row.map and row.x==nil and row.y==nil,'Invalid reviewed tree canopy')
    local games=trees[row.game]or{};trees[row.game]=games
    local maps=games[row.map]or{};games[row.map]=maps
    local block=maps[row.id]or{};maps[row.id]=block
    assert(block[row.quadrant]==nil,'Duplicate tree canopy source alias')
    block[row.quadrant]=row
  end
  local upperPCMaps={["CELADON_POKECENTER_2F_BETA"]=true,["CERULEAN_POKECENTER_2F_BETA"]=true,["CINNABAR_POKECENTER_2F_BETA"]=true,["FUCHSIA_POKECENTER_2F_BETA"]=true,["LAVENDER_POKECENTER_2F_BETA"]=true,["PEWTER_POKECENTER_2F_BETA"]=true,["POKECENTER_2F"]=true,["ROUTE_10_POKECENTER_2F_BETA"]=true,["SAFFRON_POKECENTER_2F_BETA"]=true,["VERMILION_POKECENTER_2F_BETA"]=true,["VIRIDIAN_POKECENTER_2F_BETA"]=true}
  local shipBedAnchors={["gold"]={["FAST_SHIP_B1F"]={["21:10"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=192,["footX"]=21,["footY"]=11,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["23:10"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=192,["footX"]=23,["footY"]=11,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["25:10"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=192,["footX"]=25,["footY"]=11,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["27:10"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=192,["footX"]=27,["footY"]=11,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["21:12"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=224,["footX"]=21,["footY"]=13,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["23:12"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=224,["footX"]=23,["footY"]=13,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["25:12"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=224,["footX"]=25,["footY"]=13,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["27:12"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=224,["footX"]=27,["footY"]=13,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"}},["FAST_SHIP_CABINS_NNW_NNE_NE"]={["7:1"]={["id"]=56,["quadrant"]=3,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=48,["footX"]=7,["footY"]=2,["footId"]=57,["footQuadrant"]=1,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["1:30"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=512,["footX"]=1,["footY"]=31,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["3:30"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=512,["footX"]=3,["footY"]=31,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"}},["FAST_SHIP_CABINS_SE_SSE_CAPTAINS_CABIN"]={["1:2"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=64,["footX"]=1,["footY"]=3,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["3:2"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=64,["footX"]=3,["footY"]=3,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["7:13"]={["id"]=56,["quadrant"]=3,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=240,["footX"]=7,["footY"]=14,["footId"]=57,["footQuadrant"]=1,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["9:25"]={["id"]=56,["quadrant"]=3,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=432,["footX"]=9,["footY"]=26,["footId"]=57,["footQuadrant"]=1,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"}},["FAST_SHIP_CABINS_SW_SSW_NW"]={["7:1"]={["id"]=56,["quadrant"]=3,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=48,["footX"]=7,["footY"]=2,["footId"]=57,["footQuadrant"]=1,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["7:18"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=320,["footX"]=7,["footY"]=19,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["7:28"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=480,["footX"]=7,["footY"]=29,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["7:30"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=512,["footX"]=7,["footY"]=31,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"}}},["silver"]={["FAST_SHIP_B1F"]={["21:10"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=192,["footX"]=21,["footY"]=11,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["23:10"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=192,["footX"]=23,["footY"]=11,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["25:10"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=192,["footX"]=25,["footY"]=11,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["27:10"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=192,["footX"]=27,["footY"]=11,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["21:12"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=224,["footX"]=21,["footY"]=13,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["23:12"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=224,["footX"]=23,["footY"]=13,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["25:12"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=224,["footX"]=25,["footY"]=13,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["27:12"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=224,["footX"]=27,["footY"]=13,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"}},["FAST_SHIP_CABINS_NNW_NNE_NE"]={["7:1"]={["id"]=56,["quadrant"]=3,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=48,["footX"]=7,["footY"]=2,["footId"]=57,["footQuadrant"]=1,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["1:30"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=512,["footX"]=1,["footY"]=31,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["3:30"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=512,["footX"]=3,["footY"]=31,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"}},["FAST_SHIP_CABINS_SE_SSE_CAPTAINS_CABIN"]={["1:2"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=64,["footX"]=1,["footY"]=3,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["3:2"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=64,["footX"]=3,["footY"]=3,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["7:13"]={["id"]=56,["quadrant"]=3,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=240,["footX"]=7,["footY"]=14,["footId"]=57,["footQuadrant"]=1,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["9:25"]={["id"]=56,["quadrant"]=3,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=432,["footX"]=9,["footY"]=26,["footId"]=57,["footQuadrant"]=1,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"}},["FAST_SHIP_CABINS_SW_SSW_NW"]={["7:1"]={["id"]=56,["quadrant"]=3,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=48,["footX"]=7,["footY"]=2,["footId"]=57,["footQuadrant"]=1,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["7:18"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=320,["footX"]=7,["footY"]=19,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["7:28"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=480,["footX"]=7,["footY"]=29,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"},["7:30"]={["id"]=54,["quadrant"]=1,["sourceHash"]="c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150",["frontY"]=512,["footX"]=7,["footY"]=31,["footId"]=54,["footQuadrant"]=3,["footHash"]="732afc72dbbd4e1f9c7fc4da596f51159063015c9b3f2c283a6c1eabfa2b10ea"}}},["crystal"]={["FAST_SHIP_B1F"]={["21:10"]={["id"]=54,["quadrant"]=1,["sourceHash"]="174172f8f6fb3eac98ca33e52ae4b8b4e8912eddb47077444b3435fb520c16e3",["frontY"]=192,["footX"]=21,["footY"]=11,["footId"]=54,["footQuadrant"]=3,["footHash"]="eea9db525cfd0aaa83c8838a71ae157ac81905a898e7910aa3e8a64a3c9fbf1d"},["23:10"]={["id"]=54,["quadrant"]=1,["sourceHash"]="174172f8f6fb3eac98ca33e52ae4b8b4e8912eddb47077444b3435fb520c16e3",["frontY"]=192,["footX"]=23,["footY"]=11,["footId"]=54,["footQuadrant"]=3,["footHash"]="eea9db525cfd0aaa83c8838a71ae157ac81905a898e7910aa3e8a64a3c9fbf1d"},["25:10"]={["id"]=54,["quadrant"]=1,["sourceHash"]="174172f8f6fb3eac98ca33e52ae4b8b4e8912eddb47077444b3435fb520c16e3",["frontY"]=192,["footX"]=25,["footY"]=11,["footId"]=54,["footQuadrant"]=3,["footHash"]="eea9db525cfd0aaa83c8838a71ae157ac81905a898e7910aa3e8a64a3c9fbf1d"},["27:10"]={["id"]=54,["quadrant"]=1,["sourceHash"]="174172f8f6fb3eac98ca33e52ae4b8b4e8912eddb47077444b3435fb520c16e3",["frontY"]=192,["footX"]=27,["footY"]=11,["footId"]=54,["footQuadrant"]=3,["footHash"]="eea9db525cfd0aaa83c8838a71ae157ac81905a898e7910aa3e8a64a3c9fbf1d"},["21:12"]={["id"]=54,["quadrant"]=1,["sourceHash"]="174172f8f6fb3eac98ca33e52ae4b8b4e8912eddb47077444b3435fb520c16e3",["frontY"]=224,["footX"]=21,["footY"]=13,["footId"]=54,["footQuadrant"]=3,["footHash"]="eea9db525cfd0aaa83c8838a71ae157ac81905a898e7910aa3e8a64a3c9fbf1d"},["23:12"]={["id"]=54,["quadrant"]=1,["sourceHash"]="174172f8f6fb3eac98ca33e52ae4b8b4e8912eddb47077444b3435fb520c16e3",["frontY"]=224,["footX"]=23,["footY"]=13,["footId"]=54,["footQuadrant"]=3,["footHash"]="eea9db525cfd0aaa83c8838a71ae157ac81905a898e7910aa3e8a64a3c9fbf1d"},["25:12"]={["id"]=54,["quadrant"]=1,["sourceHash"]="174172f8f6fb3eac98ca33e52ae4b8b4e8912eddb47077444b3435fb520c16e3",["frontY"]=224,["footX"]=25,["footY"]=13,["footId"]=54,["footQuadrant"]=3,["footHash"]="eea9db525cfd0aaa83c8838a71ae157ac81905a898e7910aa3e8a64a3c9fbf1d"},["27:12"]={["id"]=54,["quadrant"]=1,["sourceHash"]="174172f8f6fb3eac98ca33e52ae4b8b4e8912eddb47077444b3435fb520c16e3",["frontY"]=224,["footX"]=27,["footY"]=13,["footId"]=54,["footQuadrant"]=3,["footHash"]="eea9db525cfd0aaa83c8838a71ae157ac81905a898e7910aa3e8a64a3c9fbf1d"}},["FAST_SHIP_CABINS_NNW_NNE_NE"]={["7:1"]={["id"]=56,["quadrant"]=3,["sourceHash"]="174172f8f6fb3eac98ca33e52ae4b8b4e8912eddb47077444b3435fb520c16e3",["frontY"]=48,["footX"]=7,["footY"]=2,["footId"]=57,["footQuadrant"]=1,["footHash"]="eea9db525cfd0aaa83c8838a71ae157ac81905a898e7910aa3e8a64a3c9fbf1d"},["1:30"]={["id"]=54,["quadrant"]=1,["sourceHash"]="174172f8f6fb3eac98ca33e52ae4b8b4e8912eddb47077444b3435fb520c16e3",["frontY"]=512,["footX"]=1,["footY"]=31,["footId"]=54,["footQuadrant"]=3,["footHash"]="eea9db525cfd0aaa83c8838a71ae157ac81905a898e7910aa3e8a64a3c9fbf1d"},["3:30"]={["id"]=54,["quadrant"]=1,["sourceHash"]="174172f8f6fb3eac98ca33e52ae4b8b4e8912eddb47077444b3435fb520c16e3",["frontY"]=512,["footX"]=3,["footY"]=31,["footId"]=54,["footQuadrant"]=3,["footHash"]="eea9db525cfd0aaa83c8838a71ae157ac81905a898e7910aa3e8a64a3c9fbf1d"}},["FAST_SHIP_CABINS_SE_SSE_CAPTAINS_CABIN"]={["1:2"]={["id"]=54,["quadrant"]=1,["sourceHash"]="174172f8f6fb3eac98ca33e52ae4b8b4e8912eddb47077444b3435fb520c16e3",["frontY"]=64,["footX"]=1,["footY"]=3,["footId"]=54,["footQuadrant"]=3,["footHash"]="eea9db525cfd0aaa83c8838a71ae157ac81905a898e7910aa3e8a64a3c9fbf1d"},["3:2"]={["id"]=54,["quadrant"]=1,["sourceHash"]="174172f8f6fb3eac98ca33e52ae4b8b4e8912eddb47077444b3435fb520c16e3",["frontY"]=64,["footX"]=3,["footY"]=3,["footId"]=54,["footQuadrant"]=3,["footHash"]="eea9db525cfd0aaa83c8838a71ae157ac81905a898e7910aa3e8a64a3c9fbf1d"},["7:13"]={["id"]=56,["quadrant"]=3,["sourceHash"]="174172f8f6fb3eac98ca33e52ae4b8b4e8912eddb47077444b3435fb520c16e3",["frontY"]=240,["footX"]=7,["footY"]=14,["footId"]=57,["footQuadrant"]=1,["footHash"]="eea9db525cfd0aaa83c8838a71ae157ac81905a898e7910aa3e8a64a3c9fbf1d"},["9:25"]={["id"]=56,["quadrant"]=3,["sourceHash"]="174172f8f6fb3eac98ca33e52ae4b8b4e8912eddb47077444b3435fb520c16e3",["frontY"]=432,["footX"]=9,["footY"]=26,["footId"]=57,["footQuadrant"]=1,["footHash"]="eea9db525cfd0aaa83c8838a71ae157ac81905a898e7910aa3e8a64a3c9fbf1d"}},["FAST_SHIP_CABINS_SW_SSW_NW"]={["7:1"]={["id"]=56,["quadrant"]=3,["sourceHash"]="174172f8f6fb3eac98ca33e52ae4b8b4e8912eddb47077444b3435fb520c16e3",["frontY"]=48,["footX"]=7,["footY"]=2,["footId"]=57,["footQuadrant"]=1,["footHash"]="eea9db525cfd0aaa83c8838a71ae157ac81905a898e7910aa3e8a64a3c9fbf1d"},["7:18"]={["id"]=54,["quadrant"]=1,["sourceHash"]="174172f8f6fb3eac98ca33e52ae4b8b4e8912eddb47077444b3435fb520c16e3",["frontY"]=320,["footX"]=7,["footY"]=19,["footId"]=54,["footQuadrant"]=3,["footHash"]="eea9db525cfd0aaa83c8838a71ae157ac81905a898e7910aa3e8a64a3c9fbf1d"},["7:28"]={["id"]=54,["quadrant"]=1,["sourceHash"]="174172f8f6fb3eac98ca33e52ae4b8b4e8912eddb47077444b3435fb520c16e3",["frontY"]=480,["footX"]=7,["footY"]=29,["footId"]=54,["footQuadrant"]=3,["footHash"]="eea9db525cfd0aaa83c8838a71ae157ac81905a898e7910aa3e8a64a3c9fbf1d"},["7:30"]={["id"]=54,["quadrant"]=1,["sourceHash"]="174172f8f6fb3eac98ca33e52ae4b8b4e8912eddb47077444b3435fb520c16e3",["frontY"]=512,["footX"]=7,["footY"]=31,["footId"]=54,["footQuadrant"]=3,["footHash"]="eea9db525cfd0aaa83c8838a71ae157ac81905a898e7910aa3e8a64a3c9fbf1d"}}}}
  local shipAnchorLimits={["FAST_SHIP_B1F"]=8,["FAST_SHIP_CABINS_NNW_NNE_NE"]=8,["FAST_SHIP_CABINS_SE_SSE_CAPTAINS_CABIN"]=8,["FAST_SHIP_CABINS_SW_SSW_NW"]=8}
  -- The entire authentic Kurt workbench is anchored to its unchanged source L.
  -- Every participating32px block is watched, including the former lower foot.
  local kurtBenchCells={
    {x=12,y=1,id=49,quadrant=2,hash='b9295a913782f9438c63c5f146202a3b262bc43a49fe338c068b9767d3ee220b'},
    {x=13,y=1,id=49,quadrant=3,hash='6aad667c7993cc7aa6b12104144ef5a0fe254f80ef3cb7bb567f61ede00a447c'},
    {x=14,y=1,id=50,quadrant=2,hash='0445289066f8beb0aa795030d84a8e012695ffeaa611049f3895abff46bdae26'},
    {x=15,y=1,id=50,quadrant=3,hash='85e05ca8d97d814a1ccc7ac5c0be84b0d7f6e11cf7ed1c4abdbb3be96301cb4c'},
    {x=12,y=2,id=51,quadrant=0,hash='1d068997799d518875612f5df729a90a02a1d42e6b58687a6d4053fa65622f98'},
    {x=13,y=2,id=51,quadrant=1,hash='1b32d0746f623c45f9c13689c2be40ca30ae95efbbeac5e5d2c8237569d62755'},
    {x=12,y=3,id=51,quadrant=2,hash='fae51ed02f5f74eb17faafcd6a4cbaece10efd262b3a4e22a0bde27c00ef2ffe'},
    {x=14,y=2,id=53,quadrant=0,hash='f728a12ca28ba217234f4dda04ba0a4274560d219b384ea1193b7fc2555e92d3'},
    {x=15,y=2,id=53,quadrant=1,hash='09276ddd3411793b5c8a62ee283232872ba8587040987d2d77f5db775ccbac92'},
    {x=12,y=4,id=54,quadrant=0,hash='fae51ed02f5f74eb17faafcd6a4cbaece10efd262b3a4e22a0bde27c00ef2ffe'},
    {x=12,y=5,id=54,quadrant=2,hash='fb006ef3e8a343bbf74801356e790b283332289945694d869117d277fcc8d779'},
  }
  local azaleaTreeHashes={
    'cbdb6c065210ca65781a327b7d776b53f80fb548173d5f71ade6f1cbb2ce6650',
    'e27d249251e5d1b68a55631041b8062346fc36acc606978199802c301ea9398a',
    'ff97f81649dcf1055be0ebeef7baf65bfdf5a231a0166e7f3d1d2a9f81fc3fb9',
    'cc86810bf719f37ed02658f3b1c08947304c2ae5b9925a204c51b78196f73c5f',
  }
  -- Finite original department-counter footprints and native piece identities.
  local departmentCounterSources={["crystal"]={["GOLDENROD_DEPT_STORE_1F"]={["anchorX"]=9,["anchorY"]=2,["cells"]={{["hash"]="8f8fce8abd561270a25973c9729dc11dd04cb0fadc2fa02bd8d0d6e1bbabadee",["id"]=8,["quadrant"]=1,["x"]=9,["y"]=0},{["hash"]="8f8fce8abd561270a25973c9729dc11dd04cb0fadc2fa02bd8d0d6e1bbabadee",["id"]=10,["quadrant"]=0,["x"]=12,["y"]=0},{["hash"]="c9658faaedf7e62d48c791f01ffa6222d9d4f2c2c73297e1953edf018c81661c",["id"]=8,["quadrant"]=3,["x"]=9,["y"]=1},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=9,["quadrant"]=2,["x"]=10,["y"]=1},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=9,["quadrant"]=3,["x"]=11,["y"]=1},{["hash"]="b51c0ebac662331da135eb93664f5638adbf07b2925a32666b94f7b9e46b6fa6",["id"]=10,["quadrant"]=2,["x"]=12,["y"]=1},{["hash"]="b9b003cb5c5621f895b2166da4949072f52153452d8091d7a9bda80a9a7ad900",["id"]=12,["quadrant"]=1,["x"]=9,["y"]=2},{["hash"]="8780028768c1c44fde5b4b505ac4ebc19599527400095dd2d883f2578307f94e",["id"]=13,["quadrant"]=0,["x"]=10,["y"]=2},{["hash"]="8780028768c1c44fde5b4b505ac4ebc19599527400095dd2d883f2578307f94e",["id"]=13,["quadrant"]=1,["x"]=11,["y"]=2},{["hash"]="776657a845a95979e78dc786b78c2ec8f5cc261a81b6a49069b532d91aaf3a93",["id"]=14,["quadrant"]=0,["x"]=12,["y"]=2}},["id"]=12,["pieces"]={["10:1"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6582c11004cc1799552a.png",["frontY"]=48,["hash"]="f2f3bb70871560eb4dddcadc6318429009214d7f0f8e18fce0864b09cad31947"},["10:2"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-16c9354880a9a7774d18.png",["frontY"]=48,["hash"]="41d6e8f459b7516cd5bdc9d2fcaaa9b6acb544b02364c02baa5abe30a79d8420"},["11:1"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-4b3a7daa9f7ac9b6d581.png",["frontY"]=48,["hash"]="335c007a4d5aa34e32ba0c26fb7ba7e4dde8b9dc2ffb8a4f8ab60df2b1787cd8"},["11:2"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-e702d7949d690b345ca6.png",["frontY"]=48,["hash"]="89fe0ade51fc81a008cfcd04d75ebdc32611f8d9d292ddd80c1d2630bb1017f7"},["12:0"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-2d7f0aea809f62e8d2e1.png",["frontY"]=48,["hash"]="b4ecc7515227e7111e41473c59d09879aae2627727e3ac7d123b48cdb0b14cca"},["12:1"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-3eed508e92c89dc7db9a.png",["frontY"]=48,["hash"]="5cec47489c31f913b9f7396e348690893f6613230bd0c71cffaf2506418b91d5"},["12:2"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-288c7ff75e04aaed419b.png",["frontY"]=48,["hash"]="524f2003cf6598170ea6c311cf9fe45a6c8057667dc292f11874f70684d85108"},["9:0"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-2d7f0aea809f62e8d2e1.png",["frontY"]=48,["hash"]="b4ecc7515227e7111e41473c59d09879aae2627727e3ac7d123b48cdb0b14cca"},["9:1"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-848fce8ccdf1b117f3fd.png",["frontY"]=48,["hash"]="edcea0fc1501b9f8045dc466be3d31caeae16cac2d85a183f5fbe49b878d12df"},["9:2"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-22b88c6bea27ef40dfd4.png",["frontY"]=48,["hash"]="b5c0d85c63874f8cc3a82f2295c3a4549298a2059644ac8b83b77d7ebd5550ff"}},["quadrant"]=1,["sourceCollision"]=144,["sourceHash"]="b9b003cb5c5621f895b2166da4949072f52153452d8091d7a9bda80a9a7ad900"},["GOLDENROD_DEPT_STORE_2F"]={["anchorX"]=12,["anchorY"]=4,["cells"]={{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=4,["quadrant"]=2,["x"]=12,["y"]=3},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=4,["quadrant"]=3,["x"]=13,["y"]=3},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=4,["quadrant"]=2,["x"]=14,["y"]=3},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=4,["quadrant"]=3,["x"]=15,["y"]=3},{["hash"]="036b90c0f01bebeb6f7400647ae37bf578640d727d398d7d4babd4bcde9f5c9c",["id"]=16,["quadrant"]=0,["x"]=12,["y"]=4},{["hash"]="97351a342ef935ce193b68076751b3a9e183f381a654f220956d53585930b57d",["id"]=16,["quadrant"]=1,["x"]=13,["y"]=4},{["hash"]="97351a342ef935ce193b68076751b3a9e183f381a654f220956d53585930b57d",["id"]=44,["quadrant"]=0,["x"]=14,["y"]=4},{["hash"]="97351a342ef935ce193b68076751b3a9e183f381a654f220956d53585930b57d",["id"]=44,["quadrant"]=1,["x"]=15,["y"]=4},{["hash"]="c9658faaedf7e62d48c791f01ffa6222d9d4f2c2c73297e1953edf018c81661c",["id"]=16,["quadrant"]=2,["x"]=12,["y"]=5},{["hash"]="8807ce1ae2b858a140d25687845909dda1d839a086492160284cbf13c608799c",["id"]=44,["quadrant"]=3,["x"]=15,["y"]=5},{["hash"]="c9658faaedf7e62d48c791f01ffa6222d9d4f2c2c73297e1953edf018c81661c",["id"]=46,["quadrant"]=0,["x"]=12,["y"]=6},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=46,["quadrant"]=1,["x"]=13,["y"]=6},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=45,["quadrant"]=0,["x"]=14,["y"]=6},{["hash"]="c4762e1e4d61da1987a2bdc4e7458be93bc9add26d5784a9a04f3f1c8ff4e67e",["id"]=45,["quadrant"]=1,["x"]=15,["y"]=6},{["hash"]="b9b003cb5c5621f895b2166da4949072f52153452d8091d7a9bda80a9a7ad900",["id"]=46,["quadrant"]=2,["x"]=12,["y"]=7},{["hash"]="8780028768c1c44fde5b4b505ac4ebc19599527400095dd2d883f2578307f94e",["id"]=46,["quadrant"]=3,["x"]=13,["y"]=7},{["hash"]="8780028768c1c44fde5b4b505ac4ebc19599527400095dd2d883f2578307f94e",["id"]=45,["quadrant"]=2,["x"]=14,["y"]=7},{["hash"]="8780028768c1c44fde5b4b505ac4ebc19599527400095dd2d883f2578307f94e",["id"]=45,["quadrant"]=3,["x"]=15,["y"]=7}},["id"]=16,["pieces"]={["12:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-603deded81c03bbe576b.png",["frontY"]=80,["hash"]="2f84652bd2bb86cbbe389a81501334a0a457a81f1cf1287dfc23c04c3c309c0f"},["12:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-2b7a8e1b02e185d574f8.png",["frontY"]=80,["hash"]="24d7ac37ec09bff4469df576961c1fc3a4c54123ab41a79d1342c9c94452072d"},["12:5"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6dcddc56b723432e193f.png",["frontY"]=96,["hash"]="edd70642024dbbbd44c64d7ccf99d578ef0b8a2f5cd54fb947f536fc10a644f7"},["12:6"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6dcddc56b723432e193f.png",["frontY"]=112,["hash"]="edd70642024dbbbd44c64d7ccf99d578ef0b8a2f5cd54fb947f536fc10a644f7"},["12:7"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-22b88c6bea27ef40dfd4.png",["frontY"]=128,["hash"]="b5c0d85c63874f8cc3a82f2295c3a4549298a2059644ac8b83b77d7ebd5550ff"},["13:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6582c11004cc1799552a.png",["frontY"]=80,["hash"]="f2f3bb70871560eb4dddcadc6318429009214d7f0f8e18fce0864b09cad31947"},["13:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-16c9354880a9a7774d18.png",["frontY"]=80,["hash"]="41d6e8f459b7516cd5bdc9d2fcaaa9b6acb544b02364c02baa5abe30a79d8420"},["13:6"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-4b3a7daa9f7ac9b6d581.png",["frontY"]=128,["hash"]="335c007a4d5aa34e32ba0c26fb7ba7e4dde8b9dc2ffb8a4f8ab60df2b1787cd8"},["13:7"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-e702d7949d690b345ca6.png",["frontY"]=128,["hash"]="89fe0ade51fc81a008cfcd04d75ebdc32611f8d9d292ddd80c1d2630bb1017f7"},["14:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-4b3a7daa9f7ac9b6d581.png",["frontY"]=80,["hash"]="335c007a4d5aa34e32ba0c26fb7ba7e4dde8b9dc2ffb8a4f8ab60df2b1787cd8"},["14:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-e702d7949d690b345ca6.png",["frontY"]=80,["hash"]="89fe0ade51fc81a008cfcd04d75ebdc32611f8d9d292ddd80c1d2630bb1017f7"},["14:6"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-4b3a7daa9f7ac9b6d581.png",["frontY"]=128,["hash"]="335c007a4d5aa34e32ba0c26fb7ba7e4dde8b9dc2ffb8a4f8ab60df2b1787cd8"},["14:7"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-e702d7949d690b345ca6.png",["frontY"]=128,["hash"]="89fe0ade51fc81a008cfcd04d75ebdc32611f8d9d292ddd80c1d2630bb1017f7"},["15:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6be7e0e06e0d01952945.png",["frontY"]=80,["hash"]="422074ba3e3a4a610fc81a70a5f78d441dff1eb0df9374de922659f2d51fcd8f"},["15:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-e7a911beee94612d1804.png",["frontY"]=112,["hash"]="97f2e92afc3010e76d0b435a3768a6a94091c650729eb409f731ca38ef65f0b7"},["15:5"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-02b755bc3ab8b4a3050d.png",["frontY"]=112,["hash"]="160ef88d1f79605aa12a74db4e7616ecf8c5419192221255fa0fedf67f642b0c"},["15:6"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-3e5d82feede94747ae8a.png",["frontY"]=128,["hash"]="719d67d4035d3273b773d2dc1fc953499b99cadd67379917f4b6cd813145128f"},["15:7"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-288c7ff75e04aaed419b.png",["frontY"]=128,["hash"]="524f2003cf6598170ea6c311cf9fe45a6c8057667dc292f11874f70684d85108"}},["quadrant"]=0,["sourceCollision"]=144,["sourceHash"]="036b90c0f01bebeb6f7400647ae37bf578640d727d398d7d4babd4bcde9f5c9c"},["GOLDENROD_DEPT_STORE_3F"]={["anchorX"]=5,["anchorY"]=2,["cells"]={{["hash"]="8f8fce8abd561270a25973c9729dc11dd04cb0fadc2fa02bd8d0d6e1bbabadee",["id"]=23,["quadrant"]=1,["x"]=5,["y"]=0},{["hash"]="8f8fce8abd561270a25973c9729dc11dd04cb0fadc2fa02bd8d0d6e1bbabadee",["id"]=10,["quadrant"]=0,["x"]=8,["y"]=0},{["hash"]="c9658faaedf7e62d48c791f01ffa6222d9d4f2c2c73297e1953edf018c81661c",["id"]=23,["quadrant"]=3,["x"]=5,["y"]=1},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=9,["quadrant"]=2,["x"]=6,["y"]=1},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=9,["quadrant"]=3,["x"]=7,["y"]=1},{["hash"]="b51c0ebac662331da135eb93664f5638adbf07b2925a32666b94f7b9e46b6fa6",["id"]=10,["quadrant"]=2,["x"]=8,["y"]=1},{["hash"]="b9b003cb5c5621f895b2166da4949072f52153452d8091d7a9bda80a9a7ad900",["id"]=12,["quadrant"]=1,["x"]=5,["y"]=2},{["hash"]="8780028768c1c44fde5b4b505ac4ebc19599527400095dd2d883f2578307f94e",["id"]=13,["quadrant"]=0,["x"]=6,["y"]=2},{["hash"]="8780028768c1c44fde5b4b505ac4ebc19599527400095dd2d883f2578307f94e",["id"]=13,["quadrant"]=1,["x"]=7,["y"]=2},{["hash"]="776657a845a95979e78dc786b78c2ec8f5cc261a81b6a49069b532d91aaf3a93",["id"]=14,["quadrant"]=0,["x"]=8,["y"]=2}},["id"]=12,["pieces"]={["5:0"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-2d7f0aea809f62e8d2e1.png",["frontY"]=48,["hash"]="b4ecc7515227e7111e41473c59d09879aae2627727e3ac7d123b48cdb0b14cca"},["5:1"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-848fce8ccdf1b117f3fd.png",["frontY"]=48,["hash"]="edcea0fc1501b9f8045dc466be3d31caeae16cac2d85a183f5fbe49b878d12df"},["5:2"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-22b88c6bea27ef40dfd4.png",["frontY"]=48,["hash"]="b5c0d85c63874f8cc3a82f2295c3a4549298a2059644ac8b83b77d7ebd5550ff"},["6:1"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6582c11004cc1799552a.png",["frontY"]=48,["hash"]="f2f3bb70871560eb4dddcadc6318429009214d7f0f8e18fce0864b09cad31947"},["6:2"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-16c9354880a9a7774d18.png",["frontY"]=48,["hash"]="41d6e8f459b7516cd5bdc9d2fcaaa9b6acb544b02364c02baa5abe30a79d8420"},["7:1"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-4b3a7daa9f7ac9b6d581.png",["frontY"]=48,["hash"]="335c007a4d5aa34e32ba0c26fb7ba7e4dde8b9dc2ffb8a4f8ab60df2b1787cd8"},["7:2"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-e702d7949d690b345ca6.png",["frontY"]=48,["hash"]="89fe0ade51fc81a008cfcd04d75ebdc32611f8d9d292ddd80c1d2630bb1017f7"},["8:0"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-2d7f0aea809f62e8d2e1.png",["frontY"]=48,["hash"]="b4ecc7515227e7111e41473c59d09879aae2627727e3ac7d123b48cdb0b14cca"},["8:1"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-3eed508e92c89dc7db9a.png",["frontY"]=48,["hash"]="5cec47489c31f913b9f7396e348690893f6613230bd0c71cffaf2506418b91d5"},["8:2"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-288c7ff75e04aaed419b.png",["frontY"]=48,["hash"]="524f2003cf6598170ea6c311cf9fe45a6c8057667dc292f11874f70684d85108"}},["quadrant"]=1,["sourceCollision"]=144,["sourceHash"]="b9b003cb5c5621f895b2166da4949072f52153452d8091d7a9bda80a9a7ad900"},["GOLDENROD_DEPT_STORE_4F"]={["anchorX"]=12,["anchorY"]=4,["cells"]={{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=4,["quadrant"]=2,["x"]=12,["y"]=3},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=4,["quadrant"]=3,["x"]=13,["y"]=3},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=4,["quadrant"]=2,["x"]=14,["y"]=3},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=4,["quadrant"]=3,["x"]=15,["y"]=3},{["hash"]="036b90c0f01bebeb6f7400647ae37bf578640d727d398d7d4babd4bcde9f5c9c",["id"]=16,["quadrant"]=0,["x"]=12,["y"]=4},{["hash"]="97351a342ef935ce193b68076751b3a9e183f381a654f220956d53585930b57d",["id"]=16,["quadrant"]=1,["x"]=13,["y"]=4},{["hash"]="97351a342ef935ce193b68076751b3a9e183f381a654f220956d53585930b57d",["id"]=17,["quadrant"]=0,["x"]=14,["y"]=4},{["hash"]="97351a342ef935ce193b68076751b3a9e183f381a654f220956d53585930b57d",["id"]=17,["quadrant"]=1,["x"]=15,["y"]=4},{["hash"]="c9658faaedf7e62d48c791f01ffa6222d9d4f2c2c73297e1953edf018c81661c",["id"]=16,["quadrant"]=2,["x"]=12,["y"]=5}},["id"]=16,["pieces"]={["12:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-603deded81c03bbe576b.png",["frontY"]=80,["hash"]="2f84652bd2bb86cbbe389a81501334a0a457a81f1cf1287dfc23c04c3c309c0f"},["12:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-2b7a8e1b02e185d574f8.png",["frontY"]=80,["hash"]="24d7ac37ec09bff4469df576961c1fc3a4c54123ab41a79d1342c9c94452072d"},["12:5"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-8d66aa4d2e53543b6c59.png",["frontY"]=96,["hash"]="0d43dcaf467282c44db927b6e635f2aef832fb0d0ee00ccf93bb6dbdd2584f57"},["13:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6582c11004cc1799552a.png",["frontY"]=80,["hash"]="f2f3bb70871560eb4dddcadc6318429009214d7f0f8e18fce0864b09cad31947"},["13:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-16c9354880a9a7774d18.png",["frontY"]=80,["hash"]="41d6e8f459b7516cd5bdc9d2fcaaa9b6acb544b02364c02baa5abe30a79d8420"},["14:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-4b3a7daa9f7ac9b6d581.png",["frontY"]=80,["hash"]="335c007a4d5aa34e32ba0c26fb7ba7e4dde8b9dc2ffb8a4f8ab60df2b1787cd8"},["14:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-e702d7949d690b345ca6.png",["frontY"]=80,["hash"]="89fe0ade51fc81a008cfcd04d75ebdc32611f8d9d292ddd80c1d2630bb1017f7"},["15:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6be7e0e06e0d01952945.png",["frontY"]=80,["hash"]="422074ba3e3a4a610fc81a70a5f78d441dff1eb0df9374de922659f2d51fcd8f"},["15:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-288c7ff75e04aaed419b.png",["frontY"]=80,["hash"]="524f2003cf6598170ea6c311cf9fe45a6c8057667dc292f11874f70684d85108"}},["quadrant"]=0,["sourceCollision"]=144,["sourceHash"]="036b90c0f01bebeb6f7400647ae37bf578640d727d398d7d4babd4bcde9f5c9c"},["GOLDENROD_DEPT_STORE_5F"]={["anchorX"]=6,["anchorY"]=4,["cells"]={{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=30,["quadrant"]=2,["x"]=6,["y"]=3},{["hash"]="cb245d1b5e168ecd974894979bfda574ffaf90c1a44043bc66a6397c234d8f66",["id"]=30,["quadrant"]=3,["x"]=7,["y"]=3},{["hash"]="64e47ea6b830d76ea11249ab85120bf06e76c31483be3a42a1a03a87698d266e",["id"]=31,["quadrant"]=2,["x"]=8,["y"]=3},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=31,["quadrant"]=3,["x"]=9,["y"]=3},{["hash"]="036b90c0f01bebeb6f7400647ae37bf578640d727d398d7d4babd4bcde9f5c9c",["id"]=26,["quadrant"]=0,["x"]=6,["y"]=4},{["hash"]="97351a342ef935ce193b68076751b3a9e183f381a654f220956d53585930b57d",["id"]=26,["quadrant"]=1,["x"]=7,["y"]=4},{["hash"]="97351a342ef935ce193b68076751b3a9e183f381a654f220956d53585930b57d",["id"]=27,["quadrant"]=0,["x"]=8,["y"]=4},{["hash"]="3bab771b029a33f48f16d7503c60400f9562564052180660d2f0dde9bc690270",["id"]=27,["quadrant"]=1,["x"]=9,["y"]=4},{["hash"]="c9658faaedf7e62d48c791f01ffa6222d9d4f2c2c73297e1953edf018c81661c",["id"]=26,["quadrant"]=2,["x"]=6,["y"]=5},{["hash"]="cbc3ca31eb8276a81438554f6874497890a714343b44a9baa974cba34b4567e7",["id"]=26,["quadrant"]=3,["x"]=7,["y"]=5},{["hash"]="cbc3ca31eb8276a81438554f6874497890a714343b44a9baa974cba34b4567e7",["id"]=27,["quadrant"]=2,["x"]=8,["y"]=5},{["hash"]="c9658faaedf7e62d48c791f01ffa6222d9d4f2c2c73297e1953edf018c81661c",["id"]=27,["quadrant"]=3,["x"]=9,["y"]=5},{["hash"]="cba12cafb35e87bf841d779233d2f7c53219179dc9777a2abe19a613b250f5a1",["id"]=28,["quadrant"]=0,["x"]=6,["y"]=6},{["hash"]="fa3ce1f09177d337a9d578f7b7f185fac6ae1df353de88b0a378bff90b38d683",["id"]=28,["quadrant"]=1,["x"]=7,["y"]=6},{["hash"]="fa3ce1f09177d337a9d578f7b7f185fac6ae1df353de88b0a378bff90b38d683",["id"]=29,["quadrant"]=0,["x"]=8,["y"]=6},{["hash"]="cba12cafb35e87bf841d779233d2f7c53219179dc9777a2abe19a613b250f5a1",["id"]=29,["quadrant"]=1,["x"]=9,["y"]=6}},["id"]=26,["pieces"]={["6:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-603deded81c03bbe576b.png",["frontY"]=80,["hash"]="2f84652bd2bb86cbbe389a81501334a0a457a81f1cf1287dfc23c04c3c309c0f"},["6:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-2b7a8e1b02e185d574f8.png",["frontY"]=80,["hash"]="24d7ac37ec09bff4469df576961c1fc3a4c54123ab41a79d1342c9c94452072d"},["6:5"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6dcddc56b723432e193f.png",["frontY"]=96,["hash"]="edd70642024dbbbd44c64d7ccf99d578ef0b8a2f5cd54fb947f536fc10a644f7"},["6:6"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-22b88c6bea27ef40dfd4.png",["frontY"]=112,["hash"]="b5c0d85c63874f8cc3a82f2295c3a4549298a2059644ac8b83b77d7ebd5550ff"},["7:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6582c11004cc1799552a.png",["frontY"]=80,["hash"]="f2f3bb70871560eb4dddcadc6318429009214d7f0f8e18fce0864b09cad31947"},["7:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-16c9354880a9a7774d18.png",["frontY"]=80,["hash"]="41d6e8f459b7516cd5bdc9d2fcaaa9b6acb544b02364c02baa5abe30a79d8420"},["7:5"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-4b3a7daa9f7ac9b6d581.png",["frontY"]=112,["hash"]="335c007a4d5aa34e32ba0c26fb7ba7e4dde8b9dc2ffb8a4f8ab60df2b1787cd8"},["7:6"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-e702d7949d690b345ca6.png",["frontY"]=112,["hash"]="89fe0ade51fc81a008cfcd04d75ebdc32611f8d9d292ddd80c1d2630bb1017f7"},["8:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-4b3a7daa9f7ac9b6d581.png",["frontY"]=80,["hash"]="335c007a4d5aa34e32ba0c26fb7ba7e4dde8b9dc2ffb8a4f8ab60df2b1787cd8"},["8:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-16c9354880a9a7774d18.png",["frontY"]=80,["hash"]="41d6e8f459b7516cd5bdc9d2fcaaa9b6acb544b02364c02baa5abe30a79d8420"},["8:5"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-4b3a7daa9f7ac9b6d581.png",["frontY"]=112,["hash"]="335c007a4d5aa34e32ba0c26fb7ba7e4dde8b9dc2ffb8a4f8ab60df2b1787cd8"},["8:6"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-e702d7949d690b345ca6.png",["frontY"]=112,["hash"]="89fe0ade51fc81a008cfcd04d75ebdc32611f8d9d292ddd80c1d2630bb1017f7"},["9:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6be7e0e06e0d01952945.png",["frontY"]=80,["hash"]="422074ba3e3a4a610fc81a70a5f78d441dff1eb0df9374de922659f2d51fcd8f"},["9:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-70367231624334145bb1.png",["frontY"]=80,["hash"]="e1c9590c41e4f535e2dc9ab44eaab260cf1f0071facb7382a27188c5a81e3042"},["9:5"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6dcddc56b723432e193f.png",["frontY"]=96,["hash"]="edd70642024dbbbd44c64d7ccf99d578ef0b8a2f5cd54fb947f536fc10a644f7"},["9:6"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-288c7ff75e04aaed419b.png",["frontY"]=112,["hash"]="524f2003cf6598170ea6c311cf9fe45a6c8057667dc292f11874f70684d85108"}},["quadrant"]=0,["sourceCollision"]=144,["sourceHash"]="036b90c0f01bebeb6f7400647ae37bf578640d727d398d7d4babd4bcde9f5c9c"}},["gold"]={["GOLDENROD_DEPT_STORE_1F"]={["anchorX"]=9,["anchorY"]=2,["cells"]={{["hash"]="8f8fce8abd561270a25973c9729dc11dd04cb0fadc2fa02bd8d0d6e1bbabadee",["id"]=8,["quadrant"]=1,["x"]=9,["y"]=0},{["hash"]="8f8fce8abd561270a25973c9729dc11dd04cb0fadc2fa02bd8d0d6e1bbabadee",["id"]=10,["quadrant"]=0,["x"]=12,["y"]=0},{["hash"]="c9658faaedf7e62d48c791f01ffa6222d9d4f2c2c73297e1953edf018c81661c",["id"]=8,["quadrant"]=3,["x"]=9,["y"]=1},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=9,["quadrant"]=2,["x"]=10,["y"]=1},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=9,["quadrant"]=3,["x"]=11,["y"]=1},{["hash"]="b51c0ebac662331da135eb93664f5638adbf07b2925a32666b94f7b9e46b6fa6",["id"]=10,["quadrant"]=2,["x"]=12,["y"]=1},{["hash"]="b9b003cb5c5621f895b2166da4949072f52153452d8091d7a9bda80a9a7ad900",["id"]=12,["quadrant"]=1,["x"]=9,["y"]=2},{["hash"]="8780028768c1c44fde5b4b505ac4ebc19599527400095dd2d883f2578307f94e",["id"]=13,["quadrant"]=0,["x"]=10,["y"]=2},{["hash"]="8780028768c1c44fde5b4b505ac4ebc19599527400095dd2d883f2578307f94e",["id"]=13,["quadrant"]=1,["x"]=11,["y"]=2},{["hash"]="776657a845a95979e78dc786b78c2ec8f5cc261a81b6a49069b532d91aaf3a93",["id"]=14,["quadrant"]=0,["x"]=12,["y"]=2}},["id"]=12,["pieces"]={["10:1"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6582c11004cc1799552a.png",["frontY"]=48,["hash"]="f2f3bb70871560eb4dddcadc6318429009214d7f0f8e18fce0864b09cad31947"},["10:2"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-16c9354880a9a7774d18.png",["frontY"]=48,["hash"]="41d6e8f459b7516cd5bdc9d2fcaaa9b6acb544b02364c02baa5abe30a79d8420"},["11:1"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-4b3a7daa9f7ac9b6d581.png",["frontY"]=48,["hash"]="335c007a4d5aa34e32ba0c26fb7ba7e4dde8b9dc2ffb8a4f8ab60df2b1787cd8"},["11:2"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-e702d7949d690b345ca6.png",["frontY"]=48,["hash"]="89fe0ade51fc81a008cfcd04d75ebdc32611f8d9d292ddd80c1d2630bb1017f7"},["12:0"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-2d7f0aea809f62e8d2e1.png",["frontY"]=48,["hash"]="b4ecc7515227e7111e41473c59d09879aae2627727e3ac7d123b48cdb0b14cca"},["12:1"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-3eed508e92c89dc7db9a.png",["frontY"]=48,["hash"]="5cec47489c31f913b9f7396e348690893f6613230bd0c71cffaf2506418b91d5"},["12:2"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-288c7ff75e04aaed419b.png",["frontY"]=48,["hash"]="524f2003cf6598170ea6c311cf9fe45a6c8057667dc292f11874f70684d85108"},["9:0"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-2d7f0aea809f62e8d2e1.png",["frontY"]=48,["hash"]="b4ecc7515227e7111e41473c59d09879aae2627727e3ac7d123b48cdb0b14cca"},["9:1"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-848fce8ccdf1b117f3fd.png",["frontY"]=48,["hash"]="edcea0fc1501b9f8045dc466be3d31caeae16cac2d85a183f5fbe49b878d12df"},["9:2"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-22b88c6bea27ef40dfd4.png",["frontY"]=48,["hash"]="b5c0d85c63874f8cc3a82f2295c3a4549298a2059644ac8b83b77d7ebd5550ff"}},["quadrant"]=1,["sourceCollision"]=144,["sourceHash"]="b9b003cb5c5621f895b2166da4949072f52153452d8091d7a9bda80a9a7ad900"},["GOLDENROD_DEPT_STORE_2F"]={["anchorX"]=12,["anchorY"]=4,["cells"]={{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=4,["quadrant"]=2,["x"]=12,["y"]=3},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=4,["quadrant"]=3,["x"]=13,["y"]=3},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=4,["quadrant"]=2,["x"]=14,["y"]=3},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=4,["quadrant"]=3,["x"]=15,["y"]=3},{["hash"]="036b90c0f01bebeb6f7400647ae37bf578640d727d398d7d4babd4bcde9f5c9c",["id"]=16,["quadrant"]=0,["x"]=12,["y"]=4},{["hash"]="97351a342ef935ce193b68076751b3a9e183f381a654f220956d53585930b57d",["id"]=16,["quadrant"]=1,["x"]=13,["y"]=4},{["hash"]="97351a342ef935ce193b68076751b3a9e183f381a654f220956d53585930b57d",["id"]=44,["quadrant"]=0,["x"]=14,["y"]=4},{["hash"]="97351a342ef935ce193b68076751b3a9e183f381a654f220956d53585930b57d",["id"]=44,["quadrant"]=1,["x"]=15,["y"]=4},{["hash"]="c9658faaedf7e62d48c791f01ffa6222d9d4f2c2c73297e1953edf018c81661c",["id"]=16,["quadrant"]=2,["x"]=12,["y"]=5},{["hash"]="8807ce1ae2b858a140d25687845909dda1d839a086492160284cbf13c608799c",["id"]=44,["quadrant"]=3,["x"]=15,["y"]=5},{["hash"]="c9658faaedf7e62d48c791f01ffa6222d9d4f2c2c73297e1953edf018c81661c",["id"]=46,["quadrant"]=0,["x"]=12,["y"]=6},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=46,["quadrant"]=1,["x"]=13,["y"]=6},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=45,["quadrant"]=0,["x"]=14,["y"]=6},{["hash"]="c4762e1e4d61da1987a2bdc4e7458be93bc9add26d5784a9a04f3f1c8ff4e67e",["id"]=45,["quadrant"]=1,["x"]=15,["y"]=6},{["hash"]="b9b003cb5c5621f895b2166da4949072f52153452d8091d7a9bda80a9a7ad900",["id"]=46,["quadrant"]=2,["x"]=12,["y"]=7},{["hash"]="8780028768c1c44fde5b4b505ac4ebc19599527400095dd2d883f2578307f94e",["id"]=46,["quadrant"]=3,["x"]=13,["y"]=7},{["hash"]="8780028768c1c44fde5b4b505ac4ebc19599527400095dd2d883f2578307f94e",["id"]=45,["quadrant"]=2,["x"]=14,["y"]=7},{["hash"]="8780028768c1c44fde5b4b505ac4ebc19599527400095dd2d883f2578307f94e",["id"]=45,["quadrant"]=3,["x"]=15,["y"]=7}},["id"]=16,["pieces"]={["12:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-603deded81c03bbe576b.png",["frontY"]=80,["hash"]="2f84652bd2bb86cbbe389a81501334a0a457a81f1cf1287dfc23c04c3c309c0f"},["12:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-2b7a8e1b02e185d574f8.png",["frontY"]=80,["hash"]="24d7ac37ec09bff4469df576961c1fc3a4c54123ab41a79d1342c9c94452072d"},["12:5"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6dcddc56b723432e193f.png",["frontY"]=96,["hash"]="edd70642024dbbbd44c64d7ccf99d578ef0b8a2f5cd54fb947f536fc10a644f7"},["12:6"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6dcddc56b723432e193f.png",["frontY"]=112,["hash"]="edd70642024dbbbd44c64d7ccf99d578ef0b8a2f5cd54fb947f536fc10a644f7"},["12:7"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-22b88c6bea27ef40dfd4.png",["frontY"]=128,["hash"]="b5c0d85c63874f8cc3a82f2295c3a4549298a2059644ac8b83b77d7ebd5550ff"},["13:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6582c11004cc1799552a.png",["frontY"]=80,["hash"]="f2f3bb70871560eb4dddcadc6318429009214d7f0f8e18fce0864b09cad31947"},["13:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-16c9354880a9a7774d18.png",["frontY"]=80,["hash"]="41d6e8f459b7516cd5bdc9d2fcaaa9b6acb544b02364c02baa5abe30a79d8420"},["13:6"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-4b3a7daa9f7ac9b6d581.png",["frontY"]=128,["hash"]="335c007a4d5aa34e32ba0c26fb7ba7e4dde8b9dc2ffb8a4f8ab60df2b1787cd8"},["13:7"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-e702d7949d690b345ca6.png",["frontY"]=128,["hash"]="89fe0ade51fc81a008cfcd04d75ebdc32611f8d9d292ddd80c1d2630bb1017f7"},["14:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-4b3a7daa9f7ac9b6d581.png",["frontY"]=80,["hash"]="335c007a4d5aa34e32ba0c26fb7ba7e4dde8b9dc2ffb8a4f8ab60df2b1787cd8"},["14:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-e702d7949d690b345ca6.png",["frontY"]=80,["hash"]="89fe0ade51fc81a008cfcd04d75ebdc32611f8d9d292ddd80c1d2630bb1017f7"},["14:6"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-4b3a7daa9f7ac9b6d581.png",["frontY"]=128,["hash"]="335c007a4d5aa34e32ba0c26fb7ba7e4dde8b9dc2ffb8a4f8ab60df2b1787cd8"},["14:7"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-e702d7949d690b345ca6.png",["frontY"]=128,["hash"]="89fe0ade51fc81a008cfcd04d75ebdc32611f8d9d292ddd80c1d2630bb1017f7"},["15:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6be7e0e06e0d01952945.png",["frontY"]=80,["hash"]="422074ba3e3a4a610fc81a70a5f78d441dff1eb0df9374de922659f2d51fcd8f"},["15:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-e7a911beee94612d1804.png",["frontY"]=112,["hash"]="97f2e92afc3010e76d0b435a3768a6a94091c650729eb409f731ca38ef65f0b7"},["15:5"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-02b755bc3ab8b4a3050d.png",["frontY"]=112,["hash"]="160ef88d1f79605aa12a74db4e7616ecf8c5419192221255fa0fedf67f642b0c"},["15:6"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-3e5d82feede94747ae8a.png",["frontY"]=128,["hash"]="719d67d4035d3273b773d2dc1fc953499b99cadd67379917f4b6cd813145128f"},["15:7"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-288c7ff75e04aaed419b.png",["frontY"]=128,["hash"]="524f2003cf6598170ea6c311cf9fe45a6c8057667dc292f11874f70684d85108"}},["quadrant"]=0,["sourceCollision"]=144,["sourceHash"]="036b90c0f01bebeb6f7400647ae37bf578640d727d398d7d4babd4bcde9f5c9c"},["GOLDENROD_DEPT_STORE_3F"]={["anchorX"]=5,["anchorY"]=2,["cells"]={{["hash"]="8f8fce8abd561270a25973c9729dc11dd04cb0fadc2fa02bd8d0d6e1bbabadee",["id"]=23,["quadrant"]=1,["x"]=5,["y"]=0},{["hash"]="8f8fce8abd561270a25973c9729dc11dd04cb0fadc2fa02bd8d0d6e1bbabadee",["id"]=10,["quadrant"]=0,["x"]=8,["y"]=0},{["hash"]="c9658faaedf7e62d48c791f01ffa6222d9d4f2c2c73297e1953edf018c81661c",["id"]=23,["quadrant"]=3,["x"]=5,["y"]=1},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=9,["quadrant"]=2,["x"]=6,["y"]=1},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=9,["quadrant"]=3,["x"]=7,["y"]=1},{["hash"]="b51c0ebac662331da135eb93664f5638adbf07b2925a32666b94f7b9e46b6fa6",["id"]=10,["quadrant"]=2,["x"]=8,["y"]=1},{["hash"]="b9b003cb5c5621f895b2166da4949072f52153452d8091d7a9bda80a9a7ad900",["id"]=12,["quadrant"]=1,["x"]=5,["y"]=2},{["hash"]="8780028768c1c44fde5b4b505ac4ebc19599527400095dd2d883f2578307f94e",["id"]=13,["quadrant"]=0,["x"]=6,["y"]=2},{["hash"]="8780028768c1c44fde5b4b505ac4ebc19599527400095dd2d883f2578307f94e",["id"]=13,["quadrant"]=1,["x"]=7,["y"]=2},{["hash"]="776657a845a95979e78dc786b78c2ec8f5cc261a81b6a49069b532d91aaf3a93",["id"]=14,["quadrant"]=0,["x"]=8,["y"]=2}},["id"]=12,["pieces"]={["5:0"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-2d7f0aea809f62e8d2e1.png",["frontY"]=48,["hash"]="b4ecc7515227e7111e41473c59d09879aae2627727e3ac7d123b48cdb0b14cca"},["5:1"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-848fce8ccdf1b117f3fd.png",["frontY"]=48,["hash"]="edcea0fc1501b9f8045dc466be3d31caeae16cac2d85a183f5fbe49b878d12df"},["5:2"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-22b88c6bea27ef40dfd4.png",["frontY"]=48,["hash"]="b5c0d85c63874f8cc3a82f2295c3a4549298a2059644ac8b83b77d7ebd5550ff"},["6:1"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6582c11004cc1799552a.png",["frontY"]=48,["hash"]="f2f3bb70871560eb4dddcadc6318429009214d7f0f8e18fce0864b09cad31947"},["6:2"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-16c9354880a9a7774d18.png",["frontY"]=48,["hash"]="41d6e8f459b7516cd5bdc9d2fcaaa9b6acb544b02364c02baa5abe30a79d8420"},["7:1"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-4b3a7daa9f7ac9b6d581.png",["frontY"]=48,["hash"]="335c007a4d5aa34e32ba0c26fb7ba7e4dde8b9dc2ffb8a4f8ab60df2b1787cd8"},["7:2"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-e702d7949d690b345ca6.png",["frontY"]=48,["hash"]="89fe0ade51fc81a008cfcd04d75ebdc32611f8d9d292ddd80c1d2630bb1017f7"},["8:0"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-2d7f0aea809f62e8d2e1.png",["frontY"]=48,["hash"]="b4ecc7515227e7111e41473c59d09879aae2627727e3ac7d123b48cdb0b14cca"},["8:1"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-3eed508e92c89dc7db9a.png",["frontY"]=48,["hash"]="5cec47489c31f913b9f7396e348690893f6613230bd0c71cffaf2506418b91d5"},["8:2"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-288c7ff75e04aaed419b.png",["frontY"]=48,["hash"]="524f2003cf6598170ea6c311cf9fe45a6c8057667dc292f11874f70684d85108"}},["quadrant"]=1,["sourceCollision"]=144,["sourceHash"]="b9b003cb5c5621f895b2166da4949072f52153452d8091d7a9bda80a9a7ad900"},["GOLDENROD_DEPT_STORE_4F"]={["anchorX"]=12,["anchorY"]=4,["cells"]={{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=4,["quadrant"]=2,["x"]=12,["y"]=3},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=4,["quadrant"]=3,["x"]=13,["y"]=3},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=4,["quadrant"]=2,["x"]=14,["y"]=3},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=4,["quadrant"]=3,["x"]=15,["y"]=3},{["hash"]="036b90c0f01bebeb6f7400647ae37bf578640d727d398d7d4babd4bcde9f5c9c",["id"]=16,["quadrant"]=0,["x"]=12,["y"]=4},{["hash"]="97351a342ef935ce193b68076751b3a9e183f381a654f220956d53585930b57d",["id"]=16,["quadrant"]=1,["x"]=13,["y"]=4},{["hash"]="97351a342ef935ce193b68076751b3a9e183f381a654f220956d53585930b57d",["id"]=17,["quadrant"]=0,["x"]=14,["y"]=4},{["hash"]="97351a342ef935ce193b68076751b3a9e183f381a654f220956d53585930b57d",["id"]=17,["quadrant"]=1,["x"]=15,["y"]=4},{["hash"]="c9658faaedf7e62d48c791f01ffa6222d9d4f2c2c73297e1953edf018c81661c",["id"]=16,["quadrant"]=2,["x"]=12,["y"]=5}},["id"]=16,["pieces"]={["12:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-603deded81c03bbe576b.png",["frontY"]=80,["hash"]="2f84652bd2bb86cbbe389a81501334a0a457a81f1cf1287dfc23c04c3c309c0f"},["12:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-2b7a8e1b02e185d574f8.png",["frontY"]=80,["hash"]="24d7ac37ec09bff4469df576961c1fc3a4c54123ab41a79d1342c9c94452072d"},["12:5"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-8d66aa4d2e53543b6c59.png",["frontY"]=96,["hash"]="0d43dcaf467282c44db927b6e635f2aef832fb0d0ee00ccf93bb6dbdd2584f57"},["13:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6582c11004cc1799552a.png",["frontY"]=80,["hash"]="f2f3bb70871560eb4dddcadc6318429009214d7f0f8e18fce0864b09cad31947"},["13:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-16c9354880a9a7774d18.png",["frontY"]=80,["hash"]="41d6e8f459b7516cd5bdc9d2fcaaa9b6acb544b02364c02baa5abe30a79d8420"},["14:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-4b3a7daa9f7ac9b6d581.png",["frontY"]=80,["hash"]="335c007a4d5aa34e32ba0c26fb7ba7e4dde8b9dc2ffb8a4f8ab60df2b1787cd8"},["14:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-e702d7949d690b345ca6.png",["frontY"]=80,["hash"]="89fe0ade51fc81a008cfcd04d75ebdc32611f8d9d292ddd80c1d2630bb1017f7"},["15:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6be7e0e06e0d01952945.png",["frontY"]=80,["hash"]="422074ba3e3a4a610fc81a70a5f78d441dff1eb0df9374de922659f2d51fcd8f"},["15:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-288c7ff75e04aaed419b.png",["frontY"]=80,["hash"]="524f2003cf6598170ea6c311cf9fe45a6c8057667dc292f11874f70684d85108"}},["quadrant"]=0,["sourceCollision"]=144,["sourceHash"]="036b90c0f01bebeb6f7400647ae37bf578640d727d398d7d4babd4bcde9f5c9c"},["GOLDENROD_DEPT_STORE_5F"]={["anchorX"]=6,["anchorY"]=4,["cells"]={{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=30,["quadrant"]=2,["x"]=6,["y"]=3},{["hash"]="cb245d1b5e168ecd974894979bfda574ffaf90c1a44043bc66a6397c234d8f66",["id"]=30,["quadrant"]=3,["x"]=7,["y"]=3},{["hash"]="64e47ea6b830d76ea11249ab85120bf06e76c31483be3a42a1a03a87698d266e",["id"]=31,["quadrant"]=2,["x"]=8,["y"]=3},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=31,["quadrant"]=3,["x"]=9,["y"]=3},{["hash"]="036b90c0f01bebeb6f7400647ae37bf578640d727d398d7d4babd4bcde9f5c9c",["id"]=26,["quadrant"]=0,["x"]=6,["y"]=4},{["hash"]="97351a342ef935ce193b68076751b3a9e183f381a654f220956d53585930b57d",["id"]=26,["quadrant"]=1,["x"]=7,["y"]=4},{["hash"]="97351a342ef935ce193b68076751b3a9e183f381a654f220956d53585930b57d",["id"]=27,["quadrant"]=0,["x"]=8,["y"]=4},{["hash"]="3bab771b029a33f48f16d7503c60400f9562564052180660d2f0dde9bc690270",["id"]=27,["quadrant"]=1,["x"]=9,["y"]=4},{["hash"]="c9658faaedf7e62d48c791f01ffa6222d9d4f2c2c73297e1953edf018c81661c",["id"]=26,["quadrant"]=2,["x"]=6,["y"]=5},{["hash"]="cbc3ca31eb8276a81438554f6874497890a714343b44a9baa974cba34b4567e7",["id"]=26,["quadrant"]=3,["x"]=7,["y"]=5},{["hash"]="cbc3ca31eb8276a81438554f6874497890a714343b44a9baa974cba34b4567e7",["id"]=27,["quadrant"]=2,["x"]=8,["y"]=5},{["hash"]="c9658faaedf7e62d48c791f01ffa6222d9d4f2c2c73297e1953edf018c81661c",["id"]=27,["quadrant"]=3,["x"]=9,["y"]=5},{["hash"]="cba12cafb35e87bf841d779233d2f7c53219179dc9777a2abe19a613b250f5a1",["id"]=28,["quadrant"]=0,["x"]=6,["y"]=6},{["hash"]="fa3ce1f09177d337a9d578f7b7f185fac6ae1df353de88b0a378bff90b38d683",["id"]=28,["quadrant"]=1,["x"]=7,["y"]=6},{["hash"]="fa3ce1f09177d337a9d578f7b7f185fac6ae1df353de88b0a378bff90b38d683",["id"]=29,["quadrant"]=0,["x"]=8,["y"]=6},{["hash"]="cba12cafb35e87bf841d779233d2f7c53219179dc9777a2abe19a613b250f5a1",["id"]=29,["quadrant"]=1,["x"]=9,["y"]=6}},["id"]=26,["pieces"]={["6:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-603deded81c03bbe576b.png",["frontY"]=80,["hash"]="2f84652bd2bb86cbbe389a81501334a0a457a81f1cf1287dfc23c04c3c309c0f"},["6:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-2b7a8e1b02e185d574f8.png",["frontY"]=80,["hash"]="24d7ac37ec09bff4469df576961c1fc3a4c54123ab41a79d1342c9c94452072d"},["6:5"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6dcddc56b723432e193f.png",["frontY"]=96,["hash"]="edd70642024dbbbd44c64d7ccf99d578ef0b8a2f5cd54fb947f536fc10a644f7"},["6:6"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-22b88c6bea27ef40dfd4.png",["frontY"]=112,["hash"]="b5c0d85c63874f8cc3a82f2295c3a4549298a2059644ac8b83b77d7ebd5550ff"},["7:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6582c11004cc1799552a.png",["frontY"]=80,["hash"]="f2f3bb70871560eb4dddcadc6318429009214d7f0f8e18fce0864b09cad31947"},["7:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-16c9354880a9a7774d18.png",["frontY"]=80,["hash"]="41d6e8f459b7516cd5bdc9d2fcaaa9b6acb544b02364c02baa5abe30a79d8420"},["7:5"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-4b3a7daa9f7ac9b6d581.png",["frontY"]=112,["hash"]="335c007a4d5aa34e32ba0c26fb7ba7e4dde8b9dc2ffb8a4f8ab60df2b1787cd8"},["7:6"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-e702d7949d690b345ca6.png",["frontY"]=112,["hash"]="89fe0ade51fc81a008cfcd04d75ebdc32611f8d9d292ddd80c1d2630bb1017f7"},["8:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-4b3a7daa9f7ac9b6d581.png",["frontY"]=80,["hash"]="335c007a4d5aa34e32ba0c26fb7ba7e4dde8b9dc2ffb8a4f8ab60df2b1787cd8"},["8:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-16c9354880a9a7774d18.png",["frontY"]=80,["hash"]="41d6e8f459b7516cd5bdc9d2fcaaa9b6acb544b02364c02baa5abe30a79d8420"},["8:5"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-4b3a7daa9f7ac9b6d581.png",["frontY"]=112,["hash"]="335c007a4d5aa34e32ba0c26fb7ba7e4dde8b9dc2ffb8a4f8ab60df2b1787cd8"},["8:6"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-e702d7949d690b345ca6.png",["frontY"]=112,["hash"]="89fe0ade51fc81a008cfcd04d75ebdc32611f8d9d292ddd80c1d2630bb1017f7"},["9:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6be7e0e06e0d01952945.png",["frontY"]=80,["hash"]="422074ba3e3a4a610fc81a70a5f78d441dff1eb0df9374de922659f2d51fcd8f"},["9:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-70367231624334145bb1.png",["frontY"]=80,["hash"]="e1c9590c41e4f535e2dc9ab44eaab260cf1f0071facb7382a27188c5a81e3042"},["9:5"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6dcddc56b723432e193f.png",["frontY"]=96,["hash"]="edd70642024dbbbd44c64d7ccf99d578ef0b8a2f5cd54fb947f536fc10a644f7"},["9:6"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-288c7ff75e04aaed419b.png",["frontY"]=112,["hash"]="524f2003cf6598170ea6c311cf9fe45a6c8057667dc292f11874f70684d85108"}},["quadrant"]=0,["sourceCollision"]=144,["sourceHash"]="036b90c0f01bebeb6f7400647ae37bf578640d727d398d7d4babd4bcde9f5c9c"}},["silver"]={["GOLDENROD_DEPT_STORE_1F"]={["anchorX"]=9,["anchorY"]=2,["cells"]={{["hash"]="8f8fce8abd561270a25973c9729dc11dd04cb0fadc2fa02bd8d0d6e1bbabadee",["id"]=8,["quadrant"]=1,["x"]=9,["y"]=0},{["hash"]="8f8fce8abd561270a25973c9729dc11dd04cb0fadc2fa02bd8d0d6e1bbabadee",["id"]=10,["quadrant"]=0,["x"]=12,["y"]=0},{["hash"]="c9658faaedf7e62d48c791f01ffa6222d9d4f2c2c73297e1953edf018c81661c",["id"]=8,["quadrant"]=3,["x"]=9,["y"]=1},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=9,["quadrant"]=2,["x"]=10,["y"]=1},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=9,["quadrant"]=3,["x"]=11,["y"]=1},{["hash"]="b51c0ebac662331da135eb93664f5638adbf07b2925a32666b94f7b9e46b6fa6",["id"]=10,["quadrant"]=2,["x"]=12,["y"]=1},{["hash"]="b9b003cb5c5621f895b2166da4949072f52153452d8091d7a9bda80a9a7ad900",["id"]=12,["quadrant"]=1,["x"]=9,["y"]=2},{["hash"]="8780028768c1c44fde5b4b505ac4ebc19599527400095dd2d883f2578307f94e",["id"]=13,["quadrant"]=0,["x"]=10,["y"]=2},{["hash"]="8780028768c1c44fde5b4b505ac4ebc19599527400095dd2d883f2578307f94e",["id"]=13,["quadrant"]=1,["x"]=11,["y"]=2},{["hash"]="776657a845a95979e78dc786b78c2ec8f5cc261a81b6a49069b532d91aaf3a93",["id"]=14,["quadrant"]=0,["x"]=12,["y"]=2}},["id"]=12,["pieces"]={["10:1"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6582c11004cc1799552a.png",["frontY"]=48,["hash"]="f2f3bb70871560eb4dddcadc6318429009214d7f0f8e18fce0864b09cad31947"},["10:2"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-16c9354880a9a7774d18.png",["frontY"]=48,["hash"]="41d6e8f459b7516cd5bdc9d2fcaaa9b6acb544b02364c02baa5abe30a79d8420"},["11:1"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-4b3a7daa9f7ac9b6d581.png",["frontY"]=48,["hash"]="335c007a4d5aa34e32ba0c26fb7ba7e4dde8b9dc2ffb8a4f8ab60df2b1787cd8"},["11:2"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-e702d7949d690b345ca6.png",["frontY"]=48,["hash"]="89fe0ade51fc81a008cfcd04d75ebdc32611f8d9d292ddd80c1d2630bb1017f7"},["12:0"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-2d7f0aea809f62e8d2e1.png",["frontY"]=48,["hash"]="b4ecc7515227e7111e41473c59d09879aae2627727e3ac7d123b48cdb0b14cca"},["12:1"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-3eed508e92c89dc7db9a.png",["frontY"]=48,["hash"]="5cec47489c31f913b9f7396e348690893f6613230bd0c71cffaf2506418b91d5"},["12:2"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-288c7ff75e04aaed419b.png",["frontY"]=48,["hash"]="524f2003cf6598170ea6c311cf9fe45a6c8057667dc292f11874f70684d85108"},["9:0"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-2d7f0aea809f62e8d2e1.png",["frontY"]=48,["hash"]="b4ecc7515227e7111e41473c59d09879aae2627727e3ac7d123b48cdb0b14cca"},["9:1"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-848fce8ccdf1b117f3fd.png",["frontY"]=48,["hash"]="edcea0fc1501b9f8045dc466be3d31caeae16cac2d85a183f5fbe49b878d12df"},["9:2"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-22b88c6bea27ef40dfd4.png",["frontY"]=48,["hash"]="b5c0d85c63874f8cc3a82f2295c3a4549298a2059644ac8b83b77d7ebd5550ff"}},["quadrant"]=1,["sourceCollision"]=144,["sourceHash"]="b9b003cb5c5621f895b2166da4949072f52153452d8091d7a9bda80a9a7ad900"},["GOLDENROD_DEPT_STORE_2F"]={["anchorX"]=12,["anchorY"]=4,["cells"]={{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=4,["quadrant"]=2,["x"]=12,["y"]=3},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=4,["quadrant"]=3,["x"]=13,["y"]=3},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=4,["quadrant"]=2,["x"]=14,["y"]=3},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=4,["quadrant"]=3,["x"]=15,["y"]=3},{["hash"]="036b90c0f01bebeb6f7400647ae37bf578640d727d398d7d4babd4bcde9f5c9c",["id"]=16,["quadrant"]=0,["x"]=12,["y"]=4},{["hash"]="97351a342ef935ce193b68076751b3a9e183f381a654f220956d53585930b57d",["id"]=16,["quadrant"]=1,["x"]=13,["y"]=4},{["hash"]="97351a342ef935ce193b68076751b3a9e183f381a654f220956d53585930b57d",["id"]=44,["quadrant"]=0,["x"]=14,["y"]=4},{["hash"]="97351a342ef935ce193b68076751b3a9e183f381a654f220956d53585930b57d",["id"]=44,["quadrant"]=1,["x"]=15,["y"]=4},{["hash"]="c9658faaedf7e62d48c791f01ffa6222d9d4f2c2c73297e1953edf018c81661c",["id"]=16,["quadrant"]=2,["x"]=12,["y"]=5},{["hash"]="8807ce1ae2b858a140d25687845909dda1d839a086492160284cbf13c608799c",["id"]=44,["quadrant"]=3,["x"]=15,["y"]=5},{["hash"]="c9658faaedf7e62d48c791f01ffa6222d9d4f2c2c73297e1953edf018c81661c",["id"]=46,["quadrant"]=0,["x"]=12,["y"]=6},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=46,["quadrant"]=1,["x"]=13,["y"]=6},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=45,["quadrant"]=0,["x"]=14,["y"]=6},{["hash"]="c4762e1e4d61da1987a2bdc4e7458be93bc9add26d5784a9a04f3f1c8ff4e67e",["id"]=45,["quadrant"]=1,["x"]=15,["y"]=6},{["hash"]="b9b003cb5c5621f895b2166da4949072f52153452d8091d7a9bda80a9a7ad900",["id"]=46,["quadrant"]=2,["x"]=12,["y"]=7},{["hash"]="8780028768c1c44fde5b4b505ac4ebc19599527400095dd2d883f2578307f94e",["id"]=46,["quadrant"]=3,["x"]=13,["y"]=7},{["hash"]="8780028768c1c44fde5b4b505ac4ebc19599527400095dd2d883f2578307f94e",["id"]=45,["quadrant"]=2,["x"]=14,["y"]=7},{["hash"]="8780028768c1c44fde5b4b505ac4ebc19599527400095dd2d883f2578307f94e",["id"]=45,["quadrant"]=3,["x"]=15,["y"]=7}},["id"]=16,["pieces"]={["12:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-603deded81c03bbe576b.png",["frontY"]=80,["hash"]="2f84652bd2bb86cbbe389a81501334a0a457a81f1cf1287dfc23c04c3c309c0f"},["12:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-2b7a8e1b02e185d574f8.png",["frontY"]=80,["hash"]="24d7ac37ec09bff4469df576961c1fc3a4c54123ab41a79d1342c9c94452072d"},["12:5"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6dcddc56b723432e193f.png",["frontY"]=96,["hash"]="edd70642024dbbbd44c64d7ccf99d578ef0b8a2f5cd54fb947f536fc10a644f7"},["12:6"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6dcddc56b723432e193f.png",["frontY"]=112,["hash"]="edd70642024dbbbd44c64d7ccf99d578ef0b8a2f5cd54fb947f536fc10a644f7"},["12:7"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-22b88c6bea27ef40dfd4.png",["frontY"]=128,["hash"]="b5c0d85c63874f8cc3a82f2295c3a4549298a2059644ac8b83b77d7ebd5550ff"},["13:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6582c11004cc1799552a.png",["frontY"]=80,["hash"]="f2f3bb70871560eb4dddcadc6318429009214d7f0f8e18fce0864b09cad31947"},["13:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-16c9354880a9a7774d18.png",["frontY"]=80,["hash"]="41d6e8f459b7516cd5bdc9d2fcaaa9b6acb544b02364c02baa5abe30a79d8420"},["13:6"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-4b3a7daa9f7ac9b6d581.png",["frontY"]=128,["hash"]="335c007a4d5aa34e32ba0c26fb7ba7e4dde8b9dc2ffb8a4f8ab60df2b1787cd8"},["13:7"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-e702d7949d690b345ca6.png",["frontY"]=128,["hash"]="89fe0ade51fc81a008cfcd04d75ebdc32611f8d9d292ddd80c1d2630bb1017f7"},["14:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-4b3a7daa9f7ac9b6d581.png",["frontY"]=80,["hash"]="335c007a4d5aa34e32ba0c26fb7ba7e4dde8b9dc2ffb8a4f8ab60df2b1787cd8"},["14:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-e702d7949d690b345ca6.png",["frontY"]=80,["hash"]="89fe0ade51fc81a008cfcd04d75ebdc32611f8d9d292ddd80c1d2630bb1017f7"},["14:6"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-4b3a7daa9f7ac9b6d581.png",["frontY"]=128,["hash"]="335c007a4d5aa34e32ba0c26fb7ba7e4dde8b9dc2ffb8a4f8ab60df2b1787cd8"},["14:7"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-e702d7949d690b345ca6.png",["frontY"]=128,["hash"]="89fe0ade51fc81a008cfcd04d75ebdc32611f8d9d292ddd80c1d2630bb1017f7"},["15:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6be7e0e06e0d01952945.png",["frontY"]=80,["hash"]="422074ba3e3a4a610fc81a70a5f78d441dff1eb0df9374de922659f2d51fcd8f"},["15:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-e7a911beee94612d1804.png",["frontY"]=112,["hash"]="97f2e92afc3010e76d0b435a3768a6a94091c650729eb409f731ca38ef65f0b7"},["15:5"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-02b755bc3ab8b4a3050d.png",["frontY"]=112,["hash"]="160ef88d1f79605aa12a74db4e7616ecf8c5419192221255fa0fedf67f642b0c"},["15:6"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-3e5d82feede94747ae8a.png",["frontY"]=128,["hash"]="719d67d4035d3273b773d2dc1fc953499b99cadd67379917f4b6cd813145128f"},["15:7"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-288c7ff75e04aaed419b.png",["frontY"]=128,["hash"]="524f2003cf6598170ea6c311cf9fe45a6c8057667dc292f11874f70684d85108"}},["quadrant"]=0,["sourceCollision"]=144,["sourceHash"]="036b90c0f01bebeb6f7400647ae37bf578640d727d398d7d4babd4bcde9f5c9c"},["GOLDENROD_DEPT_STORE_3F"]={["anchorX"]=5,["anchorY"]=2,["cells"]={{["hash"]="8f8fce8abd561270a25973c9729dc11dd04cb0fadc2fa02bd8d0d6e1bbabadee",["id"]=23,["quadrant"]=1,["x"]=5,["y"]=0},{["hash"]="8f8fce8abd561270a25973c9729dc11dd04cb0fadc2fa02bd8d0d6e1bbabadee",["id"]=10,["quadrant"]=0,["x"]=8,["y"]=0},{["hash"]="c9658faaedf7e62d48c791f01ffa6222d9d4f2c2c73297e1953edf018c81661c",["id"]=23,["quadrant"]=3,["x"]=5,["y"]=1},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=9,["quadrant"]=2,["x"]=6,["y"]=1},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=9,["quadrant"]=3,["x"]=7,["y"]=1},{["hash"]="b51c0ebac662331da135eb93664f5638adbf07b2925a32666b94f7b9e46b6fa6",["id"]=10,["quadrant"]=2,["x"]=8,["y"]=1},{["hash"]="b9b003cb5c5621f895b2166da4949072f52153452d8091d7a9bda80a9a7ad900",["id"]=12,["quadrant"]=1,["x"]=5,["y"]=2},{["hash"]="8780028768c1c44fde5b4b505ac4ebc19599527400095dd2d883f2578307f94e",["id"]=13,["quadrant"]=0,["x"]=6,["y"]=2},{["hash"]="8780028768c1c44fde5b4b505ac4ebc19599527400095dd2d883f2578307f94e",["id"]=13,["quadrant"]=1,["x"]=7,["y"]=2},{["hash"]="776657a845a95979e78dc786b78c2ec8f5cc261a81b6a49069b532d91aaf3a93",["id"]=14,["quadrant"]=0,["x"]=8,["y"]=2}},["id"]=12,["pieces"]={["5:0"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-2d7f0aea809f62e8d2e1.png",["frontY"]=48,["hash"]="b4ecc7515227e7111e41473c59d09879aae2627727e3ac7d123b48cdb0b14cca"},["5:1"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-848fce8ccdf1b117f3fd.png",["frontY"]=48,["hash"]="edcea0fc1501b9f8045dc466be3d31caeae16cac2d85a183f5fbe49b878d12df"},["5:2"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-22b88c6bea27ef40dfd4.png",["frontY"]=48,["hash"]="b5c0d85c63874f8cc3a82f2295c3a4549298a2059644ac8b83b77d7ebd5550ff"},["6:1"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6582c11004cc1799552a.png",["frontY"]=48,["hash"]="f2f3bb70871560eb4dddcadc6318429009214d7f0f8e18fce0864b09cad31947"},["6:2"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-16c9354880a9a7774d18.png",["frontY"]=48,["hash"]="41d6e8f459b7516cd5bdc9d2fcaaa9b6acb544b02364c02baa5abe30a79d8420"},["7:1"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-4b3a7daa9f7ac9b6d581.png",["frontY"]=48,["hash"]="335c007a4d5aa34e32ba0c26fb7ba7e4dde8b9dc2ffb8a4f8ab60df2b1787cd8"},["7:2"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-e702d7949d690b345ca6.png",["frontY"]=48,["hash"]="89fe0ade51fc81a008cfcd04d75ebdc32611f8d9d292ddd80c1d2630bb1017f7"},["8:0"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-2d7f0aea809f62e8d2e1.png",["frontY"]=48,["hash"]="b4ecc7515227e7111e41473c59d09879aae2627727e3ac7d123b48cdb0b14cca"},["8:1"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-3eed508e92c89dc7db9a.png",["frontY"]=48,["hash"]="5cec47489c31f913b9f7396e348690893f6613230bd0c71cffaf2506418b91d5"},["8:2"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-288c7ff75e04aaed419b.png",["frontY"]=48,["hash"]="524f2003cf6598170ea6c311cf9fe45a6c8057667dc292f11874f70684d85108"}},["quadrant"]=1,["sourceCollision"]=144,["sourceHash"]="b9b003cb5c5621f895b2166da4949072f52153452d8091d7a9bda80a9a7ad900"},["GOLDENROD_DEPT_STORE_4F"]={["anchorX"]=12,["anchorY"]=4,["cells"]={{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=4,["quadrant"]=2,["x"]=12,["y"]=3},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=4,["quadrant"]=3,["x"]=13,["y"]=3},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=4,["quadrant"]=2,["x"]=14,["y"]=3},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=4,["quadrant"]=3,["x"]=15,["y"]=3},{["hash"]="036b90c0f01bebeb6f7400647ae37bf578640d727d398d7d4babd4bcde9f5c9c",["id"]=16,["quadrant"]=0,["x"]=12,["y"]=4},{["hash"]="97351a342ef935ce193b68076751b3a9e183f381a654f220956d53585930b57d",["id"]=16,["quadrant"]=1,["x"]=13,["y"]=4},{["hash"]="97351a342ef935ce193b68076751b3a9e183f381a654f220956d53585930b57d",["id"]=17,["quadrant"]=0,["x"]=14,["y"]=4},{["hash"]="97351a342ef935ce193b68076751b3a9e183f381a654f220956d53585930b57d",["id"]=17,["quadrant"]=1,["x"]=15,["y"]=4},{["hash"]="c9658faaedf7e62d48c791f01ffa6222d9d4f2c2c73297e1953edf018c81661c",["id"]=16,["quadrant"]=2,["x"]=12,["y"]=5}},["id"]=16,["pieces"]={["12:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-603deded81c03bbe576b.png",["frontY"]=80,["hash"]="2f84652bd2bb86cbbe389a81501334a0a457a81f1cf1287dfc23c04c3c309c0f"},["12:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-2b7a8e1b02e185d574f8.png",["frontY"]=80,["hash"]="24d7ac37ec09bff4469df576961c1fc3a4c54123ab41a79d1342c9c94452072d"},["12:5"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-8d66aa4d2e53543b6c59.png",["frontY"]=96,["hash"]="0d43dcaf467282c44db927b6e635f2aef832fb0d0ee00ccf93bb6dbdd2584f57"},["13:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6582c11004cc1799552a.png",["frontY"]=80,["hash"]="f2f3bb70871560eb4dddcadc6318429009214d7f0f8e18fce0864b09cad31947"},["13:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-16c9354880a9a7774d18.png",["frontY"]=80,["hash"]="41d6e8f459b7516cd5bdc9d2fcaaa9b6acb544b02364c02baa5abe30a79d8420"},["14:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-4b3a7daa9f7ac9b6d581.png",["frontY"]=80,["hash"]="335c007a4d5aa34e32ba0c26fb7ba7e4dde8b9dc2ffb8a4f8ab60df2b1787cd8"},["14:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-e702d7949d690b345ca6.png",["frontY"]=80,["hash"]="89fe0ade51fc81a008cfcd04d75ebdc32611f8d9d292ddd80c1d2630bb1017f7"},["15:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6be7e0e06e0d01952945.png",["frontY"]=80,["hash"]="422074ba3e3a4a610fc81a70a5f78d441dff1eb0df9374de922659f2d51fcd8f"},["15:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-288c7ff75e04aaed419b.png",["frontY"]=80,["hash"]="524f2003cf6598170ea6c311cf9fe45a6c8057667dc292f11874f70684d85108"}},["quadrant"]=0,["sourceCollision"]=144,["sourceHash"]="036b90c0f01bebeb6f7400647ae37bf578640d727d398d7d4babd4bcde9f5c9c"},["GOLDENROD_DEPT_STORE_5F"]={["anchorX"]=6,["anchorY"]=4,["cells"]={{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=30,["quadrant"]=2,["x"]=6,["y"]=3},{["hash"]="cb245d1b5e168ecd974894979bfda574ffaf90c1a44043bc66a6397c234d8f66",["id"]=30,["quadrant"]=3,["x"]=7,["y"]=3},{["hash"]="64e47ea6b830d76ea11249ab85120bf06e76c31483be3a42a1a03a87698d266e",["id"]=31,["quadrant"]=2,["x"]=8,["y"]=3},{["hash"]="524b73e151ec45d57aca07b3b9d64b8ccb7498353276bfc83661fee237e0f932",["id"]=31,["quadrant"]=3,["x"]=9,["y"]=3},{["hash"]="036b90c0f01bebeb6f7400647ae37bf578640d727d398d7d4babd4bcde9f5c9c",["id"]=26,["quadrant"]=0,["x"]=6,["y"]=4},{["hash"]="97351a342ef935ce193b68076751b3a9e183f381a654f220956d53585930b57d",["id"]=26,["quadrant"]=1,["x"]=7,["y"]=4},{["hash"]="97351a342ef935ce193b68076751b3a9e183f381a654f220956d53585930b57d",["id"]=27,["quadrant"]=0,["x"]=8,["y"]=4},{["hash"]="3bab771b029a33f48f16d7503c60400f9562564052180660d2f0dde9bc690270",["id"]=27,["quadrant"]=1,["x"]=9,["y"]=4},{["hash"]="c9658faaedf7e62d48c791f01ffa6222d9d4f2c2c73297e1953edf018c81661c",["id"]=26,["quadrant"]=2,["x"]=6,["y"]=5},{["hash"]="cbc3ca31eb8276a81438554f6874497890a714343b44a9baa974cba34b4567e7",["id"]=26,["quadrant"]=3,["x"]=7,["y"]=5},{["hash"]="cbc3ca31eb8276a81438554f6874497890a714343b44a9baa974cba34b4567e7",["id"]=27,["quadrant"]=2,["x"]=8,["y"]=5},{["hash"]="c9658faaedf7e62d48c791f01ffa6222d9d4f2c2c73297e1953edf018c81661c",["id"]=27,["quadrant"]=3,["x"]=9,["y"]=5},{["hash"]="cba12cafb35e87bf841d779233d2f7c53219179dc9777a2abe19a613b250f5a1",["id"]=28,["quadrant"]=0,["x"]=6,["y"]=6},{["hash"]="fa3ce1f09177d337a9d578f7b7f185fac6ae1df353de88b0a378bff90b38d683",["id"]=28,["quadrant"]=1,["x"]=7,["y"]=6},{["hash"]="fa3ce1f09177d337a9d578f7b7f185fac6ae1df353de88b0a378bff90b38d683",["id"]=29,["quadrant"]=0,["x"]=8,["y"]=6},{["hash"]="cba12cafb35e87bf841d779233d2f7c53219179dc9777a2abe19a613b250f5a1",["id"]=29,["quadrant"]=1,["x"]=9,["y"]=6}},["id"]=26,["pieces"]={["6:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-603deded81c03bbe576b.png",["frontY"]=80,["hash"]="2f84652bd2bb86cbbe389a81501334a0a457a81f1cf1287dfc23c04c3c309c0f"},["6:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-2b7a8e1b02e185d574f8.png",["frontY"]=80,["hash"]="24d7ac37ec09bff4469df576961c1fc3a4c54123ab41a79d1342c9c94452072d"},["6:5"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6dcddc56b723432e193f.png",["frontY"]=96,["hash"]="edd70642024dbbbd44c64d7ccf99d578ef0b8a2f5cd54fb947f536fc10a644f7"},["6:6"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-22b88c6bea27ef40dfd4.png",["frontY"]=112,["hash"]="b5c0d85c63874f8cc3a82f2295c3a4549298a2059644ac8b83b77d7ebd5550ff"},["7:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6582c11004cc1799552a.png",["frontY"]=80,["hash"]="f2f3bb70871560eb4dddcadc6318429009214d7f0f8e18fce0864b09cad31947"},["7:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-16c9354880a9a7774d18.png",["frontY"]=80,["hash"]="41d6e8f459b7516cd5bdc9d2fcaaa9b6acb544b02364c02baa5abe30a79d8420"},["7:5"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-4b3a7daa9f7ac9b6d581.png",["frontY"]=112,["hash"]="335c007a4d5aa34e32ba0c26fb7ba7e4dde8b9dc2ffb8a4f8ab60df2b1787cd8"},["7:6"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-e702d7949d690b345ca6.png",["frontY"]=112,["hash"]="89fe0ade51fc81a008cfcd04d75ebdc32611f8d9d292ddd80c1d2630bb1017f7"},["8:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-4b3a7daa9f7ac9b6d581.png",["frontY"]=80,["hash"]="335c007a4d5aa34e32ba0c26fb7ba7e4dde8b9dc2ffb8a4f8ab60df2b1787cd8"},["8:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-16c9354880a9a7774d18.png",["frontY"]=80,["hash"]="41d6e8f459b7516cd5bdc9d2fcaaa9b6acb544b02364c02baa5abe30a79d8420"},["8:5"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-4b3a7daa9f7ac9b6d581.png",["frontY"]=112,["hash"]="335c007a4d5aa34e32ba0c26fb7ba7e4dde8b9dc2ffb8a4f8ab60df2b1787cd8"},["8:6"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-e702d7949d690b345ca6.png",["frontY"]=112,["hash"]="89fe0ade51fc81a008cfcd04d75ebdc32611f8d9d292ddd80c1d2630bb1017f7"},["9:3"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6be7e0e06e0d01952945.png",["frontY"]=80,["hash"]="422074ba3e3a4a610fc81a70a5f78d441dff1eb0df9374de922659f2d51fcd8f"},["9:4"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-70367231624334145bb1.png",["frontY"]=80,["hash"]="e1c9590c41e4f535e2dc9ab44eaab260cf1f0071facb7382a27188c5a81e3042"},["9:5"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-6dcddc56b723432e193f.png",["frontY"]=96,["hash"]="edd70642024dbbbd44c64d7ccf99d578ef0b8a2f5cd54fb947f536fc10a644f7"},["9:6"]={["asset"]="assets/third_party/johto-hacks/crystaldust-department-counters/cell-288c7ff75e04aaed419b.png",["frontY"]=112,["hash"]="524f2003cf6598170ea6c311cf9fe45a6c8057667dc292f11874f70684d85108"}},["quadrant"]=0,["sourceCollision"]=144,["sourceHash"]="036b90c0f01bebeb6f7400647ae37bf578640d727d398d7d4babd4bcde9f5c9c"}}}
  for _,row in ipairs(ctx.furnitureRows or{})do
    -- Furniture has its own explicit, small source envelopes. It is neither a
    -- conifer canopy nor a positioned mapping: callbacks can activate its
    -- checked block after the bare room has already warmed its map cache.
    local coords=type(row.x)=='number'and row.x%1==0 and type(row.y)=='number'and row.y%1==0
    local bedroom=(row.game=='gold'or row.game=='silver'or row.game=='crystal')
      and row.map=='PLAYERS_HOUSE_2F'and row.tileset=='TILESET_PLAYERS_ROOM'
    local bed=coords and row.furniture=='bed'and bedroom
      and type(row.id)=='number'and row.id>=27 and row.id<=30 and row.id%1==0
      and row.anchorX==0 and row.anchorY==4 and row.x>=0 and row.x<=1 and row.y>=3 and row.y<=5
      and row.quadrant==0 and row.frontY==96
    local pc=coords and row.furniture=='elm_pc'and row.game=='crystal'and row.map=='ELMS_LAB'and row.tileset=='TILESET_LAB'
      and row.id==33 and row.anchorX==2 and row.anchorY==4 and row.x>=2 and row.x<=3 and row.y>=4 and row.y<=5
      and row.quadrant==0 and row.frontY==96
    local carpet=coords and row.furniture=='carpet'and bedroom
      and(row.id==9 or row.id==12 or row.id==15 or row.id==18)
      and(row.anchorX==0 or row.anchorX==5)and row.anchorY==2 and row.x==row.anchorX
      and(row.y==2 or row.y==3)and row.quadrant==row.anchorX%2 and row.frontY==nil
    local shrine=coords and row.furniture=='ilex_shrine'
      and(row.game=='gold'or row.game=='silver'or row.game=='crystal')
      and row.map=='ILEX_FOREST'and row.tileset=='TILESET_FOREST'
      and row.id==32 and row.quadrant==0 and row.anchorX==8 and row.anchorY==22
      and row.sourceHash=='7909c2afb5b8ad5d87ad24345244efdbd3798b6908ec2c32a9ddec904b498b42'
      and row.sourceCollision==7 and row.role=='ilex_crystaldust_native_shrine'
      and row.x>=7 and row.x<=9 and row.y>=21 and row.y<=23 and row.frontY==380
    local lighthouse=(row.game=='gold'or row.game=='silver'or row.game=='crystal')
      and row.map=='OLIVINE_LIGHTHOUSE_6F'and row.tileset=='TILESET_LIGHTHOUSE'
    local bedHash={gold='c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150',
      silver='c385a5bdb9b237570bbb108de4df72c0f96be91ba1caa7d921940ab1e53fe150',
      crystal='174172f8f6fb3eac98ca33e52ae4b8b4e8912eddb47077444b3435fb520c16e3'}
    local tableHash={gold='f1f1a9a311726cb727513dc98898528e04138e2ae5c26afc42bf176cad9b4d4a',
      silver='f1f1a9a311726cb727513dc98898528e04138e2ae5c26afc42bf176cad9b4d4a',
      crystal='cd6d3daa76f4aa557f43655289dd483fee61c29a4341e9c9af1f1385c1c559ca'}
    local lighthouseBed=coords and lighthouse and row.furniture=='lighthouse_bed'
      and row.id==54 and row.quadrant==1 and row.anchorX==11 and row.anchorY==6
      and row.sourceHash==bedHash[row.game]and row.sourceCollision==7
      and row.role=='olivine_crystaldust_native_medical_bed'
      and row.x>=10 and row.x<=11 and row.y>=6 and row.y<=7 and row.frontY==128
    local lighthouseTable=coords and lighthouse and row.furniture=='lighthouse_table'
      and row.id==6 and row.quadrant==2 and row.anchorX==6 and row.anchorY==9
      and row.sourceHash==tableHash[row.game]and row.sourceCollision==7
      and row.role=='olivine_crystaldust_native_table'
      and row.x>=6 and row.x<=7 and row.y>=8 and row.y<=11 and row.frontY==192
    local linkMachine=coords and row.furniture=='link_trade_apparatus'
      and(row.game=='gold'or row.game=='silver'or row.game=='crystal')
      and(row.map=='TRADE_CENTER'or row.map=='TIME_CAPSULE')and row.tileset=='TILESET_GATE'
      and row.id==33 and row.quadrant==0 and row.anchorX==4 and row.anchorY==4
      and row.sourceHash=='1e0be084305e405fe6e6e55e3043b19e7d100bfac0d4dc496d3661c07ef29ccb'
      and row.sourceCollision==144 and row.role=='crystaldust_native_link_trade_apparatus'
      and row.x>=3 and row.x<=6 and row.y>=2 and row.y<=4 and row.frontY==76
    local battleMachine=coords and row.furniture=='link_battle_apparatus'
      and(row.game=='gold'or row.game=='silver'or row.game=='crystal')
      and row.map=='COLOSSEUM'and row.tileset=='TILESET_GATE'
      and row.id==29 and row.quadrant==0 and row.anchorX==4 and row.anchorY==4
      and row.sourceHash=='1a1c7d4b890f991a1290f715332ee869b8c2eb211929e52a0f5dc95284ddfe5d'
      and row.sourceCollision==7 and row.role=='crystaldust_native_link_battle_apparatus'
      and row.x>=3 and row.x<=6 and row.y>=2 and row.y<=4 and row.frontY==76
    local mrPokemonPC=coords and row.furniture=='mr_pokemon_pc'
      and(row.game=='gold'or row.game=='silver'or row.game=='crystal')
      and row.map=='MR_POKEMONS_HOUSE'and row.tileset=='TILESET_FACILITY'
      and row.id==40 and row.quadrant==0 and row.anchorX==6 and row.anchorY==4
      and row.sourceHash=='db23202aaa2045d6e5c03289eb4979eb90847fc827155f15fce037c75f710837'
      and row.sourceCollision==7 and row.role=='route30_crystaldust_oak_workstation'
      and row.x>=6 and row.x<=7 and row.y>=3 and row.y<=4 and row.frontY==80
    local upperPC=coords and row.furniture=='pokecenter_upper_pc'
      and(row.game=='gold'or row.game=='silver'or row.game=='crystal')
      and upperPCMaps[row.map]and row.tileset=='TILESET_POKECENTER'
      and row.id==50 and row.quadrant==0 and row.anchorX==2 and row.anchorY==2
      and row.sourceHash=='fee446d3a4961d29dd5190ffddf57d3c4d70c1e76b3e499cf19a983f78ebc681'
      and row.sourceCollision==147 and row.role=='crystaldust_complete_upper_room_pc'
      and row.x==2 and row.y>=1 and row.y<=2 and row.frontY==48
    local redBed=coords and row.furniture=='red_house_bed'
      and(row.game=='gold'or row.game=='silver'or row.game=='crystal')
      and row.map=='REDS_HOUSE_2F'and row.tileset=='TILESET_PLAYERS_HOUSE'
      and row.id==34 and row.quadrant==0 and row.anchorX==0 and row.anchorY==6
      and row.sourceHash=='72121c5cd7c189b972a20a70e9d1510f288c87735317e7d61fe67ab6746bf4c0'
      and row.sourceCollision==7 and row.role=='crystaldust_complete_red_house_bed'
      and row.x>=0 and row.x<=1 and row.y>=5 and row.y<=7 and row.frontY==128
    local celadonBed=coords and row.furniture=='celadon_mansion_bed'
      and(row.game=='gold'or row.game=='silver'or row.game=='crystal')
      and row.map=='CELADON_MANSION_2F'and row.tileset=='TILESET_MANSION'
      and row.id==20 and row.quadrant==0 and row.anchorX==0 and row.anchorY==6
      and row.sourceHash=='3de9891e182a5340ff15d420f5383fdde549c73df43b59d672ca52da02da00fc'
      and row.sourceCollision==7 and row.role=='crystaldust_complete_celadon_mansion_bed'
      and row.footX==0 and row.footY==7 and row.footId==20 and row.footQuadrant==2
      and row.footHash=='76fb1ccc1b4a6b279f94bfdbf3d736034a1c500a9ceb8449f08eed6f79a3903f'
      and row.x>=0 and row.x<=1 and row.y>=6 and row.y<=7 and row.frontY==128
    local shipGames=shipBedAnchors[row.game]
    local shipMap=shipGames and shipGames[row.map]
    local shipSource=shipMap and shipMap[tostring(row.anchorX)..':'..tostring(row.anchorY)]
    local shipBed=coords and row.furniture=='ship_bed'and shipSource
      and row.tileset=='TILESET_LIGHTHOUSE'and row.sourceCollision==7
      and row.role=='crystaldust_complete_native_ship_bed'
      and row.id==shipSource.id and row.quadrant==shipSource.quadrant and row.sourceHash==shipSource.sourceHash
      and row.frontY==shipSource.frontY and row.footX==shipSource.footX and row.footY==shipSource.footY
      and row.footId==shipSource.footId and row.footQuadrant==shipSource.footQuadrant and row.footHash==shipSource.footHash
      and row.x>=row.anchorX-1 and row.x<=row.anchorX and row.y>=row.anchorY and row.y<=row.anchorY+1
    local unionUpper=(row.anchorX==7 and row.anchorY==19 and row.map=='UNION_CAVE_B1F')
      or(row.anchorX==9 and row.anchorY==11 and row.map=='SLOWPOKE_WELL_B2F')
    local unionFloor=(row.anchorX==3 and row.anchorY==33 and row.map=='UNION_CAVE_B1F')
      or(row.anchorX==5 and row.anchorY==3 and row.map=='UNION_CAVE_B2F')
      or(row.anchorX==17 and row.anchorY==15 and row.map=='SLOWPOKE_WELL_B1F')
    local unionLadder=coords and row.furniture=='union_cave_ladder'
      and(row.game=='gold'or row.game=='silver'or row.game=='crystal')
      and row.tileset=='TILESET_CAVE'and(unionUpper or unionFloor)
      and row.id==(unionUpper and 20 or 27)and row.quadrant==3 and row.sourceCollision==114
      and row.sourceHash==(unionUpper and'525cbc4519b754336ed3ac102cc6523246523def55a9fb5739e29b9fadfdb103'
        or'5df7a0f817f557f6f6173b5dde2e21ca91d7e3661477ad1042d7abd093305758')
      and row.upperX==row.anchorX and row.upperY==row.anchorY-1 and row.upperId==row.id and row.upperQuadrant==1
      and row.upperHash==(unionUpper and'9bd2df64df770d82c85fa1539199ff530962ccb1869ced60e2f520f4607d59de'
        or'48c0a551f12607b1c1d59c1c8ab67046e07d45c9a18a93da2931d87d6b4aef8f')
      and row.upperCollision==(unionUpper and 178 or 0)
      and row.role=='crystaldust_complete_union_cave_ladder'
      and row.x==row.anchorX and row.y>=row.anchorY-1 and row.y<=row.anchorY
      and row.frontY==(row.anchorY+1)*16
    local kurtBench=coords and row.furniture=='kurt_workbench'
      and(row.game=='gold'or row.game=='silver'or row.game=='crystal')
      and row.map=='KURTS_HOUSE'and row.tileset=='TILESET_TRADITIONAL_HOUSE'
      and row.id==49 and row.quadrant==2 and row.anchorX==12 and row.anchorY==1
      and row.sourceHash=='b9295a913782f9438c63c5f146202a3b262bc43a49fe338c068b9767d3ee220b'
      and row.sourceCollision==7 and row.role=='crystaldust_complete_kurt_workbench'
      and row.x>=12 and row.x<=15 and row.y>=-1 and row.y<=4 and row.frontY==(row.y<=2 and 48 or 80)
    local azaleaTree=coords and row.furniture=='azalea_gym_tree'
      and(row.game=='gold'or row.game=='silver'or row.game=='crystal')
      and row.map=='AZALEA_GYM'and row.tileset=='TILESET_ELITE_FOUR_ROOM'
      and row.id==33 and row.quadrant==0 and row.anchorX==4 and row.anchorY==6
      and row.sourceHash==azaleaTreeHashes[1]and row.sourceCollision==7
      and row.role=='azalea_gym_center_tree_north16'
      and row.x>=4 and row.x<=5 and row.y>=5 and row.y<=6 and row.frontY==108
      and type(ctx.treeFrames)=='function'and type(ctx.treePhase)=='function'
    local counterSource=departmentCounterSources[row.game]and departmentCounterSources[row.game][row.map]
    local counterPiece=coords and counterSource and counterSource.pieces[row.x..':'..row.y]
    local departmentCounter=counterPiece and row.furniture=='department_counter'
      and row.tileset=='TILESET_MART'and row.anchorX==counterSource.anchorX and row.anchorY==counterSource.anchorY
      and row.id==counterSource.id and row.quadrant==counterSource.quadrant
      and row.sourceHash==counterSource.sourceHash and row.sourceCollision==counterSource.sourceCollision
      and row.role=='crystaldust_complete_department_counter'and row.frontY==counterPiece.frontY
      and row.asset==counterPiece.asset and row.assetFileHash==counterPiece.hash
    local checked={};for k,v in pairs(row)do checked[k]=v end
    checked.x,checked.y=row.anchorX,row.anchorY
    assert((bed or pc or carpet or shrine or lighthouseBed or lighthouseTable or linkMachine or battleMachine or upperPC or redBed or shipBed or celadonBed or mrPokemonPC or unionLadder or kurtBench or azaleaTree or departmentCounter)and row.style=='gen3'and row.kind=='third_party'
      and row.sourceFiles and type(row.assetFileHash)=='string'and #row.assetFileHash==64
      and not(row.base or row.donor or row.parts or row.canopy or row.animated or row.foreground or row.occludes)
      and not(row.side or row.sourceX or row.sourceY or row.animation or row.frames or row.assetFrames or row.artOverlay or row.overMask)
      and ctx.validate(checked),'Invalid reviewed furniture foreground')
    local games=furniture[row.game]or{};furniture[row.game]=games
    local maps=games[row.map]or{rows={},anchors={},seen={}};games[row.map]=maps
    local key=row.furniture..':'..row.id..':'..row.x..':'..row.y
    assert(not maps.seen[key],'Duplicate furniture foreground cell');maps.seen[key]=true
    maps.rows[#maps.rows+1]=row
    -- Cache only the distinct32px source blocks of registered finite furniture.
    local anchorKey=math.floor(row.anchorY/2)..':'..math.floor(row.anchorX/2)
    if not maps.seen[anchorKey]then
      maps.seen[anchorKey]=true;maps.anchors[#maps.anchors+1]={x=row.anchorX,y=row.anchorY}
    end
    if shipBed or celadonBed then
      local footKey=math.floor(row.footY/2)..':'..math.floor(row.footX/2)
      if not maps.seen[footKey]then
        maps.seen[footKey]=true;maps.anchors[#maps.anchors+1]={x=row.footX,y=row.footY}
      end
    end
    if kurtBench then
      for _,guard in ipairs(kurtBenchCells)do
        local guardKey=math.floor(guard.y/2)..':'..math.floor(guard.x/2)
        if not maps.seen[guardKey]then
          maps.seen[guardKey]=true;maps.anchors[#maps.anchors+1]={x=guard.x,y=guard.y}
        end
      end
    end
    if departmentCounter then
      for _,guard in ipairs(counterSource.cells)do
        local key=math.floor(guard.y/2)..':'..math.floor(guard.x/2)
        if not maps.seen[key]then maps.seen[key]=true;maps.anchors[#maps.anchors+1]={x=guard.x,y=guard.y}end
      end
    end
    assert(#maps.anchors<=(row.map=='KURTS_HOUSE'and 5 or(departmentCounter and 6)or shipAnchorLimits[row.map]or 3),'Too many bounded furniture source blocks')
  end
  local self={}
  local function foregroundTexture(entry,phase)
    if not entry.treeTextures then return entry.texture end
    phase=phase or ctx.treePhase();assert(type(phase)=='number'and phase%1==0 and phase>=1 and phase<=4,'Invalid finite tree wind phase')
    return entry.treeTextures[phase]
  end
  function self:cells(game,def)
    if closed or not def then return nil end
    local list=groups[game]and groups[game][def.id]
    local treeList=trees[game]and trees[game][def.id]
    local furnitureList=furniture[game]and furniture[game][def.id]
    if(not list and not treeList and not furnitureList)or not ctx.active()then return nil end
    local rev=ctx.revision()
    if rev~=revision then cache={};revision=rev end
    local games=cache[game]or{};cache[game]=games
    local cached=games[def]
    if cached then
      local changed=false
      if furnitureList then
        changed=cached.width~=def.width or cached.height~=def.height or cached.tileset~=def.tileset
        for i,anchor in ipairs(furnitureList.anchors)do
          local bid=def.blocks[math.floor(anchor.y/2)*def.width+math.floor(anchor.x/2)+1]
          if cached.furnitureBlocks[i]~=bid then changed=true;break end
        end
      end
      if not changed then return cached end
    end
    local result={rows={},grid={},minY=0,width=def.width,height=def.height,tileset=def.tileset,furnitureBlocks={}};games[def]=result
    if furnitureList then for i,anchor in ipairs(furnitureList.anchors)do
      result.furnitureBlocks[i]=def.blocks[math.floor(anchor.y/2)*def.width+math.floor(anchor.x/2)+1]
    end end
    local counterChecked=false
    local function append(row,x,y,sourceY,canopy,isFurniture)
      if not ctx.enabled or ctx.enabled(row)then
      local ok,data,treeFrames=pcall(function()
        local sx,sy=isFurniture and row.anchorX or(row.sourceX or x),isFurniture and row.anchorY or(sourceY or row.sourceY or y)
        if row.side then
          assert(row.buildingX+row.buildingW<=def.width*2 and row.buildingY+row.buildingH<=def.height*2,
            'Decorative building footprint lies outside source map')
          sx=math.max(0,math.min(def.width*2-1,row.x))
          assert(row.sourceX==sx,'Decorative side anchor changed')
        elseif row.sourceX~=nil then
          assert(row.sourceX==math.max(0,math.min(def.width*2-1,x)),
            'Upper decoration source anchor changed')
        end
        if row.sourceY~=nil then
          assert(row.buildingX+row.buildingW<=def.width*2 and row.buildingY+row.buildingH<=def.height*2,
            'North-edge building footprint lies outside source map')
        end
        assert(row.tileset==def.tileset and sx>=0 and sy>=0
          and sx<def.width*2 and sy<def.height*2,'Decoration lies outside checked source map')
        if canopy then assert(y==sy-1 and sy+1<def.height*2,'Canopy must sit one cell above its two-cell tree')end
        local bid=def.blocks[math.floor(sy/2)*def.width+math.floor(sx/2)+1]
        assert(bid==row.id and row.quadrant==sy%2*2+sx%2,'Decoration source position changed')
        local source,why=ctx.donor:cell({game=game,tileset=row.tileset,id=row.id,
          quadrant=row.quadrant,hash=row.sourceHash,hashOnly=true,map=def,
          monochrome=true,sourceFiles=row.sourceFiles})
        assert(source,why or'Roof source fingerprint changed')
        if isFurniture and row.furniture=='department_counter'then
          assert(def.width==8 and def.height==4,'Department counter source room bounds changed')
          if not counterChecked then
            local spec=departmentCounterSources[game][def.id]
            for _,guard in ipairs(spec.cells)do
              local bid=def.blocks[math.floor(guard.y/2)*def.width+math.floor(guard.x/2)+1]
              assert(bid==guard.id,'Complete department counter source footprint changed')
              local part,why=ctx.donor:cell({game=game,tileset=row.tileset,id=guard.id,quadrant=guard.quadrant,
                hash=guard.hash,hashOnly=true,map=def,monochrome=true,sourceFiles=row.sourceFiles})
              assert(part,why or'Complete department counter source glyph changed')
            end
            counterChecked=true
          end
        end
        if isFurniture and row.furniture=='azalea_gym_tree'then
          assert(def.width==5 and def.height==8,'Azalea Gym source bounds changed')
          for q=0,3 do
            local piece,pieceWhy=ctx.donor:cell({game=game,tileset=row.tileset,id=33,quadrant=q,
              hash=azaleaTreeHashes[q+1],hashOnly=true,map=def,monochrome=true,sourceFiles=row.sourceFiles})
            assert(piece,pieceWhy or'Azalea Gym source tree glyph changed')
          end
          local frames=ctx.treeFrames(row);assert(type(frames)=='table'and #frames==4,'Finite tree requires four complete wind frames')
          for _,frame in ipairs(frames)do
            local w,h=frame:getDimensions();assert(w==16 and h==16,'Finite tree piece must retain native16px quadrants')
          end
          return frames[1],frames
        end
        if isFurniture and row.furniture=='union_cave_ladder'then
          local upperBid=def.blocks[math.floor(row.upperY/2)*def.width+math.floor(row.upperX/2)+1]
          assert(upperBid==row.upperId,'Complete Union ladder upper source position changed')
          local upper,upperWhy=ctx.donor:cell({game=game,tileset=row.tileset,id=row.upperId,
            quadrant=row.upperQuadrant,hash=row.upperHash,hashOnly=true,map=def,
            monochrome=true,sourceFiles=row.sourceFiles})
          assert(upper,upperWhy or'Complete Union ladder upper source fingerprint changed')
        end
        if isFurniture and row.furniture=='kurt_workbench'then
          assert(def.width==8 and def.height==4,'Kurt workshop source room bounds changed')
          for _,guard in ipairs(kurtBenchCells)do
            local guardBid=def.blocks[math.floor(guard.y/2)*def.width+math.floor(guard.x/2)+1]
            assert(guardBid==guard.id,'Complete Kurt workbench source L changed')
            local part,partWhy=ctx.donor:cell({game=game,tileset=row.tileset,id=guard.id,
              quadrant=guard.quadrant,hash=guard.hash,hashOnly=true,map=def,
              monochrome=true,sourceFiles=row.sourceFiles})
            assert(part,partWhy or'Complete Kurt workbench source fingerprint changed')
          end
        end
        if isFurniture and(row.furniture=='ship_bed'or row.furniture=='celadon_mansion_bed')then
          local footBid=def.blocks[math.floor(row.footY/2)*def.width+math.floor(row.footX/2)+1]
          assert(footBid==row.footId and row.footQuadrant==row.footY%2*2+row.footX%2,
            'Complete native bed source foot changed')
          local foot,footWhy=ctx.donor:cell({game=game,tileset=row.tileset,id=row.footId,
            quadrant=row.footQuadrant,hash=row.footHash,hashOnly=true,map=def,
            monochrome=true,sourceFiles=row.sourceFiles})
          assert(foot,footWhy or'Complete native bed foot fingerprint changed')
        end

        if row.parts then
          local piece,why=ctx.compose(row)
          assert(piece,why or'Decorative native composition unavailable')
          return piece.under
        end
        local image=ctx.original(canopy and row.canopy.asset or row.asset,canopy and row.canopy.hash or row.assetFileHash)
        if isFurniture then
          assert(image and image.getDimensions,'Furniture foreground image is unavailable')
          local w,h=image:getDimensions()
          assert(w==16 and h==16,'Furniture foreground must be exactly16x16')
          if row.furniture=='union_cave_ladder'or row.furniture=='kurt_workbench'then
            local ladder=row.furniture=='union_cave_ladder'
            local left=ladder and row.anchorX*16+1 or 192
            local right=ladder and row.anchorX*16+14 or 256
            local top=ladder and(row.anchorY-1)*16+2 or -10
            local bottom=ladder and(row.anchorY+1)*16 or 80
            for py=0,15 do for px=0,15 do
              local _,_,_,alpha=image:getPixel(px,py)
              local wx,wy=x*16+px,y*16+py
              assert(alpha==0 or(wx>=left and wx<right and wy>=top and wy<bottom),
                'Complete native ladder or workbench escapes its reviewed source envelope')
            end end
          end
          if row.furniture=='bed'then
            -- The intact24x34 bed starts two pixels above its original32px
            -- source block. Keep every pixel beyond that envelope transparent.
            for py=0,15 do for px=0,15 do
              local _,_,_,alpha=image:getPixel(px,py)
              assert(alpha==0 or(x*16+px<24 and y*16+py>=62 and y*16+py<96),
                'Furniture foreground escapes its native bed silhouette envelope')
            end end
          end
          if row.furniture=='link_trade_apparatus'or row.furniture=='link_battle_apparatus'then
            -- Complete native62x37 apparatus/chairs; seatedfeet76 stay in front.
            for py=0,15 do for px=0,15 do
              local _,_,_,alpha=image:getPixel(px,py)
              local wx,wy=x*16+px,y*16+py
              assert(alpha==0 or(wx>=49 and wx<111 and wy>=43 and wy<80),
                'Link apparatus foreground escapes its complete native62x37 envelope')
            end end
          end
          if row.furniture=='celadon_mansion_bed'then
            assert(def.width==4 and def.height==5,'Celadon bedroom source bounds changed')
            for py=0,15 do for px=0,15 do
              local _,_,_,alpha=image:getPixel(px,py)
              local wx,wy=x*16+px,y*16+py
              assert(alpha==0 or(wx>=0 and wx<20 and wy>=99 and wy<128),
                'Celadon bed foreground escapes its complete native20x29 envelope')
            end end
          end
          if row.furniture=='pokecenter_upper_pc'or row.furniture=='red_house_bed'or row.furniture=='ship_bed'then
            local pc,red=row.furniture=='pokecenter_upper_pc',row.furniture=='red_house_bed'
            local left=pc and 32 or(red and 0 or row.anchorX*16-4)
            local right=pc and 48 or(red and 24 or row.anchorX*16+16)
            local top=pc and 16 or(red and 94 or row.anchorY*16+3)
            local bottom=pc and 48 or(red and 128 or(row.anchorY+2)*16)
            for py=0,15 do for px=0,15 do
              local _,_,_,alpha=image:getPixel(px,py)
              local wx,wy=x*16+px,y*16+py
              assert(alpha==0 or(wx>=left and wx<right and wy>=top and wy<bottom),
                'Complete native furniture escapes its source-specific envelope')
            end end
          end
          if row.furniture=='lighthouse_bed'or row.furniture=='lighthouse_table'then
            local bed=row.furniture=='lighthouse_bed'
            local left,right,top,bottom=bed and 172 or 96,bed and 192 or 128,bed and 99 or 141,bed and 128 or 192
            for py=0,15 do for px=0,15 do
              local _,_,_,alpha=image:getPixel(px,py)
              local wx,wy=x*16+px,y*16+py
              assert(alpha==0 or(wx>=left and wx<right and wy>=top and wy<bottom),
                'Lighthouse furniture escapes its complete native silhouette envelope')
            end end
          end
          if row.furniture=='mr_pokemon_pc'then
            for py=0,15 do for px=0,15 do
              local _,_,_,alpha=image:getPixel(px,py)
              local wx,wy=x*16+px,y*16+py
              assert(alpha==0 or(wx>=96 and wx<128 and wy>=54 and wy<80),
                'Mr Pokemon workstation escapes its complete native32x26 envelope')
            end end
          end
          if row.furniture=='ilex_shrine'then
            -- Complete native24x34 altar, centered at the original Ilex source.
            for py=0,15 do for px=0,15 do
              local _,_,_,alpha=image:getPixel(px,py)
              local wx,wy=x*16+px,y*16+py
              assert(alpha==0 or(wx>=124 and wx<148 and wy>=350 and wy<384),
                'Shrine foreground escapes its native24x34 silhouette envelope')
            end end
          end
        end
        return image
      end)
      if ok and data then
        -- Native compositions can produce fresh ImageData after an option
        -- revision. Keep one GPU texture per reviewed row, not per rebuild.
        local textureKey=row.parts and row or data
        local texture=textures[textureKey]
        if texture and row.parts then texture:replacePixels(data)end
        if not texture then texture=G.newImage(data);texture:setFilter('nearest','nearest');textures[textureKey]=texture end
        local entry={x=x,y=y,data=data,texture=texture,role=canopy and'dense_conifer_canopy'or row.role,
          treeCanopy=canopy or nil,sourceY=canopy and sourceY or nil,
          groundOnly=isFurniture and row.furniture=='carpet'or nil,
          outside=x<0 or y<0 or x>=def.width*2 or y>=def.height*2,
          frontY=isFurniture and row.frontY or(canopy and(sourceY+2)*16 or(row.side and(row.buildingY+row.buildingH)*16 or nil))}
        if treeFrames then
          result.hasTreeFrames=true
          entry.treeTextures={}
          for i,frame in ipairs(treeFrames)do
            local t=textures[frame]
            if not t then t=G.newImage(frame);t:setFilter('nearest','nearest');textures[frame]=t end
            entry.treeTextures[i]=t
          end
        end
        result.minY=math.min(result.minY,y)
        -- Adjacent native buildings may share a decorative cell. Retain their
        -- draw order and separate physical front/behind boundaries. This
        -- linked stack is constructed once, never rebuilt in map/actor draws.
        local key=y*65536+x
        local previous=result.grid[key]
        if(canopy or isFurniture)and previous then
          -- Ground-only rug borders stay below finite-front furniture/canopies.
          -- Existing building sides win ties and overhead roofs stay above.
          local before,current=nil,previous
          while current and not entry.groundOnly
            and(current.groundOnly or(current.frontY and current.frontY<entry.frontY))do before=current;current=current.next end
          entry.next=current
          if before then before.next=entry else result.grid[key]=entry end
          local depth=0;current=result.grid[key]
          while current do depth=depth+1;current=current.next end
          assert(depth<=4,'More than four overlapping decorative entries')
        elseif previous then
          local depth=1
          while previous.next do previous=previous.next;depth=depth+1 end
          assert(depth<4,'More than four overlapping decorative entries')
          previous.next=entry
        else result.grid[key]=entry end
      elseif ctx.warn then ctx.warn('TileShift skipped '..(isFurniture and'furniture foreground'or'roof overhang')..': '..tostring(data))end
      end
    end
    for i=1,list and #list or 0 do
      local row=list[i];append(row,row.x,row.y)
    end
    if treeList then
      -- Expand the actual source block grid once per map/revision. Generic
      -- aliases retain their real source guards, including a y=-1 canopy.
      for index,bid in ipairs(def.blocks)do
        local aliases=treeList[bid]
        if aliases then for q=0,3 do
          local row=aliases[q]
          if row then
            local x=(index-1)%def.width*2+q%2
            local sy=math.floor((index-1)/def.width)*2+math.floor(q/2)
            append(row,x,sy-1,sy,true)
          end
        end end
      end
    end
    for _,row in ipairs(furnitureList and furnitureList.rows or{})do
      local bid=def.blocks[math.floor(row.anchorY/2)*def.width+math.floor(row.anchorX/2)+1]
      if bid==row.id then append(row,row.x,row.y,nil,nil,true)end
    end
    local roots={}
    for _,entry in pairs(result.grid)do
      local line=roots[entry.y]or{};roots[entry.y]=line;line[#line+1]=entry
    end
    for y,line in pairs(roots)do
      table.sort(line,function(a,b)return a.x<b.x end)
      local ordered={};result.rows[y]=ordered
      for _,entry in ipairs(line)do
        while entry do ordered[#ordered+1]=entry;entry=entry.next end
      end
    end
    return result
  end
  function self:map(world,def,ox,oy,s,edgeMode)
    if not world or world.daytime=='DARK'then return end
    local cells=self:cells(ctx.version(),def);if not cells then return end
    local cam=world.camera;s=s or 1;ox,oy=ox or 0,oy or 0
    -- Sample once for the whole32px sprite and reuse it for actor overlays.
    if cells.hasTreeFrames then cells.treePhase=ctx.treePhase()end
    local cx,cy=cam and cam.x or 0,cam and cam.y or 0
    local first=math.max(cells.minY,math.floor((cy-oy)/16)-1)
    local last=math.min(def.height*2-1,math.floor((cy-oy+(world.viewH or 144))/16))
    if edgeMode=='onlyBorder'then
      if cells.minY~=-1 then return end
      first,last=-1,-1
    end
    G.push('all');G.setShader();G.setColor(1,1,1,1)
    for y=first,last do
      local line=cells.rows[y]
      for i=1,line and #line or 0 do
        local e=line[i]
        local x=e.x*16+ox-cx
        if(edgeMode~='withoutBorder'or y>=0)and x+16>=0 and x<=(world.viewW or 160)then
          local dx,dy=math.floor(x*s),math.floor((y*16+oy-cy)*s)
          G.draw(foregroundTexture(e,cells.treePhase),dx,dy,0,s,s)
          if ctx.markTrueColor then ctx.markTrueColor(dx,dy,16*s,16*s)end
        end
      end
    end
    G.pop()
  end
  function self:borders(world,s)
    if closed or not ctx.active()or not next(trees)or not world or not world.maps or world.daytime=='DARK'then return end
    -- Neighbors' canvases are drawn before the current map. Replay only their
    -- one outside canopy row afterward, so it cannot disappear at a connection.
    for _,neighbor in ipairs(world.neighbors or{})do
      local def=world.maps[neighbor.id]
      if def then self:map(world,def,neighbor.ox,neighbor.oy,s,'onlyBorder')end
    end
  end
  function self:actor(map,entity,ox,oy,s,moved,now,world,originX,originY,borderOnly,actorOriginX,actorOriginY)
    if closed or not ctx.active()or not map or not entity or not world or world.daytime=='DARK'then return end
    local def=map.def or map
    local cells=self:cells(ctx.version(),def)
    local primary=originX==nil
    originX,originY=originX or 0,originY or 0
    actorOriginX,actorOriginY=actorOriginX or 0,actorOriginY or 0
    local sprite=entity.sprite
    local fw,fh=sprite and sprite.frameWidth or 16,sprite and sprite.frameHeight or 16
    local ax,ay=sprite and sprite.anchorX or fw/2,sprite and sprite.anchorY or fh
    local x0=math.floor(entity.px+actorOriginX+8-ax)-originX
    local y0=math.floor(entity.py+actorOriginY+(entity.spriteYOffset or 0)+12-ay)-originY
    local x1,y1=x0+fw,y0+fh;s=s or 1;ox,oy=ox or 0,oy or 0
    if cells then for ty=math.floor(y0/16),math.floor((y1-1)/16)do
      for tx=math.floor(x0/16),math.floor((x1-1)/16)do
        local entry=cells.grid[ty*65536+tx]
        if entry then
          local xx,yy=math.max(x0,tx*16),math.max(y0,ty*16)
          local w,h=math.min(x1,tx*16+16)-xx,math.min(y1,ty*16+16)-yy
          if not quad then quad=G.newQuad(0,0,16,16,16,16)end
          quad:setViewport(xx-tx*16,yy-ty*16,w,h,16,16)
          while entry do
            if not entry.groundOnly and(not borderOnly or entry.outside)
              and(not entry.frontY or entity.py+actorOriginY+12<entry.frontY+originY)then
              G.push('all');G.setShader();G.setColor(1,1,1,1)
              G.draw(foregroundTexture(entry,cells.treePhase),quad,math.floor(ox+(xx+originX)*s),math.floor(oy+(yy+originY)*s),0,s,s);G.pop()
              if ctx.markTrueColor then ctx.markTrueColor(math.floor(ox+(xx+originX)*s),math.floor(oy+(yy+originY)*s),w*s,h*s)end
            end
            entry=entry.next
          end
        end
      end
    end end
    if primary and(staticBorders or next(trees))and world.neighbors then
      for _,neighbor in ipairs(world.neighbors)do
        -- Gen1 neighbors retain loaded native Map objects; Gen2 keeps their
        -- definitions by ID. Only cached decorations outside that source map
        -- can cross over an actor in the current map.
        local neighborDef=neighbor.map and(neighbor.map.def or neighbor.map)
          or(world.maps and world.maps[neighbor.id])
        if neighborDef then
          local ownMap=neighbor.ox==actorOriginX and neighbor.oy==actorOriginY
          self:actor(neighborDef,entity,ox,oy,s,moved,now,world,neighbor.ox,neighbor.oy,not ownMap,actorOriginX,actorOriginY)
        end
      end
    end
  end
  function self:dispose()
    if closed then return end;closed=true;cache={}
    for _,texture in pairs(textures)do texture:release()end
    textures={};if quad and quad.release then quad:release()end
  end
  return self
end
return R
