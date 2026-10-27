"""Review the complete Viridian schoolhouse and western cliff silhouettes."""
import argparse,copy,json,os
from pathlib import Path
from types import SimpleNamespace
import catalog,preview,gen2_extended_review as ext,kanto_architecture_review as k
from newbark_building_review import lua
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser();p.add_argument('--activate',action='store_true');args=p.parse_args()
 cache=Path(os.environ['APPDATA'])/'pokemon-love2d';out=ROOT.parent/'.work/tileshift-viridian-finish';out.mkdir(exist_ok=True)
 active=[r for path in (ROOT/'mappings').glob('*.lua') if path.name!='viridian.lua' for r in preview.read_reviewed(path)]
 ground=next(r['base']for r in active if r.get('base',{}).get('tileset')=='general__petalburg' and r['base']['id']==1)
 donor=json.loads((ROOT.parent/'.work/tileshift-catalog/firered.json').read_text(encoding='utf-8'))['cells'];donor={r['mid']:r for r in donor if r['pair']=='pewter_outdoor'}
 modelpath=ROOT.parent/'.work/tileshift-building-kanto';model=json.loads((modelpath/'kanto-building-variants.json').read_text())['templates']['home32']
 (out/'home32-compact-prototype.png').write_bytes((modelpath/'home32-compact-prototype.png').read_bytes())
 instances=[{'game':g,'map':'VIRIDIAN_CITY','template':'home32','rect_cells':[20,14,4,2],'door_map_cell':[21,15],'door_bottom_anchor_px':[24,32],'destination':'VIRIDIAN_SCHOOL_HOUSE'}for g in ('red','blue','yellow')]
 stage=SimpleNamespace(cache=cache,catalog=ROOT.parent/'.work/tileshift-catalog',output=out,approved_candidates=True,write_reviewed=False)
 rows=k.positioned_rows(stage,{'home32':model},instances)
 for row in rows:row['sourceCells']=[[row['x'],row['y']]];row['role']='architecture_viridian_schoolhouse';row['evidence']+=' Complete original schoolhouse exterior; native school destination and original entrance21,15 preserved.'
 # Full cliff tops, east sides and south foot, including the diagonal northeast bend.
 mids={44:[113]*4,41:[113,114,113,114],87:[113,113,121,121],37:[113,114,121,122],63:[105,105,113,113],59:[105,106,113,114]}
 packed={};proof=[]
 for game in ('red','blue','yellow'):
  m,ts,sheet,_=k.source_map(cache,game,'VIRIDIAN_CITY');assert any(w['x']==21 and w['y']==15 and w['destMap']=='VIRIDIAN_SCHOOL_HOUSE'for w in m['warps'])
  cat=json.loads((ROOT.parent/f'.work/tileshift-catalog/{game}.json').read_text(encoding='utf-8'));idx={(r['block_id'],r['quadrant']):r for r in cat['cells'] if r.get('tileset')==m['tileset']};files=next(t['fingerprints']for t in cat['tilesets']if t['tileset']==m['tileset'])
  for pos,bid in enumerate(m['blocks']):
   if bid not in mids:continue
   for q,mid in enumerate(mids[bid]):
    x,y=pos%m['width']*2+q%2,pos//m['width']*2+q//2;source=idx[bid,q];assert not source['warp_tile_present'] and not source['grass_tile_present'];assert source['walkable_tiles']==([False,True,False,False] if (bid,q)==(59,1) else [False]*4)
    r=donor[mid];ref={'game':'firered','tileset':'pewter_outdoor','id':mid,'hash':r['pixel_sha256']}
    row={'game':game,'style':'gen3','map':'VIRIDIAN_CITY','tileset':m['tileset'],'id':bid,'quadrant':q,'x':x,'y':y,'sourceCells':[[x,y]],'sourceHash':source['grayscale_pixel_sha256'],'sourceFiles':files,'role':'viridian_complete_western_cliff','kind':'native_composite','status':'reviewed','base':copy.deepcopy(ground),'parts':[{'donor':ref,'layers':['mid'],'layerHashes':{'mid':r['layer_sha256']['mid']},'srcX':0,'srcY':0,'w':16,'h':16,'x':0,'y':0}],'evidence':'Reviewed complete western Viridian cliff mass in the original map footprint. Full native FR outdoor113 rock top,114 east face,121 south face,122 southeast corner,105 north rim and106 diagonal northeast corner remain unscaled. Original terrain extends beyond the west/north map edge. Southern mass north rim and diagonal northeast bend retain their original directions. Only empty native layer pixels use matching Emerald1 lawn. The diagonal corner retains its original upper-right walkable8px quadrant; all other cliff cells remain blocked. No encounter or warp tile is reclassified, and source geometry/events are unchanged.'}
    row['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,row,packed,ROOT).tobytes());rows.append(row)
  contexts=preview.map_preview(cache,out,game,'VIRIDIAN_CITY',game+'-complete',active+rows,packed,2,ROOT);assert contexts['replaced_occurrences']==contexts['visible_cells']==1440;proof.append(contexts)
 assert len(rows)==396
 live=ext.validate_batch(rows,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=out),ROOT)
 (out/'candidates.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');(out/'proof.json').write_text(json.dumps({'live':live,'contexts':proof},indent=2),encoding='utf-8')
 if args.activate:
  text='-- Reviewed Viridian schoolhouse and complete western cliff silhouettes.\nlocal rows={}\nlocal function add(batch)for _,r in ipairs(batch)do rows[#rows+1]=r end end\n'
  for start in range(0,len(rows),20):text+='add((function()return '+lua(rows[start:start+20])+' end)())\n'
  (ROOT/'mappings/viridian.lua').write_text(text+'return rows\n',encoding='utf-8')
 print(json.dumps({'rows':len(rows),'live':live,'coverage':'1440/1440 each RBY','activated':args.activate}))
if __name__=='__main__':main()
