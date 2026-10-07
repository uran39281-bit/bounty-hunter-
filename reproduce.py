#!/usr/bin/env python3
"""Reproduce this private static-recompilation experiment, not a playable port."""
import argparse
import hashlib
import shutil
import subprocess
from pathlib import Path

PIN = '2c5fbb9389e11dd95693385969490c9e8e6f57b4'
EXPECTED = '51c56737105d1186f0b14155e39d8af67e63b12c4ac0543e1f0e178ccd6a4304'


def run(args, root):
    print('Running:', ' '.join(map(str,args)),flush=True)
    subprocess.run(list(map(str,args)),cwd=root,check=True)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('executable',type=Path,help='Original SLUS_204.20 from your disc')
    p.add_argument('--cmake',default='cmake')
    p.add_argument('--jobs',default='4')
    a=p.parse_args()
    exe=a.executable.resolve()
    if hashlib.sha256(exe.read_bytes()).hexdigest()!=EXPECTED:
        raise SystemExit('Different executable revision: do not reuse this inferred boundary blindly.')
    root=Path(__file__).resolve().parent
    repo=root/'PS2Recomp'
    if not repo.exists():
        run(['git','clone','https://github.com/ran-j/PS2Recomp.git',repo],root)
    run(['git','-C',repo,'checkout','--detach',PIN],root)
    build=repo/'build-tools'
    run([a.cmake,'-S',repo,'-B',build,'-DCMAKE_BUILD_TYPE=Release','-DPS2X_BUILD_RUNTIME=OFF','-DPS2X_BUILD_TEST=OFF','-DPS2X_BUILD_STUDIO=OFF'],root)
    run([a.cmake,'--build',build,'--target','ps2_analyzer','ps2_recomp','-j',a.jobs],root)
    analysis=root/'SLUS_204.20.analysis.elf'
    run(['python3',root/'split_analysis_elf.py',exe,analysis],root)
    config=root/'reproduced-config.toml'
    run([build/'ps2xAnalyzer'/'ps2_analyzer',analysis,config],root)
    run([build/'ps2xRecomp'/'ps2_recomp',config],root)
    print('Translation generated. This does not validate execution or create an Android APK.')


if __name__=='__main__':
    main()
