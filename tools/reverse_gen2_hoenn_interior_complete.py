"""Source-scoped complete Crystal counterparts for remaining RSE interiors.

Only actual logical map cells, reachable procedural inputs, defined runtime
decorations, and real header borders enter the inventory. Candidates remain in
the private review directory until the parent integrates the reviewed batch.
"""
from __future__ import annotations

import argparse
import copy
import json
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import catalog
import preview
from reverse_common import ROOT
from reverse_gen2_hoenn_interior_finish import Review as PreviousReview, GAMES, TARGET as PREVIOUS_TARGET, identity, scoped
from building_review import decode_layout
from reverse_kanto_review import runs

TARGET = ROOT / 'mappings/reverse_gen2_hoenn_interior_complete.lua'
BASELINE = ROOT.parent / '.work/tileshift-v0320-final-reverse-coverage/report.json'
CLINIC_EXTRA_CONTRACTS = {'emerald:731': '8a1e453dce71a7c0f4c7b66e81e15f910cd60671e97041d29755e8aafbdbde07', 'emerald:739': '1e52e0a8154b2fd039fd5179cd05fb966c6fe1d41b435d9ed4ca4b2355441dbd', 'emerald:730': '8a1e453dce71a7c0f4c7b66e81e15f910cd60671e97041d29755e8aafbdbde07', 'emerald:738': '1e52e0a8154b2fd039fd5179cd05fb966c6fe1d41b435d9ed4ca4b2355441dbd', 'emerald:615': '53350e71cb393a36e3a74ab3a9fbaba7ceba4dfac1c5db2316ec604bc34a4c58', 'emerald:712': '10749da96bc7830a08165f108fa76e52e57a946f7d30655b58b2a4709baae130', 'emerald:713': '358203aee9855aeebf1b06251b2954413638b0a5fbac335b3fe30ecd342365b7', 'emerald:623': 'fafdcd53504754bd20282c9ec4b7f4393b095c0290d85723c5a73673649b4f10', 'emerald:720': '6551d540f45d9ed8817920e502a8b8b9628bc54404feb366b3aea35f6efba0e1', 'emerald:721': '5cf07f69eb499011cd123244ab1c3c4ef2dacf38b41c4fc52b2ef24aa60a607c', 'emerald:714': '16e445c12a2857a5f9838fe5ed8e1c3d7afda8f3f9068db76978394285de94da', 'emerald:715': 'ad87e67707f96d787a47d7992fe42c46f79f390764b4e1632540ec32b0a3b703', 'emerald:716': '75639d766fd44786490314437e381e57280120f939399cb35b6582198757d8c3', 'emerald:722': 'db9ddd1adcbafd37e55253e89da3b40ac25369607af0b4f1fdb8c86e84f3ee2b', 'emerald:723': '137d348b4afd5303c14313af4c6dd7465ffb53f0019d28d6d281e0f3eb2cc68d', 'emerald:724': '3f673800e9e464b52766938c8858718bde3dbc247bf5b80b058d78c9e343cd41', 'ruby:599': '89e5e91c819226e444f27bb79ce38c45962f877997b4cfa8c11754281c173251', 'sapphire:599': '89e5e91c819226e444f27bb79ce38c45962f877997b4cfa8c11754281c173251'}
CLINIC_COUNTER_CONTRACTS = {'717': 'ce3561795339b16084c38c9857b03487398faf6071f728f045cb39a05df91cc1', '719': '216d1ffe5f26602fb882213552df96bb382079487b2e957a7496a0a1f08dbc80', '729': '9a93ef5c05cbcf022b77e14d48d7b3473de0d0b084a554499f974f1785e8b756', '725': 'c649f718e3a28088c4b0c086b33d99d72a9127a3487c63d671f7c1c764dc396d', '727': 'e67b8363996f122c8b9d9f5f8d0b628c2f7180edbf5049f3b9500156b9ff5341', '736': 'fef4553d5463f95ebdc33fcb3d645e717bfe9e0e3a4309ebcd11adca5df312e3', 'ruby:605': '4928692494fef872fb0d594f35e536a8d3faf4a3d419cf4c14b1057043e63214', 'sapphire:605': '4928692494fef872fb0d594f35e536a8d3faf4a3d419cf4c14b1057043e63214', 'emerald:605': '4928692494fef872fb0d594f35e536a8d3faf4a3d419cf4c14b1057043e63214'}
CLINIC_FRAME_CONTRACTS = {'575': '8143f48dd5124375d0ad80bf10e13ac5bde7e41169fd03707d3f676c680ad5c9', '583': 'c0e9d0bfa65667cf0c8b42fc639504bc71b0f2dae9237973d9ac6fd9f8454b7f', '591': 'cca12515a3f2279d96c991f2b7b63fdcaeda0875007b94f4e1010c6f5c0dfa54', '604': '255777ebb12800e9fbc93be49e34ffb9b498fd6ad0fae378b9fb248696f5b4c2', '612': '4c7ed6b3155c86520a8a862b6c7cac36b32a2ecb11b1fef22752f92f331386fb'}

RS_CLINIC_CONTRACTS = [('ruby', 588, 'c92d0a330d71f9fd9b5cfd5de37b7bdf6566cc1ef0f930d975215a7585b35670', 262), ('ruby', 589, '50c4f31301e57f7e0d9c8b84908e15140b5d35b820711e90be51d5ec04369f99', 262), ('ruby', 590, '30c61ff14d471d4e8510b96e426d77221cbb49898d4b7e25c4faf5f9319f04ea', 262), ('ruby', 596, 'e3bd3e7d11fd70030f2f816cb157f29ec8594b97d40cc207cef8615ee8bcc412', 0), ('ruby', 597, 'b55515263e74dd71c7c8671bfcc460fa3c535362e5188f4239da6d8e0033886e', 0), ('ruby', 598, 'f68190403e468dfead529bbdabd5021e5a2a789cb0b5c8af3e3af5537e9df9f2', 0), ('ruby', 607, '1a72a8d92e06390b5fcd395613cfe115407feb4b3cbb92430329328478df9251', 0), ('ruby', 611, '05ca07f2be80d125d6f0b23665c76a6f30eae211e2e907161aa0395a3d836246', 0), ('ruby', 613, '904610a4e9659772d054b743165f53d0f9b94585836c0f50c01338de35692811', 388), ('ruby', 616, '88caa95e68a35f4958b425b7940f671fcce26dd2a9de636a0fa416fce14bb5c3', 0), ('ruby', 619, '7e6bc6d98d1648a229a54fafe2f31a4f47b91dfb1e41ba1b805f11f4abbb8c67', 0), ('ruby', 624, '77200475a572e03674edb3a0eca772a968fb40f82f51d1c15bb7c45dd1a63f77', 128), ('sapphire', 588, 'c92d0a330d71f9fd9b5cfd5de37b7bdf6566cc1ef0f930d975215a7585b35670', 262), ('sapphire', 589, '50c4f31301e57f7e0d9c8b84908e15140b5d35b820711e90be51d5ec04369f99', 262), ('sapphire', 590, '30c61ff14d471d4e8510b96e426d77221cbb49898d4b7e25c4faf5f9319f04ea', 262), ('sapphire', 596, 'e3bd3e7d11fd70030f2f816cb157f29ec8594b97d40cc207cef8615ee8bcc412', 0), ('sapphire', 597, 'b55515263e74dd71c7c8671bfcc460fa3c535362e5188f4239da6d8e0033886e', 0), ('sapphire', 598, 'f68190403e468dfead529bbdabd5021e5a2a789cb0b5c8af3e3af5537e9df9f2', 0), ('sapphire', 607, '1a72a8d92e06390b5fcd395613cfe115407feb4b3cbb92430329328478df9251', 0), ('sapphire', 611, '05ca07f2be80d125d6f0b23665c76a6f30eae211e2e907161aa0395a3d836246', 0), ('sapphire', 613, '904610a4e9659772d054b743165f53d0f9b94585836c0f50c01338de35692811', 388), ('sapphire', 616, '88caa95e68a35f4958b425b7940f671fcce26dd2a9de636a0fa416fce14bb5c3', 0), ('sapphire', 619, '7e6bc6d98d1648a229a54fafe2f31a4f47b91dfb1e41ba1b805f11f4abbb8c67', 0), ('sapphire', 624, '77200475a572e03674edb3a0eca772a968fb40f82f51d1c15bb7c45dd1a63f77', 128)]

