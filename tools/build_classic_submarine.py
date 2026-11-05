"""Verify and split the generated complete Crystal-style Hoenn submarine.

The original64x48 canvas is retained, including its transparent lower16 rows.
Raw generation and cartridge reference images remain private. --raw reproduces
the documented uniform sampling, four-color normalization and source alpha.
"""
from __future__ import annotations
import argparse,json,os
from pathlib import Path
from PIL import Image
import catalog

ROOT=Path(__file__).resolve().parents[1]
DIRECTORY=ROOT/'assets/original/classic-submarine'
RGBA_HASH='34022d195fa21528791927e21fe8a25fc03295d5bdf833cb5f15f103ccb189e5'
RAW_HASH='e61617fcd2ac06b809f9b744cd7fc3064b319c0214709dde042de179c9102a98'
PALETTE=[(58,58,58),(66,82,99),(115,140,156),(189,206,214)]
GRID=[[740,741,742,743],[736,737,738,739],[744,745,746,747]]

def build(raw=None):
    provenance=json.loads((DIRECTORY/'provenance.json').read_text())
    if raw:
        assert catalog.sha(raw.read_bytes())==RAW_HASH
        generated=Image.open(raw).convert('RGBA')
        assert generated.size==(1448,1086)
        padded=Image.new('RGBA',(1472,1104))
        padded.paste(generated,(12,9))
        small=padded.resize((64,48),Image.Resampling.NEAREST)
        base=Path(os.environ['APPDATA'])/'pokemon-love2d/emerald/data/generated/gba/native/general__underwater'
        ids,pixels,_=catalog.read_idx(base/'mids.idx')
        output=Image.new('RGBA',(64,48))
        for cy,row in enumerate(GRID):
            for cx,mid in enumerate(row):
                block=pixels[ids.index(mid)*256:(ids.index(mid)+1)*256]
                for y in range(16):
                    for x in range(16):
                        if block[y*16+x]//16==6:
                            rgb=small.getpixel((cx*16+x,cy*16+y))[:3]
                            color=min(PALETTE,key=lambda p:sum((a-b)**2 for a,b in zip(rgb,p)))
                            output.putpixel((cx*16+x,cy*16+y),color+(255,))
        assert catalog.sha(output.tobytes())==RGBA_HASH
        output.save(DIRECTORY/'submarine64x48.png')
    whole=Image.open(DIRECTORY/'submarine64x48.png').convert('RGBA')
    assert whole.size==(64,48) and catalog.sha(whole.tobytes())==RGBA_HASH
    assert set(whole.getchannel('A').get_flattened_data())<={0,255}
    assert not whole.crop((0,32,64,48)).getbbox()
    assert {p[:3]for p in whole.get_flattened_data()if p[3]}==set(PALETTE)
    records=[]
    for y,row in enumerate(GRID[:2]):
        for x,mid in enumerate(row):
            piece=whole.crop((x*16,y*16,x*16+16,y*16+16))
            path=DIRECTORY/f'submarine-{mid}.png';piece.save(path)
            records.append(dict(mid=mid,asset=path.relative_to(ROOT).as_posix(),
                                file_sha256=catalog.sha(path.read_bytes()),rgba_sha256=catalog.sha(piece.tobytes())))
    assert records==provenance['cells']
    generation=provenance['generation']
    assert generation['mode']=='built-in image_gen'
    assert catalog.sha(generation['prompt'].encode())==generation['prompt_sha256']
    return dict(whole_rgba_sha256=RGBA_HASH,source_cell_grid=GRID,assets=len(records),complete_canvas=[64,48])

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--raw',type=Path)
    print(json.dumps(build(parser.parse_args().raw),indent=2))
