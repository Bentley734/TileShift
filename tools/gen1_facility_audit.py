"""Review Gen1 facility and cave artwork with exact original source guards.

New mapping module only; all source layouts, puzzles, NPCs and interactions
remain native. Private comparison contacts and integration manifests record the
old rows so the integrating owner can remove only exact matching keys.
"""
import argparse
import copy
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace
from PIL import Image, ImageDraw, ImageFont
import catalog
import preview
import gen1_family_review as source
import gen2_extended_review as validation
from interior_review import Imports
from johto_remaining_review import artwork
from center_mart_overhang_review import write_rows
from gen2_facility_floor_audit import Audit as NativeLayerHelpers
from native_room_parts import RoomParts

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / '.work/tileshift-gen1-facility-audit'
TARGET = ROOT / 'mappings/gen1_facility_audit.lua'
ASSETS = ROOT / 'assets/third_party/gamefreak/rby-facility-floor'
SETS = {'FACILITY', 'GYM', 'DOJO', 'CEMETERY', 'LAB', 'SHIP', 'MUSEUM', 'CAVERN', 'UNDERGROUND'}
SPECIAL = {'BILLS_HOUSE', 'SILPH_CO_11F', 'ROCKET_HIDEOUT_ELEVATOR', 'SILPH_CO_ELEVATOR'}
BORDER_SOURCES = {
    'SEAFOAM_ISLANDS_1F':125,'SEAFOAM_ISLANDS_B1F':125,'SEAFOAM_ISLANDS_B2F':125,
    'SEAFOAM_ISLANDS_B3F':125,'SEAFOAM_ISLANDS_B4F':125,'VICTORY_ROAD_3F':125,
    'POKEMON_MANSION_B1F':1,
}
DOMESTIC = {'WARDENS_HOUSE', 'FUCHSIA_MEETING_ROOM', 'SAFARI_ZONE_SECRET_HOUSE',
            'CERULEAN_BADGE_HOUSE', 'FUCHSIA_GOOD_ROD_HOUSE', 'POKEMON_FAN_CLUB'}


