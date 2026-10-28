"""Finish Johto outdoor geometry with explicit landmarks and checked counterparts."""
import argparse,copy,json,os
from pathlib import Path
from types import SimpleNamespace
from PIL import Image
import catalog,preview,gen2_extended_review as e
from interior_review import Imports
from newbark_building_review import native_reference
from center_mart_overhang_review import write_rows
ROOT=Path(__file__).resolve().parents[1]
MAPS=('ILEX_FOREST','ROUTE_32','ROUTE_34','ROUTE_38','ROUTE_39','ROUTE_40','ROUTE_41','RUINS_OF_ALPH_OUTSIDE')
ART=('kind','donor','base','parts','asset','assetFileHash','assetFrames','animated','animation','foreground','occludes','credit','sourceUrl','artOverlay','sourceColors')
def artwork(r):return{k:copy.deepcopy(r[k])for k in ART if k in r}

def strip(parts,sy,h,ty):
 result=[]
 for part in parts:
  top=max(sy,part.get('y',0));bottom=min(sy+h,part.get('y',0)+part['h'])
  if top<bottom:
   v=copy.deepcopy(part);v.update(srcY=part.get('srcY',0)+top-part.get('y',0),y=ty+top-sy,h=bottom-top);result.append(v)
 return result

def gate96(closed,front,ox,oy,door):
 result={}
 for dy in range(6):
  for dx in range(6):
   if dy<4:
    sx=(0,1,1,1,2,3)[dx];parts=[]
    for half in range(2):
     sy=(0,1,2,1,2,1,2,3)[dy*2+half];parts+=strip(closed[sx,sy//2]['parts'],sy%2*8,8,half*8)
    art={'kind':'native_composite','base':copy.deepcopy(closed[0,0]['base']),'parts':parts}
   else:
    sx=(0,1,2,2,2,3)[dx]if door else(0,1,1,1,2,3)[dx];art=artwork(front[sx,dy-4]if door else closed[sx,dy-2])
   result[ox+dx,oy+dy]=art
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--activate',action='store_true');args=p.parse_args()
 cache=Path(os.environ['APPDATA'])/'pokemon-love2d';out=ROOT.parent/'.work/tileshift-johto-remaining';out.mkdir(exist_ok=True);imports=Imports(cache,ROOT.parent/'.work/tileshift-catalog');packed=imports.packed
 active=[r for path in(ROOT/'mappings').glob('*.lua')if path.name!='johto_remaining.lua'for r in preview.read_reviewed(path)]
 ground=next(r['base']for r in active if r.get('base',{}).get('tileset')=='general__petalburg'and r['base']['id']==1)
 stage=SimpleNamespace(cache=cache,catalog=ROOT.parent/'.work/tileshift-catalog',output=out)
 templates={}
 for name,native_spec,ys in(
  ('farmhouse',('emerald','EM_OLDALE_TOWN','EM_OLDALE_TOWN_HOUSE1',(4,4,4,4)),tuple(range(8))),
  ('barn',('emerald','EM_ROUTE117','EM_ROUTE117_POKEMON_DAY_CARE',(50,2,4,4)),(0,1,4,5,6,7))):
  source,n=native_reference(stage,name,{'native':native_spec},packed);parts={}
  for y,sy in enumerate(ys):
   for x in range(8):
    gx,gy=n['pixel_origin'][0]+x*8,n['pixel_origin'][1]+sy*8;mid=n['layout']['mids'][gy//16*n['layout']['width']+gx//16];rec=n['records'][mid]
    v={'donor':{'game':n['game'],'tileset':n['pair'],'id':mid,'hash':rec['pixel_sha256']},'srcX':gx%16,'srcY':gy%16,'x':x%2*8,'y':y%2*8,'w':8,'h':8}
    if y<2:v.update(layers=['over'],layerHashes={'over':rec['layer_sha256']['over']})
    parts.setdefault((x//2,y//2),[]).append(v)
  templates[name]=parts
 # Actual native Route117 Daycare, widened using complete window units.
 source,n=native_reference(stage,'daycare',{'native':('emerald','EM_ROUTE117','EM_ROUTE117_POKEMON_DAY_CARE',(50,2,4,4))},packed);parts={}
 for y in range(8):
  xs=(0,1,2,3,4,5,2,3,2,3,6,7)if y<5 else(0,1,2,3,4,5,6,4,5,6,1,7)
  for x,sx in enumerate(xs):
   gx,gy=n['pixel_origin'][0]+sx*8,n['pixel_origin'][1]+y*8;mid=n['layout']['mids'][gy//16*n['layout']['width']+gx//16];rec=n['records'][mid];v={'donor':{'game':n['game'],'tileset':n['pair'],'id':mid,'hash':rec['pixel_sha256']},'srcX':gx%16,'srcY':gy%16,'x':x%2*8,'y':y%2*8,'w':8,'h':8}
   if y<2:v.update(layers=['over'],layerHashes={'over':rec['layer_sha256']['over']})
   parts.setdefault((x//2,y//2),[]).append(v)
 templates['daycare']=parts
 rows=[];roofs=[];stats=[];unmatched=[];landmarks=[]
 for game in e.GAMES:
  data=e.source(cache,game);known={}
  for r in active:
   if r['game']==game and r['tileset']in e.SETS and any(s in r['role']for s in('metal_fence','fence_turn','thin_cliff','half_rock','retaining_wall','whole_raised','rocky_coast','coastal_ocean','raised_rock','paved_rock_front','full_diagonal')):
    c=e.cell_info(cache,game,data,r['tileset'],r['id'],r['quadrant']);known.setdefault(e.identity(c),r)
  closed={(r['x']-18,r['y']-28):r for r in active if r['game']==game and r.get('map')=='OLIVINE_CITY'and r['role']=='olivine_port_closed_front'}
  front={(r['x']-8,r['y']):r for r in active if r['game']==game and r.get('map')=='MAHOGANY_TOWN'and r['role']=='mahogany_north_gate'}
  side=[next(r for r in active if r['game']==game and r['role']=='azalea_ilex_gate_side_entrance'and r.get('parts',[{}])[0].get('donor',{}).get('id')==mid)for mid in(324,332)]
  for name in MAPS:
   m=data['maps'][name];selected=[r for r in active if r['game']==game and r['tileset']==m['tileset']and r.get('map',name)==name];generic={(r['id'],r['quadrant'])for r in selected if r.get('x')is None};pos={(r['x'],r['y'])for r in selected if r.get('x')is not None}
   special={}
   if name=='ILEX_FOREST':
    for ox,oy,kind in((0,0,'front'),(4,38,'side')):
     for dy in range(6):
      for dx in range(6):
       if dy<4:
        sx=(0,1,1,1,2,3)[dx];parts=[]
        for half in range(2):
         sy=(0,1,2,1,2,1,2,3)[dy*2+half];parts+=strip(closed[sx,sy//2]['parts'],sy%2*8,8,half*8)
        art={'kind':'native_composite','base':copy.deepcopy(ground),'parts':parts}
       else:
        sx=(0,1,2,2,2,3)[dx]if kind=='front'else(0,1,1,1,2,3)[dx]
        art=artwork(front[sx,dy-4]if kind=='front'else closed[sx,dy-2])
       special[ox+dx,oy+dy]=art
    for dy in range(2):special[3,42+dy]=artwork(side[dy])
    folder=ROOT/'assets/original/ilex-shrine'
    for dy in range(2):
     path=folder/('cell-'+str(dy)+'.png');special[8,22+dy]={'kind':'original','base':copy.deepcopy(ground),'asset':path.relative_to(ROOT).as_posix(),'assetFileHash':catalog.sha(path.read_bytes())}
    for raw_y in(22,23):
     rec=imports.cell_index('firered')['pewter_outdoor',114];special[27,raw_y]={'kind':'native_composite','base':copy.deepcopy(ground),'parts':[{'donor':{'game':'firered','tileset':'pewter_outdoor','id':114,'hash':rec['pixel_sha256']},'layers':['mid'],'layerHashes':{'mid':rec['layer_sha256']['mid']},'srcX':8,'srcY':0,'w':8,'h':16,'x':8,'y':0}]}
    water=next(z for z in active if z['game']==game and z.get('map')=='ECRUTEAK_CITY'and z.get('donor',{}).get('id')==393)
    pond_mids={(9,42,27,20):392,(42,42,20,20):393,(42,11,20,25):394,(27,20,27,20):400,(20,20,20,20):368,(20,25,20,25):402}
    for py in range(8,14):
     for px in range(4,10):
      bid=m['blocks'][py//2*m['width']+px//2];c=e.cell_info(cache,game,data,m['tileset'],bid,py%2*2+px%2)
      if c['collision']!=41:continue
      mid=pond_mids[tuple(c['tiles'])];rec=imports.cell_index('emerald')['general__petalburg',mid];art={'kind':'native','donor':{'game':'emerald','tileset':'general__petalburg','id':mid,'hash':rec['pixel_sha256']},'animated':True,'animation':copy.deepcopy(water['animation'])};art['animation'].pop('frame0Hash',None);art['animation']['frame0Hash']=catalog.sha(preview.replacement_image(cache,art,packed,ROOT).tobytes());special[px,py]=art
    sign=next(z for z in active if z['game']==game and z['role']=='freestanding_sign');special[3,17]=artwork(sign)
    assert any(w['x']==1 and w['y']==5 and w['destMap']=='ROUTE_34_ILEX_FOREST_GATE'for w in m['warps'])
    assert {(w['x'],w['y'])for w in m['warps']if w['destMap']=='ILEX_FOREST_AZALEA_GATE'}=={(3,42),(3,43)}
   if name=='ROUTE_32':
    for dy in range(4):
     for dx in range(4):special[dx,dy]=artwork(closed[dx,dy])
    for dy in range(2):special[4,2+dy]=artwork(side[dy])
   if name=='ROUTE_34':
    for dy in range(4):
     for dx in range(4):special[12+dx,38+dy]=artwork(front[dx,dy-2]if dy>=2 else closed[dx,dy])
     for dx in range(2):special[18+dx,44+dy]=artwork(closed[dx,dy])
    for dy in range(4):
     for dx in range(6):special[12+dx,12+dy]={'kind':'native_composite','base':copy.deepcopy(ground),'parts':copy.deepcopy(templates['daycare'][dx,dy])}
    for dy in range(2):special[11,14+dy]=artwork(side[dy])
    assert {(w['x'],w['y'])for w in m['warps']if w['destMap']=='DAY_CARE'}=={(11,14),(11,15),(13,15)}
   if name=='ROUTE_38':
    for dy in range(4):
     for dx in range(4):special[36+dx,6+dy]=artwork(closed[dx,dy])
    for dy in range(2):special[35,8+dy]=artwork(side[dy])
    assert {(w['x'],w['y'],w['destMap'])for w in m['warps']}=={(35,8,'ROUTE_38_ECRUTEAK_GATE'),(35,9,'ROUTE_38_ECRUTEAK_GATE')}
   if name=='ROUTE_40'and game=='crystal':
    for dy in range(4):
     for dx in range(4):special[8+dx,2+dy]=artwork(front[dx,dy-2]if dy>=2 else closed[dx,dy])
    assert any(w['x']==9 and w['y']==5 and w['destMap']=='ROUTE_40_BATTLE_TOWER_GATE'for w in m['warps'])
   if name=='RUINS_OF_ALPH_OUTSIDE':
    for ox,oy,door in((6,2,True),(14,18,False)):
     for dy in range(4):
      for dx in range(4):special[ox+dx,oy+dy]=artwork(front[dx,dy-2]if door and dy>=2 else closed[dx,dy])
    for dy in range(2):
     for ox in(13,18):special[ox,20+dy]=artwork(side[dy])
    # Native residence facade reused whole for the small research station.
    # Only one repeated16px roof band is omitted; complete window/door remains.
    for dy in range(2):
     for dx in range(4):special[16+dx,10+dy]={'kind':'native_composite','base':copy.deepcopy(ground),'parts':copy.deepcopy(templates['farmhouse'][dx,dy+2])}
   for y in range(m['height']*2):
    for x in range(m['width']*2):
     bid=m['blocks'][y//2*m['width']+x//2];q=y%2*2+x%2
     farm=next(((kind,ox,oy,h)for kind,ox,oy,h in(('barn',0,2,2),('farmhouse',4,0,4))if name=='ROUTE_39'and ox<=x<ox+4 and oy<=y<oy+h),None)
     override_pond=name=='ILEX_FOREST'and 4<=x<10 and 8<=y<14 and(x,y)in special
     if((bid,q)in generic or(x,y)in pos)and not override_pond:continue
     c=e.cell_info(cache,game,data,m['tileset'],bid,q);r={'game':game,'style':'gen3','map':name,'tileset':m['tileset'],'id':bid,'quadrant':q,'x':x,'y':y,'sourceCells':[[x,y]],'sourceHash':c['sourceHash'],'sourceFiles':data['fingerprints'][m['tileset']],'sourceCollision':c['collision'],'sourcePriority':[bool(a.get('priority'))for a in c['attributes']],'sourcePalettes':[a.get('palette',1)for a in c['attributes']],'status':'reviewed','evidence':'Exact original source pixels, collision, palettes and priority reviewed in the full route. Native Gen3 parts retain full windows, frames, roof outlines and original scale. Source entrances, actors, grass encounters, fishing, story scripts and all original map cells remain unchanged.'}
     if(x,y)in special:
      role='freshwater_pond_ilex'if name=='ILEX_FOREST'and c['collision']==41 else'ilex_original_shrine'if name=='ILEX_FOREST'and x==8 and y in(22,23)else'freestanding_sign'if name=='ILEX_FOREST'and(x,y)==(3,17)else'johto_remaining_native_gate'
      r.update(special[x,y],role=role)
     elif c['collision']==112:
      seed=next(z for z in active if z['game']==game and z['role']=='olivine_port_down_warp_marker');r.update(artwork(seed),role='johto_remaining_down_marker')
     elif c['collision']==0 and set(c['tiles'])<={0,5,6}:r.update(kind='native',donor=copy.deepcopy(ground),role='open_grassy_ground')
     elif name=='ROUTE_32'and c['tiles']==[7,7,7,7]and c['collision']==114:
      path=ROOT/'assets/third_party/peekychew/pier-boards.png';r.update(kind='third_party',credit='Peekychew',sourceUrl='https://www.deviantart.com/peekychew',asset=path.relative_to(ROOT).as_posix(),assetFileHash=catalog.sha(path.read_bytes()),role='johto_fishing_pier_floor')
     elif name=='ROUTE_32'and c['tiles']==[73,73,20,20]and c['collision']==41:
      ocean=next(z for z in active if z['game']==game and z['role']=='coastal_ocean_water_interior');path=ROOT/'assets/third_party/peekychew/pier-edge.png';r.update(kind='third_party',credit='Peekychew',sourceUrl='https://www.deviantart.com/peekychew',asset=path.relative_to(ROOT).as_posix(),assetFileHash=catalog.sha(path.read_bytes()),base=copy.deepcopy(ocean['donor']),animated=True,animation=copy.deepcopy(ocean['animation']),role='johto_fishing_pier_edge')
     elif name=='ROUTE_41'and c['collision']==36:
      ocean=next(z for z in active if z['game']==game and z['role']=='coastal_ocean_water_interior');frames=[{'asset':'assets/original/whirlpool/foam-'+str(i)+'.png','hash':catalog.sha((ROOT/'assets/original/whirlpool'/('foam-'+str(i)+'.png')).read_bytes())}for i in range(8)];r.update(kind='original',base=copy.deepcopy(ocean['donor']),animated=True,animation=copy.deepcopy(ocean['animation']),asset=frames[0]['asset'],assetFileHash=frames[0]['hash'],assetFrames=frames,role='rocky_coast_whirlpool')
     elif c['collision']==123:
      warp=next((w for w in m['warps']if(w['x'],w['y'])==(x,y)),None);assert(name=='ROUTE_32'and((x,y)==(2,15)and warp is None or(x,y)==(6,79)and warp['destMap']=='UNION_CAVE_1F'))or(name=='ROUTE_41'and warp and warp['destMap'].startswith('WHIRL_ISLAND'))or(name=='RUINS_OF_ALPH_OUTSIDE'and warp);rec=imports.cell_index('firered')['general__rom_082d4af4',169];r.update(donor={'game':'firered','tileset':'general__rom_082d4af4','id':169,'hash':rec['pixel_sha256']},role='johto_remaining_cave_mouth')
      if warp:r['sourceDestination']=warp['destMap']
      else:r['evidence']+=' The original physical cave glyph2,15 has no warp event; preserve its appearance without inventing a destination.'
     elif farm:
      kind,ox,oy,h=farm;r.update(kind='native_composite',base=copy.deepcopy(ground),parts=copy.deepcopy(templates[kind][x-ox,y-oy+(1 if kind=='barn'else 0)]),role='johto_moomoo_'+kind)
     elif e.identity(c)in known:
      seed=known[e.identity(c)];r.update(artwork(seed),role=seed['role']if c['collision']==41 else'johto_remaining_'+seed['role']);r['reviewedSeed']={'map':seed.get('map'),'tileset':seed['tileset'],'id':seed['id'],'quadrant':seed['quadrant']}
      if name=='RUINS_OF_ALPH_OUTSIDE'and c['collision']==41:r['role']='freshwater_pond_ruins_'+str(0 if x<10 else 1)
     else:unmatched.append({'game':game,'map':name,'x':x,'y':y,'raw':c['tiles'],'collision':c['collision']});continue
     if name in('ROUTE_32','ROUTE_34','ROUTE_40','ROUTE_41')and(c['collision']in(36,41)or(r.get('animated')and r.get('base'))):r['sourceOceanBounds']=[0,0,m['width']*2-1,m['height']*2-1]
     r['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,r,packed,ROOT).tobytes());rows.append(r)
   if name=='RUINS_OF_ALPH_OUTSIDE':
    for dx in range(4):
     x,y=16+dx,9;bid=m['blocks'][y//2*m['width']+x//2];q=y%2*2+x%2;c=e.cell_info(cache,game,data,m['tileset'],bid,q)
     roofs.append({'game':game,'style':'gen3','map':name,'tileset':m['tileset'],'id':bid,'quadrant':q,'x':x,'y':y,'buildingY':10,'sourceHash':c['sourceHash'],'sourceFiles':data['fingerprints'][m['tileset']],'sourceCollision':c['collision'],'sourcePriority':[bool(a.get('priority'))for a in c['attributes']],'sourcePalettes':[a.get('palette',1)for a in c['attributes']],'kind':'native_composite','parts':copy.deepcopy(templates['farmhouse'][dx,0]),'role':'alph_research_station_roof','status':'reviewed','evidence':'One transparent decorative roof row. Whole native window and doorway including frame caps retain native scale. Original research station entrance17,11 and source collision/events unchanged.'})
   if name=='ROUTE_39':
    assert any(w['x']==1 and w['y']==3 and w['destMap']=='ROUTE_39_BARN'for w in m['warps'])
    assert any(w['x']==5 and w['y']==3 and w['destMap']=='ROUTE_39_FARMHOUSE'for w in m['warps'])
    for dx in range(4):
     x,y=dx,1;bid=m['blocks'][y//2*m['width']+x//2];q=y%2*2+x%2;c=e.cell_info(cache,game,data,m['tileset'],bid,q)
     r={'game':game,'style':'gen3','map':name,'tileset':m['tileset'],'id':bid,'quadrant':q,'x':x,'y':y,'buildingY':2,'sourceHash':c['sourceHash'],'sourceFiles':data['fingerprints'][m['tileset']],'sourceCollision':c['collision'],'sourcePriority':[bool(a.get('priority'))for a in c['attributes']],'sourcePalettes':[a.get('palette',1)for a in c['attributes']],'kind':'native_composite','parts':copy.deepcopy(templates['barn'][dx,0]),'role':'moomoo_barn_roof','status':'reviewed','evidence':'One decorative upper roof row over the original fence/ground. The complete native wooden farm-outbuilding facade, window and door stay unscaled; original barn entrance1,3, Miltank and story events remain unchanged.'};roofs.append(r)
   stats.append({'game':game,'map':name,'total':m['width']*m['height']*4})
 (out/'unmatched.json').write_text(json.dumps(unmatched,indent=2)+'\n')
 if unmatched:print(json.dumps({'unmatched':len(unmatched),'examples':unmatched[:20]}));return
 live=e.validate_batch(rows,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=out),ROOT)
 (out/'proof.json').write_text(json.dumps({'maps':stats,'live':live,'roof_cells':len(roofs)},indent=2)+'\n')
 for game in e.GAMES:
  for name in MAPS:
   all_roofs=[r for p in ('roof_catalog.lua','side_catalog.lua','center_mart_roofs.lua','goldenrod_roofs.lua','pallet_roofs.lua')if(ROOT/'lib'/p).exists()for r in preview.read_reviewed(ROOT/'lib'/p)]+roofs
   r=preview.map_preview(cache,out,game,name,game+'-'+name,active+rows,packed,1,ROOT,roof_rows=all_roofs);assert r['replaced_occurrences']==r['visible_cells'],(game,name,r)
 if args.activate:write_rows(ROOT/'mappings/johto_remaining.lua',rows);write_rows(ROOT/'lib/johto_roofs.lua',roofs)
 print(json.dumps({'rows':len(rows),'roofs':len(roofs),'maps':stats,'live':live,'activated':args.activate}))
if __name__=='__main__':main()
