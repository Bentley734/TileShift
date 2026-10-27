"""Native complete feature bounds for the upstairs household pass."""
import json
import os
from pathlib import Path
from PIL import Image, ImageDraw
from interior_review import Imports, WORKSPACE


def main():
    cache = Path(os.environ['APPDATA']) / 'pokemon-love2d'
    imports = Imports(cache, WORKSPACE / '.work/tileshift-catalog')
    output = WORKSPACE / '.work/tileshift-upper-room-review'
    output.mkdir(parents=True, exist_ok=True)
    picture, rows, _, meta = imports.gba('firered', 'FR_PLAYERS_HOUSE_2F')
    image = picture.resize((picture.width * 5, picture.height * 5), Image.Resampling.NEAREST).convert('RGB')
    draw = ImageDraw.Draw(image)
    for row in rows:
        for x, y in row['coordinates']:
            draw.rectangle((x * 80, y * 80, x * 80 + 79, y * 80 + 79), outline='#ff80be')
            draw.text((x * 80 + 2, y * 80 + 2), str(row['id']), fill='black', stroke_width=1, stroke_fill='white')
    image.save(output / 'whole-native-upstairs-grid.png')
    (output / 'native-upstairs-context.json').write_text(json.dumps({'meta': meta, 'cells': rows}, indent=2))
    source, rows, _, meta = imports.gb('red', 'REDS_HOUSE_2F')
    source.resize((source.width * 5, source.height * 5), Image.Resampling.NEAREST).save(output / 'whole-original-upstairs.png')
    (output / 'original-upstairs-context.json').write_text(json.dumps({'meta': meta, 'cells': rows}, indent=2))
    print(output)


if __name__ == '__main__':
    main()
