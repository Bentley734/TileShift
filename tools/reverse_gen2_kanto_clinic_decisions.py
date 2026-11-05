"""Freeze reviewed native clinic wall/floor modules in actual full rooms."""
import json
import catalog
from reverse_gen2_kanto_final import Final,DECISIONS

# All are complete ordinary floor, its nine-cell lamp/window brightness patch,
# or the repeatable plain upper/back wall. No table, desk, planter, machine,
# doorway, screen, room corner or staircase enters these finite selections.
FLOORS=(643,649,650,651,657,658,659,665,666,667,675,695,702,703,709,710,719)
WALLS=(644,652)


def main():
 r=Final();r.remaining_inventory();r.stage();d=json.loads(DECISIONS.read_text());records=[]
 owned={(x['game'],'gen2',x['pair'],x['mid'],None)for x in d.get('native_modules',[])if x['feature'].startswith('ordinary_clinic_')}
 wall=r.gb_at('crystal','VIRIDIAN_POKECENTER_1F',3,0)
 for game in r.games:
  floor=r.current[game,'gen2','network',641,None]['donor']
  for mid in FLOORS+WALLS:
   key=game,'gen2','network',mid,None
   if key in r.current or(key in r.rows and key not in owned):continue
   c=r.imp.cell_index(game)['network',mid]
   assert c['layer_sha256']['over']==catalog.sha(bytes(1024))
   usages=r.usage[game,'network',mid]
   assert all('POKEMON_CENTER'in u['map']or'POKECENTER'in u['map']for u in usages if u['count'])
   is_wall=mid in WALLS;staff=mid==643
   feature='ordinary_clinic_back_wall'if is_wall else'ordinary_clinic_staff_floor_shadow'if staff else'ordinary_clinic_floor_and_light_patch'
   selected=r.current[game,'gen2','network',695,None]['donor']if staff else wall if is_wall else floor
   art=r.native(selected,'classic_gen2_complete_'+feature);art['overMask']='0'*256
   records.append(dict(game=game,pair='network',mid=mid,rgba=c['pixel_sha256'],behavior=c['behavior'],layers=c['layer_sha256'],feature=feature,art=art,
    evidence='Complete OneIsland1F and Celadon2F clinic layouts, all ordinary clinic uses and the full network-source atlas were reviewed. '
     +( 'The plain horizontal rear wall has no label, display or functional object; use the complete actual Crystal Viridian clinic wall at1:1, repeating only its ordinary horizontal stripe to the source32px wall height. The curved orange source wall ornament is replaced by the complete plain native wall design. '
       if is_wall else'The whole source cell is ordinary staff-side floor behind the healing/link counter, including a cosmetic wall shadow. Use the independently selected native red/pink staff checker from695, maintaining its distinction from the public pink diamond floor. '
       if staff else'The whole source cell is ordinary tiled clinic floor or its cosmetic nine-cell light/shadow patch. It contains no table frame, machine, chair, door, planter, stair or gameplay marker. Use the same complete original Crystal pink diamond floor selected for641, aligning its16px pattern and removing the mismatched yellow shaded rectangles around clinic furniture. ')
     +'All native source OVER planes are empty; exact source RGBA, every plane hash and original behavior remain independently guarded. Layouts, collisions, scripts, NPCs, warps and actor anchors are unchanged.'))
 d['native_modules']=[x for x in d.get('native_modules',[])if not x['feature'].startswith('ordinary_clinic_')]+records;DECISIONS.write_text(json.dumps(d,indent=2)+'\n')
 print(json.dumps(dict(keys=len(records),cells=sum(sum(u['count']for u in r.usage[x['game'],x['pair'],x['mid']])for x in records))))


if __name__=='__main__':main()
