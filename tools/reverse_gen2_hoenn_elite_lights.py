"""Preserve both native Elite Four lighting updates in the Crystal theme."""
from pathlib import Path
import argparse
import json

import catalog
import preview
from classic_geometry_review import art as geometry_art,source_under_frames
from reverse_common import ROOT
from reverse_gen2_hoenn_outdoor_remaining import Review as Outdoor

PAIR='building__elite_four'
OUTPUT=ROOT.parent/'.work/tileshift-v0360-elite-lights'
GUARDS=Path(__file__).with_name('reverse_gen2_hoenn_elite_lights_guards.json')
TARGET=ROOT/'mappings/reverse_gen2_hoenn_elite_lights.lua'
LAMP_LEVELS={(173,82,66):1,(247,99,49):3}


class Review(Outdoor):
    def __init__(self):
        super().__init__(OUTPUT)
        self.target_module=TARGET
        self.guards=json.loads(GUARDS.read_text(encoding='utf-8'))
        maps=self.imp.table('crystal','maps')
        palettes=self.imp.table('crystal','palettes')
        self.blue=sorted(map(tuple,preview.palette_set(palettes,maps['OLIVINE_CITY'],'DAY')[6]),key=self.light)

    @staticmethod
    def light(rgb):return (54*rgb[0]+183*rgb[1]+19*rgb[2])/256

    def build(self):
        for item in self.guards:
            game,mid=item['game'],item['mid'];source=self.imp.cell_index(game)[PAIR,mid]
            assert source['pixel_sha256']==item['sourceHash'] and source['layer_sha256']==item['sourceLayers']
            assert source['behavior']==item['sourceBehavior']
            assert (game,'gen2',PAIR,mid,None)not in self.occupied
            for witness in item['contexts']:
                layout=self.native_layout(game,witness['map']);assert layout['pair']==PAIR
                width=layout['width'];actual=[(i%width,i//width)for i,n in enumerate(layout['mids'])if n==mid]
                assert actual==[tuple(p)for p in witness['coords']]
            preview.native_donor(self.cache,dict(game=game,tileset=PAIR,id=mid,hash=source['pixel_sha256']),self.packed)
            mids,colors,planes=self.packed[game,PAIR];offset=mids.index(mid)*256
            animation=item['sourceAnimation']
            frames,_,_=source_under_frames(self.cache,game,PAIR,mid,self.packed,animation)
            assert len({frame.tobytes()for frame in frames})==7
            images=[catalog.rgba_native(blob[offset:offset+256],colors,name!='under')for name,blob in planes.items()]
            images.extend(frames)
            used={p[:3]for image in images for p in image.get_flattened_data()if p[3]}
            mapping={rgb:self.blue[LAMP_LEVELS.get(rgb,sum(self.light(rgb)>=cut for cut in (83,147,208)))]for rgb in used}
            art=geometry_art(self,game,PAIR,mid,'elite_four_joined_floor_and_wall_lamps',self.blue,mapping,
                             source_animation=animation)
            row=self.row(game,PAIR,mid,'gen2',art,
                'The complete left or right Elite Four lamp keeps its source shape, reflected floor detail and priority. '
                'The independent native floor and wall animation banks keep their original timing and write order. '
                'The Crystal material covers every checked combined source state.')
            themed=preview.classic_geometry_frames(self.cache,row,self.packed)
            assert len({frame.tobytes()for frame in themed})==7,('Elite Four lamp states lost contrast',game,mid)
            row['eliteLightReview']=dict(source_binding=catalog.sha(json.dumps(item,sort_keys=True,separators=(',',':')).encode()),pixel_scale=1)
        assert len(self.rows)==6


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate',action='store_true')
    args=parser.parse_args()
    review=Review();review.build();proof=review.validate()
    review.write(OUTPUT/'candidate.lua')
    if args.activate:review.write(TARGET)
    print(json.dumps(dict(rows=len(review.rows),body_cells=sum(len(w['coords'])for r in review.guards for w in r['contexts']),
                          proof=proof,activated=args.activate)))


if __name__=='__main__':main()
