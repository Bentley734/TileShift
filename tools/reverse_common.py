"""Explicit GB donor recipes for native GBA sources; no inferred identity.

Outputs extracted comparison material only in the private workspace .work.
The installable mappings contain native references, masks and hashes, not ROM art.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import zlib

from PIL import Image, ImageDraw, ImageFont
import catalog
import preview
from interior_review import Imports
from newbark_building_review import lua

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path(os.environ['APPDATA']) / 'pokemon-love2d'
CATALOGS = ROOT.parent / '.work/tileshift-catalog'
STYLES = {'gen1': 'red', 'gen2': 'crystal'}


class ReverseReview:
    def __init__(self, name, games):
        self.name, self.games = name, tuple(games)
        self.cache = CACHE
        self.out = ROOT.parent / ('.work/tileshift-reverse-' + name)
        self.out.mkdir(parents=True, exist_ok=True)
        self.imp = Imports(CACHE, CATALOGS)
        self.packed = self.imp.packed
        self.rows = {}
        self._gb = {}
        self._refs = {}

    def gb_ref(self, game, map_id, block_id, quadrant):
        assert game in ('red', 'crystal')
        cache_key = (game, map_id, block_id, quadrant)
        if cache_key in self._refs:
            return copy.deepcopy(self._refs[cache_key])
        definition = self.imp.table(game, 'maps')[map_id]
        tileset = definition['tileset']
        cell = self.imp.cell_index(game)[tileset, block_id, quadrant]
        ts = self.imp.table(game, 'tilesets')[tileset]
        # Donor.gb deliberately fingerprints the neutral source pixels, even
        # when a Crystal map/time/roof context determines the displayed RGB.
        ref = {'game': game, 'tileset': tileset, 'id': block_id,
               'quadrant': quadrant, 'hash': cell['grayscale_pixel_sha256'],
               'fingerprints': {
                   'metadata': catalog.sha((CACHE / game / 'data/generated/tilesets.lua').read_bytes()),
                   'image': catalog.sha((CACHE / game / ts['image']).read_bytes())}}
        if game == 'red':
            ref['monochrome'] = True
        else:
            ref.update(map=map_id, daytime='DAY')
            for key, relative in (('maps', 'maps.lua'), ('palettes', 'palettes.lua'), ('roofs', 'roofs.lua')):
                path = CACHE / game / 'data/generated' / relative
                if path.exists():
                    ref['fingerprints'][key] = catalog.sha(path.read_bytes())
            if tileset in ('TILESET_JOHTO', 'TILESET_JOHTO_MODERN'):
                roofs = self.imp.table(game, 'roofs')
                name = catalog.dict_at(roofs.get('mapGroupRoofs', {}), definition['group'])
                spec = roofs.get('roofs', {}).get(name) if name else None
                if spec and spec.get('image'):
                    ref['fingerprints']['roofImage'] = catalog.sha((CACHE/game/spec['image']).read_bytes())
        self._refs[cache_key] = ref
        return ref

    def gb_at(self, game, map_id, x, y):
        m = self.imp.table(game, 'maps')[map_id]
        assert 0 <= x < m['width'] * 2 and 0 <= y < m['height'] * 2
        bid = m['blocks'][y // 2 * m['width'] + x // 2]
        return self.gb_ref(game, map_id, bid, y % 2 * 2 + x % 2)

    def gb_rect(self, game, map_id, sx, sy, w, h, x=0, y=0):
        """Complete native pixel rectangle, split at source16px boundaries."""
        assert 0 < w <= 16 and 0 < h <= 16 and 0 <= x <= 16-w and 0 <= y <= 16-h
        definition = self.imp.table(game, 'maps')[map_id]
        assert 0 <= sx <= definition['width']*32-w and 0 <= sy <= definition['height']*32-h
        parts = []
        py = sy
        while py < sy+h:
            ph = min(sy+h-py,16-py%16);px=sx
            while px < sx+w:
                pw = min(sx+w-px,16-px%16)
                parts.append({'donor':self.gb_at(game,map_id,px//16,py//16),
                    'srcX':px%16,'srcY':py%16,'w':pw,'h':ph,'x':x+px-sx,'y':y+py-sy})
                px += pw
            py += ph
        return parts

    def gb_image(self, ref):
        key = json.dumps(ref, sort_keys=True)
        if key in self._gb:
            return self._gb[key]
        game = ref['game']
        ts = self.imp.table(game, 'tilesets')[ref['tileset']]
        sheet = Image.open(CACHE / game / ts['image']).convert('RGBA')
        block = catalog.lua_array(catalog.dict_at(ts['blocks'], ref['id'] + 1))
        neutral = preview.native_cell(sheet, ts, block, ref['quadrant'])
        assert catalog.sha(neutral.tobytes()) == ref['hash']
        palettes = roof = None
        if game == 'crystal':
            definition = self.imp.table(game, 'maps')[ref['map']]
            palettes = preview.palette_set(self.imp.table(game, 'palettes'), definition, ref.get('daytime', 'DAY'))
            if ref['tileset'] in ('TILESET_JOHTO', 'TILESET_JOHTO_MODERN'):
                roofs = self.imp.table(game, 'roofs')
                name = catalog.dict_at(roofs.get('mapGroupRoofs', {}), definition['group'])
                spec = roofs.get('roofs', {}).get(name) if name else None
                if spec and spec.get('image'):
                    roof = Image.open(CACHE / game / spec['image']).convert('RGBA')
        result = preview.native_cell(sheet, ts, block, ref['quadrant'], palettes, roof)
        self._gb[key] = result
        return result

    @staticmethod
    def native(ref, role):
        return {'kind': 'native', 'donor': copy.deepcopy(ref), 'role': role}

    @staticmethod
    def composite(base, parts, role):
        row = {'kind': 'native_composite', 'parts': copy.deepcopy(parts), 'role': role}
        if base is not None:
            row['base'] = copy.deepcopy(base)
        return row

    def row(self, game, pair, mid, style, art, evidence, map_id=None):
        assert game in self.games and style in STYLES
        cell = self.imp.cell_index(game)[pair, mid]
        row = {'game': game, 'style': style, 'tileset': pair, 'id': mid,
               'sourceHash': cell['pixel_sha256'], 'status': 'reviewed',
               'evidence': evidence}
        if cell.get('behavior') is not None:
            row['sourceBehavior'] = cell['behavior']
        if map_id is not None:
            row['map'] = map_id
        row.update(copy.deepcopy(art))
        row['compositionPixelHash'] = catalog.sha(self.render(row).tobytes())
        key = (game, style, pair, mid, map_id)
        assert key not in self.rows or self.rows[key] == row, ('Conflicting reverse recipe', key)
        self.rows[key] = row
        return row

    def render(self, row):
        if row.get('animated'):
            return preview.replacement_image(self.cache,row,self.packed,ROOT)
        if row.get('donor'):
            out = self.gb_image(row['donor']).copy()
        else:
            out = self.gb_image(row['base']).copy() if row.get('base') else Image.new('RGBA', (16, 16))
            for p in row['parts']:
                assert p.get('layers') is None, 'GB sources have one complete colored pixel canvas'
                im = self.gb_image(p['donor'])
                sx, sy, w, h = p.get('srcX', 0), p.get('srcY', 0), p['w'], p['h']
                piece = im.crop((sx, sy, sx+w, sy+h))
                out.alpha_composite(piece, (p.get('x', 0), p.get('y', 0)))
        if row.get('artOverlay'):
            spec=row['artOverlay'];path=ROOT/spec['asset'];raw=path.read_bytes()
            assert catalog.sha(raw)==spec['hash']
            original=out.copy();image=Image.open(path).convert('RGBA');assert image.size==(16,16)
            if spec.get('mode')!='over':out=self.gb_image(row['base']).copy()
            out.alpha_composite(image)
            for x,y,w,h in spec['preserveRects']:
                out.paste(original.crop((x,y,x+w,y+h)),(x,y))
        return out

    def map_preview(self, game, map_id, style):
        before, source, _, meta = self.imp.gba(game, map_id)
        after = before.copy()
        by_mid = {r['id']: r for r in self.rows.values()
                  if r['game'] == game and r['style'] == style and r['tileset'] == meta['tileset']
                  and r.get('map', map_id) == map_id}
        replaced = 0
        for c in source:
            row = by_mid.get(c['id'])
            if row is None:
                continue
            piece = self.render(row)
            for x, y in c['coordinates']:
                after.paste(piece, (x*16, y*16)); replaced += 1
        prefix = game + '-' + map_id + '-' + style
        before.save(self.out / (prefix + '-before.png'))
        after.save(self.out / (prefix + '-after.png'))
        scale = 2
        panel = Image.new('RGB', (before.width*scale*2+56, before.height*scale+120), '#18212b')
        draw = ImageDraw.Draw(panel);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 16)
        draw.text((18, 14), game.title()+' / '+map_id+' / '+style+' — reviewed native tile counterparts', font=font, fill='white')
        draw.text((18, 42), 'Background-map development preview; nearest-neighbour pixels. No actors rendered.', font=font, fill='#c4cdd8')
        panel.paste(before.resize((before.width*scale,before.height*scale),Image.Resampling.NEAREST),(18,72))
        panel.paste(after.resize((after.width*scale,after.height*scale),Image.Resampling.NEAREST),(38+before.width*scale,72))
        total=before.width*before.height//256
        draw.text((18,80+before.height*scale),f'Replaced {replaced}/{total} cells ({replaced/total:.1%}). Unreviewed cells retain native art.',font=font,fill='#c4cdd8')
        panel.save(self.out/(prefix+'-comparison.png'))
        return {'game':game,'map':map_id,'style':style,'replaced':replaced,'total':total}

    def write(self, target):
        rows = list(self.rows.values())
        body = '-- Reviewed reverse-generation native pixel counterparts; no ROM artwork bundled.\nlocal rows={}\n'
        body += 'local function append(batch)for _,row in ipairs(batch)do rows[#rows+1]=row end end\n'
        for start in range(0, len(rows), 24):
            body += 'append((function()return {\n' + '\n'.join(lua(r)+',' for r in rows[start:start+24]) + '\n}end)())\n'
        body += 'return rows\n'
        def plain_empty(v):
            if isinstance(v,list):return [plain_empty(x)for x in v]if v else{}
            if isinstance(v,dict):return{k:plain_empty(x)for k,x in v.items()}
            return v
        assert plain_empty(catalog.plain(catalog.LUA.execute(body))) == plain_empty(rows)
        Path(target).write_text(body, encoding='utf-8')
        (self.out/'rows.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
        return rows

    def validate(self):
        """Real neutral Donor/Composition/Session decoding under each theme."""
        from lupa.luajit21 import LuaRuntime
        from validate_animation import IMAGE_FIXTURE
        rows = list(self.rows.values())
        vm = LuaRuntime(unpack_returned_tuples=True, encoding=None)
        original = Path.cwd()
        def read(relative):
            p = (CACHE / relative.decode()).resolve(); assert p.is_relative_to(CACHE.resolve())
            if not p.is_file(): return None
            raw = p.read_bytes()
            if p.suffix in ('.idx','.rgba'):
                try: raw = zlib.decompress(raw)
                except zlib.error: pass
            return raw
        try:
            os.chdir(ROOT.parent/'.tools/engine-0395')
            vm.execute(IMAGE_FIXTURE.encode())
            make = vm.globals()[b'makeData']
            def load_image(relative, raw):
                image = Image.open(CACHE/relative.decode()).convert('RGBA')
                return make(image.width,image.height,b'rgba8',image.tobytes())
            gb_animation=vm.execute((ROOT/'lib/gb_animation.lua').read_bytes())
            wrap=vm.eval(b'function(callback)return function(...)return callback(...)end end')
            checked_hash=wrap(lambda raw:hashlib.sha256(raw).hexdigest().encode())
            ctx=vm.table_from({b'read':read,b'prefix':lambda g:g+b'/',b'hash':checked_hash,b'newImageData':make,b'loadImage':load_image,b'gbAnimation':gb_animation})
            decoder=vm.execute((ROOT/'lib/donor.lua').read_bytes())[b'new'](ctx)
            composer=vm.execute((ROOT/'lib/composition.lua').read_bytes())[b'new'](vm.table_from({b'donor':decoder,b'newImageData':make}))
            vm.globals()[b'reverseRows']=vm.execute(('return '+lua(rows)).encode())
            vm.globals()[b'reverseMapping']=vm.execute((ROOT/'lib/mapping.lua').read_bytes())
            vm.globals()[b'reverseSession']=vm.execute((ROOT/'lib/session.lua').read_bytes())
            vm.globals()[b'reverseDecoder']=decoder; vm.globals()[b'reverseComposer']=composer
            vm.globals()[b'reverseHash']=lambda raw:hashlib.sha256(raw).hexdigest().encode()
            def original_art(relative, expected):
                path=(ROOT/relative.decode()).resolve();assert path.is_relative_to(ROOT)
                raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest().encode()==expected
                image=Image.open(path).convert('RGBA');assert image.size==(16,16)
                return make(16,16,b'rgba8',image.tobytes())
            vm.globals()[b'reverseOriginal']=original_art
            result=vm.execute(br'''
local indexed,errors=reverseMapping.index(reverseRows);assert(#errors==0,table.concat(errors,'\n'))
local totals={}
for _,style in ipairs({'gen1','gen2'})do
 local state=reverseSession.new({mappings=indexed,donor=reverseDecoder,newImageData=makeData,
  generations=reverseMapping.generations,themes=reverseMapping.themes,normalizeStyle=reverseMapping.normalizeStyle,
  validate=reverseMapping.validate,compose=function(row)return reverseComposer:cell(row)end,
  composeFrames=function(row)return reverseComposer:frames(row)end,original=reverseOriginal,warn=error})
 state:select(style)
 local visited={};local expected=0
 for _,row in ipairs(reverseRows)do if row.style==style then
  expected=expected+1;local k=row.game..':'..row.tileset..':'..(row.map or '*')
  if not visited[k]then visited[k]=assert(state:replacements(row.game,row.tileset,row.map and{id=row.map}or nil))end
  local piece=assert(visited[k][row.id]);assert(piece.under)
  assert(reverseHash(piece.under:getString())==row.compositionPixelHash,'Reverse RGB output differs from independently rendered GB counterpart')
 end end
 assert(state.rejected==0 and state.accepted==expected,'Reverse rows failed strict source/donor decoding')
 totals[style]=state.accepted
end
return totals
''')
            accepted={k.decode()if isinstance(k,bytes)else k:v for k,v in result.items()}
            proof={'accepted':accepted,'rejected':0,'neutral_imports_only':True,'source_and_donor_hashes_checked':True,
                   'independent_output_pixels_checked':len(rows)*256}
            (self.out/'proof.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
            return proof
        finally:
            os.chdir(original)