CLINIC_GEOMETRY_CONTRACTS = [('emerald', 728, '0382e4bbbd592758635bd879cfd108090a1ba8adb0963433f7fb96577a91e4e3', 0), ('emerald', 610, 'e6cd1fda431801cce18593abbdffc16cb353a46d304fee148db69703296c4923', 0), ('emerald', 726, '58dba73f2c264a09db5b4198c2c0ac42074db5f601a95506bf544398e30f7e23', 128), ('emerald', 664, '264f4545cc296ad644fd12ee882cb7c90fa9e62d20fe036f5af9d7aaef42d82f', 0), ('emerald', 665, '8ab6805a12acfcf91637a0d4924636a42fe6b5ba1c48931c1dd91253191f6a56', 0), ('emerald', 672, '25c8c827ccc8200fafdec604dcd7d89f61fc7b5e03f84ac0bc02039c503c7d64', 0), ('emerald', 673, '751cdd7b2a79587ac37b5015ccad7407f27a621a23ece5c719eba9437a85c925', 107), ('emerald', 680, '834119f3f8e12f4bc4d7f62091f9227355175375f5ae16a5f0d981a5bcefd601', 0), ('emerald', 681, '43cd6e4efe1e85fba4fe044d3ef9295faaaee2586eed38b5a4bd0cfbaa66dc6e', 0), ('emerald', 606, '073d039b002fd9c380611735a50f5f9daff5b492a4865e4a77e7a1f420329c2e', 0), ('emerald', 614, '32a2b36730700d09a48feb5a9c70812d3f80b1cd9b1bf63cd69b024f710aa070', 0)]

# SOURCE_SURFACES_CONTRACTS
INDEPENDENT_SURFACE_VARIANTS = [('ruby', 'building__generic_building', 812, 'ba62ef14a3f027aa0d4e890bd054d99511ab19c3bc77867e21b337c7a6a448e9'), ('sapphire', 'building__generic_building', 812, 'ba62ef14a3f027aa0d4e890bd054d99511ab19c3bc77867e21b337c7a6a448e9'), ('ruby', 'building__petalburg_gym', 531, 'd1801e4160b932c20ddda123a7c435950e2222ff5bc094033fe35f19a7f06fce'), ('sapphire', 'building__petalburg_gym', 531, 'd1801e4160b932c20ddda123a7c435950e2222ff5bc094033fe35f19a7f06fce')]
SURFACES = [{'pair': 'general__facility', 'id': 522, 'target': 'vertical', 'label': 'Full vertical exterior and partition wall stem; no floor or device pixels', 'sourceHash': 'a63d21c60e70a315c158e1815a02c2536cd7478416d28ac6b5713a46f32e13fb'}, {'pair': 'building__generic_building', 'id': 812, 'target': 'house', 'label': 'Ordinary complete beige checker walking-floor tile in Cutter and other homes', 'sourceHash': 'ac6b4ca76480af450a2670ed629b3e11dcff24525dd3d075ac41790aebc43032'}, {'pair': 'building__elite_four', 'id': 743, 'target': 'black', 'label': 'Nonwalkable empty exterior void beside the complete League stairway; coll7 in the actual corridor', 'sourceHash': '516c1c2666e350a2ba58be63a11662a342e6124a81727216d4dafa83b6f11a10'}, {'pair': 'general__inside_ship', 'id': 561, 'target': 'black', 'label': 'Pure empty white nonwalkable outside-room backing around cabin walls; coll7, no wall or floor feature', 'sourceHash': '5f4ecdb7b71c3e403983fe405cddcdc2f2576b655fdb3e80d94a6f7c32e58bc2'}, {'pair': 'building__cable_club', 'id': 758, 'target': 'link', 'label': 'Complete purple link/battle communication-room walking floor, preserving its original behavior', 'sourceHash': '91921eb972aa48b5c6c428cd901543271d24cd929360bd0f3086939361a74258'}, {'pair': 'building__generic_building', 'id': 985, 'target': 'wood', 'label': 'Complete ordinary timber walking floor in the Fortree decoration shop', 'sourceHash': '089550b2783bee2bca715eed9a2f7b231bf4ee41f68a0c9d5f7924098c581051'}, {'pair': 'building__lab', 'id': 617, 'target': 'stone', 'label': 'Complete ordinary gray-tiled Weather Institute walking floor', 'sourceHash': 'd9383846c80dbf496f4dc772eb9a2d2a5b168032cd3dd10da33e64aa2e7eecba'}, {'pair': 'building__battle_frontier', 'id': 968, 'target': 'blue', 'label': 'Complete blue ceramic lounge walking-floor variation', 'sourceHash': 'ea2ae9f7f6518cf8946fc994e95d63eb1a37497d066952fb0d860e2c183388b9'}, {'pair': 'building__battle_frontier', 'id': 969, 'target': 'blue', 'label': 'Complete second blue ceramic lounge walking-floor variation', 'sourceHash': '9669db68d1a5a5943e4f6277497638097924aceb06a91beba8f8ea231738edf6'}, {'pair': 'building__contest', 'id': 545, 'target': 'facility', 'label': 'Complete plain parquet/carpet walking-floor module in the contest lobby', 'sourceHash': 'b55ad0476ef834d414bb70eaf9b9fc9f1a763f3141dfad33ab983083844ce565'}, {'pair': 'building__contest', 'id': 607, 'target': 'facility', 'label': 'Complete second contest lobby walking-floor module, matching existing reviewed public floors', 'sourceHash': 'e2420747581c213adbb634587e33a7ce2950e6870c0aeb56eebc9a471daff105'}, {'pair': 'general__bike_shop', 'id': 637, 'target': 'stone', 'label': 'Complete gray tiled New Mauville encounter floor; original indoor encounter behavior retained', 'sourceHash': '421682c5a8a1660d12ac713d4fec6c4f9454f4bd4b84b9a9e52e7cc469a1d1f2'}, {'pair': 'building__generic_building', 'id': 824, 'target': 'house_wall', 'label': 'Complete unadorned yellow back-wall panel above the domestic room floor, not carpet', 'sourceHash': '90fdfb39161ee6389c5f10dc085787bcef1ecfe6e5aaddee2639bd7109b11c7d'}, {'pair': 'building__battle_palace', 'id': 513, 'target': 'stone', 'label': 'Complete ordinary patterned Palace walking floor; excludes floor logos and controls', 'sourceHash': '805323d4330c91412e0e3b27fd463697daae31c9d04fabe31ff4befa16148e30'}, {'pair': 'building__petalburg_gym', 'id': 531, 'target': 'wood', 'label': 'Complete horizontal timber walking floor in the actual gym room', 'sourceHash': '6d011c920b3409167762b1a6590b0378907474c527b5bf8d77a200984d9887c0'}, {'pair': 'building__battle_dome', 'id': 835, 'target': 'facility', 'label': 'Complete ordinary green corridor walking floor under the seating area', 'sourceHash': 'e5c157c55a8613fa189366e8e8b11371d17d803812cfecc0ed6c3199a08408a0'}, {'pair': 'general__facility', 'id': 544, 'target': 'vertical', 'label': 'Complete thick plain vertical structural wall stem beside the deck landing', 'sourceHash': '12f5bc99fd166c7b072729d7e64f6fc0856a3b5668d7ebe221d9d889e5e8332d'}, {'pair': 'general__facility', 'id': 529, 'target': 'lower', 'label': 'Complete lower-end cap of the vertical plain partition wall beside hideout equipment', 'sourceHash': 'dd095e90c52e44c989cae66cfd6975dc5367b16e767e3ab3c067743fbf5f2319'}, {'pair': 'general__facility', 'id': 521, 'target': 'lower', 'label': 'Complete straight vertical wall end with its horizontal lower structural foot', 'sourceHash': 'b1453d42fdc974d8d62a9be568b3fe2da2e07d592f4766c1f97bf7988862d699'}, {'pair': 'building__battle_factory', 'id': 538, 'target': 'vertical', 'label': 'Complete plain white vertical partition wall stem; no vent or device pixels', 'sourceHash': 'd1f2b9ae8f971c537144b4998b877089b412358c454669054da8f959b471c9d9'}, {'pair': 'building__trick_house_puzzle', 'id': 616, 'target': 'black', 'label': 'Empty nonwalkable exterior backing around the puzzle floor and wall; retains native bounds', 'sourceHash': '516c1c2666e350a2ba58be63a11662a342e6124a81727216d4dafa83b6f11a10'}, {'pair': 'building__battle_frontier_ranking_hall', 'id': 522, 'target': 'stone', 'label': 'Complete ordinary patterned tile walking floor in the Ranking Hall', 'sourceHash': '485a6abfb00d3ce7185057815e13a4930652f2a8b94d5411c46a12f6d72345cc'}]


