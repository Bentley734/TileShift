"""Explicit Kanto outdoor banks, whole raised-earth profiles and pier modules.

Every selection names its original visible glyph and orientation. Native water
uses the same checked FireRed bank as the already reviewed Kanto water surface;
freshwater and marine semantic roles remain separate for connected Mixed mode.
Only this new module is written; map geometry and all movement remain original.
"""
import argparse
import copy
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace

import catalog
import preview
import gen2_extended_review as e
from center_mart_overhang_review import write_rows
from gen2_kanto_water_finish import MARINE
from interior_review import Imports
from johto_remaining_review import artwork
from native_room_parts import RoomParts

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / '.work/tileshift-gen2-kanto-shores'
TARGET = ROOT / 'mappings/gen2_kanto_shores_finish.lua'
SETS = {'TILESET_JOHTO', 'TILESET_KANTO'}
# Full native FR rock-bank family: inward corners preserve the exact handed
# four-pixel native cap (305 top-left land,304 top-right land), not a straight.
BANK_MIDS = {'northwest': 721, 'north': 291, 'northeast': 722,
             'west': 298, 'east': 300, 'inward_northwest': 305, 'inward_northeast': 304}
KANTO_BANKS = {(51,51,51,20): 'northwest', (51,51,20,20): 'north',
              (51,51,20,84): 'northeast', (51,20,51,20): 'west',
              (20,84,20,84): 'east', (51,20,20,20): 'inward_northwest',
              (20,51,20,20): 'inward_northeast'}
JOHTO_BANKS = {(92,76,61,20): 'northwest', (76,76,20,20): 'north',
              (76,93,20,59): 'northeast', (61,20,61,20): 'west',
              (20,59,20,59): 'east', (77,20,20,20): 'inward_northwest',
              (20,75,20,20): 'inward_northeast'}
# These match the complete already reviewed Violet/Azalea/Mahogany profile,
# including directional upper blocking0xb2, all full curves and the Cianwood
# solid-backed inward corners123/125. Numbers are native metatiles, not a
# numerical inference from the unrelated source cartridge tile identifiers.
RAISED = {(60,60,60,60): 113, (44,44,60,60): 105,
          (45,60,61,45): 106, (61,61,61,61): 114,
          (59,59,59,59): 112, (59,75,75,76): 120,
          (76,76,76,76): 121, (77,61,76,77): 122,
          (60,43,43,59): 104, (76,76,61,76): 123,
          (76,76,76,59): 125}
OUTCROPS = {(43,44,59,60): (104,0,0), (44,45,60,61): (106,1,0),
            (59,60,75,76): (120,0,1), (60,61,76,77): (122,1,1)}


