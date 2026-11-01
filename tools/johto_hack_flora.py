"""Extract native hack foliage; retain whole trees with exact integer reduction.

Small shrubs/flowers/grass remain16px. Whole32x48 trees are reduced uniformly
by exactly2 and centred in their existing32px footprint, never clipped.
"""
import argparse
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace

from PIL import Image, ImageDraw
import catalog
import preview
import gen2_extended_review as e
from newbark_building_review import lua
from center_mart_overhang_review import write_rows

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent / '.work/tileshift-firegold'
DEST = ROOT / 'assets/third_party/johto-hacks/flora'
SOURCE = {
    'firegold': ('082d4a94_082d4aac', 1, 'FireGold 1.4 by Tzx211',
                 'https://www.pokecommunity.com/threads/pok%C3%A9mon-fire-gold-1-4.473130/'),
    'crystaldust': ('083df704_083df74c', 1, 'CrystalDust by Sierraffinity and its contributors',
                    'https://github.com/Sierraffinity/CrystalDust'),
    'liquidcrystal': ('082d4a94_082d4b9c', 9, 'Liquid Crystal by Linkandzelda and Synyster Zeikku',
                     'https://www.pokecommunity.com/threads/pok%C3%A9mon-liquid-crystal-3-3-xxxxx-live-beta.242023/'),
}
ENTRIES = (
    ('trees', 'crystaldust', 199, 'conifer'),
    ('trees', 'firegold', 5, 'round-shrub'),
    ('trees', 'liquidcrystal', 5, 'berry-shrub'),
    ('flowers', 'firegold', 4, 'red-flowers'),
    ('flowers', 'crystaldust', 36, 'yellow-flowers'),
    ('flowers', 'liquidcrystal', 4, 'red-flowers'),
    ('flowers', 'liquidcrystal', 1, 'wildflowers'),
    ('grass', 'firegold', 13, 'grass'),
    ('grass', 'crystaldust', 21, 'long-grass'),
    ('grass', 'liquidcrystal', 13, 'grass'),
)
BIG = (
    ('liquidcrystal', 'g03_m017', (352, 80, 384, 128), 'round-tree'),
    ('firegold', 'g03_m001', (384, 32, 416, 80), 'conifer'),
    ('crystaldust', 'g00_m000', (96, 176, 128, 224), 'conifer'),
)


