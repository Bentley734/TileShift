"""Finish actual remaining Crystal-theme RSE interior source cells.

Only frozen, explicit source identities and native counterparts are authored.
The inventory uses logical SVML bodies and real native headers, never padding.
"""
from __future__ import annotations
import argparse, copy, hashlib, json, re, struct, zlib
from collections import Counter, defaultdict
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import catalog, preview
from reverse_common import ReverseReview, ROOT
from reverse_gen2_hoenn_interior_finish import scoped, GAMES
from reverse_hoenn_review import native_geometry

TARGET=ROOT/'mappings/reverse_gen2_hoenn_interiors_completion.lua'
OUT=ROOT.parent/'.work/tileshift-v0360-hoenn-interiors-completion'
ALIAS_GUARDS=ROOT/'tools/reverse_gen2_hoenn_interiors_completion_aliases.json'
SURFACE_GUARDS=ROOT/'tools/reverse_gen2_hoenn_interiors_completion_surfaces.json'
FEATURE_GUARDS=ROOT/'tools/reverse_gen2_hoenn_interiors_completion_features.json'
OBJECT_GUARDS=ROOT/'tools/reverse_gen2_hoenn_interiors_completion_objects.json'
ART_FIELDS=('kind','donor','parts','base','asset','assetFileHash','assetPixelHash','overMask','animated','animation',
            'animationCategory','assetFrames','artOverlay','foreground','sourceColors','role','occludes','canopy')

def sha(value): return hashlib.sha256(value).hexdigest()
def digest(value): return sha(json.dumps(value,sort_keys=True,separators=(',',':')).encode())

