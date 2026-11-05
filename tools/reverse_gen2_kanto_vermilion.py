"""Use complete native Crystal materials through Vermilion and its port."""

import argparse
from collections import Counter
import json
import zlib

import catalog
import reverse_gen2_kanto_final as final
from classic_geometry_review import art as classic_art, source_under_frames
from gb_theme_animation import frames
from reverse_gen2_kanto_final import DECISIONS, OUT
from reverse_gen2_kanto_lavender import Lavender, SAND_GBA
from reverse_kanto_review import exterior


PREFIX = "kanto_vermilion_"
PAIRS = {"firered": "general__rom_082d4b24", "leafgreen": "general__rom_082d4b04"}
CITY = "FR_VERMILION_CITY"
PORT = "FR_SSANNE_EXTERIOR"
ROUTES = ("FR_ROUTE_6", "FR_ROUTE_11")
PALE = (222, 255, 222, 255)
LAVENDER_NATIVE = (
    61, 84, 85, 86, 103, 194, 205, 207, 208, 209, 210, 211, 214, 215,
    216, 218, 224, 226, 236, 237, 239, 246, 247, 254, 255, 258, 259, 260,
    261, 263, 264, 265, 274, 282, 290, 296, 317, 318, 319,
)
SAFFRON_GATES = (
    68, 69, 70, 76, 77, 78, 92, 94, 100, 101, 102, 312, 316, 320, 324,
    328, 332, 387, 388, 389, 392, 393, 394, 397, 400, 401, 402, 408, 409,
    410, 437, 438, 439,
)
HOME_WALL = {
    670: (5, 5), 683: (6, 5), 684: (7, 5), 685: (4, 5), 686: (6, 5),
    696: (4, 5), 697: (6, 5),
    675: (6, 3), 676: (7, 3), 677: (4, 3), 678: (5, 3),
    679: (5, 3), 688: (4, 3), 689: (6, 3),
}
HOME_CAP = {
    672: (4, "water"), 673: (6, "water"), 674: (7, "water"),
    694: (4, "rock"), 695: (5, "rock"),
    699: (4, "ground"), 700: (6, "ground"), 701: (7, "ground"),
    702: (6, "water"), 703: (7, "ground"), 704: (6, "ground"), 705: (7, "ground"),
    706: (4, "ground"), 707: (6, "ground"), 708: (6, "ground"), 709: (7, "ground"),
}
GRAY = ((58,58,58), (107,107,107), (173,173,173), (222,255,222))
SEA = {(49,99,181), (66,123,189), (74,123,222), (74,148,222)}
ROCK = {(90,58,66), (123,74,74), (148,107,107), (189,148,140), (222,197,165), (239,214,197)}
PAVING = {(222,230,230), (197,206,214), (173,189,206)}
STEEL = {
    (0,0,0):GRAY[0], (66,74,107):GRAY[0], (90,90,115):GRAY[0],
    (123,123,132):GRAY[1], (148,165,181):GRAY[1], (173,189,206):GRAY[2],
    (206,222,239):GRAY[2], (247,247,255):GRAY[3],
    (222,107,99):GRAY[1], (206,82,74):GRAY[1],
    (156,123,99):GRAY[1], (197,173,140):GRAY[2],
    **{c:GRAY[0] for c in SEA | ROCK},
    (222,230,230):GRAY[3], (197,206,214):GRAY[2],
}
LAMPS = (653,654,655,663,671,687,719,727,735,743)
TRUCK = (787,788,789,790,791,792,793,794)


