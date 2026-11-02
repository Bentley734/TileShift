"""Build portable, pixel-verified Gen2 comparison images and a release gallery."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import zipfile
from PIL import Image, ImageChops, ImageDraw, ImageFont
from gpu_comparison import make, NAMES, readback
from validate_gpu import runtime_fingerprint

ROOT=Path(__file__).resolve().parents[1]
TOWNS={'PALLET_TOWN','VIRIDIAN_CITY','PEWTER_CITY','CERULEAN_CITY','LAVENDER_TOWN',
       'VERMILION_CITY','CELADON_CITY','FUCHSIA_CITY','SAFFRON_CITY','CINNABAR_ISLAND'}


def validate_seating_report(report,inputs):
    """Accept only the passed current native five-person Cafe probe."""
    assert report['status']=='passed'and report['theme']=='gen3'and report['actors_rendered']is True
    assert report['type']=='native GSC cafe NPC seating and sprite GPU validation'
    assert report['runtime_inputs']==inputs,'Runtime changed after native Cafe seating validation'
    assert report['runtime_inputs_unchanged_during_probe']is True and not report['warnings']
    assert report['totals']['source_npcs']==15 and report['totals']['moved_npcs']==12 and report['totals']['unchanged_bar_npcs']==3
    assert len(report['fixtures'])==3 and{f['game']for f in report['fixtures']}=={'gold','silver','crystal'}
    expected={1:([9,3],[9,3],'left','SPRITE_SUPER_NERD'),
              2:([4,6],[4,5],'left','SPRITE_FISHER'),
              3:([1,7],[1,6],'right','SPRITE_FISHER'),
              4:([1,2],[1,1],'right','SPRITE_FISHER'),
              5:([4,3],[4,2],'left','SPRITE_TEACHER')}
    gs_scripts=[(25637,'5e:6425'),(25645,'5e:642d'),(25662,'5e:643e'),(25679,'5e:644f'),(25696,'5e:6460')]
    crystal_scripts=[(28745,'1c:7049'),(28753,'1c:7051'),(28770,'1c:7062'),(28787,'1c:7073'),(28804,'1c:7084')]
    for fixture in report['fixtures']:
        assert fixture['map']=='CELADON_CAFE'and fixture['actors_rendered']is True and fixture['native_actor_count']==5
        assert 'World.drawPersonEntry'in fixture['native_renderer']and'Npc.draw'in fixture['native_renderer']
        for key in ('original_restored','dispose_restored','original_map_and_object_definitions_unchanged','source_collision_events_unchanged'):
            assert fixture[key]is True,(fixture['game'],key)
        assert fixture['warm_source_art_checks']==0 and fixture['warm_pool_calls']==480
        actors=fixture['actors'];assert len(actors)==5 and{a['index']for a in actors}==set(expected)
        scripts=crystal_scripts if fixture['game']=='crystal'else gs_scripts
        for actor in actors:
            index=actor['index'];before,after,facing,sprite=expected[index]
            assert actor['id']==f'CELADON_CAFE_obj_{index}'and actor['sprite_id']==sprite
            assert actor['original']==before and actor['gen3']==after
            assert actor['original_facing']==actor['gen3_facing']==facing
            assert(actor['script'],actor['scriptKey'])==scripts[index-1]
            assert actor['moved']is(index!=1)and actor['source_identity_and_wardrobe_unchanged']is True
            assert actor['checked_sprite_pixels']>0
            if index!=1:assert actor['native_occupancy_and_talk_geometry']is True


def make_seating(fixture,output,scale=3):
    """Present actor-inclusive native readbacks separately from BG-only make()."""
    assert fixture['actors_rendered']is True and fixture['native_actor_count']==5
    assert scale in(2,3)and type(scale)is int
    before,after=readback(fixture['before']),readback(fixture['after'])
    assert before.size==after.size==(192,128)
    size=(before.width*scale,before.height*scale)
    left=before.resize(size,Image.Resampling.NEAREST);right=after.resize(size,Image.Resampling.NEAREST)
    padding,gap=18,20;width=padding*2+gap+size[0]*2
    fonts=Path('C:/Windows/Fonts')
    title_font=ImageFont.truetype(str(fonts/'arial.ttf'),20)
    font=ImageFont.truetype(str(fonts/'arial.ttf'),15)
    def lines(text,face,available):
        result=[];current=''
        for word in text.split():
            candidate=(current+' '+word).strip()
            if current and face.getlength(candidate)>available:result.append(current);current=word
            else:current=candidate
        return result+([current]if current else[])
    game=fixture['game'].capitalize()
    groups=[(lines('DEVELOPMENT — '+game+' / Celadon Café',title_font,width-padding*2),title_font,25,'#f5f7fa'),
            (lines(f'Actual native GPU backgrounds and NPC sprites; {scale}× nearest-neighbor pixels.',font,width-padding*2),font,18,'#c4cdd8'),
            (lines('Five original NPCs rendered in each panel. Table guests follow the raised chairs; original facings are preserved.',font,width-padding*2),font,18,'#c4cdd8')]
    labels_y=13+sum(len(text)*step+4 for text,face,step,color in groups)
    labels=[lines('Original '+game+' — native background + 5 NPCs',font,size[0]),
            lines('Gen 3 — retiled background + same 5 NPCs',font,size[0])]
    top=labels_y+max(map(len,labels))*18+12
    caption=lines('Four table guests moved up exactly one tile. Bar NPC unchanged. Original mode and disabling the mod restore native seating.',font,width-padding*2)
    canvas=Image.new('RGB',(width,top+size[1]+max(56,18+len(caption)*18)),'#18212b')
    draw=ImageDraw.Draw(canvas);y=13
    for text,face,step,color in groups:
        for line in text:draw.text((padding,y),line,font=face,fill=color);y+=step
        y+=4
    rx=padding+size[0]+gap
    for x,text in((padding,labels[0]),(rx,labels[1])):
        for index,line in enumerate(text):draw.text((x,labels_y+index*18),line,font=font,fill='#f5f7fa')
    canvas.paste(left,(padding,top));canvas.paste(right,(rx,top))
    for index,line in enumerate(caption):draw.text((padding,top+size[1]+15+index*18),line,font=font,fill='#c4cdd8')
    target=output/f'TileShift-Gen3-{game}-CeladonCafe-with-NPCs-comparison.png'
    canvas.save(target)
    saved=Image.open(target).convert('RGB')
    rectangles={}
    for name,panel,x in(('before',left,padding),('after',right,rx)):
        rectangle=(x,top,x+size[0],top+size[1]);rectangles[name]=list(rectangle)
        assert ImageChops.difference(saved.crop(rectangle),panel).getbbox()is None,'Saved native actor panel changed'
    return dict(game=fixture['game'],map=fixture['map'],output=str(target),scene_type='native background and five original NPCs',
        actors_rendered=True,native_actor_count=5,actors=copy.deepcopy(fixture['actors']),scale=scale,resampling='nearest-neighbor',
        panel_rectangles=rectangles,panels_exact_gpu_rgb=True,before_gpu_rgba_sha256=fixture['before']['rgba_sha256'],
        after_gpu_rgba_sha256=fixture['after']['rgba_sha256'],comparison_png_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        source_collision_events_unchanged=True,original_map_and_object_definitions_unchanged=True,
        original_seating_restored=True,dispose_seating_restored=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--report',type=Path,default=ROOT.parent/'.work/tileshift-v0300-gen2-gpu/report.json')
    p.add_argument('--output',type=Path,default=ROOT.parent/'.work/tileshift-v0300-comparisons')
    p.add_argument('--build',type=Path,default=ROOT/'build')
    p.add_argument('--seating-report',type=Path,help='Optional passed current native G/S/C Cafe report with all five NPCs')
    args=p.parse_args();report=json.loads(args.report.read_text())
    assert report['status']=='passed'and report['theme']=='gen3'
    inputs=runtime_fingerprint(ROOT)
    assert report['runtime_inputs']==inputs,'Runtime changed after native GPU validation'
    version=json.loads((ROOT/'manifest.json').read_text())['version']
    args.output.mkdir(parents=True,exist_ok=True);args.build.mkdir(parents=True,exist_ok=True)
    comparisons=[]
    for source in report['fixtures']:
        game,name=source['game'],source['map']
        if game!='crystal'and name not in TOWNS|{'LANCES_ROOM'}:continue
        assert source['coverage']['preserved_native_occurrences']==0
        NAMES[game,name]=(game.capitalize()+' / '+name.replace('_',' ').title(),
                         game.capitalize()+'-'+name.title().replace('_',''),
                         'Original '+game.capitalize()+' native DAY colors')
        fixture=copy.deepcopy(source)
        fixture['comparison_after_label']='Gen 3 - complete background'
        result=make(fixture,args.output.resolve())
        result['output']=Path(result['output']).name
        result.update(scene_type='background only',actors_rendered=False,native_actor_count=0)
        comparisons.append(result)
    seating=None
    if args.seating_report:
        seating=json.loads(args.seating_report.read_text());validate_seating_report(seating,inputs)
        for fixture in sorted(seating['fixtures'],key=lambda f:('gold','silver','crystal').index(f['game'])):
            result=make_seating(fixture,args.output.resolve())
            result['output']=Path(result['output']).name;comparisons.append(result)
    assert comparisons and len({r['output']for r in comparisons})==len(comparisons)
    metadata=dict(version=version,source_type=report['type'],native_gpu_checks=report['checks'],
                  runtime_inputs_sha256=inputs['sha256'],comparisons=comparisons,
                  source_report_sha256=hashlib.sha256(args.report.read_bytes()).hexdigest(),
                  pixel_scales=sorted({r['scale']for r in comparisons}),resampling='nearest-neighbor',
                  actors_rendered=seating is not None,actors_rendered_scope='Per scene; only files marked with-NPCs render actors',
                  scene_counts=dict(background_only=sum(not r['actors_rendered']for r in comparisons),with_native_npcs=sum(r['actors_rendered']for r in comparisons)))
    if seating:metadata['seating_gpu']=dict(source_type=seating['type'],native_gpu_checks=seating['checks'],
        source_report_sha256=hashlib.sha256(args.seating_report.read_bytes()).hexdigest(),totals=seating['totals'],
        runtime_inputs_sha256=seating['runtime_inputs']['sha256'])
    (args.output/'comparison-verification.json').write_text(json.dumps(metadata,indent=2)+'\n')
    (args.output/'README.txt').write_text(
        'TileShift '+version+' - Gen2 Kanto and shared interiors\n\n'
        'Original native DAY backgrounds and current complete Gen3 backgrounds.\n'
        'Background-only files use actual native renderer readbacks at exactly2x\n'
        'nearest-neighbor. All their visible background cells are replaced; no actors\n'
        'are rendered in those scenes. Each image and metadata identify actor scope.\n'
        +('The three Cafe files marked with-NPCs use native GPU backgrounds and all\n'
          'five real imported NPCs at exactly3x nearest-neighbor. Original panels\n'
          'show native seating; Gen3 panels move the four table guests up one tile\n'
          'with their chairs. The bar NPC stays put. Identities, sprites, palettes\n'
          'and original facings are preserved. Original mode and disabling restore\n'
          'the exact native scene. Source object/map definitions remain unchanged.\n'if seating else'')+
        'Scenes include Gold/Silver/Crystal Kanto towns and representative Crystal\n'
        'routes, rooms, transport, League and Johto interior corrections.\n'
        'Original gameplay geometry, collision, interactions and warps are preserved.\n'
        'Unmatched unique compact details retain original GSC geometry in Gen3 colors.\n'
        'Source pixels and saved comparison panels were independently verified.\n')
    archive=args.build/('TileShift-Gen2-Comparisons-v'+version+'.zip')
    names=[r['output']for r in comparisons]+['README.txt','comparison-verification.json']
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as bundle:
        for name in sorted(names):
            entry=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED
            entry.external_attr=0o100644<<16;bundle.writestr(entry,(args.output/name).read_bytes(),compresslevel=9)
    with zipfile.ZipFile(archive)as bundle:
        assert bundle.testzip()is None and set(bundle.namelist())==set(names)
        for r in comparisons:assert hashlib.sha256(bundle.read(r['output'])).hexdigest()==r['comparison_png_sha256']
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.zip.sha256').write_text(digest+'  '+archive.name+'\n')
    print(json.dumps(dict(images=len(comparisons),scene_counts=metadata['scene_counts'],archive=str(archive.resolve()),bytes=archive.stat().st_size,sha256=digest,
        crystal_cafe_with_npcs=str((args.output/'TileShift-Gen3-Crystal-CeladonCafe-with-NPCs-comparison.png').resolve())if seating else None)))

if __name__=='__main__':main()
