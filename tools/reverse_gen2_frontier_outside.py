"""Build reviewed Crystal exterior counterparts for the Emerald Battle Frontier."""
from pathlib import Path
import argparse
from collections import Counter
import json
import zlib

import catalog
import preview
from classic_geometry_review import art as geometry_art, source_under_frames
from gb_theme_animation import specification
from reverse_common import ROOT
from reverse_gen2_hoenn_outdoor_remaining import Review as Outdoor
from reverse_hoenn_review import ground_ref
from reverse_kanto_review import runs
from reverse_oldale_review import exterior

GAME='emerald'
EAST='general__battle_frontier_outside_east'
WEST='general__battle_frontier_outside_west'
GUARDS=Path(__file__).with_name('reverse_gen2_frontier_outside_guards.json')
OUTPUT=ROOT.parent/'.work/tileshift-v0360-frontier'
TARGET=ROOT/'mappings/reverse_gen2_frontier_outside.lua'

PAVERS={
    EAST:{949,950,957,958,965,966,973,974},
    WEST:{516,616,617,618,619,624,625,626,627},
}
PLAIN_LAWN={EAST:{513},WEST:set()}
FACILITIES={
    EAST:(('frontier_tower_full_stepped_glass_front','blue',((8,0,25,16),)),
          ('frontier_pyramid_complete_terraced_roof','wood',((51,5,66,16),)),
          ('frontier_palace_full_roof_colonnade_and_deck','wood',((33,23,46,32),)),
          ('frontier_palace_complete_garden_gate','gray',((35,36,44,41),)),
          ('frontier_arena_complete_pitched_roof_facade','wood',((40,49,52,57),)),
          ('frontier_complete_small_visitor_pavilions','red',((3,5,7,9),(7,24,14,29),(32,8,39,14),
              (63,27,68,33),(3,41,7,46),(13,48,17,53),(21,47,28,53))),
          ('frontier_complete_raised_flower_planters','red',((15,33,20,41),(18,42,27,47)))),
    WEST:(('frontier_dome_complete_ribbed_exterior','gray',((13,4,26,18),)),
          ('frontier_pike_complete_serpent_facade','serpent',((40,17,46,30),)),
          ('frontier_factory_complete_stacked_front','wood',((4,29,19,39),)),
          ('frontier_complete_entry_arches','gray',((24,46,29,61),)),
          ('frontier_complete_small_visitor_pavilions','red',((43,1,47,6),(3,17,8,22),(44,40,51,45),
              (52,40,56,45),(23,61,30,67))),
          ('frontier_complete_raised_flower_planters','red',((7,40,9,44),(14,40,16,44),(17,45,22,48),(31,45,41,48)))),
}
TOWER_BRICKS={737,738,745,746}
PIKE_PAVING={(165,165,165),(189,189,189),(214,214,214)}
REGIONAL={
    EAST:(
        ('frontier_complete_coastal_flags','flag','paving',{926,927,1013,1014,1015,1021}),
        ('frontier_complete_coastal_flags','flag','water',{1002,1003,1010,1011}),
        ('frontier_coastal_retaining_wall','gray','paving',{920,928,929,943,945,947,951,955,956,959,963,967,969,
             971,972,975,991}),
        ('frontier_sand_retaining_wall','gray','sand',{960,961,962,968,970,976,977,978,1017}),
        ('frontier_native_garden_rail','gray','lawn',{312,314,330,983}),
        ('frontier_native_planter_and_shrub','green','lawn',{6,515,864,865,872,873,866,867}),
        ('frontier_arena_upper_roof_and_flowers','wood','lawn',set(range(520,536))|{560,561,562,563,567,568,569,570,608,609,610}),
        ('frontier_palace_bay_deck_silhouette','wood','water',{631,640,641,642,647,678}),
        ('frontier_tower_full_entry_plinth','gray','lawn',{719,735,751,752,755,796,797,798,799}),
        ('frontier_tower_complete_entry_emblem','emblem','lawn',{756,757,758}),
        ('frontier_pavilion_curved_roof_edges','red','lawn',{859,861,893,895}),
        ('frontier_cliff_and_water_join','wood','water',{988,996}),
    ),
    WEST:(
        ('frontier_complete_coastal_flags','flag','paving',{926,927,973,982,983,1013,1014,1015,1021}),
        ('frontier_complete_coastal_flags','flag','water',{966,967,974,975}),
        ('frontier_coastal_retaining_wall','gray','paving',{554,555,599,607,613,614,615,620,621,623,628,629}),
        ('frontier_pier_brick_support','wood','water',{547,548,549,935}),
        ('frontier_pier_brick_support','wood','paving',{539,540,541}),
        ('frontier_native_planter_and_shrub','green','lawn',{5,6,1016}),
        ('frontier_native_garden_rail','gray','lawn',{308,314,559,678,744,756,765}),
        ('frontier_dome_complete_grass_corners','gray','lawn',{634,638,640,685,737,738,747,774}),
        ('frontier_factory_complete_coastal_roof','wood','water',{560,561,563,568,569,570,571,732,743,751,
             787,788,789,790,791,792,793,794,795,796,797,798,799,800,801,802,803,804,805,806,807}),
        ('frontier_pavilion_curved_roof_edges','red','water',{882,883,884}),
        ('frontier_pavilion_curved_roof_edges','red','lawn',{893,895}),
    ),
}
REGIONAL_KEYS={pair:{mid:(name,material,ground)for name,material,ground,ids in groups for mid in ids}
               for pair,groups in REGIONAL.items()}
