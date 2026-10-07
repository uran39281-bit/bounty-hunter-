#!/usr/bin/env python3
"""Add opt-in file tracing and lowest-free descriptor reuse to a pinned checkout."""
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    args = parser.parse_args()
    path = args.repo/'ps2xRuntime/src/lib/ps2_vfs.cpp'
    text = path.read_text()
    if '// BOUNTY_VFS_PROBE' in text:
        print('VFS probe already installed')
        return
    old = '''    if (m_nextDescriptor < 3)
        m_nextDescriptor = 3;
    const int32_t descriptor = m_nextDescriptor++;
    m_descriptors.emplace(descriptor, OpenDescriptor{std::move(file), parsed.deviceName, std::string(path)});
    return descriptor;'''
    new = '''    // BOUNTY_VFS_PROBE
    int32_t descriptor;
    if (std::getenv("PS2X_VFS_REUSE_DESCRIPTORS"))
    {
        descriptor = 3;
        while (m_descriptors.contains(descriptor))
        {
            if (descriptor == std::numeric_limits<int32_t>::max()) return -1;
            ++descriptor;
        }
    }
    else
    {
        if (m_nextDescriptor < 3) m_nextDescriptor = 3;
        descriptor = m_nextDescriptor++;
    }
    m_descriptors.emplace(descriptor, OpenDescriptor{std::move(file), parsed.deviceName, std::string(path)});
    if (std::getenv("PS2X_VFS_TRACE"))
        std::cerr << "VFS_OPEN fd=" << descriptor << " path=" << path << '\\n';
    return descriptor;'''
    close_old = '    return m_descriptors.erase(descriptor) == 1u ? 0 : -1;'
    close_new = '''    const int32_t result = m_descriptors.erase(descriptor) == 1u ? 0 : -1;
    if (std::getenv("PS2X_VFS_TRACE"))
        std::cerr << "VFS_CLOSE fd=" << descriptor << " result=" << result << '\\n';
    return result;'''
    if text.count(old) != 1 or text.count(close_old) != 1:
        raise ValueError('Unexpected upstream descriptor allocator')
    text = '#include <cstdlib>\n#include <iostream>\n' + text.replace(old,new).replace(close_old,close_new)
    path.write_text(text)
    print('Installed opt-in VFS tracing/reuse experiment')

if __name__ == '__main__':
    main()
