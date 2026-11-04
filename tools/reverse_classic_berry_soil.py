"""Crystal berry dirt over the exact existing selected Hoenn ground.

Only individually reviewed, actually used native dirt-family cells are mapped.
The secondary-bank aliases are explicit per bank, not inferred from their IDs.
All actual behavior416 soil seeds and their plain connected borders are audited.
The unused302/303 cells
contain native sprout artwork and are excluded rather than flattened as soil.
Generated dirt artwork is masked at authoring time; no source ROM art is bundled.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
from collections import Counter

from PIL import Image, ImageDraw, ImageFont
import catalog
import preview
from building_review import decode_layout
from newbark_building_review import lua
from reverse_common import ReverseReview, ROOT, CACHE

GAMES=('ruby','sapphire','emerald')
SOIL_IDS=(259,260,261,267,268,269,275,276,277,331,332,333)
SOIL_ALIASES={'general__fortree':(659,660,667,668),
    'general__lilycove':(627,629,635,637,725,733,741),
    'general__mauville':(582,583),'general__petalburg':(652,653,654)}
SOIL_COLORS={(99,66,82,255),(132,90,90,255),(156,115,115,255),(189,148,140,255)}
TARGET=ROOT/'mappings/reverse_classic_berry_soil.lua'
OUT=ROOT.parent/'.work/tileshift-v0350-berry-soil'
MATERIAL=ROOT/'assets/original/berries/gen2/soil-material.png'
MATERIAL_HASH='74e557413a165affcd997d7b33444e91b0835fa9ee097ec445a6dfdb71458292'
REVIEWED_SOURCE_BINDING='0ad07dae0d000157b0c6ab83ddee3abd47eb2f65637642396c0090231da31af5'
REVIEWED_ALIAS_BINDING='a1fb3a7d9f5554562da75146e7bcf60b94e71410bbf90c00fa6b32495ea2f109'


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def identity(row):return row['game'],row['style'],row['tileset'],row['id'],row.get('map')


class Review(ReverseReview):
    def __init__(self,output=OUT):
        super().__init__('classic-berry-soil',GAMES);self.out=output.resolve();self.out.mkdir(parents=True,exist_ok=True)
        self.active=[];self.prior={};self.sources={};self.scenes=[];self.primary_scenes=[];self.alias_scenes=[];self.soil_seed_scenes=[];self.used=Counter();self.native={};self.masks={}
        self.previous_soil=preview.read_reviewed(TARGET)if TARGET.exists()else[]
        self.previous_module_bytes=TARGET.read_bytes()if TARGET.exists()else None
        modules=dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(ROOT/'main.lua').read_text()))
        for module in modules:
            if ROOT/module==TARGET:continue
            for row in preview.read_reviewed(ROOT/module):
                self.active.append(row)
                if row['game']in GAMES and row['style']=='gen2':
                    k=(row['game'],row['tileset'],row['id'],row.get('map'));assert k not in self.prior;self.prior[k]=row
        for game in GAMES:
            index=self.imp.cell_index(game)
            for name,spec in sorted(self.imp.table(game,'gba/native/manifest')['layouts'].items()):
                path=CACHE/game/'data/generated/gba/native'/spec['file'];layout=decode_layout(path)
                seeds=Counter(mid for mid in layout['mids']if index[spec['pair'],mid].get('behavior')==416)
                if seeds:
                    self.soil_seed_scenes.append(dict(game=game,map=name,pair=spec['pair'],source_layout_sha256=catalog.sha(path.read_bytes()),source_layout_metadata=spec,
                        dimensions=[layout['width'],layout['height']],source_warps=self.imp.table(game,'gba/warps').get(name,[]),
                        cells=[dict(id=mid,count=count,source_rgba_sha256=index[spec['pair'],mid]['pixel_sha256'],source_layer_sha256=index[spec['pair'],mid]['layer_sha256'],
                            source_behavior=index[spec['pair'],mid]['behavior'],coordinates=[[i%layout['width'],i//layout['width']]for i,value in enumerate(layout['mids'])if value==mid])for mid,count in sorted(seeds.items())]))
                if not spec['pair'].startswith('general__'):continue
                primary_counts=Counter(mid for mid in layout['mids']if mid in SOIL_IDS)
                alias_counts=Counter(mid for mid in layout['mids']if mid in SOIL_ALIASES.get(spec['pair'],()))
                counts=primary_counts+alias_counts
                assert 302 not in layout['mids']and 303 not in layout['mids'],'Unused sprout-state tiles need their own review'
                if not counts:continue
                scene=dict(game=game,map=name,pair=spec['pair'],source_layout_sha256=catalog.sha(path.read_bytes()),source_layout_metadata=spec,
                    dimensions=[layout['width'],layout['height']],source_warps=self.imp.table(game,'gba/warps').get(name,[]),counts=dict(counts))
                self.scenes.append(scene)
                for group,partial in((self.primary_scenes,primary_counts),(self.alias_scenes,alias_counts)):
                    if partial:group.append(dict(scene,counts=dict(partial)))
                for mid,count in counts.items():self.used[game,spec['pair'],mid]+=count
        self.keys=sorted(self.used)
        self.primary_keys=[k for k in self.keys if k[2]in SOIL_IDS]
        self.alias_keys=[k for k in self.keys if k not in self.primary_keys]
        assert len(self.keys)==219 and len(self.primary_keys)==171 and len(self.alias_keys)==48
        assert len(self.scenes)==45 and sum(self.used.values())==825
        for scene in self.soil_seed_scenes:
            assert all((scene['game'],scene['pair'],cell['id'])in self.keys for cell in scene['cells']),'An actual native berry-soil behavior lacks reviewed artwork'
        for game,pair,mid in self.keys:
            assert(game,pair,mid,None)not in self.prior,('Existing soil recipe needs explicit supersession review',game,pair,mid)
            c=self.imp.cell_index(game)[pair,mid]
            ref=dict(game=game,tileset=pair,id=mid,hash=c['pixel_sha256'])
            image=preview.native_donor(CACHE,ref,self.packed)
            mask=[p in SOIL_COLORS for p in image.get_flattened_data()];assert any(mask)
            # Every omitted source pixel must belong to connected exterior
            # lawn; enclosed details may never be removed by color alone.
            outside={(x,y)for y in range(16)for x in range(16)if not mask[y*16+x]}
            visited=set();queue=[p for p in outside if p[0]in(0,15)or p[1]in(0,15)]
            while queue:
                x,y=queue.pop()
                if(x,y)in visited:continue
                visited.add((x,y));queue.extend(p for p in((x-1,y),(x+1,y),(x,y-1),(x,y+1))if p in outside and p not in visited)
            assert visited==outside,('Unreviewed enclosed nonsoil detail',game,pair,mid)
            base=self.prior.get((game,pair,1,None));assert base and base.get('donor')and base['donor']['game']=='crystal'
            self.native[game,pair,mid]=image;self.masks[game,pair,mid]=mask
            self.sources[game,pair,mid]=dict(game=game,pair=pair,id=mid,rgba_sha256=c['pixel_sha256'],layer_sha256=c['layer_sha256'],behavior=c.get('behavior'),
                dirt_mask_sha256=catalog.sha(bytes(mask)),dirt_pixels=sum(mask),selected_ground=base['donor'],selected_ground_row_sha256=digest(base),occurrences=self.used[game,pair,mid])

    def freeze(self,require_frozen=True):
        common=dict(material_sha256=MATERIAL_HASH,
            source_berry_contract_sha256=digest(json.loads((ROOT/'tools/berry_source_contract.json').read_text())))
        primary=dict(cells=[self.sources[k]for k in self.primary_keys],scenes=self.primary_scenes,**common)
        aliases=dict(cells=[self.sources[k]for k in self.alias_keys],scenes=self.alias_scenes,all_actual_behavior416_scenes=self.soil_seed_scenes,**common)
        primary_hash,alias_hash=digest(primary),digest(aliases)
        binding=dict(primary=dict(sha256=primary_hash,binding=primary),aliases=dict(sha256=alias_hash,binding=aliases))
        value=digest(binding)
        (self.out/'source-binding.json').write_text(json.dumps(dict(sha256=value,binding=binding),sort_keys=True,indent=2)+'\n')
        if require_frozen:
            assert primary_hash==REVIEWED_SOURCE_BINDING,('Primary soil binding changed; fresh review required',primary_hash)
            assert alias_hash==REVIEWED_ALIAS_BINDING,('Alias RGBA/layers/behavior/layout/warp/ground binding changed; fresh review required',alias_hash)
        return value

    def render(self,row):return preview.replacement_image(CACHE,row,self.packed,ROOT)

    def build(self):
        assert catalog.sha(MATERIAL.read_bytes())==MATERIAL_HASH
        material=Image.open(MATERIAL).convert('RGBA');assert material.size==(16,16)and all(p[3]==255 for p in material.get_flattened_data())
        assets={};by_mask={}
        for key in self.primary_keys+self.alias_keys:
            game,pair,mid=key;mask=self.masks[key];maskhash=catalog.sha(bytes(mask))
            if key in self.alias_keys and maskhash in by_mask:assets[mid,maskhash]=by_mask[maskhash]
            if(mid,maskhash)not in assets:
                output=material.copy()
                for y in range(16):
                    for x in range(16):
                        if not mask[y*16+x]:output.putpixel((x,y),(0,0,0,0))
                name='soil-'+(pair.split('__',1)[1]+'-'if key in self.alias_keys else'')+str(mid)+'.png'
                relative='assets/original/berries/gen2/'+name;path=ROOT/relative
                # Existing primary assets stay byte-identical on reproduction.
                import io
                encoded=io.BytesIO();output.save(encoded,format='PNG');body=encoded.getvalue()
                if not path.exists()or path.read_bytes()!=body:path.write_bytes(body)
                assets[mid,maskhash]=dict(asset=relative,assetFileHash=catalog.sha(path.read_bytes()),assetPixelHash=catalog.sha(output.tobytes()))
            by_mask[maskhash]=assets[mid,maskhash]
            c=self.imp.cell_index(game)[pair,mid]
            assert c['layer_sha256']['over']==catalog.sha(bytes(1024)),'A soil priority state needs separate artwork review'
            art=dict(kind='original',base=copy.deepcopy(self.sources[key]['selected_ground']),role='classic_gen2_native_berry_dirt_silhouette',overMask='0'*256,**assets[mid,maskhash])
            row=self.row(game,pair,mid,'gen2',art,'Explicit original Hoenn berry-dirt source silhouette is retained at native16px scale, with newly authored Crystal-style dirt. Only the connected cyan lawn exterior is transparent in the dirt asset; it reveals the exact existing selected Crystal ground from source1 in this same pair. Source RGBA, all priority planes, behavior, complete layouts and warps are individually frozen. Original soil interaction, berry objects, growth, watering and harvesting remain unchanged.')
            row['berrySoilReview']=dict(source_binding=REVIEWED_ALIAS_BINDING if key in self.alias_keys else REVIEWED_SOURCE_BINDING,source_dirt_mask_sha256=self.sources[key]['dirt_mask_sha256'],source_dirt_pixels=sum(mask),pixel_scale=1,material_hash=MATERIAL_HASH)
            base=self.gb_image(art['base']);after=self.render(row)
            assert all(after.getpixel((x,y))==base.getpixel((x,y))for y in range(16)for x in range(16)if not mask[y*16+x])
            assert all(p[3]==255 for p in after.get_flattened_data())
        self.rows={k:json.loads(json.dumps(v,sort_keys=True))for k,v in sorted(self.rows.items(),key=lambda kv:tuple(str(x)for x in kv[0]))}
        return assets

    def save(self,activate):
        target=self.out/'candidate.lua';self.write(target)
        from gen2_side_threshold_orientation import literal_rows
        new_text=target.read_text(encoding='utf-8');new_rows={identity(row):(row,new_text[a:b])for a,b,row in literal_rows(new_text)}
        old_text=self.previous_module_bytes.decode('utf-8')if self.previous_module_bytes else''
        old_rows={identity(row):(row,old_text[a:b])for a,b,row in literal_rows(old_text)}
        assert all(new_rows.get(key)==value for key,value in old_rows.items()),'An existing soil row changed structurally or by literal bytes'
        (self.out/'existing-row-preservation.json').write_text(json.dumps(dict(existing_rows=len(old_rows),candidate_rows=len(new_rows),
            existing_rows_structurally_and_literal_byte_identical=True,existing_module_sha256=catalog.sha(self.previous_module_bytes)if self.previous_module_bytes else None,
            candidate_module_sha256=catalog.sha(target.read_bytes())),indent=2)+'\n',encoding='utf-8')
        if activate:
            assert (TARGET.read_bytes()if TARGET.exists()else None)==self.previous_module_bytes,'Concurrent soil module edit'
            TARGET.write_bytes(target.read_bytes())
        (self.out/'new-keys.json').write_text(json.dumps([dict(pair=r['tileset'],mid=r['id'],**{n:r[n]for n in('game','style','tileset','id','sourceHash','sourceBehavior','compositionPixelHash')})for r in self.rows.values()],sort_keys=True,indent=2)+'\n')
        (self.out/'affected-scenes.json').write_text(json.dumps([dict(game=s['game'],map=s['map'])for s in self.scenes],indent=2)+'\n')

    def soil_provenance(self,assets,activate):
        target=ROOT/'assets/original/berries/gen2/provenance.json'
        original=json.loads(target.read_text(encoding='utf-8'));updated=copy.deepcopy(original)
        inventory={item['asset']:dict(asset=item['asset'],sha256=item['assetFileHash'],rgba_sha256=item['assetPixelHash'],size=[16,16])for item in assets.values()}
        assert len(inventory)==22
        for item in original['soil_material']['shape_variants']:
            assert inventory[item['asset']]==item,'A previously approved soil asset changed'
        updated['soil_material']['shape_variants']=[inventory[name]for name in sorted(inventory)]
        assert updated['varieties']==original['varieties'],'Tree provenance must remain unchanged'
        for item in original['varieties']:
            assert catalog.sha((ROOT/item['asset']).read_bytes())==item['native_png_sha256'],'Tree artwork must remain unchanged'
        output=target if activate else self.out/'soil-provenance.json'
        output.write_text(json.dumps(updated,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        return dict(shape_variants=22,soil_assets=23,total_pngs=66,provenance_sha256=catalog.sha(output.read_bytes()),tree_records_sha256=digest(original['varieties']))

    def previews(self):
        reports=[];font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
        for game,prefix in(('ruby','RU_'),('sapphire','SA_'),('emerald','EM_')):
            name=prefix+'ROUTE104';original,cells,_,meta=self.imp.gba(game,name)
            before=original.copy();after=original.copy()
            previous={r['id']:r for r in self.active+self.previous_soil if r['game']==game and r['style']=='gen2'and r['tileset']==meta['tileset']and r.get('map',name)==name}
            fixed={r['id']:r for r in self.rows.values()if r['game']==game and r['tileset']==meta['tileset']}
            for cell in cells:
                prior=previous.get(cell['id']);row=fixed.get(cell['id'])or prior
                prior_image=self.render(prior)if prior else None;new_image=self.render(row)if row else None
                for x,y in cell['coordinates']:
                    if prior_image:before.paste(prior_image,(x*16,y*16))
                    if new_image:after.paste(new_image,(x*16,y*16))
            for suffix,image in(('source',original),('previous',before),('after',after)):image.save(self.out/(game+'-route104-'+suffix+'.png'))
            for label,box in(('north',(32*16,4*16,40*16,10*16)),('west',(0,20*16,8*16,29*16))):
                images=[image.crop(box)for image in(original,before,after)];w,h=images[0].size;scale=3
                panel=Image.new('RGB',(w*scale*3+64,h*scale+78),'#18212b');draw=ImageDraw.Draw(panel)
                for i,(title,image)in enumerate(zip(('Original source ground','Previous Crystal ground','New Crystal dirt'),images)):
                    x=16+i*(w*scale+16);draw.text((x,12),title,font=font,fill='white');panel.paste(image.resize((w*scale,h*scale),Image.Resampling.NEAREST),(x,42))
                filename=game+'-route104-'+label+'-soil-comparison.png';panel.save(self.out/filename);reports.append(dict(game=game,map=name,crop=label,file=filename))
            # These complete plots exercise every secondary bank family, with
            # both native dirt halves and the selected surrounding lawn visible.
            crops={'ROUTE102':(('whole',(22,1,28,5)),),
                'ROUTE118':(('whole',(32,3,41,9)),),
                'ROUTE119':(('west',(5,20,15,27)),('south',(26,87,36,94))),
                'ROUTE121':(('north',(12,0,21,6)),('east',(61,11,77,18))),
                'ROUTE123':(('farm',(9,1,22,11)),)}
            for route,boxes in crops.items():
                map_id=prefix+route;source,map_cells,_,map_meta=self.imp.gba(game,map_id)
                old=source.copy();new=source.copy()
                prior_rows={r['id']:r for r in self.active+self.previous_soil if r['game']==game and r['style']=='gen2'and r['tileset']==map_meta['tileset']and r.get('map',map_id)==map_id}
                new_rows={r['id']:r for r in self.rows.values()if r['game']==game and r['tileset']==map_meta['tileset']}
                for cell in map_cells:
                    prior=prior_rows.get(cell['id']);fixed=new_rows.get(cell['id'])or prior
                    a=self.render(prior)if prior else None;b=self.render(fixed)if fixed else None
                    for x,y in cell['coordinates']:
                        if a:old.paste(a,(x*16,y*16))
                        if b:new.paste(b,(x*16,y*16))
                for label,tiles in boxes:
                    box=tuple(v*16 for v in tiles);images=[im.crop(box)for im in(source,old,new)];w,h=images[0].size;scale=3
                    panel=Image.new('RGB',(w*scale*3+64,h*scale+78),'#18212b');draw=ImageDraw.Draw(panel)
                    for i,(title,image)in enumerate(zip(('Original source plot','Current Crystal plot','Complete Crystal dirt'),images)):
                        x=16+i*(w*scale+16);draw.text((x,12),title,font=font,fill='white');panel.paste(image.resize((w*scale,h*scale),Image.Resampling.NEAREST),(x,42))
                    filename=game+'-'+route.lower()+'-'+label+'-soil-comparison.png';panel.save(self.out/filename);reports.append(dict(game=game,map=map_id,crop=label,file=filename))
        return reports


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inventory',action='store_true');p.add_argument('--validate',action='store_true');p.add_argument('--activate',action='store_true');p.add_argument('--output',type=Path,default=OUT);args=p.parse_args();assert not args.activate or args.validate
    review=Review(args.output);binding=review.freeze(not args.inventory)
    report=dict(status='inventory',keys=len(review.keys),source_binding=binding,scenes=len(review.scenes),occurrences=sum(review.used.values()),by_game=dict(Counter(k[0]for k in review.keys)),ids=sorted({k[2]for k in review.keys}))
    if not args.inventory:
        assets=review.build();report.update(status='candidate',assets=len({item['asset']for item in assets.values()}),activated=args.activate,previews=review.previews())
        if args.validate:report['neutral']=review.validate();report['status']='passed'
        review.save(args.activate)
        report['artwork']=review.soil_provenance(assets,args.activate)
    (review.out/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':main()