OPEN_WATER={EAST:set(),WEST:{575}}
WATER_COLORS={(41,66,140,255),(58,82,156,255),(82,107,214,255),(107,132,214,255),
              (156,165,189,255),(173,197,230,255)}


def in_footprint(coords,bounds):
    return all(any(x0<=x<x1 and y0<=y<y1 for x0,y0,x1,y1 in bounds) for x,y in coords)


class Review(Outdoor):
    def __init__(self):
        super().__init__(OUTPUT)
        self.target_module=TARGET
        self.guards=json.loads(GUARDS.read_text(encoding='utf-8'))
        self.field=ground_ref(self,'gen2')
        self.street=self.raw_ref('TILESET_JOHTO',(6,)*4,'VIOLET_CITY')
        self.sand=self.raw_ref('TILESET_KANTO',(48,57,57,48),'PALLET_TOWN')
        self.water=self.gb_ref('crystal','UNION_CAVE_1F',15,0)
        self.water_program=specification(self.cache,self.water,'program')
        assert self.water_program
        maps=self.imp.table('crystal','maps')
        palettes=self.imp.table('crystal','palettes')
        self.colors={}
        for key,map_id,slot in (('gray','SAFFRON_CITY',0),('blue','OLIVINE_CITY',6),('red','PLAYERS_HOUSE_1F',1),
                               ('green','VIOLET_CITY',2)):
            self.colors[key]=sorted(map(tuple,preview.palette_set(palettes,maps[map_id],'DAY')[slot]),key=self.lightness)
        wood=self.locations['emerald','gen2','building__generic_building',547,None][2]['donor']
        used={p[:3]for p in self.gb_image(wood).get_flattened_data()if p[3]}
        choices=wood.get('palettes')or preview.palette_set(palettes,maps[wood['map']],'DAY')
        self.colors['wood']=sorted(map(tuple,next(colors for colors in choices if used<=set(map(tuple,colors)))),key=self.lightness)
        pavement=Counter(self.gb_image(self.street).get_flattened_data()).most_common(1)[0][0][:3]
        self.colors['serpent']=[*self.colors['blue'][:2],pavement,self.colors['wood'][-1]]
        self.colors['flag']=[*self.colors['gray'][:2],self.colors['wood'][-1],self.colors['gray'][-1]]
        self.colors['emblem']=[self.colors['gray'][2],self.colors['green'][2],self.colors['wood'][-1],self.colors['gray'][-1]]
        self.source_cache={}
        self.source_banks={}
        self.source_bank_hashes={}

    @staticmethod
    def lightness(rgb):
        return (54*rgb[0]+183*rgb[1]+19*rgb[2])/256

    def source_image(self,pair,mid):
        key=pair,mid
        if key not in self.source_cache:
            c=self.imp.cell_index(GAME)[key]
            ref=dict(game=GAME,tileset=pair,id=mid,hash=c['pixel_sha256'])
            self.source_cache[key]=preview.native_donor(self.cache,ref,self.packed)
        return self.source_cache[key]

    def lawn_colors(self,pair):
        colors=set(self.source_image(pair,1).get_flattened_data())
        if pair==WEST:
            colors.update(p for p in self.source_image(WEST,516).get_flattened_data()if p[1]>p[0]and p[1]>p[2])
        return colors

    def source_program(self,pair,mid):
        path=self.cache/GAME/'data/generated/gba/native'/pair
        if pair not in self.source_banks:
            manifest=catalog.read_lua(path/'anim_manifest.lua')
            self.source_banks[pair]=manifest['banks']
        def select(members,filename_key):
            banks=[b for b in self.source_banks[pair]if mid in b.get(members,())]
            if not banks:return None
            assert len(banks)==1 and banks[0]['kind']=='tiles',(pair,mid,members)
            bank=banks[0];filename=bank[filename_key];assert Path(filename).name==filename
            key=pair,filename
            if key not in self.source_bank_hashes:
                raw=(path/filename).read_bytes()
                expected=bank['frames']*len(bank[members])*256
                if len(raw)!=expected:raw=zlib.decompress(raw)
                assert len(raw)==expected
                self.source_bank_hashes[key]=catalog.sha(raw)
            return dict(bank=bank['name'],hash=self.source_bank_hashes[key])
        retained=select('overMids','overFile')
        spec=select('mids','file')
        if spec is None:return None,[],set(),retained
        spec['mode']='water_mask'
        frames,changed,_=source_under_frames(self.cache,GAME,pair,mid,self.packed,spec)
        return spec,frames,changed,retained

    def paving(self,pair,mid):
        src=self.source_image(pair,mid)
        lawn=self.lawn_colors(pair)
        # Mixed corners use the actual exterior outline of the original flagstones.
        outside=exterior(src,lawn)
        if not outside:return self.native(self.street,'reverse_gen2_frontier_complete_native_paving')
        mask=[(x,y)not in outside for y in range(16)for x in range(16)]
        parts=[dict(donor=self.street,srcX=part['x'],srcY=part['y'],**part)for part in runs(mask)]
        assert 0<len(parts)<=32
        return self.composite(self.field,parts,'reverse_gen2_frontier_complete_paving_lawn_join')

    def structure(self,pair,mid,name,material,backdrop='lawn'):
        self.source_image(pair,mid)
        mids,source_palette,planes=self.packed[GAME,pair]
        offset=mids.index(mid)*256
        palette=self.colors['wood'if pair==EAST and mid in TOWER_BRICKS else material]
        candidates={'lawn':(self.field,self.lawn_colors(pair)),
                    'paving':(self.street,set(self.source_image(pair,965 if pair==EAST else 616).get_flattened_data())),
                    'sand':(self.sand,{(214,197,115,255),(222,206,132,255),(239,222,148,255)}),
                    'water':(self.water,WATER_COLORS)}
        donor,outside_colors=candidates[backdrop]
        program,frames,changed,retained=self.source_program(pair,mid)
        if program and backdrop!='water':program['mode']='native_under'if changed else'static_equivalent'
        assert not retained or not program or program['mode']=='water_mask',(pair,mid)
        colors={};masks={}
        def color_pixels(image):
            for r,g,b,a in image.get_flattened_data():
                if a:
                    light=self.lightness((r,g,b))
                    level=sum(light>=cut for cut in (83,148,213))
                    if material=='serpent':
                        level=2 if (r,g,b)in PIKE_PAVING else 3 if r>180 and g>135 and b<96 else min(level,1)
                    if material=='flag':level=2 if r>180 and g>135 and b<125 else (3 if light>=213 else min(level,1))
                    if material=='emblem':level=1 if g>r and g>b else 2 if r>180 and g>135 and b<120 else 3 if light>215 else 0
                    colors[r,g,b]=palette[level]
        for layer,blob in planes.items():
            if layer=='over'and retained:continue
            image=catalog.rgba_native(blob[offset:offset+256],source_palette,layer!='under')
            outside=exterior(image,outside_colors)
            mask=''.join('1'if (x,y)in outside and image.getpixel((x,y))[3]==255
                         and not(program and program['mode']=='native_under'and layer in ('under','mid')and y*16+x in changed)else '0'
                         for y in range(16)for x in range(16))
            if '1'in mask:masks[layer]=mask
            color_pixels(image)
        if program and program['mode']=='native_under':
            for frame in frames:color_pixels(frame)
        ground=dict(donor=donor,masks=masks)if masks else None
        if ground and backdrop=='water':ground['animation']=self.water_program
        return geometry_art(self,GAME,pair,mid,name,palette,colors,ground=ground,
                            source_animation=program,native_over=retained)

    def build(self):
        for item in self.guards:
            pair,mid=item['pair'],item['mid']
            source=self.imp.cell_index(GAME)[pair,mid]
            assert source['pixel_sha256']==item['sourceHash'] and source['layer_sha256']==item['sourceLayers']
            assert source['behavior']==item['sourceBehavior']
            assert (GAME,'gen2',pair,mid,None)not in self.occupied
            for context in item['contexts']:
                layout=self.native_layout(GAME,context['map']);width=layout['width']
                assert layout['pair']==pair
                coords=[(i%width,i//width)for i,m in enumerate(layout['mids'])if m==mid]
                assert coords==[tuple(point)for point in context['coords']]
            kind=item['kind']
            if kind=='paving':
                assert mid in PAVERS[pair]
                art=self.paving(pair,mid)
                evidence='The full original Crystal flagstone continues the actual paved ground. The same selected lawn shows through the verified source outline.'
            elif kind=='lawn':
                assert mid in PLAIN_LAWN[pair]
                art=self.native(self.field,'reverse_gen2_frontier_native_lawn')
                evidence='This complete walking lawn cell uses the same imported Crystal lawn as its neighbors.'
            elif kind=='water':
                assert mid in OPEN_WATER[pair]
                part=dict(donor=self.water,x=0,y=0,w=16,h=16,animated=True)
                art=self.composite(None,[part],'reverse_gen2_frontier_native_open_water')
                art.update(animated=True,animation=self.water_program,animationCategory='water')
                evidence='The complete native Crystal water animation continues the actual open-water surface.'
            elif kind=='regional':
                name,material,backdrop=REGIONAL_KEYS[pair][mid]
                art=self.structure(pair,mid,name,material,backdrop)
                evidence='The complete regional feature preserves its exact placement, silhouette and priority. The selected Crystal material and backdrop join the checked source surroundings.'
            else:
                assert kind=='structure'
                name,material,bounds=item['feature']
                assert (name,material,tuple(map(tuple,bounds)))in FACILITIES[pair]
                assert in_footprint((point for context in item['contexts']for point in context['coords']),bounds)
                art=self.structure(pair,mid,name,material)
                evidence='The named Frontier structure retains its complete original silhouette, windows, roof lines and entrance. Its precise priority and exterior ground use the reviewed Crystal materials.'
            if art['kind']!='classic_native_geometry':art.setdefault('overMask','0'*256)
            row=self.row(GAME,pair,mid,'gen2',art,evidence+' Source coordinates, collision, warps and events remain intact.')
            row['frontierOutdoorReview']=dict(source_binding=catalog.sha(json.dumps(item,sort_keys=True,separators=(',',':')).encode()),pixel_scale=1)
        assert len(self.rows)==len(self.guards)

    def previews(self):
        shared={(r['game'],r['style'],r['tileset'],r['id'],r.get('map')):r
                for r in preview.read_reviewed(ROOT/'mappings/reverse_gen2_hoenn_outdoor_remaining.lua')
                if r['tileset'] in (EAST,WEST) and r['style']=='gen2'}
        assert not set(self.rows)&set(shared)
        for name,pair in (('EM_BATTLE_FRONTIER_OUTSIDE_EAST',EAST),('EM_BATTLE_FRONTIER_OUTSIDE_WEST',WEST)):
            image,cells,_,_=self.imp.gba(GAME,name)
            for cell in cells:
                key=GAME,'gen2',pair,cell['id'],None
                row=self.rows.get(key)or shared.get(key)
                if row is None and key in self.locations:row=self.locations[key][2]
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
    review.write(OUTPUT/'frontier-outside-candidate.lua')
    proof=review.validate() if args.validate else None
    if args.previews:review.previews()
    if args.activate:review.write(TARGET)
    print(json.dumps(dict(rows=len(review.rows),body_cells=sum(item['body_cells']for item in review.guards),proof=proof,activated=args.activate)))


if __name__=='__main__':main()
