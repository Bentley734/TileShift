"""Existing native laboratory and school furniture at complete pixel scale."""
from johto_family_review import FamilyReview,ROOT
from native_room_parts import RoomParts
f=FamilyReview('labrooms',{'TILESET_LAB'},{'ELMS_LAB','EARLS_POKEMON_ACADEMY'})
f.overrides={(game,'ELMS_LAB',x,y)for game in('gold','silver','crystal')for x in range(6,9)for y in(3,4)}
lab=RoomParts(f.imp,'firered','FR_OAKS_LAB');school=RoomParts(f.imp,'emerald','EM_RUSTBORO_CITY_POKEMON_SCHOOL')
floor=f.ref('emerald','building__lab',514);wall=lab.ref(lab.layout['mids'][0]);sfloor=school.ref(school.layout['mids'][4*school.layout['width']]);swall=school.ref(school.layout['mids'][school.layout['width']])
def tile(room,sx,sy,base,role,layers=None):return f.composite(base,room.rect(sx,sy,16,16,layers=layers),'johto_labrooms_'+role)
def shelf(head,base):return f.template('johto_domestic_complete_single_bay_bookcase_'+str(0 if head else 1),base)
def handle(c,x,y,name,m,data):
 raw=tuple(c['tiles'])
 if raw in((2,2,18,18),(40,2,56,18),(2,41,18,57)):
  left=x==(3 if name=='EARLS_POKEMON_ACADEMY'else 4)
  return f.template('household_rug_left'if left else'household_rug_right',sfloor if name=='EARLS_POKEMON_ACADEMY'else floor)
 if name=='EARLS_POKEMON_ACADEMY':
  if 2<=x<=5 and y<=1:return tile(school,64+(x-2)*16,16+y*16,sfloor,'complete_school_blackboard_'+str(x-2)+'_'+str(y))
  if raw==(36,36,36,36):return f.native(sfloor,'johto_labrooms_school_floor')
  if raw==(5,7,3,4)and y==0:return shelf(True,swall)
  if raw in((5,7,19,20),(42,44,58,60)):
   parts=[]
   for sx,tx in((80,0),(104,8)):
    parts+=school.rect(sx,56,8,8,tx,0)+school.rect(sx,72,8,8,tx,8)
   return f.composite(sfloor,parts,'johto_labrooms_teacher_desk')
  if raw in((3,4,53,54),(3,4,19,20)):
   if y==1:return shelf(False,sfloor)
   parts=school.rect(80,64,8,16)+school.rect(104,64,8,16,8,0)
   return f.composite(sfloor,parts,'johto_labrooms_teacher_desk_base')
  if raw in((42,43,58,59),(43,44,59,60)):return tile(school,16,80,sfloor,'whole_student_desk_head')
  if raw==(64,65,80,81):return tile(school,16,96,sfloor,'whole_student_chair_base')
  if raw==(52,52,52,52):return f.native(swall,'johto_labrooms_school_wall')
  if raw==(52,52,36,36):return f.native(sfloor,'johto_labrooms_school_front_wall_floor')
  return None
 if 6<=x<=8 and y in(3,4):return tile(lab,128+(x-6)*16,64+(y-3)*16,floor,'complete_lab_table_'+str(x-6)+'_'+str(y-3),layers=['mid'])
 # Elm's wall computers retain complete bezels and desk feet.
 if raw==(1,1,17,17):return f.native(wall,'johto_labrooms_lab_wall')
 if raw==(5,7,3,4):return shelf(True,wall)
 if raw in((3,4,19,20),):return shelf(False,floor)
 if raw==(32,33,48,49):return f.template('johto_house_complete_window',wall)
 if raw==(34,35,50,51):return f.template('johto_complete_native_region_map',wall)
 if raw in((10,11,26,27),(12,13,28,29)):
  return tile(lab,32 if raw[0]==10 else 48,8,floor,'complete_wall_workstation_head',layers=['mid'])
 if raw in((37,38,16,16),(38,39,16,16)):
  if y==4 and 6<=x<=8:return tile(lab,128+(x-6)*16,80,floor,'complete_lab_table_foot_'+str(x-6),layers=['mid'])
  return tile(lab,32 if raw[0]==37 else 48,24,floor,'complete_wall_workstation_foot',layers=['mid'])
 if raw in((5,6,21,22),(6,6,22,22),(6,7,22,23)):
  xx=0 if raw[0]==5 else 2 if raw[1]==7 else 1
  return tile(lab,128+16*xx,64,floor,'complete_lab_table_head_'+str(xx),layers=['mid'])
 if raw==(38,38,16,16):return tile(lab,144,80,floor,'complete_lab_table_foot',layers=['mid'])
 if raw==(14,15,30,31):
  return f.template('johto_house_chair_right',floor)
 machines={(16,16,129,130):(32,16),(133,134,131,132):(16,16),(145,146,161,162):(32,32),(147,148,163,164):(16,32)}
 if raw in machines:
  sx,sy=machines[raw];return tile(lab,sx,sy,floor,'complete_research_workstation',layers=['mid'])
 return None
f.run(handle,('ELMS_LAB','EARLS_POKEMON_ACADEMY'),'Complete native FireRed laboratory furniture and Emerald Rustboro school counterparts. The native blackboard spans four original columns and keeps its complete frame and platform. Whole desk, chair, workstation, shelves, lab table, wall window and map modules use original pixel scale. Only repeated flat teacher-desk center columns are omitted; both outside frames and legs remain. Original professor, starter selection, healing, school text, collision and entry coordinates remain unchanged.')
