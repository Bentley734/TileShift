"""Complete native Red Pokémon Center and Poké Mart exteriors for FRLG."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re

from PIL import Image

import catalog
import preview
from reverse_common import ROOT
from reverse_gen1_kanto_gyms import Review as OutdoorReview
from reverse_kanto_review import ground_ref
from reverse_oldale_review import mask_piece


GUARDS = Path(__file__).with_name('reverse_gen1_kanto_services_guards.json')
DONOR_MAP = 'VIRIDIAN_CITY'
DONOR_ORIGINS = {'center': (352, 352), 'mart': (448, 256)}
CENTER_BODY = [[72,73,74,75,391], [80,81,82,83,399], [88,89,90,91,407]]
MART_BODY = [[48,49,50,51], [56,57,58,59]]


class Review(OutdoorReview):
    def __init__(self, baseline):
        super().__init__(baseline)
        self.out = ROOT.parent / '.work/tileshift-reverse-gen1-kanto-services'
        self.out.mkdir(exist_ok=True)

    def contexts(self):
        found = set()
        for game in self.games:
            manifest = self.imp.table(game, 'gba/native/manifest')['layouts']
            for name, warps in sorted(self.imp.table(game, 'gba/warps').items()):
                if name not in manifest or not (name.endswith(('_CITY','_TOWN','_ISLAND')) or
                                               re.fullmatch(r'FR_ROUTE_?\d+',name)):
                    continue
                for warp in warps:
                    dest = warp.get('destMap','')
                    if dest.endswith('_POKEMON_CENTER_1F'):
                        kind, width, height = 'center', 5, 5
                    elif dest.endswith('_MART'):
                        kind, width, height = 'mart', 4, 4
                    else:
                        continue
                    x0,y0 = warp['x']-2,warp['y']-height+1
                    identity = game,name,x0,y0
                    if identity in found:
                        continue
                    found.add(identity)
                    layout = self.layout(game,name)
                    assert 0 <= x0 <= layout['width']-width and -1 <= y0
                    assert y0 != -1 or name == 'FR_SEVEN_ISLAND' and kind == 'center'
                    matrix = [None if y < 0 else layout['cells'][y][x0:x0+width]
                              for y in range(y0, y0+height)]
                    ids = [None if row is None else [cell[0] for cell in row] for row in matrix]
                    assert ids[-1][2] == 98, (game,name,kind,ids)
                    body = ids[1:-1]
                    assert body == (CENTER_BODY if kind == 'center' else MART_BODY), (game,name,kind,ids)
                    seam = self.north_roof(game, layout, name, x0, width) if y0 < 0 else None
                    yield dict(game=game,name=name,pair=layout['pair'],kind=kind,
                               x0=x0,y0=y0,width=width,matrix=matrix,warp=warp,
                               layout_hash=layout['file_sha256'],seam=seam)

    def north_roof(self, game, town, name, x0, width):
        connections = self.imp.table(game,'gba/connections')
        north, = [connection for connection in connections[name] if connection['dir']=='north']
        other = self.layout(game,north['map'])
        assert north == dict(dir='north',map='FR_SEVEN_ISLAND_TRAINER_TOWER',offset=-48)
        assert other['pair']==town['pair']
        x = x0 - north['offset']
        y = other['height'] - 1
        cells = other['cells'][y][x:x+width]
        assert [cell[0] for cell in cells]==[379,380,789,790,791]
        return dict(connection=north, x=x, y=y, cells=cells, hash=other['file_sha256'])

    def native_module(self, kind, x, y):
        ox,oy = DONOR_ORIGINS[kind]
        sx = ([0,1,1,2,3] if kind == 'center' else range(4))[x] * 16
        sy = (y if y < 3 else 3) * 16
        if kind == 'center' and y == 3:
            # The full native roof stays 32 pixels tall. Fill the new wall
            # row with two complete eight-pixel native brick courses.
            parts = self.source_piece(DONOR_MAP,ox+sx,oy+40,16,8)
            parts += self.source_piece(DONOR_MAP,ox+sx,oy+40,16,8,0,8)
        elif kind == 'center' and y == 4 and x == 1:
            parts = self.source_piece(DONOR_MAP,ox+16,oy+40,16,8)
            parts += self.source_piece(DONOR_MAP,ox+16,oy+40,16,8,0,8)
            parts += self.source_piece(DONOR_MAP,ox+15,oy+63,1,1,15,15)
        elif kind == 'mart' and y == 3:
            # Move the complete door and its feet to the actual warp. The
            # entire MART board and its legs fit on the left beside the door.
            sx = (0,32,16,48)[x]
            parts = self.source_piece(DONOR_MAP,ox+sx,oy+sy)
            if x == 1:
                parts += self.source_piece(DONOR_MAP,ox+15,oy+63,1,1,15,15)
            if x == 3:
                parts += self.source_piece(DONOR_MAP,ox+32,oy+63,1,1,0,15)
        else:
            parts = self.source_piece(DONOR_MAP,ox+sx,oy+sy)
        return self.composite(None,parts,f'gen1_native_{kind}_exterior')

    def service_art(self, context):
        kind,width,name = (context[k] for k in ('kind','width','name'))
        backing = (self.gb_ref('red','PALLET_TOWN',1,2) if name=='FR_SAFFRON_CITY'
                   else ground_ref(self,'gen1'))
        arts = {}
        height = len(context['matrix'])
        whole = Image.new('RGBA',(16*width,16*height))
        for y in range(height):
            for x in range(width):
                raw = self.native_module(kind,x,y)
                whole.paste(self.render(raw),(16*x,16*y))
                if x in (0,width-1):
                    margin = 3 if y < 2 else 1
                    mask = [(px >= margin if x==0 else px < 16-margin)
                            for py in range(16) for px in range(16)]
                    floor=backing
                    if context['seam'] and x==width-1 and y==0:
                        key=context['game'],context['pair'],113,None
                        floor=self.active[key]['donor']
                        assert floor['game']=='red'
                    arts[x,y] = mask_piece(self,raw,mask,floor,y<2)
                else:
                    arts[x,y] = dict(raw,overMask=('1' if y<2 else '0')*256)
                if y==height-1 and x==2:
                    arts[x,y]['role']='gen1_complete_native_center_and_mart_door'
        self.verify(whole,kind)
        return arts

    def verify(self, whole, kind):
        ox,oy = DONOR_ORIGINS[kind]
        donor = self.imp.gb('red',DONOR_MAP)[0]
        base = whole.height - 16
        # A complete door module plus the two one-pixel native feet.
        assert whole.crop((32,base,48,base+16)).tobytes()==donor.crop((ox+16,oy+48,ox+32,oy+64)).tobytes()
        assert whole.getpixel((31,base+15))==donor.getpixel((ox+15,oy+63))
        assert whole.getpixel((48,base+15))==donor.getpixel((ox+32,oy+63))
        sign_x = 48 if kind=='center' else 16
        assert whole.crop((sign_x,base,sign_x+16,base+15)).tobytes()==donor.crop((ox+32,oy+48,ox+48,oy+63)).tobytes()
        assert set(whole.crop((3,31,whole.width-3,32)).get_flattened_data())=={(0,0,0,255)}
        assert len(set(whole.crop((8,15,whole.width-8,16)).get_flattened_data()))>1

    def build(self):
        contexts = list(self.contexts())
        for context in contexts:
            arts = self.service_art(context)
            kind,game,pair,name,x0,y0 = (context[k] for k in ('kind','game','pair','name','x0','y0'))
            image = Image.new('RGBA',(context['width']*16,len(context['matrix'])*16))
            for y,cells in enumerate(context['matrix']):
                map_name, start_x, map_y = name, x0, y0+y
                if cells is None:
                    seam = context['seam']
                    cells = seam['cells']
                    map_name, start_x, map_y = seam['connection']['map'], seam['x'], seam['y']
                for x,(mid,_,_) in enumerate(cells):
                    key=game,pair,mid
                    assert (*key,None) not in self.active and (*key,map_name) not in self.active, key
                    row=self.row(game,pair,mid,'gen1',arts[x,y],
                                 'Complete native Red clinic or shop modules preserve the original doorway, '
                                 'window panels and sign. Native roof borders keep their 32-pixel height. '
                                 'The five-row clinic puts its extra height in intact brick courses under the roof.')
                    self.placements[key].add((map_name,start_x+x,map_y))
                    image.paste(self.render(row),(16*x,16*y))
            image.save(self.out/f'{game}-{name}-{kind}.png')
        reviewed = self.usage()
        layouts = {f'{game}/{name}': data['file_sha256'] for (game,name),data in self.layouts.items()}
        return dict(contexts=contexts,layouts=layouts,reviewed=reviewed)

    def usage(self):
        actual = defaultdict(set)
        for game in self.games:
            pairs = {pair for g,pair,_ in self.placements if g==game}
            for name,spec in self.imp.table(game,'gba/native/manifest')['layouts'].items():
                pair=spec['pair']
                if pair not in pairs:
                    continue
                for y,row in enumerate(self.layout(game,name)['cells']):
                    for x,(mid,_,_) in enumerate(row):
                        if (game,pair,mid) in self.placements:
                            actual[game,pair,mid].add((name,x,y))
        unexpected = {str(key):sorted(actual[key]-known) for key,known in self.placements.items()
                      if actual[key]-known}
        (self.out/'additional-occurrences.json').write_text(json.dumps(unexpected,indent=2)+'\n',encoding='utf-8')
        report=[]
        for key,known in sorted(self.placements.items()):
            game,pair,mid = key
            found=actual[key]
            assert known <= found
            for name,x,y in found-known:
                assert name=='FR_SAFFRON_CITY_CONNECTION' and ('FR_SAFFRON_CITY',x+10,y+7) in known, (key,name,x,y)
            row=self.rows[game,'gen1',pair,mid,None]
            cell=self.imp.cell_index(game)[pair,mid]
            donor=dict(game=game,tileset=pair,id=mid,hash=cell['pixel_sha256'])
            for layer,expected in cell['layer_sha256'].items():
                preview.native_donor(self.cache,donor,self.packed,[layer],{layer:expected})
            report.append(dict(game=game,pair=pair,mid=mid,positions=sorted(found),
                               source=cell['pixel_sha256'],behavior=cell['behavior'],layers=cell['layer_sha256'],
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
        assert proof==json.loads(GUARDS.read_text(encoding='utf-8')), 'Reviewed service building geometry changed'
    review.write(review.out/'candidate.lua')
    keys=[{key:row[key] for key in ('game','pair','mid')} for row in proof['reviewed']]
    (review.out/'keys.json').write_text(json.dumps(keys,indent=2)+'\n',encoding='utf-8')
    validation=review.validate() if args.validate else None
    print(json.dumps(dict(buildings=len(proof['contexts']),rows=len(review.rows),
                          body_cells=sum(len(r['positions']) for r in proof['reviewed']),validation=validation)))


if __name__=='__main__':
    main()
