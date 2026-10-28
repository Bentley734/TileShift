"""Extract native-size pier boards from the route sheet supplied by the user."""
import argparse,json
from pathlib import Path
from PIL import Image
import catalog
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);args=p.parse_args();image=Image.open(args.source).convert('RGBA');assert image.size==(464,272)
 tile=image.crop((272,160,288,176));assert tile.getchannel('A').getextrema()==(255,255)
 folder=ROOT/'assets/third_party/peekychew';folder.mkdir(parents=True,exist_ok=True);path=folder/'pier-boards.png';tile.save(path)
 edge=Image.new('RGBA',(16,16));edge.paste(tile.crop((0,0,16,8)),(0,0));edge_path=folder/'pier-edge.png';edge.save(edge_path)
 proof={'artist':'Peekychew','source_url':'https://www.deviantart.com/peekychew','source_file':args.source.name,'source_sha256':catalog.sha(args.source.read_bytes()),'authorization':'User supplied this public route asset sheet and explicitly authorized its use for fences, steps and other useful assets.','crop':[272,160,288,176],'size':[16,16],'scale':1,'edge':'Upper8px board strip; transparent lower8px reveals the same animated sea as adjoining water.','purpose':'Unscaled complete wooden-board pattern for Route32 fishing piers. Source ladder/walk permissions and all original fishing positions remain unchanged.','files':{path.name:catalog.sha(path.read_bytes()),edge_path.name:catalog.sha(edge_path.read_bytes())}};(folder/'provenance.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))
if __name__=='__main__':main()
