"""Review complete Mahogany exteriors with source geometry and native Gen3 features."""
import argparse,copy,json,os
from pathlib import Path
from types import SimpleNamespace
from PIL import Image
import catalog,preview,gen2_extended_review as e,architecture_review as a,kanto_architecture_review as k
from newbark_building_review import CONFIGS,native_reference,lua
from interior_review import Imports
from building_review import decode_layout
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser();p.add_argument('--activate',action='store_true');args=p.parse_args();cache=Path(os.environ['APPDATA'])/'pokemon-love2d';out=ROOT.parent/'.work/tileshift-mahogany-finish';out.mkdir(exist_ok=True)
 active=[r for path in (ROOT/'mappings').glob('*.lua')if path.name!='mahogany.lua'for r in preview.read_reviewed(path)];im=Imports(cache,ROOT.parent/'.work/tileshift-catalog');ground=copy.deepcopy(next(r['base']for r in active if r.get('base',{}).get('tileset')=='general__petalburg'and r['base']['id']==1));packed=im.packed
 stage=SimpleNamespace(cache=cache,catalog=ROOT.parent/'.work/tileshift-catalog',output=out,approved_candidates=True,write_reviewed=False)
 cfg=copy.deepcopy(CONFIGS['ordinary']);cfg.update(size=(64,64),rows=tuple(range(8)),roof_rows=6,anchor=(24,64));cfg['features']=tuple((label,src,(dst[0],dst[1]+32,dst[2],dst[3]))for label,src,dst in cfg['features']);cfg['notes']='Complete native FR residence-style shop exterior, with single original entrance. Width compacted by removing plain spacing and the complete chimney; full height, window and entrance frames retained. This disguised shop keeps MAHOGANY_MART_1F and Rocket story behavior, without a Pokemon Mart sign.'
 # Source column8 includes the removed chimney's yellow right-hand jamb.
 # Use a whole plain roof panel there, and native alpha for both top rows.
 # The facade cap row uses facade columns so every window/door stays intact.
 cfg.update(roof_columns=(0,1,2,3,4,4,4,9),force_over_rows=(0,1),
            row_columns={5:cfg['facade_columns']})
 cfg['notes']+=' Chimney-free roof panels replace the stray yellow chimney jamb; both upper roof rows retain native exterior alpha, revealing the selected scenery beneath the roof corners.'
 original,native=native_reference(stage,'shop64',cfg,packed);target,model=a.compose(stage,'shop64',cfg,original,native,preview.native_donor(cache,ground,packed),ground,packed)
 records=[{'game':g,'map':'MAHOGANY_TOWN','template':'shop64','rect_cells':[10,4,4,4],'door_map_cell':[11,7],'door_bottom_anchor_px':[24,64],'destination':'MAHOGANY_MART_1F'}for g in e.GAMES]
 rows=k.positioned_rows(stage,{'shop64':model},records)
 for row in rows:row['sourceCells']=[[row['x'],row['y']]]
 (out/'shop-model.json').write_text(json.dumps({'templates':{'shop64':model},'source_instances':records},indent=2),encoding='utf-8')
 spec=im.table('firered','gba/native/manifest')['layouts']['FR_ROUTE_15'];layout=decode_layout(cache/'firered/data/generated/gba/native'/spec['file']);ordinary=json.loads((ROOT.parent/'.work/tileshift-building-kanto/kanto-building-variants.json').read_text())['templates']['home32']
 def part(mid,sx=0,sy=0,w=16,h=16,x=0,y=0,pair='pewter_outdoor',layers=('mid',)):
  c=im.cell_index('firered')[pair,mid];return {'donor':{'game':'firered','tileset':pair,'id':mid,'hash':c['pixel_sha256']},'layers':list(layers),'layerHashes':{n:c['layer_sha256'][n]for n in layers},'srcX':sx,'srcY':sy,'w':w,'h':h,'x':x,'y':y}
 def gatepart(x,y):return part(layout['mids'][y*layout['width']+x],pair=spec['pair'],layers=('mid','over'))
 for game in e.GAMES:
  data=e.source(cache,game);m=data['maps']['MAHOGANY_TOWN'];selected=[r for r in active if r['game']==game and r['tileset']==m['tileset']and r.get('map','MAHOGANY_TOWN')=='MAHOGANY_TOWN'];gen={(r['id'],r['quadrant'])for r in selected if r.get('x')is None};pos={(r['id'],r['quadrant'],r['x'],r['y'])for r in selected if r.get('x')is not None};known={}
  for r in active:
   if r['game']==game and r['tileset']in e.SETS and any(w in r['role']for w in ('raised_rock','half_rock','whole_raised_ground','paved_rock_front')):
    known.setdefault(e.identity(e.cell_info(cache,game,data,r['tileset'],r['id'],r['quadrant'])),r)
  for j,bid in enumerate(m['blocks']):
   for q in range(4):
    x,y=j%m['width']*2+q%2,j//m['width']*2+q//2
    if (bid,q)in gen or(bid,q,x,y)in pos or(10<=x<=13 and 4<=y<=7):continue
    c=e.cell_info(cache,game,data,m['tileset'],bid,q);row={'game':game,'style':'gen3','map':'MAHOGANY_TOWN','tileset':m['tileset'],'id':bid,'quadrant':q,'x':x,'y':y,'sourceCells':[[x,y]],'sourceHash':c['sourceHash'],'sourceFiles':data['fingerprints'][m['tileset']],'sourceCollision':c['collision'],'sourcePriority':[bool(z.get('priority'))for z in c['attributes']],'sourcePalettes':[z.get('palette',1)for z in c['attributes']],'status':'reviewed','base':copy.deepcopy(ground),'kind':'native_composite'}
    if 8<=x<=11 and y<=1:
     assert bid in (22,30);tx=x-8;ty=y;parts=[gatepart((10,11,14,15)[tx],11+ty)]
     # Complete16x17 native single doorway; upper cap is included at target y15.
     for old in ordinary['parts']:
      ox,oy=old['target_xy'];ix=max(ox,16);iy=max(oy,15);ex=min(ox+old['w'],32);ey=min(oy+old['h'],32)
      cx,cy=tx*16,ty*16;ix=max(ix,cx);iy=max(iy,cy);ex=min(ex,cx+16);ey=min(ey,cy+16)
      if ix<ex and iy<ey:
       v={z:copy.deepcopy(old[z])for z in ('donor','srcX','srcY','w','h')};v.update(srcX=old['srcX']+ix-ox,srcY=old['srcY']+iy-oy,w=ex-ix,h=ey-iy,x=ix-cx,y=iy-cy)
       for z in ('layers','layerHashes'):
        if z in old:v[z]=copy.deepcopy(old[z])
       parts.append(v)
     row.update(parts=parts,role='mahogany_north_gate',evidence='Reviewed north gate facade in its original visible4x2 footprint; roof continues beyond the north map edge. Native FRRoute15 complete left/right facade edges, glass and brick sections use only unscaled whole16px cells. Complete native16x17 single doorway, including its top frame cap, matches the original gate entrance9,1 and ROUTE_43_MAHOGANY_GATE. No source warp or collision changes.')
    else:
     seed=known.get(e.identity(c))
     if seed:
      for key in ('donor','parts','kind'):
       if key in seed:row[key]=copy.deepcopy(seed[key])
      row['role']='mahogany_'+seed['role'];row['evidence']='Reviewed Mahogany raised terrain: identical complete source pixels, collision, palette slots and priority as the approved '+seed['role']+'. Complete native rock top, directional side and base components retained with matching Emerald1 lawn. Source north walls are not jump ledges. Exact position and original terrain adjacency checked; maps, warps and events unchanged.'
     elif (bid,q)==(106,0):row.update(parts=[part(104)],role='mahogany_northwest_rock_corner',evidence='Reviewed full native FR104 northwest diagonal rock corner at original18,10; complete original curve connects its north rim to west face. No scaling or source mechanic changes.')
     elif (bid,q)in ((82,0),(82,2)):
      assert c['tiles']==([59,5,59,5]if q==0 else[59,5,75,76])
      parts=[part(112 if q==0 else 120,w=8)]
      if q==2:
       seed=next(v for v in known.values()if 'half_rock' in v['role']);assert len(seed['parts'])==2
       for old in seed['parts']:
        v=copy.deepcopy(old);v.update(srcX=old['srcX']+8,w=8,x=8);parts.append(v)
      row.update(parts=parts,role='mahogany_short_retaining_wall',evidence='Reviewed original8px-wide west retaining-wall strip, upper vertical and southwest corner. Native FR112/120 outer8px side/base profile is kept at original scale; the adjoining complete8px straight front band uses the reviewed top/base strips from FR121. Empty space remains native Emerald1 lawn. Original blocking7 and directional neighboring movement unchanged.')
     else:raise AssertionError((game,bid,q,x,y,c['tiles']))
    row['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,row,packed,ROOT).tobytes());rows.append(row)
  assert any(w['x']==9 and w['y']==1 and w['destMap']=='ROUTE_43_MAHOGANY_GATE'for w in m['warps'])
  c=preview.map_preview(cache,out,game,'MAHOGANY_TOWN',game+'-complete',active+rows,packed,2,ROOT);assert c['replaced_occurrences']==c['visible_cells']==360
 assert len(rows)==435
 live=e.validate_batch(rows,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=out),ROOT);(out/'candidates.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');(out/'proof.json').write_text(json.dumps(live,indent=2),encoding='utf-8')
 if args.activate:
  text='-- Reviewed complete Mahogany terrain, north gate and disguised shop.\nlocal rows={}\nlocal function add(batch)for _,r in ipairs(batch)do rows[#rows+1]=r end end\n'
  for i in range(0,len(rows),20):text+='add((function()return '+lua(rows[i:i+20])+' end)())\n'
  (ROOT/'mappings/mahogany.lua').write_text(text+'return rows\n',encoding='utf-8')
 print(json.dumps({'rows':len(rows),'live':live,'coverage':'360/360 each GSC','activated':args.activate}))
if __name__=='__main__':main()