class Reviewer:
    def __init__(self):
        self.cache = Path(os.environ['APPDATA']) / 'pokemon-love2d'
        self.imp = Imports(self.cache, ROOT.parent / '.work/tileshift-catalog')
        self.packed = self.imp.packed
        self.active = [r for path in sorted((ROOT/'mappings').glob('*.lua')) if path != TARGET
                       for r in preview.read_reviewed(path)]
        self.templates = {r['role']: r for r in self.active if r['game'] == 'crystal'}
        self.ground = next(copy.deepcopy(r['base']) for r in self.active
            if r.get('base',{}).get('tileset') == 'general__petalburg' and r['base']['id'] == 1)
        self.ocean = next(r for r in self.active if r['game'] == 'crystal'
            and r['role'] == 'coastal_ocean_water_interior' and r.get('donor',{}).get('game') == 'firered')
        self.animations = {}
        # Actual complete sand interior277, not the different native NW
        # grass/sand corner258. The native path texture stays unscaled.
        self.sand = RoomParts(self.imp,'firered','FR_SAFARI_ZONE_WEST').ref(277)

    def ref(self, game, pair, mid):
        rec = self.imp.cell_index(game)[pair,mid]
        return {'game': game, 'tileset': pair, 'id': mid, 'hash': rec['pixel_sha256']}

    def part(self, mid, sx=0, sy=0, w=16, h=16, x=0, y=0, game='firered', pair='pewter_outdoor'):
        rec = self.imp.cell_index(game)[pair,mid]
        return {'donor': self.ref(game,pair,mid), 'layers': ['mid'],
            'layerHashes': {'mid': rec['layer_sha256']['mid']},
            'srcX': sx, 'srcY': sy, 'w': w, 'h': h, 'x': x, 'y': y}

    def animation(self, mid):
        if mid not in self.animations:
            value = artwork(self.ocean)
            value['donor'] = self.ref('firered','pallet_outdoor',mid)
            value['animation'].pop('frame0Hash',None)
            frames = preview.native_water_frames(self.cache,value,self.packed)
            assert len(frames) == 8
            value['animation']['frame0Hash'] = catalog.sha(frames[0].tobytes())
            self.animations[mid] = value['animation']
        return copy.deepcopy(self.animations[mid])

    def water(self, mid, name, shape):
        return {'kind':'native', 'donor':self.ref('firered','pallet_outdoor',mid),
            'animated': True, 'animation': self.animation(mid),
            'role': ('coastal_rock_shore_' if name in MARINE else 'freshwater_pond_native_rock_') + shape}

    def rock(self, mid, role, base=None):
        return {'kind':'native_composite', 'base':copy.deepcopy(base or self.ground),
                'parts':[self.part(mid)], 'role':role}

    def choose(self, c, x, y, name, m, grid):
        if not all(a.get('source_pixels_complete') for a in c['attributes']):
            return None
        raw = tuple(c['tiles'])
        bank = JOHTO_BANKS if m['tileset'] == 'TILESET_JOHTO' else KANTO_BANKS
        if raw in bank:
            assert c['collision'] == 41
            return self.water(BANK_MIDS[bank[raw]],name,bank[raw])
        if m['tileset'] == 'TILESET_JOHTO' and raw in RAISED:
            assert c['collision'] in (0,7,178)
            return self.rock(RAISED[raw], 'kanto_complete_native_raised_earth_'+str(RAISED[raw]))
        if m['tileset'] == 'TILESET_JOHTO' and raw in OUTCROPS:
            assert c['collision'] == 7
            mid,dx,dy = OUTCROPS[raw]
            # The complete2x2 rock is checked independently. Its corners can
            # face field or sea in this original map, so use actual outward
            # neighbour cells for its transparent exterior instead of filling
            # all repetitions with one map-wide floor.
            ox,oy = x-dx,y-dy
            for shape,(_,sx,sy) in OUTCROPS.items():
                assert tuple(grid[ox+sx,oy+sy]['tiles']) == shape, (name,ox,oy,shape)
            nx,ny = (-1 if dx == 0 else 1),(-1 if dy == 0 else 1)
            outside = [(x+nx,y),(x,y+ny),(x+nx,y+ny)]
            marine = any(grid.get(p,{}).get('collision') in (36,39,41) for p in outside)
            r = self.rock(mid, 'rocky_coast_whole_outcrop_'+str(dy*2+dx) if marine
                          else 'kanto_complete_native_land_outcrop_'+str(dy*2+dx))
            if marine:
                r.update(base=copy.deepcopy(self.ocean['donor']), animated=True,
                         animation=self.animation(299))
            r['_context'] = {'outcropOrigin':[ox,oy], 'exteriorNeighbors':[list(p) for p in outside],
                             'exteriorIsWater':marine}
            return r
        if m['tileset'] == 'TILESET_JOHTO' and raw == (88,88,88,88):
            assert c['collision'] == 39
            r = {'kind':'native_composite','role':'rocky_coast_sea_rock_barrier',
                 'parts':[self.part(404,game='emerald',pair='general__petalburg')]}
            r.update(base=copy.deepcopy(self.ocean['donor']), animated=True, animation=self.animation(299))
            return r
        if m['tileset'] == 'TILESET_JOHTO' and raw == (50,51,66,67):
            assert c['collision'] == 36
            r = artwork(self.templates['rocky_coast_whirlpool'])
            r.update(base=copy.deepcopy(self.ocean['donor']), animated=True,
                     animation=self.animation(299),role='rocky_coast_whirlpool')
            return r
        if m['tileset'] == 'TILESET_JOHTO' and raw == (6,6,76,76):
            r = artwork(self.templates['violet_paved_rock_front']);r['role']='kanto_paved_rock_front'
            return r
        if m['tileset'] == 'TILESET_KANTO' and raw == (75,75,75,75) and c['collision'] == 114:
            r = artwork(self.templates['johto_fishing_pier_floor']);r['role']='kanto_complete_native_pier_floor'
            return r
        if m['tileset'] == 'TILESET_KANTO' and raw == (49,49,20,20):
            assert c['collision'] == 41
            r = artwork(self.templates['johto_fishing_pier_edge'])
            r.update(base=copy.deepcopy(self.ocean['donor']),animated=True,animation=self.animation(299),
                     role='rocky_coast_kanto_pier_edge' if name in MARINE else 'freshwater_pond_kanto_pier_edge')
            return r
        if m['tileset'] == 'TILESET_KANTO' and raw in ((57,57,55,55),(57,57,54,55)):
            assert c['collision'] == 7
            # Native front keeps its complete upper/lower outlines, omitting
            # only the repeating middle face for the original8px-high bank.
            if raw[2] == 54:
                return self.rock(120,'kanto_complete_native_low_bank_west_corner')
            return {'kind':'native_composite','base':copy.deepcopy(self.ground),
                'parts':[self.part(121,sy=0,h=4,y=8),self.part(121,sy=12,h=4,y=12)],
                'role':'kanto_native_eight_pixel_south_bank'}
        if m['tileset'] == 'TILESET_KANTO' and raw == (48,57,57,48):
            assert c['collision'] == 0
            return {'kind':'native','donor':copy.deepcopy(self.sand),'role':'kanto_native_nonencounter_sandy_ground'}
        if m['tileset'] == 'TILESET_KANTO' and raw == (57,57,4,4):
            assert c['collision'] == 0
            return {'kind':'native_composite','base':copy.deepcopy(self.ground),
                'parts':[{'donor':copy.deepcopy(self.sand),'srcX':0,'srcY':0,'w':16,'h':8,'x':0,'y':0}],
                'role':'kanto_native_sandy_ground_north_half'}
        return None


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--validate',action='store_true');p.add_argument('--activate',action='store_true')
    p.add_argument('--no-previews',action='store_true');args=p.parse_args()
    assert not args.activate or args.validate
    OUT.mkdir(parents=True,exist_ok=True);tool=Reviewer();rows=[];held=[];stats=[]
    for game in e.GAMES:
        data=e.source(tool.cache,game)
        limit=catalog.read_lua(tool.cache/game/'data/generated/landmarks.lua')['landmarks']['LANDMARK_PALLET_TOWN']['index']
        for name,m in sorted(data['maps'].items()):
            if not isinstance(m,dict) or m.get('tileset') not in SETS or m.get('environment') not in ('TOWN','ROUTE'):
                continue
            if 0 < m.get('landmark',999) < limit:continue
            current=[r for r in tool.active if r['game']==game and r['tileset']==m['tileset'] and r.get('map',name)==name]
            generic={(r['id'],r['quadrant']) for r in current if r.get('x') is None}
            positioned={(r['x'],r['y']) for r in current if r.get('x') is not None}
            grid={};missing=[];groups={}
            for i,bid in enumerate(m['blocks']):
                for q in range(4):
                    x,y=i%m['width']*2+q%2,i//m['width']*2+q//2
                    c=e.cell_info(tool.cache,game,data,m['tileset'],bid,q);grid[x,y]=c
                    if (bid,q) not in generic and (x,y) not in positioned:missing.append((x,y,c))
            for x,y,c in missing:
                value=tool.choose(c,x,y,name,m,grid)
                if value is None:
                    held.append(dict(game=game,map=name,tileset=m['tileset'],id=c['id'],quadrant=c['quadrant'],
                        x=x,y=y,raw=c['tiles'],collision=c['collision']));continue
                context=value.pop('_context',None)
                row=dict(game=game,style='gen3',map=name,tileset=m['tileset'],id=c['id'],quadrant=c['quadrant'],
                    sourceCells=[[x,y]],sourceHash=c['sourceHash'],sourceFiles=data['fingerprints'][m['tileset']],
                    sourceCollision=c['collision'],sourcePriority=[bool(a.get('priority')) for a in c['attributes']],
                    sourcePalettes=[a.get('palette',1) for a in c['attributes']],status='reviewed',
                    evidence='Explicit original oriented source glyph reviewed in its complete map context. Full native '
                    'FR/LG directional raised-earth and rocky-water-bank families retain whole corner curves, handedness, '
                    'native pixel size and original source footprint. Native FireRed water retains all eight checked frames '
                    'and uses the same bank as adjoining reviewed Kanto water. Marine and freshwater roles remain distinct '
                    'for connected Mixed styles. Original collision including north-only walls, ledges, Surf/Whirlpool, '
                    'encounters, maps, warps, scripts and events remain unchanged.')
                row.update(value)
                if context:row['sourceExteriorContexts']=[context|{'cell':[x,y]}]
                row['compositionPixelHash']=catalog.sha(preview.replacement_image(tool.cache,row,tool.packed,ROOT).tobytes())
                key=c['id'],c['quadrant'],json.dumps(artwork(row),sort_keys=True)
                if key in groups:
                    groups[key]['sourceCells'].append([x,y])
                    if context:groups[key]['sourceExteriorContexts'].append(context|{'cell':[x,y]})
                else:groups[key]=row
            variants=Counter((r['id'],r['quadrant']) for r in groups.values());made=[]
            for row in groups.values():
                if variants[row['id'],row['quadrant']] > 1:
                    for x,y in row['sourceCells']:
                        r=copy.deepcopy(row);r.update(x=x,y=y,sourceCells=[[x,y]])
                        if 'sourceExteriorContexts' in r:r['sourceExteriorContexts']=[z for z in r['sourceExteriorContexts'] if z['cell']==[x,y]]
                        made.append(r)
                else:made.append(row)
            rows.extend(made)
            if made:stats.append(dict(game=game,map=name,rows=len(made),cells=sum(len(r['sourceCells']) for r in made)))
    (OUT/'candidates.json').write_text(json.dumps(rows,indent=2)+'\n')
    (OUT/'held.json').write_text(json.dumps(held,indent=2)+'\n')
    proof={'rows':len(rows),'cells':sum(len(r['sourceCells']) for r in rows),'maps':len(stats),
           'roles':dict(Counter(r['role'] for r in rows)),'maps_added':stats,'active':args.activate}
    if args.validate:
        proof['validation']=e.validate_batch(rows,SimpleNamespace(cache=tool.cache,
                engine=ROOT.parent/'.tools/engine-0395',output=OUT),ROOT)
    (OUT/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    if not args.no_previews:
        for name in ('ROUTE_26','ROUTE_27','CINNABAR_ISLAND','ROUTE_1','ROUTE_12','CELADON_CITY','VIRIDIAN_CITY'):
            preview.map_preview(tool.cache,OUT,'crystal',name,'staged-'+name,tool.active+rows,tool.packed,1,ROOT)
    if args.activate:write_rows(TARGET,rows)
    print(json.dumps({k:v for k,v in proof.items() if k not in ('roles','maps_added')},indent=2))


if __name__=='__main__':main()
