-- Assemble reviewed native pixel rectangles without scaling or changing the
-- donor art. Source references pass through the normal fingerprint decoder.
local Composition={}
local function integer(n,maximum)
  return type(n)=='number' and n>=0 and n%1==0 and n<=maximum
end
local function coordinate(n)return n==nil and 0 or n end
local function reference(ref)
  assert(type(ref)=='table','Native composition donor reference is required')
  assert(type(ref.hash)=='string' and #ref.hash==64 and ref.hash:match('^[0-9a-f]+$'),
    'Native composition donor fingerprint is required')
end
local function image16(image)
  assert(image and type(image.getDimensions)=='function' and type(image.getPixel)=='function',
    'Native composition donor pixels are unavailable')
  local w,h=image:getDimensions()
  assert(w==16 and h==16,'Native composition donor must be 16 by 16 pixels')
end
local function blend(destination,x,y,r,g,b,a)
  if a<=0 then return end
  if a>=1 then destination:setPixel(x,y,r,g,b,1);return end
  local dr,dg,db,da=destination:getPixel(x,y)
  local alpha=a+da*(1-a)
  destination:setPixel(x,y,(r*a+dr*da*(1-a))/alpha,
    (g*a+dg*da*(1-a))/alpha,(b*a+db*da*(1-a))/alpha,alpha)
end
function Composition.new(ctx)
  assert(type(ctx)=='table' and ctx.donor and type(ctx.donor.cell)=='function',
    'Native composition donor decoder is required')
  local donor=ctx.donor
  local factory=ctx.newImageData or love.image.newImageData
  local self={}
  function self:cell(row)
    local ok,result=pcall(function()
      assert(type(row)=='table' and row.kind=='native_composite','Native composition row is required')
      local parts=row.parts
      assert(type(parts)=='table' and #parts>=1 and #parts<=16,'Native composition needs 1 to 16 parts')
      for key in pairs(parts) do
        assert(integer(key,#parts) and key>=1,'Native composition parts must be a dense array')
      end
      if row.base~=nil then reference(row.base) end
      -- Check every rectangle before asking the decoder for any artwork.
      for i=1,#parts do
        local part=parts[i]
        assert(type(part)=='table','Native composition part is required')
        reference(part.donor)
        local sx,sy,x,y=coordinate(part.srcX),coordinate(part.srcY),coordinate(part.x),coordinate(part.y)
        local w,h=part.w,part.h
        assert(integer(sx,15) and integer(sy,15) and integer(x,15) and integer(y,15)
          and integer(w,16) and w>0 and integer(h,16) and h>0
          and sx+w<=16 and sy+h<=16 and x+w<=16 and y+h<=16,
          'Native composition rectangle exceeds its 16 pixel cell')
      end
      local function flatten(ref)
        local piece,why=donor:cell(ref)
        assert(piece,'Native composition donor failed: '..tostring(why))
        assert(piece.hash==ref.hash or piece.sourceHash==ref.hash,
          'Native composition donor fingerprint changed')
        assert(piece.under,'Native composition donor under layer is unavailable')
        local out=factory(16,16)
        for _,name in ipairs({'under','mid','over'}) do
          local image=piece[name]
          if image then
            image16(image)
            for y=0,15 do for x=0,15 do blend(out,x,y,image:getPixel(x,y)) end end
          end
        end
        return out
      end
      local under=row.base and flatten(row.base) or factory(16,16)
      for i=1,#parts do
        local part=parts[i]
        local source=flatten(part.donor)
        local sx,sy,x,y=coordinate(part.srcX),coordinate(part.srcY),coordinate(part.x),coordinate(part.y)
        for dy=0,part.h-1 do for dx=0,part.w-1 do
          blend(under,x+dx,y+dy,source:getPixel(sx+dx,sy+dy))
        end end
      end
      return {under=under,over=factory(16,16)}
    end)
    if not ok then return nil,tostring(result) end
    return result
  end
  return self
end
return Composition
