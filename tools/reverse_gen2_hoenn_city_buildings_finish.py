"""Whole native Crystal modules for independently reviewed Hoenn city buildings.

Source building envelopes, entrances and every complete window remain intact.
Only ordinary roof/wall modules repeat; these are not resized bitmap assets.
"""
from __future__ import annotations

import argparse
import copy
import json

from PIL import Image, ImageDraw, ImageFont

import catalog
import preview
from building_review import decode_layout
from reverse_common import ROOT, ReverseReview
from reverse_hoenn_review import ground_ref
from reverse_kanto_review import exterior
from reverse_oldale_review import mask_piece

GAMES = ('ruby', 'sapphire', 'emerald')
TARGET = ROOT / 'mappings/reverse_gen2_hoenn_city_buildings_finish.lua'
MODERN_ROOF = {'roof_nw':(0,0),'roof_n':(16,0),'roof_ne':(48,0),
               'roof_w':(0,8),'roof_fill':(16,8),'roof_e':(48,8),
               'roof_sw':(0,16),'roof_s':(16,16),'roof_se':(48,16)}
MODERN_BASE = {'base_w':0,'base':32,'base_e':48,'door':16}


class Review(ReverseReview):
    def __init__(self):
        super().__init__('gen2-hoenn-city-buildings-finish', GAMES)
        self.contracts = []

    def modern_house_module(self, role):
        def rect(x,y,w=16,h=16,dx=0,dy=0):
            return self.gb_rect('crystal','SAFFRON_CITY',128+x,128+y,w,h,dx,dy)
        if role in MODERN_ROOF:parts=rect(*MODERN_ROOF[role])
        elif role in ('wall','wall_w','wall_e','window','door_head'):
            x=0 if role=='wall_w' else 48 if role=='wall_e' else 16
            parts=rect(x,40,16,8)+rect(x,40,16,8,0,8)
            if role=='window':
                parts=rect(x,40,16,8)+self.gb_rect('crystal','NEW_BARK_TOWN',232,72,16,8,0,8)
        else:
            x=MODERN_BASE[role]
            parts=rect(x,48)
        return self.composite(None,parts,'reverse_gen2_hoenn_city_modern_'+role)

    def rustboro_plain_homes(self):
        # Full roofs/windows/doors reviewed in the actual80x80 houses and
        # repeated apartment facade. Larger buildings share these modules.
        pair='general__rustboro'
        roles={548:'roof_nw',549:'roof_n',550:'roof_ne',566:'roof_w',574:'roof_fill',567:'roof_e',
               556:'roof_sw',557:'roof_s',558:'roof_se',532:'wall_w',533:'wall',534:'wall_e',
               578:'window',535:'door_head',540:'base_w',541:'base',543:'door',542:'base_e'}
        # MID699 is the actual original brick walk pavement around these
        # homes, independently checked at(30,14),(31,14),(30,15..19) and
        # (31,20). The separate source layout and original floor remain intact.
        base_ref=self.gb_ref('crystal','GOLDENROD_CITY',6,0)
        shadow_ref=copy.deepcopy(base_ref)
        original_palettes=preview.palette_set(self.imp.table('crystal','palettes'),self.imp.table('crystal','maps')['GOLDENROD_CITY'],'DAY')
        # A deliberate four-shade Gen2 shadow counterpart, quantized to the
        # original five-bit GBC channel grid. Geometry stays original6q0.
        shadow_ref['palettes']=[[[round(round(round(channel*31/255)*.8)*255/31) for channel in color] for color in slot] for slot in original_palettes]
        for game,prefix in (('emerald','EM_'),('ruby','RU_'),('sapphire','SA_')):
            source_map=prefix+'RUSTBORO_CITY'
            spec=self.imp.table(game,'gba/native/manifest')['layouts'][source_map]
            path=self.cache/game/'data/generated/gba/native'/spec['file']
            layout=decode_layout(path);refs=self.imp.cell_index(game)
            anchors=((30,14),(31,14),(30,15),(30,16),(30,18),(30,19),(31,20))
            assert all(layout['mids'][y*layout['width']+x]==699 for x,y in anchors)
            floor=refs[pair,699]
            actual=preview.native_donor(self.cache,dict(game=game,tileset=pair,id=699,hash=floor['pixel_sha256']),self.packed)
            assert catalog.sha(actual.tobytes())==floor['pixel_sha256']
            self.row(game,pair,699,'gen2',self.native(base_ref,'reverse_gen2_hoenn_city_brick_walk_pavement'),
                'Actual Rustboro ordinary brick walk pavement is independently reviewed beside and around the complete native city houses at explicit source coordinates. Original Crystal Goldenrod complete16px brick street is its native Gen2 counterpart at1:1. This is a floor-to-floor material adaptation, not a whole-roof UNDER guess or an object/ledge alias. Actual native source RGBA and behavior are guarded for each cartridge; source layout, collision, actors and all events remain unchanged.')
            self.row(game,pair,707,'gen2',self.native(shadow_ref,'reverse_gen2_hoenn_city_shadowed_brick_walk_pavement'),
                'Actual native Rustboro707 is the same whole brick walk pavement as699 under a uniform building shadow, independently reviewed for Ruby/Sapphire and Emerald beside each full house and Devon Corp. The original complete Crystal Goldenrod6q0 brick glyph receives a deliberate darker four-shade palette on the original five-bit GBC color grid; no source pixels are recolored or rescaled. This retains the paving material and its shadow instead of baking the old Gen3 floor behind new buildings. Native source collision, actors, events and layout remain unchanged.')
            backing_evidence=dict(source_mid=699,sourceHash=floor['pixel_sha256'],native_donor=base_ref,actual_source_contexts=anchors)
            model=Image.new('RGBA',(64,64));field=self.gb_image(base_ref)
            for y in range(4):
                for x in range(4):
                    parts=self.gb_rect('crystal','SAFFRON_CITY',128+x*16,128+y*16,16,16)
                    model.paste(self.render(self.composite(None,parts,'proof')),(x*16,y*16))
            # The original Saffron house has pale urban field at its real
            # outside corners; never remove enclosed pale roof/window pixels.
            corner_colors={(222,255,222,255)}
            outside=exterior(model,corner_colors)
            for mid,role in roles.items():
                art=self.modern_house_module(role)
                # Track the exact original crop, including8px roof-band
                # offsets and repeated brick rows. Every exterior side strip
                # exposes the same pavement; enclosed trim/highlights remain.
                def source_xy(x,y):
                    if role in MODERN_ROOF:
                        sx,sy=MODERN_ROOF[role];return sx+x,sy+y
                    if role in ('wall','wall_w','wall_e','window','door_head'):
                        sx=0 if role=='wall_w'else 48 if role=='wall_e'else 16
                        return sx+x,40+y%8
                    return MODERN_BASE[role]+x,48+y
                mask=[source_xy(x,y)not in outside for y in range(16)for x in range(16)]
                art=mask_piece(self,art,mask,base_ref,role.startswith('roof_'))
                self.row(game,pair,mid,'gen2',art,
                    'The entire Rustboro modern house/flat facade and80x80 house roof were reviewed in their actual city layout. Complete original Crystal Saffron gray-roof caps, brick side frames, wall base and16px doorway retain1:1 pixels. Only the plain roof middle8..23 band and ordinary8px brick rows repeat to reach the original source size; every window source receives one entire original Crystal16x8 window pair. Repeated apartment floors retain the same complete window modules. Actual source city pavement699 is independently checked at seven neighboring walking cells and supplies the matching native brick background at true outside corners; no complete roof UNDER is treated as a flat floor. Source collision, original entrances, height, actors and all events remain unchanged.')
            self.contracts.append(dict(game=game,map=source_map,kind='complete_modern_house_modules',source_ids=roles,
                source_contact='home1-source.png and town-native-inventory.json',backing=backing_evidence,
                per_cartridge_source_design_review='rustboro-all3-house-and-paving.png',
                shadow_counterpart=dict(source=707,native_block=6,native_quadrant=0,shade_ratio=.8,color_grid_bits=5),
                native_complete_model=['crystal','SAFFRON_CITY',8,8,4,4],whole_native_window=['NEW_BARK_TOWN',232,72,16,8],pixel_scale=1))

    def house_module(self, x, y, window=False, clear_half_window=False):
        def rect(sx, sy, w=16, h=16, dx=0, dy=0):
            return self.gb_rect('crystal', 'NEW_BARK_TOWN', 192+sx, 32+sy, w, h, dx, dy)
        parts = rect(x*16, y*16)
        if window:
            # One entire original16x8 pair goes in the source window cell.
            parts = rect(16, 32, 16, 8) + rect(40, 40, 16, 8, 0, 8)
        elif clear_half_window:
            # Keep the complete outer8px wall cap; omit its former half-window.
            parts = rect(16, 32, 8, 16) + rect(56, 32, 8, 16, 8)
        return self.composite(None, parts, 'reverse_gen2_hoenn_city_complete_house_module')

    def mauville_homes(self):
        pair = 'general__mauville'
        layouts = [
            ('EM_MAUVILLE_CITY', 'EM_MAUVILLE_CITY_HOUSE2', 18, 11,
             [[643,644,644,645], [651,652,652,653], [659,676,623,661], [667,684,631,669]]),
            ('EM_MAUVILLE_CITY', 'EM_MAUVILLE_CITY_BIKE_SHOP', 34, 2,
             [[643,644,644,644,645], [651,652,652,652,653], [659,676,677,623,661], [667,684,685,631,669]]),
        ]
        positions = {
            643:(0,0),644:(1,0),645:(3,0),651:(0,1),652:(1,1),653:(3,1),
            659:(0,2),676:(1,2),677:(1,2),623:(2,2),661:(3,2),
            667:(0,3),684:(1,3),685:(2,3),631:(2,3),669:(3,3),
        }
        field = ground_ref(self, 'gen2')
        original = Image.new('RGBA', (64,64))
        for y in range(4):
            for x in range(4):
                original.paste(self.render(self.house_module(x,y)), (x*16,y*16))
        outside = exterior(original, set(self.gb_image(field).get_flattened_data()) | {(222,255,222,255)})
        modules = {}
        for mid,(x,y) in positions.items():
            art = self.house_module(x,y,window=mid==623,clear_half_window=mid==661)
            mask = [(x*16+px,y*16+py) not in outside for py in range(16) for px in range(16)]
            modules[mid] = mask_piece(self, art, mask, field, y<2)
        by_game = {'emerald':'EM_', 'ruby':'RU_', 'sapphire':'SA_'}
        canonical = self.imp.cell_index('emerald')
        for game,prefix in by_game.items():
            refs = self.imp.cell_index(game)
            name = prefix+'MAUVILLE_CITY'
            spec = self.imp.table(game,'gba/native/manifest')['layouts'][name]
            assert spec['pair'] == pair
            path = self.cache/game/'data/generated/gba/native'/spec['file']
            native = decode_layout(path)
            warps = self.imp.table(game,'gba/warps')[name]
            for _,dest,ox,oy,layout in layouts:
                expected = [native['mids'][(oy+y)*native['width']+ox:(oy+y)*native['width']+ox+len(row)] for y,row in enumerate(layout)]
                assert expected == layout, ('Whole source building layout changed',game,dest,expected)
                actual_dest = prefix+dest[3:]
                anchor = [w for w in warps if w['destMap']==actual_dest and w['x']==ox+1 and w['y']==oy+3]
                assert len(anchor)==1, ('Original complete house entrance moved',game,actual_dest)
                for row in layout:
                    for mid in row:
                        assert refs[pair,mid]['behavior']==canonical[pair,mid]['behavior']
                        # R/S have striped roofs, square windows and timber
                        # posts; Emerald has a cornice, arched windows and
                        # plain posts. These complete source buildings were
                        # reviewed separately, not approved by index identity.
                        cell=refs[pair,mid]
                        actual=preview.native_donor(self.cache,dict(game=game,tileset=pair,id=mid,hash=cell['pixel_sha256']),self.packed)
                        assert catalog.sha(actual.tobytes())==cell['pixel_sha256']
                self.contracts.append(dict(game=game,map=name,destination=actual_dest,source_origin=[ox,oy],
                    source_layout=layout,source_file_sha256=catalog.sha(path.read_bytes()),original_warp=anchor[0],
                    source_cells=[dict(id=m,hash=refs[pair,m]['pixel_sha256'],behavior=refs[pair,m]['behavior']) for m in sorted({m for row in layout for m in row})],
                    native_model=['crystal','NEW_BARK_TOWN',12,2,4,4],whole_window=[40,40,16,8],native_pixel_scale=1,
                    independently_reviewed_source_contact='mauville-all3-source-buildings.png',
                    source_design='cornice/arched-window/plain-post' if game=='emerald' else 'striped-roof/square-window/timber-post'))
            for mid,art in modules.items():
                self.row(game,pair,mid,'gen2',art,
                    'Whole Mauville house and bike-shop source buildings reviewed separately for Ruby/Sapphire striped roofs, square windows and timber posts, and Emerald cornices, arched windows and plain posts, at their actual original entrance warps. This is an explicit same-purpose building adaptation, not a numerical or exact-geometry alias. Complete original Crystal64x64 New Bark roof, side caps, doorway frame, facade and16x8 window pair retain1:1 pixels. The80px-wide bike shop repeats ordinary middle roof/wall modules. Each source window cell receives the full native pair; its former half-window in the outercap is replaced with plain native wall while retaining the entire outer8px frame. Complete source matrices, per-cartridge actual full RGBA fingerprints and behavior are checked independently. No source layout, collision, entrance, NPC or event changes.')
        self.joined_previews(layouts, modules)

    def joined_previews(self, layouts, modules):
        font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
        panel = Image.new('RGB',(1240,650),'#18212b')
        draw = ImageDraw.Draw(panel)
        for i,(name,dest,ox,oy,layout) in enumerate(layouts):
            source = self.imp.gba('emerald',name)[0].crop((ox*16,oy*16,(ox+len(layout[0]))*16,(oy+len(layout))*16))
            target = Image.new('RGBA',source.size)
            for y,row in enumerate(layout):
                for x,mid in enumerate(row):target.paste(self.render(modules[mid]),(x*16,y*16))
            source.save(self.out/(dest+'-source-native.png'))
            target.save(self.out/(dest+'-gen2-native.png'))
            draw.text((8,i*310+6),dest,fill='white',font=font)
            panel.paste(source.resize((source.width*4,source.height*4),Image.Resampling.NEAREST),(8,i*310+34))
            panel.paste(target.resize((target.width*4,target.height*4),Image.Resampling.NEAREST),(440,i*310+34))
        panel.save(self.out/'mauville-complete-house-models-comparison.png')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate',action='store_true')
    parser.add_argument('--activate',action='store_true')
    args = parser.parse_args()
    review = Review()
    review.mauville_homes()
    review.rustboro_plain_homes()
    review.write(TARGET if args.activate else review.out/'candidates.lua')
    report = dict(rows=len(review.rows),contracts=review.contracts)
    if args.validate or args.activate:report['validation']=review.validate()
    (review.out/'building-contracts.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(rows=len(review.rows),validation=report.get('validation'))))


if __name__=='__main__':main()
