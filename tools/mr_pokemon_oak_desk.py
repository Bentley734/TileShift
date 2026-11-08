"""Author Mr. Pokemon's native CrystalDust machine, carpet and raised desk.

Run after the 0.46.1 Route 30 room authoring. Original collision, NPCs,
warps and interactions remain unchanged. Complete native modules stay at1:1.
"""
from __future__ import annotations
import argparse,copy,hashlib,json,os,re,sys
from pathlib import Path
from types import SimpleNamespace
WORKSPACE=next(p for p in Path(__file__).resolve().parents if(p/'.tools/python').is_dir()and(p/'.work').is_dir())
sys.path.insert(0,str(WORKSPACE/'.tools/python'))
from PIL import Image
MODULE='mappings/route30_mr_pokemon.lua'
FURNITURE='lib/johto_furniture.lua'
ROOFS='lib/johto_roofs.lua'
PC='assets/third_party/johto-hacks/newbark-cd-lab'
MACHINE='assets/third_party/johto-hacks/mr-pokemon-research-machine'
CONTEXT='assets/third_party/johto-hacks/mr-pokemon-research-floor'
MAP='MR_POKEMONS_HOUSE';GAMES=('gold','silver','crystal')
sha=lambda b:hashlib.sha256(b).hexdigest()
pixel=lambda im:sha(im.convert('RGBA').tobytes())

def canonical(v):
    if isinstance(v,dict):return{k:canonical(v[k])for k in sorted(v)}
    if isinstance(v,list):return[canonical(x)for x in v]
    return v

