"""Explicit complete classic counterparts for Oldale's remaining native cells.

The source map is unchanged. Native GB art is copied at its original pixel size;
only the Red home's plain roof bands repeat to retain the64x64 source footprint.
Private comparison material is extracted to .work and is never packaged as art.
"""
from __future__ import annotations

import argparse
import copy
import json
from collections import Counter

from PIL import Image
import catalog
import preview
from reverse_common import ReverseReview, ROOT, STYLES
from reverse_hoenn_review import ground_ref
from reverse_kanto_review import exterior, runs, tree_art

GAMES = ('ruby', 'sapphire', 'emerald')
PAIR = 'general__petalburg'
LAYOUTS = {
    'home': [[620,621,621,622], [628,629,629,630],
             [636,639,637,638], [644,647,655,646]],
    'center': [[72,73,642,643], [80,81,82,83],
               [88,89,90,91], [96,97,98,99]],
    'mart': [[40,41,41,645], [48,49,50,51],
             [56,57,58,59], [96,65,66,67]],
}
GROUND = {
    518: 'rounded_north_worn_clearing_edge',
    519: 'south_worn_clearing_grass_join',
    632: 'east_worn_path_decorative_tree_cap_join',
}
DONORS = {
    'gen1': {'home': ('red','PALLET_TOWN',4,3),
             'center': ('red','VIRIDIAN_CITY',22,22),
             'mart': ('red','VIRIDIAN_CITY',28,16)},
    'gen2': {'home': ('crystal','NEW_BARK_TOWN',12,2),
             'center': ('crystal','CHERRYGROVE_CITY',28,0),
             'mart': ('crystal','CHERRYGROVE_CITY',22,0)},
}


def existing_rows():
    rows=[]
    for path in sorted((ROOT/'mappings').glob('reverse_*.lua')):
        if path.name != 'reverse_oldale.lua':
            rows += preview.read_reviewed(path)
    return rows


def identity(row):
    return (row['game'],row['style'],row['tileset'],row['id'],row.get('map'))


def native_piece(review, style, kind, col, row):
    game,map_id,ox,oy = DONORS[style][kind]
    sx,sy = ox*16,oy*16
    def rect(x,y,w,h,dx=0,dy=0):
        return review.gb_rect(game,map_id,sx+x,sy+y,w,h,dx,dy)
    if style == 'gen1' and kind == 'home':
        if row >= 2:
            parts=rect(col*16,(row-1)*16,16,16)
        else:
            # The original roof is16px. Preserve its complete upper/lower8px;
            # only repeat its plain internal shingles/vertical side panel.
            parts=[]
            if row == 0:
                parts += rect(col*16,0,16,8)
            if row == 1:
                parts += rect(col*16,8,16,8,0,8)
            start=8 if row==0 else 0
            if col in (0,3):
                for y in range(start,start+8):
                    parts += rect(col*16,8,16,1,0,y)
            else:
                for y in range(start,start+8,4):
                    parts += rect(col*16,4,16,4,0,y)
    else:
        parts=rect(col*16,row*16,16,16)
    role='oldale_'+kind+'_complete_native_'+('roof' if row<2 else 'facade')
    return review.composite(None,parts,role)


def mask_piece(review, art, mask, ground, roof):
    parts=[]
    for part in art['parts']:
        covered=[bool(mask[i]) and part.get('x',0)<=i%16<part.get('x',0)+part['w']
                 and part.get('y',0)<=i//16<part.get('y',0)+part['h']
                 for i in range(256)]
        for span in runs(covered):
            p=copy.deepcopy(part)
            p.update(srcX=part.get('srcX',0)+span['x']-part.get('x',0),
                     srcY=part.get('srcY',0)+span['y']-part.get('y',0),**span)
            parts.append(p)
    assert 0<len(parts)<=32, ('Oldale part count',len(parts))
    return dict(art,base=ground,parts=parts,
                overMask=''.join('1' if bit and roof else '0' for bit in mask))


