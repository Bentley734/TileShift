"""Frozen native Crystal rock silhouettes, independent of displayed palettes.

These masks remove only the connected exterior backing of complete native
objects. Dark outlines, interior brown shading and enclosed highlights remain.
They are authoring-time geometry; runtime recipes use bounded cached parts.
"""
from __future__ import annotations

import hashlib

OUTCROP_HASHES=(
    'c098da81d1e2b62642eaf1a9c03005efb8fe34c13d0985c9274dd81c8be7a9a7',
    'd0cde5cdee229d42dd4d90e6d9909f52fb6443621977d1dbe4e56b011bccfd73',
    '798362c2866c23e68df6dbbff089c23e0d9c885a8e631eb3f6dd610356dc6d59',
    '2a3c4ebcb4580fd26d8460d9220ee2a234fadf5635961a43142a43655e6563c7',
)
BOULDER_HASH='7ad1c2c69f2f5be229423a136197c62116f24a4488a516dd868f7c1377452086'
KANTO_CORNER_HASHES={
    104:'201860ccdb904144752d1819c759111bdaf98426bf84c098fd02a40832322a1d',
    106:'e5caf9afdb058e6a5e8b45c4bb07b3f19448e7633a1a92110cc30a96874d5de8',
    120:'02c9c3102adef09047e3a3c013fd4b6bf72dce10ae62c91a8e6dcfb4f0be6ae1',
    122:'bcae2fd247b9679ec1fd4b47f352a9d484cb03a6d583befb9fdba32c1f6c7bd2',
}

# Inclusive row bounds traced against the complete native objects. These
# preserve every dark outline pixel, including the irregular lower rock feet.
OUTCROP_BOUNDS=(
    (8,23),(6,25),(4,27),(3,28),(2,29),(1,30),(1,30),
    *((0,31),)*20,
    (1,30),(1,30),(2,29),(3,28),(5,26),
)
BOULDER_BOUNDS=tuple(zip(
    (6,4,3,2,1,1,1,0,0,0,0,0,0,1,1,2),
    (10,11,12,13,14,14,15,15,15,15,15,15,15,15,14,12),
))
assert len(OUTCROP_BOUNDS)==32 and len(BOULDER_BOUNDS)==16


def bounds_mask(bounds):
    width=len(bounds)
    mask=[bounds[y][0]<=x<=bounds[y][1]for y in range(width)for x in range(width)]
    outside={(x,y)for y in range(width)for x in range(width)if not mask[y*width+x]}
    visited=set();queue=[p for p in outside if p[0]in(0,width-1)or p[1]in(0,width-1)]
    while queue:
        p=queue.pop()
        if p in visited:continue
        visited.add(p);x,y=p
        queue.extend(q for q in((x-1,y),(x+1,y),(x,y-1),(x,y+1))if q in outside and q not in visited)
    assert visited==outside,'An object silhouette may remove only connected exterior backing'
    return mask


OUTCROP_MASK=bounds_mask(OUTCROP_BOUNDS)
# Preserve the earlier connected field transparency too. These five shade0
# pixels are the original whole-object exterior components; enclosed white
# rock highlights are deliberately not part of this set.
OUTCROP_EXISTING_FIELD_OUTSIDE=(320,384,576,640,1023)
for index in OUTCROP_EXISTING_FIELD_OUTSIDE:OUTCROP_MASK[index]=False
BOULDER_MASK=bounds_mask(BOULDER_BOUNDS)
# These are complete native stair-stepped corner cells, not their individual
# 8px glyphs. Shared glyph60/75/77 remain opaque when enclosed in plateau113,
# straight walls or concave continuation modules. Both copies of top cap43/45
# have a full exterior checker first row; the first 104/106 row is empty.
_LEFT104=(16,14,12,11,10,9,9,8,8,6,4,3,2,1,1,0)
_LEFT120=(0,0,0,0,0,0,0,0,0,0,0,1,1,2,3,5)
KANTO_CORNER_MASKS={
    104:bounds_mask(tuple((x,15)for x in _LEFT104)),
    106:bounds_mask(tuple((0,15-x)for x in _LEFT104)),
    120:bounds_mask(tuple((x,15)for x in _LEFT120)),
    122:bounds_mask(tuple((0,15-x)for x in _LEFT120)),
}


def mask_digest(mask):
    return hashlib.sha256(bytes(mask)).hexdigest()


def quadrant_mask(q):
    assert 0<=q<=3
    return [OUTCROP_MASK[(q//2*16+y)*32+q%2*16+x]for y in range(16)for x in range(16)]
