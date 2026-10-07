#!/usr/bin/env python3
"""Opt-in execution of supplied boot SIFCMD after IOP reset (partial boot probe)."""
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    args = parser.parse_args()
    path = args.repo/'ps2xRuntime/src/lib/Kernel/Stubs/SIF.cpp'
    text = path.read_text()
    if '// BOUNTY_BOOT_SIFCMD_PROBE' in text:
        print('Boot probe already installed')
        return
    old = '        PS2IopTransport::reset(runtime);\n        setReturnS32(ctx, 1);'
    new = r'''        PS2IopTransport::reset(runtime);
        // BOUNTY_BOOT_SIFCMD_PROBE
        if (runtime && std::getenv("PS2X_LOAD_BOOT_SIFCMD"))
        {
            const auto boot = runtime->loadIopModule("cdrom0:\\BOOT\\SIFCMD.IRX;1");
            std::cerr << "BOOT_SIFCMD handled=" << boot.handled
                      << " id=" << boot.moduleId << " start=" << boot.startResult << '\n';
        }
        setReturnS32(ctx, 1);'''
    if text.count(old) != 2:
        raise ValueError('Expected two upstream IOP reset entry points')
    path.write_text('#include <cstdlib>\n' + text.replace(old,new))
    print('Installed optional execution of supplied SIFCMD boot module')

if __name__ == '__main__':
    main()
