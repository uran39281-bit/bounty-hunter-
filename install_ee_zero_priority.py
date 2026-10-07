#!/usr/bin/env python3
"""Allow real priority-zero EE thread creation when explicitly enabled."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    args = parser.parse_args()
    path = args.repo / 'ps2xRuntime/src/lib/Kernel/EeScheduler.cpp'
    text = path.read_text()
    if 'BOUNTY_EE_ZERO_PRIORITY' in text:
        print('EE priority-zero compatibility already installed')
        return
    old = '''    if (params.priority < 1 || params.priority >= kPriorityCount)'''
    new = '''    // BOUNTY_EE_ZERO_PRIORITY: PS2SDK creates an actual priority-zero EE thread.
    // Keep baseline validation unless the compatibility experiment is enabled.
    const int minimumPriority = std::getenv("PS2X_EE_ZERO_PRIORITY") ? 0 : 1;
    if (params.priority < minimumPriority || params.priority >= kPriorityCount)'''
    if text.count(old) != 1:
        raise ValueError('Unexpected EE priority validation anchor')
    if '#include <cstdlib>' not in text:
        text = '#include <cstdlib>\n' + text
    path.write_text(text.replace(old, new))
    print('Installed opt-in priority-zero EE thread creation')


if __name__ == '__main__':
    main()
