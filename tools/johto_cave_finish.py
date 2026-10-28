"""Audit remaining Johto caves; stage only exact, unambiguous reviewed artwork."""
import argparse,copy,json,os,zlib
from collections import defaultdict,Counter
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import catalog,preview,gen2_extended_review as e,gen2_cave_review as cave
from johto_remaining_review import artwork
from interior_review import Imports
from center_mart_overhang_review import write_rows
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
SKIP={'MOUNT_MOON','DIGLETTS_CAVE','VICTORY_ROAD','ROCK_TUNNEL_1F','ROCK_TUNNEL_B1F','SEAFOAM_GYM','HALL_OF_FAME'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT.parent/'.work/tileshift-johto-cave-finish');p.add_argument('--validate',action='store_true');p.add_argument('--activate',action='store_true');a=p.parse_args();assert not a.activate or a.validate;a.output.mkdir(exist_ok=True,parents=True);cache=Path(os.environ['APPDATA'])/'pokemon-love2d';active=[r for f in(ROOT/'mappings').glob('*.lua')if f.name!='johto_cave_finish.lua'for r in preview.read_reviewed(f)];candidates=[];held={};stats=[];packed={};imp=Imports(cache,ROOT.parent/'.work/tileshift-catalog')
 def ref(mid,game='emerald',pair='general__cave'):
  return{'game':game,'tileset':pair,'id':mid,'hash':imp.cell_index(game)[pair,mid]['pixel_sha256']}
 animations={}
 def animated(mid,bank_name='general_water'):
  key=mid,bank_name
  if key not in animations:
   path=cache/'emerald/data/generated/gba/native/general__cave';manifest=imp.table('emerald','gba/native/general__cave/anim_manifest');bank=next(z for z in manifest['banks']if z['name']==bank_name);raw=(path/bank['file']).read_bytes();expected=bank['frames']*len(bank['mids'])*256
   if len(raw)!=expected:raw=zlib.decompress(raw)
   assert len(raw)==expected;spec={'bank':bank_name,'hash':catalog.sha(raw),'manifestHash':catalog.sha((path/'anim_manifest.lua').read_bytes()),'frames':bank['frames'],'period':bank['period'],'phase':bank.get('phase',0),'counter':bank['counter'],'counterMax':manifest['counters'][bank['counter']]['max'],'quadMask':bank['quads'][bank['mids'].index(mid)]};art={'kind':'native','donor':ref(mid),'animated':True,'animation':spec};spec['frame0Hash']=catalog.sha(preview.replacement_image(cache,art,packed,ROOT).tobytes());animations[key]=art
  return copy.deepcopy(animations[key])
 def explicit(c):
  raw,col=tuple(c['tiles']),c['collision'];ice=c['tileset']=='TILESET_ICE_PATH'
  if ice:
   def iref(mid):return ref(mid,'firered','general__rom_082d4e24')
   def native(mid,role):return{'kind':'native','donor':iref(mid),'role':role}
   def clipped(mid,sx,sy,x,y,w,h):return{'kind':'native_composite','base':iref(641),'parts':[{'donor':iref(mid),'srcX':sx,'srcY':sy,'x':x,'y':y,'w':w,'h':h}],'role':'ice_thin_original_wall'}
   if col==96 and raw in((142,143,158,159),(16,16,16,16)):return native(859,'ice_open_fall_hole')
   if col==7 and raw==(6,7,22,23):return native(642,'fixed_ice_boulder')
   walls={(1,2,17,18):648,(2,3,18,19):650,(17,18,33,34):664,(18,19,34,35):666,(25,1,1,17):648,(3,25,19,3):650,(17,33,33,34):664,(35,19,34,35):666,(36,34,19,36):667,(34,37,37,17):668,(17,17,17,17):656,(19,19,19,19):658,(34,34,34,34):665,(18,18,18,18):657,(2,2,18,18):649,
    (160,161,176,177):667,(162,163,178,179):668,(132,133,148,149):648,(134,135,150,151):650,(164,165,180,181):664,(166,167,182,183):666,(136,137,152,153):648,(140,141,156,157):650,(184,185,200,201):664,(184,185,200,200):664,(188,189,204,205):666,(128,129,144,145):665,(130,131,146,147):650,(185,186,201,202):665,(186,187,202,203):665,(186,186,202,202):665,(168,169,168,169):656,(172,173,172,173):658,(192,193,208,209):666,(194,195,210,211):664,(152,153,168,169):656,(156,157,172,173):658,(138,139,154,154):649,(138,139,155,155):649,(155,155,155,155):657,(17,25,33,34):668,(169,155,200,186):668}
   if col in(7,178)and raw in walls:return native(walls[raw],'ice_full_native_wall_'+str(walls[raw]))
   if col in(112,160,161,163,164,165)and set(raw)<={18,25,154,155,170,171}:return native(641,'ice_snow_with_original_movement')
   if col==0 and raw in((60,61,60,61),(174,175,190,191)):return native(644,'ice_complete_stone_steps')
   if col==7 and raw in((66,67,18,18),(66,67,170,25)):return native(647,'ice_complete_native_exit')
   if col==7 and raw in((17,25,17,25),(153,154,169,154)):return clipped(656,8,0,0,0,8,16)
   if col==7 and raw==(155,156,155,156):return clipped(658,0,0,8,0,8,16)
   if col==7 and raw in((25,25,34,34),(170,171,186,186),(170,155,186,186),(155,155,186,186)):return clipped(665,0,8,0,8,16,8)
   if raw==(155,156,25,154):return clipped(658,0,0,8,0,8,8)
   return None
  simple={(10,38,23,10):539,(38,11,11,21):540,(54,55,54,55):516,(1,1,38,38):594,(1,23,38,39):539,(21,1,37,38):540,(37,38,37,38):528,(38,39,38,39):530}
  if raw in simple:return{'kind':'native','donor':ref(simple[raw]),'role':'johto_cave_'+('stone_steps'if simple[raw]==516 else'inward_wall_'+str(simple[raw]))}
  if raw==(1,1,1,1)and col in(96,112,160,161,163,164,165):return{'kind':'native','donor':ref(513),'role':'cave_original_floor_with_native_movement'}
  if raw==(16,16,16,16)and col==7:return{'kind':'native','donor':ref(0),'role':'cave_black_void'}
  if raw==(26,27,22,22)and col==7:return{'kind':'native_composite','base':ref(529),'parts':[{'donor':ref(601),'w':16,'h':8}],'role':'johto_cave_complete_exit_light'}
  if raw==(14,15,30,31)and col==123:return{'kind':'native','donor':ref(555),'role':'johto_cave_complete_rock_portal'}
  if raw in((21,1,21,1),(1,23,1,23))and col==7:
   west=raw[0]==21;return{'kind':'native_composite','base':ref(513),'parts':[{'donor':ref(528 if west else 530),'srcX':8 if west else 0,'x':0 if west else 8,'w':8,'h':16}],'role':'cave_thin_rock_face_'+('west'if west else'east')}
  water={(20,20,20,20):635,(23,20,23,20):650,(20,21,20,21):648,(38,38,20,20):657,(10,38,23,20):649,(38,11,20,21):641,(39,38,20,20):657,(39,20,20,20):658,(20,37,20,20):656}
  if col==41 and raw in water:return{**animated(water[raw]),'role':'cave_plain_water'if water[raw]==635 else'freshwater_pond_cave_bank_'+str(water[raw])}
  if col==51 and raw==(64,64,64,64):return{**animated(179,'general_waterfall'),'role':'cave_native_vertical_waterfall'}
  return None
 for game in e.GAMES:
  data=e.source(cache,game);known=defaultdict(list)
  for r in active:
   if r['game']!=game or r['tileset']not in cave.SETS:continue
   if r.get('donor',{}).get('game')=='firered':continue
   if 'compact' in r['role']and r.get('parts',[{}])[0].get('donor',{}).get('game')!='emerald':continue
   c=e.cell_info(cache,game,data,r['tileset'],r['id'],r['quadrant']);known[e.identity(c)].append(r)
  for name,m in sorted(data['maps'].items()):
   if not isinstance(m,dict)or m.get('tileset')not in cave.SETS or name in SKIP or m.get('environment')!='CAVE':continue
   existing=[r for r in active if r['game']==game and r['tileset']==m['tileset']and r.get('map',name)==name];generic={(r['id'],r['quadrant'])for r in existing if r.get('x')is None};positions={(r['x'],r['y'])for r in existing if r.get('x')is not None};occ=defaultdict(list)
   for y in range(m['height']*2):
    for x in range(m['width']*2):
     b=m['blocks'][y//2*m['width']+x//2];q=y%2*2+x%2
     if(b,q)not in generic and(x,y)not in positions:occ[b,q].append([x,y])
   count=Counter()
   for(b,q),coords in occ.items():
    c=e.cell_info(cache,game,data,m['tileset'],b,q);matches=[r for r in known[e.identity(c)]if not r.get('sourceWhole32Profile')or catalog.lua_array(catalog.dict_at(data['sets'][m['tileset']]['blocks'],b+1))==r['sourceWhole32Profile']];arts={json.dumps(artwork(r),sort_keys=True):r for r in matches}
    if len(arts)==1:
     seed=next(iter(arts.values()));r={'game':game,'style':'gen3','map':name,'tileset':m['tileset'],'id':b,'quadrant':q,'sourceCells':coords,'sourceHash':c['sourceHash'],'sourceFiles':data['fingerprints'][m['tileset']],'sourceCollision':c['collision'],'sourcePriority':[bool(z.get('priority'))for z in c['attributes']],'sourcePalettes':[z.get('palette',1)for z in c['attributes']],'role':seed['role'],'status':'candidate','evidence':'Exact original16px pixels, movement byte, palette slots and priorities match one unambiguous reviewed Gen3 recipe. Candidate requires review in the complete Johto cave context before activation. No source geometry, warp, darkness, puzzle or event changes.','reviewedSourceTemplate':{'map':seed.get('map'),'tileset':seed['tileset'],'id':seed['id'],'quadrant':seed['quadrant']}};r.update(artwork(seed))
     if seed.get('sourceWhole32Profile'):r['sourceWhole32Profile']=seed['sourceWhole32Profile']
     candidates.append(r);count['candidate_cells']+=len(coords)
    elif explicit(c):
     art=explicit(c);r={'game':game,'style':'gen3','map':name,'tileset':m['tileset'],'id':b,'quadrant':q,'sourceCells':coords,'sourceHash':c['sourceHash'],'sourceFiles':data['fingerprints'][m['tileset']],'sourceCollision':c['collision'],'sourcePriority':[bool(z.get('priority'))for z in c['attributes']],'sourcePalettes':[z.get('palette',1)for z in c['attributes']],'status':'candidate','evidence':'Explicit native counterpart reviewed as a complete shape in actual native and source cave context. New stage: full-map visual review and live decoding required before activation. Source collision, invisible jump/fall rules, exit coordinates and HM requirements remain unchanged.'};r.update(art)
     if c['collision']==51:
      def is_fall(x,y):
       return 0<=y<m['height']*2 and e.cell_info(cache,game,data,m['tileset'],m['blocks'][y//2*m['width']+x//2],y%2*2+x%2)['collision']==51
      for x,y in coords:
       top,bottom=not is_fall(x,y-1),not is_fall(x,y+1);assert not(top and bottom);v=copy.deepcopy(r);v.update(animated(185 if top else 76 if bottom else 179,'general_waterfall'),x=x,y=y,sourceCells=[[x,y]]);v['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,v,packed,ROOT).tobytes());candidates.append(v)
     else:r['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,r,packed,ROOT).tobytes());candidates.append(r)
     count['candidate_cells']+=len(coords)
    else:
     count['held_cells']+=len(coords);key=(game,c['sourceHash'],c['collision'],tuple(c['tiles']),tuple(z.get('palette',1)for z in c['attributes']))
     if key not in held:held[key]={'game':game,'tileset':m['tileset'],'bid':b,'q':q,'raw':c['tiles'],'collision':c['collision'],'contexts':[],'ambiguous_recipes':len(arts),'image':cave.source_image(cache,game,data,c,m)}
     held[key]['contexts'].append({'map':name,'coords':coords})
   stats.append({'game':game,'map':name,'total':m['width']*m['height']*4,'remaining_before':sum(map(len,occ.values())),**count})
 (a.output/'candidates.json').write_text(json.dumps(candidates,indent=2));(a.output/'summary.json').write_text(json.dumps(stats,indent=2));records=[];images=[]
 for z in held.values():
  image=z.pop('image');records.append(z)
  if z['game']=='crystal':images.append((str(len(images))+' '+str(z['raw'])+' col'+str(z['collision'])+'\n'+z['contexts'][0]['map']+'\n'+str(z['contexts'][0]['coords'][:3])+' recipes'+str(z['ambiguous_recipes']),image))
 for start in range(0,len(images),35):cave.contact(a.output/('remaining-'+str(start//35)+'.png'),'Remaining Johto cave cells: exact source artwork and context',images[start:start+35])
 (a.output/'held.json').write_text(json.dumps(records,indent=2));print(json.dumps({'candidate_rows':len(candidates),'candidate_cells':sum(len(r['sourceCells'])for r in candidates),'held_unique_crystal':len(images),'maps':stats}))
 for name in('BURNED_TOWER_B1F','DRAGONS_DEN_1F','DARK_CAVE_BLACKTHORN_ENTRANCE','UNION_CAVE_1F','ICE_PATH_1F','ICE_PATH_B3F','WHIRL_ISLAND_LUGIA_CHAMBER','TOHJO_FALLS'):
  preview.map_preview(cache,a.output,'crystal',name,'crystal-'+name,active+candidates,packed,2,ROOT)
 if a.validate:
  assert not held,'Unresolved cave shapes remain'
  for r in candidates:r['status']='reviewed';r['evidence']=r['evidence'].replace('Candidate requires review in the complete Johto cave context before activation.','Reviewed in the complete Johto cave context.').replace('New stage: full-map visual review and live decoding required before activation.','Complete source/native shape family and full-map context reviewed; live source and donor hashes checked.')
  proof=e.validate_batch(candidates,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=a.output),ROOT)
  for s in stats:
   rendered=preview.map_preview(cache,a.output,s['game'],s['map'],s['game']+'-'+s['map'],active+candidates,packed,1,ROOT);assert rendered['visible_cells']==rendered['replaced_occurrences'],s
  (a.output/'proof.json').write_text(json.dumps({'live':proof,'maps':stats,'new_cells':sum(len(r['sourceCells'])for r in candidates)},indent=2))
  if a.activate:write_rows(ROOT/'mappings/johto_cave_finish.lua',candidates)
if __name__=='__main__':main()
