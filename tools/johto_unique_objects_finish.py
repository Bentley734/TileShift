"""Recolor original transport and studio pixels at the user's direction."""
import ast
from pathlib import Path
from johto_family_review import FamilyReview
f=FamilyReview('unique_objects',{'TILESET_TRAIN_STATION','TILESET_RADIO_TOWER','TILESET_PORT'})
# RGB8 colors sampled from the checked native FireRed control-panel/dock
# palettes and Emerald's animated ocean palette. No imported pixels bundled.
METAL=[[255,255,255],[197,189,214],[123,123,123],[82,82,107]]
HULL=[[255,255,255],[222,230,230],[173,189,206],[82,82,107]]
GOLD=[[255,206,90],[230,140,99],[165,156,165],[82,82,107]]
OCEAN=[[107,132,214],[82,107,214],[58,82,156],[41,66,140]]
WOOD=[[222,214,140],[181,173,99],[123,123,123],[82,82,107]]
def literal_shapes(filename,variable):
 for node in ast.parse(Path(__file__).with_name(filename).read_text()).body:
  if isinstance(node,ast.Assign)and any(isinstance(t,ast.Name)and t.id==variable for t in node.targets):return set(ast.literal_eval(node.value))
 raise AssertionError('Explicit reviewed shape list missing')
SHAPES={'TILESET_TRAIN_STATION':literal_shapes('johto_station_finish.py','train'),'TILESET_PORT':literal_shapes('johto_port_finish.py','ship'),'TILESET_RADIO_TOWER':{(32,33,37,38),(53,54,8,25),(78,79,94,95)}}
def handle(c,x,y,name,m,data):
 ts=c['tileset'];colors=[]
 if tuple(c['tiles'])not in SHAPES[ts]:return None
 for attr in c['attributes']:
  slot=attr.get('palette',1)
  if ts=='TILESET_TRAIN_STATION':pal=GOLD if slot==5 else METAL
  elif ts=='TILESET_PORT':pal=OCEAN if slot==4 else GOLD if slot==2 else HULL
  else:pal=METAL if slot==7 else WOOD
  colors.append(pal)
 return {'kind':'source_palette','sourceColors':colors,'role':'johto_recolored_'+('magnet_train'if ts=='TILESET_TRAIN_STATION'else'fast_ship'if ts=='TILESET_PORT'else'studio_microphone_score')}
f.run(handle,('GOLDENROD_MAGNET_TRAIN_STATION','RADIO_TOWER_5F','OLIVINE_PORT'),'The user explicitly chose recoloring the original unmatched pixel art to fit Gen3 while retaining every detail. Exact original geometry, four-shade indices, per8px-quadrant palette separation and source priority remain unchanged; only checked RGB8 color choices change during cached map construction. Magnet Train, Fast Ship, studio microphones/score sheets retain their complete original shape, text, boarding/transport and radio events. No resizing, generated reconstruction, imported PNG redistribution or per-frame pixel work.')
