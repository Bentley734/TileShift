"""Native Gen3 office furniture; preserve unmatched telecom artwork exactly."""
import json
from johto_family_review import FamilyReview,ROOT
from native_room_parts import RoomParts
f=FamilyReview('pokecom',{'TILESET_POKECOM_CENTER'})
center=RoomParts(f.imp,'firered','FR_VIRIDIAN_CITY_POKEMON_CENTER_1F')
admin=RoomParts(f.imp,'firered','FR_CINNABAR_ISLAND_POKEMON_LAB_EXPERIMENT_ROOM')
floor=center.ref(641);wall=f.templates['johto_center_full_wall']['donor'];office=f.ref('firered','building__rom_082d4ecc',820)
for r in f.active:
 if r['game']=='red'and r['role'].startswith('household_'):f.templates.setdefault(r['role'],r)
computers=((3,26),(6,26),(6,28))
f.overrides={('crystal','POKECOM_CENTER_ADMIN_OFFICE_MOBILE',x,y)for ox,oy in computers for x in range(ox,ox+2)for y in range(oy,oy+2)}
native=f.imp.gba('firered',admin.map)[0]
background=set(native.crop((80,48,96,64)).get_flattened_data())
background|={v for v in native.crop((32,64,40,72)).get_flattened_data()if v[0]>v[1]>v[2]}
outside=admin.exterior(40,48,32,24,background)
pc={}
for yy in(0,1):
 for xx in(0,1):
  pc[xx,yy]=admin.masked(40+16*xx,48+16*yy,list(range(16)),list(range(16 if yy==0 else 8)),transparent_pixels=outside)
# User-approved exact original pixels are recolored when the special mobile
# kiosk has no matching native Gen3 geometry. Four source tones stay ordered.
PALETTES={
 1:[[238,244,252],[174,188,209],[103,121,145],[43,56,77]],
 2:[[255,231,201],[247,143,104],[161,72,64],[50,54,68]],
 4:[[225,239,247],[130,174,206],[71,103,145],[37,53,80]],
 5:[[255,247,185],[237,197,82],[151,126,54],[54,57,68]],
 6:[[236,255,181],[124,190,93],[59,117,70],[39,65,44]],
}
def handle(c,x,y,name,m,data):
 raw=tuple(c['tiles']);base=office if y>=24 else floor
 for ox,oy in computers:
  if ox<=x<ox+2 and oy<=y<oy+2:
   return f.composite(office,pc[x-ox,y-oy],'johto_pokecom_complete_admin_computer_'+str(x-ox)+'_'+str(y-oy))
 if raw==(129,129,129,129):return f.native(office,'johto_pokecom_admin_floor')
 if raw==(72,73,88,89):return f.template('johto_center_whole_lounge_chair',base)
 if raw==(34,35,50,51):return f.original('assets/original/interior-stairs/up.png',base,'johto_pokecom_stairs_up')
 if raw==(81,81,80,80):return f.template('household_rug_left'if x==6 else'household_rug_right',base)
 if raw in((174,175,190,191),(1,1,174,175)):return f.template('household_plant_head',base)
 if raw in((190,191,222,223),(206,207,222,223),(190,191,94,95)):return f.template('household_plant_base',base)
 if raw==(174,175,222,223):return f.original('assets/original/interior-flowerpot/flowerpot.png',base,'johto_pokecom_complete_small_planter')
 if raw==(52,52,36,36):return f.template('johto_center_nurse_counter',base)
 colors=[]
 for t,a in zip(raw,c['attributes']):
  if t in(129,130):colors.append([[173,222,230],[132,189,197],[99,156,165],[57,99,123]])
  elif t in(1,17):colors.append([[255,255,222],[239,239,181],[214,214,148],[181,181,115]])
  else:colors.append(PALETTES.get(a.get('palette',1),PALETTES[1]))
 return{'kind':'source_palette','sourceColors':colors,'role':'johto_pokecom_original_communications_geometry_gen3_palette'}
f.run(handle,('POKECOM_CENTER_ADMIN_OFFICE_MOBILE',),'Whole native Gen3 office computers, plants, lounge chairs, floor and stairs. Each native computer retains the complete monitor, tower and keyboard at original pixels; the surrounding native floor and separate48px desk are excluded, keeping the full32x24 device in its original32x32 source area. Unique mobile communications kiosk, large monitor, cables, controls, reflective window frames and counter bends retain every original source pixel in the user-approved Gen3 palette. No scaling or ROM-art asset files. Original administrative computer interactions, scientist positions, counter collision and exits stay unchanged.')
(f.out/'admin-computer-native-proof.json').write_text(json.dumps({'native_map':admin.map,'device_bounds':[40,48,32,24],'source_host_bounds':[32,32],'scale':1,'complete_monitor_tower_keyboard':True,'separate_native48px_desk_excluded':True,'outside_background_pixel_count':len(outside),'parts_by_quadrant':{str(k):len(v)for k,v in pc.items()}},indent=2))
