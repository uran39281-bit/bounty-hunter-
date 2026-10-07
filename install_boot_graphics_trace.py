#!/usr/bin/env python3
"""Bounded read-only trace of native boot graphics calls and buffer state."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    args = parser.parse_args()
    path = args.repo / 'ps2xRuntime/src/lib/ps2_runtime.cpp'
    text = path.read_text()
    if 'BOUNTY_BOOT_GRAPHICS_TRACE' in text:
        print('Boot graphics trace already installed')
        return
    old = '    ctx->pc = targetPc;\n    const bool isCall = (kind == GuestBranchKind::DirectCall'
    new = '''    ctx->pc = targetPc;
    // BOUNTY_BOOT_GRAPHICS_TRACE: no guest writes or injected packets.
    if (std::getenv("PS2X_BOOT_GRAPHICS_TRACE") &&
        (targetPc == 0x349790u || targetPc == 0x3420f0u ||
         targetPc == 0x3423c0u || targetPc == 0x334540u ||
         targetPc == 0x18f9e0u || targetPc == 0x347a00u ||
         targetPc == 0x347410u || targetPc == 0x33fda0u))
    {
        static thread_local std::unordered_map<uint32_t, uint32_t> counts;
        const uint32_t hit = ++counts[targetPc];
        if (hit <= 8u || hit == 64u || hit == 1024u)
        {
            const uint32_t gp = static_cast<uint32_t>(_mm_cvtsi128_si32(ctx->r[28]));
            auto word = [&](uint32_t address) -> uint32_t {
                return address <= PS2_RAM_SIZE - 4u ? m_memory.read32(address) : 0u;
            };
            std::cerr << "BOOT_GRAPHICS_CALL target=0x" << std::hex << targetPc
                      << " source=0x" << sourcePc << " a0=0x"
                      << static_cast<uint32_t>(_mm_cvtsi128_si32(ctx->r[4]))
                      << " buffer=0x" << word(0x454918u)
                      << " end=0x" << word(0x45491cu)
                      << " surface=0x" << word(gp-0x3a20u)
                      << std::dec << " current=" << word(gp-0x38fcu)
                      << " requested=" << word(gp-0x38f8u)
                      << " count=" << ctx->cop0_count << " hit=" << hit << '\\n';
        }
    }
    const bool isCall = (kind == GuestBranchKind::DirectCall'''
    if text.count(old) != 1:
        raise ValueError('Unexpected guest branch anchor')
    path.write_text(text.replace(old, new))
    print('Installed read-only bounded boot graphics trace')


if __name__ == '__main__':
    main()
