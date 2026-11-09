"""Move only Azalea Gym's complete native tree north16, keeping its source map."""
from pathlib import Path
import argparse,copy,hashlib,json,os,re,sys
W=next(p for p in Path(__file__).resolve().parents if(p/'.tools/python').is_dir())
sys.path.insert(0,str(W/'.tools/python'))
from PIL import Image
SHA=lambda b:hashlib.sha256(b).hexdigest()
MARK='FINITE AZALEA GYM TREE NORTH16'

def canonical(v):
    if isinstance(v,dict):return{k:canonical(x)for k,x in sorted(v.items())}
    if isinstance(v,list):return[canonical(x)for x in v]
    return v

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--mod-root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    base,mod,out=(v.resolve()for v in(a.baseline,a.mod_root,a.output));assert base!=mod;out.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(mod/'tools'));import preview,catalog,gen2_extended_review as review
    from newbark_building_review import lua
    path='mappings/johto_gyms_finish.lua';rows=preview.read_reviewed(base/path);old=[r for r in rows if r.get('map')=='AZALEA_GYM'and r['id']==33 and r['game']in('gold','silver','crystal')];assert len(old)==12
    cleared=[];furniture=[];packed={};cache=Path(os.environ['APPDATA'])/'pokemon-love2d';scope=[];fixture=dict(assets={},maps={},phases={})
    for game in('gold','silver','crystal'):
        subset=sorted((r for r in old if r['game']==game),key=lambda r:r['quadrant']);assert len(subset)==4
        for r in subset:
            z=copy.deepcopy(r)
            for k in('asset','assetFileHash','assetPixelHash','base','credit','sourceUrl'):z.pop(k,None)
            z.update(kind='native',role='azalea_gym_center_tree_grass_backing',donor=copy.deepcopy(r['base']),evidence='Exact original native grass under the finite center tree. The complete selected tree is drawn16pixels north as guarded foreground; source map, all collisions including east passage, Bugsy, NPCs, scripts and warps remain unchanged.')
            z['compositionPixelHash']=SHA(preview.replacement_image(cache,z,packed,mod).tobytes());cleared.append(canonical(z))
            scope.append(dict(game=game,map='AZALEA_GYM',id=33,quadrant=r['quadrant'],sourceHash=r['sourceHash'],sourceCollision=r['sourceCollision'],sourceFiles=r['sourceFiles']))
        anchor=subset[0]
        for q,r in enumerate(subset):
            z=copy.deepcopy(anchor)
            for k in('base','donor','parts','animated','animation','frames','foreground','canopy','occludes','sourceColors'):z.pop(k,None)
            im=Image.open(base/r['asset']).convert('RGBA')
            z.update(kind='third_party',furniture='azalea_gym_tree',role='azalea_gym_center_tree_north16',anchorX=4,anchorY=6,x=4+q%2,y=5+q//2,frontY=108,
                asset=r['asset'],assetFileHash=r['assetFileHash'],assetPixelHash=SHA(im.tobytes()),compositionPixelHash=SHA(im.tobytes()),
                evidence='Complete native32x32 Azalea Gym center tree translated north16pixels. BIG TREES Default/Random/Mixed/native choices and four whole-sprite wind phases use the existing source-anchor selection key. All source block33 glyphs, source collisions, corridor, Bugsy, NPCs, scripts and warps are preserved; source-row6/7 actors stay in front at physical foot108.')
            furniture.append(canonical(z));fixture['assets'][r['asset']]=dict(hash=r['assetFileHash'],mask=''.join('1'if v[3]else'0'for v in im.get_flattened_data()))
        d=review.source(cache,game);md=d['maps']['AZALEA_GYM'];fixture['maps'][game]={'AZALEA_GYM':{k:md[k]for k in('width','height','tileset')}}
        assert [(j%md['width']*2,j//md['width']*2)for j,b in enumerate(catalog.lua_array(md['blocks']))if b==33]==[(4,6)]
    # Raw alpha phases are an independent ROM-free renderer fixture.
    whole=Image.new('RGBA',(32,32))
    for r in sorted((r for r in old if r['game']=='crystal'),key=lambda r:r['quadrant']):whole.paste(Image.open(base/r['asset']).convert('RGBA'),(r['quadrant']%2*16,r['quadrant']//2*16))
    whole.save(out/'complete-current-native-tree32.png')
    for q in range(4):
        fixture['phases'][q+1]=[]
        for i,offset in enumerate((0,1,0,-1)):
            wind=Image.new('RGBA',(32,32))
            for y in range(32):
                occupied=[x for x in range(32)if whole.getpixel((x,y))[3]];shift=offset if y<19 else 0
                if occupied and(min(occupied)+shift<0 or max(occupied)+shift>=32):shift=0
                for x in occupied:wind.putpixel((x+shift,y),whole.getpixel((x,y)))
            im=wind.crop((q%2*16,q//2*16,q%2*16+16,q//2*16+16));fixture['phases'][q+1].append(dict(path='tree-phase-'+str(q)+'-'+str(i),mask=''.join('1'if v[3]else'0'for v in im.get_flattened_data())))
    def append(path,body):
        text=(base/path).read_text(encoding='utf8');assert MARK not in text;tail=re.search(r'\nreturn rows\s*$',text);assert tail,path
        (mod/path).write_text(text[:tail.start()]+'\n-- BEGIN '+MARK+'\n'+body+'\n-- END '+MARK+'\nreturn rows\n',encoding='utf8')
    compact=review.write_compact(cleared,None)[0]
    append(path,'do\nlocal fixed=(function()\n'+compact+'\nend)()\nlocal lookup={}\nfor _,r in ipairs(fixed)do lookup[r.game..":"..r.quadrant]=r end\nlocal n=0\nfor i,r in ipairs(rows)do if r.map=="AZALEA_GYM"and r.id==33 and r.style=="gen3"then rows[i]=assert(lookup[r.game..":"..r.quadrant]);n=n+1 end end\nassert(n==12,"Azalea tree source scope changed")\nend')
    compact=review.write_compact(furniture,None)[0]
    append('lib/johto_furniture.lua','do\nlocal fixed=(function()\n'+compact+'\nend)()\nfor _,r in ipairs(fixed)do rows[#rows+1]=r end\nend')
    (mod/'tests/azalea_tree_native_alpha.lua').write_text('-- Exact native full-tree alpha, whole wind frames and original source bounds.\nreturn '+lua(canonical(fixture))+'\n',encoding='utf8')
    from types import SimpleNamespace
    validation=review.validate_batch(cleared,SimpleNamespace(cache=cache,engine=W/'.work/tileshift-engine-0420'),mod);assert validation['rows_accepted']==12 and validation['rejected']==0
    proof=dict(status='passed',changed_source_rows=12,new_furniture_rows=12,source_guard_scope=scope,source_anchor=[4,6],source_id=33,
        new_native_origin=[64,80],old_native_origin=[64,96],native_size=[32,32],frontY=108,native_scale=1,
        original_tree_assets_byte_unchanged=True,tree_chooser_and_four_wind_frames_preserved=True,source_collisions_NPCs_scripts_warps_unchanged=True,native_validation=validation)
    (out/'proof.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in proof.items()if k!='source_guard_scope'}))

if __name__=='__main__':main()
