"""Native Red Silph, Fighting Dojo, Mansion and Lab facades for FRLG."""

import argparse
from collections import defaultdict
import json
from pathlib import Path

from PIL import Image

import preview
from reverse_common import ROOT
from reverse_gen1_kanto_gyms import Review as GymReview
from reverse_gen2_cinnabar_pallet_completion import LAB, MANSION
from reverse_gen2_kanto_saffron import DOJO, TOWER
from reverse_kanto_review import exterior, ground_ref, runs
from reverse_oldale_review import mask_piece


GUARDS = Path(__file__).with_name('reverse_gen1_kanto_landmarks_guards.json')
CITY = 'FR_SAFFRON_CITY'
CONNECTION = 'FR_SAFFRON_CITY_CONNECTION'
ISLAND = 'FR_CINNABAR_ISLAND'
ROUTE = 'FR_ROUTE_21_SOUTH'
FOOTPRINTS = {
    'silph': (TOWER, CITY, 29, 16, (33,30,'FR_SILPH_CO_1F')),
    'dojo': (DOJO, CITY, 37, 8, (40,12,'FR_SAFFRON_CITY_DOJO')),
    'mansion': (MANSION, ISLAND, 5, -1, (8,3,'FR_POKEMON_MANSION_1F')),
    'lab': (LAB, ISLAND, 5, 6, (8,9,'FR_CINNABAR_ISLAND_POKEMON_LAB_ENTRANCE')),
}


