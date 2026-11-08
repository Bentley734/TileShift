"""Extract complete native CrystalDust Mr. Pokemon research-machine pixels."""
from __future__ import annotations
from pathlib import Path
import argparse,hashlib,json,sys
HERE=Path(__file__).resolve().parent
for ancestor in HERE.parents:
    dependencies=ancestor/'.tools/python'
    if dependencies.is_dir():
        sys.path.insert(0,str(dependencies));break
from PIL import Image
PAIR='083df884_083dfb0c'
PREFIX='assets/third_party/johto-hacks/mr-pokemon-research-machine'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rgba=lambda im:hashlib.sha256(im.convert('RGBA').tobytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root',type=Path,required=True,
        help='Read-only native CrystalDust extraction containing catalog.json, pairs and maps.')
    p.add_argument('--output',type=Path,default=HERE.parent/PREFIX)
    a=p.parse_args();source=a.source_root.resolve();out=a.output.resolve()
    assert out!=source and not out.is_relative_to(source),'Keep native extraction read only'
    catalog_path=source/'catalog.json';catalog=json.loads(catalog_path.read_text(encoding='utf-8'))
    assert catalog['rom_sha256']=='51196cba923c315d0088b747b5cdee704f2ac057cd493f9ddf226fb7227302cf'
    md=next(m for m in catalog['maps']if m['id']=='g02_m006')
    assert(md['width'],md['height'],md['pair'])==(8,9,PAIR)
    directory=source/'pairs'/PAIR
    planes={n:Image.open(directory/(n+'.png')).convert('RGBA')for n in('bottom','top','flat')}
    metadata={r['id']:r for r in json.loads((directory/'metatiles.json').read_text(encoding='utf-8'))}
    native_map=Image.open(source/'maps/g02_m006-flat.png').convert('RGBA')
    assert native_map.size==(128,144)
    out.mkdir(parents=True,exist_ok=True)
    files={};modules={};whole=Image.new('RGBA',(32,48));parts=[]
    for dy in range(3):
        for dx in range(2):
            x,y=6+dx,dy;word=md['grid'][y*md['width']+x];mid=word&1023
            sx,sy=(mid%16)*16,(mid//16)*16;rect=(sx,sy,sx+16,sy+16)
            flat=Image.alpha_composite(planes['bottom'].crop(rect),planes['top'].crop(rect))
            assert flat.tobytes()==planes['flat'].crop(rect).tobytes()
            assert rgba(flat)==metadata[mid]['pixel_sha256']
            assert flat.tobytes()==native_map.crop((x*16,y*16,x*16+16,y*16+16)).tobytes()
            image=planes['top'].crop(rect)
            assert set(image.getchannel('A').get_flattened_data())<={0,255}
            name=f'machine-{dx}-{dy}.png';path=out/name;image.save(path)
            assert Image.open(path).convert('RGBA').tobytes()==image.tobytes()
            whole.paste(image,(dx*16,dy*16));files[name]=sha(path)
            modules[name]={'asset':PREFIX+'/'+name,'assetFileHash':sha(path),'assetPixelHash':rgba(image),
                'native_map_cell':[x,y],'native_grid_value':word,'native_metatile_id':mid,
                'plane':'top','source_rect_xywh':[sx,sy,16,16],'destination_xy':[dx*16,dy*16],
                'complete_module':True,'native_alpha_unchanged':True,'scale':1}
            parts.append({'asset':PREFIX+'/'+name,'xy':[dx*16,dy*16]})
    assert whole.getbbox()==(0,9,32,48)
    name='complete-native-machine.png';whole.save(out/name);files[name]=sha(out/name)
    assert Image.open(out/name).convert('RGBA').tobytes()==whole.tobytes()
    wall_mid=md['grid'][2]&1023
    assert wall_mid==105
    wx,wy=wall_mid%16*16,wall_mid//16*16
    wall=planes['flat'].crop((wx,wy,wx+16,wy+16))
    assert rgba(wall)==metadata[wall_mid]['pixel_sha256']
    compounds={}
    for dx in range(2):
        piece=Image.open(out/f'machine-{dx}-1.png').convert('RGBA')
        compound=Image.alpha_composite(wall,piece)
        filename=f'machine-wall-{dx}.png';compound.save(out/filename);files[filename]=sha(out/filename)
        assert all(not p[3]or p==q for p,q in zip(piece.get_flattened_data(),compound.get_flattened_data()))
        compounds[filename]={'asset':PREFIX+'/'+filename,'assetFileHash':files[filename],
            'assetPixelHash':rgba(compound),'recipe':'Exact native FLAT wall105 + intact TOP machine middle module, both at0,0.',
            'native_wall_metatile':wall_mid,'native_wall_plane':'flat','native_wall_rgba_sha256':rgba(wall),
            'native_wall_source_rect_xywh':[wx,wy,16,16],'native_foreground':f'machine-{dx}-1.png',
            'native_foreground_rgba_sha256':rgba(piece),'native_alpha_unchanged':True,'scale':1}
    carpet_roles={'top-left':620,'top':621,'top-right':622,'left':631,'center':627,
        'right':623,'bottom-left':628,'bottom':629,'bottom-right':630}
    carpet_modules={}
    for role,mid in carpet_roles.items():
        sx,sy=mid%16*16,mid//16*16;rect=(sx,sy,sx+16,sy+16)
        flat=Image.alpha_composite(planes['bottom'].crop(rect),planes['top'].crop(rect))
        assert flat.tobytes()==planes['flat'].crop(rect).tobytes()
        assert rgba(flat)==metadata[mid]['pixel_sha256']and flat.getchannel('A').getextrema()==(255,255)
        filename='carpet-'+role+'.png';flat.save(out/filename);files[filename]=sha(out/filename)
        carpet_modules[role]={'asset':PREFIX+'/'+filename,'assetFileHash':files[filename],
            'assetPixelHash':rgba(flat),'native_metatile_id':mid,'native_plane':'flat',
            'source_rect_xywh':[sx,sy,16,16],'native_top_sha256':rgba(planes['top'].crop(rect)),
            'native_bottom_sha256':rgba(planes['bottom'].crop(rect)),
            'source_map_cells':[[n%8,n//8]for n,v in enumerate(md['grid'])if(v&1023)==mid],
            'complete_native_floor_module':True,'contains_furniture':False,'scale':1}
    roles=[['top-left','top','top','top','top','top-right'],
        ['left','center','center','center','center','right'],
        ['left','center','center','center','center','right'],
        ['bottom-left','bottom','bottom','bottom','bottom','bottom-right']]
    layout=[['carpet-'+r+'.png'for r in row]for row in roles]
    carpet_whole=Image.new('RGBA',(96,64))
    for y,row in enumerate(layout):
        for x,filename in enumerate(row):carpet_whole.paste(Image.open(out/filename).convert('RGBA'),(x*16,y*16))
    carpet={'width_cells':6,'height_cells':4,'layout':layout,'source_rect_xywh':[32,48,96,64],
        'placement_cells_xy':[2,3],'native_module_roles':carpet_modules,
        'assembly_rgba_sha256':rgba(carpet_whole),'assembly_size':[96,64],
        'recipe':'Arrange complete native clean carpet floor modules in the same6x4 rectangle as CrystalDust. Native clean FLAT carpet modules retain their own exact gray-floor exterior corners. Carpet artwork occupies TOP over native gray BOTTOM; copying BOTTOM alone would omit carpet. Furniture is independently composed above these floor modules.',
        'native_carpet_plane':'flat (bottom+top)','new_pixels_generated':False}
    proof={'format':1,'origin':'CrystalDust by Sierraffinity and contributors',
        'sourceUrl':'https://github.com/Sierraffinity/CrystalDust',
        'purpose':'Complete native Mr. Pokemon research machine, preserving its original size and alpha.',
        'recipe':'Six intact 16x16 TOP-plane modules from CrystalDust Mr. Pokemon House cells6..7,0..2. Assemble at1:1 native pixel scale. No crop of opaque pixels, color keying, recoloring, generated pixels or scaling.',
        'source_rom_sha256':catalog['rom_sha256'],'source_catalog_sha256':sha(catalog_path),
        'source_map_id':md['id'],'source_pair':PAIR,'source_map_metatiles_sha256':sha(directory/'metatiles.json'),
        'source_map_png_sha256':sha(source/'maps/g02_m006-flat.png'),
        'source_map_rgba_sha256':rgba(native_map),'source_map_rect_xywh':[96,0,32,48],
        'source_planes':{n:{'path':str((directory/(n+'.png')).resolve()),'sha256':sha(directory/(n+'.png'))}for n in planes},
        'files':files,'source_modules':modules,'native_wall_compounds':compounds,'carpet':carpet,
        'whole':{'asset':PREFIX+'/'+name,'assetFileHash':files[name],'assetPixelHash':rgba(whole),
            'canvas':[32,48],'opaque_bounds_xyxy':list(whole.getbbox()),'native_opaque_pixels':sum(p[3]!=0 for p in whole.get_flattened_data()),
            'parts':parts,'native_alpha_unchanged':True,'scale':1}}
    (out/'provenance.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'passed','pngs':len(files),'native_canvas':[32,48],
        'opaque_bounds':whole.getbbox(),'native_opaque_pixels':proof['whole']['native_opaque_pixels'],
        'carpet_size':[96,64],'carpet_metatiles':carpet_roles,
        'output':str(out)},indent=2))
if __name__=='__main__':main()
