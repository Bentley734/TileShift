"""Review native-scale Crystal counterparts for the complete Fallarbor Town."""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import json
import re
import struct
import zlib

from PIL import Image, ImageDraw, ImageFont

import catalog
import preview
from reverse_common import ROOT, ReverseReview
from reverse_gen2_hoenn_city_complete import Review as CityReview
from reverse_gen2_hoenn_outdoor_finish import Review as OutdoorReview
from johto_remaining_review import artwork
from reverse_kanto_review import exterior, runs
from reverse_oldale_review import native_piece, mask_piece

GAMES = ('ruby', 'sapphire', 'emerald')
PAIR = 'general__fallarbor'
TARGET = ROOT / 'mappings/reverse_gen2_fallarbor_complete.lua'
SOURCE_BINDING = 'e5e37c6c056e586f5e7e64006627f23f8df83d77a7b8f733055277c206e9105e'
MISSING_BINDING = '9d2a169bd302b4cc7eaf27346319b92227094c7375f67b740c9b25b95e0e6e90'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class Review(CityReview):
    def __init__(self):
        ReverseReview.__init__(self, 'gen2-fallarbor-complete', GAMES)
        self.out = ROOT.parent / '.work/tileshift-v0350-fallarbor'
        self.out.mkdir(parents=True, exist_ok=True)
        self.prior, self.contracts, self.proofs = {}, [], {}
        select = catalog.LUA.eval('function(rows)local out={} for _,r in ipairs(rows)do if r.style=="gen2" and r.tileset=="general__fallarbor" then out[#out+1]=r end end return out end')
        modules = dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]", (ROOT / 'main.lua').read_text()))
        for module in modules:
            if ROOT / module == TARGET:
                continue
            selected = catalog.plain(select(catalog.LUA.execute((ROOT / module).read_text(encoding='utf-8-sig'))))
            for row in selected if isinstance(selected, list) else []:
                key = row['game'], row['tileset'], row['id']
                assert key not in self.prior
                self.prior[key] = row

    raw_ref = OutdoorReview.raw_ref
    classic_cliff = OutdoorReview.classic_cliff
    park_tree_art = OutdoorReview.park_tree_art

    def emit_for(self, game, mid, art, role, reason):
        assert mid in self.missing[game] and (game, PAIR, mid) not in self.prior
        art = copy.deepcopy(art)
        art['role'] = 'reverse_gen2_fallarbor_' + role
        art.setdefault('overMask', '0' * 256)
        return self.row(game, PAIR, mid, 'gen2', art, reason +
                        ' Literal frozen source RGBA, every under/mid/over layer, behavior, full logical layout/collision/elevation and all original warps are checked independently for each cartridge. Source map, collisions, encounters, scripts, actors and entrance interactions stay unchanged. All original native Crystal object and module pixels retain 1:1 scale.')

    def emit(self, mid, art, role, reason):
        for game in GAMES:
            self.emit_for(game, mid, art, role, reason)

    def check_sources(self):
        records = self.source_binding()
        assert digest(records) == SOURCE_BINDING, 'Fallarbor source art/layers/behavior/layout/warps changed; re-review required'
        self.missing = {}
        for record in records:
            layout = record['layout']; game = layout['game']
            self.missing[game] = sorted({cell[0] for row in layout['cells'] for cell in row
                                         if (game, PAIR, cell[0]) not in self.prior})
            for cell in record['cells']:
                assert catalog.sha(self.source((game, PAIR, cell['id'])).tobytes()) == cell['rgba_sha256']
                reference = dict(game=game, tileset=PAIR, id=cell['id'], hash=cell['rgba_sha256'])
                for layer, expected in cell['layer_sha256'].items():
                    preview.native_donor(self.cache, reference, self.packed, [layer], {layer: expected})
        assert digest(self.missing) == MISSING_BINDING, 'Existing Fallarbor reviewed keys changed; review before integrating'
        self.proofs['literal_source_binding'] = SOURCE_BINDING
        self.proofs['logical_layouts_and_original_warps'] = [record['layout'] for record in records]

    def floor_materials(self):
        self.ash = self.gb_ref('crystal', 'UNION_CAVE_1F', 2, 0)
        gray = preview.palette_set(self.imp.table('crystal', 'palettes'), self.imp.table('crystal', 'maps')['SAFFRON_CITY'], 'DAY')[0]
        self.ash['palettes'] = [copy.deepcopy(gray) for _ in range(8)]
        self.path = self.gb_ref('crystal', 'CIANWOOD_CITY', 1, 0)
        self.emit(633, self.native(self.ash, 'ash'), 'ordinary_volcanic_ash',
                  'The full Fallarbor walking surface is fine volcanic ash, including the native route backdrop and solid far-map backfill. Original Crystal complete pebble-floor texture in its actual DAY gray-stone palette supplies an ash counterpart, distinct from grass, cliffs and the sandy town paths.')
        self.emit(753, self.native(self.path, 'path'), 'ordinary_light_path',
                  'This whole light sandy town footpath receives the complete native Crystal Cianwood walking-path cell, retaining its original texture and pixel size. The separately reviewed ash beside it remains visibly distinct.')
        for game in GAMES:
            colors = set(self.source((game, PAIR, 753)).get_flattened_data())
            for mid in (744, 745, 746, 752, 754, 760, 761, 762):
                source = self.source((game, PAIR, mid))
                mask = [pixel in colors for pixel in source.get_flattened_data()]
                spans = runs(mask); assert spans and len(spans) <= 32
                art = self.composite(self.ash, [dict(donor=self.path, srcX=s['x'], srcY=s['y'], **s) for s in spans], 'path_edge')
                self.emit_for(game, mid, art, 'path_edge_' + str(mid),
                              'The whole native town crossroads establishes this exact north/south/east/west path edge or end cap. Native Crystal sandy-path texture fills only the actual original path-colored pixels, while the reviewed native gray ash remains outside. Each cartridge palette and handed original footprint is checked separately; no cliff, boulder or ash grass is flattened into a path.')
        grass = self.raw_ref('TILESET_JOHTO', (4, 4, 4, 4), 'NEW_BARK_TOWN')
        for mid, q in ((671, 1), (679, 2)):
            art = self.composite(self.ash, [dict(donor=grass, gbForeground=True, srcX=0, srcY=0, w=8, h=8, x=q % 2 * 8, y=q // 2 * 8)], 'small_tuft')
            self.emit(mid, art, 'complete_small_ash_tuft_' + str(mid),
                      'The tiny decorative nonencounter tuft at the path margin is a whole native Crystal 8px leaf glyph at its original size and original source quadrant. Its transparent native foreground exposes ash between the blades. It is neither an encounter-grass field nor a clipped replacement tree crown.')
        self.proofs['native_floor_materials'] = dict(ash=self.ash, path=self.path, ash_is_not_encounter_grass=True)

    def cliff_piece(self, shape, background='ash'):
        art = self.classic_cliff(shape, 'field' if background == 'ash' else background)
        if background == 'ash':
            art['base'] = copy.deepcopy(self.ash)
        return art

    def volcanic_cliffs(self):
        for mid, shape, base in ((617, 'front', 'front'), (618, 'e', 'front'), (634, 'se', 'ash')):
            self.emit(mid, self.cliff_piece(shape, base), 'joined_volcanic_cliff_' + str(mid),
                      'The complete stepped cliff across the north of Fallarbor is independently reviewed as joined solid front walls, east-facing walls and lower outside turns. Complete original Crystal Violet outcrop cap/face modules keep native scale, lighting direction and the original raised/low-side relationship; gray ash appears only on the true low exterior side.')
        cap = self.cliff_piece('n', 'top')
        face = self.cliff_piece('front', 'front')
        for mid, template, src_y, dst_y, width in ((798, cap, 0, 8, 16), (625, face, 8, 0, 16), (789, cap, 0, 8, 8)):
            parts = []
            for part in template['parts']:
                x0, x1 = max(0, part.get('x', 0)), min(width, part.get('x', 0) + part['w'])
                y0, y1 = max(src_y, part.get('y', 0)), min(src_y + 8, part.get('y', 0) + part['h'])
                if x0 < x1 and y0 < y1:
                    parts.append(dict(part, srcX=part.get('srcX', 0) + x0 - part.get('x', 0),
                                      srcY=part.get('srcY', 0) + y0 - part.get('y', 0),
                                      x=x0, y=dst_y + y0 - src_y, w=x1-x0, h=y1-y0))
            art = self.composite(self.ash, parts, 'cliff_rim')
            self.emit(mid, art, 'volcanic_rim_' + str(mid),
                      'The actual ash/cliff transition is an eight-pixel top cap or foot/shadow band, not an additional full wall cell. One complete native Crystal 8px rim/face band stays at its original pixel size on the correct source edge; the remaining native ash remains open. The full wall immediately beside it is separately retained.')
        self.emit(797, self.cliff_piece('nw'), 'volcanic_cap_inner_join',
                  'This source is the native northwestern inside step of the ash-backed volcanic rim, between its horizontal top cap and the solid wall below. Complete original Crystal handed corner modules retain the connected rim, while the ordinary ash outside stays separate.')

    def bind(self, game, origin, matrix, arts, destination, description):
        layout = self.layout(game); ox, oy = origin
        height, width = len(matrix), len(matrix[0])
        actual = [[cell[0] for cell in row[ox:ox+width]] for row in layout['cells'][oy:oy+height]]
        assert actual == matrix, (game, destination, actual)
        doors = [warp for warp in layout['original_warps'] if warp['destMap'].endswith(destination)]
        assert len(doors) == 1 and (doors[0]['x'], doors[0]['y']) == (ox + (2 if width == 5 else 1), oy + height - 1)
        new = []
        for y, row in enumerate(matrix):
            for x, mid in enumerate(row):
                if (game, PAIR, mid) in self.prior:
                    continue
                art = arts[x, y]
                key = game, 'gen2', PAIR, mid, None
                if key in self.rows:
                    assert self.render(self.rows[key]).tobytes() == self.render(art).tobytes() and self.rows[key].get('overMask') == art.get('overMask', '0' * 256), (game, mid, 'Shared building cells differ')
                else:
                    self.emit_for(game, mid, art, 'whole_building_' + str(mid), description)
                new.append(mid)
        self.contracts.append(dict(game=game, map=layout['map'], origin=origin, source_matrix=matrix,
                                   original_entrance=doors[0], native_pixel_scale=1, new_ids=sorted(set(new)), description=description))

    def native_public(self, kind):
        arts = {(x, y): native_piece(self, 'gen2', kind, x, y) for y in range(4) for x in range(4)}
        whole = Image.new('RGBA', (64, 64))
        for (x, y), art in arts.items():
            whole.paste(self.render(art), (x*16, y*16))
        from reverse_hoenn_review import ground_ref
        outside = exterior(whole, set(self.gb_image(ground_ref(self, 'gen2')).get_flattened_data()) | {(222, 255, 222, 255)})
        return {(x, y): mask_piece(self, art, [(x*16+px, y*16+py) not in outside for py in range(16) for px in range(16)], self.ash, y < 2)
                for (x, y), art in arts.items()}

    def buildings(self):
        home = self.town_model(4, 2, 1, (2,), base=self.ash)
        upper = [[802, 803, 803, 804], [645, 646, 646, 647], [653, 669, 670, 655], [661, 677, 678, 663]]
        lower = [[637, 638, 808, 809], [645, 646, 646, 647], [653, 669, 670, 655], [661, 677, 678, 663]]
        lower_art = copy.deepcopy(home)
        for x in (2, 3):
            donor = self.gb_ref('crystal', 'RADIO_TOWER_5F', 10, 2)
            lower_art[x, 0]['parts'].append(dict(donor=donor, w=16, h=16, x=0, y=0))
            lower_art[x, 0]['overMask'] = '1' * 256
        for mid in (800, 801):
            art = self.composite(self.ash, [dict(donor=self.gb_ref('crystal', 'RADIO_TOWER_5F', 10, 0), w=16, h=16, x=0, y=0)], 'roof_vent')
            art['overMask'] = '1' * 256
            self.emit(mid, art, 'complete_roof_vent_upper_' + str(mid),
                      'The whole original Fallarbor rooftop apparatus spans 32x32 pixels above and into the house roof. Two intact original Crystal 16x32 metal-grille columns retain their complete upper and lower frames at 1:1; no part is scaled or used as an outdoor sign. The real roof remains complete beneath their opaque lower halves.')
        center, mart = self.native_public('center'), self.native_public('mart')
        hall = self.town_model(5, 3, 2, (1, 3), modern=True, base=self.ash)
        rs_hall = [[768, 769, 769, 769, 770], [688, 691, 691, 691, 692], [776, 777, 777, 777, 778], [784, 785, 467, 786, 787], [792, 793, 475, 794, 795]]
        em_hall = [[842, 843, 844, 845, 846], [850, 851, 852, 853, 854], [858, 859, 860, 861, 862], [866, 867, 868, 869, 870], [874, 875, 876, 877, 878]]
        for game in GAMES:
            destinations = ('FALLARBOR_TOWN_MOVE_RELEARNERS_HOUSE', 'FALLARBOR_TOWN_COZMOS_HOUSE') if game == 'emerald' else ('FALLARBOR_TOWN_HOUSE2', 'FALLARBOR_TOWN_HOUSE1')
            self.bind(game, (0, 3), upper, home, destinations[0], 'Complete native-size 64x64 Crystal timber house with full roof caps, whole 16px doorway and complete original 16x8 window pair. Only plain middle roof/wall modules repeat; original source entrance remains at relative 1,3, with gray native ash outside its genuinely transparent silhouette.')
            self.bind(game, (5, 14), lower, lower_art, destinations[1], 'Complete 64x64 native Crystal timber house with its full roof, full entrance and complete window pair; the separately reviewed whole 32x32 two-column rooftop grille retains every selected native frame above its original roof slot. No roof/window/door feature is reduced or truncated.')
            self.bind(game, (13, 4), [[672, 673, 674, 675], [80, 81, 82, 83], [88, 89, 90, 91], [681, 97, 98, 682]], center, 'FALLARBOR_TOWN_POKEMON_CENTER_1F', 'Whole native Crystal Cherrygrove Center retains its complete 64x64 roof, emblem/signage, facade and original full doorway. The upper roof and actual outer base corners expose the reviewed volcanic ash rather than grass; all already released body cells remain unchanged.')
            self.bind(game, (14, 12), [[699, 680, 680, 700], [48, 49, 50, 51], [56, 57, 58, 59], [681, 65, 66, 683]], mart, 'FALLARBOR_TOWN_MART', 'Whole original Crystal Cherrygrove Mart retains every native roof cap, full MART lettering, facade and entrance frame at its original 64x64 size. Only the separately checked ash-backed top row and base corners are added; original entrance, collision and released body art are preserved.')
            self.bind(game, (6, 3), em_hall if game == 'emerald' else rs_hall, hall,
                      'FALLARBOR_TOWN_BATTLE_TENT_LOBBY' if game == 'emerald' else 'FALLARBOR_TOWN_CONTEST_LOBBY',
                      'The original 80x80 public hall keeps its full source width, complete height and original centered 16px entrance. Whole original Crystal Saffron roof caps and complete New Bark window pairs/door form a purpose-arranged native public-building counterpart, with only ordinary middle roof/wall modules repeated. Ruby/Sapphire Contest Hall and Emerald Battle Tent source matrices and entrances are independently checked. No GYM label is introduced, no unique roof/window/door glyph is cut or fractionally resized, and gray ash remains visible outside the complete silhouette.')

    def vegetation_and_stones(self):
        trees = {q: self.park_tree_art(q, self.ash) for q in range(4)}
        def overlap(art, sx, sy, width, height, dx, dy):
            # Foreground canopy bands from the NEXT overlapping tree hide
            # only the same ordinary neighboring-root space as the source.
            # Source and destination dimensions remain identical integers.
            art = copy.deepcopy(art); mask = list(art['overMask'])
            for part in trees[0]['parts']:
                ax, ay = max(sx, part.get('x', 0)), max(sy, part.get('y', 0))
                bx, by = min(sx+width, part.get('x', 0)+part['w']), min(sy+height, part.get('y', 0)+part['h'])
                if ax < bx and ay < by:
                    art['parts'].append(dict(part, srcX=part.get('srcX', 0)+ax-part.get('x', 0),
                                             srcY=part.get('srcY', 0)+ay-part.get('y', 0),
                                             x=dx+ax-sx, y=dy+ay-sy, w=bx-ax, h=by-ay))
                    for yy in range(dy+ay-sy, dy+by-sy):
                        for xx in range(dx+ax-sx, dx+bx-sx): mask[yy*16+xx] = '1'
            art['overMask'] = ''.join(mask)
            assert len(art['parts']) <= 32
            return art
        variants = {518: trees[0], 519: trees[1], 526: trees[2]}
        variants[627] = overlap(trees[2], 0, 0, 16, 8, 0, 8)
        variants[628] = overlap(trees[3], 8, 0, 8, 16, 8, 0)
        variants[619] = overlap(variants[627], 8, 8, 8, 8, 0, 0)
        variants[620] = overlap(variants[628], 8, 8, 8, 8, 0, 0)
        for mid, art in variants.items():
            self.emit(mid, art, 'whole_native_tree_quadrant_' + str(mid),
                      'The full Fallarbor forest border uses complete native Crystal National Park 32x32 trees at the original 32px gameplay scale. Its reviewed staggered source rows include a next-tree canopy in front of neighboring roots. Complete original native 8px leaf/canopy bands preserve that real overlap, rather than leaving exposed floating trunks between the dense trees. Only genuine exterior grass becomes ash; all glyph pixels keep their size, and the real map boundary may naturally cut off artwork beyond the map.')
        cliff = self.cliff_piece('front', 'front')
        foot = artwork(self.rows['emerald', 'gen2', PAIR, 625, None])
        for mid, q in ((706, 0), (707, 1), (714, 2), (715, 3)):
            background = cliff if q < 2 else foot
            art = copy.deepcopy(trees[q]); art['base'] = copy.deepcopy(background['base']); art['parts'] = background['parts'] + art['parts']
            self.emit(mid, art, 'whole_tree_at_cliff_' + str(mid),
                      'This exact source mixes the complete nearby forest tree quarter with the volcanic wall behind it. Whole native Crystal canopy/trunk pixels remain in front of the separately selected native cliff; only unused exterior pixels show the wall. Original trees, collision and map geometry remain unchanged.')
        boulder = self.gb_ref('crystal', 'UNION_CAVE_1F', 24, 0)
        left = [6, 4, 3, 2, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 2]
        right = [11, 12, 13, 14, 15, 15, 16, 16, 16, 16, 16, 16, 16, 16, 15, 13]
        mask = [left[y] <= x < right[y] for y in range(16) for x in range(16)]
        art = self.composite(self.ash, [dict(donor=boulder, srcX=s['x'], srcY=s['y'], **s) for s in runs(mask)], 'fixed_boulder')
        self.emit(547, art, 'whole_fixed_boulder', 'Each fixed original 16px stone beside the public hall receives one entire original Crystal round cave boulder, retaining the complete cap, side shading and base. Only its old cave-floor exterior becomes the actual town ash. The source stone remains fixed, with no added Strength, Rock Smash or other interaction.')

    def crater(self):
        # The original decorative meteor depression is a full48x48 terrain
        # feature, not a cave entrance. Complete native texture at1:1 fills
        # purpose-authored shallow depth contours at that exact logical size.
        matrix = [[805, 806, 807], [813, 814, 815], [821, 822, 823]]
        gray = preview.palette_set(self.imp.table('crystal', 'palettes'), self.imp.table('crystal', 'maps')['SAFFRON_CITY'], 'DAY')[0]
        dark = copy.deepcopy(self.ash)
        dark['palettes'] = [[copy.deepcopy(gray[1]), copy.deepcopy(gray[2]), copy.deepcopy(gray[3]), copy.deepcopy(gray[3])] for _ in range(8)]
        art_by_mid = {}
        for y, row in enumerate(matrix):
            for x, mid in enumerate(row):
                # Native ash texture remains at its original pixel scale in
                # each depth zone. The rounded48px contour is authored at its
                # logical size, without reducing any donor object.
                outer = [((x*16+px-23.5)/23)**2 + ((y*16+py-23.5)/23)**2 <= 1 for py in range(16) for px in range(16)]
                inner = [((x*16+px-23.5)/11)**2 + ((y*16+py-23.5)/10)**2 <= 1 for py in range(16) for px in range(16)]
                parts = [dict(donor=dark, srcX=s['x'], srcY=s['y'], **s) for s in runs(outer)]
                parts += [dict(donor=self.ash, srcX=s['x'], srcY=s['y'], **s) for s in runs(inner)]
                assert len(parts) <= 32
                art_by_mid[mid] = self.composite(self.ash, parts, 'meteor_crater')
                self.emit(mid, art_by_mid[mid], 'meteor_crater_' + str(x) + '_' + str(y),
                          'The meteor depression remains one complete 48x48 shallow circular terrain feature in its original nine source cells. Native Crystal stone/ash texture retains 1:1 pixels within separately authored outer depression and inner floor contours at the actual logical size; no existing crater picture is downscaled, no doorway or black cave opening is substituted, and the originally walkable decoration adds no collision, warp or event.')
        self.proofs['meteor_crater'] = dict(source_origin=[1, 14], source_matrix=matrix, dimensions=[48, 48], native_texture=self.ash, shallow_depth_palette=dark['palettes'][0], no_entrance=True)

    def author(self):
        self.rows = {}; self.contracts = []; self.proofs = {}
        self.check_sources(); self.floor_materials(); self.volcanic_cliffs(); self.buildings(); self.vegetation_and_stones(); self.crater()
        assert len(self.rows) == 273, (len(self.rows), self.missing)
        for game in GAMES:
            assert {key[3] for key in self.rows if key[0] == game} == set(self.missing[game])
        def ordered(value):
            if isinstance(value, dict): return {k: ordered(value[k]) for k in sorted(value, key=str)}
            if isinstance(value, list): return [ordered(v) for v in value]
            return value
        self.rows = {key: ordered(self.rows[key]) for key in sorted(self.rows)}
        self.write(TARGET)
        scenes = [self.preview_map(game, self.layout(game)['map']) for game in GAMES]
        assert all(scene['replaced'] == scene['total'] == 400 for scene in scenes)
        affected = []
        for game in GAMES:
            for name, spec in self.imp.table(game, 'gba/native/manifest')['layouts'].items():
                if spec['pair'] != PAIR: continue
                raw = (self.cache / game / 'data/generated/gba/native' / spec['file']).read_bytes()
                data = raw if raw[:4] == b'SVML' else zlib.decompress(raw)
                pw, ph, width, height = struct.unpack_from('<HHHH', data, 6)
                width, height = width or pw, height or ph
                start = 16 + data[14] * data[15] * 2
                mids = [struct.unpack_from('<H', data, start + 4*(y*pw+x))[0] for y in range(height) for x in range(width)]
                used = Counter(mid for mid in mids if mid in self.missing[game])
                if used:
                    affected.append(dict(game=game, map=name, complete=name.endswith('FALLARBOR_TOWN')))
        affected.sort(key=lambda item: (item['game'], item['map']))
        (self.out / 'affected-scenes.json').write_text(json.dumps(affected, indent=2) + '\n')
        self.proofs['existing_recipe_key_guards'] = dict(previous_rows=len(self.prior),
                                                       previous_recipe_sha256=digest([self.prior[key] for key in sorted(self.prior)]),
                                                       existing_keys_overwritten=0, new_rows=273)
        (self.out / 'contracts.json').write_text(json.dumps(dict(rows=273, scenes=scenes, buildings=self.contracts, proofs=self.proofs), indent=2) + '\n')
        return scenes

    def layout(self, game):
        name = {'ruby': 'RU_', 'sapphire': 'SA_', 'emerald': 'EM_'}[game] + 'FALLARBOR_TOWN'
        spec = self.imp.table(game, 'gba/native/manifest')['layouts'][name]
        raw = (self.cache / game / 'data/generated/gba/native' / spec['file']).read_bytes()
        data = raw if raw[:4] == b'SVML' else zlib.decompress(raw)
        pw, ph, width, height = struct.unpack_from('<HHHH', data, 6)
        width, height = width or pw, height or ph
        start = 16 + data[14] * data[15] * 2
        cells = [[struct.unpack_from('<HBB', data, start + 4 * (y * pw + x)) for x in range(width)] for y in range(height)]
        return dict(game=game, map=name, pair=spec['pair'], file=spec['file'], file_sha256=catalog.sha(raw),
                    width=width, height=height, cells=cells, original_warps=self.imp.table(game, 'gba/warps')[name])

    def source_binding(self):
        records = []
        for game in GAMES:
            layout = self.layout(game)
            ids = sorted({cell[0] for row in layout['cells'] for cell in row})
            index = self.imp.cell_index(game)
            records.append(dict(layout=layout, cells=[dict(id=mid, rgba_sha256=index[PAIR, mid]['pixel_sha256'],
                                                          behavior=index[PAIR, mid]['behavior'], layer_sha256=index[PAIR, mid]['layer_sha256']) for mid in ids]))
        return records

    def inspect(self):
        records = self.source_binding()
        (self.out / 'source-bindings.json').write_text(json.dumps(records, indent=2) + '\n')
        report = []
        for record in records:
            layout = record['layout']; game, name = layout['game'], layout['map']
            cells = [[cell[0] for cell in row] for row in layout['cells']]
            missing = Counter(mid for row in cells for mid in row if (game, PAIR, mid) not in self.prior)
            items = []
            contact = Image.new('RGB', (128 * 8, 120 * ((len(missing) + 7) // 8)), '#18212b')
            draw = ImageDraw.Draw(contact); font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 12)
            for i, (mid, count) in enumerate(missing.most_common()):
                positions = [(x, y) for y, row in enumerate(cells) for x, value in enumerate(row) if value == mid]
                cell = self.imp.cell_index(game)[PAIR, mid]
                items.append(dict(id=mid, count=count, positions=positions, source=cell))
                x, y = i % 8 * 128, i // 8 * 120
                draw.text((x + 3, y + 2), f'{mid} x{count} b{cell.get("behavior")}', font=font, fill='white')
                contact.paste(self.source((game, PAIR, mid)).resize((64, 64), Image.Resampling.NEAREST), (x + 4, y + 30))
            contact.save(self.out / (game + '-missing.png'))
            self.preview_map(game, name)
            (self.out / (game + '-' + name + '-previous.png')).write_bytes((self.out / (game + '-' + name + '-after.png')).read_bytes())
            report.append(dict(game=game, map=name, pair=PAIR, remaining=sum(missing.values()), rows=items, layout=cells))
        (self.out / 'inventory.json').write_text(json.dumps(report, indent=2) + '\n')
        return dict(source_binding=digest(records), games=[dict(game=r['game'], remaining=r['remaining'], ids=[x['id'] for x in r['rows']]) for r in report])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inspect', action='store_true')
    parser.add_argument('--validate', action='store_true')
    args = parser.parse_args()
    review = Review()
    if args.inspect:
        print(json.dumps(review.inspect()))
    else:
        print(json.dumps(review.author()))
        if args.validate:
            print(json.dumps(review.validate()))


if __name__ == '__main__':
    main()
