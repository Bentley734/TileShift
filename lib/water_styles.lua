-- Retain each reviewed bank's exact land silhouette and native animation.
-- Only water-colored pixels are covered by the selected artist's full-size
-- 16px surface tile. No source map, depth, collision or Surf flags are edited.
local W={}
local rippleHashes={
 '3ff6a61cea580bc856579f1d5dc331dce567a1ec4bee7f85ba5e26511d9c6c17',
 '14658a009e46c7f407f0d6f568d313c1421b0ebce84f19ec98daefd931726316',
 '5caf10de75bda3f8f99384a1fbf909b20c46d9e687550c222ea0dd07a32969ae',
 '313cd2c3ba43e0b6f6d9dc7cd6a051df7ba2952090cddf496d982eb869f3450a',
 'a8d5fe828df89bad15662da8f1e94777102fbe2934dc18d8ff8df4b4a75c7dad',
 '313cd2c3ba43e0b6f6d9dc7cd6a051df7ba2952090cddf496d982eb869f3450a',
 '5caf10de75bda3f8f99384a1fbf909b20c46d9e687550c222ea0dd07a32969ae',
 '14658a009e46c7f407f0d6f568d313c1421b0ebce84f19ec98daefd931726316',
}
function W.new(ctx)
 local sheets,tiles={},{ }
 local function tile(entry,frame)
  local key=entry.id..':'..frame
  if tiles[key] then return tiles[key] end
  local path,hash,w,h
  assert(entry.sheet=='magiscarf','Only animated custom water is selectable')
  path='assets/third_party/magiscarf/water-frame-'..frame..'.png';hash=rippleHashes[frame];w,h=464,208
  if not sheets[path] then
   local image=assert(ctx.image(path,hash))
   local iw,ih=image:getDimensions();assert(iw==w and ih==h,'Water artwork dimensions changed')
   sheets[path]=image
  end
  local out=ctx.newImageData(16,16)
  out:paste(sheets[path],0,0,entry.x,entry.y,16,16)
  tiles[key]=out;return out
 end
 local function flatten(piece)
  local out=ctx.newImageData(16,16)
  for _,name in ipairs({'under','mid','over'})do if piece[name] then
   for y=0,15 do for x=0,15 do
    local r,g,b,a=piece[name]:getPixel(x,y)
    if a>0 then
     local dr,dg,db,da=out:getPixel(x,y);local alpha=a+da*(1-a)
     out:setPixel(x,y,(r*a+dr*da*(1-a))/alpha,(g*a+dg*da*(1-a))/alpha,(b*a+db*da*(1-a))/alpha,alpha)
    end
   end end
  end end
  return out
 end
 local function paint(piece,surface,protected)
  local out=flatten(piece)
  for y=0,15 do for x=0,15 do
   local r,g,b,a=out:getPixel(x,y)
   -- Grey rocks, white foam, grass and brown banks are outside this mask.
   if not protected[y*16+x] and a>0 and b-r>48/255 and b-g>8/255 then
    local sr,sg,sb,sa=surface:getPixel(x,y)
    if sa>0 then out:setPixel(x,y,sr,sg,sb,a) end
   end
  end end
  return {under=out,foreground=piece.foreground}
 end
 local self={}
 function self:finish(entry,piece,sequence,row)
  local protected={}
  -- Original building pixels, including blue glass, are never water pixels.
  if row and row.asset and piece.over then
   for y=0,15 do for x=0,15 do
    local _,_,_,a=piece.over:getPixel(x,y)
    if a>0 then protected[y*16+x]=true end
   end end
  end
  for _,part in ipairs(row and row.parts or {})do
   local source=assert(ctx.donor:cell(part.donor))
   for _,name in ipairs(part.layers or {'under','mid','over'})do
    local layer=source[name]
    if layer then for y=0,part.h-1 do for x=0,part.w-1 do
     local _,_,_,a=layer:getPixel((part.srcX or 0)+x,(part.srcY or 0)+y)
     if a>0 then protected[((part.y or 0)+y)*16+(part.x or 0)+x]=true end
    end end end
   end
  end
  local count=sequence and #sequence.frames or 8
  local frames={}
  for i=1,count do frames[i]=paint(sequence and sequence.frames[i] or piece,
   tile(entry,(i-1)%8+1),protected) end
  local result={frames=frames,period=sequence and sequence.period or .1}
  if sequence then for _,name in ipairs({'ticks','bank','counter','offset'})do result[name]=sequence[name] end end
  return frames[1],result
 end
 return self
end
return W
