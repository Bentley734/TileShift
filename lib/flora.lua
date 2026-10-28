-- Cosmetic options operate only on already reviewed semantic mappings.
local F={}
local roles={boundary_tree='trees',dense_round_tree='trees',forest_boundary_small_tree='trees',
  forest_safari_round_boundary_tree='trees',
  decorative_flower_northwest='flowers',decorative_flower_southeast='flowers',
  tall_grass='grass',forest_tall_grass='grass',cuttable_small_tree='cut_trees'}
roles.cave_native_vertical_waterfall='water'
local treeParts={dense_forest_tree_northwest=0,dense_forest_tree_northeast=1,
  dense_forest_tree_southwest=2,dense_forest_tree_southeast=3}
local function treePart(row)
  return treeParts[row.role] or (type(row.role)=='string' and tonumber(row.role:match('^forest_whole_broadleaf_tree_([0-3])$'))) or nil
end
local function category(row)
  local role=row.role
  if treePart(row)~=nil then return 'big_trees' end
  if (row.parts or row.asset) and row.base and row.animated and row.animation
    and type(row.animation.bank)=='string' and row.animation.bank:find('water',1,true) then return 'water' end
  if type(role)=='string' and (role:match('^coastal_rock_shore_') or role:match('^rocky_coast_')
    or role:match('^freshwater_pond_') or role=='coastal_ocean_water_interior' or role=='cave_plain_water') then return 'water' end
  return roles[role]
end
local function hash(text,seed)
  local value=seed or 1
  for i=1,#text do value=(value*131+text:byte(i))%2147483647 end
  return value
end
local function blend(image,x,y,r,g,b,a)
  local dr,dg,db,da=image:getPixel(x,y)
  local alpha=a+da*(1-a)
  if alpha>0 then image:setPixel(x,y,(r*a+dr*da*(1-a))/alpha,
    (g*a+dg*da*(1-a))/alpha,(b*a+db*da*(1-a))/alpha,alpha) end