class Review(ReverseReview):
    def __init__(self):
        super().__init__('gen2-hoenn-interiors-completion',GAMES)
        self.out=OUT;self.out.mkdir(parents=True,exist_ok=True)
        self.prior=[];self.owners={};self.active={};self.used=Counter();self.contexts=defaultdict(list)
        self.maps=[];self.headers=Counter();self.groups={};self.records=[];self.contracts=[]
        modules=dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(ROOT/'main.lua').read_text()))
        for module in modules:
            if ROOT/module==TARGET:continue
            for row in preview.read_reviewed(ROOT/module):
                self.prior.append(row)
                if row['game']in GAMES and row['style']=='gen2':
                    key=row['game'],row['tileset'],row['id'];assert key not in self.active
                    self.active[key]=row;self.owners[key]=module
        for game in GAMES:
            scope_pairs={p for p,mid in self.imp.cell_index(game)if scoped(p,mid)}
            for name,spec in sorted(self.imp.table(game,'gba/native/manifest')['layouts'].items()):
                pair=spec['pair']
                if pair not in scope_pairs:continue
                path=self.cache/game/'data/generated/gba/native'/spec['file'];raw=path.read_bytes()
                blob=raw if raw[:4]==b'SVML'else zlib.decompress(raw);assert blob[:4]==b'SVML'
                sw,sh,w,h=struct.unpack_from('<HHHH',blob,6);w,h=w or sw,h or sh
                bw,bh=blob[14],blob[15];offset=16+bw*bh*2
                mids=[]
                for y in range(h):
                    for x in range(w):
                        mid,coll,elev=struct.unpack_from('<HBB',blob,offset+(y*sw+x)*4);mids.append(mid)
                        if scoped(pair,mid):
                            key=game,pair,mid;self.used[key]+=1
                            if len(self.contexts[key])<12:self.contexts[key].append(dict(map=name,x=x,y=y,collision=coll,elevation=elev))
                for i in range(bw*bh):
                    mid=struct.unpack_from('<H',blob,16+i*2)[0]
                    if scoped(pair,mid):self.headers[game,pair,mid]+=1
                self.maps.append(dict(game=game,map=name,pair=pair,width=w,height=h,mids=mids,
                                      layout_sha256=sha(raw),file=spec['file']))

    def render(self,row):return preview.replacement_image(self.cache,row,self.packed,ROOT)

    def write(self,target):
        def canonical(value):
            if isinstance(value,dict):return {key:canonical(value[key])for key in sorted(value,key=str)}
            if isinstance(value,list):return [canonical(item)for item in value]
            return value
        self.rows={key:canonical(value)for key,value in sorted(self.rows.items())}
        return super().write(target)

    def alias_batch(self):
        guards=json.loads(ALIAS_GUARDS.read_text())
        assert guards['format']==1 and guards['review']=='whole-source/witness/counterpart contact review'
        assert {m['game']+'/'+m['file']:m['layout_sha256']for m in self.maps}==guards['source_layouts_sha256']
        for contract in guards['sources']:
            key=contract['game'],contract['pair'],contract['id'];assert key not in self.active
            assert self.used[key]==contract['body_cells'] and self.headers[key]==contract['header_cells']
            cell=self.imp.cell_index(key[0])[key[1:]]
            assert cell['pixel_sha256']==contract['sourceHash'] and cell.get('behavior')==contract['sourceBehavior']
            assert cell['layer_sha256']==contract['layer_sha256']
            assert [sha(raw)for raw in native_geometry(self,*key)]==contract['geometry_sha256']
            witness=contract['witness'];oldkey=witness['game'],witness['pair'],witness['id'];row=self.active[oldkey]
            assert self.owners[oldkey]==witness['module'] and digest(row)==witness['row_sha256']
            original=self.imp.cell_index(oldkey[0])[oldkey[1:]]
            assert original.get('behavior')==cell.get('behavior')
            assert [sha(raw)for raw in native_geometry(self,*oldkey)]==contract['geometry_sha256']
            assert contract['expected_output_sha256']==row['compositionPixelHash']
            art={name:copy.deepcopy(row[name])for name in ART_FIELDS if name in row}
            result=self.row(key[0],key[1],key[2],'gen2',art,
                'Explicit complete source/witness/counterpart review confirms this exact native indexed three-plane geometry and behavior alias. '
                'The existing complete Crystal counterpart is retained byte-for-byte at native pixel scale; no similarity metric, nearest-color guess, generic replacement or new crop is used. '
                'All source RGBA planes, actual logical layout usage and original collision/elevation coordinates are frozen separately for this alias. '
                'Original room layout, warps, scripted mechanics and actor coordinates remain unchanged.')
            assert result['compositionPixelHash']==contract['expected_output_sha256']
            result['reverseGen2HoennInteriorsCompletion']=dict(reviewed_contract_sha256=digest(contract),
                witness=copy.deepcopy(contract['witness']),indexed_geometry_sha256=contract['geometry_sha256'],pixel_scale=1)
        return len(guards['sources'])

    def surface_batch(self):
        guards=json.loads(SURFACE_GUARDS.read_text());assert guards['format']==1
        for contract in guards['sources']:
            game,pair,mid=contract['game'],contract['pair'],contract['id'];key=game,pair,mid
            assert key not in self.active and (game,'gen2',pair,mid,None) not in self.rows
            cell=self.imp.cell_index(game)[pair,mid]
            assert cell['pixel_sha256']==contract['sourceHash'] and cell.get('behavior')==contract['sourceBehavior']
            assert cell['layer_sha256']==contract['layer_sha256'] and self.used[key]==contract['body_cells']
            assert cell['layer_sha256']['over']==sha(bytes(1024))
            assert cell['layer_sha256'].get('mid',sha(bytes(1024)))in(sha(bytes(1024)),cell['layer_sha256']['under'])
            donor=self.gb_ref('crystal',contract['native_map'],contract['native_block'],contract['native_quadrant'])
            row=self.row(game,pair,mid,'gen2',self.native(donor,'reverse_gen2_hoenn_interiors_complete_'+contract['material']),
                'Whole source room and weighted source context were explicitly reviewed: '+contract['feature']+'. '
                'Uses one complete original Crystal sixteen-pixel '+contract['material']+' module at native scale, with no fractional resizing, extracted source pixels, or unreviewed object suppression. '
                'The literal source RGBA, every priority plane, exact behavior and actual logical-cell usage are frozen separately for this source. '
                'Original map geometry, collision, entrances, actors and scripted mechanics remain unchanged.')
            assert row['compositionPixelHash']==contract['expected_output_sha256']
            row['reverseGen2HoennInteriorsCompletion']=dict(reviewed_contract_sha256=digest(contract),
                named_feature=contract['feature'],source_contexts=contract['source_maps'],pixel_scale=1,native_complete_module=True)

    def feature_batch(self):
        """Only closed, individually fingerprinted named feature members."""
        from classic_geometry_review import art
        guards=json.loads(FEATURE_GUARDS.read_text());assert guards['format']==1
        for contract in guards['sources']:
            game,pair,mid=contract['game'],contract['pair'],contract['id'];key=game,pair,mid
            assert key not in self.active and (game,'gen2',pair,mid,None) not in self.rows
            cell=self.imp.cell_index(game)[pair,mid]
            assert cell['pixel_sha256']==contract['sourceHash'] and cell.get('behavior')==contract['sourceBehavior']
            assert cell['layer_sha256']==contract['layer_sha256'] and self.used[key]==contract['body_cells']
            assert self.headers[key]==contract['header_cells']
            if 'floor_witness' in contract:
                floor_game,floor_pair,floor_mid=contract['floor_witness']
                floor=self.active.get((floor_game,floor_pair,floor_mid)) or self.rows.get((floor_game,'gen2',floor_pair,floor_mid,None))
                assert floor and floor['kind']=='native'
                assert floor['donor']==contract['ground']['donor']
            colors={tuple(entry[:3]):tuple(entry[3:])for entry in contract['colorMap']}
            recipe=art(self,game,pair,mid,contract['feature'],contract['palette'],colors,
                'reverse_gen2_hoenn_named_'+contract['feature'],ground=contract.get('ground'),
                native_over=contract.get('nativeOver'),source_animation=contract.get('sourceAnimation'))
            assert recipe['classicGeometry']['animationManifestHash']==contract['animationManifestHash']
            row=self.row(game,pair,mid,'gen2',recipe,
                'Named whole-feature context review: '+contract['review']+'. '
                'A documented four-color Crystal derivative retains every original pixel coordinate, silhouette, carved glyph, doorway/stair anchor and separate native priority plane. '
                'The literal RGB-to-Crystal table, full source RGBA planes, animation-manifest identity and exact logical-cell usage are frozen independently. '
                'This is a limited-palette derivative of the named Hoenn feature, not native Crystal donor artwork. '
                'No geometry is cropped, shrunk, filled over or inferred from a generic material; collision, actors and scripted mechanics remain unchanged.')
            assert row['compositionPixelHash']==contract['expected_output_sha256']
            if 'expected_phase_sha256' in contract:
                assert [sha(frame.tobytes())for frame in preview.replacement_frames(self.cache,row,self.packed,ROOT)]==contract['expected_phase_sha256']
            row['reverseGen2HoennInteriorsCompletion']=dict(reviewed_contract_sha256=digest(contract),
                named_feature=contract['feature'],source_contexts=contract['source_maps'],pixel_scale=1,
                original_feature_geometry=True,independent_output_sha256=contract['expected_output_sha256'])

    def object_batch(self):
        guards=json.loads(OBJECT_GUARDS.read_text());assert guards['format']==1
        for contract in guards['sources']:
            game,pair,mid=contract['game'],contract['pair'],contract['id'];key=game,pair,mid
            assert key not in self.active and (game,'gen2',pair,mid,None) not in self.rows
            cell=self.imp.cell_index(game)[pair,mid]
            assert cell['pixel_sha256']==contract['sourceHash'] and cell.get('behavior')==contract['sourceBehavior']
            assert cell['layer_sha256']==contract['layer_sha256'] and self.used[key]==contract['body_cells']
            if 'reviewed_layout_sha256' in contract:
                layouts=[m for m in self.maps if m['game']==game and m['map'] in contract['source_maps']]
                assert len(layouts)==1 and layouts[0]['layout_sha256']==contract['reviewed_layout_sha256']
            row=self.row(game,pair,mid,'gen2',contract['art'],contract['review']+
                ' Uses complete original Crystal object artwork at native pixel scale and the exact selected native floor; only connected exterior floor pixels are excluded. '
                'Whole source identity, every source priority plane, behavior and actual logical usage are frozen independently. '
                'No source room layout, collision, warp, actor or interaction changes.')
            assert row['compositionPixelHash']==contract['expected_output_sha256']
            row['reverseGen2HoennInteriorsCompletion']=dict(reviewed_contract_sha256=digest(contract),
                named_feature=contract['feature'],source_contexts=contract['source_maps'],pixel_scale=1,complete_native_module=True)

    def save(self,activate=False):
        self.rows=dict(sorted(self.rows.items()))
        self.write(TARGET if activate else self.out/'candidate.lua')
        keys={(r['game'],r['tileset'],r['id'])for r in self.rows.values()}
        scenes=[]
        for m in self.maps:
            used=sum((m['game'],m['pair'],mid)in keys for mid in m['mids'])
            if used:scenes.append(dict(game=m['game'],map=m['map'],new_cells=used))
        (self.out/'new-keys.json').write_text(json.dumps([dict(game=g,pair=p,mid=mid)for g,p,mid in sorted(keys)],indent=2)+'\n')
        (self.out/'affected-scenes.json').write_text(json.dumps(scenes,indent=2)+'\n')
        (self.out/'source-layout-hashes.json').write_text(json.dumps({m['game']+'/'+m['file']:m['layout_sha256']for m in self.maps},indent=2)+'\n')
        return dict(new_keys=len(keys),new_body_cells=sum(self.used[key]for key in keys),affected_maps=len(scenes),activated=activate)

    def inventory(self,contacts=False):
        for key in sorted(set(self.used)|set(self.headers)):
            game,pair,mid=key
            if key in self.active:continue
            source=self.imp.cell_index(game).get((pair,mid))
            if source is None:
                self.records.append(dict(game=game,pair=pair,id=mid,missing_native_source=True,body_cells=self.used[key],header_cells=self.headers[key]));continue
            geometry=[sha(data)for data in native_geometry(self,game,pair,mid)]
            item=dict(game=game,pair=pair,id=mid,sourceHash=source['pixel_sha256'],sourceBehavior=source.get('behavior'),
                      layer_sha256=source['layer_sha256'],geometry_sha256=geometry,body_cells=self.used[key],header_cells=self.headers[key],contexts=self.contexts[key])
            self.records.append(item)
            signature=digest([pair,source.get('behavior'),geometry])
            group=self.groups.setdefault(signature,dict(signature=signature,pair=pair,items=[],geometry_sha256=geometry,behavior=source.get('behavior')))
            group['items'].append(item)
        groups=sorted(self.groups.values(),key=lambda g:(-sum(i['body_cells']for i in g['items']),g['pair'],g['signature']))
        for index,group in enumerate(groups):group['review_index']=index
        self.group_list=groups
        summary=dict(missing_keys=len(self.records),missing_groups=len(groups),body_cells=sum(r['body_cells']for r in self.records),
                     header_cells=sum(r['header_cells']for r in self.records),by_game=dict(Counter(r['game']for r in self.records)),
                     by_pair={p:dict(keys=len([r for r in self.records if r['pair']==p]),body_cells=sum(r['body_cells']for r in self.records if r['pair']==p))for p in sorted({r['pair']for r in self.records})})
        (self.out/'inventory.json').write_text(json.dumps(groups,indent=2)+'\n')
        (self.out/'missing-keys.json').write_text(json.dumps(self.records,indent=2)+'\n')
        (self.out/'inventory-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        if contacts:self.contacts(groups)
        return summary

    def contacts(self,groups):
        font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',11)
        for start in range(0,len(groups),64):
            panel=Image.new('RGB',(8*176,8*124+34),'#18212b');draw=ImageDraw.Draw(panel)
            draw.text((8,8),'Missing actual-used Hoenn interior cells; source context required before authoring',font=font,fill='white')
            for number,group in enumerate(groups[start:start+64]):
                source=next((s for s in group['items']if s['game']=='emerald'),group['items'][0]);x,y=number%8*176,number//8*124+34
                ref=dict(game=source['game'],tileset=source['pair'],id=source['id'],hash=source['sourceHash'])
                image=preview.native_donor(self.cache,ref,self.packed)
                panel.paste(image.resize((64,64),Image.Resampling.NEAREST),(x+4,y+20))
                draw.text((x+4,y+2),f"{group['review_index']}: {source['id']}",font=font,fill='white')
                draw.text((x+72,y+20),source['pair'].replace('building__','')[:16]+'\nB:'+str(source['sourceBehavior'])+'\n'+str(sum(s['body_cells']for s in group['items'])),font=font,fill='#cbd6e3')
                contexts=source['contexts'];draw.text((x+4,y+90),contexts[0]['map'][3:27]if contexts else'Header only',font=font,fill='#a9c6d5')
            panel.save(self.out/f'missing-contact-{start//64+1:02}.png')

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--inventory',action='store_true');parser.add_argument('--contacts',action='store_true');parser.add_argument('--aliases',action='store_true');parser.add_argument('--build',action='store_true');parser.add_argument('--features',action='store_true');parser.add_argument('--validate',action='store_true');parser.add_argument('--activate',action='store_true');args=parser.parse_args()
    assert not args.activate or args.validate
    review=Review();report=review.inventory(args.contacts)
    if args.aliases or args.build:
        review.alias_batch()
        if args.build:
            review.surface_batch()
            if OBJECT_GUARDS.exists():review.object_batch()
        if args.features:review.feature_batch()
        report.update(review.save(False))
        if args.validate:report['neutral']=review.validate();report['status']='passed'
        if args.activate:report.update(review.save(True))
    (review.out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)

if __name__=='__main__':main()
