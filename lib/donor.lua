-- Decode a reviewed donor cell from another game's version-scoped import.
-- No active cartridge, mount, registry or generation-specific runtime changes.
local Donor={}
local generations={red=1,blue=1,yellow=1,gold=2,silver=2,crystal=2,
  ruby=3,sapphire=3,emerald=3,firered=3,leafgreen=3}
local MONO={{255,255,255},{170,170,170},{85,85,85},{0,0,0}}
local LIMITS={allowArray=true,allowComments=true,maxBytes=8*1024*1024,
  maxDepth=64,maxNodes=500000,maxStringBytes=2*1024*1024,maxTableEntries=250000,
  rootName='donor generated data'}
local function validPart(s)
  return type(s)=='string' and s~='' and s:match('^[%w_%-]+$')~=nil
end
local function integer(n,max)
  return type(n)=='number' and n>=0 and n%1==0 and n<=max
end
local function validateColors(colors)
  assert(type(colors)=='table','Missing donor palette')
  for i=1,4 do
    assert(type(colors[i])=='table','Incomplete donor palette')
    for channel=1,3 do
      local c=colors[i][channel]
      assert(type(c)=='number' and c>=0 and c<=255,'Invalid donor palette color')
    end
  end
  return colors
end
local function copyColors(colors)
  validateColors(colors)
  local out={}
  for i=1,4 do out[i]={colors[i][1],colors[i][2],colors[i][3]} end
  return out
end

