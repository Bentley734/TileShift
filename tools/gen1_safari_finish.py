"""Direct native Gen3 Safari terrain and complete rest-house modules."""
from gen1_family_review import FamilyReview
from native_room_parts import RoomParts
from johto_remaining_review import artwork
import preview
f=FamilyReview('safari',{'FOREST'})
safari=RoomParts(f.imp,'firered','FR_SAFARI_ZONE_WEST')
ground=safari.ref(1)
indigo=RoomParts(f.imp,'firered','FR_INDIGO_PLATEAU_EXTERIOR')
bg=set()
for mid in (1,8,9,16,17):bg.update(preview.native_donor(f.cache,indigo.ref(mid),f.packed).get_flattened_data())
outside=indigo.exterior(128,144,16,32,bg)
statue={dy:indigo.masked(128,144+dy*16,list(range(16)),list(range(16)),transparent_pixels=outside)for dy in (0,1)}
oldhouse=[r for r in f.active if r['game']=='red'and r.get('map')=='FUCHSIA_CITY'and r['role']=='architecture_home32'];assert len(oldhouse)==8
house={(r['x']-10,r['y']-26):artwork(r)for r in oldhouse}
def native(mid,role):return f.native(safari.ref(mid),'gen1_safari_'+role)
rock={
 (46,46,46,46):113,(30,30,46,46):105,
 (45,45,45,45):112,(47,47,47,47):114,(62,62,62,62):121,
 (48,29,29,45):104,(31,48,47,31):106,
 (45,61,61,62):120,(63,47,62,63):122,
 (62,14,14,45):178,(15,62,47,15):179,
}
water={
 (20,20,20,20):'freshwater_pond_interior',
 (73,73,20,20):'freshwater_pond_north_bank',
 (72,20,72,20):'freshwater_pond_west_bank',
 (20,74,20,74):'freshwater_pond_east_bank',
 (73,73,72,20):'freshwater_pond_northwest_bank',
 (73,73,20,74):'freshwater_pond_northeast_bank',
 (77,20,72,20):'freshwater_pond_northwest_bank',
 (73,20,20,20):'freshwater_pond_inward_northwest_bank',
 (20,78,20,74):'freshwater_pond_northeast_bank',
 (20,73,20,20):'freshwater_pond_north_johto_410',
}
def handle(c,x,y,name,m,data):
 raw=tuple(c['tiles'])
 for w in m.get('warps',[]):
  if 'HOUSE'not in w.get('destMap',''):continue
  ox,oy=w['x']-1,w['y']-1
  if ox<=x<ox+4 and oy<=y<oy+2:return house[x-ox,y-oy]|{'role':'gen1_safari_complete_native_rest_house'}
 if raw in rock:return native(rock[raw],'complete_rock_profile_'+str(rock[raw]))
 if raw in water:return f.template(water[raw])
 if raw in((94,94,94,94),(94,94,52,52),(94,52,94,94),(52,94,94,94)):
  p=RoomParts(f.imp,'firered','FR_INDIGO_PLATEAU_EXTERIOR')
  return f.native(p.ref(650),'gen1_safari_complete_native_paved_path')
 if raw==(64,65,64,65):return native(137,'whole_native_stone_steps')
 if raw in((48,48,10,11),(26,27,75,76)):
  return f.composite(ground,statue[0 if raw[0]==48 else 1],'gen1_safari_whole_native_rhydon_statue')
 if raw==(66,66,67,67):return f.native(safari.ref(695),'gen1_safari_native_observation_railing')
 return None
f.run(handle,('SAFARI_ZONE_WEST','SAFARI_ZONE_CENTER','SAFARI_ZONE_NORTH','SAFARI_ZONE_EAST'),'Native Gen3 Safari rock profiles, complete pond banks, paths, statues and railings at original pixels. Original Safari steps, encounters, Surf, signs, items, exits and collision materials stay unchanged. Rest-house modules reviewed separately; no automatic architecture guess.')
