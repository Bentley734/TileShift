"""Prove every recolored cell retains its exact original geometry and alpha."""
from __future__ import annotations
import argparse
from collections import Counter
import json, os
from pathlib import Path
from PIL import Image
import catalog, preview

def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=Path(os.environ['APPDATA']) / 'pokemon-love2d')
    parser.add_argument('--output', type=Path, default=root.parent / '.work/tileshift-source-palette-proof.json')
    args = parser.parse_args()
    packed, counts = {}, Counter()
    for path in sorted((root / 'mappings').glob('*.lua')):
        for row in preview.read_reviewed(path):
            if row.get('kind') != 'source_palette':
                continue
            colors = row['sourceColors']
            assert all(len({tuple(c) for c in palette}) == 4 for palette in colors), (path, row['role'], 'Palette collapses distinct source shades')
            colored = preview.replacement_image(args.cache, row, packed, root)
            original = Image.new('RGBA', (16, 16))
            inverse = [{tuple(c): 255 - 85 * i for i, c in enumerate(p)} for p in colors]
            for y in range(16):
                for x in range(16):
                    r, g, b, alpha = colored.getpixel((x, y))
                    shade = inverse[y // 8 * 2 + x // 8][r, g, b]
                    original.putpixel((x, y), (shade, shade, shade, alpha))
            assert catalog.sha(original.tobytes()) == row['sourceHash'], (path, row['role'], 'Recolored geometry differs from original source')
            counts[row['game']] += 1
    report = {'rows': sum(counts.values()), 'pixels': sum(counts.values()) * 256, 'by_game': dict(counts),
              'every_recolored_pixel_inverts_to_exact_original_source_hash': True, 'geometry_scaling_or_pixel_loss': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
