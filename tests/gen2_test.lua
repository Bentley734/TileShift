-- Run with arg[1] = TileShift directory; pure fixtures, no live game changes.
local root=assert(arg and arg[1], 'TileShift directory required')
local Adapter=assert(loadfile(root..'/lib/gen2.lua'))()
local count=0
local function eq(a,b,message)
  count=count+1;assert(a==b,(message or 'mismatch')..': '..tostring(a)..' ~= '..tostring(b))
end
local calls,shader,stack={},'native-shader',{}
local G={}
function G.push() stack[#stack+1]=shader end
function G.pop() shader=table.remove(stack) end
function G.setShader(s) shader=s end
function G.setColor() end
function G.origin() end
function G.setScissor() end
function G.clear() end
function G.draw(image,...)
  calls[#calls+1]={image=image,args={...},shader=shader}
end
function G.newQuad(...) return {quad={...}} end
local function data(label,w,h)
  return {label=label,getDimensions=function()return w or 32,h or 32 end}
end
function G.newImage(d)
  return {source=d,getDimensions=d.getDimensions,setFilter=function()end,
    setWrap=function(self,x,y)self.wrap={x,y}end,
    release=function(self)self.released=true end}
end
local originalCells={ [4]={tile=4,slot=1,layer={kind='water'},cells={0,0,32,0,64,0}} }
local nativeCalls=0
local World={}
function World:mapCacheKey(id)return id..'|DAY'end
function World:bakeMapImage()
  return {renderTo=function(_,fn)fn()end},'native-palettes'
end
function World:animCellsFor() return originalCells end
function World:drawAnimCells()nativeCalls=nativeCalls+1 end
function World:borderImageFor()return 'native-border'end
function World:blitBgOverRegionLocal(def,ox,oy,x0,y0)
  calls[#calls+1]={native=true,x=x0,y=y0,ox=ox,oy=oy}
end
function World:drawGrassOverGoldSilver() nativeCalls=nativeCalls+1 end
function World:grassAtlasFor()return self.atlas,self.tilesets.TEST end
function World:bgTileAt()return 4 end
function World:bgTileAttrAt(_,_,x) return {attr={priority=x==0}}end
local Border={blockFor=function(id,border)return (id==nil or id==0) and border or id end,
  fillBlock=function(def)return def.borderBlock end}
local Palette={available=function()return true end,use=function()shader='palette-shader'end}
local main,grass,fore,frame1,frame2=data('main'),data('grass'),data('foreground'),data('frame1'),data('frame2')
local art={ [1]={image=main,frames={frame1,frame2},period=.2},
  [2]={image=grass,foreground=fore},[3]=data('unsafe-grass') }
local def={id='MAP',tileset='TEST',width=3,height=1,blocks={1,2,3},borderBlock=1}
local ts={blocks={{}, {},{},{}},collision={{},{0,0,0,0},{0x18,0x18,0x18,0x18},{0x18,0,0,0}}}
local map={id='MAP',def=def,width=3,height=1,blocks=def.blocks,borderBlock=1}
local world=setmetatable({map=map,maps={MAP=def},tilesets={TEST=ts},mapImages={},animCells={},
  bgSets={},camera={x=0,y=0},atlas=G.newImage(data('native-atlas')),neighbors={}}, {__index=World})
local warns,time,revision={},.3,0
local function newCanvas(w,h)
  return {getDimensions=function()return w,h end,renderTo=function(_,fn)fn()end,
    setFilter=function()end,setWrap=function()end,release=function(self)self.released=true end}
end
local originals={};for k,v in pairs(World)do originals[k]=v end
local close=Adapter.install({worldClass=World,borderFill=Border,palette=Palette,graphics=G,
  version=function()return 'gold'end,replacements=function(version,tileset,actualDef)
    eq(version,'gold');eq(tileset,'TEST');eq(actualDef,def);return art
  end,time=function()return time end,revision=function()return revision end,
  newCanvas=newCanvas,
  warn=function(message)warns[#warns+1]=message end})
local key=world:mapCacheKey('MAP')
eq(key:sub(1,7),'MAP|DAY');eq(key:find('|tileshift|',1,true)~=nil,true)
revision=1;eq(world:mapCacheKey('MAP')~=key,true,'settings revision invalidates map bake')
local canvas,bg=world:bakeMapImage(map,'DAY')
eq(bg,'native-palettes');eq(#calls,2,'unsafe grass remains native')
eq(calls[1].image.source,main);eq(calls[2].image.source,grass)
eq(calls[1].shader,nil,'replacement retains full color');eq(shader,'native-shader','shader restored')
eq(map.blocks,def.blocks);eq(map.blocks[1],1);eq(ts.blocks[2][1],nil,'source blocks unchanged')
eq(#warns,1,'missing foreground reported once')
local filtered=world:animCellsFor(map,ts)
eq(#originalCells[4].cells,6,'native list untouched')
eq(#filtered[4].cells,2,'covered animation cells suppressed')
eq(filtered[4].cells[1],64,'unsafe grass still animates natively')
calls={};world:drawAnimCells('MAP',0,0,1)
eq(nativeCalls,1);eq(#calls,1);eq(calls[1].image.source,frame2,'donor animation current frame')
eq(shader,'native-shader')
art[1].period=16/60;art[1].offset=1/60
time=16/60;calls={};world:drawAnimCells('MAP',0,0,1)
eq(calls[1].image.source,frame1,'native phase1 holds frame zero through tick16')
time=17/60;calls={};world:drawAnimCells('MAP',0,0,1)
eq(calls[1].image.source,frame2,'native phase1 advances at tick17')
time=0;calls={};world:drawAnimCells('MAP',0,0,1)
eq(calls[1].image.source,frame1,'pre-phase clock clamps to initial frame')
art[1].period=.2;art[1].offset=nil;time=.3
local border=world:borderImageFor('MAP')
eq(border.source,frame2);eq(border.wrap[1],'repeat');eq(border.wrap[2],'repeat')
calls={};world:blitBgOverRegionLocal(def,0,0,0,0,72,8,false,function(info)return true end,1)
eq(#calls,9,'one render per native or donor tile')
eq(calls[1].image.source,frame2);eq(calls[5].image.source,grass)
eq(calls[9].native,true);eq(calls[9].x,64)
calls={};world:blitBgOverRegionLocal(def,0,0,0,0,8,8,false,
  function(info)return not info.attr.priority end,1)
eq(#calls,0,'native priority filter honored')
calls={};world:blitBgOverRegionLocal(def,0,0,32,0,40,8,true,nil,1)
eq(calls[1].image.source,fore,'grass uses explicit alpha layer')
calls={};world:drawGrassOverGoldSilver({inGrass=true,px=32,py=0},0,0,1)
eq(#calls,4);eq(calls[1].image.source,fore);eq(calls[1].shader,nil)
eq(shader,'native-shader')
-- A reviewed 16px quadrant must not hide source animation or sprite overlays
-- in any of the other three quadrants of the same 32px block.
art[1].coverage={[0]=true}
originalCells[4].cells[#originalCells[4].cells+1]=16
originalCells[4].cells[#originalCells[4].cells+1]=0
local partial=world:animCellsFor(map,ts)
eq(#partial[4].cells,4);eq(partial[4].cells[3],16,'uncovered same-block native animation survives')
calls={};world:blitBgOverRegionLocal(def,0,0,0,0,32,8,false,nil,1)
eq(#calls,4);eq(calls[1].image.source,frame2);eq(calls[3].native,true);eq(calls[3].x,16)
calls={};world:bakeMapImage(map,'DAY')
eq(calls[1].args[1].quad[3],16,'partial bake crops to reviewed 16px quadrant')
eq(calls[1].args[1].quad[4],16)
calls={};local partialBorder=world:borderImageFor('MAP')
eq(#calls,2,'partial border draws source then donor quadrant')
eq(calls[1].image,'native-border');eq(calls[2].image.source,frame2)
calls={};eq(world:borderImageFor('MAP'),partialBorder);eq(#calls,0,'partial border composition cached')
-- One reused block can receive different reviewed art at a single map position.
local posBackground,posForeground=data('position-background'),data('position-foreground')
art[1].positions={['0:0']={image=posBackground,foreground=posForeground,coverage={[1]=true}}}
local previousBlock=def.blocks[3];def.blocks[3]=1
calls={};world:bakeMapImage(map,'DAY')
eq(#calls,3);eq(calls[1].image.source,posBackground,'first occurrence selects its variant')
eq(calls[1].args[1].quad[1],16,'position variant has independent quadrant coverage')
eq(calls[3].image.source,main,'same source block elsewhere keeps generic art')
calls={};world:drawAnimCells('MAP',0,0,1)
eq(#calls,1);eq(calls[1].image.source,frame2,'static positional art suppresses only its own generic animation')
eq(calls[1].args[2],64,'other occurrence continues its own animation')
local positionFiltered=world:animCellsFor(map,ts)
eq(#positionFiltered[4].cells,2);eq(positionFiltered[4].cells[1],0,
  'source animation filtering uses occurrence coverage instead of shared block coverage')
calls={};world:blitBgOverRegionLocal(def,0,0,16,0,24,8,true,nil,1)
eq(calls[1].image.source,posForeground,'position foreground follows the same occurrence')
calls={};world:blitBgOverRegionLocal(def,0,0,80,0,88,8,true,nil,1)
eq(calls[1].native,true,'other occurrence does not inherit position coverage')
calls={};eq(world:borderImageFor('MAP'),partialBorder);eq(#calls,0,'position art never leaks into repeating border')
def.blocks[3]=previousBlock;art[1].positions=nil
world.mapImages[key]=canvas;world.animCells[key]=filtered;world.bgSets[key]=bg
local borrowed=function()return 'later-mod'end
World.borderImageFor=borrowed
local retained=World.blitBgOverRegionLocal
close();close()
eq(World.borderImageFor,borrowed,'cleanup does not undo another mod wrapper')
eq(World.bakeMapImage,originals.bakeMapImage);eq(World.animCellsFor,originals.animCellsFor)
eq(world.mapImages[key],nil);eq(world.animCells[key],nil);eq(world.bgSets[key],nil)
eq(border.released,true,'owned image released')
eq(partialBorder.released,true,'partial border canvas released')
calls={};retained(world,def,0,0,0,0,8,8,false,nil,1)
eq(calls[1].native,true,'retained wrapper delegates after unloading')
eq(calls[1].image,nil,'retained wrapper cannot use released artwork')
-- Native mapImage pointers are cached outside mapImages. Losing mod ownership
-- has to restore those pointers before the next native world draw.
local active=true
local Live={}
function Live:mapCacheKey(id)return id end
function Live:imageFor(id)return 'native-'..id end
function Live:draw()return self.mapImage end
local live=setmetatable({map={id='ACTIVE'},mapImage='painted',neighbors={{id='NEIGHBOR',image='painted'}}},
  {__index=Live})
local dispose=Adapter.install({worldClass=Live,borderFill=Border,palette=Palette,graphics=G,
  replacements=function()return art end,version=function()return 'gold'end,
  active=function()return active end})
eq(live:draw(),'painted');active=false
eq(live:draw(),'native-ACTIVE','lost ownership restores source before world draw')
eq(live.neighbors[1].image,'native-NEIGHBOR','neighbor pointers restored too')
eq(live:mapCacheKey('ACTIVE'),'ACTIVE','ownership loss unregisters cache wrapper')
dispose()
print('PASS Gen 2 graphics adapter: '..count..' assertions')
