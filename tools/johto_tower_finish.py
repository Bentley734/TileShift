"""Explicit pagoda floor-puzzle geometry and complete compact wood structures."""
import json,re
from pathlib import Path
from PIL import Image
import catalog,preview
from johto_family_review import FamilyReview,ROOT
from native_room_parts import RoomParts
f=FamilyReview('tower',{'TILESET_TOWER'});dojo=RoomParts(f.imp,'firered','FR_SAFFRON_CITY_DOJO');floor=dojo.ref(704);void=dojo.ref(0);folder=ROOT/'assets/original/interior-tower-modules';folder.mkdir(exist_ok=True);files={};source=(ROOT/'assets/original/sprout-tower/tower.png');roof=Image.open(source).convert('RGBA');post_path=ROOT/'assets/original/interior-railpost/railpost.png';post=Image.open(post_path).convert('RGBA');grid_path=ROOT/'assets/original/interior-lattice/lattice.png';grid=Image.open(grid_path).convert('RGBA')
def save(name,im):
 path=folder/name;im.save(path);files[name]=catalog.sha(path.read_bytes());return path.relative_to(ROOT).as_posix()
def repeat(im):
 out=Image.new('RGBA',(16,16))
 for yy in(0,8):
  for xx in(0,8):out.paste(im,(xx,yy))
 return out
for name,box in(('roof-west',(2,8,10,16)),('roof-east',(54,8,62,16))):
 motif=roof.crop(box);tile=repeat(motif)
 if name=='roof-east':
  # Stagger repeating shingle courses by4 native pixels; do not create a
  # continuous artificial seam down the whole roof plane.
  tile.paste(motif.crop((4,0,8,8)),(0,8));tile.paste(motif,(4,8));tile.paste(motif.crop((0,0,4,8)),(12,8))
 save(name+'.png',tile)
ridge=Image.new('RGBA',(16,16),post.getpixel((4,10)));ridge.alpha_composite(repeat(post.crop((0,8,8,16))));save('ridge.png',ridge)
ridge_end=ridge.copy()
for xx in(0,8):ridge_end.paste(post.crop((0,0,8,8)),(xx,8))
save('ridge-end.png',ridge_end)
fringe=Image.new('RGBA',(16,16),(0,0,0,255))
for xx in(0,8):fringe.alpha_composite(post.crop((0,8,8,16)),(xx,0))
save('fringe.png',fringe)
wall=Image.new('RGBA',(16,16));wall.paste(post,(0,0));wall.paste(post,(8,0));save('wall.png',wall)
broken=wall.copy();broken.paste(Image.new('RGBA',(8,8)),(8,8));save('broken-wall.png',broken)
vertical=Image.new('RGBA',(16,16));vertical.paste(post.crop((2,0,6,16)),(4,0));save('vertical-wall.png',vertical)
painting_path=ROOT/'assets/original/interior-painting/painting.png'
if painting_path.exists():
 painting=Image.open(painting_path).convert('RGBA')
 for name,box,px,rx in(('painting-left',(0,0,8,16),8,0),('painting-right',(8,0,16,16),0,8)):
  cell=Image.new('RGBA',(16,16));cell.paste(post,(rx,0));cell.paste(painting.crop(box),(px,0));save(name+'.png',cell)
for r in f.active:
 if r['game']=='red'and r['role'].startswith('household_'):f.templates.setdefault(r['role'],r)
def asset(name,base,role):return f.original('assets/original/interior-tower-modules/'+name+'.png',base,role)
def level(name):
 if name.endswith('_ROOF'):return 10
 m=re.search(r'_(B?)(\d+)F$',name)
 return(-1 if m[1]else 1)*int(m[2])if m else 0
def stairs(c,x,y,name,m):
 warp=next((w for w in m['warps']if w['x']==x and w['y']==y),None)
 if not warp:return None
 direction='up'if level(warp['destMap'])>level(name)else'down';return f.original('assets/original/interior-stairs/'+direction+'.png',floor,'johto_tower_stairs_'+direction)
def lattice(raw):
 name='lattice-'+'-'.join(map(str,raw));path=folder/(name+'.png')
 if not path.exists():
  out=Image.new('RGBA',(16,16))
  for q,tile in enumerate(raw):
   xx,yy=q%2*8,q//2*8
   if tile in(10,11,26,27):
    piece=Image.new('RGBA',(8,8),(0,0,0,255));piece.alpha_composite(grid)
    if tile in(10,11):piece.paste(Image.new('RGBA',(8,3),(0,0,0,255)),(0,0))
    if tile in(10,26):piece.paste(Image.new('RGBA',(3,8),(0,0,0,255)),(0,0))
    out.paste(piece,(xx,yy))
   elif tile in(86,87):out.paste(post.crop((2,8,5,16)),(xx+(5 if tile==86 else 0),yy))
  save(name+'.png',out)
 else:files[path.name]=catalog.sha(path.read_bytes())
 return asset(name,floor,'johto_tower_open_wooden_lattice')
