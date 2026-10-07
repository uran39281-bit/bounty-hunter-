#!/usr/bin/env python3
"""Add opt-in IOP import and DMA counts; no guest execution changes."""
import argparse
from pathlib import Path

REPLACEMENTS = [('#include "iop_emulator.h"\n', '#include <cstdlib>\n#include "iop_emulator.h"\n'), ('            modules.clear();\n            imports.reset();\n', '            modules.clear();\n            diagnosticCounts.clear();\n            diagnosticNotes.clear();\n            imports.reset();\n'), ('        {\n            if (const auto dma = memory.takeDmaStart())\n                pendingDmaInterrupts[dma->irq] = totalCycles + dma->delayCycles;\n', '        {\n            if (const auto dma = memory.takeDmaStart()) {\n                pendingDmaInterrupts[dma->irq] = totalCycles + dma->delayCycles;\n'), ('                pendingDmaInterrupts[dma->irq] = totalCycles + dma->delayCycles;\n        }\n', '                pendingDmaInterrupts[dma->irq] = totalCycles + dma->delayCycles;\n                if (std::getenv("PS2X_IOP_IMPORT_TRACE")) {\n                    const auto chcr = dma->irq == 0x24 ? 0x1f8010c8u : 0x1f801508u;\n                    ++diagnosticCounts["DMA_START irq=" + std::to_string(dma->irq) +\n                        " bcr=" + std::to_string(memory.read32(chcr - 4u)) +\n                        " chcr=" + std::to_string(memory.read32(chcr)) +\n                        " admas=" + std::to_string(memory.read16(dma->irq == 0x24 ? 0x1f9001b0u : 0x1f9005b0u))];\n                }\n            }\n        }\n'), ('            const uint32_t a0 = cpu.gpr[4];\n            auto setV0 = [&](uint32_t value)\n', '            const uint32_t a0 = cpu.gpr[4];\n            // BOUNTY_IOP_IMPORT_TRACE\n            if (std::getenv("PS2X_IOP_IMPORT_TRACE")) {\n                ++diagnosticCounts["IMPORT " + call.library + ":" + std::to_string(call.ordinal)];\n                if (call.library == "thsemap" && call.ordinal == 4u)\n                    diagnosticNotes.push_back("SEMA_CREATE current=" + std::to_string(read32(a0 + 8u)) +\n                        " max=" + std::to_string(read32(a0 + 12u)));\n            }\n            auto setV0 = [&](uint32_t value)\n'), ('            {\n                for (const int irq : completed)\n                    (void)intrman.dispatchInterrupt(irq, *this);\n', '            {\n                for (const int irq : completed) {\n                    if (std::getenv("PS2X_IOP_IMPORT_TRACE"))\n                        ++diagnosticCounts["DMA_COMPLETED irq=" + std::to_string(irq)];\n                    (void)intrman.dispatchInterrupt(irq, *this);\n'), ('                    (void)intrman.dispatchInterrupt(irq, *this);\n            }\n', '                    (void)intrman.dispatchInterrupt(irq, *this);\n                }\n            }\n'), ('        std::map<int, Module> modules;\n        std::map<int, uint64_t> pendingDmaInterrupts;\n', '        std::map<int, Module> modules;\n        std::map<std::string, uint64_t> diagnosticCounts;\n        std::vector<std::string> diagnosticNotes;\n        std::map<int, uint64_t> pendingDmaInterrupts;\n'), ('        for (auto sid : m_impl->rpc.debugSids())', '        for (const auto &[key, count] : m_impl->diagnosticCounts)\n            rows.push_back("IOP_TRACE " + key + " count=" + std::to_string(count));\n        for (const auto &note : m_impl->diagnosticNotes)\n            rows.push_back("IOP_TRACE " + note);\n        for (auto sid : m_impl->rpc.debugSids())')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    args = parser.parse_args()
    path = args.repo / 'ps2xIOP/src/emulator/iop_emulator.cpp'
    text = path.read_text()
    if 'BOUNTY_IOP_IMPORT_TRACE' in text:
        print('IOP import trace already installed')
        return
    for old, new in REPLACEMENTS:
        if text.count(old) != 1:
            raise ValueError('Unexpected IOP trace anchor; install snapshot and execution probes first')
        text = text.replace(old, new)
    path.write_text(text)
    print('Installed opt-in IOP import and DMA counters')


if __name__ == '__main__':
    main()
