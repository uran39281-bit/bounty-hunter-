#!/usr/bin/env python3
"""Advance the shared EE COP0 Count from already-accounted scheduler cycles."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    args = parser.parse_args()
    path = args.repo / 'ps2xRuntime/src/lib/Kernel/EeScheduler.cpp'
    text = path.read_text()
    if 'BOUNTY_COP0_NEW_CONTEXT' in text:
        print('COP0 Count cadence already installed')
        return
    old = '    m_eeCycle += elapsed;\n    m_pendingEeTimerInterrupts'
    new = '''    m_eeCycle += elapsed;
    // BOUNTY_COP0_COUNT: one shared hardware counter, including IRQ contexts.
    // Only scheduler-accounted cycles are used; no host-time success shortcut.
    if (std::getenv("PS2X_COP0_COUNT"))
    {
        R5900Context *active = currentContext();
        const uint32_t previous = active ? active->cop0_count : m_runtime.m_cpuContext.cop0_count;
        const uint32_t count = previous + static_cast<uint32_t>(elapsed);
        m_runtime.m_cpuContext.cop0_count = count;
        for (auto &[id, item] : m_threads)
        {
            (void)id;
            item.context.cop0_count = count;
            for (auto &invocation : item.invocations)
                invocation.context.cop0_count = count;
        }
        for (auto &invocation : m_pendingInvocations)
            invocation.context.cop0_count = count;
    }
    m_pendingEeTimerInterrupts'''
    if 'BOUNTY_COP0_COUNT' not in text and text.count(old) != 1:
        raise ValueError('Unexpected scheduler cycle anchor')
    if '#include <cstdlib>' not in text:
        text = '#include <cstdlib>\n' + text
    if 'BOUNTY_COP0_COUNT' not in text:
        text = text.replace(old, new)
    hooks = {
        '    target->context.pc = target->entry;': '''    target->context.pc = target->entry;
    // BOUNTY_COP0_NEW_CONTEXT: kernel context creation does not reset hardware Count.
    if (std::getenv("PS2X_COP0_COUNT")) target->context.cop0_count = caller.cop0_count;''',
        '    invocation.sequence = ++m_invocationSequence;': '''    if (std::getenv("PS2X_COP0_COUNT"))
    {
        R5900Context *active = currentContext();
        invocation.context.cop0_count = active ? active->cop0_count : m_runtime.m_cpuContext.cop0_count;
    }
    invocation.sequence = ++m_invocationSequence;''',
        '    for (auto it = invocations.rbegin(); it != invocations.rend(); ++it)\n    {': '''    for (auto it = invocations.rbegin(); it != invocations.rend(); ++it)
    {
        if (std::getenv("PS2X_COP0_COUNT"))
            it->context.cop0_count = owner->activeContext().cop0_count;''',
    }
    for anchor, replacement in hooks.items():
        if text.count(anchor) != (2 if anchor.startswith('    invocation.sequence') else 1):
            raise ValueError('Unexpected new-context anchor')
        text = text.replace(anchor, replacement)
    path.write_text(text)
    print('Installed opt-in shared COP0 Count from scheduler cycles')


if __name__ == '__main__':
    main()
