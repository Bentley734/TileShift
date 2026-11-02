"""Complete remaining Kanto outdoor railings with their native handed corners.

Uses complete native FR/LG fence panels/corners, transparent vertical rails and
whole single posts. Unusual compact terminal glyphs keep all original pixels in
the authorized steel/grass palette instead of inventing a rail or cropping a
larger post. Only explicit outdoor source glyphs are selected.
"""
import argparse
import copy
import json
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import catalog
import preview
import gen2_extended_review as e
from center_mart_overhang_review import write_rows
from gen2_kanto_shores_finish import Reviewer as ShoresReviewer
from native_room_parts import RoomParts

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'.work/tileshift-gen2-kanto-details'
TARGET=ROOT/'mappings/gen2_kanto_details_finish.lua'
PAIR='general__rom_082d4b54'
# Canonical native map proofs: FR_ROUTE_15 horizontal231 at6,8; NE237 at16,13;
# cap238 at16,5; right245 at16,6; SE253 at16,8. FR_FUCHSIA_CITY NW236 at31,23,
# left244 at7,18 and SW252 at7,22. Actual orientation is checked from these maps.
FENCES={(16,35,16,35):(244,'over','west_vertical'),
        (35,16,35,16):(245,'over','east_vertical'),
        (35,35,32,32):(231,'mid','south_horizontal'),
        (32,32,35,35):(231,'mid','north_horizontal'),
        (33,32,16,35):(236,'mid','northwest_corner'),
        (32,33,35,16):(237,'mid','northeast_corner'),
        (16,35,33,32):(252,'mid','southwest_corner'),
        (35,16,32,33):(253,'mid','southeast_corner')}
SINGLE_POST={(33,35,35,35):0,(35,33,35,35):8,
             (35,35,33,35):0,(35,35,35,33):8,
             (33,35,16,35):0,(35,33,35,16):8}
COMPACT_TERMINALS={(16,35,33,35),(35,16,35,33)}
CONTEXTS={231:('FR_ROUTE_15',6,8),237:('FR_ROUTE_15',16,13),
          238:('FR_ROUTE_15',16,5),245:('FR_ROUTE_15',16,6),
          253:('FR_ROUTE_15',16,8),236:('FR_FUCHSIA_CITY',31,23),
          244:('FR_FUCHSIA_CITY',7,18),252:('FR_FUCHSIA_CITY',7,22)}


