"""Integrate reviewed interior modules, removing exact duplicate source rows.

Runs offline, keeps every unrelated serialized byte, validates the combined
main-loaded Mapping.index before activation, and records all removed rows.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re

import catalog
import preview

ROOT=Path(__file__).resolve().parents[1]
FIELDS=('game','style','tileset','id','quadrant','map','x','y')
GUARDS=FIELDS+('sourceHash','sourceFiles','sourceCollision','sourcePriority','sourcePalettes')


def key(row):
    return tuple(row.get(k)for k in FIELDS)


def literal_rows(text):
    """Find row-shaped literal tables without interpreting braces in strings."""
    stack=[];i=0
    while i<len(text):
        c=text[i]
        if text.startswith('--',i):
            if text.startswith('--[[',i):
                end=text.find(']]',i+4);assert end>=0;i=end+2
            else:
                end=text.find('\n',i);i=len(text)if end<0 else end+1
            continue
        if c in ('"',"'"):
            quote=c;i+=1
            while i<len(text):
                if text[i]=='\\':i+=2
                elif text[i]==quote:i+=1;break
                else:i+=1
            continue
        if c=='['and stack:
            match=re.match(r'''\[\s*["'](game|style|tileset|id|quadrant|sourceHash)["']\s*\]\s*=''',text[i:i+45])
            if match:stack[-1][1].add(match[1])
        if c=='{':stack.append([i,set()])
        elif c=='}':
            assert stack,'Unbalanced literal table'
            start,fields=stack.pop()
            if {'game','style','tileset','id','quadrant','sourceHash'}<=fields:
                yield start,i+1
        i+=1
    assert not stack,'Unclosed literal table'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--module',action='append',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--activate',action='store_true')
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    main_path=ROOT/'main.lua';main_before=main_path.read_bytes();main_text=main_before.decode()
    modules=list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",main_text)))
    assert not(set(args.module)&set(modules)),'Audit module already integrated'
    old={};sources={};indexed={}
    for module in modules:
        sources[module]=(ROOT/module).read_bytes()
        rows=catalog.plain(catalog.LUA.execute(sources[module].decode()))
        rows=[]if rows=={}else rows
        old[module]=rows
        for index,row in enumerate(rows):
            assert key(row)not in indexed,'Existing exact duplicate'
            indexed[key(row)]=(module,index,row)
    removals=defaultdict(dict);new=[];audit_sources={}
    for module in args.module:
        assert module.startswith('mappings/')and(ROOT/module).is_file()
        audit_sources[module]=(ROOT/module).read_bytes()
        audit_rows=catalog.plain(catalog.LUA.execute(audit_sources[module].decode()))
        for row in ([]if audit_rows=={}else audit_rows):
            assert key(row)not in{key(r)for r in new},'Audit modules overlap'
            new.append(row)
            prior=indexed.get(key(row))
            if prior:
                oldmodule,index,oldrow=prior
                assert all(row.get(k)==oldrow.get(k)for k in GUARDS),'Source guard changed'
                removals[oldmodule][key(row)]=(index,oldrow)
    proposals={};proof=[]
    for module,targets in removals.items():
        text=sources[module].decode();intervals=[];found=set()
        for start,end in literal_rows(text):
            row=catalog.plain(catalog.LUA.execute('return '+text[start:end]))
            target=targets.get(key(row))
            if target:
                assert row==target[1],'Literal differs from executed row'
                assert key(row)not in found;found.add(key(row))
                stop=end
                while stop<len(text)and text[stop].isspace():stop+=1
                if stop<len(text)and text[stop]==',':end=stop+1
                else:
                    previous=start-1
                    while previous>=0 and text[previous].isspace():previous-=1
                    if previous>=0 and text[previous]==',':start=previous
                intervals.append((start,end))
                proof.append(dict(module=module,old_index=target[0],old_row=row,
                    old_row_sha256=hashlib.sha256(json.dumps(row,sort_keys=True,separators=(',',':')).encode()).hexdigest()))
        assert found==set(targets),f'Unlocated literal rows in {module}: {set(targets)-found}'
        merged=[]
        for start,end in sorted(intervals):
            if merged and start<=merged[-1][1]:merged[-1]=(merged[-1][0],max(end,merged[-1][1]))
            else:merged.append((start,end))
        for start,end in reversed(merged):text=text[:start]+text[end:]
        after=catalog.plain(catalog.LUA.execute(text));after=[]if after=={}else after
        expected=[row for row in old[module]if key(row)not in targets]
        assert after==expected,'Unrelated rows changed'
        proposals[module]=text.encode()
    marker=b'  }) do'
    assert main_before.count(marker)==1
    addition=('    '+','.join(repr(m)for m in args.module)+',\n').encode()
    main_after=main_before.replace(marker,addition+marker)
    combined=[]
    for module in modules:
        combined.extend(row for row in old[module]if key(row)not in removals.get(module,{}))
    combined.extend(new)
    lua_rows=catalog.LUA.table_from([catalog.LUA.table_from(r,recursive=True)for r in combined])
    mapping=catalog.LUA.execute((ROOT/'lib/mapping.lua').read_text())
    _,errors=mapping.index(lua_rows);assert not catalog.plain(errors),catalog.plain(errors)
    report=dict(new_modules=args.module,new_rows=len(new),removed_rows=len(proof),
        indexed_rows=len(combined),index_errors=0,removed=proof,
        changed_existing_modules=list(proposals),unrelated_rows_unchanged=True,
        untouched_module_count=len(modules)-len(proposals))
    (args.output/'integration-proof.json').write_text(json.dumps(report,indent=2)+'\n')
    if args.activate:
        assert main_path.read_bytes()==main_before
        for module in modules:assert(ROOT/module).read_bytes()==sources[module]
        for module,content in audit_sources.items():assert(ROOT/module).read_bytes()==content,'Audit module changed after validation'
        for module,content in proposals.items():(ROOT/module).write_bytes(content)
        main_path.write_bytes(main_after)
    print(json.dumps({k:v for k,v in report.items()if k!='removed'},indent=2))


if __name__=='__main__':main()
