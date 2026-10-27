"""Review intact32px native broadleaf trees and compact forest boundary trees."""
from __future__ import annotations
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import zlib
from PIL import Image,ImageDraw,ImageFont
import catalog
import preview
import review
import gen1_extended_review as extended
from gen1_forest_review import MAPS
from building_review import decode_layout

ROOT=Path(__file__).resolve().parents[2]
CACHE=Path(catalog.os.environ['APPDATA'])/'pokemon-love2d'
OUT=ROOT/'.work/tileshift-gen1-forest-review'
BIG_ROLES={'forest_whole_broadleaf_tree_'+str(q)for q in range(4)}
SMALL_ROLE='forest_boundary_small_tree'
ROLES=BIG_ROLES|{SMALL_ROLE}


def scene(game,name,rows,packed):
    root=CACHE/game;m=catalog.read_lua(root/'data/generated/maps.lua')[name]
    ts=catalog.read_lua(root/'data/generated/tilesets.lua')['FOREST'];sheet=Image.open(root/ts['image'])
    selected={};positioned={}
    for row in sorted(rows,key=lambda r:bool(r.get('map'))):
        if row['game']==game and row['tileset']=='FOREST'and row.get('map',name)==name:
            if 'x'in row:positioned[row['id'],row['quadrant'],row['x'],row['y']]=row
            else:selected[row['id'],row['quadrant']]=row
    source=Image.new('RGBA',(m['width']*32,m['height']*32));candidate=source.copy();count=0
    for pos,bid in enumerate(m['blocks']):
        for q in range(4):
            x,y=pos%m['width']*2+q%2,pos//m['width']*2+q//2
            original=preview.native_cell(sheet,ts,ts['blocks'][bid],q);source.paste(original,(x*16,y*16))
            row=positioned.get((bid,q,x,y),selected.get((bid,q)))
            candidate.paste(preview.replacement_image(CACHE,row,packed,ROOT/'TileShift')if row else original,(x*16,y*16));count+=bool(row)
    return source,candidate,count


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write-approved-trees',action='store_true')
    args=p.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    active=[r for path in(ROOT/'TileShift/mappings').glob('*.lua')for r in preview.read_reviewed(path)if r['role']not in ROLES]
    records=json.loads((ROOT/'.work/tileshift-catalog/firered.json').read_text())['cells']
    records={(r['pair'],r['mid']):r for r in records}
    def ref(pair,mid):return {'game':'firered','tileset':pair,'id':mid,'hash':records[pair,mid]['pixel_sha256']}
    native_root=CACHE/'firered/data/generated/gba/native';mf=catalog.read_lua(native_root/'manifest.lua')
    spec=mf['layouts']['FR_PALLET_TOWN'];layout=decode_layout(native_root/spec['file']);mids=(28,29,36,37)
    native_positions=[]
    for y in range(layout['height']-1):
        for x in range(layout['width']-1):
            if[layout['mids'][(y+dy)*layout['width']+x+dx]for dx,dy in((0,0),(1,0),(0,1),(1,1))]==list(mids):native_positions.append((x,y))
    assert native_positions and spec['pair']=='pallet_outdoor'
    native_raw=(native_root/spec['file']).read_bytes()
    if native_raw[:4]!=b'SVML':native_raw=zlib.decompress(native_raw)
    offset=16+native_raw[14]*native_raw[15]*2
    for x,y in native_positions:
        assert all(native_raw[offset+((y+dy)*layout['width']+x+dx)*4+2]==7 for dx,dy in((0,0),(1,0),(0,1),(1,1)))
    packed={};whole_native=Image.new('RGBA',(32,32))
    for q,mid in enumerate(mids):whole_native.paste(preview.native_donor(CACHE,ref('pallet_outdoor',mid),packed),(q%2*16,q//2*16))
    whole_native.save(OUT/'firered-complete-native-broadleaf32.png')
    boundary_seed=next(r for r in active if r.get('role')=='boundary_tree'and r.get('kind')=='third_party')
    rows=[];proofs=[];counts=Counter();source_example=None;small_example=None
    for game in ('red','blue','yellow'):
        root=CACHE/game;maps=catalog.read_lua(root/'data/generated/maps.lua')
        ts=catalog.read_lua(root/'data/generated/tilesets.lua')['FOREST'];sheet=Image.open(root/ts['image'])
        data=json.loads((ROOT/f'.work/tileshift-catalog/{game}.json').read_text())
        cells={(r['block_id'],r['quadrant']):r for r in data['cells']if r['tileset']=='FOREST'}
        files=next(t['fingerprints']for t in data['tilesets']if t['tileset']=='FOREST')
        seeds=[cells[2,q]for q in range(4)];small=cells[4,2]
        assert small['tiles']==[2,3,18,19]and small['walkable_tiles']==[False]*4
        assert not small['warp_tile_present']and not small['grass_tile_present']
        for name in MAPS:
            m=maps[name];w,h=m['width']*2,m['height']*2
            def source(x,y):
                bid=m['blocks'][y//2*m['width']+x//2];q=y%2*2+x%2
                return bid,q,cells[bid,q]
            def new(bid,q,cell,role):
                return {'game':game,'style':'gen3','tileset':'FOREST','map':name,'id':bid,'quadrant':q,'role':role,
                        'status':'reviewed','sourceHash':cell['grayscale_pixel_sha256'],'sourceFiles':files}
            accounted=set()
            for y in range(h-1):
                for x in range(w-1):
                    parts=[source(x+q%2,y+q//2)for q in range(4)]
                    if not all(c['tiles']==s['tiles']and c['grayscale_pixel_sha256']==s['grayscale_pixel_sha256']and review.behavior_key(c)==review.behavior_key(s)for (_,_,c),s in zip(parts,seeds)):continue
                    rendered=Image.new('RGBA',(32,32));original=rendered.copy()
                    for q,(bid,sq,cell)in enumerate(parts):
                        xx,yy=x+q%2,y+q//2;assert(xx,yy)not in accounted;accounted.add((xx,yy))
                        assert not cell['walkable_tiles'][2]and not cell['grass_tile_present']and not cell['warp_tile_present']
                        row=new(bid,sq,cell,'forest_whole_broadleaf_tree_'+str(q))
                        row.update(x=xx,y=yy,donor=ref('pallet_outdoor',mids[q]),
                            evidence='Reviewed intact native32x32 FireRed broadleaf tree, actual FRPalletTown28/29 above36/37. All1024 native canopy/trunk/ground pixels remain unchanged: no clipping, compaction or scaling. Every original full2x2 source-tree neighborhood, all16 raw8px materials, per-quadrant source pixels and walk/grass/warp flags are checked. Position-scoped rows publish the four matching source occurrences together. This static FOREST scenery retains original source collision and original FOREST Cut restrictions; native scripts and events are unchanged.')
                        rows.append(row);rendered.paste(preview.replacement_image(CACHE,row,packed,ROOT/'TileShift'),(q%2*16,q//2*16))
                        original.paste(preview.native_cell(sheet,ts,ts['blocks'][bid],sq),(q%2*16,q//2*16))
                    assert rendered.tobytes()==whole_native.tobytes()
                    counts[game,'whole_tree']+=1
                    proofs.append({'game':game,'map':name,'northwest_cell':[x,y],'source_cells':[[b,q]for b,q,_ in parts],
                        'all_source_raw16':sum([c['tiles']for _,_,c in parts],[]),
                        'source_collision_cells':[c['walkable_tiles'][2]for _,_,c in parts],
                        'whole_native_rgba_sha256':catalog.sha(rendered.tobytes()),'all_native_pixels_unchanged':1024})
                    if source_example is None:source_example=original
            for y in range(h):
                for x in range(w):
                    bid,q,cell=source(x,y)
                    if any(cell['tiles']==s['tiles']and cell['grayscale_pixel_sha256']==s['grayscale_pixel_sha256']and review.behavior_key(cell)==review.behavior_key(s)for s in seeds):assert(x,y)in accounted,'Unmatched partial source tree feature'
            uses=Counter((bid,q)for bid in m['blocks']for q in range(4))
            for bid,q in sorted(uses):
                cell=cells[bid,q]
                if cell['tiles']!=small['tiles']or cell['grayscale_pixel_sha256']!=small['grayscale_pixel_sha256']or review.behavior_key(cell)!=review.behavior_key(small):continue
                row=new(bid,q,cell,SMALL_ROLE)
                for key in ('kind','asset','assetFileHash','credit','sourceUrl'):row[key]=copy.deepcopy(boundary_seed[key])
                row['base']=ref(mf['layouts']['FR_'+name]['pair'],1)
                row['evidence']='Reviewed static small forest boundary-tree role in actual source/remake context. Exact raw2,3,18,19, all four8px materials blocked, no grass/warp flag. Uses the user-approved compact Gen3 round tree already selected for narrow boundary scenery, over complete native counterpart forest ground1. Original FOREST restrictions prohibit the OVERWORLD Cut-tree swap; this remains static boundary scenery and no object interaction, map geometry or source event is changed.'
                rows.append(row);counts[game,'small_boundary_cells']+=uses[bid,q]
                if small_example is None:small_example=preview.native_cell(sheet,ts,ts['blocks'][bid],q)
    catalogs={g:json.loads((ROOT/f'.work/tileshift-catalog/{g}.json').read_text())for g in('red','blue','yellow','firered')}
    assert preview.verify(rows,CACHE,catalogs,ROOT/'TileShift')==len(rows)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    canvas=Image.new('RGB',(1380,740),'#18212b');d=ImageDraw.Draw(canvas)
    d.text((12,12),'GEN1 FOREST TREES - complete native32x32 broadleaf feature and narrow compact boundary trees',font=font,fill='white')
    d.text((12,41),'All four source-neighbor cells and full source8px behavior are checked. Original static FOREST collision and Cut restrictions stay unchanged.',font=font,fill='#c4cdd8')
    for x,label,im in ((12,'Source whole32x32 tree',source_example),(310,'Complete native FR32x32 tree',whole_native)):
        d.text((x,90),label,font=font,fill='white');canvas.paste(im.resize((256,256),Image.Resampling.NEAREST),(x,120))
    d.multiline_text((620,125),'Native FR_PALLET_TOWN actual full glyph:\n28 29\n36 37\n\nAll1024 native pixels unchanged\nNo48px ViridianForest clipping\nComplete original32px footprint\nAll four source collision cells blocked',font=font,fill='white',spacing=9)
    small_row=next(r for r in rows if r['role']==SMALL_ROLE)
    for x,label,im in ((12,'Source narrow boundary tree',small_example),(310,'Approved compact Gen3 tree',preview.replacement_image(CACHE,small_row,packed,ROOT/'TileShift'))):
        d.text((x,433),label,font=font,fill='white');canvas.paste(im.resize((128,128),Image.Resampling.NEAREST),(x,466))
    d.multiline_text((620,455),'Small boundary art: user-approved J-Treecko252 tree\nNative FR counterpart ground1 remains under its alpha.\nNo Cuttable object/event is added.\n\nPer-cart whole trees: '+str(counts['red','whole_tree'])+'; small boundary cells: '+str(counts['red','small_boundary_cells']),font=font,fill='white',spacing=9)
    d.text((12,670),'Private proposal; whole native32px artwork requires visual approval before activation.',font=font,fill='white')
    canvas.save(OUT/'forest-whole-native-and-boundary-tree-review.png')
    for name in ('VIRIDIAN_FOREST','SAFARI_ZONE_WEST'):
        source,current,current_count=scene('red',name,active,packed);_,candidate,candidate_count=scene('red',name,active+rows,packed)
        candidate.save(OUT/f'red-{name}-trees-candidate.png')
        image=Image.new('RGB',(source.width*2+48,source.height+128),'#18212b');draw=ImageDraw.Draw(image)
        draw.text((12,12),name+' - complete native32px broadleaf trees; original terrain/encounters/collision unchanged',font=font,fill='white')
        for col,(label,im)in enumerate((('Current reviewed ground/grass',current),('Candidate complete forest trees',candidate))):
            x=16+col*(source.width+16);draw.text((x,48),label,font=font,fill='white');image.paste(im,(x,80))
        draw.text((12,source.height+93),f'Coverage{current_count} -> {candidate_count}/{source.width*source.height//256}; unreviewed source features stay visible.',font=font,fill='white')
        image.save(OUT/f'red-{name}-trees-context-review.png')
    (OUT/'forest-tree-candidates.lua').write_text('return '+review.lua_value(rows)+'\n',encoding='utf-8')
    (OUT/'forest-tree-proof.json').write_text(json.dumps({'status':'private_visual_review_required','rows':len(rows),
       'counts':{g:{k:counts[g,k]for k in ('whole_tree','small_boundary_cells')}for g in('red','blue','yellow')},
       'native_map':'FR_PALLET_TOWN','native_complete_tree_positions':native_positions,
       'whole_native_pixel_sha256':catalog.sha(whole_native.tobytes()),'source_proofs':proofs},indent=2))
    if args.write_approved_trees:
        retained=[r for r in preview.read_reviewed(extended.TARGET)if r['role']not in ROLES];extended.write_groups(retained+rows)
    print(json.dumps({'rows':len(rows),'counts':{g:{k:counts[g,k]for k in('whole_tree','small_boundary_cells')}for g in('red','blue','yellow')},
                      'production_written':args.write_approved_trees},indent=2))


if __name__=='__main__':main()