def stable(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def scope(name, definition):
    return name not in DOMESTIC and (definition.get('tileset') in SETS or name in SPECIAL)


class Audit(NativeLayerHelpers):
    def __init__(self):
        self.cache = Path(os.environ['APPDATA']) / 'pokemon-love2d'
        self.imports = Imports(self.cache, ROOT.parent / '.work/tileshift-catalog')
        self.packed = self.imports.packed
        paths = list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]", (ROOT / 'main.lua').read_text())))
        self.rows, self.origin, self.lookup = [], {}, {}
        for name in paths:
            if ROOT / name == TARGET:
                continue
            for index, row in enumerate(preview.read_reviewed(ROOT / name), 1):
                self.rows.append(row);self.origin[id(row)] = (name, index);self.lookup[name, index] = row
        self.data = {game: source.source(self.cache, game) for game in source.GAMES}
        self.by_game = {game: [r for r in self.rows if r['game'] == game and r['style'] == 'gen3'] for game in source.GAMES}
        self.images, self.floors = {}, {}
        self.rooms, self.floor_masks, self.asset_proofs = {}, {}, {}

    def room(self, name):
        if name not in self.rooms:
            self.rooms[name] = RoomParts(self.imports, 'firered', name)
        return self.rooms[name]

    def image(self,row):
        # Candidate rows are short-lived copies, so Python object IDs may be
        # reused. Cache their semantic artwork plus exact guarded source pixels.
        key=(row.get('sourceHash'),stable(artwork(row)))
        if key not in self.images:
            self.images[key]=preview.replacement_image(self.cache,row,self.packed,ROOT)
        return self.images[key]

    def floor(self, game, name, definition, cells):
        key = game, name
        if key not in self.floors:
            candidates = {stable(row['donor']): row['donor'] for row in cells.values()
                if row and row.get('donor') and 'floor' in row['role'] and not row.get('animated')}
            self.floors[key] = next(iter(candidates.values())) if len(candidates) == 1 else None
        return copy.deepcopy(self.floors[key])

    def render(self, game, name):
        data = self.data[game];definition = data['maps'][name]
        cells = self.selected(game, name, definition)
        before = Image.new('RGBA', (definition['width'] * 32, definition['height'] * 32));after = before.copy()
        originals = {}
        for (x, y), row in cells.items():
            bid = definition['blocks'][y // 2 * definition['width'] + x // 2];q = y % 2 * 2 + x % 2
            if (bid, q) not in originals:
                cell = source.cell_info(self.cache, game, data, definition['tileset'], bid, q)
                originals[bid, q] = source.source_image(self.cache, game, data, cell, definition)
            before.paste(originals[bid, q], (x * 16, y * 16))
            after.paste(self.image(row) if row else originals[bid, q], (x * 16, y * 16))
        return before, after

    def inventory(self):
        maps, rows, excluded = [], [], []
        for game, data in self.data.items():
            for name, definition in sorted(data['maps'].items()):
                if not isinstance(definition, dict) or not definition.get('tileset'):
                    continue
                if not scope(name, definition):
                    excluded.append(dict(game=game, map=name, tileset=definition['tileset']));continue
                cells = self.selected(game, name, definition);unique = {}
                for xy, row in cells.items():
                    if row:unique.setdefault(id(row), [row, []])[1].append(list(xy))
                maps.append(dict(game=game, map=name, tileset=definition['tileset'], cells=len(cells),
                    missing=sum(r is None for r in cells.values()), unique_rows=len(unique),
                    kinds=dict(Counter(r.get('kind', 'native') for r, _ in unique.values()))))
                for row, coords in unique.values():
                    module, index = self.origin[id(row)]
                    rows.append(dict(game=game, map=name, tileset=definition['tileset'], module=module, index=index,
                        role=row['role'], kind=row.get('kind', 'native'), coordinates=coords,
                        base=row.get('base'), donor=row.get('donor'), asset=row.get('asset'), parts=row.get('parts')))
        result = dict(maps=maps, unique_rows=rows, excluded_maps=excluded,
            totals=dict(maps=len(maps), cells=sum(m['cells'] for m in maps), missing=sum(m['missing'] for m in maps)))
        (OUT / 'inventory.json').write_text(json.dumps(result, indent=2));return result

    def object_contacts(self, inventory):
        """Inspect complete donor layers; foreground alpha never implies approval."""
        proposals, seen = [], set()
        for item in inventory['unique_rows']:
            if item['game'] != 'red' or any(word in item['role'] for word in ('chair', 'stool', 'lounge', 'student', 'seat', 'cushion')):
                continue
            row = self.lookup[item['module'], item['index']]
            trial = copy.deepcopy(row);details = []
            if row.get('parts'):
                trial, details = self.detached(row)
            if not details:
                continue
            before = self.image(row);after = preview.replacement_image(self.cache, trial, self.packed, ROOT)
            if before.tobytes() == after.tobytes():
                continue
            key = stable([row['role'], row['sourceHash'], artwork(row)])
            if key in seen:
                continue
            seen.add(key)
            d = self.data[item['game']];m = d['maps'][item['map']]
            c = source.cell_info(self.cache, item['game'], d, m['tileset'], row['id'], row['quadrant'])
            proposals.append(dict(item=item, details=details, original=source.source_image(self.cache, item['game'], d, c, m), before=before, after=after))
        font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 13)
        for offset in range(0, len(proposals), 12):
            chunk = proposals[offset:offset + 12];canvas = Image.new('RGB', (1100, len(chunk) * 96 + 32), '#18212b');draw = ImageDraw.Draw(canvas)
            draw.text((4, 4), 'AUDIT ONLY — original source / current / detached MID+OVER candidate (not approved)', fill='white', font=font)
            for local, value in enumerate(chunk):
                y = 30 + local * 96
                for col, name in enumerate(('original', 'before', 'after')):
                    canvas.paste(value[name].resize((80, 80), Image.Resampling.NEAREST), (4 + col * 90, y))
                item = value['item'];draw.text((280, y + 2), str(offset + local) + ' ' + item['map'] + ' ' + str(item['coordinates'][:3]), fill='white', font=font)
                draw.text((280, y + 25), item['role'], fill='white', font=font)
                draw.text((280, y + 48), str([(p['donor']['tileset'], p['donor']['id'], p['outside_native_pixels']) for p in value['details']]), fill='white', font=font)
            canvas.save(OUT / ('object-candidates-' + str(offset // 12 + 1).zfill(2) + '.png'))
        (OUT / 'object-candidates.json').write_text(json.dumps([
            dict(number=i, item=v['item'], details=v['details']) for i, v in enumerate(proposals)], indent=2))
        return len(proposals)

    def connected_floor(self, game, name, definition, cells, floor):
        """Exact original floor-pattern pixels connected to reviewed floor cells."""
        key = game, name, stable(floor)
        if key in self.floor_masks:
            return self.floor_masks[key]
        original, _ = self.render(game, name)
        patterns = {}
        seeds = []
        for (x, y), row in cells.items():
            if not row or row.get('donor') != floor or 'floor' not in row['role']:
                continue
            cell = original.crop((x * 16, y * 16, x * 16 + 16, y * 16 + 16))
            patterns.setdefault(cell.tobytes(), cell)
            seeds.extend((x * 16 + px, y * 16 + py) for py in range(16) for px in range(16))
        assert patterns and seeds, (game, name, 'No exact source floor seeds')
        allowed = [set(im.getpixel((x, y)) for im in patterns.values()) for y in range(16) for x in range(16)]
        # The executive table is bounded by a complete dark outline. Its
        # diagonal floor motif changes phase beside that outline; retain the
        # whole enclosed table/chair while walking both exterior floor colors.
        # This broader rule is deliberately limited to that reviewed room.
        if name == 'SILPH_CO_11F':
            colors = set().union(*allowed)
            allowed = [colors] * 256
        outside = set(seeds);queue = list(outside)
        for x, y in queue:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                xx, yy = x + dx, y + dy
                if (0 <= xx < original.width and 0 <= yy < original.height
                    and (xx, yy) not in outside and original.getpixel((xx, yy)) in allowed[yy % 16 * 16 + xx % 16]):
                    outside.add((xx, yy));queue.append((xx, yy))
        self.floor_masks[key] = outside
        return outside

    def cutout(self, row, game, name, xy, floor, outside):
        x, y = xy
        masked = [[px, py] for py in range(16) for px in range(16) if (x * 16 + px, y * 16 + py) in outside]
        if not masked or len(masked) == 256:
            return None
        before = self.image(row);image = before.copy()
        for px, py in masked:
            image.putpixel((px, py), (0, 0, 0, 0))
        retained = 256 - len(masked)
        assert retained > 0
        for py in range(16):
            for px in range(16):
                if [px, py] not in masked:
                    assert image.getpixel((px, py)) == before.getpixel((px, py))
        rgba_hash = catalog.sha(image.tobytes())
        filename = 'source-' + rgba_hash[:24] + '.png'
        ASSETS.mkdir(parents=True, exist_ok=True)
        path = ASSETS / filename;image.save(path)
        proof = self.asset_proofs.setdefault(filename, dict(
            pixel_scale=1, dimensions=[16, 16], rgba_sha256=rgba_hash,
            retained_original_pixels=retained, sources=[]))
        proof['sources'].append(dict(game=game, map=name, coordinate=[x, y], tileset=row['tileset'],
            id=row['id'], quadrant=row['quadrant'], sourceHash=row['sourceHash'],
            sourceFiles=copy.deepcopy(row['sourceFiles']), sourceColors=copy.deepcopy(row['sourceColors']),
            original_colored_rgba_sha256=catalog.sha(before.tobytes()),
            omitted_connected_original_floor=masked))
        result = copy.deepcopy(row)
        result.pop('sourceColors')
        result.update(kind='third_party', asset=path.relative_to(ROOT).as_posix(),
            assetFileHash=catalog.sha(path.read_bytes()), base=copy.deepcopy(floor),
            credit='Original Pokemon Red/Blue/Yellow / Game Freak; complete original geometry recolored, exterior source floor omitted.',
            sourceUrl='https://github.com/pret/pokered')
        return result, dict(family='original_complete_prop_exterior_floor', pixel_scale=1,
            retained_original_foreground_pixels=retained, omitted_source_floor_pixels=len(masked),
            rule='Only exact original floor-pattern pixels connected to reviewed source floor cells are transparent; every retained original RGBA pixel remains unchanged.')

    def fix(self, row, game, name, definition, cells, xy):
        role = row['role'];x, y = xy
        integrated = name == 'SILPH_CO_11F' and role == 'gen1_special_original_complete_executive_meeting_table_and_chair'
        if not integrated and any(word in role for word in ('chair', 'stool', 'seat', 'cushion', 'lounge', 'student')):
            return None
        floor = self.floor(game, name, definition, cells)
        family = None;details = None
        if row.get('asset', '').startswith('assets/original/interior-stairs/'):
            # Native GBA house stair assemblies are wider than this complete
            # original16px glyph. Preserve every source rail and tread rather
            # than resize or truncate a native staircase.
            ramp = [[240,248,240],[184,200,208],[104,128,144],[48,56,80]]
            result = copy.deepcopy(row)
            for key in ('donor','base','parts','asset','assetFileHash','assetPixelHash','artOverlay','foreground','occludes'):
                result.pop(key,None)
            result.update(kind='source_palette',sourceColors=[copy.deepcopy(ramp)for _ in range(4)],
                credit='Original Pokemon Red/Blue/Yellow / Game Freak; complete compact staircase geometry recolored at1:1.',
                sourceUrl='https://github.com/pret/pokered')
            family='complete_original_compact_stairs'
            if floor:
                value=self.cutout(result,game,name,xy,floor,self.connected_floor(game,name,definition,cells,floor))
                if value:result,details=value
            details=dict(family=family,pixel_scale=1,original_source_asset=row['asset'],
                rule='Every original rail, tread and step stays at its source pixel position; only connected exterior floor may be transparent.')
        if name == 'OAKS_LAB':
            room = self.room('FR_OAKS_LAB');floor = room.ref(649)
            # The original64x32 computer bench is one complete native64x32
            # workstation; native left tower/control and right CRT/desk remain
            # intact. The omitted extension is a separate repeating desk bay.
            if 0 <= x < 4 and 1 <= y < 3:
                result = copy.deepcopy(row)
                for key in ('donor', 'base', 'parts', 'asset', 'assetFileHash', 'sourceColors'):
                    result.pop(key, None)
                result.update(kind='native_composite', base=floor,
                    parts=room.rect(x * 16, 16 + (y - 1) * 16, 16, 16, layers=['mid', 'over']),
                    role='gen1_complete_native_oaks_workstation')
                family='complete_native_oaks_workstation'
            elif 6 <= x < 9 and 3 <= y < 5:
                result = copy.deepcopy(row)
                for key in ('donor', 'base', 'parts', 'asset', 'assetFileHash', 'sourceColors'):
                    result.pop(key, None)
                result.update(kind='native_composite', base=floor,
                    parts=room.rect(128 + (x - 6) * 16, 64 + (y - 3) * 16, 16, 16, layers=['mid', 'over']),
                    role='gen1_complete_native_oaks_lab_table')
                family='complete_native_oaks_lab_table'
            elif role == 'gen1_temple_complete_wall_header':
                result=copy.deepcopy(row);result['donor']=room.ref(109)
                family='actual_native_oaks_wall'
        reviewed_original_exterior=(name=='SILPH_CO_11F'and role in(
            'gen1_special_original_complete_executive_meeting_table_and_chair',
            'gen1_special_original_silph_complete_partition_corner_or_desk'))or(
            name=='SS_ANNE_CAPTAINS_ROOM'and xy==(1,1)and role=='gen1_ship_complete_compact_original_furniture_and_railings')
        if family is None and row.get('kind') == 'source_palette' and floor and reviewed_original_exterior:
            # Integrated executive chair stays part of its complete64px object;
            # no facing, source coordinates or source pixels are rearranged.
            outside = self.connected_floor(game, name, definition, cells, floor)
            value = self.cutout(row, game, name, xy, floor, outside)
            if value:
                result, details = value;family=details['family']
        if family is None and row.get('parts') and not role.startswith('cave_'):
            if role.startswith(('johto_house_bookcase_', 'johto_domestic_complete_single_bay_bookcase_')):
                family='bookcase_actual_room_floor'
            elif role in ('gen1_facility_complete_native_modular_lab_table', 'gen1_facility_complete_table_cap_below_wall',
                          'gen1_complete_native_lab_wall_clock', 'johto_complete_native_region_map'):
                family='native_prop_actual_room_surroundings'
            elif name == 'BILLS_HOUSE' and role in ('gen1_whole_native_bill_transporter_pod', 'gen1_bill_complete_native_transporter_conduit'):
                # The source top row is wall behind the pods; its native gray
                # wall stays intact. Lower outside corners use the room floor.
                if y > 0:family='bill_complete_pod_floor'
            if family:
                result, layers=self.detached(row)
                if floor and family=='bookcase_actual_room_floor':
                    if y > 0:result['base']=copy.deepcopy(floor)
                    old=row.get('base')
                    for part in result['parts']:
                        ref=part['donor']
                        if ref==old or (ref['game']=='firered'and ref['tileset']in('house','player_house','pewter_gym')and ref['id']in(1,40,715)):
                            part['donor']=copy.deepcopy(result['base']);part.pop('layers',None);part.pop('layerHashes',None)
                elif floor and family=='bill_complete_pod_floor':result['base']=copy.deepcopy(floor)
                details=dict(family=family,pixel_scale=1)
                if layers:details['native_layers']=layers
        if family is None:
            return None
        before=self.image(row);after=preview.replacement_image(self.cache,result,self.packed,ROOT)
        if before.tobytes()==after.tobytes():return None
        if details is None:details=dict(family=family,pixel_scale=1)
        if family in ('bookcase_actual_room_floor','native_prop_actual_room_surroundings','bill_complete_pod_floor'):
            foreground=Image.new('RGBA',(16,16))
            for part in result.get('parts',[]):
                if not part.get('layers')or part['donor']==result.get('base'):continue
                pixels=preview.native_donor(self.cache,part['donor'],self.packed,part['layers'],part['layerHashes'])
                sx,sy=part.get('srcX',0),part.get('srcY',0)
                piece=pixels.crop((sx,sy,sx+part.get('w',16),sy+part.get('h',16)))
                foreground.alpha_composite(piece,(part.get('x',0),part.get('y',0)))
            count=0
            for py in range(16):
                for px in range(16):
                    if foreground.getpixel((px,py))[3]:
                        assert before.getpixel((px,py))==after.getpixel((px,py)),(game,name,role,xy,'Native foreground changed',px,py)
                        count+=1
            assert count>0,(game,name,role,xy,'No whole native foreground')
            details['retained_native_foreground_pixels']=count
        for field in ('game','style','tileset','id','quadrant','sourceHash','sourceFiles','sourceBehavior'):
            assert result.get(field)==row.get(field),(game,name,role,field)
        result['gen1FacilityAudit']=details
        result['evidence']=row.get('evidence','')+' Gen1 facility audit: complete source-matched native counterpart or authorized original-geometry cutout at1:1; original map, source behavior, warps, objects, scripts and interactions unchanged.'
        result['compositionPixelHash']=catalog.sha(after.tobytes())
        return result

    def stage(self):
        rows=[];removals={};changes=[]
        for game,data in self.data.items():
            for name,definition in sorted(data['maps'].items()):
                if not isinstance(definition,dict)or not scope(name,definition):continue
                cells=self.selected(game,name,definition);groups=defaultdict(list)
                for xy,row in cells.items():
                    if row:groups[id(row)].append(xy)
                for coords in groups.values():
                    old=cells[coords[0]];plans=[]
                    for xy in coords:
                        value=self.fix(old,game,name,definition,cells,xy)
                        if value:plans.append((xy,value))
                    if not plans:continue
                    same=len(plans)==len(coords)and len({stable(artwork(r))for _,r in plans})==1
                    if same and old.get('x')is None:
                        r=plans[0][1];r['map']=name;r.pop('x',None);r.pop('y',None);r['sourceCells']=[list(xy)for xy,_ in plans];made=[r]
                    else:
                        made=[]
                        for xy,r in plans:r['map']=name;r['x'],r['y']=xy;r['sourceCells']=[list(xy)];made.append(r)
                    module,index=self.origin[id(old)];digest=hashlib.sha256(stable(old).encode()).hexdigest()
                    if old.get('map')==name and(same or old.get('x')is not None):removals[module,index]=True
                    for r in made:r['gen1FacilityAudit']['prior']=dict(module=module,index=index,old_row_sha256=digest);rows.append(r)
                    changes.append(dict(game=game,map=name,role=old['role'],coordinates=[list(xy)for xy,_ in plans],family=plans[0][1]['gen1FacilityAudit']['family']))
        integration=[]
        for index,row in enumerate(rows,1):
            prior=row['gen1FacilityAudit']['prior'];old=self.lookup[prior['module'],prior['index']]
            integration.append(dict(oldmodule=prior['module'],oldindex=prior['index'],oldrow=old,old_row_sha256=prior['old_row_sha256'],
                newmodule=TARGET.relative_to(ROOT).as_posix(),newindex=index,newrow=row,remove_old=(prior['module'],prior['index'])in removals))
        border_rows=self.border_rows()
        rows.extend(border_rows)
        (OUT/'border-additions.json').write_text(json.dumps(border_rows,indent=2))
        (OUT/'candidates.json').write_text(json.dumps(rows,indent=2));(OUT/'integration-manifest.json').write_text(json.dumps(integration,indent=2))
        summary=dict(rows=len(rows),cells=sum(len(c['coordinates'])for c in changes),maps=len({(c['game'],c['map'])for c in changes}),
            border_rows=len(border_rows),by_family=dict(Counter(c['family']for c in changes)),changes=changes)
        (OUT/'changes.json').write_text(json.dumps(summary,indent=2))
        if self.asset_proofs:
            files={name:catalog.sha((ASSETS/name).read_bytes())for name in self.asset_proofs}
            # This new, tool-owned folder contains only this audit's cutouts.
            # Remove obsolete drafts so package hashes cover every PNG present.
            assert ASSETS.resolve().is_relative_to((ROOT/'assets/third_party/gamefreak').resolve())
            for path in ASSETS.glob('source-*.png'):
                if path.name not in files:path.unlink()
            (ASSETS/'provenance.json').write_text(json.dumps(dict(source='Original Pokemon Red/Blue/Yellow / Game Freak; original-geometry recolor cutouts only.',
                sourceUrl='https://github.com/pret/pokered',pixel_scale=1,files=files,assets=self.asset_proofs),indent=2)+'\n')
        return rows,summary

    def border_rows(self):
        result=[]
        for game,name,block,q in((g,n,b,q)for g in source.GAMES for n,b in BORDER_SOURCES.items()for q in range(4)):
            data=self.data[game];definition=data['maps'][name]
            assert scope(name,definition)
            cell=source.cell_info(self.cache,game,data,definition['tileset'],block,q)
            assert cell['tiles']==([17]*4 if name=='POKEMON_MANSION_B1F'else[2,3,18,19])
            # Use the exact already-reviewed regional solid fill, never a cave
            # surface from a different palette or a corner inferred by collision.
            template_map=('SEAFOAM_ISLANDS_B2F'if name.startswith('SEAFOAM_')else
                          'VICTORY_ROAD_3F'if name.startswith('VICTORY_ROAD_')else'POKEMON_MANSION_3F')
            template_definition=data['maps'][template_map]
            choices=[r for r in self.selected(game,template_map,template_definition).values()
                if r['sourceHash']==cell['sourceHash']and
                source.cell_info(self.cache,game,data,r['tileset'],r['id'],r['quadrant'])['behavior']==cell['behavior']]
            unique={stable(artwork(r)):r for r in choices}
            assert len(unique)==1,(game,name,block,q,'Ambiguous original border counterpart')
            template=next(iter(unique.values()));module,index=self.origin[id(template)]
            row=dict(game=game,style='gen3',map=name,tileset=definition['tileset'],id=block,quadrant=q,
                sourceCells={},
                sourceHash=cell['sourceHash'],sourceFiles=copy.deepcopy(data['fingerprints'][definition['tileset']]),
                sourceBehavior=copy.deepcopy(cell['behavior']),status='reviewed',
                role='gen1_facility_complete_regional_border_fill',
                gen1FacilityAudit=dict(family='complete_regional_border_fill',pixel_scale=1,
                    border_mode='map',source_raw=cell['tiles'],
                    source_template=dict(map=template_map,module=module,index=index,sourceHash=template['sourceHash'])),
                evidence='Complete original border-block quadrant matched to identical source pixels and all original movement/grass/warp/door/counter flags in the reviewed same-region map. Exact native regional solid fill at1:1, not a directional edge or gameplay tile. Original border definition, source metadata and interactions remain unchanged.')
            row.update(artwork(template));row['role']='gen1_facility_complete_regional_border_fill'
            row['compositionPixelHash']=catalog.sha(preview.replacement_image(self.cache,row,self.packed,ROOT).tobytes())
            result.append(row)
        assert len(result)==84,len(result)
        return result

    def staged_contacts(self,rows):
        font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
        scenes=[];seen=set()
        for game,name in sorted({(r['game'],r['map'])for r in rows if r.get('sourceCells')}):
            source_image,before=self.render(game,name);after=before.copy()
            for r in rows:
                if r['game']==game and r['map']==name:
                    image=preview.replacement_image(self.cache,r,self.packed,ROOT)
                    for x,y in r.get('sourceCells',[]):after.paste(image,(x*16,y*16))
            digest=catalog.sha(source_image.tobytes()+before.tobytes()+after.tobytes())
            if digest in seen:continue
            seen.add(digest)
            canvas=Image.new('RGB',(before.width*4+36,before.height*2+48),'#18212b');ImageDraw.Draw(canvas).text((8,6),game.title()+' / '+name+' — current / staged Gen3 facility fixes',font=font,fill='white')
            canvas.paste(before.resize((before.width*2,before.height*2),Image.Resampling.NEAREST),(8,32));canvas.paste(after.resize((after.width*2,after.height*2),Image.Resampling.NEAREST),(before.width*2+28,32));canvas.save(OUT/(game+'-'+name+'-staged.png'))
            if game=='red':canvas.save(OUT/(name+'-staged.png'))
            scenes.append((game,name,source_image,before,after))
        for offset in range(0,len(scenes),6):
            canvas=Image.new('RGB',(1560,6*285),'#18212b');draw=ImageDraw.Draw(canvas)
            for local,(game,name,*images)in enumerate(scenes[offset:offset+6]):
                y=local*285;draw.text((8,y+3),game+' / '+name+' — source / current / staged',font=font,fill='white')
                for col,im in enumerate(images):
                    im=im.copy();im.thumbnail((504,254),Image.Resampling.NEAREST)
                    canvas.paste(im,(8+col*520,y+27))
            canvas.save(OUT/('staged-rooms-'+str(offset//6+1).zfill(2)+'.png'))
        (OUT/'staged-scenes.json').write_text(json.dumps([dict(game=g,map=n,comparison=g+'-'+n+'-staged.png')for g,n,*_ in scenes],indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--object-contacts', action='store_true')
    parser.add_argument('--stage', action='store_true')
    parser.add_argument('--validate', action='store_true')
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args();OUT.mkdir(parents=True, exist_ok=True)
    audit = Audit();result = audit.inventory()
    if args.object_contacts:result['totals']['object_candidates'] = audit.object_contacts(result)
    if args.stage or args.validate or args.activate:
        rows,summary=audit.stage();audit.staged_contacts(rows)
        if args.validate or args.activate:
            proof=validation.validate_batch(rows,SimpleNamespace(cache=audit.cache,engine=ROOT.parent/'.tools/engine-0395',output=OUT),ROOT)
            (OUT/'proof.json').write_text(json.dumps(proof,indent=2))
        if args.activate:
            assert args.validate;write_rows(TARGET,rows)
        result['totals']['staged']={k:v for k,v in summary.items()if k!='changes'}
    print(json.dumps(result['totals']))


if __name__ == '__main__':
    main()
