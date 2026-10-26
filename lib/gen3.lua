-- Render-only overrides for the native Gen 3 metatile atlas. Runtime map
-- layouts, metatile ids, collision, attributes and events are never changed.
-- replacements(version, pair) returns {[midId] = {under=ImageData?,
-- over=ImageData?, mid=ImageData?}}, mapRevision?. Each piece is 16x16.
-- Native 0.3.96's under atlas already composites BG1; its optional midImage is
-- retained separately too. This adapter updates that texture without inventing
-- an extra world draw pass or treating a middle layer as an overhead layer.
local M = {}
local unpack = table.unpack or unpack
local function pack(...) return {n = select('#', ...), ...} end

local function isPiece(piece)
  local kind = type(piece)
  if (kind ~= 'table' and kind ~= 'userdata') or type(piece.getDimensions) ~= 'function' then
    return false
  end
  local ok, w, h = pcall(piece.getDimensions, piece)
  return ok and w == 16 and h == 16
end

local function copyPiece(data, x, y, factory)
  local piece = factory(16, 16)
  piece:paste(data, 0, 0, x, y, 16, 16)
  return piece
end

function M.install(context)
  assert(type(context) == 'table' and type(context.replacements) == 'function',
    'Gen 3 renderer needs an explicit replacements function')
  local req = context.require or require
  local native = context.native or req('src.core.game3.tileset_native')
  local animation = context.animation or req('src.core.game3.tileset_anim')
  local view = context.view or req('src.core.game3.field_view')
  local factory = context.newImageData or function(w, h)
    return love.image.newImageData(w, h)
  end
  local states = setmetatable({}, {__mode = 'k'})
  local hooks, stopped, activeDepth = {}, false, 0
  local originalFlush = native.flush
  assert(type(originalFlush) == 'function', 'Native tileset flush is unavailable')

  local function version()
    return type(context.version) == 'function' and context.version() or context.version
  end
  local function revision()
    return type(context.revision) == 'function' and context.revision() or context.revision
  end
  local function hook(object, key, make)
    local original = object and object[key]
    if type(original) ~= 'function' then return end
    local wrapped = make(original)
    object[key] = wrapped
    hooks[#hooks + 1] = {object = object, key = key, original = original, wrapped = wrapped}
  end
  local function alive(state)
    local ts = state.ts
    return ts.imageData and (not native._pairs or native._pairs[state.pair] == ts)
  end
  local function eachLayer(state, fn)
    for _, row in pairs(state.rows) do
      local x, y = (row.slot % state.ts.cols) * 16, math.floor(row.slot / state.ts.cols) * 16
      if row.under then fn('under', state.ts.imageData, row, 'under', x, y) end
      if row.over and state.ts.overImageData then
        fn('over', state.ts.overImageData, row, 'over', x, y)
      end
      if row.mid and state.ts.midImageData then
        fn('mid', state.ts.midImageData, row, 'mid', x, y)
      end
    end
  end
  local function restore(state)
    eachLayer(state, function(_, data, row, layer, x, y)
      data:paste(row[layer .. 'Source'], x, y)
    end)
  end
  local function capture(state)
    eachLayer(state, function(_, data, row, layer, x, y)
      row[layer .. 'Source']:paste(data, 0, 0, x, y, 16, 16)
    end)
  end
  local function mark(state, layer, slot)
    -- The native API takes (atlas, over:boolean, slot), not a layer name.
    if layer == 'mid' then state.midDirty = true
    else native.markDirty(state.ts, layer == 'over', slot) end
  end
  local function paint(state)
    eachLayer(state, function(layerName, data, row, layer, x, y)
      data:paste(row[layer], x, y)
      mark(state, layerName, row.slot)
    end)
  end
  local function flags(state)
    local under, over = false, false
    eachLayer(state, function(layer)
      if layer == 'over' then over = true
      elseif layer == 'under' then under = true end
    end)
    return under, over
  end
  local function uploadMiddle(state)
    if not state.midDirty then return end
    local ts = state.ts
    -- Native flush currently supports under and overhead only. Preserve the
    -- texture identity so any existing or future middle batches remain valid.
    for _, key in ipairs({'midImage', 'midImageAlt'}) do
      local image = ts[key]
      if image and image.replacePixels then image:replacePixels(ts.midImageData) end
    end
    state.midDirty = false
  end
  local function upload(state)
    local under, over = flags(state)
    if under or over then originalFlush(state.ts, under, over) end
    uploadMiddle(state)
  end
  local function unpaint(state)
    if not alive(state) then return end
    restore(state)
    eachLayer(state, function(layer, _, row) mark(state, layer, row.slot) end)
    upload(state)
  end

  -- A changing map object must return a new identity or increment a revision.
  -- Both the second return value and context.revision participate in the key.
  local function refresh(ts, pair)
    if not ts or not ts.imageData or not ts.cols or not ts.midToSlot then return end
    local v, rev = version(), revision()
    local replacements, mapRevision = context.replacements(v, pair)
    local state = states[ts]
    if state and state.map == replacements and state.version == v
        and state.revision == rev and state.mapRevision == mapRevision then return state end
    if state then
      assert(state.depth == 0, 'Cannot change tile mappings during native animation')
      unpaint(state)
    end
    state = {ts = ts, pair = pair, version = v, revision = rev,
      map = replacements, mapRevision = mapRevision, rows = {}, depth = activeDepth}
    states[ts] = state
    if type(replacements) == 'table' then
      for mid, replacement in pairs(replacements) do
        local slot = type(mid) == 'number' and mid >= 0 and mid % 1 == 0
          and ts.midToSlot[mid]
        if slot ~= nil and slot ~= false and type(replacement) == 'table' then
          local row = {slot = slot}
          local x, y = (slot % ts.cols) * 16, math.floor(slot / ts.cols) * 16
          if isPiece(replacement.under) then
            row.under = replacement.under
            row.underSource = copyPiece(ts.imageData, x, y, factory)
          end
          if ts.overImageData and isPiece(replacement.over) then
            row.over = replacement.over
            row.overSource = copyPiece(ts.overImageData, x, y, factory)
          end
          if ts.midImageData and isPiece(replacement.mid) then
            row.mid = replacement.mid
            row.midSource = copyPiece(ts.midImageData, x, y, factory)
          end
          if row.under or row.over or row.mid then state.rows[mid] = row end
        end
      end
    end
    paint(state)
    upload(state)
    if state.depth > 0 then restore(state) end
    return state
  end
  local function refreshAll()
    for ts, state in pairs(states) do
      if alive(state) then refresh(ts, state.pair) else states[ts] = nil end
    end
    for pair, ts in pairs(native._pairs or {}) do refresh(ts, pair) end
  end

  -- Native animators keep their current source frame beneath a replacement.
  -- Restore that frame while they run; reapply donor pixels before GPU upload.
  local function transaction(original)
    return function(...)
      if stopped then return original(...) end
      activeDepth = activeDepth + 1
      for _, state in pairs(states) do
        if alive(state) and next(state.rows) then
          if state.depth == 0 then restore(state) end
          state.depth = state.depth + 1
        end
      end
      local result = pack(pcall(original, ...))
      activeDepth = activeDepth - 1
      for _, state in pairs(states) do
        if state.depth > 0 then
          state.depth = state.depth - 1
          if state.depth == 0 and alive(state) then
            capture(state)
            paint(state)
          end
        end
      end
      if not result[1] then error(result[2], 0) end
      return unpack(result, 2, result.n)
    end
  end

  hook(native, 'flush', function(original)
    return function(ts, under, over, ...)
      local state = states[ts]
      if stopped or not state or not next(state.rows) then
        return original(ts, under, over, ...)
      end
      if state.depth > 0 then capture(state) end
      paint(state)
      local forceUnder, forceOver = flags(state)
      local result = pack(pcall(original, ts, under or forceUnder, over or forceOver, ...))
      if result[1] then uploadMiddle(state) end
      if state.depth > 0 then restore(state) end
      if not result[1] then error(result[2], 0) end
      return unpack(result, 2, result.n)
    end
  end)
  hook(native, 'get', function(original)
    return function(pair, ...)
      local result = pack(original(pair, ...))
      if not stopped then refresh(result[1], pair) end
      return unpack(result, 1, result.n)
    end
  end)
  for _, key in ipairs({'setSlotPalette', 'resetSlotPalette'}) do hook(native, key, transaction) end
  for _, key in ipairs({'bindPair', '_applyKind', 'step', 'stepRse', 'setVisiblePairs'}) do
    hook(animation, key, transaction)
  end
  hook(view, 'draw', function(original)
    return function(...)
      if not stopped then refreshAll() end
      return original(...)
    end
  end)
  refreshAll()

  return function()
    if stopped then return end
    stopped = true
    for _, state in pairs(states) do unpaint(state) end
    for i = #hooks, 1, -1 do
      local entry = hooks[i]
      if entry.object[entry.key] == entry.wrapped then entry.object[entry.key] = entry.original end
    end
  end
end

return M
