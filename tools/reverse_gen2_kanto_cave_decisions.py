"""Freeze explicitly reviewed ordinary cave modules, without editing mappings.

The selected native source IDs were viewed in the complete MtMoon1F/B2F
layouts and the full 640..799 cave atlas.  This is a finite feature review,
not an algorithm that guesses cliff direction from collision or luminance.
"""
import json
from reverse_gen2_kanto_final import Final,DECISIONS,previous,catalog

CHOICES={
 'north_raised_plateau_rim':(649,(673,675,676,684,735,746,752,753)),
 'repeated_south_facing_rock_wall':(665,(708,718,740,780,785,788)),
 'west_facing_rock_wall':(656,(707,739,784,781,789)),
 'east_facing_rock_wall':(658,(709,741,742,743,782,790)),
 'plain_raised_rock_top':(657,(706,712,714,744,745)),
 'ordinary_cave_floor_or_sandy_floor_join':(641,(723,724,731,732,755,756,757,760,761,763,765,768,769,770,771,772,773)),
}


def main():
 r=Final();r.remaining_inventory();r.stage();d=json.loads(DECISIONS.read_text());records=[]
 for role,(canonical_mid,mids)in CHOICES.items():
  old=r.current['firered','gen2','general__rom_082d4bfc',canonical_mid,None]
  origin=dict(game='firered',pair='general__rom_082d4bfc',mid=canonical_mid)
  targets=[];selected=[]
  for mid in mids:
   signature=r.source_signature('firered','general__rom_082d4bfc',mid)
   group=next((g for g in r.remaining if g['signature']==signature),None)
   if not group:continue
   for s in group['sources']:
    key=s['game'],'gen2',s['pair'],s['id'],None
    if key in r.rows or key in r.current:continue
    if s['layers']['over']!=catalog.sha(bytes(1024)):continue
    if not all(any(v in u['map']for v in('CAVE','MOON','VICTORY_ROAD','MT_EMBER','TANOBY_KEY'))for u in s['witnesses']):continue
    # All corners/floor joins must meet the already selected ordinary cave floor.
    floor=r.current.get((s['game'],'gen2',s['pair'],641,None))
    ordinary=r.current['firered','gen2','general__rom_082d4bfc',641,None]
    if not floor or r.render(floor).tobytes()!=r.render(ordinary).tobytes():continue
    targets.append(dict(game=s['game'],pair=s['pair'],mid=s['id'],rgba=s['rgba'],behavior=s['behavior'],layers=s['layers']))
    selected.append(dict(game=s['game'],pair=s['pair'],mid=s['id'],count=s['count'],witnesses=s['witnesses']))
  if not targets:continue
  decision=dict(canonical=origin,canonical_row_sha256=catalog.sha(previous.stable(old).encode()),
   semantic_role=role,comparison='reviewed_whole_cave_module',
   review_basis='Whole native MtMoon1F/B2F walls and source atlas reviewed as one connected cave-bank family: '+role+'. '
    'Ordinary upper rims and long west/east/south faces are separate from the walkable cave floor. '
    'Plain sand/stone joins are ordinary nonfunctional walking material; fossil-circle plots, holes, sockets, entrance heads, ladders, water borders and scattered boulder clusters are excluded. '
    'Every target context is a cave in the same explicitly checked selected classic floor; full source RGBA, all layer hashes and original behavior are pinned.',targets=targets)
  d['aliases'].append(decision);records.append(dict(role=role,targets=selected))
 DECISIONS.write_text(json.dumps(d,indent=2)+'\n')
 (r.out/'curated-cave-family-decisions.json').write_text(json.dumps(records,indent=2)+'\n')
 print(json.dumps(dict(groups=len(records),keys=sum(len(x['targets'])for x in records),cells=sum(t['count']for x in records for t in x['targets']))))


if __name__=='__main__':main()
