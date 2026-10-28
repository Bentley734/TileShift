"""Battle Tower exterior from intact native Gen3 facade/window modules."""
import argparse,copy,json,sys
from types import SimpleNamespace
from johto_family_review import FamilyReview,ROOT
from native_room_parts import RoomParts
from johto_remaining_review import artwork
from center_mart_overhang_review import write_rows
import catalog,preview,gen2_extended_review as e

p=argparse.ArgumentParser();p.add_argument('--validate',action='store_true');p.add_argument('--activate',action='store_true');args=p.parse_args();assert not args.activate or args.validate
f=FamilyReview('battle_outside',{'TILESET_BATTLE_TOWER_OUTSIDE'});r=RoomParts(f.imp,'emerald','EM_BATTLE_FRONTIER_OUTSIDE_EAST');ground=f.ref('emerald','general__petalburg',1)
# Remove whole repeating brick/pier bays. Every retained angled window is a
# complete32px panel; the center window remains48px and the entrance32px.
#176px artwork extends8px into each neighbouring cell of the160px footprint.
columns=(128,144,176,192,240,256,272,320,336,368,384)
def facade(x,y):
 parts=[]
 for tx in range(16):
  local=x*16+tx-56
  if not 0<=local<176:continue
  sx=columns[local//16]+local%16;sy=y*16+88
  # Coalesce native-contiguous columns before bounded native metatile split.
  if parts and parts[-1]['sx']+parts[-1]['w']==sx and parts[-1]['tx']+parts[-1]['w']==tx:parts[-1]['w']+=1
  else:parts.append({'sx':sx,'tx':tx,'w':1})
 result=[]
 for v in parts:
  # At the foot, the native under plane is ground/entrance paving. Native
  # middle+over planes contain the complete wall/door and real outside alpha.
  result+=r.rect(v['sx'],y*16+88,v['w'],16,v['tx'],0,layers=['mid','over']if y==9 else None)
 assert len(result)<=16
 return f.composite(ground,result,'johto_battle_tower_complete_native_facade')

roof={(z['x']-18,z['y']-28):z for z in f.active if z['game']=='crystal'and z['role']=='olivine_port_closed_front'}
front={(z['x']-8,z['y']):z for z in f.active if z['game']=='crystal'and z['role']=='mahogany_north_gate'}
def handle(c,x,y,name,m,data):
 raw=tuple(c['tiles'])
 if 4<=x<=13 and y<10:return facade(x,y)
 if 7<=x<=10 and 22<=y<=25:
  a=artwork(roof[x-7,y-22]if y<24 else front[x-7,y-24]);a['role']='johto_battle_tower_complete_native_gate';return a
 if raw in((47,47,47,47),(64,64,64,64)):return f.template('goldenrod_brick_road')
 if raw==(90,90,89,89):return f.template('ecruteak_native_metal_fence',ground)
 if raw==(60,60,60,60):return f.native(f.ref('firered','pewter_outdoor',113),'johto_battle_tower_raised_rock_top')
 if raw==(44,44,60,60):return f.native(f.ref('firered','pewter_outdoor',105),'johto_battle_tower_raised_rock_north_rim')
 if raw==(45,60,61,45):return f.template('violet_whole_raised_ground',ground)
 if raw in((0,0,0,0),(0,0,6,6),(0,0,6,0)):return f.native(ground,'johto_battle_tower_ground')
 return None

saved=sys.argv;sys.argv=[sys.argv[0]]
try:f.run(handle,('BATTLE_TOWER_OUTSIDE',),'Complete native Emerald Battle Tower window and wall modules, rearranged at1:1 pixel size. Full32px angled windows,48px center glazing and32px door remain intact; the facade uses176px width with8px transparent decorative side extensions. Repeating structural bays are omitted whole; no image scaling or feature clipping. Top continues naturally beyond the original map border. Source entrance8/9,9, map, collisions and events remain unchanged. Lower gate uses complete previously reviewed native64x64 roof/front modules.')
finally:sys.argv=saved
rows=json.loads((f.out/'candidates.json').read_text());held=json.loads((f.out/'held.json').read_text());sides=[]
data=e.source(f.cache,'crystal');m=data['maps']['BATTLE_TOWER_OUTSIDE'];assert any(w['x']==8 and w['y']==9 and w['destMap']=='BATTLE_TOWER_1F'for w in m['warps'])
for x,side in((3,'left'),(14,'right')):
 for y in range(10):
  bid=m['blocks'][y//2*m['width']+x//2];q=y%2*2+x%2;c=e.cell_info(f.cache,'crystal',data,m['tileset'],bid,q)
  z={'game':'crystal','style':'gen3','map':'BATTLE_TOWER_OUTSIDE','tileset':m['tileset'],'id':bid,'quadrant':q,'x':x,'y':y,'sourceX':x,'sourceCells':[[x,y]],'buildingX':4,'buildingY':0,'buildingW':10,'buildingH':10,'side':side,'sourceHash':c['sourceHash'],'sourceFiles':data['fingerprints'][m['tileset']],'sourceCollision':c['collision'],'sourcePriority':[bool(a.get('priority'))for a in c['attributes']],'sourcePalettes':[a.get('palette',1)for a in c['attributes']],'status':'reviewed','evidence':'Only8px of this adjacent side cell contain the unscaled native Battle Tower facade. Remaining pixels are transparent; original selected trees/ground, actor pixels, map geometry and collision remain underneath unchanged.'};z.update(facade(x,y));z.pop('base',None);z['role']='battle_tower_partial_side';sides.append(z)
prior=preview.read_reviewed(ROOT/'lib/side_catalog.lua');prior=[z for z in prior if z['role']!='battle_tower_partial_side'];other_roofs=[z for path in('roof_catalog.lua','center_mart_roofs.lua','goldenrod_roofs.lua','pallet_roofs.lua','johto_roofs.lua')for z in preview.read_reviewed(ROOT/'lib'/path)]
preview.map_preview(f.cache,f.out,'crystal','BATTLE_TOWER_OUTSIDE','crystal-complete',f.active+rows,f.packed,2,ROOT,roof_rows=other_roofs+prior+sides)
(f.out/'side-candidates.json').write_text(json.dumps(sides,indent=2))
if args.validate:
 assert not held
 for z in rows:z['status']='reviewed'
 proof=e.validate_batch(rows+sides,SimpleNamespace(cache=f.cache,engine=ROOT.parent/'.tools/engine-0395',output=f.out),ROOT);proof.update(source_footprint=[4,0,10,10],artwork_pixels=[176,160],entrance=[8,9],side_alpha_pixels=8)
 (f.out/'proof.json').write_text(json.dumps(proof,indent=2))
 if args.activate:write_rows(f.path,rows);write_rows(ROOT/'lib/side_catalog.lua',prior+sides)
