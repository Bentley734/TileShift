"""Read user supplied FRLG/RSE Johto hacks without modifying ROMs or imports.

Exports private native-scale map backgrounds, separate native half layers,
tileset-pair atlases and source-address metadata. Structural pointer discovery
allows rebuilt/decompiled hacks whose tables have moved. No ROM is bundled.
"""
from pathlib import Path
import argparse, hashlib, json, struct, re
from PIL import Image, ImageDraw

BASE = 0x08000000


class Rom:
    def __init__(self, path, family):
        self.path = Path(path)
        self.raw = self.path.read_bytes()
        self.words = memoryview(self.raw).cast('I')
        self.family = family
        self.sha256 = hashlib.sha256(self.raw).hexdigest()
        self.primary = 640 if family == 'frlg' else 512
        self.primary_tiles = self.primary
        self.primary_pals = 7 if family == 'frlg' else 6
        # CrystalDust retains Emerald's512-metatile bank but expands graphics
        # bank to FRLG's640 tiles. Palette split remains Emerald's6. Pin this
        # expansion to the exact user-supplied ROM, never to a filename.
        if self.sha256 == '51196cba923c315d0088b747b5cdee704f2ac057cd493f9ddf226fb7227302cf':
            self.primary_tiles = 640
        self.attr_size = 4 if family == 'frlg' else 2
        self.ts_cache, self.pair_cache = {}, {}
        self.callback_offsets = set()

    def u16(self, at): return struct.unpack_from('<H', self.raw, at)[0]
    def u32(self, at): return struct.unpack_from('<I', self.raw, at)[0]
    def ptr(self, value): return BASE <= value < BASE + len(self.raw)
    def off(self, value):
        assert self.ptr(value), hex(value)
        return value - BASE

    def is_ts(self, value, secondary):
        if not self.ptr(value): return False
        p = value - BASE
        return p + 24 < len(self.raw) and self.raw[p] in (0, 1) and self.raw[p+1] == secondary and all(self.ptr(self.u32(p+d)) for d in (4, 8, 12))

    def discover(self):
        a = self.words
        layouts = {i*4 for i, w in enumerate(a[:-6]) if 1 <= w <= 256 and 1 <= a[i+1] <= 256 and self.ptr(a[i+2]) and self.ptr(a[i+3]) and self.is_ts(a[i+4], 0) and self.is_ts(a[i+5], 1)}
        headers = {i*4 for i, w in enumerate(a[:-7]) if w-BASE in layouts and all(a[i+d] == 0 or self.ptr(a[i+d]) for d in (1, 2, 3)) and 0 < self.u16(i*4+18) <= 2048 and self.raw[i*4+23] in range(16)}
        slots = {i*4 for i, w in enumerate(a) if w-BASE in headers}
        if self.sha256 == '925cd6bd824e3e903636340e5f3519bc9ecb2f5f75c0bb87248213250514c965':
            # AdvanceMap's relocated data can start at any byte offset.
            dimension = rb'(?:[\x01-\xff]\x00\x00\x00|\x00\x01\x00\x00)'
            for match in re.finditer(dimension+dimension, self.raw):
                p = match.start()
                if self.ptr(self.u32(p+8)) and self.ptr(self.u32(p+12)) and self.is_ts(self.u32(p+16),0) and self.is_ts(self.u32(p+20),1): layouts.add(p)
            for lp in layouts:
                needle = struct.pack('<I',lp+BASE); at = 0
                while True:
                    h = self.raw.find(needle, at)
                    if h < 0: break
                    at = h+1
                    if h+28 < len(self.raw) and all(self.u32(h+d)==0 or self.ptr(self.u32(h+d)) for d in (4,8,12)) and self.u16(h+18)<=2048 and self.raw[h+23]<16: headers.add(h)
            for h in headers:
                needle = struct.pack('<I',h+BASE); at = 0
                while True:
                    p = self.raw.find(needle, at)
                    if p < 0: break
                    at = p+1; slots.add(p)
        runs = []
        for p in (i*4 for i, w in enumerate(a) if w-BASE in slots):
            if runs and runs[-1][-1]+4 == p: runs[-1].append(p)
            else: runs.append([p])
        group_run = max(runs, key=len)
        if self.sha256 == '925cd6bd824e3e903636340e5f3519bc9ecb2f5f75c0bb87248213250514c965':
            # Liquid Crystal retains FR1.0's group table with deliberately
            # unused slots. The structural consecutive run is fragmented.
            group_run = list(range(0x3526a8, 0x3526a8+43*4, 4))
        else: assert len(group_run) >= 10
        groups = [self.off(self.u32(p)) if self.ptr(self.u32(p)) else None for p in group_run]
        maps = []
        for g, start in enumerate(groups):
            if start is None: continue
            ends = [p for p in groups if p is not None and p > start]
            end = min(ends) if ends else start+512*4
            for num, p in enumerate(range(start, min(end,start+256*4), 4)):
                # Relocated hacks leave unused slots inside a map bank;
                # these do not renumber or terminate later valid map IDs.
                if p not in slots: continue
                h = self.off(self.u32(p)); lp = self.off(self.u32(h))
                maps.append({'id': f'g{g:02d}_m{num:03d}', 'group': g, 'num': num,
                    'header_offset': h, 'layout_offset': lp, 'width': self.u32(lp), 'height': self.u32(lp+4),
                    'region': self.raw[h+20], 'map_type': self.raw[h+23], 'layout_id': self.u16(h+18),
                    'primary_tileset': self.u32(lp+16), 'secondary_tileset': self.u32(lp+20),
                    'grid_offset': self.off(self.u32(lp+12)), 'border_offset': self.off(self.u32(lp+8))})
                maps[-1]['warps'] = self.warps(self.u32(h+4))
        # Adjacent one-record callback tables are not always FF-terminated.
        # The next callback pointer explicitly referenced by a live tileset
        # is an authoritative boundary between descriptor arrays.
        for m in maps:
            for key in ('primary_tileset','secondary_tileset'):
                at = self.off(m[key])+(16 if self.family == 'frlg' else 20)
                pointer = self.u32(at)
                if self.ptr(pointer) and not pointer & 1: self.callback_offsets.add(self.off(pointer))
        return {'group_table_offset': group_run[0], 'group_count': len(groups), 'layout_candidates': len(layouts), 'maps': maps}

    def warps(self, events_ptr):
        if not self.ptr(events_ptr): return []
        p = self.off(events_ptr); count = self.raw[p+1]
        if not count: return []
        wp = self.u32(p+8)
        if not self.ptr(wp): return []
        wp = self.off(wp)
        return [{'x':self.u16(wp+i*8), 'y':self.u16(wp+i*8+2),
                 'elevation':self.raw[wp+i*8+4], 'dest_warp':self.raw[wp+i*8+5],
                 'dest_num':self.raw[wp+i*8+6], 'dest_group':self.raw[wp+i*8+7]} for i in range(count)]

    def lz(self, at):
        assert self.raw[at] == 0x10, hex(at)
        length = int.from_bytes(self.raw[at+1:at+4], 'little'); at += 4
        assert length <= 2**20
        out = bytearray()
        while len(out) < length:
            flags = self.raw[at]; at += 1
            for bit in range(7, -1, -1):
                if flags & (1 << bit):
                    x, y = self.raw[at:at+2]; at += 2
                    count, dist = (x >> 4)+3, ((x & 15) << 8)+y+1
                    assert dist <= len(out)
                    for _ in range(count): out.append(out[-dist])
                else: out.append(self.raw[at]); at += 1
                if len(out) >= length: break
        return bytes(out[:length])

    def animation_records(self, pointer):
        """FireGold custom tileset animation tables, identified structurally.

        Vanilla callback pointers are Thumb code; these even data pointers
        contain16-byte records pointing to a list of equal-size raw frames.
        Only checked ROM frame tables are accepted; code is never executed.
        """
        if not self.ptr(pointer) or pointer & 1: return []
        records = []; p = self.off(pointer)
        for i in range(32):
            at = p+i*16; table = self.u32(at)
            if i and at in self.callback_offsets: break
            if table == 0xffffffff: break
            if not self.ptr(table): return [] if i == 0 else records
            dest, count = self.u16(at+8), self.u16(at+12)
            if not (0 <= dest < 1024 and 1 <= count <= 256 and dest+count <= 1024): return [] if i == 0 else records
            table_off = self.off(table); frames = []
            for j in range(64):
                ptr = self.u32(table_off+j*4)
                if not self.ptr(ptr): break
                offset = self.off(ptr)
                if offset+count*32 > len(self.raw): break
                frames.append(offset)
            if not frames: return [] if i == 0 else records
            # More than one frame and the exact expected raw-frame stride
            # corroborate this is animation data rather than a code literal.
            if len(frames) > 1 and frames[1]-frames[0] != count*32: return [] if i == 0 else records
            records.append({'record_offset':at, 'frame_table_offset':table_off, 'dest_tile':dest,
                            'tile_count':count, 'frame_offsets':frames})
            # CrystalDust's callback pointer addresses one descriptor, with
            # unrelated descriptor structs packed immediately after it. Unlike
            # FireGold these are not FF-terminated descriptor arrays.
            if self.sha256 == '51196cba923c315d0088b747b5cdee704f2ac057cd493f9ddf226fb7227302cf': break
        return records

    def tileset(self, ptr):
        if ptr in self.ts_cache: return self.ts_cache[ptr]
        p = self.off(ptr); tiles, pals, mts = [self.off(self.u32(p+d)) for d in (4, 8, 12)]
        attr = self.off(self.u32(p+(20 if self.family == 'frlg' else 16)))
        secondary = bool(self.raw[p+1]); maximum = 1024-self.primary if secondary else self.primary
        count = min(maximum, (attr-mts)//16) if attr > mts else maximum
        if count < 1: count = maximum
        raw_tiles = self.lz(tiles) if self.raw[p] else self.raw[tiles:tiles+(1024-self.primary if secondary else self.primary)*32]
        entries = [struct.unpack_from('<8H', self.raw, mts+i*16) for i in range(count)]
        attrs = [int.from_bytes(self.raw[attr+i*self.attr_size:attr+(i+1)*self.attr_size], 'little') for i in range(count)]
        result = {'struct_offset': p, 'tiles_offset': tiles, 'palettes_offset': pals, 'metatiles_offset': mts,
                  'attributes_offset': attr, 'tile_count': len(raw_tiles)//32, 'metatile_count': count,
                  'tile_bytes': raw_tiles, 'palettes': [self.u16(pals+i*2) for i in range(256)], 'entries': entries, 'attrs': attrs,
                  'animations':self.animation_records(self.u32(p+(16 if self.family == 'frlg' else 20)))}
        self.ts_cache[ptr] = result
        return result

    def pair(self, primary_ptr, secondary_ptr):
        key = primary_ptr, secondary_ptr
        if key in self.pair_cache: return self.pair_cache[key]
        primary, secondary = self.tileset(primary_ptr), self.tileset(secondary_ptr)
        primary, secondary = dict(primary), dict(secondary)
        primary['tile_bytes'] = bytearray(primary['tile_bytes'].ljust(self.primary_tiles*32, b'\0'))
        secondary['tile_bytes'] = bytearray(secondary['tile_bytes'].ljust((1024-self.primary_tiles)*32, b'\0'))
        for spec in (primary, secondary):
            for anim in spec['animations']:
                dest = anim['dest_tile']; count = anim['tile_count']; at = anim['frame_offsets'][0]
                target, index = (primary, dest) if dest < self.primary_tiles else (secondary, dest-self.primary_tiles)
                target['tile_bytes'][index*32:(index+count)*32] = self.raw[at:at+count*32]
        pals = primary['palettes'][:self.primary_pals*16] + secondary['palettes'][self.primary_pals*16:13*16] + primary['palettes'][:16]*3
        for i in range(self.primary_pals): pals[i*16] = 0
        rgba = [(round((c & 31)*255/31), round(((c >> 5) & 31)*255/31), round(((c >> 10) & 31)*255/31), 255) for c in pals]
        all_cells = {}
        for mid in range(1024):
            ts, local = (primary, mid) if mid < self.primary else (secondary, mid-self.primary)
            if local >= len(ts['entries']): continue
            entries, attr = ts['entries'][local], ts['attrs'][local]
            layers = [Image.new('RGBA', (16, 16)) for _ in range(2)]
            for layer in (0, 1):
                pixels = layers[layer].load()
                for quadrant in range(4):
                    entry = entries[layer*4+quadrant]; tid = entry & 1023
                    tile_ts, tile_id = (primary, tid) if tid < self.primary_tiles else (secondary, tid-self.primary_tiles)
                    tile = tile_ts['tile_bytes'][tile_id*32:(tile_id+1)*32]
                    if len(tile) != 32: continue
                    for y in range(8):
                        sy = 7-y if entry & 2048 else y
                        for x in range(8):
                            sx = 7-x if entry & 1024 else x
                            color = (tile[sy*4+sx//2] >> (4*(sx % 2))) & 15
                            if layer == 1 and color == 0: continue
                            index = color+(entry >> 12)*16
                            pixels[quadrant % 2*8+x, quadrant//2*8+y] = rgba[index if color else 0]
            flat = Image.alpha_composite(layers[0], layers[1])
            kind = (attr >> (29 if self.family == 'frlg' else 12)) & (3 if self.family == 'frlg' else 15)
            empty = Image.new('RGBA', (16,16))
            all_cells[mid] = {'flat': flat, 'bottom': layers[0], 'top': layers[1], 'under': flat if kind == 1 else layers[0],
                'over': empty if kind == 1 else layers[1], 'mid': layers[0] if kind == 0 else layers[1] if kind == 1 else empty,
                'layer_type': kind, 'attribute': attr, 'entries': entries}
        self.pair_cache[key] = all_cells
        return all_cells


def export(rom_path, family, output, outdoor_only=False):
    rom = Rom(rom_path, family); output = Path(output); output.mkdir(parents=True, exist_ok=True)
    census = rom.discover(); print(f'{rom.path.name}: {len(census["maps"])} maps; {census["group_count"]} groups', flush=True)
    pairs, records, errors = {}, [], []
    for m in census['maps']:
        key = m['primary_tileset'], m['secondary_tileset']; name = f'{key[0]:08x}_{key[1]:08x}'
        try:
            cells = rom.pair(*key)
            if name not in pairs:
                target = output/'pairs'/name; target.mkdir(parents=True, exist_ok=True)
                metadata = []
                for mode in ('flat', 'bottom', 'top', 'under', 'mid', 'over'):
                    atlas = Image.new('RGBA', (256, 1024))
                    for mid, cell in cells.items(): atlas.paste(cell[mode], (mid % 16*16, mid//16*16))
                    atlas.save(target/(mode+'.png'))
                labeled = Image.new('RGBA', (16*40, 64*43), '#222831'); draw = ImageDraw.Draw(labeled)
                for mid, cell in cells.items():
                    x, y = mid % 16*40, mid//16*43
                    labeled.paste(cell['flat'].resize((32,32), Image.Resampling.NEAREST), (x, y))
                    draw.text((x,y+32), str(mid), fill='white')
                    metadata.append({'id': mid, 'layer_type':cell['layer_type'], 'attribute':cell['attribute'], 'entries':cell['entries'], 'pixel_sha256':hashlib.sha256(cell['flat'].tobytes()).hexdigest()})
                labeled.save(target/'labeled.png')
                (target/'metatiles.json').write_text(json.dumps(metadata, indent=2))
                pairs[name] = {label:{k:v for k,v in rom.tileset(ptr).items() if k not in ('entries','attrs','palettes','tile_bytes')} for label,ptr in zip(('primary','secondary'), key)}
            grid = [rom.u16(m['grid_offset']+i*2) for i in range(m['width']*m['height'])]
            record = dict(m, pair=name, grid=grid)
            if not outdoor_only or m['map_type'] in (1,2,3):
                target = output/'maps'; target.mkdir(exist_ok=True)
                for mode in ('flat', 'under', 'mid', 'over'):
                    image = Image.new('RGBA', (m['width']*16, m['height']*16))
                    for i, value in enumerate(grid):
                        if value & 1023 in cells: image.paste(cells[value & 1023][mode], (i % m['width']*16, i//m['width']*16))
                    image.save(target/(m['id']+'-'+mode+'.png'))
            records.append(record)
        except Exception as error:
            errors.append({'map':m['id'],'error':repr(error)}); print(errors[-1], flush=True)
    metadata = {'rom_name':rom.path.name, 'rom_bytes':len(rom.raw), 'rom_sha256':rom.sha256, 'family':family,
                'primary_metatiles':rom.primary, 'primary_tiles':rom.primary_tiles, 'primary_palettes':rom.primary_pals,
                'group_table_offset':census['group_table_offset'], 'group_count':census['group_count'], 'maps':records, 'pairs':pairs, 'errors':errors,
                'notes':'Native16px metatiles. Layer alpha preserved fromROMtop-half/layer-type attributes; no scaling or color erasure. Checked custom animation descriptor tables initialize exact first-frame raw tiles; callbacks are not executed. Vanilla code callbacks remain at stored graphics phase.'}
    (output/'catalog.json').write_text(json.dumps(metadata, indent=2))
    print(json.dumps({'output':str(output),'maps':len(records),'pairs':len(pairs),'errors':len(errors)}), flush=True)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom', type=Path)
    parser.add_argument('--family', choices=('frlg','rse'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--outdoor-only', action='store_true')
    args = parser.parse_args()
    export(args.rom, args.family, args.output, args.outdoor_only)


if __name__ == '__main__': main()
