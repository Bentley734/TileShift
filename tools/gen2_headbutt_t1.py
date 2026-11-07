"""Prepare the user-selected T1 artwork for existing GSC Headbutt-tree rows.

Private output only. Reads the published v0.44.3 frozen source; never edits its
input. No chooser, preferences, catalog, runtime, collision or script changes.
"""
from pathlib import Path
from collections import Counter, defaultdict
from types import SimpleNamespace
import argparse
import copy
import hashlib
import json
import os
import shutil
import sys

W = next(p for p in Path(__file__).resolve().parents if (p/'.tools/python').is_dir() and (p/'.work/tileshift-firegold').is_dir())
FROZEN = json.loads((W/'.work/tileshift-v0443-checkpoint/frozen.json').read_text())
PARSER = argparse.ArgumentParser(description=__doc__)
PARSER.add_argument('--mod-root',type=Path,default=Path(FROZEN['stage']))
PARSER.add_argument('--output',type=Path,default=W/'.work/tileshift-tree-chooser/t1-only')
ARGS = PARSER.parse_args()
MOD, OUT = ARGS.mod_root.resolve(), ARGS.output.resolve()
assert not OUT.is_relative_to(MOD)
sys.path.insert(0,str(W/'.tools/python'))
sys.path.insert(0,str(MOD/'tools'))
from PIL import Image
import catalog
import preview
import gen2_extended_review as review
from newbark_building_review import lua

