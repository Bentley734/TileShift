-- Every replacement has an explicit origin and review state. Numeric tile
-- IDs from different games are never treated as equivalent by coincidence.
local M = {}
local generations={red=1,blue=1,yellow=1,gold=2,silver=2,crystal=2,ruby=3,sapphire=3,emerald=3,firered=3,leafgreen=3}
M.generations=generations
M.games={'red','blue','yellow','gold','silver','crystal','ruby','sapphire','emerald','firered','leafgreen'}
-- Cartridge identity belongs to source/donor references; the target theme
-- pools Gen 3's compatible art under one choice.
M.themes={gen1=1,gen2=2,gen3=3,red=1,blue=1,yellow=1,gold=2,silver=2,crystal=2}
function M.normalizeStyle(style)
  return generations[style]==3 and 'gen3' or style
end
function M.donorMatches(style,game)
  if style=='gen3' then return generations[game]==3 end
  if style=='gen1' then return generations[game]==1 end
  if style=='gen2' then return generations[game]==2 end
  return M.themes[style]~=nil and game==style
end

local function integer(value,maximum)
  return type(value)=='number' and value>=0 and value%1==0 and value<=maximum
end
local function fingerprint(value)
  return type(value)=='string' and #value==64 and value:match('^[0-9a-f]+$')~=nil
end
local function dense(value,size)
  if type(value)~='table' or #value~=size then return false end
  for i=1,size do if rawget(value,i)==nil then return false end end
  for key in pairs(value)do if not integer(key,size) or key==0 then return false end end
  return true
end
local function sourceColors(colors)
  if not dense(colors,4) then return false end
  for _,palette in ipairs(colors)do
    if not dense(palette,4) then return false end
    for _,rgb in ipairs(palette)do
      if not dense(rgb,3) then return false end
      for _,channel in ipairs(rgb)do if not integer(channel,255) then return false end end
    end
  end
  return true
end
local function origin(ref)
  if ref.kind==nil then return true end
  if ref.kind=='field_effect' then
    return generations[ref.game]==3 and ref.tileset=='arrow' and ref.quadrant==nil and ref.frame==nil
      and integer(ref.id,7) and fingerprint(ref.metaHash) and fingerprint(ref.rgbaHash)
  end
  return ref.kind=='field_object' and generations[ref.game]==3 and ref.tileset=='ow' and ref.quadrant==nil
    and integer(ref.frame,65535) and fingerprint(ref.metaHash) and fingerprint(ref.rgbaHash)
