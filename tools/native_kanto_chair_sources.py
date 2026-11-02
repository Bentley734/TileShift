"""Keep the complete native north chair and substitute the native casino blue ramp.

The S.S. Tidal chair crosses two metatiles at their8px boundary. The desk
behind it is a separate component; no chair pixels, rows, legs or frame parts
are resized, rotated, mirrored, rearranged or removed.
"""
import argparse,hashlib,json,os
from pathlib import Path
from PIL import Image,ImageDraw
import catalog,preview
from interior_review import Imports
from native_room_parts import RoomParts

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'.work/tileshift-chair-directions'
DEST=ROOT/'assets/third_party/native-kanto-chairs'
SOURCE_REFS={673:'8385893549108fa02b091185a3143457ba4fe8080afda07597fd5a19e1fd354c',
             674:'862b0ef8fbacf9e9b7b8ea1aa2246d5989bb5ea85ea5a6b4ce33b42a34c5765f'}
# All target colors are literal colors from FireRed casino683's native MID.
COLOR_MAP={
    (74,74,99,255):(82,82,107,255),
    (148,107,58,255):(74,132,197,255),
    (189,140,58,255):(140,197,255,255),
    (214,189,132,255):(255,255,255,255),
}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--activate',action='store_true');args=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);cache=Path(os.environ['APPDATA'])/'pokemon-love2d'
    imp=Imports(cache,ROOT.parent/'.work/tileshift-catalog');room=RoomParts(imp,'emerald','EM_SS_TIDAL_ROOMS')
    assert room.layout['mids'][3*room.layout['width']+28]==673
    assert room.layout['mids'][3*room.layout['width']+29]==674
    raw=Image.new('RGBA',(16,16));pieces=[]
    for mid,sx,dx in((673,8,0),(674,0,8)):
        ref=room.ref(mid);assert ref['hash']==SOURCE_REFS[mid]
        rec=imp.cell_index('emerald')[room.pair,mid]
        image=preview.replacement_image(cache,dict(kind='native_composite',parts=[dict(donor=ref,
            layers=['mid'],layerHashes={'mid':rec['layer_sha256']['mid']},w=16,h=16)]),imp.packed,ROOT)
        raw.paste(image.crop((sx,0,sx+8,16)),(dx,0))
        pieces.append(dict(donor=ref,layer='mid',layer_rgba_sha256=rec['layer_sha256']['mid'],
            source_rect=[sx,0,8,16],destination=[dx,0]))
    # Verify the same native pixels against a second direct-ROM decoder.
    from firegold_extract import Rom,BASE
    rom=Rom(ROOT.parent/'Emerald.gba','rse');native=rom.pair(BASE+0x3df704,BASE+0x3dfc44)
    for piece in pieces:
        assert catalog.sha(native[piece['donor']['id']]['mid'].tobytes())==piece['layer_rgba_sha256']
    gray_desk=(206,206,197,255);omit={(x,y)for y in range(16)for x in range(16)if raw.getpixel((x,y))==gray_desk}
    assert len(omit)==17
    # The desk's straight lower lip extends into the left/right outside
    # margins on row2. The actual chair side posts are x2 and x14.
    lip={(0,2),(1,2),(15,2)}
    assert all(raw.getpixel(xy)==(74,74,99,255)for xy in lip)
    omit|=lip;native_chair=raw.copy();blue=Image.new('RGBA',(16,16));retained=0
    casino=RoomParts(imp,'firered','FR_CELADON_CITY_GAME_CORNER');ref=casino.ref(683)
    rec=imp.cell_index('firered')[casino.pair,683]
    casino_image=preview.replacement_image(cache,dict(kind='native_composite',parts=[dict(donor=ref,
        layers=['mid'],layerHashes={'mid':rec['layer_sha256']['mid']},w=16,h=16)]),imp.packed,ROOT)
    casino_colors=set(casino_image.get_flattened_data())
    assert set(COLOR_MAP.values())<=casino_colors
    for y in range(16):
        for x in range(16):
            color=raw.getpixel((x,y))
            if(x,y)in omit:native_chair.putpixel((x,y),(0,0,0,0));continue
            if not color[3]:continue
            assert color in COLOR_MAP,('Unidentified native chair material',x,y,color)
            blue.putpixel((x,y),COLOR_MAP[color]);retained+=1
    assert blue.getbbox()==native_chair.getbbox()==(2,0,15,16)
    assert all((native_chair.getpixel((x,y))[3]>0)==(blue.getpixel((x,y))[3]>0)for y in range(16)for x in range(16))
    target=(DEST if args.activate else OUT)/'north-blue.png';target.parent.mkdir(parents=True,exist_ok=True);blue.save(target)
    proof=dict(origin='Complete native Emerald S.S. Tidal north-facing chair; exact FireRed casino blue palette substitution only.',
        credit='Original Pokemon Emerald/FireRed chair artwork / Game Freak; native geometry and native palette colors.',
        sourceUrl='https://github.com/pret/pokeemerald',source_game='emerald',source_rom_name='Emerald.gba',
        source_rom_sha256=rom.sha256,source_map=room.map,source_map_cells=[[28,3],[29,3]],
        source_pixel_rect=[456,48,16,16],source_tileset=room.pair,native_parts=pieces,
        facing='north',facing_evidence='The whole slatted chair is directly below the native cabin desk; its back faces south toward the viewer and its seat faces north toward the desk.',
        omitted_gray_desk_board_coordinates=sorted(omit-lip),omitted_dark_desk_lip_coordinates=sorted(lip),
        all_chair_wood_pixels_retained=True,all_chair_side_posts_and_feet_retained=True,
        palette_reference=dict(donor=ref,layer='mid',layer_rgba_sha256=rec['layer_sha256']['mid']),
        palette_substitution=[dict(source=list(a),target=list(b))for a,b in COLOR_MAP.items()],
        pixel_scale=1,dimensions=[16,16],source_raw_rgba_sha256=catalog.sha(raw.tobytes()),
        retained_native_rgba_sha256=catalog.sha(native_chair.tobytes()),target_rgba_sha256=catalog.sha(blue.tobytes()),
        native_pixels_retained=retained,target_opaque_pixels=retained,only_nonchair_desk_pixels_removed=len(omit),
        source_and_target_alpha_identical=True,independent_direct_rom_pixel_verification=True,
        files={'north-blue.png':catalog.sha(target.read_bytes())})
    (DEST if args.activate else OUT).joinpath('provenance.json').write_text(json.dumps(proof,indent=2)+'\n')
    raw.save(OUT/'north-source-with-desk.png');native_chair.save(OUT/'north-native-chair.png')
    contact=Image.new('RGB',(3*224,270),(26,32,42));draw=ImageDraw.Draw(contact)
    for x,(label,image)in enumerate((('Source with desk edge',raw),('Whole native chair',native_chair),('Native casino blue ramp',blue))):
        scaled=image.resize((192,192),Image.Resampling.NEAREST);contact.paste(scaled,(x*224,40),scaled);draw.text((x*224+4,12),label,fill='white')
    draw.text((4,242),f'{retained} native chair pixels; original16x16 geometry; only desk board/lip removed.',fill='white')
    contact.save(OUT/'north-chair-source-palette-comparison.png')
    print(json.dumps({k:proof[k]for k in('native_pixels_retained','only_nonchair_desk_pixels_removed','retained_native_rgba_sha256','target_rgba_sha256','files')},indent=2))

if __name__=='__main__':main()
