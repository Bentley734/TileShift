"""Connect Saffron's walkable streets with its existing native brick paving.

Only Saffron art is changed. Original curb cells are collision0; genuine four
blocked interior fence cells retain visible whole native stone bollards. The
outer rail stays, with paved access gaps anchored to actual original warps.
Native object/door/window colors stay bit-for-bit intact, including both Center
variants; only checked exposed ground beneath their alpha changes.
"""
import argparse
import copy
import hashlib
import json
import os
import re
from collections import Counter,defaultdict
from pathlib import Path
from types import SimpleNamespace

from PIL import Image,ImageDraw,ImageFont
import catalog
import preview
import gen2_extended_review as e
from center_mart_overhang_review import write_rows
from interior_review import Imports
from johto_remaining_review import artwork
from native_room_parts import RoomParts

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'.work/tileshift-v0301-saffron'
TARGET=ROOT/'mappings/gen2_kanto_details_finish.lua'
DEST=ROOT/'assets/third_party/saffron-paving'
CITY='SAFFRON_CITY'
BLOCKED={(14,21),(24,21),(25,21),(24,29)}
GROUND_ROLES={'short_nonencounter_grass','open_grassy_ground','gen2_pallet_open_lawn',
              'kanto_native_brick_road','saffron_urban_brick_paving'}
CATALOGS=('roof_catalog.lua','side_catalog.lua','center_mart_roofs.lua','goldenrod_roofs.lua',
          'pallet_roofs.lua','johto_roofs.lua','gen2_kanto_building_roofs.lua','gen2_kanto_landmark_decorations.lua')
ART_FIELDS={'kind','donor','base','parts','asset','assetFileHash','assetPixelHash','assetFrames','artOverlay',
            'sourceColors','animated','animation','frames','flora'}


