#!/usr/bin/env python3
"""Privately preserve built objects and their native link command for incremental work."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-directory',required=True,type=Path)
    parser.add_argument('--ninja',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    directory=args.build_directory.resolve()
    commands=subprocess.check_output([str(args.ninja),'-C',str(directory),'-t','commands','ps2EntryRunner'],text=True).splitlines()
    link=next(command for command in reversed(commands) if ' -shared ' in command and 'libps2EntryRunner.so' in command)
    entries=sorted([p for p in directory.rglob('*') if p.is_file() and p.suffix in ('.o','.a')])
    if not entries: raise ValueError('Native objects have not been built')
    manifest={'original_build_directory':str(directory),'link_command':link,
        'contains_private_translated_game_objects':True,
        'files':[{ 'path':p.relative_to(directory).as_posix(),'bytes':p.stat().st_size,
                  'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in entries]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    report=args.output.with_suffix('.json'); report.write_text(json.dumps(manifest,indent=2)+'\n')
    with tarfile.open(args.output,'w:xz',preset=3) as archive:
        archive.add(report,arcname='link-cache.json')
        for path in entries: archive.add(path,arcname=path.relative_to(directory).as_posix(),recursive=False)
        metadata=[directory/'compile_commands.json']
        metadata += sorted(directory.rglob('Unity/*.cxx'))
        metadata += sorted(directory.rglob('cmake_pch.hxx'))
        for path in metadata:
            if path.is_file(): archive.add(path,arcname=path.relative_to(directory).as_posix(),recursive=False)
    print(json.dumps({'object_count':len(entries),'object_bytes':sum(p.stat().st_size for p in entries),
        'cache_bytes':args.output.stat().st_size,'archive_sha256':hashlib.sha256(args.output.read_bytes()).hexdigest()}))

if __name__=='__main__': main()
