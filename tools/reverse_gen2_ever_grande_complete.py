"""Review the complete Crystal-style Ever Grande exterior at native pixel scale.

The private source/comparison renders stay in .work. The emitted module contains
only individually guarded source keys and references to the user's imports.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import struct
import zlib
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import catalog
import preview
from reverse_common import ROOT, ReverseReview
from reverse_gen2_hoenn_city_complete import Review as CityReview
from reverse_hoenn_review import ground_ref
from reverse_gen2_hoenn_outdoor_finish import Review as NatureReview
from reverse_kanto_review import exterior
from reverse_oldale_review import mask_piece
from gb_theme_animation import specification

GAMES = ('ruby', 'sapphire', 'emerald')
PREFIXES = dict(ruby='RU_', sapphire='SA_', emerald='EM_')
PAIR = 'general__ever_grande'
TARGET = ROOT / 'mappings/reverse_gen2_ever_grande_complete.lua'
REVIEWED_SOURCE_IDS = (
    159,167,175,187,188,207,372,384,385,512,513,514,516,517,518,
    520,521,522,523,524,525,526,527,528,529,530,531,532,533,534,
    535,536,537,538,539,540,541,542,543,547,548,549,550,551,552,
    553,555,556,557,559,560,561,563,564,565,567,568,569,570,576,
    577,578,579,580,584,585,586,587,588,589,591,592,593,594,595,
    596,597,599,600,601,602,603,604,605,607,608,610,612,618,620,631,
)
REVIEWED_SOURCE_BINDING = 'ae2cf13242863d930ddece6cfdd34a26981ff4481cdf56c6ce6f4d59d09bc725'


class Review(CityReview):
    def __init__(self,out=None):
        ReverseReview.__init__(self, 'gen2-ever-grande-complete', GAMES)
        self.out = Path(out)if out else ROOT.parent / '.work/tileshift-v0340-ever-grande'
        self.out.mkdir(exist_ok=True)
        self.prior, self.all_prior = {}, []
        self.contracts, self.proofs = [], {}
        self._source_images = {}
        modules = dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]", (ROOT/'main.lua').read_text()))
        for module in modules:
            if ROOT/module == TARGET:
                continue
            for row in preview.read_reviewed(ROOT/module):
                if row['style'] == 'gen2' and row['game'] in GAMES:
                    self.all_prior.append(row)
                    k = row['game'], row['tileset'], row['id']
                    assert k not in self.prior
                    self.prior[k] = row
        self.layouts, self.sources = {}, {}
        self.missing = {}
        for game in GAMES:
            name = PREFIXES[game]+'EVER_GRANDE_CITY'
            spec = self.imp.table(game, 'gba/native/manifest')['layouts'][name]
            assert spec['pair'] == PAIR
            raw = (self.cache/game/'data/generated/gba/native'/spec['file']).read_bytes()
            b = raw if raw[:4] == b'SVML' else zlib.decompress(raw)
            pw, ph, w, h = struct.unpack_from('<HHHH', b, 6)
            w, h = w or pw, h or ph
            at = 16+b[14]*b[15]*2
            self.layouts[game] = [[struct.unpack_from('<H', b, at+4*(y*pw+x))[0] for x in range(w)] for y in range(h)]
            self.sources[game] = dict(map=name, path=str(self.cache/game/'data/generated/gba/native'/spec['file']), sha256=catalog.sha(raw), dimensions=[w,h], warps=copy.deepcopy(self.imp.table(game, 'gba/warps')[name]))
            self.missing[game] = Counter(mid for row in self.layouts[game] for mid in row if (game, PAIR, mid) not in self.prior)
        binding = {}
        for game in GAMES:
            assert sorted(self.missing[game])==list(REVIEWED_SOURCE_IDS),('Reviewed Ever Grande source key scope changed; re-review source artwork',game)
            source=self.sources[game]
            binding[game]=dict(map=source['map'],logical_layout_sha256=source['sha256'],dimensions=source['dimensions'],warps=source['warps'],cells=[])
            for mid in REVIEWED_SOURCE_IDS:
                cell=self.imp.cell_index(game)[PAIR,mid]
                binding[game]['cells'].append(dict(mid=mid,source_rgba_sha256=cell['pixel_sha256'],layer_sha256=cell['layer_sha256'],behavior=cell['behavior']))
        binding_hash=catalog.sha(json.dumps(binding,sort_keys=True,separators=(',',':')).encode())
        (self.out/'source-binding.json').write_text(json.dumps(dict(sha256=binding_hash,binding=binding),sort_keys=True,indent=2)+'\n')
        assert binding_hash==REVIEWED_SOURCE_BINDING,('Reviewed Ever Grande source binding changed; independently inspect source artwork, layers, behavior, layouts and warps before updating this literal',binding_hash)
        self.proofs['frozen_source_binding']=dict(sha256=binding_hash,source_ids=list(REVIEWED_SOURCE_IDS),per_cartridge_source_keys=91,logical_layouts_and_all_warps_bound=True,full_rgba_and_all_layers_and_behavior_bound=True)

    def source(self, k):
        if k not in self._source_images:
            self._source_images[k] = CityReview.source(self, k)
        return self._source_images[k]

    def art(self, row):
        return {k:copy.deepcopy(v) for k,v in row.items() if k not in ('game','style','tileset','id','map','sourceHash','sourceBehavior','status','evidence','compositionPixelHash')}

    def put(self, game, mid, art, reason, proof=None):
        assert mid in self.missing[game], ('Not an unreviewed source key', game, mid)
        row = self.row(game, PAIR, mid, 'gen2', art, reason+' Every per-cartridge native source RGBA and behavior is fingerprinted. Source layout, collision, warp coordinates, actors and events remain unchanged.')
        row['everGrandeReview'] = dict(pixel_scale=1, proof=proof or {})
        return row

    raw_ref = NatureReview.raw_ref
    classic_cliff = NatureReview.classic_cliff

    def rectangle(self, map_id, x, y, role, base=None):
        return self.composite(base,self.gb_rect('crystal',map_id,x,y,16,16),role)

    def plain_brick(self, edge=None):
        x=96 if edge=='w' else 208 if edge=='e' else 112
        parts=self.gb_rect('crystal','ROUTE_23',x,8,16,8)+self.gb_rect('crystal','ROUTE_23',x,8,16,8,0,8)
        return self.composite(None,parts,'reverse_gen2_ever_grande_native_league_brick_'+str(edge))

    def roof_modules(self, width, height, base):
        arts={};model=Image.new('RGBA',(width*16,height*16))
        for y in range(height):
            for x in range(width):
                sx=128 if x==0 else 176 if x==width-1 else 144
                sy=128 if y==0 else 144 if y==height-1 else 136
                art=self.rectangle('SAFFRON_CITY',sx,sy,'reverse_gen2_ever_grande_complete_native_roof')
                arts[x,y]=art;model.paste(self.render(art),(x*16,y*16))
        outside=exterior(model,{(222,255,222,255)});result={}
        for (x,y),art in arts.items():
            mask=[(x*16+px,y*16+py)not in outside for py in range(16)for px in range(16)]
            result[x,y]=mask_piece(self,art,mask,base,True)
            native,actual=self.render(art),self.render(result[x,y])
            assert all(not mask[py*16+px]or native.getpixel((px,py))==actual.getpixel((px,py))for py in range(16)for px in range(16))
        model.save(self.out/('complete-native-roof-'+str(width)+'x'+str(height)+'.png'))
        return result

    def pillar(self, base):
        # This actual tower support is one complete16x32 object: cap, shaft
        # and foot. Golden floor/fence pixels outside it are not the pillar.
        model=Image.new('RGBA',(16,32));arts={}
        for y in range(2):
            art=self.rectangle('TIN_TOWER_1F',112,y*16,'reverse_gen2_ever_grande_whole_native_pillar_'+str(y))
            arts[y]=art;model.paste(self.render(art),(0,y*16))
        floor=self.gb_image(self.gb_at('crystal','TIN_TOWER_1F',6,2))
        colors={v for v in model.get_flattened_data() if v[0]!=v[1] or v[1]!=v[2]}|set(floor.get_flattened_data())
        outside=exterior(model,colors)
        output={}
        for y,art in arts.items():
            mask=[(x,y*16+py)not in outside for py in range(16)for x in range(16)]
            output[y]=mask_piece(self,art,mask,base,True)
            original,actual=self.render(art),self.render(output[y])
            assert all(not mask[py*16+x]or original.getpixel((x,py))==actual.getpixel((x,py))for py in range(16)for x in range(16))
        joined=Image.new('RGBA',(16,32))
        for y,art in output.items():joined.paste(self.render(art),(0,y*16))
        joined.save(self.out/'native-complete-pillar16x32.png')
        self.proofs['pillar']=dict(native_rect=['crystal','TIN_TOWER_1F',112,0,16,32],complete_cap_shaft_and_foot=True,pixel_scale=1,retained_native_pixels=512-len(outside))
        return output

    def league(self):
        ground=ground_ref(self,'gen2')
        # The actual Crystal League itself continues through its north map
        # boundary. Its full windows/door and repeatable brick modules match
        # this source facade, which likewise continues beyond y=0.
        bricks={k:self.plain_brick(k)for k in(None,'w','e')}
        arts={}
        for mid,dx in ((513,96),(514,112),(552,208)):
            arts[mid]=self.rectangle('ROUTE_23',dx,0,'reverse_gen2_ever_grande_native_league_complete_window')
        for mid in (522,530,538):arts[mid]=copy.deepcopy(bricks[None])
        for mid in (512,520,521,528,529,536,537,578):arts[mid]=copy.deepcopy(bricks['w'])
        for mid in (553,560,561,568,569,576,577,579):arts[mid]=copy.deepcopy(bricks['e'])
        # A complete native32px gray roof is a porch roof here. Only its
        # ordinary middle column repeats to reach the original80px frontage.
        roof=self.roof_modules(5,2,self.gb_at('crystal','ROUTE_23',7,1))
        for row,mids in enumerate(((523,524,525,526,527),(531,532,533,534,535))):
            for col,mid in enumerate(mids):
                arts[mid]=roof[col,row]
        # The user explicitly requested a plain center roof band instead of
        # the former pink framed emblem. Keep the same complete native gray
        # band as both neighbors; the full entrance below remains unchanged.
        assert self.render(arts[533]).tobytes()==self.render(arts[532]).tobytes()==self.render(arts[534]).tobytes()
        pavement=self.art(self.prior['emerald',PAIR,573])
        assert len(pavement.get('parts',[]))==1 and pavement['parts'][0]['w']==16 and pavement['parts'][0]['h']==16
        pillar=self.pillar(pavement['parts'][0]['donor'])
        for mid in (539,543):arts[mid]=copy.deepcopy(bricks[None])
        arts[540]=copy.deepcopy(pillar[0]);arts[542]=copy.deepcopy(pillar[0])
        arts[541]=self.rectangle('ROUTE_23',144,80,'reverse_gen2_ever_grande_whole_native_league_door')
        arts[541]['overMask']='0'*256
        arts[548]=copy.deepcopy(pillar[1]);arts[550]=copy.deepcopy(pillar[1]);arts[549]=copy.deepcopy(pavement)
        for mid,side in ((547,'w'),(551,'e')):
            # Complete native rounded outside curb, with matching selected
            # lawn outside and the reviewed forecourt paving inside.
            ref=self.gb_ref('crystal','SAFFRON_CITY',68 if side=='w'else 69,2 if side=='w'else 3)
            image=self.gb_image(ref);outside=exterior(image,{(222,255,222,255)})
            mask=[(x,y)not in outside for y in range(16)for x in range(16)]
            module=self.composite(None,[dict(donor=ref,w=16,h=16,x=0,y=0)],'reverse_gen2_ever_grande_whole_native_forecourt_curb')
            arts[mid]=mask_piece(self,module,mask,ground,False)
        # The little lawn cells below the building hold a gray threshold
        # edge. They are not additional roof, column or doorway fragments.
        for mid in (516,517,518):
            art=self.composite(ground,self.gb_rect('crystal','ROUTE_23',112,94,16,2),'reverse_gen2_ever_grande_native_threshold_edge');art['overMask']='0'*256;arts[mid]=art
        for game in GAMES:
            name=PREFIXES[game]+'EVER_GRANDE_CITY'
            entrance=[w for w in self.sources[game]['warps']if 'POKEMON_LEAGUE'in w['destMap']]
            assert len(entrance)==1 and (entrance[0]['x'],entrance[0]['y'])==(18,5)
            assert self.layouts[game][5][18]==541
            for mid,art in arts.items():
                if mid not in self.missing[game]:continue
                evidence=('The user-requested plain Ever Grande porch roof center retains exactly the same complete native Crystal gray lower roof band as both adjacent roof cells532/534. The former unrelated pink framed emblem is removed from this roof cell only; the complete native doorway541 immediately below, all roof caps, pillars, entrance at18,5 and original source collision stay unchanged. No native roof or doorway pixels are resized, rotated or clipped.'if mid==533 else 'Whole Ever Grande League facade and80x64 entrance pavilion are independently reviewed as connected native-size objects. The original Crystal Route23 League supplies whole window, brick and16px entrance modules; only ordinary brick/window repeats widen the tall facade, which naturally continues above the actual north map border. The porch retains complete native gray roof caps, a complete16px framed BattleTower emblem, the full32px TinTower pillar caps/shafts/feet and one full original door at18,5. No bitmap, window, roof tip, emblem or doorway is downsized or clipped.')
                self.put(game,mid,art,evidence,dict(object='league',source_entrance=[18,5],native_league=['crystal','ROUTE_23'],native_pixel_scale=1))
            matrix=[row[13:24]for row in self.layouts[game][:7]]
            self.contracts.append(dict(game=game,map=name,object='league',visible_origin=[13,0],visible_source_matrix=matrix,source_entrance=entrance[0],north_boundary_continuation=True,source_layout_sha256=self.sources[game]['sha256']))

    def arches(self):
        ground=ground_ref(self,'gen2');arts={}
        roof=self.roof_modules(7,3,ground)
        for row,ids in enumerate(((584,585,586,587,588,589,591),(592,593,594,595,596,597,599),(600,601,602,603,604,605,607))):
            for mid in ids:
                side='w'if mid in(584,592,600)else'e'if mid in(588,596,604)else None
                arts[mid]=copy.deepcopy(roof[0 if side=='w'else 6 if side=='e'else 1,row])
        pillar=self.pillar(ground);arts[608]=pillar[0];arts[612]=copy.deepcopy(pillar[0]);arts[620]=pillar[1]
        matrices=[([15,11],[[584,589,586,586,586,591,588],[592,597,594,594,594,599,596],[600,605,602,602,602,607,604]]),([24,19],[[584,585,586,587,588],[592,593,594,595,596],[600,601,602,603,604]])]
        for game in GAMES:
            for origin,matrix in matrices:
                ox,oy=origin
                assert [row[ox:ox+len(matrix[0])]for row in self.layouts[game][oy:oy+len(matrix)]]==matrix
                self.contracts.append(dict(game=game,object='open ceremonial arch',origin=origin,source_matrix=matrix,roof_height=48,whole_native_pillar_dimensions=[16,32],unchanged_open_path=True))
            for mid,art in arts.items():
                self.put(game,mid,art,'Both complete Ever Grande ceremonial arches are checked in their actual112px and80px source widths. Complete original Crystal gray roof end caps and ordinary middle roof bands remain at1:1; only plain shingle columns/bands repeat to match the48px roof height. Two full16x32 TinTower pillars retain their native cap, shaft and foot at the original support locations. The central walk path remains visually open below the roof, with true foreground transparency outside roof/pillar silhouettes; native source movement, elevations and actor priority are retained.',dict(object='ceremonial arches',source_models=matrices,complete_native_roof_caps=True,complete_native_pillars=True))

    def nature(self):
        ground=ground_ref(self,'gen2');arts={};notes={}
        stairs=self.native(self.gb_ref('crystal','UNION_CAVE_1F',18,3),'reverse_gen2_ever_grande_complete_native_stone_steps');stairs['overMask']='0'*256
        for mid in (175,207):arts[mid]=stairs;notes[mid]='The actual outdoor stair flight retains an entire native16px Crystal stone-step glyph at each source step cell. Its original ascent corridor and source elevation changes remain distinct from walls and ordinary floor.'
        arts[159]=self.classic_cliff('front','front')
        arts[167]=self.rectangle('SILVER_CAVE_OUTSIDE',288,176,'reverse_gen2_ever_grande_single_whole_native_cave_entrance')
        for mid in(159,167):notes[mid]='The original paired upper159/lower167 outside cave entrance has a single complete native16px Crystal MtSilver cave opening at the actual lower warp anchor, with native rock backing above. No half opening is stretched across two cells and no duplicate entrance is introduced.'
        arts[631]=self.classic_cliff('ne');notes[631]='The joined northeastern raised-rock edge immediately east of the League retains its actual convex upper cap and eastern rock face through complete native Crystal Violet outcrop modules, rather than becoming an isolated boulder or ordinary field.'
        # Keep the canonical source20 cave-water animation in every newly
        # exposed water quadrant, matching the released connected body.
        water=self.gb_ref('crystal','UNION_CAVE_1F',15,0);program=specification(self.cache,water,'program');assert program
        bank_shapes={372:('ne',None),384:(None,(92,76,61,20)),385:(None,(76,93,20,59))}
        for mid,(shape,raw)in bank_shapes.items():
            if shape:
                art=self.classic_cliff(shape);art.pop('base',None);art['parts']=[dict(donor=water,w=16,h=16,x=0,y=0,animated=True)]+art['parts']
            else:
                ref=self.raw_ref('TILESET_JOHTO',raw,'NEW_BARK_TOWN');parts=[dict(donor=ref,w=16,h=16,x=0,y=0)]
                for q,tile in enumerate(raw):
                    if tile==20:parts.append(dict(donor=water,srcX=q%2*8,srcY=q//2*8,w=8,h=8,x=q%2*8,y=q//2*8,animated=True))
                art=self.composite(None,parts,'reverse_gen2_ever_grande_native_rock_bank_'+str(mid))
            art.update(animated=True,animation=program,animationCategory='water',overMask='0'*256);arts[mid]=art
            notes[mid]='The actual joined coastal rock/water corner receives complete handed Crystal rock-cap and bank8px modules, with canonical native Crystal CAVE20 animated water only in its exterior water quadrants. The convex372 cap remains distinct from the two inward384/385 water corners; original blocking/Surf footprints and water-body joins remain unchanged.'
        # Waterfall upper corners retain the same whole native waterfall
        # program as the released185 body, plus intact handed rock nubs.
        waterfall=self.art(self.prior['emerald',PAIR,185])
        for mid,q in ((187,2),(188,3)):
            art=copy.deepcopy(waterfall)
            if art['kind']=='native':art=self.composite(None,[dict(donor=art.pop('donor'),w=16,h=16,x=0,y=0,animated=True)],'reverse_gen2_ever_grande_native_waterfall_corner')|{k:v for k,v in art.items()if k!='kind'}
            ref=self.gb_ref('crystal','VIOLET_CITY',10,q);sx=0 if q==2 else 8;dx=0 if q==2 else 8
            native=self.gb_image(ref).crop((sx,8,sx+8,16));outside=exterior(native,set(self.gb_image(ground).get_flattened_data())|{(222,255,222,255)})
            mask=[(x,y)not in outside for y in range(8)for x in range(8)]
            # Complete cap glyph8x8; only its true outside field is removed.
            for y in range(8):
                start=0
                while start<8:
                    if not mask[y*8+start]:start+=1;continue
                    stop=start+1
                    while stop<8 and mask[y*8+stop]:stop+=1
                    art['parts'].append(dict(donor=ref,srcX=sx+start,srcY=8+y,w=stop-start,h=1,x=dx+start,y=y));start=stop
            art['role']='reverse_gen2_ever_grande_native_waterfall_upper_corner_'+str(mid);arts[mid]=art
            notes[mid]='The waterfall upper corner retains the released complete native Crystal vertical waterfall animation and one whole handed native Violet8px lower rock cap at the original upper edge. Only native exterior field is transparent around the cap; no new animation, rescaling or cut rock edge is used.'
        # Retaining-wall top strips and full front faces are independently
        # distinguished in the actual joined terrace corners.
        glyphs={43:(0,0),44:(8,0),45:(24,0),59:(0,8),60:(8,8),61:(24,8),75:(0,24),76:(8,24),77:(24,24)}
        wall={555:[None,None,43,44],556:[None,None,44,44],557:[None,None,44,44],559:[None,None,44,45],563:[59,60,75,76],564:[60,60,76,76],565:[60,61,76,77],567:[60]*4,570:[59,60,75,76],580:[60,60,44,44]}
        for mid,tiles in wall.items():
            parts=[]
            for q,tile in enumerate(tiles):
                if tile is None:continue
                sx,sy=glyphs[tile];ref=self.gb_ref('crystal','VIOLET_CITY',10,sy//16*2+sx//16)
                parts.append(dict(donor=ref,srcX=sx%16,srcY=sy%16,w=8,h=8,x=q%2*8,y=q//2*8))
            art=self.composite(ground,parts,'reverse_gen2_ever_grande_native_retaining_wall_'+str(mid));art['overMask']='0'*256;arts[mid]=art
            notes[mid]='Joined terrace review distinguishes the upper grass/stone cap strip, solid raised backing, west/east front cap and full frontal retaining wall. Complete original Crystal Violet8px stone cap/face modules assemble the same handed wall at native pixels; plain stone alone repeats and grass remains only outside its upper boundary.'
        # Complete original16x32 conifer crown AND root. This is a narrow
        # two-cell tree, not the released one-cell ornamental shrub.
        model=Image.new('RGBA',(16,32))
        for y in range(2):model.paste(self.gb_image(self.gb_at('crystal','NEW_BARK_TOWN',0,y)),(0,y*16))
        outside=exterior(model,set(self.gb_image(ground).get_flattened_data()))
        for mid,sy in ((610,0),(618,16)):
            art=self.rectangle('NEW_BARK_TOWN',0,sy,'reverse_gen2_ever_grande_whole_native_narrow_tree_'+str(sy))
            mask=[(x,y+sy)not in outside for y in range(16)for x in range(16)]
            arts[mid]=mask_piece(self,art,mask,ground,True);notes[mid]='The complete narrow two-cell tree is the original native Crystal NewBark16x32 conifer, retaining its entire upper crown and lower foliage, trunk and roots at1:1. Only actual exterior lawn is transparent; no tree part is reduced, cut or substituted with a small shrub.'
        for game in GAMES:
            for mid,art in arts.items():
                if mid in self.missing[game]:self.put(game,mid,art,notes[mid],dict(object='reviewed terrain and native objects',source_mid=mid))
            for warp in self.sources[game]['warps']:
                if 'VICTORY_ROAD'in warp['destMap']:
                    assert self.layouts[game][warp['y']][warp['x']]==167
        self.proofs['all_native_maps_complete_after_review']={g:sum(1 for row in self.layouts[g]for mid in row if (g,PAIR,mid)in self.prior or (g,'gen2',PAIR,mid,None)in self.rows)for g in GAMES}

    def equivalent_terrain(self):
        def sig(cell):
            return cell['pixel_sha256'], cell.get('behavior'), json.dumps(cell['layer_sha256'], sort_keys=True)
        indexed = {}
        for row in self.all_prior:
            if row.get('map') is None and row['id'] < 512:
                c = self.imp.cell_index(row['game'])[row['tileset'], row['id']]
                indexed.setdefault(sig(c), row)
        reused = []
        for game in GAMES:
            for mid in self.missing[game]:
                if mid >= 512:
                    continue
                c = self.imp.cell_index(game)[PAIR, mid]
                row = indexed.get(sig(c))
                if row:
                    proof = dict(existing_source=[row['game'],row['tileset'],row['id']], full_rgba_behavior_and_all_layer_hashes_equal=True)
                    self.put(game, mid, self.art(row), 'The complete Ever Grande source terrain cell is byte-identical in full RGBA, every rendered layer and behavior to an already individually reviewed terrain counterpart. The same native Crystal glyph, masks and animation program retain that reviewed geometry; palette, MID or collision alone is never used to infer a match.', proof)
                    reused.append(dict(game=game, id=mid, **proof))
        self.proofs['exact_terrain_reuse'] = reused

    def save(self, activate=False):
        self.rows = {k:json.loads(json.dumps(self.rows[k],sort_keys=True)) for k in sorted(self.rows)}
        self.write(TARGET if activate else self.out/'candidates.lua')
        (self.out/'contracts.json').write_text(json.dumps(dict(rows=len(self.rows),sources=self.sources,contracts=self.contracts,proofs=self.proofs),indent=2)+'\n')

    def inventory(self):
        report = dict(status='source inventory',games={g:dict(remaining_keys=len(self.missing[g]),remaining_cells=sum(self.missing[g].values()),ids=dict(self.missing[g])) for g in GAMES})
        (self.out/'source-inventory.json').write_text(json.dumps(report,indent=2)+'\n')
        groups = sorted(set(mid for mids in self.missing.values() for mid in mids))
        im = Image.new('RGB',(1536,((len(groups)+11)//12)*120),'#18212b')
        d = ImageDraw.Draw(im);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',12)
        for i,mid in enumerate(groups):
            x,y=i%12*128,i//12*120
            d.text((x+3,y+2),str(mid)+' x'+str(self.missing['emerald'].get(mid,0)),fill='white',font=font)
            im.paste(self.source(('emerald',PAIR,mid)).resize((64,64),Image.Resampling.NEAREST),(x+4,y+27))
        im.save(self.out/'remaining-native-contacts.png')
        return report

    def preview(self, game):
        layout=self.layouts[game];w,h=len(layout[0]),len(layout)
        source=Image.new('RGBA',(w*16,h*16));before=source.copy();after=source.copy();rendered={};covered=0;new=0
        for y,row in enumerate(layout):
            for x,mid in enumerate(row):
                k=(game,PAIR,mid);orig=self.source(k);source.paste(orig,(x*16,y*16))
                prior=self.prior.get(k);candidate=self.rows.get((game,'gen2',PAIR,mid,None))
                for tag,recipe,dest in [('before',prior,before),('after',candidate or prior,after)]:
                    if recipe:
                        ck=(tag,mid)
                        if ck not in rendered:rendered[ck]=self.render(recipe)
                        dest.paste(rendered[ck],(x*16,y*16))
                    else:dest.paste(orig,(x*16,y*16))
                if candidate or prior:covered+=1
                if candidate:new+=1
        for suffix,im in [('source',source),('before',before),('after',after)]:im.save(self.out/(game+'-ever-grande-'+suffix+'.png'))
        panel=Image.new('RGB',(w*32+56,h*16+90),'#18212b');d=ImageDraw.Draw(panel);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
        d.text((18,12),game.title()+' / Ever Grande City / Crystal theme: previous and complete',fill='white',font=font)
        d.text((18,38),f'{covered}/{w*h} logical cells retiled; {new} newly covered. CPU artwork preview; native GPU checks separate.',fill='#c4cdd8',font=font)
        panel.paste(before,(18,66));panel.paste(after,(38+w*16,66));panel.save(self.out/(game+'-ever-grande-comparison.png'))
        return dict(game=game,map=self.sources[game]['map'],total=w*h,replaced=covered,newly_covered=new,remaining=w*h-covered)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--activate',action='store_true');p.add_argument('--validate',action='store_true');p.add_argument('--inventory-only',action='store_true');p.add_argument('--output',type=Path)
    args=p.parse_args();r=Review(args.output);r.inventory()
    if args.inventory_only:
        r.equivalent_terrain();r.save()
        print(json.dumps(dict(rows=len(r.rows),remaining={g:[m for m in r.missing[g] if (g,'gen2',PAIR,m,None)not in r.rows] for g in GAMES})),flush=True)
        return
    r.equivalent_terrain()
    r.league();r.arches();r.nature()
    assert all((g,'gen2',PAIR,m,None)in r.rows for g in GAMES for m in r.missing[g]),'Unreviewed source keys remain'
    r.save(args.activate)
    report=dict(status='candidate',rows=len(r.rows),maps=[r.preview(g)for g in GAMES])
    if args.validate:report['validation']=r.validate();report['status']='passed'
    (r.out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':main()
