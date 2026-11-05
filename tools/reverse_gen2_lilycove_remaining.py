"""Build source-guarded Crystal Lilycove paths, fences and regional features."""
from pathlib import Path
import argparse
import json
import zlib

import catalog
import preview
from classic_geometry_review import art as geometry_art
from gb_theme_animation import specification
from johto_remaining_review import artwork
from reverse_common import ROOT
from reverse_gen2_hoenn_outdoor_remaining import Review as Outdoor
from reverse_hoenn_review import ground_ref
from reverse_kanto_review import runs
from reverse_oldale_review import exterior

PAIR='general__lilycove'
GUARDS=Path(__file__).with_name('reverse_gen2_lilycove_guards.json')
OUTPUT=ROOT.parent/'.work/tileshift-v0360-lilycove'
TARGET=ROOT/'mappings/reverse_gen2_lilycove_remaining.lua'

PATHS={554,555,556,562,563,564,570,571,572,817}
FENCES={592:657,593:657,594:657,600:313,602:650,789:657,790:650,798:657,833:657}
EDGES={808:'nw',809:'n',810:'ne',816:'w',818:'e',824:'s',825:'s',826:'se'}
ROOFS={586:558,595:557,596:559,603:565,604:567,605:557,606:558,607:559,613:565,614:566,615:567}
WATER_ROCKS={204:0,506:0,507:0,544:2,552:2,553:2,560:0,561:0,568:2,569:2,578:0,715:0}
OPEN_WATER={360,361}
RETIRED_CENTER_ROOF={619,620,621,622}
BUILDINGS={
    'lilycove_department_store_tiered_facade':{512,513,514,515,516,517,518,519,520,521,522,523,524,525,526,527,
        529,530,531,532,533,534,535,541,542,543,549,550,608,609,610,611,616,617,618,624,625,626,632,633,634,
        640,641,650,651,652},
    'lilycove_museum_complete_tall_facade':{726,727,749,750,757,758,759,763,764,765,766,767,768,769,770,
        771,772,773,774,775,779,780,781,782,783},
    'lilycove_contest_hall_framed_roof_and_front':{467,475,704,705,706,712,713,714,720,721,722,728,729,730,
        731,732,736,737,738,739,740},
    'lilycove_wooden_house_layered_facade':{646,654,655,659,660,661,662,663,667,668,669,670,671,675,677,678,
        683,685,686,687,695,703},
    'lilycove_whole_harbor_terminal':{743,840,841,842,843,844,845,846,847,848,849,850,851,852,854,856,857,858,
        859,860,861,862},
    'lilycove_joined_house_side_window':{579,580,587,588},
}
BUILDING_BY_MID={mid:name for name,mids in BUILDINGS.items()for mid in mids}
assert len(BUILDING_BY_MID)==sum(map(len,BUILDINGS.values()))
REGIONAL_FEATURES={
    'lilycove_joined_low_cliff_and_rock_corners':('rock',{68,143,149,150,239,262,642,647,653,691,692,693,694,717,794,799,803,807}),
    'lilycove_complete_secret_base_wall_and_cove':('rock',{416,680,681,682,688,689,690}),
    'lilycove_outdoor_post_silhouettes':('stone',{306,307}),
    'lilycove_route123_complete_tree_profiles':('green',{631,639}),
    'lilycove_department_store_stone_steps':('stone',{537,538,539,540,545,546,547,548}),
    'lilycove_harbor_lamp_and_anchor':('stone',{576,674}),
    'lilycove_safari_complete_boundary_posts':('stone',{784,792,793}),
    'lilycove_safari_cutaway_rock_and_field_seams':('rock',{786,787,788,791,797,800,801,802}),
    'lilycove_safari_gate_facade_and_entry':('stone',{804,805,806,813,819,821,822,823}),
    'lilycove_safari_gate_clipped_planting':('green',{795,796,815,834,835,836,837}),
}
REGIONAL_BY_MID={mid:(name,material)for name,(material,mids) in REGIONAL_FEATURES.items()for mid in mids}
assert len(REGIONAL_BY_MID)==sum(len(mids)for _,mids in REGIONAL_FEATURES.values())
HARBOR_WATER_EDGES={576,793,858,860}
SOURCE_WATER_COLORS={(82,107,214,255),(107,132,214,255)}


