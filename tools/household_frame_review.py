"""Independent private TV-frame proof; never changes production mappings."""
from __future__ import annotations
import argparse
import copy
import json
import os
from pathlib import Path
import sys

WORKSPACE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(WORKSPACE/'.tools/python'))
from PIL import Image,ImageDraw,ImageFont
import catalog
import preview
import gen2_extended_review as ext


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=Path(os.environ['APPDATA'])/'pokemon-love2d')
    parser.add_argument('--engine',type=Path,default=WORKSPACE/'.tools/engine-0395')
    parser.add_argument('--output',type=Path,default=WORKSPACE/'.work/tileshift-house-review')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    mod=WORKSPACE/'TileShift';records={r['mid']:r for r in json.loads((WORKSPACE/'.work/tileshift-catalog/firered.json').read_text())['cells'] if r['pair']=='player_house'};packed={}
    def ref(mid):return {'game':'firered','tileset':'player_house','id':mid,'hash':records[mid]['pixel_sha256']}
    def tile(mid):return preview.native_donor(args.cache,ref(mid),packed)
    def part(mid,sx,sy,w,h,x,y):return {'donor':ref(mid),'srcX':sx,'srcY':sy,'w':w,'h':h,'x':x,'y':y}
    recipe={'kind':'native_composite','base':ref(1),'parts':[
        part(45,3,13,10,1,3,0),part(45,2,14,12,1,2,1),part(45,0,15,16,1,0,2),
        part(53,0,0,16,2,0,3),part(53,0,6,16,10,0,5),part(61,0,0,16,1,0,15)]}
    body=tile(53);base=tile(1);original=Image.new('RGBA',(16,48))
    for i,mid in enumerate((45,53,61)):original.paste(tile(mid),(0,i*16))
    for y in range(2,6):assert body.crop((0,y,16,y+1)).tobytes()==body.crop((0,1,16,2)).tobytes()
    target=preview.replacement_image(args.cache,recipe,packed,mod)
    recipe['compositionPixelHash']=catalog.sha(target.tobytes())
    row_map=[13,14,15,16,17]+list(range(22,32))+[32];assert len(row_map)==16
    cap_ranges=((3,13),(2,14),(0,16));pixels=0
    for y,source_y in enumerate(row_map):
        for x in range(16):
            included=y>=3 or cap_ranges[y][0]<=x<cap_ranges[y][1]
            expected=original.getpixel((x,source_y)) if included else base.getpixel((x,y))
            assert target.getpixel((x,y))==expected
            pixels+=included
    assert pixels==246
    rows=json.loads((args.output/'household-candidates.json').read_text())
    emerald_pair='building__brendans_mays_house'
    emerald={r['mid']:r for r in json.loads((WORKSPACE/'.work/tileshift-catalog/emerald.json').read_text())['cells'] if r['pair']==emerald_pair}
    def eref(mid):return {'game':'emerald','tileset':emerald_pair,'id':mid,'hash':emerald[mid]['pixel_sha256']}
    def epart(mid,sx,sy,w,h,x,y):return {'donor':eref(mid),'srcX':sx,'srcY':sy,'w':w,'h':h,'x':x,'y':y}
    wall=next(r for r in rows if r['role']=='household_wall')
    window_recipe={'kind':'native_composite','base':ref(1),'parts':copy.deepcopy(wall['parts'])+[
        epart(542,0,8,15,1,0,2),epart(542,0,9,16,7,0,3),
        epart(550,0,0,16,3,0,10),epart(550,1,3,15,1,1,13)]}
    window=preview.replacement_image(args.cache,window_recipe,packed,mod)
    window_recipe['compositionPixelHash']=catalog.sha(window.tobytes())
    wall_image=preview.replacement_image(args.cache,wall,packed,mod)
    window_stack=Image.new('RGBA',(16,32))
    for i,mid in enumerate((542,550)):window_stack.paste(preview.native_donor(args.cache,eref(mid),packed),(0,i*16))
    window_mask={(x,y) for y in range(2,14) for x in range(16)
                 if not (y==2 and x==15) and not (y==13 and x==0)}
    assert len(window_mask)==190
    for y in range(16):
        for x in range(16):
            expected=window_stack.getpixel((x,y+6)) if (x,y) in window_mask else wall_image.getpixel((x,y))
            assert window.getpixel((x,y))==expected
    compact_stack=Image.new('RGBA',(16,48))
    for i,(left,right) in enumerate(((43,44),(51,52),(59,60))):
        compact_stack.paste(tile(left).crop((0,0,8,16)),(0,i*16))
        compact_stack.paste(tile(right).crop((8,0,16,16)),(8,i*16))
    for y in range(16,21):assert compact_stack.crop((0,y,16,y+1)).tobytes()==compact_stack.crop((0,16,16,17)).tobytes()
    book_head={'kind':'native_composite','base':ref(1),'parts':copy.deepcopy(wall['parts'])+[
        part(43,1,11,4,1,1,0),part(44,11,11,4,1,11,0),
        part(43,1,12,7,1,1,1),part(44,8,12,7,1,8,1),
        part(43,1,13,7,3,1,2),part(44,8,13,8,3,8,2),
        part(51,0,5,8,11,0,5),part(52,8,5,8,11,8,5)]}
    book_base=copy.deepcopy(next(r for r in rows if r['role']=='household_bookcase_base'))
    head_image=preview.replacement_image(args.cache,book_head,packed,mod)
    base_image=preview.replacement_image(args.cache,book_base,packed,mod)
    book_head['compositionPixelHash']=catalog.sha(head_image.tobytes())
    book=Image.new('RGBA',(16,32));book.paste(head_image,(0,0));book.paste(base_image,(0,16))
    book_mask=set();book_rows=list(range(11,16))+list(range(21,48))
    assert len(book_rows)==32
    for y,sy in enumerate(book_rows):
        for x in range(16):
            included=(y>=5 or (y==0 and (1<=x<5 or 11<=x<15)) or
                      (y==1 and 1<=x<15) or (2<=y<5 and 1<=x<16))
            expected=compact_stack.getpixel((x,sy)) if included else wall_image.getpixel((x,y))
            assert book.getpixel((x,y))==expected
            if included:book_mask.add((x,y))
    assert len(book_mask)==499
    for row in rows:
        row['sourceCells']=[[row['x'],row['y']]]
        if row['role']=='household_television':
            row.pop('donor',None);row.update(copy.deepcopy(recipe))
            row['evidence']='Private complete native TV casing compacted only through four identical blank perspective rows; all top bevel, full screen and lower controls preserved within the original16px source footprint.'
        elif row['role']=='household_window':
            row.pop('donor',None);row.update(copy.deepcopy(window_recipe))
            row['evidence']='Private complete native16x12 house window, including all190 frame/glass/highlight pixels, centered within the original16px source wall cell. Native window542/550 is copied without shortening; all66 outside pixels retain the compact FR wall.'
        elif row['role']=='household_bookcase_head':
            row.update(copy.deepcopy(book_head))
            row['evidence']='Private complete bookcase cap43/44 plus body51/52; only five identical blank green-panel rows removed after the approved horizontal middle-column compaction. Full native shelves, books, lower frame and shadow remain.'
    live=ext.validate_batch(rows,args,mod)
    canvas=Image.new('RGB',(1220,540),'#18202c');d=ImageDraw.Draw(canvas);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    d.text((14,12),'Complete native TV casing: preserve top bevel, full screen, bottom rim and controls',font=font,fill='white')
    d.text((14,41),'Only four identical blank perspective rows removed.246 retained native glyph pixels are0diff;10 outside-cap pixels use room wood.',fill='#ccd7e5')
    for x,label,image in ((20,'Native complete casing16x20',original.crop((0,13,16,33))),
                          (420,'Previous tile53 only16x16',body),(820,'Complete-frame proposal16x16',target)):
        d.text((x,80),label,font=font,fill='white');canvas.paste(image.resize((288,image.height*18),Image.Resampling.NEAREST),(x,113))
    canvas.save(args.output/'independent-tv-complete-frame-proposal.png')
    windows=Image.new('RGB',(1220,530),'#18202c');d=ImageDraw.Draw(windows)
    d.text((14,12),'Complete native house window: all190 frame, glass and highlight pixels retained',font=font,fill='white')
    d.text((14,41),'The two beige outside corners and all other outside pixels use the FR wall; no native window row is removed.',fill='#ccd7e5')
    native_window=window_stack.crop((0,8,16,20))
    previous=next(r for r in json.loads((args.output/'household-candidates.json').read_text()) if r['role']=='household_window')
    old_window=preview.replacement_image(args.cache,previous,packed,mod)
    for x,label,picture in ((20,'Native complete16x12 window',native_window),
                            (420,'Previous Celadon652 crop',old_window),(820,'Whole window on compact FR wall',window)):
        d.text((x,80),label,font=font,fill='white');windows.paste(picture.resize((288,picture.height*18),Image.Resampling.NEAREST),(x,113))
    windows.save(args.output/'independent-window-complete-frame-proposal.png')
    books=Image.new('RGB',(1220,790),'#18202c');d=ImageDraw.Draw(books)
    d.text((14,12),'Complete bookcase casing and native floor shadow within the original16x32 footprint',font=font,fill='white')
    d.text((14,41),'Cap43/44 retained; five identical blank green-panel rows removed. Every shelf, book row, bottom frame and shadow is preserved.',fill='#ccd7e5')
    previous_head=next(r for r in json.loads((args.output/'household-candidates.json').read_text()) if r['role']=='household_bookcase_head')
    old_book=Image.new('RGBA',(16,32));old_book.paste(preview.replacement_image(args.cache,previous_head,packed,mod),(0,0));old_book.paste(base_image,(0,16))
    for x,label,picture in ((20,'Native casing + shadow16x37',compact_stack.crop((0,11,16,48))),
                            (420,'Previous crop without cap',old_book),(820,'Complete-frame16x32 proposal',book)):
        d.text((x,80),label,font=font,fill='white');books.paste(picture.resize((256,picture.height*16),Image.Resampling.NEAREST),(x,113))
    books.save(args.output/'independent-bookcase-complete-frame-proposal.png')
    floors=preview.read_reviewed(mod/'mappings/interiors.lua')
    preview.map_preview(args.cache,args.output,'red','REDS_HOUSE_1F','red-household-tv-complete-frame-proposal',floors+rows,packed,4,mod)
    (args.output/'independent-tv-complete-frame-recipe.json').write_text(json.dumps(recipe,indent=2),encoding='utf-8')
    (args.output/'independent-window-complete-frame-recipe.json').write_text(json.dumps(window_recipe,indent=2),encoding='utf-8')
    (args.output/'independent-bookcase-complete-frame-recipe.json').write_text(json.dumps(book_head,indent=2),encoding='utf-8')
    (args.output/'independent-bookcase-complete-frame-proof.json').write_text(json.dumps({
        'nativeCasingAndShadowBBox':[0,11,16,37],'nativeStackRows':[[43,44],[51,52],[59,60]],
        'removedBlankBodyRows':[0,1,2,3,4],'removedRowsAllIdentical':True,
        'headParts':len(book_head['parts']),'baseRecipeUnchanged':True,
        'retainedNativePixels':499,'retainedPixelDifferences':0,'outsideCapWallPixels':13,
        'fullNativeFloorShadowRetained':True,'sourceFootprint':[16,32],'live':live},indent=2),encoding='utf-8')
    (args.output/'independent-window-complete-frame-proof.json').write_text(json.dumps({
        'nativeWindowBBox':[0,8,16,12],'nativeStackMids':[542,550],
        'retainedGlyphPixels':190,'retainedGlyphDifferences':0,'outsideGlyphPixels':66,
        'maskRows':[[0,15]]+[[0,16]]*10+[[1,16]],'targetTop':2,
        'plainWallExcluded':[[15,8],[0,19]],'rightAndBottomHighlightPreserved':True,
        'compositionPixelHash':catalog.sha(window.tobytes()),'live':live},indent=2),encoding='utf-8')
    (args.output/'independent-tv-complete-frame-proof.json').write_text(json.dumps({
        'nativeCasingBBox':[0,13,16,20],'nativeStackMids':[45,53,61],
        'removedBodyRows':[2,3,4,5],'removedRowsEqualRetainedBodyRow':1,
        'retainedGlyphPixels':pixels,'retainedGlyphDifferences':0,'outsideCapFloorPixels':10,
        'fullScreenBodyRowsRetained':[6,15],'lowerControlsRetained':True,'sourceFootprint':[16,16],
        'compositionPixelHash':catalog.sha(target.tobytes()),'live':live},indent=2),encoding='utf-8')
    print('Private complete TV frame proof',pixels,'unchanged glyph pixels',live,'production writes: 0')


if __name__=='__main__':main()
