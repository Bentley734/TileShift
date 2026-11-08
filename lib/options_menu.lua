-- TileShift-owned groups on the engine's existing options pages. Child pages
-- never rebuild the global options hook, so other mods retain their own rows.
local M={}
function M.new(ctx)
  assert(type(ctx)=='table'and ctx.generation,'TileShift options need a host generation')
  local engine=ctx.require or require
  local self={}
  local function gameOf(value)return type(value)=='table'and(value.game or value)or value end
  local function nativeRows(rows)
    local result={}
    for _,source in ipairs(rows)do
      local row={id=source.id,label=source.label,group=source.group}
      for _,name in ipairs({'value','step','activate'})do
        local callback=source[name]
        if callback then row[name]=function(c,...)return callback(gameOf(c),...)end end
      end
      result[#result+1]=row
    end
    return result
  end
  local function warn(message)
    if ctx.warn then ctx.warn(message)end
    return nil,message
  end
  local function hostModule(path)
    local ok,result=pcall(engine,path)
    if ok and type(result)=='table'then return result end
    return warn('TileShift options host is unavailable: '..path)
  end
  function self:open(game,title,rows)
    game=gameOf(game)
    if ctx.active and not ctx.active()then return nil,'TileShift is inactive'end
    if not game then return warn('TileShift options have no active game')end
    if ctx.generation==1 then
      if not(game.stack and game.stack.push)then return warn('TileShift options have no menu stack')end
      local host=hostModule('src.ui.OptionsMenu')
      if not host or type(host.new)~='function'then return warn('TileShift options need fixed native submenu rows')end
      local page=host.new(game,{rows=rows})
      page.title=title;game.stack:push(page);return page
    elseif ctx.generation==2 then
      if not(game.stack and game.stack.push and game.stack.top)then return warn('TileShift options have no menu stack')end
      local parent=game.stack:top()
      -- Same data shape as native Gen2 pushGroup; calling new would run every
      -- mod's rows hook again and would replace the requested child rows.
      local host=hostModule('src.ui.gen2.OptionsMenu');if not host then return nil end
      local page=setmetatable({game=game,rows=rows,view={},options=parent and parent.options or game.options,
        index=1,scroll=0,sub=true,title=title},host)
      for i,row in ipairs(rows)do page.view[i]=row end
      page.view[#page.view+1]={id='cancel',label='BACK',cancel=true}
      game.stack:push(page);return page
    end
    local version=ctx.version and ctx.version()or''
    local path=(version=='ruby'or version=='sapphire')and'src.ui.game3.rs.option_menu'
      or version=='emerald'and'src.ui.game3.rse.option_menu'or'src.ui.game3.option_menu'
    local menu=hostModule(path);if not menu then return nil end
    local state=type(menu._st)=='table'and menu._st
    local pages=state and state.pages or menu._pages
    local owner=state and state.ctx and state.ctx.game or menu._game
    local ok,opened=false,false
    if type(menu.isOpen)=='function'then ok,opened=pcall(menu.isOpen)end
    if not(type(pages)=='table'and owner==game and ok and opened)then
      return warn('TileShift options require an active native options page')
    end
    local page={title=title,rows=nativeRows(rows),index=1,scroll=0}
    pages[#pages+1]=page;return page
  end
  local function group(id,label,rows,root)
    return{id='tileshift:'..id,label=label,group=true,rows=rows,
      value=function()return root and'OPTIONS'or tostring(#rows)..' ITEMS'end,
      activate=function(game)return self:open(game,label,rows)end}
  end
  function self:append(out,settings)
    -- Rebuilding an already hooked list must not duplicate this mod's entry,
    -- and legacy flat rows belong inside the same TileShift-owned page.
    for i=#out,1,-1 do
      local id=out[i].id
      if type(id)=='string'and id:match('^tileshift:')then table.remove(out,i)end
    end
    local page={}
    if ctx.generation==3 then
      -- GBA hosts only expose a handful of applicable settings; keep them
      -- together rather than nesting a page for two animation controls.
      for _,row in ipairs(settings)do page[#page+1]=row end
    else
      local scenery,animation={},{}
      local coverage
      for _,row in ipairs(settings)do
        local id=row.id or''
        if id:match('^tileshift:flora_')then scenery[#scenery+1]=row
        elseif id:match('^tileshift:speed_')or id=='tileshift:grass_motion'then animation[#animation+1]=row
        elseif id=='tileshift:coverage'then coverage=row
        else page[#page+1]=row end
      end
      if #scenery>0 then page[#page+1]=group('scenery','SCENERY',scenery)end
      if #animation>0 then page[#page+1]=group('animations','ANIMATIONS',animation)end
      if coverage then page[#page+1]=coverage end
    end
    out[#out+1]=group('menu','TILESHIFT',page,true)
    return out
  end
  return self
end
return M
