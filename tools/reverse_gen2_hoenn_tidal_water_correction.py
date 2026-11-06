"""Correct the common Hoenn cave and Mirage Island tidal shoreline."""

import argparse
from collections import defaultdict
import copy
import json
from pathlib import Path

from PIL import Image

import catalog
from classic_geometry_review import source_under_frames
import preview
from reverse_common import ROOT
from reverse_gen2_hoenn_alternate_layouts import CAVE, Review as AlternateReview, grid, parts


MIDS=(397,398,413,414,415,419,420,421,422,423,429,431,437,439,445,446,447)
GUARDS=Path(__file__).with_name('reverse_gen2_hoenn_tidal_water_guards.json')
SAND={91,92,93,94}
SHALLOW={70,75}
OWNERS=('mappings/reverse_gen2_hoenn_outdoor_finish.lua',
        'mappings/reverse_gen2_hoenn_outdoor_remaining.lua')
# The few source pixels colored 77 through every relevant phase lie in
# these eight-pixel quadrants or alongside the actual diagonal tide line.
DIAGONALS={
    429:('right',[16]*8+[13,10,9,9,8,8,8,8]),
    431:('left',[0]*8+[4,6,7,8,8,8,8,8]),
    445:('right',[8,8,8,8,9,9,10,12]+[16]*8),
    447:('left',[8,7,7,8,8,7,7,5]+[0]*8),
}


def digest(value):
    return catalog.sha(json.dumps(value,sort_keys=True,separators=(',',':')).encode())


