#!/usr/bin/env python3
"""Route opt-in SPR normal receive through the existing real DMA memory engine."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    args = parser.parse_args()
    path = args.repo / 'ps2xRuntime/src/lib/Kernel/Stubs/DMA.cpp'
    text = path.read_text()
    if 'BOUNTY_SPR_RECVN' in text:
        print('Scratchpad receive already installed')
        return
    old = '        TODO_NAMED("sceDmaRecvN", rdram, ctx, runtime);'
    new = '''        // BOUNTY_SPR_RECVN: only the implemented scratchpad-from channel.
        const uint32_t channel = resolveDmaChannelBase(rdram, getRegU32(ctx, 4));
        if (!std::getenv("PS2X_SPR_RECVN") || channel != 0x1000D000u) {
            TODO_NAMED("sceDmaRecvN", rdram, ctx, runtime);
            return;
        }
        const uint32_t address = getRegU32(ctx, 5) & 0x7FFFFFF0u;
        const uint32_t qwc = getRegU32(ctx, 6);
        if (!runtime || qwc > 0xFFFFu) {
            setReturnS32(ctx, -1);
            return;
        }
        auto &memory = runtime->memory();
        const uint32_t control = memory.readIORegister(channel);
        uint32_t offset = 0u;
        try { offset = memory.translateAddress(address); }
        catch (const std::exception &) { setReturnS32(ctx, -1); return; }
        if (offset > PS2_RAM_SIZE || qwc * 16u > PS2_RAM_SIZE - offset ||
            (control & 0x100u) != 0u) {
            setReturnS32(ctx, -1);
            return;
        }
        memory.writeIORegister(channel + 0x10u, address);
        memory.writeIORegister(channel + 0x20u, qwc);
        memory.writeIORegister(channel, (control & ~0xDu) | 0x100u);
        setReturnS32(ctx, 0);'''
    if text.count(old) != 1:
        raise ValueError('Unexpected sceDmaRecvN anchor')
    path.write_text(text.replace(old, new))
    print('Installed opt-in scratchpad DMA receive')


if __name__ == '__main__':
    main()
