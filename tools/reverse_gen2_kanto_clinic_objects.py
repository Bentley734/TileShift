"""Complete native Crystal clinic hardware/furniture, independently scoped FR/LG."""
import copy,json
from PIL import Image
import catalog,preview
from reverse_gen2_kanto_final import Final,DECISIONS,OUT
from reverse_gen2_hoenn_interior_finish import Review as NativeObjects


class Objects(Final):
 neutral=NativeObjects.neutral
 prepare_art=NativeObjects.prepare_art
 object_family=NativeObjects.object_family
 def add(self,game,pair,mid,art,evidence):
  c=self.imp.cell_index(game)[pair,mid]
  assert pair=='network'and(game,pair,mid)in self.usage
  assert all('POKECENTER'in u['map']or'POKEMON_CENTER'in u['map']for u in self.usage[game,pair,mid]if u['count'])
  self.frozen.append(dict(game=game,pair=pair,mid=mid,rgba=c['pixel_sha256'],behavior=c['behavior'],layers=c['layer_sha256'],art=art,
   feature=self.feature,source_family=self.family,whole_source_rgba_sha256=self.whole_source_hash,
   evidence=evidence+' The complete actual FireRed and LeafGreen source family '+str(self.family)+' is independently fingerprinted with all source planes and original behavior. '
    'The same existing native public pink diamond floor, separate staff red/pink checker and horizontal clinic wall remain behind the appropriate object. Original complete source anchors, facing, collision, NPCs, scripts, labels and interactions stay unchanged.'))
 def family_source(self,game,layout,label):
  whole=Image.new('RGBA',(len(layout[0])*16,len(layout)*16))
  for y,row in enumerate(layout):
   for x,mid in enumerate(row):
    c=self.imp.cell_index(game)['network',mid]
    im=preview.native_donor(self.cache,dict(game=game,tileset='network',id=mid,hash=c['pixel_sha256']),self.packed);whole.paste(im,(x*16,y*16))
  whole.resize((whole.width*6,whole.height*6),Image.Resampling.NEAREST).save(OUT/f'{game}-clinic-{label}-source-whole.png')
  self.whole_source_hash=catalog.sha(whole.tobytes());self.family=layout;self.feature=label


def main():
 r=Objects();r.contracts=[];r.frozen=[]
 clinic=r.gb_ref('crystal','CHERRYGROVE_POKECENTER_1F',4,0)
 house=r.gb_ref('crystal','GUIDE_GENTS_HOUSE',15,0)
 wall=r.gb_at('crystal','AZALEA_POKECENTER_1F',3,0)
 staff=r.gb_at('crystal','AZALEA_POKECENTER_1F',3,1)
 palettes=preview.palette_set(r.imp.table('crystal','palettes'),r.imp.table('crystal','maps')['AZALEA_POKECENTER_1F'],'DAY')
 for game in r.games:
  layout=[[682,683],[690,691]];r.family_source(game,layout,'healing-machine')
  r.object_family('network',layout,'AZALEA_POKECENTER_1F',(0,0),clinic,[wall,staff],
   'complete Kanto clinic healing machine',source_bounds=[0,0,32,32],foot_anchor=31,only_game=game)
  layout=[[98],[661]];r.family_source(game,layout,'public-computer')
  r.object_family('network',layout,'CHERRYGROVE_POKECENTER_1F',(9,0),wall,staff,
   'complete Kanto clinic computer',row_pixels=list(range(8,32))+[None]*8,preserve_rects=[(0,0,16,24)],
   background_bands=[(0,24,wall),(24,32,staff)],source_bounds=[0,0,16,24],foot_anchor=23,only_game=game)
  layout=[[668,669],[676,677]];r.family_source(game,layout,'coffee-table')
  r.object_family('network',layout,'GUIDE_GENTS_HOUSE',(3,3),house,clinic,
   'complete Kanto clinic coffee table',source_bounds=[0,0,32,32],foot_anchor=31,only_game=game)
  for mid,variant in((757,'gold-padded-seat'),(765,'blue-padded-seat')):
   r.family_source(game,[[mid]],variant)
   r.object_family('network',[[mid]],'CHERRYGROVE_POKECENTER_1F',(7,5),house,clinic,
    'complete Kanto clinic '+variant,source_bounds=[0,0,16,16],foot_anchor=15,only_game=game,
    donor_palettes=[copy.deepcopy(palettes[3])for _ in range(8)]if mid==765 else None)
 d = json.loads(DECISIONS.read_text())
 d['native_objects'] = [
  entry for entry in d.get('native_objects', []) if entry['pair'] != 'network'
 ] + r.frozen
 DECISIONS.write_text(json.dumps(d,indent=2)+'\n')
 (OUT/'native-clinic-object-contracts.json').write_text(json.dumps(r.contracts,indent=2)+'\n')
 print(json.dumps(dict(rows=len(r.frozen),cells=sum(sum(u['count']for u in r.usage[x['game'],x['pair'],x['mid']])for x in r.frozen))))


if __name__=='__main__':main()
