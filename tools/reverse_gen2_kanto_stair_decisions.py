"""Freeze the complete actually north/south outdoor stone-flight family."""
import json
import catalog
from reverse_gen2_kanto_final import Final,DECISIONS,OUT


def main():
 r=Final();r.remaining_inventory();r.stage();d=json.loads(DECISIONS.read_text());records=[]
 owned = {
  (entry['game'], 'gen2', entry['pair'], entry['mid'], None)
  for entry in d.get('native_modules', [])
  if entry['feature'] == 'complete_north_south_stone_flight'
 }
 reference=r.gb_ref('crystal','UNION_CAVE_1F',18,3)
 rgba={r.imp.cell_index('firered')['sevii_outdoor',mid]['pixel_sha256']for mid in(137,145)}
 for group in r.remaining:
  for s in group['sources']:
   if s['id']not in(137,145)or s['rgba']not in rgba:continue
   if s['pair'].split('__')[0]not in{'general','pallet_outdoor','viridian_outdoor','pewter_outdoor','sevii_outdoor'}:continue
   key=s['game'],'gen2',s['pair'],s['id'],None
   if key in r.rows and key not in owned:continue
   assert s['layers']['over']==catalog.sha(bytes(1024))
   art=r.native(reference,'classic_gen2_complete_north_south_stone_flight');art['overMask']='0'*256
   records.append(dict(game=s['game'],pair=s['pair'],mid=s['id'],rgba=s['rgba'],behavior=s['behavior'],layers=s['layers'],feature='complete_north_south_stone_flight',art=art,
    evidence='The complete source137/145 flights were reviewed together in actual MtEmber and Sevault Canyon outdoor cliff contexts. Their horizontal tread lines form repeated north/south travel flights, including the source145 cosmetic side shade. '
     'Use the complete original Crystal UNION_CAVE18q3 stone-flight module at1:1, the established same whole native outdoor-flight counterpart used for EverGrande. Every native tread, edge and highlight remains intact; repeated full flight modules fill the unchanged native source flight height. '
     'No rotation, east/west side-entry threshold, warp cap, ladder, cliff face or generic floor is mistaken for a flight. Only this full source artwork in the actual outdoor General family qualifies; each exact target source RGBA, behavior and all layers remain pinned. Source direction, collisions, actor anchors, events and maps are unchanged.'))
 d['native_modules']=[x for x in d.get('native_modules',[])if x['feature']!='complete_north_south_stone_flight']+records
 DECISIONS.write_text(json.dumps(d,indent=2)+'\n')
 print(json.dumps(dict(keys=len(records),cells=sum(sum(u['count']for u in r.usage[x['game'],x['pair'],x['mid']])for x in records))))


if __name__=='__main__':main()
