-- Native imported GB water/flowers, decoded once and cached by Donor.frames.
-- Only the tile that the original program animates is overridden; the donor
-- decoder keeps all other pixels, per-quadrant GBC palettes and source hashes.
local M={}
local GENERATIONS={red=1,blue=1,yellow=1,gold=2,silver=2,crystal=2}
local OFFSETS={1,2,3,2,1,0,7,0}
local function integer(n,max)return type(n)=='number'and n>=0 and n%1==0 and n<=max end
local function part(s)return type(s)=='string'and s~=''and s:match('^[%w_%-]+$')~=nil end
local function piece(image,w,h)
  if not image or type(image.getDimensions)~='function'then return false end
  local x,y=image:getDimensions();return x==w and y==h
end
local function animatedInCell(ts,ref,tile,name)
  local block=ts.blocks and ts.blocks[ref.id+1]
  assert(type(block)=='table'and #block>=16,'GB animation block is unavailable')
  local q=ref.quadrant or 0;local x,y=q%2*2,math.floor(q/2)*2
  local raw={}
  for _,i in ipairs({y*4+x+1,y*4+x+2,(y+1)*4+x+1,(y+1)*4+x+2})do raw[block[i]]=true end
  assert(raw[tile],'GB donor cell contains no native animated '..name..' tile')
  return raw
end
local FLOWER_ORDER={1,2,3,1,1,2,3,1}
local function flowerFrames(context,ref,spec)
  assert(type(context)=='table'and type(context.module)=='function'and type(context.sheet)=='function'
    and type(context.decode)=='function'and type(context.hash)=='function'and type(context.newImageData)=='function',
    'GB flower decoder context is incomplete')
  assert(type(ref)=='table'and GENERATIONS[ref.game]and part(ref.tileset)
    and integer(ref.id,65535)and integer(ref.quadrant or 0,3),'Invalid GB flower donor reference')
  assert(type(spec)=='table'and spec.kind=='gb'and spec.bank=='flower'
    and type(spec.hash)=='string'and spec.hash~=''and type(spec.manifestHash)=='string'and spec.manifestHash~='',
    'Checked GB flower animation specification required')
  local sets,metadata=context.module(ref.game,'data/generated/tilesets.lua')
  assert(type(sets)=='table'and type(metadata)=='string'and context.hash(metadata)==spec.manifestHash,
    'GB flower tileset metadata fingerprint changed')
  local ts=sets[ref.tileset]
  assert(type(ts)=='table','GB flower donor tileset is unavailable')
  local raw=animatedInCell(ts,ref,3,'flower')
  local variants,order,ticks={},{},nil
  if GENERATIONS[ref.game]==1 then
    assert(ts.animatedTiles==nil,'Custom GB tile animation programs are unsupported')
    assert(ts.animation=='TILEANIM_WATER_FLOWER','Gen1 donor tileset has no native flower animation')
    assert(not raw[20],'GB flower cell also uses another native tile animation: water20')
    local bytes={}
    for i=1,3 do
      local frame,source=context.sheet(ref.game,'assets/generated/tilesets/flower'..i..'.png')
      assert(type(source)=='string'and piece(frame,8,8),'Gen1 native flower source must contain complete8x8 frames')
      variants[i]=frame;bytes[i]=source
    end
    assert(context.hash(table.concat(bytes))==spec.hash,'Gen1 flower frames fingerprint changed')
    order=FLOWER_ORDER;ticks=21
  else
    local program=ts.anim
    assert(type(program)=='table'and type(program.frames)=='table'and integer(program.period,65535)
      and program.period>0,'Gen2 donor tileset has no native animation program')
    local found=false
    for _,frame in ipairs(program.frames)do
      if frame.func=='AnimateFlowerTile'then found=true
      else
        assert(not(type(frame.func)=='string'and frame.tile~=nil and raw[frame.tile]),
          'GB flower cell also uses another native tile animation: '..tostring(frame.func))
      end
    end
    assert(found,'Gen2 donor tileset has no native flower animation')
    local path=sets.flowerFrames
    assert(type(path)=='string'and path:match('^assets/generated/tilesets/[%w_/%-]+%.png$')
      and not path:find('..',1,true),'Gen2 flower frame strip is unavailable')
    local strip,bytes=context.sheet(ref.game,path)
    assert(type(bytes)=='string'and context.hash(bytes)==spec.hash,'Gen2 flower strip fingerprint changed')
    assert(piece(strip,8,32),'Gen2 native flower strip must contain four complete8x8 rows')
    local rows=sets.flowerCgbFrames
    local first,second=2,4
    if rows and rows[1]and rows[2]then first,second=rows[1],rows[2]end
    assert(integer(first,4)and first>0 and integer(second,4)and second>0,
      'Gen2 native CGB flower rows are invalid')
    for i,row in ipairs({first,second})do
      local frame=context.newImageData(8,8)
      for y=0,7 do for x=0,7 do frame:setPixel(x,y,strip:getPixel(x,(row-1)*8+y))end end
      variants[i]=frame
    end
    order={1,2};ticks=program.period*2
  end
  local sequence={frames={},ticks=ticks,period=ticks/60,offset=0,bank='gb_flower',category='flowers'}
  local decodedFrames={}
  for i,index in ipairs(order)do
    if not decodedFrames[index]then
      local decoded,why=context.decode(ref,{[3]=variants[index]})
      assert(decoded and piece(decoded.under,16,16),'GB flower frame decode failed: '..tostring(why))
      decodedFrames[index]=decoded
    end
    sequence.frames[i]=decodedFrames[index]
  end
  return sequence
end
function M.frames(context,ref,spec)
  if type(spec)=='table'and spec.bank=='flower'then return flowerFrames(context,ref,spec)end
  assert(type(context)=='table'and type(context.module)=='function'and type(context.sheet)=='function'
    and type(context.decode)=='function'and type(context.hash)=='function'and type(context.newImageData)=='function',
    'GB water decoder context is incomplete')
  assert(type(ref)=='table'and GENERATIONS[ref.game]and part(ref.tileset)
    and integer(ref.id,65535)and integer(ref.quadrant or 0,3),'Invalid GB water donor reference')
  assert(type(spec)=='table'and spec.kind=='gb'and spec.bank=='water'
    and type(spec.hash)=='string'and spec.hash~=''and type(spec.manifestHash)=='string'and spec.manifestHash~='',
    'Checked GB water animation specification required')
  local sets,metadata=context.module(ref.game,'data/generated/tilesets.lua')
  assert(type(sets)=='table'and type(metadata)=='string'and context.hash(metadata)==spec.manifestHash,
    'GB water tileset metadata fingerprint changed')
  local ts=sets[ref.tileset]
  assert(type(ts)=='table','GB water donor tileset is unavailable')
  local raw=animatedInCell(ts,ref,20,'water')
  local variants,ticks={},nil
  if GENERATIONS[ref.game]==1 then
    assert(ts.animatedTiles==nil,'Custom GB tile animation programs are unsupported')
    assert(ts.animation=='TILEANIM_WATER'or ts.animation=='TILEANIM_WATER_FLOWER',
      'Gen1 donor tileset has no native water animation')
    assert(not(ts.animation=='TILEANIM_WATER_FLOWER'and raw[3]),
      'GB water cell also uses another native tile animation: flower3')
    ticks=ts.animation=='TILEANIM_WATER_FLOWER'and 21 or 20
    local atlas,bytes=context.sheet(ref.game,ts.image)
    assert(type(bytes)=='string'and context.hash(bytes)==spec.hash,'Gen1 water atlas fingerprint changed')
    local perRow=ts.tilesPerRow or 16
    assert(integer(perRow,65535)and perRow>0,'Invalid Gen1 tile atlas width')
    local w,h=atlas:getDimensions();local sx,sy=20%perRow*8,math.floor(20/perRow)*8
    assert(sx+8<=w and sy+8<=h,'Gen1 native water tile pixels are incomplete')
    for i=1,#OFFSETS do
      local frame=context.newImageData(8,8)
      for y=0,7 do for x=0,7 do
        frame:setPixel((x+OFFSETS[i])%8,y,atlas:getPixel(sx+x,sy+y))
      end end
      variants[i]=frame
    end
  else
    local program=ts.anim
    assert(type(program)=='table'and type(program.frames)=='table'and integer(program.period,65535)
      and program.period>0,'Gen2 donor tileset has no native animation program')
    local found=false
    for _,frame in ipairs(program.frames)do
      if frame.func=='AnimateWaterTile'and frame.tile==20 then found=true
      else
        local tile=frame.func=='AnimateFlowerTile'and 3 or frame.tile
        assert(not(type(frame.func)=='string'and tile~=nil and raw[tile]),
          'GB water cell also uses another native tile animation: '..tostring(frame.func))
      end
    end
    assert(found,'Gen2 donor tileset has no native water animation')
    -- Native World:animLayers reads the strip from the global tileset table.
    local path=sets.waterFrames
    assert(type(path)=='string'and path:match('^assets/generated/tilesets/[%w_/%-]+%.png$')
      and not path:find('..',1,true),'Gen2 water frame strip is unavailable')
    local strip,bytes=context.sheet(ref.game,path)
    assert(type(bytes)=='string'and context.hash(bytes)==spec.hash,'Gen2 water strip fingerprint changed')
    assert(piece(strip,8,32),'Gen2 native water strip must contain four complete8x8 frames')
    ticks=program.period*2
    for i=1,4 do
      local frame=context.newImageData(8,8)
      for y=0,7 do for x=0,7 do frame:setPixel(x,y,strip:getPixel(x,(i-1)*8+y))end end
      variants[i]=frame
    end
  end
  local sequence={frames={},ticks=ticks,period=ticks/60,offset=0,bank='gb_water',category='water'}
  for i=1,#variants do
    local decoded,why=context.decode(ref,{[20]=variants[i]})
    assert(decoded and piece(decoded.under,16,16),'GB water frame decode failed: '..tostring(why))
    sequence.frames[i]=decoded
  end
  return sequence
end
return M
