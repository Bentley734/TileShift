"""Stage native object floor removal using actual source-room floor connectivity."""
import os,json,copy,argparse
from types import SimpleNamespace
from pathlib import Path
from collections import deque
import catalog,preview
import gen2_extended_review as e
from interior_review import Imports
from native_room_parts import RoomParts
from reverse_kanto_review import runs
from center_mart_overhang_review import write_rows
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'.work/tileshift-interior-floor-cleanup';OUT.mkdir(exist_ok=True)
SOURCES={'building__rom_082d4cec':('FR_CELADON_CITY_GAME_CORNER',657),'oak_lab':('FR_OAKS_LAB',649),'building__rom_082d4bcc':('FR_VIRIDIAN_CITY_MART',641),'network':('FR_VIRIDIAN_CITY_POKEMON_CENTER_2F',641),'house':('FR_RIVALS_HOUSE',1)}
WORDS=('chair','seat','studio_table','stock','shelf','bookcase','refrigerator','tv_base','potted','plant','audio_control')
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--activate',action='store_true');args=parser.parse_args()
 cache=Path(os.environ['APPDATA'])/'pokemon-love2d';imp=Imports(cache,ROOT.parent/'.work/tileshift-catalog');source_masks={}
 for pair,(name,floor_mid)in list(SOURCES.items())+[('house-plants',('FR_RIVALS_HOUSE',1))]:
  room=RoomParts(imp,'firered',name);assert room.pair==('house'if pair=='house-plants'else pair)
  image=imp.gba('firered',name)[0];floor=preview.native_donor(cache,room.ref(floor_mid),imp.packed);colors=set(floor.get_flattened_data());
  if pair=='house-plants':colors.update(preview.native_donor(cache,room.ref(40),imp.packed).get_flattened_data())
  if pair=='oak_lab':colors.update(preview.native_donor(cache,room.ref(641),imp.packed).get_flattened_data())
  w,h=image.size;outside=set();queue=deque()
  for index,mid in enumerate(room.layout['mids']):
   if mid!=floor_mid and not(pair=='house-plants'and mid==40):continue
   ox=index%room.layout['width']*16;oy=index//room.layout['width']*16
   for y in range(oy,oy+16):
    for x in range(ox,ox+16):outside.add((x,y));queue.append((x,y))
  while queue:
   x,y=queue.popleft()
   for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
    q=x+dx,y+dy
    if 0<=q[0]<w and 0<=q[1]<h and q not in outside and image.getpixel(q)in colors:outside.add(q);queue.append(q)
  masks={}
  for index,mid in enumerate(room.layout['mids']):
   ox=index%room.layout['width']*16;oy=index//room.layout['width']*16;mask={(x,y)for y in range(16)for x in range(16)if(ox+x,oy+y)in outside}
   masks[mid]=masks.get(mid,mask)&mask
  source_masks[pair]=masks
 files={p:preview.read_reviewed(p)for p in sorted((ROOT/'mappings').glob('*.lua'))};before=[r for rows in files.values()for r in rows];changes=[];maps={g:imp.table(g,'maps')for g in('gold','silver','crystal')}
 for path,rows in files.items():
  for index,row in enumerate(rows):
   if row['game']not in maps or row['style']!='gen3'or row.get('map')=='AZALEA_GYM'or not row.get('base')or not(row.get('parts')or row.get('donor'))or not any(word in row['role']for word in WORDS):continue
   name=row.get('map');definition=maps[row['game']].get(name,{})
   if definition.get('environment')not in('INDOOR','GATE','DUNGEON','CAVE'):continue
   new=copy.deepcopy(row);parts=[];removed=0
   source_parts=row.get('parts')or[{'donor':row['donor'],'w':16,'h':16}]
   if row.get('donor'):new.pop('donor');new['kind']='native_composite'
   if name.startswith(('GOLDENROD_DEPT_STORE_','CELADON_DEPT_STORE_'))and 'stock'in row['role']:
    room=RoomParts(imp,'firered','FR_CELADON_CITY_DEPARTMENT_STORE_1F');new['base']=room.ref(704)
   for part in source_parts:
    # This old bookcase recipe painted a gym-floor patch below the cabinet.
    # It is a background filler, not part of the native cabinet silhouette.
    if 'bookcase' in row['role'] and part['donor']['game']=='firered' and part['donor']['tileset']=='pewter_gym' and part['donor']['id']==715:
     removed+=part['w']*part['h'];continue
    donor=part['donor'];mask=source_masks.get('house-plants'if donor['tileset']=='house'and 'plant'in row['role']else donor['tileset'],{}).get(donor['id'])if donor['game']=='firered'and not part.get('layers')else None
    if mask is None:parts.append(copy.deepcopy(part));continue
    sx,sy=part.get('srcX',0),part.get('srcY',0);x,y=part.get('x',0),part.get('y',0);pw,ph=part['w'],part['h'];keep=[False]*256
    for py in range(ph):
     for px in range(pw):
      if(sx+px,sy+py)in mask:removed+=1
      else:keep[(y+py)*16+x+px]=True
    for span in runs(keep):
     p=copy.deepcopy(part);p.update(srcX=sx+span['x']-x,srcY=sy+span['y']-y,**span);parts.append(p)
   if not parts or len(parts)>16 or(removed==0 and new['base']==row['base']):continue
   new['parts']=parts;new['evidence']+=' Reviewed source-room connected floor pixels are omitted; intact object pixels are drawn above the selected context floor. Enclosed highlights, frames and shadows remain.'
   new_image=preview.replacement_image(cache,new,imp.packed,ROOT)
   if new_image.tobytes()==preview.replacement_image(cache,row,imp.packed,ROOT).tobytes():continue
   new['compositionPixelHash']=catalog.sha(new_image.tobytes());rows[index]=new
   changes.append({'file':path.name,'row':index,'game':row['game'],'map':name,'role':row['role'],'removed_floor_pixels':removed})
 after=[r for rows in files.values()for r in rows]
 (OUT/'changes.json').write_text(json.dumps(changes,indent=2))
 for name in sorted({c['map']for c in changes if c['game']=='crystal'}):
  preview.map_preview(cache,OUT,'crystal',name,name+'-old',before,imp.packed,2,ROOT)
  preview.map_preview(cache,OUT,'crystal',name,name+'-fixed',after,imp.packed,2,ROOT)
 if args.activate:
  changed=[files[ROOT/'mappings'/c['file']][c['row']]for c in changes]
  print(e.validate_batch(changed,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=OUT),ROOT))
  for path,rows in files.items():
   if any(c['file']==path.name for c in changes):write_rows(path,rows)
 print(json.dumps({'changed_rows':len(changes),'maps':len({(c['game'],c['map'])for c in changes}),'roles':sorted({c['role']for c in changes})}))
if __name__=='__main__':main()
