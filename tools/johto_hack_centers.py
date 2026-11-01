"""Retain FireGold's whole native clinic, anchored to the original GSC door.

Only the expanded-center core mapping is activated here. Matching roof/left
decoration rows are staged for merging with the existing decoration catalogs.
Compact-center artwork is retained byte-for-byte in buildingCompact.
"""
import argparse
import copy
import json
import os
from collections import defaultdict, deque
from pathlib import Path
from types import SimpleNamespace

from PIL import Image
import catalog
import preview
import gen2_extended_review as e
from center_mart_overhang_review import write_rows

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / '.work/tileshift-firegold/centers'
SOURCE_URL = 'https://www.pokecommunity.com/threads/pok%C3%A9mon-fire-gold-1-4.473130/'
CREDIT = 'FireGold 1.4 by Tzx211; artwork extracted from the user-supplied ROM'
SOURCE_RECT = (384, 352, 464, 432)
SOURCE_MAP = 'g03_m001'
EVIDENCE = ('Complete native80x80 FireGold clinic retained at1:1 pixel scale, '
            'including the roof, emblem, windows and door frame. Its source door '
            'column2 aligns with original GSC entrance column1 by extending one '
            'decorative16px column to the left. A single upper decorative row '
            'retains the full native height. Only connected source ground pixels '
            'outside the building silhouette are omitted; native overhead '
            'pixels are protected. Original source maps, collision and entrances '
            'are unchanged; compact artwork remains selectable.')


