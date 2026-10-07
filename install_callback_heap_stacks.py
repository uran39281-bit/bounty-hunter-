#!/usr/bin/env python3
"""Opt-in callback stacks in allocated guest heap, separated from main stack."""
import argparse
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('repo',type=Path)
    args=parser.parse_args();path=args.repo/'ps2xRuntime/src/lib/ps2_runtime.cpp';text=path.read_text()
    if 'BOUNTY_CALLBACK_HEAP_STACKS' in text:
        print('Callback stack separation already installed');return
    old='''    std::lock_guard<std::mutex> lock(m_asyncCallbackStackMutex);
    uint32_t top = m_asyncCallbackStackTop;'''
    new='''    // BOUNTY_CALLBACK_HEAP_STACKS: avoid the main thread's top-of-RAM stack.
    // Allocate real guest memory; allocation failure remains failure.
    if (std::getenv("PS2X_CALLBACK_HEAP_STACKS")) {
        const uint32_t base = guestMalloc(allocSize, normalizedAlignment);
        return base != 0u ? base + allocSize - 0x10u : 0u;
    }
    std::lock_guard<std::mutex> lock(m_asyncCallbackStackMutex);
    uint32_t top = m_asyncCallbackStackTop;'''
    if text.count(old)!=1:raise ValueError('Unexpected callback stack allocation anchor')
    if '#include <cstdlib>' not in text:text='#include <cstdlib>\n'+text
    path.write_text(text.replace(old,new));print('Installed opt-in allocated callback stack separation')


if __name__=='__main__':main()
