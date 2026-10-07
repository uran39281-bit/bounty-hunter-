#!/usr/bin/env python3
"""Expose read-only IOP thread PCs, waits, initialized SIF state and actual RPC SIDs."""
import argparse
from pathlib import Path

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('repo', type=Path)
    args = p.parse_args()
    root = args.repo/'ps2xIOP/src'
    edits = [
        ('emulator/core/iop_kernel.h', '#include <map>', '#include <map>\n#include <vector>'),
        ('emulator/core/iop_kernel.h', '        [[nodiscard]] size_t threadCount() const noexcept { return m_threads.size(); }',
         '''        [[nodiscard]] size_t threadCount() const noexcept { return m_threads.size(); }
        // BOUNTY_IOP_SNAPSHOT
        [[nodiscard]] std::vector<IopThread> debugThreads() const {
            std::vector<IopThread> rows;
            for (const auto &[id, thread] : m_threads) rows.push_back(thread);
            return rows;
        }'''),
        ('emulator/services/iop_rpc.h', '        [[nodiscard]] size_t serverCount() const noexcept { return m_servers.size(); }',
         '''        [[nodiscard]] size_t serverCount() const noexcept { return m_servers.size(); }
        [[nodiscard]] bool sifInitialized() const noexcept { return m_sifInitialized; }
        [[nodiscard]] std::vector<uint32_t> debugSids() const {
            std::vector<uint32_t> rows;
            for (const auto &[sid, server] : m_servers) rows.push_back(sid);
            return rows;
        }'''),
        ('emulator/iop_emulator.h', '        [[nodiscard]] uint32_t rpcServerCount() const noexcept;',
         '        [[nodiscard]] uint32_t rpcServerCount() const noexcept;\n        void appendDiagnosticRows(std::vector<std::string> &rows) const;'),
        ('emulator/iop_emulator.cpp', '    uint32_t IopEmulator::rpcServerCount() const noexcept',
         '''    void IopEmulator::appendDiagnosticRows(std::vector<std::string> &rows) const
    {
        rows.push_back("IOP_SIF_INITIALIZED " + std::to_string(m_impl->rpc.sifInitialized()));
        for (const auto &thread : m_impl->kernel.debugThreads())
            rows.push_back("IOP_THREAD id=" + std::to_string(thread.id) +
                " pc=" + std::to_string(thread.cpu.pc) + " entry=" + std::to_string(thread.entry) +
                " state=" + std::to_string(static_cast<unsigned>(thread.state)) +
                " waitId=" + std::to_string(thread.waitId));
        for (auto sid : m_impl->rpc.debugSids())
            rows.push_back("IOP_RPC_SID " + std::to_string(sid));
    }

    uint32_t IopEmulator::rpcServerCount() const noexcept'''),
        ('iop_subsystem.cpp', '        snapshot.diagnostics = m_impl->loadOutcomes;',
         '        snapshot.diagnostics = m_impl->loadOutcomes;\n        if (std::getenv("PS2X_IOP_SNAPSHOT"))\n            m_impl->emulator.appendDiagnosticRows(snapshot.diagnostics);')]
    if 'BOUNTY_IOP_SNAPSHOT' in (root/'emulator/core/iop_kernel.h').read_text():
        print('IOP snapshot probe already installed')
        return
    contents = {}
    for name, old, new in edits:
        path = root/name
        text = contents.get(path, path.read_text())
        if text.count(old) != 1: raise ValueError(f'Unexpected anchor: {name}')
        contents[path] = text.replace(old,new)
    for path, text in contents.items():
        if path.name == 'iop_subsystem.cpp': text = '#include <cstdlib>\n' + text
        path.write_text(text)
    print('Installed read-only IOP diagnostic rows')

if __name__ == '__main__':
    main()
