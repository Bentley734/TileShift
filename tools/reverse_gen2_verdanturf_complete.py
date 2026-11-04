"""Individually review native-size Crystal counterparts for Verdanturf Town.

Only previously unmatched source keys are authored. Existing shared Mauville
recipes, original layouts, collision and entrance warps are left intact.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import struct
import zlib
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import catalog
import preview
import reverse_common
from interior_review import Imports
from reverse_common import ROOT
from reverse_gen2_hoenn_city_complete import Review as CityReview
from reverse_hoenn_review import ground_ref
from reverse_kanto_review import exterior, runs
from reverse_oldale_review import mask_piece
from reverse_oldale_review import native_piece
from reverse_gen2_hoenn_outdoor_finish import Review as OutdoorReview

GAMES = ('ruby', 'sapphire', 'emerald')
PREFIXES = dict(ruby='RU_', sapphire='SA_', emerald='EM_')
PAIR = 'general__mauville'
TARGET = ROOT / 'mappings/reverse_gen2_verdanturf_complete.lua'
REVIEWED_SOURCE_BINDING = 'd4b8731f1355b6e5e15a09c9afb5be22d61bf57e97dd47a08ccb6cb7d630518b'


class Review(CityReview):
    def __init__(self, cache):
        self.name, self.games = 'v0350-verdanturf', GAMES
        self.cache = Path(cache)
        reverse_common.CACHE = self.cache
        self.out = ROOT.parent / '.work/tileshift-v0350-verdanturf'
        self.out.mkdir(parents=True, exist_ok=True)
        self.imp = Imports(self.cache, ROOT.parent / '.work/tileshift-catalog')
        self.packed = self.imp.packed
        self.rows, self._gb, self._refs = {}, {}, {}
        self.prior, self.contracts = {}, []
        self.proofs = {}
        self.counts, self.contexts = Counter(), defaultdict(list)
        self.groups = []
        select = catalog.LUA.eval('function(rows)local out={} for _,r in ipairs(rows)do '
                                  'if r.style=="gen2" and r.tileset=="general__mauville" '
                                  'and(r.game=="ruby"or r.game=="sapphire"or r.game=="emerald") '
                                  'then out[#out+1]=r end end return out end')
        modules = dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]", (ROOT/'main.lua').read_text()))
        for module in modules:
            if ROOT/module == TARGET:
                continue
            text = (ROOT/module).read_text(encoding='utf-8-sig')
            if PAIR not in text:
                continue
            rows = catalog.plain(select(catalog.LUA.execute(text)))
            for row in rows if isinstance(rows, list) else []:
                key = row['game'], row['tileset'], row['id']
                assert key not in self.prior
                self.prior[key] = row
        self.layouts, self.sources = {}, {}
        self.missing = {}
        for game in GAMES:
            name = PREFIXES[game]+'VERDANTURF_TOWN'
            spec = self.imp.table(game, 'gba/native/manifest')['layouts'][name]
            assert spec['pair'] == PAIR
            raw = (self.cache/game/'data/generated/gba/native'/spec['file']).read_bytes()
            body = raw if raw[:4] == b'SVML' else zlib.decompress(raw)
            pw, ph, width, height = struct.unpack_from('<HHHH', body, 6)
            width, height = width or pw, height or ph
            assert (width, height) == (20, 20)
            start = 16+body[14]*body[15]*2
            self.layouts[game] = [[struct.unpack_from('<H', body, start+4*(y*pw+x))[0]
                                   for x in range(width)]for y in range(height)]
            self.sources[game] = dict(map=name, pair=PAIR, layout_sha256=catalog.sha(raw),
                                      dimensions=[width,height], warps=self.imp.table(game,'gba/warps')[name])
            self.missing[game] = Counter(mid for row in self.layouts[game]for mid in row
                                         if (game,PAIR,mid)not in self.prior)

    def inventory(self):
        binding = {}
        for game in GAMES:
            binding[game] = dict(self.sources[game], cells=[])
            index = self.imp.cell_index(game)
            items = []
            image = Image.new('RGBA', (320,320))
            for y, row in enumerate(self.layouts[game]):
                for x, mid in enumerate(row):
                    image.paste(self.source((game,PAIR,mid)),(x*16,y*16))
            image.save(self.out/(game+'-source.png'))
            grid = image.resize((960,960),Image.Resampling.NEAREST)
            draw = ImageDraw.Draw(grid)
            font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
            contacts = Image.new('RGB',(128*8,120*((len(self.missing[game])+7)//8)),'#18212b')
            contact = ImageDraw.Draw(contacts)
            for i,(mid,count)in enumerate(sorted(self.missing[game].items())):
                coordinates = [(x,y)for y,row in enumerate(self.layouts[game])for x,value in enumerate(row)if value==mid]
                cell = index[PAIR,mid]
                native = self.source((game,PAIR,mid))
                assert catalog.sha(native.tobytes()) == cell['pixel_sha256']
                binding[game]['cells'].append(dict(id=mid,source_rgba_sha256=cell['pixel_sha256'],
                                                   layer_sha256=cell['layer_sha256'],behavior=cell['behavior']))
                items.append(dict(id=mid,count=count,coordinates=coordinates,source=cell))
                for x,y in coordinates:
                    draw.rectangle((x*48,y*48,x*48+47,y*48+47),outline='red')
                    draw.text((x*48,y*48),str(mid),font=font,fill='red',stroke_width=1,stroke_fill='white')
                x,y=i%8*128,i//8*120
                contact.text((x+3,y+2),f'{mid} x{count} b{cell["behavior"]}',font=font,fill='white')
                contacts.paste(native.resize((64,64),Image.Resampling.NEAREST),(x+3,y+27))
            grid.save(self.out/(game+'-missing-grid.png'))
            contacts.save(self.out/(game+'-missing-contact.png'))
            self.preview_map(game,self.sources[game]['map'])
            (self.out/(game+'-inventory.json')).write_text(json.dumps(dict(source=self.sources[game],
              missing_cells=sum(self.missing[game].values()),missing_keys=len(items),missing=items,
              logical_matrix=self.layouts[game]),indent=2)+'\n')
        digest = catalog.sha(json.dumps(binding,sort_keys=True,separators=(',',':')).encode())
        (self.out/'source-binding.json').write_text(json.dumps(dict(sha256=digest,binding=binding),sort_keys=True,indent=2)+'\n')
        if REVIEWED_SOURCE_BINDING is not None:
            assert digest == REVIEWED_SOURCE_BINDING, 'Reviewed source pixels/layers/behavior/layout/warps changed'
        return dict(binding_sha256=digest,games={g:dict(missing_cells=sum(self.missing[g].values()),
                                                       missing_keys=len(self.missing[g]))for g in GAMES})

    raw_ref = OutdoorReview.raw_ref
    classic_cliff = OutdoorReview.classic_cliff

    @staticmethod
    def art(row):
        fields = ('kind','donor','base','parts','animated','animation','animationCategory','overMask','role')
        return {k:copy.deepcopy(row[k])for k in fields if k in row}

    def put(self, game, mid, art, reason):
        assert mid in self.missing[game], ('Attempt to change existing source key',game,mid)
        assert (game,PAIR,mid)not in self.prior
        key=(game,'gen2',PAIR,mid,None)
        if key in self.rows:
            old=self.rows[key]
            assert old['compositionPixelHash']==catalog.sha(self.render(art).tobytes()), ('Conflicting shared object pixels',key)
            assert old.get('overMask')==art.get('overMask'), ('Conflicting shared foreground',key)
            assert old.get('animated')==art.get('animated')and old.get('animation')==art.get('animation')
            return old
        return self.row(game,PAIR,mid,'gen2',art,reason+
                        ' The separately reviewed cartridge RGBA, every source layer, behavior, logical '
                        'layout and all source warps are bound to a literal frozen SHA256 contract. '
                        'Native counterpart pixels stay1:1; source collision, elevation, actors, '
                        'entrances, scripts and interactions remain unchanged.')

    def all_games(self, mids, art, reason):
        for game in GAMES:
            for mid in mids:
                if mid in self.missing[game]:
                    self.put(game,mid,art,reason)

    def object(self,game,origin,matrix,arts,destination,reason):
        ox,oy=origin;w,h=len(matrix[0]),len(matrix)
        assert all(len(row)==w for row in matrix)
        actual=[row[ox:ox+w]for row in self.layouts[game][oy:oy+h]]
        assert actual==matrix,('Whole reviewed source object changed',game,origin,actual)
        warps=[v for v in self.sources[game]['warps']if destination is not None and v['destMap']==PREFIXES[game]+destination]
        if destination is not None:
            assert len(warps)==1 and ox<=warps[0]['x']<ox+w and warps[0]['y']==oy+h-1
        before=Image.new('RGBA',(w*16,h*16));after=before.copy()
        for y,row in enumerate(matrix):
            for x,mid in enumerate(row):
                art=arts[x,y]
                if mid in self.missing[game]:self.put(game,mid,art,reason)
                recipe=self.rows.get((game,'gen2',PAIR,mid,None))or self.prior[game,PAIR,mid]
                before.paste(self.source((game,PAIR,mid)),(x*16,y*16))
                after.paste(self.render(recipe),(x*16,y*16))
        name=destination or 'object_'+str(ox)+'_'+str(oy)
        before.save(self.out/(game+'-'+name+'-source.png'))
        after.save(self.out/(game+'-'+name+'-counterpart.png'))
        self.contracts.append(dict(game=game,object=name,source_origin=origin,source_matrix=matrix,
                                   original_entrances=warps,native_pixel_scale=1,
                                   existing_source_keys_unchanged=True))

    def gardens(self):
        field=ground_ref(self,'gen2')
        self.all_games((516,517),self.native(field,'verdanturf_complete_native_lawn'),
                       'The actual complete Verdanturf lawn cells516/517 are independently reviewed '
                       'as ordinary open field, without a curb, plant, doorway or ground edge. They '
                       'receive the complete native Crystal field already selected elsewhere in this '
                       'town, removing the old mixed-lawn patches while retaining their actual behavior.')
        flower=self.art(self.prior['emerald',PAIR,4])
        flower['role']='verdanturf_whole_native_animated_flower'
        self.all_games((529,530,531,532,533,534),flower,
                       'Each separately reviewed Verdanturf decorative ground flower is a complete '
                       'single-cell flower, not part of a larger tree or a hanging pot. The complete '
                       'native Crystal8px blossom/stem and its original animation retain every native '
                       'pixel over matching field; its opaque lower flower stencil covers actor feet.')
        self.all_games((705,),self.art(self.prior['emerald',PAIR,206]),
                       'The narrow Verdanturf conifer uses the complete native16px Crystal crown, '
                       'matching its complete lower foliage/trunk in source713. Dense border crowns '
                       'retain the same native-size overlapping-canopy interpretation; a source tree '
                       'continuing beyond the actual map boundary remains naturally clipped there.')
        self.all_games((713,),self.art(self.prior['emerald',PAIR,199]),
                       'The complete lower Crystal conifer foliage, trunk and roots join the native '
                       'crown above, without shrinking a tree or omitting its original native roots.')
        floor=self.gb_image(self.gb_at('crystal','GOLDENROD_FLOWER_SHOP',4,6))
        floor_colors=set(floor.get_flattened_data())
        for mids,rect in (((691,),(32,16,16,16)),((692,700),(0,64,16,32))):
            sx,sy,w,h=rect
            model=Image.new('RGBA',(w,h));native={}
            for y in range(h//16):
                a=self.composite(None,self.gb_rect('crystal','GOLDENROD_FLOWER_SHOP',sx,sy+y*16,16,16),'verdanturf_native_wooden_flower_box')
                native[y]=a;model.paste(self.render(a),(0,y*16))
            outside=exterior(model,floor_colors)
            for y,mid in enumerate(mids):
                mask=[(x,y*16+py)not in outside for py in range(16)for x in range(16)]
                a=mask_piece(self,native[y],mask,field,False)
                self.all_games((mid,),a,
                    'The actual original Crystal Goldenrod Flower Shop supplies one complete '
                    +str(w)+'x'+str(h)+' wooden flower-box counterpart, including its entire blossom, '
                    'leaf mass and wooden container. Only connected original shop floor outside '
                    'that full object becomes the selected outdoor lawn; every retained native '
                    'flower/wood pixel is exact. The tall source692/700 is one complete32px object '
                    'across its original row seam, not duplicated16px pots or a reduced plant.')
            model.save(self.out/('native-flower-box-'+str(h)+'.png'))
            self.contracts.append(dict(object='complete wooden flower box',source_ids=mids,
                                       native_rect=['crystal','GOLDENROD_FLOWER_SHOP',*rect],pixel_scale=1))

    def small_rails_and_terrain(self):
        # These are three separate full source silhouettes, explicitly joined
        # along one straight east-of-tunnel rail; no rotated corner is inferred.
        vertical=self.art(self.prior['emerald',PAIR,320])
        self.all_games((944,846,803),vertical,
                       'The complete source view identifies944/846/803 as the upper, middle and '
                       'lower portions of one straight north/south low gray rail east of Rusturf. '
                       'The original Crystal complete native upright bar glyph stays on the same '
                       'horizontal position in all three cells; matching lawn remains around it.')
        horizontal=self.art(self.prior['emerald',PAIR,78])
        self.all_games((845,),horizontal,
                       'The four source845 cells form one straight horizontal garden rail between '
                       'the two houses. Complete native Crystal horizontal low-bar modules repeat '
                       'at one consistent pixel height over matching lawn, with no inferred turn.')
        self.all_games((159,),self.classic_cliff('front','front'),
                       'Rusturf has one complete source upper-rock/lower-opening pair at8,0/8,1. '
                       'The upper cell is solid rock above the original entry, supplied by complete '
                       'native Crystal cliff faces; it does not introduce a second cave opening.')
        entrance=self.composite(None,self.gb_rect('crystal','SILVER_CAVE_OUTSIDE',288,176,16,16),'verdanturf_whole_native_rusturf_entrance')
        self.all_games((167,),entrance,
                       'One complete original Crystal MtSilver16px cave entrance occupies Rusturf '
                       'at the original8,1 warp anchor. Its full rock frame and dark opening retain '
                       'native pixels; the separately reviewed upper rock remains above it.')
        self.all_games((557,),self.classic_cliff('se'),
                       'The actual joined northeastern town cliff ends in this southeast convex '
                       'front/right rock corner beside the public facility. Complete native Violet '
                       '8px rock caps/faces retain the handed stone mass and expose matching field '
                       'only beyond the original outer corner.')

    def homes(self):
        specs=[((0,11),[[904,905,905,906],[912,913,913,914],[920,921,907,908],[928,929,915,916]],
                'VERDANTURF_TOWN_FRIENDSHIP_RATERS_HOUSE',4,1,(2,)),
               ((8,11),[[904,905,905,905,906],[912,913,913,913,914],[920,907,921,907,908],[928,915,929,915,916]],
                'VERDANTURF_TOWN_WANDAS_HOUSE',5,2,(1,3)),
               ((16,12),[[904,905,905,906],[912,913,913,914],[920,921,907,908],[928,929,915,916]],
                'VERDANTURF_TOWN_HOUSE',4,1,(2,))]
        for origin,matrix,destination,width,door,windows in specs:
            arts=self.town_model(width,2,door,windows)
            for game in GAMES:
                self.object(game,origin,matrix,arts,destination,
                    'The whole Verdanturf home retains its complete64/80x64 source envelope, '
                    'original entrance and full window positions. Complete native Crystal New Bark '
                    'roof caps,16px door frame, entire16x8 window pairs and outside side frames '
                    'remain1:1. Only ordinary middle roof/wall modules repeat for Wanda\'s wider '
                    'house; no bitmap or unique pane is reduced or clipped. Transparent outside '
                    'roof corners reveal matching selected field.')

    def public_roofs(self):
        field=ground_ref(self,'gen2')
        for kind,mids in (('mart',(608,575,575,574)),('center',(571,572,573,581))):
            model=Image.new('RGBA',(64,64));arts={}
            for y in range(4):
                for x in range(4):
                    a=native_piece(self,'gen2',kind,x,y);arts[x,y]=a;model.paste(self.render(a),(x*16,y*16))
            outside=exterior(model,set(self.gb_image(field).get_flattened_data())|{(222,255,222,255)})
            for x,mid in enumerate(mids):
                mask=[(x*16+px,py)not in outside for py in range(16)for px in range(16)]
                roof=mask_piece(self,arts[x,0],mask,field,True)
                backing=self.classic_cliff('front','front')
                roof['base']=backing['base'];roof['parts']=backing['parts']+roof['parts']
                self.all_games((mid,),roof,
                    'The missing upper Verdanturf '+kind+' roof joins its already released full '
                    'native Crystal Cherrygrove lower roof/front. Complete native roof caps, '
                    'signage, normal roof proportions and entrance remain intact. The actual '
                    'northern cliff shows only at true roof-outside corners; no original GBA '
                    'cliff pixels or wrong lawn patch remain behind those corners.')

    def contest_hall(self):
        # Actual Ecruteak Dance Theater is64x48. One plain middle column and
        # one plain roof band/wall row make80x80, retaining the entire native
        # roof ends, one complete wooden door and the native small window.
        arts={};field=ground_ref(self,'gen2')
        for y in range(5):
            for x in range(5):
                if y<3:
                    sx=352 if x==0 else 400 if x==4 else 368
                    sy=304 if y==0 else 312 if y==1 else 320
                    parts=self.gb_rect('crystal','ECRUTEAK_CITY',sx,sy,16,16)
                elif y==3:
                    parts=self.gb_rect('crystal','ECRUTEAK_CITY',384,336,16,8)+self.gb_rect('crystal','ECRUTEAK_CITY',384,336,16,8,0,8)
                    if x in(0,4):
                        parts+=self.gb_rect('crystal','ECRUTEAK_CITY',352 if x==0 else 408,336,8,8,0 if x==0 else 8,0)
                        parts+=self.gb_rect('crystal','ECRUTEAK_CITY',352 if x==0 else 408,336,8,8,0 if x==0 else 8,8)
                else:
                    sx=(352,384,368,384,400)[x]
                    parts=self.gb_rect('crystal','ECRUTEAK_CITY',sx,336,16,16)
                arts[x,y]=self.composite(None,parts,'verdanturf_complete_native_performance_hall')
        model=Image.new('RGBA',(80,80))
        for (x,y),a in arts.items():model.paste(self.render(a),(x*16,y*16))
        colors=set(self.gb_image(field).get_flattened_data())|{(222,255,222,255)}
        colors|={c for c in model.get_flattened_data()if c[1]>c[0]and c[1]>c[2]}
        outside=exterior(model,colors)
        for (x,y),a in list(arts.items()):
            mask=[(x*16+px,y*16+py)not in outside for py in range(16)for px in range(16)]
            a=mask_piece(self,a,mask,field,y<3)
            if y==0:
                backing=self.classic_cliff('front','front');a['base']=backing['base'];a['parts']=backing['parts']+a['parts']
            arts[x,y]=a
        matrix=[[917,918,918,918,924],[925,926,926,926,932],[933,934,934,934,940],
                [941,942,467,943,927],[910,911,475,919,935]]
        for game in('ruby','sapphire'):
            self.object(game,(2,3),matrix,arts,'VERDANTURF_TOWN_CONTEST_LOBBY',
                'The complete80x80 Contest Hall uses the actual native Crystal Ecruteak Dance '
                'Theater as its same-purpose performance-building counterpart. Its complete '
                'wooden roof end caps, lower cornice, whole16px framed wooden doorway and small '
                'native window remain at original pixel size. Only plain middle roof bands, one '
                'middle column and ordinary blank wall sections repeat to retain the complete '
                'source envelope and original central entry. No unique roof edge, doorway or '
                'window is resized, cut off, or replaced with an interior device.')

    def battle_tent(self):
        field=ground_ref(self,'gen2');arts=self.town_model(5,3,2,(1,3),True)
        for x in range(5):
            a=arts[x,0];backing=self.classic_cliff('front','front')
            a['base']=backing['base'];a['parts']=backing['parts']+a['parts']
        matrix=[[946,947,948,949,950],[954,955,956,957,958],[962,963,964,965,966],
                [970,971,972,973,974],[978,979,980,981,982]]
        self.object('emerald',(1,3),matrix,arts,'VERDANTURF_TOWN_BATTLE_TENT_LOBBY',
            'The complete80x80 Battle Tent receives a native Crystal battle-facility pavilion: '
            'whole original Saffron gray roof end caps and ordinary middle shingle bands, '
            'complete native window pairs and a whole original16px doorway. The roof remains '
            'a plain uninterrupted rectangle, including the matching gray module above the '
            'entrance, following the user\'s explicit preference. Only ordinary roof/wall '
            'modules repeat at1:1 to retain the80px height. Its single doorway stays at the original3,7 '
            'Battle Tent warp; genuine outside roof corners expose the native northern cliff.')

    def build(self):
        self.gardens();self.small_rails_and_terrain();self.homes();self.public_roofs()
        self.contest_hall();self.battle_tent()
        for game in GAMES:
            absent=[mid for mid in self.missing[game]if(game,'gen2',PAIR,mid,None)not in self.rows]
            assert not absent,('Unreviewed Verdanturf source keys',game,absent)
        def ordered(v):
            if isinstance(v,dict):return{k:ordered(v[k])for k in sorted(v,key=str)}
            if isinstance(v,list):return[ordered(x)for x in v]
            return v
        self.rows={k:ordered(self.rows[k])for k in sorted(self.rows)}
        self.write(self.out/'candidates.lua')
        coverage=[self.preview_map(game,self.sources[game]['map'])for game in GAMES]
        assert all(v['replaced']==v['total']==400 for v in coverage)
        (self.out/'contracts.json').write_text(json.dumps(dict(contracts=self.contracts,proofs=self.proofs,
          source_binding=REVIEWED_SOURCE_BINDING,existing_source_keys_unchanged=True),sort_keys=True,indent=2)+'\n')
        (self.out/'coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')
        changed={(r['game'],r['tileset'],r['id'])for r in self.rows.values()}
        affected=[]
        for game in GAMES:
            for name,spec in self.imp.table(game,'gba/native/manifest')['layouts'].items():
                if spec['pair']!=PAIR:continue
                raw=(self.cache/game/'data/generated/gba/native'/spec['file']).read_bytes()
                body=raw if raw[:4]==b'SVML'else zlib.decompress(raw)
                pw,ph,w,h=struct.unpack_from('<HHHH',body,6);w,h=w or pw,h or ph;start=16+body[14]*body[15]*2
                mids=Counter(struct.unpack_from('<H',body,start+4*(y*pw+x))[0]
                             for y in range(h)for x in range(w))
                used={mid:n for mid,n in mids.items()if(game,PAIR,mid)in changed}
                if used:affected.append(dict(game=game,map=name,pair=PAIR,newly_covered_cells=sum(used.values()),source_ids=used))
        affected.sort(key=lambda r:(r['game'],r['map']))
        (self.out/'affected-maps.json').write_text(json.dumps(affected,sort_keys=True,indent=2)+'\n')
        return coverage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=reverse_common.CACHE)
    parser.add_argument('--inventory-only',action='store_true')
    parser.add_argument('--validate',action='store_true')
    parser.add_argument('--activate',action='store_true')
    args = parser.parse_args()
    review = Review(args.cache)
    inventory=review.inventory()
    if args.inventory_only:
        print(json.dumps(inventory));return
    assert not args.activate or args.validate
    coverage=review.build()
    validation=review.validate()if args.validate else None
    if args.activate:review.write(TARGET)
    print(json.dumps(dict(rows=len(review.rows),coverage=coverage,validation=validation)))


if __name__ == '__main__':
    main()
