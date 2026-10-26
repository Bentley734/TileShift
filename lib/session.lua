-- Build only fingerprint-checked, reviewed visual replacements, lazily per
-- tileset. Partial GB blocks are transparent outside reviewed quadrants.
local S={}
function S.new(ctx)
  local mappings, donor, factory=ctx.mappings,ctx.donor,ctx.newImageData
  local themes=ctx.themes or {gen3=3,red=1,blue=1,yellow=1,gold=2,silver=2,crystal=2}
  local function normalizeStyle(style)
    if ctx.normalizeStyle then return ctx.normalizeStyle(style) end
    return ctx.generations[style]==3 and 'gen3' or style
  end
  local warnings,cache={},{}
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
  local function blankBlock()
    return {image=factory(32,32),foreground=factory(32,32),coverage={}}
  end
  local function cloneBlock(block)
    local out=blankBlock()
    out.image:paste(block.image,0,0)
    if block.foreground then out.foreground:paste(block.foreground,0,0) end
    for q,value in pairs(block.coverage or {})do out.coverage[q]=value end
    for _,name in ipairs({'frames','foregroundFrames'})do
      if block[name] then
        out[name]={}
        for i,frame in ipairs(block[name])do
          local copy=factory(32,32);copy:paste(frame,0,0);out[name][i]=copy
        end
      end
    end
    for _,name in ipairs({'period','ticks','bank','counter','offset'})do out[name]=block[name] end
    return out
  end
  function state:select(style)
    style=normalizeStyle(style)
    if style==self.style then return false end
    assert(style=='original' or themes[style],'Unknown TileShift style')
    self.style=style;self.revision=self.revision+1
    cache={};self.accepted=0;self.rejected=0
    donor:invalidate()
    return true
  end
  function state:replacements(game,tileset,def)
    if self.style=='original' or self.style==game
      or (self.style=='gen3' and ctx.generations[game]==3) then return nil end
    local key=table.concat({game,self.style,tileset,def and (def.id or def.name) or ''},':')
    if cache[key] then return cache[key] end
    local rows={};cache[key]=rows
    local applicable={}
    for _,row in pairs(mappings) do
      if type(row)=='table' and row.game==game and row.style==self.style and row.tileset==tileset
        and (row.map==nil or (def and row.map==def.id)) then applicable[#applicable+1]=row end
    end
    -- Context-specific equivalents override a generic reviewed mapping only
    -- in that map. Pairs iteration must never decide which artwork wins.
    table.sort(applicable,function(a,b)
      if (a.x~=nil)~=(b.x~=nil) then return a.x==nil end
      if (a.map~=nil)~=(b.map~=nil) then return a.map==nil end
      if a.id~=b.id then return (tonumber(a.id) or -1)<(tonumber(b.id) or -1) end
      if a.quadrant~=b.quadrant then return (a.quadrant or -1)<(b.quadrant or -1) end
      if a.y~=b.y then return tostring(a.y or '')<tostring(b.y or '') end
      if a.x~=b.x then return tostring(a.x or '')<tostring(b.x or '') end
      return tostring(a.evidence or '')<tostring(b.evidence or '')
    end)
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
          if not base and create then base=blankBlock();rows[row.id]=base end
          if not position or not base then return base end
          if not base.positions then
            if not create then return nil end
            base.positions={}
          end
          local block=base.positions[position]
          if not block and create then block=cloneBlock(base);base.positions[position]=block end
          return block
        end
        if ok and row.animated and (not row.animation or ctx.generations[game]==3) then
          ok=nil;why='Animated donor frames are still awaiting integration for this mapping'
        end
        local source,sourceError
        if ok then
          local generation=ctx.generations[game]
          local sourceRef={game=game,tileset=tileset,id=row.id,quadrant=row.quadrant,
            hash=row.sourceHash,hashOnly=true,map=row.sourceMap,monochrome=true}
          if generation==2 and not sourceRef.map then sourceRef.map=def end
          source,sourceError=tryCall(donor.cell,donor,sourceRef)
        end
        local piece,pieceError,sequence
        if source then
          if row.donor then piece,pieceError=tryCall(donor.cell,donor,row.donor)
          elseif row.parts then
            if ctx.compose then piece,pieceError=tryCall(ctx.compose,row)
            else pieceError='Native composition service is unavailable' end
          elseif row.asset then
            local image,err=tryCall(ctx.original,row.asset,row.assetFileHash)
            if image then
              piece={under=image,over=factory(16,16)}
              if row.base then
                local base,baseError=tryCall(donor.cell,donor,row.base)
                if base then piece={under=copyLayers({under=copyLayers(base),over=image}),over=factory(16,16)}
                else piece=nil;pieceError=baseError end
              end
            else pieceError=err or ('Missing original asset '..row.asset) end
          end
        end
        if piece and row.animated then
          if type(donor.frames)~='function' then piece=nil;pieceError='Donor animation decoder is unavailable'
          else
            sequence,pieceError=tryCall(donor.frames,donor,row.donor,row.animation)
            if sequence and type(sequence.frames)=='table' and #sequence.frames>=2
              and type(sequence.period)=='number' and sequence.period>0 and sequence.period<math.huge then
              piece=sequence.frames[1]
            else piece=nil;pieceError=pieceError or 'Invalid donor animation sequence' end
          end
        end
        if piece and row.foreground and ctx.foreground then
          local foreground,err=tryCall(ctx.foreground,row.foreground)
          piece={under=piece.under,mid=piece.mid,over=piece.over,foreground=foreground}
          if not foreground then piece=nil;pieceError=err end
        end
        if piece and row.foreground and not ctx.foreground then piece=nil;pieceError='Foreground loader is unavailable' end
        if piece and sequence and ctx.generations[game]<3 then
          local block=targetBlock(false)
          if not block and position then block=rows[row.id] end
          if block and block.frames and (block.bank~=sequence.bank or block.period~=sequence.period
            or #block.frames~=#sequence.frames or block.offset~=(sequence.offset or 0)
            or block.counter~=sequence.counter) then
            piece=nil;pieceError='Different animation cycles share one source block'
          end
        end
        if piece then
          if ctx.generations[game]==3 then
            rows[row.id]={under=piece.under,over=piece.over,mid=piece.mid}
          else
            local q=row.quadrant or 0
            local block=targetBlock(true)
            local x,y=q%2*16,math.floor(q/2)*16
            local static=copyLayers(piece)
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
                frame:paste(sequence and copyLayers(sequence.frames[i]) or static,x,y)
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
