#!/usr/bin/env python3
"""Log actual EE CreateThread parameters and results; no scheduler behavior changes."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    args = parser.parse_args()
    path = args.repo / 'ps2xRuntime/src/lib/Kernel/Syscalls/Thread.cpp'
    text = path.read_text()
    if 'BOUNTY_EE_THREAD_PROBE' in text:
        print('EE thread probe already installed')
        return
    old = '        setReturnS32(ctx, scheduler(rdram, ctx, runtime).createThread(decoded));'
    new = '''        // BOUNTY_EE_THREAD_PROBE: diagnostic only.
        const int result = scheduler(rdram, ctx, runtime).createThread(decoded);
        if (std::getenv("PS2X_EE_THREAD_TRACE"))
            std::cerr << "EE_CREATE_THREAD entry=" << decoded.entry
                      << " stack=" << decoded.stack << " size=" << decoded.stackSize
                      << " priority=" << decoded.priority << " result=" << result << '\\n';
        setReturnS32(ctx, result);'''
    if text.count(old) != 1:
        raise ValueError('Unexpected CreateThread anchor')
    text = text.replace('#include "Common.h"', '#include "Common.h"\n#include <cstdlib>\n#include <iostream>')
    path.write_text(text.replace(old, new))
    print('Installed opt-in EE thread diagnostic')


if __name__ == '__main__':
    main()
