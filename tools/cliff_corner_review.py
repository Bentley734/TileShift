"""Independently verify complete inward cliff corners and their original source joins."""
import json,os
from pathlib import Path
import catalog,preview,gen2_extended_review as e
ROOT=Path(__file__).resolve().parents[1]
SHAPES={(76,76,76,59):125,(76,76,61,76):123}
def main():
 cache=Path(os.environ['APPDATA'])/'pokemon-love2d';data={g:e.source(cache,g)for g in e.GAMES};rows=preview.read_reviewed(ROOT/'mappings/cianwood.lua');packed={};proof=[]
 for row in rows:
  if row['role']!='cianwood_inward_rock_corner':continue
  game=row['game'];d=data[game];m=d['maps'][row['map']];cell=e.cell_info(cache,game,d,row['tileset'],row['id'],row['quadrant']);want=SHAPES[tuple(cell['tiles'])]
  assert cell['collision']==7 and len(row['parts'])==1
  part=row['parts'][0];assert part['donor']['id']==want;assert (part['srcX'],part['srcY'],part['w'],part['h'],part['x'],part['y'])==(0,0,16,16,0,0)
  native=preview.native_donor(cache,part['donor'],packed,part['layers'],part['layerHashes']);assert native.getchannel('A').getextrema()==(255,255)
  result=preview.replacement_image(cache,row,packed,ROOT);assert native.tobytes()==result.tobytes()
  adjacent={}
  for label,(dx,dy)in {'north':(0,-1),'west':(-1,0),'east':(1,0),'south':(0,1)}.items():
   x,y=row['x']+dx,row['y']+dy
   if 0<=x<m['width']*2 and 0<=y<m['height']*2:
    bid=m['blocks'][y//2*m['width']+x//2];q=y%2*2+x%2;adjacent[label]=e.cell_info(cache,game,d,row['tileset'],bid,q)['tiles']
   else:adjacent[label]='original map boundary'
  proof.append({'game':game,'xy':[row['x'],row['y']],'source_tiles':cell['tiles'],'native_mid':want,'whole_native_pixels':256,'adjacent_source_tiles':adjacent})
 assert len(proof)==16
 output=ROOT.parent/'.work/tileshift-cliff-corner-audit';output.mkdir(exist_ok=True);(output/'complete-inward-corner-proof.json').write_text(json.dumps(proof,indent=2),encoding='utf-8');print(json.dumps({'complete_native_corners':len(proof),'checked_original_pixels':len(proof)*256,'source_blocking_unchanged':True}))
if __name__=='__main__':main()
