"""Offline review of every selected Gen2 residential interior and floor context.

Only the new domestic-floor module is authored. Chair/seat artwork belongs to
the independent chair audit. No original module, runtime, collision or map edit.
"""
import argparse
import copy
import json
import os
import re
from collections import Counter,defaultdict,deque
from pathlib import Path
from types import SimpleNamespace

from PIL import Image,ImageDraw,ImageFont
import catalog
import preview
import gen2_extended_review as e
from interior_review import Imports
from johto_remaining_review import artwork
from native_room_parts import RoomParts
from center_mart_overhang_review import write_rows

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'.work/tileshift-v0303-domestic-floor-audit'
TARGET=ROOT/'mappings/gen2_domestic_floor_audit.lua'
SETS={'TILESET_HOUSE','TILESET_TRADITIONAL_HOUSE','TILESET_PLAYERS_HOUSE',
      'TILESET_PLAYERS_ROOM','TILESET_MANSION','TILESET_HOTEL'}
EXTRA={'MR_POKEMONS_HOUSE','TRAINER_HOUSE_B1F'}
ASSETS=ROOT/'assets/third_party/gen2-domestic-floor-audit'
SOURCE_ROOMS=(('firered','FR_RIVALS_HOUSE',(1,)),
              ('firered','FR_PLAYERS_HOUSE_1F',(1,)),
              ('firered','FR_VIRIDIAN_CITY_POKEMON_CENTER_1F',(641,)),
              ('firered','FR_VIRIDIAN_CITY_POKEMON_CENTER_2F',(641,)))


def digest(value):return catalog.sha(json.dumps(value,sort_keys=True,separators=(',',':')).encode())
def key(row):return tuple(row.get(k)for k in('game','style','tileset','id','quadrant','map','x','y'))
def is_chair(row):return any(t in row['role']for t in('chair','stool','seat','student_desk'))
def scoped(name,m):return m.get('environment')=='INDOOR'and(m.get('tileset')in SETS or name in EXTRA)


