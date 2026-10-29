"""Boot TileShift through the actual engine Loader/Sandbox without disk writes.

This checks entry-point compatibility and generation gates. It does not render
maps or claim graphical coverage. A payload can override the source tree's Lua
modules in memory, allowing the installed engine build to be checked directly.
"""
from __future__ import annotations

import argparse
import importlib
import os
from pathlib import Path
import sys
import zipfile

GAMES = ("red", "blue", "yellow", "gold", "silver", "crystal", "ruby",
         "sapphire", "emerald", "firered", "leafgreen")

BOOT = r'''
love=require('tests.love_stub')
bit=require('bit')
if payloadModule then
  local searchers=package.loaders or package.searchers
  table.insert(searchers,2,function(name)
    local source=payloadModule(name)
    if not source then return '\n\tno payload module '..name end
    return assert(loadstring(source,'@payload/'..name:gsub('%.','/')..'.lua'))
  end)
end
local GV=require('src.core.GameVersion');GV.set(selectedVersion)
require('src.core.Version').engine='0.3.97'
local Loader=require('src.mods.Loader')
local Runtime=require('src.mods.Runtime')
local Serializer=require('src.core.SaveSerializer')
local fs={}
function fs.getInfo(path)
  if path=='mods' or path=='mods/tileshift' then return {type='directory'} end
  if modFiles[path] then return {type='file',size=#modFiles[path]} end
  for file in pairs(modFiles)do
    if file:sub(1,#path+1)==path..'/' then return {type='directory'} end
  end
end
function fs.getDirectoryItems(path)
  local result,seen={},{}
  for file in pairs(modFiles)do
    if file:sub(1,#path+1)==path..'/' then
      local name=file:sub(#path+2):match('^[^/]+')
      if name and not seen[name] then result[#result+1]=name;seen[name]=true end
    end
  end
  table.sort(result);return result
end
function fs.read(path)return modFiles[path]end
function fs.write(path,value)modFiles[path]=value;return true end
function fs.createDirectory()return true end
function fs.remove(path)modFiles[path]=nil;return true end
function fs.load(path)return loadstring(modFiles[path] or '')end
-- Loader's own compatibility/UI services import some cross-generation
-- helpers even on a vanilla boot. Audit only additional runtime modules
-- caused by loading this mod; Loader's actual require gate also remains on.
local savedFiles=modFiles;modFiles={}
local baseline=Loader.new({fs=fs,generation=GV.generation(),version=selectedVersion,dev=false})
baseline.game={generation=GV.generation()}
baseline:load({pokemon={},moves={},items={},maps={},tilesets={}})
local preloaded={};for name in pairs(package.loaded)do preloaded[name]=true end
modFiles=savedFiles
local loader=Loader.new({fs=fs,generation=GV.generation(),version=selectedVersion,dev=false})
local host={generation=GV.generation(),options={},save={options={}},mods=loader,
  writeOptions=function()return true end}
loader.game=host
local data={pokemon={},moves={},items={},maps={},tilesets={}}
local before=Serializer.encode(data.maps)
loader:load(data)
local mod=loader.mods.tileshift
assert(mod and mod.state=='loaded',table.concat(loader.errors,'\n'))
assert(#loader.errors==0,table.concat(loader.errors,'\n'))
local exported=assert(loader.exports.tileshift)
assert(exported.state.style=='gen3','fresh boot must enable the implemented Gen3 theme')
assert(exported.select('original'))
local rows=loader.hooks:call('ui.options.rows',function(_,out)return out end,host,{})
local function option(items,id)for _,row in ipairs(items)do if row.id==id then return row end end error('missing option '..id)end
local styleRow=option(rows,'tileshift:style')
assert(styleRow.value()=='ORIGINAL')
assert(rows[#rows].id=='tileshift:coverage' and rows[#rows].value()=='IN PROGRESS')
styleRow.step({game=host},1)
assert(exported.state.style=='gen3','native option step did not select Gen3')
assert(host.options.modOptions.tileshift.style==2,'style selection did not persist')
assert(exported.select('original'))
assert(Serializer.encode(data.maps)==before,'source map registry changed during boot')
-- The native mod manager accepts choice rows, not an enum/values schema.
-- Exercise its actual row builder, persistence, event and live art update.
local Manager=require('src.mods.ManagerState')
local manager=Manager.new(host)
local schema=assert(loader.optionSchemas.tileshift)
local schemaByKey={};for _,row in ipairs(schema)do schemaByKey[row.key]=row end
local gen3=GV.generation()==3
assert(schema[1].type=='choice' and #schema[1].choices==(gen3 and 4 or 2)
 and schema[1].default==2,'implemented mod-manager choice schema missing')
assert(schema[1].choices[1][1]=='ORIGINAL' and schema[1].choices[1][2]==1)
assert(schema[1].choices[2][1]=='GEN 3' and schema[1].choices[2][2]==2)
manager:setOption('tileshift','style',1)
local managerRows=manager:buildOptionRows({id='tileshift'},schema)
assert(managerRows[1].id=='style' and managerRows[1].value()=='ORIGINAL','mod-manager tileset row missing')
managerRows[1].step(host,1)
assert(exported.state.style=='gen3','mod-manager change did not apply art live')
assert(host.save.options.modOptions.tileshift.style==2,'mod-manager choice was not persisted')
assert(managerRows[1].value()=='GEN 3')
if gen3 then
 assert(#schema==3,'Gen3 schema must contain themes and native flower/water speeds')
 for i,entry in ipairs({{'GEN 1',3,'gen1'},{'GEN 2',4,'gen2'},{'ORIGINAL',1,'original'}})do
  managerRows[1].step(host,1)
  assert(managerRows[1].value()==entry[1] and exported.state.style==entry[3],
   'mod-manager reverse theme did not apply live')
  assert(host.save.options.modOptions.tileshift.style==entry[2],
   'mod-manager reverse theme did not retain its stored ID')
 end
 for _,key in ipairs({'center_style','flora_trees','flora_big_trees','flora_cut_trees',
  'flora_flowers','flora_grass','flora_water','speed_trees','speed_grass','grass_motion'})do
  assert(schemaByKey[key]==nil,'Gen3 schema exposed an unsupported custom art option: '..key)
  for _,row in ipairs(rows)do assert(row.id~='tileshift:'..key,'unsupported native Gen3 option: '..key)end
 end
 assert(#rows==4,'Gen3 native hook must have exactly one theme, two speeds and coverage')
else
for i,key in ipairs({'flora_trees','flora_big_trees','flora_cut_trees','flora_flowers','flora_grass','flora_water'})do
 assert(schemaByKey[key]and schemaByKey[key].type=='choice','custom artwork schema missing')
 local beforeRevision=exported.state.revision
 manager:setOption('tileshift',key,3)
 assert(exported.flora.selected[key:sub(7)]=='mixed','custom artwork manager change did not apply')
 assert(exported.state.revision>beforeRevision,'custom artwork did not invalidate cached maps')
 assert(host.save.options.modOptions.tileshift[key]==3,'custom artwork choice did not persist')
 manager:setOption('tileshift',key,1)
end
assert(#schemaByKey.flora_water.choices==6,'Static custom water options must be absent')
assert(schemaByKey.center_style and #schemaByKey.center_style.choices==2,'Compact/expanded Center choices missing')
manager:setOption('tileshift','center_style',1)
assert(host.save.options.modOptions.tileshift.center_style==1,'Compact Center preference did not persist')
manager:setOption('tileshift','center_style',2)
assert(host.save.options.modOptions.tileshift.center_style==2,'Expanded Center preference did not persist')
for value,id in pairs({[6]='ripple-blue',[7]='ripple-teal',[8]='ripple-olive',[4]='default',[5]='default'})do
 manager:setOption('tileshift','flora_water',value)
 assert(exported.flora.selected.water==id,'Existing water preference changed during option removal')
end
manager:setOption('tileshift','flora_water',6)
local waterRow=option(manager:buildOptionRows({id='tileshift'},schema),'flora_water')
assert(waterRow.value()=='1','Sparse stored water IDs are not shown correctly')
waterRow.step(host,1)
assert(exported.flora.selected.water=='ripple-teal' and host.save.options.modOptions.tileshift.flora_water==7,
 'Water step did not retain its existing stored ID')
manager:setOption('tileshift','flora_water',1)
managerRows[1].step(host,-1)
end
assert(exported.state.style=='original','mod-manager return to original did not apply live')
for _,group in ipairs(gen3 and {'flowers','water'}or{'trees','flowers','grass','water'})do
 local key='speed_'..group
 local field=assert(schemaByKey[key],'animation speed schema missing: '..key)
 assert(field.type=='choice'and field.default==3 and #field.choices==4)
 for value,label in ipairs({'OFF','SLOW','NORMAL','FAST'})do
  assert(field.choices[value][1]==label and field.choices[value][2]==value,'speed choices changed stored IDs')
  local revision=exported.state.revision
  manager:setOption('tileshift',key,value)
  assert(option(manager:buildOptionRows({id='tileshift'},schema),key).value()==label,
   'mod-manager speed value did not update')
  assert(host.save.options.modOptions.tileshift[key]==value,'speed choice did not persist')
  assert(exported.state.revision>revision,'speed choice did not invalidate cached art')
 end
 local nativeSpeed=option(rows,'tileshift:'..key)
 assert(nativeSpeed.value()=='FAST')
 nativeSpeed.step({game=host},1)
 assert(nativeSpeed.value()=='OFF'and host.options.modOptions.tileshift[key]==1,
  'native speed Off did not persist')
 manager:setOption('tileshift',key,3)
end
assert(#loader.errors==0,table.concat(loader.errors,'\n'))
assert(Serializer.encode(data.maps)==before,'source maps changed through mod-manager option')
local gen3Rows,gen3Context,skipCart
if GV.generation()==3 then
  -- Actual Rows.build and Rows.withCart both bridge the shared hook.
  -- Skip only ROM-text cart controls in this ROM-free headless boot.
  gen3Rows=require('src.ui.game3.option_rows')
  gen3Context={game=host,session={version=selectedVersion},options=host.options}
  skipCart={textSpeed=true,battleScene=true,battleStyle=true,sound=true,buttonMode=true,frameType=true}
  local function checkNativeRows(native)
    local style,styleCount,reviewCount=nil,0,0
    for _,row in ipairs(native)do
      if row.id=='tileshift:style' then style=row;styleCount=styleCount+1 end
      if row.id=='tileshift:coverage' then reviewCount=reviewCount+1 end
    end
    assert(styleCount==1 and reviewCount==1,'missing or duplicate native Gen3 options')
    assert(style.value(gen3Context)=='ORIGINAL')
    for _,entry in ipairs({{'GEN 3',2,'gen3'},{'GEN 1',3,'gen1'},
     {'GEN 2',4,'gen2'},{'ORIGINAL',1,'original'}})do
     style.step(gen3Context,1)
     assert(style.value(gen3Context)==entry[1]and exported.state.style==entry[3],
      'native Gen3 bridged theme did not execute')
     assert(host.options.modOptions.tileshift.style==entry[2],
      'native Gen3 bridged theme did not persist')
    end
    for _,group in ipairs({'flowers','water'})do
     local speed=option(native,'tileshift:speed_'..group)
     assert(speed.value(gen3Context)=='NORMAL')
     speed.step(gen3Context,1)
     assert(speed.value(gen3Context)=='FAST'and host.options.modOptions.tileshift['speed_'..group]==4,
      'native Gen3 bridged speed did not execute')
     manager:setOption('tileshift','speed_'..group,3)
    end
  end
  checkNativeRows(gen3Rows.build(gen3Context,skipCart))
  checkNativeRows(gen3Rows.withCart(gen3Context,skipCart,function()end))
end
local loaded={}
-- src.render.TextBox deliberately loads the shared Gen2 Chrome helper even
-- under game3; this engine dependency is permitted by the real require gate.
local sharedHelpers={['src.ui.gen2.Chrome']=true}
for name in pairs(package.loaded)do
  local gen2=name:match('^src%.[%w_]+%.gen2%.') or name=='src.core.Game2'
  local gen3=name:match('^src%.[%w_]+%.game3%.') or name=='src.core.Game3'
  assert(preloaded[name] or sharedHelpers[name] or not gen2 or GV.generation()==2,
    'wrong-generation runtime loaded: '..name)
  assert(preloaded[name] or not gen3 or GV.generation()==3,'wrong-generation runtime loaded: '..name)
  if name:match('^src%.') then loaded[#loaded+1]=name end
end
loader.hooks:removeOwner('tileshift');exported.dispose();exported.dispose()
assert(Runtime._tileShiftDispose==nil,'adapter disposal marker retained')
manager:setOption('tileshift','style',2)
assert(exported.state.style=='original','disabled mod retained option event behavior')
if gen3Rows then
  for _,row in ipairs(gen3Rows.build(gen3Context,skipCart))do
    assert(row.id~='tileshift:style' and row.id~='tileshift:coverage',
      'disabled TileShift retained native options')
  end
end
-- A real saved Original choice must win over the fresh-install Gen3 default.
local SaveData=require('src.core.SaveData')
local persisted=SaveData.loadOptions(fs)
persisted.modOptions=persisted.modOptions or {}
persisted.modOptions.tileshift={style=1,flora_water=6}
assert(SaveData.saveOptions(persisted,fs),'in-memory Original preference did not save')
local restoredLoader=Loader.new({fs=fs,generation=GV.generation(),version=selectedVersion,dev=false})
local restoredHost={generation=GV.generation(),options=persisted,save={options=persisted},mods=restoredLoader,
  writeOptions=function()return true end}
restoredLoader.game=restoredHost
local restoredData={pokemon={},moves={},items={},maps={},tilesets={}}
restoredLoader:load(restoredData)
assert(#restoredLoader.errors==0,table.concat(restoredLoader.errors,'\n'))
local restored=assert(restoredLoader.exports.tileshift)
assert(restored.state.style=='original','persisted Original choice was replaced by the fresh default')
assert(restored.flora.selected.water=='ripple-blue','v0.7.0 animated water choice did not survive a fresh Loader boot')
local restoredRows=restoredLoader.hooks:call('ui.options.rows',function(_,out)return out end,restoredHost,{})
assert(option(restoredRows,'tileshift:style').value()=='ORIGINAL')
assert(Serializer.encode(restoredData.maps)==before,'source maps changed on saved-preference reload')
restoredLoader.hooks:removeOwner('tileshift');restored.dispose()
-- The two new stored theme IDs must survive a real SaveData/Loader round trip.
if gen3 then
 for value,expected in pairs({[3]='gen1',[4]='gen2'})do
  persisted.modOptions.tileshift={style=value,speed_flowers=1,speed_water=2}
  assert(SaveData.saveOptions(persisted,fs),'reverse theme preference did not save')
  local reloaded=SaveData.loadOptions(fs)
  local savedLoader=Loader.new({fs=fs,generation=GV.generation(),version=selectedVersion,dev=false})
  local savedHost={generation=GV.generation(),options=reloaded,save={options=reloaded},mods=savedLoader,
   writeOptions=function()return true end}
  savedLoader.game=savedHost
  savedLoader:load({pokemon={},moves={},items={},maps={},tilesets={}})
  assert(#savedLoader.errors==0,table.concat(savedLoader.errors,'\n'))
  local saved=assert(savedLoader.exports.tileshift)
  assert(saved.state.style==expected,'stored reverse theme was replaced by another theme')
  local savedRows=savedLoader.hooks:call('ui.options.rows',function(_,out)return out end,savedHost,{})
  assert(option(savedRows,'tileshift:style').value()==(value==3 and 'GEN 1'or'GEN 2'))
  assert(option(savedRows,'tileshift:speed_flowers').value()=='OFF','saved flower Off was lost')
  assert(option(savedRows,'tileshift:speed_water').value()=='SLOW','saved water speed was lost')
  assert(savedHost.options.modOptions.tileshift.style==value,'saved reverse theme ID changed')
  savedLoader.hooks:removeOwner('tileshift');saved.dispose()
 end
end
return #loaded
'''


