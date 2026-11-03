"""Review complete native-size Crystal counterparts for Hoenn architecture.

Only newly reviewed source keys are emitted. Source layouts and entrances are
read-only; whole native modules keep their original pixels and transparent
outside corners. Inventory uses actual logical SVML bodies, not unused slots.
"""
from __future__ import annotations
import argparse,copy,json,re,struct,zlib
from collections import Counter,defaultdict
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import catalog,preview
from reverse_common import ROOT,ReverseReview
from reverse_oldale_review import mask_piece
from reverse_kanto_review import exterior

GAMES=('ruby','sapphire','emerald')
PAIRS=('general__rustboro','general__slateport','general__mauville','general__fortree','general__lilycove','general__mossdeep','general__sootopolis','general__ever_grande','general__pacifidlog','general__battle_frontier_outside_east','general__battle_frontier_outside_west')
TARGET=ROOT/'mappings/reverse_gen2_hoenn_city_complete.lua'

def key(r):return r['game'],r['tileset'],r['id']

class Review(ReverseReview):
 def __init__(self):
  super().__init__('gen2-hoenn-city-complete',GAMES)
  self.prior={};self.counts=Counter();self.contexts=defaultdict(list);self.groups=[];self.contracts=[]
  modules=dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(ROOT/'main.lua').read_text()))
  for module in modules:
   if ROOT/module==TARGET:continue
   for row in preview.read_reviewed(ROOT/module):
    if row['game']in GAMES and row['style']=='gen2':
     assert key(row)not in self.prior
     self.prior[key(row)]=row
 def source(self,k):
  game,pair,mid=k;c=self.imp.cell_index(game)[pair,mid]
  return preview.native_donor(self.cache,dict(game=game,tileset=pair,id=mid,hash=c['pixel_sha256']),self.packed)
 def inventory(self):
  for game in GAMES:
   for name,spec in self.imp.table(game,'gba/native/manifest')['layouts'].items():
    if spec['pair']not in PAIRS:continue
    raw=(self.cache/game/'data/generated/gba/native'/spec['file']).read_bytes();b=raw if raw[:4]==b'SVML'else zlib.decompress(raw)
    pw,ph,w,h=struct.unpack_from('<HHHH',b,6);w,h=w or pw,h or ph;at=16+b[14]*b[15]*2
    for y in range(h):
     for x in range(w):
      mid=struct.unpack_from('<H',b,at+4*(y*pw+x))[0];k=game,spec['pair'],mid
      if mid<512 or k in self.prior:continue
      self.counts[k]+=1
      if len(self.contexts[k])<4:self.contexts[k].append(dict(map=name,x=x,y=y))
  grouped=defaultdict(list)
  for k,n in self.counts.items():
   c=self.imp.cell_index(k[0])[k[1:]]
   signature=(k[1],c['pixel_sha256'],c.get('behavior'),json.dumps(c['layer_sha256'],sort_keys=True))
   grouped[signature].append(k)
  for sig,keys in grouped.items():
   self.groups.append(dict(pair=sig[0],keys=sorted(keys),occurrences=sum(self.counts[k]for k in keys),sourceHash=sig[1],sourceBehavior=sig[2]))
  self.groups.sort(key=lambda g:(g['pair'],-g['occurrences'],g['keys']))
  for i,g in enumerate(self.groups):g['index']=i
  report=dict(status='review inventory; not a runtime validation',source_keys=len(self.counts),source_occurrences=sum(self.counts.values()),groups=self.groups,contexts=[dict(game=k[0],pair=k[1],id=k[2],count=n,contexts=self.contexts[k])for k,n in self.counts.most_common()])
  (self.out/'inventory.json').write_text(json.dumps(report,indent=2)+'\n')
  return report
 def contacts(self):
  font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',12)
  for pair in PAIRS:
   groups=[g for g in self.groups if g['pair']==pair]
   for start in range(0,len(groups),96):
    batch=groups[start:start+96];image=Image.new('RGB',(1536,960),'#18212b');draw=ImageDraw.Draw(image)
    for i,g in enumerate(batch):
     x=(i%12)*128;y=(i//12)*120;k=g['keys'][0]
     draw.text((x+3,y+2),f"{g['index']}: {k[2]} x{g['occurrences']}",font=font,fill='white')
     draw.text((x+3,y+18),k[0]+f" +{len(g['keys'])-1}",font=font,fill='#ccd2da')
     image.paste(self.source(k).resize((64,64),Image.Resampling.NEAREST),(x+4,y+37))
    image.save(self.out/f"{pair}-{start//96:02}.png")
 def map_sources(self,names):
  for game in ('emerald',):
   for name in names:
    im,_,_,_=self.imp.gba(game,name);im.save(self.out/(name+'-source.png'))
 def emit(self,group,art,evidence):
  assert group['keys']
  for game,pair,mid in group['keys']:
   assert(game,pair,mid)not in self.prior
   self.row(game,pair,mid,'gen2',art,evidence)

 def house_modules(self):
  from reverse_gen2_hoenn_city_buildings_finish import Review as Legacy
  from reverse_hoenn_review import ground_ref
  field=ground_ref(self,'gen2');arts={};model=Image.new('RGBA',(64,64))
  for y in range(4):
   for x in range(4):
    a=Legacy.house_module(self,1 if y<2 and x==2 else x,y,window=x==2 and y==2,clear_half_window=x==3 and y==2)
    arts[x,y]=a;model.paste(self.render(a),(x*16,y*16))
  outside=exterior(model,set(self.gb_image(field).get_flattened_data())|{(222,255,222,255)})
  masked={}
  for (x,y),a in arts.items():
   mask=[(x*16+px,y*16+py)not in outside for py in range(16)for px in range(16)]
   masked[x,y]=mask_piece(self,a,mask,field,y<2)
   native=self.render(a);actual=self.render(masked[x,y])
   assert all(actual.getpixel((px,py))==native.getpixel((px,py))for py in range(16)for px in range(16)if mask[py*16+px])
  return masked
 def bind_building(self,name,dest,origin,matrix,arts,description,entry_cells=None):
  ox,oy=origin;w,h=len(matrix[0]),len(matrix);assert all(len(row)==w for row in matrix)
  for game,prefix in (('ruby','RU_'),('sapphire','SA_'),('emerald','EM_')):
   source_map=prefix+name;target=prefix+(dest[game]if isinstance(dest,dict)else dest)if dest is not None else prefix+name+'__CLOSED_'+str(ox)+'_'+str(oy)
   spec=self.imp.table(game,'gba/native/manifest')['layouts'][source_map];pair=spec['pair']
   raw=(self.cache/game/'data/generated/gba/native'/spec['file']).read_bytes();b=raw if raw[:4]==b'SVML'else zlib.decompress(raw)
   pw,ph,tw,th=struct.unpack_from('<HHHH',b,6);at=16+b[14]*b[15]*2
   actual=[[struct.unpack_from('<H',b,at+4*((oy+y)*pw+ox+x))[0]for x in range(w)]for y in range(h)]
   assert actual==matrix,('Whole building source layout changed',game,name,actual)
   warps=[a for a in self.imp.table(game,'gba/warps')[source_map]if (a['destMap']==target if dest is not None else ox<=a['x']<ox+w and oy<=a['y']<oy+h)]
   if entry_cells is None:assert len(warps)==1 and ox<=warps[0]['x']<ox+w and warps[0]['y']==oy+h-1,('Source entrance differs',target,warps)
   else:assert {(a['x']-ox,a['y']-oy)for a in warps}==set(entry_cells),('Source entrances differ',target,warps)
   originals=[];new=[];image=Image.new('RGBA',(w*16,h*16));joined=image.copy()
   for y,row in enumerate(matrix):
    for x,mid in enumerate(row):
     k=game,pair,mid;a=arts[x,y];cell=self.imp.cell_index(game)[pair,mid];originals.append(dict(id=mid,hash=cell['pixel_sha256'],behavior=cell['behavior']))
     image.paste(self.source(k),(x*16,y*16))
     if k not in self.prior:
      candidate=self.rows.get((game,'gen2',pair,mid,None))
      if candidate:
       assert self.render(candidate).tobytes()==self.render(a).tobytes() and candidate.get('overMask')==a.get('overMask'),('Conflicting shared building module',k)
      else:self.row(game,pair,mid,'gen2',a,description+' Every native source cell is bound to its full per-cartridge RGBA and behavior; the complete source matrix and original entrance are independently checked. Source collision, actor positions, events and layout remain unchanged.')
      new.append(mid);used=self.rows[(game,'gen2',pair,mid,None)]
     else:used=self.prior[k]
     joined.paste(self.render(used),(x*16,y*16))
   image.save(self.out/(target+'-source.png'));joined.save(self.out/(target+'-gen2.png'))
   self.contracts.append(dict(game=game,map=source_map,destination=target,origin=origin,source_matrix=matrix,original_entrance=warps[0]if warps else None,original_entrances=warps,native_pixel_scale=1,source_cells=originals,new_source_ids=sorted(set(new)),source_layout_sha256=catalog.sha(raw)))
 def slateport_named_house(self):
  # All three original source houses use the same complete64x64 construction;
  # their source window occupies one16px cell, so retain the entire original
  # native16x8 window pair there and clear its old half from the side cap.
  matrix=[[704,705,705,706],[712,713,713,714],[720,724,721,722],[32,732,19,34]]
  self.bind_building('SLATEPORT_CITY',dict(ruby='SLATEPORT_CITY_HOUSE1',sapphire='SLATEPORT_CITY_HOUSE1',emerald='SLATEPORT_CITY_NAME_RATERS_HOUSE'),(4,16),matrix,self.house_modules(),
   'Whole Slateport Name Rater house counterpart at its complete original64x64 size. Original Crystal New Bark roof caps, full doorway and full16x8 window pair retain1:1 pixel scale. Both roof rows and both facade rows remain complete; no fractional resizing, cut window panels or truncated doorway. Existing released primary wall/base cells remain registered unchanged. Only connected exterior ground is removed from the foreground, with the selected native Crystal lawn behind the roof corners.')
 def sootopolis_modules(self):
  from reverse_gen2_hoenn_city_buildings_finish import Review as Legacy
  contract=json.loads((ROOT.parent/'.work/tileshift-reverse-gen2-hoenn-outdoor-complete/native-limestone-floor-contract.json').read_text())
  base=contract['art']['donor'];gray=base['palettes'][0]
  roles=[['roof_nw','roof_n','roof_ne'],['roof_sw','roof_s','roof_se'],['wall_w','window','wall_e'],['base_w','door','base_e']]
  arts={};model=Image.new('RGBA',(48,64))
  for y,row in enumerate(roles):
   for x,role in enumerate(row):
    art=Legacy.modern_house_module(self,role)
    if y>=2:
     for part in art['parts']:part['donor']['palettes']=[copy.deepcopy(gray)for _ in range(8)]
    arts[x,y]=art;model.paste(self.render(art),(x*16,y*16))
  outside=exterior(model,{(222,255,222,255)})
  output={}
  for (x,y),art in arts.items():
   mask=[(x*16+px,y*16+py)not in outside for py in range(16)for px in range(16)]
   output[x,y]=mask_piece(self,art,mask,base,y<2)
   original=self.render(art);actual=self.render(output[x,y])
   assert all(original.getpixel((px,py))==actual.getpixel((px,py))for py in range(16)for px in range(16)if mask[py*16+px])
  self.sootopolis_floor_ref=copy.deepcopy(base)
  return output
 def sootopolis_flat_houses(self):
  matrix=[[587,588,589],[525,526,602],[533,534,535],[541,542,543]]
  self.bind_building('SOOTOPOLIS_CITY','SOOTOPOLIS_CITY_HOUSE2',(44,3),matrix,self.sootopolis_modules(),
   'Complete Sootopolis flat-roof house counterpart at the original48x64 size and original doorway. Intact Crystal Saffron gray roof caps, native complete16px door and native New Bark complete16x8 window pair keep1:1 pixels; only one ordinary middle roof/wall column is omitted, never a unique cap, doorway frame or window. Original Crystal DAY gray palette0 supplies the pale limestone facade, preserving every original native glyph. The separately reviewed complete Crystal CAVE2q0 stone floor in that same native gray palette supplies outside corners, matching Sootopolis729 rather than adding grass. All retained native building pixels are asserted exact and the roof foreground is transparent only outside its complete silhouette.')

 def town_model(self,width,roof_rows=2,door=1,windows=(2,),modern=False,gray=False,base=None,roof_palette=None):
  from reverse_gen2_hoenn_city_buildings_finish import Review as Legacy
  from reverse_hoenn_review import ground_ref
  field=base or ground_ref(self,'gen2');arts={};height=roof_rows+2;model=Image.new('RGBA',(width*16,height*16))
  gray_colors=self.sootopolis_floor_ref['palettes'][0]if gray else None
  for y in range(height):
   for x in range(width):
    edge='w'if x==0 else'e'if x==width-1 else''
    if y<roof_rows:
     sx=0 if x==0 else 48 if x==width-1 else 16;sy=0 if y==0 else 16 if y==roof_rows-1 else 8
     origin=(128,128,'SAFFRON_CITY')if modern else(192,32,'NEW_BARK_TOWN')
     art=self.composite(None,self.gb_rect('crystal',origin[2],origin[0]+sx,origin[1]+sy,16,16),'reverse_gen2_city_complete_'+('modern'if modern else'wood')+'_roof')
    elif modern:
     role=('wall_'+edge if edge else'window'if x in windows else'wall')if y==roof_rows else'door'if x==door else'base_'+edge if edge else'base'
     art=Legacy.modern_house_module(self,role)
    else:
     if y==roof_rows:art=Legacy.house_module(self,0 if x==0 else 3 if x==width-1 else 1,2,window=x in windows,clear_half_window=x==width-1)
     else:art=Legacy.house_module(self,1 if x==door else 0 if x==0 else 3 if x==width-1 else 2,3)
    if roof_palette is not None and y<roof_rows:
     for part in art['parts']:
      ref=part['donor'];pals=preview.palette_set(self.imp.table('crystal','palettes'),self.imp.table('crystal','maps')[ref['map']],'DAY');pals[6]=copy.deepcopy(roof_palette);ref['palettes']=pals
    if gray and y>=roof_rows:
     for part in art['parts']:part['donor']['palettes']=[copy.deepcopy(gray_colors)for _ in range(8)]
    arts[x,y]=art;model.paste(self.render(art),(x*16,y*16))
  outside_colors={(222,255,222,255)}
  if not modern:outside_colors|=set(self.gb_image(ground_ref(self,'gen2')).get_flattened_data())
  outside=exterior(model,outside_colors);output={}
  for (x,y),art in arts.items():
   mask=[(x*16+px,y*16+py)not in outside for py in range(16)for px in range(16)]
   output[x,y]=mask_piece(self,art,mask,field,y<roof_rows)
   before,after=self.render(art),self.render(output[x,y])
   assert all(before.getpixel((px,py))==after.getpixel((px,py))for py in range(16)for px in range(16)if mask[py*16+px])
  return output
 def slateport_fan_club(self):
  matrix=[[608,609,609,609,610],[576,577,577,577,578],[584,585,585,585,586],[592,593,594,595,596],[600,601,602,603,604]]
  self.bind_building('SLATEPORT_CITY','SLATEPORT_CITY_POKEMON_FAN_CLUB',(2,22),matrix,self.town_model(5,3,2,(1,3)),
   'Whole Slateport Pokemon Fan Club stays80x80 with its central entrance, both complete window pairs and full side walls. Complete original Crystal New Bark roof caps,16px door and16x8 window pairs keep native pixels. Only ordinary native8..23 roof-band and plain roof/wall repeats extend its original Gen2 modules to the source dimensions; no unique window, door frame or roof edge is cut or resized. Outside roof corners expose the selected native lawn and retain transparent foreground.')
 def sootopolis_domed_houses(self):
  field=self.sootopolis_floor_ref
  matrix=[[513,514,536],[521,522,523],[547,532,548],[555,540,556]]
  arts=self.town_model(3,2,1,(1,),True,True,field)
  self.bind_building('SOOTOPOLIS_CITY','SOOTOPOLIS_CITY_HOUSE1',(8,3),matrix,arts,
   'Whole Sootopolis raised-roof house keeps its complete48px facade, native-size roof edges, whole16px door and16x8 window pair in an original Crystal gray counterpart. The separate top16px roof ornament is supplied independently in its own source cell; surrounding limestone is not reclassified as roof. Complete original Saffron roof caps and full New Bark window glyphs retain1:1 pixels with the original Crystal DAY gray facade palette and independently reviewed limestone corner background.')
  # The original roof ornament occupies only one cell above the3x4 body;
  # its neighboring stone cells must retain their terrain counterpart.
  parts=self.gb_rect('crystal','SAFFRON_CITY',128,128,8,16)+self.gb_rect('crystal','SAFFRON_CITY',184,128,8,16,8)
  art=self.composite(None,parts,'reverse_gen2_city_native_compact_roof_cupola')
  im=self.render(art);outside=exterior(im,{(222,255,222,255)});mask=[(x,y)not in outside for y in range(16)for x in range(16)]
  art=mask_piece(self,art,mask,field,True)
  for game,prefix in (('ruby','RU_'),('sapphire','SA_'),('emerald','EM_')):
   k=game,'general__sootopolis',569
   assert k not in self.prior
   self.row(game,k[1],k[2],'gen2',art,'The complete Sootopolis one-cell rooftop cupola is an intact pair of original Crystal8px gray roof end-cap glyphs at1:1. Only ordinary middle roof fill is omitted to form the16px cap; no source roof tip, edge, facade, door or window is cut or reduced. Its actual source is the single roof ornament at9,2 above the separately reviewed48x64 main house body. Limestone side cells remain untouched and the cap foreground is transparent outside the complete silhouette. Native entrance, collisions, events and actor positions stay unchanged.')
  closed=[[520,528,536],[521,522,523],[529,516,531],[537,524,539]]
  closed_arts=self.town_model(3,2,-1,(1,),True,True,field)
  # This roof shares its already-reviewed native caps with the open house;
  # the two closed facade rows contain a window and plain base, never a door.
  self.bind_building('SOOTOPOLIS_CITY',None,(22,2),closed,closed_arts,
   'Whole Sootopolis closed decorative house reviewed at22,2 through24,5. Its complete48x64 body and separate roof cupola keep original native Crystal gray roof caps, one complete16x8 window pair and plain lower wall. No false door or new entrance is introduced. Original pixel scale, source solid-house collision and all source map/events remain unchanged; matching native limestone fills only outside roof corners.',[])

 def rustboro_school(self):
  from reverse_hoenn_review import ground_ref
  matrix=[[544,545,545,545,545,546,547],[552,553,553,553,553,554,555],[560,561,561,561,561,561,563],[568,570,570,551,570,570,571],[576,577,577,559,577,577,579]]
  # The four equal source windows receive full native panels at their actual
  # facade positions. A complete16x32 native metal grille forms the narrow
  # roof exhaust; no32px vent is downsized or sliced in half.
  arts=self.town_model(7,3,3,(1,2,4,5),True,False,ground_ref(self,'gen2'))
  for y in (0,1):
   art=copy.deepcopy(arts[6,y]);ref=self.gb_ref('crystal','RADIO_TOWER_5F',10,0 if y==0 else 2)
   art['parts'].append(dict(donor=ref,w=16,h=16,x=0,y=0))
   art['overMask']='1'*256;art['role']='reverse_gen2_city_complete_roof_metal_grille';arts[6,y]=art
  self.bind_building('RUSTBORO_CITY','RUSTBORO_CITY_POKEMON_SCHOOL',(24,30),matrix,arts,
   'Whole112x80 Rustboro school uses complete native Crystal Saffron roof caps, plain brick wall/base, four intact16x8 native window pairs and a full16px original doorway, preserving every original source facade position. Only ordinary native roof/wall sections repeat to keep the source size; no bitmap or unique panel is reduced. The complete native Crystal RadioTower16x32 framed metal grille/housing is repurposed as a narrow roof exhaust at original pixel size; every original frame, header and grille slot is retained. This avoids shrinking the existing32px exhaust asset. The original source roof exhaust footprint and entire front remain intact, with coherent selected ground outside the roof and true foreground transparency.')

 def lilycove_houses(self):
  matrix=[[557,558,558,559],[565,566,566,567],[573,574,575,589],[581,582,583,597]]
  blue=preview.palette_set(self.imp.table('crystal','palettes'),self.imp.table('crystal','maps')['OLIVINE_CITY'],'DAY')[6]
  self.bind_building('LILYCOVE_CITY','LILYCOVE_CITY_MOVE_DELETERS_HOUSE',(35,3),matrix,self.town_model(4,2,1,(2,),roof_palette=blue),
   'Whole64x64 Lilycove standard house counterparts retain original complete roofs, side frames,16px doorway and full native16x8 window pair. Original Crystal New Bark wooden house modules remain at1:1 pixels; the original Crystal Olivine DAY blue roof palette alone replaces the roof palette slot, while grass/walls/windows keep their native contexts. Only ordinary central roof repeats are used. Every roof corner exposes the selected native lawn, not an old Gen3 background. The complete Move Deleter source house and its unchanged native entry explicitly establish the shared house-family construction.')

 def portal_shadow(self):
  source=self.prior['ruby','general__cave',0]['donor'];ref=copy.deepcopy(source);ref.pop('monochrome',None)
  gray=preview.palette_set(self.imp.table('crystal','palettes'),self.imp.table('crystal','maps')['SAFFRON_CITY'],'DAY')[0]
  ref['palettes']=[copy.deepcopy(gray)for _ in range(8)]
  assert set(self.gb_image(ref).get_flattened_data())=={(58,58,58,255)}
  return ref
 def add_building_parts(self,arts,rects):
  # Split only plain bars and complete modular frame corners at destination
  # cell boundaries. Every original source pixel keeps its native size.
  for ref,sx,sy,w,h,dx,dy in rects:
   for ty in range(dy//16,(dy+h-1)//16+1):
    for tx in range(dx//16,(dx+w-1)//16+1):
     ax,ay=max(dx,tx*16),max(dy,ty*16);bx,by=min(dx+w,(tx+1)*16),min(dy+h,(ty+1)*16)
     art=arts[tx,ty]
     if art['kind']=='native':
      mask=art.get('overMask','0'*256);art=self.composite(art['donor'],[],art['role']);art['overMask']=mask;arts[tx,ty]=art
     art['parts'].append(dict(donor=copy.deepcopy(ref),srcX=sx+ax-dx,srcY=sy+ay-dy,w=bx-ax,h=by-ay,x=ax-tx*16,y=ay-ty*16))
     mask=list(art.get('overMask','0'*256))
     for py in range(ay-ty*16,by-ty*16):
      for px in range(ax-tx*16,bx-tx*16):mask[py*16+px]='1'
     art['overMask']=''.join(mask)
 def open_portal_parts(self,left,top,hole_width,hole_height):
  ref=self.gb_at('crystal','SAFFRON_CITY',9,11);door=self.gb_image(ref)
  assert door.getpixel((2,1))==(58,58,58,255)and door.getpixel((3,2))==(255,132,8,255)
  rects=[]
  def add(sx,sy,w,h,dx,dy):rects.append((ref,sx,sy,w,h,dx,dy))
  # Preserve all four complete2x3 original native frame corners. Ordinary
  # straight bars alone repeat to make a full-size open public doorway.
  add(2,1,2,3,left-2,top-3);add(12,1,2,3,left+hole_width,top-3)
  add(2,13,2,3,left-2,top+hole_height-3);add(12,13,2,3,left+hole_width,top+hole_height-3)
  for dx in range(0,hole_width,8):
   width=min(8,hole_width-dx);add(4,1,width,3,left+dx,top-3);add(4,13,width,3,left+dx,top+hole_height-3)
  for dy in range(0,hole_height-3,4):
   height=min(4,hole_height-3-dy);add(2,9,2,height,left-2,top+dy);add(12,9,2,height,left+hole_width,top+dy)
  return rects
 def slateport_museum(self):
  from reverse_hoenn_review import ground_ref
  matrix=[[776,777,778,778,779,780],[784,785,786,763,787,788],[792,793,794,771,795,796],[800,801,802,802,803,804],[808,809,810,810,811,812],[816,817,818,818,819,820]]
  field=ground_ref(self,'gen2');arts=self.town_model(6,3,-1,(),True,False,field)
  # Complete lower support row keeps the96px original height. Selected lawn
  # shows through the native pillar spacing, rather than old Gen3 floor.
  for x in range(6):arts[x,5]=self.native(field,'reverse_gen2_city_museum_native_lawn_below_supports');arts[x,5]['overMask']='0'*256
  wall=self.composite(None,self.gb_rect('crystal','SAFFRON_CITY',144,168,16,8)+self.gb_rect('crystal','SAFFRON_CITY',144,168,16,8,0,8),'reverse_gen2_city_complete_plain_brick_wall')
  # Original roof has two separate porthole windows, each across a cell seam.
  # Each receives one entire original native8x8 window, never half a pair.
  for x in (2,3):
   arts[x,1]['parts']+=self.gb_rect('crystal','NEW_BARK_TOWN',232,72,8,4,4,12)
   arts[x,2]['parts']+=self.gb_rect('crystal','NEW_BARK_TOWN',232,76,8,4,4,0)
  for x in (1,2,3,4):
   arts[x,3]=copy.deepcopy(wall);arts[x,3]['overMask']='0'*256
   arts[x,3]['parts']+=self.gb_rect('crystal','NEW_BARK_TOWN',232,72,16,8,0,0)
  # Two source columns share each completely empty doorway MID. Keep those
  # cells identically open; frame corners belong in the adjacent side cells.
  shadow=self.portal_shadow()
  for y in (4,5):
   for x in (2,3):arts[x,y]=self.native(shadow,'reverse_gen2_city_complete_open_door_shadow');arts[x,y]['overMask']='0'*256
  self.add_building_parts(arts,self.open_portal_parts(32,64,32,32))
  # Full ordinary post modules support the two outer facade corners. Their
  # original plain native wood grain is recolored with Crystal DAY gray.
  gray=preview.palette_set(self.imp.table('crystal','palettes'),self.imp.table('crystal','maps')['SAFFRON_CITY'],'DAY')[0]
  post=self.gb_at('crystal','SAFFRON_CITY',9,11);post['palettes']=[copy.deepcopy(gray)for _ in range(8)]
  supports=[]
  for x,px in ((0,8),(5,0)):
   for dy in range(0,16,4):
    supports.extend([(post,2,9,2,4,x*16+px,80+dy),(post,6,10,4,4,x*16+px+2,80+dy),(post,12,9,2,4,x*16+px+6,80+dy)])
  self.add_building_parts(arts,supports)
  self.bind_building('SLATEPORT_CITY','SLATEPORT_CITY_OCEANIC_MUSEUM_1F',(28,22),matrix,arts,
   'Whole Oceanic Museum stays96x96 with both original doorway cells at30/31,26. Complete original Crystal roof caps, facade and native8px roof porthole-window glyphs keep native pixels; both complete roof windows span their source cell seam without truncation. The32px-wide open doorway keeps a genuine native dark opening, all four complete original Crystal2x3 door-frame corners, and only repeated plain native frame bars; no closed door is stretched and no unique frame/window is cut. Plain native pillar modules retain the lower support row and expose the selected lawn between supports. Every complete source row, paired original entrance and per-cartridge native picture/behavior is guarded.',[(2,4),(3,4)])

 def save_candidate(self):
  def ordered(v):
   if isinstance(v,dict):return {k:ordered(v[k])for k in sorted(v,key=str)}
   if isinstance(v,list):return [ordered(x)for x in v]
   return v
  self.rows={k:ordered(self.rows[k])for k in sorted(self.rows)}
  self.write(self.out/'candidates.lua')
  (self.out/'building-contracts.json').write_text(json.dumps(dict(rows=len(self.rows),contracts=self.contracts),indent=2)+'\n')
 def preview_map(self,game,name):
  spec=self.imp.table(game,'gba/native/manifest')['layouts'][name];raw=(self.cache/game/'data/generated/gba/native'/spec['file']).read_bytes();b=raw if raw[:4]==b'SVML'else zlib.decompress(raw)
  pw,ph,w,h=struct.unpack_from('<HHHH',b,6);w,h=w or pw,h or ph;at=16+b[14]*b[15]*2
  before=Image.new('RGBA',(w*16,h*16));after=before.copy();rendered={};covered=0
  for y in range(h):
   for x in range(w):
    mid=struct.unpack_from('<H',b,at+4*(y*pw+x))[0];k=game,spec['pair'],mid
    original=self.source(k);before.paste(original,(x*16,y*16));row=self.rows.get((game,'gen2',spec['pair'],mid,None))or self.prior.get(k)
    if row:
     if k not in rendered:rendered[k]=self.render(row)
     tile=rendered[k];covered+=1
    else:tile=original
    after.paste(tile,(x*16,y*16))
  before.save(self.out/(game+'-'+name+'-before.png'));after.save(self.out/(game+'-'+name+'-after.png'))
  scale=1;canvas=Image.new('RGB',(w*32+56,h*16+110),'#18212b');d=ImageDraw.Draw(canvas);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
  d.text((18,12),game.title()+' / '+name+' / Crystal style',fill='white',font=font);d.text((18,38),'CPU development preview; native-size source pixels; GPU review pending. No actors.',fill='#c4cdd8',font=font)
  canvas.paste(before,(18,68));canvas.paste(after,(38+w*16,68));d.text((18,h*16+77),f'{covered}/{w*h} cells retiled ({covered/(w*h):.1%}); native art remains in unreviewed cells.',fill='#c4cdd8',font=font)
  canvas.save(self.out/(game+'-'+name+'-comparison.png'));return dict(game=game,map=name,replaced=covered,total=w*h)


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inventory',action='store_true');p.add_argument('--contacts',action='store_true');p.add_argument('--source-map',nargs='*',default=[]);p.add_argument('--validate',action='store_true');args=p.parse_args()
 r=Review();report=r.inventory();r.slateport_named_house();r.sootopolis_flat_houses();r.slateport_fan_club();r.sootopolis_domed_houses();r.rustboro_school();r.lilycove_houses();r.slateport_museum();r.save_candidate()
 if args.contacts:r.contacts()
 if args.source_map:r.map_sources(args.source_map)
 if args.validate:
  validation=r.validate();(r.out/'proof.json').write_text(json.dumps(validation,indent=2)+'\n')
 print(json.dumps(dict(keys=report['source_keys'],occurrences=report['source_occurrences'],groups=len(report['groups']))))

if __name__=='__main__':main()