class Vermilion(Lavender):
    def __init__(self):
        super().__init__()
        self.out = OUT / "vermilion"
        self.out.mkdir(exist_ok=True)
        self.water_banks = {}

    def emit_detail(self, game, pair, mid, art, feature, evidence):
        self.whole_source(game, pair, [[mid]], f"vermilion_{feature}_{mid}")
        self.feature = PREFIX + feature
        art["role"] = self.feature
        if not {"overMask", "_objectMask"} & art.keys():
            parts = art.get("parts", [])
            art["_objectMask"] = "".join(
                "1" if any(
                    p["x"] <= x < p["x"]+p["w"] and p["y"] <= y < p["y"]+p["h"]
                    for p in parts
                ) else "0"
                for y in range(16) for x in range(16)
            )
        self.add(game, pair, mid, self.prepare_art(game, pair, mid, art), evidence)

    def matching_materials(self, game, pair):
        cells = self.imp.cell_index(game)
        field = self.previous(game, pair, 8)["donor"]
        warps = self.imp.table(game, "gba/warps")
        assert {(w["x"], w["y"]) for w in warps["FR_ROUTE_6"] if "ENTRANCE" in w["destMap"]} == {
            (12, 5), (13, 5), (19, 13),
        }
        assert {(w["x"], w["y"]) for w in warps["FR_ROUTE_11"] if "ROUTE_11_EAST_ENTRANCE" in w["destMap"]} == {
            (58, 10), (65, 10),
        }
        for area, ids in (
            ("FR_LAVENDER_TOWN", LAVENDER_NATIVE),
            ("FR_SAFFRON_CITY", SAFFRON_GATES),
            ("FR_FUCHSIA_CITY", (292,)),
        ):
            other = self.layouts[game, area][0]["pair"]
            for mid in ids:
                one, two = cells[pair, mid], cells[other, mid]
                assert all(one[k] == two[k] for k in ("pixel_sha256", "layer_sha256", "behavior")), (game, mid)
                previous = self.previous(game, other, mid)
                art = self.art_of(previous)
                if area == "FR_SAFFRON_CITY" and art.get("base"):
                    art["base"] = field
                self.emit_detail(
                    game, pair, mid, art, "matched_complete_crystal_kanto_module",
                    "The exact full source shape, behavior and layer pixels "
                    "match the same complete native Crystal surface or "
                    "correctly facing outdoor gate. Actual neighboring "
                    "modules and source doorway locations preserve the "
                    "same function and material at every placement.",
                )

    def houses(self, game, pair):
        field = self.previous(game, pair, 8)["donor"]
        warps = self.imp.table(game, "gba/warps")[CITY]
        doors = {
            (w["x"], w["y"]) for w in warps
            if "_HOUSE" in w["destMap"] or "FAN_CLUB" in w["destMap"]
        }
        assert doors == {(9, 6), (12, 17), (19, 17), (28, 24)}
        assert {(x,y) for _, _, x, y in self.placements(game, pair, 670)} == doors
        native = "VERMILION_CITY"
        native_warps = self.imp.table("crystal", "maps")[native]["warps"]
        assert any((w["x"],w["y"],w["destMap"]) == (5,5,"VERMILION_FISHING_SPEECH_HOUSE") for w in native_warps)
        assert any((w["x"],w["y"],w["destMap"]) == (7,13,"POKEMON_FAN_CLUB") for w in native_warps)
        for mid, (x,y) in HOME_WALL.items():
            assert all(n == CITY for n, _, _, _ in self.placements(game, pair, mid))
            art = self.native(self.gb_at("crystal", native, x, y), "")
            self.emit_detail(
                game, pair, mid, art, "complete_native_vermilion_house",
                "The complete original Vermilion home eaves, windows "
                "and exterior frame use the actual facing. Only whole "
                "interior windows repeat across the wider source home. "
                "The complete native doorway is at each source entrance.",
            )
        for mid, x in ((680,4), (681,6), (682,7), (720,6), (721,8), (722,9)):
            assert all(n == CITY for n, _, _, _ in self.placements(game, pair, mid))
            row = 10 if mid in (720,721,722) else 2
            donor = self.gb_at("crystal", native, x, row)
            art = self.native_building_part(field, donor, [8+i%8 for i in range(16)])
            self.emit_detail(
                game, pair, mid, art, "complete_native_vermilion_roof_band",
                "The full slate roof joins the native upper cap and "
                "eave. Its added source height repeats only the plain "
                "native roof surface and the true outer frame.",
            )
        water_row = self.previous(game, pair, 299)
        animation = water_row["animation"]
        water = water_row["parts"][0]["donor"]
        waves = frames(self.cache, water, animation, self.packed)
        for mid, (x, surface) in HOME_CAP.items():
            assert all(n == CITY for n, _, _, _ in self.placements(game, pair, mid))
            cap = self.gb_at("crystal", native, x, 2)
            parts = []
            if surface in ("water", "rock"):
                parts.append(dict(donor=water, x=0, y=0, w=16, h=16, animated=True))
                if surface == "rock":
                    q = mid-692
                    canonical = self.previous(game, pair, 280 if q == 2 else 281)
                    assert canonical["role"] == f"classic_gen2_complete_coastal_small_rock_quarter_{q}"
                    p = canonical["parts"][1]
                    rx,ry=p["srcX"],p["srcY"]
                    image=self.gb_image(p["donor"]).crop((rx,ry,rx+4,ry+4))
                    wet=exterior(image,{px for px in image.get_flattened_data() if px[2]>px[1]})
                    parts.extend(dict(
                        donor=p["donor"], srcX=rx+xx, srcY=ry+yy,
                        x=p["x"]+xx, y=p["y"]+yy, w=1, h=1,
                    ) for yy in range(4) for xx in range(4) if (xx,yy) not in wet)
            cap_image = self.gb_image(cap)
            outside = exterior(cap_image, {PALE}) if x in (4, 7) else set()
            parts.extend(dict(p, y=p["y"]+8) for p in self.mask_parts(cap, [
                y < 8 and (px, y) not in outside
                for y in range(16) for px in range(16)
            ]))
            art = self.composite(None if surface != "ground" else field, parts, "")
            if surface != "ground":
                art.update(animated=True, animation=animation, animationCategory="water", overMask="0"*256)
                self.assert_animated_parts(game, mid, art, waves)
            self.emit_detail(
                game, pair, mid, art, "complete_native_vermilion_roof_cap",
                "The original full roof cap connects the house in front "
                "of its actual land or sea backdrop. Native water stays "
                "animated around any original coastal boulder quarters.",
            )
        for mid in (642, 643, 644, 645, 646):
            for n, l, x, y in self.placements(game, pair, mid):
                assert n == CITY and self.adjacent(l,x,y,"below") in (72,73,74,75,391)
            self.emit_detail(
                game, pair, mid, self.art_of(water_row), "complete_sea_behind_native_center",
                "The whole native Center roof is already drawn below. "
                "The selected original Crystal sea stays fully animated "
                "around its true outer edge.",
            )

        for mid,x in ((712,6),(713,8),(714,9),(715,9),(728,6),(729,7),(730,8),(731,8),
                      (723,9),(736,6),(738,8),(739,8)):
            assert all(n == CITY for n, _, _, _ in self.placements(game,pair,mid))
            row = 10 if mid in (712,713,714) else 11 if mid in (715,728,729,730,731) else 13
            donor = self.gb_at("crystal", native, x, row)
            if row == 10:
                art = self.native_building_part(field, donor, [None]*8+list(range(8)))
            else:
                art = self.native(donor, "")
            self.emit_detail(
                game, pair, mid, art, "complete_native_vermilion_fan_club",
                "The actual Crystal Fan Club contributes its complete "
                "native roof, native windows and outer frame. Its single "
                "full native door follows the actual source doorway.",
            )

    def port_paving(self, game, pair):
        field = self.previous(game, pair, 449)["donor"]
        assert field["game"] == "crystal"
        boardwalk = (440,441,442,445,446,448,450,453,454,455,716,717,718,724,725,726,732,
                     734,747,748,749,776,777,778,779,780,781)
        for mid in boardwalk:
            assert all(n in (CITY,PORT) for n,_,_,_ in self.placements(game,pair,mid))
            art = self.native(field, "")
            if mid in (732, 734, 747, 749, 779, 781):
                left = mid in (732, 747, 779)
                x = 0 if left else 8
                rail = self.gb_ref("crystal", "SAFFRON_CITY", 39, 0 if left else 1)
                art = self.composite(field, [dict(donor=rail,srcX=x,srcY=0,x=x,y=0,w=8,h=16)], "")
            self.emit_detail(
                game, pair, mid, art, "complete_native_vermilion_port_paving",
                "The complete connected port walkway uses the same "
                "original native paving selected for its central squares. "
                "The outer rail meets the same native paving and the "
                "original visible embarkation threshold.",
            )
        for mid in (770,771,774,775,795,797,798,805):
            assert all(n in (CITY,PORT) for n,_,_,_ in self.placements(game,pair,mid)), (game,mid)
            donor = self.gb_ref("crystal", "SAFFRON_CITY", 39, 0 if mid in (770,774) else 1)
            if mid in (770,771,774,775,798,805):
                x = 0 if mid in (770,774,805) else 8
                if mid == 805:
                    donor = self.gb_ref("crystal","SAFFRON_CITY",73,0)
                parts = [dict(donor=donor,srcX=x,srcY=0,x=x,y=0,w=8,h=16)]
            else:
                y=0 if mid==795 else 8
                donor = self.gb_ref("crystal","SAFFRON_CITY",35,0 if mid==795 else 2)
                parts=[dict(donor=donor,srcX=0,srcY=y,x=0,y=y,w=16,h=8)]
            self.emit_detail(
                game, pair, mid, self.composite(field, parts, ""), "complete_native_vermilion_port_rail",
                "Complete original Crystal low dock railing is aligned "
                "to the matching outer edge, gate and corner. Its exterior "
                "reveals the same native pavement as the joined port deck.",
            )

    def shape_animation(self, game, pair, mid):
        if game not in self.water_banks:
            directory = self.cache / game / "data/generated/gba/native" / pair
            bank = catalog.read_lua(directory / "anim_manifest.lua")["water"]
            raw = (directory / "anim_water.rgba").read_bytes()
            size = bank["frames"] * len(bank["mids"]) * 1024
            if len(raw) != size:
                raw = zlib.decompress(raw)
            assert len(raw) == size and bank["frames"] == 8
            self.water_banks[game] = set(bank["mids"]), catalog.sha(raw)
        mids, digest = self.water_banks[game]
        if mid not in mids:
            return None, set(), set()
        animation = dict(mode="water_mask", bank="water", hash=digest)
        _, changed, middle = source_under_frames(self.cache, game, pair, mid, self.packed, animation)
        if not changed:
            animation["mode"] = "static_equivalent"
        return animation, changed, middle

    def steel_shape(self, game, pair, mid, donor, floor, water_program, feature, evidence):
        self.source(game,pair,mid)
        ids, palette, planes = self.packed[game,pair]
        off = ids.index(mid)*256
        animation, changed, middle = self.shape_animation(game,pair,mid)
        masks = {}
        for name,data in planes.items():
            image = catalog.rgba_native(data[off:off+256],palette,name!="under")
            mask = "".join("1" if p[3] and p[:3] in floor else "0" for p in image.get_flattened_data())
            assert all(mask[i]=="1" for i in (changed if name=="under" else middle if name=="mid" else ()))
            if "1" in mask:
                masks[name] = mask
        ground = dict(donor=donor, masks=masks) if masks else None
        if water_program and ground:
            ground["animation"] = water_program
        feature = PREFIX+feature
        art = classic_art(
            self,game,pair,mid,feature,GRAY,STEEL,ground=ground,source_animation=animation,
        )
        self.record("geometry",game,pair,mid,feature,art,evidence)

    def marine_fixtures(self, game, pair):
        gray = self.gb_at("crystal","LAVENDER_TOWN",13,8)
        assert {p[:3] for p in self.gb_image(gray).get_flattened_data()} == set(GRAY)
        deck = self.previous(game,pair,449)["donor"]
        wet = self.previous(game,pair,299)
        water = wet["parts"][0]["donor"]
        program = wet["animation"]
        for mid in LAMPS:
            assert all(n==CITY and 32<=y<=34 for n,_,_,y in self.placements(game,pair,mid))
            shore = mid in (727,743)
            donor = self.gb_ref("crystal","ROUTE_27",109,2) if shore else water
            self.steel_shape(
                game,pair,mid,donor,ROCK if shore else SEA,None if shore else program,
                "complete_maritime_marker_lamp",
                "The complete two original harbor marker lamps use four "
                "Crystal slate colors while retaining every original "
                "fixture pixel and priority plane. Only exact surrounding "
                "water or stone pixels reveal the matching native material.",
            )
        _, scene = self.layouts[game,PORT]
        assert self.matches_layout(scene, [[789,790,791],[792,793,794]],55,2)
        for mid in TRUCK:
            assert all(n==PORT and 55<=x<=57 and 1<=y<=3 for n,_,x,y in self.placements(game,pair,mid))
            wet = mid in (787,788)
            # The cargo outline has distinct colors from the three original
            # blue-gray deck shades. Do not include its medium steel highlight.
            self.steel_shape(
                game,pair,mid,water if wet else deck,SEA if wet else PAVING-{(173,189,206)},
                program if wet else None,"complete_vermilion_cargo_truck",
                "The complete dockside cargo truck has no full original "
                "Crystal counterpart. Its actual cab, wheels and bed keep "
                "their exact outline and all priority planes in native "
                "Crystal slate shades over the matching deck or water.",
            )
        donor = self.gb_at("crystal","GOLDENROD_UNDERGROUND_WAREHOUSE",2,2)
        assert (donor["id"],donor["quadrant"]) == (11,0)
        assert all(n==PORT and 59<=x<=61 and 2<=y<=3 for n,_,x,y in self.placements(game,pair,799))
        self.emit_detail(
            game,pair,799,self.native(donor,""),"complete_native_vermilion_cargo_crate",
            "The original Crystal warehouse storage crate replaces each "
            "complete cargo crate at the original dock positions.",
        )

    def planters(self, game, pair):
        field = self.previous(game,pair,8)["donor"]
        high = self.gb_at("crystal","NATIONAL_PARK",22,42)
        low = self.gb_at("crystal","NATIONAL_PARK",22,43)
        for mid in (752,756,757,760,761,762,763,764,765,766):
            assert all(n==CITY for n,_,_,_ in self.placements(game,pair,mid))
            if mid in (756,760,761,763,764):
                column = 7 if mid in (756,764) else 6
                wall = self.gb_at("crystal","VERMILION_CITY",column,5)
                parts = [
                    dict(donor=wall,srcX=0,srcY=0,x=0,y=0,w=16,h=16),
                    dict(donor=high,srcX=0,srcY=4,x=0,y=8,w=16,h=8),
                ]
            else:
                parts = [dict(donor=low,srcX=0,srcY=0,x=0,y=0,w=16,h=8)]
            self.emit_detail(
                game,pair,mid,self.composite(field,parts,""),"complete_native_vermilion_planter",
                "The original Crystal flower planter joins its matching "
                "upper flowers, solid rim, and the complete native home "
                "wall. The outside field is the same native turf.",
            )

    def shore(self, game, pair):
        water_row = self.previous(game,pair,299)
        animation = water_row["animation"]
        water = water_row["parts"][0]["donor"]
        waves = frames(self.cache,water,animation,self.packed)
        field = self.previous(game,pair,8)["donor"]
        cliff = self.gb_ref("crystal","ROUTE_27",109,2)
        for mid in (266,267,275,283,657,658,659,750,751,784,785,786,800,801,802,803,804):
            source = self.source(game,pair,mid)
            uses = list(self.placements(game,pair,mid))
            mineral = [p[:3] in ROCK for p in source.get_flattened_data()]
            parts = [dict(donor=water,x=0,y=0,w=16,h=16,animated=True)]
            parts.extend(self.mask_parts(cliff,mineral))
            if mid in (266,267):
                tree = self.previous(game,pair,28 if mid==266 else 29)
                assert "tree" in tree["role"]
                parts.extend(dict(p,srcY=p.get("srcY",0)+max(8-p["y"],0),
                                  y=max(p["y"],8),h=p["h"]-max(8-p["y"],0))
                             for p in tree["parts"] if p["y"]+p["h"]>8)
            if mid in (275,283):
                q = 1 if mid==275 else 3
                assert all(n == PORT for n,_,_,_ in uses)
                original = self.previous(game,pair,273 if q==1 else 281)
                p = original["parts"][1]
                image = self.gb_image(p["donor"]).crop((p["srcX"],p["srcY"],p["srcX"]+4,p["srcY"]+4))
                outside = exterior(image,{px for px in image.get_flattened_data() if px[2]>px[1]})
                parts.extend(dict(
                    donor=p["donor"],srcX=p["srcX"]+x,srcY=p["srcY"]+y,
                    x=p["x"]+x,y=p["y"]+y,w=1,h=1,
                ) for y in range(4) for x in range(4) if (x,y) not in outside)
            # The isolated island cap is entirely dry where its own
            # original pixels are ordinary field rather than sea.
            if mid in (657,658,659,784,786):
                grass = [(p[0],p[1],p[2]) in {(115,206,165),(66,181,140),(165,230,197)}
                         for p in source.get_flattened_data()]
                parts.extend(self.mask_parts(field,grass))
            assert len(parts) <= 32, (game,mid,len(parts))
            art = self.composite(None,parts,"")
            art.update(animated=True,animation=animation,animationCategory="water",overMask="0"*256)
            self.assert_animated_parts(game,mid,art,waves)
            self.emit_detail(
                game,pair,mid,art,"complete_native_vermilion_water_edge",
                "The full actual sea or pond edge uses native Crystal "
                "water and the corresponding native stone, canopy or "
                "boulder. Each exposed corner shows the matching water "
                "in every phase.",
            )
        lavender = self.layouts[game,"FR_LAVENDER_TOWN"][0]["pair"]
        for mid,canonical in ((462,776),(463,778)):
            assert all(n==CITY for n,_,_,_ in self.placements(game,pair,mid))
            art = self.art_of(self.previous(game,lavender,canonical))
            self.emit_detail(
                game,pair,mid,art,"complete_native_vermilion_boardwalk_support",
                "Original Crystal bridge supports connect the complete "
                "native wharf deck to the same animated sea beneath.",
            )

    def small_ground_details(self, game, pair):
        field = self.previous(game,pair,8)["donor"]
        sand = self.previous(game,pair,220)["donor"]
        raw = self.source(game,pair,262)
        mask = [pixel[:3] in SAND_GBA for pixel in raw.get_flattened_data()]
        assert 0 < sum(mask) < 256
        self.emit_detail(
            game,pair,262,self.composite(field,self.mask_parts(sand,mask),""),
            "complete_native_vermilion_sand_join",
            "The curved sand boundary joins the same selected native "
            "sand and ordinary field at their original source coordinates.",
        )
        for mid in (469,471,485,487,488,489,490,491,647):
            assert all(n==CITY for n,_,_,_ in self.placements(game,pair,mid))
            self.emit_detail(
                game,pair,mid,self.native(sand,""),"native_vermilion_sandy_path",
                "The source sandy walking-ground edge continues the "
                "matching original native Crystal sandy surface.",
            )
        boulder = self.gb_ref("crystal","ROUTE_1",24,0)
        image = self.gb_image(boulder)
        outside = exterior(image,{PALE})
        parts = self.mask_parts(boulder,[(x,y) not in outside for y in range(16) for x in range(16)])
        self.emit_detail(
            game,pair,159,self.composite(field,parts,""),"complete_native_vermilion_boulder",
            "The full native round Crystal boulder keeps clear outside "
            "corners over the same original native lawn.",
        )
        posts = self.previous(game,pair,231)["donor"]
        image = self.gb_image(posts)
        outside = exterior(image,{PALE})
        fence = self.mask_parts(posts,[(x,y) not in outside for y in range(16) for x in range(16)])
        for mid in (222,648,649):
            self.emit_detail(
                game,pair,mid,self.composite(sand if mid!=222 else field,fence,""),
                "complete_native_vermilion_fence",
                "Two complete original Crystal pickets continue the "
                "same wood-post fence over the matching sand or lawn.",
            )
        rail = self.art_of(self.previous(game,pair,245))
        self.emit_detail(
            game,pair,551,rail,"complete_native_vermilion_low_rail",
            "The complete original native low curb meets the actual "
            "fence return with the same facing and ground.",
        )
        safari = self.layouts[game,"FR_FUCHSIA_CITY"][0]["pair"]
        for mid,canonical in ((660,106),(661,105),(662,104)):
            assert all(n=="FR_ROUTE_11" and y==3 for n,_,_,y in self.placements(game,pair,mid))
            self.emit_detail(
                game,pair,mid,self.art_of(self.previous(game,safari,canonical)),
                "complete_native_vermilion_cave_cap",
                "The whole native crystal rock crest completes the "
                "matching left, middle and right cliff modules above "
                "the actual Diglett's Cave mouth.",
            )
        for mid,canonical in ((250,28),(251,29),(665,28),(666,29),(667,28),(668,29),(669,28)):
            uses = list(self.placements(game,pair,mid))
            assert all(n=="FR_ROUTE_11" for n,_,_,_ in uses)
            tree = self.previous(game,pair,canonical)
            assert "tree" in tree["role"]
            art = self.art_of(tree)
            if mid>=665:
                parts = []
                for p in art["parts"]:
                    y = max(p["y"],8)
                    if p["y"]+p["h"]>y:
                        parts.append(dict(p,y=y,srcY=p.get("srcY",0)+y-p["y"],h=p["y"]+p["h"]-y))
                art = self.composite(sand,parts,"")
            self.emit_detail(
                game,pair,mid,art,"complete_native_vermilion_tree_join",
                "The original native Crystal tree crown continues its "
                "neighboring canopy. At the actual sandy border only "
                "the visible lower half of the crown meets the path.",
            )

    def remaining(self):
        result = {}
        for (game,name),(spec,layout) in self.layouts.items():
            pair = spec["pair"]
            if PAIRS[game]!=pair:
                continue
            missing = Counter()
            for mid in layout["mids"]:
                key = game,"gen2",pair,mid,None
                if key not in self.replacements and key not in self.current:
                    prior = self.rows.get(key)
                    if not prior or prior["role"].startswith(PREFIX):
                        missing[mid] += 1
            result[f"{game}:{name}"] = dict(cells=len(layout["mids"]),remaining=sum(missing.values()),missing=missing)
        (self.out/"candidate-residual.json").write_text(json.dumps(result,indent=2)+"\n")
        return sum(x["remaining"] for x in result.values())

