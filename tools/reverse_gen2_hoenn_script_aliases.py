"""Reuse exact reviewed Crystal art for identical source states in the same atlas."""
from pathlib import Path
import argparse
import copy
import json

from classic_geometry_review import static_manifest
from coverage import active_rows
from johto_remaining_review import artwork
from reverse_common import ROOT, ReverseReview
import preview


GAMES = ('ruby', 'sapphire', 'emerald')
OUT = ROOT.parent / '.work/tileshift-v0420-rse-runtime-audit/alias-candidate'
GUARDS = Path(__file__).with_name('reverse_gen2_hoenn_script_aliases_guards.json')


class Review(ReverseReview):
    def __init__(self, baseline):
        super().__init__('gen2-hoenn-script-aliases', GAMES)
        self.out = OUT
        self.out.mkdir(parents=True,exist_ok=True)
        _, rows = active_rows(baseline)
        self.current = {(r['game'], r['tileset'], r['id']): r for r in rows
                        if r['game'] in GAMES and r['style'] == 'gen2'}

    def build(self):
        guards = json.loads(GUARDS.read_text(encoding='utf-8'))
        for guard in guards:
            game, pair, mid = (guard[k] for k in ('game', 'pair', 'mid'))
            assert (game, pair, mid) not in self.current
            basis = guard['basis_mid']
            original = self.current[game, pair, basis]
            assert original['role'] == guard['basis_role'] and original['sourceHash'] == guard['sourceHash']
            bank = self.imp.cell_index(game)
            expected = guard['sourceHash'], guard['sourceLayers'], guard['sourceBehavior']
            for id in (basis, mid):
                source = bank[pair, id]
                assert tuple(source[field] for field in ('pixel_sha256','layer_sha256','behavior')) == expected
            art = artwork(original)
            art.update({field: original[field] for field in ('classicGeometry','overMask','animationCategory')
                        if field in original})
            if original['role']=='reverse_gen2_hoenn_named_new_mauville_animated_generator_indicators':
                assert mid in {752,755} and basis in {728,731}
                # The exact parked indicator art matches an animated frame,
                # but these two script MIDs have no native animation owner.
                geometry = copy.deepcopy(art['classicGeometry'])
                assert geometry.pop('sourceAnimation')['mode']=='static_equivalent'
                preview.native_donor(self.cache,dict(game=game,tileset=pair,id=mid,hash=guard['sourceHash']),self.packed)
                assert geometry['animationManifestHash']==static_manifest(self.cache,game,pair,mid,self.packed)
                art['classicGeometry']=geometry
            art['role'] = original['role']
            self.row(game,pair,mid,'gen2',art,
                     'The imported script state has identical complete source pixels, priority planes and behavior in the same atlas as its checked Crystal counterpart.')
        assert len(self.rows) == len(guards)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, default=ROOT)
    args = parser.parse_args()
    review = Review(args.baseline)
    review.build()
    print(review.validate())
    review.write(OUT / 'candidate.lua')


if __name__ == '__main__':
    main()
