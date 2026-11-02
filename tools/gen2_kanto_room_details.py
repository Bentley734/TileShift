"""Explicit complete-object details for the remaining compact GSC rooms."""
import copy
import json
from collections import deque
from pathlib import Path
from PIL import Image
import catalog
import preview
import gen2_extended_review as review
from johto_remaining_review import artwork
from native_room_parts import RoomParts

STEEL=[[240,248,240],[176,200,216],[96,120,152],[48,56,80]]
WOOD=[[248,232,176],[208,176,104],[144,104,56],[56,40,32]]
STONE=[[240,240,232],[184,192,184],[112,128,136],[48,56,72]]


def crop(art,sx,sy,w,h,x,y):
    if art.get('donor'):
        return [dict(donor=art['donor'],srcX=sx,srcY=sy,w=w,h=h,x=x,y=y)]
    out=[]
    # The target room supplies its floor. A template's former background
    # must never be inserted into a transparent native furniture corner.
    for part in art.get('parts',[]):
        px,py=part.get('x',0),part.get('y',0)
        ix,iy=max(sx,px),max(sy,py);ex,ey=min(sx+w,px+part.get('w',16)),min(sy+h,py+part.get('h',16))
        if ex>ix and ey>iy:
            p=copy.deepcopy(part);p.update(srcX=part.get('srcX',0)+ix-px,srcY=part.get('srcY',0)+iy-py,
                x=x+ix-sx,y=y+iy-sy,w=ex-ix,h=ey-iy);out.append(p)
    return out


