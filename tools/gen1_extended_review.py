"""Track and review remaining Gen1 terrain using explicit native references.

Private contact sheets stay below .work. Activation requires a named batch
that has been visually reviewed; tile IDs never imply equivalence.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import copy
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import catalog
import outdoor_review
import preview
import review
import cave_review

WORKSPACE=Path(__file__).resolve().parents[2]
CACHE=Path(catalog.os.environ['APPDATA'])/'pokemon-love2d'
OUTPUT=WORKSPACE/'.work/tileshift-gen1-extended-review'
TARGET=WORKSPACE/'TileShift/mappings/gen1_extended.lua'
GLOBAL_STAIRS_APPROVED=True
CAVE_SIMPLE_APPROVED=True
CAVE_HELD_ROLES=set()
CAVE_SIMPLE=(
    (4,2,642,'cave_solid_rock_fill'),
    (96,0,641,'cave_alternate_dry_floor'),
    (41,2,644,'cave_rock_stairs'),
    (42,3,717,'cave_signpost'),
    (3,0,754,'cave_black_void'),
    (36,2,647,'cave_exit_threshold'),
    (20,3,657,'cave_raised_mass_top_missing_scopes'),
    (1,0,641,'cave_dry_floor_missing_scopes'),
)

def write_groups(rows):
    groups={}
    for row in rows:
        shared={k:v for k,v in row.items()if k not in('id','quadrant','x','y')}
        key=json.dumps(shared,sort_keys=True,separators=(',',':'))
        if key not in groups:groups[key]={**shared,'cells':[]}
        cell=[row['id'],row['quadrant']]
        if 'x' in row:cell.extend([row['x'],row['y']])
        groups[key]['cells'].append(cell)
    TARGET.write_text('-- Reviewed extended Gen1 terrain; complete runtime rows expand from exact-source alias groups.\nlocal groups={\n'
        +''.join('  '+review.lua_value(g)+',\n'for g in groups.values())
        +'}\nlocal rows={}\nfor _,group in ipairs(groups)do\n  for _,cell in ipairs(group.cells)do\n'
        +'    local row={}\n    for key,value in pairs(group)do if key~="cells"then row[key]=value end end\n'
        +'    row.id,row.quadrant,row.x,row.y=cell[1],cell[2],cell[3],cell[4]\n    rows[#rows+1]=row\n  end\nend\nreturn rows\n',encoding='utf-8')

def existing_rows():
    return [r for p in(WORKSPACE/'TileShift/mappings').glob('*.lua')
            if p.name!='gen1_extended.lua' for r in preview.read_reviewed(p)]

def write_contact(path,heading,entries,cols=6):
    cw,ch=220,144
    canvas=Image.new('RGB',(cols*cw,80+ch*((len(entries)+cols-1)//cols)),'#18212b')
    d=ImageDraw.Draw(canvas);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
    d.text((12,12),heading,font=font,fill='white')
    d.text((12,38),'Native source pixels, enlarged by nearest-neighbor. Coordinates and direction require review.',font=font,fill='#c4cdd8')
    for i,entry in enumerate(entries):
        x=i%cols*cw+10;y=i//cols*ch+78
        canvas.paste(entry['image'].resize((80,80),Image.Resampling.NEAREST),(x,y))
        d.multiline_text((x,y+84),entry['label'],font=font,fill='white',spacing=2)
    canvas.save(path)

def inventory(rows,tilesets=('OVERWORLD','CAVERN','FOREST','PLATEAU')):
    maps=catalog.read_lua(CACHE/'red/data/generated/maps.lua')
    sets=catalog.read_lua(CACHE/'red/data/generated/tilesets.lua')
    cells=json.loads((WORKSPACE/'.work/tileshift-catalog/red.json').read_text())['cells']
    report={}
    for tileset in tilesets:
        index={(r['block_id'],r['quadrant']):r for r in cells if r['tileset']==tileset}
        groups=defaultdict(lambda:{'occurrences':0,'unmapped':0,'contexts':[],'keys':set()})
        for name,m in maps.items():
            if not isinstance(m,dict)or m.get('tileset')!=tileset:continue
            applicable=[r for r in rows if r['game']=='red'and r['tileset']==tileset and r.get('map',name)==name]
            selected={(r['id'],r['quadrant'])for r in applicable if r.get('x')is None}
            positioned={(r['id'],r['quadrant'],r['x'],r['y'])for r in applicable if r.get('x')is not None}
            for pos,bid in enumerate(m['blocks']):
                for q in range(4):
                    cell=index[bid,q];g=groups[cell['grayscale_pixel_sha256'],review.behavior_key(cell)]
                    g['occurrences']+=1;g['keys'].add((bid,q))
                    x,y=pos%m['width']*2+q%2,pos//m['width']*2+q//2
                    if(bid,q)not in selected and(bid,q,x,y)not in positioned:
                        g['unmapped']+=1
                        if len(g['contexts'])<12:g['contexts'].append({'map':name,'cell':[x,y],'source':[bid,q]})
        ordered=[];pictures=[];ts=sets[tileset];atlas=Image.open(CACHE/'red'/ts['image'])
        for n,((fingerprint,behavior),g)in enumerate(sorted(groups.items(),key=lambda item:-item[1]['unmapped'])):
            seed=sorted(g['keys'])[0];cell=index[seed]
            row={**g,'number':n,'hash':fingerprint,'seed':seed,'keys':sorted(g['keys']),
                 'tiles':cell['tiles'],'walkable':cell['walkable_tiles'],'warp':cell['warp_tile_present']}
            ordered.append(row)
            if g['unmapped']:
                pictures.append({'image':preview.native_cell(atlas,ts,ts['blocks'][seed[0]],seed[1]),
                    'label':f"#{n} {seed[0]}:{seed[1]} missing{g['unmapped']}\nraw{cell['tiles']}"})
        report[tileset]=ordered
        write_contact(OUTPUT/f'red-{tileset.lower()}-remaining.png',f'RED {tileset}: unmatched semantic graphics',pictures)
    (OUTPUT/'inventory.json').write_text(json.dumps(report,indent=2))
    return report

def repeated_terrain(rows):
    """Existing approved complete terrain cells, exact aliases across maps."""
    proposals=[];summary=[]
    for game in('red','blue','yellow'):
        data=json.loads((WORKSPACE/f'.work/tileshift-catalog/{game}.json').read_text())
        source=[r for r in data['cells']if r['tileset']=='OVERWORLD'and r['used_by_map_count']]
        index={(r['block_id'],r['quadrant']):r for r in source}
        source_files=next(t['fingerprints']for t in data['tilesets']if t['tileset']=='OVERWORLD')
        generic={(r['id'],r['quadrant'])for r in rows if r['game']==game and r['tileset']=='OVERWORLD'and not r.get('map')}
        seeds=[]
        for role in sorted({s[3]for s in outdoor_review.SPECS}|{'walkable_stairs_bottom_half'}):
            seed=next(r for r in rows if r['game']==game and r['tileset']=='OVERWORLD'and r['role']==role)
            seeds.append(seed)
        for seed in seeds:
            source_seed=index[seed['id'],seed['quadrant']]
            aliases=[r for r in source if(r['block_id'],r['quadrant'])not in generic
                     and r['grayscale_pixel_sha256']==source_seed['grayscale_pixel_sha256']
                     and review.behavior_key(r)==review.behavior_key(source_seed)]
            summary.append({'game':game,'role':seed['role'],'sourceHash':source_seed['grayscale_pixel_sha256'],
                            'aliases':[[r['block_id'],r['quadrant']]for r in aliases]})
            for source_cell in aliases:
                row={k:copy.deepcopy(v)for k,v in seed.items()if k not in('map','sourceHash','sourceFiles','id','quadrant','evidence')}
                row.update(id=source_cell['block_id'],quadrant=source_cell['quadrant'],
                           sourceHash=source_cell['grayscale_pixel_sha256'],sourceFiles=source_files,
                           evidence='Global OVERWORLD exact-art alias of the previously reviewed complete terrain role '
                           +seed['role']+'. Same cartridge source pixels and complete native walk/grass/warp flags; '
                           'actual source map use required. Existing context-specific rows take precedence. '
                           'No shoreline, building or differently shaped graphic is inferred; mechanics remain source-owned.')
                proposals.append(row)
    (OUTPUT/'repeated-terrain-candidates.json').write_text(json.dumps(proposals,indent=2))
    (OUTPUT/'repeated-terrain-aliases.json').write_text(json.dumps(summary,indent=2))
    return proposals

def simple_caves(existing):
    fr=json.loads((WORKSPACE/'.work/tileshift-catalog/firered.json').read_text())['cells']
    donors={(r['pair'],r['mid']):r for r in fr}
    native_root=CACHE/'firered/data/generated/gba/native'
    manifest=catalog.read_lua(native_root/'manifest.lua')
    candidates=[];held=[]
    for game in('red','blue','yellow'):
        game_root=CACHE/game;maps=catalog.read_lua(game_root/'data/generated/maps.lua')
        data=json.loads((WORKSPACE/f'.work/tileshift-catalog/{game}.json').read_text())
        index={(r['block_id'],r['quadrant']):r for r in data['cells']if r['tileset']=='CAVERN'}
        source_files=next(t['fingerprints']for t in data['tilesets']if t['tileset']=='CAVERN')
        for name,m in maps.items():
            if not isinstance(m,dict)or m.get('tileset')!='CAVERN':continue
            counterpart=cave_review.counterpart(name);pair=manifest['layouts'][counterpart]['pair']
            used={(bid,q)for bid in m['blocks']for q in range(4)}
            covered={(r['id'],r['quadrant'])for r in existing if r['game']==game and r['tileset']=='CAVERN'and r.get('map',name)==name}
            for block,q,mid,role in CAVE_SIMPLE:
                seed=index[block,q]
                aliases=sorted(key for key in used-covered if index[key]['grayscale_pixel_sha256']==seed['grayscale_pixel_sha256']
                               and review.behavior_key(index[key])==review.behavior_key(seed))
                if not aliases:continue
                donor=donors.get((pair,mid))
                if not donor:
                    held.append({'game':game,'map':name,'role':role,'source':aliases,'reason':'No reviewed same-family native metatile '+str(mid)})
                    continue
                ref={'game':'firered','tileset':pair,'id':mid,'hash':donor['pixel_sha256']}
                for bid,quadrant in aliases:
                    candidates.append({'game':game,'style':'gen3','tileset':'CAVERN','map':name,'id':bid,'quadrant':quadrant,
                        'role':role,'status':'reviewed','sourceHash':seed['grayscale_pixel_sha256'],'sourceFiles':source_files,
                        'donor':ref,'nativeContext':{'map':counterpart,'pair':pair},
                        'evidence':'Complete16px native cave feature reviewed against the original source and actual FRLG regional cave palette. '
                        'Distinguishes blocked solid bedrock, freely walkable alternate dry floor, full rockstairs, sign, black void and exit threshold. '
                        'Known floor/raised-mass art may fill held scopes where the remake rearranged geometry but uses the same cave-family pack. '
                        'Per-cartridge aliases require exact source pixels and walk/warp/grass flags. Native map geometry, collision and warp destinations stay unchanged.'})
    (OUTPUT/'simple-cave-candidates.json').write_text(json.dumps(candidates,indent=2))
    (OUTPUT/'simple-cave-held.json').write_text(json.dumps(held,indent=2))
    pairs=('general__rom_082d4bfc','general__rom_082d4e0c','general__rom_082d4e24','general__rom_082d4df4','general__rom_082d4e54')
    ts=catalog.read_lua(CACHE/'red/data/generated/tilesets.lua')['CAVERN'];atlas=Image.open(CACHE/'red'/ts['image'])
    canvas=Image.new('RGB',(1320,80+len(CAVE_SIMPLE)*150),'#18212b');d=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
    for i,title in enumerate(('Gen1 source','MtMoon/Victory','Diglett','Seafoam','RockTunnel','Cerulean')):d.text((i*220+10,14),title,font=font,fill='white')
    for n,(block,q,mid,role)in enumerate(CAVE_SIMPLE):
        y=70+n*150;source=preview.native_cell(atlas,ts,ts['blocks'][block],q)
        canvas.paste(source.resize((80,80),Image.Resampling.NEAREST),(10,y));d.text((10,y+84),f'{block}:{q} '+role.removeprefix('cave_'),font=font,fill='white')
        for x,pair in enumerate(pairs):
            cell=donors.get((pair,mid))
            if cell:
                ref={'game':'firered','tileset':pair,'id':mid,'hash':cell['pixel_sha256']}
                image=preview.native_donor(CACHE,ref,{})
                canvas.paste(image.resize((80,80),Image.Resampling.NEAREST),((x+1)*220+10,y))
                d.text(((x+1)*220+10,y+84),f'{mid} '+str(cell['behavior_hint']),font=font,fill='#c4cdd8')
            else:d.text(((x+1)*220+10,y+16),'Not used / no donor',font=font,fill='#c4cdd8')
    canvas.save(OUTPUT/'cave-complete-cells-review.png')
    return candidates

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--activate-repeated-terrain',action='store_true')
    args=p.parse_args();OUTPUT.mkdir(parents=True,exist_ok=True)
    rows=existing_rows();proposals=repeated_terrain(rows);caves=simple_caves(rows)
    if args.activate_repeated_terrain:
        generated_roles={row['role']for row in proposals+caves}
        retained=[row for row in preview.read_reviewed(TARGET)if row['role']not in generated_roles]if TARGET.exists()else[]
        write_groups([row for row in proposals if GLOBAL_STAIRS_APPROVED or row['role']!='walkable_stairs_bottom_half']
                     +([row for row in caves if row['role']not in CAVE_HELD_ROLES]if CAVE_SIMPLE_APPROVED else[])+retained)
    active=rows+(preview.read_reviewed(TARGET)if TARGET.exists()else[])
    report=inventory(active)
    print(json.dumps({'proposed_repeated_terrain_rows':len(proposals),'proposed_simple_cave_rows':len(caves),
        'remaining':{ts:{'distinct':sum(bool(r['unmapped'])for r in entries),'occurrences':sum(r['unmapped']for r in entries)}for ts,entries in report.items()}},indent=2))

if __name__=='__main__':main()
