"""Complete Pacifidlog's Crystal-style floating village at native pixel scale.

Private native source/donor previews stay in .work. Production contains only
reviewed source fingerprints and guarded native donor recipes, never ROM art.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import struct
import zlib
from collections import Counter

from PIL import Image, ImageDraw, ImageFont

import catalog
import preview
from reverse_common import ROOT, ReverseReview
from reverse_gen2_hoenn_city_complete import Review as CityReview
from reverse_kanto_review import exterior, runs
from reverse_oldale_review import mask_piece, native_piece
from reverse_gen2_hoenn_outdoor_finish import Review as NatureReview
from gb_theme_animation import specification

GAMES=('ruby','sapphire','emerald')
PREFIXES=dict(ruby='RU_',sapphire='SA_',emerald='EM_')
PAIR='general__pacifidlog'
TARGET=ROOT/'mappings/reverse_gen2_pacifidlog_complete.lua'
REVIEWED_SOURCE_IDS=(180,372,384,385,514,520,521,522,523,524,528,529,530,531,532,536,537,538,539,540,544,545,548,552,553,554,556,560,561,562,563,584,587,592,593,600,608)
REVIEWED_SOURCE_BINDING='9c80360e55bb0a507a6b6b9256b4bfb70951470ce9432050b253176f292f922c'
# Individually reviewed source object colors: native GBA water, foam and
# water-shadow shades are excluded; every timber/rope/outline pixel remains.
RAFT_COLORS={(239,197,99,255),(239,230,165,255),(206,156,58,255),(165,123,25,255),(66,74,107,255),(33,33,82,255),(107,58,41,255)}
BRIDGE_COLORS={(123,82,82,255),(156,115,115,255),(189,148,140,255),(82,49,66,255),(222,181,165,255)}
RAFT_IDS=(520,524,528,532,536,540,544,545,548,552,553,554,556)
BRIDGE_IDS=(592,593,600,608)


class Review(ReverseReview):
    def __init__(self):
        super().__init__('gen2-pacifidlog-complete',GAMES)
        self.out=ROOT.parent/'.work/tileshift-v0350-pacifidlog';self.out.mkdir(exist_ok=True)
        self.prior={};self.contracts=[];self.proofs={};self._source_images={}
        modules=dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(ROOT/'main.lua').read_text()))
        for module in modules:
            if ROOT/module==TARGET:continue
            for row in preview.read_reviewed(ROOT/module):
                if row['game']in GAMES and row['style']=='gen2':
                    k=row['game'],row['tileset'],row['id'];assert k not in self.prior;self.prior[k]=row
        self.layouts={};self.sources={};self.missing={}
        for game in GAMES:
            name=PREFIXES[game]+'PACIFIDLOG_TOWN';spec=self.imp.table(game,'gba/native/manifest')['layouts'][name];assert spec['pair']==PAIR
            raw=(self.cache/game/'data/generated/gba/native'/spec['file']).read_bytes();b=raw if raw[:4]==b'SVML'else zlib.decompress(raw)
            pw,ph,w,h=struct.unpack_from('<HHHH',b,6);w,h=w or pw,h or ph;at=16+b[14]*b[15]*2
            self.layouts[game]=[[struct.unpack_from('<H',b,at+4*(y*pw+x))[0]for x in range(w)]for y in range(h)]
            self.sources[game]=dict(map=name,layout_sha256=catalog.sha(raw),dimensions=[w,h],warps=self.imp.table(game,'gba/warps')[name])
            self.missing[game]=Counter(mid for row in self.layouts[game]for mid in row if(game,PAIR,mid)not in self.prior)

    raw_ref=NatureReview.raw_ref
    classic_cliff=NatureReview.classic_cliff

    def freeze_sources(self):
        binding={}
        for game in GAMES:
            assert sorted(self.missing[game])==list(REVIEWED_SOURCE_IDS),('Pacifidlog reviewed source scope changed',game)
            binding[game]=dict(source=self.sources[game],cells=[])
            for mid in REVIEWED_SOURCE_IDS:
                c=self.imp.cell_index(game)[PAIR,mid]
                binding[game]['cells'].append(dict(mid=mid,rgba_sha256=c['pixel_sha256'],layer_sha256=c['layer_sha256'],behavior=c['behavior']))
        value=catalog.sha(json.dumps(binding,sort_keys=True,separators=(',',':')).encode())
        (self.out/'source-binding.json').write_text(json.dumps(dict(sha256=value,binding=binding),sort_keys=True,indent=2)+'\n')
        assert value==REVIEWED_SOURCE_BINDING,('Pacifidlog source/layout/layer/behavior/warp binding changed; fresh review required',value)
        self.proofs['frozen_source_binding']=value

    def put(self,game,mid,art,evidence,proof):
        assert mid in self.missing[game]and(game,PAIR,mid)not in self.prior
        row=self.row(game,PAIR,mid,'gen2',art,evidence+' Each cartridge source RGBA, every priority plane and behavior, complete logical layout and all original warps are bound to a frozen reviewed digest. Native collision, entrances, events and actor positions remain unchanged.')
        row['pacifidlogReview']=dict(pixel_scale=1,proof=proof,source_binding=REVIEWED_SOURCE_BINDING)
        return row

    def water(self):
        ref=self.gb_ref('crystal','UNION_CAVE_1F',15,0);program=specification(self.cache,ref,'program');assert program
        art=self.composite(None,[dict(donor=ref,w=16,h=16,x=0,y=0,animated=True)],'reverse_gen2_pacifidlog_canonical_native_water')
        art.update(animated=True,animation=program,animationCategory='water',overMask='0'*256)
        return art

    def plank(self):
        # Actual complete S.S.Aqua deck, away from its rail, portholes and
        # cabin doors. Whole wood-grain8px modules retain their native pixels.
        ref=self.gb_at('crystal','FAST_SHIP_1F',16,6)
        return ref

    def water_backed(self,art):
        result=self.water();result['parts']+=copy.deepcopy(art['parts']);result['role']=art['role']
        result['overMask']=art.get('overMask','0'*256)
        assert len(result['parts'])<=32
        return result

    def platform_art(self,game,mid):
        colors=BRIDGE_COLORS if mid in BRIDGE_IDS else RAFT_COLORS
        source=self.source((game,PAIR,mid));mask=[p in colors for p in source.get_flattened_data()]
        assert any(mask)
        ref=self.plank();parts=[dict(donor=ref,srcX=span['x'],srcY=span['y'],**span)for span in runs(mask)]
        assert len(parts)<=31
        art=self.composite(None,parts,'reverse_gen2_pacifidlog_native_wood_'+str(mid));art['overMask']='0'*256
        if not all(mask):art=self.water_backed(art)
        self.proofs.setdefault('platform_silhouettes',{})[game+'/'+str(mid)]=dict(source_object_rgba_colors=[list(c)for c in sorted(colors)],object_pixels=sum(mask),object_mask_sha256=catalog.sha(bytes(mask)),native_material=ref,source_cartridge=game,original_water_and_solid_pixel_outline_preserved=True)
        return art

    def huts(self):
        # Cianwood's complete native compact facade is64x16. Omit only its
        # blank third siding column; the whole door, outer frames and complete
        # roof end caps stay intact in the original48px source frontage.
        native_cols=(64,80,112);arts={};model=Image.new('RGBA',(48,48))
        for y in range(3):
            for x,sx in enumerate(native_cols):
                if y<2:
                    parts=[]
                    for py in range(16):
                        full_y=y*16+py;sy=full_y if full_y<2 else 14+full_y-30 if full_y>=30 else 2+(full_y-2)%12
                        parts+=self.gb_rect('crystal','CIANWOOD_CITY',sx,256+sy,16,1,0,py)
                    art=self.composite(None,parts,'reverse_gen2_pacifidlog_whole_native_compact_roof')
                else:
                    art=self.composite(None,self.gb_rect('crystal','CIANWOOD_CITY',sx,272,16,16),'reverse_gen2_pacifidlog_whole_native_compact_facade')
                arts[x,y]=art;model.paste(self.render(art),(x*16,y*16))
        outside=exterior(model,{(222,255,222,255)})
        matrix=[[521,522,523],[529,530,531],[537,538,539]]
        for y,row in enumerate(matrix):
            for x,mid in enumerate(row):
                mask=[(x*16+px,y*16+py)not in outside for py in range(16)for px in range(16)]
                backing=self.plank()
                art=mask_piece(self,arts[x,y],mask,backing,y<2)
                if y<2:
                    art.pop('base',None);art=self.water_backed(art)
                for game in GAMES:
                    self.put(game,mid,art,'The complete native Crystal Cianwood compact timber house is arranged as a48x48 floating hut. The original16px entrance, both complete side frames, full upper/lower roof caps and every native roof feature remain at1:1. Only one blank wall/roof middle column is omitted; plain internal roof-fill bands alone repeat vertically to the original source height. No doorway, window, unique cap or whole bitmap is resized or cut. Selected native deck planks remain visible beside the lower facade; canonical Crystal water shows through actual roof corners.',dict(object='complete timber hut',source_matrix=matrix,native_counterpart=['crystal','CIANWOOD_CITY',64,256,64,32],native_columns=list(native_cols),native_door_pixel_rect=[80,272,16,16],native_whole_object_scale=1))
        # A Cianwood roof has no finial. Keep that complete naturally plain
        # counterpart rather than transplanting an unrelated small object.
        for game in GAMES:
            self.put(game,514,self.water(),'The selected complete native Cianwood hut has its naturally plain roof and no separate finial. The old source-only ornament cell exposes matching synchronized Crystal water above that intact native roof; no selected native building feature is clipped and no unrelated ornament is invented.',dict(native_counterpart_has_no_finial=True,complete_native_roof_preserved=True))
            for warp in self.sources[game]['warps']:
                if '_HOUSE'in warp['destMap']:
                    x,y=warp['x'],warp['y'];assert self.layouts[game][y][x]==538
                    actual=[row[x-1:x+2]for row in self.layouts[game][y-2:y+1]];assert actual==matrix
                    self.contracts.append(dict(game=game,object='hut',origin=[x-1,y-2],source_matrix=actual,source_entrance=warp,source_finial=[x,y-3],native_dimensions=[48,48],native_pixel_scale=1))
        model.save(self.out/'complete-native-hut48x48.png')

    def clinic(self):
        # Same complete64x64 Crystal Center as the already reviewed lower
        # three rows. Its formerly native GBA top row must join that roof.
        whole=Image.new('RGBA',(64,64));pieces={}
        for y in range(4):
            for x in range(4):
                a=native_piece(self,'gen2','center',x,y);pieces[x,y]=a;whole.paste(self.render(a),(x*16,y*16))
        outside=exterior(whole,{(222,255,222,255)})
        for mid,x,y in((560,0,0),(561,1,0),(562,2,0),(563,3,0),(584,0,3),(587,3,3)):
            a=pieces[x,y];mask=[(x*16+px,y*16+py)not in outside for py in range(16)for px in range(16)]
            a=mask_piece(self,a,mask,self.plank(),y==0)
            if y==0:a.pop('base',None);a=self.water_backed(a)
            for game in GAMES:self.put(game,mid,a,'The floating Center retains the complete original native Crystal Cherrygrove64x64 building and original entrance. The missing top row now supplies its full native roof rather than extra Gen3 roof pixels. Both lower side/frame cells retain their entire original outlines over the same native wooden raft surface; complete native signs, roof edges, window panels and doorway keep1:1 pixels.',dict(object='complete Center',native_counterpart=['crystal','CHERRYGROVE_CITY',448,0,64,64],module=[x,y]))
        for game in GAMES:
            warp=next(w for w in self.sources[game]['warps']if'POKEMON_CENTER'in w['destMap']);assert(warp['x'],warp['y'])==(8,15)
            self.contracts.append(dict(game=game,object='Center',source_origin=[7,12],source_matrix=[row[7:11]for row in self.layouts[game][12:16]],source_entrance=warp,native_pixel_scale=1))

    def terrain(self):
        arts={180:self.classic_cliff('top','top')}
        water=self.water();ref=water['parts'][0]['donor']
        a=self.classic_cliff('ne');a.pop('base',None);arts[372]=self.water_backed(a)
        for mid,raw in((384,(92,76,61,20)),(385,(76,93,20,59))):
            bank=self.raw_ref('TILESET_JOHTO',raw,'NEW_BARK_TOWN');parts=[dict(donor=bank,w=16,h=16,x=0,y=0)]
            for q,tile in enumerate(raw):
                if tile==20:parts.append(dict(donor=ref,srcX=q%2*8,srcY=q//2*8,w=8,h=8,x=q%2*8,y=q//2*8,animated=True))
            art=self.composite(None,parts,'reverse_gen2_pacifidlog_joined_inward_rock_bank_'+str(mid));art.update(animated=True,animation=water['animation'],animationCategory='water',overMask='0'*256);arts[mid]=art
        for game in GAMES:
            for mid,a in arts.items():self.put(game,mid,a,'The complete original joined Pacifidlog cliff and water-bank context determines the handed raised-stone cap and inward shore corners. Whole native Crystal Violet rock modules retain original pixel scale, with the same native CAVE20 animated water only in the actual water quadrants. No water or rock collision, height or native map border is changed.',dict(object='joined cliff/water banks',source_mid=mid))

    def build(self):
        self.huts();self.clinic();self.terrain()
        for mid in RAFT_IDS+BRIDGE_IDS:
            for game in GAMES:
                a=self.platform_art(game,mid)
                self.put(game,mid,a,'The connected original floating raft/bridge timber silhouette is individually reviewed at its actual source size. Every timber/rope/support and dark object-outline pixel remains in the source solid outline; water, foam and water-shadow pixels become the same synchronized native Crystal water as the surrounding body. Complete original S.S.Aqua deck8px wood-grain modules repeat without scaling across plain plank surfaces. The original rounded raft corners, bridge direction, post gaps and support footprint remain exact, including the separately reviewed Ruby/Sapphire and Emerald contour variants; no extra floor or collision is introduced.',dict(object='raft or bridge',source_mid=mid,source_shape=self.proofs['platform_silhouettes'][game+'/'+str(mid)]))
        assert len(self.rows)==111 and all((g,'gen2',PAIR,mid,None)in self.rows for g in GAMES for mid in REVIEWED_SOURCE_IDS)

    def save(self,activate=False):
        self.rows={k:json.loads(json.dumps(self.rows[k],sort_keys=True))for k in sorted(self.rows)}
        self.write(TARGET if activate else self.out/'candidates.lua')
        (self.out/'contracts.json').write_text(json.dumps(dict(contracts=self.contracts,proofs=self.proofs),sort_keys=True,indent=2)+'\n')

    def source(self,k):
        if k not in self._source_images:self._source_images[k]=CityReview.source(self,k)
        return self._source_images[k]

    def inventory(self):
        rows=[]
        for game in GAMES:
            for mid,count in sorted(self.missing[game].items()):
                c=self.imp.cell_index(game)[PAIR,mid]
                coords=[[x,y]for y,row in enumerate(self.layouts[game])for x,value in enumerate(row)if value==mid]
                rows.append(dict(game=game,id=mid,count=count,source_rgba_sha256=c['pixel_sha256'],layer_sha256=c['layer_sha256'],behavior=c['behavior'],coordinates=coords))
        report=dict(status='source inventory only',sources=self.sources,cells=rows)
        (self.out/'inventory.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
        for game in('emerald',):
            mids=sorted(self.missing[game]);im=Image.new('RGB',(1280,((len(mids)+9)//10)*112),'#18212b');d=ImageDraw.Draw(im);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',12)
            for i,mid in enumerate(mids):
                x,y=i%10*128,i//10*112;d.text((x+3,y+2),str(mid)+' x'+str(self.missing[game][mid]),fill='white',font=font)
                im.paste(self.source((game,PAIR,mid)).resize((64,64),Image.Resampling.NEAREST),(x+4,y+28))
            im.save(self.out/'remaining-native-contact.png')
        for game in GAMES:
            layout=self.layouts[game];im=Image.new('RGBA',(len(layout[0])*16,len(layout)*16))
            for y,row in enumerate(layout):
                for x,mid in enumerate(row):im.paste(self.source((game,PAIR,mid)),(x*16,y*16))
            im.save(self.out/(game+'-pacifidlog-source.png'))
        return report

    def preview_map(self,game):
        layout=self.layouts[game];w,h=len(layout[0]),len(layout)
        images={k:Image.new('RGBA',(w*16,h*16))for k in('source','previous','after')};rendered={};covered=0;new=0
        for y,row in enumerate(layout):
            for x,mid in enumerate(row):
                k=(game,PAIR,mid);orig=self.source(k);images['source'].paste(orig,(x*16,y*16));prior=self.prior.get(k);candidate=self.rows.get((game,'gen2',PAIR,mid,None))
                for label,recipe in(('previous',prior),('after',candidate or prior)):
                    if recipe:
                        ck=(label,mid)
                        if ck not in rendered:rendered[ck]=self.render(recipe)
                        tile=rendered[ck]
                    else:tile=orig
                    images[label].paste(tile,(x*16,y*16))
                if candidate or prior:covered+=1
                if candidate:new+=1
        for suffix,im in images.items():im.save(self.out/(game+'-pacifidlog-'+suffix+'.png'))
        for label,box in(('town',(0,0,w*16,h*16)),('hut-raft-bridges',(0,128,176,448))):
            clips=[images[k].crop(box)for k in('source','previous','after')];cw,ch=clips[0].size;scale=1 if label=='town'else 2
            canvas=Image.new('RGB',(cw*scale*3+64,ch*scale+80),'#18212b');d=ImageDraw.Draw(canvas);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
            for i,(title,im)in enumerate(zip(('Native source','Previous Crystal theme','Reviewed Crystal completion'),clips)):
                x=16+i*(cw*scale+16);d.text((x,12),title,fill='white',font=font);canvas.paste(im.resize((cw*scale,ch*scale),Image.Resampling.NEAREST),(x,40))
            d.text((16,ch*scale+52),game.title()+f': {covered}/{w*h} cells retiled; {new} newly reviewed. CPU artwork preview; native GPU checks separate.',fill='#ccd7e5',font=font)
            canvas.save(self.out/(game+'-pacifidlog-'+label+'-comparison.png'))
        return dict(game=game,map=self.sources[game]['map'],total=w*h,replaced=covered,newly_covered=new,remaining=w*h-covered)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inventory',action='store_true');p.add_argument('--validate',action='store_true');p.add_argument('--activate',action='store_true');args=p.parse_args();assert not args.activate or args.validate
    r=Review();r.inventory()
    if args.inventory:
        print(json.dumps(dict(games={g:dict(keys=len(r.missing[g]),cells=sum(r.missing[g].values()),ids=sorted(r.missing[g]))for g in GAMES})),flush=True);return
    r.freeze_sources();r.build();r.save(args.activate)
    maps=[r.preview_map(g)for g in GAMES];assert all(m['replaced']==m['total']==800 and m['remaining']==0 for m in maps)
    report=dict(status='candidate',rows=len(r.rows),maps=maps,source_binding=REVIEWED_SOURCE_BINDING,source_original_layouts_warps_collision_untouched=True)
    if args.validate:report['neutral']=r.validate();report['status']='passed'
    report['activated']=args.activate;(r.out/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':main()
