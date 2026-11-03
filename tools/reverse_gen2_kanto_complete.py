"""Complete remaining native-used FR/LG families with reviewed Crystal art.

Candidate-only authoring: existing mappings and runtime remain unchanged.
Each source choice is pinned to its full RGBA, behavior and native layer hashes.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import copy
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import catalog
import preview
import reverse_gen2_kanto_finish as previous
from reverse_gen2_kanto_finish import Finish, GAMES, identity, stable
from reverse_kanto_review import runs


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'mappings/reverse_gen2_kanto_complete.lua'

# Manually reviewed source art/context, keyed independently of contact order.
SOURCES = {'cave_bank_nw': ('general__rom_082d4e0c',
                  720,
                  '8c8eecd4eb86d7e1f888e9ff2d397687473df584b51aea6c98ca436a93953ef5'),
 'cave_bank_n': ('general__rom_082d4e0c',
                 721,
                 'f43c308c7e6e868b7788e589cc74b2165968b99cadd0b2c0f8b8af3fe85ec47a'),
 'cave_bank_ne': ('general__rom_082d4e0c',
                  722,
                  '6347a2a61cb8586a1e32c8caf3e44b0c637c66f10c84113e0f8c65dd901e9099'),
 'cave_bank_w': ('general__rom_082d4e0c',
                 728,
                 'd00fdfa8c5dd8e3b06c4b4b8d07779e6cf428d53d31984efa597a6f2e99d0ed4'),
 'cave_bank_e': ('general__rom_082d4e0c',
                 730,
                 '101645d5e1399584f5725a2f3bac7e9b46c508417437e3994987c184dfe323b0'),
 'cave_bank_sw': ('general__rom_082d4e0c',
                  736,
                  '9ff61256216a8c4248febdb7c91b57cd10ea58d43fbbfe1f21c49d3184de984b'),
 'cave_bank_s': ('general__rom_082d4e0c',
                 737,
                 'b351f91abefe21329d037c97c62dd03da96a38d1430eafd18d16496e3ac6d61e'),
 'cave_bank_se': ('general__rom_082d4e0c',
                  738,
                  '9ad7dc8d442fcd06823b529d7e48bf83f3b452ca3cd5f1e51a1523c5561124d4'),
 'cave_bank_inner_ne': ('general__rom_082d4e0c',
                        675,
                        'c256c1188923909b848e64360bd0254d58449b9ed47f41f62b24b4b4e5fd4a52'),
 'cave_bank_inner_nw': ('general__rom_082d4e0c',
                        676,
                        '4ec48b6ddfd40a14f2013196687e17b2e73eb7501d70e3d3ed92f41f3488000f'),
 'cave_raised_top_fill': ('general__rom_082d4e0c',
                          770,
                          '0626c8e875f1721fb657d7e58033a62322c8d1b95d1150050cc6de2c1d745e08'),
 'cave_gray_boulder': ('general__rom_082d4e54',
                       642,
                       '5b7ea859bbb62f4e037857ad67d988e237aa9097ed9ec8a3446f6a403eb7f6f4'),
 'cave_red_boulder': ('general__rom_082d4bfc',
                      643,
                      'cc178deb4d97f64cbe38efa37cf6494d996faa15c9dc23afa89726acca152f6b'),
 'south_jump_ledge': ('general__rom_082d4b3c',
                      135,
                      'f5691dab17e4b76a8d98f238c67456179bd50712b1bb62ef75eddd7e87532d0b'),
 'rocket_east': ('building__rom_082d4ecc',
                 660,
                 '94fdee42035cc53177d0824fc01153d2f2a70c6187ab8b99cb1f66b71675dbb9'),
 'rocket_west': ('building__rom_082d4ecc',
                 656,
                 '5867e9b209b0570c8bc95d248707f486e82c1314897448660b83a8ba12bfc014'),
 'tower_grave': ('building__rom_082d4efc',
                 657,
                 '791a8f77827e2e6438906278da819db9c9f0c7727d5abce535879b39f5a58303'),
 'silph_front_lip': ('building__rom_082d4ecc',
                     818,
                     '0677915c78ddf16c72d127ffb4fbefbee171d3f191d3e6d7dcbdb8e7c533f912'),
 'summit_sky': ('general__rom_082d501c',
                695,
                'c027f2a67d11139b08e77337d6e5aea294fc30c1b4d7d64fb636868297e0f59d'),
 'lab_floor': ('oak_lab', 129, 'f5ae3a4a437a7711c4f26068187fd5e7a28cf7bfdfa5807edf1265166c2959c1'),
 'museum_floor': ('building__rom_082d4c2c',
                  641,
                  '16be85bc74c3c0f22b612509e045fa29493d5816fb48eb82459aaf4799265699'),
 'home_parquet_floor': ('player_house',
                        169,
                        '58932ca20adf6cb593fde3cbdde180cfa70d7c1b298f037caea865b75ccbee7e'),
 'cave_sand_floor': ('general__rom_082d4bfc',
                     764,
                     '804ec0e63c955ca88f6336ca90fa9fe4d839abd7a529465eed0cafe379fda230'),
 'ship_empty_void': ('general__rom_082d4d94',
                     656,
                     'a2bd0a18557f86119f1ff12f6d42545171a2eb1b579c49bcf9dfdfab14df2f2d'),
 'ruin_pattern_floor': ('building__rom_082d5034',
                        697,
                        'c4d8735765630b1225e408bf8736f87e4069ac2a1a354e1a5e88c4fb44dcee11'),
 'mansion_wood_floor_joint': ('building__rom_082d4f2c',
                              647,
                              'a2d170d993deabf26f5d9896d9c7bb3d70a3055d916c59c379707ce64bad4a3f'),
 'ruin_pattern_floor_variant': ('building__rom_082d5034',
                                726,
                                '6d4ef3d71a92664379aa1248fd59b0574dbc1f5d814644d19bc07c0c7b135c19'),
 'harbor_stone_paving': ('harbor', 642, 'e0362765a15c937417c4ece4400459ccc91415fd63032ce434d44aa7721bca40'),
 'ship_kitchen_timber': ('general__rom_082d4d94',
                         665,
                         '380e01ba4828d1586286b7a6585b2572f6d5485953003dfd508ec7ed2fed63ab'),
 'saffron_paving_variant_a': ('general__rom_082d4b9c',
                              748,
                              'f9b921c5da3691f6ed9387a9ff0a6db8647d786a5d72eb8860ef843b3ef8b465'),
 'celadon_open_lawn': ('general__rom_082d4b3c',
                       206,
                       'a5b7c82f6bb1a14f82b7855fa3f380761ec73ac9fa1006f3756727582aec4cb0'),
 'cycling_open_lawn': ('general__rom_082d4b3c',
                       839,
                       'badcc0c5b9804988ad6bff44651f3e4c66b015f0b8d239165b4728c9a2c2573b'),
 'ordinary_snow_floor': ('general__rom_082d4e24',
                         737,
                         'ff5c7a5615e236756fa190d5acf5d4e56f7d8a89f6f11e8083a1d01da6bce3d0'),
 'spa_gravel_floor': ('general__rom_082d4fec',
                      813,
                      'a00970a197d328b8df4cf3ed21884f9d555106f721b3b6536183f7f33e3c55f3'),
 'cave_gravel_floor_variant': ('general__rom_082d4bfc',
                               737,
                               'ba319b246f23a5609ac56291acc5c9b50c4b9fd62db8d04e53ef64e7500b0a6a'),
 'saffron_paving_variant_b': ('general__rom_082d4b9c',
                              756,
                              '93830965e26aa79539fe0df66ca75b61ddcb1bf36ca8a84005baa393511ebda9'),
 'pewter_museum_paving': ('pewter_outdoor',
                          449,
                          '4e138a76ceac3a9c16a00e43713f92ef89193c26384a3b3c5dfdb677e8d3d103'),
 'cliff_palette_0': ('general__rom_082d5064',
                     160,
                     '123546b586a4cd933a3e033dbfd11a4c4164f8c60eff87069793bd1964b1b59b'),
 'cliff_palette_1': ('sevii_outdoor', 861, '002660028ffc343eeab77eebb68f3986a7a032cb99e8bdf09f18a7504be73c2a'),
 'cliff_palette_2': ('sevii_outdoor', 859, 'b8ba26eff9a4a66fd4ce275faa4bd71f26bc0ed09d8accf0d376730d2c949d22'),
 'cliff_palette_3': ('general__rom_082d5064',
                     162,
                     '79e26288c829fae071bcdd119b41f6bcdec2b8e74bbe941fb352d05dc3de6ca9'),
 'cliff_palette_4': ('sevii_outdoor', 857, 'f74c01ef61c5ed21cfedba6faf31e4bffc9d523298afef13da779ca747d201fa'),
 'cliff_palette_5': ('general__rom_082d4b0c',
                     138,
                     '44fac11516609e68fceaddfe397526e9d23112ef99a811efd4dceebfe35e94d1'),
 'cliff_palette_6': ('general__rom_082d5064',
                     170,
                     '078e07f7512f841190b9904bf4cd5d493f40222c7e5511156ad67693795f2267'),
 'cliff_palette_7': ('general__rom_082d5064',
                     153,
                     'd7fcd6ec9118357818d433f592cbf4b260d4ec559efbf5d1e1245a1ef230314c'),
 'cliff_palette_8': ('sevii_outdoor', 823, '47c626e53b2918491388315c045966cfc115a58e30b5e157f766efbbf7017479'),
 'cliff_palette_9': ('sevii_outdoor', 846, 'bee53e9b1fcb4ecf9aac4c58171064641b4a1a7e52c965008c3713ad695db19f'),
 'cliff_palette_10': ('sevii_outdoor', 837, '4bf95fbb4073ec1a457003681ec95dfbc2d7e0bb49e6daaa7d48d608c1bc431a'),
 'cliff_palette_11': ('sevii_outdoor', 847, '628297f39f91d7a993e17ec637e4104fec1fb837b9f854abb2b45c833f45ae6c'),
 'cliff_palette_12': ('sevii_outdoor', 839, '821f8662d26e517b11805dfb6b654540c764a09f047a585cca551f2ea6188c00'),
 'cliff_palette_13': ('sevii_outdoor', 848, '2ca68ba4e825e6c67aa9e7510d94c21e3e14592883237b240bd2922d5d276df5'),
 'cliff_palette_14': ('sevii_outdoor', 850, 'efe35b0f91d2e728dba0d1b8956bc5e61b30f6c80e40a0807912d0648933ae0e'),
 'cliff_palette_15': ('sevii_outdoor', 858, 'b7900e9d4af552091b335aad66694809e6806e8802d0ccfbb5c6d0132db5caf7'),
 'cliff_palette_16': ('sevii_outdoor', 865, '34624208a0d1757ab4d4f50edfb1e4a66210310277deaf5a214c1c0a38f37f6d'),
 'cliff_palette_17': ('sevii_outdoor', 864, 'de72e0519dae24eecde1fc26eefa4e8b680cb76eac1f4667fcdb98b028b07472'),
 'ice_boulder_tall': ('general__rom_082d4e24',
                      642,
                      'edbcd803901cd2fbb01592064033e46cca9c2f9b7d6c328f7e8223eefd469164'),
 'ice_boulder_round': ('general__rom_082d4e24',
                       643,
                       '9840be9199e03029badbf654d29ede4eced73bf19867e5cc0e930a090865dd23'),
 'cave_palette_0': ('general__rom_082d4e0c',
                    788,
                    'e1c37ebc5cbf80afc88d3ba533608ac24b55745d1b3015b14a5faa6accbb0731'),
 'cave_palette_1': ('general__rom_082d4e0c',
                    787,
                    '44df7dda8d5efffc730c3d670e1113c83a01a82f15d78c10ea16503723e85bfe'),
 'cave_palette_2': ('general__rom_082d4e0c',
                    785,
                    '01b4372801a73172e96c5dbdd2db90bd707ce69e8046df82cf47d76c4632f283'),
 'cave_palette_3': ('general__rom_082d4e0c',
                    790,
                    '086007323e9846a1012838a4f7e832271b7703acb76a14a48a39db1ed1f3b97f'),
 'cave_palette_4': ('general__rom_082d4e0c',
                    748,
                    '5af726c84570981e73ebef44ddb7682e44a70ab934ab613d0e578e37ecbff3cf'),
 'cave_palette_5': ('general__rom_082d4e0c',
                    749,
                    '6a7989ecc3486e15a2b0b711545f641eb03f792c8567605f80f8be89d5148baf'),
 'cave_palette_6': ('general__rom_082d4e0c',
                    789,
                    'f58dbf51f1b4ae602f6ba4da117d3e638c0e9deda3e3315fb5e85f692b8f4038'),
 'cave_palette_7': ('general__rom_082d4e0c',
                    786,
                    '2ef4df0e914bd126094d73706db31672bb3b4748fa53d4814cdae41ea654a426'),
 'cave_palette_8': ('general__rom_082d4e0c',
                    784,
                    'f63d382bb92d5446be843ecd4738bde91330f63e396f54f915cf92ef4bb874c6')}

PALETTE_CLIFF_CANONICAL = [('general__rom_082d5064', 112),
 ('general__rom_082d507c', 125),
 ('general__rom_082d507c', 123),
 ('general__rom_082d5064', 114),
 ('general__rom_082d4af4', 121),
 ('general__rom_082d5064', 114),
 ('general__rom_082d4af4', 122),
 ('general__rom_082d5064', 105),
 ('general__rom_082d5064', 114),
 ('general__rom_082d5064', 112),
 ('general__rom_082d5064', 120),
 ('general__rom_082d5064', 114),
 ('general__rom_082d4af4', 122),
 ('general__rom_082d5064', 112),
 ('general__rom_082d5064', 114),
 ('general__rom_082d4af4', 122),
 ('general__rom_082d5064', 105),
 ('general__rom_082d5064', 104)]


PALETTE_CAVE_CANONICAL = [('cave_palette_0', 'cave_bank_e'),
 ('cave_palette_1', 'cave_bank_w'),
 ('cave_palette_2', 'cave_bank_n'),
 ('cave_palette_3', 'cave_bank_s'),
 ('cave_palette_4', 'cave_bank_inner_ne'),
 ('cave_palette_5', 'cave_bank_inner_nw'),
 ('cave_palette_6', 'cave_bank_sw'),
 ('cave_palette_7', 'cave_bank_ne'),
 ('cave_palette_8', 'cave_bank_nw')]

class Complete(Finish):
    def __init__(self):
        # Reuse the verified native layout/source readers, while including the
        # entire released v0.32 module in the baseline rather than restaging it.
        old = previous.TARGET
        previous.TARGET = TARGET
        try:
            super().__init__()
        finally:
            previous.TARGET = old
        self.name = 'gen2-kanto-complete'
        self.out = ROOT.parent / '.work/tileshift-reverse-gen2-kanto-complete'
        self.out.mkdir(parents=True, exist_ok=True)
        self.target_module = TARGET
        self.decisions = []

    def source_signature(self, game, pair, mid):
        cell = self.imp.cell_index(game)[pair, mid]
        return catalog.sha(stable(dict(rgba=cell['pixel_sha256'], behavior=cell['behavior'],
                                       layers=cell['layer_sha256'])).encode())

    def remaining_inventory(self):
        groups = defaultdict(list)
        for (game, pair, mid), usages in self.usage.items():
            if (game, 'gen2', pair, mid, None) in self.current:
                continue
            count = sum(u['count'] for u in usages)
            if not count:
                continue
            cell = self.imp.cell_index(game)[pair, mid]
            witnesses = sorted((u for u in usages if u['count']), key=lambda u: (-u['count'], u['map']))
            groups[self.source_signature(game, pair, mid)].append(dict(
                game=game, pair=pair, id=mid, count=count, rgba=cell['pixel_sha256'],
                behavior=cell['behavior'], behavior_hint=cell['behavior_hint'], layers=cell['layer_sha256'],
                witnesses=witnesses))
        records = [dict(signature=sig, count=sum(v['count'] for v in entries), sources=entries)
                   for sig, entries in groups.items()]
        records.sort(key=lambda r: (-r['count'], r['signature']))
        for i, record in enumerate(records):
            record['review_number'] = i
        result = dict(games=self.inventory()['games'], groups=records,
                      remaining_cells=sum(r['count'] for r in records),
                      actual_used_source_keys=sum(len(r['sources']) for r in records),
                      source_groups=len(records))
        (self.out / 'remaining-inventory.json').write_text(json.dumps(result, indent=2))
        self.remaining = records
        return result

    def contacts(self):
        font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 13)
        for start in range(0, len(self.remaining), 30):
            canvas = Image.new('RGB', (1440, 10 * 126), '#18212b')
            draw = ImageDraw.Draw(canvas)
            for index, item in enumerate(self.remaining[start:start + 30]):
                cell = next((s for s in item['sources'] if s['game'] == 'firered'), item['sources'][0])
                image = preview.native_donor(self.cache, dict(game=cell['game'], tileset=cell['pair'],
                    id=cell['id'], hash=cell['rgba']), self.packed)
                x, y = index % 3 * 480, index // 3 * 126
                canvas.paste(image.resize((96, 96), Image.Resampling.NEAREST), (x + 4, y + 4))
                lines = [f"{item['review_number']} / {cell['id']} — {item['count']} cells",
                         cell['behavior_hint'], cell['pair'], cell['witnesses'][0]['map']]
                for n, line in enumerate(lines):
                    draw.text((x + 108, y + 5 + n * 22), line, font=font, fill='white')
            canvas.save(self.out / f'remaining-contact-{start // 30 + 1:02}.png')

    def stage(self):
        self.first_reviewed_families()
        self.whole_cave_boulders()
        self.joined_cave_banks()
        self.reviewed_floor_surfaces()
        self.reviewed_cliff_palette_variants()
        self.native_ice_boulders()
        self.reviewed_cave_palette_variants()
        (self.out / 'decisions.json').write_text(json.dumps(self.decisions, indent=2))
        (self.out / 'uncertain-queue.json').write_text(json.dumps(self.held, indent=2))
        return list(self.rows.values())

    def reviewed_floor_surfaces(self):
        # Each explicit source is reviewed in its complete five-by-five native
        # context. These are entire ordinary surfaces, never a role-name guess.
        refs = {
            'cave_sand_floor':self.gb_ref('crystal','UNION_CAVE_1F',2,0),
            'ship_empty_void':self.black_ref(),
            'ruin_pattern_floor':self.gb_ref('crystal','RUINS_OF_ALPH_AERODACTYL_CHAMBER',5,3),
            'ruin_pattern_floor_variant':self.gb_ref('crystal','RUINS_OF_ALPH_AERODACTYL_CHAMBER',5,3),
            'mansion_wood_floor_joint':self.current['firered','gen2','building__rom_082d4f2c',646,None]['donor'],
            'harbor_stone_paving':self.gb_ref('crystal','SAFFRON_CITY',119,0),
            'pewter_museum_paving':self.gb_ref('crystal','SAFFRON_CITY',119,0),
            'ship_kitchen_timber':self.gb_ref('crystal','PLAYERS_HOUSE_1F',3,0),
            'saffron_paving_variant_a':self.gb_ref('crystal','SAFFRON_CITY',119,0),
            'saffron_paving_variant_b':self.gb_ref('crystal','SAFFRON_CITY',119,0),
            'celadon_open_lawn':self.current['firered','gen2','general__rom_082d4b3c',8,None]['donor'],
            'cycling_open_lawn':self.current['firered','gen2','general__rom_082d4b3c',8,None]['donor'],
            'ordinary_snow_floor':self.current['firered','gen2','general__rom_082d4e24',641,None]['donor'],
            'spa_gravel_floor':self.gb_ref('crystal','UNION_CAVE_1F',2,0),
            'cave_gravel_floor_variant':self.current['firered','gen2','general__rom_082d4bfc',641,None]['donor'],
        }
        for name,ref in refs.items():
            self.emit(name,self.native(ref,'classic_gen2_complete_'+name),
                'Actual complete native source surface and adjoining five-by-five room/route context reviewed: '+name+'. '
                'The source contains only the indicated timber, stone paving, gravel, ordinary snow, open nonencounter '
                'field or empty ship exterior. Original whole Crystal16px material remains1:1 and joins the already '
                'selected material for its room/region. Ruin pips and pavement plank variants are ordinary walking '
                'surfaces, not new objects; ship white outside the corridor is empty void and becomes native black. '
                'Raised faces, stair lips, mats, props, doors and all partial-OVER source cells are excluded.', '0'*256)

    def reviewed_cliff_palette_variants(self):
        evidence=[]
        for index,(pair,mid) in enumerate(PALETTE_CLIFF_CANONICAL):
            name='cliff_palette_'+str(index);source_pair,source_mid,_=SOURCES[name]
            canonical=self.current['firered','gen2',pair,mid,None]
            assert canonical.get('reverseGen2KantoReview',{}).get('kind')=='explicit_whole_cliff_family'
            original=self.imp.cell_index('firered')[pair,mid]
            source=self.imp.cell_index('firered')[source_pair,source_mid]
            assert original['behavior']==source['behavior']
            mapping={};inverse={};checks=0;priority=None
            for layer in (None,'under','mid','over'):
                images=[]
                for pp,mm,cell in ((pair,mid,original),(source_pair,source_mid,source)):
                    ref=dict(game='firered',tileset=pp,id=mm,hash=cell['pixel_sha256'])
                    images.append(preview.native_donor(self.cache,ref,self.packed,
                        [layer] if layer else None,{layer:cell['layer_sha256'][layer]} if layer else None))
                for left,right in zip(images[0].get_flattened_data(),images[1].get_flattened_data()):
                    assert left[3]==right[3],(name,layer,'alpha')
                    checks+=1
                    if not left[3]:continue
                    assert left not in mapping or mapping[left]==right,(name,'non-bijective source')
                    assert right not in inverse or inverse[right]==left,(name,'non-bijective target')
                    mapping[left]=right;inverse[right]=left
                if layer=='over':priority=''.join('1'if p[3]else'0'for p in images[1].get_flattened_data())
            art={k:copy.deepcopy(v)for k,v in canonical.items()if k in ('kind','donor','base','parts','animation','role','foregroundMask')}
            self.emit(name,art,
                'Complete original outdoor cliff module is the reviewed raised-earth directional family, with '
                'the identical complete final/UNDER/MID/OVER geometry, alpha and behavior as its independently '
                'reviewed source cliff; only an exact injective color substitution differs. All1024 source '
                'pixels across those four planes are checked under one bijection. Actual MemorialPillar, '
                'KindleRoad, MtEmber and Route10 contexts confirm continuous ordinary rock banks, not ice, '
                'machinery or a unique prop. The complete corresponding native Crystal cliff stays1:1, retaining '
                'all caps, corners and adjoining faces; no per-cell collision inference or automatic inverse.',priority)
            evidence.append(dict(kind=name,canonical_pair=pair,canonical_id=mid,source_pair=source_pair,
                source_id=source_mid,checked_pixels=checks,palette_bijection=[dict(source=list(k),target=list(v))for k,v in sorted(mapping.items())]))
        (self.out/'cliff-palette-variant-proof.json').write_text(json.dumps(evidence,indent=2))

    def reviewed_cave_palette_variants(self):
        evidence=[]
        for name,canonical_name in PALETTE_CAVE_CANONICAL:
            source_pair,source_mid,_=SOURCES[name]
            pair,mid,_=SOURCES[canonical_name]
            canonical=self.rows['firered','gen2',pair,mid,None]
            original=self.imp.cell_index('firered')[pair,mid]
            source=self.imp.cell_index('firered')[source_pair,source_mid]
            assert source['behavior']==original['behavior']
            mapping={};inverse={};checks=0;priority=None
            for layer in (None,'under','mid','over'):
                images=[]
                for pp,mm,cell in ((pair,mid,original),(source_pair,source_mid,source)):
                    ref=dict(game='firered',tileset=pp,id=mm,hash=cell['pixel_sha256'])
                    images.append(preview.native_donor(self.cache,ref,self.packed,
                        [layer]if layer else None,{layer:cell['layer_sha256'][layer]}if layer else None))
                for left,right in zip(images[0].get_flattened_data(),images[1].get_flattened_data()):
                    checks+=1;assert left[3]==right[3]
                    if not left[3]:continue
                    assert left not in mapping or mapping[left]==right
                    assert right not in inverse or inverse[right]==left
                    mapping[left]=right;inverse[right]=left
                if layer=='over':priority=''.join('1'if p[3]else'0'for p in images[1].get_flattened_data())
            art={k:copy.deepcopy(v)for k,v in canonical.items()if k in ('kind','donor','base','parts','animation','role','foregroundMask')}
            self.emit(name,art,
                'The complete shaded cave-bank variant is byte-geometry identical to the explicitly reviewed '
                'joined Diglett family under one injective native color substitution, jointly checked across '
                'all1024 FINAL/UNDER/MID/OVER pixels and exact behavior/alpha. Actual Diglett/Tanoby source '
                'contexts show the same complete directional face or inward return, never a socket, hole, '
                'stairhead or walking-floor object. Its whole matching original Crystal cave module remains '
                'at1:1 and joins the same classic bank family; source layer priority is unchanged.',priority)
            evidence.append(dict(kind=name,canonical=canonical_name,checked_pixels=checks,
                palette_bijection=[dict(source=list(k),target=list(v))for k,v in sorted(mapping.items())]))
        (self.out/'cave-palette-variant-proof.json').write_text(json.dumps(evidence,indent=2))

    def native_ice_boulders(self):
        ref=self.gb_ref('crystal','MOUNT_MOON',24,0)
        # This is an explicit classic ice-color adaptation of the complete
        # original CAVE rock, never a claim that it is an ICE_PATH rock glyph.
        definition=self.imp.table('crystal','maps')['ICE_PATH_1F']
        ice_palettes=preview.palette_set(self.imp.table('crystal','palettes'),definition,'DAY')
        # The original ice-bank blue/purple ramp is palette6. CAVE glyph
        # attribute palette indices have different meanings, so retain its
        # four native shade indices while explicitly applying this one ramp.
        ref['palettes']=[copy.deepcopy(ice_palettes[6])for _ in range(8)]
        original=self.gb_image(ref)
        left=[6,4,3,2,1,1,1,0,0,0,0,0,0,1,1,2]
        right=[11,12,13,14,15,15,16,16,16,16,16,16,16,16,15,13]
        mask=[left[y]<=x<right[y]for y in range(16)for x in range(16)]
        parts=[dict(donor=ref,srcX=p['x'],srcY=p['y'],**p)for p in runs(mask)]
        base=self.current['firered','gen2','general__rom_082d4e24',641,None]['donor']
        art=self.composite(base,parts,'classic_gen2_complete_native_ice_palette_boulder')
        image=self.render(art);floor=self.gb_image(base)
        for y in range(16):
            for x in range(16):assert image.getpixel((x,y))==(original if mask[y*16+x]else floor).getpixel((x,y))
        for name in ('ice_boulder_tall','ice_boulder_round'):
            self.emit(name,art,
                'Actual Seafoam source is a complete isolated16px blue/ice boulder, separately reviewed from '
                'raised ice banks, slide floors and pillars. The whole original Crystal CAVE rock24q0 retains '
                'every native contour, outline, highlight and shadow pixel at1:1, rendered in the original '
                'Crystal ICE_PATH palette as an explicit ice-color counterpart. It is not claimed to be an '
                'original ICE_PATH boulder. Only its verified exterior floor is removed; the exact neighboring '
                'selected native snow floor is visible around the closed silhouette. No image scaling.', '0'*256)
        image.resize((256,256),Image.Resampling.NEAREST).save(self.out/'native-ice-boulder-counterpart.png')
        (self.out/'native-ice-boulder-proof.json').write_text(json.dumps(dict(ref=ref,native_dimensions=[16,16],
            original_native_geometry_unchanged=True,source_native_cave_rock=True,palette_context='ICE_PATH_1F',native_ice_palette_index=6,
            retained_native_pixels=sum(mask),native_rgba_sha256=catalog.sha(original.tobytes()),all_retained_pixels_exact=True),indent=2))

    def joined_cave_banks(self):
        modules = {'cave_bank_nw':(4,0), 'cave_bank_n':(4,1), 'cave_bank_ne':(6,1),
                   'cave_bank_w':(4,2), 'cave_bank_e':(6,3), 'cave_bank_sw':(12,2),
                   'cave_bank_s':(12,3), 'cave_bank_se':(14,3),
                   'cave_bank_inner_ne':(16,3), 'cave_bank_inner_nw':(17,2),
                   'cave_raised_top_fill':(4,3)}
        for name,(block,quadrant) in modules.items():
            ref = self.gb_ref('crystal','UNION_CAVE_1F',block,quadrant)
            self.emit(name,self.native(ref,'classic_gen2_complete_'+name),
                'Complete native cave bank reviewed as one joined source family in the actual long Diglett maze '
                'and Tanoby cave. North, west, east, south faces, both convex caps and the two concave returns '
                'are assigned by their visible rock surfaces and adjoining source bank directions, never by '
                'collision labels alone. The original complete Crystal UNION_CAVE bank quadrant stays1:1 '
                'and joins the already selected same native cave family. Plain raised-rock fill is separate '
                'from the walkable floor; holes, strength sockets, entrance heads and scattered boulder clusters '
                'are excluded from this material family.', '0' * 256)
        source = Image.new('RGBA',(48,48));target=source.copy()
        rows=(('cave_bank_nw','cave_bank_n','cave_bank_ne'),
              ('cave_bank_w','cave_raised_top_fill','cave_bank_e'),
              ('cave_bank_sw','cave_bank_s','cave_bank_se'))
        for y,names in enumerate(rows):
            for x,name in enumerate(names):
                pair,mid,_=SOURCES[name];cell=self.imp.cell_index('firered')[pair,mid]
                image=preview.native_donor(self.cache,dict(game='firered',tileset=pair,id=mid,hash=cell['pixel_sha256']),self.packed)
                source.paste(image,(x*16,y*16));block,q=modules[name]
                target.paste(self.gb_image(self.gb_ref('crystal','UNION_CAVE_1F',block,q)),(x*16,y*16))
        proof=Image.new('RGB',(48*12+24,48*6+32),'#18212b');draw=ImageDraw.Draw(proof)
        font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
        for n,(label,image) in enumerate((('Whole source cave bank',source),('Complete native Crystal modules',target))):
            x=4+n*(48*6+16);draw.text((x,4),label,font=font,fill='white')
            proof.paste(image.resize((288,288),Image.Resampling.NEAREST),(x,26))
        proof.save(self.out/'joined-cave-bank-family-proof.png')

    def whole_cave_boulders(self):
        ref = self.gb_ref('crystal','MOUNT_MOON',24,0)
        assert 24 in self.imp.table('crystal','maps')['MOUNT_MOON']['blocks']
        original = self.gb_image(ref)
        left = [6,4,3,2,1,1,1,0,0,0,0,0,0,1,1,2]
        right = [11,12,13,14,15,15,16,16,16,16,16,16,16,16,15,13]
        mask = [left[y] <= x < right[y] for y in range(16) for x in range(16)]
        parts = [dict(donor=ref,srcX=p['x'],srcY=p['y'],**p) for p in runs(mask)]
        assert len(parts) <= 32
        details = []
        for name in ('cave_gray_boulder','cave_red_boulder'):
            pair, mid, signature = SOURCES[name]
            old_floor = self.current['firered','gen2',pair,641,None]
            floor = old_floor['donor']
            floor_pixels = self.render(old_floor)
            group = next(g for g in self.remaining if g['signature'] == signature)
            for source in group['sources']:
                existing = self.current[source['game'],'gen2',source['pair'],641,None]
                assert self.render(existing).tobytes() == floor_pixels.tobytes(), 'Boulder alias has a different selected floor'
            art = self.composite(floor, parts, 'classic_gen2_complete_native_'+name)
            image = self.render(art)
            assert all(image.getpixel((x,y)) == original.getpixel((x,y)) for y in range(16) for x in range(16) if mask[y*16+x])
            assert all(image.getpixel((x,y)) == floor_pixels.getpixel((x,y)) for y in range(16) for x in range(16) if not mask[y*16+x])
            self.emit(name, art,
                'Complete original Crystal16px cave boulder, independently witnessed in MountMoon block24 and '
                'separate from that32px block\'s other two boulders. The reviewed closed contour retains every '
                'native object pixel at1:1 and removes only exterior original floor. Actual native Cerulean/'
                'MtMoon/VictoryRoad source context confirms an isolated16px static boulder, not a raised bank '
                'or a multi-rock floor texture. The selected existing cave floor shows through around it; '
                'no bounding rectangle, clipped rock cap or scaled glyph is used.', '0' * 256)
            image.resize((256,256),Image.Resampling.NEAREST).save(self.out/(name+'-counterpart.png'))
            details.append(dict(kind=name,native_ref=ref,native_dimensions=[16,16],retained_native_pixels=sum(mask),
                native_left=left,native_right_exclusive=right,all_native_pixels_exact=True,all_exterior_floor_matches_existing=True))
        (self.out/'whole-native-boulder-proof.json').write_text(json.dumps(details,indent=2))

    def previews(self):
        scenes = ('FR_ROCKET_HIDEOUT_B1F', 'FR_FIVE_ISLAND_ROCKET_WAREHOUSE', 'FR_SILPH_CO_3F',
                  'FR_POKEMON_TOWER_2F', 'FR_NAVEL_ROCK_SUMMIT',
                  'FR_CINNABAR_ISLAND_POKEMON_LAB_ENTRANCE', 'FR_PEWTER_CITY_MUSEUM_1F',
                  'FR_SAFFRON_CITY_COPYCATS_HOUSE_1F','FR_DIGLETTS_CAVE_B1F',
                  'FR_SEVEN_ISLAND_SEVAULT_CANYON_TANOBY_KEY','FR_ROUTE_1','FR_CERULEAN_CAVE_2F','FR_MT_EMBER_EXTERIOR',
                  'FR_FIVE_ISLAND_MEMORIAL_PILLAR','FR_ROUTE_10','FR_MT_MOON_1F','FR_MT_MOON_B2F',
                  'FR_SSANNE_KITCHEN','FR_SSANNE_1F_CORRIDOR','FR_SEAFOAM_ISLANDS_1F','FR_SEAFOAM_ISLANDS_B4F',
                  'FR_SEVEN_ISLAND_TANOBY_RUINS_MONEAN_CHAMBER','FR_POKEMON_MANSION_B1F',
                  'FR_BIRTH_ISLAND_HARBOR','FR_SAFFRON_CITY','FR_CELADON_CITY','FR_ROUTE_17',
                  'FR_ONE_ISLAND_KINDLE_ROAD_EMBER_SPA')
        font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15)
        for name in scenes:
            spec, layout = self.layouts['firered', name]
            w, h = layout['width'], layout['height']
            canvases = [Image.new('RGBA', (w*16,h*16)) for _ in range(3)]
            images = {}
            for index, mid in enumerate(layout['mids']):
                key = 'firered', 'gen2', spec['pair'], mid, None
                if mid not in images:
                    cell = self.imp.cell_index('firered')[spec['pair'],mid]
                    original = preview.native_donor(self.cache, dict(game='firered',tileset=spec['pair'],
                        id=mid,hash=cell['pixel_sha256']), self.packed)
                    old, new = self.current.get(key), self.rows.get(key)
                    images[mid] = (original, self.render(old) if old else original,
                                   self.render(new or old) if new or old else original)
                for canvas, image in zip(canvases, images[mid]):
                    canvas.paste(image, (index%w*16,index//w*16))
            for label, image in zip(('source','baseline','candidate'),canvases):
                image.save(self.out / (name+'-'+label+'.png'))
            panel = Image.new('RGB', (w*96+48,h*32+56), '#18212b')
            draw = ImageDraw.Draw(panel)
            for n,(label,image) in enumerate(zip(('Original FireRed','Released Crystal theme','New reviewed counterparts'),canvases)):
                x=8+n*(w*32+16);draw.text((x,6),label,font=font,fill='white')
                panel.paste(image.resize((w*32,h*32),Image.Resampling.NEAREST),(x,32))
            panel.save(self.out / (name+'-comparison.png'))
        (self.out / 'mandatory-native-scenes.json').write_text(json.dumps(
            [dict(game=game,map=name) for game in GAMES for name in scenes], indent=2))

    def black_ref(self):
        for row in self.current.values():
            ref = row.get('donor')
            if ref and ref.get('game') == 'crystal' and ref.get('monochrome'):
                if set(self.gb_image(ref).get_flattened_data()) == {(0, 0, 0, 255)}:
                    return copy.deepcopy(ref)
        raise AssertionError('Released exact original black glyph unavailable')

    def emit(self, name, art, note, priority):
        pair, mid, signature = SOURCES[name]
        assert self.source_signature('firered', pair, mid) == signature
        matching = next(g for g in self.remaining if g['signature'] == signature)
        checked = []
        for source in matching['sources']:
            game, tp, tm = source['game'], source['pair'], source['id']
            key = game, 'gen2', tp, tm, None
            assert key not in self.current and key not in self.rows
            assert self.source_signature(game, tp, tm) == signature
            cell = self.imp.cell_index(game)[tp, tm]
            over = preview.native_donor(self.cache, dict(game=game, tileset=tp, id=tm, hash=source['rgba']),
                self.packed, ['over'], {'over': cell['layer_sha256']['over']})
            source_mask = ''.join('1' if p[3] else '0' for p in over.get_flattened_data())
            assert source_mask == priority, ('Source priority plane changed', name, game, tp, tm)
            selected = copy.deepcopy(art)
            selected['overMask'] = priority
            row = self.row(game, tp, tm, 'gen2', selected, note +
                ' Original source layout, permissions, collisions, doors/warps, NPCs, scripts and events are unchanged.')
            row['reverseGen2KantoComplete'] = dict(kind=name, pixel_scale=1, source_signature=signature,
                source_pair=pair, source_id=mid, source_layers=cell['layer_sha256'],
                native_source_priority_mask_sha256=catalog.sha(priority.encode()), witnesses=source['witnesses'])
            checked.append(dict(game=game, pair=tp, id=tm, count=source['count']))
        self.decisions.append(dict(kind=name, source_signature=signature, sources=checked,
                                  cells=sum(s['count'] for s in checked), art=art, evidence=note))

    def first_reviewed_families(self):
        # GSC's jump trigger is the grass cell above the visible ledge.
        # Its physical lower quadrant, rather than that trigger's grass art,
        # is the actual whole16px equivalent of the GBA south-facing lip.
        assert 26 in self.imp.table('crystal','maps')['ROUTE_1']['blocks']
        ledge = self.gb_ref('crystal','ROUTE_1',26,2)
        self.emit('south_jump_ledge', self.native(ledge, 'classic_gen2_complete_south_jump_ledge'),
            'Actual south jump ledge reviewed as a whole horizontal source field/stone lip. Original Crystal '
            'Route1 block26 lower-left quadrant is the complete visible16px south-facing ledge, with matching '
            'pale Kanto field above its stone edge. Its upper quadrant carries the original GSC hop trigger but '
            'contains only grass; that trigger graphic is deliberately not mistaken for the physical ledge. '
            'Every native ledge pixel stays1:1; the GBA south-hop direction and landing mechanics remain native.',
            '0' * 256)
        black = self.black_ref()
        # Actual outer Rocket-room partitions are eight opaque OVER columns
        # beside an empty void, not a walking-floor tile or an entire16px wall.
        west = self.gb_at('crystal', 'TEAM_ROCKET_BASE_B1F', 0, 4)
        east = self.gb_ref('crystal', 'TEAM_ROCKET_BASE_B1F', 10, 3)
        for name, ref, dx in (('rocket_west', west, 8), ('rocket_east', east, 0)):
            wall_image = self.gb_image(ref)
            assert set(wall_image.crop((4,0,12,16)).get_flattened_data()) == {(58,58,58,255)}
            # Preserve both original edge strokes; remove only the plain gray
            # interior columns to fit the source's eight-pixel wall width.
            parts = [dict(donor=ref,srcX=0,srcY=0,w=4,h=16,x=dx,y=0),
                     dict(donor=ref,srcX=12,srcY=0,w=4,h=16,x=dx+4,y=0)]
            art = self.composite(black, parts,
                                 'classic_gen2_complete_native_' + name + '_partition')
            priority = ''.join('1' if dx <= x < dx + 8 else '0' for y in range(16) for x in range(16))
            self.emit(name, art,
                'Whole native source Rocket partition reviewed along Hideout B1F and Warehouse room boundaries. '
                'Both original Crystal wall edge strokes and their full16px height stay1:1 on the correct handed side; '
                'only eight identical flat-gray interior columns are omitted to fit the native source8px width. '
                'the empty half remains exact original black. The actual128-pixel source OVER plane is preserved '
                'exactly, so neither a floor rectangle nor a whole opaque overhead tile replaces it.', priority)
        # This source row is the lower half of an overhead wall lip, with the
        # actual office floor visible above it. Adjacent released wall bands
        # already use this same original Silph horizontal module.
        floor = self.gb_ref('crystal', 'SILPH_CO_1F', 7, 0)
        wall = self.gb_ref('crystal', 'SILPH_CO_1F', 1, 0)
        art = self.composite(floor, [dict(donor=wall, srcX=0, srcY=0, w=16, h=8, x=0, y=8)],
                             'classic_gen2_complete_silph_front_wall_lip')
        self.emit('silph_front_lip', art,
            'Actual Silph office partition lip reviewed in the full3F/2F layouts and joined source818/816/824 band. '
            'The complete original8px Silph wall stripe lies in the lower half; the upper half exposes the same '
            'native Crystal office floor as neighboring820/821. The original lower128 OVER pixels are retained '
            'without painting the upper floor over actors.', '0' * 128 + '1' * 128)
        # Soul House's complete16px memorial has a plaque, pedestal and a
        # stippled right-hand shadow. Keep every dark/olive object pixel and
        # all manually bounded light frame/plaque pixels; remove only the
        # exterior two light checker shades imposed by its source palette.
        grave = self.gb_at('crystal', 'SOUL_HOUSE', 0, 2)
        original = self.gb_image(grave)
        colors = sorted(set(original.get_flattened_data()))
        assert colors == [(58, 58, 58, 255), (132, 107, 25, 255), (173, 140, 58, 255), (214, 197, 140, 255)]
        bounds = [(4,10),(3,11),(2,12),(2,12),(2,12),(2,12),(0,14)] + [(0,12)] * 7 + [(0,10),(0,10)]
        assert len(bounds) == 16
        mask = [bounds[y][0] <= x < bounds[y][1] or original.getpixel((x,y)) in colors[:2]
                for y in range(16) for x in range(16)]
        parts = [dict(donor=grave, srcX=p['x'], srcY=p['y'], **p) for p in runs(mask)]
        assert len(parts) <= 32
        base = self.gb_ref('crystal', 'SAFFRON_GYM', 15, 0)
        art = self.composite(base, parts, 'classic_gen2_complete_soul_house_gravestone')
        rendered = self.render(art)
        assert all(rendered.getpixel((x,y)) == original.getpixel((x,y)) for y in range(16) for x in range(16) if mask[y*16+x])
        assert all(original.getpixel((x,y)) in colors[2:] for y in range(16) for x in range(16) if not mask[y*16+x])
        self.emit('tower_grave', art,
            'Complete native Crystal Soul House memorial at(0,2), including the whole plaque/frame/pedestal and '
            'native stippled shadow, replaces the actual16px Pokemon Tower grave at1:1. Explicit native silhouette '
            'removes only its exterior checker field, exposing the existing selected Tower floor rather than a '
            'brown/pink background rectangle. Every retained native object/shadow pixel is independently checked.', '0' * 256)
        (self.out / 'complete-gravestone-mask-proof.json').write_text(json.dumps(dict(ref=grave,
            native_dimensions=[16,16], retained_native_pixels=sum(mask), silhouette_rows=[
                ''.join('1' if mask[y*16+x] else '0' for x in range(16)) for y in range(16)],
            original_native_rgba_sha256=catalog.sha(original.tobytes()), all_retained_pixels_exact=True), indent=2))
        rendered.resize((256,256), Image.Resampling.NEAREST).save(self.out / 'complete-gravestone-counterpart.png')
        # Native Crystal's final Mt Silver room uses empty gray space around
        # its summit. This is the counterpart to Navel Rock's plain sky,
        # confirmed by the full map; the blue source is not swimmable water.
        sky = self.gb_at('crystal', 'SILVER_CAVE_ROOM_3', 0, 0)
        assert set(self.gb_image(sky).get_flattened_data()) == {(58,58,58,255)}
        self.emit('summit_sky', self.native(sky, 'classic_gen2_native_summit_empty_sky'),
            'The actual full Navel Rock summit places this plain blue background outside the raised summit rock. '
            'It is empty elevated sky, not water or walking floor. The original Crystal Mt Silver summit empty '
            'gray background at(0,0) provides its native classic counterpart at1:1.', '0' * 256)
        for name, donor, role, note in (
            ('lab_floor', self.gb_ref('crystal','OAKS_LAB',32,2), 'lab_metal_floor',
             'Complete pale laboratory walking-floor squares in the actual Cinnabar laboratory rooms use the same original Crystal Oaks lab metal-floor planking as the already reviewed neighboring lab floor.'),
            ('home_parquet_floor', self.gb_ref('crystal','PLAYERS_HOUSE_1F',3,0), 'home_parquet_floor',
             'Actual Copycat room parquet, repeated uninterrupted beneath the furniture, uses the complete original Crystal home timber floor at1:1. This is a plain wood surface, not stairs, a cabinet corner or a rug border.'),
            ('museum_floor', self.gb_ref('crystal','RUINS_OF_ALPH_AERODACTYL_CHAMBER',5,3), 'museum_stone_floor',
             'The native Pewter museum floor has a repeated whole octagonal stone-paving motif in both floors of the museum, separate from fossil exhibits and stands. Complete original Crystal Ruins stone paving is the native classic material counterpart at1:1.')):
            assert self.imp.cell_index('crystal')[donor['tileset'],donor['id'],donor['quadrant']]['collision'] != 7
            self.emit(name, self.native(donor, 'classic_gen2_complete_' + role), note, '0' * 256)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contacts', action='store_true')
    parser.add_argument('--stage', action='store_true')
    parser.add_argument('--validate', action='store_true')
    args = parser.parse_args()
    review = Complete()
    inventory = review.remaining_inventory()
    if args.contacts:
        review.contacts()
    result = {k: inventory[k] for k in ('games', 'remaining_cells', 'source_groups', 'actual_used_source_keys')}
    if args.stage or args.validate:
        rows = review.stage()
        review.previews()
        result['rows'] = len(rows)
        result['new_cells'] = sum(sum(u['count'] for u in review.usage[r['game'],r['tileset'],r['id']]) for r in rows)
        if args.validate and rows:
            result['proof'] = review.validate()
        review.write(review.out / 'candidate.lua')
        (review.out / 'stage-summary.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
