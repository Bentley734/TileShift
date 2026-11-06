"""Native Red outdoor Gyms and signs for FireRed and LeafGreen."""

import argparse
from collections import defaultdict
import json
from pathlib import Path

from PIL import Image

import catalog
from coverage import active_rows
import preview
from reverse_classic_gyms_finish import Review as GymLayoutReview
from reverse_common import ROOT, ReverseReview
from reverse_kanto_review import exterior, ground_ref, runs
from reverse_oldale_review import mask_piece


GAMES = ('firered', 'leafgreen')
TOWNS = ('CELADON_CITY', 'CERULEAN_CITY', 'CINNABAR_ISLAND', 'FUCHSIA_CITY',
         'PEWTER_CITY', 'SAFFRON_CITY', 'VERMILION_CITY', 'VIRIDIAN_CITY')
TARGET = ROOT / 'mappings/reverse_gen1_kanto_gyms.lua'
GUARDS = Path(__file__).with_name('reverse_gen1_kanto_gyms_guards.json')
ROOF_MAP, ROOF_X, ROOF_Y = 'SAFFRON_CITY', 256, 160
GYM_MAP, GYM_X, GYM_Y = 'VIRIDIAN_CITY', 448, 64
LAWN_IDS = {'CELADON_CITY': 8, 'CINNABAR_ISLAND': 9, 'VERMILION_CITY': 8,
            'VIRIDIAN_CITY': 8}


