"""Whole native16x32 plant, verified intact in the actual native mid layer."""
from native_room_parts import RoomParts
_plants={}
def native_plant_parts(imports,top):
 key=id(imports)
 if key not in _plants:
  room=RoomParts(imports,'firered','FR_ROUTE_11_EAST_ENTRANCE_1F')
  # Both actual746 crown and753 pot were independently inspected beside
  # their complete native cells. Their mid sheets contain the full plant;
  # the structural room backdrop is confined to the native base layer.
  _plants[key]={True:room.rect(16,16,16,16,layers=['mid']),False:room.rect(16,32,16,16,layers=['mid'])}
 return _plants[key][bool(top)]
