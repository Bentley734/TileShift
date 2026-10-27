"""Stage and activate the reviewed whole Bike Shop without changing older rows."""
import argparse
import json
import os
from pathlib import Path
from types import SimpleNamespace
import catalog
import preview
import kanto_architecture_review as kanto

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    source = ROOT / '.work/tileshift-special-buildings'
    output = source / 'bike-activation'
    output.mkdir(exist_ok=True)
    report = json.loads((source / 'special-native-counterparts.json').read_text())
    models = {'bike_shop': report['templates']['bike_shop']}
    instances = [r for r in report['source_instances'] if r['template'] == 'bike_shop']
    assert len(instances) == 6 and len(models['bike_shop']['features_checked']) == 4
    (output / 'bike_shop-compact-prototype.png').write_bytes((source / 'bike_shop-compact-prototype.png').read_bytes())
    stage = SimpleNamespace(cache=Path(os.environ['APPDATA']) / 'pokemon-love2d',
        catalog=ROOT / '.work/tileshift-catalog', output=output,
        approved_candidates=True, write_reviewed=False)
    rows = kanto.positioned_rows(stage, models, instances)
    assert len(rows) == 96
    contexts = kanto.city_contexts(stage, rows, instances)
    (output / 'bike-contexts.json').write_text(json.dumps(contexts, indent=2))
    if args.activate:
        proof = json.loads((output / 'bike-production-proof.json').read_text())
        assert proof['session_rejected'] == 0 and proof['actual_positioned_session_cells_verified'] == 96
        assert proof['private_candidate_file_sha256'] == catalog.sha((output / 'kanto-staged-rows.json').read_bytes())
        target = ROOT / 'TileShift/mappings/buildings_extended.lua'
        original = target.read_bytes()
        stage.write_reviewed = True
        kanto.positioned_rows(stage, models, instances)
        text = target.read_bytes()
        assert text.startswith(original.rstrip()[:-len(b'return rows')])
        proof.update(status='reviewed_bike_shop_active', production_rows_written=96)
        (output / 'bike-production-proof.json').write_text(json.dumps(proof, indent=2))
    print(json.dumps({'rows': len(rows), 'contexts': contexts, 'active': args.activate}))


if __name__ == '__main__':
    main()
