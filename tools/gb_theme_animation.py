"""Independent native GB water/flower preview frames for reverse themes."""
from pathlib import Path
import json
from PIL import Image, ImageChops
import catalog

MONO=[(255,255,255),(170,170,170),(85,85,85),(0,0,0)]

def specification(cache,ref,bank):
    root=Path(cache)/ref['game'];meta=root/'data/generated/tilesets.lua'
    sets=catalog.read_lua(meta);ts=sets[ref['tileset']]
    if ref['game']in('red','blue','yellow'):
        if bank=='water':
            if ts.get('animation')not in('TILEANIM_WATER','TILEANIM_WATER_FLOWER'):return None
            digest=catalog.sha((root/ts['image']).read_bytes())
        else:
            if ts.get('animation')!='TILEANIM_WATER_FLOWER':return None
            digest=catalog.sha(b''.join((root/f'assets/generated/tilesets/flower{i}.png').read_bytes()for i in(1,2,3)))
    else:
        frames=ts.get('anim',{}).get('frames',[])
        func='AnimateWaterTile'if bank=='water'else'AnimateFlowerTile'
        if not any(f.get('func')==func for f in frames):return None
        name='waterFrames'if bank=='water'else'flowerFrames'
        digest=catalog.sha((root/sets[name]).read_bytes())
    return {'kind':'gb','bank':bank,'hash':digest,'manifestHash':catalog.sha(meta.read_bytes())}

def frames(cache,ref,spec,packed):
    import preview
    key=('gb_animation',json.dumps(ref,sort_keys=True),json.dumps(spec,sort_keys=True))
    if key in packed:return packed[key]
    root=Path(cache)/ref['game'];sets=catalog.read_lua(root/'data/generated/tilesets.lua');ts=sets[ref['tileset']]
    assert specification(cache,ref,spec['bank'])==spec,'Native GB animation files changed'
    block=catalog.lua_array(catalog.dict_at(ts['blocks'],ref['id']+1));bank=spec['bank'];tile=20 if bank=='water'else 3
    if ref['game']in('red','blue','yellow'):
        palettes=[MONO]*8
        if bank=='water':
            sheet=Image.open(root/ts['image']).convert('RGBA');per=ts.get('tilesPerRow',16)
            neutral=sheet.crop((20%per*8,20//per*8,20%per*8+8,20//per*8+8))
            variants=[ImageChops.offset(neutral,n,0)for n in(1,2,3,2,1,0,7,0)]
        else:variants=[Image.open(root/f'assets/generated/tilesets/flower{i}.png').convert('RGBA')for i in(1,2,3,1,1,2,3,1)]
    else:
        definition=catalog.read_lua(root/'data/generated/maps.lua')[ref['map']]
        palettes=preview.palette_set(catalog.read_lua(root/'data/generated/palettes.lua'),definition,ref.get('daytime','DAY'))
        path=sets['waterFrames'if bank=='water'else'flowerFrames'];strip=Image.open(root/path).convert('RGBA')
        rows=(1,2,3,4)if bank=='water'else tuple(sets.get('flowerCgbFrames',[2,4]))
        variants=[strip.crop((0,(n-1)*8,8,n*8))for n in rows]
    base=preview.native_donor(cache,ref,packed);output=[];q=ref.get('quadrant',0);qx,qy=q%2*2,q//2*2
    sheet=Image.open(root/ts['image']).convert('RGBA')
    for neutral in variants:
        result=base.copy();found=False
        for i in range(4):
            raw=block[(qy+i//2)*4+qx+i%2]
            if raw!=tile:continue
            found=True;_,attrs=catalog.gb_tile(sheet,ts,raw);colors=palettes[attrs.get('palette',1)-1]
            glyph=neutral.copy();glyph.putdata([tuple(colors[max(0,min(3,round((255-r)*3/255)))])+(a,)for r,g,b,a in glyph.get_flattened_data()])
            result.paste(glyph,(i%2*8,i//2*8))
        assert found,'GB source cell has no requested animated glyph'
        output.append(result)
    packed[key]=output;return output
