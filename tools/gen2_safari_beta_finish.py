"""Guarded G/S Safari beta terrain; unavailable ROM graphics stay native."""
from pathlib import Path
import argparse,collections,copy,json,os,re
from types import SimpleNamespace
import catalog,preview,gen2_extended_review as review
from review import lua_value
from johto_remaining_review import artwork
from lupa.lua54 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]
TARGET='SAFARI_ZONE_BETA'
MARKER='REVIEWED SAFARI BETA NATIVE TERRAIN'
FLOOR_MARKER='REVIEWED SAFARI BETA BIN FLOOR'

def footer(path,marker,code):
 text=path.read_text(encoding='utf-8')
 start='-- BEGIN '+marker
 if start in text:text=text.split(start,1)[0]
 else:
  assert text.rstrip().endswith('return rows')
  text=text[:text.rfind('return rows')]
 path.write_text(text.rstrip()+'\n'+start+'\n'+code+'\n-- END '+marker+'\nreturn rows\n',encoding='utf-8')

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
 p.add_argument('--cache',type=Path,default=Path(os.environ['APPDATA'])/'pokemon-love2d')
 p.add_argument('--engine',type=Path,required=True);p.add_argument('--validate',action='store_true')
 a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 data={g:review.source(a.cache,g) for g in ['gold','silver','crystal']}
 paths=[ROOT/'mappings/gen2_kanto_special_rooms_finish.lua',ROOT/'mappings/park.lua',ROOT/'mappings/johto_park_finish.lua',ROOT/'mappings/gen2_outdoor.lua',ROOT/'mappings/gen2_outdoor_extended.lua']
 active=[r for path in paths if path.exists() for r in preview.read_reviewed(path)]
 crystal={(r['id'],r['quadrant']):r for r in active if r.get('game')=='crystal' and r.get('map')==TARGET and r.get('style')=='gen3'}
 assert len(crystal)==68
 ground=copy.deepcopy(crystal[2,0]['donor'])
 known=collections.defaultdict(list)
 for row in active:
  g=row.get('game')
  if g not in ['gold','silver'] or row.get('style')!='gen3' or row.get('tileset')!='TILESET_PARK':continue
  if row.get('map')==TARGET:continue
  try:cell=review.cell_info(a.cache,g,data[g],'TILESET_PARK',row['id'],row['quadrant'])
  except Exception:continue
  known[g,review.identity(cell)].append(row)
 added=[];held=[];packed={}
 colors={1:[[112,192,160],[144,208,176],[88,168,136],[56,112,96]],4:[[112,192,160],[160,200,216],[88,128,168],[40,64,96]]}
 for game in ['gold','silver']:
  md=data[game]['maps'][TARGET];groups=collections.defaultdict(list)
  for index,bid in enumerate(md['blocks']):
   for q in range(4):groups[bid,q].append([index%md['width']*2+q%2,index//md['width']*2+q//2])
  for (bid,q),positions in sorted(groups.items()):
   try:cell=review.cell_info(a.cache,game,data[game],'TILESET_PARK',bid,q)
   except Exception as error:
    held.append(dict(game=game,map=TARGET,id=bid,quadrant=q,coordinates=positions,reason=str(error)));continue
   row=dict(game=game,style='gen3',map=TARGET,tileset='TILESET_PARK',id=bid,quadrant=q,
    sourceHash=cell['sourceHash'],sourceFiles=data[game]['fingerprints']['TILESET_PARK'],sourceCells=positions,
    sourceCollision=cell['collision'],sourcePriority=[bool(x.get('priority'))for x in cell['attributes']],
    sourcePalettes=[x.get('palette',1)for x in cell['attributes']],status='reviewed')
   if bid==47:
    row.update(kind='source_palette',role='park_preserved_complete_legacy_ornament',
     sourceColors=[colors[x.get('palette',1)]for x in cell['attributes']],
     evidence='Preserve every actual G/S legacy courtyard ornament pixel and its full original footprint. No verified full native counterpart exists for this older distinct graphic. Gen3 ground/blue-grey colors replace the old palette; no bank fragment, crop, guessed object or source mechanics change.')
   else:
    seed=crystal[bid,q];other=review.cell_info(a.cache,'crystal',data['crystal'],'TILESET_PARK',bid,q)
    if review.identity(cell)!=review.identity(other):
     choices=known.get((game,review.identity(cell)),[])
     preferred=[r for r in choices if r.get('map') in ['NATIONAL_PARK','NATIONAL_PARK_BUG_CONTEST']]
     choices=preferred or choices
     variants={json.dumps(artwork(r),sort_keys=True)for r in choices}
     assert len(variants)==1,(game,bid,q,'No unambiguous exact native counterpart')
     seed=choices[0]
    row.update(artwork(seed));row.update(role=seed['role'],reviewedSeed={k:seed.get(k)for k in ['game','map','tileset','id','quadrant']},
     evidence='Actual source tileset cell has the identical complete neutral pixels, collision, per8px palette slots and priority as this reviewed Park counterpart. Complete native grass, flowers, water, fences and full paired tree parts retain source layout, NPCs, warps, encounters and events. The unused map environment is not used to guess geometry.')
   row['compositionPixelHash']=catalog.sha(preview.replacement_image(a.cache,row,packed,ROOT).tobytes());added.append(row)
 assert len(added)==120 and sum(len(r['sourceCells'])for r in added)==1416
 added=json.loads(json.dumps(added,sort_keys=True))
 native_path=ROOT/'mappings/gen2_kanto_terrain_finish.lua'
 footer(native_path,MARKER,'for _,row in ipairs('+lua_value(added)+')do rows[#rows+1]=row end')
 fixed=[]
 for q in range(4):
  row=copy.deepcopy(crystal[47,q])
  if q==1:row['base']=copy.deepcopy(ground)
  else:row['donor']=copy.deepcopy(ground);row['role']='short_nonencounter_grass'
  row['evidence']='The Crystal beta courtyard uses the same verified plain ground as adjacent source block2. Keep the complete already-reviewed native litter-bin middle layer and its whole footprint; remove the unrelated curved shore/water background only. Source cells, collisions, palettes, priority, warps and events remain unchanged.'
  row['compositionPixelHash']=catalog.sha(preview.replacement_image(a.cache,row,packed,ROOT).tobytes());fixed.append(row)
 fixed=json.loads(json.dumps(fixed,sort_keys=True))
 code='local replacements='+lua_value(fixed)+'\nfor _,replacement in ipairs(replacements)do local found=0;for i,row in ipairs(rows)do if row.game==replacement.game and row.style==replacement.style and row.map==replacement.map and row.id==replacement.id and row.quadrant==replacement.quadrant then rows[i]=replacement;found=found+1 end end;assert(found==1,"Safari beta bin source changed")end'
 footer(ROOT/'mappings/gen2_kanto_special_rooms_finish.lua',FLOOR_MARKER,code)
 (a.output/'added.json').write_text(json.dumps(added,indent=2)+'\n');(a.output/'held.json').write_text(json.dumps(held,indent=2)+'\n');(a.output/'crystal-floor.json').write_text(json.dumps(fixed,indent=2)+'\n')
 proof={'status':'authored','new_rows':len(added),'guarded_gs_cells':1416,'preserved_missing_graphics_cells':sum(len(x['coordinates'])for x in held),'held':held,'crystal_floor_rows':4,'crystal_floor_cells':8,'no_new_assets_or_runtime_API':True,'source_layout_objects_warps_events_unchanged':True,'markers':[MARKER,FLOOR_MARKER]}
 paths=list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(ROOT/'main.lua').read_text())))
 runtime=LuaRuntime(unpack_returned_tuples=True);runtime.globals().paths=runtime.table_from(paths)
 runtime.globals().source=lambda name:(ROOT/name).read_text(encoding='utf-8-sig')
 total=runtime.execute('''local rows={};for _,path in ipairs(paths)do for _,row in ipairs(assert(load(source(path)))())do rows[#rows+1]=row end end
  local M=assert(load(source('lib/mapping.lua')))();local _,errors=M.index(rows);assert(#errors==0,table.concat(errors,'\\n'));return #rows''')
 proof.update(registered_rows=total,index_errors=0)
 if a.validate:
  proof['native_validation']=review.validate_batch(added+fixed,SimpleNamespace(cache=a.cache,engine=a.engine,output=a.output),ROOT)
  proof['status']='passed'
 (a.output/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
 print(json.dumps({k:v for k,v in proof.items()if k not in ['held','native_validation']}))

if __name__=='__main__':main()
