#!/usr/bin/env python3
"""Opt-in SPU2 AutoDMA write cadence; not an audio renderer or full SPU2 model."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    args = parser.parse_args()
    path = args.repo / 'ps2xIOP/src/emulator/core/iop_memory.cpp'
    text = path.read_text()
    if 'BOUNTY_SPU2_ADMA_TIMING' in text:
        print('SPU2 AutoDMA timing already installed')
        return
    old = '''        m_dmaStart = DmaStart{
            secondCore ? kDmaSpu1Irq : kDmaSpu0Irq,
            std::max<uint64_t>(transferWords * 2u, 64u),
        };'''
    new = '''        uint64_t completionDelay = std::max<uint64_t>(transferWords * 2u, 64u);
        // BOUNTY_SPU2_ADMA_TIMING
        // AutoDMA streams 16-bit stereo samples at 48 kHz. One 32-bit DMA
        // word supplies one stereo frame: 36.864 MHz / 48 kHz = 768 cycles.
        // Bus-copy timing alone continually refills the worker semaphore,
        // preventing lower-priority RPC initialization from running.
        // This models completion cadence only; it does not render audio.
        const uint16_t admas = read16(0x1F9001B0u + (secondCore ? 0x400u : 0u));
        const uint16_t coreBit = secondCore ? 2u : 1u;
        if (std::getenv("PS2X_SPU2_ADMA_TIMING") && (value & 1u) != 0u &&
            (admas & coreBit) != 0u)
            completionDelay = transferWords * 768u;
        m_dmaStart = DmaStart{
            secondCore ? kDmaSpu1Irq : kDmaSpu0Irq,
            completionDelay,
        };'''
    if text.count(old) != 1:
        raise ValueError('Unexpected IOP DMA timing anchor')
    path.write_text('#include <cstdlib>\n' + text.replace(old, new))
    print('Installed opt-in SPU2 AutoDMA write completion cadence')


if __name__ == '__main__':
    main()
