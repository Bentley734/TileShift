"""Keep Cherrygrove's northeast inland pond separate from its coastal sea."""
import argparse
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import preview
import gen2_extended_review as ext

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    cache, mod = Path(os.environ['APPDATA']) / 'pokemon-love2d', ROOT / 'TileShift'
    output = ROOT / '.work/tileshift-cherrygrove-pond-review'
    output.mkdir(exist_ok=True)
    active, rows = ext.active_rows(mod), []
    for game in ext.GAMES:
        data = ext.source(cache, game)
        definition = data['maps']['CHERRYGROVE_CITY']
        known = {}
        for old in active:
            if old['game'] == game and old.get('map') == 'ROUTE_30' and old['role'].startswith('freshwater_pond_'):
                cell = ext.cell_info(cache, game, data, old['tileset'], old['id'], old['quadrant'])
                key = ext.identity(cell)
                assert key not in known or old['donor'] == known[key]['donor']
                known[key] = old
        for y in (0, 1):
            for x in range(34, 38):
                bid = definition['blocks'][y // 2 * definition['width'] + x // 2]
                q = y % 2 * 2 + x % 2
                cell = ext.cell_info(cache, game, data, definition['tileset'], bid, q)
                assert cell['collision'] == 0x29 and ext.identity(cell) in known
                template = known[ext.identity(cell)]
                row = copy.deepcopy(template)
                row.update(map='CHERRYGROVE_CITY', tileset=definition['tileset'], id=bid, quadrant=q,
                    x=x, y=y, sourceCells=[[x, y]], sourceHash=cell['sourceHash'],
                    sourceFiles=data['fingerprints'][definition['tileset']], sourceCollision=cell['collision'],
                    sourcePalettes=[a.get('palette', 1) for a in cell['attributes']],
                    sourcePriority=[bool(a.get('priority')) for a in cell['attributes']],
                    sourceBody='northeast inland pond, distinct from the coastal sea', status='reviewed')
                row['evidence'] = 'PRIVATE Cherrygrove northeast inland pond only, exact cells34..37,y0..1. Source pixels, water collision0x29, palette slots and priority match the already reviewed Route30 freshwater bank/interior family independently per cartridge. This pond is outside the explicit marine region; shared source block IDs also occur in the sea, so all eight cells use exact positions to prevent calm pond art leaking into coastal water or ocean waves leaking into the pond. Actual native FR Viridian banks/interior remain complete and static, with original Surf/fishing/movement unchanged. No north-map water connection is inferred; the actual Route30 connection covers a different strip. Layout, warps and events remain native.'
                rows.append(row)
    assert len(rows) == 24
    live = ext.validate_batch(rows, SimpleNamespace(cache=cache, engine=ROOT / '.tools/engine-0395', output=output), mod)
    contexts = [preview.map_preview(cache, output, game, 'CHERRYGROVE_CITY', game + '-cherrygrove-pond', active + rows, {}, 2, mod) for game in ext.GAMES]
    (output / 'candidates.json').write_text(json.dumps(rows, indent=2, sort_keys=True))
    (output / 'proof.json').write_text(json.dumps({'status': 'private_bounded_pond_review', 'rows': 24, 'live': live,
        'pond_cells_per_game': 8, 'contexts': contexts, 'marine_region_excluded': True}, indent=2))
    if args.activate:
        for row in rows:
            row['evidence'] = row['evidence'].replace('PRIVATE Cherrygrove', 'Reviewed Cherrygrove')
        stats = ext.merge_reviewed(rows, mod / 'mappings/gen2_outdoor_extended.lua')
        (output / 'activation.json').write_text(json.dumps({'mapping': stats, 'live': live}, indent=2))
    print(json.dumps({'rows': 24, 'live': live, 'active': args.activate}))


if __name__ == '__main__':
    main()