class Reviewer(ShoresReviewer):
    def __init__(self):
        super().__init__()
        self.active=[r for p in sorted((ROOT/'mappings').glob('*.lua')) if p!=TARGET
                     for r in preview.read_reviewed(p)]
        self.contexts=[]
        for mid,(name,x,y) in sorted(CONTEXTS.items()):
            native=RoomParts(self.imp,'firered',name)
            assert native.pair==PAIR and native.layout['mids'][y*native.layout['width']+x]==mid
            self.contexts.append(dict(game='firered',map=name,pair=PAIR,cell=[x,y],metatile=mid,
                rectangle=[x*16,y*16,16,16],wholePixelHash=native.ref(mid)['hash'],
                layerHashes=self.imp.cell_index('firered')[PAIR,mid]['layer_sha256']))

    def piece(self,mid,layer,sx=0,sy=0,w=16,h=16,x=0,y=0):
        rec=self.imp.cell_index('firered')[PAIR,mid]
        return {'donor':self.ref('firered',PAIR,mid),'layers':[layer],
            'layerHashes':{layer:rec['layer_sha256'][layer]},'srcX':sx,'srcY':sy,
            'w':w,'h':h,'x':x,'y':y}

    def choose(self,c):
        if c['tileset']!='TILESET_KANTO' or c['collision']!=0:return None
        if not all(a.get('source_pixels_complete') for a in c['attributes']):return None
        raw=tuple(c['tiles'])
        if raw in FENCES:
            mid,layer,shape=FENCES[raw]
            return {'kind':'native_composite','base':copy.deepcopy(self.ground),
                'parts':[self.piece(mid,layer)],'role':'kanto_complete_native_fence_'+shape,
                'nativeShape':{'metatile':mid,'layer':layer,'shape':shape}}
        if raw in SINGLE_POST:
            # The full native single post is its complete84-pixel over layer,
            # bbox8,2..16,16. This rectangle retains every opaque pixel, along
            # with its whole cap/shaft/shadow, at original size.
            return {'kind':'native_composite','base':copy.deepcopy(self.ground),
                'parts':[self.piece(238,'over',sx=8,sy=2,w=8,h=14,x=SINGLE_POST[raw],y=2)],
                'role':'kanto_complete_native_single_fence_post'}
        if raw in COMPACT_TERMINALS:
            grass=[115,206,165]
            # One source8px terminal above a continuing rail has no complete
            # matching native8px cap; all source pixels/handedness are retained.
            return {'kind':'source_palette','sourceColors':[[grass,[189,206,214],[99,115,132],[49,66,82]]for _ in range(4)],
                'role':'kanto_original_complete_compact_fence_terminal',
                'credit':'Original Pokemon Gold/Silver/Crystal compact fence terminal in Gen3 steel and lawn colors.',
                'sourceUrl':'https://github.com/pret/pokecrystal'}
        return None


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--validate',action='store_true');p.add_argument('--activate',action='store_true');p.add_argument('--no-previews',action='store_true');args=p.parse_args();assert not args.activate or args.validate
    OUT.mkdir(parents=True,exist_ok=True);tool=Reviewer();rows=[];held=[];stats=[]
    # Prove the single native post crop includes every opaque source pixel.
    ref=tool.ref('firered',PAIR,238);rec=tool.imp.cell_index('firered')[PAIR,238]
    whole=preview.native_donor(tool.cache,ref,tool.packed,['over'],{'over':rec['layer_sha256']['over']})
    assert whole.getbbox()==(8,2,16,16)
    assert sum(p[3]>0 for p in whole.get_flattened_data())==84
    for game in e.GAMES:
        data=e.source(tool.cache,game)
        limit=catalog.read_lua(tool.cache/game/'data/generated/landmarks.lua')['landmarks']['LANDMARK_PALLET_TOWN']['index']
        for name,m in sorted(data['maps'].items()):
            if not isinstance(m,dict)or m.get('tileset')!='TILESET_KANTO'or m.get('environment')not in('TOWN','ROUTE')or 0<m.get('landmark',999)<limit:continue
            selected=[r for r in tool.active if r['game']==game and r['tileset']==m['tileset']and r.get('map',name)==name]
            generic={(r['id'],r['quadrant'])for r in selected if r.get('x')is None};pos={(r['x'],r['y'])for r in selected if r.get('x')is not None};groups={}
            for i,bid in enumerate(m['blocks']):
                for q in range(4):
                    x,y=i%m['width']*2+q%2,i//m['width']*2+q//2
                    if(bid,q)in generic or(x,y)in pos:continue
                    c=e.cell_info(tool.cache,game,data,m['tileset'],bid,q);value=tool.choose(c)
                    if value is None:
                        held.append(dict(game=game,map=name,id=bid,quadrant=q,x=x,y=y,raw=c['tiles'],collision=c['collision']));continue
                    key=bid,q
                    if key in groups:groups[key]['sourceCells'].append([x,y]);continue
                    r=dict(game=game,style='gen3',map=name,tileset=m['tileset'],id=bid,quadrant=q,sourceCells=[[x,y]],
                        sourceHash=c['sourceHash'],sourceFiles=data['fingerprints'][m['tileset']],sourceCollision=c['collision'],
                        sourcePriority=[bool(a.get('priority'))for a in c['attributes']],sourcePalettes=[a.get('palette',1)for a in c['attributes']],
                        status='reviewed',evidence='Actual native FireRed steel railing family has distinct complete horizontal231, vertical244/245, northwest236, northeast237, southwest252 and southeast253 modules. Source glyph orientation and complete native map context determine the matching module. Full native single-post238 over-layer retains all84 opaque pixels, including cap, shaft and shadow. Transparent exterior shows the same native lawn as the adjoining map. No scaling, invented rail, changed source collision, map, gate, encounter, warp or event.')
                    r.update(value)
                    if r['kind']=='source_palette':r['evidence']='The unique original compact8px lower fence terminal has no complete matching native8px cap. Preserve every original source pixel and handed continuation in the authorized Gen3 steel/lawn palette; this is recolored cartridge geometry, not extracted hack artwork. Original source collision, map layout, gates, connections, encounters and events remain unchanged.'
                    r['compositionPixelHash']=catalog.sha(preview.replacement_image(tool.cache,r,tool.packed,ROOT).tobytes());groups[key]=r
            current=list(groups.values());rows.extend(current)
            if current:stats.append(dict(game=game,map=name,rows=len(current),cells=sum(len(r['sourceCells'])for r in current)))
    proof={'rows':len(rows),'cells':sum(len(r['sourceCells'])for r in rows),'maps':len(stats),'roles':dict(Counter(r['role']for r in rows)),'map_additions':stats,'active':args.activate,'whole_native_post_pixels_retained':84,'native_contexts':tool.contexts}
    (OUT/'candidates.json').write_text(json.dumps(rows,indent=2)+'\n');(OUT/'held.json').write_text(json.dumps(held,indent=2)+'\n')
    if args.validate:proof['validation']=e.validate_batch(rows,SimpleNamespace(cache=tool.cache,engine=ROOT.parent/'.tools/engine-0395',output=OUT),ROOT)
    (OUT/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    if not args.no_previews:
        for name in('SAFFRON_CITY','ROUTE_11','ROUTE_17','CERULEAN_CITY'):
            preview.map_preview(tool.cache,OUT,'crystal',name,'staged-'+name,tool.active+rows,tool.packed,1,ROOT)
    if args.activate:write_rows(TARGET,rows)
    print(json.dumps({k:v for k,v in proof.items()if k not in('roles','map_additions','native_contexts')},indent=2))


if __name__=='__main__':main()
