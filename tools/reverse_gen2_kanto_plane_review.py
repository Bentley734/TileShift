"""Proposal-only whole visual modules with harmless BG1 plane splitting.

Only native cells with an entirely empty OVER plane qualify.  Every target
still receives independent full source/layer/behavior guards.  These are
context-review candidates, never coverage-driven automatic authoring.
"""
from __future__ import annotations
import json
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont
import catalog
import preview
from reverse_gen2_kanto_final import Final, OUT, previous


def main():
    r=Final();r.remaining_inventory();r.stage();empty=catalog.sha(bytes(1024));images={}
    def original(game,pair,mid):
        key=game,pair,mid
        if key not in images:
            c=r.imp.cell_index(game)[pair,mid]
            images[key]=preview.native_donor(r.cache,dict(game=game,tileset=pair,id=mid,hash=c['pixel_sha256']),r.packed)
        return images[key]
    def signature(game,pair,mid):
        c=r.imp.cell_index(game)[pair,mid]
        if c['layer_sha256']['over']!=empty:return None
        lookup={}
        geometry=bytes(lookup.setdefault(p,len(lookup))for p in original(game,pair,mid).get_flattened_data())
        return catalog.sha(previous.stable(dict(family=pair.split('__')[0],geometry=catalog.sha(geometry))).encode())
    active=defaultdict(list)
    for key,row in r.current.items():
        game,style,pair,mid,map_id=key
        if map_id is None and(game,pair,mid)in r.usage:
            sig=signature(game,pair,mid)
            if sig:active[sig].append(row)
    grouped=defaultdict(list)
    for item in r.remaining:
        for src in item['sources']:
            if(src['game'],'gen2',src['pair'],src['id'],None)in r.rows:continue
            sig=signature(src['game'],src['pair'],src['id'])
            if sig:grouped[sig].append(src)
    proposals=[]
    for sig,sources in grouped.items():
        rows=active.get(sig,[])
        if not rows:continue
        outputs=defaultdict(list)
        for row in rows:outputs[row.get('compositionPixelHash')or catalog.sha(r.render(row).tobytes())].append(row)
        if len(outputs)!=1:continue
        origins=next(iter(outputs.values()));old=min(origins,key=lambda o:(o['game'],o['tileset'],o['id']))
        proposals.append(dict(signature=sig,count=sum(s['count']for s in sources),canonical=dict(game=old['game'],pair=old['tileset'],mid=old['id']),
            canonical_row_sha256=catalog.sha(previous.stable(old).encode()),roles=sorted({o.get('role','')for o in origins}),targets=sources))
    proposals.sort(key=lambda p:-p['count'])
    for n,p in enumerate(proposals):p['number']=n
    (OUT/'plane-split-proposals.json').write_text(json.dumps(proposals,indent=2)+'\n')
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',12)
    for start in range(0,len(proposals),12):
        canvas=Image.new('RGB',(1600,6*244),'#18212b');draw=ImageDraw.Draw(canvas)
        for local,item in enumerate(proposals[start:start+12]):
            x,y=local%2*800,local//2*244;target=item['targets'][0];origin=item['canonical']
            old=r.current[origin['game'],'gen2',origin['pair'],origin['mid'],None]
            ims=[original(origin['game'],origin['pair'],origin['mid']),original(target['game'],target['pair'],target['id']),r.render(old)]
            for i,im in enumerate(ims):canvas.paste(im.resize((96,96),Image.Resampling.NEAREST),(x+4+i*104,y+36))
            witness=next(u for u in target['witnesses']if u['count']);spec,layout=r.layouts[target['game'],witness['map']]
            at=layout['mids'].index(target['id']);cx,cy=at%layout['width'],at//layout['width'];ctx=Image.new('RGBA',(80,80))
            for yy in range(5):
                for xx in range(5):
                    tx,ty=cx+xx-2,cy+yy-2
                    if 0<=tx<layout['width']and 0<=ty<layout['height']:ctx.paste(original(target['game'],spec['pair'],layout['mids'][ty*layout['width']+tx]),(xx*16,yy*16))
            canvas.paste(ctx.resize((200,200),Image.Resampling.NEAREST),(x+584,y+32))
            draw.text((x+4,y+2),str(item['number'])+' cells='+str(item['count'])+' targets='+str(len(item['targets'])),font=font,fill='white')
            draw.text((x+4,y+140),target['pair']+'/'+str(target['id'])+' '+witness['map'],font=font,fill='white')
            draw.text((x+4,y+160),origin['pair']+'/'+str(origin['mid']),font=font,fill='#c4cdd8')
            draw.text((x+4,y+180),'\n'.join(item['roles'])[:190],font=font,fill='#c4cdd8')
        canvas.save(OUT/f'plane-context-review-{start//12+1:02}.png')
    print(json.dumps(dict(groups=len(proposals),keys=sum(len(p['targets'])for p in proposals),cells=sum(p['count']for p in proposals))))


if __name__=='__main__':main()
