"""Build portable, pixel-verified Gen2 comparison images and a release gallery."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import zipfile
from gpu_comparison import make, NAMES
from validate_gpu import runtime_fingerprint

ROOT=Path(__file__).resolve().parents[1]
TOWNS={'PALLET_TOWN','VIRIDIAN_CITY','PEWTER_CITY','CERULEAN_CITY','LAVENDER_TOWN',
       'VERMILION_CITY','CELADON_CITY','FUCHSIA_CITY','SAFFRON_CITY','CINNABAR_ISLAND'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--report',type=Path,default=ROOT.parent/'.work/tileshift-v0300-gen2-gpu/report.json')
    p.add_argument('--output',type=Path,default=ROOT.parent/'.work/tileshift-v0300-comparisons')
    p.add_argument('--build',type=Path,default=ROOT/'build')
    args=p.parse_args();report=json.loads(args.report.read_text())
    assert report['status']=='passed'and report['theme']=='gen3'
    inputs=runtime_fingerprint(ROOT)
    assert report['runtime_inputs']==inputs,'Runtime changed after native GPU validation'
    version=json.loads((ROOT/'manifest.json').read_text())['version']
    args.output.mkdir(parents=True,exist_ok=True);args.build.mkdir(parents=True,exist_ok=True)
    comparisons=[]
    for source in report['fixtures']:
        game,name=source['game'],source['map']
        if game!='crystal'and name not in TOWNS|{'LANCES_ROOM'}:continue
        assert source['coverage']['preserved_native_occurrences']==0
        NAMES[game,name]=(game.capitalize()+' / '+name.replace('_',' ').title(),
                         game.capitalize()+'-'+name.title().replace('_',''),
                         'Original '+game.capitalize()+' native DAY colors')
        fixture=copy.deepcopy(source)
        fixture['comparison_after_label']='Gen 3 - complete background'
        result=make(fixture,args.output.resolve())
        result['output']=Path(result['output']).name
        comparisons.append(result)
    assert comparisons and len({r['output']for r in comparisons})==len(comparisons)
    metadata=dict(version=version,source_type=report['type'],native_gpu_checks=report['checks'],
                  runtime_inputs_sha256=inputs['sha256'],comparisons=comparisons,
                  pixel_scale=2,resampling='nearest-neighbor',actors_rendered=False)
    (args.output/'comparison-verification.json').write_text(json.dumps(metadata,indent=2)+'\n')
    (args.output/'README.txt').write_text(
        'TileShift '+version+' - Gen2 Kanto and shared interiors\n\n'
        'Original native DAY backgrounds and current complete Gen3 backgrounds.\n'
        'Both panels are actual native renderer readbacks at exactly2x nearest-neighbor.\n'
        'All visible background cells in these images are replaced. No actors rendered.\n'
        'Scenes include Gold/Silver/Crystal Kanto towns and representative Crystal\n'
        'routes, rooms, transport, League and Johto interior corrections.\n'
        'Original gameplay geometry, collision, interactions and warps are preserved.\n'
        'Unmatched unique compact details retain original GSC geometry in Gen3 colors.\n'
        'Source pixels and saved comparison panels were independently verified.\n')
    archive=args.build/('TileShift-Gen2-Comparisons-v'+version+'.zip')
    names=[r['output']for r in comparisons]+['README.txt','comparison-verification.json']
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as bundle:
        for name in sorted(names):
            entry=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED
            entry.external_attr=0o100644<<16;bundle.writestr(entry,(args.output/name).read_bytes(),compresslevel=9)
    with zipfile.ZipFile(archive)as bundle:
        assert bundle.testzip()is None and set(bundle.namelist())==set(names)
        for r in comparisons:assert hashlib.sha256(bundle.read(r['output'])).hexdigest()==r['comparison_png_sha256']
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.zip.sha256').write_text(digest+'  '+archive.name+'\n')
    print(json.dumps(dict(images=len(comparisons),archive=str(archive.resolve()),bytes=archive.stat().st_size,sha256=digest)))

if __name__=='__main__':main()
