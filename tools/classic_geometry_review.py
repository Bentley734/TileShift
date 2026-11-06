"""Guarded, explicitly named four-color derivatives of unique static features.

This does not choose artwork or assign tiles. Authors provide the whole-feature
decision, four reviewed colors and a literal mapping for every opaque source
RGB. Coordinates, alpha and all native priority planes remain unchanged.
"""
from pathlib import Path
import re
import struct
import zlib
import catalog


def legacy_source_under_frames(cache, game, pair, mid, packed, animation):
    """Verify the baked, opaque legacy FRLG water or sand UNDER frames."""
    from PIL import Image
    assert set(animation) == {'mode', 'bank', 'hash'}
    assert animation['mode'] in ('water_mask', 'static_equivalent')
    name = animation['bank']
    assert name in ('water', 'sand')
    path = Path(cache) / game / 'data/generated/gba/native' / pair / 'anim_manifest.lua'
    manifest = catalog.read_lua(path)
    assert manifest.get('family') in (None, 'frlg')
    bank = manifest[name]
    assert bank['frames'] == 8 and bank['mids'].count(mid) == 1
    index = bank['mids'].index(mid)
    key = ('classic_legacy_under_bank', game, pair, name)
    if key not in packed:
        data = (path.parent / f'anim_{name}.rgba').read_bytes()
        size = 8 * len(bank['mids']) * 1024
        if len(data) != size:
            data = zlib.decompress(data)
        assert len(data) == size
        packed[key] = data, catalog.sha(data)
    data, fingerprint = packed[key]
    assert fingerprint == animation['hash'], 'Classic legacy source animation bank changed'
    mids, palette, planes = packed[game, pair]
    offset = mids.index(mid) * 256
    under = planes['under'][offset:offset + 256]
    mid_plane = planes.get('mid')
    middle = mid_plane[offset:offset + 256] if mid_plane else bytes(256)
    base = catalog.rgba_native(bytes(m or u for m, u in zip(middle, under)), palette, False).tobytes()
    frames, changed = [], set()
    for phase in range(8):
        start = (phase * len(bank['mids']) + index) * 1024
        frame = data[start:start + 1024]
        assert frame[3::4] == b'\xff' * 256, 'Classic legacy source animation changes UNDER alpha'
        changed.update(i // 4 for i in range(0, 1024, 4) if frame[i:i + 4] != base[i:i + 4])
        frames.append(Image.frombytes('RGBA', (16, 16), frame))
    if animation['mode'] == 'static_equivalent':
        assert not changed, 'Source animation is not exactly static'
    return frames, changed, {i for i in changed if middle[i]}


def source_under_frames(cache, game, pair, mid, packed, animation):
    """Decode the pinned UNDER bank exactly as the native atlas writer."""
    if game in ('firered', 'leafgreen'):
        return legacy_source_under_frames(cache, game, pair, mid, packed, animation)
    assert game in ('ruby', 'sapphire', 'emerald')
    if 'secondary'in animation:
        return overlapping_source_under_frames(cache,game,pair,mid,packed,animation)
    assert set(animation) == {'mode', 'bank', 'hash'}
    assert animation['mode'] in ('water_mask', 'native_under', 'static_equivalent')
    path = Path(cache) / game / 'data/generated/gba/native' / pair / 'anim_manifest.lua'
    manifest = catalog.read_lua(path)
    banks = manifest.get('banks', [])
    if isinstance(banks, dict):
        banks = list(banks.values())
    selected = [bank for bank in banks if bank.get('name') == animation['bank']]
    assert manifest.get('family') == 'rse' and len(selected) == 1
    bank = selected[0]
    assert bank['kind'] in ('tiles','palette') and 2 <= bank['frames'] <= 256
    if bank['kind']=='palette':
        assert animation['mode']!='water_mask' and re.fullmatch(r'[\w-]+\.pal',bank['file'],re.ASCII)
        palette_slot=bank['paletteSlot'];assert type(palette_slot)is int and 0<=palette_slot<=15
        size=bank['frames']*32
    else:
        assert mid not in bank.get('overMids', ()) and bank['mids'].count(mid)==1
        assert re.fullmatch(r'[\w-]+\.idx',bank['file'],re.ASCII)
        index=bank['mids'].index(mid)
        quads=bank.get('quads',[])
        flags=quads[index]if len(quads)>index else 15
        assert type(flags)is int and 1<=flags<=15
        size=bank['frames']*len(bank['mids'])*256
    key = ('classic_under_bank', game, pair, bank['name'])
    if key not in packed:
        data = (path.parent / bank['file']).read_bytes()
        if len(data) != size:
            data = zlib.decompress(data)
        assert len(data) == size
        packed[key] = data, catalog.sha(data)
    data, fingerprint = packed[key]
    assert fingerprint == animation['hash'], 'Classic source animation bank changed'
    mids, palette, planes = packed[game, pair]
    source_slot = mids.index(mid) * 256
    under = planes['under'][source_slot:source_slot+256]
    middle = planes['mid'][source_slot:source_slot+256] if 'mid' in planes else None
    frames, changed = [], set()
    if bank['kind']=='palette':
        start=palette_slot*16
        over=planes.get('over',b'')[source_slot:source_slot+256]
        assert any(byte//16==palette_slot and (name=='under'or byte!=0)
                   for name,blob in planes.items()for byte in blob[source_slot:source_slot+256])
        for phase in range(bank['frames']):
            bgr=struct.unpack_from('<16H',data,phase*32)
            values=[tuple((((c>>shift)&31)*255+15)//31 for shift in (0,5,10))for c in bgr]
            colors=list(palette);colors[start:start+16]=values
            assert all(not byte or colors[byte]==palette[byte]for byte in over), 'Classic source palette animation changes native foreground pixels'
            changed.update(i for i,byte in enumerate(under)if colors[byte]!=palette[byte])
            frames.append(catalog.rgba_native(under,colors,False))
    else:
        for phase in range(bank['frames']):
            offset=(phase*len(bank['mids'])+index)*256
            layer=bytearray(under)
            for i in range(256):
                quadrant=(i//16//8)*2+(i%16//8)
                if flags&(1<<quadrant):
                    layer[i]=data[offset+i]
                    if palette[layer[i]]!=palette[under[i]]:changed.add(i)
            frames.append(catalog.rgba_native(layer,palette,False))
    opaque_middle = {i for i in changed if middle is not None and middle[i]}
    middle_overlap = {i for i in opaque_middle if palette[middle[i]] == palette[under[i]]}
    if animation['mode'] == 'native_under':
        assert changed, 'Native under animation does not change source pixels'
        assert opaque_middle == middle_overlap, (
            'Native under animation overlaps a distinct middle pixel', game, pair, mid)
    if animation['mode'] == 'static_equivalent':
        assert not changed, 'Source animation is not exactly static'
    return frames, changed, middle_overlap


def overlapping_source_under_frames(cache,game,pair,mid,packed,animation):
    assert set(animation)=={'mode','bank','hash','secondary'} and animation['mode']=='native_under'
    secondary=animation['secondary'];assert set(secondary)=={'bank','hash'} and secondary['bank']!=animation['bank']
    manifest=catalog.read_lua(Path(cache)/game/'data/generated/gba/native'/pair/'anim_manifest.lua')
    bank_rows=manifest['banks']
    if isinstance(bank_rows,dict):bank_rows=bank_rows.values()
    programs=[]
    for spec in (dict(mode='native_under',bank=animation['bank'],hash=animation['hash']),
                 dict(mode='native_under',**secondary)):
        bank,= [row for row in bank_rows if row['name']==spec['bank']]
        assert bank['kind']=='tiles' and bank['mids'].count(mid)==1 and mid not in bank.get('overMids',())
        index=bank['mids'].index(mid);quads=bank.get('quads',[])
        flags=quads[index]if index<len(quads)else 15
        frames,_,_=source_under_frames(cache,game,pair,mid,packed,spec)
        programs.append((frames,flags))
    (first,first_flags),(second,second_flags)=programs
    assert len(first)+len(second)+2*len(first)*len(second)<=256

    def overwrite(base,frame,flags):
        result=base.copy()
        for q in range(4):
            if flags&(1<<q):
                x,y=q%2*8,q//2*8
                result.paste(frame.crop((x,y,x+8,y+8)),(x,y))
        return result

    frames=[*first,*second]
    for a in first:
        for b in second:
            frames.extend((overwrite(a,b,second_flags),overwrite(b,a,first_flags)))
    mids,palette,planes=packed[game,pair];offset=mids.index(mid)*256
    under=planes['under'][offset:offset+256]
    base=list(catalog.rgba_native(under,palette).get_flattened_data())
    changed={i for frame in frames for i,pixel in enumerate(frame.get_flattened_data())if pixel!=base[i]}
    assert changed
    mid_plane=planes.get('mid',b'')[offset:offset+256]
    duplicate={i for i in changed if mid_plane and mid_plane[i]}
    assert all(palette[mid_plane[i]]==palette[under[i]]for i in duplicate), 'Combined animation overlaps a distinct middle pixel'
    return frames,changed,duplicate


def static_manifest(cache, game, pair, mid, packed, ground_masks=None, native_over=None,
                    source_animation=None):
    path=Path(cache)/game/'data/generated/gba/native'/pair/'anim_manifest.lua'
    raw=path.read_bytes() if path.is_file() else b''
    spec=catalog.read_lua(path) if raw else {}
    mids,_,planes=packed[game,pair];slot=mids.index(mid)
    if ground_masks is not None:assert all(len(mask)==256 and set(mask)<={'0','1'}for mask in ground_masks.values())
    duplicate_mid='mid'in planes and planes['mid'][slot*256:(slot+1)*256]==planes['under'][slot*256:(slot+1)*256]
    retained_over=False
    source_banks={source_animation['bank']}if source_animation else set()
    if source_animation and source_animation.get('secondary'):source_banks.add(source_animation['secondary']['bank'])
    checked_source_banks=set()
    banks=spec.get('banks',[])
    if isinstance(banks,dict):banks=list(banks.values())
    if game in ('firered','leafgreen'):
        banks=list(banks)+[dict(spec[k],name=k,kind='legacy_rgba') for k in ('water','sand','flower') if k in spec]
    def covered(name,offset):return ground_masks is not None and ground_masks.get(name,'0'*256)[offset]=='1'
    for bank in banks:
        for field,quads,name in (('mids','quads','under'),('overMids','overQuads','over')):
            for index,source_id in enumerate(bank.get(field,[])):
                if source_id!=mid:continue
                if source_animation and game in ('firered','leafgreen'):
                    assert bank.get('kind')=='legacy_rgba' and bank['name']==source_animation['bank'] and name=='under', (
                        'Classic legacy source cell uses multiple animation banks')
                flags=bank.get(quads,[]);bits=flags[index]if len(flags)>index else 15
                assert type(bits)is int and 0<=bits<=15
                if name=='over'and native_over and bank.get('name')==native_over['bank']:
                    assert not retained_over and 'over'in planes and bits>0 and bank['kind']=='tiles' and bank.get('overFile')
                    assert bool(bank.get('file')) == bool(bank.get('mids')) and mid not in bank.get('mids', ())
                    key=('retained_native_over',game,pair,native_over['bank'])
                    if key not in packed:
                        filename=bank['overFile'];assert Path(filename).name==filename
                        data=(path.parent/filename).read_bytes();size=bank['frames']*len(bank['overMids'])*256
                        if len(data)!=size:data=zlib.decompress(data)
                        assert len(data)==size
                        packed[key]=catalog.sha(data)
                    assert packed[key]==native_over['hash'],'Native foreground bank changed'
                    retained_over=True
                    continue
                if name=='under' and bank.get('name')in source_banks:
                    assert bank['name']not in checked_source_banks
                    if not checked_source_banks:
                        _,changed,middle_overlap=source_under_frames(cache,game,pair,mid,packed,source_animation)
                        if source_animation['mode']=='water_mask':
                            assert all(covered('under',i)for i in changed)
                            assert all(covered('mid',i)for i in middle_overlap),'Animated source water middle pixel also needs a mask'
                    checked_source_banks.add(bank['name'])
                    continue
                for offset in range(256):
                    q=(offset//16//8)*2+(offset%16//8)
                    if bits&(1<<q):
                        assert covered(name,offset),('Animated native feature requires an animation recipe covering every source quadrant',game,pair,mid,bank.get('name'))
                        if name=='under'and duplicate_mid:assert covered('mid',offset),'Duplicate native water middle plane also needs animated ground coverage'
        if bank.get('kind')=='palette' and 'paletteSlot' in bank:
            if bank.get('name')in source_banks:
                assert not checked_source_banks and len(source_banks)==1
                source_under_frames(cache,game,pair,mid,packed,source_animation)
                checked_source_banks.add(bank['name'])
            else:
                for layer,blob in planes.items():
                    assert all(p//16!=bank['paletteSlot']or covered(layer,i)for i,p in enumerate(blob[slot*256:(slot+1)*256])if layer=='under'or p!=0),('Native palette animation requires an animation recipe',game,pair,mid,bank.get('name'))
    assert not native_over or retained_over,'Native foreground bank does not own this source cell'
    assert checked_source_banks==source_banks,'Classic source animation bank does not own this source cell'
    return catalog.sha(raw)


def art(review, game, pair, mid, feature, palette, colors, role=None, ground=None,
        native_over=None, source_animation=None):
    """Build one explicitly selected static member of a reviewed whole feature."""
    import preview
    assert isinstance(feature,str) and 1<=len(feature)<=96 and all(c.isascii() and (c.isalnum() or c in '_-') for c in feature)
    palette=[list(p) for p in palette]
    assert len(palette)==4 and len(set(map(tuple,palette)))==4
    assert all(len(p)==3 and all(type(c)is int and 0<=c<=255 for c in p) for p in palette)
    cell=review.imp.cell_index(game)[pair,mid]
    preview.native_donor(review.cache,dict(game=game,tileset=pair,id=mid,hash=cell['pixel_sha256']),review.packed)
    mids,native_palette,planes=review.packed[game,pair];slot=mids.index(mid)
    source={name:catalog.rgba_native(blob[slot*256:(slot+1)*256],native_palette,name!='under') for name,blob in planes.items()}
    # The native decoder always emits an empty over plane even in a two-plane
    # import; keep that convention explicit rather than flattening priority.
    if 'over' not in source:
        from PIL import Image
        source['over']=Image.new('RGBA',(16,16))
    if native_over:
        assert game in ('ruby','sapphire','emerald')and set(native_over)=={'bank','hash'}
        assert not ground or 'over'not in ground['masks']
        assert not source_animation or source_animation['mode']=='water_mask'
    used={p[:3]for name,image in source.items()if name!='over'or not native_over for p in image.get_flattened_data()if p[3]}
    if source_animation and source_animation['mode'] == 'native_under':
        frames, changed, _ = source_under_frames(review.cache, game, pair, mid, review.packed, source_animation)
        assert not native_over and not (ground and ground.get('animation'))
        if ground:
            masks = ground['masks']
            empty = '0' * 256
            assert all(masks.get(name, empty)[i] == '0' for name in ('under', 'mid') for i in changed)
        used.update(pixel[:3] for frame in frames for pixel in frame.get_flattened_data())
    mapping={tuple(k):tuple(v) for k,v in colors.items()}
    assert used<=set(mapping),('Incomplete literal RGB map',game,pair,mid,used-set(mapping))
    assert set(mapping.values())<=set(map(tuple,palette))
    entries=[list(rgb)+list(mapping[rgb]) for rgb in sorted(used)]
    assert 1<=len(entries)<=256
    result=dict(kind='classic_native_geometry',role=role or feature,
        classicGeometry=dict(version=1,static=True,feature=feature,palette=palette,colorMap=entries,
            sourceLayers={name:catalog.sha(im.tobytes()) for name,im in source.items()},
            animationManifestHash=static_manifest(review.cache,game,pair,mid,review.packed,
                ground['masks']if ground and ground.get('animation')else None,native_over,source_animation)))
    if native_over:result['classicGeometry']['nativeOver']=dict(native_over)
    if source_animation:result['classicGeometry']['sourceAnimation']=dict(source_animation)
    if ground is not None:
        import copy
        donor=ground['donor']
        assert donor['game']=='crystal' or (donor['game']=='red' and donor.get('monochrome') is True)
        assert {'donor','masks'}<=set(ground)<={'donor','masks','animation','repeatWidth'}
        if 'repeatWidth'in ground:assert ground['repeatWidth']==8 and ground.get('animation',{}).get('bank')=='program'
        assert ground['masks'] and set(ground['masks'])<=set(source)
        assert all(len(mask)==256 and set(mask)<={'0','1'} for mask in ground['masks'].values())
        assert any('1'in mask for mask in ground['masks'].values())
        for name,mask in ground['masks'].items():
            assert all(bit=='0'or source[name].getpixel((i%16,i//16))[3]==255 for i,bit in enumerate(mask))
        review.gb_image(ground['donor'])
        result['classicGeometry']['ground']=copy.deepcopy(ground)
    return result
