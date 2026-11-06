"""Author exact Crystal matches for Hoenn's Gym and elevator phases."""
from pathlib import Path
import argparse
import json
import zlib

import catalog
from classic_geometry_review import art as geometry_art, source_under_frames
from coverage import active_rows
from reverse_common import ROOT, ReverseReview
from reverse_gen2_kanto_department import Review as Interior


GAMES = ('ruby','sapphire','emerald')
OUT = ROOT.parent / '.work/tileshift-rse-doors'
GUARDS = Path(__file__).with_name('reverse_gen2_rse_doors_elevators_guards.json')
ELECTRIC = 'mauville_gym_electric_gates'
VIOLET = [(58,58,58),(132,49,189),(214,99,247),(247,230,214)]


class Review(Interior):
    def __init__(self, baseline):
        ReverseReview.__init__(self,'gen2-rse-doors-elevators',GAMES)
        self.out=OUT
        self.layouts={}
        self.layout_hashes={}
        self.guards=json.loads(GUARDS.read_text(encoding='utf-8'))
        _, rows=active_rows(baseline)
        self.existing={(r['game'],r['tileset'],r['id']):r for r in rows if r['game'] in GAMES and r['style']=='gen2'}
        self.banks={}

    def electric_program(self,game,pair,mid):
        path=self.cache/game/'data/generated/gba/native'/pair
        if game not in self.banks:
            manifest=catalog.read_lua(path/'anim_manifest.lua')
            self.banks[game]=next(bank for bank in manifest['banks'] if bank['name']==ELECTRIC)
        bank=self.banks[game]
        def digest(filename,count):
            raw=(path/filename).read_bytes()
            expected=bank['frames']*count*256
            if len(raw)!=expected:
                raw=zlib.decompress(raw)
            assert len(raw)==expected
            return catalog.sha(raw)
        over=source=None
        if mid in bank.get('overMids',()):
            over=dict(bank=ELECTRIC,hash=digest(bank['overFile'],len(bank['overMids'])))
        if mid in bank.get('mids',()):
            source=dict(bank=ELECTRIC,mode='native_under',hash=digest(bank['file'],len(bank['mids'])))
        assert not (over and source)
        return over,source

    @staticmethod
    def palette_map(palette):
        levels=(83,145,207)
        def color(pixel):
            if pixel[0]>200 and pixel[1]<90 and pixel[2]>130:
                return palette[2]
            luma=(54*pixel[0]+183*pixel[1]+19*pixel[2])/256
            return palette[sum(luma>=limit for limit in levels)]
        return color

    def build_phase(self,game,pair,mid,basis,feature):
        previous=self.existing[game,pair,basis]
        spec=previous.get('classicGeometry',{})
        if feature=='petalburg_completed_room_jamb':
            spec=self.existing[game,pair,536]['classicGeometry']
        source=self.planes(game,mid)
        old=self.planes(game,basis)
        native_over=animation=None
        variant_frames,variation=[],set()
        if feature=='mauville_electric_gate_phase':
            native_over,animation=self.electric_program(game,pair,mid)
            if animation:
                variant_frames,variation,_=source_under_frames(self.cache,game,pair,mid,self.packed,animation)
        ground=None
        inherited=spec.get('ground')
        if feature=='mauville_electric_gate_phase':
            donor=inherited['donor'] if inherited else previous.get('donor')
            assert donor
            masks={}
            for layer in ('under','mid'):
                if layer not in source or layer not in old:
                    continue
                earlier=inherited['masks'].get(layer,'0'*256) if inherited else '1'*256
                mask=''.join('1' if n not in variation and bit=='1' and a==b and a[3] else '0'
                             for n,(bit,a,b) in enumerate(zip(earlier,source[layer].get_flattened_data(),old[layer].get_flattened_data())))
                if '1' in mask:
                    masks[layer]=mask
            if masks:
                ground=dict(donor=donor,masks=masks)
        else:
            assert spec and not inherited and not spec.get('nativeOver') and not spec.get('sourceAnimation')

        palette=spec.get('palette',VIOLET)
        literal={tuple(entry[:3]):entry[3:] for entry in spec.get('colorMap',())}
        used={p[:3] for layer,image in source.items() if layer!='over' or not native_over
              for p in image.get_flattened_data() if p[3]}
        used.update(p[:3] for image in variant_frames for p in image.get_flattened_data() if p[3])
        luminance=self.palette_map(palette)
        original_colors=tuple(literal)
        for pixel in sorted(used-literal.keys()):
            if original_colors:
                match=min(original_colors,key=lambda sample:sum((a-b)**2 for a,b in zip(sample,pixel)))
                literal[pixel]=literal[match]
            else:
                literal[pixel]=luminance(pixel)
        return geometry_art(self,game,pair,mid,feature,palette,literal,ground=ground,
                            native_over=native_over,source_animation=animation)

    def build(self):
        features={'native:mauville_barriers':'mauville_electric_gate_phase',
                  'native:petalburg_sliding_doors':'petalburg_sliding_door_phase',
                  'native:elevator_window_lights':'hoenn_elevator_window_light_phase',
                  'script:PETALBURG_CITY_GYM':'petalburg_completed_room_jamb'}
        for row in self.guards:
            game,pair,mid=(row[k] for k in ('game','pair','mid'))
            self.pairs={game:pair}
            source=self.imp.cell_index(game)[pair,mid]
            assert tuple(source[k] for k in ('pixel_sha256','layer_sha256','behavior'))==(
                row['sourceHash'],row['sourceLayers'],row['sourceBehavior'])
            for context in row['contexts']:
                layout=self.native_layout(game,context['map'])
                assert layout['pair']==pair and layout['mids'][context['y']*layout['width']+context['x']]==context['before_mid']
            before={c['before_mid'] for c in row['contexts']}
            assert len(before)==1,(game,pair,mid,before)
            art=self.build_phase(game,pair,mid,before.pop(),features[row['group']])
            self.row(game,pair,mid,'gen2',art,
                     'The exact reachable door, current or window phase keeps the installed source animation and the adjoining reviewed room material.')
        assert len(self.rows)==len(self.guards)==71


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path,default=ROOT)
    args=parser.parse_args()
    review=Review(args.baseline)
    review.build()
    print(review.validate())
    review.write(OUT/'candidate.lua')


if __name__=='__main__':
    main()
