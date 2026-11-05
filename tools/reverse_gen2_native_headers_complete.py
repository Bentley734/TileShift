"""Eleven explicitly reviewed native map-border canvases, never body tiles."""
from pathlib import Path
from collections import Counter
import argparse,copy,json,re,struct,zlib
from PIL import Image
import catalog,preview
from reverse_common import ReverseReview,ROOT

TARGET=ROOT/'mappings/reverse_gen2_native_headers_complete.lua'
GUARDS=ROOT/'tools/reverse_gen2_native_headers_guards.json'
OUT=ROOT.parent/'.work/tileshift-v0360-headers'

class Review(ReverseReview):
    def __init__(self):
        super().__init__('gen2-native-headers-complete',('ruby','sapphire','emerald','firered','leafgreen'))
        self.out=OUT;OUT.mkdir(exist_ok=True)
    def build(self):
        guards=json.loads(GUARDS.read_text());assert len(guards)==11
        occupied={}
        for path in dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(ROOT/'main.lua').read_text())):
            if ROOT/path==TARGET:continue
            for row in preview.read_reviewed(ROOT/path):
                if row['style']=='gen2'and row['game']in self.games:occupied[row['game'],row['tileset'],row['id']]=row
        black=copy.deepcopy(next(row['donor']for row in occupied.values()if row.get('role')=='reverse_gen2_exact_black_canvas'))
        assert set(self.gb_image(black).getdata())=={(0,0,0,255)}
        sky=self.gb_at('crystal','TIN_TOWER_ROOF',0,0)
        assert len(set(self.gb_image(sky).getdata()))==1
        for item in guards:
            g,p,m=item['game'],item['pair'],item['mid'];assert(g,p,m)not in occupied
            cell=self.imp.cell_index(g)[p,m]
            assert cell['pixel_sha256']==item['sourceHash']and cell['layer_sha256']==item['sourceLayers']and cell['behavior']==item['sourceBehavior']
            body_count=0;headers={}
            for name,spec in self.imp.table(g,'gba/native/manifest')['layouts'].items():
                if spec['pair']!=p:continue
                raw=(self.cache/g/'data/generated/gba/native'/spec['file']).read_bytes();blob=raw if raw[:4]==b'SVML'else zlib.decompress(raw)
                sw,sh,w,h=struct.unpack_from('<HHHH',blob,6);w,h=w or sw,h or sh;start=16+blob[14]*blob[15]*2
                body_count+=sum(struct.unpack_from('<H',blob,start+(y*sw+x)*4)[0]==m for y in range(h)for x in range(w))
                if any(struct.unpack_from('<H',blob,16+i*2)[0]==m for i in range(blob[14]*blob[15])):headers[name]=catalog.sha(raw)
            assert body_count==0 and headers==item['headers'],'Header-only source context changed'
            meaning='complete native Crystal Tin Tower rooftop exterior sky canvas'if item['target']=='roof_sky'else'complete native Crystal empty outside-room black canvas'
            art=self.native(sky if item['target']=='roof_sky'else black,'reverse_gen2_explicit_native_header_'+item['target']);art['overMask']='0'*256
            row=self.row(g,p,m,'gen2',art,
                'Individually reviewed header-only source: '+meaning+'. The exact source is a uniform border canvas, absent every logical map-body cell. Museum, sealed-chamber and facility outside-room voids use the existing exact native black donor; the Trainer Tower roof exterior uses the actual native Crystal rooftop exterior. All named source layouts, header occurrences, source RGB/layers and behavior are frozen. No playable floor, sky object, prop, wall or collision is inferred from a flat color.')
            row['nativeHeaderCompletion']=dict(headers=headers,logical_body_cells=0,target=item['target'])
        assert len(self.rows)==11
        self.write(OUT/'candidate.lua')
        return 11

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--validate',action='store_true');p.add_argument('--activate',action='store_true');a=p.parse_args();assert not a.activate or a.validate
    r=Review();r.build();proof=r.validate()if a.validate else None
    if a.activate:r.write(TARGET)
    print(json.dumps(dict(rows=11,proof=proof,activated=a.activate)))
if __name__=='__main__':main()
