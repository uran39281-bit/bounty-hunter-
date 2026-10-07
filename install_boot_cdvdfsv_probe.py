#!/usr/bin/env python3
"""Opt-in execution of supplied CDVDFSV after SIFCMD at IOP reset."""
import argparse
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo',type=Path)
    args=parser.parse_args()
    path=args.repo/'ps2xRuntime/src/lib/Kernel/Stubs/SIF.cpp'
    text=path.read_text()
    if 'BOUNTY_BOOT_CDVDFSV_PROBE' in text:
        print('CDVDFSV boot probe already installed')
        return
    old='''                      << " id=" << boot.moduleId << " start=" << boot.startResult << '\\n';
        }
        setReturnS32(ctx, 1);'''
    new=r'''                      << " id=" << boot.moduleId << " start=" << boot.startResult << '\n';
        }
        // BOUNTY_BOOT_CDVDFSV_PROBE: run supplied IRX; never synthesize RPC servers.
        if (runtime && std::getenv("PS2X_LOAD_BOOT_CDVDFSV"))
        {
            const auto boot = runtime->loadIopModule("cdrom0:\\BOOT\\CDVDFSV.IRX;1");
            std::cerr << "BOOT_CDVDFSV handled=" << boot.handled
                      << " id=" << boot.moduleId << " start=" << boot.startResult << '\n';
        }
        setReturnS32(ctx, 1);'''
    if text.count(old)!=2:
        raise ValueError('Install SIFCMD probe first; unexpected reset anchors')
    path.write_text(text.replace(old,new))
    print('Installed opt-in real CDVDFSV boot execution')


if __name__=='__main__': main()
