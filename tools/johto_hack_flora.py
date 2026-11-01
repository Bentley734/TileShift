"""Extract native hack foliage and compose compact trees at native pixel size.

Small shrubs/flowers/grass remain16px. Large trees retain their original32px
width, canopy and roots; complete foliage sections are arranged into32x32.
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
    ('liquidcrystal', 'round-tree', ((22, 23), (28, 29), (36, 37)), ((0, 16), (32, 48))),
    ('firegold', 'conifer', ((18, 19), (26, 27), (34, 35)), ((0, 16), (32, 48))),
    ('crystaldust', 'conifer', None, ((0, 8), (16, 32), (40, 48))),
)


def cell(sheet, mid):
    x, y = mid % 16 * 16, mid // 16 * 16
    return sheet.crop((x, y, x+16, y+16))


def write_changed_rows(path, rows, changed):
    """Keep unrelated authored rows byte-for-byte, including Lua key order."""
    raw = path.read_bytes(); text = raw.decode(); spans = []; depth = 0; quoted = escaped = False; number = 0
    for line in text.splitlines(keepends=True):
        if not line.startswith('add((function()return {'):
            spans.append(line); continue
        start = line.index('{'); record = None; pieces = []; last = 0
        for index in range(start, len(line)):
            char = line[index]
            if quoted:
                if escaped: escaped = False
                elif char == '\\': escaped = True
                elif char == '"': quoted = False
                continue
            if char == '"': quoted = True
            elif char == '{':
                if depth == 1: record = index
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 1 and record is not None:
                    if number in changed:
                        pieces.extend((line[last:record], lua(rows[number])))
                        last = index + 1
                    number += 1
                    record = None
        assert depth == 0 and not quoted
        pieces.append(line[last:]); spans.append(''.join(pieces))
    assert number == len(rows)
    path.write_bytes(''.join(spans).encode())


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

    for hack, name, grid, bands in BIG:
        pair = SOURCE[hack][0]
        if grid:
            original = Image.new('RGBA', (32, 48))
            for y, row in enumerate(grid):
                for x, mid in enumerate(row):
                    original.paste(cell(sheets[hack]['flat'], mid), (x * 16, y * 16))
            location = dict(pair=pair, native_metatile_grid=grid, layers=['flat'])
        else:
            map_id, box = 'g00_m000', (96, 176, 128, 224)
            native = Image.open(BASE / hack / 'maps' / (map_id+'-flat.png')).convert('RGBA')
            original = native.crop(box)
            location = dict(map=map_id, native_rect=box)
        assert original.size == (32, 48)
        background = set(cell(sheets[hack]['flat'], SOURCE[hack][1]).get_flattened_data())
        if hack == 'crystaldust':
            # This isolated tree stands partly against Violet's gold paving.
            background.update(native.crop((128, 176, 144, 192)).get_flattened_data())
        source = original.copy()
        for y in range(48):
            for x in range(32):
                if source.getpixel((x, y)) in background:
                    source.putpixel((x, y), (0, 0, 0, 0))
        sprite = Image.new('RGBA', (32, 32)); offset = 0; modules = []
        for start, end in bands:
            piece = source.crop((0, start, 32, end))
            sprite.paste(piece, (0, offset))
            modules.append(dict(source_rect=[0, start, 32, end], placement=[0, offset]))
            offset += end - start
        assert offset == 32 and sprite.getchannel('A').getbbox()
        bounds = sprite.getchannel('A').getbbox()
        assert bounds[2] - bounds[0] >= 26 and bounds[3] - bounds[1] >= 27, 'Compact tree must fill its original footprint'
        save(sprite, hack, name+'-whole32', 'big_trees',
             dict(**location, native_dimensions=[32, 48], integer_scale=1,
                  compact_dimensions=[32, 32], modules=modules, alpha_bounds=bounds,
                  processing='Native canopy and matching root sections; omitted middle foliage tiers, no resized pixels.',
                  source_rgba_sha256=catalog.sha(original.tobytes()), canopy_and_roots_retained=True))
        if hack == 'liquidcrystal':
            for q in range(4):
                tile = sprite.crop((q % 2 * 16, q // 2 * 16, q % 2 * 16+16, q // 2 * 16+16))
                path = DEST / ('default-tree-q'+str(q)+'.png'); tile.save(path)
                files[path.name] = catalog.sha(path.read_bytes())

    provenance = dict(origin='Native artwork extracted only from the user-supplied Johto ROM hacks.',
                      no_generated_designs=True, no_fractional_scaling=True, entries=records, files=files)
    (DEST / 'provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')
    # Azalea's tree uses the same four cells and keeps a copy of their source
    # recipe in the interior provenance. Refresh it on subsequent extractions.
    interior_proof = ROOT / 'assets/third_party/johto-hacks/interiors/provenance.json'
    if interior_proof.is_file():
        interior = json.loads(interior_proof.read_text())
        native_tree = next(r for r in records if r['asset']=='liquidcrystal-round-tree-whole32.png')
        for index, item in enumerate(interior['pieces']):
            asset = item.get('asset', '')
            if asset.startswith('assets/third_party/johto-hacks/flora/default-tree-q'):
                interior['pieces'][index] = dict(native_tree, asset=asset,
                    assetFileHash=files[Path(asset).name], source='liquidcrystal',
                    source_provenance='assets/third_party/johto-hacks/flora/provenance.json')
        interior_proof.write_text(json.dumps(interior, indent=2)+'\n')
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
    for path in sorted((ROOT / 'mappings').glob('*.lua')):
        rows = preview.read_reviewed(path); indexes = set()
        for index, row in enumerate(rows):
            if row['game'] not in e.GAMES: continue
            old = row.get('asset', '')
            target = None
            if old.startswith('assets/original/compact-conifer/'):
                target = DEST / pine['asset']
            elif old.startswith('assets/original/flora/johto-oak32-q'):
                q = int(Path(old).stem[-1]); target = DEST / ('default-tree-q'+str(q)+'.png')
            elif old.startswith('assets/third_party/johto-hacks/flora/default-tree-q'):
                target = DEST / Path(old).name
            if target is None: continue
            row.update(kind='third_party', asset=target.relative_to(ROOT).as_posix(),
                       assetFileHash=files[target.name], credit=SOURCE['crystaldust' if 'conifer' in old else 'liquidcrystal'][2],
                       sourceUrl=SOURCE['crystaldust' if 'conifer' in old else 'liquidcrystal'][3],
                       evidence='Native Johto hack foliage at original pixel size. Compact32x32 trees use complete canopy and matching root sections with transparent ground corners, without scaled pixels. Original source collision, map roles, room floors and events are unchanged.')
            row.pop('assetPixelHash', None)
            row['compositionPixelHash'] = catalog.sha(preview.replacement_image(cache, row, packed, ROOT).tobytes())
            changed.append(row)
            indexes.add(index)
        if indexes: staged[path] = (rows, indexes)
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
        for path, (rows, indexes) in staged.items():
            write_changed_rows(path, rows, indexes)
        main = ROOT / 'main.lua'; raw = main.read_bytes()
        old = b"local flora=readModule('lib/flora.lua').new({catalog=readModule('lib/flora_catalog.lua'),"
        new = b"local floraCatalog=readModule('lib/flora_catalog.lua')\n  if mod.generation==2 then floraCatalog=readModule('lib/johto_hack_flora.lua')(floraCatalog)end\n  local flora=readModule('lib/flora.lua').new({catalog=floraCatalog,"
        assert old in raw or b"readModule('lib/johto_hack_flora.lua')" in raw
        if old in raw: main.write_bytes(raw.replace(old, new, 1))
    print(json.dumps(dict(changed_rows=len(changed), validation=proof, activated=a.activate, choices={k:len(v) for k,v in entries.items()})))


if __name__ == '__main__':
    main()
