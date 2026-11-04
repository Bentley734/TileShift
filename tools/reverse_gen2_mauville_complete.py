"""Review complete native-size Crystal counterparts for Mauville City only.

The authoring inventory reads actual logical SVML map bodies. Every recipe is
bound to the source cartridge's full RGBA picture and behavior. Existing recipes
and all source maps, events, collision and entrances remain unchanged.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import struct
import zlib
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import catalog
import preview
import reverse_common
from interior_review import Imports
from reverse_common import ROOT
from reverse_gen2_hoenn_city_complete import Review as CityReview
from reverse_hoenn_review import ground_ref
from reverse_kanto_review import exterior, runs
from reverse_oldale_review import mask_piece

TARGET = ROOT / 'mappings/reverse_gen2_mauville_complete.lua'
GAMES = ('ruby', 'sapphire', 'emerald')
PREFIXES = dict(ruby='RU_', sapphire='SA_', emerald='EM_')
EXPECTED_LAYOUT_SHA256 = 'db60bf6b68fea4c595ce4afc2c4b244ce00141210a6ff3e7948a241189fbf07b'
EXPECTED_SOURCE_CONTRACT_SHA256 = 'e5e1a444bd9c85fb3f947a12358069e724caaa213d74b7c3c3e664aa3478b7d1'
EXPECTED_COMPACT_BICYCLE_RGBA_SHA256 = '0722675b8255373cb0ff2c9cb7bef3bc57e9eb5eb0b5286ce3b4f9853180de67'


class Review(CityReview):
    def __init__(self, cache):
        self.name = 'v0340-mauville'
        self.games = GAMES
        self.cache = Path(cache)
        reverse_common.CACHE = self.cache
        self.out = ROOT.parent / '.work/tileshift-v0340-mauville'
        self.out.mkdir(parents=True, exist_ok=True)
        self.imp = Imports(self.cache, ROOT.parent / '.work/tileshift-catalog')
        self.packed = self.imp.packed
        self.rows, self._gb, self._refs = {}, {}, {}
        self.prior, self.contracts = {}, []
        self.counts, self.contexts = Counter(), defaultdict(list)
        self.groups = []
        modules = dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]", (ROOT / 'main.lua').read_text()))
        for module in modules:
            if ROOT / module == TARGET:
                continue
            for row in preview.read_reviewed(ROOT / module):
                if row['game'] in GAMES and row['style'] == 'gen2':
                    key = row['game'], row['tileset'], row['id']
                    assert key not in self.prior
                    self.prior[key] = row

    def layout(self, game):
        name = PREFIXES[game] + 'MAUVILLE_CITY'
        spec = self.imp.table(game, 'gba/native/manifest')['layouts'][name]
        raw = (self.cache / game / 'data/generated/gba/native' / spec['file']).read_bytes()
        body = raw if raw[:4] == b'SVML' else zlib.decompress(raw)
        pw, ph, width, height = struct.unpack_from('<HHHH', body, 6)
        width, height = width or pw, height or ph
        start = 16 + body[14] * body[15] * 2
        matrix = [[struct.unpack_from('<H', body, start + 4 * (y * pw + x))[0]
                   for x in range(width)] for y in range(height)]
        assert (width, height) == (40, 20)
        assert catalog.sha(raw) == EXPECTED_LAYOUT_SHA256, ('Reviewed Mauville source layout changed', game)
        return name, spec['pair'], matrix, catalog.sha(raw)

    def inventory(self):
        records = []
        for game in GAMES:
            name, pair, matrix, fingerprint = self.layout(game)
            missing = defaultdict(list)
            for y, line in enumerate(matrix):
                for x, mid in enumerate(line):
                    if (game, pair, mid) not in self.prior:
                        missing[mid].append([x, y])
            source, _, _, _ = self.imp.gba(game, name)
            source.save(self.out / (game + '-source.png'))
            grid = source.resize((source.width * 2, source.height * 2), Image.Resampling.NEAREST)
            draw = ImageDraw.Draw(grid)
            font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 10)
            for mid, coords in missing.items():
                for x, y in coords:
                    draw.rectangle((x * 32, y * 32, x * 32 + 31, y * 32 + 31), outline='red')
                    draw.text((x * 32, y * 32), str(mid), fill='red', font=font, stroke_width=1, stroke_fill='white')
            grid.save(self.out / (game + '-missing-grid.png'))
            contacts = Image.new('RGB', (128 * 10, 112 * ((len(missing) + 9) // 10)), '#18212b')
            draw = ImageDraw.Draw(contacts)
            for i, (mid, coords) in enumerate(sorted(missing.items())):
                x, y = (i % 10) * 128, (i // 10) * 112
                draw.text((x + 2, y + 2), f'{mid} x{len(coords)}', fill='white', font=font)
                contacts.paste(self.source((game, pair, mid)).resize((64, 64), Image.Resampling.NEAREST), (x + 2, y + 22))
            contacts.save(self.out / (game + '-missing-contacts.png'))
            records.append(dict(game=game, map=name, pair=pair, layout_sha256=fingerprint,
                                source_cells=sum(map(len, matrix)), missing_cells=sum(map(len, missing.values())),
                                missing=[dict(id=mid, coordinates=coords) for mid, coords in sorted(missing.items())]))
        (self.out / 'inventory.json').write_text(json.dumps(records, indent=2) + '\n')
        return records

    def new(self, game, mid, art, evidence):
        pair = 'general__mauville'
        assert (game, pair, mid) not in self.prior
        return self.row(game, pair, mid, 'gen2', art, evidence)

    def barriers(self):
        # This is an explicit source review of each connected low barrier,
        # not a color match or a numeric alias to other cartridges.
        shapes = {313: 320, 627: 77, 640: 61, 642: 63, 648: 69,
                  650: 71, 656: 77, 657: 78, 658: 79, 689: 77,
                  690: 79, 698: 61}
        for game in GAMES:
            for mid, donor_mid in shapes.items():
                art = copy.deepcopy(self.prior[game, 'general__mauville', donor_mid])
                art = {k: v for k, v in art.items() if k in
                       ('kind', 'donor', 'base', 'parts', 'overMask', 'role')}
                art['role'] = 'reverse_gen2_mauville_connected_low_barrier'
                self.new(game, mid, art,
                    'Individually reviewed Mauville low garden barrier in all three original city maps: '
                    '640/642 are upper left/right turns,648/650 vertical sides,656/658 and689/690 lower turns, '
                    '657 the lower horizontal span,698 a north-left endpoint,627 the west/eastward junction, '
                    'and313 the separate gray road-edge vertical curb. The same handed complete original '
                    'Crystal Saffron low-curb counterpart already used for this city preserves every native '
                    '8px bar and rounded post; source wooden posts become the coherent low Gen2 barrier. '
                    'Original walking openings, source collision, layouts, source events and actor coordinates '
                    'remain unchanged. Each cartridge source has its own full RGBA and behavior fingerprint.')
        self.contracts.append(dict(kind='connected_garden_barriers', source_to_existing_native_shape=shapes,
                                   native_complete_8px_modules=True, native_pixel_scale=1))

    def bicycles(self):
        # The Bike Shop has an intact compact frontal display as well as its
        # wider side-on bicycle. The compact native object preserves all eight
        # bicycles in the two racks without shrinking the wider counterpart.
        ref = self.gb_at('crystal', 'GOLDENROD_BIKE_SHOP', 2, 1)
        source = self.gb_image(ref)
        assert catalog.sha(source.tobytes()) == EXPECTED_COMPACT_BICYCLE_RGBA_SHA256
        # Whole native object contour, independently bounded against the
        # adjacent empty checker/floor tile in the actual original Bike Shop.
        # The original spokes and light enclosed frame highlights remain.
        bounds = [(3,13),(2,14),(3,13),(2,14),(1,13),(2,8),(7,11),(6,12),
                  (5,13),(4,12),(2,12),(2,12),(2,11),(3,11),(6,11),(7,11)]
        mask = [bounds[y][0] <= x <= bounds[y][1] for y in range(16) for x in range(16)]
        field = ground_ref(self, 'gen2')
        pieces = {i: [] for i in range(3)}
        glyph = Image.new('RGBA', (16,16))
        glyph.putdata([source.getpixel((x,y)) if mask[y*16+x] else (0,0,0,0)
                       for y in range(16) for x in range(16)])
        for offset in (4, 28):
            for run in runs(mask):
                left, top, width, height = run['x'], run['y'], run['w'], run['h']
                for cell_x in range((offset+left)//16, (offset+left+width-1)//16+1):
                    a, b = max(offset+left, cell_x*16), min(offset+left+width, (cell_x+1)*16)
                    pieces[cell_x].append(dict(donor=copy.deepcopy(ref), srcX=a-offset, srcY=top,
                                               w=b-a, h=height, x=a-cell_x*16, y=top))
        arts = {i: self.composite(field, parts, 'reverse_gen2_mauville_complete_native_bicycles')
                for i, parts in pieces.items()}
        model = Image.new('RGBA', (48,16))
        for i, art in arts.items():
            assert len(art['parts']) <= 32
            art['overMask'] = '0'*256
            model.paste(self.render(art), (i*16,0))
        expected = Image.new('RGBA',(48,16))
        for x in range(0,48,16): expected.paste(self.gb_image(field),(x,0))
        expected.alpha_composite(glyph,(4,0));expected.alpha_composite(glyph,(28,0))
        assert model.tobytes() == expected.tobytes()
        source.resize((256,256),Image.Resampling.NEAREST).save(self.out/'compact-bicycle-native-source16.png')
        glyph.resize((256,256),Image.Resampling.NEAREST).save(self.out/'compact-bicycle-retained-contour16.png')
        model.resize((768,256),Image.Resampling.NEAREST).save(self.out/'two-complete-native-bicycles48.png')
        for game in GAMES:
            for i, mid in enumerate((664,665,666)):
                self.new(game, mid, arts[i],
                    'The actual Mauville bicycle racks have two complete bicycles in each48x16 row, '
                    'two rows in each rack and two racks, eight bicycles total. Two intact compact '
                    'original Crystal Goldenrod Bike Shop frontal16px bicycle glyphs occupy each row '
                    'at original1:1 pixels, centered at offsets4 and28. The wider32px side-on bicycle '
                    'is not shrunk or substituted for a pair. A separately reviewed native contour '
                    'removes only the original shop wall/floor backdrop; native spokes, tire, frame '
                    'and enclosed highlights retain their exact original pixels. Matching selected '
                    'Crystal lawn shows between the bikes. All eight source blocked positions and '
                    'original map/events, collision and actor positions remain unchanged.')
        self.contracts.append(dict(kind='eight_complete_native_bicycles', native_reference=ref,
                                   complete_native_glyph_dimensions=[16,16], pixel_scale=1,
                                   native_retained_contour=bounds, row_object_offsets=[4,28],
                                   source_row=[664,665,666], source_rack_rows=2, source_racks=2,
                                   source_and_replacement_bicycles=8,
                                   composed_pixel_sha256=catalog.sha(model.tobytes())))

    def east_house(self):
        house = [[643,644,644,644,645], [651,652,652,652,653],
                 [672,676,673,675,674], [680,684,681,683,682]]
        self.bind_building('MAUVILLE_CITY', 'MAUVILLE_CITY_HOUSE1', (31,11), house,
                          self.town_model(5,2,1,(3,)),
                          'Whole Mauville eastern house keeps its complete80x64 facade, native-size '
                          'doorway and full16x8 Crystal window pair at the original window position. '
                          'Original complete New Bark wooden roof/side/window/door modules remain1:1; '
                          'only ordinary middle roof and wall modules repeat. The differently designed '
                          'R/S and Emerald fronts are reviewed independently, preserving their original '
                          'entrance and all existing released roof/door recipes.')
        annex = [[638,679,679,639], [646,687,687,647], [654,695,695,655],
                 [662,678,678,663], [670,668,668,671]]
        self.bind_building('MAUVILLE_CITY', None, (36,11), annex,
                          self.town_model(4,3,-1,(1,2),True),
                          'Whole64x80 eastern Mauville house annex retains its complete tall roof '
                          'and both original window positions without adding an entrance. Complete '
                          'original Crystal Saffron gray roof caps and native brick side/base modules '
                          'remain1:1; one ordinary8px middle roof band repeats to retain the full48px '
                          'source roof height. Each source window receives one whole original16x8 '
                          'Crystal window pair, never half a frame or a downscaled bitmap. Only '
                          'genuine exterior roof corners expose the selected lawn.', [])

    def game_corner(self):
        field = ground_ref(self,'gen2')
        arts = {}
        # Complete native Goldenrod brick/roof modules, complete16x8 windows
        # and the original complete16px doorway retain their original pixels.
        plain = self.gb_rect('crystal','GOLDENROD_CITY',224,320,16,16)
        for y in range(4):
            for x in range(7):
                if y < 2:
                    sx = 0 if x == 0 else 80 if x == 6 else 16
                    parts = self.gb_rect('crystal','GOLDENROD_CITY',192+sx,288+y*16,16,16)
                elif y == 2:
                    parts = copy.deepcopy(plain)
                    if x in (0,6):
                        parts += self.gb_rect('crystal','GOLDENROD_CITY',192 if x==0 else 280,320,8,16,0 if x==0 else 8)
                    if x in (1,5):
                        parts += self.gb_rect('crystal','GOLDENROD_CITY',200,328,16,8,0,8)
                else:
                    sx = 0 if x == 0 else 80 if x == 6 else 32 if x == 3 else 48
                    parts = self.gb_rect('crystal','GOLDENROD_CITY',192+sx,336,16,16)
                arts[x,y] = self.composite(None,parts,'reverse_gen2_mauville_complete_native_game_corner')
        model=Image.new('RGBA',(112,64))
        for (x,y),art in arts.items():model.paste(self.render(art),(x*16,y*16))
        outside=exterior(model,{(222,255,222,255)})
        for (x,y),art in list(arts.items()):
            mask=[(x*16+px,y*16+py)not in outside for py in range(16)for px in range(16)]
            arts[x,y]=mask_piece(self,art,mask,field,y<2)
        matrix=[[728,729,729,729,729,729,732], [736,737,737,737,737,737,740],
                [744,731,745,746,747,731,748], [721,739,722,723,730,739,738]]
        self.bind_building('MAUVILLE_CITY','MAUVILLE_CITY_GAME_CORNER',(5,10),matrix,arts,
                          'Whole Mauville Game Corner keeps its complete112x64 main facade, original '
                          'central entrance and both full window pairs. The actual native Crystal '
                          'Goldenrod Game Corner supplies complete roof end caps, original brick '
                          'wall/side/base modules, entire16px doorway and full16x8 window pair; only '
                          'plain native roof/brick repeats widen the building. No unique pane, frame, '
                          'roof edge or doorway is cut or resized. The source decorative front-post '
                          'bases below the compact native facade retain their walking cells with '
                          'matching selected lawn; no collision or source event changes.')
        for game in GAMES:
            for mid in (800,801):
                art=self.native(field,'reverse_gen2_mauville_gamecorner_native_lawn_below_facade')
                art['overMask']='0'*256
                self.new(game,mid,art,'The source decorative Game Corner post foot is below the '
                         'complete native Crystal facade, outside its complete roof/window/door '
                         'assembly. Matching native Crystal lawn clears this obsolete extra foot '
                         'without cutting any native building pixel or changing source collision, '
                         'entrances, layout, actors or events.')

    def build(self):
        self.barriers(); self.bicycles(); self.east_house(); self.game_corner()
        source_contracts=sorted([[row['game'],row['tileset'],row['id'],row['sourceHash'],row.get('sourceBehavior')]
                                 for row in self.rows.values()])
        digest=catalog.sha(json.dumps(source_contracts,sort_keys=True,separators=(',',':')).encode())
        assert digest==EXPECTED_SOURCE_CONTRACT_SHA256, 'Reviewed Mauville source pixels/behaviors changed'
        (self.out/'source-contracts.json').write_text(json.dumps(dict(sha256=digest,contracts=source_contracts),indent=2)+'\n')
        covered=[]
        for game in GAMES:
            name, pair, matrix, _ = self.layout(game)
            missing=[mid for row in matrix for mid in row
                     if (game,pair,mid)not in self.prior
                     and (game,'gen2',pair,mid,None)not in self.rows]
            assert not missing, (game,missing)
            covered.append(self.preview_map(game,name))
        (self.out/'coverage.json').write_text(json.dumps(covered,indent=2)+'\n')
        def ordered(value):
            if isinstance(value,dict):return {k:ordered(value[k])for k in sorted(value,key=str)}
            if isinstance(value,list):return [ordered(v)for v in value]
            return value
        self.rows={k:ordered(self.rows[k])for k in sorted(self.rows)}
        self.write(self.out/'candidates.lua')
        (self.out/'contracts.json').write_text(json.dumps(self.contracts,indent=2)+'\n')
        changed=set((row['game'],row['tileset'],row['id'])for row in self.rows.values())
        affected=[]
        for game in GAMES:
            for name,spec in self.imp.table(game,'gba/native/manifest')['layouts'].items():
                if spec['pair']!='general__mauville':continue
                raw=(self.cache/game/'data/generated/gba/native'/spec['file']).read_bytes()
                body=raw if raw[:4]==b'SVML'else zlib.decompress(raw)
                pw,ph,w,h=struct.unpack_from('<HHHH',body,6);w,h=w or pw,h or ph;start=16+body[14]*body[15]*2
                occurrences=Counter(struct.unpack_from('<H',body,start+4*(y*pw+x))[0]
                                    for y in range(h)for x in range(w))
                used={mid:n for mid,n in occurrences.items()if (game,spec['pair'],mid)in changed}
                if used:affected.append(dict(game=game,map=name,pair=spec['pair'],changed_occurrences=sum(used.values()),source_keys=used))
        (self.out/'affected-maps.json').write_text(json.dumps(affected,indent=2)+'\n')
        return covered


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=reverse_common.CACHE)
    parser.add_argument('--validate', action='store_true')
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    assert not args.activate or args.validate
    review = Review(args.cache)
    report = review.inventory()
    coverage = review.build()
    validation = review.validate() if args.validate else None
    if args.activate:
        review.write(TARGET)
    print(json.dumps(dict(rows=len(review.rows), coverage=coverage, validation=validation)))


if __name__ == '__main__':
    main()
