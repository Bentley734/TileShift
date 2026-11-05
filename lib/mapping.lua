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
local function assetPath(path,kind)
  if kind~='original' and kind~='third_party' then return false end
  return type(path)=='string' and path:match('^assets/'..kind..'/[%w_/%-%.]+%.png$')~=nil
    and not path:find('..',1,true)
end
local function credited(row)
  return type(row.credit)=='string' and row.credit~=''
    and type(row.sourceUrl)=='string' and row.sourceUrl:match('^https://')~=nil
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
function M.validateClassicGeometry(row)
  local spec=row.classicGeometry
  if generations[row.game]~=3 or row.style~='gen2' or row.kind~='classic_native_geometry'
    or row.donor or row.base or row.parts or row.asset or row.artOverlay or row.foreground
    or row.overMask or row.occludes or row.animated or row.animation or row.frames or row.assetFrames
    or type(spec)~='table' or spec.version~=1 or spec.static~=true
    or type(spec.feature)~='string' or #spec.feature<1 or #spec.feature>96
    or not spec.feature:match('^[%w_%-]+$') or not fingerprint(spec.animationManifestHash)
    or not fingerprint(row.compositionPixelHash) then return nil,'invalid static classic geometry contract' end
  local known={version=true,static=true,feature=true,palette=true,colorMap=true,sourceLayers=true,animationManifestHash=true,ground=true,nativeOver=true,sourceAnimation=true}
  for k in pairs(spec)do if not known[k]then return nil,'unknown classic geometry field' end end
  if not dense(spec.palette,4)then return nil,'classic geometry needs four reviewed RGB8 colors' end
  local palette={}
  for _,rgb in ipairs(spec.palette)do
    if not dense(rgb,3)then return nil,'invalid classic geometry palette' end
    for _,c in ipairs(rgb)do if not integer(c,255)then return nil,'invalid classic geometry palette channel' end end
    local key=rgb[1]*65536+rgb[2]*256+rgb[3]
    if palette[key]then return nil,'duplicate classic geometry palette color' end
    palette[key]=true
  end
  if type(spec.colorMap)~='table' or #spec.colorMap<1 or #spec.colorMap>256
    or not dense(spec.colorMap,#spec.colorMap)then return nil,'invalid classic geometry color map' end
  local used={}
  for _,entry in ipairs(spec.colorMap)do
    if not dense(entry,6)then return nil,'classic geometry color map needs six RGB8 channels' end
    for _,c in ipairs(entry)do if not integer(c,255)then return nil,'invalid classic geometry mapped channel' end end
    local source=entry[1]*65536+entry[2]*256+entry[3]
    if used[source] or not palette[entry[4]*65536+entry[5]*256+entry[6]]then return nil,'duplicate source or unreviewed target color' end
    used[source]=true
  end
  if type(spec.sourceLayers)~='table' or not fingerprint(spec.sourceLayers.under)
    or not fingerprint(spec.sourceLayers.over)then return nil,'classic geometry needs native layer fingerprints' end
  for name,value in pairs(spec.sourceLayers)do
    if(name~='under'and name~='mid'and name~='over')or not fingerprint(value)then return nil,'invalid classic geometry layer fingerprint' end
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
local function validPartDonor(row,part)
  if part.donorStyle==nil then return validRef(row.style,part.donor) end
  -- Explicitly reviewed Red native objects may keep their original monochrome
  -- pixels inside the Crystal theme on GBA hosts. This does not pool themes,
  -- change base/direct donors, or permit a borrowed animation program.
  return part.donorStyle=='gen1' and row.kind=='native_composite'
    and row.style=='gen2' and generations[row.game]==3 and not part.animated
    and type(part.donor)=='table' and part.donor.game=='red'
    and part.donor.kind==nil and validRef('gen1',part.donor)
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
    if type(overlay)~='table' or not assetPath(overlay.asset,overlay.kind or 'original')
      or not fingerprint(overlay.hash)
      or type(overlay.preserveRects)~='table' then return nil,'invalid artwork overlay' end
    if overlay.kind=='third_party' and not credited(row)then return nil,'third-party art requires credit and its source URL' end
    if overlay.mode~=nil and overlay.mode~='over'then return nil,'invalid original overlay mode' end
    for _,rect in ipairs(overlay.preserveRects)do
      if type(rect)~='table' or #rect~=4 or not integer(rect[1],15) or not integer(rect[2],15)
        or not integer(rect[3],16) or not integer(rect[4],16) or rect[3]==0 or rect[4]==0
        or rect[1]+rect[3]>16 or rect[2]+rect[4]>16 then return nil,'invalid retained native rectangle' end
    end
  end
  if row.canopy~=nil then
    local canopy=row.canopy
    if generations[row.game]~=2 or row.style~='gen3' or row.kind~='third_party'
      or row.role~='dense_conifer_crown' or row.x~=nil or row.y~=nil
      or row.donor or row.parts or row.animated or not row.base
      or type(canopy)~='table' or not assetPath(canopy.asset,'third_party')
      or not fingerprint(canopy.hash) or not credited(row)then
      return nil,'tree canopy requires a checked native Gen2 crown and one third-party top tile'
    end
    for name in pairs(canopy)do
      if name~='asset'and name~='hash'then return nil,'unknown tree canopy field'end
    end
  end
  if row.sourceColors~=nil and row.kind~='source_palette' then return nil,'source colors require source palette artwork' end
  local ref=row.donor
  if row.kind=='classic_native_geometry'then
    local ok,why=M.validateClassicGeometry(row);if not ok then return nil,why end
    local nativeOver=row.classicGeometry.nativeOver
    local sourceAnimation=row.classicGeometry.sourceAnimation
    if sourceAnimation~=nil then
      if (row.game~='ruby'and row.game~='sapphire'and row.game~='emerald')
        or type(sourceAnimation)~='table'
        or(sourceAnimation.mode~='water_mask'and sourceAnimation.mode~='native_under'
          and sourceAnimation.mode~='static_equivalent')
        or type(sourceAnimation.bank)~='string'or not sourceAnimation.bank:match('^[%w_]+$')
        or not fingerprint(sourceAnimation.hash)then
        return nil,'classic source animation needs one checked RSE under-only bank'
      end
      for key in pairs(sourceAnimation)do
        if key~='mode'and key~='bank'and key~='hash'then return nil,'unknown classic source animation field'end
      end
      if nativeOver and sourceAnimation.mode~='water_mask'then
        return nil,'retained native foreground can only combine with masked background animation'
      end
    end
    if nativeOver~=nil then
      if(row.game~='ruby'and row.game~='sapphire'and row.game~='emerald')or type(nativeOver)~='table'
        or type(nativeOver.bank)~='string'or not nativeOver.bank:match('^[%w_]+$')or not fingerprint(nativeOver.hash)then
        return nil,'native foreground preservation requires a checked RSE over-only bank'
      end
      for key in pairs(nativeOver)do if key~='bank'and key~='hash'then return nil,'unknown native foreground field'end end
    end
    local ground=row.classicGeometry.ground
    if ground~=nil then
      if type(ground)~='table'or not validRef('gen2',ground.donor)or ground.donor.game~='crystal'
        or type(ground.masks)~='table'then return nil,'classic geometry ground needs one reviewed Crystal donor and explicit native-plane masks'end
      for key in pairs(ground)do
        if key~='donor'and key~='masks'and key~='animation'and key~='repeatWidth'then return nil,'unknown classic geometry ground field'end
      end
      if ground.repeatWidth~=nil and(ground.repeatWidth~=8 or type(ground.animation)~='table'or ground.animation.bank~='program')then
        return nil,'classic animated ground may repeat one complete native eight-pixel column'
      end
      local found=false
      for name,mask in pairs(ground.masks)do
        if not row.classicGeometry.sourceLayers[name]or type(mask)~='string'or #mask~=256 or mask:find('[^01]')then
          return nil,'invalid classic geometry ground mask'
        end
        if mask:find('1',1,true)then found=true end
      end
      if not found then return nil,'classic geometry ground mask is empty'end
      if nativeOver and ground.masks.over then return nil,'native foreground must remain solely owned by its source animation'end
      if sourceAnimation and sourceAnimation.mode~='water_mask'and ground.animation then
        return nil,'classic native source animation cannot also animate its ground'
      end
      if ground.animation~=nil then
        local probe={game=row.game,style=row.style,tileset=row.tileset,id=row.id,sourceHash=row.sourceHash,
          status=row.status,role=row.role,evidence=row.evidence,kind='native_composite',animated=true,
          animation=ground.animation,parts={{donor=ground.donor,animated=true,w=16,h=16,x=0,y=0}}}
        if type(ground.animation)~='table'or ground.animation.kind~='gb'
          or(ground.animation.bank~='water'and ground.animation.bank~='program')then return nil,'classic geometry ground needs a checked native GB water program'end
        local valid,reason=M.validate(probe);if not valid then return nil,reason end
      end
    end
  elseif row.classicGeometry~=nil then return nil,'classic geometry contract requires its explicit artwork kind'
  elseif row.kind=='source_palette' then
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
    if not assetPath(row.asset,row.kind)then return nil,'invalid asset path' end
    if row.kind=='third_party' and not credited(row)then return nil,'third-party art requires credit and its source URL' end
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
      if type(part)~='table' or not validPartDonor(row,part) then return nil,'invalid composition donor' end
      if part.gbForeground~=nil and type(part.gbForeground)~='boolean'then return nil,'invalid GB foreground selection' end
      if part.gbForeground and(generations[part.donor.game]>=3 or part.donor.kind~=nil or part.layers~=nil or part.layerHashes~=nil)then
        return nil,'GB foreground needs a native GB donor without layer selection'
      end
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
    if not row.asset or (row.kind~='original'and row.kind~='third_party')or row.animated~=true or type(row.assetFrames)~='table'
      or #row.assetFrames<2 or #row.assetFrames>16 then return nil,'invalid artwork overlay animation' end
    for key in pairs(row.assetFrames)do
      if not integer(key,#row.assetFrames)or key==0 then return nil,'overlay frames must be a dense array' end
    end
    for i=1,#row.assetFrames do
      local frame=row.assetFrames[i]
      if type(frame)~='table'or not assetPath(frame.asset,row.kind)
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
      if animation.flowDirection~=nil and(animation.bank~='program'or not({north=true,south=true,east=true,west=true})[animation.flowDirection])then
        return nil,'invalid native GB current direction'
      end
      if row.parts then
        local marked
        for _,part in ipairs(row.parts)do if part.animated then animatedRef=part.donor;marked=true;break end end
        if not marked then return nil,'GB animation needs a marked source part' end
      end
      if generations[row.game]~=3 or not animatedRef or generations[animatedRef.game]>=3
        or (animation.bank~='water'and animation.bank~='flower'and animation.bank~='program')
        or (animation.bank=='program'and generations[animatedRef.game]~=2)
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
