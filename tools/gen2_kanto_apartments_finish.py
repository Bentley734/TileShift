"""Complete GSC Celadon apartments and Crystal's compact Mobile Adapter rooms.

Native condo material and complete furniture retain their pixel size. Original
compact elevator/stair, office and Mobile Adapter glyphs use the authorized
geometry-preserving palette fallback when a complete native counterpart will
not fit. No generated artwork or scaled replacement is used.
"""
import argparse,copy,json,os
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
import catalog,preview,gen2_extended_review as e
from PIL import Image
from gen2_kanto_special_rooms_finish import Review,RED_SOURCES
from gen2_kanto_buildings_finish import safe_native_art,stable
from johto_remaining_review import artwork
from center_mart_overhang_review import write_rows

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'.work/tileshift-gen2-apartments'
TARGET=ROOT/'mappings/gen2_kanto_apartments_finish.lua'
NAMES=('CELADON_MANSION_1F','CELADON_MANSION_2F','CELADON_MANSION_3F','CELADON_MANSION_ROOF',
       'MOBILE_BATTLE_ROOM','MOBILE_TRADE_ROOM')
STEEL=[[240,244,232],[176,192,200],[104,128,144],[48,56,72]]
WOOD=[[240,224,168],[192,160,96],[128,104,64],[48,56,64]]
GREEN=[[224,232,176],[168,184,112],[104,136,80],[48,64,56]]
BLUE=[[224,240,240],[144,184,216],[88,128,176],[40,56,80]]
RED=[[232,236,216],[232,136,144],[184,72,80],[48,56,72]]
PALETTES={1:STEEL,2:RED,3:GREEN,4:BLUE,5:[[208,224,224],[160,184,192],[96,136,168],[48,56,72]],6:WOOD}

def palette(c,role,palettes=PALETTES):
    return dict(kind='source_palette',sourceColors=[copy.deepcopy(palettes.get(a.get('palette',1),STEEL))
        for a in c['attributes']],role=role,credit='Original Pokemon Gold/Silver/Crystal / Game Freak; palette recolor only.',
        sourceUrl='https://github.com/pret/pokecrystal')