class Review(ReverseReview):
    layout = GymLayoutReview.layout

    def __init__(self, baseline):
        super().__init__('gen1-kanto-gyms', GAMES)
        self.layouts = {}
        _, rows = active_rows(baseline)
        self.active = {(r['game'], r['tileset'], r['id'], r.get('map')): r for r in rows
                       if r['game'] in GAMES and r['style'] == 'gen1'}
        self.placements = defaultdict(set)

    def contexts(self):
        for game in GAMES:
            for town in TOWNS:
                name = 'FR_' + town
                layout = self.layout(game, name)
                entrance, = [warp for warp in layout['warps'] if 'GYM' in warp['destMap']]
                x0, y0 = entrance['x'] - 3, entrance['y'] - 4
                assert x0 >= 0 and y0 >= 0
                markers = layout['cells'][y0+1]
                assert markers[x0][0] == 321
                right = x0 + 1
                while markers[right][0] == 322:
                    right += 1
                assert markers[right][0] == 323
                width = right - x0 + 1
                assert 6 <= width <= 8 and layout['cells'][y0+4][entrance['x']][0] == 347
                roof = [row[x0:right+1] for row in layout['cells'][y0:y0+5]]
                upper, lower = (772, 780) if town == 'SAFFRON_CITY' else (352, 360)
                signs = [(x, y, cell) for y, row in enumerate(layout['cells'])
                         for x, cell in enumerate(row) if cell[0] in (upper, lower)]
                assert any(cell[0] == lower for _, _, cell in signs)
                yield dict(game=game, name=name, town=town, pair=layout['pair'], x0=x0, y0=y0,
                           width=width, matrix=roof, signs=signs, upper=upper,
                           warp=entrance, layout_hash=layout['file_sha256'])

    def source_piece(self, name, x, y, w=16, h=16, dx=0, dy=0):
        return self.gb_rect('red', name, x, y, w, h, dx, dy)

    def rectangular_roof(self, width, x, y):
        sx = 0 if x == 0 else 112 if x == width - 1 else 16
        sy = (0, 8, 16)[y]
        parts = self.source_piece(ROOF_MAP, ROOF_X + sx, ROOF_Y + sy)
        return self.composite(None, parts, 'gen1_complete_rectangular_gym_roof')

    def facade(self, width, x, y):
        edge = x in (0, width-1)
        if y == 3:
            sx = (0 if x == 0 else 80) if edge else min(x, 4) * 16
            if edge:
                parts = (self.source_piece(GYM_MAP, GYM_X+sx, GYM_Y+40, 16, 8) +
                         self.source_piece(GYM_MAP, GYM_X+sx, GYM_Y+40, 16, 8, 0, 8))
            else:
                parts = self.source_piece(GYM_MAP, GYM_X+sx, GYM_Y+32)
            return self.composite(None, parts, 'gen1_complete_gym_upper_facade')
        # The original door is in column four. The FRLG warp is in column
        # three. Move the full door module and swap the complete pane left
        # of it into the new right window bank. Repeat only that bank.
        sx = 80 if x == width-1 else 64 if x == 3 else 48 if x >= 4 else x*16
        parts = self.source_piece(GYM_MAP, GYM_X+sx, GYM_Y+48)
        return self.composite(None, parts, 'gen1_complete_gym_lower_facade')

    def backing(self, context, sign=False):
        town = context['town']
        if town in LAWN_IDS:
            ref = self.active[context['game'], context['pair'], LAWN_IDS[town], None]['donor']
            assert ref['game'] == 'red'
            return ref
        if sign and town == 'FUCHSIA_CITY':
            return ground_ref(self, 'gen1')
        return self.gb_ref('red', 'PALLET_TOWN', 1, 2)

    def gym_art(self, context):
        width = context['width']
        arts = {}
        whole = Image.new('RGBA', (width*16, 80))
        backing = self.backing(context)
        for y in range(5):
            roof = y < 3
            for x in range(width):
                edge = x in (0,width-1)
                art = self.rectangular_roof(width, x, y) if roof else self.facade(width, x, y)
                whole.paste(self.render(art), (16*x,16*y))
                if edge:
                    margin = 3 if roof else 1
                    mask = [(px >= margin if x == 0 else px < 16-margin)
                            for py in range(16) for px in range(16)]
                    arts[x,y] = mask_piece(self, art, mask, backing, roof)
                else:
                    arts[x,y] = dict(art, overMask=('1' if roof else '0')*256)
        self.verify_facade(whole, width)
        return arts

    def verify_facade(self, whole, width):
        original = self.imp.gb('red', GYM_MAP)[0]
        assert whole.crop((16,48,80,56)).tobytes() == original.crop((GYM_X+16,GYM_Y+32,GYM_X+80,GYM_Y+40)).tobytes()
        assert whole.crop((48,64,64,80)).tobytes() == original.crop((GYM_X+64,GYM_Y+48,GYM_X+80,GYM_Y+64)).tobytes()
        pane = original.crop((GYM_X+48,GYM_Y+48,GYM_X+64,GYM_Y+64)).tobytes()
        cap = original.crop((GYM_X+80,GYM_Y+48,GYM_X+96,GYM_Y+64)).tobytes()
        windows = [whole.crop((x*16,64,(x+1)*16,80)).tobytes() for x in range(4,width)]
        assert windows[-1] == cap and windows.count(cap) == 1
        assert all(tile == pane for tile in windows[:-1])
        assert set(whole.crop((3,47,width*16-3,48)).get_flattened_data()) == {(0,0,0,255)}

    def sign(self, context, top):
        ground = self.backing(context, sign=True)
        if top:
            return dict(self.native(ground, 'gen1_clear_unused_gym_badge_extension'), overMask='0'*256)
        ref = self.gb_at('red', GYM_MAP, 27, 7)
        image = self.gb_image(ref)
        outside = exterior(image, {(255,255,255,255)})
        shape = [(x,y) not in outside for y in range(16) for x in range(16)]
        parts = [dict(part, donor=ref, srcX=part['x'], srcY=part['y']) for part in runs(shape)]
        return dict(self.composite(ground, parts, 'gen1_complete_original_outdoor_gym_sign'),
                    overMask='0'*256)

    def emit(self, context, mid, art, x, y):
        game, pair, name = (context[k] for k in ('game','pair','name'))
        key = game, pair, mid
        assert (*key, None) not in self.active and (*key, name) not in self.active, key
        row = self.row(game, pair, mid, 'gen1', art,
                       'Native Red Gym artwork at its original pixel scale. The whole entrance, lettering and '
                       'window modules stay intact. The complete flat shingle roof and lower edge align across the '
                       'entrance. The outdoor sign uses its original Red frame and feet. Source warp and map data are retained.')
        self.placements[key].add((name, x, y))
        return row

    def build(self):
        contexts = list(self.contexts())
        assert len(contexts) == 16
        for context in contexts:
            arts = self.gym_art(context)
            x0,y0 = context['x0'],context['y0']
            source = Image.new('RGBA',(context['width']*16,80))
            output = source.copy()
            for y,cells in enumerate(context['matrix']):
                for x,(mid,_,_) in enumerate(cells):
                    row = self.emit(context, mid, arts[x,y], x0+x, y0+y)
                    donor = dict(game=row['game'],tileset=row['tileset'],id=mid,hash=row['sourceHash'])
                    source.paste(preview.native_donor(self.cache, donor, self.packed), (x*16,y*16))
                    output.paste(self.render(row), (x*16,y*16))
            for x,y,(mid,_,_) in context['signs']:
                self.emit(context, mid, self.sign(context,mid == context['upper']), x, y)
            stem=f"{context['game']}-{context['name']}"
            source.save(self.out/f'{stem}-source.png')
            output.save(self.out/f'{stem}-candidate.png')
        reviewed = self.usage()
        layout_hashes = {f'{game}/{name}': data['file_sha256'] for (game,name),data in self.layouts.items()}
        return dict(contexts=contexts, layouts=layout_hashes, reviewed=reviewed)

    def usage(self):
        actual = defaultdict(set)
        for game in GAMES:
            pairs = {pair for g,pair,_ in self.placements if g==game}
            for name,spec in self.imp.table(game, 'gba/native/manifest')['layouts'].items():
                pair=spec['pair']
                if pair not in pairs:
                    continue
                layout = self.layout(game,name)
                for y, cells in enumerate(layout['cells']):
                    for x, (mid,_,_) in enumerate(cells):
                        if (game,pair,mid) in self.placements:
                            actual[game,pair,mid].add((name,x,y))
        report = []
        for key, wanted in sorted(self.placements.items()):
            game,pair,mid = key
            found = actual[key]
            assert wanted <= found
            for name,x,y in found-wanted:
                duplicate_city = name == 'FR_SAFFRON_CITY_CONNECTION' and pair in (
                    'general__rom_082d4b9c','general__rom_082d4b7c')
                other_door = (name,x,y) in (('FR_CELADON_CITY',39,20),('FR_CELADON_CITY',34,21)) or name=='FR_ROUTE_22'
                assert duplicate_city or (mid==347 and other_door), (key,name,x,y)
            row = self.rows[game,'gen1',pair,mid,None]
            cell = self.imp.cell_index(game)[pair,mid]
            donor=dict(game=game,tileset=pair,id=mid,hash=cell['pixel_sha256'])
            for layer,expected in cell['layer_sha256'].items():
                preview.native_donor(self.cache,donor,self.packed,[layer],{layer:expected})
            report.append(dict(game=game,pair=pair,mid=mid,positions=[list(p) for p in sorted(found)],
                               source=cell['pixel_sha256'],behavior=cell['behavior'],layers=cell['layer_sha256'],
                               output=row['compositionPixelHash'],over_mask=row['overMask']))
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, default=ROOT)
    parser.add_argument('--freeze', action='store_true')
    parser.add_argument('--validate', action='store_true')
    args = parser.parse_args()
    review = Review(args.baseline.resolve())
    proof = json.loads(json.dumps(review.build()))
    if args.freeze:
        GUARDS.write_text(json.dumps(proof, indent=2)+'\n', encoding='utf-8')
    else:
        assert proof == json.loads(GUARDS.read_text(encoding='utf-8')), 'Reviewed gym geometry changed'
    review.write(review.out/'candidate.lua')
    keys = [{key: row[key] for key in ('game','pair','mid')} for row in proof['reviewed']]
    (review.out/'keys.json').write_text(json.dumps(keys,indent=2)+'\n',encoding='utf-8')
    validation = review.validate() if args.validate else None
    print(json.dumps(dict(rows=len(review.rows), body_cells=sum(len(row['positions']) for row in proof['reviewed']),
                          validation=validation)))


if __name__ == '__main__':
    main()