def build(review, prior):
    occupied={identity(row) for row in prior}
    recipes={}
    for style in STYLES:
        ground=ground_ref(review,style)
        for kind,layout in LAYOUTS.items():
            whole=Image.new('RGBA',(64,64))
            pieces={}
            for y,row in enumerate(layout):
                for x,mid in enumerate(row):
                    art=native_piece(review,style,kind,x,y)
                    pieces[x,y]=art
                    whole.paste(review.render(art),(x*16,y*16))
            colors=({(255,255,255,255)} if style=='gen1'
                    else set(review.gb_image(ground).get_flattened_data())|{(222,255,222,255)})
            outside=exterior(whole,colors)
            for y,row in enumerate(layout):
                for x,mid in enumerate(row):
                    mask=[(x*16+px,y*16+py)not in outside
                          for py in range(16) for px in range(16)]
                    art=mask_piece(review,pieces[x,y],mask,ground,y<2)
                    if mid==645:
                        # This source cell is both the Mart roof and the
                        # actual lower-left quarter of the tree at its back.
                        # Retain selected native tree pixels behind true roof
                        # holes; only the opaque roof has foreground priority.
                        background=tree_art(review,style,2,ground)
                        art['parts']=copy.deepcopy(background['parts'])+art['parts']
                        art['role']='oldale_mart_complete_native_roof_with_tree_behind'
                        assert len(art['parts'])<=32
                    key=style,mid
                    if key in recipes:
                        # Source96 and repeated plain home/Mart roof cells
                        # genuinely repeat. Never resolve a conflict by silently
                        # picking one of two differently rendered buildings.
                        assert review.render(recipes[key]).tobytes()==review.render(art).tobytes(), (style,kind,mid,'Nonrepeatable native module')
                        assert recipes[key]['overMask']==art['overMask']
                    else:
                        recipes[key]=art
            whole.save(review.out/(style+'-'+kind+'-native-modules.png'))
        for mid,role in GROUND.items():
            art=review.native(ground,'oldale_nonencounter_'+role)
            art['overMask']='0'*256
            recipes[style,mid]=art

    for game in GAMES:
        index=review.imp.cell_index(game)
        for (style,mid),art in recipes.items():
            assert (PAIR,mid) in index and index[PAIR,mid]['used_by_map_count']
            key=(game,style,PAIR,mid,None)
            assert key not in occupied, ('Oldale overlaps an existing mapping',key)
            evidence=('Actual Oldale source cell reviewed independently in Ruby, Sapphire and Emerald. '
                      'Complete original Red/Crystal counterpart at native1:1 pixels. '
                      'Native64x64 service buildings and Crystal house remain intact; the Red64x48 house '
                      'retains its complete32px facade while only plain roof bands repeat to64x64. '
                      'Complete16px entrance frames, all windows/signs, side shadows and roof highlights are retained. '
                      'Whole-building connected exterior masks expose matching classic nonencounter ground outside true corners. '
                      'Roof silhouettes alone retain foreground priority. Original entrance anchors, maps, source collision, '
                      'warps, NPCs, scripts and events are unchanged. No map-position scope or inferred palette-only alias.')
            if mid in GROUND:
                evidence=('Reviewed native Oldale '+GROUND[mid]+'. This is nonencounter worn-ground/grass edging '
                          'with a purely decorative partial next-tree cap, not a flower or extra obstacle. '
                          'The native classic nonencounter lawn matches the already selected field palette; '
                          'the complete32px classic trees need no third-row cap. Source collision, encounters and events are unchanged.')
            review.row(game,PAIR,mid,style,art,evidence)
    return recipes


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate',action='store_true')
    parser.add_argument('--activate',action='store_true')
    args=parser.parse_args()
    assert not args.activate or args.validate
    review=ReverseReview('oldale',GAMES)
    prior=existing_rows()
    build(review,prior)
    target=ROOT/'mappings/reverse_oldale.lua' if args.activate else review.out/'candidates.lua'
    review.write(target)
    if args.validate:
        print(json.dumps(review.validate(),indent=2))
    new=review.rows
    review.rows={identity(r):r for r in prior if r['game']in GAMES}
    assert not set(review.rows)&set(new)
    review.rows.update(new)
    scenes=[]
    for game,prefix in (('ruby','RU'),('sapphire','SA'),('emerald','EM')):
        for style in STYLES:
            scenes.append(review.map_preview(game,prefix+'_OLDALE_TOWN',style))
    review.rows=new
    assert all(s['replaced']==s['total']==400 for s in scenes),scenes
    report={'new_rows':len(new),'by_style':dict(Counter(r['style']for r in new.values())),
            'no_existing_row_conflicts':True,'scenes':scenes}
    (review.out/'coverage.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
