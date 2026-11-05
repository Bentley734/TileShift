"""Retile Emerald's whole Dome court while retaining its original lighting program."""
from pathlib import Path
import argparse
import json

import catalog
import preview
from classic_geometry_review import art as geometry_art,source_under_frames
from reverse_common import ROOT
from reverse_gen2_hoenn_outdoor_remaining import Review as Outdoor

GAME='emerald'
PAIR='building__battle_dome'
SCENE='EM_BATTLE_FRONTIER_BATTLE_DOME_BATTLE_ROOM'
OUTPUT=ROOT.parent/'.work/tileshift-v0360-dome'
GUARDS=Path(__file__).with_name('reverse_gen2_hoenn_dome_lights_guards.json')
TARGET=ROOT/'mappings/reverse_gen2_hoenn_dome_lights.lua'
LIGHT_PHASES={(255,123,33):0,(255,156,66):1,(255,189,99):2,(255,222,132):3}


class Review(Outdoor):
    def __init__(self):
        super().__init__(OUTPUT)
        self.target_module=TARGET
        self.guards=json.loads(GUARDS.read_text(encoding='utf-8'))
        tables=self.imp.table('crystal','palettes')
        maps=self.imp.table('crystal','maps')
        self.blue=sorted(map(tuple,preview.palette_set(tables,maps['OLIVINE_CITY'],'DAY')[6]),key=self.light)
        self.stone=sorted(map(tuple,preview.palette_set(tables,maps['SAFFRON_CITY'],'DAY')[0]),key=self.light)
        timber=self.locations['emerald','gen2','building__generic_building',547,None][2]['donor']
        colors={p[:3]for p in self.gb_image(timber).get_flattened_data()if p[3]}
        palettes=timber.get('palettes')or preview.palette_set(tables,maps[timber['map']],timber.get('daytime','DAY'))
        self.timber=sorted(map(tuple,next(p for p in palettes if colors<=set(map(tuple,p)))),key=self.light)

    @staticmethod
    def light(rgb):return (54*rgb[0]+183*rgb[1]+19*rgb[2])/256

    def placement(self,mid,coords):
        if mid<=730:return 'dome_complete_stadium_seating_and_banner',self.blue
        if all(6<=x<=13 for x,y in coords):return 'dome_complete_court_field_and_lines',self.blue
        if mid in (747,748,770,771,772,796,797,819,820,821):return 'dome_full_platform_stair_treads',self.stone
        return 'dome_complete_lighted_platform_and_perimeter',self.timber

    def build(self):
        layout=self.native_layout(GAME,SCENE);width=layout['width'];assert layout['pair']==PAIR
        for item in self.guards:
            mid=item['mid'];source=self.imp.cell_index(GAME)[PAIR,mid]
            assert source['pixel_sha256']==item['sourceHash'] and source['layer_sha256']==item['sourceLayers']
            assert source['behavior']==item['sourceBehavior']
            assert (GAME,'gen2',PAIR,mid,None)not in self.occupied
            coords=[(i%width,i//width)for i,n in enumerate(layout['mids'])if n==mid]
            assert coords==[tuple(p)for p in item['coords']]
            feature,palette=self.placement(mid,coords)
            ref=dict(game=GAME,tileset=PAIR,id=mid,hash=source['pixel_sha256'])
            preview.native_donor(self.cache,ref,self.packed)
            mids,colors,planes=self.packed[GAME,PAIR];offset=mids.index(mid)*256
            images=[catalog.rgba_native(blob[offset:offset+256],colors,name!='under')for name,blob in planes.items()]
            animation=item['sourceAnimation']
            frames,changed,_=source_under_frames(self.cache,GAME,PAIR,mid,self.packed,animation)
            images.extend(frames)
            source_colors={p[:3]for image in images for p in image.get_flattened_data()if p[3]}
            color_map={rgb:palette[LIGHT_PHASES.get(rgb,sum(self.light(rgb)>=cut for cut in (85,151,214)))]for rgb in source_colors}
            art=geometry_art(self,GAME,PAIR,mid,feature,palette,color_map,source_animation=animation)
            row=self.row(GAME,PAIR,mid,'gen2',art,
                'The complete Dome seating, banner, court, steps or platform follows its exact source geometry. '
                'Its native lighting phases keep their own timing, with each changing source shade using a distinct Crystal material color. '
                'Source priority, battle layout, collision and entrances are preserved.')
            if changed:
                themed=preview.classic_geometry_frames(self.cache,row,self.packed)
                assert len({frame.tobytes()for frame in themed})==4,('Dome light phase lost contrast',mid)
            row['domeLightReview']=dict(source_binding=catalog.sha(json.dumps(item,sort_keys=True,separators=(',',':')).encode()),pixel_scale=1)
        assert len(self.rows)==94

    def preview_scene(self):
        image,cells,_,_=self.imp.gba(GAME,SCENE)
        shared={(r['game'],r['style'],r['tileset'],r['id'],r.get('map')):r
                for r in preview.read_reviewed(ROOT/'mappings/reverse_gen2_hoenn_interiors_completion.lua')
                if r['tileset']==PAIR and r['style']=='gen2'}
        assert not set(shared)&set(self.rows)
        for cell in cells:
            key=GAME,'gen2',PAIR,cell['id'],None
            row=self.rows.get(key)or shared.get(key)
            if row is None and key in self.locations:row=self.locations[key][2]
            assert row,('Dome room has an untouched native cell',key)
            piece=self.render(row)
            for x,y in cell['coordinates']:image.paste(piece,(x*16,y*16))
        image.save(OUTPUT/'battle-dome-review.png')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate',action='store_true')
    args=parser.parse_args()
    review=Review();review.build();review.preview_scene();proof=review.validate()
    review.write(OUTPUT/'candidate.lua')
    if args.activate:review.write(TARGET)
    print(json.dumps(dict(rows=len(review.rows),body_cells=sum(len(r['coords'])for r in review.guards),proof=proof,activated=args.activate)))


if __name__=='__main__':main()