function Donor.new(ctx)
  ctx=ctx or {}
  local read=ctx.read or (ctx.fs and ctx.fs.readAt) or require('src.import.CacheFs').readAt
  local decode=ctx.decode or require('src.core.SaveSerializer').decode
  local prefix=ctx.prefix or require('src.core.GameVersion').cachePrefix
  local newData=ctx.newImageData or love.image.newImageData
  local hash=ctx.hash or function(bytes)
    return love.data.encode('string','hex',love.data.hash('sha256',bytes))
  end
  local modules,sheets,packs,animations,objects={},{},{},{},{}
  local self={}
  local function readFile(game,path,optional)
    assert(type(path)=='string' and not path:find('..',1,true) and
      not path:find('[%z\\:]') and path:sub(1,1)~='/','Invalid donor source path')
    local bytes,err=read(prefix(game)..path)
    assert(bytes or optional,'Donor import missing '..game..'/'..path..': '..tostring(err))
    return bytes
  end
  local function module(game,path,optional)
    local key=game..':'..path
    local cached=modules[key]
    if cached then return cached.value,cached.bytes end
    local bytes=readFile(game,path,optional)
    if not bytes then return nil end
    local value,err=decode(bytes,LIMITS)
    assert(type(value)=='table','Invalid donor data '..path..': '..tostring(err))
    modules[key]={value=value,bytes=bytes}
    return value,bytes
  end
  local function sheet(game,path)
    local key=game..':'..path
    local cached=sheets[key]
    if cached then return cached.data,cached.bytes end
    local bytes=readFile(game,path)
    local data=ctx.loadImage and ctx.loadImage(prefix(game)..path,bytes) or newData(prefix(game)..path)
    assert(data and data.getPixel,'Donor image cannot be decoded: '..game..'/'..path)
    sheets[key]={data=data,bytes=bytes}
    return data,bytes
  end
  local function importIdentity(game)
    local marker=readFile(game,'rom-cache.complete',true) or ''
    local meta=generations[game]==3 and (readFile(game,'data/generated/gba/meta.json',true) or '') or ''
    return hash(marker..'\n'..meta)
  end
  local function checkFiles(ref,files)
    if ref.cacheIdentity then
      assert(ref.cacheIdentity==importIdentity(ref.game),'Donor import identity changed')
    end
    for name,expected in pairs(ref.fingerprints or {}) do
      assert(files[name],'Unknown donor fingerprint file: '..tostring(name))
      assert(hash(files[name])==expected,'Donor source changed: '..name)
    end
  end
  local function bytesFor(image)
    if image.getString then return image:getString() end
    local w,h=image:getDimensions();local out={}
    for y=0,h-1 do for x=0,w-1 do
      local r,g,b,a=image:getPixel(x,y)
      out[#out+1]=string.char(math.floor(r*255+.5),math.floor(g*255+.5),
        math.floor(b*255+.5),math.floor((a or 1)*255+.5))
    end end
    return table.concat(out)
  end
  local function palette2(ref,ts)
    local pc=ref.paletteContext or {}
    local selectedMap=ref.map or pc.map
    local def
    if type(selectedMap)=='table' then def=selectedMap
    elseif type(selectedMap)=='string' then
      local maps=module(ref.game,'data/generated/maps.lua')
      def=maps[selectedMap]
      assert(def,'Unknown donor map '..selectedMap)
    end
    if def then assert(def.tileset==ref.tileset,'Donor map uses a different tileset') end
    if ref.palettes then
      for slot=1,8 do validateColors(ref.palettes[slot]) end
      return ref.palettes,def,ref.daytime or pc.daytime or 'DAY'
    end
    assert(def,'Gen 2 donor needs a map or eight explicit palettes')
    local data=module(ref.game,'data/generated/palettes.lua')
    local forced={PALETTE_DAY='DAY',PALETTE_NITE='NITE',PALETTE_MORN='MORN',PALETTE_DARK='DARK'}
    local daytime=ref.daytime or pc.daytime or forced[def.palette] or 'DAY'
    assert(daytime=='DAY' or daytime=='MORN' or daytime=='NITE' or daytime=='DARK',
      'Invalid donor time of day')
    local special=data.specialTilesets and data.specialTilesets[ref.tileset]
    if ref.tileset=='TILESET_ICE_PATH' and def.environment=='INDOOR' then special=nil end
    local result={}
    if special then
      for slot=1,8 do result[slot]=copyColors(special[slot]) end
    else
      local env=data.environments and data.environments[def.environment]
      assert(env,'Donor map environment palette is unavailable')
      local slots=env[daytime]
      assert(slots,'Donor time-of-day palette is unavailable')
      for slot=1,8 do
        result[slot]=copyColors(data.bg and data.bg[slots[slot]])
      end
    end
    if (def.environment=='TOWN' or def.environment=='ROUTE') and data.roofs then
      local roof=data.roofs[def.group]
      if roof then
        local pair=(daytime=='MORN' or daytime=='DAY') and roof.mornDay or roof.nite
        assert(pair and pair[1] and pair[2],'Donor roof colors are unavailable')
        local slot=data.roofSlot or 7
        result[slot][2]={pair[1][1],pair[1][2],pair[1][3]}
        result[slot][3]={pair[2][1],pair[2][2],pair[2][3]}
      end
    end
    return result,def,daytime
  end
  local function attributes(ts,raw)
    -- Matches TileAttrs.forTile, used by the native Gen 2 map bake.
    local attrs=ts.tileAttrs
    local a=attrs and attrs[raw+1]
    if not a and raw<128 then
      local upper=attrs and attrs[raw+129]
      if upper and upper.vramBank==1 then a=upper end
    end
    if a then return a end
    local bank=raw>=128 and raw<224 and 1 or 0
    local palettes=ts.tilePalettes
    local slot=palettes and (palettes[raw+1] or
      (bank==1 and palettes[129+raw%128]) or palettes[raw%128+1]) or 1
    return {palette=slot,vramBank=bank}
  end
  local function gb(ref,gen)
    local sets,setBytes=module(ref.game,'data/generated/tilesets.lua')
    local ts=sets[ref.tileset]
    assert(ts and ts.blocks,'Donor tileset is unavailable: '..ref.tileset)
    local block=ts.blocks[ref.id+1]
    assert(block and #block>=16,'Donor block is unavailable: '..ref.id)
    local atlas,imageBytes=sheet(ref.game,ts.image)
    local aw,ah=atlas:getDimensions()
    local colors,def,daytime
    if ref.hashOnly then
      if gen==2 then colors={MONO,MONO,MONO,MONO,MONO,MONO,MONO,MONO} else colors=MONO end
    elseif gen==2 then colors,def,daytime=palette2(ref,ts)
    else
      colors=(ref.monochrome and MONO) or ref.palette or
        (type(ctx.gen1Palette)=='function' and ctx.gen1Palette(ref)) or ctx.gen1Palette or MONO
      if type(colors)=='string' then
        local data=module(ref.game,'data/generated/palettes.lua')
        colors=data.palettes and data.palettes[colors]
      end
      validateColors(colors)
    end
    local roof
    if gen==2 and def and (ref.tileset=='TILESET_JOHTO' or ref.tileset=='TILESET_JOHTO_MODERN') then
      local roofs=module(ref.game,'data/generated/roofs.lua',true)
      local name=roofs and roofs.mapGroupRoofs and roofs.mapGroupRoofs[def.group]
      local spec=name and roofs.roofs and roofs.roofs[name]
      if spec and spec.image then roof=sheet(ref.game,spec.image) end
    end
    local under,over,foreground,rawImage=newData(16,16),newData(16,16),newData(16,16),newData(16,16)
    local q=ref.quadrant or 0;local qx,qy=q%2*2,math.floor(q/2)*2
    local perRow=ts.tilesPerRow or 16
    for i=0,3 do
      local raw=block[(qy+math.floor(i/2))*4+qx+i%2+1]
      assert(integer(raw,65535),'Invalid donor 8px tile')
      local attr=gen==2 and attributes(ts,raw) or {}
      local actual=raw
      if gen==2 and raw<128 and attr.vramBank==1 then actual=raw+128 end
      local sx,sy=actual%perRow*8,math.floor(actual/perRow)*8
      assert(sx+8<=aw and sy+8<=ah,'Donor source pixels are incomplete')
      local palette=gen==2 and colors[attr.palette or 1] or colors
      validateColors(palette)
      for y=0,7 do for x=0,7 do
        local px,py=attr.xFlip and 7-x or x,attr.yFlip and 7-y or y
        local r,g,b,a=atlas:getPixel(sx+px,sy+py)
        local dx,dy=i%2*8+x,math.floor(i/2)*8+y
        rawImage:setPixel(dx,dy,r,g,b,a)
        if roof and raw>=10 and raw<=18 then r,g,b,a=roof:getPixel((raw-10)*8+px,py) end
        local shade=math.max(0,math.min(3,math.floor((1-r)*3+.5)))
        local col=palette[shade+1]
        local cr,cg,cb=col[1]/255,col[2]/255,col[3]/255
        under:setPixel(dx,dy,cr,cg,cb,a)
        if attr.priority then over:setPixel(dx,dy,cr,cg,cb,a) end
        if shade~=0 then foreground:setPixel(dx,dy,cr,cg,cb,a) end
      end end
    end
    local fingerprint=hash(bytesFor(rawImage))
    checkFiles(ref,{metadata=setBytes,image=imageBytes})
    return {under=under,over=over,foreground=foreground,hash=fingerprint,sourceHash=fingerprint,
      game=ref.game,tileset=ref.tileset,id=ref.id,quadrant=q,daytime=daytime,
      cacheIdentity=importIdentity(ref.game)}
  end
  local function native(ref)
    local key=ref.game..':'..ref.tileset
    local pack=packs[key]
    if not pack then
      local np=ctx.nativePack or require('src.import.gba.native_pack')
      local root='data/generated/gba/native/'..ref.tileset..'/'
      local palBytes=readFile(ref.game,root..'palettes.bin')
      local pals,err=np.decodePalettes(palBytes)
      assert(pals,'Invalid donor native palettes: '..tostring(err))
      local colors=np.palsToRgb8(pals)
      pack={files={['palettes.bin']=palBytes},layers={},slots={}}
      for _,layer in ipairs({'under','mid','over'}) do
        local file=layer=='under' and 'mids.idx' or 'mids_'..layer..'.idx'
        local bytes=readFile(ref.game,root..file,layer~='under')
        if bytes then
          local idx,why=np.decodeIdx(bytes)
          assert(idx,'Invalid donor native layer: '..tostring(why))
          if layer=='under' then
            pack.count=#idx.midIds
            for i,id in ipairs(idx.midIds)do pack.slots[id]=i-1 end
          else
            assert(#idx.midIds==pack.count,'Donor native layer counts disagree')
            for i,id in ipairs(idx.midIds)do
              assert(pack.slots[id]==i-1,'Donor native layer IDs disagree')
            end
          end
          pack.files[file]=bytes
          pack.layers[layer]={idx=idx,colors=colors}
        end
      end
      packs[key]=pack
    end
    checkFiles(ref,pack.files)
    local slot=pack.slots[ref.id]
    assert(slot~=nil,'Donor metatile is unavailable: '..ref.id)
    local result={game=ref.game,tileset=ref.tileset,id=ref.id,cacheIdentity=importIdentity(ref.game)}
    local flattened=newData(16,16)
    for _,layer in ipairs({'under','mid','over'}) do
      local source=pack.layers[layer]
      local image=newData(16,16)
      if source then
        local pixels=source.idx.pixels
        for y=0,15 do for x=0,15 do
          local byte=pixels[slot*256+y*16+x+1]
          assert(byte~=nil,'Donor native pixels are incomplete')
          local c=source.colors[math.floor(byte/16)][byte%16]
          local a=(layer~='under' and byte==0) and 0 or 1
          local r,g,b=c[1]/255,c[2]/255,c[3]/255
          image:setPixel(x,y,r,g,b,a)
          if a==1 then flattened:setPixel(x,y,r,g,b,1) end
        end end
      end
      if layer~='mid' or source then result[layer]=image end
    end
    result.hash=hash(bytesFor(flattened))
    result.sourceHash=result.hash
    return result
  end
  local function fieldObject(ref)
    assert(generations[ref.game]==3 and ref.tileset=='ow' and ref.quadrant==nil,
      'Field-object donor needs a Gen3 ow reference without a quadrant')
    assert(type(ref.metaHash)=='string' and type(ref.rgbaHash)=='string' and type(ref.hash)=='string',
      'Field-object source fingerprints are required')
    local identity=importIdentity(ref.game)
    local key=ref.game..':'..ref.id..':'..identity
    local cached=objects[key]
    if not cached then
      local root='data/generated/gba/ow/'..ref.id
      local meta,rgba=readFile(ref.game,root..'.meta'),readFile(ref.game,root..'.rgba')
      assert(#meta==120 and meta:sub(1,4)=='SVOW','Invalid field-object metadata')
      assert(meta:byte(5)==4,'Unsupported field-object metadata version')
      local function u16(position)return meta:byte(position)+meta:byte(position+1)*256 end
      local id,w,h,frames=u16(7),u16(9),u16(11),u16(13)
      assert(id==ref.id,'Field-object graphics ID changed')
      assert(w==16 and h==16,'Field-object donor must have a complete 16 by 16 pixel canvas')
      assert(integer(frames,256) and frames>0,'Invalid field-object frame count')
      assert(#rgba==w*h*frames*4,'Field-object RGBA pixels are incomplete')
      cached={meta=meta,rgba=rgba,frames=frames};objects[key]=cached
    end
    assert(hash(cached.meta)==ref.metaHash,'Field-object metadata fingerprint changed')
    assert(hash(cached.rgba)==ref.rgbaHash,'Field-object RGBA fingerprint changed')
    checkFiles(ref,{[ref.id..'.meta']=cached.meta,[ref.id..'.rgba']=cached.rgba})
    local frame=ref.frame or 0
    assert(integer(frame,cached.frames-1),'Field-object frame is unavailable')
    local under,over=newData(16,16),newData(16,16)
    local offset=frame*1024
    for y=0,15 do for x=0,15 do
      local i=offset+(y*16+x)*4+1
      under:setPixel(x,y,cached.rgba:byte(i)/255,cached.rgba:byte(i+1)/255,
        cached.rgba:byte(i+2)/255,cached.rgba:byte(i+3)/255)
    end end
    local fingerprint=hash(bytesFor(under))
    return {game=ref.game,tileset=ref.tileset,id=ref.id,kind='field_object',frame=frame,
      under=under,over=over,hash=fingerprint,sourceHash=fingerprint,cacheIdentity=identity}
  end
  function self:cell(ref)
    local ok,result=pcall(function()
      assert(type(ref)=='table' and generations[ref.game],'Unknown donor cartridge')
      assert(validPart(ref.tileset),'Invalid donor tileset')
      assert(integer(ref.id,65535),'Invalid donor tile ID')
      assert(ref.quadrant==nil or integer(ref.quadrant,3),'Invalid donor quadrant')
      assert(ref.kind==nil or ref.kind=='field_object','Unknown donor kind')
      local gen=generations[ref.game]
      local out=ref.kind=='field_object' and fieldObject(ref) or gen==3 and native(ref) or gb(ref,gen)
      assert(not ref.hash or out.hash==ref.hash,'Donor tile fingerprint changed')
      return out
    end)
    if not ok then return nil,tostring(result) end
    return result
  end
  -- Neutral decoder for Emerald indexed and FR/LG RGBA tile-animation banks.
  -- Requested pixels and every source file are verified before publication.
  -- Palette cycling and special scheduling functions remain unsupported.
  function self:frames(ref,spec)
    local ok,result=pcall(function()
      assert(type(ref)=='table' and (ref.game=='emerald' or ref.game=='firered' or ref.game=='leafgreen'),
        'Animated donor cartridge is unsupported')
      assert(type(spec)=='table' and validPart(spec.bank),'Animation bank is required')
      assert(type(spec.hash)=='string' and type(spec.manifestHash)=='string',
        'Animation source fingerprints are required')
      local key=table.concat({ref.game,tostring(ref.tileset),tostring(ref.id),tostring(ref.hash or ''),
        spec.bank,spec.hash,spec.manifestHash,tostring(spec.overHash or '')},':')
      if animations[key] then return animations[key] end
      local base,err=self:cell(ref)
      assert(base,'Animated donor cell is unavailable: '..tostring(err))
      local root='data/generated/gba/native/'..ref.tileset..'/'
      local manifest,manifestBytes=module(ref.game,root..'anim_manifest.lua')
      assert(hash(manifestBytes)==spec.manifestHash,'Animation manifest fingerprint changed')
      if manifest.family~='rse' then
        assert(ref.game=='firered' or ref.game=='leafgreen','Unsupported animation manifest family')
        assert(manifest.family==nil or manifest.family=='frlg','Unsupported animation manifest family')
        -- The native FR/LG scheduler has three fixed timelines. Cache data
        -- with a different frame count would not be a simple repeated cycle.
        local schedules={water={ticks=16,phase=1,frames=8},
          sand={ticks=8,phase=0,frames=8},flower={ticks=16,phase=2,frames=5}}
        local schedule=schedules[spec.bank]
        assert(schedule,'Legacy animation bank is unsupported')
        local bank=manifest[spec.bank]
        assert(type(bank)=='table' and type(bank.mids)=='table','Animation bank is unavailable: '..spec.bank)
        assert(bank.frames==schedule.frames,'Legacy animation frame count is unsupported')
        local selected
        for i,mid in ipairs(bank.mids)do
          if mid==ref.id then assert(not selected,'Duplicate animated metatile');selected=i end
        end
        assert(selected,'Donor metatile is not targeted by animation bank')
        for name in pairs(schedules)do
          if name~=spec.bank then
            for _,mid in ipairs(manifest[name] and manifest[name].mids or {})do
              assert(mid~=ref.id,'Donor metatile uses multiple animation banks')
            end
          end
        end
        local blob=readFile(ref.game,root..'anim_'..spec.bank..'.rgba')
        assert(hash(blob)==spec.hash,'Animation bank fingerprint changed')
        assert(#blob==bank.frames*#bank.mids*16*16*4,'Animation RGBA pixels are incomplete')
        local sequence={frames={},ticks=schedule.ticks,period=schedule.ticks/60,
          phase=schedule.phase,offset=schedule.phase/60,bank=spec.bank,counter='global',
          game=ref.game,tileset=ref.tileset,id=ref.id}
        for frame=0,bank.frames-1 do
          local offset=(frame*#bank.mids+selected-1)*1024
          local under,over=newData(16,16),newData(16,16)
          for y=0,15 do for x=0,15 do
            local i=offset+(y*16+x)*4+1
            under:setPixel(x,y,blob:byte(i)/255,blob:byte(i+1)/255,
              blob:byte(i+2)/255,blob:byte(i+3)/255)
            -- _applyKind writes only the composed under atlas; native BG2
            -- remains the original static over layer for this metatile.
            over:setPixel(x,y,base.over:getPixel(x,y))
          end end
          sequence.frames[#sequence.frames+1]={under=under,over=over}
        end
        animations[key]=sequence
        return sequence
      end
      assert(ref.game=='emerald','RSE animation cartridge is unsupported')
      assert(manifest.family=='rse','Unsupported animation manifest family')
      local bank
      for _,row in ipairs(manifest.banks or {}) do
        if row.name==spec.bank then assert(not bank,'Duplicate animation bank name');bank=row end
      end
      assert(bank,'Animation bank is unavailable: '..spec.bank)
      assert(bank.kind=='tiles','Palette animation banks are unsupported')
      assert(bank.fn=='mod','Animation scheduling function is unsupported')
      assert(integer(bank.frames,256) and bank.frames>=2,'Invalid animation frame count')
      assert(integer(bank.period,65535) and bank.period>0,'Invalid animation period')
      local phase=bank.phase or 0
      assert(integer(phase,bank.period-1),'Invalid animation phase')
      local function indexOf(list,id)
        local result
        for i,mid in ipairs(list or {})do
          if mid==id then assert(not result,'Duplicate animated metatile');result=i end
        end
        return result
      end
      local ui,oi=indexOf(bank.mids,ref.id),indexOf(bank.overMids,ref.id)
      assert(ui or oi,'Donor metatile is not targeted by animation bank')
      -- Combining independent banks or palette timelines would require a
      -- shared native counter model; do not silently freeze the other bank.
      local pack=packs[ref.game..':'..ref.tileset]
      for _,other in ipairs(manifest.banks or {})do
        if other~=bank then
          assert(not indexOf(other.mids,ref.id) and not indexOf(other.overMids,ref.id),
            'Donor metatile uses multiple animation banks')
          if other.kind=='palette' and other.paletteSlot~=nil then
            local sourceSlot=pack.slots[ref.id]
            for name,source in pairs(pack.layers)do
              for i=1,256 do
                local byte=source.idx.pixels[sourceSlot*256+i]
                if not (name~='under' and byte==0) then
                  assert(math.floor(byte/16)~=other.paletteSlot,
                    'Donor metatile also uses an unsupported palette animation')
                end
              end
            end
          end
        end
      end
      local underBlob=bank.file and readFile(ref.game,root..bank.file) or nil
      local overBlob=bank.overFile and readFile(ref.game,root..bank.overFile) or nil
      assert(underBlob or overBlob,'Animation pixels are unavailable')
      assert(hash(underBlob or overBlob)==spec.hash,'Animation bank fingerprint changed')
      if underBlob and overBlob then
        assert(type(spec.overHash)=='string' and hash(overBlob)==spec.overHash,
          'Animation over-layer fingerprint is missing or changed')
      end
      if underBlob then
        assert(#underBlob==bank.frames*#(bank.mids or {})*256,'Animation under pixels are incomplete')
      end
      if overBlob then
        assert(#overBlob==bank.frames*#(bank.overMids or {})*256,'Animation over pixels are incomplete')
      end
      assert(not ui or underBlob,'Animation under pixels are unavailable')
      assert(not oi or overBlob,'Animation over pixels are unavailable')
      local function maskAt(list,index)
        if not index then return 0 end
        local mask=list and list[index] or 15
        assert(integer(mask,15),'Invalid animation quadrant mask')
        return mask
      end
      local underMask,overMask=maskAt(bank.quads,ui),maskAt(bank.overQuads,oi)
      assert(underMask>0 or overMask>0,'Animation bank does not change donor pixels')
      local function clone(image)
        local copy=newData(16,16)
        if image then for y=0,15 do for x=0,15 do copy:setPixel(x,y,image:getPixel(x,y))end end end
        return copy
      end
      local colors=pack.layers.under.colors
      local function patch(image,blob,index,n,frame,mask,over)
        if not index or mask==0 then return end
        local offset=(frame*n+index-1)*256
        for y=0,15 do for x=0,15 do
          local quadrant=math.floor(y/8)*2+math.floor(x/8)
          if math.floor(mask/2^quadrant)%2==1 then
            local byte=blob:byte(offset+y*16+x+1)
            assert(byte~=nil,'Animation pixels are incomplete')
            local palette=colors[math.floor(byte/16)]
            local c=palette and palette[byte%16]
            assert(c and c[1] and c[2] and c[3],'Animation palette is unavailable')
            if over and byte==0 then image:setPixel(x,y,0,0,0,0)
            else image:setPixel(x,y,c[1]/255,c[2]/255,c[3]/255,1) end
          end
        end end
      end
      local sequence={frames={},ticks=bank.period,period=bank.period/60,phase=phase,offset=phase/60,
        bank=spec.bank,counter=bank.counter,game=ref.game,tileset=ref.tileset,id=ref.id}
      for frame=0,bank.frames-1 do
        -- Native under pixels already composite BG1. Keeping a second static
        -- mid layer here would paint old BG1 pixels over the animated result.
        local piece={under=clone(base.under),over=clone(base.over)}
        patch(piece.under,underBlob,ui,#(bank.mids or {}),frame,underMask,false)
        patch(piece.over,overBlob,oi,#(bank.overMids or {}),frame,overMask,true)
        sequence.frames[#sequence.frames+1]=piece
      end
      animations[key]=sequence
      return sequence
    end)
    if not ok then return nil,tostring(result) end
    return result
  end
  function self:invalidate() modules,sheets,packs,animations,objects={},{},{},{},{} end
  return self
end
return Donor
