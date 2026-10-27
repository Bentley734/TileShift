local root=assert(arg[1])
local unpack=table.unpack or unpack
local F=assert(loadfile(root..'/lib/flora.lua'))()
local C=assert(loadfile(root..'/lib/flora_catalog.lua'))()
local count=0
local function eq(a,b,message)count=count+1;assert(a==b,(message or 'mismatch')..': '..tostring(a)..' ~= '..tostring(b))end
local function new(seed)return F.new({catalog=C,seed=seed})end
local f=new(42)
for _,category in ipairs({'trees','flowers','grass'})do
  local choices=f:choices(category)
  eq(choices[1][2],'default');eq(choices[2][2],'random');eq(choices[3][2],'mixed')
  local seen={}
  for _,entry in ipairs(C[category])do
    eq(seen[entry.id],nil,'no duplicate stable IDs in category');seen[entry.id]=true
    if entry.sheet then assert(entry.row>=1 and entry.row<=9 and entry.column>=1 and entry.column<=13)
    else assert(entry.asset or entry.donor) end
  end
  eq(f:select(category,'random'),true)
  eq(f:entry(category,'MAP:A'),f:entry(category,'MAP:B'),'random selects one design for the whole session')
  local same=new(42);same:select(category,'random')
  eq(f:entry(category,'MAP:A').id,same:entry(category,'MAP:B').id,'seed repeats random session choice')
  eq(f:select(category,'mixed'),true)
  eq(f:entry(category,'MAP:A'),f:entry(category,'MAP:A'),'mixed is stable on revisit')
  local other=new(42);other:select(category,'mixed')
  eq(f:entry(category,'MAP:A').id,other:entry(category,'MAP:A').id,'same seed restores same map')
  local used={}
  for i=1,100 do used[f:entry(category,'MAP:'..i).id]=true end
  local n=0 for _ in pairs(used)do n=n+1 end assert(n>1,'mixed must vary within a map')
