"""Use complete native CrystalDust public booths and correct warehouse wall faces."""
from pathlib import Path
from types import SimpleNamespace
import argparse,copy,hashlib,json,os,re,sys
W=next(p for p in Path(__file__).resolve().parents if(p/'.tools/python').is_dir())
sys.path.insert(0,str(W/'.tools/python'))
from PIL import Image
SHA=lambda b:hashlib.sha256(b).hexdigest()
MODULE='mappings/johto_underground_finish.lua'
MARKER='COMPLETE NATIVE CRYSTALDUST UNDERGROUND FIXTURES'

def canonical(v):
    if isinstance(v,dict):return{k:canonical(x)for k,x in sorted(v.items())}
    if isinstance(v,list):return[canonical(x)for x in v]
    return v

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--catalog-dir',type=Path,required=True)
    p.add_argument('--mod-root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();base,cat,mod,out=(v.resolve()for v in(a.baseline,a.catalog_dir,a.mod_root,a.output))
    assert base!=mod;out.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(mod/'tools'))
    import preview,gen2_extended_review as review
    from newbark_building_review import lua
    plan=json.loads((mod/'tools/underground_fixture_plan.json').read_text())
    catalog=json.loads((cat/'catalog.json').read_text());assert plan['rom_sha256']==catalog['rom_sha256']=='51196cba923c315d0088b747b5cdee704f2ac057cd493f9ddf226fb7227302cf'
    cache=Path(os.environ['APPDATA'])/'pokemon-love2d';packed={}
    rows={path:preview.read_reviewed(base/path)for path in('mappings/johto_gate_finish.lua',MODULE)}
    fixes=[];scope=[];assets={};planes={};native_modules={}
    folder=mod/'assets/third_party/johto-hacks/crystaldust-underground-fixtures';folder.mkdir(parents=True,exist_ok=True)
    for game in('gold','silver','crystal'):
        data=review.source(cache,game)
        for r in plan['cells']:
            name=r['map'];x,y=r['xy'];md=data['maps'][name]
            bid=md['blocks'][y//2*md['width']+x//2];q=y%2*2+x%2
            module='mappings/johto_gate_finish.lua'if name=='GOLDENROD_UNDERGROUND'else MODULE
            matches=[(i,old)for i,old in enumerate(rows[module])if old['game']==game and old['style']=='gen3'
                     and old.get('map')==name and old['id']==bid and old['quadrant']==q
                     and(old.get('x')is None or(old['x']==x and old['y']==y))]
            assert matches,(game,name,x,y,bid,q)
            i,old=next(((i,v)for i,v in matches if v.get('x')is not None),matches[-1])
            cell=review.cell_info(cache,game,data,md['tileset'],bid,q)
            assert old['sourceHash']==cell['sourceHash'] and old['sourceCollision']==cell['collision']
            pair=r['native_pair'];mid=r['native_mid'];box=(mid%16*16,mid//16*16,mid%16*16+16,mid//16*16+16)
            if pair not in planes:planes[pair]=[Image.open(cat/'pairs'/pair/(n+'.png')).convert('RGBA')for n in('bottom','top')]
            bottom,top=planes[pair];image=Image.alpha_composite(bottom.crop(box),top.crop(box))
            assert image.size==(16,16)and all(v[3]==255 for v in image.get_flattened_data())
            key=pair+':'+str(mid);native_modules[key]={'pair':pair,'mid':mid,'planes':['bottom','top'],'atlas_xyxy':box,
                'bottom_atlas_sha256':SHA((cat/'pairs'/pair/'bottom.png').read_bytes()),'top_atlas_sha256':SHA((cat/'pairs'/pair/'top.png').read_bytes()),'RGBA_sha256':SHA(image.tobytes()),'opaque_pixels':256}
            pixel=SHA(image.tobytes());filename='cell-'+pixel[:20]+'.png';path=folder/filename
            if filename not in assets:
                image.save(path);assets[filename]={'asset':path.relative_to(mod).as_posix(),'assetFileHash':SHA(path.read_bytes()),'assetPixelHash':pixel,'native_size':[16,16],'native_scale':1,'native_modules':[]}
            art=assets[filename]
            if key not in art['native_modules']:art['native_modules'].append(key)
            new=copy.deepcopy(old)
            for field in('parts','donor','base','animated','animation','frames','assetFrames','foreground','occludes','artOverlay','flora','asset','assetFileHash','assetPixelHash','compositionPixelHash','canopy','overMask'):new.pop(field,None)
            new.update(x=x,y=y,sourceCells=[[x,y]],kind='third_party',status='reviewed',asset=art['asset'],assetFileHash=art['assetFileHash'],assetPixelHash=pixel,compositionPixelHash=pixel,
                       role='crystaldust_public_booth_'+str(mid)if name=='GOLDENROD_UNDERGROUND'else'crystaldust_warehouse_wall_'+str(mid),
                       credit='Pokemon CrystalDust / Sierraffinity and DoMoreAwesome Games',sourceUrl='https://github.com/Sierraffinity/CrystalDust',
                       evidence='Whole native CrystalDust BOTTOM+TOP at1:1. Public booth retains all three native surface/body/foot modules599/607/606. Warehouse replaces repeated corner caps with genuine straight faces and correct native top corners. Original crates, floor, maze/doors/switches, callbacks, NPCs, collision, warps and scripts remain unchanged.')
            assert SHA(preview.replacement_image(cache,new,packed,mod).tobytes())==pixel
            fixes.append(canonical(new));scope.append({'game':game,'map':name,'xy':[x,y],'source_module':module,'source_index':i,'old_row':old,'candidate_row':new,'native_pair':pair,'native_mid':mid})
    keys=[(r['game'],r['map'],r['id'],r['quadrant'],r['x'],r['y'])for r in fixes]
    assert len(keys)==len(set(keys))==81
    replacement_keys={(r['game'],r['map'],r['id'],r['quadrant'],r.get('x'),r.get('y'))for r in rows[MODULE]if r.get('x')is not None}
    replacements=[r for r,k in zip(fixes,keys)if k in replacement_keys]
    additions=[r for r,k in zip(fixes,keys)if k not in replacement_keys]
    assert len(replacements)==45 and len(additions)==36
    raw=(base/MODULE).read_bytes();tail=re.search(br'\r?\nreturn rows\s*$',raw);assert tail and MARKER.encode()not in raw
    code='\n-- BEGIN '+MARKER+'\ndo\nlocal replacements='+lua(canonical(replacements))+'''
local function key(r)return r.game..':'..r.map..':'..r.id..':'..r.quadrant..':'..r.x..':'..r.y end
local lookup={};for _,r in ipairs(replacements)do assert(not lookup[key(r)]);lookup[key(r)]=r end
local n=0
for i,r in ipairs(rows)do if r.x~=nil then local fix=lookup[key(r)];if fix then rows[i]=fix;n=n+1 end end end
assert(n==45,'Underground native positioned source scope changed')
for _,r in ipairs('''+lua(canonical(additions))+''')do rows[#rows+1]=r end
end
-- END '''+MARKER+'\nreturn rows\n'
    if b'\r\n'in raw:code=code.replace('\n','\r\n')
    (mod/MODULE).write_bytes(raw[:tail.start()]+code.encode())
    validation=review.validate_batch(fixes,SimpleNamespace(cache=cache,engine=W/'.work/tileshift-engine-0420'),mod)
    assert validation['rows_accepted']==81 and validation['rejected']==0
    provenance={'origin':'Whole native CrystalDust Underground fixtures and warehouse walls','rom_sha256':plan['rom_sha256'],'credit':'Sierraffinity / DoMoreAwesome Games','sourceUrl':'https://github.com/Sierraffinity/CrystalDust','native_scale':1,'native_modules':native_modules,'source_modules':assets,
                'processing':'Use complete BOTTOM+TOP modules, with every native object pixel retained. No resizing/cropping/recoloring or invented pixels. Booth is the complete16x48 three-module assembly; warehouse tiles are exact full16px faces/corners.'}
    (folder/'provenance.json').write_text(json.dumps(canonical(provenance),indent=2)+'\n',encoding='utf8')
    proof={'status':'passed','physical_source_cells':81,'new_positioned_rows':36,'exact_existing_positioned_supersessions':45,'scope':scope,'native_validation':validation,'native_modules':native_modules,'assets':assets,'native_scale':1,'all_unselected_rows_and_source_gameplay_unchanged':True}
    (out/'proof.json').write_text(json.dumps(canonical(proof),indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in proof.items()if k not in('scope','assets','native_modules')}))

if __name__=='__main__':main()
