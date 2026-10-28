"""Gen3 ocean, harbour breakwater and pier; preserve the unmatched Fast Ship."""
from johto_family_review import FamilyReview
from native_room_parts import RoomParts
f=FamilyReview('port',{'TILESET_PORT'})
dock=RoomParts(f.imp,'firered','FR_SSANNE_EXTERIOR')
ship=((26,35,36,37),(20,20,38,39),(20,20,40,41),(20,20,42,20),(43,44,57,58),(45,45,58,51),(46,47,59,60),(48,50,61,62),(51,52,63,64),(53,16,65,66),(54,55,67,68),(56,20,69,20),(45,51,80,81),(70,71,82,82),(72,73,83,83),(73,74,84,44),(75,76,45,85),(77,78,86,87),(79,20,20,20),(20,88,20,20),(89,90,20,20),(90,91,20,20),(92,92,20,20),(93,94,20,20),(94,94,20,20),(95,20,20,20))
def handle(c,x,y,name,m,data):
 raw=tuple(c['tiles'])
 if raw==(20,20,20,20):return f.template('coastal_ocean_water_interior')
 if raw==(1,2,17,18):return f.template('rocky_coast_sea_rock_barrier')
 if raw in((5,5,5,5),(49,49,49,49)):return f.native(dock.ref(449),'johto_port_native_concrete_pier_floor')
 if raw==(3,4,30,31):return f.original('assets/original/interior-stairs/down.png',dock.ref(449),'johto_port_complete_passage_steps')
 if raw in ship:return None
 return None
f.run(handle,('OLIVINE_PORT',),'Native Gen3 animated coastal water, whole Emerald sea-rock breakwater units and FireRed S.S. Anne concrete marina floor replace the source ocean, solid dock barrier and brick pier respectively. Each breakwater unit remains visibly blocked; it is not presented as additional walkable floor. The complete previously approved compact steps retain the underground-passage warp. Original fishing, hidden item, sailors, boarding events, timetable and all collisions remain unchanged. The unique Fast Ship background vehicle has no reviewed matching native Gen3 metatile counterpart; its source cells remain held pending the user choice.',preserved_raw=ship)
