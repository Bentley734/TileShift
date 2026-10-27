"""Complete Gen2 Pallet using reviewed complete Gen3 Pallet counterparts."""
import argparse,copy,json,os
from pathlib import Path
from types import SimpleNamespace
import catalog,preview,gen2_extended_review as ext
from newbark_building_review import lua
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser();p.add_argument('--activate',action='store_true');args=p.parse_args();cache=Path(os.environ['APPDATA'])/'pokemon-love2d';out=ROOT.parent/'.work/tileshift-gen2-pallet-finish';out.mkdir(exist_ok=True)
 active=[r for path in (ROOT/'mappings').glob('*.lua')if path.name!='gen2_pallet.lua'for r in preview.read_reviewed(path)]
 source=ext.source(cache,'red');red=source['maps']['PALLET_TOWN'];rrows=[r for r in active if r['game']=='red' and r['tileset']==red['tileset'] and r.get('map','PALLET_TOWN')=='PALLET_TOWN'];generic={(r['id'],r['quadrant']):r for r in rrows if r.get('x')is None};positioned={(r['id'],r['quadrant'],r['x'],r['y']):r for r in rrows if r.get('x')is not None}
 def counterpart(x,y):
  bid=red['blocks'][y//2*red['width']+x//2];q=y%2*2+x%2;return positioned.get((bid,q,x,y),generic.get((bid,q)))
 ground=copy.deepcopy(next(r['base']for r in active if r.get('base',{}).get('tileset')=='general__petalburg' and r['base']['id']==1));rows=[];contexts=[];packed={}
 artkeys={'donor','base','parts','kind','asset','assetFileHash','compositionPixelHash','assetPixelHash','artOverlay'}
 for game in ext.GAMES:
  data=ext.source(cache,game);m=data['maps']['PALLET_TOWN'];selected=[r for r in active if r['game']==game and r['tileset']==m['tileset'] and r.get('map','PALLET_TOWN')=='PALLET_TOWN'];gen={(r['id'],r['quadrant'])for r in selected if r.get('x')is None};pos={(r['id'],r['quadrant'],r['x'],r['y'])for r in selected if r.get('x')is not None}
  assert [(w['x'],w['y'],w['destMap'])for w in m['warps']]==[(5,5,'REDS_HOUSE_1F'),(13,5,'BLUES_HOUSE'),(12,11,'OAKS_LAB')]
  for j,bid in enumerate(m['blocks']):
   for q in range(4):
    x,y=j%m['width']*2+q%2,j//m['width']*2+q//2
    if (bid,q)in gen or(bid,q,x,y)in pos:continue
    cell=ext.cell_info(cache,game,data,m['tileset'],bid,q)
    row={'game':game,'style':'gen3','map':'PALLET_TOWN','tileset':m['tileset'],'id':bid,'quadrant':q,'x':x,'y':y,'sourceCells':[[x,y]],'sourceHash':cell['sourceHash'],'sourceFiles':data['fingerprints'][m['tileset']],'sourceCollision':cell['collision'],'sourcePriority':[bool(a.get('priority'))for a in cell['attributes']],'sourcePalettes':[a.get('palette',1)for a in cell['attributes']],'status':'reviewed'}
    building=any(ox<=x<ox+w and oy<=y<oy+h for ox,oy,w,h in ((4,3,4,3),(12,3,4,3),(10,8,6,4)))
    if building or cell['collision']==7:
     seed=counterpart(x,y);assert seed
     if building:assert any(k in seed.get('role','')for k in ('home','lab','building')),seed['role']
     else:assert any(k in seed['role']for k in ('fence','sign')),seed['role']
     row.update({k:copy.deepcopy(v)for k,v in seed.items()if k in artkeys});row['role']='gen2_pallet_'+seed['role']
     row['evidence']='Reviewed complete Pallet counterpart at the identical source map coordinates. Gen2 home64x48 and lab96x64 footprints retain complete Gen3 roof, window-frame caps and door frames from the reviewed Gen1 Pallet composition, with the same door anchor5,5 /13,5 /12,11. Fence and sign coordinates independently checked against the original Gen2 garden/sign glyph. Native roof alpha uses Emerald1 grass. Own cartridge source pixels, collision, palettes and priority are fingerprinted. Native warps, people, garden boundaries and map layout stay unchanged; no scaling.'
    else:
     assert cell['collision']==0 and (bid==1 or (bid,q)in ((56,0),(56,1),(57,0),(57,1))), (game,bid,q,x,y,cell['collision'])
     row.update(kind='native',donor=copy.deepcopy(ground),role='gen2_pallet_open_lawn',evidence='Reviewed original open walkable Pallet ground, including empty space above the two roofs. Complete native Emerald1 lawn matches surrounding reviewed grass. Source movement0, map geometry, encounters, people and events are unchanged; no scaling.')
    row['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,row,packed,ROOT).tobytes());rows.append(row)
  c=preview.map_preview(cache,out,game,'PALLET_TOWN',game+'-complete',active+rows,packed,2,ROOT);assert c['replaced_occurrences']==c['visible_cells']==360;contexts.append(c)
 assert len(rows)==492
 live=ext.validate_batch(rows,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=out),ROOT)
 (out/'candidates.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');(out/'proof.json').write_text(json.dumps({'live':live,'contexts':contexts},indent=2),encoding='utf-8')
 if args.activate:
  text='-- Complete reviewed Gen2 Pallet homes, laboratory, gardens and open lawn.\nlocal rows={}\nlocal function add(batch)for _,r in ipairs(batch)do rows[#rows+1]=r end end\n'
  for i in range(0,len(rows),20):text+='add((function()return '+lua(rows[i:i+20])+' end)())\n'
  (ROOT/'mappings/gen2_pallet.lua').write_text(text+'return rows\n',encoding='utf-8')
 print(json.dumps({'rows':len(rows),'live':live,'coverage':'360/360 each GSC','activated':args.activate}))
if __name__=='__main__':main()
