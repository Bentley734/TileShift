local root=assert(arg[1]);local unpack=table.unpack or unpack
local F=assert(loadfile(root..'/lib/flora.lua'))()
local checks,allocations,reads=0,0,0
local function eq(a,b,why)checks=checks+1;assert(a==b,why or(tostring(a)..' ~= '..tostring(b)))end
local function image(w,h)
 allocations=allocations+1;local p={};local out={}
 function out:getDimensions()return w,h end
 function out:getPixel(x,y)local z=p[y*w+x];if z then return unpack(z)end;return 0,0,0,0 end
 function out:setPixel(x,y,...)assert(x>=0 and x<w and y>=0 and y<h);p[y*w+x]={...}end
 function out:paste(source,dx,dy,sx,sy,sw,sh)for y=0,sh-1 do for x=0,sw-1 do self:setPixel(dx+x,dy+y,source:getPixel(sx+x,sy+y))end end end
 return out
end
local catalog={big_trees={},base={game='firered',tileset='test',id=1,hash=string.rep('a',64)}}
local sprites={}
for i=1,3 do
 local path='native-tree-'..i;catalog.big_trees[i]={id=path,asset=path,hash=string.rep(tostring(i),64),size=32};local im=image(32,32)
 for y=2,30 do for x=0,31 do
  local left=i==2 and 0 or 3;local right=i==3 and 31 or 28
  if x>=left and x<=right and(x+y)%5~=0 then im:setPixel(x,y,x/32,y/32,i/4,1)end
 end end;sprites[path]=im
end
local f=F.new({catalog=catalog,seed=42,newImageData=image,sheet=function(path)reads=reads+1;return assert(sprites[path])end,base=function()return image(16,16)end})
local roles={'northwest','northeast','southwest','southeast'};local source={}
for q=0,3 do source[q+1]={game='crystal',map='AZALEA_GYM',tileset='TILESET_ELITE_FOUR_ROOM',id=33,quadrant=q,role='dense_forest_tree_'..roles[q+1]}end
local def={id='AZALEA_GYM',width=5,height=8,blocks={}}
for i=1,40 do def.blocks[i]=0 end;def.blocks[18]=33
for _,choice in ipairs({'default','random','mixed','native-tree-1','native-tree-2','native-tree-3'})do
 f:select('big_trees',choice);local normal=f:rows(source,'crystal',def)
 for q=0,3 do
  local row
  for _,r in ipairs(normal)do if r.quadrant==q and(choice~='mixed'or(r.x==4+q%2 and r.y==6+math.floor(q/2)))then row=r end end
  assert(row);local _,sequence=f:piece(row)
  local placement={game='crystal',map='AZALEA_GYM',furniture='azalea_gym_tree',anchorX=4,anchorY=6,x=4+q%2,y=5+math.floor(q/2)}
  local moved=f:offsetTreeFrames(placement)
  for phase=1,4 do for y=0,15 do for x=0,15 do
   local a={moved[phase]:getPixel(x,y)};local b={sequence.frames[phase].under:getPixel(x,y)}
   for c=1,4 do eq(a[c],b[c],'finite offset keeps exact existing selected-tree/wind pixels')end
  end end end
 end
end
for _,speed in ipairs({0,.5,1,2})do
 f:speed('trees',speed)
 for _,now in ipairs({0,.1,.36,.71,1.06,2.3})do
  local expected=speed==0 and 1 or(math.floor(now/(.35/speed))%4+1)
  eq(f:offsetTreePhase(now),expected,'existing tree animation-rate option is preserved')
 end
end
local row={game='crystal',map='AZALEA_GYM',furniture='azalea_gym_tree',anchorX=4,anchorY=6,x=4,y=5}
f:select('big_trees','native-tree-1');f:offsetTreeFrames(row);local a,r=allocations,reads
for i=1,100 do f:offsetTreeFrames(row)end
eq(allocations,a,'warm finite tree has no image allocations');eq(reads,r,'warm finite tree has no sheet reads')
local wrong={};for k,v in pairs(row)do wrong[k]=v end;wrong.map='NEW_BARK_TOWN';eq(pcall(function()f:offsetTreeFrames(wrong)end),false,'finite path cannot affect other maps')
print('flora_offset_tree_test: '..checks..' checks')
