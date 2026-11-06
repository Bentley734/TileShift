"""Review alternate Hoenn map layouts reached by imported field scripts."""

import argparse
from collections import defaultdict
import copy
import json
from pathlib import Path
import struct
import zlib

from PIL import Image

import catalog
from classic_geometry_review import art as classic_art, source_under_frames
from coverage import active_rows
from gb_theme_animation import specification
import preview
from reverse_common import ROOT, ReverseReview
from reverse_gen2_cerulean_outdoor_completion import source_indices
from reverse_kanto_review import exterior, runs
from reverse_oldale_review import mask_piece


GAMES = ('ruby','sapphire','emerald')
CAVE = 'general__cave'
ART_FIELDS = {'kind','role','donor','base','parts','asset','assetFileHash','assetPixelHash',
              'artOverlay','overMask','foregroundMask','foreground','animated','animation',
              'animationCategory','classicGeometry'}
MIRAGE_ALIAS = {
    1:'reverse_hoenn_short_nonencounter_grass',
    2:'reverse_gen2_hoenn_native_field_below_complete_bank',
    4:'reverse_hoenn_complete_native_flower',
    13:'reverse_hoenn_tall_grass',
    14:'reverse_gen2_hoenn_complete_native_conifer_0',
    22:'reverse_gen2_hoenn_complete_native_conifer_16',
    114:'reverse_gen2_hoenn_native_cliff_e_field',
    120:'reverse_gen2_hoenn_native_cliff_sw_field',
    122:'reverse_gen2_hoenn_native_cliff_se_field',
    136:'reverse_gen2_hoenn_native_cliff_w_sand',
    144:'reverse_gen2_hoenn_native_cliff_sw_sand',
    169:'reverse_gen2_hoenn_native_cliff_front_front',
    198:'reverse_gen2_hoenn_complete_native_conifer_8',
    **{m:f'reverse_gen2_hoenn_reviewed_mask_{m}' for m in (146,211,212,358,359,366,367)},
    **{m:'classic_gen2_native_berry_dirt_silhouette' for m in (259,260,261,267,268,269,275,276,277)},
    **{m:'reverse_gen2_hoenn_native_sand_field_edge' for m in (280,281,282,288,289,290)},
    372:'reverse_gen2_hoenn_coast_whole_rock_829',
}
MIRAGE_EDGES = {637:(6,1),638:(6,3),645:(6,1),646:(6,3)}
SOOTOPOLIS_ROCK = {658:(4,2),659:(6,1),660:(4,0),666:(6,1),668:(6,3),669:(6,1),
                   674:(4,2),676:(4,0),680:(4,3),681:(4,3),682:(4,3),750:(4,2),751:(4,0)}
LAVA_CORNERS = {864:(4,2),865:(4,3),866:(4,0),869:(4,2),870:(4,3),871:(4,0),
                872:(4,0),873:(4,3),874:(6,3),875:(6,1),876:(6,1),877:(6,3),
                878:(6,1),879:(6,3),880:(6,1),881:(6,3),882:(4,0),883:(4,2)}
CRYSTALS = {806,807,840,841,846,847}
FAMILY_COUNTS = {'mirage':120,'sootopolis':47,'caves':26,'interiors':7}


def artwork(row):
    return {key: copy.deepcopy(value) for key,value in row.items() if key in ART_FIELDS}


def grid(path):
    raw=path.read_bytes()
    data=raw if raw[:4]==b'SVML' else zlib.decompress(raw)
    assert data[:4]==b'SVML'
    stride, rows, width, height=struct.unpack_from('<HHHH',data,6)
    width,height=width or stride,height or rows
    offset=16+2*data[14]*data[15]
    cells=[struct.unpack_from('<HBB',data,offset+4*(y*stride+x))
           for y in range(height) for x in range(width)]
    return catalog.sha(raw),width,height,cells