end
local function selectedLayers(part)
  if part.layers==nil then return part.layerHashes==nil end
  local order={under=1,mid=2,over=3}
  if type(part.layers)~='table' or #part.layers<1 or #part.layers>3
    or type(part.layerHashes)~='table' then return false end
  for key in pairs(part.layers)do
    if not integer(key,#part.layers) or key==0 then return false end
  end
  local previous,selected=0,{}
  for _,name in ipairs(part.layers)do
    if not order[name] or order[name]<=previous or not fingerprint(part.layerHashes[name]) then return false end
    previous=order[name];selected[name]=true
  end
  for name in pairs(part.layerHashes)do if not selected[name] then return false end end
  return true
end
local function validRef(style,ref)
  return type(ref)=='table' and M.donorMatches(style,ref.game)
    and type(ref.tileset)=='string' and ref.tileset~='' and integer(ref.id,65535)
    and type(ref.hash)=='string' and #ref.hash==64 and ref.hash:match('^[0-9a-f]+$')~=nil
    and (generations[ref.game]==3 or integer(ref.quadrant or 0,3)) and origin(ref)
    and (style~='gen1'or ref.monochrome==true)
end
function M.validate(row)
  if type(row)~='table' then return nil,'mapping must be a table' end
  if not generations[row.game] or not M.themes[row.style] then return nil,'unknown game or style' end
  if type(row.tileset)~='string' or row.tileset=='' then return nil,'source tileset required' end
  if not integer(row.id,65535) then return nil,'invalid source tile ID' end
  if row.map~=nil and (type(row.map)~='string' or not row.map:match('^[%w_]+$')) then return nil,'invalid source map scope' end
  if row.x~=nil or row.y~=nil then
    if not row.map or generations[row.game]>=3 or not integer(row.x,65535) or not integer(row.y,65535) then
      return nil,'position scope requires a GB map and two cell coordinates'
    end
    if row.quadrant~=(row.y%2)*2+row.x%2 then return nil,'position scope does not match source quadrant' end
  end
  if generations[row.game]<3 and not integer(row.quadrant,3) then return nil,'GB mapping requires an explicit quadrant' end
  if type(row.role)~='string' or row.role=='' then return nil,'tile meaning required' end
  if row.status~='reviewed' then return nil,'mapping has not been visually reviewed' end
  if type(row.evidence)~='string' or row.evidence=='' then return nil,'review evidence required' end
  if type(row.sourceHash)~='string' or #row.sourceHash~=64 or not row.sourceHash:match('^[0-9a-f]+$') then return nil,'source fingerprint required' end
  if row.sourceFiles~=nil then
    if generations[row.game]>=3 or type(row.sourceFiles)~='table' then return nil,'source file fingerprints require a GB source' end
    local known={metadata=true,image=true,maps=true,palettes=true,roofs=true}
    for name,value in pairs(row.sourceFiles)do
      if not known[name] or not fingerprint(value) then return nil,'invalid source file fingerprint' end
    end
    if not fingerprint(row.sourceFiles.metadata) or not fingerprint(row.sourceFiles.image)
      or not fingerprint(row.sourceFiles.maps) then return nil,'source metadata, image and map fingerprints are required' end
  end
  if row.overMask~=nil then
    if generations[row.game]~=3 or type(row.overMask)~='string' or #row.overMask~=256
      or row.overMask:find('[^01]') then return nil,'Gen3 overhead mask must contain256 binary pixels' end
  end
  if generations[row.game]==3 and row.map~=nil then return nil,'Gen3 map scopes require a separate per-map atlas' end
  if row.artOverlay~=nil then
    local overlay=row.artOverlay
    if type(overlay)~='table' or type(overlay.asset)~='string'
      or not overlay.asset:match('^assets/original/[%w_/%-%.]+%.png$')
      or overlay.asset:find('..',1,true) or not fingerprint(overlay.hash)
      or type(overlay.preserveRects)~='table' then return nil,'invalid original artwork overlay' end
    if overlay.mode~=nil and overlay.mode~='over'then return nil,'invalid original overlay mode' end
    for _,rect in ipairs(overlay.preserveRects)do
      if type(rect)~='table' or #rect~=4 or not integer(rect[1],15) or not integer(rect[2],15)
        or not integer(rect[3],16) or not integer(rect[4],16) or rect[3]==0 or rect[4]==0
        or rect[1]+rect[3]>16 or rect[2]+rect[4]>16 then return nil,'invalid retained native rectangle' end
    end
  end
  if row.sourceColors~=nil and row.kind~='source_palette' then return nil,'source colors require source palette artwork' end
  local ref=row.donor
  if row.kind=='source_palette' then
    if generations[row.game]>=3 or row.style~='gen3' then return nil,'source palette artwork requires a GB source and Gen3 style' end
    if ref or row.base or row.parts or row.asset or row.artOverlay or row.foreground
      or row.occludes or row.animated or row.animation or row.frames or row.assetFrames then
      return nil,'source palette artwork must only recolor its original source'
    end
    if not sourceColors(row.sourceColors) then return nil,'source colors must be four dense palettes of four RGB8 triples' end
  elseif ref then
    if type(ref)~='table' or not M.donorMatches(row.style,ref.game) then return nil,'donor does not match selected style' end
    if type(ref.tileset)~='string' or ref.tileset=='' or not integer(ref.id,65535) then return nil,'invalid donor tile reference' end
    if generations[ref.game]<3 and not integer(ref.quadrant or 0,3) then return nil,'invalid donor quadrant' end
    if type(ref.hash)~='string' or #ref.hash~=64 or not ref.hash:match('^[0-9a-f]+$') then return nil,'donor fingerprint required' end
    if not origin(ref) then return nil,'invalid native donor origin' end
    if row.style=='gen1'and ref.monochrome~=true then return nil,'Gen1 theme requires original monochrome donors' end
  elseif row.asset then
    if row.kind~='original' and row.kind~='third_party' then return nil,'asset origin must be identified' end
    local prefix=row.kind=='original' and 'original' or 'third_party'
    if type(row.asset)~='string' or not row.asset:match('^assets/'..prefix..'/[%w_/%-%.]+%.png$') or row.asset:find('..',1,true) then return nil,'invalid asset path' end
    if row.kind=='third_party' and (type(row.credit)~='string' or row.credit=='' or type(row.sourceUrl)~='string' or not row.sourceUrl:match('^https://')) then return nil,'third-party art requires credit and its source URL' end
    if row.assetFileHash~=nil and (type(row.assetFileHash)~='string' or #row.assetFileHash~=64 or not row.assetFileHash:match('^[0-9a-f]+$')) then return nil,'invalid asset fingerprint' end
    if row.base then
      if type(row.base)~='table' or not M.donorMatches(row.style,row.base.game)
        or type(row.base.tileset)~='string' or row.base.tileset=='' or not integer(row.base.id,65535)
        or type(row.base.hash)~='string' or #row.base.hash~=64 or not row.base.hash:match('^[0-9a-f]+$')
        or (generations[row.base.game]<3 and not integer(row.base.quadrant or 0,3)) or not origin(row.base) then return nil,'invalid asset ground reference' end
    end
  elseif row.parts then
    if row.kind~='native_composite' then return nil,'native composition origin required' end
    local maxParts=generations[row.game]==3 and (row.style=='gen1'or row.style=='gen2')and 32 or 16
    if type(row.parts)~='table' or #row.parts<1 or #row.parts>maxParts then return nil,'invalid native composition parts' end
    for key in pairs(row.parts)do
      if not integer(key,#row.parts) or key==0 then return nil,'native composition parts must be a dense array' end
    end
    if row.base and not validRef(row.style,row.base) then return nil,'invalid composition ground reference' end
    for i=1,#row.parts do
      local part=row.parts[i]
      if type(part)~='table' or not validRef(row.style,part.donor) then return nil,'invalid composition donor' end
      if part.animated~=nil and type(part.animated)~='boolean'then return nil,'invalid animated composition part' end
      if part.animated and not(row.animated==true and type(row.animation)=='table'and row.animation.kind=='gb')then
        return nil,'animated GB parts need an animated row and native GB animation profile'
      end
      if part.animated and part.layers~=nil then return nil,'animated GB parts cannot select native layers' end
      if not selectedLayers(part) then return nil,'invalid composition layer selection or fingerprint' end
      local sx,sy,x,y,w,h=part.srcX or 0,part.srcY or 0,part.x or 0,part.y or 0,part.w,part.h
      if not integer(sx,15) or not integer(sy,15) or not integer(x,15) or not integer(y,15)
        or not integer(w,16) or w==0 or not integer(h,16) or h==0
        or sx+w>16 or sy+h>16 or x+w>16 or y+h>16 then return nil,'composition rectangle exceeds its cell' end
    end
  else return nil,'donor, native composition or original artwork required' end
  if ref and row.asset then return nil,'mapping must have exactly one artwork source' end
  if row.parts and (ref or row.asset) then return nil,'mapping must have exactly one artwork source' end
  if row.assetFrames~=nil then
    if not row.asset or row.kind~='original'or row.animated~=true or type(row.assetFrames)~='table'
      or #row.assetFrames<2 or #row.assetFrames>16 then return nil,'invalid original overlay animation' end
    for key in pairs(row.assetFrames)do
      if not integer(key,#row.assetFrames)or key==0 then return nil,'overlay frames must be a dense array' end
    end
    for i=1,#row.assetFrames do
      local frame=row.assetFrames[i]
      if type(frame)~='table'or type(frame.asset)~='string'
        or not frame.asset:match('^assets/original/[%w_/%-%.]+%.png$')or frame.asset:find('..',1,true)
        or not fingerprint(frame.hash)then return nil,'invalid overlay animation fingerprint' end
    end
    if row.assetFrames[1].asset~=row.asset or row.assetFrames[1].hash~=row.assetFileHash then
      return nil,'overlay animation must start with its checked original asset'
    end
  end
  if row.animated~=nil and type(row.animated)~='boolean' then return nil,'invalid animated tile flag' end
  if row.animated then
    local animation=row.animation
    if animation~=nil and type(animation)~='table'then return nil,'invalid animation profile' end
    local animatedRef=ref or ((row.parts or row.asset) and row.base)
    if (row.parts or row.asset) and not(animation and animation.kind=='gb') and (generations[row.game]>=3 or not row.base or not animation or row.base.kind~=nil) then
      return nil,'animated composition requires a GB host and fingerprint-checked metatile base bank'
    end
    if animation and animation.kind=='gb' then
      if row.parts then
        local marked
        for _,part in ipairs(row.parts)do if part.animated then animatedRef=part.donor;marked=true;break end end
        if not marked then return nil,'GB animation needs a marked source part' end
      end
      if generations[row.game]~=3 or not animatedRef or generations[animatedRef.game]>=3
        or (animation.bank~='water'and animation.bank~='flower')
        or not fingerprint(animation.hash)or not fingerprint(animation.manifestHash)then return nil,'GB water animation needs checked native source files and a Gen3 host' end
    elseif animation then
      if type(animation)~='table' or not animatedRef or animatedRef.kind~=nil or generations[animatedRef.game]~=3
        or type(animation.bank)~='string' or not animation.bank:match('^[%w_]+$')
        or type(animation.hash)~='string' or #animation.hash~=64 or not animation.hash:match('^[0-9a-f]+$')
        or type(animation.manifestHash)~='string' or #animation.manifestHash~=64 or not animation.manifestHash:match('^[0-9a-f]+$')
        or (animation.overHash~=nil and not fingerprint(animation.overHash))
        or (animation.frame0Hash~=nil and not fingerprint(animation.frame0Hash)) then return nil,'animated tile needs a fingerprint-checked donor bank' end
    elseif not row.frames or #row.frames<2 then return nil,'animated tile needs reviewed animation frames' end
  end
  if row.occludes and not row.foreground then return nil,'occluding tile needs a foreground mask' end
  return true
end
function M.key(row)
  return table.concat({row.game,row.style,row.tileset,tostring(row.id),row.quadrant==nil and '*' or tostring(row.quadrant),row.map or '*',
    row.x==nil and '*' or tostring(row.x),row.y==nil and '*' or tostring(row.y)},':')
end
function M.index(rows)
  local out,errors={},{}
  for i,row in ipairs(rows) do
    local ok,why=M.validate(row)
    if ok then
      local key=M.key(row)
      if out[key] then errors[#errors+1]='duplicate mapping '..key else out[key]=row end
    else errors[#errors+1]='row '..i..': '..why end
  end
  return out,errors
end
return M
