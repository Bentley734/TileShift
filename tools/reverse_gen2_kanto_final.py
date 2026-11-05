"""Review every remaining actual-used FR/LG Crystal counterpart.

The inventory is complete against current main.lua; new recipes remain a
separate candidate module until integrated by the release workflow.
"""
from __future__ import annotations
import argparse
import copy
import json
from collections import Counter, defaultdict
from pathlib import Path

import catalog
import preview
from reverse_hoenn_review import native_geometry
from PIL import Image, ImageDraw, ImageFont
import reverse_gen2_kanto_finish as previous
from reverse_gen2_kanto_complete import Complete

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'mappings/reverse_gen2_kanto_final.lua'
OUT=ROOT.parent/'.work/tileshift-v0360-kanto-completion'
DECISIONS=ROOT/'tools/reverse_gen2_kanto_final_decisions.json'
ART_KEYS={'kind','donor','base','parts','asset','assetFileHash','assetPixelHash','artOverlay',
    'role','overMask','foregroundMask','foreground','animated','animation','animationCategory','classicGeometry'}


class Final(Complete):
    def __init__(self):
        old=previous.TARGET
        previous.TARGET=TARGET
        try:
            previous.Finish.__init__(self)
        finally:
            previous.TARGET=old
        self.name='gen2-kanto-final'
        self.out=OUT
        self.out.mkdir(parents=True,exist_ok=True)
        self.target_module=TARGET
        self.decisions=[]

    def exact_active_aliases(self):
        """Propose only complete source/layer/behavior-identical aliases.

        These proposals still require semantic/context review. Conflicting
        approved outputs are listed, never resolved by contact order.
        """
        active=defaultdict(list)
        for key,row in self.current.items():
            game,style,pair,mid,map_id=key
            if map_id is not None or (game,pair,mid)not in self.usage:
                continue
            signature=self.source_signature(game,pair,mid)
            active[signature].append(row)
        proposals=[]
        for item in self.remaining:
            rows=active.get(item['signature'],[])
            if not rows:continue
            outputs=defaultdict(list)
            for row in rows:
                output=row.get('compositionPixelHash')
                if not output:
                    output=catalog.sha(self.render(row).tobytes())
                outputs[output].append(row)
            proposals.append(dict(signature=item['signature'],count=item['count'],
                sources=item['sources'],unambiguous=len(outputs)==1,
                approved_outputs=[dict(hash=h,roles=sorted({r.get('role','')for r in v}),
                    origins=[dict(game=r['game'],pair=r['tileset'],mid=r['id'])for r in v])for h,v in outputs.items()]))
        (self.out/'exact-active-alias-proposals.json').write_text(json.dumps(proposals,indent=2)+'\n')
        return dict(groups=len(proposals),keys=sum(len(p['sources'])for p in proposals),
            cells=sum(p['count']for p in proposals),unambiguous_groups=sum(p['unambiguous']for p in proposals),
            unambiguous_keys=sum(len(p['sources'])for p in proposals if p['unambiguous']),
            unambiguous_cells=sum(p['count']for p in proposals if p['unambiguous']))

    def indexed_active_aliases(self):
        def signature(game,pair,mid):
            cell=self.imp.cell_index(game)[pair,mid]
            # Primary IDs are stable within the same source primary family.
            family=pair.split('__')[0] if '__'in pair else pair
            return catalog.sha(previous.stable(dict(family=family,mid=mid,
                behavior=cell['behavior'],geometry=[catalog.sha(p)for p in native_geometry(self,game,pair,mid)])).encode())
        active=defaultdict(list)
        for key,row in self.current.items():
            game,style,pair,mid,map_id=key
            if map_id is None and (game,pair,mid)in self.usage:
                active[signature(game,pair,mid)].append(row)
        groups=defaultdict(list)
        for item in self.remaining:
            for src in item['sources']:
                groups[signature(src['game'],src['pair'],src['id'])].append(src)
        proposals=[]
        for sig,sources in groups.items():
            rows=active.get(sig,[])
            if not rows:continue
            outputs=defaultdict(list)
            for row in rows:
                output=row.get('compositionPixelHash')or catalog.sha(self.render(row).tobytes())
                outputs[output].append(row)
            proposals.append(dict(signature=sig,count=sum(s['count']for s in sources),
                sources=sources,unambiguous=len(outputs)==1,
                approved_outputs=[dict(hash=h,roles=sorted({r.get('role','')for r in v}),
                    origins=[dict(game=r['game'],pair=r['tileset'],mid=r['id'])for r in v])for h,v in outputs.items()]))
        proposals.sort(key=lambda p:-p['count'])
        (self.out/'indexed-active-alias-proposals.json').write_text(json.dumps(proposals,indent=2)+'\n')
        summary=dict(unresolved_indexed_groups=len(groups),groups=len(proposals),keys=sum(len(p['sources'])for p in proposals),
            cells=sum(p['count']for p in proposals),unambiguous_groups=sum(p['unambiguous']for p in proposals),
            unambiguous_keys=sum(len(p['sources'])for p in proposals if p['unambiguous']),
            unambiguous_cells=sum(p['count']for p in proposals if p['unambiguous']))
        return summary

    def partition_active_aliases(self):
        def signature(game,pair,mid):
            cell=self.imp.cell_index(game)[pair,mid]
            family=pair.split('__')[0] if '__'in pair else pair
            lookup={};values=[]
            for plane in native_geometry(self,game,pair,mid):
                values.append(bytes(255 if v==255 else lookup.setdefault(v,len(lookup))for v in plane))
            return catalog.sha(previous.stable(dict(family=family,behavior=cell['behavior'],
                colors=len(lookup),geometry=[catalog.sha(p)for p in values])).encode()),len(lookup)
        active=defaultdict(list)
        for key,row in self.current.items():
            game,style,pair,mid,map_id=key
            if map_id is None and(game,pair,mid)in self.usage:
                sig,colors=signature(game,pair,mid)
                active[sig].append(row)
        groups=defaultdict(list);colors_by_sig={}
        for item in self.remaining:
            for src in item['sources']:
                sig,colors=signature(src['game'],src['pair'],src['id'])
                groups[sig].append(src);colors_by_sig[sig]=colors
        proposals=[]
        for sig,sources in groups.items():
            rows=active.get(sig,[])
            if not rows:continue
            outputs=defaultdict(list)
            for row in rows:
                output=row.get('compositionPixelHash')or catalog.sha(self.render(row).tobytes())
                outputs[output].append(row)
            proposals.append(dict(signature=sig,count=sum(s['count']for s in sources),colors=colors_by_sig[sig],
                sources=sources,unambiguous=len(outputs)==1,
                approved_outputs=[dict(hash=h,roles=sorted({r.get('role','')for r in v}),
                    origins=[dict(game=r['game'],pair=r['tileset'],mid=r['id'])for r in v])for h,v in outputs.items()]))
        proposals.sort(key=lambda p:-p['count'])
        (self.out/'partition-active-alias-proposals.json').write_text(json.dumps(proposals,indent=2)+'\n')
        return dict(unresolved_partition_groups=len(groups),groups=len(proposals),keys=sum(len(p['sources'])for p in proposals),
            cells=sum(p['count']for p in proposals),unambiguous_groups=sum(p['unambiguous']for p in proposals),
            unambiguous_keys=sum(len(p['sources'])for p in proposals if p['unambiguous']),
            unambiguous_cells=sum(p['count']for p in proposals if p['unambiguous']))

    def partition_reviews(self):
        proposals=json.loads((self.out/'partition-active-alias-proposals.json').read_text())
        font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',12)
        reviews=[]
        for number,p in enumerate(proposals):
            if not p['unambiguous']:continue
            origin=p['approved_outputs'][0]['origins'][0]
            old=self.current[origin['game'],'gen2',origin['pair'],origin['mid'],None]
            target=p['sources'][0]
            lookup={};inverse={};checked=0;valid=True
            for layer in (None,'under','mid','over'):
                images=[]
                for src in (dict(game=origin['game'],pair=origin['pair'],id=origin['mid']),target):
                    cell=self.imp.cell_index(src['game'])[src['pair'],src['id']]
                    ref=dict(game=src['game'],tileset=src['pair'],id=src['id'],hash=cell['pixel_sha256'])
                    images.append(preview.native_donor(self.cache,ref,self.packed,[layer]if layer else None,
                        {layer:cell['layer_sha256'][layer]}if layer else None))
                for a,b in zip(images[0].get_flattened_data(),images[1].get_flattened_data()):
                    checked+=1
                    if a[3]!=b[3]:valid=False;continue
                    if not a[3]:continue
                    if(a in lookup and lookup[a]!=b)or(b in inverse and inverse[b]!=a):valid=False
                    lookup[a]=b;inverse[b]=a
            item=dict(number=number,signature=p['signature'],valid_rgba_bijection=valid,checked_pixels=checked,
                canonical=origin,targets=p['sources'],count=p['count'],roles=p['approved_outputs'][0]['roles'],
                palette=[dict(source=list(a),target=list(b))for a,b in sorted(lookup.items())])
            reviews.append(item)
        (self.out/'partition-source-bijection-reviews.json').write_text(json.dumps(reviews,indent=2)+'\n')
        for start in range(0,len(reviews),12):
            canvas=Image.new('RGB',(1600,6*244),'#18212b');draw=ImageDraw.Draw(canvas)
            for local,item in enumerate(reviews[start:start+12]):
                x,y=local%2*800,local//2*244
                target=item['targets'][0];origin=item['canonical']
                old=self.current[origin['game'],'gen2',origin['pair'],origin['mid'],None]
                ims=[]
                for src in (dict(game=origin['game'],pair=origin['pair'],id=origin['mid']),target):
                    cell=self.imp.cell_index(src['game'])[src['pair'],src['id']]
                    ims.append(preview.native_donor(self.cache,dict(game=src['game'],tileset=src['pair'],id=src['id'],hash=cell['pixel_sha256']),self.packed))
                ims.append(self.render(old))
                for i,im in enumerate(ims):canvas.paste(im.resize((96,96),Image.Resampling.NEAREST),(x+4+i*104,y+36))
                witness=next(u for u in target['witnesses']if u['count'])
                spec,layout=self.layouts[target['game'],witness['map']]
                at=layout['mids'].index(target['id']);cx,cy=at%layout['width'],at//layout['width']
                ctx=Image.new('RGBA',(80,80))
                for yy in range(5):
                    for xx in range(5):
                        tx,ty=cx+xx-2,cy+yy-2
                        if not(0<=tx<layout['width']and 0<=ty<layout['height']):continue
                        mid=layout['mids'][ty*layout['width']+tx];cell=self.imp.cell_index(target['game'])[spec['pair'],mid]
                        im=preview.native_donor(self.cache,dict(game=target['game'],tileset=spec['pair'],id=mid,hash=cell['pixel_sha256']),self.packed)
                        ctx.paste(im,(xx*16,yy*16))
                canvas.paste(ctx.resize((200,200),Image.Resampling.NEAREST),(x+584,y+32))
                draw.text((x+4,y+2),str(item['number'])+' cells='+str(item['count'])+' bijection='+str(item['valid_rgba_bijection']),font=font,fill='white')
                draw.text((x+4,y+140),target['pair']+'/'+str(target['id'])+' '+witness['map'],font=font,fill='white')
                draw.text((x+4,y+160),origin['pair']+'/'+str(origin['mid']),font=font,fill='#c4cdd8')
                draw.text((x+4,y+180),'\n'.join(item['roles'])[:180],font=font,fill='#c4cdd8')
            canvas.save(self.out/f'partition-context-review-{start//12+1:02}.png')
        return dict(groups=len(reviews),rgba_bijections=sum(x['valid_rgba_bijection']for x in reviews))

    def art_of(self,row):
        return {k:copy.deepcopy(v)for k,v in row.items()if k in ART_KEYS}

    def rgba_bijection(self,origin,target,layers=(None,'under','mid','over')):
        mapping={};inverse={};checks=0
        for layer in layers:
            images=[]
            for src in(origin,target):
                c=self.imp.cell_index(src['game'])[src['pair'],src['mid']]
                images.append(preview.native_donor(self.cache,dict(game=src['game'],tileset=src['pair'],id=src['mid'],hash=c['pixel_sha256']),self.packed,
                    [layer]if layer else None,{layer:c['layer_sha256'][layer]}if layer else None))
            for a,b in zip(images[0].get_flattened_data(),images[1].get_flattened_data()):
                checks+=1
                assert a[3]==b[3],'Native palette alias alpha changed'
                if not a[3]:continue
                assert a not in mapping or mapping[a]==b,'Non-bijective source colour alias'
                assert b not in inverse or inverse[b]==a,'Non-bijective target colour alias'
                mapping[a]=b;inverse[b]=a
        assert checks==256*len(layers)
        return [dict(source=list(a),target=list(b))for a,b in sorted(mapping.items())]

    def emit_final(self,game,pair,mid,art,note,proof):
        key=game,'gen2',pair,mid,None
        old=self.current.get(key)
        if old and self.art_of(old)==art:return None
        row=self.row(game,pair,mid,'gen2',art,note)
        row['reverseGen2KantoFinal']=proof
        if old:
            module,index=self.origins[id(old)]
            self.supersessions[key]=dict(module=module,index=index,old_row=old,
                old_row_sha256=catalog.sha(previous.stable(old).encode()),new_row=row)
        return row

    def stage(self):
        decisions=json.loads(DECISIONS.read_text())
        assert decisions['format']==1
        aliases=[]
        for decision in decisions['aliases']:
            origin=decision['canonical']
            old=self.current[origin['game'],'gen2',origin['pair'],origin['mid'],None]
            assert catalog.sha(previous.stable(old).encode())==decision['canonical_row_sha256']
            art=self.art_of(old)
            for target in decision['targets']:
                c=self.imp.cell_index(target['game'])[target['pair'],target['mid']]
                assert c['pixel_sha256']==target['rgba']and c['behavior']==target['behavior']and c['layer_sha256']==target['layers']
                assert(game_key:=(target['game'],'gen2',target['pair'],target['mid'],None))not in self.current
                semantic_cave=decision.get('comparison')=='reviewed_whole_cave_module'
                final_only=decision.get('comparison')=='final_empty_over'
                if final_only:
                    empty=catalog.sha(bytes(1024))
                    assert c['layer_sha256']['over']==self.imp.cell_index(origin['game'])[origin['pair'],origin['mid']]['layer_sha256']['over']==empty
                    assert not any(v=='1'for v in art.get('overMask',''))
                if semantic_cave:
                    assert 'cave'in old.get('role','').lower()
                    assert c['layer_sha256']['over']==catalog.sha(bytes(1024))
                    assert all('CAVE'in u['map']or'MOON'in u['map']or'VICTORY_ROAD'in u['map']or'MT_EMBER'in u['map']or'TANOBY_KEY'in u['map']for u in self.usage[target['game'],target['pair'],target['mid']]if u['count'])
                    palette=[]
                else:palette=self.rgba_bijection(origin,target,(None,)if final_only else(None,'under','mid','over'))
                plane_note=(decision['review_basis']+' Complete original Crystal16px directional bank/floor module remains at1:1; native plain fill extends only repeatable rock or ordinary cave floor. '
                    if semantic_cave else'Every final pixel position and alpha is identical under one bijective native color substitution. '
                    'Both source OVER planes are entirely empty; a harmless difference in the UNDER/MID split cannot alter BG1 priority. '
                    if final_only else'A single exact bijective colour substitution preserves every FINAL/UNDER/MID/OVER pixel position and alpha. ')
                row=self.emit_final(target['game'],target['pair'],target['mid'],art,
                    'Explicit full native context review of the same '+decision['semantic_role']+' feature as the already approved native Crystal counterpart. '
                    +plane_note+
                    'The target retains its own exact behavior guard, including any original directional movement, stair or cycling trigger; '
                    'the complete existing counterpart is reused without scaling or changing its selected floor. Source layouts, collision, warps, NPCs and scripts stay unchanged.',
                    dict(kind='reviewed_whole_cave_module'if semantic_cave else'reviewed_final_empty_over_alias'if final_only else'reviewed_full_plane_palette_alias',semantic_role=decision['semantic_role'],
                        canonical=origin,canonical_row_sha256=decision['canonical_row_sha256'],source_layers=c['layer_sha256'],
                        source_contexts=self.usage[target['game'],target['pair'],target['mid']],checked_source_pixels=0 if semantic_cave else 256 if final_only else 1024,palette_bijection=palette))
                aliases.append(dict(game=target['game'],pair=target['pair'],mid=target['mid'],canonical=origin))
        forest=[]
        for decision in decisions['forest']:
            game,pair,mid=decision['game'],decision['pair'],decision['mid']
            c=self.imp.cell_index(game)[pair,mid]
            assert(c['pixel_sha256'],c['behavior'],c['layer_sha256'])==(decision['rgba'],decision['behavior'],decision['layers'])
            cx,cy=decision['section']
            role=f'classic_gen2_complete_native_forest_tree_48_{cx}_{cy}'
            candidates=[r for r in self.current.values()if r['game']=='firered'and r['tileset']=='general__rom_082d4dc4'and r.get('role')==role]
            assert candidates,role
            old=min(candidates,key=lambda r:r['id'])
            art=self.art_of(old)
            mask=[False]*256
            for part in art['parts']:
                for y in range(part.get('y',0),part.get('y',0)+part.get('h',16)):
                    for x in range(part.get('x',0),part.get('x',0)+part.get('w',16)):mask[y*16+x]=True
            over=preview.native_donor(self.cache,dict(game=game,tileset=pair,id=mid,hash=c['pixel_sha256']),self.packed,['over'],{'over':c['layer_sha256']['over']})
            has_over=any(p[3]for p in over.get_flattened_data())
            art['overMask']=''.join('1'if v and has_over else'0'for v in mask)
            self.emit_final(game,pair,mid,art,
                'Explicit whole Berry Forest broadleaf-tree family review: the actual native48x48 canopy/root family uses standalone cap(648,665,650), '
                'lower canopy(672,673,674), roots(675,676,677), and dense overlapping crown rows(664,665,666)/(656,657,658). '
                'Use the corresponding already approved complete Crystal Ilex FOREST5 crown/root module, preserving all original836 native tree pixels at1:1. '
                'Only complete8px middle foliage and plain shadow bands fill the host48px envelope. Outside tree pixels reveal the selected classic field; '
                'native canopy priority is retained, and no cave-bank/rock glyph is treated as a tree. Original collision, source positions and game logic remain untouched.',
                dict(kind='complete_native_berry_forest_canopy',section=[cx,cy],native_map='ILEX_FOREST',native_block=5,
                    native_tree_foreground_pixels_preserved=836,source_layers=c['layer_sha256'],source_contexts=self.usage[game,pair,mid],
                    canonical_role=role,canonical_row_sha256=catalog.sha(previous.stable(old).encode())))
            forest.append(dict(game=game,pair=pair,mid=mid,section=[cx,cy],has_over=has_over))
        (self.out/'staged-aliases.json').write_text(json.dumps(aliases,indent=2)+'\n')
        (self.out/'staged-forest.json').write_text(json.dumps(forest,indent=2)+'\n')
        for decision in decisions.get('geometry',[]):
            game,pair,mid=decision['game'],decision['pair'],decision['mid']
            cell=self.imp.cell_index(game)[pair,mid]
            assert(cell['pixel_sha256'],cell['behavior'],cell['layer_sha256'])==(decision['rgba'],decision['behavior'],decision['layers'])
            prior=self.current.get((game,'gen2',pair,mid,None))
            if prior:
                assert decision.get('replace_prior_row_sha256')==catalog.sha(previous.stable(prior).encode()),'Geometry repair prior row changed'
            self.emit_final(game,pair,mid,copy.deepcopy(decision['art']),decision['evidence'],
                dict(kind='reviewed_complete_unique_feature',feature=decision['art']['classicGeometry']['feature'],
                    source_contexts=self.usage[game,pair,mid],source_layers=cell['layer_sha256'],
                    **({'selected_native_floor_or_wall':decision['art']['classicGeometry']['ground']}if decision['art']['classicGeometry'].get('ground')else{}),
                    pixel_coordinates_and_alpha_unchanged=True))
        for decision in decisions.get('native_modules',[]):
            game,pair,mid=decision['game'],decision['pair'],decision['mid']
            cell=self.imp.cell_index(game)[pair,mid]
            assert(cell['pixel_sha256'],cell['behavior'],cell['layer_sha256'])==(decision['rgba'],decision['behavior'],decision['layers'])
            prior=self.current.get((game,'gen2',pair,mid,None))
            if prior:assert decision.get('replace_prior_row_sha256')==catalog.sha(previous.stable(prior).encode()),'Native repair prior row changed'
            if decision.get('canonical'):
                origin=decision['canonical'];canonical=self.current[origin['game'],'gen2',origin['pair'],origin['mid'],None]
                assert catalog.sha(previous.stable(canonical).encode())==decision['canonical_row_sha256'],'Reviewed native floor row changed'
            assert cell['layer_sha256']['over']==catalog.sha(bytes(1024))
            self.emit_final(game,pair,mid,copy.deepcopy(decision['art']),decision['evidence'],
                dict(kind='reviewed_complete_native_module',feature=decision['feature'],
                    source_contexts=self.usage[game,pair,mid],source_layers=cell['layer_sha256'],native_pixel_scale=1))
        for decision in decisions.get('native_objects',[]):
            game,pair,mid=decision['game'],decision['pair'],decision['mid']
            cell=self.imp.cell_index(game)[pair,mid]
            assert(cell['pixel_sha256'],cell['behavior'],cell['layer_sha256'])==(decision['rgba'],decision['behavior'],decision['layers'])
            self.emit_final(game,pair,mid,copy.deepcopy(decision['art']),decision['evidence'],
                dict(kind='reviewed_complete_native_feature',feature=decision['feature'],
                    source_contexts=self.usage[game,pair,mid],source_layers=cell['layer_sha256'],native_pixel_scale=1,
                    complete_source_family=decision['source_family'],whole_source_rgba_sha256=decision['whole_source_rgba_sha256']))
        (self.out/'supersessions.json').write_text(json.dumps(list(self.supersessions.values()),indent=2)+'\n')
        return list(self.rows.values())

    def scene_previews(self,names):
        for game in self.games:
            for name in names:
                if(game,name)not in self.layouts:continue
                spec,layout=self.layouts[game,name];w,h=layout['width'],layout['height']
                source=Image.new('RGBA',(w*16,h*16));before=source.copy();after=source.copy();images={}
                for index,mid in enumerate(layout['mids']):
                    key=game,'gen2',spec['pair'],mid,None
                    if mid not in images:
                        c=self.imp.cell_index(game)[spec['pair'],mid]
                        original=preview.native_donor(self.cache,dict(game=game,tileset=spec['pair'],id=mid,hash=c['pixel_sha256']),self.packed)
                        old=self.current.get(key);new=self.rows.get(key)
                        images[mid]=original,self.render(old)if old else original,self.render(new or old)if new or old else original
                    for canvas,image in zip((source,before,after),images[mid]):canvas.paste(image,(index%w*16,index//w*16))
                for suffix,image in zip(('source','before','after'),(source,before,after)):image.save(self.out/f'{game}-{name}-{suffix}.png')
                panel=Image.new('RGB',(w*32*3+64,h*32+48),'#18212b');draw=ImageDraw.Draw(panel)
                for i,(title,image)in enumerate(zip(('Native source','Previous Crystal','New reviewed Crystal'),(source,before,after))):
                    x=16+i*(w*32+16);draw.text((x,8),title,fill='white');panel.paste(image.resize((w*32,h*32),Image.Resampling.NEAREST),(x,32))
                panel.save(self.out/f'{game}-{name}-qa.png')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contacts',action='store_true')
    parser.add_argument('--review-contacts',action='store_true')
    parser.add_argument('--stage',action='store_true')
    parser.add_argument('--validate',action='store_true')
    parser.add_argument('--activate',action='store_true')
    args=parser.parse_args()
    review=Final()
    inventory=review.remaining_inventory()
    if args.contacts:review.contacts()
    summary={k:inventory[k]for k in('games','remaining_cells','source_groups','actual_used_source_keys')}
    summary['exact_active_aliases']=review.exact_active_aliases()
    summary['indexed_active_aliases']=review.indexed_active_aliases()
    summary['partition_active_aliases']=review.partition_active_aliases()
    if args.review_contacts:summary['partition_reviews']=review.partition_reviews()
    if args.stage or args.validate or args.activate:
        assert not args.activate or args.validate
        rows=review.stage()
        review.scene_previews(('FR_THREE_ISLAND_BERRY_FOREST','FR_ROUTE_23','FR_MT_EMBER_RUBY_PATH_B4F','FR_CELADON_CITY_HOUSE1','FR_CINNABAR_ISLAND_GYM','FR_POKEMON_TOWER_7F',
            'FR_MT_MOON_1F','FR_MT_MOON_B2F','FR_MT_EMBER_SUMMIT_PATH_2F','FR_ROUTE_17','SEVII_ONE_ISLAND_POKECENTER','FR_CELADON_CITY_POKEMON_CENTER_2F',
            'FR_BIRTH_ISLAND_HARBOR','FR_MT_EMBER_EXTERIOR','FR_SEVEN_ISLAND_SEVAULT_CANYON','FR_FUCHSIA_CITY_GYM'))
        if args.validate:summary['proof']=review.validate()
        review.write(TARGET if args.activate else OUT/'candidate.lua')
        new_only=[r for r in rows if(r['game'],'gen2',r['tileset'],r['id'],None)not in review.current]
        summary.update(new_rows=len(rows),supersessions=len(review.supersessions),new_cells=sum(sum(u['count']for u in review.usage[r['game'],r['tileset'],r['id']])for r in new_only),
            new_cells_by_game={g:sum(sum(u['count']for u in review.usage[r['game'],r['tileset'],r['id']])for r in new_only if r['game']==g)for g in review.games},
            new_keys_by_game={g:sum(r['game']==g for r in new_only)for g in review.games})
        (OUT/'new-keys.json').write_text(json.dumps([dict(game=r['game'],pair=r['tileset'],mid=r['id'])for r in rows],indent=2)+'\n')
        (OUT/'new-only-keys.json').write_text(json.dumps([dict(game=r['game'],pair=r['tileset'],mid=r['id'])for r in new_only],indent=2)+'\n')
        affected={(r['game'],u['map'])for r in rows for u in review.usage[r['game'],r['tileset'],r['id']]}
        scenes=[]
        for game,name in sorted(affected):
            changed=[r for r in rows if r['game']==game and any(u['map']==name for u in review.usage[r['game'],r['tileset'],r['id']])]
            added=[r for r in changed if(r['game'],'gen2',r['tileset'],r['id'],None)not in review.current]
            count=lambda selected:sum(sum(u['count']for u in review.usage[r['game'],r['tileset'],r['id']]if u['map']==name)for r in selected)
            scenes.append(dict(game=game,map=name,new_keys=len(added),changed_keys=len(changed),new_body_cells=count(added),changed_body_cells=count(changed)))
        (OUT/'affected-scenes.json').write_text(json.dumps(scenes,indent=2)+'\n')
    (OUT/'inventory-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary),flush=True)


if __name__=='__main__':main()
