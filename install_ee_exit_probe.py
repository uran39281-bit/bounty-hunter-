#!/usr/bin/env python3
"""Trace actual EE thread exit registers without changing guest behavior."""
import argparse
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo',type=Path)
    args=parser.parse_args()
    path=args.repo/'ps2xRuntime/src/lib/Kernel/EeScheduler.cpp';text=path.read_text()
    if 'BOUNTY_EE_EXIT_PROBE' in text:
        print('EE exit trace already installed');return
    old='''    const int id = exiting->id;
    const uint32_t ownedStack'''
    new='''    const int id = exiting->id;
    // BOUNTY_EE_EXIT_PROBE: log before the real thread becomes dormant.
    if (std::getenv("PS2X_EE_THREAD_TRACE"))
        std::cerr << "EE_THREAD_EXIT id=" << id << " pc=" << exiting->context.pc
                  << " ra=" << getRegU32(&exiting->context, 31)
                  << " a0=" << getRegU32(&exiting->context, 4) << '\\n';
    const uint32_t ownedStack'''
    if text.count(old)!=1:raise ValueError('Unexpected scheduler exit anchor')
    text=text.replace(old,new)
    if '#include <iostream>' not in text:text='#include <iostream>\n'+text
    path.write_text(text)
    print('Installed read-only EE exit trace')


if __name__=='__main__':main()
