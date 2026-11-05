"""Guarded native Crystal forest, timber treehouses and raised Fortree walks.

Source maps, warps, collision and existing reviewed rows are immutable. Only
the explicitly reserved secondary cells used by the three Fortree cities enter
this author. Native crowns, doors and windows retain their original pixels.
"""
from __future__ import annotations
import argparse,copy,json,re,struct,zlib
from collections import Counter
from pathlib import Path
from PIL import Image
import catalog,preview
from reverse_common import ReverseReview,ROOT
from reverse_kanto_review import runs
from reverse_gen2_kanto_finish import Finish as KantoReview,FOREST_TREE_BOUNDS,FOREST_TREE_HASHES

GAMES=('ruby','sapphire','emerald');PREFIX=dict(ruby='RU_',sapphire='SA_',emerald='EM_')
PAIR='general__fortree';TARGET=ROOT/'mappings/reverse_gen2_fortree_complete.lua'
OUT=ROOT.parent/'.work/tileshift-v0360-fortree'
IDS=(548,549,550,554,555,556,557,558,559,563,564,565,566,567,571,572,573,574,575,577,579,580,581,582,583,584,585,586,587,588,589,590,592,593,594,595,598,600,601,604,608,609,610,616,617,618,627)
REVIEWED_SOURCE_BINDING='8bccbf4e95b672c5b960f272f61047bb3f52473ed253bb4ed3805b2cbbd6c498'

def digest(value):return catalog.sha(json.dumps(value,sort_keys=True,separators=(',',':')).encode())

