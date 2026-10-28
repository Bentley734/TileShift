"""Correct checked Gen1 household plants without baking in the donor floor."""
import argparse,copy,json
from types import SimpleNamespace
import catalog,preview,gen2_extended_review as validation
from gen1_family_review import FamilyReview,ROOT
from gen1_native_plant import native_plant_parts
from interior_review import write_rows
from native_room_parts import RoomParts

def main():
 p=argparse.ArgumentParser();p.add_argument('--validate',action='store_true');p.add_argument('--activate',action='store_true');args=p.parse_args();assert not args.activate or args.validate
 f=FamilyReview('native_plant',{'HOUSE','REDS_HOUSE_1','REDS_HOUSE_2'});path=ROOT/'mappings/interiors.lua';rows=preview.read_reviewed(path);changed=[];floor=RoomParts(f.imp,'firered','FR_RIVALS_HOUSE').ref(1)
 for r in rows:
  if r['game']not in('red','blue','yellow')or r['tileset']not in f.tilesets or r.get('role')not in('household_plant_head','household_plant_base'):continue
  r.pop('donor',None);r['kind']='native_composite';r['base']=copy.deepcopy(floor);r['parts']=copy.deepcopy(native_plant_parts(f.imp,top=r['role']=='household_plant_head'))
  r['evidence']='Complete native FireRed16x32 potted plant, independently checked across both actual Gate746 crown and753 pot. The native mid layer retains every leaf, outline and pot pixel while the room backdrop stays on its native under layer. Compose the complete silhouette over this house floor without a donor-floor rectangle. Original plant position, source pixels/flags, interaction, all maps and warps remain unchanged.'
  r['compositionPixelHash']=catalog.sha(preview.replacement_image(f.cache,r,f.packed,ROOT).tobytes());changed.append(r)
 assert len(changed)==258,len(changed)
 proof={'rows':len(changed)}
 if args.validate:proof=validation.validate_batch(changed,SimpleNamespace(cache=f.cache,engine=ROOT.parent/'.tools/engine-0395',output=f.out),ROOT)
 (f.out/'proof.json').write_text(json.dumps(proof,indent=2))
 if args.activate:write_rows(rows,path)
 for game,name in(('red','BLUES_HOUSE'),('red','COPYCATS_HOUSE_2F'),('yellow','REDS_HOUSE_2F')):
  active=[r for pth in(ROOT/'mappings').glob('*.lua')if pth!=path for r in preview.read_reviewed(pth)]+rows
  preview.map_preview(f.cache,f.out,game,name,game+'-'+name,active,f.packed,3,ROOT)
 print(json.dumps(proof))
if __name__=='__main__':main()
