-- User-supplied generated artwork; printed sheet labels are not native tile IDs.
-- Stable IDs use sheet, row and column, including visibly different near-duplicates.
local C={sheets={
  natural={path='assets/user_flora/natural.jpg',hash='a58e3890072974c7854e6c013b89f8ce191ff7d6279271f855fea63bcf9f5496'},
  botanical={path='assets/user_flora/botanical.jpg',hash='688e4362c75aa1c99209ac1bba7bd4429b57babc17c7c67632eb7e8587c6c642'},
},trees={},big_trees={},cut_trees={
  {id='native-cut-firered',label='FIRE RED / LEAF GREEN',donor={game='firered',kind='field_object',tileset='ow',id=95,frame=0,
    hash='7db9e7ec5879e002bcf8c187313eb809ea5d5baf7fac863b8f51f2140f62843b',
    metaHash='b181a711bdf3d699466e97296d8b6e4a362e66d497ec37b71afa62ea37e2688b',
    rgbaHash='f78c1daf7f407870f4f69bb1da451384cedada68f57c666df0ea97138e4ccd18'}},
  {id='native-cut-emerald',label='EMERALD',donor={game='emerald',kind='field_object',tileset='ow',id=82,frame=0,
    hash='a9721e629a94ae0719dd3335077be311b4ad89a9b70f3ed48abfe0d5d27f71ed',
    metaHash='7f3583cd02bfdef90077368fc80e6cd76836a0b7f0851d76f6c0eea672ecf040',
    rgbaHash='3c819f922975d62243ed787e6c7e573bda7301366f0ccb3fefc0770f81a83c5d'}},
},flowers={},grass={},water={
  -- Keep v0.7.0 stored values6/7/8 so removing static options4/5 never
  -- silently changes an existing animated-water preference.
  {id='ripple-blue',label='RIPPLE BLUE',sheet='magiscarf',x=64,y=32,animated=true,optionValue=6},
  {id='ripple-teal',label='RIPPLE TEAL',sheet='magiscarf',x=64,y=96,animated=true,optionValue=7},
  {id='ripple-olive',label='RIPPLE OLIVE',sheet='magiscarf',x=64,y=160,animated=true,optionValue=8},
}}
local function add(category,sheet,row,columns)
  for _,column in ipairs(columns)do
    C[category][#C[category]+1]={id=sheet..'-'..row..'-'..column,
      label=(sheet=='natural' and 'N' or 'B')..' R'..row..' C'..column,
      sheet=sheet,row=row,column=column}
  end
end
local function range(a,b)local t={} for i=a,b do t[#t+1]=i end return t end
add('trees','natural',1,{1,2,3,4,11,12,13})
add('trees','natural',2,{5,6,7,8,9,13})
add('trees','natural',3,{1,11})
add('trees','natural',4,{1,2,9})
add('trees','natural',5,{8,9,10,11,12})
add('trees','natural',6,{13})
add('trees','natural',7,{1,2,3,4,5,6,7,12,13})
add('trees','natural',8,{1,2,3,4})
add('trees','botanical',1,range(1,13))
add('trees','botanical',2,range(1,13))
-- Berry shrubs are decorative tree choices, never berry-event replacements.
add('trees','natural',2,{10,11,12})
add('trees','natural',3,{2,3,4,5,6,7,8,9})
add('trees','botanical',5,range(1,13))
add('flowers','natural',1,{5,6,7,8})
add('flowers','natural',3,{10,13})
add('flowers','natural',4,{3,4,5,11,12,13})
add('flowers','natural',5,{1,2,3,4,5,6,7,13})
add('flowers','natural',6,range(1,8))
add('flowers','natural',9,{9})
add('flowers','botanical',6,range(1,13))
add('flowers','botanical',9,range(1,13))
-- Grasses only: no rocks, mushrooms, logs, cacti, crystals or water plants.
add('grass','natural',1,{10})
add('grass','natural',2,{1,2,3,4})
add('grass','natural',4,{6})
add('grass','natural',7,{10,11})
add('grass','natural',8,{7})
add('grass','natural',9,{1,12,13})
for _,entry in ipairs(C.trees)do
  local big,cut={},{}
  for k,v in pairs(entry)do big[k]=v;cut[k]=v end
  big.id='big-'..entry.id;big.size=32
  cut.id='cut-'..entry.id
  C.big_trees[#C.big_trees+1]=big
  C.cut_trees[#C.cut_trees+1]=cut
end
table.insert(C.big_trees,1,{id='johto-pine32',label='JOHTO PINE',size=32,
  asset='assets/original/flora/johto-pine32.png',hash='179937f5c631c898741fc97eb539948e655135901356d39878e5474e11a3ae6c'})
table.insert(C.big_trees,1,{id='johto-oak32',label='JOHTO OAK',size=32,
  asset='assets/original/flora/johto-oak32.png',hash='2c102ae76940fdeee6c32efb02d8a06700dab8ba79849db2264fce41c4acfc07'})
C.grass[#C.grass+1]={id='johto-meadow-grass',label='JOHTO MEADOW',size=16,
  asset='assets/original/flora/johto-meadow-grass.png',hash='eaa0d6e01331e9e56c200fd9bcd398253bc0d5996819a1cd328751f5247ee394'}
C.grass[#C.grass+1]={id='johto-clover-grass',label='JOHTO CLOVER',size=16,
  asset='assets/original/flora/johto-clover-grass.png',hash='7e0591bcfd722b248c3b539e7f92061ffff01f7a007673ffb1b271313efaa733'}
C.flowers[#C.flowers+1]={id='johto-red-flowers',label='JOHTO RED BLOOMS',size=16,
  asset='assets/original/flora/johto-red-flowers.png',hash='a969ba4de9f92d4d7316445110f61757d92b59cbed12b37feaca1ac134459158'}
C.flowers[#C.flowers+1]={id='johto-blue-ground-flowers',label='JOHTO BLUE CUPS',size=16,
  asset='assets/original/flora/johto-blue-ground-flowers.png',hash='e732ec36992977fa9ca264b5fda7d865803db2f366dc59b51c1cd36f187cea93'}
C.base={game='emerald',tileset='general__petalburg',id=1,
  hash='1c7acc0ebc7c5878e77e1dfbbc2828e1a2745c0ded470f1f0152f67193222ed1'}
return C