def main() -> int:
    mod_root = Path(__file__).resolve().parents[1]
    workspace = mod_root.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", type=Path, default=workspace / ".tools/engine-0395")
    parser.add_argument("--payload", type=Path, help="Optional actual .love payload; no extraction")
    parser.add_argument("--lupa-path", type=Path, default=workspace / ".tools/python")
    parser.add_argument("--games", choices=GAMES, nargs="+", default=GAMES)
    args = parser.parse_args()
    engine = args.engine.resolve()
    if not (engine / "tests/love_stub.lua").is_file():
        parser.error("--engine must contain tests/love_stub.lua")
    if args.lupa_path.is_dir():
        sys.path.insert(0, str(args.lupa_path.resolve()))
    LuaRuntime = importlib.import_module("lupa.luajit21").LuaRuntime
    original_files = {
        "mods/tileshift/" + path.relative_to(mod_root).as_posix(): path.read_text(encoding="utf-8")
        for path in mod_root.rglob("*")
        if path.is_file() and path.suffix in (".lua", ".json") and ".git" not in path.parts
    }
    payload = zipfile.ZipFile(args.payload.resolve()) if args.payload else None
    payload_names = set(payload.namelist()) if payload else set()

    def payload_module(name: str):
        path = name.replace(".", "/") + ".lua"
        return payload.read(path).decode("utf-8") if path in payload_names else None

    original_cwd = Path.cwd()
    failures = []
    try:
        os.chdir(engine)
        for game in args.games:
            lua = LuaRuntime(unpack_returned_tuples=True)
            lua.globals().selectedVersion = game
            lua.globals().modFiles = lua.table_from(original_files)
            if payload:
                lua.globals().payloadModule = payload_module
            try:
                loaded = lua.execute(BOOT)
                print(f"PASS actual Loader/Sandbox {game}: {loaded} engine modules; no map writes", flush=True)
            except Exception as exc:
                failures.append(game)
                print(f"FAIL actual Loader/Sandbox {game}: {exc}", flush=True)
    finally:
        os.chdir(original_cwd)
        if payload:
            payload.close()
    print(f"Booted {len(args.games)} games; {len(failures)} failures; filesystem changes stayed in memory.")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
