"""Complete Cianwood's shops, sea barriers and two inward rock corners."""
import argparse,copy,json,os
from pathlib import Path
from types import SimpleNamespace
import catalog,preview,gen2_extended_review as e,kanto_architecture_review as k
from interior_review import Imports
from newbark_building_review import lua
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser();p.add_argument('--activate',action='store_true');args=p.parse_args();cache=Path(os.environ['APPDATA'])/'pokemon-love2d';out=ROOT.parent/'.work/tileshift-cianwood-finish';out.mkdir(exist_ok=True)
 active=[r for path in (ROOT/'mappings').glob('*.lua')if path.name!='cianwood.lua'for r in preview.read_reviewed(path)];im=Imports(cache,ROOT.parent/'.work/tileshift-catalog');packed=im.packed;ground=copy.deepcopy(next(r['base']for r in active if r.get('base',{}).get('tileset')=='general__petalburg'and r['base']['id']==1))
 original=ROOT.parent/'.work/tileshift-building-kanto';model=json.loads((original/'kanto-building-variants.json').read_text())['templates']['home32'];(out/'home32-compact-prototype.png').write_bytes((original/'home32-compact-prototype.png').read_bytes())
 instances=[]
 for game in e.GAMES:
  for rect,dest in (([8,30,4,2],'CIANWOOD_PHOTO_STUDIO'),([14,46,4,2],'CIANWOOD_PHARMACY')):
   instances.append({'game':game,'map':'CIANWOOD_CITY','template':'home32','rect_cells':rect,'door_map_cell':[rect[0]+1,rect[1]+1],'door_bottom_anchor_px':[24,32],'destination':dest})
 stage=SimpleNamespace(cache=cache,catalog=ROOT.parent/'.work/tileshift-catalog',output=out,approved_candidates=True,write_reviewed=False);rows=k.positioned_rows(stage,{'home32':model},instances)
 for row in rows:
  row['sourceCells']=[[row['x'],row['y']]];row['role']='architecture_cianwood_local_shop';row['evidence']+=' Reviewed residence-style local pharmacy/photo studio, without a Pokemon Mart or Center emblem. Both complete64x32 source footprints and their original single entrance anchors remain unchanged.'
 (out/'shop-model.json').write_text(json.dumps({'templates':{'home32':model},'source_instances':instances},indent=2),encoding='utf-8')
 def part(mid,sx=0,sy=0,w=16,h=16,x=0,y=0,game='firered',pair='pewter_outdoor'):
  c=im.cell_index(game)[pair,mid];return {'donor':{'game':game,'tileset':pair,'id':mid,'hash':c['pixel_sha256']},'layers':['mid'],'layerHashes':{'mid':c['layer_sha256']['mid']},'srcX':sx,'srcY':sy,'w':w,'h':h,'x':x,'y':y}
 for game in e.GAMES:
  data=e.source(cache,game);m=data['maps']['CIANWOOD_CITY'];sel=[r for r in active if r['game']==game and r['tileset']==m['tileset']and r.get('map','CIANWOOD_CITY')=='CIANWOOD_CITY'];g={(r['id'],r['quadrant'])for r in sel if r.get('x')is None};p={(r['id'],r['quadrant'],r['x'],r['y'])for r in sel if r.get('x')is not None};ocean=next(r for r in sel if r['role']=='coastal_ocean_water_interior');sea=next(r for r in active if r['game']==game and r.get('map')=='CHERRYGROVE_CITY'and r['role']=='rocky_coast_sea_rock_barrier')
  for j,bid in enumerate(m['blocks']):
   for q in range(4):
    x,y=j%m['width']*2+q%2,j//m['width']*2+q//2
    if (bid,q)in g or(bid,q,x,y)in p or any(ox<=x<ox+4 and oy<=y<oy+2 for ox,oy in ((8,30),(14,46))):continue
    c=e.cell_info(cache,game,data,m['tileset'],bid,q);r={'game':game,'style':'gen3','map':'CIANWOOD_CITY','tileset':m['tileset'],'id':bid,'quadrant':q,'x':x,'y':y,'sourceCells':[[x,y]],'sourceHash':c['sourceHash'],'sourceFiles':data['fingerprints'][m['tileset']],'sourceCollision':c['collision'],'sourcePriority':[bool(z.get('priority'))for z in c['attributes']],'sourcePalettes':[z.get('palette',1)for z in c['attributes']],'kind':'native_composite','status':'reviewed'}
    if c['tiles']==[88]*4:
     assert c['collision']==39;r.update(role='rocky_coast_sea_rock_barrier',base=copy.deepcopy(ocean['donor']),parts=copy.deepcopy(sea['parts']),animated=True,animation=copy.deepcopy(ocean['animation']),sourceOceanBounds=[0,0,29,53],evidence='Reviewed complete permanent16px Cianwood sea-rock barrier: identical source pixels, blocking0x27, palette slots and priority as the approved Cherrygrove barrier. All205 native Emerald404 rock pixels remain unchanged; only51 transparent exterior pixels show the same8-frame animated ocean as the surrounding Cianwood body. No rock is treated as Surf water, and no source boundary, fishing, encounters or event changes.')
    else:
     assert (bid,q,c['tiles'])in ((110,2,[76,76,76,59]),(111,3,[76,76,61,76])) and c['collision']==7
     left=bid==110;parts=[part(125 if left else 123)]
     r.update(role='cianwood_inward_rock_corner',base=copy.deepcopy(ground),parts=parts,evidence='Reviewed inward rock corner at the original8px source boundary: three south-face8px sections meet one directional side section in the lower corner. The full native FR123/125 solid-backed inward turn retains its complete original curve and face. The former hand-joined south-face/side strips left a broken upward join; no fragments are spliced in the corrected corner. All components remain at original scale. Both source cells stay blocked7; no map, collision or event changes.')
    r['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,r,packed,ROOT).tobytes());rows.append(r)
  for x,y,dest in ((9,31,'CIANWOOD_PHOTO_STUDIO'),(15,47,'CIANWOOD_PHARMACY')):assert any(w['x']==x and w['y']==y and w['destMap']==dest for w in m['warps'])
  c=preview.map_preview(cache,out,game,'CIANWOOD_CITY',game+'-complete',active+rows,packed,2,ROOT);assert c['replaced_occurrences']==c['visible_cells']==1620
 counts={g:sum(r['game']==g for r in rows)for g in e.GAMES};assert counts['crystal']==66;print('row counts',counts)
 live=e.validate_batch(rows,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=out),ROOT);(out/'candidates.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');(out/'proof.json').write_text(json.dumps(live,indent=2),encoding='utf-8')
 if args.activate:
  text='-- Reviewed complete Cianwood shops, sea barriers and rock corners.\nlocal rows={}\nlocal function add(batch)for _,r in ipairs(batch)do rows[#rows+1]=r end end\n'
  for i in range(0,len(rows),20):text+='add((function()return '+lua(rows[i:i+20])+' end)())\n'
  (ROOT/'mappings/cianwood.lua').write_text(text+'return rows\n',encoding='utf-8')
 print(json.dumps({'rows':len(rows),'live':live,'coverage':'1620/1620 each GSC','activated':args.activate}))
if __name__=='__main__':main()
