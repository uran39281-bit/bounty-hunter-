#!/usr/bin/env python3
"""Optimize host GS/memory/dispatch code in a separate diagnostic archive.

Use the existing verified compiler commands and exactly the same source/defines.
Do not change native game objects, baseline archive, time accounting or game state.
"""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build',type=Path)
    args=parser.parse_args();build=args.build.resolve()
    root=Path(__file__).resolve().parent;work=root/'fast-diagnostic-runtime';work.mkdir(exist_ok=True)
    names={'gs_frontend.cpp','gs_cpu_backend.cpp','ps2_memory.cpp','ps2_runtime.cpp','EeScheduler.cpp'}
    units=[u for u in json.loads((build/'compile_commands.json').read_text()) if Path(u['file']).name in names]
    if len(units)!=len(names):parser.error('Expected all five host runtime compile units')
    records=[]
    def compile_unit(unit):
        command=shlex.split(unit['command']);source=Path(unit['file']);obj=work/(source.name+'.o')
        optimization=[i for i,t in enumerate(command) if t in ['-O0','-O1','-O2','-O3','-Og','-Os']]
        if len(optimization)!=1:raise ValueError('Unexpected optimization options')
        command[optimization[0]]='-O2';command[command.index('-o')+1]=str(obj)
        result=subprocess.run(command,cwd=unit['directory'],capture_output=True,text=True)
        (work/(source.name+'.log')).write_text(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError('Compile failed: '+source.name)
        return {'source':source.name,'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'object':str(obj),'command':command}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        for record in executor.map(compile_unit,units):records.append(record);print('Compiled '+record['source'],flush=True)
    baseline=build/'ps2xRuntime/libps2_runtime.a';archive=work/baseline.name
    members=subprocess.check_output(['ar','t',str(baseline)],text=True).splitlines()
    for record in records:
        if members.count(Path(record['object']).name)!=1:raise ValueError('Missing or duplicate baseline archive member')
    shutil.copyfile(baseline,archive)
    subprocess.run(['ar','r',str(archive),*[r['object'] for r in records]],check=True)
    subprocess.run(['ranlib',str(archive)],check=True)
    report={'baseline_archive_unchanged':True,'baseline_sha256':hashlib.sha256(baseline.read_bytes()).hexdigest(),'optimized_archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'optimization':'-O2; no fast-math','native_game_objects_unchanged':True,'units':records}
    (root/'fast-diagnostic-runtime.json').write_text(json.dumps(report,indent=2)+'\n');print(archive,flush=True)

if __name__=='__main__':main()
