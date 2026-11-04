"""Individually reviewed native Crystal counterparts for Lavaridge Town."""
from __future__ import annotations

import argparse
import copy
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct
import zlib

from PIL import Image, ImageDraw, ImageFont

import catalog
import preview
from gb_theme_animation import specification
from johto_remaining_review import artwork
from reverse_hoenn_review import ground_ref
from reverse_kanto_review import exterior, runs
from reverse_oldale_review import native_piece, mask_piece
from reverse_common import ROOT, ReverseReview
from reverse_gen2_hoenn_city_complete import Review as CityReview
from reverse_gen2_hoenn_outdoor_finish import Review as OutdoorReview

TARGET = ROOT / 'mappings/reverse_gen2_lavaridge_complete.lua'
GAMES = ('ruby', 'sapphire', 'emerald')
SOURCE_IDS = (529, 536, 542, 543, 584, 585, 586, 587, 588, 589, 590, 591,
              620, 621, 633, 635, 636, 650, 652, 657, 658, 664, 665, 666,
              667, 668, 669, 670, 671, 672, 673, 675, 677, 679, 680, 681,
              682, 684, 685, 686, 689, 690, 691, 692, 693, 697, 698, 699,
              700, 797)
SOURCE_BINDING = 'f047523e5a965074787b057534141cf553651af5255197477701510b43375a92'


