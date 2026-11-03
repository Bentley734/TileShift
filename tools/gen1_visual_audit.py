"""Capture every main-selected Red/Blue/Yellow map for the Gen3 art audit."""
import sys
from gen2_interior_visual_audit import main

if __name__=='__main__':
    sys.argv.extend(['--games','red','blue','yellow','--all-maps'])
    main()
