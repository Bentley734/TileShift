"""Correct frozen Crystal rock exterior recipes on all GBA hosts.

Run this correction AFTER legacy terrain/city authoring. Source cells, collision and
entrances remain intact; native geometry masks expose selected theme backgrounds.
The guard resource binds each complete previous/fixed row, every source plane,
behavior, used layout and warp definition. Re-running is byte-idempotent. Older
generators intentionally retain their original evidence; this reviewed final
correction must be reapplied after regenerating their mapping modules.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import json
from pathlib import Path
import re
import zlib

from PIL import Image, ImageDraw, ImageFont

import catalog
import preview
from reverse_common import ROOT, CACHE, ReverseReview
from native_gen2_rock_masks import OUTCROP_HASHES, BOULDER_HASH, quadrant_mask, BOULDER_MASK, OUTCROP_MASK, KANTO_CORNER_HASHES, KANTO_CORNER_MASKS, mask_digest
from reverse_kanto_review import runs
from gen2_side_threshold_orientation import literal_rows
from newbark_building_review import lua
from building_review import decode_layout

GAMES=('ruby','sapphire','emerald','firered','leafgreen')
OUT=ROOT.parent/'.work/tileshift-v0350-rock-corners'
MASKS={h:quadrant_mask(q)for q,h in enumerate(OUTCROP_HASHES)}|{BOULDER_HASH:BOULDER_MASK}|{h:KANTO_CORNER_MASKS[mid]for mid,h in KANTO_CORNER_HASHES.items()}
GUARD=Path(__file__).with_name('native_gen2_rock_transparency_guards.json')
REVIEWED_GUARDS='2cd7fded426d3218bdc981378d433931c94b6a3f46b8cc296b8342165467a8c7'
REVIEWED_SOURCE_BINDING='0674ef20c53e5410fbdb88080b2a842b3d6f94d2cb4f238c58cd73f20d57e546'
EXCLUDED_ROLE='reverse_gen2_complete_hard_chair'
MODULES=('mappings/reverse_kanto.lua','mappings/reverse_gen2_hoenn_outdoor_finish.lua',
 'mappings/reverse_gen2_hoenn_outdoor_complete.lua','mappings/reverse_gen2_lavaridge_complete.lua',
 'mappings/reverse_gen2_ever_grande_complete.lua','mappings/reverse_gen2_pacifidlog_complete.lua',
 'mappings/reverse_gen2_verdanturf_complete.lua','mappings/reverse_gen2_fallarbor_complete.lua',
 'mappings/reverse_gen2_kanto_finish.lua','mappings/reverse_gen2_kanto_complete.lua')
EXPECTED_ROWS=759
PATCH_NOTE=' Reviewed complete-object exterior contour removes only connected native donor backing at rock/cliff corners. Every original dark outline and interior brown/highlight pixel remains at native scale. The previously selected theme ground or original animated water is visible underneath; bare cave/underwater boulders explicitly use the already selected matching native floor. Source identity, planes, collision, elevations, warps and events remain unchanged.'


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def key(row):
    return tuple(row.get(n)for n in('game','style','tileset','id','map','quadrant','x','y'))


def native_mask(ref):
    return MASKS.get(ref.get('hash'))if ref.get('game')=='crystal'else None


def part_needs_trim(part):
    mask=native_mask(part.get('donor',{}))
    if mask is None:return False
    sx,sy=part.get('srcX',0),part.get('srcY',0)
    return any(not mask[(sy+y)*16+sx+x]for y in range(part['h'])for x in range(part['w']))


def active_rows():
    modules=dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(ROOT/'main.lua').read_text()))
    return [(module,row)for module in modules for row in preview.read_reviewed(ROOT/module)]


def audit():
    OUT.mkdir(exist_ok=True)
    candidates=[];all_rows=[];summary=Counter();roles=Counter();backgrounds=Counter()
    for module,row in active_rows():
            if row.get('game')not in GAMES or row.get('style')!='gen2':continue
            all_rows.append((module,row))
            direct=native_mask(row.get('donor',{}))is not None
            base=native_mask(row.get('base',{}))is not None
            parts=[i for i,p in enumerate(row.get('parts',[]))if part_needs_trim(p)]
            if not(direct or base or parts):continue
            kind='direct'if direct else'base'if base else'parts'
            record=dict(module=module,key=list(key(row)),kind=kind,part_indices=parts,role=row['role'],prior_row_sha256=digest(row),compositionPixelHash=row.get('compositionPixelHash'),sourceHash=row['sourceHash'],sourceBehavior=row.get('sourceBehavior'),animated=bool(row.get('animated')),animationCategory=row.get('animationCategory'),base=row.get('base'),donor=row.get('donor'),row=row)
            candidates.append(record);summary[module]+=1;roles[row['role']]+=1;backgrounds[(kind,bool(row.get('base')),bool(row.get('animated')))]+=1
    report=dict(status='read-only inventory; no runtime recipes changed',rows=len(candidates),by_module=dict(summary),by_kind=[dict(kind=k[0],has_base=k[1],animated=k[2],rows=n)for k,n in backgrounds.items()],by_role=dict(roles),candidates=candidates)
    (OUT/'audit.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k not in('candidates','by_role')}),flush=True)
    return all_rows,candidates


def source_fields(row):
    return {k:v for k,v in row.items()if k.startswith('source')or k in('game','style','tileset','id','map','quadrant','x','y','status','role')}


def clipped_part(part):
    mask=native_mask(part['donor'])
    if mask is None:return [copy.deepcopy(part)],set()
    sx,sy=part.get('srcX',0),part.get('srcY',0);dx,dy=part.get('x',0),part.get('y',0)
    keep=[False]*256;removed=set()
    for y in range(part['h']):
        for x in range(part['w']):
            if mask[(sy+y)*16+sx+x]:keep[(dy+y)*16+dx+x]=True
            else:removed.add((dx+x,dy+y))
    pieces=[]
    for span in runs(keep):
        p=copy.deepcopy(part);p.update(span,srcX=sx+span['x']-dx,srcY=sy+span['y']-dy);pieces.append(p)
    return pieces,removed


def merge_parts(parts):
    """Join adjacent same-reference/translation runs without changing z order."""
    groups=[]
    for p in parts:
        signature={k:v for k,v in p.items()if k not in('srcX','srcY','x','y','w','h')}
        signature.update(offsetX=p.get('srcX',0)-p.get('x',0),offsetY=p.get('srcY',0)-p.get('y',0))
        if groups and groups[-1][0]==signature:groups[-1][1].append(p)
        else:groups.append((signature,[p]))
    result=[]
    for signature,group in groups:
        if native_mask(signature['donor'])is None:
            result+=group;continue
        mask=[False]*256
        for p in group:
            for y in range(p.get('y',0),p.get('y',0)+p['h']):
                for x in range(p.get('x',0),p.get('x',0)+p['w']):mask[y*16+x]=True
        for span in runs(mask):
            p={k:v for k,v in signature.items()if k not in('offsetX','offsetY')}
            p.update(span,srcX=span['x']+signature['offsetX'],srcY=span['y']+signature['offsetY']);result.append(p)
    return result


def fixed_row(review,old,all_rows):
    row=copy.deepcopy(old);removed=set();floor_proof=None
    if row.get('donor'):
        ref=row.pop('donor');assert ref['hash']==BOULDER_HASH or ref['hash']in KANTO_CORNER_HASHES.values()
        base=review.gb_ref('crystal',ref['map'],24,3)if ref['hash']==BOULDER_HASH else review.gb_ref('crystal','PALLET_TOWN',1,0)
        if ref.get('palettes'):base['palettes']=copy.deepcopy(ref['palettes'])
        if row['tileset']=='general__underwater'and row['id']==559:
            reef=[r for _,r in all_rows if r['game']==row['game']and r['style']=='gen2'and r['tileset']==row['tileset']and r['id']==531]
            assert len(reef)==1 and reef[0]['role']=='reverse_gen2_hoenn_underwater_raised_reef_fill'
            base=copy.deepcopy(reef[0]['donor'])
        floor_hash=catalog.sha(review.gb_image(base).tobytes())
        selected=[list(key(r))for _,r in all_rows if r['game']==row['game']and r['style']=='gen2'and r['tileset']==row['tileset']and r.get('compositionPixelHash')==floor_hash]
        assert selected,('Bare boulder must use the already selected local floor',key(old),floor_hash)
        row.update(kind='native_composite',base=base,parts=[dict(donor=ref,srcX=0,srcY=0,x=0,y=0,w=16,h=16)])
        floor_proof=dict(floor=base,pixel_sha256=floor_hash,existing_selected_floor_keys=selected)
    assert row.get('base')is None or native_mask(row['base'])is None,'A rock cannot be its own exterior background'
    original_parts=copy.deepcopy(row['parts']);new=[]
    for part in original_parts:
        clipped,deleted=clipped_part(part);new+=clipped;removed|=deleted
    row['parts']=merge_parts(new);assert 0<len(row['parts'])<=32,('Bounded cached recipe exceeded',key(row),len(row['parts']))
    assert removed
    if 'overMask'in row:
        mask=list(row['overMask'])
        for x,y in removed:mask[y*16+x]='0'
        row['overMask']=''.join(mask)
    row['evidence']+=PATCH_NOTE
    old_frames=preview.replacement_frames(CACHE,old,review.packed,ROOT)
    new_frames=preview.replacement_frames(CACHE,row,review.packed,ROOT)
    assert len(old_frames)==len(new_frames)
    background=copy.deepcopy(row);background['parts']=[p for p in row['parts']if native_mask(p['donor'])is None]
    if background['parts']:background_frames=preview.replacement_frames(CACHE,background,review.packed,ROOT)
    else:
        assert background.get('base'),'Every cleared exterior needs selected theme ground or water'
        background_frames=[review.gb_image(background['base'])]
    assert len(background_frames)==len(new_frames)
    for after,back in zip(new_frames,background_frames):
        assert all(after.getpixel(p)==back.getpixel(p)for p in removed),('Cleared corner differs from selected theme background',key(row))
    for before,after in zip(old_frames,new_frames):
        assert all(before.getpixel((x,y))==after.getpixel((x,y))for y in range(16)for x in range(16)if(x,y)not in removed),('Non-exterior native pixels changed',key(row))
        assert all(p[3]==255 for p in after.get_flattened_data()),('Source GBA pixels would show through',key(row))
    # Every existing animated donor, frame order and original program stays exact.
    assert [p for p in old.get('parts',[])if p.get('animated')]==[p for p in row['parts']if p.get('animated')]
    for field in('animated','animation','animationCategory'):
        assert old.get(field)==row.get(field)
    assert old.get('base')==row.get('base')or old.get('donor')
    row['compositionPixelHash']=catalog.sha(new_frames[0].tobytes())
    row['nativeRockExteriorReview']=dict(pixel_scale=1,prior_row_sha256=digest(old),
        silhouette_hashes=sorted({mask_digest(native_mask(p['donor']))for p in original_parts if native_mask(p['donor'])is not None}),
        removed_destination_mask_sha256=mask_digest([(x,y)in removed for y in range(16)for x in range(16)]),
        removed_backing_pixels=len(removed),all_nonexterior_pixels_unchanged=True,selected_background_preserved=True,
        cleared_pixels_show_selected_background=True,original_animation_preserved=True)
    assert source_fields(old)==source_fields(row)
    row=json.loads(json.dumps(row,sort_keys=True))
    proof=dict(key=list(key(row)),old_sha256=digest(old),new_sha256=digest(row),source_fields_sha256=digest(source_fields(old)),
        old_phase_pixel_sha256=[catalog.sha(im.tobytes())for im in old_frames],new_phase_pixel_sha256=[catalog.sha(im.tobytes())for im in new_frames],
        selected_background_phase_pixel_sha256=[catalog.sha(im.tobytes())for im in background_frames],cleared_pixels_equal_selected_background_all_phases=True,
        removed_backing_pixels=len(removed),removed_destination_pixels=sorted([list(p)for p in removed]),
        changed_phase_pixels=[sum(a!=b for a,b in zip(before.get_flattened_data(),after.get_flattened_data()))for before,after in zip(old_frames,new_frames)],
        original_animation_preserved=True,all_nonexterior_pixels_unchanged=True,all_output_pixels_opaque=True,floor_proof=floor_proof)
    return row,proof


def source_binding(review,rows):
    cells=[];by_pair=defaultdict(set)
    for row in sorted(rows,key=lambda r:tuple(str(v)for v in key(r))):
        c=review.imp.cell_index(row['game'])[row['tileset'],row['id']]
        assert c['pixel_sha256']==row['sourceHash']and c.get('behavior')==row.get('sourceBehavior')
        cells.append(dict(key=list(key(row)),source_fields=source_fields(row),rgba_sha256=c['pixel_sha256'],layer_sha256=c['layer_sha256'],behavior=c.get('behavior')))
        by_pair[row['game'],row['tileset']].add(row['id'])
    layouts=[]
    for game in GAMES:
        warps=review.imp.table(game,'gba/warps')
        for name,spec in sorted(review.imp.table(game,'gba/native/manifest')['layouts'].items()):
            if (game,spec['pair'])not in by_pair:continue
            path=CACHE/game/'data/generated/gba/native'/spec['file'];definition=decode_layout(path)
            ids=sorted(set(definition['mids'])&by_pair[game,spec['pair']])
            if not ids:continue
            layouts.append(dict(game=game,map=name,source_layout_sha256=catalog.sha(path.read_bytes()),source_layout_metadata=spec,affected_ids=ids,warps=warps.get(name,[])))
    backgrounds=[]
    for game in('ruby','sapphire','emerald'):
        for mid in(531,534):
            c=review.imp.cell_index(game)['general__underwater',mid]
            backgrounds.append(dict(game=game,tileset='general__underwater',id=mid,rgba_sha256=c['pixel_sha256'],layer_sha256=c['layer_sha256'],behavior=c.get('behavior')))
    return dict(cells=cells,layouts=layouts,underwater_background_source_cells=backgrounds,silhouettes=dict(outcrop=mask_digest(OUTCROP_MASK),boulder=mask_digest(BOULDER_MASK),kanto_corners={mid:mask_digest(mask)for mid,mask in KANTO_CORNER_MASKS.items()}))


def silhouette_proofs(review,rows):
    refs={p['donor']['hash']:p['donor']for row in rows for p in row.get('parts',[])if native_mask(p['donor'])is not None}
    assert set(refs)==set(MASKS)
    result=[]
    for hash_value,ref in sorted(refs.items()):
        neutral_ref=copy.deepcopy(ref)
        neutral_ref['palettes']=[[[v,v,v]for v in(255,170,85,0)]for _ in range(8)]
        neutral=review.gb_image(neutral_ref);assert catalog.sha(neutral.tobytes())==hash_value
        mask=MASKS[hash_value];pixels=list(neutral.get_flattened_data())
        assert all(mask[i]for i,p in enumerate(pixels)if p[:3]==(0,0,0)),('A true dark native outline was removed',hash_value)
        result.append(dict(donor_hash=hash_value,mask_sha256=mask_digest(mask),retained_pixels=sum(mask),removed_exterior_pixels=256-sum(mask),all_dark_outline_pixels_retained=True,
            removed_neutral_shades=dict(Counter(str(p[0])for i,p in enumerate(pixels)if not mask[i]))))
    return result


def comparisons(output,new_rows,old_rows,review):
    active=active_rows();old_index={key(r):r for r in old_rows};new_index={key(r):r for r in new_rows}
    previous=[old_index.get(key(r),r)for _,r in active];fixed=[new_index.get(key(r),r)for _,r in active]
    scenes=(('emerald','EM_PACIFIDLOG_TOWN'),('emerald','EM_LAVARIDGE_TOWN'),('emerald','EM_ROUTE114'),('emerald','EM_UNDERWATER_ROUTE126'),('emerald','EM_RUSTURF_TUNNEL'),('firered','FR_ROUTE_3'),('leafgreen','FR_ROUTE_3'))
    result=[];font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    for game,name in scenes:
        if name not in review.imp.table(game,'gba/native/manifest')['layouts']:continue
        prefix=game+'-'+name
        original,cells,_,meta=review.imp.gba(game,name);before=original.copy();after=original.copy()
        for rows,image in((previous,before),(fixed,after)):
            selected={r['id']:r for r in rows if r['game']==game and r['style']=='gen2'and r['tileset']==meta['tileset']and r.get('map',name)==name}
            for cell in cells:
                row=selected.get(cell['id'])
                if row is None:continue
                tile=review.render(row)
                for x,y in cell['coordinates']:image.paste(tile,(x*16,y*16))
        for suffix,image in(('source',original),('previous',before),('fixed',after)):image.save(output/(prefix+'-'+suffix+'.png'))
        assert before.size==after.size==original.size
        changed=[(x,y)for y in range(before.height)for x in range(before.width)if before.getpixel((x,y))!=after.getpixel((x,y))]
        if not changed:continue
        def panel(box,suffix,scale):
            images=[im.crop(box)for im in(original,before,after)];w,h=images[0].size
            canvas=Image.new('RGB',(w*scale*3+64,h*scale+84),'#18212b');draw=ImageDraw.Draw(canvas)
            for i,(label,image)in enumerate(zip(('Original GBA source','Previous Crystal corners','Fixed native silhouette'),images)):
                x=16+i*(w*scale+16);draw.text((x,14),label,font=font,fill='white');canvas.paste(image.resize((w*scale,h*scale),Image.Resampling.NEAREST),(x,50))
            path=output/(prefix+'-'+suffix+'.png');canvas.save(path);return path.name
        paths=[panel((0,0,before.width,before.height),'full-comparison',2)]
        # A true map join, chosen at the uppermost changed native corner.
        cx,cy=changed[0];left=max(0,cx//16*16-32);top=max(0,cy//16*16-32)
        box=(left,top,min(before.width,left+128),min(before.height,top+96));paths.append(panel(box,'corner-join-comparison',4))
        if name=='EM_PACIFIDLOG_TOWN':
            paths.append(panel((256,128,320,208),'ne-water-rock-comparison',6))
            paths.append(panel((0,448,80,528),'sw-water-rock-comparison',6))
        result.append(dict(game=game,map=name,changed_pixels=len(changed),previews=paths))
    return result


def prepare(output,source_root=ROOT,guarded=True,validate=False,activate=False,make_previews=False):
    output.mkdir(parents=True,exist_ok=True);review=ReverseReview('v0350-rock-corners',GAMES);review.out=output
    all_rows=active_rows();baseline=[];locations={};guards=None
    if guarded:
        guards=json.loads(GUARD.read_bytes());assert digest(guards)==REVIEWED_GUARDS,'Frozen rock guard inventory changed; fresh review required'
        expected={(e['module'],tuple(e['key'])):e for e in guards['rows']}
    else:expected=None
    for module in MODULES:
        for _,_,row in literal_rows((source_root/module).read_bytes().decode('utf-8')):
            k=(module,key(row))
            if guarded:
                if k not in expected:continue
                entry=expected[k];assert digest(row)in(entry['old_sha256'],entry['new_sha256'],entry.get('superseded_intermediate_sha256')),('Reviewed rock row changed; fresh review required',k,digest(row))
            else:
                if row['game']not in GAMES or row['style']!='gen2'or row['role']==EXCLUDED_ROLE:continue
                if not(native_mask(row.get('donor',{}))or any(part_needs_trim(p)for p in row.get('parts',[]))):continue
            assert k not in locations;locations[k]=row;baseline.append((module,row))
    assert len(baseline)==EXPECTED_ROWS and (not guarded or set(locations)==set(expected))
    changes={};proofs=[];old_rows=[];new_rows=[]
    for module,old in baseline:
        if guarded and digest(old)==expected[module,key(old)]['new_sha256']:
            row=json.loads(json.dumps(old,sort_keys=True));proof=expected[module,key(old)]['proof']
        elif guarded and digest(old)==expected[module,key(old)].get('superseded_intermediate_sha256'):
            entry=expected[module,key(old)];row=copy.deepcopy(old);row.update(copy.deepcopy(entry['final_field_patch']))
            assert source_fields(row)==source_fields(old)
            row=json.loads(json.dumps(row,sort_keys=True));proof=entry['proof'];old_rows.append(old)
        else:
            row,proof=fixed_row(review,old,all_rows);old_rows.append(old)
        if guarded:assert digest(row)==expected[module,key(old)]['new_sha256']
        changes[module,key(row)]=row;new_rows.append(row);proofs.append({**proof,'module':module})
    binding=source_binding(review,new_rows);binding_hash=digest(binding)
    if guarded:assert binding_hash==REVIEWED_SOURCE_BINDING,('Rock source RGBA/layers/behavior/layout/warps changed',binding_hash)
    (output/'source-binding.json').write_text(json.dumps(dict(sha256=binding_hash,binding=binding),sort_keys=True,indent=2)+'\n')
    module_stats=[];patches={}
    for module in MODULES:
        text=(source_root/module).read_bytes().decode('utf-8');chunks=[];cursor=0;unaffected=[];found=set();parts=[]
        for start,end,row in literal_rows(text):
            k=(module,key(row))
            if k not in changes:unaffected.append((text[start:end],digest(row)));continue
            assert k not in found;found.add(k)
            chunk=text[cursor:start];chunks.append(chunk);parts.extend((chunk,lua(changes[k])));cursor=end
        chunks.append(text[cursor:]);parts.append(text[cursor:]);fixed=''.join(parts)
        assert found=={k for k in changes if k[0]==module}
        fixed_spans=list(literal_rows(fixed));fixed_unaffected=[(fixed[a:b],digest(r))for a,b,r in fixed_spans if(module,key(r))not in changes]
        assert unaffected==fixed_unaffected,'An unrelated row literal changed'
        cursor=0;after_chunks=[]
        for start,end,row in fixed_spans:
            if(module,key(row))not in changes:continue
            after_chunks.append(fixed[cursor:start]);cursor=end
        after_chunks.append(fixed[cursor:]);assert chunks==after_chunks,'Unrelated Lua bytes changed'
        target=output/'candidate-modules'/module;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(fixed.encode())
        patches[module]=fixed.encode();module_stats.append(dict(module=module,rows=len(found),untouched_rows=len(unaffected),untouched_rows_and_all_other_bytes_identical=True,before_sha256=catalog.sha(text.encode()),after_sha256=catalog.sha(fixed.encode()),untouched_chunks_sha256=catalog.sha(''.join(chunks).encode())))
    excluded=[dict(module=m,key=list(key(r)),sha256=digest(r))for m,r in all_rows if r.get('game')in GAMES and r.get('style')=='gen2'and r['role']==EXCLUDED_ROLE]
    assert len(excluded)==18 and not any((e['module'],tuple(e['key']))in changes for e in excluded)
    if guarded:assert excluded==guards['excluded_furniture'],'An excluded furniture row changed'
    report=dict(status='candidate',rows=len(changes),modules=module_stats,source_binding_sha256=binding_hash,excluded_furniture=excluded,
        source_identity_metadata_preserved=True,all_nonexterior_pixels_unchanged=True,all_output_pixels_opaque=True,original_animation_preserved=True,
        max_cached_parts=max(len(r['parts'])for r in new_rows),phase_images=sum(len(p['new_phase_pixel_sha256'])for p in proofs),native_contours=silhouette_proofs(review,new_rows))
    if validate:
        review.rows={key(r):r for r in new_rows};report['neutral']=review.validate();report['status']='passed'
        (output/'neutral-proof.json').write_text(json.dumps(report['neutral'],sort_keys=True,indent=2)+'\n')
    if make_previews:report['map_comparisons']=comparisons(output,new_rows,old_rows,review)
    inventory=[dict(module=m,key=list(key(r)),old_sha256=next(p['old_sha256']for p in proofs if p['module']==m and tuple(p['key'])==key(r)),new_sha256=digest(r),proof=next(p for p in proofs if p['module']==m and tuple(p['key'])==key(r)))for(m,k),r in changes.items()]
    if guarded:
        for entry in inventory:
            prior=expected[entry['module'],tuple(entry['key'])]
            for field in('superseded_intermediate_sha256','final_field_patch'):
                if field in prior:entry[field]=copy.deepcopy(prior[field])
    guard_data=dict(rows=inventory,source_binding_sha256=binding_hash,excluded_furniture=excluded)
    (output/'guard-candidate.json').write_text(json.dumps(guard_data,sort_keys=True,separators=(',',':'))+'\n')
    (output/'replacement-inventory.json').write_text(json.dumps(dict(rows=proofs,modules=module_stats),sort_keys=True,indent=2)+'\n')
    (output/'corrected-keys.json').write_text(json.dumps([dict(module=m,**{n:r[n]for n in('game','style','tileset','id','map','quadrant','x','y','sourceHash','sourceBehavior','compositionPixelHash')if n in r})for(m,k),r in changes.items()],sort_keys=True,indent=2)+'\n')
    (output/'affected-scenes.json').write_text(json.dumps([dict(game=s['game'],map=s['map'])for s in binding['layouts']],indent=2)+'\n')
    (output/'old-rows.json').write_text(json.dumps(old_rows,sort_keys=True,indent=2)+'\n');(output/'new-rows.json').write_text(json.dumps(new_rows,sort_keys=True,indent=2)+'\n')
    if activate:
        assert guarded and validate and source_root.resolve()==ROOT.resolve()
        stats={s['module']:s for s in module_stats}
        for module,raw in patches.items():
            if stats[module]['before_sha256']==stats[module]['after_sha256']:continue
            assert catalog.sha((ROOT/module).read_bytes())==stats[module]['before_sha256'],('A mapping changed during review; rerun to preserve concurrent edits',module)
            original=output/'activation-baseline'/module;original.parent.mkdir(parents=True,exist_ok=True)
            if not original.exists():original.write_bytes((ROOT/module).read_bytes())
            (ROOT/module).write_bytes(raw)
        report['activated']=True
    (output/'proof.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');print(json.dumps(report),flush=True)
    return new_rows,report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--audit',action='store_true');p.add_argument('--output',type=Path,default=OUT);p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--validate',action='store_true');p.add_argument('--activate',action='store_true');p.add_argument('--preview',action='store_true');args=p.parse_args()
    if args.audit:audit()
    else:prepare(args.output,args.source_root,validate=args.validate,activate=args.activate,make_previews=args.preview)


if __name__=='__main__':main()
