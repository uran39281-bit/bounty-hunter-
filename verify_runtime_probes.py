#!/usr/bin/env python3
"""Reproduce installers from pinned source and compare every changed runtime byte."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

COMMIT = '2c5fbb9389e11dd95693385969490c9e8e6f57b4'
INSTALLERS = [
    'install_memcpy_probe.py', 'install_vfs_probe.py', 'install_boot_sifcmd_probe.py',
    'install_iop_snapshot_probe.py', 'install_iop_execution_probe.py',
    'install_iop_import_trace.py', 'install_spu2_adma_timing.py',
    'install_scratchpad_receive.py', 'install_boot_cdvdfsv_probe.py', 'install_ee_thread_probe.py',
    'install_ee_zero_priority.py', 'install_cdvd_imports.py', 'install_ee_exit_probe.py', 'install_ee_return_probe.py', 'install_callback_heap_stacks.py',
    'install_cop0_count.py', 'install_boot_graphics_trace.py', 'install_graphics_dma_trace.py',
]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo',type=Path)
    parser.add_argument('--report',type=Path,default=Path('probe-installation-check.json'))
    args=parser.parse_args(); repo=args.repo.resolve(); root=Path(__file__).resolve().parent
    def git(*commands):
        return subprocess.check_output(['git','-C',str(repo),*commands])
    if git('rev-parse','HEAD').decode().strip()!=COMMIT:
        parser.error('Use pinned PS2Recomp source')
    paths=git('diff','--name-only').decode().splitlines()
    paths=[p for p in paths if p!='ps2xRuntime/src/runner/register_functions.cpp']
    expected=[
        'ps2xRuntime/src/lib/Kernel/Stubs/LibC.cpp', 'ps2xRuntime/src/lib/ps2_vfs.cpp',
        'ps2xRuntime/src/lib/Kernel/Stubs/SIF.cpp', 'ps2xIOP/src/emulator/core/iop_kernel.h',
        'ps2xIOP/src/emulator/services/iop_rpc.h', 'ps2xIOP/src/emulator/iop_emulator.h',
        'ps2xIOP/src/emulator/iop_emulator.cpp', 'ps2xIOP/src/iop_subsystem.cpp',
        'ps2xIOP/src/emulator/core/iop_memory.cpp', 'ps2xRuntime/src/lib/Kernel/Stubs/DMA.cpp',
        'ps2xRuntime/src/lib/Kernel/Syscalls/Thread.cpp', 'ps2xRuntime/src/lib/Kernel/EeScheduler.cpp',
        'ps2xIOP/src/emulator/imports/iop_cdvd.cpp', 'ps2xRuntime/src/lib/ps2_runtime.cpp',
        'ps2xRuntime/src/lib/ps2_memory.cpp', 'ps2xRuntime/src/lib/ps2_vif1_interpreter.cpp',
    ]
    if sorted(paths)!=sorted(expected): raise ValueError('Unexpected modified runtime file list')
    with tempfile.TemporaryDirectory(prefix='bounty-probes-') as tmp:
        target=Path(tmp)
        for name in paths:
            path=target/name;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(git('show',f'{COMMIT}:{name}'))
        for script in INSTALLERS:
            subprocess.run([sys.executable,str(root/script),str(target)],check=True)
        rows=[]
        for name in paths:
            actual=(repo/name).read_bytes();reproduced=(target/name).read_bytes()
            if actual!=reproduced: raise ValueError('Installer differs from built source: '+name)
            rows.append({'source':name,'sha256':hashlib.sha256(actual).hexdigest()})
        patch=git('diff','--',*paths)
        (root/'runtime-experiment.patch').write_bytes(patch)
        # Validate the alternative patch route independently.
        for name in paths: (target/name).write_bytes(git('show',f'{COMMIT}:{name}'))
        subprocess.run(['git','apply',str(root/'runtime-experiment.patch')],cwd=target,check=True)
        for name in paths:
            if (target/name).read_bytes()!=(repo/name).read_bytes():
                raise ValueError('Patch route differs: '+name)
    report={'pinned_source_installation_reproduces_current_patches':True,
            'alternative_patch_reproduces_current_patches':True,'pinned_commit':COMMIT,
            'installers':INSTALLERS,'files':rows}
    args.report.write_text(json.dumps(report,indent=2)+'\n')
    print(f'PASS: {len(paths)} source files reproduced exactly by installers and patch')


if __name__=='__main__': main()