def parts(ref, flags, animated=False):
    rectangles=[dict(p,donor=ref,srcX=p['x'],srcY=p['y']) for p in runs(flags)]
    if animated:
        for part in rectangles:
            part['animated']=True
    return rectangles


class Review(ReverseReview):
    def __init__(self, baseline):
        super().__init__('gen2-hoenn-alternate-layouts',GAMES)
        self.baseline=baseline
        _,rows=active_rows(baseline)
        self.active={(r['game'],r['tileset'],r['id']):r for r in rows
                     if r['game'] in GAMES and r['style']=='gen2' and not r.get('map')}
        self.stage_rows={(r['game'],r['tileset'],r['id'],r.get('map')):r for r in rows
                         if r['game'] in GAMES and r['style']=='gen2'}
        self.layout_proof={}
        self.donor_proof={}
        self.boards={}
        self.source_cache={}
        self.water=self.gb_ref('crystal','UNION_CAVE_1F',15,0)
        self.water_program=specification(self.cache,self.water,'program')
        assert self.water_program

    def render(self,row):
        return preview.replacement_image(self.cache,row,self.packed,self.baseline)

    def source(self, game,pair,mid):
        key=game,pair,mid
        if key not in self.source_cache:
            cell=self.imp.cell_index(game)[pair,mid]
            palette,planes=source_indices(self,game,pair,mid,cell)
            under, middle, over=(planes.get(name,bytes(256)) for name in ('under','mid','over'))
            self.source_cache[key]=palette,planes,bytes(o or m or u for u,m,o in zip(under,middle,over))
        return self.source_cache[key]

    def board(self,game,name,alt):
        key=game,name,alt
        if key not in self.boards:
            root=self.cache/game/'data/generated/gba/native'
            spec=self.imp.table(game,'gba/native/manifest')['layouts'][name]
            pair=spec['pair']
            before=grid(root/spec['file'])
            after=grid(root/'layouts'/f'{alt}.mid')
            assert before[1:3]==after[1:3]
            self.boards[key]=pair,before,after
            self.layout_proof['/'.join(key)]=dict(base=before[0],alternate=after[0],size=list(before[1:3]))
        return self.boards[key]

    def anchor(self,game,pair,mid):
        row=self.active[game,pair,mid]
        cell=self.imp.cell_index(game)[pair,mid]
        assert row['sourceHash']==cell['pixel_sha256']
        assert row['sourceBehavior']==cell['behavior']
        self.donor_proof[f'{game}/{pair}/{mid}']=catalog.sha(json.dumps(row,sort_keys=True).encode())
        return row

    def exact(self,game,pair,mid,role,reference_mid=None):
        source=self.imp.cell_index(game)[pair,mid]
        reference_mid=mid if reference_mid is None else reference_mid
        candidates=[]
        for donor_game,donor_pair,donor_mid in sorted(self.active):
            if donor_game!=game or donor_mid!=reference_mid:
                continue
            donor=self.active[donor_game,donor_pair,donor_mid]
            if donor['role']!=role:
                continue
            cell=self.imp.cell_index(game)[donor_pair,donor_mid]
            if all(source[k]==cell[k] for k in ('behavior','pixel_sha256','layer_sha256')):
                candidates.append((donor_pair,donor))
        assert candidates, (game,pair,mid,role)
        assert len({row['compositionPixelHash'] for _,row in candidates})==1, (game,pair,mid,role)
        donor_pair,_=candidates[0]
        row=self.anchor(game,donor_pair,reference_mid)
        assert row['kind']!='classic_native_geometry', 'Geometry metadata must be rebuilt against alternate animation banks'
        return artwork(row)

    def animated_surface(self, feature, layers, over=None):
        assert 1<=len(layers)<=32,(feature,len(layers))
        return dict(self.composite(None,layers,feature),animated=True,
                    animation=self.water_program,animationCategory='water',
                    overMask=over or '0'*256)

    def water_part(self):
        return dict(donor=self.water,w=16,h=16,x=0,y=0,animated=True)

    def mirage(self,game,pair,mid):
        if mid in MIRAGE_ALIAS:
            art=self.exact(game,pair,mid,MIRAGE_ALIAS[mid],829 if mid==372 else None)
            art['role']='mirage_island_'+art['role']
            return art
        palette,planes,visible=self.source(game,pair,mid)
        stone={57,58,59,60,61,62}
        exterior={70,75,77,78}
        assert set(visible)<=stone|exterior and set(visible)&stone and set(visible)&exterior
        ref=self.gb_ref('crystal','UNION_CAVE_1F',*MIRAGE_EDGES[mid])
        rock=parts(ref,[value in stone for value in visible])
        over=''.join('1' if value in stone else '0' for value in planes.get('over',bytes(256)))
        return self.animated_surface('mirage_island_complete_tidal_cliff', [self.water_part(),*rock],over)

    def bank(self,game,pair,mid,name,mode):
        folder=self.cache/game/'data/generated/gba/native'/pair
        manifest=catalog.read_lua(folder/'anim_manifest.lua')
        bank,=[b for b in manifest['banks'] if b['name']==name and mid in b.get('mids',[])]
        assert bank['kind']=='tiles' and mid not in bank.get('overMids',[])
        raw=(folder/bank['file']).read_bytes()
        length=bank['frames']*len(bank['mids'])*256
        if len(raw)!=length:
            raw=zlib.decompress(raw)
        assert len(raw)==length
        return dict(mode=mode,bank=name,hash=catalog.sha(raw))

    def ground_masks(self,planes,selected):
        masks={}
        for name,values in planes.items():
            mask=''.join('1' if value in selected and (value or name=='under') else '0' for value in values)
            if '1' in mask:
                masks[name]=mask
        return masks

    def sootopolis(self,game,pair,mid):
        assert game=='emerald' and pair=='general__sootopolis'
        roof={664:642,665:643,672:644}
        if mid in roof:
            art=artwork(self.anchor(game,pair,roof[mid]))
            assert art['role']=='classic_gen2_gym_flat_roof_and_native_sign'
            art['role']='sootopolis_storm_complete_rectangular_gym_roof'
            return art
        palette,planes,visible=self.source(game,pair,mid)
        water={12,13,14}
        deep={140,141,142}
        submerged={148,149,150}
        rock={53,57,58,59,60,61,62,63}
        if mid in (692,693,694,695,700,701,702,703,708,709,710,711):
            # The same source animation changes waves and molten fissures.
            # Retain its exact independent pixels, with native Crystal rock
            # texture only where the original stone does not animate.
            shades=((58,58,58),(8,33,255),(255,255,255),(247,82,49))
            ranks={161:0,162:0,163:0,164:0,166:0,167:0,168:3,172:3}
            known=set(ranks)|water
            assert set(visible)<=known
            colors={palette[i]:shades[ranks.get(i,2 if i==12 else 1)] for i in sorted(known)}
            colors.update({palette[i]:shades[2] for i in (9,10,11)})
            colors.update({rgb:shades[3] for rgb in ((222,74,58),(197,74,49),(173,74,41))})
            animation=self.bank(game,pair,mid,'sootopolis_stormy_water','native_under')
            _,changed,_=source_under_frames(self.cache,game,pair,mid,self.packed,animation)
            masks=self.ground_masks(planes,{161,162,163,164,166,167})
            masks={layer:''.join('0' if i in changed else bit for i,bit in enumerate(bits))
                   for layer,bits in masks.items()}
            ground=dict(donor=self.gb_ref('crystal','UNION_CAVE_1F',4,3),masks=masks)
            return classic_art(self,game,pair,mid,'sootopolis_groudon_molten_platform',
                               shades,colors,ground=ground,source_animation=animation)
        assert set(visible)<=water|deep|submerged|rock,(mid,sorted(set(visible)))
        layers=[self.water_part()]
        if set(visible)&deep:
            donor=self.anchor(game,pair,654)['donor']
            layers += parts(donor,[value in deep for value in visible],animated=True)
        if set(visible)&submerged:
            shadow=copy.deepcopy(self.water)
            colors=[[156,181,247],[107,140,214],[49,74,156],[33,49,115]]
            shadow['palettes']=[copy.deepcopy(colors) for _ in range(8)]
            layers += parts(shadow,[value in submerged for value in visible],animated=True)
        if mid in SOOTOPOLIS_ROCK:
            donor=self.gb_ref('crystal','UNION_CAVE_1F',*SOOTOPOLIS_ROCK[mid])
            layers += parts(donor,[value in rock for value in visible])
        else:
            assert not set(visible)&rock, mid
        over=''.join('1' if value in rock else '0' for value in planes.get('over',bytes(256)))
        if set(visible)<=rock:
            return dict(self.native(donor,'sootopolis_storm_native_crater_rim'),overMask=over)
        return self.animated_surface('sootopolis_storm_exact_crater_depths',layers,over)

    def caves(self,game,pair,mid):
        assert game=='ruby' and pair==CAVE
        palette,planes,visible=self.source(game,pair,mid)
        if mid in CRYSTALS:
            rock={115,116,117,118,119}
            ranks={120:0,124:1,125:2,126:3}
            assert set(visible)<=rock|set(ranks)
            shades=((255,255,255),(255,173,181),(239,41,66),(132,0,41))
            colors={palette[i]:shades[ranks.get(i,3)] for i in sorted(rock|set(ranks))}
            material=self.gb_ref('crystal','UNION_CAVE_1F',6,1 if mid in (806,840,846) else 3)
            ground=dict(donor=material,masks=self.ground_masks(planes,rock))
            return classic_art(self,game,pair,mid,'origin_cave_complete_fire_crystals',
                               shades,colors,ground=ground)
        lava={137,139,140}
        rock={99,100,101,102,103,115,116,117,118,119}
        assert set(visible)<=lava|rock and set(visible)&lava, (mid,sorted(set(visible)))
        donor=self.gb_ref('crystal','BLACKTHORN_GYM_1F',43,1)
        program=specification(self.cache,donor,'program')
        assert program
        layers=[dict(donor=donor,srcX=0,srcY=0,x=x,y=0,w=8,h=16,animated=True) for x in (0,8)]
        if set(visible)&rock:
            ref=self.gb_ref('crystal','UNION_CAVE_1F',*LAVA_CORNERS[mid])
            layers += parts(ref,[value in rock for value in visible])
        assert len(layers)<=32
        return dict(self.composite(None,layers,'ruby_story_cave_complete_molten_surface'),animated=True,
                    animation=program,animationCategory='water',overMask='0'*256)

    def interiors(self,game,pair,mid):
        assert game=='emerald'
        if pair=='building__mystery_events_house':
            assert mid==555
            old=self.anchor(game,pair,531)
            assert old['role']=='reverse_gen2_hoenn_complete_domestic_potted_tree'
            assert self.source(game,pair,mid)[1]['mid']==self.source(game,pair,531)[1]['mid']
            art=artwork(old)
            art['role']='mystery_events_house_same_complete_potted_tree'
            return art
        assert pair=='building__lab' and mid in (659,660,661,667,668,669)
        # Elm's complete 48-by-32 lab bench already fits this actual footprint.
        # Its gray planks are exactly the selected floor of Birch's lab.
        donor_map='ELMS_LAB'
        floor=self.anchor(game,pair,514)['donor']
        original=self.imp.gb('crystal',donor_map)[0].crop((96,48,144,80))
        outside=exterior(original,set(self.gb_image(floor).get_flattened_data()))
        dx=(mid-659)%8
        dy=int(mid>=667)
        mask=[(16*dx+x,16*dy+y) not in outside for y in range(16) for x in range(16)]
        art=self.composite(None,self.gb_rect('crystal',donor_map,96+16*dx,48+16*dy,16,16),
                           'birch_lab_complete_native_elm_workbench')
        return mask_piece(self,art,mask,floor,False)

    def occurrences(self, item):
        game,pair,mid=(item[k] for k in ('game','pair','mid'))
        positions={}
        for name,alt,index,address,instruction in item['scripts']:
            assert catalog.dict_at(self.imp.table(game,'gba/native/layout_files'),index)==alt
            command=self.imp.table(game,'gba/scripts/scripts')[address][instruction]
            assert command['op']=='setmaplayoutindex' and command['1']==index
            bank,before,after=self.board(game,name,alt)
            assert bank==pair
            width=before[1]
            for i,(base,alternate) in enumerate(zip(before[3],after[3])):
                if alternate[0]!=mid or alternate==base:
                    continue
                assert base[0]!=mid
                x,y=i%width,i//width
                positions[name,alt,x,y]=(base,alternate)
        assert positions
        return positions

    def build(self,items,family):
        proofs,witnesses=[],[]
        for item in items:
            game,pair,mid=(item[k] for k in ('game','pair','mid'))
            assert (game,pair,mid) not in self.active
            cell=self.imp.cell_index(game)[pair,mid]
            assert cell['pixel_sha256']==item['source'] and cell['layer_sha256']==item['layers']
            assert cell['behavior']==item['behavior']
            ref=dict(game=game,tileset=pair,id=mid,hash=cell['pixel_sha256'])
            for layer,digest in cell['layer_sha256'].items():
                preview.native_donor(self.cache,ref,self.packed,[layer],{layer:digest})
            placements=self.occurrences(item)
            assert len(placements)==item['placement_count']
            art=getattr(self,family)(game,pair,mid)
            row=self.row(game,pair,mid,'gen2',art,
                         'Reachable alternate Hoenn map layout. Complete native material follows the reviewed source '
                         'geometry, animation, foreground placement and actual field script coordinates.')
            name,alt,x,y=min(placements)
            base,target=placements[name,alt,x,y]
            witnesses.append(dict(game=game,pair=pair,mid=mid,map=name,x=x,y=y,before_mid=base[0],
                                  impassable=target[1]!=0,layout_file=alt,source_collision=base[1],
                                  target_collision=target[1],target_elevation=target[2]))
            output=[row['compositionPixelHash']]
            geometry=row.get('classicGeometry',{})
            if (row.get('animated') or geometry.get('sourceAnimation',{}).get('mode')=='native_under' or
                    geometry.get('ground',{}).get('animation')):
                output=[catalog.sha(frame.tobytes()) for frame in
                        preview.replacement_frames(self.cache,row,self.packed,self.baseline)]
            proofs.append(dict(game=game,pair=pair,mid=mid,output=output))
        return dict(layouts=self.layout_proof,anchors=self.donor_proof,rows=proofs,witnesses=witnesses)

    def scenes(self, prefix):
        for (game,name,alt),(pair,_,board) in self.boards.items():
            width,height=board[1:3]
            image=Image.new('RGBA',(width*16,height*16))
            renders={}
            for i,(mid,_,_) in enumerate(board[3]):
                if mid not in renders:
                    row=(self.rows.get((game,'gen2',pair,mid,None)) or
                         self.stage_rows.get((game,pair,mid,name)) or self.active.get((game,pair,mid)))
                    if row:
                        renders[mid]=self.render(row)
                    else:
                        cell=self.imp.cell_index(game).get((pair,mid))
                        assert cell,(game,name,mid)
                        ref=dict(game=game,tileset=pair,id=mid,hash=cell['pixel_sha256'])
                        renders[mid]=preview.native_donor(self.cache,ref,self.packed)
                image.paste(renders[mid],(16*(i%width),16*(i//width)))
            image.save(self.out/f'{prefix}-{game}-{name}-{alt}.png')


def audited_members(path, family):
    def selected(ctx):
        return ctx['family']=='alternate_map_layout' and (
            (family=='mirage' and ctx['map'].endswith('_ROUTE130')) or
            (family=='sootopolis' and ctx['map']=='EM_SOOTOPOLIS_CITY') or
            (family=='caves' and ctx['map'].startswith(('RU_CAVE_OF_ORIGIN','RU_SEAFLOOR_CAVERN'))) or
            (family=='interiors' and ctx['map'].endswith(('_PROFESSOR_BIRCHS_LAB','_MYSTERY_EVENTS_HOUSE_1F'))))
    result=[]
    for row in json.loads(path.read_text(encoding='utf-8')):
        contexts=[ctx for ctx in row['contexts'] if selected(ctx)]
        if not contexts:
            continue
        scripts, positions=set(),set()
        for ctx in contexts:
            origin=ctx['origin']
            assert origin['kind']=='script'
            scripts.add((ctx['map'],*(origin[k] for k in ('file_key','layout_index','script','index'))))
            positions.add((ctx['map'],origin['file_key'],ctx['x'],ctx['y']))
        result.append(dict(game=row['game'],pair=row['pair'],mid=row['mid'],source=row['sourceHash'],
                           layers=row['sourceLayers'],behavior=row['sourceBehavior'],
                           scripts=[list(s) for s in sorted(scripts)],placement_count=len(positions)))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path,default=ROOT)
    parser.add_argument('--family',choices=(*FAMILY_COUNTS,'all'),required=True)
    parser.add_argument('--freeze-from-audit',type=Path)
    parser.add_argument('--validate',action='store_true')
    args=parser.parse_args()
    review=Review(args.baseline.resolve())
    review.out=review.out/args.family
    review.out.mkdir(exist_ok=True)
    families=tuple(FAMILY_COUNTS) if args.family=='all' else (args.family,)
    assert not args.freeze_from_audit or len(families)==1
    witnesses,script_sites={},defaultdict(set)
    placement_count=0
    for family in families:
        guard=Path(__file__).with_name(f'reverse_gen2_hoenn_{family}_layout_guards.json')
        review.layout_proof,review.donor_proof,review.boards={},{},{}
        if args.freeze_from_audit:
            items=audited_members(args.freeze_from_audit,family)
            proof=review.build(items,family)
            guard.write_text(json.dumps(dict(items=items,proof=proof),indent=2)+'\n',encoding='utf-8')
        else:
            expected=json.loads(guard.read_text(encoding='utf-8'))
            items=expected['items']
            proof=review.build(items,family)
            assert proof==expected['proof'],'Reviewed alternate layout or output changed'
        assert len(items)==FAMILY_COUNTS[family]
        placement_count += sum(r['placement_count'] for r in items)
        for witness in proof['witnesses']:
            key=tuple(witness[k] for k in ('game','pair','mid'))
            assert key not in witnesses
            witnesses[key]=witness
        for item in items:
            for name,file_key,index,address,instruction in item['scripts']:
                script_sites[item['game'],name,file_key,index].add((address,instruction))
        review.scenes(family)
    assert len(review.rows)==sum(FAMILY_COUNTS[family] for family in families)
    review.write(review.out/'candidate.lua')
    keys=[{k:r[k] for k in ('game','pair','mid')} for r in witnesses.values()]
    (review.out/'keys.json').write_text(json.dumps(keys,indent=2)+'\n',encoding='utf-8')
    (review.out/'script-witnesses.json').write_text(json.dumps(list(witnesses.values()),indent=2)+'\n',encoding='utf-8')
    replay=[dict(game=g,map=name,layout_file=file_key,layout_index=index,sites=sorted(sites))
            for (g,name,file_key,index),sites in sorted(script_sites.items())]
    (review.out/'layout-replay-witnesses.json').write_text(json.dumps(replay,indent=2)+'\n',encoding='utf-8')
    validation=review.validate() if args.validate else None
    print(json.dumps(dict(rows=len(review.rows),placements=placement_count,validation=validation)))


if __name__=='__main__':
    main()
