#!/usr/bin/env python3
"""Load the user's original LOADFILE IRX after SIFCMD and CDVDFSV at IOP reset."""
import argparse
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('repo',type=Path)
    repo=p.parse_args().repo.resolve()
    sif=repo/'ps2xRuntime/src/lib/Kernel/Stubs/SIF.cpp'
    text=sif.read_text()
    marker='// BOUNTY_BOOT_LOADFILE: execute the original supplied service; retain SDK retry semantics.'
    if marker not in text:
        block='''        // BOUNTY_BOOT_LOADFILE: execute the original supplied service; retain SDK retry semantics.
        if (runtime && std::getenv("PS2X_LOAD_BOOT_LOADFILE"))
        {
            const auto boot = runtime->loadIopModule("cdrom0:\\\\BOOT\\\\LOADFILE.IRX;1");
            std::cerr << "BOOT_LOADFILE handled=" << boot.handled
                      << " id=" << boot.moduleId << " start=" << boot.startResult
                      << " ready=" << PS2IopTransport::canBindRpc(runtime, 0x80000006u) << '\\n';
        }
'''
        for name in ('sceSifRebootIop','sceSifResetIop'):
            start=text.index('    void '+name+'(')
            end=text.index('\n    void ',start+10)
            part=text[start:end]
            old='        setReturnS32(ctx, 1);'
            if part.count(old)!=1: raise ValueError('Unexpected reset hook: '+name)
            text=text[:start]+part.replace(old,block+old)+text[end:]
        sif.write_text(text)
    android=repo/'ps2xRuntime/src/lib/ps2_android_runtime.cpp'
    text=android.read_text()
    if '"PS2X_LOAD_BOOT_LOADFILE"' not in text:
        text=text.replace('"PS2X_LOAD_BOOT_CDVDFSV",','"PS2X_LOAD_BOOT_CDVDFSV","PS2X_LOAD_BOOT_LOADFILE",',1)
        android.write_text(text)
    print('Installed original LOADFILE boot hook in both IOP reset paths')

if __name__=='__main__':main()
