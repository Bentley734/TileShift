"""Capture actual-main Crystal-theme coverage and native-size Gen3 map pairs.

Offline review material only. Native Dataset coverage and GPU probes remain
the authoritative runtime checks; source layouts are never modified.
"""
from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import zlib

from PIL import Image, ImageDraw, ImageFont
import catalog
import preview
from reverse_common import ReverseReview, ROOT
from validate_gpu import runtime_fingerprint


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--games',nargs='+',default=['firered','leafgreen','ruby','sapphire','emerald'])
    p.add_argument('--maps',nargs='+')
    p.add_argument('--extra-module',action='append',default=[],help='Review unregistered candidate rows over the actual main selection')
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    inputs=runtime_fingerprint(ROOT)
    modules=list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(ROOT/'main.lua').read_text())))
    rows={};module_hashes={}
    candidate_hashes={}
    for module in modules+args.extra_module:
        path=Path(module);path=path if path.is_absolute()else ROOT/path
        raw=path.read_bytes();module_hashes[module]=catalog.sha(raw)
        candidate=module in args.extra_module
        if candidate:candidate_hashes[module]=catalog.sha(raw)
        for row in preview.read_reviewed(path):
            if row['style']=='gen2'and row['game']in args.games:
                assert row.get('map')is None,'Pair-global native atlas cannot select map-specific rows'
                key=row['game'],row['tileset'],row['id']
                if key in rows:
                    assert candidate,'Duplicate main-selected reverse row: '+str(key)
                    assert row['sourceHash']==rows[key]['sourceHash'],'Candidate weakened source identity'
                    assert rows[key].get('sourceBehavior')is None or row.get('sourceBehavior')==rows[key]['sourceBehavior'],'Candidate changed source behavior guard'
                rows[key]=row
    f=ReverseReview('gen2-visual',args.games)
    records=[];unique={};art={};source={};missing=Counter()
    for game in args.games:
        refs=f.imp.cell_index(game)
        for map_id,spec in sorted(f.imp.table(game,'gba/native/manifest')['layouts'].items()):
            if args.maps and map_id not in args.maps:continue
            raw=(f.cache/game/'data/generated/gba/native'/spec['file']).read_bytes()
            blob=raw if raw[:4]==b'SVML'else zlib.decompress(raw)
            assert blob[:4]==b'SVML'
            pw,ph,w,h=struct.unpack_from('<HHHH',blob,6);w=w or pw;h=h or ph
            assert 0<w<=pw and 0<h<=ph
            offset=16+blob[14]*blob[15]*2
            before=Image.new('RGBA',(w*16,h*16));after=before.copy();count=0
            ids=Counter()
            for y in range(h):
                for x in range(w):
                    mid=struct.unpack_from('<H',blob,offset+(y*pw+x)*4)[0]
                    key=game,spec['pair'],mid;cell=refs[key[1:]]
                    if key not in source:
                        source[key]=preview.native_donor(f.cache,dict(game=game,tileset=spec['pair'],id=mid,hash=cell['pixel_sha256']),f.packed)
                    original=source[key];before.paste(original,(x*16,y*16))
                    row=rows.get(key)
                    if row:
                        assert row['sourceHash']==cell['pixel_sha256']
                        if key not in art:art[key]=f.render(row)
                        piece=art[key];count+=1
                    else:piece=original;ids[mid]+=1;missing[game,spec['pair'],mid]+=1
                    after.paste(piece,(x*16,y*16))
            signature=hashlib.sha256(struct.pack('<II',w,h)+before.tobytes()+after.tobytes()).hexdigest()
            if signature not in unique:
                folder=args.output/game;folder.mkdir(exist_ok=True)
                b=folder/(map_id+'-before-native.png');a=folder/(map_id+'-after-native.png')
                before.save(b);after.save(a);unique[signature]=(str(b.resolve()),str(a.resolve()))
            b,a=unique[signature]
            records.append(dict(game=game,map=map_id,pair=spec['pair'],source_cells=w*h,replaced_cells=count,
                                remaining_cells=w*h-count,pair_sha256=signature,before=b,after=a,missing_ids=dict(ids)))
            if len(records)%25==0:(args.output/'progress.json').write_text(json.dumps(dict(maps=len(records),unique=len(unique),game=game,map=map_id)))
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',13)
    distinct=[];seen=set()
    for r in records:
        if r['pair_sha256']not in seen:seen.add(r['pair_sha256']);distinct.append(r)
    contacts=[]
    for start in range(0,len(distinct),12):
        batch=distinct[start:start+12];canvas=Image.new('RGB',(1560,1080),'#18212b');draw=ImageDraw.Draw(canvas)
        for n,r in enumerate(batch):
            x=(n%3)*520;y=(n//3)*270
            draw.text((x+4,y+3),r['game']+'/'+r['map'],fill='white',font=font)
            draw.text((x+4,y+21),f"{r['replaced_cells']}/{r['source_cells']} replaced",fill='#c4cdd8',font=font)
            for column,name in enumerate(('before','after')):
                im=Image.open(r[name]).convert('RGB');factor=max(1,(im.width+249)//250,(im.height+224)//225)
                if factor>1:im=im.resize((max(1,im.width//factor),max(1,im.height//factor)),Image.Resampling.NEAREST)
                elif max(im.size)<=112:im=im.resize((im.width*2,im.height*2),Image.Resampling.NEAREST)
                canvas.paste(im,(x+column*260+4,y+42))
        target=args.output/f'contact-{start//12+1:03}.png';canvas.save(target);contacts.append(str(target.resolve()))
    assert inputs==runtime_fingerprint(ROOT),'Production changed during offline capture'
    for module,digest in candidate_hashes.items():
        path=Path(module);path=path if path.is_absolute()else ROOT/path
        assert catalog.sha(path.read_bytes())==digest,'Candidate changed during capture'
    report=dict(type='offline actual-main native Gen3/Crystal review pairs',runtime_inputs=inputs,
                source_maps=len(records),unique_pairs=len(unique),records=records,contacts=contacts,
                selected_module_hashes=module_hashes,
                candidate_module_hashes=candidate_hashes,
                missing=[dict(game=g,pair=p,id=m,occurrences=count)for(g,p,m),count in missing.most_common()])
    (args.output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(source_maps=len(records),unique_pairs=len(unique),remaining_cells=sum(missing.values()),missing_keys=len(missing))))


if __name__=='__main__':main()
