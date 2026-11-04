"""Bind all43 Crystal berry sheets to the complete native RSE stage contracts."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image
import catalog
from newbark_building_review import lua
from reverse_common import ROOT
from validate_berry_theme import numeric_keys

SOURCE_CONTRACT=Path(__file__).with_name('berry_source_contract.json')
SOURCE_CONTRACT_HASH='37e8331d80bc3d340a80afbfdb9a01a0e120dfb932a74765cb6fb25873057f2f'
NAMES=('cheri','chesto','pecha','rawst','aspear','leppa','oran','persim','lum','sitrus',
 'figy','wiki','mago','aguav','iapapa','razz','bluk','nanab','wepear','pinap','pomeg',
 'kelpsy','qualot','hondew','grepa','tamato','cornn','magost','rabuta','nomel','spelon',
 'pamtre','watmel','durin','belue','liechi','ganlon','salac','petaya','apicot','lansat','starf','enigma')
OUT=ROOT.parent/'.work/tileshift-v0350-berries'


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inventory',action='store_true');p.add_argument('--activate',action='store_true');p.add_argument('--output',type=Path,default=OUT/'catalog-review');args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    source=json.loads(SOURCE_CONTRACT.read_text());assert digest(source)==SOURCE_CONTRACT_HASH,'Native berry source contract changed; fresh review required'
    sources=numeric_keys(source);varieties=[];proofs=[];missing=[]
    for berry,name in enumerate(NAMES,1):
        relative='assets/original/berries/gen2/'+name+'.png';path=ROOT/relative
        if not path.exists():missing.append(relative);continue
        image=Image.open(path).convert('RGBA');assert image.size==(16,240),(name,'Whole native sheet dimensions required')
        alpha=set(image.getchannel('A').get_flattened_data());assert alpha<={0,255}and 0 in alpha and 255 in alpha,(name,'Crisp transparent pixel art required')
        frames=[]
        for frame in sources['emerald']['trees'][berry]['frames']:
            box=(0,frame['y'],frame['w'],frame['y']+frame['h']);piece=image.crop(box)
            assert piece.getbbox() is not None,(name,'Empty growth state')
            frames.append(dict(y=frame['y'],w=frame['w'],h=frame['h'],rgba_sha256=catalog.sha(piece.tobytes()),alpha_sha256=catalog.sha(piece.getchannel('A').tobytes()),opaque_pixels=sum(v==255 for v in piece.getchannel('A').get_flattened_data()),bounds=piece.getbbox()))
        entry=dict(name=name,asset=relative,hash=catalog.sha(path.read_bytes()))
        varieties.append((berry,entry));proofs.append(dict(berry=berry,**entry,pixel_sha256=catalog.sha(image.tobytes()),frames=frames))
    report=dict(status='inventory'if args.inventory else'candidate',count=len(varieties),required=43,missing=missing,source_contract_sha256=SOURCE_CONTRACT_HASH)
    (args.output/'asset-inventory.json').write_text(json.dumps(dict(**report,varieties=proofs),sort_keys=True,indent=2)+'\n')
    if args.inventory:print(json.dumps(report),flush=True);return
    assert not missing,('All43 individually authored varieties are required before activation',missing)
    assert len({p['pixel_sha256']for p in proofs})==43,'Berry varieties must not repeat one bitmap'
    shape_hashes=[digest([f['alpha_sha256']for f in p['frames'][3:]])for p in proofs]
    report.update(individual_pixel_patterns=43,distinct_mature_silhouettes=len(set(shape_hashes)))
    data=dict(format=1,sourceContractHash=SOURCE_CONTRACT_HASH,varieties=dict(varieties),sources=sources)
    data=json.loads(json.dumps(data,sort_keys=True));data=numeric_keys(data)
    body='-- Individually authored Crystal berry sheets; original native RSE growth/state metadata retained.\nreturn '+lua(data)+'\n'
    target=ROOT/'lib/berry_catalog.lua'if args.activate else args.output/'berry_catalog.lua';target.write_text(body,encoding='utf-8')
    decoded=catalog.plain(catalog.LUA.execute(target.read_text()))
    assert decoded['sourceContractHash']==SOURCE_CONTRACT_HASH
    report.update(status='passed',activated=args.activate,catalog_sha256=catalog.sha(target.read_bytes()))
    (args.output/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':main()