end
function F.new(ctx)
  local catalog=assert(ctx.catalog)
  local self={selected={trees='default',big_trees='default',cut_trees='default',flowers='default',grass='default',water='default'},revision=0}
  local seed=math.floor(tonumber(ctx.seed) or 1)%2147483647
  local images,sheets,grounds={},{},{}
  function self:invalidate()grounds={} end
  local speeds={trees=1,flowers=1,grass=1,water=1}
  function self:speed(group,value)
    assert(speeds[group]~=nil,'Unknown animation speed group')
    assert(value==0 or value==.5 or value==1 or value==2,'Unknown animation speed')
    if speeds[group]==value then return false end
    speeds[group]=value;self.revision=self.revision+1;return true
  end
  function self:timing(row,sequence)
    local group=category(row)
    if group=='big_trees' or group=='cut_trees' then group='trees' end
    local rate=speeds[group]
    if not sequence or rate==nil or rate==1 then return sequence end
    local out={} for k,v in pairs(sequence)do out[k]=v end
    if rate==0 then
      out.frames={sequence.frames[1]};out.period=1;out.offset=0
    else out.period=sequence.period/rate;out.offset=(sequence.offset or 0)/rate end
    return out
  end
  function self:choices(category)
    local out={{'DEFAULT','default',1},{'RANDOM','random',2},{'MIXED','mixed',3}}
    for number,entry in ipairs(assert(catalog[category]))do
      out[#out+1]={tostring(number),entry.id,entry.optionValue or #out+1}
    end
    return out
  end
  function self:select(category,value)
    if not self.selected[category] then return nil,'Unknown flora category' end
    local valid=false
    for _,choice in ipairs(self:choices(category))do if choice[2]==value then valid=true;break end end
    if not valid then return nil,'Unknown flora choice' end
    if self.selected[category]==value then return false end
    self.selected[category]=value;self.revision=self.revision+1;return true
  end
  function self:entry(category,key)
    local value=self.selected[category]
    if value=='default' then return category=='big_trees' and catalog.big_trees[1] or nil end
    local entries=catalog[category]
    if value=='random' then return entries[hash(category,seed)%#entries+1] end
    if value=='mixed' then return entries[hash(category..':'..key,seed)%#entries+1] end
    for _,entry in ipairs(entries)do if entry.id==value then return entry end end
  end
  function self:rows(rows,game,def)
    local out,generated,scoped={},{},{}
    local finalGeneric={}
    for _,row in ipairs(rows)do if row.x==nil then finalGeneric[row.id..':'..row.quadrant]=row end end
    local function push(row,isGenerated)
      local target=row.x==nil and out or (isGenerated and generated or scoped)
      target[#target+1]=row
    end
    local bodies,borderBodies={},{}
    local mixed=false
    for _,value in pairs(self.selected)do if value=='mixed' then mixed=true end end
    if mixed and def and def.width and def.height and def.blocks then
      local width,height=def.width*2,def.height*2
      local occupied={}
      local function mark(row,x,y)
        local group=row and category(row)
        local key=y*width+x
        if group and self.selected[group]=='mixed' then
          local marine=group=='water' and not row.role:match('^freshwater_pond_') and (row.role:find('coast',1,true)~=nil
            or row.sourceOceanBounds~=nil or (row.parts and row.animated and row.base))
          occupied[key]={group=group,marine=marine,row=row}
        else occupied[key]=nil end
      end
      -- Resolve actual cells before grouping: dry/scoped overrides break patches.
      for index,id in ipairs(def.blocks)do for q=0,3 do
        mark(finalGeneric[id..':'..q],(index-1)%def.width*2+q%2,
          math.floor((index-1)/def.width)*2+math.floor(q/2))
      end end
      for _,row in ipairs(rows)do if row.x~=nil then mark(row,row.x,row.y) end end
      -- Edge and corner contacts form one area. Row-major anchors are stable
      -- across map rebuilds and do not depend on table iteration order.
      for y=0,height-1 do for x=0,width-1 do
        local key=y*width+x
        if occupied[key] and not bodies[key] then
          local group=occupied[key].group
          local anchor=x..':'..y;local queue={key};local head=1;local ocean=false
          bodies[key]=anchor
          while head<=#queue do
            local point=queue[head];head=head+1
            local px,py=point%width,math.floor(point/width)
            ocean=ocean or occupied[point].marine
            for dy=-1,1 do for dx=-1,1 do if dx~=0 or dy~=0 then
              local nx,ny=px+dx,py+dy;local neighbour=ny*width+nx
              if nx>=0 and nx<width and ny>=0 and ny<height and occupied[neighbour]
                and occupied[neighbour].group==group and not bodies[neighbour] then
                bodies[neighbour]=anchor;queue[#queue+1]=neighbour
              end
            end end end
          end
          if ocean then anchor='world-ocean' end
          for _,point in ipairs(queue)do
            bodies[point]=anchor
            local px,py=point%width,math.floor(point/width)
            if px==0 or py==0 or px==width-1 or py==height-1 then
              local row=occupied[point].row;local border=row.id..':'..row.quadrant
              borderBodies[border]=borderBodies[border] or anchor
            end
          end
        end
      end end
    end
    for _,row in ipairs(rows)do
      local group=category(row)
      local value=group and self.selected[group]
      if not group or (value=='default' and group~='big_trees') then push(row)
      else
        local function append(x,y)
          local copy={} for k,v in pairs(row)do copy[k]=v end
          if x~=nil then copy.map=def.id;copy.x=x;copy.y=y end
          local key=game..':'..tostring(def and def.id or row.map)..':'..tostring(x or row.id)..':'..tostring(y or row.quadrant)
          if group=='big_trees' then
            local quadrant=assert(treePart(row))
            key=game..':'..tostring(def and def.id or row.map)..':'..
              tostring(x and x-quadrant%2 or 'border')..':'..tostring(y and y-math.floor(quadrant/2) or 'border')
          end
          if value=='mixed' and def then
            local body=x~=nil and bodies[y*def.width*2+x] or borderBodies[row.id..':'..row.quadrant]
            if not body and group=='water' and (row.role:find('coast',1,true) or row.sourceOceanBounds) then body='world-ocean' end
            key=body=='world-ocean' and 'connected-world-ocean' or
              game..':'..def.id..':'..group..':'..tostring(body or 'border')
          end
          -- Falls connect the upper/lower water body and follow water timing,
          -- while retaining the native lip, vertical flow and bottom foam.
          if row.role~='cave_native_vertical_waterfall'then
            copy._floraEntry=self:entry(group,key);copy._floraCategory=group
          end
          push(copy,row.x==nil and x~=nil)
        end
        -- Keep the generic block for border rendering. Positional clones give
        -- each connected area of repeated source blocks its shared Mixed choice.
        append(row.x,row.y)
        if value=='mixed' and row.x==nil and finalGeneric[row.id..':'..row.quadrant]==row
          and def and type(def.blocks)=='table'
          and type(def.width)=='number' and def.width>0 then
          for index,id in ipairs(def.blocks)do if id==row.id then
            local block=index-1
            append(block%def.width*2+row.quadrant%2,
              math.floor(block/def.width)*2+math.floor(row.quadrant/2))
          end end
        end
      end
    end
    -- Every generic quadrant must be complete BEFORE cloning a32px block.
    -- Interleaving generated positions with generic rows left neighbouring
    -- grass quadrants transparent, revealing native GB palette pixels.
    for _,row in ipairs(generated)do out[#out+1]=row end
    for _,row in ipairs(scoped)do out[#out+1]=row end
    return out
  end
  local xs={29,213,396,580,765,948,1131,1315,1497,1680,1863,2045,2228}
  local ys={84,277,467,658,844,1028,1218,1407,1599}
  function self:sprite(entry)
    local size=entry.size or 16
    local cacheKey=entry.id..':'..size
    if images[cacheKey] then return images[cacheKey] end
    if entry.donor or entry.asset then
      local source=entry.donor and assert(ctx.nativeSprite(entry.donor)) or assert(ctx.sheet(entry.asset,entry.hash))
      local w,h=source:getDimensions()
      assert(w==h and size%w==0 and size>=w,'Custom sprite requires native size or integer enlargement')
      local image=source
      if size~=w then
        local factor=size/w;image=ctx.newImageData(size,size)
        for y=0,size-1 do for x=0,size-1 do image:setPixel(x,y,source:getPixel(math.floor(x/factor),math.floor(y/factor))) end end
      end
      images[cacheKey]=image;return image
    end
    local sheet=catalog.sheets[entry.sheet]
    if not sheets[entry.sheet] then
      local image=assert(ctx.sheet(sheet.path,sheet.hash))
      local w,h=image:getDimensions()
      assert(w==2400 and h==1792,'Flora sheet dimensions changed')
      sheets[entry.sheet]=image
    end
    local atlas=sheets[entry.sheet]
    local left,top=xs[entry.column]+2,ys[entry.row]+2
    local image=ctx.newImageData(size,size)
    -- A complete128px interior crop uses exactly8:1 reduction for16px or
    --4:1 for32px. Never fractionally fit a133px presentation square to a tile.
    local factor=128/size;assert(factor>=1 and factor%1==0,'Sprite reduction must use an integer factor')
    local br,bg,bb=atlas:getPixel(left,top)
    for y=0,size-1 do for x=0,size-1 do
      local r,g,b,a=atlas:getPixel(left+x*factor+math.floor(factor/2),top+y*factor+math.floor(factor/2))
      local distance=(r-br)^2+(g-bg)^2+(b-bb)^2
      local pattern=entry.sheet=='natural' and entry.row==2 and (entry.column==2 or entry.column==4)
      if pattern or distance>(45/255)^2 then image:setPixel(x,y,r,g,b,a) end
    end end
    images[cacheKey]=image;return image
  end
  function self:piece(row)
    local entry=row._floraEntry
    if not entry then return nil end
    local sprite=self:sprite(entry)
    local quadrant=row._floraCategory=='big_trees' and assert(treePart(row)) or 0
    local sx,sy=quadrant%2*16,math.floor(quadrant/2)*16
    local baseRef=row.base or catalog.base
    local groundKey=baseRef.game..':'..baseRef.tileset..':'..baseRef.id..':'..baseRef.hash
    if not grounds[groundKey] then grounds[groundKey]=assert(ctx.base(baseRef)) end
    local base=grounds[groundKey]
    local category=row._floraCategory
    local opaquePattern=category=='grass' and entry.sheet=='natural' and entry.row==2 and (entry.column==2 or entry.column==4)
    local grassMask=opaquePattern and row.foreground and assert(ctx.foreground(row.foreground))
    if category=='flowers' or category=='grass' or category=='trees' or category=='big_trees' or category=='cut_trees' then
      local size=select(1,sprite:getDimensions())
      local bottom=-1
      for y=0,size-1 do for x=0,size-1 do local _,_,_,a=sprite:getPixel(x,y);if a>0 then bottom=math.max(bottom,y) end end end
      local tree=category=='trees' or category=='big_trees' or category=='cut_trees'
      local anchored=tree and math.floor(size*.6) or bottom-1
      local frames={}
      for i,offset in ipairs({0,1,0,-1})do
        -- Move complete sprite rows before splitting big trees into quadrants.
        -- Roots and trunks stay fixed; suppress shifts that would clip artwork.
        local wind=ctx.newImageData(size,size)
        for y=0,size-1 do
          local lo,hi=size,-1
          for x=0,size-1 do local _,_,_,a=sprite:getPixel(x,y);if a>0 then lo=math.min(lo,x);hi=math.max(hi,x) end end
          local shift=y>=anchored and 0 or offset
          if category~='grass' and (lo+shift<0 or hi+shift>=size) then shift=0 end
          for x=0,size-1 do
            local r,g,b,a=sprite:getPixel(x,y)
            if a>0 then wind:setPixel((x+shift)%size,y,r,g,b,a) end
          end
        end
        local frame=ctx.newImageData(16,16);frame:paste(base,0,0,0,0,16,16)
        for y=0,15 do for x=0,15 do
          local r,g,b,a=wind:getPixel(sx+x,sy+y)
          if a>0 then blend(frame,x,y,r,g,b,a) end
        end end
        local foreground
        if category=='grass' or category=='flowers' then
          foreground=ctx.newImageData(16,16);foreground:paste(wind,0,8,0,8,16,8)
          if grassMask then
            for y=8,15 do for x=0,15 do
              local shift=y>=anchored and 0 or offset
              local _,_,_,maskAlpha=grassMask:getPixel((x-shift)%16,y)
              local r,g,b,a=wind:getPixel(x,y)
              foreground:setPixel(x,y,r,g,b,a*maskAlpha)
            end end
          end
        end
        frames[i]={under=frame,foreground=foreground}
      end
      return frames[1],{frames=frames,period=tree and .35 or .2,bank='custom_'..category..'_sway',offset=0}
    end
    local out=ctx.newImageData(16,16)
    out:paste(base,0,0,0,0,16,16)
    for y=0,15 do for x=0,15 do
      local r,g,b,a=sprite:getPixel(sx+x,sy+y)
      if a>0 then blend(out,x,y,r,g,b,a) end
    end end
    local foreground
    if row._floraCategory=='grass' then
      if entry.foreground then foreground=assert(ctx.foreground(entry.foreground))
      else foreground=ctx.newImageData(16,16);foreground:paste(sprite,0,8,0,8,16,8) end
    end
    return {under=out,foreground=foreground}
  end
  function self:category(row)return category(row)end
  function self:decorate(row,piece,sequence)
    if category(row)~='flowers' or piece.foreground then return piece,sequence end
    local function front(part)
      local flattened=ctx.newImageData(16,16)
      for _,layer in ipairs({'under','mid','over'})do if part[layer] then
        for y=0,15 do for x=0,15 do
          local r,g,b,a=part[layer]:getPixel(x,y)
          if a>0 then blend(flattened,x,y,r,g,b,a)end
        end end
      end end
      local br,bg,bb=flattened:getPixel(0,0)
      local foreground=ctx.newImageData(16,16)
      for y=8,15 do for x=0,15 do
        local r,g,b,a=flattened:getPixel(x,y)
        if a>0 and (r~=br or g~=bg or b~=bb)then foreground:setPixel(x,y,r,g,b,a)end
      end end
      local out={}for k,v in pairs(part)do out[k]=v end
      out.foreground=foreground;return out
    end
    piece=front(piece)
    if sequence then
      local copy={}for k,v in pairs(sequence)do copy[k]=v end
      copy.frames={};for i,frame in ipairs(sequence.frames)do copy.frames[i]=front(frame)end
      sequence=copy
    end
    return piece,sequence
  end
  function self:finish(row,piece,sequence)
    if row._floraCategory~='water' then return piece,sequence end
    return assert(ctx.water(row._floraEntry,piece,sequence,row))
  end
  return self
end
return F