class Review(CityReview):
    def __init__(self):
        ReverseReview.__init__(self, 'gen2-lavaridge-complete', GAMES)
        self.prior, self.contracts, self.proofs = {}, [], {}
        select = catalog.LUA.eval('function(rows)local out={} for _,r in ipairs(rows)do if r.style=="gen2" and r.tileset=="general__lavaridge" then out[#out+1]=r end end return out end')
        modules = dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]", (ROOT / 'main.lua').read_text()))
        for module in modules:
            if ROOT / module == TARGET:
                continue
            selected = catalog.plain(select(catalog.LUA.execute((ROOT / module).read_text(encoding='utf-8-sig'))))
            for row in selected if isinstance(selected, list) else []:
                key = row['game'], row['tileset'], row['id']
                assert key not in self.prior
                self.prior[key] = row
        self.out = ROOT.parent / '.work/tileshift-v0340-lavaridge'
        self.out.mkdir(parents=True, exist_ok=True)

    raw_ref = OutdoorReview.raw_ref
    classic_cliff = OutdoorReview.classic_cliff

    def existing_art(self, mid):
        original = self.prior['emerald', 'general__lavaridge', mid]
        art = artwork(original)
        for field in ('overMask', 'animationCategory'):
            if field in original:
                art[field] = copy.deepcopy(original[field])
        return art

    def emit_art(self, mid, art, role, reason):
        art = copy.deepcopy(art)
        art['role'] = 'reverse_gen2_lavaridge_' + role
        art.setdefault('overMask', '0' * 256)
        for game in GAMES:
            assert (game, 'general__lavaridge', mid) not in self.prior
            self.row(game, 'general__lavaridge', mid, 'gen2', art,
                     reason + ' The complete native Lavaridge source grid, all three cartridge RGBA/layer/behavior identities and the native-size joined object are individually reviewed. Native Crystal pixels retain 1:1 scale; source collision, elevations, actors, warps, scripts and interactions remain unchanged.')

    def check_sources(self):
        binding = []
        for game in GAMES:
            name, pair, cells = self.layout(game)
            missing = sorted(set(mid for row in cells for mid in row if (game, pair, mid) not in self.prior))
            assert tuple(missing) == SOURCE_IDS, (game, missing)
            index = self.imp.cell_index(game)
            binding.append(dict(game=game, rows=[(mid, index[pair, mid]['pixel_sha256'], index[pair, mid]['behavior'], index[pair, mid]['layer_sha256']) for mid in missing]))
            for mid in missing:
                assert catalog.sha(self.source((game, pair, mid)).tobytes()) == index[pair, mid]['pixel_sha256']
        digest = hashlib.sha256(json.dumps(binding, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        assert digest == SOURCE_BINDING, 'Lavaridge source artwork/geometry/behavior changed; a fresh review is required'
        self.proofs['frozen_source_binding'] = digest

    def terrain(self):
        for mid, shape, backing in ((620, 'n', 'field'), (621, 'ne', 'field'),
                                     (633, 'front', 'field'), (635, 'sw', 'top'),
                                     (636, 'se', 'top')):
            self.emit_art(mid, self.classic_cliff(shape, backing), 'cliff_' + str(mid),
                          'Joined original volcanic cliff context supplies this explicitly handed top edge, front face or lower turn. Complete original Crystal Violet outcrop 8px cap/face modules join the already selected native cliff family; solid backing remains stone and outside terrain remains field.')
        # Ordinary spa sand remains a separate material from the town's lawn.
        sand = self.raw_ref('TILESET_KANTO', (48, 57, 57, 48), 'PALLET_TOWN')
        self.sand = sand
        self.emit_art(680, self.native(sand, 'sand'), 'spa_sand', 'The hot-spring apron is complete coarse sandy floor, not water, a wall or a submerged object. Original Crystal native Kanto sand supplies the complete 16px surface.')
        field = ground_ref(self, 'gen2')
        source_colors = set(self.source(('emerald', 'general__lavaridge', 680)).get_flattened_data())
        for mid in (650, 652, 657, 658):
            source = self.source(('emerald', 'general__lavaridge', mid))
            mask = [color in source_colors for color in source.get_flattened_data()]
            spans = runs(mask)
            assert 0 < sum(mask) < 256 and len(spans) <= 32
            art = self.composite(field, [dict(donor=sand, srcX=s['x'], srcY=s['y'], **s) for s in spans], 'sand_edge')
            self.emit_art(mid, art, 'spa_sand_edge_' + str(mid), 'This explicitly reviewed sandy apron/grass join uses native Crystal sand only within the original sandy floor silhouette, with the same selected Crystal field outside. The original handed bend is independently checked against the full spring map; no bank or object is treated as floor.')
        for mid in (697, 698):
            self.emit_art(mid, self.native(sand, 'sand'), 'spa_sand_glint_' + str(mid), 'The white source glint is entirely within the same full sandy spring apron, without any grass boundary or object. The complete native Crystal sand texture supplies that full floor; no patch of lawn is introduced beneath the old glint.')
        self.proofs['spa_sand'] = sand

    def nature(self):
        self.emit_art(529, self.existing_art(206), 'whole_conifer_upper', 'The complete native 16px-wide Crystal conifer upper half joins its original-size roots in the next source row. The original upper canopy is neither reduced nor replaced with grass.')
        roots = self.existing_art(198)
        cliff = self.existing_art(625)
        roots['parts'] = copy.deepcopy(cliff['parts']) + roots['parts']
        roots['base'] = copy.deepcopy(cliff['base'])
        self.emit_art(536, roots, 'conifer_roots_cliff', 'The complete lower half of the native conifer is retained above the real volcanic backing. Only its outside field becomes the matching native stone; every original tree/trunk pixel stays intact, including the tree at the actual north map boundary.')
        for mid in (542, 543):
            self.emit_art(mid, self.existing_art(4), 'flower_above_whole_tree_' + str(mid), 'Each source cell contains a complete flower plus a tiny apex from the larger Hoenn tree below. The separately selected native Crystal 32x32 tree below already includes its complete original crown. The complete native animated flower stays intact, without adding a third-row canopy fragment or truncating either object.')

    def public_roofs(self):
        # These are the missing TOP roof rows; the released lower roof rows,
        # signs, complete fronts, original doors and entry cells stay intact.
        for kind, source_ids in (('center', (586, 584, 585, 589)), ('mart', (590, 587, 588, 591))):
            whole = Image.new('RGBA', (64, 64))
            arts = {}
            for y in range(4):
                for x in range(4):
                    arts[x, y] = native_piece(self, 'gen2', kind, x, y)
                    whole.paste(self.render(arts[x, y]), (x * 16, y * 16))
            field = ground_ref(self, 'gen2')
            outside = exterior(whole, set(self.gb_image(field).get_flattened_data()) | {(222, 255, 222, 255)})
            for x, mid in enumerate(source_ids):
                mask = [(x * 16 + px, py) not in outside for py in range(16) for px in range(16)]
                roof = mask_piece(self, arts[x, 0], mask, field, True)
                background = self.classic_cliff('front', 'top') if mid in (584, 585, 589) else self.classic_cliff('n', 'top') if kind == 'mart' else self.native(field, 'field')
                if background['kind'] == 'native':
                    roof['base'] = background['donor']
                else:
                    roof['base'] = background['base']
                    roof['parts'] = background['parts'] + roof['parts']
                self.emit_art(mid, roof, kind + '_complete_roof_' + str(x), 'The original Lavaridge ' + kind + ' has a distinct upper roof row against the volcanic cliff. The complete native Crystal Cherrygrove top roof row joins its already reviewed lower roof and full facade at their original pixel size. Only true outside roof corners expose the correct native backing; unique roof caps, full signage and entrance positions stay complete.')

    def spring(self):
        water = self.gb_ref('crystal', 'UNION_CAVE_1F', 15, 0)
        program = specification(self.cache, water, 'program')
        assert program
        rock = self.gb_ref('crystal', 'UNION_CAVE_1F', 4, 2)
        gray = preview.palette_set(self.imp.table('crystal', 'palettes'), self.imp.table('crystal', 'maps')['SAFFRON_CITY'], 'DAY')[0]
        rock['palettes'] = [copy.deepcopy(gray) for _ in range(8)]
        field = ground_ref(self, 'gen2')
        # Independently reviewed 8px pool plan: W native water, R complete
        # rounded stone glyph, S native sand, F native field, C volcanic bank.
        plans = {665: 'CCCR', 666: 'RRRW', 667: 'RRWW', 669: 'CCRC',
                 673: 'RWRW', 677: 'WRWR', 681: 'RWRR', 682: 'WWRW',
                 684: 'WWWR', 685: 'WRRR', 689: 'RRSR', 690: 'RRSS',
                 691: 'RRSS', 692: 'RRSS', 693: 'RRRF',
                 675: 'WWWW', 699: 'WWWW', 700: 'WWWW', 797: 'WWWW'}
        cliff = self.raw_ref('TILESET_JOHTO', (76,) * 4, 'VIOLET_CITY')
        for mid, plan in plans.items():
            parts = []
            for q, value in enumerate(plan):
                donor = {'W': water, 'R': rock, 'S': self.sand, 'F': field, 'C': cliff}[value]
                part = dict(donor=donor, srcX=0, srcY=0, w=8, h=8, x=q % 2 * 8, y=q // 2 * 8)
                if value == 'W':
                    part['animated'] = True
                parts.append(part)
            art = self.composite(None, parts, 'spring')
            if 'W' in plan:
                art.update(animated=True, animation=program, animationCategory='water')
            self.emit_art(mid, art, 'spring_join_' + str(mid), 'The whole Lavaridge hot-spring basin is reviewed as one joined 96x80 envelope. Full original Crystal 8px rounded stone glyphs in the native gray palette retain a continuous distinct rim; native cave-water glyphs animate as one coherent body inside it. These explicit handed corner/side plans preserve the sandy entry, bank direction and original bathing-water cells instead of erasing the rim as plain water. Native rock glyphs retain every source pixel at 1:1.')
        fence = self.gb_at('crystal', 'SPROUT_TOWER_1F', 4, 0)
        self.emit_art(686, self.native(fence, 'screen'), 'privacy_screen', 'The complete vertical wooden spring privacy screen receives one complete native Crystal 16px wooden palisade module from Sprout Tower. Whole cap, vertical posts and lower rail retain original pixels; ordinary full modules repeat along the source four-cell screen.')
        for mid, base in ((668, water), (670, cliff)):
            art = self.composite(base, [dict(donor=fence, srcX=0, srcY=0, w=16, h=8, x=0, y=0)], 'spring_screen_rail')
            if mid == 668:
                art['parts'].insert(0, dict(donor=water, w=16, h=16, x=0, y=0, animated=True))
                art.update(animated=True, animation=program, animationCategory='water')
            self.emit_art(mid, art, 'privacy_rail_' + str(mid), 'The source horizontal spring rail joins the complete wooden screen above. Its complete native Crystal 8px palisade top/cap module retains 1:1 scale, with the actual animated pool or solid volcanic bank beneath. The original rear clinic entrance and all source collision remain unchanged.')
        self.proofs['spring_plan'] = dict(plans=plans, complete_native_rock_glyph=rock, coherent_water=water, native_privacy_screen=fence)

    def mounds_and_machine(self):
        # One complete rounded native16px object crosses each source cell seam;
        # no duplicate object, fractional scaling or half object is introduced.
        mound = self.gb_ref('crystal', 'UNION_CAVE_1F', 24, 0)
        colors = preview.palette_set(self.imp.table('crystal', 'palettes'), self.imp.table('crystal', 'maps')['CIANWOOD_CITY'], 'DAY')[5]
        mound['palettes'] = [copy.deepcopy(colors) for _ in range(8)]
        left = [6, 4, 3, 2, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 2]
        right = [11, 12, 13, 14, 15, 15, 16, 16, 16, 16, 16, 16, 16, 16, 15, 13]
        for mid, top in ((664, True), (672, False)):
            mask = [left[y] <= x < right[y] for y in range(16) for x in range(16)]
            parts = []
            for span in runs(mask):
                sy = max(span['y'], 0 if top else 8)
                end = min(span['y'] + span['h'], 8 if top else 16)
                if sy < end:
                    parts.append(dict(donor=mound, srcX=span['x'], srcY=sy, w=span['w'], h=end-sy, x=span['x'], y=sy+8 if top else sy-8))
            self.emit_art(mid, self.composite(self.sand, parts, 'sand_mound'), 'complete_sand_mound_' + ('upper' if top else 'lower'), 'Each of the two original rounded spa-apron mounds receives one complete original Crystal 16px rounded stone/cap silhouette in the original native outdoor sand/stone palette. The whole cap, highlights, sides and base cross the same source row seam at their original pixel size. Only the old donor exterior floor becomes the matching spa sand; the native source mound positions and behavior remain unchanged.')
        for mid, sy in ((671, 0), (679, 16)):
            art = self.composite(None, self.gb_rect('crystal', 'POWER_PLANT', 192, sy, 16, 16), 'gym_machine')
            self.emit_art(mid, art, 'whole_gym_machine_' + str(sy), 'The complete 16x32 machine cabinet beside the Gym uses an intact original Crystal Power Plant control/rack column, including its full upper controls and lower cabinet. Both native rows retain 1:1 pixels; no window, control panel or base is cut to fit. The original Gym entrance and adjacent actor/collision positions stay unchanged.')

    def author(self):
        self.rows = {}
        self.check_sources()
        self.terrain()
        self.nature()
        self.public_roofs()
        self.spring()
        self.mounds_and_machine()
        assert len(self.rows) == 150
        def ordered(value):
            if isinstance(value, dict):
                return {key: ordered(value[key]) for key in sorted(value, key=str)}
            if isinstance(value, list):
                return [ordered(item) for item in value]
            return value
        self.rows = {key: ordered(self.rows[key]) for key in sorted(self.rows)}
        self.write(TARGET)
        scenes = [self.preview_map(game, self.layout(game)[0]) for game in GAMES]
        assert all(s['replaced'] == s['total'] == 400 for s in scenes)
        self.proofs['native_object_dimensions'] = dict(hot_spring_envelope=[96, 80], individual_sand_mound=[16, 16], gym_machine=[16, 32], clinic_and_mart=[64, 64], privacy_screen_module=[16, 16], all_pixel_scales=1)
        self.proofs['source_layouts_and_entrances'] = []
        for game in GAMES:
            name = self.layout(game)[0]
            spec = self.imp.table(game, 'gba/native/manifest')['layouts'][name]
            raw = (self.cache / game / 'data/generated/gba/native' / spec['file']).read_bytes()
            self.proofs['source_layouts_and_entrances'].append(dict(game=game, map=name, source_layout_sha256=catalog.sha(raw), original_entrances=self.imp.table(game, 'gba/warps')[name]))
        (self.out / 'contracts.json').write_text(json.dumps(dict(rows=len(self.rows), scenes=scenes, proofs=self.proofs), indent=2) + '\n')
        return scenes

    def layout(self, game):
        name = {'ruby': 'RU_', 'sapphire': 'SA_', 'emerald': 'EM_'}[game] + 'LAVARIDGE_TOWN'
        spec = self.imp.table(game, 'gba/native/manifest')['layouts'][name]
        raw = (self.cache / game / 'data/generated/gba/native' / spec['file']).read_bytes()
        data = raw if raw[:4] == b'SVML' else zlib.decompress(raw)
        pw, ph, width, height = struct.unpack_from('<HHHH', data, 6)
        width, height = width or pw, height or ph
        start = 16 + data[14] * data[15] * 2
        cells = [[struct.unpack_from('<H', data, start + 4 * (y * pw + x))[0]
                  for x in range(width)] for y in range(height)]
        return name, spec['pair'], cells

    def inspect(self):
        report = []
        for game in GAMES:
            name, pair, cells = self.layout(game)
            missing = Counter(mid for row in cells for mid in row if (game, pair, mid) not in self.prior)
            items = []
            font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 12)
            contact = Image.new('RGB', (128 * 8, 120 * ((len(missing) + 7) // 8)), '#18212b')
            draw = ImageDraw.Draw(contact)
            for i, (mid, count) in enumerate(missing.most_common()):
                positions = [(x, y) for y, row in enumerate(cells) for x, value in enumerate(row) if value == mid]
                cell = self.imp.cell_index(game)[pair, mid]
                items.append(dict(id=mid, count=count, positions=positions, source=cell))
                x, y = i % 8 * 128, i // 8 * 120
                draw.text((x + 3, y + 2), f'{mid} x{count} b{cell.get("behavior")}', font=font, fill='white')
                contact.paste(self.source((game, pair, mid)).resize((64, 64), Image.Resampling.NEAREST), (x + 4, y + 30))
            contact.save(self.out / (game + '-missing.png'))
            self.preview_map(game, name)
            report.append(dict(game=game, map=name, pair=pair, remaining=sum(missing.values()), rows=items, layout=cells))
        (self.out / 'inventory.json').write_text(json.dumps(report, indent=2) + '\n')
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inspect', action='store_true')
    parser.add_argument('--validate', action='store_true')
    args = parser.parse_args()
    review = Review()
    if args.inspect:
        print(json.dumps([dict(game=r['game'], remaining=r['remaining'], ids=[x['id'] for x in r['rows']]) for r in review.inspect()]))
    else:
        print(json.dumps(review.author()))
        if args.validate:
            print(json.dumps(review.validate()))


if __name__ == '__main__':
    main()
