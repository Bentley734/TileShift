"""Finish ten Johto routes with complete native gates, portals and cliff edges."""
import argparse,copy,json,os
from pathlib import Path
from types import SimpleNamespace
from PIL import Image,ImageDraw
import catalog,preview,gen2_extended_review as e
from interior_review import Imports
from newbark_building_review import lua
ROOT=Path(__file__).resolve().parents[1]
MAPS=('ROUTE_29','ROUTE_31','ROUTE_33','ROUTE_35','ROUTE_36','ROUTE_42','ROUTE_43','ROUTE_44','ROUTE_45','ROUTE_46')
GATES={'ROUTE_29':[(26,0,'front_only')],'ROUTE_31':[(0,4,'side')],
 'ROUTE_35':[(2,2,'front'),(8,34,'back')],'ROUTE_36':[(14,6,'side'),(46,14,'front')],
 'ROUTE_43':[(16,32,'front'),(8,52,'back')],'ROUTE_46':[(6,34,'back')]}
CAVES={'ROUTE_31':{(34,5):'DARK_CAVE_VIOLET_ENTRANCE'},'ROUTE_33':{(11,9):'UNION_CAVE_1F'},
 'ROUTE_42':{(10,5):'MOUNT_MORTAR_1F_OUTSIDE',(28,9):'MOUNT_MORTAR_1F_OUTSIDE',(46,7):'MOUNT_MORTAR_1F_OUTSIDE'},
 'ROUTE_44':{(56,7):'ICE_PATH_1F'},'ROUTE_45':{(2,5):'DARK_CAVE_BLACKTHORN_ENTRANCE'},
 'ROUTE_46':{(14,5):'DARK_CAVE_VIOLET_ENTRANCE'}}