def handle(c,x,y,name,m,data):
 raw=tuple(c['tiles']);col=c['collision']
 if raw==(1,1,1,1)and col in(0,96):return f.native(void,'johto_tower_original_invisible_path_or_fall')
 if raw==(2,2,2,2):return f.native(floor,'johto_tower_wooden_floor_with_original_movement')
 if raw in((37,53,37,53),(52,53,52,53)):return asset('roof-east',floor,'johto_tower_east_roof_plane')
 if raw in((22,36,22,36),(22,6,22,6)):return asset('roof-west',floor,'johto_tower_west_roof_plane')
 if raw in((80,81,80,81),(80,80,80,80)):return asset('ridge',floor,'johto_tower_complete_roof_ridge')
 if raw==(80,81,82,83):return asset('ridge-end',floor,'johto_tower_complete_roof_ridge_end')
 if raw==(94,94,1,1):return asset('fringe',void,'johto_tower_original_platform_fringe_over_void')
 if col in(114,122):return stairs(c,x,y,name,m)
 if raw==(17,17,33,33):return asset('wall',floor,'johto_tower_complete_log_rail')
 if raw==(65,49,65,49):return asset('vertical-wall',floor,'johto_tower_vertical_log_rail')
 if raw==(17,17,64,32):return asset('broken-wall',floor,'johto_tower_broken_log_rail')
 if raw==(4,5,20,21):
  donor=f.ref('emerald','general__cave',514);hashes=f.imp.cell_index('emerald')['general__cave',514]['layer_sha256'];return f.composite(floor,[{'donor':donor,'layers':['mid'],'layerHashes':{'mid':hashes['mid']},'w':16,'h':16}],'johto_tower_complete_rubble_rock')
 if raw in((34,35,50,51),(74,75,90,91),(66,67,90,91),(40,41,56,57)):return f.native(dojo.ref(726),'johto_tower_complete_statue_head')
 if raw in((18,19,54,55),(76,92,54,55),(42,43,58,59)):return f.native(dojo.ref(734),'johto_tower_complete_statue_base')
 if raw in((7,8,23,24),(8,9,24,25),(7,9,23,25)):
  return f.template('household_rug_right'if raw[0]==8 else'household_rug_left',floor)
 pillar={(45,46,61,62):(0,0),(46,47,62,63):(1,0),(60,62,77,78):(0,1),(11,44,78,79):(1,1),(1,44,78,79):(1,1),(77,78,93,94):(0,2),(78,79,94,95):(1,2)}
 if raw in pillar:
  xx,yy=pillar[raw];return f.original('assets/original/interior-pillar/cell-'+str(xx)+'-'+str(yy)+'.png',floor,'johto_tower_complete_support_pillar_'+str(xx)+'_'+str(yy))
 if raw in((17,72,33,88),(73,17,89,33)):return asset('painting-left'if raw[0]==17 else'painting-right',floor,'johto_tower_complete_bellsprout_painting')
 if any(t in(10,11,26,27)for t in raw)and all(t in(10,11,26,27,3,7,70,71,86,87)for t in raw):return lattice(raw)
 return None
f.run(handle,('SPROUT_TOWER_1F','SPROUT_TOWER_2F','SPROUT_TOWER_3F','BURNED_TOWER_1F','TIN_TOWER_6F','TIN_TOWER_ROOF','ECRUTEAK_GYM','CIANWOOD_GYM'),'Explicit complete Gen3 timber surfaces, rails, support pillar, rubble, stair and statue counterparts reviewed against the original tower geometry. All black gaps, hidden floor and fall flags stay unchanged; original puzzle movement remains authoritative. Stair direction follows the actual original warp destination. Roof shingle modules are unscaled8px texture crops from the approved original Sprout Tower asset; east courses are staggered4 native pixels. New lattice holes stay visibly open. Original Sprout3F text identifies the complete framed picture as Bellsprout; its painting and read coordinates are preserved. No source collision, warp, ladder, NPC, puzzle or story event is edited.')
(folder/'provenance.json').write_text(json.dumps({'origin':'Unscaled modular derivatives of original Gen3 artwork; no imported ROM pixels.','sources':{'sprout_roof':{'path':source.relative_to(ROOT).as_posix(),'sha256':catalog.sha(source.read_bytes()),'crops':{'roof-west':[2,8,10,16],'roof-east':[54,8,62,16]}},'post':{'path':post_path.relative_to(ROOT).as_posix(),'sha256':catalog.sha(post_path.read_bytes())},'painting':{'path':painting_path.relative_to(ROOT).as_posix(),'sha256':catalog.sha(painting_path.read_bytes())},'lattice':{'path':grid_path.relative_to(ROOT).as_posix(),'sha256':catalog.sha(grid_path.read_bytes())}},'scale':1,'composition':'Exact8px modules repeated, with explicit black gap masks for each original lattice edge and transparent original floor cutouts. Complete painting and all four frame corners span two guarded original cells.','files':files},indent=2))