class Review(Outdoor):
    def __init__(self):
        super().__init__(OUTPUT)
        self.target_module=TARGET
        self.guard=json.loads(GUARDS.read_text(encoding='utf-8'))
        self.field=ground_ref(self,'gen2')
        self.street=self.raw_ref('TILESET_JOHTO',(6,)*4,'VIOLET_CITY')
        self.water=self.gb_ref('crystal','UNION_CAVE_1F',15,0)
        self.water_program=specification(self.cache,self.water,'program')
        assert self.water_program
        maps=self.imp.table('crystal','maps')
        palette_table=self.imp.table('crystal','palettes')
        self.feature_palettes={}
        palettes=(('stone','SAFFRON_CITY',0),('harbor','OLIVINE_CITY',6),
                  ('green','VIOLET_CITY',2))
        for key,map_id,slot in palettes:
            colors=preview.palette_set(palette_table,maps[map_id],'DAY')[slot]
            self.feature_palettes[key]=sorted(map(tuple,colors),key=self.luminance)
        wood_ref=self.locations['emerald','gen2','building__generic_building',547,None][2]['donor']
        for key,ref in (('rock',self.gb_ref('crystal','VIOLET_CITY',10,0)),('wood',wood_ref)):
            used={pixel[:3]for pixel in self.gb_image(ref).get_flattened_data()if pixel[3]}
            available=ref.get('palettes')or preview.palette_set(palette_table,maps[ref['map']],ref.get('daytime','DAY'))
            palette=next(colors for colors in available if used<=set(map(tuple,colors)))
            self.feature_palettes[key]=sorted(map(tuple,palette),key=self.luminance)

    @staticmethod
    def luminance(rgb):
        return (54*rgb[0]+183*rgb[1]+19*rgb[2])/256

    def source_shape(self, game, mid, source, name, material):
        palette=self.feature_palettes[material]
        if (game,PAIR) not in self.packed:
            preview.native_donor(self.cache,dict(game=game,tileset=PAIR,id=mid,hash=source['pixel_sha256']),self.packed)
        mids,native_colors,blobs=self.packed[game,PAIR]
        slot=mids.index(mid)
        grass_slot=mids.index(1)
        grass=catalog.rgba_native(blobs['under'][grass_slot*256:(grass_slot+1)*256],native_colors,False)
        water_edge=mid in HARBOR_WATER_EDGES
        source_water={
            576:{(156,165,189,255),(173,197,230,255),(107,132,214,255)},
            793:{(115,189,247,255)},
        }.get(mid,SOURCE_WATER_COLORS)
        exterior_colors=source_water if water_edge else set(grass.get_flattened_data())
        color_map={};masks={}
        for layer,blob in blobs.items():
            plane=catalog.rgba_native(blob[slot*256:(slot+1)*256],native_colors,layer!='under')
            outside=exterior(plane,exterior_colors)
            # A facade keeps its original silhouette and fixtures. Only grass
            # that reaches the edge and matches the source lawn is replaced.
            mask=''.join('1'if (x,y) in outside and plane.getpixel((x,y))[3]==255 else '0'
                         for y in range(16)for x in range(16))
            if '1' in mask:masks[layer]=mask
            for r,g,b,a in plane.get_flattened_data():
                if a:
                    light=self.luminance((r,g,b))
                    color_map[r,g,b]=palette[sum(light>=cut for cut in (84,153,219))]
        if water_edge:
            assert masks.get('under'),(game,mid,'Harbor edge lacks reviewed water pixels')
            path=self.cache/game/'data/generated/gba/native'/PAIR
            manifest=catalog.read_lua(path/'anim_manifest.lua')
            bank=next((b for b in manifest['banks']if b.get('kind')=='tiles' and mid in b.get('mids',())),None)
            source_animation=None
            if bank:
                assert Path(bank['file']).name==bank['file']
                raw=(path/bank['file']).read_bytes()
                length=bank['frames']*len(bank['mids'])*256
                if len(raw)!=length:raw=zlib.decompress(raw)
                assert len(raw)==length
                source_animation=dict(mode='water_mask',bank=bank['name'],hash=catalog.sha(raw))
            ground=dict(donor=self.water,masks=masks,animation=self.water_program)
            return geometry_art(self,game,PAIR,mid,name,palette,color_map,ground=ground,source_animation=source_animation)
        ground=dict(donor=self.field,masks=masks) if masks else None
        return geometry_art(self,game,PAIR,mid,name,palette,color_map,ground=ground)

    def surface(self, game, mid, source):
        if mid in PATHS:
            return self.native(self.street,'reverse_gen2_lilycove_native_walkway'), (
                'A complete native Crystal walking-pavement cell continues the connected path. '
                'The original paver mottling is part of this pavement material. Adjacent source lawn stays independent.')
        if mid in FENCES:
            art=self.active_art('emerald','general__mauville',FENCES[mid])
            art['base']=self.field
            art['role']='reverse_gen2_lilycove_complete_crystal_fence'
            return art, ('Complete original Crystal picket modules at the reviewed source fence positions, '
                         'with left, right and joined sections over the same surrounding Crystal lawn.')
        if mid in ROOFS:
            art=self.active_art(game,PAIR,ROOFS[mid])
            art['role']='reverse_gen2_lilycove_native_house_roof_module'
            return art, ('The complete Crystal blue roof cap or repeat module continues the existing Lilycove roof. '
                         'The original-scale left/right boundary and lower eave remain distinct from the plain interior.')
        if mid in RETIRED_CENTER_ROOF:
            art=self.active_art(game,PAIR,124)
            art['role']='reverse_gen2_lilycove_restore_continuous_cliff_above_center'
            return art, ('The complete Crystal Pokemon Center roof already starts on the next row. '
                         'The continuous adjacent cliff front replaces the former dome pieces above it.')
        if mid in BUILDING_BY_MID:
            name=BUILDING_BY_MID[mid]
            material={'lilycove_wooden_house_layered_facade':'wood','lilycove_whole_harbor_terminal':'harbor'}.get(name,'stone')
            return self.source_shape(game,mid,source,name,material), ('A complete named Lilycove building has a distinctive source layout. '
                'Its window panels, door frames, tiered roof, signs and exterior silhouette remain in their original positions. '
                'The original geometry and priority use a checked native Crystal material palette, with the same grass outside the building.')
        if mid in REGIONAL_BY_MID:
            name,material=REGIONAL_BY_MID[mid]
            return self.source_shape(game,mid,source,name,material), ('This complete named route or coastal feature keeps '
                'the exact native outline, priority and orientation. Native Crystal material colors and the selected ground '
                'cover the visible feature and its source boundary without changing the map geometry or behavior.')
        if mid in OPEN_WATER:
            part=dict(donor=self.water,x=0,y=0,w=16,h=16,animated=True)
            art=self.composite(None,[part],'reverse_gen2_lilycove_open_surf_water')
            art.update(animated=True,animation=self.water_program,animationCategory='water')
            return art, 'The complete moving Crystal water joins both sides of this reviewed open-water surf cell.'
        if mid in WATER_ROCKS:
            ref=dict(game=game,tileset=PAIR,id=mid,hash=source['pixel_sha256'])
            native=preview.native_donor(self.cache,ref,self.packed)
            rock=[r>b for r,_,b,a in native.get_flattened_data() if a]
            assert len(rock)==256 and 0<sum(rock)<256
            donor=self.gb_ref('crystal','VIOLET_CITY',10,WATER_ROCKS[mid])
            parts=[dict(donor=self.water,x=0,y=0,w=16,h=16,animated=True)]
            parts.extend(dict(donor=donor,srcX=part['x'],srcY=part['y'],**part)for part in runs(rock))
            assert len(parts)<=32
            art=self.composite(None,parts,'reverse_gen2_lilycove_coast_cliff_with_transparent_corner')
            art.update(animated=True,animation=self.water_program,animationCategory='water')
            return art, ('The original rock contour uses the adjoining Crystal cliff material. '
                         'Only the verified blue water and gray surf pixels receive the selected native Crystal water program.')
        direction=EDGES[mid]
        role='reverse_gen2_hoenn_native_city_curb_'+direction+'_paving'
        art=artwork(next(row for row in self.prior if row['style']=='gen2' and row.get('role')==role))
        art['base']=self.street
        art['role']='reverse_gen2_lilycove_native_raised_path_'+direction
        return art, ('The complete native Crystal raised-path edge retains its straight direction and '
                     'joins the selected paved material at the actual source boundary.')

    def build(self):
        for item in self.guard:
            game,mid=item['game'],item['mid']
            source=self.imp.cell_index(game)[PAIR,mid]
            assert source['pixel_sha256']==item['sourceHash'] and source['layer_sha256']==item['sourceLayers']
            assert source['behavior']==item['sourceBehavior']
            assert (game,'gen2',PAIR,mid,None) not in self.occupied
            for context in item['contexts']:
                layout=self.native_layout(game,context['map'])
                assert layout['pair']==PAIR and layout['mids'].count(mid)==context['cells']
            art,evidence=self.surface(game,mid,source)
            if art['kind']!='classic_native_geometry':art.setdefault('overMask','0'*256)
            row=self.row(game,PAIR,mid,'gen2',art,evidence+
                         ' The checked source art, actual map placement, collision and movement are preserved.')
            row['lilycoveReview']=dict(source_binding=catalog.sha(json.dumps(item,sort_keys=True,separators=(',',':')).encode()),pixel_scale=1)
        assert len(self.rows)==len(self.guard)

    def previews(self):
        shared={
            (row['game'],row['style'],row['tileset'],row['id'],row.get('map')):row
            for row in preview.read_reviewed(ROOT/'mappings/reverse_gen2_hoenn_outdoor_remaining.lua')
            if row['tileset']==PAIR and row['style']=='gen2'
        }
        assert not set(self.rows)&set(shared)
        for name in ('EM_LILYCOVE_CITY','EM_ROUTE121','EM_SAFARI_ZONE_SOUTHEAST'):
            game='emerald'
            image,cells,_,_=self.imp.gba(game,name)
            for cell in cells:
                mid=cell['id'];key=game,'gen2',PAIR,mid,None
                row=self.rows.get(key)or shared.get(key)
                if row is None and key in self.locations:
                    row=self.locations[key][2]
                if row is not None:
                    art=self.render(row)
                    for x,y in cell['coordinates']:image.paste(art,(x*16,y*16))
            image.save(OUTPUT/(name+'-review.png'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate',action='store_true')
    parser.add_argument('--activate',action='store_true')
    parser.add_argument('--previews',action='store_true')
    args=parser.parse_args()
    assert not args.activate or args.validate
    review=Review();review.build()
    review.write(OUTPUT/'lilycove-candidate.lua')
    proof=review.validate() if args.validate else None
    if args.previews:review.previews()
    if args.activate:review.write(TARGET)
    print(json.dumps(dict(rows=len(review.rows),body_cells=sum(item['body_cells']for item in review.guard),proof=proof,activated=args.activate)))


if __name__=='__main__':main()
