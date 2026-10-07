#!/usr/bin/env python3
"""Install an opt-in pre-copy diagnostic into a dedicated runtime checkout.

PS2X_STOP_INVALID_MEMCPY=1 records registers and stops before the upstream
size clamp can overwrite guest RAM. No return values or game inputs change.
"""
import argparse
from pathlib import Path

MARKER = '// BOUNTY_PRECOPY_PROBE'
PROBE = r'''        // BOUNTY_PRECOPY_PROBE
        if (size > PS2_RAM_SIZE && std::getenv("PS2X_STOP_INVALID_MEMCPY"))
        {
            std::cerr << "INVALID_MEMCPY_PRECOPY pc=0x" << std::hex << ctx->pc
                      << " ra=0x" << getRegU32(ctx, 31)
                      << " sp=0x" << getRegU32(ctx, 29)
                      << " dst=0x" << destAddr << " src=0x" << srcAddr
                      << " size=0x" << size << std::dec << '\n';
            for (unsigned reg = 0; reg < 32; ++reg)
                std::cerr << "REG " << reg << "=0x" << std::hex
                          << getRegU32(ctx, reg) << std::dec << '\n';
            if (const char *path = std::getenv("PS2X_PRECOPY_RAM_DUMP"))
            {
                std::ofstream dump(path, std::ios::binary);
                dump.write(reinterpret_cast<const char *>(rdram), PS2_RAM_SIZE);
                if (!dump) throw std::runtime_error("Precopy RAM dump failed");
            }
            throw std::runtime_error("Invalid memcpy stopped before guest RAM write");
        }
'''

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    args = parser.parse_args()
    path = args.repo / 'ps2xRuntime/src/lib/Kernel/Stubs/LibC.cpp'
    text = path.read_text()
    if MARKER in text:
        print('Probe already installed')
        return
    anchor = '        size = sanitizeMemTransferSize(size, "memcpy");'
    if text.count(anchor) != 1:
        raise ValueError('Unexpected upstream memcpy implementation')
    text = '#include <cstdlib>\n#include <fstream>\n#include <stdexcept>\n' + text
    path.write_text(text.replace(anchor, PROBE + anchor))
    print('Installed opt-in pre-copy probe')

if __name__ == '__main__':
    main()
