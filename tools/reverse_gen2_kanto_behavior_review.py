"""Proposal-only review of equal native art with distinct behavior metadata.

Behavior is never copied or loosened in the runtime.  Each eventual recipe
retains the exact target behavior guard; this tool merely finds visual reuse
candidates whose source pixels are independently compared across all planes.
"""
from __future__ import annotations
import json
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont
import catalog
import preview
from reverse_gen2_kanto_final import Final, OUT, previous, native_geometry


def main():
    review=Final()
    review.remaining_inventory()
    staged=review.stage()
    def signature(game,pair,mid):
        lookup={};planes=[]
        for plane in native_geometry(review,game,pair,mid):
            planes.append(bytes(255 if v==255 else lookup.setdefault(v,len(lookup))for v in plane))
        return catalog.sha(previous.stable(dict(family=pair.split('__')[0],colors=len(lookup),
            geometry=[catalog.sha(p)for p in planes])).encode())
    active=defaultdict(list)
    for key,row in review.current.items():
        game,style,pair,mid,map_id=key
        if map_id is None and(game,pair,mid)in review.usage:
            active[signature(game,pair,mid)].append(row)
    grouped=defaultdict(list)
    for item in review.remaining:
        for src in item['sources']:
            if(src['game'],'gen2',src['pair'],src['id'],None)not in review.rows:
                grouped[signature(src['game'],src['pair'],src['id'])].append(src)
    proposals=[]
    for sig,sources in grouped.items():
        rows=active.get(sig,[])
        if not rows:continue
        outputs=defaultdict(list)
        for row in rows:outputs[row.get('compositionPixelHash')or catalog.sha(review.render(row).tobytes())].append(row)
        if len(outputs)!=1:continue
        origins=next(iter(outputs.values()))
        # Select one existing row, then verify every target, not just its first witness.
        canonical=min(origins,key=lambda r:(r['game'],r['tileset'],r['id']))
        origin=dict(game=canonical['game'],pair=canonical['tileset'],mid=canonical['id'])
        valid=[]
        for src in sources:
            try:palette=review.rgba_bijection(origin,dict(game=src['game'],pair=src['pair'],mid=src['id']))
            except AssertionError:continue
            valid.append(src)
        if not valid:continue
        proposals.append(dict(signature=sig,count=sum(s['count']for s in valid),canonical=origin,
            canonical_row_sha256=catalog.sha(previous.stable(canonical).encode()),
            roles=sorted({r.get('role','')for r in origins}),targets=valid))
    proposals.sort(key=lambda p:-p['count'])
    for n,item in enumerate(proposals):item['number']=n
    (OUT/'behavior-relaxed-proposals.json').write_text(json.dumps(proposals,indent=2)+'\n')
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',12)
    for start in range(0,len(proposals),12):
        canvas=Image.new('RGB',(1600,6*244),'#18212b');draw=ImageDraw.Draw(canvas)
        for local,item in enumerate(proposals[start:start+12]):
            x,y=local%2*800,local//2*244;target=item['targets'][0];origin=item['canonical']
            old=review.current[origin['game'],'gen2',origin['pair'],origin['mid'],None]
            ims=[]
            for src in(dict(game=origin['game'],pair=origin['pair'],id=origin['mid']),target):
                cell=review.imp.cell_index(src['game'])[src['pair'],src['id']]
                ims.append(preview.native_donor(review.cache,dict(game=src['game'],tileset=src['pair'],id=src['id'],hash=cell['pixel_sha256']),review.packed))
            ims.append(review.render(old))
            for i,im in enumerate(ims):canvas.paste(im.resize((96,96),Image.Resampling.NEAREST),(x+4+i*104,y+36))
            witness=next(u for u in target['witnesses']if u['count']);spec,layout=review.layouts[target['game'],witness['map']]
            at=layout['mids'].index(target['id']);cx,cy=at%layout['width'],at//layout['width'];ctx=Image.new('RGBA',(80,80))
            for yy in range(5):
                for xx in range(5):
                    tx,ty=cx+xx-2,cy+yy-2
                    if not(0<=tx<layout['width']and 0<=ty<layout['height']):continue
                    mid=layout['mids'][ty*layout['width']+tx];cell=review.imp.cell_index(target['game'])[spec['pair'],mid]
                    im=preview.native_donor(review.cache,dict(game=target['game'],tileset=spec['pair'],id=mid,hash=cell['pixel_sha256']),review.packed)
                    ctx.paste(im,(xx*16,yy*16))
            canvas.paste(ctx.resize((200,200),Image.Resampling.NEAREST),(x+584,y+32))
            draw.text((x+4,y+2),str(item['number'])+' cells='+str(item['count'])+' targets='+str(len(item['targets'])),font=font,fill='white')
            draw.text((x+4,y+140),target['pair']+'/'+str(target['id'])+' '+witness['map'],font=font,fill='white')
            draw.text((x+4,y+160),origin['pair']+'/'+str(origin['mid']),font=font,fill='#c4cdd8')
            draw.text((x+4,y+180),'\n'.join(item['roles'])[:190],font=font,fill='#c4cdd8')
        canvas.save(OUT/f'behavior-context-review-{start//12+1:02}.png')
    print(json.dumps(dict(groups=len(proposals),keys=sum(len(p['targets'])for p in proposals),cells=sum(p['count']for p in proposals))))


if __name__=='__main__':main()
