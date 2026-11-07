"""Prepare a native CrystalDust cafe-counter divider for New Bark privately.

The north-attached counter repeats only a uniform native vertical middle strip
and retains one complete lower cabinet/end. No input mod or import is modified.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import os
import shutil
import sys
from types import SimpleNamespace

WORKSPACE = next(parent for parent in Path(__file__).resolve().parents
                 if (parent/'.tools/python').is_dir()
                 and (parent/'.work/tileshift-firegold').is_dir())
sys.path.insert(0,str(WORKSPACE/'.tools/python'))
sys.path.insert(0,str(WORKSPACE/'TileShift/tools'))
from PIL import Image, ImageDraw, ImageFont
import catalog
import preview
import gen2_extended_review as review
from newbark_building_review import lua

HACK = WORKSPACE/'.work/tileshift-firegold/crystaldust'
OUT = WORKSPACE/'.work/tileshift-newbark-crystaldust/divider'
PREFIX = Path('assets/third_party/johto-hacks/newbark-crystaldust-divider')
MODULE = Path('mappings/newbark_crystaldust_divider.lua')
CACHE = Path(os.environ['APPDATA'])/'pokemon-love2d'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pixels(image):
    return hashlib.sha256(image.convert('RGBA').tobytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    default=json.loads((WORKSPACE/'.work/tileshift-v0443-checkpoint/frozen.json').read_text())['stage']
    parser.add_argument('--mod-root',type=Path,default=Path(default))
    parser.add_argument('--proposal-only',action='store_true')
    args=parser.parse_args()
    mod=args.mod_root.resolve()
    OUT.mkdir(parents=True,exist_ok=True)
    files=OUT/'files';assets=files/PREFIX
    assets.mkdir(parents=True,exist_ok=True)
    metadata=json.loads((HACK/'catalog.json').read_text())
    assert metadata['rom_sha256']=='51196cba923c315d0088b747b5cdee704f2ac057cd493f9ddf226fb7227302cf'
    assert sha(HACK/'catalog.json')=='fd8fbaf6eb4ee3774e3fe046bf3b506e7f638ab4cd9297c9f62a8bb1189bc740'
    source=next(m for m in metadata['maps']if m['id']=='g22_m000')
    assert source['pair']=='083df884_083df9a4'
    atlas_path=HACK/'pairs'/source['pair']/'flat.png'
    assert sha(atlas_path)=='05700b4aed1c3e20fe55735b9e56311485c838269052d7b007e8332ca35a4156'
    atlas=Image.open(atlas_path).convert('RGBA')
    def tile(mid):
        x,y=mid%16*16,mid//16*16
        return atlas.crop((x,y,x+16,y+16))
    middle=tile(673).crop((0,8,16,16))
    end=tile(666)
    assert source['grid'][6*source['width']+6]&1023==673
    assert source['grid'][7*source['width']+6]&1023==666
    assert len({middle.crop((0,y,16,y+1)).tobytes()for y in range(8)})==1
    # The two modules consist solely of counter pixels. No sampled native
    # cafe-floor color appears, so no color erasure or guessed mask is needed.
    native_floor_colors=set(tile(671).get_flattened_data())
    assert not native_floor_colors.intersection(middle.get_flattened_data())
    assert not native_floor_colors.intersection(end.get_flattened_data())
    whole=Image.new('RGBA',(16,64))
    for y in range(0,48,8):whole.alpha_composite(middle,(0,y))
    whole.alpha_composite(end,(0,48))
    assert whole.size==(16,64)
    assert sum(p[3]>0 for p in whole.get_flattened_data())==16*64
    (assets/'whole-counter16x48.png').unlink(missing_ok=True)
    whole.save(assets/'whole-counter16x64.png')
    whole.save(OUT/'counter-proposal-native.png')
    context_path=HACK/'maps/g22_m000-flat.png'
    context=Image.open(context_path).convert('RGBA')
    assert context.crop((96,104,112,112)).tobytes()==middle.tobytes()
    assert context.crop((96,112,112,128)).tobytes()==end.tobytes()
    context.save(OUT/'native-cafe-source-context.png')
    source_column=context.crop((96,80,112,128))
    source_column.save(OUT/'native-cafe-counter-column-context.png')
    proposal=Image.open(WORKSPACE/'.work/tileshift-v0443-checkpoint/gpu/forward-crystal/PLAYERS_HOUSE_1F-updated.png').convert('RGBA')
    proposal.alpha_composite(whole,(48,0))
    # Use the domestic author's current kitchen proposal for this review only.
    # No actor lies in its top-left six source cells.
    domestic_path=WORKSPACE/'.work/tileshift-newbark-crystaldust/domestic/kitchen-arranged-native.png'
    if domestic_path.exists():
        kitchen=Image.open(domestic_path).convert('RGBA')
        assert kitchen.size==(48,32)
        # The existing capture already supplies its wall and floor backing.
        for y in range(32):
            for x in range(48):
                if kitchen.getpixel((x,y))[3]:proposal.putpixel((x,y),kitchen.getpixel((x,y)))
    proposal.save(OUT/'room-proposal-native.png')
    sheet=Image.new('RGB',(1120,730),'#17212b')
    draw=ImageDraw.Draw(sheet)
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',23)
    small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',17)
    draw.text((16,12),'CrystalDust cafe counter divider proposal',font=font,fill='white')
    draw.text((16,49),'Exact native vertical middle pixels and one complete lower end. Integer zoom only.',font=small,fill='#c7d2de')
    draw.text((16,93),'Actual native cafe source',font=font,fill='white')
    enlarged=context.resize((context.width*2,context.height*2),Image.Resampling.NEAREST)
    sheet.paste(enlarged,(16,130),enlarged)
    draw.rectangle((16+96*2,130+104*2,16+112*2-1,130+128*2-1),outline='#ff6f50',width=2)
    draw.text((16,470),'Selected middle and complete end',font=small,fill='white')
    enlarged=middle.resize((96,48),Image.Resampling.NEAREST)
    sheet.paste(enlarged,(20,510),enlarged)
    enlarged=end.resize((96,96),Image.Resampling.NEAREST)
    sheet.paste(enlarged,(140,510),enlarged)
    draw.text((20,622),'673 lower 8px',font=small,fill='#c7d2de')
    draw.text((140,647),'666 entire 16px',font=small,fill='#c7d2de')
    draw.text((470,93),'Proposed player first floor',font=font,fill='white')
    enlarged=proposal.resize((proposal.width*4,proposal.height*4),Image.Resampling.NEAREST)
    sheet.paste(enlarged,(470,130),enlarged)
    draw.text((470,660),'Artwork proposal composed over prior native actor capture.',font=small,fill='#c7d2de')
    draw.text((470,688),'The counter covers the full source divider at x3, y0..3.',font=small,fill='#c7d2de')
    sheet.save(OUT/'divider-proposal.png')
    source_proof=dict(source='CrystalDust native Olivine Cafe counter',map='g22_m000',pair=source['pair'],
        rom_sha256=metadata['rom_sha256'],catalog_sha256=sha(HACK/'catalog.json'),
        native_map_png_sha256=sha(context_path),atlas_sha256=sha(atlas_path),
        metatiles_sha256=sha(atlas_path.parent/'metatiles.json'),
        modules=[dict(mid=673,map_cell=[6,6],source_cell_rect_xywh=[0,8,16,8],
                      source_atlas_rect_xywh=[16,680,16,8],rgba_sha256=pixels(middle),role='uniform native vertical middle',destinations=[[0,y]for y in range(0,48,8)]),
                 dict(mid=666,map_cell=[6,7],source_cell_rect_xywh=[0,0,16,16],
                      source_atlas_rect_xywh=[160,656,16,16],rgba_sha256=pixels(end),role='complete native lower cabinet/endcap',destinations=[[0,48]])],
        native_scale=1,rotation=False,redrawing=False,unique_endcap_repeated=False,
        output_size=[16,64],output_rgba_sha256=pixels(whole),
        north_end='Counter continues naturally through the existing north map boundary. No internal top/end border is repeated.',
        alpha='All 1024 selected pixels belong to the native counter. No donor floor occurs within the native 16px width; surrounding cells remain untouched.',
        target=dict(map='PLAYERS_HOUSE_1F',games=list(review.GAMES),cells=[[3,y]for y in range(4)],pixel_rect_xywh=[48,0,16,64]))
    (OUT/'source-provenance.json').write_text(json.dumps(source_proof,indent=2)+'\n')
    if args.proposal_only:
        print(json.dumps(dict(proposal=str(OUT/'divider-proposal.png'),rgba_sha256=pixels(whole))))
        return
    asset_paths=[]
    for y in range(4):
        relative=PREFIX/('counter-cell-0-'+str(y)+'.png')
        whole.crop((0,y*16,16,y*16+16)).save(files/relative)
        asset_paths.append(relative.as_posix())
    wall=dict(game='firered',tileset='player_house',id=40,hash='fd38c64864714cf6648e89dc3b28fa2ca879022c1d969074d488812eb23d6816')
    floor=dict(game='firered',tileset='player_house',id=1,hash='eba7bafe3b8bf236ae3602939529c34fad55c66c94aed6bb6cb4681b08fe2af6')
    rows=[]
    for game in review.GAMES:
        data=review.source(CACHE,game)
        m=data['maps']['PLAYERS_HOUSE_1F']
        for y in range(4):
            bid=m['blocks'][(y//2)*m['width']+1]
            q=(y%2)*2+1
            source_cell=review.cell_info(CACHE,game,data,m['tileset'],bid,q)
            assert source_cell['collision']==7
            row=dict(game=game,style='gen3',map='PLAYERS_HOUSE_1F',tileset=m['tileset'],id=bid,quadrant=q,
                x=3,y=y,sourceCells=[[3,y]],sourceHash=source_cell['sourceHash'],
                sourceFiles=data['fingerprints'][m['tileset']],sourceCollision=source_cell['collision'],
                sourcePriority=[bool(v.get('priority'))for v in source_cell['attributes']],
                sourcePalettes=[v.get('palette',1)for v in source_cell['attributes']],
                kind='third_party',asset=asset_paths[y],assetFileHash=sha(files/asset_paths[y]),
                base=copy.deepcopy(wall if y==0 else floor),status='reviewed',role='newbark_crystaldust_native_counter_divider',
                credit='CrystalDust / Sierraffinity and contributors; native cafe counter modules at original pixel scale.',
                sourceUrl='https://github.com/Sierraffinity/CrystalDust',
                evidence='User-approved CrystalDust16x64 vertical kitchen counter. Repeat only the uniform lower8px vertical middle of native cafeMID673 above one complete lower cabinet/endcapMID666. Native blue/white worktop and every end foot pixel retain1:1 geometry, palette and orientation; the northern continuation meets the existing map boundary. No floor pixels are copied from the cafe. Only player1F source cells3,0..3 are replaced, including its final native wall cell; original collision7, background interactions, NPCs, source geometry and warps stay unchanged.')
            row['compositionPixelHash']=pixels(Image.open(files/asset_paths[y]).convert('RGBA'))
            rows.append(row)
    module=files/MODULE
    module.parent.mkdir(parents=True,exist_ok=True)
    module.write_text('-- Native CrystalDust cafe-counter divider, scoped to four actual kitchen divider cells per GSC cartridge.\nreturn '+lua(rows)+'\n')
    assert preview.read_reviewed(module)==rows
    (OUT/'rows.json').write_text(json.dumps(rows,indent=2)+'\n')
    source_proof['files']={p.name:sha(p)for p in sorted(assets.glob('*.png'))}
    (assets/'provenance.json').write_text(json.dumps(source_proof,indent=2)+'\n')
    neutral=OUT/'neutral-mod'
    shutil.copytree(mod/'lib',neutral/'lib',dirs_exist_ok=True)
    shutil.copytree(files/'assets',neutral/'assets',dirs_exist_ok=True)
    neutral_proof=review.validate_batch(rows,SimpleNamespace(cache=CACHE,engine=WORKSPACE/'.work/tileshift-engine-0400',output=OUT),neutral)
    assert neutral_proof['rows_accepted']==12 and neutral_proof['rejected']==0
    result=dict(status='passed',rows=12,neutral=neutral_proof,map='PLAYERS_HOUSE_1F',games=list(review.GAMES),
                cells=[[3,y]for y in range(4)],source=source_proof,module_sha256=sha(module),
                renderer_launched=False,input_mod_modified=False,source_imports_modified=False)
    (OUT/'proof.json').write_text(json.dumps(result,indent=2)+'\n')
    integration=dict(mapping_stem=MODULE.stem,candidate=str(module),module_sha256=sha(module),
        assets=[dict(source=str(p),target=p.relative_to(files).as_posix(),sha256=sha(p))for p in sorted(assets.iterdir())if p.is_file()],
        tools=[dict(source=str(Path(__file__).resolve()),target='tools/author_newbark_crystaldust_divider.py',sha256=sha(Path(__file__)))],
        supersessions=[],rows=12,games=list(review.GAMES),map='PLAYERS_HOUSE_1F',
        placements=[[3,y]for y in range(4)],proof=str(OUT/'proof.json'))
    (OUT/'integration.json').write_text(json.dumps(integration,indent=2)+'\n')
    print(json.dumps(dict(status='passed',module_sha256=sha(module),rows=12,integration=str(OUT/'integration.json'))))


if __name__=='__main__':
    main()
