"""Render all real RSE berry collector frames through the production mod.

Private object pools exercise the native collector/draw function and full
style/source/disposal lifecycle. Imported maps, saves and tree state are never
written. Actual soil/map geometry is checked by the ordinary native map probes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import zipfile
import validate_gpu


BODY=r'''
 report.type='Native RSE berry actor pixel/lifecycle fixtures'
 report.theme='crystal_berry_actors'
 report.limits='Real field_effects_rse.collectActors and native actor draw; private object pools, no saves or interactive growth simulation.'
 local selected=Json.decode(@SELECTION@)
 local Versions=require('src.import.gba.versions')
 local CachePaths=require('src.core.game3.cache_paths')
 local Dataset=require('src.core.game3.dataset')
 local Native=require('src.core.game3.tileset_native')
 local Objects=require('src.core.game3.objects')
 report.expected_fingerprint_rejections={}
 for _,game in ipairs(selected.games)do
  GV.set(game);assetGame=game;clock=0
  local cache={read=function(_,path)return cacheRead(game..'/'..path)end,exists=function(self,path)return self:read(path)~=nil end}
  Versions.selectCache(game,cache);CachePaths.reset();Dataset.cacheRootOverride=nil;Dataset.mountExtractRoots();Native.install(cache)
  -- Each host fixture models a fresh native collector, as at game startup.
  package.loaded['src.core.game3.field_effects_rse']=nil
  local Fx=require('src.core.game3.field_effects_rse')
  require('src.core.game3.field_effects').install(cache)
  local systems=Fx.SYSTEMS;Fx.SYSTEMS={}
  local order,byId=Objects._order,Objects._byId
  local entry=assert(Fx.berryManifest());check(#entry.trees==43,'Native berry variety count changed')
  local eo={px=0,py=16,cellX=0,cellY=1,visible=true,hidden=false,invisible=true,elevation=3,graphicsId=0}
  Objects._order={1};Objects._byId={[1]=eo}
  local function selectCase(berry,frame)
   eo.berryTree={id=1,visible=true,tree=entry.trees[berry],anim={frame=frame,timer=17},gfxKey=berry..':5',animNum=4}
  end
  local function actor()
   local actors={};Fx.collectActors(actors,0,0)
   check(#actors==1,'The private berry object did not produce exactly one native actor')
   return actors[1]
  end
  local function rendered(a)
   return capture(16,32,function()a.draw(a,0,0)end)
  end
  local metadataBefore=tableString(entry)
  local originals={};local originalCollector=Fx.collectActors
  local originalContact=love.image.newImageData(43*16,9*32)
  for berry=1,43 do
   originals[berry]={}
   for frame=0,8 do
    selectCase(berry,frame);originals[berry][frame+1]=rendered(actor())
    originalContact:paste(originals[berry][frame+1],(berry-1)*16,frame*32,0,0,16,32)
   end
  end
  local mod=startMod(game,3)
  local theme=assert(mod.exports.berryTheme,'Production main did not expose the RSE berry adapter')
  mod.game.options={};mod.game.save={options={}};mod.game.mods={modOptions={}}
  local saved={};mod.save.set=function(_,key,value)saved[key]=value end
  local berrySchema
  for _,field in ipairs(mod.options.schema or {})do if field.key=='berry_style'then berrySchema=field end end
  check(berrySchema and berrySchema.default==2 and #berrySchema.choices==2
   and berrySchema.choices[1][1]=='NATIVE'and berrySchema.choices[1][2]==1
   and berrySchema.choices[2][1]=='CRYSTAL'and berrySchema.choices[2][2]==2,'RSE berry option schema/default changed')
  local optionRows=Runtime.hooks:call('ui.options.rows',function(_,out)return out end,mod.game,{})
  local berryRow
  for _,row in ipairs(optionRows)do if row.id=='tileshift:berry_style'then berryRow=row end end
  check(berryRow and berryRow.label=='BERRY TREES'and berryRow.value()=='CRYSTAL','Fresh RSE berries did not default to Crystal')
  check(mod.exports.select('gen2')and theme:prepare(game),'Crystal berry preparation failed')
  local catalog=assert(load(assert(mod:read('lib/berry_catalog.lua'))))()
  local expectedImages={};local contact=love.image.newImageData(43*16,9*32)
  local cases,alphaCounts=0,{}
  local function opaquePixels(image)
   local count=0
   for y=0,image:getHeight()-1 do for x=0,image:getWidth()-1 do
    local _,_,_,a=image:getPixel(x,y);if a>0 then count=count+1 end
   end end
   return count
  end
  for berry=1,43 do
   local asset=catalog.varieties[berry]
   local bytes=assert(mod:read(asset.asset));check(hash(bytes)==asset.hash,'Generated berry asset fingerprint changed')
   expectedImages[berry]=G.newImage(love.image.newImageData(love.filesystem.newFileData(bytes,asset.asset)))
   expectedImages[berry]:setFilter('nearest','nearest')
   for frame=0,8 do
    selectCase(berry,frame)
    local bt=eo.berryTree;local fr=entry.trees[berry].frames[frame+1]
    local a=actor()
    check(a.x==0 and a.y==32-fr.h and a.sortY==16 and a.elevation==3,'Native berry anchor/sort/elevation changed')
    check(bt.anim.frame==frame and bt.anim.timer==17 and bt.tree==entry.trees[berry],'Berry animation or identity changed')
    local actual=rendered(a)
    local q=G.newQuad(0,fr.y,fr.w,fr.h,16,240)
    local expected=capture(16,32,function()G.draw(expectedImages[berry],q,0,32-fr.h)end)
    check(actual:getString()==expected:getString(),'Native berry actor selected wrong pixels: '..game..' '..berry..' frame'..frame)
    local actualAlpha,expectedAlpha=opaquePixels(actual),opaquePixels(expected)
    check(actualAlpha==expectedAlpha and actualAlpha>0,'Berry fixture was blank or lost silhouette pixels')
    alphaCounts[#alphaCounts+1]={berry=berry,frame=frame,actual=actualAlpha,expected=expectedAlpha}
    contact:paste(actual,(berry-1)*16,frame*32,0,0,16,32);cases=cases+1
   end
  end
  local beforeGallery=encodePng(originalContact,game..'-all-43-berry-stages-native.png')
  local gallery=encodePng(contact,game..'-all-43-berry-stages-gen2.png')
  local columns={};for i=1,43 do columns[i]={column=i-1,berry=i,name=catalog.varieties[i].name}end
  local rowNames={'planted','sprout A','sprout B','taller A','taller B','flowering A','flowering B','ripe A','ripe B'}
  local rows={};for i,name in ipairs(rowNames)do rows[i]={row=i-1,frame=i-1,name=name,source_height=i<=3 and 16 or 32}end
  local reads,ownReads,assetReads=importReads,0,0
  local readMod,assetPath=mod.read,mod.assets.path
  mod.read=function(self,...)ownReads=ownReads+1;return readMod(self,...)end
  mod.assets.path=function(self,...)assetReads=assetReads+1;return assetPath(self,...)end
  for i=1,12 do rendered(actor())end
  mod.read,mod.assets.path=readMod,assetPath
  check(importReads==reads and ownReads==0 and assetReads==0,'Warm berry draw read imports or mod assets')
  -- Exercise the real manager event and the real in-game row independently
  -- of the background selector. Native must restore the already pooled actor
  -- immediately, and both choices must retain the native frame/state logic.
  local pooledOption=actor();local generatedImage,generatedQuad=pooledOption.fxImage,pooledOption.fxQuad
  local revision=mod.exports.state.revision
  mod._probeEvents:emit('mod.options_changed',{mod='tileshift',key='berry_style',value=1})
  check(berryRow.value()=='NATIVE'and saved.berry_style==1,'Manager event did not save the Native berry preference')
  check(pooledOption.fxImage~=generatedImage and pooledOption.fxQuad~=generatedQuad
   and rendered(pooledOption):getString()==originals[43][9]:getString(),'Native option did not immediately restore the pooled actor')
  check(mod.exports.state.style=='gen2'and mod.exports.state.revision==revision,'Berry selection changed the background style/cache')
  local nativeCases=0;local nativeReads,nativeOwn,nativeAssets=importReads,0,0
  mod.read=function(self,...)nativeOwn=nativeOwn+1;return readMod(self,...)end
  mod.assets.path=function(self,...)nativeAssets=nativeAssets+1;return assetPath(self,...)end
  for berry=1,43 do for frame=0,8 do
   selectCase(berry,frame);local bt=eo.berryTree;local fr=entry.trees[berry].frames[frame+1];local a=actor()
   check(rendered(a):getString()==originals[berry][frame+1]:getString(),'Native option changed original berry frame pixels')
   check(a.x==0 and a.y==32-fr.h and a.sortY==16 and a.elevation==3,'Native option changed berry placement')
   check(bt.tree==entry.trees[berry]and bt.anim.frame==frame and bt.anim.timer==17,'Native option changed berry animation/state')
   nativeCases=nativeCases+1
  end end
  mod.read,mod.assets.path=readMod,assetPath
  check(nativeCases==387 and importReads==nativeReads and nativeOwn==0 and nativeAssets==0,'Warm Native berry option performed IO')
  check(mod.exports.select('original')and mod.exports.select('gen1')and mod.exports.select('gen3')
   and mod.exports.select('gen2'),'Background style roundtrip failed')
  check(berryRow.value()=='NATIVE'and saved.berry_style==1
   and rendered(actor()):getString()==originals[43][9]:getString(),'Native preference was lost during background changes')
  revision=mod.exports.state.revision
  berryRow.step({game=mod.game},1)
  check(berryRow.value()=='CRYSTAL'and saved.berry_style==2
   and mod.game.options.modOptions.tileshift.berry_style==2
   and mod.game.save.options.modOptions.tileshift.berry_style==2
   and mod.game.mods.modOptions.tileshift.berry_style==2,'In-game row did not persist the Crystal berry preference')
  check(mod.exports.state.style=='gen2'and mod.exports.state.revision==revision,'Crystal berry reselection changed the background')
  local generatedCases=0;local optionReads,optionOwn,optionAssets=importReads,0,0
  mod.read=function(self,...)optionOwn=optionOwn+1;return readMod(self,...)end
  mod.assets.path=function(self,...)optionAssets=optionAssets+1;return assetPath(self,...)end
  for berry=1,43 do for frame=0,8 do
   selectCase(berry,frame);local bt=eo.berryTree;local fr=entry.trees[berry].frames[frame+1];local a=actor()
   local expected=capture(16,32,function()G.draw(expectedImages[berry],G.newQuad(0,fr.y,fr.w,fr.h,16,240),0,32-fr.h)end)
   check(rendered(a):getString()==expected:getString(),'Crystal option did not restore exact generated berry pixels')
   check(a.x==0 and a.y==32-fr.h and a.sortY==16 and a.elevation==3,'Crystal option changed berry placement')
   check(bt.tree==entry.trees[berry]and bt.anim.frame==frame and bt.anim.timer==17,'Crystal option changed berry animation/state')
   generatedCases=generatedCases+1
  end end
  mod.read,mod.assets.path=readMod,assetPath
  check(generatedCases==387 and importReads==optionReads and optionOwn==0 and optionAssets==0,'Warm reenabled Crystal berries performed IO')
  local berryOption={key='berry_style',default='crystal',default_value=2,choices={'native','crystal'},
   default_crystal=true,manager_event_tested=true,in_game_row_tested=true,native_cases=nativeCases,
   generated_cases_after_reenable=generatedCases,native_preference_survived_background_switch=true,
   immediate_pooled_actor_restore=true,background_style_unchanged=true,preference_persisted=true,
   native_anchor_and_state_preserved=true,warm_import_reads=0,warm_asset_reads=0,
   warm_native_import_reads=0,warm_native_asset_reads=0,warm_crystal_import_reads=0,warm_crystal_asset_reads=0}
  -- Both non-Crystal styles must remain the native actors byte-for-byte.
  for _,style in ipairs({'gen1','original','gen3'})do
   check(mod.exports.select(style),'Native berry fallback style unavailable')
   for berry=1,43 do for frame=0,8 do
    selectCase(berry,frame)
    check(rendered(actor()):getString()==originals[berry][frame+1]:getString(),'A non-Crystal style changed a native berry actor')
   end end
  end
  check(mod.exports.select('gen2')and theme:prepare(game),'Crystal reselection failed')
  selectCase(43,8);local pooled=actor();local generatedImage=pooled.fxImage
  local cacheReader=CacheFs.readAt
  CacheFs.readAt=function(path)
   local bytes=cacheReader(path)
   if path==game..'/data/generated/gba/berry_trees/manifest.lua'then return bytes..'changed'end
   return bytes
  end
  check(not theme:checkSource(game),'A changed source manifest was accepted')
  CacheFs.readAt=cacheReader
  check(pooled.fxImage~=generatedImage,'Source rejection retained a swapped pooled actor')
  check(rendered(actor()):getString()==originals[43][9]:getString(),'Source rejection did not restore native berry pixels')
  check(#report.warnings==1 and report.warnings[1]:find('Native berry manifest changed',1,true),'Unexpected source-rejection warning')
  report.expected_fingerprint_rejections[#report.expected_fingerprint_rejections+1]=table.remove(report.warnings)
  check(theme:checkSource(game),'Restored source did not recover')
  pooled=actor();check(pooled.fxImage==generatedImage,'Restored source did not reuse the verified cached artwork')
  mod.exports.dispose()
  check(Fx.collectActors==originalCollector,'Disposal retained the berry collector wrapper')
  check(rendered(actor()):getString()==originals[43][9]:getString(),'Disposal did not restore native actor pixels')
  check(tableString(entry)==metadataBefore,'Native berry manifest/state metadata changed')
  Objects._order,Objects._byId=order,byId;Fx.SYSTEMS=systems
  check(cases==387,'Incomplete per-host berry frame matrix')
  report.fixtures[#report.fixtures+1]={game=game,style='gen2',before_style='original',after_style='gen2',cases=cases,all_43_varieties=true,native_frames=9,varieties=43,
   before=beforeGallery,after=gallery,gallery=gallery,atlas_kind='private native actor atlas; not an actual map',
   atlas={columns=43,rows=9,cell_width=16,cell_height=32,width=688,height=288,column_legend=columns,row_legend=rows},
   frame_alpha_pixels=alphaCounts,all_fixture_frames_nonempty=true,source_metadata_unchanged=true,
   native_collector_and_draw=true,exact_generated_pixels=true,native_anchor_sort_elevation_preserved=true,
   native_animation_state_preserved=true,gen1_original_gen3_native_pixels_unchanged=true,
   warm_frames=12,warm_import_reads=0,warm_asset_reads=0,source_rejection_restored_pooled_actor=true,unload_restored_native=true}
  report.fixtures[#report.fixtures].berry_style_option=berryOption
 end
 @TRANSITIONS@
 check(#report.fixtures==#selected.games and #report.warnings==0,'Incomplete berry actor GPU fixture set')
 report.status='passed';write('report.json',Json.encode(report))
end
'''

TRANSITIONS=r'''
 if not selected.skip_transitions then
  local sequence={'ruby','sapphire','emerald','ruby'}
  local function cacheFor(game)
   return {read=function(_,path)return cacheRead(game..'/'..path)end,exists=function(self,path)return self:read(path)~=nil end}
  end
  local function useProfile(game)
   GV.set(game);assetGame=game
   local cache=cacheFor(game)
   Versions.selectCache(game,cache);CachePaths.reset();Dataset.cacheRootOverride=nil;Dataset.mountExtractRoots();Native.install(cache)
   require('src.core.game3.field_effects').install(cache)
  end
  -- One fresh initial Ruby boot, followed by the REAL public dataset/cache
  -- transition APIs. Never clear/replace this collector or its memo mid-run.
  useProfile('ruby')
  package.loaded['src.core.game3.field_effects_rse']=nil
  local Fx=require('src.core.game3.field_effects_rse')
  local nativeCollector=Fx.collectActors
  local nativeManifest=assert(Fx.berryManifest())
  local manifestBefore=tableString(nativeManifest)
  local systems=Fx.SYSTEMS;Fx.SYSTEMS={}
  local order,byId=Objects._order,Objects._byId
  local eo={px=0,py=16,cellX=0,cellY=1,visible=true,hidden=false,invisible=true,elevation=3,graphicsId=0}
  Objects._order={1};Objects._byId={[1]=eo}
  local function selectCase(berry,frame)
   eo.berryTree={id=1,visible=true,tree=nativeManifest.trees[berry],anim={frame=frame,timer=17},gfxKey=berry..':5',animNum=4}
  end
  local function collect(fn)
   local actors={};fn(actors,0,0);check(#actors==1,'Same-collector native berry actor missing');return actors[1]
  end
  local function draw(a)return capture(16,32,function()a.draw(a,0,0)end)end
  -- Seed the complete native original atlas at the initial Ruby boot. These
  -- engine-owned image/manifest memos remain intact across the whole sequence.
  local initialNative={}
  for berry=1,43 do initialNative[berry]={}
   for frame=0,8 do selectCase(berry,frame);initialNative[berry][frame+1]=draw(collect(nativeCollector))end
  end
  local mod=startMod('ruby',3)
  local theme=assert(mod.exports.berryTheme)
  local data=assert(load(assert(mod:read('lib/berry_catalog.lua'))))()
  local expectedImages={}
  for berry=1,43 do
   local spec=data.varieties[berry];local bytes=assert(mod:read(spec.asset));check(hash(bytes)==spec.hash,'Profile asset changed')
   expectedImages[berry]=G.newImage(love.image.newImageData(love.filesystem.newFileData(bytes,spec.asset)))
   expectedImages[berry]:setFilter('nearest','nearest')
  end
  check(mod.exports.select('gen2'),'Profile Crystal selection failed')
  report.profile_sequence={sequence=sequence,style='gen2',same_collector=true,
   setup='Fresh initial Ruby collector with all native originals seeded; no memo reset during dataset/profile sequence',steps={}}
  local function semantics(tree,spec,berry)
   return tree.berry==berry and tree.width==spec.width and tree.height==spec.height
    and tableString(tree.frames)==tableString(spec.frames)and tableString(tree.stages)==tableString(spec.stages)
  end
  for step,game in ipairs(sequence)do
   useProfile(game)
   check(Fx.berryManifest()==nativeManifest,'A profile transition cleared the original native manifest memo')
   local aliases={}
   for berry=1,43 do
    local tree=nativeManifest.trees[berry];local current=data.sources[game].trees[berry]
    check(hash(assert(cacheRead(game..'/data/generated/gba/berry_trees/'..current.file)))==current.rgbaHash,'Current profile RGBA changed')
    check(hash(assert(cacheRead(game..'/data/generated/gba/berry_trees/'..current.idx)))==current.idxHash,'Current profile IDX changed')
    local binding
    for _,host in ipairs({'ruby','sapphire','emerald'})do
     local known=data.sources[host].trees[berry]
     if tree.file==known.file and tree.idx==known.idx and semantics(tree,known,berry)and semantics(tree,current,berry)
      and current.rgbaHash==known.rgbaHash and current.idxHash==known.idxHash then binding=host;break end
    end
    check(binding~=nil,'Native cached entry lacks a frozen same-ID pixel/frame/program alias')
    aliases[#aliases+1]={berry=berry,binding_profile=binding,current_profile=game,
     binding_kind=(tree.file==current.file and tree.idx==current.idx)and'exact current entry'or'frozen filename alias',
     native_file=tree.file,current_file=current.file,native_idx=tree.idx,current_idx=current.idx,
     rgba_sha256=current.rgbaHash,idx_sha256=current.idxHash}
   end
   check(theme:checkSource(game),'Known same-collector profile alias was rejected')
   local readCount,ownCount,assetCount=importReads,0,0
   local readMod,assetPath=mod.read,mod.assets.path
   mod.read=function(self,...)ownCount=ownCount+1;return readMod(self,...)end
   mod.assets.path=function(self,...)assetCount=assetCount+1;return assetPath(self,...)end
   local cases=0
   for berry=1,43 do for frame=0,8 do
    selectCase(berry,frame);local a=collect(Fx.collectActors);local fr=nativeManifest.trees[berry].frames[frame+1]
    local expected=capture(16,32,function()G.draw(expectedImages[berry],G.newQuad(0,fr.y,fr.w,fr.h,16,240),0,32-fr.h)end)
    check(draw(a):getString()==expected:getString(),'Same-collector profile chose wrong generated berry pixels')
    check(a.x==0 and a.y==32-fr.h and a.sortY==16 and a.elevation==3,'Profile alias changed native actor placement')
    check(eo.berryTree.anim.frame==frame and eo.berryTree.anim.timer==17,'Profile alias changed native animation state')
    cases=cases+1
   end end
   mod.read,mod.assets.path=readMod,assetPath
   check(cases==387 and importReads==readCount and ownCount==0 and assetCount==0,'Profile warm collection performed IO')
   check(tableString(nativeManifest)==manifestBefore,'Profile binding mutated original native metadata')
   report.profile_sequence.steps[#report.profile_sequence.steps+1]={step=step,game=game,style='gen2',cases=cases,
    result='verified known alias accepted',same_original_collector=true,original_manifest_pointer_unchanged=true,
    source_metadata_unchanged=true,native_state_unchanged=true,current_imports_verified=true,bindings=aliases,
    generated_all_43_by_9=true,warm_import_reads=0,warm_asset_reads=0}
  end
  mod.exports.dispose();check(Fx.collectActors==nativeCollector,'Profile disposal retained collector hook')
  for berry=1,43 do for frame=0,8 do
   selectCase(berry,frame)
   check(draw(collect(nativeCollector)):getString()==initialNative[berry][frame+1]:getString(),'Profile disposal changed native cached pixels')
  end end
  check(Fx.berryManifest()==nativeManifest and tableString(nativeManifest)==manifestBefore,'Profile disposal changed original memo/state')
  Objects._order,Objects._byId=order,byId;Fx.SYSTEMS=systems
  report.profile_sequence.generated_cases=1548
  report.profile_sequence.cleanup_native_cached_pixels_exact=true
  report.profile_sequence.engine_memo_and_imports_unchanged=true
 end
'''


def main():
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--games',nargs='+',choices=('ruby','sapphire','emerald'),default=['ruby','sapphire','emerald']);parser.add_argument('--skip-transitions',action='store_true');args,remaining=parser.parse_known_args()
    root=Path(__file__).resolve().parents[1]
    if not(root/'lib/berry_catalog.lua').exists():raise RuntimeError('Activate the complete43-variety catalog before native GPU validation')
    native_args=argparse.ArgumentParser(add_help=False)
    native_args.add_argument('--engine',type=Path,default=root.parent/'.tools/engine-0395')
    native_args.add_argument('--reference-payload',type=Path)
    native_args.add_argument('--cache',type=Path,default=Path(os.environ['APPDATA'])/'pokemon-love2d')
    native_args.add_argument('--output',type=Path,default=root.parent/'.work/tileshift-v0350-berries/gpu')
    native,_=native_args.parse_known_args(remaining);native.output.mkdir(parents=True,exist_ok=True)
    critical=('src/core/game3/field_effects_rse.lua','src/core/game3/field_effects.lua','src/core/game3/objects.lua','src/core/game3/object_prepare.lua','src/core/game3/rse/berry_trees.lua')
    hashes={name:hashlib.sha256((native.engine/name).read_bytes()).hexdigest()for name in critical}
    matches=None
    if native.reference_payload:
        with zipfile.ZipFile(native.reference_payload)as bundle:matches={name:bundle.read(name)==(native.engine/name).read_bytes()for name in critical}
        assert all(matches.values()),'Native berry collector/state code differs from the required launcher payload'
    (native.output/'berry-native-source.json').write_text(json.dumps(dict(source_sha256=hashes,reference_matches=matches),sort_keys=True,indent=2)+'\n')
    contract=json.loads((root/'tools/berry_source_contract.json').read_text())
    source_games=set(args.games)if args.skip_transitions else set(('ruby','sapphire','emerald'))
    imports={}
    for game in sorted(source_games):
        paths={'data/generated/gba/berry_trees/manifest.lua'}
        for tree in contract[game]['trees'].values():paths.update('data/generated/gba/berry_trees/'+tree[k]for k in('file','idx'))
        for path in sorted(paths):imports[game+'/'+path]=hashlib.sha256((native.cache/game/path).read_bytes()).hexdigest()
    source=validate_gpu.LUA;prefix=source[:source.index(' -- Native Gen1 TileRenderer on real Red Pallet Town.')]
    option_fixture='options={define=function()end,get=function(_,key)return'
    assert prefix.count(option_fixture)==1,'Native probe option fixture changed; review required'
    prefix=prefix.replace(option_fixture,"options={define=function(self,schema)self.schema=schema end,get=function(_,key)if key=='berry_style'then return nil end;return",1)
    body=BODY.replace('@TRANSITIONS@',TRANSITIONS).replace('@SELECTION@',json.dumps(json.dumps(vars(args))))
    validate_gpu.LUA=prefix+body+source[source.index('\nfunction love.load()'):]
    sys.argv[1:]=remaining
    if '--output'not in remaining:sys.argv.extend(['--output',str(root.parent/'.work/tileshift-v0350-berries/gpu')])
    result=validate_gpu.main()
    unchanged=all(hashlib.sha256((native.cache/path).read_bytes()).hexdigest()==value for path,value in imports.items())
    assert unchanged,'Berry actor validation changed an imported source file'
    proof=dict(status='passed',source_files=len(imports),stored_file_sha256=imports,all_imported_sources_unchanged=True)
    (native.output/'berry-import-immutability.json').write_text(json.dumps(proof,sort_keys=True,indent=2)+'\n')
    if result==0:
        report_path=native.output/'report.json';report=json.loads(report_path.read_text());report['source_imports_unchanged']=True;report['source_import_files']=len(imports);report_path.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    return result


if __name__=='__main__':raise SystemExit(main())