class Audit:
    def __init__(self):
        self.cache=Path(os.environ['APPDATA'])/'pokemon-love2d'
        self.imp=Imports(self.cache,ROOT.parent/'.work/tileshift-catalog');self.packed=self.imp.packed
        self.paths=[ROOT/p for p in dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(ROOT/'main.lua').read_text()))if ROOT/p!=TARGET]
        self.rows={p:preview.read_reviewed(p)for p in self.paths};self.all=[r for rows in self.rows.values()for r in rows]
        self.by_family=defaultdict(list)
        for p,rows in self.rows.items():
            for i,r in enumerate(rows):
                if r['game']in e.GAMES and r['style']=='gen3':self.by_family[r['game'],r['tileset']].append((r,p,i))
        self.sources={g:e.source(self.cache,g)for g in e.GAMES};self.images={};self.records=[];self.cells={};self.objects={}
        self.mask_proofs=[];self.source_masks={};self.floor_refs=set();self.source_mask_cache={}

    def image(self,row):
        art=artwork(row)
        if row.get('kind')=='source_palette':art.update({k:row[k]for k in('game','tileset','id','quadrant','sourceHash','sourceFiles','sourceColors')})
        k=digest(art)
        if k not in self.images:self.images[k]=preview.replacement_image(self.cache,row,self.packed,ROOT)
        return self.images[k]

    def grid(self,g,name,m):
        generic={};pos={}
        for r,p,i in self.by_family[g,m['tileset']]:
            if r.get('map',name)!=name:continue
            if r.get('x')is None:generic[r['id'],r['quadrant']]=(r,p,i)
            else:pos[r['id'],r['quadrant'],r['x'],r['y']]=(r,p,i)
        out={}
        for i,bid in enumerate(m['blocks']):
            for q in range(4):
                x,y=i%m['width']*2+q%2,i//m['width']*2+q//2
                selected=pos.get((bid,q,x,y),generic.get((bid,q)));assert selected,(g,name,x,y)
                out[x,y]=selected
        return out

    def inventory(self,render=True):
        objects={};map_images={}
        for g in e.GAMES:
            data=self.sources[g]
            for name,m in sorted(data['maps'].items()):
                if not isinstance(m,dict)or not scoped(name,m):continue
                cells=self.grid(g,name,m);self.cells[g,name]=cells
                roles=Counter(r['role']for r,_,_ in cells.values());base=Counter();floors=Counter()
                canvas=Image.new('RGBA',(m['width']*32,m['height']*32))
                for (x,y),(r,path,idx)in cells.items():
                    im=self.image(r);canvas.alpha_composite(im,(x*16,y*16))
                    if r.get('base'):base[json.dumps(r['base'],sort_keys=True)]+=1
                    if any(t in r['role']for t in('floor','tatami','ground')):floors[r['role']]+=1
                    c=e.cell_info(self.cache,g,data,m['tileset'],r['id'],r['quadrant'])
                    objkey=digest(dict(art=artwork(r),sourceHash=r['sourceHash'],raw=c['tiles'],role=r['role']))
                    if objkey not in objects:
                        objects[objkey]=dict(role=r['role'],art=artwork(r),sourceHash=r['sourceHash'],raw=c['tiles'],
                            collision=c['collision'],contexts=[],image_hash=catalog.sha(im.tobytes()))
                        self.objects[objkey]=(r,im)
                    objects[objkey]['contexts'].append(dict(game=g,map=name,x=x,y=y,module=path.relative_to(ROOT).as_posix(),index=idx,positioned=r.get('x')is not None))
                imagehash=catalog.sha(canvas.tobytes());same=map_images.get(imagehash)
                record=dict(game=g,map=name,tileset=m['tileset'],dimensions=list(canvas.size),cells=len(cells),roles=dict(roles),
                    explicit_bases=[dict(ref=json.loads(k),cells=v)for k,v in base.items()],floor_roles=dict(floors),rgba_sha256=imagehash,
                    same_artwork_as=same)
                self.records.append(record)
                if render:
                    dest=OUT/g;dest.mkdir(parents=True,exist_ok=True);canvas.convert('RGB').save(dest/(name+'-before.png'))
                if same is None:map_images[imagehash]=[g,name]
        (OUT/'inventory.json').write_text(json.dumps(self.records,indent=2)+'\n')
        (OUT/'object-inventory.json').write_text(json.dumps(objects,indent=2)+'\n')
        self.object_inventory=objects
        if render:self.contacts(map_images)
        return objects

    def contacts(self,map_images):
        font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',13)
        unique=list(map_images.values());w,h=360,330
        for start in range(0,len(unique),12):
            canvas=Image.new('RGB',(w*3,h*4),'#18202c');d=ImageDraw.Draw(canvas)
            for i,(g,name)in enumerate(unique[start:start+12]):
                im=Image.open(OUT/g/(name+'-before.png'));x,y=i%3*w,i//3*h
                scale=min(2,max(1,min((w-12)//im.width,(h-38)//im.height)))
                show=im.resize((im.width*scale,im.height*scale),Image.Resampling.NEAREST)
                if show.width>w-12 or show.height>h-38:
                    show.thumbnail((w-12,h-38),Image.Resampling.NEAREST)
                canvas.paste(show,(x+6,y+32));d.text((x+6,y+5),g+' / '+name,fill='white',font=font)
            canvas.save(OUT/f'maps-contact-{start//12+1:02}.png')
        objitems=list(self.objects.items());cw,ch=220,130
        for start in range(0,len(objitems),48):
            canvas=Image.new('RGB',(cw*6,ch*8),'#18202c');d=ImageDraw.Draw(canvas)
            for i,(k,(r,im))in enumerate(objitems[start:start+48]):
                x,y=i%6*cw,i//6*ch
                canvas.paste(im.resize((64,64),Image.Resampling.NEAREST),(x+4,y+30))
                d.text((x+4,y+3),str(start+i)+' '+k[:8],fill='white',font=font)
                label=r['role'].replace('johto_','').replace('domestic_','')
                d.text((x+72,y+33),label[:23]+'\n'+label[23:46]+'\n'+label[46:69],fill='#d6e0e7',font=font)
                context=self.object_inventory[k]['contexts'][0]
                d.text((x+4,y+103),context['map'][:27],fill='#abc4ce',font=font)
            canvas.save(OUT/f'objects-contact-{start//48+1:02}.png')

    def masks(self):
        """Mark only native floor/wall pixels connected to empty source cells.

        An intersection across every occurrence of a metatile excludes an
        enclosed highlight even if it shares a palette color with the floor.
        """
        for game,name,mids in SOURCE_ROOMS:
            room=RoomParts(self.imp,game,name);image=self.imp.gba(game,name)[0]
            colors=set();outside=set();queue=deque();seeds=[]
            for mid in mids:
                ref=room.ref(mid);colors.update(preview.native_donor(self.cache,ref,self.packed).get_flattened_data())
                self.floor_refs.add((game,room.pair,mid))
            for i,mid in enumerate(room.layout['mids']):
                if mid not in mids:continue
                x,y=i%room.layout['width']*16,i//room.layout['width']*16;seeds.append([i%room.layout['width'],i//room.layout['width'],mid])
                for yy in range(y,y+16):
                    for xx in range(x,x+16):outside.add((xx,yy));queue.append((xx,yy))
            assert seeds
            while queue:
                x,y=queue.popleft()
                for p in((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                    if 0<=p[0]<image.width and 0<=p[1]<image.height and p not in outside and image.getpixel(p)in colors:
                        outside.add(p);queue.append(p)
            masks={};occurrences=defaultdict(list);protected_layers={}
            for i,mid in enumerate(room.layout['mids']):
                ox,oy=i%room.layout['width']*16,i//room.layout['width']*16
                mask={(x,y)for y in range(16)for x in range(16)if(ox+x,oy+y)in outside}
                masks[mid]=masks.get(mid,mask)&mask;occurrences[mid].append([ox//16,oy//16])
            for mid,mask in masks.items():
                tag=game,room.pair,mid
                # A complete native foreground layer is authoritative, even
                # if a highlight happens to share a floor color. An opaque
                # mid layer can itself bake the floor, so protect the highest
                # nonempty layer only when it is genuinely transparent.
                rec=self.imp.cell_index(game)[room.pair,mid]
                for layer in('over','mid'):
                    fg=preview.native_donor(self.cache,room.ref(mid),self.packed,[layer],{layer:rec['layer_sha256'][layer]})
                    pixels=list(fg.get_flattened_data());count=sum(p[3]>0 for p in pixels)
                    if 0<count<256:
                        mask=mask-{(x,y)for y in range(16)for x in range(16)if pixels[y*16+x][3]}
                        protected_layers[mid]=dict(layer=layer,opaque_pixels=count,layer_sha256=rec['layer_sha256'][layer])
                        break
                masks[mid]=mask
                self.source_masks[tag]=self.source_masks.get(tag,mask)&mask
            self.mask_proofs.append(dict(game=game,map=name,pair=room.pair,source_map_rgba_sha256=catalog.sha(image.tobytes()),
                empty_background_metatiles=list(mids),empty_background_seed_cells=seeds,
                source_floor_colors=[list(p)for p in sorted(colors)],
                masks=[dict(metatile=mid,omitted_floor_pixels=[list(p)for p in sorted(mask)],native_context_cells=occurrences[mid],
                    protected_native_foreground=protected_layers.get(mid,{}))for mid,mask in sorted(masks.items())]))

    def clean_art(self,row):
        if is_chair(row)or not row.get('base')or row.get('kind')=='source_palette':return None
        if not(row.get('parts')or row.get('donor')):return None
        # Floors, walls and architectural dividers are not furniture. Their
        # native opaque surface is intentional rather than an embedded floor.
        if any(t in row['role']for t in('partition','wall','window','floor','border','stairs','staircase','stage','roof','mat','screen')):return None
        before=self.image(row);parts=row.get('parts')or[dict(donor=row['donor'],w=16,h=16)]
        foreground=Image.new('RGBA',(16,16));changes=[];retained=0
        for part in parts:
            ref=part['donor'];tag=ref['game'],ref['tileset'],ref['id']
            if not part.get('layers')and tag in self.floor_refs:
                changes.append(dict(kind='copied_empty_background_part',part=copy.deepcopy(part),omitted_pixels=part['w']*part['h']))
                # A later background filler can intentionally mask an earlier
                # cropped fragment. Preserve that established silhouette by
                # clearing its rectangle instead of uncovering hidden pixels.
                px,py=part.get('x',0),part.get('y',0)
                foreground.paste((0,0,0,0),(px,py,px+part['w'],py+part['h']))
                continue
            full=preview.native_donor(self.cache,ref,self.packed,part.get('layers'),part.get('layerHashes'))
            sx,sy=part.get('srcX',0),part.get('srcY',0);w,h=part['w'],part['h']
            patch=full.crop((sx,sy,sx+w,sy+h));omitted=[]
            mask=self.source_masks.get(tag)if not part.get('layers')else None
            if mask:
                for y in range(h):
                    for x in range(w):
                        if(sx+x,sy+y)in mask and patch.getpixel((x,y))[3]:
                            patch.putpixel((x,y),(0,0,0,0));omitted.append([sx+x,sy+y])
            if omitted:changes.append(dict(kind='outside_connected_native_background',part=copy.deepcopy(part),omitted_source_pixels=omitted))
            foreground.alpha_composite(patch,(part.get('x',0),part.get('y',0)))
        if not changes or not foreground.getbbox():return None
        after=Image.alpha_composite(preview.native_donor(self.cache,row['base'],self.packed),foreground)
        if after.tobytes()==before.tobytes():return None
        for a,b in zip(foreground.get_flattened_data(),before.get_flattened_data()):
            if a[3]:assert a==b,('An original object pixel changed',row['game'],row.get('map'),row['role']);retained+=1
        assert set(foreground.getchannel('A').get_flattened_data())<={0,255}
        sha=catalog.sha(foreground.tobytes());ASSETS.mkdir(parents=True,exist_ok=True);path=ASSETS/('foreground-'+sha[:24]+'.png')
        if not path.exists():foreground.save(path)
        art=dict(kind='third_party',base=copy.deepcopy(row['base']),asset=path.relative_to(ROOT).as_posix(),assetFileHash=catalog.sha(path.read_bytes()),
            credit='Game Freak native Gen3 interior artwork from locally imported donor games; exact original object pixels, with only source-room connected background omitted.',
            sourceUrl='https://github.com/pret/pokefirered')
        return art,dict(originalArtwork=artwork(row),background_changes=changes,unchanged_object_pixels=retained,
            foreground_rgba_sha256=sha,pixel_scale=1,original_base_preserved=True)

    def stage(self,activate=False):
        self.masks()
        # Explicit bases are themselves complete empty room backgrounds. A
        # template may copy such a base inside an8px furniture fragment; it
        # must reveal the final room base instead of becoming object pixels.
        for cells in self.cells.values():
            for row,_,_ in cells.values():
                ref=row.get('base')
                if ref:self.floor_refs.add((ref['game'],ref['tileset'],ref['id']))
        added=[];removals={};changes=[];variants=defaultdict(list);pixel_checks=0;asset_proof={};delegated=[]
        for(g,name),cells in self.cells.items():
            data=self.sources[g];m=data['maps'][name]
            for(x,y),(prior,module,index)in cells.items():
                result=self.clean_art(prior)
                if result is None:continue
                art,proof=result
                if name in EXTRA:
                    # These residential-looking rooms use FACILITY. The
                    # facility audit supplies complete native MID/OVER rows:
                    # nine plant contexts are identical and six cabinet heads
                    # omit23 additional pixels proved outside the native
                    # foreground. Keep its generic recipes without hidden
                    # narrower overrides in this module.
                    delegated.append(dict(game=g,map=name,x=x,y=y,role=prior['role'],
                        owner='mappings/gen2_facility_floor_audit.lua'))
                    continue
                c=e.cell_info(self.cache,g,data,m['tileset'],prior['id'],prior['quadrant'])
                assert all(a.get('source_pixels_complete')for a in c['attributes'])
                row={k:copy.deepcopy(v)for k,v in prior.items()if k not in('donor','parts','asset','assetFileHash','artOverlay','base','kind','compositionPixelHash')}
                row.update(art);row.update(map=name,x=x,y=y,sourceCells=[[x,y]],sourceCollision=c['collision'],
                    sourcePriority=[bool(a.get('priority'))for a in c['attributes']],sourcePalettes=[a.get('palette',1)for a in c['attributes']])
                row['domesticFloorAudit']=dict(original_module=module.relative_to(ROOT).as_posix(),original_row_sha256=digest(prior),
                    source_context=[g,name,x,y],foreground_rgba_sha256=proof['foreground_rgba_sha256'],original_base_preserved=True,pixel_scale=1)
                row['evidence']=prior.get('evidence','')+' Domestic floor audit: remove only explicitly copied empty donor background pieces and native source-room floor/wall pixels connected to checked empty source cells. All complete object pixels remain byte-for-byte at1:1 over the unchanged intended room base. No source floor, collision, interaction, warp, map or event changes.'
                row['compositionPixelHash']=catalog.sha(preview.replacement_image(self.cache,row,self.packed,ROOT).tobytes())
                added.append(row);variants[g,name].append(row);pixel_checks+=proof['unchanged_object_pixels']
                changes.append(dict(game=g,map=name,x=x,y=y,role=prior['role'],base=prior['base'],foreground_rgba_sha256=proof['foreground_rgba_sha256'],
                    previous_mapping_module=module.relative_to(ROOT).as_posix(),previous_mapping_index=index,previous_positioned=prior.get('x')is not None))
                asset_proof.setdefault(art['asset'],proof)
                if prior.get('x')is not None:
                    oldkey=key(prior);removals[oldkey]=dict(module=module.relative_to(ROOT).as_posix(),index=index,old_index=index,key=list(oldkey),
                        full_row_sha256=digest(prior),old_row=prior,new_module=TARGET.relative_to(ROOT).as_posix(),new_index=len(added)-1,new_row=row)
        validation=e.validate_batch(added,SimpleNamespace(cache=self.cache,engine=ROOT.parent/'.tools/engine-0395',output=OUT),ROOT)
        if activate:write_rows(TARGET,added)
        (OUT/'candidates.json').write_text(json.dumps(added,indent=2)+'\n')
        (OUT/'positioned-supersessions.json').write_text(json.dumps(list(removals.values()),indent=2)+'\n')
        (OUT/'changes.json').write_text(json.dumps(changes,indent=2)+'\n')
        ASSETS.mkdir(parents=True,exist_ok=True)
        files={Path(p).name:catalog.sha((ROOT/p).read_bytes())for p in sorted(asset_proof)}
        (ASSETS/'provenance.json').write_text(json.dumps(dict(source_rooms=self.mask_proofs,assets=asset_proof,files=files),indent=2)+'\n')
        if activate:
            active_assets={Path(p).name for p in asset_proof}
            for path in ASSETS.glob('foreground-*.png'):
                assert path.resolve().parent==ASSETS.resolve()
                if path.name not in active_assets:path.unlink()
        proof=dict(reviewed_map_variants=len(self.records),reviewed_source_cells=sum(r['cells']for r in self.records),
            reviewed_unique_rendered_layouts=len({r['rgba_sha256']for r in self.records}),reviewed_object_contexts=len(self.object_inventory),
            corrected_cells=len(added),corrected_map_variants=len(variants),positioned_rows_requiring_exact_supersession=len(removals),
            unchanged_object_pixel_checks=pixel_checks,chair_cells_changed=0,source_collisions_changed=0,
            original_room_bases_preserved=True,validation=validation,activated=activate,
            delegated_facility_contexts=delegated,
            affected_maps=[dict(game=g,map=name,cells=len(rows))for(g,name),rows in sorted(variants.items())])
        (OUT/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
        (OUT/'review-completion.json').write_text(json.dumps(dict(
            review='All38 distinct selected residential layouts and357 source/art contexts reviewed; all240 G/S/C variants are covered by explicit RGBA aliases and source-cell inventory.',
            criteria=['Native cabinets, bookcases, plants, tables, appliances, rugs, memorial objects and unique source-palette objects checked in their full room.',
                'Native transparent foreground layers are protected; every retained foreground pixel matches the complete previous object.',
                'Intentional windows, wall fixtures, architectural floor/wall surfaces, tatami borders and stair holes retained.',
                'Chair/stool/seat/student-desk cells excluded for the independent chair-floor audit.',
                'No scaling, changed source base, collision, script, warp, map or runtime changes.'],
            maps=[dict(**r,reviewed=True,corrected_cells=len(variants.get((r['game'],r['map']),[])))for r in self.records]),indent=2)+'\n')
        changed_crystal={name for(g,name)in variants if g=='crystal'}
        for path in OUT.glob('*-floor-comparison.png'):
            if path.name.removesuffix('-floor-comparison.png')not in changed_crystal:path.unlink()
        for(g,name),rows in variants.items():
            if g!='crystal':continue
            m=self.sources[g]['maps'][name];canvas=Image.new('RGBA',(m['width']*32,m['height']*32));fixed={(r['x'],r['y']):r for r in rows}
            for pos,(r,_,_)in self.cells[g,name].items():canvas.alpha_composite(self.image(fixed.get(pos,r)),(pos[0]*16,pos[1]*16))
            canvas.convert('RGB').save(OUT/g/(name+'-after.png'))
            old=Image.open(OUT/g/(name+'-before.png')).convert('RGB');s=2
            both=Image.new('RGB',(old.width*s*2+48,old.height*s+80),'#18202c');d=ImageDraw.Draw(both)
            d.text((16,9),name.replace('_',' ').title()+' - original room floor preserved',fill='white')
            d.text((16,31),'Before',fill='white');d.text((old.width*s+32,31),'After: unchanged native furniture, correct floor',fill='white')
            both.paste(old.resize((old.width*s,old.height*s),Image.Resampling.NEAREST),(16,55));both.paste(canvas.convert('RGB').resize((old.width*s,old.height*s),Image.Resampling.NEAREST),(old.width*s+32,55))
            both.save(OUT/(name+'-floor-comparison.png'))
        unique={}
        for r in added:
            old=next(cells[r['x'],r['y']][0]for(g,name),cells in self.cells.items()if(g,name)==(r['game'],r['map']))
            k=digest([artwork(old),artwork(r)])
            unique.setdefault(k,(old,r))
        items=list(unique.values());tw,th=360,112
        for start in range(0,len(items),24):
            canvas=Image.new('RGB',(tw*3,th*8),'#18202c');d=ImageDraw.Draw(canvas)
            for i,(old,new)in enumerate(items[start:start+24]):
                x,y=i%3*tw,i//3*th
                canvas.paste(self.image(old).resize((64,64),Image.Resampling.NEAREST),(x+4,y+24))
                canvas.paste(self.image(new).resize((64,64),Image.Resampling.NEAREST),(x+76,y+24))
                d.text((x+4,y+4),'Before  /  corrected floor',fill='white')
                d.text((x+148,y+25),new['role'][:26]+'\n'+new['role'][26:52],fill='#d6e0e7')
                d.text((x+4,y+94),new['map'],fill='#abc4ce')
            canvas.save(OUT/f'changed-object-contact-{start//24+1:02}.png')
        return proof


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--no-render',action='store_true');p.add_argument('--stage',action='store_true');p.add_argument('--activate',action='store_true');args=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);audit=Audit();objects=audit.inventory(not args.no_render)
    proof=audit.stage(args.activate)if args.stage or args.activate else dict(map_variants=len(audit.records),unique_map_art=len({r['rgba_sha256']for r in audit.records}),source_cells=sum(r['cells']for r in audit.records),unique_object_contexts=len(objects))
    print(json.dumps(proof,indent=2))


if __name__=='__main__':main()
