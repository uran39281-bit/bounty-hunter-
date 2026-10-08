#!/usr/bin/env python3
"""Run the original private LOADFILE IRX and its version RPC in the pinned IOP runtime."""
import argparse
import json
import os
from pathlib import Path
import subprocess

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('repo','modules','test-support','work-directory'):
        p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--cmake',default='cmake')
    p.add_argument('--ninja',default='ninja')
    a=p.parse_args();root=Path(__file__).resolve().parent
    work=a.work_directory.resolve();work.mkdir(parents=True,exist_ok=False)
    iop=a.repo.resolve()/'ps2xIOP'
    build=work/'build'
    subprocess.run([a.cmake,'-S',str(iop),'-B',str(build),'-G','Ninja',
        '-DCMAKE_BUILD_TYPE=Release','-DCMAKE_MAKE_PROGRAM='+str(Path(a.ninja).resolve())],check=True)
    subprocess.run([a.cmake,'--build',str(build),'-j2'],check=True)
    binary=work/'probe'
    subprocess.run(['g++','-std=c++20','-O2','-I',str(iop/'include'),
        '-I',str(a.test_support.resolve()),str(root/'probe_loadfile_boot.cpp'),
        str(build/'libps2_iop.a'),'-o',str(binary)],check=True)
    env=os.environ.copy();env['PS2X_CDVD_COMPAT']='1'
    run=subprocess.run([str(binary),str(a.modules.resolve())],env=env,
        capture_output=True,text=True,timeout=30)
    (work/'result.log').write_text(run.stdout+run.stderr)
    print(json.dumps({'returncode':run.returncode,'original_IRX_execution':True,
        'checks':'missing server, original startup, version RPC 0xff, reset and reload',
        'phone_tested':False,'stdout':run.stdout,'stderr':run.stderr}))
    return run.returncode

if __name__=='__main__':raise SystemExit(main())
