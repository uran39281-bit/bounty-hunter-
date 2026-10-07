#!/usr/bin/env python3
"""Read-only, bounded DMA/VIF metadata tracing for real graphics submission."""
import argparse
from pathlib import Path


def patch(path, marker, anchor, replacement):
    text = path.read_text()
    if marker in text:
        return
    if text.count(anchor) != 1:
        raise ValueError('Unexpected graphics trace anchor: ' + str(path))
    for header in ['cstdlib', 'iostream']:
        if f'#include <{header}>' not in text:
            text = f'#include <{header}>\n' + text
    path.write_text(text.replace(anchor, replacement))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    args = parser.parse_args()
    lib = args.repo / 'ps2xRuntime/src/lib'
    anchor = '            m_dmaStartCount.fetch_add(1, std::memory_order_relaxed);'
    patch(lib / 'ps2_memory.cpp', 'BOUNTY_DMA_GRAPHICS_TRACE', anchor, anchor + '''
            // BOUNTY_DMA_GRAPHICS_TRACE: decoded register metadata only.
            if (std::getenv("PS2X_BOOT_GRAPHICS_TRACE") &&
                (channelBase == 0x10009000u || channelBase == 0x1000a000u))
            {
                static thread_local uint32_t graphicsStarts = 0;
                const uint32_t hit = ++graphicsStarts;
                if (hit <= 24u || hit == 64u || hit == 1024u)
                    std::cerr << "BOOT_GRAPHICS_DMA channel=0x" << std::hex << channelBase
                              << " chcr=0x" << value << " madr=0x" << madr
                              << " tadr=0x" << m_ioRegisters[channelBase+0x30u]
                              << std::dec << " qwc=" << qwc << " hit=" << hit << '\\n';
            }''')
    anchor = '        // Track most-recent command for VIFn_CODE emulation.'
    patch(lib / 'ps2_vif1_interpreter.cpp', 'BOUNTY_VIF_GRAPHICS_TRACE', anchor, anchor + '''
        // BOUNTY_VIF_GRAPHICS_TRACE: no packet alteration or replay.
        if (std::getenv("PS2X_BOOT_GRAPHICS_TRACE"))
        {
            static thread_local uint32_t commands = 0;
            const uint32_t hit = ++commands;
            if (hit <= 32u || (opcode == VIF_DIRECT && hit <= 256u))
                std::cerr << "BOOT_GRAPHICS_VIF opcode=" << uint32_t(opcode)
                          << " imm=" << imm << " num=" << uint32_t(num)
                          << " remaining=" << sizeBytes-pos << " hit=" << hit << '\\n';
        }''')
    print('Installed bounded read-only DMA/VIF metadata trace')


if __name__ == '__main__':
    main()