class Review(AlternateReview):
    def __init__(self,baseline):
        super().__init__(baseline)
        self.out=ROOT.parent/'.work/tileshift-reverse-gen2-hoenn-tidal-water'
        self.out.mkdir(exist_ok=True)
        self.scoped_sources={}
        self.shallow=copy.deepcopy(self.water)
        shallow=[[222,255,222],[181,197,255],[140,165,222],[82,107,206]]
        self.shallow['palettes']=[copy.deepcopy(shallow) for _ in range(8)]
        self.sand=self.gb_at('crystal','PALLET_TOWN',2,3)

    @staticmethod
    def boundary(mid,x,y):
        if mid in DIAGONALS:
            side,limits=DIAGONALS[mid]
            return x>=limits[y] if side=='right' else x<limits[y]
        if mid==419:
            return y<8 or x>=8
        if mid==420:
            return y<8 or x<8
        if mid==437:
            return x>=8
        if mid==439:
            return x<8
        assert mid==446
        return y<8

    def depth(self,game,mid,palette,visible):
        if 78 not in visible:
            assert not set(visible)-SAND-SHALLOW-{77}
            return [v not in SAND for v in visible]
        assert set(visible)<=SHALLOW|{77,78}
        animation=self.bank(game,CAVE,mid,'general_water','water_mask')
        frames,_,_=source_under_frames(self.cache,game,CAVE,mid,self.packed,animation)
        shallow_colors={palette[i] for i in SHALLOW}
        deep=palette[78]
        masks=[]
        for i,value in enumerate(visible):
            if value!=77:
                masks.append(value in SHALLOW)
                continue
            x,y=i%16,i//16
            sequence={frame.getpixel((x,y))[:3] for frame in frames}
            has_shallow,has_deep=bool(sequence&shallow_colors),deep in sequence
            masks.append(has_shallow if has_shallow!=has_deep else self.boundary(mid,x,y))
        return masks

    def contexts(self):
        scenes={}
        for game in self.games:
            root=self.cache/game/'data/generated/gba/native'
            by_mid=defaultdict(set)
            for name,spec in self.imp.table(game,'gba/native/manifest')['layouts'].items():
                if spec['pair']!=CAVE:
                    continue
                board=grid(root/spec['file'])
                used={m for m,_,_ in board[3]}&set(MIDS)
                if not used:
                    continue
                assert any(word in name for word in ('SHOAL_CAVE','SEAFLOOR_CAVERN_ENTRANCE','MARINE_CAVE_ENTRANCE')), (game,name,used)
                scenes[game,name,'body']=board
                for mid in used:
                    by_mid[mid].add((name,'body'))
            name={'ruby':'RU_ROUTE130','sapphire':'SA_ROUTE130','emerald':'EM_ROUTE130'}[game]
            assert catalog.dict_at(self.imp.table(game,'gba/native/layout_files'),46)=='alt_46'
            pair,_,alternate=self.board(game,name,'alt_46')
            assert pair==CAVE and set(MIDS)<={m for m,_,_ in alternate[3]}
            scenes[game,name,'alt_46']=alternate
            for mid in MIDS:
                by_mid[mid].add((name,'alt_46'))
                self.scoped_sources[game,mid]=sorted(by_mid[mid])
        return scenes

    def build(self):
        scenes=self.contexts()
        keys={(g,CAVE,m) for g in self.games for m in MIDS}
        locations={}
        for module in OWNERS:
            for i,row in enumerate(preview.read_reviewed(self.baseline/module)):
                key=row['game'],row['tileset'],row['id']
                if key in keys and row['style']=='gen2' and not row.get('map'):
                    assert key not in locations
                    locations[key]=(module,i)
        assert locations.keys()==keys
        records=[]
        for game,pair,mid in sorted(keys):
            source=self.imp.cell_index(game)[pair,mid]
            palette,planes,visible=self.source(game,pair,mid)
            assert not any(planes['over'])
            sand=[i in SAND for i in visible]
            shallow=self.depth(game,mid,palette,visible)
            assert not any(a and b for a,b in zip(shallow,sand))
            layers=[self.water_part(),*parts(self.shallow,shallow,animated=True),*parts(self.sand,sand)]
            art=self.animated_surface('complete_native_shallow_tidal_water_and_sand',layers)
            old=self.anchor(game,pair,mid)
            row=self.row(game,pair,mid,'gen2',art,
                         'The complete source contour is animated shallow water or a real sand join, using the same '
                         'native Crystal water pattern in both depth shades. Every actual cave and Mirage Island '
                         'placement uses that same two-depth shoreline geometry.')
            for name,h in source['layer_sha256'].items():
                ref=dict(game=game,tileset=pair,id=mid,hash=source['pixel_sha256'])
                preview.native_donor(self.cache,ref,self.packed,[name],{name:h})
            contexts=[]
            for name,layout in self.scoped_sources[game,mid]:
                board=scenes[game,name,layout]
                contexts.append(dict(map=name,layout=layout,hash=board[0],
                                     placements=sum(cell[0]==mid for cell in board[3])))
            module,index=locations[game,pair,mid]
            frames=preview.replacement_frames(self.cache,row,self.packed,self.baseline)
            records.append(dict(game=game,pair=pair,mid=mid,module=module,index=index,
                                old_row_sha256=digest(old),old=old,new=row,
                                source_layers=source['layer_sha256'],contexts=contexts,
                                shallow=''.join('1' if bit else '0' for bit in shallow),
                                sand=''.join('1' if bit else '0' for bit in sand),
                                output_frames=[catalog.sha(frame.tobytes()) for frame in frames]))
        self.draw(scenes)
        return records

    def draw(self,scenes):
        for (game,name,layout),(_,w,h,cells) in scenes.items():
            canvas=Image.new('RGBA',(w*16,h*16))
            done={}
            for i,(mid,_,_) in enumerate(cells):
                if mid not in done:
                    key=game,'gen2',CAVE,mid,None
                    row=self.rows.get(key) or self.active.get((game,CAVE,mid))
                    if row:
                        done[mid]=self.render(row)
                    else:
                        item=self.imp.cell_index(game)[CAVE,mid]
                        ref=dict(game=game,tileset=CAVE,id=mid,hash=item['pixel_sha256'])
                        done[mid]=preview.native_donor(self.cache,ref,self.packed)
                canvas.paste(done[mid],(16*(i%w),16*(i//w)))
            canvas.save(self.out/f'{game}-{name}-{layout}.png')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path,default=ROOT)
    parser.add_argument('--freeze',action='store_true')
    parser.add_argument('--validate',action='store_true')
    args=parser.parse_args()
    review=Review(args.baseline.resolve())
    proof=json.loads(json.dumps(review.build()))
    if args.freeze:
        GUARDS.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    else:
        assert proof==json.loads(GUARDS.read_text(encoding='utf-8')), 'Reviewed tide source context or artwork changed'
    review.write(review.out/'candidate.lua')
    (review.out/'supersessions.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    keys=[{k:r[k] for k in ('game','pair','mid')} for r in proof]
    (review.out/'keys.json').write_text(json.dumps(keys,indent=2)+'\n',encoding='utf-8')
    scenes=sorted({(r['game'],c['map'],c['layout'])for r in proof for c in r['contexts']})
    (review.out/'affected-scenes.json').write_text(json.dumps(scenes,indent=2)+'\n',encoding='utf-8')
    result=review.validate() if args.validate else None
    print(json.dumps(dict(rows=len(proof),scene_layouts=len(scenes),validation=result)))


if __name__=='__main__':
    main()
