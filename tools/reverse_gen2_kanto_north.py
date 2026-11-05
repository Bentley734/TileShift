"""Complete the native Viridian and Pewter outdoor families."""

import argparse
from collections import Counter
import json

import reverse_gen2_kanto_final as final
from reverse_gen2_kanto_final import DECISIONS, OUT
from reverse_gen2_kanto_lavender import Lavender, SAND_GBA
from reverse_kanto_review import exterior


PREFIX="kanto_north_"
VIRIDIAN="viridian_outdoor"
PEWTER="pewter_outdoor"
PAIRS=(VIRIDIAN,PEWTER)
PEWTER_CITY="FR_PEWTER_CITY"
VIRIDIAN_CITY="FR_VIRIDIAN_CITY"
ROUTE_2="FR_ROUTE_2"
ROUTE_22="FR_ROUTE_22"
PALE=(222,255,222,255)
COMMON={
    VIRIDIAN:{
        "FR_LAVENDER_TOWN":(151,192,193,196,205,207,211,236,237,252,253,258,259,260,261,307,498),
        "FR_FUCHSIA_CITY":(195,203,204),
        "FR_SAFFRON_CITY":(68,69,70,76,77,78,92,94,100,101,102,376,377,378,387,388,389,
                          392,393,394,400,401,402,408,409,410,437,438,439),
    },
    PEWTER:{
        "FR_LAVENDER_TOWN":(161,194,196,205,207,209,210,224,226,255,263,497,498,527),
        "FR_FUCHSIA_CITY":(195,203,204),
    },
}
WOOD={
    232:(0,8),233:(0,8),234:(4,),240:(4,),241:(4,),242:(4,),243:(4,),
    248:(0,8),249:(0,8),
}
ROADS={
    VIRIDIAN:(354,355,356,362,363,364,370,371,372),
    PEWTER:(440,441,442,443,444,448,450,451,452,456,457,458),
}
ROUTE_22_GATE=(
    (704,705,705,705,705,705,705,705,706),
    (704,705,705,705,705,705,705,705,706),
    (704,705,705,705,705,705,705,705,706),
    (712,707,707,724,725,726,707,707,714),
    (720,715,715,701,702,703,715,715,722),
    (728,723,723,709,347,711,723,723,730),
)
PEWTER_HOUSES=(
    (679,694,694,694,647),(687,702,702,702,655),
    (695,710,688,689,663),(703,718,696,697,671),
)


