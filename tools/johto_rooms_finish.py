"""Complete source-scoped Johto room furnishings with intact native objects."""
import argparse,copy,json,os
from collections import defaultdict,Counter
from pathlib import Path
from types import SimpleNamespace
from PIL import Image
import catalog,preview,gen2_extended_review as e
from interior_review import Imports
from johto_remaining_review import artwork
from center_mart_overhang_review import write_rows
from native_room_parts import RoomParts
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--validate',action='store_true');p.add_argument('--activate',action='store_true');a=p.parse_args();assert not a.activate or a.validate;cache=Path(os.environ['APPDATA'])/'pokemon-love2d';out=ROOT.parent/'.work/tileshift-johto-rooms-finish';out.mkdir(exist_ok=True);imp=Imports(cache,ROOT.parent/'.work/tileshift-catalog');active=[r for f in(ROOT/'mappings').glob('*.lua')if f.name!='johto_rooms_finish.lua'for r in preview.read_reviewed(f)]
 index=imp.cell_index('firered');house=RoomParts(imp,'firered','FR_RIVALS_HOUSE');center=RoomParts(imp,'firered','FR_VIRIDIAN_CITY_POKEMON_CENTER_1F');flowers=RoomParts(imp,'emerald','EM_ROUTE104_PRETTY_PETAL_FLOWER_SHOP')
 def ref(mid,pair='house',game='firered'):return{'game':game,'tileset':pair,'id':mid,'hash':imp.cell_index(game)[pair,mid]['pixel_sha256']}
 floor=ref(1);wall=ref(40);old={r['role']:r for r in active if r['game']=='red'and r['role'].startswith('household_')}
 center_floor=center.ref(641);center_wall=center.ref(center.layout['mids'][10])
 def native(mid,role):return{'kind':'native','donor':ref(mid),'role':role}
 def comp(parts,base=floor,role='johto_house_native_furniture'):return{'kind':'native_composite','base':base,'parts':parts,'role':role}
 def rawpart(mid,sx,sy,w,h,x=0,y=0,pair='house',game='firered',layers=None):
  z={'donor':ref(mid,pair,game),'srcX':sx,'srcY':sy,'w':w,'h':h,'x':x,'y':y}
  if layers:z.update(layers=layers,layerHashes={k:imp.cell_index(game)[pair,mid]['layer_sha256'][k]for k in layers})
  return z
 def book(q):
  col=q%2
  if q<2:return comp([rawpart(43+col,0,11,16,5),rawpart(51+col,0,5,16,11,0,5)],wall,'johto_house_bookcase_'+str(q))
  return comp([rawpart(59+col,0,0,16,16)],floor,'johto_house_bookcase_'+str(q))
 def tv(top):
  if top:return comp([rawpart(45,3,13,10,1,3,12),rawpart(45,2,14,12,1,2,13),rawpart(45,0,15,16,1,0,14),rawpart(53,0,0,16,1,0,15)],wall,'johto_house_complete_tv_head')
  return comp([rawpart(53,0,1,16,15),rawpart(61,0,0,16,1,0,15)],floor,'johto_house_complete_tv_base')
 # The native standing PC has40px of casing. Remove only eight adjacent,
 # byte-identical blank rows; retain its complete bezel, display and keyboard.
 center_image=imp.gba('firered','FR_VIRIDIAN_CITY_POKEMON_CENTER_1F')[0];pc_source=center_image.crop((176,8,192,48));pc_rows=[]
 for sy in range(40):
  if sy and pc_source.crop((0,sy,16,sy+1)).tobytes()==pc_source.crop((0,sy-1,16,sy)).tobytes():continue
  pc_rows.append(sy)
 assert len(pc_rows)==32
 bg=set(center_image.crop((160,8,176,16)).get_flattened_data())|set(preview.native_donor(cache,center_floor,imp.packed).get_flattened_data());outside=set();queue=[]
 for sy in range(40):
  for sx in range(16):
   if(sx in(0,15)or sy in(0,39))and pc_source.getpixel((sx,sy))in bg:outside.add((sx,sy));queue.append((sx,sy))
 for sx,sy in queue:
  for dx,dy in((1,0),(-1,0),(0,1),(0,-1)):
   xx,yy=sx+dx,sy+dy
   if 0<=xx<16 and 0<=yy<40 and(xx,yy)not in outside and pc_source.getpixel((xx,yy))in bg:outside.add((xx,yy));queue.append((xx,yy))
 pc_parts={0:[],1:[]}
 for half in(0,1):
  spans=[]
  for y in range(16):
   sy=pc_rows[half*16+y];x=0
   while x<16:
    if(x,sy)in outside:x+=1;continue
    end=x+1
    while end<16 and(end,sy)not in outside:end+=1
    # Merge adjacent source/target rows before splitting native metatiles.
    prior=next((v for v in reversed(spans)if v['x']==x and v['w']==end-x and v['y']+v['h']==y and v['sy']+v['h']==sy),None)
    if prior:prior['h']+=1
    else:spans.append({'x':x,'w':end-x,'y':y,'sy':sy,'h':1})
    x=end
  for v in spans:pc_parts[half]+=center.rect(176+v['x'],8+v['sy'],v['w'],v['h'],v['x'],v['y'])
  assert len(pc_parts[half])<=16
 (out/'pc-complete-frame-proof.json').write_text(json.dumps({'source_rect':[176,8,16,40],'native_map':center.map,'retained_source_rows':pc_rows,'removed_rows_identical_to_retained_adjacent_row':True,'complete_bezel_display_keyboard_and_foot':True,'native_background_pixels_excluded':len(outside),'parts_each_half':[len(pc_parts[q])for q in(0,1)]},indent=2))
 def pc(half,base):return comp(copy.deepcopy(pc_parts[half]),base,'johto_complete_pc_'+str(half))
 def region_map(base):return comp([rawpart(592,0,10,16,6,0,3,pair='building__brendans_mays_house',game='emerald'),rawpart(597,0,0,16,4,0,9,pair='building__brendans_mays_house',game='emerald')],base,'johto_complete_native_region_map')
 # Every removed bookcase row is plain repeated body, not a cap or shelf.
 for mid in(51,52):
  im=preview.native_donor(cache,ref(mid),imp.packed)
  for y in range(5):assert im.crop((0,y,16,y+1)).tobytes()==im.crop((0,0,16,1)).tobytes()
 tables={(38,39,54,47):0,(39,41,47,57):1,(5,47,60,58):2,(47,21,58,59):3,(50,39,54,47):0,(39,51,47,57):1,(60,58,1,1):2,(58,59,1,1):3}
 books={(50,51,48,49):0,(50,51,14,15):1,(0,14,16,50):2,(11,14,15,30):3}
 def house_art(c,x,y,m,data):
  raw,col=tuple(c['tiles']),c['collision']
  if raw==(1,1,1,1)and col==0:return native(1,'johto_house_plain_floor')
  if raw==(0,0,0,0):return native(40,'johto_house_full_wall')
  if raw==(16,16,16,16):return native(0,'johto_house_black_void')
  if raw in books:return book(books[raw])
  if raw in((14,15,30,31),(14,15,60,59)):
   above=e.cell_info(cache,c['game'],data,m['tileset'],m['blocks'][(y-1)//2*m['width']+x//2],(y-1)%2*2+x%2)
   assert tuple(above['tiles'])in books
   return book(2+books[tuple(above['tiles'])]%2)
  if raw in tables:return artwork(old[('household_table_nw','household_table_ne','household_table_sw','household_table_se')[tables[raw]]])|{'role':'johto_house_complete_table_'+str(tables[raw])}
  if raw==(36,74,52,44):
   r=artwork(old['household_window']);r['parts']=r['parts'][2:];r['parts'].insert(0,rawpart(40,0,0,16,16));r['role']='johto_house_complete_window';return r
  if raw==(45,46,61,62):return region_map(wall)
  if raw in((0,0,6,7),(16,0,0,6)):return tv(True)
  if raw==(22,23,30,31):return tv(False)
  if raw in((0,0,12,13),(28,29,30,31)):
   n=0 if raw[0]==0 else 1;path=ROOT/'assets/original/interior-radio'/('cell-'+str(n)+'.png')
   if not path.exists():return None
   return{'kind':'original','base':wall if n==0 else floor,'asset':path.relative_to(ROOT).as_posix(),'assetFileHash':catalog.sha(path.read_bytes()),'role':'johto_house_radio_'+str(n)}
  if raw in((0,0,64,65),(32,33,66,67)):
   n=0 if raw[0]==0 else 1;return pc(n,wall if n==0 else floor)
  if raw==(2,3,18,19):
   left=True
   if x>0:
    z=e.cell_info(cache,c['game'],data,m['tileset'],m['blocks'][y//2*m['width']+(x-1)//2],y%2*2+(x-1)%2);left=tuple(z['tiles'])not in tables
   r=artwork(old['household_chair_left'if left else'household_chair_right']);r['role']='johto_house_chair_'+('left'if left else'right');return r
  if raw==(4,4,20,20):
   right=False
   if x>0:
    z=e.cell_info(cache,c['game'],data,m['tileset'],m['blocks'][y//2*m['width']+(x-1)//2],y%2*2+(x-1)%2);right=tuple(z['tiles'])==(4,4,20,20)
   r=artwork(old['household_rug_right'if right else'household_rug_left']);r['role']='johto_house_entry_rug';return r
  if raw==(80,81,80,81):return comp([rawpart(19,0,0,16,16)],floor,'johto_house_side_entry_rug')
  if raw in((10,11,8,9),(26,27,24,25)):
   r=artwork(old['household_plant_head'if raw[0]==10 else'household_plant_base']);r['role']='johto_house_native_potted_plant';return r
  if raw==(42,43,94,95):
   path=ROOT/'assets/original/interior-flowerpot/flowerpot.png'
   if not path.exists():return None
   return{'kind':'original','base':floor,'asset':path.relative_to(ROOT).as_posix(),'assetFileHash':catalog.sha(path.read_bytes()),'role':'johto_house_complete_single_flowerpot'}
  if raw in((42,43,84,85),(84,85,94,95)):
   n=0 if raw[0]==42 else 1;return comp(flowers.rect(32,16+n*16,16,16,layers=['mid']),floor,'johto_house_native_potted_flowers')
  return None
 def center_art(c,x,y,m,data):
  raw=tuple(c['tiles'])
  def tile(sx,sy,role):return comp(center.rect(sx,sy,16,16),center_floor,role)
  if raw==(1,1,17,17):return{'kind':'native','donor':center_floor,'role':'johto_center_staff_floor'}
  if raw==(2,2,2,2):return{'kind':'native','donor':center_wall,'role':'johto_center_full_wall'}
  if raw==(4,5,20,21):return pc(0,center_wall)if c['collision']==7 else region_map(center_wall)
  if raw==(10,11,26,27):return pc(1,center_floor)
  if raw==(81,81,80,80):
   previous=False
   if x>0:
    z=e.cell_info(cache,c['game'],data,m['tileset'],m['blocks'][y//2*m['width']+(x-1)//2],y%2*2+(x-1)%2);previous=tuple(z['tiles'])==raw
   r=artwork(old['household_rug_right'if previous else'household_rug_left']);r['base']=center_floor;r['role']='johto_center_entry_rug';return r
  if raw==(72,73,88,89):return tile(176,80,'johto_center_whole_lounge_chair')
  if raw in((2,2,32,33),(48,49,64,65)):return pc(0 if raw[0]==2 else 1,center_wall if raw[0]==2 else center_floor)
  machine={(28,29,44,45):0,(30,31,46,47):1,(60,61,76,77):2,(61,63,78,79):3}
  if raw in machine:
   q=machine[raw];return tile(80+q%2*16,16+q//2*16,'johto_center_whole_healing_machine_'+str(q))
  if raw in((52,52,36,36),(12,12,36,36),(52,12,36,36)):return tile(112,48,'johto_center_nurse_counter')
  if raw==(68,69,84,85):return tile(64,48,'johto_center_counter_left_end')
  if raw==(2,2,2,15):return tile(160,16,'johto_center_counter_right_back')
  if raw==(1,15,3,37):return tile(160,32,'johto_center_counter_right_flower')
  if raw==(19,53,70,71):return tile(160,48,'johto_center_counter_right_front')
  return None
 rows=[];held=[];stats=[]
 for game in e.GAMES:
  data=e.source(cache,game);limit=imp.table(game,'landmarks')['landmarks']['LANDMARK_PALLET_TOWN']['index']
  for name,m in sorted(data['maps'].items()):
   if not isinstance(m,dict)or not 0<m.get('landmark',999)<limit or m['tileset']not in('TILESET_HOUSE','TILESET_POKECENTER'):continue
   selected=[r for r in active if r['game']==game and r['tileset']==m['tileset']and r.get('map',name)==name];generic={(r['id'],r['quadrant'])for r in selected if r.get('x')is None};pos={(r['id'],r['quadrant'],r['x'],r['y'])for r in selected if r.get('x')is not None};added=0
   for y in range(m['height']*2):
    for x in range(m['width']*2):
     b=m['blocks'][y//2*m['width']+x//2];q=y%2*2+x%2
     if(b,q)in generic or(b,q,x,y)in pos:continue
     c=e.cell_info(cache,game,data,m['tileset'],b,q);art=(house_art if m['tileset']=='TILESET_HOUSE'else center_art)(c,x,y,m,data)
     if not art:held.append({'game':game,'map':name,'x':x,'y':y,'raw':c['tiles'],'collision':c['collision']});continue
     r={'game':game,'style':'gen3','map':name,'tileset':m['tileset'],'id':b,'quadrant':q,'x':x,'y':y,'sourceCells':[[x,y]],'sourceHash':c['sourceHash'],'sourceFiles':data['fingerprints'][m['tileset']],'sourceCollision':c['collision'],'sourcePriority':[bool(v.get('priority'))for v in c['attributes']],'sourcePalettes':[v.get('palette',1)for v in c['attributes']],'status':'candidate','evidence':'Johto room function and complete native furniture reviewed in source/native room contexts. Unscaled table, chairs, windows, plant, television casing and shelves retain all unique features. Only five identical blank bookcase-panel rows are omitted; all caps, shelves and foot shadows remain. Original source interactions, NPC positions, warps and collision are unchanged.'};r.update(art);r['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,r,imp.packed,ROOT).tobytes());rows.append(r);added+=1
   stats.append({'game':game,'map':name,'added':added,'total':m['width']*m['height']*4})
 # Stable room-scoped recipes share art; only directional chairs/rugs need positions.
 grouped=defaultdict(list)
 for r in rows:grouped[r['game'],r['map'],r['id'],r['quadrant']].append(r)
 compact=[]
 for group in grouped.values():
  if len({json.dumps(artwork(r),sort_keys=True)for r in group})==1:
   r=group[0];r.pop('x');r.pop('y');r['sourceCells']=[z['sourceCells'][0]for z in group];compact.append(r)
  else:compact.extend(group)
 rows=compact;(out/'candidates.json').write_text(json.dumps(rows,indent=2));(out/'held.json').write_text(json.dumps(held,indent=2));(out/'summary.json').write_text(json.dumps(stats,indent=2))
 for name in('BILLS_FAMILYS_HOUSE','GOLDENROD_FLOWER_SHOP','DAY_CARE','CHARCOAL_KILN','AZALEA_POKECENTER_1F'):
  preview.map_preview(cache,out,'crystal',name,'crystal-'+name,active+rows,imp.packed,3,ROOT)
 print(json.dumps({'rows':len(rows),'held':len(held),'unique_held':list({tuple(z['raw'])for z in held}),'maps':len(stats)}))
 if a.validate:
  assert not held
  for r in rows:r['status']='reviewed'
  proof=e.validate_batch(rows,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=out),ROOT)
  for s in stats:
   report=preview.map_preview(cache,out,s['game'],s['map'],s['game']+'-'+s['map'],active+rows,imp.packed,1,ROOT);assert report['replaced_occurrences']==report['visible_cells']
  (out/'proof.json').write_text(json.dumps(proof,indent=2))
  if a.activate:write_rows(ROOT/'mappings/johto_rooms_finish.lua',rows)
if __name__=='__main__':main()
