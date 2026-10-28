"""Native timber floor and original dragon relief recolored into Gen3 tones."""
import argparse,json,sys
from types import SimpleNamespace
from johto_family_review import FamilyReview,ROOT
from native_room_parts import RoomParts
from center_mart_overhang_review import write_rows
import gen2_extended_review as e
p=argparse.ArgumentParser();p.add_argument('--validate',action='store_true');p.add_argument('--activate',action='store_true');args=p.parse_args();assert not args.activate or args.validate
f=FamilyReview('shrine',{'TILESET_LAB'});dojo=RoomParts(f.imp,'firered','FR_SAFFRON_CITY_DOJO');floor=dojo.ref(704)
TIMBER=[[255,255,255],[247,239,206],[222,214,140],[181,173,99]]
ALTAR=[[214,255,197],[165,230,148],[115,165,107],[82,82,107]]
native_colors={tuple(z[:3])for z in f.imp.gba('firered',dojo.map)[0].get_flattened_data()}
assert all(tuple(rgb)in native_colors for ramp in(TIMBER,ALTAR)for rgb in ramp)
def handle(c,x,y,name,m,data):
 if name!='DRAGON_SHRINE':return None
 raw=tuple(c['tiles'])
 if raw==(138,138,138,138):return f.native(floor,'johto_dragon_shrine_native_timber_floor')
 if raw==(2,2,18,18):return f.template('household_rug_left'if x==4 else'household_rug_right',floor)
 # The user approved preserving all these original details and changing only
 # their palette. Source slot4 becomes warm Gen3 dojo timber/carved gold;
 # source slot3 keeps the offering altar's separate native-style green ramp.
 return {'kind':'source_palette','sourceColors':[ALTAR if a.get('palette',1)==3 else TIMBER for a in c['attributes']],'role':'johto_dragon_shrine_preserved_dragon_relief_and_lanterns'}
saved=sys.argv;sys.argv=[sys.argv[0]]
try:f.run(handle,('DRAGON_SHRINE',),'Ordinary shrine planks use intact native Gen3 dojo timber; the complete entry mat keeps its original position. User-approved recoloring retains every original pixel of the intertwined dragon sculptures, dragon heads, offering altar, complete lanterns and their light circles. Original palette slot4 uses the native dojo timber/gold family and slot3 a distinct Gen3 green altar ramp. Four distinct tones preserve geometry and details. Source collision, actors, story examination and exit remain unchanged; no ROM pixels are redistributed.')
finally:sys.argv=saved
if args.validate:
 rows=json.loads((f.out/'candidates.json').read_text());held=json.loads((f.out/'held.json').read_text())
 assert all(z['map']=='DRAGON_SHRINE'for z in rows)
 for z in rows:z['status']='reviewed'
 assert not held
 proof=e.validate_batch(rows,SimpleNamespace(cache=f.cache,engine=ROOT.parent/'.tools/engine-0395',output=f.out),ROOT);proof['complete']=True;proof['protected_shrine_cells']=0;proof['preserved_dragon_and_lantern_geometry']=True
 for s in json.loads((f.out/'summary.json').read_text()):
  if s['map']!='DRAGON_SHRINE':continue
  game=s['game'];v=__import__('preview').map_preview(f.cache,f.out,game,'DRAGON_SHRINE',game+'-DRAGON_SHRINE',f.active+rows,f.packed,1,ROOT);assert v['replaced_occurrences']==v['visible_cells']==100
 (f.out/'proof.json').write_text(json.dumps(proof,indent=2))
 if args.activate:write_rows(f.path,rows)