def stable(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def scope(row):return row['game']in e.GAMES and row.get('map')==CITY and row['style']=='gen3'
def key(row):return tuple(row.get(k)for k in('game','style','tileset','id','quadrant','map','x','y'))
def urban(x,y):return 2<=x<=37 and 4<=y<=35 or x<=2 and y in(24,25)or x>=37 and y in(22,23)
def ring(x,y):return (x in(2,37)and 6<=y<=31)or(y in(6,31)and 2<=x<=37)


class Review:
    def __init__(self):
        self.cache=Path(os.environ['APPDATA'])/'pokemon-love2d'
        self.imp=Imports(self.cache,ROOT.parent/'.work/tileshift-catalog');self.packed=self.imp.packed
        self.paths=[ROOT/p for p in dict.fromkeys(re.findall(r"'(mappings/[^']+\.lua)'",(ROOT/'main.lua').read_text()))]
        self.catalog_paths=[ROOT/'lib'/name for name in CATALOGS]
        self.original={p:preview.read_reviewed(p)for p in self.paths+self.catalog_paths}
        self.rows={p:[copy.deepcopy(r)for r in rows if not(p==TARGET and r.get('saffronUrbanOverride'))]
                   for p,rows in self.original.items()}
        self.before=[r for p in self.paths for r in self.original[p]]
        self.brick=copy.deepcopy(next(r for r in self.before if r['game']=='crystal'and r['role']=='kanto_native_brick_road'))
        self.paving=Image.open(ROOT/self.brick['asset']).convert('RGBA');assert self.paving.size==(16,16)
        self.post_room=RoomParts(self.imp,'firered','FR_INDIGO_PLATEAU_EXTERIOR')
        self.post_ref=self.post_room.ref(711);post_rec=self.imp.cell_index('firered')[self.post_room.pair,711]
        self.post=preview.native_donor(self.cache,self.post_ref,self.packed,['mid'],{'mid':post_rec['layer_sha256']['mid']})
        assert sum(p[3]>0 for p in self.post.get_flattened_data())==211
        post_full=preview.native_donor(self.cache,self.post_ref,self.packed)
        assert all(a==b for a,b in zip(self.post.get_flattened_data(),post_full.get_flattened_data())if a[3])
        assert {b for a,b in zip(self.post.get_flattened_data(),post_full.get_flattened_data())if not a[3]}=={(115,206,165,255)}
        self.files={};self.foregrounds={};self.records=[];self.rebased=0;self.compact=0;self.pixel_checks=0
        self.added=[];self.collision_stats={};self.changed=[]
        self.grass_colors={(66,181,140,255),(115,206,165,255),(165,230,197,255),
            (189,239,214,255),(156,230,197,255),(140,214,189,255)}

    def save_foreground(self,image,source):
        digest=catalog.sha(image.tobytes());name='foreground-'+digest[:24]+'.png';path=DEST/name
        if not path.exists()or catalog.sha(Image.open(path).convert('RGBA').tobytes())!=digest:image.save(path)
        file_hash=catalog.sha(path.read_bytes());self.files[name]=file_hash
        self.foregrounds.setdefault(name,dict(rgba_sha256=digest,dimensions=[16,16],opaque_pixels=sum(p[3]>0 for p in image.get_flattened_data()),sources=[]))['sources'].append(source)
        return {'kind':'third_party','asset':path.relative_to(ROOT).as_posix(),'hash':file_hash,'mode':'over','preserveRects':{}}

    def paved_art(self,foreground,source):
        overlay=self.save_foreground(foreground,source)
        return {'kind':'third_party','asset':self.brick['asset'],'assetFileHash':self.brick['assetFileHash'],
                'artOverlay':overlay}

    def rebase(self,row,variant=False):
        """Return a checked foreground over the exact existing paving asset."""
        previous=row.get('saffronPavingRebase')
        original=copy.deepcopy(previous['originalArtwork']if previous else artwork(row))
        original.pop('canopy',None)
        if row.get('animated')or row.get('canopy'):return False
        if original.get('kind')=='source_palette':return False
        if original.get('base'):
            if original['base'].get('id')!=1:return False
            naked=copy.deepcopy(original);naked.pop('base',None)
            if not(naked.get('parts')or naked.get('asset')):return False
            if naked.get('artOverlay')and naked['artOverlay'].get('mode')!='over':return False
            foreground=preview.replacement_image(self.cache,naked,self.packed,ROOT)
        elif original.get('donor'):
            ref=original['donor']
            if ref.get('game')not in('firered','emerald','leafgreen'):return False
            rec=self.imp.cell_index(ref['game'])[ref['tileset'],ref['id']]
            full=preview.native_donor(self.cache,ref,self.packed)
            foreground=preview.native_donor(self.cache,ref,self.packed,['mid','over'],{k:rec['layer_sha256'][k]for k in('mid','over')})
            omitted={b for a,b in zip(foreground.get_flattened_data(),full.get_flattened_data())if not a[3]}
            if not omitted or not omitted<=self.grass_colors:return False
            assert all(a==b for a,b in zip(foreground.get_flattened_data(),full.get_flattened_data())if a[3])
        else:return False
        if foreground.getextrema()[3][0]==255:return False
        assert set(foreground.getchannel('A').get_flattened_data())<={0,255}
        old=preview.replacement_image(self.cache,original,self.packed,ROOT)
        source={'originalArtwork':original,'source_game':row.get('game'),'source_map':CITY,
                'role':row.get('role'),'variant':'compact'if variant else'expanded/default'}
        art=self.paved_art(foreground,source)
        updated=Image.alpha_composite(self.paving,foreground)
        for a,b,c in zip(foreground.get_flattened_data(),old.get_flattened_data(),updated.get_flattened_data()):
            if a[3]:assert b==c;self.pixel_checks+=1
        original_credit=previous.get('originalCredit')if previous else row.get('credit')
        original_url=previous.get('originalSourceUrl')if previous else row.get('sourceUrl')
        for field in ART_FIELDS:row.pop(field,None)
        row.update(art)
        row['credit']='MetalFlygon08 (brick paving); '+(original_credit or 'native Game Freak object from locally imported Gen3 artwork')
        row['sourceUrl']=original_url or self.brick['sourceUrl']
        row['saffronPavingRebase']={k:v for k,v in dict(originalArtwork=original,originalCredit=original_credit,
            originalSourceUrl=original_url,unchanged_native_foreground_pixels=sum(p[3]>0 for p in foreground.get_flattened_data())).items()if v is not None}
        self.rebased+=1;self.compact+=int(variant)
        return True

    def current(self,game):
        return[r for p in self.paths for r in self.rows[p]if r['game']==game and r['style']=='gen3'
            and r['tileset']=='TILESET_KANTO'and r.get('map',CITY)==CITY]

    def review_city(self,game):
        data=e.source(self.cache,game);m=data['maps'][CITY];selected=self.current(game)
        generic={};positioned={}
        for r in selected:
            if r.get('x')is None:generic[r['id'],r['quadrant']]=r
            else:positioned[r['x'],r['y']]=r
        north=[w for w in m['warps']if w['y']==3]
        assert {w['x']for w in north}=={8,18,26,34}
        openings={(x,6)for w in north for x in range(w['x']-1,w['x']+2)}
        openings|={(2,24),(2,25),(37,22),(37,23)}|{(x,31)for x in range(15,19)}
        count=Counter();blockers=[]
        for i,bid in enumerate(m['blocks']):
            for q in range(4):
                x,y=i%m['width']*2+q%2,i//m['width']*2+q//2;c=e.cell_info(self.cache,game,data,m['tileset'],bid,q)
                old=positioned.get((x,y),generic.get((bid,q)));assert old
                curb='fence_'in old['role']and c['collision']==0
                floor=old['role']in GROUND_ROLES
                stone=(x,y)in BLOCKED
                garden=c['tiles']==[14,14,85,85]and urban(x,y)
                if stone:
                    assert c['collision']==7
                    art=self.paved_art(self.post,dict(native_post_ref=self.post_ref,native_layer='mid',
                        native_map='FR_INDIGO_PLATEAU_EXTERIOR',native_source_cell=[6,8],whole_post_pixels_retained=211))
                    role='saffron_blocking_stone_bollard';count['blocked_cells_with_visible_bollards']+=1;blockers.append([x,y])
                elif curb and ring(x,y)and(x,y)not in openings:
                    count['perimeter_fence_cells_retained']+=1;continue
                elif urban(x,y)and(curb or floor):
                    assert c['collision']==0
                    if old.get('asset')==self.brick['asset']and old['role']=='kanto_native_brick_road':
                        count['existing_brick_cells_retained']+=1;continue
                    art=artwork(self.brick);role='saffron_urban_brick_paving';count['walkable_curbs_paved'if curb else'green_floor_cells_paved']+=1
                elif garden:
                    # True blocking north boundary objects stay visible. Their
                    # full native post pixels remain; only exterior field goes.
                    art=copy.deepcopy(old)
                    assert self.rebase(art),(game,x,y,art)
                    art={k:v for k,v in art.items()if k in ART_FIELDS or k in('credit','sourceUrl','saffronPavingRebase')}
                    role=old['role'];count['outside_garden_objects_rebased']+=1
                else:continue
                assert all(a.get('source_pixels_complete')for a in c['attributes'])
                r=dict(game=game,style='gen3',map=CITY,tileset=m['tileset'],id=bid,quadrant=q,x=x,y=y,
                    sourceCells=[[x,y]],sourceHash=c['sourceHash'],sourceFiles=data['fingerprints'][m['tileset']],
                    sourceCollision=c['collision'],sourcePriority=[bool(a.get('priority'))for a in c['attributes']],
                    sourcePalettes=[a.get('palette',1)for a in c['attributes']],role=role,status='reviewed',saffronUrbanOverride=True,
                    evidence='Saffron-specific user-approved connected brick streets. Original thin curb glyphs are collision0 and receive the exact existing brown/yellow brick paving. Only the outer street perimeter rail remains, with clear original north-building and route-access gaps. Four original collision7 interior fence cells remain visibly blocked by complete native211-pixel stone bollards, not invisible paved walls. All original collision, source geometry, doors, warps, NPCs and events remain unchanged.')
                r.update(art);r['credit']=r.get('credit',self.brick['credit']);r['sourceUrl']=r.get('sourceUrl',self.brick['sourceUrl'])
                r['compositionPixelHash']=catalog.sha(preview.replacement_image(self.cache,r,self.packed,ROOT).tobytes())
                self.added.append(r)
        assert count['blocked_cells_with_visible_bollards']==4
        self.collision_stats[game]=dict(counts=dict(count),original_north_entrances=north,
            paved_perimeter_access_cells=[list(p)for p in sorted(openings)],visible_blocked_interior_cells=blockers,
            changed_source_collisions=0)

    def apply(self):
        # Preserve every building sprite. Rebase only exposed checked native
        # ground; true green roof/window/object artwork is never recolored.
        for path,rows in self.rows.items():
            if path in self.catalog_paths:continue
            for r in rows:
                if not scope(r)or r['role']in GROUND_ROLES or r['role']in('boundary_tree','dense_conifer_crown','dense_conifer_trunk'):continue
                changed=self.rebase(r)
                compact=r.get('buildingCompact')
                if compact:
                    changed=self.rebase(compact,True)or changed
                if changed:
                    if r.get('x')is not None:r.setdefault('sourceCells',[[r['x'],r['y']]])
                    r['compositionPixelHash']=catalog.sha(preview.replacement_image(self.cache,r,self.packed,ROOT).tobytes());self.changed.append(r)
        for game in e.GAMES:self.review_city(game)
        # Source map artwork is already positional for architecture. Remove
        # only exact old ground/object keys superseded by this Saffron review;
        # generic fallbacks remain available for every unrelated location.
        newkeys={key(r)for r in self.added}
        for path,rows in self.rows.items():
            if path in self.catalog_paths:continue
            self.rows[path]=[r for r in rows if not(r.get('x')is not None and key(r)in newkeys)]
        self.rows[TARGET]+=self.added
        # Roof and side artwork remains true transparent foreground. Its actual
        # underlying map cells are now paved; no opaque ground is painted into
        # an overhead tile. Assert that no explicit grass base can survive there.
        decorations=[r for p in self.catalog_paths for r in self.rows[p]if scope(r)]
        assert not any(r.get('base')for r in decorations),'Saffron decorative layer contains an unchecked explicit ground base'
        self.decoration_checks=len(decorations)


def variant(rows,compact):
    if not compact:return rows
    result=[]
    for r in rows:
        if r.get('buildingCompact'):
            out=copy.deepcopy(r)
            for field in ART_FIELDS:out.pop(field,None)
            out.update(r['buildingCompact']);out.pop('compositionPixelHash',None);result.append(out)
        else:result.append(r)
    return result


def comparison(before,after,path,label):
    left=Image.open(before).convert('RGB');right=Image.open(after).convert('RGB');assert left.size==right.size
    im=Image.new('RGB',(left.width*2+48,left.height+106),'#18202c');d=ImageDraw.Draw(im)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17)
    d.text((16,10),'Saffron City — connected brick streets ('+label+')',fill='white',font=font)
    d.text((16,37),'Previous Gen 3 layout',fill='white');d.text((left.width+32,37),'Connected paving; perimeter access kept open',fill='white')
    im.paste(left,(16,62));im.paste(right,(left.width+32,62));d.text((16,im.height-22),'Native imported background-map previews. Four blocking garden-fence cells use visible native stone bollards; original gameplay unchanged.',fill='#cdd5df')
    im.save(path)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--activate',action='store_true');p.add_argument('--no-previews',action='store_true');args=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);DEST.mkdir(parents=True,exist_ok=True);review=Review();review.apply()
    staged=[r for p in review.paths for r in review.rows[p]]
    livekeys={key(r)for r in staged}
    newkeys={key(r)for r in review.added}
    changed=[r for r in review.changed if key(r)in livekeys and key(r)not in newkeys]+review.added
    proof={'collision_checks':review.collision_stats,'rebased_artworks':review.rebased,'compact_artworks_rebased':review.compact,
        'unchanged_foreground_pixel_checks':review.pixel_checks,'transparent_roof_side_rows_checked':review.decoration_checks,
        'positional_override_rows':len(review.added),'activated':args.activate}
    (OUT/'changed-candidates.json').write_text(json.dumps(changed,indent=2)+'\n')
    try:
        proof['validation']=e.validate_batch(changed,SimpleNamespace(cache=review.cache,engine=ROOT.parent/'.tools/engine-0395',output=OUT),ROOT)
    except AssertionError as exc:
        tb=exc.__traceback__
        while tb:
            loc=tb.tb_frame.f_locals
            if 'expanded'in loc and 'rows'in loc:
                expanded={key(r):r for r in loc['expanded']};expected={key(r):r for r in loc['rows']}
                diff=[dict(key=list(k),expected=r,actual=expanded.get(k))for k,r in expected.items()if expanded.get(k)!=r]
                (OUT/'serialization-diff.json').write_text(json.dumps(diff[:3],indent=2)+'\n')
            tb=tb.tb_next
        raise
    # Two Center variants are independently rendered and checked, matching the
    # actual runtime merge and the expanded-only decorative catalog toggle.
    if not args.no_previews:
        for compact in(False,True):
            name='compact'if compact else'expanded'
            before=variant(review.before,compact);after=variant(staged,compact)
            old_decor=[r for p in review.catalog_paths for r in review.original[p]if not(compact and r['role']=='larger_center')]
            new_decor=[r for p in review.catalog_paths for r in review.rows[p]if not(compact and r['role']=='larger_center')]
            preview.map_preview(review.cache,OUT,'crystal',CITY,'before-'+name,before,review.packed,1,ROOT,roof_rows=old_decor)
            preview.map_preview(review.cache,OUT,'crystal',CITY,'after-'+name,after,review.packed,1,ROOT,roof_rows=new_decor)
            comparison(OUT/f'before-{name}-after-native.png',OUT/f'after-{name}-after-native.png',OUT/f'Saffron-connected-paving-{name}-comparison.png',name+' Center')
    unaffected=0
    for path,old in review.original.items():
        new=review.rows[path]
        old_other=[r for r in old if not scope(r)];new_other=[r for r in new if not scope(r)]
        assert old_other==new_other,('Other map changed',path)
        unaffected+=len(old_other)
        if old!=new:
            proof.setdefault('changed_modules',[]).append(dict(path=path.relative_to(ROOT).as_posix(),before_rows=len(old),after_rows=len(new)))
            if args.activate:write_rows(path,new)
    proof['other_map_rows_preserved']=unaffected
    (DEST/'provenance.json').write_text(json.dumps(dict(origin='Exact existing MetalFlygon08 brick pavement beneath unchanged native foreground pixels. No repainting or scaling. Four blocked original garden-fence cells use the whole native FireRed Indigo stone post.',paving_asset=review.brick['asset'],paving_sha256=review.brick['assetFileHash'],foregrounds=review.foregrounds,files=review.files),indent=2)+'\n')
    (OUT/'proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof,indent=2))


if __name__=='__main__':main()
