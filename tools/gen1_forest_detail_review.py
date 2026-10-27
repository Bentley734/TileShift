"""Review forest signs, non-encounter lawn variants and small Safari trees."""
from __future__ import annotations
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import catalog
import preview
import review
import gen1_extended_review as extended
from gen1_forest_review import MAPS
from gen1_forest_tree_review import scene

ROOT=Path(__file__).resolve().parents[2]
CACHE=Path(catalog.os.environ['APPDATA'])/'pokemon-love2d'
OUT=ROOT/'.work/tileshift-gen1-forest-review'
SPECS=((21,2,3,'forest_freestanding_sign'),(41,3,1,'forest_non_encounter_lawn_tuft'),
       (46,0,1,'forest_non_encounter_lawn_tuft'),(44,0,1,'forest_non_encounter_lawn_tuft'),
       (46,3,1,'forest_non_encounter_lawn_tuft'),(124,2,None,'forest_safari_round_boundary_tree'))
ROLES={r[3]for r in SPECS}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write-approved-details',action='store_true')
    args=p.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    active=[r for path in(ROOT/'TileShift/mappings').glob('*.lua')for r in preview.read_reviewed(path)if r['role']not in ROLES]
    native=json.loads((ROOT/'.work/tileshift-catalog/firered.json').read_text())['cells']
    native={(r['pair'],r['mid']):r for r in native};mf=catalog.read_lua(CACHE/'firered/data/generated/gba/native/manifest.lua')
    compact=next(r for r in active if r.get('role')=='boundary_tree'and r.get('kind')=='third_party')
    rows=[];proofs=[];counts=Counter();packed={};examples={}
    for game in('red','blue','yellow'):
        root=CACHE/game;maps=catalog.read_lua(root/'data/generated/maps.lua')
        ts=catalog.read_lua(root/'data/generated/tilesets.lua')['FOREST'];sheet=Image.open(root/ts['image'])
        data=json.loads((ROOT/f'.work/tileshift-catalog/{game}.json').read_text())
        cells={(r['block_id'],r['quadrant']):r for r in data['cells']if r['tileset']=='FOREST'}
        files=next(t['fingerprints']for t in data['tilesets']if t['tileset']=='FOREST')
        for name in MAPS:
            m=maps[name];used=Counter((bid,q)for bid in m['blocks']for q in range(4));pair=mf['layouts']['FR_'+name]['pair']
            def ref(mid):return {'game':'firered','tileset':pair,'id':mid,'hash':native[pair,mid]['pixel_sha256']}
            for b,q,mid,role in SPECS:
                seed=cells[b,q]
                assert not seed['grass_tile_present']and not seed['warp_tile_present']
                assert seed['walkable_tiles']==([True]*4 if mid==1 else[False]*4)
                for (bid,sq),uses in sorted(used.items()):
                    source=cells[bid,sq]
                    if source['tiles']!=seed['tiles']or source['grayscale_pixel_sha256']!=seed['grayscale_pixel_sha256']or review.behavior_key(source)!=review.behavior_key(seed):continue
                    row={'game':game,'style':'gen3','tileset':'FOREST','map':name,'id':bid,'quadrant':sq,'role':role,
                         'status':'reviewed','sourceHash':source['grayscale_pixel_sha256'],'sourceFiles':files}
                    if mid:
                        row['donor']=ref(mid)
                        row['evidence']='Reviewed complete native FR counterpart feature in actual forest/Safari context. Standalone source sign retains complete native wooden sign3 and original source sign interaction; non-encounter decorative lawn tufts use complete ordinary native lawn1, as the previously reviewed lawn density variants do. Exact raw8px pattern, complete pixel hash and all source walk/grass/warp flags are checked. No tall-grass encounter, cliff, arrow or field event is inferred; original source collision, interactions and map layout remain authoritative.'
                    else:
                        for key in ('kind','asset','assetFileHash','credit','sourceUrl'):row[key]=copy.deepcopy(compact[key])
                        row['base']=ref(1)
                        row['evidence']='Reviewed actual complete16px round Safari boundary tree, raw84,85,86,87 and all four8px materials blocked, no grass/warp flag. The established compact Gen3 round-tree choice retains its full approved16px artwork over actual counterpart FRground1. Only exact source-art/behavior aliases in named Safari maps are used. This is static FOREST scenery; original collision, source Cut restrictions and scripts remain unchanged.'
                    rows.append(row);counts[game,role]+=uses
                    proofs.append({'game':game,'map':name,'source':[bid,sq],'raw':source['tiles'],'walkable8':source['walkable_tiles'],
                                   'role':role,'occurrences':uses,'native_ground_or_feature':mid or 1})
                    if game=='red':examples.setdefault((b,q),(source,preview.native_cell(sheet,ts,ts['blocks'][bid],sq),row))
    catalogs={g:json.loads((ROOT/f'.work/tileshift-catalog/{g}.json').read_text())for g in('red','blue','yellow','firered')}
    assert preview.verify(rows,CACHE,catalogs,ROOT/'TileShift')==len(rows)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
    image=Image.new('RGB',(1320,570),'#18212b');draw=ImageDraw.Draw(image)
    draw.text((12,12),'FOREST DETAILS - full signs, decorative non-encounter lawn and narrow round Safari trees',font=font,fill='white')
    draw.text((12,40),'No directional arrow is removed. All source grass/warp/walk flags and original interactions remain unchanged.',font=font,fill='#c4cdd8')
    for col,((b,q),(source,original,row))in enumerate(examples.items()):
        x=12+col*215
        draw.text((x,85),f'Source{b}:{q}',font=font,fill='white');image.paste(original.resize((96,96),Image.Resampling.NEAREST),(x,115))
        draw.text((x,220),str(source['tiles']),font=font,fill='#c4cdd8')
        candidate=preview.replacement_image(CACHE,row,packed,ROOT/'TileShift')
        image.paste(candidate.resize((96,96),Image.Resampling.NEAREST),(x,275))
        draw.multiline_text((x,385),row['role'].replace('forest_','').replace('_','\n'),font=font,fill='white',spacing=3)
    draw.text((12,525),'Per-cart cells: '+str({role:counts['red',role]for role in sorted(ROLES)}),font=font,fill='white')
    image.save(OUT/'forest-signs-lawn-and-round-safari-tree-review.png')
    for name in('VIRIDIAN_FOREST','SAFARI_ZONE_WEST'):
        source,current,count=scene('red',name,active,packed);_,candidate,newcount=scene('red',name,active+rows,packed)
        canvas=Image.new('RGB',(source.width*2+48,source.height+128),'#18212b');d=ImageDraw.Draw(canvas)
        d.text((12,12),name+' - signs, non-encounter lawn and small round Safari boundary trees',font=font,fill='white')
        for col,(label,im)in enumerate((('Current reviewed stage',current),('Candidate details; arrows remain native',candidate))):
            x=16+col*(source.width+16);d.text((x,48),label,font=font,fill='white');canvas.paste(im,(x,80))
        d.text((12,source.height+94),f'Coverage{count} -> {newcount}/{source.width*source.height//256}; all unreviewed terrain stays visible.',font=font,fill='white')
        canvas.save(OUT/f'red-{name}-details-context-review.png')
    (OUT/'forest-detail-candidates.lua').write_text('return '+review.lua_value(rows)+'\n',encoding='utf-8')
    (OUT/'forest-detail-proof.json').write_text(json.dumps({'status':'private_visual_review_required','rows':len(rows),
        'counts':{g:{role:counts[g,role]for role in sorted(ROLES)}for g in('red','blue','yellow')},'source_proofs':proofs},indent=2))
    if args.write_approved_details:
        retained=[r for r in preview.read_reviewed(extended.TARGET)if r['role']not in ROLES];extended.write_groups(retained+rows)
    print(json.dumps({'rows':len(rows),'red_cells':{role:counts['red',role]for role in sorted(ROLES)},
                      'production_written':args.write_approved_details},indent=2))


if __name__=='__main__':main()
