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
local function selectedLayers(part)
  if part.layers==nil then
    assert(part.layerHashes==nil,'Layer fingerprints require an explicit layer selection')
    return
  end
  local layers,hashes=part.layers,part.layerHashes
  assert(type(layers)=='table' and #layers>=1 and #layers<=3 and type(hashes)=='table',
    'Selected native layers and their fingerprints are required')
  for key in pairs(layers)do
    assert(integer(key,#layers) and key>=1,'Selected native layers must be a dense array')
  end
  local order,previous,selected={under=1,mid=2,over=3},0,{}
  for _,name in ipairs(layers)do
    assert(order[name] and order[name]>previous,'Selected native layers must be unique and in rendering order')
    local hash=hashes[name]
    assert(type(hash)=='string' and #hash==64 and hash:match('^[0-9a-f]+$'),
      'Selected native layer fingerprint is required')
    previous=order[name];selected[name]=true
  end
  for name in pairs(hashes)do assert(selected[name],'Unselected native layer fingerprint')end
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
  local hashImage=ctx.hashImage or function(image)
    return love.data.encode('string','hex',love.data.hash('sha256',image:getString()))
  end
  local self={}
  local function validate(row)
      assert(type(row)=='table' and row.kind=='native_composite','Native composition row is required')
      assert(row.donor==nil and row.asset==nil,'Native composition must have exactly one artwork source')
      local parts=row.parts
      local gba={ruby=true,sapphire=true,emerald=true,firered=true,leafgreen=true}
      local limit=gba[row.game]and(row.style=='gen1'or row.style=='gen2')and 32 or 16
      assert(type(parts)=='table' and #parts>=1 and #parts<=limit,limit==16 and'Native composition needs 1 to 16 parts'or'Native reverse composition needs 1 to 32 parts')
      for key in pairs(parts) do
        assert(integer(key,#parts) and key>=1,'Native composition parts must be a dense array')
      end
      if row.base~=nil then reference(row.base) end
      -- Check every rectangle before asking the decoder for any artwork.
      local marked
      for i=1,#parts do
        local part=parts[i]
        assert(type(part)=='table','Native composition part is required')
        reference(part.donor)
        assert(part.animated==nil or type(part.animated)=='boolean','Invalid animated composition part')
        if part.animated then
          assert(row.animated==true and type(row.animation)=='table'and row.animation.kind=='gb',
            'Animated GB parts need an animated row and native GB animation profile')
          assert(part.layers==nil,'Animated GB parts cannot select native layers')
          marked=true
        end
        selectedLayers(part)
        local sx,sy,x,y=coordinate(part.srcX),coordinate(part.srcY),coordinate(part.x),coordinate(part.y)
        local w,h=part.w,part.h
        assert(integer(sx,15) and integer(sy,15) and integer(x,15) and integer(y,15)
          and integer(w,16) and w>0 and integer(h,16) and h>0
          and sx+w<=16 and sy+h<=16 and x+w<=16 and y+h<=16,
          'Native composition rectangle exceeds its 16 pixel cell')
      end
      if row.animated and type(row.animation)=='table'and row.animation.kind=='gb'then
        assert(marked,'GB animation needs a marked source part')
      end
  end
  local function flatten(piece,layers,hashes)
        assert(type(piece)=='table','Native composition frame is unavailable')
        assert(piece.under,'Native composition donor under layer is unavailable')
        local out=factory(16,16)
        for _,name in ipairs(layers or {'under','mid','over'}) do
          local image=piece[name]
          assert(not layers or image,'Selected native layer is unavailable: '..name)
          if image then
            image16(image)
            assert(not layers or hashImage(image)==hashes[name],
              'Selected native layer fingerprint changed: '..name)
            for y=0,15 do for x=0,15 do blend(out,x,y,image:getPixel(x,y)) end end
          end
        end
        return out
  end
  local function decoded(ref,layers,hashes)
    local piece,why=donor:cell(ref)
    assert(piece,'Native composition donor failed: '..tostring(why))
    assert(piece.hash==ref.hash or piece.sourceHash==ref.hash,
      'Native composition donor fingerprint changed')
    return flatten(piece,layers,hashes)
  end
  local function prepare(row)
    local sources={}
    for i,part in ipairs(row.parts)do sources[i]=decoded(part.donor,part.layers,part.layerHashes)end
    return sources
  end
  local function compose(row,under,sources)
      for i,part in ipairs(row.parts) do
        local source=sources[i]
        local sx,sy,x,y=coordinate(part.srcX),coordinate(part.srcY),coordinate(part.x),coordinate(part.y)
        for dy=0,part.h-1 do for dx=0,part.w-1 do
          blend(under,x+dx,y+dy,source:getPixel(sx+dx,sy+dy))
        end end
      end
      return {under=under,over=factory(16,16)}
  end
  function self:cell(row)
    local ok,result=pcall(function()
      validate(row)
      local under=row.base and decoded(row.base) or factory(16,16)
      return compose(row,under,prepare(row))
    end)
    if not ok then return nil,tostring(result) end
    return result
  end
  function self:frames(row)
    local ok,result=pcall(function()
      validate(row)
      if row.animation and row.animation.kind=='gb'then
        local sources=prepare(row)
        local sequences,first={},nil
        for i,part in ipairs(row.parts)do if part.animated then
          local sequence,why=donor:frames(part.donor,row.animation)
          assert(sequence,'GB part animation failed: '..tostring(why))
          assert(type(sequence.frames)=='table'and #sequence.frames>=2 and #sequence.frames<=256
            and type(sequence.period)=='number'and sequence.period>0,'Invalid GB part frames')
          if first then assert(#sequence.frames==#first.frames and sequence.period==first.period
            and(sequence.offset or 0)==(first.offset or 0),'GB part animation schedules differ')end
          first=first or sequence;sequences[i]=sequence
        end end
        assert(first,'GB animation needs a marked source part')
        local base=row.base and decoded(row.base)or factory(16,16)
        local result={frames={}}
        for key,value in pairs(first)do if key~='frames'then result[key]=value end end
        for frame=1,#first.frames do
          local prepared={}
          for i,source in ipairs(sources)do
            prepared[i]=sequences[i]and flatten(sequences[i].frames[frame])or source
          end
          local under=factory(16,16)
          for y=0,15 do for x=0,15 do under:setPixel(x,y,base:getPixel(x,y))end end
          result.frames[frame]=compose(row,under,prepared)
        end
        return result
      end
      local gb={red=true,blue=true,yellow=true,gold=true,silver=true,crystal=true}
      assert(gb[row.game] and row.animated==true and type(row.animation)=='table',
        'Animated native composition requires a GB host and reviewed animation bank')
      assert(row.base and row.base.kind==nil,'Animated native composition requires a metatile base')
      assert(type(donor.frames)=='function','Native composition animation decoder is unavailable')
      -- Recheck the complete base reference even when the decoder has cached
      -- its bank. Donor.frames verifies the manifest/bank and native schedule.
      decoded(row.base)
      local sequence,why=donor:frames(row.base,row.animation)
      assert(sequence,'Native composition animation failed: '..tostring(why))
      assert(type(sequence.frames)=='table' and #sequence.frames>=2 and #sequence.frames<=256
        and type(sequence.ticks)=='number' and integer(sequence.ticks,65535) and sequence.ticks>0
        and sequence.period==sequence.ticks/60 and sequence.bank==row.animation.bank
        and integer(sequence.phase,sequence.ticks-1) and sequence.offset==sequence.phase/60
        and (sequence.counter=='global' or sequence.counter=='primary' or sequence.counter=='secondary'),
        'Native composition animation sequence is invalid')
      for key in pairs(sequence.frames)do
        assert(integer(key,#sequence.frames) and key>=1,'Native composition frames must be a dense array')
      end
      local sources=prepare(row)
      local output={frames={}}
      for key,value in pairs(sequence)do if key~='frames'then output[key]=value end end
      for i=1,#sequence.frames do
        local piece=sequence.frames[i]
        local under=flatten(piece)
        if i==1 and row.animation.frame0Hash then
          assert(hashImage(under)==row.animation.frame0Hash,'Native composition base frame fingerprint changed')
        end
        output.frames[i]=compose(row,under,sources)
      end
      return output
    end)
    if not ok then return nil,tostring(result)end
    return result
  end
  return self
end
return Composition
