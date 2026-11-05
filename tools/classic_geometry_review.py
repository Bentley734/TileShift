"""Guarded, explicitly named four-color derivatives of unique static features.

This does not choose artwork or assign tiles. Authors provide the whole-feature
decision, four reviewed colors and a literal mapping for every opaque source
RGB. Coordinates, alpha and all native priority planes remain unchanged.
"""
from pathlib import Path
import re
import zlib
import catalog


def source_under_frames(cache, game, pair, mid, packed, animation):
    """Decode the pinned RSE UNDER bank exactly as the native atlas writer."""
    assert game in ('ruby', 'sapphire', 'emerald')
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
    assert bank['kind'] == 'tiles' and mid not in bank.get('overMids', ())
    assert bank['mids'].count(mid) == 1 and re.fullmatch(r'[\w-]+\.idx', bank['file'], re.ASCII)
    index = bank['mids'].index(mid)
    flags = bank.get('quads', [])
    flags = flags[index] if len(flags) > index else 15
    assert type(flags) is int and 1 <= flags <= 15 and 2 <= bank['frames'] <= 256
    key = ('classic_under_bank', game, pair, bank['name'])
    if key not in packed:
        data = (path.parent / bank['file']).read_bytes()
        size = bank['frames'] * len(bank['mids']) * 256
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
    for phase in range(bank['frames']):
        offset = (phase * len(bank['mids']) + index) * 256
        layer = bytearray(under)
        for i in range(256):
            quadrant = (i // 16 // 8) * 2 + (i % 16 // 8)
            if flags & (1 << quadrant):
                layer[i] = data[offset+i]
                if palette[layer[i]] != palette[under[i]]:
                    changed.add(i)
        frames.append(catalog.rgba_native(layer, palette, False))
    opaque_middle = {i for i in changed if middle is not None and middle[i]}
    middle_overlap = {i for i in opaque_middle if palette[middle[i]] == palette[under[i]]}
    if animation['mode'] == 'native_under':
        assert changed, 'Native under animation does not change source pixels'
        assert opaque_middle == middle_overlap, (
            'Native under animation overlaps a distinct middle pixel', game, pair, mid)
    if animation['mode'] == 'static_equivalent':
        assert not changed, 'Source animation is not exactly static'
    return frames, changed, middle_overlap


def static_manifest(cache, game, pair, mid, packed, ground_masks=None, native_over=None,
                    source_animation=None):
    path=Path(cache)/game/'data/generated/gba/native'/pair/'anim_manifest.lua'
    raw=path.read_bytes() if path.is_file() else b''
    spec=catalog.read_lua(path) if raw else {}
    mids,_,planes=packed[game,pair];slot=mids.index(mid)
    if ground_masks is not None:assert all(len(mask)==256 and set(mask)<={'0','1'}for mask in ground_masks.values())
    duplicate_mid='mid'in planes and planes['mid'][slot*256:(slot+1)*256]==planes['under'][slot*256:(slot+1)*256]
    retained_over=False
    checked_source_animation=False
    banks=spec.get('banks',[])
    if isinstance(banks,dict):banks=list(banks.values())
    if game in ('firered','leafgreen'):
        banks=list(banks)+[spec[k] for k in ('water','sand','flower') if k in spec]
    def covered(name,offset):return ground_masks is not None and ground_masks.get(name,'0'*256)[offset]=='1'
    for bank in banks:
        for field,quads,name in (('mids','quads','under'),('overMids','overQuads','over')):
            for index,source_id in enumerate(bank.get(field,[])):
                if source_id!=mid:continue
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
                if name == 'under' and source_animation and bank.get('name') == source_animation['bank']:
                    assert not checked_source_animation
                    _, changed, middle_overlap = source_under_frames(cache, game, pair, mid, packed, source_animation)
                    if source_animation['mode'] == 'water_mask':
                        assert all(covered('under', i) for i in changed)
                        assert all(covered('mid', i) for i in middle_overlap), (
                            'Duplicate source water middle pixel also needs a mask')
                    checked_source_animation=True
                    continue
                for offset in range(256):
                    q=(offset//16//8)*2+(offset%16//8)
                    if bits&(1<<q):
                        assert covered(name,offset),('Animated native feature requires an animation recipe covering every source quadrant',game,pair,mid,bank.get('name'))
                        if name=='under'and duplicate_mid:assert covered('mid',offset),'Duplicate native water middle plane also needs animated ground coverage'
        if bank.get('kind')=='palette' and 'paletteSlot' in bank:
            for layer,blob in planes.items():
                assert all(p//16!=bank['paletteSlot']or covered(layer,i)for i,p in enumerate(blob[slot*256:(slot+1)*256])if layer=='under'or p!=0),('Native palette animation requires an animation recipe',game,pair,mid,bank.get('name'))
    assert not native_over or retained_over,'Native foreground bank does not own this source cell'
    assert not source_animation or checked_source_animation,'Classic source animation bank does not own this source cell'
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
        assert ground['donor']['game']=='crystal' and {'donor','masks'}<=set(ground)<={'donor','masks','animation','repeatWidth'}
        if 'repeatWidth'in ground:assert ground['repeatWidth']==8 and ground.get('animation',{}).get('bank')=='program'
        assert ground['masks'] and set(ground['masks'])<=set(source)
        assert all(len(mask)==256 and set(mask)<={'0','1'} for mask in ground['masks'].values())
        assert any('1'in mask for mask in ground['masks'].values())
        for name,mask in ground['masks'].items():
            assert all(bit=='0'or source[name].getpixel((i%16,i//16))[3]==255 for i,bit in enumerate(mask))
        review.gb_image(ground['donor'])
        result['classicGeometry']['ground']=copy.deepcopy(ground)
    return result
