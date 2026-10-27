local root=assert(arg[1])
local V=assert(loadfile(root..'/lib/vegetation.lua'))()
local count=0
local function eq(a,b,why)count=count+1;assert(a==b,(why or 'mismatch')..': '..tostring(a)..' ~= '..tostring(b))end
local now,active,draws,moves=0,true,0,0
local vegetation=V.new({active=function()return active end,time=function()return now end,
 draw=function(_,_,_,_,_,moved)draws=draws+1;if moved then moves=moves+1 end end})
eq(vegetation:time('A',1,1,.4),.4)
vegetation:setMode('walked');eq(vegetation:time('A',1,1,.4),nil,'untouched grass is still')
vegetation:touch('A',1,1,1,.8)
eq(vegetation:time('A',1,1,1.2),1.2-1)
eq(vegetation:time('A',2,1,1.2),nil,'neighbouring untouched grass stays still')
vegetation:touch('A',1,1,1.3,.8)
eq(vegetation:time('A',1,1,1.5),.5,'continued movement does not restart the animation each frame')
eq(vegetation:time('A',1,1,2.2),nil,'grass settles after movement stops')
local originals={}
local entities={}
for i=1,4 do
 local e={px=i*16,py=16,draw=function()return 'native',nil,3 end}
 entities[i]=e;originals[i]=e.draw
end
local world={map={id='A'},entities=entities,player=entities[1]}
vegetation:bind(world)
for _,entity in ipairs(entities)do
 local a,b,c=entity:draw(0,0);eq(a,'native');eq(b,nil);eq(c,3)
end
eq(draws,4);eq(moves,0,'standing actors do not trigger motion')
for _,entity in ipairs(entities)do entity.px=entity.px+1;entity:draw(0,0)end
eq(moves,4,'player, wild, follower and NPC draw paths observe movement')
local wrapped=entities[2].draw
for i=1,1000 do vegetation:bind(world)end
eq(entities[2].draw,wrapped,'steady frames do not rewrap or rescan the list')
entities[2].px=entities[2].px+64;entities[2]:draw(0,0)
eq(moves,4,'teleports do not rustle intervening plants')
entities[3].jumping=true;entities[3].px=entities[3].px+1;entities[3]:draw(0,0)
eq(moves,4,'jumping does not count as walking through plants')
local late={px=0,py=0,draw=function()end};entities[#entities+1]=late
local lateOriginal=late.draw;vegetation:bind(world);eq(late.draw~=lateOriginal,true,'new actors attach when the list changes')
local replacement={px=0,py=0,draw=function()end}
local replacementDraw=replacement.draw;entities[#entities]=replacement
vegetation:bind(world);eq(replacement.draw~=replacementDraw,true,'same-count appended replacements attach immediately')
local varargs={px=0,py=0,draw=function(_,...)return select('#',...)end}
entities[#entities+1]=varargs;vegetation:bind(world)
eq(varargs:draw(0,0),2,'Gen1 argument counts remain unchanged')
eq(varargs:draw(0,0,1,'top'),4,'Gen2 OAM-row arguments remain unchanged')
local before=draws;active=false;entities[1]:draw(0,0);eq(draws,before,'retained wrappers stop after ownership loss')
vegetation:dispose()
for i=1,4 do eq(entities[i].draw,originals[i],'unload restores the original actor draw')end
eq(late.draw,lateOriginal)
print('vegetation interaction checks: '..count)