class Review(GymReview):
    def __init__(self, baseline):
        super().__init__(baseline)
        self.out = ROOT.parent / '.work/tileshift-reverse-gen1-kanto-landmarks'
        self.out.mkdir(exist_ok=True)

    def contexts(self):
        for game in self.games:
            for feature,(matrix,name,x0,y0,expected_warp) in FOOTPRINTS.items():
                scene = self.layout(game,name)
                warp, = [w for w in scene['warps'] if (w['x'],w['y'],w['destMap']) == expected_warp]
                uses = []
                if name==CITY:
                    uses.append((CONNECTION,x0-10,y0-7))
                if feature=='mansion':
                    links=self.imp.table(game,'gba/connections')[name]
                    assert dict(dir='north',map=ROUTE,offset=0) in links
                    uses.append((ROUTE,x0,self.layout(game,ROUTE)['height']-1))
                yield dict(game=game,feature=feature,name=name,pair=scene['pair'],x0=x0,y0=y0,
                           town='SAFFRON_CITY' if name==CITY else 'CINNABAR_ISLAND',
                           matrix=matrix,uses=uses,warp=warp,width=len(matrix[0]))

    def silph(self,x,y,mid):
        name='SAFFRON_CITY'
        if y<5:
            sx=(0 if x==0 else 7 if x==8 else 1)*16
            sy=(0,8,8,8,16)[y]
            return self.source_piece(name,256+sx,160+sy)
        if y==14:
            sx=(0,1,4,1,2,3,4,6,7)[x]
            sy=21
        elif y==13 and mid!=714:
            sx=(0,1,2,1,2,3,2,6,7)[x]
            sy=20
        else:
            sx=(0,1,2,2,2,2,2,6,7)[x]
            sy=12 if y==5 else 14
        return self.source_piece(name,(16+sx)*16,sy*16)

    def cinnabar(self,feature,x,y):
        name='CINNABAR_ISLAND'
        roof_rows=3 if feature=='mansion' else 2
        base_y=0 if feature=='mansion' else 96
        if y<roof_rows:
            sx=0 if x==0 else 80 if x==6 else 16
            sy=(0,8,16)[y] if feature=='mansion' else y*16
        else:
            sy=(2+y-roof_rows)*16
            if feature=='mansion':
                sx=(0,1,1,2,3,4,5)[x]*16
            elif y==2:
                sx=(0,1,1,2,1,1,5)[x]*16
            else:
                sx=(0,1,3,2,4,4,5)[x]*16
        parts=self.source_piece(name,64+sx,base_y+sy)
        if feature=='lab' and y==3 and x in (4,5):
            ref=self.gb_at('red',name,9,11)
            image=self.gb_image(ref)
            outside=exterior(image,{(255,255,255,255)})
            side=x-4
            bits=[(i,j) not in outside and i//8==side for j in range(16) for i in range(16)]
            parts += [dict(p,donor=ref,srcX=p['x'],srcY=p['y'],x=p['x']+8-side*16) for p in runs(bits)]
        return parts

    def art(self, context):
        feature=context['feature']
        if feature=='dojo':
            # Red used the same native Gym facade and word for the Dojo.
            viridian=self.imp.gb('red','VIRIDIAN_CITY')[0]
            saffron=self.imp.gb('red','SAFFRON_CITY')[0]
            assert viridian.crop((464,96,528,112)).tobytes()==saffron.crop((368,32,432,48)).tobytes()
            return self.gym_art(context)
        width=context['width']
        roof_rows={'silph':5,'mansion':3,'lab':2}[feature]
        backing=(self.gb_ref('red','PALLET_TOWN',1,2) if feature=='silph' else ground_ref(self,'gen1'))
        output={}
        for y,line in enumerate(context['matrix']):
            for x,mid in enumerate(line):
                roof=y<roof_rows
                pieces=self.silph(x,y,mid) if feature=='silph' else self.cinnabar(feature,x,y)
                raw=self.composite(None,pieces,f'gen1_complete_native_{feature}')
                if x in (0,width-1):
                    margin=3 if roof else 1
                    bits=[(i>=margin if x==0 else i<16-margin) for j in range(16) for i in range(16)]
                    output[x,y]=mask_piece(self,raw,bits,backing,roof)
                else:
                    output[x,y]=dict(raw,overMask=('1' if roof else '0')*256)
        return output

    def build(self):
        contexts=list(self.contexts())
        for context in contexts:
            game, pair, name, feature, x0, y0 = (context[k] for k in ('game','pair','name','feature','x0','y0'))
            arts=self.art(context)
            matrix=context['matrix']
            output=Image.new('RGBA',(16*context['width'],16*len(matrix)))
            for y,line in enumerate(matrix):
                for x,mid in enumerate(line):
                    map_name, source_x, source_y = name,x0+x,y0+y
                    if source_y<0:
                        map_name,start_x,source_y=context['uses'][0]
                        source_x=start_x+x
                    self.place(game,pair,mid,map_name,source_x,source_y)
                    if name==CITY:
                        self.place(game,pair,mid,CONNECTION,x0+x-10,y0+y-7)
                    row=self.row(game,pair,mid,'gen1',arts[x,y],
                                 'Complete original Red landmark modules at native pixel size. Only complete '
                                 'interior brick, roof and window bands repeat. The actual doorway and exterior '
                                 'sign align with their original source placements and connected maps.')
                    output.paste(self.render(row),(16*x,16*y))
            output.save(self.out/f'{game}-{feature}.png')
        reviewed=self.verify_use()
        layouts={f'{g}/{n}':s['file_sha256'] for (g,n),s in self.layouts.items()}
        return dict(contexts=contexts,layouts=layouts,reviewed=reviewed)

    def place(self,game,pair,mid,name,x,y):
        scene=self.layout(game,name)
        assert scene['pair']==pair and scene['cells'][y][x][0]==mid,(game,name,x,y,mid)
        assert (game,pair,mid,None) not in self.active and (game,pair,mid,name) not in self.active
        self.placements[game,pair,mid].add((name,x,y))

    def verify_use(self):
        actual=defaultdict(set)
        for game in self.games:
            pairs={pair for g,pair,_ in self.placements if g==game}
            for name,spec in self.imp.table(game,'gba/native/manifest')['layouts'].items():
                pair=spec['pair']
                if pair not in pairs:
                    continue
                for y,line in enumerate(self.layout(game,name)['cells']):
                    for x,(mid,_,_) in enumerate(line):
                        if (game,pair,mid) in self.placements:
                            actual[game,pair,mid].add((name,x,y))
        report=[]
        for key,expected in sorted(self.placements.items()):
            game,pair,mid=key
            assert actual[key]==expected,(key,actual[key]-expected)
            row=self.rows[game,'gen1',pair,mid,None]
            cell=self.imp.cell_index(game)[pair,mid]
            ref=dict(game=game,tileset=pair,id=mid,hash=cell['pixel_sha256'])
            for layer,digest in cell['layer_sha256'].items():
                preview.native_donor(self.cache,ref,self.packed,[layer],{layer:digest})
            report.append(dict(game=game,pair=pair,mid=mid,positions=sorted(expected),
                               source=cell['pixel_sha256'],layers=cell['layer_sha256'],behavior=cell['behavior'],
                               output=row['compositionPixelHash'],over_mask=row['overMask']))
        return report


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
        assert proof==json.loads(GUARDS.read_text(encoding='utf-8')), 'Reviewed landmark geometry changed'
    review.write(review.out/'candidate.lua')
    keys=[{k:r[k] for k in ('game','pair','mid')} for r in proof['reviewed']]
    (review.out/'keys.json').write_text(json.dumps(keys,indent=2)+'\n',encoding='utf-8')
    result=review.validate() if args.validate else None
    print(json.dumps(dict(rows=len(review.rows),body_cells=sum(len(r['positions']) for r in proof['reviewed']),validation=result)))


if __name__=='__main__':
    main()