def cell(sheet, mid):
    x, y = mid % 16 * 16, mid // 16 * 16
    return sheet.crop((x, y, x+16, y+16))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--activate', action='store_true')
    a = p.parse_args()
    out = BASE / 'flora'; out.mkdir(exist_ok=True)
    DEST.mkdir(parents=True, exist_ok=True)
    entries = dict(trees=[], big_trees=[], flowers=[], grass=[])
    records, files, rgba = [], {}, {}
    sheets, infos = {}, {}
    for hack, (pair, ground, credit, url) in SOURCE.items():
        folder = BASE / hack
        infos[hack] = json.loads((folder / 'catalog.json').read_text())
        sheets[hack] = {name: Image.open(folder / 'pairs' / pair / (name+'.png')).convert('RGBA')
                        for name in ('flat', 'mid', 'over')}

    def save(sprite, hack, name, category, source):
        stem = hack+'-'+name
        path = DEST / (stem+'.png'); sprite.save(path)
        digest = catalog.sha(path.read_bytes()); files[path.name] = digest; rgba[stem] = sprite
        ref = dict(id='johto-hack-'+stem, asset=path.relative_to(ROOT).as_posix(),
                   hash=digest, size=sprite.width)
        entries[category].append(ref)
        records.append(dict(asset=path.name, hack=hack, source_rom=infos[hack]['rom_name'],
                            source_rom_sha256=infos[hack]['rom_sha256'],
                            credit=SOURCE[hack][2], sourceUrl=SOURCE[hack][3], **source))
        return ref

    for category, hack, mid, name in ENTRIES:
        pair, ground, _, _ = SOURCE[hack]
        original = Image.alpha_composite(cell(sheets[hack]['mid'], mid), cell(sheets[hack]['over'], mid))
        # Original hack metatiles sometimes bake their field color into a
        # foreground tile. Omit only the exact checked field colors, so mixed
        # tree selections and actor foot masks cannot recolor the ground.
        background = set(cell(sheets[hack]['flat'], ground).get_flattened_data())
        sprite = original.copy(); removed = 0
        for y in range(16):
            for x in range(16):
                if sprite.getpixel((x, y)) in background:
                    sprite.putpixel((x, y), (0, 0, 0, 0)); removed += 1
        assert sprite.getchannel('A').getbbox()
        save(sprite, hack, name, category, dict(pair=pair, metatile=mid, layers=['mid', 'over'],
                                               ground_metatile=ground, omitted_field_pixels=removed,
                                               integer_scale=1, source_rgba_sha256=catalog.sha(original.tobytes())))

    for hack, map_id, box, name in BIG:
        native = Image.open(BASE / hack / 'maps' / (map_id+'-flat.png')).convert('RGBA')
        original = native.crop(box); assert original.size == (32, 48)
        background = set(cell(sheets[hack]['flat'], SOURCE[hack][1]).get_flattened_data())
        if hack == 'crystaldust':
            # This isolated tree stands partly against Violet's gold paving.
            background.update(native.crop((128, 176, 144, 192)).get_flattened_data())
        source = original.copy()
        for y in range(48):
            for x in range(32):
                if source.getpixel((x, y)) in background:
                    source.putpixel((x, y), (0, 0, 0, 0))
        reduced = source.resize((16, 24), Image.Resampling.NEAREST)
        sprite = Image.new('RGBA', (32, 32)); sprite.paste(reduced, (8, 8))
        assert sprite.getchannel('A').getbbox()
        ref = save(sprite, hack, name+'-whole32', 'big_trees',
                   dict(map=map_id, native_rect=box, native_dimensions=[32, 48], integer_reduction=2,
                        reduced_dimensions=[16, 24], placement=[8, 8],
                        source_rgba_sha256=catalog.sha(original.tobytes()), full_canopy_and_roots_retained=True))
        if hack == 'liquidcrystal':
            for q in range(4):
                tile = sprite.crop((q % 2 * 16, q // 2 * 16, q % 2 * 16+16, q // 2 * 16+16))
                path = DEST / ('default-tree-q'+str(q)+'.png'); tile.save(path)
                files[path.name] = catalog.sha(path.read_bytes())

    provenance = dict(origin='Native artwork extracted only from the user-supplied Johto ROM hacks.',
                      no_generated_designs=True, no_fractional_scaling=True, entries=records, files=files)
    (DEST / 'provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')
    body = ('-- Native user-supplied Johto hack foliage. Construct once per GSC mod load.\n'
            '-- Original Gen1 choices and their saved preferences are not changed.\n'
            'return function(base)\nlocal C='+lua(entries)+'\n'
            'C.water=base.water;C.base=base.base;C.sheets={}\nC.cut_trees={}\n'
            "for _,entry in ipairs(base.cut_trees)do if entry.donor then C.cut_trees[#C.cut_trees+1]=entry end end\n"
            'for _,entry in ipairs(C.trees)do local cut={}for k,v in pairs(entry)do cut[k]=v end;cut.id="cut-"..entry.id;C.cut_trees[#C.cut_trees+1]=cut end\n'
            'return C\nend\n')
    (out / 'johto_hack_flora.lua').write_text(body)
    # Exact artwork replacement on the already reviewed source coordinates.
    cache = Path(os.environ['APPDATA']) / 'pokemon-love2d'; packed = {}; changed = []; staged = {}
    pine = next(r for r in records if r['hack']=='crystaldust' and r.get('metatile')==199)
    for name in ('gen2_outdoor_extended.lua', 'park.lua'):
        path = ROOT / 'mappings' / name; rows = preview.read_reviewed(path)
        for row in rows:
            if row['game'] not in e.GAMES: continue
            old = row.get('asset', '')
            target = None
            if old.startswith('assets/original/compact-conifer/'):
                target = DEST / pine['asset']
            elif old.startswith('assets/original/flora/johto-oak32-q'):
                q = int(Path(old).stem[-1]); target = DEST / ('default-tree-q'+str(q)+'.png')
            if target is None: continue
            row.update(kind='third_party', asset=target.relative_to(ROOT).as_posix(),
                       assetFileHash=files[target.name], credit=SOURCE['crystaldust' if 'conifer' in old else 'liquidcrystal'][2],
                       sourceUrl=SOURCE['crystaldust' if 'conifer' in old else 'liquidcrystal'][3],
                       evidence='Whole native Johto hack foliage replaces generated artwork. Small native shrubs remain16px; whole trees use exact2x integer reduction and transparent32px canvas. Original source collision, map roles and events are unchanged.')
            row.pop('assetPixelHash', None)
            row['compositionPixelHash'] = catalog.sha(preview.replacement_image(cache, row, packed, ROOT).tobytes())
            changed.append(row)
        staged[path] = rows
    proof = e.validate_batch(changed, SimpleNamespace(cache=cache, engine=ROOT.parent / '.tools/engine-0395', output=out), ROOT)
    (out / 'proof.json').write_text(json.dumps(dict(validation=proof, catalog_counts={k:len(v) for k,v in entries.items()}, changed_rows=len(changed)), indent=2))
    contact = Image.new('RGBA', (640, 320), (32, 40, 48, 255)); draw = ImageDraw.Draw(contact)
    for i, (stem, sprite) in enumerate(rgba.items()):
        x, y = i % 5 * 128, i // 5 * 100
        contact.alpha_composite(sprite.resize((64, 64), Image.Resampling.NEAREST), (x, y+20))
        draw.text((x, y), stem[:23], fill='white')
    contact.save(out / 'native-flora-contact.png')
    if a.activate:
        (ROOT / 'lib/johto_hack_flora.lua').write_text(body)
        for path, rows in staged.items(): write_rows(path, rows)
        main = ROOT / 'main.lua'; raw = main.read_bytes()
        old = b"local flora=readModule('lib/flora.lua').new({catalog=readModule('lib/flora_catalog.lua'),"
        new = b"local floraCatalog=readModule('lib/flora_catalog.lua')\n  if mod.generation==2 then floraCatalog=readModule('lib/johto_hack_flora.lua')(floraCatalog)end\n  local flora=readModule('lib/flora.lua').new({catalog=floraCatalog,"
        assert old in raw or b"readModule('lib/johto_hack_flora.lua')" in raw
        if old in raw: main.write_bytes(raw.replace(old, new, 1))
    print(json.dumps(dict(changed_rows=len(changed), validation=proof, activated=a.activate, choices={k:len(v) for k,v in entries.items()})))


if __name__ == '__main__':
    main()