def artwork_clear(row):
    for field in('parts','donor','base','asset','assetFileHash','assetPixelHash','artOverlay','credit','sourceUrl','compositionPixelHash'):
        row.pop(field,None)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--mod-root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--engine',type=Path,default=WORKSPACE/'.work/tileshift-engine-0420')
    a=p.parse_args();base=a.baseline.resolve();mod=a.mod_root.resolve();out=a.output.resolve()
    assert base!=mod and out not in(base,mod)
    assert json.loads((base/'manifest.json').read_text())['version']=='0.46.1'
    sys.path.insert(0,str(mod/'tools'))
    import preview,gen2_extended_review as review,interior_review
    interior_review.WORKSPACE=WORKSPACE
    from interior_review import Imports
    from center_mart_overhang_review import write_rows
    from newbark_building_review import lua
    from lupa.luajit21 import LuaRuntime
    cache=Path(os.environ['APPDATA'])/'pokemon-love2d';imp=Imports(cache,WORKSPACE/'.work/tileshift-catalog')
    out.mkdir(parents=True,exist_ok=True)
    rows=preview.read_reviewed(base/MODULE);assert len(rows)==192
    oldrows=copy.deepcopy(rows)
    native=json.loads((mod/MACHINE/'provenance.json').read_text())
    for name,expected in native['files'].items():assert sha((mod/MACHINE/name).read_bytes())==expected,name
    carpet=native['carpet'];layout=carpet.get('layout',carpet.get('placement_grid'))
    assert len(layout)==4 and all(len(line)==6 for line in layout)
    complete_pc=Image.open(mod/PC/'wall-pc-whole32x26.png').convert('RGBA');assert complete_pc.size==(32,26)
    pc_padded=Image.new('RGBA',(32,32));pc_padded.alpha_composite(complete_pc,(0,6))
    for y in range(2):
        for x in range(2):
            image=Image.open(mod/PC/f'wall-pc-cell-{x}-{y}.png').convert('RGBA')
            assert image.tobytes()==pc_padded.crop((x*16,y*16,x*16+16,y*16+16)).tobytes()
    machine=Image.open(mod/MACHINE/'complete-native-machine.png').convert('RGBA')
    assert machine.size==(32,48)and machine.getbbox()==(0,9,32,48)
    context=mod/CONTEXT;context.mkdir(parents=True,exist_ok=True)
    context_proof=dict(format=1,origin='CrystalDust / Sierraffinity and contributors',
        sourceUrl='https://github.com/Sierraffinity/CrystalDust',
        recipe='Complete native carpet modules beneath intact native furniture foregrounds, at1:1 pixel scale.',
        files={},research_nook_compositions={})
    furniture=[];roofs=[];changed=[];sources=[]
    evidence=('Mr. Pokemon house only: complete native CrystalDust32x48 research machine sits at96,-16, '
        'with only its7px opaque cap extending above the original blocked32x32 corner. Native96x64 bluecarpet '
        'at32,48 repeats complete native edge/center modules under retained furniture. Complete32x26 desk '
        'moves16px north to96,54 with its physical front at y80; alpha-only foreground covers actors behind it. '
        'Oak remains at6,5 on native carpet, fully in front of the desk. Original source collision, NPCs, '
        'warps, story flags and interactions remain unchanged; every native artwork pixel stays1:1.')

    def asset(row,path,role,base_ref=None):
        artwork_clear(row)
        image=Image.open(mod/path).convert('RGBA')
        row.update(kind='third_party',asset=path,assetFileHash=sha((mod/path).read_bytes()),assetPixelHash=pixel(image),
            role=role,evidence=evidence,credit='CrystalDust by Sierraffinity and contributors; complete native modules at1:1.',
            sourceUrl='https://github.com/Sierraffinity/CrystalDust')
        if base_ref:row['base']=copy.deepcopy(base_ref)

    def compound(x,y,floor_path,foreground,foreground_recipe):
        ground=Image.open(mod/floor_path).convert('RGBA')
        assert ground.size==(16,16)and ground.getchannel('A').getextrema()==(255,255)
        if not foreground.getbbox():return floor_path
        whole=Image.alpha_composite(ground,foreground)
        assert all(not a[3]or a==b for a,b in zip(foreground.get_flattened_data(),whole.get_flattened_data()))
        name=f'research-nook-{x}-{y}.png';path=context/name
        if path.exists():assert Image.open(path).convert('RGBA').tobytes()==whole.tobytes()
        whole.save(path)
        context_proof['files'][name]=sha(path.read_bytes())
        record=dict(native_floor_asset=floor_path,native_floor_png_sha256=sha((mod/floor_path).read_bytes()),
            foreground_rgba_sha256=pixel(foreground),foreground_recipe=foreground_recipe,
            output_rgba_sha256=pixel(whole),canvas=[16,16],offset=[0,0],pixel_scale=1)
        prior=context_proof['research_nook_compositions'].setdefault(name,record);assert prior==record
        return CONTEXT+'/'+name

    def foreground(old):
        if old['kind']=='native':return Image.new('RGBA',(16,16))
        selected=copy.deepcopy(old);selected.pop('base',None)
        return preview.replacement_image(cache,selected,imp.packed,base)

    for game in GAMES:
        data=review.source(cache,game);md=data['maps'][MAP]
        sources.append(dict(game=game,definition_sha256=sha(json.dumps(md,sort_keys=True,separators=(',',':')).encode()),
            width=md['width'],height=md['height'],objects=md.get('objects',[]),bg_events=md.get('bgEvents',[])))
        selected={(r['x'],r['y']):r for r in rows if r['game']==game};anchor=copy.deepcopy(selected[6,4])
        assert anchor['id']==40 and anchor['quadrant']==0 and anchor['sourceCollision']==7
        floor=copy.deepcopy(anchor['base'])
        for y in range(8):
            for x in range(8):
                is_carpet=2<=x<=7 and 3<=y<=6
                is_machine=x in(6,7)and y in(0,1)
                if not(is_carpet or is_machine):continue
                row=selected[x,y];old=copy.deepcopy(row)
                info=review.cell_info(cache,game,data,md['tileset'],row['id'],row['quadrant'])
                assert info['sourceHash']==row['sourceHash']and info['collision']==row['sourceCollision']
                if is_machine:
                    assert row['sourceCollision']==7
                    if y==0:asset(row,f'{MACHINE}/machine-wall-{x-6}.png','route30_crystaldust_research_machine')
                    else:asset(row,f'{MACHINE}/machine-{x-6}-2.png','route30_crystaldust_research_machine',floor)
                else:
                    floor_path=MACHINE+'/'+layout[y-3][x-2]
                    if x in(6,7)and y in(3,4):
                        pc_path=f'{PC}/wall-pc-cell-{x-6}-{y-3}.png'
                        ink=Image.open(mod/pc_path).convert('RGBA')
                        path=compound(x,y,floor_path,ink,dict(asset=pc_path,assetFileHash=sha((mod/pc_path).read_bytes())))
                        asset(row,path,'route30_crystaldust_oak_workstation')
                        entry={k:copy.deepcopy(anchor[k])for k in('game','style','tileset','id','quadrant','sourceHash','sourceCollision','sourcePalettes','sourcePriority','sourceFiles')}
                        entry.update(kind='third_party',status='reviewed',map=MAP,anchorX=6,anchorY=4,x=x,y=y,frontY=80,
                            furniture='mr_pokemon_pc',role='route30_crystaldust_oak_workstation',asset=pc_path,
                            assetFileHash=sha((mod/pc_path).read_bytes()),assetPixelHash=pixel(ink),evidence=evidence,
                            credit=row['credit'],sourceUrl=row['sourceUrl'])
                        furniture.append(entry)
                    elif x in(6,7)and y==5:
                        assert row['sourceCollision']==0
                        asset(row,floor_path,'route30_oak_desk_clear_standing_carpet')
                    else:
                        ink=foreground(old)
                        recipe={k:old[k]for k in('kind','asset','assetFileHash','assetPixelHash','parts')if k in old}
                        path=compound(x,y,floor_path,ink,recipe)
                        asset(row,path,'route30_crystaldust_research_nook_floor')
                row['compositionPixelHash']=pixel(preview.replacement_image(cache,row,imp.packed,mod))
                changed.append(dict(game=game,xy=[x,y],source_id=row['id'],source_quadrant=row['quadrant'],
                    source_collision=row['sourceCollision'],before_row_sha256=sha(json.dumps(old,sort_keys=True,separators=(',',':')).encode()),
                    after_rgba_sha256=row['compositionPixelHash']))
        for x in(6,7):
            cap=copy.deepcopy(selected[x,0]);asset(cap,f'{MACHINE}/machine-{x-6}-0.png','route30_crystaldust_research_machine_cap')
            cap.update(x=x,y=-1,sourceY=0,buildingX=6,buildingY=0,buildingW=2,buildingH=2)
            cap['compositionPixelHash']=cap['assetPixelHash'];roofs.append(cap)
        actual_pc=Image.new('RGBA',(32,32))
        for y in(3,4):
            for x in(6,7):actual_pc.paste(preview.replacement_image(cache,selected[x,y],imp.packed,mod),((x-6)*16,(y-3)*16))
        assert all(not a[3]or a==b for a,b in zip(pc_padded.get_flattened_data(),actual_pc.get_flattened_data()))
        actual_machine=Image.new('RGBA',(32,48))
        for x in(6,7):
            actual_machine.paste(Image.open(mod/MACHINE/f'machine-{x-6}-0.png').convert('RGBA'),((x-6)*16,0))
            for y in(0,1):actual_machine.paste(preview.replacement_image(cache,selected[x,y],imp.packed,mod),((x-6)*16,(y+1)*16))
        assert all(not a[3]or a==b for a,b in zip(machine.get_flattened_data(),actual_machine.get_flattened_data()))
        for x in(6,7):
            expected=Image.open(mod/MACHINE/layout[2][x-2]).convert('RGBA')
            assert preview.replacement_image(cache,selected[x,5],imp.packed,mod).tobytes()==expected.tobytes()
    (context/'provenance.json').write_text(json.dumps(canonical(context_proof),indent=2)+'\n')
    write_rows(mod/MODULE,canonical(rows))
    for module,extra,marker in((FURNITURE,furniture,'MR POKEMON OAK DESK'),(ROOFS,roofs,'MR POKEMON RESEARCH MACHINE')):
        original=(base/module).read_bytes();tail=original[original.rfind(b'return rows'):]
        assert tail in(b'return rows\n',b'return rows\r\n')
        footer=('-- BEGIN '+marker+'\nfor _,row in ipairs((function()return '+lua(canonical(extra))+' end)())do rows[#rows+1]=row end\n-- END '+marker+'\nreturn rows\n').encode()
        (mod/module).write_bytes(original[:-len(tail)]+footer)
        before=preview.read_reviewed(base/module);after=preview.read_reviewed(mod/module)
        assert after[:-len(extra)]==before and len(after)==len(before)+len(extra)
    for before,after in zip(oldrows,rows):
        if not(2<=after['x']<=7 and 3<=after['y']<=6)and not(after['x']in(6,7)and after['y']in(0,1)):assert before==after
    runtime=LuaRuntime(unpack_returned_tuples=True);runtime.globals().readSource=lambda name:(mod/name).read_text()
    runtime.globals().paths=runtime.table_from(list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(mod/'main.lua').read_text()))))
    count=runtime.execute('''local rows={}for _,path in ipairs(paths)do for _,row in ipairs(assert(load(readSource(path),'@'..path))())do rows[#rows+1]=row end end
      local mapping=assert(load(readSource('lib/mapping.lua'),'@lib/mapping.lua'))();local index,errors=mapping.index(rows)
      assert(#errors==0,table.concat(errors,'\\n'));return #rows''')
    checks=review.validate_batch(rows,SimpleNamespace(cache=cache,engine=a.engine,output=out),mod)
    assert checks['rows_accepted']==192 and checks['rejected']==0
    report=dict(status='passed',scope=MAP,changed_cells=84,foreground_rows=12,north_overhang_rows=6,
        registered_mapping_rows=count,mapping_errors=0,validation=checks,complete_native_pc_size=[32,26],
        native_pc_rgba_sha256=pixel(complete_pc),native_pc_world_bounds=[96,54,128,80],padding_top=6,
        complete_native_machine_size=[32,48],native_machine_rgba_sha256=pixel(machine),
        native_machine_world_bounds=[96,-16,128,32],opaque_above_map_pixels=7,
        native_carpet_world_bounds=[32,48,128,112],artwork_scale=1,shift_north_pixels=16,
        oak_cell=[6,5],oak_carpet_exact=True,source_definitions=sources,changed=changed,
        every_other_mapping_furniture_and_roof_row_unchanged=True)
    (out/'proof.json').write_text(json.dumps(report,indent=2)+'\n')
    for game in GAMES:preview.map_preview(cache,out,game,MAP,game+'-oak-desk',rows,imp.packed,3,mod,roof_rows=[])
    print(json.dumps({k:v for k,v in report.items()if k not in('changed','source_definitions')},indent=2))

if __name__=='__main__':main()
