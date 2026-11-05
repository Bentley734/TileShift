"""Complete native Fan Club, Day Care and Cerulean Bike Shop interiors."""

import argparse
from collections import Counter
import json

import catalog
import reverse_gen2_kanto_final as final
from classic_geometry_review import art as classic_art
from correct_gen2_mauville_fences_bicycles import rectangles
from reverse_gen2_kanto_final import DECISIONS, OUT
from reverse_gen2_kanto_lavender import Lavender
from reverse_kanto_review import exterior


PREFIX="kanto_club_shop_"
SHOP="FR_CERULEAN_CITY_BIKE_SHOP"
SHOP_DONOR="GOLDENROD_BIKE_SHOP"
PAIRS={
    "firered":("building__rom_082d4c5c","building__rom_082d4f74"),
    "leafgreen":("building__rom_082d4c3c","building__rom_082d4f54"),
}
CLUBS={"FR_VERMILION_CITY_POKEMON_FAN_CLUB","FR_SAFFRON_CITY_POKEMON_TRAINER_FAN_CLUB"}
CARE={"FR_ROUTE_5_POKEMON_DAY_CARE","FR_FOUR_ISLAND_POKEMON_DAY_CARE","FR_LAVENDER_TOWN_VOLUNTEER_POKEMON_HOUSE"}
FAN="POKEMON_FAN_CLUB"
RUG=(666,667,668,674,675,676,682,683,684,693,694,746,747)
COUCH=(704,705,706,707,712,713,714,715)
PEN=(750,753,754,755,756,757,758,759,764,765,766,767,770,771,772,790,791,792,794,795,796,797,798,799)
RUG_FILL=(206,148,197)
RUG_PALETTE=((58,58,58),(165,123,25),(255,156,197),(247,230,214))
SEAT_PALETTE=((58,58,58),(132,107,25),(214,197,140),(255,156,197))
BOOK_PALETTE=((58,58,58),(132,107,25),(214,197,140),(247,230,214))
PEN_PALETTE=((41,115,0),(99,206,8),(181,255,82),(222,255,222))
PEN_FLOOR={(197,181,115),(206,206,115),(222,214,132),(222,222,173),(230,230,132)}


