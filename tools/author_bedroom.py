"""Privately author complete native-source GSC bedroom decoration replacements."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from collections import Counter
import argparse,copy,hashlib,json,sys,zlib,struct
W=Path(__file__).resolve().parents[2]
CACHE=Path('C:/Users/LSDMTHC/AppData/Roaming/pokemon-love2d')
BASE=W/'.work/tileshift-v0444-compat-checkpoint/source-final'
OUT=Path(__file__).resolve().parent/'candidate'
S=W/'.work/tileshift-firegold'
ASSETS='assets/third_party/johto-hacks/bedroom-complete'
STEM='johto_bedroom_decorations'
GAMES=('gold','silver','crystal')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
rgba=lambda im:hashlib.sha256(im.convert('RGBA').tobytes()).hexdigest()
digest=lambda x:hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def write(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--mod-root',type=Path,default=BASE);args=parser.parse_args();root=args.mod_root.resolve()
 sys.path[:0]=[str(W/'.tools/python'),str(root/'tools')]
 import catalog,preview
 import interior_review
 interior_review.WORKSPACE=W
 from interior_review import Imports
 from center_mart_overhang_review import write_rows
 ledger=json.loads((W/'.work/tileshift-bedroom-fix/audit/bedroom-source-audit.json').read_text());assert ledger['missing_keys']==276
 imp=Imports(CACHE,W/'.work/tileshift-catalog');OUT.mkdir(parents=True,exist_ok=True);ad=OUT/ASSETS;ad.mkdir(parents=True,exist_ok=True)
 candidates=json.loads((W/'.work/tileshift-bedroom-fix/assets/candidate-inventory.json').read_text());assert all(sha(W/'.work/tileshift-bedroom-fix/assets'/r['file'])==r['png_sha256']for r in candidates['assets'])
 records=[];asset_files={}
 def save(name,im,source):
  p=ad/(name+'.png');im.save(p);assert Image.open(p).convert('RGBA').tobytes()==im.tobytes()
  records.append(dict(file=p.name,png_sha256=sha(p),rgba_sha256=rgba(im),native_size=list(im.size),opaque_pixels=sum(p[3]>0 for p in im.get_flattened_data()),source=source,pixel_scale=1))
  asset_files[p.name]=sha(p)
  return dict(asset=ASSETS+'/'+p.name,assetFileHash=sha(p),assetPixelHash=rgba(im))
 def hack(mid,layer='flat'):
  pair='083df884_083dfaf4';p=S/'crystaldust/pairs'/pair/(layer+'.png');a=Image.open(p).convert('RGBA');x,y=mid%16*16,mid//16*16
  return a.crop((x,y,x+16,y+16)),dict(hack='CrystalDust',rom_sha256=candidates['assets'][0]['source_rom_sha256'],pair=pair,mid=mid,layer=layer,source_png=str(p),source_png_sha256=sha(p),source_rect=[x,y,16,16])
 def gba(pair,mid):
  c=imp.cell_index('emerald')[pair,mid];ref=dict(game='emerald',tileset=pair,id=mid,hash=c['pixel_sha256']);im=preview.native_donor(CACHE,ref,imp.packed)
  return im,dict(donor=ref,source_rgba_sha256=rgba(im))
 def patch(im,rect):return im.crop(rect)
 green,greenproof=hack(69);yellow,yellowproof=hack(81);red,redproof=hack(137);blue,blueproof=hack(84);pink,pinkproof=gba('secret_base__secret_base_red_cave',780)
 materials={'RED':(red.crop((0,8,16,16)),dict(**redproof,material_rect=[0,8,16,8])),
            'BLUE':(blue.crop((8,0,16,8)),dict(**blueproof,material_rect=[8,0,8,8])),
            'YELLOW':(yellow,yellowproof),'GREEN':(green,greenproof)}
 portraits={}
 for gfx,name in [(143,'PIKACHU'),(149,'JIGGLYPUFF'),(151,'CLEFAIRY')]:
  p=CACHE/'emerald/data/generated/gba/ow'/f'{gfx}.rgba';mp=p.with_suffix('.meta');meta=mp.read_bytes();w,h,n=struct.unpack_from('<HHH',meta,8);raw=zlib.decompress(p.read_bytes());assert(w,h,n)==(16,16,1)
  im=Image.frombytes('RGBA',(w,h),raw);portraits[name]=(im,dict(game='emerald',graphics_id=gfx,identity=name+'_DOLL',frame=0,meta=str(mp),meta_sha256=sha(mp),rgba_file=str(p),rgba_file_sha256=sha(p),decoded_rgba_sha256=rgba(im),native_size=[w,h]))
 # Complete bed frame. Alternative surfaces are literal native Gen3 materials.
 br=next(r for r in candidates['assets']if r['id']=='crystaldust-whole-native-bed');bed=Image.open(W/'.work/tileshift-bedroom-fix/assets'/br['file']).convert('RGBA');assert bed.size==(24,34)
 beds={};bedrefs={}
 for bid,label in [(27,'FEATHERY'),(28,'PINK'),(29,'POLKADOT'),(30,'PIKACHU')]:
  im=bed.copy();surface=[];materialproof=None
  if bid in(28,29):
   material,materialproof=(pink,pinkproof)if bid==28 else(green,greenproof)
   for y in range(12,30):
    for x in range(2,22):
     if bed.getpixel((x,y))==(255,255,255,255):im.putpixel((x,y),material.getpixel(((x-2)%material.width,(y-12)%material.height)));surface.append([x,y])
  if bid==30:im.alpha_composite(portraits['PIKACHU'][0],(4,12));materialproof=portraits['PIKACHU'][1]
  beds[bid]=im;bedrefs[bid]=save('bed-'+label.lower()+'-whole24x34',im,dict(whole_frame=br,assembled_variant=label,material=materialproof,explicit_surface_pixels=surface,portrait_position=[4,12]if bid==30 else None,no_claim_preexisting_hack_variant=True))
 # Whole native green rug modules, literal surface materials retain color names.
 rugrec=next(r for r in candidates['assets']if r['id']=='cd-native-green-rug-96x48');rugb=Image.open(W/'.work/tileshift-bedroom-fix/assets'/rugrec['file']).convert('RGBA');rugs={};rugrefs={}
 for label,(material,proof)in materials.items():
  im=rugb.copy();mask=[]
  if label!='GREEN':
   for y in range(48):
    for x in range(96):
     if im.getpixel((x,y))==(107,197,107,255):im.putpixel((x,y),material.getpixel((x%material.width,y%material.height)));mask.append([x,y])
  rugs[label]=im;rugrefs[label]=save('rug-'+label.lower()+'-whole96x48',im,dict(native_modules=rugrec,material=proof,explicit_surface_pixels=mask,no_scaling=True,no_color_conversion=True))
 # Native paper portraits: preserve the complete source figures including ears/feet.
 # White material comes from the source bed's complete clear cloth8x8surface.
 paper=bed.crop((4,15,12,23));assert set(paper.get_flattened_data())=={(255,255,255,255)}
 posters={};posterrefs={}
 for name in ('PIKACHU','CLEFAIRY','JIGGLYPUFF'):
  im=Image.new('RGBA',(16,16));
  for y in range(16):
   for x in range(16):im.putpixel((x,y),paper.getpixel((x%8,y%8)))
  im.alpha_composite(portraits[name][0]);posters[name]=im;posterrefs[name]=save('poster-'+name.lower()+'-whole16',im,dict(native_portrait=portraits[name][1],paper_material=dict(source=br,rect=[4,15,8,8]),assembled_paper_poster=True))
 maprows=preview.read_reviewed(root/'mappings/gen2_facility_floor_audit.lua');maprow=next(r for r in maprows if r['game']=='crystal'and r.get('map')=='ELMS_LAB'and r['id']==9 and r['quadrant']==1)
 parts=[copy.deepcopy(p)for p in maprow['parts']if p['donor'].get('game')=='emerald'and p['donor'].get('tileset')=='building__brendans_mays_house'and p['donor']['id']in(592,597)]
 assert parts
 for p in parts:
  if p['donor']['id']==592:p['w']=15
 mapim=preview.replacement_image(CACHE,dict(kind='native_composite',parts=parts),imp.packed,root);assert mapim.getbbox()and mapim.getbbox()[2]-mapim.getbbox()[0]==15
 posters['TOWN_MAP']=mapim;posterrefs['TOWN_MAP']=save('poster-town-map-whole16',mapim,dict(original_approved_row=maprow,retained_native_parts=parts,complete_source_map=True))
 # Three distinct complete native plants, silhouettes retained at original size.
 plants={};plantrefs={}
 for bid,key in [(32,'cd-compact-potted-plant'),(33,'cd-potted-palm'),(34,'lc-compact-potted-plant')]:
  rec=next(r for r in candidates['assets']if r['id']==key);im=Image.open(W/'.work/tileshift-bedroom-fix/assets'/rec['file']).convert('RGBA');canvas=Image.new('RGBA',(16,32));canvas.alpha_composite(im,(0,32-im.height));plants[bid]=canvas;plantrefs[bid]=save('plant-'+str(bid)+'-whole16x32',canvas,dict(candidate=rec,anchor='bottom32',native_padding_only=True))
 # Background rows: exact source key guards; inactive styles stay map-scoped.
 floor=dict(game='firered',tileset='player_house',id=1,hash='eba7bafe3b8bf236ae3602939529c34fad55c66c94aed6bb6cb4681b08fe2af6')
 wall=dict(game='firered',tileset='player_house',id=40,hash='fd38c64864714cf6648e89dc3b28fa2ca879022c1d969074d488812eb23d6816')
 def guarded(game,mid,q,c):
  return dict(game=game,style='gen3',map='PLAYERS_HOUSE_2F',tileset='TILESET_PLAYERS_ROOM',id=mid,quadrant=q,sourceHash=c['sourceHash'],sourceCollision=c['sourceCollision'],sourcePriority=c['sourcePriority'],sourcePalettes=c['sourcePalettes'],sourceFiles=c['sourceFiles'],sourceCells={},status='reviewed',credit='CrystalDust by Sierraffinity and contributors; LiquidCrystal by Linkandzelda and Synyster Zeikku; native Pokemon Gen3 artwork from user-supplied ROMs.',sourceUrl='https://github.com/Sierraffinity/CrystalDust',evidence='Complete native artwork at1:1pixel scale. Explicit reviewed Gen3 cloth/portrait modules form named alternatives; these assembled combinations are not claimed as pre-existing hack items. Source map, collision, warps, interactions, script state and actors remain unchanged.')
 rows=[];fur=[];background_images={};cellassets={}
 # Stairs choice is independently supplied by the native-source reviewer.
 stairpath=W/'.work/tileshift-bedroom-fix/stairs-choice.json';stairs=json.loads(stairpath.read_text())if stairpath.exists()else None
 stairim=Image.open(stairs['file']).convert('RGBA')if stairs else None
 stairref=save('native-stair16',stairim,stairs)if stairim else None
 for compound,c in ledger['missing_source_keys'].items():
  game,_,mid,q=compound.split(':');mid,q=int(mid),int(q);r=guarded(game,mid,q,c);im=None;base=floor;role='';cellproof=None
  if 8<=mid<=19:
   color=('RED','BLUE','YELLOW','GREEN')[(mid-8)//3];local=(mid-8)%3;whole=rugs[color]
   if local==0 and q<2:base=wall;role='carpet_'+color.lower()+'_wall'
   else:
    if local==0:rect=(0 if q==2 else 16,0,16 if q==2 else 32,16)
    elif local==1:rect=(16+q%2*16,16+q//2*16,32+q%2*16,32+q//2*16)
    else:rect=(32+q%2*16,16+q//2*16,48+q%2*16,32+q//2*16)
    im=whole.crop(rect);cellproof=dict(whole=rugrefs[color],source_rect=list(rect));role='carpet_'+color.lower()+'_native_material'
  elif 27<=mid<=30:role='bed_'+str(mid)+'_native_floor'
  elif mid in(31,35,36,37):
   if q==0:name={31:'TOWN_MAP',35:'PIKACHU',36:'CLEFAIRY',37:'JIGGLYPUFF'}[mid];im=posters[name];base=wall;role='poster_'+name.lower()
   elif q==1:im=stairim;base=wall;role='native_room_stairs';cellproof=stairs
   else:role='poster_native_floor'
  elif mid in(32,33,34):
   if q%2==1:im=plants[mid].crop((0,q//2*16,16,q//2*16+16));cellproof=dict(whole=plantrefs[mid],source_rect=[0,q//2*16,16,16]);role='plant_'+str(mid)+'_native'
   else:role='plant_native_floor'
  else:raise AssertionError((mid,q))
  r['role']='johto_bedroom_'+role
  if role=='native_room_stairs':r['evidence']+=' Full compact original GSC stair geometry is explicitly retained, using actual native Gen3 material RGB; only uniform exterior top3rows reveal the selected bedroomwall.'
  if im is not None:
   key=(mid,q)
   if key not in cellassets:cellassets[key]=save('cell-'+str(mid)+'-'+str(q),im,dict(role=role,whole_source=cellproof,source_whole_asset=posterrefs.get({31:'TOWN_MAP',35:'PIKACHU',36:'CLEFAIRY',37:'JIGGLYPUFF'}.get(mid,''))if mid in(31,35,36,37)and q==0 else None))
   r.update(kind='third_party',base=base,**cellassets[key])
  else:r.update(kind='native',donor=base)
  r['compositionPixelHash']=rgba(preview.replacement_image(CACHE,r,imp.packed,OUT));rows.append(r)
  background_images[game,mid,q]=preview.replacement_image(CACHE,r,imp.packed,OUT)
 # Bounded bed foreground; source q0 anchor contracts guard active style.
 for game in GAMES:
  for mid in range(27,31):
   c=ledger['missing_source_keys'][f'{game}:TILESET_PLAYERS_ROOM:{mid}:0'];canvas=Image.new('RGBA',(32,48));canvas.alpha_composite(beds[mid],(0,14))
   for y in range(3):
    for x in range(2):
     tile=canvas.crop((x*16,y*16,x*16+16,y*16+16));key=('bed',mid,x,y)
     if key not in cellassets:cellassets[key]=save('overlay-bed-'+str(mid)+'-'+str(x)+'-'+str(y),tile,dict(whole=bedrefs[mid],placement=[0,62],source_canvas_crop=[x*16,y*16,16,16]))
     r=guarded(game,mid,0,c);r.update(kind='third_party',furniture='bed',anchorX=0,anchorY=4,x=x,y=3+y,frontY=96,role='johto_bedroom_full_native_bed_'+str(mid),**cellassets[key]);fur.append(r)
  for mid,color in [(9,'RED'),(12,'BLUE'),(15,'YELLOW'),(18,'GREEN')]:
   for x in(0,5):
    q=0 if x==0 else 1;c=ledger['missing_source_keys'][f'{game}:TILESET_PLAYERS_ROOM:{mid}:{q}']
    for y in(2,3):
     tile=rugs[color].crop((x*16,(y-1)*16,x*16+16,y*16));outside=preview.native_donor(CACHE,floor,imp.packed).copy();outside.alpha_composite(tile);tile=outside;key=('carpet',mid,x,y)
     if key not in cellassets:cellassets[key]=save('overlay-carpet-'+color.lower()+'-'+str(x)+'-'+str(y),tile,dict(whole=rugrefs[color],source_canvas_crop=[x*16,(y-1)*16,16,16],ground_only=True,opaque_backing=floor,reason='Opaque selected floor restores only the rug exterior margin over the generic cloth row.'))
     r=guarded(game,mid,q,c);r.update(kind='third_party',furniture='carpet',anchorX=x,anchorY=2,x=x,y=y,role='johto_bedroom_native_carpet_side_'+color.lower(),**cellassets[key]);fur.append(r)
 assert len(rows)==276 and len(fur)==120
 supers=[]
 if stairim:
  for game in GAMES:
   item=next(v for v in ledger['selected_rows'].values()if v['row']['game']==game and v['row']['id']==2 and v['row']['quadrant']==1);old=item['row'];r={k:copy.deepcopy(v)for k,v in old.items()if k.startswith('source')or k in('game','style','map','tileset','id','quadrant','status')};r.pop('sourceColors',None);r.update(kind='third_party',base=wall,role='johto_bedroom_actual_native_stair',credit=rows[0]['credit'],sourceUrl=rows[0]['sourceUrl'],evidence=rows[0]['evidence']+' The complete compact original GSC stair glyph is retained honestly; native Gen3 frame material replaces its old brown palette, and only uniform exterior top3rows are transparent to the selected bedroomwall. Larger32x32and48x32domestic GBA flights would require clipping or shrinking.',**stairref);r['compositionPixelHash']=rgba(preview.replacement_image(CACHE,r,imp.packed,OUT));supers.append(dict(module=item['module'],original_row=old,original_row_sha256=item['row_sha256'],candidate_row=r))
 write_rows(OUT/(STEM+'.lua'),rows);write(OUT/'rows.json',rows);write(OUT/'furniture-rows.json',fur);write(OUT/'supersessions.json',supers)
 write(ad/'provenance.json',dict(source='Actual supplied CrystalDust/LiquidCrystal and imported Emerald/FireRed native artwork',files=asset_files,candidates=records,assembly_limits='No scaling, colorconversion or generated pixels. Named bed/poster/color alternatives are explicitly assembled native-source composites.',source_ledger_sha256=sha(W/'.work/tileshift-bedroom-fix/audit/bedroom-source-audit.json')))
 # Honest native-sized full object variants, enlarged only for review.
 font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17);board=Image.new('RGB',(1100,980),'#18222d');dr=ImageDraw.Draw(board);dr.text((18,12),'All named native-source bedroom alternatives',font=font,fill='white')
 for i,(mid,im)in enumerate(beds.items()):
  x=15+i*270;dr.text((x,45),{27:'Feathery / CD native',28:'Pink / native cloth',29:'Polkadot / native dots',30:'Pikachu / whole portrait'}[mid],font=font,fill='white');up=im.resize((96,136),Image.Resampling.NEAREST);board.paste(up,(x,78),up)
 for i,(label,im)in enumerate(rugs.items()):
  x=15+i%2*545;y=245+i//2*195;dr.text((x,y),label+' CARPET / native modules + cloth',font=font,fill='white');up=im.resize((288,144),Image.Resampling.NEAREST);board.paste(up,(x,y+27),up)
 for i,(label,im)in enumerate(posters.items()):
  x=15+i*270;dr.text((x,685),label+' POSTER',font=font,fill='white');up=im.resize((64,64),Image.Resampling.NEAREST);board.paste(up,(x,715),up)
 for i,(mid,im)in enumerate(plants.items()):
  x=15+i*270;dr.text((x,830),{32:'MAGNAPLANT',33:'TROPICPLANT',34:'JUMBOPLANT'}[mid],font=font,fill='white');up=im.resize((32,64),Image.Resampling.NEAREST);board.paste(up,(x+160,815),up)
 board.save(OUT/'Named-bedroom-variants.png')
 integration=dict(mapping_stem=STEM,candidate=str(OUT/(STEM+'.lua')),mapping_sha256=sha(OUT/(STEM+'.lua')),background_rows=276,furniture_rows=str(OUT/'furniture-rows.json'),furniture_count=len(fur),supersessions=str(OUT/'supersessions.json'),assets=[dict(source=str(p),target=ASSETS+'/'+p.name,sha256=sha(p))for p in sorted(ad.iterdir())if p.is_file()],tools=[dict(source=str(Path(__file__).resolve()),target='tools/author_bedroom.py',sha256=sha(Path(__file__)))],pending_stair_choice=stairs is None,preview=str(OUT/'Named-bedroom-variants.png'))
 write(OUT/'integration.json',integration);print(json.dumps(dict(rows=len(rows),furniture=len(fur),supersessions=len(supers),pending_stair=stairs is None,integration_sha256=sha(OUT/'integration.json'))))
if __name__=='__main__':main()
