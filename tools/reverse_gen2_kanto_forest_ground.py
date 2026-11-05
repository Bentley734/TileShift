"""Correct the independently reviewed three BerryForest field/path joins."""
import json
from PIL import Image
import catalog,preview
from reverse_gen2_kanto_final import Final,DECISIONS,OUT,previous


def main():
 r=Final();r.remaining_inventory();r.stage();d=json.loads(DECISIONS.read_text());records=[]
 owned = {
  (entry['game'], 'gen2', entry['pair'], entry['mid'], None)
  for entry in d.get('native_modules', [])
  if entry['feature'] == 'berry_forest_open_path_join'
 }
 for game,pair in(('firered','general__rom_082d5004'),('leafgreen','general__rom_082d4fe4')):
  for mid in(663,667,671):
   c=r.imp.cell_index(game)[pair,mid];key=game,'gen2',pair,mid,None
   art=r.native(r.gb_at('crystal','PALLET_TOWN',2,3),'classic_gen2_complete_berry_forest_open_path_join');art['overMask']='0'*256
   if key in r.rows and key not in owned:
    assert r.render(r.rows[key]).tobytes()==r.render(art).tobytes();continue
   row=dict(game=game,pair=pair,mid=mid,rgba=c['pixel_sha256'],behavior=c['behavior'],layers=c['layer_sha256'],feature='berry_forest_open_path_join',art=art,
    evidence='Actual whole BerryForest layout and the complete source663/667/671 modules were independently reviewed together. These are ordinary pale path/grass joins beside the broadleaf canopy, not rock, mountain or cave banks. '
     'Replace the previously misclassified667 cave-bank graphic with the complete matching native Crystal Kanto open-path material already selected for adjacent forest paths. The same full native16px path keeps its1:1 pixel scale and joins the selected field without a brown cave triangle. '
     'Each exact source RGBA, all native plane hashes and original behavior are pinned; original forest terrain collision, tree positions, NPCs, source maps and scripts remain unchanged.')
   if key in r.current:row['replace_prior_row_sha256']=catalog.sha(previous.stable(r.current[key]).encode())
   records.append(row)
   im=preview.native_donor(r.cache,dict(game=game,tileset=pair,id=mid,hash=c['pixel_sha256']),r.packed)
   im.resize((128,128),Image.Resampling.NEAREST).save(OUT/f'{game}-berry-forest-path-{mid}-source.png')
 d['native_modules']=[x for x in d.get('native_modules',[])if x['feature']!='berry_forest_open_path_join']+records
 DECISIONS.write_text(json.dumps(d,indent=2)+'\n');print('frozen',len(records))


if __name__=='__main__':main()
