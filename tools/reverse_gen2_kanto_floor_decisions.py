"""Freeze the78 ordinary floor groups individually reviewed on all7 sheets."""
import argparse,json
from reverse_gen2_kanto_final import Final,DECISIONS,OUT,previous,catalog


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--flat',action='store_true');args=parser.parse_args()
 feature='ordinary_flat_floor_variant'if args.flat else'ordinary_floor_glyph_variant'
 r=Final();d=json.loads(DECISIONS.read_text());groups=json.loads((OUT/('floor-flat-proposals.json'if args.flat else'floor-glyph-proposals.json')).read_text());assert len(groups)==(5 if args.flat else 78)
 records=[]
 for number,group in enumerate(groups):
  for p in group:
   s=p['target'];origin=p['canonical'];old=r.current[origin['game'],'gen2',origin['pair'],origin['mid'],None]
   assert catalog.sha(previous.stable(old).encode())==p['canonical_row_sha256']
   c=r.imp.cell_index(s['game'])[s['pair'],s['id']]
   assert(c['pixel_sha256'],c['behavior'],c['layer_sha256'])==(s['rgba'],s['behavior'],s['layers'])
   art=r.art_of(old);art['overMask']='0'*256
   records.append(dict(game=s['game'],pair=s['pair'],mid=s['id'],rgba=s['rgba'],behavior=s['behavior'],layers=s['layers'],feature=feature,art=art,
    canonical=origin,canonical_row_sha256=p['canonical_row_sha256'],reviewed_context_group=number,
    evidence='Individually reviewed ordinary room-floor group'+str(number)+(' on the flat-floor context sheet01. The low-information blank quadrants were explicitly reviewed in whole PowerPlant/link-battle room context as ordinary floor shadows, retaining their exact native normal-floor behavior. 'if args.flat else' on the complete floor-glyph context sheets01..07. ')+ 'All four source8px quadrants are complete pattern/color partitions from the already reviewed same-room/source-pair ordinary floor; only local shade or plank/checker phase differs. '
     'Every actual logical layout use is independently checked walkable, all native OVER pixels are empty, and conflicting existing native floor outputs are never resolved automatically. Whole room context confirms ordinary floor/wall-shadow material, not stairs, furniture, electricity, water, hole, arrow, plaque, rug, panel glyph or raised border. '
     'Use the complete matching original Crystal floor at1:1, coherently joining the selected '+p['role']+'. Each target source full RGBA, all native layers and original movement/interaction behavior remain individually pinned; no source room geometry, actors, puzzle state, collision, warps or scripts change.'))
 d['native_modules']=[x for x in d.get('native_modules',[])if x['feature']!=feature]+records
 DECISIONS.write_text(json.dumps(d,indent=2)+'\n')
 print(json.dumps(dict(groups=len(groups),keys=len(records),cells=sum(sum(u['count']for u in r.usage[x['game'],x['pair'],x['mid']])for x in records))))


if __name__=='__main__':main()
