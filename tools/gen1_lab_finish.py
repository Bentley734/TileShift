"""Whole Gen3 laboratory furniture plus intact compact fossil instruments."""
from gen1_family_review import FamilyReview
from native_room_parts import RoomParts
from gen1_native_plant import native_plant_parts
from gen1_domestic_finish import tablepart,roof,booktablemask
f=FamilyReview('lab',{'LAB'});lab=RoomParts(f.imp,'firered','FR_OAKS_LAB');entry=RoomParts(f.imp,'firered','FR_CINNABAR_ISLAND_POKEMON_LAB_ENTRANCE');gate=RoomParts(f.imp,'firered','FR_ROUTE_5_SOUTH_ENTRANCE');house=RoomParts(f.imp,'firered','FR_RIVALS_HOUSE')
floor=entry.ref(129);wall=lab.ref(105);home=house.ref(1)
tables={'WARDENS_HOUSE':(0,2,2),'CINNABAR_LAB_FOSSIL_ROOM':(6,4,2),'CINNABAR_LAB_TRADE_ROOM':(3,3,3)}
instrument={(10,11,26,27),(64,66,10,11),(69,69,85,85),(69,70,85,86),(69,58,85,59),(69,59,85,59),(74,75,90,91),(74,59,90,59),(70,69,86,85),(75,10,91,26),(11,75,27,91),(48,49,34,34)}
displays={(50,51,67,68),(87,88,28,71),(88,89,71,29),(36,24,42,34),(25,37,34,43)}
def colors(raw):
 white=[[248,248,224],[184,200,184],[112,136,136],[32,48,64]];orange=[[248,240,200],[232,168,104],[152,104,72],[48,48,64]];glass=[[240,248,248],[152,216,232],[80,144,184],[32,56,88]]
 return[orange if t in(10,11,26,27,48,49)else glass if t in(69,70,74,75,85,86,90,91)else white for t in raw]
def table(c,x,y,name,base):
 if name=='FUCHSIA_MEETING_ROOM':spec=(5,2,3)if 5<=x<=7 else(10,2,2)if 10<=x<=11 else None
 else:spec=tables.get(name)
 if not spec:return None
 ox,oy,w=spec
 if not(ox<=x<ox+w and oy<=y<oy+2):return None
 if w==2:
  r=tablepart(roof,64,56,booktablemask,(y-oy)*2+x-ox,'gen1_complete_native_lab_book_table');r['base']=base;return r
 return f.composite(base,lab.rect(128+(x-ox)*16,64+(y-oy)*16,16,16,layers=['mid']),'gen1_complete_native_lab_table')
def handle(c,x,y,name,m,data):
 raw=tuple(c['tiles']);base=home if name in('WARDENS_HOUSE','SAFARI_ZONE_SECRET_HOUSE','FUCHSIA_MEETING_ROOM')else floor
 t=table(c,x,y,name,base)
 if t:return t
 if raw in((1,38,38,1),(39,39,55,55)):return f.native(base,'gen1_lab_native_floor')
 if raw in((34,34,34,34),(65,65,34,34),(35,34,35,34)):return f.native(wall,'gen1_lab_full_wall')
 if raw in((44,45,60,61),(46,47,62,63)):return f.composite(base,native_plant_parts(f.imp,top=raw[0]==44),'gen1_complete_native_lab_plant')
 if raw in((64,66,40,41),(40,41,40,41)):return f.template('johto_domestic_complete_single_bay_bookcase_'+('0'if raw[0]==64 else'1'),wall if raw[0]==64 else base)
 if raw in((14,15,30,31),):return f.template('johto_house_chair_left'if x<3 else'johto_house_chair_right',base)
 if raw==(16,17,32,33):return f.composite(wall,entry.rect(64,8,16,16),'gen1_complete_native_lab_wall_clock')
 if raw==(76,77,52,53):
  return f.composite(base,gate.rect(56,10,8,5)+gate.rect(80,10,8,5,8,0)+gate.rect(56,21,8,11,0,5)+gate.rect(80,21,8,11,8,5),'gen1_complete_native_lab_doorway')
 if raw==(24,25,34,34):return f.source_palette([[248,248,224],[184,200,184],[112,136,136],[32,48,64]],'gen1_original_lab_room_sign')
 desks={(2,3,18,19):(0,0),(4,5,20,21):(1,0),(6,7,22,23):(0,1),(8,9,38,1):(1,1)}
 if raw in desks:
  xx,yy=desks[raw];return f.composite(base,lab.rect(32+xx*16,8+yy*16,16,16,layers=['mid']),'gen1_complete_native_research_workstation')
 if raw in displays:return f.source_palette([[248,240,200],[208,184,112],[128,128,104],[40,56,64]],'gen1_original_warden_collection_display')
 if raw in instrument:return f.source_palette(colors(raw),'gen1_original_compact_fossil_instrument_bay')
 if raw in((9,12,13,13),(12,13,12,13)):return f.source_palette([[248,248,224],[184,200,184],[112,136,136],[32,48,64]],'gen1_original_lab_instrument_partition')
 # Complete paper-table variants are explicitly bounded above. The remaining
 # source table modules are plain end/surface sections, preserving full feet.
 plain={(64,65,80,81):0,(65,66,81,81):1,(80,72,83,58):2,(81,82,58,84):3,(81,81,58,58):2,(65,66,34,43):3,(64,65,42,34):2,(64,65,80,72):0,(65,66,73,82):1}
 if raw in plain:
  q=plain[raw];return f.composite(base,lab.rect(128+(0 if q%2==0 else 2)*16,64+q//2*16,16,16,layers=['mid']),'gen1_complete_native_lab_table_end')
 return None
if __name__=='__main__':f.run(handle,('CINNABAR_LAB','CINNABAR_LAB_FOSSIL_ROOM','CINNABAR_LAB_TRADE_ROOM','CINNABAR_LAB_METRONOME_ROOM','WARDENS_HOUSE','FUCHSIA_MEETING_ROOM'),'Whole native Gen3 research workstations, tables, book tables, chairs, shelves, clocks, plants and complete door frames replace the equivalent original functions at native pixel scale. Compact original fossil-machine bays retain every control, tube and display using four Gen3 colors per source8px tile; unique Warden collection displays and room signs likewise preserve their exact original geometry and meaning. Original fossil restoration/trading, Warden events, hidden items, NPCs, collision and every source warp remain unchanged.')
