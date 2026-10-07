#!/usr/bin/env python3
"""Log a real guest return to PC zero, including its final dispatch address."""
import argparse
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo',type=Path)
    args=parser.parse_args();path=args.repo/'ps2xRuntime/src/lib/Kernel/EeScheduler.cpp';text=path.read_text()
    if 'BOUNTY_EE_RETURN_PROBE' in text:
        print('EE return trace already installed');return
    old='''            function(m_rdram, &context, &m_runtime);
            m_guestExecuting.store(false, std::memory_order_release);'''
    new='''            // BOUNTY_EE_RETURN_PROBE: a PC-zero return is observable, not success.
            const uint32_t dispatchedPc = context.pc;
            function(m_rdram, &context, &m_runtime);
            if (context.pc == 0u && running->invocations.empty() &&
                std::getenv("PS2X_EE_THREAD_TRACE"))
                std::cerr << "EE_RETURN_ZERO id=" << running->id << " dispatch=" << dispatchedPc
                          << " ra=" << getRegU32(&context, 31)
                          << " v0=" << getRegU32(&context, 2) << '\\n';
            m_guestExecuting.store(false, std::memory_order_release);'''
    if text.count(old)!=1:raise ValueError('Unexpected EE dispatch anchor')
    if '#include <iostream>' not in text:text='#include <iostream>\n'+text
    path.write_text(text.replace(old,new));print('Installed read-only EE zero-return trace')


if __name__=='__main__':main()
