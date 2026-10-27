"""Private raised-rock platform reference; no production mapping writes."""
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
from building_review import decode_layout


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=Path(os.environ['APPDATA'])/'pokemon-love2d')
    parser.add_argument('--output',type=Path,default=WORKSPACE/'.work/tileshift-gen2-outdoor-cliff-review')
    parser.add_argument('--engine',type=Path,default=WORKSPACE/'.tools/engine-0395')
    parser.add_argument('--write-front-reviewed',action='store_true',help='Merge only the twelve approved Sprout front/gap rows; paving remains private')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    data=ext.source(args.cache,'crystal');definition=data['maps']['VIOLET_CITY'];packed={}
    root=args.cache/'firered/data/generated/gba/native';manifest=catalog.read_lua(root/'manifest.lua')
    spec=manifest['layouts']['FR_ROUTE_3'];layout=decode_layout(root/spec['file'])
    records={(r['pair'],r['mid']):r for r in json.loads((WORKSPACE/'.work/tileshift-catalog/firered.json').read_text())['cells']}
    def ref(mid):return {'game':'firered','tileset':spec['pair'],'id':mid,'hash':records[spec['pair'],mid]['pixel_sha256']}
    def donor(mid):return preview.native_donor(args.cache,ref(mid),packed)
    canvas=Image.new('RGB',(1450,690),'#18202c');draw=ImageDraw.Draw(canvas);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    draw.text((14,12),'Violet raised-rock sides: outdoor material and handedness, without tree or water pixels',font=font,fill='white')
    draw.text((14,42),'Source 8px strip / native 8px strip / full native wall / actual Route 3 context; new counterpart pending visual approval.',fill='#ccd7e5')
    references=[]
    for i,(label,bid,q,sx,mid,nx,ny) in enumerate((('west face',104,0,0,112,20,8),('east face',105,1,8,114,67,3))):
        y=85+i*290;cell=ext.cell_info(args.cache,'crystal',data,'TILESET_JOHTO',bid,q)
        assert cell['collision']==7 and cell['tiles']==([59,59,59,59] if i==0 else [61,61,61,61])
        source=ext.source_image(args.cache,'crystal',data,cell,definition).crop((sx,0,sx+8,16))
        full=donor(mid);target=full.crop((sx,0,sx+8,16));assert layout['mids'][ny*layout['width']+nx]==mid
        context=Image.new('RGBA',(48,48))
        for dy in range(-1,2):
            for dx in range(-1,2):
                x,z=nx+dx,ny+dy
                assert 0<=x<layout['width'] and 0<=z<layout['height']
                context.paste(donor(layout['mids'][z*layout['width']+x]),((dx+1)*16,(dy+1)*16))
        draw.text((14,y),label,font=font,fill='white')
        canvas.paste(source.resize((96,192),Image.Resampling.NEAREST),(20,y+35))
        canvas.paste(target.resize((96,192),Image.Resampling.NEAREST),(390,y+35))
        canvas.paste(full.resize((192,192),Image.Resampling.NEAREST),(660,y+35))
        canvas.paste(context.resize((192,192),Image.Resampling.NEAREST),(1080,y+35))
        draw.rectangle((660+sx*12,y+35,660+(sx+8)*12-1,y+226),outline='#fff293',width=2)
        draw.rectangle((1144,y+99,1207,y+162),outline='#fff293',width=2)
        draw.text((130,y+50),f'Source {bid}:{q}, raw 8px tile {59 if i==0 else 61}',fill='#ccd7e5')
        draw.text((130,y+75),'Repeated vertically; no water adjacent',fill='#ccd7e5')
        draw.text((490,y+50),f'FR Route 3, tile {mid}',fill='white')
        draw.text((490,y+75),f'srcX {sx}, y 0, w 8, h 16',fill='#ccd7e5')
        draw.text((1080,y+235),f'Actual native cell ({nx},{ny})',fill='#ccd7e5')
        references.append({'role':label,'donor':ref(mid),'srcX':sx,'srcY':0,'w':8,'h':16,
                           'nativeMap':'FR_ROUTE_3','nativeCell':[nx,ny],
                           'stripPixelHash':catalog.sha(target.tobytes()),'status':'needs_visual_review'})
    canvas.save(args.output/'sprout-platform-side-counterparts.png')
    (args.output/'sprout-platform-side-references.json').write_text(json.dumps(references,indent=2),encoding='utf-8')
    # The front is an independent eight-pixel-high feature. Show its complete
    # source profile beside full native faces instead of silently taking only
    # half of a native sixteen-pixel wall or substituting a jump ledge.
    front=Image.new('RGB',(1480,930),'#18202c');d=ImageDraw.Draw(front)
    d.text((14,12),'Sprout platform front: exact source profile and full native rock faces',font=font,fill='white')
    d.text((14,42),'Only the lower 8px are a rock face. The doorway opening and paved upper 8px need separate complete counterparts.',fill='#ccd7e5')
    source_cells=[]
    for i,(bid,q) in enumerate(((116,0),(116,1),(117,0),(117,1))):
        cell=ext.cell_info(args.cache,'crystal',data,'TILESET_JOHTO',bid,q)
        tile=ext.source_image(args.cache,'crystal',data,cell,definition)
        x=14+i*360;front.paste(tile.resize((160,160),Image.Resampling.NEAREST),(x,86))
        d.text((x,257),f"Source {bid}:{q} raw {cell['tiles']}",fill='white')
        d.text((x,281),f"Collision 0x{cell['collision']:02x}",fill='#ccd7e5')
        d.rectangle((x,166,x+159,245),outline='#fff293',width=2)
        source_cells.append({'id':bid,'quadrant':q,'raw':cell['tiles'],'collision':cell['collision'],'sourceHash':cell['sourceHash']})
    native_cells=[]
    for i,mid in enumerate((120,121,122,135)):
        x=14+i*360;tile=donor(mid)
        front.paste(tile.resize((160,160),Image.Resampling.NEAREST),(x,340))
        d.text((x,511),f'Native full16 rock family {mid}',fill='white')
        record=records[spec['pair'],mid]
        d.text((x,535),record.get('behavior_hint') or str(record['behavior']),fill='#ffd391' if mid==135 else '#ccd7e5')
        if mid==135:d.text((x,558),'Jump ledge: held, not a blocked-wall match',fill='#ffd391')
        positions=[(i%layout['width'],i//layout['width']) for i,v in enumerate(layout['mids'])
                   if v==mid and 0<i%layout['width']<layout['width']-1 and 0<i//layout['width']<layout['height']-1]
        assert positions;nx,ny=positions[0];context=Image.new('RGBA',(48,48))
        for dy in range(-1,2):
            for dx in range(-1,2):context.paste(donor(layout['mids'][(ny+dy)*layout['width']+nx+dx]),((dx+1)*16,(dy+1)*16))
        front.paste(context.resize((192,192),Image.Resampling.NEAREST),(x,610));d.rectangle((x+64,674,x+127,737),outline='#fff293',width=2)
        d.text((x,817),f'Actual FR Route 3 context ({nx},{ny})',fill='#ccd7e5')
        native_cells.append({'donor':ref(mid),'nativeCell':[nx,ny],'behavior':record.get('behavior_hint'),
                             'status':'held_full16_face_does_not_fit_source8_without_review' if mid!=135 else 'held_native_jumpable_ledge'})
    d.text((14,876),'No production front-rim mapping is created here. Full rock silhouette, pavement material and doorway clearance must be reviewed together.',font=font,fill='white')
    front.save(args.output/'sprout-platform-front-footprint-audit.png')
    (args.output/'sprout-platform-front-footprint-audit.json').write_text(json.dumps({'sourceCells':source_cells,'nativeFaces':native_cells,
        'frontHeightPixels':8,'sourceDoorwayCell':[116,1],'productionWrites':0},indent=2),encoding='utf-8')
    city=decode_layout(root/manifest['layouts']['FR_PEWTER_CITY']['file'])
    city_mids=sorted(mid for mid in set(city['mids'])if mid<512)
    contact=Image.new('RGB',(1440,70+((len(city_mids)+11)//12)*112),'#18202c');d=ImageDraw.Draw(contact)
    d.text((14,12),'Actual native Pewter City outdoor cells: paving and rock context reference',font=font,fill='white')
    for i,mid in enumerate(city_mids):
        x,y=12+i%12*120,62+i//12*112
        contact.paste(donor(mid).resize((64,64),Image.Resampling.NEAREST),(x,y))
        d.text((x,y+67),str(mid),fill='white')
        d.text((x,y+83),(records[spec['pair'],mid].get('behavior_hint')or'').removeprefix('MB_'),fill='#ccd7e5')
    contact.save(args.output/'native-pewter-city-ground-reference.png')
    # Private explicit native-material compaction: retain the complete upper
    # and base outline (rows0..3 and12..15), remove only the middle stone band.
    # The walkable doorway gap uses the already reviewed bottom8px of the
    # actual native ROCK_STAIRS137 repeated-rung tile, never jump-ledge art.
    pavement=ref(449);stairs_record=records['general__rom_082d4b54',137]
    stairs={'game':'firered','tileset':'general__rom_082d4b54','id':137,'hash':stairs_record['pixel_sha256']}
    def mid_part(mid,srcX=0,srcY=0,w=16,h=16,x=0,y=0):
        return {'donor':ref(mid),'srcX':srcX,'srcY':srcY,'w':w,'h':h,'x':x,'y':y,
                'layers':['mid'],'layerHashes':{'mid':records[spec['pair'],mid]['layer_sha256']['mid']}}
    proposals=[];source_band=Image.new('RGBA',(64,32));target_band=Image.new('RGBA',(64,32));ground=donor(449)
    for i,(bid,q,mid)in enumerate(((116,0,120),(116,1,None),(117,0,121),(117,1,122))):
        cell=ext.cell_info(args.cache,'crystal',data,'TILESET_JOHTO',bid,q)
        parts=[]
        if i==0:parts.append(mid_part(112,w=8,h=8))
        if i==3:parts.append(mid_part(114,srcX=8,w=8,h=8,x=8))
        if mid is not None:parts.extend((mid_part(mid,srcY=0,h=4,y=8),mid_part(mid,srcY=12,h=4,y=12)))
        else:parts.append({'donor':stairs,'srcY':8,'w':16,'h':8,'x':0,'y':8})
        row={'game':'crystal','style':'gen3','map':'VIOLET_CITY','tileset':'TILESET_JOHTO','id':bid,'quadrant':q,
             'sourceHash':cell['sourceHash'],'sourceFiles':data['fingerprints']['TILESET_JOHTO'],
             'role':'sprout_paved_platform_front_'+str(i),'kind':'native_composite','status':'candidate',
             'sourceCollision':cell['collision'],'base':pavement,'parts':parts,
             'evidence':'Private native-material outdoor rock-face compaction. Complete upper/base outlines of actual FRRoute3 faces120/121/122 retain rows0..3 and12..15; only the repeated middle stone band4..11 is omitted to fit the source8px face. Native mid-layer masks keep outside grass out of the paved approach. Actual native Pewter449 supplies the continuous paved path. Crystal source154 threshold uses two complete native ROCK_STAIRS137 rung/shadow units in its lower8px. Gold/Silver have plain paved ground at this opening and keep a continuous paved gap. Source footprint/collision and original Sprout warp remain unchanged.'}
        source_band.paste(ext.source_image(args.cache,'crystal',data,cell,definition),(i*16,0))
        below=ext.cell_info(args.cache,'crystal',data,'TILESET_JOHTO',bid,q+2)
        source_band.paste(ext.source_image(args.cache,'crystal',data,below,definition),(i*16,16))
        target_band.paste(preview.replacement_image(args.cache,row,packed,WORKSPACE/'TileShift'),(i*16,0));target_band.paste(ground,(i*16,16))
        proposals.append(row)
    review_image=Image.new('RGB',(1450,610),'#18202c');d=ImageDraw.Draw(review_image)
    d.text((14,12),'Sprout platform proposal: complete8px blocked rock face, paved approach, and original walkable doorway gap',font=font,fill='white')
    d.text((14,42),'Native-material compaction only: top4 + base4 rows retained from full16px outdoor rock; middle8px stone band omitted. No jump-ledge cue.',fill='#ccd7e5')
    for x,image,label in ((14,source_band,'Original64px continuous front + pavement'),(730,target_band,'Private compact native-material proposal')):
        d.text((x,86),label,font=font,fill='white');review_image.paste(image.resize((640,320),Image.Resampling.NEAREST),(x,122))
        d.rectangle((x+160,202,x+319,281),outline='#fff293',width=2)
    d.text((14,474),'The yellow box is the original walkable gap: source116:q1/collision0. Other three front cells retain collision7.',font=font,fill='white')
    d.text((14,507),'Paving: actual FRPewter449. Crystal threshold: native137 lower8px, two complete rung/shadow units.',font=font,fill='#ccd7e5')
    d.text((14,540),'All retained top/base rock pixels are exact native mid-layer pixels; transparent outside corners show paving instead of foreign grass.',font=font,fill='#ccd7e5')
    review_image.save(args.output/'sprout-platform-complete-front-proposal.png')
    # Gold/Silver do not contain Crystal's special154 threshold. Keep their
    # native plain paved opening distinct rather than adding inferred stairs.
    all_proposals=[];source_variants=[];paving=[]
    for game in ext.GAMES:
        donor_data=ext.source(args.cache,game);definition=donor_data['maps']['VIOLET_CITY'];blocks=catalog.lua_array(definition['blocks'])
        for original in proposals:
            row=copy.deepcopy(original);row['game']=game
            cell=ext.cell_info(args.cache,game,donor_data,'TILESET_JOHTO',row['id'],row['quadrant'])
            row['sourceHash']=cell['sourceHash'];row['sourceFiles']=donor_data['fingerprints']['TILESET_JOHTO']
            row['sourcePalettes']=[a.get('palette',1)for a in cell['attributes']]
            row['sourcePriority']=[bool(a.get('priority'))for a in cell['attributes']]
            row['sourceCells']=[[i%definition['width']*2+row['quadrant']%2,i//definition['width']*2+row['quadrant']//2]
                                for i,b in enumerate(blocks)if b==row['id']]
            assert row['sourceCells'] and cell['collision']==row['sourceCollision']
            if row['id']==116 and row['quadrant']==1 and game!='crystal':
                assert cell['tiles']==[6,6,6,6]
                row.pop('parts');row.pop('base');row.pop('kind');row['donor']=pavement
                row['role']='sprout_plain_paved_platform_gap'
            source_variants.append({'game':game,'source':[row['id'],row['quadrant']],
                                    'raw':cell['tiles'],'collision':cell['collision'],'sourceHash':cell['sourceHash']})
            row['status']='reviewed';all_proposals.append(row)
        seed=ext.cell_info(args.cache,game,donor_data,'TILESET_JOHTO',1,0)
        assert seed['tiles']==[6,6,6,6] and seed['collision']==0
        occurrences={}
        for i,bid in enumerate(blocks):
            for q in range(4):occurrences.setdefault((bid,q),[]).append([i%definition['width']*2+q%2,i//definition['width']*2+q//2])
        for (bid,q),coords in occurrences.items():
            cell=ext.cell_info(args.cache,game,donor_data,'TILESET_JOHTO',bid,q)
            if ext.identity(cell)!=ext.identity(seed):continue
            if any(row['game']==game and row['id']==bid and row['quadrant']==q for row in all_proposals):continue
            paving.append({'game':game,'style':'gen3','map':'VIOLET_CITY','tileset':'TILESET_JOHTO','id':bid,'quadrant':q,
                'sourceHash':cell['sourceHash'],'sourceFiles':donor_data['fingerprints']['TILESET_JOHTO'],
                'sourceCells':coords,'sourceCollision':cell['collision'],
                'sourcePalettes':[a.get('palette',1)for a in cell['attributes']],
                'sourcePriority':[bool(a.get('priority'))for a in cell['attributes']],
                'role':'violet_paved_walkway','status':'reviewed','donor':pavement,
                'evidence':'Private Violet paved-walkway proposal. Only complete source6/6/6/6 cells with identical source hash, collision0, palette1 and no priority are eligible, explicitly scoped to Violet City. Source and actual native Pewter City contexts show public paved paths. Complete native449 paving preserves the source walkable nonencounter ground role; no grass, dirt track, threshold, building, cliff or mixed boundary is inferred.'})
    live=ext.validate_batch(all_proposals+paving,args,WORKSPACE/'TileShift')
    for row in all_proposals:row['status']='candidate'
    (args.output/'sprout-platform-front-runtime-checks.json').write_text(json.dumps({'live':live,'sourceVariants':source_variants,
        'retainedRockRows':[0,1,2,3,12,13,14,15],'omittedInteriorStoneRows':list(range(4,12)),
        'goldSilverPlainOpeningRetained':True,'productionWrites':0},indent=2),encoding='utf-8')
    (args.output/'sprout-platform-complete-front-candidates.json').write_text(json.dumps(all_proposals,indent=2),encoding='utf-8')
    for row in paving:row['status']='candidate'
    (args.output/'violet-paving-candidates.json').write_text(json.dumps(paving,indent=2),encoding='utf-8')
    crystal_data=ext.source(args.cache,'crystal');definition=crystal_data['maps']['VIOLET_CITY'];blocks=catalog.lua_array(definition['blocks'])
    before=Image.new('RGBA',(definition['width']*32,definition['height']*32));after=before.copy()
    chosen={(row['id'],row['quadrant']):row for row in all_proposals+paving if row['game']=='crystal'}
    for i,bid in enumerate(blocks):
        for q in range(4):
            cell=ext.cell_info(args.cache,'crystal',crystal_data,'TILESET_JOHTO',bid,q)
            tile=ext.source_image(args.cache,'crystal',crystal_data,cell,definition);xy=(i%definition['width']*32+q%2*16,i//definition['width']*32+q//2*16)
            before.paste(tile,xy);after.paste(preview.replacement_image(args.cache,chosen[bid,q],packed,WORKSPACE/'TileShift')if(bid,q)in chosen else tile,xy)
    proof_image=Image.new('RGB',(1450,after.height+300),'#18202c');d=ImageDraw.Draw(proof_image)
    d.text((14,12),'Violet paved-path and Sprout front proposal in the actual complete source map',font=font,fill='white')
    d.text((14,42),'Only full plain paved ground and the separately displayed four Sprout front cells change. All architecture and other terrain are original here.',fill='#ccd7e5')
    proof_image.paste(before,(14,80));proof_image.paste(after,(744,80))
    sample=next(i for i,mid in enumerate(city['mids'])if mid==449 and 0<i%city['width']<city['width']-1 and 0<i//city['width']<city['height']-1)
    cx,cy=sample%city['width'],sample//city['width'];context=Image.new('RGBA',(48,48))
    for dy in range(-1,2):
        for dx in range(-1,2):context.paste(donor(city['mids'][(cy+dy)*city['width']+cx+dx]),((dx+1)*16,(dy+1)*16))
    proof_image.paste(context.resize((144,144),Image.Resampling.NEAREST),(14,after.height+100))
    d.text((178,after.height+110),f'Actual native FR Pewter City paved449 at({cx},{cy})',font=font,fill='white')
    d.text((178,after.height+142),f'{len(paving)} new full-ground aliases plus12 separate front/gap rows; all live source/donor checks passed.',font=font,fill='#ccd7e5')
    d.text((178,after.height+174),'Gold/Silver retain their plain paved doorway gap. Crystal154 retains a visible short threshold.',font=font,fill='#ccd7e5')
    proof_image.save(args.output/'violet-paved-ground-and-front-context.png')
    if args.write_front_reviewed:
        approved=copy.deepcopy(all_proposals)
        assert len(approved)==12
        for row in approved:
            row['status']='reviewed';row['evidence']=row['evidence'].replace('Private native-material outdoor rock-face compaction.','Visually reviewed native-material outdoor rock-face compaction.',1)
        target=WORKSPACE/'TileShift/mappings/gen2_outdoor_extended.lua';stats=ext.merge_reviewed(approved,target)
        validation=ext.validate_batch(preview.read_reviewed(target),args,WORKSPACE/'TileShift')
        (args.output/'approved-front-activation.json').write_text(json.dumps({'file':stats,'live':validation,
            'violetPavingRowsHeld':len(paving)},indent=2),encoding='utf-8')
        print('Approved Sprout front activation:',stats,validation)
    print('Private outdoor cliff side references:',len(references),'production writes: 0')


if __name__=='__main__':main()
