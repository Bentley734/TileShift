"""Correct the reviewed RIGHT-facing Gen2 outdoor gate thresholds.

Legacy gate authoring workflows must run this correction afterward. It replaces
only the36 right-entry row literals in two existing mapping files and preserves
all other bytes. Reproduction reads the immutable original recipes from Git.
Native donor pixels remain in the player's imports, never the source/package.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from types import SimpleNamespace

from PIL import Image, ImageDraw, ImageFont

import catalog
import gen2_extended_review as ext
from interior_review import Imports
from newbark_building_review import lua
import preview
from building_review import decode_layout

ROOT=Path(__file__).resolve().parents[1]
CACHE=Path(os.environ['APPDATA'])/'pokemon-love2d'
OUT=ROOT.parent/'.work/tileshift-v0340-steps'
BASE_COMMIT='ba62d92f00931e9e8dd5e8248ff6719a56f2b421'
MODULES=('mappings/johto_remaining.lua','mappings/park.lua')
MAPS=('ILEX_FOREST','ROUTE_34','ROUTE_38','RUINS_OF_ALPH_OUTSIDE','NATIONAL_PARK','NATIONAL_PARK_BUG_CONTEST')
GAMES=('gold','silver','crystal')
DONOR_PAIR='general__rom_082d4b54'
REVIEWED_BINDING='8a00b8996d9657a7471cd7dccf5a7412f29399175652588ed298b7cf77c2d285'
PATCH_NOTE=' Corrected RIGHT-facing source side threshold: the complete native FireRed Route15 WEST-side320/328 frame replaces the formerly reversed EAST-side324/332 counterpart. Each original16px cell and the complete16x32 cap/frame/foot keep1:1 pixels; the unchanged source COLL_WARP_CARPET_RIGHT0x7e, both original entrances and destinations determine orientation. This is an original side-entry threshold, not a rotated stair flight. Source layouts, collision, actors, scripts and events remain unchanged.'


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def identity(row):
    return tuple(row.get(k)for k in('game','style','map','tileset','id','quadrant','x','y'))


def target(row):
    return row.get('game')in GAMES and row.get('style')=='gen3' and row.get('map')in MAPS and row.get('sourceCollision')==126 and len(row.get('parts',[]))==1 and row['parts'][0].get('donor',{}).get('game')=='firered' and row['parts'][0]['donor'].get('tileset')==DONOR_PAIR and row['parts'][0]['donor'].get('id')in(320,328,324,332)


def baseline(relative):
    result=subprocess.run(['git','-c','safe.directory='+str(ROOT).replace('\\','/'),'-C',str(ROOT),'show',BASE_COMMIT+':'+relative],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return result.stdout.decode('utf-8')


def literal_rows(text):
    """Locate row tables inside the original bounded batch arrays exactly."""
    depth=0;quote=None;escape=False;comment=False;start=None
    for i,c in enumerate(text):
        if comment:
            if c=='\n':comment=False
            continue
        if quote:
            if escape:escape=False
            elif c=='\\':escape=True
            elif c==quote:quote=None
            continue
        if c in('\"',"'"):quote=c;continue
        if c=='-' and i+1<len(text)and text[i+1]=='-':comment=True;continue
        if c=='{':
            depth+=1
            if depth==2:start=i
        elif c=='}':
            if depth==2:
                value=catalog.plain(catalog.LUA.execute('return '+text[start:i+1]))
                if isinstance(value,dict)and all(k in value for k in('game','style','tileset','id')):
                    yield start,i+1,value
            depth-=1
    assert depth==0 and quote is None


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--activate',action='store_true');p.add_argument('--validate',action='store_true');p.add_argument('--preview',action='store_true');p.add_argument('--route38-only',action='store_true')
    args=p.parse_args();assert not args.activate or args.validate
    OUT.mkdir(exist_ok=True);imp=Imports(CACHE,ROOT.parent/'.work/tileshift-catalog')
    old_rows=[];locations={}
    for module in MODULES:
        original=baseline(module)
        for start,end,row in literal_rows(original):
            if target(row):
                assert row['parts'][0]['donor']['id']in(324,332)
                old_rows.append(row);locations[identity(row)]=dict(module=module,literal_sha256=hashlib.sha256(original[start:end].encode()).hexdigest())
    old_rows.sort(key=lambda r:tuple(''if v is None else str(v)for v in identity(r)))
    assert len(old_rows)==36 and len(locations)==36
    assert all(sum(r['game']==game and r['map']==name for r in old_rows)==2 for game in GAMES for name in MAPS)
    data={game:ext.source(CACHE,game)for game in GAMES}
    source_binding=[];scenes=[]
    for game in GAMES:
        for name in MAPS:
            m=data[game]['maps'][name];entries=[]
            for row in old_rows:
                if row['game']!=game or row['map']!=name:continue
                c=ext.cell_info(CACHE,game,data[game],row['tileset'],row['id'],row['quadrant'])
                assert c['sourceHash']==row['sourceHash']and c['collision']==126
                assert data[game]['fingerprints'][row['tileset']]==row['sourceFiles']
                assert [bool(a.get('priority'))for a in c['attributes']]==row['sourcePriority']
                assert [a.get('palette',1)for a in c['attributes']]==row['sourcePalettes']
                for x,y in row['sourceCells']:
                    assert m['blocks'][y//2*m['width']+x//2]==row['id'] and y%2*2+x%2==row['quadrant']
                    warp=[w for w in m['warps']if w['x']==x and w['y']==y]
                    assert len(warp)==1
                    entries.append(dict(x=x,y=y,destination=warp[0]['destMap'],destination_warp=warp[0]['destWarp']))
                source_binding.append(dict(identity=list(identity(row)),old_row_sha256=digest(row),source=c,source_files=row['sourceFiles'],coordinates=row['sourceCells']))
            assert len(entries)==2
            scenes.append(dict(game=game,id=name,complete=True,entrances=sorted(entries,key=lambda e:(e['x'],e['y'])),source_map_definition_sha256=digest(m)))
    donor_binding={}
    for mid in(320,328,324,332):
        c=imp.cell_index('firered')[DONOR_PAIR,mid]
        donor_binding[str(mid)]={k:c[k]for k in('pixel_sha256','layer_sha256','behavior','behavior_hint')}
    native_map=imp.table('firered','gba/native/manifest')['layouts']['FR_ROUTE_15']
    donor_layout=(CACHE/'firered/data/generated/gba/native'/native_map['file']).read_bytes()
    native=decode_layout(CACHE/'firered/data/generated/gba/native'/native_map['file'])
    for x,y,mid in((9,11,320),(9,12,328),(16,11,324),(16,12,332)):
        assert native['mids'][y*native['width']+x]==mid,('Native side-threshold source orientation changed',x,y,mid)
    donor_warps=imp.table('firered','gba/warps')['FR_ROUTE_15']
    assert any(w['x']==9 and w['y']==11 and w['destMap']=='FR_ROUTE_15_WEST_ENTRANCE_1F'for w in donor_warps)
    assert donor_binding['320']['behavior_hint']=='MB_EAST_ARROW_WARP'
    assert donor_binding['324']['behavior_hint']=='MB_WEST_ARROW_WARP'
    binding=dict(base_commit=BASE_COMMIT,source_rows=source_binding,scenes=scenes,donor_cells=donor_binding,native_donor_layout_sha256=hashlib.sha256(donor_layout).hexdigest(),native_donor_warps=donor_warps)
    binding_hash=digest(binding);(OUT/'source-binding.json').write_text(json.dumps(dict(sha256=binding_hash,binding=binding),sort_keys=True,indent=2)+'\n')
    assert binding_hash==REVIEWED_BINDING,('Original side-threshold source/donor binding changed; fresh visual/entrance review required',binding_hash)
    new_rows=[];pairs=[]
    for old in old_rows:
        row=copy.deepcopy(old);part=row['parts'][0];old_mid=part['donor']['id'];mid=old_mid-4
        assert part['layers']==['mid']and(part.get('srcX',0),part.get('srcY',0),part['w'],part['h'],part.get('x',0),part.get('y',0))==(0,0,16,16,0,0)
        c=imp.cell_index('firered')[DONOR_PAIR,mid];part['donor']['id']=mid;part['donor']['hash']=c['pixel_sha256'];part['layerHashes']={'mid':c['layer_sha256']['mid']}
        row['evidence']+=PATCH_NOTE
        row['sideThresholdReview']=dict(direction='right',source_collision=126,complete_native_dimensions=[16,32],native_donor_map='FR_ROUTE_15',native_donor_origin=[9,11],native_source_mid=mid,previous_wrong_handed_mid=old_mid,pixel_scale=1,reviewed_binding=REVIEWED_BINDING)
        row['compositionPixelHash']=catalog.sha(preview.replacement_image(CACHE,row,imp.packed,ROOT).tobytes())
        row=json.loads(json.dumps(row,sort_keys=True));new_rows.append(row)
        pairs.append(dict(identity=list(identity(row)),module=locations[identity(row)]['module'],old_row_sha256=digest(old),new_row_sha256=digest(row),old_literal_sha256=locations[identity(row)]['literal_sha256'],new_literal_sha256=hashlib.sha256(lua(row).encode()).hexdigest(),old_donor=old_mid,new_donor=mid))
    changes={identity(r):r for r in new_rows};old_index={identity(r):r for r in old_rows};patches={};module_stats=[]
    for module in MODULES:
        actual=(ROOT/module).read_bytes().decode('utf-8');found=set();parts=[];cursor=0;untouched=[];old_count=0;already=0
        for start,end,current in literal_rows(actual):
            k=identity(current)
            if k not in changes:continue
            assert k not in found;found.add(k)
            assert digest(current)in(digest(old_index[k]),digest(changes[k])),('A reviewed source row was independently changed',k)
            old_count+=digest(current)==digest(old_index[k]);already+=digest(current)==digest(changes[k])
            chunk=actual[cursor:start];parts.extend((chunk,lua(changes[k])));untouched.append(chunk);cursor=end
        parts.append(actual[cursor:]);untouched.append(actual[cursor:]);fixed=''.join(parts)
        expected={k for k,v in locations.items()if v['module']==module};assert found==expected
        # Strip only the reviewed literals: every other character must match
        # exactly, including unrelated rows, original Lua batches and comments.
        after_spans=[(a,b)for a,b,r in literal_rows(fixed)if identity(r)in changes]
        after_chunks=[];cursor=0
        for start,end in after_spans:after_chunks.append(fixed[cursor:start]);cursor=end
        after_chunks.append(fixed[cursor:]);assert untouched==after_chunks
        before_unaffected={identity(r):r for _,_,r in literal_rows(actual)if identity(r)not in changes}
        after_unaffected={identity(r):r for _,_,r in literal_rows(fixed)if identity(r)not in changes}
        assert before_unaffected==after_unaffected
        patches[module]=fixed
        module_stats.append(dict(module=module,changed_row_literals=len(found),old_rows=old_count,already_corrected_rows=already,unaffected_rows=len(before_unaffected),unaffected_rows_structurally_identical=True,all_bytes_outside_target_literals_identical=True,untouched_chunks_sha256=hashlib.sha256(''.join(untouched).encode()).hexdigest(),before_sha256=hashlib.sha256(actual.encode()).hexdigest(),after_sha256=hashlib.sha256(fixed.encode()).hexdigest()))
        candidate=OUT/'candidate-modules'/Path(module).name;candidate.parent.mkdir(exist_ok=True);candidate.write_bytes(fixed.encode())
    (OUT/'old-rows.json').write_text(json.dumps(old_rows,sort_keys=True,indent=2)+'\n');(OUT/'new-rows.json').write_text(json.dumps(new_rows,sort_keys=True,indent=2)+'\n')
    (OUT/'row-replacement-inventory.json').write_text(json.dumps(dict(binding_sha256=binding_hash,replacements=pairs,modules=module_stats),sort_keys=True,indent=2)+'\n')
    (OUT/'native-scenes.json').write_text(json.dumps([dict(game=s['game'],map=s['id'])for s in scenes],indent=2)+'\n')
    (OUT/'affected-scenes.json').write_text(json.dumps([dict(game=s['game'],map=s['id'])for s in scenes],indent=2)+'\n')
    (OUT/'scene-entrance-proof.json').write_text(json.dumps(scenes,sort_keys=True,indent=2)+'\n')
    proof=dict(status='candidate',rows=len(new_rows),right_entrance_pairs=18,affected_scenes=len(scenes),source_and_donor_binding_sha256=binding_hash,modules=module_stats,pixel_scale=1,old_left_threshold_preserved=True,source_collision_and_warps_unchanged=True)
    if args.validate:
        options=SimpleNamespace(cache=CACHE,engine=ROOT.parent/'.tools/engine-0395',output=OUT)
        proof['previous_neutral']=ext.validate_batch(old_rows,options,ROOT);proof['fixed_neutral']=ext.validate_batch(new_rows,options,ROOT)
        proof['old_and_new_source_pixels_independently_reconstructed']=True
    if args.preview:
        proof['preview_scenes']=[]
        modules=dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(ROOT/'main.lua').read_text()))
        active=[r for module in modules for r in preview.read_reviewed(ROOT/module)]
        previous=[old_index.get(identity(r),r)for r in active];fixed=[changes.get(identity(r),r)for r in active]
        for scene in scenes:
            game,name=scene['game'],scene['id']
            if args.route38_only and name!='ROUTE_38':continue
            before=preview.map_preview(CACHE,OUT,game,name,game+'-'+name+'-previous',previous,imp.packed,1,ROOT)
            after=preview.map_preview(CACHE,OUT,game,name,game+'-'+name+'-fixed',fixed,imp.packed,1,ROOT)
            assert before['replaced_occurrences']==after['replaced_occurrences']==after['visible_cells']
            old=Image.open(OUT/(game+'-'+name+'-previous-after-native.png')).convert('RGBA');new=Image.open(OUT/(game+'-'+name+'-fixed-after-native.png')).convert('RGBA')
            coords={(e['x'],e['y'])for e in scene['entrances']}
            # Decorations and every other full-map pixel remain exact.
            assert all(old.getpixel((x,y))==new.getpixel((x,y))for y in range(old.height)for x in range(old.width)if(x//16,y//16)not in coords)
            changed=sum(old.getpixel((x*16+px,y*16+py))!=new.getpixel((x*16+px,y*16+py))for x,y in coords for py in range(16)for px in range(16))
            assert changed>0
            proof['preview_scenes'].append(dict(game=game,map=name,changed_cells=2,changed_pixels=changed,every_other_full_map_pixel_unchanged=True))
            ox,oy=min(x for x,y in coords),min(y for x,y in coords);box=(max(0,ox*16-32),max(0,oy*16-32),min(old.width,ox*16+96),min(old.height,(oy+2)*16+32))
            source=Image.open(OUT/(game+'-'+name+'-fixed-before-native.png')).convert('RGBA')
            panels=[im.crop(box)for im in(source,old,new)];w,h=panels[0].size;canvas=Image.new('RGB',(w*6+64,h*2+70),'#18212b');d=ImageDraw.Draw(canvas);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
            for i,(label,im)in enumerate(zip(('Original source','Previous LEFT counterpart','Fixed native RIGHT counterpart'),panels)):
                x=16+i*(w*2+16);d.text((x,12),label,fill='white',font=font);canvas.paste(im.resize((w*2,h*2),Image.Resampling.NEAREST),(x,40))
            canvas.save(OUT/(game+'-'+name+'-threshold-comparison.png'))
    if args.activate:
        for module,fixed in patches.items():(ROOT/module).write_bytes(fixed.encode())
        proof['status']='passed';proof['activated']=True
    elif args.validate:proof['status']='passed';proof['activated']=False
    (OUT/'proof.json').write_text(json.dumps(proof,sort_keys=True,indent=2)+'\n');print(json.dumps(proof),flush=True)


if __name__=='__main__':main()
