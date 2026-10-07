#!/usr/bin/env python3
"""Opt-in eight-byte va_list slots observed in the unchanged native callers."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    args = parser.parse_args()
    lib = args.repo / 'ps2xRuntime/src/lib/Kernel/Stubs'
    path = lib / 'Helpers/Support.h'
    text = path.read_text()
    if 'BOUNTY_EE_VALIST' not in text:
        start = text.index('    class Ps2VaListCursor')
        end = text.index('    template <typename NextU32Fn', start)
        body = text[start:end]
        old = '            m_curr += 4;'
        assert body.count(old) == 1
        body = body.replace(old, '''            // BOUNTY_EE_VALIST: native callers use SD at eight-byte intervals.
            m_curr += std::getenv("PS2X_EE_VA64") ? 8u : 4u;''')
        old = '            m_curr = (m_curr + 7u) & ~7u;'
        assert body.count(old) == 1
        body = body.replace(old, old + '''
            if (std::getenv("PS2X_EE_VA64"))
            {
                uint32_t low=0, high=0;
                (void)tryReadWordFromGuest(m_rdram, m_runtime, m_curr, low);
                (void)tryReadWordFromGuest(m_rdram, m_runtime, m_curr+4u, high);
                m_curr += 8u;
                return static_cast<uint64_t>(low) | (static_cast<uint64_t>(high)<<32u);
            }''')
        if '#include <cstdlib>' not in text:
            text = '#include <cstdlib>\n' + text
            start = text.index('    class Ps2VaListCursor')
            end = text.index('    template <typename NextU32Fn', start)
        path.write_text(text[:start] + body + text[end:])
    path = lib / 'LibC.cpp'
    text = path.read_text()
    if 'BOUNTY_EE_FORMAT_TRACE' not in text:
        start = text.index('    void vsprintf(')
        end = text.index('\n    void ', start+10)
        body = text[start:end]
        anchor = '            std::string rendered = formatPs2StringWithVaList(rdram, runtime, formatOwned.c_str(), va_list_addr);'
        assert body.count(anchor) == 1
        body = body.replace(anchor, anchor + '''
            // BOUNTY_EE_FORMAT_TRACE: bounded original formatting calls.
            if (std::getenv("PS2X_BOOT_GRAPHICS_TRACE"))
            {
                static thread_local uint32_t hit=0;
                if (++hit<=64u)
                    std::cerr << "BOOT_FORMAT hit=" << hit << " va64=" << bool(std::getenv("PS2X_EE_VA64"))
                        << " format=" << sanitizeForLog(formatOwned)
                        << " output=" << sanitizeForLog(rendered) << '\\n';
            }''')
        path.write_text(text[:start]+body+text[end:])
    print('Installed opt-in native eight-byte va_list slots and bounded format trace')


if __name__ == '__main__':
    main()