class Northern(Lavender):
    def __init__(self):
        super().__init__()
        self.out=OUT/"northern"
        self.out.mkdir(exist_ok=True)

    def emit_detail(self,game,pair,mid,art,feature,evidence):
        self.whole_source(game,pair,[[mid]],f"north_{feature}_{mid}")
        self.feature=PREFIX+feature
        art["role"]=self.feature
        if not {"overMask","_objectMask"}&art.keys():
            parts=art.get("parts",[])
            art["_objectMask"]="".join(
                "1" if any(p["x"]<=x<p["x"]+p["w"] and p["y"]<=y<p["y"]+p["h"] for p in parts) else "0"
                for y in range(16) for x in range(16)
            )
        self.add(game,pair,mid,self.prepare_art(game,pair,mid,art),evidence)

    def baseline_missing(self,game,pair,mid):
        key=game,"gen2",pair,mid,None
        row=self.rows.get(key)
        return (game,pair,mid) in self.usage and key not in self.current and (not row or row["role"].startswith(PREFIX))

    def entrance_step(self,field,part):
        donor=self.gb_ref("crystal","UNION_CAVE_1F",18,3)
        if part=="center":
            pieces=[dict(donor=donor,srcX=8,srcY=0,x=x,y=0,w=1,h=16) for x in range(16)]
        else:
            x=8 if part=="left" else 0
            pieces=[dict(donor=donor,srcX=8-x,srcY=0,x=x,y=0,w=8,h=16)]
        return self.composite(field,pieces,"")

    def matched_surfaces(self,game,pair):
        cells=self.imp.cell_index(game)
        field=self.previous(game,pair,8)["donor"]
        for area,mids in COMMON[pair].items():
            other=self.layouts[game,area][0]["pair"]
            for mid in mids:
                assert self.baseline_missing(game,pair,mid), (game,pair,mid)
                a,b=cells[pair,mid],cells[other,mid]
                assert all(a[k]==b[k] for k in ("pixel_sha256","layer_sha256","behavior")), (game,pair,mid)
                art=self.art_of(self.previous(game,other,mid))
                if area=="FR_SAFFRON_CITY" and art.get("base"):
                    art["base"]=field
                self.emit_detail(
                    game,pair,mid,art,"matching_complete_kanto_terrain_or_gate",
                    "The complete reviewed Crystal terrain, fence, or gate "
                    "module matches the same source shape, priority layers "
                    "and behavior in these actual original placements. "
                    "Its full native artwork uses the original scale.",
                )
        if pair==VIRIDIAN:
            pave=self.gb_at("crystal","ROUTE_22",20,4)
            assert any(r>g>b for r,g,b,_ in self.gb_image(pave).get_flattened_data())
        else:
            pave=self.previous(game,pair,449)["donor"]
        for mid in ROADS[pair]:
            self.emit_detail(
                game,pair,mid,self.native(pave,""),"complete_native_route_paving",
                "The complete original route pavement matches the "
                "joined travel surface through its whole run and corners.",
            )
        pickets=self.gb_ref("crystal","SAFFRON_CITY",119,2)
        image=self.gb_image(pickets)
        outside=exterior(image,{PALE})
        left=[x<8 and (x,y) not in outside for y in range(16) for x in range(16)]
        base_parts=self.mask_parts(pickets,left)
        for mid,columns in WOOD.items():
            if not self.baseline_missing(game,pair,mid):
                continue
            parts=[dict(p,x=p["x"]+offset) for offset in columns for p in base_parts]
            self.emit_detail(
                game,pair,mid,self.composite(field,parts,""),"complete_native_wood_post_fence",
                "Complete original Crystal wood posts follow the "
                "actual horizontal or vertical run. The original native "
                "field shows in the open space around every post.",
            )
        if pair==PEWTER:
            sand=self.previous(game,pair,217)["donor"]
            source=self.source(game,pair,262)
            mask=[p[:3] in SAND_GBA for p in source.get_flattened_data()]
            assert 0<sum(mask)<256
            self.emit_detail(
                game,pair,262,self.composite(field,self.mask_parts(sand,mask),""),
                "native_pewter_sand_curve",
                "The complete selected native sand meets the ordinary "
                "native lawn at the same original shoreline of the path.",
            )

    def pewter_buildings(self,game,pair):
        name="PEWTER_CITY"
        _,scene=self.layouts[game,PEWTER_CITY]
        warp=self.imp.table(game,"gba/warps")[PEWTER_CITY]
        assert {(w["x"],w["y"]) for w in warp if "MUSEUM" in w["destMap"]}=={(17,6),(25,4)}
        assert {(w["x"],w["y"]) for w in warp if "HOUSE" in w["destMap"]}=={(9,30),(33,11)}
        for x,y in ((8,27),(32,8)):
            assert self.matches_layout(scene,[list(row) for row in PEWTER_HOUSES],x,y)
        assert self.matches_layout(scene,[
            [640,641,642,641,642,641,642,641,642,641,646],
            [648,649,649,649,649,649,649,649,649,649,654],
            [656,657,657,657,657,657,657,657,657,657,662],
            [664,665,665,665,665,665,665,665,665,665,670],
            [672,673,673,673,674,675,676,677,677,677,678],
            [680,681,681,681,682,683,684,685,685,685,686],
        ],12,0)
        assert self.matches_layout(scene,[
            [652,651,652,651,645],[657,657,657,657,653],
            [660,660,659,660,661],[668,667,718,668,669],
        ],23,1)
        field=self.previous(game,pair,8)["donor"]
        door=self.gb_at("crystal",name,29,13)
        roof={
            640:(10,2),641:(12,2),642:(12,2),646:(17,2),
            645:(23,2),651:(20,2),652:(20,2),
            648:(10,3),649:(12,3),654:(17,3),
            656:(10,4),657:(12,4),662:(17,4),653:(23,2),
            664:(10,5),665:(12,5),670:(17,5),
            659:(20,3),660:(20,3),661:(23,3),
        }
        wall={
            672:(10,6),673:(12,6),674:(12,6),675:(12,6),676:(12,6),
            677:(15,6),678:(17,6),680:(10,7),681:(12,7),682:(12,7),
            683:(12,7),684:(12,7),685:(15,7),686:(17,7),
            667:(20,5),668:(20,5),669:(23,5),690:(12,7),692:(15,7),
        }
        for mid,(x,y) in (roof|wall).items():
            assert all(n==PEWTER_CITY and sy<=6 for n,_,_,sy in self.placements(game,pair,mid))
            donor=self.gb_at("crystal",name,x,y)
            if mid in (640,641,642,646):
                art=self.native_building_part(field,donor,[None]*8+list(range(8)))
            elif mid==653:
                art=self.native_building_part(field,donor,[8+i%8 for i in range(16)])
            else:
                art=self.native(donor,"")
            self.emit_detail(
                game,pair,mid,art,"complete_native_pewter_museum",
                "The actual original Crystal museum and attached wing "
                "supply the joined slate roof, window bands and true outer "
                "frames. Only the whole interior modules repeat across "
                "the larger source footprint.",
            )
        for mid in (691,718,698,699,700):
            if mid in (691,718):
                art=self.native(door,"")
            else:
                art=self.entrance_step(field,("left","center","right")[mid-698])
            self.emit_detail(
                game,pair,mid,art,"native_pewter_entrance_or_step",
                "The complete native door and horizontally faced stair "
                "stay aligned to the real Museum and home entrances.",
            )
        houses={
            679:(28,12,"top"),694:(30,12,"top"),647:(31,12,"top"),
            687:(28,12,"fill"),702:(30,12,"fill"),655:(31,12,"fill"),
            695:(28,12,"eave"),710:(29,12,"eave"),688:(30,12,"eave"),
            689:(30,12,"eave"),663:(31,12,"eave"),
            703:(28,13,"wall"),696:(30,13,"wall"),697:(30,13,"wall"),671:(31,13,"wall"),
        }
        bands={
            "top":[None]*8+list(range(8)), "fill":[7]*16,
            "eave":[7]*8+list(range(8,16)), "wall":list(range(16)),
        }
        outside=set(self.gb_image(self.gb_at("crystal",name,27,12)).get_flattened_data())
        for mid,(x,y,band) in houses.items():
            assert all(n==PEWTER_CITY and sy in (8,9,10,11,27,28,29,30) for n,_,_,sy in self.placements(game,pair,mid))
            donor=self.gb_at("crystal",name,x,y)
            art=self.native_building_part(field,donor,bands[band],outside if x in (28,31) else None)
            self.emit_detail(
                game,pair,mid,art,"complete_native_pewter_house",
                "The complete original Pewter house has one roof edge, "
                "with whole original inside windows and a full frame "
                "only at its outer side.",
            )
        for mid in (379,380,381,382,383):
            assert all(self.adjacent(l,x,y,"below") in (72,73,74,75,391) for _,l,x,y in self.placements(game,pair,mid))
            self.emit_detail(
                game,pair,mid,self.native(field,""),"native_pewter_center_backdrop",
                "The whole original Center roof is already drawn below. "
                "The selected native field clears the old clipped cap.",
            )

    def viridian_checkpoint(self,game,pair):
        _,scene=self.layouts[game,ROUTE_22]
        assert self.matches_layout(scene,[list(row) for row in ROUTE_22_GATE],4,0)
        warps=self.imp.table(game,"gba/warps")[ROUTE_22]
        assert {(w["x"],w["y"]) for w in warps}=={(8,5),(9,5)}
        donor_warps=self.imp.table("crystal","maps")["ROUTE_22"]["warps"]
        assert any((w["x"],w["y"],w["destMap"])==(13,5,"VICTORY_ROAD_GATE") for w in donor_warps)
        field=self.previous(game,pair,8)["donor"]
        for mid,x,y in (
            (704,12,2),(705,14,2),(706,15,2),
            (712,12,3),(707,14,3),(724,14,3),(725,14,3),(726,14,3),(714,15,3),
            (720,12,4),(715,14,4),(701,14,4),(702,14,4),(703,14,4),(722,15,4),
            (728,12,5),(723,14,5),(709,14,5),(711,14,5),(730,15,5),
        ):
            assert all(n==ROUTE_22 for n,_,_,_ in self.placements(game,pair,mid))
            donor=self.gb_at("crystal","ROUTE_22",x,y)
            if y==2:
                art=self.native_building_part(field,donor,[8+i%8 for i in range(16)])
            else:
                art=self.native(donor,"")
            self.emit_detail(
                game,pair,mid,art,"complete_native_route_22_checkpoint",
                "The actual original Crystal Route 22 checkpoint uses its "
                "complete slate roof, outer side frames and original "
                "window bands. Only its native inner modules repeat. "
                "The true entrance and route alignment remain at the warp.",
            )
        for mid in (708,717,718,719,731):
            if mid in (708,731):
                art=self.art_of(self.previous(game,pair,5))
            else:
                art=self.entrance_step(field,("left","center","right")[mid-717])
            self.emit_detail(
                game,pair,mid,art,"complete_native_route_22_approach",
                "The original native shrubs and correctly facing north-"
                "south step join the actual checkpoint approach.",
            )

    def viridian_route_house_and_school(self,game,pair):
        _,scene=self.layouts[game,ROUTE_2]
        assert self.matches_layout(scene,[
            [44,45,45,45,47],[52,54,54,53,55],[60,6,7,61,63],
        ],14,20)
        warps=self.imp.table(game,"gba/warps")[ROUTE_2]
        assert any((w["x"],w["y"],w["destMap"])==(17,22,"FR_ROUTE_2_HOUSE") for w in warps)
        field=self.previous(game,pair,8)["donor"]
        for mid,x,y,band in (
            (44,14,14,"top"),(45,16,14,"top"),(47,17,14,"top"),
            (52,14,14,"edge"),(53,16,14,"edge"),(54,16,14,"edge"),(55,17,14,"edge"),
            (6,16,15,"wall"),(7,16,15,"wall"),(61,15,15,"wall"),
        ):
            donor=self.gb_at("crystal","ROUTE_2",x,y)
            rows=[None]*8+list(range(8)) if band=="top" else [7]*8+list(range(8,16)) if band=="edge" else list(range(16))
            art=self.native_building_part(field,donor,rows)
            self.emit_detail(
                game,pair,mid,art,"complete_native_route_2_house",
                "The whole original Crystal Route 2 home keeps its native "
                "roof, inside windows, side edge and full doorway at the "
                "original FireRed and LeafGreen warp.",
            )
        for mid,old in ((664,669),(666,677),(667,678),(668,679)):
            assert all(n==VIRIDIAN_CITY and y==18 for n,_,_,y in self.placements(game,pair,mid))
            art=self.art_of(self.previous(game,pair,old))
            self.emit_detail(
                game,pair,mid,art,"complete_native_viridian_school_facade",
                "The already selected complete native Viridian house "
                "wall and original window continue the matching School "
                "facade beside the actual doorway.",
            )
        planter=self.gb_at("crystal","NATIONAL_PARK",22,43)
        for mid in (672,674,675,676):
            assert all(n==VIRIDIAN_CITY and y==19 for n,_,_,y in self.placements(game,pair,mid))
            art=self.composite(field,[dict(donor=planter,srcX=0,srcY=0,x=0,y=0,w=16,h=8)],"")
            self.emit_detail(
                game,pair,mid,art,"complete_native_viridian_school_planter",
                "The native Crystal flower planter meets the complete "
                "School wall over the same surrounding native turf.",
            )

    def remaining_viridian(self,game,pair):
        field=self.previous(game,pair,8)["donor"]
        for mid,canonical in (
            (640,8),(641,8),(642,8),(643,8),(644,8),(645,5),(646,8),(647,8),
            (653,5),(654,135),(655,135),(661,135),
            (662,104),(663,105),(670,112),(700,122),(200,135),(201,135),
        ):
            art=self.art_of(self.previous(game,pair,canonical))
            self.emit_detail(
                game,pair,mid,art,"complete_native_viridian_field_or_rock",
                "The complete matching native field, low shrub, or "
                "correctly facing rock contour connects the original "
                "terrain and the whole completed building edge.",
            )
        saffron=self.layouts[game,"FR_SAFFRON_CITY"][0]["pair"]
        for mid,old in ((93,393),(368,92),(369,94),(693,392),(694,393),(695,394),
                        (696,100),(697,101),(698,101),(699,102)):
            art=self.art_of(self.previous(game,saffron,old))
            if art.get("base"):
                art["base"]=field
            assert all(n==ROUTE_2 for n,_,_,_ in self.placements(game,pair,mid))
            self.emit_detail(
                game,pair,mid,art,"complete_native_route_2_gate_frame",
                "The actual forest gate uses its complete original native "
                "frame and regular inside window module, with the same "
                "field around the outside edges.",
            )
    def north_residual(self):
        residual={}
        for (game,name),(spec,scene) in self.layouts.items():
            pair=spec["pair"]
            if pair not in PAIRS:
                continue
            missing=Counter(
                mid for mid in scene["mids"]
                if self.baseline_missing(game,pair,mid)
                and (game,"gen2",pair,mid,None) not in self.replacements
            )
            residual[f"{game}:{name}"]=dict(cells=len(scene["mids"]),remaining=sum(missing.values()),missing=missing)
        (self.out/"candidate-residual.json").write_text(json.dumps(residual,indent=2)+"\n")
        return sum(v["remaining"] for v in residual.values())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    options=p.add_mutually_exclusive_group()
    options.add_argument("--freeze",action="store_true")
    options.add_argument("--private-validate",action="store_true")
    args=p.parse_args()
    r=Northern()
    r.stage()
    for game in r.games:
        for pair in PAIRS:
            r.matched_surfaces(game,pair)
        r.pewter_buildings(game,PEWTER)
        r.viridian_checkpoint(game,VIRIDIAN)
        r.viridian_route_house_and_school(game,VIRIDIAN)
        r.remaining_viridian(game,VIRIDIAN)
    r.previews((VIRIDIAN_CITY,PEWTER_CITY,ROUTE_2,ROUTE_22,"FR_ROUTE_3"))
    remaining=r.north_residual()
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
        rows=len(r.replacements), remaining=remaining,
        cells=sum(sum(u["count"] for u in r.usage[g,p,m]) for g,_,p,m,_ in r.replacements),
        frozen=args.freeze,
    )))


if __name__=="__main__":
    main()