SIDE={'ROUTE_31':[(4,6)],'ROUTE_36':[(18,8)],'ROUTE_42':[(0,8)]}
def main():
 p=argparse.ArgumentParser();p.add_argument('--activate',action='store_true');args=p.parse_args()
 cache=Path(os.environ['APPDATA'])/'pokemon-love2d';out=ROOT.parent/'.work/tileshift-johto-route-details';out.mkdir(exist_ok=True)
 imports=Imports(cache,ROOT.parent/'.work/tileshift-catalog');packed=imports.packed
 active=[r for path in(ROOT/'mappings').glob('*.lua')if path.name not in('johto_route_details.lua','johto_terrain_repeats.lua')for r in preview.read_reviewed(path)]
 repeats=json.loads((ROOT.parent/'.work/tileshift-johto-terrain-repeats/candidates.json').read_text());active+=repeats
 ground=next(r['base']for r in active if r.get('base',{}).get('tileset')=='general__petalburg'and r['base']['id']==1)
 rows=[];stats=[];contacts=[]
 def part(mid,sx=0,sy=0,x=0,y=0,w=16,h=16):
  c=imports.cell_index('firered')['pewter_outdoor',mid]
  return {'donor':{'game':'firered','tileset':'pewter_outdoor','id':mid,'hash':c['pixel_sha256']},'layers':['mid'],'layerHashes':{'mid':c['layer_sha256']['mid']},'srcX':sx,'srcY':sy,'x':x,'y':y,'w':w,'h':h}
 def half_front(x,w):return [part(121,x,0,x,8,w,4),part(121,x,12,x,12,w,4)]
 def art_fields(seed):return {k:copy.deepcopy(seed[k])for k in('kind','base','donor','parts','animated','animation')if k in seed}
 for game in e.GAMES:
  data=e.source(cache,game)
  closed={(r['x']-18,r['y']-28):r for r in active if r['game']==game and r.get('map')=='OLIVINE_CITY'and r['role']=='olivine_port_closed_front'};assert len(closed)==16
  front={(r['x']-8,r['y']):r for r in active if r['game']==game and r.get('map')=='MAHOGANY_TOWN'and r['role']=='mahogany_north_gate'};assert len(front)==8
  side=[next(r for r in active if r['game']==game and r['role']=='azalea_ilex_gate_side_entrance'and r.get('parts',[{}])[0].get('donor',{}).get('id')==mid)for mid in(324,332)]
  down=next(r for r in active if r['game']==game and r['role']=='olivine_port_down_warp_marker')
  fences={e.identity(e.cell_info(cache,game,data,r['tileset'],r['id'],r['quadrant'])):r for r in active if r['game']==game and r['role']in('azalea_metal_fence','ecruteak_native_metal_fence')}
  for name in MAPS:
   m=data['maps'][name];sel=[r for r in active if r['game']==game and r['tileset']==m['tileset']and r.get('map',name)==name]
   generic={(r['id'],r['quadrant'])for r in sel if r.get('x')is None};positioned={(r['id'],r['quadrant'],r['x'],r['y'])for r in sel if r.get('x')is not None};added=[]
   gate={}
   for ox,oy,kind in GATES.get(name,[]):
    h=2 if kind in('back','front_only')else 4
    for dy in range(h):
     for dx in range(4):gate[ox+dx,oy+dy]=(front[dx,dy]if kind=='front_only'else front[dx,dy-2]if kind=='front'and dy>=2 else closed[dx,dy],kind)
   for j,bid in enumerate(m['blocks']):
    for q in range(4):
     x,y=j%m['width']*2+q%2,j//m['width']*2+q//2
     if(bid,q)in generic or(bid,q,x,y)in positioned:continue
     c=e.cell_info(cache,game,data,m['tileset'],bid,q);raw=c['tiles'];r={'game':game,'style':'gen3','map':name,'tileset':m['tileset'],'id':bid,'quadrant':q,'x':x,'y':y,'sourceCells':[[x,y]],'sourceHash':c['sourceHash'],'sourceFiles':data['fingerprints'][m['tileset']],'sourceCollision':c['collision'],'sourcePriority':[bool(a.get('priority'))for a in c['attributes']],'sourcePalettes':[a.get('palette',1)for a in c['attributes']],'status':'reviewed'}
     if(x,y)in gate:
      seed,kind=gate[x,y];assert c['collision']in(7,113);r.update(art_fields(seed),role='johto_route_gate_'+kind)
     elif c['collision']==123:
      destination=CAVES[name][x,y];assert any(w['x']==x and w['y']==y and w['destMap']==destination for w in m['warps']);c3=imports.cell_index('firered')['general__rom_082d4af4',169];r.update(donor={'game':'firered','tileset':'general__rom_082d4af4','id':169,'hash':c3['pixel_sha256']},role='johto_route_native_cave_entrance',sourceDestination=destination)
     elif c['collision']==118:
      start=next((a,b)for a,b in SIDE[name]if x==a and y in(b,b+1));assert raw==[64]*4
      warp=next(w for w in m['warps']if w['x']==x and w['y']==y);assert'GATE'in warp['destMap'];r.update(art_fields(side[y-start[1]]),role='johto_route_side_gate_entrance',sourceDestination=warp['destMap'])
     elif c['collision']==112:
      assert raw==[64]*4;warp=next(w for w in m['warps']if w['x']==x and w['y']==y);assert'GATE'in warp['destMap'];r.update(art_fields(down),role='johto_route_down_gate_marker',sourceDestination=warp['destMap'])
     elif e.identity(c)in fences:r.update(art_fields(fences[e.identity(c)]),role='johto_route_complete_metal_fence')
     elif raw==[90,90,74,89]and c['collision']==7:
      # The complete horizontal panel has a terminal at each end. The
      # following left-post cell joins its left terminal, as the reviewed
      # Ecruteak right corner joins the same panel's right terminal.
      seed=next(z for z in active if z['game']==game and z['role']=='ecruteak_native_metal_fence'and e.cell_info(cache,game,data,z['tileset'],z['id'],z['quadrant'])['tiles']==[90,90,89,74])
      r.update(art_fields(seed),role='johto_route_complete_left_fence_turn')
     else:
      r.update(kind='native_composite',base=copy.deepcopy(ground),role='johto_route_thin_cliff')
      if raw in([6,61,6,61],[5,61,5,61]):r['parts']=[part(114,8,0,8,0,8,16)]
      elif raw in([6,61,76,77],[5,61,76,77]):r['parts']=[part(122,8,0,8,0,8,16)]+half_front(0,8)
      elif raw in([59,6,59,6],[59,5,59,5]):r['parts']=[part(112,0,0,0,0,8,16)]
      elif raw in([59,6,75,76],[59,5,75,76]):r['parts']=[part(120,0,0,0,0,8,16)]+half_front(8,8)
      elif raw in([5,43,43,59],[45,5,61,45]):r.update(parts=[part(104 if raw[0]==5 else 106)],role='johto_route_full_diagonal_cliff')
      elif raw==[5,5,91,91]:
       assert c['collision']==0;r.update(parts=[copy.deepcopy(next(p for z in active for p in z.get('parts',[])if p['donor']['game']=='firered'and p['donor']['id']==137 and p.get('srcY')==8))],role='johto_route_native_stair_threshold')
      else:raise AssertionError((game,name,bid,q,x,y,c))
      if r['role']!='johto_route_native_stair_threshold':assert c['collision']==7
     r['evidence']='Reviewed complete source route geometry and original entrance events. Unscaled whole native FR Route15 roof, window/wall units and full17px single-door cap use approved Olivine/Mahogany gate assemblies. Closed side fronts retain no front doorway; genuine source side entrances use the complete paired324/332 native jambs. Down-arrow field-effect2 remains static over original DOWN warp carpets; no warp is invented for decorative physical doors. Full native169 cave mouth retains each exact original cave destination. Thin retaining faces use complete side profiles and top/base outlines, omitting only repeated middle wall material. Original collision, encounters, actors, scripts and all warp events remain untouched.'
     if r.get('parts'):r['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,r,packed,ROOT).tobytes())
     added.append(r)
   rows+=added;report=preview.map_preview(cache,out,game,name,game+'-'+name,active+rows,packed,1,ROOT);assert report['replaced_occurrences']==report['visible_cells'];stats.append({'game':game,'map':name,'added_cells':len(added),'total':report['visible_cells']})
   if game=='crystal':
    image=Image.open(out/(game+'-'+name+'-after-native.png')).convert('RGB');contacts.append((name,image))
 live=e.validate_batch(rows,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=out),ROOT)
 (out/'candidates.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');(out/'proof.json').write_text(json.dumps({'maps':stats,'live':live},indent=2),encoding='utf-8')
 # Separate exact2x local gate/cave panels: no fractional scaling even in QA.
 patches=[]
 for name,im in contacts:
  for x,y,kind in GATES.get(name,[]):patches.append((name+' '+kind,im.crop((max(0,x*16-16),max(0,y*16-16),min(im.width,(x+5)*16),min(im.height,(y+5)*16)))))
  for x,y in CAVES.get(name,{}):patches.append((name+' cave',im.crop((max(0,x*16-16),max(0,y*16-16),min(im.width,x*16+32),min(im.height,y*16+32)))))
 sheet=Image.new('RGB',(1000,((len(patches)+4)//5)*240),'#18202c');draw=ImageDraw.Draw(sheet)
 for n,(label,im)in enumerate(patches):x,y=n%5*200,n//5*240;sheet.paste(im.resize((im.width*2,im.height*2),Image.Resampling.NEAREST),(x,y+20));draw.text((x,y),label,fill='white')
 sheet.save(out/'gate-cave-contexts.png')
 if args.activate:
  text='-- Complete ten Johto routes: approved full native gates, portals and terrain.\nlocal rows={}\nlocal function add(batch)for _,r in ipairs(batch)do rows[#rows+1]=r end end\n'
  for n in range(0,len(rows),20):text+='add((function()return '+lua(rows[n:n+20])+' end)())\n'
  (ROOT/'mappings/johto_route_details.lua').write_bytes((text+'return rows\n').encode())
 print(json.dumps({'rows':len(rows),'maps':stats,'live':live,'activated':args.activate}))
if __name__=='__main__':main()
