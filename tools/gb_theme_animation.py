"""Independent native GB program/foreground preview frames for reverse themes."""
from pathlib import Path
import json
from PIL import Image, ImageChops
import catalog

MONO=[(255,255,255),(170,170,170),(85,85,85),(0,0,0)]
PROGRAM_KINDS={'AnimateWaterTile':'water','AnimateFlowerTile':'flower',
 'AnimateWhirlpoolTile':'whirlpool','AnimateTowerPillarTile':'tower',
 'AnimateLavaBubbleTile1':'lava1','AnimateLavaBubbleTile2':'lava2'}

def program_layers(sets,ts,ref):
    block=catalog.lua_array(catalog.dict_at(ts['blocks'],ref['id']+1));q=ref.get('quadrant',0);x,y=q%2*2,q//2*2
    raw={block[(y+dy)*4+x+dx]for dy in(0,1)for dx in(0,1)};layers={}
    for frame in ts.get('anim',{}).get('frames',[]):
        kind=PROGRAM_KINDS.get(frame['func']);tile=3 if kind=='flower'else frame.get('tile')
        if tile not in raw:continue
        if kind:
            path=sets['waterFrames']if kind=='water'else sets['flowerFrames']if kind=='flower'else frame['sheet']
            count=4 if kind in('water','flower')else frame['frames']
        elif frame['func']=='WriteTileFromAnimBuffer'and frame.get('scroll'):
            kind='scroll';path=ts['image'];count=8
        elif frame['func'].startswith('Animate')and frame['func'].endswith('Tile'):
            raise ValueError('Unsupported native GB tile program: '+frame['func'])
        else:continue
        assert tile not in layers
        layers[tile]=dict(kind=kind,path=path,count=count,scroll=frame.get('scroll'))
    return layers

def specification(cache,ref,bank,flow_direction=None):
    root=Path(cache)/ref['game'];meta=root/'data/generated/tilesets.lua'
    sets=catalog.read_lua(meta);ts=sets[ref['tileset']]
    if bank=='program':
        if ref['game']not in('gold','silver','crystal'):return None
        layers=program_layers(sets,ts,ref)
        if not layers:return None
        digest=catalog.sha(b''.join((root/path).read_bytes()for path in sorted({v['path']for v in layers.values()})))
        spec={'kind':'gb','bank':bank,'hash':digest,'manifestHash':catalog.sha(meta.read_bytes())}
        if flow_direction is not None:
            assert flow_direction in ('north','south','east','west')
            block=catalog.lua_array(catalog.dict_at(ts['blocks'],ref['id']+1));q=ref.get('quadrant',0);x,y=q%2*2,q//2*2
            assert {block[(y+dy)*4+x+dx]for dy in(0,1)for dx in(0,1)}=={20}
            assert layers[20]['kind']=='scroll'and layers[20]['scroll']['h']==1 and layers[20]['scroll'].get('v',0)==0
            spec['flowDirection']=flow_direction
        return spec
    assert flow_direction is None,'Directional flow requires a native scrolling program'
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
    assert specification(cache,ref,spec['bank'],spec.get('flowDirection'))==spec,'Native GB animation files changed'
    if spec['bank']=='program':
        result,foregrounds=program_frames(cache,ref,sets,ts,packed,spec.get('flowDirection'))
        packed[key]=result;packed[('gb_foreground',key)]=foregrounds;return result
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
        palettes=ref.get('palettes')or preview.palette_set(catalog.read_lua(root/'data/generated/palettes.lua'),definition,ref.get('daytime','DAY'))
        path=sets['waterFrames'if bank=='water'else'flowerFrames'];strip=Image.open(root/path).convert('RGBA')
        rows=(1,2,3,4)if bank=='water'else tuple(sets.get('flowerCgbFrames',[2,4]))
        variants=[strip.crop((0,(n-1)*8,8,n*8))for n in rows]
    base=preview.native_donor(cache,ref,packed);output=[];foregrounds=[];q=ref.get('quadrant',0);qx,qy=q%2*2,q//2*2
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
        foregrounds.append(_foreground_frame(cache,ref,sets,ts,packed,result,{tile:neutral}))
    packed[key]=output;packed[('gb_foreground',key)]=foregrounds;return output


