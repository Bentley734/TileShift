"""Author complete CrystalDust department counters in the original GSC geometry."""
from pathlib import Path
from collections import defaultdict
from types import SimpleNamespace
import argparse, copy, hashlib, json, os, re, sys
W = next(p for p in Path(__file__).resolve().parents if (p / '.tools/python').is_dir())
sys.path.insert(0, str(W / '.tools/python'))
from PIL import Image
SHA = lambda value: hashlib.sha256(value).hexdigest()
PAIR = '083df884_08ea002c'
ROM = '51196cba923c315d0088b747b5cdee704f2ac057cd493f9ddf226fb7227302cf'
MARKER = 'COMPLETE NATIVE CRYSTALDUST DEPARTMENT COUNTERS'
MODULE = 'mappings/johto_mart_finish.lua'
ART_KEYS = ('parts','donor','base','animated','animation','frames','assetFrames','foreground','occludes','artOverlay','flora','asset','assetFileHash','assetPixelHash','compositionPixelHash','canopy','overMask')

def canonical(value):
    if isinstance(value, dict): return {k: canonical(v) for k, v in sorted(value.items())}
    if isinstance(value, list): return [canonical(v) for v in value]
    return value

def footer(baseline, fixes, label):
    import gen2_extended_review as review
    tail = re.search(br'\r?\nreturn rows\s*$', baseline)
    assert tail and label.encode() not in baseline
    text = '\n-- BEGIN ' + label + '\nfor _,r in ipairs((function()\n' + review.write_compact(canonical(fixes), None)[0] + '\nend)())do rows[#rows+1]=r end\n-- END ' + label + '\nreturn rows\n'
    if b'\r\n' in baseline: text = text.replace('\n', '\r\n')
    return baseline[:tail.start()] + text.encode()

def depth(name, x, y, mid):
    if name.endswith(('1F','3F')): return 48
    if y <= 4: return 112 if name.endswith('2F') and mid == 758 else 80
    if name.endswith('2F') and mid == 671: return 112
    if name.endswith('2F') and (y == 7 or mid in (625,617,751)): return 128
    if name.endswith('5F') and (y == 6 or mid in (625,617)): return 112
    return (y + 1) * 16

