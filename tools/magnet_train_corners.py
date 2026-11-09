"""Expose existing station rails only outside the native Magnet Train hull."""
from pathlib import Path
import argparse,copy,hashlib,json,os,re,sys
W=next(p for p in Path(__file__).resolve().parents if(p/'.tools/python').is_dir());sys.path.insert(0,str(W/'.tools/python'))
from PIL import Image
SHA=lambda b:hashlib.sha256(b).hexdigest()
PROFILE=(23,19,17,15,12,10,8,7,4,3,2,1,1)+(0,)*11+(1,1,2,3)+(0,)*4
MODULES={'mappings/johto_unique_objects_finish.lua':'GOLDENROD_MAGNET_TRAIN_STATION','mappings/gen2_kanto_facilities_finish.lua':'SAFFRON_MAGNET_TRAIN_STATION'}
MARKER='EXTERIOR ONLY MAGNET TRAIN CORNERS'

def canonical(v):
    if isinstance(v,dict):return{k:canonical(x)for k,x in sorted(v.items())}
    if isinstance(v,list):return[canonical(x)for x in v]
    return v

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--mod-root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    base,mod,out=(v.resolve()for v in(a.baseline,a.mod_root,a.output));assert base!=mod;out.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(mod/'tools'));import preview,gen2_extended_review as review
    cache=Path(os.environ['APPDATA'])/'pokemon-love2d';packed={};assets={};scope=[];fixed_all=[];groups=[]
    folder=mod/'assets/third_party/johto-hacks/magnet-train-corners';folder.mkdir(parents=True,exist_ok=True)
    mask=Image.new('L',(160,32));mask_pixels=[]
    for y,n in enumerate(PROFILE):
        for x in list(range(n))+list(range(160-n,160)):mask.putpixel((x,y),255);mask_pixels.append([x,y])
    assert len(mask_pixels)==258 and all(mask.getpixel((x,y))==0 for y in range(28,32)for x in range(160))
    underlays=[]
    for phase in(0,1):
        name=f'assets/third_party/metalflygon08/rail-cell-0-{phase}.png';path=base/name;image=Image.open(path).convert('RGBA');assert image.size==(16,16)and all(z[3]==255 for z in image.get_flattened_data())
        assert path.read_bytes()==(mod/name).read_bytes();underlays.append((image,dict(asset=name,assetFileHash=SHA(path.read_bytes()),assetPixelHash=SHA(image.tobytes()))))
    for module,mapname in MODULES.items():
        rows=preview.read_reviewed(base/module);fixed=[]
        for game in('gold','silver','crystal'):
            selected=[r for r in rows if r.get('game')==game and r.get('map')==mapname and r.get('role')=='johto_recolored_magnet_train'];assert len(selected)==20
            byxy={tuple(r['sourceCells'][0]):r for r in selected};assert set(byxy)=={(x,y)for y in(4,5)for x in range(4,14)}
            whole=Image.new('RGBA',(160,32));foreground=whole.copy();after=whole.copy()
            for xy,old in byxy.items():
                x,y=xy;assert old['kind']=='source_palette'and 'x'not in old and'y'not in old and old['sourcePriority']==[False]*4
                source=preview.replacement_image(cache,old,packed,base);whole.paste(source,((x-4)*16,(y-4)*16))
            foreground=whole.copy()
            for x,y in mask_pixels:foreground.putpixel((x,y),whole.getpixel((x,y))[:3]+(0,))
            assert sum(z[3]!=0 for z in foreground.get_flattened_data())==4862
            for x in range(160):
                for y in range(32):
                    if not mask.getpixel((x,y)):assert foreground.getpixel((x,y))==whole.getpixel((x,y))
            for xy,old in sorted(byxy.items()):
                x,y=xy;box=((x-4)*16,(y-4)*16,(x-3)*16,(y-3)*16);localmask=mask.crop(box);part=foreground.crop(box)
                if not localmask.getbbox():after.paste(part,((x-4)*16,(y-4)*16));continue
                underlay,underlay_proof=underlays[y-4];image=Image.alpha_composite(underlay,part);pixel=SHA(image.tobytes());name=f'corner-{x}-{y}.png';path=folder/name
                if name not in assets:
                    image.save(path);assets[name]=dict(asset=path.relative_to(mod).as_posix(),assetFileHash=SHA(path.read_bytes()),assetPixelHash=pixel,native_size=[16,16],native_scale=1,world_xy=list(xy),whole_train_xy=[(x-4)*16,(y-4)*16],
                        exterior_mask=''.join('1'if a else'0'for a in localmask.get_flattened_data()),exterior_pixels=sum(a!=0 for a in localmask.get_flattened_data()),transparent_foreground_RGBA_sha256=SHA(part.tobytes()),rail_underlay=underlay_proof)
                art=assets[name];assert art['assetPixelHash']==pixel
                new=copy.deepcopy(old);new.pop('sourceColors');new.update(kind='third_party',x=x,y=y,asset=art['asset'],assetFileHash=art['assetFileHash'],assetPixelHash=pixel,compositionPixelHash=pixel,
                    role='magnet_train_exterior_corner_over_matching_rail',credit='Native Pokemon Gold/Silver/Crystal train pixels and existing reviewed recolor; MetalFlygon08 native Johto rail artwork.',sourceUrl='https://github.com/pret/pokecrystal',
                    evidence='Exact existing native train recolor preserved within the explicit source silhouette. Only the reviewed exterior corner pixels become transparent in the private foreground, then are precomposed over the unchanged native public rail tile of the same row phase. No hull, windows, doors, rim, shading or lower shadow-band pixel changes; full source guards, actors, collisions, boarding and separate ride cutscene remain unchanged. Position-specific original source cell only.')
                assert SHA(preview.replacement_image(cache,new,packed,mod).tobytes())==pixel;fixed.append(canonical(new));fixed_all.append(canonical(new));after.paste(image,((x-4)*16,(y-4)*16))
                scope.append(dict(module=module,game=game,map=mapname,x=x,y=y,xy=list(xy),id=old['id'],quadrant=old['quadrant'],sourceHash=old['sourceHash'],sourceFiles=old['sourceFiles'],sourceCollision=old['sourceCollision'],sourcePriority=old['sourcePriority'],sourcePalettes=old['sourcePalettes'],
                    original_row=old,original_row_sha256=SHA(json.dumps(canonical(old),separators=(',',':')).encode()),candidate_row=new,old_RGBA_sha256=SHA(whole.crop(box).tobytes()),new_RGBA_sha256=pixel,exterior_pixels=art['exterior_pixels']))
            assert len([r for r in fixed if r['game']==game])==6
            for y in range(32):
                for x in range(160):
                    if not mask.getpixel((x,y)):assert after.getpixel((x,y))==whole.getpixel((x,y))
            prefix=game+'-'+mapname;whole.save(out/(prefix+'-before.png'));foreground.save(out/(prefix+'-transparent-foreground.png'));after.save(out/(prefix+'-after.png'))
            groups.append(dict(game=game,map=mapname,whole_size=[160,32],whole_before_RGBA_sha256=SHA(whole.tobytes()),whole_foreground_RGBA_sha256=SHA(foreground.tobytes()),whole_after_RGBA_sha256=SHA(after.tobytes()),exterior_pixels=258,retained_pixels=4862,lower_shadow_rows28to31_exact=True))
        assert len(fixed)==18
        raw=(base/module).read_bytes();assert MARKER.encode()not in raw;tail=re.search(br'\r?\nreturn rows\s*$',raw);assert tail
        compact=review.write_compact(fixed,None)[0];text='\n-- BEGIN '+MARKER+'\ndo\nlocal fixes=(function()\n'+compact+'\nend)()\nassert(#fixes==18,"Magnet Train corner source scope changed")\nfor _,r in ipairs(fixes)do assert(r.x==r.sourceCells[1][1]and r.y==r.sourceCells[1][2],"Magnet Train corner position changed");rows[#rows+1]=r end\nend\n-- END '+MARKER+'\nreturn rows\n'
        suffix=text.encode('utf8');suffix=suffix.replace(b'\n',b'\r\n')if b'\r\n'in raw else suffix;(mod/module).write_bytes(raw[:tail.start()]+suffix)
    assert len(assets)==6 and len(fixed_all)==36 and len({g['whole_before_RGBA_sha256']for g in groups})==1 and len({g['whole_after_RGBA_sha256']for g in groups})==1
    provenance=dict(origin='Six bounded native train-corner composites; full imported train images remain private authoring proofs only.',native_scale=1,train_source='User-provided native Pokemon Gold/Silver/Crystal imported TILESET_TRAIN_STATION, with the existing reviewed sourceColors recolor.',sourceUrl='https://github.com/pret/pokecrystal',rail_credit='MetalFlygon08',rail_sourceUrl='https://imgur.com/gallery/testing-out-gen-3-style-tiles-johto-6A43Cji',
        processing='Explicit symmetric exterior profile, never a color flood or global palette key. Preserve every one of the4,862 unmasked pixels and all lower shadow rows28..31. Set alpha0 on exactly258 outside corner pixels; precompose the six affected cells onto the unchanged existing public rail PNG upper/lower phase. No resize, redraw, enclosed-hole clearing, background scan at runtime, main/library/API or ride cutscene changes.',whole_native_size=[160,32],exterior_width_by_row=list(PROFILE),exterior_pixels=258,retained_pixels=4862,groups=groups,source_modules=assets)
    (folder/'provenance.json').write_text(json.dumps(canonical(provenance),indent=2)+'\n',encoding='utf8')
    from types import SimpleNamespace
    validation=review.validate_batch(fixed_all,SimpleNamespace(cache=cache,engine=W/'.work/tileshift-engine-0420'),mod);assert validation['rows_accepted']==36 and validation['rejected']==0
    proof=dict(status='passed',added_positioned_rows=36,physical_source_cells=36,all_baseline_regular_rows_retained=True,no_main_runtime_or_library_changes=True,whole_size=[160,32],exterior_width_by_row=list(PROFILE),exterior_pixels_per_train=258,retained_pixels_per_train=4862,entire_lower_shadow_rows28to31_retained=True,groups=groups,selected_source_cells=scope,native_validation=validation)
    (out/'proof.json').write_text(json.dumps(canonical(proof),indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in proof.items()if k not in('selected_source_cells','groups')}))

if __name__=='__main__':main()
