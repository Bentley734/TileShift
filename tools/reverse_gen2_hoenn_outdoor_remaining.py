"""Finish actual used Crystal-style Hoenn outdoor source counterparts.

The source inventory is a read-only exact logical-body scan. Existing reviewed
rows remain occupied and are never superseded by this additive author.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
from collections import Counter,defaultdict
from pathlib import Path

import catalog
import preview
from johto_remaining_review import artwork
from reverse_common import ROOT,ReverseReview
from reverse_gen2_hoenn_outdoor_complete import Review as PreviousReview
from reverse_gen2_hoenn_outdoor_finish import identity, digest,GAMES

TARGET = ROOT / 'mappings/reverse_gen2_hoenn_outdoor_remaining.lua'
OUTPUT = ROOT.parent / '.work/tileshift-v0360-hoenn-outdoors-completion'
GUARDS = ROOT / 'tools/reverse_gen2_hoenn_outdoor_remaining_guards.json'


class Review(PreviousReview):
    def __init__(self, output=OUTPUT):
        ReverseReview.__init__(self,'gen2-hoenn-outdoor-remaining',GAMES)
        self.out = Path(output)
        self.out.mkdir(parents=True, exist_ok=True)
        self.target_module = TARGET
        self.prior, self.locations = [], {}
        self.active_modules = list(dict.fromkeys(re.findall(
            r"['\"](mappings/[^'\"]+\.lua)['\"]", (ROOT / 'main.lua').read_text())))
        for module in self.active_modules:
            if ROOT / module == TARGET:
                continue
            for number, row in enumerate(preview.read_reviewed(ROOT / module)):
                self.prior.append(row)
                self.locations[identity(row)] = (module, number, row)
        self.occupied = {identity(row) for row in self.prior}
        self.templates = copy.deepcopy(self.prior)
        self.groups={};self.group_list=[];self.counts=Counter();self.collision_profiles=defaultdict(Counter)
        self.usage=defaultdict(list);self.proofs={};self.recipes={};self.supersessions={};self.uncertain=[]
        self.layouts={};self.layout_hashes={};self._source_maps={};self._rendered_rows={}

    def render(self, row):
        return preview.replacement_image(self.cache, row, self.packed, ROOT)

    def load_inventory(self):
        self.group_list=json.loads((self.out/'inventory.json').read_text())
        self.groups={group['source_identity']:group for group in self.group_list}
        self.layout_hashes=json.loads((self.out/'source-layout-hashes.json').read_text())
        for relative,expected in self.layout_hashes.items():
            assert catalog.sha((self.cache/relative).read_bytes())==expected, 'Native source layout changed'
        for group in self.group_list:
            for source in group['source']:
                current=self.imp.cell_index(source['game'])[source['pair'],source['mid']]
                assert current['pixel_sha256']==source['hash'] and current['behavior']==source['behavior']
                self.counts[source['game'],source['pair'],source['mid']]=source['occurrences']
                self.usage[source['game'],source['pair'],source['mid']]=source['contexts']

    def exact_aliases(self):
        contracts=json.loads(GUARDS.read_text())['exact_aliases']
        records=[]
        for contract in contracts:
            game,pair,mid=contract['key']
            key=(game,'gen2',pair,mid,None)
            assert key not in self.occupied
            c=self.imp.cell_index(game)[pair,mid]
            assert c['pixel_sha256']==contract['sourceHash'] and c['behavior']==contract['sourceBehavior']
            assert c['layer_sha256']==contract['sourceLayers']
            canonical=contract['canonical']
            other=(canonical['game'],'gen2',canonical['pair'],canonical['mid'],None)
            module,_,row=self.locations[other]
            assert module==canonical['module'] and digest(row)==canonical['row_sha256']
            native=self.imp.cell_index(other[0])[other[2],other[3]]
            assert native['pixel_sha256']==c['pixel_sha256'] and native['behavior']==c['behavior']
            assert native['layer_sha256']==c['layer_sha256']
            art=artwork(row)
            for field in ('overMask','animationCategory','assetPixelHash'):
                if field in row:art[field]=copy.deepcopy(row[field])
            art['role']='reverse_gen2_hoenn_reviewed_exact_alias_'+row['role']
            result=self.row(game,pair,mid,'gen2',art,
                'The complete native source RGBA image, every under/mid/over layer and original behavior are byte-identical to the explicitly named already reviewed source counterpart in the same outdoor family. The full previously reviewed Crystal geometry, transparent exterior, foreground mask and animation are retained unchanged at native pixel scale. This is an exact complete-picture alias with one unambiguous native output, not a color/rank/nearest-neighbor guess. Source layouts, collision, elevation, warps, events and actors remain unchanged.')
            assert result['compositionPixelHash']==row['compositionPixelHash']
            result['hoennOutdoorRemainingReview']=dict(kind='exact_native_source_alias',contract_sha256=digest(contract),canonical=canonical)
            records.append(dict(game=game,pair=pair,mid=mid,sourceHash=result['sourceHash'],
                sourceBehavior=result['sourceBehavior'],compositionPixelHash=result['compositionPixelHash'],
                occurrences=self.counts[game,pair,mid],canonical=canonical))
        self.proofs['exact_source_aliases']=records
        return records

    def underwater_reef_shapes(self):
        # Explicit structural choices use the original Union Cave wall set,
        # matching the established raised-reef/floor adaptation. The source
        # indexed shape is independently identical to the named previously
        # reviewed cliff prototype; this is never selected by color/rank.
        refs={519:(12,3),525:(6,1),526:(4,1),527:(12,3),541:(14,3),543:(12,2),
              571:(4,3),576:(16,3),577:(17,2),592:(16,3),593:(17,2),595:(4,3),
              704:(16,3),705:(17,2),720:(16,3),721:(17,2),723:(4,3)}
        contracts=json.loads(GUARDS.read_text())['underwater_reef_shapes']
        assert {record['mid']for record in contracts}==set(refs)
        records=[]
        for contract in contracts:
            group=self.groups[contract['group_identity']]
            assert group['family']=='general__underwater' and group['mid']==contract['mid']
            assert {s['game']:s['hash']for s in group['source']}==contract['source_hashes']
            assert group['geometry']==contract['geometry']
            canonical=contract['canonical'];other=(canonical['game'],'gen2',canonical['pair'],canonical['mid'],None)
            _,_,prior=self.locations[other]
            from reverse_hoenn_review import native_geometry
            assert [catalog.sha(p)for p in native_geometry(self,other[0],other[2],other[3])]==group['geometry']
            bid,q=refs[group['mid']];ref=self.underwater_ref(bid,q)
            art=self.native(ref,'reverse_gen2_hoenn_underwater_complete_reef_shape_'+str(group['mid']))
            art['overMask']='0'*256
            for source in group['missing']:
                row=self.row(source['game'],source['pair'],source['mid'],'gen2',art,
                    'Joined native underwater maps distinguish this complete raised-reef front, north cap, convex corner, inner wall join or solid reef top from traversable seafloor. Its entire indexed under/mid/over geometry is exactly the named already reviewed Hoenn cliff prototype, independently establishing handedness without relying on purple source color or numeric ordering. The complete original Crystal Union Cave16px structural counterpart is shown in the same frozen native Cianwood DAY blue palette as the established underwater reef family. Original floor/reef collision, source depth/elevation, Dive and surface behavior, events and layouts remain unchanged.')
                row['hoennOutdoorRemainingReview']=dict(kind='underwater_exact_structural_counterpart',
                    contract_sha256=digest(contract),native_ref=ref,canonical_geometry_source=canonical,
                    complete_original_native_cell=True,source_mid=group['mid'])
                records.append(dict(game=source['game'],pair=source['pair'],mid=source['mid'],
                    sourceHash=row['sourceHash'],sourceBehavior=row['sourceBehavior'],
                    compositionPixelHash=row['compositionPixelHash'],occurrences=source['occurrences']))
        self.proofs['underwater_reef_shapes']=records
        return records

    def submarine(self):
        from PIL import Image
        from build_classic_submarine import build,DIRECTORY,GRID,RGBA_HASH
        from gb_theme_animation import specification
        proof=build()
        provenance=json.loads((DIRECTORY/'provenance.json').read_text())
        art_cells={record['mid']:record for record in provenance['cells']}
        whole=Image.open(DIRECTORY/'submarine64x48.png').convert('RGBA')
        water=self.gb_ref('crystal','UNION_CAVE_1F',15,0)
        program=specification(self.cache,water,'program');assert program
        contracts=json.loads(GUARDS.read_text())['submarine'];records=[]
        assert len(contracts)==36
        positions={mid:(x,y)for y,row in enumerate(GRID)for x,mid in enumerate(row)}
        for contract in contracts:
            game,pair,mid=(contract[k]for k in('game','pair','mid'))
            c=self.imp.cell_index(game)[pair,mid]
            assert c['pixel_sha256']==contract['sourceHash'] and c['behavior']==contract['sourceBehavior']
            assert c['layer_sha256']==contract['sourceLayers']
            x,y=positions[mid]
            ids,pixels,_=catalog.read_idx(self.cache/game/'data/generated/gba/native'/pair/'mids.idx')
            block=pixels[ids.index(mid)*256:(ids.index(mid)+1)*256]
            alpha=whole.crop((x*16,y*16,x*16+16,y*16+16)).getchannel('A').tobytes()
            assert alpha==bytes(255 if value//16==6 else 0 for value in block), 'Vessel silhouette changed'
            if mid in art_cells:
                cell=art_cells[mid]
                art=dict(kind='original',base=copy.deepcopy(water),asset=cell['asset'],
                    assetFileHash=cell['file_sha256'],assetPixelHash=cell['rgba_sha256'],
                    role='reverse_gen2_hoenn_complete_submarine_'+str(mid))
            else:
                art=self.native(water,'reverse_gen2_hoenn_submarine_water_lower_'+str(mid))
            art.update(animated=True,animation=copy.deepcopy(program),animationCategory='water',overMask='0'*256)
            row=self.row(game,pair,mid,'gen2',art,
                'One coherent original Crystal-style64x48 submarine was generated with the built-in image tool, uniformly normalized to the complete original logical canvas and reduced to four explicit flat colors. The entire left-facing hull, bow, tower, periscope, circular hatch, portholes and right-hand access pipe are retained together. Only the original bank6 vessel silhouette is opaque; source bank11 water is fully transparent over complete native animated Crystal cave water. The third16px row is entirely native water, matching actual original Surf collision41. No cropped or independently generated vessel fragments, stale Gen3 water, nonuniform feature scaling, changed collision/elevation or moved events are introduced. Full source image, all source planes and original behavior are frozen for every cartridge.')
            row['hoennOutdoorRemainingReview']=dict(kind='complete_generated_original_submarine',
                contract_sha256=digest(contract),whole_rgba_sha256=RGBA_HASH,
                original_canvas=[64,48],cell=[x,y],source_palette_bank_mask=6,
                source_cell_grid=GRID,native_water=water,complete_original_silhouette=True)
            records.append(dict(game=game,pair=pair,mid=mid,sourceHash=row['sourceHash'],
                sourceBehavior=row['sourceBehavior'],compositionPixelHash=row['compositionPixelHash'],
                occurrences=self.counts[game,pair,mid]))
        self.proofs['complete_submarine']=dict(art=proof,rows=records)
        return records

    def structural_native_aliases(self):
        from reverse_hoenn_review import native_geometry
        records=[]
        for contract in json.loads(GUARDS.read_text())['structural_native_aliases']:
            group=self.groups[contract['group_identity']]
            assert group['geometry']==contract['geometry']
            assert (group['family'],group['mid'])==(contract['family'],contract['mid'])
            canonical=contract['canonical']
            key=(canonical['game'],'gen2',canonical['pair'],canonical['mid'],None)
            module,_,prior=self.locations[key]
            assert module==canonical['module'] and digest(prior)==canonical['row_sha256']
            assert [catalog.sha(p)for p in native_geometry(self,key[0],key[2],key[3])]==group['geometry']
            art=artwork(prior)
            for field in ('overMask','animationCategory','assetPixelHash'):
                if field in prior:art[field]=copy.deepcopy(prior[field])
            art['role']='reverse_gen2_hoenn_explicit_structural_alias_'+prior['role']
            adapted_karst_material=group['family']=='general__fallarbor' and group['mid']in(523,554)
            if adapted_karst_material:
                # The exact east-wall shape witness uses Sootopolis gray.
                # Fallarbor's selected native mountain material is the native
                # golden UnionCave palette, matching its surrounding cap/face.
                art=self.native(self.gb_ref('crystal','UNION_CAVE_1F',6,3),
                    'reverse_gen2_hoenn_fallarbor_native_east_karst_wall')
                art['overMask']='0'*256
            for source in contract['source']:
                game,pair,mid=(source[k]for k in('game','pair','mid'))
                if (game,'gen2',pair,mid,None)in self.rows:continue
                c=self.imp.cell_index(game)[pair,mid]
                assert c['pixel_sha256']==source['sourceHash'] and c['behavior']==source['sourceBehavior']
                assert c['layer_sha256']==source['sourceLayers']
                assert c['behavior']==prior.get('sourceBehavior')
                row=self.row(game,pair,mid,'gen2',art,
                    'Individually reviewed paired source/counterpart contact binds this ordinary dry-cave, mountain, cliff, coast rock, ledge, threshold, waterfall corner or complete stair variant to the explicitly named existing complete native Crystal structural recipe. Its complete indexed under/mid/over geometry and source behavior are exactly equal, independently preserving left/right orientation and all shape boundaries. Native transparent exterior pixels expose the selected floor/water; no boulder or unknown object is replaced by flat ground. Shoal ice walls and brown cliffs whose only unique match used gray limestone were explicitly excluded for separate native material treatment. Entire original native GB pixels, masks, palette and any native animation remain exact; actual source collision, elevation, events, actors and logical layouts stay unchanged.')
                if not adapted_karst_material:
                    assert row['compositionPixelHash']==prior['compositionPixelHash']
                row['hoennOutdoorRemainingReview']=dict(kind='explicit_reviewed_native_structural_alias',
                    contract_sha256=digest(contract),canonical=canonical,
                    source_geometry=contract['geometry'],native_pixel_scale=1)
                records.append(dict(game=game,pair=pair,mid=mid,sourceHash=row['sourceHash'],
                    sourceBehavior=row['sourceBehavior'],compositionPixelHash=row['compositionPixelHash'],
                    occurrences=self.counts[game,pair,mid]))
        self.proofs['structural_native_aliases']=records
        return records

    def native_ice_and_brown_corners(self):
        records=[]
        for contract in json.loads(GUARDS.read_text())['native_ice_and_brown_corners']:
            group=self.groups[contract['group_identity']]
            assert group['geometry']==contract['geometry']
            game,map_id,bid,q=contract['native'];ref=self.gb_ref(game,map_id,bid,q)
            art=self.native(ref,'reverse_gen2_hoenn_native_ice_or_brown_corner_'+str(group['mid']))
            art['overMask']='0'*256
            ice=group['family']=='general__cave'
            for source in contract['source']:
                game,pair,mid=(source[k]for k in('game','pair','mid'))
                if (game,'gen2',pair,mid,None)in self.rows:continue
                c=self.imp.cell_index(game)[pair,mid]
                assert c['pixel_sha256']==source['sourceHash'] and c['behavior']==source['sourceBehavior']
                assert c['layer_sha256']==source['sourceLayers']
                if ice:
                    reason='The complete joined Shoal Cave Ice Room distinguishes slippery909 from ordinary snowy floor901/903/908/910/911, blocked frozen mass897/899, north cap889, handed walls/corners888/890/891/892/896/898/904/905/906, whole ice boulders893/894, and the two-cell vertical ladder887/895. Each receives an explicitly selected complete original Crystal Ice Path cell at native pixel size and its original native icy palette, including the actual glossy31q0 sliding ice, rough2q0 snow floor and whole native ladder rungs. The repeated two complete16px rung cells retain the source32px ladder span and original lower climbing coordinate. Common dry-cave geometry is deliberately not used to recolor this ice formation brown.'
                else:
                    reason='This exact brown-mountain convex front corner is separately selected from the gray limestone family that shares its indexed geometry. It receives the complete original brown Crystal Union Cave southwest or southeast corner at native pixel size, preserving direction and the adjoining brown mountain material.'
                row=self.row(game,pair,mid,'gen2',art,reason+' Frozen source RGBA, all native source planes and behavior are checked independently. The original ice puzzle movement, blocking, elevations, maps, ladder warp, events and actors remain unchanged.')
                row['hoennOutdoorRemainingReview']=dict(kind='explicit_native_ice_or_brown_terrain',
                    contract_sha256=digest(contract),complete_original_native_cell=True,native_ref=ref)
                records.append(dict(game=game,pair=pair,mid=mid,sourceHash=row['sourceHash'],
                    sourceBehavior=row['sourceBehavior'],compositionPixelHash=row['compositionPixelHash'],occurrences=self.counts[game,pair,mid]))
        self.proofs['native_ice_and_brown_corners']=records
        return records

    def braille_tablet(self):
        from classic_geometry_review import art as classic_art
        palette=[[189,189,255],[148,156,255],[107,99,255],[58,58,58]]
        colors={(58,16,165):(58,58,58),(66,74,107):(58,58,58),
            (90,49,181):(107,99,255),(115,74,206):(107,99,255),
            (148,115,222):(107,99,255),(181,148,255):(148,156,255),
            (189,206,230):(189,189,255)}
        records=[]
        for contract in json.loads(GUARDS.read_text())['braille_tablet']:
            game,pair,mid=(contract[k]for k in('game','pair','mid'))
            c=self.imp.cell_index(game)[pair,mid]
            assert c['pixel_sha256']==contract['sourceHash'] and c['behavior']==contract['sourceBehavior']
            assert c['layer_sha256']==contract['sourceLayers']
            art=classic_art(self,game,pair,mid,'sealed_chamber_exact_braille_clue',palette,colors,
                'reverse_gen2_hoenn_exact_braille_clue')
            row=self.row(game,pair,mid,'gen2',art,
                'This uniquely meaningful Sealed Chamber Braille clue has no equivalent vanilla Crystal glyph tile. Its complete original dot positions, spacing, highlight/shadow pixels and all native priority planes remain exact. The individually reviewed literal seven-color-to-four-color mapping adapts the backing rock to the same frozen Crystal Cianwood DAY blue material as adjoining reefs, with the actual bright Braille dots distinct from stone and their dark outlines retained. All opaque source RGB colors and native under/mid/over hashes are explicit, source animation/palette membership is independently excluded, and alpha, event/clue scripts, collision and coordinates remain unchanged. This named static clue exception never substitutes for ordinary native terrain or unknown objects.')
            row['hoennOutdoorRemainingReview']=dict(kind='exact_semantic_braille_clue',contract_sha256=digest(contract),all_dot_coordinates_unchanged=True)
            records.append(dict(game=game,pair=pair,mid=mid,sourceHash=row['sourceHash'],
                sourceBehavior=row['sourceBehavior'],compositionPixelHash=row['compositionPixelHash'],occurrences=self.counts[game,pair,mid]))
        self.proofs['braille_tablet']=records
        return records

    def underwater_canyon_tiers(self):
        from classic_geometry_review import art as classic_art
        records=[]
        for contract in json.loads(GUARDS.read_text())['underwater_canyon_tiers']:
            game,pair,mid=(contract[k]for k in('game','pair','mid'))
            assert pair=='general__underwater' and mid not in (624,736,737,738,739,740,741,742,743,744,745,746,747)
            c=self.imp.cell_index(game)[pair,mid]
            assert c['pixel_sha256']==contract['sourceHash'] and c['behavior']==contract['sourceBehavior']
            assert c['layer_sha256']==contract['sourceLayers']
            colors={tuple(entry[:3]):tuple(entry[3:])for entry in contract['colorMap']}
            ground=None
            if contract['native_floor_masks']:
                ground=dict(donor=self.underwater_ref(2,0),masks=contract['native_floor_masks'])
            art=classic_art(self,game,pair,mid,contract['feature'],contract['palette'],colors,
                'reverse_gen2_hoenn_preserved_deep_canyon_tier_'+str(mid),ground=ground)
            row=self.row(game,pair,mid,'gen2',art,
                'Whole original UnderwaterRoute127/128/134, Sealed Chamber and Seafloor Cavern scenes identify this specific part of the multi-depth reef/canyon architecture, shadowed floor transition or matching cave-opening frame. Crystal has no multi-depth underwater canyon counterpart. This individually reviewed named feature therefore keeps every original contour, handed tier edge, recess, depth transition and all priority/alpha planes in exact source geometry. The literal frozen RGB map uses the actual original Cianwood DAY blue, NITE blue or NITE deep-blue four-color palette according to the named source depth banks. When a complete original8px quadrant is byte-identical to the actual flat seafloor534, only that exact background quadrant is replaced by the already selected native Crystal seafloor glyph, preventing a rectangular color patch. Complete native Crystal ordinary reef/floor/boulder/kelp/water counterparts, the original generated submarine and exact Braille clue are separately authored and explicitly excluded from this derivative family. Source static animation/palette membership, all-plane hashes and every RGB are checked; collision, depth, Dive/no-surfacing rules, events, encounters, actors and logical layouts remain unchanged.')
            row['hoennOutdoorRemainingReview']=dict(kind='reviewed_unique_underwater_canyon_architecture',
                contract_sha256=digest(contract),source_depth_banks=contract['source_depth_banks'],
                source_edge_geometry_unchanged=True,native_floor_masks=contract['native_floor_masks'])
            records.append(dict(game=game,pair=pair,mid=mid,sourceHash=row['sourceHash'],
                sourceBehavior=row['sourceBehavior'],compositionPixelHash=row['compositionPixelHash'],occurrences=self.counts[game,pair,mid]))
        self.proofs['underwater_canyon_tiers']=records
        return records

    def native_shores_and_fortree_ground(self):
        from gb_theme_animation import specification
        from reverse_hoenn_review import ground_ref
        field=ground_ref(self,'gen2')
        sand=self.raw_ref('TILESET_KANTO',(48,57,57,48),'PALLET_TOWN')
        cave=self.gb_ref('crystal','UNION_CAVE_1F',2,0)
        water=self.gb_ref('crystal','UNION_CAVE_1F',15,0)
        program=specification(self.cache,water,'program');assert program
        records=[]
        for contract in json.loads(GUARDS.read_text())['native_shores_and_fortree_ground']:
            game,pair,mid=(contract[k]for k in('game','pair','mid'))
            if (game,'gen2',pair,mid,None)in self.rows:continue
            c=self.imp.cell_index(game)[pair,mid]
            assert c['pixel_sha256']==contract['sourceHash'] and c['behavior']==contract['sourceBehavior']
            assert c['layer_sha256']==contract['sourceLayers']
            kind=contract['kind']
            if kind=='native_cave_beach_shore':
                base=cave if contract['ground']=='cave'else sand
                parts=[dict(donor=water,srcX=q%2*8,srcY=q//2*8,w=8,h=8,x=q%2*8,y=q//2*8,animated=True)
                       for q,wet in enumerate(contract['native_water_grid'])if wet]
                art=self.composite(base,parts,'reverse_gen2_hoenn_remaining_native_shore_'+str(mid))
                if parts:art.update(animated=True,animation=program,animationCategory='water')
                reason='Individually reviewed actual cave-entry, tidal-shelf and sandy-coast source pictures retain their handed wet/dry extent on the original Crystal8px grid. Complete native animated Crystal cave water glyphs meet original Crystal cave floor or beach sand directly, following native Cianwood/Route40 shore conventions. Shallow shelf421/422/423 distinguishes its yellow dry shore from its gray wetted shelf; ordinary water shores distinguish actual blue water from the gray stony bank. Every snapped four-quadrant footprint is frozen per cartridge. No dry secret-base opening424/432 or unique cliff is included.'
            elif kind=='fortree_water_pool':
                art=self.native(water,'reverse_gen2_fortree_complete_native_pool');art.update(animated=True,animation=program,animationCategory='water')
                reason='This complete original Route119 pool is an entire open-water material, and receives the complete original animated Crystal water cell. It is not the adjoining narrow rainforest tree.'
            elif kind=='fortree_wet_grass':
                art=self.native(field,'reverse_gen2_fortree_wet_field')
                reason='This complete original Route120 shallow wet-lawn material receives the same complete original Crystal nonencounter lawn as its surrounding field. Original puddle and splash behavior remains intact.'
            elif kind=='fortree_south_ledge':
                prior=next(row for row in self.prior if row['style']=='gen2'and row.get('role')=='reverse_hoenn_south_ledge_center')
                art=artwork(prior);art['role']='reverse_gen2_fortree_native_south_jump_ledge'
                reason='The actual Route120 source explicitly has south-jump behavior and a complete horizontal south ledge. The whole native Crystal south-ledged stone band preserves its south-facing orientation and native pixel size.'
            else:
                art=self.classic_cliff('nw'if kind=='fortree_nw_cliff'else'ne','field')
                art['role']='reverse_gen2_fortree_complete_native_cliff_'+kind
                reason='The complete Route120 field/cliff joins have respectively northwest and northeast exterior field corners with stone mass opposite. Explicit handed complete native Crystal cliff pieces retain those directions and their selected field backdrop.'
            art['overMask']='0'*256
            row=self.row(game,pair,mid,'gen2',art,reason+' Full native source RGBA, every source plane and original behavior are checked. All original map layouts, source movement/collision/elevations, Surf, Dive, ledge and puddle rules, encounters, events and actor coordinates remain unchanged.')
            row['hoennOutdoorRemainingReview']=dict(kind=kind,contract_sha256=digest(contract),native_pixel_scale=1,
                whole_native_glyph_size=8 if contract['native_water_grid']else 16)
            records.append(dict(game=game,pair=pair,mid=mid,sourceHash=row['sourceHash'],
                sourceBehavior=row['sourceBehavior'],compositionPixelHash=row['compositionPixelHash'],occurrences=self.counts[game,pair,mid]))
        self.proofs['native_shores_and_fortree_ground']=records
        return records

    def coverage_manifests(self):
        by_scene=defaultdict(lambda:dict(new_cells=0,keys=[]))
        remaining=[]
        for group in self.group_list:
            for source in group['missing']:
                key=(source['game'],'gen2',source['pair'],source['mid'],None)
                if key not in self.rows:
                    remaining.append(source)
                    continue
                for context in source['contexts']:
                    item=by_scene[source['game'],context['map'],source['pair']]
                    item['new_cells']+=context['count']
                    item['keys'].append(source['mid'])
        scenes=[dict(game=game,map=name,pair=pair,new_cells=item['new_cells'],
                     mids=sorted(set(item['keys'])))for(game,name,pair),item in sorted(by_scene.items())]
        report=dict(affected_scenes=len(scenes),remaining_source_keys=len(remaining),
                    remaining_logical_cells=sum(s['occurrences']for s in remaining),
                    by_family={family:sum(s['occurrences']for s in remaining if ('primary'if s['mid']<512 else s['pair'])==family)
                               for family in sorted({'primary'if s['mid']<512 else s['pair']for s in remaining})})
        (self.out/'affected-scenes.json').write_text(json.dumps(scenes,indent=2)+'\n')
        (self.out/'remaining-source-keys.json').write_text(json.dumps(remaining,indent=2)+'\n')
        (self.out/'remaining-summary.json').write_text(json.dumps(report,indent=2)+'\n')
        return report

    def sky_pillar_architecture(self):
        from classic_geometry_review import art as classic_art
        records=[]
        sand=self.raw_ref('TILESET_KANTO',(48,57,57,48),'PALLET_TOWN')
        for contract in json.loads(GUARDS.read_text())['sky_pillar_architecture']:
            game,pair,mid=(contract[k]for k in('game','pair','mid'))
            assert pair=='general__pacifidlog'
            c=self.imp.cell_index(game)[pair,mid]
            assert c['pixel_sha256']==contract['sourceHash'] and c['behavior']==contract['sourceBehavior']
            assert c['layer_sha256']==contract['sourceLayers']
            colors={tuple(entry[:3]):tuple(entry[3:])for entry in contract['colorMap']}
            ground=dict(donor=sand,masks=contract['ground_masks'])if contract['ground_masks']else None
            art=classic_art(self,game,pair,mid,contract['feature'],contract['palette'],colors,
                'reverse_gen2_hoenn_sky_pillar_exact_puzzle_architecture_'+str(mid),ground=ground)
            row=self.row(game,pair,mid,'gen2',art,
                'Whole actual Sky Pillar floors, outside and summit establish this specific joined part of the unique bicycle-puzzle temple: intact or cracked paving, fragile-floor crack clue, continuous pit opening/edge, native stair span, stonework, tower trim, arrow or summit sky. Vanilla Crystal has no corresponding Sky Pillar fragile-floor puzzle/temple. Its complete original clue/crack and joined architecture geometry therefore remains exact in the actual original Crystal Saffron DAY four-color gray-stone material; the explicitly separate open summit sky uses the original Cianwood DAY blue palette. No cracks, arrows, stair rungs, thresholds or pit extents are omitted or replaced by generic flat floor. Exact known bank5 sand outside facade edges exposes original Crystal beach sand beneath the unchanged source silhouette. Ordinary Seafloor Cavern rock/flowing-water cells in the same atlas, native Pacifidlog stilt buildings, ordinary sand and boulders are explicitly outside this named architectural derivative family. All source planes, behavior, palette/static membership and every source RGB are frozen; original bicycle requirements, fragile-floor/falling behavior, elevations, blocking, stairs/warps, events, Rayquaza and actors stay unchanged.')
            row['hoennOutdoorRemainingReview']=dict(kind='reviewed_unique_sky_pillar_puzzle_architecture',
                contract_sha256=digest(contract),source_clue_and_pit_geometry_unchanged=True)
            records.append(dict(game=game,pair=pair,mid=mid,sourceHash=row['sourceHash'],
                sourceBehavior=row['sourceBehavior'],compositionPixelHash=row['compositionPixelHash'],occurrences=self.counts[game,pair,mid]))
        self.proofs['sky_pillar_architecture']=records
        return records

    def native_ash_and_sky_exterior(self):
        from reverse_kanto_review import runs
        ash=self.gb_ref('crystal','UNION_CAVE_1F',2,0)
        gray=[[222,255,222],[173,173,173],[107,107,107],[58,58,58]]
        ash['palettes']=[copy.deepcopy(gray)for _ in range(8)]
        grass=self.raw_ref('TILESET_JOHTO',(4,4,4,4),'NEW_BARK_TOWN')
        grass['palettes']=[copy.deepcopy(gray)for _ in range(8)]
        sand=self.raw_ref('TILESET_KANTO',(48,57,57,48),'PALLET_TOWN')
        boulder=self.gb_ref('crystal','UNION_CAVE_1F',24,0)
        left=[6,4,3,2,1,1,1,0,0,0,0,0,0,1,1,2]
        right=[11,12,13,14,15,15,16,16,16,16,16,16,16,16,15,13]
        mask=[left[y]<=x<right[y]for y in range(16)for x in range(16)]
        records=[]
        for contract in json.loads(GUARDS.read_text())['native_ash_and_sky_exterior']:
            game,pair,mid=(contract[k]for k in('game','pair','mid'));c=self.imp.cell_index(game)[pair,mid]
            assert c['pixel_sha256']==contract['sourceHash'] and c['behavior']==contract['sourceBehavior']
            assert c['layer_sha256']==contract['sourceLayers'];kind=contract['kind']
            if kind=='ash_encounter_grass':
                art=self.composite(ash,[dict(donor=grass,gbForeground=True,srcX=0,srcY=0,w=16,h=16,x=0,y=0)],
                    'reverse_gen2_hoenn_complete_native_ash_grass')
                art['overMask']=''.join('1'if y>=8 and self.neutral(grass).getpixel((x,y))[0]!=255 else'0'for y in range(16)for x in range(16))
                reason='Actual Route113 source522 is walkable soot/encounter grass, with original behavior292 and collision0, rather than boulder or wall. Four complete original native Crystal8px leaf glyphs retain their original pixel scale in the same native gray DAY ash palette as the surrounding selected ash, over the exact existing ash material. Only genuine lower native leaves cover actor feet.'
            elif kind=='cleared_ash_lawn':
                art=self.native(ash,'reverse_gen2_hoenn_complete_native_cleared_ash')
                reason='Actual cleared ash536 is the complete walkable surface left after the ash-covered grass is cleared. It uses the exact original Crystal gray pebble ash material already selected for Fallarbor and its forest exterior, preserving the functional visual distinction from522 grass.'
            elif kind=='cave_backing':
                art=self.native(self.gb_ref('crystal','UNION_CAVE_1F',4,3),'reverse_gen2_hoenn_fossil_tunnel_raised_backing')
                reason='This source is blocked raised backfill of the Fossil Maniac tunnel, never an open walking floor, and receives the complete original Crystal raised stone mass.'
            elif kind=='sky_pillar_sand':
                art=self.native(sand,'reverse_gen2_hoenn_complete_sky_pillar_beach_sand')
                reason='The independently reviewed complete Sky Pillar exterior ground cell is ordinary beach sand. It receives the complete existing native Crystal beach-sand glyph; source sand and bicycle/encounter behavior stay intact.'
            else:
                art=self.composite(sand,[dict(donor=boulder,srcX=s['x'],srcY=s['y'],**s)for s in runs(mask)],
                    'reverse_gen2_hoenn_sky_pillar_whole_native_boulder')
                reason='This fixed whole16px Sky Pillar exterior boulder uses one complete original Crystal round cave boulder at native pixel size. Only its verified exterior floor becomes the selected native beach sand, removing the background rectangle while retaining the entire rock outline and shading.'
            art.setdefault('overMask','0'*256)
            row=self.row(game,pair,mid,'gen2',art,reason+' Every source RGBA and plane hash and original behavior is frozen. Source grass/ash clearing, encounters, collision, elevations, scripts, actors, movement and maps remain unchanged.')
            row['hoennOutdoorRemainingReview']=dict(kind=kind,contract_sha256=digest(contract),complete_original_native_glyphs=True)
            records.append(dict(game=game,pair=pair,mid=mid,sourceHash=row['sourceHash'],sourceBehavior=row['sourceBehavior'],compositionPixelHash=row['compositionPixelHash'],occurrences=self.counts[game,pair,mid]))
        self.proofs['native_ash_and_sky_exterior']=records
        return records

    def karst_architecture(self):
        from classic_geometry_review import art as classic_art
        from reverse_hoenn_review import ground_ref
        records=[]
        for contract in json.loads(GUARDS.read_text())['karst_architecture']:
            game,pair,mid=(contract[k]for k in('game','pair','mid'));assert pair=='general__fallarbor'
            c=self.imp.cell_index(game)[pair,mid]
            assert c['pixel_sha256']==contract['sourceHash'] and c['behavior']==contract['sourceBehavior']
            assert c['layer_sha256']==contract['sourceLayers']
            colors={tuple(entry[:3]):tuple(entry[3:])for entry in contract['colorMap']}
            ground=dict(donor=ground_ref(self,'gen2'),masks=contract['ground_masks'])if contract['ground_masks']else None
            art=classic_art(self,game,pair,mid,contract['feature'],contract['palette'],colors,
                'reverse_gen2_hoenn_preserved_jagged_karst_'+str(mid),ground=ground)
            row=self.row(game,pair,mid,'gen2',art,
                'Full original Route114/115 and Fossil Maniac tunnel scenes establish this specific joined part of the distinctive multi-tier jagged Hoenn karst, its climbing cuts and high northern fossil cut. Ordinary complete native Crystal cliff/cave/rock counterparts are separately selected first. These remaining unusual layered/diagonal formations lack a complete native counterpart, so their entire actual ledges, stepped mass, narrow climbing cuts, openings and handed recesses remain exact in the same original Crystal DAY golden-stone four-color palette as the selected native mountain cap/face family. Every original ordinary field pixel in the explicitly reviewed primary field bank2 instead exposes the selected native Crystal lawn, including every irregular outer corner, so no brown rectangle or original field color remains. No encounter grass, ash clearing, tree, house, berry soil or unknown object is included. Every RGB map, complete source image, original priority/alpha plane and static/palette membership is independently guarded. Source blocking, elevations, climb/warp/event clues, water/encounter rules, scripts, actors and logical layouts remain unchanged.')
            row['hoennOutdoorRemainingReview']=dict(kind='reviewed_unique_jagged_karst_architecture',contract_sha256=digest(contract),all_climb_cut_and_entrance_geometry_unchanged=True)
            records.append(dict(game=game,pair=pair,mid=mid,sourceHash=row['sourceHash'],sourceBehavior=row['sourceBehavior'],compositionPixelHash=row['compositionPixelHash'],occurrences=self.counts[game,pair,mid]))
        self.proofs['karst_architecture']=records
        return records

    def native_small_cave_families(self):
        records=[]
        for contract in json.loads(GUARDS.read_text())['native_small_cave_families']:
            game,pair,mid=(contract[k]for k in('game','pair','mid'));c=self.imp.cell_index(game)[pair,mid]
            assert c['pixel_sha256']==contract['sourceHash'] and c['behavior']==contract['sourceBehavior']
            assert c['layer_sha256']==contract['sourceLayers'];bid,q=contract['native']
            if bid=='sand':
                art=self.native(self.raw_ref('TILESET_KANTO',(48,57,57,48),'PALLET_TOWN'),
                    'reverse_gen2_hoenn_mirage_whole_native_desert_sand')
            elif bid=='three_rocks':
                floor=self.gb_ref('crystal','UNION_CAVE_1F',2,0)
                glyph=self.gb_ref('crystal','UNION_CAVE_1F',4,2)
                art=self.composite(floor,[dict(donor=glyph,srcX=0,srcY=0,w=8,h=8,x=x,y=y)
                    for x,y in((0,0),(8,0),(4,8))], 'reverse_gen2_hoenn_mirage_three_whole_native_rocks')
            else:
                art=self.native(self.gb_ref('crystal','UNION_CAVE_1F',bid,q),
                    'reverse_gen2_hoenn_native_small_cave_'+str(mid))
            art['overMask']='0'*256
            row=self.row(game,pair,mid,'gen2',art,
                'The complete native source family is individually reviewed as ordinary Mirage Tower cave/desert material or the six-cell Rusturf south-ledge cap/face group. Exact named complete original Crystal Union Cave16px floor, raised stone, handed north cap/side/front/inner-corner, whole stair flight or ladder is selected at its original pixel size. Whole original8px rock glyphs form each explicit three-rock cluster; complete native beach/desert-sand glyphs retain the original sand region. The Rusturf joined upper563/545/564 and lower576/572/577 grid preserves the complete handed mass and original572 south-jump rule without treating it as a portal. Mirage ladder positions and complete source two-cell shaft span retain whole native16px rung cells; original fragile-floor/digging/bicycle/arrow and sand behaviors remain exact. Original source image, every source plane, behavior, collision, heights, warps, events and logical layouts are frozen independently per cartridge. No unknown object is filled with generic ground.')
            row['hoennOutdoorRemainingReview']=dict(kind=contract['feature'],contract_sha256=digest(contract),
                native_cell=contract['native'],pixel_scale=1)
            records.append(dict(game=game,pair=pair,mid=mid,sourceHash=row['sourceHash'],sourceBehavior=row['sourceBehavior'],compositionPixelHash=row['compositionPixelHash'],occurrences=self.counts[game,pair,mid]))
        self.proofs['native_small_cave_families']=records
        return records

    def meteor_falls(self):
        from classic_geometry_review import art as classic_art
        from gb_theme_animation import specification
        contracts=json.loads(GUARDS.read_text());records=[]
        water=self.gb_ref('crystal','UNION_CAVE_1F',15,0)
        program=specification(self.cache,water,'program');assert program
        for family in('meteor_falls_architecture','meteor_falls_native_shores','meteor_falls_native_floor'):
            for contract in contracts[family]:
                game,pair,mid=(contract[k]for k in('game','pair','mid'));assert pair=='general__meteor_falls'
                c=self.imp.cell_index(game)[pair,mid]
                assert c['pixel_sha256']==contract['sourceHash'] and c['behavior']==contract['sourceBehavior']
                assert c['layer_sha256']==contract['sourceLayers']
                if family=='meteor_falls_architecture':
                    colors={tuple(entry[:3]):tuple(entry[3:])for entry in contract['colorMap']}
                    art=classic_art(self,game,pair,mid,contract['feature'],contract['palette'],colors,
                        'reverse_gen2_hoenn_meteor_falls_vault_architecture_'+str(mid))
                    reason='The complete original Meteor Falls joined chambers identify this specific part of the unusual vaulted cavern: full-height fluted pillars, long stalactite bands, stratified retaining masses, wet stepped terraces, hanging formations or their actual floor/cap interfaces. Ordinary native Crystal water, shore corners, stairs and walking-floor counterparts are separately selected first. These remaining complete shapes lack a suitable full native counterpart, so every original contour, fluted shaft, column base, recess, ledge and handed interface remains exact in four explicit original Crystal colors. Ordinary stone uses the native golden-stone DAY palette; static puddle terraces retain both original Crystal blue-water shades and golden-stone/outline shades so wet cells remain visibly distinct. Every original native priority/alpha plane and clue/terrace contour stays exact, with guarded static/source animation membership. Animated water behind static fluted formations is explicitly held for a separate bounded animated-ground recipe rather than frozen or painted over.'
                elif family=='meteor_falls_native_shores':
                    cliff=self.classic_cliff(contract['shape'],'field')
                    parts=[dict(donor=water,srcX=0,srcY=0,w=16,h=16,x=0,y=0,animated=True)]+copy.deepcopy(cliff['parts'])
                    art=self.composite(None,parts,'reverse_gen2_hoenn_meteor_native_water_cliff_'+str(mid))
                    art.update(animated=True,animation=copy.deepcopy(program),animationCategory='water',overMask='0'*256)
                    reason='This separately reviewed ordinary water/cliff bank has an explicit northwest/northeast cutout or east/west face. Complete original Crystal eight-pixel cliff modules keep that handed bank direction, while only their verified exterior field is omitted over the complete original animated Crystal cave water. No original water or brown exterior rectangle remains around a stone corner. All native glyph pixels remain1:1 and source water/Surf behavior stays exact.'
                else:
                    art=self.native(self.gb_ref('crystal','UNION_CAVE_1F',2,0),'reverse_gen2_hoenn_meteor_native_walking_floor')
                    art['overMask']='0'*256
                    reason='This complete actual Meteor Falls flat walking-floor/blocked matching backfill picture is ordinary stone surface, independently separated from the vault walls, pillar shafts, stepped terrace edges and water. It receives the complete original Crystal cave-floor glyph at its original pixel size.'
                row=self.row(game,pair,mid,'gen2',art,reason+' Per-cartridge complete source RGBA, every original source plane and behavior are frozen. Original Surf/waterfall/puddle/jump movement, source depth/collision/elevations, entrances, encounters, scripts, actors and logical layouts remain unchanged.')
                row['hoennOutdoorRemainingReview']=dict(kind=family,contract_sha256=digest(contract),complete_joined_feature=True,
                    original_critical_geometry_preserved=family=='meteor_falls_architecture')
                records.append(dict(game=game,pair=pair,mid=mid,sourceHash=row['sourceHash'],sourceBehavior=row['sourceBehavior'],compositionPixelHash=row['compositionPixelHash'],occurrences=self.counts[game,pair,mid]))
        self.proofs['meteor_falls']=records
        return records

    def meteor_falls_compound(self):
        from classic_geometry_review import art as classic_art
        records=[]
        for contract in json.loads(GUARDS.read_text())['meteor_falls_compound']:
            game,pair,mid=(contract[k]for k in('game','pair','mid'));assert pair=='general__meteor_falls'
            c=self.imp.cell_index(game)[pair,mid]
            assert c['pixel_sha256']==contract['sourceHash'] and c['behavior']==contract['sourceBehavior']
            assert c['layer_sha256']==contract['sourceLayers']
            assert set(contract['ground']['masks'])=={'under','mid'}
            assert all(mask=='1'*256 for mask in contract['ground']['masks'].values())
            colors={tuple(entry[:3]):tuple(entry[3:])for entry in contract['colorMap']}
            art=classic_art(self,game,pair,mid,contract['feature'],contract['palette'],colors,
                'reverse_gen2_hoenn_meteor_exact_vault_over_animated_water_'+str(mid),ground=contract['ground'])
            row=self.row(game,pair,mid,'gen2',art,
                'This bounded Meteor Falls compound has complete native animated source water on all256 UNDER pixels and all256 duplicate MID pixels, with its static thin fluted column/terrace shape separately in OVER. The complete original selected Crystal cave-water program replaces both entire original water planes at their exact native timing. Every original static OVER pixel, alpha and actor-priority boundary remains source-exact in the selected four-color original Crystal golden-stone palette. The independent validator proves full coverage of every source animated water quad/palette pixel and guards the source manifest, all three source planes and every RGB; the original native architecture never animates and no original Gen3 water remains around or behind it. The complete16x32 column shaft/base and every surrounding cut are retained without stretching or cropping a different native object. All original source movement, collision, elevation, water/Surf rules, events, actors and layouts stay unchanged; Off restores original native source art and animation.')
            row['hoennOutdoorRemainingReview']=dict(kind='bounded_exact_vault_over_native_animated_water',contract_sha256=digest(contract),
                original_static_over_geometry_preserved=True,source_animated_ground_planes=['under','mid'],source_animated_water_pixels_covered=512)
            records.append(dict(game=game,pair=pair,mid=mid,sourceHash=row['sourceHash'],sourceBehavior=row['sourceBehavior'],compositionPixelHash=row['compositionPixelHash'],occurrences=self.counts[game,pair,mid]))
        self.proofs['meteor_falls_compound']=records
        return records

    def navel_rock_native(self):
        blue=[[189,189,255],[148,156,255],[107,99,255],[58,58,58]]
        sky=self.raw_ref('TILESET_JOHTO',(0,0,0,0),'VIOLET_CITY')
        sky['palettes']=[copy.deepcopy(blue)for _ in range(8)]
        assert len(set(self.gb_image(sky).get_flattened_data()))==1
        floor=self.gb_ref('crystal','UNION_CAVE_1F',2,0)
        rock=self.gb_ref('crystal','UNION_CAVE_1F',4,2)
        records=[]
        for contract in json.loads(GUARDS.read_text())['navel_rock_native']:
            game,pair,mid=(contract[k]for k in('game','pair','mid'));assert pair=='general__navel_rock'
            c=self.imp.cell_index(game)[pair,mid]
            assert c['pixel_sha256']==contract['sourceHash'] and c['behavior']==contract['sourceBehavior']
            assert c['layer_sha256']==contract['sourceLayers'];bid,q=contract['native']
            if bid=='sky':
                art=self.native(sky,'reverse_gen2_hoenn_navel_native_open_sky')
            elif bid in('sky_nw','sky_ne'):
                art=self.classic_cliff('nw'if bid=='sky_nw'else'ne','field');art['base']=copy.deepcopy(sky)
                art['role']='reverse_gen2_hoenn_navel_native_cliff_over_sky_'+str(mid)
            elif bid in('three_rocks','four_rocks'):
                positions=((0,0),(8,0),(4,8))if bid=='three_rocks'else((0,0),(8,0),(0,8),(8,8))
                art=self.composite(floor,[dict(donor=rock,srcX=0,srcY=0,w=8,h=8,x=x,y=y)for x,y in positions],
                    'reverse_gen2_hoenn_navel_whole_native_'+bid)
            else:
                art=self.native(self.gb_ref('crystal','UNION_CAVE_1F',bid,q),
                    'reverse_gen2_hoenn_navel_complete_native_terrain_'+str(mid))
            art['overMask']='0'*256
            row=self.row(game,pair,mid,'gen2',art,
                'The complete joined Navel Rock summit, lower peak, descent, fork and entrance cave scenes distinguish the ordinary native stone floor/backfill, full raised mass, actual handed cap/side/front/inward wall joins, complete fixed boulder/explicit three- or four-rock cluster, north/south stair treads and full ladder shafts. Each receives the explicitly selected complete original Crystal Union Cave16px counterpart, or complete original8px small-rock glyphs at the original scale. The actual blank summit backdrop uses an original complete blank Crystal glyph in the original Cianwood DAY blue palette, never water waves or encounter grass. Complete native cliff corners expose that selected sky only outside their genuine stone silhouette. Ladder/shadow/terrace roles remain distinct, original source32px ladder spans retain two full native rung cells, and no floor/pit/portal is inferred solely from thumbnail color. All per-game original source images, planes, behaviors, blocking, heights, summit encounters, stairs, warps, events, actors and source logical layouts remain unchanged.')
            row['hoennOutdoorRemainingReview']=dict(kind='explicit_native_navel_rock_terrain',contract_sha256=digest(contract),native=contract['native'],pixel_scale=1)
            records.append(dict(game=game,pair=pair,mid=mid,sourceHash=row['sourceHash'],sourceBehavior=row['sourceBehavior'],compositionPixelHash=row['compositionPixelHash'],occurrences=self.counts[game,pair,mid]))
        self.proofs['navel_rock_native']=records
        return records

    def volcanic_region(self):
        from classic_geometry_review import art as classic_art
        from gb_theme_animation import specification
        from reverse_hoenn_review import ground_ref
        from reverse_kanto_review import runs

        field = ground_ref(self, 'gen2')
        stone = self.raw_ref('TILESET_JOHTO', (60,) * 4, 'VIOLET_CITY')
        gray = [[222, 255, 222], [173, 173, 173], [107, 107, 107], [58, 58, 58]]
        lava = self.gb_ref('crystal', 'BLACKTHORN_GYM_1F', 43, 1)
        lava_program = specification(self.cache, lava, 'program')
        assert lava_program
        lava_parts = [dict(donor=lava, srcX=0, srcY=0, x=x, y=0, w=8, h=16, animated=True)
                      for x in (0, 8)]
        grass = self.raw_ref('TILESET_JOHTO', (4,) * 4, 'NEW_BARK_TOWN')
        grass_mask = ''.join('1' if y >= 8 and self.neutral(grass).getpixel((x, y))[0] != 255 else '0'
                             for y in range(16) for x in range(16))
        stairs = self.gb_ref('crystal', 'UNION_CAVE_1F', 18, 3)
        upper = self.active_art('emerald', 'general__lavaridge', 206)
        lower = self.active_art('emerald', 'general__lavaridge', 198)
        middle_row = next(row for row in self.prior if row['style'] == 'gen2' and
                          row.get('role') == 'reverse_gen2_hoenn_complete_native_conifer_8')
        middle = artwork(middle_row)
        middle['overMask'] = middle_row['overMask']
        tree_halves = {0: upper, 8: middle, 16: lower}
        cliff_cells = {
            531: (4, 0), 532: (4, 1), 533: (6, 1), 539: (12, 2), 541: (14, 3),
            649: (4, 2), 796: (6, 3), 798: (6, 1), 810: (12, 2), 811: (12, 3),
            812: (14, 3), 818: (6, 3), 820: (4, 2), 826: (4, 0), 827: (4, 1),
            828: (6, 1), 931: (4, 1), 932: (4, 1),
        }
        fence_mids = {(0,): 313, (8,): 650, (0, 8): 657}

        def tree_with_backing(art, backing, ash):
            art = copy.deepcopy(art)
            if ash:
                for part in art['parts']:
                    part['donor']['palettes'] = [copy.deepcopy(gray) for _ in range(8)]
            if backing in ('front', 'east'):
                face = self.classic_cliff('front', 'front') if backing == 'front' else self.classic_cliff('e', 'field')
                art['base'] = face['base']
                art['parts'] = face['parts'] + art['parts']
            else:
                art['base'] = copy.deepcopy(field if backing == 'field' else stone)
            assert len(art['parts']) <= 32
            return art

        def native_art(mid, plan):
            role, *details = plan
            if role in ('field', 'stone', 'stairs'):
                donor = {'field': field, 'stone': stone, 'stairs': stairs}[role]
                art = self.native(donor, 'reverse_gen2_hoenn_volcano_native_' + role)
            elif role == 'lava':
                art = self.composite(None, lava_parts, 'complete_native_lava_columns')
                art.update(animated=True, animation=lava_program, animationCategory='water')
            elif role == 'conifer':
                height, backing = details
                art = tree_with_backing(tree_halves[height], backing, backing == 'ash')
            elif role == 'round_tree':
                quadrant, ash, backing = details
                art = tree_with_backing(self.park_tree_art(quadrant, stone), backing, ash)
            elif role == 'grass':
                leaf = copy.deepcopy(grass)
                if details[0]:
                    leaf['palettes'] = [copy.deepcopy(gray) for _ in range(8)]
                art = self.composite(stone, [dict(donor=leaf, gbForeground=True, srcX=0, srcY=0,
                                                 x=0, y=0, w=16, h=16)], 'volcanic_grass')
                art['overMask'] = grass_mask
            else:
                assert role == 'fence'
                art = self.active_art('emerald', 'general__mauville', fence_mids[tuple(details[0])])
                art['base'] = copy.deepcopy(stone)
            art['role'] = f'reverse_gen2_hoenn_volcano_native_{role}_{mid}'
            art.setdefault('overMask', '0' * 256)
            return art

        records = []
        for contract in json.loads(GUARDS.read_text())['volcanic_region']:
            game, pair, mid = (contract[k] for k in ('game', 'pair', 'mid'))
            assert pair == 'general__lavaridge'
            cell = self.imp.cell_index(game)[pair, mid]
            assert cell['pixel_sha256'] == contract['sourceHash']
            assert cell['behavior'] == contract['sourceBehavior']
            assert cell['layer_sha256'] == contract['sourceLayers']
            kind = contract['kind']
            if kind == 'native':
                art = native_art(mid, contract['plan'])
                evidence = 'The joined volcanic scenes identify this complete native Crystal terrain or plant counterpart. Narrow trees retain their full 16 by 32 native crown and roots, with an intact leaf repeat where the source column is taller. Round trees retain all four native National Park quarters. Native ash-gray leaves sit over the selected stone backing. The original-size north/south tread glyph follows the actual stair orientation. Each fence post has a complete cap, face and foot. Ordinary lava uses the complete native Blackthorn Gym program.'
            elif kind == 'lava_bank':
                cliff = self.gb_ref('crystal', 'UNION_CAVE_1F', *cliff_cells[mid])
                rock_mask = [bit == '0' for bit in contract['lava_mask']]
                parts = copy.deepcopy(lava_parts)
                parts.extend(dict(donor=cliff, srcX=span['x'], srcY=span['y'], **span)
                             for span in runs(rock_mask))
                assert len(parts) <= 32
                art = self.composite(None, parts, f'reverse_gen2_hoenn_native_lava_bank_{mid}')
                art.update(animated=True, animation=lava_program, animationCategory='water', overMask='0' * 256)
                evidence = 'The exact original lava silhouette is identified by the same RGB material in the independently reviewed complete lava cells. The original Crystal lava program fills that footprint. A full native stone cell supplies the correct handed cliff texture inside the verified rock mask, so irregular corners expose the lava.'
            else:
                assert kind == 'classic'
                colors = {tuple(row[:3]): tuple(row[3:]) for row in contract['color_map']}
                backing = contract['backing']
                ground = None
                if contract['backing_masks']:
                    donor = {'field': field, 'stone': stone, 'lava': lava}[backing]
                    ground = dict(donor=donor, masks=contract['backing_masks'])
                    if backing == 'lava':
                        assert set(ground['masks']) == {'under', 'mid'}
                        assert all(mask == '1' * 256 for mask in ground['masks'].values())
                        ground.update(animation=lava_program, repeatWidth=8)
                art = classic_art(self, game, pair, mid, contract['feature'], contract['palette'], colors,
                                  f'reverse_gen2_hoenn_volcanic_geometry_{mid}', ground=ground)
                evidence = 'The individually reviewed volcanic galleries, cable-car structures and Magma Hideout machines use complete source geometry in four original Crystal colors. The literal RGB mapping retains every slope, opening, climbing rock, panel, cable and priority boundary in the named feature. Verified exterior field or stone pixels use the selected native backing. The magma apparatus above lava keeps its static foreground over the complete native animated lava planes.'
            row = self.row(game, pair, mid, 'gen2', art, evidence +
                           ' The independent source guards pin every plane and behavior. Original collision, elevations, stairs, bicycle hops, cable-car events and map layouts are preserved.')
            row['hoennOutdoorRemainingReview'] = dict(kind='reviewed_volcanic_region_' + kind,
                                                     contract_sha256=digest(contract), pixel_scale=1)
            records.append(dict(game=game, pair=pair, mid=mid, sourceHash=row['sourceHash'],
                                sourceBehavior=row['sourceBehavior'], compositionPixelHash=row['compositionPixelHash'],
                                occurrences=self.counts[game, pair, mid]))
        self.proofs['volcanic_region'] = records
        return records

    def reviewed_terrain(self, guard_key):
        from gb_theme_animation import specification
        from reverse_hoenn_review import ground_ref
        from reverse_kanto_review import runs

        field = ground_ref(self, 'gen2')
        sand = self.raw_ref('TILESET_KANTO', (48, 57, 57, 48), 'PALLET_TOWN')
        water = self.gb_ref('crystal', 'UNION_CAVE_1F', 15, 0)
        water_program = specification(self.cache, water, 'program')
        assert water_program
        terrain = {'field': field, 'sand': sand, 'water': water}
        conifer_rows = {
            0: self.active_art('emerald', 'general__lavaridge', 206),
            16: self.active_art('emerald', 'general__lavaridge', 198),
        }
        middle = next(row for row in self.prior if row['style'] == 'gen2' and
                      row.get('role') == 'reverse_gen2_hoenn_complete_native_conifer_8')
        conifer_rows[8] = artwork(middle)
        conifer_rows[8]['overMask'] = middle['overMask']
        fence_mids = {(0,): 313, (8,): 650, (0, 8): 657}
        gray = [[222, 255, 222], [173, 173, 173], [107, 107, 107], [58, 58, 58]]

        def stone_ref(contract):
            ref = self.gb_ref('crystal', 'UNION_CAVE_1F', *contract['ref'])
            if contract.get('gray'):
                ref['palettes'] = [copy.deepcopy(gray) for _ in range(8)]
            return ref

        def add_foreground(base, parts, role):
            if base == 'water':
                water_part = dict(donor=water, x=0, y=0, w=16, h=16, animated=True)
                art = self.composite(None, [water_part] + parts, role)
                art.update(animated=True, animation=water_program, animationCategory='water')
            else:
                art = self.composite(terrain[base], parts, role)
            assert len(art['parts']) <= 32
            return art

        records = []
        for contract in json.loads(GUARDS.read_text())[guard_key]:
            game, pair, mid = (contract[k] for k in ('game', 'pair', 'mid'))
            source = self.imp.cell_index(game)[pair, mid]
            assert source['pixel_sha256'] == contract['sourceHash']
            assert source['behavior'] == contract['sourceBehavior']
            assert source['layer_sha256'] == contract['sourceLayers']
            kind, base = contract['kind'], contract['base']
            role = f'reverse_gen2_hoenn_reviewed_{kind}_{mid}'
            if kind == 'surface':
                ref = stone_ref(contract) if base == 'stone' else terrain[base]
                art = self.native(ref, role)
                if base == 'water':
                    art.update(animated=True, animation=water_program, animationCategory='water')
            elif kind == 'mask':
                top = stone_ref(contract) if contract['top'] == 'stone' else terrain[contract['top']]
                bits = contract['mask']
                if bits == '1' * 256:
                    art = self.native(top, role)
                elif bits == '0' * 256:
                    art = self.native(terrain[base], role)
                    if base == 'water':
                        art.update(animated=True, animation=water_program, animationCategory='water')
                else:
                    parts = [dict(donor=top, srcX=span['x'], srcY=span['y'], **span)
                             for span in runs([bit == '1' for bit in bits])]
                    art = add_foreground(base, parts, role)
            elif kind == 'conifer':
                tree = conifer_rows[contract['height']]
                art = add_foreground(base, copy.deepcopy(tree['parts']), role)
                art['overMask'] = tree['overMask']
            elif kind == 'picket':
                art = self.active_art('emerald', 'general__mauville', fence_mids[tuple(contract['columns'])])
                art['base'] = copy.deepcopy(terrain[base])
                art['role'] = role
            else:
                assert kind == 'boulder'
                donor = self.gb_ref('crystal', 'UNION_CAVE_1F', 24, 0)
                left = [6, 4, 3, 2, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 2]
                right = [11, 12, 13, 14, 15, 15, 16, 16, 16, 16, 16, 16, 16, 16, 15, 13]
                mask = [left[y] <= x < right[y] for y in range(16) for x in range(16)]
                parts = [dict(donor=donor, srcX=span['x'], srcY=span['y'], **span) for span in runs(mask)]
                art = add_foreground(base, parts, role)
            art.setdefault('overMask', '0' * 256)
            row = self.row(game, pair, mid, 'gen2', art,
                           'The individually inspected source joins establish the terrain or complete plant and fence role. Original Crystal field, sand, cliff and animated water supply the selected surfaces at native pixel scale. A verified source terrain mask keeps the actual shoreline or ledge boundary, with the selected backing outside every corner. Trees and pickets retain complete native modules. Each separate whole boulder keeps its entire original Crystal silhouette. The source hashes pin all layers and behavior. Source collision, height, movement, encounters and map events are preserved.')
            row['hoennOutdoorRemainingReview'] = dict(kind=kind, contract_sha256=digest(contract),
                                                     source_family=guard_key, pixel_scale=1)
            records.append(dict(game=game, pair=pair, mid=mid, sourceHash=row['sourceHash'],
                                sourceBehavior=row['sourceBehavior'], compositionPixelHash=row['compositionPixelHash'],
                                occurrences=self.counts[game, pair, mid]))
        self.proofs[guard_key] = records
        return records

    def volcanic_steam(self):
        from classic_geometry_review import art as classic_art

        records = []
        for contract in json.loads(GUARDS.read_text())['volcanic_steam']:
            game, pair, mid = (contract[k] for k in ('game', 'pair', 'mid'))
            assert pair == 'general__lavaridge'
            cell = self.imp.cell_index(game)[pair, mid]
            assert cell['pixel_sha256'] == contract['sourceHash']
            assert cell['behavior'] == contract['sourceBehavior']
            assert cell['layer_sha256'] == contract['sourceLayers']
            colors = {tuple(entry[:3]): tuple(entry[3:]) for entry in contract['colorMap']}
            art = classic_art(self, game, pair, mid, contract['feature'], contract['palette'], colors,
                              f'reverse_gen2_hoenn_native_steam_over_classic_rock_{mid}',
                              ground=contract['ground'], native_over=contract['nativeOver'])
            assert art['classicGeometry']['animationManifestHash'] == contract['sourceManifestHash']
            row = self.row(game, pair, mid, 'gen2', art,
                           'The original steam effect plays on its independently guarded native foreground plane. Its expanded indexed bank, timing, alpha and priority are retained. A complete original Crystal plateau supplies the flat volcanic terrain. The four distinct cliff cells retain their original slope contours in the same golden Crystal palette. Every native source layer and behavior is pinned. The original cave layouts, collision, elevation, vents and steam timing are preserved.')
            row['hoennOutdoorRemainingReview'] = dict(kind='native_steam_over_classic_terrain',
                                                     contract_sha256=digest(contract),
                                                     native_steam_bank='lavaridge_steam',
                                                     selected_terrain=contract['static_terrain'])
            records.append(dict(game=game, pair=pair, mid=mid, sourceHash=row['sourceHash'],
                                sourceBehavior=row['sourceBehavior'], compositionPixelHash=row['compositionPixelHash'],
                                occurrences=self.counts[game, pair, mid]))
        self.proofs['volcanic_steam'] = records
        return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', action='store_true')
    parser.add_argument('--no-contacts', action='store_true')
    parser.add_argument('--reuse-inventory', action='store_true')
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--validate', action='store_true')
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    review = Review(args.output)
    if args.reuse_inventory:
        review.load_inventory()
        summary=json.loads((review.out/'inventory-summary.json').read_text())
    else:
        summary = review.inventory(not args.no_contacts)
    summary.update(status='inventoried', scope='RSE general pairs: all primary MIDs, outdoor secondary pairs and explicitly reserved facility outdoor MIDs',
                   target_module=TARGET.relative_to(ROOT).as_posix(), active_modules=review.active_modules)
    if args.build or args.validate:
        records=review.exact_aliases()
        records+=review.underwater_reef_shapes()
        records+=review.submarine()
        records+=review.structural_native_aliases()
        records+=review.native_ice_and_brown_corners()
        records+=review.braille_tablet()
        records+=review.underwater_canyon_tiers()
        records+=review.native_shores_and_fortree_ground()
        records+=review.sky_pillar_architecture()
        records+=review.native_ash_and_sky_exterior()
        records+=review.karst_architecture()
        records+=review.native_small_cave_families()
        records+=review.meteor_falls()
        records+=review.meteor_falls_compound()
        records+=review.navel_rock_native()
        records+=review.volcanic_region()
        records+=review.volcanic_steam()
        records+=review.reviewed_terrain('reviewed_shared_terrain')
        from reverse_gen2_mossdeep_remaining import emit as mossdeep
        records+=mossdeep(review)
        from reverse_gen2_slateport_remaining import emit as slateport
        records+=slateport(review)
        from reverse_gen2_mauville_routes import emit as mauville_routes
        records+=mauville_routes(review)
        from reverse_gen2_fortree_routes import emit as fortree_routes
        records+=fortree_routes(review)
        from reverse_gen2_fallarbor_routes import emit as fallarbor_routes
        records+=fallarbor_routes(review)
        from reverse_gen2_sootopolis_routes import emit as sootopolis_routes
        records+=sootopolis_routes(review)
        from reverse_gen2_pacifidlog_routes import emit as pacifidlog_routes
        records+=pacifidlog_routes(review)
        from reverse_gen2_rustboro_routes import emit as rustboro_routes
        records+=rustboro_routes(review)
        review.write(review.out/'candidate.lua')
        summary.update(status='built',rows=len(review.rows),new_cells=sum(row['occurrences']for row in records))
        summary['coverage']=review.coverage_manifests()
        if args.validate:
            summary['validation']=review.validate();summary['status']='passed'
        (review.out/'new-keys.json').write_text(json.dumps(records,indent=2)+'\n')
    (review.out / 'report.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