CACHE = Path(os.environ['APPDATA'])/'pokemon-love2d'
OPTION_DIR = W/'.work/tileshift-newbark-tree-options'
HACK = W/'.work/tileshift-firegold/crystaldust'
ASSET_DIR = Path('assets/third_party/johto-hacks/headbutt-t1')
ASSET = ASSET_DIR/'t1-mint-round-shrub.png'
T1_RGBA = 'a8e8d7ca53f4c23b11e6081b1aae0993045e2301c607d50df638bb94cf67dc0a'
MODULES = ('gen2_outdoor.lua','gen2_outdoor_extended.lua','johto_dragonden_finish.lua','johto_shared_finish.lua')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def semantic(row):
    return hashlib.sha256(json.dumps(row,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def dump(path,value):
    Path(path).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')


def row_spans(text):
    spans, depth, quoted, escaped, start = [], 0, None, False, None
    for index,char in enumerate(text):
        if quoted:
            if escaped:
                escaped=False
            elif char=='\\':
                escaped=True
            elif char==quoted:
                quoted=None
        elif char in ('"',"'"):
            quoted=char
        elif char=='{':
            depth+=1
            if depth==2:
                start=index
        elif char=='}':
            if depth==2:
                spans.append((start,index+1))
            depth-=1
    assert depth==0 and quoted is None
    return spans


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    files=OUT/'files'
    folder=files/ASSET_DIR
    folder.mkdir(parents=True,exist_ok=True)
    options=json.loads((OPTION_DIR/'provenance.json').read_text())
    choice=next(r for r in options['options'] if r['id']=='T1')
    assert choice['native_sprite_size']==[16,16] and choice['isolated_rgba_sha256']==T1_RGBA
    metadata=json.loads((HACK/'catalog.json').read_text())
    assert metadata['rom_sha256']=='51196cba923c315d0088b747b5cdee704f2ac057cd493f9ddf226fb7227302cf'
    atlas_path=HACK/'pairs'/choice['pair']/'top.png'
    assert choice['pair']=='083df704_083df7c4' and choice['source_metatile_grid']==[[198]]
    assert sha(atlas_path)==choice['source_foreground_atlas_sha256']
    atlas=Image.open(atlas_path).convert('RGBA')
    x,y=198%16*16,198//16*16
    sprite=atlas.crop((x,y,x+16,y+16))
    original_foreground_hash=hashlib.sha256(sprite.tobytes()).hexdigest()
    assert original_foreground_hash==choice['foreground_rgba_sha256']
    assert choice['exterior_ground_mask_xy']==[[5,15],[10,15]]
    for px,py in choice['exterior_ground_mask_xy']:
        assert sprite.getpixel((px,py))==(66,181,140,255)
        sprite.putpixel((px,py),(0,0,0,0))
    source_png=Path(choice['isolated_png'])
    assert sha(source_png)==choice['isolated_png_sha256']
    assert sprite.tobytes()==Image.open(source_png).convert('RGBA').tobytes()
    assert hashlib.sha256(sprite.tobytes()).hexdigest()==T1_RGBA
    assert sum(p[3]>0 for p in sprite.get_flattened_data())==170
    shutil.copyfile(source_png,files/ASSET)
    png_hash=sha(files/ASSET)
    all_new, changes, module_records, placements = [], [], [], set()
    scenes=defaultdict(set)
    data_by_game={}
    protected_change_keys={'kind','parts','asset','assetFileHash','assetPixelHash','compositionPixelHash','credit','sourceUrl','evidence'}
    for name in MODULES:
        relative=Path('mappings')/name
        original_path=MOD/relative
        assert sha(original_path)==FROZEN['source_files'][relative.as_posix()]
        original=original_path.read_bytes()
        text=original.decode('utf-8')
        original_text=text
        rows=preview.read_reviewed(original_path)
        spans=row_spans(text)
        assert len(spans)==len(rows)
        updated=copy.deepcopy(rows)
        local=[]
        for index,old in enumerate(rows):
            if old.get('game') not in review.GAMES or old.get('style')!='gen3' or old.get('role')!='headbutt_small_tree':
                continue
            game=old['game']
            if game not in data_by_game:
                data_by_game[game]=review.source(CACHE,game)
            source=data_by_game[game]
            cell=review.cell_info(CACHE,game,source,old['tileset'],old['id'],old['quadrant'])
            assert old['sourceHash']==cell['sourceHash'] and old['sourceCollision']==cell['collision']==21
            assert old['sourceFiles']==source['fingerprints'][old['tileset']]
            if 'sourcePriority' in old:
                assert old['sourcePriority']==[bool(a.get('priority'))for a in cell['attributes']]
            if 'sourcePalettes' in old:
                assert old['sourcePalettes']==[a.get('palette',1)for a in cell['attributes']]
            assert old['kind']=='native_composite' and old.get('base') and old.get('parts')
            assert not any(k in old for k in ('animation','animated','foreground','occludes','canopy','donor'))
            new=copy.deepcopy(old)
            new.pop('parts')
            new.pop('assetPixelHash',None)
            new.update(kind='third_party',asset=ASSET.as_posix(),assetFileHash=png_hash,
                credit='CrystalDust / Sierraffinity and contributors; native T1 mint round shrub.',
                sourceUrl='https://github.com/Sierraffinity/CrystalDust',
                evidence='User-selected T1 replaces only this existing small Headbutt-tree artwork. Complete native CrystalDust metatile198 foreground16x16, including crown and base shadow, retained at1:1 with exact native transparency. Existing selected ground, source Headbutt collision0x15, encounter behavior, whole-frame native shake, map layout, NPCs, events and source fingerprints remain unchanged. No Cut mechanic or chooser change.')
            base=preview.native_donor(CACHE,new['base'],{})
            composed=Image.alpha_composite(base,sprite)
            new['compositionPixelHash']=hashlib.sha256(composed.tobytes()).hexdigest()
            assert {k:v for k,v in old.items() if k not in protected_change_keys}=={k:v for k,v in new.items() if k not in protected_change_keys}
            definition=source['maps'][old['map']]
            actual=[]
            for position,bid in enumerate(definition['blocks']):
                if bid!=old['id']:
                    continue
                xx=position%definition['width']*2+old['quadrant']%2
                yy=position//definition['width']*2+old['quadrant']//2
                if old.get('x') is None or (old['x'],old['y'])==(xx,yy):
                    actual.append([xx,yy])
                    placements.add((game,old['map'],xx,yy))
                    scenes[game,old['map']].add((xx,yy))
            assert actual, 'Existing Headbutt row has no actual body use'
            changed=dict(module=relative.as_posix(),index=index,old_row=old,new_row=new,
                old_row_sha256=semantic(old),new_row_sha256=semantic(new),actual_cells=actual)
            updated[index]=new
            local.append(changed)
            changes.append(changed)
            all_new.append(new)
        assert local
        # Only selected row-literal spans change; every byte between them stays
        # exact, including unrelated rows, comments, wrappers and line endings.
        for change in reversed(local):
            start,end=spans[change['index']]
            canonical=json.loads(json.dumps(change['new_row'],sort_keys=True))
            text=text[:start]+lua(canonical)+text[end:]
        target=files/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(text.encode('utf-8'))
        assert preview.read_reviewed(target)==updated
        new_spans=row_spans(text)
        assert len(new_spans)==len(spans)
        changed_indexes={c['index']for c in local}
        for index in range(len(rows)):
            if index not in changed_indexes:
                a,b=spans[index]
                c,d=new_spans[index]
                assert original_text[a:b]==text[c:d]
        module_records.append(dict(source=str(target),target=relative.as_posix(),old_sha256=sha(original_path),
            new_sha256=sha(target),changed_rows=len(local),all_unrelated_row_bytes_unchanged=True))
    assert len(changes)==783 and len(placements)==3108 and len(scenes)==74
    counts=dict(Counter(r['game']for r in all_new))
    assert counts=={'gold':257,'silver':257,'crystal':269}
    # Exact frozen neutral libraries and the one proposed asset suffice for
    # independent source/hash/composition validation; no runtime is modified.
    neutral=OUT/'neutral-mod'
    shutil.copytree(MOD/'lib',neutral/'lib',dirs_exist_ok=True)
    (neutral/ASSET_DIR).mkdir(parents=True,exist_ok=True)
    shutil.copyfile(files/ASSET,neutral/ASSET)
    validation_rows=copy.deepcopy(all_new)
    for row in validation_rows:
        row.setdefault('sourceCells',{})
    accepted=review.validate_batch(validation_rows,SimpleNamespace(cache=CACHE,
        engine=W/'.work/tileshift-engine-0400',output=OUT),neutral)
    assert accepted['rows_accepted']==783 and accepted['rejected']==0
    provenance=dict(origin='User-selected T1 native CrystalDust mint round shrub for existing GSC Headbutt trees only.',
        credit='CrystalDust / Sierraffinity and contributors.',sourceUrl='https://github.com/Sierraffinity/CrystalDust',
        source_rom_name=metadata['rom_name'],source_rom_sha256=metadata['rom_sha256'],
        source_choice='T1',source_pair=choice['pair'],source_metatile=198,source_layer='top',
        source_atlas_sha256=sha(atlas_path),source_atlas_rect_xywh=[x,y,16,16],
        source_map=choice['source_map'],source_origin_cells=choice['source_origin_cells'],
        source_map_png_sha256=choice['source_map_png_sha256'],source_metatiles_json_sha256=choice['source_metatiles_json_sha256'],
        native_dimensions=[16,16],pixel_scale=1,native_rgba_sha256=T1_RGBA,opaque_pixels=170,
        exact_native_art_pixels=True,original_foreground_rgba_sha256=original_foreground_hash,
        exterior_field_pixels_made_transparent=choice['exterior_ground_mask_xy'],
        exterior_field_color=[66,181,140,255],removed_foliage_pixels=0,
        resampling=False,redrawing=False,source_behavior='Existing Headbutt collision0x15 and all native mechanics unchanged.',
        chooser_changed=False,runtime_changed=False,existing_bases_preserved=True,
        files={ASSET.name:png_hash})
    dump(folder/'provenance.json',provenance)
    dump(OUT/'replacement-manifest.json',changes)
    dump(OUT/'changed-keys.json',[{k:r.get(k)for k in ('game','style','map','tileset','id','quadrant','x','y')}for r in all_new])
    affected=[dict(game=g,map=m,cells=[list(c)for c in sorted(cells,key=lambda p:(p[1],p[0]))],count=len(cells))for (g,m),cells in sorted(scenes.items())]
    dump(OUT/'affected-scenes.json',affected)
    proof=dict(status='passed',modified_rows=783,actual_source_cells=3108,game_map_scenes=74,rows_by_game=counts,
        placements_by_game=dict(Counter(g for g,m,x,y in placements)),source_collision_values=[21],
        all_source_guards_and_bases_unchanged=True,all_unrelated_row_bytes_unchanged=True,
        no_runtime_catalog_or_preferences_changes=True,neutral=accepted,source_rgba_sha256=T1_RGBA,
        baseline_source=str(MOD),modules=module_records,
        files={p.relative_to(files).as_posix():sha(p)for p in files.rglob('*')if p.is_file()},
        limits='Neutral source/import/composition validation; root owns native whole-map and Headbutt playback checks.')
    dump(OUT/'proof.json',proof)
    integration=dict(kind='existing_module_replacements',modules=module_records,
        assets=[dict(source=str(p),target=p.relative_to(files).as_posix(),sha256=sha(p))for p in sorted(folder.iterdir())if p.is_file()],
        tools=[dict(source=str(Path(__file__).resolve()),target='tools/gen2_headbutt_t1.py',sha256=sha(Path(__file__)))],
        replacement_manifest=str(OUT/'replacement-manifest.json'),changed_keys=str(OUT/'changed-keys.json'),
        affected_scenes=str(OUT/'affected-scenes.json'),proof=str(OUT/'proof.json'),
        modified_rows=783,actual_source_cells=3108,no_new_mapping_module=True,no_chooser_or_runtime_change=True)
    dump(OUT/'integration.json',integration)
    print(json.dumps(dict(status='passed',rows=783,cells=3108,scenes=74,modules=[(r['target'],r['changed_rows'])for r in module_records],asset_sha256=png_hash)))


if __name__=='__main__':
    main()