def main():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--private-validate", action="store_true")
    args = p.parse_args()
    r = Vermilion()
    r.stage()
    for game, pair in PAIRS.items():
        r.matching_materials(game, pair)
        r.houses(game, pair)
        r.port_paving(game, pair)
        r.marine_fixtures(game, pair)
        r.planters(game, pair)
        r.shore(game, pair)
        r.small_ground_details(game, pair)
    r.previews((*ROUTES, CITY, PORT))
    remaining = r.remaining()
    (r.out/"native-water-frame-proof.json").write_text(json.dumps(r.frame_proof,indent=2)+"\n")
    if args.freeze or args.private_validate:
        assert remaining == 0, remaining
        decisions = json.loads(DECISIONS.read_text())
        for section, records in r.frozen.items():
            decisions[section] = [
                row for row in decisions.get(section, [])
                if not row.get("feature", "").startswith(PREFIX)
            ] + records
        destination = r.out / "combined-candidate-decisions.json" if args.private_validate else DECISIONS
        destination.write_text(json.dumps(decisions, indent=2) + "\n")
    if args.private_validate:
        final.DECISIONS = destination
        candidate = final.Final()
        candidate.out = r.out / "neutral-validation"
        candidate.out.mkdir(exist_ok=True)
        candidate.stage()
        proof = candidate.validate()
        candidate.write(candidate.out / "candidate.lua")
        print(json.dumps(proof), flush=True)
    print(json.dumps(dict(rows=len(r.replacements), cells=sum(
        sum(u["count"] for u in r.usage[g, pair, m]) for g, _, pair, m, _ in r.replacements
    ), remaining=remaining, frozen=args.freeze)))


if __name__ == "__main__":
    main()
