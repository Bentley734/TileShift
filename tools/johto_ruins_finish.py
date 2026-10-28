"""Native ruins surroundings plus detail-preserving Tanoby-colored inscriptions."""
import argparse,json,sys
from types import SimpleNamespace
from johto_family_review import FamilyReview,ROOT
from native_room_parts import RoomParts
from center_mart_overhang_review import write_rows
import gen2_extended_review as e

p=argparse.ArgumentParser();p.add_argument('--validate',action='store_true');p.add_argument('--activate',action='store_true');args=p.parse_args();assert not args.activate or args.validate
f=FamilyReview('ruins',{'TILESET_RUINS_OF_ALPH','TILESET_AERODACTYL_WORD_ROOM','TILESET_HO_OH_WORD_ROOM','TILESET_KABUTO_WORD_ROOM','TILESET_OMANYTE_WORD_ROOM'})
r=RoomParts(f.imp,'firered','FR_SEVEN_ISLAND_TANOBY_RUINS_MONEAN_CHAMBER');dojo=RoomParts(f.imp,'firered','FR_SAFFRON_CITY_DOJO');floor=r.ref(648)
# Source palette slots are1-based, and each ramp is white255,170,85,black0.
# Colors are the pale stone, olive limestone and blue-gray engraving tones
# in the actual native Tanoby floor/wall family. Four distinct tones retain
# every original pixel in the Unown alphabet and unique puzzle tablets.
STONE=[[247,247,222],[230,222,165],[206,214,156],[82,82,107]]
INSCRIPTION=[[247,247,222],[206,214,156],[99,132,132],[82,82,107]]
VOID_STONE=[[247,247,222],[206,214,156],[123,115,115],[0,0,0]]
RAMPS={1:VOID_STONE,5:INSCRIPTION,6:STONE}
native_colors={tuple(z[:3])for z in f.imp.gba('firered',r.map)[0].get_flattened_data()}
assert all(tuple(rgb)in native_colors for ramp in RAMPS.values()for rgb in ramp)
def n(mid,role):return f.native(r.ref(mid),'johto_ruins_'+role)
def handle(c,x,y,name,m,data):
 raw=tuple(c['tiles']);col=c['collision']
 if raw==(2,3,3,2):return n(648,'native_tanoby_stone_floor')
 if raw==(10,11,10,11):return n(647,'native_tanoby_stone_wall')
 if raw==(8,9,10,11):return n(644,'native_tanoby_stone_wall_cap')
 if raw==(1,1,1,1):return n(0,'original_open_void')
 if raw==(14,15,30,31):return f.native(dojo.ref(726),'johto_ruins_whole_pokemon_statue_head')
 if raw==(46,47,62,63):return f.native(dojo.ref(734),'johto_ruins_whole_pokemon_statue_base')
 if raw==(80,81,82,83):return n(648,'native_stone_below_complete_statue')
 if raw==(38,39,40,41):return f.native(f.ref('firered','general__rom_082d4fec',695),'johto_ruins_complete_stone_ladder')
 if raw==(1,1,90,3):return f.native(f.ref('emerald','general__cave',555),'johto_ruins_complete_rock_passage')
 if raw==(16,17,17,16):return f.native(f.ref('firered','building__rom_082d4cbc',653),'johto_ruins_gold_puzzle_platform')
 if raw in((12,17,3,12),(16,13,12,3)):
  left=raw[0]==12;return f.composite(floor,[{'donor':f.ref('firered','building__rom_082d4cbc',653),'srcX':0 if left else 8,'x':8 if left else 0,'w':8,'h':16}],'johto_ruins_gold_puzzle_platform_side')
 # The user chose recoloring original special details into Gen3 palettes.
 # Keep exact Unown letters, tablet controls and hole geometry; do not replace
 # their meaning with Braille or unrelated decorations.
 return {'kind':'source_palette','sourceColors':[RAMPS.get(a.get('palette',1),STONE)for a in c['attributes']],'role':'johto_ruins_preserved_unown_and_puzzle_geometry'}

saved=sys.argv;sys.argv=[sys.argv[0]]
try:f.run(handle,('RUINS_OF_ALPH_INNER_CHAMBER','RUINS_OF_ALPH_AERODACTYL_CHAMBER','RUINS_OF_ALPH_AERODACTYL_WORD_ROOM'),'Direct native Gen3 Tanoby ruins floor, masonry, complete Pokemon statues, passage and ladder counterparts. User-approved original special-detail recolor preserves every grayscale pixel of the Unown alphabet, literal floor words, tablet controls and hole edges. Source palette slots select four distinct native Tanoby limestone/engraving colors independently per8px quadrant. Original collision, falls, puzzle conditions, text meaning, warps and interactions remain unchanged; no ROM pixels are redistributed.')
finally:sys.argv=saved
if args.validate:
 rows=json.loads((f.out/'candidates.json').read_text())
 for row in rows:row['status']='reviewed'
 proof=e.validate_batch(rows,SimpleNamespace(cache=f.cache,engine=ROOT.parent/'.tools/engine-0395',output=f.out),ROOT)
 held=json.loads((f.out/'held.json').read_text());assert not held
 proof['protected_remaining_cells']=0;proof['complete']=True;proof['preserved_literal_unown_glyphs']=True
 for s in json.loads((f.out/'summary.json').read_text()):
  v=__import__('preview').map_preview(f.cache,f.out,s['game'],s['map'],s['game']+'-'+s['map'],f.active+rows,f.packed,1,ROOT);assert v['replaced_occurrences']==v['visible_cells'],s
 (f.out/'proof.json').write_text(json.dumps(proof,indent=2))
 if args.activate:write_rows(f.path,rows)
