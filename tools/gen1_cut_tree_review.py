"""Map actual Gen1 OVERWORLD Cut trees without changing field-move logic."""
import argparse
import json
import os
from pathlib import Path
import catalog
import preview
from newbark_building_review import lua

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    cache, mod = Path(os.environ['APPDATA']) / 'pokemon-love2d', ROOT / 'TileShift'
    native = next(r for r in json.loads((ROOT / '.work/tileshift-gen2-outdoor-review/native-cuttable-tree-refs.json').read_text()) if r['game'] == 'firered')
    donor = {'game': 'firered', 'tileset': 'ow', 'kind': 'field_object', 'id': 95, 'frame': 0,
             'hash': native['pixelHash'], 'metaHash': native['metaHash'], 'rgbaHash': native['rgbaHash']}
    base = {'game': 'emerald', 'tileset': 'general__petalburg', 'id': 1,
            'hash': '1c7acc0ebc7c5878e77e1dfbbc2828e1a2745c0ded470f1f0152f67193222ed1'}
    rows, proofs, catalogs = [], [], {}
    for game in ('red', 'blue', 'yellow'):
        catalogs[game] = json.loads((ROOT / '.work/tileshift-catalog' / (game + '.json')).read_text())
        field_path = cache / game / 'data/generated/field.lua'
        field = catalog.read_lua(field_path)
        swaps = {s['before']: s['after'] for s in field['cutTreeSwaps']}
        files = next(t['fingerprints'] for t in catalogs[game]['tilesets'] if t['tileset'] == 'OVERWORLD')
        selected = [c for c in catalogs[game]['cells'] if c['tileset'] == 'OVERWORLD'
                    and c['block_id'] in swaps and c['tiles'][2] == 0x3d]
        assert len(selected) == 5
        for cell in selected:
            assert cell['tiles'] == [45, 46, 61, 62] and cell['walkable_tiles'][2] is False
            assert not cell['grass_tile_present'] and not cell['warp_tile_present']
            rows.append({'game': game, 'style': 'gen3', 'tileset': 'OVERWORLD',
                'id': cell['block_id'], 'quadrant': cell['quadrant'], 'sourceHash': cell['grayscale_pixel_sha256'],
                'sourceFiles': files, 'role': 'cuttable_small_tree', 'status': 'reviewed',
                'kind': 'native_composite', 'base': base,
                'parts': [{'donor': donor, 'x': 0, 'y': 0, 'srcX': 0, 'srcY': 0, 'w': 16, 'h': 16}],
                'sourceCutSwap': {'before': cell['block_id'], 'after': swaps[cell['block_id']]},
                'sourceCutFieldHash': catalog.sha(field_path.read_bytes()),
                'evidence': 'Actual native Gen1 Cut-tree eligibility: OVERWORLD only, canonical lower-left tile0x3d, blocked source cell and an imported field.cutTreeSwaps entry for this exact block. All four raw8px source tiles are45,46,61,62. FOREST and PLATEAU scenery, GYM plants and cuttable tall grass are excluded. Complete native FR/LG Cut-tree object95 frame0 fits the original16px footprint, with all alpha and native pixels intact. The original controller still checks badges/party/move/tileset and performs its original block replacement and animation; only standing artwork is replaced. Cut Trees choices retain the same source references and behavior.'})
            proofs.append({'game': game, 'id': cell['block_id'], 'quadrant': cell['quadrant'], 'replacement': swaps[cell['block_id']]})
    catalogs['firered'] = json.loads((ROOT / '.work/tileshift-catalog/firered.json').read_text())
    catalogs['emerald'] = json.loads((ROOT / '.work/tileshift-catalog/emerald.json').read_text())
    assert preview.verify(rows, cache, catalogs, mod) == 15
    output = ROOT / '.work/tileshift-gen1-cut-review'
    output.mkdir(exist_ok=True)
    (output / 'proof.json').write_text(json.dumps({'rows': 15, 'source_eligibility': proofs, 'source_gameplay_unchanged': True}, indent=2))
    target = mod / 'mappings/cut_trees.lua' if args.activate else output / 'candidates.lua'
    target.write_text('-- Actual Gen1 Cut trees; original field-move and block-swap behavior stays native.\nreturn ' + lua(rows) + '\n', encoding='utf-8')
    print(json.dumps({'rows': 15, 'activated': args.activate, 'mapping': str(target)}))


if __name__ == '__main__':
    main()
