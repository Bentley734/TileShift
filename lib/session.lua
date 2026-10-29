-- Build only fingerprint-checked, reviewed visual replacements, lazily per
-- tileset. Partial GB blocks are transparent outside reviewed quadrants.
local S={}
function S.new(ctx)
  local mappings, donor, factory=ctx.mappings,ctx.donor,ctx.newImageData
  local themes=ctx.themes or {gen1=1,gen2=2,gen3=3,red=1,blue=1,yellow=1,gold=2,silver=2,crystal=2}
  local function normalizeStyle(style)
    if ctx.normalizeStyle then return ctx.normalizeStyle(style) end
    return ctx.generations[style]==3 and 'gen3' or style
  end
  local warnings,cache,sourceIdentities={},{},{}
  local empty={}
  local transparentPlane
  local function clearPlane()
    if not transparentPlane then transparentPlane=factory(16,16)end
    return transparentPlane
  end
  local byContext={}
  for _,row in pairs(mappings)do if type(row)=='table' and row.game and row.style and row.tileset then
    local games=byContext[row.game] or {};byContext[row.game]=games
    local styles=games[row.style] or {};games[row.style]=styles
    local bucket=styles[row.tileset] or {generic={},maps={}};styles[row.tileset]=bucket
    local list=bucket.generic
    if row.map then list=bucket.maps[row.map] or {};bucket.maps[row.map]=list end
    list[#list+1]=row
  end end
  local function rowOrder(a,b)
    if (a.x~=nil)~=(b.x~=nil) then return a.x==nil end
    if a.id~=b.id then return (tonumber(a.id) or -1)<(tonumber(b.id) or -1) end
    if a.quadrant~=b.quadrant then return (a.quadrant or -1)<(b.quadrant or -1) end
    if a.y~=b.y then return tostring(a.y or '')<tostring(b.y or '') end
    if a.x~=b.x then return tostring(a.x or '')<tostring(b.x or '') end
    return tostring(a.evidence or '')<tostring(b.evidence or '')
  end
  for _,games in pairs(byContext)do for _,styles in pairs(games)do for _,bucket in pairs(styles)do
    table.sort(bucket.generic,rowOrder)
    for _,list in pairs(bucket.maps)do table.sort(list,rowOrder)end
  end end end

  local state={style='original',revision=0,accepted=0,rejected=0}
  local function warn(message)
    if not warnings[message] then
      warnings[message]=true
      if ctx.warn then ctx.warn(message) end
    end
  end
  local function copyLayers(piece)
    local out=factory(16,16)
    for _,layer in ipairs({'under','mid','over'}) do
      local image=piece[layer]
      if image then
        for y=0,15 do for x=0,15 do
          local r,g,b,a=image:getPixel(x,y)
          if a>0 then
            local dr,dg,db,da=out:getPixel(x,y)
            local alpha=a+da*(1-a)
            out:setPixel(x,y,(r*a+dr*da*(1-a))/alpha,
              (g*a+dg*da*(1-a))/alpha,(b*a+db*da*(1-a))/alpha,alpha)
          end
        end end
      end
    end
    return out
  end
  local function tryCall(fn,...)
    local ok,result,err=pcall(fn,...)
    if not ok then return nil,tostring(result) end
    return result,err
  end
  -- The guarded source has already been decoded with the neutral four-shade
  -- palette. Recolor only once in this cached build, keeping its exact pixels,
  -- alpha and priority planes; no second import or drawing-time work is needed.
  local function recolorSource(source,colors)
    local piece={}
    for _,name in ipairs({'under','mid','over'})do
      local image=source[name]
      if image then
        local w,h=image:getDimensions();assert(w==16 and h==16,'Source palette cell must be16x16')
        local out=factory(16,16)
        for y=0,15 do for x=0,15 do
          local r,g,b,a=image:getPixel(x,y)
          if a>0 then
            assert(math.abs(r-g)<1/510 and math.abs(r-b)<1/510,'Source palette pixels must use neutral shades')
            local shade=math.max(0,math.min(3,math.floor((1-r)*3+.5)))
            local palette=colors[math.floor(y/8)*2+math.floor(x/8)+1]
            local rgb=palette[shade+1]
            out:setPixel(x,y,rgb[1]/255,rgb[2]/255,rgb[3]/255,a)
          else out:setPixel(x,y,r,g,b,a) end
        end end
        piece[name]=out
      end
    end
    assert(piece.under,'Source palette pixels are unavailable')
    piece.foreground=piece.over -- Original GBC priority only, not its optional vegetation stencil.
    return piece
  end
  local function blankBlock()
    return {image=factory(32,32),foreground=factory(32,32),coverage={},vegetation={}}
  end
  local function cloneBlock(block)
    local out=blankBlock()
    out.image:paste(block.image,0,0)
    if block.foreground then out.foreground:paste(block.foreground,0,0) end
    for q,value in pairs(block.coverage or {})do out.coverage[q]=value end
    for q,value in pairs(block.vegetation or {})do out.vegetation[q]=value end
    out.mapId=block.mapId
    for _,name in ipairs({'frames','foregroundFrames'})do
      if block[name] then
        out[name]={}
        for i,frame in ipairs(block[name])do
          local copy=factory(32,32);copy:paste(frame,0,0);out[name][i]=copy
        end
      end
    end
    for _,name in ipairs({'period','ticks','bank','counter','offset'})do out[name]=block[name] end
    if block.cellAnimations then
      out.cellAnimations={}
      for q,sequence in pairs(block.cellAnimations)do out.cellAnimations[q]=sequence end
    end
    return out
  end
  function state:select(style)
    style=normalizeStyle(style)
    if style==self.style then return false end
    assert(style=='original' or themes[style],'Unknown TileShift style')
    self.style=style;self.revision=self.revision+1
    cache={};sourceIdentities={};self.accepted=0;self.rejected=0
    donor:invalidate()
    if ctx.invalidateCustomization then ctx.invalidateCustomization() end
    return true
  end
  function state:invalidate()
    cache={};sourceIdentities={};self.accepted=0;self.rejected=0
    self.revision=self.revision+1;donor:invalidate()
    if ctx.invalidateCustomization then ctx.invalidateCustomization() end
  end
  function state:invalidateVisual()
    cache={};self.accepted=0;self.rejected=0;self.revision=self.revision+1
  end
  -- Polled by the update hook, never by a warm rendering lookup.
  function state:checkSource(game)
    if type(donor.sourceIdentity)=='function'then
      local identity,why=tryCall(donor.sourceIdentity,donor,game)
      local previous=sourceIdentities[game]
      local current=identity or false
      if previous~=nil and previous~=current then
        cache={};self.accepted=0;self.rejected=0;self.revision=self.revision+1
        donor:invalidate()
        if ctx.invalidateCustomization then ctx.invalidateCustomization() end
      end
      sourceIdentities[game]=current
      if not identity then warn('TileShift source import identity is unavailable: '..tostring(why));return false end
    end
    return true
  end
  function state:replacements(game,tileset,def)
    if self.style=='original' or self.style==game
      or (self.style=='gen3' and ctx.generations[game]==3) then return nil end
    local maps=cache[game] and cache[game][tileset]
    local mapKey=def or false
    if maps and maps[mapKey] then return maps[mapKey] end
    if sourceIdentities[game]==nil then self:checkSource(game) end
    if sourceIdentities[game]==false then return empty end
    local games=cache[game]
    if not games then games={};cache[game]=games end
    maps=games[tileset]
    if not maps then maps={};games[tileset]=maps end
    local rows={};maps[mapKey]=rows
    local applicable={}
    local bucket=byContext[game] and byContext[game][self.style] and byContext[game][self.style][tileset]
    if bucket then
      for _,row in ipairs(bucket.generic)do applicable[#applicable+1]=row end
      for _,row in ipairs(bucket.maps[def and def.id] or empty)do applicable[#applicable+1]=row end
    end
    if ctx.customizeRows then applicable=ctx.customizeRows(applicable,game,def) end
    for _,row in ipairs(applicable) do
        local ok,why=ctx.validate(row)
        local position=ok and row.x~=nil and (math.floor(row.x/2)..':'..math.floor(row.y/2)) or nil
        if ok and position then
          if not (def and type(def.width)=='number' and type(def.height)=='number' and type(def.blocks)=='table'
            and row.x<def.width*2 and row.y<def.height*2
            and def.blocks[math.floor(row.y/2)*def.width+math.floor(row.x/2)+1]==row.id) then
            ok=nil;why='Position-scoped source cell no longer matches the map layout'
          end
        end
        local function targetBlock(create)
          local base=rows[row.id]
          if not base and create then base=blankBlock();base.mapId=def and def.id;rows[row.id]=base end
          if not position or not base then return base end
          if not base.positions then
            if not create then return nil end
            base.positions={}
          end
          local block=base.positions[position]
          if not block and create then
            block=cloneBlock(base);base.positions[position]=block
            base.positionRows=base.positionRows or {}
            base.positionRows[math.floor(row.y/2)*def.width+math.floor(row.x/2)]=block
          end
          return block
        end
        if ok and row.animated and not row.animation then
          ok=nil;why='Animated donor frames are still awaiting integration for this mapping'
        end
        local source,sourceError
        if ok then
          local generation=ctx.generations[game]
          local sourceRef={game=game,tileset=tileset,id=row.id,quadrant=row.quadrant,
            hash=row.sourceHash,hashOnly=true,map=row.sourceMap,monochrome=true,sourceFiles=row.sourceFiles}
          if generation==2 and not sourceRef.map then sourceRef.map=def end
          source,sourceError=tryCall(donor.cell,donor,sourceRef)
        end
        local piece,pieceError,sequence
        if source then
          if row.kind=='source_palette' then piece,pieceError=tryCall(recolorSource,source,row.sourceColors)
          elseif row.donor then piece,pieceError=tryCall(donor.cell,donor,row.donor)
          elseif row.parts then
            if row.animated then
              if ctx.composeFrames then
                sequence,pieceError=tryCall(ctx.composeFrames,row)
                if sequence and type(sequence.frames)=='table' and #sequence.frames>=2
                  and type(sequence.period)=='number' and sequence.period>0 and sequence.period<math.huge then
                  piece=sequence.frames[1]
                else sequence=nil;pieceError=pieceError or 'Invalid native composition animation sequence' end
              else pieceError='Native composition animation service is unavailable' end
            elseif ctx.compose then piece,pieceError=tryCall(ctx.compose,row)
            else pieceError='Native composition service is unavailable' end
          elseif row.asset then
            local image,err=tryCall(ctx.original,row.asset,row.assetFileHash)
            if image then
              piece={under=image,over=factory(16,16)}
              if row.base then
                local base,baseError=tryCall(donor.cell,donor,row.base)
                if base then
                  if row.animated then
                    local native,err=tryCall(donor.frames,donor,row.base,row.animation)
                    if native and type(native.frames)=='table' and #native.frames>=2
                      and type(native.period)=='number' and native.period>0 and native.period<math.huge then
                      if row.assetFrames and #row.assetFrames~=#native.frames then
                        piece=nil;pieceError='Original overlay frame count differs from its native water bank'
                      else
                        sequence={frames={}}
                        for key,value in pairs(native)do if key~='frames'then sequence[key]=value end end
                        for i,frame in ipairs(native.frames)do
                          local overlay=image
                          if row.assetFrames and i>1 then
                            local ref=row.assetFrames[i];overlay,err=tryCall(ctx.original,ref.asset,ref.hash)
                          end
                          if not overlay then piece=nil;sequence=nil;pieceError=err or'Missing overlay animation frame';break end
                          sequence.frames[i]={under=copyLayers(frame),over=overlay}
                        end
                        if sequence then piece=sequence.frames[1]end
                      end
                    else piece=nil;pieceError=err or 'Invalid original asset background animation' end
                  else piece={under=copyLayers({under=copyLayers(base),over=image}),over=factory(16,16)} end
                else piece=nil;pieceError=baseError end
              end
            else pieceError=err or ('Missing original asset '..row.asset) end
          end
        end
        if piece and row.animated and not row.parts and not row.asset then
          if type(donor.frames)~='function' then piece=nil;pieceError='Donor animation decoder is unavailable'
          else
            sequence,pieceError=tryCall(donor.frames,donor,row.donor,row.animation)
            if sequence and type(sequence.frames)=='table' and #sequence.frames>=2
              and type(sequence.period)=='number' and sequence.period>0 and sequence.period<math.huge then
              piece=sequence.frames[1]
            else piece=nil;pieceError=pieceError or 'Invalid donor animation sequence' end
          end
        end
        if piece and row.artOverlay then
          local image,err=tryCall(ctx.original,row.artOverlay.asset,row.artOverlay.hash)
          if image and (row.base or row.artOverlay.mode=='over') then
            local original=copyLayers(piece)
            local ground,why
            if row.artOverlay.mode=='over'then ground=original
            else
              local base; base,why=tryCall(donor.cell,donor,row.base)
              if base then ground=copyLayers(base)end
            end
            if ground then
              local final=copyLayers({under=ground,over=image})
              for _,rect in ipairs(row.artOverlay.preserveRects)do
                final:paste(original,rect[1],rect[2],rect[1],rect[2],rect[3],rect[4])
              end
              piece={under=final};sequence=nil
            else piece=nil;pieceError=why end
          else piece=nil;pieceError=err or 'Original artwork overlay requires a reviewed native ground' end
        end
        if piece and row._floraEntry and row._floraCategory~='water' and ctx.floraPiece then
          local ok,custom,frames=pcall(ctx.floraPiece,row)
          if ok then piece,sequence=custom,frames
          else piece=nil;sequence=nil;pieceError=tostring(custom) end
        end
        if piece and row.foreground and ctx.foreground and (not row._floraEntry or row._floraCategory=='water') then
          local foreground,err=tryCall(ctx.foreground,row.foreground)
          piece={under=piece.under,mid=piece.mid,over=piece.over,foreground=foreground}
          if not foreground then piece=nil;pieceError=err end
        end
        if piece and row.foreground and not ctx.foreground and not row._floraEntry then piece=nil;pieceError='Foreground loader is unavailable' end
        if piece and ctx.finishPiece and row._floraCategory=='water' then
          local ok,custom,frames=pcall(ctx.finishPiece,row,piece,sequence)
          if ok then piece,sequence=custom,frames else piece=nil;pieceError=tostring(custom) end
        end
        if piece and ctx.decorateVegetation then
          piece,sequence=ctx.decorateVegetation(row,piece,sequence)
        end
        if piece and sequence and ctx.animationTiming and ctx.generations[game]~=3 then sequence=ctx.animationTiming(row,sequence) end
        if piece then
          if ctx.generations[game]==3 then
            -- The native atlas already composites its middle plane. Retheme
            -- the complete16px image and explicitly clear unused native planes.
            local overPixels={}
            for y=0,15 do for x=0,15 do
              local selected=row.overMask and row.overMask:sub(y*16+x+1,y*16+x+1)=='1'
              if row.overMask==nil and source.over then
                local _,_,_,alpha=source.over:getPixel(x,y);selected=alpha>0
              end
              if selected then overPixels[#overPixels+1]={x,y}end
            end end
            local function planes(frame)
              local image=copyLayers(frame)
              local over=clearPlane()
              if #overPixels>0 then
                over=factory(16,16)
                for _,point in ipairs(overPixels)do
                  over:setPixel(point[1],point[2],image:getPixel(point[1],point[2]))
                end
              end
              return {under=image,over=over,mid=clearPlane()}
            end
            local replacement=planes(piece)
            if sequence then
              replacement.frames={}
              for i,frame in ipairs(sequence.frames)do replacement.frames[i]=planes(frame)end
              replacement.period=sequence.period;replacement.offset=sequence.offset or 0
              replacement.category=row.animationCategory or (row.animation and row.animation.bank=='flower'and'flowers'or'water')
            end
            rows[row.id]=replacement
          else
            local q=row.quadrant or 0
            local block=targetBlock(true)
            local x,y=q%2*16,math.floor(q/2)*16
            local static=copyLayers(piece)
            local vegetation=ctx.vegetationCategory and ctx.vegetationCategory(row)
            block.vegetation[q]=vegetation
            block.cellAnimations=block.cellAnimations or {}
            block.cellAnimations[q]=nil
            if sequence then
              local cell={frames={},foregroundFrames={},period=sequence.period,offset=sequence.offset or 0,category=vegetation,mapId=block.mapId}
              for i,part in ipairs(sequence.frames)do
                local frame=factory(32,32);frame:paste(copyLayers(part),x,y);cell.frames[i]=frame
                local front=factory(32,32);front:paste(part.foreground or piece.foreground or factory(16,16),x,y)
                cell.foregroundFrames[i]=front
              end
              block.cellAnimations[q]=cell
            end
            if sequence and not block.frames then
              block.frames={}
              for i=1,#sequence.frames do
                local frame=factory(32,32);frame:paste(block.image,0,0)
                block.frames[i]=frame
              end
              block.period,block.ticks,block.bank=sequence.period,sequence.ticks,sequence.bank
              block.counter,block.offset=sequence.counter,sequence.offset or 0
            end
            block.image:paste(static,x,y)
            if block.frames then
              for i,frame in ipairs(block.frames) do
                frame:paste(sequence and copyLayers(sequence.frames[(i-1)%#sequence.frames+1]) or static,x,y)
              end
            end
            block.foreground:paste(piece.foreground or factory(16,16),x,y)
            block.coverage[q]=true
          end
          self.accepted=self.accepted+1
        else
          self.rejected=self.rejected+1
          warn('TileShift skipped '..game..'/'..tileset..'/'..row.id..': '..tostring(why or sourceError or pieceError))
        end
    end
    return rows
  end
  return state
end
return S
