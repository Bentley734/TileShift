"""Reproduce Kurt's complete native CrystalDust pegboard and L workbench.

Preserve native TOP hardware, a complete bottom-plane shaft module, and the
complete framed pegboard. Generic exterior room-wall pixels are transparent;
the distinct native chair is excluded as a whole module at Kurt's source seat.
"""
from pathlib import Path
import argparse,copy,hashlib,json,os,re,sys
W=next(p for p in Path(__file__).resolve().parents if(p/'.tools/python').is_dir())
sys.path.insert(0,str(W/'.tools/python'))
from PIL import Image
SHA=lambda b:hashlib.sha256(b).hexdigest()
ROM='51196cba923c315d0088b747b5cdee704f2ac057cd493f9ddf226fb7227302cf'
PAIR='083df884_083dfb6c'
START='-- BEGIN COMPLETE NATIVE KURT WORKBENCH'
END='-- END COMPLETE NATIVE KURT WORKBENCH'

def canonical(v):
    if isinstance(v,dict):return{k:canonical(x)for k,x in sorted(v.items())}
    if isinstance(v,list):return[canonical(x)for x in v]
    return v

def footer(path,body):
    data=path.read_text(encoding='utf8')
    data=re.sub(r'\n'+re.escape(START)+r'.*?'+re.escape(END)+r'\n','\n',data,flags=re.S)
    tail=re.search(r'\nreturn rows\s*$',data);assert tail,path
    path.write_text(data[:tail.start()]+'\n'+START+'\n'+body+'\n'+END+'\nreturn rows\n',encoding='utf8')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--catalog-dir',type=Path,required=True);p.add_argument('--mod-root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();base,cat,mod,out=(v.resolve()for v in(a.baseline,a.catalog_dir,a.mod_root,a.output));assert base!=mod;out.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(mod/'tools'));import preview,catalog,gen2_extended_review as review
    c=json.loads((cat/'catalog.json').read_text(encoding='utf8'));assert c['rom_sha256']==ROM
    m=next(m for m in c['maps']if m['id']=='g03_m004');assert m['pair']==PAIR
    top=Image.open(cat/'pairs'/PAIR/'top.png').convert('RGBA');flat=Image.open(cat/'maps/g03_m004-flat.png').convert('RGBA')
    whole=Image.new('RGBA',(64,96));top_ink=0;modules=[]
    for y in range(6):
        for x in range(4):
            mid=m['grid'][y*17+x+13]&1023
            if(x,y)==(2,4):assert mid==561;continue
            tile=top.crop((mid%16*16,mid//16*16,mid%16*16+16,mid//16*16+16))
            whole.paste(tile,(x*16,y*16));top_ink+=sum(v[3]!=0 for v in tile.get_flattened_data())
            modules.append(dict(native_xy=[x+13,y],mid=mid,plane='top',opaque_pixels=sum(v[3]!=0 for v in tile.get_flattened_data())))
    # The frame is a discrete44x31 object. The surrounding large beige wall and
    # continuous room molding are not part of this hardware silhouette.
    board=flat.crop((222,6,266,37));assert board.size==(44,31)
    assert all(v[3]==255 for v in board.get_flattened_data())
    assert not whole.crop((14,6,58,37)).getbbox()
    whole.paste(board,(14,6))
    shaft=flat.crop((208,64,224,80));assert m['grid'][4*17+13]&1023==567
    assert not whole.crop((0,64,16,80)).getbbox();whole.paste(shaft,(0,64))
    assert whole.getbbox()==(0,6,64,96)
    assert sum(v[3]!=0 for v in whole.get_flattened_data())==2837==top_ink+1364+256
    whole.save(out/'complete-native-workbench.png')
    folder=mod/'assets/third_party/johto-hacks/azalea-native-workbench';folder.mkdir(parents=True,exist_ok=True)
    pieces=[]
    for y in range(6):
        for x in range(4):
            tile=whole.crop((x*16,y*16,x*16+16,y*16+16))
            if not tile.getbbox():continue
            f=folder/f'cell-{x}-{y}.png';tile.save(f)
            pieces.append(dict(asset=f.relative_to(mod).as_posix(),assetFileHash=SHA(f.read_bytes()),assetPixelHash=SHA(tile.tobytes()),
                native_xy=[x,y],target_xy=[12+x,y-1],opaque_pixels=sum(v[3]!=0 for v in tile.get_flattened_data())))
    assert len(pieces)==18
    provenance=dict(origin='Complete authentic CrystalDust Kurt pegboard, tools, L countertop and lower return.',credit='Pokemon CrystalDust / Sierraffinity and DoMoreAwesome Games',
        sourceUrl='https://github.com/Sierraffinity/CrystalDust',rom_sha256=ROM,source_map='g03_m004',pair=PAIR,
        source_top_sha256=SHA((cat/'pairs'/PAIR/'top.png').read_bytes()),source_flat_sha256=SHA((cat/'maps/g03_m004-flat.png').read_bytes()),
        native_size=[64,96],native_alpha_bounds=[0,6,64,96],native_opaque_pixels=2837,native_top_opaque_pixels=top_ink,
        complete_pegboard_native_xyxy=[222,6,266,37],complete_pegboard_pixels=1364,complete_shaft_mid=567,complete_shaft_pixels=256,
        excluded_whole_independent_chair_mid=561,top_modules=modules,translation_pixels=[-16,-16],native_scale=1,
        processing='Every native TOP hardware pixel except independent chair561 retained exactly. Entire44x31 distinct framed pegboard retained from flat plane; only generic exterior room wall and molding omitted. Solid native shaft567 retained whole. No recoloring, scaling, hardware clipping or source mechanics changes.',
        whole_RGBA_sha256=SHA(whole.tobytes()),source_modules={f'cell-{z["native_xy"][0]}-{z["native_xy"][1]}':z for z in pieces})
    (folder/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf8')
    path='mappings/johto_domestic_finish.lua';oldrows=preview.read_reviewed(base/path);cleanup=[];furniture=[];changes=[];cache=Path(os.environ['APPDATA'])/'pokemon-love2d';packed={}
    fixture=dict(assets={},maps={})
    for z in pieces:
        im=Image.open(mod/z['asset']).convert('RGBA')
        fixture['assets'][z['asset']]=dict(hash=z['assetFileHash'],mask=''.join('1'if v[3]else'0'for v in im.get_flattened_data()))
    for game in('gold','silver','crystal'):
        d=review.source(cache,game);md=d['maps']['KURTS_HOUSE'];ts=d['sets'][md['tileset']];sheet=Image.open(cache/game/ts['image']).convert('RGBA')
        fixture['maps'][game]={'KURTS_HOUSE':dict(width=md['width'],height=md['height'],tileset=md['tileset'],blocks=catalog.lua_array(md['blocks']))}
        selected=[r for r in oldrows if r.get('game')==game and r.get('map')=='KURTS_HOUSE'and'unique_teapot_or_apricorn_workbench'in r['role']]
        assert len(selected)==11
        floor=copy.deepcopy(next(r['donor']for r in oldrows if r.get('game')==game and r.get('map')=='KURTS_HOUSE'and r['role']=='johto_domestic_tatami_mat'))
        anchor=next(r for r in selected if(r['id'],r['quadrant'])==(49,2));assert anchor['sourceHash']=='b9295a913782f9438c63c5f146202a3b262bc43a49fe338c068b9767d3ee220b'
        for old in selected:
            r=copy.deepcopy(old);r.pop('colors',None);r.pop('palette',None);r.pop('sourceColors',None);r.pop('asset',None);r.pop('assetFileHash',None)
            r.update(kind='native',donor=floor,role='crystaldust_kurt_workbench_native_floor_backing')
            # The former source-palette row carried its hardware artwork hash.
            # This row is now exactly the selected native floor, so refresh its
            # review receipt from the actual replacement rather than retaining it.
            r['compositionPixelHash']=SHA(preview.replacement_image(cache,r,packed,mod).tobytes())
            assert r['compositionPixelHash']==floor['hash']
            r['evidence']+=' The complete native CrystalDust workbench is drawn once as bounded furniture, retaining its tools,44x31 framed pegboard and continuous L return. Remove this former GSC palette rendition and show the exact selected adjacent room floor under native alpha; collision, source events and both Kurt/Twin callback states remain untouched.'
            src=preview.native_cell(sheet,ts,catalog.lua_array(catalog.dict_at(ts['blocks'],r['id']+1)),r['quadrant']);assert SHA(src.tobytes())==r['sourceHash']
            xy=next((x,y)for y in range(8)for x in range(16)if catalog.lua_array(md['blocks'])[y//2*8+x//2]==r['id']and y%2*2+x%2==r['quadrant'])
            cleanup.append(canonical(r));changes.append(dict(game=game,map='KURTS_HOUSE',xy=xy,id=r['id'],quadrant=r['quadrant'],sourceHash=r['sourceHash'],sourceCollision=r['sourceCollision'],sourceFiles=r['sourceFiles']))
        for z in pieces:
            r=copy.deepcopy(anchor)
            for f in('sourceColors','colors','palette','donor','parts','base','animated','animation','frames','assetFrames','foreground','occludes'):r.pop(f,None)
            r.update(kind='third_party',furniture='kurt_workbench',role='crystaldust_complete_kurt_workbench',anchorX=12,anchorY=1,x=z['target_xy'][0],y=z['target_xy'][1],frontY=48 if z['target_xy'][1]<=2 else 80,
                asset=z['asset'],assetFileHash=z['assetFileHash'],assetPixelHash=z['assetPixelHash'],credit=provenance['credit'],sourceUrl=provenance['sourceUrl'],
                evidence='Complete genuine native CrystalDust Kurt pegboard+tools+L workbench, unscaled and source-specific. Every2837 hardware pixel retained; generic exterior wall removed so the selected source room wall/floor show through. Native independent chair561 omitted whole at working Kurt\'s source cell. Original11-part source L, NPC callbacks, collision, BG interactions and door remain guarded unchanged.')
            furniture.append(canonical(r))
    assert len(cleanup)==33 and len(furniture)==54
    compact=review.write_compact(cleanup,None)[0]
    footer(mod/path,'do\nlocal reviewed=(function()\n'+compact+'\nend)()\nlocal lookup={}\nlocal function key(r)return table.concat({r.game,r.style,r.tileset,r.map,tostring(r.id),tostring(r.quadrant)},"|")end\nfor _,r in ipairs(reviewed)do lookup[key(r)]=r end\nlocal n=0\nfor i,r in ipairs(rows)do local v=lookup[key(r)];if v then rows[i]=v;n=n+1 end end\nassert(n==33,"Kurt workbench source scope changed")\nend')
    compact=review.write_compact(furniture,None)[0]
    footer(mod/'lib/johto_furniture.lua','do\nlocal reviewed=(function()\n'+compact+'\nend)()\nfor _,r in ipairs(reviewed)do rows[#rows+1]=r end\nend')
    from newbark_building_review import lua
    (mod/'tests/kurt_workbench_native_alpha.lua').write_text('-- Exact full native CrystalDust Kurt hardware alpha and original source block geometry.\nreturn '+lua(canonical(fixture))+'\n',encoding='utf8')
    # Validate source cleanup through the same real importer/mapping pipeline.
    from types import SimpleNamespace
    val=review.validate_batch(cleanup,SimpleNamespace(cache=cache,engine=W/'.work/tileshift-engine-0420'),mod);assert val['rows_accepted']==33 and val['rejected']==0
    proof=dict(status='passed',changed_source_rows=33,bounded_furniture_rows=54,native_validation=val,selected_source_cells=changes,
        furniture_cells=[dict(game=r['game'],map=r['map'],xy=[r['x'],r['y']],frontY=r['frontY'],asset=r['asset'])for r in furniture],
        native_opaque_pixels=2837,pegboard_opaque_pixels=1364,whole_RGBA_sha256=SHA(whole.tobytes()),source_collision_events_NPCs_warps_unchanged=True,
        native_geometry='All hardware at1:1, origin[192,-16],opaque bounds[192,-10,256,80]. Generic exterior native wall transparent. Existing source11-piece L watched in full by roofs.lua.')
    (out/'proof.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8');print(json.dumps({k:proof[k]for k in('status','changed_source_rows','bounded_furniture_rows','native_validation')}))

if __name__=='__main__':main()
