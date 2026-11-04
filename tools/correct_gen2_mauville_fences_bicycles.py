"""Repair Mauville's native Crystal picket fences and Cerulean bicycles.

Run after the original Mauville authoring workflow. Only 45 guarded row literals
are replaced in one existing module; all other bytes remain identical. Native
art stays in the player's imports. No generated or bundled ROM artwork is used.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import struct
import subprocess
import zlib
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import catalog
import preview
import reverse_common
from gen2_side_threshold_orientation import literal_rows
from interior_review import Imports
from newbark_building_review import lua
from reverse_common import ROOT, ReverseReview
from reverse_hoenn_review import ground_ref
from reverse_kanto_review import exterior

GAMES = ('ruby', 'sapphire', 'emerald')
PAIR = 'general__mauville'
MODULE = 'mappings/reverse_gen2_mauville_complete.lua'
BASE_COMMIT = 'c995dc9037644999c8f5a557a471b39f5aeb78fc'
OUT = ROOT.parent / '.work/tileshift-v0350-mauville-corrections'
FENCE_IDS = (313,627,640,642,648,650,656,657,658,689,690,698)
BIKE_IDS = (664,665,666)
REVIEWED_BINDING = 'b4d13b79c9159cdeb0a1baf99e9bc72bec9bdd8bea45bb54dfd552e0e3721418'


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def identity(row):
    return row['game'],row['style'],row['tileset'],row['id'],row.get('map')


def rectangles(mask,width,height):
    """Coalesce exact horizontal mask runs vertically without losing pixels."""
    result=[]
    for y in range(height):
        x=0
        while x<width:
            if not mask[y*width+x]:
                x+=1
                continue
            end=x+1
            while end<width and mask[y*width+end]:end+=1
            prior=next((r for r in result if r['x']==x and r['w']==end-x and r['y']+r['h']==y),None)
            if prior is None:result.append(dict(x=x,y=y,w=end-x,h=1))
            else:prior['h']+=1
            x=end
    return result


class Review(ReverseReview):
    def __init__(self,cache):
        self.cache=Path(cache)
        reverse_common.CACHE=self.cache
        self.games=GAMES
        self.name='v0350-mauville-corrections'
        self.out=OUT
        OUT.mkdir(parents=True,exist_ok=True)
        self.imp=Imports(self.cache,ROOT.parent/'.work/tileshift-catalog')
        self.packed=self.imp.packed
        self._gb,self._refs,self.rows={},{},{}
        self.proofs={}
        original=subprocess.check_output(['git','-c','safe.directory='+str(ROOT).replace('\\','/'),
                                         '-C',str(ROOT),'show',BASE_COMMIT+':'+MODULE]).decode()
        self.old={identity(r):r for _,_,r in literal_rows(original)
                  if r['game']in GAMES and r['style']=='gen2'and r['tileset']==PAIR
                  and r['id']in FENCE_IDS+BIKE_IDS}
        assert len(self.old)==45
        self.active={}
        select=catalog.LUA.eval('function(rows)local out={}for _,r in ipairs(rows)do '
                               'if r.style=="gen2"and r.tileset=="general__mauville"and '
                               '(r.game=="ruby"or r.game=="sapphire"or r.game=="emerald")then '
                               'out[#out+1]=r end end return out end')
        modules=dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(ROOT/'main.lua').read_text()))
        for module in modules:
            text=(ROOT/module).read_text(encoding='utf-8-sig')
            if PAIR not in text:continue
            found=catalog.plain(select(catalog.LUA.execute(text)))
            for row in found if isinstance(found,list)else[]:
                assert identity(row)not in self.active
                self.active[identity(row)]=row

    def fence_art(self):
        # The complete original Saffron wooden fence is two8x16 upright
        # pickets. Keep each full pointed cap, wooden face and lower shadow.
        ref=self.gb_ref('crystal','SAFFRON_CITY',119,2)
        native=self.gb_image(ref)
        assert self.imp.cell_index('crystal')[ref['tileset'],119,2]['tiles']==[14,14,85,85]
        left=native.crop((0,0,8,16));right=native.crop((8,0,16,16))
        assert left.tobytes()==right.tobytes(), 'Native fence picket units differ'
        bg={left.getpixel(p)for p in((0,0),(7,0),(0,15),(7,15))}
        outside=exterior(left,bg)
        mask=[(x,y)not in outside for y in range(16)for x in range(8)]
        glyph=left.copy();glyph.putalpha(Image.frombytes('L',(8,16),bytes(255 if v else 0 for v in mask)))
        glyph.resize((128,256),Image.Resampling.NEAREST).save(OUT/'complete-native-crystal-picket8x16.png')
        # Native posts share a common y0 origin. Shared657 has the exact
        # original two-post horizontal fence; left/right uprights and689/690
        # meet its first/second original8px column without shifted corners.
        columns={313:(0,),627:(0,8),640:(0,8),642:(0,8),648:(0,),650:(8,),
                 656:(0,8),657:(0,8),658:(0,8),689:(8,),690:(0,),698:(0,)}
        field=ground_ref(self,'gen2');models={}
        for mid,positions in columns.items():
            parts=[]
            for offset in positions:
                for r in rectangles(mask,8,16):
                    parts.append(dict(donor=copy.deepcopy(ref),srcX=r['x'],srcY=r['y'],
                                      w=r['w'],h=r['h'],x=offset+r['x'],y=r['y']))
            assert len(parts)<=32
            art=self.composite(field,parts,'mauville_complete_native_crystal_upright_fence_'+str(mid))
            art['overMask']='0'*256;models[mid]=art
        self.proofs['fence']=dict(native_map='SAFFRON_CITY',native_reference=ref,
              native_complete_fence=[14,14,85,85],native_whole_picket_dimensions=[8,16],
              original_left_and_right_pickets_identical=True,source_network_columns=columns,
              common_picket_y=0,all_complete_caps_faces_and_feet_preserved=True,
              removed_pixels='only connected original field outside complete native pickets',
              native_picket_rgba_sha256=catalog.sha(glyph.tobytes()),pixel_scale=1,
              no_rotated_pickets=True,no_generated_art=True)
        return models

    def bike_art(self):
        source=self.imp.gb('red','BIKE_SHOP')[0].crop((0,32,40,48))
        outside=exterior(source,{(255,255,255,255),(170,170,170,255)})
        mask=Image.new('L',source.size)
        mask.putdata([0 if(x,y)in outside else 255 for y in range(16)for x in range(40)])
        assert mask.getbbox()==(8,0,32,16)
        assert all(mask.getpixel((x,y))for y in range(16)for x in range(40)
                   if source.getpixel((x,y))[0]in(0,85)), 'A native tire/frame/handlebar pixel was removed'
        source.putalpha(mask)
        glyph=source.crop((8,0,32,16))
        glyph_mask=[glyph.getpixel((x,y))[3]>0 for y in range(16)for x in range(24)]
        parts={x:[]for x in range(3)}
        for offset in(0,24):
            for r in rectangles(glyph_mask,24,16):
                left,right=offset+r['x'],offset+r['x']+r['w']
                for cell in range(left//16,(right-1)//16+1):
                    a,b=max(left,cell*16),min(right,(cell+1)*16)
                    parts[cell]+=self.gb_rect('red','BIKE_SHOP',8+a-offset,32+r['y'],b-a,r['h'],a-cell*16,r['y'])
        field=ground_ref(self,'gen2')
        models={}
        for cell,mid in enumerate(BIKE_IDS):
            assert len(parts[cell])<=32,('Native whole bicycle composition exceeds bounded parts',mid,len(parts[cell]))
            for part in parts[cell]:part['donorStyle']='gen1'
            art=self.composite(field,parts[cell],'mauville_whole_native_cerulean_side_view_bicycles')
            art['overMask']='0'*256
            models[mid]=art
        expected=Image.new('RGBA',(48,16))
        for x in(0,16,32):expected.paste(self.gb_image(field),(x,0))
        expected.alpha_composite(glyph,(0,0));expected.alpha_composite(glyph,(24,0))
        actual=Image.new('RGBA',(48,16))
        for x,mid in enumerate(BIKE_IDS):actual.paste(self.render(models[mid]),(x*16,0))
        assert actual.tobytes()==expected.tobytes()
        actual.resize((768,256),Image.Resampling.NEAREST).save(OUT/'two-whole-cerulean-bikes48-final.png')
        self.proofs['bikes']=dict(game='red',map='BIKE_SHOP',inspection_canvas=[0,32,40,16],
             complete_native_object=[8,32,24,16],exterior_floor_only_removed=True,
             all_native_dark_tire_frame_handlebar_pixels_preserved=True,mask_sha256=catalog.sha(mask.tobytes()),
             glyph_rgba_sha256=catalog.sha(glyph.tobytes()),row_rgba_sha256=catalog.sha(actual.tobytes()),
             bicycles_per48px_row=2,bicycles_per_map=8,pixel_scale=1,parts_per_source_cell={mid:len(a['parts'])for mid,a in models.items()})
        return models

    def layout(self,game,name,spec):
        raw=(self.cache/game/'data/generated/gba/native'/spec['file']).read_bytes()
        body=raw if raw[:4]==b'SVML'else zlib.decompress(raw)
        pw,ph,w,h=struct.unpack_from('<HHHH',body,6);w,h=w or pw,h or ph;start=16+body[14]*body[15]*2
        matrix=[[struct.unpack_from('<H',body,start+4*(y*pw+x))[0]for x in range(w)]for y in range(h)]
        return matrix,catalog.sha(raw)

    def build(self,make_previews):
        arts=self.fence_art();arts.update(self.bike_art())
        source_binding=[]
        for k,old in sorted(self.old.items()):
            game,style,pair,mid,_=k
            cell=self.imp.cell_index(game)[pair,mid]
            assert old['sourceHash']==cell['pixel_sha256']and old['sourceBehavior']==cell['behavior']
            row=copy.deepcopy(old)
            for field in('kind','base','donor','parts','overMask','animated','animation','animationCategory'):
                row.pop(field,None)
            row.update(copy.deepcopy(arts[mid]))
            reason=('Complete native Crystal Saffron upright8x16 wooden pickets use one '
                    'consistent cap/foot baseline and the correctly handed source column. Shared source657 '
                    'retains the original complete two-post horizontal fence without the previous8px curb offset;689/690 '
                    'retain their actual right/left upright alignment. No post, pointed cap, face or foot is '
                    'rotated, reduced or cut. Only connected native field outside each intact post becomes the matching selected lawn.'
                    if mid in FENCE_IDS else
                    'The exact original Red Cerulean BIKE_SHOP side-view bicycle is24x16 inside its '
                    '40x16 inspected native canvas. Only surrounding floor padding/background is '
                    'omitted. Two complete native bicycles fit each48px rack row, preserving all8 '
                    'bicycles at1:1 with every original tire, frame, pedal and handlebar pixel intact. '
                    'The previously incorrect generic frontal display is removed.')
            row['evidence']=reason+' Original source pixels/layers/behavior, collision, entrances, actors, scripts and events remain unchanged.'
            row['compositionPixelHash']=catalog.sha(self.render(row).tobytes())
            row['mauvilleNativeCorrection']=dict(native_pixel_scale=1,baseline_commit=BASE_COMMIT,
                 original_row_sha256=digest(old),kind='connected_native_fence'if mid in FENCE_IDS else'whole_cerulean_bicycles')
            row=json.loads(json.dumps(row,sort_keys=True))
            self.rows[k]=row
            source_binding.append(dict(identity=list(k),old_row_sha256=digest(old),
                 rgba_sha256=cell['pixel_sha256'],layers=cell['layer_sha256'],behavior=cell['behavior']))
        assert len(self.rows)==45
        scenes=[];shared_layouts=[]
        for game in GAMES:
            warps=self.imp.table(game,'gba/warps')
            for name,spec in self.imp.table(game,'gba/native/manifest')['layouts'].items():
                if spec['pair']!=PAIR:continue
                matrix,layout_hash=self.layout(game,name,spec)
                occurrences=Counter(mid for row in matrix for mid in row)
                ids={mid:n for mid,n in occurrences.items()if(game,'gen2',PAIR,mid,None)in self.rows}
                raw=(self.cache/game/'data/generated/gba/native'/spec['file']).read_bytes()
                body=raw if raw[:4]==b'SVML'else zlib.decompress(raw)
                bw,bh=body[14],body[15]
                border=[struct.unpack_from('<H',body,16+2*i)[0]for i in range(bw*bh)]
                border_ids={mid:n for mid,n in Counter(border).items()if(game,'gen2',PAIR,mid,None)in self.rows}
                shared_layouts.append(dict(game=game,map=name,pair=PAIR,logical_layout_sha256=layout_hash,
                    logical_width=len(matrix[0]),logical_height=len(matrix),border_width=bw,border_height=bh,
                    border_ids=border,affected_body_ids=ids,affected_border_ids=border_ids,
                    affected_body_coordinates=[dict(x=x,y=y,id=mid)for y,line in enumerate(matrix)
                                               for x,mid in enumerate(line)if mid in ids],
                    warps=warps.get(name,[])))
                if not ids and not border_ids:continue
                scenes.append(dict(game=game,map=name,pair=PAIR,affected_cells=sum(ids.values()),
                                   source_ids=ids,affected_border_ids=border_ids,
                                   logical_layout_sha256=layout_hash,warps=warps.get(name,[])))
        scenes.sort(key=lambda v:(v['game'],v['map']))
        shared_layouts.sort(key=lambda v:(v['game'],v['map']))
        binding=dict(base_commit=BASE_COMMIT,source_rows=source_binding,scenes=scenes,
                     all_shared_pair_layouts=shared_layouts,native_proofs=self.proofs)
        binding_hash=digest(binding)
        (OUT/'source-binding.json').write_text(json.dumps(dict(sha256=binding_hash,binding=binding),sort_keys=True,indent=2)+'\n')
        if REVIEWED_BINDING is not None:assert binding_hash==REVIEWED_BINDING,('Reviewed source/native fence/bicycle binding changed',binding_hash)
        (OUT/'affected-scenes.json').write_text(json.dumps(scenes,sort_keys=True,indent=2)+'\n')
        (OUT/'all-shared-layouts-and-borders.json').write_text(json.dumps(shared_layouts,sort_keys=True,indent=2)+'\n')
        (OUT/'native-scenes.json').write_text(json.dumps([dict(game=s['game'],map=s['map'])for s in scenes],indent=2)+'\n')
        (OUT/'old-rows.json').write_text(json.dumps(list(self.old.values()),sort_keys=True,indent=2)+'\n')
        (OUT/'new-rows.json').write_text(json.dumps(list(self.rows.values()),sort_keys=True,indent=2)+'\n')
        self.write(OUT/'candidates.lua')
        if make_previews:
            self.preview_scenes(scenes)
        return binding_hash,scenes

    def preview_scenes(self,scenes):
        for scene in scenes:
            game,name=scene['game'],scene['map']
            spec=self.imp.table(game,'gba/native/manifest')['layouts'][name]
            matrix,_=self.layout(game,name,spec);w,h=len(matrix[0]),len(matrix)
            source=Image.new('RGBA',(w*16,h*16));before=source.copy();after=source.copy();cache={}
            for y,line in enumerate(matrix):
                for x,mid in enumerate(line):
                    k=game,'gen2',PAIR,mid,None
                    if ('source',mid)not in cache:
                        c=self.imp.cell_index(game)[PAIR,mid]
                        cache['source',mid]=preview.native_donor(self.cache,dict(game=game,tileset=PAIR,id=mid,hash=c['pixel_sha256']),self.packed)
                    native=cache['source',mid];source.paste(native,(x*16,y*16))
                    old=self.old.get(k)or self.active.get(k)
                    new=self.rows.get(k)or self.active.get(k)
                    for label,row,image in(('before',old,before),('after',new,after)):
                        if row:
                            if(label,mid)not in cache:cache[label,mid]=self.render(row)
                            tile=cache[label,mid]
                        else:tile=native
                        image.paste(tile,(x*16,y*16))
            stem=game+'-'+name
            for label,image in(('source',source),('before',before),('after',after)):image.save(OUT/(stem+'-'+label+'.png'))
            panel=Image.new('RGB',(w*32+56,h*16+90),'#18212b');d=ImageDraw.Draw(panel)
            d.text((18,12),game.title()+' / '+name+' / Crystal native fence and Cerulean bicycle correction',fill='white',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14))
            d.text((18,38),'Previous and corrected native pixels. Gameplay/source maps unchanged; GPU checks separate.',fill='#c4cdd8')
            panel.paste(before,(18,66));panel.paste(after,(38+w*16,66));panel.save(OUT/(stem+'-comparison.png'))
            changed={(x,y)for y,line in enumerate(matrix)for x,mid in enumerate(line)if(game,'gen2',PAIR,mid,None)in self.rows}
            assert all(before.getpixel((x,y))==after.getpixel((x,y))for y in range(h*16)for x in range(w*16)if(x//16,y//16)not in changed)

    def patch(self,activate):
        actual=(ROOT/MODULE).read_bytes().decode()
        pieces=[];untouched=[];cursor=0;found=set();changes=[]
        for start,end,current in literal_rows(actual):
            k=identity(current)
            if k not in self.rows:continue
            assert k not in found;found.add(k)
            assert digest(current)in(digest(self.old[k]),digest(self.rows[k])),('A scoped source row was independently changed',k)
            chunk=actual[cursor:start];pieces.extend((chunk,lua(self.rows[k])));untouched.append(chunk);cursor=end
            changes.append(dict(identity=list(k),old_row_sha256=digest(self.old[k]),new_row_sha256=digest(self.rows[k]),
                                original_literal_sha256=catalog.sha(actual[start:end].encode())))
        pieces.append(actual[cursor:]);untouched.append(actual[cursor:]);fixed=''.join(pieces)
        assert found==set(self.rows)
        cursor=0;after_chunks=[]
        for start,end,row in literal_rows(fixed):
            if identity(row)in self.rows:after_chunks.append(fixed[cursor:start]);cursor=end
        after_chunks.append(fixed[cursor:]);assert untouched==after_chunks
        old_other={identity(r):r for _,_,r in literal_rows(actual)if identity(r)not in self.rows}
        new_other={identity(r):r for _,_,r in literal_rows(fixed)if identity(r)not in self.rows}
        assert old_other==new_other
        candidate=OUT/'candidate-module.lua';candidate.write_bytes(fixed.encode())
        if activate:(ROOT/MODULE).write_bytes(fixed.encode())
        result=dict(module=MODULE,rows=45,unaffected_rows=len(old_other),all_unaffected_bytes_identical=True,
                    all_unaffected_rows_structurally_identical=True,before_sha256=catalog.sha(actual.encode()),
                    after_sha256=catalog.sha(fixed.encode()),activated=activate,changes=changes)
        (OUT/'row-replacement-inventory.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
        return result

    def validate_without_red(self):
        """A missing optional Red import must leave all bicycle source cells native."""
        from lupa.luajit21 import LuaRuntime
        from validate_animation import IMAGE_FIXTURE
        vm=LuaRuntime(unpack_returned_tuples=True,encoding=None)
        vm.globals()[b'enginePath']=str(ROOT.parent/'.tools/engine-0395/?.lua').replace('\\','/').encode()
        vm.execute(b'package.path=enginePath..";"..package.path')
        vm.execute(IMAGE_FIXTURE.encode());make=vm.globals()[b'makeData']
        def read(relative):
            if relative.startswith(b'red/'):return None
            path=(self.cache/relative.decode()).resolve()
            assert path.is_relative_to(self.cache.resolve())
            if not path.is_file():return None
            raw=path.read_bytes()
            if path.suffix in('.idx','.rgba'):
                try:raw=zlib.decompress(raw)
                except zlib.error:pass
            return raw
        def load_image(relative,raw):
            assert not relative.startswith(b'red/'),'Missing Red import bypassed read guard'
            image=Image.open(self.cache/relative.decode()).convert('RGBA')
            return make(image.width,image.height,b'rgba8',image.tobytes())
        wrap=vm.eval(b'function(callback)return function(...)return callback(...)end end')
        ctx=vm.table_from({b'read':read,b'prefix':lambda g:g+b'/',
             b'hash':wrap(lambda raw:hashlib.sha256(raw).hexdigest().encode()),
             b'newImageData':make,b'loadImage':load_image})
        decoder=vm.execute((ROOT/'lib/donor.lua').read_bytes())[b'new'](ctx)
        composer=vm.execute((ROOT/'lib/composition.lua').read_bytes())[b'new'](
             vm.table_from({b'donor':decoder,b'newImageData':make}))
        rows=vm.table();append=vm.eval(b'function(out,part)for _,r in ipairs(part)do out[#out+1]=r end end')
        values=list(self.rows.values())
        for start in range(0,len(values),24):append(rows,vm.execute(('return '+lua(values[start:start+24])).encode()))
        vm.globals()[b'rows']=rows
        vm.globals()[b'mapping']=vm.execute((ROOT/'lib/mapping.lua').read_bytes())
        vm.globals()[b'session']=vm.execute((ROOT/'lib/session.lua').read_bytes())
        vm.globals()[b'decoder']=decoder;vm.globals()[b'composer']=composer
        result=vm.execute(br'''
local indexed,errors=mapping.index(rows);assert(#errors==0,table.concat(errors,'\n'))
local warnings={}
local state=session.new({mappings=indexed,donor=decoder,newImageData=makeData,
 generations=mapping.generations,themes=mapping.themes,normalizeStyle=mapping.normalizeStyle,
 validate=mapping.validate,compose=function(row)return composer:cell(row)end,
 warn=function(message)warnings[#warnings+1]=message end})
state:select('gen2')
local skipped=0
for _,game in ipairs({'ruby','sapphire','emerald'})do
 local result=assert(state:replacements(game,'general__mauville'))
 for _,row in ipairs(rows)do if row.game==game then
  if row.id==664 or row.id==665 or row.id==666 then
   assert(result[row.id]==nil,'Missing Red import must not draw a partial or frontal bicycle fallback')
   skipped=skipped+1
  else assert(result[row.id],'Crystal fence must still render without Red')end
 end end
end
assert(skipped==9 and state.accepted==36 and state.rejected==9 and #warnings==9)
return skipped
''')
        return dict(red_reads_intentionally_unavailable=True,accepted_crystal_fence_rows=36,
                    skipped_bicycle_rows=result,partial_or_rejected_frontal_fallback=False,
                    missing_bicycles_leave_stock_gba_source_cells=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=reverse_common.CACHE)
    parser.add_argument('--preview',action='store_true')
    parser.add_argument('--validate',action='store_true')
    parser.add_argument('--activate',action='store_true')
    args=parser.parse_args();assert not args.activate or(args.validate and REVIEWED_BINDING is not None)
    review=Review(args.cache)
    binding,scenes=review.build(args.preview)
    proof=dict(status='candidate',rows=45,affected_scenes=len(scenes),binding_sha256=binding,native_proofs=review.proofs)
    if args.validate:
        proof['new_neutral']=review.validate()
        proof['missing_red_import']=review.validate_without_red()
        new=review.rows;review.rows=review.old
        proof['old_neutral']=review.validate();review.rows=new
    proof['module']=review.patch(args.activate)
    if args.validate:proof['status']='passed'
    (OUT/'proof.json').write_text(json.dumps(proof,sort_keys=True,indent=2)+'\n')
    print(json.dumps(dict(status=proof['status'],rows=45,affected_scenes=len(scenes),binding_sha256=binding,
                         candidate_sha256=proof['module']['after_sha256'],activated=args.activate)))


if __name__=='__main__':main()