end
eq(f:select('trees','bogus'),nil);eq(f:select('bogus','mixed'),nil)
local row={game='red',style='gen3',tileset='OVERWORLD',id=77,quadrant=1,role='boundary_tree',sourceHash='guard'}
local special={id=77,quadrant=0,role='headbutt_small_tree'}
local def={id='PALLET_TOWN',width=2,height=1,blocks={77,77}}
local output=f:rows({row,special},'red',def)
eq(#output,4,'one generic row, two independently scoped occurrences, unchanged special tree')
eq(output[3].x,1);eq(output[3].y,0);eq(output[4].x,3);eq(output[4].y,0)
eq(output[3].map,'PALLET_TOWN');eq(output[3].sourceHash,'guard')
eq(output[2],special,'Headbutt trees never silently become ordinary boundary trees')
local ground={id=77,quadrant=2,role='open_grassy_ground'}
local scoped={id=77,quadrant=0,x=0,y=0,map='PALLET_TOWN',role='headbutt_small_tree'}
local ordered=f:rows({row,ground,scoped},'red',def)
eq(ordered[2],ground,'neighbouring grass completes before any mixed position clone')
eq(ordered[#ordered],scoped,'original positional overrides retain final precedence')
local winner={id=77,quadrant=1,map='PALLET_TOWN',role='open_grassy_ground'}
eq(#f:rows({row,winner},'red',def),2,'superseded generic trees cannot paint over map-specific grass')
for _,entry in ipairs(C.water)do assert(entry.animated and entry.optionValue>=6)end
-- The four quadrants of an odd-aligned2x2 tree share one Mixed choice.
f:select('big_trees','mixed')
local whole={}
for q=0,3 do whole[q+1]={id=77,quadrant=(1+math.floor(q/2))%2*2+(1+q%2)%2,
 x=1+q%2,y=1+math.floor(q/2),map='FOREST',role='forest_whole_broadleaf_tree_'..q}end
local treeRows=f:rows(whole,'red',{id='FOREST',width=4,height=4,blocks={}})
for i=2,4 do eq(treeRows[i]._floraEntry.id,treeRows[1]._floraEntry.id,'one complete tree cannot mix quadrant designs')end
local ilex={}
for q,name in ipairs({'northwest','northeast','southwest','southeast'})do
 ilex[q]={id=5,quadrant=q-1,x=(q-1)%2,y=math.floor((q-1)/2),map='ILEX_FOREST',role='dense_forest_tree_'..name}
end
local ilexRows=f:rows(ilex,'gold',{id='ILEX_FOREST',width=1,height=1,blocks={5}})
for i=2,4 do eq(ilexRows[i]._floraEntry.id,ilexRows[1]._floraEntry.id,'Ilex Big Trees share one whole design') end
local cut={id=95,quadrant=0,role='cuttable_small_tree'}
f:select('cut_trees','native-cut-emerald')
eq(f:rows({cut,special},'crystal',def)[1]._floraEntry.donor.game,'emerald')
eq(f:rows({cut,special},'crystal',def)[2],special,'changing Cut artwork leaves Headbutt artwork alone')
eq(row.map,nil,'source mapping not mutated');eq(row._floraEntry,nil)
eq(def.blocks[1],77,'original map IDs unchanged')
f:select('trees','default');eq(f:rows({row},'red',def)[1],row,'default keeps exact reviewed row')
-- Native sheet decoding validates dimensions, caches the source and preserves
-- alpha foregrounds instead of covering actors with the ground rectangle.
local reads,baseReads=0,0
local function image(w,h,solid)
  local p={};local out={}
  function out:getDimensions()return w,h end
  function out:getPixel(x,y)
    local v=p[y*w+x];if v then return unpack(v) end
    if solid then return .2,.5,.1,1 end
    return 0,0,0,0
  end
  function out:setPixel(x,y,...)p[y*w+x]={...}end
  function out:paste(source,dx,dy,sx,sy,sw,sh)
    for y=0,sh-1 do for x=0,sw-1 do self:setPixel(dx+x,dy+y,source:getPixel(sx+x,sy+y))end end
  end
  return out
end
local renderer=F.new({catalog=C,seed=42,newImageData=image,
  sheet=function(path,expected)
    reads=reads+1;eq(#expected,64);assert(path:match('%.jpg$'))
    return {getDimensions=function()return 2400,1792 end,
      getPixel=function(_,x,y)if x<35 then return .4,.7,.6,1 end return .2,.5,.1,1 end}
  end,
  base=function()baseReads=baseReads+1;return image(16,16,true)end})
local entry=C.grass[1]
local piece=renderer:piece({_floraEntry=entry,_floraCategory='grass'})
eq(piece.under:getDimensions(),16);eq(piece.foreground:getDimensions(),16)
local _,_,_,alpha=piece.foreground:getPixel(0,0);eq(alpha,0,'foreground has no opaque ground above feet')
renderer:piece({_floraEntry=entry,_floraCategory='grass'})
eq(reads,1,'sheet decoded once');eq(baseReads,1,'native lawn decoded once')
-- Wind must preserve source pixels, anchor roots, and animate the foreground
-- with the very same grass frame used below an actor.
local sprite=image(16,16)
for y=3,14 do for x=5,10 do sprite:setPixel(x,y,.1+x/30,.8,y/30,1) end end
local wind=F.new({catalog=C,newImageData=image,
 sheet=function()return sprite end,base=function()return image(16,16,true)end})
local own={id='wind-test',asset='fixture.png',hash=string.rep('a',64),size=16}
for _,category in ipairs({'grass','flowers','trees','cut_trees'})do
 local first,sequence=wind:piece({_floraEntry=own,_floraCategory=category})
 eq(#sequence.frames,4)
 for i,frame in ipairs(sequence.frames)do
  for x=0,15 do
   local r,g,b,a=frame.under:getPixel(x,14)
   local r0,g0,b0,a0=first.under:getPixel(x,14)
   eq(r,r0,'roots remain anchored');eq(g,g0);eq(b,b0);eq(a,a0)
  end
 end
 local r=sequence.frames[2].under:getPixel(6,3)
 eq(r,select(1,sprite:getPixel(5,3)),'canopy or blade tips move exactly one pixel')
 if category=='grass' then
  local r,g,b,a=sequence.frames[2].foreground:getPixel(6,8)
  local r0,g0,b0,a0=sprite:getPixel(5,8)
  eq(r,r0);eq(g,g0);eq(b,b0);eq(a,a0,'grass foreground follows the blade animation')
 end
end
-- Mixed water shares one selection across connected surface/bank quadrants,
-- while isolated ponds can vary. Dry blocks must never join two ponds.
local water=new(42);water:select('water','mixed')
local waterRows={}
for q=0,3 do waterRows[#waterRows+1]={id=1,quadrant=q,role='freshwater_pond_interior'} end
local blocks={}
for i=1,20 do blocks[i]=i%2==1 and 1 or 2 end
local mixed=water:rows(waterRows,'gold',{id='PONDS',width=20,height=1,blocks=blocks})
local pondChoices,used={},{}
for _,row in ipairs(mixed)do if row.x then
 local pond=math.floor(row.x/4)
 if pondChoices[pond] then eq(row._floraEntry.id,pondChoices[pond],'whole pond shares one water style')
 else pondChoices[pond]=row._floraEntry.id;used[row._floraEntry.id]=true end
end end
local different=0;for _ in pairs(used)do different=different+1 end
assert(different>1,'isolated water bodies should offer style variation')
-- Speed changes only timing, never source frames, choices or native recipes.
local sequence={frames={{under='first'},{under='second'}},period=.2,offset=.1,bank='fixture'}
local grassRow={role='tall_grass'}
wind:speed('grass',.5)
local slow=wind:timing(grassRow,sequence);eq(slow.period,.4);eq(slow.offset,.2);eq(slow.frames,sequence.frames)
wind:speed('grass',2);eq(wind:timing(grassRow,sequence).period,.1)
wind:speed('grass',0)
local off=wind:timing(grassRow,sequence);eq(#off.frames,1);eq(off.frames[1],sequence.frames[1]);eq(off.offset,0)
eq(sequence.period,.2);eq(#sequence.frames,2,'Off must not mutate the native sequence')
wind:speed('trees',.5)
eq(wind:timing({role='forest_whole_broadleaf_tree_3'},sequence).period,.4)
eq(wind:timing({role='cuttable_small_tree'},sequence).period,.4)
eq(wind:timing({role='headbutt_small_tree'},sequence),sequence,'unrelated native events keep native timing')
-- Mixed areas include edge/corner contacts and preserve dry scoped breaks.
for _,case in ipairs({{'trees','boundary_tree'},{'flowers','decorative_flower_northwest'},
 {'grass','tall_grass'},{'water','freshwater_pond_interior'}})do
 local f=new(42);f:select(case[1],'mixed')
 local rows={}
 for _,xy in ipairs({{0,0},{1,0},{2,1},{6,0},{6,1}})do
  rows[#rows+1]={id=1,quadrant=xy[2]%2*2+xy[1]%2,x=xy[1],y=xy[2],map='PATCHES',role=case[2]}
 end
 local result=f:rows(rows,'red',{id='PATCHES',width=4,height=1,blocks={1,1,1,1}})
 eq(result[1]._floraEntry.id,result[2]._floraEntry.id,'edge-touching tiles share one style')
 eq(result[2]._floraEntry.id,result[3]._floraEntry.id,'corner-touching tiles share one style')
 eq(result[4]._floraEntry.id,result[5]._floraEntry.id,'separate connected patch is internally consistent')
end
-- Opaque grass textures use native leaf-shaped alpha instead of hiding feet
-- behind a solid rectangle of green ground.
local mask=image(16,16)
for y=8,15 do for x=0,15 do if x%2==0 then mask:setPixel(x,y,1,1,1,1)end end end
local patterned=F.new({catalog=C,newImageData=image,base=function()return image(16,16,true)end,
 foreground=function()return mask end,
 sheet=function()return {getDimensions=function()return 2400,1792 end,getPixel=function()return .2,.6,.3,1 end}end})
local _,frames=patterned:piece({_floraEntry=C.grass[3],_floraCategory='grass',foreground={effect='fixture'}})
for _,frame in ipairs(frames.frames)do
 local visible,covered=0,0
 for y=8,15 do for x=0,15 do local _,_,_,a=frame.foreground:getPixel(x,y)
  if a==0 then visible=visible+1 else covered=covered+1 end
 end end
 eq(visible,64,'texture has transparent gaps between native leaf shapes');eq(covered,64)
end
print('flora selection checks: '..count)
