"""Decode every reviewed Gen1 outdoor mapping against live source imports."""
from __future__ import annotations
import hashlib
import argparse
import json
import os
from pathlib import Path
import sys
import zlib
from PIL import Image

WORKSPACE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(WORKSPACE/'.tools/python'))
from lupa.luajit21 import LuaRuntime
import validate_animation

def main():
    cache=Path(os.environ['APPDATA'])/'pokemon-love2d'
    mod=WORKSPACE/'TileShift'
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mapping',type=Path,default=mod/'mappings/gen1_outdoor.lua')
    args=parser.parse_args();mapping_path=args.mapping.resolve()
    lua=LuaRuntime(unpack_returned_tuples=True,encoding=None)
    def read(relative):
        path=(cache/relative.decode()).resolve()
        assert path.is_relative_to(cache)
        if not path.is_file():return None
        raw=path.read_bytes()
        if path.suffix in ('.idx','.rgba'):
            try:return zlib.decompress(raw)
            except zlib.error:pass
        return raw
    def load_image(relative,_raw):
        image=Image.open(cache/relative.decode()).convert('RGBA')
        return lua.globals()[b'makeData'](image.width,image.height,b'rgba8',image.tobytes())
    before=Path.cwd()
    try:
        os.chdir(WORKSPACE/'.tools/engine-0395')
        lua.execute(validate_animation.IMAGE_FIXTURE.encode())
        ctx=lua.table_from({b'read':read,b'prefix':lambda game:game+b'/',
            b'hash':lambda raw:hashlib.sha256(raw).hexdigest().encode(),
            b'newImageData':lua.globals()[b'makeData'],b'loadImage':load_image})
        donor=lua.execute((mod/'lib/donor.lua').read_bytes())[b'new'](ctx)
        composition=lua.execute((mod/'lib/composition.lua').read_bytes())
        composer=composition[b'new'](lua.table_from({b'donor':donor,b'newImageData':lua.globals()[b'makeData'],
            b'hashImage':lambda image:hashlib.sha256(image[b'getString'](image)).hexdigest().encode()}))
        lua.globals()[b'outdoorDecoder']=donor
        lua.globals()[b'outdoorComposer']=composer
        lua.globals()[b'outdoorRows']=lua.execute(mapping_path.read_bytes())
        lua.globals()[b'outdoorSourceRead']=read
        lua.globals()[b'outdoorMapping']=lua.execute((mod/'lib/mapping.lua').read_bytes())
        lua.globals()[b'outdoorSession']=lua.execute((mod/'lib/session.lua').read_bytes())
        result=lua.execute(br'''
local indexed,errors=outdoorMapping.index(outdoorRows);assert(#errors==0,table.concat(errors,'\n'))
local state=outdoorSession.new({mappings=indexed,donor=outdoorDecoder,newImageData=makeData,
 generations=outdoorMapping.generations,validate=outdoorMapping.validate,
 compose=function(row)return outdoorComposer:cell(row)end,warn=function(message)error(message)end})
state:select('gen3')
local contexts,opaque,positioned,frameImages,sourceMaps={},0,0,0,{}
local function definition(row)
 if not row.map then return {id='__GLOBAL_REVIEW__'}end
 if not sourceMaps[row.game]then
  sourceMaps[row.game]=assert(require('src.core.SaveSerializer').decode(
   assert(outdoorSourceRead(row.game..'/data/generated/maps.lua')),
   {allowArray=true,allowComments=true,maxBytes=16*1024*1024,maxDepth=64,maxNodes=2000000,
    maxStringBytes=8*1024*1024,maxTableEntries=500000}))
 end
 return assert(sourceMaps[row.game][row.map],'Scoped source map is unavailable')
end
local function opaqueBlock(block)
 for _,image in ipairs(block.frames or {block.image})do
  if block.frames then frameImages=frameImages+1 end
  for q,included in pairs(block.coverage)do if included then
   for y=0,15 do for x=0,15 do
    local _,_,_,a=image:getPixel(q%2*16+x,math.floor(q/2)*16+y)
    assert(a==1,'Outdoor replacement contains unexpected transparent pixels');opaque=opaque+1
   end end
  end end
 end
end
for _,row in ipairs(outdoorRows)do
 local key=row.game..':'..row.tileset..':'..(row.map or '*')
 if not contexts[key] then
  local blocks=state:replacements(row.game,row.tileset,definition(row))
  for _,block in pairs(blocks)do
   opaqueBlock(block)
   for _,variant in pairs(block.positions or {})do opaqueBlock(variant)end
  end
  contexts[key]=blocks
 end
 if row.x~=nil then
  local def=definition(row)
  assert(row.x>=0 and row.y>=0 and row.x<def.width*2 and row.y<def.height*2,'Positioned source cell is outside its map')
  local bx,by=math.floor(row.x/2),math.floor(row.y/2)
  assert(def.blocks[by*def.width+bx+1]==row.id and row.quadrant==row.y%2*2+row.x%2,
   'Positioned source cell has a changed source block/quadrant')
  local block=assert(contexts[key][row.id])
  local variant=assert(block.positions and block.positions[bx..':'..by],'Positioned art was not published')
  assert(variant.coverage[row.quadrant],'Positioned source quadrant was not covered');positioned=positioned+1
 end
end
assert(state.rejected==0 and state.accepted>=#outdoorRows,'Not all outdoor rows decoded')
for name in pairs(package.loaded)do
 assert(not name:match('^src%.core%.game3%.') and not name:match('^src%.world%.gen2%.'),'Donor loaded source runtime '..name)
end
local n=0;for _ in pairs(contexts)do n=n+1 end
return {accepted=#outdoorRows,decoded_with_contexts=state.accepted,rejected=state.rejected,contexts=n,
 opaque_pixels_checked=opaque,positioned_source_cells_checked=positioned,native_animation_frame_images_checked=frameImages}
''')
        report={key.decode():value for key,value in result.items()}
    finally:os.chdir(before)
    report.update(status='passed',source_imports_read_only=True,source_generation_runtime_loaded=False,
                  mapping_sha256=hashlib.sha256(mapping_path.read_bytes()).hexdigest())
    folder='tileshift-outdoor-review'if mapping_path.name=='gen1_outdoor.lua'else'tileshift-gen1-extended-review'
    target=WORKSPACE/f'.work/{folder}/live-mapping-proof.json'
    target.write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