class RoomDetails:
    def __init__(self,root,cache,imports,active,packed):
        self.root,self.cache,self.imports,self.packed=root,cache,imports,packed
        self.house=RoomParts(imports,'firered','FR_PLAYERS_HOUSE_1F')
        self.center=RoomParts(imports,'firered','FR_VIRIDIAN_CITY_POKEMON_CENTER_2F')
        self.tower=RoomParts(imports,'firered','FR_POKEMON_TOWER_2F')
        self.link=RoomParts(imports,'firered','FR_TRADE_CENTER')
        self.templates={}
        # Red's shared household furniture recipes are canonical and use
        # complete native foreground layers, without room-specific geometry.
        for row in active:
            if row.get('game')=='red' and row['role'].startswith('household_'):
                self.templates.setdefault(row['role'],row)
        for row in active:
            if row.get('game')=='crystal':self.templates.setdefault(row['role'],row)
        self.floor=self.house.ref(1);self.wall=self.house.ref(40)
        self.background_parts={('firered',pair,mid) for pair,mid in (
            ('house',1),('house',40),('player_house',1),('player_house',40),
            ('pewter_gym',704),('pewter_gym',705),('pewter_gym',715))}
        self.destination=root/'assets/third_party/gsc-room-geometry'
        self.destination.mkdir(parents=True,exist_ok=True)
        self.records={}
        self.tables=[artwork(self.templates['household_table_'+suffix]) for suffix in ('nw','ne','sw','se')]
        self.table_glyph={38:(0,0,0),39:(0,8,0),41:(1,8,0),54:(0,0,8),47:(0,8,8),57:(1,8,8),
            5:(2,0,0),21:(3,8,0),60:(2,0,8),58:(2,8,8),59:(3,8,8),51:(1,8,0)}
        self.book_table={((r['y']-3)*2+r['x']-3):artwork(r) for r in active
            if r.get('game')=='red' and r.get('map')=='CELADON_MANSION_ROOF_HOUSE'
            and r['role']=='gen1_complete_native_book_table' and 3<=r.get('x',-1)<=4 and 3<=r.get('y',-1)<=4}
        assert set(self.book_table)==set(range(4))

    def template(self,role,base=None):
        art=artwork(self.templates[role])
        if base is not None and art.get('base'):
            art['base']=copy.deepcopy(base)
            self.remove_background_parts(art)
        return art

    def remove_background_parts(self,art):
        if art.get('parts'):
            art['parts']=[p for p in art['parts'] if (p['donor'].get('game'),p['donor'].get('tileset'),p['donor'].get('id')) not in self.background_parts]
        return art

    def table(self,raw):
        parts=[]
        for q,tile in enumerate(raw):
            i,sx,sy=self.table_glyph[tile]
            parts+=crop(self.tables[i],sx,sy,8,8,q%2*8,q//2*8)
        assert 1<=len(parts)<=16
        return dict(kind='native_composite',base=self.floor,parts=parts)

    def fallback(self,game,name,source,colors=STEEL,backgrounds=None):
        """Keep source glyphs at 1:1; replace literal floor/wall 8px pieces."""
        palettes=copy.deepcopy(colors) if isinstance(colors[0][0],list) else [copy.deepcopy(colors)]*4
        palette_row=dict(game=game,style='gen3',tileset=source['tileset'],id=source['id'],quadrant=source['quadrant'],
            sourceHash=source['sourceHash'],sourceFiles=source['files'],kind='source_palette',sourceColors=palettes)
        image=preview.source_palette_image(self.cache,palette_row,self.packed)
        replaced=[]
        for q,tile in enumerate(source['tiles']):
            if backgrounds and tile in backgrounds:
                ref=backgrounds[tile];native=preview.native_donor(self.cache,ref,self.packed)
                x,y=q%2*8,q//2*8;image.paste(native.crop((x,y,x+8,y+8)),(x,y));replaced.append(q)
        if not replaced:
            return dict(kind='source_palette',sourceColors=palette_row['sourceColors'],
                credit='Original Pokemon Gold/Silver/Crystal / Game Freak; palette recolor only.',sourceUrl='https://github.com/pret/pokecrystal')
        path=self.destination/(game+'-'+source['sourceHash'][:20]+'-'+catalog.sha(image.tobytes())[:12]+'.png')
        image.save(path)
        self.records[path.relative_to(self.root).as_posix()]=dict(assetFileHash=catalog.sha(path.read_bytes()),
            origin='original_gsc_palette_recolor_with_native_background_pieces',game=game,tileset=source['tileset'],
            sourceHash=source['sourceHash'],sourceFiles=source['files'],sourceTileIds=source['tiles'],
            literal_background_quadrants=replaced,backgrounds={str(k):v for k,v in (backgrounds or {}).items()},
            retained_source_glyphs_at_pixel_scale=1,sourceColors=palette_row['sourceColors'])
        return dict(kind='third_party',asset=path.relative_to(self.root).as_posix(),assetFileHash=catalog.sha(path.read_bytes()),
            credit='Original Pokemon Gold/Silver/Crystal / Game Freak; original geometry recolored at 1:1 with native FRLG background pieces.',
            sourceUrl='https://github.com/pret/pokecrystal')

    def raw_at(self,game,data,definition,x,y):
        if not (0<=x<definition['width']*2 and 0<=y<definition['height']*2):return ()
        block=definition['blocks'][y//2*definition['width']+x//2]
        return tuple(review.cell_info(self.cache,game,data,definition['tileset'],block,y%2*2+x%2)['tiles'])

    def book_context(self,name,coordinates):
        return name=='TRAINER_HOUSE_1F' and any(7<=x<=8 and 9<=y<=10 for x,y in coordinates)

    def book_art(self,x,y):
        art=copy.deepcopy(self.book_table[(y-9)*2+x-7]);art['base']=self.floor
        return art

    def ornament(self,game,name,source,coordinates,data,definition):
        # Four source cells form one complete compact table ornament. Flood
        # only its original flat tabletop exterior in the whole 32px canvas,
        # so matching highlight shades enclosed by the outline stay intact.
        raw=tuple(source['tiles']);left=raw in ((47,34,47,82),(47,37,47,47));top=raw in ((47,34,47,82),(35,47,83,47))
        x,y=coordinates[0];ox,oy=x-(0 if left else 1),y-(0 if top else 1)
        neutral=Image.new('RGBA',(32,32));pieces=[]
        for dy in range(2):
            for dx in range(2):
                px,py=ox+dx,oy+dy;b=definition['blocks'][py//2*definition['width']+px//2];q=py%2*2+px%2
                c=review.cell_info(self.cache,game,data,definition['tileset'],b,q)
                image=preview.native_cell(data['sheets'][definition['tileset']],data['sets'][definition['tileset']],
                    catalog.lua_array(catalog.dict_at(data['sets'][definition['tileset']]['blocks'],b+1)),q)
                neutral.paste(image,(dx*16,dy*16));pieces.append(dict(cell=[px,py],sourceHash=c['sourceHash']))
        flat,_=catalog.gb_tile(data['sheets'][definition['tileset']],data['sets'][definition['tileset']],47)
        assert len(set(flat.get_flattened_data()))==1
        background=flat.getpixel((0,0));outside=set();queue=deque()
        for yy in range(32):
            for xx in range(32):
                if (xx in (0,31)or yy in(0,31))and neutral.getpixel((xx,yy))==background:outside.add((xx,yy));queue.append((xx,yy))
        while queue:
            xx,yy=queue.popleft()
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                px,py=xx+dx,yy+dy
                if 0<=px<32 and 0<=py<32 and (px,py)not in outside and neutral.getpixel((px,py))==background:
                    outside.add((px,py));queue.append((px,py))
        whole=Image.new('RGBA',(32,32))
        for yy in range(32):
            for xx in range(32):
                if (xx,yy)not in outside:
                    shade=round((255-neutral.getpixel((xx,yy))[0])*3/255);whole.putpixel((xx,yy),tuple(STONE[shade])+(255,))
        tile=whole.crop(((x-ox)*16,(y-oy)*16,(x-ox+1)*16,(y-oy+1)*16))
        base_art=self.table((47,47,47,47));background_image=preview.replacement_image(self.cache,base_art,self.packed,self.root)
        background_image.alpha_composite(tile)
        path=self.destination/(game+'-'+source['sourceHash'][:20]+'-table-ornament.png');background_image.save(path)
        self.records[path.relative_to(self.root).as_posix()]=dict(assetFileHash=catalog.sha(path.read_bytes()),
            origin='complete_original_gsc_table_ornament_palette_recolor_over_native_tabletop',game=game,map=name,
            sourceHash=source['sourceHash'],sourceFiles=source['files'],whole_original_envelope=[ox,oy,2,2],sourcePieces=pieces,
            removed_only_connected_flat_tabletop_exterior=True,retained_original_outline_at_pixel_scale=1,
            native_background=base_art)
        return dict(kind='third_party',asset=path.relative_to(self.root).as_posix(),assetFileHash=catalog.sha(path.read_bytes()),
            credit='Original Pokemon Gold/Silver/Crystal table ornament / Game Freak; complete 1:1 palette recolor over native FRLG tabletop.',sourceUrl='https://github.com/pret/pokecrystal'),dict(
            origin='original_gsc_palette_recolor',pixel_scale=1,whole_original_envelope=[ox,oy,2,2],sourcePieces=pieces,
            reason='Unique compact table ornament; retain every original outlined detail and replace only exterior tabletop material')

    def override(self,game,name,source,coordinates,data,definition):
        raw=tuple(source['tiles']);ts=source['tileset'];col=source['collision'];art=None;role=None;extra={}
        if ts=='TILESET_POKECENTER' and (name=='POKECENTER_2F' or name.endswith('_POKECENTER_2F_BETA') or name=='INDIGO_PLATEAU_POKECENTER_1F'):
            # Only the still-unmatched source-specific frames/devices reach
            # this handler. Native floors and ordinary furniture are handled
            # by exact reviewed recipes in the main room generator.
            allowed={1,2,3,6,7,8,9,10,11,13,14,15,17,19,22,23,24,25,31,32,33,34,35,36,38,39,40,41,45,46,50,51,52,53,54,55,56,57,58,59,62,64,66,67,70,71,73,75,82,83,86,87,92}
            if set(raw)<=allowed:
                art=self.fallback(game,name,source,backgrounds={1:self.center.ref(641),17:self.center.ref(641),2:self.center.ref(644)})
                role='original_geometry_link_service_frame_or_information_device'
                extra['originalGeometryFallback']=dict(origin='original_gsc_palette_recolor',pixel_scale=1,
                    reason='Unique compact GSC service/link booth columns, complete doorway caps or information devices; complete native frame has different height',
                    literalFloorTilesReplacedWithNative=[1,17],literalWallTilesReplacedWithNative=[2])
        elif ts=='TILESET_HOUSE':
            if self.book_context(name,coordinates):
                x,y=coordinates[0];art=self.book_art(x,y);role='complete_native_book_table'
            elif raw in ((47,34,47,82),(35,47,83,47),(47,37,47,47),(53,47,47,47)):
                art,extra['originalGeometryFallback']=self.ornament(game,name,source,coordinates,data,definition);role='complete_original_table_ornament_on_native_surface'
            elif raw==(76,77,92,93) and name=='TRAINER_HOUSE_1F':
                art=self.fallback(game,name,source,WOOD);role='complete_original_compact_staircase'
                extra['originalGeometryFallback']=dict(origin='original_gsc_palette_recolor',pixel_scale=1,reason='Complete compact original staircase')
            elif set(raw)<=set(self.table_glyph) and col in (7,144):
                art=self.table(raw);role='complete_modular_dining_table'
            elif raw==(2,3,18,19):
                variants=[]
                for x,y in coordinates:
                    neighbor=self.raw_at(game,data,definition,x-1,y)
                    right=bool(neighbor) and set(neighbor)<=set(self.table_glyph)|{34,35,74,82,83}
                    variants.append(dict(x=x,y=y,art=self.template('household_chair_right' if right else 'household_chair_left',self.floor)))
                art=variants[0]['art'];role='complete_dining_chair_context';extra['contextVariants']=variants
            elif raw==(68,69,0,0):art=self.template('johto_complete_native_region_map',self.wall);role='complete_native_wall_information_panel'
            elif name=='MR_FUJIS_HOUSE' and raw==(48,49,30,31):
                art=self.template('johto_domestic_complete_single_bay_bookcase_1',self.floor);role='complete_narrow_bookcase_foot'
            elif name=='SOUL_HOUSE' and raw in ((55,40,56,63),(55,40,56,78)):
                art=dict(kind='native_composite',base=self.floor,parts=[dict(donor=self.tower.ref(657),layers=['mid'],
                    layerHashes={'mid':self.imports.cell_index('firered')[self.tower.pair,657]['layer_sha256']['mid']},x=0,y=0,w=16,h=16)])
                role='complete_native_memorial_stone'
            elif name=='SOUL_HOUSE' and raw==(1,79,1,1):art=dict(kind='native',donor=self.floor);role='native_floor_below_complete_memorial'
        elif ts=='TILESET_PLAYERS_HOUSE':
            if raw==(68,68,68,68):art=dict(kind='native',donor=self.house.ref(0));role='outside_black_void'
            elif raw in ((78,79,94,95),(6,7,22,23),(51,50,28,64),(50,52,64,29)):
                if raw==(6,7,22,23):art=self.template('johto_house_complete_tv_base',self.floor);role='complete_native_tv_cabinet'
                elif raw==(78,79,94,95):
                    art=self.fallback(game,name,source,WOOD);role='complete_original_compact_staircase'
                    extra['originalGeometryFallback']=dict(origin='original_gsc_palette_recolor',pixel_scale=1,reason='Complete compact original staircase')
                else:
                    # Reuse the existing player-home modular table glyphs;
                    # these complete lower caps retain their legs and shadow.
                    art=self.template('household_table_sw' if raw[0]==51 else 'household_table_se',self.floor);role='complete_native_table_lower_cap'
            elif raw in ((22,23,24,25),(35,34,51,50),(34,36,50,52)):
                art=self.template('johto_house_complete_tv_base',self.floor) if raw[0]==22 else self.template('household_table_nw' if raw[0]==35 else 'household_table_ne',self.floor)
                role='complete_native_tv_cabinet' if raw[0]==22 else 'complete_native_table_upper_cap'
            elif raw in ((40,41,56,57),(72,73,88,89)):
                art=self.template('johto_lighthouse_complete_native_bed_head' if raw[0]==40 else 'johto_lighthouse_complete_native_bed_foot',self.floor);role='complete_native_bed_'+('head' if raw[0]==40 else 'foot')
            elif name=='REDS_HOUSE_2F' and raw==(74,75,90,91):
                art=self.fallback(game,name,source,STEEL);role='complete_original_handheld_game_system_and_cord'
                extra['originalGeometryFallback']=dict(origin='original_gsc_palette_recolor',pixel_scale=1,reason='Unique compact original handheld game system and complete cord')
        elif ts=='TILESET_GATE':
            if name=='VICTORY_ROAD_GATE' and raw==(2,3,18,19):
                art=self.template('johto_gate_complete_north_doorway');role='complete_north_gate_doorway'
            elif name in ('TIME_CAPSULE','TRADE_CENTER','COLOSSEUM'):
                if raw==(1,1,1,1):art=dict(kind='native',donor=self.link.ref(648));role='native_link_room_floor'
                elif raw==(17,17,1,1):art=dict(kind='native',donor=self.link.ref(711));role='native_link_room_wall_foot'
                elif raw==(92,93,16,16):art=dict(kind='native',donor=self.link.ref(703));role='complete_native_link_wall_panel'
                elif raw==(4,4,20,20):
                    variants=[]
                    for x,y in coordinates:
                        left=self.raw_at(game,data,definition,x-1,y)==raw
                        variants.append(dict(x=x,y=y,art=dict(kind='native',donor=self.link.ref(685 if left else 684))))
                    art=variants[0]['art'];extra['contextVariants']=variants;role='complete_native_link_exit_mat'
                elif set(raw)<={1,36,37,38,39,42,43,44,45,46,47,48,49,50,51,52,54,55,58,59,60,61,62,63,64,65,66,67,68,69,70,71}:
                    floor_color=list(preview.native_donor(self.cache,self.link.ref(648),self.packed).getpixel((8,8))[:3])
                    court=[floor_color,[192,216,224],[216,128,56],[72,96,120]]
                    device=[floor_color,STEEL[0],STEEL[2],STEEL[3]]
                    palettes=[court if tile in (1,52,66,67,68,69,70,71) else device for tile in raw]
                    art=self.fallback(game,name,source,palettes,backgrounds={1:self.link.ref(648)})
                    role='complete_original_link_court_console_and_seats'
                    extra['originalGeometryFallback']=dict(origin='original_gsc_palette_recolor',pixel_scale=1,
                        reason='Compact original octagonal court, Time Capsule/link console ports and seats have different native Gen3 footprints',
                        native_palette_reference=self.link.map,literalFloorTilesReplacedWithNative=[1])
        elif ts=='TILESET_TRADITIONAL_HOUSE' and name=='MOUNT_MOON_GIFT_SHOP' and raw==(17,17,17,17):
            dojo=RoomParts(self.imports,'firered','FR_SAFFRON_CITY_DOJO');art=dict(kind='native',donor=dojo.ref(705));role='complete_traditional_wall'
        if art:
            return dict(**art,role='kanto_room_'+role,reviewedNativeCounterpart=dict(role=role,pixel_scale=1,
                geometry='Complete native modules or explicitly labelled original-GSC geometry fallback'),**extra)
        return None

    def write_provenance(self):
        (self.destination/'provenance.json').write_text(json.dumps(dict(
            origin='Clearly labelled original-GSC source geometry recolors with exact native FRLG background pieces; no generated replacement designs.',
            sourceUrl='https://github.com/pret/pokecrystal',pixel_scale=1,assets=self.records),indent=2)+'\n')
