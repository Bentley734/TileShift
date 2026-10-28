"""Private native/source room context for the Johto shop finishing pass."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from johto_family_review import FamilyReview,ROOT
from gen2_cave_review import contact
f=FamilyReview('mart',{'TILESET_MART'})
out=ROOT.parent/'.work/tileshift-johto-mart-context';out.mkdir(exist_ok=True)
scenes={'firered':['FR_VIRIDIAN_CITY_MART','FR_CELADON_CITY_DEPARTMENT_STORE_1F','FR_CELADON_CITY_DEPARTMENT_STORE_2F','FR_CELADON_CITY_DEPARTMENT_STORE_3F','FR_CELADON_CITY_DEPARTMENT_STORE_4F','FR_CELADON_CITY_DEPARTMENT_STORE_5F','FR_CELADON_CITY_DEPARTMENT_STORE_ROOF','FR_CELADON_CITY_DEPARTMENT_STORE_ELEVATOR'],'crystal':['AZALEA_MART','GOLDENROD_DEPT_STORE_1F','GOLDENROD_DEPT_STORE_2F','GOLDENROD_DEPT_STORE_3F','GOLDENROD_DEPT_STORE_5F','GOLDENROD_DEPT_STORE_6F','GOLDENROD_DEPT_STORE_ROOF','GOLDENROD_DEPT_STORE_ELEVATOR','RADIO_TOWER_1F','RADIO_TOWER_2F','RADIO_TOWER_3F','RADIO_TOWER_4F','RADIO_TOWER_5F','GOLDENROD_MAGNET_TRAIN_STATION']}
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',12)
scenes['firered']+=['FR_OAKS_LAB','FR_SILPH_CO_3F']
for game,names in scenes.items():
 for name in names:
  image,cells,pictures,meta=(f.imp.gba if game=='firered'else f.imp.gb)(game,name)
  image.resize((image.width*3,image.height*3),Image.Resampling.NEAREST).save(out/(name+'.png'))
  if game=='firered':contact(out/(name+'-cells.png'),name,[(str(k),v)for k,v in sorted(pictures.items())])
  canvas=image.resize((image.width*4,image.height*4),Image.Resampling.NEAREST);d=ImageDraw.Draw(canvas)
  for y in range(image.height//16):
   for x in range(image.width//16):
    d.rectangle((x*64,y*64,x*64+63,y*64+63),outline='#777777');d.text((x*64+1,y*64+1),str(x)+','+str(y),font=font,fill='black',stroke_width=1,stroke_fill='white')
  canvas.save(out/(name+'-grid.png'))
