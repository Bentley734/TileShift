"""Check every main-listed GB source-file guard with the production decoder.

This is a source fingerprint audit, not a map-coverage or GPU claim. Each unique
cartridge/tileset/guard combination decodes a real source cell; no donor artwork,
generation runtime, imported data or game save is changed.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from PIL import Image
import preview
import review
import validate_animation

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'.tools/python'))
from lupa.luajit21 import LuaRuntime


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'.work/tileshift-source-guards/source-file-proof.json')
    args=parser.parse_args();mod=ROOT/'TileShift';cache=Path(os.environ['APPDATA'])/'pokemon-love2d'
    paths=sorted(set(re.findall(r"['\"](mappings/[a-zA-Z0-9_]+\.lua)['\"]",(mod/'main.lua').read_text(encoding='utf-8'))))
    paths=[p for p in paths if(mod/p).is_file()]
    rows=[r for path in paths for r in preview.read_reviewed(mod/path)]
    guarded=[r for r in rows if r.get('sourceFiles')is not None]
    unique={}
    for r in guarded:unique.setdefault((r['game'],r['tileset'],json.dumps(r['sourceFiles'],sort_keys=True)),r)
    lua=LuaRuntime(unpack_returned_tuples=True,encoding=None);reads=Counter();pictures=Counter()
    def read(relative):
        path=(cache/relative.decode()).resolve();assert path.is_relative_to(cache)
        reads[relative.decode()]+=1
        return path.read_bytes()if path.is_file()else None
    def image(relative,_raw):
        pictures[relative.decode()]+=1;im=Image.open(cache/relative.decode()).convert('RGBA')
        return lua.globals()[b'makeData'](im.width,im.height,b'rgba8',im.tobytes())
    def sha(raw):return hashlib.sha256(raw).hexdigest()
    before=Path.cwd();proofs=[]
    try:
        os.chdir(ROOT/'.tools/engine-0395');lua.execute(validate_animation.IMAGE_FIXTURE.encode())
        mapping=lua.execute((mod/'lib/mapping.lua').read_bytes())
        # Keep each authored module's compact expansion/chunks; flattening the
        # whole catalog into one Lua literal exceeds LuaJIT's constant limit.
        all_rows=lua.table();append=lua.eval(b'function(out,more)for _,row in ipairs(more)do out[#out+1]=row end end')
        for path in paths:append(all_rows,lua.execute((mod/path).read_bytes()))
        _,errors=mapping[b'index'](all_rows)
        assert len(errors)==0,[errors[i]for i in range(1,len(errors)+1)]
        donor=lua.execute((mod/'lib/donor.lua').read_bytes())[b'new'](lua.table_from({
            b'read':read,b'prefix':lambda game:game+b'/',b'newImageData':lua.globals()[b'makeData'],
            b'hash':lambda raw:sha(raw).encode(),b'loadImage':image}))
        for r in unique.values():
            ref={k:r[k]for k in('game','tileset','id','quadrant','sourceFiles')}
            ref.update(hash=r['sourceHash'],hashOnly=True)
            result=donor[b'cell'](donor,lua.execute(('return '+review.lua_value(ref)).encode()))
            assert not isinstance(result,tuple),(r['game'],r['tileset'],result)
            assert result[b'sourceHash'].decode()==r['sourceHash']
            proofs.append({'game':r['game'],'tileset':r['tileset'],'source_cell':[r['id'],r['quadrant']],
                           'sourceFiles':r['sourceFiles'],'source_pixel_sha256':r['sourceHash']})
        for name in lua.eval(b'package.loaded').keys():
            assert not name.startswith((b'src.core.game3.',b'src.world.gen2.')),'Source guard loaded a generation runtime'
    finally:os.chdir(before)
    report={'status':'passed','main_listed_modules':paths,'reviewed_rows':len(rows),'guarded_rows':len(guarded),
        'legacy_rows_without_sourceFiles':len(rows)-len(guarded),'unique_source_guard_contexts':len(proofs),
        'games':sorted({p['game']for p in proofs}),'rejected':0,'source_imports_read_only':True,
        'runtime_modules':{file:sha((mod/file).read_bytes())for file in('main.lua','lib/mapping.lua','lib/session.lua','lib/donor.lua')},
        'raw_map_file_reads':{g:reads[g+'/data/generated/maps.lua']for g in sorted({p['game']for p in proofs})},
        'source_images_decoded':sum(pictures.values()),'source_contexts':proofs}
    args.output.resolve().parent.mkdir(parents=True,exist_ok=True);args.output.resolve().write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items()if k not in('source_contexts','runtime_modules','main_listed_modules')},indent=2))


if __name__=='__main__':main()
