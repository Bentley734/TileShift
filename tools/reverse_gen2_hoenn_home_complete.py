"""Whole native furnishings and explicitly reviewed Hoenn home features.

The bounded source contract is independent of aliases in other interior banks.
Native counterparts are used at original pixel scale; unique rugs retain their
complete outlines and motifs over the already selected matching native floor.
"""
from pathlib import Path
import argparse,copy,json,re
from PIL import Image
import catalog,preview
from reverse_common import ReverseReview,ROOT
from reverse_gen2_hoenn_interior_finish import Review as Modules
from classic_geometry_review import art as geometry_art
from reverse_kanto_review import runs

PAIR='building__generic_building';GAMES=('ruby','sapphire','emerald')
OUT=ROOT.parent/'.work/tileshift-v0360-homes'
TARGET=ROOT/'mappings/reverse_gen2_hoenn_home_complete.lua'
GUARDS=ROOT/'tools/reverse_gen2_hoenn_home_guards.json'

class Review(Modules):
    def __init__(self):
        ReverseReview.__init__(self,'gen2-hoenn-home-complete',GAMES);self.out=OUT;OUT.mkdir(exist_ok=True)
        guards=json.loads(GUARDS.read_text());self.reserved={};self.contracts=[];self.prior={};self.source_cache={}
        for item in guards:
            key=item['game'],item['mid'];cell=self.imp.cell_index(item['game'])[PAIR,item['mid']]
            assert cell['pixel_sha256']==item['sourceHash']and cell['layer_sha256']==item['sourceLayers']and cell['behavior']==item['sourceBehavior']
            self.reserved[key]=item
        mods=list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(ROOT/'main.lua').read_text())))
        mods+=['mappings/reverse_gen2_hoenn_interiors_completion.lua']
        for path in dict.fromkeys(mods):
            if ROOT/path==TARGET:continue
            for row in preview.read_reviewed(ROOT/path):
                if row['game']in GAMES and row['style']=='gen2'and row['tileset']==PAIR:
                    key=row['game'],row['id'];assert key not in self.prior;self.prior[key]=row
        assert not set(self.reserved).intersection(self.prior),'Reserved household keys have another owner'
        self.wood=copy.deepcopy(self.prior['emerald',547]['donor'])
        self.house=copy.deepcopy(self.prior['emerald',553]['donor'])
        self.wall=copy.deepcopy(self.prior['emerald',517]['donor'])
        self.stone=copy.deepcopy(self.prior['emerald',812]['donor'])
        self.sootopolis_floor=copy.deepcopy(self.prior['emerald',1022]['donor'])

    def source(self,game,mid):
        key=game,mid
        if key not in self.source_cache:
            c=self.imp.cell_index(game)[PAIR,mid]
            self.source_cache[key]=preview.native_donor(self.cache,dict(game=game,tileset=PAIR,id=mid,hash=c['pixel_sha256']),self.packed)
        return self.source_cache[key]

    def add(self,game,pair,mid,art,evidence):
        assert pair==PAIR
        if(game,mid)not in self.reserved:return
        item=self.reserved[game,mid]
        row=self.row(game,pair,mid,'gen2',self.prepare_art(game,pair,mid,art),evidence+
            ' This complete household feature and its actual room contexts were independently reviewed. The literal source RGB, all native planes and behavior are frozen per cartridge; native entrances, map layout, interaction and collision remain unchanged.')
        row['hoennHomeCompletion']=dict(source_binding=catalog.sha(json.dumps(item,sort_keys=True,separators=(',',':')).encode()),pixel_scale=1)

    def aliases(self,pair,mid,art,evidence):
        # The source contacts include each cartridge independently. No MID-only
        # identity is inferred; the whole semantic source family is explicit.
        for game in GAMES:
            if(game,mid)in self.reserved:self.add(game,pair,mid,art,evidence)

    def furniture(self):
        for layout in ([[586,587],[594,595]],[[588,589],[596,597]],[[872,873],[880,881]],[[874,875],[882,883]]):
            self.object_family(PAIR,layout,'GUIDE_GENTS_HOUSE',(3,3),self.house,self.wood if layout[0][0]<800 else self.stone,
                'complete native household dining table',source_bounds=[0,0,32,32],foot_anchor=31)
        self.object_family(PAIR,[[938,939],[946,947]],'GUIDE_GENTS_HOUSE',(3,3),self.house,self.house,
            'complete native maritime dining table',source_bounds=[0,0,32,32],foot_anchor=31)
        columns=list(range(16))+list(range(8,24))+list(range(16,32))
        self.object_family(PAIR,[[894,895,910],[902,903,911]],'GUIDE_GENTS_HOUSE',(3,3),self.house,self.stone,
            'complete native wide apartment dining table',column_pixels=columns,
            source_bounds=[0,0,48,32],foot_anchor=31)
        self.object_family(PAIR,[[1011,1012],[1019,1020]],'GUIDE_GENTS_HOUSE',(3,3),self.house,self.sootopolis_floor,
            'complete native Sootopolis dining table',source_bounds=[0,0,32,32],foot_anchor=31)
        self.object_family(PAIR,[[989,990],[997,991]],'GUIDE_GENTS_HOUSE',(3,3),self.house,self.sootopolis_floor,
            'complete native Sootopolis side dining table',source_bounds=[0,0,32,32],foot_anchor=31)
        self.object_family(PAIR,[[590,607],[598,599]],'GUIDE_GENTS_HOUSE',(3,3),self.house,self.house,
            'complete native plain dining table',source_bounds=[0,0,32,32],foot_anchor=31)
        self.object_family(PAIR,[[601]],'GUIDE_GENTS_HOUSE',(2,3),self.house,self.house,
            'complete native padded household stool',source_bounds=[0,0,16,16],foot_anchor=15)
        self.object_family(PAIR,[[635,636]],'GUIDE_GENTS_HOUSE',(3,3),self.house,self.wood,
            'native alternate top for the already complete dining table frame',source_bounds=[0,0,32,16],foot_anchor=15,floor_zones=[])
        for game in GAMES:
            for mid,source_mid,direction in ((733,555,'east'),(734,556,'west')):
                if(game,mid)not in self.reserved:continue
                witness=self.prior[game,source_mid]
                assert witness['role']=='reverse_gen2_complete_backed_chair_'+direction
                parts=copy.deepcopy(witness['parts'])
                occupied={y*16+x for part in parts for y in range(part['y'],part['y']+part['h'])for x in range(part['x'],part['x']+part['w'])}
                art=self.composite(self.sootopolis_floor,parts,'reverse_gen2_complete_native_sootopolis_chair_'+direction)
                art['_objectMask']=''.join('1'if i in occupied else'0'for i in range(256))
                self.add(game,PAIR,mid,art,'Whole reviewed native-module side chair at the actual source position. The complete backrest faces its dining table, with all legs and original native stone floor around it.')

    def sofas(self):
        donor_map='CHERRYGROVE_POKECENTER_1F'
        seat_floor=self.gb_at('crystal',donor_map,4,5)
        for layout,floor in (([[643,644],[651,652]],self.wood),
                             ([[658,659],[666,667]],self.stone),
                             ([[852,823,853],[860,831,861]],self.stone)):
            width=len(layout[0])*16
            columns=list(range(8))+list(range(4,12))*((width-16)//8)+list(range(8,16))
            self.object_family(PAIR,layout,donor_map,(7,5),seat_floor,floor,
                'complete native padded household sofa',column_pixels=columns,row_pixels=[None]*8+list(range(16))+[None]*8,
                preserve_rects=[(2,8,width-4,1),(1,9,width-2,1),(0,10,width,14)],
                background_bands=[(0,16,self.wall),(16,32,floor)],source_bounds=[0,8,width,16],foot_anchor=23)

    def rugs(self):
        # Crystal's complete outer4px entry-rug frame surrounds the actual
        # native household carpet. Plain woven bands extend the frame at1:1;
        # its corners and unique outside border remain intact. Using the same
        # native center also joins the existing reviewed574/925 carpet cells.
        xs=list(range(16))+list(range(8,24))+list(range(16,32))
        ys=list(range(8))+list(range(4,12))*4+list(range(8,16))
        for layout,base in (([[565,566,567],[573,574,575],[581,582,583]],self.wood),
                            ([[891,892,893],[899,900,901],[907,908,909]],self.stone),
                            ([[916,917,918],[924,925,926],[932,933,934]],self.wood)):
            center=[]
            for y in range(4,44,16):
                for x in range(4,44,16):
                    width,height=min(16,44-x),min(16,44-y)
                    center.append(dict(donor=self.house,srcX=0,srcY=0,x=x,y=y,w=width,h=height))
            self.object_family(PAIR,layout,'GUIDE_GENTS_HOUSE',(2,7),self.house,base,
                'complete native framed household area rug',row_pixels=ys,column_pixels=xs,
                preserve_rects=[(3,2,42,44)],source_bounds=[0,0,48,48],foot_anchor=47,additional_parts=center)
        for layout,base in (([[520,521]],self.wood),([[844,845]],self.stone),([[940,941]],self.wood)):
            self.object_family(PAIR,layout,'GUIDE_GENTS_HOUSE',(2,7),self.house,base,
                'complete native household entry rug',source_bounds=[0,0,32,16],foot_anchor=15)
        self.object_family(PAIR,[[980,981]],'GUIDE_GENTS_HOUSE',(2,7),self.house,self.wood,
            'complete native treehouse entry rug',source_bounds=[0,0,32,16],foot_anchor=15)

    def beds(self):
        # This Emerald apartment bed has three source columns because its old
        # feet overlap the rug. The complete native16x32 bed stays centered;
        # all six source cells use the same native carpet beneath it.
        for mid in (570,801,815,900,950,1021):self.rows.pop(('emerald','gen2',PAIR,mid,None),None)
        self.object_family(PAIR,[[570,801,815],[900,950,1021]],'FAST_SHIP_CABINS_NNW_NNE_NE',(7,1),
            self.gb_at('crystal','FAST_SHIP_CABINS_NNW_NNE_NE',0,5),self.house,
            'complete native apartment bed with cleared old side feet',column_pixels=[None]*16+list(range(16))+[None]*16,
            source_bounds=[10,0,24,32],foot_anchor=31,only_game='emerald')
        self.object_family(PAIR,[[602,603],[610,611]],'FAST_SHIP_CABINS_NNW_NNE_NE',(7,1),
            self.gb_at('crystal','FAST_SHIP_CABINS_NNW_NNE_NE',0,5),self.wood,
            'complete native Mossdeep bed centered in the original wide footprint',
            column_pixels=[None]*8+list(range(16))+[None]*8,
            source_bounds=[0,0,32,32],foot_anchor=31)
        for game in GAMES:
            installed=[self.prior.get((game,mid))for mid in (723,731)]
            if all(row and 'complete_single_bed'in row['role']for row in installed):
                for mid in (722,730):
                    self.add(game,PAIR,mid,self.native(self.wood,'reverse_gen2_home_clear_retired_bed_side'),
                        'The whole native Crystal bed is already present at the original position. This adjacent source strip held only the wider Gen3 bed side, so it now joins the selected native timber floor.')

    def kitchens(self):
        donor_map='PLAYERS_HOUSE_1F'
        timber_wall=self.gb_at('crystal',donor_map,6,0)
        kitchen_floor=self.gb_at('crystal',donor_map,5,2)
        fridge_top=self.gb_image(self.gb_at('crystal',donor_map,2,0)).crop((0,0,16,8))
        assert set(fridge_top.get_flattened_data())<=set(self.gb_image(timber_wall).get_flattened_data()),'Refrigerator art starts above the reviewed empty wall'
        kitchens=(
            ([[620,621],[628,629]],[[632],[640],[648]],self.wall,self.wood),
            ([[952,953],[960,961]],[[919],[927],[935]],timber_wall,self.wood),
            ([[854,855],[862,863]],[[888],[896],[904]],self.wall,self.stone),
        )
        for sink,fridge,wall,floor in kitchens:
            self.object_family(PAIR,sink,donor_map,(0,1),kitchen_floor,floor,
                'complete native stove and sink cabinet run',row_pixels=[None]*16+list(range(16)),
                preserve_rects=[(0,16,32,16)],background_bands=[(0,16,wall),(16,32,floor)],
                source_bounds=[0,0,32,32],foot_anchor=31)
            self.object_family(PAIR,fridge,donor_map,(2,0),timber_wall,floor,
                'complete native kitchen refrigerator',row_pixels=[None]*24+list(range(8,32)),
                preserve_rects=[(1,24,14,24)],background_bands=[(0,24,wall),(24,48,floor)],
                source_bounds=[0,8,16,40],foot_anchor=47)
        self.object_family(PAIR,[[699,700],[707,708]],donor_map,(0,1),kitchen_floor,self.sootopolis_floor,
            'complete native Sootopolis stove and sink',row_pixels=[None]*8+list(range(16))+[None]*8,
            preserve_rects=[(0,8,32,16)],background_bands=[(0,16,self.wall),(16,32,self.sootopolis_floor)],
            source_bounds=[0,8,32,16],foot_anchor=23)
        for layout,floor in (([[688],[696],[704]],self.house),([[701],[709]],self.sootopolis_floor)):
            count=len(layout)*16
            self.object_family(PAIR,layout,donor_map,(2,0),timber_wall,floor,
                'complete native regional kitchen refrigerator',row_pixels=[None]*8+list(range(8,32))+[None]*(count-32),
                preserve_rects=[(1,8,14,24)],background_bands=[(0,16,self.wall),(16,count,floor)],
                source_bounds=[0,0,16,count],foot_anchor=31)
        cabinets=(
            ([[622,623],[630,631],[638,639]],self.wall,self.wood),
            ([[633,634],[641,642],[649,650]],self.wall,self.wood),
            ([[689,690],[697,698],[705,706]],self.wall,self.house),
            ([[948,949],[956,957],[964,965]],timber_wall,self.wood),
            ([[889,890],[897,898],[905,906]],self.wall,self.stone),
        )
        for layout,wall,floor in cabinets:
            self.object_family(PAIR,layout,'GUIDE_GENTS_HOUSE',(0,0),self.house,floor,
                'complete native two-bay household storage cabinet',row_pixels=[None]*8+list(range(32))+[None]*8,
                background_bands=[(0,8,wall),(8,48,floor)],source_bounds=[0,8,32,32],foot_anchor=39)

    def windows_and_storage(self):
        for layout in ([[518],[526]],[[519],[527]],[[535],[543]],[[825],[833]],[[826],[834]],[[1009],[1017]],[[1010],[1018]]):
            self.object_family(PAIR,layout,'GUIDE_GENTS_HOUSE',(5,0),self.wall,self.wall,
                'complete native household wall window',row_pixels=[None]*8+list(range(16))+[None]*8,
                preserve_rects=[(0,8,16,16)],source_bounds=[0,8,16,16],foot_anchor=23)
        for top,bottom,base in ((616,624,self.wood),(617,625,self.wood),(672,680,self.house),(673,681,self.house),
                                (717,725,self.sootopolis_floor),(840,848,self.stone),(841,849,self.stone),
                                (936,944,self.wood),(937,945,self.wood),(995,1003,self.wood),(996,1004,self.wood)):
            self.object_family(PAIR,[[top],[bottom]],'ELMS_LAB',(6,0),self.house,base,
                'complete native household single-bay storage cabinet',preserve_rects=[(0,0,16,32)],
                source_bounds=[0,0,16,32],foot_anchor=31)
        # The television itself is already a complete reviewed native module;
        # these are its separately reviewed plain cap and cabinet front.
        for mid in (534,560):
            self.aliases(PAIR,mid,self.native(self.wall,'reverse_gen2_home_tv_plain_wall_cap'),'Plain wall above the already complete native television; its old Gen3 projecting hood is removed with no duplicate frame.')
        for mid in (646,647,870,871):
            self.aliases(PAIR,mid,self.native(self.wall,'reverse_gen2_home_glazed_cabinet_wall_cap'),
                'Unadorned wall above the complete reviewed native glazed cabinet/window, replacing the old regional top trim without a second frame.')
        for mid in (568,576,662,663,693,886,887,979):
            self.aliases(PAIR,mid,self.native(self.gb_at('crystal','ELMS_LAB',6,1),'reverse_gen2_home_tv_storage_front'),
                'Complete native sixteen-pixel storage-door/front module beneath the already complete native screen or glazed household cabinet. Retains the whole original panel and lower frame without reusing a screen.')

    def surfaces(self):
        for mids,ref,material in (([548,549,557,559,929,931],self.wood,'timber_floor'),
                                  ([811],self.stone,'apartment_floor'),
                                  ([714,715,832,1016],self.wall,'unadorned_wall')):
            for mid in mids:
                self.aliases(PAIR,mid,self.native(ref,'reverse_gen2_home_native_'+material),
                    'Individually reviewed full plain/shaded walking floor or unadorned wall in the actual household. The native Crystal material continues the selected adjoining cells. Functional marks, railings, furnishings and actual doors are excluded.')

    @staticmethod
    def brightness(rgb):
        return (54*rgb[0]+183*rgb[1]+19*rgb[2])/256

    def native_palette(self,ref):
        context=self.imp.table('crystal','maps')[ref['map']]
        palettes=ref.get('palettes')or preview.palette_set(self.imp.table('crystal','palettes'),context,ref.get('daytime','DAY'))
        pixels={p[:3]for p in self.gb_image(ref).get_flattened_data()if p[3]}
        selected=next([tuple(p)for p in colors]for colors in palettes if pixels<=set(map(tuple,colors)))
        assert len(set(selected))==4
        return sorted(selected,key=self.brightness)

    def source_planes(self,game,mid):
        self.source(game,mid)
        mids,palette,planes=self.packed[game,PAIR];slot=mids.index(mid)
        return {name:catalog.rgba_native(blob[slot*256:(slot+1)*256],palette,name!='under')for name,blob in planes.items()}

    def source_colors(self,game,mid):
        return {pixel[:3]for image in self.source_planes(game,mid).values()for pixel in image.get_flattened_data()if pixel[3]}

    def connected_floor(self,game,mid,floor_mids,donor):
        floors=[list(self.source(game,floor).get_flattened_data())for floor in floor_mids]
        masks={}
        for name,image in self.source_planes(game,mid).items():
            matching={i for i,pixel in enumerate(image.get_flattened_data())if pixel[3]==255 and any(pixel==floor[i]for floor in floors)}
            exterior={i for i in matching if i%16 in(0,15)or i//16 in(0,15)}
            pending=list(exterior)
            while pending:
                index=pending.pop();x,y=index%16,index//16
                for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                    if not(0<=nx<16 and 0<=ny<16):continue
                    neighbor=ny*16+nx
                    if neighbor in matching and neighbor not in exterior:
                        exterior.add(neighbor);pending.append(neighbor)
            if exterior:masks[name]=''.join('1'if i in exterior else'0'for i in range(256))
        return dict(donor=donor,masks=masks)if masks else None

    def fixed_structures(self):
        gray=self.native_palette(self.gb_at('crystal','ELMS_LAB',5,4))
        clay=self.native_palette(self.gb_at('crystal','PLAYERS_HOUSE_1F',6,0))
        timber=[(0,0,0)]+self.native_palette(self.wood)[1:]
        groups=(
            ('hoenn_home_full_partition_post',(760,768,776,784),gray,(547,569),self.wood,(95,170,227)),
            ('rustboro_complete_apartment_stairwell_frame',(808,809,810,816,818,858,866),gray,(811,812),self.stone,(95,170,227)),
            ('rustboro_joined_apartment_partitions',(669,670,671,727,735,743,798),gray,(811,812),self.stone,(95,170,227)),
            ('hoenn_joined_low_public_room_partitions',(762,763,764,770,771,772,777,778,780),gray,(547,548,549,569),self.wood,(95,170,227)),
            ('pacifidlog_complete_maritime_urn',(951,),clay,(929,931),self.wood,(83,139,192)),
            ('hoenn_complete_household_clay_urns',(691,692),clay,(545,553),self.house,(83,139,192)),
            ('hoenn_traditional_joined_wall_posts',(739,740,747,748,755,756),clay,(545,553),self.house,(83,139,192)),
            ('hoenn_cutaway_house_front_fascia',(792,800),clay,(545,553),self.house,(83,139,192)),
            ('hoenn_complete_indoor_stairwell_trim',(514,515,516,522,524,530,531,532,538,539,540,609),gray,(533,541,517,525),self.wall,(95,170,227)),
            ('hoenn_complete_archaeology_tunnel_entrance',(749,750,751,757,758,759),[(0,0,0)]+clay[1:],(533,541),self.wall,(88,139,192)),
            ('hoenn_excavation_dust_at_tunnel_foot',(765,766,767),clay,(545,553),self.house,(83,139,192)),
            ('hoenn_complete_fossil_exhibit_cabinet',(774,775,782,783),clay,(545,553),self.house,(83,139,192)),
            ('hoenn_framed_coastal_house_pictures',(600,608,615,637,645),clay,(517,525,533,541,1008,1016),self.wall,(83,139,192)),
            ('rustboro_complete_low_storage_chest',(842,843,850,851),gray,(811,812),self.stone,(95,170,227)),
            ('rustboro_complete_television_stand',(822,),gray,(811,812),self.stone,(95,170,227)),
            ('stevens_complete_glazed_specimen_displays',(859,867),gray,(547,569),self.wood,(95,170,227)),
            ('stevens_complete_tabletop_specimen',(721,),clay,(547,569),self.wood,(83,139,192)),
            ('pacifidlog_complete_media_cabinet_feet',(923,962,963),timber,(929,931),self.wood,(81,151,220)),
            ('fortree_complete_decoration_shop_display_tables',(982,983,1013,1014,1015),timber,(985,),self.wood,(81,151,220)),
        )
        for name,ids,palette,floor_mids,floor,thresholds in groups:
            for game in GAMES:
                for mid in ids:
                    if(game,mid)not in self.reserved:continue
                    colors={rgb:palette[sum(self.brightness(rgb)>=cut for cut in thresholds)]for rgb in self.source_colors(game,mid)}
                    ground=self.connected_floor(game,mid,floor_mids,floor)
                    art=geometry_art(self,game,PAIR,mid,name,palette,colors,ground=ground)
                    self.add(game,PAIR,mid,art,'Explicit whole regional feature with no complete native Crystal counterpart. Every original profile, alpha and priority pixel stays in place. Only boundary-connected pixels that exactly match the actual surrounding floor at the same coordinates receive the matching native Crystal ground.')

    def timber_frames(self):
        # The entire central trunk and bent wall/roof profiles are particular
        # to the Fortree treehouses. The floating houses have another closed
        # set of slanted exterior panels. Their exact contours and voids are
        # retained in the adjoining native Crystal timber material.
        palette=[(0,0,0)]+self.native_palette(self.wood)[1:]
        families={
            'fortree_indoor_trunk_and_angled_rafters':(958,959,966,967,968,969,970,971,972,973,974,975,976,977,978,984,986,987,988,1005,1006,1007),
            'pacifidlog_indoor_maritime_wall_frame':(912,913,914,915,920,921,922,928,930,954,955),
        }
        for name,ids in families.items():
            for game in GAMES:
                for mid in ids:
                    if(game,mid)not in self.reserved:continue
                    colors={}
                    for rgb in self.source_colors(game,mid):
                        light=self.brightness(rgb)
                        level=0 if rgb==(0,0,0)else 1 if light<81 else 2 if light<151 else 3
                        colors[rgb]=palette[level]
                    selected=geometry_art(self,game,PAIR,mid,name,palette,colors)
                    self.add(game,PAIR,mid,selected,
                        'Closed reviewed whole regional timber feature with no complete Crystal counterpart. Every trunk curve, sloping beam, exterior void, shadow and native priority pixel keeps its coordinates. Its explicit four-color material uses the selected Crystal room timber shades and the original black void.')

    def public_furnishings(self):
        for mid in (712,713,790,791):
            self.aliases(PAIR,mid,self.native(self.wall,'reverse_gen2_home_plain_above_complete_bookcase'),
                'The complete native bookcase begins below this cell. The original top trim gives way to the matching Crystal wall, leaving the full bookcase silhouette and shelves below.')
        for game in GAMES:
            for mid,donor_mid,direction in ((564,555,'east'),(572,556,'west')):
                if(game,mid)not in self.reserved:continue
                witness=self.prior[game,donor_mid]
                assert witness['role']=='reverse_gen2_complete_backed_chair_'+direction
                parts=copy.deepcopy(witness['parts'])
                art=self.composite(self.wood,parts,'reverse_gen2_complete_native_rest_house_chair_'+direction)
                occupied={y*16+x for part in parts for y in range(part['y'],part['y']+part['h'])for x in range(part['x'],part['x']+part['w'])}
                art['_objectMask']=''.join('1'if i in occupied else'0'for i in range(256))
                self.add(game,PAIR,mid,art,'Whole Crystal-backed chair faces the rest-house dining table. Its complete legs and backrest sit on the matching Crystal timber floor.')

    def last_furnishings(self):
        self.aliases(PAIR,817,self.native(self.wall,'reverse_gen2_home_plain_above_complete_television'),
            'Unadorned native wall above the complete television screen; its former plastic hood is retired.')
        cabinets=(
            ([[835],[846]],'GUIDE_GENTS_HOUSE',(0,6),self.house,self.stone,'complete native apartment potted plant'),
            ([[992],[1000]],'ELMS_LAB',(6,0),self.house,self.wood,'complete native treehouse cabinet'),
            ([[728,729]],'ELMS_LAB',(6,1),self.house,self.sootopolis_floor,'complete native Sootopolis bookcase lower doors'),
        )
        for layout,name,anchor,source_floor,floor,label in cabinets:
            width,height=len(layout[0])*16,len(layout)*16
            self.object_family(PAIR,layout,name,anchor,source_floor,floor,label,
                column_pixels=list(range(16))*len(layout[0]),source_bounds=[0,0,width,height],foot_anchor=height-1)

    def maritime_corners(self):
        black=next(row['donor']for row in self.prior.values()if row.get('role')=='reverse_gen2_exact_black_canvas')
        assert set(self.gb_image(black).get_flattened_data())=={(0,0,0,255)}
        for game in GAMES:
            for mid in (998,999):
                if(game,mid)not in self.reserved:continue
                mask=[pixel[:3]!=(0,0,0)for pixel in self.source(game,mid).get_flattened_data()]
                assert 0<sum(mask)<256
                for y in range(16):
                    present=[x for x in range(16)if mask[y*16+x]]
                    assert not present or present==list(range(present[0],present[-1]+1)),('Noncontiguous maritime floor corner',game,mid,y)
                parts=[dict(donor=self.wood,srcX=part['x'],srcY=part['y'],**part)for part in runs(mask)]
                assert 0<len(parts)<=32
                art=self.composite(black,parts,'reverse_gen2_native_maritime_diagonal_floor_corner')
                art['overMask']='0'*256
                self.add(game,PAIR,mid,art,'Exact original diagonal floating-house floor silhouette, painted with the matching complete native timber field. The original outside-room area remains black and no edge extends outside the source footprint.')

    def build(self):
        self.furniture()
        self.sofas()
        self.rugs()
        self.beds()
        self.kitchens()
        self.windows_and_storage()
        self.surfaces()
        self.timber_frames()
        self.maritime_corners()
        self.fixed_structures()
        self.public_furnishings()
        self.last_furnishings()
        assert {(row['game'],row['id']) for row in self.rows.values()}==set(self.reserved), 'Household coverage is incomplete'
        self.write(OUT/'home-candidate.lua')
        (OUT/'home-contracts.json').write_text(json.dumps(self.contracts,indent=2)+'\n')
        (OUT/'home-new-keys.json').write_text(json.dumps([dict(game=r['game'],pair=PAIR,mid=r['id'])for r in self.rows.values()],indent=2)+'\n')
        return len(self.rows)

    def previews(self):
        records=[]
        for name in ('EM_VERDANTURF_TOWN_WANDAS_HOUSE','EM_PACIFIDLOG_TOWN_HOUSE1','EM_RUSTBORO_CITY_FLAT1_2F',
                     'EM_RUSTBORO_CITY_CUTTERS_HOUSE','EM_FALLARBOR_TOWN_MOVE_RELEARNERS_HOUSE','EM_FORTREE_CITY_HOUSE2',
                     'EM_DEWFORD_TOWN_HOUSE1','EM_SOOTOPOLIS_CITY_HOUSE1','EM_ROUTE104_MR_BRINEYS_HOUSE','EM_DEWFORD_TOWN_HALL',
                     'EM_ROUTE114_FOSSIL_MANIACS_HOUSE','EM_ROUTE110_TRICK_HOUSE_END','EM_LILYCOVE_CITY_COVE_LILY_MOTEL_1F',
                     'EM_RUSTBORO_CITY_HOUSE1','EM_SOOTOPOLIS_CITY_HOUSE3','EM_MOSSDEEP_CITY_HOUSE4','EM_FORTREE_CITY_DECORATION_SHOP',
                     'EM_MOSSDEEP_CITY_STEVENS_HOUSE','EM_LILYCOVE_CITY_COVE_LILY_MOTEL_2F','RU_FORTREE_CITY_DECORATION_SHOP'):
            game='ruby'if name.startswith('RU_')else'emerald'
            image,cells,_,meta=self.imp.gba(game,name);remaining=[]
            for cell in cells:
                mid=cell['id'];row=self.rows.get((game,'gen2',PAIR,mid,None))or self.prior.get((game,mid))
                if row:
                    art=preview.replacement_image(self.cache,row,self.packed,ROOT)
                    for x,y in cell['coordinates']:image.paste(art,(x*16,y*16))
                else:remaining.append(mid)
            image.save(OUT/(name+'-home-candidate.png'));records.append(dict(map=name,remaining=remaining))
        (OUT/'home-scene-review.json').write_text(json.dumps(records,indent=2)+'\n')
        from PIL import ImageDraw,ImageFont
        font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',12)
        features=[c for c in self.contracts if c.get('source_ids')]
        for page,start in enumerate(range(0,len(features),5)):
            sheet=Image.new('RGBA',(800,1000),(25,32,40,255));d=ImageDraw.Draw(sheet);y=0
            for spec in features[start:start+5]:
                ids=spec['source_ids'];w,h=len(ids[0])*16,len(ids)*16
                d.text((0,y),str(start+features[start:start+5].index(spec))+': '+spec['label']+' '+str(ids),font=font,fill='white');y+=18
                for index,game in enumerate(GAMES):
                    original=Image.new('RGBA',(w,h));candidate=original.copy()
                    for yy,line in enumerate(ids):
                        for xx,mid in enumerate(line):
                            src=self.source(game,mid);original.paste(src,(xx*16,yy*16))
                            row=self.rows.get((game,'gen2',PAIR,mid,None))or self.prior.get((game,mid))
                            art=preview.replacement_image(self.cache,row,self.packed,ROOT)if row else src
                            candidate.paste(art,(xx*16,yy*16))
                    x=index*260;d.text((x,y),game,font=font,fill='white')
                    sheet.paste(original.resize((w*2,h*2),Image.Resampling.NEAREST),(x,y+15))
                    sheet.paste(candidate.resize((w*2,h*2),Image.Resampling.NEAREST),(x+112,y+15))
                y+=h*2+28
            sheet.crop((0,0,800,y)).save(OUT/('native-feature-review-'+str(page)+'.png'))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--validate',action='store_true');p.add_argument('--activate',action='store_true');p.add_argument('--previews',action='store_true');a=p.parse_args();assert not a.activate or a.validate
    r=Review();r.build();proof=r.validate()if a.validate else None
    if a.previews:r.previews()
    if a.activate:r.write(TARGET)
    print(json.dumps(dict(rows=len(r.rows),body_cells=sum(r.reserved[row['game'],row['id']]['body_cells']for row in r.rows.values()),proof=proof,activated=a.activate)))
if __name__=='__main__':main()
