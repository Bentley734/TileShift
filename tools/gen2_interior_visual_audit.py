"""Capture every main-selected GSC interior and deduplicate exact native previews.

Offline visual review material only. No inferred mapping is activated. Actual
runtime coverage and GPU probes remain the authoritative release checks.
"""
import argparse
from collections import defaultdict
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont
import catalog
import preview
from validate_gpu import runtime_fingerprint

ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENTS = {'INDOOR', 'GATE', 'DUNGEON', 'CAVE'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--games',nargs='+',default=['crystal','gold','silver'],choices=('red','blue','yellow','gold','silver','crystal'))
    parser.add_argument('--all-maps',action='store_true',help='Also capture outdoor maps; used by the Gen1 audit')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    cache = Path(os.environ['APPDATA']) / 'pokemon-love2d'
    fingerprint = runtime_fingerprint(ROOT)
    modules = list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]", (ROOT/'main.lua').read_text())))
    selected_files = ['main.lua', *modules]
    selected_hashes = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in selected_files}
    families = defaultdict(list)
    for name in modules:
        for row in preview.read_reviewed(ROOT/name):
            if row['game'] in args.games and row['style'] == 'gen3':
                families[row['game'], row['tileset']].append(row)
    original_read = catalog.read_lua
    catalog.read_lua = lru_cache(maxsize=None)(original_read)
    preview.read_reviewed = lru_cache(maxsize=None)(preview.read_reviewed)
    original_art = preview.replacement_image
    memo, packed = {}, {}
    def cached_art(cache, row, packed, root):
        key = row.get('compositionPixelHash') or json.dumps(row, sort_keys=True)
        if key not in memo:
            memo[key] = original_art(cache, row, packed, root)
        return memo[key]
    preview.replacement_image = cached_art
    records, unique, excluded = [], {}, []
    for game in args.games:
        maps = catalog.read_lua(cache/game/'data/generated/maps.lua')
        output = args.output/game
        output.mkdir(exist_ok=True)
        for name, definition in sorted(maps.items()):
            if not isinstance(definition,dict)or not definition.get('tileset')or not definition.get('width')or not definition.get('height')or not isinstance(definition.get('blocks'),list):
                continue
            if not args.all_maps and definition.get('environment') not in ENVIRONMENTS:
                continue
            if game in ('gold', 'silver') and name == 'SAFARI_ZONE_BETA':
                excluded.append(dict(game=game, map=name,
                    reason='Unused inaccessible beta map; references missing native tile255.'))
                continue
            result = preview.map_preview(cache, output, game, name, name,
                families[game, definition['tileset']], packed, 1, ROOT, roof_rows=None if args.all_maps else [])
            before = output/(name+'-before-native.png')
            after = output/(name+'-after-native.png')
            before_image, after_image = Image.open(before), Image.open(after)
            pixels = repr((before_image.size,after_image.size)).encode()+before_image.tobytes()+after_image.tobytes()
            digest = hashlib.sha256(pixels).hexdigest()
            environment=definition.get('environment','OUTDOOR'if definition['tileset']in('OVERWORLD','FOREST','SAFARI','PLATEAU')else'INTERIOR')
            record = dict(game=game, map=name, environment=environment,
                tileset=definition['tileset'], before=str(before.resolve()), after=str(after.resolve()),
                visible_cells=result['visible_cells'], replaced_cells=result['replaced_occurrences'],
                remaining_cells=result['preserved_native_occurrences'], pair_rgba_sha256=digest)
            if digest in unique:
                record['identical_to'] = [unique[digest]['game'], unique[digest]['map']]
            else:
                unique[digest] = record
            records.append(record)
            (args.output/'progress.json').write_text(json.dumps(dict(maps=len(records), unique=len(unique), game=game, map=name)))
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 12)
    pages = []
    for group, selected in [('caves', [r for r in unique.values() if r['environment']=='CAVE']),
                            ('rooms', [r for r in unique.values() if r['environment']!='CAVE'])]:
        for start in range(0, len(selected), 18):
            batch = selected[start:start+18]
            canvas = Image.new('RGB', (1536, 6*228), '#18212b')
            draw = ImageDraw.Draw(canvas)
            for i, record in enumerate(batch):
                x, y = i%3*512, i//3*228
                draw.text((x+4,y+4), record['game']+'/'+record['map'], font=font, fill='white')
                for side, key in enumerate(('before', 'after')):
                    image = Image.open(record[key]).convert('RGB')
                    image.thumbnail((250,200), Image.Resampling.NEAREST)
                    canvas.paste(image, (x+side*256+3, y+24))
            path = args.output/f'{group}-contact-{start//18+1:02}.png'
            canvas.save(path)
            pages.append(dict(path=str(path.resolve()), group=group,
                maps=[[r['game'],r['map']] for r in batch]))
    assert selected_hashes == {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in selected_files}, 'Selected mappings changed during visual capture'
    report = dict(type='offline main-selected interior previews', runtime_inputs=fingerprint,
        source_maps=len(records), unique_pairs=len(unique), records=records, contacts=pages,
        selected_mapping_hashes=selected_hashes,
        excluded_unused_maps=excluded,
        missing_cells=sum(r['remaining_cells'] for r in records),
        limits='Native imported map previews at animation frame0, no actors. Contact sheets are thumbnails; inspect full images for pixel details. Captures require visual review.')
    (args.output/'manifest.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(dict(source_maps=len(records), unique_pairs=len(unique), missing_cells=report['missing_cells'], contacts=len(pages))))


if __name__ == '__main__':
    main()
