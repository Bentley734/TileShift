"""Compare production Session warm lookups with the version cited by the user.

This isolates CPU/cache overhead; it is not an FPS or GPU benchmark.
"""
import importlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / '.tools/python'))
BASELINE = 'c395ca4371efe7ea19489dee8e2736b5f69db546'
BENCH = r'''
local identityCalls,images,decodes=0,0,0
local function image(w,h)
 images=images+1
 return {getDimensions=function()return w,h end,
  getPixel=function()return .2,.6,.3,1 end,
  setPixel=function()end,paste=function()end}
end
local cell=image(16,16)
local donor={invalidate=function()end,
 sourceIdentity=function()identityCalls=identityCalls+1;return 'unchanged-import' end,
 cell=function()decodes=decodes+1;return {under=cell} end}
local row={game='red',style='gen3',tileset='OVERWORLD',id=1,quadrant=0,
 donor={game='emerald'}}
local session=Session.new({mappings={row},donor=donor,newImageData=image,
 generations={red=1,emerald=3},validate=function()return true end})
session:select('gen3')
local maps={{id='A',width=1,height=1,blocks={1}},
 {id='B',width=1,height=1,blocks={1}}}
local first=session:replacements('red','OVERWORLD',maps[1])
local second=session:replacements('red','OVERWORLD',maps[2])
for i=1,1000 do session:replacements('red','OVERWORLD',maps[i%2+1]) end
collectgarbage('collect');collectgarbage('stop')
local beforeMemory=collectgarbage('count')
local beforeImages,beforeDecodes,beforeIdentity=images,decodes,identityCalls
local started=os.clock()
for i=1,100000 do
 local rows=session:replacements('red','OVERWORLD',maps[i%2+1])
 assert(rows==(i%2==0 and first or second))
end
local elapsed=os.clock()-started
local memory=collectgarbage('count')-beforeMemory
collectgarbage('restart')
return {seconds=elapsed,allocated_kib=memory,lookups=100000,
 image_allocations=images-beforeImages,donor_decodes=decodes-beforeDecodes,
 import_identity_calls=identityCalls-beforeIdentity}
'''


def main():
    old = subprocess.check_output(['git', 'show', BASELINE + ':lib/session.lua'], cwd=ROOT)
    new = (ROOT / 'lib/session.lua').read_bytes()
    result = {'baseline_commit': BASELINE, 'scope': __doc__, 'runtimes': {}}
    for name in ('lua51', 'luajit21'):
        runtime = importlib.import_module('lupa.' + name).LuaRuntime
        records = {}
        for label, source in (('before', old), ('after', new)):
            lua = runtime(unpack_returned_tuples=True)
            lua.globals().Session = lua.execute(source)
            records[label] = dict(lua.execute(BENCH).items())
        assert records['after']['image_allocations'] == 0
        assert records['after']['donor_decodes'] == 0
        assert records['after']['import_identity_calls'] == 0
        result['runtimes'][name] = records
    out = ROOT.parent / '.work/tileshift-session-performance.json'
    out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result['runtimes'], indent=2))


if __name__ == '__main__':
    main()
