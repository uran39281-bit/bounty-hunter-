#!/usr/bin/env python3
"""Opt-in CDVDFSV imports: real read buffer and layer-zero host-file lookup."""
import argparse
from pathlib import Path

EDITS = [
('            initialized = false;','''            initialized = false;
            // BOUNTY_CDVD_IMPORTS: release the owned read buffer on reset.
            if (fsvReadBuffer != 0u) (void)memory.freeAllocation(fsvReadBuffer);
            fsvReadBuffer = 0u;'''),
('''            case 75: // sceCdMmode''','''            case 47: // sceGetFsvRbuf
                if (!std::getenv("PS2X_CDVD_COMPAT")) return false;
                // PS2SDK cdvdman owns a 42128-byte shared FSV read buffer.
                if (fsvReadBuffer == 0u) fsvReadBuffer = memory.allocate(42128u, 64u);
                cpu.gpr[2] = fsvReadBuffer;
                return true;

            case 84: // sceCdLayerSearchFile
                if (!std::getenv("PS2X_CDVD_COMPAT")) return false;
                // The existing host-folder virtual ISO has one layer.
                // Unsupported layer values fail without inventing files.
                cpu.gpr[2] = a2 == 0u && searchFile(a0, a1) ? 1u : 0u;
                return true;

            case 75: // sceCdMmode'''),
('''            IsoNode *node = findVirtualIsoNode(guestPath);
            if (!node)''','''            IsoNode *node = findVirtualIsoNode(guestPath);
            if (std::getenv("PS2X_IOP_IMPORT_TRACE"))
                host.log(LogLevel::Info, "[IOP CDVD search] path=" + guestPath +
                    " found=" + std::to_string(node != nullptr));
            if (!node)'''),
('        bool initialized = false;','        bool initialized = false;\n        uint32_t fsvReadBuffer = 0u;'),
]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo',type=Path)
    args=parser.parse_args()
    path=args.repo/'ps2xIOP/src/emulator/imports/iop_cdvd.cpp';text=path.read_text()
    if 'BOUNTY_CDVD_IMPORTS' in text:
        print('CDVD compatibility imports already installed');return
    for old,new in EDITS:
        if text.count(old)!=1:raise ValueError('Unexpected CDVD import anchor')
        text=text.replace(old,new)
    text='#include <cstdlib>\n'+text
    path.write_text(text)
    print('Installed opt-in CDVD FSV buffer and actual layer-zero file lookup')


if __name__=='__main__':main()
