"""Unscaled native room rectangles split into checked16px compositing parts."""
from pathlib import Path
from PIL import Image
import catalog,preview
from building_review import decode_layout
class RoomParts:
 def __init__(self,imports,game,map_id):
  self.imports,self.game,self.map=imports,game,map_id;root=imports.cache/game/'data/generated/gba/native';spec=imports.table(game,'gba/native/manifest')['layouts'][map_id];self.pair=spec['pair'];self.layout=decode_layout(root/spec['file']);self.index=imports.cell_index(game)
 def ref(self,mid):return{'game':self.game,'tileset':self.pair,'id':mid,'hash':self.index[self.pair,mid]['pixel_sha256']}
 def rect(self,sx,sy,w,h,x=0,y=0,layers=None):
  assert 0<w<=16 and 0<h<=16 and 0<=x<x+w<=16 and 0<=y<y+h<=16;parts=[]
  assert 0<=sx<sx+w<=self.layout['width']*16 and 0<=sy<sy+h<=self.layout['height']*16
  py=sy
  while py<sy+h:
   ph=min(sy+h-py,16-py%16);px=sx
   while px<sx+w:
    pw=min(sx+w-px,16-px%16);mid=self.layout['mids'][py//16*self.layout['width']+px//16];p={'donor':self.ref(mid),'srcX':px%16,'srcY':py%16,'w':pw,'h':ph,'x':x+px-sx,'y':y+py-sy}
    if layers:p.update(layers=layers,layerHashes={name:self.index[self.pair,mid]['layer_sha256'][name]for name in layers})
    parts.append(p);px+=pw
   py+=ph
  return parts
 def exterior(self,sx,sy,w,h,background):
  im=self.imports.gba(self.game,self.map)[0];bg=set(background);outside=set();queue=[]
  for yy in range(sy,sy+h):
   for xx in range(sx,sx+w):
    if(xx in(sx,sx+w-1)or yy in(sy,sy+h-1))and im.getpixel((xx,yy))in bg:outside.add((xx,yy));queue.append((xx,yy))
  for xx,yy in queue:
   for dx,dy in((1,0),(-1,0),(0,1),(0,-1)):
    px,py=xx+dx,yy+dy
    if sx<=px<sx+w and sy<=py<sy+h and(px,py)not in outside and im.getpixel((px,py))in bg:outside.add((px,py));queue.append((px,py))
  return outside
 def masked(self,sx,sy,columns,rows,x=0,y=0,background=(),transparent_pixels=None):
  """Keep exact native pixels; callers justify omitted repeated rows/columns."""
  assert 0<len(columns)<=16 and 0<len(rows)<=16 and columns==sorted(set(columns))and rows==sorted(set(rows));im=self.imports.gba(self.game,self.map)[0];spans=[];bg=set(background)
  def transparent(px,py):return(px,py)in transparent_pixels if transparent_pixels is not None else im.getpixel((px,py))in bg
  for ty,ry in enumerate(rows):
   tx=0
   while tx<len(columns):
    if transparent(sx+columns[tx],sy+ry):tx+=1;continue
    end=tx+1
    while end<len(columns)and columns[end]==columns[end-1]+1 and not transparent(sx+columns[end],sy+ry):end+=1
    previous=next((v for v in reversed(spans)if v['x']==tx and v['w']==end-tx and v['y']+v['h']==ty and v['sy']+v['h']==ry and v['sx']==columns[tx]),None)
    if previous:previous['h']+=1
    else:spans.append({'x':tx,'y':ty,'sx':columns[tx],'sy':ry,'w':end-tx,'h':1})
    tx=end
  parts=[]
  for v in spans:parts+=self.rect(sx+v['sx'],sy+v['sy'],v['w'],v['h'],x+v['x'],y+v['y'])
  assert len(parts)<=16
  return parts