def foreground_frames(cache,ref,spec,packed):
    key=('gb_animation',json.dumps(ref,sort_keys=True),json.dumps(spec,sort_keys=True))
    frames(cache,ref,spec,packed)
    return packed['gb_foreground',key]


def _foreground_frame(cache,ref,sets,ts,packed,result,overrides):
    import preview
    out=preview.gb_donor_layers(cache,ref,packed)['foreground'].copy()
    block=catalog.lua_array(catalog.dict_at(ts['blocks'],ref['id']+1));q=ref.get('quadrant',0);qx,qy=q%2*2,q//2*2
    for i in range(4):
        raw=block[(qy+i//2)*4+qx+i%2]
        if raw not in overrides:continue
        glyph=overrides[raw];dx,dy=i%2*8,i//2*8
        for y in range(8):
            for x in range(8):
                out.putpixel((dx+x,dy+y),result.getpixel((dx+x,dy+y))if glyph.getpixel((x,y))[0]<255 else(0,0,0,0))
    return out


def program_frames(cache,ref,sets,ts,packed,flow_direction=None):
    import preview
    root=Path(cache)/ref['game'];layers=program_layers(sets,ts,ref)
    definition=catalog.read_lua(root/'data/generated/maps.lua')[ref['map']]
    palettes=ref.get('palettes')or preview.palette_set(catalog.read_lua(root/'data/generated/palettes.lua'),definition,ref.get('daytime','DAY'))
    block=catalog.lua_array(catalog.dict_at(ts['blocks'],ref['id']+1));q=ref.get('quadrant',0);qx,qy=q%2*2,q//2*2
    sheets={path:Image.open(root/path).convert('RGBA')for path in {v['path']for v in layers.values()}}
    base=preview.native_donor(cache,ref,packed);atlas=Image.open(root/ts['image']).convert('RGBA');output=[];foregrounds=[]
    for timer in range(8):
        glyphs={}
        for tile,layer in layers.items():
            strip=sheets[layer['path']];kind=layer['kind']
            if kind=='scroll':
                per=ts.get('tilesPerRow',16);sx,sy=tile%per*8,tile//per*8
                assert sx+8<=strip.width and sy+8<=strip.height
                dx=(0,1,2,3,2,1,0,-1)[timer]if layer['scroll'].get('h',0)>0 else 0
                dy=timer*layer['scroll'].get('v',0)
                if flow_direction:
                    vx,vy={'north':(0,-1),'south':(0,1),'east':(1,0),'west':(-1,0)}[flow_direction]
                    dx,dy=timer*vx,timer*vy
                glyph=ImageChops.offset(strip.crop((sx,sy,sx+8,sy+8)),dx,dy)
            else:
                assert strip.size==(8,layer['count']*8)
                if kind in('water','lava2'):row=timer//2
                elif kind=='flower':row=sets.get('flowerCgbFrames',[2,4])[0 if timer%4<2 else 1]-1
                elif kind=='whirlpool':row=timer%4
                elif kind=='tower':row=(0,1,2,3,4,3,2,1)[timer]
                elif kind=='lava1':row=(timer//2+2)%4
                glyph=strip.crop((0,row*8,8,row*8+8))
            glyphs[tile]=glyph
        result=base.copy()
        for i in range(4):
            tile=block[(qy+i//2)*4+qx+i%2]
            if tile not in glyphs:continue
            _,attrs=catalog.gb_tile(atlas,ts,tile);colors=palettes[attrs.get('palette',1)-1]
            glyph=glyphs[tile].copy();glyph.putdata([tuple(colors[max(0,min(3,round((255-r)*3/255)))])+(a,)for r,g,b,a in glyph.get_flattened_data()])
            result.paste(glyph,(i%2*8,i//2*8))
        output.append(result)
        foregrounds.append(_foreground_frame(cache,ref,sets,ts,packed,result,glyphs))
    return output,foregrounds
