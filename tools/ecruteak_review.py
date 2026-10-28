"""Finalize original reference-led Gen3 buildings within native Ecruteak footprints."""
from __future__ import annotations
import argparse,copy,hashlib,json,os
from pathlib import Path
from types import SimpleNamespace
from PIL import Image,ImageDraw,ImageFont
import catalog,preview,gen2_extended_review as e
from newbark_building_review import lua
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'.work/tileshift-ecruteak-finish'
GENERATED=Path('C:/Users/LSDMTHC/.codex/generated_images/01a1779e-1657-7893-8b0a-94f8fb9ac828')
SPECS={
 'burned':('exec-91f2b53e-b409-4010-b528-a28013d656d6.png',19,44,(64,64)),
 'bell':('exec-dcf549ee-d4c1-498d-8f2b-eb69e459e8af.png',12,62,(64,128)),
 'theater':('exec-43bc4a35-a72e-4652-8a57-4833b3df0aca.png',20,0,(64,64)),
 'temple':('exec-83c38fa6-8ef7-4397-a712-bd2e43132d4b.png',16,0,(96,64)),
 'home':('exec-37366145-7a44-45e7-8027-3db076121103.png',18,158,(64,64)),
 'closed':('exec-92763e6e-3ddf-4119-b5b4-77eedce90f97.png',18,158,(64,64)),
 'intact':('exec-59dc8a25-4634-4617-9d21-0cb6e54d903c.png',18,0,(64,80)),
}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def finalize(generated=GENERATED):
 folder=ROOT/'assets/original/ecruteak-v2';folder.mkdir(parents=True,exist_ok=True);assets={};files={};art={};prompts={'initial':json.loads((OUT/'v2-prompts.json').read_text(encoding='utf-8')),'full_size':json.loads((OUT/'full-prompts.json').read_text(encoding='utf-8'))}if(OUT/'v2-prompts.json').exists()else json.loads((folder/'provenance.json').read_text(encoding='utf-8'))['prompt_history']
 for name,(file,factor,left,size)in SPECS.items():
  source=generated/file;im=Image.open(source).convert('RGBA');source_size=im.size;alpha=im.getchannel('A').point(lambda a:255 if a>=128 else 0);bounds=alpha.getbbox();im.putalpha(alpha);intermediate=size;box=(left,bounds[3]-intermediate[1]*factor,left+intermediate[0]*factor,bounds[3]);assert box[0]<=bounds[0]and box[2]>=bounds[2]and(box[1]<=bounds[1]or name=='bell')
  im=im.crop(box).resize(intermediate,Image.Resampling.NEAREST);steps=[]
  # Fill only exterior/plain repeating columns; every unique feature stays
  # unscaled and complete. The original source building width is retained.
  bx0,by0,bx1,by1=im.getchannel('A').getbbox();lp,rp=bx0,size[0]-bx1
  leftpos=bx0+3;rightpos=min(bx1-3,32 if name in('home','closed','theater')else bx1-4)
  xs=list(range(bx0,leftpos))+[leftpos-1]*lp+list(range(leftpos,rightpos))+[rightpos-1]*rp+list(range(rightpos,bx1));assert len(xs)==size[0]
  before=im;im=Image.new('RGBA',size)
  for x,sx in enumerate(xs):im.paste(before.crop((sx,0,sx+1,size[1])),(x,0))
  steps.append({'exterior_repeat_columns':[lp,rp],'source_columns':[leftpos-1,rightpos-1],'unique_features_unscaled':True})
  if name=='intact' and by0:
   ys=list(range(by0,12))+[11]*by0+list(range(12,size[1]));before=im;im=Image.new('RGBA',size)
   for y,sy in enumerate(ys):im.paste(before.crop((0,sy,size[0],sy+1)),(0,y))
   steps.append({'repeated_upper_roof_rows':by0,'complete_facade_unchanged':True})
  im=im.quantize(colors=32,method=Image.Quantize.FASTOCTREE,dither=Image.Dither.NONE).convert('RGBA');assert im.size==size and set(im.getchannel('A').get_flattened_data())<={0,255};sub=folder/name;sub.mkdir(exist_ok=True);p=sub/(name+'.png');im.save(p);files[p.relative_to(folder).as_posix()]=sha(p);assets[name]={}
  for y in range(size[1]//16):
   for x in range(size[0]//16):
    p=sub/f'cell-{x}-{y}.png';im.crop((x*16,y*16,x*16+16,y*16+16)).save(p);files[p.relative_to(folder).as_posix()]=sha(p);assets[name][x,y]={'asset':p.relative_to(ROOT).as_posix(),'assetFileHash':sha(p)}
  art[name]={'source_file':file,'source_sha256':sha(source),'generated_size':source_size,'visible_alpha_bounds':bounds,'crop_xyxy':box,'integer_reduction':factor,'intermediate_size':intermediate,'final_size':size,'extra_steps':steps,'processing':'Full original building width; complete visible design retained, except Bell Tower continues beyond original north map edge. Full roofs may overhang one row above unchanged source collision footprint; binary alpha128, uniform integer nearest reduction,32 colors without dithering. No fractional/runtime scaling.','rgba_sha256':catalog.sha(im.tobytes())}
 (folder/'provenance.json').write_text(json.dumps({'origin':'Original new designs made with built-in imagegen, then fitted to original source footprints','user_choice':'Generate our own Gen3-style replacements based on the supplied reference; retain recognizable colors, roof shapes and landmark features.','reference_artist':'MetalFlygon08 / SkidMarc25; style reference only, reference bitmaps are not distributed','reference_url':'https://imgur.com/gallery/testing-out-gen-3-style-tiles-johto-6A43Cji','creator_post':'https://www.reddit.com/r/PokemonRMXP/comments/yf90qb/full_johto_gen_3_tileset_tile_set_at_the_bottom/','prompt_history':prompts,'artwork':art,'files':files},indent=2)+'\n',encoding='utf-8');return assets,art
def instances(game):
 result=[{'art':'closed','rect':[x,y,4,3],'door':None,'destination':None}for x,y in((16,1),(12,9),(4,15),(12,15),(28,25))]
 result.extend([{'art':'temple','rect':[16,9,6,3],'door':[18,11],'destination':'ECRUTEAK_TIN_TOWER_ENTRANCE'},{'art':'home','rect':[12,25,4,3],'door':[13,27],'destination':'ECRUTEAK_ITEMFINDER_HOUSE'},{'art':'bell','rect':[36,0,4,8],'door':[37,7],'destination':'TIN_TOWER_1F'},{'art':'theater','rect':[22,19,4,3],'door':[23,21],'destination':'DANCE_THEATER'},{'art':'burned'if game=='crystal'else'intact','rect':[4,2,4,4]if game=='crystal'else[4,1,4,5],'door':[5,5],'destination':'BURNED_TOWER_1F'}]);return result
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--activate',action='store_true');parser.add_argument('--generated-dir',type=Path,default=GENERATED);args=parser.parse_args();assets,art=finalize(args.generated_dir);cache=Path(os.environ['APPDATA'])/'pokemon-love2d';active=[r for p in(ROOT/'mappings').glob('*.lua')if p.name!='ecruteak.lua'for r in preview.read_reviewed(p)];original=preview.read_reviewed(ROOT/'mappings/ecruteak.lua')if(ROOT/'mappings/ecruteak.lua').exists()else json.loads((OUT/'candidates.json').read_text(encoding='utf-8'));rows=[r for r in original if not r.get('asset')and not r['role'].startswith('architecture_')];packed={};ground=copy.deepcopy(next(r['base']for r in active if r.get('base',{}).get('tileset')=='general__petalburg'and r['base']['id']==1));proof=[];roofs=[]
 for game in e.GAMES:
  data=e.source(cache,game);m=data['maps']['ECRUTEAK_CITY']
  for inst in instances(game):
   name=inst['art'];ox,oy,w,h=inst['rect'];extra=1 if name in('home','closed','theater','temple')else 0;assert SPECS[name][3]==(w*16,(h+extra)*16)
   if inst['door']:
    assert any((z['x'],z['y'],z['destMap'])==(*inst['door'],inst['destination'])for z in m['warps'])
    anchor=[(inst['door'][0]-ox)*16+8,(inst['door'][1]-oy+1)*16];assert anchor==[40 if name=='temple'else 24,h*16]
   else:
    assert not any(ox<=z['x']<ox+w and oy<=z['y']<oy+h for z in m['warps']);anchor=None
   proof.append({'game':game,'map':'ECRUTEAK_CITY',**inst,'door_bottom_anchor_px':anchor,'rgba_sha256':art[name]['rgba_sha256'],'extra_top_rows':extra,'draw_rect':[ox,oy-extra,w,h+extra]})
   for dy in range(h):
    for dx in range(w):
     x,y=ox+dx,oy+dy;bid=m['blocks'][y//2*m['width']+x//2];q=y%2*2+x%2;c=e.cell_info(cache,game,data,m['tileset'],bid,q)
     r={'game':game,'style':'gen3','map':'ECRUTEAK_CITY','tileset':m['tileset'],'id':bid,'quadrant':q,'x':x,'y':y,'sourceCells':[[x,y]],'sourceHash':c['sourceHash'],'sourceFiles':data['fingerprints'][m['tileset']],'sourceCollision':c['collision'],'sourcePalettes':[a.get('palette',1)for a in c['attributes']],'sourcePriority':[bool(a.get('priority'))for a in c['attributes']],'kind':'original','base':copy.deepcopy(ground),'role':'ecruteak_original_'+name,'status':'reviewed','evidence':'Original Gen3 reference-led '+name+' artwork fits its complete original footprint. Full roof/chimney, doors, window frames and theater planters retained. Uniform integer nearest reduction only; full roofs retained, with one decorative collision-free top row where needed; exterior repeated columns match original building width without scaling unique features. Original door anchor, blocking, Headbutt trees, events and story scripts remain unchanged.',**assets[name][dx,dy+extra]};r['compositionPixelHash']=catalog.sha(preview.replacement_image(cache,r,packed,ROOT).tobytes());rows.append(r)
   if extra:
    for dx in range(w):
     x,y=ox+dx,oy-1;bid=m['blocks'][y//2*m['width']+x//2];q=y%2*2+x%2;c=e.cell_info(cache,game,data,m['tileset'],bid,q)
     r={'game':game,'style':'gen3','map':'ECRUTEAK_CITY','tileset':m['tileset'],'id':bid,'quadrant':q,'x':x,'y':y,'buildingY':oy,'sourceHash':c['sourceHash'],'sourceFiles':data['fingerprints'][m['tileset']],'sourceCollision':c['collision'],'sourcePalettes':[a.get('palette',1)for a in c['attributes']],'sourcePriority':[bool(a.get('priority'))for a in c['attributes']],'kind':'original','role':'roof_overhang','status':'reviewed','evidence':'User permits one decorative upper row above unchanged building collisions. Draw alpha roof above existing trees and actors; preserve underlying reviewed art, Headbutt and all source interactions.',**assets[name][dx,0]};roofs.append(r)
  report=preview.map_preview(cache,OUT,game,'ECRUTEAK_CITY',game+'-v2-complete',active+rows,packed,2,ROOT,roof_rows=roofs);assert report['replaced_occurrences']==report['visible_cells']==1440
 assert len(rows)==718 and len({(r['game'],r['x'],r['y'])for r in rows})==718
 live=e.validate_batch(rows,SimpleNamespace(cache=cache,engine=ROOT.parent/'.tools/engine-0395',output=OUT/'v2-live'),ROOT);(OUT/'v2-candidates.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');(OUT/'v2-building-model.json').write_text(json.dumps({'instances':proof,'artwork':art,'live':live,'roof_rows':len(roofs)},indent=2),encoding='utf-8')
 roof_text='-- One decorative row only; never used as a source tile replacement.\nreturn '+lua(roofs)+'\n';(OUT/'full-roof-catalog.lua').write_bytes(roof_text.encode())
 if args.activate:
  (ROOT/'lib/roof_catalog.lua').write_bytes(roof_text.encode())
  # The Itemfinder house already had positional native-home rows. Remove
  # just those36 one-line records before installing their original-art replacements.
  target=ROOT/'mappings/buildings_extended.lua';old=preview.read_reviewed(target);expected=[r for r in old if not(r.get('map')=='ECRUTEAK_CITY'and r.get('role')=='architecture_home48'and r.get('x')in range(12,16)and r.get('y')in range(25,28))]
  if len(old)!=len(expected):
   assert len(old)-len(expected)==36
   raw=target.read_bytes();lines=raw.splitlines(keepends=True);kept=[line for line in lines if not(b'["map"]="ECRUTEAK_CITY"'in line and b'["role"]="architecture_home48"'in line and b'Actual source destination:ECRUTEAK_ITEMFINDER_HOUSE.'in line)];assert len(lines)-len(kept)==36;target.write_bytes(b''.join(kept));assert preview.read_reviewed(target)==expected
  text='-- Complete Ecruteak: original reference-led Gen3 buildings and reviewed native terrain.\nlocal rows={}\nlocal function add(batch)for _,r in ipairs(batch)do rows[#rows+1]=r end end\n'
  for n in range(0,len(rows),20):text+='add((function()return '+lua(rows[n:n+20])+' end)())\n'
  (ROOT/'mappings/ecruteak.lua').write_bytes((text+'return rows\n').encode())
 if args.activate and(ROOT/'assets/original/bell-wide/provenance.json').exists():
  # Preserve the later user-approved side extension when regenerating other
  # Ecruteak buildings. Reuse its checked final art; never revert to Bell v2.
  import subprocess,sys
  subprocess.run([sys.executable,str(ROOT/'tools/bell_width_review.py'),'--activate','--reuse-assets'],cwd=ROOT,check=True)
 print(json.dumps({'rows':len(rows),'live':live,'coverage':'1440/1440 each GSC','activated':args.activate}))
if __name__=='__main__':main()
