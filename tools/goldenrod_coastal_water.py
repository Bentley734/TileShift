"""Keep Goldenrod's sea, shore and marine boulders on one animated water family."""
from __future__ import annotations
import argparse,copy,json,os,re,sys
from pathlib import Path
from types import SimpleNamespace

HERE=Path(__file__).resolve()
W=next((p for p in [Path.cwd(),*HERE.parents]if(p/'.tools/python').is_dir()),Path.cwd())
sys.path.insert(0,str(W/'.tools/python'))
from PIL import Image,ImageDraw
import catalog,preview,gen2_extended_review as ext

MARKER=b'-- BEGIN REVIEWED GOLDENROD COHERENT COASTAL WATER'
GAMES=('gold','silver','crystal')
MAP='GOLDENROD_CITY'
MARINE={(x,y)for ox,oy in [(0,10),(0,22),(0,32)]for y in range(oy,oy+2)for x in range(ox,ox+2)}
RENAMES={'goldenrod_coastal_ocean_water_interior':'coastal_ocean_water_interior',
 'goldenrod_rocky_coast_east':'rocky_coast_east','goldenrod_rocky_coast_north':'rocky_coast_north',
 'goldenrod_rocky_coast_inward_northeast':'rocky_coast_inward_northeast'}

def key(row):return tuple(row.get(k)for k in ('game','style','tileset','map','id','quadrant','x','y'))

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--mod',type=Path,default=HERE.parents[1]);p.add_argument('--cache',type=Path,default=Path(os.environ['APPDATA'])/'pokemon-love2d')
 p.add_argument('--engine',type=Path,default=W/'.work/tileshift-engine-0420')
 p.add_argument('--output',type=Path,default=W/'.work/tileshift-mart-shelf-fix/water-audit/goldenrod')
 p.add_argument('--validate',action='store_true');p.add_argument('--activate',action='store_true')
 a=p.parse_args();mod,cache,out=a.mod.resolve(),a.cache.resolve(),a.output.resolve();out.mkdir(parents=True,exist_ok=True)
 target=mod/'mappings/goldenrod.lua';original=target.read_bytes();eol=b'\r\n'if b'\r\n'in original else b'\n'
 pristine=original.split(MARKER,1)[0]+b'return rows'+eol if MARKER in original else original
 assert pristine.rstrip().endswith(b'return rows')
 baseline=catalog.plain(catalog.LUA.execute(pristine.decode('utf-8-sig')))
 old={key(r):r for r in baseline};assert len(old)==len(baseline)
 template_rows=preview.read_reviewed(mod/'mappings/gen2_outdoor_extended.lua')
 packed,updates,scope,proofs={},[],[],{}
 for game in GAMES:
  template=next(r for r in template_rows if r['game']==game and r.get('map')=='OLIVINE_CITY'
    and r['role']=='coastal_ocean_water_interior'and r.get('donor',{}).get('id')==368)
  assert template['donor']['game']=='emerald'and template['donor']['tileset']=='general__petalburg'
  assert template['animation']['frames']==8 and template['animation']['bank']=='general_water'
  data=ext.source(cache,game);definition=data['maps'][MAP];blocks=catalog.lua_array(definition['blocks'])
  ocean_count,bank_count,boulder_count=0,0,0
  for prior in baseline:
   if prior['game']!=game or prior.get('map')!=MAP or prior['style']!='gen3':continue
   role=prior['role'];marine=(prior.get('x'),prior.get('y'))in MARINE and'whole_outcrop'in role
   if role not in RENAMES and not marine:continue
   row=copy.deepcopy(prior);x,y=row['x'],row['y']
   bid=blocks[y//2*definition['width']+x//2];q=y%2*2+x%2
   cell=ext.cell_info(cache,game,data,definition['tileset'],bid,q)
   assert (row['id'],row['quadrant'])==(bid,q)and row['sourceCells']==[[x,y]]
   assert row['sourceHash']==cell['sourceHash']and row['sourceFiles']==data['fingerprints'][definition['tileset']]
   assert row['sourceCollision']==cell['collision']
   assert row['sourcePriority']==[bool(z.get('priority'))for z in cell['attributes']]
   assert row['sourcePalettes']==[z.get('palette',1)for z in cell['attributes']]
   if role=='goldenrod_coastal_ocean_water_interior':
    assert prior['donor']['game']=='firered'and prior['donor']['id']==299 and cell['collision']==0x29
    row['donor']=copy.deepcopy(template['donor']);row['animation']=copy.deepcopy(template['animation'])
    row['animated']=True;row['role']=RENAMES[role];ocean_count+=1
    detail='Complete native Emerald368 ocean family replaces the unrelated FireRed299 family; all8 reviewed native frames match neighboring Emerald393/402 banks.'
   elif marine:
    assert row['kind']=='native_composite'and row.get('parts')and row['base']['id']==1 and cell['collision']==7
    row['base']=copy.deepcopy(template['donor']);row['animation']=copy.deepcopy(template['animation']);row['animated']=True
    row['role']='rocky_coast_goldenrod_sea_outcrop_'+str(q);boulder_count+=1
    detail='Only the three32x32 sea boulders at(0,10),(0,22),(0,32) use animated ocean behind every unchanged FireRed rock pixel. The11 mixed land/shore clusters retain their original reviewed ground.'
   else:
    assert row['donor']['game']=='emerald'and row['donor']['tileset']=='general__petalburg'and row['donor']['id']in(393,402,410)
    for field in ('bank','counter','hash','period','counterMax','frames','phase','manifestHash'):
     assert row['animation'][field]==template['animation'][field],field
    row['role']=RENAMES[role];bank_count+=1
    detail='The complete native Emerald bank pixels and all existing animation data stay unchanged; use the recognized rocky_coast role so the selected water style also reaches the bank.'
   row['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,row,packed,mod).tobytes())
   row['evidence']='Reviewed Goldenrod coherent coastal family. '+detail+' Source-fingerprinted exact cells, source collision, map layout, actor positions, Surf/fishing and scripts remain unchanged. Coastal role/category recognition keeps the selected water and native speed controls connected across ocean, bank and transparent rock corners.'
   updates.append(row);scope.append({'game':game,'map':MAP,'x':x,'y':y,'oldRole':role,'newRole':row['role']})
  assert(ocean_count,bank_count,boulder_count)==(56,26,12)
  proofs[game]={'ocean':ocean_count,'banks':bank_count,'marine_boulder_cells':boulder_count,
    'sourceFiles':data['fingerprints'][definition['tileset']],'native_ocean':template['donor'],'animation':template['animation']}
 assert len(updates)==282 and len({key(r)for r in updates})==282
 live=ext.validate_batch(updates,SimpleNamespace(cache=cache,engine=a.engine,output=out),mod)if a.validate else None
 changed={key(r):r for r in updates};body,compact=ext.write_compact(updates,None)
 footer='''local function seaKey(row)return table.concat({row.game,row.style,row.tileset,row.map or '',row.id,row.quadrant,row.x or '',row.y or ''},':')end
local seaUpdates=(function()
'''+body+'''end)()
local seaIndex={}for i,row in ipairs(rows)do seaIndex[seaKey(row)]=i end
for _,row in ipairs(seaUpdates)do local i=assert(seaIndex[seaKey(row)],'Goldenrod coastal source key missing');rows[i]=row end
return rows
'''
 result=pristine.rstrip()[:-len(b'return rows')]+MARKER+eol+footer.replace('\n',eol.decode()).encode()
 expanded=catalog.plain(catalog.LUA.execute(result.decode('utf-8-sig')))
 expected={key(r):changed.get(key(r),r)for r in baseline}
 assert len(expanded)==len(baseline)and{key(r):r for r in expanded}==expected
 # Honest native/default artwork previews; selected-style behavior is validated
 # through the actual Flora/category path by the native GPU review.
 before=[r for r in baseline if r['game']=='crystal'];after=[r for r in expanded if r['game']=='crystal']
 other=[]
 modules=list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(mod/'main.lua').read_text(encoding='utf-8-sig'))))
 for relative in modules:
  if Path(relative).name.startswith('reverse')or relative=='mappings/goldenrod.lua':continue
  for r in preview.read_reviewed(mod/relative):
   if r['game']=='crystal'and r['style']=='gen3'and r.get('map',MAP)==MAP:other.append(r)
 previews={}
 for label,rows in [('before',other+before),('after',other+after)]:
  previews[label]=preview.map_preview(cache,out,'crystal',MAP,label,rows,packed,1,mod)
  image=Image.open(out/(label+'-after-native.png'))
  image.crop((0,0,8*16,36*16)).resize((8*16*2,36*16*2),Image.Resampling.NEAREST).save(out/(label+'-coast.png'))
 water_before=next(r for r in before if r['role']=='goldenrod_coastal_ocean_water_interior')
 water_after=changed[key(water_before)]
 rock_before=next(r for r in before if (r.get('x'),r.get('y'))==(0,10))
 rock_after=changed[key(rock_before)]
 canvas=Image.new('RGB',(8*96,4*96+36),'#18232d');draw=ImageDraw.Draw(canvas)
 for line,row in enumerate([water_before,water_after,rock_before,rock_after]):
  frames=preview.replacement_frames(cache,row,packed,mod)
  for frame,pixels in enumerate(frames):canvas.paste(pixels.resize((96,96),Image.Resampling.NEAREST),(frame*96,36+line*96))
 draw.text((4,4),'Default water / corrected water / grass-backed rock / corrected rock: all8 native frames',fill='white')
 canvas.save(out/'native-frames.png')
 (out/'candidates.json').write_text(json.dumps(updates,indent=2)+'\n',encoding='utf-8')
 (out/'scope.json').write_text(json.dumps(scope,indent=2)+'\n',encoding='utf-8')
 report={'status':'reviewed_coherent_goldenrod_coast','changed_records':282,'per_game':proofs,'mapping_rows':len(baseline),
  'unrelated_records_unchanged':len(baseline)-282,'live_decoder':live,'compact':compact,'previews':previews,
  'source_mapping_before_sha256':catalog.sha(original),'source_mapping_after_sha256':catalog.sha(result)}
 if a.activate:target.write_bytes(result)
 (out/'proof.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'rows':282,'live_decoder':live,'activated':a.activate,'mapping_sha256':catalog.sha(result)},indent=2))

if __name__=='__main__':main()