def clearance_chairs(base, mod, cache, packed):
    """Keep the same seats keyed to their actual block, not callback-removed positions."""
    import preview, gen2_extended_review as review
    from newbark_building_review import lua
    module = 'mappings/gen2_interior_chair_audit.lua'
    audit = preview.read_reviewed(base / module)
    selected = [r for r in audit if r['game']=='crystal' and r['style']=='gen3'
                and r.get('map')=='GOLDENROD_DEPT_STORE_ROOF' and r['id']==50 and r['quadrant'] in (1,3)]
    assert len(selected)==4 and {(r['x'],r['y']) for r in selected}=={(1,2),(1,3),(1,4),(1,5)}
    md=review.source(cache,'crystal')['maps']['GOLDENROD_DEPT_STORE_ROOF']
    assert [(i%md['width']*2,i//md['width']*2) for i,b in enumerate(md['blocks']) if b==50]==[(0,2),(0,4)]
    replacements=[]
    for q in (1,3):
        candidates=[r for r in selected if r['quadrant']==q]
        def comparable(row): return {k:v for k,v in row.items() if k not in ('x','y','sourceCells')}
        assert canonical(comparable(candidates[0]))==canonical(comparable(candidates[1]))
        r=copy.deepcopy(candidates[0]);r.pop('x');r.pop('y')
        r['sourceCells']=[xy for old in candidates for xy in old['sourceCells']]
        assert preview.replacement_image(cache,r,packed,mod).tobytes()==preview.replacement_image(cache,candidates[0],packed,base).tobytes()
        replacements.append(canonical(r))
    baseline_regular=preview.read_reviewed(base / MODULE)
    assert sum(r['game']=='crystal' and r.get('map')=='GOLDENROD_DEPT_STORE_ROOF' and r['id']==50 and r['quadrant'] in (1,3) and 'x' not in r for r in baseline_regular)==2
    raw=(mod / MODULE).read_bytes();tail=re.search(br'\r?\nreturn rows\s*$',raw);assert tail
    code='''\n-- Clearance callbacks remove the two id50 chair blocks. Preserve their complete\n-- ordinary artwork as exact map/block aliases so removed seats are naturally unused.\ndo
local fixes='''+lua(canonical(replacements))+'''
local n=0
for i,r in ipairs(rows)do
 if r.game=='crystal'and r.style=='gen3'and r.map=='GOLDENROD_DEPT_STORE_ROOF'and r.id==50 and r.x==nil then
  for _,fix in ipairs(fixes)do if r.quadrant==fix.quadrant then rows[i]=fix;n=n+1 end end
 end
end
assert(n==2,'Clearance chair regular source scope changed')
end
return rows
'''
    if b'\r\n' in raw:code=code.replace('\n','\r\n')
    (mod / MODULE).write_bytes(raw[:tail.start()]+code.encode())
    raw=(base / module).read_bytes();tail=re.search(br'\r?\nreturn rows\s*$',raw);assert tail
    code='''\n-- Complete rooftop chairs now use the guarded id50 regular aliases above;\n-- no fixed-position alias survives when native clearance callbacks remove them.\ndo
local kept={};local n=0
for _,r in ipairs(rows)do
 if r.game=='crystal'and r.style=='gen3'and r.map=='GOLDENROD_DEPT_STORE_ROOF'and r.id==50
  and((r.quadrant==1 and r.x==1 and(r.y==2 or r.y==4))or(r.quadrant==3 and r.x==1 and(r.y==3 or r.y==5)))then n=n+1
 else kept[#kept+1]=r end
end
assert(n==4,'Clearance chair positioned source scope changed');rows=kept
end
return rows
'''
    if b'\r\n' in raw:code=code.replace('\n','\r\n')
    (mod / module).write_bytes(raw[:tail.start()]+code.encode())
    return {'status':'passed','removed_redundant_positioned_rows':4,'replaced_existing_regular_rows':2,'ordinary_seat_art_unchanged':True,'native_clearance_block_removal_supported':True,'source_id50_occurrences':[[0,2],[0,4]]}

def write_roofs(base, mod, sources):
    from newbark_building_review import lua
    raw = (base / 'lib/roofs.lua').read_bytes()
    newline = '\r\n' if b'\r\n' in raw else '\n'
    text = raw.decode().replace('\r\n','\n')
    point = '  for _,row in ipairs(ctx.furnitureRows or{})do'
    assert text.count(point) == 1
    text = text.replace(point,'  -- Finite original department-counter footprints and native piece identities.\n  local departmentCounterSources=' + lua(canonical(sources)) + '\n' + point,1)
    point = '    local checked={};for k,v in pairs(row)do checked[k]=v end'
    code = '''    local counterSource=departmentCounterSources[row.game]and departmentCounterSources[row.game][row.map]
    local counterPiece=coords and counterSource and counterSource.pieces[row.x..':'..row.y]
    local departmentCounter=counterPiece and row.furniture=='department_counter'
      and row.tileset=='TILESET_MART'and row.anchorX==counterSource.anchorX and row.anchorY==counterSource.anchorY
      and row.id==counterSource.id and row.quadrant==counterSource.quadrant
      and row.sourceHash==counterSource.sourceHash and row.sourceCollision==counterSource.sourceCollision
      and row.role=='crystaldust_complete_department_counter'and row.frontY==counterPiece.frontY
      and row.asset==counterPiece.asset and row.assetFileHash==counterPiece.hash
'''
    assert text.count(point) == 1
    text = text.replace(point,code+point,1)
    text = text.replace('or kurtBench or azaleaTree)and row.style', 'or kurtBench or azaleaTree or departmentCounter)and row.style',1)
    point = "    assert(#maps.anchors<=(row.map=='KURTS_HOUSE'and 5 or shipAnchorLimits[row.map]or 3)"
    code = '''    if departmentCounter then
      for _,guard in ipairs(counterSource.cells)do
        local key=math.floor(guard.y/2)..':'..math.floor(guard.x/2)
        if not maps.seen[key]then maps.seen[key]=true;maps.anchors[#maps.anchors+1]={x=guard.x,y=guard.y}end
      end
    end
'''
    assert text.count(point) == 1
    text = text.replace(point,code+point.replace("and 5 or ship", "and 5 or(departmentCounter and 6)or ship"),1)
    point = '    local function append(row,x,y,sourceY,canopy,isFurniture)'
    text = text.replace(point,'    local counterChecked=false\n'+point,1)
    point = "        if isFurniture and row.furniture=='azalea_gym_tree'then"
    code = '''        if isFurniture and row.furniture=='department_counter'then
          assert(def.width==8 and def.height==4,'Department counter source room bounds changed')
          if not counterChecked then
            local spec=departmentCounterSources[game][def.id]
            for _,guard in ipairs(spec.cells)do
              local bid=def.blocks[math.floor(guard.y/2)*def.width+math.floor(guard.x/2)+1]
              assert(bid==guard.id,'Complete department counter source footprint changed')
              local part,why=ctx.donor:cell({game=game,tileset=row.tileset,id=guard.id,quadrant=guard.quadrant,
                hash=guard.hash,hashOnly=true,map=def,monochrome=true,sourceFiles=row.sourceFiles})
              assert(part,why or'Complete department counter source glyph changed')
            end
            counterChecked=true
          end
        end
'''
    assert text.count(point) == 1
    text = text.replace(point,code+point,1)
    (mod / 'lib/roofs.lua').write_bytes(text.replace('\n',newline).encode())

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--catalog-dir', type=Path, required=True)
    p.add_argument('--mod-root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    base, cat, mod, out = (v.resolve() for v in (a.baseline,a.catalog_dir,a.mod_root,a.output))
    assert base != mod
    out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(mod / 'tools'))
    import preview, gen2_extended_review as review
    from newbark_building_review import lua
    plans = json.loads((mod / 'tools/department_counter_plan.json').read_text())
    catalog = json.loads((cat / 'catalog.json').read_text())
    assert catalog['rom_sha256'] == ROM
    cache = Path(os.environ['APPDATA']) / 'pokemon-love2d'
    packed = {}
    allrows = []
    for path in dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]", (base / 'main.lua').read_text())):
        allrows.extend((path, r) for r in preview.read_reviewed(base / path))
    generic, scoped, positioned = defaultdict(dict), defaultdict(dict), defaultdict(dict)
    for path, r in allrows:
        if r['game'] not in ('gold','silver','crystal') or r['style'] != 'gen3': continue
        key = r['id'],r['quadrant']
        if 'x' in r: positioned[r['game'],r['map']][(*key,r['x'],r['y'])] = (path,r)
        elif r.get('map'): scoped[r['game'],r['map']][key] = (path,r)
        else: generic[r['game'],r['tileset']][key] = (path,r)
    planes = {name: Image.open(cat / 'pairs' / PAIR / (name + '.png')).convert('RGBA') for name in ('bottom','top')}
    native_modules, assets, scope, fixes, foreground = {}, {}, [], [], []
    furniture_sources, fixture = {}, {'assets':{},'maps':{}}
    folder = mod / 'assets/third_party/johto-hacks/crystaldust-department-counters'
    folder.mkdir(parents=True, exist_ok=True)
    def native(mid, flat):
        xy = (mid % 16 * 16,mid // 16 * 16)
        box = (*xy,xy[0]+16,xy[1]+16)
        image = planes['top'].crop(box)
        if flat: image = Image.alpha_composite(planes['bottom'].crop(box), image)
        key = str(mid) + (':flat' if flat else ':top')
        native_modules[key] = {'pair':PAIR,'mid':mid,'plane':'flat' if flat else 'top','atlas_xyxy':box,'RGBA_sha256':SHA(image.tobytes()),'opaque_pixels':sum(v[3]>0 for v in image.get_flattened_data())}
        return image
    def asset(image, recipe):
        pixels = SHA(image.tobytes())
        name = 'cell-' + pixels[:20] + '.png'
        path = folder / name
        if name not in assets:
            image.save(path)
            assets[name] = {'asset':path.relative_to(mod).as_posix(),'assetFileHash':SHA(path.read_bytes()),'assetPixelHash':pixels,'native_size':[16,16],'native_scale':1,'recipes':[]}
        rec = assets[name]
        if recipe not in rec['recipes']: rec['recipes'].append(recipe)
        return rec
    def artrow(old, art, role):
        row = copy.deepcopy(old)
        for key in ART_KEYS: row.pop(key,None)
        row.update(kind='third_party',status='reviewed',asset=art['asset'],assetFileHash=art['assetFileHash'],assetPixelHash=art['assetPixelHash'],compositionPixelHash=art['assetPixelHash'],
                   credit='Pokemon CrystalDust / Sierraffinity and DoMoreAwesome Games',sourceUrl='https://github.com/Sierraffinity/CrystalDust',role=role,
                   evidence='Complete native CrystalDust counter modules at1:1, including rounded caps, every return rim/front/base and the whole glass display. Source cashier positions, interactions, collision and scripts stay unchanged. Native hardware is composed over the existing checked local floor/wall; foreground replays retain per-row depth.')
        return row
    for game in ('gold','silver','crystal'):
        data = review.source(cache,game)
        furniture_sources[game], fixture['maps'][game] = {}, {}
        for name, plan in plans.items():
            md = data['maps'][name]
            assert md['width'] == 8 and md['height'] == 4 and md['tileset'] == 'TILESET_MART'
            selected = generic[game,md['tileset']].copy(); selected.update(scoped[game,name])
            cells = {}
            for pos,bid in enumerate(md['blocks']):
                for q in range(4):
                    x,y = pos % md['width'] * 2 + q % 2,pos // md['width'] * 2 + q // 2
                    cells[x,y] = positioned[game,name].get((bid,q,x,y),selected.get((bid,q)))
            floor_record = next(v for v in cells.values() if v and v[1]['role'] == 'interior_dept_floor')
            floor = preview.replacement_image(cache,floor_record[1],packed,base)
            anchor_xy = tuple(plan['anchor']); anchor = cells[anchor_xy][1]
            spec = {k:anchor[k] for k in ('id','quadrant','sourceHash','sourceCollision')}
            spec.update(anchorX=anchor_xy[0],anchorY=anchor_xy[1],cells=[],pieces={})
            fixture['maps'][game][name] = {k:md[k] for k in ('width','height','tileset','blocks')}
            for cy, native_row in enumerate(plan['grid']):
                for cx,mid in enumerate(native_row):
                    if mid is None: continue
                    x,y = plan['xy'][0]+cx,plan['xy'][1]+cy
                    module,old = cells[x,y]
                    assert old.get('x') is None, ('Unexpected positioned source supersession',game,name,x,y)
                    assert old['id'] == md['blocks'][y//2*md['width']+x//2] and old['quadrant'] == y%2*2+x%2
                    ink = native(mid,mid in plan.get('flat',[]))
                    background = floor if any(s in old['role'] for s in ('counter','register','stock_display')) else preview.replacement_image(cache,old,packed,base)
                    image = Image.alpha_composite(background,ink)
                    assert all(v[3] == 255 for v in image.get_flattened_data())
                    recipe = {'family':'department_counter','mid':mid,'plane':'flat' if mid in plan.get('flat',[]) else 'top','background':'retained_department_floor' if background is floor else 'retained_original_cell','source_module':module}
                    bg_art = asset(image,recipe)
                    row = artrow(old,bg_art,'crystaldust_department_counter_'+str(mid))
                    row.update(x=x,y=y,sourceCells=[[x,y]])
                    fixes.append(canonical(row))
                    fg_art = asset(ink,{'family':'department_counter_foreground','mid':mid,'plane':recipe['plane']})
                    fg = artrow(anchor,fg_art,'crystaldust_complete_department_counter')
                    front_y = depth(name,x,y,mid)
                    fg.update(furniture='department_counter',anchorX=anchor_xy[0],anchorY=anchor_xy[1],x=x,y=y,frontY=front_y,sourceCells=[list(anchor_xy)])
                    foreground.append(canonical(fg))
                    piece_key = str(x)+':'+str(y)
                    spec['pieces'][piece_key] = {'asset':fg_art['asset'],'hash':fg_art['assetFileHash'],'frontY':front_y}
                    spec['cells'].append({'x':x,'y':y,'id':old['id'],'quadrant':old['quadrant'],'hash':old['sourceHash']})
                    fixture['assets'][fg_art['asset']] = {'hash':fg_art['assetFileHash'],'mask':''.join('1' if v[3] else '0' for v in ink.get_flattened_data())}
                    scope.append({'game':game,'map':name,'x':x,'y':y,'id':old['id'],'quadrant':old['quadrant'],'sourceHash':old['sourceHash'],'old_row':old,'candidate_row':row,'new_RGBA_sha256':SHA(image.tobytes()),'native_mid':mid,'native_plane':recipe['plane']})
            furniture_sources[game][name] = spec
    keys = [(r['game'],r['map'],r['id'],r['quadrant'],r['x'],r['y']) for r in fixes]
    assert len(keys) == len(set(keys)) == 189
    old_keys = {(r['game'],r.get('map'),r['id'],r.get('quadrant'),r.get('x'),r.get('y')) for _,r in allrows}
    assert not set(keys) & old_keys
    (mod / MODULE).write_bytes(footer((base / MODULE).read_bytes(),fixes,MARKER))
    (mod / 'lib/johto_furniture.lua').write_bytes(footer((base / 'lib/johto_furniture.lua').read_bytes(),foreground,MARKER))
    write_roofs(base,mod,furniture_sources)
    roof_chairs=clearance_chairs(base,mod,cache,packed)
    validation = review.validate_batch(fixes,SimpleNamespace(cache=cache,engine=W/'.work/tileshift-engine-0420'),mod)
    assert validation['rows_accepted'] == len(fixes) and validation['rejected'] == 0
    (out / 'furniture-source-guards.json').write_text(json.dumps(canonical(furniture_sources),indent=2)+'\n',encoding='utf8')
    (out / 'furniture-source-guards.lua').write_text('return '+lua(canonical(furniture_sources))+'\n',encoding='utf8')
    (mod / 'tests/department_counters_native_alpha.lua').write_text('-- Complete native CrystalDust counter alpha and source geometry.\nreturn '+lua(canonical(fixture))+'\n',encoding='utf8')
    provenance = {'origin':'Complete native CrystalDust department counter modular family','rom_sha256':ROM,'pair':PAIR,'credit':'Sierraffinity / DoMoreAwesome Games','sourceUrl':'https://github.com/Sierraffinity/CrystalDust','native_scale':1,'native_modules':native_modules,'source_modules':assets,'processing':'Whole native TOP or full BOTTOM+TOP glass modules only; no hardware pixel cropped, resized, recolored or drawn. Match existing local backgrounds. Complete hardware foreground uses per-row depth.'}
    (folder / 'provenance.json').write_text(json.dumps(canonical(provenance),indent=2)+'\n',encoding='utf8')
    proof = {'status':'passed','changed_maps':list(plans),'physical_BG_cells':len(fixes),'foreground_cells':len(foreground),'native_validation':validation,'source_cells':scope,'assets':assets,'native_modules':native_modules,'all_old_mapping_rows_retained_except_explicit_roof_chair_alias_consolidation':True,'roof_clearance_chairs':roof_chairs,'native_scale':1,'no_source_NPC_collision_warp_script_changes':True}
    (out / 'proof.json').write_text(json.dumps(canonical(proof),indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in proof.items() if k not in ('source_cells','assets','native_modules')}))

if __name__ == '__main__': main()
