"""Restore complete native CrystalDust Rocket equipment at its original pixel scale.

Only authored artwork changes. The source map, actors, collision, callbacks,
password doors and six Electrode anchors retain their imported definitions.
"""
from pathlib import Path
from collections import defaultdict
from types import SimpleNamespace
import argparse,copy,hashlib,json,pickle,re,sys
W=next(p for p in Path(__file__).resolve().parents if(p/'.tools/python').is_dir()and(p/'.work').is_dir())
sys.path.insert(0,str(W/'.tools/python'))
from PIL import Image
MODULE='mappings/gen2_crystaldust_rocket.lua'
ASSETS='assets/third_party/johto-hacks/crystaldust-rocket-equipment'
ROM='51196cba923c315d0088b747b5cdee704f2ac057cd493f9ddf226fb7227302cf'
PAIR='083df884_083dfc94'
GAMES=('gold','silver','crystal')
sha=lambda b:hashlib.sha256(b).hexdigest()
pixel=lambda im:sha(im.convert('RGBA').tobytes())

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,required=True);p.add_argument('--mod-root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--native-root',type=Path,default=W/'.work/tileshift-firegold/crystaldust')
    p.add_argument('--output',type=Path,required=True);p.add_argument('--row-cache',type=Path)
    p.add_argument('--engine',type=Path,default=W/'.work/tileshift-engine-0420')
    a=p.parse_args();base=a.baseline.resolve();mod=a.mod_root.resolve();out=a.output.resolve();native=a.native_root.resolve()
    assert base!=mod and json.loads((base/'manifest.json').read_text())['version']=='0.46.7'
    sys.path.insert(0,str(mod/'tools'))
    import preview,catalog,gen2_extended_review as review
    from center_mart_overhang_review import write_rows
    cache=Path('C:/Users/LSDMTHC/AppData/Roaming/pokemon-love2d');packed={};out.mkdir(parents=True,exist_ok=True)
    paths=list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(base/'main.lua').read_text(encoding='utf-8'))))
    if a.row_cache:
        assert a.row_cache.resolve().parent.parent.name=='.work'
        pairs=pickle.loads(a.row_cache.read_bytes())
    else:pairs=[(path,r)for path in paths for r in preview.read_reviewed(base/path)if r['game']in GAMES and r['style']=='gen3']
    generic,scoped,positioned=defaultdict(dict),defaultdict(dict),defaultdict(dict)
    for path,r in sorted(pairs,key=lambda v:bool(v[1].get('map'))):
        k=r['id'],r['quadrant']
        if 'x'in r:positioned[r['game'],r['map']][(*k,r['x'],r['y'])]=r
        elif r.get('map'):scoped[r['game'],r['map']][k]=r
        else:generic[r['game'],r['tileset']][k]=r
    dc=json.loads((native/'catalog.json').read_text(encoding='utf-8'));assert dc['rom_sha256']==ROM
    nm=next(m for m in dc['maps']if m['id']=='g24_m020');assert nm['pair']==PAIR
    atlas={layer:Image.open(native/'pairs'/PAIR/(layer+'.png')).convert('RGBA')for layer in('flat','bottom','top')}
    ts=json.loads((native/'pairs'/PAIR/'metatiles.json').read_text(encoding='utf-8'))
    def mid(x,y):return nm['grid'][y*nm['width']+x]&1023
    def tile(layer,ident):return atlas[layer].crop((ident%16*16,ident//16*16,ident%16*16+16,ident//16*16+16))
    floor=dict(game='firered',tileset='building__rom_082d4ecc',id=641,hash='f7c5591ac32c6da41ae316a7603d656be45618fc949c131ce8686effbc70ad46')
    old_floor=preview.native_donor(cache,floor,packed);assert pixel(old_floor)==floor['hash']
    dest=mod/ASSETS;dest.mkdir(parents=True,exist_ok=True);files={};origins=[];assets={};plans={};whole=Image.new('RGBA',(96,96))
    recipe=[5,6,7,8,15,16]
    for dy,sy in enumerate(recipe):
        for dx,sx in enumerate(range(13,19)):
            ident=mid(sx,sy);flat=tile('flat',ident);assert pixel(flat)==ts[ident]['pixel_sha256']
            plane='bottom+top'if sy==7 else'top'
            art=Image.alpha_composite(tile('bottom',ident),tile('top',ident))if sy==7 else tile('top',ident)
            native_floor=tile('bottom',mid(13,5))
            assert Image.alpha_composite(native_floor,art).tobytes()==flat.tobytes()
            name=f'generator-{ident}.png';path=dest/name
            if name in assets:assert Image.open(path).convert('RGBA').tobytes()==art.tobytes()
            else:
                art.save(path);files[name]=sha(path.read_bytes());assets[name]=dict(asset=ASSETS+'/'+name,assetFileHash=files[name],assetPixelHash=pixel(art))
                origins.append(dict(file=name,native_map='g24_m020',pair=PAIR,metatile=ident,plane=plane,
                    atlas_rect=[ident%16*16,ident//16*16,16,16],native_flat_rgba_sha256=pixel(flat),rgba_sha256=pixel(art),pixel_scale=1))
            plans[12+dx,4+dy]=(assets[name],f'crystaldust_complete_generator_bank_{dx}_{dy}')
            whole.alpha_composite(art,(dx*16,dy*16))
    assert pixel(whole)=='13bda55e925c3e18aaa0161f54922e48885d2dfe979b2a030e9774dd1cd1c861'
    assert whole.getbbox()==(0,8,96,88)
    native_edges={(mid(x,y),mid(x+1,y),'h')for y in range(nm['height'])for x in range(nm['width']-1)}
    native_edges|={(mid(x,y),mid(x,y+1),'v')for y in range(nm['height']-1)for x in range(nm['width'])}
    seams=0
    for y,sy in enumerate(recipe):
        for x in range(6):
            if x<5:assert(mid(13+x,sy),mid(14+x,sy),'h')in native_edges;seams+=x<5
            if y<5:assert(mid(13+x,sy),mid(13+x,recipe[y+1]),'v')in native_edges;seams+=y<5
    assert seams==60
    pieces={}
    for name,layer,ident,expected in(
        ('server-head','top',995,'9c2feab825a58dc2c91759aae8eced323f33cc3b756996a4789101b03610419e'),
        ('server-body','bottom',1003,'2467b2e8f417f93a91e1386b6fe76f1c1fa83227847a326dd5d62d1cc61b779f'),
        ('cable','bottom',1015,'dd29830fb3e32cefb7ec6f020ce7f43e146341e2809d9c253e2abbc9eea773c2'),
        ('electrode-terminal','bottom',1016,'79263b6638a6cfbcf0ef10db55bef2aa5d841ed33f4e1361be0d05d26133f9f1'),
        ('desk-top-568','top',568,'2e6cab271105c8a1684e2c53dda9dfff7344990ea8dc5c9cba4b663d5fcd9f69'),
        ('desk-top-570','top',570,'4876008ce2dd5b8e450103bf7397de248e2eb42e1934b9e4ec21b559f8a36ee6'),
        ('desk-front-1006','bottom',1006,'3f4867b2cf4245b8f6368a2dc6b724e5bfde4371f877f7785504cf18b1c2040f'),
        ('desk-front-1007','bottom',1007,'f369ac79c8cef48f4f28d819c802347cbf5eeaaf0d118630f01ab6316775bc4d')):
        art=tile(layer,ident);assert pixel(art)==expected
        path=dest/(name+'.png');art.save(path);files[path.name]=sha(path.read_bytes())
        pieces[name]=dict(asset=ASSETS+'/'+path.name,assetFileHash=files[path.name],assetPixelHash=pixel(art))
        origins.append(dict(file=path.name,native_map='g24_m021'if name.startswith('desk-')else'g24_m020',pair=PAIR,metatile=ident,plane=layer,
            atlas_rect=[ident%16*16,ident//16*16,16,16],rgba_sha256=pixel(art),pixel_scale=1))
    for y in(5,7,9):
        for x in(*range(8,12),*range(18,22)):plans[x,y]=(pieces['cable'],'crystaldust_complete_rocket_conduit')
        for x in(7,22):plans[x,y]=(pieces['electrode-terminal'],'crystaldust_native_electrode_terminal')
    desk=Image.new('RGBA',(32,32));desk_plan={}
    for dx,dy,key in((0,0,'desk-top-568'),(1,0,'desk-top-570'),(0,1,'desk-front-1006'),(1,1,'desk-front-1007')):
        art=pieces[key];desk.paste(Image.open(mod/art['asset']).convert('RGBA'),(dx*16,dy*16))
        for x,y in((22,6),(24,10)):
            desk_plan[x+dx,y+dy]=(art,f'crystaldust_complete_rocket_empty_desk_{dx}_{dy}',7 if dy==0 else 0)
    assert pixel(desk)=='f65f21962e98723bf59c3cd4652fe91487c868266fe25545f2554408a9f54708'
    provenance=dict(format=1,credit='CrystalDust by Sierraffinity and contributors',sourceUrl='https://github.com/Sierraffinity/CrystalDust',
        source_rom_sha256=ROM,native_map='g24_m020',pair=PAIR,files=files,pieces=origins,
        native_atlas_files={layer+'.png':sha((native/'pairs'/PAIR/(layer+'.png')).read_bytes())for layer in atlas},
        assembly=dict(size=[96,96],native_rows=recipe,native_columns=[13,19],rgba_sha256=pixel(whole),alpha_bounds=list(whole.getbbox()),
            native_adjacencies_verified=seams,complete_unique_caps_castings_fronts_and_feet=True,removed_only_repeated_join_body_pairs=3,pixel_scale=1))
    provenance['empty_desk']=dict(native_map='g24_m021',native_rect=[400,128,32,32],native_planes=[['top:568','top:570'],['bottom:1006','bottom:1007']],
        size=[32,32],opaque_pixels=1024,rgba_sha256=pixel(desk),separate_native_stool_top_planes_excluded=True,complete_native_desk_unchanged=True,pixel_scale=1)
    (dest/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8')
    pc_templates={}
    for path,r in pairs:
        if r['game']=='crystal'and r.get('map')=='TEAM_ROCKET_BASE_B1F'and r['role'].startswith('crystaldust_complete_rocket_control_pc_'):
            pc_templates[tuple(map(int,r['role'].rsplit('_',2)[1:]))]=r
    assert set(pc_templates)=={(0,0),(1,0),(0,1),(1,1)}
    pc_raw={(2,3,18,19):(0,0),(4,5,20,21):(1,0),(6,7,38,1):(0,1),(8,9,38,1):(1,1)}
    new=[];approved={};receipts=[]
    evidence=('Complete native CrystalDust Rocket equipment at1:1 pixel scale. The two48px-wide generator columns retain every unique cap, casing, front and foot; only whole repeated tier pairs are omitted to fit the original96x96 blocked bank. All60 module seams already occur in the native room. Complete native32x26 computers retain all687 opaque pixels and omit a separate stool. Whole32x32 empty desks retain complete native tabletop and front modules without importing separate stool layers. Whole16x32 native server cabinets retain all448 opaque pixels; complete16px conduit and terminal modules keep both native8px halves. Original ground remains visible through native alpha. Source collision, six Electrode anchors, power/password/door callbacks, NPCs, warps and map geometry are unchanged; no decorative overhang or runtime work is introduced.')
    for game in GAMES:
        data=review.source(cache,game)
        for name in('TEAM_ROCKET_BASE_B2F','TEAM_ROCKET_BASE_B3F'):
            md=data['maps'][name];chosen={**generic[game,md['tileset']],**scoped[game,name]};coords=[]
            receipts.append(dict(game=game,map=name,source_definition_sha256=sha(json.dumps(md,sort_keys=True,separators=(',',':')).encode())))
            for y in range(md['height']*2):
                for x in range(md['width']*2):
                    bid=md['blocks'][y//2*md['width']+x//2];q=y%2*2+x%2;old=positioned[game,name].get((bid,q,x,y))or chosen.get((bid,q))
                    assert old
                    c=review.cell_info(cache,game,data,md['tileset'],bid,q)
                    art=role=None;base_ref=floor
                    if name=='TEAM_ROCKET_BASE_B2F'and(x,y)in plans:
                        art,role=plans[x,y]
                        assert c['collision']==(7 if role.startswith('crystaldust_complete_generator_bank_')else 0)
                    elif name=='TEAM_ROCKET_BASE_B3F'and(x,y)in desk_plan:
                        art,role,collision=desk_plan[x,y];assert c['collision']==collision
                    elif old['role']in('johto_facility_whole_research_server_head','johto_facility_whole_research_server_base'):
                        head=old['role'].endswith('_head');art=pieces['server-head'if head else'server-body']
                        role='crystaldust_complete_rocket_server_head'if head else'crystaldust_complete_rocket_server_body'
                        base_ref=old['base'];assert old['sourceCollision']==7
                    elif old['role']=='johto_facility_whole_research_workstation':
                        c=review.cell_info(cache,game,data,md['tileset'],bid,q);pq=pc_raw[tuple(c['tiles'])];pc=pc_templates[pq]
                        art={k:pc[k]for k in('asset','assetFileHash','assetPixelHash')};role='crystaldust_complete_rocket_workstation_'+str(pq[0])+'_'+str(pq[1])
                    if art is None:continue
                    c=review.cell_info(cache,game,data,md['tileset'],bid,q)
                    assert c['sourceHash']==old['sourceHash']and c['collision']==old.get('sourceCollision',c['collision'])
                    assert all(old.get('sourceFiles',{}).get(k,v)==v for k,v in data['fingerprints'][md['tileset']].items())
                    priorities=[bool(v.get('priority'))for v in c['attributes']];palettes=[v.get('palette',1)for v in c['attributes']]
                    assert priorities==old.get('sourcePriority',priorities)
                    assert palettes==old.get('sourcePalettes',palettes)
                    assert'x'not in old,'Positioned overrides must be explicitly retired, not duplicated.'
                    row={k:copy.deepcopy(v)for k,v in old.items()if k.startswith('source')and k not in('sourceColors','sourceUrl','sourceCells')}
                    row.update({k:old[k]for k in('game','style','tileset','id','quadrant')})
                    row.update(map=name,x=x,y=y,sourceCells=[[x,y]],status='reviewed',kind='third_party',base=copy.deepcopy(base_ref),
                        role=role,evidence=evidence,credit=provenance['credit'],sourceUrl=provenance['sourceUrl'],**art)
                    row.update(sourceCollision=c['collision'],sourceFiles=copy.deepcopy(data['fingerprints'][md['tileset']]),
                        sourcePriority=priorities,sourcePalettes=palettes)
                    row['compositionPixelHash']=pixel(preview.replacement_image(cache,row,packed,mod));new.append(row);coords.append([x,y])
            assert len(coords)==(78 if name.endswith('B2F')else 32),(game,name,len(coords))
            approved[game+':'+name]=coords
    write_rows(mod/MODULE,new)
    main_path=mod/'main.lua';text=main_path.read_bytes();marker=b"    'mappings/gen2_native_public_counters.lua',"
    entry=b"    '"+MODULE.encode()+b"',"
    if entry not in text:assert text.count(marker)==1;text=text.replace(marker,marker+b'\r\n'+entry)
    main_path.write_bytes(text)
    test_path=mod/'tests/main_test.lua';text=test_path.read_bytes();marker=b"or path=='mappings/gen2_native_public_counters.lua' then return nil end"
    if MODULE.encode()not in text:assert text.count(marker)==1;text=text.replace(marker,b"or path=='mappings/gen2_native_public_counters.lua' or path=='"+MODULE.encode()+b"' then return nil end")
    test_path.write_bytes(text)
    valid=review.validate_batch(new,SimpleNamespace(cache=cache,engine=a.engine,output=out),mod)
    assert valid['rows_accepted']==len(new)and valid['rejected']==0
    proof=dict(status='passed',new_positioned_rows=len(new),approved_cells=approved,source_receipts=receipts,
        native_validation=valid,bank_rgba_sha256=pixel(whole),all_native_module_adjacencies_verified=seams,
        native_bank_complete=True,complete_pc_instances=18,complete_empty_desk_instances=6,
        complete_empty_desk_rgba_sha256=pixel(desk),complete_cabinet_instances=18,
        native_conduit_cells=72,native_electrode_terminals=18,source_geometry_callbacks_npcs_collision_unchanged=True)
    (out/'proof.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in proof.items()if k not in('approved_cells','source_receipts')}))
if __name__=='__main__':main()