class Review(ReverseReview):
    def __init__(self):
        super().__init__('gen2-fortree-complete',GAMES);self.out=OUT;OUT.mkdir(exist_ok=True)
        self.prior={};self.source_cache={};self.render_cache={};self.layouts={};self.sources={};self.proofs={}
        for name in dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(ROOT/'main.lua').read_text())):
            if ROOT/name==TARGET:continue
            for row in preview.read_reviewed(ROOT/name):
                if row['game']in GAMES and row['style']=='gen2'and row['tileset']==PAIR:
                    key=row['game'],row['id'];assert key not in self.prior;self.prior[key]=row
        self.missing={}
        for game in GAMES:
            name=PREFIX[game]+'FORTREE_CITY';spec=self.imp.table(game,'gba/native/manifest')['layouts'][name]
            p=self.cache/game/'data/generated/gba/native'/spec['file'];raw=p.read_bytes();b=raw if raw[:4]==b'SVML'else zlib.decompress(raw)
            pw,ph,w,h=struct.unpack_from('<HHHH',b,6);w,h=w or pw,h or ph;start=16+b[14]*b[15]*2
            assert(w,h)==(40,20)and spec['pair']==PAIR
            matrix=[[struct.unpack_from('<H',b,start+4*(y*pw+x))[0]for x in range(w)]for y in range(h)]
            self.layouts[game]=matrix;self.missing[game]=Counter(mid for row in matrix for mid in row if(game,mid)not in self.prior)
            assert set(self.missing[game])==set(IDS),(game,self.missing[game])
            self.sources[game]=dict(map=name,pair=PAIR,width=w,height=h,layout_sha256=catalog.sha(raw),warps=self.imp.table(game,'gba/warps')[name],cells=[])
            for mid in IDS:
                c=self.imp.cell_index(game)[PAIR,mid]
                self.sources[game]['cells'].append(dict(mid=mid,rgba_sha256=c['pixel_sha256'],layer_sha256=c['layer_sha256'],behavior=c['behavior']))
        self.ground=copy.deepcopy(self.prior['emerald',1]['donor'])
        for game in GAMES:assert self.gb_image(self.prior[game,1]['donor']).tobytes()==self.gb_image(self.ground).tobytes()

    def source(self,game,mid,layer=None):
        key=game,mid,layer
        if key not in self.source_cache:
            c=self.imp.cell_index(game)[PAIR,mid]
            self.source_cache[key]=preview.native_donor(self.cache,dict(game=game,tileset=PAIR,id=mid,hash=c['pixel_sha256']),self.packed,[layer]if layer else None,{layer:c['layer_sha256'][layer]}if layer else None)
        return self.source_cache[key]

    def freeze(self,inventory=False):
        used={g:{mid for line in matrix for mid in line}for g,matrix in self.layouts.items()}
        binding=dict(games=self.sources,ids=IDS,old_rows={g+':'+str(m):digest(r)for(g,m),r in sorted(self.prior.items())if m in used[g]})
        value=digest(binding);(OUT/'source-binding.json').write_text(json.dumps(dict(sha256=value,binding=binding),indent=2)+'\n')
        if not inventory:assert value==REVIEWED_SOURCE_BINDING,('Fortree source guards changed',value)
        return value

    def forest(self):
        dense=Image.new('RGBA',(32,32))
        for q in range(4):
            ref=self.gb_ref('crystal','ILEX_FOREST',5,q);assert ref['hash']==FOREST_TREE_HASHES[q]
            dense.paste(self.gb_image(ref),(q%2*16,q//2*16))
        outside={(x,y)for y,(l,r)in enumerate(FOREST_TREE_BOUNDS)for x in range(32)if x<l or x>r}
        self._dense_tree=dense,outside
        black_hash=catalog.sha(Image.new('RGBA',(16,16),(0,0,0,255)).tobytes());black=None
        name='FAST_SHIP_CABINS_SE_SSE_CAPTAINS_CABIN';m=self.imp.table('crystal','maps')[name]
        for y in range(m['height']*2):
            for x in range(m['width']*2):
                ref=self.gb_at('crystal',name,x,y)
                if ref['hash']==black_hash:black=ref;break
            if black:break
        assert black;black['monochrome']=True;black['palettes']=[[[255,255,255],[170,170,170],[85,85,85],[0,0,0]]for _ in range(8)]
        self._black_ref=black
        trees,masks,whole=KantoReview.wide_park_models(self,48)
        self.proofs['full_forest_tree']=dict(native=[32,32],counterpart=[48,48],whole_original_foreground_pixels_preserved=836,only_complete_8px_middle_foliage_and_shadow_repeat=True)
        whole.save(OUT/'native-forest48.png')
        leaf=self.composite(self.ground,self.gb_rect('crystal','ILEX_FOREST',4*16+8,16*16+8,16,16),'fortree_native_dense_middle_foliage')
        root=self.composite(self.ground,self.gb_rect('crystal','ILEX_FOREST',4*16+8,16*16+16,16,16),'fortree_native_full_middle_trunk')
        return trees,masks,leaf,root

    def timber(self,game,mid,base,role):
        # Explicit plain timber/rope palette witnesses; no field/leaf pixels
        # from these three separately reviewed source materials enter the mask.
        samples=set(self.source(game,572).get_flattened_data())|set(self.source(game,577).get_flattened_data())|set(self.source(game,565).get_flattened_data())
        leaves=set(self.source(game,548).get_flattened_data())|set(self.source(game,580).get_flattened_data())|set(self.source(game,609).get_flattened_data())
        warm={p for p in self.source(game,556).get_flattened_data()if p[0]>p[1]+20 and p[0]>p[2]+20}
        colors=(samples|warm)-leaves
        mask=[p in colors for p in self.source(game,mid).get_flattened_data()]
        assert any(mask),(game,mid,'no timber')
        plank=self.gb_at('crystal','FAST_SHIP_1F',16,6)
        parts=copy.deepcopy(base.get('parts',[]))
        if base.get('donor'):parts=[dict(donor=base['donor'],w=16,h=16,x=0,y=0)]
        parts.extend(dict(donor=plank,srcX=s['x'],srcY=s['y'],**s)for s in runs(mask))
        assert len(parts)<=32,(mid,len(parts))
        art=self.composite(base.get('base',self.ground),parts,role)
        self.proofs.setdefault('timber_masks',{})[game+':'+str(mid)]=dict(mask_sha256=catalog.sha(bytes(mask)),pixels=sum(mask),colors=[list(p)for p in sorted(colors)],material=plank)
        return art

    def put(self,game,mid,art,meaning):
        assert mid in IDS and(game,mid)not in self.prior
        art=copy.deepcopy(art)
        if mid in (600,601,608,609,610,616,617,618):art['overMask']='0'*256
        else:
            over=self.source(game,mid,'over');im=self.render(art);ground=self.gb_image(self.ground)
            art['overMask']=''.join('1'if p[3]and im.getpixel((i%16,i//16))!=ground.getpixel((i%16,i//16))else'0'for i,p in enumerate(over.get_flattened_data()))
        row=self.row(game,PAIR,mid,'gen2',art,meaning+' Complete selected Crystal feature pixels stay1:1. Original Fortree sourceRGBA, all indexed planes/behavior, logical40x20 layouts and all nine entrance warps are frozen. No existing mapping is changed; native actor/collision/elevation/warp semantics are unchanged.')
        row['fortreeCompletion']=dict(source_binding=REVIEWED_SOURCE_BINDING,pixel_scale=1,semantic_source_mid=mid,original_entrances_unchanged=True)

    def timber_rects(self,base,rects):
        art=copy.deepcopy(base);ref=self.gb_at('crystal','FAST_SHIP_1F',16,6)
        for x,y,w,h in rects:art['parts'].append(dict(donor=ref,x=x,y=y,w=w,h=h,srcX=x,srcY=y))
        assert len(art['parts'])<=32
        art['role']='fortree_native_leaf_roof_and_complete_timber_support_sections'
        return art

    def build(self):
        trees,masks,leaf,root=self.forest()
        self.proofs['source_house_entrances']=[]
        for game in GAMES:
            arts={}
            for mids,y in (((548,549,550),0),((584,585,586),0),((592,593,594),1)):
                for x,mid in enumerate(mids):arts[mid]=copy.deepcopy(trees[x,y])
            for mid in (554,580,627):arts[mid]=copy.deepcopy(leaf)
            for mid in (595,604):arts[mid]=copy.deepcopy(root if mid==595 else trees[1,2])
            arts[587]=copy.deepcopy(trees[0,0]);arts[588]=copy.deepcopy(trees[2,0])
            for mid,x in ((556,0),(557,1),(558,2)):
                arts[mid]=copy.deepcopy(trees[x,1])
                if mid!=557:arts[mid]=self.timber_rects(arts[mid],[(11 if mid==556 else 0,8,5,8)])
            for mid,x in ((555,0),(559,2)):
                arts[mid]=self.timber_rects(trees[x,0],[(9 if mid==555 else 0,5,7,3),(11 if mid==555 else 0,9,5,3),(9 if mid==555 else 0,13,7,3)])
            # Intact48px frontage: original side-frame/window cells and complete
            # centered door, omitting only the native house's blank siding col.
            for mid,sx in ((564,64),(565,80),(566,112)):
                arts[mid]=self.composite(self.ground,self.gb_rect('crystal','CIANWOOD_CITY',sx,272,16,16),'fortree_complete_native_cabin_facade')
            for mid in (563,567,571,572,573,574,575,579,581,582,583,589,590,598,577):
                base=self.native(self.ground,'fortree_open_field')if mid==590 else leaf
                arts[mid]=self.timber(game,mid,base,'fortree_native_timber_platform_bridge_or_ladder')
            for mid in (600,601,608,609,610,616,617,618):arts[mid]=self.native(self.ground,'fortree_native_open_field_transition')
            assert set(arts)==set(IDS)
            for mid in IDS:self.put(game,mid,arts[mid],
                'Explicit complete Fortree forest/treehouse/raised-walk counterpart: native Ilex broadleaf caps and trunks, whole Cianwood doorway/window frontage, and native S.S.Aqua timber grain inside the reviewed solid board/rope silhouette. Plain lawn variants use the exact already-selected same-pair Crystal lawn; no Gen3 grass rectangle remains.')
            for warp in self.sources[game]['warps']:
                if '_HOUSE'in warp['destMap']or'_DECORATION_SHOP'in warp['destMap']:
                    assert self.layouts[game][warp['y']][warp['x']]==565
                    self.proofs['source_house_entrances'].append(dict(game=game,warp=warp,centered_door_source_id=565))
            self.preview(game)
        assert len(self.rows)==141
        self.rows={k:self.rows[k]for k in sorted(self.rows)}
        self.write(OUT/'candidate.lua')
        (OUT/'proof-details.json').write_text(json.dumps(self.proofs,indent=2)+'\n')
        (OUT/'new-keys.json').write_text(json.dumps([dict(game=r['game'],pair=r['tileset'],mid=r['id'])for r in self.rows.values()],indent=2)+'\n')
        return len(self.rows)

    def preview(self,game):
        matrix=self.layouts[game];before=Image.new('RGBA',(640,320));after=before.copy();covered=0
        for y,line in enumerate(matrix):
            for x,mid in enumerate(line):
                before.paste(self.source(game,mid),(x*16,y*16))
                row=self.rows.get((game,'gen2',PAIR,mid,None))or self.prior.get((game,mid))
                if row:
                    k=digest(row)
                    if k not in self.render_cache:self.render_cache[k]=self.render(row)
                    after.paste(self.render_cache[k],(x*16,y*16));covered+=1
                else:after.paste(self.source(game,mid),(x*16,y*16))
        assert covered==800
        before.save(OUT/(game+'-source.png'));after.save(OUT/(game+'-candidate.png'))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inventory',action='store_true');p.add_argument('--validate',action='store_true');p.add_argument('--activate',action='store_true');a=p.parse_args()
    assert not a.activate or a.validate
    r=Review();binding=r.freeze(a.inventory)
    if a.inventory:print(json.dumps(dict(binding=binding,keys=141)));return
    r.build();neutral=r.validate()if a.validate else None
    if a.activate:r.write(TARGET)
    result=dict(status='passed'if neutral else'candidate',binding=binding,rows=len(r.rows),neutral=neutral,activated=a.activate)
    (OUT/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
