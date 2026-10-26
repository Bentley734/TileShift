-- Every replacement has an explicit origin and review state. Numeric tile
-- IDs from different games are never treated as equivalent by coincidence.
local M = {}
local generations={red=1,blue=1,yellow=1,gold=2,silver=2,crystal=2,ruby=3,sapphire=3,emerald=3,firered=3,leafgreen=3}
M.generations=generations
M.games={'red','blue','yellow','gold','silver','crystal','ruby','sapphire','emerald','firered','leafgreen'}
-- Cartridge identity belongs to source/donor references; the target theme
-- pools Gen 3's compatible art under one choice.
M.themes={gen3=3,red=1,blue=1,yellow=1,gold=2,silver=2,crystal=2}
function M.normalizeStyle(style)
  return generations[style]==3 and 'gen3' or style
end
function M.donorMatches(style,game)
  if style=='gen3' then return generations[game]==3 end
  return M.themes[style]~=nil and game==style
end

local function integer(value,maximum)
  return type(value)=='number' and value>=0 and value%1==0 and value<=maximum
end
local function validRef(style,ref)
  return type(ref)=='table' and M.donorMatches(style,ref.game)
    and type(ref.tileset)=='string' and ref.tileset~='' and integer(ref.id,65535)
    and type(ref.hash)=='string' and #ref.hash==64 and ref.hash:match('^[0-9a-f]+$')~=nil
    and (generations[ref.game]==3 or integer(ref.quadrant or 0,3))
end
function M.validate(row)
  if type(row)~='table' then return nil,'mapping must be a table' end
  if not generations[row.game] or not M.themes[row.style] then return nil,'unknown game or style' end
  if type(row.tileset)~='string' or row.tileset=='' then return nil,'source tileset required' end
  if not integer(row.id,65535) then return nil,'invalid source tile ID' end
  if row.map~=nil and (type(row.map)~='string' or not row.map:match('^[%w_]+$')) then return nil,'invalid source map scope' end
  if generations[row.game]<3 and not integer(row.quadrant,3) then return nil,'GB mapping requires an explicit quadrant' end
  if type(row.role)~='string' or row.role=='' then return nil,'tile meaning required' end
  if row.status~='reviewed' then return nil,'mapping has not been visually reviewed' end
  if type(row.evidence)~='string' or row.evidence=='' then return nil,'review evidence required' end
  if type(row.sourceHash)~='string' or #row.sourceHash~=64 or not row.sourceHash:match('^[0-9a-f]+$') then return nil,'source fingerprint required' end
  local ref=row.donor
  if ref then
    if type(ref)~='table' or not M.donorMatches(row.style,ref.game) then return nil,'donor does not match selected style' end
    if type(ref.tileset)~='string' or ref.tileset=='' or not integer(ref.id,65535) then return nil,'invalid donor tile reference' end
    if generations[ref.game]<3 and not integer(ref.quadrant or 0,3) then return nil,'invalid donor quadrant' end
    if type(ref.hash)~='string' or #ref.hash~=64 or not ref.hash:match('^[0-9a-f]+$') then return nil,'donor fingerprint required' end
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
        or (generations[row.base.game]<3 and not integer(row.base.quadrant or 0,3)) then return nil,'invalid asset ground reference' end
    end
  elseif row.parts then
    if row.kind~='native_composite' then return nil,'native composition origin required' end
    if type(row.parts)~='table' or #row.parts<1 or #row.parts>16 then return nil,'invalid native composition parts' end
    if row.base and not validRef(row.style,row.base) then return nil,'invalid composition ground reference' end
    for _,part in ipairs(row.parts) do
      if type(part)~='table' or not validRef(row.style,part.donor) then return nil,'invalid composition donor' end
      local sx,sy,x,y,w,h=part.srcX or 0,part.srcY or 0,part.x or 0,part.y or 0,part.w,part.h
      if not integer(sx,15) or not integer(sy,15) or not integer(x,15) or not integer(y,15)
        or not integer(w,16) or w==0 or not integer(h,16) or h==0
        or sx+w>16 or sy+h>16 or x+w>16 or y+h>16 then return nil,'composition rectangle exceeds its cell' end
    end
  else return nil,'donor, native composition or original artwork required' end
  if ref and row.asset then return nil,'mapping must have exactly one artwork source' end
  if row.parts and (ref or row.asset) then return nil,'mapping must have exactly one artwork source' end
  if row.animated then
    local animation=row.animation
    if animation then
      if not ref or generations[ref.game]~=3 or type(animation.bank)~='string' or not animation.bank:match('^[%w_]+$')
        or type(animation.hash)~='string' or #animation.hash~=64 or not animation.hash:match('^[0-9a-f]+$')
        or type(animation.manifestHash)~='string' or #animation.manifestHash~=64 or not animation.manifestHash:match('^[0-9a-f]+$') then return nil,'animated tile needs a fingerprint-checked donor bank' end
    elseif not row.frames or #row.frames<2 then return nil,'animated tile needs reviewed animation frames' end
  end
  if row.occludes and not row.foreground then return nil,'occluding tile needs a foreground mask' end
  return true
end
function M.key(row)
  return table.concat({row.game,row.style,row.tileset,tostring(row.id),row.quadrant==nil and '*' or tostring(row.quadrant),row.map or '*'},':')
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
