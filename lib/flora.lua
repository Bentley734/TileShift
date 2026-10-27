-- Cosmetic options operate only on already reviewed semantic mappings.
local F={}
local roles={boundary_tree='trees',dense_round_tree='trees',forest_boundary_small_tree='trees',
  forest_safari_round_boundary_tree='trees',
  decorative_flower_northwest='flowers',decorative_flower_southeast='flowers',
  tall_grass='grass',forest_tall_grass='grass'}
local function category(row)
  local role=row.role
  if row.parts and row.base and row.animated and row.animation
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
function F.new(ctx)
  local catalog=assert(ctx.catalog)
  local self={selected={trees='default',flowers='default',grass='default',water='default'},revision=0}
  local seed=math.floor(tonumber(ctx.seed) or 1)%2147483647
  local images,sheets,ground={},{},nil
  function self:invalidate()ground=nil end
  function self:choices(category)
    local out={{'DEFAULT','default'},{'RANDOM','random'},{'MIXED','mixed'}}
    for _,entry in ipairs(assert(catalog[category]))do out[#out+1]={entry.label,entry.id} end
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
    if value=='default' then return nil end
    local entries=catalog[category]
    if value=='random' then return entries[hash(category,seed)%#entries+1] end
    if value=='mixed' then return entries[hash(category..':'..key,seed)%#entries+1] end
    for _,entry in ipairs(entries)do if entry.id==value then return entry end end
  end
  function self:rows(rows,game,def)
    local out={}
    local bodies={}
    if self.selected.water=='mixed' and def and def.width and def.blocks then
      local occupied={}
      -- Build connected components from the final semantic row per source cell.
      -- Deterministic row-major seeds keep pairs iteration out of the result.
      for _,row in ipairs(rows)do if category(row)=='water' then
        local marine=row.role:find('coast',1,true)~=nil or row.sourceOceanBounds~=nil
          or (row.parts and row.animated and row.base)
        if row.x then occupied[row.y*def.width*2+row.x]={row.x,row.y,marine}
        else for index,id in ipairs(def.blocks)do if id==row.id then
          local x=(index-1)%def.width*2+row.quadrant%2
          local y=math.floor((index-1)/def.width)*2+math.floor(row.quadrant/2)
          occupied[y*def.width*2+x]={x,y,marine}
        end end end
      end end
      local width=def.width*2
      for y=0,(def.height or 0)*2-1 do for x=0,width-1 do
        local key=y*width+x
        if occupied[key] and not bodies[key] then
          local anchor=x..':'..y;local queue={{x,y}};bodies[key]=anchor;local head=1;local ocean=false
          while head<=#queue do
            local point=queue[head];head=head+1
            ocean=ocean or occupied[point[2]*width+point[1]][3]
            for _,offset in ipairs({{-1,0},{1,0},{0,-1},{0,1}})do
              local nx,ny=point[1]+offset[1],point[2]+offset[2]
              local nkey=ny*width+nx
              if nx>=0 and nx<width and ny>=0 and occupied[nkey] and not bodies[nkey] then
                bodies[nkey]=anchor;queue[#queue+1]={nx,ny}
              end
            end
          end
          if ocean then for _,point in ipairs(queue)do bodies[point[2]*width+point[1]]='world-ocean' end end
        end
      end end
    end
    for _,row in ipairs(rows)do
      local group=category(row)
      local value=group and self.selected[group]
      if not group or value=='default' then out[#out+1]=row
      else
        local function append(x,y)
          local copy={} for k,v in pairs(row)do copy[k]=v end
          if x~=nil then copy.map=def.id;copy.x=x;copy.y=y end
          local key=game..':'..tostring(def and def.id or row.map)..':'..tostring(x or row.id)..':'..tostring(y or row.quadrant)
          if group=='water' and def then
            local body=x~=nil and bodies[y*def.width*2+x] or 'border'
            key=body=='world-ocean' and 'connected-world-ocean' or game..':'..def.id..':'..tostring(body)
          end
          copy._floraEntry=self:entry(group,key);copy._floraCategory=group
          out[#out+1]=copy
        end
        -- Keep the generic block for border rendering. Positional clones give
        -- repeated occurrences of one source block independent mixed choices.
        append(row.x,row.y)
        if value=='mixed' and row.x==nil and def and type(def.blocks)=='table'
          and type(def.width)=='number' and def.width>0 then
          for index,id in ipairs(def.blocks)do if id==row.id then
            local block=index-1
            append(block%def.width*2+row.quadrant%2,
              math.floor(block/def.width)*2+math.floor(row.quadrant/2))
          end end
        end
      end
    end
    return out
  end
  local xs={29,213,396,580,765,948,1131,1315,1497,1680,1863,2045,2228}
  local ys={84,277,467,658,844,1028,1218,1407,1599}
  function self:sprite(entry)
    if images[entry.id] then return images[entry.id] end
    local sheet=catalog.sheets[entry.sheet]
    if not sheets[entry.sheet] then
      local image=assert(ctx.sheet(sheet.path,sheet.hash))
      local w,h=image:getDimensions()
      assert(w==2400 and h==1792,'Flora sheet dimensions changed')
      sheets[entry.sheet]=image
    end
    local atlas=sheets[entry.sheet]
    local left,top=xs[entry.column],ys[entry.row]
    local image=ctx.newImageData(16,16)
    -- Nearest sampling is intentionally crisp at the game's native footprint.
    -- Mint backgrounds are removed in the rendering decoder, not painted over.
    local br,bg,bb=atlas:getPixel(left+2,top+2)
    for y=0,15 do for x=0,15 do
      local r,g,b,a=atlas:getPixel(left+math.floor((x+.5)*133/16),top+math.floor((y+.5)*133/16))
      local distance=(r-br)^2+(g-bg)^2+(b-bb)^2
      local pattern=entry.sheet=='natural' and entry.row==2 and (entry.column==2 or entry.column==4)
      if pattern or distance>(45/255)^2 then image:setPixel(x,y,r,g,b,a) end
    end end
    images[entry.id]=image;return image
  end
  function self:piece(row)
    local entry=row._floraEntry
    if not entry then return nil end
    local sprite=self:sprite(entry)
    if not ground then ground=assert(ctx.base(catalog.base)) end
    local base=ground
    local out=ctx.newImageData(16,16)
    for y=0,15 do for x=0,15 do
      local r,g,b,a=sprite:getPixel(x,y)
      if a>0 then out:setPixel(x,y,r,g,b,a)
      else out:setPixel(x,y,base:getPixel(x,y)) end
    end end
    local foreground
    if row._floraCategory=='grass' then
      foreground=ctx.newImageData(16,16)
      foreground:paste(sprite,0,8,0,8,16,8)
    end
    return {under=out,foreground=foreground}
  end
  function self:finish(row,piece,sequence)
    if row._floraCategory~='water' then return piece,sequence end
    return assert(ctx.water(row._floraEntry,piece,sequence,row))
  end
  return self
end
return F
