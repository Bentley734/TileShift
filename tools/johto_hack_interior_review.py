"""Use reviewed, native-scale objects from the user-supplied Johto ROM hacks.

The extraction atlas remains private. Only explicitly chosen16px PNG pieces,
ROM/atlas fingerprints and their checked origin are packaged. Source Gen2
geometry, collision, interactions and room floor references remain untouched.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
from collections import deque

from PIL import Image
import catalog
import preview
import gen2_extended_review as e
from center_mart_overhang_review import write_rows

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT.parent / '.work/tileshift-firegold'
FOLDER = ROOT / 'assets/third_party/johto-hacks/interiors'
OUT = PRIVATE / 'interior-review'
FIREGOLD_URL = 'https://www.pokecommunity.com/threads/pok%C3%A9mon-fire-gold-1-4.473130/'
CRYSTALDUST_URL = 'https://github.com/Sierraffinity/CrystalDust'
LIQUIDCRYSTAL_URL = 'https://www.pokecommunity.com/threads/pok%C3%A9mon-liquid-crystal-3-3-xxxxx-live-beta.242023/'
GSC_URL = 'https://github.com/pret/pokecrystal'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract(source, pair, mid, layer, filename):
    """Take one exact native metatile layer without scaling or pixel synthesis."""
    directory = PRIVATE / source
    data = json.loads((directory / 'catalog.json').read_text())
    path = directory / 'pairs' / pair / (layer + '.png')
    atlas = Image.open(path).convert('RGBA')
    x, y = mid % 16 * 16, mid // 16 * 16
    image = atlas.crop((x, y, x + 16, y + 16))
    assert image.size == (16, 16) and image.getbbox()
    target = FOLDER / filename
    image.save(target)
    return {'asset': target.relative_to(ROOT).as_posix(),
            'assetFileHash': digest(target), 'source': source,
            'source_rom_sha256': data['rom_sha256'], 'source_rom_name': data['rom_name'],
            'tileset_pair': pair, 'metatile': mid, 'layer': layer,
            'source_atlas_sha256': digest(path), 'source_rect': [x, y, 16, 16],
            'rgba_sha256': hashlib.sha256(image.tobytes()).hexdigest(), 'scale': 1}


def modules(source, pair, filename, pieces):
    """Rearrange exact native8px/16px repeating modules; never resize art."""
    directory = PRIVATE / source
    data = json.loads((directory / 'catalog.json').read_text())
    image = Image.new('RGBA', (16, 16))
    proof = []
    for mid, layer, rect, destination in pieces:
        path = directory / 'pairs' / pair / (layer + '.png')
        atlas = Image.open(path).convert('RGBA')
        x, y, w, h = rect
        sx, sy = mid % 16 * 16 + x, mid // 16 * 16 + y
        image.paste(atlas.crop((sx, sy, sx + w, sy + h)), destination)
        proof.append({'metatile': mid, 'layer': layer, 'rect': rect, 'destination': destination,
                      'source_atlas_sha256': digest(path)})
    target = FOLDER / filename
    image.save(target)
    return {'asset': target.relative_to(ROOT).as_posix(), 'assetFileHash': digest(target),
            'source': source, 'source_rom_sha256': data['rom_sha256'], 'source_rom_name': data['rom_name'],
            'tileset_pair': pair, 'native_modules': proof, 'scale': 1,
            'rgba_sha256': hashlib.sha256(image.tobytes()).hexdigest()}


def small_object(source, pair, filename, grid=None, map_rect=None, floor_ids=()):
    """Keep a complete small object, uniformly reducing by an integer if needed."""
    directory = PRIVATE / source
    data = json.loads((directory / 'catalog.json').read_text())
    references = []
    if grid is not None:
        image = Image.new('RGBA', (len(grid[0]) * 16, len(grid) * 16))
        for y, line in enumerate(grid):
            for x, (mid, layer) in enumerate(line):
                path = directory / 'pairs' / pair / (layer + '.png')
                atlas = Image.open(path).convert('RGBA')
                sx, sy = mid % 16 * 16, mid // 16 * 16
                image.paste(atlas.crop((sx, sy, sx + 16, sy + 16)), (x * 16, y * 16))
                references.append({'metatile': mid, 'layer': layer, 'source_atlas_sha256': digest(path)})
    else:
        map_id, rect = map_rect[:2]
        mode = map_rect[2] if len(map_rect) > 2 else 'flat'
        path = directory / 'maps' / (map_id + '-' + mode + '.png')
        image = Image.open(path).convert('RGBA').crop(tuple(rect))
        references.append({'map': map_id, 'source_rect': rect, 'layer': mode, 'map_rgba_sha256': digest(path)})
    # Omit only outside-connected native room-floor pixels. The staircase's
    # closed rail/well, steps, landing and entry mat are retained in full.
    omitted = 0
    if floor_ids:
        atlas = Image.open(directory / 'pairs' / pair / 'flat.png').convert('RGBA')
        colors = set()
        for mid in floor_ids:
            x, y = mid % 16 * 16, mid // 16 * 16
            colors.update(atlas.crop((x, y, x + 16, y + 16)).get_flattened_data())
        w, h = image.size
        outside, queue = set(), deque()
        for y in range(h):
            for x in range(w):
                if (x in (0, w - 1) or y in (0, h - 1)) and image.getpixel((x, y)) in colors:
                    outside.add((x, y)); queue.append((x, y))
        while queue:
            x, y = queue.popleft()
            for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if 0 <= p[0] < w and 0 <= p[1] < h and p not in outside and image.getpixel(p) in colors:
                    outside.add(p); queue.append(p)
        for p in outside:
            image.putpixel(p, (0, 0, 0, 0))
        omitted = len(outside)
    native_size = image.size
    factor = (max(native_size) + 15) // 16
    canvas = Image.new('RGBA', (16 * factor, 16 * factor))
    placement = ((canvas.width-image.width)//2, canvas.height-image.height)
    canvas.paste(image, placement)
    final = canvas.resize((16, 16), Image.Resampling.NEAREST)
    target = FOLDER / filename
    final.save(target)
    return {'asset': target.relative_to(ROOT).as_posix(), 'assetFileHash': digest(target),
        'source': source, 'source_rom_sha256': data['rom_sha256'], 'source_rom_name': data['rom_name'],
        'tileset_pair': pair, 'native_parts': references, 'native_dimensions': native_size,
        'integer_reduction': factor, 'transparent_padding_placement': placement,
        'outside_native_floor_pixels_omitted': omitted, 'whole_object_retained': True,
        'rgba_sha256': hashlib.sha256(final.tobytes()).hexdigest()}


def original_gsc_fallback(row, cache, packed):
    """Preserve original radio/beacon geometry where the hacks lack counterparts.

    This is explicitly original cartridge art with a checked palette change,
    not claimed to be hack artwork or a newly generated replacement design.
    """
    cache_key=('original_gsc_fallback',row['sourceHash'])
    if cache_key in packed:return copy.deepcopy(packed[cache_key])
    ref = {k: row[k] for k in ('game','tileset','id','quadrant')}
    ref.update(hash=row['sourceHash'],map=row['map'])
    colored = preview.native_donor(cache, ref, packed)
    tilesets = catalog.read_lua(cache / row['game'] / 'data/generated/tilesets.lua')
    ts = tilesets[row['tileset']]
    sheet = Image.open(cache / row['game'] / ts['image']).convert('RGBA')
    block = catalog.lua_array(catalog.dict_at(ts['blocks'], row['id'] + 1))
    neutral = preview.native_cell(sheet,ts,block,row['quadrant'])
    assert catalog.sha(neutral.tobytes()) == row['sourceHash']
    levels = sorted({p[0] for p in sheet.get_flattened_data()},reverse=True)
    assert len(levels) == 4
    metal = [(248,248,232),(176,184,192),(88,104,120),(40,48,64)]
    wood = [(240,224,168),(192,168,96),(128,104,64),(56,48,40)]
    blue = [(232,248,248),(128,208,232),(64,128,176),(40,56,80)]
    gold = [(248,232,160),(224,184,72),(160,112,40),(64,48,40)]
    image = Image.new('RGBA',(16,16));beacon='beacon' in row['role']
    # The traditional/player-room upper radio cells are actual ordinary room
    # floor (all four original8px tiles17 or2). They contain no radio pixels.
    empty_head = not beacon and 'head' in row['role']
    house_head = row['role']=='johto_house_radio_0'
    bg = {colored.getpixel((x,y)) for y in range(8) for x in range(16)} if house_head else set()
    for y in range(16):
        for x in range(16):
            c = colored.getpixel((x,y));keep=not empty_head
            # Beneath the complete beacon frame/base is a central original
            # wooden support. The checker pattern beside it is donor room
            # floor, so retain the support and expose the host floor outside.
            if beacon and row['role'].endswith('_0_2') and y>=11 and x<8:keep=False
            if beacon and row['role'].endswith('_1_2') and y>=11 and x>=8:keep=False
            if not beacon:
                if house_head:keep=y>=8 and c not in bg
                elif row['role']=='johto_domestic_radio':
                    keep=max(c[:3])-min(c[:3])<=48
            if not keep:continue
            shade=levels.index(neutral.getpixel((x,y))[0]);palette=metal
            if beacon:
                palette=gold if c[0]>96 and c[2]<100 else blue if max(c[:3])-min(c[:3])>48 else metal
            elif row['role']=='johto_house_radio_1' and y>=8:palette=wood
            image.putpixel((x,y),(*palette[shade],255))
    path=FOLDER/('original-gsc-'+row['sourceHash'][:16]+'.png');image.save(path)
    result={'asset':path.relative_to(ROOT).as_posix(),'assetFileHash':digest(path),'source':'original_gsc',
        'source_game':row['game'],'source_map':row['map'],'source_tileset':row['tileset'],'source_block':row['id'],
        'source_quadrant':row['quadrant'],'source_pixel_sha256':row['sourceHash'],'source_files':row['sourceFiles'],
        'fallback_reason':'No equivalent radio/beacon artwork in supplied hacks; user approved original cartridge geometry in Gen3 colors.',
        'original_geometry_retained':True,'room_base_preserved':True,'empty_radio_head_floor_omitted':empty_head,
        'rgba_sha256':hashlib.sha256(image.tobytes()).hexdigest(),'scale':1}
    packed[cache_key]=copy.deepcopy(result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--activate', action='store_true')
    args = p.parse_args()
    FOLDER.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    cache = Path(os.environ['APPDATA']) / 'pokemon-love2d'
    # Native16px complete desktop CRT, including bezel and stand. Its separate
    # mid layer has transparent surroundings and retains the selected room floor.
    recipes = {'assets/original/interior-computer/computer.png':
        extract('firegold', '082d4bb4_082d4c8c', 117, 'mid', 'firegold-lab-computer.png')}
    tower = '083df884_083dfa94'
    prefix = 'assets/original/interior-tower-modules/'
    for original, mid, layer in [('wall', 529, 'top'), ('lattice-10-11-26-27', 550, 'flat'),
            ('lattice-11-11-27-27', 551, 'flat'), ('lattice-26-27-26-27', 566, 'flat'),
            ('lattice-27-27-27-27', 567, 'flat')]:
        recipes[prefix + original + '.png'] = extract('crystaldust', tower, mid, layer, 'crystaldust-' + original + '.png')
    recipes[prefix + 'vertical-wall.png'] = modules('crystaldust', tower, 'crystaldust-vertical-wall.png',
        [(529, 'top', [0, 0, 8, 16], (4, 0))])
    recipes[prefix + 'broken-wall.png'] = modules('crystaldust', tower, 'crystaldust-broken-wall.png',
        [(529, 'top', [0, 0, 16, 8], (0, 0)), (529, 'top', [0, 8, 8, 8], (0, 8))])
    recipes[prefix + 'fringe.png'] = modules('crystaldust', tower, 'crystaldust-fringe.png',
        [(576, 'flat', [0, 0, 16, 8], (0, 0)), (512, 'flat', [0, 0, 16, 8], (0, 8))])
    recipes[prefix + 'lattice-3-3-11-11.png'] = modules('crystaldust', tower, 'crystaldust-lattice-floor-edge.png',
        [(551, 'flat', [0, 0, 16, 8], (0, 8))])
    for raw in ((27,70,27,86),(27,11,27,27),(71,26,87,26),(11,27,27,27),(26,27,27,27)):
        pieces = []
        for q, code in enumerate(raw):
            x, y = q % 2 * 8, q // 2 * 8
            if code in (10,11,26,27):
                mid, sx, sy = {10:(550,0,0),11:(551,8,0),26:(566,0,8),27:(567,8,8)}[code]
                pieces.append((mid, 'flat', [sx,sy,8,8], (x,y)))
            elif code in (86,87):
                pieces.append((529,'top',[2,8,3,8],(x+(5 if code==86 else 0),y)))
        stem = 'lattice-' + '-'.join(map(str,raw))
        recipes[prefix + stem + '.png'] = modules('crystaldust',tower,'crystaldust-'+stem+'.png',pieces)
    painting = small_object('crystaldust',tower,'crystaldust-bellsprout-picture.png',
        grid=[[(520,'top')],[(528,'top')]])
    portrait = Image.open(ROOT / painting['asset']).convert('RGBA')
    native_posts = Image.open(PRIVATE / 'crystaldust/pairs' / tower / 'top.png')
    post = native_posts.crop((529%16*16,529//16*16,529%16*16+8,529//16*16+16))
    for side in ('left','right'):
        image = Image.new('RGBA',(16,16))
        image.paste(post,(0 if side=='left' else 8,0))
        image.paste(portrait.crop((0 if side=='left'else 8,0,8 if side=='left'else 16,16)),(8 if side=='left'else 0,0))
        path = FOLDER / ('crystaldust-painting-'+side+'.png');image.save(path)
        recipes[prefix+'painting-'+side+'.png'] = dict(painting,asset=path.relative_to(ROOT).as_posix(),
            assetFileHash=digest(path),placement='Complete reduced native picture spans two source cells, native log posts frame both sides.')
    # The native swaying support retains its entire32x48 silhouette, including
    # the original upper black core. All six native16px layers stay unscaled.
    for y in range(3):
        for x in range(2):
            old = f'assets/original/interior-pillar/cell-{x}-{y}.png'
            recipes[old] = extract('crystaldust', tower, 517 + x + y * 8, 'top', f'crystaldust-support-{x}-{y}.png')
    outdoor = '083df704_083df764'
    for old in ('roof-west', 'roof-east', 'ridge'):
        recipes[prefix + old + '.png'] = extract('crystaldust', outdoor, 683, 'flat', f'crystaldust-{old}.png')
    recipes[prefix + 'ridge-end.png'] = modules('crystaldust', outdoor, 'crystaldust-ridge-end.png',
        [(682, 'flat', [8, 0, 8, 16], (0, 0)), (683, 'flat', [0, 0, 8, 16], (8, 0))])
    house = '082d4bb4_082d4c74'
    recipes['assets/original/interior-stairs/up.png'] = small_object('firegold', house,
        'firegold-stairs-up.png', map_rect=('g44_m001', [144, 16, 192, 48]), floor_ids=(1,))
    recipes['assets/original/interior-stairs/down.png'] = small_object('firegold', house,
        'firegold-stairs-down.png', map_rect=('g44_m000', [128, 24, 176, 56]), floor_ids=(1,))
    # Complete native Flower Shop flower box, including both blooms, the
    # container and the full side leaves; adjacent trees are on the over layer.
    # Only its outside-connected native color-zero backdrop is omitted.
    flowerbox = small_object('firegold','082d4bb4_082d4f74','firegold-flowerbox.png',
        map_rect=('g44_m064',[88,112,136,128],'mid'),floor_ids=(0,647))
    recipes['assets/original/interior-flowerpot/flowerpot.png'] = flowerbox
    recipes['assets/original/interior-planter/planter.png'] = flowerbox
    tower_up = small_object('crystaldust', tower, 'crystaldust-ladder-up.png',
        grid=[[(673, 'top')], [(535, 'top')]])
    tower_down = extract('crystaldust', tower, 519, 'top', 'crystaldust-ladder-down.png')
    recipes['assets/original/azalea-lawn/pink-floor.png'] = extract('firegold',
        '082d4bb4_082d4e84', 846, 'flat', 'firegold-pink-floor.png')
    flora_proof = json.loads((ROOT / 'assets/third_party/johto-hacks/flora/provenance.json').read_text())
    native_tree = next(item for item in flora_proof['entries'] if item['asset'] == 'liquidcrystal-round-tree-whole32.png')
    for q in range(4):
        path = ROOT / 'assets/third_party/johto-hacks/flora' / f'default-tree-q{q}.png'
        recipes[f'assets/original/azalea-lawn/oak-shadow-q{q}.png'] = dict(native_tree,
            asset=path.relative_to(ROOT).as_posix(), assetFileHash=digest(path), source='liquidcrystal',
            source_provenance='assets/third_party/johto-hacks/flora/provenance.json')
    files = {}
    changes, checked, packed, fallbacks = [], [], {}, {}
    for path in sorted((ROOT / 'mappings').glob('*.lua')):
        rows = preview.read_reviewed(path)
        for index, row in enumerate(rows):
            if row.get('game') not in ('gold', 'silver', 'crystal'):
                continue
            recipe = recipes.get(row.get('asset'))
            if row.get('asset','').startswith(('assets/original/interior-radio/','assets/original/interior-beacon/')):
                recipe=original_gsc_fallback(row,cache,packed)
                fallbacks[recipe['asset']]=recipe
            overlay_recipe = recipes.get(row.get('artOverlay', {}).get('asset'))
            if recipe is None and overlay_recipe is None:
                continue
            if recipe and row['role'] == 'johto_tower_stairs_up':
                recipe = tower_up
            if recipe and row['role'] == 'johto_tower_stairs_down':
                recipe = tower_down
            old = row.get('asset') or row['artOverlay']['asset']
            row = copy.deepcopy(row)
            if recipe:
                row.update(kind='third_party', asset=recipe['asset'], assetFileHash=recipe['assetFileHash'])
            if overlay_recipe:
                row['artOverlay'].update(kind='third_party', asset=overlay_recipe['asset'], hash=overlay_recipe['assetFileHash'])
            selected = recipe or overlay_recipe
            row.update(credit={'firegold':'Pokemon Fire Gold project; native FireRed room-object artwork.',
                'crystaldust':'Pokemon CrystalDust / Sierraffinity and DoMoreAwesome Games; native Johto room artwork.',
                'liquidcrystal':'Pokemon Liquid Crystal / Linkandzelda and Synyster Zeikku; native Johto artwork.',
                'original_gsc':'Original Pokemon Gold/Silver/Crystal cartridge pixels, preserved in Gen3 colors; no hack counterpart.'}[selected['source']],
                sourceUrl={'firegold':FIREGOLD_URL,'crystaldust':CRYSTALDUST_URL,'liquidcrystal':LIQUIDCRYSTAL_URL,'original_gsc':GSC_URL}[selected['source']])
            row['evidence'] += (' Replaced generated artwork with original cartridge geometry in Gen3 colors; '
                'the supplied hacks lack an equivalent radio/beacon. Original radio-header floor pixels are omitted, '
                'and the checked room base, source interactions and collision remain unchanged.' if selected['source']=='original_gsc'
                else ' Replaced generated artwork with checked native Johto-hack pixels. '
                'Complete small objects and repeating structural modules use native scale or uniform integer reductions. '
                'The original room base, source interactions, holes and collision remain unchanged.')
            row['compositionPixelHash'] = catalog.sha(preview.replacement_image(cache, row, packed, ROOT).tobytes())
            rows[index] = row
            changes.append({'file': path.name, 'row': index, 'game': row['game'], 'map': row.get('map'),
                            'role': row['role'], 'old_asset': old, 'asset': selected['asset']})
            checked.append(row)
        if any(c['file'] == path.name for c in changes):
            files[path] = rows
    proof = e.validate_batch(checked, SimpleNamespace(cache=cache, engine=ROOT.parent / '.tools/engine-0395', output=OUT), ROOT) if checked else {'rows_accepted':0,'rejected':0}
    proof.update(changed_rows=len(checked), replaced_assets=len(recipes), changes=changes)
    (OUT / 'proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    provenance = {'origin': 'Exact selected native16px room-object layers extracted from user-supplied Johto ROM hacks.',
        'roms_not_bundled': True, 'source_urls': [FIREGOLD_URL,CRYSTALDUST_URL,LIQUIDCRYSTAL_URL],
        'pieces': list(recipes.values()) + [tower_up,tower_down] + list(fallbacks.values()),
        'files': {path.name:digest(path) for path in FOLDER.glob('*.png')}}
    (FOLDER / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    all_rows = [r for path in (ROOT / 'mappings').glob('*.lua') for r in files.get(path, preview.read_reviewed(path))]
    for name in ('RADIO_TOWER_2F', 'GOLDENROD_DEPT_STORE_1F', 'GOLDENROD_MAGNET_TRAIN_STATION',
                 'SPROUT_TOWER_1F', 'SPROUT_TOWER_2F', 'TIN_TOWER_ROOF', 'BURNED_TOWER_1F', 'AZALEA_GYM',
                 'OLIVINE_LIGHTHOUSE_6F','BILLS_FAMILYS_HOUSE','PLAYERS_HOUSE_2F','ECRUTEAK_ITEMFINDER_HOUSE'):
        preview.map_preview(cache, OUT, 'crystal', name, name, all_rows, packed, 3, ROOT)
    if args.activate:
        for path, rows in files.items():
            write_rows(path, rows)
    print(json.dumps({k: v for k, v in proof.items() if k != 'changes'}, indent=2))


if __name__ == '__main__':
    main()
