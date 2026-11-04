"""Remove repeated top-border seams from native-size Gen3 Marts on GSC hosts.

Only the inserted plain roofing bands change. Every byte outside the reviewed
row literals, all source guards, and every original roof/facade detail remain.
The original authoring generator contains the same corrected band selection.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

from PIL import Image, ImageDraw
import catalog
import gen2_extended_review as extended
import preview
from architecture_review import TEMPLATES
from gen2_side_threshold_orientation import literal_rows, identity
from newbark_building_review import lua, native_reference

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'.work/tileshift-v0350-mart-roof'
MODULE='mappings/building_overhangs.lua'
SOURCE_RGBA='e4082e7cfff2069da26c5f229395544e2a44d6b224db12222b28b597f6a560c9'


def ordered(value):
    if isinstance(value,dict):return {k:ordered(value[k])for k in sorted(value)}
    if isinstance(value,list):return [ordered(v)for v in value]
    return value


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def main():
    global OUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate',action='store_true');parser.add_argument('--activate',action='store_true')
    parser.add_argument('--output',type=Path,default=OUT)
    args=parser.parse_args();assert not args.activate or args.validate;OUT=args.output.resolve()
    OUT.mkdir(parents=True,exist_ok=True)
    cache=Path(os.environ['APPDATA'])/'pokemon-love2d';packed={}
    source,native=native_reference(SimpleNamespace(cache=cache,catalog=ROOT.parent/'.work/tileshift-catalog',output=OUT),'mart',TEMPLATES['mart'],packed)
    assert catalog.sha(source.tobytes())==SOURCE_RGBA,'Native Mart changed: inspect the source before updating the literal'
    original=(ROOT/MODULE).read_bytes().decode('utf-8');literal=list(literal_rows(original))
    groups={}
    for _,_,row in literal:
        if row['game']in extended.GAMES and row['style']=='gen3'and row['role']=='larger_mart':
            groups.setdefault((row['game'],row['map']),[]).append(row)
    assert groups and all(len(rows)==16 for rows in groups.values())
    def parts(column,corrected):
        result=[]
        for dy in range(2):
            for dx in range(2):
                x=column*2+dx;y=2+dy
                sy=2 if corrected or x in(0,1,6,7)else 1
                gx=native['pixel_origin'][0]+x*8;gy=native['pixel_origin'][1]+sy*8
                mid=native['layout']['mids'][gy//16*native['layout']['width']+gx//16];rec=native['records'][mid]
                result.append(dict(donor=dict(game=native['game'],tileset=native['pair'],id=mid,hash=rec['pixel_sha256']),srcX=gx%16,srcY=gy%16,x=dx*8,y=dy*8,w=8,h=8))
        return result
    changes={};guards=[];changed=[];scenes=[];instances=[]
    roof_rows=preview.read_reviewed(ROOT/'lib/center_mart_roofs.lua')
    for (game,map_id),rows in sorted(groups.items()):
        x0=min(r['x']for r in rows);y0=min(r['y']for r in rows)
        assert {(r['x'],r['y'])for r in rows}=={(x0+x,y0+y)for y in range(4)for x in range(4)}
        before=Image.new('RGBA',(64,80));after=Image.new('RGBA',(64,80));revised=[]
        for old in rows:
            new=copy.deepcopy(old)
            if old['y']==y0:
                column=old['x']-x0
                assert old['parts']in(parts(column,False),parts(column,True)),('Unreviewed Mart roof construction',game,map_id,column)
                new['parts']=parts(column,True)
                if new['parts']!=old['parts']:
                    new['evidence']+=' The two inserted8px roof bands use the native plain lower roofing panel, without repeating the horizontal top border. Original roof outline, ribs, emblem, facade, door and sign remain complete at native pixel scale.'
                    new['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,new,packed,ROOT).tobytes())
                    changes[identity(old)]=new;changed.append(new)
                    guards.append(dict(identity=list(identity(old)),before_row_sha256=digest(old),after_row_sha256=digest(new),sourceHash=old['sourceHash']))
            revised.append(new)
            pt=((old['x']-x0)*16,(old['y']-y0+1)*16)
            before.paste(preview.replacement_image(cache,old,packed,ROOT),pt)
            after.paste(preview.replacement_image(cache,new,packed,ROOT),pt)
        for row in roof_rows:
            if row['game']==game and row.get('map')==map_id and row['role']=='larger_mart':
                image=preview.replacement_image(cache,row,packed,ROOT);pt=((row['x']-x0)*16,0);before.paste(image,pt);after.paste(image,pt)
        # This independent source crop is the complete ordinary8px roof panel.
        expected=source.crop((16,16,48,24))
        assert after.crop((16,16,48,24)).tobytes()==expected.tobytes()
        assert after.crop((16,24,48,32)).tobytes()==expected.tobytes()
        assert before.crop((0,32,64,80)).tobytes()==after.crop((0,32,64,80)).tobytes(),'A roof repair changed the emblem/facade/entrance'
        for y in range(80):
            for x in range(64):
                if not(16<=x<48 and 16<=y<32):assert before.getpixel((x,y))==after.getpixel((x,y))
        scenes.append(dict(game=game,map=map_id));instances.append(dict(game=game,map=map_id,building_origin=[x0,y0],native_dimensions=[64,80],only_inserted_roof_bands_changed=True,facade_door_emblem_unchanged=True,after_rgba_sha256=catalog.sha(after.tobytes())))
        if map_id=='BLACKTHORN_CITY':
            canvas=Image.new('RGB',(548,364),'#18232d');draw=ImageDraw.Draw(canvas);draw.text((12,12),'Previous roof seams',fill='white');draw.text((284,12),'Plain native roofing bands',fill='white')
            canvas.paste(before.resize((256,320),Image.Resampling.NEAREST),(12,36),before.resize((256,320),Image.Resampling.NEAREST))
            canvas.paste(after.resize((256,320),Image.Resampling.NEAREST),(284,36),after.resize((256,320),Image.Resampling.NEAREST));canvas.save(OUT/(game+'-blackthorn-mart-comparison.png'))
    # Exact surgical literal replacement preserves all unrelated bytes.
    fixed=original;spans=[]
    for start,end,row in reversed(literal):
        if identity(row)in changes:spans.append((start,end));fixed=fixed[:start]+lua(ordered(changes[identity(row)]))+fixed[end:]
    def untouched(text,target):
        chunks=[];at=0
        for start,end,row in literal_rows(text):
            if identity(row)in target:chunks.append(text[at:start]);at=end
        chunks.append(text[at:]);return chunks
    assert untouched(original,changes)==untouched(fixed,changes)
    for _,_,row in literal_rows(fixed):
        if identity(row)in changes:assert row==changes[identity(row)]
    (OUT/'candidate.lua').write_bytes(fixed.encode('utf-8'))
    live=None
    if args.validate:
        candidates=[r for _,_,r in literal_rows(fixed)if r['game']in extended.GAMES and r['role']=='larger_mart'and r['y']==min(v['y']for v in groups[r['game'],r['map']])]
        live=extended.validate_batch(candidates,SimpleNamespace(cache=cache,engine=ROOT.parent/'.work/tileshift-engine-0400',output=OUT),ROOT)
    proof=dict(status='passed'if args.validate else'candidate',module=MODULE,changed_rows=len(changes),instances=instances,source_rgba_sha256=SOURCE_RGBA,all_source_guards_preserved=True,
               all_bytes_outside_changed_literals_identical=True,before_sha256=catalog.sha(original.encode()),after_sha256=catalog.sha(fixed.encode()),supersessions=guards,neutral_accepted=live,activated=args.activate)
    (OUT/'proof.json').write_text(json.dumps(proof,indent=2)+'\n');(OUT/'affected-scenes.json').write_text(json.dumps(scenes,indent=2)+'\n')
    if args.activate:(ROOT/MODULE).write_bytes(fixed.encode('utf-8'))
    print(json.dumps(dict(status=proof['status'],changed_rows=len(changes),instances=len(instances),neutral_accepted=live,activated=args.activate,after_sha256=proof['after_sha256'])))


if __name__=='__main__':main()
