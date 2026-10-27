"""Report Johto-only coverage using each cartridge's native landmark region boundary."""
import argparse,json,os
from pathlib import Path
import catalog
from validate_gpu import runtime_fingerprint
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--report',type=Path,default=ROOT.parent/'.work/tileshift-runtime-coverage/report.json');p.add_argument('--output',type=Path,default=ROOT.parent/'.work/tileshift-johto-progress.json');args=p.parse_args();audit=json.loads(args.report.read_text(encoding='utf-8'));assert audit['status']=='passed'and audit['runtime_inputs']==runtime_fingerprint(ROOT),'Use the current validated all-map report';cache=Path(os.environ['APPDATA'])/'pokemon-love2d';report={'region_rule':'Native Gen2 World:region; before Pallet landmark index, plus Fast Ship','games':{},'remaining_towns':[],'remaining_maps':[]}
 for game in ('gold','silver','crystal'):
  maps=catalog.read_lua(cache/game/'data/generated/maps.lua');landmarks=catalog.read_lua(cache/game/'data/generated/landmarks.lua')['landmarks'];boundary=landmarks['LANDMARK_PALLET_TOWN']['index'];ship=landmarks['LANDMARK_FAST_SHIP']['index'];stats={'maps':0,'complete_maps':0,'source_cells':0,'replaced_cells':0,'remaining_cells':0,'complete_towns':[]}
  for row in audit['maps']:
   if row['game']!=game:continue
   m=maps[row['map']];landmark=m.get('landmark',0)
   if isinstance(landmark,str):landmark=landmarks[landmark]['index']
   if not(landmark<boundary or landmark==ship):continue
   stats['maps']+=1
   for key in ('source_cells','replaced_cells','remaining_cells'):stats[key]+=row[key]
   if row['remaining_cells']==0:
    stats['complete_maps']+=1
    if m.get('environment')=='TOWN':stats['complete_towns'].append(row['map'])
   else:
    record={k:row[k]for k in ('game','map','source_cells','replaced_cells','remaining_cells','tileset')};record['environment']=m.get('environment');report['remaining_maps'].append(record)
    if m.get('environment')=='TOWN':report['remaining_towns'].append(record)
  stats['fraction']=stats['replaced_cells']/stats['source_cells'];report['games'][game]=stats
 args.output.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps({'games':report['games'],'remaining_crystal_towns':[r for r in report['remaining_towns']if r['game']=='crystal']},indent=2))
if __name__=='__main__':main()
