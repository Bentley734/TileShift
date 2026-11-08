local root=arg and arg[1]or'.'
local Menu=assert(loadfile(root..'/lib/options_menu.lua'))()
local checks=0
local function check(value,why)checks=checks+1;assert(value,why)end
local function eq(a,b,why)check(a==b,(why or'mismatch')..': '..tostring(a)..' ~= '..tostring(b))end
local versions={red=1,blue=1,yellow=1,gold=2,silver=2,crystal=2,ruby=3,sapphire=3,emerald=3,firered=3,leafgreen=3}
for version,generation in pairs(versions)do
  local parent={options={editing=true},index=7,scroll=3}
  local game={options={existing=true},stack={items={parent}}}
  function game.stack:top()return self.items[#self.items]end
  function game.stack:push(page)self.items[#self.items+1]=page end
  function game.stack:pop()return table.remove(self.items)end
  local requests,callbacks,warnings={},0,{}
  local g1={new=function(g,opts)
    eq(g,game,'native submenu receives the real game');check(type(opts.rows)=='table','fixed rows bypass global hooks')
    return{game=g,rows=opts.rows,view=opts.rows,index=1,scroll=0,sub=true}
  end}
  local g2={}
  local native={_game=game,_pages={{index=4,scroll=2,rows={{id='vanilla'}}}},isOpen=function()return true end}
  local emerald={_st={ctx={game=game},pages={{index=4,scroll=2,rows={{id='vanilla'}}}}},isOpen=function()return true end}
  local modules={['src.ui.OptionsMenu']=g1,['src.ui.gen2.OptionsMenu']=g2,
    ['src.ui.game3.option_menu']=native,['src.ui.game3.rs.option_menu']=native,
    ['src.ui.game3.rse.option_menu']=emerald}
  local active=true
  local menu=Menu.new({generation=generation,version=function()return version end,active=function()return active end,
    require=function(name)requests[#requests+1]=name;return assert(modules[name],name)end,
    warn=function(message)warnings[#warnings+1]=message end})
  local stored={style='ORIGINAL'}
  local function setting(id,label)
    return{id='tileshift:'..id,label=label or id,value=function()return stored[id]or'DEFAULT'end,
      step=function(received,dir)
        eq(received,game,'native callbacks retain the game rather than a GBA context')
        callbacks=callbacks+1;stored[id]=dir;return false
      end}
  end
  local settings={setting('style','MAP STYLE')}
  if generation<3 then
    settings[#settings+1]=setting('center_style','POKEMON CENTERS')
    for _,category in ipairs({'trees','big_trees','cut_trees','flowers','grass','water'})do
      settings[#settings+1]=setting('flora_'..category)
    end
    for _,group in ipairs({'trees','flowers','grass','water'})do settings[#settings+1]=setting('speed_'..group)end
    settings[#settings+1]=setting('grass_motion')
  else
    settings[#settings+1]=setting('speed_flowers')
    settings[#settings+1]=setting('speed_water')
    if version=='ruby'or version=='sapphire'or version=='emerald'then settings[#settings+1]=setting('berry_style')end
  end
  settings[#settings+1]=setting('coverage','MAP TILES')
  local vanilla={id='native',value=function()return'VANILLA'end}
  local foreign={id='another_mod',activate=function()return'OTHER'end}
  local rows={vanilla,foreign}
  eq(menu:append(rows,settings),rows,'append preserves the host list identity')
  eq(#rows,3);eq(rows[1],vanilla);eq(rows[2],foreign);eq(rows[3].id,'tileshift:menu')
  rows[#rows+1]={id='tileshift:style',label='legacy flat row'}
  menu:append(rows,settings);eq(#rows,3,'only one root remains after repeated hooks and legacy flat rows')
  eq(rows[1],vanilla);eq(rows[2],foreign)
  eq(rows[3].label,'TILESHIFT');eq(rows[3].value(),'OPTIONS');eq(callbacks,0,'building the menu changes no preferences')
  local page=rows[3].activate({game=game})
  eq(page.title,'TILESHIFT');eq(page.index,1);eq(page.scroll,0)
  if generation<3 then
    eq(game.stack:top(),page);eq(page.sub,true);eq(page.rows[1].id,'tileshift:style')
    eq(page.rows[1].value(),'ORIGINAL','Original remains directly available')
    eq(#page.rows,5);eq(page.rows[2].id,'tileshift:center_style')
    eq(page.rows[3].id,'tileshift:scenery');eq(#page.rows[3].rows,6)
    eq(page.rows[3].value(),'6 ITEMS')
    eq(page.rows[4].id,'tileshift:animations');eq(#page.rows[4].rows,5)
    eq(page.rows[4].value(),'5 ITEMS')
    eq(page.rows[5].id,'tileshift:coverage')
    if generation==2 then
      eq(getmetatable(page),g2,'Gen2 uses its own native options methods')
      eq(page.options,parent.options,'child pages share the pending native options table')
      eq(#page.view,#page.rows+1);eq(page.view[#page.view].cancel,true);eq(page.view[#page.view].label,'BACK')
    else eq(requests[1],'src.ui.OptionsMenu')end
    local child=page.rows[3].activate(game)
    eq(child.title,'SCENERY');eq(#child.rows,6);eq(game.stack:top(),child)
    eq(child.rows[6].id,'tileshift:flora_water');eq(child.rows[6].step(game,-1),false);eq(stored.flora_water,-1)
    eq(page.rows[4].rows[5].id,'tileshift:grass_motion')
    game.stack:pop();eq(game.stack:top(),page,'closing one group restores its parent')
    game.stack:pop();eq(game.stack:top(),parent);eq(parent.index,7);eq(parent.scroll,3)
    local reopened=rows[3].activate(game)
    eq(#reopened.rows,5,'opening again never duplicates BACK or setting rows')
    if generation==2 then eq(#reopened.view,6)end
    game.stack:pop()
  else
    local expected=version=='ruby'or version=='sapphire'
    local path=expected and'src.ui.game3.rs.option_menu'or version=='emerald'and'src.ui.game3.rse.option_menu'or'src.ui.game3.option_menu'
    eq(requests[1],path,'native GBA host owns the page')
    local pages=version=='emerald'and emerald._st.pages or native._pages
    eq(pages[#pages],page);eq(#pages,2)
    eq(#page.rows,#settings,'small GBA settings remain on one page')
    for _,row in ipairs(page.rows)do eq(row.group,nil,'no empty or two-item category submenu on GBA')end
    eq(page.rows[1].value({game=game}),'ORIGINAL')
    eq(page.rows[1].step({game=game},-1),false);eq(stored.style,-1)
    eq(page.rows[2].step({game=game},1),false);eq(stored.speed_flowers,1)
    table.remove(pages);eq(#pages,1);eq(pages[1].index,4);eq(pages[1].scroll,2)
    native._game={};emerald._st.ctx.game={}
    local no,why=rows[3].activate(game)
    eq(no,nil,'do not attach to a different live game');check(type(why)=='string','unavailable host returns a reason')
    eq(#warnings,1)
  end
  active=false
  local before=#requests
  local no,why=rows[3].activate(game)
  eq(no,nil);eq(why,'TileShift is inactive');eq(#requests,before,'disposed menus never access engine state')
  eq(#settings,generation<3 and 14 or(version=='ruby'or version=='sapphire'or version=='emerald')and 5 or 4)
end
do
  local warnings=0
  local game={stack={push=function()error('unsupported host must not push a broken page')end}}
  local menu=Menu.new({generation=1,require=function()error('missing older engine module')end,
    warn=function()warnings=warnings+1 end})
  local page=menu:open(game,'TILESHIFT',{})
  eq(page,nil);check(warnings>0,'missing native capabilities return safely')
end
print('options submenu checks: '..checks)
