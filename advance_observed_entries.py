#!/usr/bin/env python3
"""Iterate bounded native startup, exposing only verified missing instruction entries."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from generate_leaf_entries import generate


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo',type=Path);parser.add_argument('build',type=Path);parser.add_argument('disc',type=Path)
    parser.add_argument('--entry',type=lambda s:int(s,0),action='append',required=True)
    parser.add_argument('--attempts',type=int,default=8);parser.add_argument('--seconds',type=int,default=30)
    args=parser.parse_args();root=Path(__file__).resolve().parent;entries=sorted(set(args.entry));history=[]
    output=root/'leaf-output/observed_leaf_entries.cpp'
    for attempt in range(args.attempts):
        evidence=generate(root/'original/SLUS_204.20',entries,output,root/'corrected-output')
        (root/'observed-leaf-entries.json').write_text(json.dumps(evidence,indent=2)+'\n')
        count=len(entries);report=root/f'cdvd-auto-entry-{count:02d}.json'
        with (root/f'cdvd-auto-entry-{count:02d}-link.log').open('w') as log:
            subprocess.run([sys.executable,str(root/'link_headless.py'),str(args.repo.resolve()),str(args.build.resolve()),'--leaf-entries',str(output)],stdout=log,stderr=subprocess.STDOUT,check=True)
        cmd=[sys.executable,str(root/'run_startup.py'),'--runner',str(root/'headless-startup'),'--disc',str(args.disc.resolve()),'--report',str(report),'--seconds',str(args.seconds),
             '--stop-invalid-copy','--reuse-file-descriptors','--boot-sifcmd','--boot-cdvdfsv','--cdvd-compat','--inspect-iop','--adma-timing','--scratchpad-receive','--trace-ee-threads','--trace-iop-imports','--allow-zero-priority','--trace-files','--separate-callback-stacks','--capture-frame',str(root/'first-game-frame.ppm')]
        subprocess.run(cmd,stdout=subprocess.DEVNULL,check=True)
        result=json.loads(report.read_text())
        misses=re.findall(r'\[guest-branch:missing-target\][^\n]*?target=(0x[0-9a-f]+)',result['stderr'])
        rows={'report':report.name,'entries':[hex(a) for a in entries],'next_missing':misses[-1] if misses else None,'captured_frame':result['captured_frame_exists'],'returncode':result['returncode']}
        history.append(rows);(root/'observed-entry-progression.json').write_text(json.dumps(history,indent=2)+'\n')
        print(json.dumps(rows),flush=True)
        if not misses:break
        target=int(misses[-1],0)
        if target in entries:raise ValueError('Registered entry remains missing; stop and inspect')
        entries=sorted(set(entries+[target]))


if __name__=='__main__':main()