class Apartments(Review):
    def __init__(self):
        super().__init__()
        self.active=[r for p in sorted((ROOT/'mappings').glob('*.lua'))if p!=TARGET for r in preview.read_reviewed(p)]
        self.index=defaultdict(list)
        self.templates={r['role']:r for r in self.active if r['game']=='crystal'}
        for r in self.active:
            self.index[r['game'],r.get('map'),r.get('sourceHash')].append(r)
            if r['game']=='red':self.templates.setdefault(r['role'],r)
        self.condo=self.room('FR_CELADON_CITY_CONDOMINIUMS_1F')
        self.roof=self.room('FR_CELADON_CITY_CONDOMINIUMS_ROOF')
        self.floor=self.condo.ref(641);self.wall=self.condo.ref(657)
        self.plant=ROOT/'assets/third_party/johto-hacks/interior-plants/firegold-potted-flower16.png'
        self.plant_hash=catalog.sha(self.plant.read_bytes())
        self.details={}
        clock=self.templates['gen2_ship_complete_native_wall_clock']['donor']
        image=preview.native_donor(self.cache,clock,self.packed)
        background={image.getpixel((x,y))for x in(0,15)for y in range(15)}
        background.update(image.getpixel((x,y))for x in range(16)for y in(0,14))
        outside={(x,y)for y in range(15)for x in range(16)if(x in(0,15)or y==0)and image.getpixel((x,y))in background}
        queue=list(outside)
        for x,y in queue:
            for xx,yy in((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if 0<=xx<16 and 0<=yy<15 and(xx,yy)not in outside and image.getpixel((xx,yy))in background:
                    outside.add((xx,yy));queue.append((xx,yy))
        # The16th row is the source cabin's straight baseboard, below the
        # complete clock and shadow. It is background, not the clock frame.
        assert len({image.getpixel((x,15))for x in range(16)})==1
        outside.update((x,15)for x in range(16));self.clock_parts=[]
        for y in range(16):
            x=0
            while x<16:
                if(x,y)in outside:x+=1;continue
                end=x+1
                while end<16 and(end,y)not in outside:end+=1
                self.clock_parts.append(dict(donor=copy.deepcopy(clock),srcX=x,srcY=y,x=x,y=y,w=end-x,h=1));x=end
        assert 80<256-len(outside)<190 and len(self.clock_parts)<=16
        (OUT/'native-clock-pixel-proof.json').write_text(json.dumps(dict(native_ref=clock,
            retained_original_pixels=256-len(outside),omitted_outside_wall_pixels=sorted(outside),
            original_pixel_size=[16,16],native_clock_frame_face_hands_shadow_preserved=True),indent=2))
    def n(self,ref,role):return self.native(ref,'kanto_apartment_'+role)
    def template_art(self,role,base=None):
        a=artwork(self.templates[role]);a['role']='kanto_apartment_'+role
        if base is not None and 'base'in a:a['base']=copy.deepcopy(base)
        assert safe_native_art(a),('Generated apartment counterpart',role)
        return a
    def table(self,q):
        return self.template_art(('household_table_nw','household_table_ne','household_table_sw','household_table_se')[q],self.floor)
    def partition(self,role):
        # Only a repeating plain native wall strip is used. Its side holes
        # remain the same native condo floor, never the donor's black void.
        return dict(kind='native_composite',base=copy.deepcopy(self.floor),role='kanto_apartment_'+role,
            parts=[dict(donor=self.condo.ref(740),srcX=0,srcY=0,x=4,y=0,w=8,h=16)])
    def office_base(self,c,data):
        """Retain the original cabinet; remove only its outside source floor.

        The right foot glyph has an explicit8px floor pair. The left drawer
        glyph has an enclosed dark outline, allowing only its connected pale
        outside field to be removed. Unique paper, controls and feet remain.
        """
        value=palette(c,'kanto_apartment_complete_original_office_base_gen3_palette')
        row=dict(game=c['game'],style='gen3',tileset=c['tileset'],id=c['id'],quadrant=c['quadrant'],
            sourceHash=c['sourceHash'],sourceFiles=data['fingerprints'][c['tileset']],**value)
        image=preview.source_palette_image(self.cache,row,self.packed)
        ts=data['sets'][c['tileset']];source=preview.native_cell(data['sheets'][c['tileset']],ts,
            catalog.lua_array(catalog.dict_at(ts['blocks'],c['id']+1)),c['quadrant'])
        omit=set()
        for q,tile in enumerate(c['tiles']):
            if tile==17:
                omit.update((q%2*8+x,q//2*8+y)for y in range(8)for x in range(8))
        if tuple(c['tiles'])==(74,75,90,91):
            # The cabinet frame encloses its light drawer front. Its outside
            # field is reached only from the16px cell edge.
            def field(x,y):return source.getpixel((x,y))[0]>=170
            queue=[]
            for y in range(16):
                for x in range(16):
                    if(x in(0,15)or y in(0,15))and field(x,y):omit.add((x,y));queue.append((x,y))
            for x,y in queue:
                for xx,yy in((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                    if 0<=xx<16 and 0<=yy<16 and(xx,yy)not in omit and field(xx,yy):omit.add((xx,yy));queue.append((xx,yy))
        for x,y in omit:image.putpixel((x,y),(0,0,0,0))
        assert 0<len(omit)<160
        fingerprint=catalog.sha((c['sourceHash']+json.dumps(value['sourceColors'])).encode())[:20]
        path=ROOT/'assets/third_party/gamefreak/gsc-apartments'/('office-base-'+fingerprint+'.png')
        path.parent.mkdir(parents=True,exist_ok=True);image.save(path)
        self.details[path.name]=dict(origin='Original GSC compact office cabinet; palette recolor only, no scale or rearrangement.',
            source_game=c['game'],source_tileset=c['tileset'],source_id=c['id'],source_quadrant=c['quadrant'],
            source_rgba_sha256=c['sourceHash'],source_tile_ids=c['tiles'],source_colors=value['sourceColors'],
            omitted_floor_coordinates=sorted(omit),retained_original_geometry=True,png_sha256=catalog.sha(path.read_bytes()))
        return dict(kind='third_party',base=copy.deepcopy(self.floor),asset=path.relative_to(ROOT).as_posix(),
            assetFileHash=catalog.sha(path.read_bytes()),role=value['role'],credit=value['credit'],sourceUrl=value['sourceUrl'])
    def handle(self,c,x,y,name,m,data):
        raw=tuple(c['tiles'])
        if name.startswith('MOBILE_'):
            return palette(c,'kanto_mobile_complete_original_link_console_and_battle_field_gen3_palette')
        if name.endswith('_ROOF'):
            if raw in((32,33,48,49),(161,162,177,178),(163,164,179,180)):
                return palette(c,'kanto_apartment_complete_compact_roof_stair_or_door_gen3_palette',
                    {i:STEEL for i in range(1,9)})
            native={
                (129,130,145,146):793,(130,130,146,146):800,
                (133,134,149,150):794,(165,166,181,182):802,
                (194,194,194,194):774,(195,194,195,194):801,(194,196,194,196):802,
                (131,192,147,144):809,(192,192,144,144):800,
                (193,194,198,194):809,(192,132,144,148):810,
            }
            if raw in native:return self.n(self.roof.ref(native[raw]),'complete_native_rooftop_parapet_or_floor')
            # Stair mouths, the narrow bridge turns and compact stair housing
            # have unique outlines; no native 32px frame is cut to fit them.
            return palette(c,'kanto_apartment_complete_compact_roof_access_gen3_palette',
                {1:GREEN,2:RED,3:GREEN,4:BLUE,5:STEEL,6:WOOD})
        # The equivalent Red condo family supplies only unscaled native art.
        if raw in((74,75,90,91),(76,77,17,17)):return self.office_base(c,data)
        a=self.same(c,RED_SOURCES.get(name,()),'red')
        if a and safe_native_art(a):return a
        if raw in((1,1,1,1),(17,17,17,17),(18,18,18,18)):
            return self.n(self.floor,'native_condominium_floor')
        if raw in((3,3,19,19),(3,5,20,21)):
            return self.n(self.wall,'complete_native_condominium_baseboard')
        if raw in((69,85,14,15),(14,15,14,15),(12,15,28,15),(14,15,30,31)):
            return self.partition('native_narrow_partition')
        if raw in((10,11,26,27),(8,9,24,25),(32,33,48,49),(6,7,22,23),(22,23,38,39)):
            return palette(c,'kanto_apartment_complete_compact_stair_or_elevator_gen3_palette',{i:STEEL for i in range(1,9)})
        tables={(54,55,70,71):0,(55,56,71,72):1,(70,71,86,87):2,(71,72,87,88):3}
        if raw in tables:return self.table(tables[raw])
        bookcases={(3,3,54,56):0,(34,35,50,51):2,(52,53,50,51):3}
        if raw in bookcases:return self.template_art('johto_house_bookcase_'+str(bookcases[raw]),self.floor)
        if raw==(54,56,36,37):
            value=self.template_art('johto_house_bookcase_1',self.floor)
            value['parts']+=copy.deepcopy(self.clock_parts)
            value['role']='kanto_apartment_complete_native_clock_above_cabinet'
            return value
        if raw==(46,47,94,95):
            return dict(kind='third_party',base=copy.deepcopy(self.floor),asset=self.plant.relative_to(ROOT).as_posix(),
                assetFileHash=self.plant_hash,role='kanto_apartment_complete_native_potted_flower',
                credit='FireGold 1.4 hack authors; original Pokemon artwork by Game Freak.',
                sourceUrl='https://www.pokecommunity.com/threads/pok%C3%A9mon-firegold.459788/')
        if raw==(4,4,40,40):return palette(c,'kanto_apartment_complete_compact_exit_mat_gen3_palette')
        if raw in((42,43,58,59),(44,45,60,61),(74,75,90,91),(76,77,17,17)):
            return palette(c,'kanto_apartment_complete_original_compact_office_fixture_gen3_palette')
        return None

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--validate',action='store_true');p.add_argument('--activate',action='store_true');p.add_argument('--previews',action='store_true');a=p.parse_args();assert not a.activate or a.validate
    OUT.mkdir(parents=True,exist_ok=True);v=Apartments()
    rows=[];held=[];stats=[]
    for game in e.GAMES:
        data=e.source(v.cache,game)
        for name in NAMES:
            if name not in data['maps']:continue
            m=data['maps'][name];selected=[r for r in v.active if r['game']==game and r['tileset']==m['tileset']and r.get('map',name)==name]
            generic={(r['id'],r['quadrant'])for r in selected if r.get('x')is None};pos={(r['id'],r['quadrant'],r['x'],r['y'])for r in selected if r.get('x')is not None};added=missing=0
            for y in range(m['height']*2):
                for x in range(m['width']*2):
                    bid=m['blocks'][y//2*m['width']+x//2];q=y%2*2+x%2
                    if(bid,q)in generic or(bid,q,x,y)in pos:continue
                    missing+=1;c=e.cell_info(v.cache,game,data,m['tileset'],bid,q);value=v.handle(c,x,y,name,m,data)
                    if value is None:held.append(dict(game=game,map=name,x=x,y=y,raw=c['tiles'],collision=c['collision']));continue
                    r=dict(game=game,style='gen3',map=name,tileset=m['tileset'],id=bid,quadrant=q,x=x,y=y,sourceCells=[[x,y]],sourceHash=c['sourceHash'],sourceFiles=data['fingerprints'][m['tileset']],sourceCollision=c['collision'],sourcePriority=[bool(z.get('priority'))for z in c['attributes']],sourcePalettes=[z.get('palette',1)for z in c['attributes']],status='reviewed',
                        evidence='Complete original apartment/Mobile Adapter room context reviewed. Native condo floors, full baseboards and complete furniture use original pixels at 1:1. Narrow partitions omit donor voids. Unique compact glyphs explicitly retain all original source geometry through a Gen3 palette recolor. Source collisions, events, entrances, room layout and scripts remain unchanged.')
                    r.update(value);r['compositionPixelHash']=catalog.sha(preview.replacement_image(v.cache,r,v.packed,ROOT).tobytes());rows.append(r);added+=1
            stats.append(dict(game=game,map=name,prior_remaining=missing,added=added,remaining=missing-added))
    grouped=defaultdict(list)
    for r in rows:grouped[r['game'],r['map'],r['id'],r['quadrant']].append(r)
    rows=[]
    for group in grouped.values():
        if len({json.dumps(artwork(r),sort_keys=True)for r in group})==1:
            r=group[0];r.pop('x');r.pop('y');r['sourceCells']=[z['sourceCells'][0]for z in group];rows.append(r)
        else:rows.extend(group)
    (OUT/'candidates.json').write_text(json.dumps(rows,indent=2));(OUT/'held.json').write_text(json.dumps(held,indent=2));summary=dict(rows=len(rows),cells=sum(s['added']for s in stats),remaining=sum(s['remaining']for s in stats),maps=stats);(OUT/'summary.json').write_text(json.dumps(summary,indent=2))
    if v.details:
        path=ROOT/'assets/third_party/gamefreak/gsc-apartments/provenance.json'
        path.write_text(json.dumps(dict(credit='Original Pokemon Gold/Silver/Crystal / Game Freak; palette recolor only.',
            sourceUrl='https://github.com/pret/pokecrystal',assets=v.details),indent=2)+'\n')
    if a.previews:
        for name in NAMES:preview.map_preview(v.cache,OUT,'crystal',name,name,v.active+rows,v.packed,3,ROOT)
    if a.validate:
        proof=e.validate_batch(rows,SimpleNamespace(cache=v.cache,engine=ROOT.parent/'.tools/engine-0395',output=OUT),ROOT);(OUT/'proof.json').write_text(json.dumps(proof,indent=2))
        if a.activate:write_rows(TARGET,stable(rows))
    print(json.dumps({k:z for k,z in summary.items()if k!='maps'}))

if __name__=='__main__':main()
