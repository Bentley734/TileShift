"""Inspect unresolved source cells in one real map; no production writes."""
import argparse
import json
import os
from collections import defaultdict
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import preview
from interior_review import Imports, WORKSPACE


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', required=True)
    parser.add_argument('--map', required=True)
    args = parser.parse_args()
    output = WORKSPACE / '.work/tileshift-map-remaining' / (args.game + '-' + args.map)
    output.mkdir(parents=True, exist_ok=True)
    imports = Imports(Path(os.environ['APPDATA']) / 'pokemon-love2d', WORKSPACE / '.work/tileshift-catalog')
    image, cells, pictures, meta = imports.gb(args.game, args.map)
    generic, positioned = set(), set()
    for path in (WORKSPACE / 'TileShift/mappings').glob('*.lua'):
        for row in preview.read_reviewed(path):
            if row['game'] == args.game and row['style'] == 'gen3' and row['tileset'] == meta['tileset'] and row.get('map', args.map) == args.map:
                if 'x' in row:
                    positioned.add((row['id'], row['quadrant'], row['x'], row['y']))
                else:
                    generic.add((row['id'], row['quadrant']))
    remaining = []
    for cell in cells:
        key = cell['id'], cell['quadrant']
        coords = [(x, y) for x, y in cell['coordinates'] if key not in generic and (*key, x, y) not in positioned]
        if coords:
            remaining.append({**cell, 'coordinates': coords, 'count': len(coords)})
    remaining.sort(key=lambda r: -r['count'])
    columns, step, margin = 5, 240, 16
    sheet = Image.new('RGB', (columns * step + margin * 2, 76 + ((len(remaining) + columns - 1) // columns) * 170), '#18202c')
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15)
    draw.text((margin, 14), f'{args.game} / {args.map}: {sum(r["count"] for r in remaining)} unresolved cells; source artwork and behavior only', font=font, fill='white')
    for i, row in enumerate(remaining):
        x, y = margin + i % columns * step, 68 + i // columns * 170
        tile = pictures[row['id'], row['quadrant']]
        sheet.paste(tile.resize((80, 80), Image.Resampling.NEAREST), (x, y))
        draw.text((x + 88, y), f'{row["id"]}:{row["quadrant"]} / {row["count"]} cells', font=font, fill='white')
        draw.text((x + 88, y + 24), f'collision {row["collision"]}', fill='#ccd7e5')
        draw.text((x, y + 91), str(row['tiles']), font=font, fill='white')
        draw.text((x, y + 115), str(row['coordinates'][:3]), fill='#ccd7e5')
    sheet.save(output / 'remaining-source-cells.png')
    (output / 'remaining-source-cells.json').write_text(json.dumps({'meta': meta, 'remaining_cells': sum(r['count'] for r in remaining), 'cells': remaining}, indent=2))
    print(json.dumps({'output': str(output), 'unique_remaining': len(remaining), 'remaining_cells': sum(r['count'] for r in remaining)}))


if __name__ == '__main__':
    main()
