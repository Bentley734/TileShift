"""Review and apply guarded Crystal Gym roof/sign corrections.

Run --prepare --validate for private source/baseline/corrected previews, or
--activate for the validated row-only corrective pass. Historical generators
may be followed by this pass; rerunning it preserves the same literal rows.
The immutable published source commit supplies the original key inventory.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import json
import re
import struct
import subprocess
import zlib

from PIL import Image, ImageDraw

import catalog
import preview
from newbark_building_review import lua
from reverse_common import ROOT, ReverseReview
from reverse_kanto_review import exterior, runs
from reverse_oldale_review import mask_piece

GAMES = ('ruby', 'sapphire', 'emerald', 'firered', 'leafgreen')
RSE = ('ruby', 'sapphire', 'emerald')
TARGET = ROOT / 'mappings/reverse_classic_gyms_finish.lua'
BASELINE = '9a2181306689624ff3d574036179d16bbc24b06f'
SOURCE_GEOMETRY = '7c4d761e08fe2b8071ee5bb9f4b43e0bf80b4552758223d1b68a0931db16d259'
#Previously reviewed/activated rectangular-roof revision, before the native
#interior-window correction. These hashes permit that exact guarded upgrade.
PRIOR_GYM_EXISTING_ROWS = '32056da6cf9b26a180bfcb737636ce0fc7fbbd743fb9ad4b3b011483b2d449fd'
PRIOR_GYM_NEW_MODULE = 'e0688b7b51a38612894a1f0d2f00ddf19c551700177bd9b97f1434d69fc81a28'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def ordered(value):
    if isinstance(value, dict): return {key: ordered(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, list): return [ordered(item) for item in value]
    return value


class Review(ReverseReview):
    def __init__(self):
        super().__init__('classic-gyms-finish', GAMES)
        self.out = ROOT.parent / '.work/tileshift-v0350-gyms'
        self.out.mkdir(parents=True, exist_ok=True)
        self.contexts = []
        self.layouts = {}
        self.active = {}
        self.owners = {}
        self.baseline = {}
        self.baseline_owners = {}

    @staticmethod
    def baseline_text(module):
        return subprocess.check_output(['git', '-c', 'safe.directory='+ROOT.as_posix(), '-C', str(ROOT),
                                        'show', BASELINE+':'+module]).decode('utf-8-sig')

    def layout(self, game, name):
        key = game, name
        if key not in self.layouts:
            spec = self.imp.table(game, 'gba/native/manifest')['layouts'][name]
            raw = (self.cache / game / 'data/generated/gba/native' / spec['file']).read_bytes()
            data = raw if raw[:4] == b'SVML' else zlib.decompress(raw)
            pw, ph, width, height = struct.unpack_from('<HHHH', data, 6)
            width, height = width or pw, height or ph
            at = 16 + data[14] * data[15] * 2
            cells = [[struct.unpack_from('<HBB', data, at + 4*(y*pw+x)) for x in range(width)] for y in range(height)]
            self.layouts[key] = dict(game=game, map=name, pair=spec['pair'], width=width, height=height,
                                     cells=cells, file=spec['file'], file_sha256=catalog.sha(raw),
                                     warps=self.imp.table(game, 'gba/warps').get(name, []))
        return self.layouts[key]

    def inventory(self):
        wanted = {}
        for game in GAMES:
            manifest = self.imp.table(game, 'gba/native/manifest')['layouts']
            for name, warps in self.imp.table(game, 'gba/warps').items():
                if name not in manifest or not re.search(r'_(CITY|TOWN|ISLAND)$', name): continue
                for warp in warps:
                    if 'GYM' not in warp['destMap']: continue
                    layout = self.layout(game, name)
                    width, height = 6, 5 if game in RSE else 4
                    x0, y0 = warp['x']-3, warp['y']-height+1
                    if x0 < 0 or y0 < 0: continue
                    if game not in RSE:
                        # Actual imported Kanto Gyms include wider source
                        # roofs. Find the real end cap in this warp-anchored
                        # top row, rather than cropping at the old96px model.
                        assert layout['cells'][y0][x0][0] == 321
                        end = x0 + 1
                        while end < layout['width'] and layout['cells'][y0][end][0] == 322: end += 1
                        assert layout['cells'][y0][end][0] == 323
                        width = end-x0+1
                        #The gold top-cap uses city-specific source IDs;
                        #the whole matrix plus every actual RGBA/layer and
                        #behavior is pinned by SOURCE_GEOMETRY below.
                        assert y0 > 0
                        y0-=1; height+=1
                    cells = [[cell[0] for cell in row[x0:x0+width]] for row in layout['cells'][y0:y0+height]]
                    context = dict(game=game, map=name, pair=layout['pair'], entrance=warp,
                                   origin=[x0, y0], source_matrix=cells, width=width, height=height)
                    sign_ids=(597,605) if name.endswith('FORTREE_CITY') else (716,724) if name.endswith('RUSTBORO_CITY') else (772,780) if name.endswith('SAFFRON_CITY') else (352,360) if game not in RSE else ()
                    context['outside_sign_cells']=[dict(x=x,y=y,id=cell[0]) for y,row in enumerate(layout['cells']) for x,cell in enumerate(row) if cell[0] in sign_ids]
                    self.contexts.append(context)
                    ids = {mid for row in cells for mid in row}
                    for row in layout['cells'][max(0,y0-1):min(layout['height'],y0+height+3)]:
                        ids.update(cell[0] for cell in row[max(0,x0-2):min(layout['width'],x0+width+3)])
                    # Readable sign families are checked from actual map use,
                    # not inferred from a name in a mapping's role string.
                    ids.update(cell[0] for row in layout['cells'] for cell in row if cell[0] in (1, 2, 3, 304, 305, 528, 671, 679, 699, 729))
                    if warp['y'] + 1 < layout['height']:
                        ids.add(layout['cells'][warp['y']+1][warp['x']][0])
                    wanted.setdefault(game, {}).setdefault(layout['pair'], {}).update({mid: True for mid in ids})
        selected = catalog.LUA.execute('return ' + lua(wanted))
        pick = catalog.LUA.eval('function(rows,w)local out={} for _,r in ipairs(rows)do if (r.style=="gen1" or r.style=="gen2") and w[r.game] and w[r.game][r.tileset] and w[r.game][r.tileset][r.id] then out[#out+1]=r end end return out end')
        modules = dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]", (ROOT/'main.lua').read_text()))
        for module in modules:
            if module == TARGET.relative_to(ROOT).as_posix() and not (ROOT/module).exists(): continue
            rows = catalog.plain(pick(catalog.LUA.execute((ROOT/module).read_text(encoding='utf-8-sig')), selected))
            for row in rows if isinstance(rows, list) else []:
                key = row['game'], row['style'], row['tileset'], row['id']
                assert key not in self.active, key
                self.active[key] = row; self.owners[key] = module
        for module in dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]", self.baseline_text('main.lua'))):
            rows = catalog.plain(pick(catalog.LUA.execute(self.baseline_text(module)), selected))
            for row in rows if isinstance(rows, list) else []:
                key = row['game'], row['style'], row['tileset'], row['id']
                assert key not in self.baseline, key
                self.baseline[key] = row; self.baseline_owners[key] = module
        self.contexts.sort(key=lambda c: (c['game'], c['map'], c['entrance']['destMap']))
        results = []
        for context in self.contexts:
            game, pair = context['game'], context['pair']
            width, height = context['width'], context['height']
            source = Image.new('RGBA', (width*16, height*16)); themed = {style: source.copy() for style in ('gen1', 'gen2')}
            counts = {style: Counter() for style in themed}; roof_counts = {style: 0 for style in themed}; used = {style: [] for style in themed}
            for y, mids in enumerate(context['source_matrix']):
                for x, mid in enumerate(mids):
                    cell = self.imp.cell_index(game)[pair, mid]
                    image = preview.native_donor(self.cache, dict(game=game, tileset=pair, id=mid, hash=cell['pixel_sha256']), self.packed)
                    source.paste(image, (x*16, y*16))
                    for style, output in themed.items():
                        row = self.active.get((game, style, pair, mid))
                        output.paste(self.render(row) if row else image, (x*16, y*16))
                        if row:
                            counts[style][row['role']] += 1
                            used[style].append(dict(id=mid, position=[x,y], role=row['role'], module=self.owners[game,style,pair,mid]))
                            if y < height-2 and self.render(row).tobytes() != image.tobytes(): roof_counts[style] += 1
            stem = game + '-' + context['map'] + '-' + context['entrance']['destMap']
            source.save(self.out/(stem+'-source.png'))
            canvas = Image.new('RGB', (width*16*3+48, height*16+60), '#18212b'); draw=ImageDraw.Draw(canvas)
            draw.text((4,4), stem, fill='white')
            canvas.paste(source, (4,30))
            for i,(style,output) in enumerate(themed.items(),1):
                output.save(self.out/(stem+'-'+style+'.png')); canvas.paste(output,(4+i*(width*16+16),30))
                draw.text((4+i*(width*16+16),17), style, fill='white')
            canvas.save(self.out/(stem+'-comparison.png'))
            results.append(dict(context, converted_roof_cells=roof_counts, converted_roles={s:dict(c) for s,c in counts.items()}, converted_cells=used, comparison=stem+'-comparison.png'))
        report = dict(status='actual warp-anchored native source inventory; not a runtime validation', gyms=len(results),
                      games=GAMES, contexts=results,
                      converted_roof_occurrences_by_style={style:sum(r['converted_roof_cells'][style] for r in results) for style in ('gen1','gen2')})
        (self.out/'inventory.json').write_text(json.dumps(report,indent=2)+'\n')
        return report

    def base_for(self, context):
        game, pair = context['game'], context['pair']
        if pair == 'general__rustboro':
            row = self.active.get((game, 'gen2', pair, 699))
            if row and row.get('donor'): return copy.deepcopy(row['donor'])
        if pair == 'general__sootopolis':
            row = self.active.get((game, 'gen2', pair, 729))
            if row and row.get('donor'): return copy.deepcopy(row['donor'])
        for mids in context['source_matrix'][:context['height']-2]:
            for mid in mids:
                row = self.active.get((game, 'gen2', pair, mid))
                if row and row.get('base'): return copy.deepcopy(row['base'])
        return self.gb_ref('crystal', 'PALLET_TOWN', 1, 0)

    def native_rect(self, map_id, sx, sy, width=16, height=16, dx=0, dy=0):
        return self.gb_rect('crystal', map_id, sx, sy, width, height, dx, dy)

    def rse_model(self, context):
        ox, oy = 256, 224
        raw = {}
        compact = context['map'].endswith('LAVARIDGE_TOWN')
        for y in range(3):
            for x in range(6):
                sx = 0 if x == 0 else 80 if x == 5 else 16
                #435 is shared by the middle roof and center of its bottom
                #row. Keep all three-row fill plain, and carry the complete
                #native two-pixel bottom frame in the facade cells below.
                sy = (0, 8, 8)[y]
                raw[x,y] = self.composite(None, self.native_rect('VIOLET_CITY', ox+sx, oy+sy), 'flat_gym_roof')
        for x in range(6):
            raw[x,3] = self.composite(None, self.native_rect('VIOLET_CITY', ox+x*16, oy+32), 'complete_gym_upper_facade')
            col = (0, 1, 3, 2, 4, 5)[x]
            raw[x,4] = self.composite(None, self.native_rect('VIOLET_CITY', ox+col*16, oy+48), 'complete_gym_lower_facade')
        if compact:
            # Source Lavaridge has an80px main facade plus a separate16px
            # outdoor sign. Move the WHOLE native right window together,
            # retaining its outer frame and the unchanged door/word.
            raw[3,3]['parts'] += self.native_rect('VIOLET_CITY', ox+72, oy+40, 8, 8, 8, 8)
            raw[4,3] = self.composite(None, self.native_rect('VIOLET_CITY', ox+80, oy+32), 'compact_gym_right_window')
            raw[4,4] = self.composite(None, self.native_rect('VIOLET_CITY', ox+80, oy+48), 'compact_gym_right_base')
            ground = self.base_for(context)
            raw[5,3] = self.native(ground, 'gym_sign_unused_upper_ground')
            sign = self.gb_at('crystal', 'PALLET_TOWN', 3, 5)
            image = self.gb_image(sign)
            outside = exterior(image, set(self.gb_image(self.gb_ref('crystal', 'PALLET_TOWN', 1, 0)).get_flattened_data()))
            mask = [(px,py) not in outside for py in range(16) for px in range(16)]
            raw[5,4] = self.composite(ground, [dict(donor=sign, srcX=s['x'], srcY=s['y'], **s) for s in runs(mask)], 'native_outdoor_gym_sign')
            raw[5,4]['overMask'] = ''.join('1' if bit else '0' for bit in mask)
        for x in range(6):
            sx = 0 if x == 0 else 80 if x == 5 else 16
            raw[x,3]['parts'] = raw[x,3].get('parts', []) + self.native_rect('VIOLET_CITY', ox+sx, oy+30, 16, 2)
            if raw[x,3]['kind'] == 'native':
                raw[x,3] = self.composite(raw[x,3]['donor'], raw[x,3]['parts'], 'complete_gym_border_over_ground')
        return self.finish_model(context, raw, 3)

    def kanto_model(self, context):
        raw = {}
        palettes = preview.palette_set(self.imp.table('crystal','palettes'), self.imp.table('crystal','maps')['VIRIDIAN_CITY'], 'DAY')
        shingle = self.composite(None, self.native_rect('VIRIDIAN_CITY', 28*16+32, 4*16+8), 'native_kanto_roof_shingles')
        width = context['width']
        for y in range(3):
            for x in range(width):
                sx = 0 if x == 0 else 80 if x == width-1 else 16
                art = self.composite(None, self.native_rect('VIOLET_CITY',256+sx,224+(0,8,16)[y]), 'rectangular_kanto_gym_roof')
                source = self.render(art)
                fill = [pixel[:3] == (197,115,255) for pixel in source.get_flattened_data()]
                for part in art['parts']: part['donor']['palettes'] = copy.deepcopy(palettes)
                for part in shingle['parts']:
                    for s in runs([fill[i] and part.get('x',0) <= i%16 < part.get('x',0)+part['w']
                                   and part.get('y',0) <= i//16 < part.get('y',0)+part['h'] for i in range(256)]):
                        art['parts'].append(dict(part, srcX=part.get('srcX',0)+s['x']-part.get('x',0),
                                                 srcY=part.get('srcY',0)+s['y']-part.get('y',0), **s))
                assert len(art['parts']) <= 32
                raw[x,y] = art
        for x in range(width):
            if x in (0,width-1):
                sx = 28*16 if x == 0 else 33*16
                upper = self.native_rect('VIRIDIAN_CITY',sx,6*16+8,16,8)+self.native_rect('VIRIDIAN_CITY',sx,6*16+8,16,8,0,8)
            else:
                col = x if x < 5 else 4
                upper = self.native_rect('VIRIDIAN_CITY',(28+col)*16,6*16)
            raw[x,3] = self.composite(None, upper, 'complete_kanto_gym_upper_facade')
            if x < 3:
                parts = self.native_rect('VIRIDIAN_CITY',(28+(0,1,3)[x])*16,7*16)
            elif x == 3:
                parts = self.native_rect('VIRIDIAN_CITY',32*16,7*16)
            else:
                parts = []; left=64+(x-4)*16; right=left+16
                #The entire native8px window/panel at80..88 repeats;
                #88..96 contains the unique outer building edge and must
                #appear only once, at the actual final end cap. The former
                #84..92 repeat included that edge inside every window bank.
                strips = [(dx,80,8) for dx in range(64,width*16-8,8)] + [(width*16-8,88,8)]
                for dx,sx,segment_width in strips:
                    a,b=max(left,dx),min(right,dx+segment_width)
                    if a < b: parts += self.native_rect('VIRIDIAN_CITY',28*16+sx+a-dx,7*16,b-a,16,a-left,0)
            raw[x,4] = self.composite(None, parts, 'complete_kanto_gym_lower_facade')
        return self.finish_model(context, raw, 3)

    def finish_model(self, context, raw, roof_rows):
        width,height=context['width'],context['height']; whole=Image.new('RGBA',(width*16,height*16))
        for (x,y), art in raw.items(): whole.paste(self.render(art),(x*16,y*16))
        from reverse_hoenn_review import ground_ref
        outside=exterior(whole,set(self.gb_image(ground_ref(self,'gen2')).get_flattened_data())|{(222,255,222,255)})
        base=self.base_for(context); result={}
        for (x,y), art in raw.items():
            if art['kind']=='native' or art['role']=='native_outdoor_gym_sign':
                result[x,y]=art; continue
            mask=[(x*16+px,y*16+py) not in outside for py in range(16) for px in range(16)]
            result[x,y]=mask_piece(self,art,mask,base,y<roof_rows)
            if context['game'] in RSE and y == 3:
                result[x,y]['overMask']='1'*32+'0'*224
        # Independent full native word, window and doorway checks, before
        # exterior masks: no frame or letter is cropped to fit a source cell.
        if context['game'] in RSE:
            word=self.render(self.composite(None,self.native_rect('VIOLET_CITY',288,256,16,8),'word'))
            rightword=self.render(self.composite(None,self.native_rect('VIOLET_CITY',304,256,16,8),'word'))
            expected=Image.new('RGBA',(32,8)); expected.paste(word.crop((0,0,16,8)),(0,0)); expected.paste(rightword.crop((0,0,16,8)),(16,0))
            #The native word's top two rows contain only pink/plain trim,
            #not letters. The intact lower roof band replaces that trim;
            #every original GYM letter pixel remains at its native position.
            assert whole.crop((32,50,64,56)).tobytes()==expected.crop((0,2,32,8)).tobytes()
            native_border=self.render(self.composite(None,self.native_rect('VIOLET_CITY',272,254,16,2),'border')).crop((0,0,16,2))
            for x in range(1,5): assert whole.crop((x*16,48,x*16+16,50)).tobytes()==native_border.tobytes()
            assert len(set(whole.crop((0,49,96,50)).get_flattened_data()))==1
            assert all(pixel==(107,58,173,255) for pixel in whole.crop((1,48,95,49)).get_flattened_data())
            door=self.render(self.composite(None,self.native_rect('VIOLET_CITY',288,272),'door'))
            assert whole.crop((48,64,64,80)).tobytes()==door.tobytes()
            for src,dest in ((8,8),(72,56 if context['map'].endswith('LAVARIDGE_TOWN') else 72)):
                first=self.render(self.composite(None,self.native_rect('VIOLET_CITY',256+src,264,16,8),'window')).crop((0,0,16,8))
                assert whole.crop((dest,56,dest+16,64)).tobytes()==first.tobytes()
            native_edge=self.render(self.composite(None,self.native_rect('VIOLET_CITY',344,272,8,16),'edge')).crop((0,0,8,16))
            end=80 if context['map'].endswith('LAVARIDGE_TOWN') else 96
            assert whole.crop((end-8,64,end,80)).tobytes()==native_edge.tobytes()
            assert sum(whole.crop((dx,64,dx+8,80)).tobytes()==native_edge.tobytes() for dx in range(0,end,8))==1
            context['native_lower_right_edge_modules']=1
            context['right_edge_only_at_actual_outer_cap']=True
        else:
            first=self.render(self.composite(None,self.native_rect('VIRIDIAN_CITY',30*16,6*16,16,8),'word')).crop((0,0,16,8))
            second=self.render(self.composite(None,self.native_rect('VIRIDIAN_CITY',31*16,6*16,16,8),'word')).crop((0,0,16,8))
            expected=Image.new('RGBA',(32,8)); expected.paste(first,(0,0)); expected.paste(second,(16,0))
            assert whole.crop((32,48,64,56)).tobytes()==expected.tobytes()
            door=self.render(self.composite(None,self.native_rect('VIRIDIAN_CITY',32*16,7*16),'door'))
            assert whole.crop((48,64,64,80)).tobytes()==door.tobytes()
            assert len(set(whole.crop((0,47,width*16,48)).get_flattened_data()))==1
            assert len(set(whole.crop((1,46,width*16-1,47)).get_flattened_data()))==1
            native_pane=self.render(self.composite(None,self.native_rect('VIRIDIAN_CITY',28*16+80,7*16,8,16),'pane')).crop((0,0,8,16))
            native_edge=self.render(self.composite(None,self.native_rect('VIRIDIAN_CITY',28*16+88,7*16,8,16),'edge')).crop((0,0,8,16))
            bank=[whole.crop((dx,64,dx+8,80)) for dx in range(64,width*16,8)]
            assert len(bank)>=4 and all(pane.tobytes()==native_pane.tobytes() for pane in bank[:-1])
            assert bank[-1].tobytes()==native_edge.tobytes()
            assert sum(pane.tobytes()==native_edge.tobytes() for pane in bank)==1
            context['native_lower_right_pane_modules']=(width*16-72)//8
            context['native_lower_right_edge_modules']=1
            context['right_edge_only_at_actual_outer_cap']=True
        context['native_word_window_door_pixels_exact']=True
        context['continuous_native_lower_roof_border']=True
        return result

    def source_proof(self):
        records=[]
        for context in self.contexts:
            layout=self.layout(context['game'],context['map']); game,pair=context['game'],context['pair']; index=self.imp.cell_index(game)
            ids=sorted({mid for row in context['source_matrix'] for mid in row}|{cell['id'] for cell in context['outside_sign_cells']})
            cells=[]
            for mid in ids:
                cell=index[pair,mid]; ref=dict(game=game,tileset=pair,id=mid,hash=cell['pixel_sha256'])
                preview.native_donor(self.cache,ref,self.packed)
                for layer,expected in cell['layer_sha256'].items(): preview.native_donor(self.cache,ref,self.packed,[layer],{layer:expected})
                cells.append(dict(id=mid,rgba_sha256=cell['pixel_sha256'],layer_sha256=cell['layer_sha256'],behavior=cell['behavior']))
            records.append(dict(game=game,map=context['map'],source_layout_sha256=layout['file_sha256'],warps=layout['warps'],source_matrix=context['source_matrix'],outside_sign_cells=context['outside_sign_cells'],source_cells=cells))
        return records

    def prepare(self):
        self.inventory(); self.rows={}; changes=[]; new_keys=[]
        for context in self.contexts:
            game,pair=context['game'],context['pair']
            if not any((game,'gen2',pair,mid) in self.active for row in context['source_matrix'] for mid in row): continue
            arts=self.rse_model(context) if game in RSE else self.kanto_model(context)
            sign_arts={}
            for cell in context['outside_sign_cells']:
                mid=cell['id']; base=self.base_for(context)
                if mid in (597,716,352,772): art=self.native(base,'native_gym_sign_unused_upper_ground')
                else:
                    sign=self.gb_at('crystal','PALLET_TOWN',3,5)
                    outside=exterior(self.gb_image(sign),set(self.gb_image(self.gb_ref('crystal','PALLET_TOWN',1,0)).get_flattened_data()))
                    mask=[(px,py) not in outside for py in range(16) for px in range(16)]
                    art=self.composite(base,[dict(s,donor=sign,srcX=s['x'],srcY=s['y']) for s in runs(mask)],'native_complete_outdoor_gym_sign')
                    art['overMask']='0'*256
                    for py in range(16):
                        for px in range(16):
                            if mask[py*16+px]: assert self.render(art).getpixel((px,py))==self.gb_image(sign).getpixel((px,py))
                sign_arts[mid]=art
            width,height=context['width'],context['height']; previous=Image.new('RGBA',(width*16,height*16)); after=previous.copy()
            for y,mids in enumerate(context['source_matrix']):
                for x,mid in enumerate(mids):
                    key=game,'gen2',pair,mid; cell=self.imp.cell_index(game)[pair,mid]
                    source=preview.native_donor(self.cache,dict(game=game,tileset=pair,id=mid,hash=cell['pixel_sha256']),self.packed)
                    original=self.baseline.get(key); art=arts[x,y]
                    previous.paste(self.render(original) if original else source,(x*16,y*16)); after.paste(self.render(art),(x*16,y*16))
                    existing=self.rows.get((*key,None))
                    if existing:
                        assert self.render(existing).tobytes()==self.render(art).tobytes() and existing.get('overMask')==art.get('overMask','0'*256), ('Source key needs inconsistent Gym pieces',key)
                        continue
                    rendered=self.render(art)
                    if original and rendered.tobytes()==self.render(original).tobytes() and art.get('overMask','0'*256)==original.get('overMask','0'*256): continue
                    row=self.row(game,pair,mid,'gen2',art,
                                 'Individually reviewed whole native GBA Gym entrance/roof/sign correction. The complete rectangular roof keeps original native Crystal frame and repeatable shingle/roof bands at1:1, without the former projecting center tile or native-GBA stripe holes. Complete native GYM lettering, original windows/frames and the whole16px door remain exact. Lavaridge retains a separate actual outdoor Crystal sign, not an interior machine. Original source entrance, layout, all collisions/elevations/warps/events and source RGBA/layer/behavior guards remain unchanged.')
                    row['role']='classic_gen2_gym_flat_roof_and_native_sign'
                    if original:
                        assert all(row.get(k)==original.get(k) for k in ('game','style','tileset','id','sourceHash','sourceBehavior','map','status'))
                        changes.append(dict(game=game,style='gen2',pair=pair,id=mid,module=self.baseline_owners[key],old_row_sha256=digest(original),old=original,new=row))
                    else:
                        new_keys.append(dict(game=game,style='gen2',pair=pair,id=mid,new=row))
            for mid,art in sign_arts.items():
                key=game,'gen2',pair,mid
                if (*key,None) in self.rows: continue
                original=self.baseline.get(key)
                if original and self.render(art).tobytes()==self.render(original).tobytes() and art.get('overMask','0'*256)==original.get('overMask','0'*256): continue
                row=self.row(game,pair,mid,'gen2',art,'Individually reviewed actual exterior Gym sign from its complete native map neighborhood. The upper Gen3 badge extension clears to selected native ground; the blocked lower sign anchor receives the entire original Crystal outdoor sign, including frame and feet, at1:1. All original source text interaction, collision/elevation, warps and events remain unchanged.')
                if original:
                    assert all(row.get(k)==original.get(k) for k in ('game','style','tileset','id','sourceHash','sourceBehavior','map','status'))
                    changes.append(dict(game=game,style='gen2',pair=pair,id=mid,module=self.baseline_owners[key],old_row_sha256=digest(original),old=original,new=row))
                else: new_keys.append(dict(game=game,style='gen2',pair=pair,id=mid,new=row))
            stem=game+'-'+context['map']+'-'+context['entrance']['destMap']
            previous.save(self.out/(stem+'-previous.png')); after.save(self.out/(stem+'-candidate.png'))
            canvas=Image.new('RGB',(width*32*2+56,height*32+60),'#18212b'); draw=ImageDraw.Draw(canvas); draw.text((8,8),context['map']+' - v0.34.0 / corrected Crystal',fill='white')
            canvas.paste(previous.resize((width*32,height*32),Image.Resampling.NEAREST),(8,32)); canvas.paste(after.resize((width*32,height*32),Image.Resampling.NEAREST),(32+width*32,32)); canvas.save(self.out/(stem+'-candidate-comparison.png'))
        self.rows={key:ordered(self.rows[key]) for key in sorted(self.rows)}
        self.write(self.out/'candidates.lua')
        sources=self.source_proof()
        (self.out/'source-proposed.json').write_text(json.dumps(sources,indent=2)+'\n')
        assert digest(sources)==SOURCE_GEOMETRY, ('Unreviewed source RGBA/layers/behavior/layout/warps changed',digest(sources))
        proof=dict(status='reviewed correction against frozen published baseline; activation tracked separately',baseline_commit=BASELINE,rows=len(self.rows),changed_existing_keys=len(changes),new_keys=len(new_keys),gen1_converted_building_keys=0,source_geometry_fingerprint=digest(sources),source_contexts=sources,changes=changes,additions=new_keys,contexts=self.contexts)
        (self.out/'candidate-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
        self.outside_sign_audit()
        delta=[]
        for key,row in self.rows.items():
            old=self.active.get(key[:4])
            if old and digest(old)!=digest(row):
                assert all(old.get(k)==row.get(k) for k in ('game','style','tileset','id','map','status','sourceHash','sourceBehavior'))
                delta.append(dict(game=key[0],pair=key[2],id=key[3],module=self.owners[key[:4]],old=old,new=row,
                                  old_row_sha256=digest(old),new_row_sha256=digest(row)))
        if delta:
            (self.out/'current-refinement-proof.json').write_text(json.dumps(dict(rows=len(delta),changes=delta,
                all_40_native_features_and_continuous_borders=True,
                all_40_have_exactly_one_native_outer_right_end_cap=True,
                all_16_kanto_banks_use_complete_native_interior_modules=True),indent=2)+'\n')
        return dict(rows=len(self.rows),changed_existing_keys=len(changes),new_keys=len(new_keys),source_geometry_fingerprint=proof['source_geometry_fingerprint'])

    def outside_sign_audit(self):
        records=[]
        for context in self.contexts:
            game,pair=context['game'],context['pair']; layout=self.layout(game,context['map'])
            x0,y0=context['origin']; w,h=context['width'],context['height']
            left,top,right,bottom=max(0,x0-2),max(0,y0-1),min(layout['width'],x0+w+3),min(layout['height'],y0+h+3)
            source=Image.new('RGBA',((right-left)*16,(bottom-top)*16)); after=source.copy(); cells=[]
            for y in range(top,bottom):
                for x in range(left,right):
                    mid=layout['cells'][y][x][0]; cell=self.imp.cell_index(game)[pair,mid]
                    image=preview.native_donor(self.cache,dict(game=game,tileset=pair,id=mid,hash=cell['pixel_sha256']),self.packed)
                    row=self.rows.get((game,'gen2',pair,mid,None)) or self.active.get((game,'gen2',pair,mid))
                    source.paste(image,((x-left)*16,(y-top)*16)); after.paste(self.render(row) if row else image,((x-left)*16,(y-top)*16))
                    if not (x0<=x<x0+w and y0<=y<y0+h):
                        cells.append(dict(x=x,y=y,id=mid,source_rgba_sha256=cell['pixel_sha256'],behavior=cell['behavior'],
                                          output_rgba_sha256=catalog.sha(self.render(row).tobytes()) if row else cell['pixel_sha256'],
                                          role=row.get('role') if row else None,recipe=row))
            stem=game+'-'+context['map']+'-outside-sign-audit'
            canvas=Image.new('RGB',(source.width*4+24,source.height*2+32),'#18212b'); draw=ImageDraw.Draw(canvas)
            draw.text((4,4),context['map']+' - actual source / proposed Crystal',fill='white')
            canvas.paste(source.resize((source.width*2,source.height*2),Image.Resampling.NEAREST),(4,24))
            canvas.paste(after.resize((after.width*2,after.height*2),Image.Resampling.NEAREST),(16+source.width*2,24))
            canvas.save(self.out/(stem+'.png'))
            records.append(dict(game=game,map=context['map'],bounds=[left,top,right,bottom],outside_cells=cells,comparison=stem+'.png'))
        (self.out/'outside-sign-audit.json').write_text(json.dumps(dict(actual_warp_anchored_neighborhoods=40,contexts=records),indent=2)+'\n')

    def activate(self):
        proof=json.loads((self.out/'candidate-proof.json').read_text())
        assert proof['source_geometry_fingerprint']==SOURCE_GEOMETRY
        assert len(self.rows)==proof['rows']==717 and proof['changed_existing_keys']==522 and proof['new_keys']==195
        by_module=defaultdict(dict)
        for record in proof['changes']:
            by_module[record['module']][record['game'],record['style'],record['pair'],record['id']]=record
        sorted_records=sorted(proof['changes'],key=lambda r:(r['game'],r['style'],r['pair'],r['id']))
        current_snapshot=digest([self.active[r['game'],r['style'],r['pair'],r['id']] for r in sorted_records])
        assert current_snapshot in (PRIOR_GYM_EXISTING_ROWS,digest([r['old'] for r in sorted_records]),digest([r['new'] for r in sorted_records])), 'Refusing an unreviewed existing Gym row snapshot'
        pending=[]; reports=[]
        for module,records in sorted(by_module.items()):
            path=ROOT/module; raw=path.read_bytes(); old_lines=raw.splitlines(keepends=True); new_lines=[]; seen=set(); untouched=[]
            id_pattern=re.compile(rb'\["id"\]=(' + b'|'.join(str(k[3]).encode() for k in records) + rb')[,}]')
            changed_line_numbers=set()
            for line_number,line in enumerate(old_lines):
                stripped=line.strip().rstrip(b',')
                row=None
                if stripped.startswith(b'{') and b'["style"]="gen2"' in stripped and id_pattern.search(stripped):
                    row=catalog.plain(catalog.LUA.execute('return '+stripped.decode('utf-8')))
                key=(row.get('game'),row.get('style'),row.get('tileset'),row.get('id')) if row else None
                if key in records:
                    record=records[key]; assert key not in seen; seen.add(key)
                    changed_line_numbers.add(line_number)
                    assert digest(row)==digest(self.active[key]), ('Target Gym recipe changed during preparation',module,key)
                    assert all(row.get(k)==record['new'].get(k) for k in ('game','style','tileset','id','map','sourceHash','sourceBehavior','status'))
                    newline=b'\r\n' if line.endswith(b'\r\n') else b'\n' if line.endswith(b'\n') else b''
                    indent=line[:len(line)-len(line.lstrip())]
                    new_lines.append(line if digest(row)==digest(record['new']) else indent+lua(ordered(record['new'])).encode()+b','+newline)
                else:
                    new_lines.append(line); untouched.append(line)
            assert seen==set(records), ('Target rows must each occupy one complete literal line',module,set(records)-seen)
            replacement=b''.join(new_lines)
            assert len(new_lines)==len(old_lines)
            assert all(a==b for i,(a,b) in enumerate(zip(old_lines,new_lines)) if i not in changed_line_numbers)
            if replacement!=raw: pending.append((path,replacement))
            reports.append(dict(module=module,target_rows=len(records),changed_rows=sum(a!=b for a,b in zip(old_lines,new_lines)),before_sha256=catalog.sha(raw),after_sha256=catalog.sha(replacement),
                                unrelated_lines_sha256=catalog.sha(b''.join(untouched)),unrelated_bytes_identical=True,source_key_behavior_guards_identical=True))
        all_rows=self.rows
        self.rows={(r['game'],'gen2',r['pair'],r['id'],None):ordered(r['new']) for r in proof['additions']}
        self.write(self.out/'new-keys.lua'); new_raw=(self.out/'new-keys.lua').read_bytes(); self.rows=all_rows
        assert not TARGET.exists() or TARGET.read_bytes()==new_raw or catalog.sha(TARGET.read_bytes())==PRIOR_GYM_NEW_MODULE, 'Refusing to replace a changed new-key Gym module'
        for path,data in pending: path.write_bytes(data)
        TARGET.write_bytes(new_raw)
        keys=[dict(game=k[0],pair=k[2],mid=k[3]) for k in sorted(self.rows)]
        (self.out/'keys.json').write_text(json.dumps(keys,indent=2)+'\n')
        affected=[]; source_layouts=[]; by_pair=defaultdict(set)
        for key in self.rows: by_pair[key[0],key[2]].add(key[3])
        for game in GAMES:
            for name,spec in self.imp.table(game,'gba/native/manifest')['layouts'].items():
                ids=by_pair.get((game,spec['pair']))
                if not ids: continue
                layout=self.layout(game,name); used=Counter(cell[0] for row in layout['cells'] for cell in row if cell[0] in ids)
                if used:
                    affected.append(dict(game=game,map=name))
                    source_layouts.append(dict(game=game,map=name,source_layout_sha256=layout['file_sha256'],warps=layout['warps'],used_keys=dict(used)))
        affected.sort(key=lambda r:(r['game'],r['map']))
        (self.out/'affected-scenes.json').write_text(json.dumps(affected,indent=2)+'\n')
        report=dict(status='activated',rows=len(self.rows),existing_replacements=522,new_keys=195,new_module=TARGET.relative_to(ROOT).as_posix(),
                    new_module_sha256=catalog.sha(new_raw),source_geometry_fingerprint=SOURCE_GEOMETRY,baseline_commit=BASELINE,modules=reports,
                    key_inventory_sha256=catalog.sha((self.out/'keys.json').read_bytes()),affected_scenes=affected,source_layouts=source_layouts)
        (self.out/'activation.json').write_text(json.dumps(report,indent=2)+'\n')
        (self.out/'rows.json').write_text(json.dumps(list(self.rows.values()),indent=2)+'\n')
        return dict(status='activated',rows=717,existing_replacements=522,new_keys=195,affected_scenes=len(affected),modules=reports)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory',action='store_true')
    parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--validate',action='store_true')
    parser.add_argument('--activate',action='store_true')
    args=parser.parse_args()
    review=Review()
    if args.prepare or args.activate:
        print(json.dumps(review.prepare()))
        if args.validate or args.activate: print(json.dumps(review.validate()))
        if args.activate: print(json.dumps(review.activate()))
    else:
        report=review.inventory()
        print(json.dumps(dict(gyms=report['gyms'], converted_roof_occurrences_by_style=report['converted_roof_occurrences_by_style'])))


if __name__=='__main__': main()
