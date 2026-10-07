#!/usr/bin/env python3
"""Add module ownership and call registers to the opt-in IOP snapshot."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    args = parser.parse_args()
    path = args.repo / 'ps2xIOP/src/emulator/iop_emulator.cpp'
    text = path.read_text()
    if 'BOUNTY_IOP_EXECUTION_PROBE' in text:
        print('IOP execution probe already installed')
        return
    old = '''        for (const auto &thread : m_impl->kernel.debugThreads())
            rows.push_back("IOP_THREAD id=" + std::to_string(thread.id) +
                " pc=" + std::to_string(thread.cpu.pc) + " entry=" + std::to_string(thread.entry) +
                " state=" + std::to_string(static_cast<unsigned>(thread.state)) +
                " waitId=" + std::to_string(thread.waitId));'''
    new = '''        // BOUNTY_IOP_EXECUTION_PROBE: snapshot only; execution is unchanged.
        for (const auto &[id, module] : m_impl->modules)
            rows.push_back("IOP_MODULE id=" + std::to_string(id) + " name=" + module.name +
                " base=" + std::to_string(module.base) + " size=" + std::to_string(module.size));
        for (const auto &thread : m_impl->kernel.debugThreads()) {
            std::string owner = "unknown";
            for (const auto &[id, module] : m_impl->modules)
                if (thread.cpu.pc >= module.base && thread.cpu.pc - module.base < module.size)
                    owner = module.name;
            std::string importName = "none";
            if (const auto call = m_impl->imports.decode(thread.cpu.pc))
                importName = call->library + ":" + std::to_string(call->ordinal);
            rows.push_back("IOP_THREAD id=" + std::to_string(thread.id) +
                " pc=" + std::to_string(thread.cpu.pc) + " entry=" + std::to_string(thread.entry) +
                " state=" + std::to_string(static_cast<unsigned>(thread.state)) +
                " waitId=" + std::to_string(thread.waitId) +
                " priority=" + std::to_string(thread.priority) + " module=" + owner +
                " import=" + importName + " ra=" + std::to_string(thread.cpu.gpr[31]) +
                " a0=" + std::to_string(thread.cpu.gpr[4]) + " a1=" + std::to_string(thread.cpu.gpr[5]) +
                " v0=" + std::to_string(thread.cpu.gpr[2]));
        }'''
    if text.count(old) != 1:
        raise ValueError('Install the IOP snapshot probe first; unexpected source anchor')
    path.write_text(text.replace(old, new))
    print('Installed opt-in IOP execution snapshot')


if __name__ == '__main__':
    main()