def extract(exports):
    info = json.loads((exports / 'catalog.json').read_text())
    assert info['rom_sha256'] == 'c65f698ffb844b99836a36dc0752e8b57ebd45be53be364cb3cfe52aa0cc74ce'
    native = Image.open(exports / 'maps' / (SOURCE_MAP + '-flat.png')).convert('RGBA')
    overhead = Image.open(exports / 'maps' / (SOURCE_MAP + '-over.png')).convert('RGBA').crop(SOURCE_RECT)
    original = native.crop(SOURCE_RECT)
    sprite = original.copy()
    ground_rectangles = ((384, 336, 400, 352), (368, 384, 384, 400))
    colors = set()
    for rect in ground_rectangles:
        colors.update(native.crop(rect).get_flattened_data())
    outside, queue = set(), deque()
    for y in range(80):
        for x in range(80):
            if (x in (0, 79) or y in (0, 79)) and sprite.getpixel((x, y)) in colors:
                outside.add((x, y)); queue.append((x, y))
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            q = x + dx, y + dy
            if (0 <= q[0] < 80 and 0 <= q[1] < 80 and q not in outside
                    and sprite.getpixel(q) in colors):
                outside.add(q); queue.append(q)
    for q in outside:
        assert overhead.getpixel(q)[3] == 0, 'Native roof/emblem pixels must remain intact'
        sprite.putpixel(q, (0, 0, 0, 0))
    assert len(outside) == 862
    for y in range(80):
        for x in range(80):
            if (x, y) not in outside:
                assert sprite.getpixel((x, y)) == original.getpixel((x, y))
    target = ROOT / 'assets/third_party/johto-hacks/centers'
    target.mkdir(parents=True, exist_ok=True)
    refs, hashes = {}, {}
    for y in range(5):
        for x in range(5):
            name = f'firegold-center-{x}-{y}.png'
            path = target / name
            sprite.crop((x * 16, y * 16, x * 16 + 16, y * 16 + 16)).save(path)
            hashes[name] = catalog.sha(path.read_bytes())
            refs[x, y] = dict(kind='third_party', asset=path.relative_to(ROOT).as_posix(),
                              assetFileHash=hashes[name], credit=CREDIT, sourceUrl=SOURCE_URL)
    provenance = dict(origin=CREDIT, sourceUrl=SOURCE_URL, sourceRom=info['rom_name'],
                      rom_sha256=info['rom_sha256'], source_map=SOURCE_MAP,
                      source_rect=list(SOURCE_RECT), ground_sample_rectangles=ground_rectangles,
                      removed_connected_exterior_pixels=len(outside),
                      retained_native_pixels=6400-len(outside), source_overhead_pixels_unchanged=True,
                      integer_native_scale=1, native_entrance=dict(x=26, y=26),
                      alignment='Native column2 -> original GSC column1; left16px decorative extension',
                      files=hashes)
    (target / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    sprite.save(OUT / 'native-center-isolated.png')
    sprite.resize((400, 400), Image.Resampling.NEAREST).save(OUT / 'native-center-preview.png')
    return refs, provenance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate', action='store_true')
    parser.add_argument('--exports', type=Path, default=ROOT.parent / '.work/tileshift-firegold/firegold')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    refs, provenance = extract(args.exports)
    cache = Path(os.environ['APPDATA']) / 'pokemon-love2d'
    path = ROOT / 'mappings/building_overhangs.lua'
    rows = preview.read_reviewed(path)
    centers = defaultdict(list)
    for row in rows:
        if row['game'] in e.GAMES and row['role'] == 'larger_center':
            centers[row['game'], row['map']].append(row)
    old_roofs = preview.read_reviewed(ROOT / 'lib/center_mart_roofs.lua')
    roofs, sides, changed, packed, instances = [], [], [], {}, []
    for (game, name), group in sorted(centers.items()):
        assert len(group) == 16
        ox = min(row['x'] for row in group); oy = min(row['y'] for row in group)
        data = e.source(cache, game); m = data['maps'][name]
        warp = next(w for w in m['warps'] if w['x'] == ox+1 and w['y'] == oy+3)
        for row in group:
            dx, dy = row['x']-ox, row['y']-oy+1
            compact = copy.deepcopy(row['buildingCompact'])
            for key in ('donor', 'parts', 'asset', 'assetFileHash', 'artOverlay', 'animation', 'animated', 'assetFrames'):
                row.pop(key, None)
            row.update(copy.deepcopy(refs[dx+1, dy]), evidence=EVIDENCE)
            assert row['buildingCompact'] == compact
            row['compositionPixelHash'] = catalog.sha(preview.replacement_image(cache, row, packed, ROOT).tobytes())
            changed.append(row)
        for row in old_roofs:
            if row['game'] == game and row['map'] == name and row['role'] == 'larger_center':
                roof = copy.deepcopy(row)
                for key in ('parts', 'donor', 'base', 'artOverlay', 'compositionPixelHash'):
                    roof.pop(key, None)
                roof.update(copy.deepcopy(refs[row['x']-ox+1, 0]), evidence=EVIDENCE)
                roofs.append(roof)
        for y in range(max(0, oy-1), oy+4):
            x = ox-1; sx = max(0, x)
            bid = m['blocks'][y//2*m['width']+sx//2]; q = y%2*2+sx%2
            c = e.cell_info(cache, game, data, m['tileset'], bid, q)
            side = dict(game=game, style='gen3', map=name, tileset=m['tileset'], id=bid, quadrant=q,
                        x=x, y=y, sourceX=sx, side='left', buildingX=ox, buildingY=max(0, oy-1),
                        buildingW=4, buildingH=oy+4-max(0, oy-1), sourceHash=c['sourceHash'],
                        sourceFiles=data['fingerprints'][m['tileset']], sourceCollision=c['collision'],
                        sourcePriority=[bool(v.get('priority')) for v in c['attributes']],
                        sourcePalettes=[v.get('palette', 1) for v in c['attributes']], role='larger_center',
                        status='reviewed', evidence=EVIDENCE)
            side.update(copy.deepcopy(refs[0, y-oy+1])); sides.append(side)
        instances.append(dict(game=game, map=name, core=[ox, oy, 4, 4],
                              draw=[ox-1, oy-1, 5, 5], door=[warp['x'], warp['y']],
                              dest_map=warp['destMap']))
    assert len(changed) == 960 and len(instances) == 60
    proof = e.validate_batch(changed+roofs, SimpleNamespace(cache=cache, engine=ROOT.parent / '.tools/engine-0395', output=OUT), ROOT)
    (OUT / 'roof-replacements.json').write_text(json.dumps(roofs, indent=2))
    (OUT / 'left-side-additions.json').write_text(json.dumps(sides, indent=2))
    (OUT / 'core-candidates.json').write_text(json.dumps(changed, indent=2))
    (OUT / 'proof.json').write_text(json.dumps(dict(validation=proof, instances=instances, provenance=provenance), indent=2))
    if args.activate:
        write_rows(path, rows)
    print(json.dumps(dict(core_rows=len(changed), roofs=len(roofs), sides=len(sides), instances=len(instances), validation=proof, activated=args.activate)))


if __name__ == '__main__':
    main()
