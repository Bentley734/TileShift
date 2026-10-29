-- Render-only overrides of native Gen3 atlas pixels. Map layouts, metatile
-- IDs, collision, attributes, actor priority and event data remain native.
local M = {}
local function isPiece(piece)
  local kind = type(piece)
  if (kind ~= 'table' and kind ~= 'userdata') or type(piece.getDimensions) ~= 'function' then return false end
  local ok,w,h=pcall(piece.getDimensions,piece)
  return ok and w==16 and h==16
end
local function copyPiece(data,x,y,factory)
  local image=factory(16,16);image:paste(data,0,0,x,y,16,16);return image
end
local function finite(n) return type(n)=='number' and n==n and n~=math.huge and n~=-math.huge end
local LAYERS={'under','over','mid'}
local DATA={under='imageData',over='overImageData',mid='midImageData'}
local MIDDLE_IMAGES={'midImage','midImageAlt'}
function M.install(context)
  assert(type(context)=='table' and type(context.replacements)=='function','Gen3 renderer needs explicit replacements')
  local req=context.require or require
  local native=context.native or req('src.core.game3.tileset_native')
  local animation=context.animation or req('src.core.game3.tileset_anim')
  local view=context.view or req('src.core.game3.field_view')
  local factory=context.newImageData or function(w,h)return love.image.newImageData(w,h)end
  local states=setmetatable({},{__mode='k'})
  local hooks,pendingStates,pendingCount={}, {},0
  local stopped,activeDepth=false,0
  local originalFlush,originalMark=native.flush,native.markDirty
  assert(type(originalFlush)=='function' and type(originalMark)=='function','Native atlas upload API unavailable')
  local function version()return type(context.version)=='function'and context.version()or context.version end
  local function revision()return type(context.revision)=='function'and context.revision()or context.revision end
  local function alive(state)
    return state.ts.imageData and(not native._pairs or native._pairs[state.pair]==state.ts)
  end
  local function hook(object,key,make)
    local old=object and object[key]
    if type(old)~='function'then return end
    local wrapped=make(old);object[key]=wrapped
    hooks[#hooks+1]={object=object,key=key,original=old,wrapped=wrapped}
  end
  local function mark(state,layer,row)
    if layer=='mid'then state.midDirty=true
    else
      originalMark(state.ts,layer=='over',row.slot)
      if layer=='over'then state.overDirty=true else state.underDirty=true end
    end
  end
  local function paintRow(state,row,dirty)
    for i=1,3 do
      local layer=LAYERS[i];local image=row[layer]
      if image then
        state.ts[DATA[layer]]:paste(image,row.x,row.y)
        if dirty then mark(state,layer,row)end
      end
    end
  end
  local function restore(state)
    for i=1,#state.list do
      local row=state.list[i]
      for j=1,3 do
        local layer=LAYERS[j]
        if row[layer]then state.ts[DATA[layer]]:paste(row[layer..'Source'],row.x,row.y)end
      end
    end
  end
  local function capture(state)
    for i=1,#state.list do
      local row=state.list[i]
      for j=1,3 do
        local layer=LAYERS[j]
        if row[layer]then row[layer..'Source']:paste(state.ts[DATA[layer]],0,0,row.x,row.y,16,16)end
      end
    end
  end
  local function paint(state,dirty)
    for i=1,#state.list do paintRow(state,state.list[i],dirty)end
  end
  local function uploadMiddle(state)
    if not state.midDirty then return end
    local ts=state.ts
    for _,key in ipairs(MIDDLE_IMAGES)do
      local image=ts[key]
      if image and image.replacePixels then image:replacePixels(ts.midImageData)end
    end
    state.midDirty=false
  end
  local function upload(state)
    if state.underDirty or state.overDirty then
      originalFlush(state.ts,state.underDirty or false,state.overDirty or false)
      state.underDirty,state.overDirty=false,false
    end
    uploadMiddle(state)
  end
  -- FRLG/RSE native animation calls markDirty BEFORE changing RGBA pixels.
  -- Expose only that actual slot/plane; keep its latest native frame separately.
  -- These arrays and row flags are reused, with no frame-time row construction.
  local function expose(state,over,slot)
    if state.depth>0 then return end -- palette transaction already exposed all
    local row=state.bySlot[slot];local layer=over and'over'or'under'
    if not row or not row[layer]or row[layer..'Pending']then return end
    state.ts[DATA[layer]]:paste(row[layer..'Source'],row.x,row.y)
    row[layer..'Pending']=true
    if not row.queued then
      row.queued=true;state.pendingN=state.pendingN+1;state.pending[state.pendingN]=row
    end
    if not state.queued then
      state.queued=true;pendingCount=pendingCount+1;pendingStates[pendingCount]=state
    end
  end
  local function finishState(state)
    local live=alive(state)
    for i=1,state.pendingN do
      local row=state.pending[i]
      for j=1,2 do
        local layer=LAYERS[j]
        if row[layer..'Pending']then
          if live then
            row[layer..'Source']:paste(state.ts[DATA[layer]],0,0,row.x,row.y,16,16)
            -- Native markDirty already recorded the slot; GPU still contains
            -- this same donor frame until native's scheduled flush.
            state.ts[DATA[layer]]:paste(row[layer],row.x,row.y)
          end
          row[layer..'Pending']=false
        end
      end
      row.queued=false;state.pending[i]=nil
    end
    state.pendingN=0;state.queued=false
  end
  local function finishPending()
    local n=pendingCount;pendingCount=0
    for i=1,n do
      local state=pendingStates[i];pendingStates[i]=nil;finishState(state)
    end
  end
  local function unpaint(state)
    if not alive(state)then return end
    restore(state)
    for i=1,#state.list do
      local row=state.list[i]
      for j=1,3 do if row[LAYERS[j]]then mark(state,LAYERS[j],row)end end
    end
    upload(state)
  end
  local function clock()
    local now=context.time and context.time()or(love and love.timer and love.timer.getTime and love.timer.getTime())or 0
    return finite(now)and now or 0
  end
  local function frameIndex(row,now,rate)
    return math.floor(math.max(0,now-row.offset)*rate/row.period)%#row.frames+1
  end
  local function addFrames(state,row,replacement)
    local frames=replacement.frames
    if type(frames)~='table'or #frames<2 or #frames>256 or not finite(replacement.period)or replacement.period<=0 then return end
    local offset=replacement.offset or 0
    if not finite(offset)then return end
    -- Explicit planes must remain consistent across all frames; this avoids
    -- accidentally reviving a native canopy in a transparent donor frame.
    for i=1,#frames do
      if type(frames[i])~='table'then return end
      for j=1,3 do
        local layer=LAYERS[j]
        if row[layer]then if not isPiece(frames[i][layer])then return end
        elseif state.ts[DATA[layer]]and frames[i][layer]~=nil then return end
      end
    end
    row.frames,row.period,row.offset,row.frame=frames,replacement.period,offset,1
    local category=type(replacement.category)=='string'and replacement.category or'water'
    local group=state.groups[category]
    if not group then group={category=category,rows={}};state.groups[category]=group;state.groupList[#state.groupList+1]=group end
    group.rows[#group.rows+1]=row
    for i=1,3 do local layer=LAYERS[i];if row[layer]then row[layer]=frames[1][layer]end end
  end
  local function refresh(ts,pair)
    if not ts or not ts.imageData or not ts.cols or not ts.midToSlot then return end
    local v,rev=version(),revision()
    local replacements,mapRevision=context.replacements(v,pair)
    local state=states[ts]
    if state and state.map==replacements and state.version==v and state.revision==rev and state.mapRevision==mapRevision then return state end
    if state then
      assert(state.depth==0,'Cannot change tile mappings during native palette mutation')
      finishPending();unpaint(state)
    end
    state={ts=ts,pair=pair,version=v,revision=rev,map=replacements,mapRevision=mapRevision,
      list={},bySlot={},groups={},groupList={},pending={},pendingN=0,palettePlans={},depth=activeDepth}
    states[ts]=state
    if type(replacements)=='table'then
      for mid,replacement in pairs(replacements)do
        local slot=type(mid)=='number'and mid>=0 and mid%1==0 and ts.midToSlot[mid]
        if slot~=nil and slot~=false and type(replacement)=='table'then
          local row={slot=slot,x=slot%ts.cols*16,y=math.floor(slot/ts.cols)*16}
          for i=1,3 do
            local layer=LAYERS[i]
            if ts[DATA[layer]]and isPiece(replacement[layer])then
              row[layer]=replacement[layer];row[layer..'Source']=copyPiece(ts[DATA[layer]],row.x,row.y,factory)
            end
          end
          if row.under or row.over or row.mid then
            addFrames(state,row,replacement)
            state.list[#state.list+1]=row;state.bySlot[slot]=row
          end
        end
      end
    end
    paint(state,true);upload(state)
    if state.depth>0 then restore(state)end
    return state
  end
  local function refreshAll()
    for ts,state in pairs(states)do
      if not alive(state)then states[ts]=nil end
    end
    for pair,ts in pairs(native._pairs or{})do refresh(ts,pair)end
    -- Test/custom hosts need not expose the resident-pair registry.
    if not native._pairs then for ts,state in pairs(states)do refresh(ts,state.pair)end end
  end
  local function animate()
    local now
    for _,state in pairs(states)do
      if alive(state)and #state.groupList>0 then
        if now==nil then now=clock()end
        for i=1,#state.groupList do
          local group=state.groupList[i]
          local rate=context.animationSpeed and context.animationSpeed(group.category)or 1
          if not finite(rate)or rate<0 then rate=1 end
          for j=1,#group.rows do
            local row=group.rows[j];local index=rate==0 and 1 or frameIndex(row,now,rate)
            if row.frame~=index then
              row.frame=index;local piece=row.frames[index]
              for k=1,3 do
                local layer=LAYERS[k]
                if row[layer]and row[layer]~=piece[layer]then
                  row[layer]=piece[layer];state.ts[DATA[layer]]:paste(row[layer],row.x,row.y);mark(state,layer,row)
                end
              end
            end
          end
        end
        upload(state)
      end
    end
  end
  -- A vararg continuation preserves native nils/return arity without allocating
  -- the per-call pack table previously created on every animation step.
  local function finishCall(ok,...)
    finishPending()
    if not ok then error((...),0)end
    return ...
  end
  local function protect(original)
    return function(...)return finishCall(pcall(original,...))end
  end
  -- Native palette paint marks dirty AFTER writing. Keep its (infrequent)
  -- full source transaction, including first-load and nested palette calls.
  local function paletteResult(ok,...)
    activeDepth=activeDepth-1
    if stopped then
      for _,state in pairs(states)do state.depth=0 end
      if not ok then error((...),0)end
      return ...
    end
    for _,state in pairs(states)do
      if state.depth>0 then
        state.depth=state.depth-1
        if state.depth==0 and alive(state)then capture(state);paint(state,false)end
      end
    end
    finishPending()
    if not ok then error((...),0)end
    return ...
  end
  local function paletteTransaction(original,key)
    return function(pairOrTs,slot,...)
      if stopped then return original(pairOrTs,slot,...)end
      local ts=type(pairOrTs)=='table'and pairOrTs or(native._pairs and native._pairs[pairOrTs])
      local state=ts and states[ts]
      local index=tonumber(slot)or 0
      if key=='resetSlotPalette'and ts and(not ts.patchedSlots or not ts.patchedSlots[index])then
        return original(pairOrTs,slot,...)
      end
      if state and state.depth==0 and type(native.prepareSlot)=='function'then
        local plan=state.palettePlans[index]
        if not plan then
          local pix=native.prepareSlot(ts,index)
          plan={}
          for i=1,#state.list do
            local row=state.list[i]
            if row.under and pix.under and pix.under.cells and pix.under.cells[row.slot]then
              plan[#plan+1]={slot=row.slot,over=false}
            end
            if row.over and pix.over and pix.over.cells and pix.over.cells[row.slot]then
              plan[#plan+1]={slot=row.slot,over=true}
            end
          end
          state.palettePlans[index]=plan
        end
        -- Native's cached indexed palette membership is stable for this atlas.
        -- Expose affected source planes before palette paint; its later dirty
        -- marks then see the pending flag and cannot erase the new colors.
        for i=1,#plan do expose(state,plan[i].over,plan[i].slot)end
        return finishCall(pcall(original,pairOrTs,slot,...))
      end
      -- First-load/custom hosts without indexed membership use a full source
      -- transaction, including atlases first returned from inside native.get.
      finishPending();activeDepth=activeDepth+1
      for _,item in pairs(states)do
        if alive(item)and #item.list>0 then
          if item.depth==0 then restore(item)end
          item.depth=item.depth+1
        end
      end
      return paletteResult(pcall(original,pairOrTs,slot,...))
    end
  end
  hook(native,'markDirty',function(original)
    return function(ts,over,slot,...)
      local state=states[ts]
      if not stopped and state then expose(state,over,slot)end
      return original(ts,over,slot,...)
    end
  end)
  local function flushed(state,ok,...)
    if ok then state.underDirty,state.overDirty=false,false;uploadMiddle(state)end
    if state.depth>0 then restore(state)end
    if not ok then error((...),0)end
    return ...
  end
  hook(native,'flush',function(original)
    return function(ts,under,over,...)
      local state=states[ts]
      if stopped or not state or #state.list==0 then return original(ts,under,over,...)end
      finishPending()
      if state.depth>0 then capture(state);paint(state,true)end
      return flushed(state,pcall(original,ts,under or state.underDirty,over or state.overDirty,...))
    end
  end)
  hook(native,'get',function(original)
    local function loaded(pair,...)
      local ts=(...)
      if not stopped then refresh(ts,pair)end
      return ...
    end
    return function(pair,...)return loaded(pair,original(pair,...))end
  end)
  for _,key in ipairs({'setSlotPalette','resetSlotPalette'})do hook(native,key,function(original)return paletteTransaction(original,key)end)end
  -- Container calls only invoke these leaf writers. No scanning/copying of
  -- all replacements is needed for step, bindPair or visibility catch-up.
  for _,key in ipairs({'_applyKind','stepRse'})do hook(animation,key,protect)end
  hook(view,'draw',function(original)
    return function(...)
      if not stopped then finishPending();refreshAll();animate()end
      return original(...)
    end
  end)
  refreshAll()
  return function()
    if stopped then return end
    finishPending();stopped=true
    for _,state in pairs(states)do unpaint(state)end
    for i=#hooks,1,-1 do
      local h=hooks[i]
      if h.object[h.key]==h.wrapped then h.object[h.key]=h.original end
    end
  end
end
return M
