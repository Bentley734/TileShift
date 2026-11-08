"""Complete the two missing CrystalDust lighthouse side-window modules.

The adjacent intact window tier has byte-identical middle pieces, proving the
native 32px repeat. Reuse its complete left/right pieces at the missing tier.
"""
from pathlib import Path
import argparse,copy,json,os,sys
from types import SimpleNamespace

HERE=Path(__file__).resolve()
WORKSPACE=next(p for p in [Path.cwd(),*HERE.parents] if (p/'.tools/python').is_dir())
sys.path.insert(0,str(WORKSPACE/'.tools/python'))
from PIL import Image
import catalog,preview,gen2_extended_review as ext

MARKER=b'-- BEGIN COMPLETE NATIVE OLIVINE LIGHTHOUSE SIDE WINDOWS\n'

def key(row):
    return tuple(row.get(k)for k in('game','style','tileset','map','id','quadrant','x','y'))

def lua(value):
    if isinstance(value,str):return json.dumps(value,ensure_ascii=False)
    if isinstance(value,bool):return'true'if value else'false'
    if isinstance(value,(int,float)):return str(value)
    if isinstance(value,(list,tuple)):return'{'+','.join(lua(v)for v in value)+'}'
    return'{'+','.join('['+lua(k)+']='+lua(value[k])for k in sorted(value))+'}'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mod',type=Path,default=HERE.parents[1])
    p.add_argument('--cache',type=Path,default=Path(os.environ['APPDATA'])/'pokemon-love2d')
    p.add_argument('--engine',type=Path,default=WORKSPACE/'.work/tileshift-engine-0420')
    p.add_argument('--output',type=Path,default=WORKSPACE/'.work/tileshift-mart-shelf-fix/lighthouse-audit/review')
    p.add_argument('--activate',action='store_true')
    args=p.parse_args();mod=args.mod.resolve();args.output.mkdir(parents=True,exist_ok=True)
    target=mod/'mappings/olivine.lua';original=target.read_bytes();base=preview.read_reviewed(target)
    folder=mod/'assets/third_party/johto-hacks/exteriors'
    provenance=json.loads((folder/'provenance.json').read_text(encoding='utf-8'))
    images={}
    for x in range(4):
        for y in (6,8):
            path=folder/f'lighthouse-{x}-{y}.png'
            assert catalog.sha(path.read_bytes())==provenance['files'][path.name]
            images[x,y]=Image.open(path).convert('RGBA')
            assert images[x,y].size==(16,16)
    for x in (1,2):
        assert images[x,6].tobytes()==images[x,8].tobytes(),'Native middle window modules no longer prove this repeat'
    assert images[0,8].getchannel('A').getbbox()is None and images[3,8].getchannel('A').getbbox()is None
    assert images[0,6].getchannel('A').getbbox()==(8,0,16,16)
    assert images[3,6].getchannel('A').getbbox()==(0,0,8,16)
    for x in (0,3):assert sum(a==255 for a in images[x,6].getchannel('A').get_flattened_data())==128
    updates=[];packed={};unchanged=0
    for old in base:
        if old['game']not in ('gold','silver','crystal')or old.get('map')!='OLIVINE_CITY'or old.get('y')!=22 or old.get('x')not in (28,31):continue
        row=copy.deepcopy(old);x=old['x']-28
        assert row['kind']=='third_party'and row['sourceCollision']==7
        before_asset=f'assets/third_party/johto-hacks/exteriors/lighthouse-{x}-8.png'
        asset=f'assets/third_party/johto-hacks/exteriors/lighthouse-{x}-6.png'
        assert old['asset']in(before_asset,asset)
        row.update(asset=asset,assetFileHash=catalog.sha((mod/asset).read_bytes()),assetPixelHash=catalog.sha(images[x,6].tobytes()))
        evidence=('Complete native CrystalDust side-window module restores the two missing side cells at G/S/C28/31,22. '
          'The native middle cells1/2 of lighthouse tiers6 and8 are byte-identical; reuse intact tier6 left/right '
          'modules to complete this32px repeat at tier8. Every existing middle/front-window pixel is retained. '
          'No drawing, scaling, recoloring or new artwork; original64x224 tower, entrance29,27, source blocked '
          'collision7, map/events and source fingerprints remain unchanged. Exterior8px halves stay transparent '
          'over the selected existing ground; the missing128 building pixels per side use the original native window/shading.')
        if evidence not in row['evidence']:row['evidence']+=' '+evidence
        row['compositionPixelHash']=catalog.sha(preview.replacement_image(args.cache,row,packed,mod).tobytes())
        if row==old:unchanged+=1
        updates.append(row)
    assert len(updates)==6 and len({key(row)for row in updates})==6
    replacements={key(row):row for row in updates}
    changed=[replacements.get(key(row),row)for row in base]
    assert sum(a!=b for a,b in zip(base,changed))in(0,6)
    live=ext.validate_batch(updates,SimpleNamespace(cache=args.cache,engine=args.engine,output=args.output),mod)
    if unchanged==6:
        result=original
    else:
        assert MARKER not in original and original.rstrip().endswith(b'return rows')
        prefix=original.rstrip()[:-len(b'return rows')].rstrip()+b'\n'
        footer='''local fixed='''+lua(updates)+'''
local function lighthouseKey(row)return table.concat({row.game,row.style,row.tileset,row.map or '',row.id,row.quadrant,row.x or '',row.y or ''},':')end
local index={}for i,row in ipairs(rows)do index[lighthouseKey(row)]=i end
for _,row in ipairs(fixed)do rows[assert(index[lighthouseKey(row)],'Missing original lighthouse side cell')]=row end
return rows
'''
        result=prefix+MARKER+footer.encode('utf-8')
    expanded=catalog.plain(catalog.LUA.execute(result.decode('utf-8-sig')))
    assert {key(row):row for row in expanded}=={key(row):row for row in changed}
    assert len(expanded)==len(base)
    (args.output/'rows.json').write_text(json.dumps(updates,indent=2)+'\n',encoding='utf-8')
    report={'status':'reviewed_complete_native_lighthouse_side_windows','rows':6,'rows_per_game':2,
      'target_cells':[[28,22],[31,22]],'native_reused_asset_rows':6,'new_assets':0,
      'native_middle_modules_identical':True,'native_opaque_pixels_restored_per_game':256,
      'original_blocked_collision':7,'original_size':[64,224],'original_entrance':[29,27],
      'unrelated_rows_unchanged':len(base)-6,'source_guards_unchanged':True,'live_decoder':live,
      'mapping_sha256':catalog.sha(result),'activated':args.activate}
    if args.activate:target.write_bytes(result)
    (args.output/'proof.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
