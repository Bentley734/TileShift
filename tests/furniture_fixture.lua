-- ROM-free renderer fixture using independently frozen native asset alpha.
local Fixture={}
function Fixture.new(root,rows,nativeFixture,contextOverrides)
 local Roofs=assert(loadfile(root..'/lib/roofs.lua'))()
 local Mapping=assert(loadfile(root..'/lib/mapping.lua'))()
 local native=nativeFixture or assert(loadfile(root..'/tests/furniture_native_alpha.lua'))()
 local f={game='crystal',active=true,revision=1,valid=true,surface={},sourceReads=0,assetReads=0,images=0,releases=0,warnings={},pixels={}}
 local G={push=function()end,pop=function()end,setShader=function()end,setColor=function()end}
 function G.newImage(data)f.images=f.images+1;return{data=data,setFilter=function()end,release=function()f.releases=f.releases+1 end}end
 function G.newQuad()return{setViewport=function(q,x,y,w,h)q.x,q.y,q.w,q.h=x,y,w,h end,release=function()end}end
 function G.draw(texture,q,x,y)
  local sx,sy,w,h
  if type(q)=='table'then sx,sy,w,h=q.x,q.y,q.w,q.h else x,y=q,x;sx,sy,w,h=0,0,16,16 end
  for yy=0,h-1 do for xx=0,w-1 do if texture.data.ink(sx+xx,sy+yy)then f.surface[(y+yy)*4096+x+xx]=texture.data.path end end end
 end
 local ctx={rows={},furnitureRows=rows,graphics=G,version=function()return f.game end,
  active=function()return f.active end,revision=function()return f.revision end,
  validate=function(row)assert(row.x==row.anchorX and row.y==row.anchorY);return Mapping.validate(row)end,
  donor={cell=function(_,ref)
   f.sourceReads=f.sourceReads+1
   assert(ref.map==f.def and ref.hashOnly and ref.monochrome and ref.sourceFiles)
   if not f.valid or ref.hash==f.failHash then return nil,'changed source fixture'end
   return{}
  end},
  original=function(path,expected)
   f.assetReads=f.assetReads+1
   local fixture=assert(native.assets[path],'Missing native alpha fixture: '..path)
   assert(expected==fixture.hash,'Native asset fingerprint changed')
   local data=f.pixels[path]
   if not data then
    data={path=path,getDimensions=function()return 16,16 end}
    function data.ink(x,y)return fixture.mask:sub(y*16+x+1,y*16+x+1)=='1'end
    function data:getPixel(x,y)return 1,1,1,self.ink(x,y)and 1 or 0 end
    f.pixels[path]=data
   end
   return data
  end,warn=function(message)f.warnings[#f.warnings+1]=message end}
 for k,v in pairs(contextOverrides or{})do ctx[k]=v end
 f.ctx=ctx;f.rows=rows;f.roofs=Roofs.new(ctx)
 function f:select(game,map)
  self.game=game
  local meta=assert(native.maps[game][map]);local def={id=map,tileset=meta.tileset,width=meta.width,height=meta.height,blocks={}}
  for i=1,def.width*def.height do def.blocks[i]=0 end
  for _,r in ipairs(rows)do if r.game==game and r.map==map then
   local at=math.floor(r.anchorY/2)*def.width+math.floor(r.anchorX/2)+1
   assert(def.blocks[at]==0 or def.blocks[at]==r.id);def.blocks[at]=r.id
   if r.footId then
    local fi=math.floor(r.footY/2)*def.width+math.floor(r.footX/2)+1
    assert(def.blocks[fi]==0 or def.blocks[fi]==r.footId);def.blocks[fi]=r.footId
   end
  end end
  self.def=def;self.world={camera={x=0,y=0},viewW=def.width*32,viewH=def.height*32,daytime='DAY'}
  return def
 end
 function f:map()self.surface={};self.roofs:map(self.world,self.def,0,0,1);return self.surface end
 function f:actor(entity)self.surface={};self.roofs:actor({def=self.def},entity,0,0,1,false,0,self.world);return self.surface end
 function f:ink(x,y)return self.surface[y*4096+x]end
 function f:clear(x,y,value)self.def.blocks[math.floor(y/2)*self.def.width+math.floor(x/2)+1]=value or 0 end
 function f:reject(row)
  local bad={};for k,v in pairs(self.ctx)do bad[k]=v end;bad.furnitureRows={row}
  return pcall(Roofs.new,bad)
 end
 return f
end
return Fixture
