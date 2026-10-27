-- User-supplied generated artwork; printed sheet labels are not native tile IDs.
-- Stable IDs use sheet, row and column, including visibly different near-duplicates.
local C={sheets={
  natural={path='assets/user_flora/natural.jpg',hash='a58e3890072974c7854e6c013b89f8ce191ff7d6279271f855fea63bcf9f5496'},
  botanical={path='assets/user_flora/botanical.jpg',hash='688e4362c75aa1c99209ac1bba7bd4429b57babc17c7c67632eb7e8587c6c642'},
},trees={},flowers={},grass={},water={
  {id='clear-shallows',label='CLEAR SHALLOWS',sheet='peekychew',x=224,y=64},
  {id='clear-deep',label='CLEAR DEEP',sheet='peekychew',x=304,y=64},
  {id='ripple-blue',label='RIPPLE BLUE',sheet='magiscarf',x=64,y=32},
  {id='ripple-teal',label='RIPPLE TEAL',sheet='magiscarf',x=64,y=96},
  {id='ripple-olive',label='RIPPLE OLIVE',sheet='magiscarf',x=64,y=160},
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
C.base={game='emerald',tileset='general__petalburg',id=1,
  hash='1c7acc0ebc7c5878e77e1dfbbc2828e1a2745c0ded470f1f0152f67193222ed1'}
return C
