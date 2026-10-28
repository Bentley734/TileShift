"""Goldenrod's original city geometry, with native-scale Gen3 counterparts."""
import argparse,copy,json,os
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
from PIL import Image
import catalog,preview,gen2_extended_review as e
from newbark_building_review import native_reference,lua
from center_mart_overhang_review import write_rows
from goldenrod_native_art import build
from interior_review import Imports
ROOT=Path(__file__).resolve().parents[1]
URL='https://imgur.com/gallery/testing-out-gen-3-style-tiles-johto-6A43Cji'
ART_KEYS=('asset','assetFileHash','assetPixelHash','base','parts','donor','kind','animated','animation','foreground','occludes','frames','credit','sourceUrl','flora','artOverlay','sourceOceanBounds','buildingCompact')
def art_fields(row):return{k:copy.deepcopy(row[k])for k in ART_KEYS if k in row}

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--activate',action='store_true');args=parser.parse_args()
 out=ROOT.parent/'.work/tileshift-goldenrod-finish';out.mkdir(exist_ok=True);cache=Path(os.environ['APPDATA'])/'pokemon-love2d'
 active=e.active_rows(ROOT);arts,assets,metadata=build();imports=Imports(cache,ROOT.parent/'.work/tileshift-catalog');packed=imports.packed
 def ref(game,pair,mid):return{'game':game,'tileset':pair,'id':mid,'hash':imports.cell_index(game)[pair,mid]['pixel_sha256']}
 paving=ref('firered','pewter_outdoor',449)
 def part(mid,x=0,y=0,w=16,h=16,sx=0,sy=0,layers=('mid',)):
  c=imports.cell_index('firered')['pewter_outdoor',mid];return{'donor':ref('firered','pewter_outdoor',mid),'srcX':sx,'srcY':sy,'x':x,'y':y,'w':w,'h':h,'layers':list(layers),'layerHashes':{n:c['layer_sha256'][n]for n in layers}}
 stage=SimpleNamespace(cache=cache,catalog=ROOT.parent/'.work/tileshift-catalog',output=out)
 home,native=native_reference(stage,'home',{'native':('emerald','EM_OLDALE_TOWN','EM_OLDALE_TOWN_HOUSE1',(4,4,4,4))},packed)
 homeparts={}
 for y in range(4):
  for x in range(4):
   gx,gy=native['pixel_origin'][0]+x*16,native['pixel_origin'][1]+y*16;mid=native['layout']['mids'][gy//16*native['layout']['width']+gx//16];rec=native['records'][mid]
   p={'donor':ref('emerald',native['pair'],mid),'w':16,'h':16}
   if y==0:p.update(layers=['over'],layerHashes={'over':rec['layer_sha256']['over']})
   homeparts[x,y]=[p]
 rows=[];roofs=[];proof=[];unmatched=[]
 for game in e.GAMES:
  data=e.source(cache,game);m=data['maps']['GOLDENROD_CITY'];old={};specific={};known=defaultdict(list)
  for r in active:
   if r['game']!=game:continue
   if r['tileset']in e.SETS:
    c=e.cell_info(cache,game,data,r['tileset'],r['id'],r['quadrant']);known[e.identity(c)].append(r)
   if r['tileset']==m['tileset']and r.get('map','GOLDENROD_CITY')=='GOLDENROD_CITY':
    if r.get('x')is None:old[r['id'],r['quadrant']]=r
    else:specific[r['x'],r['y']]=r
  def source_row(x,y):
   bid=m['blocks'][y//2*m['width']+x//2];q=y%2*2+x%2;c=e.cell_info(cache,game,data,m['tileset'],bid,q)
   return{'game':game,'style':'gen3','map':'GOLDENROD_CITY','tileset':m['tileset'],'id':bid,'quadrant':q,'x':x,'y':y,'sourceCells':[[x,y]],'sourceHash':c['sourceHash'],'sourceFiles':data['fingerprints'][m['tileset']],'sourceCollision':c['collision'],'sourcePriority':[bool(z.get('priority'))for z in c['attributes']],'sourcePalettes':[z.get('palette',1)for z in c['attributes']],'status':'reviewed','evidence':'Reviewed Goldenrod native Gen3 counterpart, matched to the original source shape and purpose. Whole native pixels and complete architectural modules retain original scale. All source collisions, entrances, events, maps and actors remain unchanged.'},c
  replacements={};building_records=[]
  def install(name,rect,destination=None,door=None):
   ox,oy,w,h=rect;im=arts[name];extra=im.height//16-h;assert extra in(0,1)and im.width==w*16
   if destination:assert any(v['x']==door[0]and v['y']==door[1]and v['destMap']==destination for v in m['warps'])
   elif name.startswith('closed'):assert not any(ox<=v['x']<ox+w and oy<=v['y']<oy+h for v in m['warps'])
   building_records.append({'game':game,'map':'GOLDENROD_CITY','art':name,'rect':rect,'draw_origin':[ox,oy-extra],'door':door,'destination':destination})
   for dy in range(h+extra):
    for dx in range(w):
     x,y=ox+dx,oy-extra+dy
     if y<0:continue
     r,c=source_row(x,y);r.update(kind='third_party',credit='MetalFlygon08',sourceUrl=URL,role='goldenrod_native_'+name,**assets[name][dx,dy]);r['evidence']+=' Public MetalFlygon08 Johto components, credited under the author free-use statement.'
     if dy<extra:r['buildingY']=oy;roofs.append(r)
     else:
      r['base']=copy.deepcopy(paving)
      if name=='department'and(dx,dy)==(2,h+extra-1):r['base']=ref('firered','general__rom_082d4b3c',660)
      if name=='underground'and(dx,dy)==(1,h+extra-1):r['base']=ref('firered','general__rom_082d4af4',61)
      replacements[x,y]=r
  install('department',[22,20,6,8],'GOLDENROD_DEPT_STORE_1F',[24,27])
  install('station',[8,10,6,4],'GOLDENROD_MAGNET_TRAIN_STATION',[9,13])
  florist=next(w for w in m['warps']if w['destMap']=='GOLDENROD_FLOWER_SHOP')
  install('florist',[florist['x']-1,4,4,2],'GOLDENROD_FLOWER_SHOP',[florist['x'],5])
  for x,y,dest in((8,4,'GOLDENROD_UNDERGROUND_SWITCH_ROOM_ENTRANCES'),(10,28,'GOLDENROD_UNDERGROUND_SWITCH_ROOM_ENTRANCES')):
   actual=next(v for v in m['warps']if v['x']==x+1 and v['y']==y+1);assert'UNDERGROUND'in actual['destMap'];install('underground',[x,y,4,2],actual['destMap'],[x+1,y+1])
  for x,y in((24,12),(34,14)):install('closed_tall',[x,y,4,4])
  assert any(v['x']==19 and v['y']==1 and v['destMap']=='ROUTE_35_GOLDENROD_GATE'for v in m['warps'])
  for z in active:
   if z['game']==game and z.get('map')=='MAHOGANY_TOWN'and z['role']=='mahogany_north_gate':
    x,y=z['x']+10,z['y'];r,c=source_row(x,y);r.update(art_fields(z),role='goldenrod_north_gate');replacements[x,y]=r
  # Original Radio Tower is L-shaped: do not replace its upper-right plaza.
  assert any(v['x']==5 and v['y']==15 and v['destMap']=='RADIO_TOWER_1F'for v in m['warps'])
  building_records.append({'game':game,'map':'GOLDENROD_CITY','art':'radio','rect':[4,4,4,12],'draw_origin':[4,4],'door':[5,15],'destination':'RADIO_TOWER_1F','upper_width':2})
  for dy in range(12):
   for dx in range(2 if dy<6 else 4):
    r,c=source_row(4+dx,4+dy);r.update(kind='third_party',credit='MetalFlygon08',sourceUrl=URL,role='goldenrod_native_radio',base=copy.deepcopy(paving),**assets['radio'][dx,dy]);replacements[4+dx,4+dy]=r
  # Whole native Oldale homes fit these two original64x64 footprints.
  for ox,oy,dest in((14,4,'GOLDENROD_NAME_RATER'),(30,18,'GOLDENROD_HAPPINESS_RATER')):
   actual=next(v for v in m['warps']if v['x']==ox+1 and v['y']==oy+3);assert('NAME_RATER'in actual['destMap'])if ox==14 else('HAPPINESS'in actual['destMap'])
   for dy in range(4):
    for dx in range(4):
     r,c=source_row(ox+dx,oy+dy);r.update(kind='native_composite',base=copy.deepcopy(paving),parts=copy.deepcopy(homeparts[dx,dy]),role='goldenrod_native_home');replacements[ox+dx,oy+dy]=r
  # Detect complete decorative house runs, including the two widths used
  # along the city edges. Distinct native modules preserve complete windows.
  family={(16,17,10,11),(17,17,11,11),(17,18,11,12)}
  for y in range(m['height']*2):
   x=0
   while x<m['width']*2:
    _,c=source_row(x,y)
    if(x,y)in replacements or tuple(c['tiles'])not in family:x+=1;continue
    start=x
    while x<m['width']*2:
     _,c=source_row(x,y)
     if(x,y)in replacements or tuple(c['tiles'])not in family:break
     x+=1
     if c['tiles']==[17,18,11,12]:break
    width=x-start;assert width in(2,3,4,5,6),(start,y,width)
    if any(start<=v['x']<x and y<=v['y']<y+2 for v in m['warps']):continue
    install('closed'+str(width*16),[start,y,width,2])
  for y in range(m['height']*2):
   for x in range(m['width']*2):
    r,c=source_row(x,y);raw=c['tiles'];key=e.identity(c);seed=specific.get((x,y),old.get((r['id'],r['quadrant'])))
    if(x,y)in replacements:r=replacements[x,y]
    elif raw==[47]*4:r.update(kind='third_party',credit='MetalFlygon08',sourceUrl=URL,role='goldenrod_brick_road',**assets['road'][0,0])
    elif raw==[6]*4:r.update(kind='native_composite',parts=[{'donor':copy.deepcopy(paving),'w':16,'h':16}],role='goldenrod_city_paving')
    elif seed:r.update(art_fields(seed),role=seed['role']);r['evidence']=seed['evidence']+' Goldenrod position, native roof height and original city adjacency checked.'
    else:
     eligible=[z for z in known[key]if any(w in z['role']for w in('metal_fence','raised_rock','half_rock','whole_raised_ground','paved_rock_front','retaining_wall','rocky_coast','coastal_ocean'))]
     if eligible:
      z=next((z for z in eligible if z['role'].startswith('rocky_coast')and z.get('map')=='CHERRYGROVE_CITY'),eligible[0]);r.update(art_fields(z),role='goldenrod_'+z['role'])
      if c['collision']==41:r['sourceOceanBounds']=[0,0,5,35]
     elif raw==[90,90,74,89]:
      z=next(z for z in active if z['game']==game and z['role']=='ecruteak_native_metal_fence'and e.cell_info(cache,game,data,z['tileset'],z['id'],z['quadrant'])['tiles']==[90,90,89,74]);r.update(art_fields(z),role='goldenrod_left_fence_turn')
     elif raw in([54,54,70,70],[54,54,6,6]):
      dy=y%2;r.update(kind='third_party',credit='MetalFlygon08',sourceUrl=URL,role='goldenrod_raised_rail_platform',base=copy.deepcopy(paving),**assets['rail'][0,dy])
      if c['collision']==0:
       # Road-level crossing keeps its thin rail and visible pavement.
       r.update(assets['rail_crossing'][0,0],role='goldenrod_walkable_rail_crossing')
     elif raw==[5,43,43,59]:r.update(kind='native_composite',base=copy.deepcopy(paving),parts=[part(104)],role='goldenrod_full_northwest_cliff')
     elif raw==[76,93,20,59]and c['collision']==41:
      z=next(z for z in active if z['game']==game and z.get('donor',{}).get('tileset')=='general__petalburg'and z['donor']['id']==394 and z.get('animated'))
      r.update(art_fields(z),role='rocky_coast_goldenrod_northeast',sourceOceanBounds=[0,0,5,35])
     elif raw==[212,213,214,215]:r.update(kind='third_party',credit='MetalFlygon08',sourceUrl=URL,role='goldenrod_florist_planter',base=ref('emerald','general__petalburg',4),**assets['planter'][0,0])
     elif 222 in raw:
      f=imports.cell_index('emerald')['general__petalburg',4]
      r.update(kind='native_composite',role='decorative_flower_southeast',base=copy.deepcopy(paving),parts=[{'donor':ref('emerald','general__petalburg',4),'w':16,'h':16,'layers':['over'],'layerHashes':{'over':f['layer_sha256']['over']}}])
     else:unmatched.append({'game':game,'x':x,'y':y,'id':r['id'],'quadrant':r['quadrant'],'raw':raw,'collision':c['collision']});continue
    if c['collision']==41 or r.get('sourceOceanBounds'):r['sourceOceanBounds']=[0,0,5,35]
    if r.get('base',{}).get('tileset')=='general__petalburg'and r['base']['id']==1 and any(w in r['role']for w in('architecture_','arcade','home','gate','fence')):r['base']=copy.deepcopy(paving)
    r['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,r,packed,ROOT).tobytes());rows.append(r)
  proof+=building_records
 (out/'unmatched.json').write_text(json.dumps(unmatched,indent=2))
 if unmatched:print(json.dumps({'unmatched':len(unmatched),'examples':unmatched[:24]}));return
 assert len(rows)==4320
 live=e.validate_batch(rows,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=out),ROOT)
 live_roofs=e.validate_batch(roofs,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=out),ROOT)
 (out/'proof.json').write_text(json.dumps({'instances':proof,'artwork':metadata,'live':live,'live_roofs':live_roofs,'cells_per_game':1440},indent=2)+'\n')
 if args.activate:
  for path in(ROOT/'mappings').glob('*.lua'):
   if path.name=='goldenrod.lua':continue
   previous=preview.read_reviewed(path);keep=[r for r in previous if not(r['game']in e.GAMES and r.get('map')=='GOLDENROD_CITY')]
   if len(keep)!=len(previous):write_rows(path,keep)
  write_rows(ROOT/'mappings/goldenrod.lua',rows);write_rows(ROOT/'lib/goldenrod_roofs.lua',roofs)
 for game in e.GAMES:
  report=preview.map_preview(cache,out,game,'GOLDENROD_CITY',game+'-complete',rows,packed,1,ROOT,roof_rows=roofs+preview.read_reviewed(ROOT/'lib/center_mart_roofs.lua'));assert report['replaced_occurrences']==1440
 print(json.dumps({'rows':len(rows),'roofs':len(roofs),'live':live,'activated':args.activate}))
if __name__=='__main__':main()