class ClubsAndShop(Lavender):
    def __init__(self):
        super().__init__()
        self.out=OUT/"fan-bike"
        self.out.mkdir(exist_ok=True)

    def emit_detail(self,game,pair,mid,art,feature,evidence):
        self.whole_source(game,pair,[[mid]],f"club_shop_{feature}_{mid}")
        self.feature=PREFIX+feature
        art["role"]=self.feature
        if not {"overMask","_objectMask"}&art.keys():
            parts=art.get("parts",[])
            art["_objectMask"]="".join(
                "1" if any(p["x"]<=x<p["x"]+p["w"] and p["y"]<=y<p["y"]+p["h"] for p in parts) else "0"
                for y in range(16) for x in range(16)
            )
        self.add(game,pair,mid,self.prepare_art(game,pair,mid,art),evidence)

    def bikes(self,game,pair):
        _,layout=self.layouts[game,SHOP]
        width=layout["width"]
        assert width==11 and layout["height"]==10
        floor=self.previous(game,pair,670)["donor"]
        assert floor["game"]=="crystal"
        image=self.imp.gb("red","BIKE_SHOP")[0].crop((0,32,40,48))
        outside=exterior(image,{(255,255,255,255),(170,170,170,255)})
        mask=[(x+8,y) not in outside for y in range(16) for x in range(24)]
        assert all(mask[y*24+x] for y in range(16) for x in range(24) if image.getpixel((x+8,y))[0] in (0,85))
        assert all(
            self.adjacent(l,x,y,"left") in (641,674) and n==SHOP
            for n,l,x,y in self.placements(game,pair,642)
        )
        assert all(
            self.adjacent(l,x,y,"right")==642 and n==SHOP
            for m in (641,674) for n,l,x,y in self.placements(game,pair,m)
        )
        assert layout["mids"][3*width+1:3*width+5]==[643,644,643,644]
        pieces=[[],[]]
        for rect in rectangles(mask,24,16):
            start,end=rect["x"]+8,rect["x"]+8+rect["w"]
            for target in range(start//16,(end-1)//16+1):
                left,right=max(start,target*16),min(end,(target+1)*16)
                pieces[target].extend(self.gb_rect(
                    "red","BIKE_SHOP",left,32+rect["y"],right-left,rect["h"],
                    left-target*16,rect["y"],
                ))
        for part in (*pieces[0],*pieces[1]):
            part["donorStyle"]="gen1"
        for mid,half in ((641,0),(674,0),(642,1),(643,0),(644,1)):
            parts=list(pieces[half])
            if mid==641:
                edge=self.previous(game,pair,675)
                if edge.get("parts"):
                    parts=list(edge["parts"])+parts
            assert len(parts)<=32
            self.emit_detail(
                game,pair,mid,self.composite(floor,parts,""),"complete_native_cerulean_bicycle",
                "Each complete original Cerulean Bike Shop bicycle keeps "
                "all 24 by 16 native pixels of its tires, handlebars and "
                "frame. Only the connected original shop floor around "
                "the object is clear over this shop's native checker.",
            )
        # Full original Red donor silhouette, recomposed from the two tiles.
        selected=[self.replacements[game,"gen2",pair,m,None] for m in (674,642)]
        for y in range(16):
            for x in range(24):
                if mask[y*24+x]:
                    screen=x+8
                    assert selected[screen//16].getpixel((screen%16,y))==image.getpixel((screen,y))

    def bike_shop_fixtures(self,game,pair):
        floor=self.previous(game,pair,670)["donor"]
        warps=self.imp.table(game,"gba/warps")[SHOP]
        assert {(w["x"],w["y"]) for w in warps}=={(4,9),(5,8),(6,9)}
        shop={
            645:(6,0),646:(6,0),647:(6,0),
            653:(6,2),654:(6,2),655:(6,2),
            661:(6,3),662:(6,3),663:(6,3),
            664:(6,2),657:(7,2),658:(7,3),666:(7,4),
            651:(7,7),652:(3,2),667:(2,1),676:(4,1),
        }
        for mid,(x,y) in shop.items():
            assert all(n==SHOP for n,_,_,_ in self.placements(game,pair,mid))
            donor=self.gb_at("crystal",SHOP_DONOR,x,y)
            if mid in (646,654,655,662,663,647):
                # The complete plain wall field uses the native central
                # part of the shop panel with no repeated side outlines.
                parts=[dict(donor=donor,srcX=8,srcY=0,x=i,y=0,w=1,h=16) for i in range(16)]
                art=self.composite(floor,parts,"")
            else:
                art=self.native(donor,"")
            self.emit_detail(
                game,pair,mid,art,"complete_native_bike_shop_fixture",
                "The original Crystal bike shop wall, complete shop "
                "equipment and real service counter use the matching "
                "native panel and facing at every source position.",
            )
        for mid,y in ((660,6),(668,7)):
            donor=self.gb_at("crystal","DAY_CARE",7,y)
            image=self.gb_image(donor)
            pale={(222,255,222,255),(255,173,173,255),(255,214,214,255)}
            outside=exterior(image,pale)
            parts=self.mask_parts(donor,[(x,sy) not in outside for sy in range(16) for x in range(16)])
            self.emit_detail(
                game,pair,mid,self.composite(floor,parts,""),"complete_native_bike_shop_planter",
                "The complete original native potted tree uses both "
                "native crown and base over the same shop floor.",
            )
        self.shop_thresholds(game,pair)

    def shop_thresholds(self,game,pair):
        refs=[self.gb_at("crystal",SHOP_DONOR,x,7) for x in (2,3)]
        for mid in (26,27,28,677,678,679):
            if mid in (26,27,28):
                # Under the real exit the clipped outside row is black.
                art=self.native(self.black_ref(),"")
            else:
                art=self.native(refs[0 if mid!=679 else 1],"")
            self.emit_detail(
                game,pair,mid,art,"complete_native_bike_shop_exit",
                "The original Crystal bicycle shop mat stays under the "
                "actual shop exit, over the correct outside cutaway.",
            )

    def club_geometry(self,game,pair,mid,label,palette,colors,floor,background,evidence):
        self.source(game,pair,mid)
        ids,source_palette,planes=self.packed[game,pair]
        start=ids.index(mid)*256
        masks={}
        for name,data in planes.items():
            image=catalog.rgba_native(data[start:start+256],source_palette,name!="under")
            mask="".join("1" if p[3] and p[:3] in background else "0" for p in image.get_flattened_data())
            if "1" in mask:
                masks[name]=mask
        ground=dict(donor=floor,masks=masks) if masks else None
        feature=PREFIX+label
        art=classic_art(self,game,pair,mid,feature,palette,colors,ground=ground)
        self.record("geometry",game,pair,mid,feature,art,evidence)

    def club_special_furnishings(self,game,pair,floor):
        rug_colors={(123,123,99):RUG_PALETTE[0],(156,156,99):RUG_PALETTE[1],RUG_FILL:RUG_PALETTE[2]}
        seat_colors={
            (82,82,107):SEAT_PALETTE[0],(123,123,99):SEAT_PALETTE[0],
            (132,115,90):SEAT_PALETTE[1],(132,132,132):SEAT_PALETTE[0],
            (156,156,99):SEAT_PALETTE[1],(173,173,132):SEAT_PALETTE[1],
            (189,132,90):SEAT_PALETTE[1],RUG_FILL:SEAT_PALETTE[3],
            (206,156,90):SEAT_PALETTE[2],(239,181,90):SEAT_PALETTE[2],
        }
        pen_colors={
            (74,140,99):PEN_PALETTE[0],(82,82,107):PEN_PALETTE[0],
            (107,173,107):PEN_PALETTE[1],(123,123,99):PEN_PALETTE[0],
            (123,123,123):PEN_PALETTE[0],(123,189,222):PEN_PALETTE[2],
            (123,206,123):PEN_PALETTE[2],(132,132,132):PEN_PALETTE[0],
            (156,156,99):PEN_PALETTE[1],(173,173,132):PEN_PALETTE[1],
            (173,173,165):PEN_PALETTE[1],(189,230,255):PEN_PALETTE[3],
            (255,255,255):PEN_PALETTE[3],
            **{color:PEN_PALETTE[3] for color in PEN_FLOOR},
        }
        book_colors={
            (123,123,123):BOOK_PALETTE[0],(132,132,132):BOOK_PALETTE[0],
            (165,181,189):BOOK_PALETTE[1],(173,173,132):BOOK_PALETTE[1],
            (206,82,66):BOOK_PALETTE[0],(214,222,222):BOOK_PALETTE[3],
            (222,214,132):BOOK_PALETTE[2],(222,222,173):BOOK_PALETTE[2],
            (239,230,173):BOOK_PALETTE[2],(255,255,255):BOOK_PALETTE[3],
        }
        groups=(
            (RUG,"complete_club_or_daycare_rug",RUG_PALETTE,rug_colors,{RUG_FILL},CLUBS|CARE,
             "The large connected source room rug retains its original outline and exact border. "
             "The complete native Crystal checker fills its center to match the original room floor."),
            (COUCH,"complete_original_club_seating",SEAT_PALETTE,seat_colors,{RUG_FILL},CLUBS,
             "The original full couch and facing backed seats have no whole Crystal counterpart. "
             "Their complete shape and orientation use native wood and checker colors."),
            (PEN,"complete_daycare_indoor_pen",PEN_PALETTE,pen_colors,PEN_FLOOR,CARE,
             "The full original indoor pen, doorway and base rail have no whole Crystal equivalent. "
             "All exact source geometry uses native Crystal grass and rail colors over the room checker."),
            ((695,),"complete_volunteer_open_book",BOOK_PALETTE,book_colors,set(),CARE,
             "The original complete open book keeps its binding and pages on the source table. "
             "The entire original geometry uses four native Crystal room colors."),
        )
        for mids,label,palette,colors,background,areas,note in groups:
            for mid in mids:
                assert all(n in areas for n,_,_,_ in self.placements(game,pair,mid)), (game,mid)
                self.club_geometry(game,pair,mid,label,palette,colors,floor,background,note)

    def clubs_and_care(self,game,pair):
        floor=self.gb_at("crystal","DAY_CARE",2,1)
        assert self.gb_image(floor).tobytes()==self.gb_image(self.gb_at("crystal",FAN,2,1)).tobytes()
        blue=self.gb_at("crystal",FAN,3,0)
        black=self.black_ref()
        for mid in (26,27,28,647,648,655,656,658,661,778,779,780,781):
            donor=black if mid in (26,27,28) else floor
            self.emit_detail(
                game,pair,mid,self.native(donor,""),"complete_native_club_room_floor",
                "The original Crystal Fan Club and Day Care checker "
                "joins the whole room. Under the true exit the complete "
                "outside cutaway remains black.",
            )
        for mid in (641,642,643,644,645,646,649,651,652,654,690,691,701,702,703,
                    708,720,727,736,787,788,789,803,804):
            self.emit_detail(
                game,pair,mid,self.native(blue,""),"complete_native_club_wall_panel",
                "The complete original Crystal Fan Club wall panel uses "
                "the same native blue band across the top and joined sides.",
            )
        for mid in (657,659,660,662,663,698,699):
            art=self.native_building_part(floor,blue,list(range(8,16))+[None]*8)
            self.emit_detail(
                game,pair,mid,art,"complete_native_club_wall_base",
                "The original Crystal wall edge meets the same checker "
                "in its lower field and at the cutaway.",
            )
        for mid in (650,653):
            self.emit_detail(
                game,pair,mid,self.native(self.gb_at("crystal","DAY_CARE",3,0),""),
                "complete_native_club_window",
                "The full original Crystal framed Day Care window sits "
                "inside the same native room wall.",
            )
        shelves={
            664:(0,0),665:(1,0),672:(0,0),673:(1,0),680:(0,1),681:(1,1),
            805:(0,0),806:(1,0),808:(0,1),809:(1,1),692:(0,0),700:(0,1),
            709:(0,0),710:(1,0),716:(1,1),717:(0,1),718:(1,1),728:(1,1),
        }
        for mid,(x,y) in shelves.items():
            donor=self.gb_at("crystal",FAN,x,y)
            art=self.native_building_part(floor,donor,[8+i%8 for i in range(16)]) if mid in (672,673) else self.native(donor,"")
            self.emit_detail(
                game,pair,mid,art,"complete_native_club_storage",
                "The complete native Crystal Fan Club bookcase and "
                "cabinet preserve the original facing, shelves and base. "
                "Only the same inner shelf band repeats.",
            )
        for mid,(x,y) in {
            53:(7,0),98:(7,0),719:(7,1),743:(7,1),752:(7,1),
            669:(3,3),670:(3,3),671:(4,3),677:(3,4),678:(3,4),679:(4,4),761:(4,3),
            775:(2,3),777:(2,3),802:(2,3),
        }.items():
            donor=self.gb_at("crystal","DAY_CARE",x,y)
            if mid in (670,678):
                parts=[dict(donor=donor,srcX=8,srcY=0,x=i,y=0,w=1,h=16) for i in range(16)]
                art=self.composite(floor,parts,"")
            else:
                art=self.native(donor,"")
            self.emit_detail(
                game,pair,mid,art,"complete_native_daycare_furniture",
                "Original Crystal Day Care computer, table or whole "
                "stool uses the matching complete source position. "
                "Only the table's true inside band repeats.",
            )
        for mid,y in ((688,6),(689,6),(696,7),(697,7),(721,6),(722,6),(729,7),(730,7)):
            self.emit_detail(
                game,pair,mid,self.native(self.gb_at("crystal","DAY_CARE",7,y),""),
                "complete_native_club_potted_tree",
                "Both original native potted-tree halves meet the same "
                "native room checker at each source planter.",
            )
        for mid,y in ((737,6),(745,7),(782,6),(783,6),(784,6)):
            self.emit_detail(
                game,pair,mid,self.native(self.gb_at("crystal",FAN,0,y),""),
                "complete_native_club_flower_box",
                "Complete original Crystal flowers replace the aligned "
                "source display planter and its intact native rim.",
            )
        for mid in (723,724,731,732):
            donor=blue if mid in (723,724) else self.gb_at("crystal","PLAYERS_HOUSE_1F",mid-731,1)
            self.emit_detail(
                game,pair,mid,self.native(donor,""),"complete_native_volunteer_kitchen",
                "The full original Crystal stove and sink cabinet run "
                "joins the original wall at the same source position.",
            )
        poster=self.gb_at("crystal",FAN,7,0)
        for mid in (785,786):
            rows=[None]*8+list(range(8)) if mid==785 else list(range(8,16))+[None]*8
            self.emit_detail(
                game,pair,mid,self.native_building_part(blue if mid==785 else floor,poster,rows),
                "complete_native_club_poster",
                "The complete original Crystal Fan Club poster uses "
                "both halves above the same wall and floor.",
            )
        for mid in (685,686,687,738,739,740):
            x=3 if mid in (687,740) else 2
            self.emit_detail(
                game,pair,mid,self.native(self.gb_at("crystal",FAN,x,7),""),
                "complete_native_club_exit_mat",
                "The actual room exit has the original full Crystal red "
                "mat in the correct facing over the matching checker.",
            )
        for mid,x,y in ((793,6,2),(800,7,4),(801,6,4)):
            self.emit_detail(
                game,pair,mid,self.native(self.gb_at("crystal",SHOP_DONOR,x,y),""),
                "complete_native_daycare_counter",
                "The complete original Crystal counter panels follow "
                "the actual Day Care counter face and right edge.",
            )
        self.club_special_furnishings(game,pair,floor)

    def coverage(self,pairs):
        report={}
        for (game,name),(spec,layout) in self.layouts.items():
            pair=spec["pair"]
            if pair not in pairs:
                continue
            missing=Counter()
            for m in layout["mids"]:
                key=game,"gen2",pair,m,None
                if key not in self.replacements and key not in self.current:
                    old=self.rows.get(key)
                    if not old or old["role"].startswith(PREFIX):
                        missing[m]+=1
            report[f"{game}:{name}"]=dict(cells=len(layout["mids"]),remaining=sum(missing.values()),missing=missing)
        (self.out/"candidate-residual.json").write_text(json.dumps(report,indent=2)+"\n")
        return sum(r["remaining"] for r in report.values())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    options=p.add_mutually_exclusive_group()
    options.add_argument("--freeze",action="store_true")
    options.add_argument("--private-validate",action="store_true")
    args=p.parse_args()
    r=ClubsAndShop()
    r.stage()
    for game,(shop,club) in PAIRS.items():
        r.bikes(game,shop)
        r.bike_shop_fixtures(game,shop)
        r.clubs_and_care(game,club)
    r.previews((SHOP,*sorted(CLUBS|CARE)))
    remaining=r.coverage({pair for pairs in PAIRS.values() for pair in pairs})
    if args.freeze or args.private_validate:
        assert remaining==0,remaining
        decisions=json.loads(DECISIONS.read_text())
        for section,records in r.frozen.items():
            decisions[section]=[row for row in decisions.get(section,[]) if not row.get("feature","").startswith(PREFIX)]+records
        dest=r.out/"combined-candidate-decisions.json" if args.private_validate else DECISIONS
        dest.write_text(json.dumps(decisions,indent=2)+"\n")
    if args.private_validate:
        final.DECISIONS=dest
        candidate=final.Final()
        candidate.out=r.out/"neutral-validation"
        candidate.out.mkdir(exist_ok=True)
        candidate.stage()
        proof=candidate.validate()
        candidate.write(candidate.out/"candidate.lua")
        print(json.dumps(proof),flush=True)
    print(json.dumps(dict(
        rows=len(r.replacements),remaining=remaining,
        cells=sum(sum(u["count"] for u in r.usage[g,p,m]) for g,_,p,m,_ in r.replacements),
        frozen=args.freeze,
    )))


if __name__=="__main__":
    main()
