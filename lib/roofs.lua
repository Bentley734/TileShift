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
    local checked={};for k,v in pairs(row)do checked[k]=v end
    checked.x,checked.y=row.anchorX,row.anchorY
    assert((bed or pc or carpet or shrine or lighthouseBed or lighthouseTable or linkMachine or battleMachine or upperPC or redBed or shipBed)and row.style=='gen3'and row.kind=='third_party'
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
    if shipBed then
      local footKey=math.floor(row.footY/2)..':'..math.floor(row.footX/2)
      if not maps.seen[footKey]then
        maps.seen[footKey]=true;maps.anchors[#maps.anchors+1]={x=row.footX,y=row.footY}
      end
    end
    assert(#maps.anchors<=(shipAnchorLimits[row.map]or 3),'Too many bounded furniture source blocks')
  end
  local self={}
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
    local function append(row,x,y,sourceY,canopy,isFurniture)
      if not ctx.enabled or ctx.enabled(row)then
      local ok,data=pcall(function()
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
        if isFurniture and row.furniture=='ship_bed'then
          local footBid=def.blocks[math.floor(row.footY/2)*def.width+math.floor(row.footX/2)+1]
          assert(footBid==row.footId and row.footQuadrant==row.footY%2*2+row.footX%2,
            'Complete ship bed source foot changed')
          local foot,footWhy=ctx.donor:cell({game=game,tileset=row.tileset,id=row.footId,
            quadrant=row.footQuadrant,hash=row.footHash,hashOnly=true,map=def,
            monochrome=true,sourceFiles=row.sourceFiles})
          assert(foot,footWhy or'Complete ship bed foot fingerprint changed')
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
          G.draw(e.texture,dx,dy,0,s,s)
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
              G.draw(entry.texture,quad,math.floor(ox+(xx+originX)*s),math.floor(oy+(yy+originY)*s),0,s,s);G.pop()
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