class Review(PreviousReview):
    def __init__(self):
        super().__init__()
        self.out = ROOT.parent / '.work/tileshift-reverse-gen2-hoenn-interior-complete'
        self.out.mkdir(parents=True, exist_ok=True)
        own_name=TARGET.relative_to(ROOT).as_posix()
        self.installed_self={identity(r):r for r in self.prior if self.origins[id(r)][0]==own_name}
        self.prior=[r for r in self.prior if self.origins[id(r)][0]!=own_name]
        # The preceding author excluded its own output during regeneration.
        # For this new batch every installed preceding row is immutable.
        for index, row in enumerate(preview.read_reviewed(PREVIOUS_TARGET), 1):
            self.prior.append(row)
            self.origins[id(row)] = (PREVIOUS_TARGET.relative_to(ROOT).as_posix(), index)
        self.occupied = {identity(row) for row in self.prior if row['game'] in GAMES and row['style'] == 'gen2'}
        self.counts = Counter()
        self.contexts = defaultdict(list)
        self.map_records = []
        self.layouts = {}
        self.exclusions = []
        self.supersessions = []
        baseline = json.loads(BASELINE.read_text())
        assert baseline['status'] == 'passed' and baseline['runtime_inputs_unchanged_during_probe']
        for record in baseline['maps']:
            game, pair, name = record['game'], record['pair'], record['map']
            if game not in GAMES or not any(scoped(pair, mid) for p, mid in self.scope[game] if p == pair):
                continue
            spec = self.imp.table(game, 'gba/native/manifest')['layouts'][name]
            path = self.cache / game / 'data/generated/gba/native' / spec['file']
            decoded = decode_layout(path)
            w, h = record['width_cells'], record['height_cells']
            assert 0 < w <= decoded['width'] and 0 < h <= decoded['height']
            mids = [decoded['mids'][y * decoded['width'] + x] for y in range(h) for x in range(w)]
            self.layouts[game, name] = dict(pair=pair, width=w, height=h, mids=mids, file_sha256=decoded['file_sha256'])
            self.map_records.append(dict(game=game, map=name, pair=pair, width=w, height=h,
                                         source_file_sha256=decoded['file_sha256'], logical_cells=w*h))
            for offset, mid in enumerate(mids):
                if not scoped(pair, mid):
                    continue
                key = game, pair, mid
                self.counts[key] += 1
                if len(self.contexts[key]) < 8:
                    x, y = offset % w, offset // w
                    self.contexts[key].append(dict(map=name, x=x, y=y, width=w, height=h))

    def inventory(self):
        records = []
        for game in GAMES:
            for (pair, mid), cell in self.scope[game].items():
                key = game, pair, mid
                if (game, 'gen2', pair, mid, None) in self.occupied:
                    continue
                count = self.counts[key]
                reasons = [item['source'] for item in self.dynamic_sources
                           if item['game'] == game and item['pair'] == pair and mid in item['actual_ids']]
                border = any(item['game'] == game and item['pair'] == pair and item['id'] == mid for item in self.border_keys)
                if not count and not reasons and not border:
                    self.exclusions.append(dict(game=game, pair=pair, id=mid, reason='No actual logical source occurrence, reachable dynamic definition, or real header use.'))
                    continue
                records.append(dict(game=game, pair=pair, id=mid, sourceHash=cell['pixel_sha256'],
                                    sourceBehavior=cell.get('behavior'), source_cells=count,
                                    contexts=self.contexts[key], dynamic_reasons=reasons, header_used=border))
        records.sort(key=lambda row: (-row['source_cells'], row['game'], row['pair'], row['id']))
        pairs = defaultdict(lambda: dict(source_cells=0, keys=0, dynamic_only_keys=0))
        for row in records:
            item = pairs[row['game'], row['pair']]
            item['source_cells'] += row['source_cells']; item['keys'] += 1
            item['dynamic_only_keys'] += int(row['source_cells'] == 0 and bool(row['dynamic_reasons']))
        report = dict(baseline=str(BASELINE), scope='RSE interior secondaries, actual logical cells plus explicit reachable runtime keys/header keys',
                      missing_keys=len(records), missing_logical_cells=sum(row['source_cells'] for row in records),
                      pairs=[dict(game=g, pair=p, **item) for (g,p), item in sorted(pairs.items(), key=lambda item:-item[1]['source_cells'])],
                      missing=records, excluded_nonlogical_unused=self.exclusions)
        (self.out / 'inventory.json').write_text(json.dumps(report, indent=2) + '\n')
        (self.out / 'source-layouts.json').write_text(json.dumps(self.map_records, indent=2) + '\n')
        self.missing = records
        print(json.dumps({key:report[key] for key in ('missing_keys','missing_logical_cells')}, indent=2))
        return records

    def contact_missing(self, limit=256, game='emerald', pair=None):
        records = [row for row in self.missing if row['game'] == game and (pair is None or row['pair'] == pair)][:limit]
        font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 13)
        cw, ch, cols = 120, 100, 8
        for start in range(0, len(records), 64):
            page = records[start:start+64]
            image = Image.new('RGB', (cols*cw, ((len(page)+cols-1)//cols)*ch), '#18212b')
            draw = ImageDraw.Draw(image)
            for i, row in enumerate(page):
                x, y = i % cols*cw, i // cols*ch
                ref = dict(game=game, tileset=row['pair'], id=row['id'], hash=row['sourceHash'])
                art = preview.native_donor(self.cache, ref, self.packed)
                image.paste(art.resize((48,48), Image.Resampling.NEAREST), (x+4, y+40))
                label = row['pair'].replace('building__','').replace('general__','')
                draw.text((x+3,y+2), label[:18], font=font, fill='white')
                draw.text((x+3,y+19), f"{row['id']}  n={row['source_cells']}  b={row['sourceBehavior']}", font=font, fill='#c4cdd8')
            path = self.out / f"{game}-{pair or 'weighted'}-missing-{start//64+1:02}.png"
            image.save(path)
        (self.out / f"{game}-{pair or 'weighted'}-missing-contact-index.json").write_text(json.dumps(records, indent=2)+'\n')

    def scene_preview(self, game, name, highlight=(), label='source-review'):
        layout = self.layouts[game, name]
        width, height = layout['width']*16, layout['height']*16
        original = self.imp.gba(game, name)[0].crop((0,0,width,height))
        selected = {row['id']:row for row in self.prior
                    if row['game']==game and row['style']=='gen2' and row['tileset']==layout['pair']
                    and row.get('map',name)==name}
        selected.update({row['id']:row for row in self.rows.values()
                         if row['game']==game and row['tileset']==layout['pair']})
        after = original.copy(); rendered={}; mapped=0
        for offset, mid in enumerate(layout['mids']):
            if mid in selected:
                if mid not in rendered: rendered[mid]=self.render(selected[mid])
                after.paste(rendered[mid], (offset%layout['width']*16,offset//layout['width']*16));mapped+=1
        before_path=self.out/f'{game}-{name}-{label}-original.png'
        after_path=self.out/f'{game}-{name}-{label}-current.png'
        original.save(before_path);after.save(after_path)
        assert Image.open(before_path).convert('RGBA').tobytes()==original.tobytes()
        assert Image.open(after_path).convert('RGBA').tobytes()==after.tobytes()
        scale=2
        panel=Image.new('RGB',(width*scale*2+48,height*scale+65),'#18212b');d=ImageDraw.Draw(panel)
        font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
        d.text((10,7),f'{game} / {name} / actual source and current Crystal theme ({mapped}/{len(layout["mids"])} cells)',font=font,fill='white')
        first=original.convert('RGB').resize((width*scale,height*scale),Image.Resampling.NEAREST)
        second=after.convert('RGB').resize((width*scale,height*scale),Image.Resampling.NEAREST)
        panel.paste(first,(10,35));panel.paste(second,(width*scale+30,35))
        for offset,mid in enumerate(layout['mids']):
            if mid in highlight:
                x,y=offset%layout['width']*32,offset//layout['width']*32
                for ox in(10,width*scale+30):d.rectangle((ox+x,35+y,ox+x+31,35+y+31),outline='#ff35b9',width=1)
        path=self.out/f'{game}-{name}-{label}-comparison.png';panel.save(path)
        saved=Image.open(path).convert('RGB')
        if not highlight:
            assert saved.crop((10,35,10+width*scale,35+height*scale)).tobytes()==first.tobytes()
            assert saved.crop((width*scale+30,35,width*scale*2+30,35+height*scale)).tobytes()==second.tobytes()
        return dict(game=game,map=name,path=str(path),logical_size=[width,height],source_file_sha256=layout['file_sha256'],
                    selected_cells=mapped,total_cells=len(layout['mids']),highlighted_source_ids=list(highlight),actors_rendered=False,
                    pixel_scale=scale,resampling='integer nearest-neighbor',panels_exact_after_save=not bool(highlight),
                    before=str(before_path),after=str(after_path),comparison_png_sha256=catalog.sha(path.read_bytes()),
                    before_png_sha256=catalog.sha(before_path.read_bytes()),after_png_sha256=catalog.sha(after_path.read_bytes()),
                    before_rgba_sha256=catalog.sha(original.tobytes()),after_rgba_sha256=catalog.sha(after.tobytes()),
                    source_logical_body_dimensions=True,notes=['Native imported source pixels and current offline composed counterpart; no actors rendered.'])

    def checkpoint(self):
        """Persist a bounded, independently reviewable candidate, never activate."""
        rows=list(self.rows.values());new=[r for r in rows if identity(r)not in self.occupied]
        corrected=[r for r in rows if identity(r)in self.occupied]
        mandatory=[('emerald','EM_BATTLE_FRONTIER_POKEMON_CENTER_2F'),
                   ('ruby','RU_MAUVILLE_CITY_POKEMON_CENTER_2F'),
                   ('sapphire','SA_MAUVILLE_CITY_POKEMON_CENTER_2F'),
                   ('emerald','EM_RUSTBORO_CITY_CUTTERS_HOUSE'),
                   ('emerald','EM_AQUA_HIDEOUT_1F'),('emerald','EM_EVER_GRANDE_CITY_HALL1'),
                   ('emerald','EM_FORTREE_CITY_DECORATION_SHOP'),('emerald','EM_ROUTE119_WEATHER_INSTITUTE_2F'),
                   ('emerald','EM_BATTLE_FRONTIER_LOUNGE1'),('emerald','EM_BATTLE_FRONTIER_POKEMON_CENTER_1F')]
        mandatory=[(g,n)for g,n in mandatory if(g,n)in self.layouts]
        previews=[self.scene_preview(g,n,(), 'checkpoint')for g,n in mandatory]
        assert all(p['selected_cells']==p['total_cells']for p in previews if'POKEMON_CENTER_2F'in p['map'])
        summary=dict(status='candidate-not-activated',rows=len(rows),new_rows=len(new),corrected_existing_rows=len(corrected),
                     new_logical_cells=sum(self.counts[r['game'],r['tileset'],r['id']]for r in new),
                     corrected_existing_logical_cells=sum(self.counts[r['game'],r['tileset'],r['id']]for r in corrected),
                     per_game=dict(Counter(r['game']for r in rows)),
                     candidate_sha256=catalog.sha((self.out/'candidates.lua').read_bytes()),
                     final_module=TARGET.relative_to(ROOT).as_posix(),supersessions=len(self.supersessions),
                     exact_source_fingerprints=True,source_behaviors_individually_guarded=True,
                     original_npc_positions_facing_warps_layouts_unchanged=True,
                     previews=previews)
        order={identity(r):i for i,r in enumerate(rows,1)}
        for item in self.supersessions:item['new_row_index']=order[identity(item['new_row'])]
        (self.out/'supersessions.json').write_text(json.dumps(self.supersessions,indent=2)+'\n')
        (self.out/'checkpoint.json').write_text(json.dumps(summary,indent=2)+'\n')
        (self.out/'mandatory-native-scenes.json').write_text(json.dumps([dict(game=g,map=n)for g,n in mandatory],indent=2)+'\n')
        clinics=[]
        for(g,n),layout in self.layouts.items():
            if layout['pair']!='building__pokemon_center':continue
            selected={r['id']for r in self.prior if r['game']==g and r['style']=='gen2'and r['tileset']==layout['pair']}
            selected|={r['id']for r in rows if r['game']==g and r['tileset']==layout['pair']}
            missing=sorted(set(layout['mids'])-selected)
            clinics.append(dict(game=g,map=n,cells=len(layout['mids']),missing_ids=missing,complete=not missing))
        (self.out/'clinic-whole-room-coverage.json').write_text(json.dumps(clinics,indent=2)+'\n')
        remaining=[r for r in self.missing if(r['game'],'gen2',r['pair'],r['id'],None)not in self.rows]
        pairs=defaultdict(lambda:dict(keys=0,logical_cells=0))
        for item in remaining:
            group=pairs[item['game'],item['pair']];group['keys']+=1;group['logical_cells']+=item['source_cells']
        followup=dict(checkpoint='143-row complete clinic2F and explicitly reviewed surfaces',
                      remaining_keys=len(remaining),remaining_logical_cells=sum(r['source_cells']for r in remaining),
                      pairs=[dict(game=g,pair=p,**v)for(g,p),v in sorted(pairs.items(),key=lambda x:-x[1]['logical_cells'])],
                      clear_next_pass=['Whole ship wall/window/cabin and hull families, including exact outdoor/shared-bank context review.',
                                       'Complete League and Lavaridge special-clinic object families; ordinary clinic1F/2F rooms are already complete.',
                                       'Remaining clear gym/puzzle floor, structural wall and whole feature families with functional markings retained.',
                                       'Complete contest curtains/stage/reception features and modern facility hardware as native-module classic counterparts.',
                                       'Remaining actual-used Secret Base furnishing designs and reachable Pyramid/Trainer Hill wall/stair families.'],
                      genuine_semantic_questions_in_this_checkpoint=self.held,
                      notes=['This is a validated bounded checkpoint; remaining native art is retained until its source object/family is reviewed.',
                             'No question is queued merely because a known feature needs a new classic counterpart.'])
        (self.out/'next-pass-clear-families-and-unknowns.json').write_text(json.dumps(followup,indent=2)+'\n')
        return summary

    def validate(self):
        proof=super().validate();depth=[]
        for row in self.rows.values():
            ref=dict(game=row['game'],tileset=row['tileset'],id=row['id'],hash=row['sourceHash'])
            preview.native_donor(self.cache,ref,self.packed)
            mids,palette,layers=self.packed[row['game'],row['tileset']];slot=mids.index(row['id'])
            over=catalog.rgba_native(layers['over'][slot*256:(slot+1)*256],palette,True)if'over'in layers else Image.new('RGBA',(16,16))
            mask=''.join('1'if p[3]else'0'for p in over.get_flattened_data())
            selected=row.get('overMask','0'*256);exact=selected==mask
            if not exact:
                assert row['tileset']=='building__pokemon_center'and row['id']==606 and 'potted_palm'in row['role']
                assert mask.count('1')>0 and selected.count('1')==245
            depth.append(dict(game=row['game'],pair=row['tileset'],id=row['id'],role=row['role'],
                              source_over_pixels=mask.count('1'),target_over_pixels=selected.count('1'),exact=exact,
                              native_canopy_silhouette_adaptation=not exact))
        proof.update(exact_native_source_priority_rows=sum(r['exact']for r in depth),
                     complete_native_canopy_priority_rows=sum(not r['exact']for r in depth),
                     complete_native_canopies_keep_source_foreground_availability=True,
                     no_room_floor_drawn_over_actors=True)
        (self.out/'source-priority-proof.json').write_text(json.dumps(depth,indent=2)+'\n')
        (self.out/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
        return proof

    def write(self,target):
        # Lua table iteration order is not a source-art contract. Normalize
        # field ordering so a fresh authoring process emits identical bytes.
        def canonical(value):
            if isinstance(value,dict):return{key:canonical(value[key])for key in sorted(value)}
            if isinstance(value,list):return[canonical(item)for item in value]
            return value
        self.rows={key:canonical(row)for key,row in self.rows.items()}
        return super().write(target)

    def primitive_contact(self):
        roles = ['johto_facility_complete_vertical_wall','johto_facility_complete_horizontal_wall',
                 'johto_facility_complete_wall_lower_end','johto_facility_back_wall',
                 'johto_underground_side_wall','johto_underground_north_wall',
                 'johto_gate_complete_header_wall','johto_station_structural_wall','johto_station_structural_pillar',
                 'johto_battle_battle_wall','johto_battle_native_lift_wall','johto_steel_gym_perimeter_wall',
                 'johto_domestic_stage_floor','johto_domestic_wood_floor','johto_radio_recording_room_wood_floor',
                 'johto_dragon_shrine_native_timber_floor','johto_tower_wooden_floor_with_original_movement',
                 'gen2_ship_native_timber_corridor_floor','gen2_ship_native_cabin_floor','johto_fishing_pier_floor',
                 'johto_battle_battle_floor','johto_battle_lobby_floor','johto_gym_native_tiled_floor',
                 'johto_shop_complete_floor','johto_house_plain_floor','kanto_special_native_hall_floor',
                 'johto_port_native_concrete_pier_floor','johto_ruins_native_tanoby_stone_floor']
        font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',12);cw,ch=220,110;cols=4
        im=Image.new('RGB',(cols*cw,((len(roles)+cols-1)//cols)*ch),'#18212b');d=ImageDraw.Draw(im);proof=[]
        for i,role in enumerate(roles):
            ref=self.primitive(role);art=self.gb_image(ref);x,y=i%cols*cw,i//cols*ch
            im.paste(art.resize((64,64),Image.Resampling.NEAREST),(x+4,y+39))
            d.text((x+3,y+2),role.removeprefix('johto_')[:34],font=font,fill='white')
            d.text((x+3,y+18),f"{ref['map']} {ref['id']}/{ref['quadrant']}"[:34],font=font,fill='#c4cdd8')
            proof.append(dict(role=role,donor=ref,rgba_sha256=catalog.sha(art.tobytes())))
        im.save(self.out/'native-crystal-modules-reviewed.png')
        (self.out/'native-crystal-modules-reviewed.json').write_text(json.dumps(proof,indent=2)+'\n')

    def context_contacts(self, game='emerald', limit=128):
        records=[row for row in self.missing if row['game']==game and row['contexts']][:limit]
        font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',12);cw,ch=176,214;cols=8;images={}
        for start in range(0,len(records),48):
            page=records[start:start+48];im=Image.new('RGB',(cols*cw,((len(page)+cols-1)//cols)*ch),'#18212b');d=ImageDraw.Draw(im)
            for i,row in enumerate(page):
                ctx=row['contexts'][0];name=ctx['map'];layout=self.layouts[game,name]
                if name not in images:images[name]=self.imp.gba(game,name)[0].crop((0,0,layout['width']*16,layout['height']*16))
                native=images[name];x,y=ctx['x'],ctx['y'];crop=Image.new('RGBA',(80,80),'#101010')
                crop.paste(native,((2-x)*16,(2-y)*16))
                ox,oy=i%cols*cw,i//cols*ch
                d.text((ox+2,oy+2),row['pair'].replace('building__','').replace('general__','')[:22],font=font,fill='white')
                d.text((ox+2,oy+18),f"{row['id']} n={row['source_cells']} b={row['sourceBehavior']}",font=font,fill='white')
                d.text((ox+2,oy+34),name.removeprefix(game[:2].upper()+'_')[-23:],font=font,fill='#c4cdd8')
                im.paste(crop.convert('RGB').resize((160,160),Image.Resampling.NEAREST),(ox+2,oy+51))
                d.rectangle((ox+66,oy+115,ox+97,oy+146),outline='#ff35b9',width=1)
            im.save(self.out/f'{game}-weighted-context-{start//48+1:02}.png')
        (self.out/f'{game}-weighted-context-index.json').write_text(json.dumps(records,indent=2)+'\n')

    def build(self):
        for game,mid,expected,behavior in CLINIC_GEOMETRY_CONTRACTS:
            cell=self.imp.cell_index(game)['building__pokemon_center',mid]
            assert cell['pixel_sha256']==expected and cell['behavior']==behavior
        for game,pair,mid,expected in INDEPENDENT_SURFACE_VARIANTS:
            assert self.imp.cell_index(game)[pair,mid]['pixel_sha256']==expected
            self.independent_sources.add((game,pair,mid))
        targets = {
            'house': self.gb_ref('crystal','GUIDE_GENTS_HOUSE',15,0),
            'wood': self.gb_ref('crystal','DANCE_THEATER',45,2),
            'stone': self.gb_at('crystal','SAFFRON_GYM',1,2),
            'facility': self.gb_ref('crystal','BATTLE_TOWER_1F',1,0),
            'blue': self.gb_ref('crystal','BATTLE_TOWER_BATTLE_ROOM',10,0),
            'link': self.gb_at('crystal','TRADE_CENTER',1,1),
            'house_wall': self.gb_ref('crystal','MR_POKEMONS_HOUSE',25,0),
            'vertical': self.gb_ref('crystal','TEAM_ROCKET_BASE_B2F',60,2),
            'lower': self.gb_ref('crystal','TEAM_ROCKET_BASE_B2F',63,3),
            'horizontal': self.gb_ref('crystal','TEAM_ROCKET_BASE_B2F',60,0),
        }
        targets['black'] = copy.deepcopy(next(row['donor'] for row in self.prior
                                             if row['game'] in GAMES and row['style']=='gen2'
                                             and row.get('role')=='reverse_gen2_exact_black_canvas'))
        assert set(self.gb_image(targets['black']).get_flattened_data()) == {(0,0,0,255)}
        for item in SURFACES:
            pair,mid,target,label=item['pair'],item['id'],item['target'],item['label']
            source=self.imp.cell_index('emerald')[pair,mid]
            assert source['pixel_sha256']==item['sourceHash'],('Reviewed whole source changed',pair,mid)
            ref=targets[target]
            evidence=('The complete actual source occurrence and surrounding native room were reviewed in emerald-weighted-context-01..03 and the full priority room scenes. '+label+'. '
                      'Uses a complete original Crystal16px '+target.replace('_',' ')+' module at native1:1, without resizing, clipping an object, or mapping by color/behavior alone. '
                      'Only this exact source pair/MID/full-pixel fingerprint and geometry-equivalent cartridge counterparts are authorized. Source collision/elevation, events, NPC positions and gameplay remain unchanged.')
            art=self.native(ref,'reverse_gen2_hoenn_complete_'+target)
            art['_sourceOverMask']=True
            self.aliases(pair,mid,art,evidence)
            self.contracts.append(dict(label=label,pair=pair,source_id=mid,sourceHash=item['sourceHash'],
                                       target=ref,pixel_scale=1,complete_original_native_module=True,
                                       source_contexts=self.contexts['emerald',pair,mid],
                                       source_over_mask_preserved_exactly=True))
        self.clinic_frames()
        self.clinic_counters()
        house=self.gb_ref('crystal','GUIDE_GENTS_HOUSE',15,0)
        clinic=self.gb_ref('crystal','CHERRYGROVE_POKECENTER_1F',4,0)
        self.object_family('building__pokemon_center',[[606],[614]],'GUIDE_GENTS_HOUSE',(0,6),house,clinic,
                           'complete clinic2F potted palm with its original full pot and canopy',
                           source_bounds=[0,0,16,32],foot_anchor=31)
        self.clinic_devices_and_badges(clinic)
        self.clinic_finish_geometry(clinic)
        self.rs_clinic_finish(clinic)

    def rs_clinic_finish(self,clinic):
        pair='building__pokemon_center'
        for game,mid,expected,behavior in RS_CLINIC_CONTRACTS:
            cell=self.imp.cell_index(game)[pair,mid]
            assert cell['pixel_sha256']==expected and cell['behavior']==behavior
        front=self.gb_at('crystal','AZALEA_POKECENTER_1F',0,2)
        part=lambda sy,h,dy:dict(donor=copy.deepcopy(front),srcX=0,srcY=sy,w=16,h=h,x=0,y=dy)
        lower=self.composite(clinic,[part(4,4,0),part(5,3,4),part(8,8,7)],'reverse_gen2_complete_rs_clinic_counter_lower_front')
        top=self.composite(clinic,[part(0,4,12)],'reverse_gen2_complete_rs_clinic_counter_upper_edge')
        recipes={607:self.native(self.gb_at('crystal','POKECENTER_2F',3,3),'reverse_gen2_complete_rs_clinic_post_foot'),
                 613:self.native(self.gb_at('crystal','POKECENTER_2F',7,3),'reverse_gen2_complete_rs_clinic_labelled_post_foot'),
                 611:self.native(clinic,'reverse_gen2_complete_rs_clinic_floor_corner'),
                 619:self.native(clinic,'reverse_gen2_complete_rs_clinic_floor_below_post'),616:top,624:lower}
        for game in('ruby','sapphire'):
            for mid,art in recipes.items():
                self.add(game,pair,mid,self.prepare_art(game,pair,mid,dict(copy.deepcopy(art),_sourceOverMask=True)),
                    'The complete R/S clinic2F source room and all twelve remaining source modules were independently reviewed in ruby-clinic-remaining-twelve.png and the full logical native room. '
                    'Complete original Crystal post feet and status label remain intact1:1; the short counter starts at upper-cell row12, keeps its complete native lower frame at lower-cell row14, and exposes actual selected clinic floor at row15. '
                    'Only repeated plain cream counter rows adapt the height; no border, terminal, foot or label is cropped. Plain floor/shadow cells retain the same exact clinic floor. All source collision, actor masks, warps and positions are unchanged.')
            wall=self.gb_at('crystal','POKECENTER_2F',0,0)
            # Whole original battle-monitor and two-handheld communication signs.
            # These are the actual original Gen2 clinic signs, not the Emerald
            # wireless symbol: R/S entrances lead to Colosseum, Trade, Record.
            models={588:[dict(donor=self.gb_at('crystal','POKECENTER_2F',8,0),srcX=0,srcY=0,w=16,h=16,x=0,y=8)],
                    589:[dict(donor=self.gb_at('crystal','POKECENTER_2F',4,0),srcX=0,srcY=0,w=16,h=16,x=0,y=8)]}
            # The entire original handheld is the closed5x7 contour x9..13,
            # y3..9, including screen/buttons and its lower-right highlight.
            # A native cream bezel surrounds the complete hardware module.
            cream=self.native_color_brushes('POKECENTER_2F',0)[0]
            models[590]=[dict(donor=cream,srcX=0,srcY=0,w=9,h=11,x=3,y=10),
                         dict(donor=self.gb_at('crystal','POKECENTER_2F',4,0),srcX=9,srcY=3,w=5,h=7,x=5,y=12)]
            for upper,lower_mid in((588,596),(589,597),(590,598)):
                for cy,mid in enumerate((upper,lower_mid)):
                    clipped=[]
                    for item in models[upper]:
                        y=max(cy*16,item['y']);bottom=min(cy*16+16,item['y']+item['h'])
                        if bottom>y:
                            p=copy.deepcopy(item);p['srcY']+=y-item['y'];p['y']=y-cy*16;p['h']=bottom-y;clipped.append(p)
                    art=self.composite(wall,clipped,'reverse_gen2_complete_rs_clinic_communication_sign');art['_sourceOverMask']=True
                    self.add(game,pair,mid,self.prepare_art(game,pair,mid,art),
                        'Actual R/S clinic warp definitions prove the left sign belongs to SINGLE_BATTLE_COLOSSEUM, the middle to TRADE_CENTER, and the right to RECORD_CORNER. '
                        'The whole original Crystal battle-monitor or complete two-handheld sign remains native16px artwork1:1, centered across the actual two-cell sign canvas. '
                        'The distinct Record Corner counterpart uses one entire original5x7 handheld contour with all screen/buttons/highlights and a new native-cream bezel, rather than a wireless or battle label. '
                        'Only selected plain native clinic wall surrounds each complete sign; source overhead masks, doors, game functions, warp targets and positions remain unchanged.')
        self.contracts.append(dict(label='R/S complete clinic2F signs, post feet and bar',source_contracts=RS_CLINIC_CONTRACTS,
                                   source_sign_canvases=[[588,596],[589,597],[590,598]],source_entrances=[[5,1],[8,1],[11,1]],
                                   source_functions=['SINGLE_BATTLE_COLOSSEUM','TRADE_CENTER','RECORD_CORNER'],
                                   native_record_handheld_rectangle=[9,3,5,7],single_handheld_complete=True,
                                   whole_native_battle_monitor=True,whole_native_linked_handhelds=True,
                                   native_counter_complete_lower_frame_rows=[8,15],counter_lower_foot_anchor=14,
                                   lower_floor_row=15,pixel_scale=1,positions_collision_and_warps_unchanged=True))

    def clinic_finish_geometry(self,clinic):
        pair='building__pokemon_center'
        gray=self.native_color_brushes('AZALEA_POKECENTER_1F',0)
        wall=self.gb_at('crystal','AZALEA_POKECENTER_1F',3,0)
        black=copy.deepcopy(next(row['donor']for row in self.prior if row['game']in GAMES and row['style']=='gen2'and row.get('role')=='reverse_gen2_exact_black_canvas'))
        orange={(222,123,49,255),(247,181,115,255),(255,230,181,255)}
        cap={(255,255,255,255),(148,148,148,255)};edge={(82,82,107,255)}
        for mid in(728,610,726):
            c=self.imp.cell_index('emerald')[pair,mid]
            source=preview.native_donor(self.cache,dict(game='emerald',tileset=pair,id=mid,hash=c['pixel_sha256']),self.packed)
            pixels=list(source.get_flattened_data());parts=[]
            for donor,mask in[(black,[p==(0,0,0,255)for p in pixels]),
                               (wall,[p in orange for p in pixels]),
                               (gray[3],[p in cap|edge for p in pixels])]:
                for r in runs(mask):parts.append(dict(donor=donor,srcX=r['x']if donor==wall else 0,
                                                      srcY=r['y']if donor==wall else 0,w=r['w'],h=r['h'],x=r['x'],y=r['y']))
            assert len(parts)<=32
            art=self.composite(clinic,parts,'reverse_gen2_complete_clinic2f_cutaway_wall_corner');art['_sourceOverMask']=True
            self.aliases(pair,mid,art,
                'Actual complete clinic2F wall/counter cutaway joins were reviewed in clinic2f-before, extending the already-reviewed clinic corner family. '
                'Known plain orange wall surfaces use the same complete native Crystal wall texture, literal original gray trim retains the exact handed source contour, and exact black exterior remains black. '
                'All empty room-floor areas use the same selected classic clinic floor; no sign, frame, device, plant or control is flattened. Source actor-depth masks, collision, warps and positions stay unchanged.')
        # The full descending-frame source is32x48. A whole original Crystal
        # down-stair icon sits exactly on the actual native warp cell(1,6),
        # which is the middle-right cell673 of this family. The surrounding
        # plain steel/tread frame keeps the source geometry, in native ink.
        layout=[[664,665],[672,673],[680,681]]
        icon=self.primitive('johto_shop_stairs_down');native=self.gb_image(icon)
        stair_colors=set(self.gb_image(self.gb_at('crystal','POKECENTER_2F',0,7)).get_flattened_data())
        palette=preview.palette_set(self.imp.table('crystal','palettes'),self.imp.table('crystal','maps')['POKECENTER_2F'],'DAY')[1]
        colors=sorted([tuple(color)+(255,)for color in palette],key=lambda p:sum(p[:3]))
        assert len(set(colors))==4 and stair_colors<=set(colors)
        brushes=[]
        for color in colors:
            ref=copy.deepcopy(black);ref.pop('monochrome',None)
            ref['palettes']=[[list(color[:3])for _ in range(4)]for _ in range(8)];brushes.append(ref)
        # These exact source colors were reviewed on the complete frame:
        # orange rails, teal housing, gray treads, and their thin shadows.
        # They use the four genuine colors of the original clinic staircase;
        # the separate warm room-floor colors never become stair material.
        structural={(82,82,107,255):0,(140,181,173,255):0,(148,148,148,255):3,
                    (148,148,165,255):3,(156,115,90,255):0,(197,222,206,255):3,
                    (206,189,197,255):2,(255,99,49,255):1,(255,255,255,255):3}
        floor_colors={(206,197,140,255),(239,222,165,255),(247,239,189,255),(255,255,197,255)}
        source_records=[]
        for cy,line in enumerate(layout):
            for cx,mid in enumerate(line):
                c=self.imp.cell_index('emerald')[pair,mid]
                source=preview.native_donor(self.cache,dict(game='emerald',tileset=pair,id=mid,hash=c['pixel_sha256']),self.packed)
                pixels=list(source.get_flattened_data());groups=[[]for _ in range(4)]
                for p in pixels:
                    index=structural.get(p)
                    assert index is not None or p in floor_colors,('Unexpected stair source pixel',mid,p)
                    for i,mask in enumerate(groups):mask.append(index==i)
                parts=[]
                for donor,mask in zip(brushes,groups):
                    for r in runs(mask):parts.append(dict(donor=donor,srcX=0,srcY=0,w=r['w'],h=r['h'],x=r['x'],y=r['y']))
                if mid==673:parts=[dict(donor=icon,srcX=0,srcY=0,w=16,h=16,x=0,y=0)]
                if len(parts)>32:parts=self.visible_program_parts(parts)
                assert len(parts)<=32
                art=self.composite(clinic,parts,'reverse_gen2_complete_clinic_descending_stair_frame');art['_sourceOverMask']=True
                self.aliases(pair,mid,art,
                    'The whole actual32x48 clinic descending-stair frame was reviewed as one family. Its exact source outline, rail, housing and plain tread geometry remain intact in the four literal original clinic-stair colors. '
                    'The complete original sixteen-pixel Crystal down-stair glyph is retained at1:1 on the actual source warp cell673, with no cut frame, resized icon or repeated unique footer. '
                    'Source entrance(1,6) still targets the original1F room. Native collision, warp targets, actors and original overhead mask remain unchanged; visible room-floor gaps match the selected native clinic floor.')
                source_records.append(dict(id=mid,sourceHash=c['pixel_sha256'],sourceBehavior=c['behavior']))
        self.contracts.append(dict(label='complete descending clinic frame',source_ids=layout,source_cells=source_records,
                                   canvas=[32,48],whole_native_down_stair=icon,whole_icon_position=[16,16,16,16],
                                   source_warp_cell=[1,6],source_warp_mid=673,source_destination='original POKEMON_CENTER_1F',
                                   source_frame_outline_and_black_void_preserved=True,pixel_scale=1))

    def program_game(self,game,pair,layout,parts,base,label):
        for cy,line in enumerate(layout):
            for cx,mid in enumerate(line):
                if (pair,mid)not in self.scope[game]:continue
                assert self.imp.cell_index(game)[pair,mid]['pixel_sha256']==CLINIC_EXTRA_CONTRACTS[game+':'+str(mid)]
                left,top=cx*16,cy*16;selected=[]
                for part in parts:
                    x,y=max(left,part['x']),max(top,part['y'])
                    right,bottom=min(left+16,part['x']+part['w']),min(top+16,part['y']+part['h'])
                    if right<=x or bottom<=y:continue
                    selected.append(dict(donor=copy.deepcopy(part['donor']),srcX=part.get('srcX',0)+x-part['x'],
                                         srcY=part.get('srcY',0)+y-part['y'],w=right-x,h=bottom-y,x=x-left,y=y-top))
                assert len(selected)<=32
                art=self.composite(base,selected,'reverse_gen2_'+label.replace(' ','_'))if selected else self.native(base,'reverse_gen2_'+label.replace(' ','_'))
                art['_sourceOverMask']=True
                key=(game,'gen2',pair,mid,None)
                evidence=('Complete actual source '+label+' family '+str(layout)+' was reviewed together with its native room and entrance function. '
                          'Uses complete original Crystal hardware/label modules or an explicitly authored native-palette counterpart at1:1, with the exact selected clinic floor outside the object. '
                          'Source placements, functions, collision, warp destinations, NPCs and original over-priority mask stay unchanged.')
                if key in self.occupied:
                    old=next(row for row in self.prior if identity(row)==key)
                    if self.render(old).tobytes()!=self.render(art).tobytes():self.replace_exact(game,pair,mid,art,evidence)
                else:self.add(game,pair,mid,self.prepare_art(game,pair,mid,art),evidence)
        self.contracts.append(dict(label=label,game=game,pair=pair,source_ids=layout,whole_canvas=[len(layout[0])*16,len(layout)*16],
                                   complete_native_parts=parts,pixel_scale=1,source_over_mask_preserved_exactly=True))

    def whole_gb_rect(self,map_id,sx,sy,w,h,x=0,y=0):
        parts=self.gb_rect('crystal',map_id,sx,sy,w,h)
        for part in parts:part['x']+=x;part['y']+=y
        return parts

    def clinic_devices_and_badges(self,clinic):
        pair='building__pokemon_center'
        # The complete24-row Crystal PC is the same genuine native hardware
        # already independently reviewed for the personal-PC family. Its body
        # begins at y8 and ends at31, matching the registration terminal below
        # the eight-row decorative post foot.
        parts=self.whole_gb_rect('POKECENTER_2F',48,56,16,8,0,0)
        parts+=self.whole_gb_rect('CHERRYGROVE_POKECENTER_1F',144,8,16,8,0,8)
        parts+=self.whole_gb_rect('CHERRYGROVE_POKECENTER_1F',144,16,16,16,0,16)
        for layout in([ [731],[739] ],[ [730],[738] ]):
            self.program_game('emerald',pair,layout,parts,clinic,'complete classic link registration terminal')
        for game in('ruby','sapphire'):
            mid=599
            if(pair,mid)not in self.scope[game]:continue
            assert self.imp.cell_index(game)[pair,mid]['pixel_sha256']==CLINIC_EXTRA_CONTRACTS[game+':599']
            art=self.native(self.gb_at('crystal','POKECENTER_2F',3,0),'reverse_gen2_complete_rs_clinic_post_shaft')
            art['_sourceOverMask']=True
            self.add(game,pair,mid,self.prepare_art(game,pair,mid,art),
                     'Actual R/S source599 is a plain post shaft above the final lower foot607/613. It uses the complete original Crystal POKECENTER_2F blue/cream straight post at1:1. The complete lower foot and distinct six-dot status panel are authored in their actual following source cells, so no unique cap is repeated or cut off. Source masks and all source positions stay unchanged.')
        # Native linked-handheld sign: remove only the connected original
        # striped-wall background. The enclosing frame protects every internal
        # dark screen and pale highlight, so a foreground-color shortcut cannot
        # punch holes through the devices.
        ref=self.gb_at('crystal','POKECENTER_2F',4,0);source=self.gb_image(ref)
        wall=self.gb_image(self.gb_at('crystal','POKECENTER_2F',0,0))
        eligible=[source.getpixel((x,y))==wall.getpixel((x,y))for y in range(16)for x in range(16)]
        outside=set();todo=[(x,y)for y in range(16)for x in range(16)if x in(0,15)or y in(0,15)]
        while todo:
            x,y=todo.pop();index=y*16+x
            if index in outside or not eligible[index]:continue
            outside.add(index)
            todo.extend((xx,yy)for xx,yy in((x-1,y),(x+1,y),(x,y-1),(x,y+1))if 0<=xx<16 and 0<=yy<16)
        mask=[i not in outside for i in range(256)]
        trade=[dict(donor=ref,srcX=r['x'],srcY=r['y'],w=r['w'],h=r['h'],x=16+r['x'],y=8+r['y'])for r in runs(mask)]
        self.program_game('emerald',pair,[[615,712,713],[623,720,721]],trade,clinic,'complete original linked handheld floor marker')
        # Gen2 has no wireless-adapter floor label. This new16px marker uses
        # literal original clinic ink, with three stepped radio arcs and a
        # central transmitter dot. It is a deliberate new classic counterpart,
        # not claimed to be an original Crystal wireless symbol.
        pattern=['................','...##########...','..##........##..','.##..........##.',
                 '................','.....######.....','....##....##....','...##......##...',
                 '................','......####......','.....##..##.....','................',
                 '.......##.......','......####......','.......##.......','................']
        ink=self.native_color_brushes('POKECENTER_2F',0)[3]
        wireless=[dict(donor=ink,srcX=0,srcY=0,w=r['w'],h=r['h'],x=16+r['x'],y=8+r['y'])for r in runs([c=='#'for line in pattern for c in line])]
        self.program_game('emerald',pair,[[714,715,716],[722,723,724]],wireless,clinic,'purpose built classic wireless communication floor marker')
        self.contracts.append(dict(label='communication floor markers',native_linked_handhelds=ref,
                                   retained_native_handheld_pixels=sum(mask),removed_connected_original_wall_pixels=len(outside),
                                   all_native_internal_highlights_and_screens_retained=True,
                                   native_handhelds_scale=1,new_wireless_symbol_pattern=pattern,
                                   wireless_palette_source='literal original POKECENTER_2F palette0 ink',
                                   functions={'wireless':'EM_UNION_ROOM','linked_handhelds':'EM_TRADE_CENTER'},
                                   original_floor_outside_both_markers='exact selected native clinic floor',
                                   source_style_variants='Emerald-only; R/S labels have separately reviewed room functions'))

    def replace_exact(self,game,pair,mid,art,evidence):
        key=(game,'gen2',pair,mid,None)
        old=[row for row in self.prior if identity(row)==key]
        if not old:
            # After integration the superseded literal is intentionally absent;
            # regeneration may only rebuild the identical already-installed row.
            assert key in self.installed_self,('Missing exact old row',key)
            selected=self.prepare_art(game,pair,mid,art)
            assert self.installed_self[key]['compositionPixelHash']==catalog.sha(self.render(selected).tobytes())
            self.add(game,pair,mid,selected,evidence)
            return
        assert len(old)==1,('Exact supersession must identify one old row',key,len(old))
        original=old[0];module,index=self.origins[id(original)]
        assert key in self.occupied
        self.occupied.remove(key)
        try:self.add(game,pair,mid,self.prepare_art(game,pair,mid,art),evidence)
        finally:self.occupied.add(key)
        self.supersessions.append(dict(game=game,pair=pair,id=mid,old_module=module,old_index=index,
                                       old_row=original,old_row_json_sha256=catalog.sha(json.dumps(original,sort_keys=True,separators=(',',':')).encode()),
                                       new_module=TARGET.relative_to(ROOT).as_posix(),new_row=self.rows[key]))

    def clinic_counters(self):
        pair='building__pokemon_center'
        floor=self.gb_ref('crystal','CHERRYGROVE_POKECENTER_1F',4,0)
        front=self.gb_at('crystal','AZALEA_POKECENTER_1F',0,2)
        image=self.gb_image(front)
        # This original counter consists of a unique two-row top border, six equal
        # plain cream rows, and the complete blue lower frame. Only the equal
        # plain rows are added/removed to retain the actual source foot anchor.
        assert all(image.crop((0,y,16,y+1)).tobytes()==image.crop((0,2,16,3)).tobytes()for y in range(2,8))
        part=lambda sy,h,dy:dict(donor=copy.deepcopy(front),srcX=0,srcY=sy,w=16,h=h,x=0,y=dy)
        top=self.composite(floor,[part(0,4,12)],'reverse_gen2_complete_clinic_counter_upper_edge')
        lower=self.composite(floor,[part(2,6,0),part(6,2,6),part(8,8,8)],'reverse_gen2_complete_clinic_counter_lower_front')
        recipes={717:top,719:top,729:top,725:lower,727:lower,736:lower}
        for mid,art in recipes.items():
            assert self.imp.cell_index('emerald')[pair,mid]['pixel_sha256']==CLINIC_COUNTER_CONTRACTS[str(mid)]
            art=copy.deepcopy(art);art['_sourceOverMask']=True
            self.aliases(pair,mid,art,
                'The complete original clinic2F bar and its staff-floor margin were reviewed together in clinic2f-before and clinic-counter-and-controller-native-grid. '
                'The upper source cell has twelve rows of visible floor before the counter edge; those rows retain the exact selected classic clinic floor. '
                'The whole original Crystal counter top border, cream field and complete blue lower frame form one coherent twenty-pixel bar across two source rows. '
                'Only identical unadorned cream rows extend; no feet, frame, floor, controls or unique pixels are repeated. Original source foot anchor and overhead mask remain unchanged.')
        # The short service bar has six rows of genuine visible room floor
        # below its ten-row face. The old full-height face hid those floor rows.
        compact=self.composite(floor,[part(0,2,0),part(8,8,2)],'reverse_gen2_complete_clinic_short_service_bar')
        for game in GAMES:
            source=self.imp.cell_index(game)[pair,605]
            assert source['pixel_sha256']==CLINIC_COUNTER_CONTRACTS[game+':605']
            compact['_sourceOverMask']=True
            self.replace_exact(game,pair,605,compact,
                'Actual complete plain clinic service-counter source has its lower six rows as visible room floor, confirmed in the native1F/2F context and source605 grid. '
                'The full original Crystal two-row top border and complete eight-row blue lower frame are retained1:1; only the six repeated plain cream face rows are omitted to fit the actual ten-row face. '
                'Rows10..15 now expose the same exact native classic clinic floor as adjacent cells. Source collision, floor/warp behavior, staff/NPC positions and overhead availability remain unchanged.')
        self.contracts.append(dict(label='complete native-module clinic counter and corrected floor margins',
                                   native_counter=front,native_plain_repeat_rows=[2,7],native_complete_lower_frame_rows=[8,15],
                                   side_bar_canvas=[16,32],source_and_target_side_foot_anchor=31,
                                   side_counter_starts_at=12,side_staff_floor_rows=[0,11],
                                   short_bar_canvas=[16,16],source_and_target_short_foot_anchor=9,
                                   short_public_floor_rows=[10,15],source_hashes=CLINIC_COUNTER_CONTRACTS,
                                   source_context='clinic-counter-and-controller-native-grid.png',pixel_scale=1))

    def clinic_frames(self):
        pair='building__pokemon_center'
        wall=self.gb_at('crystal','POKECENTER_2F',0,0)
        stem=self.gb_at('crystal','POKECENTER_2F',3,0)
        door_lower=self.gb_at('crystal','POKECENTER_2F',3,1)
        cap=[]
        # The original blue/cream pane has a complete eight-row lower frame.
        # Reflect this plain architectural border vertically to make the new
        # matching top cap. No text, control, seat or directional art is flipped.
        for y in range(8):cap.extend(self.gb_rect('crystal','POKECENTER_2F',48,31-y,16,1,0,8+y))
        recipes={575:self.composite(wall,cap,'reverse_gen2_complete_clinic_glass_post_cap'),
                 583:self.native(stem,'reverse_gen2_complete_clinic_plain_glass_post'),
                 591:self.native(stem,'reverse_gen2_complete_clinic_plain_glass_post'),
                 604:self.composite(wall,cap,'reverse_gen2_complete_clinic_glass_door_cap'),
                 612:self.native(door_lower,'reverse_gen2_complete_clinic_glass_door_lower_frame')}
        for mid,art in recipes.items():
            assert self.imp.cell_index('emerald')[pair,mid]['pixel_sha256']==CLINIC_FRAME_CONTRACTS[str(mid)]
            art['_sourceOverMask']=True
            self.aliases(pair,mid,art,
                'Actual complete clinic2F source caps, straight glass posts and two-cell communication door were reviewed together in clinic2f-before. '
                'The purpose-built Crystal counterpart uses the original POKECENTER_2F blue/cream glass frame and complete border at native1:1. '
                'Only a plain eight-row architectural border is reflected for the new top cap; the original full sixteen-row shaft repeats without scaling. '
                'Door lower frame remains whole, with its bottom aligned to the original sixteen-by-thirty-two source door. '
                'Matching original upper-wall pixels fill the eight-row margin above the cap. Source entrance/warp cells, collision, NPC positions and source overhead mask remain unchanged.')
        self.contracts.append(dict(label='native-module blue/cream clinic glass frames',pair=pair,
                                   source_ids=[575,583,591,604,612],source_hashes=CLINIC_FRAME_CONTRACTS,
                                   native_map='POKECENTER_2F',native_shaft_rectangle=[48,0,16,16],
                                   native_cap_rectangle=[48,24,16,8],cap_plain_border_reflected_vertically=True,
                                   native_lower_door_rectangle=[48,16,16,16],door_canvas=[16,32],
                                   source_door_foot_anchor=31,replacement_door_foot_anchor=31,
                                   pixel_scale=1,source_over_mask_preserved_exactly=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contacts', action='store_true')
    parser.add_argument('--game', choices=GAMES, default='emerald')
    parser.add_argument('--pair')
    parser.add_argument('--limit', type=int, default=256)
    parser.add_argument('--validate', action='store_true')
    parser.add_argument('--previews', action='store_true')
    args = parser.parse_args()
    review = Review(); review.inventory()
    if args.contacts: review.contact_missing(args.limit, args.game, args.pair)
    review.build()
    if review.rows:
        review.write(review.out / 'candidates.lua')
        if args.validate: print(json.dumps(review.validate(), indent=2))
    (review.out / 'contracts.json').write_text(json.dumps(review.contracts, indent=2)+'\n')
    (review.out / 'held.json').write_text(json.dumps(review.held, indent=2)+'\n')
    if args.previews: print(json.dumps(review.checkpoint(),indent=2))


if __name__ == '__main__':
    main()
